
# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta3.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .grpc import DiscussServiceGrpcTransport


class DiscussServiceGrpcAsyncIOTransport(DiscussServiceTransport):
    """gRPC AsyncIO backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
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
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
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
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
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

        if isinstance(channel, aio.Channel):
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

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Awaitable[discuss_service.GenerateMessageResponse],
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    Awaitable[~.GenerateMessageResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Awaitable[discuss_service.CountMessageTokensResponse],
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    Awaitable[~.CountMessageTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_message: gapic_v1.method_async.wrap_method(
                self.generate_message,
                default_timeout=None,
                client_info=client_info,
            ),
            self.count_message_tokens: gapic_v1.method_async.wrap_method(
                self.count_message_tokens,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("DiscussServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\google\api_core\future\polling.py ===
# Copyright 2017, Google LLC
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

"""Abstract and helper bases for Future implementations."""

import abc
import concurrent.futures

from google.api_core import exceptions
from google.api_core import retry as retries
from google.api_core.future import _helpers
from google.api_core.future import base


class _OperationNotComplete(Exception):
    """Private exception used for polling via retry."""

    pass


# DEPRECATED as it conflates RPC retry and polling concepts into one.
# Use POLLING_PREDICATE instead to configure polling.
RETRY_PREDICATE = retries.if_exception_type(
    _OperationNotComplete,
    exceptions.TooManyRequests,
    exceptions.InternalServerError,
    exceptions.BadGateway,
    exceptions.ServiceUnavailable,
)

# DEPRECATED: use DEFAULT_POLLING to configure LRO polling logic. Construct
# Retry object using its default values as a baseline for any custom retry logic
# (not to be confused with polling logic).
DEFAULT_RETRY = retries.Retry(predicate=RETRY_PREDICATE)

# POLLING_PREDICATE is supposed to poll only on _OperationNotComplete.
# Any RPC-specific errors (like ServiceUnavailable) will be handled
# by retry logic (not to be confused with polling logic) which is triggered for
# every polling RPC independently of polling logic but within its context.
POLLING_PREDICATE = retries.if_exception_type(
    _OperationNotComplete,
)

# Default polling configuration
DEFAULT_POLLING = retries.Retry(
    predicate=POLLING_PREDICATE,
    initial=1.0,  # seconds
    maximum=20.0,  # seconds
    multiplier=1.5,
    timeout=900,  # seconds
)


class PollingFuture(base.Future):
    """A Future that needs to poll some service to check its status.

    The :meth:`done` method should be implemented by subclasses. The polling
    behavior will repeatedly call ``done`` until it returns True.

    The actual polling logic is encapsulated in :meth:`result` method. See
    documentation for that method for details on how polling works.

    .. note::

        Privacy here is intended to prevent the final class from
        overexposing, not to prevent subclasses from accessing methods.

    Args:
        polling (google.api_core.retry.Retry): The configuration used for polling.
            This parameter controls how often :meth:`done` is polled. If the
            ``timeout`` argument is specified in :meth:`result` method it will
            override the ``polling.timeout`` property.
        retry (google.api_core.retry.Retry): DEPRECATED use ``polling`` instead.
            If set, it will override ``polling`` parameter for backward
            compatibility.
    """

    _DEFAULT_VALUE = object()

    def __init__(self, polling=DEFAULT_POLLING, **kwargs):
        super(PollingFuture, self).__init__()
        self._polling = kwargs.get("retry", polling)
        self._result = None
        self._exception = None
        self._result_set = False
        """bool: Set to True when the result has been set via set_result or
        set_exception."""
        self._polling_thread = None
        self._done_callbacks = []

    @abc.abstractmethod
    def done(self, retry=None):
        """Checks to see if the operation is complete.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the
                polling RPC (to not be confused with polling configuration. See
                the documentation for :meth:`result` for details).

        Returns:
            bool: True if the operation is complete, False otherwise.
        """
        # pylint: disable=redundant-returns-doc, missing-raises-doc
        raise NotImplementedError()

    def _done_or_raise(self, retry=None):
        """Check if the future is done and raise if it's not."""
        if not self.done(retry=retry):
            raise _OperationNotComplete()

    def running(self):
        """True if the operation is currently running."""
        return not self.done()

    def _blocking_poll(self, timeout=_DEFAULT_VALUE, retry=None, polling=None):
        """Poll and wait for the Future to be resolved."""

        if self._result_set:
            return

        polling = polling or self._polling
        if timeout is not PollingFuture._DEFAULT_VALUE:
            polling = polling.with_timeout(timeout)

        try:
            polling(self._done_or_raise)(retry=retry)
        except exceptions.RetryError:
            raise concurrent.futures.TimeoutError(
                f"Operation did not complete within the designated timeout of "
                f"{polling.timeout} seconds."
            )

    def result(self, timeout=_DEFAULT_VALUE, retry=None, polling=None):
        """Get the result of the operation.

        This method will poll for operation status periodically, blocking if
        necessary. If you just want to make sure that this method does not block
        for more than X seconds and you do not care about the nitty-gritty of
        how this method operates, just call it with ``result(timeout=X)``. The
        other parameters are for advanced use only.

        Every call to this method is controlled by the following three
        parameters, each of which has a specific, distinct role, even though all three
        may look very similar: ``timeout``, ``retry`` and ``polling``. In most
        cases users do not need to specify any custom values for any of these
        parameters and may simply rely on default ones instead.

        If you choose to specify custom parameters, please make sure you've
        read the documentation below carefully.

        First, please check :class:`google.api_core.retry.Retry`
        class documentation for the proper definition of timeout and deadline
        terms and for the definition the three different types of timeouts.
        This class operates in terms of Retry Timeout and Polling Timeout. It
        does not let customizing RPC timeout and the user is expected to rely on
        default behavior for it.

        The roles of each argument of this method are as follows:

        ``timeout`` (int): (Optional) The Polling Timeout as defined in
        :class:`google.api_core.retry.Retry`. If the operation does not complete
        within this timeout an exception will be thrown. This parameter affects
        neither Retry Timeout nor RPC Timeout.

        ``retry`` (google.api_core.retry.Retry): (Optional) How to retry the
        polling RPC. The ``retry.timeout`` property of this parameter is the
        Retry Timeout as defined in :class:`google.api_core.retry.Retry`.
        This parameter defines ONLY how the polling RPC call is retried
        (i.e. what to do if the RPC we used for polling returned an error). It
        does NOT define how the polling is done (i.e. how frequently and for
        how long to call the polling RPC); use the ``polling`` parameter for that.
        If a polling RPC throws and error and retrying it fails, the whole
        future fails with the corresponding exception. If you want to tune which
        server response error codes are not fatal for operation polling, use this
        parameter to control that (``retry.predicate`` in particular).

        ``polling`` (google.api_core.retry.Retry): (Optional) How often and
        for how long to call the polling RPC periodically (i.e. what to do if
        a polling rpc returned successfully but its returned result indicates
        that the long running operation is not completed yet, so we need to
        check it again at some point in future). This parameter does NOT define
        how to retry each individual polling RPC in case of an error; use the
        ``retry`` parameter for that. The ``polling.timeout`` of this parameter
        is Polling Timeout as defined in as defined in
        :class:`google.api_core.retry.Retry`.

        For each of the arguments, there are also default values in place, which
        will be used if a user does not specify their own. The default values
        for the three parameters are not to be confused with the default values
        for the corresponding arguments in this method (those serve as "not set"
        markers for the resolution logic).

        If ``timeout`` is provided (i.e.``timeout is not _DEFAULT VALUE``; note
        the ``None`` value means "infinite timeout"), it will be used to control
        the actual Polling Timeout. Otherwise, the ``polling.timeout`` value
        will be used instead (see below for how the ``polling`` config itself
        gets resolved). In other words, this parameter  effectively overrides
        the ``polling.timeout`` value if specified. This is so to preserve
        backward compatibility.

        If ``retry`` is provided (i.e. ``retry is not None``) it will be used to
        control retry behavior for the polling RPC and the ``retry.timeout``
        will determine the Retry Timeout. If not provided, the
        polling RPC will be called with whichever default retry config was
        specified for the polling RPC at the moment of the construction of the
        polling RPC's client. For example, if the polling RPC is
        ``operations_client.get_operation()``, the ``retry`` parameter will be
        controlling its retry behavior (not polling  behavior) and, if not
        specified, that specific method (``operations_client.get_operation()``)
        will be retried according to the default retry config provided during
        creation of ``operations_client`` client instead. This argument exists
        mainly for backward compatibility; users are very unlikely to ever need
        to set this parameter explicitly.

        If ``polling`` is provided (i.e. ``polling is not None``), it will be used
        to control the overall polling behavior and ``polling.timeout`` will
        control Polling Timeout unless it is overridden by ``timeout`` parameter
        as described above. If not provided, the``polling`` parameter specified
        during construction of this future (the ``polling`` argument in the
        constructor) will be used instead. Note: since the ``timeout`` argument may
        override ``polling.timeout`` value, this parameter should be viewed as
        coupled with the ``timeout`` parameter as described above.

        Args:
            timeout (int): (Optional) How long (in seconds) to wait for the
                operation to complete. If None, wait indefinitely.
            retry (google.api_core.retry.Retry): (Optional) How to retry the
                polling RPC. This defines ONLY how the polling RPC call is
                retried (i.e. what to do if the RPC we used for polling returned
                an error). It does  NOT define how the polling is done (i.e. how
                frequently and for how long to call the polling RPC).
            polling (google.api_core.retry.Retry): (Optional) How often and
                for how long to call polling RPC periodically. This parameter
                does NOT define how to retry each individual polling RPC call
                (use the ``retry`` parameter for that).

        Returns:
            google.protobuf.Message: The Operation's result.

        Raises:
            google.api_core.GoogleAPICallError: If the operation errors or if
                the timeout is reached before the operation completes.
        """

        self._blocking_poll(timeout=timeout, retry=retry, polling=polling)

        if self._exception is not None:
            # pylint: disable=raising-bad-type
            # Pylint doesn't recognize that this is valid in this case.
            raise self._exception

        return self._result

    def exception(self, timeout=_DEFAULT_VALUE):
        """Get the exception from the operation, blocking if necessary.

        See the documentation for the :meth:`result` method for details on how
        this method operates, as both ``result`` and this method rely on the
        exact same polling logic. The only difference is that this method does
        not accept ``retry`` and ``polling`` arguments but relies on the default ones
        instead.

        Args:
            timeout (int): How long to wait for the operation to complete.
            If None, wait indefinitely.

        Returns:
            Optional[google.api_core.GoogleAPICallError]: The operation's
                error.
        """
        self._blocking_poll(timeout=timeout)
        return self._exception

    def add_done_callback(self, fn):
        """Add a callback to be executed when the operation is complete.

        If the operation is not already complete, this will start a helper
        thread to poll for the status of the operation in the background.

        Args:
            fn (Callable[Future]): The callback to execute when the operation
                is complete.
        """
        if self._result_set:
            _helpers.safe_invoke_callback(fn, self)
            return

        self._done_callbacks.append(fn)

        if self._polling_thread is None:
            # The polling thread will exit on its own as soon as the operation
            # is done.
            self._polling_thread = _helpers.start_daemon_thread(
                target=self._blocking_poll
            )

    def _invoke_callbacks(self, *args, **kwargs):
        """Invoke all done callbacks."""
        for callback in self._done_callbacks:
            _helpers.safe_invoke_callback(callback, *args, **kwargs)

    def set_result(self, result):
        """Set the Future's result."""
        self._result = result
        self._result_set = True
        self._invoke_callbacks(self)

    def set_exception(self, exception):
        """Set the Future's exception."""
        self._exception = exception
        self._result_set = True
        self._invoke_callbacks(self)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\replicate\chat\transformation.py ===
from typing import TYPE_CHECKING, Any, List, Optional, Union

import httpx

import litellm
from litellm.constants import REPLICATE_MODEL_NAME_WITH_ID_LENGTH
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse, Usage
from litellm.utils import token_counter

from ..common_utils import ReplicateError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class ReplicateConfig(BaseConfig):
    """
    Reference: https://replicate.com/meta/llama-2-70b-chat/api
    - `prompt` (string): The prompt to send to the model.

    - `system_prompt` (string): The system prompt to send to the model. This is prepended to the prompt and helps guide system behavior. Default value: `You are a helpful assistant`.

    - `max_new_tokens` (integer): Maximum number of tokens to generate. Typically, a word is made up of 2-3 tokens. Default value: `128`.

    - `min_new_tokens` (integer): Minimum number of tokens to generate. To disable, set to `-1`. A word is usually 2-3 tokens. Default value: `-1`.

    - `temperature` (number): Adjusts the randomness of outputs. Values greater than 1 increase randomness, 0 is deterministic, and 0.75 is a reasonable starting value. Default value: `0.75`.

    - `top_p` (number): During text decoding, it samples from the top `p` percentage of most likely tokens. Reduce this to ignore less probable tokens. Default value: `0.9`.

    - `top_k` (integer): During text decoding, samples from the top `k` most likely tokens. Reduce this to ignore less probable tokens. Default value: `50`.

    - `stop_sequences` (string): A comma-separated list of sequences to stop generation at. For example, inputting '<end>,<stop>' will cease generation at the first occurrence of either 'end' or '<stop>'.

    - `seed` (integer): This is the seed for the random generator. Leave it blank to randomize the seed.

    - `debug` (boolean): If set to `True`, it provides debugging output in logs.

    Please note that Replicate's mapping of these parameters can be inconsistent across different models, indicating that not all of these parameters may be available for use with all models.
    """

    system_prompt: Optional[str] = None
    max_new_tokens: Optional[int] = None
    min_new_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[str] = None
    seed: Optional[int] = None
    debug: Optional[bool] = None

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        min_new_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[str] = None,
        seed: Optional[int] = None,
        debug: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str) -> list:
        return [
            "stream",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "seed",
            "tools",
            "tool_choice",
            "functions",
            "function_call",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "stream":
                optional_params["stream"] = value
            if param == "max_tokens":
                if "vicuna" in model or "flan" in model:
                    optional_params["max_length"] = value
                elif "meta/codellama-13b" in model:
                    optional_params["max_tokens"] = value
                else:
                    optional_params["max_new_tokens"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "stop":
                optional_params["stop_sequences"] = value

        return optional_params

    # Function to extract version ID from model string
    def model_to_version_id(self, model: str) -> str:
        if ":" in model:
            split_model = model.split(":")
            return split_model[1]
        return model

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return ReplicateError(
            status_code=status_code, message=error_message, headers=headers
        )

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        version_id = self.model_to_version_id(model)
        base_url = api_base
        if "deployments" in version_id:
            version_id = version_id.replace("deployments/", "")
            base_url = f"https://api.replicate.com/v1/deployments/{version_id}"
        else:  # assume it's a model
            base_url = f"https://api.replicate.com/v1/models/{version_id}"

        base_url = f"{base_url}/predictions"
        return base_url

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        ## Load Config
        config = litellm.ReplicateConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > replicate_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        system_prompt = None
        if optional_params is not None and "supports_system_prompt" in optional_params:
            supports_sys_prompt = optional_params.pop("supports_system_prompt")
        else:
            supports_sys_prompt = False

        if supports_sys_prompt:
            for i in range(len(messages)):
                if messages[i]["role"] == "system":
                    first_sys_message = messages.pop(i)
                    system_prompt = convert_content_list_to_str(first_sys_message)
                    break

        if model in litellm.custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = litellm.custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details.get("roles", {}),
                initial_prompt_value=model_prompt_details.get(
                    "initial_prompt_value", ""
                ),
                final_prompt_value=model_prompt_details.get("final_prompt_value", ""),
                bos_token=model_prompt_details.get("bos_token", ""),
                eos_token=model_prompt_details.get("eos_token", ""),
                messages=messages,
            )
        else:
            prompt = prompt_factory(model=model, messages=messages)

        if prompt is None or not isinstance(prompt, str):
            raise ReplicateError(
                status_code=400,
                message="LiteLLM Error - prompt is not a string - {}".format(prompt),
                headers={},
            )

        # If system prompt is supported, and a system prompt is provided, use it
        if system_prompt is not None:
            input_data = {
                "prompt": prompt,
                "system_prompt": system_prompt,
                **optional_params,
            }
        # Otherwise, use the prompt as is
        else:
            input_data = {"prompt": prompt, **optional_params}

        version_id = self.model_to_version_id(model)
        request_data: dict = {"input": input_data}
        if ":" in version_id and len(version_id) > REPLICATE_MODEL_NAME_WITH_ID_LENGTH:
            model_parts = version_id.split(":")
            if (
                len(model_parts) > 1
                and len(model_parts[1]) == REPLICATE_MODEL_NAME_WITH_ID_LENGTH
            ):  ## checks if model name has a 64 digit code - e.g. "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3"
                request_data["version"] = model_parts[1]

        return request_data

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )
        raw_response_json = raw_response.json()
        if raw_response_json.get("status") != "succeeded":
            raise ReplicateError(
                status_code=422,
                message="LiteLLM Error - prediction not succeeded - {}".format(
                    raw_response_json
                ),
                headers=raw_response.headers,
            )
        outputs = raw_response_json.get("output", [])
        response_str = "".join(outputs)
        if len(response_str) == 0:  # edge case, where result from replicate is empty
            response_str = " "

        ## Building RESPONSE OBJECT
        if len(response_str) >= 1:
            model_response.choices[0].message.content = response_str  # type: ignore

        # Calculate usage
        prompt_tokens = token_counter(model=model, messages=messages)
        completion_tokens = token_counter(
            model=model,
            text=response_str,
            count_response_tokens=True,
        )
        model_response.model = "replicate/" + model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)

        return model_response

    def get_prediction_url(self, response: httpx.Response) -> str:
        """
        response json: {
        ...,
        "urls":{"cancel":"https://api.replicate.com/v1/predictions/gqsmqmp1pdrj00cknr08dgmvb4/cancel","get":"https://api.replicate.com/v1/predictions/gqsmqmp1pdrj00cknr08dgmvb4","stream":"https://stream-b.svc.rno2.c.replicate.net/v1/streams/eot4gbydowuin4snhncydwxt57dfwgsc3w3snycx5nid7oef7jga"}
        }
        """
        response_json = response.json()
        prediction_url = response_json.get("urls", {}).get("get")
        if prediction_url is None:
            raise ReplicateError(
                status_code=400,
                message="LiteLLM Error - prediction url is None - {}".format(
                    response_json
                ),
                headers=response.headers,
            )
        return prediction_url

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }
        return headers

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\exceptions.py ===
from __future__ import absolute_import

from .packages.six.moves.http_client import IncompleteRead as httplib_IncompleteRead

# Base Exceptions


class HTTPError(Exception):
    """Base exception used by this module."""

    pass


class HTTPWarning(Warning):
    """Base warning used by this module."""

    pass


class PoolError(HTTPError):
    """Base exception for errors caused within a pool."""

    def __init__(self, pool, message):
        self.pool = pool
        HTTPError.__init__(self, "%s: %s" % (pool, message))

    def __reduce__(self):
        # For pickling purposes.
        return self.__class__, (None, None)


class RequestError(PoolError):
    """Base exception for PoolErrors that have associated URLs."""

    def __init__(self, pool, url, message):
        self.url = url
        PoolError.__init__(self, pool, message)

    def __reduce__(self):
        # For pickling purposes.
        return self.__class__, (None, self.url, None)


class SSLError(HTTPError):
    """Raised when SSL certificate fails in an HTTPS connection."""

    pass


class ProxyError(HTTPError):
    """Raised when the connection to a proxy fails."""

    def __init__(self, message, error, *args):
        super(ProxyError, self).__init__(message, error, *args)
        self.original_error = error


class DecodeError(HTTPError):
    """Raised when automatic decoding based on Content-Type fails."""

    pass


class ProtocolError(HTTPError):
    """Raised when something unexpected happens mid-request/response."""

    pass


#: Renamed to ProtocolError but aliased for backwards compatibility.
ConnectionError = ProtocolError


# Leaf Exceptions


class MaxRetryError(RequestError):
    """Raised when the maximum number of retries is exceeded.

    :param pool: The connection pool
    :type pool: :class:`~urllib3.connectionpool.HTTPConnectionPool`
    :param string url: The requested Url
    :param exceptions.Exception reason: The underlying error

    """

    def __init__(self, pool, url, reason=None):
        self.reason = reason

        message = "Max retries exceeded with url: %s (Caused by %r)" % (url, reason)

        RequestError.__init__(self, pool, url, message)


class HostChangedError(RequestError):
    """Raised when an existing pool gets a request for a foreign host."""

    def __init__(self, pool, url, retries=3):
        message = "Tried to open a foreign host with url: %s" % url
        RequestError.__init__(self, pool, url, message)
        self.retries = retries


class TimeoutStateError(HTTPError):
    """Raised when passing an invalid state to a timeout"""

    pass


class TimeoutError(HTTPError):
    """Raised when a socket timeout error occurs.

    Catching this error will catch both :exc:`ReadTimeoutErrors
    <ReadTimeoutError>` and :exc:`ConnectTimeoutErrors <ConnectTimeoutError>`.
    """

    pass


class ReadTimeoutError(TimeoutError, RequestError):
    """Raised when a socket timeout occurs while receiving data from a server"""

    pass


# This timeout error does not have a URL attached and needs to inherit from the
# base HTTPError
class ConnectTimeoutError(TimeoutError):
    """Raised when a socket timeout occurs while connecting to a server"""

    pass


class NewConnectionError(ConnectTimeoutError, PoolError):
    """Raised when we fail to establish a new connection. Usually ECONNREFUSED."""

    pass


class EmptyPoolError(PoolError):
    """Raised when a pool runs out of connections and no more are allowed."""

    pass


class ClosedPoolError(PoolError):
    """Raised when a request enters a pool after the pool has been closed."""

    pass


class LocationValueError(ValueError, HTTPError):
    """Raised when there is something wrong with a given URL input."""

    pass


class LocationParseError(LocationValueError):
    """Raised when get_host or similar fails to parse the URL input."""

    def __init__(self, location):
        message = "Failed to parse: %s" % location
        HTTPError.__init__(self, message)

        self.location = location


class URLSchemeUnknown(LocationValueError):
    """Raised when a URL input has an unsupported scheme."""

    def __init__(self, scheme):
        message = "Not supported URL scheme %s" % scheme
        super(URLSchemeUnknown, self).__init__(message)

        self.scheme = scheme


class ResponseError(HTTPError):
    """Used as a container for an error reason supplied in a MaxRetryError."""

    GENERIC_ERROR = "too many error responses"
    SPECIFIC_ERROR = "too many {status_code} error responses"


class SecurityWarning(HTTPWarning):
    """Warned when performing security reducing actions"""

    pass


class SubjectAltNameWarning(SecurityWarning):
    """Warned when connecting to a host with a certificate missing a SAN."""

    pass


class InsecureRequestWarning(SecurityWarning):
    """Warned when making an unverified HTTPS request."""

    pass


class SystemTimeWarning(SecurityWarning):
    """Warned when system time is suspected to be wrong"""

    pass


class InsecurePlatformWarning(SecurityWarning):
    """Warned when certain TLS/SSL configuration is not available on a platform."""

    pass


class SNIMissingWarning(HTTPWarning):
    """Warned when making a HTTPS request without SNI available."""

    pass


class DependencyWarning(HTTPWarning):
    """
    Warned when an attempt is made to import a module with missing optional
    dependencies.
    """

    pass


class ResponseNotChunked(ProtocolError, ValueError):
    """Response needs to be chunked in order to read it as chunks."""

    pass


class BodyNotHttplibCompatible(HTTPError):
    """
    Body should be :class:`http.client.HTTPResponse` like
    (have an fp attribute which returns raw chunks) for read_chunked().
    """

    pass


class IncompleteRead(HTTPError, httplib_IncompleteRead):
    """
    Response length doesn't match expected Content-Length

    Subclass of :class:`http.client.IncompleteRead` to allow int value
    for ``partial`` to avoid creating large objects on streamed reads.
    """

    def __init__(self, partial, expected):
        super(IncompleteRead, self).__init__(partial, expected)

    def __repr__(self):
        return "IncompleteRead(%i bytes read, %i more expected)" % (
            self.partial,
            self.expected,
        )


class InvalidChunkLength(HTTPError, httplib_IncompleteRead):
    """Invalid chunk length in a chunked response."""

    def __init__(self, response, length):
        super(InvalidChunkLength, self).__init__(
            response.tell(), response.length_remaining
        )
        self.response = response
        self.length = length

    def __repr__(self):
        return "InvalidChunkLength(got length %r, %i bytes read)" % (
            self.length,
            self.partial,
        )


class InvalidHeader(HTTPError):
    """The header provided was somehow invalid."""

    pass


class ProxySchemeUnknown(AssertionError, URLSchemeUnknown):
    """ProxyManager does not support the supplied scheme"""

    # TODO(t-8ch): Stop inheriting from AssertionError in v2.0.

    def __init__(self, scheme):
        # 'localhost' is here because our URL parser parses
        # localhost:8080 -> scheme=localhost, remove if we fix this.
        if scheme == "localhost":
            scheme = None
        if scheme is None:
            message = "Proxy URL had no scheme, should start with http:// or https://"
        else:
            message = (
                "Proxy URL had unsupported scheme %s, should use http:// or https://"
                % scheme
            )
        super(ProxySchemeUnknown, self).__init__(message)


class ProxySchemeUnsupported(ValueError):
    """Fetching HTTPS resources through HTTPS proxies is unsupported"""

    pass


class HeaderParsingError(HTTPError):
    """Raised by assert_header_parsing, but we convert it to a log.warning statement."""

    def __init__(self, defects, unparsed_data):
        message = "%s, unparsed data: %r" % (defects or "Unknown", unparsed_data)
        super(HeaderParsingError, self).__init__(message)


class UnrewindableBodyError(HTTPError):
    """urllib3 encountered an error when trying to rewind a body"""

    pass

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_js_handle.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import collections.abc
import datetime
import math
import struct
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import ParseResult, urlparse, urlunparse

from playwright._impl._connection import Channel, ChannelOwner, from_channel
from playwright._impl._errors import Error, is_target_closed_error
from playwright._impl._map import Map

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._element_handle import ElementHandle


Serializable = Any


class VisitorInfo:
    visited: Map[Any, int]
    last_id: int

    def __init__(self) -> None:
        self.visited = Map()
        self.last_id = 0

    def visit(self, obj: Any) -> int:
        assert obj not in self.visited
        self.last_id += 1
        self.visited[obj] = self.last_id
        return self.last_id


