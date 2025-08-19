
# === NexusCore/tools\exports\export_20250803_114325\combined_104.py ===

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\async_client.py ===
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

from google.api_core import operation  # type: ignore
from google.api_core import operation_async  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.model_service import pagers
from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model, model_service
from google.ai.generativelanguage_v1beta.types import tuned_model

from .client import ModelServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport


class ModelServiceAsyncClient:
    """Provides methods for getting metadata information about
    Generative Models.
    """

    _client: ModelServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = ModelServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = ModelServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(ModelServiceClient.model_path)
    parse_model_path = staticmethod(ModelServiceClient.parse_model_path)
    tuned_model_path = staticmethod(ModelServiceClient.tuned_model_path)
    parse_tuned_model_path = staticmethod(ModelServiceClient.parse_tuned_model_path)
    common_billing_account_path = staticmethod(
        ModelServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        ModelServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(ModelServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(ModelServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(ModelServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        ModelServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(ModelServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        ModelServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(ModelServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        ModelServiceClient.parse_common_location_path
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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_info.__func__(ModelServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_file.__func__(ModelServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return ModelServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client instance.
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
        type(ModelServiceClient).get_transport_class, type(ModelServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the ModelServiceTransport constructor.
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
        self._client = ModelServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def get_model(
        self,
        request: Optional[Union[model_service.GetModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> model.Model:
        r"""Gets information about a specific Model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Model:
                Information about a Generative
                Language Model.

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
        if not isinstance(request, model_service.GetModelRequest):
            request = model_service.GetModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_model
        ]

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

    async def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsAsyncPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListModelsRequest, dict]]):
                The request object. Request for listing all Models.
            page_size (:class:`int`):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                A page token, received from a previous ``ListModels``
                call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListModels`` must match the call that provided the
                page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.model_service.pagers.ListModelsAsyncPager:
                Response from ListModel containing a paginated list of
                Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListModelsRequest):
            request = model_service.ListModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_models
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
        response = pagers.ListModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_tuned_model(
        self,
        request: Optional[Union[model_service.GetTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> tuned_model.TunedModel:
        r"""Gets information about a specific TunedModel.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetTunedModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                Format: ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

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
        if not isinstance(request, model_service.GetTunedModelRequest):
            request = model_service.GetTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_tuned_model
        ]

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

    async def list_tuned_models(
        self,
        request: Optional[Union[model_service.ListTunedModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListTunedModelsAsyncPager:
        r"""Lists tuned models owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_tuned_models():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListTunedModelsRequest(
                )

                # Make the request
                page_result = client.list_tuned_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListTunedModelsRequest, dict]]):
                The request object. Request for listing TunedModels.
            page_size (:class:`int`):
                Optional. The maximum number of ``TunedModels`` to
                return (per page). The service may return fewer tuned
                models.

                If unspecified, at most 10 tuned models will be
                returned. This method returns at most 1000 models per
                page, even if you pass a larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                Optional. A page token, received from a previous
                ``ListTunedModels`` call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListTunedModels`` must match the call that provided
                the page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.model_service.pagers.ListTunedModelsAsyncPager:
                Response from ListTunedModels containing a paginated
                list of Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListTunedModelsRequest):
            request = model_service.ListTunedModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_tuned_models
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
        response = pagers.ListTunedModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def create_tuned_model(
        self,
        request: Optional[Union[model_service.CreateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        tuned_model_id: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operation_async.AsyncOperation:
        r"""Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta.CreateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                operation = client.create_tuned_model(request=request)

                print("Waiting for operation to complete...")

                response = (await operation).result()

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateTunedModelRequest, dict]]):
                The request object. Request to create a TunedModel.
            tuned_model (:class:`google.ai.generativelanguage_v1beta.types.TunedModel`):
                Required. The tuned model to create.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            tuned_model_id (:class:`str`):
                Optional. The unique id for the tuned model if
                specified. This value should be up to 40 characters, the
                first character must be a letter, the last could be a
                letter or a number. The id must match the regular
                expression: `a-z <[a-z0-9-]{0,38}[a-z0-9]>`__?.

                This corresponds to the ``tuned_model_id`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operation_async.AsyncOperation:
                An object representing a long-running operation.

                The result type for the operation will be
                :class:`google.ai.generativelanguage_v1beta.types.TunedModel`
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, tuned_model_id])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.CreateTunedModelRequest):
            request = model_service.CreateTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if tuned_model is not None:
            request.tuned_model = tuned_model
        if tuned_model_id is not None:
            request.tuned_model_id = tuned_model_id

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_tuned_model
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

        # Wrap the response in an operation future.
        response = operation_async.from_gapic(
            response,
            self._client._transport.operations_client,
            gag_tuned_model.TunedModel,
            metadata_type=model_service.CreateTunedModelMetadata,
        )

        # Done; return the response.
        return response

    async def update_tuned_model(
        self,
        request: Optional[Union[model_service.UpdateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_tuned_model.TunedModel:
        r"""Updates a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta.UpdateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                response = await client.update_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdateTunedModelRequest, dict]]):
                The request object. Request to update a TunedModel.
            tuned_model (:class:`google.ai.generativelanguage_v1beta.types.TunedModel`):
                Required. The tuned model to update.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to
                update.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.UpdateTunedModelRequest):
            request = model_service.UpdateTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if tuned_model is not None:
            request.tuned_model = tuned_model
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_tuned_model
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("tuned_model.name", request.tuned_model.name),)
            ),
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

    async def delete_tuned_model(
        self,
        request: Optional[Union[model_service.DeleteTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_tuned_model(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteTunedModelRequest, dict]]):
                The request object. Request to delete a TunedModel.
            name (:class:`str`):
                Required. The resource name of the model. Format:
                ``tunedModels/my-model-id``

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
        if not isinstance(request, model_service.DeleteTunedModelRequest):
            request = model_service.DeleteTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_tuned_model
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

    async def __aenter__(self) -> "ModelServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.api_core import operation  # type: ignore
from google.api_core import operation_async  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.services.model_service import pagers
from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model, model_service
from google.ai.generativelanguage_v1beta3.types import tuned_model

from .client import ModelServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport


class ModelServiceAsyncClient:
    """Provides methods for getting metadata information about
    Generative Models.
    """

    _client: ModelServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = ModelServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = ModelServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(ModelServiceClient.model_path)
    parse_model_path = staticmethod(ModelServiceClient.parse_model_path)
    tuned_model_path = staticmethod(ModelServiceClient.tuned_model_path)
    parse_tuned_model_path = staticmethod(ModelServiceClient.parse_tuned_model_path)
    common_billing_account_path = staticmethod(
        ModelServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        ModelServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(ModelServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(ModelServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(ModelServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        ModelServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(ModelServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        ModelServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(ModelServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        ModelServiceClient.parse_common_location_path
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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_info.__func__(ModelServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_file.__func__(ModelServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return ModelServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client instance.
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
        type(ModelServiceClient).get_transport_class, type(ModelServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the ModelServiceTransport constructor.
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
        self._client = ModelServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def get_model(
        self,
        request: Optional[Union[model_service.GetModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> model.Model:
        r"""Gets information about a specific Model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.GetModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Model:
                Information about a Generative
                Language Model.

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
        if not isinstance(request, model_service.GetModelRequest):
            request = model_service.GetModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_model
        ]

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

    async def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsAsyncPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.ListModelsRequest, dict]]):
                The request object. Request for listing all Models.
            page_size (:class:`int`):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                A page token, received from a previous ``ListModels``
                call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListModels`` must match the call that provided the
                page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.model_service.pagers.ListModelsAsyncPager:
                Response from ListModel containing a paginated list of
                Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListModelsRequest):
            request = model_service.ListModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_models
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
        response = pagers.ListModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_tuned_model(
        self,
        request: Optional[Union[model_service.GetTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> tuned_model.TunedModel:
        r"""Gets information about a specific TunedModel.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_get_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.GetTunedModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                Format: ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

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
        if not isinstance(request, model_service.GetTunedModelRequest):
            request = model_service.GetTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_tuned_model
        ]

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

    async def list_tuned_models(
        self,
        request: Optional[Union[model_service.ListTunedModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListTunedModelsAsyncPager:
        r"""Lists tuned models owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_list_tuned_models():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListTunedModelsRequest(
                )

                # Make the request
                page_result = client.list_tuned_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.ListTunedModelsRequest, dict]]):
                The request object. Request for listing TunedModels.
            page_size (:class:`int`):
                Optional. The maximum number of ``TunedModels`` to
                return (per page). The service may return fewer tuned
                models.

                If unspecified, at most 10 tuned models will be
                returned. This method returns at most 1000 models per
                page, even if you pass a larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                Optional. A page token, received from a previous
                ``ListTunedModels`` call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListTunedModels`` must match the call that provided
                the page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.model_service.pagers.ListTunedModelsAsyncPager:
                Response from ListTunedModels containing a paginated
                list of Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListTunedModelsRequest):
            request = model_service.ListTunedModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_tuned_models
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
        response = pagers.ListTunedModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def create_tuned_model(
        self,
        request: Optional[Union[model_service.CreateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        tuned_model_id: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operation_async.AsyncOperation:
        r"""Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_create_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta3.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta3.CreateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                operation = client.create_tuned_model(request=request)

                print("Waiting for operation to complete...")

                response = (await operation).result()

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.CreateTunedModelRequest, dict]]):
                The request object. Request to create a TunedModel.
            tuned_model (:class:`google.ai.generativelanguage_v1beta3.types.TunedModel`):
                Required. The tuned model to create.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            tuned_model_id (:class:`str`):
                Optional. The unique id for the tuned model if
                specified. This value should be up to 40 characters, the
                first character must be a letter, the last could be a
                letter or a number. The id must match the regular
                expression: `a-z <[a-z0-9-]{0,38}[a-z0-9]>`__?.

                This corresponds to the ``tuned_model_id`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operation_async.AsyncOperation:
                An object representing a long-running operation.

                The result type for the operation will be
                :class:`google.ai.generativelanguage_v1beta3.types.TunedModel`
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, tuned_model_id])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.CreateTunedModelRequest):
            request = model_service.CreateTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if tuned_model is not None:
            request.tuned_model = tuned_model
        if tuned_model_id is not None:
            request.tuned_model_id = tuned_model_id

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_tuned_model
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

        # Wrap the response in an operation future.
        response = operation_async.from_gapic(
            response,
            self._client._transport.operations_client,
            gag_tuned_model.TunedModel,
            metadata_type=model_service.CreateTunedModelMetadata,
        )

        # Done; return the response.
        return response

    async def update_tuned_model(
        self,
        request: Optional[Union[model_service.UpdateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_tuned_model.TunedModel:
        r"""Updates a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_update_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta3.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta3.UpdateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                response = await client.update_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.UpdateTunedModelRequest, dict]]):
                The request object. Request to update a TunedModel.
            tuned_model (:class:`google.ai.generativelanguage_v1beta3.types.TunedModel`):
                Required. The tuned model to update.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to
                update.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.UpdateTunedModelRequest):
            request = model_service.UpdateTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if tuned_model is not None:
            request.tuned_model = tuned_model
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_tuned_model
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("tuned_model.name", request.tuned_model.name),)
            ),
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

    async def delete_tuned_model(
        self,
        request: Optional[Union[model_service.DeleteTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_delete_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.DeleteTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_tuned_model(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.DeleteTunedModelRequest, dict]]):
                The request object. Request to delete a TunedModel.
            name (:class:`str`):
                Required. The resource name of the model. Format:
                ``tunedModels/my-model-id``

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
        if not isinstance(request, model_service.DeleteTunedModelRequest):
            request = model_service.DeleteTunedModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_tuned_model
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

    async def __aenter__(self) -> "ModelServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\sql.py ===
"""
    pygments.lexers.sql
    ~~~~~~~~~~~~~~~~~~~

    Lexers for various SQL dialects and related interactive sessions.

    Postgres specific lexers:

    `PostgresLexer`
        A SQL lexer for the PostgreSQL dialect. Differences w.r.t. the SQL
        lexer are:

        - keywords and data types list parsed from the PG docs (run the
          `_postgres_builtins` module to update them);
        - Content of $-strings parsed using a specific lexer, e.g. the content
          of a PL/Python function is parsed using the Python lexer;
        - parse PG specific constructs: E-strings, $-strings, U&-strings,
          different operators and punctuation.

    `PlPgsqlLexer`
        A lexer for the PL/pgSQL language. Adds a few specific construct on
        top of the PG SQL lexer (such as <<label>>).

    `PostgresConsoleLexer`
        A lexer to highlight an interactive psql session:

        - identifies the prompt and does its best to detect the end of command
          in multiline statement where not all the lines are prefixed by a
          prompt, telling them apart from the output;
        - highlights errors in the output and notification levels;
        - handles psql backslash commands.

    `PostgresExplainLexer`
        A lexer to highlight Postgres execution plan.

    The ``tests/examplefiles`` contains a few test files with data to be
    parsed by these lexers.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import collections
import re

from pygments.lexer import Lexer, RegexLexer, do_insertions, bygroups, words
from pygments.lexers import _googlesql_builtins
from pygments.lexers import _mysql_builtins
from pygments.lexers import _postgres_builtins
from pygments.lexers import _sql_builtins
from pygments.lexers import _tsql_builtins
from pygments.lexers import get_lexer_by_name, ClassNotFound
from pygments.token import Punctuation, Whitespace, Text, Comment, Operator, \
    Keyword, Name, String, Number, Generic, Literal


__all__ = ['GoogleSqlLexer', 'PostgresLexer', 'PlPgsqlLexer',
           'PostgresConsoleLexer', 'PostgresExplainLexer', 'SqlLexer',
           'TransactSqlLexer', 'MySqlLexer', 'SqliteConsoleLexer', 'RqlLexer']

line_re  = re.compile('.*?\n')
sqlite_prompt_re = re.compile(r'^(?:sqlite|   ...)>(?= )')

language_re = re.compile(r"\s+LANGUAGE\s+'?(\w+)'?", re.IGNORECASE)

do_re = re.compile(r'\bDO\b', re.IGNORECASE)

# Regular expressions for analyse_text()
name_between_bracket_re = re.compile(r'\[[a-zA-Z_]\w*\]')
name_between_backtick_re = re.compile(r'`[a-zA-Z_]\w*`')
tsql_go_re = re.compile(r'\bgo\b', re.IGNORECASE)
tsql_declare_re = re.compile(r'\bdeclare\s+@', re.IGNORECASE)
tsql_variable_re = re.compile(r'@[a-zA-Z_]\w*\b')

# Identifiers for analyse_text()
googlesql_identifiers = (
    _googlesql_builtins.functionnames
    + _googlesql_builtins.keywords
    + _googlesql_builtins.types)


def language_callback(lexer, match):
    """Parse the content of a $-string using a lexer

    The lexer is chosen looking for a nearby LANGUAGE or assumed as
    plpgsql if inside a DO statement and no LANGUAGE has been found.
    """
    lx = None
    m = language_re.match(lexer.text[match.end():match.end()+100])
    if m is not None:
        lx = lexer._get_lexer(m.group(1))
    else:
        m = list(language_re.finditer(
            lexer.text[max(0, match.start()-100):match.start()]))
        if m:
            lx = lexer._get_lexer(m[-1].group(1))
        else:
            m = list(do_re.finditer(
                lexer.text[max(0, match.start()-25):match.start()]))
            if m:
                lx = lexer._get_lexer('plpgsql')

    # 1 = $, 2 = delimiter, 3 = $
    yield (match.start(1), String, match.group(1))
    yield (match.start(2), String.Delimiter, match.group(2))
    yield (match.start(3), String, match.group(3))
    # 4 = string contents
    if lx:
        yield from lx.get_tokens_unprocessed(match.group(4))
    else:
        yield (match.start(4), String, match.group(4))
    # 5 = $, 6 = delimiter, 7 = $
    yield (match.start(5), String, match.group(5))
    yield (match.start(6), String.Delimiter, match.group(6))
    yield (match.start(7), String, match.group(7))


class PostgresBase:
    """Base class for Postgres-related lexers.

    This is implemented as a mixin to avoid the Lexer metaclass kicking in.
    this way the different lexer don't have a common Lexer ancestor. If they
    had, _tokens could be created on this ancestor and not updated for the
    other classes, resulting e.g. in PL/pgSQL parsed as SQL. This shortcoming
    seem to suggest that regexp lexers are not really subclassable.
    """
    def get_tokens_unprocessed(self, text, *args):
        # Have a copy of the entire text to be used by `language_callback`.
        self.text = text
        yield from super().get_tokens_unprocessed(text, *args)

    def _get_lexer(self, lang):
        if lang.lower() == 'sql':
            return get_lexer_by_name('postgresql', **self.options)

        tries = [lang]
        if lang.startswith('pl'):
            tries.append(lang[2:])
        if lang.endswith('u'):
            tries.append(lang[:-1])
        if lang.startswith('pl') and lang.endswith('u'):
            tries.append(lang[2:-1])

        for lx in tries:
            try:
                return get_lexer_by_name(lx, **self.options)
            except ClassNotFound:
                pass
        else:
            # TODO: better logging
            # print >>sys.stderr, "language not found:", lang
            return None


class PostgresLexer(PostgresBase, RegexLexer):
    """
    Lexer for the PostgreSQL dialect of SQL.
    """

    name = 'PostgreSQL SQL dialect'
    aliases = ['postgresql', 'postgres']
    mimetypes = ['text/x-postgresql']
    url = 'https://www.postgresql.org'
    version_added = '1.5'

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'--.*\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'(' + '|'.join(s.replace(" ", r"\s+")
                             for s in _postgres_builtins.DATATYPES +
                             _postgres_builtins.PSEUDO_TYPES) + r')\b',
             Name.Builtin),
            (words(_postgres_builtins.KEYWORDS, suffix=r'\b'), Keyword),
            (r'[+*/<>=~!@#%^&|`?-]+', Operator),
            (r'::', Operator),  # cast
            (r'\$\d+', Name.Variable),
            (r'([0-9]*\.[0-9]*|[0-9]+)(e[+-]?[0-9]+)?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r"((?:E|U&)?)(')", bygroups(String.Affix, String.Single), 'string'),
            # quoted identifier
            (r'((?:U&)?)(")', bygroups(String.Affix, String.Name), 'quoted-ident'),
            (r'(?s)(\$)([^$]*)(\$)(.*?)(\$)(\2)(\$)', language_callback),
            (r'[a-z_]\w*', Name),

            # psql variable in SQL
            (r""":(['"]?)[a-z]\w*\b\1""", Name.Variable),

            (r'[;:()\[\]{},.]', Punctuation),
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ],
        'string': [
            (r"[^']+", String.Single),
            (r"''", String.Single),
            (r"'", String.Single, '#pop'),
        ],
        'quoted-ident': [
            (r'[^"]+', String.Name),
            (r'""', String.Name),
            (r'"', String.Name, '#pop'),
        ],
    }


class PlPgsqlLexer(PostgresBase, RegexLexer):
    """
    Handle the extra syntax in Pl/pgSQL language.
    """
    name = 'PL/pgSQL'
    aliases = ['plpgsql']
    mimetypes = ['text/x-plpgsql']
    url = 'https://www.postgresql.org/docs/current/plpgsql.html'
    version_added = '1.5'

    flags = re.IGNORECASE
    # FIXME: use inheritance
    tokens = {name: state[:] for (name, state) in PostgresLexer.tokens.items()}

    # extend the keywords list
    for i, pattern in enumerate(tokens['root']):
        if pattern[1] == Keyword:
            tokens['root'][i] = (
                words(_postgres_builtins.KEYWORDS +
                      _postgres_builtins.PLPGSQL_KEYWORDS, suffix=r'\b'),
                Keyword)
            del i
            break
    else:
        assert 0, "SQL keywords not found"

    # Add specific PL/pgSQL rules (before the SQL ones)
    tokens['root'][:0] = [
        (r'\%[a-z]\w*\b', Name.Builtin),     # actually, a datatype
        (r':=', Operator),
        (r'\<\<[a-z]\w*\>\>', Name.Label),
        (r'\#[a-z]\w*\b', Keyword.Pseudo),   # #variable_conflict
    ]


class PsqlRegexLexer(PostgresBase, RegexLexer):
    """
    Extend the PostgresLexer adding support specific for psql commands.

    This is not a complete psql lexer yet as it lacks prompt support
    and output rendering.
    """

    name = 'PostgreSQL console - regexp based lexer'
    aliases = []    # not public

    flags = re.IGNORECASE
    tokens = {name: state[:] for (name, state) in PostgresLexer.tokens.items()}

    tokens['root'].append(
        (r'\\[^\s]+', Keyword.Pseudo, 'psql-command'))
    tokens['psql-command'] = [
        (r'\n', Text, 'root'),
        (r'\s+', Whitespace),
        (r'\\[^\s]+', Keyword.Pseudo),
        (r""":(['"]?)[a-z]\w*\b\1""", Name.Variable),
        (r"'(''|[^'])*'", String.Single),
        (r"`([^`])*`", String.Backtick),
        (r"[^\s]+", String.Symbol),
    ]


re_prompt = re.compile(r'^(\S.*?)??[=\-\(\$\'\"][#>]')
re_psql_command = re.compile(r'\s*\\')
re_end_command = re.compile(r';\s*(--.*?)?$')
re_psql_command = re.compile(r'(\s*)(\\.+?)(\s+)$')
re_error = re.compile(r'(ERROR|FATAL):')
re_message = re.compile(
    r'((?:DEBUG|INFO|NOTICE|WARNING|ERROR|'
    r'FATAL|HINT|DETAIL|CONTEXT|LINE [0-9]+):)(.*?\n)')


class lookahead:
    """Wrap an iterator and allow pushing back an item."""
    def __init__(self, x):
        self.iter = iter(x)
        self._nextitem = None

    def __iter__(self):
        return self

    def send(self, i):
        self._nextitem = i
        return i

    def __next__(self):
        if self._nextitem is not None:
            ni = self._nextitem
            self._nextitem = None
            return ni
        return next(self.iter)
    next = __next__


class PostgresConsoleLexer(Lexer):
    """
    Lexer for psql sessions.
    """

    name = 'PostgreSQL console (psql)'
    aliases = ['psql', 'postgresql-console', 'postgres-console']
    mimetypes = ['text/x-postgresql-psql']
    url = 'https://www.postgresql.org'
    version_added = '1.5'
    _example = "psql/psql_session.txt"

    def get_tokens_unprocessed(self, data):
        sql = PsqlRegexLexer(**self.options)

        lines = lookahead(line_re.findall(data))

        # prompt-output cycle
        while 1:

            # consume the lines of the command: start with an optional prompt
            # and continue until the end of command is detected
            curcode = ''
            insertions = []
            for line in lines:
                # Identify a shell prompt in case of psql commandline example
                if line.startswith('$') and not curcode:
                    lexer = get_lexer_by_name('console', **self.options)
                    yield from lexer.get_tokens_unprocessed(line)
                    break

                # Identify a psql prompt
                mprompt = re_prompt.match(line)
                if mprompt is not None:
                    insertions.append((len(curcode),
                                       [(0, Generic.Prompt, mprompt.group())]))
                    curcode += line[len(mprompt.group()):]
                else:
                    curcode += line

                # Check if this is the end of the command
                # TODO: better handle multiline comments at the end with
                # a lexer with an external state?
                if re_psql_command.match(curcode) \
                   or re_end_command.search(curcode):
                    break

            # Emit the combined stream of command and prompt(s)
            yield from do_insertions(insertions,
                                     sql.get_tokens_unprocessed(curcode))

            # Emit the output lines
            out_token = Generic.Output
            for line in lines:
                mprompt = re_prompt.match(line)
                if mprompt is not None:
                    # push the line back to have it processed by the prompt
                    lines.send(line)
                    break

                mmsg = re_message.match(line)
                if mmsg is not None:
                    if mmsg.group(1).startswith("ERROR") \
                       or mmsg.group(1).startswith("FATAL"):
                        out_token = Generic.Error
                    yield (mmsg.start(1), Generic.Strong, mmsg.group(1))
                    yield (mmsg.start(2), out_token, mmsg.group(2))
                else:
                    yield (0, out_token, line)
            else:
                return


class PostgresExplainLexer(RegexLexer):
    """
    Handle PostgreSQL EXPLAIN output
    """

    name = 'PostgreSQL EXPLAIN dialect'
    aliases = ['postgres-explain']
    filenames = ['*.explain']
    mimetypes = ['text/x-postgresql-explain']
    url = 'https://www.postgresql.org/docs/current/using-explain.html'
    version_added = '2.15'

    tokens = {
        'root': [
            (r'(:|\(|\)|ms|kB|->|\.\.|\,|\/)', Punctuation),
            (r'(\s+)', Whitespace),

            # This match estimated cost and effectively measured counters with ANALYZE
            # Then, we move to instrumentation state
            (r'(cost)(=?)', bygroups(Name.Class, Punctuation), 'instrumentation'),
            (r'(actual)( )(=?)', bygroups(Name.Class, Whitespace, Punctuation), 'instrumentation'),

            # Misc keywords
            (words(('actual', 'Memory Usage', 'Disk Usage', 'Memory', 'Buckets', 'Batches',
                    'originally', 'row', 'rows', 'Hits', 'Misses',
                    'Evictions', 'Overflows', 'Planned Partitions'), suffix=r'\b'),
             Comment.Single),

            (r'(hit|read|dirtied|written|write|time|calls)(=)', bygroups(Comment.Single, Operator)),
            (r'(shared|temp|local)', Keyword.Pseudo),

            # We move to sort state in order to emphasize specific keywords (especially disk access)
            (r'(Sort Method)(: )', bygroups(Comment.Preproc, Punctuation), 'sort'),

            # These keywords can be followed by an object, like a table
            (r'(Sort Key|Group Key|Presorted Key|Hash Key)(:)( )',
             bygroups(Comment.Preproc, Punctuation, Whitespace), 'object_name'),
            (r'(Cache Key|Cache Mode)(:)( )', bygroups(Comment, Punctuation, Whitespace), 'object_name'),

            # These keywords can be followed by a predicate
            (words(('Join Filter', 'Subplans Removed', 'Filter', 'Merge Cond',
                    'Hash Cond', 'Index Cond', 'Recheck Cond', 'Heap Blocks',
                    'TID Cond', 'Run Condition', 'Order By', 'Function Call',
                    'Table Function Call', 'Inner Unique', 'Params Evaluated',
                    'Single Copy', 'Sampling', 'One-Time Filter', 'Output',
                    'Relations', 'Remote SQL'), suffix=r'\b'),
             Comment.Preproc, 'predicate'),

            # Special keyword to handle ON CONFLICT
            (r'Conflict ', Comment.Preproc, 'conflict'),

            # Special keyword for InitPlan or SubPlan
            (r'(InitPlan|SubPlan)( )(\d+)( )',
             bygroups(Keyword, Whitespace, Number.Integer, Whitespace),
             'init_plan'),

            (words(('Sort Method', 'Join Filter', 'Planning time',
                    'Planning Time', 'Execution time', 'Execution Time',
                    'Workers Planned', 'Workers Launched', 'Buffers',
                    'Planning', 'Worker', 'Query Identifier', 'Time',
                    'Full-sort Groups', 'Pre-sorted Groups'), suffix=r'\b'), Comment.Preproc),

            # Emphasize these keywords

            (words(('Rows Removed by Join Filter', 'Rows Removed by Filter',
                    'Rows Removed by Index Recheck',
                    'Heap Fetches', 'never executed'),
                   suffix=r'\b'), Name.Exception),
            (r'(I/O Timings)(:)( )', bygroups(Name.Exception, Punctuation, Whitespace)),

            (words(_postgres_builtins.EXPLAIN_KEYWORDS, suffix=r'\b'), Keyword),

            # join keywords
            (r'((Right|Left|Full|Semi|Anti) Join)', Keyword.Type),
            (r'(Parallel |Async |Finalize |Partial )', Comment.Preproc),
            (r'Backward', Comment.Preproc),
            (r'(Intersect|Except|Hash)', Comment.Preproc),

            (r'(CTE)( )(\w*)?', bygroups(Comment, Whitespace, Name.Variable)),


            # Treat "on" and "using" as a punctuation
            (r'(on|using)', Punctuation, 'object_name'),


            # strings
            (r"'(''|[^'])*'", String.Single),
            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'(-?\d+)', Number.Integer),

            # boolean
            (r'(true|false)', Name.Constant),
            # explain header
            (r'\s*QUERY PLAN\s*\n\s*-+', Comment.Single),
            # Settings
            (r'(Settings)(:)( )', bygroups(Comment.Preproc, Punctuation, Whitespace), 'setting'),

            # Handle JIT counters
            (r'(JIT|Functions|Options|Timing)(:)', bygroups(Comment.Preproc, Punctuation)),
            (r'(Inlining|Optimization|Expressions|Deforming|Generation|Emission|Total)', Keyword.Pseudo),

            # Handle Triggers counters
            (r'(Trigger)( )(\S*)(:)( )',
             bygroups(Comment.Preproc, Whitespace, Name.Variable, Punctuation, Whitespace)),

        ],
        'expression': [
            # matches any kind of parenthesized expression
            # the first opening paren is matched by the 'caller'
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
            (r'(never executed)', Name.Exception),
            (r'[^)(]+', Comment),
        ],
        'object_name': [

            # This is a cost or analyze measure
            (r'(\(cost)(=?)', bygroups(Name.Class, Punctuation), 'instrumentation'),
            (r'(\(actual)( )(=?)', bygroups(Name.Class, Whitespace, Punctuation), 'instrumentation'),

            # if object_name is parenthesized, mark opening paren as
            # punctuation, call 'expression', and exit state
            (r'\(', Punctuation, 'expression'),
            (r'(on)', Punctuation),
            # matches possibly schema-qualified table and column names
            (r'\w+(\.\w+)*( USING \S+| \w+ USING \S+)', Name.Variable),
            (r'\"?\w+\"?(?:\.\"?\w+\"?)?', Name.Variable),
            (r'\'\S*\'', Name.Variable),

            # if we encounter a comma, another object is listed
            (r',\n', Punctuation, 'object_name'),
            (r',', Punctuation, 'object_name'),

            # special case: "*SELECT*"
            (r'"\*SELECT\*( \d+)?"(.\w+)?', Name.Variable),
            (r'"\*VALUES\*(_\d+)?"(.\w+)?', Name.Variable),
            (r'"ANY_subquery"', Name.Variable),

            # Variable $1 ...
            (r'\$\d+', Name.Variable),
            # cast
            (r'::\w+', Name.Variable),
            (r' +', Whitespace),
            (r'"', Punctuation),
            (r'\[\.\.\.\]', Punctuation),
            (r'\)', Punctuation, '#pop'),
        ],
        'predicate': [
            # if predicate is parenthesized, mark paren as punctuation
            (r'(\()([^\n]*)(\))', bygroups(Punctuation, Name.Variable, Punctuation), '#pop'),
            # otherwise color until newline
            (r'[^\n]*', Name.Variable, '#pop'),
        ],
        'instrumentation': [
            (r'=|\.\.', Punctuation),
            (r' +', Whitespace),
            (r'(rows|width|time|loops)', Name.Class),
            (r'\d+\.\d+', Number.Float),
            (r'(\d+)', Number.Integer),
            (r'\)', Punctuation, '#pop'),
        ],
        'conflict': [
            (r'(Resolution: )(\w+)', bygroups(Comment.Preproc, Name.Variable)),
            (r'(Arbiter \w+:)', Comment.Preproc, 'object_name'),
            (r'(Filter: )', Comment.Preproc, 'predicate'),
        ],
        'setting': [
            (r'([a-z_]*?)(\s*)(=)(\s*)(\'.*?\')', bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String)),
            (r'\, ', Punctuation),
        ],
        'init_plan': [
            (r'\(', Punctuation),
            (r'returns \$\d+(,\$\d+)?', Name.Variable),
            (r'\)', Punctuation, '#pop'),
        ],
        'sort': [
            (r':|kB', Punctuation),
            (r'(quicksort|top-N|heapsort|Average|Memory|Peak)', Comment.Prepoc),
            (r'(external|merge|Disk|sort)', Name.Exception),
            (r'(\d+)', Number.Integer),
            (r' +', Whitespace),
        ],
    }


class SqlLexer(RegexLexer):
    """
    Lexer for Structured Query Language. Currently, this lexer does
    not recognize any special syntax except ANSI SQL.
    """

    name = 'SQL'
    aliases = ['sql']
    filenames = ['*.sql']
    mimetypes = ['text/x-sql']
    url = 'https://en.wikipedia.org/wiki/SQL'
    version_added = ''

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'--.*\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (words(_sql_builtins.KEYWORDS, suffix=r'\b'), Keyword),
            (words(_sql_builtins.DATATYPES, suffix=r'\b'), Name.Builtin),
            (r'[+*/<>=~!@#%^&|`?-]', Operator),
            (r'[0-9]+', Number.Integer),
            # TODO: Backslash escapes?
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),  # not a real string literal in ANSI SQL
            (r'[a-z_][\w$]*', Name),  # allow $s in strings for Oracle
            (r'[;:()\[\],.]', Punctuation)
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }

    def analyse_text(self, text):
        return


class TransactSqlLexer(RegexLexer):
    """
    Transact-SQL (T-SQL) is Microsoft's and Sybase's proprietary extension to
    SQL.

    The list of keywords includes ODBC and keywords reserved for future use.
    """

    name = 'Transact-SQL'
    aliases = ['tsql', 't-sql']
    filenames = ['*.sql']
    mimetypes = ['text/x-tsql']
    url = 'https://www.tsql.info'
    version_added = ''

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'--.*[$|\n]?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (words(_tsql_builtins.OPERATORS), Operator),
            (words(_tsql_builtins.OPERATOR_WORDS, suffix=r'\b'), Operator.Word),
            (words(_tsql_builtins.TYPES, suffix=r'\b'), Name.Class),
            (words(_tsql_builtins.FUNCTIONS, suffix=r'\b'), Name.Function),
            (r'(goto)(\s+)(\w+\b)', bygroups(Keyword, Whitespace, Name.Label)),
            (words(_tsql_builtins.KEYWORDS, suffix=r'\b'), Keyword),
            (r'(\[)([^]]+)(\])', bygroups(Operator, Name, Operator)),
            (r'0x[0-9a-f]+', Number.Hex),
            # Float variant 1, for example: 1., 1.e2, 1.2e3
            (r'[0-9]+\.[0-9]*(e[+-]?[0-9]+)?', Number.Float),
            # Float variant 2, for example: .1, .1e2
            (r'\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),
            # Float variant 3, for example: 123e45
            (r'[0-9]+e[+-]?[0-9]+', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),
            (r'[;(),.]', Punctuation),
            # Below we use \w even for the first "real" character because
            # tokens starting with a digit have already been recognized
            # as Number above.
            (r'@@\w+', Name.Builtin),
            (r'@\w+', Name.Variable),
            (r'(\w+)(:)', bygroups(Name.Label, Punctuation)),
            (r'#?#?\w+', Name),  # names for temp tables and anything else
            (r'\?', Name.Variable.Magic),  # parameter for prepared statements
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }

    def analyse_text(text):
        rating = 0
        if tsql_declare_re.search(text):
            # Found T-SQL variable declaration.
            rating = 1.0
        else:
            name_between_backtick_count = len(
                name_between_backtick_re.findall(text))
            name_between_bracket_count = len(
                name_between_bracket_re.findall(text))
            # We need to check if there are any names using
            # backticks or brackets, as otherwise both are 0
            # and 0 >= 2 * 0, so we would always assume it's true
            dialect_name_count = name_between_backtick_count + name_between_bracket_count
            if dialect_name_count >= 1 and \
               name_between_bracket_count >= 2 * name_between_backtick_count:
                # Found at least twice as many [name] as `name`.
                rating += 0.5
            elif name_between_bracket_count > name_between_backtick_count:
                rating += 0.2
            elif name_between_bracket_count > 0:
                rating += 0.1
            if tsql_variable_re.search(text) is not None:
                rating += 0.1
            if tsql_go_re.search(text) is not None:
                rating += 0.1
        return rating


class MySqlLexer(RegexLexer):
    """The Oracle MySQL lexer.

    This lexer does not attempt to maintain strict compatibility with
    MariaDB syntax or keywords. Although MySQL and MariaDB's common code
    history suggests there may be significant overlap between the two,
    compatibility between the two is not a target for this lexer.
    """

    name = 'MySQL'
    aliases = ['mysql']
    mimetypes = ['text/x-mysql']
    url = 'https://www.mysql.com'
    version_added = ''

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Whitespace),

            # Comments
            (r'(?:#|--\s+).*', Comment.Single),
            (r'/\*\+', Comment.Special, 'optimizer-hints'),
            (r'/\*', Comment.Multiline, 'multiline-comment'),

            # Hexadecimal literals
            (r"x'([0-9a-f]{2})+'", Number.Hex),  # MySQL requires paired hex characters in this form.
            (r'0x[0-9a-f]+', Number.Hex),

            # Binary literals
            (r"b'[01]+'", Number.Bin),
            (r'0b[01]+', Number.Bin),

            # Numeric literals
            (r'[0-9]+\.[0-9]*(e[+-]?[0-9]+)?', Number.Float),  # Mandatory integer, optional fraction and exponent
            (r'[0-9]*\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),  # Mandatory fraction, optional integer and exponent
            (r'[0-9]+e[+-]?[0-9]+', Number.Float),  # Exponents with integer significands are still floats
            (r'[0-9]+(?=[^0-9a-z$_\u0080-\uffff])', Number.Integer),  # Integers that are not in a schema object name

            # Date literals
            (r"\{\s*d\s*(?P<quote>['\"])\s*\d{2}(\d{2})?.?\d{2}.?\d{2}\s*(?P=quote)\s*\}",
             Literal.Date),

            # Time literals
            (r"\{\s*t\s*(?P<quote>['\"])\s*(?:\d+\s+)?\d{1,2}.?\d{1,2}.?\d{1,2}(\.\d*)?\s*(?P=quote)\s*\}",
             Literal.Date),

            # Timestamp literals
            (
                r"\{\s*ts\s*(?P<quote>['\"])\s*"
                r"\d{2}(?:\d{2})?.?\d{2}.?\d{2}"  # Date part
                r"\s+"  # Whitespace between date and time
                r"\d{1,2}.?\d{1,2}.?\d{1,2}(\.\d*)?"  # Time part
                r"\s*(?P=quote)\s*\}",
                Literal.Date
            ),

            # String literals
            (r"'", String.Single, 'single-quoted-string'),
            (r'"', String.Double, 'double-quoted-string'),

            # Variables
            (r'@@(?:global\.|persist\.|persist_only\.|session\.)?[a-z_]+', Name.Variable),
            (r'@[a-z0-9_$.]+', Name.Variable),
            (r"@'", Name.Variable, 'single-quoted-variable'),
            (r'@"', Name.Variable, 'double-quoted-variable'),
            (r"@`", Name.Variable, 'backtick-quoted-variable'),
            (r'\?', Name.Variable),  # For demonstrating prepared statements

            # Operators
            (r'[!%&*+/:<=>^|~-]+', Operator),

            # Exceptions; these words tokenize differently in different contexts.
            (r'\b(set)(?!\s*\()', Keyword),
            (r'\b(character)(\s+)(set)\b', bygroups(Keyword, Whitespace, Keyword)),
            # In all other known cases, "SET" is tokenized by MYSQL_DATATYPES.

            (words(_mysql_builtins.MYSQL_CONSTANTS, prefix=r'\b', suffix=r'\b'),
             Name.Constant),
            (words(_mysql_builtins.MYSQL_DATATYPES, prefix=r'\b', suffix=r'\b'),
             Keyword.Type),
            (words(_mysql_builtins.MYSQL_KEYWORDS, prefix=r'\b', suffix=r'\b'),
             Keyword),
            (words(_mysql_builtins.MYSQL_FUNCTIONS, prefix=r'\b', suffix=r'\b(\s*)(\()'),
             bygroups(Name.Function, Whitespace, Punctuation)),

            # Schema object names
            #
            # Note: Although the first regex supports unquoted all-numeric
            # identifiers, this will not be a problem in practice because
            # numeric literals have already been handled above.
            #
            ('[0-9a-z$_\u0080-\uffff]+', Name),
            (r'`', Name.Quoted, 'schema-object-name'),

            # Punctuation
            (r'[(),.;]', Punctuation),
        ],

        # Multiline comment substates
        # ---------------------------

        'optimizer-hints': [
            (r'[^*a-z]+', Comment.Special),
            (r'\*/', Comment.Special, '#pop'),
            (words(_mysql_builtins.MYSQL_OPTIMIZER_HINTS, suffix=r'\b'),
             Comment.Preproc),
            ('[a-z]+', Comment.Special),
            (r'\*', Comment.Special),
        ],

        'multiline-comment': [
            (r'[^*]+', Comment.Multiline),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'\*', Comment.Multiline),
        ],

        # String substates
        # ----------------

        'single-quoted-string': [
            (r"[^'\\]+", String.Single),
            (r"''", String.Escape),
            (r"""\\[0'"bnrtZ\\%_]""", String.Escape),
            (r"'", String.Single, '#pop'),
        ],

        'double-quoted-string': [
            (r'[^"\\]+', String.Double),
            (r'""', String.Escape),
            (r"""\\[0'"bnrtZ\\%_]""", String.Escape),
            (r'"', String.Double, '#pop'),
        ],

        # Variable substates
        # ------------------

        'single-quoted-variable': [
            (r"[^']+", Name.Variable),
            (r"''", Name.Variable),
            (r"'", Name.Variable, '#pop'),
        ],

        'double-quoted-variable': [
            (r'[^"]+', Name.Variable),
            (r'""', Name.Variable),
            (r'"', Name.Variable, '#pop'),
        ],

        'backtick-quoted-variable': [
            (r'[^`]+', Name.Variable),
            (r'``', Name.Variable),
            (r'`', Name.Variable, '#pop'),
        ],

        # Schema object name substates
        # ----------------------------
        #
        # "Name.Quoted" and "Name.Quoted.Escape" are non-standard but
        # formatters will style them as "Name" by default but add
        # additional styles based on the token name. This gives users
        # flexibility to add custom styles as desired.
        #
        'schema-object-name': [
            (r'[^`]+', Name.Quoted),
            (r'``', Name.Quoted.Escape),
            (r'`', Name.Quoted, '#pop'),
        ],
    }

    def analyse_text(text):
        rating = 0
        name_between_backtick_count = len(
            name_between_backtick_re.findall(text))
        name_between_bracket_count = len(
            name_between_bracket_re.findall(text))
        # Same logic as above in the TSQL analysis
        dialect_name_count = name_between_backtick_count + name_between_bracket_count
        if dialect_name_count >= 1 and \
           name_between_backtick_count >= 2 * name_between_bracket_count:
            # Found at least twice as many `name` as [name].
            rating += 0.5
        elif name_between_backtick_count > name_between_bracket_count:
            rating += 0.2
        elif name_between_backtick_count > 0:
            rating += 0.1
        return rating


class GoogleSqlLexer(RegexLexer):
    """
    GoogleSQL is Google's standard SQL dialect, formerly known as ZetaSQL.

    The list of keywords includes reserved words for future use.
    """

    name = 'GoogleSQL'
    aliases = ['googlesql', 'zetasql']
    filenames = ['*.googlesql', '*.googlesql.sql']
    mimetypes = ['text/x-google-sql', 'text/x-google-sql-aux']
    url = 'https://cloud.google.com/bigquery/googlesql'
    version_added = '2.19'

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Whitespace),

            # Comments
            (r'(?:#|--\s+).*', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comment'),

            # Hexadecimal literals
            (r"x'([0-9a-f]{2})+'", Number.Hex),
            (r'0x[0-9a-f]+', Number.Hex),

            # Binary literals
            (r"b'[01]+'", Number.Bin),
            (r'0b[01]+', Number.Bin),

            # Numeric literals
            (r'[0-9]+\.[0-9]*(e[+-]?[0-9]+)?', Number.Float),  # Mandatory integer, optional fraction and exponent
            (r'[0-9]*\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),  # Mandatory fraction, optional integer and exponent
            (r'[0-9]+e[+-]?[0-9]+', Number.Float),  # Exponents with integer significands are still floats
            (r'[0-9]+(?=[^0-9a-z$_\u0080-\uffff])', Number.Integer),  # Integers that are not in a schema object name

            # Date literals
            (r"\{\s*d\s*(?P<quote>['\"])\s*\d{2}(\d{2})?.?\d{2}.?\d{2}\s*(?P=quote)\s*\}",
             Literal.Date),

            # Time literals
            (r"\{\s*t\s*(?P<quote>['\"])\s*(?:\d+\s+)?\d{1,2}.?\d{1,2}.?\d{1,2}(\.\d*)?\s*(?P=quote)\s*\}",
             Literal.Date),

            # Timestamp literals
            (
                r"\{\s*ts\s*(?P<quote>['\"])\s*"
                r"\d{2}(?:\d{2})?.?\d{2}.?\d{2}"  # Date part
                r"\s+"  # Whitespace between date and time
                r"\d{1,2}.?\d{1,2}.?\d{1,2}(\.\d*)?"  # Time part
                r"\s*(?P=quote)\s*\}",
                Literal.Date
            ),

            # String literals
            (r"'", String.Single, 'single-quoted-string'),
            (r'"', String.Double, 'double-quoted-string'),

            # Variables
            (r'@@(?:global\.|persist\.|persist_only\.|session\.)?[a-z_]+', Name.Variable),
            (r'@[a-z0-9_$.]+', Name.Variable),
            (r"@'", Name.Variable, 'single-quoted-variable'),
            (r'@"', Name.Variable, 'double-quoted-variable'),
            (r"@`", Name.Variable, 'backtick-quoted-variable'),
            (r'\?', Name.Variable),  # For demonstrating prepared statements

            # Exceptions; these words tokenize differently in different contexts.
            (r'\b(set)(?!\s*\()', Keyword),
            (r'\b(character)(\s+)(set)\b', bygroups(Keyword, Whitespace, Keyword)),

            # Constants, types, keywords, functions, operators
            (words(_googlesql_builtins.constants, prefix=r'\b', suffix=r'\b'), Name.Constant),
            (words(_googlesql_builtins.types, prefix=r'\b', suffix=r'\b'), Keyword.Type),
            (words(_googlesql_builtins.keywords, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(_googlesql_builtins.functionnames, prefix=r'\b', suffix=r'\b(\s*)(\()'),
             bygroups(Name.Function, Whitespace, Punctuation)),
            (words(_googlesql_builtins.operators, prefix=r'\b', suffix=r'\b'), Operator),

            # Schema object names
            #
            # Note: Although the first regex supports unquoted all-numeric
            # identifiers, this will not be a problem in practice because
            # numeric literals have already been handled above.
            #
            ('[0-9a-z$_\u0080-\uffff]+', Name),
            (r'`', Name.Quoted, 'schema-object-name'),

            # Punctuation
            (r'[(),.;]', Punctuation),
        ],

        # Multiline comment substates
        # ---------------------------

        'multiline-comment': [
            (r'[^*]+', Comment.Multiline),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'\*', Comment.Multiline),
        ],

        # String substates
        # ----------------

        'single-quoted-string': [
            (r"[^'\\]+", String.Single),
            (r"''", String.Escape),
            (r"""\\[0'"bnrtZ\\%_]""", String.Escape),
            (r"'", String.Single, '#pop'),
        ],

        'double-quoted-string': [
            (r'[^"\\]+', String.Double),
            (r'""', String.Escape),
            (r"""\\[0'"bnrtZ\\%_]""", String.Escape),
            (r'"', String.Double, '#pop'),
        ],

        # Variable substates
        # ------------------

        'single-quoted-variable': [
            (r"[^']+", Name.Variable),
            (r"''", Name.Variable),
            (r"'", Name.Variable, '#pop'),
        ],

        'double-quoted-variable': [
            (r'[^"]+', Name.Variable),
            (r'""', Name.Variable),
            (r'"', Name.Variable, '#pop'),
        ],

        'backtick-quoted-variable': [
            (r'[^`]+', Name.Variable),
            (r'``', Name.Variable),
            (r'`', Name.Variable, '#pop'),
        ],

        # Schema object name substates
        # ----------------------------
        #
        # "Name.Quoted" and "Name.Quoted.Escape" are non-standard but
        # formatters will style them as "Name" by default but add
        # additional styles based on the token name. This gives users
        # flexibility to add custom styles as desired.
        #
        'schema-object-name': [
            (r'[^`]+', Name.Quoted),
            (r'``', Name.Quoted.Escape),
            (r'`', Name.Quoted, '#pop'),
        ],
    }

    def analyse_text(text):
        tokens = collections.Counter(text.split())
        return 0.001 * sum(count for t, count in tokens.items()
                           if t in googlesql_identifiers)


