
# === NexusCore/src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

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

# === NexusCore/tools\exports\export_20250803_114325\combined_127.py ===

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta.types import safety, text_service

from .client import TextServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .transports.grpc_asyncio import TextServiceGrpcAsyncIOTransport


class TextServiceAsyncClient:
    """API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.
    """

    _client: TextServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = TextServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = TextServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = TextServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = TextServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(TextServiceClient.model_path)
    parse_model_path = staticmethod(TextServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        TextServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        TextServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(TextServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(TextServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(TextServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        TextServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(TextServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        TextServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(TextServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        TextServiceClient.parse_common_location_path
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
            TextServiceAsyncClient: The constructed client.
        """
        return TextServiceClient.from_service_account_info.__func__(TextServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            TextServiceAsyncClient: The constructed client.
        """
        return TextServiceClient.from_service_account_file.__func__(TextServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return TextServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> TextServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            TextServiceTransport: The transport used by the client instance.
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
        type(TextServiceClient).get_transport_class, type(TextServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, TextServiceTransport, Callable[..., TextServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the text service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,TextServiceTransport,Callable[..., TextServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the TextServiceTransport constructor.
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
        self._client = TextServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_text(
        self,
        request: Optional[Union[text_service.GenerateTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.GenerateTextResponse:
        r"""Generates a response from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_generate_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta.GenerateTextRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.generate_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GenerateTextRequest, dict]]):
                The request object. Request to generate a text completion
                response from the model.
            model (:class:`str`):
                Required. The name of the ``Model`` or ``TunedModel`` to
                use for generating the completion. Examples:
                models/text-bison-001
                tunedModels/sentence-translator-u3b7m

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta.types.TextPrompt`):
                Required. The free-form input text
                given to the model as a prompt.
                Given a prompt, the model will generate
                a TextCompletion response it predicts as
                the completion of the input text.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (:class:`float`):
                Optional. Controls the randomness of the output. Note:
                The default value varies by model, see the
                ``Model.temperature`` attribute of the ``Model``
                returned the ``getModel`` function.

                Values can range from [0.0,1.0], inclusive. A value
                closer to 1.0 will produce responses that are more
                varied and creative, while a value closer to 0.0 will
                typically result in more straightforward responses from
                the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (:class:`int`):
                Optional. Number of generated responses to return.

                This value must be between [1, 8], inclusive. If unset,
                this will default to 1.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            max_output_tokens (:class:`int`):
                Optional. The maximum number of tokens to include in a
                candidate.

                If unset, this will default to output_token_limit
                specified in the ``Model`` specification.

                This corresponds to the ``max_output_tokens`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (:class:`float`):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Tokens are sorted based on their assigned probabilities
                so that only the most likely tokens are considered.
                Top-k sampling directly limits the maximum number of
                tokens to consider, while Nucleus sampling limits number
                of tokens based on the cumulative probability.

                Note: The default value varies by model, see the
                ``Model.top_p`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (:class:`int`):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens. Defaults to 40.

                Note: The default value varies by model, see the
                ``Model.top_k`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateTextResponse:
                The response from the model,
                including candidate completions.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [
                model,
                prompt,
                temperature,
                candidate_count,
                max_output_tokens,
                top_p,
                top_k,
            ]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.GenerateTextRequest):
            request = text_service.GenerateTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt
        if temperature is not None:
            request.temperature = temperature
        if candidate_count is not None:
            request.candidate_count = candidate_count
        if max_output_tokens is not None:
            request.max_output_tokens = max_output_tokens
        if top_p is not None:
            request.top_p = top_p
        if top_k is not None:
            request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def embed_text(
        self,
        request: Optional[Union[text_service.EmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        text: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.EmbedTextResponse:
        r"""Generates an embedding from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_embed_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.EmbedTextRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.EmbedTextRequest, dict]]):
                The request object. Request to get a text embedding from
                the model.
            model (:class:`str`):
                Required. The model name to use with
                the format model=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            text (:class:`str`):
                Optional. The free-form input text
                that the model will turn into an
                embedding.

                This corresponds to the ``text`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.EmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, text])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.EmbedTextRequest):
            request = text_service.EmbedTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if text is not None:
            request.text = text

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.embed_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def batch_embed_text(
        self,
        request: Optional[Union[text_service.BatchEmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        texts: Optional[MutableSequence[str]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.BatchEmbedTextResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_batch_embed_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.BatchEmbedTextRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.batch_embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.BatchEmbedTextRequest, dict]]):
                The request object. Batch request to get a text embedding
                from the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the embedding. Examples:
                models/embedding-gecko-001

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            texts (:class:`MutableSequence[str]`):
                Optional. The free-form input texts
                that the model will turn into an
                embedding. The current limit is 100
                texts, over which an error will be
                thrown.

                This corresponds to the ``texts`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchEmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, texts])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.BatchEmbedTextRequest):
            request = text_service.BatchEmbedTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if texts:
            request.texts.extend(texts)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_embed_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def count_text_tokens(
        self,
        request: Optional[Union[text_service.CountTextTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.CountTextTokensResponse:
        r"""Runs a model's tokenizer on a text and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_count_text_tokens():
                # Create a client
                client = generativelanguage_v1beta.TextServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta.CountTextTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.count_text_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CountTextTokensRequest, dict]]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta.types.TextPrompt`):
                Required. The free-form input text
                given to the model as a prompt.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountTextTokensResponse:
                A response from CountTextTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.CountTextTokensRequest):
            request = text_service.CountTextTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_text_tokens
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def __aenter__(self) -> "TextServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("TextServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\anthropic\_response.py ===
from __future__ import annotations

import os
import inspect
import logging
import datetime
import functools
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    Generic,
    TypeVar,
    Callable,
    Iterator,
    AsyncIterator,
    cast,
    overload,
)
from typing_extensions import Awaitable, ParamSpec, override, get_origin

import anyio
import httpx
import pydantic

from ._types import NoneType
from ._utils import is_given, extract_type_arg, is_annotated_type, extract_type_var_from_base
from ._models import BaseModel, is_basemodel
from ._constants import RAW_RESPONSE_HEADER, OVERRIDE_CAST_TO_HEADER
from ._streaming import Stream, AsyncStream, is_stream_class_type, extract_stream_chunk_type
from ._exceptions import AnthropicError, APIResponseValidationError
from ._decoders.jsonl import JSONLDecoder, AsyncJSONLDecoder

if TYPE_CHECKING:
    from ._models import FinalRequestOptions
    from ._base_client import BaseClient


P = ParamSpec("P")
R = TypeVar("R")
_T = TypeVar("_T")
_APIResponseT = TypeVar("_APIResponseT", bound="APIResponse[Any]")
_AsyncAPIResponseT = TypeVar("_AsyncAPIResponseT", bound="AsyncAPIResponse[Any]")

log: logging.Logger = logging.getLogger(__name__)


class BaseAPIResponse(Generic[R]):
    _cast_to: type[R]
    _client: BaseClient[Any, Any]
    _parsed_by_type: dict[type[Any], Any]
    _is_sse_stream: bool
    _stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None
    _options: FinalRequestOptions

    http_response: httpx.Response

    retries_taken: int
    """The number of retries made. If no retries happened this will be `0`"""

    def __init__(
        self,
        *,
        raw: httpx.Response,
        cast_to: type[R],
        client: BaseClient[Any, Any],
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        options: FinalRequestOptions,
        retries_taken: int = 0,
    ) -> None:
        self._cast_to = cast_to
        self._client = client
        self._parsed_by_type = {}
        self._is_sse_stream = stream
        self._stream_cls = stream_cls
        self._options = options
        self.http_response = raw
        self.retries_taken = retries_taken

    @property
    def headers(self) -> httpx.Headers:
        return self.http_response.headers

    @property
    def http_request(self) -> httpx.Request:
        """Returns the httpx Request instance associated with the current response."""
        return self.http_response.request

    @property
    def status_code(self) -> int:
        return self.http_response.status_code

    @property
    def url(self) -> httpx.URL:
        """Returns the URL for which the request was made."""
        return self.http_response.url

    @property
    def method(self) -> str:
        return self.http_request.method

    @property
    def http_version(self) -> str:
        return self.http_response.http_version

    @property
    def elapsed(self) -> datetime.timedelta:
        """The time taken for the complete request/response cycle to complete."""
        return self.http_response.elapsed

    @property
    def is_closed(self) -> bool:
        """Whether or not the response body has been closed.

        If this is False then there is response data that has not been read yet.
        You must either fully consume the response body or call `.close()`
        before discarding the response to prevent resource leaks.
        """
        return self.http_response.is_closed

    @override
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} [{self.status_code} {self.http_response.reason_phrase}] type={self._cast_to}>"
        )

    def _parse(self, *, to: type[_T] | None = None) -> R | _T:
        # unwrap `Annotated[T, ...]` -> `T`
        if to and is_annotated_type(to):
            to = extract_type_arg(to, 0)

        cast_to = to if to is not None else self._cast_to
        origin = get_origin(cast_to) or cast_to

        if inspect.isclass(origin):
            if issubclass(origin, (JSONLDecoder)):
                return cast(
                    R,
                    cast("type[JSONLDecoder[Any]]", cast_to)(
                        raw_iterator=self.http_response.iter_bytes(chunk_size=4096),
                        line_type=extract_type_arg(cast_to, 0),
                        http_response=self.http_response,
                    ),
                )

            if issubclass(origin, AsyncJSONLDecoder):
                return cast(
                    R,
                    cast("type[AsyncJSONLDecoder[Any]]", cast_to)(
                        raw_iterator=self.http_response.aiter_bytes(chunk_size=4096),
                        line_type=extract_type_arg(cast_to, 0),
                        http_response=self.http_response,
                    ),
                )

        if self._is_sse_stream:
            if to:
                if not is_stream_class_type(to):
                    raise TypeError(f"Expected custom parse type to be a subclass of {Stream} or {AsyncStream}")

                return cast(
                    _T,
                    to(
                        cast_to=extract_stream_chunk_type(
                            to,
                            failure_message="Expected custom stream type to be passed with a type argument, e.g. Stream[ChunkType]",
                        ),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            if self._stream_cls:
                return cast(
                    R,
                    self._stream_cls(
                        cast_to=extract_stream_chunk_type(self._stream_cls),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            stream_cls = cast("type[Stream[Any]] | type[AsyncStream[Any]] | None", self._client._default_stream_cls)
            if stream_cls is None:
                raise MissingStreamClassError()

            return cast(
                R,
                stream_cls(
                    cast_to=self._cast_to,
                    response=self.http_response,
                    client=cast(Any, self._client),
                ),
            )

        # unwrap `Annotated[T, ...]` -> `T`
        if is_annotated_type(cast_to):
            cast_to = extract_type_arg(cast_to, 0)

        if cast_to is NoneType:
            return cast(R, None)

        response = self.http_response
        if cast_to == str:
            return cast(R, response.text)

        if cast_to == bytes:
            return cast(R, response.content)

        if cast_to == int:
            return cast(R, int(response.text))

        if cast_to == float:
            return cast(R, float(response.text))

        if cast_to == bool:
            return cast(R, response.text.lower() == "true")

        # handle the legacy binary response case
        if inspect.isclass(cast_to) and cast_to.__name__ == "HttpxBinaryResponseContent":
            return cast(R, cast_to(response))  # type: ignore

        if origin == APIResponse:
            raise RuntimeError("Unexpected state - cast_to is `APIResponse`")

        if inspect.isclass(origin) and issubclass(origin, httpx.Response):
            # Because of the invariance of our ResponseT TypeVar, users can subclass httpx.Response
            # and pass that class to our request functions. We cannot change the variance to be either
            # covariant or contravariant as that makes our usage of ResponseT illegal. We could construct
            # the response class ourselves but that is something that should be supported directly in httpx
            # as it would be easy to incorrectly construct the Response object due to the multitude of arguments.
            if cast_to != httpx.Response:
                raise ValueError(f"Subclasses of httpx.Response cannot be passed to `cast_to`")
            return cast(R, response)

        if inspect.isclass(origin) and not issubclass(origin, BaseModel) and issubclass(origin, pydantic.BaseModel):
            raise TypeError("Pydantic models must subclass our base model type, e.g. `from anthropic import BaseModel`")

        if (
            cast_to is not object
            and not origin is list
            and not origin is dict
            and not origin is Union
            and not issubclass(origin, BaseModel)
        ):
            raise RuntimeError(
                f"Unsupported type, expected {cast_to} to be a subclass of {BaseModel}, {dict}, {list}, {Union}, {NoneType}, {str} or {httpx.Response}."
            )

        # split is required to handle cases where additional information is included
        # in the response, e.g. application/json; charset=utf-8
        content_type, *_ = response.headers.get("content-type", "*").split(";")
        if content_type != "application/json":
            if is_basemodel(cast_to):
                try:
                    data = response.json()
                except Exception as exc:
                    log.debug("Could not read JSON from response data due to %s - %s", type(exc), exc)
                else:
                    return self._client._process_response_data(
                        data=data,
                        cast_to=cast_to,  # type: ignore
                        response=response,
                    )

            if self._client._strict_response_validation:
                raise APIResponseValidationError(
                    response=response,
                    message=f"Expected Content-Type response header to be `application/json` but received `{content_type}` instead.",
                    body=response.text,
                )

            # If the API responds with content that isn't JSON then we just return
            # the (decoded) text without performing any parsing so that you can still
            # handle the response however you need to.
            return response.text  # type: ignore

        data = response.json()

        return self._client._process_response_data(
            data=data,
            cast_to=cast_to,  # type: ignore
            response=response,
        )


class APIResponse(BaseAPIResponse[R]):
    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("request-id")  # type: ignore[no-any-return]

    @overload
    def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    def parse(self) -> R: ...

    def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from anthropic import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `int`
          - `float`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        if not self._is_sse_stream:
            self.read()

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        self._parsed_by_type[cache_key] = parsed
        return parsed

    def read(self) -> bytes:
        """Read and return the binary response content."""
        try:
            return self.http_response.read()
        except httpx.StreamConsumed as exc:
            # The default error raised by httpx isn't very
            # helpful in our case so we re-raise it with
            # a different error message.
            raise StreamAlreadyConsumed() from exc

    def text(self) -> str:
        """Read and decode the response content into a string."""
        self.read()
        return self.http_response.text

    def json(self) -> object:
        """Read and decode the JSON response content."""
        self.read()
        return self.http_response.json()

    def close(self) -> None:
        """Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.http_response.close()

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        """
        A byte-iterator over the decoded response content.

        This automatically handles gzip, deflate and brotli encoded responses.
        """
        for chunk in self.http_response.iter_bytes(chunk_size):
            yield chunk

    def iter_text(self, chunk_size: int | None = None) -> Iterator[str]:
        """A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        for chunk in self.http_response.iter_text(chunk_size):
            yield chunk

    def iter_lines(self) -> Iterator[str]:
        """Like `iter_text()` but will only yield chunks for each line"""
        for chunk in self.http_response.iter_lines():
            yield chunk


class AsyncAPIResponse(BaseAPIResponse[R]):
    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("request-id")  # type: ignore[no-any-return]

    @overload
    async def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    async def parse(self) -> R: ...

    async def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from anthropic import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        if not self._is_sse_stream:
            await self.read()

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        self._parsed_by_type[cache_key] = parsed
        return parsed

    async def read(self) -> bytes:
        """Read and return the binary response content."""
        try:
            return await self.http_response.aread()
        except httpx.StreamConsumed as exc:
            # the default error raised by httpx isn't very
            # helpful in our case so we re-raise it with
            # a different error message
            raise StreamAlreadyConsumed() from exc

    async def text(self) -> str:
        """Read and decode the response content into a string."""
        await self.read()
        return self.http_response.text

    async def json(self) -> object:
        """Read and decode the JSON response content."""
        await self.read()
        return self.http_response.json()

    async def close(self) -> None:
        """Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.http_response.aclose()

    async def iter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.

        This automatically handles gzip, deflate and brotli encoded responses.
        """
        async for chunk in self.http_response.aiter_bytes(chunk_size):
            yield chunk

    async def iter_text(self, chunk_size: int | None = None) -> AsyncIterator[str]:
        """A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        async for chunk in self.http_response.aiter_text(chunk_size):
            yield chunk

    async def iter_lines(self) -> AsyncIterator[str]:
        """Like `iter_text()` but will only yield chunks for each line"""
        async for chunk in self.http_response.aiter_lines():
            yield chunk


class BinaryAPIResponse(APIResponse[bytes]):
    """Subclass of APIResponse providing helpers for dealing with binary data.

    Note: If you want to stream the response data instead of eagerly reading it
    all at once then you should use `.with_streaming_response` when making
    the API request, e.g. `.with_streaming_response.get_binary_response()`
    """

    def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `.with_streaming_response.get_binary_response()`
        """
        with open(file, mode="wb") as f:
            for data in self.iter_bytes():
                f.write(data)


class AsyncBinaryAPIResponse(AsyncAPIResponse[bytes]):
    """Subclass of APIResponse providing helpers for dealing with binary data.

    Note: If you want to stream the response data instead of eagerly reading it
    all at once then you should use `.with_streaming_response` when making
    the API request, e.g. `.with_streaming_response.get_binary_response()`
    """

    async def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `.with_streaming_response.get_binary_response()`
        """
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.iter_bytes():
                await f.write(data)


class StreamedBinaryAPIResponse(APIResponse[bytes]):
    def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        """Streams the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path
        """
        with open(file, mode="wb") as f:
            for data in self.iter_bytes(chunk_size):
                f.write(data)


class AsyncStreamedBinaryAPIResponse(AsyncAPIResponse[bytes]):
    async def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        """Streams the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path
        """
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.iter_bytes(chunk_size):
                await f.write(data)


class MissingStreamClassError(TypeError):
    def __init__(self) -> None:
        super().__init__(
            "The `stream` argument was set to `True` but the `stream_cls` argument was not given. See `anthropic._streaming` for reference",
        )


class StreamAlreadyConsumed(AnthropicError):
    """
    Attempted to read or stream content, but the content has already
    been streamed.

    This can happen if you use a method like `.iter_lines()` and then attempt
    to read th entire response body afterwards, e.g.

    ```py
    response = await client.post(...)
    async for line in response.iter_lines():
        ...  # do something with `line`

    content = await response.read()
    # ^ error
    ```

    If you want this behaviour you'll need to either manually accumulate the response
    content or call `await response.read()` before iterating over the stream.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream some content, but the content has "
            "already been streamed. "
            "This could be due to attempting to stream the response "
            "content more than once."
            "\n\n"
            "You can fix this by manually accumulating the response content while streaming "
            "or by calling `.read()` before starting to stream."
        )
        super().__init__(message)


class ResponseContextManager(Generic[_APIResponseT]):
    """Context manager for ensuring that a request is not made
    until it is entered and that the response will always be closed
    when the context manager exits
    """

    def __init__(self, request_func: Callable[[], _APIResponseT]) -> None:
        self._request_func = request_func
        self.__response: _APIResponseT | None = None

    def __enter__(self) -> _APIResponseT:
        self.__response = self._request_func()
        return self.__response

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__response is not None:
            self.__response.close()


class AsyncResponseContextManager(Generic[_AsyncAPIResponseT]):
    """Context manager for ensuring that a request is not made
    until it is entered and that the response will always be closed
    when the context manager exits
    """

    def __init__(self, api_request: Awaitable[_AsyncAPIResponseT]) -> None:
        self._api_request = api_request
        self.__response: _AsyncAPIResponseT | None = None

    async def __aenter__(self) -> _AsyncAPIResponseT:
        self.__response = await self._api_request
        return self.__response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__response is not None:
            await self.__response.close()


def to_streamed_response_wrapper(func: Callable[P, R]) -> Callable[P, ResponseContextManager[APIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support streaming and returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseContextManager[APIResponse[R]]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"

        kwargs["extra_headers"] = extra_headers

        make_request = functools.partial(func, *args, **kwargs)

        return ResponseContextManager(cast(Callable[[], APIResponse[R]], make_request))

    return wrapped


def async_to_streamed_response_wrapper(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, AsyncResponseContextManager[AsyncAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support streaming and returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncResponseContextManager[AsyncAPIResponse[R]]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"

        kwargs["extra_headers"] = extra_headers

        make_request = func(*args, **kwargs)

        return AsyncResponseContextManager(cast(Awaitable[AsyncAPIResponse[R]], make_request))

    return wrapped


def to_custom_streamed_response_wrapper(
    func: Callable[P, object],
    response_cls: type[_APIResponseT],
) -> Callable[P, ResponseContextManager[_APIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support streaming and returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseContextManager[_APIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        make_request = functools.partial(func, *args, **kwargs)

        return ResponseContextManager(cast(Callable[[], _APIResponseT], make_request))

    return wrapped


def async_to_custom_streamed_response_wrapper(
    func: Callable[P, Awaitable[object]],
    response_cls: type[_AsyncAPIResponseT],
) -> Callable[P, AsyncResponseContextManager[_AsyncAPIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support streaming and returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncResponseContextManager[_AsyncAPIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        make_request = func(*args, **kwargs)

        return AsyncResponseContextManager(cast(Awaitable[_AsyncAPIResponseT], make_request))

    return wrapped


def to_raw_response_wrapper(func: Callable[P, R]) -> Callable[P, APIResponse[R]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> APIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"

        kwargs["extra_headers"] = extra_headers

        return cast(APIResponse[R], func(*args, **kwargs))

    return wrapped


def async_to_raw_response_wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[AsyncAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"

        kwargs["extra_headers"] = extra_headers

        return cast(AsyncAPIResponse[R], await func(*args, **kwargs))

    return wrapped


def to_custom_raw_response_wrapper(
    func: Callable[P, object],
    response_cls: type[_APIResponseT],
) -> Callable[P, _APIResponseT]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> _APIResponseT:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        return cast(_APIResponseT, func(*args, **kwargs))

    return wrapped


def async_to_custom_raw_response_wrapper(
    func: Callable[P, Awaitable[object]],
    response_cls: type[_AsyncAPIResponseT],
) -> Callable[P, Awaitable[_AsyncAPIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> Awaitable[_AsyncAPIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        return cast(Awaitable[_AsyncAPIResponseT], func(*args, **kwargs))

    return wrapped


def extract_response_type(typ: type[BaseAPIResponse[Any]]) -> type:
    """Given a type like `APIResponse[T]`, returns the generic type variable `T`.

    This also handles the case where a concrete subclass is given, e.g.
    ```py
    class MyResponse(APIResponse[bytes]):
        ...

    extract_response_type(MyResponse) -> bytes
    ```
    """
    return extract_type_var_from_base(
        typ,
        generic_bases=cast("tuple[type, ...]", (BaseAPIResponse, APIResponse, AsyncAPIResponse)),
        index=0,
    )

# === NexusCore/openenv\Lib\site-packages\nltk\sem\chat80.py ===
# Natural Language Toolkit: Chat-80 KB Reader
# See https://www.w3.org/TR/swbp-skos-core-guide/
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
Overview
========

Chat-80 was a natural language system which allowed the user to
interrogate a Prolog knowledge base in the domain of world
geography. It was developed in the early '80s by Warren and Pereira; see
``https://www.aclweb.org/anthology/J82-3002.pdf`` for a description and
``http://www.cis.upenn.edu/~pereira/oldies.html`` for the source
files.

This module contains functions to extract data from the Chat-80
relation files ('the world database'), and convert then into a format
that can be incorporated in the FOL models of
``nltk.sem.evaluate``. The code assumes that the Prolog
input files are available in the NLTK corpora directory.

The Chat-80 World Database consists of the following files::

    world0.pl
    rivers.pl
    cities.pl
    countries.pl
    contain.pl
    borders.pl

This module uses a slightly modified version of ``world0.pl``, in which
a set of Prolog rules have been omitted. The modified file is named
``world1.pl``. Currently, the file ``rivers.pl`` is not read in, since
it uses a list rather than a string in the second field.

Reading Chat-80 Files
=====================

Chat-80 relations are like tables in a relational database. The
relation acts as the name of the table; the first argument acts as the
'primary key'; and subsequent arguments are further fields in the
table. In general, the name of the table provides a label for a unary
predicate whose extension is all the primary keys. For example,
relations in ``cities.pl`` are of the following form::

   'city(athens,greece,1368).'

Here, ``'athens'`` is the key, and will be mapped to a member of the
unary predicate *city*.

The fields in the table are mapped to binary predicates. The first
argument of the predicate is the primary key, while the second
argument is the data in the relevant field. Thus, in the above
example, the third field is mapped to the binary predicate
*population_of*, whose extension is a set of pairs such as
``'(athens, 1368)'``.

An exception to this general framework is required by the relations in
the files ``borders.pl`` and ``contains.pl``. These contain facts of the
following form::

    'borders(albania,greece).'

    'contains0(africa,central_africa).'

We do not want to form a unary concept out the element in
the first field of these records, and we want the label of the binary
relation just to be ``'border'``/``'contain'`` respectively.

In order to drive the extraction process, we use 'relation metadata bundles'
which are Python dictionaries such as the following::

  city = {'label': 'city',
          'closures': [],
          'schema': ['city', 'country', 'population'],
          'filename': 'cities.pl'}

According to this, the file ``city['filename']`` contains a list of
relational tuples (or more accurately, the corresponding strings in
Prolog form) whose predicate symbol is ``city['label']`` and whose
relational schema is ``city['schema']``. The notion of a ``closure`` is
discussed in the next section.

Concepts
========
In order to encapsulate the results of the extraction, a class of
``Concept`` objects is introduced.  A ``Concept`` object has a number of
attributes, in particular a ``prefLabel`` and ``extension``, which make
it easier to inspect the output of the extraction. In addition, the
``extension`` can be further processed: in the case of the ``'border'``
relation, we check that the relation is symmetric, and in the case
of the ``'contain'`` relation, we carry out the transitive
closure. The closure properties associated with a concept is
indicated in the relation metadata, as indicated earlier.

The ``extension`` of a ``Concept`` object is then incorporated into a
``Valuation`` object.

Persistence
===========
The functions ``val_dump`` and ``val_load`` are provided to allow a
valuation to be stored in a persistent database and re-loaded, rather
than having to be re-computed each time.

Individuals and Lexical Items
=============================
As well as deriving relations from the Chat-80 data, we also create a
set of individual constants, one for each entity in the domain. The
individual constants are string-identical to the entities. For
example, given a data item such as ``'zloty'``, we add to the valuation
a pair ``('zloty', 'zloty')``. In order to parse English sentences that
refer to these entities, we also create a lexical item such as the
following for each individual constant::

   PropN[num=sg, sem=<\P.(P zloty)>] -> 'Zloty'

The set of rules is written to the file ``chat_pnames.cfg`` in the
current directory.

"""

import os
import re
import shelve
import sys

import nltk.data

###########################################################################
# Chat-80 relation metadata bundles needed to build the valuation
###########################################################################

borders = {
    "rel_name": "borders",
    "closures": ["symmetric"],
    "schema": ["region", "border"],
    "filename": "borders.pl",
}

contains = {
    "rel_name": "contains0",
    "closures": ["transitive"],
    "schema": ["region", "contain"],
    "filename": "contain.pl",
}

city = {
    "rel_name": "city",
    "closures": [],
    "schema": ["city", "country", "population"],
    "filename": "cities.pl",
}

country = {
    "rel_name": "country",
    "closures": [],
    "schema": [
        "country",
        "region",
        "latitude",
        "longitude",
        "area",
        "population",
        "capital",
        "currency",
    ],
    "filename": "countries.pl",
}

circle_of_lat = {
    "rel_name": "circle_of_latitude",
    "closures": [],
    "schema": ["circle_of_latitude", "degrees"],
    "filename": "world1.pl",
}

circle_of_long = {
    "rel_name": "circle_of_longitude",
    "closures": [],
    "schema": ["circle_of_longitude", "degrees"],
    "filename": "world1.pl",
}

continent = {
    "rel_name": "continent",
    "closures": [],
    "schema": ["continent"],
    "filename": "world1.pl",
}

region = {
    "rel_name": "in_continent",
    "closures": [],
    "schema": ["region", "continent"],
    "filename": "world1.pl",
}

ocean = {
    "rel_name": "ocean",
    "closures": [],
    "schema": ["ocean"],
    "filename": "world1.pl",
}

sea = {"rel_name": "sea", "closures": [], "schema": ["sea"], "filename": "world1.pl"}


items = [
    "borders",
    "contains",
    "city",
    "country",
    "circle_of_lat",
    "circle_of_long",
    "continent",
    "region",
    "ocean",
    "sea",
]
items = tuple(sorted(items))

item_metadata = {
    "borders": borders,
    "contains": contains,
    "city": city,
    "country": country,
    "circle_of_lat": circle_of_lat,
    "circle_of_long": circle_of_long,
    "continent": continent,
    "region": region,
    "ocean": ocean,
    "sea": sea,
}

rels = item_metadata.values()

not_unary = ["borders.pl", "contain.pl"]

###########################################################################


class Concept:
    """
    A Concept class, loosely based on SKOS
    (https://www.w3.org/TR/swbp-skos-core-guide/).
    """

    def __init__(self, prefLabel, arity, altLabels=[], closures=[], extension=set()):
        """
        :param prefLabel: the preferred label for the concept
        :type prefLabel: str
        :param arity: the arity of the concept
        :type arity: int
        :param altLabels: other (related) labels
        :type altLabels: list
        :param closures: closure properties of the extension
            (list items can be ``symmetric``, ``reflexive``, ``transitive``)
        :type closures: list
        :param extension: the extensional value of the concept
        :type extension: set
        """
        self.prefLabel = prefLabel
        self.arity = arity
        self.altLabels = altLabels
        self.closures = closures
        # keep _extension internally as a set
        self._extension = extension
        # public access is via a list (for slicing)
        self.extension = sorted(list(extension))

    def __str__(self):
        # _extension = ''
        # for element in sorted(self.extension):
        # if isinstance(element, tuple):
        # element = '(%s, %s)' % (element)
        # _extension += element + ', '
        # _extension = _extension[:-1]

        return "Label = '{}'\nArity = {}\nExtension = {}".format(
            self.prefLabel,
            self.arity,
            self.extension,
        )

    def __repr__(self):
        return "Concept('%s')" % self.prefLabel

    def augment(self, data):
        """
        Add more data to the ``Concept``'s extension set.

        :param data: a new semantic value
        :type data: string or pair of strings
        :rtype: set

        """
        self._extension.add(data)
        self.extension = sorted(list(self._extension))
        return self._extension

    def _make_graph(self, s):
        """
        Convert a set of pairs into an adjacency linked list encoding of a graph.
        """
        g = {}
        for x, y in s:
            if x in g:
                g[x].append(y)
            else:
                g[x] = [y]
        return g

    def _transclose(self, g):
        """
        Compute the transitive closure of a graph represented as a linked list.
        """
        for x in g:
            for adjacent in g[x]:
                # check that adjacent is a key
                if adjacent in g:
                    for y in g[adjacent]:
                        if y not in g[x]:
                            g[x].append(y)
        return g

    def _make_pairs(self, g):
        """
        Convert an adjacency linked list back into a set of pairs.
        """
        pairs = []
        for node in g:
            for adjacent in g[node]:
                pairs.append((node, adjacent))
        return set(pairs)

    def close(self):
        """
        Close a binary relation in the ``Concept``'s extension set.

        :return: a new extension for the ``Concept`` in which the
                 relation is closed under a given property
        """
        from nltk.sem import is_rel

        assert is_rel(self._extension)
        if "symmetric" in self.closures:
            pairs = []
            for x, y in self._extension:
                pairs.append((y, x))
            sym = set(pairs)
            self._extension = self._extension.union(sym)
        if "transitive" in self.closures:
            all = self._make_graph(self._extension)
            closed = self._transclose(all)
            trans = self._make_pairs(closed)
            self._extension = self._extension.union(trans)
        self.extension = sorted(list(self._extension))


def clause2concepts(filename, rel_name, schema, closures=[]):
    """
    Convert a file of Prolog clauses into a list of ``Concept`` objects.

    :param filename: filename containing the relations
    :type filename: str
    :param rel_name: name of the relation
    :type rel_name: str
    :param schema: the schema used in a set of relational tuples
    :type schema: list
    :param closures: closure properties for the extension of the concept
    :type closures: list
    :return: a list of ``Concept`` objects
    :rtype: list
    """
    concepts = []
    # position of the subject of a binary relation
    subj = 0
    # label of the 'primary key'
    pkey = schema[0]
    # fields other than the primary key
    fields = schema[1:]

    # convert a file into a list of lists
    records = _str2records(filename, rel_name)

    # add a unary concept corresponding to the set of entities
    # in the primary key position
    # relations in 'not_unary' are more like ordinary binary relations
    if not filename in not_unary:
        concepts.append(unary_concept(pkey, subj, records))

    # add a binary concept for each non-key field
    for field in fields:
        obj = schema.index(field)
        concepts.append(binary_concept(field, closures, subj, obj, records))

    return concepts


def cities2table(filename, rel_name, dbname, verbose=False, setup=False):
    """
    Convert a file of Prolog clauses into a database table.

    This is not generic, since it doesn't allow arbitrary
    schemas to be set as a parameter.

    Intended usage::

        cities2table('cities.pl', 'city', 'city.db', verbose=True, setup=True)

    :param filename: filename containing the relations
    :type filename: str
    :param rel_name: name of the relation
    :type rel_name: str
    :param dbname: filename of persistent store
    :type schema: str
    """
    import sqlite3

    records = _str2records(filename, rel_name)
    connection = sqlite3.connect(dbname)
    cur = connection.cursor()
    if setup:
        cur.execute(
            """CREATE TABLE city_table
        (City text, Country text, Population int)"""
        )

    table_name = "city_table"
    for t in records:
        cur.execute("insert into %s values (?,?,?)" % table_name, t)
        if verbose:
            print("inserting values into %s: " % table_name, t)
    connection.commit()
    if verbose:
        print("Committing update to %s" % dbname)
    cur.close()


def sql_query(dbname, query):
    """
    Execute an SQL query over a database.
    :param dbname: filename of persistent store
    :type schema: str
    :param query: SQL query
    :type rel_name: str
    """
    import sqlite3

    try:
        path = nltk.data.find(dbname)
        connection = sqlite3.connect(str(path))
        cur = connection.cursor()
        return cur.execute(query)
    except (ValueError, sqlite3.OperationalError):
        import warnings

        warnings.warn(
            "Make sure the database file %s is installed and uncompressed." % dbname
        )
        raise


def _str2records(filename, rel):
    """
    Read a file into memory and convert each relation clause into a list.
    """
    recs = []
    contents = nltk.data.load("corpora/chat80/%s" % filename, format="text")
    for line in contents.splitlines():
        if line.startswith(rel):
            line = re.sub(rel + r"\(", "", line)
            line = re.sub(r"\)\.$", "", line)
            record = line.split(",")
            recs.append(record)
    return recs


def unary_concept(label, subj, records):
    """
    Make a unary concept out of the primary key in a record.

    A record is a list of entities in some relation, such as
    ``['france', 'paris']``, where ``'france'`` is acting as the primary
    key.

    :param label: the preferred label for the concept
    :type label: string
    :param subj: position in the record of the subject of the predicate
    :type subj: int
    :param records: a list of records
    :type records: list of lists
    :return: ``Concept`` of arity 1
    :rtype: Concept
    """
    c = Concept(label, arity=1, extension=set())
    for record in records:
        c.augment(record[subj])
    return c


def binary_concept(label, closures, subj, obj, records):
    """
    Make a binary concept out of the primary key and another field in a record.

    A record is a list of entities in some relation, such as
    ``['france', 'paris']``, where ``'france'`` is acting as the primary
    key, and ``'paris'`` stands in the ``'capital_of'`` relation to
    ``'france'``.

    More generally, given a record such as ``['a', 'b', 'c']``, where
    label is bound to ``'B'``, and ``obj`` bound to 1, the derived
    binary concept will have label ``'B_of'``, and its extension will
    be a set of pairs such as ``('a', 'b')``.


    :param label: the base part of the preferred label for the concept
    :type label: str
    :param closures: closure properties for the extension of the concept
    :type closures: list
    :param subj: position in the record of the subject of the predicate
    :type subj: int
    :param obj: position in the record of the object of the predicate
    :type obj: int
    :param records: a list of records
    :type records: list of lists
    :return: ``Concept`` of arity 2
    :rtype: Concept
    """
    if not label == "border" and not label == "contain":
        label = label + "_of"
    c = Concept(label, arity=2, closures=closures, extension=set())
    for record in records:
        c.augment((record[subj], record[obj]))
    # close the concept's extension according to the properties in closures
    c.close()
    return c


def process_bundle(rels):
    """
    Given a list of relation metadata bundles, make a corresponding
    dictionary of concepts, indexed by the relation name.

    :param rels: bundle of metadata needed for constructing a concept
    :type rels: list(dict)
    :return: a dictionary of concepts, indexed by the relation name.
    :rtype: dict(str): Concept
    """
    concepts = {}
    for rel in rels:
        rel_name = rel["rel_name"]
        closures = rel["closures"]
        schema = rel["schema"]
        filename = rel["filename"]

        concept_list = clause2concepts(filename, rel_name, schema, closures)
        for c in concept_list:
            label = c.prefLabel
            if label in concepts:
                for data in c.extension:
                    concepts[label].augment(data)
                concepts[label].close()
            else:
                concepts[label] = c
    return concepts


def make_valuation(concepts, read=False, lexicon=False):
    """
    Convert a list of ``Concept`` objects into a list of (label, extension) pairs;
    optionally create a ``Valuation`` object.

    :param concepts: concepts
    :type concepts: list(Concept)
    :param read: if ``True``, ``(symbol, set)`` pairs are read into a ``Valuation``
    :type read: bool
    :rtype: list or Valuation
    """
    vals = []

    for c in concepts:
        vals.append((c.prefLabel, c.extension))
    if lexicon:
        read = True
    if read:
        from nltk.sem import Valuation

        val = Valuation({})
        val.update(vals)
        # add labels for individuals
        val = label_indivs(val, lexicon=lexicon)
        return val
    else:
        return vals


def val_dump(rels, db):
    """
    Make a ``Valuation`` from a list of relation metadata bundles and dump to
    persistent database.

    :param rels: bundle of metadata needed for constructing a concept
    :type rels: list of dict
    :param db: name of file to which data is written.
               The suffix '.db' will be automatically appended.
    :type db: str
    """
    concepts = process_bundle(rels).values()
    valuation = make_valuation(concepts, read=True)
    db_out = shelve.open(db, "n")

    db_out.update(valuation)

    db_out.close()


def val_load(db):
    """
    Load a ``Valuation`` from a persistent database.

    :param db: name of file from which data is read.
               The suffix '.db' should be omitted from the name.
    :type db: str
    """
    dbname = db + ".db"

    if not os.access(dbname, os.R_OK):
        sys.exit("Cannot read file: %s" % dbname)
    else:
        db_in = shelve.open(db)
        from nltk.sem import Valuation

        val = Valuation(db_in)
        #        val.read(db_in.items())
        return val


# def alpha(str):
# """
# Utility to filter out non-alphabetic constants.

#:param str: candidate constant
#:type str: string
#:rtype: bool
# """
# try:
# int(str)
# return False
# except ValueError:
## some unknown values in records are labeled '?'
# if not str == '?':
# return True


def label_indivs(valuation, lexicon=False):
    """
    Assign individual constants to the individuals in the domain of a ``Valuation``.

    Given a valuation with an entry of the form ``{'rel': {'a': True}}``,
    add a new entry ``{'a': 'a'}``.

    :type valuation: Valuation
    :rtype: Valuation
    """
    # collect all the individuals into a domain
    domain = valuation.domain
    # convert the domain into a sorted list of alphabetic terms
    # use the same string as a label
    pairs = [(e, e) for e in domain]
    if lexicon:
        lex = make_lex(domain)
        with open("chat_pnames.cfg", "w") as outfile:
            outfile.writelines(lex)
    # read the pairs into the valuation
    valuation.update(pairs)
    return valuation


def make_lex(symbols):
    """
    Create lexical CFG rules for each individual symbol.

    Given a valuation with an entry of the form ``{'zloty': 'zloty'}``,
    create a lexical rule for the proper name 'Zloty'.

    :param symbols: a list of individual constants in the semantic representation
    :type symbols: sequence -- set(str)
    :rtype: list(str)
    """
    lex = []
    header = """
##################################################################
# Lexical rules automatically generated by running 'chat80.py -x'.
##################################################################

"""
    lex.append(header)
    template = r"PropN[num=sg, sem=<\P.(P %s)>] -> '%s'\n"

    for s in symbols:
        parts = s.split("_")
        caps = [p.capitalize() for p in parts]
        pname = "_".join(caps)
        rule = template % (s, pname)
        lex.append(rule)
    return lex


###########################################################################
# Interface function to emulate other corpus readers
###########################################################################


def concepts(items=items):
    """
    Build a list of concepts corresponding to the relation names in ``items``.

    :param items: names of the Chat-80 relations to extract
    :type items: list(str)
    :return: the ``Concept`` objects which are extracted from the relations
    :rtype: list(Concept)
    """
    if isinstance(items, str):
        items = (items,)

    rels = [item_metadata[r] for r in items]

    concept_map = process_bundle(rels)
    return concept_map.values()


###########################################################################


def main():
    import sys
    from optparse import OptionParser

    description = """
Extract data from the Chat-80 Prolog files and convert them into a
Valuation object for use in the NLTK semantics package.
    """

    opts = OptionParser(description=description)
    opts.set_defaults(verbose=True, lex=False, vocab=False)
    opts.add_option(
        "-s", "--store", dest="outdb", help="store a valuation in DB", metavar="DB"
    )
    opts.add_option(
        "-l",
        "--load",
        dest="indb",
        help="load a stored valuation from DB",
        metavar="DB",
    )
    opts.add_option(
        "-c",
        "--concepts",
        action="store_true",
        help="print concepts instead of a valuation",
    )
    opts.add_option(
        "-r",
        "--relation",
        dest="label",
        help="print concept with label REL (check possible labels with '-v' option)",
        metavar="REL",
    )
    opts.add_option(
        "-q",
        "--quiet",
        action="store_false",
        dest="verbose",
        help="don't print out progress info",
    )
    opts.add_option(
        "-x",
        "--lex",
        action="store_true",
        dest="lex",
        help="write a file of lexical entries for country names, then exit",
    )
    opts.add_option(
        "-v",
        "--vocab",
        action="store_true",
        dest="vocab",
        help="print out the vocabulary of concept labels and their arity, then exit",
    )

    (options, args) = opts.parse_args()
    if options.outdb and options.indb:
        opts.error("Options --store and --load are mutually exclusive")

    if options.outdb:
        # write the valuation to a persistent database
        if options.verbose:
            outdb = options.outdb + ".db"
            print("Dumping a valuation to %s" % outdb)
        val_dump(rels, options.outdb)
        sys.exit(0)
    else:
        # try to read in a valuation from a database
        if options.indb is not None:
            dbname = options.indb + ".db"
            if not os.access(dbname, os.R_OK):
                sys.exit("Cannot read file: %s" % dbname)
            else:
                valuation = val_load(options.indb)
        # we need to create the valuation from scratch
        else:
            # build some concepts
            concept_map = process_bundle(rels)
            concepts = concept_map.values()
            # just print out the vocabulary
            if options.vocab:
                items = sorted((c.arity, c.prefLabel) for c in concepts)
                for arity, label in items:
                    print(label, arity)
                sys.exit(0)
            # show all the concepts
            if options.concepts:
                for c in concepts:
                    print(c)
                    print()
            if options.label:
                print(concept_map[options.label])
                sys.exit(0)
            else:
                # turn the concepts into a Valuation
                if options.lex:
                    if options.verbose:
                        print("Writing out lexical rules")
                    make_valuation(concepts, lexicon=True)
                else:
                    valuation = make_valuation(concepts, read=True)
                    print(valuation)


def sql_demo():
    """
    Print out every row from the 'city.db' database.
    """
    print()
    print("Using SQL to extract rows from 'city.db' RDB.")
    for row in sql_query("corpora/city_database/city.db", "SELECT * FROM city_table"):
        print(row)


if __name__ == "__main__":
    main()
    sql_demo()

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_response.py ===
import asyncio
import collections.abc
import datetime
import enum
import json
import math
import time
import warnings
from concurrent.futures import Executor
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    MutableMapping,
    Optional,
    Union,
    cast,
)

from multidict import CIMultiDict, istr

from . import hdrs, payload
from .abc import AbstractStreamWriter
from .compression_utils import ZLibCompressor
from .helpers import (
    ETAG_ANY,
    QUOTED_ETAG_RE,
    ETag,
    HeadersMixin,
    must_be_empty_body,
    parse_http_date,
    rfc822_formatted_time,
    sentinel,
    should_remove_content_length,
    validate_etag_value,
)
from .http import SERVER_SOFTWARE, HttpVersion10, HttpVersion11
from .payload import Payload
from .typedefs import JSONEncoder, LooseHeaders

REASON_PHRASES = {http_status.value: http_status.phrase for http_status in HTTPStatus}
LARGE_BODY_SIZE = 1024**2

__all__ = ("ContentCoding", "StreamResponse", "Response", "json_response")


if TYPE_CHECKING:
    from .web_request import BaseRequest

    BaseClass = MutableMapping[str, Any]
else:
    BaseClass = collections.abc.MutableMapping


# TODO(py311): Convert to StrEnum for wider use
class ContentCoding(enum.Enum):
    # The content codings that we have support for.
    #
    # Additional registered codings are listed at:
    # https://www.iana.org/assignments/http-parameters/http-parameters.xhtml#content-coding
    deflate = "deflate"
    gzip = "gzip"
    identity = "identity"


CONTENT_CODINGS = {coding.value: coding for coding in ContentCoding}

############################################################
# HTTP Response classes
############################################################


class StreamResponse(BaseClass, HeadersMixin):

    _body: Union[None, bytes, bytearray, Payload]
    _length_check = True
    _body = None
    _keep_alive: Optional[bool] = None
    _chunked: bool = False
    _compression: bool = False
    _compression_strategy: Optional[int] = None
    _compression_force: Optional[ContentCoding] = None
    _req: Optional["BaseRequest"] = None
    _payload_writer: Optional[AbstractStreamWriter] = None
    _eof_sent: bool = False
    _must_be_empty_body: Optional[bool] = None
    _body_length = 0
    _cookies: Optional[SimpleCookie] = None
    _send_headers_immediately = True

    def __init__(
        self,
        *,
        status: int = 200,
        reason: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
        _real_headers: Optional[CIMultiDict[str]] = None,
    ) -> None:
        """Initialize a new stream response object.

        _real_headers is an internal parameter used to pass a pre-populated
        headers object. It is used by the `Response` class to avoid copying
        the headers when creating a new response object. It is not intended
        to be used by external code.
        """
        self._state: Dict[str, Any] = {}

        if _real_headers is not None:
            self._headers = _real_headers
        elif headers is not None:
            self._headers: CIMultiDict[str] = CIMultiDict(headers)
        else:
            self._headers = CIMultiDict()

        self._set_status(status, reason)

    @property
    def prepared(self) -> bool:
        return self._eof_sent or self._payload_writer is not None

    @property
    def task(self) -> "Optional[asyncio.Task[None]]":
        if self._req:
            return self._req.task
        else:
            return None

    @property
    def status(self) -> int:
        return self._status

    @property
    def chunked(self) -> bool:
        return self._chunked

    @property
    def compression(self) -> bool:
        return self._compression

    @property
    def reason(self) -> str:
        return self._reason

    def set_status(
        self,
        status: int,
        reason: Optional[str] = None,
    ) -> None:
        assert (
            not self.prepared
        ), "Cannot change the response status code after the headers have been sent"
        self._set_status(status, reason)

    def _set_status(self, status: int, reason: Optional[str]) -> None:
        self._status = int(status)
        if reason is None:
            reason = REASON_PHRASES.get(self._status, "")
        elif "\n" in reason:
            raise ValueError("Reason cannot contain \\n")
        self._reason = reason

    @property
    def keep_alive(self) -> Optional[bool]:
        return self._keep_alive

    def force_close(self) -> None:
        self._keep_alive = False

    @property
    def body_length(self) -> int:
        return self._body_length

    @property
    def output_length(self) -> int:
        warnings.warn("output_length is deprecated", DeprecationWarning)
        assert self._payload_writer
        return self._payload_writer.buffer_size

    def enable_chunked_encoding(self, chunk_size: Optional[int] = None) -> None:
        """Enables automatic chunked transfer encoding."""
        if hdrs.CONTENT_LENGTH in self._headers:
            raise RuntimeError(
                "You can't enable chunked encoding when a content length is set"
            )
        if chunk_size is not None:
            warnings.warn("Chunk size is deprecated #1615", DeprecationWarning)
        self._chunked = True

    def enable_compression(
        self,
        force: Optional[Union[bool, ContentCoding]] = None,
        strategy: Optional[int] = None,
    ) -> None:
        """Enables response compression encoding."""
        # Backwards compatibility for when force was a bool <0.17.
        if isinstance(force, bool):
            force = ContentCoding.deflate if force else ContentCoding.identity
            warnings.warn(
                "Using boolean for force is deprecated #3318", DeprecationWarning
            )
        elif force is not None:
            assert isinstance(
                force, ContentCoding
            ), "force should one of None, bool or ContentEncoding"

        self._compression = True
        self._compression_force = force
        self._compression_strategy = strategy

    @property
    def headers(self) -> "CIMultiDict[str]":
        return self._headers

    @property
    def cookies(self) -> SimpleCookie:
        if self._cookies is None:
            self._cookies = SimpleCookie()
        return self._cookies

    def set_cookie(
        self,
        name: str,
        value: str,
        *,
        expires: Optional[str] = None,
        domain: Optional[str] = None,
        max_age: Optional[Union[int, str]] = None,
        path: str = "/",
        secure: Optional[bool] = None,
        httponly: Optional[bool] = None,
        version: Optional[str] = None,
        samesite: Optional[str] = None,
        partitioned: Optional[bool] = None,
    ) -> None:
        """Set or update response cookie.

        Sets new cookie or updates existent with new value.
        Also updates only those params which are not None.
        """
        if self._cookies is None:
            self._cookies = SimpleCookie()

        self._cookies[name] = value
        c = self._cookies[name]

        if expires is not None:
            c["expires"] = expires
        elif c.get("expires") == "Thu, 01 Jan 1970 00:00:00 GMT":
            del c["expires"]

        if domain is not None:
            c["domain"] = domain

        if max_age is not None:
            c["max-age"] = str(max_age)
        elif "max-age" in c:
            del c["max-age"]

        c["path"] = path

        if secure is not None:
            c["secure"] = secure
        if httponly is not None:
            c["httponly"] = httponly
        if version is not None:
            c["version"] = version
        if samesite is not None:
            c["samesite"] = samesite

        if partitioned is not None:
            c["partitioned"] = partitioned

    def del_cookie(
        self,
        name: str,
        *,
        domain: Optional[str] = None,
        path: str = "/",
        secure: Optional[bool] = None,
        httponly: Optional[bool] = None,
        samesite: Optional[str] = None,
    ) -> None:
        """Delete cookie.

        Creates new empty expired cookie.
        """
        # TODO: do we need domain/path here?
        if self._cookies is not None:
            self._cookies.pop(name, None)
        self.set_cookie(
            name,
            "",
            max_age=0,
            expires="Thu, 01 Jan 1970 00:00:00 GMT",
            domain=domain,
            path=path,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    @property
    def content_length(self) -> Optional[int]:
        # Just a placeholder for adding setter
        return super().content_length

    @content_length.setter
    def content_length(self, value: Optional[int]) -> None:
        if value is not None:
            value = int(value)
            if self._chunked:
                raise RuntimeError(
                    "You can't set content length when chunked encoding is enable"
                )
            self._headers[hdrs.CONTENT_LENGTH] = str(value)
        else:
            self._headers.pop(hdrs.CONTENT_LENGTH, None)

    @property
    def content_type(self) -> str:
        # Just a placeholder for adding setter
        return super().content_type

    @content_type.setter
    def content_type(self, value: str) -> None:
        self.content_type  # read header values if needed
        self._content_type = str(value)
        self._generate_content_type_header()

    @property
    def charset(self) -> Optional[str]:
        # Just a placeholder for adding setter
        return super().charset

    @charset.setter
    def charset(self, value: Optional[str]) -> None:
        ctype = self.content_type  # read header values if needed
        if ctype == "application/octet-stream":
            raise RuntimeError(
                "Setting charset for application/octet-stream "
                "doesn't make sense, setup content_type first"
            )
        assert self._content_dict is not None
        if value is None:
            self._content_dict.pop("charset", None)
        else:
            self._content_dict["charset"] = str(value).lower()
        self._generate_content_type_header()

    @property
    def last_modified(self) -> Optional[datetime.datetime]:
        """The value of Last-Modified HTTP header, or None.

        This header is represented as a `datetime` object.
        """
        return parse_http_date(self._headers.get(hdrs.LAST_MODIFIED))

    @last_modified.setter
    def last_modified(
        self, value: Optional[Union[int, float, datetime.datetime, str]]
    ) -> None:
        if value is None:
            self._headers.pop(hdrs.LAST_MODIFIED, None)
        elif isinstance(value, (int, float)):
            self._headers[hdrs.LAST_MODIFIED] = time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(math.ceil(value))
            )
        elif isinstance(value, datetime.datetime):
            self._headers[hdrs.LAST_MODIFIED] = time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", value.utctimetuple()
            )
        elif isinstance(value, str):
            self._headers[hdrs.LAST_MODIFIED] = value
        else:
            msg = f"Unsupported type for last_modified: {type(value).__name__}"
            raise TypeError(msg)

    @property
    def etag(self) -> Optional[ETag]:
        quoted_value = self._headers.get(hdrs.ETAG)
        if not quoted_value:
            return None
        elif quoted_value == ETAG_ANY:
            return ETag(value=ETAG_ANY)
        match = QUOTED_ETAG_RE.fullmatch(quoted_value)
        if not match:
            return None
        is_weak, value = match.group(1, 2)
        return ETag(
            is_weak=bool(is_weak),
            value=value,
        )

    @etag.setter
    def etag(self, value: Optional[Union[ETag, str]]) -> None:
        if value is None:
            self._headers.pop(hdrs.ETAG, None)
        elif (isinstance(value, str) and value == ETAG_ANY) or (
            isinstance(value, ETag) and value.value == ETAG_ANY
        ):
            self._headers[hdrs.ETAG] = ETAG_ANY
        elif isinstance(value, str):
            validate_etag_value(value)
            self._headers[hdrs.ETAG] = f'"{value}"'
        elif isinstance(value, ETag) and isinstance(value.value, str):
            validate_etag_value(value.value)
            hdr_value = f'W/"{value.value}"' if value.is_weak else f'"{value.value}"'
            self._headers[hdrs.ETAG] = hdr_value
        else:
            raise ValueError(
                f"Unsupported etag type: {type(value)}. "
                f"etag must be str, ETag or None"
            )

    def _generate_content_type_header(
        self, CONTENT_TYPE: istr = hdrs.CONTENT_TYPE
    ) -> None:
        assert self._content_dict is not None
        assert self._content_type is not None
        params = "; ".join(f"{k}={v}" for k, v in self._content_dict.items())
        if params:
            ctype = self._content_type + "; " + params
        else:
            ctype = self._content_type
        self._headers[CONTENT_TYPE] = ctype

    async def _do_start_compression(self, coding: ContentCoding) -> None:
        if coding is ContentCoding.identity:
            return
        assert self._payload_writer is not None
        self._headers[hdrs.CONTENT_ENCODING] = coding.value
        self._payload_writer.enable_compression(
            coding.value, self._compression_strategy
        )
        # Compressed payload may have different content length,
        # remove the header
        self._headers.popall(hdrs.CONTENT_LENGTH, None)

    async def _start_compression(self, request: "BaseRequest") -> None:
        if self._compression_force:
            await self._do_start_compression(self._compression_force)
            return
        # Encoding comparisons should be case-insensitive
        # https://www.rfc-editor.org/rfc/rfc9110#section-8.4.1
        accept_encoding = request.headers.get(hdrs.ACCEPT_ENCODING, "").lower()
        for value, coding in CONTENT_CODINGS.items():
            if value in accept_encoding:
                await self._do_start_compression(coding)
                return

    async def prepare(self, request: "BaseRequest") -> Optional[AbstractStreamWriter]:
        if self._eof_sent:
            return None
        if self._payload_writer is not None:
            return self._payload_writer
        self._must_be_empty_body = must_be_empty_body(request.method, self.status)
        return await self._start(request)

    async def _start(self, request: "BaseRequest") -> AbstractStreamWriter:
        self._req = request
        writer = self._payload_writer = request._payload_writer

        await self._prepare_headers()
        await request._prepare_hook(self)
        await self._write_headers()

        return writer

    async def _prepare_headers(self) -> None:
        request = self._req
        assert request is not None
        writer = self._payload_writer
        assert writer is not None
        keep_alive = self._keep_alive
        if keep_alive is None:
            keep_alive = request.keep_alive
        self._keep_alive = keep_alive

        version = request.version

        headers = self._headers
        if self._cookies:
            for cookie in self._cookies.values():
                value = cookie.output(header="")[1:]
                headers.add(hdrs.SET_COOKIE, value)

        if self._compression:
            await self._start_compression(request)

        if self._chunked:
            if version != HttpVersion11:
                raise RuntimeError(
                    "Using chunked encoding is forbidden "
                    "for HTTP/{0.major}.{0.minor}".format(request.version)
                )
            if not self._must_be_empty_body:
                writer.enable_chunking()
                headers[hdrs.TRANSFER_ENCODING] = "chunked"
        elif self._length_check:  # Disabled for WebSockets
            writer.length = self.content_length
            if writer.length is None:
                if version >= HttpVersion11:
                    if not self._must_be_empty_body:
                        writer.enable_chunking()
                        headers[hdrs.TRANSFER_ENCODING] = "chunked"
                elif not self._must_be_empty_body:
                    keep_alive = False

        # HTTP 1.1: https://tools.ietf.org/html/rfc7230#section-3.3.2
        # HTTP 1.0: https://tools.ietf.org/html/rfc1945#section-10.4
        if self._must_be_empty_body:
            if hdrs.CONTENT_LENGTH in headers and should_remove_content_length(
                request.method, self.status
            ):
                del headers[hdrs.CONTENT_LENGTH]
            # https://datatracker.ietf.org/doc/html/rfc9112#section-6.1-10
            # https://datatracker.ietf.org/doc/html/rfc9112#section-6.1-13
            if hdrs.TRANSFER_ENCODING in headers:
                del headers[hdrs.TRANSFER_ENCODING]
        elif (writer.length if self._length_check else self.content_length) != 0:
            # https://www.rfc-editor.org/rfc/rfc9110#section-8.3-5
            headers.setdefault(hdrs.CONTENT_TYPE, "application/octet-stream")
        headers.setdefault(hdrs.DATE, rfc822_formatted_time())
        headers.setdefault(hdrs.SERVER, SERVER_SOFTWARE)

        # connection header
        if hdrs.CONNECTION not in headers:
            if keep_alive:
                if version == HttpVersion10:
                    headers[hdrs.CONNECTION] = "keep-alive"
            elif version == HttpVersion11:
                headers[hdrs.CONNECTION] = "close"

    async def _write_headers(self) -> None:
        request = self._req
        assert request is not None
        writer = self._payload_writer
        assert writer is not None
        # status line
        version = request.version
        status_line = f"HTTP/{version[0]}.{version[1]} {self._status} {self._reason}"
        await writer.write_headers(status_line, self._headers)
        # Send headers immediately if not opted into buffering
        if self._send_headers_immediately:
            writer.send_headers()

    async def write(self, data: Union[bytes, bytearray, memoryview]) -> None:
        assert isinstance(
            data, (bytes, bytearray, memoryview)
        ), "data argument must be byte-ish (%r)" % type(data)

        if self._eof_sent:
            raise RuntimeError("Cannot call write() after write_eof()")
        if self._payload_writer is None:
            raise RuntimeError("Cannot call write() before prepare()")

        await self._payload_writer.write(data)

    async def drain(self) -> None:
        assert not self._eof_sent, "EOF has already been sent"
        assert self._payload_writer is not None, "Response has not been started"
        warnings.warn(
            "drain method is deprecated, use await resp.write()",
            DeprecationWarning,
            stacklevel=2,
        )
        await self._payload_writer.drain()

    async def write_eof(self, data: bytes = b"") -> None:
        assert isinstance(
            data, (bytes, bytearray, memoryview)
        ), "data argument must be byte-ish (%r)" % type(data)

        if self._eof_sent:
            return

        assert self._payload_writer is not None, "Response has not been started"

        await self._payload_writer.write_eof(data)
        self._eof_sent = True
        self._req = None
        self._body_length = self._payload_writer.output_size
        self._payload_writer = None

    def __repr__(self) -> str:
        if self._eof_sent:
            info = "eof"
        elif self.prepared:
            assert self._req is not None
            info = f"{self._req.method} {self._req.path} "
        else:
            info = "not prepared"
        return f"<{self.__class__.__name__} {self.reason} {info}>"

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __delitem__(self, key: str) -> None:
        del self._state[key]

    def __len__(self) -> int:
        return len(self._state)

    def __iter__(self) -> Iterator[str]:
        return iter(self._state)

    def __hash__(self) -> int:
        return hash(id(self))

    def __eq__(self, other: object) -> bool:
        return self is other

    def __bool__(self) -> bool:
        return True


class Response(StreamResponse):

    _compressed_body: Optional[bytes] = None
    _send_headers_immediately = False

    def __init__(
        self,
        *,
        body: Any = None,
        status: int = 200,
        reason: Optional[str] = None,
        text: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
        content_type: Optional[str] = None,
        charset: Optional[str] = None,
        zlib_executor_size: Optional[int] = None,
        zlib_executor: Optional[Executor] = None,
    ) -> None:
        if body is not None and text is not None:
            raise ValueError("body and text are not allowed together")

        if headers is None:
            real_headers: CIMultiDict[str] = CIMultiDict()
        else:
            real_headers = CIMultiDict(headers)

        if content_type is not None and "charset" in content_type:
            raise ValueError("charset must not be in content_type argument")

        if text is not None:
            if hdrs.CONTENT_TYPE in real_headers:
                if content_type or charset:
                    raise ValueError(
                        "passing both Content-Type header and "
                        "content_type or charset params "
                        "is forbidden"
                    )
            else:
                # fast path for filling headers
                if not isinstance(text, str):
                    raise TypeError("text argument must be str (%r)" % type(text))
                if content_type is None:
                    content_type = "text/plain"
                if charset is None:
                    charset = "utf-8"
                real_headers[hdrs.CONTENT_TYPE] = content_type + "; charset=" + charset
                body = text.encode(charset)
                text = None
        elif hdrs.CONTENT_TYPE in real_headers:
            if content_type is not None or charset is not None:
                raise ValueError(
                    "passing both Content-Type header and "
                    "content_type or charset params "
                    "is forbidden"
                )
        elif content_type is not None:
            if charset is not None:
                content_type += "; charset=" + charset
            real_headers[hdrs.CONTENT_TYPE] = content_type

        super().__init__(status=status, reason=reason, _real_headers=real_headers)

        if text is not None:
            self.text = text
        else:
            self.body = body

        self._zlib_executor_size = zlib_executor_size
        self._zlib_executor = zlib_executor

    @property
    def body(self) -> Optional[Union[bytes, Payload]]:
        return self._body

    @body.setter
    def body(self, body: Any) -> None:
        if body is None:
            self._body = None
        elif isinstance(body, (bytes, bytearray)):
            self._body = body
        else:
            try:
                self._body = body = payload.PAYLOAD_REGISTRY.get(body)
            except payload.LookupError:
                raise ValueError("Unsupported body type %r" % type(body))

            headers = self._headers

            # set content-type
            if hdrs.CONTENT_TYPE not in headers:
                headers[hdrs.CONTENT_TYPE] = body.content_type

            # copy payload headers
            if body.headers:
                for key, value in body.headers.items():
                    if key not in headers:
                        headers[key] = value

        self._compressed_body = None

    @property
    def text(self) -> Optional[str]:
        if self._body is None:
            return None
        # Note: When _body is a Payload (e.g. FilePayload), this may do blocking I/O
        # This is generally safe as most common payloads (BytesPayload, StringPayload)
        # don't do blocking I/O, but be careful with file-based payloads
        return self._body.decode(self.charset or "utf-8")

    @text.setter
    def text(self, text: str) -> None:
        assert text is None or isinstance(
            text, str
        ), "text argument must be str (%r)" % type(text)

        if self.content_type == "application/octet-stream":
            self.content_type = "text/plain"
        if self.charset is None:
            self.charset = "utf-8"

        self._body = text.encode(self.charset)
        self._compressed_body = None

    @property
    def content_length(self) -> Optional[int]:
        if self._chunked:
            return None

        if hdrs.CONTENT_LENGTH in self._headers:
            return int(self._headers[hdrs.CONTENT_LENGTH])

        if self._compressed_body is not None:
            # Return length of the compressed body
            return len(self._compressed_body)
        elif isinstance(self._body, Payload):
            # A payload without content length, or a compressed payload
            return None
        elif self._body is not None:
            return len(self._body)
        else:
            return 0

    @content_length.setter
    def content_length(self, value: Optional[int]) -> None:
        raise RuntimeError("Content length is set automatically")

    async def write_eof(self, data: bytes = b"") -> None:
        if self._eof_sent:
            return
        if self._compressed_body is None:
            body: Optional[Union[bytes, Payload]] = self._body
        else:
            body = self._compressed_body
        assert not data, f"data arg is not supported, got {data!r}"
        assert self._req is not None
        assert self._payload_writer is not None
        if body is None or self._must_be_empty_body:
            await super().write_eof()
        elif isinstance(self._body, Payload):
            await self._body.write(self._payload_writer)
            await self._body.close()
            await super().write_eof()
        else:
            await super().write_eof(cast(bytes, body))

    async def _start(self, request: "BaseRequest") -> AbstractStreamWriter:
        if hdrs.CONTENT_LENGTH in self._headers:
            if should_remove_content_length(request.method, self.status):
                del self._headers[hdrs.CONTENT_LENGTH]
        elif not self._chunked:
            if isinstance(self._body, Payload):
                if self._body.size is not None:
                    self._headers[hdrs.CONTENT_LENGTH] = str(self._body.size)
            else:
                body_len = len(self._body) if self._body else "0"
                # https://www.rfc-editor.org/rfc/rfc9110.html#section-8.6-7
                if body_len != "0" or (
                    self.status != 304 and request.method not in hdrs.METH_HEAD_ALL
                ):
                    self._headers[hdrs.CONTENT_LENGTH] = str(body_len)

        return await super()._start(request)

    async def _do_start_compression(self, coding: ContentCoding) -> None:
        if self._chunked or isinstance(self._body, Payload):
            return await super()._do_start_compression(coding)
        if coding is ContentCoding.identity:
            return
        # Instead of using _payload_writer.enable_compression,
        # compress the whole body
        compressor = ZLibCompressor(
            encoding=coding.value,
            max_sync_chunk_size=self._zlib_executor_size,
            executor=self._zlib_executor,
        )
        assert self._body is not None
        if self._zlib_executor_size is None and len(self._body) > LARGE_BODY_SIZE:
            warnings.warn(
                "Synchronous compression of large response bodies "
                f"({len(self._body)} bytes) might block the async event loop. "
                "Consider providing a custom value to zlib_executor_size/"
                "zlib_executor response properties or disabling compression on it."
            )
        self._compressed_body = (
            await compressor.compress(self._body) + compressor.flush()
        )
        self._headers[hdrs.CONTENT_ENCODING] = coding.value
        self._headers[hdrs.CONTENT_LENGTH] = str(len(self._compressed_body))


def json_response(
    data: Any = sentinel,
    *,
    text: Optional[str] = None,
    body: Optional[bytes] = None,
    status: int = 200,
    reason: Optional[str] = None,
    headers: Optional[LooseHeaders] = None,
    content_type: str = "application/json",
    dumps: JSONEncoder = json.dumps,
) -> Response:
    if data is not sentinel:
        if text or body:
            raise ValueError("only one of data, text, or body should be specified")
        else:
            text = dumps(data)
    return Response(
        text=text,
        body=body,
        status=status,
        reason=reason,
        headers=headers,
        content_type=content_type,
    )

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\osm.py ===
"""Implementation of magic functions for interaction with the OS.

Note: this module is named 'osm' instead of 'os' to avoid a collision with the
builtin.
"""
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import io
import os
import pathlib
import re
import sys
from pprint import pformat

from IPython.core import magic_arguments
from IPython.core import oinspect
from IPython.core import page
from IPython.core.alias import AliasError, Alias
from IPython.core.error import UsageError
from IPython.core.magic import  (
    Magics, compress_dhist, magics_class, line_magic, cell_magic, line_cell_magic
)
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.openpy import source_to_unicode
from IPython.utils.process import abbrev_cwd
from IPython.utils.terminal import set_term_title
from traitlets import Bool
from warnings import warn


@magics_class
class OSMagics(Magics):
    """Magics to interact with the underlying OS (shell-type functionality).
    """

    cd_force_quiet = Bool(False,
        help="Force %cd magic to be quiet even if -q is not passed."
    ).tag(config=True)

    def __init__(self, shell=None, **kwargs):

        # Now define isexec in a cross platform manner.
        self.is_posix = False
        self.execre = None
        if os.name == 'posix':
            self.is_posix = True
        else:
            try:
                winext = os.environ['pathext'].replace(';','|').replace('.','')
            except KeyError:
                winext = 'exe|com|bat|py'
            try:
                self.execre = re.compile(r'(.*)\.(%s)$' % winext,re.IGNORECASE)
            except re.error:
                warn("Seems like your pathext environmental "
                     "variable is malformed. Please check it to "
                     "enable a proper handle of file extensions "
                     "managed for your system")
                winext = 'exe|com|bat|py'
                self.execre = re.compile(r'(.*)\.(%s)$' % winext,re.IGNORECASE)

        # call up the chain
        super().__init__(shell=shell, **kwargs)


    def _isexec_POSIX(self, file):
        """
        Test for executable on a POSIX system
        """
        if os.access(file.path, os.X_OK):
            # will fail on maxOS if access is not X_OK
            return file.is_file()
        return False



    def _isexec_WIN(self, file):
        """
        Test for executable file on non POSIX system
        """
        return file.is_file() and self.execre.match(file.name) is not None

    def isexec(self, file):
        """
        Test for executable file on non POSIX system
        """
        if self.is_posix:
            return self._isexec_POSIX(file)
        else:
            return self._isexec_WIN(file)


    @skip_doctest
    @line_magic
    def alias(self, parameter_s=''):
        """Define an alias for a system command.

        '%alias alias_name cmd' defines 'alias_name' as an alias for 'cmd'

        Then, typing 'alias_name params' will execute the system command 'cmd
        params' (from your underlying operating system).

        Aliases have lower precedence than magic functions and Python normal
        variables, so if 'foo' is both a Python variable and an alias, the
        alias can not be executed until 'del foo' removes the Python variable.

        You can use the %l specifier in an alias definition to represent the
        whole line when the alias is called.  For example::

          In [2]: alias bracket echo "Input in brackets: <%l>"
          In [3]: bracket hello world
          Input in brackets: <hello world>

        You can also define aliases with parameters using %s specifiers (one
        per parameter)::

          In [1]: alias parts echo first %s second %s
          In [2]: %parts A B
          first A second B
          In [3]: %parts A
          Incorrect number of arguments: 2 expected.
          parts is an alias to: 'echo first %s second %s'

        Note that %l and %s are mutually exclusive.  You can only use one or
        the other in your aliases.

        Aliases expand Python variables just like system calls using ! or !!
        do: all expressions prefixed with '$' get expanded.  For details of
        the semantic rules, see PEP-215:
        https://peps.python.org/pep-0215/.  This is the library used by
        IPython for variable expansion.  If you want to access a true shell
        variable, an extra $ is necessary to prevent its expansion by
        IPython::

          In [6]: alias show echo
          In [7]: PATH='A Python string'
          In [8]: show $PATH
          A Python string
          In [9]: show $$PATH
          /usr/local/lf9560/bin:/usr/local/intel/compiler70/ia32/bin:...

        You can use the alias facility to access all of $PATH.  See the %rehashx
        function, which automatically creates aliases for the contents of your
        $PATH.

        If called with no parameters, %alias prints the current alias table
        for your system.  For posix systems, the default aliases are 'cat',
        'cp', 'mv', 'rm', 'rmdir', and 'mkdir', and other platform-specific
        aliases are added.  For windows-based systems, the default aliases are
        'copy', 'ddir', 'echo', 'ls', 'ldir', 'mkdir', 'ren', and 'rmdir'.

        You can see the definition of alias by adding a question mark in the
        end::

          In [1]: cat?
          Repr: <alias cat for 'cat'>"""

        par = parameter_s.strip()
        if not par:
            aliases = sorted(self.shell.alias_manager.aliases)
            # stored = self.shell.db.get('stored_aliases', {} )
            # for k, v in stored:
            #     atab.append(k, v[0])

            print("Total number of aliases:", len(aliases))
            sys.stdout.flush()
            return aliases

        # Now try to define a new one
        try:
            alias,cmd = par.split(None, 1)
        except TypeError:
            print(oinspect.getdoc(self.alias))
            return
        
        try:
            self.shell.alias_manager.define_alias(alias, cmd)
        except AliasError as e:
            print(e)
    # end magic_alias

    @line_magic
    def unalias(self, parameter_s=''):
        """Remove an alias"""

        aname = parameter_s.strip()
        try:
            self.shell.alias_manager.undefine_alias(aname)
        except ValueError as e:
            print(e)
            return
        
        stored = self.shell.db.get('stored_aliases', {} )
        if aname in stored:
            print("Removing %stored alias",aname)
            del stored[aname]
            self.shell.db['stored_aliases'] = stored

    @line_magic
    def rehashx(self, parameter_s=''):
        """Update the alias table with all executable files in $PATH.

        rehashx explicitly checks that every entry in $PATH is a file
        with execute access (os.X_OK).

        Under Windows, it checks executability as a match against a
        '|'-separated string of extensions, stored in the IPython config
        variable win_exec_ext.  This defaults to 'exe|com|bat'.

        This function also resets the root module cache of module completer,
        used on slow filesystems.
        """
        from IPython.core.alias import InvalidAliasError

        # for the benefit of module completer in ipy_completers.py
        del self.shell.db['rootmodules_cache']

        path = [os.path.abspath(os.path.expanduser(p)) for p in
            os.environ.get('PATH','').split(os.pathsep)]

        syscmdlist = []
        savedir = os.getcwd()

        # Now walk the paths looking for executables to alias.
        try:
            # write the whole loop for posix/Windows so we don't have an if in
            # the innermost part
            if self.is_posix:
                for pdir in path:
                    try:
                        os.chdir(pdir)
                    except OSError:
                        continue

                    # for python 3.6+ rewrite to: with os.scandir(pdir) as dirlist:
                    dirlist = os.scandir(path=pdir)
                    for ff in dirlist:
                        if self.isexec(ff):
                            fname = ff.name
                            try:
                                # Removes dots from the name since ipython
                                # will assume names with dots to be python.
                                if not self.shell.alias_manager.is_alias(fname):
                                    self.shell.alias_manager.define_alias(
                                        fname.replace('.',''), fname)
                            except InvalidAliasError:
                                pass
                            else:
                                syscmdlist.append(fname)
            else:
                no_alias = Alias.blacklist
                for pdir in path:
                    try:
                        os.chdir(pdir)
                    except OSError:
                        continue

                    # for python 3.6+ rewrite to: with os.scandir(pdir) as dirlist:
                    dirlist = os.scandir(pdir)
                    for ff in dirlist:
                        fname = ff.name
                        base, ext = os.path.splitext(fname)
                        if self.isexec(ff) and base.lower() not in no_alias:
                            if ext.lower() == '.exe':
                                fname = base
                                try:
                                    # Removes dots from the name since ipython
                                    # will assume names with dots to be python.
                                    self.shell.alias_manager.define_alias(
                                        base.lower().replace('.',''), fname)
                                except InvalidAliasError:
                                    pass
                                syscmdlist.append(fname)

            self.shell.db['syscmdlist'] = syscmdlist
        finally:
            os.chdir(savedir)

    @skip_doctest
    @line_magic
    def pwd(self, parameter_s=''):
        """Return the current working directory path.

        Examples
        --------
        ::

          In [9]: pwd
          Out[9]: '/home/tsuser/sprint/ipython'
        """
        try:
            return os.getcwd()
        except FileNotFoundError as e:
            raise UsageError("CWD no longer exists - please use %cd to change directory.") from e

    @skip_doctest
    @line_magic
    def cd(self, parameter_s=''):
        """Change the current working directory.

        This command automatically maintains an internal list of directories
        you visit during your IPython session, in the variable ``_dh``. The
        command :magic:`%dhist` shows this history nicely formatted. You can
        also do ``cd -<tab>`` to see directory history conveniently.
        Usage:

          - ``cd 'dir'``: changes to directory 'dir'.
          - ``cd -``: changes to the last visited directory.
          - ``cd -<n>``: changes to the n-th directory in the directory history.
          - ``cd --foo``: change to directory that matches 'foo' in history
          - ``cd -b <bookmark_name>``: jump to a bookmark set by %bookmark
          - Hitting a tab key after ``cd -b`` allows you to tab-complete
            bookmark names.

          .. note::
            ``cd <bookmark_name>`` is enough if there is no directory
            ``<bookmark_name>``, but a bookmark with the name exists.

        Options:

        -q               Be quiet. Do not print the working directory after the
                          cd command is executed. By default IPython's cd
                          command does print this directory, since the default
                          prompts do not display path information.

        .. note::
           Note that ``!cd`` doesn't work for this purpose because the shell
           where ``!command`` runs is immediately discarded after executing
           'command'.

        Examples
        --------
        ::

          In [10]: cd parent/child
          /home/tsuser/parent/child
        """

        try:
            oldcwd = os.getcwd()
        except FileNotFoundError:
            # Happens if the CWD has been deleted.
            oldcwd = None

        numcd = re.match(r'(-)(\d+)$',parameter_s)
        # jump in directory history by number
        if numcd:
            nn = int(numcd.group(2))
            try:
                ps = self.shell.user_ns['_dh'][nn]
            except IndexError:
                print('The requested directory does not exist in history.')
                return
            else:
                opts = {}
        elif parameter_s.startswith('--'):
            ps = None
            fallback = None
            pat = parameter_s[2:]
            dh = self.shell.user_ns['_dh']
            # first search only by basename (last component)
            for ent in reversed(dh):
                if pat in os.path.basename(ent) and os.path.isdir(ent):
                    ps = ent
                    break

                if fallback is None and pat in ent and os.path.isdir(ent):
                    fallback = ent

            # if we have no last part match, pick the first full path match
            if ps is None:
                ps = fallback

            if ps is None:
                print("No matching entry in directory history")
                return
            else:
                opts = {}


        else:
            opts, ps = self.parse_options(parameter_s, 'qb', mode='string')
        # jump to previous
        if ps == '-':
            try:
                ps = self.shell.user_ns['_dh'][-2]
            except IndexError as e:
                raise UsageError('%cd -: No previous directory to change to.') from e
        # jump to bookmark if needed
        else:
            if not os.path.isdir(ps) or 'b' in opts:
                bkms = self.shell.db.get('bookmarks', {})

                if ps in bkms:
                    target = bkms[ps]
                    print('(bookmark:%s) -> %s' % (ps, target))
                    ps = target
                else:
                    if 'b' in opts:
                        raise UsageError("Bookmark '%s' not found.  "
                              "Use '%%bookmark -l' to see your bookmarks." % ps)

        # at this point ps should point to the target dir
        if ps:
            try:
                os.chdir(os.path.expanduser(ps))
                if hasattr(self.shell, 'term_title') and self.shell.term_title:
                    set_term_title(self.shell.term_title_format.format(cwd=abbrev_cwd()))
            except OSError:
                print(sys.exc_info()[1])
            else:
                cwd = pathlib.Path.cwd()
                dhist = self.shell.user_ns['_dh']
                if oldcwd != cwd:
                    dhist.append(cwd)
                    self.shell.db['dhist'] = compress_dhist(dhist)[-100:]

        else:
            os.chdir(self.shell.home_dir)
            if hasattr(self.shell, 'term_title') and self.shell.term_title:
                set_term_title(self.shell.term_title_format.format(cwd="~"))
            cwd = pathlib.Path.cwd()
            dhist = self.shell.user_ns['_dh']

            if oldcwd != cwd:
                dhist.append(cwd)
                self.shell.db["dhist"] = compress_dhist(dhist)[-100:]
        if "q" not in opts and not self.cd_force_quiet and self.shell.user_ns["_dh"]:
            print(self.shell.user_ns["_dh"][-1])

    @line_magic
    def env(self, parameter_s=''):
        """Get, set, or list environment variables.

        Usage:\\

          :``%env``: lists all environment variables/values
          :``%env var``: get value for var
          :``%env var val``: set value for var
          :``%env var=val``: set value for var
          :``%env var=$val``: set value for var, using python expansion if possible
        """
        if parameter_s.strip():
            split = '=' if '=' in parameter_s else ' '
            bits = parameter_s.split(split)
            if len(bits) == 1:
                key = parameter_s.strip()
                if key in os.environ:
                    return os.environ[key]
                else:
                    err = "Environment does not have key: {0}".format(key)
                    raise UsageError(err)
            if len(bits) > 1:
                return self.set_env(parameter_s)
        env = dict(os.environ)
        # hide likely secrets when printing the whole environment
        for key in list(env):
            if any(s in key.lower() for s in ('key', 'token', 'secret')):
                env[key] = '<hidden>'

        return env

    @line_magic
    def set_env(self, parameter_s):
        """Set environment variables.  Assumptions are that either "val" is a
        name in the user namespace, or val is something that evaluates to a
        string.

        Usage:\\
          :``%set_env var val``: set value for var
          :``%set_env var=val``: set value for var
          :``%set_env var=$val``: set value for var, using python expansion if possible
        """
        split = '=' if '=' in parameter_s else ' '
        bits = parameter_s.split(split, 1)
        if not parameter_s.strip() or len(bits)<2:
            raise UsageError("usage is 'set_env var=val'")
        var = bits[0].strip()
        val = bits[1].strip()
        if re.match(r'.*\s.*', var):
            # an environment variable with whitespace is almost certainly
            # not what the user intended.  what's more likely is the wrong
            # split was chosen, ie for "set_env cmd_args A=B", we chose
            # '=' for the split and should have chosen ' '.  to get around
            # this, users should just assign directly to os.environ or use
            # standard magic {var} expansion.
            err = "refusing to set env var with whitespace: '{0}'"
            err = err.format(val)
            raise UsageError(err)
        os.environ[var] = val
        print('env: {0}={1}'.format(var,val))

    @line_magic
    def pushd(self, parameter_s=''):
        """Place the current dir on stack and change directory.

        Usage:\\
          %pushd ['dirname']
        """

        dir_s = self.shell.dir_stack
        tgt = os.path.expanduser(parameter_s)
        cwd = os.getcwd().replace(self.shell.home_dir,'~')
        if tgt:
            self.cd(parameter_s)
        dir_s.insert(0,cwd)
        return self.shell.run_line_magic('dirs', '')

    @line_magic
    def popd(self, parameter_s=''):
        """Change to directory popped off the top of the stack.
        """
        if not self.shell.dir_stack:
            raise UsageError("%popd on empty stack")
        top = self.shell.dir_stack.pop(0)
        self.cd(top)
        print("popd ->",top)

    @line_magic
    def dirs(self, parameter_s=''):
        """Return the current directory stack."""

        return self.shell.dir_stack

    @line_magic
    def dhist(self, parameter_s=''):
        """Print your history of visited directories.

        %dhist       -> print full history\\
        %dhist n     -> print last n entries only\\
        %dhist n1 n2 -> print entries between n1 and n2 (n2 not included)\\

        This history is automatically maintained by the %cd command, and
        always available as the global list variable _dh. You can use %cd -<n>
        to go to directory number <n>.

        Note that most of time, you should view directory history by entering
        cd -<TAB>.

        """

        dh = self.shell.user_ns['_dh']
        if parameter_s:
            try:
                args = map(int,parameter_s.split())
            except:
                self.arg_err(self.dhist)
                return
            if len(args) == 1:
                ini,fin = max(len(dh)-(args[0]),0),len(dh)
            elif len(args) == 2:
                ini,fin = args
                fin = min(fin, len(dh))
            else:
                self.arg_err(self.dhist)
                return
        else:
            ini,fin = 0,len(dh)
        print('Directory history (kept in _dh)')
        for i in range(ini, fin):
            print("%d: %s" % (i, dh[i]))

    @skip_doctest
    @line_magic
    def sc(self, parameter_s=''):
        """Shell capture - run shell command and capture output (DEPRECATED use !).

        DEPRECATED. Suboptimal, retained for backwards compatibility.

        You should use the form 'var = !command' instead. Example:

         "%sc -l myfiles = ls ~" should now be written as

         "myfiles = !ls ~"

        myfiles.s, myfiles.l and myfiles.n still apply as documented
        below.

        --
        %sc [options] varname=command

        IPython will run the given command using commands.getoutput(), and
        will then update the user's interactive namespace with a variable
        called varname, containing the value of the call.  Your command can
        contain shell wildcards, pipes, etc.

        The '=' sign in the syntax is mandatory, and the variable name you
        supply must follow Python's standard conventions for valid names.

        (A special format without variable name exists for internal use)

        Options:

          -l: list output.  Split the output on newlines into a list before
          assigning it to the given variable.  By default the output is stored
          as a single string.

          -v: verbose.  Print the contents of the variable.

        In most cases you should not need to split as a list, because the
        returned value is a special type of string which can automatically
        provide its contents either as a list (split on newlines) or as a
        space-separated string.  These are convenient, respectively, either
        for sequential processing or to be passed to a shell command.

        For example::

            # Capture into variable a
            In [1]: sc a=ls *py

            # a is a string with embedded newlines
            In [2]: a
            Out[2]: 'setup.py\\nwin32_manual_post_install.py'

            # which can be seen as a list:
            In [3]: a.l
            Out[3]: ['setup.py', 'win32_manual_post_install.py']

            # or as a whitespace-separated string:
            In [4]: a.s
            Out[4]: 'setup.py win32_manual_post_install.py'

            # a.s is useful to pass as a single command line:
            In [5]: !wc -l $a.s
              146 setup.py
              130 win32_manual_post_install.py
              276 total

            # while the list form is useful to loop over:
            In [6]: for f in a.l:
               ...:      !wc -l $f
               ...:
            146 setup.py
            130 win32_manual_post_install.py

        Similarly, the lists returned by the -l option are also special, in
        the sense that you can equally invoke the .s attribute on them to
        automatically get a whitespace-separated string from their contents::

            In [7]: sc -l b=ls *py

            In [8]: b
            Out[8]: ['setup.py', 'win32_manual_post_install.py']

            In [9]: b.s
            Out[9]: 'setup.py win32_manual_post_install.py'

        In summary, both the lists and strings used for output capture have
        the following special attributes::

            .l (or .list) : value as list.
            .n (or .nlstr): value as newline-separated string.
            .s (or .spstr): value as space-separated string.
        """

        opts,args = self.parse_options(parameter_s, 'lv')
        # Try to get a variable name and command to run
        try:
            # the variable name must be obtained from the parse_options
            # output, which uses shlex.split to strip options out.
            var,_ = args.split('=', 1)
            var = var.strip()
            # But the command has to be extracted from the original input
            # parameter_s, not on what parse_options returns, to avoid the
            # quote stripping which shlex.split performs on it.
            _,cmd = parameter_s.split('=', 1)
        except ValueError:
            var,cmd = '',''
        # If all looks ok, proceed
        split = 'l' in opts
        out = self.shell.getoutput(cmd, split=split)
        if 'v' in opts:
            print('%s ==\n%s' % (var, pformat(out)))
        if var:
            self.shell.user_ns.update({var:out})
        else:
            return out

    @line_cell_magic
    def sx(self, line='', cell=None):
        """Shell execute - run shell command and capture output (!! is short-hand).

        %sx command

        IPython will run the given command using commands.getoutput(), and
        return the result formatted as a list (split on '\\n').  Since the
        output is _returned_, it will be stored in ipython's regular output
        cache Out[N] and in the '_N' automatic variables.

        Notes:

        1) If an input line begins with '!!', then %sx is automatically
        invoked.  That is, while::

          !ls

        causes ipython to simply issue system('ls'), typing::

          !!ls

        is a shorthand equivalent to::

          %sx ls

        2) %sx differs from %sc in that %sx automatically splits into a list,
        like '%sc -l'.  The reason for this is to make it as easy as possible
        to process line-oriented shell output via further python commands.
        %sc is meant to provide much finer control, but requires more
        typing.

        3) Just like %sc -l, this is a list with special attributes:
        ::

          .l (or .list) : value as list.
          .n (or .nlstr): value as newline-separated string.
          .s (or .spstr): value as whitespace-separated string.

        This is very useful when trying to use such lists as arguments to
        system commands."""
        
        if cell is None:
            # line magic
            return self.shell.getoutput(line)
        else:
            opts,args = self.parse_options(line, '', 'out=')
            output = self.shell.getoutput(cell)
            out_name = opts.get('out', opts.get('o'))
            if out_name:
                self.shell.user_ns[out_name] = output
            else:
                return output

    system = line_cell_magic('system')(sx)
    bang = cell_magic('!')(sx)

    @line_magic
    def bookmark(self, parameter_s=''):
        """Manage IPython's bookmark system.

        %bookmark <name>       - set bookmark to current dir
        %bookmark <name> <dir> - set bookmark to <dir>
        %bookmark -l           - list all bookmarks
        %bookmark -d <name>    - remove bookmark
        %bookmark -r           - remove all bookmarks

        You can later on access a bookmarked folder with::

          %cd -b <name>

        or simply '%cd <name>' if there is no directory called <name> AND
        there is such a bookmark defined.

        Your bookmarks persist through IPython sessions, but they are
        associated with each profile."""

        opts,args = self.parse_options(parameter_s,'drl',mode='list')
        if len(args) > 2:
            raise UsageError("%bookmark: too many arguments")

        bkms = self.shell.db.get('bookmarks',{})

        if 'd' in opts:
            try:
                todel = args[0]
            except IndexError as e:
                raise UsageError(
                    "%bookmark -d: must provide a bookmark to delete") from e
            else:
                try:
                    del bkms[todel]
                except KeyError as e:
                    raise UsageError(
                        "%%bookmark -d: Can't delete bookmark '%s'" % todel) from e

        elif 'r' in opts:
            bkms = {}
        elif 'l' in opts:
            bks = sorted(bkms)
            if bks:
                size = max(map(len, bks))
            else:
                size = 0
            fmt = '%-'+str(size)+'s -> %s'
            print('Current bookmarks:')
            for bk in bks:
                print(fmt % (bk, bkms[bk]))
        else:
            if not args:
                raise UsageError("%bookmark: You must specify the bookmark name")
            elif len(args)==1:
                bkms[args[0]] = os.getcwd()
            elif len(args)==2:
                bkms[args[0]] = args[1]
        self.shell.db['bookmarks'] = bkms

    @line_magic
    def pycat(self, parameter_s=''):
        """Show a syntax-highlighted file through a pager.

        This magic is similar to the cat utility, but it will assume the file
        to be Python source and will show it with syntax highlighting.

        This magic command can either take a local filename, an url,
        an history range (see %history) or a macro as argument.

        If no parameter is given, prints out history of current session up to
        this point. ::

        %pycat myscript.py
        %pycat 7-27
        %pycat myMacro
        %pycat http://www.example.com/myscript.py
        """
        try:
            cont = self.shell.find_user_code(parameter_s, skip_encoding_cookie=False)
        except (ValueError, IOError):
            print("Error: no such file, variable, URL, history range or macro")
            return

        page.page(self.shell.pycolorize(source_to_unicode(cont)))

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-a', '--append', action='store_true', default=False,
        help='Append contents of the cell to an existing file. '
             'The file will be created if it does not exist.'
    )
    @magic_arguments.argument(
        'filename', type=str,
        help='file to write'
    )
    @cell_magic
    def writefile(self, line, cell):
        """Write the contents of the cell to a file.

        The file will be overwritten unless the -a (--append) flag is specified.
        """
        args = magic_arguments.parse_argstring(self.writefile, line)
        if re.match(r'^(\'.*\')|(".*")$', args.filename):
            filename = os.path.expanduser(args.filename[1:-1])
        else:
            filename = os.path.expanduser(args.filename)
            
        if os.path.exists(filename):
            if args.append:
                print("Appending to %s" % filename)
            else:
                print("Overwriting %s" % filename)
        else:
            print("Writing %s" % filename)
        
        mode = 'a' if args.append else 'w'
        with io.open(filename, mode, encoding='utf-8') as f:
            f.write(cell)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\hub_mixin.py ===
import inspect
import json
import os
from dataclasses import Field, asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional, Protocol, Tuple, Type, TypeVar, Union

import packaging.version

from . import constants
from .errors import EntryNotFoundError, HfHubHTTPError
from .file_download import hf_hub_download
from .hf_api import HfApi
from .repocard import ModelCard, ModelCardData
from .utils import (
    SoftTemporaryDirectory,
    is_jsonable,
    is_safetensors_available,
    is_simple_optional_type,
    is_torch_available,
    logging,
    unwrap_simple_optional_type,
    validate_hf_hub_args,
)


if is_torch_available():
    import torch  # type: ignore

if is_safetensors_available():
    import safetensors
    from safetensors.torch import load_model as load_model_as_safetensor
    from safetensors.torch import save_model as save_model_as_safetensor


logger = logging.get_logger(__name__)


# Type alias for dataclass instances, copied from https://github.com/python/typeshed/blob/9f28171658b9ca6c32a7cb93fbb99fc92b17858b/stdlib/_typeshed/__init__.pyi#L349
class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


# Generic variable that is either ModelHubMixin or a subclass thereof
T = TypeVar("T", bound="ModelHubMixin")
# Generic variable to represent an args type
ARGS_T = TypeVar("ARGS_T")
ENCODER_T = Callable[[ARGS_T], Any]
DECODER_T = Callable[[Any], ARGS_T]
CODER_T = Tuple[ENCODER_T, DECODER_T]


DEFAULT_MODEL_CARD = """
---
# For reference on model card metadata, see the spec: https://github.com/huggingface/hub-docs/blob/main/modelcard.md?plain=1
# Doc / guide: https://huggingface.co/docs/hub/model-cards
{{ card_data }}
---

This model has been pushed to the Hub using the [PytorchModelHubMixin](https://huggingface.co/docs/huggingface_hub/package_reference/mixins#huggingface_hub.PyTorchModelHubMixin) integration:
- Code: {{ repo_url | default("[More Information Needed]", true) }}
- Paper: {{ paper_url | default("[More Information Needed]", true) }}
- Docs: {{ docs_url | default("[More Information Needed]", true) }}
"""


@dataclass
class MixinInfo:
    model_card_template: str
    model_card_data: ModelCardData
    docs_url: Optional[str] = None
    paper_url: Optional[str] = None
    repo_url: Optional[str] = None


class ModelHubMixin:
    """
    A generic mixin to integrate ANY machine learning framework with the Hub.

    To integrate your framework, your model class must inherit from this class. Custom logic for saving/loading models
    have to be overwritten in  [`_from_pretrained`] and [`_save_pretrained`]. [`PyTorchModelHubMixin`] is a good example
    of mixin integration with the Hub. Check out our [integration guide](../guides/integrations) for more instructions.

    When inheriting from [`ModelHubMixin`], you can define class-level attributes. These attributes are not passed to
    `__init__` but to the class definition itself. This is useful to define metadata about the library integrating
    [`ModelHubMixin`].

    For more details on how to integrate the mixin with your library, checkout the [integration guide](../guides/integrations).

    Args:
        repo_url (`str`, *optional*):
            URL of the library repository. Used to generate model card.
        paper_url (`str`, *optional*):
            URL of the library paper. Used to generate model card.
        docs_url (`str`, *optional*):
            URL of the library documentation. Used to generate model card.
        model_card_template (`str`, *optional*):
            Template of the model card. Used to generate model card. Defaults to a generic template.
        language (`str` or `List[str]`, *optional*):
            Language supported by the library. Used to generate model card.
        library_name (`str`, *optional*):
            Name of the library integrating ModelHubMixin. Used to generate model card.
        license (`str`, *optional*):
            License of the library integrating ModelHubMixin. Used to generate model card.
            E.g: "apache-2.0"
        license_name (`str`, *optional*):
            Name of the library integrating ModelHubMixin. Used to generate model card.
            Only used if `license` is set to `other`.
            E.g: "coqui-public-model-license".
        license_link (`str`, *optional*):
            URL to the license of the library integrating ModelHubMixin. Used to generate model card.
            Only used if `license` is set to `other` and `license_name` is set.
            E.g: "https://coqui.ai/cpml".
        pipeline_tag (`str`, *optional*):
            Tag of the pipeline. Used to generate model card. E.g. "text-classification".
        tags (`List[str]`, *optional*):
            Tags to be added to the model card. Used to generate model card. E.g. ["computer-vision"]
        coders (`Dict[Type, Tuple[Callable, Callable]]`, *optional*):
            Dictionary of custom types and their encoders/decoders. Used to encode/decode arguments that are not
            jsonable by default. E.g dataclasses, argparse.Namespace, OmegaConf, etc.

    Example:

    ```python
    >>> from huggingface_hub import ModelHubMixin

    # Inherit from ModelHubMixin
    >>> class MyCustomModel(
    ...         ModelHubMixin,
    ...         library_name="my-library",
    ...         tags=["computer-vision"],
    ...         repo_url="https://github.com/huggingface/my-cool-library",
    ...         paper_url="https://arxiv.org/abs/2304.12244",
    ...         docs_url="https://huggingface.co/docs/my-cool-library",
    ...         # ^ optional metadata to generate model card
    ...     ):
    ...     def __init__(self, size: int = 512, device: str = "cpu"):
    ...         # define how to initialize your model
    ...         super().__init__()
    ...         ...
    ...
    ...     def _save_pretrained(self, save_directory: Path) -> None:
    ...         # define how to serialize your model
    ...         ...
    ...
    ...     @classmethod
    ...     def from_pretrained(
    ...         cls: Type[T],
    ...         pretrained_model_name_or_path: Union[str, Path],
    ...         *,
    ...         force_download: bool = False,
    ...         resume_download: Optional[bool] = None,
    ...         proxies: Optional[Dict] = None,
    ...         token: Optional[Union[str, bool]] = None,
    ...         cache_dir: Optional[Union[str, Path]] = None,
    ...         local_files_only: bool = False,
    ...         revision: Optional[str] = None,
    ...         **model_kwargs,
    ...     ) -> T:
    ...         # define how to deserialize your model
    ...         ...

    >>> model = MyCustomModel(size=256, device="gpu")

    # Save model weights to local directory
    >>> model.save_pretrained("my-awesome-model")

    # Push model weights to the Hub
    >>> model.push_to_hub("my-awesome-model")

    # Download and initialize weights from the Hub
    >>> reloaded_model = MyCustomModel.from_pretrained("username/my-awesome-model")
    >>> reloaded_model.size
    256

    # Model card has been correctly populated
    >>> from huggingface_hub import ModelCard
    >>> card = ModelCard.load("username/my-awesome-model")
    >>> card.data.tags
    ["x-custom-tag", "pytorch_model_hub_mixin", "model_hub_mixin"]
    >>> card.data.library_name
    "my-library"
    ```
    """

    _hub_mixin_config: Optional[Union[dict, DataclassInstance]] = None
    # ^ optional config attribute automatically set in `from_pretrained`
    _hub_mixin_info: MixinInfo
    # ^ information about the library integrating ModelHubMixin (used to generate model card)
    _hub_mixin_inject_config: bool  # whether `_from_pretrained` expects `config` or not
    _hub_mixin_init_parameters: Dict[str, inspect.Parameter]  # __init__ parameters
    _hub_mixin_jsonable_default_values: Dict[str, Any]  # default values for __init__ parameters
    _hub_mixin_jsonable_custom_types: Tuple[Type, ...]  # custom types that can be encoded/decoded
    _hub_mixin_coders: Dict[Type, CODER_T]  # encoders/decoders for custom types
    # ^ internal values to handle config

    def __init_subclass__(
        cls,
        *,
        # Generic info for model card
        repo_url: Optional[str] = None,
        paper_url: Optional[str] = None,
        docs_url: Optional[str] = None,
        # Model card template
        model_card_template: str = DEFAULT_MODEL_CARD,
        # Model card metadata
        language: Optional[List[str]] = None,
        library_name: Optional[str] = None,
        license: Optional[str] = None,
        license_name: Optional[str] = None,
        license_link: Optional[str] = None,
        pipeline_tag: Optional[str] = None,
        tags: Optional[List[str]] = None,
        # How to encode/decode arguments with custom type into a JSON config?
        coders: Optional[
            Dict[Type, CODER_T]
            # Key is a type.
            # Value is a tuple (encoder, decoder).
            # Example: {MyCustomType: (lambda x: x.value, lambda data: MyCustomType(data))}
        ] = None,
    ) -> None:
        """Inspect __init__ signature only once when subclassing + handle modelcard."""
        super().__init_subclass__()

        # Will be reused when creating modelcard
        tags = tags or []
        tags.append("model_hub_mixin")

        # Initialize MixinInfo if not existent
        info = MixinInfo(model_card_template=model_card_template, model_card_data=ModelCardData())

        # If parent class has a MixinInfo, inherit from it as a copy
        if hasattr(cls, "_hub_mixin_info"):
            # Inherit model card template from parent class if not explicitly set
            if model_card_template == DEFAULT_MODEL_CARD:
                info.model_card_template = cls._hub_mixin_info.model_card_template

            # Inherit from parent model card data
            info.model_card_data = ModelCardData(**cls._hub_mixin_info.model_card_data.to_dict())

            # Inherit other info
            info.docs_url = cls._hub_mixin_info.docs_url
            info.paper_url = cls._hub_mixin_info.paper_url
            info.repo_url = cls._hub_mixin_info.repo_url
        cls._hub_mixin_info = info

        # Update MixinInfo with metadata
        if model_card_template is not None and model_card_template != DEFAULT_MODEL_CARD:
            info.model_card_template = model_card_template
        if repo_url is not None:
            info.repo_url = repo_url
        if paper_url is not None:
            info.paper_url = paper_url
        if docs_url is not None:
            info.docs_url = docs_url
        if language is not None:
            info.model_card_data.language = language
        if library_name is not None:
            info.model_card_data.library_name = library_name
        if license is not None:
            info.model_card_data.license = license
        if license_name is not None:
            info.model_card_data.license_name = license_name
        if license_link is not None:
            info.model_card_data.license_link = license_link
        if pipeline_tag is not None:
            info.model_card_data.pipeline_tag = pipeline_tag
        if tags is not None:
            if info.model_card_data.tags is not None:
                info.model_card_data.tags.extend(tags)
            else:
                info.model_card_data.tags = tags

        info.model_card_data.tags = sorted(set(info.model_card_data.tags))

        # Handle encoders/decoders for args
        cls._hub_mixin_coders = coders or {}
        cls._hub_mixin_jsonable_custom_types = tuple(cls._hub_mixin_coders.keys())

        # Inspect __init__ signature to handle config
        cls._hub_mixin_init_parameters = dict(inspect.signature(cls.__init__).parameters)
        cls._hub_mixin_jsonable_default_values = {
            param.name: cls._encode_arg(param.default)
            for param in cls._hub_mixin_init_parameters.values()
            if param.default is not inspect.Parameter.empty and cls._is_jsonable(param.default)
        }
        cls._hub_mixin_inject_config = "config" in inspect.signature(cls._from_pretrained).parameters

    def __new__(cls: Type[T], *args, **kwargs) -> T:
        """Create a new instance of the class and handle config.

        3 cases:
        - If `self._hub_mixin_config` is already set, do nothing.
        - If `config` is passed as a dataclass, set it as `self._hub_mixin_config`.
        - Otherwise, build `self._hub_mixin_config` from default values and passed values.
        """
        instance = super().__new__(cls)

        # If `config` is already set, return early
        if instance._hub_mixin_config is not None:
            return instance

        # Infer passed values
        passed_values = {
            **{
                key: value
                for key, value in zip(
                    # [1:] to skip `self` parameter
                    list(cls._hub_mixin_init_parameters)[1:],
                    args,
                )
            },
            **kwargs,
        }

        # If config passed as dataclass => set it and return early
        if is_dataclass(passed_values.get("config")):
            instance._hub_mixin_config = passed_values["config"]
            return instance

        # Otherwise, build config from default + passed values
        init_config = {
            # default values
            **cls._hub_mixin_jsonable_default_values,
            # passed values
            **{
                key: cls._encode_arg(value)  # Encode custom types as jsonable value
                for key, value in passed_values.items()
                if instance._is_jsonable(value)  # Only if jsonable or we have a custom encoder
            },
        }
        passed_config = init_config.pop("config", {})

        # Populate `init_config` with provided config
        if isinstance(passed_config, dict):
            init_config.update(passed_config)

        # Set `config` attribute and return
        if init_config != {}:
            instance._hub_mixin_config = init_config
        return instance

    @classmethod
    def _is_jsonable(cls, value: Any) -> bool:
        """Check if a value is JSON serializable."""
        if is_dataclass(value):
            return True
        if isinstance(value, cls._hub_mixin_jsonable_custom_types):
            return True
        return is_jsonable(value)

    @classmethod
    def _encode_arg(cls, arg: Any) -> Any:
        """Encode an argument into a JSON serializable format."""
        if is_dataclass(arg):
            return asdict(arg)  # type: ignore[arg-type]
        for type_, (encoder, _) in cls._hub_mixin_coders.items():
            if isinstance(arg, type_):
                if arg is None:
                    return None
                return encoder(arg)
        return arg

    @classmethod
    def _decode_arg(cls, expected_type: Type[ARGS_T], value: Any) -> Optional[ARGS_T]:
        """Decode a JSON serializable value into an argument."""
        if is_simple_optional_type(expected_type):
            if value is None:
                return None
            expected_type = unwrap_simple_optional_type(expected_type)
        # Dataclass => handle it
        if is_dataclass(expected_type):
            return _load_dataclass(expected_type, value)  # type: ignore[return-value]
        # Otherwise => check custom decoders
        for type_, (_, decoder) in cls._hub_mixin_coders.items():
            if inspect.isclass(expected_type) and issubclass(expected_type, type_):
                return decoder(value)
        # Otherwise => don't decode
        return value

    def save_pretrained(
        self,
        save_directory: Union[str, Path],
        *,
        config: Optional[Union[dict, DataclassInstance]] = None,
        repo_id: Optional[str] = None,
        push_to_hub: bool = False,
        model_card_kwargs: Optional[Dict[str, Any]] = None,
        **push_to_hub_kwargs,
    ) -> Optional[str]:
        """
        Save weights in local directory.

        Args:
            save_directory (`str` or `Path`):
                Path to directory in which the model weights and configuration will be saved.
            config (`dict` or `DataclassInstance`, *optional*):
                Model configuration specified as a key/value dictionary or a dataclass instance.
            push_to_hub (`bool`, *optional*, defaults to `False`):
                Whether or not to push your model to the Huggingface Hub after saving it.
            repo_id (`str`, *optional*):
                ID of your repository on the Hub. Used only if `push_to_hub=True`. Will default to the folder name if
                not provided.
            model_card_kwargs (`Dict[str, Any]`, *optional*):
                Additional arguments passed to the model card template to customize the model card.
            push_to_hub_kwargs:
                Additional key word arguments passed along to the [`~ModelHubMixin.push_to_hub`] method.
        Returns:
            `str` or `None`: url of the commit on the Hub if `push_to_hub=True`, `None` otherwise.
        """
        save_directory = Path(save_directory)
        save_directory.mkdir(parents=True, exist_ok=True)

        # Remove config.json if already exists. After `_save_pretrained` we don't want to overwrite config.json
        # as it might have been saved by the custom `_save_pretrained` already. However we do want to overwrite
        # an existing config.json if it was not saved by `_save_pretrained`.
        config_path = save_directory / constants.CONFIG_NAME
        config_path.unlink(missing_ok=True)

        # save model weights/files (framework-specific)
        self._save_pretrained(save_directory)

        # save config (if provided and if not serialized yet in `_save_pretrained`)
        if config is None:
            config = self._hub_mixin_config
        if config is not None:
            if is_dataclass(config):
                config = asdict(config)  # type: ignore[arg-type]
            if not config_path.exists():
                config_str = json.dumps(config, sort_keys=True, indent=2)
                config_path.write_text(config_str)

        # save model card
        model_card_path = save_directory / "README.md"
        model_card_kwargs = model_card_kwargs if model_card_kwargs is not None else {}
        if not model_card_path.exists():  # do not overwrite if already exists
            self.generate_model_card(**model_card_kwargs).save(save_directory / "README.md")

        # push to the Hub if required
        if push_to_hub:
            kwargs = push_to_hub_kwargs.copy()  # soft-copy to avoid mutating input
            if config is not None:  # kwarg for `push_to_hub`
                kwargs["config"] = config
            if repo_id is None:
                repo_id = save_directory.name  # Defaults to `save_directory` name
            return self.push_to_hub(repo_id=repo_id, model_card_kwargs=model_card_kwargs, **kwargs)
        return None

    def _save_pretrained(self, save_directory: Path) -> None:
        """
        Overwrite this method in subclass to define how to save your model.
        Check out our [integration guide](../guides/integrations) for instructions.

        Args:
            save_directory (`str` or `Path`):
                Path to directory in which the model weights and configuration will be saved.
        """
        raise NotImplementedError

    @classmethod
    @validate_hf_hub_args
    def from_pretrained(
        cls: Type[T],
        pretrained_model_name_or_path: Union[str, Path],
        *,
        force_download: bool = False,
        resume_download: Optional[bool] = None,
        proxies: Optional[Dict] = None,
        token: Optional[Union[str, bool]] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        local_files_only: bool = False,
        revision: Optional[str] = None,
        **model_kwargs,
    ) -> T:
        """
        Download a model from the Huggingface Hub and instantiate it.

        Args:
            pretrained_model_name_or_path (`str`, `Path`):
                - Either the `model_id` (string) of a model hosted on the Hub, e.g. `bigscience/bloom`.
                - Or a path to a `directory` containing model weights saved using
                    [`~transformers.PreTrainedModel.save_pretrained`], e.g., `../path/to/my_model_directory/`.
            revision (`str`, *optional*):
                Revision of the model on the Hub. Can be a branch name, a git tag or any commit id.
                Defaults to the latest commit on `main` branch.
            force_download (`bool`, *optional*, defaults to `False`):
                Whether to force (re-)downloading the model weights and configuration files from the Hub, overriding
                the existing cache.
            proxies (`Dict[str, str]`, *optional*):
                A dictionary of proxy servers to use by protocol or endpoint, e.g., `{'http': 'foo.bar:3128',
                'http://hostname': 'foo.bar:4012'}`. The proxies are used on every request.
            token (`str` or `bool`, *optional*):
                The token to use as HTTP bearer authorization for remote files. By default, it will use the token
                cached when running `huggingface-cli login`.
            cache_dir (`str`, `Path`, *optional*):
                Path to the folder where cached files are stored.
            local_files_only (`bool`, *optional*, defaults to `False`):
                If `True`, avoid downloading the file and return the path to the local cached file if it exists.
            model_kwargs (`Dict`, *optional*):
                Additional kwargs to pass to the model during initialization.
        """
        model_id = str(pretrained_model_name_or_path)
        config_file: Optional[str] = None
        if os.path.isdir(model_id):
            if constants.CONFIG_NAME in os.listdir(model_id):
                config_file = os.path.join(model_id, constants.CONFIG_NAME)
            else:
                logger.warning(f"{constants.CONFIG_NAME} not found in {Path(model_id).resolve()}")
        else:
            try:
                config_file = hf_hub_download(
                    repo_id=model_id,
                    filename=constants.CONFIG_NAME,
                    revision=revision,
                    cache_dir=cache_dir,
                    force_download=force_download,
                    proxies=proxies,
                    resume_download=resume_download,
                    token=token,
                    local_files_only=local_files_only,
                )
            except HfHubHTTPError as e:
                logger.info(f"{constants.CONFIG_NAME} not found on the HuggingFace Hub: {str(e)}")

        # Read config
        config = None
        if config_file is not None:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Decode custom types in config
            for key, value in config.items():
                if key in cls._hub_mixin_init_parameters:
                    expected_type = cls._hub_mixin_init_parameters[key].annotation
                    if expected_type is not inspect.Parameter.empty:
                        config[key] = cls._decode_arg(expected_type, value)

            # Populate model_kwargs from config
            for param in cls._hub_mixin_init_parameters.values():
                if param.name not in model_kwargs and param.name in config:
                    model_kwargs[param.name] = config[param.name]

            # Check if `config` argument was passed at init
            if "config" in cls._hub_mixin_init_parameters and "config" not in model_kwargs:
                # Decode `config` argument if it was passed
                config_annotation = cls._hub_mixin_init_parameters["config"].annotation
                config = cls._decode_arg(config_annotation, config)

                # Forward config to model initialization
                model_kwargs["config"] = config

            # Inject config if `**kwargs` are expected
            if is_dataclass(cls):
                for key in cls.__dataclass_fields__:
                    if key not in model_kwargs and key in config:
                        model_kwargs[key] = config[key]
            elif any(param.kind == inspect.Parameter.VAR_KEYWORD for param in cls._hub_mixin_init_parameters.values()):
                for key, value in config.items():
                    if key not in model_kwargs:
                        model_kwargs[key] = value

            # Finally, also inject if `_from_pretrained` expects it
            if cls._hub_mixin_inject_config and "config" not in model_kwargs:
                model_kwargs["config"] = config

        instance = cls._from_pretrained(
            model_id=str(model_id),
            revision=revision,
            cache_dir=cache_dir,
            force_download=force_download,
            proxies=proxies,
            resume_download=resume_download,
            local_files_only=local_files_only,
            token=token,
            **model_kwargs,
        )

        # Implicitly set the config as instance attribute if not already set by the class
        # This way `config` will be available when calling `save_pretrained` or `push_to_hub`.
        if config is not None and (getattr(instance, "_hub_mixin_config", None) in (None, {})):
            instance._hub_mixin_config = config

        return instance

    @classmethod
    def _from_pretrained(
        cls: Type[T],
        *,
        model_id: str,
        revision: Optional[str],
        cache_dir: Optional[Union[str, Path]],
        force_download: bool,
        proxies: Optional[Dict],
        resume_download: Optional[bool],
        local_files_only: bool,
        token: Optional[Union[str, bool]],
        **model_kwargs,
    ) -> T:
        """Overwrite this method in subclass to define how to load your model from pretrained.

        Use [`hf_hub_download`] or [`snapshot_download`] to download files from the Hub before loading them. Most
        args taken as input can be directly passed to those 2 methods. If needed, you can add more arguments to this
        method using "model_kwargs". For example [`PyTorchModelHubMixin._from_pretrained`] takes as input a `map_location`
        parameter to set on which device the model should be loaded.

        Check out our [integration guide](../guides/integrations) for more instructions.

        Args:
            model_id (`str`):
                ID of the model to load from the Huggingface Hub (e.g. `bigscience/bloom`).
            revision (`str`, *optional*):
                Revision of the model on the Hub. Can be a branch name, a git tag or any commit id. Defaults to the
                latest commit on `main` branch.
            force_download (`bool`, *optional*, defaults to `False`):
                Whether to force (re-)downloading the model weights and configuration files from the Hub, overriding
                the existing cache.
            proxies (`Dict[str, str]`, *optional*):
                A dictionary of proxy servers to use by protocol or endpoint (e.g., `{'http': 'foo.bar:3128',
                'http://hostname': 'foo.bar:4012'}`).
            token (`str` or `bool`, *optional*):
                The token to use as HTTP bearer authorization for remote files. By default, it will use the token
                cached when running `huggingface-cli login`.
            cache_dir (`str`, `Path`, *optional*):
                Path to the folder where cached files are stored.
            local_files_only (`bool`, *optional*, defaults to `False`):
                If `True`, avoid downloading the file and return the path to the local cached file if it exists.
            model_kwargs:
                Additional keyword arguments passed along to the [`~ModelHubMixin._from_pretrained`] method.
        """
        raise NotImplementedError

    @validate_hf_hub_args
    def push_to_hub(
        self,
        repo_id: str,
        *,
        config: Optional[Union[dict, DataclassInstance]] = None,
        commit_message: str = "Push model using huggingface_hub.",
        private: Optional[bool] = None,
        token: Optional[str] = None,
        branch: Optional[str] = None,
        create_pr: Optional[bool] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        delete_patterns: Optional[Union[List[str], str]] = None,
        model_card_kwargs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Upload model checkpoint to the Hub.

        Use `allow_patterns` and `ignore_patterns` to precisely filter which files should be pushed to the hub. Use
        `delete_patterns` to delete existing remote files in the same commit. See [`upload_folder`] reference for more
        details.

        Args:
            repo_id (`str`):
                ID of the repository to push to (example: `"username/my-model"`).
            config (`dict` or `DataclassInstance`, *optional*):
                Model configuration specified as a key/value dictionary or a dataclass instance.
            commit_message (`str`, *optional*):
                Message to commit while pushing.
            private (`bool`, *optional*):
                Whether the repository created should be private.
                If `None` (default), the repo will be public unless the organization's default is private.
            token (`str`, *optional*):
                The token to use as HTTP bearer authorization for remote files. By default, it will use the token
                cached when running `huggingface-cli login`.
            branch (`str`, *optional*):
                The git branch on which to push the model. This defaults to `"main"`.
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request from `branch` with that commit. Defaults to `False`.
            allow_patterns (`List[str]` or `str`, *optional*):
                If provided, only files matching at least one pattern are pushed.
            ignore_patterns (`List[str]` or `str`, *optional*):
                If provided, files matching any of the patterns are not pushed.
            delete_patterns (`List[str]` or `str`, *optional*):
                If provided, remote files matching any of the patterns will be deleted from the repo.
            model_card_kwargs (`Dict[str, Any]`, *optional*):
                Additional arguments passed to the model card template to customize the model card.

        Returns:
            The url of the commit of your model in the given repository.
        """
        api = HfApi(token=token)
        repo_id = api.create_repo(repo_id=repo_id, private=private, exist_ok=True).repo_id

        # Push the files to the repo in a single commit
        with SoftTemporaryDirectory() as tmp:
            saved_path = Path(tmp) / repo_id
            self.save_pretrained(saved_path, config=config, model_card_kwargs=model_card_kwargs)
            return api.upload_folder(
                repo_id=repo_id,
                repo_type="model",
                folder_path=saved_path,
                commit_message=commit_message,
                revision=branch,
                create_pr=create_pr,
                allow_patterns=allow_patterns,
                ignore_patterns=ignore_patterns,
                delete_patterns=delete_patterns,
            )

    def generate_model_card(self, *args, **kwargs) -> ModelCard:
        card = ModelCard.from_template(
            card_data=self._hub_mixin_info.model_card_data,
            template_str=self._hub_mixin_info.model_card_template,
            repo_url=self._hub_mixin_info.repo_url,
            paper_url=self._hub_mixin_info.paper_url,
            docs_url=self._hub_mixin_info.docs_url,
            **kwargs,
        )
        return card


class PyTorchModelHubMixin(ModelHubMixin):
    """
    Implementation of [`ModelHubMixin`] to provide model Hub upload/download capabilities to PyTorch models. The model
    is set in evaluation mode by default using `model.eval()` (dropout modules are deactivated). To train the model,
    you should first set it back in training mode with `model.train()`.

    See [`ModelHubMixin`] for more details on how to use the mixin.

    Example:

    ```python
    >>> import torch
    >>> import torch.nn as nn
    >>> from huggingface_hub import PyTorchModelHubMixin

    >>> class MyModel(
    ...         nn.Module,
    ...         PyTorchModelHubMixin,
    ...         library_name="keras-nlp",
    ...         repo_url="https://github.com/keras-team/keras-nlp",
    ...         paper_url="https://arxiv.org/abs/2304.12244",
    ...         docs_url="https://keras.io/keras_nlp/",
    ...         # ^ optional metadata to generate model card
    ...     ):
    ...     def __init__(self, hidden_size: int = 512, vocab_size: int = 30000, output_size: int = 4):
    ...         super().__init__()
    ...         self.param = nn.Parameter(torch.rand(hidden_size, vocab_size))
    ...         self.linear = nn.Linear(output_size, vocab_size)

    ...     def forward(self, x):
    ...         return self.linear(x + self.param)
    >>> model = MyModel(hidden_size=256)

    # Save model weights to local directory
    >>> model.save_pretrained("my-awesome-model")

    # Push model weights to the Hub
    >>> model.push_to_hub("my-awesome-model")

    # Download and initialize weights from the Hub
    >>> model = MyModel.from_pretrained("username/my-awesome-model")
    >>> model.hidden_size
    256
    ```
    """

    def __init_subclass__(cls, *args, tags: Optional[List[str]] = None, **kwargs) -> None:
        tags = tags or []
        tags.append("pytorch_model_hub_mixin")
        kwargs["tags"] = tags
        return super().__init_subclass__(*args, **kwargs)

    def _save_pretrained(self, save_directory: Path) -> None:
        """Save weights from a Pytorch model to a local directory."""
        model_to_save = self.module if hasattr(self, "module") else self  # type: ignore
        save_model_as_safetensor(model_to_save, str(save_directory / constants.SAFETENSORS_SINGLE_FILE))  # type: ignore [arg-type]

    @classmethod
    def _from_pretrained(
        cls,
        *,
        model_id: str,
        revision: Optional[str],
        cache_dir: Optional[Union[str, Path]],
        force_download: bool,
        proxies: Optional[Dict],
        resume_download: Optional[bool],
        local_files_only: bool,
        token: Union[str, bool, None],
        map_location: str = "cpu",
        strict: bool = False,
        **model_kwargs,
    ):
        """Load Pytorch pretrained weights and return the loaded model."""
        model = cls(**model_kwargs)
        if os.path.isdir(model_id):
            print("Loading weights from local directory")
            model_file = os.path.join(model_id, constants.SAFETENSORS_SINGLE_FILE)
            return cls._load_as_safetensor(model, model_file, map_location, strict)
        else:
            try:
                model_file = hf_hub_download(
                    repo_id=model_id,
                    filename=constants.SAFETENSORS_SINGLE_FILE,
                    revision=revision,
                    cache_dir=cache_dir,
                    force_download=force_download,
                    proxies=proxies,
                    resume_download=resume_download,
                    token=token,
                    local_files_only=local_files_only,
                )
                return cls._load_as_safetensor(model, model_file, map_location, strict)
            except EntryNotFoundError:
                model_file = hf_hub_download(
                    repo_id=model_id,
                    filename=constants.PYTORCH_WEIGHTS_NAME,
                    revision=revision,
                    cache_dir=cache_dir,
                    force_download=force_download,
                    proxies=proxies,
                    resume_download=resume_download,
                    token=token,
                    local_files_only=local_files_only,
                )
                return cls._load_as_pickle(model, model_file, map_location, strict)

    @classmethod
    def _load_as_pickle(cls, model: T, model_file: str, map_location: str, strict: bool) -> T:
        state_dict = torch.load(model_file, map_location=torch.device(map_location), weights_only=True)
        model.load_state_dict(state_dict, strict=strict)  # type: ignore
        model.eval()  # type: ignore
        return model

    @classmethod
    def _load_as_safetensor(cls, model: T, model_file: str, map_location: str, strict: bool) -> T:
        if packaging.version.parse(safetensors.__version__) < packaging.version.parse("0.4.3"):  # type: ignore [attr-defined]
            load_model_as_safetensor(model, model_file, strict=strict)  # type: ignore [arg-type]
            if map_location != "cpu":
                logger.warning(
                    "Loading model weights on other devices than 'cpu' is not supported natively in your version of safetensors."
                    " This means that the model is loaded on 'cpu' first and then copied to the device."
                    " This leads to a slower loading time."
                    " Please update safetensors to version 0.4.3 or above for improved performance."
                )
                model.to(map_location)  # type: ignore [attr-defined]
        else:
            safetensors.torch.load_model(model, model_file, strict=strict, device=map_location)  # type: ignore [arg-type]
        return model


def _load_dataclass(datacls: Type[DataclassInstance], data: dict) -> DataclassInstance:
    """Load a dataclass instance from a dictionary.

    Fields not expected by the dataclass are ignored.
    """
    return datacls(**{k: v for k, v in data.items() if k in datacls.__dataclass_fields__})

# === NexusCore/openenv\Lib\site-packages\openai\_response.py ===
from __future__ import annotations

import os
import inspect
import logging
import datetime
import functools
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    Generic,
    TypeVar,
    Callable,
    Iterator,
    AsyncIterator,
    cast,
    overload,
)
from typing_extensions import Awaitable, ParamSpec, override, get_origin

import anyio
import httpx
import pydantic

from ._types import NoneType
from ._utils import is_given, extract_type_arg, is_annotated_type, is_type_alias_type, extract_type_var_from_base
from ._models import BaseModel, is_basemodel, add_request_id
from ._constants import RAW_RESPONSE_HEADER, OVERRIDE_CAST_TO_HEADER
from ._streaming import Stream, AsyncStream, is_stream_class_type, extract_stream_chunk_type
from ._exceptions import OpenAIError, APIResponseValidationError

if TYPE_CHECKING:
    from ._models import FinalRequestOptions
    from ._base_client import BaseClient


P = ParamSpec("P")
R = TypeVar("R")
_T = TypeVar("_T")
_APIResponseT = TypeVar("_APIResponseT", bound="APIResponse[Any]")
_AsyncAPIResponseT = TypeVar("_AsyncAPIResponseT", bound="AsyncAPIResponse[Any]")

log: logging.Logger = logging.getLogger(__name__)


class BaseAPIResponse(Generic[R]):
    _cast_to: type[R]
    _client: BaseClient[Any, Any]
    _parsed_by_type: dict[type[Any], Any]
    _is_sse_stream: bool
    _stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None
    _options: FinalRequestOptions

    http_response: httpx.Response

    retries_taken: int
    """The number of retries made. If no retries happened this will be `0`"""

    def __init__(
        self,
        *,
        raw: httpx.Response,
        cast_to: type[R],
        client: BaseClient[Any, Any],
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        options: FinalRequestOptions,
        retries_taken: int = 0,
    ) -> None:
        self._cast_to = cast_to
        self._client = client
        self._parsed_by_type = {}
        self._is_sse_stream = stream
        self._stream_cls = stream_cls
        self._options = options
        self.http_response = raw
        self.retries_taken = retries_taken

    @property
    def headers(self) -> httpx.Headers:
        return self.http_response.headers

    @property
    def http_request(self) -> httpx.Request:
        """Returns the httpx Request instance associated with the current response."""
        return self.http_response.request

    @property
    def status_code(self) -> int:
        return self.http_response.status_code

    @property
    def url(self) -> httpx.URL:
        """Returns the URL for which the request was made."""
        return self.http_response.url

    @property
    def method(self) -> str:
        return self.http_request.method

    @property
    def http_version(self) -> str:
        return self.http_response.http_version

    @property
    def elapsed(self) -> datetime.timedelta:
        """The time taken for the complete request/response cycle to complete."""
        return self.http_response.elapsed

    @property
    def is_closed(self) -> bool:
        """Whether or not the response body has been closed.

        If this is False then there is response data that has not been read yet.
        You must either fully consume the response body or call `.close()`
        before discarding the response to prevent resource leaks.
        """
        return self.http_response.is_closed

    @override
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} [{self.status_code} {self.http_response.reason_phrase}] type={self._cast_to}>"
        )

    def _parse(self, *, to: type[_T] | None = None) -> R | _T:
        cast_to = to if to is not None else self._cast_to

        # unwrap `TypeAlias('Name', T)` -> `T`
        if is_type_alias_type(cast_to):
            cast_to = cast_to.__value__  # type: ignore[unreachable]

        # unwrap `Annotated[T, ...]` -> `T`
        if cast_to and is_annotated_type(cast_to):
            cast_to = extract_type_arg(cast_to, 0)

        origin = get_origin(cast_to) or cast_to

        if self._is_sse_stream:
            if to:
                if not is_stream_class_type(to):
                    raise TypeError(f"Expected custom parse type to be a subclass of {Stream} or {AsyncStream}")

                return cast(
                    _T,
                    to(
                        cast_to=extract_stream_chunk_type(
                            to,
                            failure_message="Expected custom stream type to be passed with a type argument, e.g. Stream[ChunkType]",
                        ),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            if self._stream_cls:
                return cast(
                    R,
                    self._stream_cls(
                        cast_to=extract_stream_chunk_type(self._stream_cls),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            stream_cls = cast("type[Stream[Any]] | type[AsyncStream[Any]] | None", self._client._default_stream_cls)
            if stream_cls is None:
                raise MissingStreamClassError()

            return cast(
                R,
                stream_cls(
                    cast_to=cast_to,
                    response=self.http_response,
                    client=cast(Any, self._client),
                ),
            )

        if cast_to is NoneType:
            return cast(R, None)

        response = self.http_response
        if cast_to == str:
            return cast(R, response.text)

        if cast_to == bytes:
            return cast(R, response.content)

        if cast_to == int:
            return cast(R, int(response.text))

        if cast_to == float:
            return cast(R, float(response.text))

        if cast_to == bool:
            return cast(R, response.text.lower() == "true")

        # handle the legacy binary response case
        if inspect.isclass(cast_to) and cast_to.__name__ == "HttpxBinaryResponseContent":
            return cast(R, cast_to(response))  # type: ignore

        if origin == APIResponse:
            raise RuntimeError("Unexpected state - cast_to is `APIResponse`")

        if inspect.isclass(origin) and issubclass(origin, httpx.Response):
            # Because of the invariance of our ResponseT TypeVar, users can subclass httpx.Response
            # and pass that class to our request functions. We cannot change the variance to be either
            # covariant or contravariant as that makes our usage of ResponseT illegal. We could construct
            # the response class ourselves but that is something that should be supported directly in httpx
            # as it would be easy to incorrectly construct the Response object due to the multitude of arguments.
            if cast_to != httpx.Response:
                raise ValueError(f"Subclasses of httpx.Response cannot be passed to `cast_to`")
            return cast(R, response)

        if (
            inspect.isclass(
                origin  # pyright: ignore[reportUnknownArgumentType]
            )
            and not issubclass(origin, BaseModel)
            and issubclass(origin, pydantic.BaseModel)
        ):
            raise TypeError("Pydantic models must subclass our base model type, e.g. `from openai import BaseModel`")

        if (
            cast_to is not object
            and not origin is list
            and not origin is dict
            and not origin is Union
            and not issubclass(origin, BaseModel)
        ):
            raise RuntimeError(
                f"Unsupported type, expected {cast_to} to be a subclass of {BaseModel}, {dict}, {list}, {Union}, {NoneType}, {str} or {httpx.Response}."
            )

        # split is required to handle cases where additional information is included
        # in the response, e.g. application/json; charset=utf-8
        content_type, *_ = response.headers.get("content-type", "*").split(";")
        if not content_type.endswith("json"):
            if is_basemodel(cast_to):
                try:
                    data = response.json()
                except Exception as exc:
                    log.debug("Could not read JSON from response data due to %s - %s", type(exc), exc)
                else:
                    return self._client._process_response_data(
                        data=data,
                        cast_to=cast_to,  # type: ignore
                        response=response,
                    )

            if self._client._strict_response_validation:
                raise APIResponseValidationError(
                    response=response,
                    message=f"Expected Content-Type response header to be `application/json` but received `{content_type}` instead.",
                    body=response.text,
                )

            # If the API responds with content that isn't JSON then we just return
            # the (decoded) text without performing any parsing so that you can still
            # handle the response however you need to.
            return response.text  # type: ignore

        data = response.json()

        return self._client._process_response_data(
            data=data,
            cast_to=cast_to,  # type: ignore
            response=response,
        )


class APIResponse(BaseAPIResponse[R]):
    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("x-request-id")  # type: ignore[no-any-return]

    @overload
    def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    def parse(self) -> R: ...

    def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from openai import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `int`
          - `float`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        if not self._is_sse_stream:
            self.read()

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        if isinstance(parsed, BaseModel):
            add_request_id(parsed, self.request_id)

        self._parsed_by_type[cache_key] = parsed
        return cast(R, parsed)

    def read(self) -> bytes:
        """Read and return the binary response content."""
        try:
            return self.http_response.read()
        except httpx.StreamConsumed as exc:
            # The default error raised by httpx isn't very
            # helpful in our case so we re-raise it with
            # a different error message.
            raise StreamAlreadyConsumed() from exc

    def text(self) -> str:
        """Read and decode the response content into a string."""
        self.read()
        return self.http_response.text

    def json(self) -> object:
        """Read and decode the JSON response content."""
        self.read()
        return self.http_response.json()

    def close(self) -> None:
        """Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.http_response.close()

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        """
        A byte-iterator over the decoded response content.

        This automatically handles gzip, deflate and brotli encoded responses.
        """
        for chunk in self.http_response.iter_bytes(chunk_size):
            yield chunk

    def iter_text(self, chunk_size: int | None = None) -> Iterator[str]:
        """A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        for chunk in self.http_response.iter_text(chunk_size):
            yield chunk

    def iter_lines(self) -> Iterator[str]:
        """Like `iter_text()` but will only yield chunks for each line"""
        for chunk in self.http_response.iter_lines():
            yield chunk


class AsyncAPIResponse(BaseAPIResponse[R]):
    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("x-request-id")  # type: ignore[no-any-return]

    @overload
    async def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    async def parse(self) -> R: ...

    async def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from openai import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        if not self._is_sse_stream:
            await self.read()

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        if isinstance(parsed, BaseModel):
            add_request_id(parsed, self.request_id)

        self._parsed_by_type[cache_key] = parsed
        return cast(R, parsed)

    async def read(self) -> bytes:
        """Read and return the binary response content."""
        try:
            return await self.http_response.aread()
        except httpx.StreamConsumed as exc:
            # the default error raised by httpx isn't very
            # helpful in our case so we re-raise it with
            # a different error message
            raise StreamAlreadyConsumed() from exc

    async def text(self) -> str:
        """Read and decode the response content into a string."""
        await self.read()
        return self.http_response.text

    async def json(self) -> object:
        """Read and decode the JSON response content."""
        await self.read()
        return self.http_response.json()

    async def close(self) -> None:
        """Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.http_response.aclose()

    async def iter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.

        This automatically handles gzip, deflate and brotli encoded responses.
        """
        async for chunk in self.http_response.aiter_bytes(chunk_size):
            yield chunk

    async def iter_text(self, chunk_size: int | None = None) -> AsyncIterator[str]:
        """A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        async for chunk in self.http_response.aiter_text(chunk_size):
            yield chunk

    async def iter_lines(self) -> AsyncIterator[str]:
        """Like `iter_text()` but will only yield chunks for each line"""
        async for chunk in self.http_response.aiter_lines():
            yield chunk


class BinaryAPIResponse(APIResponse[bytes]):
    """Subclass of APIResponse providing helpers for dealing with binary data.

    Note: If you want to stream the response data instead of eagerly reading it
    all at once then you should use `.with_streaming_response` when making
    the API request, e.g. `.with_streaming_response.get_binary_response()`
    """

    def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `.with_streaming_response.get_binary_response()`
        """
        with open(file, mode="wb") as f:
            for data in self.iter_bytes():
                f.write(data)


class AsyncBinaryAPIResponse(AsyncAPIResponse[bytes]):
    """Subclass of APIResponse providing helpers for dealing with binary data.

    Note: If you want to stream the response data instead of eagerly reading it
    all at once then you should use `.with_streaming_response` when making
    the API request, e.g. `.with_streaming_response.get_binary_response()`
    """

    async def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `.with_streaming_response.get_binary_response()`
        """
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.iter_bytes():
                await f.write(data)


class StreamedBinaryAPIResponse(APIResponse[bytes]):
    def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        """Streams the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path
        """
        with open(file, mode="wb") as f:
            for data in self.iter_bytes(chunk_size):
                f.write(data)


class AsyncStreamedBinaryAPIResponse(AsyncAPIResponse[bytes]):
    async def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        """Streams the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path
        """
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.iter_bytes(chunk_size):
                await f.write(data)


class MissingStreamClassError(TypeError):
    def __init__(self) -> None:
        super().__init__(
            "The `stream` argument was set to `True` but the `stream_cls` argument was not given. See `openai._streaming` for reference",
        )


class StreamAlreadyConsumed(OpenAIError):
    """
    Attempted to read or stream content, but the content has already
    been streamed.

    This can happen if you use a method like `.iter_lines()` and then attempt
    to read th entire response body afterwards, e.g.

    ```py
    response = await client.post(...)
    async for line in response.iter_lines():
        ...  # do something with `line`

    content = await response.read()
    # ^ error
    ```

    If you want this behaviour you'll need to either manually accumulate the response
    content or call `await response.read()` before iterating over the stream.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream some content, but the content has "
            "already been streamed. "
            "This could be due to attempting to stream the response "
            "content more than once."
            "\n\n"
            "You can fix this by manually accumulating the response content while streaming "
            "or by calling `.read()` before starting to stream."
        )
        super().__init__(message)


class ResponseContextManager(Generic[_APIResponseT]):
    """Context manager for ensuring that a request is not made
    until it is entered and that the response will always be closed
    when the context manager exits
    """

    def __init__(self, request_func: Callable[[], _APIResponseT]) -> None:
        self._request_func = request_func
        self.__response: _APIResponseT | None = None

    def __enter__(self) -> _APIResponseT:
        self.__response = self._request_func()
        return self.__response

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__response is not None:
            self.__response.close()


class AsyncResponseContextManager(Generic[_AsyncAPIResponseT]):
    """Context manager for ensuring that a request is not made
    until it is entered and that the response will always be closed
    when the context manager exits
    """

    def __init__(self, api_request: Awaitable[_AsyncAPIResponseT]) -> None:
        self._api_request = api_request
        self.__response: _AsyncAPIResponseT | None = None

    async def __aenter__(self) -> _AsyncAPIResponseT:
        self.__response = await self._api_request
        return self.__response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__response is not None:
            await self.__response.close()


def to_streamed_response_wrapper(func: Callable[P, R]) -> Callable[P, ResponseContextManager[APIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support streaming and returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseContextManager[APIResponse[R]]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"

        kwargs["extra_headers"] = extra_headers

        make_request = functools.partial(func, *args, **kwargs)

        return ResponseContextManager(cast(Callable[[], APIResponse[R]], make_request))

    return wrapped


def async_to_streamed_response_wrapper(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, AsyncResponseContextManager[AsyncAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support streaming and returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncResponseContextManager[AsyncAPIResponse[R]]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"

        kwargs["extra_headers"] = extra_headers

        make_request = func(*args, **kwargs)

        return AsyncResponseContextManager(cast(Awaitable[AsyncAPIResponse[R]], make_request))

    return wrapped


def to_custom_streamed_response_wrapper(
    func: Callable[P, object],
    response_cls: type[_APIResponseT],
) -> Callable[P, ResponseContextManager[_APIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support streaming and returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseContextManager[_APIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        make_request = functools.partial(func, *args, **kwargs)

        return ResponseContextManager(cast(Callable[[], _APIResponseT], make_request))

    return wrapped


def async_to_custom_streamed_response_wrapper(
    func: Callable[P, Awaitable[object]],
    response_cls: type[_AsyncAPIResponseT],
) -> Callable[P, AsyncResponseContextManager[_AsyncAPIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support streaming and returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncResponseContextManager[_AsyncAPIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "stream"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        make_request = func(*args, **kwargs)

        return AsyncResponseContextManager(cast(Awaitable[_AsyncAPIResponseT], make_request))

    return wrapped


def to_raw_response_wrapper(func: Callable[P, R]) -> Callable[P, APIResponse[R]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> APIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"

        kwargs["extra_headers"] = extra_headers

        return cast(APIResponse[R], func(*args, **kwargs))

    return wrapped


def async_to_raw_response_wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[AsyncAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> AsyncAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"

        kwargs["extra_headers"] = extra_headers

        return cast(AsyncAPIResponse[R], await func(*args, **kwargs))

    return wrapped


def to_custom_raw_response_wrapper(
    func: Callable[P, object],
    response_cls: type[_APIResponseT],
) -> Callable[P, _APIResponseT]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> _APIResponseT:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        return cast(_APIResponseT, func(*args, **kwargs))

    return wrapped


def async_to_custom_raw_response_wrapper(
    func: Callable[P, Awaitable[object]],
    response_cls: type[_AsyncAPIResponseT],
) -> Callable[P, Awaitable[_AsyncAPIResponseT]]:
    """Higher order function that takes one of our bound API methods and an `APIResponse` class
    and wraps the method to support returning the given response class directly.

    Note: the given `response_cls` *must* be concrete, e.g. `class BinaryAPIResponse(APIResponse[bytes])`
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> Awaitable[_AsyncAPIResponseT]:
        extra_headers: dict[str, Any] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "raw"
        extra_headers[OVERRIDE_CAST_TO_HEADER] = response_cls

        kwargs["extra_headers"] = extra_headers

        return cast(Awaitable[_AsyncAPIResponseT], func(*args, **kwargs))

    return wrapped


def extract_response_type(typ: type[BaseAPIResponse[Any]]) -> type:
    """Given a type like `APIResponse[T]`, returns the generic type variable `T`.

    This also handles the case where a concrete subclass is given, e.g.
    ```py
    class MyResponse(APIResponse[bytes]):
        ...

    extract_response_type(MyResponse) -> bytes
    ```
    """
    return extract_type_var_from_base(
        typ,
        generic_bases=cast("tuple[type, ...]", (BaseAPIResponse, APIResponse, AsyncAPIResponse)),
        index=0,
    )

# === NexusCore/openenv\Lib\site-packages\socks.py ===
from base64 import b64encode
try:
    from collections.abc import Callable
except ImportError:
    from collections import Callable
from errno import EOPNOTSUPP, EINVAL, EAGAIN
import functools
from io import BytesIO
import logging
import os
from os import SEEK_CUR
import socket
import struct
import sys

__version__ = "1.7.1"


if os.name == "nt" and sys.version_info < (3, 0):
    try:
        import win_inet_pton
    except ImportError:
        raise ImportError(
            "To run PySocks on Windows you must install win_inet_pton")

log = logging.getLogger(__name__)

PROXY_TYPE_SOCKS4 = SOCKS4 = 1
PROXY_TYPE_SOCKS5 = SOCKS5 = 2
PROXY_TYPE_HTTP = HTTP = 3

PROXY_TYPES = {"SOCKS4": SOCKS4, "SOCKS5": SOCKS5, "HTTP": HTTP}
PRINTABLE_PROXY_TYPES = dict(zip(PROXY_TYPES.values(), PROXY_TYPES.keys()))

_orgsocket = _orig_socket = socket.socket


def set_self_blocking(function):

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            _is_blocking = self.gettimeout()
            if _is_blocking == 0:
                self.setblocking(True)
            return function(*args, **kwargs)
        except Exception as e:
            raise
        finally:
            # set orgin blocking
            if _is_blocking == 0:
                self.setblocking(False)
    return wrapper


class ProxyError(IOError):
    """Socket_err contains original socket.error exception."""
    def __init__(self, msg, socket_err=None):
        self.msg = msg
        self.socket_err = socket_err

        if socket_err:
            self.msg += ": {}".format(socket_err)

    def __str__(self):
        return self.msg


class GeneralProxyError(ProxyError):
    pass


class ProxyConnectionError(ProxyError):
    pass


class SOCKS5AuthError(ProxyError):
    pass


class SOCKS5Error(ProxyError):
    pass


class SOCKS4Error(ProxyError):
    pass


class HTTPError(ProxyError):
    pass

SOCKS4_ERRORS = {
    0x5B: "Request rejected or failed",
    0x5C: ("Request rejected because SOCKS server cannot connect to identd on"
           " the client"),
    0x5D: ("Request rejected because the client program and identd report"
           " different user-ids")
}

SOCKS5_ERRORS = {
    0x01: "General SOCKS server failure",
    0x02: "Connection not allowed by ruleset",
    0x03: "Network unreachable",
    0x04: "Host unreachable",
    0x05: "Connection refused",
    0x06: "TTL expired",
    0x07: "Command not supported, or protocol error",
    0x08: "Address type not supported"
}

DEFAULT_PORTS = {SOCKS4: 1080, SOCKS5: 1080, HTTP: 8080}


def set_default_proxy(proxy_type=None, addr=None, port=None, rdns=True,
                      username=None, password=None):
    """Sets a default proxy.

    All further socksocket objects will use the default unless explicitly
    changed. All parameters are as for socket.set_proxy()."""
    socksocket.default_proxy = (proxy_type, addr, port, rdns,
                                username.encode() if username else None,
                                password.encode() if password else None)


def setdefaultproxy(*args, **kwargs):
    if "proxytype" in kwargs:
        kwargs["proxy_type"] = kwargs.pop("proxytype")
    return set_default_proxy(*args, **kwargs)


def get_default_proxy():
    """Returns the default proxy, set by set_default_proxy."""
    return socksocket.default_proxy

getdefaultproxy = get_default_proxy


def wrap_module(module):
    """Attempts to replace a module's socket library with a SOCKS socket.

    Must set a default proxy using set_default_proxy(...) first. This will
    only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category."""
    if socksocket.default_proxy:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError("No default proxy specified")

wrapmodule = wrap_module


def create_connection(dest_pair,
                      timeout=None, source_address=None,
                      proxy_type=None, proxy_addr=None,
                      proxy_port=None, proxy_rdns=True,
                      proxy_username=None, proxy_password=None,
                      socket_options=None):
    """create_connection(dest_pair, *[, timeout], **proxy_args) -> socket object

    Like socket.create_connection(), but connects to proxy
    before returning the socket object.

    dest_pair - 2-tuple of (IP/hostname, port).
    **proxy_args - Same args passed to socksocket.set_proxy() if present.
    timeout - Optional socket timeout value, in seconds.
    source_address - tuple (host, port) for the socket to bind to as its source
    address before connecting (only for compatibility)
    """
    # Remove IPv6 brackets on the remote address and proxy address.
    remote_host, remote_port = dest_pair
    if remote_host.startswith("["):
        remote_host = remote_host.strip("[]")
    if proxy_addr and proxy_addr.startswith("["):
        proxy_addr = proxy_addr.strip("[]")

    err = None

    # Allow the SOCKS proxy to be on IPv4 or IPv6 addresses.
    for r in socket.getaddrinfo(proxy_addr, proxy_port, 0, socket.SOCK_STREAM):
        family, socket_type, proto, canonname, sa = r
        sock = None
        try:
            sock = socksocket(family, socket_type, proto)

            if socket_options:
                for opt in socket_options:
                    sock.setsockopt(*opt)

            if isinstance(timeout, (int, float)):
                sock.settimeout(timeout)

            if proxy_type:
                sock.set_proxy(proxy_type, proxy_addr, proxy_port, proxy_rdns,
                               proxy_username, proxy_password)
            if source_address:
                sock.bind(source_address)

            sock.connect((remote_host, remote_port))
            return sock

        except (socket.error, ProxyError) as e:
            err = e
            if sock:
                sock.close()
                sock = None

    if err:
        raise err

    raise socket.error("gai returned empty list.")


class _BaseSocket(socket.socket):
    """Allows Python 2 delegated methods such as send() to be overridden."""
    def __init__(self, *pos, **kw):
        _orig_socket.__init__(self, *pos, **kw)

        self._savedmethods = dict()
        for name in self._savenames:
            self._savedmethods[name] = getattr(self, name)
            delattr(self, name)  # Allows normal overriding mechanism to work

    _savenames = list()


def _makemethod(name):
    return lambda self, *pos, **kw: self._savedmethods[name](*pos, **kw)
for name in ("sendto", "send", "recvfrom", "recv"):
    method = getattr(_BaseSocket, name, None)

    # Determine if the method is not defined the usual way
    # as a function in the class.
    # Python 2 uses __slots__, so there are descriptors for each method,
    # but they are not functions.
    if not isinstance(method, Callable):
        _BaseSocket._savenames.append(name)
        setattr(_BaseSocket, name, _makemethod(name))


class socksocket(_BaseSocket):
    """socksocket([family[, type[, proto]]]) -> socket object

    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET and proto=0.
    The "type" argument must be either SOCK_STREAM or SOCK_DGRAM.
    """

    default_proxy = None

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM,
                 proto=0, *args, **kwargs):
        if type not in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            msg = "Socket type must be stream or datagram, not {!r}"
            raise ValueError(msg.format(type))

        super(socksocket, self).__init__(family, type, proto, *args, **kwargs)
        self._proxyconn = None  # TCP connection to keep UDP relay alive

        if self.default_proxy:
            self.proxy = self.default_proxy
        else:
            self.proxy = (None, None, None, None, None, None)
        self.proxy_sockname = None
        self.proxy_peername = None

        self._timeout = None

    def _readall(self, file, count):
        """Receive EXACTLY the number of bytes requested from the file object.

        Blocks until the required number of bytes have been received."""
        data = b""
        while len(data) < count:
            d = file.read(count - len(data))
            if not d:
                raise GeneralProxyError("Connection closed unexpectedly")
            data += d
        return data

    def settimeout(self, timeout):
        self._timeout = timeout
        try:
            # test if we're connected, if so apply timeout
            peer = self.get_proxy_peername()
            super(socksocket, self).settimeout(self._timeout)
        except socket.error:
            pass

    def gettimeout(self):
        return self._timeout

    def setblocking(self, v):
        if v:
            self.settimeout(None)
        else:
            self.settimeout(0.0)

    def set_proxy(self, proxy_type=None, addr=None, port=None, rdns=True,
                  username=None, password=None):
        """ Sets the proxy to be used.

        proxy_type -  The type of the proxy to be used. Three types
                        are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                        PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                        servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be performed on the remote side
                       (rather than the local side). The default is True.
                       Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                       The default is no authentication.
        password -    Password to authenticate with to the server.
                       Only relevant when username is also provided."""
        self.proxy = (proxy_type, addr, port, rdns,
                      username.encode() if username else None,
                      password.encode() if password else None)

    def setproxy(self, *args, **kwargs):
        if "proxytype" in kwargs:
            kwargs["proxy_type"] = kwargs.pop("proxytype")
        return self.set_proxy(*args, **kwargs)

    def bind(self, *pos, **kw):
        """Implements proxy connection for UDP sockets.

        Happens during the bind() phase."""
        (proxy_type, proxy_addr, proxy_port, rdns, username,
         password) = self.proxy
        if not proxy_type or self.type != socket.SOCK_DGRAM:
            return _orig_socket.bind(self, *pos, **kw)

        if self._proxyconn:
            raise socket.error(EINVAL, "Socket already bound to an address")
        if proxy_type != SOCKS5:
            msg = "UDP only supported by SOCKS5 proxy type"
            raise socket.error(EOPNOTSUPP, msg)
        super(socksocket, self).bind(*pos, **kw)

        # Need to specify actual local port because
        # some relays drop packets if a port of zero is specified.
        # Avoid specifying host address in case of NAT though.
        _, port = self.getsockname()
        dst = ("0", port)

        self._proxyconn = _orig_socket()
        proxy = self._proxy_addr()
        self._proxyconn.connect(proxy)

        UDP_ASSOCIATE = b"\x03"
        _, relay = self._SOCKS5_request(self._proxyconn, UDP_ASSOCIATE, dst)

        # The relay is most likely on the same host as the SOCKS proxy,
        # but some proxies return a private IP address (10.x.y.z)
        host, _ = proxy
        _, port = relay
        super(socksocket, self).connect((host, port))
        super(socksocket, self).settimeout(self._timeout)
        self.proxy_sockname = ("0.0.0.0", 0)  # Unknown

    def sendto(self, bytes, *args, **kwargs):
        if self.type != socket.SOCK_DGRAM:
            return super(socksocket, self).sendto(bytes, *args, **kwargs)
        if not self._proxyconn:
            self.bind(("", 0))

        address = args[-1]
        flags = args[:-1]

        header = BytesIO()
        RSV = b"\x00\x00"
        header.write(RSV)
        STANDALONE = b"\x00"
        header.write(STANDALONE)
        self._write_SOCKS5_address(address, header)

        sent = super(socksocket, self).send(header.getvalue() + bytes, *flags,
                                            **kwargs)
        return sent - header.tell()

    def send(self, bytes, flags=0, **kwargs):
        if self.type == socket.SOCK_DGRAM:
            return self.sendto(bytes, flags, self.proxy_peername, **kwargs)
        else:
            return super(socksocket, self).send(bytes, flags, **kwargs)

    def recvfrom(self, bufsize, flags=0):
        if self.type != socket.SOCK_DGRAM:
            return super(socksocket, self).recvfrom(bufsize, flags)
        if not self._proxyconn:
            self.bind(("", 0))

        buf = BytesIO(super(socksocket, self).recv(bufsize + 1024, flags))
        buf.seek(2, SEEK_CUR)
        frag = buf.read(1)
        if ord(frag):
            raise NotImplementedError("Received UDP packet fragment")
        fromhost, fromport = self._read_SOCKS5_address(buf)

        if self.proxy_peername:
            peerhost, peerport = self.proxy_peername
            if fromhost != peerhost or peerport not in (0, fromport):
                raise socket.error(EAGAIN, "Packet filtered")

        return (buf.read(bufsize), (fromhost, fromport))

    def recv(self, *pos, **kw):
        bytes, _ = self.recvfrom(*pos, **kw)
        return bytes

    def close(self):
        if self._proxyconn:
            self._proxyconn.close()
        return super(socksocket, self).close()

    def get_proxy_sockname(self):
        """Returns the bound IP address and port number at the proxy."""
        return self.proxy_sockname

    getproxysockname = get_proxy_sockname

    def get_proxy_peername(self):
        """
        Returns the IP and port number of the proxy.
        """
        return self.getpeername()

    getproxypeername = get_proxy_peername

    def get_peername(self):
        """Returns the IP address and port number of the destination machine.

        Note: get_proxy_peername returns the proxy."""
        return self.proxy_peername

    getpeername = get_peername

    def _negotiate_SOCKS5(self, *dest_addr):
        """Negotiates a stream connection through a SOCKS5 server."""
        CONNECT = b"\x01"
        self.proxy_peername, self.proxy_sockname = self._SOCKS5_request(
            self, CONNECT, dest_addr)

    def _SOCKS5_request(self, conn, cmd, dst):
        """
        Send SOCKS5 request with given command (CMD field) and
        address (DST field). Returns resolved DST address that was used.
        """
        proxy_type, addr, port, rdns, username, password = self.proxy

        writer = conn.makefile("wb")
        reader = conn.makefile("rb", 0)  # buffering=0 renamed in Python 3
        try:
            # First we'll send the authentication packages we support.
            if username and password:
                # The username/password details were supplied to the
                # set_proxy method so we support the USERNAME/PASSWORD
                # authentication (in addition to the standard none).
                writer.write(b"\x05\x02\x00\x02")
            else:
                # No username/password were entered, therefore we
                # only support connections with no authentication.
                writer.write(b"\x05\x01\x00")

            # We'll receive the server's response to determine which
            # method was selected
            writer.flush()
            chosen_auth = self._readall(reader, 2)

            if chosen_auth[0:1] != b"\x05":
                # Note: string[i:i+1] is used because indexing of a bytestring
                # via bytestring[i] yields an integer in Python 3
                raise GeneralProxyError(
                    "SOCKS5 proxy server sent invalid data")

            # Check the chosen authentication method

            if chosen_auth[1:2] == b"\x02":
                # Okay, we need to perform a basic username/password
                # authentication.
                if not (username and password):
                    # Although we said we don't support authentication, the
                    # server may still request basic username/password
                    # authentication
                    raise SOCKS5AuthError("No username/password supplied. "
                                          "Server requested username/password"
                                          " authentication")

                writer.write(b"\x01" + chr(len(username)).encode()
                             + username
                             + chr(len(password)).encode()
                             + password)
                writer.flush()
                auth_status = self._readall(reader, 2)
                if auth_status[0:1] != b"\x01":
                    # Bad response
                    raise GeneralProxyError(
                        "SOCKS5 proxy server sent invalid data")
                if auth_status[1:2] != b"\x00":
                    # Authentication failed
                    raise SOCKS5AuthError("SOCKS5 authentication failed")

                # Otherwise, authentication succeeded

            # No authentication is required if 0x00
            elif chosen_auth[1:2] != b"\x00":
                # Reaching here is always bad
                if chosen_auth[1:2] == b"\xFF":
                    raise SOCKS5AuthError(
                        "All offered SOCKS5 authentication methods were"
                        " rejected")
                else:
                    raise GeneralProxyError(
                        "SOCKS5 proxy server sent invalid data")

            # Now we can request the actual connection
            writer.write(b"\x05" + cmd + b"\x00")
            resolved = self._write_SOCKS5_address(dst, writer)
            writer.flush()

            # Get the response
            resp = self._readall(reader, 3)
            if resp[0:1] != b"\x05":
                raise GeneralProxyError(
                    "SOCKS5 proxy server sent invalid data")

            status = ord(resp[1:2])
            if status != 0x00:
                # Connection failed: server returned an error
                error = SOCKS5_ERRORS.get(status, "Unknown error")
                raise SOCKS5Error("{:#04x}: {}".format(status, error))

            # Get the bound address/port
            bnd = self._read_SOCKS5_address(reader)

            super(socksocket, self).settimeout(self._timeout)
            return (resolved, bnd)
        finally:
            reader.close()
            writer.close()

    def _write_SOCKS5_address(self, addr, file):
        """
        Return the host and port packed for the SOCKS5 protocol,
        and the resolved address as a tuple object.
        """
        host, port = addr
        proxy_type, _, _, rdns, username, password = self.proxy
        family_to_byte = {socket.AF_INET: b"\x01", socket.AF_INET6: b"\x04"}

        # If the given destination address is an IP address, we'll
        # use the IP address request even if remote resolving was specified.
        # Detect whether the address is IPv4/6 directly.
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                addr_bytes = socket.inet_pton(family, host)
                file.write(family_to_byte[family] + addr_bytes)
                host = socket.inet_ntop(family, addr_bytes)
                file.write(struct.pack(">H", port))
                return host, port
            except socket.error:
                continue

        # Well it's not an IP number, so it's probably a DNS name.
        if rdns:
            # Resolve remotely
            host_bytes = host.encode("idna")
            file.write(b"\x03" + chr(len(host_bytes)).encode() + host_bytes)
        else:
            # Resolve locally
            addresses = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                           socket.SOCK_STREAM,
                                           socket.IPPROTO_TCP,
                                           socket.AI_ADDRCONFIG)
            # We can't really work out what IP is reachable, so just pick the
            # first.
            target_addr = addresses[0]
            family = target_addr[0]
            host = target_addr[4][0]

            addr_bytes = socket.inet_pton(family, host)
            file.write(family_to_byte[family] + addr_bytes)
            host = socket.inet_ntop(family, addr_bytes)
        file.write(struct.pack(">H", port))
        return host, port

    def _read_SOCKS5_address(self, file):
        atyp = self._readall(file, 1)
        if atyp == b"\x01":
            addr = socket.inet_ntoa(self._readall(file, 4))
        elif atyp == b"\x03":
            length = self._readall(file, 1)
            addr = self._readall(file, ord(length))
        elif atyp == b"\x04":
            addr = socket.inet_ntop(socket.AF_INET6, self._readall(file, 16))
        else:
            raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

        port = struct.unpack(">H", self._readall(file, 2))[0]
        return addr, port

    def _negotiate_SOCKS4(self, dest_addr, dest_port):
        """Negotiates a connection through a SOCKS4 server."""
        proxy_type, addr, port, rdns, username, password = self.proxy

        writer = self.makefile("wb")
        reader = self.makefile("rb", 0)  # buffering=0 renamed in Python 3
        try:
            # Check if the destination address provided is an IP address
            remote_resolve = False
            try:
                addr_bytes = socket.inet_aton(dest_addr)
            except socket.error:
                # It's a DNS name. Check where it should be resolved.
                if rdns:
                    addr_bytes = b"\x00\x00\x00\x01"
                    remote_resolve = True
                else:
                    addr_bytes = socket.inet_aton(
                        socket.gethostbyname(dest_addr))

            # Construct the request packet
            writer.write(struct.pack(">BBH", 0x04, 0x01, dest_port))
            writer.write(addr_bytes)

            # The username parameter is considered userid for SOCKS4
            if username:
                writer.write(username)
            writer.write(b"\x00")

            # DNS name if remote resolving is required
            # NOTE: This is actually an extension to the SOCKS4 protocol
            # called SOCKS4A and may not be supported in all cases.
            if remote_resolve:
                writer.write(dest_addr.encode("idna") + b"\x00")
            writer.flush()

            # Get the response from the server
            resp = self._readall(reader, 8)
            if resp[0:1] != b"\x00":
                # Bad data
                raise GeneralProxyError(
                    "SOCKS4 proxy server sent invalid data")

            status = ord(resp[1:2])
            if status != 0x5A:
                # Connection failed: server returned an error
                error = SOCKS4_ERRORS.get(status, "Unknown error")
                raise SOCKS4Error("{:#04x}: {}".format(status, error))

            # Get the bound address/port
            self.proxy_sockname = (socket.inet_ntoa(resp[4:]),
                                   struct.unpack(">H", resp[2:4])[0])
            if remote_resolve:
                self.proxy_peername = socket.inet_ntoa(addr_bytes), dest_port
            else:
                self.proxy_peername = dest_addr, dest_port
        finally:
            reader.close()
            writer.close()

    def _negotiate_HTTP(self, dest_addr, dest_port):
        """Negotiates a connection through an HTTP server.

        NOTE: This currently only supports HTTP CONNECT-style proxies."""
        proxy_type, addr, port, rdns, username, password = self.proxy

        # If we need to resolve locally, we do this now
        addr = dest_addr if rdns else socket.gethostbyname(dest_addr)

        http_headers = [
            (b"CONNECT " + addr.encode("idna") + b":"
             + str(dest_port).encode() + b" HTTP/1.1"),
            b"Host: " + dest_addr.encode("idna")
        ]

        if username and password:
            http_headers.append(b"Proxy-Authorization: basic "
                                + b64encode(username + b":" + password))

        http_headers.append(b"\r\n")

        self.sendall(b"\r\n".join(http_headers))

        # We just need the first line to check if the connection was successful
        fobj = self.makefile()
        status_line = fobj.readline()
        fobj.close()

        if not status_line:
            raise GeneralProxyError("Connection closed unexpectedly")

        try:
            proto, status_code, status_msg = status_line.split(" ", 2)
        except ValueError:
            raise GeneralProxyError("HTTP proxy server sent invalid response")

        if not proto.startswith("HTTP/"):
            raise GeneralProxyError(
                "Proxy server does not appear to be an HTTP proxy")

        try:
            status_code = int(status_code)
        except ValueError:
            raise HTTPError(
                "HTTP proxy server did not return a valid HTTP status")

        if status_code != 200:
            error = "{}: {}".format(status_code, status_msg)
            if status_code in (400, 403, 405):
                # It's likely that the HTTP proxy server does not support the
                # CONNECT tunneling method
                error += ("\n[*] Note: The HTTP proxy server may not be"
                          " supported by PySocks (must be a CONNECT tunnel"
                          " proxy)")
            raise HTTPError(error)

        self.proxy_sockname = (b"0.0.0.0", 0)
        self.proxy_peername = addr, dest_port

    _proxy_negotiators = {
                           SOCKS4: _negotiate_SOCKS4,
                           SOCKS5: _negotiate_SOCKS5,
                           HTTP: _negotiate_HTTP
                         }

    @set_self_blocking
    def connect(self, dest_pair, catch_errors=None):
        """
        Connects to the specified destination through a proxy.
        Uses the same API as socket's connect().
        To select the proxy server, use set_proxy().

        dest_pair - 2-tuple of (IP/hostname, port).
        """
        if len(dest_pair) != 2 or dest_pair[0].startswith("["):
            # Probably IPv6, not supported -- raise an error, and hope
            # Happy Eyeballs (RFC6555) makes sure at least the IPv4
            # connection works...
            raise socket.error("PySocks doesn't support IPv6: %s"
                               % str(dest_pair))

        dest_addr, dest_port = dest_pair

        if self.type == socket.SOCK_DGRAM:
            if not self._proxyconn:
                self.bind(("", 0))
            dest_addr = socket.gethostbyname(dest_addr)

            # If the host address is INADDR_ANY or similar, reset the peer
            # address so that packets are received from any peer
            if dest_addr == "0.0.0.0" and not dest_port:
                self.proxy_peername = None
            else:
                self.proxy_peername = (dest_addr, dest_port)
            return

        (proxy_type, proxy_addr, proxy_port, rdns, username,
         password) = self.proxy

        # Do a minimal input check first
        if (not isinstance(dest_pair, (list, tuple))
                or len(dest_pair) != 2
                or not dest_addr
                or not isinstance(dest_port, int)):
            # Inputs failed, raise an error
            raise GeneralProxyError(
                "Invalid destination-connection (host, port) pair")

        # We set the timeout here so that we don't hang in connection or during
        # negotiation.
        super(socksocket, self).settimeout(self._timeout)

        if proxy_type is None:
            # Treat like regular socket object
            self.proxy_peername = dest_pair
            super(socksocket, self).settimeout(self._timeout)
            super(socksocket, self).connect((dest_addr, dest_port))
            return

        proxy_addr = self._proxy_addr()

        try:
            # Initial connection to proxy server.
            super(socksocket, self).connect(proxy_addr)

        except socket.error as error:
            # Error while connecting to proxy
            self.close()
            if not catch_errors:
                proxy_addr, proxy_port = proxy_addr
                proxy_server = "{}:{}".format(proxy_addr, proxy_port)
                printable_type = PRINTABLE_PROXY_TYPES[proxy_type]

                msg = "Error connecting to {} proxy {}".format(printable_type,
                                                                    proxy_server)
                log.debug("%s due to: %s", msg, error)
                raise ProxyConnectionError(msg, error)
            else:
                raise error

        else:
            # Connected to proxy server, now negotiate
            try:
                # Calls negotiate_{SOCKS4, SOCKS5, HTTP}
                negotiate = self._proxy_negotiators[proxy_type]
                negotiate(self, dest_addr, dest_port)
            except socket.error as error:
                if not catch_errors:
                    # Wrap socket errors
                    self.close()
                    raise GeneralProxyError("Socket error", error)
                else:
                    raise error
            except ProxyError:
                # Protocol error while negotiating with proxy
                self.close()
                raise
                
    @set_self_blocking
    def connect_ex(self, dest_pair):
        """ https://docs.python.org/3/library/socket.html#socket.socket.connect_ex
        Like connect(address), but return an error indicator instead of raising an exception for errors returned by the C-level connect() call (other problems, such as "host not found" can still raise exceptions).
        """
        try:
            self.connect(dest_pair, catch_errors=True)
            return 0
        except OSError as e:
            # If the error is numeric (socket errors are numeric), then return number as 
            # connect_ex expects. Otherwise raise the error again (socket timeout for example)
            if e.errno:
                return e.errno
            else:
                raise

    def _proxy_addr(self):
        """
        Return proxy address to connect to as tuple object
        """
        (proxy_type, proxy_addr, proxy_port, rdns, username,
         password) = self.proxy
        proxy_port = proxy_port or DEFAULT_PORTS.get(proxy_type)
        if not proxy_port:
            raise GeneralProxyError("Invalid proxy type")
        return proxy_addr, proxy_port

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_constants.py ===
"""
This module holds the constants used for specifying the states of the debugger.
"""

from __future__ import nested_scopes
import platform
import weakref
import struct
import warnings
import functools
from contextlib import contextmanager

STATE_RUN = 1
STATE_SUSPEND = 2

PYTHON_SUSPEND = 1
DJANGO_SUSPEND = 2
JINJA2_SUSPEND = 3

int_types = (int,)

# types does not include a MethodWrapperType
try:
    MethodWrapperType = type([].__str__)
except:
    MethodWrapperType = None

import sys  # Note: the sys import must be here anyways (others depend on it)

# Preload codecs to avoid imports to them later on which can potentially halt the debugger.
import codecs as _codecs

for _codec in ["ascii", "utf8", "utf-8", "latin1", "latin-1", "idna"]:
    _codecs.lookup(_codec)


class DebugInfoHolder:
    # we have to put it here because it can be set through the command line (so, the
    # already imported references would not have it).

    # General information
    DEBUG_TRACE_LEVEL = 0  # 0 = critical, 1 = info, 2 = debug, 3 = verbose

    PYDEVD_DEBUG_FILE = None


# Any filename that starts with these strings is not traced nor shown to the user.
# In Python 3.7 "<frozen ..." appears multiple times during import and should be ignored for the user.
# In PyPy "<builtin> ..." can appear and should be ignored for the user.
# <attrs is used internally by attrs
# <__array_function__ is used by numpy
IGNORE_BASENAMES_STARTING_WITH = ("<frozen ", "<builtin", "<attrs", "<__array_function__")

# Note: <string> has special heuristics to know whether it should be traced or not (it's part of
# user code when it's the <string> used in python -c and part of the library otherwise).

# Any filename that starts with these strings is considered user (project) code. Note
# that files for which we have a source mapping are also considered as a part of the project.
USER_CODE_BASENAMES_STARTING_WITH = ("<ipython",)

# Any filename that starts with these strings is considered library code (note: checked after USER_CODE_BASENAMES_STARTING_WITH).
LIBRARY_CODE_BASENAMES_STARTING_WITH = ("<",)

IS_CPYTHON = platform.python_implementation() == "CPython"

# Hold a reference to the original _getframe (because psyco will change that as soon as it's imported)
IS_IRONPYTHON = sys.platform == "cli"
try:
    get_frame = sys._getframe
    if IS_IRONPYTHON:

        def get_frame():
            try:
                return sys._getframe()
            except ValueError:
                pass

except AttributeError:

    def get_frame():
        raise AssertionError("sys._getframe not available (possible causes: enable -X:Frames on IronPython?)")


# Used to determine the maximum size of each variable passed to eclipse -- having a big value here may make
# the communication slower -- as the variables are being gathered lazily in the latest version of eclipse,
# this value was raised from 200 to 1000.
MAXIMUM_VARIABLE_REPRESENTATION_SIZE = 1000
# Prefix for saving functions return values in locals
RETURN_VALUES_DICT = "__pydevd_ret_val_dict"
GENERATED_LEN_ATTR_NAME = "len()"

import os

from _pydevd_bundle import pydevd_vm_type

# Constant detects when running on Jython/windows properly later on.
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform in ("linux", "linux2")
IS_MAC = sys.platform == "darwin"
IS_WASM = sys.platform == "emscripten" or sys.platform == "wasi"

IS_64BIT_PROCESS = sys.maxsize > (2**32)

IS_JYTHON = pydevd_vm_type.get_vm_type() == pydevd_vm_type.PydevdVmType.JYTHON

IS_PYPY = platform.python_implementation() == "PyPy"

if IS_JYTHON:
    import java.lang.System  # @UnresolvedImport

    IS_WINDOWS = java.lang.System.getProperty("os.name").lower().startswith("windows")

USE_CUSTOM_SYS_CURRENT_FRAMES = not hasattr(sys, "_current_frames") or IS_PYPY
USE_CUSTOM_SYS_CURRENT_FRAMES_MAP = USE_CUSTOM_SYS_CURRENT_FRAMES and (IS_PYPY or IS_IRONPYTHON)

if USE_CUSTOM_SYS_CURRENT_FRAMES:
    # Some versions of Jython don't have it (but we can provide a replacement)
    if IS_JYTHON:
        from java.lang import NoSuchFieldException
        from org.python.core import ThreadStateMapping

        try:
            cachedThreadState = ThreadStateMapping.getDeclaredField("globalThreadStates")  # Dev version
        except NoSuchFieldException:
            cachedThreadState = ThreadStateMapping.getDeclaredField("cachedThreadState")  # Release Jython 2.7.0
        cachedThreadState.accessible = True
        thread_states = cachedThreadState.get(ThreadStateMapping)

        def _current_frames():
            as_array = thread_states.entrySet().toArray()
            ret = {}
            for thread_to_state in as_array:
                thread = thread_to_state.getKey()
                if thread is None:
                    continue
                thread_state = thread_to_state.getValue()
                if thread_state is None:
                    continue

                frame = thread_state.frame
                if frame is None:
                    continue

                ret[thread.getId()] = frame
            return ret

    elif USE_CUSTOM_SYS_CURRENT_FRAMES_MAP:
        constructed_tid_to_last_frame = {}

        # IronPython doesn't have it. Let's use our workaround...
        def _current_frames():
            return constructed_tid_to_last_frame

    else:
        raise RuntimeError("Unable to proceed (sys._current_frames not available in this Python implementation).")
else:
    _current_frames = sys._current_frames

IS_PYTHON_STACKLESS = "stackless" in sys.version.lower()
CYTHON_SUPPORTED = False

python_implementation = platform.python_implementation()
if python_implementation == "CPython":
    # Only available for CPython!
    CYTHON_SUPPORTED = True

# =======================================================================================================================
# Python 3?
# =======================================================================================================================
IS_PY36_OR_GREATER = sys.version_info >= (3, 6)
IS_PY37_OR_GREATER = sys.version_info >= (3, 7)
IS_PY38_OR_GREATER = sys.version_info >= (3, 8)
IS_PY39_OR_GREATER = sys.version_info >= (3, 9)
IS_PY310_OR_GREATER = sys.version_info >= (3, 10)
IS_PY311_OR_GREATER = sys.version_info >= (3, 11)
IS_PY312_OR_GREATER = sys.version_info >= (3, 12)
IS_PY313_OR_GREATER = sys.version_info >= (3, 13)
IS_PY314_OR_GREATER = sys.version_info >= (3, 14)

# Bug affecting Python 3.13.0 specifically makes some tests crash the interpreter!
# Hopefully it'll be fixed in 3.13.1.
IS_PY313_0 = sys.version_info[:3] == (3, 13, 0)

# Mark tests that need to be fixed with this.
TODO_PY313_OR_GREATER = IS_PY313_OR_GREATER

# Not currently supported in Python 3.14.
SUPPORT_ATTACH_TO_PID = not IS_PY314_OR_GREATER


def version_str(v):
    return ".".join((str(x) for x in v[:3])) + "".join((str(x) for x in v[3:]))


PY_VERSION_STR = version_str(sys.version_info)
try:
    PY_IMPL_VERSION_STR = version_str(sys.implementation.version)
except AttributeError:
    PY_IMPL_VERSION_STR = ""

try:
    PY_IMPL_NAME = sys.implementation.name
except AttributeError:
    PY_IMPL_NAME = ""

ENV_TRUE_LOWER_VALUES = ("yes", "true", "1")
ENV_FALSE_LOWER_VALUES = ("no", "false", "0")

PYDEVD_USE_SYS_MONITORING = IS_PY312_OR_GREATER and hasattr(sys, "monitoring")
if PYDEVD_USE_SYS_MONITORING:  # Default gotten, let's see if it was somehow customize by the user.
    _use_sys_monitoring_env_var = os.getenv("PYDEVD_USE_SYS_MONITORING", "").lower()
    if _use_sys_monitoring_env_var:
        # Check if the user specified something.
        if _use_sys_monitoring_env_var in ENV_FALSE_LOWER_VALUES:
            PYDEVD_USE_SYS_MONITORING = False
        elif _use_sys_monitoring_env_var in ENV_TRUE_LOWER_VALUES:
            PYDEVD_USE_SYS_MONITORING = True
        else:
            raise RuntimeError("Unrecognized value for PYDEVD_USE_SYS_MONITORING: %s" % (_use_sys_monitoring_env_var,))


def is_true_in_env(env_key):
    if isinstance(env_key, tuple):
        # If a tuple, return True if any of those ends up being true.
        for v in env_key:
            if is_true_in_env(v):
                return True
        return False
    else:
        return os.getenv(env_key, "").lower() in ENV_TRUE_LOWER_VALUES


def as_float_in_env(env_key, default):
    value = os.getenv(env_key)
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        raise RuntimeError("Error: expected the env variable: %s to be set to a float value. Found: %s" % (env_key, value))


def as_int_in_env(env_key, default):
    value = os.getenv(env_key)
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        raise RuntimeError("Error: expected the env variable: %s to be set to a int value. Found: %s" % (env_key, value))


# If true in env, use gevent mode.
SUPPORT_GEVENT = is_true_in_env("GEVENT_SUPPORT")

# Opt-in support to show gevent paused greenlets. False by default because if too many greenlets are
# paused the UI can slow-down (i.e.: if 1000 greenlets are paused, each one would be shown separate
# as a different thread, but if the UI isn't optimized for that the experience is lacking...).
GEVENT_SHOW_PAUSED_GREENLETS = is_true_in_env("GEVENT_SHOW_PAUSED_GREENLETS")

DISABLE_FILE_VALIDATION = is_true_in_env("PYDEVD_DISABLE_FILE_VALIDATION")

GEVENT_SUPPORT_NOT_SET_MSG = os.getenv(
    "GEVENT_SUPPORT_NOT_SET_MSG",
    "It seems that the gevent monkey-patching is being used.\n"
    "Please set an environment variable with:\n"
    "GEVENT_SUPPORT=True\n"
    "to enable gevent support in the debugger.",
)

USE_LIB_COPY = SUPPORT_GEVENT

INTERACTIVE_MODE_AVAILABLE = sys.platform in ("darwin", "win32") or os.getenv("DISPLAY") is not None

# If true in env, forces cython to be used (raises error if not available).
# If false in env, disables it.
# If not specified, uses default heuristic to determine if it should be loaded.
USE_CYTHON_FLAG = os.getenv("PYDEVD_USE_CYTHON")

if USE_CYTHON_FLAG is not None:
    USE_CYTHON_FLAG = USE_CYTHON_FLAG.lower()
    if USE_CYTHON_FLAG not in ENV_TRUE_LOWER_VALUES and USE_CYTHON_FLAG not in ENV_FALSE_LOWER_VALUES:
        raise RuntimeError(
            "Unexpected value for PYDEVD_USE_CYTHON: %s (enable with one of: %s, disable with one of: %s)"
            % (USE_CYTHON_FLAG, ENV_TRUE_LOWER_VALUES, ENV_FALSE_LOWER_VALUES)
        )

else:
    if not CYTHON_SUPPORTED:
        USE_CYTHON_FLAG = "no"

# If true in env, forces frame eval to be used (raises error if not available).
# If false in env, disables it.
# If not specified, uses default heuristic to determine if it should be loaded.
PYDEVD_USE_FRAME_EVAL = os.getenv("PYDEVD_USE_FRAME_EVAL", "").lower()

# Values used to determine how much container items will be shown.
# PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS:
#     - Defines how many items will appear initially expanded after which a 'more...' will appear.
#
# PYDEVD_CONTAINER_BUCKET_SIZE
#    - Defines the size of each bucket inside the 'more...' item
#        i.e.: a bucket with size == 2 would show items such as:
#            - [2:4]
#            - [4:6]
#            ...
#
# PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS
#    - Defines the maximum number of items for dicts and sets.
#
PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS = as_int_in_env("PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS", 100)
PYDEVD_CONTAINER_BUCKET_SIZE = as_int_in_env("PYDEVD_CONTAINER_BUCKET_SIZE", 1000)
PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS = as_int_in_env("PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS", 500)
PYDEVD_CONTAINER_NUMPY_MAX_ITEMS = as_int_in_env("PYDEVD_CONTAINER_NUMPY_MAX_ITEMS", 500)

PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING = is_true_in_env("PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING")

# If specified in PYDEVD_IPYTHON_CONTEXT it must be a string with the basename
# and then the name of 2 methods in which the evaluate is done.
PYDEVD_IPYTHON_CONTEXT = ("interactiveshell.py", "run_code", "run_ast_nodes")
_ipython_ctx = os.getenv("PYDEVD_IPYTHON_CONTEXT")
if _ipython_ctx:
    PYDEVD_IPYTHON_CONTEXT = tuple(x.strip() for x in _ipython_ctx.split(","))
    assert len(PYDEVD_IPYTHON_CONTEXT) == 3, "Invalid PYDEVD_IPYTHON_CONTEXT: %s" % (_ipython_ctx,)

# Use to disable loading the lib to set tracing to all threads (default is using heuristics based on where we're running).
LOAD_NATIVE_LIB_FLAG = os.getenv("PYDEVD_LOAD_NATIVE_LIB", "").lower()

LOG_TIME = os.getenv("PYDEVD_LOG_TIME", "true").lower() in ENV_TRUE_LOWER_VALUES

SHOW_COMPILE_CYTHON_COMMAND_LINE = is_true_in_env("PYDEVD_SHOW_COMPILE_CYTHON_COMMAND_LINE")

LOAD_VALUES_ASYNC = is_true_in_env("PYDEVD_LOAD_VALUES_ASYNC")
DEFAULT_VALUE = "__pydevd_value_async"
ASYNC_EVAL_TIMEOUT_SEC = 60
NEXT_VALUE_SEPARATOR = "__pydev_val__"
BUILTINS_MODULE_NAME = "builtins"

# Pandas customization.
PANDAS_MAX_ROWS = as_int_in_env("PYDEVD_PANDAS_MAX_ROWS", 60)
PANDAS_MAX_COLS = as_int_in_env("PYDEVD_PANDAS_MAX_COLS", 10)
PANDAS_MAX_COLWIDTH = as_int_in_env("PYDEVD_PANDAS_MAX_COLWIDTH", 50)

# If getting an attribute or computing some value is too slow, let the user know if the given timeout elapses.
PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT = as_float_in_env("PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT", 0.50)

# This timeout is used to track the time to send a message saying that the evaluation
# is taking too long and possible mitigations.
PYDEVD_WARN_EVALUATION_TIMEOUT = as_float_in_env("PYDEVD_WARN_EVALUATION_TIMEOUT", 3.0)

# If True in env shows a thread dump when the evaluation times out.
PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT = is_true_in_env("PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT")

# This timeout is used only when the mode that all threads are stopped/resumed at once is used
# (i.e.: multi_threads_single_notification)
#
# In this mode, if some evaluation doesn't finish until this timeout, we notify the user
# and then resume all threads until the evaluation finishes.
#
# A negative value will disable the timeout and a value of 0 will automatically run all threads
# (without any notification) when the evaluation is started and pause all threads when the
# evaluation is finished. A positive value will run run all threads after the timeout
# elapses.
PYDEVD_UNBLOCK_THREADS_TIMEOUT = as_float_in_env("PYDEVD_UNBLOCK_THREADS_TIMEOUT", -1.0)

# Timeout to interrupt a thread (so, if some evaluation doesn't finish until this
# timeout, the thread doing the evaluation is interrupted).
# A value <= 0 means this is disabled.
# See: _pydevd_bundle.pydevd_timeout.create_interrupt_this_thread_callback for details
# on how the thread interruption works (there are some caveats related to it).
PYDEVD_INTERRUPT_THREAD_TIMEOUT = as_float_in_env("PYDEVD_INTERRUPT_THREAD_TIMEOUT", -1)

# If PYDEVD_APPLY_PATCHING_TO_HIDE_PYDEVD_THREADS is set to False, the patching to hide pydevd threads won't be applied.
PYDEVD_APPLY_PATCHING_TO_HIDE_PYDEVD_THREADS = (
    os.getenv("PYDEVD_APPLY_PATCHING_TO_HIDE_PYDEVD_THREADS", "true").lower() in ENV_TRUE_LOWER_VALUES
)

EXCEPTION_TYPE_UNHANDLED = "UNHANDLED"
EXCEPTION_TYPE_USER_UNHANDLED = "USER_UNHANDLED"
EXCEPTION_TYPE_HANDLED = "HANDLED"

SHOW_DEBUG_INFO_ENV = is_true_in_env(("PYCHARM_DEBUG", "PYDEV_DEBUG", "PYDEVD_DEBUG"))

if SHOW_DEBUG_INFO_ENV:
    # show debug info before the debugger start
    DebugInfoHolder.DEBUG_TRACE_LEVEL = 3

DebugInfoHolder.PYDEVD_DEBUG_FILE = os.getenv("PYDEVD_DEBUG_FILE")


def protect_libraries_from_patching():
    """
    In this function we delete some modules from `sys.modules` dictionary and import them again inside
      `_pydev_saved_modules` in order to save their original copies there. After that we can use these
      saved modules within the debugger to protect them from patching by external libraries (e.g. gevent).
    """
    patched = [
        "threading",
        "thread",
        "_thread",
        "time",
        "socket",
        "queue",
        "select",
        "xmlrpclib",
        "SimpleXMLRPCServer",
        "BaseHTTPServer",
        "SocketServer",
        "xmlrpc.client",
        "xmlrpc.server",
        "http.server",
        "socketserver",
    ]

    for name in patched:
        try:
            __import__(name)
        except:
            pass

    patched_modules = dict([(k, v) for k, v in sys.modules.items() if k in patched])

    for name in patched_modules:
        del sys.modules[name]

    # import for side effects
    import _pydev_bundle._pydev_saved_modules

    for name in patched_modules:
        sys.modules[name] = patched_modules[name]


if USE_LIB_COPY:
    protect_libraries_from_patching()

from _pydev_bundle._pydev_saved_modules import thread, threading

_fork_safe_locks = []

if IS_JYTHON:

    def ForkSafeLock(rlock=False):
        if rlock:
            return threading.RLock()
        else:
            return threading.Lock()

else:

    class ForkSafeLock(object):
        """
        A lock which is fork-safe (when a fork is done, `pydevd_constants.after_fork()`
        should be called to reset the locks in the new process to avoid deadlocks
        from a lock which was locked during the fork).

        Note:
            Unlike `threading.Lock` this class is not completely atomic, so, doing:

            lock = ForkSafeLock()
            with lock:
                ...

            is different than using `threading.Lock` directly because the tracing may
            find an additional function call on `__enter__` and on `__exit__`, so, it's
            not recommended to use this in all places, only where the forking may be important
            (so, for instance, the locks on PyDB should not be changed to this lock because
            of that -- and those should all be collected in the new process because PyDB itself
            should be completely cleared anyways).

            It's possible to overcome this limitation by using `ForkSafeLock.acquire` and
            `ForkSafeLock.release` instead of the context manager (as acquire/release are
            bound to the original implementation, whereas __enter__/__exit__ is not due to Python
            limitations).
        """

        def __init__(self, rlock=False):
            self._rlock = rlock
            self._init()
            _fork_safe_locks.append(weakref.ref(self))

        def __enter__(self):
            return self._lock.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._lock.__exit__(exc_type, exc_val, exc_tb)

        def _init(self):
            if self._rlock:
                self._lock = threading.RLock()
            else:
                self._lock = thread.allocate_lock()

            self.acquire = self._lock.acquire
            self.release = self._lock.release
            _fork_safe_locks.append(weakref.ref(self))


def after_fork():
    """
    Must be called after a fork operation (will reset the ForkSafeLock).
    """
    global _fork_safe_locks
    locks = _fork_safe_locks[:]
    _fork_safe_locks = []
    for lock in locks:
        lock = lock()
        if lock is not None:
            lock._init()


_thread_id_lock = ForkSafeLock()
thread_get_ident = thread.get_ident


def as_str(s):
    assert isinstance(s, str)
    return s


@contextmanager
def filter_all_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        yield


def silence_warnings_decorator(func):
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        with filter_all_warnings():
            return func(*args, **kwargs)

    return new_func


def sorted_dict_repr(d):
    s = sorted(d.items(), key=lambda x: str(x[0]))
    return "{" + ", ".join(("%r: %r" % x) for x in s) + "}"


def iter_chars(b):
    # In Python 2, we can iterate bytes or str with individual characters, but Python 3 onwards
    # changed that behavior so that when iterating bytes we actually get ints!
    if isinstance(b, bytes):
        # i.e.: do something as struct.unpack('3c', b)
        return iter(struct.unpack(str(len(b)) + "c", b))
    return iter(b)


if IS_JYTHON or PYDEVD_USE_SYS_MONITORING:

    def NO_FTRACE(frame, event, arg):
        return None

else:
    _curr_trace = sys.gettrace()

    # Set a temporary trace which does nothing for us to test (otherwise setting frame.f_trace has no
    # effect).
    def _temp_trace(frame, event, arg):
        return None

    sys.settrace(_temp_trace)

    def _check_ftrace_set_none():
        """
        Will throw an error when executing a line event
        """
        sys._getframe().f_trace = None
        _line_event = 1
        _line_event = 2

    try:
        _check_ftrace_set_none()

        def NO_FTRACE(frame, event, arg):
            frame.f_trace = None
            return None

    except TypeError:

        def NO_FTRACE(frame, event, arg):
            # In Python <= 2.6 and <= 3.4, if we're tracing a method, frame.f_trace may not be set
            # to None, it must always be set to a tracing function.
            # See: tests_python.test_tracing_gotchas.test_tracing_gotchas
            #
            # Note: Python 2.7 sometimes works and sometimes it doesn't depending on the minor
            # version because of https://bugs.python.org/issue20041 (although bug reports didn't
            # include the minor version, so, mark for any Python 2.7 as I'm not completely sure
            # the fix in later 2.7 versions is the same one we're dealing with).
            return None

    sys.settrace(_curr_trace)


# =======================================================================================================================
# get_pid
# =======================================================================================================================
def get_pid():
    try:
        return os.getpid()
    except AttributeError:
        try:
            # Jython does not have it!
            import java.lang.management.ManagementFactory  # @UnresolvedImport -- just for jython

            pid = java.lang.management.ManagementFactory.getRuntimeMXBean().getName()
            return pid.replace("@", "_")
        except:
            # ok, no pid available (will be unable to debug multiple processes)
            return "000001"


def clear_cached_thread_id(thread):
    with _thread_id_lock:
        try:
            if thread.__pydevd_id__ != "console_main":
                # The console_main is a special thread id used in the console and its id should never be reset
                # (otherwise we may no longer be able to get its variables -- see: https://www.brainwy.com/tracker/PyDev/776).
                del thread.__pydevd_id__
        except AttributeError:
            pass


# Don't let threads be collected (so that id(thread) is guaranteed to be unique).
_thread_id_to_thread_found = {}


def _get_or_compute_thread_id_with_lock(thread, is_current_thread):
    with _thread_id_lock:
        # We do a new check with the lock in place just to be sure that nothing changed
        tid = getattr(thread, "__pydevd_id__", None)
        if tid is not None:
            return tid

        _thread_id_to_thread_found[id(thread)] = thread

        # Note: don't use thread.ident because a new thread may have the
        # same id from an old thread.
        pid = get_pid()
        tid = "pid_%s_id_%s" % (pid, id(thread))

        thread.__pydevd_id__ = tid

    return tid


def get_current_thread_id(thread):
    """
    Note: the difference from get_current_thread_id to get_thread_id is that
    for the current thread we can get the thread id while the thread.ident
    is still not set in the Thread instance.
    """
    try:
        # Fast path without getting lock.
        tid = thread.__pydevd_id__
        if tid is None:
            # Fix for https://www.brainwy.com/tracker/PyDev/645
            # if __pydevd_id__ is None, recalculate it... also, use an heuristic
            # that gives us always the same id for the thread (using thread.ident or id(thread)).
            raise AttributeError()
    except AttributeError:
        tid = _get_or_compute_thread_id_with_lock(thread, is_current_thread=True)

    return tid


def get_thread_id(thread):
    try:
        # Fast path without getting lock.
        tid = thread.__pydevd_id__
        if tid is None:
            # Fix for https://www.brainwy.com/tracker/PyDev/645
            # if __pydevd_id__ is None, recalculate it... also, use an heuristic
            # that gives us always the same id for the thread (using thread.ident or id(thread)).
            raise AttributeError()
    except AttributeError:
        tid = _get_or_compute_thread_id_with_lock(thread, is_current_thread=False)

    return tid


def set_thread_id(thread, thread_id):
    with _thread_id_lock:
        thread.__pydevd_id__ = thread_id


# =======================================================================================================================
# Null
# =======================================================================================================================
class Null:
    """
    Gotten from: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/68205
    """

    def __init__(self, *args, **kwargs):
        return None

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        return self

    def __getattr__(self, mname):
        if len(mname) > 4 and mname[:2] == "__" and mname[-2:] == "__":
            # Don't pretend to implement special method names.
            raise AttributeError(mname)
        return self

    def __setattr__(self, name, value):
        return self

    def __delattr__(self, name):
        return self

    def __repr__(self):
        return "<Null>"

    def __str__(self):
        return "Null"

    def __len__(self):
        return 0

    def __getitem__(self):
        return self

    def __setitem__(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass

    def __nonzero__(self):
        return 0

    def __iter__(self):
        return iter(())


# Default instance
NULL = Null()


class KeyifyList(object):
    def __init__(self, inner, key):
        self.inner = inner
        self.key = key

    def __len__(self):
        return len(self.inner)

    def __getitem__(self, k):
        return self.key(self.inner[k])


def call_only_once(func):
    """
    To be used as a decorator

    @call_only_once
    def func():
        print 'Calling func only this time'

    Actually, in PyDev it must be called as:

    func = call_only_once(func) to support older versions of Python.
    """

    def new_func(*args, **kwargs):
        if not new_func._called:
            new_func._called = True
            return func(*args, **kwargs)

    new_func._called = False
    return new_func


# Protocol where each line is a new message (text is quoted to prevent new lines).
# payload is xml
QUOTED_LINE_PROTOCOL = "quoted-line"
ARGUMENT_QUOTED_LINE_PROTOCOL = "protocol-quoted-line"

# Uses http protocol to provide a new message.
# i.e.: Content-Length:xxx\r\n\r\npayload
# payload is xml
HTTP_PROTOCOL = "http"
ARGUMENT_HTTP_PROTOCOL = "protocol-http"

# Message is sent without any header.
# payload is json
JSON_PROTOCOL = "json"
ARGUMENT_JSON_PROTOCOL = "json-dap"

# Same header as the HTTP_PROTOCOL
# payload is json
HTTP_JSON_PROTOCOL = "http_json"
ARGUMENT_HTTP_JSON_PROTOCOL = "json-dap-http"

ARGUMENT_PPID = "ppid"


class _GlobalSettings:
    protocol = QUOTED_LINE_PROTOCOL


def set_protocol(protocol):
    expected = (HTTP_PROTOCOL, QUOTED_LINE_PROTOCOL, JSON_PROTOCOL, HTTP_JSON_PROTOCOL)
    assert protocol in expected, "Protocol (%s) should be one of: %s" % (protocol, expected)

    _GlobalSettings.protocol = protocol


def get_protocol():
    return _GlobalSettings.protocol


def is_json_protocol():
    return _GlobalSettings.protocol in (JSON_PROTOCOL, HTTP_JSON_PROTOCOL)


class GlobalDebuggerHolder:
    """
    Holder for the global debugger.
    """

    global_dbg = None  # Note: don't rename (the name is used in our attach to process)


def get_global_debugger():
    return GlobalDebuggerHolder.global_dbg


GetGlobalDebugger = get_global_debugger  # Backward-compatibility


def set_global_debugger(dbg):
    GlobalDebuggerHolder.global_dbg = dbg


if __name__ == "__main__":
    if Null():
        sys.stdout.write("here\n")

# === NexusCore/openenv\Lib\site-packages\google\oauth2\service_account.py ===
# Copyright 2016 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Service Accounts: JSON Web Token (JWT) Profile for OAuth 2.0

This module implements the JWT Profile for OAuth 2.0 Authorization Grants
as defined by `RFC 7523`_ with particular support for how this RFC is
implemented in Google's infrastructure. Google refers to these credentials
as *Service Accounts*.

Service accounts are used for server-to-server communication, such as
interactions between a web application server and a Google service. The
service account belongs to your application instead of to an individual end
user. In contrast to other OAuth 2.0 profiles, no users are involved and your
application "acts" as the service account.

Typically an application uses a service account when the application uses
Google APIs to work with its own data rather than a user's data. For example,
an application that uses Google Cloud Datastore for data persistence would use
a service account to authenticate its calls to the Google Cloud Datastore API.
However, an application that needs to access a user's Drive documents would
use the normal OAuth 2.0 profile.

Additionally, Google Apps domain administrators can grant service accounts
`domain-wide delegation`_ authority to access user data on behalf of users in
the domain.

This profile uses a JWT to acquire an OAuth 2.0 access token. The JWT is used
in place of the usual authorization token returned during the standard
OAuth 2.0 Authorization Code grant. The JWT is only used for this purpose, as
the acquired access token is used as the bearer token when making requests
using these credentials.

This profile differs from normal OAuth 2.0 profile because no user consent
step is required. The use of the private key allows this profile to assert
identity directly.

This profile also differs from the :mod:`google.auth.jwt` authentication
because the JWT credentials use the JWT directly as the bearer token. This
profile instead only uses the JWT to obtain an OAuth 2.0 access token. The
obtained OAuth 2.0 access token is used as the bearer token.

Domain-wide delegation
----------------------

Domain-wide delegation allows a service account to access user data on
behalf of any user in a Google Apps domain without consent from the user.
For example, an application that uses the Google Calendar API to add events to
the calendars of all users in a Google Apps domain would use a service account
to access the Google Calendar API on behalf of users.

The Google Apps administrator must explicitly authorize the service account to
do this. This authorization step is referred to as "delegating domain-wide
authority" to a service account.

You can use domain-wise delegation by creating a set of credentials with a
specific subject using :meth:`~Credentials.with_subject`.

.. _RFC 7523: https://tools.ietf.org/html/rfc7523
"""

import copy
import datetime

from google.auth import _helpers
from google.auth import _service_account_info
from google.auth import credentials
from google.auth import exceptions
from google.auth import iam
from google.auth import jwt
from google.auth import metrics
from google.oauth2 import _client

_DEFAULT_TOKEN_LIFETIME_SECS = 3600  # 1 hour in seconds
_GOOGLE_OAUTH2_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class Credentials(
    credentials.Signing,
    credentials.Scoped,
    credentials.CredentialsWithQuotaProject,
    credentials.CredentialsWithTokenUri,
):
    """Service account credentials

    Usually, you'll create these credentials with one of the helper
    constructors. To create credentials using a Google service account
    private key JSON file::

        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json')

    Or if you already have the service account file loaded::

        service_account_info = json.load(open('service_account.json'))
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info)

    Both helper methods pass on arguments to the constructor, so you can
    specify additional scopes and a subject if necessary::

        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json',
            scopes=['email'],
            subject='user@example.com')

    The credentials are considered immutable. If you want to modify the scopes
    or the subject used for delegation, use :meth:`with_scopes` or
    :meth:`with_subject`::

        scoped_credentials = credentials.with_scopes(['email'])
        delegated_credentials = credentials.with_subject(subject)

    To add a quota project, use :meth:`with_quota_project`::

        credentials = credentials.with_quota_project('myproject-123')
    """

    def __init__(
        self,
        signer,
        service_account_email,
        token_uri,
        scopes=None,
        default_scopes=None,
        subject=None,
        project_id=None,
        quota_project_id=None,
        additional_claims=None,
        always_use_jwt_access=False,
        universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
        trust_boundary=None,
    ):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            service_account_email (str): The service account's email.
            scopes (Sequence[str]): User-defined scopes to request during the
                authorization grant.
            default_scopes (Sequence[str]): Default scopes passed by a
                Google client library. Use 'scopes' for user-defined scopes.
            token_uri (str): The OAuth 2.0 Token URI.
            subject (str): For domain-wide delegation, the email address of the
                user to for which to request delegated access.
            project_id  (str): Project ID associated with the service account
                credential.
            quota_project_id (Optional[str]): The project ID used for quota and
                billing.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT assertion used in the authorization grant.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be always used.
            universe_domain (str): The universe domain. The default
                universe domain is googleapis.com. For default value self
                signed jwt is used for token refresh.
            trust_boundary (str): String representation of trust boundary meta.

        .. note:: Typically one of the helper constructors
            :meth:`from_service_account_file` or
            :meth:`from_service_account_info` are used instead of calling the
            constructor directly.
        """
        super(Credentials, self).__init__()

        self._cred_file_path = None
        self._scopes = scopes
        self._default_scopes = default_scopes
        self._signer = signer
        self._service_account_email = service_account_email
        self._subject = subject
        self._project_id = project_id
        self._quota_project_id = quota_project_id
        self._token_uri = token_uri
        self._always_use_jwt_access = always_use_jwt_access
        self._universe_domain = universe_domain or credentials.DEFAULT_UNIVERSE_DOMAIN

        if universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN:
            self._always_use_jwt_access = True

        self._jwt_credentials = None

        if additional_claims is not None:
            self._additional_claims = additional_claims
        else:
            self._additional_claims = {}
        self._trust_boundary = {"locations": [], "encoded_locations": "0x0"}

    @classmethod
    def _from_signer_and_info(cls, signer, info, **kwargs):
        """Creates a Credentials instance from a signer and service account
        info.

        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            info (Mapping[str, str]): The service account info.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: The constructed credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        return cls(
            signer,
            service_account_email=info["client_email"],
            token_uri=info["token_uri"],
            project_id=info.get("project_id"),
            universe_domain=info.get(
                "universe_domain", credentials.DEFAULT_UNIVERSE_DOMAIN
            ),
            trust_boundary=info.get("trust_boundary"),
            **kwargs,
        )

    @classmethod
    def from_service_account_info(cls, info, **kwargs):
        """Creates a Credentials instance from parsed service account info.

        Args:
            info (Mapping[str, str]): The service account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.service_account.Credentials: The constructed
                credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        signer = _service_account_info.from_dict(
            info, require=["client_email", "token_uri"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename, **kwargs):
        """Creates a Credentials instance from a service account json file.

        Args:
            filename (str): The path to the service account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.service_account.Credentials: The constructed
                credentials.
        """
        info, signer = _service_account_info.from_filename(
            filename, require=["client_email", "token_uri"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    @property
    def service_account_email(self):
        """The service account email."""
        return self._service_account_email

    @property
    def project_id(self):
        """Project ID associated with this credential."""
        return self._project_id

    @property
    def requires_scopes(self):
        """Checks if the credentials requires scopes.

        Returns:
            bool: True if there are no scopes set otherwise False.
        """
        return True if not self._scopes else False

    def _make_copy(self):
        cred = self.__class__(
            self._signer,
            service_account_email=self._service_account_email,
            scopes=copy.copy(self._scopes),
            default_scopes=copy.copy(self._default_scopes),
            token_uri=self._token_uri,
            subject=self._subject,
            project_id=self._project_id,
            quota_project_id=self._quota_project_id,
            additional_claims=self._additional_claims.copy(),
            always_use_jwt_access=self._always_use_jwt_access,
            universe_domain=self._universe_domain,
        )
        cred._cred_file_path = self._cred_file_path
        return cred

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes, default_scopes=None):
        cred = self._make_copy()
        cred._scopes = scopes
        cred._default_scopes = default_scopes
        return cred

    def with_always_use_jwt_access(self, always_use_jwt_access):
        """Create a copy of these credentials with the specified always_use_jwt_access value.

        Args:
            always_use_jwt_access (bool): Whether always use self signed JWT or not.

        Returns:
            google.auth.service_account.Credentials: A new credentials
                instance.
        Raises:
            google.auth.exceptions.InvalidValue: If the universe domain is not
                default and always_use_jwt_access is False.
        """
        cred = self._make_copy()
        if (
            cred._universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN
            and not always_use_jwt_access
        ):
            raise exceptions.InvalidValue(
                "always_use_jwt_access should be True for non-default universe domain"
            )
        cred._always_use_jwt_access = always_use_jwt_access
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithUniverseDomain)
    def with_universe_domain(self, universe_domain):
        cred = self._make_copy()
        cred._universe_domain = universe_domain
        if universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN:
            cred._always_use_jwt_access = True
        return cred

    def with_subject(self, subject):
        """Create a copy of these credentials with the specified subject.

        Args:
            subject (str): The subject claim.

        Returns:
            google.auth.service_account.Credentials: A new credentials
                instance.
        """
        cred = self._make_copy()
        cred._subject = subject
        return cred

    def with_claims(self, additional_claims):
        """Returns a copy of these credentials with modified claims.

        Args:
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload. This will be merged with the current
                additional claims.

        Returns:
            google.auth.service_account.Credentials: A new credentials
                instance.
        """
        new_additional_claims = copy.deepcopy(self._additional_claims)
        new_additional_claims.update(additional_claims or {})
        cred = self._make_copy()
        cred._additional_claims = new_additional_claims
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        cred = self._make_copy()
        cred._quota_project_id = quota_project_id
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithTokenUri)
    def with_token_uri(self, token_uri):
        cred = self._make_copy()
        cred._token_uri = token_uri
        return cred

    def _make_authorization_grant_assertion(self):
        """Create the OAuth 2.0 assertion.

        This assertion is used during the OAuth 2.0 grant to acquire an
        access token.

        Returns:
            bytes: The authorization grant assertion.
        """
        now = _helpers.utcnow()
        lifetime = datetime.timedelta(seconds=_DEFAULT_TOKEN_LIFETIME_SECS)
        expiry = now + lifetime

        payload = {
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
            # The issuer must be the service account email.
            "iss": self._service_account_email,
            # The audience must be the auth token endpoint's URI
            "aud": _GOOGLE_OAUTH2_TOKEN_ENDPOINT,
            "scope": _helpers.scopes_to_string(self._scopes or ()),
        }

        payload.update(self._additional_claims)

        # The subject can be a user email for domain-wide delegation.
        if self._subject:
            payload.setdefault("sub", self._subject)

        token = jwt.encode(self._signer, payload)

        return token

    def _use_self_signed_jwt(self):
        # Since domain wide delegation doesn't work with self signed JWT. If
        # subject exists, then we should not use self signed JWT.
        return self._subject is None and self._jwt_credentials is not None

    def _metric_header_for_usage(self):
        if self._use_self_signed_jwt():
            return metrics.CRED_TYPE_SA_JWT
        return metrics.CRED_TYPE_SA_ASSERTION

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        if self._always_use_jwt_access and not self._jwt_credentials:
            # If self signed jwt should be used but jwt credential is not
            # created, try to create one with scopes
            self._create_self_signed_jwt(None)

        if (
            self._universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN
            and self._subject
        ):
            raise exceptions.RefreshError(
                "domain wide delegation is not supported for non-default universe domain"
            )

        if self._use_self_signed_jwt():
            self._jwt_credentials.refresh(request)
            self.token = self._jwt_credentials.token.decode()
            self.expiry = self._jwt_credentials.expiry
        else:
            assertion = self._make_authorization_grant_assertion()
            access_token, expiry, _ = _client.jwt_grant(
                request, self._token_uri, assertion
            )
            self.token = access_token
            self.expiry = expiry

    def _create_self_signed_jwt(self, audience):
        """Create a self-signed JWT from the credentials if requirements are met.

        Args:
            audience (str): The service URL. ``https://[API_ENDPOINT]/``
        """
        # https://google.aip.dev/auth/4111
        if self._always_use_jwt_access:
            if self._scopes:
                additional_claims = {"scope": " ".join(self._scopes)}
                if (
                    self._jwt_credentials is None
                    or self._jwt_credentials.additional_claims != additional_claims
                ):
                    self._jwt_credentials = jwt.Credentials.from_signing_credentials(
                        self, None, additional_claims=additional_claims
                    )
            elif audience:
                if (
                    self._jwt_credentials is None
                    or self._jwt_credentials._audience != audience
                ):

                    self._jwt_credentials = jwt.Credentials.from_signing_credentials(
                        self, audience
                    )
            elif self._default_scopes:
                additional_claims = {"scope": " ".join(self._default_scopes)}
                if (
                    self._jwt_credentials is None
                    or additional_claims != self._jwt_credentials.additional_claims
                ):
                    self._jwt_credentials = jwt.Credentials.from_signing_credentials(
                        self, None, additional_claims=additional_claims
                    )
        elif not self._scopes and audience:
            self._jwt_credentials = jwt.Credentials.from_signing_credentials(
                self, audience
            )

    @_helpers.copy_docstring(credentials.Signing)
    def sign_bytes(self, message):
        return self._signer.sign(message)

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer(self):
        return self._signer

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer_email(self):
        return self._service_account_email

    @_helpers.copy_docstring(credentials.Credentials)
    def get_cred_info(self):
        if self._cred_file_path:
            return {
                "credential_source": self._cred_file_path,
                "credential_type": "service account credentials",
                "principal": self.service_account_email,
            }
        return None


class IDTokenCredentials(
    credentials.Signing,
    credentials.CredentialsWithQuotaProject,
    credentials.CredentialsWithTokenUri,
):
    """Open ID Connect ID Token-based service account credentials.

    These credentials are largely similar to :class:`.Credentials`, but instead
    of using an OAuth 2.0 Access Token as the bearer token, they use an Open
    ID Connect ID Token as the bearer token. These credentials are useful when
    communicating to services that require ID Tokens and can not accept access
    tokens.

    Usually, you'll create these credentials with one of the helper
    constructors. To create credentials using a Google service account
    private key JSON file::

        credentials = (
            service_account.IDTokenCredentials.from_service_account_file(
                'service-account.json'))


    Or if you already have the service account file loaded::

        service_account_info = json.load(open('service_account.json'))
        credentials = (
            service_account.IDTokenCredentials.from_service_account_info(
                service_account_info))


    Both helper methods pass on arguments to the constructor, so you can
    specify additional scopes and a subject if necessary::

        credentials = (
            service_account.IDTokenCredentials.from_service_account_file(
                'service-account.json',
                scopes=['email'],
                subject='user@example.com'))


    The credentials are considered immutable. If you want to modify the scopes
    or the subject used for delegation, use :meth:`with_scopes` or
    :meth:`with_subject`::

        scoped_credentials = credentials.with_scopes(['email'])
        delegated_credentials = credentials.with_subject(subject)

    """

    def __init__(
        self,
        signer,
        service_account_email,
        token_uri,
        target_audience,
        additional_claims=None,
        quota_project_id=None,
        universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
    ):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            service_account_email (str): The service account's email.
            token_uri (str): The OAuth 2.0 Token URI.
            target_audience (str): The intended audience for these credentials,
                used when requesting the ID Token. The ID Token's ``aud`` claim
                will be set to this string.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT assertion used in the authorization grant.
            quota_project_id (Optional[str]): The project ID used for quota and billing.
            universe_domain (str): The universe domain. The default
                universe domain is googleapis.com. For default value IAM ID
                token endponint is used for token refresh. Note that
                iam.serviceAccountTokenCreator role is required to use the IAM
                endpoint.
        .. note:: Typically one of the helper constructors
            :meth:`from_service_account_file` or
            :meth:`from_service_account_info` are used instead of calling the
            constructor directly.
        """
        super(IDTokenCredentials, self).__init__()
        self._signer = signer
        self._service_account_email = service_account_email
        self._token_uri = token_uri
        self._target_audience = target_audience
        self._quota_project_id = quota_project_id
        self._use_iam_endpoint = False

        if not universe_domain:
            self._universe_domain = credentials.DEFAULT_UNIVERSE_DOMAIN
        else:
            self._universe_domain = universe_domain
        self._iam_id_token_endpoint = iam._IAM_IDTOKEN_ENDPOINT.replace(
            "googleapis.com", self._universe_domain
        )

        if self._universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN:
            self._use_iam_endpoint = True

        if additional_claims is not None:
            self._additional_claims = additional_claims
        else:
            self._additional_claims = {}

    @classmethod
    def _from_signer_and_info(cls, signer, info, **kwargs):
        """Creates a credentials instance from a signer and service account
        info.

        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            info (Mapping[str, str]): The service account info.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.IDTokenCredentials: The constructed credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        kwargs.setdefault("service_account_email", info["client_email"])
        kwargs.setdefault("token_uri", info["token_uri"])
        if "universe_domain" in info:
            kwargs["universe_domain"] = info["universe_domain"]
        return cls(signer, **kwargs)

    @classmethod
    def from_service_account_info(cls, info, **kwargs):
        """Creates a credentials instance from parsed service account info.

        Args:
            info (Mapping[str, str]): The service account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.service_account.IDTokenCredentials: The constructed
                credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        signer = _service_account_info.from_dict(
            info, require=["client_email", "token_uri"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename, **kwargs):
        """Creates a credentials instance from a service account json file.

        Args:
            filename (str): The path to the service account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.service_account.IDTokenCredentials: The constructed
                credentials.
        """
        info, signer = _service_account_info.from_filename(
            filename, require=["client_email", "token_uri"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    def _make_copy(self):
        cred = self.__class__(
            self._signer,
            service_account_email=self._service_account_email,
            token_uri=self._token_uri,
            target_audience=self._target_audience,
            additional_claims=self._additional_claims.copy(),
            quota_project_id=self.quota_project_id,
            universe_domain=self._universe_domain,
        )
        # _use_iam_endpoint is not exposed in the constructor
        cred._use_iam_endpoint = self._use_iam_endpoint
        return cred

    def with_target_audience(self, target_audience):
        """Create a copy of these credentials with the specified target
        audience.

        Args:
            target_audience (str): The intended audience for these credentials,
            used when requesting the ID Token.

        Returns:
            google.auth.service_account.IDTokenCredentials: A new credentials
                instance.
        """
        cred = self._make_copy()
        cred._target_audience = target_audience
        return cred

    def _with_use_iam_endpoint(self, use_iam_endpoint):
        """Create a copy of these credentials with the use_iam_endpoint value.

        Args:
            use_iam_endpoint (bool): If True, IAM generateIdToken endpoint will
                be used instead of the token_uri. Note that
                iam.serviceAccountTokenCreator role is required to use the IAM
                endpoint. The default value is False. This feature is currently
                experimental and subject to change without notice.

        Returns:
            google.auth.service_account.IDTokenCredentials: A new credentials
                instance.
        Raises:
            google.auth.exceptions.InvalidValue: If the universe domain is not
                default and use_iam_endpoint is False.
        """
        cred = self._make_copy()
        if (
            cred._universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN
            and not use_iam_endpoint
        ):
            raise exceptions.InvalidValue(
                "use_iam_endpoint should be True for non-default universe domain"
            )
        cred._use_iam_endpoint = use_iam_endpoint
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        cred = self._make_copy()
        cred._quota_project_id = quota_project_id
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithTokenUri)
    def with_token_uri(self, token_uri):
        cred = self._make_copy()
        cred._token_uri = token_uri
        return cred

    def _make_authorization_grant_assertion(self):
        """Create the OAuth 2.0 assertion.

        This assertion is used during the OAuth 2.0 grant to acquire an
        ID token.

        Returns:
            bytes: The authorization grant assertion.
        """
        now = _helpers.utcnow()
        lifetime = datetime.timedelta(seconds=_DEFAULT_TOKEN_LIFETIME_SECS)
        expiry = now + lifetime

        payload = {
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
            # The issuer must be the service account email.
            "iss": self.service_account_email,
            # The audience must be the auth token endpoint's URI
            "aud": _GOOGLE_OAUTH2_TOKEN_ENDPOINT,
            # The target audience specifies which service the ID token is
            # intended for.
            "target_audience": self._target_audience,
        }

        payload.update(self._additional_claims)

        token = jwt.encode(self._signer, payload)

        return token

    def _refresh_with_iam_endpoint(self, request):
        """Use IAM generateIdToken endpoint to obtain an ID token.

        It works as follows:

        1. First we create a self signed jwt with
        https://www.googleapis.com/auth/iam being the scope.

        2. Next we use the self signed jwt as the access token, and make a POST
        request to IAM generateIdToken endpoint. The request body is:
            {
                "audience": self._target_audience,
                "includeEmail": "true",
                "useEmailAzp": "true",
            }

        If the request is succesfully, it will return {"token":"the ID token"},
        and we can extract the ID token and compute its expiry.
        """
        jwt_credentials = jwt.Credentials.from_signing_credentials(
            self,
            None,
            additional_claims={"scope": "https://www.googleapis.com/auth/iam"},
        )
        jwt_credentials.refresh(request)
        self.token, self.expiry = _client.call_iam_generate_id_token_endpoint(
            request,
            self._iam_id_token_endpoint,
            self.signer_email,
            self._target_audience,
            jwt_credentials.token.decode(),
            self._universe_domain,
        )

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        if self._use_iam_endpoint:
            self._refresh_with_iam_endpoint(request)
        else:
            assertion = self._make_authorization_grant_assertion()
            access_token, expiry, _ = _client.id_token_jwt_grant(
                request, self._token_uri, assertion
            )
            self.token = access_token
            self.expiry = expiry

    @property
    def service_account_email(self):
        """The service account email."""
        return self._service_account_email

    @_helpers.copy_docstring(credentials.Signing)
    def sign_bytes(self, message):
        return self._signer.sign(message)

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer(self):
        return self._signer

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer_email(self):
        return self._service_account_email

# === NexusCore/openenv\Lib\site-packages\matplotlib\table.py ===
# Original code by:
#    John Gill <jng@europe.renre.com>
#    Copyright 2004 John Gill and John Hunter
#
# Subsequent changes:
#    The Matplotlib development team
#    Copyright The Matplotlib development team

"""
Tables drawing.

.. note::
    The table implementation in Matplotlib is lightly maintained. For a more
    featureful table implementation, you may wish to try `blume
    <https://github.com/swfiua/blume>`_.

Use the factory function `~matplotlib.table.table` to create a ready-made
table from texts. If you need more control, use the `.Table` class and its
methods.

The table consists of a grid of cells, which are indexed by (row, column).
The cell (0, 0) is positioned at the top left.

Thanks to John Gill for providing the class and table.
"""

import numpy as np

from . import _api, _docstring
from .artist import Artist, allow_rasterization
from .patches import Rectangle
from .text import Text
from .transforms import Bbox
from .path import Path

from .cbook import _is_pandas_dataframe


class Cell(Rectangle):
    """
    A cell is a `.Rectangle` with some associated `.Text`.

    As a user, you'll most likely not creates cells yourself. Instead, you
    should use either the `~matplotlib.table.table` factory function or
    `.Table.add_cell`.
    """

    PAD = 0.1
    """Padding between text and rectangle."""

    _edges = 'BRTL'
    _edge_aliases = {'open':         '',
                     'closed':       _edges,  # default
                     'horizontal':   'BT',
                     'vertical':     'RL'
                     }

    def __init__(self, xy, width, height, *,
                 edgecolor='k', facecolor='w',
                 fill=True,
                 text='',
                 loc='right',
                 fontproperties=None,
                 visible_edges='closed',
                 ):
        """
        Parameters
        ----------
        xy : 2-tuple
            The position of the bottom left corner of the cell.
        width : float
            The cell width.
        height : float
            The cell height.
        edgecolor : :mpltype:`color`, default: 'k'
            The color of the cell border.
        facecolor : :mpltype:`color`, default: 'w'
            The cell facecolor.
        fill : bool, default: True
            Whether the cell background is filled.
        text : str, optional
            The cell text.
        loc : {'right', 'center', 'left'}
            The alignment of the text within the cell.
        fontproperties : dict, optional
            A dict defining the font properties of the text. Supported keys and
            values are the keyword arguments accepted by `.FontProperties`.
        visible_edges : {'closed', 'open', 'horizontal', 'vertical'} or \
substring of 'BRTL'
            The cell edges to be drawn with a line: a substring of 'BRTL'
            (bottom, right, top, left), or one of 'open' (no edges drawn),
            'closed' (all edges drawn), 'horizontal' (bottom and top),
            'vertical' (right and left).
        """

        # Call base
        super().__init__(xy, width=width, height=height, fill=fill,
                         edgecolor=edgecolor, facecolor=facecolor)
        self.set_clip_on(False)
        self.visible_edges = visible_edges

        # Create text object
        self._loc = loc
        self._text = Text(x=xy[0], y=xy[1], clip_on=False,
                          text=text, fontproperties=fontproperties,
                          horizontalalignment=loc, verticalalignment='center')

    def set_transform(self, t):
        super().set_transform(t)
        # the text does not get the transform!
        self.stale = True

    def set_figure(self, fig):
        super().set_figure(fig)
        self._text.set_figure(fig)

    def get_text(self):
        """Return the cell `.Text` instance."""
        return self._text

    def set_fontsize(self, size):
        """Set the text fontsize."""
        self._text.set_fontsize(size)
        self.stale = True

    def get_fontsize(self):
        """Return the cell fontsize."""
        return self._text.get_fontsize()

    def auto_set_font_size(self, renderer):
        """Shrink font size until the text fits into the cell width."""
        fontsize = self.get_fontsize()
        required = self.get_required_width(renderer)
        while fontsize > 1 and required > self.get_width():
            fontsize -= 1
            self.set_fontsize(fontsize)
            required = self.get_required_width(renderer)

        return fontsize

    @allow_rasterization
    def draw(self, renderer):
        if not self.get_visible():
            return
        # draw the rectangle
        super().draw(renderer)
        # position the text
        self._set_text_position(renderer)
        self._text.draw(renderer)
        self.stale = False

    def _set_text_position(self, renderer):
        """Set text up so it is drawn in the right place."""
        bbox = self.get_window_extent(renderer)
        # center vertically
        y = bbox.y0 + bbox.height / 2
        # position horizontally
        loc = self._text.get_horizontalalignment()
        if loc == 'center':
            x = bbox.x0 + bbox.width / 2
        elif loc == 'left':
            x = bbox.x0 + bbox.width * self.PAD
        else:  # right.
            x = bbox.x0 + bbox.width * (1 - self.PAD)
        self._text.set_position((x, y))

    def get_text_bounds(self, renderer):
        """
        Return the text bounds as *(x, y, width, height)* in table coordinates.
        """
        return (self._text.get_window_extent(renderer)
                .transformed(self.get_data_transform().inverted())
                .bounds)

    def get_required_width(self, renderer):
        """Return the minimal required width for the cell."""
        l, b, w, h = self.get_text_bounds(renderer)
        return w * (1.0 + (2.0 * self.PAD))

    @_docstring.interpd
    def set_text_props(self, **kwargs):
        """
        Update the text properties.

        Valid keyword arguments are:

        %(Text:kwdoc)s
        """
        self._text._internal_update(kwargs)
        self.stale = True

    @property
    def visible_edges(self):
        """
        The cell edges to be drawn with a line.

        Reading this property returns a substring of 'BRTL' (bottom, right,
        top, left').

        When setting this property, you can use a substring of 'BRTL' or one
        of {'open', 'closed', 'horizontal', 'vertical'}.
        """
        return self._visible_edges

    @visible_edges.setter
    def visible_edges(self, value):
        if value is None:
            self._visible_edges = self._edges
        elif value in self._edge_aliases:
            self._visible_edges = self._edge_aliases[value]
        else:
            if any(edge not in self._edges for edge in value):
                raise ValueError('Invalid edge param {}, must only be one of '
                                 '{} or string of {}'.format(
                                     value,
                                     ", ".join(self._edge_aliases),
                                     ", ".join(self._edges)))
            self._visible_edges = value
        self.stale = True

    def get_path(self):
        """Return a `.Path` for the `.visible_edges`."""
        codes = [Path.MOVETO]
        codes.extend(
            Path.LINETO if edge in self._visible_edges else Path.MOVETO
            for edge in self._edges)
        if Path.MOVETO not in codes[1:]:  # All sides are visible
            codes[-1] = Path.CLOSEPOLY
        return Path(
            [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]],
            codes,
            readonly=True
            )


CustomCell = Cell  # Backcompat. alias.


class Table(Artist):
    """
    A table of cells.

    The table consists of a grid of cells, which are indexed by (row, column).

    For a simple table, you'll have a full grid of cells with indices from
    (0, 0) to (num_rows-1, num_cols-1), in which the cell (0, 0) is positioned
    at the top left. However, you can also add cells with negative indices.
    You don't have to add a cell to every grid position, so you can create
    tables that have holes.

    *Note*: You'll usually not create an empty table from scratch. Instead use
    `~matplotlib.table.table` to create a table from data.
    """
    codes = {'best': 0,
             'upper right':  1,  # default
             'upper left':   2,
             'lower left':   3,
             'lower right':  4,
             'center left':  5,
             'center right': 6,
             'lower center': 7,
             'upper center': 8,
             'center':       9,
             'top right':    10,
             'top left':     11,
             'bottom left':  12,
             'bottom right': 13,
             'right':        14,
             'left':         15,
             'top':          16,
             'bottom':       17,
             }
    """Possible values where to place the table relative to the Axes."""

    FONTSIZE = 10

    AXESPAD = 0.02
    """The border between the Axes and the table edge in Axes units."""

    def __init__(self, ax, loc=None, bbox=None, **kwargs):
        """
        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The `~.axes.Axes` to plot the table into.
        loc : str, optional
            The position of the cell with respect to *ax*. This must be one of
            the `~.Table.codes`.
        bbox : `.Bbox` or [xmin, ymin, width, height], optional
            A bounding box to draw the table into. If this is not *None*, this
            overrides *loc*.

        Other Parameters
        ----------------
        **kwargs
            `.Artist` properties.
        """

        super().__init__()

        if isinstance(loc, str):
            if loc not in self.codes:
                raise ValueError(
                    "Unrecognized location {!r}. Valid locations are\n\t{}"
                    .format(loc, '\n\t'.join(self.codes)))
            loc = self.codes[loc]
        self.set_figure(ax.get_figure(root=False))
        self._axes = ax
        self._loc = loc
        self._bbox = bbox

        # use axes coords
        ax._unstale_viewLim()
        self.set_transform(ax.transAxes)

        self._cells = {}
        self._edges = None
        self._autoColumns = []
        self._autoFontsize = True
        self._internal_update(kwargs)

        self.set_clip_on(False)

    def add_cell(self, row, col, *args, **kwargs):
        """
        Create a cell and add it to the table.

        Parameters
        ----------
        row : int
            Row index.
        col : int
            Column index.
        *args, **kwargs
            All other parameters are passed on to `Cell`.

        Returns
        -------
        `.Cell`
            The created cell.

        """
        xy = (0, 0)
        cell = Cell(xy, visible_edges=self.edges, *args, **kwargs)
        self[row, col] = cell
        return cell

    def __setitem__(self, position, cell):
        """
        Set a custom cell in a given position.
        """
        _api.check_isinstance(Cell, cell=cell)
        try:
            row, col = position[0], position[1]
        except Exception as err:
            raise KeyError('Only tuples length 2 are accepted as '
                           'coordinates') from err
        cell.set_figure(self.get_figure(root=False))
        cell.set_transform(self.get_transform())
        cell.set_clip_on(False)
        self._cells[row, col] = cell
        self.stale = True

    def __getitem__(self, position):
        """Retrieve a custom cell from a given position."""
        return self._cells[position]

    @property
    def edges(self):
        """
        The default value of `~.Cell.visible_edges` for newly added
        cells using `.add_cell`.

        Notes
        -----
        This setting does currently only affect newly created cells using
        `.add_cell`.

        To change existing cells, you have to set their edges explicitly::

            for c in tab.get_celld().values():
                c.visible_edges = 'horizontal'

        """
        return self._edges

    @edges.setter
    def edges(self, value):
        self._edges = value
        self.stale = True

    def _approx_text_height(self):
        return (self.FONTSIZE / 72.0 * self.get_figure(root=True).dpi /
                self._axes.bbox.height * 1.2)

    @allow_rasterization
    def draw(self, renderer):
        # docstring inherited

        # Need a renderer to do hit tests on mouseevent; assume the last one
        # will do
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        if renderer is None:
            raise RuntimeError('No renderer defined')

        if not self.get_visible():
            return
        renderer.open_group('table', gid=self.get_gid())
        self._update_positions(renderer)

        for key in sorted(self._cells):
            self._cells[key].draw(renderer)

        renderer.close_group('table')
        self.stale = False

    def _get_grid_bbox(self, renderer):
        """
        Get a bbox, in axes coordinates for the cells.

        Only include those in the range (0, 0) to (maxRow, maxCol).
        """
        boxes = [cell.get_window_extent(renderer)
                 for (row, col), cell in self._cells.items()
                 if row >= 0 and col >= 0]
        bbox = Bbox.union(boxes)
        return bbox.transformed(self.get_transform().inverted())

    def contains(self, mouseevent):
        # docstring inherited
        if self._different_canvas(mouseevent):
            return False, {}
        # TODO: Return index of the cell containing the cursor so that the user
        # doesn't have to bind to each one individually.
        renderer = self.get_figure(root=True)._get_renderer()
        if renderer is not None:
            boxes = [cell.get_window_extent(renderer)
                     for (row, col), cell in self._cells.items()
                     if row >= 0 and col >= 0]
            bbox = Bbox.union(boxes)
            return bbox.contains(mouseevent.x, mouseevent.y), {}
        else:
            return False, {}

    def get_children(self):
        """Return the Artists contained by the table."""
        return list(self._cells.values())

    def get_window_extent(self, renderer=None):
        # docstring inherited
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        self._update_positions(renderer)
        boxes = [cell.get_window_extent(renderer)
                 for cell in self._cells.values()]
        return Bbox.union(boxes)

    def _do_cell_alignment(self):
        """
        Calculate row heights and column widths; position cells accordingly.
        """
        # Calculate row/column widths
        widths = {}
        heights = {}
        for (row, col), cell in self._cells.items():
            height = heights.setdefault(row, 0.0)
            heights[row] = max(height, cell.get_height())
            width = widths.setdefault(col, 0.0)
            widths[col] = max(width, cell.get_width())

        # work out left position for each column
        xpos = 0
        lefts = {}
        for col in sorted(widths):
            lefts[col] = xpos
            xpos += widths[col]

        ypos = 0
        bottoms = {}
        for row in sorted(heights, reverse=True):
            bottoms[row] = ypos
            ypos += heights[row]

        # set cell positions
        for (row, col), cell in self._cells.items():
            cell.set_x(lefts[col])
            cell.set_y(bottoms[row])

    def auto_set_column_width(self, col):
        """
        Automatically set the widths of given columns to optimal sizes.

        Parameters
        ----------
        col : int or sequence of ints
            The indices of the columns to auto-scale.
        """
        col1d = np.atleast_1d(col)
        if not np.issubdtype(col1d.dtype, np.integer):
            raise TypeError("col must be an int or sequence of ints.")
        for cell in col1d:
            self._autoColumns.append(cell)

        self.stale = True

    def _auto_set_column_width(self, col, renderer):
        """Automatically set width for column."""
        cells = [cell for key, cell in self._cells.items() if key[1] == col]
        max_width = max((cell.get_required_width(renderer) for cell in cells),
                        default=0)
        for cell in cells:
            cell.set_width(max_width)

    def auto_set_font_size(self, value=True):
        """Automatically set font size."""
        self._autoFontsize = value
        self.stale = True

    def _auto_set_font_size(self, renderer):

        if len(self._cells) == 0:
            return
        fontsize = next(iter(self._cells.values())).get_fontsize()
        cells = []
        for key, cell in self._cells.items():
            # ignore auto-sized columns
            if key[1] in self._autoColumns:
                continue
            size = cell.auto_set_font_size(renderer)
            fontsize = min(fontsize, size)
            cells.append(cell)

        # now set all fontsizes equal
        for cell in self._cells.values():
            cell.set_fontsize(fontsize)

    def scale(self, xscale, yscale):
        """Scale column widths by *xscale* and row heights by *yscale*."""
        for c in self._cells.values():
            c.set_width(c.get_width() * xscale)
            c.set_height(c.get_height() * yscale)

    def set_fontsize(self, size):
        """
        Set the font size, in points, of the cell text.

        Parameters
        ----------
        size : float

        Notes
        -----
        As long as auto font size has not been disabled, the value will be
        clipped such that the text fits horizontally into the cell.

        You can disable this behavior using `.auto_set_font_size`.

        >>> the_table.auto_set_font_size(False)
        >>> the_table.set_fontsize(20)

        However, there is no automatic scaling of the row height so that the
        text may exceed the cell boundary.
        """
        for cell in self._cells.values():
            cell.set_fontsize(size)
        self.stale = True

    def _offset(self, ox, oy):
        """Move all the artists by ox, oy (axes coords)."""
        for c in self._cells.values():
            x, y = c.get_x(), c.get_y()
            c.set_x(x + ox)
            c.set_y(y + oy)

    def _update_positions(self, renderer):
        # called from renderer to allow more precise estimates of
        # widths and heights with get_window_extent

        # Do any auto width setting
        for col in self._autoColumns:
            self._auto_set_column_width(col, renderer)

        if self._autoFontsize:
            self._auto_set_font_size(renderer)

        # Align all the cells
        self._do_cell_alignment()

        bbox = self._get_grid_bbox(renderer)
        l, b, w, h = bbox.bounds

        if self._bbox is not None:
            # Position according to bbox
            if isinstance(self._bbox, Bbox):
                rl, rb, rw, rh = self._bbox.bounds
            else:
                rl, rb, rw, rh = self._bbox
            self.scale(rw / w, rh / h)
            ox = rl - l
            oy = rb - b
            self._do_cell_alignment()
        else:
            # Position using loc
            (BEST, UR, UL, LL, LR, CL, CR, LC, UC, C,
             TR, TL, BL, BR, R, L, T, B) = range(len(self.codes))
            # defaults for center
            ox = (0.5 - w / 2) - l
            oy = (0.5 - h / 2) - b
            if self._loc in (UL, LL, CL):   # left
                ox = self.AXESPAD - l
            if self._loc in (BEST, UR, LR, R, CR):  # right
                ox = 1 - (l + w + self.AXESPAD)
            if self._loc in (BEST, UR, UL, UC):     # upper
                oy = 1 - (b + h + self.AXESPAD)
            if self._loc in (LL, LR, LC):           # lower
                oy = self.AXESPAD - b
            if self._loc in (LC, UC, C):            # center x
                ox = (0.5 - w / 2) - l
            if self._loc in (CL, CR, C):            # center y
                oy = (0.5 - h / 2) - b

            if self._loc in (TL, BL, L):            # out left
                ox = - (l + w)
            if self._loc in (TR, BR, R):            # out right
                ox = 1.0 - l
            if self._loc in (TR, TL, T):            # out top
                oy = 1.0 - b
            if self._loc in (BL, BR, B):           # out bottom
                oy = - (b + h)

        self._offset(ox, oy)

    def get_celld(self):
        r"""
        Return a dict of cells in the table mapping *(row, column)* to
        `.Cell`\s.

        Notes
        -----
        You can also directly index into the Table object to access individual
        cells::

            cell = table[row, col]

        """
        return self._cells


@_docstring.interpd
def table(ax,
          cellText=None, cellColours=None,
          cellLoc='right', colWidths=None,
          rowLabels=None, rowColours=None, rowLoc='left',
          colLabels=None, colColours=None, colLoc='center',
          loc='bottom', bbox=None, edges='closed',
          **kwargs):
    """
    Add a table to an `~.axes.Axes`.

    At least one of *cellText* or *cellColours* must be specified. These
    parameters must be 2D lists, in which the outer lists define the rows and
    the inner list define the column values per row. Each row must have the
    same number of elements.

    The table can optionally have row and column headers, which are configured
    using *rowLabels*, *rowColours*, *rowLoc* and *colLabels*, *colColours*,
    *colLoc* respectively.

    For finer grained control over tables, use the `.Table` class and add it to
    the Axes with `.Axes.add_table`.

    Parameters
    ----------
    cellText : 2D list of str or pandas.DataFrame, optional
        The texts to place into the table cells.

        *Note*: Line breaks in the strings are currently not accounted for and
        will result in the text exceeding the cell boundaries.

    cellColours : 2D list of :mpltype:`color`, optional
        The background colors of the cells.

    cellLoc : {'right', 'center', 'left'}
        The alignment of the text within the cells.

    colWidths : list of float, optional
        The column widths in units of the axes. If not given, all columns will
        have a width of *1 / ncols*.

    rowLabels : list of str, optional
        The text of the row header cells.

    rowColours : list of :mpltype:`color`, optional
        The colors of the row header cells.

    rowLoc : {'left', 'center', 'right'}
        The text alignment of the row header cells.

    colLabels : list of str, optional
        The text of the column header cells.

    colColours : list of :mpltype:`color`, optional
        The colors of the column header cells.

    colLoc : {'center', 'left', 'right'}
        The text alignment of the column header cells.

    loc : str, default: 'bottom'
        The position of the cell with respect to *ax*. This must be one of
        the `~.Table.codes`.

    bbox : `.Bbox` or [xmin, ymin, width, height], optional
        A bounding box to draw the table into. If this is not *None*, this
        overrides *loc*.

    edges : {'closed', 'open', 'horizontal', 'vertical'} or substring of 'BRTL'
        The cell edges to be drawn with a line. See also
        `~.Cell.visible_edges`.

    Returns
    -------
    `~matplotlib.table.Table`
        The created table.

    Other Parameters
    ----------------
    **kwargs
        `.Table` properties.

    %(Table:kwdoc)s
    """

    if cellColours is None and cellText is None:
        raise ValueError('At least one argument from "cellColours" or '
                         '"cellText" must be provided to create a table.')

    # Check we have some cellText
    if cellText is None:
        # assume just colours are needed
        rows = len(cellColours)
        cols = len(cellColours[0])
        cellText = [[''] * cols] * rows

    # Check if we have a Pandas DataFrame
    if _is_pandas_dataframe(cellText):
        # if rowLabels/colLabels are empty, use DataFrame entries.
        # Otherwise, throw an error.
        if rowLabels is None:
            rowLabels = cellText.index
        else:
            raise ValueError("rowLabels cannot be used alongside Pandas DataFrame")
        if colLabels is None:
            colLabels = cellText.columns
        else:
            raise ValueError("colLabels cannot be used alongside Pandas DataFrame")
        # Update cellText with only values
        cellText = cellText.values

    rows = len(cellText)
    cols = len(cellText[0])
    for row in cellText:
        if len(row) != cols:
            raise ValueError(f"Each row in 'cellText' must have {cols} "
                             "columns")

    if cellColours is not None:
        if len(cellColours) != rows:
            raise ValueError(f"'cellColours' must have {rows} rows")
        for row in cellColours:
            if len(row) != cols:
                raise ValueError("Each row in 'cellColours' must have "
                                 f"{cols} columns")
    else:
        cellColours = ['w' * cols] * rows

    # Set colwidths if not given
    if colWidths is None:
        colWidths = [1.0 / cols] * cols

    # Fill in missing information for column
    # and row labels
    rowLabelWidth = 0
    if rowLabels is None:
        if rowColours is not None:
            rowLabels = [''] * rows
            rowLabelWidth = colWidths[0]
    elif rowColours is None:
        rowColours = 'w' * rows

    if rowLabels is not None:
        if len(rowLabels) != rows:
            raise ValueError(f"'rowLabels' must be of length {rows}")

    # If we have column labels, need to shift
    # the text and colour arrays down 1 row
    offset = 1
    if colLabels is None:
        if colColours is not None:
            colLabels = [''] * cols
        else:
            offset = 0
    elif colColours is None:
        colColours = 'w' * cols

    # Set up cell colours if not given
    if cellColours is None:
        cellColours = ['w' * cols] * rows

    # Now create the table
    table = Table(ax, loc, bbox, **kwargs)
    table.edges = edges
    height = table._approx_text_height()

    # Add the cells
    for row in range(rows):
        for col in range(cols):
            table.add_cell(row + offset, col,
                           width=colWidths[col], height=height,
                           text=cellText[row][col],
                           facecolor=cellColours[row][col],
                           loc=cellLoc)
    # Do column labels
    if colLabels is not None:
        for col in range(cols):
            table.add_cell(0, col,
                           width=colWidths[col], height=height,
                           text=colLabels[col], facecolor=colColours[col],
                           loc=colLoc)

    # Do row labels
    if rowLabels is not None:
        for row in range(rows):
            table.add_cell(row + offset, -1,
                           width=rowLabelWidth or 1e-15, height=height,
                           text=rowLabels[row], facecolor=rowColours[row],
                           loc=rowLoc)
        if rowLabelWidth == 0:
            table.auto_set_column_width(-1)

    # set_fontsize is only effective after cells are added
    if "fontsize" in kwargs:
        table.set_fontsize(kwargs["fontsize"])

    ax.add_table(table)
    return table

# === NexusCore/openenv\Lib\site-packages\openai\_models.py ===
from __future__ import annotations

import os
import inspect
from typing import TYPE_CHECKING, Any, Type, Tuple, Union, Generic, TypeVar, Callable, Optional, cast
from datetime import date, datetime
from typing_extensions import (
    Unpack,
    Literal,
    ClassVar,
    Protocol,
    Required,
    Sequence,
    ParamSpec,
    TypedDict,
    TypeGuard,
    final,
    override,
    runtime_checkable,
)

import pydantic
from pydantic.fields import FieldInfo

from ._types import (
    Body,
    IncEx,
    Query,
    ModelT,
    Headers,
    Timeout,
    NotGiven,
    AnyMapping,
    HttpxRequestFiles,
)
from ._utils import (
    PropertyInfo,
    is_list,
    is_given,
    json_safe,
    lru_cache,
    is_mapping,
    parse_date,
    coerce_boolean,
    parse_datetime,
    strip_not_given,
    extract_type_arg,
    is_annotated_type,
    is_type_alias_type,
    strip_annotated_type,
)
from ._compat import (
    PYDANTIC_V2,
    ConfigDict,
    GenericModel as BaseGenericModel,
    get_args,
    is_union,
    parse_obj,
    get_origin,
    is_literal_type,
    get_model_config,
    get_model_fields,
    field_get_default,
)
from ._constants import RAW_RESPONSE_HEADER

if TYPE_CHECKING:
    from pydantic_core.core_schema import ModelField, ModelSchema, LiteralSchema, ModelFieldsSchema

__all__ = ["BaseModel", "GenericModel"]

_T = TypeVar("_T")
_BaseModelT = TypeVar("_BaseModelT", bound="BaseModel")

P = ParamSpec("P")

ReprArgs = Sequence[Tuple[Optional[str], Any]]


@runtime_checkable
class _ConfigProtocol(Protocol):
    allow_population_by_field_name: bool


class BaseModel(pydantic.BaseModel):
    if PYDANTIC_V2:
        model_config: ClassVar[ConfigDict] = ConfigDict(
            extra="allow", defer_build=coerce_boolean(os.environ.get("DEFER_PYDANTIC_BUILD", "true"))
        )
    else:

        @property
        @override
        def model_fields_set(self) -> set[str]:
            # a forwards-compat shim for pydantic v2
            return self.__fields_set__  # type: ignore

        class Config(pydantic.BaseConfig):  # pyright: ignore[reportDeprecated]
            extra: Any = pydantic.Extra.allow  # type: ignore

        @override
        def __repr_args__(self) -> ReprArgs:
            # we don't want these attributes to be included when something like `rich.print` is used
            return [arg for arg in super().__repr_args__() if arg[0] not in {"_request_id", "__exclude_fields__"}]

    if TYPE_CHECKING:
        _request_id: Optional[str] = None
        """The ID of the request, returned via the X-Request-ID header. Useful for debugging requests and reporting issues to OpenAI.

        This will **only** be set for the top-level response object, it will not be defined for nested objects. For example:
        
        ```py
        completion = await client.chat.completions.create(...)
        completion._request_id  # req_id_xxx
        completion.usage._request_id  # raises `AttributeError`
        ```

        Note: unlike other properties that use an `_` prefix, this property
        *is* public. Unless documented otherwise, all other `_` prefix properties,
        methods and modules are *private*.
        """

    def to_dict(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> dict[str, object]:
        """Recursively generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        By default, fields that were not set by the API will not be included,
        and keys will match the API response, *not* the property names from the model.

        For example, if the API responds with `"fooBar": true` but we've defined a `foo_bar: bool` property,
        the output will use the `"fooBar"` key (unless `use_api_names=False` is passed).

        Args:
            mode:
                If mode is 'json', the dictionary will only contain JSON serializable types. e.g. `datetime` will be turned into a string, `"2024-3-22T18:11:19.117000Z"`.
                If mode is 'python', the dictionary may contain any Python objects. e.g. `datetime(2024, 3, 22)`

            use_api_names: Whether to use the key that the API responded with or the property name. Defaults to `True`.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value from the output.
            exclude_none: Whether to exclude fields that have a value of `None` from the output.
            warnings: Whether to log warnings when invalid fields are encountered. This is only supported in Pydantic v2.
        """
        return self.model_dump(
            mode=mode,
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    def to_json(
        self,
        *,
        indent: int | None = 2,
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> str:
        """Generates a JSON string representing this model as it would be received from or sent to the API (but with indentation).

        By default, fields that were not set by the API will not be included,
        and keys will match the API response, *not* the property names from the model.

        For example, if the API responds with `"fooBar": true` but we've defined a `foo_bar: bool` property,
        the output will use the `"fooBar"` key (unless `use_api_names=False` is passed).

        Args:
            indent: Indentation to use in the JSON output. If `None` is passed, the output will be compact. Defaults to `2`
            use_api_names: Whether to use the key that the API responded with or the property name. Defaults to `True`.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that have the default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            warnings: Whether to show any warnings that occurred during serialization. This is only supported in Pydantic v2.
        """
        return self.model_dump_json(
            indent=indent,
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    @override
    def __str__(self) -> str:
        # mypy complains about an invalid self arg
        return f"{self.__repr_name__()}({self.__repr_str__(', ')})"  # type: ignore[misc]

    # Override the 'construct' method in a way that supports recursive parsing without validation.
    # Based on https://github.com/samuelcolvin/pydantic/issues/1168#issuecomment-817742836.
    @classmethod
    @override
    def construct(  # pyright: ignore[reportIncompatibleMethodOverride]
        __cls: Type[ModelT],
        _fields_set: set[str] | None = None,
        **values: object,
    ) -> ModelT:
        m = __cls.__new__(__cls)
        fields_values: dict[str, object] = {}

        config = get_model_config(__cls)
        populate_by_name = (
            config.allow_population_by_field_name
            if isinstance(config, _ConfigProtocol)
            else config.get("populate_by_name")
        )

        if _fields_set is None:
            _fields_set = set()

        model_fields = get_model_fields(__cls)
        for name, field in model_fields.items():
            key = field.alias
            if key is None or (key not in values and populate_by_name):
                key = name

            if key in values:
                fields_values[name] = _construct_field(value=values[key], field=field, key=key)
                _fields_set.add(name)
            else:
                fields_values[name] = field_get_default(field)

        _extra = {}
        for key, value in values.items():
            if key not in model_fields:
                if PYDANTIC_V2:
                    _extra[key] = value
                else:
                    _fields_set.add(key)
                    fields_values[key] = value

        object.__setattr__(m, "__dict__", fields_values)

        if PYDANTIC_V2:
            # these properties are copied from Pydantic's `model_construct()` method
            object.__setattr__(m, "__pydantic_private__", None)
            object.__setattr__(m, "__pydantic_extra__", _extra)
            object.__setattr__(m, "__pydantic_fields_set__", _fields_set)
        else:
            # init_private_attributes() does not exist in v2
            m._init_private_attributes()  # type: ignore

            # copied from Pydantic v1's `construct()` method
            object.__setattr__(m, "__fields_set__", _fields_set)

        return m

    if not TYPE_CHECKING:
        # type checkers incorrectly complain about this assignment
        # because the type signatures are technically different
        # although not in practice
        model_construct = construct

    if not PYDANTIC_V2:
        # we define aliases for some of the new pydantic v2 methods so
        # that we can just document these methods without having to specify
        # a specific pydantic version as some users may not know which
        # pydantic version they are currently using

        @override
        def model_dump(
            self,
            *,
            mode: Literal["json", "python"] | str = "python",
            include: IncEx | None = None,
            exclude: IncEx | None = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal["none", "warn", "error"] = True,
            context: dict[str, Any] | None = None,
            serialize_as_any: bool = False,
        ) -> dict[str, Any]:
            """Usage docs: https://docs.pydantic.dev/2.4/concepts/serialization/#modelmodel_dump

            Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

            Args:
                mode: The mode in which `to_python` should run.
                    If mode is 'json', the dictionary will only contain JSON serializable types.
                    If mode is 'python', the dictionary may contain any Python objects.
                include: A list of fields to include in the output.
                exclude: A list of fields to exclude from the output.
                by_alias: Whether to use the field's alias in the dictionary key if defined.
                exclude_unset: Whether to exclude fields that are unset or None from the output.
                exclude_defaults: Whether to exclude fields that are set to their default value from the output.
                exclude_none: Whether to exclude fields that have a value of `None` from the output.
                round_trip: Whether to enable serialization and deserialization round-trip support.
                warnings: Whether to log warnings when invalid fields are encountered.

            Returns:
                A dictionary representation of the model.
            """
            if mode not in {"json", "python"}:
                raise ValueError("mode must be either 'json' or 'python'")
            if round_trip != False:
                raise ValueError("round_trip is only supported in Pydantic v2")
            if warnings != True:
                raise ValueError("warnings is only supported in Pydantic v2")
            if context is not None:
                raise ValueError("context is only supported in Pydantic v2")
            if serialize_as_any != False:
                raise ValueError("serialize_as_any is only supported in Pydantic v2")
            dumped = super().dict(  # pyright: ignore[reportDeprecated]
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )

            return cast(dict[str, Any], json_safe(dumped)) if mode == "json" else dumped

        @override
        def model_dump_json(
            self,
            *,
            indent: int | None = None,
            include: IncEx | None = None,
            exclude: IncEx | None = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal["none", "warn", "error"] = True,
            context: dict[str, Any] | None = None,
            serialize_as_any: bool = False,
        ) -> str:
            """Usage docs: https://docs.pydantic.dev/2.4/concepts/serialization/#modelmodel_dump_json

            Generates a JSON representation of the model using Pydantic's `to_json` method.

            Args:
                indent: Indentation to use in the JSON output. If None is passed, the output will be compact.
                include: Field(s) to include in the JSON output. Can take either a string or set of strings.
                exclude: Field(s) to exclude from the JSON output. Can take either a string or set of strings.
                by_alias: Whether to serialize using field aliases.
                exclude_unset: Whether to exclude fields that have not been explicitly set.
                exclude_defaults: Whether to exclude fields that have the default value.
                exclude_none: Whether to exclude fields that have a value of `None`.
                round_trip: Whether to use serialization/deserialization between JSON and class instance.
                warnings: Whether to show any warnings that occurred during serialization.

            Returns:
                A JSON string representation of the model.
            """
            if round_trip != False:
                raise ValueError("round_trip is only supported in Pydantic v2")
            if warnings != True:
                raise ValueError("warnings is only supported in Pydantic v2")
            if context is not None:
                raise ValueError("context is only supported in Pydantic v2")
            if serialize_as_any != False:
                raise ValueError("serialize_as_any is only supported in Pydantic v2")
            return super().json(  # type: ignore[reportDeprecated]
                indent=indent,
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )


def _construct_field(value: object, field: FieldInfo, key: str) -> object:
    if value is None:
        return field_get_default(field)

    if PYDANTIC_V2:
        type_ = field.annotation
    else:
        type_ = cast(type, field.outer_type_)  # type: ignore

    if type_ is None:
        raise RuntimeError(f"Unexpected field type is None for {key}")

    return construct_type(value=value, type_=type_)


def is_basemodel(type_: type) -> bool:
    """Returns whether or not the given type is either a `BaseModel` or a union of `BaseModel`"""
    if is_union(type_):
        for variant in get_args(type_):
            if is_basemodel(variant):
                return True

        return False

    return is_basemodel_type(type_)


def is_basemodel_type(type_: type) -> TypeGuard[type[BaseModel] | type[GenericModel]]:
    origin = get_origin(type_) or type_
    if not inspect.isclass(origin):
        return False
    return issubclass(origin, BaseModel) or issubclass(origin, GenericModel)


def build(
    base_model_cls: Callable[P, _BaseModelT],
    *args: P.args,
    **kwargs: P.kwargs,
) -> _BaseModelT:
    """Construct a BaseModel class without validation.

    This is useful for cases where you need to instantiate a `BaseModel`
    from an API response as this provides type-safe params which isn't supported
    by helpers like `construct_type()`.

    ```py
    build(MyModel, my_field_a="foo", my_field_b=123)
    ```
    """
    if args:
        raise TypeError(
            "Received positional arguments which are not supported; Keyword arguments must be used instead",
        )

    return cast(_BaseModelT, construct_type(type_=base_model_cls, value=kwargs))


def construct_type_unchecked(*, value: object, type_: type[_T]) -> _T:
    """Loose coercion to the expected type with construction of nested values.

    Note: the returned value from this function is not guaranteed to match the
    given type.
    """
    return cast(_T, construct_type(value=value, type_=type_))


def construct_type(*, value: object, type_: object) -> object:
    """Loose coercion to the expected type with construction of nested values.

    If the given value does not match the expected type then it is returned as-is.
    """

    # store a reference to the original type we were given before we extract any inner
    # types so that we can properly resolve forward references in `TypeAliasType` annotations
    original_type = None

    # we allow `object` as the input type because otherwise, passing things like
    # `Literal['value']` will be reported as a type error by type checkers
    type_ = cast("type[object]", type_)
    if is_type_alias_type(type_):
        original_type = type_  # type: ignore[unreachable]
        type_ = type_.__value__  # type: ignore[unreachable]

    # unwrap `Annotated[T, ...]` -> `T`
    if is_annotated_type(type_):
        meta: tuple[Any, ...] = get_args(type_)[1:]
        type_ = extract_type_arg(type_, 0)
    else:
        meta = tuple()

    # we need to use the origin class for any types that are subscripted generics
    # e.g. Dict[str, object]
    origin = get_origin(type_) or type_
    args = get_args(type_)

    if is_union(origin):
        try:
            return validate_type(type_=cast("type[object]", original_type or type_), value=value)
        except Exception:
            pass

        # if the type is a discriminated union then we want to construct the right variant
        # in the union, even if the data doesn't match exactly, otherwise we'd break code
        # that relies on the constructed class types, e.g.
        #
        # class FooType:
        #   kind: Literal['foo']
        #   value: str
        #
        # class BarType:
        #   kind: Literal['bar']
        #   value: int
        #
        # without this block, if the data we get is something like `{'kind': 'bar', 'value': 'foo'}` then
        # we'd end up constructing `FooType` when it should be `BarType`.
        discriminator = _build_discriminated_union_meta(union=type_, meta_annotations=meta)
        if discriminator and is_mapping(value):
            variant_value = value.get(discriminator.field_alias_from or discriminator.field_name)
            if variant_value and isinstance(variant_value, str):
                variant_type = discriminator.mapping.get(variant_value)
                if variant_type:
                    return construct_type(type_=variant_type, value=value)

        # if the data is not valid, use the first variant that doesn't fail while deserializing
        for variant in args:
            try:
                return construct_type(value=value, type_=variant)
            except Exception:
                continue

        raise RuntimeError(f"Could not convert data into a valid instance of {type_}")

    if origin == dict:
        if not is_mapping(value):
            return value

        _, items_type = get_args(type_)  # Dict[_, items_type]
        return {key: construct_type(value=item, type_=items_type) for key, item in value.items()}

    if (
        not is_literal_type(type_)
        and inspect.isclass(origin)
        and (issubclass(origin, BaseModel) or issubclass(origin, GenericModel))
    ):
        if is_list(value):
            return [cast(Any, type_).construct(**entry) if is_mapping(entry) else entry for entry in value]

        if is_mapping(value):
            if issubclass(type_, BaseModel):
                return type_.construct(**value)  # type: ignore[arg-type]

            return cast(Any, type_).construct(**value)

    if origin == list:
        if not is_list(value):
            return value

        inner_type = args[0]  # List[inner_type]
        return [construct_type(value=entry, type_=inner_type) for entry in value]

    if origin == float:
        if isinstance(value, int):
            coerced = float(value)
            if coerced != value:
                return value
            return coerced

        return value

    if type_ == datetime:
        try:
            return parse_datetime(value)  # type: ignore
        except Exception:
            return value

    if type_ == date:
        try:
            return parse_date(value)  # type: ignore
        except Exception:
            return value

    return value


@runtime_checkable
class CachedDiscriminatorType(Protocol):
    __discriminator__: DiscriminatorDetails


class DiscriminatorDetails:
    field_name: str
    """The name of the discriminator field in the variant class, e.g.

    ```py
    class Foo(BaseModel):
        type: Literal['foo']
    ```

    Will result in field_name='type'
    """

    field_alias_from: str | None
    """The name of the discriminator field in the API response, e.g.

    ```py
    class Foo(BaseModel):
        type: Literal['foo'] = Field(alias='type_from_api')
    ```

    Will result in field_alias_from='type_from_api'
    """

    mapping: dict[str, type]
    """Mapping of discriminator value to variant type, e.g.

    {'foo': FooVariant, 'bar': BarVariant}
    """

    def __init__(
        self,
        *,
        mapping: dict[str, type],
        discriminator_field: str,
        discriminator_alias: str | None,
    ) -> None:
        self.mapping = mapping
        self.field_name = discriminator_field
        self.field_alias_from = discriminator_alias


def _build_discriminated_union_meta(*, union: type, meta_annotations: tuple[Any, ...]) -> DiscriminatorDetails | None:
    if isinstance(union, CachedDiscriminatorType):
        return union.__discriminator__

    discriminator_field_name: str | None = None

    for annotation in meta_annotations:
        if isinstance(annotation, PropertyInfo) and annotation.discriminator is not None:
            discriminator_field_name = annotation.discriminator
            break

    if not discriminator_field_name:
        return None

    mapping: dict[str, type] = {}
    discriminator_alias: str | None = None

    for variant in get_args(union):
        variant = strip_annotated_type(variant)
        if is_basemodel_type(variant):
            if PYDANTIC_V2:
                field = _extract_field_schema_pv2(variant, discriminator_field_name)
                if not field:
                    continue

                # Note: if one variant defines an alias then they all should
                discriminator_alias = field.get("serialization_alias")

                field_schema = field["schema"]

                if field_schema["type"] == "literal":
                    for entry in cast("LiteralSchema", field_schema)["expected"]:
                        if isinstance(entry, str):
                            mapping[entry] = variant
            else:
                field_info = cast("dict[str, FieldInfo]", variant.__fields__).get(discriminator_field_name)  # pyright: ignore[reportDeprecated, reportUnnecessaryCast]
                if not field_info:
                    continue

                # Note: if one variant defines an alias then they all should
                discriminator_alias = field_info.alias

                if (annotation := getattr(field_info, "annotation", None)) and is_literal_type(annotation):
                    for entry in get_args(annotation):
                        if isinstance(entry, str):
                            mapping[entry] = variant

    if not mapping:
        return None

    details = DiscriminatorDetails(
        mapping=mapping,
        discriminator_field=discriminator_field_name,
        discriminator_alias=discriminator_alias,
    )
    cast(CachedDiscriminatorType, union).__discriminator__ = details
    return details


def _extract_field_schema_pv2(model: type[BaseModel], field_name: str) -> ModelField | None:
    schema = model.__pydantic_core_schema__
    if schema["type"] == "definitions":
        schema = schema["schema"]

    if schema["type"] != "model":
        return None

    schema = cast("ModelSchema", schema)
    fields_schema = schema["schema"]
    if fields_schema["type"] != "model-fields":
        return None

    fields_schema = cast("ModelFieldsSchema", fields_schema)
    field = fields_schema["fields"].get(field_name)
    if not field:
        return None

    return cast("ModelField", field)  # pyright: ignore[reportUnnecessaryCast]


def validate_type(*, type_: type[_T], value: object) -> _T:
    """Strict validation that the given value matches the expected type"""
    if inspect.isclass(type_) and issubclass(type_, pydantic.BaseModel):
        return cast(_T, parse_obj(type_, value))

    return cast(_T, _validate_non_model_type(type_=type_, value=value))


def set_pydantic_config(typ: Any, config: pydantic.ConfigDict) -> None:
    """Add a pydantic config for the given type.

    Note: this is a no-op on Pydantic v1.
    """
    setattr(typ, "__pydantic_config__", config)  # noqa: B010


def add_request_id(obj: BaseModel, request_id: str | None) -> None:
    obj._request_id = request_id

    # in Pydantic v1, using setattr like we do above causes the attribute
    # to be included when serializing the model which we don't want in this
    # case so we need to explicitly exclude it
    if not PYDANTIC_V2:
        try:
            exclude_fields = obj.__exclude_fields__  # type: ignore
        except AttributeError:
            cast(Any, obj).__exclude_fields__ = {"_request_id", "__exclude_fields__"}
        else:
            cast(Any, obj).__exclude_fields__ = {*(exclude_fields or {}), "_request_id", "__exclude_fields__"}


# our use of subclassing here causes weirdness for type checkers,
# so we just pretend that we don't subclass
if TYPE_CHECKING:
    GenericModel = BaseModel
else:

    class GenericModel(BaseGenericModel, BaseModel):
        pass


if PYDANTIC_V2:
    from pydantic import TypeAdapter as _TypeAdapter

    _CachedTypeAdapter = cast("TypeAdapter[object]", lru_cache(maxsize=None)(_TypeAdapter))

    if TYPE_CHECKING:
        from pydantic import TypeAdapter
    else:
        TypeAdapter = _CachedTypeAdapter

    def _validate_non_model_type(*, type_: type[_T], value: object) -> _T:
        return TypeAdapter(type_).validate_python(value)

elif not TYPE_CHECKING:  # TODO: condition is weird

    class RootModel(GenericModel, Generic[_T]):
        """Used as a placeholder to easily convert runtime types to a Pydantic format
        to provide validation.

        For example:
        ```py
        validated = RootModel[int](__root__="5").__root__
        # validated: 5
        ```
        """

        __root__: _T

    def _validate_non_model_type(*, type_: type[_T], value: object) -> _T:
        model = _create_pydantic_model(type_).validate(value)
        return cast(_T, model.__root__)

    def _create_pydantic_model(type_: _T) -> Type[RootModel[_T]]:
        return RootModel[type_]  # type: ignore


class FinalRequestOptionsInput(TypedDict, total=False):
    method: Required[str]
    url: Required[str]
    params: Query
    headers: Headers
    max_retries: int
    timeout: float | Timeout | None
    files: HttpxRequestFiles | None
    idempotency_key: str
    json_data: Body
    extra_json: AnyMapping
    follow_redirects: bool


@final
class FinalRequestOptions(pydantic.BaseModel):
    method: str
    url: str
    params: Query = {}
    headers: Union[Headers, NotGiven] = NotGiven()
    max_retries: Union[int, NotGiven] = NotGiven()
    timeout: Union[float, Timeout, None, NotGiven] = NotGiven()
    files: Union[HttpxRequestFiles, None] = None
    idempotency_key: Union[str, None] = None
    post_parser: Union[Callable[[Any], Any], NotGiven] = NotGiven()
    follow_redirects: Union[bool, None] = None

    # It should be noted that we cannot use `json` here as that would override
    # a BaseModel method in an incompatible fashion.
    json_data: Union[Body, None] = None
    extra_json: Union[AnyMapping, None] = None

    if PYDANTIC_V2:
        model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)
    else:

        class Config(pydantic.BaseConfig):  # pyright: ignore[reportDeprecated]
            arbitrary_types_allowed: bool = True

    def get_max_retries(self, max_retries: int) -> int:
        if isinstance(self.max_retries, NotGiven):
            return max_retries
        return self.max_retries

    def _strip_raw_response_header(self) -> None:
        if not is_given(self.headers):
            return

        if self.headers.get(RAW_RESPONSE_HEADER):
            self.headers = {**self.headers}
            self.headers.pop(RAW_RESPONSE_HEADER)

    # override the `construct` method so that we can run custom transformations.
    # this is necessary as we don't want to do any actual runtime type checking
    # (which means we can't use validators) but we do want to ensure that `NotGiven`
    # values are not present
    #
    # type ignore required because we're adding explicit types to `**values`
    @classmethod
    def construct(  # type: ignore
        cls,
        _fields_set: set[str] | None = None,
        **values: Unpack[FinalRequestOptionsInput],
    ) -> FinalRequestOptions:
        kwargs: dict[str, Any] = {
            # we unconditionally call `strip_not_given` on any value
            # as it will just ignore any non-mapping types
            key: strip_not_given(value)
            for key, value in values.items()
        }
        if PYDANTIC_V2:
            return super().model_construct(_fields_set, **kwargs)
        return cast(FinalRequestOptions, super().construct(_fields_set, **kwargs))  # pyright: ignore[reportDeprecated]

    if not TYPE_CHECKING:
        # type checkers incorrectly complain about this assignment
        model_construct = construct