class JSHandle(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._preview = self._initializer["preview"]
        self._channel.on(
            "previewUpdated", lambda params: self._on_preview_updated(params["preview"])
        )

    def __repr__(self) -> str:
        return f"<JSHandle preview={self._preview}>"

    def __str__(self) -> str:
        return self._preview

    def _on_preview_updated(self, preview: str) -> None:
        self._preview = preview

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> "JSHandle":
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def get_property(self, propertyName: str) -> "JSHandle":
        return from_channel(
            await self._channel.send("getProperty", dict(name=propertyName))
        )

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        return {
            prop["name"]: from_channel(prop["value"])
            for prop in await self._channel.send("getPropertyList")
        }

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        try:
            await self._channel.send("dispose")
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    async def json_value(self) -> Any:
        return parse_result(await self._channel.send("jsonValue"))


def serialize_value(
    value: Any, handles: List[Channel], visitor_info: Optional[VisitorInfo] = None
) -> Any:
    if visitor_info is None:
        visitor_info = VisitorInfo()
    if isinstance(value, JSHandle):
        h = len(handles)
        handles.append(value._channel)
        return dict(h=h)
    if value is None:
        return dict(v="null")
    if isinstance(value, float):
        if value == float("inf"):
            return dict(v="Infinity")
        if value == float("-inf"):
            return dict(v="-Infinity")
        if value == float("-0"):
            return dict(v="-0")
        if math.isnan(value):
            return dict(v="NaN")
    if isinstance(value, datetime.datetime):
        # Node.js Date objects are always in UTC.
        return {
            "d": datetime.datetime.strftime(
                value.astimezone(datetime.timezone.utc), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        }
    if isinstance(value, Exception):
        return {
            "e": {
                "m": str(value),
                "n": (
                    (value.name or "")
                    if isinstance(value, Error)
                    else value.__class__.__name__
                ),
                "s": (
                    (value.stack or "")
                    if isinstance(value, Error)
                    else "".join(
                        traceback.format_exception(type(value), value=value, tb=None)
                    )
                ),
            }
        }
    if isinstance(value, bool):
        return {"b": value}
    if isinstance(value, (int, float)):
        return {"n": value}
    if isinstance(value, str):
        return {"s": value}
    if isinstance(value, ParseResult):
        return {"u": urlunparse(value)}

    if value in visitor_info.visited:
        return dict(ref=visitor_info.visited[value])

    if isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        id = visitor_info.visit(value)
        a = []
        for e in value:
            a.append(serialize_value(e, handles, visitor_info))
        return dict(a=a, id=id)

    if isinstance(value, dict):
        id = visitor_info.visit(value)
        o = []
        for name in value:
            o.append(
                {"k": name, "v": serialize_value(value[name], handles, visitor_info)}
            )
        return dict(o=o, id=id)
    return dict(v="undefined")


def serialize_argument(arg: Serializable = None) -> Any:
    handles: List[Channel] = []
    value = serialize_value(arg, handles)
    return dict(value=value, handles=handles)


def parse_value(value: Any, refs: Optional[Dict[int, Any]] = None) -> Any:
    if refs is None:
        refs = {}
    if value is None:
        return None
    if isinstance(value, dict):
        if "ref" in value:
            return refs[value["ref"]]

        if "v" in value:
            v = value["v"]
            if v == "Infinity":
                return float("inf")
            if v == "-Infinity":
                return float("-inf")
            if v == "-0":
                return float("-0")
            if v == "NaN":
                return float("nan")
            if v == "undefined":
                return None
            if v == "null":
                return None
            return v

        if "u" in value:
            return urlparse(value["u"])

        if "bi" in value:
            return int(value["bi"])

        if "e" in value:
            error = Error(value["e"]["m"])
            error._name = value["e"]["n"]
            error._stack = value["e"]["s"]
            return error

        if "a" in value:
            a: List = []
            refs[value["id"]] = a
            for e in value["a"]:
                a.append(parse_value(e, refs))
            return a

        if "d" in value:
            # Node.js Date objects are always in UTC.
            return datetime.datetime.strptime(
                value["d"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=datetime.timezone.utc)

        if "o" in value:
            o: Dict = {}
            refs[value["id"]] = o
            for e in value["o"]:
                o[e["k"]] = parse_value(e["v"], refs)
            return o

        if "n" in value:
            return value["n"]

        if "s" in value:
            return value["s"]

        if "b" in value:
            return value["b"]

        if "ta" in value:
            encoded_bytes = value["ta"]["b"]
            decoded_bytes = base64.b64decode(encoded_bytes)
            array_type = value["ta"]["k"]
            if array_type == "i8":
                word_size = 1
                fmt = "b"
            elif array_type == "ui8" or array_type == "ui8c":
                word_size = 1
                fmt = "B"
            elif array_type == "i16":
                word_size = 2
                fmt = "h"
            elif array_type == "ui16":
                word_size = 2
                fmt = "H"
            elif array_type == "i32":
                word_size = 4
                fmt = "i"
            elif array_type == "ui32":
                word_size = 4
                fmt = "I"
            elif array_type == "f32":
                word_size = 4
                fmt = "f"
            elif array_type == "f64":
                word_size = 8
                fmt = "d"
            elif array_type == "bi64":
                word_size = 8
                fmt = "q"
            elif array_type == "bui64":
                word_size = 8
                fmt = "Q"
            else:
                raise ValueError(f"Unsupported array type: {array_type}")

            byte_len = len(decoded_bytes)
            if byte_len % word_size != 0:
                raise ValueError(
                    f"Decoded bytes length {byte_len} is not a multiple of word size {word_size}"
                )

            if byte_len == 0:
                return []
            array_len = byte_len // word_size
            # "<" denotes little-endian
            format_string = f"<{array_len}{fmt}"
            return list(struct.unpack(format_string, decoded_bytes))
    return value


def parse_result(result: Any) -> Any:
    return parse_value(result)


def add_source_url_to_script(source: str, path: Union[str, Path]) -> str:
    return source + "\n//# sourceURL=" + str(path).replace("\n", "")

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\screen.py ===
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Callable

from prompt_toolkit.cache import FastDictCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.utils import get_cwidth

if TYPE_CHECKING:
    from .containers import Window


__all__ = [
    "Screen",
    "Char",
]


class Char:
    """
    Represent a single character in a :class:`.Screen`.

    This should be considered immutable.

    :param char: A single character (can be a double-width character).
    :param style: A style string. (Can contain classnames.)
    """

    __slots__ = ("char", "style", "width")

    # If we end up having one of these special control sequences in the input string,
    # we should display them as follows:
    # Usually this happens after a "quoted insert".
    display_mappings: dict[str, str] = {
        "\x00": "^@",  # Control space
        "\x01": "^A",
        "\x02": "^B",
        "\x03": "^C",
        "\x04": "^D",
        "\x05": "^E",
        "\x06": "^F",
        "\x07": "^G",
        "\x08": "^H",
        "\x09": "^I",
        "\x0a": "^J",
        "\x0b": "^K",
        "\x0c": "^L",
        "\x0d": "^M",
        "\x0e": "^N",
        "\x0f": "^O",
        "\x10": "^P",
        "\x11": "^Q",
        "\x12": "^R",
        "\x13": "^S",
        "\x14": "^T",
        "\x15": "^U",
        "\x16": "^V",
        "\x17": "^W",
        "\x18": "^X",
        "\x19": "^Y",
        "\x1a": "^Z",
        "\x1b": "^[",  # Escape
        "\x1c": "^\\",
        "\x1d": "^]",
        "\x1e": "^^",
        "\x1f": "^_",
        "\x7f": "^?",  # ASCII Delete (backspace).
        # Special characters. All visualized like Vim does.
        "\x80": "<80>",
        "\x81": "<81>",
        "\x82": "<82>",
        "\x83": "<83>",
        "\x84": "<84>",
        "\x85": "<85>",
        "\x86": "<86>",
        "\x87": "<87>",
        "\x88": "<88>",
        "\x89": "<89>",
        "\x8a": "<8a>",
        "\x8b": "<8b>",
        "\x8c": "<8c>",
        "\x8d": "<8d>",
        "\x8e": "<8e>",
        "\x8f": "<8f>",
        "\x90": "<90>",
        "\x91": "<91>",
        "\x92": "<92>",
        "\x93": "<93>",
        "\x94": "<94>",
        "\x95": "<95>",
        "\x96": "<96>",
        "\x97": "<97>",
        "\x98": "<98>",
        "\x99": "<99>",
        "\x9a": "<9a>",
        "\x9b": "<9b>",
        "\x9c": "<9c>",
        "\x9d": "<9d>",
        "\x9e": "<9e>",
        "\x9f": "<9f>",
        # For the non-breaking space: visualize like Emacs does by default.
        # (Print a space, but attach the 'nbsp' class that applies the
        # underline style.)
        "\xa0": " ",
    }

    def __init__(self, char: str = " ", style: str = "") -> None:
        # If this character has to be displayed otherwise, take that one.
        if char in self.display_mappings:
            if char == "\xa0":
                style += " class:nbsp "  # Will be underlined.
            else:
                style += " class:control-character "

            char = self.display_mappings[char]

        self.char = char
        self.style = style

        # Calculate width. (We always need this, so better to store it directly
        # as a member for performance.)
        self.width = get_cwidth(char)

    # In theory, `other` can be any type of object, but because of performance
    # we don't want to do an `isinstance` check every time. We assume "other"
    # is always a "Char".
    def _equal(self, other: Char) -> bool:
        return self.char == other.char and self.style == other.style

    def _not_equal(self, other: Char) -> bool:
        # Not equal: We don't do `not char.__eq__` here, because of the
        # performance of calling yet another function.
        return self.char != other.char or self.style != other.style

    if not TYPE_CHECKING:
        __eq__ = _equal
        __ne__ = _not_equal

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.char!r}, {self.style!r})"


_CHAR_CACHE: FastDictCache[tuple[str, str], Char] = FastDictCache(
    Char, size=1000 * 1000
)
Transparent = "[transparent]"


class Screen:
    """
    Two dimensional buffer of :class:`.Char` instances.
    """

    def __init__(
        self,
        default_char: Char | None = None,
        initial_width: int = 0,
        initial_height: int = 0,
    ) -> None:
        if default_char is None:
            default_char2 = _CHAR_CACHE[" ", Transparent]
        else:
            default_char2 = default_char

        self.data_buffer: defaultdict[int, defaultdict[int, Char]] = defaultdict(
            lambda: defaultdict(lambda: default_char2)
        )

        #: Escape sequences to be injected.
        self.zero_width_escapes: defaultdict[int, defaultdict[int, str]] = defaultdict(
            lambda: defaultdict(str)
        )

        #: Position of the cursor.
        self.cursor_positions: dict[
            Window, Point
        ] = {}  # Map `Window` objects to `Point` objects.

        #: Visibility of the cursor.
        self.show_cursor = True

        #: (Optional) Where to position the menu. E.g. at the start of a completion.
        #: (We can't use the cursor position, because we don't want the
        #: completion menu to change its position when we browse through all the
        #: completions.)
        self.menu_positions: dict[
            Window, Point
        ] = {}  # Map `Window` objects to `Point` objects.

        #: Currently used width/height of the screen. This will increase when
        #: data is written to the screen.
        self.width = initial_width or 0
        self.height = initial_height or 0

        # Windows that have been drawn. (Each `Window` class will add itself to
        # this list.)
        self.visible_windows_to_write_positions: dict[Window, WritePosition] = {}

        # List of (z_index, draw_func)
        self._draw_float_functions: list[tuple[int, Callable[[], None]]] = []

    @property
    def visible_windows(self) -> list[Window]:
        return list(self.visible_windows_to_write_positions.keys())

    def set_cursor_position(self, window: Window, position: Point) -> None:
        """
        Set the cursor position for a given window.
        """
        self.cursor_positions[window] = position

    def set_menu_position(self, window: Window, position: Point) -> None:
        """
        Set the cursor position for a given window.
        """
        self.menu_positions[window] = position

    def get_cursor_position(self, window: Window) -> Point:
        """
        Get the cursor position for a given window.
        Returns a `Point`.
        """
        try:
            return self.cursor_positions[window]
        except KeyError:
            return Point(x=0, y=0)

    def get_menu_position(self, window: Window) -> Point:
        """
        Get the menu position for a given window.
        (This falls back to the cursor position if no menu position was set.)
        """
        try:
            return self.menu_positions[window]
        except KeyError:
            try:
                return self.cursor_positions[window]
            except KeyError:
                return Point(x=0, y=0)

    def draw_with_z_index(self, z_index: int, draw_func: Callable[[], None]) -> None:
        """
        Add a draw-function for a `Window` which has a >= 0 z_index.
        This will be postponed until `draw_all_floats` is called.
        """
        self._draw_float_functions.append((z_index, draw_func))

    def draw_all_floats(self) -> None:
        """
        Draw all float functions in order of z-index.
        """
        # We keep looping because some draw functions could add new functions
        # to this list. See `FloatContainer`.
        while self._draw_float_functions:
            # Sort the floats that we have so far by z_index.
            functions = sorted(self._draw_float_functions, key=lambda item: item[0])

            # Draw only one at a time, then sort everything again. Now floats
            # might have been added.
            self._draw_float_functions = functions[1:]
            functions[0][1]()

    def append_style_to_content(self, style_str: str) -> None:
        """
        For all the characters in the screen.
        Set the style string to the given `style_str`.
        """
        b = self.data_buffer
        char_cache = _CHAR_CACHE

        append_style = " " + style_str

        for y, row in b.items():
            for x, char in row.items():
                row[x] = char_cache[char.char, char.style + append_style]

    def fill_area(
        self, write_position: WritePosition, style: str = "", after: bool = False
    ) -> None:
        """
        Fill the content of this area, using the given `style`.
        The style is prepended before whatever was here before.
        """
        if not style.strip():
            return

        xmin = write_position.xpos
        xmax = write_position.xpos + write_position.width
        char_cache = _CHAR_CACHE
        data_buffer = self.data_buffer

        if after:
            append_style = " " + style
            prepend_style = ""
        else:
            append_style = ""
            prepend_style = style + " "

        for y in range(
            write_position.ypos, write_position.ypos + write_position.height
        ):
            row = data_buffer[y]
            for x in range(xmin, xmax):
                cell = row[x]
                row[x] = char_cache[
                    cell.char, prepend_style + cell.style + append_style
                ]


class WritePosition:
    def __init__(self, xpos: int, ypos: int, width: int, height: int) -> None:
        assert height >= 0
        assert width >= 0
        # xpos and ypos can be negative. (A float can be partially visible.)

        self.xpos = xpos
        self.ypos = ypos
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.xpos!r}, y={self.ypos!r}, width={self.width!r}, height={self.height!r})"

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\browseProjects.py ===
import glob
import os
import pyclbr

import commctrl
import pywin.framework.scriptutils
import regutil
import win32api
import win32con
import win32ui
from pywin.mfc import afxres, dialog

from . import hierlist


class HLIErrorItem(hierlist.HierListItem):
    def __init__(self, text):
        self.text = text
        hierlist.HierListItem.__init__(self)

    def GetText(self):
        return self.text


class HLICLBRItem(hierlist.HierListItem):
    def __init__(self, name: str, file, lineno, suffix=""):
        # If the 'name' object itself has a .name, use it.  Not sure
        # how this happens, but seems pyclbr related.
        # See PyWin32 bug 817035
        self.name = getattr(name, "name", name)
        self.file = file
        self.lineno = lineno
        self.suffix = suffix

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def GetText(self):
        return self.name + self.suffix

    def TakeDefaultAction(self):
        if self.file:
            pywin.framework.scriptutils.JumpToDocument(
                self.file, self.lineno, bScrollToTop=1
            )
        else:
            win32ui.SetStatusText("The source of this object is unknown")

    def PerformItemSelected(self):
        if self.file is None:
            msg = f"{self.name} - source can not be located."
        else:
            msg = "%s defined at line %d of %s" % (self.name, self.lineno, self.file)
        win32ui.SetStatusText(msg)


class HLICLBRClass(HLICLBRItem):
    def __init__(self, clbrclass, suffix=""):
        try:
            name = clbrclass.name
            file = clbrclass.file
            lineno = clbrclass.lineno
            self.super = clbrclass.super
            self.methods = clbrclass.methods
        except AttributeError:
            name = clbrclass
            file = lineno = None
            self.super = []
            self.methods = {}
        HLICLBRItem.__init__(self, name, file, lineno, suffix)

    def GetSubList(self):
        ret = []
        for c in self.super:
            ret.append(HLICLBRClass(c, " (Parent class)"))
        for meth, lineno in self.methods.items():
            ret.append(HLICLBRMethod(meth, self.file, lineno, " (method)"))
        return ret

    def IsExpandable(self):
        return len(self.methods) + len(self.super)

    def GetBitmapColumn(self):
        return 21


class HLICLBRFunction(HLICLBRClass):
    def GetBitmapColumn(self):
        return 22


class HLICLBRMethod(HLICLBRItem):
    def GetBitmapColumn(self):
        return 22


class HLIModuleItem(hierlist.HierListItem):
    def __init__(self, path):
        hierlist.HierListItem.__init__(self)
        self.path = path

    def GetText(self):
        return os.path.split(self.path)[1] + " (module)"

    def IsExpandable(self):
        return 1

    def TakeDefaultAction(self):
        win32ui.GetApp().OpenDocumentFile(self.path)

    def GetBitmapColumn(self):
        col = 4  # Default
        try:
            if win32api.GetFileAttributes(self.path) & win32con.FILE_ATTRIBUTE_READONLY:
                col = 5
        except win32api.error:
            pass
        return col

    def GetSubList(self):
        mod, path = pywin.framework.scriptutils.GetPackageModuleName(self.path)
        win32ui.SetStatusText("Building class list - please wait...", 1)
        win32ui.DoWaitCursor(1)
        try:
            try:
                reader = pyclbr.readmodule_ex  # Post 1.5.2 interface.
                extra_msg = " or functions"
            except AttributeError:
                reader = pyclbr.readmodule
                extra_msg = ""
            data = reader(mod, [path])
            if data:
                ret = []
                for item in data.values():
                    if (
                        item.__class__ != pyclbr.Class
                    ):  # ie, it is a pyclbr Function instance (only introduced post 1.5.2)
                        ret.append(HLICLBRFunction(item, " (function)"))
                    else:
                        ret.append(HLICLBRClass(item, " (class)"))
                ret.sort()
                return ret
            else:
                return [HLIErrorItem(f"No Python classes{extra_msg} in module.")]
        finally:
            win32ui.DoWaitCursor(0)
            win32ui.SetStatusText(win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE))


def MakePathSubList(path):
    ret = []
    for filename in glob.glob(os.path.join(path, "*")):
        if os.path.isdir(filename) and os.path.isfile(
            os.path.join(filename, "__init__.py")
        ):
            ret.append(HLIDirectoryItem(filename, os.path.split(filename)[1]))
        else:
            if os.path.splitext(filename)[1].lower() in [".py", ".pyw"]:
                ret.append(HLIModuleItem(filename))
    return ret


class HLIDirectoryItem(hierlist.HierListItem):
    def __init__(self, path, displayName=None, bSubDirs=0):
        hierlist.HierListItem.__init__(self)
        self.path = path
        self.bSubDirs = bSubDirs
        if displayName:
            self.displayName = displayName
        else:
            self.displayName = path

    def IsExpandable(self):
        return 1

    def GetText(self):
        return self.displayName

    def GetSubList(self):
        ret = MakePathSubList(self.path)
        if (
            os.path.split(self.path)[1] == "win32com"
        ):  # Complete and utter hack for win32com.
            try:
                path = win32api.GetFullPathName(
                    os.path.join(self.path, "..\\win32comext")
                )
                ret.extend(MakePathSubList(path))
            except win32ui.error:
                pass
        return ret


class HLIProjectRoot(hierlist.HierListItem):
    def __init__(self, projectName, displayName=None):
        hierlist.HierListItem.__init__(self)
        self.projectName = projectName
        self.displayName = displayName or projectName

    def GetText(self):
        return self.displayName

    def IsExpandable(self):
        return 1

    def GetSubList(self):
        paths = regutil.GetRegisteredNamedPath(self.projectName)
        pathList = paths.split(";")
        if len(pathList) == 1:  # Single dir - don't bother putting the dir in
            ret = MakePathSubList(pathList[0])
        else:
            ret = list(map(HLIDirectoryItem, pathList))
        return ret


class HLIRoot(hierlist.HierListItem):
    def __init__(self):
        hierlist.HierListItem.__init__(self)

    def IsExpandable(self):
        return 1

    def GetSubList(self):
        keyStr = regutil.BuildDefaultPythonKey() + "\\PythonPath"
        hKey = win32api.RegOpenKey(regutil.GetRootKey(), keyStr)
        try:
            ret = []
            ret.append(HLIProjectRoot("", "Standard Python Library"))  # The core path.
            index = 0
            while 1:
                try:
                    ret.append(HLIProjectRoot(win32api.RegEnumKey(hKey, index)))
                    index += 1
                except win32api.error:
                    break
            return ret
        finally:
            win32api.RegCloseKey(hKey)


class dynamic_browser(dialog.Dialog):
    style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
    cs = (
        win32con.WS_CHILD
        | win32con.WS_VISIBLE
        | commctrl.TVS_HASLINES
        | commctrl.TVS_LINESATROOT
        | commctrl.TVS_HASBUTTONS
    )

    dt = [
        ["Python Projects", (0, 0, 200, 200), style, None, (8, "MS Sans Serif")],
        ["SysTreeView32", None, win32ui.IDC_LIST1, (0, 0, 200, 200), cs],
    ]

    def __init__(self, hli_root):
        dialog.Dialog.__init__(self, self.dt)
        self.hier_list = hierlist.HierListWithItems(hli_root, win32ui.IDB_BROWSER_HIER)
        self.HookMessage(self.on_size, win32con.WM_SIZE)

    def OnInitDialog(self):
        self.hier_list.HierInit(self)
        return dialog.Dialog.OnInitDialog(self)

    def on_size(self, params):
        lparam = params[3]
        w = win32api.LOWORD(lparam)
        h = win32api.HIWORD(lparam)
        self.GetDlgItem(win32ui.IDC_LIST1).MoveWindow((0, 0, w, h))


def BrowseDialog():
    root = HLIRoot()
    if not root.IsExpandable():
        raise TypeError(
            "Browse() argument must have __dict__ attribute, or be a Browser supported type"
        )

    dlg = dynamic_browser(root)
    dlg.CreateWindow()


def DockableBrowserCreator(parent):
    root = HLIRoot()
    hl = hierlist.HierListWithItems(root, win32ui.IDB_BROWSER_HIER)

    style = (
        win32con.WS_CHILD
        | win32con.WS_VISIBLE
        | win32con.WS_BORDER
        | commctrl.TVS_HASLINES
        | commctrl.TVS_LINESATROOT
        | commctrl.TVS_HASBUTTONS
    )

    control = win32ui.CreateTreeCtrl()
    control.CreateWindow(style, (0, 0, 150, 300), parent, win32ui.IDC_LIST1)
    list = hl.HierInit(parent, control)
    return control


def DockablePathBrowser():
    import pywin.docking.DockingBar

    bar = pywin.docking.DockingBar.DockingBar()
    bar.CreateWindow(
        win32ui.GetMainFrame(), DockableBrowserCreator, "Path Browser", 0x8E0A
    )
    bar.SetBarStyle(
        bar.GetBarStyle()
        | afxres.CBRS_TOOLTIPS
        | afxres.CBRS_FLYBY
        | afxres.CBRS_SIZE_DYNAMIC
    )
    bar.EnableDocking(afxres.CBRS_ALIGN_ANY)
    win32ui.GetMainFrame().DockControlBar(bar)


# The "default" entry point
Browse = DockablePathBrowser

# === NexusCore/myenv\Lib\site-packages\pip\_internal\build_env.py ===
"""Build Environment used for isolation during sdist building
"""

import logging
import os
import pathlib
import site
import sys
import textwrap
from collections import OrderedDict
from types import TracebackType
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Tuple, Type, Union

from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.cli.spinners import open_spinner
from pip._internal.locations import get_platlib, get_purelib, get_scheme
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.logging import VERBOSE
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


def _dedup(a: str, b: str) -> Union[Tuple[str], Tuple[str, str]]:
    return (a, b) if a != b else (a,)


class _Prefix:
    def __init__(self, path: str) -> None:
        self.path = path
        self.setup = False
        scheme = get_scheme("", prefix=path)
        self.bin_dir = scheme.scripts
        self.lib_dirs = _dedup(scheme.purelib, scheme.platlib)


def get_runnable_pip() -> str:
    """Get a file to pass to a Python executable, to run the currently-running pip.

    This is used to run a pip subprocess, for installing requirements into the build
    environment.
    """
    source = pathlib.Path(pip_location).resolve().parent

    if not source.is_dir():
        # This would happen if someone is using pip from inside a zip file. In that
        # case, we can use that directly.
        return str(source)

    return os.fsdecode(source / "__pip-runner__.py")


def _get_system_sitepackages() -> Set[str]:
    """Get system site packages

    Usually from site.getsitepackages,
    but fallback on `get_purelib()/get_platlib()` if unavailable
    (e.g. in a virtualenv created by virtualenv<20)

    Returns normalized set of strings.
    """
    if hasattr(site, "getsitepackages"):
        system_sites = site.getsitepackages()
    else:
        # virtualenv < 20 overwrites site.py without getsitepackages
        # fallback on get_purelib/get_platlib.
        # this is known to miss things, but shouldn't in the cases
        # where getsitepackages() has been removed (inside a virtualenv)
        system_sites = [get_purelib(), get_platlib()]
    return {os.path.normcase(path) for path in system_sites}


class BuildEnvironment:
    """Creates and manages an isolated environment to install build deps"""

    def __init__(self) -> None:
        temp_dir = TempDirectory(kind=tempdir_kinds.BUILD_ENV, globally_managed=True)

        self._prefixes = OrderedDict(
            (name, _Prefix(os.path.join(temp_dir.path, name)))
            for name in ("normal", "overlay")
        )

        self._bin_dirs: List[str] = []
        self._lib_dirs: List[str] = []
        for prefix in reversed(list(self._prefixes.values())):
            self._bin_dirs.append(prefix.bin_dir)
            self._lib_dirs.extend(prefix.lib_dirs)

        # Customize site to:
        # - ensure .pth files are honored
        # - prevent access to system site packages
        system_sites = _get_system_sitepackages()

        self._site_dir = os.path.join(temp_dir.path, "site")
        if not os.path.exists(self._site_dir):
            os.mkdir(self._site_dir)
        with open(
            os.path.join(self._site_dir, "sitecustomize.py"), "w", encoding="utf-8"
        ) as fp:
            fp.write(
                textwrap.dedent(
                    """
                import os, site, sys

                # First, drop system-sites related paths.
                original_sys_path = sys.path[:]
                known_paths = set()
                for path in {system_sites!r}:
                    site.addsitedir(path, known_paths=known_paths)
                system_paths = set(
                    os.path.normcase(path)
                    for path in sys.path[len(original_sys_path):]
                )
                original_sys_path = [
                    path for path in original_sys_path
                    if os.path.normcase(path) not in system_paths
                ]
                sys.path = original_sys_path

                # Second, add lib directories.
                # ensuring .pth file are processed.
                for path in {lib_dirs!r}:
                    assert not path in sys.path
                    site.addsitedir(path)
                """
                ).format(system_sites=system_sites, lib_dirs=self._lib_dirs)
            )

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name, None)
            for name in ("PATH", "PYTHONNOUSERSITE", "PYTHONPATH")
        }

        path = self._bin_dirs[:]
        old_path = self._save_env["PATH"]
        if old_path:
            path.extend(old_path.split(os.pathsep))

        pythonpath = [self._site_dir]

        os.environ.update(
            {
                "PATH": os.pathsep.join(path),
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": os.pathsep.join(pythonpath),
            }
        )

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        for varname, old_value in self._save_env.items():
            if old_value is None:
                os.environ.pop(varname, None)
            else:
                os.environ[varname] = old_value

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        """Return 2 sets:
        - conflicting requirements: set of (installed, wanted) reqs tuples
        - missing requirements: set of reqs
        """
        missing = set()
        conflicting = set()
        if reqs:
            env = (
                get_environment(self._lib_dirs)
                if hasattr(self, "_lib_dirs")
                else get_default_environment()
            )
            for req_str in reqs:
                req = get_requirement(req_str)
                # We're explicitly evaluating with an empty extra value, since build
                # environments are not provided any mechanism to select specific extras.
                if req.marker is not None and not req.marker.evaluate({"extra": ""}):
                    continue
                dist = env.get_distribution(req.name)
                if not dist:
                    missing.add(req_str)
                    continue
                if isinstance(dist.version, Version):
                    installed_req_str = f"{req.name}=={dist.version}"
                else:
                    installed_req_str = f"{req.name}==={dist.version}"
                if not req.specifier.contains(dist.version, prereleases=True):
                    conflicting.add((installed_req_str, req_str))
                # FIXME: Consider direct URL?
        return conflicting, missing

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        prefix = self._prefixes[prefix_as_string]
        assert not prefix.setup
        prefix.setup = True
        if not requirements:
            return
        self._install_requirements(
            get_runnable_pip(),
            finder,
            requirements,
            prefix,
            kind=kind,
        )

    @staticmethod
    def _install_requirements(
        pip_runnable: str,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix: _Prefix,
        *,
        kind: str,
    ) -> None:
        args: List[str] = [
            sys.executable,
            pip_runnable,
            "install",
            "--ignore-installed",
            "--no-user",
            "--prefix",
            prefix.path,
            "--no-warn-script-location",
            "--disable-pip-version-check",
            # The prefix specified two lines above, thus
            # target from config file or env var should be ignored
            "--target",
            "",
        ]
        if logger.getEffectiveLevel() <= logging.DEBUG:
            args.append("-vv")
        elif logger.getEffectiveLevel() <= VERBOSE:
            args.append("-v")
        for format_control in ("no_binary", "only_binary"):
            formats = getattr(finder.format_control, format_control)
            args.extend(
                (
                    "--" + format_control.replace("_", "-"),
                    ",".join(sorted(formats or {":none:"})),
                )
            )

        index_urls = finder.index_urls
        if index_urls:
            args.extend(["-i", index_urls[0]])
            for extra_index in index_urls[1:]:
                args.extend(["--extra-index-url", extra_index])
        else:
            args.append("--no-index")
        for link in finder.find_links:
            args.extend(["--find-links", link])

        if finder.proxy:
            args.extend(["--proxy", finder.proxy])
        for host in finder.trusted_hosts:
            args.extend(["--trusted-host", host])
        if finder.custom_cert:
            args.extend(["--cert", finder.custom_cert])
        if finder.client_cert:
            args.extend(["--client-cert", finder.client_cert])
        if finder.allow_all_prereleases:
            args.append("--pre")
        if finder.prefer_binary:
            args.append("--prefer-binary")
        args.append("--")
        args.extend(requirements)
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
            )


class NoOpBuildEnvironment(BuildEnvironment):
    """A no-op drop-in replacement for BuildEnvironment"""

    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\jupyter_core\application.py ===
"""
A base Application class for Jupyter applications.

All Jupyter applications should inherit from this.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import logging
import os
import sys
import typing as t
from copy import deepcopy
from pathlib import Path
from shutil import which

from traitlets import Bool, List, Unicode, observe
from traitlets.config.application import Application, catch_config_error
from traitlets.config.loader import ConfigFileNotFound

from .paths import (
    allow_insecure_writes,
    issue_insecure_write_warning,
    jupyter_config_dir,
    jupyter_config_path,
    jupyter_data_dir,
    jupyter_path,
    jupyter_runtime_dir,
)
from .utils import ensure_dir_exists, ensure_event_loop

# mypy: disable-error-code="no-untyped-call"

# aliases and flags

base_aliases: dict[str, t.Any] = {}
if isinstance(Application.aliases, dict):
    # traitlets 5
    base_aliases.update(Application.aliases)
_jupyter_aliases = {
    "log-level": "Application.log_level",
    "config": "JupyterApp.config_file",
}
base_aliases.update(_jupyter_aliases)

base_flags: dict[str, t.Any] = {}
if isinstance(Application.flags, dict):
    # traitlets 5
    base_flags.update(Application.flags)
_jupyter_flags: dict[str, t.Any] = {
    "debug": (
        {"Application": {"log_level": logging.DEBUG}},
        "set log level to logging.DEBUG (maximize logging output)",
    ),
    "generate-config": ({"JupyterApp": {"generate_config": True}}, "generate default config file"),
    "y": (
        {"JupyterApp": {"answer_yes": True}},
        "Answer yes to any questions instead of prompting.",
    ),
}
base_flags.update(_jupyter_flags)


class NoStart(Exception):
    """Exception to raise when an application shouldn't start"""


class JupyterApp(Application):
    """Base class for Jupyter applications"""

    name = "jupyter"  # override in subclasses
    description = "A Jupyter Application"

    aliases = base_aliases
    flags = base_flags

    def _log_level_default(self) -> int:
        return logging.INFO

    jupyter_path = List(Unicode())

    def _jupyter_path_default(self) -> list[str]:
        return jupyter_path()

    config_dir = Unicode()

    def _config_dir_default(self) -> str:
        return jupyter_config_dir()

    @property
    def config_file_paths(self) -> list[str]:
        path = jupyter_config_path()
        if self.config_dir not in path:
            # Insert config dir as first item.
            path.insert(0, self.config_dir)
        return path

    data_dir = Unicode()

    def _data_dir_default(self) -> str:
        d = jupyter_data_dir()
        ensure_dir_exists(d, mode=0o700)
        return d

    runtime_dir = Unicode()

    def _runtime_dir_default(self) -> str:
        rd = jupyter_runtime_dir()
        ensure_dir_exists(rd, mode=0o700)
        return rd

    @observe("runtime_dir")
    def _runtime_dir_changed(self, change: t.Any) -> None:
        ensure_dir_exists(change["new"], mode=0o700)

    generate_config = Bool(False, config=True, help="""Generate default config file.""")

    config_file_name = Unicode(config=True, help="Specify a config file to load.")

    def _config_file_name_default(self) -> str:
        if not self.name:
            return ""
        return self.name.replace("-", "_") + "_config"

    config_file = Unicode(
        config=True,
        help="""Full path of a config file.""",
    )

    answer_yes = Bool(False, config=True, help="""Answer yes to any prompts.""")

    def write_default_config(self) -> None:
        """Write our default config to a .py config file"""
        config_file: str
        if self.config_file:
            config_file = self.config_file
        else:
            config_file = str(Path(self.config_dir, self.config_file_name + ".py"))

        if Path(config_file).exists() and not self.answer_yes:
            answer = ""

            def ask() -> str:
                prompt = f"Overwrite {config_file!r} with default config? [y/N]"
                try:
                    return input(prompt).lower() or "n"
                except KeyboardInterrupt:
                    print("")  # empty line
                    return "n"

            answer = ask()
            while not answer.startswith(("y", "n")):
                print("Please answer 'yes' or 'no'")
                answer = ask()
            if answer.startswith("n"):
                return

        config_text = self.generate_config_file()
        print("Writing default config to: {config_file!r}")
        ensure_dir_exists(Path(config_file).parent.resolve(), 0o700)
        with Path.open(Path(config_file), mode="w", encoding="utf-8") as f:
            f.write(config_text)

    def migrate_config(self) -> None:
        """Migrate config/data from IPython 3"""
        try:  # let's see if we can open the marker file
            # for reading and updating (writing)
            f_marker = Path.open(Path(self.config_dir, "migrated"), "r+")
        except FileNotFoundError:  # cannot find the marker file
            pass  # that means we have not migrated yet, so continue
        except OSError:  # not readable and/or writable
            return  # so let's give up migration in such an environment
        else:  # if we got here without raising anything,
            # that means the file exists
            f_marker.close()
            return  # so we must have already migrated -> bail out

        from .migrate import get_ipython_dir, migrate

        # No IPython dir, nothing to migrate
        if not Path(get_ipython_dir()).exists():
            return

        migrate()

    def load_config_file(self, suppress_errors: bool = True) -> None:  # type:ignore[override]
        """Load the config file.

        By default, errors in loading config are handled, and a warning
        printed on screen. For testing, the suppress_errors option is set
        to False, so errors will make tests fail.
        """
        self.log.debug("Searching %s for config files", self.config_file_paths)
        base_config = "jupyter_config"
        try:
            super().load_config_file(
                base_config,
                path=self.config_file_paths,
            )
        except ConfigFileNotFound:
            # ignore errors loading parent
            self.log.debug("Config file %s not found", base_config)

        if self.config_file:
            path, config_file_name = os.path.split(self.config_file)
        else:
            path = self.config_file_paths  # type:ignore[assignment]
            config_file_name = self.config_file_name

            if not config_file_name or (config_file_name == base_config):
                return

        try:
            super().load_config_file(config_file_name, path=path)
        except ConfigFileNotFound:
            self.log.debug("Config file not found, skipping: %s", config_file_name)
        except Exception:
            # Reraise errors for testing purposes, or if set in
            # self.raise_config_file_errors
            if (not suppress_errors) or self.raise_config_file_errors:
                raise
            self.log.warning("Error loading config file: %s", config_file_name, exc_info=True)

    # subcommand-related
    def _find_subcommand(self, name: str) -> str:
        name = f"{self.name}-{name}"
        return which(name) or ""

    @property
    def _dispatching(self) -> bool:
        """Return whether we are dispatching to another command

        or running ourselves.
        """
        return bool(self.generate_config or self.subapp or self.subcommand)

    subcommand = Unicode()

    @catch_config_error
    def initialize(self, argv: t.Any = None) -> None:
        """Initialize the application."""
        # don't hook up crash handler before parsing command-line
        if argv is None:
            argv = sys.argv[1:]
        if argv:
            subc = self._find_subcommand(argv[0])
            if subc:
                self.argv = argv
                self.subcommand = subc
                return
        self.parse_command_line(argv)
        cl_config = deepcopy(self.config)
        if self._dispatching:
            return
        self.migrate_config()
        self.load_config_file()
        # enforce cl-opts override configfile opts:
        self.update_config(cl_config)
        if allow_insecure_writes:
            issue_insecure_write_warning()

    def start(self) -> None:
        """Start the whole thing"""
        if self.subcommand:
            os.execv(self.subcommand, [self.subcommand] + self.argv[1:])  # noqa: S606
            raise NoStart()

        if self.subapp:
            self.subapp.start()
            raise NoStart()

        if self.generate_config:
            self.write_default_config()
            raise NoStart()

    @classmethod
    def launch_instance(cls, argv: t.Any = None, **kwargs: t.Any) -> None:
        """Launch an instance of a Jupyter Application"""
        # Ensure an event loop is set before any other code runs.
        loop = ensure_event_loop()
        try:
            super().launch_instance(argv=argv, **kwargs)
        except NoStart:
            return
        loop.close()


