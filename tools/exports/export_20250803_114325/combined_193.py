
# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\operations_async_client.py ===
# Copyright 2020 Google LLC
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

"""An async client for the google.longrunning.operations meta-API.

.. _Google API Style Guide:
    https://cloud.google.com/apis/design/design_pattern
    s#long_running_operations
.. _google/longrunning/operations.proto:
    https://github.com/googleapis/googleapis/blob/master/google/longrunning
    /operations.proto
"""

import functools

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, page_iterator_async
from google.api_core import retry_async as retries
from google.api_core import timeout as timeouts
from google.longrunning import operations_pb2
from grpc import Compression


class OperationsAsyncClient:
    """Async client for interacting with long-running operations.

    Args:
        channel (aio.Channel): The gRPC AsyncIO channel associated with the
            service that implements the ``google.longrunning.operations``
            interface.
        client_config (dict):
            A dictionary of call options for each method. If not specified
            the default configuration is used.
    """

    def __init__(self, channel, client_config=None):
        # Create the gRPC client stub with gRPC AsyncIO channel.
        self.operations_stub = operations_pb2.OperationsStub(channel)

        default_retry = retries.AsyncRetry(
            initial=0.1,  # seconds
            maximum=60.0,  # seconds
            multiplier=1.3,
            predicate=retries.if_exception_type(
                core_exceptions.DeadlineExceeded,
                core_exceptions.ServiceUnavailable,
            ),
            timeout=600.0,  # seconds
        )
        default_timeout = timeouts.TimeToDeadlineTimeout(timeout=600.0)

        default_compression = Compression.NoCompression

        self._get_operation = gapic_v1.method_async.wrap_method(
            self.operations_stub.GetOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._list_operations = gapic_v1.method_async.wrap_method(
            self.operations_stub.ListOperations,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._cancel_operation = gapic_v1.method_async.wrap_method(
            self.operations_stub.CancelOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._delete_operation = gapic_v1.method_async.wrap_method(
            self.operations_stub.DeleteOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

    async def get_operation(
        self,
        name,
        retry=gapic_v1.method_async.DEFAULT,
        timeout=gapic_v1.method_async.DEFAULT,
        compression=gapic_v1.method_async.DEFAULT,
        metadata=None,
    ):
        """Gets the latest state of a long-running operation.

        Clients can use this method to poll the operation result at intervals
        as recommended by the API service.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> response = await api.get_operation(name)

        Args:
            name (str): The name of the operation resource.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]):
                Additional gRPC metadata.

        Returns:
            google.longrunning.operations_pb2.Operation: The state of the
                operation.

        Raises:
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        request = operations_pb2.GetOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        return await self._get_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

    async def list_operations(
        self,
        name,
        filter_,
        retry=gapic_v1.method_async.DEFAULT,
        timeout=gapic_v1.method_async.DEFAULT,
        compression=gapic_v1.method_async.DEFAULT,
        metadata=None,
    ):
        """
        Lists operations that match the specified filter in the request.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>>
            >>> # Iterate over all results
            >>> for operation in await api.list_operations(name):
            >>>   # process operation
            >>>   pass
            >>>
            >>> # Or iterate over results one page at a time
            >>> iter = await api.list_operations(name)
            >>> for page in iter.pages:
            >>>   for operation in page:
            >>>     # process operation
            >>>     pass

        Args:
            name (str): The name of the operation collection.
            filter_ (str): The standard list filter.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.

        Returns:
            google.api_core.page_iterator.Iterator: An iterator that yields
                :class:`google.longrunning.operations_pb2.Operation` instances.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        # Create the request object.
        request = operations_pb2.ListOperationsRequest(name=name, filter=filter_)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        # Create the method used to fetch pages
        method = functools.partial(
            self._list_operations,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

        iterator = page_iterator_async.AsyncGRPCIterator(
            client=None,
            method=method,
            request=request,
            items_field="operations",
            request_token_field="page_token",
            response_token_field="next_page_token",
        )

        return iterator

    async def cancel_operation(
        self,
        name,
        retry=gapic_v1.method_async.DEFAULT,
        timeout=gapic_v1.method_async.DEFAULT,
        compression=gapic_v1.method_async.DEFAULT,
        metadata=None,
    ):
        """Starts asynchronous cancellation on a long-running operation.

        The server makes a best effort to cancel the operation, but success is
        not guaranteed. Clients can use :meth:`get_operation` or service-
        specific methods to check whether the cancellation succeeded or whether
        the operation completed despite cancellation. On successful
        cancellation, the operation is not deleted; instead, it becomes an
        operation with an ``Operation.error`` value with a
        ``google.rpc.Status.code`` of ``1``, corresponding to
        ``Code.CANCELLED``.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> api.cancel_operation(name)

        Args:
            name (str): The name of the operation resource to be cancelled.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.
        """
        # Create the request object.
        request = operations_pb2.CancelOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        await self._cancel_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

    async def delete_operation(
        self,
        name,
        retry=gapic_v1.method_async.DEFAULT,
        timeout=gapic_v1.method_async.DEFAULT,
        compression=gapic_v1.method_async.DEFAULT,
        metadata=None,
    ):
        """Deletes a long-running operation.

        This method indicates that the client is no longer interested in the
        operation result. It does not cancel the operation.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> api.delete_operation(name)

        Args:
            name (str): The name of the operation resource to be deleted.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        # Create the request object.
        request = operations_pb2.DeleteOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        await self._delete_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_base_channel.py ===
# Copyright 2020 The gRPC Authors
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
"""Abstract base classes for Channel objects and Multicallable objects."""

import abc
from typing import Generic, Optional

import grpc

from . import _base_call
from ._typing import DeserializingFunction
from ._typing import MetadataType
from ._typing import RequestIterableType
from ._typing import RequestType
from ._typing import ResponseType
from ._typing import SerializingFunction


class UnaryUnaryMultiCallable(Generic[RequestType, ResponseType], abc.ABC):
    """Enables asynchronous invocation of a unary-call RPC."""

    @abc.abstractmethod
    def __call__(
        self,
        request: RequestType,
        *,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.UnaryUnaryCall[RequestType, ResponseType]:
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional duration of time in seconds to allow
            for the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          A UnaryUnaryCall object.

        Raises:
          RpcError: Indicates that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """


class UnaryStreamMultiCallable(Generic[RequestType, ResponseType], abc.ABC):
    """Enables asynchronous invocation of a server-streaming RPC."""

    @abc.abstractmethod
    def __call__(
        self,
        request: RequestType,
        *,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.UnaryStreamCall[RequestType, ResponseType]:
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional duration of time in seconds to allow
            for the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          A UnaryStreamCall object.

        Raises:
          RpcError: Indicates that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """


class StreamUnaryMultiCallable(abc.ABC):
    """Enables asynchronous invocation of a client-streaming RPC."""

    @abc.abstractmethod
    def __call__(
        self,
        request_iterator: Optional[RequestIterableType] = None,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.StreamUnaryCall:
        """Asynchronously invokes the underlying RPC.

        Args:
          request_iterator: An optional async iterable or iterable of request
            messages for the RPC.
          timeout: An optional duration of time in seconds to allow
            for the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          A StreamUnaryCall object.

        Raises:
          RpcError: Indicates that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """


class StreamStreamMultiCallable(abc.ABC):
    """Enables asynchronous invocation of a bidirectional-streaming RPC."""

    @abc.abstractmethod
    def __call__(
        self,
        request_iterator: Optional[RequestIterableType] = None,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.StreamStreamCall:
        """Asynchronously invokes the underlying RPC.

        Args:
          request_iterator: An optional async iterable or iterable of request
            messages for the RPC.
          timeout: An optional duration of time in seconds to allow
            for the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          A StreamStreamCall object.

        Raises:
          RpcError: Indicates that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """


class Channel(abc.ABC):
    """Enables asynchronous RPC invocation as a client.

    Channel objects implement the Asynchronous Context Manager (aka. async
    with) type, although they are not supported to be entered and exited
    multiple times.
    """

    @abc.abstractmethod
    async def __aenter__(self):
        """Starts an asynchronous context manager.

        Returns:
          Channel the channel that was instantiated.
        """

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Finishes the asynchronous context manager by closing the channel.

        Still active RPCs will be cancelled.
        """

    @abc.abstractmethod
    async def close(self, grace: Optional[float] = None):
        """Closes this Channel and releases all resources held by it.

        This method immediately stops the channel from executing new RPCs in
        all cases.

        If a grace period is specified, this method waits until all active
        RPCs are finished or until the grace period is reached. RPCs that haven't
        been terminated within the grace period are aborted.
        If a grace period is not specified (by passing None for grace),
        all existing RPCs are cancelled immediately.

        This method is idempotent.
        """

    @abc.abstractmethod
    def get_state(
        self, try_to_connect: bool = False
    ) -> grpc.ChannelConnectivity:
        """Checks the connectivity state of a channel.

        This is an EXPERIMENTAL API.

        If the channel reaches a stable connectivity state, it is guaranteed
        that the return value of this function will eventually converge to that
        state.

        Args:
          try_to_connect: a bool indicate whether the Channel should try to
            connect to peer or not.

        Returns: A ChannelConnectivity object.
        """

    @abc.abstractmethod
    async def wait_for_state_change(
        self,
        last_observed_state: grpc.ChannelConnectivity,
    ) -> None:
        """Waits for a change in connectivity state.

        This is an EXPERIMENTAL API.

        The function blocks until there is a change in the channel connectivity
        state from the "last_observed_state". If the state is already
        different, this function will return immediately.

        There is an inherent race between the invocation of
        "Channel.wait_for_state_change" and "Channel.get_state". The state can
        change arbitrary many times during the race, so there is no way to
        observe every state transition.

        If there is a need to put a timeout for this function, please refer to
        "asyncio.wait_for".

        Args:
          last_observed_state: A grpc.ChannelConnectivity object representing
            the last known state.
        """

    @abc.abstractmethod
    async def channel_ready(self) -> None:
        """Creates a coroutine that blocks until the Channel is READY."""

    @abc.abstractmethod
    def unary_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> UnaryUnaryMultiCallable:
        """Creates a UnaryUnaryMultiCallable for a unary-unary method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. Optional: A bool representing
            whether the method is registered.

        Returns:
          A UnaryUnaryMultiCallable value for the named unary-unary method.
        """

    @abc.abstractmethod
    def unary_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> UnaryStreamMultiCallable:
        """Creates a UnaryStreamMultiCallable for a unary-stream method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. Optional: A bool representing
            whether the method is registered.

        Returns:
          A UnaryStreamMultiCallable value for the named unary-stream method.
        """

    @abc.abstractmethod
    def stream_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> StreamUnaryMultiCallable:
        """Creates a StreamUnaryMultiCallable for a stream-unary method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. Optional: A bool representing
            whether the method is registered.

        Returns:
          A StreamUnaryMultiCallable value for the named stream-unary method.
        """

    @abc.abstractmethod
    def stream_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> StreamStreamMultiCallable:
        """Creates a StreamStreamMultiCallable for a stream-stream method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. Optional: A bool representing
            whether the method is registered.

        Returns:
          A StreamStreamMultiCallable value for the named stream-stream method.
        """

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\llm_provider_handlers\vertex_passthrough_logging_handler.py ===
import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import httpx

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
    ModelResponseIterator as VertexModelResponseIterator,
)
from litellm.proxy._types import PassThroughEndpointLoggingTypedDict
from litellm.types.utils import (
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    TextCompletionResponse,
)

if TYPE_CHECKING:
    from ..success_handler import PassThroughEndpointLogging
    from ..types import EndpointType
else:
    PassThroughEndpointLogging = Any
    EndpointType = Any


class VertexPassthroughLoggingHandler:
    @staticmethod
    def vertex_passthrough_handler(
        httpx_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ) -> PassThroughEndpointLoggingTypedDict:
        if "generateContent" in url_route:
            model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)

            instance_of_vertex_llm = litellm.VertexGeminiConfig()
            litellm_model_response: ModelResponse = (
                instance_of_vertex_llm.transform_response(
                    model=model,
                    messages=[
                        {"role": "user", "content": "no-message-pass-through-endpoint"}
                    ],
                    raw_response=httpx_response,
                    model_response=litellm.ModelResponse(),
                    logging_obj=logging_obj,
                    optional_params={},
                    litellm_params={},
                    api_key="",
                    request_data={},
                    encoding=litellm.encoding,
                )
            )
            kwargs = VertexPassthroughLoggingHandler._create_vertex_response_logging_payload_for_generate_content(
                litellm_model_response=litellm_model_response,
                model=model,
                kwargs=kwargs,
                start_time=start_time,
                end_time=end_time,
                logging_obj=logging_obj,
                custom_llm_provider=VertexPassthroughLoggingHandler._get_custom_llm_provider_from_url(
                    url_route
                ),
            )

            return {
                "result": litellm_model_response,
                "kwargs": kwargs,
            }

        elif "predict" in url_route:
            from litellm.llms.vertex_ai.image_generation.image_generation_handler import (
                VertexImageGeneration,
            )
            from litellm.types.utils import PassthroughCallTypes

            vertex_image_generation_class = VertexImageGeneration()

            model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)

            _json_response = httpx_response.json()

            litellm_prediction_response: Union[
                ModelResponse, EmbeddingResponse, ImageResponse
            ] = ModelResponse()
            if vertex_image_generation_class.is_image_generation_response(
                _json_response
            ):
                litellm_prediction_response = (
                    vertex_image_generation_class.process_image_generation_response(
                        _json_response,
                        model_response=litellm.ImageResponse(),
                        model=model,
                    )
                )

                logging_obj.call_type = (
                    PassthroughCallTypes.passthrough_image_generation.value
                )
            else:
                litellm_prediction_response = litellm.vertexAITextEmbeddingConfig.transform_vertex_response_to_openai(
                    response=_json_response,
                    model=model,
                    model_response=litellm.EmbeddingResponse(),
                )
            if isinstance(litellm_prediction_response, litellm.EmbeddingResponse):
                litellm_prediction_response.model = model

            logging_obj.model = model
            logging_obj.model_call_details["model"] = logging_obj.model

            return {
                "result": litellm_prediction_response,
                "kwargs": kwargs,
            }
        elif "rawPredict" in url_route or "streamRawPredict" in url_route:
            from litellm.llms.vertex_ai.vertex_ai_partner_models import (
                get_vertex_ai_partner_model_config,
            )

            model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)
            vertex_publisher_or_api_spec = VertexPassthroughLoggingHandler._get_vertex_publisher_or_api_spec_from_url(
                url_route
            )

            _json_response = httpx_response.json()

            litellm_prediction_response = ModelResponse()

            if vertex_publisher_or_api_spec is not None:
                vertex_ai_partner_model_config = get_vertex_ai_partner_model_config(
                    model=model,
                    vertex_publisher_or_api_spec=vertex_publisher_or_api_spec,
                )
                litellm_prediction_response = (
                    vertex_ai_partner_model_config.transform_response(
                        model=model,
                        raw_response=httpx_response,
                        model_response=litellm_prediction_response,
                        logging_obj=logging_obj,
                        request_data={},
                        encoding=litellm.encoding,
                        optional_params={},
                        litellm_params={},
                        api_key="",
                        messages=[
                            {
                                "role": "user",
                                "content": "no-message-pass-through-endpoint",
                            }
                        ],
                    )
                )

            kwargs = VertexPassthroughLoggingHandler._create_vertex_response_logging_payload_for_generate_content(
                litellm_model_response=litellm_prediction_response,
                model="vertex_ai/" + model,
                kwargs=kwargs,
                start_time=start_time,
                end_time=end_time,
                logging_obj=logging_obj,
                custom_llm_provider="vertex_ai",
            )

            return {
                "result": litellm_prediction_response,
                "kwargs": kwargs,
            }
        else:
            return {
                "result": None,
                "kwargs": kwargs,
            }

    @staticmethod
    def _handle_logging_vertex_collected_chunks(
        litellm_logging_obj: LiteLLMLoggingObj,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
        request_body: dict,
        endpoint_type: EndpointType,
        start_time: datetime,
        all_chunks: List[str],
        end_time: datetime,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Takes raw chunks from Vertex passthrough endpoint and logs them in litellm callbacks

        - Builds complete response from chunks
        - Creates standard logging object
        - Logs in litellm callbacks
        """
        kwargs: Dict[str, Any] = {}
        model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)
        complete_streaming_response = (
            VertexPassthroughLoggingHandler._build_complete_streaming_response(
                all_chunks=all_chunks,
                litellm_logging_obj=litellm_logging_obj,
                model=model,
                url_route=url_route,
            )
        )

        if complete_streaming_response is None:
            verbose_proxy_logger.error(
                "Unable to build complete streaming response for Vertex passthrough endpoint, not logging..."
            )
            return {
                "result": None,
                "kwargs": kwargs,
            }

        kwargs = VertexPassthroughLoggingHandler._create_vertex_response_logging_payload_for_generate_content(
            litellm_model_response=complete_streaming_response,
            model=model,
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
            logging_obj=litellm_logging_obj,
            custom_llm_provider=VertexPassthroughLoggingHandler._get_custom_llm_provider_from_url(
                url_route
            ),
        )

        return {
            "result": complete_streaming_response,
            "kwargs": kwargs,
        }

    @staticmethod
    def _build_complete_streaming_response(
        all_chunks: List[str],
        litellm_logging_obj: LiteLLMLoggingObj,
        model: str,
        url_route: str,
    ) -> Optional[Union[ModelResponse, TextCompletionResponse]]:
        parsed_chunks = []
        if "generateContent" in url_route or "streamGenerateContent" in url_route:
            vertex_iterator: Any = VertexModelResponseIterator(
                streaming_response=None,
                sync_stream=False,
                logging_obj=litellm_logging_obj,
            )
            chunk_parsing_logic: Any = vertex_iterator._common_chunk_parsing_logic
            parsed_chunks = [chunk_parsing_logic(chunk) for chunk in all_chunks]
        elif "rawPredict" in url_route or "streamRawPredict" in url_route:
            from litellm.llms.anthropic.chat.handler import ModelResponseIterator
            from litellm.llms.base_llm.base_model_iterator import (
                BaseModelResponseIterator,
            )

            vertex_iterator = ModelResponseIterator(
                streaming_response=None,
                sync_stream=False,
            )
            chunk_parsing_logic = vertex_iterator.chunk_parser
            for chunk in all_chunks:
                dict_chunk = BaseModelResponseIterator._string_to_dict_parser(chunk)
                if dict_chunk is None:
                    continue
                parsed_chunks.append(chunk_parsing_logic(dict_chunk))
        else:
            return None
        if len(parsed_chunks) == 0:
            return None
        litellm_custom_stream_wrapper = litellm.CustomStreamWrapper(
            completion_stream=vertex_iterator,
            model=model,
            logging_obj=litellm_logging_obj,
            custom_llm_provider="vertex_ai",
        )
        all_openai_chunks = []
        for parsed_chunk in parsed_chunks:
            try:
                litellm_chunk = litellm_custom_stream_wrapper.chunk_creator(
                    chunk=parsed_chunk
                )
            except Exception as e:
                verbose_proxy_logger.error(
                    "Error creating litellm chunk from vertex passthrough endpoint: %s",
                    str(e),
                )
                continue
            if litellm_chunk is not None:
                all_openai_chunks.append(litellm_chunk)

        complete_streaming_response = litellm.stream_chunk_builder(
            chunks=all_openai_chunks
        )

        return complete_streaming_response

    @staticmethod
    def extract_model_from_url(url: str) -> str:
        pattern = r"/models/([^:]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return "unknown"

    @staticmethod
    def _get_vertex_publisher_or_api_spec_from_url(url: str) -> Optional[str]:
        # Check for specific Vertex AI partner publishers
        if "/publishers/mistralai/" in url:
            return "mistralai"
        elif "/publishers/anthropic/" in url:
            return "anthropic"
        elif "/publishers/ai21/" in url:
            return "ai21"
        elif "/endpoints/openapi/" in url:
            return "openapi"
        return None

    @staticmethod
    def _get_custom_llm_provider_from_url(url: str) -> str:
        parsed_url = urlparse(url)
        if parsed_url.hostname and parsed_url.hostname.endswith(
            "generativelanguage.googleapis.com"
        ):
            return litellm.LlmProviders.GEMINI.value
        return litellm.LlmProviders.VERTEX_AI.value

    @staticmethod
    def _create_vertex_response_logging_payload_for_generate_content(
        litellm_model_response: Union[ModelResponse, TextCompletionResponse],
        model: str,
        kwargs: dict,
        start_time: datetime,
        end_time: datetime,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: str,
    ):
        """
        Create the standard logging object for Vertex passthrough generateContent (streaming and non-streaming)

        """

        response_cost = litellm.completion_cost(
            completion_response=litellm_model_response,
            model=model,
            custom_llm_provider="vertex_ai",
        )

        kwargs["response_cost"] = response_cost
        kwargs["model"] = model

        # pretty print standard logging object
        verbose_proxy_logger.debug("kwargs= %s", json.dumps(kwargs, indent=4))

        # set litellm_call_id to logging response object
        litellm_model_response.id = logging_obj.litellm_call_id
        logging_obj.model = litellm_model_response.model or model
        logging_obj.model_call_details["model"] = logging_obj.model
        logging_obj.model_call_details["custom_llm_provider"] = custom_llm_provider
        return kwargs

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\crystal.py ===
"""
    pygments.lexers.crystal
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Crystal.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, include, bygroups, default, \
    words, line_re
from pygments.token import Comment, Operator, Keyword, Name, String, Number, \
    Punctuation, Error, Whitespace

__all__ = ['CrystalLexer']


CRYSTAL_OPERATORS = [
    '!=', '!~', '!', '%', '&&', '&', '**', '*', '+', '-', '/', '<=>', '<<', '<=', '<',
    '===', '==', '=~', '=', '>=', '>>', '>', '[]=', '[]?', '[]', '^', '||', '|', '~'
]


class CrystalLexer(ExtendedRegexLexer):
    """
    For Crystal source code.
    """

    name = 'Crystal'
    url = 'https://crystal-lang.org'
    aliases = ['cr', 'crystal']
    filenames = ['*.cr']
    mimetypes = ['text/x-crystal']
    version_added = '2.2'

    flags = re.DOTALL | re.MULTILINE

    def heredoc_callback(self, match, ctx):
        # okay, this is the hardest part of parsing Crystal...
        # match: 1 = <<-?, 2 = quote? 3 = name 4 = quote? 5 = rest of line

        start = match.start(1)
        yield start, Operator, match.group(1)        # <<-?
        yield match.start(2), String.Heredoc, match.group(2)    # quote ", ', `
        yield match.start(3), String.Delimiter, match.group(3)  # heredoc name
        yield match.start(4), String.Heredoc, match.group(4)    # quote again

        heredocstack = ctx.__dict__.setdefault('heredocstack', [])
        outermost = not bool(heredocstack)
        heredocstack.append((match.group(1) == '<<-', match.group(3)))

        ctx.pos = match.start(5)
        ctx.end = match.end(5)
        # this may find other heredocs, so limit the recursion depth
        if len(heredocstack) < 100:
            yield from self.get_tokens_unprocessed(context=ctx)
        else:
            yield ctx.pos, String.Heredoc, match.group(5)
        ctx.pos = match.end()

        if outermost:
            # this is the outer heredoc again, now we can process them all
            for tolerant, hdname in heredocstack:
                lines = []
                for match in line_re.finditer(ctx.text, ctx.pos):
                    if tolerant:
                        check = match.group().strip()
                    else:
                        check = match.group().rstrip()
                    if check == hdname:
                        for amatch in lines:
                            yield amatch.start(), String.Heredoc, amatch.group()
                        yield match.start(), String.Delimiter, match.group()
                        ctx.pos = match.end()
                        break
                    else:
                        lines.append(match)
                else:
                    # end of heredoc not found -- error!
                    for amatch in lines:
                        yield amatch.start(), Error, amatch.group()
            ctx.end = len(ctx.text)
            del heredocstack[:]

    def gen_crystalstrings_rules():
        states = {}
        states['strings'] = [
            (r'\:\w+[!?]?', String.Symbol),
            (words(CRYSTAL_OPERATORS, prefix=r'\:'), String.Symbol),
            (r":'(\\\\|\\[^\\]|[^'\\])*'", String.Symbol),
            # This allows arbitrary text after '\ for simplicity
            (r"'(\\\\|\\'|[^']|\\[^'\\]+)'", String.Char),
            (r':"', String.Symbol, 'simple-sym'),
            # Crystal doesn't have "symbol:"s but this simplifies function args
            (r'([a-zA-Z_]\w*)(:)(?!:)', bygroups(String.Symbol, Punctuation)),
            (r'"', String.Double, 'simple-string'),
            (r'(?<!\.)`', String.Backtick, 'simple-backtick'),
        ]

        # double-quoted string and symbol
        for name, ttype, end in ('string', String.Double, '"'), \
                                ('sym', String.Symbol, '"'), \
                                ('backtick', String.Backtick, '`'):
            states['simple-'+name] = [
                include('string-escaped' if name == 'sym' else 'string-intp-escaped'),
                (rf'[^\\{end}#]+', ttype),
                (r'[\\#]', ttype),
                (end, ttype, '#pop'),
            ]

        # https://crystal-lang.org/docs/syntax_and_semantics/literals/string.html#percent-string-literals
        for lbrace, rbrace, bracecc, name in \
                ('\\{', '\\}', '{}', 'cb'), \
                ('\\[', '\\]', '\\[\\]', 'sb'), \
                ('\\(', '\\)', '()', 'pa'), \
                ('<', '>', '<>', 'ab'), \
                ('\\|', '\\|', '\\|', 'pi'):
            states[name+'-intp-string'] = [
                (r'\\' + lbrace, String.Other),
            ] + (lbrace != rbrace) * [
                (lbrace, String.Other, '#push'),
            ] + [
                (rbrace, String.Other, '#pop'),
                include('string-intp-escaped'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            states['strings'].append((r'%Q?' + lbrace, String.Other,
                                      name+'-intp-string'))
            states[name+'-string'] = [
                (r'\\[\\' + bracecc + ']', String.Other),
            ] + (lbrace != rbrace) * [
                (lbrace, String.Other, '#push'),
            ] + [
                (rbrace, String.Other, '#pop'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            # https://crystal-lang.org/docs/syntax_and_semantics/literals/array.html#percent-array-literals
            states['strings'].append((r'%[qwi]' + lbrace, String.Other,
                                      name+'-string'))
            states[name+'-regex'] = [
                (r'\\[\\' + bracecc + ']', String.Regex),
            ] + (lbrace != rbrace) * [
                (lbrace, String.Regex, '#push'),
            ] + [
                (rbrace + '[imsx]*', String.Regex, '#pop'),
                include('string-intp'),
                (r'[\\#' + bracecc + ']', String.Regex),
                (r'[^\\#' + bracecc + ']+', String.Regex),
            ]
            states['strings'].append((r'%r' + lbrace, String.Regex,
                                      name+'-regex'))

        return states

    tokens = {
        'root': [
            (r'#.*?$', Comment.Single),
            # keywords
            (words('''
                abstract asm begin break case do else elsif end ensure extend if in
                include next of private protected require rescue return select self super
                then unless until when while with yield
            '''.split(), suffix=r'\b'), Keyword),
            (words('''
                previous_def forall out uninitialized __DIR__ __FILE__ __LINE__
                __END_LINE__
            '''.split(), prefix=r'(?<!\.)', suffix=r'\b'), Keyword.Pseudo),
            # https://crystal-lang.org/docs/syntax_and_semantics/is_a.html
            (r'\.(is_a\?|nil\?|responds_to\?|as\?|as\b)', Keyword.Pseudo),
            (words(['true', 'false', 'nil'], suffix=r'\b'), Keyword.Constant),
            # start of function, class and module names
            (r'(module|lib)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(def|fun|macro)(\s+)((?:[a-zA-Z_]\w*::)*)',
             bygroups(Keyword, Whitespace, Name.Namespace), 'funcname'),
            (r'def(?=[*%&^`~+-/\[<>=])', Keyword, 'funcname'),
            (r'(annotation|class|struct|union|type|alias|enum)(\s+)((?:[a-zA-Z_]\w*::)*)',
             bygroups(Keyword, Whitespace, Name.Namespace), 'classname'),
            # https://crystal-lang.org/api/toplevel.html
            (words('''
                instance_sizeof offsetof pointerof sizeof typeof
            '''.split(), prefix=r'(?<!\.)', suffix=r'\b'), Keyword.Pseudo),
            # macros
            (r'(?<!\.)(debugger\b|p!|pp!|record\b|spawn\b)', Name.Builtin.Pseudo),
            # builtins
            (words('''
                abort at_exit caller exit gets loop main p pp print printf puts
                raise rand read_line sleep spawn sprintf system
            '''.split(), prefix=r'(?<!\.)', suffix=r'\b'), Name.Builtin),
            # https://crystal-lang.org/api/Object.html#macro-summary
            (r'(?<!\.)(((class_)?((getter|property)\b[!?]?|setter\b))|'
             r'(def_(clone|equals|equals_and_hash|hash)|delegate|forward_missing_to)\b)',
             Name.Builtin.Pseudo),
            # normal heredocs
            (r'(?<!\w)(<<-?)(["`\']?)([a-zA-Z_]\w*)(\2)(.*?\n)',
             heredoc_callback),
            # empty string heredocs
            (r'(<<-?)("|\')()(\2)(.*?\n)', heredoc_callback),
            (r'__END__', Comment.Preproc, 'end-part'),
            # multiline regex (after keywords or assignments)
            (r'(?:^|(?<=[=<>~!:])|'
             r'(?<=(?:\s|;)when\s)|'
             r'(?<=(?:\s|;)or\s)|'
             r'(?<=(?:\s|;)and\s)|'
             r'(?<=\.index\s)|'
             r'(?<=\.scan\s)|'
             r'(?<=\.sub\s)|'
             r'(?<=\.sub!\s)|'
             r'(?<=\.gsub\s)|'
             r'(?<=\.gsub!\s)|'
             r'(?<=\.match\s)|'
             r'(?<=(?:\s|;)if\s)|'
             r'(?<=(?:\s|;)elsif\s)|'
             r'(?<=^when\s)|'
             r'(?<=^index\s)|'
             r'(?<=^scan\s)|'
             r'(?<=^sub\s)|'
             r'(?<=^gsub\s)|'
             r'(?<=^sub!\s)|'
             r'(?<=^gsub!\s)|'
             r'(?<=^match\s)|'
             r'(?<=^if\s)|'
             r'(?<=^elsif\s)'
             r')(\s*)(/)', bygroups(Whitespace, String.Regex), 'multiline-regex'),
            # multiline regex (in method calls or subscripts)
            (r'(?<=\(|,|\[)/', String.Regex, 'multiline-regex'),
            # multiline regex (this time the funny no whitespace rule)
            (r'(\s+)(/)(?![\s=])', bygroups(Whitespace, String.Regex),
             'multiline-regex'),
            # lex numbers and ignore following regular expressions which
            # are division operators in fact (grrrr. i hate that. any
            # better ideas?)
            # since pygments 0.7 we also eat a "?" operator after numbers
            # so that the char operator does not work. Chars are not allowed
            # there so that you can use the ternary operator.
            # stupid example:
            #   x>=0?n[x]:""
            (r'(0o[0-7]+(?:_[0-7]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Oct, Whitespace, Operator)),
            (r'(0x[0-9A-Fa-f]+(?:_[0-9A-Fa-f]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Hex, Whitespace, Operator)),
            (r'(0b[01]+(?:_[01]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Bin, Whitespace, Operator)),
            # 3 separate expressions for floats because any of the 3 optional
            # parts makes it a float
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)(?:e[+-]?[0-9]+)?'
             r'(?:_?f[0-9]+)?)(\s*)([/?])?',
             bygroups(Number.Float, Whitespace, Operator)),
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)?(?:e[+-]?[0-9]+)'
             r'(?:_?f[0-9]+)?)(\s*)([/?])?',
             bygroups(Number.Float, Whitespace, Operator)),
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)?(?:e[+-]?[0-9]+)?'
             r'(?:_?f[0-9]+))(\s*)([/?])?',
             bygroups(Number.Float, Whitespace, Operator)),
            (r'(0\b|[1-9][\d]*(?:_\d+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Integer, Whitespace, Operator)),
            # Names
            (r'@@[a-zA-Z_]\w*', Name.Variable.Class),
            (r'@[a-zA-Z_]\w*', Name.Variable.Instance),
            (r'\$\w+', Name.Variable.Global),
            (r'\$[!@&`\'+~=/\\,;.<>_*$?:"^-]', Name.Variable.Global),
            (r'\$-[0adFiIlpvw]', Name.Variable.Global),
            (r'::', Operator),
            include('strings'),
            # https://crystal-lang.org/reference/syntax_and_semantics/literals/char.html
            (r'\?(\\[MC]-)*'  # modifiers
             r'(\\([\\abefnrtv#"\']|[0-7]{1,3}|x[a-fA-F0-9]{2}|u[a-fA-F0-9]{4}|u\{[a-fA-F0-9 ]+\})|\S)'
             r'(?!\w)',
             String.Char),
            (r'[A-Z][A-Z_]+\b(?!::|\.)', Name.Constant),
            # macro expansion
            (r'\{%', String.Interpol, 'in-macro-control'),
            (r'\{\{', String.Interpol, 'in-macro-expr'),
            # annotations
            (r'(@\[)(\s*)([A-Z]\w*(::[A-Z]\w*)*)',
             bygroups(Operator, Whitespace, Name.Decorator), 'in-annot'),
            # this is needed because Crystal attributes can look
            # like keywords (class) or like this: ` ?!?
            (words(CRYSTAL_OPERATORS, prefix=r'(\.|::)'),
             bygroups(Operator, Name.Operator)),
            (r'(\.|::)([a-zA-Z_]\w*[!?]?|[*%&^`~+\-/\[<>=])',
             bygroups(Operator, Name)),
            # Names can end with [!?] unless it's "!="
            (r'[a-zA-Z_]\w*(?:[!?](?!=))?', Name),
            (r'(\[|\]\??|\*\*|<=>?|>=|<<?|>>?|=~|===|'
             r'!~|&&?|\|\||\.{1,3})', Operator),
            (r'[-+/*%=<>&!^|~]=?', Operator),
            (r'[(){};,/?:\\]', Punctuation),
            (r'\s+', Whitespace)
        ],
        'funcname': [
            (r'(?:([a-zA-Z_]\w*)(\.))?'
             r'([a-zA-Z_]\w*[!?]?|\*\*?|[-+]@?|'
             r'[/%&|^`~]|\[\]=?|<<|>>|<=?>|>=?|===?)',
             bygroups(Name.Class, Operator, Name.Function), '#pop'),
            default('#pop')
        ],
        'classname': [
            (r'[A-Z_]\w*', Name.Class),
            (r'(\()(\s*)([A-Z_]\w*)(\s*)(\))',
             bygroups(Punctuation, Whitespace, Name.Class, Whitespace, Punctuation)),
            default('#pop')
        ],
        'in-intp': [
            (r'\{', String.Interpol, '#push'),
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
        'string-intp': [
            (r'#\{', String.Interpol, 'in-intp'),
        ],
        'string-escaped': [
            # https://crystal-lang.org/reference/syntax_and_semantics/literals/string.html
            (r'\\([\\abefnrtv#"\']|[0-7]{1,3}|x[a-fA-F0-9]{2}|u[a-fA-F0-9]{4}|u\{[a-fA-F0-9 ]+\})',
             String.Escape)
        ],
        'string-intp-escaped': [
            include('string-intp'),
            include('string-escaped'),
        ],
        'interpolated-regex': [
            include('string-intp'),
            (r'[\\#]', String.Regex),
            (r'[^\\#]+', String.Regex),
        ],
        'interpolated-string': [
            include('string-intp'),
            (r'[\\#]', String.Other),
            (r'[^\\#]+', String.Other),
        ],
        'multiline-regex': [
            include('string-intp'),
            (r'\\\\', String.Regex),
            (r'\\/', String.Regex),
            (r'[\\#]', String.Regex),
            (r'[^\\/#]+', String.Regex),
            (r'/[imsx]*', String.Regex, '#pop'),
        ],
        'end-part': [
            (r'.+', Comment.Preproc, '#pop')
        ],
        'in-macro-control': [
            (r'\{%', String.Interpol, '#push'),
            (r'%\}', String.Interpol, '#pop'),
            (r'(for|verbatim)\b', Keyword),
            include('root'),
        ],
        'in-macro-expr': [
            (r'\{\{', String.Interpol, '#push'),
            (r'\}\}', String.Interpol, '#pop'),
            include('root'),
        ],
        'in-annot': [
            (r'\[', Operator, '#push'),
            (r'\]', Operator, '#pop'),
            include('root'),
        ],
    }
    tokens.update(gen_crystalstrings_rules())

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\pydevd_modify_bytecode.py ===
from collections import namedtuple
import dis
from functools import partial
import itertools
import os.path
import sys

from _pydevd_frame_eval.vendored import bytecode
from _pydevd_frame_eval.vendored.bytecode.instr import Instr, Label
from _pydev_bundle import pydev_log
from _pydevd_frame_eval.pydevd_frame_tracing import _pydev_stop_at_break, _pydev_needs_stop_at_break

DEBUG = False


class DebugHelper(object):
    def __init__(self):
        self._debug_dir = os.path.join(os.path.dirname(__file__), "debug_info")
        try:
            os.makedirs(self._debug_dir)
        except:
            pass
        self._next = partial(next, itertools.count(0))

    def _get_filename(self, op_number=None, prefix=""):
        if op_number is None:
            op_number = self._next()
            name = "%03d_before.txt" % op_number
        else:
            name = "%03d_change.txt" % op_number

        filename = os.path.join(self._debug_dir, prefix + name)
        return filename, op_number

    def write_bytecode(self, b, op_number=None, prefix=""):
        filename, op_number = self._get_filename(op_number, prefix)
        with open(filename, "w") as stream:
            bytecode.dump_bytecode(b, stream=stream, lineno=True)
        return op_number

    def write_dis(self, code_to_modify, op_number=None, prefix=""):
        filename, op_number = self._get_filename(op_number, prefix)
        with open(filename, "w") as stream:
            stream.write("-------- ")
            stream.write("-------- ")
            stream.write("id(code_to_modify): %s" % id(code_to_modify))
            stream.write("\n\n")
            dis.dis(code_to_modify, file=stream)
        return op_number


_CodeLineInfo = namedtuple("_CodeLineInfo", "line_to_offset, first_line, last_line")


# Note: this method has a version in cython too (that one is usually used, this is just for tests).
def _get_code_line_info(code_obj):
    line_to_offset = {}
    first_line = None
    last_line = None

    for offset, line in dis.findlinestarts(code_obj):
        if line is not None:
            line_to_offset[line] = offset

    if line_to_offset:
        first_line = min(line_to_offset)
        last_line = max(line_to_offset)
    return _CodeLineInfo(line_to_offset, first_line, last_line)


if DEBUG:
    debug_helper = DebugHelper()


def get_instructions_to_add(stop_at_line, _pydev_stop_at_break=_pydev_stop_at_break, _pydev_needs_stop_at_break=_pydev_needs_stop_at_break):
    """
    This is the bytecode for something as:

        if _pydev_needs_stop_at_break():
            _pydev_stop_at_break()

    but with some special handling for lines.
    """
    # Good reference to how things work regarding line numbers and jumps:
    # https://github.com/python/cpython/blob/3.6/Objects/lnotab_notes.txt

    # Usually use a stop line -1, but if that'd be 0, using line +1 is ok too.
    spurious_line = stop_at_line - 1
    if spurious_line <= 0:
        spurious_line = stop_at_line + 1

    label = Label()
    return [
        # -- if _pydev_needs_stop_at_break():
        Instr("LOAD_CONST", _pydev_needs_stop_at_break, lineno=stop_at_line),
        Instr("LOAD_CONST", stop_at_line, lineno=stop_at_line),
        Instr("CALL_FUNCTION", 1, lineno=stop_at_line),
        Instr("POP_JUMP_IF_FALSE", label, lineno=stop_at_line),
        #     -- _pydev_stop_at_break()
        #
        # Note that this has line numbers -1 so that when the NOP just below
        # is executed we have a spurious line event.
        Instr("LOAD_CONST", _pydev_stop_at_break, lineno=spurious_line),
        Instr("LOAD_CONST", stop_at_line, lineno=spurious_line),
        Instr("CALL_FUNCTION", 1, lineno=spurious_line),
        Instr("POP_TOP", lineno=spurious_line),
        # Reason for the NOP: Python will give us a 'line' trace event whenever we forward jump to
        # the first instruction of a line, so, in the case where we haven't added a programmatic
        # breakpoint (either because we didn't hit a breakpoint anymore or because it was already
        # tracing), we don't want the spurious line event due to the line change, so, we make a jump
        # to the instruction right after the NOP so that the spurious line event is NOT generated in
        # this case (otherwise we'd have a line event even if the line didn't change).
        Instr("NOP", lineno=stop_at_line),
        label,
    ]


class _Node(object):
    def __init__(self, data):
        self.prev = None
        self.next = None
        self.data = data

    def append(self, data):
        node = _Node(data)

        curr_next = self.next

        node.next = self.next
        node.prev = self
        self.next = node

        if curr_next is not None:
            curr_next.prev = node

        return node

    def prepend(self, data):
        node = _Node(data)

        curr_prev = self.prev

        node.prev = self.prev
        node.next = self
        self.prev = node

        if curr_prev is not None:
            curr_prev.next = node

        return node


class _HelperBytecodeList(object):
    """
    A helper double-linked list to make the manipulation a bit easier (so that we don't need
    to keep track of indices that change) and performant (because adding multiple items to
    the middle of a regular list isn't ideal).
    """

    def __init__(self, lst=None):
        self._head = None
        self._tail = None
        if lst:
            node = self
            for item in lst:
                node = node.append(item)

    def append(self, data):
        if self._tail is None:
            node = _Node(data)
            self._head = self._tail = node
            return node
        else:
            node = self._tail = self.tail.append(data)
            return node

    @property
    def head(self):
        node = self._head
        # Manipulating the node directly may make it unsynchronized.
        while node.prev:
            self._head = node = node.prev
        return node

    @property
    def tail(self):
        node = self._tail
        # Manipulating the node directly may make it unsynchronized.
        while node.next:
            self._tail = node = node.next
        return node

    def __iter__(self):
        node = self.head

        while node:
            yield node.data
            node = node.next


_PREDICT_TABLE = {
    "LIST_APPEND": ("JUMP_ABSOLUTE",),
    "SET_ADD": ("JUMP_ABSOLUTE",),
    "GET_ANEXT": ("LOAD_CONST",),
    "GET_AWAITABLE": ("LOAD_CONST",),
    "DICT_MERGE": ("CALL_FUNCTION_EX",),
    "MAP_ADD": ("JUMP_ABSOLUTE",),
    "COMPARE_OP": (
        "POP_JUMP_IF_FALSE",
        "POP_JUMP_IF_TRUE",
    ),
    "IS_OP": (
        "POP_JUMP_IF_FALSE",
        "POP_JUMP_IF_TRUE",
    ),
    "CONTAINS_OP": (
        "POP_JUMP_IF_FALSE",
        "POP_JUMP_IF_TRUE",
    ),
    # Note: there are some others with PREDICT on ceval, but they have more logic
    # and it needs more experimentation to know how it behaves in the static generated
    # code (and it's only an issue for us if there's actually a line change between
    # those, so, we don't have to really handle all the cases, only the one where
    # the line number actually changes from one instruction to the predicted one).
}

# 3.10 optimizations include copying code branches multiple times (for instance
# if the body of a finally has a single assign statement it can copy the assign to the case
# where an exception happens and doesn't happen for optimization purposes) and as such
# we need to add the programmatic breakpoint multiple times.
TRACK_MULTIPLE_BRANCHES = sys.version_info[:2] >= (3, 10)

# When tracking multiple branches, we try to fix the bytecodes which would be PREDICTED in the
# Python eval loop so that we don't have spurious line events that wouldn't usually be issued
# in the tracing as they're ignored due to the eval prediction (even though they're in the bytecode).
FIX_PREDICT = sys.version_info[:2] >= (3, 10)


def insert_pydevd_breaks(
    code_to_modify,
    breakpoint_lines,
    code_line_info=None,
    _pydev_stop_at_break=_pydev_stop_at_break,
    _pydev_needs_stop_at_break=_pydev_needs_stop_at_break,
):
    """
    Inserts pydevd programmatic breaks into the code (at the given lines).

    :param breakpoint_lines: set with the lines where we should add breakpoints.
    :return: tuple(boolean flag whether insertion was successful, modified code).
    """
    if code_line_info is None:
        code_line_info = _get_code_line_info(code_to_modify)

    if not code_line_info.line_to_offset:
        return False, code_to_modify

    # Create a copy (and make sure we're dealing with a set).
    breakpoint_lines = set(breakpoint_lines)

    # Note that we can even generate breakpoints on the first line of code
    # now, since we generate a spurious line event -- it may be a bit pointless
    # as we'll stop in the first line and we don't currently stop the tracing after the
    # user resumes, but in the future, if we do that, this would be a nice
    # improvement.
    # if code_to_modify.co_firstlineno in breakpoint_lines:
    #     return False, code_to_modify

    for line in breakpoint_lines:
        if line <= 0:
            # The first line is line 1, so, a break at line 0 is not valid.
            pydev_log.info("Trying to add breakpoint in invalid line: %s", line)
            return False, code_to_modify

    try:
        b = bytecode.Bytecode.from_code(code_to_modify)

        if DEBUG:
            op_number_bytecode = debug_helper.write_bytecode(b, prefix="bytecode.")

        helper_list = _HelperBytecodeList(b)

        modified_breakpoint_lines = breakpoint_lines.copy()

        curr_node = helper_list.head
        added_breaks_in_lines = set()
        last_lineno = None
        while curr_node is not None:
            instruction = curr_node.data
            instruction_lineno = getattr(instruction, "lineno", None)
            curr_name = getattr(instruction, "name", None)

            if FIX_PREDICT:
                predict_targets = _PREDICT_TABLE.get(curr_name)
                if predict_targets:
                    # Odd case: the next instruction may have a line number but it doesn't really
                    # appear in the tracing due to the PREDICT() in ceval, so, fix the bytecode so
                    # that it does things the way that ceval actually interprets it.
                    # See: https://mail.python.org/archives/list/python-dev@python.org/thread/CP2PTFCMTK57KM3M3DLJNWGO66R5RVPB/
                    next_instruction = curr_node.next.data
                    next_name = getattr(next_instruction, "name", None)
                    if next_name in predict_targets:
                        next_instruction_lineno = getattr(next_instruction, "lineno", None)
                        if next_instruction_lineno:
                            next_instruction.lineno = None

            if instruction_lineno is not None:
                if TRACK_MULTIPLE_BRANCHES:
                    if last_lineno is None:
                        last_lineno = instruction_lineno
                    else:
                        if last_lineno == instruction_lineno:
                            # If the previous is a label, someone may jump into it, so, we need to add
                            # the break even if it's in the same line.
                            if curr_node.prev.data.__class__ != Label:
                                # Skip adding this as the line is still the same.
                                curr_node = curr_node.next
                                continue
                        last_lineno = instruction_lineno
                else:
                    if instruction_lineno in added_breaks_in_lines:
                        curr_node = curr_node.next
                        continue

                if instruction_lineno in modified_breakpoint_lines:
                    added_breaks_in_lines.add(instruction_lineno)
                    if curr_node.prev is not None and curr_node.prev.data.__class__ == Label and curr_name == "POP_TOP":
                        # If we have a SETUP_FINALLY where the target is a POP_TOP, we can't change
                        # the target to be the breakpoint instruction (this can crash the interpreter).

                        for new_instruction in get_instructions_to_add(
                            instruction_lineno,
                            _pydev_stop_at_break=_pydev_stop_at_break,
                            _pydev_needs_stop_at_break=_pydev_needs_stop_at_break,
                        ):
                            curr_node = curr_node.append(new_instruction)

                    else:
                        for new_instruction in get_instructions_to_add(
                            instruction_lineno,
                            _pydev_stop_at_break=_pydev_stop_at_break,
                            _pydev_needs_stop_at_break=_pydev_needs_stop_at_break,
                        ):
                            curr_node.prepend(new_instruction)

            curr_node = curr_node.next

        b[:] = helper_list

        if DEBUG:
            debug_helper.write_bytecode(b, op_number_bytecode, prefix="bytecode.")

        new_code = b.to_code()

    except:
        pydev_log.exception("Error inserting pydevd breaks.")
        return False, code_to_modify

    if DEBUG:
        op_number = debug_helper.write_dis(code_to_modify)
        debug_helper.write_dis(new_code, op_number)

    return True, new_code

# === NexusCore/openenv\Lib\site-packages\google\generativeai\answer.py ===
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
from __future__ import annotations

import dataclasses
from collections.abc import Iterable
import itertools
from typing import Any, Iterable, Union, Mapping, Optional
from typing_extensions import TypedDict

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.generativeai.client import (
    get_default_generative_client,
    get_default_generative_async_client,
)
from google.generativeai.types import model_types
from google.generativeai.types import helper_types
from google.generativeai.types import safety_types
from google.generativeai.types import content_types
from google.generativeai.types import retriever_types
from google.generativeai.types.retriever_types import MetadataFilter

DEFAULT_ANSWER_MODEL = "models/aqa"

AnswerStyle = protos.GenerateAnswerRequest.AnswerStyle

AnswerStyleOptions = Union[int, str, AnswerStyle]

_ANSWER_STYLES: dict[AnswerStyleOptions, AnswerStyle] = {
    AnswerStyle.ANSWER_STYLE_UNSPECIFIED: AnswerStyle.ANSWER_STYLE_UNSPECIFIED,
    0: AnswerStyle.ANSWER_STYLE_UNSPECIFIED,
    "answer_style_unspecified": AnswerStyle.ANSWER_STYLE_UNSPECIFIED,
    "unspecified": AnswerStyle.ANSWER_STYLE_UNSPECIFIED,
    AnswerStyle.ABSTRACTIVE: AnswerStyle.ABSTRACTIVE,
    1: AnswerStyle.ABSTRACTIVE,
    "answer_style_abstractive": AnswerStyle.ABSTRACTIVE,
    "abstractive": AnswerStyle.ABSTRACTIVE,
    AnswerStyle.EXTRACTIVE: AnswerStyle.EXTRACTIVE,
    2: AnswerStyle.EXTRACTIVE,
    "answer_style_extractive": AnswerStyle.EXTRACTIVE,
    "extractive": AnswerStyle.EXTRACTIVE,
    AnswerStyle.VERBOSE: AnswerStyle.VERBOSE,
    3: AnswerStyle.VERBOSE,
    "answer_style_verbose": AnswerStyle.VERBOSE,
    "verbose": AnswerStyle.VERBOSE,
}


def to_answer_style(x: AnswerStyleOptions) -> AnswerStyle:
    if isinstance(x, str):
        x = x.lower()
    return _ANSWER_STYLES[x]


GroundingPassageOptions = (
    Union[
        protos.GroundingPassage, tuple[str, content_types.ContentType], content_types.ContentType
    ],
)

GroundingPassagesOptions = Union[
    protos.GroundingPassages,
    Iterable[GroundingPassageOptions],
    Mapping[str, content_types.ContentType],
]


def _make_grounding_passages(source: GroundingPassagesOptions) -> protos.GroundingPassages:
    """
    Converts the `source` into a `protos.GroundingPassage`. A `GroundingPassages` contains a list of
    `protos.GroundingPassage` objects, which each contain a `protos.Content` and a string `id`.

    Args:
        source: `Content` or a `GroundingPassagesOptions` that will be converted to protos.GroundingPassages.

    Return:
        `protos.GroundingPassages` to be passed into `protos.GenerateAnswer`.
    """
    if isinstance(source, protos.GroundingPassages):
        return source

    if not isinstance(source, Iterable):
        raise TypeError(
            f"Invalid input: The 'source' argument must be an instance of 'GroundingPassagesOptions'. Received a '{type(source).__name__}' object instead."
        )

    passages = []
    if isinstance(source, Mapping):
        source = source.items()

    for n, data in enumerate(source):
        if isinstance(data, protos.GroundingPassage):
            passages.append(data)
        elif isinstance(data, tuple):
            id, content = data  # tuple must have exactly 2 items.
            passages.append({"id": id, "content": content_types.to_content(content)})
        else:
            passages.append({"id": str(n), "content": content_types.to_content(data)})

    return protos.GroundingPassages(passages=passages)


SourceNameType = Union[
    str, retriever_types.Corpus, protos.Corpus, retriever_types.Document, protos.Document
]


class SemanticRetrieverConfigDict(TypedDict):
    source: SourceNameType
    query: content_types.ContentsType
    metadata_filter: Optional[Iterable[MetadataFilter]]
    max_chunks_count: Optional[int]
    minimum_relevance_score: Optional[float]


SemanticRetrieverConfigOptions = Union[
    SourceNameType,
    SemanticRetrieverConfigDict,
    protos.SemanticRetrieverConfig,
]


def _maybe_get_source_name(source) -> str | None:
    if isinstance(source, str):
        return source
    elif isinstance(
        source, (retriever_types.Corpus, protos.Corpus, retriever_types.Document, protos.Document)
    ):
        return source.name
    else:
        return None


def _make_semantic_retriever_config(
    source: SemanticRetrieverConfigOptions,
    query: content_types.ContentsType,
) -> protos.SemanticRetrieverConfig:
    if isinstance(source, protos.SemanticRetrieverConfig):
        return source

    name = _maybe_get_source_name(source)
    if name is not None:
        source = {"source": name}
    elif isinstance(source, dict):
        source["source"] = _maybe_get_source_name(source["source"])
    else:
        raise TypeError(
            f"Invalid input: Failed to create a 'protos.SemanticRetrieverConfig' from the provided source. "
            f"Received type: {type(source).__name__}, "
            f"Received value: {source}"
        )

    if source["query"] is None:
        source["query"] = query
    elif isinstance(source["query"], str):
        source["query"] = content_types.to_content(source["query"])

    return protos.SemanticRetrieverConfig(source)


def _make_generate_answer_request(
    *,
    model: model_types.AnyModelNameOptions = DEFAULT_ANSWER_MODEL,
    contents: content_types.ContentsType,
    inline_passages: GroundingPassagesOptions | None = None,
    semantic_retriever: SemanticRetrieverConfigOptions | None = None,
    answer_style: AnswerStyle | None = None,
    safety_settings: safety_types.SafetySettingOptions | None = None,
    temperature: float | None = None,
) -> protos.GenerateAnswerRequest:
    """
    constructs a protos.GenerateAnswerRequest object by organizing the input parameters for the API call to generate a grounded answer from the model.

    Args:
        model: Name of the model used to generate the grounded response.
        contents: Content of the current conversation with the model. For single-turn query, this is a
            single question to answer. For multi-turn queries, this is a repeated field that contains
            conversation history and the last `Content` in the list containing the question.
        inline_passages: Grounding passages (a list of `Content`-like objects or `(id, content)` pairs,
            or a `protos.GroundingPassages`) to send inline with the request. Exclusive with `semantic_retriever`,
            one must be set, but not both.
        semantic_retriever: A Corpus, Document, or `protos.SemanticRetrieverConfig` to use for grounding. Exclusive with
             `inline_passages`, one must be set, but not both.
        answer_style: Style for grounded answers.
        safety_settings: Safety settings for generated output.
        temperature: The temperature for randomness in the output.

    Returns:
        Call for protos.GenerateAnswerRequest().
    """
    model = model_types.make_model_name(model)

    contents = content_types.to_contents(contents)

    if safety_settings:
        safety_settings = safety_types.normalize_safety_settings(safety_settings)

    if inline_passages is not None and semantic_retriever is not None:
        raise ValueError(
            f"Invalid configuration: Please set either 'inline_passages' or 'semantic_retriever_config', but not both. "
            f"Received for inline_passages: {inline_passages}, and for semantic_retriever: {semantic_retriever}."
        )
    elif inline_passages is not None:
        inline_passages = _make_grounding_passages(inline_passages)
    elif semantic_retriever is not None:
        semantic_retriever = _make_semantic_retriever_config(semantic_retriever, contents[-1])
    else:
        raise TypeError(
            f"Invalid configuration: Either 'inline_passages' or 'semantic_retriever_config' must be provided, but currently both are 'None'. "
            f"Received for inline_passages: {inline_passages}, and for semantic_retriever: {semantic_retriever}."
        )

    if answer_style:
        answer_style = to_answer_style(answer_style)

    return protos.GenerateAnswerRequest(
        model=model,
        contents=contents,
        inline_passages=inline_passages,
        semantic_retriever=semantic_retriever,
        safety_settings=safety_settings,
        temperature=temperature,
        answer_style=answer_style,
    )


def generate_answer(
    *,
    model: model_types.AnyModelNameOptions = DEFAULT_ANSWER_MODEL,
    contents: content_types.ContentsType,
    inline_passages: GroundingPassagesOptions | None = None,
    semantic_retriever: SemanticRetrieverConfigOptions | None = None,
    answer_style: AnswerStyle | None = None,
    safety_settings: safety_types.SafetySettingOptions | None = None,
    temperature: float | None = None,
    client: glm.GenerativeServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):
    """Calls the GenerateAnswer API and returns a `types.Answer` containing the response.

    You can pass a literal list of text chunks:

    >>> from google.generativeai import answer
    >>> answer.generate_answer(
    ...     content=question,
    ...     inline_passages=splitter.split(document)
    ... )

    Or pass a reference to a retreiver Document or Corpus:

    >>> from google.generativeai import answer
    >>> from google.generativeai import retriever
    >>> my_corpus = retriever.get_corpus('my_corpus')
    >>> genai.generate_answer(
    ...     content=question,
    ...     semantic_retriever=my_corpus
    ... )


    Args:
        model: Which model to call, as a string or a `types.Model`.
        contents: The question to be answered by the model, grounded in the
                provided source.
        inline_passages: Grounding passages (a list of `Content`-like objects or (id, content) pairs,
            or a `protos.GroundingPassages`) to send inline with the request. Exclusive with `semantic_retriever`,
            one must be set, but not both.
        semantic_retriever: A Corpus, Document, or `protos.SemanticRetrieverConfig` to use for grounding. Exclusive with
             `inline_passages`, one must be set, but not both.
        answer_style: Style in which the grounded answer should be returned.
        safety_settings: Safety settings for generated output. Defaults to None.
        temperature: Controls the randomness of the output.
        client: If you're not relying on a default client, you pass a `glm.TextServiceClient` instead.
        request_options: Options for the request.

    Returns:
        A `types.Answer` containing the model's text answer response.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_generative_client()

    request = _make_generate_answer_request(
        model=model,
        contents=contents,
        inline_passages=inline_passages,
        semantic_retriever=semantic_retriever,
        safety_settings=safety_settings,
        temperature=temperature,
        answer_style=answer_style,
    )

    response = client.generate_answer(request, **request_options)

    return response


async def generate_answer_async(
    *,
    model: model_types.AnyModelNameOptions = DEFAULT_ANSWER_MODEL,
    contents: content_types.ContentsType,
    inline_passages: GroundingPassagesOptions | None = None,
    semantic_retriever: SemanticRetrieverConfigOptions | None = None,
    answer_style: AnswerStyle | None = None,
    safety_settings: safety_types.SafetySettingOptions | None = None,
    temperature: float | None = None,
    client: glm.GenerativeServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):
    """
    Calls the API and returns a `types.Answer` containing the answer.

    Args:
        model: Which model to call, as a string or a `types.Model`.
        contents: The question to be answered by the model, grounded in the
                provided source.
        inline_passages: Grounding passages (a list of `Content`-like objects or (id, content) pairs,
            or a `protos.GroundingPassages`) to send inline with the request. Exclusive with `semantic_retriever`,
            one must be set, but not both.
        semantic_retriever: A Corpus, Document, or `protos.SemanticRetrieverConfig` to use for grounding. Exclusive with
             `inline_passages`, one must be set, but not both.
        answer_style: Style in which the grounded answer should be returned.
        safety_settings: Safety settings for generated output. Defaults to None.
        temperature: Controls the randomness of the output.
        client: If you're not relying on a default client, you pass a `glm.TextServiceClient` instead.

    Returns:
        A `types.Answer` containing the model's text answer response.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_generative_async_client()

    request = _make_generate_answer_request(
        model=model,
        contents=contents,
        inline_passages=inline_passages,
        semantic_retriever=semantic_retriever,
        safety_settings=safety_settings,
        temperature=temperature,
        answer_style=answer_style,
    )

    response = await client.generate_answer(request, **request_options)

    return response

# === NexusCore/openenv\Lib\site-packages\numpy\_core\memmap.py ===
import operator
from contextlib import nullcontext

import numpy as np
from numpy._utils import set_module

from .numeric import dtype, ndarray, uint8

__all__ = ['memmap']

dtypedescr = dtype
valid_filemodes = ["r", "c", "r+", "w+"]
writeable_filemodes = ["r+", "w+"]

mode_equivalents = {
    "readonly": "r",
    "copyonwrite": "c",
    "readwrite": "r+",
    "write": "w+"
    }


@set_module('numpy')
class memmap(ndarray):
    """Create a memory-map to an array stored in a *binary* file on disk.

    Memory-mapped files are used for accessing small segments of large files
    on disk, without reading the entire file into memory.  NumPy's
    memmap's are array-like objects.  This differs from Python's ``mmap``
    module, which uses file-like objects.

    This subclass of ndarray has some unpleasant interactions with
    some operations, because it doesn't quite fit properly as a subclass.
    An alternative to using this subclass is to create the ``mmap``
    object yourself, then create an ndarray with ndarray.__new__ directly,
    passing the object created in its 'buffer=' parameter.

    This class may at some point be turned into a factory function
    which returns a view into an mmap buffer.

    Flush the memmap instance to write the changes to the file. Currently there
    is no API to close the underlying ``mmap``. It is tricky to ensure the
    resource is actually closed, since it may be shared between different
    memmap instances.


    Parameters
    ----------
    filename : str, file-like object, or pathlib.Path instance
        The file name or file object to be used as the array data buffer.
    dtype : data-type, optional
        The data-type used to interpret the file contents.
        Default is `uint8`.
    mode : {'r+', 'r', 'w+', 'c'}, optional
        The file is opened in this mode:

        +------+-------------------------------------------------------------+
        | 'r'  | Open existing file for reading only.                        |
        +------+-------------------------------------------------------------+
        | 'r+' | Open existing file for reading and writing.                 |
        +------+-------------------------------------------------------------+
        | 'w+' | Create or overwrite existing file for reading and writing.  |
        |      | If ``mode == 'w+'`` then `shape` must also be specified.    |
        +------+-------------------------------------------------------------+
        | 'c'  | Copy-on-write: assignments affect data in memory, but       |
        |      | changes are not saved to disk.  The file on disk is         |
        |      | read-only.                                                  |
        +------+-------------------------------------------------------------+

        Default is 'r+'.
    offset : int, optional
        In the file, array data starts at this offset. Since `offset` is
        measured in bytes, it should normally be a multiple of the byte-size
        of `dtype`. When ``mode != 'r'``, even positive offsets beyond end of
        file are valid; The file will be extended to accommodate the
        additional data. By default, ``memmap`` will start at the beginning of
        the file, even if ``filename`` is a file pointer ``fp`` and
        ``fp.tell() != 0``.
    shape : int or sequence of ints, optional
        The desired shape of the array. If ``mode == 'r'`` and the number
        of remaining bytes after `offset` is not a multiple of the byte-size
        of `dtype`, you must specify `shape`. By default, the returned array
        will be 1-D with the number of elements determined by file size
        and data-type.

        .. versionchanged:: 2.0
         The shape parameter can now be any integer sequence type, previously
         types were limited to tuple and int.

    order : {'C', 'F'}, optional
        Specify the order of the ndarray memory layout:
        :term:`row-major`, C-style or :term:`column-major`,
        Fortran-style.  This only has an effect if the shape is
        greater than 1-D.  The default order is 'C'.

    Attributes
    ----------
    filename : str or pathlib.Path instance
        Path to the mapped file.
    offset : int
        Offset position in the file.
    mode : str
        File mode.

    Methods
    -------
    flush
        Flush any changes in memory to file on disk.
        When you delete a memmap object, flush is called first to write
        changes to disk.


    See also
    --------
    lib.format.open_memmap : Create or load a memory-mapped ``.npy`` file.

    Notes
    -----
    The memmap object can be used anywhere an ndarray is accepted.
    Given a memmap ``fp``, ``isinstance(fp, numpy.ndarray)`` returns
    ``True``.

    Memory-mapped files cannot be larger than 2GB on 32-bit systems.

    When a memmap causes a file to be created or extended beyond its
    current size in the filesystem, the contents of the new part are
    unspecified. On systems with POSIX filesystem semantics, the extended
    part will be filled with zero bytes.

    Examples
    --------
    >>> import numpy as np
    >>> data = np.arange(12, dtype='float32')
    >>> data.resize((3,4))

    This example uses a temporary file so that doctest doesn't write
    files to your directory. You would use a 'normal' filename.

    >>> from tempfile import mkdtemp
    >>> import os.path as path
    >>> filename = path.join(mkdtemp(), 'newfile.dat')

    Create a memmap with dtype and shape that matches our data:

    >>> fp = np.memmap(filename, dtype='float32', mode='w+', shape=(3,4))
    >>> fp
    memmap([[0., 0., 0., 0.],
            [0., 0., 0., 0.],
            [0., 0., 0., 0.]], dtype=float32)

    Write data to memmap array:

    >>> fp[:] = data[:]
    >>> fp
    memmap([[  0.,   1.,   2.,   3.],
            [  4.,   5.,   6.,   7.],
            [  8.,   9.,  10.,  11.]], dtype=float32)

    >>> fp.filename == path.abspath(filename)
    True

    Flushes memory changes to disk in order to read them back

    >>> fp.flush()

    Load the memmap and verify data was stored:

    >>> newfp = np.memmap(filename, dtype='float32', mode='r', shape=(3,4))
    >>> newfp
    memmap([[  0.,   1.,   2.,   3.],
            [  4.,   5.,   6.,   7.],
            [  8.,   9.,  10.,  11.]], dtype=float32)

    Read-only memmap:

    >>> fpr = np.memmap(filename, dtype='float32', mode='r', shape=(3,4))
    >>> fpr.flags.writeable
    False

    Copy-on-write memmap:

    >>> fpc = np.memmap(filename, dtype='float32', mode='c', shape=(3,4))
    >>> fpc.flags.writeable
    True

    It's possible to assign to copy-on-write array, but values are only
    written into the memory copy of the array, and not written to disk:

    >>> fpc
    memmap([[  0.,   1.,   2.,   3.],
            [  4.,   5.,   6.,   7.],
            [  8.,   9.,  10.,  11.]], dtype=float32)
    >>> fpc[0,:] = 0
    >>> fpc
    memmap([[  0.,   0.,   0.,   0.],
            [  4.,   5.,   6.,   7.],
            [  8.,   9.,  10.,  11.]], dtype=float32)

    File on disk is unchanged:

    >>> fpr
    memmap([[  0.,   1.,   2.,   3.],
            [  4.,   5.,   6.,   7.],
            [  8.,   9.,  10.,  11.]], dtype=float32)

    Offset into a memmap:

    >>> fpo = np.memmap(filename, dtype='float32', mode='r', offset=16)
    >>> fpo
    memmap([  4.,   5.,   6.,   7.,   8.,   9.,  10.,  11.], dtype=float32)

    """

    __array_priority__ = -100.0

    def __new__(subtype, filename, dtype=uint8, mode='r+', offset=0,
                shape=None, order='C'):
        # Import here to minimize 'import numpy' overhead
        import mmap
        import os.path
        try:
            mode = mode_equivalents[mode]
        except KeyError as e:
            if mode not in valid_filemodes:
                all_modes = valid_filemodes + list(mode_equivalents.keys())
                raise ValueError(
                    f"mode must be one of {all_modes!r} (got {mode!r})"
                ) from None

        if mode == 'w+' and shape is None:
            raise ValueError("shape must be given if mode == 'w+'")

        if hasattr(filename, 'read'):
            f_ctx = nullcontext(filename)
        else:
            f_ctx = open(
                os.fspath(filename),
                ('r' if mode == 'c' else mode) + 'b'
            )

        with f_ctx as fid:
            fid.seek(0, 2)
            flen = fid.tell()
            descr = dtypedescr(dtype)
            _dbytes = descr.itemsize

            if shape is None:
                bytes = flen - offset
                if bytes % _dbytes:
                    raise ValueError("Size of available data is not a "
                            "multiple of the data-type size.")
                size = bytes // _dbytes
                shape = (size,)
            else:
                if not isinstance(shape, (tuple, list)):
                    try:
                        shape = [operator.index(shape)]
                    except TypeError:
                        pass
                shape = tuple(shape)
                size = np.intp(1)  # avoid overflows
                for k in shape:
                    size *= k

            bytes = int(offset + size * _dbytes)

            if mode in ('w+', 'r+'):
                # gh-27723
                # if bytes == 0, we write out 1 byte to allow empty memmap.
                bytes = max(bytes, 1)
                if flen < bytes:
                    fid.seek(bytes - 1, 0)
                    fid.write(b'\0')
                    fid.flush()

            if mode == 'c':
                acc = mmap.ACCESS_COPY
            elif mode == 'r':
                acc = mmap.ACCESS_READ
            else:
                acc = mmap.ACCESS_WRITE

            start = offset - offset % mmap.ALLOCATIONGRANULARITY
            bytes -= start
            # bytes == 0 is problematic as in mmap length=0 maps the full file.
            # See PR gh-27723 for a more detailed explanation.
            if bytes == 0 and start > 0:
                bytes += mmap.ALLOCATIONGRANULARITY
                start -= mmap.ALLOCATIONGRANULARITY
            array_offset = offset - start
            mm = mmap.mmap(fid.fileno(), bytes, access=acc, offset=start)

            self = ndarray.__new__(subtype, shape, dtype=descr, buffer=mm,
                                   offset=array_offset, order=order)
            self._mmap = mm
            self.offset = offset
            self.mode = mode

            if isinstance(filename, os.PathLike):
                # special case - if we were constructed with a pathlib.path,
                # then filename is a path object, not a string
                self.filename = filename.resolve()
            elif hasattr(fid, "name") and isinstance(fid.name, str):
                # py3 returns int for TemporaryFile().name
                self.filename = os.path.abspath(fid.name)
            # same as memmap copies (e.g. memmap + 1)
            else:
                self.filename = None

        return self

    def __array_finalize__(self, obj):
        if hasattr(obj, '_mmap') and np.may_share_memory(self, obj):
            self._mmap = obj._mmap
            self.filename = obj.filename
            self.offset = obj.offset
            self.mode = obj.mode
        else:
            self._mmap = None
            self.filename = None
            self.offset = None
            self.mode = None

    def flush(self):
        """
        Write any changes in the array to the file on disk.

        For further information, see `memmap`.

        Parameters
        ----------
        None

        See Also
        --------
        memmap

        """
        if self.base is not None and hasattr(self.base, 'flush'):
            self.base.flush()

    def __array_wrap__(self, arr, context=None, return_scalar=False):
        arr = super().__array_wrap__(arr, context)

        # Return a memmap if a memmap was given as the output of the
        # ufunc. Leave the arr class unchanged if self is not a memmap
        # to keep original memmap subclasses behavior
        if self is arr or type(self) is not memmap:
            return arr

        # Return scalar instead of 0d memmap, e.g. for np.sum with
        # axis=None (note that subclasses will not reach here)
        if return_scalar:
            return arr[()]

        # Return ndarray otherwise
        return arr.view(np.ndarray)

    def __getitem__(self, index):
        res = super().__getitem__(index)
        if type(res) is memmap and res._mmap is None:
            return res.view(type=ndarray)
        return res

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\factor.py ===
"""
    pygments.lexers.factor
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for the Factor language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, default, words
from pygments.token import Text, Comment, Keyword, Name, String, Number, \
    Whitespace, Punctuation

__all__ = ['FactorLexer']


class FactorLexer(RegexLexer):
    """
    Lexer for the Factor language.
    """
    name = 'Factor'
    url = 'http://factorcode.org'
    aliases = ['factor']
    filenames = ['*.factor']
    mimetypes = ['text/x-factor']
    version_added = '1.4'

    builtin_kernel = words((
        '-rot', '2bi', '2bi@', '2bi*', '2curry', '2dip', '2drop', '2dup', '2keep', '2nip',
        '2over', '2tri', '2tri@', '2tri*', '3bi', '3curry', '3dip', '3drop', '3dup', '3keep',
        '3tri', '4dip', '4drop', '4dup', '4keep', '<wrapper>', '=', '>boolean', 'clone',
        '?', '?execute', '?if', 'and', 'assert', 'assert=', 'assert?', 'bi', 'bi-curry',
        'bi-curry@', 'bi-curry*', 'bi@', 'bi*', 'boa', 'boolean', 'boolean?', 'both?',
        'build', 'call', 'callstack', 'callstack>array', 'callstack?', 'clear', '(clone)',
        'compose', 'compose?', 'curry', 'curry?', 'datastack', 'die', 'dip', 'do', 'drop',
        'dup', 'dupd', 'either?', 'eq?', 'equal?', 'execute', 'hashcode', 'hashcode*',
        'identity-hashcode', 'identity-tuple', 'identity-tuple?', 'if', 'if*',
        'keep', 'loop', 'most', 'new', 'nip', 'not', 'null', 'object', 'or', 'over',
        'pick', 'prepose', 'retainstack', 'rot', 'same?', 'swap', 'swapd', 'throw',
        'tri', 'tri-curry', 'tri-curry@', 'tri-curry*', 'tri@', 'tri*', 'tuple',
        'tuple?', 'unless', 'unless*', 'until', 'when', 'when*', 'while', 'with',
        'wrapper', 'wrapper?', 'xor'), suffix=r'(\s+)')

    builtin_assocs = words((
        '2cache', '<enum>', '>alist', '?at', '?of', 'assoc', 'assoc-all?',
        'assoc-any?', 'assoc-clone-like', 'assoc-combine', 'assoc-diff',
        'assoc-diff!', 'assoc-differ', 'assoc-each', 'assoc-empty?',
        'assoc-filter', 'assoc-filter!', 'assoc-filter-as', 'assoc-find',
        'assoc-hashcode', 'assoc-intersect', 'assoc-like', 'assoc-map',
        'assoc-map-as', 'assoc-partition', 'assoc-refine', 'assoc-size',
        'assoc-stack', 'assoc-subset?', 'assoc-union', 'assoc-union!',
        'assoc=', 'assoc>map', 'assoc?', 'at', 'at+', 'at*', 'cache', 'change-at',
        'clear-assoc', 'delete-at', 'delete-at*', 'enum', 'enum?', 'extract-keys',
        'inc-at', 'key?', 'keys', 'map>assoc', 'maybe-set-at', 'new-assoc', 'of',
        'push-at', 'rename-at', 'set-at', 'sift-keys', 'sift-values', 'substitute',
        'unzip', 'value-at', 'value-at*', 'value?', 'values', 'zip'), suffix=r'(\s+)')

    builtin_combinators = words((
        '2cleave', '2cleave>quot', '3cleave', '3cleave>quot', '4cleave',
        '4cleave>quot', 'alist>quot', 'call-effect', 'case', 'case-find',
        'case>quot', 'cleave', 'cleave>quot', 'cond', 'cond>quot', 'deep-spread>quot',
        'execute-effect', 'linear-case-quot', 'no-case', 'no-case?', 'no-cond',
        'no-cond?', 'recursive-hashcode', 'shallow-spread>quot', 'spread',
        'to-fixed-point', 'wrong-values', 'wrong-values?'), suffix=r'(\s+)')

    builtin_math = words((
        '-', '/', '/f', '/i', '/mod', '2/', '2^', '<', '<=', '<fp-nan>', '>',
        '>=', '>bignum', '>fixnum', '>float', '>integer', '(all-integers?)',
        '(each-integer)', '(find-integer)', '*', '+', '?1+',
        'abs', 'align', 'all-integers?', 'bignum', 'bignum?', 'bit?', 'bitand',
        'bitnot', 'bitor', 'bits>double', 'bits>float', 'bitxor', 'complex',
        'complex?', 'denominator', 'double>bits', 'each-integer', 'even?',
        'find-integer', 'find-last-integer', 'fixnum', 'fixnum?', 'float',
        'float>bits', 'float?', 'fp-bitwise=', 'fp-infinity?', 'fp-nan-payload',
        'fp-nan?', 'fp-qnan?', 'fp-sign', 'fp-snan?', 'fp-special?',
        'if-zero', 'imaginary-part', 'integer', 'integer>fixnum',
        'integer>fixnum-strict', 'integer?', 'log2', 'log2-expects-positive',
        'log2-expects-positive?', 'mod', 'neg', 'neg?', 'next-float',
        'next-power-of-2', 'number', 'number=', 'number?', 'numerator', 'odd?',
        'out-of-fixnum-range', 'out-of-fixnum-range?', 'power-of-2?',
        'prev-float', 'ratio', 'ratio?', 'rational', 'rational?', 'real',
        'real-part', 'real?', 'recip', 'rem', 'sgn', 'shift', 'sq', 'times',
        'u<', 'u<=', 'u>', 'u>=', 'unless-zero', 'unordered?', 'when-zero',
        'zero?'), suffix=r'(\s+)')

    builtin_sequences = words((
        '1sequence', '2all?', '2each', '2map', '2map-as', '2map-reduce', '2reduce',
        '2selector', '2sequence', '3append', '3append-as', '3each', '3map', '3map-as',
        '3sequence', '4sequence', '<repetition>', '<reversed>', '<slice>', '?first',
        '?last', '?nth', '?second', '?set-nth', 'accumulate', 'accumulate!',
        'accumulate-as', 'all?', 'any?', 'append', 'append!', 'append-as',
        'assert-sequence', 'assert-sequence=', 'assert-sequence?',
        'binary-reduce', 'bounds-check', 'bounds-check?', 'bounds-error',
        'bounds-error?', 'but-last', 'but-last-slice', 'cartesian-each',
        'cartesian-map', 'cartesian-product', 'change-nth', 'check-slice',
        'check-slice-error', 'clone-like', 'collapse-slice', 'collector',
        'collector-for', 'concat', 'concat-as', 'copy', 'count', 'cut', 'cut-slice',
        'cut*', 'delete-all', 'delete-slice', 'drop-prefix', 'each', 'each-from',
        'each-index', 'empty?', 'exchange', 'filter', 'filter!', 'filter-as', 'find',
        'find-from', 'find-index', 'find-index-from', 'find-last', 'find-last-from',
        'first', 'first2', 'first3', 'first4', 'flip', 'follow', 'fourth', 'glue', 'halves',
        'harvest', 'head', 'head-slice', 'head-slice*', 'head*', 'head?',
        'if-empty', 'immutable', 'immutable-sequence', 'immutable-sequence?',
        'immutable?', 'index', 'index-from', 'indices', 'infimum', 'infimum-by',
        'insert-nth', 'interleave', 'iota', 'iota-tuple', 'iota-tuple?', 'join',
        'join-as', 'last', 'last-index', 'last-index-from', 'length', 'lengthen',
        'like', 'longer', 'longer?', 'longest', 'map', 'map!', 'map-as', 'map-find',
        'map-find-last', 'map-index', 'map-integers', 'map-reduce', 'map-sum',
        'max-length', 'member-eq?', 'member?', 'midpoint@', 'min-length',
        'mismatch', 'move', 'new-like', 'new-resizable', 'new-sequence',
        'non-negative-integer-expected', 'non-negative-integer-expected?',
        'nth', 'nths', 'pad-head', 'pad-tail', 'padding', 'partition', 'pop', 'pop*',
        'prefix', 'prepend', 'prepend-as', 'produce', 'produce-as', 'product', 'push',
        'push-all', 'push-either', 'push-if', 'reduce', 'reduce-index', 'remove',
        'remove!', 'remove-eq', 'remove-eq!', 'remove-nth', 'remove-nth!', 'repetition',
        'repetition?', 'replace-slice', 'replicate', 'replicate-as', 'rest',
        'rest-slice', 'reverse', 'reverse!', 'reversed', 'reversed?', 'second',
        'selector', 'selector-for', 'sequence', 'sequence-hashcode', 'sequence=',
        'sequence?', 'set-first', 'set-fourth', 'set-last', 'set-length', 'set-nth',
        'set-second', 'set-third', 'short', 'shorten', 'shorter', 'shorter?',
        'shortest', 'sift', 'slice', 'slice-error', 'slice-error?', 'slice?',
        'snip', 'snip-slice', 'start', 'start*', 'subseq', 'subseq?', 'suffix',
        'suffix!', 'sum', 'sum-lengths', 'supremum', 'supremum-by', 'surround', 'tail',
        'tail-slice', 'tail-slice*', 'tail*', 'tail?', 'third', 'trim',
        'trim-head', 'trim-head-slice', 'trim-slice', 'trim-tail', 'trim-tail-slice',
        'unclip', 'unclip-last', 'unclip-last-slice', 'unclip-slice', 'unless-empty',
        'virtual-exemplar', 'virtual-sequence', 'virtual-sequence?', 'virtual@',
        'when-empty'), suffix=r'(\s+)')

    builtin_namespaces = words((
        '+@', 'change', 'change-global', 'counter', 'dec', 'get', 'get-global',
        'global', 'inc', 'init-namespaces', 'initialize', 'is-global', 'make-assoc',
        'namespace', 'namestack', 'off', 'on', 'set', 'set-global', 'set-namestack',
        'toggle', 'with-global', 'with-scope', 'with-variable', 'with-variables'),
        suffix=r'(\s+)')

    builtin_arrays = words((
        '1array', '2array', '3array', '4array', '<array>', '>array', 'array',
        'array?', 'pair', 'pair?', 'resize-array'), suffix=r'(\s+)')

    builtin_io = words((
        '(each-stream-block-slice)', '(each-stream-block)',
        '(stream-contents-by-block)', '(stream-contents-by-element)',
        '(stream-contents-by-length-or-block)',
        '(stream-contents-by-length)', '+byte+', '+character+',
        'bad-seek-type', 'bad-seek-type?', 'bl', 'contents', 'each-block',
        'each-block-size', 'each-block-slice', 'each-line', 'each-morsel',
        'each-stream-block', 'each-stream-block-slice', 'each-stream-line',
        'error-stream', 'flush', 'input-stream', 'input-stream?',
        'invalid-read-buffer', 'invalid-read-buffer?', 'lines', 'nl',
        'output-stream', 'output-stream?', 'print', 'read', 'read-into',
        'read-partial', 'read-partial-into', 'read-until', 'read1', 'readln',
        'seek-absolute', 'seek-absolute?', 'seek-end', 'seek-end?',
        'seek-input', 'seek-output', 'seek-relative', 'seek-relative?',
        'stream-bl', 'stream-contents', 'stream-contents*', 'stream-copy',
        'stream-copy*', 'stream-element-type', 'stream-flush',
        'stream-length', 'stream-lines', 'stream-nl', 'stream-print',
        'stream-read', 'stream-read-into', 'stream-read-partial',
        'stream-read-partial-into', 'stream-read-partial-unsafe',
        'stream-read-unsafe', 'stream-read-until', 'stream-read1',
        'stream-readln', 'stream-seek', 'stream-seekable?', 'stream-tell',
        'stream-write', 'stream-write1', 'tell-input', 'tell-output',
        'with-error-stream', 'with-error-stream*', 'with-error>output',
        'with-input-output+error-streams',
        'with-input-output+error-streams*', 'with-input-stream',
        'with-input-stream*', 'with-output-stream', 'with-output-stream*',
        'with-output>error', 'with-output+error-stream',
        'with-output+error-stream*', 'with-streams', 'with-streams*',
        'write', 'write1'), suffix=r'(\s+)')

    builtin_strings = words((
        '1string', '<string>', '>string', 'resize-string', 'string',
        'string?'), suffix=r'(\s+)')

    builtin_vectors = words((
        '1vector', '<vector>', '>vector', '?push', 'vector', 'vector?'),
        suffix=r'(\s+)')

    builtin_continuations = words((
        '<condition>', '<continuation>', '<restart>', 'attempt-all',
        'attempt-all-error', 'attempt-all-error?', 'callback-error-hook',
        'callcc0', 'callcc1', 'cleanup', 'compute-restarts', 'condition',
        'condition?', 'continuation', 'continuation?', 'continue',
        'continue-restart', 'continue-with', 'current-continuation',
        'error', 'error-continuation', 'error-in-thread', 'error-thread',
        'ifcc', 'ignore-errors', 'in-callback?', 'original-error', 'recover',
        'restart', 'restart?', 'restarts', 'rethrow', 'rethrow-restarts',
        'return', 'return-continuation', 'thread-error-hook', 'throw-continue',
        'throw-restarts', 'with-datastack', 'with-return'), suffix=r'(\s+)')

    tokens = {
        'root': [
            # factor allows a file to start with a shebang
            (r'#!.*$', Comment.Preproc),
            default('base'),
        ],
        'base': [
            (r'\s+', Whitespace),

            # defining words
            (r'((?:MACRO|MEMO|TYPED)?:[:]?)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function)),
            (r'(M:[:]?)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class, Whitespace,
                 Name.Function)),
            (r'(C:)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function, Whitespace,
                 Name.Class)),
            (r'(GENERIC:)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function)),
            (r'(HOOK:|GENERIC#)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function, Whitespace,
                 Name.Function)),
            (r'(\()(\s)', bygroups(Name.Function, Whitespace), 'stackeffect'),
            (r'(;)(\s)', bygroups(Keyword, Whitespace)),

            # imports and namespaces
            (r'(USING:)(\s+)',
             bygroups(Keyword.Namespace, Whitespace), 'vocabs'),
            (r'(USE:|UNUSE:|IN:|QUALIFIED:)(\s+)(\S+)',
             bygroups(Keyword.Namespace, Whitespace, Name.Namespace)),
            (r'(QUALIFIED-WITH:)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword.Namespace, Whitespace, Name.Namespace,
                 Whitespace, Name.Namespace)),
            (r'(FROM:|EXCLUDE:)(\s+)(\S+)(\s+=>\s)',
             bygroups(Keyword.Namespace, Whitespace, Name.Namespace,
                 Whitespace), 'words'),
            (r'(RENAME:)(\s+)(\S+)(\s+)(\S+)(\s+)(=>)(\s+)(\S+)',
             bygroups(Keyword.Namespace, Whitespace, Name.Function, Whitespace,
                 Name.Namespace, Whitespace, Punctuation, Whitespace,
                 Name.Function)),
            (r'(ALIAS:|TYPEDEF:)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword.Namespace, Whitespace, Name.Function, Whitespace,
                 Name.Function)),
            (r'(DEFER:|FORGET:|POSTPONE:)(\s+)(\S+)',
             bygroups(Keyword.Namespace, Whitespace, Name.Function)),

            # tuples and classes
            (r'(TUPLE:|ERROR:)(\s+)(\S+)(\s+)(<)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class, Whitespace, Punctuation,
                 Whitespace, Name.Class), 'slots'),
            (r'(TUPLE:|ERROR:|BUILTIN:)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class), 'slots'),
            (r'(MIXIN:|UNION:|INTERSECTION:)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class)),
            (r'(PREDICATE:)(\s+)(\S+)(\s+)(<)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class, Whitespace,
                 Punctuation, Whitespace, Name.Class)),
            (r'(C:)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function, Whitespace, Name.Class)),
            (r'(INSTANCE:)(\s+)(\S+)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Class, Whitespace, Name.Class)),
            (r'(SLOT:)(\s+)(\S+)', bygroups(Keyword, Whitespace, Name.Function)),
            (r'(SINGLETON:)(\s+)(\S+)', bygroups(Keyword, Whitespace, Name.Class)),
            (r'SINGLETONS:', Keyword, 'classes'),

            # other syntax
            (r'(CONSTANT:|SYMBOL:|MAIN:|HELP:)(\s+)(\S+)',
             bygroups(Keyword, Whitespace, Name.Function)),
            (r'(SYMBOLS:)(\s+)', bygroups(Keyword, Whitespace), 'words'),
            (r'(SYNTAX:)(\s+)', bygroups(Keyword, Whitespace)),
            (r'(ALIEN:)(\s+)', bygroups(Keyword, Whitespace)),
            (r'(STRUCT:)(\s+)(\S+)', bygroups(Keyword, Whitespace, Name.Class)),
            (r'(FUNCTION:)(\s+)'
                r'(\S+)(\s+)(\S+)(\s+)'
                r'(\()(\s+)([^)]+)(\))(\s)',
             bygroups(Keyword.Namespace, Whitespace,
                 Text, Whitespace, Name.Function, Whitespace,
                 Punctuation, Whitespace, Text, Punctuation, Whitespace)),
            (r'(FUNCTION-ALIAS:)(\s+)'
                r'(\S+)(\s+)(\S+)(\s+)'
                r'(\S+)(\s+)'
                r'(\()(\s+)([^)]+)(\))(\s)',
             bygroups(Keyword.Namespace, Whitespace,
                 Text, Whitespace, Name.Function, Whitespace,
                 Name.Function, Whitespace,
                 Punctuation, Whitespace, Text, Punctuation, Whitespace)),

            # vocab.private
            (r'(<PRIVATE|PRIVATE>)(\s)', bygroups(Keyword.Namespace, Whitespace)),

            # strings
            (r'"""\s(?:.|\n)*?\s"""', String),
            (r'"(?:\\\\|\\"|[^"])*"', String),
            (r'(\S+")(\s+)((?:\\\\|\\"|[^"])*")',
                bygroups(String, Whitespace, String)),
            (r'(CHAR:)(\s+)(\\[\\abfnrstv]|[^\\]\S*)(\s)',
                bygroups(String.Char, Whitespace, String.Char, Whitespace)),

            # comments
            (r'!\s+.*$', Comment),
            (r'#!\s+.*$', Comment),
            (r'/\*\s+(?:.|\n)*?\s\*/', Comment),

            # boolean constants
            (r'[tf]\b', Name.Constant),

            # symbols and literals
            (r'[\\$]\s+\S+', Name.Constant),
            (r'M\\\s+\S+\s+\S+', Name.Constant),

            # numbers
            (r'[+-]?(?:[\d,]*\d)?\.(?:\d([\d,]*\d)?)?(?:[eE][+-]?\d+)?\s', Number),
            (r'[+-]?\d(?:[\d,]*\d)?(?:[eE][+-]?\d+)?\s', Number),
            (r'0x[a-fA-F\d](?:[a-fA-F\d,]*[a-fA-F\d])?(?:p\d([\d,]*\d)?)?\s', Number),
            (r'NAN:\s+[a-fA-F\d](?:[a-fA-F\d,]*[a-fA-F\d])?(?:p\d([\d,]*\d)?)?\s', Number),
            (r'0b[01]+\s', Number.Bin),
            (r'0o[0-7]+\s', Number.Oct),
            (r'(?:\d([\d,]*\d)?)?\+\d(?:[\d,]*\d)?/\d(?:[\d,]*\d)?\s', Number),
            (r'(?:\-\d([\d,]*\d)?)?\-\d(?:[\d,]*\d)?/\d(?:[\d,]*\d)?\s', Number),

            # keywords
            (r'(?:deprecated|final|foldable|flushable|inline|recursive)\s',
             Keyword),

            # builtins
            (builtin_kernel, bygroups(Name.Builtin, Whitespace)),
            (builtin_assocs, bygroups(Name.Builtin, Whitespace)),
            (builtin_combinators, bygroups(Name.Builtin, Whitespace)),
            (builtin_math, bygroups(Name.Builtin, Whitespace)),
            (builtin_sequences, bygroups(Name.Builtin, Whitespace)),
            (builtin_namespaces, bygroups(Name.Builtin, Whitespace)),
            (builtin_arrays, bygroups(Name.Builtin, Whitespace)),
            (builtin_io, bygroups(Name.Builtin, Whitespace)),
            (builtin_strings, bygroups(Name.Builtin, Whitespace)),
            (builtin_vectors, bygroups(Name.Builtin, Whitespace)),
            (builtin_continuations, bygroups(Name.Builtin, Whitespace)),

            # everything else is text
            (r'\S+', Text),
        ],
        'stackeffect': [
            (r'\s+', Whitespace),
            (r'(\()(\s+)', bygroups(Name.Function, Whitespace), 'stackeffect'),
            (r'(\))(\s+)', bygroups(Name.Function, Whitespace), '#pop'),
            (r'(--)(\s+)', bygroups(Name.Function, Whitespace)),
            (r'\S+', Name.Variable),
        ],
        'slots': [
            (r'\s+', Whitespace),
            (r'(;)(\s+)', bygroups(Keyword, Whitespace), '#pop'),
            (r'(\{)(\s+)(\S+)(\s+)([^}]+)(\s+)(\})(\s+)',
             bygroups(Text, Whitespace, Name.Variable, Whitespace,
                 Text, Whitespace, Text, Whitespace)),
            (r'\S+', Name.Variable),
        ],
        'vocabs': [
            (r'\s+', Whitespace),
            (r'(;)(\s+)', bygroups(Keyword, Whitespace), '#pop'),
            (r'\S+', Name.Namespace),
        ],
        'classes': [
            (r'\s+', Whitespace),
            (r'(;)(\s+)', bygroups(Keyword, Whitespace), '#pop'),
            (r'\S+', Name.Class),
        ],
        'words': [
            (r'\s+', Whitespace),
            (r'(;)(\s+)', bygroups(Keyword, Whitespace), '#pop'),
            (r'\S+', Name.Function),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\phix.py ===
"""
    pygments.lexers.phix
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Phix.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Whitespace

__all__ = ['PhixLexer']


class PhixLexer(RegexLexer):
    """
    Pygments Lexer for Phix files (.exw).
    See http://phix.x10.mx
    """

    name = 'Phix'
    url = 'http://phix.x10.mx'
    aliases = ['phix']
    filenames = ['*.exw']
    mimetypes = ['text/x-phix']
    version_added = '2.14'

    flags = re.MULTILINE    # nb: **NOT** re.DOTALL! (totally spanners comment handling)

    preproc = (
        'ifdef', 'elsifdef', 'elsedef'
    )
    # Note these lists are auto-generated by pwa/p2js.exw, when pwa\src\p2js_keywords.e (etc)
    #     change, though of course subsequent copy/commit/pull requests are all manual steps.
    types = (
        'string', 'nullable_string', 'atom_string', 'atom', 'bool', 'boolean',
        'cdCanvan', 'cdCanvas', 'complex', 'CURLcode', 'dictionary', 'int',
        'integer', 'Ihandle', 'Ihandles', 'Ihandln', 'mpfr', 'mpq', 'mpz',
        'mpz_or_string', 'number', 'rid_string', 'seq', 'sequence', 'timedate',
        'object'
    )
    keywords = (
        'abstract', 'class', 'continue', 'export', 'extends', 'nullable',
        'private', 'public', 'static', 'struct', 'trace',
        'and', 'break', 'by', 'case', 'catch', 'const', 'constant', 'debug',
        'default', 'do', 'else', 'elsif', 'end', 'enum', 'exit', 'fallthru',
        'fallthrough', 'for', 'forward', 'function', 'global', 'if', 'in',
        'include', 'js', 'javascript', 'javascript_semantics', 'let', 'not',
        'or', 'procedure', 'profile', 'profile_time', 'return', 'safe_mode',
        'switch', 'then', 'to', 'try', 'type', 'type_check', 'until', 'warning',
        'while', 'with', 'without', 'xor'
    )
    routines = (
        'abort', 'abs', 'adjust_timedate', 'and_bits', 'and_bitsu', 'apply',
        'append', 'arccos', 'arcsin', 'arctan', 'assert', 'atan2',
        'atom_to_float32', 'atom_to_float64', 'bankers_rounding', 'beep',
        'begins', 'binary_search', 'bits_to_int', 'bk_color', 'bytes_to_int',
        'call_func', 'call_proc', 'cdCanvasActivate', 'cdCanvasArc',
        'cdCanvasBegin', 'cdCanvasBox', 'cdCanvasChord', 'cdCanvasCircle',
        'cdCanvasClear', 'cdCanvasEnd', 'cdCanvasFlush', 'cdCanvasFont',
        'cdCanvasGetImageRGB', 'cdCanvasGetSize', 'cdCanvasGetTextAlignment',
        'cdCanvasGetTextSize', 'cdCanvasLine', 'cdCanvasMark',
        'cdCanvasMarkSize', 'cdCanvasMultiLineVectorText', 'cdCanvasPixel',
        'cdCanvasRect', 'cdCanvasRoundedBox', 'cdCanvasRoundedRect',
        'cdCanvasSector', 'cdCanvasSetAttribute', 'cdCanvasSetBackground',
        'cdCanvasSetFillMode', 'cdCanvasSetForeground',
        'cdCanvasSetInteriorStyle', 'cdCanvasSetLineStyle',
        'cdCanvasSetLineWidth', 'cdCanvasSetTextAlignment', 'cdCanvasText',
        'cdCanvasSetTextOrientation', 'cdCanvasGetTextOrientation',
        'cdCanvasVectorText', 'cdCanvasVectorTextDirection',
        'cdCanvasVectorTextSize', 'cdCanvasVertex', 'cdCreateCanvas',
        'cdDecodeAlpha', 'cdDecodeColor', 'cdDecodeColorAlpha', 'cdEncodeAlpha',
        'cdEncodeColor', 'cdEncodeColorAlpha', 'cdKillCanvas', 'cdVersion',
        'cdVersionDate', 'ceil', 'change_timezone', 'choose', 'clear_screen',
        'columnize', 'command_line', 'compare', 'complex_abs', 'complex_add',
        'complex_arg', 'complex_conjugate', 'complex_cos', 'complex_cosh',
        'complex_div', 'complex_exp', 'complex_imag', 'complex_inv',
        'complex_log', 'complex_mul', 'complex_neg', 'complex_new',
        'complex_norm', 'complex_power', 'complex_rho', 'complex_real',
        'complex_round', 'complex_sin', 'complex_sinh', 'complex_sprint',
        'complex_sqrt', 'complex_sub', 'complex_theta', 'concat', 'cos',
        'crash', 'custom_sort', 'date', 'day_of_week', 'day_of_year',
        'days_in_month', 'decode_base64', 'decode_flags', 'deep_copy', 'deld',
        'deserialize', 'destroy_dict', 'destroy_queue', 'destroy_stack',
        'dict_name', 'dict_size', 'elapsed', 'elapsed_short', 'encode_base64',
        'equal', 'even', 'exp', 'extract', 'factorial', 'factors',
        'file_size_k', 'find', 'find_all', 'find_any', 'find_replace', 'filter',
        'flatten', 'float32_to_atom', 'float64_to_atom', 'floor',
        'format_timedate', 'free_console', 'from_polar', 'gcd', 'get_file_base',
        'get_file_extension', 'get_file_name', 'get_file_name_and_path',
        'get_file_path', 'get_file_path_and_name', 'get_maxprime', 'get_prime',
        'get_primes', 'get_primes_le', 'get_proper_dir', 'get_proper_path',
        'get_rand', 'get_routine_info', 'get_test_abort', 'get_test_logfile',
        'get_test_pause', 'get_test_verbosity', 'get_tzid', 'getd', 'getdd',
        'getd_all_keys', 'getd_by_index', 'getd_index', 'getd_partial_key',
        'glAttachShader', 'glBindBuffer', 'glBindTexture', 'glBufferData',
        'glCanvasSpecialText', 'glClear', 'glClearColor', 'glColor',
        'glCompileShader', 'glCreateBuffer', 'glCreateProgram',
        'glCreateShader', 'glCreateTexture', 'glDeleteProgram',
        'glDeleteShader', 'glDrawArrays', 'glEnable',
        'glEnableVertexAttribArray', 'glFloat32Array', 'glInt32Array',
        'glFlush', 'glGetAttribLocation', 'glGetError', 'glGetProgramInfoLog',
        'glGetProgramParameter', 'glGetShaderInfoLog', 'glGetShaderParameter',
        'glGetUniformLocation', 'glLinkProgram', 'glLoadIdentity',
        'glMatrixMode', 'glOrtho', 'glRotatef', 'glShadeModel',
        'glShaderSource', 'glSimpleA7texcoords', 'glTexImage2Dc',
        'glTexParameteri', 'glTranslate', 'glUniform1f', 'glUniform1i',
        'glUniformMatrix4fv', 'glUseProgram', 'glVertex',
        'glVertexAttribPointer', 'glViewport', 'head', 'hsv_to_rgb', 'iff',
        'iif', 'include_file', 'incl0de_file', 'insert', 'instance',
        'int_to_bits', 'int_to_bytes', 'is_dict', 'is_integer', 's_leap_year',
        'is_prime', 'is_prime2', 'islower', 'isupper', 'Icallback',
        'iup_isdouble', 'iup_isprint', 'iup_XkeyBase', 'IupAppend', 'IupAlarm',
        'IupBackgroundBox', 'IupButton', 'IupCalendar', 'IupCanvas',
        'IupClipboard', 'IupClose', 'IupCloseOnEscape', 'IupControlsOpen',
        'IupDatePick', 'IupDestroy', 'IupDialog', 'IupDrawArc', 'IupDrawBegin',
        'IupDrawEnd', 'IupDrawGetSize', 'IupDrawGetTextSize', 'IupDrawLine',
        'IupDrawRectangle', 'IupDrawText', 'IupExpander', 'IupFill',
        'IupFlatLabel', 'IupFlatList', 'IupFlatTree', 'IupFlush', 'IupFrame',
        'IupGetAttribute', 'IupGetAttributeId', 'IupGetAttributePtr',
        'IupGetBrother', 'IupGetChild', 'IupGetChildCount', 'IupGetClassName',
        'IupGetDialog', 'IupGetDialogChild', 'IupGetDouble', 'IupGetFocus',
        'IupGetGlobal', 'IupGetGlobalInt', 'IupGetGlobalIntInt', 'IupGetInt',
        'IupGetInt2', 'IupGetIntId', 'IupGetIntInt', 'IupGetParent',
        'IupGLCanvas', 'IupGLCanvasOpen', 'IupGLMakeCurrent', 'IupGraph',
        'IupHbox', 'IupHide', 'IupImage', 'IupImageRGBA', 'IupItem',
        'iupKeyCodeToName', 'IupLabel', 'IupLink', 'IupList', 'IupMap',
        'IupMenu', 'IupMenuItem', 'IupMessage', 'IupMessageDlg', 'IupMultiBox',
        'IupMultiLine', 'IupNextField', 'IupNormaliser', 'IupOpen',
        'IupPlayInput', 'IupPopup', 'IupPreviousField', 'IupProgressBar',
        'IupRadio', 'IupRecordInput', 'IupRedraw', 'IupRefresh',
        'IupRefreshChildren', 'IupSeparator', 'IupSetAttribute',
        'IupSetAttributes', 'IupSetAttributeHandle', 'IupSetAttributeId',
        'IupSetAttributePtr', 'IupSetCallback', 'IupSetCallbacks',
        'IupSetDouble', 'IupSetFocus', 'IupSetGlobal', 'IupSetGlobalInt',
        'IupSetGlobalFunction', 'IupSetHandle', 'IupSetInt',
        'IupSetStrAttribute', 'IupSetStrGlobal', 'IupShow', 'IupShowXY',
        'IupSplit', 'IupStoreAttribute', 'IupSubmenu', 'IupTable',
        'IupTableClearSelected', 'IupTableClick_cb', 'IupTableGetSelected',
        'IupTableResize_cb', 'IupTableSetData', 'IupTabs', 'IupText',
        'IupTimer', 'IupToggle', 'IupTreeAddNodes', 'IupTreeView', 'IupUpdate',
        'IupValuator', 'IupVbox', 'join', 'join_by', 'join_path', 'k_perm',
        'largest', 'lcm', 'length', 'log', 'log10', 'log2', 'lower',
        'm4_crossProduct', 'm4_inverse', 'm4_lookAt', 'm4_multiply',
        'm4_normalize', 'm4_perspective', 'm4_subtractVectors', 'm4_xRotate',
        'm4_yRotate', 'machine_bits', 'machine_word', 'match', 'match_all',
        'match_replace', 'max', 'maxsq', 'min', 'minsq', 'mod', 'mpfr_add',
        'mpfr_ceil', 'mpfr_cmp', 'mpfr_cmp_si', 'mpfr_const_pi', 'mpfr_div',
        'mpfr_div_si', 'mpfr_div_z', 'mpfr_floor', 'mpfr_free', 'mpfr_get_d',
        'mpfr_get_default_precision', 'mpfr_get_default_rounding_mode',
        'mpfr_get_fixed', 'mpfr_get_precision', 'mpfr_get_si', 'mpfr_init',
        'mpfr_inits', 'mpfr_init_set', 'mpfr_init_set_q', 'mpfr_init_set_z',
        'mpfr_mul', 'mpfr_mul_si', 'mpfr_pow_si', 'mpfr_set', 'mpfr_set_d',
        'mpfr_set_default_precision', 'mpfr_set_default_rounding_mode',
        'mpfr_set_precision', 'mpfr_set_q', 'mpfr_set_si', 'mpfr_set_str',
        'mpfr_set_z', 'mpfr_si_div', 'mpfr_si_sub', 'mpfr_sqrt', 'mpfr_sub',
        'mpfr_sub_si', 'mpq_abs', 'mpq_add', 'mpq_add_si', 'mpq_canonicalize',
        'mpq_cmp', 'mpq_cmp_si', 'mpq_div', 'mpq_div_2exp', 'mpq_free',
        'mpq_get_den', 'mpq_get_num', 'mpq_get_str', 'mpq_init', 'mpq_init_set',
        'mpq_init_set_si', 'mpq_init_set_str', 'mpq_init_set_z', 'mpq_inits',
        'mpq_inv', 'mpq_mul', 'mpq_neg', 'mpq_set', 'mpq_set_si', 'mpq_set_str',
        'mpq_set_z', 'mpq_sub', 'mpz_abs', 'mpz_add', 'mpz_addmul',
        'mpz_addmul_ui', 'mpz_addmul_si', 'mpz_add_si', 'mpz_add_ui', 'mpz_and',
        'mpz_bin_uiui', 'mpz_cdiv_q', 'mpz_cmp', 'mpz_cmp_si', 'mpz_divexact',
        'mpz_divexact_ui', 'mpz_divisible_p', 'mpz_divisible_ui_p', 'mpz_even',
        'mpz_fac_ui', 'mpz_factorstring', 'mpz_fdiv_q', 'mpz_fdiv_q_2exp',
        'mpz_fdiv_q_ui', 'mpz_fdiv_qr', 'mpz_fdiv_r', 'mpz_fdiv_ui',
        'mpz_fib_ui', 'mpz_fib2_ui', 'mpz_fits_atom', 'mpz_fits_integer',
        'mpz_free', 'mpz_gcd', 'mpz_gcd_ui', 'mpz_get_atom', 'mpz_get_integer',
        'mpz_get_short_str', 'mpz_get_str', 'mpz_init', 'mpz_init_set',
        'mpz_inits', 'mpz_invert', 'mpz_lcm', 'mpz_lcm_ui', 'mpz_max',
        'mpz_min', 'mpz_mod', 'mpz_mod_ui', 'mpz_mul', 'mpz_mul_2exp',
        'mpz_mul_d', 'mpz_mul_si', 'mpz_neg', 'mpz_nthroot', 'mpz_odd',
        'mpz_pollard_rho', 'mpz_pow_ui', 'mpz_powm', 'mpz_powm_ui', 'mpz_prime',
        'mpz_prime_factors', 'mpz_prime_mr', 'mpz_rand', 'mpz_rand_ui',
        'mpz_re_compose', 'mpz_remove', 'mpz_scan0', 'mpz_scan1', 'mpz_set',
        'mpz_set_d', 'mpz_set_si', 'mpz_set_str', 'mpz_set_v', 'mpz_sign',
        'mpz_sizeinbase', 'mpz_sqrt', 'mpz_sub', 'mpz_sub_si', 'mpz_sub_ui',
        'mpz_si_sub', 'mpz_tdiv_q_2exp', 'mpz_tdiv_r_2exp', 'mpz_tstbit',
        'mpz_ui_pow_ui', 'mpz_xor', 'named_dict', 'new_dict', 'new_queue',
        'new_stack', 'not_bits', 'not_bitsu', 'odd', 'or_all', 'or_allu',
        'or_bits', 'or_bitsu', 'ord', 'ordinal', 'ordinant',
        'override_timezone', 'pad', 'pad_head', 'pad_tail', 'parse_date_string',
        'papply', 'peep', 'peepn', 'peep_dict', 'permute', 'permutes',
        'platform', 'pop', 'popn', 'pop_dict', 'power', 'pp', 'ppEx', 'ppExf',
        'ppf', 'ppOpt', 'pq_add', 'pq_destroy', 'pq_empty', 'pq_new', 'pq_peek',
        'pq_pop', 'pq_pop_data', 'pq_size', 'prepend', 'prime_factors',
        'printf', 'product', 'proper', 'push', 'pushn', 'putd', 'puts',
        'queue_empty', 'queue_size', 'rand', 'rand_range', 'reinstate',
        'remainder', 'remove', 'remove_all', 'repeat', 'repeatch', 'replace',
        'requires', 'reverse', 'rfind', 'rgb', 'rmatch', 'rmdr', 'rnd', 'round',
        'routine_id', 'scanf', 'serialize', 'series', 'set_rand',
        'set_test_abort', 'set_test_logfile', 'set_test_module',
        'set_test_pause', 'set_test_verbosity', 'set_timedate_formats',
        'set_timezone', 'setd', 'setd_default', 'shorten', 'sha256',
        'shift_bits', 'shuffle', 'sign', 'sin', 'smallest', 'sort',
        'sort_columns', 'speak', 'splice', 'split', 'split_any', 'split_by',
        'sprint', 'sprintf', 'sq_abs', 'sq_add', 'sq_and', 'sq_and_bits',
        'sq_arccos', 'sq_arcsin', 'sq_arctan', 'sq_atom', 'sq_ceil', 'sq_cmp',
        'sq_cos', 'sq_div', 'sq_even', 'sq_eq', 'sq_floor', 'sq_floor_div',
        'sq_ge', 'sq_gt', 'sq_int', 'sq_le', 'sq_log', 'sq_log10', 'sq_log2',
        'sq_lt', 'sq_max', 'sq_min', 'sq_mod', 'sq_mul', 'sq_ne', 'sq_not',
        'sq_not_bits', 'sq_odd', 'sq_or', 'sq_or_bits', 'sq_power', 'sq_rand',
        'sq_remainder', 'sq_rmdr', 'sq_rnd', 'sq_round', 'sq_seq', 'sq_sign',
        'sq_sin', 'sq_sqrt', 'sq_str', 'sq_sub', 'sq_tan', 'sq_trunc',
        'sq_uminus', 'sq_xor', 'sq_xor_bits', 'sqrt', 'square_free',
        'stack_empty', 'stack_size', 'substitute', 'substitute_all', 'sum',
        'tail', 'tan', 'test_equal', 'test_fail', 'test_false',
        'test_not_equal', 'test_pass', 'test_summary', 'test_true',
        'text_color', 'throw', 'time', 'timedate_diff', 'timedelta',
        'to_integer', 'to_number', 'to_rgb', 'to_string', 'traverse_dict',
        'traverse_dict_partial_key', 'trim', 'trim_head', 'trim_tail', 'trunc',
        'tagset', 'tagstart', 'typeof', 'unique', 'unix_dict', 'upper',
        'utf8_to_utf32', 'utf32_to_utf8', 'version', 'vlookup', 'vslice',
        'wglGetProcAddress', 'wildcard_file', 'wildcard_match', 'with_rho',
        'with_theta', 'xml_new_doc', 'xml_new_element', 'xml_set_attribute',
        'xml_sprint', 'xor_bits', 'xor_bitsu',
        'accept', 'allocate', 'allocate_string', 'allow_break', 'ARM',
        'atom_to_float80', 'c_func', 'c_proc', 'call_back', 'chdir',
        'check_break', 'clearDib', 'close', 'closesocket', 'console',
        'copy_file', 'create', 'create_directory', 'create_thread',
        'curl_easy_cleanup', 'curl_easy_get_file', 'curl_easy_init',
        'curl_easy_perform', 'curl_easy_perform_ex', 'curl_easy_setopt',
        'curl_easy_strerror', 'curl_global_cleanup', 'curl_global_init',
        'curl_slist_append', 'curl_slist_free_all', 'current_dir', 'cursor',
        'define_c_func', 'define_c_proc', 'delete', 'delete_cs', 'delete_file',
        'dir', 'DLL', 'drawDib', 'drawShadedPolygonToDib', 'ELF32', 'ELF64',
        'enter_cs', 'eval', 'exit_thread', 'free', 'file_exists', 'final',
        'float80_to_atom', 'format', 'get_bytes', 'get_file_date',
        'get_file_size', 'get_file_type', 'get_interpreter', 'get_key',
        'get_socket_error', 'get_text', 'get_thread_exitcode', 'get_thread_id',
        'getc', 'getenv', 'gets', 'getsockaddr', 'glBegin', 'glCallList',
        'glFrustum', 'glGenLists', 'glGetString', 'glLight', 'glMaterial',
        'glNewList', 'glNormal', 'glPopMatrix', 'glPushMatrix', 'glRotate',
        'glEnd', 'glEndList', 'glTexImage2D', 'goto', 'GUI', 'icons', 'ilASM',
        'include_files', 'include_paths', 'init_cs', 'ip_to_string',
        'IupConfig', 'IupConfigDialogClosed', 'IupConfigDialogShow',
        'IupConfigGetVariableInt', 'IupConfigLoad', 'IupConfigSave',
        'IupConfigSetVariableInt', 'IupExitLoop', 'IupFileDlg', 'IupFileList',
        'IupGLSwapBuffers', 'IupHelp', 'IupLoopStep', 'IupMainLoop',
        'IupNormalizer', 'IupPlot', 'IupPlotAdd', 'IupPlotBegin', 'IupPlotEnd',
        'IupPlotInsert', 'IupSaveImage', 'IupTreeGetUserId', 'IupUser',
        'IupVersion', 'IupVersionDate', 'IupVersionNumber', 'IupVersionShow',
        'killDib', 'leave_cs', 'listen', 'manifest', 'mem_copy', 'mem_set',
        'mpfr_gamma', 'mpfr_printf', 'mpfr_sprintf', 'mpz_export', 'mpz_import',
        'namespace', 'new', 'newDib', 'open', 'open_dll', 'PE32', 'PE64',
        'peek', 'peek_string', 'peek1s', 'peek1u', 'peek2s', 'peek2u', 'peek4s',
        'peek4u', 'peek8s', 'peek8u', 'peekNS', 'peekns', 'peeknu', 'poke',
        'poke2', 'poke4', 'poke8', 'pokeN', 'poke_string', 'poke_wstring',
        'position', 'progress', 'prompt_number', 'prompt_string', 'read_file',
        'read_lines', 'recv', 'resume_thread', 'seek', 'select', 'send',
        'setHandler', 'shutdown', 'sleep', 'SO', 'sockaddr_in', 'socket',
        'split_path', 'suspend_thread', 'system', 'system_exec', 'system_open',
        'system_wait', 'task_clock_start', 'task_clock_stop', 'task_create',
        'task_delay', 'task_list', 'task_schedule', 'task_self', 'task_status',
        'task_suspend', 'task_yield', 'thread_safe_string', 'try_cs',
        'utf8_to_utf16', 'utf16_to_utf8', 'utf16_to_utf32', 'utf32_to_utf16',
        'video_config', 'WSACleanup', 'wait_thread', 'walk_dir', 'where',
        'write_lines', 'wait_key'
    )
    constants = (
        'ANY_QUEUE', 'ASCENDING', 'BLACK', 'BLOCK_CURSOR', 'BLUE',
        'BRIGHT_CYAN', 'BRIGHT_BLUE', 'BRIGHT_GREEN', 'BRIGHT_MAGENTA',
        'BRIGHT_RED', 'BRIGHT_WHITE', 'BROWN', 'C_DWORD', 'C_INT', 'C_POINTER',
        'C_USHORT', 'C_WORD', 'CD_AMBER', 'CD_BLACK', 'CD_BLUE', 'CD_BOLD',
        'CD_BOLD_ITALIC', 'CD_BOX', 'CD_CENTER', 'CD_CIRCLE', 'CD_CLOSED_LINES',
        'CD_CONTINUOUS', 'CD_CUSTOM', 'CD_CYAN', 'CD_DARK_BLUE', 'CD_DARK_CYAN',
        'CD_DARK_GRAY', 'CD_DARK_GREY', 'CD_DARK_GREEN', 'CD_DARK_MAGENTA',
        'CD_DARK_RED', 'CD_DARK_YELLOW', 'CD_DASH_DOT', 'CD_DASH_DOT_DOT',
        'CD_DASHED', 'CD_DBUFFER', 'CD_DEG2RAD', 'CD_DIAMOND', 'CD_DOTTED',
        'CD_EAST', 'CD_EVENODD', 'CD_FILL', 'CD_GL', 'CD_GRAY', 'CD_GREY',
        'CD_GREEN', 'CD_HATCH', 'CD_HOLLOW', 'CD_HOLLOW_BOX',
        'CD_HOLLOW_CIRCLE', 'CD_HOLLOW_DIAMOND', 'CD_INDIGO', 'CD_ITALIC',
        'CD_IUP', 'CD_IUPDBUFFER', 'CD_LIGHT_BLUE', 'CD_LIGHT_GRAY',
        'CD_LIGHT_GREY', 'CD_LIGHT_GREEN', 'CD_LIGHT_PARCHMENT', 'CD_MAGENTA',
        'CD_NAVY', 'CD_NORTH', 'CD_NORTH_EAST', 'CD_NORTH_WEST', 'CD_OLIVE',
        'CD_OPEN_LINES', 'CD_ORANGE', 'CD_PARCHMENT', 'CD_PATTERN',
        'CD_PRINTER', 'CD_PURPLE', 'CD_PLAIN', 'CD_PLUS', 'CD_QUERY',
        'CD_RAD2DEG', 'CD_RED', 'CD_SILVER', 'CD_SOLID', 'CD_SOUTH_EAST',
        'CD_SOUTH_WEST', 'CD_STAR', 'CD_STIPPLE', 'CD_STRIKEOUT',
        'CD_UNDERLINE', 'CD_WEST', 'CD_WHITE', 'CD_WINDING', 'CD_VIOLET',
        'CD_X', 'CD_YELLOW', 'CURLE_OK', 'CURLOPT_MAIL_FROM',
        'CURLOPT_MAIL_RCPT', 'CURLOPT_PASSWORD', 'CURLOPT_READDATA',
        'CURLOPT_READFUNCTION', 'CURLOPT_SSL_VERIFYPEER',
        'CURLOPT_SSL_VERIFYHOST', 'CURLOPT_UPLOAD', 'CURLOPT_URL',
        'CURLOPT_USE_SSL', 'CURLOPT_USERNAME', 'CURLOPT_VERBOSE',
        'CURLOPT_WRITEFUNCTION', 'CURLUSESSL_ALL', 'CYAN', 'D_NAME',
        'D_ATTRIBUTES', 'D_SIZE', 'D_YEAR', 'D_MONTH', 'D_DAY', 'D_HOUR',
        'D_MINUTE', 'D_SECOND', 'D_CREATION', 'D_LASTACCESS', 'D_MODIFICATION',
        'DT_YEAR', 'DT_MONTH', 'DT_DAY', 'DT_HOUR', 'DT_MINUTE', 'DT_SECOND',
        'DT_DOW', 'DT_MSEC', 'DT_DOY', 'DT_GMT', 'EULER', 'E_CODE', 'E_ADDR',
        'E_LINE', 'E_RTN', 'E_NAME', 'E_FILE', 'E_PATH', 'E_USER', 'false',
        'False', 'FALSE', 'FIFO_QUEUE', 'FILETYPE_DIRECTORY', 'FILETYPE_FILE',
        'GET_EOF', 'GET_FAIL', 'GET_IGNORE', 'GET_SUCCESS',
        'GL_AMBIENT_AND_DIFFUSE', 'GL_ARRAY_BUFFER', 'GL_CLAMP',
        'GL_CLAMP_TO_BORDER', 'GL_CLAMP_TO_EDGE', 'GL_COLOR_BUFFER_BIT',
        'GL_COMPILE', 'GL_COMPILE_STATUS', 'GL_CULL_FACE',
        'GL_DEPTH_BUFFER_BIT', 'GL_DEPTH_TEST', 'GL_EXTENSIONS', 'GL_FLAT',
        'GL_FLOAT', 'GL_FRAGMENT_SHADER', 'GL_FRONT', 'GL_LIGHT0',
        'GL_LIGHTING', 'GL_LINEAR', 'GL_LINK_STATUS', 'GL_MODELVIEW',
        'GL_NEAREST', 'GL_NO_ERROR', 'GL_NORMALIZE', 'GL_POSITION',
        'GL_PROJECTION', 'GL_QUAD_STRIP', 'GL_QUADS', 'GL_RENDERER',
        'GL_REPEAT', 'GL_RGB', 'GL_RGBA', 'GL_SMOOTH', 'GL_STATIC_DRAW',
        'GL_TEXTURE_2D', 'GL_TEXTURE_MAG_FILTER', 'GL_TEXTURE_MIN_FILTER',
        'GL_TEXTURE_WRAP_S', 'GL_TEXTURE_WRAP_T', 'GL_TRIANGLES',
        'GL_UNSIGNED_BYTE', 'GL_VENDOR', 'GL_VERSION', 'GL_VERTEX_SHADER',
        'GRAY', 'GREEN', 'GT_LF_STRIPPED', 'GT_WHOLE_FILE', 'INVLN10',
        'IUP_CLOSE', 'IUP_CONTINUE', 'IUP_DEFAULT', 'IUP_BLACK', 'IUP_BLUE',
        'IUP_BUTTON1', 'IUP_BUTTON3', 'IUP_CENTER', 'IUP_CYAN', 'IUP_DARK_BLUE',
        'IUP_DARK_CYAN', 'IUP_DARK_GRAY', 'IUP_DARK_GREY', 'IUP_DARK_GREEN',
        'IUP_DARK_MAGENTA', 'IUP_DARK_RED', 'IUP_GRAY', 'IUP_GREY', 'IUP_GREEN',
        'IUP_IGNORE', 'IUP_INDIGO', 'IUP_MAGENTA', 'IUP_MASK_INT',
        'IUP_MASK_UINT', 'IUP_MOUSEPOS', 'IUP_NAVY', 'IUP_OLIVE', 'IUP_RECTEXT',
        'IUP_RED', 'IUP_LIGHT_BLUE', 'IUP_LIGHT_GRAY', 'IUP_LIGHT_GREY',
        'IUP_LIGHT_GREEN', 'IUP_ORANGE', 'IUP_PARCHMENT', 'IUP_PURPLE',
        'IUP_SILVER', 'IUP_TEAL', 'IUP_VIOLET', 'IUP_WHITE', 'IUP_YELLOW',
        'K_BS', 'K_cA', 'K_cC', 'K_cD', 'K_cF5', 'K_cK', 'K_cM', 'K_cN', 'K_cO',
        'K_cP', 'K_cR', 'K_cS', 'K_cT', 'K_cW', 'K_CR', 'K_DEL', 'K_DOWN',
        'K_END', 'K_ESC', 'K_F1', 'K_F2', 'K_F3', 'K_F4', 'K_F5', 'K_F6',
        'K_F7', 'K_F8', 'K_F9', 'K_F10', 'K_F11', 'K_F12', 'K_HOME', 'K_INS',
        'K_LEFT', 'K_MIDDLE', 'K_PGDN', 'K_PGUP', 'K_RIGHT', 'K_SP', 'K_TAB',
        'K_UP', 'K_h', 'K_i', 'K_j', 'K_p', 'K_r', 'K_s', 'JS', 'LIFO_QUEUE',
        'LINUX', 'MAX_HEAP', 'MAGENTA', 'MIN_HEAP', 'Nan', 'NO_CURSOR', 'null',
        'NULL', 'PI', 'pp_Ascii', 'pp_Brkt', 'pp_Date', 'pp_File', 'pp_FltFmt',
        'pp_Indent', 'pp_IntCh', 'pp_IntFmt', 'pp_Maxlen', 'pp_Nest',
        'pp_Pause', 'pp_Q22', 'pp_StrFmt', 'RED', 'SEEK_OK', 'SLASH',
        'TEST_ABORT', 'TEST_CRASH', 'TEST_PAUSE', 'TEST_PAUSE_FAIL',
        'TEST_QUIET', 'TEST_SHOW_ALL', 'TEST_SHOW_FAILED', 'TEST_SUMMARY',
        'true', 'True', 'TRUE', 'VC_SCRNLINES', 'WHITE', 'WINDOWS', 'YELLOW'
    )

    tokens = {
        'root': [
            (r"\s+", Whitespace),
            (r'/\*|--/\*|#\[', Comment.Multiline, 'comment'),
            (r'(?://|--|#!).*$', Comment.Single),
#Alt:
#           (r'//.*$|--.*$|#!.*$', Comment.Single),
            (r'"([^"\\]|\\.)*"', String.Other),
            (r'\'[^\']*\'', String.Other),
            (r'`[^`]*`', String.Other),

            (words(types, prefix=r'\b', suffix=r'\b'), Name.Function),
            (words(routines, prefix=r'\b', suffix=r'\b'), Name.Function),
            (words(preproc, prefix=r'\b', suffix=r'\b'), Keyword.Declaration),
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword.Declaration),
            (words(constants, prefix=r'\b', suffix=r'\b'), Name.Constant),
            # Aside: Phix only supports/uses the ascii/non-unicode tilde
            (r'!=|==|<<|>>|:=|[-~+/*%=<>&^|\.(){},?:\[\]$\\;#]', Operator),
            (r'[\w-]+', Text)
        ],
        'comment': [
            (r'[^*/#]+', Comment.Multiline),
            (r'/\*|#\[', Comment.Multiline, '#push'),
            (r'\*/|#\]', Comment.Multiline, '#pop'),
            (r'[*/#]', Comment.Multiline)
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\config.py ===
# config.py - deals with loading configuration information.

# Loads config data from a .cfg file.  Also caches the compiled
# data back into a .cfc file.

# If you are wondering how to avoid needing .cfg files (eg,
# if you are freezing Pythonwin etc) I suggest you create a
# .py file, and put the config info in a docstring.  Then
# pass a CStringIO file (rather than a filename) to the
# config manager.
import glob
import importlib.util
import marshal
import os
import stat
import sys
import traceback
import types

import pywin
import win32api

from . import keycodes

debugging = 0
if debugging:
    import win32traceutil  # Some trace statements fire before the interactive window is open.

    def trace(*args):
        sys.stderr.write(" ".join(map(str, args)) + "\n")

else:
    trace = lambda *args: None

compiled_config_version = 3


def split_line(line, lineno):
    comment_pos = line.find("#")
    if comment_pos >= 0:
        line = line[:comment_pos]
    sep_pos = line.rfind("=")
    if sep_pos == -1:
        if line.strip():
            print(f"Warning: Line {lineno}: {line!r} is an invalid entry")
            return None, None
        return "", ""
    return line[:sep_pos].strip(), line[sep_pos + 1 :].strip()


def get_section_header(line):
    # Returns the section if the line is a section header, else None
    if line[0] == "[":
        end = line.find("]")
        if end == -1:
            end = len(line)
        rc = line[1:end].lower()
        try:
            i = rc.index(":")
            return rc[:i], rc[i + 1 :]
        except ValueError:
            return rc, ""
    return None, None


def find_config_file(f):
    return os.path.join(next(iter(pywin.__path__)), f + ".cfg")


def find_config_files():
    return [
        os.path.split(x)[1]
        for x in [
            os.path.splitext(x)[0]
            for x in glob.glob(os.path.join(next(iter(pywin.__path__)), "*.cfg"))
        ]
    ]


class ConfigManager:
    def __init__(self, f):
        self.filename = "unknown"
        self.last_error = None
        self.key_to_events = {}
        b_close = False
        if hasattr(f, "readline"):
            fp = f
            self.filename = "<config string>"
            compiled_name = None
        else:
            try:
                f = find_config_file(f)
                src_stat = os.stat(f)
            except OSError:
                self.report_error("Config file '%s' not found" % f)
                return
            self.filename = f
            self.basename = os.path.basename(f)
            trace("Loading configuration", self.basename)
            compiled_name = os.path.splitext(f)[0] + ".cfc"
            try:
                cf = open(compiled_name, "rb")
                try:
                    ver = marshal.load(cf)
                    ok = compiled_config_version == ver
                    if ok:
                        kblayoutname = marshal.load(cf)
                        magic = marshal.load(cf)
                        size = marshal.load(cf)
                        mtime = marshal.load(cf)
                        if (
                            magic == importlib.util.MAGIC_NUMBER
                            and win32api.GetKeyboardLayoutName() == kblayoutname
                            and src_stat[stat.ST_MTIME] == mtime
                            and src_stat[stat.ST_SIZE] == size
                        ):
                            self.cache = marshal.load(cf)
                            trace("Configuration loaded cached", compiled_name)
                            return  # We are ready to roll!
                finally:
                    cf.close()
            except (OSError, EOFError):
                pass
            fp = open(f)
            b_close = True
        self.cache = {}
        lineno = 1
        line = fp.readline()
        while line:
            # Skip to the next section (maybe already there!)
            section, subsection = get_section_header(line)
            while line and section is None:
                line = fp.readline()
                if not line:
                    break
                lineno += 1
                section, subsection = get_section_header(line)
            if not line:
                break

            if section == "keys":
                line, lineno = self._load_keys(subsection, fp, lineno)
            elif section == "extensions":
                line, lineno = self._load_extensions(subsection, fp, lineno)
            elif section == "idle extensions":
                line, lineno = self._load_idle_extensions(subsection, fp, lineno)
            elif section == "general":
                line, lineno = self._load_general(subsection, fp, lineno)
            else:
                self.report_error(
                    f"Unrecognised section header '{section}:{subsection}'"
                )
                line = fp.readline()
                lineno += 1
        if b_close:
            fp.close()
        # Check critical data.
        if not self.cache.get("keys"):
            self.report_error("No keyboard definitions were loaded")
        if not self.last_error and compiled_name:
            try:
                cf = open(compiled_name, "wb")
                marshal.dump(compiled_config_version, cf)
                marshal.dump(win32api.GetKeyboardLayoutName(), cf)
                marshal.dump(importlib.util.MAGIC_NUMBER, cf)
                marshal.dump(src_stat[stat.ST_SIZE], cf)
                marshal.dump(src_stat[stat.ST_MTIME], cf)
                marshal.dump(self.cache, cf)
                cf.close()
            except (OSError, EOFError):
                pass  # Ignore errors - may be read only.

    def configure(self, editor, subsections=None):
        # Execute the extension code, and find any events.
        # First, we "recursively" connect any we are based on.
        if subsections is None:
            subsections = []
        subsections = [""] + subsections
        general = self.get_data("general")
        if general:
            parents = general.get("based on", [])
            for parent in parents:
                trace("Configuration based on", parent, "- loading.")
                parent = self.__class__(parent)
                parent.configure(editor, subsections)
                if parent.last_error:
                    self.report_error(parent.last_error)

        bindings = editor.bindings
        codeob = self.get_data("extension code")
        if codeob is not None:
            ns = {}
            try:
                exec(codeob, ns)
            except:
                traceback.print_exc()
                self.report_error("Executing extension code failed")
                ns = None
            if ns:
                num = 0
                for name, func in ns.items():
                    if isinstance(func, types.FunctionType) and name[:1] != "_":
                        bindings.bind(name, func)
                        num += 1
                trace("Configuration Extension code loaded", num, "events")
        # Load the idle extensions
        for subsection in subsections:
            for ext in self.get_data("idle extensions", {}).get(subsection, []):
                try:
                    editor.idle.IDLEExtension(ext)
                    trace("Loaded IDLE extension", ext)
                except:
                    self.report_error("Can not load the IDLE extension '%s'" % ext)

        # Now bind up the key-map (remembering a reverse map
        subsection_keymap = self.get_data("keys")
        num_bound = 0
        for subsection in subsections:
            keymap = subsection_keymap.get(subsection, {})
            bindings.update_keymap(keymap)
            num_bound += len(keymap)
        trace("Configuration bound", num_bound, "keys")

    def get_key_binding(self, event, subsections=None):
        if subsections is None:
            subsections = []
        subsections = [""] + subsections

        subsection_keymap = self.get_data("keys")
        for subsection in subsections:
            map = self.key_to_events.get(subsection)
            if map is None:  # Build it
                keymap = subsection_keymap.get(subsection, {})
                map = {map_event: key_info for key_info, map_event in keymap.items()}
                self.key_to_events[subsection] = map

            info = map.get(event)
            if info is not None:
                return keycodes.make_key_name(info[0], info[1])
        return None

    def report_error(self, msg):
        self.last_error = msg
        print(f"Error in {self.filename}: {msg}")

    def report_warning(self, msg):
        print(f"Warning in {self.filename}: {msg}")

    def _readline(self, fp, lineno, bStripComments=1):
        line = fp.readline()
        lineno += 1
        if line:
            bBreak = (
                get_section_header(line)[0] is not None
            )  # A new section is starting
            if bStripComments and not bBreak:
                pos = line.find("#")
                if pos >= 0:
                    line = line[:pos] + "\n"
        else:
            bBreak = 1
        return line, lineno, bBreak

    def get_data(self, name, default=None):
        return self.cache.get(name, default)

    def _save_data(self, name, data):
        self.cache[name] = data
        return data

    def _load_general(self, sub_section, fp, lineno):
        map = {}
        while 1:
            line, lineno, bBreak = self._readline(fp, lineno)
            if bBreak:
                break

            key, val = split_line(line, lineno)
            if not key:
                continue
            key = key.lower()
            l = map.get(key, [])
            l.append(val)
            map[key] = l
        self._save_data("general", map)
        return line, lineno

    def _load_keys(self, sub_section, fp, lineno):
        # Builds a nested dictionary of
        # (scancode, flags) = event_name
        main_map = self.get_data("keys", {})
        map = main_map.get(sub_section, {})
        while 1:
            line, lineno, bBreak = self._readline(fp, lineno)
            if bBreak:
                break

            key, event = split_line(line, lineno)
            if not event:
                continue
            sc, flag = keycodes.parse_key_name(key)
            if sc is None:
                self.report_warning("Line %d: Invalid key name '%s'" % (lineno, key))
            else:
                map[sc, flag] = event
        main_map[sub_section] = map
        self._save_data("keys", main_map)
        return line, lineno

    def _load_extensions(self, sub_section, fp, lineno):
        start_lineno = lineno
        lines = []
        while 1:
            line, lineno, bBreak = self._readline(fp, lineno, 0)
            if bBreak:
                break
            lines.append(line)
        try:
            c = compile(
                "\n" * start_lineno + "".join(lines),  # produces correct tracebacks
                self.filename,
                "exec",
            )
            self._save_data("extension code", c)
        except SyntaxError as details:
            errlineno = details.lineno + start_lineno
            # Should handle syntax errors better here, and offset the lineno.
            self.report_error(
                "Compiling extension code failed:\r\nFile: %s\r\nLine %d\r\n%s"
                % (details.filename, errlineno, details.msg)
            )
        return line, lineno

    def _load_idle_extensions(self, sub_section, fp, lineno):
        extension_map = self.get_data("idle extensions")
        if extension_map is None:
            extension_map = {}
        extensions = []
        while 1:
            line, lineno, bBreak = self._readline(fp, lineno)
            if bBreak:
                break
            line = line.strip()
            if line:
                extensions.append(line)
        extension_map[sub_section] = extensions
        self._save_data("idle extensions", extension_map)
        return line, lineno


def test():
    import time

    start = time.clock()
    f = "default"
    cm = ConfigManager(f)
    map = cm.get_data("keys")
    took = time.clock() - start
    print(f"Loaded {len(map)} items in {took:.4f} secs")


if __name__ == "__main__":
    test()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\lexers\__init__.py ===
"""
    pygments.lexers
    ~~~~~~~~~~~~~~~

    Pygments lexers.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pip._vendor.pygments.lexers._mapping import LEXERS
from pip._vendor.pygments.modeline import get_filetype_from_buffer
from pip._vendor.pygments.plugin import find_plugin_lexers
from pip._vendor.pygments.util import ClassNotFound, guess_decode

COMPAT = {
    'Python3Lexer': 'PythonLexer',
    'Python3TracebackLexer': 'PythonTracebackLexer',
    'LeanLexer': 'Lean3Lexer',
}

__all__ = ['get_lexer_by_name', 'get_lexer_for_filename', 'find_lexer_class',
           'guess_lexer', 'load_lexer_from_file'] + list(LEXERS) + list(COMPAT)

_lexer_cache = {}
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_lexers(module_name):
    """Load a lexer (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for lexer_name in mod.__all__:
        cls = getattr(mod, lexer_name)
        _lexer_cache[cls.name] = cls


def get_all_lexers(plugins=True):
    """Return a generator of tuples in the form ``(name, aliases,
    filenames, mimetypes)`` of all know lexers.

    If *plugins* is true (the default), plugin lexers supplied by entrypoints
    are also returned.  Otherwise, only builtin ones are considered.
    """
    for item in LEXERS.values():
        yield item[1:]
    if plugins:
        for lexer in find_plugin_lexers():
            yield lexer.name, lexer.aliases, lexer.filenames, lexer.mimetypes


def find_lexer_class(name):
    """
    Return the `Lexer` subclass that with the *name* attribute as given by
    the *name* argument.
    """
    if name in _lexer_cache:
        return _lexer_cache[name]
    # lookup builtin lexers
    for module_name, lname, aliases, _, _ in LEXERS.values():
        if name == lname:
            _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if cls.name == name:
            return cls


def find_lexer_class_by_name(_alias):
    """
    Return the `Lexer` subclass that has `alias` in its aliases list, without
    instantiating it.

    Like `get_lexer_by_name`, but does not instantiate the class.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.

    .. versionadded:: 2.2
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')
    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def get_lexer_by_name(_alias, **options):
    """
    Return an instance of a `Lexer` subclass that has `alias` in its
    aliases list. The lexer is given the `options` at its
    instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')

    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name](**options)
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls(**options)
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def load_lexer_from_file(filename, lexername="CustomLexer", **options):
    """Load a lexer from a file.

    This method expects a file located relative to the current working
    directory, which contains a Lexer class. By default, it expects the
    Lexer to be name CustomLexer; you can specify your own class name
    as the second argument to this function.

    Users should be very careful with the input, because this method
    is equivalent to running eval on the input file.

    Raises ClassNotFound if there are any problems importing the Lexer.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `lexername` from that namespace
        if lexername not in custom_namespace:
            raise ClassNotFound(f'no valid {lexername} class found in {filename}')
        lexer_class = custom_namespace[lexername]
        # And finally instantiate it with the options
        return lexer_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom lexer: {err}')


def find_lexer_class_for_filename(_fn, code=None):
    """Get a lexer for a filename.

    If multiple lexers match the filename pattern, use ``analyse_text()`` to
    figure out which one is more appropriate.

    Returns None if not found.
    """
    matches = []
    fn = basename(_fn)
    for modname, name, _, filenames, _ in LEXERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _lexer_cache:
                    _load_lexers(modname)
                matches.append((_lexer_cache[name], filename))
    for cls in find_plugin_lexers():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                matches.append((cls, filename))

    if isinstance(code, bytes):
        # decode it, since all analyse_text functions expect unicode
        code = guess_decode(code)

    def get_rating(info):
        cls, filename = info
        # explicit patterns get a bonus
        bonus = '*' not in filename and 0.5 or 0
        # The class _always_ defines analyse_text because it's included in
        # the Lexer class.  The default implementation returns None which
        # gets turned into 0.0.  Run scripts/detect_missing_analyse_text.py
        # to find lexers which need it overridden.
        if code:
            return cls.analyse_text(code) + bonus, cls.__name__
        return cls.priority + bonus, cls.__name__

    if matches:
        matches.sort(key=get_rating)
        # print "Possible lexers, after sort:", matches
        return matches[-1][0]


def get_lexer_for_filename(_fn, code=None, **options):
    """Get a lexer for a filename.

    Return a `Lexer` subclass instance that has a filename pattern
    matching `fn`. The lexer is given the `options` at its
    instantiation.

    Raise :exc:`pygments.util.ClassNotFound` if no lexer for that filename
    is found.

    If multiple lexers match the filename pattern, use their ``analyse_text()``
    methods to figure out which one is more appropriate.
    """
    res = find_lexer_class_for_filename(_fn, code)
    if not res:
        raise ClassNotFound(f'no lexer for filename {_fn!r} found')
    return res(**options)


def get_lexer_for_mimetype(_mime, **options):
    """
    Return a `Lexer` subclass instance that has `mime` in its mimetype
    list. The lexer is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if not lexer for that mimetype
    is found.
    """
    for modname, name, _, _, mimetypes in LEXERS.values():
        if _mime in mimetypes:
            if name not in _lexer_cache:
                _load_lexers(modname)
            return _lexer_cache[name](**options)
    for cls in find_plugin_lexers():
        if _mime in cls.mimetypes:
            return cls(**options)
    raise ClassNotFound(f'no lexer for mimetype {_mime!r} found')


def _iter_lexerclasses(plugins=True):
    """Return an iterator over all lexer classes."""
    for key in sorted(LEXERS):
        module_name, name = LEXERS[key][:2]
        if name not in _lexer_cache:
            _load_lexers(module_name)
        yield _lexer_cache[name]
    if plugins:
        yield from find_plugin_lexers()


def guess_lexer_for_filename(_fn, _text, **options):
    """
    As :func:`guess_lexer()`, but only lexers which have a pattern in `filenames`
    or `alias_filenames` that matches `filename` are taken into consideration.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """
    fn = basename(_fn)
    primary = {}
    matching_lexers = set()
    for lexer in _iter_lexerclasses():
        for filename in lexer.filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = True
        for filename in lexer.alias_filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = False
    if not matching_lexers:
        raise ClassNotFound(f'no lexer for filename {fn!r} found')
    if len(matching_lexers) == 1:
        return matching_lexers.pop()(**options)
    result = []
    for lexer in matching_lexers:
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        result.append((rv, lexer))

    def type_sort(t):
        # sort by:
        # - analyse score
        # - is primary filename pattern?
        # - priority
        # - last resort: class name
        return (t[0], primary[t[1]], t[1].priority, t[1].__name__)
    result.sort(key=type_sort)

    return result[-1][1](**options)


def guess_lexer(_text, **options):
    """
    Return a `Lexer` subclass instance that's guessed from the text in
    `text`. For that, the :meth:`.analyse_text()` method of every known lexer
    class is called with the text as argument, and the lexer which returned the
    highest value will be instantiated and returned.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """

    if not isinstance(_text, str):
        inencoding = options.get('inencoding', options.get('encoding'))
        if inencoding:
            _text = _text.decode(inencoding or 'utf8')
        else:
            _text, _ = guess_decode(_text)

    # try to get a vim modeline first
    ft = get_filetype_from_buffer(_text)

    if ft is not None:
        try:
            return get_lexer_by_name(ft, **options)
        except ClassNotFound:
            pass

    best_lexer = [0.0, None]
    for lexer in _iter_lexerclasses():
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        if rv > best_lexer[0]:
            best_lexer[:] = (rv, lexer)
    if not best_lexer[0] or best_lexer[1] is None:
        raise ClassNotFound('no lexer matching the text found')
    return best_lexer[1](**options)


class _automodule(types.ModuleType):
    """Automatically import lexers."""

    def __getattr__(self, name):
        info = LEXERS.get(name)
        if info:
            _load_lexers(info[0])
            cls = _lexer_cache[info[1]]
            setattr(self, name, cls)
            return cls
        if name in COMPAT:
            return getattr(self, COMPAT[name])
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types

# === NexusCore/openenv\Lib\site-packages\joblib\pool.py ===
"""Custom implementation of multiprocessing.Pool with custom pickler.

This module provides efficient ways of working with data stored in
shared memory with numpy.memmap arrays without inducing any memory
copy between the parent and child processes.

This module should not be imported if multiprocessing is not
available as it implements subclasses of multiprocessing Pool
that uses a custom alternative to SimpleQueue.

"""
# Author: Olivier Grisel <olivier.grisel@ensta.org>
# Copyright: 2012, Olivier Grisel
# License: BSD 3 clause

import copyreg
import sys
import warnings
from time import sleep

try:
    WindowsError
except NameError:
    WindowsError = type(None)

from io import BytesIO

# We need the class definition to derive from it, not the multiprocessing.Pool
# factory function
from multiprocessing.pool import Pool
from pickle import HIGHEST_PROTOCOL, Pickler

from ._memmapping_reducer import TemporaryResourcesManager, get_memmapping_reducers
from ._multiprocessing_helpers import assert_spawning, mp

try:
    import numpy as np
except ImportError:
    np = None


###############################################################################
# Enable custom pickling in Pool queues


class CustomizablePickler(Pickler):
    """Pickler that accepts custom reducers.

    TODO python2_drop : can this be simplified ?

    HIGHEST_PROTOCOL is selected by default as this pickler is used
    to pickle ephemeral datastructures for interprocess communication
    hence no backward compatibility is required.

    `reducers` is expected to be a dictionary with key/values
    being `(type, callable)` pairs where `callable` is a function that
    give an instance of `type` will return a tuple `(constructor,
    tuple_of_objects)` to rebuild an instance out of the pickled
    `tuple_of_objects` as would return a `__reduce__` method. See the
    standard library documentation on pickling for more details.

    """

    # We override the pure Python pickler as its the only way to be able to
    # customize the dispatch table without side effects in Python 2.7
    # to 3.2. For Python 3.3+ leverage the new dispatch_table
    # feature from https://bugs.python.org/issue14166 that makes it possible
    # to use the C implementation of the Pickler which is faster.

    def __init__(self, writer, reducers=None, protocol=HIGHEST_PROTOCOL):
        Pickler.__init__(self, writer, protocol=protocol)
        if reducers is None:
            reducers = {}
        if hasattr(Pickler, "dispatch"):
            # Make the dispatch registry an instance level attribute instead of
            # a reference to the class dictionary under Python 2
            self.dispatch = Pickler.dispatch.copy()
        else:
            # Under Python 3 initialize the dispatch table with a copy of the
            # default registry
            self.dispatch_table = copyreg.dispatch_table.copy()
        for type, reduce_func in reducers.items():
            self.register(type, reduce_func)

    def register(self, type, reduce_func):
        """Attach a reducer function to a given type in the dispatch table."""
        if hasattr(Pickler, "dispatch"):
            # Python 2 pickler dispatching is not explicitly customizable.
            # Let us use a closure to workaround this limitation.
            def dispatcher(self, obj):
                reduced = reduce_func(obj)
                self.save_reduce(obj=obj, *reduced)

            self.dispatch[type] = dispatcher
        else:
            self.dispatch_table[type] = reduce_func


class CustomizablePicklingQueue(object):
    """Locked Pipe implementation that uses a customizable pickler.

    This class is an alternative to the multiprocessing implementation
    of SimpleQueue in order to make it possible to pass custom
    pickling reducers, for instance to avoid memory copy when passing
    memory mapped datastructures.

    `reducers` is expected to be a dict with key / values being
    `(type, callable)` pairs where `callable` is a function that, given an
    instance of `type`, will return a tuple `(constructor, tuple_of_objects)`
    to rebuild an instance out of the pickled `tuple_of_objects` as would
    return a `__reduce__` method.

    See the standard library documentation on pickling for more details.
    """

    def __init__(self, context, reducers=None):
        self._reducers = reducers
        self._reader, self._writer = context.Pipe(duplex=False)
        self._rlock = context.Lock()
        if sys.platform == "win32":
            self._wlock = None
        else:
            self._wlock = context.Lock()
        self._make_methods()

    def __getstate__(self):
        assert_spawning(self)
        return (self._reader, self._writer, self._rlock, self._wlock, self._reducers)

    def __setstate__(self, state):
        (self._reader, self._writer, self._rlock, self._wlock, self._reducers) = state
        self._make_methods()

    def empty(self):
        return not self._reader.poll()

    def _make_methods(self):
        self._recv = recv = self._reader.recv
        racquire, rrelease = self._rlock.acquire, self._rlock.release

        def get():
            racquire()
            try:
                return recv()
            finally:
                rrelease()

        self.get = get

        if self._reducers:

            def send(obj):
                buffer = BytesIO()
                CustomizablePickler(buffer, self._reducers).dump(obj)
                self._writer.send_bytes(buffer.getvalue())

            self._send = send
        else:
            self._send = send = self._writer.send
        if self._wlock is None:
            # writes to a message oriented win32 pipe are atomic
            self.put = send
        else:
            wlock_acquire, wlock_release = (self._wlock.acquire, self._wlock.release)

            def put(obj):
                wlock_acquire()
                try:
                    return send(obj)
                finally:
                    wlock_release()

            self.put = put


class PicklingPool(Pool):
    """Pool implementation with customizable pickling reducers.

    This is useful to control how data is shipped between processes
    and makes it possible to use shared memory without useless
    copies induces by the default pickling methods of the original
    objects passed as arguments to dispatch.

    `forward_reducers` and `backward_reducers` are expected to be
    dictionaries with key/values being `(type, callable)` pairs where
    `callable` is a function that, given an instance of `type`, will return a
    tuple `(constructor, tuple_of_objects)` to rebuild an instance out of the
    pickled `tuple_of_objects` as would return a `__reduce__` method.
    See the standard library documentation about pickling for more details.

    """

    def __init__(
        self, processes=None, forward_reducers=None, backward_reducers=None, **kwargs
    ):
        if forward_reducers is None:
            forward_reducers = dict()
        if backward_reducers is None:
            backward_reducers = dict()
        self._forward_reducers = forward_reducers
        self._backward_reducers = backward_reducers
        poolargs = dict(processes=processes)
        poolargs.update(kwargs)
        super(PicklingPool, self).__init__(**poolargs)

    def _setup_queues(self):
        context = getattr(self, "_ctx", mp)
        self._inqueue = CustomizablePicklingQueue(context, self._forward_reducers)
        self._outqueue = CustomizablePicklingQueue(context, self._backward_reducers)
        self._quick_put = self._inqueue._send
        self._quick_get = self._outqueue._recv


class MemmappingPool(PicklingPool):
    """Process pool that shares large arrays to avoid memory copy.

    This drop-in replacement for `multiprocessing.pool.Pool` makes
    it possible to work efficiently with shared memory in a numpy
    context.

    Existing instances of numpy.memmap are preserved: the child
    suprocesses will have access to the same shared memory in the
    original mode except for the 'w+' mode that is automatically
    transformed as 'r+' to avoid zeroing the original data upon
    instantiation.

    Furthermore large arrays from the parent process are automatically
    dumped to a temporary folder on the filesystem such as child
    processes to access their content via memmapping (file system
    backed shared memory).

    Note: it is important to call the terminate method to collect
    the temporary folder used by the pool.

    Parameters
    ----------
    processes: int, optional
        Number of worker processes running concurrently in the pool.
    initializer: callable, optional
        Callable executed on worker process creation.
    initargs: tuple, optional
        Arguments passed to the initializer callable.
    temp_folder: (str, callable) optional
        If str:
          Folder to be used by the pool for memmapping large arrays
          for sharing memory with worker processes. If None, this will try in
          order:
          - a folder pointed by the JOBLIB_TEMP_FOLDER environment variable,
          - /dev/shm if the folder exists and is writable: this is a RAMdisk
            filesystem available by default on modern Linux distributions,
          - the default system temporary folder that can be overridden
            with TMP, TMPDIR or TEMP environment variables, typically /tmp
            under Unix operating systems.
        if callable:
            An callable in charge of dynamically resolving a temporary folder
            for memmapping large arrays.
    max_nbytes int or None, optional, 1e6 by default
        Threshold on the size of arrays passed to the workers that
        triggers automated memory mapping in temp_folder.
        Use None to disable memmapping of large arrays.
    mmap_mode: {'r+', 'r', 'w+', 'c'}
        Memmapping mode for numpy arrays passed to workers.
        See 'max_nbytes' parameter documentation for more details.
    forward_reducers: dictionary, optional
        Reducers used to pickle objects passed from main process to worker
        processes: see below.
    backward_reducers: dictionary, optional
        Reducers used to pickle return values from workers back to the
        main process.
    verbose: int, optional
        Make it possible to monitor how the communication of numpy arrays
        with the subprocess is handled (pickling or memmapping)
    prewarm: bool or str, optional, "auto" by default.
        If True, force a read on newly memmapped array to make sure that OS
        pre-cache it in memory. This can be useful to avoid concurrent disk
        access when the same data array is passed to different worker
        processes. If "auto" (by default), prewarm is set to True, unless the
        Linux shared memory partition /dev/shm is available and used as temp
        folder.

    `forward_reducers` and `backward_reducers` are expected to be
    dictionaries with key/values being `(type, callable)` pairs where
    `callable` is a function that give an instance of `type` will return
    a tuple `(constructor, tuple_of_objects)` to rebuild an instance out
    of the pickled `tuple_of_objects` as would return a `__reduce__`
    method. See the standard library documentation on pickling for more
    details.

    """

    def __init__(
        self,
        processes=None,
        temp_folder=None,
        max_nbytes=1e6,
        mmap_mode="r",
        forward_reducers=None,
        backward_reducers=None,
        verbose=0,
        prewarm=False,
        **kwargs,
    ):
        manager = TemporaryResourcesManager(temp_folder)
        self._temp_folder_manager = manager

        # The usage of a temp_folder_resolver over a simple temp_folder is
        # superfluous for multiprocessing pools, as they don't get reused, see
        # get_memmapping_executor for more details. We still use it for code
        # simplicity.
        forward_reducers, backward_reducers = get_memmapping_reducers(
            temp_folder_resolver=manager.resolve_temp_folder_name,
            max_nbytes=max_nbytes,
            mmap_mode=mmap_mode,
            forward_reducers=forward_reducers,
            backward_reducers=backward_reducers,
            verbose=verbose,
            unlink_on_gc_collect=False,
            prewarm=prewarm,
        )

        poolargs = dict(
            processes=processes,
            forward_reducers=forward_reducers,
            backward_reducers=backward_reducers,
        )
        poolargs.update(kwargs)
        super(MemmappingPool, self).__init__(**poolargs)

    def terminate(self):
        n_retries = 10
        for i in range(n_retries):
            try:
                super(MemmappingPool, self).terminate()
                break
            except OSError as e:
                if isinstance(e, WindowsError):
                    # Workaround  occasional "[Error 5] Access is denied" issue
                    # when trying to terminate a process under windows.
                    sleep(0.1)
                    if i + 1 == n_retries:
                        warnings.warn(
                            "Failed to terminate worker processes in"
                            " multiprocessing pool: %r" % e
                        )

        # Clean up the temporary resources as the workers should now be off.
        self._temp_folder_manager._clean_temporary_resources()

    @property
    def _temp_folder(self):
        # Legacy property in tests. could be removed if we refactored the
        # memmapping tests. SHOULD ONLY BE USED IN TESTS!
        # We cache this property because it is called late in the tests - at
        # this point, all context have been unregistered, and
        # resolve_temp_folder_name raises an error.
        if getattr(self, "_cached_temp_folder", None) is not None:
            return self._cached_temp_folder
        else:
            self._cached_temp_folder = (
                self._temp_folder_manager.resolve_temp_folder_name()
            )  # noqa
            return self._cached_temp_folder

# === NexusCore/openenv\Lib\site-packages\packaging\markers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import operator
import os
import platform
import sys
from typing import AbstractSet, Any, Callable, Literal, TypedDict, Union, cast

from ._parser import MarkerAtom, MarkerList, Op, Value, Variable
from ._parser import parse_marker as _parse_marker
from ._tokenizer import ParserSyntaxError
from .specifiers import InvalidSpecifier, Specifier
from .utils import canonicalize_name

__all__ = [
    "EvaluateContext",
    "InvalidMarker",
    "Marker",
    "UndefinedComparison",
    "UndefinedEnvironmentName",
    "default_environment",
]

Operator = Callable[[str, Union[str, AbstractSet[str]]], bool]
EvaluateContext = Literal["metadata", "lock_file", "requirement"]
MARKERS_ALLOWING_SET = {"extras", "dependency_groups"}


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


class Environment(TypedDict):
    implementation_name: str
    """The implementation's identifier, e.g. ``'cpython'``."""

    implementation_version: str
    """
    The implementation's version, e.g. ``'3.13.0a2'`` for CPython 3.13.0a2, or
    ``'7.3.13'`` for PyPy3.10 v7.3.13.
    """

    os_name: str
    """
    The value of :py:data:`os.name`. The name of the operating system dependent module
    imported, e.g. ``'posix'``.
    """

    platform_machine: str
    """
    Returns the machine type, e.g. ``'i386'``.

    An empty string if the value cannot be determined.
    """

    platform_release: str
    """
    The system's release, e.g. ``'2.2.0'`` or ``'NT'``.

    An empty string if the value cannot be determined.
    """

    platform_system: str
    """
    The system/OS name, e.g. ``'Linux'``, ``'Windows'`` or ``'Java'``.

    An empty string if the value cannot be determined.
    """

    platform_version: str
    """
    The system's release version, e.g. ``'#3 on degas'``.

    An empty string if the value cannot be determined.
    """

    python_full_version: str
    """
    The Python version as string ``'major.minor.patchlevel'``.

    Note that unlike the Python :py:data:`sys.version`, this value will always include
    the patchlevel (it defaults to 0).
    """

    platform_python_implementation: str
    """
    A string identifying the Python implementation, e.g. ``'CPython'``.
    """

    python_version: str
    """The Python version as string ``'major.minor'``."""

    sys_platform: str
    """
    This string contains a platform identifier that can be used to append
    platform-specific components to :py:data:`sys.path`, for instance.

    For Unix systems, except on Linux and AIX, this is the lowercased OS name as
    returned by ``uname -s`` with the first part of the version as returned by
    ``uname -r`` appended, e.g. ``'sunos5'`` or ``'freebsd8'``, at the time when Python
    was built.
    """


def _normalize_extra_values(results: Any) -> Any:
    """
    Normalize extra values.
    """
    if isinstance(results[0], tuple):
        lhs, op, rhs = results[0]
        if isinstance(lhs, Variable) and lhs.value == "extra":
            normalized_extra = canonicalize_name(rhs.value)
            rhs = Value(normalized_extra)
        elif isinstance(rhs, Variable) and rhs.value == "extra":
            normalized_extra = canonicalize_name(lhs.value)
            lhs = Value(normalized_extra)
        results[0] = lhs, op, rhs
    return results


def _format_marker(
    marker: list[str] | MarkerAtom | str, first: bool | None = True
) -> str:
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


_operators: dict[str, Operator] = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs: str, op: Op, rhs: str | AbstractSet[str]) -> bool:
    if isinstance(rhs, str):
        try:
            spec = Specifier("".join([op.serialize(), rhs]))
        except InvalidSpecifier:
            pass
        else:
            return spec.contains(lhs, prereleases=True)

    oper: Operator | None = _operators.get(op.serialize())
    if oper is None:
        raise UndefinedComparison(f"Undefined {op!r} on {lhs!r} and {rhs!r}.")

    return oper(lhs, rhs)


def _normalize(
    lhs: str, rhs: str | AbstractSet[str], key: str
) -> tuple[str, str | AbstractSet[str]]:
    # PEP 685 – Comparison of extra names for optional distribution dependencies
    # https://peps.python.org/pep-0685/
    # > When comparing extra names, tools MUST normalize the names being
    # > compared using the semantics outlined in PEP 503 for names
    if key == "extra":
        assert isinstance(rhs, str), "extra value must be a string"
        return (canonicalize_name(lhs), canonicalize_name(rhs))
    if key in MARKERS_ALLOWING_SET:
        if isinstance(rhs, str):  # pragma: no cover
            return (canonicalize_name(lhs), canonicalize_name(rhs))
        else:
            return (canonicalize_name(lhs), {canonicalize_name(v) for v in rhs})

    # other environment markers don't have such standards
    return lhs, rhs


def _evaluate_markers(
    markers: MarkerList, environment: dict[str, str | AbstractSet[str]]
) -> bool:
    groups: list[list[bool]] = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, str))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                environment_key = lhs.value
                lhs_value = environment[environment_key]
                rhs_value = rhs.value
            else:
                lhs_value = lhs.value
                environment_key = rhs.value
                rhs_value = environment[environment_key]
            assert isinstance(lhs_value, str), "lhs must be a string"
            lhs_value, rhs_value = _normalize(lhs_value, rhs_value, key=environment_key)
            groups[-1].append(_eval_op(lhs_value, op, rhs_value))
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def format_full_version(info: sys._version_info) -> str:
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> Environment:
    iver = format_full_version(sys.implementation.version)
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


class Marker:
    def __init__(self, marker: str) -> None:
        # Note: We create a Marker object without calling this constructor in
        #       packaging.requirements.Requirement. If any additional logic is
        #       added here, make sure to mirror/adapt Requirement.
        try:
            self._markers = _normalize_extra_values(_parse_marker(marker))
            # The attribute `_markers` can be described in terms of a recursive type:
            # MarkerList = List[Union[Tuple[Node, ...], str, MarkerList]]
            #
            # For example, the following expression:
            # python_version > "3.6" or (python_version == "3.6" and os_name == "unix")
            #
            # is parsed into:
            # [
            #     (<Variable('python_version')>, <Op('>')>, <Value('3.6')>),
            #     'and',
            #     [
            #         (<Variable('python_version')>, <Op('==')>, <Value('3.6')>),
            #         'or',
            #         (<Variable('os_name')>, <Op('==')>, <Value('unix')>)
            #     ]
            # ]
        except ParserSyntaxError as e:
            raise InvalidMarker(str(e)) from e

    def __str__(self) -> str:
        return _format_marker(self._markers)

    def __repr__(self) -> str:
        return f"<Marker('{self}')>"

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, str(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Marker):
            return NotImplemented

        return str(self) == str(other)

    def evaluate(
        self,
        environment: dict[str, str] | None = None,
        context: EvaluateContext = "metadata",
    ) -> bool:
        """Evaluate a marker.

        Return the boolean from evaluating the given marker against the
        environment. environment is an optional argument to override all or
        part of the determined environment. The *context* parameter specifies what
        context the markers are being evaluated for, which influences what markers
        are considered valid. Acceptable values are "metadata" (for core metadata;
        default), "lock_file", and "requirement" (i.e. all other situations).

        The environment is determined from the current Python process.
        """
        current_environment = cast(
            "dict[str, str | AbstractSet[str]]", default_environment()
        )
        if context == "lock_file":
            current_environment.update(
                extras=frozenset(), dependency_groups=frozenset()
            )
        elif context == "metadata":
            current_environment["extra"] = ""
        if environment is not None:
            current_environment.update(environment)
            # The API used to allow setting extra to None. We need to handle this
            # case for backwards compatibility.
            if "extra" in current_environment and current_environment["extra"] is None:
                current_environment["extra"] = ""

        return _evaluate_markers(
            self._markers, _repair_python_full_version(current_environment)
        )


def _repair_python_full_version(
    env: dict[str, str | AbstractSet[str]],
) -> dict[str, str | AbstractSet[str]]:
    """
    Work around platform.python_version() returning something that is not PEP 440
    compliant for non-tagged Python builds.
    """
    python_full_version = cast(str, env["python_full_version"])
    if python_full_version.endswith("+"):
        env["python_full_version"] = f"{python_full_version}local"
    return env

# === NexusCore/openenv\Lib\site-packages\pyparsing\testing.py ===
# testing.py

from contextlib import contextmanager
import re
import typing


from .core import (
    ParserElement,
    ParseException,
    Keyword,
    __diag__,
    __compat__,
)


class pyparsing_test:
    """
    namespace class for classes useful in writing unit tests
    """

    class reset_pyparsing_context:
        """
        Context manager to be used when writing unit tests that modify pyparsing config values:
        - packrat parsing
        - bounded recursion parsing
        - default whitespace characters.
        - default keyword characters
        - literal string auto-conversion class
        - __diag__ settings

        Example::

            with reset_pyparsing_context():
                # test that literals used to construct a grammar are automatically suppressed
                ParserElement.inlineLiteralsUsing(Suppress)

                term = Word(alphas) | Word(nums)
                group = Group('(' + term[...] + ')')

                # assert that the '()' characters are not included in the parsed tokens
                self.assertParseAndCheckList(group, "(abc 123 def)", ['abc', '123', 'def'])

            # after exiting context manager, literals are converted to Literal expressions again
        """

        def __init__(self):
            self._save_context = {}

        def save(self):
            self._save_context["default_whitespace"] = ParserElement.DEFAULT_WHITE_CHARS
            self._save_context["default_keyword_chars"] = Keyword.DEFAULT_KEYWORD_CHARS

            self._save_context["literal_string_class"] = (
                ParserElement._literalStringClass
            )

            self._save_context["verbose_stacktrace"] = ParserElement.verbose_stacktrace

            self._save_context["packrat_enabled"] = ParserElement._packratEnabled
            if ParserElement._packratEnabled:
                self._save_context["packrat_cache_size"] = (
                    ParserElement.packrat_cache.size
                )
            else:
                self._save_context["packrat_cache_size"] = None
            self._save_context["packrat_parse"] = ParserElement._parse
            self._save_context["recursion_enabled"] = (
                ParserElement._left_recursion_enabled
            )

            self._save_context["__diag__"] = {
                name: getattr(__diag__, name) for name in __diag__._all_names
            }

            self._save_context["__compat__"] = {
                "collect_all_And_tokens": __compat__.collect_all_And_tokens
            }

            return self

        def restore(self):
            # reset pyparsing global state
            if (
                ParserElement.DEFAULT_WHITE_CHARS
                != self._save_context["default_whitespace"]
            ):
                ParserElement.set_default_whitespace_chars(
                    self._save_context["default_whitespace"]
                )

            ParserElement.verbose_stacktrace = self._save_context["verbose_stacktrace"]

            Keyword.DEFAULT_KEYWORD_CHARS = self._save_context["default_keyword_chars"]
            ParserElement.inlineLiteralsUsing(
                self._save_context["literal_string_class"]
            )

            for name, value in self._save_context["__diag__"].items():
                (__diag__.enable if value else __diag__.disable)(name)

            ParserElement._packratEnabled = False
            if self._save_context["packrat_enabled"]:
                ParserElement.enable_packrat(self._save_context["packrat_cache_size"])
            else:
                ParserElement._parse = self._save_context["packrat_parse"]
            ParserElement._left_recursion_enabled = self._save_context[
                "recursion_enabled"
            ]

            __compat__.collect_all_And_tokens = self._save_context["__compat__"]

            return self

        def copy(self):
            ret = type(self)()
            ret._save_context.update(self._save_context)
            return ret

        def __enter__(self):
            return self.save()

        def __exit__(self, *args):
            self.restore()

    class TestParseResultsAsserts:
        """
        A mixin class to add parse results assertion methods to normal unittest.TestCase classes.
        """

        def assertParseResultsEquals(
            self, result, expected_list=None, expected_dict=None, msg=None
        ):
            """
            Unit test assertion to compare a :class:`ParseResults` object with an optional ``expected_list``,
            and compare any defined results names with an optional ``expected_dict``.
            """
            if expected_list is not None:
                self.assertEqual(expected_list, result.as_list(), msg=msg)
            if expected_dict is not None:
                self.assertEqual(expected_dict, result.as_dict(), msg=msg)

        def assertParseAndCheckList(
            self, expr, test_string, expected_list, msg=None, verbose=True
        ):
            """
            Convenience wrapper assert to test a parser element and input string, and assert that
            the resulting ``ParseResults.asList()`` is equal to the ``expected_list``.
            """
            result = expr.parse_string(test_string, parse_all=True)
            if verbose:
                print(result.dump())
            else:
                print(result.as_list())
            self.assertParseResultsEquals(result, expected_list=expected_list, msg=msg)

        def assertParseAndCheckDict(
            self, expr, test_string, expected_dict, msg=None, verbose=True
        ):
            """
            Convenience wrapper assert to test a parser element and input string, and assert that
            the resulting ``ParseResults.asDict()`` is equal to the ``expected_dict``.
            """
            result = expr.parse_string(test_string, parseAll=True)
            if verbose:
                print(result.dump())
            else:
                print(result.as_list())
            self.assertParseResultsEquals(result, expected_dict=expected_dict, msg=msg)

        def assertRunTestResults(
            self, run_tests_report, expected_parse_results=None, msg=None
        ):
            """
            Unit test assertion to evaluate output of ``ParserElement.runTests()``. If a list of
            list-dict tuples is given as the ``expected_parse_results`` argument, then these are zipped
            with the report tuples returned by ``runTests`` and evaluated using ``assertParseResultsEquals``.
            Finally, asserts that the overall ``runTests()`` success value is ``True``.

            :param run_tests_report: tuple(bool, [tuple(str, ParseResults or Exception)]) returned from runTests
            :param expected_parse_results (optional): [tuple(str, list, dict, Exception)]
            """
            run_test_success, run_test_results = run_tests_report

            if expected_parse_results is None:
                self.assertTrue(
                    run_test_success, msg=msg if msg is not None else "failed runTests"
                )
                return

            merged = [
                (*rpt, expected)
                for rpt, expected in zip(run_test_results, expected_parse_results)
            ]
            for test_string, result, expected in merged:
                # expected should be a tuple containing a list and/or a dict or an exception,
                # and optional failure message string
                # an empty tuple will skip any result validation
                fail_msg = next((exp for exp in expected if isinstance(exp, str)), None)
                expected_exception = next(
                    (
                        exp
                        for exp in expected
                        if isinstance(exp, type) and issubclass(exp, Exception)
                    ),
                    None,
                )
                if expected_exception is not None:
                    with self.assertRaises(
                        expected_exception=expected_exception, msg=fail_msg or msg
                    ):
                        if isinstance(result, Exception):
                            raise result
                else:
                    expected_list = next(
                        (exp for exp in expected if isinstance(exp, list)), None
                    )
                    expected_dict = next(
                        (exp for exp in expected if isinstance(exp, dict)), None
                    )
                    if (expected_list, expected_dict) != (None, None):
                        self.assertParseResultsEquals(
                            result,
                            expected_list=expected_list,
                            expected_dict=expected_dict,
                            msg=fail_msg or msg,
                        )
                    else:
                        # warning here maybe?
                        print(f"no validation for {test_string!r}")

            # do this last, in case some specific test results can be reported instead
            self.assertTrue(
                run_test_success, msg=msg if msg is not None else "failed runTests"
            )

        @contextmanager
        def assertRaisesParseException(
            self, exc_type=ParseException, expected_msg=None, msg=None
        ):
            if expected_msg is not None:
                if isinstance(expected_msg, str):
                    expected_msg = re.escape(expected_msg)
                with self.assertRaisesRegex(exc_type, expected_msg, msg=msg) as ctx:
                    yield ctx

            else:
                with self.assertRaises(exc_type, msg=msg) as ctx:
                    yield ctx

    @staticmethod
    def with_line_numbers(
        s: str,
        start_line: typing.Optional[int] = None,
        end_line: typing.Optional[int] = None,
        expand_tabs: bool = True,
        eol_mark: str = "|",
        mark_spaces: typing.Optional[str] = None,
        mark_control: typing.Optional[str] = None,
        *,
        indent: typing.Union[str, int] = "",
        base_1: bool = True,
    ) -> str:
        """
        Helpful method for debugging a parser - prints a string with line and column numbers.
        (Line and column numbers are 1-based by default - if debugging a parse action,
        pass base_1=False, to correspond to the loc value passed to the parse action.)

        :param s: tuple(bool, str - string to be printed with line and column numbers
        :param start_line: int - (optional) starting line number in s to print (default=1)
        :param end_line: int - (optional) ending line number in s to print (default=len(s))
        :param expand_tabs: bool - (optional) expand tabs to spaces, to match the pyparsing default
        :param eol_mark: str - (optional) string to mark the end of lines, helps visualize trailing spaces (default="|")
        :param mark_spaces: str - (optional) special character to display in place of spaces
        :param mark_control: str - (optional) convert non-printing control characters to a placeholding
                                 character; valid values:
                                 - "unicode" - replaces control chars with Unicode symbols, such as "␍" and "␊"
                                 - any single character string - replace control characters with given string
                                 - None (default) - string is displayed as-is
        :param indent: str | int - (optional) string to indent with line and column numbers; if an int
                                   is passed, converted to " " * indent
        :param base_1: bool - (optional) whether to label string using base 1; if False, string will be
                              labeled based at 0 (default=True)

        :return: str - input string with leading line numbers and column number headers
        """
        if expand_tabs:
            s = s.expandtabs()
        if isinstance(indent, int):
            indent = " " * indent
        indent = indent.expandtabs()
        if mark_control is not None:
            mark_control = typing.cast(str, mark_control)
            if mark_control == "unicode":
                transtable_map = {
                    c: u for c, u in zip(range(0, 33), range(0x2400, 0x2433))
                }
                transtable_map[127] = 0x2421
                tbl = str.maketrans(transtable_map)
                eol_mark = ""
            else:
                ord_mark_control = ord(mark_control)
                tbl = str.maketrans(
                    {c: ord_mark_control for c in list(range(0, 32)) + [127]}
                )
            s = s.translate(tbl)
        if mark_spaces is not None and mark_spaces != " ":
            if mark_spaces == "unicode":
                tbl = str.maketrans({9: 0x2409, 32: 0x2423})
                s = s.translate(tbl)
            else:
                s = s.replace(" ", mark_spaces)
        if start_line is None:
            start_line = 0
        if end_line is None:
            end_line = len(s)
        end_line = min(end_line, len(s))
        start_line = min(max(0, start_line), end_line)

        if mark_control != "unicode":
            s_lines = s.splitlines()[start_line - base_1 : end_line]
        else:
            s_lines = [
                line + "␊" for line in s.split("␊")[start_line - base_1 : end_line]
            ]
        if not s_lines:
            return ""

        lineno_width = len(str(end_line))
        max_line_len = max(len(line) for line in s_lines)
        lead = indent + " " * (lineno_width + 1)
        if max_line_len >= 99:
            header0 = (
                lead
                + ("" if base_1 else " ")
                + "".join(
                    f"{' ' * 99}{(i + 1) % 100}"
                    for i in range(1 if base_1 else 0, max(max_line_len // 100, 1))
                )
                + "\n"
            )
        else:
            header0 = ""
        header1 = (
            ("" if base_1 else " ")
            + lead
            + "".join(f"         {(i + 1) % 10}" for i in range(-(-max_line_len // 10)))
            + "\n"
        )
        digits = "1234567890"
        header2 = (
            lead + ("" if base_1 else "0") + digits * (-(-max_line_len // 10)) + "\n"
        )
        return (
            header1
            + header2
            + "\n".join(
                f"{indent}{i:{lineno_width}d}:{line}{eol_mark}"
                for i, line in enumerate(s_lines, start=start_line + base_1)
            )
            + "\n"
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import text_service

from .base import DEFAULT_CLIENT_INFO, TextServiceTransport


class TextServiceGrpcTransport(TextServiceTransport):
    """gRPC backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, grpc.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None

        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], text_service.GenerateTextResponse
    ]:
        r"""Return a callable for the generate text method over gRPC.

        Generates a response from the model given an input
        message.

        Returns:
            Callable[[~.GenerateTextRequest],
                    ~.GenerateTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_text" not in self._stubs:
            self._stubs["generate_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/GenerateText",
                request_serializer=text_service.GenerateTextRequest.serialize,
                response_deserializer=text_service.GenerateTextResponse.deserialize,
            )
        return self._stubs["generate_text"]

    @property
    def embed_text(
        self,
    ) -> Callable[[text_service.EmbedTextRequest], text_service.EmbedTextResponse]:
        r"""Return a callable for the embed text method over gRPC.

        Generates an embedding from the model given an input
        message.

        Returns:
            Callable[[~.EmbedTextRequest],
                    ~.EmbedTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_text" not in self._stubs:
            self._stubs["embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/EmbedText",
                request_serializer=text_service.EmbedTextRequest.serialize,
                response_deserializer=text_service.EmbedTextResponse.deserialize,
            )
        return self._stubs["embed_text"]

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest], text_service.BatchEmbedTextResponse
    ]:
        r"""Return a callable for the batch embed text method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedTextRequest],
                    ~.BatchEmbedTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_text" not in self._stubs:
            self._stubs["batch_embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/BatchEmbedText",
                request_serializer=text_service.BatchEmbedTextRequest.serialize,
                response_deserializer=text_service.BatchEmbedTextResponse.deserialize,
            )
        return self._stubs["batch_embed_text"]

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest], text_service.CountTextTokensResponse
    ]:
        r"""Return a callable for the count text tokens method over gRPC.

        Runs a model's tokenizer on a text and returns the
        token count.

        Returns:
            Callable[[~.CountTextTokensRequest],
                    ~.CountTextTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_text_tokens" not in self._stubs:
            self._stubs["count_text_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/CountTextTokens",
                request_serializer=text_service.CountTextTokensRequest.serialize,
                response_deserializer=text_service.CountTextTokensResponse.deserialize,
            )
        return self._stubs["count_text_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("TextServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta3.types import text_service

from .base import DEFAULT_CLIENT_INFO, TextServiceTransport


class TextServiceGrpcTransport(TextServiceTransport):
    """gRPC backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, grpc.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None

        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], text_service.GenerateTextResponse
    ]:
        r"""Return a callable for the generate text method over gRPC.

        Generates a response from the model given an input
        message.

        Returns:
            Callable[[~.GenerateTextRequest],
                    ~.GenerateTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_text" not in self._stubs:
            self._stubs["generate_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.TextService/GenerateText",
                request_serializer=text_service.GenerateTextRequest.serialize,
                response_deserializer=text_service.GenerateTextResponse.deserialize,
            )
        return self._stubs["generate_text"]

    @property
    def embed_text(
        self,
    ) -> Callable[[text_service.EmbedTextRequest], text_service.EmbedTextResponse]:
        r"""Return a callable for the embed text method over gRPC.

        Generates an embedding from the model given an input
        message.

        Returns:
            Callable[[~.EmbedTextRequest],
                    ~.EmbedTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_text" not in self._stubs:
            self._stubs["embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.TextService/EmbedText",
                request_serializer=text_service.EmbedTextRequest.serialize,
                response_deserializer=text_service.EmbedTextResponse.deserialize,
            )
        return self._stubs["embed_text"]

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest], text_service.BatchEmbedTextResponse
    ]:
        r"""Return a callable for the batch embed text method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedTextRequest],
                    ~.BatchEmbedTextResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_text" not in self._stubs:
            self._stubs["batch_embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.TextService/BatchEmbedText",
                request_serializer=text_service.BatchEmbedTextRequest.serialize,
                response_deserializer=text_service.BatchEmbedTextResponse.deserialize,
            )
        return self._stubs["batch_embed_text"]

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest], text_service.CountTextTokensResponse
    ]:
        r"""Return a callable for the count text tokens method over gRPC.

        Runs a model's tokenizer on a text and returns the
        token count.

        Returns:
            Callable[[~.CountTextTokensRequest],
                    ~.CountTextTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_text_tokens" not in self._stubs:
            self._stubs["count_text_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.TextService/CountTextTokens",
                request_serializer=text_service.CountTextTokensRequest.serialize,
                response_deserializer=text_service.CountTextTokensResponse.deserialize,
            )
        return self._stubs["count_text_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("TextServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\lexers\__init__.py ===
"""
    pygments.lexers
    ~~~~~~~~~~~~~~~

    Pygments lexers.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pip._vendor.pygments.lexers._mapping import LEXERS
from pip._vendor.pygments.modeline import get_filetype_from_buffer
from pip._vendor.pygments.plugin import find_plugin_lexers
from pip._vendor.pygments.util import ClassNotFound, guess_decode

COMPAT = {
    'Python3Lexer': 'PythonLexer',
    'Python3TracebackLexer': 'PythonTracebackLexer',
    'LeanLexer': 'Lean3Lexer',
}

__all__ = ['get_lexer_by_name', 'get_lexer_for_filename', 'find_lexer_class',
           'guess_lexer', 'load_lexer_from_file'] + list(LEXERS) + list(COMPAT)

_lexer_cache = {}
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_lexers(module_name):
    """Load a lexer (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for lexer_name in mod.__all__:
        cls = getattr(mod, lexer_name)
        _lexer_cache[cls.name] = cls


def get_all_lexers(plugins=True):
    """Return a generator of tuples in the form ``(name, aliases,
    filenames, mimetypes)`` of all know lexers.

    If *plugins* is true (the default), plugin lexers supplied by entrypoints
    are also returned.  Otherwise, only builtin ones are considered.
    """
    for item in LEXERS.values():
        yield item[1:]
    if plugins:
        for lexer in find_plugin_lexers():
            yield lexer.name, lexer.aliases, lexer.filenames, lexer.mimetypes


def find_lexer_class(name):
    """
    Return the `Lexer` subclass that with the *name* attribute as given by
    the *name* argument.
    """
    if name in _lexer_cache:
        return _lexer_cache[name]
    # lookup builtin lexers
    for module_name, lname, aliases, _, _ in LEXERS.values():
        if name == lname:
            _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if cls.name == name:
            return cls


def find_lexer_class_by_name(_alias):
    """
    Return the `Lexer` subclass that has `alias` in its aliases list, without
    instantiating it.

    Like `get_lexer_by_name`, but does not instantiate the class.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.

    .. versionadded:: 2.2
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')
    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def get_lexer_by_name(_alias, **options):
    """
    Return an instance of a `Lexer` subclass that has `alias` in its
    aliases list. The lexer is given the `options` at its
    instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')

    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name](**options)
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls(**options)
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def load_lexer_from_file(filename, lexername="CustomLexer", **options):
    """Load a lexer from a file.

    This method expects a file located relative to the current working
    directory, which contains a Lexer class. By default, it expects the
    Lexer to be name CustomLexer; you can specify your own class name
    as the second argument to this function.

    Users should be very careful with the input, because this method
    is equivalent to running eval on the input file.

    Raises ClassNotFound if there are any problems importing the Lexer.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `lexername` from that namespace
        if lexername not in custom_namespace:
            raise ClassNotFound(f'no valid {lexername} class found in {filename}')
        lexer_class = custom_namespace[lexername]
        # And finally instantiate it with the options
        return lexer_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom lexer: {err}')


def find_lexer_class_for_filename(_fn, code=None):
    """Get a lexer for a filename.

    If multiple lexers match the filename pattern, use ``analyse_text()`` to
    figure out which one is more appropriate.

    Returns None if not found.
    """
    matches = []
    fn = basename(_fn)
    for modname, name, _, filenames, _ in LEXERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _lexer_cache:
                    _load_lexers(modname)
                matches.append((_lexer_cache[name], filename))
    for cls in find_plugin_lexers():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                matches.append((cls, filename))

    if isinstance(code, bytes):
        # decode it, since all analyse_text functions expect unicode
        code = guess_decode(code)

    def get_rating(info):
        cls, filename = info
        # explicit patterns get a bonus
        bonus = '*' not in filename and 0.5 or 0
        # The class _always_ defines analyse_text because it's included in
        # the Lexer class.  The default implementation returns None which
        # gets turned into 0.0.  Run scripts/detect_missing_analyse_text.py
        # to find lexers which need it overridden.
        if code:
            return cls.analyse_text(code) + bonus, cls.__name__
        return cls.priority + bonus, cls.__name__

    if matches:
        matches.sort(key=get_rating)
        # print "Possible lexers, after sort:", matches
        return matches[-1][0]


def get_lexer_for_filename(_fn, code=None, **options):
    """Get a lexer for a filename.

    Return a `Lexer` subclass instance that has a filename pattern
    matching `fn`. The lexer is given the `options` at its
    instantiation.

    Raise :exc:`pygments.util.ClassNotFound` if no lexer for that filename
    is found.

    If multiple lexers match the filename pattern, use their ``analyse_text()``
    methods to figure out which one is more appropriate.
    """
    res = find_lexer_class_for_filename(_fn, code)
    if not res:
        raise ClassNotFound(f'no lexer for filename {_fn!r} found')
    return res(**options)


def get_lexer_for_mimetype(_mime, **options):
    """
    Return a `Lexer` subclass instance that has `mime` in its mimetype
    list. The lexer is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if not lexer for that mimetype
    is found.
    """
    for modname, name, _, _, mimetypes in LEXERS.values():
        if _mime in mimetypes:
            if name not in _lexer_cache:
                _load_lexers(modname)
            return _lexer_cache[name](**options)
    for cls in find_plugin_lexers():
        if _mime in cls.mimetypes:
            return cls(**options)
    raise ClassNotFound(f'no lexer for mimetype {_mime!r} found')


def _iter_lexerclasses(plugins=True):
    """Return an iterator over all lexer classes."""
    for key in sorted(LEXERS):
        module_name, name = LEXERS[key][:2]
        if name not in _lexer_cache:
            _load_lexers(module_name)
        yield _lexer_cache[name]
    if plugins:
        yield from find_plugin_lexers()


def guess_lexer_for_filename(_fn, _text, **options):
    """
    As :func:`guess_lexer()`, but only lexers which have a pattern in `filenames`
    or `alias_filenames` that matches `filename` are taken into consideration.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """
    fn = basename(_fn)
    primary = {}
    matching_lexers = set()
    for lexer in _iter_lexerclasses():
        for filename in lexer.filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = True
        for filename in lexer.alias_filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = False
    if not matching_lexers:
        raise ClassNotFound(f'no lexer for filename {fn!r} found')
    if len(matching_lexers) == 1:
        return matching_lexers.pop()(**options)
    result = []
    for lexer in matching_lexers:
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        result.append((rv, lexer))

    def type_sort(t):
        # sort by:
        # - analyse score
        # - is primary filename pattern?
        # - priority
        # - last resort: class name
        return (t[0], primary[t[1]], t[1].priority, t[1].__name__)
    result.sort(key=type_sort)

    return result[-1][1](**options)


def guess_lexer(_text, **options):
    """
    Return a `Lexer` subclass instance that's guessed from the text in
    `text`. For that, the :meth:`.analyse_text()` method of every known lexer
    class is called with the text as argument, and the lexer which returned the
    highest value will be instantiated and returned.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """

    if not isinstance(_text, str):
        inencoding = options.get('inencoding', options.get('encoding'))
        if inencoding:
            _text = _text.decode(inencoding or 'utf8')
        else:
            _text, _ = guess_decode(_text)

    # try to get a vim modeline first
    ft = get_filetype_from_buffer(_text)

    if ft is not None:
        try:
            return get_lexer_by_name(ft, **options)
        except ClassNotFound:
            pass

    best_lexer = [0.0, None]
    for lexer in _iter_lexerclasses():
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        if rv > best_lexer[0]:
            best_lexer[:] = (rv, lexer)
    if not best_lexer[0] or best_lexer[1] is None:
        raise ClassNotFound('no lexer matching the text found')
    return best_lexer[1](**options)


class _automodule(types.ModuleType):
    """Automatically import lexers."""

    def __getattr__(self, name):
        info = LEXERS.get(name)
        if info:
            _load_lexers(info[0])
            cls = _lexer_cache[info[1]]
            setattr(self, name, cls)
            return cls
        if name in COMPAT:
            return getattr(self, COMPAT[name])
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\__init__.py ===
"""
    pygments.lexers
    ~~~~~~~~~~~~~~~

    Pygments lexers.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pygments.lexers._mapping import LEXERS
from pygments.modeline import get_filetype_from_buffer
from pygments.plugin import find_plugin_lexers
from pygments.util import ClassNotFound, guess_decode

COMPAT = {
    'Python3Lexer': 'PythonLexer',
    'Python3TracebackLexer': 'PythonTracebackLexer',
    'LeanLexer': 'Lean3Lexer',
}

__all__ = ['get_lexer_by_name', 'get_lexer_for_filename', 'find_lexer_class',
           'guess_lexer', 'load_lexer_from_file'] + list(LEXERS) + list(COMPAT)

_lexer_cache = {}
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_lexers(module_name):
    """Load a lexer (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for lexer_name in mod.__all__:
        cls = getattr(mod, lexer_name)
        _lexer_cache[cls.name] = cls


def get_all_lexers(plugins=True):
    """Return a generator of tuples in the form ``(name, aliases,
    filenames, mimetypes)`` of all know lexers.

    If *plugins* is true (the default), plugin lexers supplied by entrypoints
    are also returned.  Otherwise, only builtin ones are considered.
    """
    for item in LEXERS.values():
        yield item[1:]
    if plugins:
        for lexer in find_plugin_lexers():
            yield lexer.name, lexer.aliases, lexer.filenames, lexer.mimetypes


def find_lexer_class(name):
    """
    Return the `Lexer` subclass that with the *name* attribute as given by
    the *name* argument.
    """
    if name in _lexer_cache:
        return _lexer_cache[name]
    # lookup builtin lexers
    for module_name, lname, aliases, _, _ in LEXERS.values():
        if name == lname:
            _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if cls.name == name:
            return cls


def find_lexer_class_by_name(_alias):
    """
    Return the `Lexer` subclass that has `alias` in its aliases list, without
    instantiating it.

    Like `get_lexer_by_name`, but does not instantiate the class.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.

    .. versionadded:: 2.2
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')
    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name]
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def get_lexer_by_name(_alias, **options):
    """
    Return an instance of a `Lexer` subclass that has `alias` in its
    aliases list. The lexer is given the `options` at its
    instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no lexer with that alias is
    found.
    """
    if not _alias:
        raise ClassNotFound(f'no lexer for alias {_alias!r} found')

    # lookup builtin lexers
    for module_name, name, aliases, _, _ in LEXERS.values():
        if _alias.lower() in aliases:
            if name not in _lexer_cache:
                _load_lexers(module_name)
            return _lexer_cache[name](**options)
    # continue with lexers from setuptools entrypoints
    for cls in find_plugin_lexers():
        if _alias.lower() in cls.aliases:
            return cls(**options)
    raise ClassNotFound(f'no lexer for alias {_alias!r} found')


def load_lexer_from_file(filename, lexername="CustomLexer", **options):
    """Load a lexer from a file.

    This method expects a file located relative to the current working
    directory, which contains a Lexer class. By default, it expects the
    Lexer to be name CustomLexer; you can specify your own class name
    as the second argument to this function.

    Users should be very careful with the input, because this method
    is equivalent to running eval on the input file.

    Raises ClassNotFound if there are any problems importing the Lexer.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `lexername` from that namespace
        if lexername not in custom_namespace:
            raise ClassNotFound(f'no valid {lexername} class found in {filename}')
        lexer_class = custom_namespace[lexername]
        # And finally instantiate it with the options
        return lexer_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom lexer: {err}')


def find_lexer_class_for_filename(_fn, code=None):
    """Get a lexer for a filename.

    If multiple lexers match the filename pattern, use ``analyse_text()`` to
    figure out which one is more appropriate.

    Returns None if not found.
    """
    matches = []
    fn = basename(_fn)
    for modname, name, _, filenames, _ in LEXERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _lexer_cache:
                    _load_lexers(modname)
                matches.append((_lexer_cache[name], filename))
    for cls in find_plugin_lexers():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                matches.append((cls, filename))

    if isinstance(code, bytes):
        # decode it, since all analyse_text functions expect unicode
        code = guess_decode(code)

    def get_rating(info):
        cls, filename = info
        # explicit patterns get a bonus
        bonus = '*' not in filename and 0.5 or 0
        # The class _always_ defines analyse_text because it's included in
        # the Lexer class.  The default implementation returns None which
        # gets turned into 0.0.  Run scripts/detect_missing_analyse_text.py
        # to find lexers which need it overridden.
        if code:
            return cls.analyse_text(code) + bonus, cls.__name__
        return cls.priority + bonus, cls.__name__

    if matches:
        matches.sort(key=get_rating)
        # print "Possible lexers, after sort:", matches
        return matches[-1][0]


def get_lexer_for_filename(_fn, code=None, **options):
    """Get a lexer for a filename.

    Return a `Lexer` subclass instance that has a filename pattern
    matching `fn`. The lexer is given the `options` at its
    instantiation.

    Raise :exc:`pygments.util.ClassNotFound` if no lexer for that filename
    is found.

    If multiple lexers match the filename pattern, use their ``analyse_text()``
    methods to figure out which one is more appropriate.
    """
    res = find_lexer_class_for_filename(_fn, code)
    if not res:
        raise ClassNotFound(f'no lexer for filename {_fn!r} found')
    return res(**options)


def get_lexer_for_mimetype(_mime, **options):
    """
    Return a `Lexer` subclass instance that has `mime` in its mimetype
    list. The lexer is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if not lexer for that mimetype
    is found.
    """
    for modname, name, _, _, mimetypes in LEXERS.values():
        if _mime in mimetypes:
            if name not in _lexer_cache:
                _load_lexers(modname)
            return _lexer_cache[name](**options)
    for cls in find_plugin_lexers():
        if _mime in cls.mimetypes:
            return cls(**options)
    raise ClassNotFound(f'no lexer for mimetype {_mime!r} found')


def _iter_lexerclasses(plugins=True):
    """Return an iterator over all lexer classes."""
    for key in sorted(LEXERS):
        module_name, name = LEXERS[key][:2]
        if name not in _lexer_cache:
            _load_lexers(module_name)
        yield _lexer_cache[name]
    if plugins:
        yield from find_plugin_lexers()


def guess_lexer_for_filename(_fn, _text, **options):
    """
    As :func:`guess_lexer()`, but only lexers which have a pattern in `filenames`
    or `alias_filenames` that matches `filename` are taken into consideration.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """
    fn = basename(_fn)
    primary = {}
    matching_lexers = set()
    for lexer in _iter_lexerclasses():
        for filename in lexer.filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = True
        for filename in lexer.alias_filenames:
            if _fn_matches(fn, filename):
                matching_lexers.add(lexer)
                primary[lexer] = False
    if not matching_lexers:
        raise ClassNotFound(f'no lexer for filename {fn!r} found')
    if len(matching_lexers) == 1:
        return matching_lexers.pop()(**options)
    result = []
    for lexer in matching_lexers:
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        result.append((rv, lexer))

    def type_sort(t):
        # sort by:
        # - analyse score
        # - is primary filename pattern?
        # - priority
        # - last resort: class name
        return (t[0], primary[t[1]], t[1].priority, t[1].__name__)
    result.sort(key=type_sort)

    return result[-1][1](**options)


def guess_lexer(_text, **options):
    """
    Return a `Lexer` subclass instance that's guessed from the text in
    `text`. For that, the :meth:`.analyse_text()` method of every known lexer
    class is called with the text as argument, and the lexer which returned the
    highest value will be instantiated and returned.

    :exc:`pygments.util.ClassNotFound` is raised if no lexer thinks it can
    handle the content.
    """

    if not isinstance(_text, str):
        inencoding = options.get('inencoding', options.get('encoding'))
        if inencoding:
            _text = _text.decode(inencoding or 'utf8')
        else:
            _text, _ = guess_decode(_text)

    # try to get a vim modeline first
    ft = get_filetype_from_buffer(_text)

    if ft is not None:
        try:
            return get_lexer_by_name(ft, **options)
        except ClassNotFound:
            pass

    best_lexer = [0.0, None]
    for lexer in _iter_lexerclasses():
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        if rv > best_lexer[0]:
            best_lexer[:] = (rv, lexer)
    if not best_lexer[0] or best_lexer[1] is None:
        raise ClassNotFound('no lexer matching the text found')
    return best_lexer[1](**options)


class _automodule(types.ModuleType):
    """Automatically import lexers."""

    def __getattr__(self, name):
        info = LEXERS.get(name)
        if info:
            _load_lexers(info[0])
            cls = _lexer_cache[info[1]]
            setattr(self, name, cls)
            return cls
        if name in COMPAT:
            return getattr(self, COMPAT[name])
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types

# === NexusCore/evaluation\evalplus\evalplus\evaluate.py ===
import argparse
import json
import multiprocessing
import os
import pickle
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Tuple
from warnings import warn

import numpy as np
from termcolor import cprint
from tqdm import tqdm

from evalplus.data import (
    get_human_eval_plus,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
    load_solutions,
)
from evalplus.data.mbpp import mbpp_serialize_inputs
from evalplus.data.utils import CACHE_DIR
from evalplus.eval import (
    PASS,
    compatible_eval_result,
    estimate_pass_at_k,
    untrusted_check,
)
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from evalplus.gen.util import trusted_exec

# 1st item: the status
# 2nd item (optional): the detailed pass/fail boolean for each input
Result = Tuple[str, List[bool]]


def get_groundtruth(problems, hashcode, tasks_only_output_not_none):
    cache_file = os.path.join(CACHE_DIR, f"{hashcode}.pkl")
    if os.path.exists(cache_file):
        print(f"Load from ground-truth from {cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    os.makedirs(CACHE_DIR, exist_ok=True)
    print("Computing expected output...")
    tbegin = time.time()
    expected_output = {}
    for task_id, problem in problems.items():
        oracle = {}
        oracle["base"], oracle["base_time"] = trusted_exec(
            problem["prompt"] + problem["canonical_solution"],
            problem["base_input"],
            problem["entry_point"],
            record_time=True,
            output_not_none=problem["entry_point"] in tasks_only_output_not_none,
        )

        oracle["plus"], oracle["plus_time"] = trusted_exec(
            problem["prompt"] + problem["canonical_solution"],
            problem["plus_input"],
            problem["entry_point"],
            record_time=True,
            output_not_none=problem["entry_point"] in tasks_only_output_not_none,
        )
        expected_output[task_id] = oracle
    print(f"Expected outputs computed in {time.time() - tbegin:.2f}s")

    with open(cache_file, "wb") as f:
        pickle.dump(expected_output, f)

    return expected_output


def check_correctness(
    dataset: str,
    completion_id: int,
    problem: Dict[str, Any],
    solution: str,
    expected_output: Dict[str, List],
    base_only=False,
    fast_check=False,
    identifier=None,
    min_time_limit: float = 0.1,
    gt_time_limit_factor: float = 2.0,
) -> Dict[str, Result]:  # {...}, "base" | "plus" -> (status, details)
    ret = {
        "completion_id": completion_id,
        "task_id": problem["task_id"],
        "_identifier": identifier,
        "solution": solution,
    }
    ret["base"] = untrusted_check(
        dataset,
        solution,
        problem["base_input"],
        problem["entry_point"],
        expected=expected_output["base"],
        atol=problem["atol"],
        ref_time=expected_output["base_time"],
        fast_check=fast_check,
        min_time_limit=min_time_limit,
        gt_time_limit_factor=gt_time_limit_factor,
    )

    if not base_only:
        ret["plus"] = untrusted_check(
            dataset,
            solution,
            problem["plus_input"],
            problem["entry_point"],
            expected=expected_output["plus"],
            atol=problem["atol"],
            ref_time=expected_output["plus_time"],
            fast_check=fast_check,
            min_time_limit=min_time_limit,
            gt_time_limit_factor=gt_time_limit_factor,
        )

    return ret


def evaluate(flags):
    if flags.parallel is None:
        n_workers = max(1, multiprocessing.cpu_count() // 2)
    else:
        n_workers = flags.parallel

    if os.path.isdir(flags.samples):
        result_path = os.path.join(flags.samples, "eval_results.json")
    else:
        assert flags.samples.endswith(".jsonl")
        result_path = flags.samples.replace(".jsonl", "_eval_results.json")

    if os.path.isfile(result_path) and not flags.i_just_wanna_run:
        print(f"Load from previous results from {result_path}")
        with open(result_path, "r") as f:
            results = json.load(f)

        results = compatible_eval_result(results)
    else:
        if flags.dataset == "humaneval":
            problems = get_human_eval_plus(
                mini=flags.mini, noextreme=flags.noextreme, version=flags.version
            )
            dataset_hash = get_human_eval_plus_hash(
                mini=flags.mini, noextreme=flags.noextreme, version=flags.version
            )
            expected_output = get_groundtruth(problems, dataset_hash, [])
        elif flags.dataset == "mbpp":
            problems = get_mbpp_plus(
                mini=flags.mini, noextreme=flags.noextreme, version=flags.version
            )
            dataset_hash = get_mbpp_plus_hash(
                mini=flags.mini, noextreme=flags.noextreme, version=flags.version
            )
            expected_output = get_groundtruth(
                problems,
                dataset_hash,
                MBPP_OUTPUT_NOT_NONE_TASKS,
            )

        results = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hash": dataset_hash,
            "eval": {},
        }

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            completion_id = Counter()
            n_samples = 0
            eval_results = defaultdict(list)  # task_id ->
            remainings = set()

            print("Reading samples...")
            for sample in tqdm(load_solutions(flags.samples)):
                task_id = sample["task_id"]
                if task_id not in problems:
                    warn(
                        f"Task {task_id} is found in the samples but not found in the dataset"
                    )
                    continue
                solution = (
                    sample["solution"]
                    if "solution" in sample
                    else problems[task_id]["prompt"] + sample["completion"]
                )
                remainings.add(sample["_identifier"])
                args = (
                    flags.dataset,
                    completion_id[task_id],
                    problems[task_id],
                    solution,
                    expected_output[task_id],
                    flags.base_only,
                    not flags.test_details,  # fast_check
                    sample["_identifier"],
                    flags.min_time_limit,
                    flags.gt_time_limit_factor,
                )
                futures.append(executor.submit(check_correctness, *args))
                completion_id[task_id] += 1
                n_samples += 1

            assert n_samples == len(remainings), "Missing problems in unfinished"
            assert len(completion_id) == len(problems), "Missing problems in samples"

            def stucking_checker():
                while remainings:
                    last_size = len(remainings)
                    time.sleep(20)
                    if last_size != len(remainings) or len(remainings) == 0:
                        continue
                    # Potential stucking
                    warn("No samples had finished testing in the last 20s")
                    warn(f"{len(remainings)} samples to be tested: {remainings}")

            threading.Thread(target=stucking_checker).start()

            for future in tqdm(as_completed(futures), total=n_samples):
                result = future.result()
                remainings.remove(result["_identifier"])
                eval_results[result["task_id"]].append(result)

        # sort the results for each problem by completion_id
        for task_id, task_results in eval_results.items():
            task_results.sort(key=lambda x: x["completion_id"])
            results["eval"][task_id] = []
            for res in task_results:

                def get_failed_tests(stat, details, inputs) -> List[Any]:
                    if stat == PASS or not details:
                        return []

                    if flags.test_details:
                        return [
                            inputs[i] for i in range(len(details)) if not details[i]
                        ]

                    # esle => simply return the only and the last fail test
                    return [inputs[len(details)]]

                base_stat, base_details = res["base"]
                base_fail_tests = get_failed_tests(
                    base_stat, base_details, problems[task_id]["base_input"]
                )

                # initialize plus tests
                plus_stat = None
                plus_fail_tests = []

                # with plus tests
                if not flags.base_only:
                    plus_stat, plus_details = res["plus"]
                    plus_fail_tests = get_failed_tests(
                        plus_stat, plus_details, problems[task_id]["plus_input"]
                    )

                if flags.dataset == "mbpp":
                    base_fail_tests = mbpp_serialize_inputs(task_id, base_fail_tests)
                    plus_fail_tests = mbpp_serialize_inputs(task_id, plus_fail_tests)

                results["eval"][task_id].append(
                    {
                        "task_id": task_id,
                        "solution": res["solution"],
                        "base_status": base_stat,
                        "plus_status": plus_stat,
                        "base_fail_tests": base_fail_tests,
                        "plus_fail_tests": plus_fail_tests,
                    }
                )

    # Calculate pass@k.
    total = np.array([len(r) for r in results["eval"].values()])
    base_correct = []
    new_correct = []

    for res in results["eval"].values():
        bc = sum([r["base_status"] == PASS for r in res])
        base_correct.append(bc)
        if not flags.base_only:
            new_correct.append(
                sum(
                    [
                        res[i]["base_status"] == res[i]["plus_status"] == PASS
                        for i in range(len(res))
                    ]
                )
            )
    base_correct = np.array(base_correct)

    pass_at_k = {
        f"pass@{k}": estimate_pass_at_k(total, base_correct, k).mean()
        for k in [1, 10, 100]
        if total.min() >= k
    }
    cprint(f"{flags.dataset} (base tests)", "red")
    for k, v in pass_at_k.items():
        cprint(f"{k}:\t{v:.3f}", "red")

    if new_correct:
        cprint(f"{flags.dataset}+ (base + extra tests)", "green")
        pass_at_k = {
            f"pass@{k}": estimate_pass_at_k(total, np.array(new_correct), k).mean()
            for k in [1, 10, 100]
            if (total >= k).all()
        }
        for k, v in pass_at_k.items():
            cprint(f"{k}:\t{v:.3f}", "green")

    # save results
    if os.path.isfile(result_path) and flags.i_just_wanna_run:
        decision = ""
        while decision.lower() not in ["y", "n"]:
            print(f"{result_path} already exists. Press [Y/N] to overwrite or exit...")
            decision = input()

        if decision.lower() == "y":
            # mv the file to a backup
            new_path = result_path + ".bak"
            while os.path.isfile(new_path):
                new_path += ".bak"
            os.rename(result_path, new_path)
            print(f"Backup {result_path} to {new_path}")

    if not os.path.isfile(result_path):
        with open(result_path, "w") as f:
            json.dump(results, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", required=True, type=str, choices=["humaneval", "mbpp"]
    )
    parser.add_argument("--samples", required=True, type=str)
    parser.add_argument("--base-only", action="store_true")
    parser.add_argument("--parallel", default=None, type=int)
    parser.add_argument("--i-just-wanna-run", action="store_true")
    parser.add_argument("--test-details", action="store_true")
    parser.add_argument("--min-time-limit", default=1, type=float)
    parser.add_argument("--gt-time-limit-factor", default=4.0, type=float)
    parser.add_argument("--mini", action="store_true")
    parser.add_argument(
        "--noextreme", action="store_true", help="Omit extreme test inputs"
    )
    parser.add_argument(
        "--version", default="default", type=str, help="Version of the dataset"
    )
    args = parser.parse_args()

    evaluate(args)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\jinxed\win32.py ===
# -*- coding: utf-8 -*-
# Copyright 2019 - 2024 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Support functions and wrappers for calls to the Windows API
"""

import atexit
import codecs
from collections import namedtuple
import ctypes
from ctypes import wintypes
import io
import msvcrt  # pylint: disable=import-error
import os
import platform
import sys

from jinxed._util import mock, IS_WINDOWS

# Workaround for auto-doc generation on Linux
if not IS_WINDOWS:
    ctypes = mock.Mock()  # noqa: F811

LPDWORD = ctypes.POINTER(wintypes.DWORD)
COORD = wintypes._COORD  # pylint: disable=protected-access

# Console input modes
ENABLE_ECHO_INPUT = 0x0004
ENABLE_EXTENDED_FLAGS = 0x0080
ENABLE_INSERT_MODE = 0x0020
ENABLE_LINE_INPUT = 0x0002
ENABLE_MOUSE_INPUT = 0x0010
ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_QUICK_EDIT_MODE = 0x0040
ENABLE_WINDOW_INPUT = 0x0008
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

# Console output modes
ENABLE_PROCESSED_OUTPUT = 0x0001
ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
DISABLE_NEWLINE_AUTO_RETURN = 0x0008
ENABLE_LVB_GRID_WORLDWIDE = 0x0010

if IS_WINDOWS and tuple(int(num) for num in platform.version().split('.')) >= (10, 0, 10586):
    VTMODE_SUPPORTED = True
    CBREAK_MODE = ENABLE_PROCESSED_INPUT | ENABLE_VIRTUAL_TERMINAL_INPUT
    RAW_MODE = ENABLE_VIRTUAL_TERMINAL_INPUT
else:
    VTMODE_SUPPORTED = False
    CBREAK_MODE = ENABLE_PROCESSED_INPUT
    RAW_MODE = 0

GTS_SUPPORTED = hasattr(os, 'get_terminal_size')
TerminalSize = namedtuple('TerminalSize', ('columns', 'lines'))


class ConsoleScreenBufferInfo(ctypes.Structure):  # pylint: disable=too-few-public-methods
    """
    Python representation of CONSOLE_SCREEN_BUFFER_INFO structure
    https://docs.microsoft.com/en-us/windows/console/console-screen-buffer-info-str
    """

    _fields_ = [('dwSize', COORD),
                ('dwCursorPosition', COORD),
                ('wAttributes', wintypes.WORD),
                ('srWindow', wintypes.SMALL_RECT),
                ('dwMaximumWindowSize', COORD)]


CSBIP = ctypes.POINTER(ConsoleScreenBufferInfo)


def _check_bool(result, func, args):  # pylint: disable=unused-argument
    """
    Used as an error handler for Windows calls
    Gets last error if call is not successful
    """

    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return args


KERNEL32 = ctypes.WinDLL('kernel32', use_last_error=True)

KERNEL32.GetConsoleCP.errcheck = _check_bool
KERNEL32.GetConsoleCP.argtypes = ()

KERNEL32.GetConsoleMode.errcheck = _check_bool
KERNEL32.GetConsoleMode.argtypes = (wintypes.HANDLE, LPDWORD)

KERNEL32.SetConsoleMode.errcheck = _check_bool
KERNEL32.SetConsoleMode.argtypes = (wintypes.HANDLE, wintypes.DWORD)

KERNEL32.GetConsoleScreenBufferInfo.errcheck = _check_bool
KERNEL32.GetConsoleScreenBufferInfo.argtypes = (wintypes.HANDLE, CSBIP)


def get_csbi(filehandle=None):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`

    Returns:
        :py:class:`ConsoleScreenBufferInfo`: CONSOLE_SCREEN_BUFFER_INFO_ structure

    Wrapper for GetConsoleScreenBufferInfo_

    If ``filehandle`` is :py:data:`None`, uses the filehandle of :py:data:`sys.__stdout__`.

    """

    if filehandle is None:
        filehandle = msvcrt.get_osfhandle(sys.__stdout__.fileno())

    csbi = ConsoleScreenBufferInfo()
    KERNEL32.GetConsoleScreenBufferInfo(filehandle, ctypes.byref(csbi))
    return csbi


def get_console_input_encoding():
    """
    Returns:
        int: Current console mode

    Query for the console input code page and provide an encoding

    If the code page can not be resolved to a Python encoding, :py:data:`None` is returned.
    """

    try:
        encoding = 'cp%d' % KERNEL32.GetConsoleCP()
    except OSError:
        return None

    try:
        codecs.lookup(encoding)
    except LookupError:
        return None

    return encoding


def get_console_mode(filehandle):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`

    Returns:
        int: Current console mode

    Raises:
        OSError: Error calling Windows API

    Wrapper for GetConsoleMode_
    """

    mode = wintypes.DWORD()
    KERNEL32.GetConsoleMode(filehandle, ctypes.byref(mode))
    return mode.value


def set_console_mode(filehandle, mode):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`
        mode(int): Desired console mode

    Raises:
        OSError: Error calling Windows API

    Wrapper for SetConsoleMode_
    """

    return bool(KERNEL32.SetConsoleMode(filehandle, mode))


def setcbreak(filehandle):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`

    Raises:
        OSError: Error calling Windows API

    Convenience function which mimics :py:func:`tty.setcbreak` behavior

    All console input options are disabled except ``ENABLE_PROCESSED_INPUT``
    and, if supported, ``ENABLE_VIRTUAL_TERMINAL_INPUT``
    """

    set_console_mode(filehandle, CBREAK_MODE)


def setraw(filehandle):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`

    Raises:
        OSError: Error calling Windows API

    Convenience function which mimics :py:func:`tty.setraw` behavior

    All console input options are disabled except, if supported, ``ENABLE_VIRTUAL_TERMINAL_INPUT``
    """

    set_console_mode(filehandle, RAW_MODE)


def enable_vt_mode(filehandle=None):
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`

    Raises:
        OSError: Error calling Windows API

    Enables virtual terminal processing mode for the given console

    If ``filehandle`` is :py:data:`None`, uses the filehandle of :py:data:`sys.__stdout__`.
    """

    if filehandle is None:
        filehandle = msvcrt.get_osfhandle(sys.__stdout__.fileno())

    mode = get_console_mode(filehandle)
    mode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
    set_console_mode(filehandle, mode)


def get_terminal_size(fd):  # pylint:  disable=invalid-name
    """
    Args:
        fd(int): Python file descriptor

    Returns:
        :py:class:`os.terminal_size`: Named tuple representing terminal size

    Convenience function for getting terminal size

    In Python 3.3 and above, this is a wrapper for :py:func:`os.get_terminal_size`.
    In older versions of Python, this function calls GetConsoleScreenBufferInfo_.
    """

    # In Python 3.3+ we can let the standard library handle this
    if GTS_SUPPORTED:
        return os.get_terminal_size(fd)

    handle = msvcrt.get_osfhandle(fd)
    window = get_csbi(handle).srWindow
    return TerminalSize(window.Right - window.Left + 1, window.Bottom - window.Top + 1)


def flush_and_set_console(fd, mode=None):  # pylint:  disable=invalid-name
    """
    Args:
        filehandle(int): Windows filehandle object as returned by :py:func:`msvcrt.get_osfhandle`
        mode(int): Desired console mode. If None, mode is not changed

    Attempts to set console to specified mode, but will not raise on failure

    If the file descriptor is STDOUT or STDERR, attempts to flush first
    """

    try:
        if fd in (sys.__stdout__.fileno(), sys.__stderr__.fileno()):
            sys.__stdout__.flush()
            sys.__stderr__.flush()
    except (AttributeError, TypeError, io.UnsupportedOperation):
        pass

    if mode is not None:

        try:
            filehandle = msvcrt.get_osfhandle(fd)
            set_console_mode(filehandle, mode)
        except OSError:
            pass


def get_term(fd, fallback=True):  # pylint:  disable=invalid-name
    """
    Args:
        fd(int): Python file descriptor
        fallback(bool): Use fallback terminal type if type can not be determined
    Returns:
        str: Terminal type

    Attempts to determine and enable the current terminal type

    The current logic is:

        - If TERM is defined in the environment, the value is returned
        - Else, if ANSICON is defined in the environment, ``'ansicon'`` is returned
        - Else, if virtual terminal mode is natively supported,
          it is enabled and ``'vtwin10'`` is returned
        - Else, if ``fallback`` is ``True``, Ansicon is loaded, and ``'ansicon'`` is returned
        - If no other conditions are satisfied, ``'unknown'`` is returned

    This logic may change in the future as additional terminal types are added.
    """

    # First try TERM
    term = os.environ.get('TERM', None)

    if term is None:

        # See if ansicon is enabled
        if os.environ.get('ANSICON', None):
            term = 'ansicon'

        # See if Windows Terminal is being used
        elif os.environ.get('WT_SESSION', None):
            term = 'vtwin10'

        # See if the version of Windows supports VTMODE
        elif VTMODE_SUPPORTED:
            try:
                filehandle = msvcrt.get_osfhandle(fd)
                mode = get_console_mode(filehandle)
            except OSError:
                term = 'unknown'
            else:
                # Proceed if VT mode is already enabled
                if mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
                    atexit.register(flush_and_set_console, fd, None)

                # Otherwise, enable VT mode
                else:
                    atexit.register(flush_and_set_console, fd, mode)
                    # pylint: disable=unsupported-binary-operation
                    set_console_mode(filehandle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

                term = 'vtwin10'

        # Currently falling back to Ansicon for older versions of Windows
        elif fallback:
            import ansicon  # pylint: disable=import-error,import-outside-toplevel
            ansicon.load()

            try:
                filehandle = msvcrt.get_osfhandle(fd)
                mode = get_console_mode(filehandle)
            except OSError:
                term = 'unknown'
            else:
                atexit.register(flush_and_set_console, fd, mode)
                set_console_mode(filehandle, mode ^ ENABLE_WRAP_AT_EOL_OUTPUT)
                term = 'ansicon'

        else:
            term = 'unknown'

    return term

# === NexusCore/openenv\Lib\site-packages\PIL\features.py ===
from __future__ import annotations

import collections
import os
import sys
import warnings
from typing import IO

import PIL

from . import Image
from ._deprecate import deprecate

modules = {
    "pil": ("PIL._imaging", "PILLOW_VERSION"),
    "tkinter": ("PIL._tkinter_finder", "tk_version"),
    "freetype2": ("PIL._imagingft", "freetype2_version"),
    "littlecms2": ("PIL._imagingcms", "littlecms_version"),
    "webp": ("PIL._webp", "webpdecoder_version"),
    "avif": ("PIL._avif", "libavif_version"),
}


def check_module(feature: str) -> bool:
    """
    Checks if a module is available.

    :param feature: The module to check for.
    :returns: ``True`` if available, ``False`` otherwise.
    :raises ValueError: If the module is not defined in this version of Pillow.
    """
    if feature not in modules:
        msg = f"Unknown module {feature}"
        raise ValueError(msg)

    module, ver = modules[feature]

    try:
        __import__(module)
        return True
    except ModuleNotFoundError:
        return False
    except ImportError as ex:
        warnings.warn(str(ex))
        return False


def version_module(feature: str) -> str | None:
    """
    :param feature: The module to check for.
    :returns:
        The loaded version number as a string, or ``None`` if unknown or not available.
    :raises ValueError: If the module is not defined in this version of Pillow.
    """
    if not check_module(feature):
        return None

    module, ver = modules[feature]

    return getattr(__import__(module, fromlist=[ver]), ver)


def get_supported_modules() -> list[str]:
    """
    :returns: A list of all supported modules.
    """
    return [f for f in modules if check_module(f)]


codecs = {
    "jpg": ("jpeg", "jpeglib"),
    "jpg_2000": ("jpeg2k", "jp2klib"),
    "zlib": ("zip", "zlib"),
    "libtiff": ("libtiff", "libtiff"),
}


def check_codec(feature: str) -> bool:
    """
    Checks if a codec is available.

    :param feature: The codec to check for.
    :returns: ``True`` if available, ``False`` otherwise.
    :raises ValueError: If the codec is not defined in this version of Pillow.
    """
    if feature not in codecs:
        msg = f"Unknown codec {feature}"
        raise ValueError(msg)

    codec, lib = codecs[feature]

    return f"{codec}_encoder" in dir(Image.core)


def version_codec(feature: str) -> str | None:
    """
    :param feature: The codec to check for.
    :returns:
        The version number as a string, or ``None`` if not available.
        Checked at compile time for ``jpg``, run-time otherwise.
    :raises ValueError: If the codec is not defined in this version of Pillow.
    """
    if not check_codec(feature):
        return None

    codec, lib = codecs[feature]

    version = getattr(Image.core, f"{lib}_version")

    if feature == "libtiff":
        return version.split("\n")[0].split("Version ")[1]

    return version


def get_supported_codecs() -> list[str]:
    """
    :returns: A list of all supported codecs.
    """
    return [f for f in codecs if check_codec(f)]


features: dict[str, tuple[str, str | bool, str | None]] = {
    "webp_anim": ("PIL._webp", True, None),
    "webp_mux": ("PIL._webp", True, None),
    "transp_webp": ("PIL._webp", True, None),
    "raqm": ("PIL._imagingft", "HAVE_RAQM", "raqm_version"),
    "fribidi": ("PIL._imagingft", "HAVE_FRIBIDI", "fribidi_version"),
    "harfbuzz": ("PIL._imagingft", "HAVE_HARFBUZZ", "harfbuzz_version"),
    "libjpeg_turbo": ("PIL._imaging", "HAVE_LIBJPEGTURBO", "libjpeg_turbo_version"),
    "mozjpeg": ("PIL._imaging", "HAVE_MOZJPEG", "libjpeg_turbo_version"),
    "zlib_ng": ("PIL._imaging", "HAVE_ZLIBNG", "zlib_ng_version"),
    "libimagequant": ("PIL._imaging", "HAVE_LIBIMAGEQUANT", "imagequant_version"),
    "xcb": ("PIL._imaging", "HAVE_XCB", None),
}


def check_feature(feature: str) -> bool | None:
    """
    Checks if a feature is available.

    :param feature: The feature to check for.
    :returns: ``True`` if available, ``False`` if unavailable, ``None`` if unknown.
    :raises ValueError: If the feature is not defined in this version of Pillow.
    """
    if feature not in features:
        msg = f"Unknown feature {feature}"
        raise ValueError(msg)

    module, flag, ver = features[feature]

    if isinstance(flag, bool):
        deprecate(f'check_feature("{feature}")', 12)
    try:
        imported_module = __import__(module, fromlist=["PIL"])
        if isinstance(flag, bool):
            return flag
        return getattr(imported_module, flag)
    except ModuleNotFoundError:
        return None
    except ImportError as ex:
        warnings.warn(str(ex))
        return None


def version_feature(feature: str) -> str | None:
    """
    :param feature: The feature to check for.
    :returns: The version number as a string, or ``None`` if not available.
    :raises ValueError: If the feature is not defined in this version of Pillow.
    """
    if not check_feature(feature):
        return None

    module, flag, ver = features[feature]

    if ver is None:
        return None

    return getattr(__import__(module, fromlist=[ver]), ver)


def get_supported_features() -> list[str]:
    """
    :returns: A list of all supported features.
    """
    supported_features = []
    for f, (module, flag, _) in features.items():
        if flag is True:
            for feature, (feature_module, _) in modules.items():
                if feature_module == module:
                    if check_module(feature):
                        supported_features.append(f)
                    break
        elif check_feature(f):
            supported_features.append(f)
    return supported_features


def check(feature: str) -> bool | None:
    """
    :param feature: A module, codec, or feature name.
    :returns:
        ``True`` if the module, codec, or feature is available,
        ``False`` or ``None`` otherwise.
    """

    if feature in modules:
        return check_module(feature)
    if feature in codecs:
        return check_codec(feature)
    if feature in features:
        return check_feature(feature)
    warnings.warn(f"Unknown feature '{feature}'.", stacklevel=2)
    return False


def version(feature: str) -> str | None:
    """
    :param feature:
        The module, codec, or feature to check for.
    :returns:
        The version number as a string, or ``None`` if unknown or not available.
    """
    if feature in modules:
        return version_module(feature)
    if feature in codecs:
        return version_codec(feature)
    if feature in features:
        return version_feature(feature)
    return None


def get_supported() -> list[str]:
    """
    :returns: A list of all supported modules, features, and codecs.
    """

    ret = get_supported_modules()
    ret.extend(get_supported_features())
    ret.extend(get_supported_codecs())
    return ret


def pilinfo(out: IO[str] | None = None, supported_formats: bool = True) -> None:
    """
    Prints information about this installation of Pillow.
    This function can be called with ``python3 -m PIL``.
    It can also be called with ``python3 -m PIL.report`` or ``python3 -m PIL --report``
    to have "supported_formats" set to ``False``, omitting the list of all supported
    image file formats.

    :param out:
        The output stream to print to. Defaults to ``sys.stdout`` if ``None``.
    :param supported_formats:
        If ``True``, a list of all supported image file formats will be printed.
    """

    if out is None:
        out = sys.stdout

    Image.init()

    print("-" * 68, file=out)
    print(f"Pillow {PIL.__version__}", file=out)
    py_version_lines = sys.version.splitlines()
    print(f"Python {py_version_lines[0].strip()}", file=out)
    for py_version in py_version_lines[1:]:
        print(f"       {py_version.strip()}", file=out)
    print("-" * 68, file=out)
    print(f"Python executable is {sys.executable or 'unknown'}", file=out)
    if sys.prefix != sys.base_prefix:
        print(f"Environment Python files loaded from {sys.prefix}", file=out)
    print(f"System Python files loaded from {sys.base_prefix}", file=out)
    print("-" * 68, file=out)
    print(
        f"Python Pillow modules loaded from {os.path.dirname(Image.__file__)}",
        file=out,
    )
    print(
        f"Binary Pillow modules loaded from {os.path.dirname(Image.core.__file__)}",
        file=out,
    )
    print("-" * 68, file=out)

    for name, feature in [
        ("pil", "PIL CORE"),
        ("tkinter", "TKINTER"),
        ("freetype2", "FREETYPE2"),
        ("littlecms2", "LITTLECMS2"),
        ("webp", "WEBP"),
        ("avif", "AVIF"),
        ("jpg", "JPEG"),
        ("jpg_2000", "OPENJPEG (JPEG2000)"),
        ("zlib", "ZLIB (PNG/ZIP)"),
        ("libtiff", "LIBTIFF"),
        ("raqm", "RAQM (Bidirectional Text)"),
        ("libimagequant", "LIBIMAGEQUANT (Quantization method)"),
        ("xcb", "XCB (X protocol)"),
    ]:
        if check(name):
            v: str | None = None
            if name == "jpg":
                libjpeg_turbo_version = version_feature("libjpeg_turbo")
                if libjpeg_turbo_version is not None:
                    v = "mozjpeg" if check_feature("mozjpeg") else "libjpeg-turbo"
                    v += " " + libjpeg_turbo_version
            if v is None:
                v = version(name)
            if v is not None:
                version_static = name in ("pil", "jpg")
                if name == "littlecms2":
                    # this check is also in src/_imagingcms.c:setup_module()
                    version_static = tuple(int(x) for x in v.split(".")) < (2, 7)
                t = "compiled for" if version_static else "loaded"
                if name == "zlib":
                    zlib_ng_version = version_feature("zlib_ng")
                    if zlib_ng_version is not None:
                        v += ", compiled for zlib-ng " + zlib_ng_version
                elif name == "raqm":
                    for f in ("fribidi", "harfbuzz"):
                        v2 = version_feature(f)
                        if v2 is not None:
                            v += f", {f} {v2}"
                print("---", feature, "support ok,", t, v, file=out)
            else:
                print("---", feature, "support ok", file=out)
        else:
            print("***", feature, "support not installed", file=out)
    print("-" * 68, file=out)

    if supported_formats:
        extensions = collections.defaultdict(list)
        for ext, i in Image.EXTENSION.items():
            extensions[i].append(ext)

        for i in sorted(Image.ID):
            line = f"{i}"
            if i in Image.MIME:
                line = f"{line} {Image.MIME[i]}"
            print(line, file=out)

            if i in extensions:
                print(
                    "Extensions: {}".format(", ".join(sorted(extensions[i]))), file=out
                )

            features = []
            if i in Image.OPEN:
                features.append("open")
            if i in Image.SAVE:
                features.append("save")
            if i in Image.SAVE_ALL:
                features.append("save_all")
            if i in Image.DECODERS:
                features.append("decode")
            if i in Image.ENCODERS:
                features.append("encode")

            print("Features: {}".format(", ".join(features)), file=out)
            print("-" * 68, file=out)

# === NexusCore/openenv\Lib\site-packages\setuptools\_scripts.py ===
from __future__ import annotations

import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import textwrap
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypedDict

from ._importlib import metadata, resources

if TYPE_CHECKING:
    from typing_extensions import Self

from .warnings import SetuptoolsWarning

from distutils.command.build_scripts import first_line_re
from distutils.util import get_platform


class _SplitArgs(TypedDict, total=False):
    comments: bool
    posix: bool


class CommandSpec(list):
    """
    A command spec for a #! header, specified as a list of arguments akin to
    those passed to Popen.
    """

    options: list[str] = []
    split_args = _SplitArgs()

    @classmethod
    def best(cls):
        """
        Choose the best CommandSpec class based on environmental conditions.
        """
        return cls

    @classmethod
    def _sys_executable(cls):
        _default = os.path.normpath(sys.executable)
        return os.environ.get('__PYVENV_LAUNCHER__', _default)

    @classmethod
    def from_param(cls, param: Self | str | Iterable[str] | None) -> Self:
        """
        Construct a CommandSpec from a parameter to build_scripts, which may
        be None.
        """
        if isinstance(param, cls):
            return param
        if isinstance(param, str):
            return cls.from_string(param)
        if isinstance(param, Iterable):
            return cls(param)
        if param is None:
            return cls.from_environment()
        raise TypeError(f"Argument has an unsupported type {type(param)}")

    @classmethod
    def from_environment(cls):
        return cls([cls._sys_executable()])

    @classmethod
    def from_string(cls, string: str) -> Self:
        """
        Construct a command spec from a simple string representing a command
        line parseable by shlex.split.
        """
        items = shlex.split(string, **cls.split_args)
        return cls(items)

    def install_options(self, script_text: str):
        self.options = shlex.split(self._extract_options(script_text))
        cmdline = subprocess.list2cmdline(self)
        if not isascii(cmdline):
            self.options[:0] = ['-x']

    @staticmethod
    def _extract_options(orig_script):
        """
        Extract any options from the first line of the script.
        """
        first = (orig_script + '\n').splitlines()[0]
        match = _first_line_re().match(first)
        options = match.group(1) or '' if match else ''
        return options.strip()

    def as_header(self):
        return self._render(self + list(self.options))

    @staticmethod
    def _strip_quotes(item):
        _QUOTES = '"\''
        for q in _QUOTES:
            if item.startswith(q) and item.endswith(q):
                return item[1:-1]
        return item

    @staticmethod
    def _render(items):
        cmdline = subprocess.list2cmdline(
            CommandSpec._strip_quotes(item.strip()) for item in items
        )
        return '#!' + cmdline + '\n'


class WindowsCommandSpec(CommandSpec):
    split_args = _SplitArgs(posix=False)


class ScriptWriter:
    """
    Encapsulates behavior around writing entry point scripts for console and
    gui apps.
    """

    template = textwrap.dedent(
        r"""
        # EASY-INSTALL-ENTRY-SCRIPT: %(spec)r,%(group)r,%(name)r
        import re
        import sys

        # for compatibility with easy_install; see #2198
        __requires__ = %(spec)r

        try:
            from importlib.metadata import distribution
        except ImportError:
            try:
                from importlib_metadata import distribution
            except ImportError:
                from pkg_resources import load_entry_point


        def importlib_load_entry_point(spec, group, name):
            dist_name, _, _ = spec.partition('==')
            matches = (
                entry_point
                for entry_point in distribution(dist_name).entry_points
                if entry_point.group == group and entry_point.name == name
            )
            return next(matches).load()


        globals().setdefault('load_entry_point', importlib_load_entry_point)


        if __name__ == '__main__':
            sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
            sys.exit(load_entry_point(%(spec)r, %(group)r, %(name)r)())
        """
    ).lstrip()

    command_spec_class = CommandSpec

    @classmethod
    def get_args(cls, dist, header=None):
        """
        Yield write_script() argument tuples for a distribution's
        console_scripts and gui_scripts entry points.
        """

        # If distribution is not an importlib.metadata.Distribution, assume
        # it's a pkg_resources.Distribution and transform it.
        if not hasattr(dist, 'entry_points'):
            SetuptoolsWarning.emit("Unsupported distribution encountered.")
            dist = metadata.Distribution.at(dist.egg_info)

        if header is None:
            header = cls.get_header()
        spec = f'{dist.name}=={dist.version}'
        for type_ in 'console', 'gui':
            group = f'{type_}_scripts'
            for ep in dist.entry_points.select(group=group):
                name = ep.name
                cls._ensure_safe_name(ep.name)
                script_text = cls.template % locals()
                args = cls._get_script_args(type_, ep.name, header, script_text)
                yield from args

    @staticmethod
    def _ensure_safe_name(name):
        """
        Prevent paths in *_scripts entry point names.
        """
        has_path_sep = re.search(r'[\\/]', name)
        if has_path_sep:
            raise ValueError("Path separators not allowed in script names")

    @classmethod
    def best(cls):
        """
        Select the best ScriptWriter for this environment.
        """
        if sys.platform == 'win32' or (os.name == 'java' and os._name == 'nt'):
            return WindowsScriptWriter.best()
        else:
            return cls

    @classmethod
    def _get_script_args(cls, type_, name, header, script_text):
        # Simply write the stub with no extension.
        yield (name, header + script_text)

    @classmethod
    def get_header(
        cls,
        script_text: str = "",
        executable: str | CommandSpec | Iterable[str] | None = None,
    ) -> str:
        """Create a #! line, getting options (if any) from script_text"""
        cmd = cls.command_spec_class.best().from_param(executable)
        cmd.install_options(script_text)
        return cmd.as_header()


class WindowsScriptWriter(ScriptWriter):
    command_spec_class = WindowsCommandSpec

    @classmethod
    def best(cls):
        """
        Select the best ScriptWriter suitable for Windows
        """
        writer_lookup = dict(
            executable=WindowsExecutableLauncherWriter,
            natural=cls,
        )
        # for compatibility, use the executable launcher by default
        launcher = os.environ.get('SETUPTOOLS_LAUNCHER', 'executable')
        return writer_lookup[launcher]

    @classmethod
    def _get_script_args(cls, type_, name, header, script_text):
        "For Windows, add a .py extension"
        ext = dict(console='.pya', gui='.pyw')[type_]
        if ext not in os.environ['PATHEXT'].lower().split(';'):
            msg = (
                "{ext} not listed in PATHEXT; scripts will not be "
                "recognized as executables."
            ).format(**locals())
            SetuptoolsWarning.emit(msg)
        old = ['.pya', '.py', '-script.py', '.pyc', '.pyo', '.pyw', '.exe']
        old.remove(ext)
        header = cls._adjust_header(type_, header)
        blockers = [name + x for x in old]
        yield name + ext, header + script_text, 't', blockers

    @classmethod
    def _adjust_header(cls, type_, orig_header):
        """
        Make sure 'pythonw' is used for gui and 'python' is used for
        console (regardless of what sys.executable is).
        """
        pattern = 'pythonw.exe'
        repl = 'python.exe'
        if type_ == 'gui':
            pattern, repl = repl, pattern
        pattern_ob = re.compile(re.escape(pattern), re.IGNORECASE)
        new_header = pattern_ob.sub(string=orig_header, repl=repl)
        return new_header if cls._use_header(new_header) else orig_header

    @staticmethod
    def _use_header(new_header):
        """
        Should _adjust_header use the replaced header?

        On non-windows systems, always use. On
        Windows systems, only use the replaced header if it resolves
        to an executable on the system.
        """
        clean_header = new_header[2:-1].strip('"')
        return sys.platform != 'win32' or shutil.which(clean_header)


class WindowsExecutableLauncherWriter(WindowsScriptWriter):
    @classmethod
    def _get_script_args(cls, type_, name, header, script_text):
        """
        For Windows, add a .py extension and an .exe launcher
        """
        if type_ == 'gui':
            launcher_type = 'gui'
            ext = '-script.pyw'
            old = ['.pyw']
        else:
            launcher_type = 'cli'
            ext = '-script.py'
            old = ['.py', '.pyc', '.pyo']
        hdr = cls._adjust_header(type_, header)
        blockers = [name + x for x in old]
        yield (name + ext, hdr + script_text, 't', blockers)
        yield (
            name + '.exe',
            get_win_launcher(launcher_type),
            'b',  # write in binary mode
        )
        if not is_64bit():
            # install a manifest for the launcher to prevent Windows
            # from detecting it as an installer (which it will for
            #  launchers like easy_install.exe). Consider only
            #  adding a manifest for launchers detected as installers.
            #  See Distribute #143 for details.
            m_name = name + '.exe.manifest'
            yield (m_name, load_launcher_manifest(name), 't')


def get_win_launcher(type):
    """
    Load the Windows launcher (executable) suitable for launching a script.

    `type` should be either 'cli' or 'gui'

    Returns the executable as a byte string.
    """
    launcher_fn = f'{type}.exe'
    if is_64bit():
        if get_platform() == "win-arm64":
            launcher_fn = launcher_fn.replace(".", "-arm64.")
        else:
            launcher_fn = launcher_fn.replace(".", "-64.")
    else:
        launcher_fn = launcher_fn.replace(".", "-32.")
    return resources.files('setuptools').joinpath(launcher_fn).read_bytes()


def load_launcher_manifest(name):
    res = resources.files(__name__).joinpath('launcher manifest.xml')
    return res.read_text(encoding='utf-8') % vars()


def _first_line_re():
    """
    Return a regular expression based on first_line_re suitable for matching
    strings.
    """
    if isinstance(first_line_re.pattern, str):
        return first_line_re

    # first_line_re in Python >=3.1.4 and >=3.2.1 is a bytes pattern.
    return re.compile(first_line_re.pattern.decode())


def is_64bit():
    return struct.calcsize("P") == 8


def isascii(s):
    try:
        s.encode('ascii')
    except UnicodeError:
        return False
    return True

# === NexusCore/openenv\Lib\site-packages\IPython\external\pickleshare.py ===
#!/usr/bin/env python

"""PickleShare - a small 'shelve' like datastore with concurrency support

Like shelve, a PickleShareDB object acts like a normal dictionary. Unlike
shelve, many processes can access the database simultaneously. Changing a
value in database is immediately visible to other processes accessing the
same database.

Concurrency is possible because the values are stored in separate files. Hence
the "database" is a directory where *all* files are governed by PickleShare.

Example usage::

    from pickleshare import *
    db = PickleShareDB('~/testpickleshare')
    db.clear()
    print "Should be empty:",db.items()
    db['hello'] = 15
    db['aku ankka'] = [1,2,313]
    db['paths/are/ok/key'] = [1,(5,46)]
    print db.keys()
    del db['aku ankka']

This module is certainly not ZODB, but can be used for low-load
(non-mission-critical) situations where tiny code size trumps the
advanced features of a "real" object database.

Installation guide: pip install pickleshare

Author: Ville Vainio <vivainio@gmail.com>
License: MIT open source license.

"""

from __future__ import print_function


__version__ = "0.7.5"

try:
    from pathlib import Path
except ImportError:
    # Python 2 backport
    from pathlib2 import Path

import os, stat, time

try:
    import collections.abc as collections_abc
except ImportError:
    import collections as collections_abc
try:
    import cPickle as pickle
except ImportError:
    import pickle
import errno
import sys

if sys.version_info[0] >= 3:
    string_types = (str,)
else:
    string_types = (str, unicode)


def gethashfile(key):
    return ("%02x" % abs(hash(key) % 256))[-2:]


_sentinel = object()


class PickleShareDB(collections_abc.MutableMapping):
    """The main 'connection' object for PickleShare database"""

    def __init__(self, root):
        """Return a db object that will manage the specied directory"""
        if not isinstance(root, string_types):
            root = str(root)
        root = os.path.abspath(os.path.expanduser(root))
        self.root = Path(root)
        if not self.root.is_dir():
            # catching the exception is necessary if multiple processes are concurrently trying to create a folder
            # exists_ok keyword argument of mkdir does the same but only from Python 3.5
            try:
                self.root.mkdir(parents=True)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        # cache has { 'key' : (obj, orig_mod_time) }
        self.cache = {}

    def __getitem__(self, key):
        """db['key'] reading"""
        fil = self.root / key
        try:
            mtime = fil.stat()[stat.ST_MTIME]
        except OSError:
            raise KeyError(key)

        if fil in self.cache and mtime == self.cache[fil][1]:
            return self.cache[fil][0]
        try:
            # The cached item has expired, need to read
            with fil.open("rb") as f:
                obj = pickle.loads(f.read())
        except:
            raise KeyError(key)

        self.cache[fil] = (obj, mtime)
        return obj

    def __setitem__(self, key, value):
        """db['key'] = 5"""
        fil = self.root / key
        parent = fil.parent
        if parent and not parent.is_dir():
            parent.mkdir(parents=True)
        # We specify protocol 2, so that we can mostly go between Python 2
        # and Python 3. We can upgrade to protocol 3 when Python 2 is obsolete.
        with fil.open("wb") as f:
            pickle.dump(value, f, protocol=2)
        try:
            self.cache[fil] = (value, fil.stat().st_mtime)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def hset(self, hashroot, key, value):
        """hashed set"""
        hroot = self.root / hashroot
        if not hroot.is_dir():
            hroot.mkdir()
        hfile = hroot / gethashfile(key)
        d = self.get(hfile, {})
        d.update({key: value})
        self[hfile] = d

    def hget(self, hashroot, key, default=_sentinel, fast_only=True):
        """hashed get"""
        hroot = self.root / hashroot
        hfile = hroot / gethashfile(key)

        d = self.get(hfile, _sentinel)
        # print "got dict",d,"from",hfile
        if d is _sentinel:
            if fast_only:
                if default is _sentinel:
                    raise KeyError(key)

                return default

            # slow mode ok, works even after hcompress()
            d = self.hdict(hashroot)

        return d.get(key, default)

    def hdict(self, hashroot):
        """Get all data contained in hashed category 'hashroot' as dict"""
        hfiles = self.keys(hashroot + "/*")
        hfiles.sort()
        last = len(hfiles) and hfiles[-1] or ""
        if last.endswith("xx"):
            # print "using xx"
            hfiles = [last] + hfiles[:-1]

        all = {}

        for f in hfiles:
            # print "using",f
            try:
                all.update(self[f])
            except KeyError:
                print("Corrupt", f, "deleted - hset is not threadsafe!")
                del self[f]

            self.uncache(f)

        return all

    def hcompress(self, hashroot):
        """Compress category 'hashroot', so hset is fast again

        hget will fail if fast_only is True for compressed items (that were
        hset before hcompress).

        """
        hfiles = self.keys(hashroot + "/*")
        all = {}
        for f in hfiles:
            # print "using",f
            all.update(self[f])
            self.uncache(f)

        self[hashroot + "/xx"] = all
        for f in hfiles:
            p = self.root / f
            if p.name == "xx":
                continue
            p.unlink()

    def __delitem__(self, key):
        """del db["key"]"""
        fil = self.root / key
        self.cache.pop(fil, None)
        try:
            fil.unlink()
        except OSError:
            # notfound and permission denied are ok - we
            # lost, the other process wins the conflict
            pass

    def _normalized(self, p):
        """Make a key suitable for user's eyes"""
        return str(p.relative_to(self.root)).replace("\\", "/")

    def keys(self, globpat=None):
        """All keys in DB, or all keys matching a glob"""

        if globpat is None:
            files = self.root.rglob("*")
        else:
            files = self.root.glob(globpat)
        return [self._normalized(p) for p in files if p.is_file()]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def uncache(self, *items):
        """Removes all, or specified items from cache

        Use this after reading a large amount of large objects
        to free up memory, when you won't be needing the objects
        for a while.

        """
        if not items:
            self.cache = {}
        for it in items:
            self.cache.pop(it, None)

    def waitget(self, key, maxwaittime=60):
        """Wait (poll) for a key to get a value

        Will wait for `maxwaittime` seconds before raising a KeyError.
        The call exits normally if the `key` field in db gets a value
        within the timeout period.

        Use this for synchronizing different processes or for ensuring
        that an unfortunately timed "db['key'] = newvalue" operation
        in another process (which causes all 'get' operation to cause a
        KeyError for the duration of pickling) won't screw up your program
        logic.
        """

        wtimes = [0.2] * 3 + [0.5] * 2 + [1]
        tries = 0
        waited = 0
        while 1:
            try:
                val = self[key]
                return val
            except KeyError:
                pass

            if waited > maxwaittime:
                raise KeyError(key)

            time.sleep(wtimes[tries])
            waited += wtimes[tries]
            if tries < len(wtimes) - 1:
                tries += 1

    def getlink(self, folder):
        """Get a convenient link for accessing items"""
        return PickleShareLink(self, folder)

    def __repr__(self):
        return "PickleShareDB('%s')" % self.root


class PickleShareLink:
    """A shortdand for accessing nested PickleShare data conveniently.

    Created through PickleShareDB.getlink(), example::

        lnk = db.getlink('myobjects/test')
        lnk.foo = 2
        lnk.bar = lnk.foo + 5

    """

    def __init__(self, db, keydir):
        self.__dict__.update(locals())

    def __getattr__(self, key):
        return self.__dict__["db"][self.__dict__["keydir"] + "/" + key]

    def __setattr__(self, key, val):
        self.db[self.keydir + "/" + key] = val

    def __repr__(self):
        db = self.__dict__["db"]
        keys = db.keys(self.__dict__["keydir"] + "/*")
        return "<PickleShareLink '%s': %s>" % (
            self.__dict__["keydir"],
            ";".join([Path(k).basename() for k in keys]),
        )


def main():
    import textwrap

    usage = textwrap.dedent(
        """\
    pickleshare - manage PickleShare databases

    Usage:

        pickleshare dump /path/to/db > dump.txt
        pickleshare load /path/to/db < dump.txt
        pickleshare test /path/to/db
    """
    )
    DB = PickleShareDB
    import sys

    if len(sys.argv) < 2:
        print(usage)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "dump":
        if not args:
            args = ["."]
        db = DB(args[0])
        import pprint

        pprint.pprint(db.items())
    elif cmd == "load":
        cont = sys.stdin.read()
        db = DB(args[0])
        data = eval(cont)
        db.clear()
        for k, v in db.items():
            db[k] = v
    elif cmd == "testwait":
        db = DB(args[0])
        db.clear()
        print(db.waitget("250"))
    elif cmd == "test":
        test()
        stress()


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\nltk\stem\arlstem.py ===
#
# Natural Language Toolkit: ARLSTem Stemmer
#
# Copyright (C) 2001-2024 NLTK Project
#
# Author: Kheireddine Abainia (x-programer) <k.abainia@gmail.com>
# Algorithms: Kheireddine Abainia <k.abainia@gmail.com>
#                         Siham Ouamour
#                         Halim Sayoud
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
ARLSTem Arabic Stemmer
The details about the implementation of this algorithm are described in:
K. Abainia, S. Ouamour and H. Sayoud, A Novel Robust Arabic Light Stemmer ,
Journal of Experimental & Theoretical Artificial Intelligence (JETAI'17),
Vol. 29, No. 3, 2017, pp. 557-573.
The ARLSTem is a light Arabic stemmer that is based on removing the affixes
from the word (i.e. prefixes, suffixes and infixes). It was evaluated and
compared to several other stemmers using Paice's parameters (under-stemming
index, over-stemming index and stemming weight), and the results showed that
ARLSTem is promising and producing high performances. This stemmer is not
based on any dictionary and can be used on-line effectively.
"""
import re

from nltk.stem.api import StemmerI


class ARLSTem(StemmerI):
    """
    ARLSTem stemmer : a light Arabic Stemming algorithm without any dictionary.
    Department of Telecommunication & Information Processing. USTHB University,
    Algiers, Algeria.
    ARLSTem.stem(token) returns the Arabic stem for the input token.
    The ARLSTem Stemmer requires that all tokens are encoded using Unicode
    encoding.
    """

    def __init__(self):
        # different Alif with hamza
        self.re_hamzated_alif = re.compile(r"[\u0622\u0623\u0625]")
        self.re_alifMaqsura = re.compile(r"[\u0649]")
        self.re_diacritics = re.compile(r"[\u064B-\u065F]")

        # Alif Laam, Laam Laam, Fa Laam, Fa Ba
        self.pr2 = ["\u0627\u0644", "\u0644\u0644", "\u0641\u0644", "\u0641\u0628"]
        # Ba Alif Laam, Kaaf Alif Laam, Waaw Alif Laam
        self.pr3 = ["\u0628\u0627\u0644", "\u0643\u0627\u0644", "\u0648\u0627\u0644"]
        # Fa Laam Laam, Waaw Laam Laam
        self.pr32 = ["\u0641\u0644\u0644", "\u0648\u0644\u0644"]
        # Fa Ba Alif Laam, Waaw Ba Alif Laam, Fa Kaaf Alif Laam
        self.pr4 = [
            "\u0641\u0628\u0627\u0644",
            "\u0648\u0628\u0627\u0644",
            "\u0641\u0643\u0627\u0644",
        ]

        # Kaf Yaa, Kaf Miim
        self.su2 = ["\u0643\u064A", "\u0643\u0645"]
        # Ha Alif, Ha Miim
        self.su22 = ["\u0647\u0627", "\u0647\u0645"]
        # Kaf Miim Alif, Kaf Noon Shadda
        self.su3 = ["\u0643\u0645\u0627", "\u0643\u0646\u0651"]
        # Ha Miim Alif, Ha Noon Shadda
        self.su32 = ["\u0647\u0645\u0627", "\u0647\u0646\u0651"]

        # Alif Noon, Ya Noon, Waaw Noon
        self.pl_si2 = ["\u0627\u0646", "\u064A\u0646", "\u0648\u0646"]
        # Taa Alif Noon, Taa Ya Noon
        self.pl_si3 = ["\u062A\u0627\u0646", "\u062A\u064A\u0646"]

        # Alif Noon, Waaw Noon
        self.verb_su2 = ["\u0627\u0646", "\u0648\u0646"]
        # Siin Taa, Siin Yaa
        self.verb_pr2 = ["\u0633\u062A", "\u0633\u064A"]
        # Siin Alif, Siin Noon
        self.verb_pr22 = ["\u0633\u0627", "\u0633\u0646"]
        # Lam Noon, Lam Taa, Lam Yaa, Lam Hamza
        self.verb_pr33 = [
            "\u0644\u0646",
            "\u0644\u062A",
            "\u0644\u064A",
            "\u0644\u0623",
        ]
        # Taa Miim Alif, Taa Noon Shadda
        self.verb_suf3 = ["\u062A\u0645\u0627", "\u062A\u0646\u0651"]
        # Noon Alif, Taa Miim, Taa Alif, Waaw Alif
        self.verb_suf2 = [
            "\u0646\u0627",
            "\u062A\u0645",
            "\u062A\u0627",
            "\u0648\u0627",
        ]
        # Taa, Alif, Noon
        self.verb_suf1 = ["\u062A", "\u0627", "\u0646"]

    def stem(self, token):
        """
        call this function to get the word's stem based on ARLSTem .
        """
        try:
            if token is None:
                raise ValueError(
                    "The word could not be stemmed, because \
                                 it is empty !"
                )
            # remove Arabic diacritics and replace some letters with others
            token = self.norm(token)
            # strip common prefixes of the nouns
            pre = self.pref(token)
            if pre is not None:
                token = pre
            # strip the suffixes which are common to nouns and verbs
            token = self.suff(token)
            # transform a plural noun to a singular noun
            ps = self.plur2sing(token)
            if ps is None:
                # transform from the feminine form to the masculine form
                fm = self.fem2masc(token)
                if fm is not None:
                    return fm
                else:
                    if pre is None:  # if the prefixes are not stripped
                        # strip the verb prefixes and suffixes
                        return self.verb(token)
            else:
                return ps
            return token
        except ValueError as e:
            print(e)

    def norm(self, token):
        """
        normalize the word by removing diacritics, replacing hamzated Alif
        with Alif replacing AlifMaqsura with Yaa and removing Waaw at the
        beginning.
        """
        # strip Arabic diacritics
        token = self.re_diacritics.sub("", token)
        # replace Hamzated Alif with Alif bare
        token = self.re_hamzated_alif.sub("\u0627", token)
        # replace alifMaqsura with Yaa
        token = self.re_alifMaqsura.sub("\u064A", token)
        # strip the Waaw from the word beginning if the remaining is 3 letters
        # at least
        if token.startswith("\u0648") and len(token) > 3:
            token = token[1:]
        return token

    def pref(self, token):
        """
        remove prefixes from the words' beginning.
        """
        if len(token) > 5:
            for p3 in self.pr3:
                if token.startswith(p3):
                    return token[3:]
        if len(token) > 6:
            for p4 in self.pr4:
                if token.startswith(p4):
                    return token[4:]
        if len(token) > 5:
            for p3 in self.pr32:
                if token.startswith(p3):
                    return token[3:]
        if len(token) > 4:
            for p2 in self.pr2:
                if token.startswith(p2):
                    return token[2:]

    def suff(self, token):
        """
        remove suffixes from the word's end.
        """
        if token.endswith("\u0643") and len(token) > 3:
            return token[:-1]
        if len(token) > 4:
            for s2 in self.su2:
                if token.endswith(s2):
                    return token[:-2]
        if len(token) > 5:
            for s3 in self.su3:
                if token.endswith(s3):
                    return token[:-3]
        if token.endswith("\u0647") and len(token) > 3:
            token = token[:-1]
            return token
        if len(token) > 4:
            for s2 in self.su22:
                if token.endswith(s2):
                    return token[:-2]
        if len(token) > 5:
            for s3 in self.su32:
                if token.endswith(s3):
                    return token[:-3]
        if token.endswith("\u0646\u0627") and len(token) > 4:
            return token[:-2]
        return token

    def fem2masc(self, token):
        """
        transform the word from the feminine form to the masculine form.
        """
        if token.endswith("\u0629") and len(token) > 3:
            return token[:-1]

    def plur2sing(self, token):
        """
        transform the word from the plural form to the singular form.
        """
        if len(token) > 4:
            for ps2 in self.pl_si2:
                if token.endswith(ps2):
                    return token[:-2]
        if len(token) > 5:
            for ps3 in self.pl_si3:
                if token.endswith(ps3):
                    return token[:-3]
        if len(token) > 3 and token.endswith("\u0627\u062A"):
            return token[:-2]
        if len(token) > 3 and token.startswith("\u0627") and token[2] == "\u0627":
            return token[:2] + token[3:]
        if len(token) > 4 and token.startswith("\u0627") and token[-2] == "\u0627":
            return token[1:-2] + token[-1]

    def verb(self, token):
        """
        stem the verb prefixes and suffixes or both
        """
        vb = self.verb_t1(token)
        if vb is not None:
            return vb
        vb = self.verb_t2(token)
        if vb is not None:
            return vb
        vb = self.verb_t3(token)
        if vb is not None:
            return vb
        vb = self.verb_t4(token)
        if vb is not None:
            return vb
        vb = self.verb_t5(token)
        if vb is not None:
            return vb
        return self.verb_t6(token)

    def verb_t1(self, token):
        """
        stem the present prefixes and suffixes
        """
        if len(token) > 5 and token.startswith("\u062A"):  # Taa
            for s2 in self.pl_si2:
                if token.endswith(s2):
                    return token[1:-2]
        if len(token) > 5 and token.startswith("\u064A"):  # Yaa
            for s2 in self.verb_su2:
                if token.endswith(s2):
                    return token[1:-2]
        if len(token) > 4 and token.startswith("\u0627"):  # Alif
            # Waaw Alif
            if len(token) > 5 and token.endswith("\u0648\u0627"):
                return token[1:-2]
            # Yaa
            if token.endswith("\u064A"):
                return token[1:-1]
            # Alif
            if token.endswith("\u0627"):
                return token[1:-1]
            # Noon
            if token.endswith("\u0646"):
                return token[1:-1]
        # ^Yaa, Noon$
        if len(token) > 4 and token.startswith("\u064A") and token.endswith("\u0646"):
            return token[1:-1]
        # ^Taa, Noon$
        if len(token) > 4 and token.startswith("\u062A") and token.endswith("\u0646"):
            return token[1:-1]

    def verb_t2(self, token):
        """
        stem the future prefixes and suffixes
        """
        if len(token) > 6:
            for s2 in self.pl_si2:
                # ^Siin Taa
                if token.startswith(self.verb_pr2[0]) and token.endswith(s2):
                    return token[2:-2]
            # ^Siin Yaa, Alif Noon$
            if token.startswith(self.verb_pr2[1]) and token.endswith(self.pl_si2[0]):
                return token[2:-2]
            # ^Siin Yaa, Waaw Noon$
            if token.startswith(self.verb_pr2[1]) and token.endswith(self.pl_si2[2]):
                return token[2:-2]
        # ^Siin Taa, Noon$
        if (
            len(token) > 5
            and token.startswith(self.verb_pr2[0])
            and token.endswith("\u0646")
        ):
            return token[2:-1]
        # ^Siin Yaa, Noon$
        if (
            len(token) > 5
            and token.startswith(self.verb_pr2[1])
            and token.endswith("\u0646")
        ):
            return token[2:-1]

    def verb_t3(self, token):
        """
        stem the present suffixes
        """
        if len(token) > 5:
            for su3 in self.verb_suf3:
                if token.endswith(su3):
                    return token[:-3]
        if len(token) > 4:
            for su2 in self.verb_suf2:
                if token.endswith(su2):
                    return token[:-2]
        if len(token) > 3:
            for su1 in self.verb_suf1:
                if token.endswith(su1):
                    return token[:-1]

    def verb_t4(self, token):
        """
        stem the present prefixes
        """
        if len(token) > 3:
            for pr1 in self.verb_suf1:
                if token.startswith(pr1):
                    return token[1:]
            if token.startswith("\u064A"):
                return token[1:]

    def verb_t5(self, token):
        """
        stem the future prefixes
        """
        if len(token) > 4:
            for pr2 in self.verb_pr22:
                if token.startswith(pr2):
                    return token[2:]
            for pr2 in self.verb_pr2:
                if token.startswith(pr2):
                    return token[2:]
        return token

    def verb_t6(self, token):
        """
        stem the order prefixes
        """
        if len(token) > 4:
            for pr3 in self.verb_pr33:
                if token.startswith(pr3):
                    return token[2:]
        return token

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\class_validators.py ===
import warnings
from collections import ChainMap
from functools import partial, partialmethod, wraps
from itertools import chain
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Type, Union, overload

from pydantic.v1.errors import ConfigError
from pydantic.v1.typing import AnyCallable
from pydantic.v1.utils import ROOT_KEY, in_ipython

if TYPE_CHECKING:
    from pydantic.v1.typing import AnyClassMethod


class Validator:
    __slots__ = 'func', 'pre', 'each_item', 'always', 'check_fields', 'skip_on_failure'

    def __init__(
        self,
        func: AnyCallable,
        pre: bool = False,
        each_item: bool = False,
        always: bool = False,
        check_fields: bool = False,
        skip_on_failure: bool = False,
    ):
        self.func = func
        self.pre = pre
        self.each_item = each_item
        self.always = always
        self.check_fields = check_fields
        self.skip_on_failure = skip_on_failure


if TYPE_CHECKING:
    from inspect import Signature

    from pydantic.v1.config import BaseConfig
    from pydantic.v1.fields import ModelField
    from pydantic.v1.types import ModelOrDc

    ValidatorCallable = Callable[[Optional[ModelOrDc], Any, Dict[str, Any], ModelField, Type[BaseConfig]], Any]
    ValidatorsList = List[ValidatorCallable]
    ValidatorListDict = Dict[str, List[Validator]]

_FUNCS: Set[str] = set()
VALIDATOR_CONFIG_KEY = '__validator_config__'
ROOT_VALIDATOR_CONFIG_KEY = '__root_validator_config__'


def validator(
    *fields: str,
    pre: bool = False,
    each_item: bool = False,
    always: bool = False,
    check_fields: bool = True,
    whole: Optional[bool] = None,
    allow_reuse: bool = False,
) -> Callable[[AnyCallable], 'AnyClassMethod']:
    """
    Decorate methods on the class indicating that they should be used to validate fields
    :param fields: which field(s) the method should be called on
    :param pre: whether or not this validator should be called before the standard validators (else after)
    :param each_item: for complex objects (sets, lists etc.) whether to validate individual elements rather than the
      whole object
    :param always: whether this method and other validators should be called even if the value is missing
    :param check_fields: whether to check that the fields actually exist on the model
    :param allow_reuse: whether to track and raise an error if another validator refers to the decorated function
    """
    if not fields:
        raise ConfigError('validator with no fields specified')
    elif isinstance(fields[0], FunctionType):
        raise ConfigError(
            "validators should be used with fields and keyword arguments, not bare. "  # noqa: Q000
            "E.g. usage should be `@validator('<field_name>', ...)`"
        )
    elif not all(isinstance(field, str) for field in fields):
        raise ConfigError(
            "validator fields should be passed as separate string args. "  # noqa: Q000
            "E.g. usage should be `@validator('<field_name_1>', '<field_name_2>', ...)`"
        )

    if whole is not None:
        warnings.warn(
            'The "whole" keyword argument is deprecated, use "each_item" (inverse meaning, default False) instead',
            DeprecationWarning,
        )
        assert each_item is False, '"each_item" and "whole" conflict, remove "whole"'
        each_item = not whole

    def dec(f: AnyCallable) -> 'AnyClassMethod':
        f_cls = _prepare_validator(f, allow_reuse)
        setattr(
            f_cls,
            VALIDATOR_CONFIG_KEY,
            (
                fields,
                Validator(func=f_cls.__func__, pre=pre, each_item=each_item, always=always, check_fields=check_fields),
            ),
        )
        return f_cls

    return dec


@overload
def root_validator(_func: AnyCallable) -> 'AnyClassMethod':
    ...


@overload
def root_validator(
    *, pre: bool = False, allow_reuse: bool = False, skip_on_failure: bool = False
) -> Callable[[AnyCallable], 'AnyClassMethod']:
    ...


def root_validator(
    _func: Optional[AnyCallable] = None, *, pre: bool = False, allow_reuse: bool = False, skip_on_failure: bool = False
) -> Union['AnyClassMethod', Callable[[AnyCallable], 'AnyClassMethod']]:
    """
    Decorate methods on a model indicating that they should be used to validate (and perhaps modify) data either
    before or after standard model parsing/validation is performed.
    """
    if _func:
        f_cls = _prepare_validator(_func, allow_reuse)
        setattr(
            f_cls, ROOT_VALIDATOR_CONFIG_KEY, Validator(func=f_cls.__func__, pre=pre, skip_on_failure=skip_on_failure)
        )
        return f_cls

    def dec(f: AnyCallable) -> 'AnyClassMethod':
        f_cls = _prepare_validator(f, allow_reuse)
        setattr(
            f_cls, ROOT_VALIDATOR_CONFIG_KEY, Validator(func=f_cls.__func__, pre=pre, skip_on_failure=skip_on_failure)
        )
        return f_cls

    return dec


def _prepare_validator(function: AnyCallable, allow_reuse: bool) -> 'AnyClassMethod':
    """
    Avoid validators with duplicated names since without this, validators can be overwritten silently
    which generally isn't the intended behaviour, don't run in ipython (see #312) or if allow_reuse is False.
    """
    f_cls = function if isinstance(function, classmethod) else classmethod(function)
    if not in_ipython() and not allow_reuse:
        ref = (
            getattr(f_cls.__func__, '__module__', '<No __module__>')
            + '.'
            + getattr(f_cls.__func__, '__qualname__', f'<No __qualname__: id:{id(f_cls.__func__)}>')
        )
        if ref in _FUNCS:
            raise ConfigError(f'duplicate validator function "{ref}"; if this is intended, set `allow_reuse=True`')
        _FUNCS.add(ref)
    return f_cls


class ValidatorGroup:
    def __init__(self, validators: 'ValidatorListDict') -> None:
        self.validators = validators
        self.used_validators = {'*'}

    def get_validators(self, name: str) -> Optional[Dict[str, Validator]]:
        self.used_validators.add(name)
        validators = self.validators.get(name, [])
        if name != ROOT_KEY:
            validators += self.validators.get('*', [])
        if validators:
            return {getattr(v.func, '__name__', f'<No __name__: id:{id(v.func)}>'): v for v in validators}
        else:
            return None

    def check_for_unused(self) -> None:
        unused_validators = set(
            chain.from_iterable(
                (
                    getattr(v.func, '__name__', f'<No __name__: id:{id(v.func)}>')
                    for v in self.validators[f]
                    if v.check_fields
                )
                for f in (self.validators.keys() - self.used_validators)
            )
        )
        if unused_validators:
            fn = ', '.join(unused_validators)
            raise ConfigError(
                f"Validators defined with incorrect fields: {fn} "  # noqa: Q000
                f"(use check_fields=False if you're inheriting from the model and intended this)"
            )


def extract_validators(namespace: Dict[str, Any]) -> Dict[str, List[Validator]]:
    validators: Dict[str, List[Validator]] = {}
    for var_name, value in namespace.items():
        validator_config = getattr(value, VALIDATOR_CONFIG_KEY, None)
        if validator_config:
            fields, v = validator_config
            for field in fields:
                if field in validators:
                    validators[field].append(v)
                else:
                    validators[field] = [v]
    return validators


def extract_root_validators(namespace: Dict[str, Any]) -> Tuple[List[AnyCallable], List[Tuple[bool, AnyCallable]]]:
    from inspect import signature

    pre_validators: List[AnyCallable] = []
    post_validators: List[Tuple[bool, AnyCallable]] = []
    for name, value in namespace.items():
        validator_config: Optional[Validator] = getattr(value, ROOT_VALIDATOR_CONFIG_KEY, None)
        if validator_config:
            sig = signature(validator_config.func)
            args = list(sig.parameters.keys())
            if args[0] == 'self':
                raise ConfigError(
                    f'Invalid signature for root validator {name}: {sig}, "self" not permitted as first argument, '
                    f'should be: (cls, values).'
                )
            if len(args) != 2:
                raise ConfigError(f'Invalid signature for root validator {name}: {sig}, should be: (cls, values).')
            # check function signature
            if validator_config.pre:
                pre_validators.append(validator_config.func)
            else:
                post_validators.append((validator_config.skip_on_failure, validator_config.func))
    return pre_validators, post_validators


def inherit_validators(base_validators: 'ValidatorListDict', validators: 'ValidatorListDict') -> 'ValidatorListDict':
    for field, field_validators in base_validators.items():
        if field not in validators:
            validators[field] = []
        validators[field] += field_validators
    return validators


def make_generic_validator(validator: AnyCallable) -> 'ValidatorCallable':
    """
    Make a generic function which calls a validator with the right arguments.

    Unfortunately other approaches (eg. return a partial of a function that builds the arguments) is slow,
    hence this laborious way of doing things.

    It's done like this so validators don't all need **kwargs in their signature, eg. any combination of
    the arguments "values", "fields" and/or "config" are permitted.
    """
    from inspect import signature

    if not isinstance(validator, (partial, partialmethod)):
        # This should be the default case, so overhead is reduced
        sig = signature(validator)
        args = list(sig.parameters.keys())
    else:
        # Fix the generated argument lists of partial methods
        sig = signature(validator.func)
        args = [
            k
            for k in signature(validator.func).parameters.keys()
            if k not in validator.args | validator.keywords.keys()
        ]

    first_arg = args.pop(0)
    if first_arg == 'self':
        raise ConfigError(
            f'Invalid signature for validator {validator}: {sig}, "self" not permitted as first argument, '
            f'should be: (cls, value, values, config, field), "values", "config" and "field" are all optional.'
        )
    elif first_arg == 'cls':
        # assume the second argument is value
        return wraps(validator)(_generic_validator_cls(validator, sig, set(args[1:])))
    else:
        # assume the first argument was value which has already been removed
        return wraps(validator)(_generic_validator_basic(validator, sig, set(args)))


def prep_validators(v_funcs: Iterable[AnyCallable]) -> 'ValidatorsList':
    return [make_generic_validator(f) for f in v_funcs if f]


all_kwargs = {'values', 'field', 'config'}


def _generic_validator_cls(validator: AnyCallable, sig: 'Signature', args: Set[str]) -> 'ValidatorCallable':
    # assume the first argument is value
    has_kwargs = False
    if 'kwargs' in args:
        has_kwargs = True
        args -= {'kwargs'}

    if not args.issubset(all_kwargs):
        raise ConfigError(
            f'Invalid signature for validator {validator}: {sig}, should be: '
            f'(cls, value, values, config, field), "values", "config" and "field" are all optional.'
        )

    if has_kwargs:
        return lambda cls, v, values, field, config: validator(cls, v, values=values, field=field, config=config)
    elif args == set():
        return lambda cls, v, values, field, config: validator(cls, v)
    elif args == {'values'}:
        return lambda cls, v, values, field, config: validator(cls, v, values=values)
    elif args == {'field'}:
        return lambda cls, v, values, field, config: validator(cls, v, field=field)
    elif args == {'config'}:
        return lambda cls, v, values, field, config: validator(cls, v, config=config)
    elif args == {'values', 'field'}:
        return lambda cls, v, values, field, config: validator(cls, v, values=values, field=field)
    elif args == {'values', 'config'}:
        return lambda cls, v, values, field, config: validator(cls, v, values=values, config=config)
    elif args == {'field', 'config'}:
        return lambda cls, v, values, field, config: validator(cls, v, field=field, config=config)
    else:
        # args == {'values', 'field', 'config'}
        return lambda cls, v, values, field, config: validator(cls, v, values=values, field=field, config=config)


def _generic_validator_basic(validator: AnyCallable, sig: 'Signature', args: Set[str]) -> 'ValidatorCallable':
    has_kwargs = False
    if 'kwargs' in args:
        has_kwargs = True
        args -= {'kwargs'}

    if not args.issubset(all_kwargs):
        raise ConfigError(
            f'Invalid signature for validator {validator}: {sig}, should be: '
            f'(value, values, config, field), "values", "config" and "field" are all optional.'
        )

    if has_kwargs:
        return lambda cls, v, values, field, config: validator(v, values=values, field=field, config=config)
    elif args == set():
        return lambda cls, v, values, field, config: validator(v)
    elif args == {'values'}:
        return lambda cls, v, values, field, config: validator(v, values=values)
    elif args == {'field'}:
        return lambda cls, v, values, field, config: validator(v, field=field)
    elif args == {'config'}:
        return lambda cls, v, values, field, config: validator(v, config=config)
    elif args == {'values', 'field'}:
        return lambda cls, v, values, field, config: validator(v, values=values, field=field)
    elif args == {'values', 'config'}:
        return lambda cls, v, values, field, config: validator(v, values=values, config=config)
    elif args == {'field', 'config'}:
        return lambda cls, v, values, field, config: validator(v, field=field, config=config)
    else:
        # args == {'values', 'field', 'config'}
        return lambda cls, v, values, field, config: validator(v, values=values, field=field, config=config)


def gather_all_validators(type_: 'ModelOrDc') -> Dict[str, 'AnyClassMethod']:
    all_attributes = ChainMap(*[cls.__dict__ for cls in type_.__mro__])  # type: ignore[arg-type,var-annotated]
    return {
        k: v
        for k, v in all_attributes.items()
        if hasattr(v, VALIDATOR_CONFIG_KEY) or hasattr(v, ROOT_VALIDATOR_CONFIG_KEY)
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\jaraco\context.py ===
from __future__ import annotations

import contextlib
import functools
import operator
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import warnings
from typing import Iterator


if sys.version_info < (3, 12):
    from backports import tarfile
else:
    import tarfile


@contextlib.contextmanager
def pushd(dir: str | os.PathLike) -> Iterator[str | os.PathLike]:
    """
    >>> tmp_path = getfixture('tmp_path')
    >>> with pushd(tmp_path):
    ...     assert os.getcwd() == os.fspath(tmp_path)
    >>> assert os.getcwd() != os.fspath(tmp_path)
    """

    orig = os.getcwd()
    os.chdir(dir)
    try:
        yield dir
    finally:
        os.chdir(orig)


@contextlib.contextmanager
def tarball(
    url, target_dir: str | os.PathLike | None = None
) -> Iterator[str | os.PathLike]:
    """
    Get a tarball, extract it, yield, then clean up.

    >>> import urllib.request
    >>> url = getfixture('tarfile_served')
    >>> target = getfixture('tmp_path') / 'out'
    >>> tb = tarball(url, target_dir=target)
    >>> import pathlib
    >>> with tb as extracted:
    ...     contents = pathlib.Path(extracted, 'contents.txt').read_text(encoding='utf-8')
    >>> assert not os.path.exists(extracted)
    """
    if target_dir is None:
        target_dir = os.path.basename(url).replace('.tar.gz', '').replace('.tgz', '')
    # In the tar command, use --strip-components=1 to strip the first path and
    #  then
    #  use -C to cause the files to be extracted to {target_dir}. This ensures
    #  that we always know where the files were extracted.
    os.mkdir(target_dir)
    try:
        req = urllib.request.urlopen(url)
        with tarfile.open(fileobj=req, mode='r|*') as tf:
            tf.extractall(path=target_dir, filter=strip_first_component)
        yield target_dir
    finally:
        shutil.rmtree(target_dir)


def strip_first_component(
    member: tarfile.TarInfo,
    path,
) -> tarfile.TarInfo:
    _, member.name = member.name.split('/', 1)
    return member


def _compose(*cmgrs):
    """
    Compose any number of dependent context managers into a single one.

    The last, innermost context manager may take arbitrary arguments, but
    each successive context manager should accept the result from the
    previous as a single parameter.

    Like :func:`jaraco.functools.compose`, behavior works from right to
    left, so the context manager should be indicated from outermost to
    innermost.

    Example, to create a context manager to change to a temporary
    directory:

    >>> temp_dir_as_cwd = _compose(pushd, temp_dir)
    >>> with temp_dir_as_cwd() as dir:
    ...     assert os.path.samefile(os.getcwd(), dir)
    """

    def compose_two(inner, outer):
        def composed(*args, **kwargs):
            with inner(*args, **kwargs) as saved, outer(saved) as res:
                yield res

        return contextlib.contextmanager(composed)

    return functools.reduce(compose_two, reversed(cmgrs))


tarball_cwd = _compose(pushd, tarball)


@contextlib.contextmanager
def tarball_context(*args, **kwargs):
    warnings.warn(
        "tarball_context is deprecated. Use tarball or tarball_cwd instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pushd_ctx = kwargs.pop('pushd', pushd)
    with tarball(*args, **kwargs) as tball, pushd_ctx(tball) as dir:
        yield dir


def infer_compression(url):
    """
    Given a URL or filename, infer the compression code for tar.

    >>> infer_compression('http://foo/bar.tar.gz')
    'z'
    >>> infer_compression('http://foo/bar.tgz')
    'z'
    >>> infer_compression('file.bz')
    'j'
    >>> infer_compression('file.xz')
    'J'
    """
    warnings.warn(
        "infer_compression is deprecated with no replacement",
        DeprecationWarning,
        stacklevel=2,
    )
    # cheat and just assume it's the last two characters
    compression_indicator = url[-2:]
    mapping = dict(gz='z', bz='j', xz='J')
    # Assume 'z' (gzip) if no match
    return mapping.get(compression_indicator, 'z')


@contextlib.contextmanager
def temp_dir(remover=shutil.rmtree):
    """
    Create a temporary directory context. Pass a custom remover
    to override the removal behavior.

    >>> import pathlib
    >>> with temp_dir() as the_dir:
    ...     assert os.path.isdir(the_dir)
    ...     _ = pathlib.Path(the_dir).joinpath('somefile').write_text('contents', encoding='utf-8')
    >>> assert not os.path.exists(the_dir)
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        remover(temp_dir)


@contextlib.contextmanager
def repo_context(url, branch=None, quiet=True, dest_ctx=temp_dir):
    """
    Check out the repo indicated by url.

    If dest_ctx is supplied, it should be a context manager
    to yield the target directory for the check out.
    """
    exe = 'git' if 'git' in url else 'hg'
    with dest_ctx() as repo_dir:
        cmd = [exe, 'clone', url, repo_dir]
        if branch:
            cmd.extend(['--branch', branch])
        devnull = open(os.path.devnull, 'w')
        stdout = devnull if quiet else None
        subprocess.check_call(cmd, stdout=stdout)
        yield repo_dir


def null():
    """
    A null context suitable to stand in for a meaningful context.

    >>> with null() as value:
    ...     assert value is None

    This context is most useful when dealing with two or more code
    branches but only some need a context. Wrap the others in a null
    context to provide symmetry across all options.
    """
    warnings.warn(
        "null is deprecated. Use contextlib.nullcontext",
        DeprecationWarning,
        stacklevel=2,
    )
    return contextlib.nullcontext()


class ExceptionTrap:
    """
    A context manager that will catch certain exceptions and provide an
    indication they occurred.

    >>> with ExceptionTrap() as trap:
    ...     raise Exception()
    >>> bool(trap)
    True

    >>> with ExceptionTrap() as trap:
    ...     pass
    >>> bool(trap)
    False

    >>> with ExceptionTrap(ValueError) as trap:
    ...     raise ValueError("1 + 1 is not 3")
    >>> bool(trap)
    True
    >>> trap.value
    ValueError('1 + 1 is not 3')
    >>> trap.tb
    <traceback object at ...>

    >>> with ExceptionTrap(ValueError) as trap:
    ...     raise Exception()
    Traceback (most recent call last):
    ...
    Exception

    >>> bool(trap)
    False
    """

    exc_info = None, None, None

    def __init__(self, exceptions=(Exception,)):
        self.exceptions = exceptions

    def __enter__(self):
        return self

    @property
    def type(self):
        return self.exc_info[0]

    @property
    def value(self):
        return self.exc_info[1]

    @property
    def tb(self):
        return self.exc_info[2]

    def __exit__(self, *exc_info):
        type = exc_info[0]
        matches = type and issubclass(type, self.exceptions)
        if matches:
            self.exc_info = exc_info
        return matches

    def __bool__(self):
        return bool(self.type)

    def raises(self, func, *, _test=bool):
        """
        Wrap func and replace the result with the truth
        value of the trap (True if an exception occurred).

        First, give the decorator an alias to support Python 3.8
        Syntax.

        >>> raises = ExceptionTrap(ValueError).raises

        Now decorate a function that always fails.

        >>> @raises
        ... def fail():
        ...     raise ValueError('failed')
        >>> fail()
        True
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ExceptionTrap(self.exceptions) as trap:
                func(*args, **kwargs)
            return _test(trap)

        return wrapper

    def passes(self, func):
        """
        Wrap func and replace the result with the truth
        value of the trap (True if no exception).

        First, give the decorator an alias to support Python 3.8
        Syntax.

        >>> passes = ExceptionTrap(ValueError).passes

        Now decorate a function that always fails.

        >>> @passes
        ... def fail():
        ...     raise ValueError('failed')

        >>> fail()
        False
        """
        return self.raises(func, _test=operator.not_)


class suppress(contextlib.suppress, contextlib.ContextDecorator):
    """
    A version of contextlib.suppress with decorator support.

    >>> @suppress(KeyError)
    ... def key_error():
    ...     {}['']
    >>> key_error()
    """


class on_interrupt(contextlib.ContextDecorator):
    """
    Replace a KeyboardInterrupt with SystemExit(1)

    >>> def do_interrupt():
    ...     raise KeyboardInterrupt()
    >>> on_interrupt('error')(do_interrupt)()
    Traceback (most recent call last):
    ...
    SystemExit: 1
    >>> on_interrupt('error', code=255)(do_interrupt)()
    Traceback (most recent call last):
    ...
    SystemExit: 255
    >>> on_interrupt('suppress')(do_interrupt)()
    >>> with __import__('pytest').raises(KeyboardInterrupt):
    ...     on_interrupt('ignore')(do_interrupt)()
    """

    def __init__(self, action='error', /, code=1):
        self.action = action
        self.code = code

    def __enter__(self):
        return self

    def __exit__(self, exctype, excinst, exctb):
        if exctype is not KeyboardInterrupt or self.action == 'ignore':
            return
        elif self.action == 'error':
            raise SystemExit(self.code) from excinst
        return self.action == 'suppress'

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\models.py ===
from __future__ import annotations

from encodings.aliases import aliases
from hashlib import sha256
from json import dumps
from re import sub
from typing import Any, Iterator, List, Tuple

from .constant import RE_POSSIBLE_ENCODING_INDICATION, TOO_BIG_SEQUENCE
from .utils import iana_name, is_multi_byte_encoding, unicode_range


class CharsetMatch:
    def __init__(
        self,
        payload: bytes,
        guessed_encoding: str,
        mean_mess_ratio: float,
        has_sig_or_bom: bool,
        languages: CoherenceMatches,
        decoded_payload: str | None = None,
        preemptive_declaration: str | None = None,
    ):
        self._payload: bytes = payload

        self._encoding: str = guessed_encoding
        self._mean_mess_ratio: float = mean_mess_ratio
        self._languages: CoherenceMatches = languages
        self._has_sig_or_bom: bool = has_sig_or_bom
        self._unicode_ranges: list[str] | None = None

        self._leaves: list[CharsetMatch] = []
        self._mean_coherence_ratio: float = 0.0

        self._output_payload: bytes | None = None
        self._output_encoding: str | None = None

        self._string: str | None = decoded_payload

        self._preemptive_declaration: str | None = preemptive_declaration

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CharsetMatch):
            if isinstance(other, str):
                return iana_name(other) == self.encoding
            return False
        return self.encoding == other.encoding and self.fingerprint == other.fingerprint

    def __lt__(self, other: object) -> bool:
        """
        Implemented to make sorted available upon CharsetMatches items.
        """
        if not isinstance(other, CharsetMatch):
            raise ValueError

        chaos_difference: float = abs(self.chaos - other.chaos)
        coherence_difference: float = abs(self.coherence - other.coherence)

        # Below 1% difference --> Use Coherence
        if chaos_difference < 0.01 and coherence_difference > 0.02:
            return self.coherence > other.coherence
        elif chaos_difference < 0.01 and coherence_difference <= 0.02:
            # When having a difficult decision, use the result that decoded as many multi-byte as possible.
            # preserve RAM usage!
            if len(self._payload) >= TOO_BIG_SEQUENCE:
                return self.chaos < other.chaos
            return self.multi_byte_usage > other.multi_byte_usage

        return self.chaos < other.chaos

    @property
    def multi_byte_usage(self) -> float:
        return 1.0 - (len(str(self)) / len(self.raw))

    def __str__(self) -> str:
        # Lazy Str Loading
        if self._string is None:
            self._string = str(self._payload, self._encoding, "strict")
        return self._string

    def __repr__(self) -> str:
        return f"<CharsetMatch '{self.encoding}' bytes({self.fingerprint})>"

    def add_submatch(self, other: CharsetMatch) -> None:
        if not isinstance(other, CharsetMatch) or other == self:
            raise ValueError(
                "Unable to add instance <{}> as a submatch of a CharsetMatch".format(
                    other.__class__
                )
            )

        other._string = None  # Unload RAM usage; dirty trick.
        self._leaves.append(other)

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def encoding_aliases(self) -> list[str]:
        """
        Encoding name are known by many name, using this could help when searching for IBM855 when it's listed as CP855.
        """
        also_known_as: list[str] = []
        for u, p in aliases.items():
            if self.encoding == u:
                also_known_as.append(p)
            elif self.encoding == p:
                also_known_as.append(u)
        return also_known_as

    @property
    def bom(self) -> bool:
        return self._has_sig_or_bom

    @property
    def byte_order_mark(self) -> bool:
        return self._has_sig_or_bom

    @property
    def languages(self) -> list[str]:
        """
        Return the complete list of possible languages found in decoded sequence.
        Usually not really useful. Returned list may be empty even if 'language' property return something != 'Unknown'.
        """
        return [e[0] for e in self._languages]

    @property
    def language(self) -> str:
        """
        Most probable language found in decoded sequence. If none were detected or inferred, the property will return
        "Unknown".
        """
        if not self._languages:
            # Trying to infer the language based on the given encoding
            # Its either English or we should not pronounce ourselves in certain cases.
            if "ascii" in self.could_be_from_charset:
                return "English"

            # doing it there to avoid circular import
            from charset_normalizer.cd import encoding_languages, mb_encoding_languages

            languages = (
                mb_encoding_languages(self.encoding)
                if is_multi_byte_encoding(self.encoding)
                else encoding_languages(self.encoding)
            )

            if len(languages) == 0 or "Latin Based" in languages:
                return "Unknown"

            return languages[0]

        return self._languages[0][0]

    @property
    def chaos(self) -> float:
        return self._mean_mess_ratio

    @property
    def coherence(self) -> float:
        if not self._languages:
            return 0.0
        return self._languages[0][1]

    @property
    def percent_chaos(self) -> float:
        return round(self.chaos * 100, ndigits=3)

    @property
    def percent_coherence(self) -> float:
        return round(self.coherence * 100, ndigits=3)

    @property
    def raw(self) -> bytes:
        """
        Original untouched bytes.
        """
        return self._payload

    @property
    def submatch(self) -> list[CharsetMatch]:
        return self._leaves

    @property
    def has_submatch(self) -> bool:
        return len(self._leaves) > 0

    @property
    def alphabets(self) -> list[str]:
        if self._unicode_ranges is not None:
            return self._unicode_ranges
        # list detected ranges
        detected_ranges: list[str | None] = [unicode_range(char) for char in str(self)]
        # filter and sort
        self._unicode_ranges = sorted(list({r for r in detected_ranges if r}))
        return self._unicode_ranges

    @property
    def could_be_from_charset(self) -> list[str]:
        """
        The complete list of encoding that output the exact SAME str result and therefore could be the originating
        encoding.
        This list does include the encoding available in property 'encoding'.
        """
        return [self._encoding] + [m.encoding for m in self._leaves]

    def output(self, encoding: str = "utf_8") -> bytes:
        """
        Method to get re-encoded bytes payload using given target encoding. Default to UTF-8.
        Any errors will be simply ignored by the encoder NOT replaced.
        """
        if self._output_encoding is None or self._output_encoding != encoding:
            self._output_encoding = encoding
            decoded_string = str(self)
            if (
                self._preemptive_declaration is not None
                and self._preemptive_declaration.lower()
                not in ["utf-8", "utf8", "utf_8"]
            ):
                patched_header = sub(
                    RE_POSSIBLE_ENCODING_INDICATION,
                    lambda m: m.string[m.span()[0] : m.span()[1]].replace(
                        m.groups()[0],
                        iana_name(self._output_encoding).replace("_", "-"),  # type: ignore[arg-type]
                    ),
                    decoded_string[:8192],
                    count=1,
                )

                decoded_string = patched_header + decoded_string[8192:]

            self._output_payload = decoded_string.encode(encoding, "replace")

        return self._output_payload  # type: ignore

    @property
    def fingerprint(self) -> str:
        """
        Retrieve the unique SHA256 computed using the transformed (re-encoded) payload. Not the original one.
        """
        return sha256(self.output()).hexdigest()


class CharsetMatches:
    """
    Container with every CharsetMatch items ordered by default from most probable to the less one.
    Act like a list(iterable) but does not implements all related methods.
    """

    def __init__(self, results: list[CharsetMatch] | None = None):
        self._results: list[CharsetMatch] = sorted(results) if results else []

    def __iter__(self) -> Iterator[CharsetMatch]:
        yield from self._results

    def __getitem__(self, item: int | str) -> CharsetMatch:
        """
        Retrieve a single item either by its position or encoding name (alias may be used here).
        Raise KeyError upon invalid index or encoding not present in results.
        """
        if isinstance(item, int):
            return self._results[item]
        if isinstance(item, str):
            item = iana_name(item, False)
            for result in self._results:
                if item in result.could_be_from_charset:
                    return result
        raise KeyError

    def __len__(self) -> int:
        return len(self._results)

    def __bool__(self) -> bool:
        return len(self._results) > 0

    def append(self, item: CharsetMatch) -> None:
        """
        Insert a single match. Will be inserted accordingly to preserve sort.
        Can be inserted as a submatch.
        """
        if not isinstance(item, CharsetMatch):
            raise ValueError(
                "Cannot append instance '{}' to CharsetMatches".format(
                    str(item.__class__)
                )
            )
        # We should disable the submatch factoring when the input file is too heavy (conserve RAM usage)
        if len(item.raw) < TOO_BIG_SEQUENCE:
            for match in self._results:
                if match.fingerprint == item.fingerprint and match.chaos == item.chaos:
                    match.add_submatch(item)
                    return
        self._results.append(item)
        self._results = sorted(self._results)

    def best(self) -> CharsetMatch | None:
        """
        Simply return the first match. Strict equivalent to matches[0].
        """
        if not self._results:
            return None
        return self._results[0]

    def first(self) -> CharsetMatch | None:
        """
        Redundant method, call the method best(). Kept for BC reasons.
        """
        return self.best()


CoherenceMatch = Tuple[str, float]
CoherenceMatches = List[CoherenceMatch]


class CliDetectionResult:
    def __init__(
        self,
        path: str,
        encoding: str | None,
        encoding_aliases: list[str],
        alternative_encodings: list[str],
        language: str,
        alphabets: list[str],
        has_sig_or_bom: bool,
        chaos: float,
        coherence: float,
        unicode_path: str | None,
        is_preferred: bool,
    ):
        self.path: str = path
        self.unicode_path: str | None = unicode_path
        self.encoding: str | None = encoding
        self.encoding_aliases: list[str] = encoding_aliases
        self.alternative_encodings: list[str] = alternative_encodings
        self.language: str = language
        self.alphabets: list[str] = alphabets
        self.has_sig_or_bom: bool = has_sig_or_bom
        self.chaos: float = chaos
        self.coherence: float = coherence
        self.is_preferred: bool = is_preferred

    @property
    def __dict__(self) -> dict[str, Any]:  # type: ignore
        return {
            "path": self.path,
            "encoding": self.encoding,
            "encoding_aliases": self.encoding_aliases,
            "alternative_encodings": self.alternative_encodings,
            "language": self.language,
            "alphabets": self.alphabets,
            "has_sig_or_bom": self.has_sig_or_bom,
            "chaos": self.chaos,
            "coherence": self.coherence,
            "unicode_path": self.unicode_path,
            "is_preferred": self.is_preferred,
        }

    def to_json(self) -> str:
        return dumps(self.__dict__, ensure_ascii=True, indent=4)

# === NexusCore/openenv\Lib\site-packages\PIL\ImageShow.py ===
#
# The Python Imaging Library.
# $Id$
#
# im.show() drivers
#
# History:
# 2008-04-06 fl   Created
#
# Copyright (c) Secret Labs AB 2008.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import abc
import os
import shutil
import subprocess
import sys
from shlex import quote
from typing import Any

from . import Image

_viewers = []


def register(viewer: type[Viewer] | Viewer, order: int = 1) -> None:
    """
    The :py:func:`register` function is used to register additional viewers::

        from PIL import ImageShow
        ImageShow.register(MyViewer())  # MyViewer will be used as a last resort
        ImageShow.register(MySecondViewer(), 0)  # MySecondViewer will be prioritised
        ImageShow.register(ImageShow.XVViewer(), 0)  # XVViewer will be prioritised

    :param viewer: The viewer to be registered.
    :param order:
        Zero or a negative integer to prepend this viewer to the list,
        a positive integer to append it.
    """
    if isinstance(viewer, type) and issubclass(viewer, Viewer):
        viewer = viewer()
    if order > 0:
        _viewers.append(viewer)
    else:
        _viewers.insert(0, viewer)


def show(image: Image.Image, title: str | None = None, **options: Any) -> bool:
    r"""
    Display a given image.

    :param image: An image object.
    :param title: Optional title. Not all viewers can display the title.
    :param \**options: Additional viewer options.
    :returns: ``True`` if a suitable viewer was found, ``False`` otherwise.
    """
    for viewer in _viewers:
        if viewer.show(image, title=title, **options):
            return True
    return False


class Viewer:
    """Base class for viewers."""

    # main api

    def show(self, image: Image.Image, **options: Any) -> int:
        """
        The main function for displaying an image.
        Converts the given image to the target format and displays it.
        """

        if not (
            image.mode in ("1", "RGBA")
            or (self.format == "PNG" and image.mode in ("I;16", "LA"))
        ):
            base = Image.getmodebase(image.mode)
            if image.mode != base:
                image = image.convert(base)

        return self.show_image(image, **options)

    # hook methods

    format: str | None = None
    """The format to convert the image into."""
    options: dict[str, Any] = {}
    """Additional options used to convert the image."""

    def get_format(self, image: Image.Image) -> str | None:
        """Return format name, or ``None`` to save as PGM/PPM."""
        return self.format

    def get_command(self, file: str, **options: Any) -> str:
        """
        Returns the command used to display the file.
        Not implemented in the base class.
        """
        msg = "unavailable in base viewer"
        raise NotImplementedError(msg)

    def save_image(self, image: Image.Image) -> str:
        """Save to temporary file and return filename."""
        return image._dump(format=self.get_format(image), **self.options)

    def show_image(self, image: Image.Image, **options: Any) -> int:
        """Display the given image."""
        return self.show_file(self.save_image(image), **options)

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        os.system(self.get_command(path, **options))  # nosec
        return 1


# --------------------------------------------------------------------


class WindowsViewer(Viewer):
    """The default viewer on Windows is the default system application for PNG files."""

    format = "PNG"
    options = {"compress_level": 1, "save_all": True}

    def get_command(self, file: str, **options: Any) -> str:
        return (
            f'start "Pillow" /WAIT "{file}" '
            "&& ping -n 4 127.0.0.1 >NUL "
            f'&& del /f "{file}"'
        )

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        subprocess.Popen(
            self.get_command(path, **options),
            shell=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW"),
        )  # nosec
        return 1


if sys.platform == "win32":
    register(WindowsViewer)


class MacViewer(Viewer):
    """The default viewer on macOS using ``Preview.app``."""

    format = "PNG"
    options = {"compress_level": 1, "save_all": True}

    def get_command(self, file: str, **options: Any) -> str:
        # on darwin open returns immediately resulting in the temp
        # file removal while app is opening
        command = "open -a Preview.app"
        command = f"({command} {quote(file)}; sleep 20; rm -f {quote(file)})&"
        return command

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        subprocess.call(["open", "-a", "Preview.app", path])
        executable = sys.executable or shutil.which("python3")
        if executable:
            subprocess.Popen(
                [
                    executable,
                    "-c",
                    "import os, sys, time; time.sleep(20); os.remove(sys.argv[1])",
                    path,
                ]
            )
        return 1


if sys.platform == "darwin":
    register(MacViewer)


class UnixViewer(abc.ABC, Viewer):
    format = "PNG"
    options = {"compress_level": 1, "save_all": True}

    @abc.abstractmethod
    def get_command_ex(self, file: str, **options: Any) -> tuple[str, str]:
        pass

    def get_command(self, file: str, **options: Any) -> str:
        command = self.get_command_ex(file, **options)[0]
        return f"{command} {quote(file)}"


class XDGViewer(UnixViewer):
    """
    The freedesktop.org ``xdg-open`` command.
    """

    def get_command_ex(self, file: str, **options: Any) -> tuple[str, str]:
        command = executable = "xdg-open"
        return command, executable

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        subprocess.Popen(["xdg-open", path])
        return 1


class DisplayViewer(UnixViewer):
    """
    The ImageMagick ``display`` command.
    This viewer supports the ``title`` parameter.
    """

    def get_command_ex(
        self, file: str, title: str | None = None, **options: Any
    ) -> tuple[str, str]:
        command = executable = "display"
        if title:
            command += f" -title {quote(title)}"
        return command, executable

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        args = ["display"]
        title = options.get("title")
        if title:
            args += ["-title", title]
        args.append(path)

        subprocess.Popen(args)
        return 1


class GmDisplayViewer(UnixViewer):
    """The GraphicsMagick ``gm display`` command."""

    def get_command_ex(self, file: str, **options: Any) -> tuple[str, str]:
        executable = "gm"
        command = "gm display"
        return command, executable

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        subprocess.Popen(["gm", "display", path])
        return 1


class EogViewer(UnixViewer):
    """The GNOME Image Viewer ``eog`` command."""

    def get_command_ex(self, file: str, **options: Any) -> tuple[str, str]:
        executable = "eog"
        command = "eog -n"
        return command, executable

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        subprocess.Popen(["eog", "-n", path])
        return 1


class XVViewer(UnixViewer):
    """
    The X Viewer ``xv`` command.
    This viewer supports the ``title`` parameter.
    """

    def get_command_ex(
        self, file: str, title: str | None = None, **options: Any
    ) -> tuple[str, str]:
        # note: xv is pretty outdated.  most modern systems have
        # imagemagick's display command instead.
        command = executable = "xv"
        if title:
            command += f" -name {quote(title)}"
        return command, executable

    def show_file(self, path: str, **options: Any) -> int:
        """
        Display given file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError
        args = ["xv"]
        title = options.get("title")
        if title:
            args += ["-name", title]
        args.append(path)

        subprocess.Popen(args)
        return 1


if sys.platform not in ("win32", "darwin"):  # unixoids
    if shutil.which("xdg-open"):
        register(XDGViewer)
    if shutil.which("display"):
        register(DisplayViewer)
    if shutil.which("gm"):
        register(GmDisplayViewer)
    if shutil.which("eog"):
        register(EogViewer)
    if shutil.which("xv"):
        register(XVViewer)


class IPythonViewer(Viewer):
    """The viewer for IPython frontends."""

    def show_image(self, image: Image.Image, **options: Any) -> int:
        ipython_display(image)
        return 1


try:
    from IPython.display import display as ipython_display
except ImportError:
    pass
else:
    register(IPythonViewer)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Syntax: python3 ImageShow.py imagefile [title]")
        sys.exit()

    with Image.open(sys.argv[1]) as im:
        print(show(im, *sys.argv[2:]))