class SqliteConsoleLexer(Lexer):
    """
    Lexer for example sessions using sqlite3.
    """

    name = 'sqlite3con'
    aliases = ['sqlite3']
    filenames = ['*.sqlite3-console']
    mimetypes = ['text/x-sqlite3-console']
    url = 'https://www.sqlite.org'
    version_added = '0.11'
    _example = "sqlite3/sqlite3.sqlite3-console"

    def get_tokens_unprocessed(self, data):
        sql = SqlLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(data):
            line = match.group()
            prompt_match = sqlite_prompt_re.match(line)
            if prompt_match is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:7])]))
                insertions.append((len(curcode),
                                   [(7, Whitespace, ' ')]))
                curcode += line[8:]
            else:
                if curcode:
                    yield from do_insertions(insertions,
                                             sql.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                if line.startswith('SQL error: '):
                    yield (match.start(), Generic.Traceback, line)
                else:
                    yield (match.start(), Generic.Output, line)
        if curcode:
            yield from do_insertions(insertions,
                                     sql.get_tokens_unprocessed(curcode))


class RqlLexer(RegexLexer):
    """
    Lexer for Relation Query Language.
    """
    name = 'RQL'
    url = 'http://www.logilab.org/project/rql'
    aliases = ['rql']
    filenames = ['*.rql']
    mimetypes = ['text/x-rql']
    version_added = '2.0'

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(DELETE|SET|INSERT|UNION|DISTINCT|WITH|WHERE|BEING|OR'
             r'|AND|NOT|GROUPBY|HAVING|ORDERBY|ASC|DESC|LIMIT|OFFSET'
             r'|TODAY|NOW|TRUE|FALSE|NULL|EXISTS)\b', Keyword),
            (r'[+*/<>=%-]', Operator),
            (r'(Any|is|instance_of|CWEType|CWRelation)\b', Name.Builtin),
            (r'[0-9]+', Number.Integer),
            (r'[A-Z_]\w*\??', Name),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Single),
            (r'[;:()\[\],.]', Punctuation)
        ],
    }