class JupyterAsyncApp(JupyterApp):
    """A Jupyter application that runs on an asyncio loop."""

    name = "jupyter_async"  # override in subclasses
    description = "An Async Jupyter Application"

    # Set to True for tornado-based apps.
    _prefer_selector_loop = False

    async def initialize_async(self, argv: t.Any = None) -> None:
        """Initialize the application asynchronoously."""

    async def start_async(self) -> None:
        """Run the application in an event loop."""

    @classmethod
    async def _launch_instance(cls, argv: t.Any = None, **kwargs: t.Any) -> None:
        app = cls.instance(**kwargs)
        app.initialize(argv)
        await app.initialize_async(argv)
        await app.start_async()

    @classmethod
    def launch_instance(cls, argv: t.Any = None, **kwargs: t.Any) -> None:
        """Launch an instance of an async Jupyter Application"""
        loop = ensure_event_loop(cls._prefer_selector_loop)
        coro = cls._launch_instance(argv, **kwargs)
        loop.run_until_complete(coro)
        loop.close()


if __name__ == "__main__":
    JupyterApp.launch_instance()

# === NexusCore/openenv\Lib\site-packages\fontTools\svgLib\path\parser.py ===
# SVG Path specification parser.
# This is an adaptation from 'svg.path' by Lennart Regebro (@regebro),
# modified so that the parser takes a FontTools Pen object instead of
# returning a list of svg.path Path objects.
# The original code can be found at:
# https://github.com/regebro/svg.path/blob/4f9b6e3/src/svg/path/parser.py
# Copyright (c) 2013-2014 Lennart Regebro
# License: MIT

from .arc import EllipticalArc
import re


COMMANDS = set("MmZzLlHhVvCcSsQqTtAa")
ARC_COMMANDS = set("Aa")
UPPERCASE = set("MZLHVCSQTA")

COMMAND_RE = re.compile("([MmZzLlHhVvCcSsQqTtAa])")

# https://www.w3.org/TR/css-syntax-3/#number-token-diagram
#   but -6.e-5 will be tokenized as "-6" then "-5" and confuse parsing
FLOAT_RE = re.compile(
    r"[-+]?"  # optional sign
    r"(?:"
    r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?"  # int/float
    r"|"
    r"(?:\.[0-9]+(?:[eE][-+]?[0-9]+)?)"  # float with leading dot (e.g. '.42')
    r")"
)
BOOL_RE = re.compile("^[01]")
SEPARATOR_RE = re.compile(f"[, \t]")


def _tokenize_path(pathdef):
    arc_cmd = None
    for x in COMMAND_RE.split(pathdef):
        if x in COMMANDS:
            arc_cmd = x if x in ARC_COMMANDS else None
            yield x
            continue

        if arc_cmd:
            try:
                yield from _tokenize_arc_arguments(x)
            except ValueError as e:
                raise ValueError(f"Invalid arc command: '{arc_cmd}{x}'") from e
        else:
            for token in FLOAT_RE.findall(x):
                yield token


ARC_ARGUMENT_TYPES = (
    ("rx", FLOAT_RE),
    ("ry", FLOAT_RE),
    ("x-axis-rotation", FLOAT_RE),
    ("large-arc-flag", BOOL_RE),
    ("sweep-flag", BOOL_RE),
    ("x", FLOAT_RE),
    ("y", FLOAT_RE),
)


def _tokenize_arc_arguments(arcdef):
    raw_args = [s for s in SEPARATOR_RE.split(arcdef) if s]
    if not raw_args:
        raise ValueError(f"Not enough arguments: '{arcdef}'")
    raw_args.reverse()

    i = 0
    while raw_args:
        arg = raw_args.pop()

        name, pattern = ARC_ARGUMENT_TYPES[i]
        match = pattern.search(arg)
        if not match:
            raise ValueError(f"Invalid argument for '{name}' parameter: {arg!r}")

        j, k = match.span()
        yield arg[j:k]
        arg = arg[k:]

        if arg:
            raw_args.append(arg)

        # wrap around every 7 consecutive arguments
        if i == 6:
            i = 0
        else:
            i += 1

    if i != 0:
        raise ValueError(f"Not enough arguments: '{arcdef}'")


def parse_path(pathdef, pen, current_pos=(0, 0), arc_class=EllipticalArc):
    """Parse SVG path definition (i.e. "d" attribute of <path> elements)
    and call a 'pen' object's moveTo, lineTo, curveTo, qCurveTo and closePath
    methods.

    If 'current_pos' (2-float tuple) is provided, the initial moveTo will
    be relative to that instead being absolute.

    If the pen has an "arcTo" method, it is called with the original values
    of the elliptical arc curve commands:

    .. code-block::

        pen.arcTo(rx, ry, rotation, arc_large, arc_sweep, (x, y))

    Otherwise, the arcs are approximated by series of cubic Bezier segments
    ("curveTo"), one every 90 degrees.
    """
    # In the SVG specs, initial movetos are absolute, even if
    # specified as 'm'. This is the default behavior here as well.
    # But if you pass in a current_pos variable, the initial moveto
    # will be relative to that current_pos. This is useful.
    current_pos = complex(*current_pos)

    elements = list(_tokenize_path(pathdef))
    # Reverse for easy use of .pop()
    elements.reverse()

    start_pos = None
    command = None
    last_control = None

    have_arcTo = hasattr(pen, "arcTo")

    while elements:
        if elements[-1] in COMMANDS:
            # New command.
            last_command = command  # Used by S and T
            command = elements.pop()
            absolute = command in UPPERCASE
            command = command.upper()
        else:
            # If this element starts with numbers, it is an implicit command
            # and we don't change the command. Check that it's allowed:
            if command is None:
                raise ValueError(
                    "Unallowed implicit command in %s, position %s"
                    % (pathdef, len(pathdef.split()) - len(elements))
                )
            last_command = command  # Used by S and T

        if command == "M":
            # Moveto command.
            x = elements.pop()
            y = elements.pop()
            pos = float(x) + float(y) * 1j
            if absolute:
                current_pos = pos
            else:
                current_pos += pos

            # M is not preceded by Z; it's an open subpath
            if start_pos is not None:
                pen.endPath()

            pen.moveTo((current_pos.real, current_pos.imag))

            # when M is called, reset start_pos
            # This behavior of Z is defined in svg spec:
            # http://www.w3.org/TR/SVG/paths.html#PathDataClosePathCommand
            start_pos = current_pos

            # Implicit moveto commands are treated as lineto commands.
            # So we set command to lineto here, in case there are
            # further implicit commands after this moveto.
            command = "L"

        elif command == "Z":
            # Close path
            if current_pos != start_pos:
                pen.lineTo((start_pos.real, start_pos.imag))
            pen.closePath()
            current_pos = start_pos
            start_pos = None
            command = None  # You can't have implicit commands after closing.

        elif command == "L":
            x = elements.pop()
            y = elements.pop()
            pos = float(x) + float(y) * 1j
            if not absolute:
                pos += current_pos
            pen.lineTo((pos.real, pos.imag))
            current_pos = pos

        elif command == "H":
            x = elements.pop()
            pos = float(x) + current_pos.imag * 1j
            if not absolute:
                pos += current_pos.real
            pen.lineTo((pos.real, pos.imag))
            current_pos = pos

        elif command == "V":
            y = elements.pop()
            pos = current_pos.real + float(y) * 1j
            if not absolute:
                pos += current_pos.imag * 1j
            pen.lineTo((pos.real, pos.imag))
            current_pos = pos

        elif command == "C":
            control1 = float(elements.pop()) + float(elements.pop()) * 1j
            control2 = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control1 += current_pos
                control2 += current_pos
                end += current_pos

            pen.curveTo(
                (control1.real, control1.imag),
                (control2.real, control2.imag),
                (end.real, end.imag),
            )
            current_pos = end
            last_control = control2

        elif command == "S":
            # Smooth curve. First control point is the "reflection" of
            # the second control point in the previous path.

            if last_command not in "CS":
                # If there is no previous command or if the previous command
                # was not an C, c, S or s, assume the first control point is
                # coincident with the current point.
                control1 = current_pos
            else:
                # The first control point is assumed to be the reflection of
                # the second control point on the previous command relative
                # to the current point.
                control1 = current_pos + current_pos - last_control

            control2 = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control2 += current_pos
                end += current_pos

            pen.curveTo(
                (control1.real, control1.imag),
                (control2.real, control2.imag),
                (end.real, end.imag),
            )
            current_pos = end
            last_control = control2

        elif command == "Q":
            control = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control += current_pos
                end += current_pos

            pen.qCurveTo((control.real, control.imag), (end.real, end.imag))
            current_pos = end
            last_control = control

        elif command == "T":
            # Smooth curve. Control point is the "reflection" of
            # the second control point in the previous path.

            if last_command not in "QT":
                # If there is no previous command or if the previous command
                # was not an Q, q, T or t, assume the first control point is
                # coincident with the current point.
                control = current_pos
            else:
                # The control point is assumed to be the reflection of
                # the control point on the previous command relative
                # to the current point.
                control = current_pos + current_pos - last_control

            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                end += current_pos

            pen.qCurveTo((control.real, control.imag), (end.real, end.imag))
            current_pos = end
            last_control = control

        elif command == "A":
            rx = abs(float(elements.pop()))
            ry = abs(float(elements.pop()))
            rotation = float(elements.pop())
            arc_large = bool(int(elements.pop()))
            arc_sweep = bool(int(elements.pop()))
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                end += current_pos

            # if the pen supports arcs, pass the values unchanged, otherwise
            # approximate the arc with a series of cubic bezier curves
            if have_arcTo:
                pen.arcTo(
                    rx,
                    ry,
                    rotation,
                    arc_large,
                    arc_sweep,
                    (end.real, end.imag),
                )
            else:
                arc = arc_class(
                    current_pos, rx, ry, rotation, arc_large, arc_sweep, end
                )
                arc.draw(pen)

            current_pos = end

    # no final Z command, it's an open path
    if start_pos is not None:
        pen.endPath()

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\shortcuts\filters.py ===
"""
Filters restricting scope of IPython Terminal shortcuts.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import ast
import re
import signal
import sys
from typing import Callable, Dict, Union

from prompt_toolkit.application.current import get_app
from prompt_toolkit.enums import DEFAULT_BUFFER, SEARCH_BUFFER
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.filters import Condition, Filter, emacs_insert_mode, has_completions
from prompt_toolkit.filters import has_focus as has_focus_impl
from prompt_toolkit.filters import (
    Always,
    Never,
    has_selection,
    has_suggestion,
    vi_insert_mode,
    vi_mode,
)
from prompt_toolkit.layout.layout import FocusableElement

from IPython.core.getipython import get_ipython
from IPython.core.guarded_eval import _find_dunder, BINARY_OP_DUNDERS, UNARY_OP_DUNDERS
from IPython.terminal.shortcuts import auto_suggest
from IPython.utils.decorators import undoc


@undoc
@Condition
def cursor_in_leading_ws():
    before = get_app().current_buffer.document.current_line_before_cursor
    return (not before) or before.isspace()


def has_focus(value: FocusableElement):
    """Wrapper around has_focus adding a nice `__name__` to tester function"""
    tester = has_focus_impl(value).func
    tester.__name__ = f"is_focused({value})"
    return Condition(tester)


@undoc
@Condition
def has_line_below() -> bool:
    document = get_app().current_buffer.document
    return document.cursor_position_row < len(document.lines) - 1


@undoc
@Condition
def is_cursor_at_the_end_of_line() -> bool:
    document = get_app().current_buffer.document
    return document.is_cursor_at_the_end_of_line


@undoc
@Condition
def has_line_above() -> bool:
    document = get_app().current_buffer.document
    return document.cursor_position_row != 0


@Condition
def ebivim():
    shell = get_ipython()
    return shell.emacs_bindings_in_vi_insert_mode


@Condition
def supports_suspend():
    return hasattr(signal, "SIGTSTP")


@Condition
def auto_match():
    shell = get_ipython()
    return shell.auto_match


def all_quotes_paired(quote, buf):
    paired = True
    i = 0
    while i < len(buf):
        c = buf[i]
        if c == quote:
            paired = not paired
        elif c == "\\":
            i += 1
        i += 1
    return paired


_preceding_text_cache: Dict[Union[str, Callable], Condition] = {}
_following_text_cache: Dict[Union[str, Callable], Condition] = {}


def preceding_text(pattern: Union[str, Callable]):
    if pattern in _preceding_text_cache:
        return _preceding_text_cache[pattern]

    if callable(pattern):

        def _preceding_text():
            app = get_app()
            before_cursor = app.current_buffer.document.current_line_before_cursor
            # mypy can't infer if(callable): https://github.com/python/mypy/issues/3603
            return bool(pattern(before_cursor))  # type: ignore[operator]

    else:
        m = re.compile(pattern)

        def _preceding_text():
            app = get_app()
            before_cursor = app.current_buffer.document.current_line_before_cursor
            return bool(m.match(before_cursor))

        _preceding_text.__name__ = f"preceding_text({pattern!r})"

    condition = Condition(_preceding_text)
    _preceding_text_cache[pattern] = condition
    return condition


def following_text(pattern):
    try:
        return _following_text_cache[pattern]
    except KeyError:
        pass
    m = re.compile(pattern)

    def _following_text():
        app = get_app()
        return bool(m.match(app.current_buffer.document.current_line_after_cursor))

    _following_text.__name__ = f"following_text({pattern!r})"

    condition = Condition(_following_text)
    _following_text_cache[pattern] = condition
    return condition


@Condition
def not_inside_unclosed_string():
    app = get_app()
    s = app.current_buffer.document.text_before_cursor
    # remove escaped quotes
    s = s.replace('\\"', "").replace("\\'", "")
    # remove triple-quoted string literals
    s = re.sub(r"(?:\"\"\"[\s\S]*\"\"\"|'''[\s\S]*''')", "", s)
    # remove single-quoted string literals
    s = re.sub(r"""(?:"[^"]*["\n]|'[^']*['\n])""", "", s)
    return not ('"' in s or "'" in s)


@Condition
def navigable_suggestions():
    shell = get_ipython()
    return isinstance(shell.auto_suggest, auto_suggest.NavigableAutoSuggestFromHistory)


@Condition
def readline_like_completions():
    shell = get_ipython()
    return shell.display_completions == "readlinelike"


@Condition
def is_windows_os():
    return sys.platform == "win32"


class PassThrough(Filter):
    """A filter allowing to implement pass-through behaviour of keybindings.

    Prompt toolkit key processor dispatches only one event per binding match,
    which means that adding a new shortcut will suppress the old shortcut
    if the keybindings are the same (unless one is filtered out).

    To stop a shortcut binding from suppressing other shortcuts:
    - add the `pass_through` filter to list of filter, and
    - call `pass_through.reply(event)` in the shortcut handler.
    """

    def __init__(self):
        self._is_replying = False

    def reply(self, event: KeyPressEvent):
        self._is_replying = True
        try:
            event.key_processor.reset()
            event.key_processor.feed_multiple(event.key_sequence)
            event.key_processor.process_keys()
        finally:
            self._is_replying = False

    def __call__(self):
        return not self._is_replying


pass_through = PassThrough()

# these one is callable and re-used multiple times hence needs to be
# only defined once beforehand so that transforming back to human-readable
# names works well in the documentation.
default_buffer_focused = has_focus(DEFAULT_BUFFER)

KEYBINDING_FILTERS = {
    "always": Always(),
    # never is used for exposing commands which have no default keybindings
    "never": Never(),
    "has_line_below": has_line_below,
    "has_line_above": has_line_above,
    "is_cursor_at_the_end_of_line": is_cursor_at_the_end_of_line,
    "has_selection": has_selection,
    "has_suggestion": has_suggestion,
    "vi_mode": vi_mode,
    "vi_insert_mode": vi_insert_mode,
    "emacs_insert_mode": emacs_insert_mode,
    # https://github.com/ipython/ipython/pull/12603 argued for inclusion of
    # emacs key bindings with a configurable `emacs_bindings_in_vi_insert_mode`
    # toggle; when the toggle is on user can access keybindigns like `ctrl + e`
    # in vi insert mode. Because some of the emacs bindings involve `escape`
    # followed by another key, e.g. `escape` followed by `f`, prompt-toolkit
    # needs to wait to see if there will be another character typed in before
    # executing pure `escape` keybinding; in vi insert mode `escape` switches to
    # command mode which is common and performance critical action for vi users.
    # To avoid the delay users employ a workaround:
    # https://github.com/ipython/ipython/issues/13443#issuecomment-1032753703
    # which involves switching `emacs_bindings_in_vi_insert_mode` off.
    #
    # For the workaround to work:
    # 1) end users need to toggle `emacs_bindings_in_vi_insert_mode` off
    # 2) all keybindings which would involve `escape` need to respect that
    #    toggle by including either:
    #      - `vi_insert_mode & ebivim` for actions which have emacs keybindings
    #        predefined upstream in prompt-toolkit, or
    #      - `emacs_like_insert_mode` for actions which do not have existing
    #        emacs keybindings predefined upstream (or need overriding of the
    #        upstream bindings to modify behaviour), defined below.
    "emacs_like_insert_mode": (vi_insert_mode & ebivim) | emacs_insert_mode,
    "has_completions": has_completions,
    "insert_mode": vi_insert_mode | emacs_insert_mode,
    "default_buffer_focused": default_buffer_focused,
    "search_buffer_focused": has_focus(SEARCH_BUFFER),
    # `ebivim` stands for emacs bindings in vi insert mode
    "ebivim": ebivim,
    "supports_suspend": supports_suspend,
    "is_windows_os": is_windows_os,
    "auto_match": auto_match,
    "focused_insert": (vi_insert_mode | emacs_insert_mode) & default_buffer_focused,
    "not_inside_unclosed_string": not_inside_unclosed_string,
    "readline_like_completions": readline_like_completions,
    "preceded_by_paired_double_quotes": preceding_text(
        lambda line: all_quotes_paired('"', line)
    ),
    "preceded_by_paired_single_quotes": preceding_text(
        lambda line: all_quotes_paired("'", line)
    ),
    "preceded_by_raw_str_prefix": preceding_text(r".*(r|R)[\"'](-*)$"),
    "preceded_by_two_double_quotes": preceding_text(r'^.*""$'),
    "preceded_by_two_single_quotes": preceding_text(r"^.*''$"),
    "followed_by_closing_paren_or_end": following_text(r"[,)}\]]|$"),
    "preceded_by_opening_round_paren": preceding_text(r".*\($"),
    "preceded_by_opening_bracket": preceding_text(r".*\[$"),
    "preceded_by_opening_brace": preceding_text(r".*\{$"),
    "preceded_by_double_quote": preceding_text('.*"$'),
    "preceded_by_single_quote": preceding_text(r".*'$"),
    "followed_by_closing_round_paren": following_text(r"^\)"),
    "followed_by_closing_bracket": following_text(r"^\]"),
    "followed_by_closing_brace": following_text(r"^\}"),
    "followed_by_double_quote": following_text('^"'),
    "followed_by_single_quote": following_text("^'"),
    "navigable_suggestions": navigable_suggestions,
    "cursor_in_leading_ws": cursor_in_leading_ws,
    "pass_through": pass_through,
}


def eval_node(node: Union[ast.AST, None]):
    if node is None:
        return None
    if isinstance(node, ast.Expression):
        return eval_node(node.body)
    if isinstance(node, ast.BinOp):
        left = eval_node(node.left)
        right = eval_node(node.right)
        dunders = _find_dunder(node.op, BINARY_OP_DUNDERS)
        if dunders:
            return getattr(left, dunders[0])(right)
        raise ValueError(f"Unknown binary operation: {node.op}")
    if isinstance(node, ast.UnaryOp):
        value = eval_node(node.operand)
        dunders = _find_dunder(node.op, UNARY_OP_DUNDERS)
        if dunders:
            return getattr(value, dunders[0])()
        raise ValueError(f"Unknown unary operation: {node.op}")
    if isinstance(node, ast.Name):
        if node.id in KEYBINDING_FILTERS:
            return KEYBINDING_FILTERS[node.id]
        else:
            sep = "\n  - "
            known_filters = sep.join(sorted(KEYBINDING_FILTERS))
            raise NameError(
                f"{node.id} is not a known shortcut filter."
                f" Known filters are: {sep}{known_filters}."
            )
    raise ValueError("Unhandled node", ast.dump(node))


def filter_from_string(code: str):
    expression = ast.parse(code, mode="eval")
    return eval_node(expression)


__all__ = ["KEYBINDING_FILTERS", "filter_from_string"]

# === NexusCore/openenv\Lib\site-packages\matplotlib\axes\_secondary_axes.py ===
import numbers

import numpy as np

from matplotlib import _api, _docstring, transforms
import matplotlib.ticker as mticker
from matplotlib.axes._base import _AxesBase, _TransformedBoundsLocator
from matplotlib.axis import Axis
from matplotlib.transforms import Transform


class SecondaryAxis(_AxesBase):
    """
    General class to hold a Secondary_X/Yaxis.
    """

    def __init__(self, parent, orientation, location, functions, transform=None,
                 **kwargs):
        """
        See `.secondary_xaxis` and `.secondary_yaxis` for the doc string.
        While there is no need for this to be private, it should really be
        called by those higher level functions.
        """
        _api.check_in_list(["x", "y"], orientation=orientation)
        self._functions = functions
        self._parent = parent
        self._orientation = orientation
        self._ticks_set = False

        fig = self._parent.get_figure(root=False)
        if self._orientation == 'x':
            super().__init__(fig, [0, 1., 1, 0.0001], **kwargs)
            self._axis = self.xaxis
            self._locstrings = ['top', 'bottom']
            self._otherstrings = ['left', 'right']
        else:  # 'y'
            super().__init__(fig, [0, 1., 0.0001, 1], **kwargs)
            self._axis = self.yaxis
            self._locstrings = ['right', 'left']
            self._otherstrings = ['top', 'bottom']
        self._parentscale = None
        # this gets positioned w/o constrained_layout so exclude:

        self.set_location(location, transform)
        self.set_functions(functions)

        # styling:
        otheraxis = self.yaxis if self._orientation == 'x' else self.xaxis
        otheraxis.set_major_locator(mticker.NullLocator())
        otheraxis.set_ticks_position('none')

        self.spines[self._otherstrings].set_visible(False)
        self.spines[self._locstrings].set_visible(True)

        if self._pos < 0.5:
            # flip the location strings...
            self._locstrings = self._locstrings[::-1]
        self.set_alignment(self._locstrings[0])

    def set_alignment(self, align):
        """
        Set if axes spine and labels are drawn at top or bottom (or left/right)
        of the Axes.

        Parameters
        ----------
        align : {'top', 'bottom', 'left', 'right'}
            Either 'top' or 'bottom' for orientation='x' or
            'left' or 'right' for orientation='y' axis.
        """
        _api.check_in_list(self._locstrings, align=align)
        if align == self._locstrings[1]:  # Need to change the orientation.
            self._locstrings = self._locstrings[::-1]
        self.spines[self._locstrings[0]].set_visible(True)
        self.spines[self._locstrings[1]].set_visible(False)
        self._axis.set_ticks_position(align)
        self._axis.set_label_position(align)

    def set_location(self, location, transform=None):
        """
        Set the vertical or horizontal location of the axes in
        parent-normalized coordinates.

        Parameters
        ----------
        location : {'top', 'bottom', 'left', 'right'} or float
            The position to put the secondary axis.  Strings can be 'top' or
            'bottom' for orientation='x' and 'right' or 'left' for
            orientation='y'. A float indicates the relative position on the
            parent Axes to put the new Axes, 0.0 being the bottom (or left)
            and 1.0 being the top (or right).

        transform : `.Transform`, optional
            Transform for the location to use. Defaults to
            the parent's ``transAxes``, so locations are normally relative to
            the parent axes.

            .. versionadded:: 3.9
        """

        _api.check_isinstance((transforms.Transform, None), transform=transform)

        # This puts the rectangle into figure-relative coordinates.
        if isinstance(location, str):
            _api.check_in_list(self._locstrings, location=location)
            self._pos = 1. if location in ('top', 'right') else 0.
        elif isinstance(location, numbers.Real):
            self._pos = location
        else:
            raise ValueError(
                f"location must be {self._locstrings[0]!r}, "
                f"{self._locstrings[1]!r}, or a float, not {location!r}")

        self._loc = location

        if self._orientation == 'x':
            # An x-secondary axes is like an inset axes from x = 0 to x = 1 and
            # from y = pos to y = pos + eps, in the parent's transAxes coords.
            bounds = [0, self._pos, 1., 1e-10]

            # If a transformation is provided, use its y component rather than
            # the parent's transAxes. This can be used to place axes in the data
            # coords, for instance.
            if transform is not None:
                transform = transforms.blended_transform_factory(
                    self._parent.transAxes, transform)
        else:  # 'y'
            bounds = [self._pos, 0, 1e-10, 1]
            if transform is not None:
                transform = transforms.blended_transform_factory(
                    transform, self._parent.transAxes)  # Use provided x axis

        # If no transform is provided, use the parent's transAxes
        if transform is None:
            transform = self._parent.transAxes

        # this locator lets the axes move in the parent axes coordinates.
        # so it never needs to know where the parent is explicitly in
        # figure coordinates.
        # it gets called in ax.apply_aspect() (of all places)
        self.set_axes_locator(_TransformedBoundsLocator(bounds, transform))

    def apply_aspect(self, position=None):
        # docstring inherited.
        self._set_lims()
        super().apply_aspect(position)

    @_docstring.copy(Axis.set_ticks)
    def set_ticks(self, ticks, labels=None, *, minor=False, **kwargs):
        ret = self._axis.set_ticks(ticks, labels, minor=minor, **kwargs)
        self.stale = True
        self._ticks_set = True
        return ret

    def set_functions(self, functions):
        """
        Set how the secondary axis converts limits from the parent Axes.

        Parameters
        ----------
        functions : 2-tuple of func, or `Transform` with an inverse.
            Transform between the parent axis values and the secondary axis
            values.

            If supplied as a 2-tuple of functions, the first function is
            the forward transform function and the second is the inverse
            transform.

            If a transform is supplied, then the transform must have an
            inverse.
        """

        if (isinstance(functions, tuple) and len(functions) == 2 and
                callable(functions[0]) and callable(functions[1])):
            # make an arbitrary convert from a two-tuple of functions
            # forward and inverse.
            self._functions = functions
        elif isinstance(functions, Transform):
            self._functions = (
                 functions.transform,
                 lambda x: functions.inverted().transform(x)
            )
        elif functions is None:
            self._functions = (lambda x: x, lambda x: x)
        else:
            raise ValueError('functions argument of secondary Axes '
                             'must be a two-tuple of callable functions '
                             'with the first function being the transform '
                             'and the second being the inverse')
        self._set_scale()

    def draw(self, renderer):
        """
        Draw the secondary Axes.

        Consults the parent Axes for its limits and converts them
        using the converter specified by
        `~.axes._secondary_axes.set_functions` (or *functions*
        parameter when Axes initialized.)
        """
        self._set_lims()
        # this sets the scale in case the parent has set its scale.
        self._set_scale()
        super().draw(renderer)

    def _set_scale(self):
        """
        Check if parent has set its scale
        """

        if self._orientation == 'x':
            pscale = self._parent.xaxis.get_scale()
            set_scale = self.set_xscale
        else:  # 'y'
            pscale = self._parent.yaxis.get_scale()
            set_scale = self.set_yscale
        if pscale == self._parentscale:
            return

        if self._ticks_set:
            ticks = self._axis.get_ticklocs()

        # need to invert the roles here for the ticks to line up.
        set_scale('functionlog' if pscale == 'log' else 'function',
                  functions=self._functions[::-1])

        # OK, set_scale sets the locators, but if we've called
        # axsecond.set_ticks, we want to keep those.
        if self._ticks_set:
            self._axis.set_major_locator(mticker.FixedLocator(ticks))

        # If the parent scale doesn't change, we can skip this next time.
        self._parentscale = pscale

    def _set_lims(self):
        """
        Set the limits based on parent limits and the convert method
        between the parent and this secondary Axes.
        """
        if self._orientation == 'x':
            lims = self._parent.get_xlim()
            set_lim = self.set_xlim
        else:  # 'y'
            lims = self._parent.get_ylim()
            set_lim = self.set_ylim
        order = lims[0] < lims[1]
        lims = self._functions[0](np.array(lims))
        neworder = lims[0] < lims[1]
        if neworder != order:
            # Flip because the transform will take care of the flipping.
            lims = lims[::-1]
        set_lim(lims)

    def set_aspect(self, *args, **kwargs):
        """
        Secondary Axes cannot set the aspect ratio, so calling this just
        sets a warning.
        """
        _api.warn_external("Secondary Axes can't set the aspect ratio")

    def set_color(self, color):
        """
        Change the color of the secondary Axes and all decorators.

        Parameters
        ----------
        color : :mpltype:`color`
        """
        axis = self._axis_map[self._orientation]
        axis.set_tick_params(colors=color)
        for spine in self.spines.values():
            if spine.axis is axis:
                spine.set_color(color)
        axis.label.set_color(color)


_secax_docstring = '''
Warnings
--------
This method is experimental as of 3.1, and the API may change.

Parameters
----------
location : {'top', 'bottom', 'left', 'right'} or float
    The position to put the secondary axis.  Strings can be 'top' or
    'bottom' for orientation='x' and 'right' or 'left' for
    orientation='y'. A float indicates the relative position on the
    parent Axes to put the new Axes, 0.0 being the bottom (or left)
    and 1.0 being the top (or right).

functions : 2-tuple of func, or Transform with an inverse

    If a 2-tuple of functions, the user specifies the transform
    function and its inverse.  i.e.
    ``functions=(lambda x: 2 / x, lambda x: 2 / x)`` would be an
    reciprocal transform with a factor of 2. Both functions must accept
    numpy arrays as input.

    The user can also directly supply a subclass of
    `.transforms.Transform` so long as it has an inverse.

    See :doc:`/gallery/subplots_axes_and_figures/secondary_axis`
    for examples of making these conversions.

transform : `.Transform`, optional
    If specified, *location* will be
    placed relative to this transform (in the direction of the axis)
    rather than the parent's axis. i.e. a secondary x-axis will
    use the provided y transform and the x transform of the parent.

    .. versionadded:: 3.9

Returns
-------
ax : axes._secondary_axes.SecondaryAxis

Other Parameters
----------------
**kwargs : `~matplotlib.axes.Axes` properties.
    Other miscellaneous Axes parameters.
'''
_docstring.interpd.register(_secax_docstring=_secax_docstring)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\build_env.py ===
"""Build Environment used for isolation during sdist building
"""

import logging
import os
import pathlib
import site
import sys
import textwrap
from collections import OrderedDict
from types import TracebackType
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Tuple, Type, Union

from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.cli.spinners import open_spinner
from pip._internal.locations import get_platlib, get_purelib, get_scheme
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.logging import VERBOSE
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


def _dedup(a: str, b: str) -> Union[Tuple[str], Tuple[str, str]]:
    return (a, b) if a != b else (a,)


class _Prefix:
    def __init__(self, path: str) -> None:
        self.path = path
        self.setup = False
        scheme = get_scheme("", prefix=path)
        self.bin_dir = scheme.scripts
        self.lib_dirs = _dedup(scheme.purelib, scheme.platlib)


def get_runnable_pip() -> str:
    """Get a file to pass to a Python executable, to run the currently-running pip.

    This is used to run a pip subprocess, for installing requirements into the build
    environment.
    """
    source = pathlib.Path(pip_location).resolve().parent

    if not source.is_dir():
        # This would happen if someone is using pip from inside a zip file. In that
        # case, we can use that directly.
        return str(source)

    return os.fsdecode(source / "__pip-runner__.py")


def _get_system_sitepackages() -> Set[str]:
    """Get system site packages

    Usually from site.getsitepackages,
    but fallback on `get_purelib()/get_platlib()` if unavailable
    (e.g. in a virtualenv created by virtualenv<20)

    Returns normalized set of strings.
    """
    if hasattr(site, "getsitepackages"):
        system_sites = site.getsitepackages()
    else:
        # virtualenv < 20 overwrites site.py without getsitepackages
        # fallback on get_purelib/get_platlib.
        # this is known to miss things, but shouldn't in the cases
        # where getsitepackages() has been removed (inside a virtualenv)
        system_sites = [get_purelib(), get_platlib()]
    return {os.path.normcase(path) for path in system_sites}


class BuildEnvironment:
    """Creates and manages an isolated environment to install build deps"""

    def __init__(self) -> None:
        temp_dir = TempDirectory(kind=tempdir_kinds.BUILD_ENV, globally_managed=True)

        self._prefixes = OrderedDict(
            (name, _Prefix(os.path.join(temp_dir.path, name)))
            for name in ("normal", "overlay")
        )

        self._bin_dirs: List[str] = []
        self._lib_dirs: List[str] = []
        for prefix in reversed(list(self._prefixes.values())):
            self._bin_dirs.append(prefix.bin_dir)
            self._lib_dirs.extend(prefix.lib_dirs)

        # Customize site to:
        # - ensure .pth files are honored
        # - prevent access to system site packages
        system_sites = _get_system_sitepackages()

        self._site_dir = os.path.join(temp_dir.path, "site")
        if not os.path.exists(self._site_dir):
            os.mkdir(self._site_dir)
        with open(
            os.path.join(self._site_dir, "sitecustomize.py"), "w", encoding="utf-8"
        ) as fp:
            fp.write(
                textwrap.dedent(
                    """
                import os, site, sys

                # First, drop system-sites related paths.
                original_sys_path = sys.path[:]
                known_paths = set()
                for path in {system_sites!r}:
                    site.addsitedir(path, known_paths=known_paths)
                system_paths = set(
                    os.path.normcase(path)
                    for path in sys.path[len(original_sys_path):]
                )
                original_sys_path = [
                    path for path in original_sys_path
                    if os.path.normcase(path) not in system_paths
                ]
                sys.path = original_sys_path

                # Second, add lib directories.
                # ensuring .pth file are processed.
                for path in {lib_dirs!r}:
                    assert not path in sys.path
                    site.addsitedir(path)
                """
                ).format(system_sites=system_sites, lib_dirs=self._lib_dirs)
            )

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name, None)
            for name in ("PATH", "PYTHONNOUSERSITE", "PYTHONPATH")
        }

        path = self._bin_dirs[:]
        old_path = self._save_env["PATH"]
        if old_path:
            path.extend(old_path.split(os.pathsep))

        pythonpath = [self._site_dir]

        os.environ.update(
            {
                "PATH": os.pathsep.join(path),
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": os.pathsep.join(pythonpath),
            }
        )

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        for varname, old_value in self._save_env.items():
            if old_value is None:
                os.environ.pop(varname, None)
            else:
                os.environ[varname] = old_value

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        """Return 2 sets:
        - conflicting requirements: set of (installed, wanted) reqs tuples
        - missing requirements: set of reqs
        """
        missing = set()
        conflicting = set()
        if reqs:
            env = (
                get_environment(self._lib_dirs)
                if hasattr(self, "_lib_dirs")
                else get_default_environment()
            )
            for req_str in reqs:
                req = get_requirement(req_str)
                # We're explicitly evaluating with an empty extra value, since build
                # environments are not provided any mechanism to select specific extras.
                if req.marker is not None and not req.marker.evaluate({"extra": ""}):
                    continue
                dist = env.get_distribution(req.name)
                if not dist:
                    missing.add(req_str)
                    continue
                if isinstance(dist.version, Version):
                    installed_req_str = f"{req.name}=={dist.version}"
                else:
                    installed_req_str = f"{req.name}==={dist.version}"
                if not req.specifier.contains(dist.version, prereleases=True):
                    conflicting.add((installed_req_str, req_str))
                # FIXME: Consider direct URL?
        return conflicting, missing

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        prefix = self._prefixes[prefix_as_string]
        assert not prefix.setup
        prefix.setup = True
        if not requirements:
            return
        self._install_requirements(
            get_runnable_pip(),
            finder,
            requirements,
            prefix,
            kind=kind,
        )

    @staticmethod
    def _install_requirements(
        pip_runnable: str,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix: _Prefix,
        *,
        kind: str,
    ) -> None:
        args: List[str] = [
            sys.executable,
            pip_runnable,
            "install",
            "--ignore-installed",
            "--no-user",
            "--prefix",
            prefix.path,
            "--no-warn-script-location",
            "--disable-pip-version-check",
            # The prefix specified two lines above, thus
            # target from config file or env var should be ignored
            "--target",
            "",
        ]
        if logger.getEffectiveLevel() <= logging.DEBUG:
            args.append("-vv")
        elif logger.getEffectiveLevel() <= VERBOSE:
            args.append("-v")
        for format_control in ("no_binary", "only_binary"):
            formats = getattr(finder.format_control, format_control)
            args.extend(
                (
                    "--" + format_control.replace("_", "-"),
                    ",".join(sorted(formats or {":none:"})),
                )
            )

        index_urls = finder.index_urls
        if index_urls:
            args.extend(["-i", index_urls[0]])
            for extra_index in index_urls[1:]:
                args.extend(["--extra-index-url", extra_index])
        else:
            args.append("--no-index")
        for link in finder.find_links:
            args.extend(["--find-links", link])

        if finder.proxy:
            args.extend(["--proxy", finder.proxy])
        for host in finder.trusted_hosts:
            args.extend(["--trusted-host", host])
        if finder.custom_cert:
            args.extend(["--cert", finder.custom_cert])
        if finder.client_cert:
            args.extend(["--client-cert", finder.client_cert])
        if finder.allow_all_prereleases:
            args.append("--pre")
        if finder.prefer_binary:
            args.append("--prefer-binary")
        args.append("--")
        args.extend(requirements)
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
            )


class NoOpBuildEnvironment(BuildEnvironment):
    """A no-op drop-in replacement for BuildEnvironment"""

    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\rsa\cli.py ===
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Commandline scripts.

These scripts are called by the executables defined in setup.py.
"""

import abc
import sys
import typing
import optparse

import rsa
import rsa.key
import rsa.pkcs1

HASH_METHODS = sorted(rsa.pkcs1.HASH_METHODS.keys())
Indexable = typing.Union[typing.Tuple, typing.List[str]]


def keygen() -> None:
    """Key generator."""

    # Parse the CLI options
    parser = optparse.OptionParser(
        usage="usage: %prog [options] keysize",
        description='Generates a new RSA key pair of "keysize" bits.',
    )

    parser.add_option(
        "--pubout",
        type="string",
        help="Output filename for the public key. The public key is "
        "not saved if this option is not present. You can use "
        "pyrsa-priv2pub to create the public key file later.",
    )

    parser.add_option(
        "-o",
        "--out",
        type="string",
        help="Output filename for the private key. The key is "
        "written to stdout if this option is not present.",
    )

    parser.add_option(
        "--form",
        help="key format of the private and public keys - default PEM",
        choices=("PEM", "DER"),
        default="PEM",
    )

    (cli, cli_args) = parser.parse_args(sys.argv[1:])

    if len(cli_args) != 1:
        parser.print_help()
        raise SystemExit(1)

    try:
        keysize = int(cli_args[0])
    except ValueError as ex:
        parser.print_help()
        print("Not a valid number: %s" % cli_args[0], file=sys.stderr)
        raise SystemExit(1) from ex

    print("Generating %i-bit key" % keysize, file=sys.stderr)
    (pub_key, priv_key) = rsa.newkeys(keysize)

    # Save public key
    if cli.pubout:
        print("Writing public key to %s" % cli.pubout, file=sys.stderr)
        data = pub_key.save_pkcs1(format=cli.form)
        with open(cli.pubout, "wb") as outfile:
            outfile.write(data)

    # Save private key
    data = priv_key.save_pkcs1(format=cli.form)

    if cli.out:
        print("Writing private key to %s" % cli.out, file=sys.stderr)
        with open(cli.out, "wb") as outfile:
            outfile.write(data)
    else:
        print("Writing private key to stdout", file=sys.stderr)
        sys.stdout.buffer.write(data)


class CryptoOperation(metaclass=abc.ABCMeta):
    """CLI callable that operates with input, output, and a key."""

    keyname = "public"  # or 'private'
    usage = "usage: %%prog [options] %(keyname)s_key"
    description = ""
    operation = "decrypt"
    operation_past = "decrypted"
    operation_progressive = "decrypting"
    input_help = "Name of the file to %(operation)s. Reads from stdin if " "not specified."
    output_help = (
        "Name of the file to write the %(operation_past)s file "
        "to. Written to stdout if this option is not present."
    )
    expected_cli_args = 1
    has_output = True

    key_class = rsa.PublicKey  # type: typing.Type[rsa.key.AbstractKey]

    def __init__(self) -> None:
        self.usage = self.usage % self.__class__.__dict__
        self.input_help = self.input_help % self.__class__.__dict__
        self.output_help = self.output_help % self.__class__.__dict__

    @abc.abstractmethod
    def perform_operation(
        self, indata: bytes, key: rsa.key.AbstractKey, cli_args: Indexable
    ) -> typing.Any:
        """Performs the program's operation.

        Implement in a subclass.

        :returns: the data to write to the output.
        """

    def __call__(self) -> None:
        """Runs the program."""

        (cli, cli_args) = self.parse_cli()

        key = self.read_key(cli_args[0], cli.keyform)

        indata = self.read_infile(cli.input)

        print(self.operation_progressive.title(), file=sys.stderr)
        outdata = self.perform_operation(indata, key, cli_args)

        if self.has_output:
            self.write_outfile(outdata, cli.output)

    def parse_cli(self) -> typing.Tuple[optparse.Values, typing.List[str]]:
        """Parse the CLI options

        :returns: (cli_opts, cli_args)
        """

        parser = optparse.OptionParser(usage=self.usage, description=self.description)

        parser.add_option("-i", "--input", type="string", help=self.input_help)

        if self.has_output:
            parser.add_option("-o", "--output", type="string", help=self.output_help)

        parser.add_option(
            "--keyform",
            help="Key format of the %s key - default PEM" % self.keyname,
            choices=("PEM", "DER"),
            default="PEM",
        )

        (cli, cli_args) = parser.parse_args(sys.argv[1:])

        if len(cli_args) != self.expected_cli_args:
            parser.print_help()
            raise SystemExit(1)

        return cli, cli_args

    def read_key(self, filename: str, keyform: str) -> rsa.key.AbstractKey:
        """Reads a public or private key."""

        print("Reading %s key from %s" % (self.keyname, filename), file=sys.stderr)
        with open(filename, "rb") as keyfile:
            keydata = keyfile.read()

        return self.key_class.load_pkcs1(keydata, keyform)

    def read_infile(self, inname: str) -> bytes:
        """Read the input file"""

        if inname:
            print("Reading input from %s" % inname, file=sys.stderr)
            with open(inname, "rb") as infile:
                return infile.read()

        print("Reading input from stdin", file=sys.stderr)
        return sys.stdin.buffer.read()

    def write_outfile(self, outdata: bytes, outname: str) -> None:
        """Write the output file"""

        if outname:
            print("Writing output to %s" % outname, file=sys.stderr)
            with open(outname, "wb") as outfile:
                outfile.write(outdata)
        else:
            print("Writing output to stdout", file=sys.stderr)
            sys.stdout.buffer.write(outdata)


class EncryptOperation(CryptoOperation):
    """Encrypts a file."""

    keyname = "public"
    description = (
        "Encrypts a file. The file must be shorter than the key " "length in order to be encrypted."
    )
    operation = "encrypt"
    operation_past = "encrypted"
    operation_progressive = "encrypting"

    def perform_operation(
        self, indata: bytes, pub_key: rsa.key.AbstractKey, cli_args: Indexable = ()
    ) -> bytes:
        """Encrypts files."""
        assert isinstance(pub_key, rsa.key.PublicKey)
        return rsa.encrypt(indata, pub_key)


class DecryptOperation(CryptoOperation):
    """Decrypts a file."""

    keyname = "private"
    description = (
        "Decrypts a file. The original file must be shorter than "
        "the key length in order to have been encrypted."
    )
    operation = "decrypt"
    operation_past = "decrypted"
    operation_progressive = "decrypting"
    key_class = rsa.PrivateKey

    def perform_operation(
        self, indata: bytes, priv_key: rsa.key.AbstractKey, cli_args: Indexable = ()
    ) -> bytes:
        """Decrypts files."""
        assert isinstance(priv_key, rsa.key.PrivateKey)
        return rsa.decrypt(indata, priv_key)


class SignOperation(CryptoOperation):
    """Signs a file."""

    keyname = "private"
    usage = "usage: %%prog [options] private_key hash_method"
    description = (
        "Signs a file, outputs the signature. Choose the hash "
        "method from %s" % ", ".join(HASH_METHODS)
    )
    operation = "sign"
    operation_past = "signature"
    operation_progressive = "Signing"
    key_class = rsa.PrivateKey
    expected_cli_args = 2

    output_help = (
        "Name of the file to write the signature to. Written "
        "to stdout if this option is not present."
    )

    def perform_operation(
        self, indata: bytes, priv_key: rsa.key.AbstractKey, cli_args: Indexable
    ) -> bytes:
        """Signs files."""
        assert isinstance(priv_key, rsa.key.PrivateKey)

        hash_method = cli_args[1]
        if hash_method not in HASH_METHODS:
            raise SystemExit("Invalid hash method, choose one of %s" % ", ".join(HASH_METHODS))

        return rsa.sign(indata, priv_key, hash_method)


class VerifyOperation(CryptoOperation):
    """Verify a signature."""

    keyname = "public"
    usage = "usage: %%prog [options] public_key signature_file"
    description = (
        "Verifies a signature, exits with status 0 upon success, "
        "prints an error message and exits with status 1 upon error."
    )
    operation = "verify"
    operation_past = "verified"
    operation_progressive = "Verifying"
    key_class = rsa.PublicKey
    expected_cli_args = 2
    has_output = False

    def perform_operation(
        self, indata: bytes, pub_key: rsa.key.AbstractKey, cli_args: Indexable
    ) -> None:
        """Verifies files."""
        assert isinstance(pub_key, rsa.key.PublicKey)

        signature_file = cli_args[1]

        with open(signature_file, "rb") as sigfile:
            signature = sigfile.read()

        try:
            rsa.verify(indata, signature, pub_key)
        except rsa.VerificationError as ex:
            raise SystemExit("Verification failed.") from ex

        print("Verification OK", file=sys.stderr)


encrypt = EncryptOperation()
decrypt = DecryptOperation()
sign = SignOperation()
verify = VerifyOperation()

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\image\image_handler.py ===
import copy
import json
import os
from typing import TYPE_CHECKING, Any, Optional, Union

import httpx
from pydantic import BaseModel

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LitellmLogging
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.utils import ImageResponse

from ..base_aws_llm import BaseAWSLLM
from ..common_utils import BedrockError

if TYPE_CHECKING:
    from botocore.awsrequest import AWSPreparedRequest
else:
    AWSPreparedRequest = Any


class BedrockImagePreparedRequest(BaseModel):
    """
    Internal/Helper class for preparing the request for bedrock image generation
    """

    endpoint_url: str
    prepped: AWSPreparedRequest
    body: bytes
    data: dict


class BedrockImageGeneration(BaseAWSLLM):
    """
    Bedrock Image Generation handler
    """

    def image_generation(
        self,
        model: str,
        prompt: str,
        model_response: ImageResponse,
        optional_params: dict,
        logging_obj: LitellmLogging,
        timeout: Optional[Union[float, httpx.Timeout]],
        aimg_generation: bool = False,
        api_base: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ):
        prepared_request = self._prepare_request(
            model=model,
            optional_params=optional_params,
            api_base=api_base,
            extra_headers=extra_headers,
            logging_obj=logging_obj,
            prompt=prompt,
        )

        if aimg_generation is True:
            return self.async_image_generation(
                prepared_request=prepared_request,
                timeout=timeout,
                model=model,
                logging_obj=logging_obj,
                prompt=prompt,
                model_response=model_response,
                client=(
                    client
                    if client is not None and isinstance(client, AsyncHTTPHandler)
                    else None
                ),
            )

        if client is None or not isinstance(client, HTTPHandler):
            client = _get_httpx_client()
        try:
            response = client.post(url=prepared_request.endpoint_url, headers=prepared_request.prepped.headers, data=prepared_request.body)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")
        ### FORMAT RESPONSE TO OPENAI FORMAT ###
        model_response = self._transform_response_dict_to_openai_response(
            model_response=model_response,
            model=model,
            logging_obj=logging_obj,
            prompt=prompt,
            response=response,
            data=prepared_request.data,
        )
        return model_response

    async def async_image_generation(
        self,
        prepared_request: BedrockImagePreparedRequest,
        timeout: Optional[Union[float, httpx.Timeout]],
        model: str,
        logging_obj: LitellmLogging,
        prompt: str,
        model_response: ImageResponse,
        client: Optional[AsyncHTTPHandler] = None,
    ) -> ImageResponse:
        """
        Asynchronous handler for bedrock image generation

        Awaits the response from the bedrock image generation endpoint
        """
        async_client = client or get_async_httpx_client(
            llm_provider=litellm.LlmProviders.BEDROCK,
            params={"timeout": timeout},
        )

        try:
            response = await async_client.post(url=prepared_request.endpoint_url, headers=prepared_request.prepped.headers, data=prepared_request.body)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        ### FORMAT RESPONSE TO OPENAI FORMAT ###
        model_response = self._transform_response_dict_to_openai_response(
            model=model,
            logging_obj=logging_obj,
            prompt=prompt,
            response=response,
            data=prepared_request.data,
            model_response=model_response,
        )
        return model_response

    def _prepare_request(
        self,
        model: str,
        optional_params: dict,
        api_base: Optional[str],
        extra_headers: Optional[dict],
        logging_obj: LitellmLogging,
        prompt: str,
    ) -> BedrockImagePreparedRequest:
        """
        Prepare the request body, headers, and endpoint URL for the Bedrock Image Generation API

        Args:
            model (str): The model to use for the image generation
            optional_params (dict): The optional parameters for the image generation
            api_base (Optional[str]): The base URL for the Bedrock API
            extra_headers (Optional[dict]): The extra headers to include in the request
            logging_obj (LitellmLogging): The logging object to use for logging
            prompt (str): The prompt to use for the image generation
        Returns:
            BedrockImagePreparedRequest: The prepared request object

        The BedrockImagePreparedRequest contains:
            endpoint_url (str): The endpoint URL for the Bedrock Image Generation API
            prepped (httpx.Request): The prepared request object
            body (bytes): The request body
        """
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        boto3_credentials_info = self._get_boto_credentials_from_optional_params(
            optional_params, model
        )

        ### SET RUNTIME ENDPOINT ###
        modelId = model
        _, proxy_endpoint_url = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=boto3_credentials_info.aws_bedrock_runtime_endpoint,
            aws_region_name=boto3_credentials_info.aws_region_name,
        )
        proxy_endpoint_url = f"{proxy_endpoint_url}/model/{modelId}/invoke"
        sigv4 = SigV4Auth(
            boto3_credentials_info.credentials,
            "bedrock",
            boto3_credentials_info.aws_region_name,
        )

        data = self._get_request_body(
            model=model, prompt=prompt, optional_params=optional_params
        )

        # Make POST Request
        body = json.dumps(data).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}
        request = AWSRequest(
            method="POST", url=proxy_endpoint_url, data=body, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]
        prepped = request.prepare()

        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": proxy_endpoint_url,
                "headers": prepped.headers,
            },
        )
        return BedrockImagePreparedRequest(
            endpoint_url=proxy_endpoint_url,
            prepped=prepped,
            body=body,
            data=data,
        )

    def _get_request_body(
        self,
        model: str,
        prompt: str,
        optional_params: dict,
    ) -> dict:
        """
        Get the request body for the Bedrock Image Generation API

        Checks the model/provider and transforms the request body accordingly

        Returns:
            dict: The request body to use for the Bedrock Image Generation API
        """
        provider = model.split(".")[0]
        inference_params = copy.deepcopy(optional_params)
        inference_params.pop(
            "user", None
        )  # make sure user is not passed in for bedrock call
        data = {}
        if provider == "stability":
            if litellm.AmazonStability3Config._is_stability_3_model(model):
                request_body = litellm.AmazonStability3Config.transform_request_body(
                    prompt=prompt, optional_params=optional_params
                )
                return dict(request_body)
            else:
                prompt = prompt.replace(os.linesep, " ")
                ## LOAD CONFIG
                config = litellm.AmazonStabilityConfig.get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                data = {
                    "text_prompts": [{"text": prompt, "weight": 1}],
                    **inference_params,
                }
        elif provider == "amazon":
            return dict(
                litellm.AmazonNovaCanvasConfig.transform_request_body(
                    text=prompt, optional_params=optional_params
                )
            )
        else:
            raise BedrockError(
                status_code=422, message=f"Unsupported model={model}, passed in"
            )
        return data

    def _transform_response_dict_to_openai_response(
        self,
        model_response: ImageResponse,
        model: str,
        logging_obj: LitellmLogging,
        prompt: str,
        response: httpx.Response,
        data: dict,
    ) -> ImageResponse:
        """
        Transforms the Image Generation response from Bedrock to OpenAI format
        """

        ## LOGGING
        if logging_obj is not None:
            logging_obj.post_call(
                input=prompt,
                api_key="",
                original_response=response.text,
                additional_args={"complete_input_dict": data},
            )
        verbose_logger.debug("raw model_response: %s", response.text)
        response_dict = response.json()
        if response_dict is None:
            raise ValueError("Error in response object format, got None")

        config_class = (
            litellm.AmazonStability3Config
            if litellm.AmazonStability3Config._is_stability_3_model(model=model)
            else (
                litellm.AmazonNovaCanvasConfig
                if litellm.AmazonNovaCanvasConfig._is_nova_model(model=model)
                else litellm.AmazonStabilityConfig
            )
        )
        config_class.transform_response_dict_to_openai_response(
            model_response=model_response,
            response_dict=response_dict,
        )

        return model_response

# === NexusCore/evaluation\evaluate\multi_turn\gen_plus_solution_multiround_human_feedback.py ===
import argparse
import os
import torch
from pathlib import Path
from tqdm import tqdm
import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from evalplus.data import (get_human_eval_plus, 
    write_jsonl,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from utils import sanitize_solution,check_correctness,get_groundtruth,SUCCESS
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from copy import deepcopy
from chat_with_gpt import gpt_predict

MAX_TRY = 2

def humaneval_build_instruction(languge: str, question: str):
    return '''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given code to do completion:
```{}
{}
```
Please continue to complete the function with {} programming language. You are not allowed to modify the given code and do the completion only. 

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''.strip().format(languge.lower(), question.strip(),languge.lower(),languge.lower())

mbpp_build_deepseekcoder_instruction='''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given problem and test examples:
{}

Please use the {} programming language to solve this problem.
Please make sure that your code includes the functions from the test samples and that the input and output formats of these functions match the test samples.

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''


def build_gpt_prompt(pre_messages: str, problem: str, current_code: str, execution_feedback: str):
    prompt = """You are tasked with providing guidance to a programmer who has drafted a code for a programming problem. 
Your role is to mimic human-like responses and offer suggestions for modifying the code based on the observed execution results.
You should refrain from directly writing code.
Begin by thoroughly examining the existing code and its functionality.
Analyze the @@Execution Result obtained from running the @@Existing Code. Identify any errors, unexpected behavior, or deviations from the expected output.
Consider potential edge cases, optimization opportunities, or alternative approaches based on insights from the @@Execution Result.
Offer guidance in a clear and understandable manner, explaining the rationale behind each suggestion.
Refrain from providing actual code solutions, but instead focus on conceptual modifications or strategies.
Provide constructive feedback to help the programmer improve their coding skills.
Remember, your role is to simulate human-like guidance and expertise in programming without directly implementing solutions.
Please respond in no more than three sentences.

@@Problem
{}

@@Existing Code
{}

@@Execution Result
{}

@@Guidance
""".format(problem.strip(), current_code, execution_feedback)
    return prompt


def generate_multi_round(problem, expected_output, example, lang, tokenizer, model,name,flags):
    pre_messages=[]
    if flags.dataset=="humaneval":
        prompt = humaneval_build_instruction(lang, example['prompt'])
    elif flags.dataset=="mbpp":
        prompt = mbpp_build_deepseekcoder_instruction.strip().format(example['prompt'],"python","python")
    pre_messages.append({"role":"user","content":prompt})

    inputs = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': prompt}],
        return_tensors="pt"
    ).to(model.device)
    stop_id = tokenizer.convert_tokens_to_ids("<|EOT|>")
    assert isinstance(stop_id, int), "Invalid tokenizer, EOT id not found"
    max_new_tokens=1024
    logging.info(f"max_new_tokens{max_new_tokens}")
    outputs = model.generate(
        inputs, 
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        temperature=0,
    )
    output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
    canonical_solution = example["canonical_solution"]
    solution = {k:v for k,v in example.items()}
    solution["solution"]=output
    sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)
    attempt = 1
    judge = False
    modify = False
    code = sanitized_solution["solution"]
    while attempt==1 or sanitized_solution["solution"]!="":
        pre_messages.append({"role":"assistant","content":solution["solution"]})
        args = (
            flags.dataset,
            0,
            problem,
            sanitized_solution["solution"],
            expected_output,
            flags.version,
            True,  # fast_check
            example["task_id"]+f'_{attempt}',
            flags.min_time_limit,
            flags.gt_time_limit_factor,
        )
        result = check_correctness(*args)
        if flags.version=="base" and result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        elif flags.version=="plus" and result["plus"][0]==result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        else:
            attempt += 1    
            if attempt > MAX_TRY:
                code = sanitized_solution["solution"]
                break
            execution_feedback=""
            if flags.version=="base":
                execution_feedback=result["base"][2]
            elif flags.version=="plus":
                if result["base"][0]!=SUCCESS:
                    execution_feedback+=result["base"][2]
                    if "The results aren't as expected." in execution_feedback:
                        if result["plus"][0]!=SUCCESS:
                            execution_feedback+="\n"+result["plus"][2]
                else:
                    execution_feedback=result["plus"][2]
            gpt_messages=[{"role":"system","content":"You are a helpful assistant."}]
            gpt_messages.append({"role":"user","content":build_gpt_prompt(\
                pre_messages, example['prompt'], sanitized_solution["solution"], execution_feedback)})
            gpt_feedback=None
            trytime=0
            while gpt_feedback is None and trytime<5:
                gpt_feedback=gpt_predict(gpt_messages)
                trytime+=1
            if gpt_feedback==None:
                raise BaseException("Please resume.")
            if prompt.endswith("@@ Response"):
                prompt +="""
{}

@@ Instruction
{}
""".format(solution["solution"],gpt_feedback)
            else:
                prompt +="""

@@ Response
{}