# === NexusCore/openenv\Lib\site-packages\jupyter_client\session.py ===
"""Session object for building, serializing, sending, and receiving messages.

The Session object supports serialization, HMAC signatures,
and metadata on messages.

Also defined here are utilities for working with Sessions:
* A SessionFactory to be used as a base class for configurables that work with
Sessions.
* A Message object for convenience that allows attribute-access to the msg dict.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import pickle
import pprint
import random
import typing as t
import warnings
from binascii import b2a_hex
from datetime import datetime, timezone
from hmac import compare_digest

# We are using compare_digest to limit the surface of timing attacks
import zmq.asyncio
from tornado.ioloop import IOLoop
from traitlets import (
    Any,
    Bool,
    CBytes,
    CUnicode,
    Dict,
    DottedObjectName,
    Instance,
    Integer,
    Set,
    TraitError,
    Unicode,
    observe,
)
from traitlets.config.configurable import Configurable, LoggingConfigurable
from traitlets.log import get_logger
from traitlets.utils.importstring import import_item
from zmq.eventloop.zmqstream import ZMQStream

from ._version import protocol_version
from .adapter import adapt
from .jsonutil import extract_dates, json_clean, json_default, squash_dates

PICKLE_PROTOCOL = pickle.DEFAULT_PROTOCOL

utc = timezone.utc

# -----------------------------------------------------------------------------
# utility functions
# -----------------------------------------------------------------------------


def squash_unicode(obj: t.Any) -> t.Any:
    """coerce unicode back to bytestrings."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            obj[key] = squash_unicode(obj[key])
            if isinstance(key, str):
                obj[squash_unicode(key)] = obj.pop(key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = squash_unicode(v)
    elif isinstance(obj, str):
        obj = obj.encode("utf8")
    return obj


# -----------------------------------------------------------------------------
# globals and defaults
# -----------------------------------------------------------------------------

# default values for the thresholds:
MAX_ITEMS = 64
MAX_BYTES = 1024

# ISO8601-ify datetime objects
# allow unicode
# disallow nan, because it's not actually valid JSON


def json_packer(obj: t.Any) -> bytes:
    """Convert a json object to a bytes."""
    try:
        return json.dumps(
            obj,
            default=json_default,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf8", errors="surrogateescape")
    except (TypeError, ValueError) as e:
        # Fallback to trying to clean the json before serializing
        packed = json.dumps(
            json_clean(obj),
            default=json_default,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf8", errors="surrogateescape")

        warnings.warn(
            f"Message serialization failed with:\n{e}\n"
            "Supporting this message is deprecated in jupyter-client 7, please make "
            "sure your message is JSON-compliant",
            stacklevel=2,
        )

        return packed


def json_unpacker(s: str | bytes) -> t.Any:
    """Convert a json bytes or string to an object."""
    if isinstance(s, bytes):
        s = s.decode("utf8", "replace")
    return json.loads(s)


def pickle_packer(o: t.Any) -> bytes:
    """Pack an object using the pickle module."""
    return pickle.dumps(squash_dates(o), PICKLE_PROTOCOL)


pickle_unpacker = pickle.loads

default_packer = json_packer
default_unpacker = json_unpacker

DELIM = b"<IDS|MSG>"
# singleton dummy tracker, which will always report as done
DONE = zmq.MessageTracker()

# -----------------------------------------------------------------------------
# Mixin tools for apps that use Sessions
# -----------------------------------------------------------------------------


def new_id() -> str:
    """Generate a new random id.

    Avoids problematic runtime import in stdlib uuid on Python 2.

    Returns
    -------

    id string (16 random bytes as hex-encoded text, chunks separated by '-')
    """
    buf = os.urandom(16)
    return "-".join(b2a_hex(x).decode("ascii") for x in (buf[:4], buf[4:]))


def new_id_bytes() -> bytes:
    """Return new_id as ascii bytes"""
    return new_id().encode("ascii")


session_aliases = {
    "ident": "Session.session",
    "user": "Session.username",
    "keyfile": "Session.keyfile",
}

session_flags = {
    "secure": (
        {"Session": {"key": new_id_bytes(), "keyfile": ""}},
        """Use HMAC digests for authentication of messages.
        Setting this flag will generate a new UUID to use as the HMAC key.
        """,
    ),
    "no-secure": (
        {"Session": {"key": b"", "keyfile": ""}},
        """Don't authenticate messages.""",
    ),
}


def default_secure(cfg: t.Any) -> None:  # pragma: no cover
    """Set the default behavior for a config environment to be secure.

    If Session.key/keyfile have not been set, set Session.key to
    a new random UUID.
    """
    warnings.warn("default_secure is deprecated", DeprecationWarning, stacklevel=2)
    if "Session" in cfg and ("key" in cfg.Session or "keyfile" in cfg.Session):
        return
    # key/keyfile not specified, generate new UUID:
    cfg.Session.key = new_id_bytes()


def utcnow() -> datetime:
    """Return timezone-aware UTC timestamp"""
    return datetime.now(utc)


# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------


class SessionFactory(LoggingConfigurable):
    """The Base class for configurables that have a Session, Context, logger,
    and IOLoop.
    """

    logname = Unicode("")

    @observe("logname")
    def _logname_changed(self, change: t.Any) -> None:
        self.log = logging.getLogger(change["new"])

    # not configurable:
    context = Instance("zmq.Context")

    def _context_default(self) -> zmq.Context:
        return zmq.Context()

    session = Instance("jupyter_client.session.Session", allow_none=True)

    loop = Instance("tornado.ioloop.IOLoop")

    def _loop_default(self) -> IOLoop:
        return IOLoop.current()

    def __init__(self, **kwargs: t.Any) -> None:
        """Initialize a session factory."""
        super().__init__(**kwargs)

        if self.session is None:
            # construct the session
            self.session = Session(**kwargs)


class Message:
    """A simple message object that maps dict keys to attributes.

    A Message can be created from a dict and a dict from a Message instance
    simply by calling dict(msg_obj)."""

    def __init__(self, msg_dict: dict[str, t.Any]) -> None:
        """Initialize a message."""
        dct = self.__dict__
        for k, v in dict(msg_dict).items():
            if isinstance(v, dict):
                v = Message(v)  # noqa
            dct[k] = v

    # Having this iterator lets dict(msg_obj) work out of the box.
    def __iter__(self) -> t.ItemsView[str, t.Any]:
        return iter(self.__dict__.items())  # type:ignore[return-value]

    def __repr__(self) -> str:
        return repr(self.__dict__)

    def __str__(self) -> str:
        return pprint.pformat(self.__dict__)

    def __contains__(self, k: object) -> bool:
        return k in self.__dict__

    def __getitem__(self, k: str) -> t.Any:
        return self.__dict__[k]


def msg_header(
    msg_id: str, msg_type: str, username: str, session: Session | str
) -> dict[str, t.Any]:
    """Create a new message header"""
    date = utcnow()
    version = protocol_version
    return locals()


def extract_header(msg_or_header: dict[str, t.Any]) -> dict[str, t.Any]:
    """Given a message or header, return the header."""
    if not msg_or_header:
        return {}
    try:
        # See if msg_or_header is the entire message.
        h = msg_or_header["header"]
    except KeyError:
        try:
            # See if msg_or_header is just the header
            h = msg_or_header["msg_id"]
        except KeyError:
            raise
        else:
            h = msg_or_header
    if not isinstance(h, dict):
        h = dict(h)
    return h


class Session(Configurable):
    """Object for handling serialization and sending of messages.

    The Session object handles building messages and sending them
    with ZMQ sockets or ZMQStream objects.  Objects can communicate with each
    other over the network via Session objects, and only need to work with the
    dict-based IPython message spec. The Session will handle
    serialization/deserialization, security, and metadata.

    Sessions support configurable serialization via packer/unpacker traits,
    and signing with HMAC digests via the key/keyfile traits.

    Parameters
    ----------

    debug : bool
        whether to trigger extra debugging statements
    packer/unpacker : str : 'json', 'pickle' or import_string
        importstrings for methods to serialize message parts.  If just
        'json' or 'pickle', predefined JSON and pickle packers will be used.
        Otherwise, the entire importstring must be used.

        The functions must accept at least valid JSON input, and output *bytes*.

        For example, to use msgpack:
        packer = 'msgpack.packb', unpacker='msgpack.unpackb'
    pack/unpack : callables
        You can also set the pack/unpack callables for serialization directly.
    session : bytes
        the ID of this Session object.  The default is to generate a new UUID.
    username : unicode
        username added to message headers.  The default is to ask the OS.
    key : bytes
        The key used to initialize an HMAC signature.  If unset, messages
        will not be signed or checked.
    keyfile : filepath
        The file containing a key.  If this is set, `key` will be initialized
        to the contents of the file.

    """

    debug = Bool(False, config=True, help="""Debug output in the Session""")

    check_pid = Bool(
        True,
        config=True,
        help="""Whether to check PID to protect against calls after fork.

        This check can be disabled if fork-safety is handled elsewhere.
        """,
    )

    packer = DottedObjectName(
        "json",
        config=True,
        help="""The name of the packer for serializing messages.
            Should be one of 'json', 'pickle', or an import name
            for a custom callable serializer.""",
    )

    @observe("packer")
    def _packer_changed(self, change: t.Any) -> None:
        new = change["new"]
        if new.lower() == "json":
            self.pack = json_packer
            self.unpack = json_unpacker
            self.unpacker = new
        elif new.lower() == "pickle":
            self.pack = pickle_packer
            self.unpack = pickle_unpacker
            self.unpacker = new
        else:
            self.pack = import_item(str(new))

    unpacker = DottedObjectName(
        "json",
        config=True,
        help="""The name of the unpacker for unserializing messages.
        Only used with custom functions for `packer`.""",
    )

    @observe("unpacker")
    def _unpacker_changed(self, change: t.Any) -> None:
        new = change["new"]
        if new.lower() == "json":
            self.pack = json_packer
            self.unpack = json_unpacker
            self.packer = new
        elif new.lower() == "pickle":
            self.pack = pickle_packer
            self.unpack = pickle_unpacker
            self.packer = new
        else:
            self.unpack = import_item(str(new))

    session = CUnicode("", config=True, help="""The UUID identifying this session.""")

    def _session_default(self) -> str:
        u = new_id()
        self.bsession = u.encode("ascii")
        return u

    @observe("session")
    def _session_changed(self, change: t.Any) -> None:
        self.bsession = self.session.encode("ascii")

    # bsession is the session as bytes
    bsession = CBytes(b"")

    username = Unicode(
        os.environ.get("USER", "username"),
        help="""Username for the Session. Default is your system username.""",
        config=True,
    )

    metadata = Dict(
        {},
        config=True,
        help="Metadata dictionary, which serves as the default top-level metadata dict for each "
        "message.",
    )

    # if 0, no adapting to do.
    adapt_version = Integer(0)

    # message signature related traits:

    key = CBytes(config=True, help="""execution key, for signing messages.""")

    def _key_default(self) -> bytes:
        return new_id_bytes()

    @observe("key")
    def _key_changed(self, change: t.Any) -> None:
        self._new_auth()

    signature_scheme = Unicode(
        "hmac-sha256",
        config=True,
        help="""The digest scheme used to construct the message signatures.
        Must have the form 'hmac-HASH'.""",
    )

    @observe("signature_scheme")
    def _signature_scheme_changed(self, change: t.Any) -> None:
        new = change["new"]
        if not new.startswith("hmac-"):
            raise TraitError("signature_scheme must start with 'hmac-', got %r" % new)
        hash_name = new.split("-", 1)[1]
        try:
            self.digest_mod = getattr(hashlib, hash_name)
        except AttributeError as e:
            raise TraitError("hashlib has no such attribute: %s" % hash_name) from e
        self._new_auth()

    digest_mod = Any()

    def _digest_mod_default(self) -> t.Callable:
        return hashlib.sha256

    auth = Instance(hmac.HMAC, allow_none=True)

    def _new_auth(self) -> None:
        if self.key:
            self.auth = hmac.HMAC(self.key, digestmod=self.digest_mod)
        else:
            self.auth = None

    digest_history = Set()
    digest_history_size = Integer(
        2**16,
        config=True,
        help="""The maximum number of digests to remember.

        The digest history will be culled when it exceeds this value.
        """,
    )

    keyfile = Unicode("", config=True, help="""path to file containing execution key.""")

    @observe("keyfile")
    def _keyfile_changed(self, change: t.Any) -> None:
        with open(change["new"], "rb") as f:
            self.key = f.read().strip()

    # for protecting against sends from forks
    pid = Integer()

    # serialization traits:

    pack = Any(default_packer)  # the actual packer function

    @observe("pack")
    def _pack_changed(self, change: t.Any) -> None:
        new = change["new"]
        if not callable(new):
            raise TypeError("packer must be callable, not %s" % type(new))

    unpack = Any(default_unpacker)  # the actual packer function

    @observe("unpack")
    def _unpack_changed(self, change: t.Any) -> None:
        # unpacker is not checked - it is assumed to be
        new = change["new"]
        if not callable(new):
            raise TypeError("unpacker must be callable, not %s" % type(new))

    # thresholds:
    copy_threshold = Integer(
        2**16,
        config=True,
        help="Threshold (in bytes) beyond which a buffer should be sent without copying.",
    )
    buffer_threshold = Integer(
        MAX_BYTES,
        config=True,
        help="Threshold (in bytes) beyond which an object's buffer should be extracted to avoid "
        "pickling.",
    )
    item_threshold = Integer(
        MAX_ITEMS,
        config=True,
        help="""The maximum number of items for a container to be introspected for custom serialization.
        Containers larger than this are pickled outright.
        """,
    )

    def __init__(self, **kwargs: t.Any) -> None:
        """create a Session object

        Parameters
        ----------

        debug : bool
            whether to trigger extra debugging statements
        packer/unpacker : str : 'json', 'pickle' or import_string
            importstrings for methods to serialize message parts.  If just
            'json' or 'pickle', predefined JSON and pickle packers will be used.
            Otherwise, the entire importstring must be used.

            The functions must accept at least valid JSON input, and output
            *bytes*.

            For example, to use msgpack:
            packer = 'msgpack.packb', unpacker='msgpack.unpackb'
        pack/unpack : callables
            You can also set the pack/unpack callables for serialization
            directly.
        session : unicode (must be ascii)
            the ID of this Session object.  The default is to generate a new
            UUID.
        bsession : bytes
            The session as bytes
        username : unicode
            username added to message headers.  The default is to ask the OS.
        key : bytes
            The key used to initialize an HMAC signature.  If unset, messages
            will not be signed or checked.
        signature_scheme : str
            The message digest scheme. Currently must be of the form 'hmac-HASH',
            where 'HASH' is a hashing function available in Python's hashlib.
            The default is 'hmac-sha256'.
            This is ignored if 'key' is empty.
        keyfile : filepath
            The file containing a key.  If this is set, `key` will be
            initialized to the contents of the file.
        """
        super().__init__(**kwargs)
        self._check_packers()
        self.none = self.pack({})
        # ensure self._session_default() if necessary, so bsession is defined:
        self.session  # noqa
        self.pid = os.getpid()
        self._new_auth()
        if not self.key:
            get_logger().warning(
                "Message signing is disabled.  This is insecure and not recommended!"
            )

    def clone(self) -> Session:
        """Create a copy of this Session

        Useful when connecting multiple times to a given kernel.
        This prevents a shared digest_history warning about duplicate digests
        due to multiple connections to IOPub in the same process.

        .. versionadded:: 5.1
        """
        # make a copy
        new_session = type(self)()
        for name in self.traits():
            setattr(new_session, name, getattr(self, name))
        # fork digest_history
        new_session.digest_history = set()
        new_session.digest_history.update(self.digest_history)
        return new_session

    message_count = 0

    @property
    def msg_id(self) -> str:
        message_number = self.message_count
        self.message_count += 1
        return f"{self.session}_{os.getpid()}_{message_number}"

    def _check_packers(self) -> None:
        """check packers for datetime support."""
        pack = self.pack
        unpack = self.unpack

        # check simple serialization
        msg_list = {"a": [1, "hi"]}
        try:
            packed = pack(msg_list)
        except Exception as e:
            msg = f"packer '{self.packer}' could not serialize a simple message: {e}"
            raise ValueError(msg) from e

        # ensure packed message is bytes
        if not isinstance(packed, bytes):
            raise ValueError("message packed to %r, but bytes are required" % type(packed))

        # check that unpack is pack's inverse
        try:
            unpacked = unpack(packed)
            assert unpacked == msg_list
        except Exception as e:
            msg = (
                f"unpacker '{self.unpacker}' could not handle output from packer"
                f" '{self.packer}': {e}"
            )
            raise ValueError(msg) from e

        # check datetime support
        msg_datetime = {"t": utcnow()}
        try:
            unpacked = unpack(pack(msg_datetime))
            if isinstance(unpacked["t"], datetime):
                msg = "Shouldn't deserialize to datetime"
                raise ValueError(msg)
        except Exception:
            self.pack = lambda o: pack(squash_dates(o))
            self.unpack = lambda s: unpack(s)

    def msg_header(self, msg_type: str) -> dict[str, t.Any]:
        """Create a header for a message type."""
        return msg_header(self.msg_id, msg_type, self.username, self.session)

    def msg(
        self,
        msg_type: str,
        content: dict | None = None,
        parent: dict[str, t.Any] | None = None,
        header: dict[str, t.Any] | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any]:
        """Return the nested message dict.

        This format is different from what is sent over the wire. The
        serialize/deserialize methods converts this nested message dict to the wire
        format, which is a list of message parts.
        """
        msg = {}
        header = self.msg_header(msg_type) if header is None else header
        msg["header"] = header
        msg["msg_id"] = header["msg_id"]
        msg["msg_type"] = header["msg_type"]
        msg["parent_header"] = {} if parent is None else extract_header(parent)
        msg["content"] = {} if content is None else content
        msg["metadata"] = self.metadata.copy()
        if metadata is not None:
            msg["metadata"].update(metadata)
        return msg

    def sign(self, msg_list: list) -> bytes:
        """Sign a message with HMAC digest. If no auth, return b''.

        Parameters
        ----------
        msg_list : list
            The [p_header,p_parent,p_content] part of the message list.
        """
        if self.auth is None:
            return b""
        h = self.auth.copy()
        for m in msg_list:
            h.update(m)
        return h.hexdigest().encode()

    def serialize(
        self,
        msg: dict[str, t.Any],
        ident: list[bytes] | bytes | None = None,
    ) -> list[bytes]:
        """Serialize the message components to bytes.

        This is roughly the inverse of deserialize. The serialize/deserialize
        methods work with full message lists, whereas pack/unpack work with
        the individual message parts in the message list.

        Parameters
        ----------
        msg : dict or Message
            The next message dict as returned by the self.msg method.

        Returns
        -------
        msg_list : list
            The list of bytes objects to be sent with the format::

                [ident1, ident2, ..., DELIM, HMAC, p_header, p_parent,
                 p_metadata, p_content, buffer1, buffer2, ...]

            In this list, the ``p_*`` entities are the packed or serialized
            versions, so if JSON is used, these are utf8 encoded JSON strings.
        """
        content = msg.get("content", {})
        if content is None:
            content = self.none
        elif isinstance(content, dict):
            content = self.pack(content)
        elif isinstance(content, bytes):
            # content is already packed, as in a relayed message
            pass
        elif isinstance(content, str):
            # should be bytes, but JSON often spits out unicode
            content = content.encode("utf8")
        else:
            raise TypeError("Content incorrect type: %s" % type(content))

        real_message = [
            self.pack(msg["header"]),
            self.pack(msg["parent_header"]),
            self.pack(msg["metadata"]),
            content,
        ]

        to_send = []

        if isinstance(ident, list):
            # accept list of idents
            to_send.extend(ident)
        elif ident is not None:
            to_send.append(ident)
        to_send.append(DELIM)

        signature = self.sign(real_message)
        to_send.append(signature)

        to_send.extend(real_message)

        return to_send

    def send(
        self,
        stream: zmq.sugar.socket.Socket | ZMQStream | None,
        msg_or_type: dict[str, t.Any] | str,
        content: dict[str, t.Any] | None = None,
        parent: dict[str, t.Any] | None = None,
        ident: bytes | list[bytes] | None = None,
        buffers: list[bytes] | None = None,
        track: bool = False,
        header: dict[str, t.Any] | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any] | None:
        """Build and send a message via stream or socket.

        The message format used by this function internally is as follows:

        [ident1,ident2,...,DELIM,HMAC,p_header,p_parent,p_content,
         buffer1,buffer2,...]

        The serialize/deserialize methods convert the nested message dict into this
        format.

        Parameters
        ----------

        stream : zmq.Socket or ZMQStream
            The socket-like object used to send the data.
        msg_or_type : str or Message/dict
            Normally, msg_or_type will be a msg_type unless a message is being
            sent more than once. If a header is supplied, this can be set to
            None and the msg_type will be pulled from the header.

        content : dict or None
            The content of the message (ignored if msg_or_type is a message).
        header : dict or None
            The header dict for the message (ignored if msg_to_type is a message).
        parent : Message or dict or None
            The parent or parent header describing the parent of this message
            (ignored if msg_or_type is a message).
        ident : bytes or list of bytes
            The zmq.IDENTITY routing path.
        metadata : dict or None
            The metadata describing the message
        buffers : list or None
            The already-serialized buffers to be appended to the message.
        track : bool
            Whether to track.  Only for use with Sockets, because ZMQStream
            objects cannot track messages.


        Returns
        -------
        msg : dict
            The constructed message.
        """
        if not isinstance(stream, zmq.Socket):
            # ZMQStreams and dummy sockets do not support tracking.
            track = False

        if isinstance(stream, zmq.asyncio.Socket):
            assert stream is not None  # type:ignore[unreachable]
            stream = zmq.Socket.shadow(stream.underlying)

        if isinstance(msg_or_type, (Message, dict)):
            # We got a Message or message dict, not a msg_type so don't
            # build a new Message.
            msg = msg_or_type
            buffers = buffers or msg.get("buffers", [])
        else:
            msg = self.msg(
                msg_or_type,
                content=content,
                parent=parent,
                header=header,
                metadata=metadata,
            )
        if self.check_pid and os.getpid() != self.pid:
            get_logger().warning("WARNING: attempted to send message from fork\n%s", msg)
            return None
        buffers = [] if buffers is None else buffers
        for idx, buf in enumerate(buffers):
            if isinstance(buf, memoryview):
                view = buf
            else:
                try:
                    # check to see if buf supports the buffer protocol.
                    view = memoryview(buf)
                except TypeError as e:
                    emsg = "Buffer objects must support the buffer protocol."
                    raise TypeError(emsg) from e
            # memoryview.contiguous is new in 3.3,
            # just skip the check on Python 2
            if hasattr(view, "contiguous") and not view.contiguous:
                # zmq requires memoryviews to be contiguous
                raise ValueError("Buffer %i (%r) is not contiguous" % (idx, buf))

        if self.adapt_version:
            msg = adapt(msg, self.adapt_version)
        to_send = self.serialize(msg, ident)
        to_send.extend(buffers)
        longest = max([len(s) for s in to_send])
        copy = longest < self.copy_threshold

        if stream and buffers and track and not copy:
            # only really track when we are doing zero-copy buffers
            tracker = stream.send_multipart(to_send, copy=False, track=True)
        elif stream:
            # use dummy tracker, which will be done immediately
            tracker = DONE
            stream.send_multipart(to_send, copy=copy)
        else:
            tracker = DONE

        if self.debug:
            pprint.pprint(msg)  # noqa
            pprint.pprint(to_send)  # noqa
            pprint.pprint(buffers)  # noqa

        msg["tracker"] = tracker

        return msg

    def send_raw(
        self,
        stream: zmq.sugar.socket.Socket,
        msg_list: list,
        flags: int = 0,
        copy: bool = True,
        ident: bytes | list[bytes] | None = None,
    ) -> None:
        """Send a raw message via ident path.

        This method is used to send a already serialized message.

        Parameters
        ----------
        stream : ZMQStream or Socket
            The ZMQ stream or socket to use for sending the message.
        msg_list : list
            The serialized list of messages to send. This only includes the
            [p_header,p_parent,p_metadata,p_content,buffer1,buffer2,...] portion of
            the message.
        ident : ident or list
            A single ident or a list of idents to use in sending.
        """
        to_send = []
        if isinstance(ident, bytes):
            ident = [ident]
        if ident is not None:
            to_send.extend(ident)

        to_send.append(DELIM)
        # Don't include buffers in signature (per spec).
        to_send.append(self.sign(msg_list[0:4]))
        to_send.extend(msg_list)
        if isinstance(stream, zmq.asyncio.Socket):
            stream = zmq.Socket.shadow(stream.underlying)
        stream.send_multipart(to_send, flags, copy=copy)

    def recv(
        self,
        socket: zmq.sugar.socket.Socket,
        mode: int = zmq.NOBLOCK,
        content: bool = True,
        copy: bool = True,
    ) -> tuple[list[bytes] | None, dict[str, t.Any] | None]:
        """Receive and unpack a message.

        Parameters
        ----------
        socket : ZMQStream or Socket
            The socket or stream to use in receiving.

        Returns
        -------
        [idents], msg
            [idents] is a list of idents and msg is a nested message dict of
            same format as self.msg returns.
        """
        if isinstance(socket, ZMQStream):  # type:ignore[unreachable]
            socket = socket.socket  # type:ignore[unreachable]
        if isinstance(socket, zmq.asyncio.Socket):
            socket = zmq.Socket.shadow(socket.underlying)

        try:
            msg_list = socket.recv_multipart(mode, copy=copy)
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                # We can convert EAGAIN to None as we know in this case
                # recv_multipart won't return None.
                return None, None
            else:
                raise
        # split multipart message into identity list and message dict
        # invalid large messages can cause very expensive string comparisons
        idents, msg_list = self.feed_identities(msg_list, copy)
        try:
            return idents, self.deserialize(msg_list, content=content, copy=copy)
        except Exception as e:
            # TODO: handle it
            raise e

    def feed_identities(
        self, msg_list: list[bytes] | list[zmq.Message], copy: bool = True
    ) -> tuple[list[bytes], list[bytes] | list[zmq.Message]]:
        """Split the identities from the rest of the message.

        Feed until DELIM is reached, then return the prefix as idents and
        remainder as msg_list. This is easily broken by setting an IDENT to DELIM,
        but that would be silly.

        Parameters
        ----------
        msg_list : a list of Message or bytes objects
            The message to be split.
        copy : bool
            flag determining whether the arguments are bytes or Messages

        Returns
        -------
        (idents, msg_list) : two lists
            idents will always be a list of bytes, each of which is a ZMQ
            identity. msg_list will be a list of bytes or zmq.Messages of the
            form [HMAC,p_header,p_parent,p_content,buffer1,buffer2,...] and
            should be unpackable/unserializable via self.deserialize at this
            point.
        """
        if copy:
            msg_list = t.cast(t.List[bytes], msg_list)
            idx = msg_list.index(DELIM)
            return msg_list[:idx], msg_list[idx + 1 :]
        else:
            msg_list = t.cast(t.List[zmq.Message], msg_list)
            failed = True
            for idx, m in enumerate(msg_list):  # noqa
                if m.bytes == DELIM:
                    failed = False
                    break
            if failed:
                msg = "DELIM not in msg_list"
                raise ValueError(msg)
            idents, msg_list = msg_list[:idx], msg_list[idx + 1 :]
            return [bytes(m.bytes) for m in idents], msg_list

    def _add_digest(self, signature: bytes) -> None:
        """add a digest to history to protect against replay attacks"""
        if self.digest_history_size == 0:
            # no history, never add digests
            return

        self.digest_history.add(signature)
        if len(self.digest_history) > self.digest_history_size:
            # threshold reached, cull 10%
            self._cull_digest_history()

    def _cull_digest_history(self) -> None:
        """cull the digest history

        Removes a randomly selected 10% of the digest history
        """
        current = len(self.digest_history)
        n_to_cull = max(int(current // 10), current - self.digest_history_size)
        if n_to_cull >= current:
            self.digest_history = set()
            return
        to_cull = random.sample(tuple(sorted(self.digest_history)), n_to_cull)
        self.digest_history.difference_update(to_cull)

    def deserialize(
        self,
        msg_list: list[bytes] | list[zmq.Message],
        content: bool = True,
        copy: bool = True,
    ) -> dict[str, t.Any]:
        """Unserialize a msg_list to a nested message dict.

        This is roughly the inverse of serialize. The serialize/deserialize
        methods work with full message lists, whereas pack/unpack work with
        the individual message parts in the message list.

        Parameters
        ----------
        msg_list : list of bytes or Message objects
            The list of message parts of the form [HMAC,p_header,p_parent,
            p_metadata,p_content,buffer1,buffer2,...].
        content : bool (True)
            Whether to unpack the content dict (True), or leave it packed
            (False).
        copy : bool (True)
            Whether msg_list contains bytes (True) or the non-copying Message
            objects in each place (False).

        Returns
        -------
        msg : dict
            The nested message dict with top-level keys [header, parent_header,
            content, buffers].  The buffers are returned as memoryviews.
        """
        minlen = 5
        message = {}
        if not copy:
            # pyzmq didn't copy the first parts of the message, so we'll do it
            msg_list = t.cast(t.List[zmq.Message], msg_list)
            msg_list_beginning = [bytes(msg.bytes) for msg in msg_list[:minlen]]
            msg_list = t.cast(t.List[bytes], msg_list)
            msg_list = msg_list_beginning + msg_list[minlen:]
        msg_list = t.cast(t.List[bytes], msg_list)
        if self.auth is not None:
            signature = msg_list[0]
            if not signature:
                msg = "Unsigned Message"
                raise ValueError(msg)
            if signature in self.digest_history:
                raise ValueError("Duplicate Signature: %r" % signature)
            if content:
                # Only store signature if we are unpacking content, don't store if just peeking.
                self._add_digest(signature)
            check = self.sign(msg_list[1:5])
            if not compare_digest(signature, check):
                msg = "Invalid Signature: %r" % signature
                raise ValueError(msg)
        if not len(msg_list) >= minlen:
            msg = "malformed message, must have at least %i elements" % minlen
            raise TypeError(msg)
        header = self.unpack(msg_list[1])
        message["header"] = extract_dates(header)
        message["msg_id"] = header["msg_id"]
        message["msg_type"] = header["msg_type"]
        message["parent_header"] = extract_dates(self.unpack(msg_list[2]))
        message["metadata"] = self.unpack(msg_list[3])
        if content:
            message["content"] = self.unpack(msg_list[4])
        else:
            message["content"] = msg_list[4]
        buffers = [memoryview(b) for b in msg_list[5:]]
        if buffers and buffers[0].shape is None:
            # force copy to workaround pyzmq #646
            msg_list = t.cast(t.List[zmq.Message], msg_list)
            buffers = [memoryview(bytes(b.bytes)) for b in msg_list[5:]]
        message["buffers"] = buffers
        if self.debug:
            pprint.pprint(message)  # noqa
        # adapt to the current version
        return adapt(message)

    def unserialize(self, *args: t.Any, **kwargs: t.Any) -> dict[str, t.Any]:
        """**DEPRECATED** Use deserialize instead."""
        # pragma: no cover
        warnings.warn(
            "Session.unserialize is deprecated. Use Session.deserialize.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.deserialize(*args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\generative_service\async_client.py ===
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
    AsyncIterable,
    Awaitable,
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

from google.ai.generativelanguage_v1 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.types import content
from google.ai.generativelanguage_v1.types import content as gag_content
from google.ai.generativelanguage_v1.types import generative_service

from .client import GenerativeServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .transports.grpc_asyncio import GenerativeServiceGrpcAsyncIOTransport


class GenerativeServiceAsyncClient:
    """API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.
    """

    _client: GenerativeServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = GenerativeServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = GenerativeServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = GenerativeServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = GenerativeServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(GenerativeServiceClient.model_path)
    parse_model_path = staticmethod(GenerativeServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        GenerativeServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        GenerativeServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(GenerativeServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        GenerativeServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        GenerativeServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        GenerativeServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(GenerativeServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        GenerativeServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(GenerativeServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        GenerativeServiceClient.parse_common_location_path
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
            GenerativeServiceAsyncClient: The constructed client.
        """
        return GenerativeServiceClient.from_service_account_info.__func__(GenerativeServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            GenerativeServiceAsyncClient: The constructed client.
        """
        return GenerativeServiceClient.from_service_account_file.__func__(GenerativeServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return GenerativeServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> GenerativeServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            GenerativeServiceTransport: The transport used by the client instance.
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
        type(GenerativeServiceClient).get_transport_class, type(GenerativeServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                GenerativeServiceTransport,
                Callable[..., GenerativeServiceTransport],
            ]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the generative service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,GenerativeServiceTransport,Callable[..., GenerativeServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the GenerativeServiceTransport constructor.
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
        self._client = GenerativeServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateContentResponse:
        r"""Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_generate_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.generate_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.GenerateContentRequest, dict]]):
                The request object. Request to generate a completion from
                the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.GenerateContentResponse:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_content
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

    def stream_generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> Awaitable[AsyncIterable[generative_service.GenerateContentResponse]]:
        r"""Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_stream_generate_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                stream = await client.stream_generate_content(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.GenerateContentRequest, dict]]):
                The request object. Request to generate a completion from
                the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[google.ai.generativelanguage_v1.types.GenerateContentResponse]:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.stream_generate_content
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def embed_content(
        self,
        request: Optional[Union[generative_service.EmbedContentRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        content: Optional[gag_content.Content] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.EmbedContentResponse:
        r"""Generates an embedding from the model given an input
        ``Content``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_embed_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.EmbedContentRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.embed_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.EmbedContentRequest, dict]]):
                The request object. Request containing the ``Content`` for the model to
                embed.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            content (:class:`google.ai.generativelanguage_v1.types.Content`):
                Required. The content to embed. Only the ``parts.text``
                fields will be counted.

                This corresponds to the ``content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.EmbedContentResponse:
                The response to an EmbedContentRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.EmbedContentRequest):
            request = generative_service.EmbedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if content is not None:
            request.content = content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.embed_content
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

    async def batch_embed_contents(
        self,
        request: Optional[
            Union[generative_service.BatchEmbedContentsRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        requests: Optional[
            MutableSequence[generative_service.EmbedContentRequest]
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.BatchEmbedContentsResponse:
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
            from google.ai import generativelanguage_v1

            async def sample_batch_embed_contents():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1.EmbedContentRequest()
                requests.model = "model_value"

                request = generativelanguage_v1.BatchEmbedContentsRequest(
                    model="model_value",
                    requests=requests,
                )

                # Make the request
                response = await client.batch_embed_contents(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.BatchEmbedContentsRequest, dict]]):
                The request object. Batch request to get embeddings from
                the model for a list of prompts.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            requests (:class:`MutableSequence[google.ai.generativelanguage_v1.types.EmbedContentRequest]`):
                Required. Embed requests for the batch. The model in
                each of these requests must match the model specified
                ``BatchEmbedContentsRequest.model``.

                This corresponds to the ``requests`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.BatchEmbedContentsResponse:
                The response to a BatchEmbedContentsRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, requests])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.BatchEmbedContentsRequest):
            request = generative_service.BatchEmbedContentsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if requests:
            request.requests.extend(requests)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_embed_contents
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

    async def count_tokens(
        self,
        request: Optional[Union[generative_service.CountTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.CountTokensResponse:
        r"""Runs a model's tokenizer on input content and returns
        the token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_count_tokens():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.CountTokensRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.count_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.CountTokensRequest, dict]]):
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
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1.types.Content]`):
                Optional. The input given to the model as a prompt. This
                field is ignored when ``generate_content_request`` is
                set.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.CountTokensResponse:
                A response from CountTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.CountTokensRequest):
            request = generative_service.CountTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_tokens
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

    async def list_operations(
        self,
        request: Optional[operations_pb2.ListOperationsRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.ListOperationsResponse:
        r"""Lists operations that match the specified filter in the request.

        Args:
            request (:class:`~.operations_pb2.ListOperationsRequest`):
                The request object. Request message for
                `ListOperations` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.ListOperationsResponse:
                Response message for ``ListOperations`` method.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.ListOperationsRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.list_operations,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

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

    async def get_operation(
        self,
        request: Optional[operations_pb2.GetOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Gets the latest state of a long-running operation.

        Args:
            request (:class:`~.operations_pb2.GetOperationRequest`):
                The request object. Request message for
                `GetOperation` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.Operation:
                An ``Operation`` object.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.GetOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.get_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

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

    async def cancel_operation(
        self,
        request: Optional[operations_pb2.CancelOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Starts asynchronous cancellation on a long-running operation.

        The server makes a best effort to cancel the operation, but success
        is not guaranteed.  If the server doesn't support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.

        Args:
            request (:class:`~.operations_pb2.CancelOperationRequest`):
                The request object. Request message for
                `CancelOperation` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            None
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.CancelOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.cancel_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

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

    async def __aenter__(self) -> "GenerativeServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("GenerativeServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\generative_service\async_client.py ===
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
    AsyncIterable,
    Awaitable,
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

from google.ai.generativelanguage_v1beta.types import generative_service, safety
from google.ai.generativelanguage_v1beta.types import content
from google.ai.generativelanguage_v1beta.types import content as gag_content

from .client import GenerativeServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .transports.grpc_asyncio import GenerativeServiceGrpcAsyncIOTransport


class GenerativeServiceAsyncClient:
    """API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.
    """

    _client: GenerativeServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = GenerativeServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = GenerativeServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = GenerativeServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = GenerativeServiceClient._DEFAULT_UNIVERSE

    cached_content_path = staticmethod(GenerativeServiceClient.cached_content_path)
    parse_cached_content_path = staticmethod(
        GenerativeServiceClient.parse_cached_content_path
    )
    model_path = staticmethod(GenerativeServiceClient.model_path)
    parse_model_path = staticmethod(GenerativeServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        GenerativeServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        GenerativeServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(GenerativeServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        GenerativeServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        GenerativeServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        GenerativeServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(GenerativeServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        GenerativeServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(GenerativeServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        GenerativeServiceClient.parse_common_location_path
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
            GenerativeServiceAsyncClient: The constructed client.
        """
        return GenerativeServiceClient.from_service_account_info.__func__(GenerativeServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            GenerativeServiceAsyncClient: The constructed client.
        """
        return GenerativeServiceClient.from_service_account_file.__func__(GenerativeServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return GenerativeServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> GenerativeServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            GenerativeServiceTransport: The transport used by the client instance.
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
        type(GenerativeServiceClient).get_transport_class, type(GenerativeServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                GenerativeServiceTransport,
                Callable[..., GenerativeServiceTransport],
            ]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the generative service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,GenerativeServiceTransport,Callable[..., GenerativeServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the GenerativeServiceTransport constructor.
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
        self._client = GenerativeServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateContentResponse:
        r"""Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_generate_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.generate_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GenerateContentRequest, dict]]):
                The request object. Request to generate a completion from
                the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateContentResponse:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_content
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

    async def generate_answer(
        self,
        request: Optional[Union[generative_service.GenerateAnswerRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        safety_settings: Optional[MutableSequence[safety.SafetySetting]] = None,
        answer_style: Optional[
            generative_service.GenerateAnswerRequest.AnswerStyle
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateAnswerResponse:
        r"""Generates a grounded answer from the model given an input
        ``GenerateAnswerRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_generate_answer():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateAnswerRequest(
                    model="model_value",
                    answer_style="VERBOSE",
                )

                # Make the request
                response = await client.generate_answer(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GenerateAnswerRequest, dict]]):
                The request object. Request to generate a grounded answer
                from the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the grounded response.

                Format: ``model=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.Content]`):
                Required. The content of the current conversation with
                the model. For single-turn queries, this is a single
                question to answer. For multi-turn queries, this is a
                repeated field that contains conversation history and
                the last ``Content`` in the list containing the
                question.

                Note: GenerateAnswer currently only supports queries in
                English.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            safety_settings (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.SafetySetting]`):
                Optional. A list of unique ``SafetySetting`` instances
                for blocking unsafe content.

                This will be enforced on the
                ``GenerateAnswerRequest.contents`` and
                ``GenerateAnswerResponse.candidate``. There should not
                be more than one setting for each ``SafetyCategory``
                type. The API will block any contents and responses that
                fail to meet the thresholds set by these settings. This
                list overrides the default settings for each
                ``SafetyCategory`` specified in the safety_settings. If
                there is no ``SafetySetting`` for a given
                ``SafetyCategory`` provided in the list, the API will
                use the default safety setting for that category. Harm
                categories HARM_CATEGORY_HATE_SPEECH,
                HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HARM_CATEGORY_DANGEROUS_CONTENT,
                HARM_CATEGORY_HARASSMENT are supported.

                This corresponds to the ``safety_settings`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            answer_style (:class:`google.ai.generativelanguage_v1beta.types.GenerateAnswerRequest.AnswerStyle`):
                Required. Style in which answers
                should be returned.

                This corresponds to the ``answer_style`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateAnswerResponse:
                Response from the model for a
                grounded answer.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents, safety_settings, answer_style])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateAnswerRequest):
            request = generative_service.GenerateAnswerRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if answer_style is not None:
            request.answer_style = answer_style
        if contents:
            request.contents.extend(contents)
        if safety_settings:
            request.safety_settings.extend(safety_settings)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_answer
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

    def stream_generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> Awaitable[AsyncIterable[generative_service.GenerateContentResponse]]:
        r"""Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_stream_generate_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                stream = await client.stream_generate_content(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GenerateContentRequest, dict]]):
                The request object. Request to generate a completion from
                the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[google.ai.generativelanguage_v1beta.types.GenerateContentResponse]:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.stream_generate_content
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def embed_content(
        self,
        request: Optional[Union[generative_service.EmbedContentRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        content: Optional[gag_content.Content] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.EmbedContentResponse:
        r"""Generates an embedding from the model given an input
        ``Content``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_embed_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.EmbedContentRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.embed_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.EmbedContentRequest, dict]]):
                The request object. Request containing the ``Content`` for the model to
                embed.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            content (:class:`google.ai.generativelanguage_v1beta.types.Content`):
                Required. The content to embed. Only the ``parts.text``
                fields will be counted.

                This corresponds to the ``content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.EmbedContentResponse:
                The response to an EmbedContentRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.EmbedContentRequest):
            request = generative_service.EmbedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if content is not None:
            request.content = content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.embed_content
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

    async def batch_embed_contents(
        self,
        request: Optional[
            Union[generative_service.BatchEmbedContentsRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        requests: Optional[
            MutableSequence[generative_service.EmbedContentRequest]
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.BatchEmbedContentsResponse:
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

            async def sample_batch_embed_contents():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.EmbedContentRequest()
                requests.model = "model_value"

                request = generativelanguage_v1beta.BatchEmbedContentsRequest(
                    model="model_value",
                    requests=requests,
                )

                # Make the request
                response = await client.batch_embed_contents(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.BatchEmbedContentsRequest, dict]]):
                The request object. Batch request to get embeddings from
                the model for a list of prompts.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            requests (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.EmbedContentRequest]`):
                Required. Embed requests for the batch. The model in
                each of these requests must match the model specified
                ``BatchEmbedContentsRequest.model``.

                This corresponds to the ``requests`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchEmbedContentsResponse:
                The response to a BatchEmbedContentsRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, requests])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.BatchEmbedContentsRequest):
            request = generative_service.BatchEmbedContentsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if requests:
            request.requests.extend(requests)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_embed_contents
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

    async def count_tokens(
        self,
        request: Optional[Union[generative_service.CountTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.CountTokensResponse:
        r"""Runs a model's tokenizer on input content and returns
        the token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_count_tokens():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CountTokensRequest(
                    model="model_value",
                )

                # Make the request
                response = await client.count_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CountTokensRequest, dict]]):
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
            contents (:class:`MutableSequence[google.ai.generativelanguage_v1beta.types.Content]`):
                Optional. The input given to the model as a prompt. This
                field is ignored when ``generate_content_request`` is
                set.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountTokensResponse:
                A response from CountTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.CountTokensRequest):
            request = generative_service.CountTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_tokens
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

    async def __aenter__(self) -> "GenerativeServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("GenerativeServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\decoder.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Code for decoding protocol buffer primitives.

This code is very similar to encoder.py -- read the docs for that module first.

A "decoder" is a function with the signature:
  Decode(buffer, pos, end, message, field_dict)
The arguments are:
  buffer:     The string containing the encoded message.
  pos:        The current position in the string.
  end:        The position in the string where the current message ends.  May be
              less than len(buffer) if we're reading a sub-message.
  message:    The message object into which we're parsing.
  field_dict: message._fields (avoids a hashtable lookup).
The decoder reads the field and stores it into field_dict, returning the new
buffer position.  A decoder for a repeated field may proactively decode all of
the elements of that field, if they appear consecutively.

Note that decoders may throw any of the following:
  IndexError:  Indicates a truncated message.
  struct.error:  Unpacking of a fixed-width field failed.
  message.DecodeError:  Other errors.

Decoders are expected to raise an exception if they are called with pos > end.
This allows callers to be lax about bounds checking:  it's fineto read past
"end" as long as you are sure that someone else will notice and throw an
exception later on.

Something up the call stack is expected to catch IndexError and struct.error
and convert them to message.DecodeError.

Decoders are constructed using decoder constructors with the signature:
  MakeDecoder(field_number, is_repeated, is_packed, key, new_default)
The arguments are:
  field_number:  The field number of the field we want to decode.
  is_repeated:   Is the field a repeated field? (bool)
  is_packed:     Is the field a packed field? (bool)
  key:           The key to use when looking up the field within field_dict.
                 (This is actually the FieldDescriptor but nothing in this
                 file should depend on that.)
  new_default:   A function which takes a message object as a parameter and
                 returns a new instance of the default value for this field.
                 (This is called for repeated fields and sub-messages, when an
                 instance does not already exist.)

As with encoders, we define a decoder constructor for every type of field.
Then, for every field of every message class we construct an actual decoder.
That decoder goes into a dict indexed by tag, so when we decode a message
we repeatedly read a tag, look up the corresponding decoder, and invoke it.
"""

__author__ = 'kenton@google.com (Kenton Varda)'

import math
import struct

from google.protobuf.internal import containers
from google.protobuf.internal import encoder
from google.protobuf.internal import wire_format
from google.protobuf import message


# This is not for optimization, but rather to avoid conflicts with local
# variables named "message".
_DecodeError = message.DecodeError


def _VarintDecoder(mask, result_type):
  """Return an encoder for a basic varint value (does not include tag).

  Decoded values will be bitwise-anded with the given mask before being
  returned, e.g. to limit them to 32 bits.  The returned decoder does not
  take the usual "end" parameter -- the caller is expected to do bounds checking
  after the fact (often the caller can defer such checking until later).  The
  decoder returns a (value, new_pos) pair.
  """

  def DecodeVarint(buffer, pos):
    result = 0
    shift = 0
    while 1:
      b = buffer[pos]
      result |= ((b & 0x7f) << shift)
      pos += 1
      if not (b & 0x80):
        result &= mask
        result = result_type(result)
        return (result, pos)
      shift += 7
      if shift >= 64:
        raise _DecodeError('Too many bytes when decoding varint.')
  return DecodeVarint


def _SignedVarintDecoder(bits, result_type):
  """Like _VarintDecoder() but decodes signed values."""

  signbit = 1 << (bits - 1)
  mask = (1 << bits) - 1

  def DecodeVarint(buffer, pos):
    result = 0
    shift = 0
    while 1:
      b = buffer[pos]
      result |= ((b & 0x7f) << shift)
      pos += 1
      if not (b & 0x80):
        result &= mask
        result = (result ^ signbit) - signbit
        result = result_type(result)
        return (result, pos)
      shift += 7
      if shift >= 64:
        raise _DecodeError('Too many bytes when decoding varint.')
  return DecodeVarint

# All 32-bit and 64-bit values are represented as int.
_DecodeVarint = _VarintDecoder((1 << 64) - 1, int)
_DecodeSignedVarint = _SignedVarintDecoder(64, int)

# Use these versions for values which must be limited to 32 bits.
_DecodeVarint32 = _VarintDecoder((1 << 32) - 1, int)
_DecodeSignedVarint32 = _SignedVarintDecoder(32, int)


def ReadTag(buffer, pos):
  """Read a tag from the memoryview, and return a (tag_bytes, new_pos) tuple.

  We return the raw bytes of the tag rather than decoding them.  The raw
  bytes can then be used to look up the proper decoder.  This effectively allows
  us to trade some work that would be done in pure-python (decoding a varint)
  for work that is done in C (searching for a byte string in a hash table).
  In a low-level language it would be much cheaper to decode the varint and
  use that, but not in Python.

  Args:
    buffer: memoryview object of the encoded bytes
    pos: int of the current position to start from

  Returns:
    Tuple[bytes, int] of the tag data and new position.
  """
  start = pos
  while buffer[pos] & 0x80:
    pos += 1
  pos += 1

  tag_bytes = buffer[start:pos].tobytes()
  return tag_bytes, pos


# --------------------------------------------------------------------


def _SimpleDecoder(wire_type, decode_value):
  """Return a constructor for a decoder for fields of a particular type.

  Args:
      wire_type:  The field's wire type.
      decode_value:  A function which decodes an individual value, e.g.
        _DecodeVarint()
  """

  def SpecificDecoder(field_number, is_repeated, is_packed, key, new_default,
                      clear_if_default=False):
    if is_packed:
      local_DecodeVarint = _DecodeVarint
      def DecodePackedField(
          buffer, pos, end, message, field_dict, current_depth=0
      ):
        del current_depth # unused
        value = field_dict.get(key)
        if value is None:
          value = field_dict.setdefault(key, new_default(message))
        (endpoint, pos) = local_DecodeVarint(buffer, pos)
        endpoint += pos
        if endpoint > end:
          raise _DecodeError('Truncated message.')
        while pos < endpoint:
          (element, pos) = decode_value(buffer, pos)
          value.append(element)
        if pos > endpoint:
          del value[-1]   # Discard corrupt value.
          raise _DecodeError('Packed element was truncated.')
        return pos
      return DecodePackedField
    elif is_repeated:
      tag_bytes = encoder.TagBytes(field_number, wire_type)
      tag_len = len(tag_bytes)
      def DecodeRepeatedField(
          buffer, pos, end, message, field_dict, current_depth=0
      ):
        del current_depth # unused
        value = field_dict.get(key)
        if value is None:
          value = field_dict.setdefault(key, new_default(message))
        while 1:
          (element, new_pos) = decode_value(buffer, pos)
          value.append(element)
          # Predict that the next tag is another copy of the same repeated
          # field.
          pos = new_pos + tag_len
          if buffer[new_pos:pos] != tag_bytes or new_pos >= end:
            # Prediction failed.  Return.
            if new_pos > end:
              raise _DecodeError('Truncated message.')
            return new_pos
      return DecodeRepeatedField
    else:
      def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
        del current_depth # unused
        (new_value, pos) = decode_value(buffer, pos)
        if pos > end:
          raise _DecodeError('Truncated message.')
        if clear_if_default and not new_value:
          field_dict.pop(key, None)
        else:
          field_dict[key] = new_value
        return pos
      return DecodeField

  return SpecificDecoder


def _ModifiedDecoder(wire_type, decode_value, modify_value):
  """Like SimpleDecoder but additionally invokes modify_value on every value
  before storing it.  Usually modify_value is ZigZagDecode.
  """

  # Reusing _SimpleDecoder is slightly slower than copying a bunch of code, but
  # not enough to make a significant difference.

  def InnerDecode(buffer, pos):
    (result, new_pos) = decode_value(buffer, pos)
    return (modify_value(result), new_pos)
  return _SimpleDecoder(wire_type, InnerDecode)


def _StructPackDecoder(wire_type, format):
  """Return a constructor for a decoder for a fixed-width field.

  Args:
      wire_type:  The field's wire type.
      format:  The format string to pass to struct.unpack().
  """

  value_size = struct.calcsize(format)
  local_unpack = struct.unpack

  # Reusing _SimpleDecoder is slightly slower than copying a bunch of code, but
  # not enough to make a significant difference.

  # Note that we expect someone up-stack to catch struct.error and convert
  # it to _DecodeError -- this way we don't have to set up exception-
  # handling blocks every time we parse one value.

  def InnerDecode(buffer, pos):
    new_pos = pos + value_size
    result = local_unpack(format, buffer[pos:new_pos])[0]
    return (result, new_pos)
  return _SimpleDecoder(wire_type, InnerDecode)


def _FloatDecoder():
  """Returns a decoder for a float field.

  This code works around a bug in struct.unpack for non-finite 32-bit
  floating-point values.
  """

  local_unpack = struct.unpack

  def InnerDecode(buffer, pos):
    """Decode serialized float to a float and new position.

    Args:
      buffer: memoryview of the serialized bytes
      pos: int, position in the memory view to start at.

    Returns:
      Tuple[float, int] of the deserialized float value and new position
      in the serialized data.
    """
    # We expect a 32-bit value in little-endian byte order.  Bit 1 is the sign
    # bit, bits 2-9 represent the exponent, and bits 10-32 are the significand.
    new_pos = pos + 4
    float_bytes = buffer[pos:new_pos].tobytes()

    # If this value has all its exponent bits set, then it's non-finite.
    # In Python 2.4, struct.unpack will convert it to a finite 64-bit value.
    # To avoid that, we parse it specially.
    if (float_bytes[3:4] in b'\x7F\xFF' and float_bytes[2:3] >= b'\x80'):
      # If at least one significand bit is set...
      if float_bytes[0:3] != b'\x00\x00\x80':
        return (math.nan, new_pos)
      # If sign bit is set...
      if float_bytes[3:4] == b'\xFF':
        return (-math.inf, new_pos)
      return (math.inf, new_pos)

    # Note that we expect someone up-stack to catch struct.error and convert
    # it to _DecodeError -- this way we don't have to set up exception-
    # handling blocks every time we parse one value.
    result = local_unpack('<f', float_bytes)[0]
    return (result, new_pos)
  return _SimpleDecoder(wire_format.WIRETYPE_FIXED32, InnerDecode)


def _DoubleDecoder():
  """Returns a decoder for a double field.

  This code works around a bug in struct.unpack for not-a-number.
  """

  local_unpack = struct.unpack

  def InnerDecode(buffer, pos):
    """Decode serialized double to a double and new position.

    Args:
      buffer: memoryview of the serialized bytes.
      pos: int, position in the memory view to start at.

    Returns:
      Tuple[float, int] of the decoded double value and new position
      in the serialized data.
    """
    # We expect a 64-bit value in little-endian byte order.  Bit 1 is the sign
    # bit, bits 2-12 represent the exponent, and bits 13-64 are the significand.
    new_pos = pos + 8
    double_bytes = buffer[pos:new_pos].tobytes()

    # If this value has all its exponent bits set and at least one significand
    # bit set, it's not a number.  In Python 2.4, struct.unpack will treat it
    # as inf or -inf.  To avoid that, we treat it specially.
    if ((double_bytes[7:8] in b'\x7F\xFF')
        and (double_bytes[6:7] >= b'\xF0')
        and (double_bytes[0:7] != b'\x00\x00\x00\x00\x00\x00\xF0')):
      return (math.nan, new_pos)

    # Note that we expect someone up-stack to catch struct.error and convert
    # it to _DecodeError -- this way we don't have to set up exception-
    # handling blocks every time we parse one value.
    result = local_unpack('<d', double_bytes)[0]
    return (result, new_pos)
  return _SimpleDecoder(wire_format.WIRETYPE_FIXED64, InnerDecode)


def EnumDecoder(field_number, is_repeated, is_packed, key, new_default,
                clear_if_default=False):
  """Returns a decoder for enum field."""
  enum_type = key.enum_type
  if is_packed:
    local_DecodeVarint = _DecodeVarint
    def DecodePackedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      """Decode serialized packed enum to its value and a new position.

      Args:
        buffer: memoryview of the serialized bytes.
        pos: int, position in the memory view to start at.
        end: int, end position of serialized data
        message: Message object to store unknown fields in
        field_dict: Map[Descriptor, Any] to store decoded values in.

      Returns:
        int, new position in serialized data.
      """
      del current_depth # unused
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      (endpoint, pos) = local_DecodeVarint(buffer, pos)
      endpoint += pos
      if endpoint > end:
        raise _DecodeError('Truncated message.')
      while pos < endpoint:
        value_start_pos = pos
        (element, pos) = _DecodeSignedVarint32(buffer, pos)
        # pylint: disable=protected-access
        if element in enum_type.values_by_number:
          value.append(element)
        else:
          if not message._unknown_fields:
            message._unknown_fields = []
          tag_bytes = encoder.TagBytes(field_number,
                                       wire_format.WIRETYPE_VARINT)

          message._unknown_fields.append(
              (tag_bytes, buffer[value_start_pos:pos].tobytes()))
          if message._unknown_field_set is None:
            message._unknown_field_set = containers.UnknownFieldSet()
          message._unknown_field_set._add(
              field_number, wire_format.WIRETYPE_VARINT, element)
          # pylint: enable=protected-access
      if pos > endpoint:
        if element in enum_type.values_by_number:
          del value[-1]   # Discard corrupt value.
        else:
          del message._unknown_fields[-1]
          # pylint: disable=protected-access
          del message._unknown_field_set._values[-1]
          # pylint: enable=protected-access
        raise _DecodeError('Packed element was truncated.')
      return pos
    return DecodePackedField
  elif is_repeated:
    tag_bytes = encoder.TagBytes(field_number, wire_format.WIRETYPE_VARINT)
    tag_len = len(tag_bytes)
    def DecodeRepeatedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      """Decode serialized repeated enum to its value and a new position.

      Args:
        buffer: memoryview of the serialized bytes.
        pos: int, position in the memory view to start at.
        end: int, end position of serialized data
        message: Message object to store unknown fields in
        field_dict: Map[Descriptor, Any] to store decoded values in.

      Returns:
        int, new position in serialized data.
      """
      del current_depth # unused
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      while 1:
        (element, new_pos) = _DecodeSignedVarint32(buffer, pos)
        # pylint: disable=protected-access
        if element in enum_type.values_by_number:
          value.append(element)
        else:
          if not message._unknown_fields:
            message._unknown_fields = []
          message._unknown_fields.append(
              (tag_bytes, buffer[pos:new_pos].tobytes()))
          if message._unknown_field_set is None:
            message._unknown_field_set = containers.UnknownFieldSet()
          message._unknown_field_set._add(
              field_number, wire_format.WIRETYPE_VARINT, element)
        # pylint: enable=protected-access
        # Predict that the next tag is another copy of the same repeated
        # field.
        pos = new_pos + tag_len
        if buffer[new_pos:pos] != tag_bytes or new_pos >= end:
          # Prediction failed.  Return.
          if new_pos > end:
            raise _DecodeError('Truncated message.')
          return new_pos
    return DecodeRepeatedField
  else:
    def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
      """Decode serialized repeated enum to its value and a new position.

      Args:
        buffer: memoryview of the serialized bytes.
        pos: int, position in the memory view to start at.
        end: int, end position of serialized data
        message: Message object to store unknown fields in
        field_dict: Map[Descriptor, Any] to store decoded values in.

      Returns:
        int, new position in serialized data.
      """
      del current_depth # unused
      value_start_pos = pos
      (enum_value, pos) = _DecodeSignedVarint32(buffer, pos)
      if pos > end:
        raise _DecodeError('Truncated message.')
      if clear_if_default and not enum_value:
        field_dict.pop(key, None)
        return pos
      # pylint: disable=protected-access
      if enum_value in enum_type.values_by_number:
        field_dict[key] = enum_value
      else:
        if not message._unknown_fields:
          message._unknown_fields = []
        tag_bytes = encoder.TagBytes(field_number,
                                     wire_format.WIRETYPE_VARINT)
        message._unknown_fields.append(
            (tag_bytes, buffer[value_start_pos:pos].tobytes()))
        if message._unknown_field_set is None:
          message._unknown_field_set = containers.UnknownFieldSet()
        message._unknown_field_set._add(
            field_number, wire_format.WIRETYPE_VARINT, enum_value)
        # pylint: enable=protected-access
      return pos
    return DecodeField


# --------------------------------------------------------------------


Int32Decoder = _SimpleDecoder(
    wire_format.WIRETYPE_VARINT, _DecodeSignedVarint32)

Int64Decoder = _SimpleDecoder(
    wire_format.WIRETYPE_VARINT, _DecodeSignedVarint)

UInt32Decoder = _SimpleDecoder(wire_format.WIRETYPE_VARINT, _DecodeVarint32)
UInt64Decoder = _SimpleDecoder(wire_format.WIRETYPE_VARINT, _DecodeVarint)

SInt32Decoder = _ModifiedDecoder(
    wire_format.WIRETYPE_VARINT, _DecodeVarint32, wire_format.ZigZagDecode)
SInt64Decoder = _ModifiedDecoder(
    wire_format.WIRETYPE_VARINT, _DecodeVarint, wire_format.ZigZagDecode)

# Note that Python conveniently guarantees that when using the '<' prefix on
# formats, they will also have the same size across all platforms (as opposed
# to without the prefix, where their sizes depend on the C compiler's basic
# type sizes).
Fixed32Decoder  = _StructPackDecoder(wire_format.WIRETYPE_FIXED32, '<I')
Fixed64Decoder  = _StructPackDecoder(wire_format.WIRETYPE_FIXED64, '<Q')
SFixed32Decoder = _StructPackDecoder(wire_format.WIRETYPE_FIXED32, '<i')
SFixed64Decoder = _StructPackDecoder(wire_format.WIRETYPE_FIXED64, '<q')
FloatDecoder = _FloatDecoder()
DoubleDecoder = _DoubleDecoder()

BoolDecoder = _ModifiedDecoder(
    wire_format.WIRETYPE_VARINT, _DecodeVarint, bool)


def StringDecoder(field_number, is_repeated, is_packed, key, new_default,
                  clear_if_default=False):
  """Returns a decoder for a string field."""

  local_DecodeVarint = _DecodeVarint

  def _ConvertToUnicode(memview):
    """Convert byte to unicode."""
    byte_str = memview.tobytes()
    try:
      value = str(byte_str, 'utf-8')
    except UnicodeDecodeError as e:
      # add more information to the error message and re-raise it.
      e.reason = '%s in field: %s' % (e, key.full_name)
      raise

    return value

  assert not is_packed
  if is_repeated:
    tag_bytes = encoder.TagBytes(field_number,
                                 wire_format.WIRETYPE_LENGTH_DELIMITED)
    tag_len = len(tag_bytes)
    def DecodeRepeatedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      del current_depth # unused
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      while 1:
        (size, pos) = local_DecodeVarint(buffer, pos)
        new_pos = pos + size
        if new_pos > end:
          raise _DecodeError('Truncated string.')
        value.append(_ConvertToUnicode(buffer[pos:new_pos]))
        # Predict that the next tag is another copy of the same repeated field.
        pos = new_pos + tag_len
        if buffer[new_pos:pos] != tag_bytes or new_pos == end:
          # Prediction failed.  Return.
          return new_pos
    return DecodeRepeatedField
  else:
    def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
      del current_depth # unused
      (size, pos) = local_DecodeVarint(buffer, pos)
      new_pos = pos + size
      if new_pos > end:
        raise _DecodeError('Truncated string.')
      if clear_if_default and not size:
        field_dict.pop(key, None)
      else:
        field_dict[key] = _ConvertToUnicode(buffer[pos:new_pos])
      return new_pos
    return DecodeField


def BytesDecoder(field_number, is_repeated, is_packed, key, new_default,
                 clear_if_default=False):
  """Returns a decoder for a bytes field."""

  local_DecodeVarint = _DecodeVarint

  assert not is_packed
  if is_repeated:
    tag_bytes = encoder.TagBytes(field_number,
                                 wire_format.WIRETYPE_LENGTH_DELIMITED)
    tag_len = len(tag_bytes)
    def DecodeRepeatedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      del current_depth # unused
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      while 1:
        (size, pos) = local_DecodeVarint(buffer, pos)
        new_pos = pos + size
        if new_pos > end:
          raise _DecodeError('Truncated string.')
        value.append(buffer[pos:new_pos].tobytes())
        # Predict that the next tag is another copy of the same repeated field.
        pos = new_pos + tag_len
        if buffer[new_pos:pos] != tag_bytes or new_pos == end:
          # Prediction failed.  Return.
          return new_pos
    return DecodeRepeatedField
  else:
    def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
      del current_depth # unused
      (size, pos) = local_DecodeVarint(buffer, pos)
      new_pos = pos + size
      if new_pos > end:
        raise _DecodeError('Truncated string.')
      if clear_if_default and not size:
        field_dict.pop(key, None)
      else:
        field_dict[key] = buffer[pos:new_pos].tobytes()
      return new_pos
    return DecodeField


def GroupDecoder(field_number, is_repeated, is_packed, key, new_default):
  """Returns a decoder for a group field."""

  end_tag_bytes = encoder.TagBytes(field_number,
                                   wire_format.WIRETYPE_END_GROUP)
  end_tag_len = len(end_tag_bytes)

  assert not is_packed
  if is_repeated:
    tag_bytes = encoder.TagBytes(field_number,
                                 wire_format.WIRETYPE_START_GROUP)
    tag_len = len(tag_bytes)
    def DecodeRepeatedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      while 1:
        value = field_dict.get(key)
        if value is None:
          value = field_dict.setdefault(key, new_default(message))
        # Read sub-message.
        current_depth += 1
        if current_depth > _recursion_limit:
          raise _DecodeError(
              'Error parsing message: too many levels of nesting.'
          )
        pos = value.add()._InternalParse(buffer, pos, end, current_depth)
        current_depth -= 1
        # Read end tag.
        new_pos = pos+end_tag_len
        if buffer[pos:new_pos] != end_tag_bytes or new_pos > end:
          raise _DecodeError('Missing group end tag.')
        # Predict that the next tag is another copy of the same repeated field.
        pos = new_pos + tag_len
        if buffer[new_pos:pos] != tag_bytes or new_pos == end:
          # Prediction failed.  Return.
          return new_pos
    return DecodeRepeatedField
  else:
    def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      # Read sub-message.
      current_depth += 1
      if current_depth > _recursion_limit:
        raise _DecodeError('Error parsing message: too many levels of nesting.')
      pos = value._InternalParse(buffer, pos, end, current_depth)
      current_depth -= 1
      # Read end tag.
      new_pos = pos+end_tag_len
      if buffer[pos:new_pos] != end_tag_bytes or new_pos > end:
        raise _DecodeError('Missing group end tag.')
      return new_pos
    return DecodeField


def MessageDecoder(field_number, is_repeated, is_packed, key, new_default):
  """Returns a decoder for a message field."""

  local_DecodeVarint = _DecodeVarint

  assert not is_packed
  if is_repeated:
    tag_bytes = encoder.TagBytes(field_number,
                                 wire_format.WIRETYPE_LENGTH_DELIMITED)
    tag_len = len(tag_bytes)
    def DecodeRepeatedField(
        buffer, pos, end, message, field_dict, current_depth=0
    ):
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      while 1:
        # Read length.
        (size, pos) = local_DecodeVarint(buffer, pos)
        new_pos = pos + size
        if new_pos > end:
          raise _DecodeError('Truncated message.')
        # Read sub-message.
        current_depth += 1
        if current_depth > _recursion_limit:
          raise _DecodeError(
              'Error parsing message: too many levels of nesting.'
          )
        if (
            value.add()._InternalParse(buffer, pos, new_pos, current_depth)
            != new_pos
        ):
          # The only reason _InternalParse would return early is if it
          # encountered an end-group tag.
          raise _DecodeError('Unexpected end-group tag.')
        # Predict that the next tag is another copy of the same repeated field.
        current_depth -= 1
        pos = new_pos + tag_len
        if buffer[new_pos:pos] != tag_bytes or new_pos == end:
          # Prediction failed.  Return.
          return new_pos
    return DecodeRepeatedField
  else:
    def DecodeField(buffer, pos, end, message, field_dict, current_depth=0):
      value = field_dict.get(key)
      if value is None:
        value = field_dict.setdefault(key, new_default(message))
      # Read length.
      (size, pos) = local_DecodeVarint(buffer, pos)
      new_pos = pos + size
      if new_pos > end:
        raise _DecodeError('Truncated message.')
      current_depth += 1
      if current_depth > _recursion_limit:
        raise _DecodeError('Error parsing message: too many levels of nesting.')
      if value._InternalParse(buffer, pos, new_pos, current_depth) != new_pos:
        # The only reason _InternalParse would return early is if it encountered
        # an end-group tag.
        raise _DecodeError('Unexpected end-group tag.')
      current_depth -= 1
      return new_pos
    return DecodeField


# --------------------------------------------------------------------

MESSAGE_SET_ITEM_TAG = encoder.TagBytes(1, wire_format.WIRETYPE_START_GROUP)

def MessageSetItemDecoder(descriptor):
  """Returns a decoder for a MessageSet item.

  The parameter is the message Descriptor.

  The message set message looks like this:
    message MessageSet {
      repeated group Item = 1 {
        required int32 type_id = 2;
        required string message = 3;
      }
    }
  """

  type_id_tag_bytes = encoder.TagBytes(2, wire_format.WIRETYPE_VARINT)
  message_tag_bytes = encoder.TagBytes(3, wire_format.WIRETYPE_LENGTH_DELIMITED)
  item_end_tag_bytes = encoder.TagBytes(1, wire_format.WIRETYPE_END_GROUP)

  local_ReadTag = ReadTag
  local_DecodeVarint = _DecodeVarint
  local_SkipField = SkipField

  def DecodeItem(buffer, pos, end, message, field_dict):
    """Decode serialized message set to its value and new position.

    Args:
      buffer: memoryview of the serialized bytes.
      pos: int, position in the memory view to start at.
      end: int, end position of serialized data
      message: Message object to store unknown fields in
      field_dict: Map[Descriptor, Any] to store decoded values in.

    Returns:
      int, new position in serialized data.
    """
    message_set_item_start = pos
    type_id = -1
    message_start = -1
    message_end = -1

    # Technically, type_id and message can appear in any order, so we need
    # a little loop here.
    while 1:
      (tag_bytes, pos) = local_ReadTag(buffer, pos)
      if tag_bytes == type_id_tag_bytes:
        (type_id, pos) = local_DecodeVarint(buffer, pos)
      elif tag_bytes == message_tag_bytes:
        (size, message_start) = local_DecodeVarint(buffer, pos)
        pos = message_end = message_start + size
      elif tag_bytes == item_end_tag_bytes:
        break
      else:
        pos = SkipField(buffer, pos, end, tag_bytes)
        if pos == -1:
          raise _DecodeError('Missing group end tag.')

    if pos > end:
      raise _DecodeError('Truncated message.')

    if type_id == -1:
      raise _DecodeError('MessageSet item missing type_id.')
    if message_start == -1:
      raise _DecodeError('MessageSet item missing message.')

    extension = message.Extensions._FindExtensionByNumber(type_id)
    # pylint: disable=protected-access
    if extension is not None:
      value = field_dict.get(extension)
      if value is None:
        message_type = extension.message_type
        if not hasattr(message_type, '_concrete_class'):
          message_factory.GetMessageClass(message_type)
        value = field_dict.setdefault(
            extension, message_type._concrete_class())
      if value._InternalParse(buffer, message_start,message_end) != message_end:
        # The only reason _InternalParse would return early is if it encountered
        # an end-group tag.
        raise _DecodeError('Unexpected end-group tag.')
    else:
      if not message._unknown_fields:
        message._unknown_fields = []
      message._unknown_fields.append(
          (MESSAGE_SET_ITEM_TAG, buffer[message_set_item_start:pos].tobytes()))
      if message._unknown_field_set is None:
        message._unknown_field_set = containers.UnknownFieldSet()
      message._unknown_field_set._add(
          type_id,
          wire_format.WIRETYPE_LENGTH_DELIMITED,
          buffer[message_start:message_end].tobytes())
      # pylint: enable=protected-access

    return pos

  return DecodeItem


def UnknownMessageSetItemDecoder():
  """Returns a decoder for a Unknown MessageSet item."""

  type_id_tag_bytes = encoder.TagBytes(2, wire_format.WIRETYPE_VARINT)
  message_tag_bytes = encoder.TagBytes(3, wire_format.WIRETYPE_LENGTH_DELIMITED)
  item_end_tag_bytes = encoder.TagBytes(1, wire_format.WIRETYPE_END_GROUP)

  def DecodeUnknownItem(buffer):
    pos = 0
    end = len(buffer)
    message_start = -1
    message_end = -1
    while 1:
      (tag_bytes, pos) = ReadTag(buffer, pos)
      if tag_bytes == type_id_tag_bytes:
        (type_id, pos) = _DecodeVarint(buffer, pos)
      elif tag_bytes == message_tag_bytes:
        (size, message_start) = _DecodeVarint(buffer, pos)
        pos = message_end = message_start + size
      elif tag_bytes == item_end_tag_bytes:
        break
      else:
        pos = SkipField(buffer, pos, end, tag_bytes)
        if pos == -1:
          raise _DecodeError('Missing group end tag.')

    if pos > end:
      raise _DecodeError('Truncated message.')

    if type_id == -1:
      raise _DecodeError('MessageSet item missing type_id.')
    if message_start == -1:
      raise _DecodeError('MessageSet item missing message.')

    return (type_id, buffer[message_start:message_end].tobytes())

  return DecodeUnknownItem

# --------------------------------------------------------------------

def MapDecoder(field_descriptor, new_default, is_message_map):
  """Returns a decoder for a map field."""

  key = field_descriptor
  tag_bytes = encoder.TagBytes(field_descriptor.number,
                               wire_format.WIRETYPE_LENGTH_DELIMITED)
  tag_len = len(tag_bytes)
  local_DecodeVarint = _DecodeVarint
  # Can't read _concrete_class yet; might not be initialized.
  message_type = field_descriptor.message_type

  def DecodeMap(buffer, pos, end, message, field_dict, current_depth=0):
    del current_depth # unused
    submsg = message_type._concrete_class()
    value = field_dict.get(key)
    if value is None:
      value = field_dict.setdefault(key, new_default(message))
    while 1:
      # Read length.
      (size, pos) = local_DecodeVarint(buffer, pos)
      new_pos = pos + size
      if new_pos > end:
        raise _DecodeError('Truncated message.')
      # Read sub-message.
      submsg.Clear()
      if submsg._InternalParse(buffer, pos, new_pos) != new_pos:
        # The only reason _InternalParse would return early is if it
        # encountered an end-group tag.
        raise _DecodeError('Unexpected end-group tag.')

      if is_message_map:
        value[submsg.key].CopyFrom(submsg.value)
      else:
        value[submsg.key] = submsg.value

      # Predict that the next tag is another copy of the same repeated field.
      pos = new_pos + tag_len
      if buffer[new_pos:pos] != tag_bytes or new_pos == end:
        # Prediction failed.  Return.
        return new_pos

  return DecodeMap

# --------------------------------------------------------------------
# Optimization is not as heavy here because calls to SkipField() are rare,
# except for handling end-group tags.

def _SkipVarint(buffer, pos, end):
  """Skip a varint value.  Returns the new position."""
  # Previously ord(buffer[pos]) raised IndexError when pos is out of range.
  # With this code, ord(b'') raises TypeError.  Both are handled in
  # python_message.py to generate a 'Truncated message' error.
  while ord(buffer[pos:pos+1].tobytes()) & 0x80:
    pos += 1
  pos += 1
  if pos > end:
    raise _DecodeError('Truncated message.')
  return pos

def _SkipFixed64(buffer, pos, end):
  """Skip a fixed64 value.  Returns the new position."""

  pos += 8
  if pos > end:
    raise _DecodeError('Truncated message.')
  return pos


def _DecodeFixed64(buffer, pos):
  """Decode a fixed64."""
  new_pos = pos + 8
  return (struct.unpack('<Q', buffer[pos:new_pos])[0], new_pos)


def _SkipLengthDelimited(buffer, pos, end):
  """Skip a length-delimited value.  Returns the new position."""

  (size, pos) = _DecodeVarint(buffer, pos)
  pos += size
  if pos > end:
    raise _DecodeError('Truncated message.')
  return pos


def _SkipGroup(buffer, pos, end):
  """Skip sub-group.  Returns the new position."""

  while 1:
    (tag_bytes, pos) = ReadTag(buffer, pos)
    new_pos = SkipField(buffer, pos, end, tag_bytes)
    if new_pos == -1:
      return pos
    pos = new_pos

DEFAULT_RECURSION_LIMIT = 100
_recursion_limit = DEFAULT_RECURSION_LIMIT


def SetRecursionLimit(new_limit):
  global _recursion_limit
  _recursion_limit = new_limit


def _DecodeUnknownFieldSet(buffer, pos, end_pos=None, current_depth=0):
  """Decode UnknownFieldSet.  Returns the UnknownFieldSet and new position."""

  unknown_field_set = containers.UnknownFieldSet()
  while end_pos is None or pos < end_pos:
    (tag_bytes, pos) = ReadTag(buffer, pos)
    (tag, _) = _DecodeVarint(tag_bytes, 0)
    field_number, wire_type = wire_format.UnpackTag(tag)
    if wire_type == wire_format.WIRETYPE_END_GROUP:
      break
    (data, pos) = _DecodeUnknownField(buffer, pos, wire_type, current_depth)
    # pylint: disable=protected-access
    unknown_field_set._add(field_number, wire_type, data)

  return (unknown_field_set, pos)


def _DecodeUnknownField(buffer, pos, wire_type, current_depth=0):
  """Decode a unknown field.  Returns the UnknownField and new position."""

  if wire_type == wire_format.WIRETYPE_VARINT:
    (data, pos) = _DecodeVarint(buffer, pos)
  elif wire_type == wire_format.WIRETYPE_FIXED64:
    (data, pos) = _DecodeFixed64(buffer, pos)
  elif wire_type == wire_format.WIRETYPE_FIXED32:
    (data, pos) = _DecodeFixed32(buffer, pos)
  elif wire_type == wire_format.WIRETYPE_LENGTH_DELIMITED:
    (size, pos) = _DecodeVarint(buffer, pos)
    data = buffer[pos:pos+size].tobytes()
    pos += size
  elif wire_type == wire_format.WIRETYPE_START_GROUP:
    current_depth += 1
    if current_depth >= _recursion_limit:
      raise _DecodeError('Error parsing message: too many levels of nesting.')
    (data, pos) = _DecodeUnknownFieldSet(buffer, pos, None, current_depth)
    current_depth -= 1
  elif wire_type == wire_format.WIRETYPE_END_GROUP:
    return (0, -1)
  else:
    raise _DecodeError('Wrong wire type in tag.')

  return (data, pos)


def _EndGroup(buffer, pos, end):
  """Skipping an END_GROUP tag returns -1 to tell the parent loop to break."""

  return -1


def _SkipFixed32(buffer, pos, end):
  """Skip a fixed32 value.  Returns the new position."""

  pos += 4
  if pos > end:
    raise _DecodeError('Truncated message.')
  return pos


def _DecodeFixed32(buffer, pos):
  """Decode a fixed32."""

  new_pos = pos + 4
  return (struct.unpack('<I', buffer[pos:new_pos])[0], new_pos)


def _RaiseInvalidWireType(buffer, pos, end):
  """Skip function for unknown wire types.  Raises an exception."""

  raise _DecodeError('Tag had invalid wire type.')

def _FieldSkipper():
  """Constructs the SkipField function."""

  WIRETYPE_TO_SKIPPER = [
      _SkipVarint,
      _SkipFixed64,
      _SkipLengthDelimited,
      _SkipGroup,
      _EndGroup,
      _SkipFixed32,
      _RaiseInvalidWireType,
      _RaiseInvalidWireType,
      ]

  wiretype_mask = wire_format.TAG_TYPE_MASK

  def SkipField(buffer, pos, end, tag_bytes):
    """Skips a field with the specified tag.

    |pos| should point to the byte immediately after the tag.

    Returns:
        The new position (after the tag value), or -1 if the tag is an end-group
        tag (in which case the calling loop should break).
    """

    # The wire type is always in the first byte since varints are little-endian.
    wire_type = ord(tag_bytes[0:1]) & wiretype_mask
    return WIRETYPE_TO_SKIPPER[wire_type](buffer, pos, end)

  return SkipField

SkipField = _FieldSkipper()

# === NexusCore/openenv\Lib\site-packages\aiohttp\payload.py ===
import asyncio
import enum
import io
import json
import mimetypes
import os
import sys
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import chain
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    Type,
    Union,
)

from multidict import CIMultiDict

from . import hdrs
from .abc import AbstractStreamWriter
from .helpers import (
    _SENTINEL,
    content_disposition_header,
    guess_filename,
    parse_mimetype,
    sentinel,
)
from .streams import StreamReader
from .typedefs import JSONEncoder, _CIMultiDict

__all__ = (
    "PAYLOAD_REGISTRY",
    "get_payload",
    "payload_type",
    "Payload",
    "BytesPayload",
    "StringPayload",
    "IOBasePayload",
    "BytesIOPayload",
    "BufferedReaderPayload",
    "TextIOPayload",
    "StringIOPayload",
    "JsonPayload",
    "AsyncIterablePayload",
)

TOO_LARGE_BYTES_BODY: Final[int] = 2**20  # 1 MB
READ_SIZE: Final[int] = 2**16  # 64 KB
_CLOSE_FUTURES: Set[asyncio.Future[None]] = set()


class LookupError(Exception):
    """Raised when no payload factory is found for the given data type."""


class Order(str, enum.Enum):
    normal = "normal"
    try_first = "try_first"
    try_last = "try_last"


def get_payload(data: Any, *args: Any, **kwargs: Any) -> "Payload":
    return PAYLOAD_REGISTRY.get(data, *args, **kwargs)


def register_payload(
    factory: Type["Payload"], type: Any, *, order: Order = Order.normal
) -> None:
    PAYLOAD_REGISTRY.register(factory, type, order=order)


class payload_type:
    def __init__(self, type: Any, *, order: Order = Order.normal) -> None:
        self.type = type
        self.order = order

    def __call__(self, factory: Type["Payload"]) -> Type["Payload"]:
        register_payload(factory, self.type, order=self.order)
        return factory


PayloadType = Type["Payload"]
_PayloadRegistryItem = Tuple[PayloadType, Any]


class PayloadRegistry:
    """Payload registry.

    note: we need zope.interface for more efficient adapter search
    """

    __slots__ = ("_first", "_normal", "_last", "_normal_lookup")

    def __init__(self) -> None:
        self._first: List[_PayloadRegistryItem] = []
        self._normal: List[_PayloadRegistryItem] = []
        self._last: List[_PayloadRegistryItem] = []
        self._normal_lookup: Dict[Any, PayloadType] = {}

    def get(
        self,
        data: Any,
        *args: Any,
        _CHAIN: "Type[chain[_PayloadRegistryItem]]" = chain,
        **kwargs: Any,
    ) -> "Payload":
        if self._first:
            for factory, type_ in self._first:
                if isinstance(data, type_):
                    return factory(data, *args, **kwargs)
        # Try the fast lookup first
        if lookup_factory := self._normal_lookup.get(type(data)):
            return lookup_factory(data, *args, **kwargs)
        # Bail early if its already a Payload
        if isinstance(data, Payload):
            return data
        # Fallback to the slower linear search
        for factory, type_ in _CHAIN(self._normal, self._last):
            if isinstance(data, type_):
                return factory(data, *args, **kwargs)
        raise LookupError()

    def register(
        self, factory: PayloadType, type: Any, *, order: Order = Order.normal
    ) -> None:
        if order is Order.try_first:
            self._first.append((factory, type))
        elif order is Order.normal:
            self._normal.append((factory, type))
            if isinstance(type, Iterable):
                for t in type:
                    self._normal_lookup[t] = factory
            else:
                self._normal_lookup[type] = factory
        elif order is Order.try_last:
            self._last.append((factory, type))
        else:
            raise ValueError(f"Unsupported order {order!r}")


class Payload(ABC):

    _default_content_type: str = "application/octet-stream"
    _size: Optional[int] = None
    _consumed: bool = False  # Default: payload has not been consumed yet
    _autoclose: bool = False  # Default: assume resource needs explicit closing

    def __init__(
        self,
        value: Any,
        headers: Optional[
            Union[_CIMultiDict, Dict[str, str], Iterable[Tuple[str, str]]]
        ] = None,
        content_type: Union[str, None, _SENTINEL] = sentinel,
        filename: Optional[str] = None,
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._encoding = encoding
        self._filename = filename
        self._headers: _CIMultiDict = CIMultiDict()
        self._value = value
        if content_type is not sentinel and content_type is not None:
            self._headers[hdrs.CONTENT_TYPE] = content_type
        elif self._filename is not None:
            if sys.version_info >= (3, 13):
                guesser = mimetypes.guess_file_type
            else:
                guesser = mimetypes.guess_type
            content_type = guesser(self._filename)[0]
            if content_type is None:
                content_type = self._default_content_type
            self._headers[hdrs.CONTENT_TYPE] = content_type
        else:
            self._headers[hdrs.CONTENT_TYPE] = self._default_content_type
        if headers:
            self._headers.update(headers)

    @property
    def size(self) -> Optional[int]:
        """Size of the payload in bytes.

        Returns the number of bytes that will be transmitted when the payload
        is written. For string payloads, this is the size after encoding to bytes,
        not the length of the string.
        """
        return self._size

    @property
    def filename(self) -> Optional[str]:
        """Filename of the payload."""
        return self._filename

    @property
    def headers(self) -> _CIMultiDict:
        """Custom item headers"""
        return self._headers

    @property
    def _binary_headers(self) -> bytes:
        return (
            "".join([k + ": " + v + "\r\n" for k, v in self.headers.items()]).encode(
                "utf-8"
            )
            + b"\r\n"
        )

    @property
    def encoding(self) -> Optional[str]:
        """Payload encoding"""
        return self._encoding

    @property
    def content_type(self) -> str:
        """Content type"""
        return self._headers[hdrs.CONTENT_TYPE]

    @property
    def consumed(self) -> bool:
        """Whether the payload has been consumed and cannot be reused."""
        return self._consumed

    @property
    def autoclose(self) -> bool:
        """
        Whether the payload can close itself automatically.

        Returns True if the payload has no file handles or resources that need
        explicit closing. If False, callers must await close() to release resources.
        """
        return self._autoclose

    def set_content_disposition(
        self,
        disptype: str,
        quote_fields: bool = True,
        _charset: str = "utf-8",
        **params: Any,
    ) -> None:
        """Sets ``Content-Disposition`` header."""
        self._headers[hdrs.CONTENT_DISPOSITION] = content_disposition_header(
            disptype, quote_fields=quote_fields, _charset=_charset, **params
        )

    @abstractmethod
    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        This is named decode() to allow compatibility with bytes objects.
        """

    @abstractmethod
    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This is a legacy method that writes the entire payload without length constraints.

        Important:
            For new implementations, use write_with_length() instead of this method.
            This method is maintained for backwards compatibility and will eventually
            delegate to write_with_length(writer, None) in all implementations.

        All payload subclasses must override this method for backwards compatibility,
        but new code should use write_with_length for more flexibility and control.

        """

    # write_with_length is new in aiohttp 3.12
    # it should be overridden by subclasses
    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method allows writing payload content with a specific length constraint,
        which is particularly useful for HTTP responses with Content-Length header.

        Note:
            This is the base implementation that provides backwards compatibility
            for subclasses that don't override this method. Specific payload types
            should override this method to implement proper length-constrained writing.

        """
        # Backwards compatibility for subclasses that don't override this method
        # and for the default implementation
        await self.write(writer)

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This is a convenience method that calls decode() and encodes the result
        to bytes using the specified encoding.
        """
        # Use instance encoding if available, otherwise use parameter
        actual_encoding = self._encoding or encoding
        return self.decode(actual_encoding, errors).encode(actual_encoding)

    def _close(self) -> None:
        """
        Async safe synchronous close operations for backwards compatibility.

        This method exists only for backwards compatibility with code that
        needs to clean up payloads synchronously. In the future, we will
        drop this method and only support the async close() method.

        WARNING: This method must be safe to call from within the event loop
        without blocking. Subclasses should not perform any blocking I/O here.

        WARNING: This method must be called from within an event loop for
        certain payload types (e.g., IOBasePayload). Calling it outside an
        event loop may raise RuntimeError.
        """
        # This is a no-op by default, but subclasses can override it
        # for non-blocking cleanup operations.

    async def close(self) -> None:
        """
        Close the payload if it holds any resources.

        IMPORTANT: This method must not await anything that might not finish
        immediately, as it may be called during cleanup/cancellation. Schedule
        any long-running operations without awaiting them.

        In the future, this will be the only close method supported.
        """
        self._close()


class BytesPayload(Payload):
    _value: bytes
    # _consumed = False (inherited) - Bytes are immutable and can be reused
    _autoclose = True  # No file handle, just bytes in memory

    def __init__(
        self, value: Union[bytes, bytearray, memoryview], *args: Any, **kwargs: Any
    ) -> None:
        if "content_type" not in kwargs:
            kwargs["content_type"] = "application/octet-stream"

        super().__init__(value, *args, **kwargs)

        if isinstance(value, memoryview):
            self._size = value.nbytes
        elif isinstance(value, (bytes, bytearray)):
            self._size = len(value)
        else:
            raise TypeError(f"value argument must be byte-ish, not {type(value)!r}")

        if self._size > TOO_LARGE_BYTES_BODY:
            kwargs = {"source": self}
            warnings.warn(
                "Sending a large body directly with raw bytes might"
                " lock the event loop. You should probably pass an "
                "io.BytesIO object instead",
                ResourceWarning,
                **kwargs,
            )

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self._value.decode(encoding, errors)

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method returns the raw bytes content of the payload.
        It is equivalent to accessing the _value attribute directly.
        """
        return self._value

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire bytes payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method writes the entire bytes content without any length constraint.

        Note:
            For new implementations that need length control, use write_with_length().
            This method is maintained for backwards compatibility and is equivalent
            to write_with_length(writer, None).

        """
        await writer.write(self._value)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write bytes payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method writes either the entire byte sequence or a slice of it
        up to the specified content_length. For BytesPayload, this operation
        is performed efficiently using array slicing.

        """
        if content_length is not None:
            await writer.write(self._value[:content_length])
        else:
            await writer.write(self._value)


class StringPayload(BytesPayload):
    def __init__(
        self,
        value: str,
        *args: Any,
        encoding: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:

        if encoding is None:
            if content_type is None:
                real_encoding = "utf-8"
                content_type = "text/plain; charset=utf-8"
            else:
                mimetype = parse_mimetype(content_type)
                real_encoding = mimetype.parameters.get("charset", "utf-8")
        else:
            if content_type is None:
                content_type = "text/plain; charset=%s" % encoding
            real_encoding = encoding

        super().__init__(
            value.encode(real_encoding),
            encoding=real_encoding,
            content_type=content_type,
            *args,
            **kwargs,
        )


class StringIOPayload(StringPayload):
    def __init__(self, value: IO[str], *args: Any, **kwargs: Any) -> None:
        super().__init__(value.read(), *args, **kwargs)


class IOBasePayload(Payload):
    _value: io.IOBase
    # _consumed = False (inherited) - File can be re-read from the same position
    _start_position: Optional[int] = None
    # _autoclose = False (inherited) - Has file handle that needs explicit closing

    def __init__(
        self, value: IO[Any], disposition: str = "attachment", *args: Any, **kwargs: Any
    ) -> None:
        if "filename" not in kwargs:
            kwargs["filename"] = guess_filename(value)

        super().__init__(value, *args, **kwargs)

        if self._filename is not None and disposition is not None:
            if hdrs.CONTENT_DISPOSITION not in self.headers:
                self.set_content_disposition(disposition, filename=self._filename)

    def _set_or_restore_start_position(self) -> None:
        """Set or restore the start position of the file-like object."""
        if self._start_position is None:
            try:
                self._start_position = self._value.tell()
            except OSError:
                self._consumed = True  # Cannot seek, mark as consumed
            return
        self._value.seek(self._start_position)

    def _read_and_available_len(
        self, remaining_content_len: Optional[int]
    ) -> Tuple[Optional[int], bytes]:
        """
        Read the file-like object and return both its total size and the first chunk.

        Args:
            remaining_content_len: Optional limit on how many bytes to read in this operation.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A tuple containing:
            - The total size of the remaining unread content (None if size cannot be determined)
            - The first chunk of bytes read from the file object

        This method is optimized to perform both size calculation and initial read
        in a single operation, which is executed in a single executor job to minimize
        context switches and file operations when streaming content.

        """
        self._set_or_restore_start_position()
        size = self.size  # Call size only once since it does I/O
        return size, self._value.read(
            min(READ_SIZE, size or READ_SIZE, remaining_content_len or READ_SIZE)
        )

    def _read(self, remaining_content_len: Optional[int]) -> bytes:
        """
        Read a chunk of data from the file-like object.

        Args:
            remaining_content_len: Optional maximum number of bytes to read.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A chunk of bytes read from the file object, respecting the
            remaining_content_len limit if specified.

        This method is used for subsequent reads during streaming after
        the initial _read_and_available_len call has been made.

        """
        return self._value.read(remaining_content_len or READ_SIZE)  # type: ignore[no-any-return]

    @property
    def size(self) -> Optional[int]:
        """
        Size of the payload in bytes.

        Returns the number of bytes remaining to be read from the file.
        Returns None if the size cannot be determined (e.g., for unseekable streams).
        """
        try:
            return os.fstat(self._value.fileno()).st_size - self._value.tell()
        except (AttributeError, OSError):
            return None

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire file-like payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method writes the entire file content without any length constraint.
        It delegates to write_with_length() with no length limit for implementation
        consistency.

        Note:
            For new implementations that need length control, use write_with_length() directly.
            This method is maintained for backwards compatibility with existing code.

        """
        await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write file-like payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method implements optimized streaming of file content with length constraints:

        1. File reading is performed in a thread pool to avoid blocking the event loop
        2. Content is read and written in chunks to maintain memory efficiency
        3. Writing stops when either:
           - All available file content has been written (when size is known)
           - The specified content_length has been reached
        4. File resources are properly closed even if the operation is cancelled

        The implementation carefully handles both known-size and unknown-size payloads,
        as well as constrained and unconstrained content lengths.

        """
        loop = asyncio.get_running_loop()
        total_written_len = 0
        remaining_content_len = content_length

        # Get initial data and available length
        available_len, chunk = await loop.run_in_executor(
            None, self._read_and_available_len, remaining_content_len
        )
        # Process data chunks until done
        while chunk:
            chunk_len = len(chunk)

            # Write data with or without length constraint
            if remaining_content_len is None:
                await writer.write(chunk)
            else:
                await writer.write(chunk[:remaining_content_len])
                remaining_content_len -= chunk_len

            total_written_len += chunk_len

            # Check if we're done writing
            if self._should_stop_writing(
                available_len, total_written_len, remaining_content_len
            ):
                return

            # Read next chunk
            chunk = await loop.run_in_executor(
                None,
                self._read,
                (
                    min(READ_SIZE, remaining_content_len)
                    if remaining_content_len is not None
                    else READ_SIZE
                ),
            )

    def _should_stop_writing(
        self,
        available_len: Optional[int],
        total_written_len: int,
        remaining_content_len: Optional[int],
    ) -> bool:
        """
        Determine if we should stop writing data.

        Args:
            available_len: Known size of the payload if available (None if unknown)
            total_written_len: Number of bytes already written
            remaining_content_len: Remaining bytes to be written for content-length limited responses

        Returns:
            True if we should stop writing data, based on either:
            - Having written all available data (when size is known)
            - Having written all requested content (when content-length is specified)

        """
        return (available_len is not None and total_written_len >= available_len) or (
            remaining_content_len is not None and remaining_content_len <= 0
        )

    def _close(self) -> None:
        """
        Async safe synchronous close operations for backwards compatibility.

        This method exists only for backwards
        compatibility. Use the async close() method instead.

        WARNING: This method MUST be called from within an event loop.
        Calling it outside an event loop will raise RuntimeError.
        """
        # Skip if already consumed
        if self._consumed:
            return
        self._consumed = True  # Mark as consumed to prevent further writes
        # Schedule file closing without awaiting to prevent cancellation issues
        loop = asyncio.get_running_loop()
        close_future = loop.run_in_executor(None, self._value.close)
        # Hold a strong reference to the future to prevent it from being
        # garbage collected before it completes.
        _CLOSE_FUTURES.add(close_future)
        close_future.add_done_callback(_CLOSE_FUTURES.remove)

    async def close(self) -> None:
        """
        Close the payload if it holds any resources.

        IMPORTANT: This method must not await anything that might not finish
        immediately, as it may be called during cleanup/cancellation. Schedule
        any long-running operations without awaiting them.
        """
        self._close()

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        WARNING: This method does blocking I/O and should not be called in the event loop.
        """
        return self._read_all().decode(encoding, errors)

    def _read_all(self) -> bytes:
        """Read the entire file-like object and return its content as bytes."""
        self._set_or_restore_start_position()
        # Use readlines() to ensure we get all content
        return b"".join(self._value.readlines())

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire file content and returns it as bytes.
        It is equivalent to reading the file-like object directly.
        The file reading is performed in an executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_all)


class TextIOPayload(IOBasePayload):
    _value: io.TextIOBase
    # _autoclose = False (inherited) - Has text file handle that needs explicit closing

    def __init__(
        self,
        value: TextIO,
        *args: Any,
        encoding: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:

        if encoding is None:
            if content_type is None:
                encoding = "utf-8"
                content_type = "text/plain; charset=utf-8"
            else:
                mimetype = parse_mimetype(content_type)
                encoding = mimetype.parameters.get("charset", "utf-8")
        else:
            if content_type is None:
                content_type = "text/plain; charset=%s" % encoding

        super().__init__(
            value,
            content_type=content_type,
            encoding=encoding,
            *args,
            **kwargs,
        )

    def _read_and_available_len(
        self, remaining_content_len: Optional[int]
    ) -> Tuple[Optional[int], bytes]:
        """
        Read the text file-like object and return both its total size and the first chunk.

        Args:
            remaining_content_len: Optional limit on how many bytes to read in this operation.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A tuple containing:
            - The total size of the remaining unread content (None if size cannot be determined)
            - The first chunk of bytes read from the file object, encoded using the payload's encoding

        This method is optimized to perform both size calculation and initial read
        in a single operation, which is executed in a single executor job to minimize
        context switches and file operations when streaming content.

        Note:
            TextIOPayload handles encoding of the text content before writing it
            to the stream. If no encoding is specified, UTF-8 is used as the default.

        """
        self._set_or_restore_start_position()
        size = self.size
        chunk = self._value.read(
            min(READ_SIZE, size or READ_SIZE, remaining_content_len or READ_SIZE)
        )
        return size, chunk.encode(self._encoding) if self._encoding else chunk.encode()

    def _read(self, remaining_content_len: Optional[int]) -> bytes:
        """
        Read a chunk of data from the text file-like object.

        Args:
            remaining_content_len: Optional maximum number of bytes to read.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A chunk of bytes read from the file object and encoded using the payload's
            encoding. The data is automatically converted from text to bytes.

        This method is used for subsequent reads during streaming after
        the initial _read_and_available_len call has been made. It properly
        handles text encoding, converting the text content to bytes using
        the specified encoding (or UTF-8 if none was provided).

        """
        chunk = self._value.read(remaining_content_len or READ_SIZE)
        return chunk.encode(self._encoding) if self._encoding else chunk.encode()

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        WARNING: This method does blocking I/O and should not be called in the event loop.
        """
        self._set_or_restore_start_position()
        return self._value.read()

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire text file content and returns it as bytes.
        It encodes the text content using the specified encoding.
        The file reading is performed in an executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()

        # Use instance encoding if available, otherwise use parameter
        actual_encoding = self._encoding or encoding

        def _read_and_encode() -> bytes:
            self._set_or_restore_start_position()
            # TextIO read() always returns the full content
            return self._value.read().encode(actual_encoding, errors)

        return await loop.run_in_executor(None, _read_and_encode)


class BytesIOPayload(IOBasePayload):
    _value: io.BytesIO
    _size: int  # Always initialized in __init__
    _autoclose = True  # BytesIO is in-memory, safe to auto-close

    def __init__(self, value: io.BytesIO, *args: Any, **kwargs: Any) -> None:
        super().__init__(value, *args, **kwargs)
        # Calculate size once during initialization
        self._size = len(self._value.getbuffer()) - self._value.tell()

    @property
    def size(self) -> int:
        """Size of the payload in bytes.

        Returns the number of bytes in the BytesIO buffer that will be transmitted.
        This is calculated once during initialization for efficiency.
        """
        return self._size

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        self._set_or_restore_start_position()
        return self._value.read().decode(encoding, errors)

    async def write(self, writer: AbstractStreamWriter) -> None:
        return await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write BytesIO payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This implementation is specifically optimized for BytesIO objects:

        1. Reads content in chunks to maintain memory efficiency
        2. Yields control back to the event loop periodically to prevent blocking
           when dealing with large BytesIO objects
        3. Respects content_length constraints when specified
        4. Properly cleans up by closing the BytesIO object when done or on error

        The periodic yielding to the event loop is important for maintaining
        responsiveness when processing large in-memory buffers.

        """
        self._set_or_restore_start_position()
        loop_count = 0
        remaining_bytes = content_length
        while chunk := self._value.read(READ_SIZE):
            if loop_count > 0:
                # Avoid blocking the event loop
                # if they pass a large BytesIO object
                # and we are not in the first iteration
                # of the loop
                await asyncio.sleep(0)
            if remaining_bytes is None:
                await writer.write(chunk)
            else:
                await writer.write(chunk[:remaining_bytes])
                remaining_bytes -= len(chunk)
                if remaining_bytes <= 0:
                    return
            loop_count += 1

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire BytesIO content and returns it as bytes.
        It is equivalent to accessing the _value attribute directly.
        """
        self._set_or_restore_start_position()
        return self._value.read()

    async def close(self) -> None:
        """
        Close the BytesIO payload.

        This does nothing since BytesIO is in-memory and does not require explicit closing.
        """


class BufferedReaderPayload(IOBasePayload):
    _value: io.BufferedIOBase
    # _autoclose = False (inherited) - Has buffered file handle that needs explicit closing

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        self._set_or_restore_start_position()
        return self._value.read().decode(encoding, errors)


class JsonPayload(BytesPayload):
    def __init__(
        self,
        value: Any,
        encoding: str = "utf-8",
        content_type: str = "application/json",
        dumps: JSONEncoder = json.dumps,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            dumps(value).encode(encoding),
            content_type=content_type,
            encoding=encoding,
            *args,
            **kwargs,
        )


if TYPE_CHECKING:
    from typing import AsyncIterable, AsyncIterator

    _AsyncIterator = AsyncIterator[bytes]
    _AsyncIterable = AsyncIterable[bytes]
else:
    from collections.abc import AsyncIterable, AsyncIterator

    _AsyncIterator = AsyncIterator
    _AsyncIterable = AsyncIterable


class AsyncIterablePayload(Payload):

    _iter: Optional[_AsyncIterator] = None
    _value: _AsyncIterable
    _cached_chunks: Optional[List[bytes]] = None
    # _consumed stays False to allow reuse with cached content
    _autoclose = True  # Iterator doesn't need explicit closing

    def __init__(self, value: _AsyncIterable, *args: Any, **kwargs: Any) -> None:
        if not isinstance(value, AsyncIterable):
            raise TypeError(
                "value argument must support "
                "collections.abc.AsyncIterable interface, "
                "got {!r}".format(type(value))
            )

        if "content_type" not in kwargs:
            kwargs["content_type"] = "application/octet-stream"

        super().__init__(value, *args, **kwargs)

        self._iter = value.__aiter__()

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire async iterable payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method iterates through the async iterable and writes each chunk
        to the writer without any length constraint.

        Note:
            For new implementations that need length control, use write_with_length() directly.
            This method is maintained for backwards compatibility with existing code.

        """
        await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write async iterable payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This implementation handles streaming of async iterable content with length constraints:

        1. If cached chunks are available, writes from them
        2. Otherwise iterates through the async iterable one chunk at a time
        3. Respects content_length constraints when specified
        4. Does NOT generate cache - that's done by as_bytes()

        """
        # If we have cached chunks, use them
        if self._cached_chunks is not None:
            remaining_bytes = content_length
            for chunk in self._cached_chunks:
                if remaining_bytes is None:
                    await writer.write(chunk)
                elif remaining_bytes > 0:
                    await writer.write(chunk[:remaining_bytes])
                    remaining_bytes -= len(chunk)
                else:
                    break
            return

        # If iterator is exhausted and we don't have cached chunks, nothing to write
        if self._iter is None:
            return

        # Stream from the iterator
        remaining_bytes = content_length

        try:
            while True:
                if sys.version_info >= (3, 10):
                    chunk = await anext(self._iter)
                else:
                    chunk = await self._iter.__anext__()
                if remaining_bytes is None:
                    await writer.write(chunk)
                # If we have a content length limit
                elif remaining_bytes > 0:
                    await writer.write(chunk[:remaining_bytes])
                    remaining_bytes -= len(chunk)
                # We still want to exhaust the iterator even
                # if we have reached the content length limit
                # since the file handle may not get closed by
                # the iterator if we don't do this
        except StopAsyncIteration:
            # Iterator is exhausted
            self._iter = None
            self._consumed = True  # Mark as consumed when streamed without caching

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """Decode the payload content as a string if cached chunks are available."""
        if self._cached_chunks is not None:
            return b"".join(self._cached_chunks).decode(encoding, errors)
        raise TypeError("Unable to decode - content not cached. Call as_bytes() first.")

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire async iterable content and returns it as bytes.
        It generates and caches the chunks for future reuse.
        """
        # If we have cached chunks, return them joined
        if self._cached_chunks is not None:
            return b"".join(self._cached_chunks)

        # If iterator is exhausted and no cache, return empty
        if self._iter is None:
            return b""

        # Read all chunks and cache them
        chunks: List[bytes] = []
        async for chunk in self._iter:
            chunks.append(chunk)

        # Iterator is exhausted, cache the chunks
        self._iter = None
        self._cached_chunks = chunks
        # Keep _consumed as False to allow reuse with cached chunks

        return b"".join(chunks)


class StreamReaderPayload(AsyncIterablePayload):
    def __init__(self, value: StreamReader, *args: Any, **kwargs: Any) -> None:
        super().__init__(value.iter_any(), *args, **kwargs)


PAYLOAD_REGISTRY = PayloadRegistry()
PAYLOAD_REGISTRY.register(BytesPayload, (bytes, bytearray, memoryview))
PAYLOAD_REGISTRY.register(StringPayload, str)
PAYLOAD_REGISTRY.register(StringIOPayload, io.StringIO)
PAYLOAD_REGISTRY.register(TextIOPayload, io.TextIOBase)
PAYLOAD_REGISTRY.register(BytesIOPayload, io.BytesIO)
PAYLOAD_REGISTRY.register(BufferedReaderPayload, (io.BufferedReader, io.BufferedRandom))
PAYLOAD_REGISTRY.register(IOBasePayload, io.IOBase)
PAYLOAD_REGISTRY.register(StreamReaderPayload, StreamReader)
# try_last for giving a chance to more specialized async interables like
# multipart.BodyPartReaderPayload override the default
PAYLOAD_REGISTRY.register(AsyncIterablePayload, AsyncIterable, order=Order.try_last)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\wheel.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import base64
import codecs
import datetime
from email import message_from_file
import hashlib
import json
import logging
import os
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile

from . import __version__, DistlibException
from .compat import sysconfig, ZipFile, fsdecode, text_type, filter
from .database import InstalledDistribution
from .metadata import Metadata, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME
from .util import (FileOperator, convert_path, CSVReader, CSVWriter, Cache, cached_property, get_cache_base,
                   read_exports, tempdir, get_platform)
from .version import NormalizedVersion, UnsupportedVersionError

logger = logging.getLogger(__name__)

cache = None  # created when needed

if hasattr(sys, 'pypy_version_info'):  # pragma: no cover
    IMP_PREFIX = 'pp'
elif sys.platform.startswith('java'):  # pragma: no cover
    IMP_PREFIX = 'jy'
elif sys.platform == 'cli':  # pragma: no cover
    IMP_PREFIX = 'ip'
else:
    IMP_PREFIX = 'cp'

VER_SUFFIX = sysconfig.get_config_var('py_version_nodot')
if not VER_SUFFIX:  # pragma: no cover
    VER_SUFFIX = '%s%s' % sys.version_info[:2]
PYVER = 'py' + VER_SUFFIX
IMPVER = IMP_PREFIX + VER_SUFFIX

ARCH = get_platform().replace('-', '_').replace('.', '_')

ABI = sysconfig.get_config_var('SOABI')
if ABI and ABI.startswith('cpython-'):
    ABI = ABI.replace('cpython-', 'cp').split('-')[0]
else:

    def _derive_abi():
        parts = ['cp', VER_SUFFIX]
        if sysconfig.get_config_var('Py_DEBUG'):
            parts.append('d')
        if IMP_PREFIX == 'cp':
            vi = sys.version_info[:2]
            if vi < (3, 8):
                wpm = sysconfig.get_config_var('WITH_PYMALLOC')
                if wpm is None:
                    wpm = True
                if wpm:
                    parts.append('m')
                if vi < (3, 3):
                    us = sysconfig.get_config_var('Py_UNICODE_SIZE')
                    if us == 4 or (us is None and sys.maxunicode == 0x10FFFF):
                        parts.append('u')
        return ''.join(parts)

    ABI = _derive_abi()
    del _derive_abi

FILENAME_RE = re.compile(
    r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?
-(?P<py>\w+\d+(\.\w+\d+)*)
-(?P<bi>\w+)
-(?P<ar>\w+(\.\w+)*)
\.whl$
''', re.IGNORECASE | re.VERBOSE)

NAME_VERSION_RE = re.compile(r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?$
''', re.IGNORECASE | re.VERBOSE)

SHEBANG_RE = re.compile(br'\s*#![^\r\n]*')
SHEBANG_DETAIL_RE = re.compile(br'^(\s*#!("[^"]+"|\S+))\s+(.*)$')
SHEBANG_PYTHON = b'#!python'
SHEBANG_PYTHONW = b'#!pythonw'

if os.sep == '/':
    to_posix = lambda o: o
else:
    to_posix = lambda o: o.replace(os.sep, '/')

if sys.version_info[0] < 3:
    import imp
else:
    imp = None
    import importlib.machinery
    import importlib.util


def _get_suffixes():
    if imp:
        return [s[0] for s in imp.get_suffixes()]
    else:
        return importlib.machinery.EXTENSION_SUFFIXES


def _load_dynamic(name, path):
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    if imp:
        return imp.load_dynamic(name, path)
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


class Mounter(object):

    def __init__(self):
        self.impure_wheels = {}
        self.libs = {}

    def add(self, pathname, extensions):
        self.impure_wheels[pathname] = extensions
        self.libs.update(extensions)

    def remove(self, pathname):
        extensions = self.impure_wheels.pop(pathname)
        for k, v in extensions:
            if k in self.libs:
                del self.libs[k]

    def find_module(self, fullname, path=None):
        if fullname in self.libs:
            result = self
        else:
            result = None
        return result

    def load_module(self, fullname):
        if fullname in sys.modules:
            result = sys.modules[fullname]
        else:
            if fullname not in self.libs:
                raise ImportError('unable to find extension for %s' % fullname)
            result = _load_dynamic(fullname, self.libs[fullname])
            result.__loader__ = self
            parts = fullname.rsplit('.', 1)
            if len(parts) > 1:
                result.__package__ = parts[0]
        return result


_hook = Mounter()


class Wheel(object):
    """
    Class to build and install from Wheel files (PEP 427).
    """

    wheel_version = (1, 1)
    hash_kind = 'sha256'

    def __init__(self, filename=None, sign=False, verify=False):
        """
        Initialise an instance using a (valid) filename.
        """
        self.sign = sign
        self.should_verify = verify
        self.buildver = ''
        self.pyver = [PYVER]
        self.abi = ['none']
        self.arch = ['any']
        self.dirname = os.getcwd()
        if filename is None:
            self.name = 'dummy'
            self.version = '0.1'
            self._filename = self.filename
        else:
            m = NAME_VERSION_RE.match(filename)
            if m:
                info = m.groupdict('')
                self.name = info['nm']
                # Reinstate the local version separator
                self.version = info['vn'].replace('_', '-')
                self.buildver = info['bn']
                self._filename = self.filename
            else:
                dirname, filename = os.path.split(filename)
                m = FILENAME_RE.match(filename)
                if not m:
                    raise DistlibException('Invalid name or '
                                           'filename: %r' % filename)
                if dirname:
                    self.dirname = os.path.abspath(dirname)
                self._filename = filename
                info = m.groupdict('')
                self.name = info['nm']
                self.version = info['vn']
                self.buildver = info['bn']
                self.pyver = info['py'].split('.')
                self.abi = info['bi'].split('.')
                self.arch = info['ar'].split('.')

    @property
    def filename(self):
        """
        Build and return a filename from the various components.
        """
        if self.buildver:
            buildver = '-' + self.buildver
        else:
            buildver = ''
        pyver = '.'.join(self.pyver)
        abi = '.'.join(self.abi)
        arch = '.'.join(self.arch)
        # replace - with _ as a local version separator
        version = self.version.replace('-', '_')
        return '%s-%s%s-%s-%s-%s.whl' % (self.name, version, buildver, pyver, abi, arch)

    @property
    def exists(self):
        path = os.path.join(self.dirname, self.filename)
        return os.path.isfile(path)

    @property
    def tags(self):
        for pyver in self.pyver:
            for abi in self.abi:
                for arch in self.arch:
                    yield pyver, abi, arch

    @cached_property
    def metadata(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        wrapper = codecs.getreader('utf-8')
        with ZipFile(pathname, 'r') as zf:
            self.get_wheel_metadata(zf)
            # wv = wheel_metadata['Wheel-Version'].split('.', 1)
            # file_version = tuple([int(i) for i in wv])
            # if file_version < (1, 1):
            # fns = [WHEEL_METADATA_FILENAME, METADATA_FILENAME,
            # LEGACY_METADATA_FILENAME]
            # else:
            # fns = [WHEEL_METADATA_FILENAME, METADATA_FILENAME]
            fns = [WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME]
            result = None
            for fn in fns:
                try:
                    metadata_filename = posixpath.join(info_dir, fn)
                    with zf.open(metadata_filename) as bf:
                        wf = wrapper(bf)
                        result = Metadata(fileobj=wf)
                        if result:
                            break
                except KeyError:
                    pass
            if not result:
                raise ValueError('Invalid wheel, because metadata is '
                                 'missing: looked in %s' % ', '.join(fns))
        return result

    def get_wheel_metadata(self, zf):
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        metadata_filename = posixpath.join(info_dir, 'WHEEL')
        with zf.open(metadata_filename) as bf:
            wf = codecs.getreader('utf-8')(bf)
            message = message_from_file(wf)
        return dict(message)

    @cached_property
    def info(self):
        pathname = os.path.join(self.dirname, self.filename)
        with ZipFile(pathname, 'r') as zf:
            result = self.get_wheel_metadata(zf)
        return result

    def process_shebang(self, data):
        m = SHEBANG_RE.match(data)
        if m:
            end = m.end()
            shebang, data_after_shebang = data[:end], data[end:]
            # Preserve any arguments after the interpreter
            if b'pythonw' in shebang.lower():
                shebang_python = SHEBANG_PYTHONW
            else:
                shebang_python = SHEBANG_PYTHON
            m = SHEBANG_DETAIL_RE.match(shebang)
            if m:
                args = b' ' + m.groups()[-1]
            else:
                args = b''
            shebang = shebang_python + args
            data = shebang + data_after_shebang
        else:
            cr = data.find(b'\r')
            lf = data.find(b'\n')
            if cr < 0 or cr > lf:
                term = b'\n'
            else:
                if data[cr:cr + 2] == b'\r\n':
                    term = b'\r\n'
                else:
                    term = b'\r'
            data = SHEBANG_PYTHON + term + data
        return data

    def get_hash(self, data, hash_kind=None):
        if hash_kind is None:
            hash_kind = self.hash_kind
        try:
            hasher = getattr(hashlib, hash_kind)
        except AttributeError:
            raise DistlibException('Unsupported hash algorithm: %r' % hash_kind)
        result = hasher(data).digest()
        result = base64.urlsafe_b64encode(result).rstrip(b'=').decode('ascii')
        return hash_kind, result

    def write_record(self, records, record_path, archive_record_path):
        records = list(records)  # make a copy, as mutated
        records.append((archive_record_path, '', ''))
        with CSVWriter(record_path) as writer:
            for row in records:
                writer.writerow(row)

    def write_records(self, info, libdir, archive_paths):
        records = []
        distinfo, info_dir = info
        # hasher = getattr(hashlib, self.hash_kind)
        for ap, p in archive_paths:
            with open(p, 'rb') as f:
                data = f.read()
            digest = '%s=%s' % self.get_hash(data)
            size = os.path.getsize(p)
            records.append((ap, digest, size))

        p = os.path.join(distinfo, 'RECORD')
        ap = to_posix(os.path.join(info_dir, 'RECORD'))
        self.write_record(records, p, ap)
        archive_paths.append((ap, p))

    def build_zip(self, pathname, archive_paths):
        with ZipFile(pathname, 'w', zipfile.ZIP_DEFLATED) as zf:
            for ap, p in archive_paths:
                logger.debug('Wrote %s to %s in wheel', p, ap)
                zf.write(p, ap)

    def build(self, paths, tags=None, wheel_version=None):
        """
        Build a wheel from files in specified paths, and use any specified tags
        when determining the name of the wheel.
        """
        if tags is None:
            tags = {}

        libkey = list(filter(lambda o: o in paths, ('purelib', 'platlib')))[0]
        if libkey == 'platlib':
            is_pure = 'false'
            default_pyver = [IMPVER]
            default_abi = [ABI]
            default_arch = [ARCH]
        else:
            is_pure = 'true'
            default_pyver = [PYVER]
            default_abi = ['none']
            default_arch = ['any']

        self.pyver = tags.get('pyver', default_pyver)
        self.abi = tags.get('abi', default_abi)
        self.arch = tags.get('arch', default_arch)

        libdir = paths[libkey]

        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        archive_paths = []

        # First, stuff which is not in site-packages
        for key in ('data', 'headers', 'scripts'):
            if key not in paths:
                continue
            path = paths[key]
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fn in files:
                        p = fsdecode(os.path.join(root, fn))
                        rp = os.path.relpath(p, path)
                        ap = to_posix(os.path.join(data_dir, key, rp))
                        archive_paths.append((ap, p))
                        if key == 'scripts' and not p.endswith('.exe'):
                            with open(p, 'rb') as f:
                                data = f.read()
                            data = self.process_shebang(data)
                            with open(p, 'wb') as f:
                                f.write(data)

        # Now, stuff which is in site-packages, other than the
        # distinfo stuff.
        path = libdir
        distinfo = None
        for root, dirs, files in os.walk(path):
            if root == path:
                # At the top level only, save distinfo for later
                # and skip it for now
                for i, dn in enumerate(dirs):
                    dn = fsdecode(dn)
                    if dn.endswith('.dist-info'):
                        distinfo = os.path.join(root, dn)
                        del dirs[i]
                        break
                assert distinfo, '.dist-info directory expected, not found'

            for fn in files:
                # comment out next suite to leave .pyc files in
                if fsdecode(fn).endswith(('.pyc', '.pyo')):
                    continue
                p = os.path.join(root, fn)
                rp = to_posix(os.path.relpath(p, path))
                archive_paths.append((rp, p))

        # Now distinfo. Assumed to be flat, i.e. os.listdir is enough.
        files = os.listdir(distinfo)
        for fn in files:
            if fn not in ('RECORD', 'INSTALLER', 'SHARED', 'WHEEL'):
                p = fsdecode(os.path.join(distinfo, fn))
                ap = to_posix(os.path.join(info_dir, fn))
                archive_paths.append((ap, p))

        wheel_metadata = [
            'Wheel-Version: %d.%d' % (wheel_version or self.wheel_version),
            'Generator: distlib %s' % __version__,
            'Root-Is-Purelib: %s' % is_pure,
        ]
        for pyver, abi, arch in self.tags:
            wheel_metadata.append('Tag: %s-%s-%s' % (pyver, abi, arch))
        p = os.path.join(distinfo, 'WHEEL')
        with open(p, 'w') as f:
            f.write('\n'.join(wheel_metadata))
        ap = to_posix(os.path.join(info_dir, 'WHEEL'))
        archive_paths.append((ap, p))

        # sort the entries by archive path. Not needed by any spec, but it
        # keeps the archive listing and RECORD tidier than they would otherwise
        # be. Use the number of path segments to keep directory entries together,
        # and keep the dist-info stuff at the end.
        def sorter(t):
            ap = t[0]
            n = ap.count('/')
            if '.dist-info' in ap:
                n += 10000
            return (n, ap)

        archive_paths = sorted(archive_paths, key=sorter)

        # Now, at last, RECORD.
        # Paths in here are archive paths - nothing else makes sense.
        self.write_records((distinfo, info_dir), libdir, archive_paths)
        # Now, ready to build the zip file
        pathname = os.path.join(self.dirname, self.filename)
        self.build_zip(pathname, archive_paths)
        return pathname

    def skip_entry(self, arcname):
        """
        Determine whether an archive entry should be skipped when verifying
        or installing.
        """
        # The signature file won't be in RECORD,
        # and we  don't currently don't do anything with it
        # We also skip directories, as they won't be in RECORD
        # either. See:
        #
        # https://github.com/pypa/wheel/issues/294
        # https://github.com/pypa/wheel/issues/287
        # https://github.com/pypa/wheel/pull/289
        #
        return arcname.endswith(('/', '/RECORD.jws'))

    def install(self, paths, maker, **kwargs):
        """
        Install a wheel to the specified paths. If kwarg ``warner`` is
        specified, it should be a callable, which will be called with two
        tuples indicating the wheel version of this software and the wheel
        version in the file, if there is a discrepancy in the versions.
        This can be used to issue any warnings to raise any exceptions.
        If kwarg ``lib_only`` is True, only the purelib/platlib files are
        installed, and the headers, scripts, data and dist-info metadata are
        not written. If kwarg ``bytecode_hashed_invalidation`` is True, written
        bytecode will try to use file-hash based invalidation (PEP-552) on
        supported interpreter versions (CPython 3.7+).

        The return value is a :class:`InstalledDistribution` instance unless
        ``options.lib_only`` is True, in which case the return value is ``None``.
        """

        dry_run = maker.dry_run
        warner = kwargs.get('warner')
        lib_only = kwargs.get('lib_only', False)
        bc_hashed_invalidation = kwargs.get('bytecode_hashed_invalidation', False)

        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        metadata_name = posixpath.join(info_dir, LEGACY_METADATA_FILENAME)
        wheel_metadata_name = posixpath.join(info_dir, 'WHEEL')
        record_name = posixpath.join(info_dir, 'RECORD')

        wrapper = codecs.getreader('utf-8')

        with ZipFile(pathname, 'r') as zf:
            with zf.open(wheel_metadata_name) as bwf:
                wf = wrapper(bwf)
                message = message_from_file(wf)
            wv = message['Wheel-Version'].split('.', 1)
            file_version = tuple([int(i) for i in wv])
            if (file_version != self.wheel_version) and warner:
                warner(self.wheel_version, file_version)

            if message['Root-Is-Purelib'] == 'true':
                libdir = paths['purelib']
            else:
                libdir = paths['platlib']

            records = {}
            with zf.open(record_name) as bf:
                with CSVReader(stream=bf) as reader:
                    for row in reader:
                        p = row[0]
                        records[p] = row

            data_pfx = posixpath.join(data_dir, '')
            info_pfx = posixpath.join(info_dir, '')
            script_pfx = posixpath.join(data_dir, 'scripts', '')

            # make a new instance rather than a copy of maker's,
            # as we mutate it
            fileop = FileOperator(dry_run=dry_run)
            fileop.record = True  # so we can rollback if needed

            bc = not sys.dont_write_bytecode  # Double negatives. Lovely!

            outfiles = []  # for RECORD writing

            # for script copying/shebang processing
            workdir = tempfile.mkdtemp()
            # set target dir later
            # we default add_launchers to False, as the
            # Python Launcher should be used instead
            maker.source_dir = workdir
            maker.target_dir = None
            try:
                for zinfo in zf.infolist():
                    arcname = zinfo.filename
                    if isinstance(arcname, text_type):
                        u_arcname = arcname
                    else:
                        u_arcname = arcname.decode('utf-8')
                    if self.skip_entry(u_arcname):
                        continue
                    row = records[u_arcname]
                    if row[2] and str(zinfo.file_size) != row[2]:
                        raise DistlibException('size mismatch for '
                                               '%s' % u_arcname)
                    if row[1]:
                        kind, value = row[1].split('=', 1)
                        with zf.open(arcname) as bf:
                            data = bf.read()
                        _, digest = self.get_hash(data, kind)
                        if digest != value:
                            raise DistlibException('digest mismatch for '
                                                   '%s' % arcname)

                    if lib_only and u_arcname.startswith((info_pfx, data_pfx)):
                        logger.debug('lib_only: skipping %s', u_arcname)
                        continue
                    is_script = (u_arcname.startswith(script_pfx) and not u_arcname.endswith('.exe'))

                    if u_arcname.startswith(data_pfx):
                        _, where, rp = u_arcname.split('/', 2)
                        outfile = os.path.join(paths[where], convert_path(rp))
                    else:
                        # meant for site-packages.
                        if u_arcname in (wheel_metadata_name, record_name):
                            continue
                        outfile = os.path.join(libdir, convert_path(u_arcname))
                    if not is_script:
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, outfile)
                        # Issue #147: permission bits aren't preserved. Using
                        # zf.extract(zinfo, libdir) should have worked, but didn't,
                        # see https://www.thetopsites.net/article/53834422.shtml
                        # So ... manually preserve permission bits as given in zinfo
                        if os.name == 'posix':
                            # just set the normal permission bits
                            os.chmod(outfile, (zinfo.external_attr >> 16) & 0x1FF)
                        outfiles.append(outfile)
                        # Double check the digest of the written file
                        if not dry_run and row[1]:
                            with open(outfile, 'rb') as bf:
                                data = bf.read()
                                _, newdigest = self.get_hash(data, kind)
                                if newdigest != digest:
                                    raise DistlibException('digest mismatch '
                                                           'on write for '
                                                           '%s' % outfile)
                        if bc and outfile.endswith('.py'):
                            try:
                                pyc = fileop.byte_compile(outfile, hashed_invalidation=bc_hashed_invalidation)
                                outfiles.append(pyc)
                            except Exception:
                                # Don't give up if byte-compilation fails,
                                # but log it and perhaps warn the user
                                logger.warning('Byte-compilation failed', exc_info=True)
                    else:
                        fn = os.path.basename(convert_path(arcname))
                        workname = os.path.join(workdir, fn)
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, workname)

                        dn, fn = os.path.split(outfile)
                        maker.target_dir = dn
                        filenames = maker.make(fn)
                        fileop.set_executable_mode(filenames)
                        outfiles.extend(filenames)

                if lib_only:
                    logger.debug('lib_only: returning None')
                    dist = None
                else:
                    # Generate scripts

                    # Try to get pydist.json so we can see if there are
                    # any commands to generate. If this fails (e.g. because
                    # of a legacy wheel), log a warning but don't give up.
                    commands = None
                    file_version = self.info['Wheel-Version']
                    if file_version == '1.0':
                        # Use legacy info
                        ep = posixpath.join(info_dir, 'entry_points.txt')
                        try:
                            with zf.open(ep) as bwf:
                                epdata = read_exports(bwf)
                            commands = {}
                            for key in ('console', 'gui'):
                                k = '%s_scripts' % key
                                if k in epdata:
                                    commands['wrap_%s' % key] = d = {}
                                    for v in epdata[k].values():
                                        s = '%s:%s' % (v.prefix, v.suffix)
                                        if v.flags:
                                            s += ' [%s]' % ','.join(v.flags)
                                        d[v.name] = s
                        except Exception:
                            logger.warning('Unable to read legacy script '
                                           'metadata, so cannot generate '
                                           'scripts')
                    else:
                        try:
                            with zf.open(metadata_name) as bwf:
                                wf = wrapper(bwf)
                                commands = json.load(wf).get('extensions')
                                if commands:
                                    commands = commands.get('python.commands')
                        except Exception:
                            logger.warning('Unable to read JSON metadata, so '
                                           'cannot generate scripts')
                    if commands:
                        console_scripts = commands.get('wrap_console', {})
                        gui_scripts = commands.get('wrap_gui', {})
                        if console_scripts or gui_scripts:
                            script_dir = paths.get('scripts', '')
                            if not os.path.isdir(script_dir):
                                raise ValueError('Valid script path not '
                                                 'specified')
                            maker.target_dir = script_dir
                            for k, v in console_scripts.items():
                                script = '%s = %s' % (k, v)
                                filenames = maker.make(script)
                                fileop.set_executable_mode(filenames)

                            if gui_scripts:
                                options = {'gui': True}
                                for k, v in gui_scripts.items():
                                    script = '%s = %s' % (k, v)
                                    filenames = maker.make(script, options)
                                    fileop.set_executable_mode(filenames)

                    p = os.path.join(libdir, info_dir)
                    dist = InstalledDistribution(p)

                    # Write SHARED
                    paths = dict(paths)  # don't change passed in dict
                    del paths['purelib']
                    del paths['platlib']
                    paths['lib'] = libdir
                    p = dist.write_shared_locations(paths, dry_run)
                    if p:
                        outfiles.append(p)

                    # Write RECORD
                    dist.write_installed_files(outfiles, paths['prefix'], dry_run)
                return dist
            except Exception:  # pragma: no cover
                logger.exception('installation failed.')
                fileop.rollback()
                raise
            finally:
                shutil.rmtree(workdir)

    def _get_dylib_cache(self):
        global cache
        if cache is None:
            # Use native string to avoid issues on 2.x: see Python #20140.
            base = os.path.join(get_cache_base(), str('dylib-cache'), '%s.%s' % sys.version_info[:2])
            cache = Cache(base)
        return cache

    def _get_extensions(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        arcname = posixpath.join(info_dir, 'EXTENSIONS')
        wrapper = codecs.getreader('utf-8')
        result = []
        with ZipFile(pathname, 'r') as zf:
            try:
                with zf.open(arcname) as bf:
                    wf = wrapper(bf)
                    extensions = json.load(wf)
                    cache = self._get_dylib_cache()
                    prefix = cache.prefix_to_dir(self.filename, use_abspath=False)
                    cache_base = os.path.join(cache.base, prefix)
                    if not os.path.isdir(cache_base):
                        os.makedirs(cache_base)
                    for name, relpath in extensions.items():
                        dest = os.path.join(cache_base, convert_path(relpath))
                        if not os.path.exists(dest):
                            extract = True
                        else:
                            file_time = os.stat(dest).st_mtime
                            file_time = datetime.datetime.fromtimestamp(file_time)
                            info = zf.getinfo(relpath)
                            wheel_time = datetime.datetime(*info.date_time)
                            extract = wheel_time > file_time
                        if extract:
                            zf.extract(relpath, cache_base)
                        result.append((name, dest))
            except KeyError:
                pass
        return result

    def is_compatible(self):
        """
        Determine if a wheel is compatible with the running system.
        """
        return is_compatible(self)

    def is_mountable(self):
        """
        Determine if a wheel is asserted as mountable by its metadata.
        """
        return True  # for now - metadata details TBD

    def mount(self, append=False):
        pathname = os.path.abspath(os.path.join(self.dirname, self.filename))
        if not self.is_compatible():
            msg = 'Wheel %s not compatible with this Python.' % pathname
            raise DistlibException(msg)
        if not self.is_mountable():
            msg = 'Wheel %s is marked as not mountable.' % pathname
            raise DistlibException(msg)
        if pathname in sys.path:
            logger.debug('%s already in path', pathname)
        else:
            if append:
                sys.path.append(pathname)
            else:
                sys.path.insert(0, pathname)
            extensions = self._get_extensions()
            if extensions:
                if _hook not in sys.meta_path:
                    sys.meta_path.append(_hook)
                _hook.add(pathname, extensions)

    def unmount(self):
        pathname = os.path.abspath(os.path.join(self.dirname, self.filename))
        if pathname not in sys.path:
            logger.debug('%s not in path', pathname)
        else:
            sys.path.remove(pathname)
            if pathname in _hook.impure_wheels:
                _hook.remove(pathname)
            if not _hook.impure_wheels:
                if _hook in sys.meta_path:
                    sys.meta_path.remove(_hook)

    def verify(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        # data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        # metadata_name = posixpath.join(info_dir, LEGACY_METADATA_FILENAME)
        wheel_metadata_name = posixpath.join(info_dir, 'WHEEL')
        record_name = posixpath.join(info_dir, 'RECORD')

        wrapper = codecs.getreader('utf-8')

        with ZipFile(pathname, 'r') as zf:
            with zf.open(wheel_metadata_name) as bwf:
                wf = wrapper(bwf)
                message_from_file(wf)
            # wv = message['Wheel-Version'].split('.', 1)
            # file_version = tuple([int(i) for i in wv])
            # TODO version verification

            records = {}
            with zf.open(record_name) as bf:
                with CSVReader(stream=bf) as reader:
                    for row in reader:
                        p = row[0]
                        records[p] = row

            for zinfo in zf.infolist():
                arcname = zinfo.filename
                if isinstance(arcname, text_type):
                    u_arcname = arcname
                else:
                    u_arcname = arcname.decode('utf-8')
                # See issue #115: some wheels have .. in their entries, but
                # in the filename ... e.g. __main__..py ! So the check is
                # updated to look for .. in the directory portions
                p = u_arcname.split('/')
                if '..' in p:
                    raise DistlibException('invalid entry in '
                                           'wheel: %r' % u_arcname)

                if self.skip_entry(u_arcname):
                    continue
                row = records[u_arcname]
                if row[2] and str(zinfo.file_size) != row[2]:
                    raise DistlibException('size mismatch for '
                                           '%s' % u_arcname)
                if row[1]:
                    kind, value = row[1].split('=', 1)
                    with zf.open(arcname) as bf:
                        data = bf.read()
                    _, digest = self.get_hash(data, kind)
                    if digest != value:
                        raise DistlibException('digest mismatch for '
                                               '%s' % arcname)

    def update(self, modifier, dest_dir=None, **kwargs):
        """
        Update the contents of a wheel in a generic way. The modifier should
        be a callable which expects a dictionary argument: its keys are
        archive-entry paths, and its values are absolute filesystem paths
        where the contents the corresponding archive entries can be found. The
        modifier is free to change the contents of the files pointed to, add
        new entries and remove entries, before returning. This method will
        extract the entire contents of the wheel to a temporary location, call
        the modifier, and then use the passed (and possibly updated)
        dictionary to write a new wheel. If ``dest_dir`` is specified, the new
        wheel is written there -- otherwise, the original wheel is overwritten.

        The modifier should return True if it updated the wheel, else False.
        This method returns the same value the modifier returns.
        """

        def get_version(path_map, info_dir):
            version = path = None
            key = '%s/%s' % (info_dir, LEGACY_METADATA_FILENAME)
            if key not in path_map:
                key = '%s/PKG-INFO' % info_dir
            if key in path_map:
                path = path_map[key]
                version = Metadata(path=path).version
            return version, path

        def update_version(version, path):
            updated = None
            try:
                NormalizedVersion(version)
                i = version.find('-')
                if i < 0:
                    updated = '%s+1' % version
                else:
                    parts = [int(s) for s in version[i + 1:].split('.')]
                    parts[-1] += 1
                    updated = '%s+%s' % (version[:i], '.'.join(str(i) for i in parts))
            except UnsupportedVersionError:
                logger.debug('Cannot update non-compliant (PEP-440) '
                             'version %r', version)
            if updated:
                md = Metadata(path=path)
                md.version = updated
                legacy = path.endswith(LEGACY_METADATA_FILENAME)
                md.write(path=path, legacy=legacy)
                logger.debug('Version updated from %r to %r', version, updated)

        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        record_name = posixpath.join(info_dir, 'RECORD')
        with tempdir() as workdir:
            with ZipFile(pathname, 'r') as zf:
                path_map = {}
                for zinfo in zf.infolist():
                    arcname = zinfo.filename
                    if isinstance(arcname, text_type):
                        u_arcname = arcname
                    else:
                        u_arcname = arcname.decode('utf-8')
                    if u_arcname == record_name:
                        continue
                    if '..' in u_arcname:
                        raise DistlibException('invalid entry in '
                                               'wheel: %r' % u_arcname)
                    zf.extract(zinfo, workdir)
                    path = os.path.join(workdir, convert_path(u_arcname))
                    path_map[u_arcname] = path

            # Remember the version.
            original_version, _ = get_version(path_map, info_dir)
            # Files extracted. Call the modifier.
            modified = modifier(path_map, **kwargs)
            if modified:
                # Something changed - need to build a new wheel.
                current_version, path = get_version(path_map, info_dir)
                if current_version and (current_version == original_version):
                    # Add or update local version to signify changes.
                    update_version(current_version, path)
                # Decide where the new wheel goes.
                if dest_dir is None:
                    fd, newpath = tempfile.mkstemp(suffix='.whl', prefix='wheel-update-', dir=workdir)
                    os.close(fd)
                else:
                    if not os.path.isdir(dest_dir):
                        raise DistlibException('Not a directory: %r' % dest_dir)
                    newpath = os.path.join(dest_dir, self.filename)
                archive_paths = list(path_map.items())
                distinfo = os.path.join(workdir, info_dir)
                info = distinfo, info_dir
                self.write_records(info, workdir, archive_paths)
                self.build_zip(newpath, archive_paths)
                if dest_dir is None:
                    shutil.copyfile(newpath, pathname)
        return modified


def _get_glibc_version():
    import platform
    ver = platform.libc_ver()
    result = []
    if ver[0] == 'glibc':
        for s in ver[1].split('.'):
            result.append(int(s) if s.isdigit() else 0)
        result = tuple(result)
    return result


def compatible_tags():
    """
    Return (pyver, abi, arch) tuples compatible with this Python.
    """
    class _Version:
        def __init__(self, major, minor):
            self.major = major
            self.major_minor = (major, minor)
            self.string = ''.join((str(major), str(minor)))

        def __str__(self):
            return self.string


    versions = [
        _Version(sys.version_info.major, minor_version)
        for minor_version in range(sys.version_info.minor, -1, -1)
    ]
    abis = []
    for suffix in _get_suffixes():
        if suffix.startswith('.abi'):
            abis.append(suffix.split('.', 2)[1])
    abis.sort()
    if ABI != 'none':
        abis.insert(0, ABI)
    abis.append('none')
    result = []

    arches = [ARCH]
    if sys.platform == 'darwin':
        m = re.match(r'(\w+)_(\d+)_(\d+)_(\w+)$', ARCH)
        if m:
            name, major, minor, arch = m.groups()
            minor = int(minor)
            matches = [arch]
            if arch in ('i386', 'ppc'):
                matches.append('fat')
            if arch in ('i386', 'ppc', 'x86_64'):
                matches.append('fat3')
            if arch in ('ppc64', 'x86_64'):
                matches.append('fat64')
            if arch in ('i386', 'x86_64'):
                matches.append('intel')
            if arch in ('i386', 'x86_64', 'intel', 'ppc', 'ppc64'):
                matches.append('universal')
            while minor >= 0:
                for match in matches:
                    s = '%s_%s_%s_%s' % (name, major, minor, match)
                    if s != ARCH:  # already there
                        arches.append(s)
                minor -= 1

    # Most specific - our Python version, ABI and arch
    for i, version_object in enumerate(versions):
        version = str(version_object)
        add_abis = []

        if i == 0:
            add_abis = abis

        if IMP_PREFIX == 'cp' and version_object.major_minor >= (3, 2):
            limited_api_abi = 'abi' + str(version_object.major)
            if limited_api_abi not in add_abis:
                add_abis.append(limited_api_abi)

        for abi in add_abis:
            for arch in arches:
                result.append((''.join((IMP_PREFIX, version)), abi, arch))
                # manylinux
                if abi != 'none' and sys.platform.startswith('linux'):
                    arch = arch.replace('linux_', '')
                    parts = _get_glibc_version()
                    if len(parts) == 2:
                        if parts >= (2, 5):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux1_%s' % arch))
                        if parts >= (2, 12):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux2010_%s' % arch))
                        if parts >= (2, 17):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux2014_%s' % arch))
                        result.append((''.join(
                            (IMP_PREFIX, version)), abi, 'manylinux_%s_%s_%s' % (parts[0], parts[1], arch)))

    # where no ABI / arch dependency, but IMP_PREFIX dependency
    for i, version_object in enumerate(versions):
        version = str(version_object)
        result.append((''.join((IMP_PREFIX, version)), 'none', 'any'))
        if i == 0:
            result.append((''.join((IMP_PREFIX, version[0])), 'none', 'any'))

    # no IMP_PREFIX, ABI or arch dependency
    for i, version_object in enumerate(versions):
        version = str(version_object)
        result.append((''.join(('py', version)), 'none', 'any'))
        if i == 0:
            result.append((''.join(('py', version[0])), 'none', 'any'))

    return set(result)


COMPATIBLE_TAGS = compatible_tags()

del compatible_tags


def is_compatible(wheel, tags=None):
    if not isinstance(wheel, Wheel):
        wheel = Wheel(wheel)  # assume it's a filename
    result = False
    if tags is None:
        tags = COMPATIBLE_TAGS
    for ver, abi, arch in tags:
        if ver in wheel.pyver and abi in wheel.abi and arch in wheel.arch:
            result = True
            break
    return result

# === NexusCore/openenv\Lib\site-packages\jupyter_core\paths.py ===
"""Path utility functions."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Derived from IPython.utils.path, which is
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import errno
import os
import site
import stat
import sys
import tempfile
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Literal, Optional, overload

import platformdirs

from .utils import deprecation

pjoin = os.path.join

# Capitalize Jupyter in paths only on Windows and MacOS (when not in Homebrew)
if sys.platform == "win32" or (
    sys.platform == "darwin" and not sys.prefix.startswith("/opt/homebrew")
):
    APPNAME = "Jupyter"
else:
    APPNAME = "jupyter"

# UF_HIDDEN is a stat flag not defined in the stat module.
# It is used by BSD to indicate hidden files.
UF_HIDDEN = getattr(stat, "UF_HIDDEN", 32768)


@overload
def envset(name: str, default: bool = False) -> bool: ...


@overload
def envset(name: str, default: Literal[None]) -> Optional[bool]: ...


def envset(name: str, default: Optional[bool] = False) -> Optional[bool]:
    """Return the boolean value of a given environment variable.

    An environment variable is considered set if it is assigned to a value
    other than 'no', 'n', 'false', 'off', '0', or '0.0' (case insensitive)

    If the environment variable is not defined, the default value is returned.
    """
    if name not in os.environ:
        return default

    return os.environ[name].lower() not in ["no", "n", "false", "off", "0", "0.0"]


def use_platform_dirs() -> bool:
    """Determine if platformdirs should be used for system-specific paths.

    We plan for this to default to False in jupyter_core version 5 and to True
    in jupyter_core version 6.
    """
    return envset("JUPYTER_PLATFORM_DIRS", False)


def get_home_dir() -> str:
    """Get the real path of the home directory"""
    homedir = Path("~").expanduser()
    # Next line will make things work even when /home/ is a symlink to
    # /usr/home as it is on FreeBSD, for example
    return str(Path(homedir).resolve())


_dtemps: dict[str, str] = {}


def _do_i_own(path: str) -> bool:
    """Return whether the current user owns the given path"""
    p = Path(path).resolve()

    # walk up to first existing parent
    while not p.exists() and p != p.parent:
        p = p.parent

    # simplest check: owner by name
    # not always implemented or available
    try:
        return p.owner() == os.getlogin()
    except Exception:  # noqa: S110
        pass

    if hasattr(os, "geteuid"):
        try:
            st = p.stat()
            return st.st_uid == os.geteuid()
        except (NotImplementedError, OSError):
            # geteuid not always implemented
            pass

    # no ownership checks worked, check write access
    return os.access(p, os.W_OK)


def prefer_environment_over_user() -> bool:
    """Determine if environment-level paths should take precedence over user-level paths."""
    # If JUPYTER_PREFER_ENV_PATH is defined, that signals user intent, so return its value
    if "JUPYTER_PREFER_ENV_PATH" in os.environ:
        return envset("JUPYTER_PREFER_ENV_PATH")

    # If we are in a Python virtualenv, default to True (see https://docs.python.org/3/library/venv.html#venv-def)
    if sys.prefix != sys.base_prefix and _do_i_own(sys.prefix):
        return True

    # If sys.prefix indicates Python comes from a conda/mamba environment that is not the root environment, default to True
    if (
        "CONDA_PREFIX" in os.environ
        and sys.prefix.startswith(os.environ["CONDA_PREFIX"])
        and os.environ.get("CONDA_DEFAULT_ENV", "base") != "base"
        and _do_i_own(sys.prefix)
    ):
        return True

    return False


def _mkdtemp_once(name: str) -> str:
    """Make or reuse a temporary directory.

    If this is called with the same name in the same process, it will return
    the same directory.
    """
    try:
        return _dtemps[name]
    except KeyError:
        d = _dtemps[name] = tempfile.mkdtemp(prefix=name + "-")
        return d


def jupyter_config_dir() -> str:
    """Get the Jupyter config directory for this platform and user.

    Returns JUPYTER_CONFIG_DIR if defined, otherwise the appropriate
    directory for the platform.
    """

    env = os.environ
    if env.get("JUPYTER_NO_CONFIG"):
        return _mkdtemp_once("jupyter-clean-cfg")

    if env.get("JUPYTER_CONFIG_DIR"):
        return env["JUPYTER_CONFIG_DIR"]

    if use_platform_dirs():
        return platformdirs.user_config_dir(APPNAME, appauthor=False)

    home_dir = get_home_dir()
    return pjoin(home_dir, ".jupyter")


def jupyter_data_dir() -> str:
    """Get the config directory for Jupyter data files for this platform and user.

    These are non-transient, non-configuration files.

    Returns JUPYTER_DATA_DIR if defined, else a platform-appropriate path.
    """
    env = os.environ

    if env.get("JUPYTER_DATA_DIR"):
        return env["JUPYTER_DATA_DIR"]

    if use_platform_dirs():
        return platformdirs.user_data_dir(APPNAME, appauthor=False)

    home = get_home_dir()

    if sys.platform == "darwin":
        return str(Path(home, "Library", "Jupyter"))
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", None)
        if appdata:
            return str(Path(appdata, "jupyter").resolve())
        return pjoin(jupyter_config_dir(), "data")
    # Linux, non-OS X Unix, AIX, etc.
    xdg = env.get("XDG_DATA_HOME", None)
    if not xdg:
        xdg = pjoin(home, ".local", "share")
    return pjoin(xdg, "jupyter")


def jupyter_runtime_dir() -> str:
    """Return the runtime dir for transient jupyter files.

    Returns JUPYTER_RUNTIME_DIR if defined.

    The default is now (data_dir)/runtime on all platforms;
    we no longer use XDG_RUNTIME_DIR after various problems.
    """
    env = os.environ

    if env.get("JUPYTER_RUNTIME_DIR"):
        return env["JUPYTER_RUNTIME_DIR"]

    return pjoin(jupyter_data_dir(), "runtime")


# %PROGRAMDATA% is not safe by default, require opt-in to trust it
_use_programdata: bool = envset("JUPYTER_USE_PROGRAMDATA")
# _win_programdata is a path str if we're using it, None otherwise
_win_programdata: str | None = None
if os.name == "nt" and _use_programdata:
    _win_programdata = os.environ.get("PROGRAMDATA", None)


if use_platform_dirs():
    if os.name == "nt" and not _use_programdata:
        # default PROGRAMDATA used by site_* is not safe by default on Windows
        SYSTEM_JUPYTER_PATH = [str(Path(sys.prefix, "share", "jupyter"))]
    else:
        SYSTEM_JUPYTER_PATH = platformdirs.site_data_dir(
            APPNAME, appauthor=False, multipath=True
        ).split(os.pathsep)
else:
    deprecation(
        "Jupyter is migrating its paths to use standard platformdirs\n"
        "given by the platformdirs library.  To remove this warning and\n"
        "see the appropriate new directories, set the environment variable\n"
        "`JUPYTER_PLATFORM_DIRS=1` and then run `jupyter --paths`.\n"
        "The use of platformdirs will be the default in `jupyter_core` v6"
    )
    if os.name == "nt":
        # PROGRAMDATA is not defined by default on XP, and not safe by default
        if _win_programdata:
            SYSTEM_JUPYTER_PATH = [pjoin(_win_programdata, "jupyter")]
        else:
            SYSTEM_JUPYTER_PATH = [str(Path(sys.prefix, "share", "jupyter"))]
    else:
        SYSTEM_JUPYTER_PATH = [
            "/usr/local/share/jupyter",
            "/usr/share/jupyter",
        ]

ENV_JUPYTER_PATH: list[str] = [str(Path(sys.prefix, "share", "jupyter"))]


def jupyter_path(*subdirs: str) -> list[str]:
    """Return a list of directories to search for data files.

    There are four sources of paths to search:

    - $JUPYTER_PATH environment variable (always highest priority)
    - user directories (e.g. ~/.local/share/jupyter)
    - environment directories (e.g. {sys.prefix}/share/jupyter)
    - system-wide paths (e.g. /usr/local/share/jupyter)

    JUPYTER_PATH environment variable has highest priority, if defined,
    and is purely additive.

    If the JUPYTER_PREFER_ENV_PATH environment variable is set, the environment-level
    directories will have priority over user-level directories.
    You can also set JUPYTER_PREFER_ENV_PATH=0 to explicitly prefer user directories.
    If Jupyter detects that you are in a virtualenv or conda environment,
    environment paths are also preferred to user paths,
    otherwise user paths are preferred to environment paths.

    If the Python site.ENABLE_USER_SITE variable is True, we also add the
    appropriate Python user site subdirectory to the user-level directories.

    Finally, system-wide directories, such as `/usr/local/share/jupyter` are searched.

    If ``*subdirs`` are given, that subdirectory will be added to each element.


    .. versionchanged:: 5.8

        On Windows, %PROGRAMDATA% will be used as a system-wide path only if
        the JUPYTER_USE_PROGRAMDATA env is set.
        By default, there is no default system-wide path on Windows and the env path
        is used instead.

    Examples:

    >>> jupyter_path()
    ['~/.local/jupyter', '/usr/local/share/jupyter']
    >>> jupyter_path('kernels')
    ['~/.local/jupyter/kernels', '/usr/local/share/jupyter/kernels']
    """

    paths: list[str] = []

    # highest priority is explicit environment variable
    if os.environ.get("JUPYTER_PATH"):
        paths.extend(p.rstrip(os.sep) for p in os.environ["JUPYTER_PATH"].split(os.pathsep))

    # Next is environment or user, depending on the JUPYTER_PREFER_ENV_PATH flag
    user = [jupyter_data_dir()]
    if site.ENABLE_USER_SITE:
        # Check if site.getuserbase() exists to be compatible with virtualenv,
        # which often does not have this method.
        userbase: Optional[str]
        userbase = site.getuserbase() if hasattr(site, "getuserbase") else site.USER_BASE

        if userbase:
            userdir = str(Path(userbase, "share", "jupyter"))
            if userdir not in user:
                user.append(userdir)

    # Windows usually doesn't have a 'system' prefix,
    # so 'system' and 'env' are the same
    # make sure that env can still be preferred in this case
    if ENV_JUPYTER_PATH == SYSTEM_JUPYTER_PATH:
        env = ENV_JUPYTER_PATH
    else:
        env = [p for p in ENV_JUPYTER_PATH if p not in SYSTEM_JUPYTER_PATH]

    if prefer_environment_over_user():
        paths.extend(env)
        paths.extend(user)
    else:
        paths.extend(user)
        paths.extend(env)

    # finally, add system paths (can overlap with env, so avoid duplicates)
    for _path in SYSTEM_JUPYTER_PATH:
        if _path not in paths:
            paths.append(_path)

    # add subdir, if requested
    if subdirs:
        paths = [pjoin(p, *subdirs) for p in paths]
    return paths


ENV_CONFIG_PATH: list[str] = [str(Path(sys.prefix, "etc", "jupyter"))]

if use_platform_dirs():
    if os.name == "nt" and not _use_programdata:
        # default PROGRAMDATA is not safe by default on Windows
        # use ENV to avoid an empty list, since some may assume this is non-empty
        SYSTEM_CONFIG_PATH = ENV_CONFIG_PATH[:]
    else:
        SYSTEM_CONFIG_PATH = platformdirs.site_config_dir(
            APPNAME, appauthor=False, multipath=True
        ).split(os.pathsep)
elif os.name == "nt":
    # PROGRAMDATA is not defined by default on XP, and not safe by default
    # but make sure it's not empty
    if _win_programdata:
        SYSTEM_CONFIG_PATH = [str(Path(_win_programdata, "jupyter"))]
    else:
        SYSTEM_CONFIG_PATH = ENV_CONFIG_PATH[:]
else:
    SYSTEM_CONFIG_PATH = [
        "/usr/local/etc/jupyter",
        "/etc/jupyter",
    ]


def jupyter_config_path() -> list[str]:
    """Return the search path for Jupyter config files as a list.

    If the JUPYTER_PREFER_ENV_PATH environment variable is set, the
    environment-level directories will have priority over user-level
    directories.

    If the Python site.ENABLE_USER_SITE variable is True, we also add the
    appropriate Python user site subdirectory to the user-level directories.

    Finally, system-wide directories such as `/usr/local/etc/jupyter` are searched.


    .. versionchanged:: 5.8

        On Windows, %PROGRAMDATA% will be used as a system-wide path only if
        the JUPYTER_USE_PROGRAMDATA env is set.
        By default, there is no system-wide config path on Windows.

    Examples:

    >>> jupyter_config_path()
    ['~/.jupyter', '~/.local/etc/jupyter', '/usr/local/etc/jupyter', '/etc/jupyter']

    """
    if os.environ.get("JUPYTER_NO_CONFIG"):
        # jupyter_config_dir makes a blank config when JUPYTER_NO_CONFIG is set.
        return [jupyter_config_dir()]

    paths: list[str] = []

    # highest priority is explicit environment variable
    if os.environ.get("JUPYTER_CONFIG_PATH"):
        paths.extend(p.rstrip(os.sep) for p in os.environ["JUPYTER_CONFIG_PATH"].split(os.pathsep))

    # Next is environment or user, depending on the JUPYTER_PREFER_ENV_PATH flag
    user = [jupyter_config_dir()]
    if site.ENABLE_USER_SITE:
        userbase: Optional[str]
        # Check if site.getuserbase() exists to be compatible with virtualenv,
        # which often does not have this method.
        userbase = site.getuserbase() if hasattr(site, "getuserbase") else site.USER_BASE

        if userbase:
            userdir = str(Path(userbase, "etc", "jupyter"))
            if userdir not in user:
                user.append(userdir)

    # Windows usually doesn't have a 'system' prefix,
    # so 'system' and 'env' are the same
    # make sure that env can still be preferred in this case
    if ENV_CONFIG_PATH == SYSTEM_CONFIG_PATH:
        env = ENV_CONFIG_PATH
    else:
        env = [p for p in ENV_CONFIG_PATH if p not in SYSTEM_CONFIG_PATH]

    if prefer_environment_over_user():
        paths.extend(env)
        paths.extend(user)
    else:
        paths.extend(user)
        paths.extend(env)

    # Finally, system path
    if ENV_CONFIG_PATH != SYSTEM_CONFIG_PATH:
        paths.extend(SYSTEM_CONFIG_PATH)
    return paths


def exists(path: str) -> bool:
    """Replacement for `os.path.exists` which works for host mapped volumes
    on Windows containers
    """
    try:
        os.lstat(path)
    except OSError:
        return False
    return True


def is_file_hidden_win(abs_path: str, stat_res: Optional[Any] = None) -> bool:
    """Is a file hidden?

    This only checks the file itself; it should be called in combination with
    checking the directory containing the file.

    Use is_hidden() instead to check the file and its parent directories.

    Parameters
    ----------
    abs_path : unicode
        The absolute path to check.
    stat_res : os.stat_result, optional
        The result of calling stat() on abs_path. If not passed, this function
        will call stat() internally.
    """
    if Path(abs_path).name.startswith("."):
        return True

    if stat_res is None:
        try:
            stat_res = Path(abs_path).stat()
        except OSError as e:
            if e.errno == errno.ENOENT:
                return False
            raise

    try:
        if (
            stat_res.st_file_attributes  # type:ignore[union-attr]
            & stat.FILE_ATTRIBUTE_HIDDEN  # type:ignore[attr-defined]
        ):
            return True
    except AttributeError:
        # allow AttributeError on PyPy for Windows
        # 'stat_result' object has no attribute 'st_file_attributes'
        # https://foss.heptapod.net/pypy/pypy/-/issues/3469
        warnings.warn(
            "hidden files are not detectable on this system, so no file will be marked as hidden.",
            stacklevel=2,
        )

    return False


def is_file_hidden_posix(abs_path: str, stat_res: Optional[Any] = None) -> bool:
    """Is a file hidden?

    This only checks the file itself; it should be called in combination with
    checking the directory containing the file.

    Use is_hidden() instead to check the file and its parent directories.

    Parameters
    ----------
    abs_path : unicode
        The absolute path to check.
    stat_res : os.stat_result, optional
        The result of calling stat() on abs_path. If not passed, this function
        will call stat() internally.
    """
    if Path(abs_path).name.startswith("."):
        return True

    if stat_res is None or stat.S_ISLNK(stat_res.st_mode):
        try:
            stat_res = Path(abs_path).stat()
        except OSError as e:
            if e.errno == errno.ENOENT:
                return False
            raise

    # check that dirs can be listed
    if stat.S_ISDIR(stat_res.st_mode):  # noqa: SIM102
        # use x-access, not actual listing, in case of slow/large listings
        if not os.access(abs_path, os.X_OK | os.R_OK):
            return True

    # check UF_HIDDEN
    if getattr(stat_res, "st_flags", 0) & UF_HIDDEN:
        return True

    return False


if sys.platform == "win32":
    is_file_hidden = is_file_hidden_win
else:
    is_file_hidden = is_file_hidden_posix


def is_hidden(abs_path: str, abs_root: str = "") -> bool:
    """Is a file hidden or contained in a hidden directory?

    This will start with the rightmost path element and work backwards to the
    given root to see if a path is hidden or in a hidden directory. Hidden is
    determined by either name starting with '.' or the UF_HIDDEN flag as
    reported by stat.

    If abs_path is the same directory as abs_root, it will be visible even if
    that is a hidden folder. This only checks the visibility of files
    and directories *within* abs_root.

    Parameters
    ----------
    abs_path : unicode
        The absolute path to check for hidden directories.
    abs_root : unicode
        The absolute path of the root directory in which hidden directories
        should be checked for.
    """
    abs_path = os.path.normpath(abs_path)
    abs_root = os.path.normpath(abs_root)

    if abs_path == abs_root:
        return False

    if is_file_hidden(abs_path):
        return True

    if not abs_root:
        abs_root = abs_path.split(os.sep, 1)[0] + os.sep
    inside_root = abs_path[len(abs_root) :]
    if any(part.startswith(".") for part in Path(inside_root).parts):
        return True

    # check UF_HIDDEN on any location up to root.
    # is_file_hidden() already checked the file, so start from its parent dir
    path = str(Path(abs_path).parent)
    while path and path.startswith(abs_root) and path != abs_root:
        if not Path(path).exists():
            path = str(Path(path).parent)
            continue
        try:
            # may fail on Windows junctions
            st = os.lstat(path)
        except OSError:
            return True
        if getattr(st, "st_flags", 0) & UF_HIDDEN:
            return True
        path = str(Path(path).parent)

    return False


def win32_restrict_file_to_user(fname: str) -> None:
    """Secure a windows file to read-only access for the user.
    Follows guidance from win32 library creator:
    http://timgolden.me.uk/python/win32_how_do_i/add-security-to-a-file.html

    This method should be executed against an already generated file which
    has no secrets written to it yet.

    Parameters
    ----------

    fname : unicode
        The path to the file to secure
    """
    try:
        import win32api
    except ImportError:
        return _win32_restrict_file_to_user_ctypes(fname)

    import ntsecuritycon as con
    import win32security

    # everyone, _domain, _type = win32security.LookupAccountName("", "Everyone")
    admins = win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid)
    user, _domain, _type = win32security.LookupAccountName(
        "", win32api.GetUserNameEx(win32api.NameSamCompatible)
    )

    sd = win32security.GetFileSecurity(fname, win32security.DACL_SECURITY_INFORMATION)

    dacl = win32security.ACL()
    # dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, everyone)
    dacl.AddAccessAllowedAce(
        win32security.ACL_REVISION,
        con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE | con.DELETE,
        user,
    )
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, admins)

    sd.SetSecurityDescriptorDacl(1, dacl, 0)
    win32security.SetFileSecurity(fname, win32security.DACL_SECURITY_INFORMATION, sd)
    return None


def _win32_restrict_file_to_user_ctypes(fname: str) -> None:
    """Secure a windows file to read-only access for the user.

    Follows guidance from win32 library creator:
    http://timgolden.me.uk/python/win32_how_do_i/add-security-to-a-file.html

    This method should be executed against an already generated file which
    has no secrets written to it yet.

    Parameters
    ----------

    fname : unicode
        The path to the file to secure
    """
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)  # type:ignore[attr-defined]
    secur32 = ctypes.WinDLL("secur32", use_last_error=True)  # type:ignore[attr-defined]

    NameSamCompatible = 2
    WinBuiltinAdministratorsSid = 26
    DACL_SECURITY_INFORMATION = 4
    ACL_REVISION = 2
    ERROR_INSUFFICIENT_BUFFER = 122
    ERROR_MORE_DATA = 234

    SYNCHRONIZE = 0x100000
    DELETE = 0x00010000
    STANDARD_RIGHTS_REQUIRED = 0xF0000
    STANDARD_RIGHTS_READ = 0x20000
    STANDARD_RIGHTS_WRITE = 0x20000
    FILE_READ_DATA = 1
    FILE_READ_EA = 8
    FILE_READ_ATTRIBUTES = 128
    FILE_WRITE_DATA = 2
    FILE_APPEND_DATA = 4
    FILE_WRITE_EA = 16
    FILE_WRITE_ATTRIBUTES = 256
    FILE_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 0x1FF
    FILE_GENERIC_READ = (
        STANDARD_RIGHTS_READ | FILE_READ_DATA | FILE_READ_ATTRIBUTES | FILE_READ_EA | SYNCHRONIZE
    )
    FILE_GENERIC_WRITE = (
        STANDARD_RIGHTS_WRITE
        | FILE_WRITE_DATA
        | FILE_WRITE_ATTRIBUTES
        | FILE_WRITE_EA
        | FILE_APPEND_DATA
        | SYNCHRONIZE
    )

    class ACL(ctypes.Structure):
        _fields_ = [
            ("AclRevision", wintypes.BYTE),
            ("Sbz1", wintypes.BYTE),
            ("AclSize", wintypes.WORD),
            ("AceCount", wintypes.WORD),
            ("Sbz2", wintypes.WORD),
        ]

    PSID = ctypes.c_void_p
    PACL = ctypes.POINTER(ACL)
    PSECURITY_DESCRIPTOR = ctypes.POINTER(wintypes.BYTE)

    def _nonzero_success(result: int, func: Any, args: Any) -> Any:  # noqa: ARG001
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())  # type:ignore[attr-defined]
        return args

    secur32.GetUserNameExW.errcheck = _nonzero_success
    secur32.GetUserNameExW.restype = wintypes.BOOL
    secur32.GetUserNameExW.argtypes = (
        ctypes.c_int,  # EXTENDED_NAME_FORMAT NameFormat
        wintypes.LPWSTR,  # LPWSTR lpNameBuffer,
        wintypes.PULONG,  # PULONG nSize
    )

    advapi32.CreateWellKnownSid.errcheck = _nonzero_success
    advapi32.CreateWellKnownSid.restype = wintypes.BOOL
    advapi32.CreateWellKnownSid.argtypes = (
        wintypes.DWORD,  # WELL_KNOWN_SID_TYPE WellKnownSidType
        PSID,  # PSID DomainSid
        PSID,  # PSID pSid
        wintypes.PDWORD,  # DWORD *cbSid
    )

    advapi32.LookupAccountNameW.errcheck = _nonzero_success
    advapi32.LookupAccountNameW.restype = wintypes.BOOL
    advapi32.LookupAccountNameW.argtypes = (
        wintypes.LPWSTR,  # LPCWSTR lpSystemName
        wintypes.LPWSTR,  # LPCWSTR lpAccountName
        PSID,  # PSID Sid
        wintypes.LPDWORD,  # LPDWORD cbSid
        wintypes.LPWSTR,  # LPCWSTR ReferencedDomainName
        wintypes.LPDWORD,  # LPDWORD cchReferencedDomainName
        wintypes.LPDWORD,  # PSID_NAME_USE peUse
    )

    advapi32.AddAccessAllowedAce.errcheck = _nonzero_success
    advapi32.AddAccessAllowedAce.restype = wintypes.BOOL
    advapi32.AddAccessAllowedAce.argtypes = (
        PACL,  # PACL pAcl
        wintypes.DWORD,  # DWORD dwAceRevision
        wintypes.DWORD,  # DWORD AccessMask
        PSID,  # PSID pSid
    )

    advapi32.SetSecurityDescriptorDacl.errcheck = _nonzero_success
    advapi32.SetSecurityDescriptorDacl.restype = wintypes.BOOL
    advapi32.SetSecurityDescriptorDacl.argtypes = (
        PSECURITY_DESCRIPTOR,  # PSECURITY_DESCRIPTOR pSecurityDescriptor
        wintypes.BOOL,  # BOOL bDaclPresent
        PACL,  # PACL pDacl
        wintypes.BOOL,  # BOOL bDaclDefaulted
    )

    advapi32.GetFileSecurityW.errcheck = _nonzero_success
    advapi32.GetFileSecurityW.restype = wintypes.BOOL
    advapi32.GetFileSecurityW.argtypes = (
        wintypes.LPCWSTR,  # LPCWSTR lpFileName
        wintypes.DWORD,  # SECURITY_INFORMATION RequestedInformation
        PSECURITY_DESCRIPTOR,  # PSECURITY_DESCRIPTOR pSecurityDescriptor
        wintypes.DWORD,  # DWORD nLength
        wintypes.LPDWORD,  # LPDWORD lpnLengthNeeded
    )

    advapi32.SetFileSecurityW.errcheck = _nonzero_success
    advapi32.SetFileSecurityW.restype = wintypes.BOOL
    advapi32.SetFileSecurityW.argtypes = (
        wintypes.LPCWSTR,  # LPCWSTR lpFileName
        wintypes.DWORD,  # SECURITY_INFORMATION SecurityInformation
        PSECURITY_DESCRIPTOR,  # PSECURITY_DESCRIPTOR pSecurityDescriptor
    )

    advapi32.MakeAbsoluteSD.errcheck = _nonzero_success
    advapi32.MakeAbsoluteSD.restype = wintypes.BOOL
    advapi32.MakeAbsoluteSD.argtypes = (
        PSECURITY_DESCRIPTOR,  # pSelfRelativeSecurityDescriptor
        PSECURITY_DESCRIPTOR,  # pAbsoluteSecurityDescriptor
        wintypes.LPDWORD,  # LPDWORD lpdwAbsoluteSecurityDescriptorSize
        PACL,  # PACL pDacl
        wintypes.LPDWORD,  # LPDWORD lpdwDaclSize
        PACL,  # PACL pSacl
        wintypes.LPDWORD,  # LPDWORD lpdwSaclSize
        PSID,  # PSID pOwner
        wintypes.LPDWORD,  # LPDWORD lpdwOwnerSize
        PSID,  # PSID pPrimaryGroup
        wintypes.LPDWORD,  # LPDWORD lpdwPrimaryGroupSize
    )

    advapi32.MakeSelfRelativeSD.errcheck = _nonzero_success
    advapi32.MakeSelfRelativeSD.restype = wintypes.BOOL
    advapi32.MakeSelfRelativeSD.argtypes = (
        PSECURITY_DESCRIPTOR,  # pAbsoluteSecurityDescriptor
        PSECURITY_DESCRIPTOR,  # pSelfRelativeSecurityDescriptor
        wintypes.LPDWORD,  # LPDWORD lpdwBufferLength
    )

    advapi32.InitializeAcl.errcheck = _nonzero_success
    advapi32.InitializeAcl.restype = wintypes.BOOL
    advapi32.InitializeAcl.argtypes = (
        PACL,  # PACL pAcl,
        wintypes.DWORD,  # DWORD nAclLength,
        wintypes.DWORD,  # DWORD dwAclRevision
    )

    def CreateWellKnownSid(WellKnownSidType: Any) -> Any:
        # return a SID for predefined aliases
        pSid = (ctypes.c_char * 1)()
        cbSid = wintypes.DWORD()
        try:
            advapi32.CreateWellKnownSid(WellKnownSidType, None, pSid, ctypes.byref(cbSid))
        except OSError as e:
            if e.winerror != ERROR_INSUFFICIENT_BUFFER:  # type:ignore[attr-defined]
                raise
            pSid = (ctypes.c_char * cbSid.value)()
            advapi32.CreateWellKnownSid(WellKnownSidType, None, pSid, ctypes.byref(cbSid))
        return pSid[:]

    def GetUserNameEx(NameFormat: Any) -> Any:
        # return the user or other security principal associated with
        # the calling thread
        nSize = ctypes.pointer(ctypes.c_ulong(0))
        try:
            secur32.GetUserNameExW(NameFormat, None, nSize)
        except OSError as e:
            if e.winerror != ERROR_MORE_DATA:  # type:ignore[attr-defined]
                raise
        if not nSize.contents.value:
            return None
        lpNameBuffer = ctypes.create_unicode_buffer(nSize.contents.value)
        secur32.GetUserNameExW(NameFormat, lpNameBuffer, nSize)
        return lpNameBuffer.value

    def LookupAccountName(lpSystemName: Any, lpAccountName: Any) -> Any:
        # return a security identifier (SID) for an account on a system
        # and the name of the domain on which the account was found
        cbSid = wintypes.DWORD(0)
        cchReferencedDomainName = wintypes.DWORD(0)
        peUse = wintypes.DWORD(0)
        try:
            advapi32.LookupAccountNameW(
                lpSystemName,
                lpAccountName,
                None,
                ctypes.byref(cbSid),
                None,
                ctypes.byref(cchReferencedDomainName),
                ctypes.byref(peUse),
            )
        except OSError as e:
            if e.winerror != ERROR_INSUFFICIENT_BUFFER:  # type:ignore[attr-defined]
                raise
        Sid = ctypes.create_unicode_buffer("", cbSid.value)
        pSid = ctypes.cast(ctypes.pointer(Sid), wintypes.LPVOID)
        lpReferencedDomainName = ctypes.create_unicode_buffer("", cchReferencedDomainName.value + 1)
        success = advapi32.LookupAccountNameW(
            lpSystemName,
            lpAccountName,
            pSid,
            ctypes.byref(cbSid),
            lpReferencedDomainName,
            ctypes.byref(cchReferencedDomainName),
            ctypes.byref(peUse),
        )
        if not success:
            raise ctypes.WinError()  # type:ignore[attr-defined]
        return pSid, lpReferencedDomainName.value, peUse.value

    def AddAccessAllowedAce(pAcl: Any, dwAceRevision: Any, AccessMask: Any, pSid: Any) -> Any:
        # add an access-allowed access control entry (ACE)
        # to an access control list (ACL)
        advapi32.AddAccessAllowedAce(pAcl, dwAceRevision, AccessMask, pSid)

    def GetFileSecurity(lpFileName: Any, RequestedInformation: Any) -> Any:
        # return information about the security of a file or directory
        nLength = wintypes.DWORD(0)
        try:
            advapi32.GetFileSecurityW(
                lpFileName,
                RequestedInformation,
                None,
                0,
                ctypes.byref(nLength),
            )
        except OSError as e:
            if e.winerror != ERROR_INSUFFICIENT_BUFFER:  # type:ignore[attr-defined]
                raise
        if not nLength.value:
            return None
        pSecurityDescriptor = (wintypes.BYTE * nLength.value)()
        advapi32.GetFileSecurityW(
            lpFileName,
            RequestedInformation,
            pSecurityDescriptor,
            nLength,
            ctypes.byref(nLength),
        )
        return pSecurityDescriptor

    def SetFileSecurity(
        lpFileName: Any, RequestedInformation: Any, pSecurityDescriptor: Any
    ) -> Any:
        # set the security of a file or directory object
        advapi32.SetFileSecurityW(lpFileName, RequestedInformation, pSecurityDescriptor)

    def SetSecurityDescriptorDacl(
        pSecurityDescriptor: Any, bDaclPresent: Any, pDacl: Any, bDaclDefaulted: Any
    ) -> Any:
        # set information in a discretionary access control list (DACL)
        advapi32.SetSecurityDescriptorDacl(pSecurityDescriptor, bDaclPresent, pDacl, bDaclDefaulted)

    def MakeAbsoluteSD(pSelfRelativeSecurityDescriptor: Any) -> Any:
        # return a security descriptor in absolute format
        # by using a security descriptor in self-relative format as a template
        pAbsoluteSecurityDescriptor = None
        lpdwAbsoluteSecurityDescriptorSize = wintypes.DWORD(0)
        pDacl = None
        lpdwDaclSize = wintypes.DWORD(0)
        pSacl = None
        lpdwSaclSize = wintypes.DWORD(0)
        pOwner = None
        lpdwOwnerSize = wintypes.DWORD(0)
        pPrimaryGroup = None
        lpdwPrimaryGroupSize = wintypes.DWORD(0)
        try:
            advapi32.MakeAbsoluteSD(
                pSelfRelativeSecurityDescriptor,
                pAbsoluteSecurityDescriptor,
                ctypes.byref(lpdwAbsoluteSecurityDescriptorSize),
                pDacl,
                ctypes.byref(lpdwDaclSize),
                pSacl,
                ctypes.byref(lpdwSaclSize),
                pOwner,
                ctypes.byref(lpdwOwnerSize),
                pPrimaryGroup,
                ctypes.byref(lpdwPrimaryGroupSize),
            )
        except OSError as e:
            if e.winerror != ERROR_INSUFFICIENT_BUFFER:  # type:ignore[attr-defined]
                raise
        pAbsoluteSecurityDescriptor = (wintypes.BYTE * lpdwAbsoluteSecurityDescriptorSize.value)()
        pDaclData = (wintypes.BYTE * lpdwDaclSize.value)()
        pDacl = ctypes.cast(pDaclData, PACL).contents
        pSaclData = (wintypes.BYTE * lpdwSaclSize.value)()
        pSacl = ctypes.cast(pSaclData, PACL).contents
        pOwnerData = (wintypes.BYTE * lpdwOwnerSize.value)()
        pOwner = ctypes.cast(pOwnerData, PSID)
        pPrimaryGroupData = (wintypes.BYTE * lpdwPrimaryGroupSize.value)()
        pPrimaryGroup = ctypes.cast(pPrimaryGroupData, PSID)
        advapi32.MakeAbsoluteSD(
            pSelfRelativeSecurityDescriptor,
            pAbsoluteSecurityDescriptor,
            ctypes.byref(lpdwAbsoluteSecurityDescriptorSize),
            pDacl,
            ctypes.byref(lpdwDaclSize),
            pSacl,
            ctypes.byref(lpdwSaclSize),
            pOwner,
            lpdwOwnerSize,
            pPrimaryGroup,
            ctypes.byref(lpdwPrimaryGroupSize),
        )
        return pAbsoluteSecurityDescriptor

    def MakeSelfRelativeSD(pAbsoluteSecurityDescriptor: Any) -> Any:
        # return a security descriptor in self-relative format
        # by using a security descriptor in absolute format as a template
        pSelfRelativeSecurityDescriptor = None
        lpdwBufferLength = wintypes.DWORD(0)
        try:
            advapi32.MakeSelfRelativeSD(
                pAbsoluteSecurityDescriptor,
                pSelfRelativeSecurityDescriptor,
                ctypes.byref(lpdwBufferLength),
            )
        except OSError as e:
            if e.winerror != ERROR_INSUFFICIENT_BUFFER:  # type:ignore[attr-defined]
                raise
        pSelfRelativeSecurityDescriptor = (wintypes.BYTE * lpdwBufferLength.value)()
        advapi32.MakeSelfRelativeSD(
            pAbsoluteSecurityDescriptor,
            pSelfRelativeSecurityDescriptor,
            ctypes.byref(lpdwBufferLength),
        )
        return pSelfRelativeSecurityDescriptor

    def NewAcl() -> Any:
        # return a new, initialized ACL (access control list) structure
        nAclLength = 32767  # TODO: calculate this: ctypes.sizeof(ACL) + ?
        acl_data = ctypes.create_string_buffer(nAclLength)
        pAcl = ctypes.cast(acl_data, PACL).contents
        advapi32.InitializeAcl(pAcl, nAclLength, ACL_REVISION)
        return pAcl

    SidAdmins = CreateWellKnownSid(WinBuiltinAdministratorsSid)
    SidUser = LookupAccountName("", GetUserNameEx(NameSamCompatible))[0]

    Acl = NewAcl()
    AddAccessAllowedAce(Acl, ACL_REVISION, FILE_ALL_ACCESS, SidAdmins)
    AddAccessAllowedAce(
        Acl,
        ACL_REVISION,
        FILE_GENERIC_READ | FILE_GENERIC_WRITE | DELETE,
        SidUser,
    )

    SelfRelativeSD = GetFileSecurity(fname, DACL_SECURITY_INFORMATION)
    AbsoluteSD = MakeAbsoluteSD(SelfRelativeSD)
    SetSecurityDescriptorDacl(AbsoluteSD, 1, Acl, 0)
    SelfRelativeSD = MakeSelfRelativeSD(AbsoluteSD)

    SetFileSecurity(fname, DACL_SECURITY_INFORMATION, SelfRelativeSD)


def get_file_mode(fname: str) -> int:
    """Retrieves the file mode corresponding to fname in a filesystem-tolerant manner.

    Parameters
    ----------

    fname : unicode
        The path to the file to get mode from

    """
    # Some filesystems (e.g., CIFS) auto-enable the execute bit on files.  As a result, we
    # should tolerate the execute bit on the file's owner when validating permissions - thus
    # the missing least significant bit on the third octal digit. In addition, we also tolerate
    # the sticky bit being set, so the lsb from the fourth octal digit is also removed.
    return (
        stat.S_IMODE(Path(fname).stat().st_mode) & 0o6677
    )  # Use 4 octal digits since S_IMODE does the same


allow_insecure_writes = os.getenv("JUPYTER_ALLOW_INSECURE_WRITES", "false").lower() in ("true", "1")


@contextmanager
def secure_write(fname: str, binary: bool = False) -> Iterator[Any]:
    """Opens a file in the most restricted pattern available for
    writing content. This limits the file mode to `0o0600` and yields
    the resulting opened filed handle.

    Parameters
    ----------

    fname : unicode
        The path to the file to write

    binary: boolean
        Indicates that the file is binary
    """
    mode = "wb" if binary else "w"
    encoding = None if binary else "utf-8"
    open_flag = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    try:
        Path(fname).unlink()
    except OSError:
        # Skip any issues with the file not existing
        pass

    if os.name == "nt":
        if allow_insecure_writes:
            # Mounted file systems can have a number of failure modes inside this block.
            # For windows machines in insecure mode we simply skip this to avoid failures :/
            issue_insecure_write_warning()
        else:
            # Python on windows does not respect the group and public bits for chmod, so we need
            # to take additional steps to secure the contents.
            # Touch file preemptively to avoid editing permissions in open files in Windows
            fd = os.open(fname, open_flag, 0o0600)
            os.close(fd)
            open_flag = os.O_WRONLY | os.O_TRUNC
            win32_restrict_file_to_user(fname)

    with os.fdopen(os.open(fname, open_flag, 0o0600), mode, encoding=encoding) as f:
        if os.name != "nt":
            # Enforce that the file got the requested permissions before writing
            file_mode = get_file_mode(fname)
            if file_mode != 0o0600:
                if allow_insecure_writes:
                    issue_insecure_write_warning()
                else:
                    msg = (
                        f"Permissions assignment failed for secure file: '{fname}'."
                        f" Got '{oct(file_mode)}' instead of '0o0600'."
                    )
                    raise RuntimeError(msg)
        yield f


def issue_insecure_write_warning() -> None:
    """Issue an insecure write warning."""

    def format_warning(msg: str, *args: Any, **kwargs: Any) -> str:  # noqa: ARG001
        return str(msg) + "\n"

    warnings.formatwarning = format_warning  # type:ignore[assignment]
    warnings.warn(
        "WARNING: Insecure writes have been enabled via environment variable "
        "'JUPYTER_ALLOW_INSECURE_WRITES'! If this is not intended, remove the "
        "variable or set its value to 'False'.",
        stacklevel=2,
    )