@@ Instruction
{}
""".format(solution["solution"],gpt_feedback)        
            pre_messages.append({"role":"user","content":gpt_feedback})
            inputs = tokenizer.apply_chat_template(
                [{'role': 'user', 'content': prompt }],
                return_tensors="pt"
            ).to(model.device)

            outputs = model.generate(
                inputs, 
                max_new_tokens=max_new_tokens,#待定，evalplus论文说除了gpt用的1024，其他都用的512
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                temperature=0,
            )
            output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
            solution = {k:v for k,v in example.items()}
            solution["solution"]=output 
            sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)

    return code,judge,modify


def gen_solution(args):
    a,b = 0,0
    total_modify = 0
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    fail_list=[]
    model_path = args.model
    logging.info(f"model:{model_path}")
    model_name =model_path.replace("/", "_")
    lang = "python"
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    output_file = os.path.join(args.output_path,model_name,f"multiround_{args.dataset}_{args.version}_solutions-sanitized.jsonl")
    if not args.resume:
        if os.path.exists(output_file):
            logging.info(f"Old sample jsonl file exists, remove it. {output_file}")
            os.remove(output_file)
    else:
        existing_task_ids = set()
        if os.path.exists(output_file):
            with open(output_file, 'r') as file:
                for line in file:
                    data = json.loads(line)
                    if 'task_id' in data:
                        existing_task_ids.add(data['task_id'])
                        a=data["pass_num"]
                        total_modify=data["total_modify"]
                        b=data["total_num"]-a
                        fail_list=data["fail_list"]

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    logging.info("load tokenizer {} from {} over.".format(tokenizer.__class__, model_path))
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()

    modelname=model_path.replace("/", "_")
    if args.dataset=="humaneval":
        problems = get_human_eval_plus()
        examples = problems.items()
        dataset_hash = get_human_eval_plus_hash()
        expected_outputs = get_groundtruth(problems, dataset_hash, [])
    else:
        problems = get_mbpp_plus()
        examples = problems.items()
        dataset_hash = get_mbpp_plus_hash()
        expected_outputs = get_groundtruth(
                problems,
                dataset_hash,
                MBPP_OUTPUT_NOT_NONE_TASKS,
            )
    logging.info("Read {} examples for evaluation over.".format(len(examples)))
    for task_id,example in tqdm(examples, desc='Generating'):
        if args.resume:
            if task_id in existing_task_ids:
                continue
        problem = problems[task_id]
        expected_output = expected_outputs[task_id]
        code,judge,modify = generate_multi_round(problem,expected_output,example, lang, tokenizer, model, modelname,args)
        if modify:
            total_modify += 1
        if judge:
            a += 1
        else:
            b += 1
            fail_list.append(task_id)
        result = a/(a+b)
        single_result = (a-total_modify)/(a+b)
        print ("pass num ",a)
        print ("total num",a+b)
        print ("judge: ",judge)
        print ('modify: '+str(modify))
        print ("num modify: "+str(total_modify))
        print ("fail list: ",fail_list)
        print ('multisound rate: '+str(result))
        print ('singlesound rate: '+str(single_result))
        gen_sample=[dict(task_id=task_id, solution=code, pass_num=a, total_modify=total_modify, total_num=a+b, fail_list=fail_list)]
        write_jsonl(output_file, gen_sample ,append=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, help="model path")
    parser.add_argument('--output_path', type=str, help="output path", default="./multiround_output")
    parser.add_argument('--log_file', type=str, help="log file name", default="gen_humaneval_plus_solution_singleround.log")
    parser.add_argument("--min-time-limit", default=1, type=float)
    parser.add_argument("--gt-time-limit-factor", default=4.0, type=float)
    parser.add_argument(
        "--version", required=True, type=str, choices=["base", "plus"]
    )
    parser.add_argument(
        "--dataset", required=True, type=str, choices=["humaneval", "mbpp"]
    )
    parser.add_argument('--resume', action="store_true")

    args = parser.parse_args()
    args.eofs=None

    model_name = args.model.replace("/", "_")
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    logfile=os.path.join(args.output_path,model_name,args.log_file)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler.setFormatter(formatter)  
    logging.getLogger().addHandler(file_handler)

    gen_solution(args)

# === NexusCore/openenv\Lib\site-packages\PIL\ImageColor.py ===
#
# The Python Imaging Library
# $Id$
#
# map CSS3-style colour description strings to RGB
#
# History:
# 2002-10-24 fl   Added support for CSS-style color strings
# 2002-12-15 fl   Added RGBA support
# 2004-03-27 fl   Fixed remaining int() problems for Python 1.5.2
# 2004-07-19 fl   Fixed gray/grey spelling issues
# 2009-03-05 fl   Fixed rounding error in grayscale calculation
#
# Copyright (c) 2002-2004 by Secret Labs AB
# Copyright (c) 2002-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import re
from functools import lru_cache

from . import Image


@lru_cache
def getrgb(color: str) -> tuple[int, int, int] | tuple[int, int, int, int]:
    """
     Convert a color string to an RGB or RGBA tuple. If the string cannot be
     parsed, this function raises a :py:exc:`ValueError` exception.

    .. versionadded:: 1.1.4

    :param color: A color string
    :return: ``(red, green, blue[, alpha])``
    """
    if len(color) > 100:
        msg = "color specifier is too long"
        raise ValueError(msg)
    color = color.lower()

    rgb = colormap.get(color, None)
    if rgb:
        if isinstance(rgb, tuple):
            return rgb
        rgb_tuple = getrgb(rgb)
        assert len(rgb_tuple) == 3
        colormap[color] = rgb_tuple
        return rgb_tuple

    # check for known string formats
    if re.match("#[a-f0-9]{3}$", color):
        return int(color[1] * 2, 16), int(color[2] * 2, 16), int(color[3] * 2, 16)

    if re.match("#[a-f0-9]{4}$", color):
        return (
            int(color[1] * 2, 16),
            int(color[2] * 2, 16),
            int(color[3] * 2, 16),
            int(color[4] * 2, 16),
        )

    if re.match("#[a-f0-9]{6}$", color):
        return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    if re.match("#[a-f0-9]{8}$", color):
        return (
            int(color[1:3], 16),
            int(color[3:5], 16),
            int(color[5:7], 16),
            int(color[7:9], 16),
        )

    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    m = re.match(r"rgb\(\s*(\d+)%\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)$", color)
    if m:
        return (
            int((int(m.group(1)) * 255) / 100.0 + 0.5),
            int((int(m.group(2)) * 255) / 100.0 + 0.5),
            int((int(m.group(3)) * 255) / 100.0 + 0.5),
        )

    m = re.match(
        r"hsl\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)%\s*,\s*(\d+\.?\d*)%\s*\)$", color
    )
    if m:
        from colorsys import hls_to_rgb

        rgb_floats = hls_to_rgb(
            float(m.group(1)) / 360.0,
            float(m.group(3)) / 100.0,
            float(m.group(2)) / 100.0,
        )
        return (
            int(rgb_floats[0] * 255 + 0.5),
            int(rgb_floats[1] * 255 + 0.5),
            int(rgb_floats[2] * 255 + 0.5),
        )

    m = re.match(
        r"hs[bv]\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)%\s*,\s*(\d+\.?\d*)%\s*\)$", color
    )
    if m:
        from colorsys import hsv_to_rgb

        rgb_floats = hsv_to_rgb(
            float(m.group(1)) / 360.0,
            float(m.group(2)) / 100.0,
            float(m.group(3)) / 100.0,
        )
        return (
            int(rgb_floats[0] * 255 + 0.5),
            int(rgb_floats[1] * 255 + 0.5),
            int(rgb_floats[2] * 255 + 0.5),
        )

    m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    msg = f"unknown color specifier: {repr(color)}"
    raise ValueError(msg)


@lru_cache
def getcolor(color: str, mode: str) -> int | tuple[int, ...]:
    """
    Same as :py:func:`~PIL.ImageColor.getrgb` for most modes. However, if
    ``mode`` is HSV, converts the RGB value to a HSV value, or if ``mode`` is
    not color or a palette image, converts the RGB value to a grayscale value.
    If the string cannot be parsed, this function raises a :py:exc:`ValueError`
    exception.

    .. versionadded:: 1.1.4

    :param color: A color string
    :param mode: Convert result to this mode
    :return: ``graylevel, (graylevel, alpha) or (red, green, blue[, alpha])``
    """
    # same as getrgb, but converts the result to the given mode
    rgb, alpha = getrgb(color), 255
    if len(rgb) == 4:
        alpha = rgb[3]
        rgb = rgb[:3]

    if mode == "HSV":
        from colorsys import rgb_to_hsv

        r, g, b = rgb
        h, s, v = rgb_to_hsv(r / 255, g / 255, b / 255)
        return int(h * 255), int(s * 255), int(v * 255)
    elif Image.getmodebase(mode) == "L":
        r, g, b = rgb
        # ITU-R Recommendation 601-2 for nonlinear RGB
        # scaled to 24 bits to match the convert's implementation.
        graylevel = (r * 19595 + g * 38470 + b * 7471 + 0x8000) >> 16
        if mode[-1] == "A":
            return graylevel, alpha
        return graylevel
    elif mode[-1] == "A":
        return rgb + (alpha,)
    return rgb


colormap: dict[str, str | tuple[int, int, int]] = {
    # X11 colour table from https://drafts.csswg.org/css-color-4/, with
    # gray/grey spelling issues fixed.  This is a superset of HTML 4.0
    # colour names used in CSS 1.
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgreen": "#90ee90",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}

# === NexusCore/openenv\Lib\site-packages\PIL\WebPImagePlugin.py ===
from __future__ import annotations

from io import BytesIO
from typing import IO, Any

from . import Image, ImageFile

try:
    from . import _webp

    SUPPORTED = True
except ImportError:
    SUPPORTED = False


_VP8_MODES_BY_IDENTIFIER = {
    b"VP8 ": "RGB",
    b"VP8X": "RGBA",
    b"VP8L": "RGBA",  # lossless
}


def _accept(prefix: bytes) -> bool | str:
    is_riff_file_format = prefix.startswith(b"RIFF")
    is_webp_file = prefix[8:12] == b"WEBP"
    is_valid_vp8_mode = prefix[12:16] in _VP8_MODES_BY_IDENTIFIER

    if is_riff_file_format and is_webp_file and is_valid_vp8_mode:
        if not SUPPORTED:
            return (
                "image file could not be identified because WEBP support not installed"
            )
        return True
    return False


class WebPImageFile(ImageFile.ImageFile):
    format = "WEBP"
    format_description = "WebP image"
    __loaded = 0
    __logical_frame = 0

    def _open(self) -> None:
        # Use the newer AnimDecoder API to parse the (possibly) animated file,
        # and access muxed chunks like ICC/EXIF/XMP.
        self._decoder = _webp.WebPAnimDecoder(self.fp.read())

        # Get info from decoder
        self._size, loop_count, bgcolor, frame_count, mode = self._decoder.get_info()
        self.info["loop"] = loop_count
        bg_a, bg_r, bg_g, bg_b = (
            (bgcolor >> 24) & 0xFF,
            (bgcolor >> 16) & 0xFF,
            (bgcolor >> 8) & 0xFF,
            bgcolor & 0xFF,
        )
        self.info["background"] = (bg_r, bg_g, bg_b, bg_a)
        self.n_frames = frame_count
        self.is_animated = self.n_frames > 1
        self._mode = "RGB" if mode == "RGBX" else mode
        self.rawmode = mode

        # Attempt to read ICC / EXIF / XMP chunks from file
        icc_profile = self._decoder.get_chunk("ICCP")
        exif = self._decoder.get_chunk("EXIF")
        xmp = self._decoder.get_chunk("XMP ")
        if icc_profile:
            self.info["icc_profile"] = icc_profile
        if exif:
            self.info["exif"] = exif
        if xmp:
            self.info["xmp"] = xmp

        # Initialize seek state
        self._reset(reset=False)

    def _getexif(self) -> dict[int, Any] | None:
        if "exif" not in self.info:
            return None
        return self.getexif()._get_merged_dict()

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return

        # Set logical frame to requested position
        self.__logical_frame = frame

    def _reset(self, reset: bool = True) -> None:
        if reset:
            self._decoder.reset()
        self.__physical_frame = 0
        self.__loaded = -1
        self.__timestamp = 0

    def _get_next(self) -> tuple[bytes, int, int]:
        # Get next frame
        ret = self._decoder.get_next()
        self.__physical_frame += 1

        # Check if an error occurred
        if ret is None:
            self._reset()  # Reset just to be safe
            self.seek(0)
            msg = "failed to decode next frame in WebP file"
            raise EOFError(msg)

        # Compute duration
        data, timestamp = ret
        duration = timestamp - self.__timestamp
        self.__timestamp = timestamp

        # libwebp gives frame end, adjust to start of frame
        timestamp -= duration
        return data, timestamp, duration

    def _seek(self, frame: int) -> None:
        if self.__physical_frame == frame:
            return  # Nothing to do
        if frame < self.__physical_frame:
            self._reset()  # Rewind to beginning
        while self.__physical_frame < frame:
            self._get_next()  # Advance to the requested frame

    def load(self) -> Image.core.PixelAccess | None:
        if self.__loaded != self.__logical_frame:
            self._seek(self.__logical_frame)

            # We need to load the image data for this frame
            data, timestamp, duration = self._get_next()
            self.info["timestamp"] = timestamp
            self.info["duration"] = duration
            self.__loaded = self.__logical_frame

            # Set tile
            if self.fp and self._exclusive_fp:
                self.fp.close()
            self.fp = BytesIO(data)
            self.tile = [ImageFile._Tile("raw", (0, 0) + self.size, 0, self.rawmode)]

        return super().load()

    def load_seek(self, pos: int) -> None:
        pass

    def tell(self) -> int:
        return self.__logical_frame


def _convert_frame(im: Image.Image) -> Image.Image:
    # Make sure image mode is supported
    if im.mode not in ("RGBX", "RGBA", "RGB"):
        im = im.convert("RGBA" if im.has_transparency_data else "RGB")
    return im


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    encoderinfo = im.encoderinfo.copy()
    append_images = list(encoderinfo.get("append_images", []))

    # If total frame count is 1, then save using the legacy API, which
    # will preserve non-alpha modes
    total = 0
    for ims in [im] + append_images:
        total += getattr(ims, "n_frames", 1)
    if total == 1:
        _save(im, fp, filename)
        return

    background: int | tuple[int, ...] = (0, 0, 0, 0)
    if "background" in encoderinfo:
        background = encoderinfo["background"]
    elif "background" in im.info:
        background = im.info["background"]
        if isinstance(background, int):
            # GifImagePlugin stores a global color table index in
            # info["background"]. So it must be converted to an RGBA value
            palette = im.getpalette()
            if palette:
                r, g, b = palette[background * 3 : (background + 1) * 3]
                background = (r, g, b, 255)
            else:
                background = (background, background, background, 255)

    duration = im.encoderinfo.get("duration", im.info.get("duration", 0))
    loop = im.encoderinfo.get("loop", 0)
    minimize_size = im.encoderinfo.get("minimize_size", False)
    kmin = im.encoderinfo.get("kmin", None)
    kmax = im.encoderinfo.get("kmax", None)
    allow_mixed = im.encoderinfo.get("allow_mixed", False)
    verbose = False
    lossless = im.encoderinfo.get("lossless", False)
    quality = im.encoderinfo.get("quality", 80)
    alpha_quality = im.encoderinfo.get("alpha_quality", 100)
    method = im.encoderinfo.get("method", 0)
    icc_profile = im.encoderinfo.get("icc_profile") or ""
    exif = im.encoderinfo.get("exif", "")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    xmp = im.encoderinfo.get("xmp", "")
    if allow_mixed:
        lossless = False

    # Sensible keyframe defaults are from gif2webp.c script
    if kmin is None:
        kmin = 9 if lossless else 3
    if kmax is None:
        kmax = 17 if lossless else 5

    # Validate background color
    if (
        not isinstance(background, (list, tuple))
        or len(background) != 4
        or not all(0 <= v < 256 for v in background)
    ):
        msg = f"Background color is not an RGBA tuple clamped to (0-255): {background}"
        raise OSError(msg)

    # Convert to packed uint
    bg_r, bg_g, bg_b, bg_a = background
    background = (bg_a << 24) | (bg_r << 16) | (bg_g << 8) | (bg_b << 0)

    # Setup the WebP animation encoder
    enc = _webp.WebPAnimEncoder(
        im.size,
        background,
        loop,
        minimize_size,
        kmin,
        kmax,
        allow_mixed,
        verbose,
    )

    # Add each frame
    frame_idx = 0
    timestamp = 0
    cur_idx = im.tell()
    try:
        for ims in [im] + append_images:
            # Get number of frames in this image
            nfr = getattr(ims, "n_frames", 1)

            for idx in range(nfr):
                ims.seek(idx)

                frame = _convert_frame(ims)

                # Append the frame to the animation encoder
                enc.add(
                    frame.getim(),
                    round(timestamp),
                    lossless,
                    quality,
                    alpha_quality,
                    method,
                )

                # Update timestamp and frame index
                if isinstance(duration, (list, tuple)):
                    timestamp += duration[frame_idx]
                else:
                    timestamp += duration
                frame_idx += 1

    finally:
        im.seek(cur_idx)

    # Force encoder to flush frames
    enc.add(None, round(timestamp), lossless, quality, alpha_quality, 0)

    # Get the final output from the encoder
    data = enc.assemble(icc_profile, exif, xmp)
    if data is None:
        msg = "cannot write file as WebP (encoder returned None)"
        raise OSError(msg)

    fp.write(data)


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    lossless = im.encoderinfo.get("lossless", False)
    quality = im.encoderinfo.get("quality", 80)
    alpha_quality = im.encoderinfo.get("alpha_quality", 100)
    icc_profile = im.encoderinfo.get("icc_profile") or ""
    exif = im.encoderinfo.get("exif", b"")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    if exif.startswith(b"Exif\x00\x00"):
        exif = exif[6:]
    xmp = im.encoderinfo.get("xmp", "")
    method = im.encoderinfo.get("method", 4)
    exact = 1 if im.encoderinfo.get("exact") else 0

    im = _convert_frame(im)

    data = _webp.WebPEncode(
        im.getim(),
        lossless,
        float(quality),
        float(alpha_quality),
        icc_profile,
        method,
        exact,
        exif,
        xmp,
    )
    if data is None:
        msg = "cannot write file as WebP (encoder returned None)"
        raise OSError(msg)

    fp.write(data)


Image.register_open(WebPImageFile.format, WebPImageFile, _accept)
if SUPPORTED:
    Image.register_save(WebPImageFile.format, _save)
    Image.register_save_all(WebPImageFile.format, _save_all)
    Image.register_extension(WebPImageFile.format, ".webp")
    Image.register_mime(WebPImageFile.format, "image/webp")

# === NexusCore/openenv\Lib\site-packages\starlette\requests.py ===
from __future__ import annotations

import json
import typing
from http import cookies as http_cookies

import anyio

from starlette._utils import AwaitableOrContextManager, AwaitableOrContextManagerWrapper
from starlette.datastructures import URL, Address, FormData, Headers, QueryParams, State
from starlette.exceptions import HTTPException
from starlette.formparsers import FormParser, MultiPartException, MultiPartParser
from starlette.types import Message, Receive, Scope, Send

try:
    from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    parse_options_header = None


if typing.TYPE_CHECKING:
    from starlette.routing import Router


SERVER_PUSH_HEADERS_TO_COPY = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "user-agent",
}


def cookie_parser(cookie_string: str) -> dict[str, str]:
    """
    This function parses a ``Cookie`` HTTP header into a dict of key/value pairs.

    It attempts to mimic browser cookie parsing behavior: browsers and web servers
    frequently disregard the spec (RFC 6265) when setting and reading cookies,
    so we attempt to suit the common scenarios here.

    This function has been adapted from Django 3.1.0.
    Note: we are explicitly _NOT_ using `SimpleCookie.load` because it is based
    on an outdated spec and will fail on lots of input we want to support
    """
    cookie_dict: dict[str, str] = {}
    for chunk in cookie_string.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookie_dict[key] = http_cookies._unquote(val)
    return cookie_dict


class ClientDisconnect(Exception):
    pass


class HTTPConnection(typing.Mapping[str, typing.Any]):
    """
    A base class for incoming HTTP connections, that is used to provide
    any functionality that is common to both `Request` and `WebSocket`.
    """

    def __init__(self, scope: Scope, receive: Receive | None = None) -> None:
        assert scope["type"] in ("http", "websocket")
        self.scope = scope

    def __getitem__(self, key: str) -> typing.Any:
        return self.scope[key]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    # Don't use the `abc.Mapping.__eq__` implementation.
    # Connection instances should never be considered equal
    # unless `self is other`.
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def app(self) -> typing.Any:
        return self.scope["app"]

    @property
    def url(self) -> URL:
        if not hasattr(self, "_url"):
            self._url = URL(scope=self.scope)
        return self._url

    @property
    def base_url(self) -> URL:
        if not hasattr(self, "_base_url"):
            base_url_scope = dict(self.scope)
            # This is used by request.url_for, it might be used inside a Mount which
            # would have its own child scope with its own root_path, but the base URL
            # for url_for should still be the top level app root path.
            app_root_path = base_url_scope.get(
                "app_root_path", base_url_scope.get("root_path", "")
            )
            path = app_root_path
            if not path.endswith("/"):
                path += "/"
            base_url_scope["path"] = path
            base_url_scope["query_string"] = b""
            base_url_scope["root_path"] = app_root_path
            self._base_url = URL(scope=base_url_scope)
        return self._base_url

    @property
    def headers(self) -> Headers:
        if not hasattr(self, "_headers"):
            self._headers = Headers(scope=self.scope)
        return self._headers

    @property
    def query_params(self) -> QueryParams:
        if not hasattr(self, "_query_params"):
            self._query_params = QueryParams(self.scope["query_string"])
        return self._query_params

    @property
    def path_params(self) -> dict[str, typing.Any]:
        return self.scope.get("path_params", {})

    @property
    def cookies(self) -> dict[str, str]:
        if not hasattr(self, "_cookies"):
            cookies: dict[str, str] = {}
            cookie_header = self.headers.get("cookie")

            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = cookies
        return self._cookies

    @property
    def client(self) -> Address | None:
        # client is a 2 item tuple of (host, port), None or missing
        host_port = self.scope.get("client")
        if host_port is not None:
            return Address(*host_port)
        return None

    @property
    def session(self) -> dict[str, typing.Any]:
        assert (
            "session" in self.scope
        ), "SessionMiddleware must be installed to access request.session"
        return self.scope["session"]  # type: ignore[no-any-return]

    @property
    def auth(self) -> typing.Any:
        assert (
            "auth" in self.scope
        ), "AuthenticationMiddleware must be installed to access request.auth"
        return self.scope["auth"]

    @property
    def user(self) -> typing.Any:
        assert (
            "user" in self.scope
        ), "AuthenticationMiddleware must be installed to access request.user"
        return self.scope["user"]

    @property
    def state(self) -> State:
        if not hasattr(self, "_state"):
            # Ensure 'state' has an empty dict if it's not already populated.
            self.scope.setdefault("state", {})
            # Create a state instance with a reference to the dict in which it should
            # store info
            self._state = State(self.scope["state"])
        return self._state

    def url_for(self, name: str, /, **path_params: typing.Any) -> URL:
        router: Router = self.scope["router"]
        url_path = router.url_path_for(name, **path_params)
        return url_path.make_absolute_url(base_url=self.base_url)


async def empty_receive() -> typing.NoReturn:
    raise RuntimeError("Receive channel has not been made available")


async def empty_send(message: Message) -> typing.NoReturn:
    raise RuntimeError("Send channel has not been made available")


class Request(HTTPConnection):
    _form: FormData | None

    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        super().__init__(scope)
        assert scope["type"] == "http"
        self._receive = receive
        self._send = send
        self._stream_consumed = False
        self._is_disconnected = False
        self._form = None

    @property
    def method(self) -> str:
        return typing.cast(str, self.scope["method"])

    @property
    def receive(self) -> Receive:
        return self._receive

    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        if hasattr(self, "_body"):
            yield self._body
            yield b""
            return
        if self._stream_consumed:
            raise RuntimeError("Stream consumed")
        while not self._stream_consumed:
            message = await self._receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if not message.get("more_body", False):
                    self._stream_consumed = True
                if body:
                    yield body
            elif message["type"] == "http.disconnect":
                self._is_disconnected = True
                raise ClientDisconnect()
        yield b""

    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            chunks: list[bytes] = []
            async for chunk in self.stream():
                chunks.append(chunk)
            self._body = b"".join(chunks)
        return self._body

    async def json(self) -> typing.Any:
        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = json.loads(body)
        return self._json

    async def _get_form(
        self, *, max_files: int | float = 1000, max_fields: int | float = 1000
    ) -> FormData:
        if self._form is None:
            assert (
                parse_options_header is not None
            ), "The `python-multipart` library must be installed to use form parsing."
            content_type_header = self.headers.get("Content-Type")
            content_type: bytes
            content_type, _ = parse_options_header(content_type_header)
            if content_type == b"multipart/form-data":
                try:
                    multipart_parser = MultiPartParser(
                        self.headers,
                        self.stream(),
                        max_files=max_files,
                        max_fields=max_fields,
                    )
                    self._form = await multipart_parser.parse()
                except MultiPartException as exc:
                    if "app" in self.scope:
                        raise HTTPException(status_code=400, detail=exc.message)
                    raise exc
            elif content_type == b"application/x-www-form-urlencoded":
                form_parser = FormParser(self.headers, self.stream())
                self._form = await form_parser.parse()
            else:
                self._form = FormData()
        return self._form

    def form(
        self, *, max_files: int | float = 1000, max_fields: int | float = 1000
    ) -> AwaitableOrContextManager[FormData]:
        return AwaitableOrContextManagerWrapper(
            self._get_form(max_files=max_files, max_fields=max_fields)
        )

    async def close(self) -> None:
        if self._form is not None:
            await self._form.close()

    async def is_disconnected(self) -> bool:
        if not self._is_disconnected:
            message: Message = {}

            # If message isn't immediately available, move on
            with anyio.CancelScope() as cs:
                cs.cancel()
                message = await self._receive()

            if message.get("type") == "http.disconnect":
                self._is_disconnected = True

        return self._is_disconnected

    async def send_push_promise(self, path: str) -> None:
        if "http.response.push" in self.scope.get("extensions", {}):
            raw_headers: list[tuple[bytes, bytes]] = []
            for name in SERVER_PUSH_HEADERS_TO_COPY:
                for value in self.headers.getlist(name):
                    raw_headers.append(
                        (name.encode("latin-1"), value.encode("latin-1"))
                    )
            await self._send(
                {"type": "http.response.push", "path": path, "headers": raw_headers}
            )

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_p_o_s_t.py ===
from fontTools import ttLib
from fontTools.ttLib.standardGlyphOrder import standardGlyphOrder
from fontTools.misc import sstruct
from fontTools.misc.textTools import bytechr, byteord, tobytes, tostr, safeEval, readHex
from . import DefaultTable
import sys
import struct
import array
import logging

log = logging.getLogger(__name__)

postFormat = """
	>
	formatType:			16.16F
	italicAngle:		16.16F		# italic angle in degrees
	underlinePosition:	h
	underlineThickness:	h
	isFixedPitch:		L
	minMemType42:		L			# minimum memory if TrueType font is downloaded
	maxMemType42:		L			# maximum memory if TrueType font is downloaded
	minMemType1:		L			# minimum memory if Type1 font is downloaded
	maxMemType1:		L			# maximum memory if Type1 font is downloaded
"""

postFormatSize = sstruct.calcsize(postFormat)


class table__p_o_s_t(DefaultTable.DefaultTable):
    """PostScript table

    The ``post`` table contains information needed to use the font on
    PostScript printers, including the PostScript names of glyphs and
    data that was stored in the ``FontInfo`` dictionary for Type 1 fonts.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/post
    """

    def decompile(self, data, ttFont):
        sstruct.unpack(postFormat, data[:postFormatSize], self)
        data = data[postFormatSize:]
        if self.formatType == 1.0:
            self.decode_format_1_0(data, ttFont)
        elif self.formatType == 2.0:
            self.decode_format_2_0(data, ttFont)
        elif self.formatType == 3.0:
            self.decode_format_3_0(data, ttFont)
        elif self.formatType == 4.0:
            self.decode_format_4_0(data, ttFont)
        else:
            # supported format
            raise ttLib.TTLibError(
                "'post' table format %f not supported" % self.formatType
            )

    def compile(self, ttFont):
        data = sstruct.pack(postFormat, self)
        if self.formatType == 1.0:
            pass  # we're done
        elif self.formatType == 2.0:
            data = data + self.encode_format_2_0(ttFont)
        elif self.formatType == 3.0:
            pass  # we're done
        elif self.formatType == 4.0:
            data = data + self.encode_format_4_0(ttFont)
        else:
            # supported format
            raise ttLib.TTLibError(
                "'post' table format %f not supported" % self.formatType
            )
        return data

    def getGlyphOrder(self):
        """This function will get called by a ttLib.TTFont instance.
        Do not call this function yourself, use TTFont().getGlyphOrder()
        or its relatives instead!
        """
        if not hasattr(self, "glyphOrder"):
            raise ttLib.TTLibError("illegal use of getGlyphOrder()")
        glyphOrder = self.glyphOrder
        del self.glyphOrder
        return glyphOrder

    def decode_format_1_0(self, data, ttFont):
        self.glyphOrder = standardGlyphOrder[: ttFont["maxp"].numGlyphs]

    def decode_format_2_0(self, data, ttFont):
        (numGlyphs,) = struct.unpack(">H", data[:2])
        numGlyphs = int(numGlyphs)
        if numGlyphs > ttFont["maxp"].numGlyphs:
            # Assume the numGlyphs field is bogus, so sync with maxp.
            # I've seen this in one font, and if the assumption is
            # wrong elsewhere, well, so be it: it's hard enough to
            # work around _one_ non-conforming post format...
            numGlyphs = ttFont["maxp"].numGlyphs
        data = data[2:]
        indices = array.array("H")
        indices.frombytes(data[: 2 * numGlyphs])
        if sys.byteorder != "big":
            indices.byteswap()
        data = data[2 * numGlyphs :]
        maxIndex = max(indices)
        self.extraNames = extraNames = unpackPStrings(data, maxIndex - 257)
        self.glyphOrder = glyphOrder = [""] * int(ttFont["maxp"].numGlyphs)
        for glyphID in range(numGlyphs):
            index = indices[glyphID]
            if index > 257:
                try:
                    name = extraNames[index - 258]
                except IndexError:
                    name = ""
            else:
                # fetch names from standard list
                name = standardGlyphOrder[index]
            glyphOrder[glyphID] = name
        self.build_psNameMapping(ttFont)

    def build_psNameMapping(self, ttFont):
        mapping = {}
        allNames = {}
        for i in range(ttFont["maxp"].numGlyphs):
            glyphName = psName = self.glyphOrder[i]
            if glyphName == "":
                glyphName = "glyph%.5d" % i

            if glyphName in allNames:
                # make up a new glyphName that's unique
                n = allNames[glyphName]
                # check if the exists in any of the seen names or later ones
                names = set(allNames.keys()) | set(self.glyphOrder)
                while (glyphName + "." + str(n)) in names:
                    n += 1
                allNames[glyphName] = n + 1
                glyphName = glyphName + "." + str(n)

            self.glyphOrder[i] = glyphName
            allNames[glyphName] = 1
            if glyphName != psName:
                mapping[glyphName] = psName

        self.mapping = mapping

    def decode_format_3_0(self, data, ttFont):
        # Setting self.glyphOrder to None will cause the TTFont object
        # try and construct glyph names from a Unicode cmap table.
        self.glyphOrder = None

    def decode_format_4_0(self, data, ttFont):
        from fontTools import agl

        numGlyphs = ttFont["maxp"].numGlyphs
        indices = array.array("H")
        indices.frombytes(data)
        if sys.byteorder != "big":
            indices.byteswap()
        # In some older fonts, the size of the post table doesn't match
        # the number of glyphs. Sometimes it's bigger, sometimes smaller.
        self.glyphOrder = glyphOrder = [""] * int(numGlyphs)
        for i in range(min(len(indices), numGlyphs)):
            if indices[i] == 0xFFFF:
                self.glyphOrder[i] = ""
            elif indices[i] in agl.UV2AGL:
                self.glyphOrder[i] = agl.UV2AGL[indices[i]]
            else:
                self.glyphOrder[i] = "uni%04X" % indices[i]
        self.build_psNameMapping(ttFont)

    def encode_format_2_0(self, ttFont):
        numGlyphs = ttFont["maxp"].numGlyphs
        glyphOrder = ttFont.getGlyphOrder()
        assert len(glyphOrder) == numGlyphs
        indices = array.array("H")
        extraDict = {}
        extraNames = self.extraNames = [
            n for n in self.extraNames if n not in standardGlyphOrder
        ]
        for i in range(len(extraNames)):
            extraDict[extraNames[i]] = i
        for glyphID in range(numGlyphs):
            glyphName = glyphOrder[glyphID]
            if glyphName in self.mapping:
                psName = self.mapping[glyphName]
            else:
                psName = glyphName
            if psName in extraDict:
                index = 258 + extraDict[psName]
            elif psName in standardGlyphOrder:
                index = standardGlyphOrder.index(psName)
            else:
                index = 258 + len(extraNames)
                extraDict[psName] = len(extraNames)
                extraNames.append(psName)
            indices.append(index)
        if sys.byteorder != "big":
            indices.byteswap()
        return (
            struct.pack(">H", numGlyphs) + indices.tobytes() + packPStrings(extraNames)
        )

    def encode_format_4_0(self, ttFont):
        from fontTools import agl

        numGlyphs = ttFont["maxp"].numGlyphs
        glyphOrder = ttFont.getGlyphOrder()
        assert len(glyphOrder) == numGlyphs
        indices = array.array("H")
        for glyphID in glyphOrder:
            glyphID = glyphID.split("#")[0]
            if glyphID in agl.AGL2UV:
                indices.append(agl.AGL2UV[glyphID])
            elif len(glyphID) == 7 and glyphID[:3] == "uni":
                indices.append(int(glyphID[3:], 16))
            else:
                indices.append(0xFFFF)
        if sys.byteorder != "big":
            indices.byteswap()
        return indices.tobytes()

    def toXML(self, writer, ttFont):
        formatstring, names, fixes = sstruct.getformat(postFormat)
        for name in names:
            value = getattr(self, name)
            writer.simpletag(name, value=value)
            writer.newline()
        if hasattr(self, "mapping"):
            writer.begintag("psNames")
            writer.newline()
            writer.comment(
                "This file uses unique glyph names based on the information\n"
                "found in the 'post' table. Since these names might not be unique,\n"
                "we have to invent artificial names in case of clashes. In order to\n"
                "be able to retain the original information, we need a name to\n"
                "ps name mapping for those cases where they differ. That's what\n"
                "you see below.\n"
            )
            writer.newline()
            items = sorted(self.mapping.items())
            for name, psName in items:
                writer.simpletag("psName", name=name, psName=psName)
                writer.newline()
            writer.endtag("psNames")
            writer.newline()
        if hasattr(self, "extraNames"):
            writer.begintag("extraNames")
            writer.newline()
            writer.comment(
                "following are the name that are not taken from the standard Mac glyph order"
            )
            writer.newline()
            for name in self.extraNames:
                writer.simpletag("psName", name=name)
                writer.newline()
            writer.endtag("extraNames")
            writer.newline()
        if hasattr(self, "data"):
            writer.begintag("hexdata")
            writer.newline()
            writer.dumphex(self.data)
            writer.endtag("hexdata")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name not in ("psNames", "extraNames", "hexdata"):
            setattr(self, name, safeEval(attrs["value"]))
        elif name == "psNames":
            self.mapping = {}
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name == "psName":
                    self.mapping[attrs["name"]] = attrs["psName"]
        elif name == "extraNames":
            self.extraNames = []
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name == "psName":
                    self.extraNames.append(attrs["name"])
        else:
            self.data = readHex(content)


def unpackPStrings(data, n):
    # extract n Pascal strings from data.
    # if there is not enough data, use ""

    strings = []
    index = 0
    dataLen = len(data)

    for _ in range(n):
        if dataLen <= index:
            length = 0
        else:
            length = byteord(data[index])
        index += 1

        if dataLen <= index + length - 1:
            name = ""
        else:
            name = tostr(data[index : index + length], encoding="latin1")
        strings.append(name)
        index += length

    if index < dataLen:
        log.warning("%d extra bytes in post.stringData array", dataLen - index)

    elif dataLen < index:
        log.warning("not enough data in post.stringData array")

    return strings


def packPStrings(strings):
    data = b""
    for s in strings:
        data = data + bytechr(len(s)) + tobytes(s, encoding="latin1")
    return data

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, operations_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version
from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model, model_service
from google.ai.generativelanguage_v1beta.types import tuned_model

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class ModelServiceTransport(abc.ABC):
    """Abstract transport class for ModelService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
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
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.get_model: gapic_v1.method.wrap_method(
                self.get_model,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method.wrap_method(
                self.list_models,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.get_tuned_model: gapic_v1.method.wrap_method(
                self.get_tuned_model,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_tuned_models: gapic_v1.method.wrap_method(
                self.list_tuned_models,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.create_tuned_model: gapic_v1.method.wrap_method(
                self.create_tuned_model,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.update_tuned_model: gapic_v1.method.wrap_method(
                self.update_tuned_model,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.delete_tuned_model: gapic_v1.method.wrap_method(
                self.delete_tuned_model,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def operations_client(self):
        """Return the client designed to process long-running operations."""
        raise NotImplementedError()

    @property
    def get_model(
        self,
    ) -> Callable[
        [model_service.GetModelRequest], Union[model.Model, Awaitable[model.Model]]
    ]:
        raise NotImplementedError()

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest],
        Union[
            model_service.ListModelsResponse,
            Awaitable[model_service.ListModelsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_tuned_model(
        self,
    ) -> Callable[
        [model_service.GetTunedModelRequest],
        Union[tuned_model.TunedModel, Awaitable[tuned_model.TunedModel]],
    ]:
        raise NotImplementedError()

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest],
        Union[
            model_service.ListTunedModelsResponse,
            Awaitable[model_service.ListTunedModelsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def create_tuned_model(
        self,
    ) -> Callable[
        [model_service.CreateTunedModelRequest],
        Union[operations_pb2.Operation, Awaitable[operations_pb2.Operation]],
    ]:
        raise NotImplementedError()

    @property
    def update_tuned_model(
        self,
    ) -> Callable[
        [model_service.UpdateTunedModelRequest],
        Union[gag_tuned_model.TunedModel, Awaitable[gag_tuned_model.TunedModel]],
    ]:
        raise NotImplementedError()

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[
        [model_service.DeleteTunedModelRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("ModelServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\win32com\test\testall.py ===
import getopt
import os
import re
import sys
import traceback
import unittest

try:
    this_file = __file__
except NameError:
    this_file = sys.argv[0]

win32com_src_dir = os.path.abspath(os.path.join(this_file, "../.."))

import win32com

# We'd prefer the win32com namespace to be the parent of __file__ - ie, our source-tree,
# rather than the version installed - otherwise every .py change needs a full install to
# test!
# We can't patch win32comext as most of them have a .pyd in their root :(
# This clearly ins't ideal or perfect :)
win32com.__path__[0] = win32com_src_dir

import pythoncom
import win32com.client
from pywin32_testutil import TestLoader, TestRunner
from win32com.test.util import (
    CapturingFunctionTestCase,
    CheckClean,
    RegisterPythonServer,
    ShellTestCase,
    TestCase,
)

verbosity = 1  # default unittest verbosity.


def GenerateAndRunOldStyle():
    from . import GenTestScripts

    GenTestScripts.GenerateAll()
    try:
        pass  #
    finally:
        GenTestScripts.CleanAll()


def CleanGenerated():
    import shutil

    import win32com

    if os.path.isdir(win32com.__gen_path__):
        if verbosity > 1:
            print("Deleting files from %s" % (win32com.__gen_path__))
        shutil.rmtree(win32com.__gen_path__)
    import win32com.client.gencache

    win32com.client.gencache.__init__()  # Reset


def RemoveRefCountOutput(data):
    while 1:
        last_line_pos = data.rfind("\n")
        if not re.match(r"\[\d+ refs\]", data[last_line_pos + 1 :]):
            break
        if last_line_pos < 0:
            # All the output
            return ""
        data = data[:last_line_pos]

    return data


def ExecuteSilentlyIfOK(cmd, testcase):
    f = os.popen(cmd)
    data = f.read().strip()
    rc = f.close()
    if rc:
        print(data)
        testcase.fail("Executing '%s' failed (%d)" % (cmd, rc))
    # for "_d" builds, strip the '[xxx refs]' line
    return RemoveRefCountOutput(data)


class PyCOMTest(TestCase):
    no_leak_tests = True  # done by the test itself

    def testit(self):
        # Check that the item is registered, so we get the correct
        # 'skipped' behaviour (and recorded as such) rather than either
        # error or silence due to non-registration.
        RegisterPythonServer(
            os.path.join(
                os.path.dirname(__file__), "..", "servers", "test_pycomtest.py"
            ),
            "Python.Test.PyCOMTest",
        )

        # Execute testPyComTest in its own process so it can play
        # with the Python thread state
        fname = os.path.join(os.path.dirname(this_file), "testPyComTest.py")
        cmd = f'{sys.executable} "{fname}" -q 2>&1'
        data = ExecuteSilentlyIfOK(cmd, self)


class PippoTest(TestCase):
    def testit(self):
        # Check we are registered before spawning the process.
        from win32com.test import pippo_server

        RegisterPythonServer(pippo_server.__file__, "Python.Test.Pippo")

        python = sys.executable
        fname = os.path.join(os.path.dirname(this_file), "testPippo.py")
        cmd = f'{python} "{fname}" 2>&1'
        ExecuteSilentlyIfOK(cmd, self)


# This is a list of "win32com.test.???" module names, optionally with a
# function in that module if the module isn't unitest based...
unittest_modules = [
    # Level 1 tests - fast and few dependencies - good for CI!
    """testIterators testvbscript_regexp testStorage
          testStreams testWMI policySemantics testShell testROT
          testxslt testCollections
          errorSemantics.test testArrays
          testClipboard
          testConversionErrors
        """.split(),
    # Level 2 tests - wants our demo COM objects registered.
    # (these are strange; on github CI they get further than expected when
    # our objects are not installed, so fail to quietly fail with "can't
    # register" like they do locally. So really just a nod to CI)
    """
        testAXScript testDictionary testServers testvb testMarshal
        """.split(),
    # Level 3 tests - Requires Office or other non-free stuff.
    """testMSOffice.TestAll testMSOfficeEvents.test testAccess.test
           testExplorer.TestAll testExchange.test
        """.split(),
    # Level 4 tests - we try and run `makepy` over every typelib installed!
    """testmakepy.TestAll
        """.split(),
]

# A list of other unittest modules we use - these are fully qualified module
# names and the module is assumed to be unittest based.
unittest_other_modules = [
    # Level 1 tests.
    """win32com.directsound.test.ds_test
        """.split(),
    # Level 2 tests.
    [],
    # Level 3 tests.
    [],
    # Level 4 tests.
    [],
]


output_checked_programs = [
    # Level 1 tests.
    [],
    # Level 2 tests.
    [
        ("cscript.exe /nologo //E:vbscript testInterp.vbs", "VBScript test worked OK"),
        (
            "cscript.exe /nologo //E:vbscript testDictionary.vbs",
            "VBScript has successfully tested Python.Dictionary",
        ),
    ],
    # Level 3 tests
    [],
    # Level 4 tests.
    [],
]

custom_test_cases = [
    # Level 1 tests.
    [],
    # Level 2 tests.
    [
        PyCOMTest,
        PippoTest,
    ],
    # Level 3 tests
    [],
    # Level 4 tests.
    [],
]


def get_test_mod_and_func(test_name, import_failures):
    if test_name.find(".") > 0:
        mod_name, func_name = test_name.split(".")
    else:
        mod_name = test_name
        func_name = None
    fq_mod_name = "win32com.test." + mod_name
    try:
        __import__(fq_mod_name)
        mod = sys.modules[fq_mod_name]
    except:
        import_failures.append((mod_name, sys.exc_info()[:2]))
        return None, None
    func = None if func_name is None else getattr(mod, func_name)
    return mod, func


# Return a test suite all loaded with the tests we want to run
def make_test_suite(test_level=1):
    suite = unittest.TestSuite()
    import_failures = []
    loader = TestLoader()
    for i in range(testLevel):
        for mod_name in unittest_modules[i]:
            mod, func = get_test_mod_and_func(mod_name, import_failures)
            if mod is None:
                raise ModuleNotFoundError(f"no such module '{mod_name}'")
            if func is not None:
                test = CapturingFunctionTestCase(func, description=mod_name)
            else:
                if hasattr(mod, "suite"):
                    test = mod.suite()
                else:
                    test = loader.loadTestsFromModule(mod)
            assert test.countTestCases() > 0, f"No tests loaded from {mod!r}"
            suite.addTest(test)
        for cmd, output in output_checked_programs[i]:
            suite.addTest(ShellTestCase(cmd, output))

        for test_class in custom_test_cases[i]:
            suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(test_class))
    # other "normal" unittest modules.
    for i in range(testLevel):
        for mod_name in unittest_other_modules[i]:
            try:
                __import__(mod_name)
            except:
                import_failures.append((mod_name, sys.exc_info()[:2]))
                continue

            mod = sys.modules[mod_name]
            if hasattr(mod, "suite"):
                test = mod.suite()
            else:
                test = loader.loadTestsFromModule(mod)
            assert test.countTestCases() > 0, f"No tests loaded from {mod!r}"
            suite.addTest(test)

    return suite, import_failures


def usage(why):
    print(why)
    print()
    print("win32com test suite")
    print("usage: testall [-v] test_level")
    print("  where test_level is an integer 1-3.  Level 1 tests are quick,")
    print("  level 2 tests invoke Word, IE etc, level 3 take ages!")
    sys.exit(1)


if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v")
    except getopt.error as why:
        usage(why)
    for opt, val in opts:
        if opt == "-v":
            verbosity += 1
    testLevel = 2  # default to quick test with local objects
    test_names = []
    for arg in args:
        try:
            testLevel = int(arg)
            if testLevel < 0 or testLevel > 4:
                raise ValueError("Only levels 1-4 are supported")
        except ValueError:
            test_names.append(arg)
    if test_names:
        usage("Test names are not supported yet")
    CleanGenerated()

    suite, import_failures = make_test_suite(testLevel)
    if verbosity:
        if hasattr(sys, "gettotalrefcount"):
            print("This is a debug build - memory leak tests will also be run.")
            print("These tests may take *many* minutes to run - be patient!")
            print("(running from python.exe will avoid these leak tests)")
        print(
            "Executing level %d tests - %d test cases will be run"
            % (testLevel, suite.countTestCases())
        )
        if verbosity == 1 and suite.countTestCases() < 70:
            # A little row of markers so the dots show how close to finished
            print("|" * suite.countTestCases())
    testRunner = TestRunner(verbosity=verbosity)
    testResult = testRunner.run(suite)
    if import_failures:
        testResult.stream.writeln(
            "*** The following test modules could not be imported ***"
        )
        for mod_name, (exc_type, exc_val) in import_failures:
            desc = "\n".join(traceback.format_exception_only(exc_type, exc_val))
            testResult.stream.write(f"{mod_name}: {desc}")
        testResult.stream.writeln(
            "*** %d test(s) could not be run ***" % len(import_failures)
        )

    # re-print unit-test error here so it is noticed
    if not testResult.wasSuccessful():
        print("*" * 20, "- unittest tests FAILED")

    CheckClean()
    pythoncom.CoUninitialize()
    CleanGenerated()
    if not testResult.wasSuccessful():
        sys.exit(1)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\references.py ===
import os
import re

from parso import python_bytes_to_unicode

from jedi.debug import dbg
from jedi.file_io import KnownContentFileIO, FolderIO
from jedi.inference.names import SubModuleName
from jedi.inference.imports import load_module_from_path
from jedi.inference.filters import ParserTreeFilter
from jedi.inference.gradual.conversion import convert_names

_IGNORE_FOLDERS = ('.tox', '.venv', '.mypy_cache', 'venv', '__pycache__')

_OPENED_FILE_LIMIT = 2000
"""
Stats from a 2016 Lenovo Notebook running Linux:
With os.walk, it takes about 10s to scan 11'000 files (without filesystem
caching). Once cached it only takes 5s. So it is expected that reading all
those files might take a few seconds, but not a lot more.
"""
_PARSED_FILE_LIMIT = 30
"""
For now we keep the amount of parsed files really low, since parsing might take
easily 100ms for bigger files.
"""


def _resolve_names(definition_names, avoid_names=()):
    for name in definition_names:
        if name in avoid_names:
            # Avoiding recursions here, because goto on a module name lands
            # on the same module.
            continue

        if not isinstance(name, SubModuleName):
            # SubModuleNames are not actually existing names but created
            # names when importing something like `import foo.bar.baz`.
            yield name

        if name.api_type == 'module':
            yield from _resolve_names(name.goto(), definition_names)


def _dictionarize(names):
    return dict(
        (n if n.tree_name is None else n.tree_name, n)
        for n in names
    )


def _find_defining_names(module_context, tree_name):
    found_names = _find_names(module_context, tree_name)

    for name in list(found_names):
        # Convert from/to stubs, because those might also be usages.
        found_names |= set(convert_names(
            [name],
            only_stubs=not name.get_root_context().is_stub(),
            prefer_stub_to_compiled=False
        ))

    found_names |= set(_find_global_variables(found_names, tree_name.value))
    for name in list(found_names):
        if name.api_type == 'param' or name.tree_name is None \
                or name.tree_name.parent.type == 'trailer':
            continue
        found_names |= set(_add_names_in_same_context(name.parent_context, name.string_name))
    return set(_resolve_names(found_names))


def _find_names(module_context, tree_name):
    name = module_context.create_name(tree_name)
    found_names = set(name.goto())
    found_names.add(name)

    return set(_resolve_names(found_names))


def _add_names_in_same_context(context, string_name):
    if context.tree_node is None:
        return

    until_position = None
    while True:
        filter_ = ParserTreeFilter(
            parent_context=context,
            until_position=until_position,
        )
        names = set(filter_.get(string_name))
        if not names:
            break
        yield from names
        ordered = sorted(names, key=lambda x: x.start_pos)
        until_position = ordered[0].start_pos


def _find_global_variables(names, search_name):
    for name in names:
        if name.tree_name is None:
            continue
        module_context = name.get_root_context()
        try:
            method = module_context.get_global_filter
        except AttributeError:
            continue
        else:
            for global_name in method().get(search_name):
                yield global_name
                c = module_context.create_context(global_name.tree_name)
                yield from _add_names_in_same_context(c, global_name.string_name)


def find_references(module_context, tree_name, only_in_module=False):
    inf = module_context.inference_state
    search_name = tree_name.value

    # We disable flow analysis, because if we have ifs that are only true in
    # certain cases, we want both sides.
    try:
        inf.flow_analysis_enabled = False
        found_names = _find_defining_names(module_context, tree_name)
    finally:
        inf.flow_analysis_enabled = True

    found_names_dct = _dictionarize(found_names)

    module_contexts = [module_context]
    if not only_in_module:
        for m in set(d.get_root_context() for d in found_names):
            if m != module_context and m.tree_node is not None \
                    and inf.project.path in m.py__file__().parents:
                module_contexts.append(m)
    # For param no search for other modules is necessary.
    if only_in_module or any(n.api_type == 'param' for n in found_names):
        potential_modules = module_contexts
    else:
        potential_modules = get_module_contexts_containing_name(
            inf,
            module_contexts,
            search_name,
        )

    non_matching_reference_maps = {}
    for module_context in potential_modules:
        for name_leaf in module_context.tree_node.get_used_names().get(search_name, []):
            new = _dictionarize(_find_names(module_context, name_leaf))
            if any(tree_name in found_names_dct for tree_name in new):
                found_names_dct.update(new)
                for tree_name in new:
                    for dct in non_matching_reference_maps.get(tree_name, []):
                        # A reference that was previously searched for matches
                        # with a now found name. Merge.
                        found_names_dct.update(dct)
                    try:
                        del non_matching_reference_maps[tree_name]
                    except KeyError:
                        pass
            else:
                for name in new:
                    non_matching_reference_maps.setdefault(name, []).append(new)
    result = found_names_dct.values()
    if only_in_module:
        return [n for n in result if n.get_root_context() == module_context]
    return result


def _check_fs(inference_state, file_io, regex):
    try:
        code = file_io.read()
    except FileNotFoundError:
        return None
    code = python_bytes_to_unicode(code, errors='replace')
    if not regex.search(code):
        return None
    new_file_io = KnownContentFileIO(file_io.path, code)
    m = load_module_from_path(inference_state, new_file_io)
    if m.is_compiled():
        return None
    return m.as_context()


def gitignored_paths(folder_io, file_io):
    ignored_paths_abs = set()
    ignored_paths_rel = set()

    for l in file_io.read().splitlines():
        if not l or l.startswith(b'#') or l.startswith(b'!') or b'*' in l:
            continue

        p = l.decode('utf-8', 'ignore').rstrip('/')
        if '/' in p:
            name = p.lstrip('/')
            ignored_paths_abs.add(os.path.join(folder_io.path, name))
        else:
            name = p
            ignored_paths_rel.add((folder_io.path, name))

    return ignored_paths_abs, ignored_paths_rel


def expand_relative_ignore_paths(folder_io, relative_paths):
    curr_path = folder_io.path
    return {os.path.join(curr_path, p[1]) for p in relative_paths if curr_path.startswith(p[0])}


def recurse_find_python_folders_and_files(folder_io, except_paths=()):
    except_paths = set(except_paths)
    except_paths_relative = set()

    for root_folder_io, folder_ios, file_ios in folder_io.walk():
        # Delete folders that we don't want to iterate over.
        for file_io in file_ios:
            path = file_io.path
            if path.suffix in ('.py', '.pyi'):
                if path not in except_paths:
                    yield None, file_io

            if path.name == '.gitignore':
                ignored_paths_abs, ignored_paths_rel = gitignored_paths(
                    root_folder_io, file_io
                )
                except_paths |= ignored_paths_abs
                except_paths_relative |= ignored_paths_rel

        except_paths_relative_expanded = expand_relative_ignore_paths(
            root_folder_io, except_paths_relative
        )

        folder_ios[:] = [
            folder_io
            for folder_io in folder_ios
            if folder_io.path not in except_paths
            and folder_io.path not in except_paths_relative_expanded
            and folder_io.get_base_name() not in _IGNORE_FOLDERS
        ]
        for folder_io in folder_ios:
            yield folder_io, None


def recurse_find_python_files(folder_io, except_paths=()):
    for folder_io, file_io in recurse_find_python_folders_and_files(folder_io, except_paths):
        if file_io is not None:
            yield file_io


def _find_python_files_in_sys_path(inference_state, module_contexts):
    sys_path = inference_state.get_sys_path()
    except_paths = set()
    yielded_paths = [m.py__file__() for m in module_contexts]
    for module_context in module_contexts:
        file_io = module_context.get_value().file_io
        if file_io is None:
            continue

        folder_io = file_io.get_parent_folder()
        while True:
            path = folder_io.path
            if not any(path.startswith(p) for p in sys_path) or path in except_paths:
                break
            for file_io in recurse_find_python_files(folder_io, except_paths):
                if file_io.path not in yielded_paths:
                    yield file_io
            except_paths.add(path)
            folder_io = folder_io.get_parent_folder()


def _find_project_modules(inference_state, module_contexts):
    except_ = [m.py__file__() for m in module_contexts]
    yield from recurse_find_python_files(FolderIO(inference_state.project.path), except_)


def get_module_contexts_containing_name(inference_state, module_contexts, name,
                                        limit_reduction=1):
    """
    Search a name in the directories of modules.

    :param limit_reduction: Divides the limits on opening/parsing files by this
        factor.
    """
    # Skip non python modules
    for module_context in module_contexts:
        if module_context.is_compiled():
            continue
        yield module_context

    # Very short names are not searched in other modules for now to avoid lots
    # of file lookups.
    if len(name) <= 2:
        return

    # Currently not used, because there's only `scope=project` and `scope=file`
    # At the moment there is no such thing as `scope=sys.path`.
    # file_io_iterator = _find_python_files_in_sys_path(inference_state, module_contexts)
    file_io_iterator = _find_project_modules(inference_state, module_contexts)
    yield from search_in_file_ios(inference_state, file_io_iterator, name,
                                  limit_reduction=limit_reduction)


def search_in_file_ios(inference_state, file_io_iterator, name,
                       limit_reduction=1, complete=False):
    parse_limit = _PARSED_FILE_LIMIT / limit_reduction
    open_limit = _OPENED_FILE_LIMIT / limit_reduction
    file_io_count = 0
    parsed_file_count = 0
    regex = re.compile(r'\b' + re.escape(name) + (r'' if complete else r'\b'))
    for file_io in file_io_iterator:
        file_io_count += 1
        m = _check_fs(inference_state, file_io, regex)
        if m is not None:
            parsed_file_count += 1
            yield m
            if parsed_file_count >= parse_limit:
                dbg('Hit limit of parsed files: %s', parse_limit)
                break

        if file_io_count >= open_limit:
            dbg('Hit limit of opened files: %s', open_limit)
            break

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\chat\gpt_transformation.py ===
from typing import TYPE_CHECKING, Any, List, Optional, Union

from httpx._models import Headers, Response

import litellm
from litellm.litellm_core_utils.prompt_templates.factory import (
    convert_to_azure_openai_messages,
)
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.llms.azure import (
    API_VERSION_MONTH_SUPPORTED_RESPONSE_FORMAT,
    API_VERSION_YEAR_SUPPORTED_RESPONSE_FORMAT,
)
from litellm.types.utils import ModelResponse
from litellm.utils import supports_response_schema

from ....exceptions import UnsupportedParamsError
from ....types.llms.openai import AllMessageValues
from ...base_llm.chat.transformation import BaseConfig
from ..common_utils import AzureOpenAIError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class AzureOpenAIConfig(BaseConfig):
    """
    Reference: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions

    The class `AzureOpenAIConfig` provides configuration for the OpenAI's Chat API interface, for use with Azure. Below are the parameters::

    - `frequency_penalty` (number or null): Defaults to 0. Allows a value between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, thereby minimizing repetition.

    - `function_call` (string or object): This optional parameter controls how the model calls functions.

    - `functions` (array): An optional parameter. It is a list of functions for which the model may generate JSON inputs.

    - `logit_bias` (map): This optional parameter modifies the likelihood of specified tokens appearing in the completion.

    - `max_tokens` (integer or null): This optional parameter helps to set the maximum number of tokens to generate in the chat completion.

    - `n` (integer or null): This optional parameter helps to set how many chat completion choices to generate for each input message.

    - `presence_penalty` (number or null): Defaults to 0. It penalizes new tokens based on if they appear in the text so far, hence increasing the model's likelihood to talk about new topics.

    - `stop` (string / array / null): Specifies up to 4 sequences where the API will stop generating further tokens.

    - `temperature` (number or null): Defines the sampling temperature to use, varying between 0 and 2.

    - `top_p` (number or null): An alternative to sampling with temperature, used for nucleus sampling.
    """

    def __init__(
        self,
        frequency_penalty: Optional[int] = None,
        function_call: Optional[Union[str, dict]] = None,
        functions: Optional[list] = None,
        logit_bias: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        stop: Optional[Union[str, list]] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str) -> List[str]:
        return [
            "temperature",
            "n",
            "stream",
            "stream_options",
            "stop",
            "max_tokens",
            "max_completion_tokens",
            "tools",
            "tool_choice",
            "presence_penalty",
            "frequency_penalty",
            "logit_bias",
            "user",
            "function_call",
            "functions",
            "tools",
            "tool_choice",
            "top_p",
            "logprobs",
            "top_logprobs",
            "response_format",
            "seed",
            "extra_headers",
            "parallel_tool_calls",
            "prediction",
            "modalities",
            "audio",
            "web_search_options",
        ]

    def _is_response_format_supported_model(self, model: str) -> bool:
        """
        - all 4o models are supported
        - check if 'supports_response_format' is True from get_model_info
        - [TODO] support smart retries for 3.5 models (some supported, some not)
        """
        if "4o" in model:
            return True

        # Normalize model name by replacing dashes between numbers with dots
        # e.g., gpt-4-1 -> gpt-4.1, gpt-3-5-turbo -> gpt-3.5-turbo
        import re

        normalized_model = re.sub(r"(\d)-(\d)", r"\1.\2", model)

        if supports_response_schema(normalized_model):
            return True

        return False

    def _is_response_format_supported_api_version(
        self, api_version_year: str, api_version_month: str
    ) -> bool:
        """
        - check if api_version is supported for response_format
        - returns True if the API version is equal to or newer than the supported version
        """
        api_year = int(api_version_year)
        api_month = int(api_version_month)
        supported_year = int(API_VERSION_YEAR_SUPPORTED_RESPONSE_FORMAT)
        supported_month = int(API_VERSION_MONTH_SUPPORTED_RESPONSE_FORMAT)

        # If the year is greater than supported year, it's definitely supported
        if api_year > supported_year:
            return True
        # If the year is less than supported year, it's not supported
        elif api_year < supported_year:
            return False
        # If same year, check if month is >= supported month
        else:
            return api_month >= supported_month

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
        api_version: str = "",
    ) -> dict:
        supported_openai_params = self.get_supported_openai_params(model)

        api_version_times = api_version.split("-")
        api_version_year = api_version_times[0]
        api_version_month = api_version_times[1]
        api_version_day = api_version_times[2]
        for param, value in non_default_params.items():
            if param == "tool_choice":
                """
                This parameter requires API version 2023-12-01-preview or later

                tool_choice='required' is not supported as of 2024-05-01-preview
                """
                ## check if api version supports this param ##
                if (
                    api_version_year < "2023"
                    or (api_version_year == "2023" and api_version_month < "12")
                    or (
                        api_version_year == "2023"
                        and api_version_month == "12"
                        and api_version_day < "01"
                    )
                ):
                    if litellm.drop_params is True or (
                        drop_params is not None and drop_params is True
                    ):
                        pass
                    else:
                        raise UnsupportedParamsError(
                            status_code=400,
                            message=f"""Azure does not support 'tool_choice', for api_version={api_version}. Bump your API version to '2023-12-01-preview' or later. This parameter requires 'api_version="2023-12-01-preview"' or later. Azure API Reference: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions""",
                        )
                elif value == "required" and (
                    api_version_year == "2024" and api_version_month <= "05"
                ):  ## check if tool_choice value is supported ##
                    if litellm.drop_params is True or (
                        drop_params is not None and drop_params is True
                    ):
                        pass
                    else:
                        raise UnsupportedParamsError(
                            status_code=400,
                            message=f"Azure does not support '{value}' as a {param} param, for api_version={api_version}. To drop 'tool_choice=required' for calls with this Azure API version, set `litellm.drop_params=True` or for proxy:\n\n`litellm_settings:\n drop_params: true`\nAzure API Reference: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions",
                        )
                else:
                    optional_params["tool_choice"] = value
            elif param == "response_format" and isinstance(value, dict):
                _is_response_format_supported_model = (
                    self._is_response_format_supported_model(model)
                )

                is_response_format_supported_api_version = (
                    self._is_response_format_supported_api_version(
                        api_version_year, api_version_month
                    )
                )
                is_response_format_supported = (
                    is_response_format_supported_api_version
                    and _is_response_format_supported_model
                )

                optional_params = self._add_response_format_to_tools(
                    optional_params=optional_params,
                    value=value,
                    is_response_format_supported=is_response_format_supported,
                )
            elif param == "tools" and isinstance(value, list):
                optional_params.setdefault("tools", [])
                optional_params["tools"].extend(value)
            elif param in supported_openai_params:
                optional_params[param] = value

        return optional_params

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        messages = convert_to_azure_openai_messages(messages)
        return {
            "model": model,
            "messages": messages,
            **optional_params,
        }

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        raise NotImplementedError(
            "Azure OpenAI handler.py has custom logic for transforming response, as it uses the OpenAI SDK."
        )

    def get_mapped_special_auth_params(self) -> dict:
        return {"token": "azure_ad_token"}

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        for param, value in non_default_params.items():
            if param == "token":
                optional_params["azure_ad_token"] = value
        return optional_params

    def get_eu_regions(self) -> List[str]:
        """
        Source: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models#gpt-4-and-gpt-4-turbo-model-availability
        """
        return ["europe", "sweden", "switzerland", "france", "uk"]

    def get_us_regions(self) -> List[str]:
        """
        Source: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models#gpt-4-and-gpt-4-turbo-model-availability
        """
        return [
            "us",
            "eastus",
            "eastus2",
            "eastus2euap",
            "eastus3",
            "southcentralus",
            "westus",
            "westus2",
            "westus3",
            "westus4",
        ]

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return AzureOpenAIError(
            message=error_message, status_code=status_code, headers=headers
        )

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        raise NotImplementedError(
            "Azure OpenAI has custom logic for validating environment, as it uses the OpenAI SDK."
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\credential_endpoints\endpoints.py ===
"""
CRUD endpoints for storing reusable credentials.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Path

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.credential_accessor import CredentialAccessor
from litellm.litellm_core_utils.litellm_logging import _get_masked_values
from litellm.proxy._types import CommonProxyErrors, UserAPIKeyAuth
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_utils.encrypt_decrypt_utils import encrypt_value_helper
from litellm.proxy.utils import handle_exception_on_proxy, jsonify_object
from litellm.types.utils import CreateCredentialItem, CredentialItem

router = APIRouter()


class CredentialHelperUtils:
    @staticmethod
    def encrypt_credential_values(credential: CredentialItem) -> CredentialItem:
        """Encrypt values in credential.credential_values and add to DB"""
        encrypted_credential_values = {}
        for key, value in credential.credential_values.items():
            encrypted_credential_values[key] = encrypt_value_helper(value)
        credential.credential_values = encrypted_credential_values
        return credential


@router.post(
    "/credentials",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
)
async def create_credential(
    request: Request,
    fastapi_response: Response,
    credential: CreateCredentialItem,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] endpoint. This might change unexpectedly.
    Stores credential in DB.
    Reloads credentials in memory.
    """
    from litellm.proxy.proxy_server import llm_router, prisma_client

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )
        if credential.model_id:
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail="LLM router not found. Please ensure you have a valid router instance.",
                )
            # get model from router
            model = llm_router.get_deployment(credential.model_id)
            if model is None:
                raise HTTPException(status_code=404, detail="Model not found")
            credential_values = llm_router.get_deployment_credentials(
                credential.model_id
            )
            if credential_values is None:
                raise HTTPException(status_code=404, detail="Model not found")
            credential.credential_values = credential_values

        if credential.credential_values is None:
            raise HTTPException(
                status_code=400,
                detail="Credential values are required. Unable to infer credential values from model ID.",
            )
        processed_credential = CredentialItem(
            credential_name=credential.credential_name,
            credential_values=credential.credential_values,
            credential_info=credential.credential_info,
        )
        encrypted_credential = CredentialHelperUtils.encrypt_credential_values(
            processed_credential
        )
        credentials_dict = encrypted_credential.model_dump()
        credentials_dict_jsonified = jsonify_object(credentials_dict)
        await prisma_client.db.litellm_credentialstable.create(
            data={
                **credentials_dict_jsonified,
                "created_by": user_api_key_dict.user_id,
                "updated_by": user_api_key_dict.user_id,
            }
        )

        ## ADD TO LITELLM ##
        CredentialAccessor.upsert_credentials([processed_credential])

        return {"success": True, "message": "Credential created successfully"}
    except Exception as e:
        verbose_proxy_logger.exception(e)
        raise handle_exception_on_proxy(e)


@router.get(
    "/credentials",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
)
async def get_credentials(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] endpoint. This might change unexpectedly.
    """
    try:
        masked_credentials = [
            {
                "credential_name": credential.credential_name,
                "credential_values": _get_masked_values(credential.credential_values),
                "credential_info": credential.credential_info,
            }
            for credential in litellm.credential_list
        ]
        return {"success": True, "credentials": masked_credentials}
    except Exception as e:
        return handle_exception_on_proxy(e)


@router.get(
    "/credentials/by_name/{credential_name:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
    response_model=CredentialItem,
)
@router.get(
    "/credentials/by_model/{model_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
    response_model=CredentialItem,
)
async def get_credential(
    request: Request,
    fastapi_response: Response,
    credential_name: str = Path(..., description="The credential name, percent-decoded; may contain slashes"),
    model_id: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] endpoint. This might change unexpectedly.
    """
    from litellm.proxy.proxy_server import llm_router

    try:
        if model_id:
            if llm_router is None:
                raise HTTPException(status_code=500, detail="LLM router not found")
            model = llm_router.get_deployment(model_id)
            if model is None:
                raise HTTPException(status_code=404, detail="Model not found")
            credential_values = llm_router.get_deployment_credentials(model_id)
            if credential_values is None:
                raise HTTPException(status_code=404, detail="Model not found")
            masked_credential_values = _get_masked_values(
                credential_values,
                unmasked_length=4,
                number_of_asterisks=4,
            )
            credential = CredentialItem(
                credential_name="{}-credential-{}".format(model.model_name, model_id),
                credential_values=masked_credential_values,
                credential_info={},
            )
            # return credential object
            return credential
        elif credential_name:
            for credential in litellm.credential_list:
                if credential.credential_name == credential_name:
                    masked_credential = CredentialItem(
                        credential_name=credential.credential_name,
                        credential_values=_get_masked_values(
                            credential.credential_values,
                            unmasked_length=4,
                            number_of_asterisks=4,
                        ),
                        credential_info=credential.credential_info,
                    )
                    return masked_credential
            raise HTTPException(
                status_code=404,
                detail="Credential not found. Got credential name: " + credential_name,
            )
        else:
            raise HTTPException(
                status_code=404, detail="Credential name or model ID required"
            )
    except Exception as e:
        verbose_proxy_logger.exception(e)
        raise handle_exception_on_proxy(e)


@router.delete(
    "/credentials/{credential_name:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
)
async def delete_credential(
    request: Request,
    fastapi_response: Response,
    credential_name: str = Path(..., description="The credential name, percent-decoded; may contain slashes"),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] endpoint. This might change unexpectedly.
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )
        await prisma_client.db.litellm_credentialstable.delete(
            where={"credential_name": credential_name}
        )

        ## DELETE FROM LITELLM ##
        litellm.credential_list = [
            cred
            for cred in litellm.credential_list
            if cred.credential_name != credential_name
        ]
        return {"success": True, "message": "Credential deleted successfully"}
    except Exception as e:
        return handle_exception_on_proxy(e)


def update_db_credential(
    db_credential: CredentialItem, updated_patch: CredentialItem
) -> CredentialItem:
    """
    Update a credential in the DB.
    """
    merged_credential = CredentialItem(
        credential_name=db_credential.credential_name,
        credential_info=db_credential.credential_info,
        credential_values=db_credential.credential_values,
    )

    encrypted_credential = CredentialHelperUtils.encrypt_credential_values(
        updated_patch
    )
    # update model name
    if encrypted_credential.credential_name:
        merged_credential.credential_name = encrypted_credential.credential_name

    # update litellm params
    if encrypted_credential.credential_values:
        # Encrypt any sensitive values
        encrypted_params = {
            k: v for k, v in encrypted_credential.credential_values.items()
        }

        merged_credential.credential_values.update(encrypted_params)

    # update model info
    if encrypted_credential.credential_info:
        """Update credential info"""
        if "credential_info" not in merged_credential.credential_info:
            merged_credential.credential_info = {}
        merged_credential.credential_info.update(encrypted_credential.credential_info)

    return merged_credential


@router.patch(
    "/credentials/{credential_name:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["credential management"],
)
async def update_credential(
    request: Request,
    fastapi_response: Response,
    credential: CredentialItem,
    credential_name: str = Path(..., description="The credential name, percent-decoded; may contain slashes"),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] endpoint. This might change unexpectedly.
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )
        db_credential = await prisma_client.db.litellm_credentialstable.find_unique(
            where={"credential_name": credential_name},
        )
        if db_credential is None:
            raise HTTPException(status_code=404, detail="Credential not found in DB.")
        merged_credential = update_db_credential(db_credential, credential)
        credential_object_jsonified = jsonify_object(merged_credential.model_dump())
        await prisma_client.db.litellm_credentialstable.update(
            where={"credential_name": credential_name},
            data={
                **credential_object_jsonified,
                "updated_by": user_api_key_dict.user_id,
            },
        )
        return {"success": True, "message": "Credential updated successfully"}
    except Exception as e:
        return handle_exception_on_proxy(e)

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\rule.py ===
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

from abc import ABCMeta, abstractmethod

from nltk import jsontags


######################################################################
# Tag Rules
######################################################################
class TagRule(metaclass=ABCMeta):
    """
    An interface for tag transformations on a tagged corpus, as
    performed by tbl taggers.  Each transformation finds all tokens
    in the corpus that are tagged with a specific original tag and
    satisfy a specific condition, and replaces their tags with a
    replacement tag.  For any given transformation, the original
    tag, replacement tag, and condition are fixed.  Conditions may
    depend on the token under consideration, as well as any other
    tokens in the corpus.

    Tag rules must be comparable and hashable.
    """

    def __init__(self, original_tag, replacement_tag):
        self.original_tag = original_tag
        """The tag which this TagRule may cause to be replaced."""

        self.replacement_tag = replacement_tag
        """The tag with which this TagRule may replace another tag."""

    def apply(self, tokens, positions=None):
        """
        Apply this rule at every position in positions where it
        applies to the given sentence.  I.e., for each position p
        in *positions*, if *tokens[p]* is tagged with this rule's
        original tag, and satisfies this rule's condition, then set
        its tag to be this rule's replacement tag.

        :param tokens: The tagged sentence
        :type tokens: list(tuple(str, str))
        :type positions: list(int)
        :param positions: The positions where the transformation is to
            be tried.  If not specified, try it at all positions.
        :return: The indices of tokens whose tags were changed by this
            rule.
        :rtype: int
        """
        if positions is None:
            positions = list(range(len(tokens)))

        # Determine the indices at which this rule applies.
        change = [i for i in positions if self.applies(tokens, i)]

        # Make the changes.  Note: this must be done in a separate
        # step from finding applicable locations, since we don't want
        # the rule to interact with itself.
        for i in change:
            tokens[i] = (tokens[i][0], self.replacement_tag)

        return change

    @abstractmethod
    def applies(self, tokens, index):
        """
        :return: True if the rule would change the tag of
            ``tokens[index]``, False otherwise
        :rtype: bool
        :param tokens: A tagged sentence
        :type tokens: list(str)
        :param index: The index to check
        :type index: int
        """

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self, other):
        raise TypeError("Rules must implement __eq__()")

    def __ne__(self, other):
        raise TypeError("Rules must implement __ne__()")

    def __hash__(self):
        raise TypeError("Rules must implement __hash__()")


@jsontags.register_tag
class Rule(TagRule):
    """
    A Rule checks the current corpus position for a certain set of conditions;
    if they are all fulfilled, the Rule is triggered, meaning that it
    will change tag A to tag B. For other tags than A, nothing happens.

    The conditions are parameters to the Rule instance. Each condition is a feature-value pair,
    with a set of positions to check for the value of the corresponding feature.
    Conceptually, the positions are joined by logical OR, and the feature set by logical AND.

    More formally, the Rule is then applicable to the M{n}th token iff:

      - The M{n}th token is tagged with the Rule's original tag; and
      - For each (Feature(positions), M{value}) tuple:

        - The value of Feature of at least one token in {n+p for p in positions}
          is M{value}.
    """

    json_tag = "nltk.tbl.Rule"

    def __init__(self, templateid, original_tag, replacement_tag, conditions):
        """
        Construct a new Rule that changes a token's tag from
        C{original_tag} to C{replacement_tag} if all of the properties
        specified in C{conditions} hold.

        :param templateid: the template id (a zero-padded string, '001' etc,
            so it will sort nicely)
        :type templateid: string

        :param conditions: A list of Feature(positions),
            each of which specifies that the property (computed by
            Feature.extract_property()) of at least one
            token in M{n} + p in positions is C{value}.
        :type conditions: C{iterable} of C{Feature}

        """
        TagRule.__init__(self, original_tag, replacement_tag)
        self._conditions = conditions
        self.templateid = templateid

    def encode_json_obj(self):
        return {
            "templateid": self.templateid,
            "original": self.original_tag,
            "replacement": self.replacement_tag,
            "conditions": self._conditions,
        }

    @classmethod
    def decode_json_obj(cls, obj):
        return cls(
            obj["templateid"],
            obj["original"],
            obj["replacement"],
            tuple(tuple(feat) for feat in obj["conditions"]),
        )

    def applies(self, tokens, index):
        # Inherit docs from TagRule

        # Does the given token have this Rule's "original tag"?
        if tokens[index][1] != self.original_tag:
            return False

        # Check to make sure that every condition holds.
        for feature, val in self._conditions:
            # Look for *any* token that satisfies the condition.
            for pos in feature.positions:
                if not (0 <= index + pos < len(tokens)):
                    continue
                if feature.extract_property(tokens, index + pos) == val:
                    break
            else:
                # No token satisfied the condition; return false.
                return False

        # Every condition checked out, so the Rule is applicable.
        return True

    def __eq__(self, other):
        return self is other or (
            other is not None
            and other.__class__ == self.__class__
            and self.original_tag == other.original_tag
            and self.replacement_tag == other.replacement_tag
            and self._conditions == other._conditions
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        # Cache our hash value (justified by profiling.)
        try:
            return self.__hash
        except AttributeError:
            self.__hash = hash(repr(self))
            return self.__hash

    def __repr__(self):
        # Cache the repr (justified by profiling -- this is used as
        # a sort key when deterministic=True.)
        try:
            return self.__repr
        except AttributeError:
            self.__repr = "{}('{}', {}, {}, [{}])".format(
                self.__class__.__name__,
                self.templateid,
                repr(self.original_tag),
                repr(self.replacement_tag),
                # list(self._conditions) would be simpler but will not generate
                # the same Rule.__repr__ in python 2 and 3 and thus break some tests
                ", ".join(f"({f},{repr(v)})" for (f, v) in self._conditions),
            )

            return self.__repr

    def __str__(self):
        def _condition_to_logic(feature, value):
            """
            Return a compact, predicate-logic styled string representation
            of the given condition.
            """
            return "{}:{}@[{}]".format(
                feature.PROPERTY_NAME,
                value,
                ",".join(str(w) for w in feature.positions),
            )

        conditions = " & ".join(
            [_condition_to_logic(f, v) for (f, v) in self._conditions]
        )
        s = f"{self.original_tag}->{self.replacement_tag} if {conditions}"

        return s

    def format(self, fmt):
        """
        Return a string representation of this rule.

        >>> from nltk.tbl.rule import Rule
        >>> from nltk.tag.brill import Pos

        >>> r = Rule("23", "VB", "NN", [(Pos([-2,-1]), 'DT')])

        r.format("str") == str(r)
        True
        >>> r.format("str")
        'VB->NN if Pos:DT@[-2,-1]'

        r.format("repr") == repr(r)
        True
        >>> r.format("repr")
        "Rule('23', 'VB', 'NN', [(Pos([-2, -1]),'DT')])"

        >>> r.format("verbose")
        'VB -> NN if the Pos of words i-2...i-1 is "DT"'

        >>> r.format("not_found")
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "nltk/tbl/rule.py", line 256, in format
            raise ValueError("unknown rule format spec: {0}".format(fmt))
        ValueError: unknown rule format spec: not_found
        >>>

        :param fmt: format specification
        :type fmt: str
        :return: string representation
        :rtype: str
        """
        if fmt == "str":
            return self.__str__()
        elif fmt == "repr":
            return self.__repr__()
        elif fmt == "verbose":
            return self._verbose_format()
        else:
            raise ValueError(f"unknown rule format spec: {fmt}")

    def _verbose_format(self):
        """
        Return a wordy, human-readable string representation
        of the given rule.

        Not sure how useful this is.
        """

        def condition_to_str(feature, value):
            return 'the {} of {} is "{}"'.format(
                feature.PROPERTY_NAME,
                range_to_str(feature.positions),
                value,
            )

        def range_to_str(positions):
            if len(positions) == 1:
                p = positions[0]
                if p == 0:
                    return "this word"
                if p == -1:
                    return "the preceding word"
                elif p == 1:
                    return "the following word"
                elif p < 0:
                    return "word i-%d" % -p
                elif p > 0:
                    return "word i+%d" % p
            else:
                # for complete compatibility with the wordy format of nltk2
                mx = max(positions)
                mn = min(positions)
                if mx - mn == len(positions) - 1:
                    return "words i%+d...i%+d" % (mn, mx)
                else:
                    return "words {{{}}}".format(
                        ",".join("i%+d" % d for d in positions)
                    )

        replacement = f"{self.original_tag} -> {self.replacement_tag}"
        conditions = (" if " if self._conditions else "") + ", and ".join(
            condition_to_str(f, v) for (f, v) in self._conditions
        )
        return replacement + conditions

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm2.py ===
# Natural Language Toolkit: IBM Model 2
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Lexical translation model that considers word order.

IBM Model 2 improves on Model 1 by accounting for word order.
An alignment probability is introduced, a(i | j,l,m), which predicts
a source word position, given its aligned target word's position.

The EM algorithm used in Model 2 is:

:E step: In the training data, collect counts, weighted by prior
         probabilities.

         - (a) count how many times a source language word is translated
               into a target language word
         - (b) count how many times a particular position in the source
               sentence is aligned to a particular position in the target
               sentence

:M step: Estimate new probabilities based on the counts from the E step

Notations
---------

:i: Position in the source sentence
     Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
:j: Position in the target sentence
     Valid values are 1, 2, ..., length of target sentence
:l: Number of words in the source sentence, excluding NULL
:m: Number of words in the target sentence
:s: A word in the source language
:t: A word in the target language

References
----------

Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

import warnings
from collections import defaultdict

from nltk.translate import AlignedSent, Alignment, IBMModel, IBMModel1
from nltk.translate.ibm_model import Counts


class IBMModel2(IBMModel):
    """
    Lexical translation model that considers word order

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'ist', 'ja', 'groß'], ['the', 'house', 'is', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))

    >>> ibm2 = IBMModel2(bitext, 5)

    >>> print(round(ibm2.translation_table['buch']['book'], 3))
    1.0
    >>> print(round(ibm2.translation_table['das']['book'], 3))
    0.0
    >>> print(round(ibm2.translation_table['buch'][None], 3))
    0.0
    >>> print(round(ibm2.translation_table['ja'][None], 3))
    0.0

    >>> print(round(ibm2.alignment_table[1][1][2][2], 3))
    0.939
    >>> print(round(ibm2.alignment_table[1][2][2][2], 3))
    0.0
    >>> print(round(ibm2.alignment_table[2][2][4][5], 3))
    1.0

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, 2), (4, 3)])

    """

    def __init__(self, sentence_aligned_corpus, iterations, probability_tables=None):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model and an alignment model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int

        :param probability_tables: Optional. Use this to pass in custom
            probability values. If not specified, probabilities will be
            set to a uniform distribution, or some other sensible value.
            If specified, all the following entries must be present:
            ``translation_table``, ``alignment_table``.
            See ``IBMModel`` for the type and purpose of these tables.
        :type probability_tables: dict[str]: object
        """
        super().__init__(sentence_aligned_corpus)

        if probability_tables is None:
            # Get translation probabilities from IBM Model 1
            # Run more iterations of training for Model 1, since it is
            # faster than Model 2
            ibm1 = IBMModel1(sentence_aligned_corpus, 2 * iterations)
            self.translation_table = ibm1.translation_table
            self.set_uniform_probabilities(sentence_aligned_corpus)
        else:
            # Set user-defined probabilities
            self.translation_table = probability_tables["translation_table"]
            self.alignment_table = probability_tables["alignment_table"]

        for n in range(0, iterations):
            self.train(sentence_aligned_corpus)

        self.align_all(sentence_aligned_corpus)

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        # a(i | j,l,m) = 1 / (l+1) for all i, j, l, m
        l_m_combinations = set()
        for aligned_sentence in sentence_aligned_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)
            if (l, m) not in l_m_combinations:
                l_m_combinations.add((l, m))
                initial_prob = 1 / (l + 1)
                if initial_prob < IBMModel.MIN_PROB:
                    warnings.warn(
                        "A source sentence is too long ("
                        + str(l)
                        + " words). Results may be less accurate."
                    )

                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        self.alignment_table[i][j][l][m] = initial_prob

    def train(self, parallel_corpus):
        counts = Model2Counts()
        for aligned_sentence in parallel_corpus:
            src_sentence = [None] + aligned_sentence.mots
            trg_sentence = ["UNUSED"] + aligned_sentence.words  # 1-indexed
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)

            # E step (a): Compute normalization factors to weigh counts
            total_count = self.prob_all_alignments(src_sentence, trg_sentence)

            # E step (b): Collect counts
            for j in range(1, m + 1):
                t = trg_sentence[j]
                for i in range(0, l + 1):
                    s = src_sentence[i]
                    count = self.prob_alignment_point(i, j, src_sentence, trg_sentence)
                    normalized_count = count / total_count[t]

                    counts.update_lexical_translation(normalized_count, s, t)
                    counts.update_alignment(normalized_count, i, j, l, m)

        # M step: Update probabilities with maximum likelihood estimates
        self.maximize_lexical_translation_probabilities(counts)
        self.maximize_alignment_probabilities(counts)

    def maximize_alignment_probabilities(self, counts):
        MIN_PROB = IBMModel.MIN_PROB
        for i, j_s in counts.alignment.items():
            for j, src_sentence_lengths in j_s.items():
                for l, trg_sentence_lengths in src_sentence_lengths.items():
                    for m in trg_sentence_lengths:
                        estimate = (
                            counts.alignment[i][j][l][m]
                            / counts.alignment_for_any_i[j][l][m]
                        )
                        self.alignment_table[i][j][l][m] = max(estimate, MIN_PROB)

    def prob_all_alignments(self, src_sentence, trg_sentence):
        """
        Computes the probability of all possible word alignments,
        expressed as a marginal distribution over target words t

        Each entry in the return value represents the contribution to
        the total alignment probability by the target word t.

        To obtain probability(alignment | src_sentence, trg_sentence),
        simply sum the entries in the return value.

        :return: Probability of t for all s in ``src_sentence``
        :rtype: dict(str): float
        """
        alignment_prob_for_t = defaultdict(float)
        for j in range(1, len(trg_sentence)):
            t = trg_sentence[j]
            for i in range(0, len(src_sentence)):
                alignment_prob_for_t[t] += self.prob_alignment_point(
                    i, j, src_sentence, trg_sentence
                )
        return alignment_prob_for_t

    def prob_alignment_point(self, i, j, src_sentence, trg_sentence):
        """
        Probability that position j in ``trg_sentence`` is aligned to
        position i in the ``src_sentence``
        """
        l = len(src_sentence) - 1
        m = len(trg_sentence) - 1
        s = src_sentence[i]
        t = trg_sentence[j]
        return self.translation_table[t][s] * self.alignment_table[i][j][l][m]

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        prob = 1.0
        l = len(alignment_info.src_sentence) - 1
        m = len(alignment_info.trg_sentence) - 1

        for j, i in enumerate(alignment_info.alignment):
            if j == 0:
                continue  # skip the dummy zeroeth element
            trg_word = alignment_info.trg_sentence[j]
            src_word = alignment_info.src_sentence[i]
            prob *= (
                self.translation_table[trg_word][src_word]
                * self.alignment_table[i][j][l][m]
            )

        return max(prob, IBMModel.MIN_PROB)

    def align_all(self, parallel_corpus):
        for sentence_pair in parallel_corpus:
            self.align(sentence_pair)

    def align(self, sentence_pair):
        """
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The best alignment will be set in ``sentence_pair`` when the
        method returns. In contrast with the internal implementation of
        IBM models, the word indices in the ``Alignment`` are zero-
        indexed, not one-indexed.

        :param sentence_pair: A sentence in the source language and its
            counterpart sentence in the target language
        :type sentence_pair: AlignedSent
        """
        best_alignment = []

        l = len(sentence_pair.mots)
        m = len(sentence_pair.words)

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            best_prob = (
                self.translation_table[trg_word][None]
                * self.alignment_table[0][j + 1][l][m]
            )
            best_prob = max(best_prob, IBMModel.MIN_PROB)
            best_alignment_point = None
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = (
                    self.translation_table[trg_word][src_word]
                    * self.alignment_table[i + 1][j + 1][l][m]
                )
                if align_prob >= best_prob:
                    best_prob = align_prob
                    best_alignment_point = i

            best_alignment.append((j, best_alignment_point))

        sentence_pair.alignment = Alignment(best_alignment)


class Model2Counts(Counts):
    """
    Data object to store counts of various parameters during training.
    Includes counts for alignment.
    """

    def __init__(self):
        super().__init__()
        self.alignment = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        )
        self.alignment_for_any_i = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

    def update_lexical_translation(self, count, s, t):
        self.t_given_s[t][s] += count
        self.any_t_given_s[s] += count

    def update_alignment(self, count, i, j, l, m):
        self.alignment[i][j][l][m] += count
        self.alignment_for_any_i[j][l][m] += count

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\panel.py ===
from typing import TYPE_CHECKING, Optional

from .align import AlignMethod
from .box import ROUNDED, Box
from .cells import cell_len
from .jupyter import JupyterMixin
from .measure import Measurement, measure_renderables
from .padding import Padding, PaddingDimensions
from .segment import Segment
from .style import Style, StyleType
from .text import Text, TextType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult


class Panel(JupyterMixin):
    """A console renderable that draws a border around its contents.

    Example:
        >>> console.print(Panel("Hello, World!"))

    Args:
        renderable (RenderableType): A console renderable object.
        box (Box, optional): A Box instance that defines the look of the border (see :ref:`appendix_box`. Defaults to box.ROUNDED.
        title (Optional[TextType], optional): Optional title displayed in panel header. Defaults to None.
        title_align (AlignMethod, optional): Alignment of title. Defaults to "center".
        subtitle (Optional[TextType], optional): Optional subtitle displayed in panel footer. Defaults to None.
        subtitle_align (AlignMethod, optional): Alignment of subtitle. Defaults to "center".
        safe_box (bool, optional): Disable box characters that don't display on windows legacy terminal with *raster* fonts. Defaults to True.
        expand (bool, optional): If True the panel will stretch to fill the console width, otherwise it will be sized to fit the contents. Defaults to True.
        style (str, optional): The style of the panel (border and contents). Defaults to "none".
        border_style (str, optional): The style of the border. Defaults to "none".
        width (Optional[int], optional): Optional width of panel. Defaults to None to auto-detect.
        height (Optional[int], optional): Optional height of panel. Defaults to None to auto-detect.
        padding (Optional[PaddingDimensions]): Optional padding around renderable. Defaults to 0.
        highlight (bool, optional): Enable automatic highlighting of panel title (if str). Defaults to False.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        expand: bool = True,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> None:
        self.renderable = renderable
        self.box = box
        self.title = title
        self.title_align: AlignMethod = title_align
        self.subtitle = subtitle
        self.subtitle_align = subtitle_align
        self.safe_box = safe_box
        self.expand = expand
        self.style = style
        self.border_style = border_style
        self.width = width
        self.height = height
        self.padding = padding
        self.highlight = highlight

    @classmethod
    def fit(
        cls,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> "Panel":
        """An alternative constructor that sets expand=False."""
        return cls(
            renderable,
            box,
            title=title,
            title_align=title_align,
            subtitle=subtitle,
            subtitle_align=subtitle_align,
            safe_box=safe_box,
            style=style,
            border_style=border_style,
            width=width,
            height=height,
            padding=padding,
            highlight=highlight,
            expand=False,
        )

    @property
    def _title(self) -> Optional[Text]:
        if self.title:
            title_text = (
                Text.from_markup(self.title)
                if isinstance(self.title, str)
                else self.title.copy()
            )
            title_text.end = ""
            title_text.plain = title_text.plain.replace("\n", " ")
            title_text.no_wrap = True
            title_text.expand_tabs()
            title_text.pad(1)
            return title_text
        return None

    @property
    def _subtitle(self) -> Optional[Text]:
        if self.subtitle:
            subtitle_text = (
                Text.from_markup(self.subtitle)
                if isinstance(self.subtitle, str)
                else self.subtitle.copy()
            )
            subtitle_text.end = ""
            subtitle_text.plain = subtitle_text.plain.replace("\n", " ")
            subtitle_text.no_wrap = True
            subtitle_text.expand_tabs()
            subtitle_text.pad(1)
            return subtitle_text
        return None

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        _padding = Padding.unpack(self.padding)
        renderable = (
            Padding(self.renderable, _padding) if any(_padding) else self.renderable
        )
        style = console.get_style(self.style)
        partial_border_style = console.get_style(self.border_style)
        border_style = style + partial_border_style
        width = (
            options.max_width
            if self.width is None
            else min(options.max_width, self.width)
        )

        safe_box: bool = console.safe_box if self.safe_box is None else self.safe_box
        box = self.box.substitute(options, safe=safe_box)

        def align_text(
            text: Text, width: int, align: str, character: str, style: Style
        ) -> Text:
            """Gets new aligned text.

            Args:
                text (Text): Title or subtitle text.
                width (int): Desired width.
                align (str): Alignment.
                character (str): Character for alignment.
                style (Style): Border style

            Returns:
                Text: New text instance
            """
            text = text.copy()
            text.truncate(width)
            excess_space = width - cell_len(text.plain)
            if text.style:
                text.stylize(console.get_style(text.style))

            if excess_space:
                if align == "left":
                    return Text.assemble(
                        text,
                        (character * excess_space, style),
                        no_wrap=True,
                        end="",
                    )
                elif align == "center":
                    left = excess_space // 2
                    return Text.assemble(
                        (character * left, style),
                        text,
                        (character * (excess_space - left), style),
                        no_wrap=True,
                        end="",
                    )
                else:
                    return Text.assemble(
                        (character * excess_space, style),
                        text,
                        no_wrap=True,
                        end="",
                    )
            return text

        title_text = self._title
        if title_text is not None:
            title_text.stylize_before(partial_border_style)

        child_width = (
            width - 2
            if self.expand
            else console.measure(
                renderable, options=options.update_width(width - 2)
            ).maximum
        )
        child_height = self.height or options.height or None
        if child_height:
            child_height -= 2
        if title_text is not None:
            child_width = min(
                options.max_width - 2, max(child_width, title_text.cell_len + 2)
            )

        width = child_width + 2
        child_options = options.update(
            width=child_width, height=child_height, highlight=self.highlight
        )
        lines = console.render_lines(renderable, child_options, style=style)

        line_start = Segment(box.mid_left, border_style)
        line_end = Segment(f"{box.mid_right}", border_style)
        new_line = Segment.line()
        if title_text is None or width <= 4:
            yield Segment(box.get_top([width - 2]), border_style)
        else:
            title_text = align_text(
                title_text,
                width - 4,
                self.title_align,
                box.top,
                border_style,
            )
            yield Segment(box.top_left + box.top, border_style)
            yield from console.render(title_text, child_options.update_width(width - 4))
            yield Segment(box.top + box.top_right, border_style)

        yield new_line
        for line in lines:
            yield line_start
            yield from line
            yield line_end
            yield new_line

        subtitle_text = self._subtitle
        if subtitle_text is not None:
            subtitle_text.stylize_before(partial_border_style)

        if subtitle_text is None or width <= 4:
            yield Segment(box.get_bottom([width - 2]), border_style)
        else:
            subtitle_text = align_text(
                subtitle_text,
                width - 4,
                self.subtitle_align,
                box.bottom,
                border_style,
            )
            yield Segment(box.bottom_left + box.bottom, border_style)
            yield from console.render(
                subtitle_text, child_options.update_width(width - 4)
            )
            yield Segment(box.bottom + box.bottom_right, border_style)

        yield new_line

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _title = self._title
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        renderables = [self.renderable, _title] if _title else [self.renderable]

        if self.width is None:
            width = (
                measure_renderables(
                    console,
                    options.update_width(options.max_width - padding - 2),
                    renderables,
                ).maximum
                + padding
                + 2
            )
        else:
            width = self.width
        return Measurement(width, width)


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    c = Console()

    from .box import DOUBLE, ROUNDED
    from .padding import Padding

    p = Panel(
        "Hello, World!",
        title="rich.Panel",
        style="white on blue",
        box=DOUBLE,
        padding=1,
    )

    c.print()
    c.print(p)

# === NexusCore/openenv\Lib\site-packages\httpcore\_synchronization.py ===
from __future__ import annotations

import threading
import types

from ._exceptions import ExceptionMapping, PoolTimeout, map_exceptions

# Our async synchronization primatives use either 'anyio' or 'trio' depending
# on if they're running under asyncio or trio.

try:
    import trio
except (ImportError, NotImplementedError):  # pragma: nocover
    trio = None  # type: ignore

try:
    import anyio
except ImportError:  # pragma: nocover
    anyio = None  # type: ignore


def current_async_library() -> str:
    # Determine if we're running under trio or asyncio.
    # See https://sniffio.readthedocs.io/en/latest/
    try:
        import sniffio
    except ImportError:  # pragma: nocover
        environment = "asyncio"
    else:
        environment = sniffio.current_async_library()

    if environment not in ("asyncio", "trio"):  # pragma: nocover
        raise RuntimeError("Running under an unsupported async environment.")

    if environment == "asyncio" and anyio is None:  # pragma: nocover
        raise RuntimeError(
            "Running with asyncio requires installation of 'httpcore[asyncio]'."
        )

    if environment == "trio" and trio is None:  # pragma: nocover
        raise RuntimeError(
            "Running with trio requires installation of 'httpcore[trio]'."
        )

    return environment


class AsyncLock:
    """
    This is a standard lock.

    In the sync case `Lock` provides thread locking.
    In the async case `AsyncLock` provides async locking.
    """

    def __init__(self) -> None:
        self._backend = ""

    def setup(self) -> None:
        """
        Detect if we're running under 'asyncio' or 'trio' and create
        a lock with the correct implementation.
        """
        self._backend = current_async_library()
        if self._backend == "trio":
            self._trio_lock = trio.Lock()
        elif self._backend == "asyncio":
            self._anyio_lock = anyio.Lock()

    async def __aenter__(self) -> AsyncLock:
        if not self._backend:
            self.setup()

        if self._backend == "trio":
            await self._trio_lock.acquire()
        elif self._backend == "asyncio":
            await self._anyio_lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        if self._backend == "trio":
            self._trio_lock.release()
        elif self._backend == "asyncio":
            self._anyio_lock.release()


class AsyncThreadLock:
    """
    This is a threading-only lock for no-I/O contexts.

    In the sync case `ThreadLock` provides thread locking.
    In the async case `AsyncThreadLock` is a no-op.
    """

    def __enter__(self) -> AsyncThreadLock:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        pass


class AsyncEvent:
    def __init__(self) -> None:
        self._backend = ""

    def setup(self) -> None:
        """
        Detect if we're running under 'asyncio' or 'trio' and create
        a lock with the correct implementation.
        """
        self._backend = current_async_library()
        if self._backend == "trio":
            self._trio_event = trio.Event()
        elif self._backend == "asyncio":
            self._anyio_event = anyio.Event()

    def set(self) -> None:
        if not self._backend:
            self.setup()

        if self._backend == "trio":
            self._trio_event.set()
        elif self._backend == "asyncio":
            self._anyio_event.set()

    async def wait(self, timeout: float | None = None) -> None:
        if not self._backend:
            self.setup()

        if self._backend == "trio":
            trio_exc_map: ExceptionMapping = {trio.TooSlowError: PoolTimeout}
            timeout_or_inf = float("inf") if timeout is None else timeout
            with map_exceptions(trio_exc_map):
                with trio.fail_after(timeout_or_inf):
                    await self._trio_event.wait()
        elif self._backend == "asyncio":
            anyio_exc_map: ExceptionMapping = {TimeoutError: PoolTimeout}
            with map_exceptions(anyio_exc_map):
                with anyio.fail_after(timeout):
                    await self._anyio_event.wait()


class AsyncSemaphore:
    def __init__(self, bound: int) -> None:
        self._bound = bound
        self._backend = ""

    def setup(self) -> None:
        """
        Detect if we're running under 'asyncio' or 'trio' and create
        a semaphore with the correct implementation.
        """
        self._backend = current_async_library()
        if self._backend == "trio":
            self._trio_semaphore = trio.Semaphore(
                initial_value=self._bound, max_value=self._bound
            )
        elif self._backend == "asyncio":
            self._anyio_semaphore = anyio.Semaphore(
                initial_value=self._bound, max_value=self._bound
            )

    async def acquire(self) -> None:
        if not self._backend:
            self.setup()

        if self._backend == "trio":
            await self._trio_semaphore.acquire()
        elif self._backend == "asyncio":
            await self._anyio_semaphore.acquire()

    async def release(self) -> None:
        if self._backend == "trio":
            self._trio_semaphore.release()
        elif self._backend == "asyncio":
            self._anyio_semaphore.release()


class AsyncShieldCancellation:
    # For certain portions of our codebase where we're dealing with
    # closing connections during exception handling we want to shield
    # the operation from being cancelled.
    #
    # with AsyncShieldCancellation():
    #     ... # clean-up operations, shielded from cancellation.

    def __init__(self) -> None:
        """
        Detect if we're running under 'asyncio' or 'trio' and create
        a shielded scope with the correct implementation.
        """
        self._backend = current_async_library()

        if self._backend == "trio":
            self._trio_shield = trio.CancelScope(shield=True)
        elif self._backend == "asyncio":
            self._anyio_shield = anyio.CancelScope(shield=True)

    def __enter__(self) -> AsyncShieldCancellation:
        if self._backend == "trio":
            self._trio_shield.__enter__()
        elif self._backend == "asyncio":
            self._anyio_shield.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        if self._backend == "trio":
            self._trio_shield.__exit__(exc_type, exc_value, traceback)
        elif self._backend == "asyncio":
            self._anyio_shield.__exit__(exc_type, exc_value, traceback)


# Our thread-based synchronization primitives...


class Lock:
    """
    This is a standard lock.

    In the sync case `Lock` provides thread locking.
    In the async case `AsyncLock` provides async locking.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def __enter__(self) -> Lock:
        self._lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self._lock.release()


class ThreadLock:
    """
    This is a threading-only lock for no-I/O contexts.

    In the sync case `ThreadLock` provides thread locking.
    In the async case `AsyncThreadLock` is a no-op.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def __enter__(self) -> ThreadLock:
        self._lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self._lock.release()


class Event:
    def __init__(self) -> None:
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def wait(self, timeout: float | None = None) -> None:
        if timeout == float("inf"):  # pragma: no cover
            timeout = None
        if not self._event.wait(timeout=timeout):
            raise PoolTimeout()  # pragma: nocover


class Semaphore:
    def __init__(self, bound: int) -> None:
        self._semaphore = threading.Semaphore(value=bound)

    def acquire(self) -> None:
        self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()


class ShieldCancellation:
    # Thread-synchronous codebases don't support cancellation semantics.
    # We have this class because we need to mirror the async and sync
    # cases within our package, but it's just a no-op.
    def __enter__(self) -> ShieldCancellation:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        pass

# === NexusCore/openenv\Lib\site-packages\jinja2\idtracking.py ===
import typing as t

from . import nodes
from .visitor import NodeVisitor

if t.TYPE_CHECKING:
    import typing_extensions as te

VAR_LOAD_PARAMETER = "param"
VAR_LOAD_RESOLVE = "resolve"
VAR_LOAD_ALIAS = "alias"
VAR_LOAD_UNDEFINED = "undefined"


def find_symbols(
    nodes: t.Iterable[nodes.Node], parent_symbols: t.Optional["Symbols"] = None
) -> "Symbols":
    sym = Symbols(parent=parent_symbols)
    visitor = FrameSymbolVisitor(sym)
    for node in nodes:
        visitor.visit(node)
    return sym


def symbols_for_node(
    node: nodes.Node, parent_symbols: t.Optional["Symbols"] = None
) -> "Symbols":
    sym = Symbols(parent=parent_symbols)
    sym.analyze_node(node)
    return sym


class Symbols:
    def __init__(
        self, parent: t.Optional["Symbols"] = None, level: t.Optional[int] = None
    ) -> None:
        if level is None:
            if parent is None:
                level = 0
            else:
                level = parent.level + 1

        self.level: int = level
        self.parent = parent
        self.refs: t.Dict[str, str] = {}
        self.loads: t.Dict[str, t.Any] = {}
        self.stores: t.Set[str] = set()

    def analyze_node(self, node: nodes.Node, **kwargs: t.Any) -> None:
        visitor = RootVisitor(self)
        visitor.visit(node, **kwargs)

    def _define_ref(
        self, name: str, load: t.Optional[t.Tuple[str, t.Optional[str]]] = None
    ) -> str:
        ident = f"l_{self.level}_{name}"
        self.refs[name] = ident
        if load is not None:
            self.loads[ident] = load
        return ident

    def find_load(self, target: str) -> t.Optional[t.Any]:
        if target in self.loads:
            return self.loads[target]

        if self.parent is not None:
            return self.parent.find_load(target)

        return None

    def find_ref(self, name: str) -> t.Optional[str]:
        if name in self.refs:
            return self.refs[name]

        if self.parent is not None:
            return self.parent.find_ref(name)

        return None

    def ref(self, name: str) -> str:
        rv = self.find_ref(name)
        if rv is None:
            raise AssertionError(
                "Tried to resolve a name to a reference that was"
                f" unknown to the frame ({name!r})"
            )
        return rv

    def copy(self) -> "te.Self":
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.refs = self.refs.copy()
        rv.loads = self.loads.copy()
        rv.stores = self.stores.copy()
        return rv

    def store(self, name: str) -> None:
        self.stores.add(name)

        # If we have not see the name referenced yet, we need to figure
        # out what to set it to.
        if name not in self.refs:
            # If there is a parent scope we check if the name has a
            # reference there.  If it does it means we might have to alias
            # to a variable there.
            if self.parent is not None:
                outer_ref = self.parent.find_ref(name)
                if outer_ref is not None:
                    self._define_ref(name, load=(VAR_LOAD_ALIAS, outer_ref))
                    return

            # Otherwise we can just set it to undefined.
            self._define_ref(name, load=(VAR_LOAD_UNDEFINED, None))

    def declare_parameter(self, name: str) -> str:
        self.stores.add(name)
        return self._define_ref(name, load=(VAR_LOAD_PARAMETER, None))

    def load(self, name: str) -> None:
        if self.find_ref(name) is None:
            self._define_ref(name, load=(VAR_LOAD_RESOLVE, name))

    def branch_update(self, branch_symbols: t.Sequence["Symbols"]) -> None:
        stores: t.Set[str] = set()

        for branch in branch_symbols:
            stores.update(branch.stores)

        stores.difference_update(self.stores)

        for sym in branch_symbols:
            self.refs.update(sym.refs)
            self.loads.update(sym.loads)
            self.stores.update(sym.stores)

        for name in stores:
            target = self.find_ref(name)
            assert target is not None, "should not happen"

            if self.parent is not None:
                outer_target = self.parent.find_ref(name)
                if outer_target is not None:
                    self.loads[target] = (VAR_LOAD_ALIAS, outer_target)
                    continue
            self.loads[target] = (VAR_LOAD_RESOLVE, name)

    def dump_stores(self) -> t.Dict[str, str]:
        rv: t.Dict[str, str] = {}
        node: t.Optional[Symbols] = self

        while node is not None:
            for name in sorted(node.stores):
                if name not in rv:
                    rv[name] = self.find_ref(name)  # type: ignore

            node = node.parent

        return rv

    def dump_param_targets(self) -> t.Set[str]:
        rv = set()
        node: t.Optional[Symbols] = self

        while node is not None:
            for target, (instr, _) in self.loads.items():
                if instr == VAR_LOAD_PARAMETER:
                    rv.add(target)

            node = node.parent

        return rv


class RootVisitor(NodeVisitor):
    def __init__(self, symbols: "Symbols") -> None:
        self.sym_visitor = FrameSymbolVisitor(symbols)

    def _simple_visit(self, node: nodes.Node, **kwargs: t.Any) -> None:
        for child in node.iter_child_nodes():
            self.sym_visitor.visit(child)

    visit_Template = _simple_visit
    visit_Block = _simple_visit
    visit_Macro = _simple_visit
    visit_FilterBlock = _simple_visit
    visit_Scope = _simple_visit
    visit_If = _simple_visit
    visit_ScopedEvalContextModifier = _simple_visit

    def visit_AssignBlock(self, node: nodes.AssignBlock, **kwargs: t.Any) -> None:
        for child in node.body:
            self.sym_visitor.visit(child)

    def visit_CallBlock(self, node: nodes.CallBlock, **kwargs: t.Any) -> None:
        for child in node.iter_child_nodes(exclude=("call",)):
            self.sym_visitor.visit(child)

    def visit_OverlayScope(self, node: nodes.OverlayScope, **kwargs: t.Any) -> None:
        for child in node.body:
            self.sym_visitor.visit(child)

    def visit_For(
        self, node: nodes.For, for_branch: str = "body", **kwargs: t.Any
    ) -> None:
        if for_branch == "body":
            self.sym_visitor.visit(node.target, store_as_param=True)
            branch = node.body
        elif for_branch == "else":
            branch = node.else_
        elif for_branch == "test":
            self.sym_visitor.visit(node.target, store_as_param=True)
            if node.test is not None:
                self.sym_visitor.visit(node.test)
            return
        else:
            raise RuntimeError("Unknown for branch")

        if branch:
            for item in branch:
                self.sym_visitor.visit(item)

    def visit_With(self, node: nodes.With, **kwargs: t.Any) -> None:
        for target in node.targets:
            self.sym_visitor.visit(target)
        for child in node.body:
            self.sym_visitor.visit(child)

    def generic_visit(self, node: nodes.Node, *args: t.Any, **kwargs: t.Any) -> None:
        raise NotImplementedError(f"Cannot find symbols for {type(node).__name__!r}")


class FrameSymbolVisitor(NodeVisitor):
    """A visitor for `Frame.inspect`."""

    def __init__(self, symbols: "Symbols") -> None:
        self.symbols = symbols

    def visit_Name(
        self, node: nodes.Name, store_as_param: bool = False, **kwargs: t.Any
    ) -> None:
        """All assignments to names go through this function."""
        if store_as_param or node.ctx == "param":
            self.symbols.declare_parameter(node.name)
        elif node.ctx == "store":
            self.symbols.store(node.name)
        elif node.ctx == "load":
            self.symbols.load(node.name)

    def visit_NSRef(self, node: nodes.NSRef, **kwargs: t.Any) -> None:
        self.symbols.load(node.name)

    def visit_If(self, node: nodes.If, **kwargs: t.Any) -> None:
        self.visit(node.test, **kwargs)
        original_symbols = self.symbols

        def inner_visit(nodes: t.Iterable[nodes.Node]) -> "Symbols":
            self.symbols = rv = original_symbols.copy()

            for subnode in nodes:
                self.visit(subnode, **kwargs)

            self.symbols = original_symbols
            return rv

        body_symbols = inner_visit(node.body)
        elif_symbols = inner_visit(node.elif_)
        else_symbols = inner_visit(node.else_ or ())
        self.symbols.branch_update([body_symbols, elif_symbols, else_symbols])

    def visit_Macro(self, node: nodes.Macro, **kwargs: t.Any) -> None:
        self.symbols.store(node.name)

    def visit_Import(self, node: nodes.Import, **kwargs: t.Any) -> None:
        self.generic_visit(node, **kwargs)
        self.symbols.store(node.target)

    def visit_FromImport(self, node: nodes.FromImport, **kwargs: t.Any) -> None:
        self.generic_visit(node, **kwargs)

        for name in node.names:
            if isinstance(name, tuple):
                self.symbols.store(name[1])
            else:
                self.symbols.store(name)

    def visit_Assign(self, node: nodes.Assign, **kwargs: t.Any) -> None:
        """Visit assignments in the correct order."""
        self.visit(node.node, **kwargs)
        self.visit(node.target, **kwargs)

    def visit_For(self, node: nodes.For, **kwargs: t.Any) -> None:
        """Visiting stops at for blocks.  However the block sequence
        is visited as part of the outer scope.
        """
        self.visit(node.iter, **kwargs)

    def visit_CallBlock(self, node: nodes.CallBlock, **kwargs: t.Any) -> None:
        self.visit(node.call, **kwargs)

    def visit_FilterBlock(self, node: nodes.FilterBlock, **kwargs: t.Any) -> None:
        self.visit(node.filter, **kwargs)

    def visit_With(self, node: nodes.With, **kwargs: t.Any) -> None:
        for target in node.values:
            self.visit(target)

    def visit_AssignBlock(self, node: nodes.AssignBlock, **kwargs: t.Any) -> None:
        """Stop visiting at block assigns."""
        self.visit(node.target, **kwargs)

    def visit_Scope(self, node: nodes.Scope, **kwargs: t.Any) -> None:
        """Stop visiting at scopes."""

    def visit_Block(self, node: nodes.Block, **kwargs: t.Any) -> None:
        """Stop visiting at blocks."""

    def visit_OverlayScope(self, node: nodes.OverlayScope, **kwargs: t.Any) -> None:
        """Do not visit into overlay scopes."""

# === NexusCore/openenv\Lib\site-packages\rich\panel.py ===
from typing import TYPE_CHECKING, Optional

from .align import AlignMethod
from .box import ROUNDED, Box
from .cells import cell_len
from .jupyter import JupyterMixin
from .measure import Measurement, measure_renderables
from .padding import Padding, PaddingDimensions
from .segment import Segment
from .style import Style, StyleType
from .text import Text, TextType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult


class Panel(JupyterMixin):
    """A console renderable that draws a border around its contents.

    Example:
        >>> console.print(Panel("Hello, World!"))

    Args:
        renderable (RenderableType): A console renderable object.
        box (Box, optional): A Box instance that defines the look of the border (see :ref:`appendix_box`. Defaults to box.ROUNDED.
        title (Optional[TextType], optional): Optional title displayed in panel header. Defaults to None.
        title_align (AlignMethod, optional): Alignment of title. Defaults to "center".
        subtitle (Optional[TextType], optional): Optional subtitle displayed in panel footer. Defaults to None.
        subtitle_align (AlignMethod, optional): Alignment of subtitle. Defaults to "center".
        safe_box (bool, optional): Disable box characters that don't display on windows legacy terminal with *raster* fonts. Defaults to True.
        expand (bool, optional): If True the panel will stretch to fill the console width, otherwise it will be sized to fit the contents. Defaults to True.
        style (str, optional): The style of the panel (border and contents). Defaults to "none".
        border_style (str, optional): The style of the border. Defaults to "none".
        width (Optional[int], optional): Optional width of panel. Defaults to None to auto-detect.
        height (Optional[int], optional): Optional height of panel. Defaults to None to auto-detect.
        padding (Optional[PaddingDimensions]): Optional padding around renderable. Defaults to 0.
        highlight (bool, optional): Enable automatic highlighting of panel title (if str). Defaults to False.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        expand: bool = True,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> None:
        self.renderable = renderable
        self.box = box
        self.title = title
        self.title_align: AlignMethod = title_align
        self.subtitle = subtitle
        self.subtitle_align = subtitle_align
        self.safe_box = safe_box
        self.expand = expand
        self.style = style
        self.border_style = border_style
        self.width = width
        self.height = height
        self.padding = padding
        self.highlight = highlight

    @classmethod
    def fit(
        cls,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> "Panel":
        """An alternative constructor that sets expand=False."""
        return cls(
            renderable,
            box,
            title=title,
            title_align=title_align,
            subtitle=subtitle,
            subtitle_align=subtitle_align,
            safe_box=safe_box,
            style=style,
            border_style=border_style,
            width=width,
            height=height,
            padding=padding,
            highlight=highlight,
            expand=False,
        )

    @property
    def _title(self) -> Optional[Text]:
        if self.title:
            title_text = (
                Text.from_markup(self.title)
                if isinstance(self.title, str)
                else self.title.copy()
            )
            title_text.end = ""
            title_text.plain = title_text.plain.replace("\n", " ")
            title_text.no_wrap = True
            title_text.expand_tabs()
            title_text.pad(1)
            return title_text
        return None

    @property
    def _subtitle(self) -> Optional[Text]:
        if self.subtitle:
            subtitle_text = (
                Text.from_markup(self.subtitle)
                if isinstance(self.subtitle, str)
                else self.subtitle.copy()
            )
            subtitle_text.end = ""
            subtitle_text.plain = subtitle_text.plain.replace("\n", " ")
            subtitle_text.no_wrap = True
            subtitle_text.expand_tabs()
            subtitle_text.pad(1)
            return subtitle_text
        return None

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        _padding = Padding.unpack(self.padding)
        renderable = (
            Padding(self.renderable, _padding) if any(_padding) else self.renderable
        )
        style = console.get_style(self.style)
        partial_border_style = console.get_style(self.border_style)
        border_style = style + partial_border_style
        width = (
            options.max_width
            if self.width is None
            else min(options.max_width, self.width)
        )

        safe_box: bool = console.safe_box if self.safe_box is None else self.safe_box
        box = self.box.substitute(options, safe=safe_box)

        def align_text(
            text: Text, width: int, align: str, character: str, style: Style
        ) -> Text:
            """Gets new aligned text.

            Args:
                text (Text): Title or subtitle text.
                width (int): Desired width.
                align (str): Alignment.
                character (str): Character for alignment.
                style (Style): Border style

            Returns:
                Text: New text instance
            """
            text = text.copy()
            text.truncate(width)
            excess_space = width - cell_len(text.plain)
            if text.style:
                text.stylize(console.get_style(text.style))

            if excess_space:
                if align == "left":
                    return Text.assemble(
                        text,
                        (character * excess_space, style),
                        no_wrap=True,
                        end="",
                    )
                elif align == "center":
                    left = excess_space // 2
                    return Text.assemble(
                        (character * left, style),
                        text,
                        (character * (excess_space - left), style),
                        no_wrap=True,
                        end="",
                    )
                else:
                    return Text.assemble(
                        (character * excess_space, style),
                        text,
                        no_wrap=True,
                        end="",
                    )
            return text

        title_text = self._title
        if title_text is not None:
            title_text.stylize_before(partial_border_style)

        child_width = (
            width - 2
            if self.expand
            else console.measure(
                renderable, options=options.update_width(width - 2)
            ).maximum
        )
        child_height = self.height or options.height or None
        if child_height:
            child_height -= 2
        if title_text is not None:
            child_width = min(
                options.max_width - 2, max(child_width, title_text.cell_len + 2)
            )

        width = child_width + 2
        child_options = options.update(
            width=child_width, height=child_height, highlight=self.highlight
        )
        lines = console.render_lines(renderable, child_options, style=style)

        line_start = Segment(box.mid_left, border_style)
        line_end = Segment(f"{box.mid_right}", border_style)
        new_line = Segment.line()
        if title_text is None or width <= 4:
            yield Segment(box.get_top([width - 2]), border_style)
        else:
            title_text = align_text(
                title_text,
                width - 4,
                self.title_align,
                box.top,
                border_style,
            )
            yield Segment(box.top_left + box.top, border_style)
            yield from console.render(title_text, child_options.update_width(width - 4))
            yield Segment(box.top + box.top_right, border_style)

        yield new_line
        for line in lines:
            yield line_start
            yield from line
            yield line_end
            yield new_line

        subtitle_text = self._subtitle
        if subtitle_text is not None:
            subtitle_text.stylize_before(partial_border_style)

        if subtitle_text is None or width <= 4:
            yield Segment(box.get_bottom([width - 2]), border_style)
        else:
            subtitle_text = align_text(
                subtitle_text,
                width - 4,
                self.subtitle_align,
                box.bottom,
                border_style,
            )
            yield Segment(box.bottom_left + box.bottom, border_style)
            yield from console.render(
                subtitle_text, child_options.update_width(width - 4)
            )
            yield Segment(box.bottom + box.bottom_right, border_style)

        yield new_line

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _title = self._title
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        renderables = [self.renderable, _title] if _title else [self.renderable]

        if self.width is None:
            width = (
                measure_renderables(
                    console,
                    options.update_width(options.max_width - padding - 2),
                    renderables,
                ).maximum
                + padding
                + 2
            )
        else:
            width = self.width
        return Measurement(width, width)


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    c = Console()

    from .box import DOUBLE, ROUNDED
    from .padding import Padding

    p = Panel(
        "Hello, World!",
        title="rich.Panel",
        style="white on blue",
        box=DOUBLE,
        padding=1,
    )

    c.print()
    c.print(p)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\completion\handler.py ===
import json
from typing import Callable, List, Optional, Union

from openai import AsyncOpenAI, OpenAI

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.llms.base import BaseLLM
from litellm.types.llms.openai import AllMessageValues, OpenAITextCompletionUserMessage
from litellm.types.utils import LlmProviders, ModelResponse, TextCompletionResponse
from litellm.utils import ProviderConfigManager

from ..common_utils import OpenAIError
from .transformation import OpenAITextCompletionConfig


class OpenAITextCompletion(BaseLLM):
    openai_text_completion_global_config = OpenAITextCompletionConfig()

    def __init__(self) -> None:
        super().__init__()

    def validate_environment(self, api_key):
        headers = {
            "content-type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def completion(
        self,
        model_response: ModelResponse,
        api_key: str,
        model: str,
        messages: Union[List[AllMessageValues], List[OpenAITextCompletionUserMessage]],
        timeout: float,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        print_verbose: Optional[Callable] = None,
        api_base: Optional[str] = None,
        acompletion: bool = False,
        litellm_params=None,
        logger_fn=None,
        client=None,
        organization: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        try:
            if headers is None:
                headers = self.validate_environment(api_key=api_key)
            if model is None or messages is None:
                raise OpenAIError(status_code=422, message="Missing model or messages")

            # don't send max retries to the api, if set

            provider_config = ProviderConfigManager.get_provider_text_completion_config(
                model=model,
                provider=LlmProviders(custom_llm_provider),
            )

            data = provider_config.transform_text_completion_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                headers=headers,
            )
            max_retries = data.pop("max_retries", 2)
            ## LOGGING
            logging_obj.pre_call(
                input=messages,
                api_key=api_key,
                additional_args={
                    "headers": headers,
                    "api_base": api_base,
                    "complete_input_dict": data,
                },
            )
            if acompletion is True:
                if optional_params.get("stream", False):
                    return self.async_streaming(
                        logging_obj=logging_obj,
                        api_base=api_base,
                        api_key=api_key,
                        data=data,
                        headers=headers,
                        model_response=model_response,
                        model=model,
                        timeout=timeout,
                        max_retries=max_retries,
                        client=client,
                        organization=organization,
                    )
                else:
                    return self.acompletion(api_base=api_base, data=data, headers=headers, model_response=model_response, api_key=api_key, logging_obj=logging_obj, model=model, timeout=timeout, max_retries=max_retries, organization=organization, client=client)  # type: ignore
            elif optional_params.get("stream", False):
                return self.streaming(
                    logging_obj=logging_obj,
                    api_base=api_base,
                    api_key=api_key,
                    data=data,
                    headers=headers,
                    model_response=model_response,
                    model=model,
                    timeout=timeout,
                    max_retries=max_retries,  # type: ignore
                    client=client,
                    organization=organization,
                )
            else:
                if client is None:
                    openai_client = OpenAI(
                        api_key=api_key,
                        base_url=api_base,
                        http_client=litellm.client_session,
                        timeout=timeout,
                        max_retries=max_retries,  # type: ignore
                        organization=organization,
                    )
                else:
                    openai_client = client

                raw_response = openai_client.completions.with_raw_response.create(**data)  # type: ignore
                response = raw_response.parse()
                response_json = response.model_dump()

                ## LOGGING
                logging_obj.post_call(
                    api_key=api_key,
                    original_response=response_json,
                    additional_args={
                        "headers": headers,
                        "api_base": api_base,
                    },
                )

                ## RESPONSE OBJECT
                return TextCompletionResponse(**response_json)
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

    async def acompletion(
        self,
        logging_obj,
        api_base: str,
        data: dict,
        headers: dict,
        model_response: ModelResponse,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        organization: Optional[str] = None,
        client=None,
    ):
        try:
            if client is None:
                openai_aclient = AsyncOpenAI(
                    api_key=api_key,
                    base_url=api_base,
                    http_client=litellm.aclient_session,
                    timeout=timeout,
                    max_retries=max_retries,
                    organization=organization,
                )
            else:
                openai_aclient = client

            raw_response = await openai_aclient.completions.with_raw_response.create(
                **data
            )
            response = raw_response.parse()
            response_json = response.model_dump()

            ## LOGGING
            logging_obj.post_call(
                api_key=api_key,
                original_response=response,
                additional_args={
                    "headers": headers,
                    "api_base": api_base,
                },
            )
            ## RESPONSE OBJECT
            response_obj = TextCompletionResponse(**response_json)
            response_obj._hidden_params.original_response = json.dumps(response_json)
            return response_obj
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

    def streaming(
        self,
        logging_obj,
        api_key: str,
        data: dict,
        headers: dict,
        model_response: ModelResponse,
        model: str,
        timeout: float,
        api_base: Optional[str] = None,
        max_retries=None,
        client=None,
        organization=None,
    ):
        if client is None:
            openai_client = OpenAI(
                api_key=api_key,
                base_url=api_base,
                http_client=litellm.client_session,
                timeout=timeout,
                max_retries=max_retries,  # type: ignore
                organization=organization,
            )
        else:
            openai_client = client

        try:
            raw_response = openai_client.completions.with_raw_response.create(**data)
            response = raw_response.parse()
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )
        streamwrapper = CustomStreamWrapper(
            completion_stream=response,
            model=model,
            custom_llm_provider="text-completion-openai",
            logging_obj=logging_obj,
            stream_options=data.get("stream_options", None),
        )

        try:
            for chunk in streamwrapper:
                yield chunk
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

    async def async_streaming(
        self,
        logging_obj,
        api_key: str,
        data: dict,
        headers: dict,
        model_response: ModelResponse,
        model: str,
        timeout: float,
        max_retries: int,
        api_base: Optional[str] = None,
        client=None,
        organization=None,
    ):
        if client is None:
            openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_base,
                http_client=litellm.aclient_session,
                timeout=timeout,
                max_retries=max_retries,
                organization=organization,
            )
        else:
            openai_client = client

        raw_response = await openai_client.completions.with_raw_response.create(**data)
        response = raw_response.parse()
        streamwrapper = CustomStreamWrapper(
            completion_stream=response,
            model=model,
            custom_llm_provider="text-completion-openai",
            logging_obj=logging_obj,
            stream_options=data.get("stream_options", None),
        )

        try:
            async for transformed_chunk in streamwrapper:
                yield transformed_chunk
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )