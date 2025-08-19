
# === NexusCore/tools\exports\export_20250803_114325\combined_176.py ===

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\transports\rest.py ===
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

from google.ai.generativelanguage_v1beta.types import discuss_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import DiscussServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class DiscussServiceRestInterceptor:
    """Interceptor for DiscussService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the DiscussServiceRestTransport.

    .. code-block:: python
        class MyCustomDiscussServiceInterceptor(DiscussServiceRestInterceptor):
            def pre_count_message_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_message_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_message(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_message(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = DiscussServiceRestTransport(interceptor=MyCustomDiscussServiceInterceptor())
        client = DiscussServiceClient(transport=transport)


    """

    def pre_count_message_tokens(
        self,
        request: discuss_service.CountMessageTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.CountMessageTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_count_message_tokens(
        self, response: discuss_service.CountMessageTokensResponse
    ) -> discuss_service.CountMessageTokensResponse:
        """Post-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_message(
        self,
        request: discuss_service.GenerateMessageRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.GenerateMessageRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_message

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_generate_message(
        self, response: discuss_service.GenerateMessageResponse
    ) -> discuss_service.GenerateMessageResponse:
        """Post-rpc interceptor for generate_message

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class DiscussServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: DiscussServiceRestInterceptor


class DiscussServiceRestTransport(DiscussServiceTransport):
    """REST backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

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
        interceptor: Optional[DiscussServiceRestInterceptor] = None,
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
        self._interceptor = interceptor or DiscussServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CountMessageTokens(DiscussServiceRestStub):
        def __hash__(self):
            return hash("CountMessageTokens")

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
            request: discuss_service.CountMessageTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.CountMessageTokensResponse:
            r"""Call the count message tokens method over HTTP.

            Args:
                request (~.discuss_service.CountMessageTokensRequest):
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
                ~.discuss_service.CountMessageTokensResponse:
                    A response from ``CountMessageTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:countMessageTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_message_tokens(
                request, metadata
            )
            pb_request = discuss_service.CountMessageTokensRequest.pb(request)
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
            resp = discuss_service.CountMessageTokensResponse()
            pb_resp = discuss_service.CountMessageTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_message_tokens(resp)
            return resp

    class _GenerateMessage(DiscussServiceRestStub):
        def __hash__(self):
            return hash("GenerateMessage")

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
            request: discuss_service.GenerateMessageRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.GenerateMessageResponse:
            r"""Call the generate message method over HTTP.

            Args:
                request (~.discuss_service.GenerateMessageRequest):
                    The request object. Request to generate a message
                response from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.discuss_service.GenerateMessageResponse:
                    The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:generateMessage",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_message(
                request, metadata
            )
            pb_request = discuss_service.GenerateMessageRequest.pb(request)
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
            resp = discuss_service.GenerateMessageResponse()
            pb_resp = discuss_service.GenerateMessageResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_message(resp)
            return resp

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountMessageTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateMessage(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("DiscussServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\transports\rest.py ===
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

from google.ai.generativelanguage_v1beta3.types import discuss_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import DiscussServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class DiscussServiceRestInterceptor:
    """Interceptor for DiscussService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the DiscussServiceRestTransport.

    .. code-block:: python
        class MyCustomDiscussServiceInterceptor(DiscussServiceRestInterceptor):
            def pre_count_message_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_message_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_message(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_message(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = DiscussServiceRestTransport(interceptor=MyCustomDiscussServiceInterceptor())
        client = DiscussServiceClient(transport=transport)


    """

    def pre_count_message_tokens(
        self,
        request: discuss_service.CountMessageTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.CountMessageTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_count_message_tokens(
        self, response: discuss_service.CountMessageTokensResponse
    ) -> discuss_service.CountMessageTokensResponse:
        """Post-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_message(
        self,
        request: discuss_service.GenerateMessageRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.GenerateMessageRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_message

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_generate_message(
        self, response: discuss_service.GenerateMessageResponse
    ) -> discuss_service.GenerateMessageResponse:
        """Post-rpc interceptor for generate_message

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class DiscussServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: DiscussServiceRestInterceptor


class DiscussServiceRestTransport(DiscussServiceTransport):
    """REST backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

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
        interceptor: Optional[DiscussServiceRestInterceptor] = None,
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
        self._interceptor = interceptor or DiscussServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CountMessageTokens(DiscussServiceRestStub):
        def __hash__(self):
            return hash("CountMessageTokens")

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
            request: discuss_service.CountMessageTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.CountMessageTokensResponse:
            r"""Call the count message tokens method over HTTP.

            Args:
                request (~.discuss_service.CountMessageTokensRequest):
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
                ~.discuss_service.CountMessageTokensResponse:
                    A response from ``CountMessageTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:countMessageTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_message_tokens(
                request, metadata
            )
            pb_request = discuss_service.CountMessageTokensRequest.pb(request)
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
            resp = discuss_service.CountMessageTokensResponse()
            pb_resp = discuss_service.CountMessageTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_message_tokens(resp)
            return resp

    class _GenerateMessage(DiscussServiceRestStub):
        def __hash__(self):
            return hash("GenerateMessage")

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
            request: discuss_service.GenerateMessageRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.GenerateMessageResponse:
            r"""Call the generate message method over HTTP.

            Args:
                request (~.discuss_service.GenerateMessageRequest):
                    The request object. Request to generate a message
                response from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.discuss_service.GenerateMessageResponse:
                    The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:generateMessage",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_message(
                request, metadata
            )
            pb_request = discuss_service.GenerateMessageRequest.pb(request)
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
            resp = discuss_service.GenerateMessageResponse()
            pb_resp = discuss_service.GenerateMessageResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_message(resp)
            return resp

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountMessageTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateMessage(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("DiscussServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\parse\stanford.py ===
# Natural Language Toolkit: Interface to the Stanford Parser
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile
import warnings
from subprocess import PIPE

from nltk.internals import (
    _java_options,
    config_java,
    find_jar_iter,
    find_jars_within_path,
    java,
)
from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.tree import Tree

_stanford_url = "https://nlp.stanford.edu/software/lex-parser.shtml"


class GenericStanfordParser(ParserI):
    """Interface to the Stanford Parser"""

    _MODEL_JAR_PATTERN = r"stanford-parser-(\d+)(\.(\d+))+-models\.jar"
    _JAR = r"stanford-parser\.jar"
    _MAIN_CLASS = "edu.stanford.nlp.parser.lexparser.LexicalizedParser"

    _USE_STDIN = False
    _DOUBLE_SPACED_OUTPUT = False

    def __init__(
        self,
        path_to_jar=None,
        path_to_models_jar=None,
        model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
        encoding="utf8",
        verbose=False,
        java_options="-mx4g",
        corenlp_options="",
    ):
        # find the most recent code and model jar
        stanford_jar = max(
            find_jar_iter(
                self._JAR,
                path_to_jar,
                env_vars=("STANFORD_PARSER", "STANFORD_CORENLP"),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
                is_regex=True,
            ),
            key=lambda model_path: os.path.dirname(model_path),
        )

        model_jar = max(
            find_jar_iter(
                self._MODEL_JAR_PATTERN,
                path_to_models_jar,
                env_vars=("STANFORD_MODELS", "STANFORD_CORENLP"),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
                is_regex=True,
            ),
            key=lambda model_path: os.path.dirname(model_path),
        )

        # self._classpath = (stanford_jar, model_jar)

        # Adding logging jar files to classpath
        stanford_dir = os.path.split(stanford_jar)[0]
        self._classpath = tuple([model_jar] + find_jars_within_path(stanford_dir))

        self.model_path = model_path
        self._encoding = encoding
        self.corenlp_options = corenlp_options
        self.java_options = java_options

    def _parse_trees_output(self, output_):
        res = []
        cur_lines = []
        cur_trees = []
        blank = False
        for line in output_.splitlines(False):
            if line == "":
                if blank:
                    res.append(iter(cur_trees))
                    cur_trees = []
                    blank = False
                elif self._DOUBLE_SPACED_OUTPUT:
                    cur_trees.append(self._make_tree("\n".join(cur_lines)))
                    cur_lines = []
                    blank = True
                else:
                    res.append(iter([self._make_tree("\n".join(cur_lines))]))
                    cur_lines = []
            else:
                cur_lines.append(line)
                blank = False
        return iter(res)

    def parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list where each sentence is a list of words.
        Each sentence will be automatically tagged with this StanfordParser instance's
        tagger.
        If whitespaces exists inside a token, then the token will be treated as
        separate tokens.

        :param sentences: Input sentences to parse
        :type sentences: list(list(str))
        :rtype: iter(iter(Tree))
        """
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
            "-tokenized",
            "-escaper",
            "edu.stanford.nlp.process.PTBEscapingProcessor",
        ]
        return self._parse_trees_output(
            self._execute(
                cmd, "\n".join(" ".join(sentence) for sentence in sentences), verbose
            )
        )

    def raw_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a string;
        before parsing, it will be automatically tokenized and tagged by
        the Stanford Parser.

        :param sentence: Input sentence to parse
        :type sentence: str
        :rtype: iter(Tree)
        """
        return next(self.raw_parse_sents([sentence], verbose))

    def raw_parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list of strings.
        Each sentence will be automatically tokenized and tagged by the Stanford Parser.

        :param sentences: Input sentences to parse
        :type sentences: list(str)
        :rtype: iter(iter(Tree))
        """
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
        ]
        return self._parse_trees_output(
            self._execute(cmd, "\n".join(sentences), verbose)
        )

    def tagged_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized and
        tagged.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :rtype: iter(Tree)
        """
        return next(self.tagged_parse_sents([sentence], verbose))

    def tagged_parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences
        where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentences: list(list(tuple(str, str)))
        :rtype: iter(iter(Tree))
        """
        tag_separator = "/"
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
            "-tokenized",
            "-tagSeparator",
            tag_separator,
            "-tokenizerFactory",
            "edu.stanford.nlp.process.WhitespaceTokenizer",
            "-tokenizerMethod",
            "newCoreLabelTokenizerFactory",
        ]
        # We don't need to escape slashes as "splitting is done on the last instance of the character in the token"
        return self._parse_trees_output(
            self._execute(
                cmd,
                "\n".join(
                    " ".join(tag_separator.join(tagged) for tagged in sentence)
                    for sentence in sentences
                ),
                verbose,
            )
        )

    def _execute(self, cmd, input_, verbose=False):
        encoding = self._encoding
        cmd.extend(["-encoding", encoding])
        if self.corenlp_options:
            cmd.extend(self.corenlp_options.split())

        default_options = " ".join(_java_options)

        # Configure java.
        config_java(options=self.java_options, verbose=verbose)

        # Windows is incompatible with NamedTemporaryFile() without passing in delete=False.
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as input_file:
            # Write the actual sentences to the temporary input file
            if isinstance(input_, str) and encoding:
                input_ = input_.encode(encoding)
            input_file.write(input_)
            input_file.flush()

            # Run the tagger and get the output.
            if self._USE_STDIN:
                input_file.seek(0)
                stdout, stderr = java(
                    cmd,
                    classpath=self._classpath,
                    stdin=input_file,
                    stdout=PIPE,
                    stderr=PIPE,
                )
            else:
                cmd.append(input_file.name)
                stdout, stderr = java(
                    cmd, classpath=self._classpath, stdout=PIPE, stderr=PIPE
                )

            stdout = stdout.replace(b"\xc2\xa0", b" ")
            stdout = stdout.replace(b"\x00\xa0", b" ")
            stdout = stdout.decode(encoding)

        os.unlink(input_file.name)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout


class StanfordParser(GenericStanfordParser):
    """
    >>> parser=StanfordParser(
    ...     model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"
    ... ) # doctest: +SKIP

    >>> list(parser.raw_parse("the quick brown fox jumps over the lazy dog")) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('NP', [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('NP', [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']),
    Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.raw_parse_sents((
    ...     "the quick brown fox jumps over the lazy dog",
    ...     "the quick grey wolf jumps over the lazy fox"
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('NP', [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('NP', [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']),
    Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])])])]), Tree('ROOT', [Tree('NP',
    [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['grey']), Tree('NN', ['wolf'])]), Tree('NP',
    [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']), Tree('NP', [Tree('DT', ['the']),
    Tree('JJ', ['lazy']), Tree('NN', ['fox'])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('S', [Tree('NP', [Tree('PRP', ['I'])]), Tree('VP', [Tree('VBP', ["'m"]),
    Tree('NP', [Tree('DT', ['a']), Tree('NN', ['dog'])])])])]), Tree('ROOT', [Tree('S', [Tree('NP',
    [Tree('DT', ['This'])]), Tree('VP', [Tree('VBZ', ['is']), Tree('NP', [Tree('NP', [Tree('NP', [Tree('PRP$', ['my']),
    Tree('NNS', ['friends']), Tree('POS', ["'"])]), Tree('NN', ['cat'])]), Tree('PRN', [Tree('-LRB-', [Tree('', []),
    Tree('NP', [Tree('DT', ['the']), Tree('NN', ['tabby'])]), Tree('-RRB-', [])])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.tagged_parse_sents((
    ...     (
    ...         ("The", "DT"),
    ...         ("quick", "JJ"),
    ...         ("brown", "JJ"),
    ...         ("fox", "NN"),
    ...         ("jumped", "VBD"),
    ...         ("over", "IN"),
    ...         ("the", "DT"),
    ...         ("lazy", "JJ"),
    ...         ("dog", "NN"),
    ...         (".", "."),
    ...     ),
    ... ))],[]) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('S', [Tree('NP', [Tree('DT', ['The']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('VP', [Tree('VBD', ['jumped']), Tree('PP', [Tree('IN', ['over']), Tree('NP',
    [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])]), Tree('.', ['.'])])])]
    """

    _OUTPUT_FORMAT = "penn"

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)

    def _make_tree(self, result):
        return Tree.fromstring(result)


class StanfordDependencyParser(GenericStanfordParser):
    """
    >>> dep_parser=StanfordDependencyParser(
    ...     model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"
    ... ) # doctest: +SKIP

    >>> [parse.tree() for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy'])])]

    >>> [list(parse.triples()) for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumps', u'VBZ'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det', (u'The', u'DT')),
    ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'), u'amod', (u'brown', u'JJ')),
    ((u'jumps', u'VBZ'), u'nmod', (u'dog', u'NN')), ((u'dog', u'NN'), u'case', (u'over', u'IN')),
    ((u'dog', u'NN'), u'det', (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ'))]]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.raw_parse_sents((
    ...     "The quick brown fox jumps over the lazy dog.",
    ...     "The quick grey wolf jumps over the lazy fox."
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy'])]),
    Tree('jumps', [Tree('wolf', ['The', 'quick', 'grey']), Tree('fox', ['over', 'the', 'lazy'])])]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('dog', ['I', "'m", 'a']), Tree('cat', ['This', 'is', Tree('friends', ['my', "'"]), Tree('tabby', ['the'])])]

    >>> sum([[list(parse.triples()) for parse in dep_graphs] for dep_graphs in dep_parser.tagged_parse_sents((
    ...     (
    ...         ("The", "DT"),
    ...         ("quick", "JJ"),
    ...         ("brown", "JJ"),
    ...         ("fox", "NN"),
    ...         ("jumped", "VBD"),
    ...         ("over", "IN"),
    ...         ("the", "DT"),
    ...         ("lazy", "JJ"),
    ...         ("dog", "NN"),
    ...         (".", "."),
    ...     ),
    ... ))],[]) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumped', u'VBD'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det', (u'The', u'DT')),
    ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'), u'amod', (u'brown', u'JJ')),
    ((u'jumped', u'VBD'), u'nmod', (u'dog', u'NN')), ((u'dog', u'NN'), u'case', (u'over', u'IN')),
    ((u'dog', u'NN'), u'det', (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ'))]]

    """

    _OUTPUT_FORMAT = "conll2007"

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordDependencyParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPDependencyParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)

    def _make_tree(self, result):
        return DependencyGraph(result, top_relation_label="root")


class StanfordNeuralDependencyParser(GenericStanfordParser):
    """
    >>> from nltk.parse.stanford import StanfordNeuralDependencyParser # doctest: +SKIP
    >>> dep_parser=StanfordNeuralDependencyParser(java_options='-mx4g')# doctest: +SKIP

    >>> [parse.tree() for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy']), '.'])]

    >>> [list(parse.triples()) for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumps', u'VBZ'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det',
    (u'The', u'DT')), ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'),
    u'amod', (u'brown', u'JJ')), ((u'jumps', u'VBZ'), u'nmod', (u'dog', u'NN')),
    ((u'dog', u'NN'), u'case', (u'over', u'IN')), ((u'dog', u'NN'), u'det',
    (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ')), ((u'jumps', u'VBZ'),
    u'punct', (u'.', u'.'))]]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.raw_parse_sents((
    ...     "The quick brown fox jumps over the lazy dog.",
    ...     "The quick grey wolf jumps over the lazy fox."
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over',
    'the', 'lazy']), '.']), Tree('jumps', [Tree('wolf', ['The', 'quick', 'grey']),
    Tree('fox', ['over', 'the', 'lazy']), '.'])]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('dog', ['I', "'m", 'a']), Tree('cat', ['This', 'is', Tree('friends',
    ['my', "'"]), Tree('tabby', ['-LRB-', 'the', '-RRB-'])])]
    """

    _OUTPUT_FORMAT = "conll"
    _MAIN_CLASS = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
    _JAR = r"stanford-corenlp-(\d+)(\.(\d+))+\.jar"
    _MODEL_JAR_PATTERN = r"stanford-corenlp-(\d+)(\.(\d+))+-models\.jar"
    _USE_STDIN = True
    _DOUBLE_SPACED_OUTPUT = True

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordNeuralDependencyParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPDependencyParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)
        self.corenlp_options += "-annotators tokenize,ssplit,pos,depparse"

    def tagged_parse_sents(self, sentences, verbose=False):
        """
        Currently unimplemented because the neural dependency parser (and
        the StanfordCoreNLP pipeline class) doesn't support passing in pre-
        tagged tokens.
        """
        raise NotImplementedError(
            "tagged_parse[_sents] is not supported by "
            "StanfordNeuralDependencyParser; use "
            "parse[_sents] or raw_parse[_sents] instead."
        )

    def _make_tree(self, result):
        return DependencyGraph(result, top_relation_label="ROOT")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\rdf.py ===
"""
    pygments.lexers.rdf
    ~~~~~~~~~~~~~~~~~~~

    Lexers for semantic web and RDF query languages and markup.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, default
from pygments.token import Keyword, Punctuation, String, Number, Operator, \
    Generic, Whitespace, Name, Literal, Comment, Text

__all__ = ['SparqlLexer', 'TurtleLexer', 'ShExCLexer']


class SparqlLexer(RegexLexer):
    """
    Lexer for SPARQL query language.
    """
    name = 'SPARQL'
    aliases = ['sparql']
    filenames = ['*.rq', '*.sparql']
    mimetypes = ['application/sparql-query']
    url = 'https://www.w3.org/TR/sparql11-query'
    version_added = '2.0'

    # character group definitions ::

    PN_CHARS_BASE_GRP = ('a-zA-Z'
                         '\u00c0-\u00d6'
                         '\u00d8-\u00f6'
                         '\u00f8-\u02ff'
                         '\u0370-\u037d'
                         '\u037f-\u1fff'
                         '\u200c-\u200d'
                         '\u2070-\u218f'
                         '\u2c00-\u2fef'
                         '\u3001-\ud7ff'
                         '\uf900-\ufdcf'
                         '\ufdf0-\ufffd')

    PN_CHARS_U_GRP = (PN_CHARS_BASE_GRP + '_')

    PN_CHARS_GRP = (PN_CHARS_U_GRP +
                    r'\-' +
                    r'0-9' +
                    '\u00b7' +
                    '\u0300-\u036f' +
                    '\u203f-\u2040')

    HEX_GRP = '0-9A-Fa-f'

    PN_LOCAL_ESC_CHARS_GRP = r' _~.\-!$&"()*+,;=/?#@%'

    # terminal productions ::

    PN_CHARS_BASE = '[' + PN_CHARS_BASE_GRP + ']'

    PN_CHARS_U = '[' + PN_CHARS_U_GRP + ']'

    PN_CHARS = '[' + PN_CHARS_GRP + ']'

    HEX = '[' + HEX_GRP + ']'

    PN_LOCAL_ESC_CHARS = '[' + PN_LOCAL_ESC_CHARS_GRP + ']'

    IRIREF = r'<(?:[^<>"{}|^`\\\x00-\x20])*>'

    BLANK_NODE_LABEL = '_:[0-9' + PN_CHARS_U_GRP + '](?:[' + PN_CHARS_GRP + \
                       '.]*' + PN_CHARS + ')?'

    PN_PREFIX = PN_CHARS_BASE + '(?:[' + PN_CHARS_GRP + '.]*' + PN_CHARS + ')?'

    VARNAME = '[0-9' + PN_CHARS_U_GRP + '][' + PN_CHARS_U_GRP + \
              '0-9\u00b7\u0300-\u036f\u203f-\u2040]*'

    PERCENT = '%' + HEX + HEX

    PN_LOCAL_ESC = r'\\' + PN_LOCAL_ESC_CHARS

    PLX = '(?:' + PERCENT + ')|(?:' + PN_LOCAL_ESC + ')'

    PN_LOCAL = ('(?:[' + PN_CHARS_U_GRP + ':0-9' + ']|' + PLX + ')' +
                '(?:(?:[' + PN_CHARS_GRP + '.:]|' + PLX + ')*(?:[' +
                PN_CHARS_GRP + ':]|' + PLX + '))?')

    EXPONENT = r'[eE][+-]?\d+'

    # Lexer token definitions ::

    tokens = {
        'root': [
            (r'\s+', Text),
            # keywords ::
            (r'(?i)(select|construct|describe|ask|where|filter|group\s+by|minus|'
             r'distinct|reduced|from\s+named|from|order\s+by|desc|asc|limit|'
             r'offset|values|bindings|load|into|clear|drop|create|add|move|copy|'
             r'insert\s+data|delete\s+data|delete\s+where|with|delete|insert|'
             r'using\s+named|using|graph|default|named|all|optional|service|'
             r'silent|bind|undef|union|not\s+in|in|as|having|to|prefix|base)\b', Keyword),
            (r'(a)\b', Keyword),
            # IRIs ::
            ('(' + IRIREF + ')', Name.Label),
            # blank nodes ::
            ('(' + BLANK_NODE_LABEL + ')', Name.Label),
            #  # variables ::
            ('[?$]' + VARNAME, Name.Variable),
            # prefixed names ::
            (r'(' + PN_PREFIX + r')?(\:)(' + PN_LOCAL + r')?',
             bygroups(Name.Namespace, Punctuation, Name.Tag)),
            # function names ::
            (r'(?i)(str|lang|langmatches|datatype|bound|iri|uri|bnode|rand|abs|'
             r'ceil|floor|round|concat|strlen|ucase|lcase|encode_for_uri|'
             r'contains|strstarts|strends|strbefore|strafter|year|month|day|'
             r'hours|minutes|seconds|timezone|tz|now|uuid|struuid|md5|sha1|sha256|sha384|'
             r'sha512|coalesce|if|strlang|strdt|sameterm|isiri|isuri|isblank|'
             r'isliteral|isnumeric|regex|substr|replace|exists|not\s+exists|'
             r'count|sum|min|max|avg|sample|group_concat|separator)\b',
             Name.Function),
            # boolean literals ::
            (r'(true|false)', Keyword.Constant),
            # double literals ::
            (r'[+\-]?(\d+\.\d*' + EXPONENT + r'|\.?\d+' + EXPONENT + ')', Number.Float),
            # decimal literals ::
            (r'[+\-]?(\d+\.\d*|\.\d+)', Number.Float),
            # integer literals ::
            (r'[+\-]?\d+', Number.Integer),
            # operators ::
            (r'(\|\||&&|=|\*|\-|\+|/|!=|<=|>=|!|<|>)', Operator),
            # punctuation characters ::
            (r'[(){}.;,:^\[\]]', Punctuation),
            # line comments ::
            (r'#[^\n]*', Comment),
            # strings ::
            (r'"""', String, 'triple-double-quoted-string'),
            (r'"', String, 'single-double-quoted-string'),
            (r"'''", String, 'triple-single-quoted-string'),
            (r"'", String, 'single-single-quoted-string'),
        ],
        'triple-double-quoted-string': [
            (r'"""', String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-double-quoted-string': [
            (r'"', String, 'end-of-string'),
            (r'[^"\\\n]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'triple-single-quoted-string': [
            (r"'''", String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String.Escape, 'string-escape'),
        ],
        'single-single-quoted-string': [
            (r"'", String, 'end-of-string'),
            (r"[^'\\\n]+", String),
            (r'\\', String, 'string-escape'),
        ],
        'string-escape': [
            (r'u' + HEX + '{4}', String.Escape, '#pop'),
            (r'U' + HEX + '{8}', String.Escape, '#pop'),
            (r'.', String.Escape, '#pop'),
        ],
        'end-of-string': [
            (r'(@)([a-zA-Z]+(?:-[a-zA-Z0-9]+)*)',
             bygroups(Operator, Name.Function), '#pop:2'),
            (r'\^\^', Operator, '#pop:2'),
            default('#pop:2'),
        ],
    }


class TurtleLexer(RegexLexer):
    """
    Lexer for Turtle data language.
    """
    name = 'Turtle'
    aliases = ['turtle']
    filenames = ['*.ttl']
    mimetypes = ['text/turtle', 'application/x-turtle']
    url = 'https://www.w3.org/TR/turtle'
    version_added = '2.1'

    # character group definitions ::
    PN_CHARS_BASE_GRP = ('a-zA-Z'
                         '\u00c0-\u00d6'
                         '\u00d8-\u00f6'
                         '\u00f8-\u02ff'
                         '\u0370-\u037d'
                         '\u037f-\u1fff'
                         '\u200c-\u200d'
                         '\u2070-\u218f'
                         '\u2c00-\u2fef'
                         '\u3001-\ud7ff'
                         '\uf900-\ufdcf'
                         '\ufdf0-\ufffd')

    PN_CHARS_U_GRP = (PN_CHARS_BASE_GRP + '_')

    PN_CHARS_GRP = (PN_CHARS_U_GRP +
                    r'\-' +
                    r'0-9' +
                    '\u00b7' +
                    '\u0300-\u036f' +
                    '\u203f-\u2040')

    PN_CHARS = '[' + PN_CHARS_GRP + ']'

    PN_CHARS_BASE = '[' + PN_CHARS_BASE_GRP + ']'

    PN_PREFIX = PN_CHARS_BASE + '(?:[' + PN_CHARS_GRP + '.]*' + PN_CHARS + ')?'

    HEX_GRP = '0-9A-Fa-f'

    HEX = '[' + HEX_GRP + ']'

    PERCENT = '%' + HEX + HEX

    PN_LOCAL_ESC_CHARS_GRP = r' _~.\-!$&"()*+,;=/?#@%'

    PN_LOCAL_ESC_CHARS = '[' + PN_LOCAL_ESC_CHARS_GRP + ']'

    PN_LOCAL_ESC = r'\\' + PN_LOCAL_ESC_CHARS

    PLX = '(?:' + PERCENT + ')|(?:' + PN_LOCAL_ESC + ')'

    PN_LOCAL = ('(?:[' + PN_CHARS_U_GRP + ':0-9' + ']|' + PLX + ')' +
                '(?:(?:[' + PN_CHARS_GRP + '.:]|' + PLX + ')*(?:[' +
                PN_CHARS_GRP + ':]|' + PLX + '))?')

    patterns = {
        'PNAME_NS': r'((?:[a-zA-Z][\w-]*)?\:)',  # Simplified character range
        'IRIREF': r'(<[^<>"{}|^`\\\x00-\x20]*>)'
    }

    tokens = {
        'root': [
            (r'\s+', Text),

            # Base / prefix
            (r'(@base|BASE)(\s+){IRIREF}(\s*)(\.?)'.format(**patterns),
             bygroups(Keyword, Whitespace, Name.Variable, Whitespace,
                      Punctuation)),
            (r'(@prefix|PREFIX)(\s+){PNAME_NS}(\s+){IRIREF}(\s*)(\.?)'.format(**patterns),
             bygroups(Keyword, Whitespace, Name.Namespace, Whitespace,
                      Name.Variable, Whitespace, Punctuation)),

            # The shorthand predicate 'a'
            (r'(?<=\s)a(?=\s)', Keyword.Type),

            # IRIREF
            (r'{IRIREF}'.format(**patterns), Name.Variable),

            # PrefixedName
            (r'(' + PN_PREFIX + r')?(\:)(' + PN_LOCAL + r')?',
             bygroups(Name.Namespace, Punctuation, Name.Tag)),

            # BlankNodeLabel
            (r'(_)(:)([' + PN_CHARS_U_GRP + r'0-9]([' + PN_CHARS_GRP + r'.]*' + PN_CHARS + ')?)',
             bygroups(Name.Namespace, Punctuation, Name.Tag)),

            # Comment
            (r'#[^\n]+', Comment),

            (r'\b(true|false)\b', Literal),
            (r'[+\-]?\d*\.\d+', Number.Float),
            (r'[+\-]?\d*(:?\.\d+)?E[+\-]?\d+', Number.Float),
            (r'[+\-]?\d+', Number.Integer),
            (r'[\[\](){}.;,:^]', Punctuation),

            (r'"""', String, 'triple-double-quoted-string'),
            (r'"', String, 'single-double-quoted-string'),
            (r"'''", String, 'triple-single-quoted-string'),
            (r"'", String, 'single-single-quoted-string'),
        ],
        'triple-double-quoted-string': [
            (r'"""', String, 'end-of-string'),
            (r'[^\\]+(?=""")', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-double-quoted-string': [
            (r'"', String, 'end-of-string'),
            (r'[^"\\\n]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'triple-single-quoted-string': [
            (r"'''", String, 'end-of-string'),
            (r"[^\\]+(?=''')", String),
            (r'\\', String, 'string-escape'),
        ],
        'single-single-quoted-string': [
            (r"'", String, 'end-of-string'),
            (r"[^'\\\n]+", String),
            (r'\\', String, 'string-escape'),
        ],
        'string-escape': [
            (r'.', String, '#pop'),
        ],
        'end-of-string': [
            (r'(@)([a-zA-Z]+(?:-[a-zA-Z0-9]+)*)',
             bygroups(Operator, Generic.Emph), '#pop:2'),

            (r'(\^\^){IRIREF}'.format(**patterns), bygroups(Operator, Generic.Emph), '#pop:2'),

            default('#pop:2'),

        ],
    }

    # Turtle and Tera Term macro files share the same file extension
    # but each has a recognizable and distinct syntax.
    def analyse_text(text):
        for t in ('@base ', 'BASE ', '@prefix ', 'PREFIX '):
            if re.search(rf'^\s*{t}', text):
                return 0.80


class ShExCLexer(RegexLexer):
    """
    Lexer for ShExC shape expressions language syntax.
    """
    name = 'ShExC'
    aliases = ['shexc', 'shex']
    filenames = ['*.shex']
    mimetypes = ['text/shex']
    url = 'https://shex.io/shex-semantics/#shexc'
    version_added = ''

    # character group definitions ::

    PN_CHARS_BASE_GRP = ('a-zA-Z'
                         '\u00c0-\u00d6'
                         '\u00d8-\u00f6'
                         '\u00f8-\u02ff'
                         '\u0370-\u037d'
                         '\u037f-\u1fff'
                         '\u200c-\u200d'
                         '\u2070-\u218f'
                         '\u2c00-\u2fef'
                         '\u3001-\ud7ff'
                         '\uf900-\ufdcf'
                         '\ufdf0-\ufffd')

    PN_CHARS_U_GRP = (PN_CHARS_BASE_GRP + '_')

    PN_CHARS_GRP = (PN_CHARS_U_GRP +
                    r'\-' +
                    r'0-9' +
                    '\u00b7' +
                    '\u0300-\u036f' +
                    '\u203f-\u2040')

    HEX_GRP = '0-9A-Fa-f'

    PN_LOCAL_ESC_CHARS_GRP = r"_~.\-!$&'()*+,;=/?#@%"

    # terminal productions ::

    PN_CHARS_BASE = '[' + PN_CHARS_BASE_GRP + ']'

    PN_CHARS_U = '[' + PN_CHARS_U_GRP + ']'

    PN_CHARS = '[' + PN_CHARS_GRP + ']'

    HEX = '[' + HEX_GRP + ']'

    PN_LOCAL_ESC_CHARS = '[' + PN_LOCAL_ESC_CHARS_GRP + ']'

    UCHAR_NO_BACKSLASH = '(?:u' + HEX + '{4}|U' + HEX + '{8})'

    UCHAR = r'\\' + UCHAR_NO_BACKSLASH

    IRIREF = r'<(?:[^\x00-\x20<>"{}|^`\\]|' + UCHAR + ')*>'

    BLANK_NODE_LABEL = '_:[0-9' + PN_CHARS_U_GRP + '](?:[' + PN_CHARS_GRP + \
                       '.]*' + PN_CHARS + ')?'

    PN_PREFIX = PN_CHARS_BASE + '(?:[' + PN_CHARS_GRP + '.]*' + PN_CHARS + ')?'

    PERCENT = '%' + HEX + HEX

    PN_LOCAL_ESC = r'\\' + PN_LOCAL_ESC_CHARS

    PLX = '(?:' + PERCENT + ')|(?:' + PN_LOCAL_ESC + ')'

    PN_LOCAL = ('(?:[' + PN_CHARS_U_GRP + ':0-9' + ']|' + PLX + ')' +
                '(?:(?:[' + PN_CHARS_GRP + '.:]|' + PLX + ')*(?:[' +
                PN_CHARS_GRP + ':]|' + PLX + '))?')

    EXPONENT = r'[eE][+-]?\d+'

    # Lexer token definitions ::

    tokens = {
        'root': [
            (r'\s+', Text),
            # keywords ::
            (r'(?i)(base|prefix|start|external|'
             r'literal|iri|bnode|nonliteral|length|minlength|maxlength|'
             r'mininclusive|minexclusive|maxinclusive|maxexclusive|'
             r'totaldigits|fractiondigits|'
             r'closed|extra)\b', Keyword),
            (r'(a)\b', Keyword),
            # IRIs ::
            ('(' + IRIREF + ')', Name.Label),
            # blank nodes ::
            ('(' + BLANK_NODE_LABEL + ')', Name.Label),
            # prefixed names ::
            (r'(' + PN_PREFIX + r')?(\:)(' + PN_LOCAL + ')?',
             bygroups(Name.Namespace, Punctuation, Name.Tag)),
            # boolean literals ::
            (r'(true|false)', Keyword.Constant),
            # double literals ::
            (r'[+\-]?(\d+\.\d*' + EXPONENT + r'|\.?\d+' + EXPONENT + ')', Number.Float),
            # decimal literals ::
            (r'[+\-]?(\d+\.\d*|\.\d+)', Number.Float),
            # integer literals ::
            (r'[+\-]?\d+', Number.Integer),
            # operators ::
            (r'[@|$&=*+?^\-~]', Operator),
            # operator keywords ::
            (r'(?i)(and|or|not)\b', Operator.Word),
            # punctuation characters ::
            (r'[(){}.;,:^\[\]]', Punctuation),
            # line comments ::
            (r'#[^\n]*', Comment),
            # strings ::
            (r'"""', String, 'triple-double-quoted-string'),
            (r'"', String, 'single-double-quoted-string'),
            (r"'''", String, 'triple-single-quoted-string'),
            (r"'", String, 'single-single-quoted-string'),
        ],
        'triple-double-quoted-string': [
            (r'"""', String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-double-quoted-string': [
            (r'"', String, 'end-of-string'),
            (r'[^"\\\n]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'triple-single-quoted-string': [
            (r"'''", String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String.Escape, 'string-escape'),
        ],
        'single-single-quoted-string': [
            (r"'", String, 'end-of-string'),
            (r"[^'\\\n]+", String),
            (r'\\', String, 'string-escape'),
        ],
        'string-escape': [
            (UCHAR_NO_BACKSLASH, String.Escape, '#pop'),
            (r'.', String.Escape, '#pop'),
        ],
        'end-of-string': [
            (r'(@)([a-zA-Z]+(?:-[a-zA-Z0-9]+)*)',
             bygroups(Operator, Name.Function), '#pop:2'),
            (r'\^\^', Operator, '#pop:2'),
            default('#pop:2'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\config\pyprojecttoml.py ===
"""
Load setuptools configuration from ``pyproject.toml`` files.

**PRIVATE MODULE**: API reserved for setuptools internal usage only.

To read project metadata, consider using
``build.util.project_wheel_metadata`` (https://pypi.org/project/build/).
For simple scenarios, you can also try parsing the file directly
with the help of ``tomllib`` or ``tomli``.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from contextlib import contextmanager
from functools import partial
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable

from .._path import StrPath
from ..errors import FileError, InvalidConfigError
from ..warnings import SetuptoolsWarning
from . import expand as _expand
from ._apply_pyprojecttoml import _PREVIOUSLY_DEFINED, _MissingDynamic, apply as _apply

if TYPE_CHECKING:
    from typing_extensions import Self

    from setuptools.dist import Distribution

_logger = logging.getLogger(__name__)


def load_file(filepath: StrPath) -> dict:
    from ..compat.py310 import tomllib

    with open(filepath, "rb") as file:
        return tomllib.load(file)


def validate(config: dict, filepath: StrPath) -> bool:
    from . import _validate_pyproject as validator

    trove_classifier = validator.FORMAT_FUNCTIONS.get("trove-classifier")
    if hasattr(trove_classifier, "_disable_download"):
        # Improve reproducibility by default. See abravalheri/validate-pyproject#31
        trove_classifier._disable_download()  # type: ignore[union-attr]

    try:
        return validator.validate(config)
    except validator.ValidationError as ex:
        summary = f"configuration error: {ex.summary}"
        if ex.name.strip("`") != "project":
            # Probably it is just a field missing/misnamed, not worthy the verbosity...
            _logger.debug(summary)
            _logger.debug(ex.details)

        error = f"invalid pyproject.toml config: {ex.name}."
        raise ValueError(f"{error}\n{summary}") from None


def apply_configuration(
    dist: Distribution,
    filepath: StrPath,
    ignore_option_errors: bool = False,
) -> Distribution:
    """Apply the configuration from a ``pyproject.toml`` file into an existing
    distribution object.
    """
    config = read_configuration(filepath, True, ignore_option_errors, dist)
    return _apply(dist, config, filepath)


def read_configuration(
    filepath: StrPath,
    expand: bool = True,
    ignore_option_errors: bool = False,
    dist: Distribution | None = None,
) -> dict[str, Any]:
    """Read given configuration file and returns options from it as a dict.

    :param str|unicode filepath: Path to configuration file in the ``pyproject.toml``
        format.

    :param bool expand: Whether to expand directives and other computed values
        (i.e. post-process the given configuration)

    :param bool ignore_option_errors: Whether to silently ignore
        options, values of which could not be resolved (e.g. due to exceptions
        in directives such as file:, attr:, etc.).
        If False exceptions are propagated as expected.

    :param Distribution|None: Distribution object to which the configuration refers.
        If not given a dummy object will be created and discarded after the
        configuration is read. This is used for auto-discovery of packages and in the
        case a dynamic configuration (e.g. ``attr`` or ``cmdclass``) is expanded.
        When ``expand=False`` this object is simply ignored.

    :rtype: dict
    """
    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        raise FileError(f"Configuration file {filepath!r} does not exist.")

    asdict = load_file(filepath) or {}
    project_table = asdict.get("project", {})
    tool_table = asdict.get("tool", {})
    setuptools_table = tool_table.get("setuptools", {})
    if not asdict or not (project_table or setuptools_table):
        return {}  # User is not using pyproject to configure setuptools

    if "setuptools" in asdict.get("tools", {}):
        # let the user know they probably have a typo in their metadata
        _ToolsTypoInMetadata.emit()

    if "distutils" in tool_table:
        _ExperimentalConfiguration.emit(subject="[tool.distutils]")

    # There is an overall sense in the community that making include_package_data=True
    # the default would be an improvement.
    # `ini2toml` backfills include_package_data=False when nothing is explicitly given,
    # therefore setting a default here is backwards compatible.
    if dist and dist.include_package_data is not None:
        setuptools_table.setdefault("include-package-data", dist.include_package_data)
    else:
        setuptools_table.setdefault("include-package-data", True)
    # Persist changes:
    asdict["tool"] = tool_table
    tool_table["setuptools"] = setuptools_table

    if "ext-modules" in setuptools_table:
        _ExperimentalConfiguration.emit(subject="[tool.setuptools.ext-modules]")

    with _ignore_errors(ignore_option_errors):
        # Don't complain about unrelated errors (e.g. tools not using the "tool" table)
        subset = {"project": project_table, "tool": {"setuptools": setuptools_table}}
        validate(subset, filepath)

    if expand:
        root_dir = os.path.dirname(filepath)
        return expand_configuration(asdict, root_dir, ignore_option_errors, dist)

    return asdict


def expand_configuration(
    config: dict,
    root_dir: StrPath | None = None,
    ignore_option_errors: bool = False,
    dist: Distribution | None = None,
) -> dict:
    """Given a configuration with unresolved fields (e.g. dynamic, cmdclass, ...)
    find their final values.

    :param dict config: Dict containing the configuration for the distribution
    :param str root_dir: Top-level directory for the distribution/project
        (the same directory where ``pyproject.toml`` is place)
    :param bool ignore_option_errors: see :func:`read_configuration`
    :param Distribution|None: Distribution object to which the configuration refers.
        If not given a dummy object will be created and discarded after the
        configuration is read. Used in the case a dynamic configuration
        (e.g. ``attr`` or ``cmdclass``).

    :rtype: dict
    """
    return _ConfigExpander(config, root_dir, ignore_option_errors, dist).expand()


class _ConfigExpander:
    def __init__(
        self,
        config: dict,
        root_dir: StrPath | None = None,
        ignore_option_errors: bool = False,
        dist: Distribution | None = None,
    ) -> None:
        self.config = config
        self.root_dir = root_dir or os.getcwd()
        self.project_cfg = config.get("project", {})
        self.dynamic = self.project_cfg.get("dynamic", [])
        self.setuptools_cfg = config.get("tool", {}).get("setuptools", {})
        self.dynamic_cfg = self.setuptools_cfg.get("dynamic", {})
        self.ignore_option_errors = ignore_option_errors
        self._dist = dist
        self._referenced_files = set[str]()

    def _ensure_dist(self) -> Distribution:
        from setuptools.dist import Distribution

        attrs = {"src_root": self.root_dir, "name": self.project_cfg.get("name", None)}
        return self._dist or Distribution(attrs)

    def _process_field(self, container: dict, field: str, fn: Callable):
        if field in container:
            with _ignore_errors(self.ignore_option_errors):
                container[field] = fn(container[field])

    def _canonic_package_data(self, field="package-data"):
        package_data = self.setuptools_cfg.get(field, {})
        return _expand.canonic_package_data(package_data)

    def expand(self):
        self._expand_packages()
        self._canonic_package_data()
        self._canonic_package_data("exclude-package-data")

        # A distribution object is required for discovering the correct package_dir
        dist = self._ensure_dist()
        ctx = _EnsurePackagesDiscovered(dist, self.project_cfg, self.setuptools_cfg)
        with ctx as ensure_discovered:
            package_dir = ensure_discovered.package_dir
            self._expand_data_files()
            self._expand_cmdclass(package_dir)
            self._expand_all_dynamic(dist, package_dir)

        dist._referenced_files.update(self._referenced_files)
        return self.config

    def _expand_packages(self):
        packages = self.setuptools_cfg.get("packages")
        if packages is None or isinstance(packages, (list, tuple)):
            return

        find = packages.get("find")
        if isinstance(find, dict):
            find["root_dir"] = self.root_dir
            find["fill_package_dir"] = self.setuptools_cfg.setdefault("package-dir", {})
            with _ignore_errors(self.ignore_option_errors):
                self.setuptools_cfg["packages"] = _expand.find_packages(**find)

    def _expand_data_files(self):
        data_files = partial(_expand.canonic_data_files, root_dir=self.root_dir)
        self._process_field(self.setuptools_cfg, "data-files", data_files)

    def _expand_cmdclass(self, package_dir: Mapping[str, str]):
        root_dir = self.root_dir
        cmdclass = partial(_expand.cmdclass, package_dir=package_dir, root_dir=root_dir)
        self._process_field(self.setuptools_cfg, "cmdclass", cmdclass)

    def _expand_all_dynamic(self, dist: Distribution, package_dir: Mapping[str, str]):
        special = (  # need special handling
            "version",
            "readme",
            "entry-points",
            "scripts",
            "gui-scripts",
            "classifiers",
            "dependencies",
            "optional-dependencies",
        )
        # `_obtain` functions are assumed to raise appropriate exceptions/warnings.
        obtained_dynamic = {
            field: self._obtain(dist, field, package_dir)
            for field in self.dynamic
            if field not in special
        }
        obtained_dynamic.update(
            self._obtain_entry_points(dist, package_dir) or {},
            version=self._obtain_version(dist, package_dir),
            readme=self._obtain_readme(dist),
            classifiers=self._obtain_classifiers(dist),
            dependencies=self._obtain_dependencies(dist),
            optional_dependencies=self._obtain_optional_dependencies(dist),
        )
        # `None` indicates there is nothing in `tool.setuptools.dynamic` but the value
        # might have already been set by setup.py/extensions, so avoid overwriting.
        updates = {k: v for k, v in obtained_dynamic.items() if v is not None}
        self.project_cfg.update(updates)

    def _ensure_previously_set(self, dist: Distribution, field: str):
        previous = _PREVIOUSLY_DEFINED[field](dist)
        if previous is None and not self.ignore_option_errors:
            msg = (
                f"No configuration found for dynamic {field!r}.\n"
                "Some dynamic fields need to be specified via `tool.setuptools.dynamic`"
                "\nothers must be specified via the equivalent attribute in `setup.py`."
            )
            raise InvalidConfigError(msg)

    def _expand_directive(
        self, specifier: str, directive, package_dir: Mapping[str, str]
    ):
        from more_itertools import always_iterable

        with _ignore_errors(self.ignore_option_errors):
            root_dir = self.root_dir
            if "file" in directive:
                self._referenced_files.update(always_iterable(directive["file"]))
                return _expand.read_files(directive["file"], root_dir)
            if "attr" in directive:
                return _expand.read_attr(directive["attr"], package_dir, root_dir)
            raise ValueError(f"invalid `{specifier}`: {directive!r}")
        return None

    def _obtain(self, dist: Distribution, field: str, package_dir: Mapping[str, str]):
        if field in self.dynamic_cfg:
            return self._expand_directive(
                f"tool.setuptools.dynamic.{field}",
                self.dynamic_cfg[field],
                package_dir,
            )
        self._ensure_previously_set(dist, field)
        return None

    def _obtain_version(self, dist: Distribution, package_dir: Mapping[str, str]):
        # Since plugins can set version, let's silently skip if it cannot be obtained
        if "version" in self.dynamic and "version" in self.dynamic_cfg:
            return _expand.version(
                # We already do an early check for the presence of "version"
                self._obtain(dist, "version", package_dir)  # pyright: ignore[reportArgumentType]
            )
        return None

    def _obtain_readme(self, dist: Distribution) -> dict[str, str] | None:
        if "readme" not in self.dynamic:
            return None

        dynamic_cfg = self.dynamic_cfg
        if "readme" in dynamic_cfg:
            return {
                # We already do an early check for the presence of "readme"
                "text": self._obtain(dist, "readme", {}),
                "content-type": dynamic_cfg["readme"].get("content-type", "text/x-rst"),
            }  # pyright: ignore[reportReturnType]

        self._ensure_previously_set(dist, "readme")
        return None

    def _obtain_entry_points(
        self, dist: Distribution, package_dir: Mapping[str, str]
    ) -> dict[str, dict[str, Any]] | None:
        fields = ("entry-points", "scripts", "gui-scripts")
        if not any(field in self.dynamic for field in fields):
            return None

        text = self._obtain(dist, "entry-points", package_dir)
        if text is None:
            return None

        groups = _expand.entry_points(text)
        # Any is str | dict[str, str], but causes variance issues
        expanded: dict[str, dict[str, Any]] = {"entry-points": groups}

        def _set_scripts(field: str, group: str):
            if group in groups:
                value = groups.pop(group)
                if field not in self.dynamic:
                    raise InvalidConfigError(_MissingDynamic.details(field, value))
                expanded[field] = value

        _set_scripts("scripts", "console_scripts")
        _set_scripts("gui-scripts", "gui_scripts")

        return expanded

    def _obtain_classifiers(self, dist: Distribution):
        if "classifiers" in self.dynamic:
            value = self._obtain(dist, "classifiers", {})
            if value:
                return value.splitlines()
        return None

    def _obtain_dependencies(self, dist: Distribution):
        if "dependencies" in self.dynamic:
            value = self._obtain(dist, "dependencies", {})
            if value:
                return _parse_requirements_list(value)
        return None

    def _obtain_optional_dependencies(self, dist: Distribution):
        if "optional-dependencies" not in self.dynamic:
            return None
        if "optional-dependencies" in self.dynamic_cfg:
            optional_dependencies_map = self.dynamic_cfg["optional-dependencies"]
            assert isinstance(optional_dependencies_map, dict)
            return {
                group: _parse_requirements_list(
                    self._expand_directive(
                        f"tool.setuptools.dynamic.optional-dependencies.{group}",
                        directive,
                        {},
                    )
                )
                for group, directive in optional_dependencies_map.items()
            }
        self._ensure_previously_set(dist, "optional-dependencies")
        return None


def _parse_requirements_list(value):
    return [
        line
        for line in value.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


@contextmanager
def _ignore_errors(ignore_option_errors: bool):
    if not ignore_option_errors:
        yield
        return

    try:
        yield
    except Exception as ex:
        _logger.debug(f"ignored error: {ex.__class__.__name__} - {ex}")


class _EnsurePackagesDiscovered(_expand.EnsurePackagesDiscovered):
    def __init__(
        self, distribution: Distribution, project_cfg: dict, setuptools_cfg: dict
    ) -> None:
        super().__init__(distribution)
        self._project_cfg = project_cfg
        self._setuptools_cfg = setuptools_cfg

    def __enter__(self) -> Self:
        """When entering the context, the values of ``packages``, ``py_modules`` and
        ``package_dir`` that are missing in ``dist`` are copied from ``setuptools_cfg``.
        """
        dist, cfg = self._dist, self._setuptools_cfg
        package_dir: dict[str, str] = cfg.setdefault("package-dir", {})
        package_dir.update(dist.package_dir or {})
        dist.package_dir = package_dir  # needs to be the same object

        dist.set_defaults._ignore_ext_modules()  # pyproject.toml-specific behaviour

        # Set `name`, `py_modules` and `packages` in dist to short-circuit
        # auto-discovery, but avoid overwriting empty lists purposefully set by users.
        if dist.metadata.name is None:
            dist.metadata.name = self._project_cfg.get("name")
        if dist.py_modules is None:
            dist.py_modules = cfg.get("py-modules")
        if dist.packages is None:
            dist.packages = cfg.get("packages")

        return super().__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """When exiting the context, if values of ``packages``, ``py_modules`` and
        ``package_dir`` are missing in ``setuptools_cfg``, copy from ``dist``.
        """
        # If anything was discovered set them back, so they count in the final config.
        self._setuptools_cfg.setdefault("packages", self._dist.packages)
        self._setuptools_cfg.setdefault("py-modules", self._dist.py_modules)
        return super().__exit__(exc_type, exc_value, traceback)


class _ExperimentalConfiguration(SetuptoolsWarning):
    _SUMMARY = (
        "`{subject}` in `pyproject.toml` is still *experimental* "
        "and likely to change in future releases."
    )


class _ToolsTypoInMetadata(SetuptoolsWarning):
    _SUMMARY = (
        "Ignoring [tools.setuptools] in pyproject.toml, did you mean [tool.setuptools]?"
    )

# === NexusCore/openenv\Lib\site-packages\asttokens\mark_tokens.py ===
# Copyright 2016 Grist Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import numbers
import sys
import token
from ast import Module
from typing import Callable, List, Union, cast, Optional, Tuple, TYPE_CHECKING

from . import util
from .asttokens import ASTTokens
from .astroid_compat import astroid_node_classes as nc, BaseContainer as AstroidBaseContainer

if TYPE_CHECKING:
  from .util import AstNode


# Mapping of matching braces. To find a token here, look up token[:2].
_matching_pairs_left = {
  (token.OP, '('): (token.OP, ')'),
  (token.OP, '['): (token.OP, ']'),
  (token.OP, '{'): (token.OP, '}'),
}

_matching_pairs_right = {
  (token.OP, ')'): (token.OP, '('),
  (token.OP, ']'): (token.OP, '['),
  (token.OP, '}'): (token.OP, '{'),
}


class MarkTokens:
  """
  Helper that visits all nodes in the AST tree and assigns .first_token and .last_token attributes
  to each of them. This is the heart of the token-marking logic.
  """
  def __init__(self, code):
    # type: (ASTTokens) -> None
    self._code = code
    self._methods = util.NodeMethods()
    self._iter_children = None # type: Optional[Callable]

  def visit_tree(self, node):
    # type: (Module) -> None
    self._iter_children = util.iter_children_func(node)
    util.visit_tree(node, self._visit_before_children, self._visit_after_children)

  def _visit_before_children(self, node, parent_token):
    # type: (AstNode, Optional[util.Token]) -> Tuple[Optional[util.Token], Optional[util.Token]]
    col = getattr(node, 'col_offset', None)
    token = self._code.get_token_from_utf8(node.lineno, col) if col is not None else None

    if not token and util.is_module(node):
      # We'll assume that a Module node starts at the start of the source code.
      token = self._code.get_token(1, 0)

    # Use our own token, or our parent's if we don't have one, to pass to child calls as
    # parent_token argument. The second value becomes the token argument of _visit_after_children.
    return (token or parent_token, token)

  def _visit_after_children(self, node, parent_token, token):
    # type: (AstNode, Optional[util.Token], Optional[util.Token]) -> None
    # This processes the node generically first, after all children have been processed.

    # Get the first and last tokens that belong to children. Note how this doesn't assume that we
    # iterate through children in order that corresponds to occurrence in source code. This
    # assumption can fail (e.g. with return annotations).
    first = token
    last = None
    for child in cast(Callable, self._iter_children)(node):
      # astroid slices have especially wrong positions, we don't want them to corrupt their parents.
      if util.is_empty_astroid_slice(child):
        continue
      if not first or child.first_token.index < first.index:
        first = child.first_token
      if not last or child.last_token.index > last.index:
        last = child.last_token

    # If we don't have a first token from _visit_before_children, and there were no children, then
    # use the parent's token as the first token.
    first = first or parent_token

    # If no children, set last token to the first one.
    last = last or first

    # Statements continue to before NEWLINE. This helps cover a few different cases at once.
    if util.is_stmt(node):
      last = self._find_last_in_stmt(cast(util.Token, last))

    # Capture any unmatched brackets.
    first, last = self._expand_to_matching_pairs(cast(util.Token, first), cast(util.Token, last), node)

    # Give a chance to node-specific methods to adjust.
    nfirst, nlast = self._methods.get(self, node.__class__)(node, first, last)

    if (nfirst, nlast) != (first, last):
      # If anything changed, expand again to capture any unmatched brackets.
      nfirst, nlast = self._expand_to_matching_pairs(nfirst, nlast, node)

    node.first_token = nfirst
    node.last_token = nlast

  def _find_last_in_stmt(self, start_token):
    # type: (util.Token) -> util.Token
    t = start_token
    while (not util.match_token(t, token.NEWLINE) and
           not util.match_token(t, token.OP, ';') and
           not token.ISEOF(t.type)):
      t = self._code.next_token(t, include_extra=True)
    return self._code.prev_token(t)

  def _expand_to_matching_pairs(self, first_token, last_token, node):
    # type: (util.Token, util.Token, AstNode) -> Tuple[util.Token, util.Token]
    """
    Scan tokens in [first_token, last_token] range that are between node's children, and for any
    unmatched brackets, adjust first/last tokens to include the closing pair.
    """
    # We look for opening parens/braces among non-child tokens (i.e. tokens between our actual
    # child nodes). If we find any closing ones, we match them to the opens.
    to_match_right = [] # type: List[Tuple[int, str]]
    to_match_left = []
    for tok in self._code.token_range(first_token, last_token):
      tok_info = tok[:2]
      if to_match_right and tok_info == to_match_right[-1]:
        to_match_right.pop()
      elif tok_info in _matching_pairs_left:
        to_match_right.append(_matching_pairs_left[tok_info])
      elif tok_info in _matching_pairs_right:
        to_match_left.append(_matching_pairs_right[tok_info])

    # Once done, extend `last_token` to match any unclosed parens/braces.
    for match in reversed(to_match_right):
      last = self._code.next_token(last_token)
      # Allow for trailing commas or colons (allowed in subscripts) before the closing delimiter
      while any(util.match_token(last, token.OP, x) for x in (',', ':')):
        last = self._code.next_token(last)
      # Now check for the actual closing delimiter.
      if util.match_token(last, *match):
        last_token = last

    # And extend `first_token` to match any unclosed opening parens/braces.
    for match in to_match_left:
      first = self._code.prev_token(first_token)
      if util.match_token(first, *match):
        first_token = first

    return (first_token, last_token)

  #----------------------------------------------------------------------
  # Node visitors. Each takes a preliminary first and last tokens, and returns the adjusted pair
  # that will actually be assigned.

  def visit_default(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # pylint: disable=no-self-use
    # By default, we don't need to adjust the token we computed earlier.
    return (first_token, last_token)

  def handle_comp(self, open_brace, node, first_token, last_token):
    # type: (str, AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # For list/set/dict comprehensions, we only get the token of the first child, so adjust it to
    # include the opening brace (the closing brace will be matched automatically).
    before = self._code.prev_token(first_token)
    util.expect_token(before, token.OP, open_brace)
    return (before, last_token)

  def visit_comprehension(self,
                          node,  # type: AstNode
                          first_token,  # type: util.Token
                          last_token,  # type: util.Token
                          ):
    # type: (...) -> Tuple[util.Token, util.Token]
    # The 'comprehension' node starts with 'for' but we only get first child; we search backwards
    # to find the 'for' keyword.
    first = self._code.find_token(first_token, token.NAME, 'for', reverse=True)
    return (first, last_token)

  def visit_if(self, node, first_token, last_token):
    # type: (util.Token, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    while first_token.string not in ('if', 'elif'):
      first_token = self._code.prev_token(first_token)
    return first_token, last_token

  def handle_attr(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # Attribute node has ".attr" (2 tokens) after the last child.
    dot = self._code.find_token(last_token, token.OP, '.')
    name = self._code.next_token(dot)
    util.expect_token(name, token.NAME)
    return (first_token, name)

  visit_attribute = handle_attr
  visit_assignattr = handle_attr
  visit_delattr = handle_attr

  def handle_def(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # With astroid, nodes that start with a doc-string can have an empty body, in which case we
    # need to adjust the last token to include the doc string.
    if not node.body and (getattr(node, 'doc_node', None) or getattr(node, 'doc', None)): # type: ignore[union-attr]
      last_token = self._code.find_token(last_token, token.STRING)

    # Include @ from decorator
    if first_token.index > 0:
      prev = self._code.prev_token(first_token)
      if util.match_token(prev, token.OP, '@'):
        first_token = prev
    return (first_token, last_token)

  visit_classdef = handle_def
  visit_functiondef = handle_def

  def handle_following_brackets(self, node, last_token, opening_bracket):
    # type: (AstNode, util.Token, str) -> util.Token
    # This is for calls and subscripts, which have a pair of brackets
    # at the end which may contain no nodes, e.g. foo() or bar[:].
    # We look for the opening bracket and then let the matching pair be found automatically
    # Remember that last_token is at the end of all children,
    # so we are not worried about encountering a bracket that belongs to a child.
    first_child = next(cast(Callable, self._iter_children)(node))
    call_start = self._code.find_token(first_child.last_token, token.OP, opening_bracket)
    if call_start.index > last_token.index:
      last_token = call_start
    return last_token

  def visit_call(self, node, first_token, last_token):
    # type: (util.Token, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    last_token = self.handle_following_brackets(node, last_token, '(')

    # Handling a python bug with decorators with empty parens, e.g.
    # @deco()
    # def ...
    if util.match_token(first_token, token.OP, '@'):
      first_token = self._code.next_token(first_token)
    return (first_token, last_token)

  def visit_matchclass(self, node, first_token, last_token):
    # type: (util.Token, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    last_token = self.handle_following_brackets(node, last_token, '(')
    return (first_token, last_token)

  def visit_subscript(self,
                      node,  # type: AstNode
                      first_token,  # type: util.Token
                      last_token,  # type: util.Token
                      ):
    # type: (...) -> Tuple[util.Token, util.Token]
    last_token = self.handle_following_brackets(node, last_token, '[')
    return (first_token, last_token)

  def visit_slice(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # consume `:` tokens to the left and right. In Python 3.9, Slice nodes are
    # given a col_offset, (and end_col_offset), so this will always start inside
    # the slice, even if it is the empty slice. However, in 3.8 and below, this
    # will only expand to the full slice if the slice contains a node with a
    # col_offset. So x[:] will only get the correct tokens in 3.9, but x[1:] and
    # x[:1] will even on earlier versions of Python.
    while True:
      prev = self._code.prev_token(first_token)
      if prev.string != ':':
        break
      first_token = prev
    while True:
      next_ = self._code.next_token(last_token)
      if next_.string != ':':
        break
      last_token = next_
    return (first_token, last_token)

  def handle_bare_tuple(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # A bare tuple doesn't include parens; if there is a trailing comma, make it part of the tuple.
    maybe_comma = self._code.next_token(last_token)
    if util.match_token(maybe_comma, token.OP, ','):
      last_token = maybe_comma
    return (first_token, last_token)

  # In Python3.8 parsed tuples include parentheses when present.
  def handle_tuple_nonempty(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    assert isinstance(node, ast.Tuple) or isinstance(node, AstroidBaseContainer)
    # It's a bare tuple if the first token belongs to the first child. The first child may
    # include extraneous parentheses (which don't create new nodes), so account for those too.
    child = node.elts[0]
    if TYPE_CHECKING:
      child = cast(AstNode, child)
    child_first, child_last = self._gobble_parens(child.first_token, child.last_token, True)
    if first_token == child_first:
      return self.handle_bare_tuple(node, first_token, last_token)
    return (first_token, last_token)

  def visit_tuple(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    assert isinstance(node, ast.Tuple) or isinstance(node, AstroidBaseContainer)
    if not node.elts:
      # An empty tuple is just "()", and we need no further info.
      return (first_token, last_token)
    return self.handle_tuple_nonempty(node, first_token, last_token)

  def _gobble_parens(self, first_token, last_token, include_all=False):
    # type: (util.Token, util.Token, bool) -> Tuple[util.Token, util.Token]
    # Expands a range of tokens to include one or all pairs of surrounding parentheses, and
    # returns (first, last) tokens that include these parens.
    while first_token.index > 0:
      prev = self._code.prev_token(first_token)
      next = self._code.next_token(last_token)
      if util.match_token(prev, token.OP, '(') and util.match_token(next, token.OP, ')'):
        first_token, last_token = prev, next
        if include_all:
          continue
      break
    return (first_token, last_token)

  def visit_str(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    return self.handle_str(first_token, last_token)

  def visit_joinedstr(self,
                      node,  # type: AstNode
                      first_token,  # type: util.Token
                      last_token,  # type: util.Token
                      ):
    # type: (...) -> Tuple[util.Token, util.Token]
    if sys.version_info < (3, 12):
      # Older versions don't tokenize the contents of f-strings
      return self.handle_str(first_token, last_token)

    last = first_token
    while True:
      if util.match_token(last, getattr(token, "FSTRING_START")):
        # Python 3.12+ has tokens for the start (e.g. `f"`) and end (`"`)
        # of the f-string. We can't just look for the next FSTRING_END
        # because f-strings can be nested, e.g. f"{f'{x}'}", so we need
        # to treat this like matching balanced parentheses.
        count = 1
        while count > 0:
          last = self._code.next_token(last)
          # mypy complains about token.FSTRING_START and token.FSTRING_END.
          if util.match_token(last, getattr(token, "FSTRING_START")):
            count += 1
          elif util.match_token(last, getattr(token, "FSTRING_END")):
            count -= 1
        last_token = last
        last = self._code.next_token(last_token)
      elif util.match_token(last, token.STRING):
        # Similar to handle_str, we also need to handle adjacent strings.
        last_token = last
        last = self._code.next_token(last_token)
      else:
        break
    return (first_token, last_token)

  def visit_bytes(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    return self.handle_str(first_token, last_token)

  def handle_str(self, first_token, last_token):
    # type: (util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # Multiple adjacent STRING tokens form a single string.
    last = self._code.next_token(last_token)
    while util.match_token(last, token.STRING):
      last_token = last
      last = self._code.next_token(last_token)
    return (first_token, last_token)

  def handle_num(self,
                 node,  # type: AstNode
                 value,  # type: Union[complex, int, numbers.Number]
                 first_token,  # type: util.Token
                 last_token,  # type: util.Token
                 ):
    # type: (...) -> Tuple[util.Token, util.Token]
    # A constant like '-1' gets turned into two tokens; this will skip the '-'.
    while util.match_token(last_token, token.OP):
      last_token = self._code.next_token(last_token)

    if isinstance(value, complex):
      # A complex number like -2j cannot be compared directly to 0
      # A complex number like 1-2j is expressed as a binary operation
      # so we don't need to worry about it
      value = value.imag

    # This makes sure that the - is included
    if value < 0 and first_token.type == token.NUMBER: # type: ignore[operator]
        first_token = self._code.prev_token(first_token)
    return (first_token, last_token)

  def visit_num(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    return self.handle_num(node, cast(ast.Num, node).n, first_token, last_token)

  def visit_const(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    assert isinstance(node, ast.Constant) or isinstance(node, nc.Const)
    if isinstance(node.value, numbers.Number):
      return self.handle_num(node, node.value, first_token, last_token)
    elif isinstance(node.value, (str, bytes)):
      return self.visit_str(node, first_token, last_token)
    return (first_token, last_token)

  visit_constant = visit_const

  def visit_keyword(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # Until python 3.9 (https://bugs.python.org/issue40141),
    # ast.keyword nodes didn't have line info. Astroid has lineno None.
    assert isinstance(node, ast.keyword) or isinstance(node, nc.Keyword)
    if node.arg is not None and getattr(node, 'lineno', None) is None:
      equals = self._code.find_token(first_token, token.OP, '=', reverse=True)
      name = self._code.prev_token(equals)
      util.expect_token(name, token.NAME, node.arg)
      first_token = name
    return (first_token, last_token)

  def visit_starred(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # Astroid has 'Starred' nodes (for "foo(*bar)" type args), but they need to be adjusted.
    if not util.match_token(first_token, token.OP, '*'):
      star = self._code.prev_token(first_token)
      if util.match_token(star, token.OP, '*'):
        first_token = star
    return (first_token, last_token)

  def visit_assignname(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    # Astroid may turn 'except' clause into AssignName, but we need to adjust it.
    if util.match_token(first_token, token.NAME, 'except'):
      colon = self._code.find_token(last_token, token.OP, ':')
      first_token = last_token = self._code.prev_token(colon)
    return (first_token, last_token)

  # Async nodes should typically start with the word 'async'
  # but Python < 3.7 doesn't put the col_offset there
  # AsyncFunctionDef is slightly different because it might have
  # decorators before that, which visit_functiondef handles
  def handle_async(self, node, first_token, last_token):
    # type: (AstNode, util.Token, util.Token) -> Tuple[util.Token, util.Token]
    if not first_token.string == 'async':
      first_token = self._code.prev_token(first_token)
    return (first_token, last_token)

  visit_asyncfor = handle_async
  visit_asyncwith = handle_async

  def visit_asyncfunctiondef(self,
                             node,  # type: AstNode
                             first_token,  # type: util.Token
                             last_token,  # type: util.Token
                             ):
    # type: (...) -> Tuple[util.Token, util.Token]
    if util.match_token(first_token, token.NAME, 'def'):
      # Include the 'async' token
      first_token = self._code.prev_token(first_token)
    return self.visit_functiondef(node, first_token, last_token)

# === NexusCore/openenv\Lib\site-packages\git\objects\submodule\root.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["RootModule", "RootUpdateProgress"]

import logging

import git
from git.exc import InvalidGitRepositoryError

from .base import Submodule, UpdateProgress
from .util import find_first_remote_branch

# typing -------------------------------------------------------------------

from typing import TYPE_CHECKING, Union

from git.types import Commit_ish

if TYPE_CHECKING:
    from git.repo import Repo
    from git.util import IterableList

# ----------------------------------------------------------------------------

_logger = logging.getLogger(__name__)


class RootUpdateProgress(UpdateProgress):
    """Utility class which adds more opcodes to
    :class:`~git.objects.submodule.base.UpdateProgress`."""

    REMOVE, PATHCHANGE, BRANCHCHANGE, URLCHANGE = [
        1 << x for x in range(UpdateProgress._num_op_codes, UpdateProgress._num_op_codes + 4)
    ]
    _num_op_codes = UpdateProgress._num_op_codes + 4

    __slots__ = ()


BEGIN = RootUpdateProgress.BEGIN
END = RootUpdateProgress.END
REMOVE = RootUpdateProgress.REMOVE
BRANCHCHANGE = RootUpdateProgress.BRANCHCHANGE
URLCHANGE = RootUpdateProgress.URLCHANGE
PATHCHANGE = RootUpdateProgress.PATHCHANGE


class RootModule(Submodule):
    """A (virtual) root of all submodules in the given repository.

    This can be used to more easily traverse all submodules of the
    superproject (master repository).
    """

    __slots__ = ()

    k_root_name = "__ROOT__"

    def __init__(self, repo: "Repo") -> None:
        # repo, binsha, mode=None, path=None, name = None, parent_commit=None, url=None, ref=None)
        super().__init__(
            repo,
            binsha=self.NULL_BIN_SHA,
            mode=self.k_default_mode,
            path="",
            name=self.k_root_name,
            parent_commit=repo.head.commit,
            url="",
            branch_path=git.Head.to_full_path(self.k_head_default),
        )

    def _clear_cache(self) -> None:
        """May not do anything."""
        pass

    # { Interface

    def update(  # type: ignore[override]
        self,
        previous_commit: Union[Commit_ish, str, None] = None,
        recursive: bool = True,
        force_remove: bool = False,
        init: bool = True,
        to_latest_revision: bool = False,
        progress: Union[None, "RootUpdateProgress"] = None,
        dry_run: bool = False,
        force_reset: bool = False,
        keep_going: bool = False,
    ) -> "RootModule":
        """Update the submodules of this repository to the current HEAD commit.

        This method behaves smartly by determining changes of the path of a submodule's
        repository, next to changes to the to-be-checked-out commit or the branch to be
        checked out. This works if the submodule's ID does not change.

        Additionally it will detect addition and removal of submodules, which will be
        handled gracefully.

        :param previous_commit:
            If set to a commit-ish, the commit we should use as the previous commit the
            HEAD pointed to before it was set to the commit it points to now.
            If ``None``, it defaults to ``HEAD@{1}`` otherwise.

        :param recursive:
            If ``True``, the children of submodules will be updated as well using the
            same technique.

        :param force_remove:
            If submodules have been deleted, they will be forcibly removed. Otherwise
            the update may fail if a submodule's repository cannot be deleted as changes
            have been made to it.
            (See :meth:`Submodule.update <git.objects.submodule.base.Submodule.update>`
            for more information.)

        :param init:
            If we encounter a new module which would need to be initialized, then do it.

        :param to_latest_revision:
            If ``True``, instead of checking out the revision pointed to by this
            submodule's sha, the checked out tracking branch will be merged with the
            latest remote branch fetched from the repository's origin.

            Unless `force_reset` is specified, a local tracking branch will never be
            reset into its past, therefore the remote branch must be in the future for
            this to have an effect.

        :param force_reset:
            If ``True``, submodules may checkout or reset their branch even if the
            repository has pending changes that would be overwritten, or if the local
            tracking branch is in the future of the remote tracking branch and would be
            reset into its past.

        :param progress:
            :class:`RootUpdateProgress` instance, or ``None`` if no progress should be
            sent.

        :param dry_run:
            If ``True``, operations will not actually be performed. Progress messages
            will change accordingly to indicate the WOULD DO state of the operation.

        :param keep_going:
            If ``True``, we will ignore but log all errors, and keep going recursively.
            Unless `dry_run` is set as well, `keep_going` could cause
            subsequent/inherited errors you wouldn't see otherwise.
            In conjunction with `dry_run`, this can be useful to anticipate all errors
            when updating submodules.

        :return:
            self
        """
        if self.repo.bare:
            raise InvalidGitRepositoryError("Cannot update submodules in bare repositories")
        # END handle bare

        if progress is None:
            progress = RootUpdateProgress()
        # END ensure progress is set

        prefix = ""
        if dry_run:
            prefix = "DRY-RUN: "

        repo = self.repo

        try:
            # SETUP BASE COMMIT
            ###################
            cur_commit = repo.head.commit
            if previous_commit is None:
                try:
                    previous_commit = repo.commit(repo.head.log_entry(-1).oldhexsha)
                    if previous_commit.binsha == previous_commit.NULL_BIN_SHA:
                        raise IndexError
                    # END handle initial commit
                except IndexError:
                    # In new repositories, there is no previous commit.
                    previous_commit = cur_commit
                # END exception handling
            else:
                previous_commit = repo.commit(previous_commit)  # Obtain commit object.
            # END handle previous commit

            psms: "IterableList[Submodule]" = self.list_items(repo, parent_commit=previous_commit)
            sms: "IterableList[Submodule]" = self.list_items(repo)
            spsms = set(psms)
            ssms = set(sms)

            # HANDLE REMOVALS
            ###################
            rrsm = spsms - ssms
            len_rrsm = len(rrsm)

            for i, rsm in enumerate(rrsm):
                op = REMOVE
                if i == 0:
                    op |= BEGIN
                # END handle begin

                # Fake it into thinking its at the current commit to allow deletion
                # of previous module. Trigger the cache to be updated before that.
                progress.update(
                    op,
                    i,
                    len_rrsm,
                    prefix + "Removing submodule %r at %s" % (rsm.name, rsm.abspath),
                )
                rsm._parent_commit = repo.head.commit
                rsm.remove(
                    configuration=False,
                    module=True,
                    force=force_remove,
                    dry_run=dry_run,
                )

                if i == len_rrsm - 1:
                    op |= END
                # END handle end
                progress.update(op, i, len_rrsm, prefix + "Done removing submodule %r" % rsm.name)
            # END for each removed submodule

            # HANDLE PATH RENAMES
            #####################
            # URL changes + branch changes.
            csms = spsms & ssms
            len_csms = len(csms)
            for i, csm in enumerate(csms):
                psm: "Submodule" = psms[csm.name]
                sm: "Submodule" = sms[csm.name]

                # PATH CHANGES
                ##############
                if sm.path != psm.path and psm.module_exists():
                    progress.update(
                        BEGIN | PATHCHANGE,
                        i,
                        len_csms,
                        prefix + "Moving repository of submodule %r from %s to %s" % (sm.name, psm.abspath, sm.abspath),
                    )
                    # Move the module to the new path.
                    if not dry_run:
                        psm.move(sm.path, module=True, configuration=False)
                    # END handle dry_run
                    progress.update(
                        END | PATHCHANGE,
                        i,
                        len_csms,
                        prefix + "Done moving repository of submodule %r" % sm.name,
                    )
                # END handle path changes

                if sm.module_exists():
                    # HANDLE URL CHANGE
                    ###################
                    if sm.url != psm.url:
                        # Add the new remote, remove the old one.
                        # This way, if the url just changes, the commits will not have
                        # to be re-retrieved.
                        nn = "__new_origin__"
                        smm = sm.module()
                        rmts = smm.remotes

                        # Don't do anything if we already have the url we search in
                        # place.
                        if len([r for r in rmts if r.url == sm.url]) == 0:
                            progress.update(
                                BEGIN | URLCHANGE,
                                i,
                                len_csms,
                                prefix + "Changing url of submodule %r from %s to %s" % (sm.name, psm.url, sm.url),
                            )

                            if not dry_run:
                                assert nn not in [r.name for r in rmts]
                                smr = smm.create_remote(nn, sm.url)
                                smr.fetch(progress=progress)

                                # If we have a tracking branch, it should be available
                                # in the new remote as well.
                                if len([r for r in smr.refs if r.remote_head == sm.branch_name]) == 0:
                                    raise ValueError(
                                        "Submodule branch named %r was not available in new submodule remote at %r"
                                        % (sm.branch_name, sm.url)
                                    )
                                # END head is not detached

                                # Now delete the changed one.
                                rmt_for_deletion = None
                                for remote in rmts:
                                    if remote.url == psm.url:
                                        rmt_for_deletion = remote
                                        break
                                    # END if urls match
                                # END for each remote

                                # If we didn't find a matching remote, but have exactly
                                # one, we can safely use this one.
                                if rmt_for_deletion is None:
                                    if len(rmts) == 1:
                                        rmt_for_deletion = rmts[0]
                                    else:
                                        # If we have not found any remote with the
                                        # original URL we may not have a name. This is a
                                        # special case, and its okay to fail here.
                                        # Alternatively we could just generate a unique
                                        # name and leave all existing ones in place.
                                        raise InvalidGitRepositoryError(
                                            "Couldn't find original remote-repo at url %r" % psm.url
                                        )
                                    # END handle one single remote
                                # END handle check we found a remote

                                orig_name = rmt_for_deletion.name
                                smm.delete_remote(rmt_for_deletion)
                                # NOTE: Currently we leave tags from the deleted remotes
                                # as well as separate tracking branches in the possibly
                                # totally changed repository (someone could have changed
                                # the url to another project). At some point, one might
                                # want to clean it up, but the danger is high to remove
                                # stuff the user has added explicitly.

                                # Rename the new remote back to what it was.
                                smr.rename(orig_name)

                                # Early on, we verified that the our current tracking
                                # branch exists in the remote. Now we have to ensure
                                # that the sha we point to is still contained in the new
                                # remote tracking branch.
                                smsha = sm.binsha
                                found = False
                                rref = smr.refs[self.branch_name]
                                for c in rref.commit.traverse():
                                    if c.binsha == smsha:
                                        found = True
                                        break
                                    # END traverse all commits in search for sha
                                # END for each commit

                                if not found:
                                    # Adjust our internal binsha to use the one of the
                                    # remote this way, it will be checked out in the
                                    # next step. This will change the submodule relative
                                    # to us, so the user will be able to commit the
                                    # change easily.
                                    _logger.warning(
                                        "Current sha %s was not contained in the tracking\
             branch at the new remote, setting it the the remote's tracking branch",
                                        sm.hexsha,
                                    )
                                    sm.binsha = rref.commit.binsha
                                # END reset binsha

                                # NOTE: All checkout is performed by the base
                                # implementation of update.
                            # END handle dry_run
                            progress.update(
                                END | URLCHANGE,
                                i,
                                len_csms,
                                prefix + "Done adjusting url of submodule %r" % (sm.name),
                            )
                        # END skip remote handling if new url already exists in module
                    # END handle url

                    # HANDLE PATH CHANGES
                    #####################
                    if sm.branch_path != psm.branch_path:
                        # Finally, create a new tracking branch which tracks the new
                        # remote branch.
                        progress.update(
                            BEGIN | BRANCHCHANGE,
                            i,
                            len_csms,
                            prefix
                            + "Changing branch of submodule %r from %s to %s"
                            % (sm.name, psm.branch_path, sm.branch_path),
                        )
                        if not dry_run:
                            smm = sm.module()
                            smmr = smm.remotes
                            # As the branch might not exist yet, we will have to fetch
                            # all remotes to be sure...
                            for remote in smmr:
                                remote.fetch(progress=progress)
                            # END for each remote

                            try:
                                tbr = git.Head.create(
                                    smm,
                                    sm.branch_name,
                                    logmsg="branch: Created from HEAD",
                                )
                            except OSError:
                                # ...or reuse the existing one.
                                tbr = git.Head(smm, sm.branch_path)
                            # END ensure tracking branch exists

                            tbr.set_tracking_branch(find_first_remote_branch(smmr, sm.branch_name))
                            # NOTE: All head-resetting is done in the base
                            # implementation of update but we will have to checkout the
                            # new branch here. As it still points to the currently
                            # checked out commit, we don't do any harm.
                            # As we don't want to update working-tree or index, changing
                            # the ref is all there is to do.
                            smm.head.reference = tbr
                        # END handle dry_run

                        progress.update(
                            END | BRANCHCHANGE,
                            i,
                            len_csms,
                            prefix + "Done changing branch of submodule %r" % sm.name,
                        )
                    # END handle branch
                # END handle
            # END for each common submodule
        except Exception as err:
            if not keep_going:
                raise
            _logger.error(str(err))
        # END handle keep_going

        # FINALLY UPDATE ALL ACTUAL SUBMODULES
        ######################################
        for sm in sms:
            # Update the submodule using the default method.
            sm.update(
                recursive=False,
                init=init,
                to_latest_revision=to_latest_revision,
                progress=progress,
                dry_run=dry_run,
                force=force_reset,
                keep_going=keep_going,
            )

            # Update recursively depth first - question is which inconsistent state will
            # be better in case it fails somewhere. Defective branch or defective depth.
            # The RootSubmodule type will never process itself, which was done in the
            # previous expression.
            if recursive:
                # The module would exist by now if we are not in dry_run mode.
                if sm.module_exists():
                    type(self)(sm.module()).update(
                        recursive=True,
                        force_remove=force_remove,
                        init=init,
                        to_latest_revision=to_latest_revision,
                        progress=progress,
                        dry_run=dry_run,
                        force_reset=force_reset,
                        keep_going=keep_going,
                    )
                # END handle dry_run
            # END handle recursive
        # END for each submodule to update

        return self

    def module(self) -> "Repo":
        """:return: The actual repository containing the submodules"""
        return self.repo

    # } END interface


# } END classes

# === NexusCore/openenv\Lib\site-packages\google\generativeai\models.py ===
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

import typing
from typing import Any, Literal

import google.ai.generativelanguage as glm

from google.generativeai import protos
from google.generativeai import operations
from google.generativeai.client import get_default_model_client
from google.generativeai.types import model_types
from google.generativeai.types import helper_types
from google.api_core import operation
from google.api_core import protobuf_helpers
from google.protobuf import field_mask_pb2
from google.generativeai.utils import flatten_update_paths


def get_model(
    name: model_types.AnyModelNameOptions,
    *,
    client=None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.Model | model_types.TunedModel:
    """Calls the API to fetch a model by name.

    ```
    import pprint
    model = genai.get_model('models/gemini-pro')
    pprint.pprint(model)
    ```

    Args:
        name: The name of the model to fetch. Should start with `models/`
        client: The client to use.
        request_options: Options for the request.

    Returns:
        A `types.Model`
    """
    name = model_types.make_model_name(name)
    if name.startswith("models/"):
        return get_base_model(name, client=client, request_options=request_options)
    elif name.startswith("tunedModels/"):
        return get_tuned_model(name, client=client, request_options=request_options)
    else:
        raise ValueError(
            f"Invalid model name: Model names must start with `models/` or `tunedModels/`. Received: {name}"
        )


def get_base_model(
    name: model_types.BaseModelNameOptions,
    *,
    client=None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.Model:
    """Calls the API to fetch a base model by name.

    ```
    import pprint
    model = genai.get_base_model('models/chat-bison-001')
    pprint.pprint(model)
    ```

    Args:
        name: The name of the model to fetch. Should start with `models/`
        client: The client to use.
        request_options: Options for the request.

    Returns:
        A `types.Model`.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    name = model_types.make_model_name(name)
    if not name.startswith("models/"):
        raise ValueError(
            f"Invalid model name: Base model names must start with `models/`. Received: {name}"
        )

    result = client.get_model(name=name, **request_options)
    result = type(result).to_dict(result)
    return model_types.Model(**result)


def get_tuned_model(
    name: model_types.TunedModelNameOptions,
    *,
    client=None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.TunedModel:
    """Calls the API to fetch a tuned model by name.

    ```
    import pprint
    model = genai.get_tuned_model('tunedModels/gemini-1.0-pro-001')
    pprint.pprint(model)
    ```

    Args:
        name: The name of the model to fetch. Should start with `tunedModels/`
        client: The client to use.
        request_options: Options for the request.

    Returns:
        A `types.TunedModel`.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    name = model_types.make_model_name(name)

    if not name.startswith("tunedModels/"):
        raise ValueError(
            f"Invalid model name: Tuned model names must start with `tunedModels/`. Received: {name}"
        )

    result = client.get_tuned_model(name=name, **request_options)

    return model_types.decode_tuned_model(result)


def get_base_model_name(
    model: model_types.AnyModelNameOptions, client: glm.ModelServiceClient | None = None
):
    """Calls the API to fetch the base model name of a model."""

    if isinstance(model, str):
        if model.startswith("tunedModels/"):
            model = get_model(model, client=client)
            base_model = model.base_model
        else:
            base_model = model
    elif isinstance(model, model_types.TunedModel):
        base_model = model.base_model
    elif isinstance(model, model_types.Model):
        base_model = model.name
    elif isinstance(model, protos.Model):
        base_model = model.name
    elif isinstance(model, protos.TunedModel):
        base_model = getattr(model, "base_model", None)
        if not base_model:
            base_model = model.tuned_model_source.base_model
    else:
        raise TypeError(
            f"Invalid model: The provided model '{model}' is not recognized or supported. "
            "Supported types are: str, model_types.TunedModel, model_types.Model, protos.Model, and protos.TunedModel."
        )

    return base_model


def list_models(
    *,
    page_size: int | None = 50,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.ModelsIterable:
    """Calls the API to list all available models.

    ```
    import pprint
    for model in genai.list_models():
        pprint.pprint(model)
    ```

    Args:
        page_size: How many `types.Models` to fetch per page (api call).
        client: You may pass a `glm.ModelServiceClient` instead of using the default client.
        request_options: Options for the request.

    Yields:
        `types.Model` objects.

    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    for model in client.list_models(page_size=page_size, **request_options):
        model = type(model).to_dict(model)
        yield model_types.Model(**model)


def list_tuned_models(
    *,
    page_size: int | None = 50,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.TunedModelsIterable:
    """Calls the API to list all tuned models.

    ```
    import pprint
    for model in genai.list_tuned_models():
        pprint.pprint(model)
    ```

    Args:
        page_size: How many `types.Models` to fetch per page (api call).
        client: You may pass a `glm.ModelServiceClient` instead of using the default client.
        request_options: Options for the request.

    Yields:
        `types.TunedModel` objects.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    for model in client.list_tuned_models(
        page_size=page_size,
        **request_options,
    ):
        model = type(model).to_dict(model)
        yield model_types.decode_tuned_model(model)


def create_tuned_model(
    source_model: model_types.AnyModelNameOptions,
    training_data: model_types.TuningDataOptions,
    *,
    id: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    epoch_count: int | None = None,
    batch_size: int | None = None,
    learning_rate: float | None = None,
    input_key: str = "text_input",
    output_key: str = "output",
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> operations.CreateTunedModelOperation:
    """Calls the API to initiate a tuning process that optimizes a model for specific data, returning an operation object to track and manage the tuning progress.

    Since tuning a model can take significant time, this API doesn't wait for the tuning to complete.
    Instead, it returns a `google.api_core.operation.Operation` object that lets you check on the
    status of the tuning job, or wait for it to complete, and check the result.

    After the job completes you can either find the resulting `TunedModel` object in
    `Operation.result()` or `palm.list_tuned_models` or `palm.get_tuned_model(model_id)`.

    ```
    my_id = "my-tuned-model-id"
    operation = palm.create_tuned_model(
      id = my_id,
      source_model="models/text-bison-001",
      training_data=[{'text_input': 'example input', 'output': 'example output'},...]
    )
    tuned_model=operation.result()      # Wait for tuning to finish

    palm.generate_text(f"tunedModels/{my_id}", prompt="...")
    ```

    Args:
        source_model: The name of the model to tune.
        training_data: The dataset to tune the model on. This must be either:
          * A `protos.Dataset`, or
          * An `Iterable` of:
            *`protos.TuningExample`,
            * `{'text_input': text_input, 'output': output}` dicts
            * `(text_input, output)` tuples.
          * A `Mapping` of `Iterable[str]` - use `input_key` and `output_key` to choose which
            columns to use as the input/output
          * A csv file (will be read with `pd.read_csv` and handles as a `Mapping`
            above). This can be:
            * A local path as a `str` or `pathlib.Path`.
            * A url for a csv file.
            * The url of a Google Sheets file.
          * A JSON file - Its contents will be handled either as an `Iterable` or `Mapping`
            above. This can be:
            * A local path as a `str` or `pathlib.Path`.
        id: The model identifier, used to refer to the model in the API
          `tunedModels/{id}`. Must be unique.
        display_name: A human-readable name for display.
        description: A description of the tuned model.
        temperature: The default temperature for the tuned model, see `types.Model` for details.
        top_p: The default `top_p` for the model, see `types.Model` for details.
        top_k: The default `top_k` for the model, see `types.Model` for details.
        epoch_count: The number of tuning epochs to run. An epoch is a pass over the whole dataset.
        batch_size: The number of examples to use in each training batch.
        learning_rate: The step size multiplier for the gradient updates.
        client: Which client to use.
        request_options: Options for the request.

    Returns:
        A [`google.api_core.operation.Operation`](https://googleapis.dev/python/google-api-core/latest/operation.html)
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    source_model_name = model_types.make_model_name(source_model)
    base_model_name = get_base_model_name(source_model)
    if source_model_name.startswith("models/"):
        source_model = {"base_model": source_model_name}
    elif source_model_name.startswith("tunedModels/"):
        source_model = {
            "tuned_model_source": {
                "tuned_model": source_model_name,
                "base_model": base_model_name,
            }
        }
    else:
        raise ValueError(
            f"Invalid model name: The provided model '{source_model}' does not match any known model patterns such as 'models/' or 'tunedModels/'"
        )

    training_data = model_types.encode_tuning_data(
        training_data, input_key=input_key, output_key=output_key
    )

    hyperparameters = protos.Hyperparameters(
        epoch_count=epoch_count,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )
    tuning_task = protos.TuningTask(
        training_data=training_data,
        hyperparameters=hyperparameters,
    )

    tuned_model = protos.TunedModel(
        **source_model,
        display_name=display_name,
        description=description,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        tuning_task=tuning_task,
    )

    operation = client.create_tuned_model(
        dict(tuned_model_id=id, tuned_model=tuned_model), **request_options
    )

    return operations.CreateTunedModelOperation.from_core_operation(operation)


@typing.overload
def update_tuned_model(
    tuned_model: protos.TunedModel,
    updates: None = None,
    *,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.TunedModel:
    pass


@typing.overload
def update_tuned_model(
    tuned_model: str,
    updates: dict[str, Any],
    *,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.TunedModel:
    pass


def update_tuned_model(
    tuned_model: str | protos.TunedModel,
    updates: dict[str, Any] | None = None,
    *,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> model_types.TunedModel:
    """Calls the API to push updates to a specified tuned model where only certain attributes are updatable."""

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    if isinstance(tuned_model, str):
        name = tuned_model
        if not isinstance(updates, dict):
            raise TypeError(
                f"Invalid argument type: In the function `update_tuned_model(name:str, updates: dict)`, the `updates` argument must be of type `dict`. Received type: {type(updates).__name__}."
            )

        tuned_model = client.get_tuned_model(name=name, **request_options)

        updates = flatten_update_paths(updates)
        field_mask = field_mask_pb2.FieldMask()
        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            _apply_update(tuned_model, path, value)
    elif isinstance(tuned_model, protos.TunedModel):
        if updates is not None:
            raise ValueError(
                "Invalid argument: When calling `update_tuned_model(tuned_model:protos.TunedModel, updates=None)`, "
                "the `updates` argument must not be set."
            )

        name = tuned_model.name
        was = client.get_tuned_model(name=name)
        field_mask = protobuf_helpers.field_mask(was._pb, tuned_model._pb)
    else:
        raise TypeError(
            "Invalid argument type: In the function `update_tuned_model(tuned_model:dict|protos.TunedModel)`, the "
            f"`tuned_model` argument must be of type `dict` or `protos.TunedModel`. Received type: {type(tuned_model).__name__}."
        )

    result = client.update_tuned_model(
        protos.UpdateTunedModelRequest(tuned_model=tuned_model, update_mask=field_mask),
        **request_options,
    )
    return model_types.decode_tuned_model(result)


def _apply_update(thing, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        thing = getattr(thing, part)
    setattr(thing, parts[-1], value)


def delete_tuned_model(
    tuned_model: model_types.TunedModelNameOptions,
    client: glm.ModelServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> None:
    """Calls the API to delete a specified tuned model"""

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_model_client()

    name = model_types.make_model_name(tuned_model)
    client.delete_tuned_model(name=name, **request_options)

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\agreement.py ===
# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Implementations of inter-annotator agreement coefficients surveyed by Artstein
and Poesio (2007), Inter-Coder Agreement for Computational Linguistics.

An agreement coefficient calculates the amount that annotators agreed on label
assignments beyond what is expected by chance.

In defining the AnnotationTask class, we use naming conventions similar to the
paper's terminology.  There are three types of objects in an annotation task:

    the coders (variables "c" and "C")
    the items to be annotated (variables "i" and "I")
    the potential categories to be assigned (variables "k" and "K")

Additionally, it is often the case that we don't want to treat two different
labels as complete disagreement, and so the AnnotationTask constructor can also
take a distance metric as a final argument.  Distance metrics are simply
functions that take two arguments, and return a value between 0.0 and 1.0
indicating the distance between them.  If not supplied, the default is binary
comparison between the arguments.

The simplest way to initialize an AnnotationTask is with a list of triples,
each containing a coder's assignment for one object in the task:

    task = AnnotationTask(data=[('c1', '1', 'v1'),('c2', '1', 'v1'),...])

Note that the data list needs to contain the same number of triples for each
individual coder, containing category values for the same set of items.

Alpha (Krippendorff 1980)
Kappa (Cohen 1960)
S (Bennet, Albert and Goldstein 1954)
Pi (Scott 1955)


TODO: Describe handling of multiple coders and missing data

Expected results from the Artstein and Poesio survey paper:

    >>> from nltk.metrics.agreement import AnnotationTask
    >>> import os.path
    >>> t = AnnotationTask(data=[x.split() for x in open(os.path.join(os.path.dirname(__file__), "artstein_poesio_example.txt"))])
    >>> t.avg_Ao()
    0.88
    >>> round(t.pi(), 5)
    0.79953
    >>> round(t.S(), 2)
    0.82

    This would have returned a wrong value (0.0) in @785fb79 as coders are in
    the wrong order. Subsequently, all values for pi(), S(), and kappa() would
    have been wrong as they are computed with avg_Ao().
    >>> t2 = AnnotationTask(data=[('b','1','stat'),('a','1','stat')])
    >>> t2.avg_Ao()
    1.0

    The following, of course, also works.
    >>> t3 = AnnotationTask(data=[('a','1','othr'),('b','1','othr')])
    >>> t3.avg_Ao()
    1.0

"""

import logging
from itertools import groupby
from operator import itemgetter

from nltk.internals import deprecated
from nltk.metrics.distance import binary_distance
from nltk.probability import ConditionalFreqDist, FreqDist

log = logging.getLogger(__name__)


class AnnotationTask:
    """Represents an annotation task, i.e. people assign labels to items.

    Notation tries to match notation in Artstein and Poesio (2007).

    In general, coders and items can be represented as any hashable object.
    Integers, for example, are fine, though strings are more readable.
    Labels must support the distance functions applied to them, so e.g.
    a string-edit-distance makes no sense if your labels are integers,
    whereas interval distance needs numeric values.  A notable case of this
    is the MASI metric, which requires Python sets.
    """

    def __init__(self, data=None, distance=binary_distance):
        """Initialize an annotation task.

        The data argument can be None (to create an empty annotation task) or a sequence of 3-tuples,
        each representing a coder's labeling of an item:
        ``(coder,item,label)``

        The distance argument is a function taking two arguments (labels) and producing a numerical distance.
        The distance from a label to itself should be zero:
        ``distance(l,l) = 0``
        """
        self.distance = distance
        self.I = set()
        self.K = set()
        self.C = set()
        self.data = []
        if data is not None:
            self.load_array(data)

    def __str__(self):
        return "\r\n".join(
            map(
                lambda x: "%s\t%s\t%s"
                % (x["coder"], x["item"].replace("_", "\t"), ",".join(x["labels"])),
                self.data,
            )
        )

    def load_array(self, array):
        """Load an sequence of annotation results, appending to any data already loaded.

        The argument is a sequence of 3-tuples, each representing a coder's labeling of an item:
            (coder,item,label)
        """
        for coder, item, labels in array:
            self.C.add(coder)
            self.K.add(labels)
            self.I.add(item)
            self.data.append({"coder": coder, "labels": labels, "item": item})

    def agr(self, cA, cB, i, data=None):
        """Agreement between two coders on a given item"""
        data = data or self.data
        # cfedermann: we don't know what combination of coder/item will come
        # first in x; to avoid StopIteration problems due to assuming an order
        # cA,cB, we allow either for k1 and then look up the missing as k2.
        k1 = next(x for x in data if x["coder"] in (cA, cB) and x["item"] == i)
        if k1["coder"] == cA:
            k2 = next(x for x in data if x["coder"] == cB and x["item"] == i)
        else:
            k2 = next(x for x in data if x["coder"] == cA and x["item"] == i)

        ret = 1.0 - float(self.distance(k1["labels"], k2["labels"]))
        log.debug("Observed agreement between %s and %s on %s: %f", cA, cB, i, ret)
        log.debug(
            'Distance between "%r" and "%r": %f', k1["labels"], k2["labels"], 1.0 - ret
        )
        return ret

    def Nk(self, k):
        return float(sum(1 for x in self.data if x["labels"] == k))

    def Nik(self, i, k):
        return float(sum(1 for x in self.data if x["item"] == i and x["labels"] == k))

    def Nck(self, c, k):
        return float(sum(1 for x in self.data if x["coder"] == c and x["labels"] == k))

    @deprecated("Use Nk, Nik or Nck instead")
    def N(self, k=None, i=None, c=None):
        """Implements the "n-notation" used in Artstein and Poesio (2007)"""
        if k is not None and i is None and c is None:
            ret = self.Nk(k)
        elif k is not None and i is not None and c is None:
            ret = self.Nik(i, k)
        elif k is not None and c is not None and i is None:
            ret = self.Nck(c, k)
        else:
            raise ValueError(
                f"You must pass either i or c, not both! (k={k!r},i={i!r},c={c!r})"
            )
        log.debug("Count on N[%s,%s,%s]: %d", k, i, c, ret)
        return ret

    def _grouped_data(self, field, data=None):
        data = data or self.data
        return groupby(sorted(data, key=itemgetter(field)), itemgetter(field))

    def Ao(self, cA, cB):
        """Observed agreement between two coders on all items."""
        data = self._grouped_data(
            "item", (x for x in self.data if x["coder"] in (cA, cB))
        )
        ret = sum(self.agr(cA, cB, item, item_data) for item, item_data in data) / len(
            self.I
        )
        log.debug("Observed agreement between %s and %s: %f", cA, cB, ret)
        return ret

    def _pairwise_average(self, function):
        """
        Calculates the average of function results for each coder pair
        """
        total = 0
        n = 0
        s = self.C.copy()
        for cA in self.C:
            s.remove(cA)
            for cB in s:
                total += function(cA, cB)
                n += 1
        ret = total / n
        return ret

    def avg_Ao(self):
        """Average observed agreement across all coders and items."""
        ret = self._pairwise_average(self.Ao)
        log.debug("Average observed agreement: %f", ret)
        return ret

    def Do_Kw_pairwise(self, cA, cB, max_distance=1.0):
        """The observed disagreement for the weighted kappa coefficient."""
        total = 0.0
        data = (x for x in self.data if x["coder"] in (cA, cB))
        for i, itemdata in self._grouped_data("item", data):
            # we should have two items; distance doesn't care which comes first
            total += self.distance(next(itemdata)["labels"], next(itemdata)["labels"])

        ret = total / (len(self.I) * max_distance)
        log.debug("Observed disagreement between %s and %s: %f", cA, cB, ret)
        return ret

    def Do_Kw(self, max_distance=1.0):
        """Averaged over all labelers"""
        ret = self._pairwise_average(
            lambda cA, cB: self.Do_Kw_pairwise(cA, cB, max_distance)
        )
        log.debug("Observed disagreement: %f", ret)
        return ret

    # Agreement Coefficients
    def S(self):
        """Bennett, Albert and Goldstein 1954"""
        Ae = 1.0 / len(self.K)
        ret = (self.avg_Ao() - Ae) / (1.0 - Ae)
        return ret

    def pi(self):
        """Scott 1955; here, multi-pi.
        Equivalent to K from Siegel and Castellan (1988).

        """
        total = 0.0
        label_freqs = FreqDist(x["labels"] for x in self.data)
        for k, f in label_freqs.items():
            total += f**2
        Ae = total / ((len(self.I) * len(self.C)) ** 2)
        return (self.avg_Ao() - Ae) / (1 - Ae)

    def Ae_kappa(self, cA, cB):
        Ae = 0.0
        nitems = float(len(self.I))
        label_freqs = ConditionalFreqDist((x["labels"], x["coder"]) for x in self.data)
        for k in label_freqs.conditions():
            Ae += (label_freqs[k][cA] / nitems) * (label_freqs[k][cB] / nitems)
        return Ae

    def kappa_pairwise(self, cA, cB):
        """ """
        Ae = self.Ae_kappa(cA, cB)
        ret = (self.Ao(cA, cB) - Ae) / (1.0 - Ae)
        log.debug("Expected agreement between %s and %s: %f", cA, cB, Ae)
        return ret

    def kappa(self):
        """Cohen 1960
        Averages naively over kappas for each coder pair.

        """
        return self._pairwise_average(self.kappa_pairwise)

    def multi_kappa(self):
        """Davies and Fleiss 1982
        Averages over observed and expected agreements for each coder pair.

        """
        Ae = self._pairwise_average(self.Ae_kappa)
        return (self.avg_Ao() - Ae) / (1.0 - Ae)

    def Disagreement(self, label_freqs):
        total_labels = sum(label_freqs.values())
        pairs = 0.0
        for j, nj in label_freqs.items():
            for l, nl in label_freqs.items():
                pairs += float(nj * nl) * self.distance(l, j)
        return 1.0 * pairs / (total_labels * (total_labels - 1))

    def alpha(self):
        """Krippendorff 1980"""
        # check for degenerate cases
        if len(self.K) == 0:
            raise ValueError("Cannot calculate alpha, no data present!")
        if len(self.K) == 1:
            log.debug("Only one annotation value, alpha returning 1.")
            return 1
        if len(self.C) == 1 and len(self.I) == 1:
            raise ValueError("Cannot calculate alpha, only one coder and item present!")

        total_disagreement = 0.0
        total_ratings = 0
        all_valid_labels_freq = FreqDist([])
        total_do = 0.0  # Total observed disagreement for all items.
        for i, itemdata in self._grouped_data("item"):
            label_freqs = FreqDist(x["labels"] for x in itemdata)
            labels_count = sum(label_freqs.values())
            if labels_count < 2:
                # Ignore the item.
                continue
            all_valid_labels_freq += label_freqs
            total_do += self.Disagreement(label_freqs) * labels_count

        if len(all_valid_labels_freq.keys()) == 1:
            log.debug("Only one valid annotation value, alpha returning 1.")
            return 1

        do = total_do / sum(all_valid_labels_freq.values())

        de = self.Disagreement(all_valid_labels_freq)  # Expected disagreement.
        k_alpha = 1.0 - do / de

        return k_alpha

    def weighted_kappa_pairwise(self, cA, cB, max_distance=1.0):
        """Cohen 1968"""
        total = 0.0
        label_freqs = ConditionalFreqDist(
            (x["coder"], x["labels"]) for x in self.data if x["coder"] in (cA, cB)
        )
        for j in self.K:
            for l in self.K:
                total += label_freqs[cA][j] * label_freqs[cB][l] * self.distance(j, l)
        De = total / (max_distance * pow(len(self.I), 2))
        log.debug("Expected disagreement between %s and %s: %f", cA, cB, De)
        Do = self.Do_Kw_pairwise(cA, cB)
        ret = 1.0 - (Do / De)
        return ret

    def weighted_kappa(self, max_distance=1.0):
        """Cohen 1968"""
        return self._pairwise_average(
            lambda cA, cB: self.weighted_kappa_pairwise(cA, cB, max_distance)
        )


if __name__ == "__main__":
    import optparse
    import re

    from nltk.metrics import distance

    # process command-line arguments
    parser = optparse.OptionParser()
    parser.add_option(
        "-d",
        "--distance",
        dest="distance",
        default="binary_distance",
        help="distance metric to use",
    )
    parser.add_option(
        "-a",
        "--agreement",
        dest="agreement",
        default="kappa",
        help="agreement coefficient to calculate",
    )
    parser.add_option(
        "-e",
        "--exclude",
        dest="exclude",
        action="append",
        default=[],
        help="coder names to exclude (may be specified multiple times)",
    )
    parser.add_option(
        "-i",
        "--include",
        dest="include",
        action="append",
        default=[],
        help="coder names to include, same format as exclude",
    )
    parser.add_option(
        "-f",
        "--file",
        dest="file",
        help="file to read labelings from, each line with three columns: 'labeler item labels'",
    )
    parser.add_option(
        "-v",
        "--verbose",
        dest="verbose",
        default="0",
        help="how much debugging to print on stderr (0-4)",
    )
    parser.add_option(
        "-c",
        "--columnsep",
        dest="columnsep",
        default="\t",
        help="char/string that separates the three columns in the file, defaults to tab",
    )
    parser.add_option(
        "-l",
        "--labelsep",
        dest="labelsep",
        default=",",
        help="char/string that separates labels (if labelers can assign more than one), defaults to comma",
    )
    parser.add_option(
        "-p",
        "--presence",
        dest="presence",
        default=None,
        help="convert each labeling into 1 or 0, based on presence of LABEL",
    )
    parser.add_option(
        "-T",
        "--thorough",
        dest="thorough",
        default=False,
        action="store_true",
        help="calculate agreement for every subset of the annotators",
    )
    (options, remainder) = parser.parse_args()

    if not options.file:
        parser.print_help()
        exit()

    logging.basicConfig(level=50 - 10 * int(options.verbose))

    # read in data from the specified file
    data = []
    with open(options.file) as infile:
        for l in infile:
            toks = l.split(options.columnsep)
            coder, object_, labels = (
                toks[0],
                str(toks[1:-1]),
                frozenset(toks[-1].strip().split(options.labelsep)),
            )
            if (
                (options.include == options.exclude)
                or (len(options.include) > 0 and coder in options.include)
                or (len(options.exclude) > 0 and coder not in options.exclude)
            ):
                data.append((coder, object_, labels))

    if options.presence:
        task = AnnotationTask(
            data, getattr(distance, options.distance)(options.presence)
        )
    else:
        task = AnnotationTask(data, getattr(distance, options.distance))

    if options.thorough:
        pass
    else:
        print(getattr(task, options.agreement)())

    logging.shutdown()

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\adb.py ===
"""The glue between the Python debugger interface and the Active Debugger interface"""

import _thread
import bdb
import os
import sys
import traceback

import pythoncom
import win32api
import win32com.client.connect
from win32com.axdebug.util import _wrap, trace

from . import axdebug, gateways, stackframe


def fnull(*args):
    pass


debugging = "DEBUG_AXDEBUG" in os.environ
traceenter = fnull  # trace enter of functions
tracev = fnull  # verbose trace

if debugging:
    traceenter = trace  # trace enter of functions
    tracev = trace  # verbose trace


class OutputReflector:
    def __init__(self, file, writefunc):
        self.writefunc = writefunc
        self.file = file

    def __getattr__(self, name):
        return getattr(self.file, name)

    def write(self, message):
        self.writefunc(message)
        self.file.write(message)


def _dumpf(frame):
    if frame is None:
        return "<None>"
    else:
        addn = "(with trace!)"
        if frame.f_trace is None:
            addn = " **No Trace Set **"
        return f"Frame at {id(frame)}, file {frame.f_code.co_filename}, line: {frame.f_lineno}{addn}"


g_adb = None


def OnSetBreakPoint(codeContext, breakPointState, lineNo):
    try:
        fileName = codeContext.codeContainer.GetFileName()
        # inject the code into linecache.
        import linecache

        linecache.cache[fileName] = 0, 0, codeContext.codeContainer.GetText(), fileName
        g_adb._OnSetBreakPoint(fileName, codeContext, breakPointState, lineNo + 1)
    except:
        traceback.print_exc()


class Adb(bdb.Bdb, gateways.RemoteDebugApplicationEvents):
    def __init__(self):
        self.debugApplication = None
        self.debuggingThread = None
        self.debuggingThreadStateHandle = None
        self.stackSnifferCookie = self.stackSniffer = None
        self.codeContainerProvider = None
        self.debuggingThread = None
        self.breakFlags = None
        self.breakReason = None
        self.appDebugger = None
        self.appEventConnection = None
        self.logicalbotframe = None  # Anything at this level or below does not exist!
        self.currentframe = None  # The frame we are currently in.
        self.recursiveData = []  # Data saved for each reentery on this thread.
        bdb.Bdb.__init__(self)
        self._threadprotectlock = _thread.allocate_lock()
        self.reset()

    def canonic(self, fname):
        if fname[0] == "<":
            return fname
        return bdb.Bdb.canonic(self, fname)

    def reset(self):
        traceenter("adb.reset")
        bdb.Bdb.reset(self)

    def __xxxxx__set_break(self, filename, lineno, cond=None):
        # As per standard one, except no linecache checking!
        if filename not in self.breaks:
            self.breaks[filename] = []
        list = self.breaks[filename]
        if lineno in list:
            return "There is already a breakpoint there!"
        list.append(lineno)
        if cond is not None:
            self.cbreaks[filename, lineno] = cond

    def stop_here(self, frame):
        traceenter("stop_here", _dumpf(frame), _dumpf(self.stopframe))
        # As per bdb.stop_here, except for logicalbotframe
        # if self.stopframe is None:
        #     return 1
        if frame is self.stopframe:
            return 1

        tracev("stop_here said 'No'!")
        return 0

    def break_here(self, frame):
        traceenter("break_here", self.breakFlags, _dumpf(frame))
        self.breakReason = None
        if self.breakFlags == axdebug.APPBREAKFLAG_DEBUGGER_HALT:
            self.breakReason = axdebug.BREAKREASON_DEBUGGER_HALT
        elif self.breakFlags == axdebug.APPBREAKFLAG_DEBUGGER_BLOCK:
            self.breakReason = axdebug.BREAKREASON_DEBUGGER_BLOCK
        elif self.breakFlags == axdebug.APPBREAKFLAG_STEP:
            self.breakReason = axdebug.BREAKREASON_STEP
        else:
            print("Calling base 'break_here' with", self.breaks)
            if bdb.Bdb.break_here(self, frame):
                self.breakReason = axdebug.BREAKREASON_BREAKPOINT
        return self.breakReason is not None

    def break_anywhere(self, frame):
        traceenter("break_anywhere", _dumpf(frame))
        if self.breakFlags == axdebug.APPBREAKFLAG_DEBUGGER_HALT:
            self.breakReason = axdebug.BREAKREASON_DEBUGGER_HALT
            return 1
        rc = bdb.Bdb.break_anywhere(self, frame)
        tracev("break_anywhere", _dumpf(frame), "returning", rc)
        return rc

    def dispatch_return(self, frame, arg):
        traceenter("dispatch_return", _dumpf(frame), arg)
        if self.logicalbotframe is frame:
            # We don't want to debug parent frames.
            tracev("dispatch_return resetting sys.trace")
            sys.settrace(None)
            return
        # self.bSetTrace = 0
        self.currentframe = frame.f_back
        return bdb.Bdb.dispatch_return(self, frame, arg)

    def dispatch_line(self, frame):
        traceenter("dispatch_line", _dumpf(frame), _dumpf(self.botframe))
        # trace("logbotframe is", _dumpf(self.logicalbotframe), "botframe is", self.botframe)
        if frame is self.logicalbotframe:
            trace("dispatch_line", _dumpf(frame), "for bottom frame returing tracer")
            # The next code executed in the frame above may be a builtin (eg, apply())
            # in which sys.trace needs to be set.
            sys.settrace(self.trace_dispatch)
            # And return the tracer incase we are about to execute Python code,
            # in which case sys tracer is ignored!
            return self.trace_dispatch

        if self.codeContainerProvider.FromFileName(frame.f_code.co_filename) is None:
            trace(
                "dispatch_line has no document for", _dumpf(frame), "- skipping trace!"
            )
            return None
        self.currentframe = (
            frame  # So the stack sniffer knows our most recent, debuggable code.
        )
        return bdb.Bdb.dispatch_line(self, frame)

    def dispatch_call(self, frame, arg):
        traceenter("dispatch_call", _dumpf(frame))
        frame.f_locals["__axstack_address__"] = axdebug.GetStackAddress()
        if frame is self.botframe:
            trace("dispatch_call is self.botframe - returning tracer")
            return self.trace_dispatch
        # Not our bottom frame.  If we have a document for it,
        # then trace it, otherwise run at full speed.
        if self.codeContainerProvider.FromFileName(frame.f_code.co_filename) is None:
            trace(
                "dispatch_call has no document for", _dumpf(frame), "- skipping trace!"
            )
            # sys.settrace(None)
            return None
        return self.trace_dispatch

        # rc =  bdb.Bdb.dispatch_call(self, frame, arg)
        # trace("dispatch_call", _dumpf(frame),"returned",rc)
        # return rc

    def trace_dispatch(self, frame, event, arg):
        traceenter("trace_dispatch", _dumpf(frame), event, arg)
        if self.debugApplication is None:
            trace("trace_dispatch has no application!")
            return  # None
        return bdb.Bdb.trace_dispatch(self, frame, event, arg)

    #
    # The user functions do bugger all!
    #
    # def user_call(self, frame, argument_list):
    #     traceenter("user_call",_dumpf(frame))

    def user_line(self, frame):
        traceenter("user_line", _dumpf(frame))
        # Traces at line zero
        if frame.f_lineno != 0:
            breakReason = self.breakReason
            if breakReason is None:
                breakReason = axdebug.BREAKREASON_STEP
            self._HandleBreakPoint(frame, None, breakReason)

    def user_return(self, frame, return_value):
        # traceenter("user_return",_dumpf(frame),return_value)
        bdb.Bdb.user_return(self, frame, return_value)

    def user_exception(self, frame, exc_info):
        # traceenter("user_exception")
        bdb.Bdb.user_exception(self, frame, exc_info)

    def _HandleBreakPoint(self, frame, tb, reason):
        traceenter(
            "Calling HandleBreakPoint with reason", reason, "at frame", _dumpf(frame)
        )
        traceenter(" Current frame is", _dumpf(self.currentframe))
        try:
            resumeAction = self.debugApplication.HandleBreakPoint(reason)
            tracev("HandleBreakPoint returned with ", resumeAction)
        except pythoncom.com_error as details:
            # Eeek - the debugger is dead, or something serious is happening.
            # Assume we should continue
            resumeAction = axdebug.BREAKRESUMEACTION_CONTINUE
            trace("HandleBreakPoint FAILED with", details)

        self.stack = []
        self.curindex = 0
        if resumeAction == axdebug.BREAKRESUMEACTION_ABORT:
            self.set_quit()
        elif resumeAction == axdebug.BREAKRESUMEACTION_CONTINUE:
            tracev("resume action is continue")
            self.set_continue()
        elif resumeAction == axdebug.BREAKRESUMEACTION_STEP_INTO:
            tracev("resume action is step")
            self.set_step()
        elif resumeAction == axdebug.BREAKRESUMEACTION_STEP_OVER:
            tracev("resume action is next")
            self.set_next(frame)
        elif resumeAction == axdebug.BREAKRESUMEACTION_STEP_OUT:
            tracev("resume action is stop out")
            self.set_return(frame)
        else:
            raise ValueError("unknown resume action flags")
        self.breakReason = None

    def set_trace(self):
        self.breakReason = axdebug.BREAKREASON_LANGUAGE_INITIATED
        bdb.Bdb.set_trace(self)

    def CloseApp(self):
        traceenter("ClosingApp")
        self.reset()
        self.logicalbotframe = None
        if self.stackSnifferCookie is not None:
            try:
                self.debugApplication.RemoveStackFrameSniffer(self.stackSnifferCookie)

            except pythoncom.com_error:
                trace(
                    f"*** Could not RemoveStackFrameSniffer {self.stackSnifferCookie}"
                )
        self.stackSnifferCookie = self.stackSniffer = None

        if self.appEventConnection is not None:
            self.appEventConnection.Disconnect()
            self.appEventConnection = None
        self.debugApplication = None
        self.appDebugger = None
        if self.codeContainerProvider is not None:
            self.codeContainerProvider.Close()
            self.codeContainerProvider = None

    def AttachApp(self, debugApplication, codeContainerProvider):
        # traceenter("AttachApp", debugApplication, codeContainerProvider)
        self.codeContainerProvider = codeContainerProvider
        self.debugApplication = debugApplication
        self.stackSniffer = _wrap(
            stackframe.DebugStackFrameSniffer(self), axdebug.IID_IDebugStackFrameSniffer
        )
        self.stackSnifferCookie = debugApplication.AddStackFrameSniffer(
            self.stackSniffer
        )
        # trace(f"StackFrameSniffer added ({self.stackSnifferCookie})")

        # Connect to the application events.
        self.appEventConnection = win32com.client.connect.SimpleConnection(
            self.debugApplication, self, axdebug.IID_IRemoteDebugApplicationEvents
        )

    def ResetAXDebugging(self):
        traceenter("ResetAXDebugging", self, "with refcount", len(self.recursiveData))
        if win32api.GetCurrentThreadId() != self.debuggingThread:
            trace("ResetAXDebugging called on other thread")
            return

        if len(self.recursiveData) == 0:
            # print("ResetAXDebugging called for final time.")
            self.logicalbotframe = None
            self.debuggingThread = None
            self.currentframe = None
            self.debuggingThreadStateHandle = None
            return

        (
            self.logbotframe,
            self.stopframe,
            self.currentframe,
            self.debuggingThreadStateHandle,
        ) = self.recursiveData[0]
        self.recursiveData = self.recursiveData[1:]

    def SetupAXDebugging(self, baseFrame=None, userFrame=None):
        """Get ready for potential debugging.  Must be called on the thread
        that is being debugged.
        """
        # userFrame is for non AXScript debugging.  This is the first frame of the
        # users code.
        if userFrame is None:
            userFrame = baseFrame
        else:
            # We have missed the "dispatch_call" function, so set this up now!
            userFrame.f_locals["__axstack_address__"] = axdebug.GetStackAddress()

        traceenter("SetupAXDebugging", self)
        self._threadprotectlock.acquire()
        try:
            thisThread = win32api.GetCurrentThreadId()
            if self.debuggingThread is None:
                self.debuggingThread = thisThread
            else:
                if self.debuggingThread != thisThread:
                    trace("SetupAXDebugging called on other thread - ignored!")
                    return
                # push our context.
                self.recursiveData.insert(
                    0,
                    (
                        self.logicalbotframe,
                        self.stopframe,
                        self.currentframe,
                        self.debuggingThreadStateHandle,
                    ),
                )
        finally:
            self._threadprotectlock.release()

        trace("SetupAXDebugging has base frame as", _dumpf(baseFrame))
        self.botframe = baseFrame
        self.stopframe = userFrame
        self.logicalbotframe = baseFrame
        self.currentframe = None
        self.debuggingThreadStateHandle = axdebug.GetThreadStateHandle()

        self._BreakFlagsChanged()

    # RemoteDebugApplicationEvents
    def OnConnectDebugger(self, appDebugger):
        traceenter("OnConnectDebugger", appDebugger)
        self.appDebugger = appDebugger
        # Reflect output to appDebugger
        writefunc = lambda s: appDebugger.onDebugOutput(s)
        sys.stdout = OutputReflector(sys.stdout, writefunc)
        sys.stderr = OutputReflector(sys.stderr, writefunc)

    def OnDisconnectDebugger(self):
        traceenter("OnDisconnectDebugger")
        # Stop reflecting output
        if isinstance(sys.stdout, OutputReflector):
            sys.stdout = sys.stdout.file
        if isinstance(sys.stderr, OutputReflector):
            sys.stderr = sys.stderr.file
        self.appDebugger = None
        self.set_quit()

    def OnSetName(self, name):
        traceenter("OnSetName", name)

    def OnDebugOutput(self, string):
        traceenter("OnDebugOutput", string)

    def OnClose(self):
        traceenter("OnClose")

    def OnEnterBreakPoint(self, rdat):
        traceenter("OnEnterBreakPoint", rdat)

    def OnLeaveBreakPoint(self, rdat):
        traceenter("OnLeaveBreakPoint", rdat)

    def OnCreateThread(self, rdat):
        traceenter("OnCreateThread", rdat)

    def OnDestroyThread(self, rdat):
        traceenter("OnDestroyThread", rdat)

    def OnBreakFlagChange(self, abf, rdat):
        traceenter("Debugger OnBreakFlagChange", abf, rdat)
        self.breakFlags = abf
        self._BreakFlagsChanged()

    def _BreakFlagsChanged(self):
        traceenter(
            f"_BreakFlagsChanged to {self.breakFlags} "
            + f"with our thread = {self.debuggingThread}, "
            + f"and debugging thread = {win32api.GetCurrentThreadId()}"
        )
        trace("_BreakFlagsChanged has breaks", self.breaks)
        # If a request comes on our debugging thread, then do it now!
        # if self.debuggingThread!=win32api.GetCurrentThreadId():
        #     return

        if len(self.breaks) or self.breakFlags:
            if self.logicalbotframe:
                trace("BreakFlagsChange with bot frame", _dumpf(self.logicalbotframe))
                # We have frames not to be debugged (eg, Scripting engine frames
                # (sys.settrace will be set when out logicalbotframe is hit -
                #  this may not be the right thing to do, as it may not cause the
                #  immediate break we desire.)
                self.logicalbotframe.f_trace = self.trace_dispatch
            else:
                trace("BreakFlagsChanged, but no bottom frame")
                if self.stopframe is not None:
                    self.stopframe.f_trace = self.trace_dispatch
            # If we have the thread-state for the thread being debugged, then
            # we dynamically set its trace function - it is possible that the thread
            # being debugged is in a blocked call (eg, a message box) and we
            # want to hit the debugger the instant we return
        if (
            self.debuggingThreadStateHandle is not None
            and self.breakFlags
            and self.debuggingThread != win32api.GetCurrentThreadId()
        ):
            axdebug.SetThreadStateTrace(
                self.debuggingThreadStateHandle, self.trace_dispatch
            )

    def _OnSetBreakPoint(self, key, codeContext, bps, lineNo):
        traceenter("_OnSetBreakPoint", self, key, codeContext, bps, lineNo)
        if bps == axdebug.BREAKPOINT_ENABLED:
            problem = self.set_break(key, lineNo)
            if problem:
                print("*** set_break failed -", problem)
            trace("_OnSetBreakPoint just set BP and has breaks", self.breaks)
        else:
            self.clear_break(key, lineNo)
        self._BreakFlagsChanged()
        trace("_OnSetBreakPoint leaving with breaks", self.breaks)


def Debugger():
    global g_adb
    if g_adb is None:
        g_adb = Adb()
    return g_adb

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\discuss_service\transports\rest.py ===
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


from google.ai.generativelanguage_v1beta2.types import discuss_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import DiscussServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class DiscussServiceRestInterceptor:
    """Interceptor for DiscussService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the DiscussServiceRestTransport.

    .. code-block:: python
        class MyCustomDiscussServiceInterceptor(DiscussServiceRestInterceptor):
            def pre_count_message_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_message_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_message(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_message(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = DiscussServiceRestTransport(interceptor=MyCustomDiscussServiceInterceptor())
        client = DiscussServiceClient(transport=transport)


    """

    def pre_count_message_tokens(
        self,
        request: discuss_service.CountMessageTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.CountMessageTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_count_message_tokens(
        self, response: discuss_service.CountMessageTokensResponse
    ) -> discuss_service.CountMessageTokensResponse:
        """Post-rpc interceptor for count_message_tokens

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_message(
        self,
        request: discuss_service.GenerateMessageRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[discuss_service.GenerateMessageRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_message

        Override in a subclass to manipulate the request or metadata
        before they are sent to the DiscussService server.
        """
        return request, metadata

    def post_generate_message(
        self, response: discuss_service.GenerateMessageResponse
    ) -> discuss_service.GenerateMessageResponse:
        """Post-rpc interceptor for generate_message

        Override in a subclass to manipulate the response
        after it is returned by the DiscussService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class DiscussServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: DiscussServiceRestInterceptor


class DiscussServiceRestTransport(DiscussServiceTransport):
    """REST backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

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
        interceptor: Optional[DiscussServiceRestInterceptor] = None,
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
        self._interceptor = interceptor or DiscussServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CountMessageTokens(DiscussServiceRestStub):
        def __hash__(self):
            return hash("CountMessageTokens")

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
            request: discuss_service.CountMessageTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.CountMessageTokensResponse:
            r"""Call the count message tokens method over HTTP.

            Args:
                request (~.discuss_service.CountMessageTokensRequest):
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
                ~.discuss_service.CountMessageTokensResponse:
                    A response from ``CountMessageTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta2/{model=models/*}:countMessageTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_message_tokens(
                request, metadata
            )
            pb_request = discuss_service.CountMessageTokensRequest.pb(request)
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
            resp = discuss_service.CountMessageTokensResponse()
            pb_resp = discuss_service.CountMessageTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_message_tokens(resp)
            return resp

    class _GenerateMessage(DiscussServiceRestStub):
        def __hash__(self):
            return hash("GenerateMessage")

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
            request: discuss_service.GenerateMessageRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> discuss_service.GenerateMessageResponse:
            r"""Call the generate message method over HTTP.

            Args:
                request (~.discuss_service.GenerateMessageRequest):
                    The request object. Request to generate a message
                response from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.discuss_service.GenerateMessageResponse:
                    The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta2/{model=models/*}:generateMessage",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_message(
                request, metadata
            )
            pb_request = discuss_service.GenerateMessageRequest.pb(request)
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
            resp = discuss_service.GenerateMessageResponse()
            pb_resp = discuss_service.GenerateMessageResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_message(resp)
            return resp

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountMessageTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateMessage(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("DiscussServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\llm\llm.py ===
import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import sys

import litellm

litellm.suppress_debug_info = True
litellm.REPEATED_STREAMING_CHUNK_LIMIT = 99999999

import json
import logging
import subprocess
import time
import uuid

import requests
import tokentrim as tt

from .run_text_llm import run_text_llm

# from .run_function_calling_llm import run_function_calling_llm
from .run_tool_calling_llm import run_tool_calling_llm
from .utils.convert_to_openai_messages import convert_to_openai_messages

# Create or get the logger
logger = logging.getLogger("LiteLLM")


class SuppressDebugFilter(logging.Filter):
    def filter(self, record):
        # Suppress only the specific message containing the keywords
        if "cost map" in record.getMessage():
            return False  # Suppress this log message
        return True  # Allow all other messages


class Llm:
    """
    A stateless LMC-style LLM with some helpful properties.
    """

    def __init__(self, interpreter):
        # Add the filter to the logger
        logger.addFilter(SuppressDebugFilter())

        # Store a reference to parent interpreter
        self.interpreter = interpreter

        # OpenAI-compatible chat completions "endpoint"
        self.completions = fixed_litellm_completions

        # Settings
        self.model = "gpt-4o"
        self.temperature = 0

        self.supports_vision = None  # Will try to auto-detect
        self.vision_renderer = (
            self.interpreter.computer.vision.query
        )  # Will only use if supports_vision is False

        self.supports_functions = None  # Will try to auto-detect
        self.execution_instructions = "To execute code on the user's machine, write a markdown code block. Specify the language after the ```. You will receive the output. Use any programming language."  # If supports_functions is False, this will be added to the system message

        # Optional settings
        self.context_window = None
        self.max_tokens = None
        self.api_base = None
        self.api_key = None
        self.api_version = None
        self._is_loaded = False

        # Budget manager powered by LiteLLM
        self.max_budget = None

    def run(self, messages):
        """
        We're responsible for formatting the call into the llm.completions object,
        starting with LMC messages in interpreter.messages, going to OpenAI compatible messages into the llm,
        respecting whether it's a vision or function model, respecting its context window and max tokens, etc.

        And then processing its output, whether it's a function or non function calling model, into LMC format.
        """

        if not self._is_loaded:
            self.load()

        if (
            self.max_tokens is not None
            and self.context_window is not None
            and self.max_tokens > self.context_window
        ):
            print(
                "Warning: max_tokens is larger than context_window. Setting max_tokens to be 0.2 times the context_window."
            )
            self.max_tokens = int(0.2 * self.context_window)

        # Assertions
        assert (
            messages[0]["role"] == "system"
        ), "First message must have the role 'system'"
        for msg in messages[1:]:
            assert (
                msg["role"] != "system"
            ), "No message after the first can have the role 'system'"

        model = self.model
        if model in [
            "claude-3.5",
            "claude-3-5",
            "claude-3.5-sonnet",
            "claude-3-5-sonnet",
        ]:
            model = "claude-3-5-sonnet-20240620"
            self.model = "claude-3-5-sonnet-20240620"
        # Setup our model endpoint
        if model == "i":
            model = "openai/i"
            if not hasattr(self.interpreter, "conversation_id"):  # Only do this once
                self.context_window = 7000
                self.api_key = "x"
                self.max_tokens = 1000
                self.api_base = "https://api.openinterpreter.com/v0"
                self.interpreter.conversation_id = str(uuid.uuid4())

        # Detect function support
        if self.supports_functions == None:
            try:
                if litellm.supports_function_calling(model):
                    self.supports_functions = True
                else:
                    self.supports_functions = False
            except:
                self.supports_functions = False

        # Detect vision support
        if self.supports_vision == None:
            try:
                if litellm.supports_vision(model):
                    self.supports_vision = True
                else:
                    self.supports_vision = False
            except:
                self.supports_vision = False

        # Trim image messages if they're there
        image_messages = [msg for msg in messages if msg["type"] == "image"]
        if self.supports_vision:
            if self.interpreter.os:
                # Keep only the last two images if the interpreter is running in OS mode
                if len(image_messages) > 1:
                    for img_msg in image_messages[:-2]:
                        messages.remove(img_msg)
                        if self.interpreter.verbose:
                            print("Removing image message!")
            else:
                # Delete all the middle ones (leave only the first and last 2 images) from messages_for_llm
                if len(image_messages) > 3:
                    for img_msg in image_messages[1:-2]:
                        messages.remove(img_msg)
                        if self.interpreter.verbose:
                            print("Removing image message!")
                # Idea: we could set detail: low for the middle messages, instead of deleting them
        elif self.supports_vision == False and self.vision_renderer:
            for img_msg in image_messages:
                if img_msg["format"] != "description":
                    self.interpreter.display_message("\n  *Viewing image...*\n")

                    if img_msg["format"] == "path":
                        precursor = f"The image I'm referring to ({img_msg['content']}) contains the following: "
                        if self.interpreter.computer.import_computer_api:
                            postcursor = f"\nIf you want to ask questions about the image, run `computer.vision.query(path='{img_msg['content']}', query='(ask any question here)')` and a vision AI will answer it."
                        else:
                            postcursor = ""
                    else:
                        precursor = "Imagine I have just shown you an image with this description: "
                        postcursor = ""

                    try:
                        image_description = self.vision_renderer(lmc=img_msg)
                        ocr = self.interpreter.computer.vision.ocr(lmc=img_msg)

                        # It would be nice to format this as a message to the user and display it like: "I see: image_description"

                        img_msg["content"] = (
                            precursor
                            + image_description
                            + "\n---\nI've OCR'd the image, this is the result (this may or may not be relevant. If it's not relevant, ignore this): '''\n"
                            + ocr
                            + "\n'''"
                            + postcursor
                        )
                        img_msg["format"] = "description"

                    except ImportError:
                        print(
                            "\nTo use local vision, run `pip install 'open-interpreter[local]'`.\n"
                        )
                        img_msg["format"] = "description"
                        img_msg["content"] = ""

        # Convert to OpenAI messages format
        messages = convert_to_openai_messages(
            messages,
            function_calling=self.supports_functions,
            vision=self.supports_vision,
            shrink_images=self.interpreter.shrink_images,
            interpreter=self.interpreter,
        )

        system_message = messages[0]["content"]
        messages = messages[1:]

        # Trim messages
        try:
            if self.context_window and self.max_tokens:
                trim_to_be_this_many_tokens = (
                    self.context_window - self.max_tokens - 25
                )  # arbitrary buffer
                messages = tt.trim(
                    messages,
                    system_message=system_message,
                    max_tokens=trim_to_be_this_many_tokens,
                )
            elif self.context_window and not self.max_tokens:
                # Just trim to the context window if max_tokens not set
                messages = tt.trim(
                    messages,
                    system_message=system_message,
                    max_tokens=self.context_window,
                )
            else:
                try:
                    messages = tt.trim(
                        messages, system_message=system_message, model=model
                    )
                except:
                    if len(messages) == 1:
                        if self.interpreter.in_terminal_interface:
                            self.interpreter.display_message(
                                """
**We were unable to determine the context window of this model.** Defaulting to 8000.

If your model can handle more, run `interpreter --context_window {token limit} --max_tokens {max tokens per response}`.

Continuing...
                            """
                            )
                        else:
                            self.interpreter.display_message(
                                """
**We were unable to determine the context window of this model.** Defaulting to 8000.

If your model can handle more, run `self.context_window = {token limit}`.

Also please set `self.max_tokens = {max tokens per response}`.

Continuing...
                            """
                            )
                    messages = tt.trim(
                        messages, system_message=system_message, max_tokens=8000
                    )
        except:
            # If we're trimming messages, this won't work.
            # If we're trimming from a model we don't know, this won't work.
            # Better not to fail until `messages` is too big, just for frustrations sake, I suppose.

            # Reunite system message with messages
            messages = [{"role": "system", "content": system_message}] + messages

            pass

        # If there should be a system message, there should be a system message!
        # Empty system messages appear to be deleted :(
        if system_message == "":
            if messages[0]["role"] != "system":
                messages = [{"role": "system", "content": system_message}] + messages

        ## Start forming the request

        params = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        # Optional inputs
        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        if self.api_version:
            params["api_version"] = self.api_version
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        if self.temperature:
            params["temperature"] = self.temperature
        if hasattr(self.interpreter, "conversation_id"):
            params["conversation_id"] = self.interpreter.conversation_id

        # Set some params directly on LiteLLM
        if self.max_budget:
            litellm.max_budget = self.max_budget
        if self.interpreter.verbose:
            litellm.set_verbose = True

        if (
            self.interpreter.debug == True and False  # DISABLED
        ):  # debug will equal "server" if we're debugging the server specifically
            print("\n\n\nOPENAI COMPATIBLE MESSAGES:\n\n\n")
            for message in messages:
                if len(str(message)) > 5000:
                    print(str(message)[:200] + "...")
                else:
                    print(message)
                print("\n")
            print("\n\n\n")

        if self.supports_functions:
            # yield from run_function_calling_llm(self, params)
            yield from run_tool_calling_llm(self, params)
        else:
            yield from run_text_llm(self, params)

    # If you change model, set _is_loaded to false
    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value
        self._is_loaded = False

    def load(self):
        if self._is_loaded:
            return

        if self.model.startswith("ollama/") and not ":" in self.model:
            self.model = self.model + ":latest"

        self._is_loaded = True

        if self.model.startswith("ollama/"):
            model_name = self.model.replace("ollama/", "")
            api_base = getattr(self, "api_base", None) or os.getenv(
                "OLLAMA_HOST", "http://localhost:11434"
            )
            names = []
            try:
                # List out all downloaded ollama models. Will fail if ollama isn't installed
                response = requests.get(f"{api_base}/api/tags")
                if response.ok:
                    data = response.json()
                    names = [
                        model["name"]
                        for model in data["models"]
                        if "name" in model and model["name"]
                    ]

            except Exception as e:
                print(str(e))
                self.interpreter.display_message(
                    f"> Ollama not found\n\nPlease download Ollama from [ollama.com](https://ollama.com/) to use `{model_name}`.\n"
                )
                exit()

            # Download model if not already installed
            if model_name not in names:
                self.interpreter.display_message(f"\nDownloading {model_name}...\n")
                requests.post(f"{api_base}/api/pull", json={"name": model_name})

            # Get context window if not set
            if self.context_window == None:
                response = requests.post(
                    f"{api_base}/api/show", json={"name": model_name}
                )
                model_info = response.json().get("model_info", {})
                context_length = None
                for key in model_info:
                    if "context_length" in key:
                        context_length = model_info[key]
                        break
                if context_length is not None:
                    self.context_window = context_length
            if self.max_tokens == None:
                if self.context_window != None:
                    self.max_tokens = int(self.context_window * 0.2)

            # Send a ping, which will actually load the model
            model_name = model_name.replace(":latest", "")
            print(f"Loading {model_name}...\n")

            old_max_tokens = self.max_tokens
            self.max_tokens = 1
            self.interpreter.computer.ai.chat("ping")
            self.max_tokens = old_max_tokens

            self.interpreter.display_message("*Model loaded.*\n")

        # Validate LLM should be moved here!!

        if self.context_window == None:
            try:
                model_info = litellm.get_model_info(model=self.model)
                self.context_window = model_info["max_input_tokens"]
                if self.max_tokens == None:
                    self.max_tokens = min(
                        int(self.context_window * 0.2), model_info["max_output_tokens"]
                    )
            except:
                pass


def fixed_litellm_completions(**params):
    """
    Just uses a dummy API key, since we use litellm without an API key sometimes.
    Hopefully they will fix this!
    """

    if "local" in params.get("model"):
        # Kinda hacky, but this helps sometimes
        params["stop"] = ["<|assistant|>", "<|end|>", "<|eot_id|>"]

    if params.get("model") == "i" and "conversation_id" in params:
        litellm.drop_params = (
            False  # If we don't do this, litellm will drop this param!
        )
    else:
        litellm.drop_params = True

    params["model"] = params["model"].replace(":latest", "")

    # Run completion
    attempts = 4
    first_error = None

    params["num_retries"] = 0

    for attempt in range(attempts):
        try:
            yield from litellm.completion(**params)
            return  # If the completion is successful, exit the function
        except KeyboardInterrupt:
            print("Exiting...")
            sys.exit(0)
        except Exception as e:
            if attempt == 0:
                # Store the first error
                first_error = e
            if (
                isinstance(e, litellm.exceptions.AuthenticationError)
                and "api_key" not in params
            ):
                print(
                    "LiteLLM requires an API key. Trying again with a dummy API key. In the future, if this fixes it, please set a dummy API key to prevent this message. (e.g `interpreter --api_key x` or `self.api_key = 'x'`)"
                )
                # So, let's try one more time with a dummy API key:
                params["api_key"] = "x"
            if attempt == 1:
                # Try turning up the temperature?
                params["temperature"] = params.get("temperature", 0.0) + 0.1

    if first_error is not None:
        raise first_error  # If all attempts fail, raise the first error

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\chat\converse_handler.py ===
import json
import urllib
from typing import Any, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObject
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.utils import ModelResponse
from litellm.utils import CustomStreamWrapper

from ..base_aws_llm import BaseAWSLLM, Credentials
from ..common_utils import BedrockError
from .invoke_handler import AWSEventStreamDecoder, MockResponseIterator, make_call


def make_sync_call(
    client: Optional[HTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj: LiteLLMLoggingObject,
    json_mode: Optional[bool] = False,
    fake_stream: bool = False,
):
    if client is None:
        client = _get_httpx_client()  # Create a new client if none provided

    response = client.post(
        api_base,
        headers=headers,
        data=data,
        stream=not fake_stream,
        logging_obj=logging_obj,
    )

    if response.status_code != 200:
        raise BedrockError(
            status_code=response.status_code, message=str(response.read())
        )

    if fake_stream:
        model_response: (
            ModelResponse
        ) = litellm.AmazonConverseConfig()._transform_response(
            model=model,
            response=response,
            model_response=litellm.ModelResponse(),
            stream=True,
            logging_obj=logging_obj,
            optional_params={},
            api_key="",
            data=data,
            messages=messages,
            encoding=litellm.encoding,
        )  # type: ignore
        completion_stream: Any = MockResponseIterator(
            model_response=model_response, json_mode=json_mode
        )
    else:
        decoder = AWSEventStreamDecoder(model=model)
        completion_stream = decoder.iter_bytes(response.iter_bytes(chunk_size=1024))

    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response="first stream response received",
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


class BedrockConverseLLM(BaseAWSLLM):
    def __init__(self) -> None:
        super().__init__()

    def encode_model_id(self, model_id: str) -> str:
        """
        Double encode the model ID to ensure it matches the expected double-encoded format.
        Args:
            model_id (str): The model ID to encode.
        Returns:
            str: The double-encoded model ID.
        """
        return urllib.parse.quote(model_id, safe="")  # type: ignore

    async def async_streaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj,
        stream,
        optional_params: dict,
        litellm_params: dict,
        credentials: Credentials,
        logger_fn=None,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
        fake_stream: bool = False,
        json_mode: Optional[bool] = False,
    ) -> CustomStreamWrapper:
        request_data = await litellm.AmazonConverseConfig()._async_transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )
        data = json.dumps(request_data)

        prepped = self.get_request_headers(
            credentials=credentials,
            aws_region_name=litellm_params.get("aws_region_name") or "us-west-2",
            extra_headers=headers,
            endpoint_url=api_base,
            data=data,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": dict(prepped.headers),
            },
        )

        completion_stream = await make_call(
            client=client,
            api_base=api_base,
            headers=dict(prepped.headers),
            data=data,
            model=model,
            messages=messages,
            logging_obj=logging_obj,
            fake_stream=fake_stream,
            json_mode=json_mode,
        )
        streaming_response = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider="bedrock",
            logging_obj=logging_obj,
        )
        return streaming_response

    async def async_completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj: LiteLLMLoggingObject,
        stream,
        optional_params: dict,
        litellm_params: dict,
        credentials: Credentials,
        logger_fn=None,
        headers: dict = {},
        client: Optional[AsyncHTTPHandler] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        request_data = await litellm.AmazonConverseConfig()._async_transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )
        data = json.dumps(request_data)

        prepped = self.get_request_headers(
            credentials=credentials,
            aws_region_name=litellm_params.get("aws_region_name") or "us-west-2",
            extra_headers=headers,
            endpoint_url=api_base,
            data=data,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": prepped.headers,
            },
        )

        headers = dict(prepped.headers)
        if client is None or not isinstance(client, AsyncHTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = get_async_httpx_client(
                params=_params, llm_provider=litellm.LlmProviders.BEDROCK
            )
        else:
            client = client  # type: ignore

        try:
            response = await client.post(
                url=api_base,
                headers=headers,
                data=data,
                logging_obj=logging_obj,
            )  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return litellm.AmazonConverseConfig()._transform_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream if isinstance(stream, bool) else False,
            logging_obj=logging_obj,
            api_key="",
            data=data,
            messages=messages,
            optional_params=optional_params,
            encoding=encoding,
        )

    def completion(  # noqa: PLR0915
        self,
        model: str,
        messages: list,
        api_base: Optional[str],
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        encoding,
        logging_obj: LiteLLMLoggingObject,
        optional_params: dict,
        acompletion: bool,
        timeout: Optional[Union[float, httpx.Timeout]],
        litellm_params: dict,
        logger_fn=None,
        extra_headers: Optional[dict] = None,
        client: Optional[Union[AsyncHTTPHandler, HTTPHandler]] = None,
    ):
        ## SETUP ##
        stream = optional_params.pop("stream", None)
        unencoded_model_id = optional_params.pop("model_id", None)
        fake_stream = optional_params.pop("fake_stream", False)
        json_mode = optional_params.get("json_mode", False)
        if unencoded_model_id is not None:
            modelId = self.encode_model_id(model_id=unencoded_model_id)
        else:
            modelId = self.encode_model_id(model_id=model)

        if stream is True and "ai21" in modelId:
            fake_stream = True

        ### SET REGION NAME ###
        aws_region_name = self._get_aws_region_name(
            optional_params=optional_params,
            model=model,
            model_id=unencoded_model_id,
        )

        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        aws_bedrock_runtime_endpoint = optional_params.pop(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)
        optional_params.pop("aws_region_name", None)

        litellm_params[
            "aws_region_name"
        ] = aws_region_name  # [DO NOT DELETE] important for async calls

        credentials: Credentials = self.get_credentials(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region_name=aws_region_name,
            aws_session_name=aws_session_name,
            aws_profile_name=aws_profile_name,
            aws_role_name=aws_role_name,
            aws_web_identity_token=aws_web_identity_token,
            aws_sts_endpoint=aws_sts_endpoint,
        )

        ### SET RUNTIME ENDPOINT ###
        endpoint_url, proxy_endpoint_url = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=aws_bedrock_runtime_endpoint,
            aws_region_name=aws_region_name,
        )
        if (stream is not None and stream is True) and not fake_stream:
            endpoint_url = f"{endpoint_url}/model/{modelId}/converse-stream"
            proxy_endpoint_url = f"{proxy_endpoint_url}/model/{modelId}/converse-stream"
        else:
            endpoint_url = f"{endpoint_url}/model/{modelId}/converse"
            proxy_endpoint_url = f"{proxy_endpoint_url}/model/{modelId}/converse"

        ## COMPLETION CALL
        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}

        ### ROUTING (ASYNC, STREAMING, SYNC)
        if acompletion:
            if isinstance(client, HTTPHandler):
                client = None
            if stream is True:
                return self.async_streaming(
                    model=model,
                    messages=messages,
                    api_base=proxy_endpoint_url,
                    model_response=model_response,
                    encoding=encoding,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=True,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    timeout=timeout,
                    client=client,
                    json_mode=json_mode,
                    fake_stream=fake_stream,
                    credentials=credentials,
                )  # type: ignore
            ### ASYNC COMPLETION
            return self.async_completion(
                model=model,
                messages=messages,
                api_base=proxy_endpoint_url,
                model_response=model_response,
                encoding=encoding,
                logging_obj=logging_obj,
                optional_params=optional_params,
                stream=stream,  # type: ignore
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                headers=headers,
                timeout=timeout,
                client=client,
                credentials=credentials,
            )  # type: ignore

        ## TRANSFORMATION ##

        _data = litellm.AmazonConverseConfig()._transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )
        data = json.dumps(_data)

        prepped = self.get_request_headers(
            credentials=credentials,
            aws_region_name=aws_region_name,
            extra_headers=extra_headers,
            endpoint_url=proxy_endpoint_url,
            data=data,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": proxy_endpoint_url,
                "headers": prepped.headers,
            },
        )
        if client is None or isinstance(client, AsyncHTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = _get_httpx_client(_params)  # type: ignore
        else:
            client = client

        if stream is not None and stream is True:
            completion_stream = make_sync_call(
                client=(
                    client
                    if client is not None and isinstance(client, HTTPHandler)
                    else None
                ),
                api_base=proxy_endpoint_url,
                headers=prepped.headers,  # type: ignore
                data=data,
                model=model,
                messages=messages,
                logging_obj=logging_obj,
                json_mode=json_mode,
                fake_stream=fake_stream,
            )
            streaming_response = CustomStreamWrapper(
                completion_stream=completion_stream,
                model=model,
                custom_llm_provider="bedrock",
                logging_obj=logging_obj,
            )

            return streaming_response

        ### COMPLETION

        try:
            response = client.post(
                url=proxy_endpoint_url,
                headers=prepped.headers,
                data=data,
                logging_obj=logging_obj,
            )  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return litellm.AmazonConverseConfig()._transform_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream if isinstance(stream, bool) else False,
            logging_obj=logging_obj,
            api_key="",
            data=data,
            messages=messages,
            optional_params=optional_params,
            encoding=encoding,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\csound.py ===
"""
    pygments.lexers.csound
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Csound languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, default, include, using, words
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, Punctuation, \
    String, Text, Whitespace
from pygments.lexers._csound_builtins import OPCODES, DEPRECATED_OPCODES, REMOVED_OPCODES
from pygments.lexers.html import HtmlLexer
from pygments.lexers.python import PythonLexer
from pygments.lexers.scripting import LuaLexer

__all__ = ['CsoundScoreLexer', 'CsoundOrchestraLexer', 'CsoundDocumentLexer']

newline = (r'((?:(?:;|//).*)*)(\n)', bygroups(Comment.Single, Text))


class CsoundLexer(RegexLexer):
    url = 'https://csound.com/'

    tokens = {
        'whitespace': [
            (r'[ \t]+', Whitespace),
            (r'/[*](?:.|\n)*?[*]/', Comment.Multiline),
            (r'(?:;|//).*$', Comment.Single),
            (r'(\\)(\n)', bygroups(Text, Whitespace))
        ],

        'preprocessor directives': [
            (r'#(?:e(?:nd(?:if)?|lse)\b|##)|@@?[ \t]*\d+', Comment.Preproc),
            (r'#includestr', Comment.Preproc, 'includestr directive'),
            (r'#include', Comment.Preproc, 'include directive'),
            (r'#[ \t]*define', Comment.Preproc, 'define directive'),
            (r'#(?:ifn?def|undef)\b', Comment.Preproc, 'macro directive')
        ],

        'include directive': [
            include('whitespace'),
            (r'([^ \t]).*?\1', String, '#pop')
        ],
        'includestr directive': [
            include('whitespace'),
            (r'"', String, ('#pop', 'quoted string'))
        ],

        'define directive': [
            (r'\n', Whitespace),
            include('whitespace'),
            (r'([A-Z_a-z]\w*)(\()', bygroups(Comment.Preproc, Punctuation),
             ('#pop', 'macro parameter name list')),
            (r'[A-Z_a-z]\w*', Comment.Preproc, ('#pop', 'before macro body'))
        ],
        'macro parameter name list': [
            include('whitespace'),
            (r'[A-Z_a-z]\w*', Comment.Preproc),
            (r"['#]", Punctuation),
            (r'\)', Punctuation, ('#pop', 'before macro body'))
        ],
        'before macro body': [
            (r'\n', Whitespace),
            include('whitespace'),
            (r'#', Punctuation, ('#pop', 'macro body'))
        ],
        'macro body': [
            (r'(?:\\(?!#)|[^#\\]|\n)+', Comment.Preproc),
            (r'\\#', Comment.Preproc),
            (r'(?<!\\)#', Punctuation, '#pop')
        ],

        'macro directive': [
            include('whitespace'),
            (r'[A-Z_a-z]\w*', Comment.Preproc, '#pop')
        ],

        'macro uses': [
            (r'(\$[A-Z_a-z]\w*\.?)(\()', bygroups(Comment.Preproc, Punctuation),
             'macro parameter value list'),
            (r'\$[A-Z_a-z]\w*(?:\.|\b)', Comment.Preproc)
        ],
        'macro parameter value list': [
            (r'(?:[^\'#"{()]|\{(?!\{))+', Comment.Preproc),
            (r"['#]", Punctuation),
            (r'"', String, 'macro parameter value quoted string'),
            (r'\{\{', String, 'macro parameter value braced string'),
            (r'\(', Comment.Preproc, 'macro parameter value parenthetical'),
            (r'\)', Punctuation, '#pop')
        ],
        'macro parameter value quoted string': [
            (r"\\[#'()]", Comment.Preproc),
            (r"[#'()]", Error),
            include('quoted string')
        ],
        'macro parameter value braced string': [
            (r"\\[#'()]", Comment.Preproc),
            (r"[#'()]", Error),
            include('braced string')
        ],
        'macro parameter value parenthetical': [
            (r'(?:[^\\()]|\\\))+', Comment.Preproc),
            (r'\(', Comment.Preproc, '#push'),
            (r'\)', Comment.Preproc, '#pop')
        ],

        'whitespace and macro uses': [
            include('whitespace'),
            include('macro uses')
        ],

        'numbers': [
            (r'\d+[Ee][+-]?\d+|(\d+\.\d*|\d*\.\d+)([Ee][+-]?\d+)?', Number.Float),
            (r'(0[Xx])([0-9A-Fa-f]+)', bygroups(Keyword.Type, Number.Hex)),
            (r'\d+', Number.Integer)
        ],

        'quoted string': [
            (r'"', String, '#pop'),
            (r'[^"$]+', String),
            include('macro uses'),
            (r'[$]', String)
        ],

        'braced string': [
            # Do nothing. This must be defined in subclasses.
        ]
    }


class CsoundScoreLexer(CsoundLexer):
    """
    For `Csound <https://csound.com>`_ scores.
    """

    name = 'Csound Score'
    aliases = ['csound-score', 'csound-sco']
    filenames = ['*.sco']
    version_added = '2.1'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            include('whitespace and macro uses'),
            include('preprocessor directives'),

            (r'[aBbCdefiqstvxy]', Keyword),
            # There is also a w statement that is generated internally and should not be
            # used; see https://github.com/csound/csound/issues/750.

            (r'z', Keyword.Constant),
            # z is a constant equal to 800,000,000,000. 800 billion seconds is about
            # 25,367.8 years. See also
            # https://csound.com/docs/manual/ScoreTop.html and
            # https://github.com/csound/csound/search?q=stof+path%3AEngine+filename%3Asread.c.

            (r'([nNpP][pP])(\d+)', bygroups(Keyword, Number.Integer)),

            (r'[mn]', Keyword, 'mark statement'),

            include('numbers'),
            (r'[!+\-*/^%&|<>#~.]', Operator),
            (r'[()\[\]]', Punctuation),
            (r'"', String, 'quoted string'),
            (r'\{', Comment.Preproc, 'loop after left brace'),
        ],

        'mark statement': [
            include('whitespace and macro uses'),
            (r'[A-Z_a-z]\w*', Name.Label),
            (r'\n', Whitespace, '#pop')
        ],

        'loop after left brace': [
            include('whitespace and macro uses'),
            (r'\d+', Number.Integer, ('#pop', 'loop after repeat count')),
        ],
        'loop after repeat count': [
            include('whitespace and macro uses'),
            (r'[A-Z_a-z]\w*', Comment.Preproc, ('#pop', 'loop'))
        ],
        'loop': [
            (r'\}', Comment.Preproc, '#pop'),
            include('root')
        ],

        # Braced strings are not allowed in Csound scores, but this is needed because the
        # superclass includes it.
        'braced string': [
            (r'\}\}', String, '#pop'),
            (r'[^}]|\}(?!\})', String)
        ]
    }


class CsoundOrchestraLexer(CsoundLexer):
    """
    For `Csound <https://csound.com>`_ orchestras.
    """

    name = 'Csound Orchestra'
    aliases = ['csound', 'csound-orc']
    filenames = ['*.orc', '*.udo']
    version_added = '2.1'

    user_defined_opcodes = set()

    def opcode_name_callback(lexer, match):
        opcode = match.group(0)
        lexer.user_defined_opcodes.add(opcode)
        yield match.start(), Name.Function, opcode

    def name_callback(lexer, match):
        type_annotation_token = Keyword.Type

        name = match.group(1)
        if name in OPCODES or name in DEPRECATED_OPCODES or name in REMOVED_OPCODES:
            yield match.start(), Name.Builtin, name
        elif name in lexer.user_defined_opcodes:
            yield match.start(), Name.Function, name
        else:
            type_annotation_token = Name
            name_match = re.search(r'^(g?[afikSw])(\w+)', name)
            if name_match:
                yield name_match.start(1), Keyword.Type, name_match.group(1)
                yield name_match.start(2), Name, name_match.group(2)
            else:
                yield match.start(), Name, name

        if match.group(2):
            yield match.start(2), Punctuation, match.group(2)
            yield match.start(3), type_annotation_token, match.group(3)

    tokens = {
        'root': [
            (r'\n', Whitespace),

            (r'^([ \t]*)(\w+)(:)([ \t]+|$)', bygroups(Whitespace, Name.Label, Punctuation, Whitespace)),

            include('whitespace and macro uses'),
            include('preprocessor directives'),

            (r'\binstr\b', Keyword.Declaration, 'instrument numbers and identifiers'),
            (r'\bopcode\b', Keyword.Declaration, 'after opcode keyword'),
            (r'\b(?:end(?:in|op))\b', Keyword.Declaration),

            include('partial statements')
        ],

        'partial statements': [
            (r'\b(?:0dbfs|A4|k(?:r|smps)|nchnls(?:_i)?|sr)\b', Name.Variable.Global),

            include('numbers'),

            (r'\+=|-=|\*=|/=|<<|>>|<=|>=|==|!=|&&|\|\||[~¬]|[=!+\-*/^%&|<>#?:]', Operator),
            (r'[(),\[\]]', Punctuation),

            (r'"', String, 'quoted string'),
            (r'\{\{', String, 'braced string'),

            (words((
                'do', 'else', 'elseif', 'endif', 'enduntil', 'fi', 'if', 'ithen', 'kthen',
                'od', 'then', 'until', 'while',
                ), prefix=r'\b', suffix=r'\b'), Keyword),
            (words(('return', 'rireturn'), prefix=r'\b', suffix=r'\b'), Keyword.Pseudo),

            (r'\b[ik]?goto\b', Keyword, 'goto label'),
            (r'\b(r(?:einit|igoto)|tigoto)(\(|\b)', bygroups(Keyword.Pseudo, Punctuation),
             'goto label'),
            (r'\b(c(?:g|in?|k|nk?)goto)(\(|\b)', bygroups(Keyword.Pseudo, Punctuation),
             ('goto label', 'goto argument')),
            (r'\b(timout)(\(|\b)', bygroups(Keyword.Pseudo, Punctuation),
             ('goto label', 'goto argument', 'goto argument')),
            (r'\b(loop_[gl][et])(\(|\b)', bygroups(Keyword.Pseudo, Punctuation),
             ('goto label', 'goto argument', 'goto argument', 'goto argument')),

            (r'\bprintk?s\b', Name.Builtin, 'prints opcode'),
            (r'\b(?:readscore|scoreline(?:_i)?)\b', Name.Builtin, 'Csound score opcode'),
            (r'\bpyl?run[it]?\b', Name.Builtin, 'Python opcode'),
            (r'\blua_(?:exec|opdef)\b', Name.Builtin, 'Lua opcode'),
            (r'\bp\d+\b', Name.Variable.Instance),
            (r'\b([A-Z_a-z]\w*)(?:(:)([A-Za-z]))?\b', name_callback)
        ],

        'instrument numbers and identifiers': [
            include('whitespace and macro uses'),
            (r'\d+|[A-Z_a-z]\w*', Name.Function),
            (r'[+,]', Punctuation),
            (r'\n', Whitespace, '#pop')
        ],

        'after opcode keyword': [
            include('whitespace and macro uses'),
            (r'[A-Z_a-z]\w*', opcode_name_callback, ('#pop', 'opcode type signatures')),
            (r'\n', Whitespace, '#pop')
        ],
        'opcode type signatures': [
            include('whitespace and macro uses'),

            # https://github.com/csound/csound/search?q=XIDENT+path%3AEngine+filename%3Acsound_orc.lex
            (r'0|[afijkKoOpPStV\[\]]+', Keyword.Type),

            (r',', Punctuation),
            (r'\n', Whitespace, '#pop')
        ],

        'quoted string': [
            (r'"', String, '#pop'),
            (r'[^\\"$%)]+', String),
            include('macro uses'),
            include('escape sequences'),
            include('format specifiers'),
            (r'[\\$%)]', String)
        ],
        'braced string': [
            (r'\}\}', String, '#pop'),
            (r'(?:[^\\%)}]|\}(?!\}))+', String),
            include('escape sequences'),
            include('format specifiers'),
            (r'[\\%)]', String)
        ],
        'escape sequences': [
            # https://github.com/csound/csound/search?q=unquote_string+path%3AEngine+filename%3Acsound_orc_compile.c
            (r'\\(?:[\\abnrt"]|[0-7]{1,3})', String.Escape)
        ],
        # Format specifiers are highlighted in all strings, even though only
        #   fprintks        https://csound.com/docs/manual/fprintks.html
        #   fprints         https://csound.com/docs/manual/fprints.html
        #   printf/printf_i https://csound.com/docs/manual/printf.html
        #   printks         https://csound.com/docs/manual/printks.html
        #   prints          https://csound.com/docs/manual/prints.html
        #   sprintf         https://csound.com/docs/manual/sprintf.html
        #   sprintfk        https://csound.com/docs/manual/sprintfk.html
        # work with strings that contain format specifiers. In addition, these opcodes’
        # handling of format specifiers is inconsistent:
        #   - fprintks and fprints accept %a and %A specifiers, and accept %s specifiers
        #     starting in Csound 6.15.0.
        #   - printks and prints accept %a and %A specifiers, but don’t accept %s
        #     specifiers.
        #   - printf, printf_i, sprintf, and sprintfk don’t accept %a and %A specifiers,
        #     but accept %s specifiers.
        # See https://github.com/csound/csound/issues/747 for more information.
        'format specifiers': [
            (r'%[#0\- +]*\d*(?:\.\d+)?[AE-GXac-giosux]', String.Interpol),
            (r'%%', String.Escape)
        ],

        'goto argument': [
            include('whitespace and macro uses'),
            (r',', Punctuation, '#pop'),
            include('partial statements')
        ],
        'goto label': [
            include('whitespace and macro uses'),
            (r'\w+', Name.Label, '#pop'),
            default('#pop')
        ],

        'prints opcode': [
            include('whitespace and macro uses'),
            (r'"', String, 'prints quoted string'),
            default('#pop')
        ],
        'prints quoted string': [
            (r'\\\\[aAbBnNrRtT]', String.Escape),
            (r'%[!nNrRtT]|[~^]{1,2}', String.Escape),
            include('quoted string')
        ],

        'Csound score opcode': [
            include('whitespace and macro uses'),
            (r'"', String, 'quoted string'),
            (r'\{\{', String, 'Csound score'),
            (r'\n', Whitespace, '#pop')
        ],
        'Csound score': [
            (r'\}\}', String, '#pop'),
            (r'([^}]+)|\}(?!\})', using(CsoundScoreLexer))
        ],

        'Python opcode': [
            include('whitespace and macro uses'),
            (r'"', String, 'quoted string'),
            (r'\{\{', String, 'Python'),
            (r'\n', Whitespace, '#pop')
        ],
        'Python': [
            (r'\}\}', String, '#pop'),
            (r'([^}]+)|\}(?!\})', using(PythonLexer))
        ],

        'Lua opcode': [
            include('whitespace and macro uses'),
            (r'"', String, 'quoted string'),
            (r'\{\{', String, 'Lua'),
            (r'\n', Whitespace, '#pop')
        ],
        'Lua': [
            (r'\}\}', String, '#pop'),
            (r'([^}]+)|\}(?!\})', using(LuaLexer))
        ]
    }


class CsoundDocumentLexer(RegexLexer):
    """
    For Csound documents.
    """

    name = 'Csound Document'
    aliases = ['csound-document', 'csound-csd']
    filenames = ['*.csd']
    url = 'https://csound.com'
    version_added = '2.1'

    # These tokens are based on those in XmlLexer in pygments/lexers/html.py. Making
    # CsoundDocumentLexer a subclass of XmlLexer rather than RegexLexer may seem like a
    # better idea, since Csound Document files look like XML files. However, Csound
    # Documents can contain Csound comments (preceded by //, for example) before and
    # after the root element, unescaped bitwise AND & and less than < operators, etc. In
    # other words, while Csound Document files look like XML files, they may not actually
    # be XML files.
    tokens = {
        'root': [
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'(?:;|//).*$', Comment.Single),
            (r'[^/;<]+|/(?!/)', Text),

            (r'<\s*CsInstruments', Name.Tag, ('orchestra', 'tag')),
            (r'<\s*CsScore', Name.Tag, ('score', 'tag')),
            (r'<\s*[Hh][Tt][Mm][Ll]', Name.Tag, ('HTML', 'tag')),

            (r'<\s*[\w:.-]+', Name.Tag, 'tag'),
            (r'<\s*/\s*[\w:.-]+\s*>', Name.Tag)
        ],

        'orchestra': [
            (r'<\s*/\s*CsInstruments\s*>', Name.Tag, '#pop'),
            (r'(.|\n)+?(?=<\s*/\s*CsInstruments\s*>)', using(CsoundOrchestraLexer))
        ],
        'score': [
            (r'<\s*/\s*CsScore\s*>', Name.Tag, '#pop'),
            (r'(.|\n)+?(?=<\s*/\s*CsScore\s*>)', using(CsoundScoreLexer))
        ],
        'HTML': [
            (r'<\s*/\s*[Hh][Tt][Mm][Ll]\s*>', Name.Tag, '#pop'),
            (r'(.|\n)+?(?=<\s*/\s*[Hh][Tt][Mm][Ll]\s*>)', using(HtmlLexer))
        ],

        'tag': [
            (r'\s+', Whitespace),
            (r'[\w.:-]+\s*=', Name.Attribute, 'attr'),
            (r'/?\s*>', Name.Tag, '#pop')
        ],
        'attr': [
            (r'\s+', Whitespace),
            (r'".*?"', String, '#pop'),
            (r"'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop')
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\hdl.py ===
"""
    pygments.lexers.hdl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for hardware descriptor languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, include, using, this, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['VerilogLexer', 'SystemVerilogLexer', 'VhdlLexer']


class VerilogLexer(RegexLexer):
    """
    For verilog source code with preprocessor directives.
    """
    name = 'verilog'
    aliases = ['verilog', 'v']
    filenames = ['*.v']
    mimetypes = ['text/x-verilog']
    url = 'https://en.wikipedia.org/wiki/Verilog'
    version_added = '1.4'

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'

    tokens = {
        'root': [
            (r'^\s*`define', Comment.Preproc, 'macro'),
            (r'\s+', Whitespace),
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'[{}#@]', Punctuation),
            (r'L?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'([0-9]+)|(\'h)[0-9a-fA-F]+', Number.Hex),
            (r'([0-9]+)|(\'b)[01]+', Number.Bin),
            (r'([0-9]+)|(\'d)[0-9]+', Number.Integer),
            (r'([0-9]+)|(\'o)[0-7]+', Number.Oct),
            (r'\'[01xz]', Number),
            (r'\d+[Ll]?', Number.Integer),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.;\']', Punctuation),
            (r'`[a-zA-Z_]\w*', Name.Constant),

            (r'^(\s*)(package)(\s+)', bygroups(Whitespace, Keyword.Namespace, Text)),
            (r'^(\s*)(import)(\s+)', bygroups(Whitespace, Keyword.Namespace, Text),
             'import'),

            (words((
                'always', 'always_comb', 'always_ff', 'always_latch', 'and',
                'assign', 'automatic', 'begin', 'break', 'buf', 'bufif0', 'bufif1',
                'case', 'casex', 'casez', 'cmos', 'const', 'continue', 'deassign',
                'default', 'defparam', 'disable', 'do', 'edge', 'else', 'end', 'endcase',
                'endfunction', 'endgenerate', 'endmodule', 'endpackage', 'endprimitive',
                'endspecify', 'endtable', 'endtask', 'enum', 'event', 'final', 'for',
                'force', 'forever', 'fork', 'function', 'generate', 'genvar', 'highz0',
                'highz1', 'if', 'initial', 'inout', 'input', 'integer', 'join', 'large',
                'localparam', 'macromodule', 'medium', 'module', 'nand', 'negedge',
                'nmos', 'nor', 'not', 'notif0', 'notif1', 'or', 'output', 'packed',
                'parameter', 'pmos', 'posedge', 'primitive', 'pull0', 'pull1',
                'pulldown', 'pullup', 'rcmos', 'ref', 'release', 'repeat', 'return',
                'rnmos', 'rpmos', 'rtran', 'rtranif0', 'rtranif1', 'scalared', 'signed',
                'small', 'specify', 'specparam', 'strength', 'string', 'strong0',
                'strong1', 'struct', 'table', 'task', 'tran', 'tranif0', 'tranif1',
                'type', 'typedef', 'unsigned', 'var', 'vectored', 'void', 'wait',
                'weak0', 'weak1', 'while', 'xnor', 'xor'), suffix=r'\b'),
             Keyword),

            (words((
                'accelerate', 'autoexpand_vectornets', 'celldefine', 'default_nettype',
                'else', 'elsif', 'endcelldefine', 'endif', 'endprotect', 'endprotected',
                'expand_vectornets', 'ifdef', 'ifndef', 'include', 'noaccelerate',
                'noexpand_vectornets', 'noremove_gatenames', 'noremove_netnames',
                'nounconnected_drive', 'protect', 'protected', 'remove_gatenames',
                'remove_netnames', 'resetall', 'timescale', 'unconnected_drive',
                'undef'), prefix=r'`', suffix=r'\b'),
             Comment.Preproc),

            (words((
                'bits', 'bitstoreal', 'bitstoshortreal', 'countdrivers', 'display', 'fclose',
                'fdisplay', 'finish', 'floor', 'fmonitor', 'fopen', 'fstrobe', 'fwrite',
                'getpattern', 'history', 'incsave', 'input', 'itor', 'key', 'list', 'log',
                'monitor', 'monitoroff', 'monitoron', 'nokey', 'nolog', 'printtimescale',
                'random', 'readmemb', 'readmemh', 'realtime', 'realtobits', 'reset',
                'reset_count', 'reset_value', 'restart', 'rtoi', 'save', 'scale', 'scope',
                'shortrealtobits', 'showscopes', 'showvariables', 'showvars', 'sreadmemb',
                'sreadmemh', 'stime', 'stop', 'strobe', 'time', 'timeformat', 'write'),
                prefix=r'\$', suffix=r'\b'),
             Name.Builtin),

            (words((
                'byte', 'shortint', 'int', 'longint', 'integer', 'time',
                'bit', 'logic', 'reg', 'supply0', 'supply1', 'tri', 'triand',
                'trior', 'tri0', 'tri1', 'trireg', 'uwire', 'wire', 'wand', 'wor'
                'shortreal', 'real', 'realtime'), suffix=r'\b'),
             Keyword.Type),
            (r'[a-zA-Z_]\w*:(?!:)', Name.Label),
            (r'\$?[a-zA-Z_]\w*', Name),
            (r'\\(\S+)', Name),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Whitespace, '#pop'),
        ],
        'import': [
            (r'[\w:]+\*?', Name.Namespace, '#pop')
        ]
    }

    def analyse_text(text):
        """Verilog code will use one of reg/wire/assign for sure, and that
        is not common elsewhere."""
        result = 0
        if 'reg' in text:
            result += 0.1
        if 'wire' in text:
            result += 0.1
        if 'assign' in text:
            result += 0.1

        return result


class SystemVerilogLexer(RegexLexer):
    """
    Extends verilog lexer to recognise all SystemVerilog keywords from IEEE
    1800-2009 standard.
    """
    name = 'systemverilog'
    aliases = ['systemverilog', 'sv']
    filenames = ['*.sv', '*.svh']
    mimetypes = ['text/x-systemverilog']
    url = 'https://en.wikipedia.org/wiki/SystemVerilog'
    version_added = '1.5'

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'

    tokens = {
        'root': [
            (r'^(\s*)(`define)', bygroups(Whitespace, Comment.Preproc), 'macro'),
            (r'^(\s*)(package)(\s+)', bygroups(Whitespace, Keyword.Namespace, Whitespace)),
            (r'^(\s*)(import)(\s+)', bygroups(Whitespace, Keyword.Namespace, Whitespace), 'import'),

            (r'\s+', Whitespace),
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'[{}#@]', Punctuation),
            (r'L?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),

            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),

            (r'([1-9][_0-9]*)?\s*\'[sS]?[bB]\s*[xXzZ?01][_xXzZ?01]*',
             Number.Bin),
            (r'([1-9][_0-9]*)?\s*\'[sS]?[oO]\s*[xXzZ?0-7][_xXzZ?0-7]*',
             Number.Oct),
            (r'([1-9][_0-9]*)?\s*\'[sS]?[dD]\s*[xXzZ?0-9][_xXzZ?0-9]*',
             Number.Integer),
            (r'([1-9][_0-9]*)?\s*\'[sS]?[hH]\s*[xXzZ?0-9a-fA-F][_xXzZ?0-9a-fA-F]*',
             Number.Hex),

            (r'\'[01xXzZ]', Number),
            (r'[0-9][_0-9]*', Number.Integer),

            (r'[~!%^&*+=|?:<>/-]', Operator),
            (words(('inside', 'dist'), suffix=r'\b'), Operator.Word),

            (r'[()\[\],.;\'$]', Punctuation),
            (r'`[a-zA-Z_]\w*', Name.Constant),

            (words((
                'accept_on', 'alias', 'always', 'always_comb', 'always_ff',
                'always_latch', 'and', 'assert', 'assign', 'assume', 'automatic',
                'before', 'begin', 'bind', 'bins', 'binsof', 'break', 'buf',
                'bufif0', 'bufif1', 'case', 'casex', 'casez', 'cell',
                'checker', 'clocking', 'cmos', 'config',
                'constraint', 'context', 'continue', 'cover', 'covergroup',
                'coverpoint', 'cross', 'deassign', 'default', 'defparam', 'design',
                'disable', 'do', 'edge', 'else', 'end', 'endcase',
                'endchecker', 'endclocking', 'endconfig', 'endfunction',
                'endgenerate', 'endgroup', 'endinterface', 'endmodule', 'endpackage',
                'endprimitive', 'endprogram', 'endproperty', 'endsequence',
                'endspecify', 'endtable', 'endtask', 'enum', 'eventually',
                'expect', 'export', 'extern', 'final', 'first_match',
                'for', 'force', 'foreach', 'forever', 'fork', 'forkjoin', 'function',
                'generate', 'genvar', 'global', 'highz0', 'highz1', 'if', 'iff',
                'ifnone', 'ignore_bins', 'illegal_bins', 'implies', 'implements', 'import',
                'incdir', 'include', 'initial', 'inout', 'input',
                'instance', 'interconnect', 'interface', 'intersect', 'join',
                'join_any', 'join_none', 'large', 'let', 'liblist', 'library',
                'local', 'localparam', 'macromodule', 'matches',
                'medium', 'modport', 'module', 'nand', 'negedge', 'nettype', 'new', 'nexttime',
                'nmos', 'nor', 'noshowcancelled', 'not', 'notif0', 'notif1', 'null',
                'or', 'output', 'package', 'packed', 'parameter', 'pmos', 'posedge',
                'primitive', 'priority', 'program', 'property', 'protected', 'pull0',
                'pull1', 'pulldown', 'pullup', 'pulsestyle_ondetect',
                'pulsestyle_onevent', 'pure', 'rand', 'randc', 'randcase',
                'randsequence', 'rcmos', 'ref',
                'reject_on', 'release', 'repeat', 'restrict', 'return', 'rnmos',
                'rpmos', 'rtran', 'rtranif0', 'rtranif1', 's_always', 's_eventually',
                's_nexttime', 's_until', 's_until_with', 'scalared', 'sequence',
                'showcancelled', 'small', 'soft', 'solve',
                'specify', 'specparam', 'static', 'strong', 'strong0',
                'strong1', 'struct', 'super', 'sync_accept_on',
                'sync_reject_on', 'table', 'tagged', 'task', 'this', 'throughout',
                'timeprecision', 'timeunit', 'tran', 'tranif0', 'tranif1',
                'typedef', 'union', 'unique', 'unique0', 'until',
                'until_with', 'untyped', 'use', 'vectored',
                'virtual', 'wait', 'wait_order', 'weak', 'weak0',
                'weak1', 'while', 'wildcard', 'with', 'within',
                'xnor', 'xor'),
                suffix=r'\b'),
             Keyword),

            (r'(class)(\s+)([a-zA-Z_]\w*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (r'(extends)(\s+)([a-zA-Z_]\w*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (r'(endclass\b)(?:(\s*)(:)(\s*)([a-zA-Z_]\w*))?',
             bygroups(Keyword.Declaration, Whitespace, Punctuation, Whitespace, Name.Class)),

            (words((
                # Variable types
                'bit', 'byte', 'chandle', 'const', 'event', 'int', 'integer',
                'logic', 'longint', 'real', 'realtime', 'reg', 'shortint',
                'shortreal', 'signed', 'string', 'time', 'type', 'unsigned',
                'var', 'void',
                # Net types
                'supply0', 'supply1', 'tri', 'triand', 'trior', 'trireg',
                'tri0', 'tri1', 'uwire', 'wand', 'wire', 'wor'),
                suffix=r'\b'),
             Keyword.Type),

            (words((
                '`__FILE__', '`__LINE__', '`begin_keywords', '`celldefine',
                '`default_nettype', '`define', '`else', '`elsif', '`end_keywords',
                '`endcelldefine', '`endif', '`ifdef', '`ifndef', '`include',
                '`line', '`nounconnected_drive', '`pragma', '`resetall',
                '`timescale', '`unconnected_drive', '`undef', '`undefineall'),
                suffix=r'\b'),
             Comment.Preproc),

            (words((
                # Simulation control tasks (20.2)
                '$exit', '$finish', '$stop',
                # Simulation time functions (20.3)
                '$realtime', '$stime', '$time',
                # Timescale tasks (20.4)
                '$printtimescale', '$timeformat',
                # Conversion functions
                '$bitstoreal', '$bitstoshortreal', '$cast', '$itor',
                '$realtobits', '$rtoi', '$shortrealtobits', '$signed',
                '$unsigned',
                # Data query functions (20.6)
                '$bits', '$isunbounded', '$typename',
                # Array query functions (20.7)
                '$dimensions', '$high', '$increment', '$left', '$low', '$right',
                '$size', '$unpacked_dimensions',
                # Math functions (20.8)
                '$acos', '$acosh', '$asin', '$asinh', '$atan', '$atan2',
                '$atanh', '$ceil', '$clog2', '$cos', '$cosh', '$exp', '$floor',
                '$hypot', '$ln', '$log10', '$pow', '$sin', '$sinh', '$sqrt',
                '$tan', '$tanh',
                # Bit vector system functions (20.9)
                '$countbits', '$countones', '$isunknown', '$onehot', '$onehot0',
                # Severity tasks (20.10)
                '$info', '$error', '$fatal', '$warning',
                # Assertion control tasks (20.12)
                '$assertcontrol', '$assertfailoff', '$assertfailon',
                '$assertkill', '$assertnonvacuouson', '$assertoff', '$asserton',
                '$assertpassoff', '$assertpasson', '$assertvacuousoff',
                # Sampled value system functions (20.13)
                '$changed', '$changed_gclk', '$changing_gclk', '$falling_gclk',
                '$fell', '$fell_gclk', '$future_gclk', '$past', '$past_gclk',
                '$rising_gclk', '$rose', '$rose_gclk', '$sampled', '$stable',
                '$stable_gclk', '$steady_gclk',
                # Coverage control functions (20.14)
                '$coverage_control', '$coverage_get', '$coverage_get_max',
                '$coverage_merge', '$coverage_save', '$get_coverage',
                '$load_coverage_db', '$set_coverage_db_name',
                # Probabilistic distribution functions (20.15)
                '$dist_chi_square', '$dist_erlang', '$dist_exponential',
                '$dist_normal', '$dist_poisson', '$dist_t', '$dist_uniform',
                '$random',
                # Stochastic analysis tasks and functions (20.16)
                '$q_add', '$q_exam', '$q_full', '$q_initialize', '$q_remove',
                # PLA modeling tasks (20.17)
                '$async$and$array', '$async$and$plane', '$async$nand$array',
                '$async$nand$plane', '$async$nor$array', '$async$nor$plane',
                '$async$or$array', '$async$or$plane', '$sync$and$array',
                '$sync$and$plane', '$sync$nand$array', '$sync$nand$plane',
                '$sync$nor$array', '$sync$nor$plane', '$sync$or$array',
                '$sync$or$plane',
                # Miscellaneous tasks and functions (20.18)
                '$system',
                # Display tasks (21.2)
                '$display', '$displayb', '$displayh', '$displayo', '$monitor',
                '$monitorb', '$monitorh', '$monitoro', '$monitoroff',
                '$monitoron', '$strobe', '$strobeb', '$strobeh', '$strobeo',
                '$write', '$writeb', '$writeh', '$writeo',
                # File I/O tasks and functions (21.3)
                '$fclose', '$fdisplay', '$fdisplayb', '$fdisplayh',
                '$fdisplayo', '$feof', '$ferror', '$fflush', '$fgetc', '$fgets',
                '$fmonitor', '$fmonitorb', '$fmonitorh', '$fmonitoro', '$fopen',
                '$fread', '$fscanf', '$fseek', '$fstrobe', '$fstrobeb',
                '$fstrobeh', '$fstrobeo', '$ftell', '$fwrite', '$fwriteb',
                '$fwriteh', '$fwriteo', '$rewind', '$sformat', '$sformatf',
                '$sscanf', '$swrite', '$swriteb', '$swriteh', '$swriteo',
                '$ungetc',
                # Memory load tasks (21.4)
                '$readmemb', '$readmemh',
                # Memory dump tasks (21.5)
                '$writememb', '$writememh',
                # Command line input (21.6)
                '$test$plusargs', '$value$plusargs',
                # VCD tasks (21.7)
                '$dumpall', '$dumpfile', '$dumpflush', '$dumplimit', '$dumpoff',
                '$dumpon', '$dumpports', '$dumpportsall', '$dumpportsflush',
                '$dumpportslimit', '$dumpportsoff', '$dumpportson', '$dumpvars',
                ), suffix=r'\b'),
             Name.Builtin),

            (r'[a-zA-Z_]\w*:(?!:)', Name.Label),
            (r'\$?[a-zA-Z_]\w*', Name),
            (r'\\(\S+)', Name),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?$', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Whitespace, '#pop'),
        ],
        'import': [
            (r'[\w:]+\*?', Name.Namespace, '#pop')
        ]
    }


class VhdlLexer(RegexLexer):
    """
    For VHDL source code.
    """
    name = 'vhdl'
    aliases = ['vhdl']
    filenames = ['*.vhdl', '*.vhd']
    mimetypes = ['text/x-vhdl']
    url = 'https://en.wikipedia.org/wiki/VHDL'
    version_added = '1.5'
    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'--.*?$', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r"'(U|X|0|1|Z|W|L|H|-)'", String.Char),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r"'[a-z_]\w*", Name.Attribute),
            (r'[()\[\],.;\']', Punctuation),
            (r'"[^\n\\"]*"', String),

            (r'(library)(\s+)([a-z_]\w*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(use)(\s+)(entity)', bygroups(Keyword, Whitespace, Keyword)),
            (r'(use)(\s+)([a-z_][\w.]*\.)(all)',
             bygroups(Keyword, Whitespace, Name.Namespace, Keyword)),
            (r'(use)(\s+)([a-z_][\w.]*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(std|ieee)(\.[a-z_]\w*)',
             bygroups(Name.Namespace, Name.Namespace)),
            (words(('std', 'ieee', 'work'), suffix=r'\b'),
             Name.Namespace),
            (r'(entity|component)(\s+)([a-z_]\w*)',
             bygroups(Keyword, Whitespace, Name.Class)),
            (r'(architecture|configuration)(\s+)([a-z_]\w*)(\s+)'
             r'(of)(\s+)([a-z_]\w*)(\s+)(is)',
             bygroups(Keyword, Whitespace, Name.Class, Whitespace, Keyword, Whitespace,
                      Name.Class, Whitespace, Keyword)),
            (r'([a-z_]\w*)(:)(\s+)(process|for)',
             bygroups(Name.Class, Operator, Whitespace, Keyword)),
            (r'(end)(\s+)', bygroups(using(this), Whitespace), 'endblock'),

            include('types'),
            include('keywords'),
            include('numbers'),

            (r'[a-z_]\w*', Name),
        ],
        'endblock': [
            include('keywords'),
            (r'[a-z_]\w*', Name.Class),
            (r'\s+', Whitespace),
            (r';', Punctuation, '#pop'),
        ],
        'types': [
            (words((
                'boolean', 'bit', 'character', 'severity_level', 'integer', 'time',
                'delay_length', 'natural', 'positive', 'string', 'bit_vector',
                'file_open_kind', 'file_open_status', 'std_ulogic', 'std_ulogic_vector',
                'std_logic', 'std_logic_vector', 'signed', 'unsigned'), suffix=r'\b'),
             Keyword.Type),
        ],
        'keywords': [
            (words((
                'abs', 'access', 'after', 'alias', 'all', 'and',
                'architecture', 'array', 'assert', 'attribute', 'begin', 'block',
                'body', 'buffer', 'bus', 'case', 'component', 'configuration',
                'constant', 'disconnect', 'downto', 'else', 'elsif', 'end',
                'entity', 'exit', 'file', 'for', 'function', 'generate',
                'generic', 'group', 'guarded', 'if', 'impure', 'in',
                'inertial', 'inout', 'is', 'label', 'library', 'linkage',
                'literal', 'loop', 'map', 'mod', 'nand', 'new',
                'next', 'nor', 'not', 'null', 'of', 'on',
                'open', 'or', 'others', 'out', 'package', 'port',
                'postponed', 'procedure', 'process', 'pure', 'range', 'record',
                'register', 'reject', 'rem', 'return', 'rol', 'ror', 'select',
                'severity', 'signal', 'shared', 'sla', 'sll', 'sra',
                'srl', 'subtype', 'then', 'to', 'transport', 'type',
                'units', 'until', 'use', 'variable', 'wait', 'when',
                'while', 'with', 'xnor', 'xor'), suffix=r'\b'),
             Keyword),
        ],
        'numbers': [
            (r'\d{1,2}#[0-9a-f_]+#?', Number.Integer),
            (r'\d+', Number.Integer),
            (r'(\d+\.\d*|\.\d+|\d+)E[+-]?\d+', Number.Float),
            (r'X"[0-9a-f_]+"', Number.Hex),
            (r'O"[0-7_]+"', Number.Oct),
            (r'B"[01_]+"', Number.Bin),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\git\index\fun.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Standalone functions to accompany the index implementation and make it more
versatile."""

__all__ = [
    "write_cache",
    "read_cache",
    "write_tree_from_cache",
    "entry_key",
    "stat_mode_to_index_mode",
    "S_IFGITLINK",
    "run_commit_hook",
    "hook_path",
]

from io import BytesIO
import os
import os.path as osp
from pathlib import Path
from stat import S_IFDIR, S_IFLNK, S_IFMT, S_IFREG, S_ISDIR, S_ISLNK, S_IXUSR
import subprocess
import sys

from gitdb.base import IStream
from gitdb.typ import str_tree_type

from git.cmd import handle_process_output, safer_popen
from git.compat import defenc, force_bytes, force_text, safe_decode
from git.exc import HookExecutionError, UnmergedEntriesError
from git.objects.fun import (
    traverse_tree_recursive,
    traverse_trees_recursive,
    tree_to_stream,
)
from git.util import IndexFileSHA1Writer, finalize_process

from .typ import BaseIndexEntry, IndexEntry, CE_NAMEMASK, CE_STAGESHIFT
from .util import pack, unpack

# typing -----------------------------------------------------------------------------

from typing import Dict, IO, List, Sequence, TYPE_CHECKING, Tuple, Type, Union, cast

from git.types import PathLike

if TYPE_CHECKING:
    from git.db import GitCmdObjectDB
    from git.objects.tree import TreeCacheTup

    from .base import IndexFile

# ------------------------------------------------------------------------------------

S_IFGITLINK = S_IFLNK | S_IFDIR
"""Flags for a submodule."""

CE_NAMEMASK_INV = ~CE_NAMEMASK


def hook_path(name: str, git_dir: PathLike) -> str:
    """:return: path to the given named hook in the given git repository directory"""
    return osp.join(git_dir, "hooks", name)


def _has_file_extension(path: str) -> str:
    return osp.splitext(path)[1]


def run_commit_hook(name: str, index: "IndexFile", *args: str) -> None:
    """Run the commit hook of the given name. Silently ignore hooks that do not exist.

    :param name:
        Name of hook, like ``pre-commit``.

    :param index:
        :class:`~git.index.base.IndexFile` instance.

    :param args:
        Arguments passed to hook file.

    :raise git.exc.HookExecutionError:
    """
    hp = hook_path(name, index.repo.git_dir)
    if not os.access(hp, os.X_OK):
        return

    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = safe_decode(str(index.path))
    env["GIT_EDITOR"] = ":"
    cmd = [hp]
    try:
        if sys.platform == "win32" and not _has_file_extension(hp):
            # Windows only uses extensions to determine how to open files
            # (doesn't understand shebangs). Try using bash to run the hook.
            relative_hp = Path(hp).relative_to(index.repo.working_dir).as_posix()
            cmd = ["bash.exe", relative_hp]

        process = safer_popen(
            cmd + list(args),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=index.repo.working_dir,
        )
    except Exception as ex:
        raise HookExecutionError(hp, ex) from ex
    else:
        stdout_list: List[str] = []
        stderr_list: List[str] = []
        handle_process_output(process, stdout_list.append, stderr_list.append, finalize_process)
        stdout = "".join(stdout_list)
        stderr = "".join(stderr_list)
        if process.returncode != 0:
            stdout = force_text(stdout, defenc)
            stderr = force_text(stderr, defenc)
            raise HookExecutionError(hp, process.returncode, stderr, stdout)
    # END handle return code


def stat_mode_to_index_mode(mode: int) -> int:
    """Convert the given mode from a stat call to the corresponding index mode and
    return it."""
    if S_ISLNK(mode):  # symlinks
        return S_IFLNK
    if S_ISDIR(mode) or S_IFMT(mode) == S_IFGITLINK:  # submodules
        return S_IFGITLINK
    return S_IFREG | (mode & S_IXUSR and 0o755 or 0o644)  # blobs with or without executable bit


def write_cache(
    entries: Sequence[Union[BaseIndexEntry, "IndexEntry"]],
    stream: IO[bytes],
    extension_data: Union[None, bytes] = None,
    ShaStreamCls: Type[IndexFileSHA1Writer] = IndexFileSHA1Writer,
) -> None:
    """Write the cache represented by entries to a stream.

    :param entries:
        **Sorted** list of entries.

    :param stream:
        Stream to wrap into the AdapterStreamCls - it is used for final output.

    :param ShaStreamCls:
        Type to use when writing to the stream. It produces a sha while writing to it,
        before the data is passed on to the wrapped stream.

    :param extension_data:
        Any kind of data to write as a trailer, it must begin a 4 byte identifier,
        followed by its size (4 bytes).
    """
    # Wrap the stream into a compatible writer.
    stream_sha = ShaStreamCls(stream)

    tell = stream_sha.tell
    write = stream_sha.write

    # Header
    version = 2
    write(b"DIRC")
    write(pack(">LL", version, len(entries)))

    # Body
    for entry in entries:
        beginoffset = tell()
        write(entry.ctime_bytes)  # ctime
        write(entry.mtime_bytes)  # mtime
        path_str = str(entry.path)
        path: bytes = force_bytes(path_str, encoding=defenc)
        plen = len(path) & CE_NAMEMASK  # Path length
        assert plen == len(path), "Path %s too long to fit into index" % entry.path
        flags = plen | (entry.flags & CE_NAMEMASK_INV)  # Clear possible previous values.
        write(
            pack(
                ">LLLLLL20sH",
                entry.dev,
                entry.inode,
                entry.mode,
                entry.uid,
                entry.gid,
                entry.size,
                entry.binsha,
                flags,
            )
        )
        write(path)
        real_size = (tell() - beginoffset + 8) & ~7
        write(b"\0" * ((beginoffset + real_size) - tell()))
    # END for each entry

    # Write previously cached extensions data.
    if extension_data is not None:
        stream_sha.write(extension_data)

    # Write the sha over the content.
    stream_sha.write_sha()


def read_header(stream: IO[bytes]) -> Tuple[int, int]:
    """Return tuple(version_long, num_entries) from the given stream."""
    type_id = stream.read(4)
    if type_id != b"DIRC":
        raise AssertionError("Invalid index file header: %r" % type_id)
    unpacked = cast(Tuple[int, int], unpack(">LL", stream.read(4 * 2)))
    version, num_entries = unpacked

    # TODO: Handle version 3: extended data, see read-cache.c.
    assert version in (1, 2)
    return version, num_entries


def entry_key(*entry: Union[BaseIndexEntry, PathLike, int]) -> Tuple[PathLike, int]:
    """
    :return:
        Key suitable to be used for the
        :attr:`index.entries <git.index.base.IndexFile.entries>` dictionary.

    :param entry:
        One instance of type BaseIndexEntry or the path and the stage.
    """

    # def is_entry_key_tup(entry_key: Tuple) -> TypeGuard[Tuple[PathLike, int]]:
    #     return isinstance(entry_key, tuple) and len(entry_key) == 2

    if len(entry) == 1:
        entry_first = entry[0]
        assert isinstance(entry_first, BaseIndexEntry)
        return (entry_first.path, entry_first.stage)
    else:
        # assert is_entry_key_tup(entry)
        entry = cast(Tuple[PathLike, int], entry)
        return entry
    # END handle entry


def read_cache(
    stream: IO[bytes],
) -> Tuple[int, Dict[Tuple[PathLike, int], "IndexEntry"], bytes, bytes]:
    """Read a cache file from the given stream.

    :return:
        tuple(version, entries_dict, extension_data, content_sha)

        * *version* is the integer version number.
        * *entries_dict* is a dictionary which maps IndexEntry instances to a path at a
          stage.
        * *extension_data* is ``""`` or 4 bytes of type + 4 bytes of size + size bytes.
        * *content_sha* is a 20 byte sha on all cache file contents.
    """
    version, num_entries = read_header(stream)
    count = 0
    entries: Dict[Tuple[PathLike, int], "IndexEntry"] = {}

    read = stream.read
    tell = stream.tell
    while count < num_entries:
        beginoffset = tell()
        ctime = unpack(">8s", read(8))[0]
        mtime = unpack(">8s", read(8))[0]
        (dev, ino, mode, uid, gid, size, sha, flags) = unpack(">LLLLLL20sH", read(20 + 4 * 6 + 2))
        path_size = flags & CE_NAMEMASK
        path = read(path_size).decode(defenc)

        real_size = (tell() - beginoffset + 8) & ~7
        read((beginoffset + real_size) - tell())
        entry = IndexEntry((mode, sha, flags, path, ctime, mtime, dev, ino, uid, gid, size))
        # entry_key would be the method to use, but we save the effort.
        entries[(path, entry.stage)] = entry
        count += 1
    # END for each entry

    # The footer contains extension data and a sha on the content so far.
    # Keep the extension footer,and verify we have a sha in the end.
    # Extension data format is:
    #   4 bytes ID
    #   4 bytes length of chunk
    #   Repeated 0 - N times
    extension_data = stream.read(~0)
    assert len(extension_data) > 19, (
        "Index Footer was not at least a sha on content as it was only %i bytes in size" % len(extension_data)
    )

    content_sha = extension_data[-20:]

    # Truncate the sha in the end as we will dynamically create it anyway.
    extension_data = extension_data[:-20]

    return (version, entries, extension_data, content_sha)


def write_tree_from_cache(
    entries: List[IndexEntry], odb: "GitCmdObjectDB", sl: slice, si: int = 0
) -> Tuple[bytes, List["TreeCacheTup"]]:
    R"""Create a tree from the given sorted list of entries and put the respective
    trees into the given object database.

    :param entries:
        **Sorted** list of :class:`~git.index.typ.IndexEntry`\s.

    :param odb:
        Object database to store the trees in.

    :param si:
        Start index at which we should start creating subtrees.

    :param sl:
        Slice indicating the range we should process on the entries list.

    :return:
        tuple(binsha, list(tree_entry, ...))

        A tuple of a sha and a list of tree entries being a tuple of hexsha, mode, name.
    """
    tree_items: List["TreeCacheTup"] = []

    ci = sl.start
    end = sl.stop
    while ci < end:
        entry = entries[ci]
        if entry.stage != 0:
            raise UnmergedEntriesError(entry)
        # END abort on unmerged
        ci += 1
        rbound = entry.path.find("/", si)
        if rbound == -1:
            # It's not a tree.
            tree_items.append((entry.binsha, entry.mode, entry.path[si:]))
        else:
            # Find common base range.
            base = entry.path[si:rbound]
            xi = ci
            while xi < end:
                oentry = entries[xi]
                orbound = oentry.path.find("/", si)
                if orbound == -1 or oentry.path[si:orbound] != base:
                    break
                # END abort on base mismatch
                xi += 1
            # END find common base

            # Enter recursion.
            # ci - 1 as we want to count our current item as well.
            sha, _tree_entry_list = write_tree_from_cache(entries, odb, slice(ci - 1, xi), rbound + 1)
            tree_items.append((sha, S_IFDIR, base))

            # Skip ahead.
            ci = xi
        # END handle bounds
    # END for each entry

    # Finally create the tree.
    sio = BytesIO()
    tree_to_stream(tree_items, sio.write)  # Writes to stream as bytes, but doesn't change tree_items.
    sio.seek(0)

    istream = odb.store(IStream(str_tree_type, len(sio.getvalue()), sio))
    return (istream.binsha, tree_items)


def _tree_entry_to_baseindexentry(tree_entry: "TreeCacheTup", stage: int) -> BaseIndexEntry:
    return BaseIndexEntry((tree_entry[1], tree_entry[0], stage << CE_STAGESHIFT, tree_entry[2]))


def aggressive_tree_merge(odb: "GitCmdObjectDB", tree_shas: Sequence[bytes]) -> List[BaseIndexEntry]:
    R"""
    :return:
        List of :class:`~git.index.typ.BaseIndexEntry`\s representing the aggressive
        merge of the given trees. All valid entries are on stage 0, whereas the
        conflicting ones are left on stage 1, 2 or 3, whereas stage 1 corresponds to the
        common ancestor tree, 2 to our tree and 3 to 'their' tree.

    :param tree_shas:
        1, 2 or 3 trees as identified by their binary 20 byte shas. If 1 or two, the
        entries will effectively correspond to the last given tree. If 3 are given, a 3
        way merge is performed.
    """
    out: List[BaseIndexEntry] = []

    # One and two way is the same for us, as we don't have to handle an existing
    # index, instrea
    if len(tree_shas) in (1, 2):
        for entry in traverse_tree_recursive(odb, tree_shas[-1], ""):
            out.append(_tree_entry_to_baseindexentry(entry, 0))
        # END for each entry
        return out
    # END handle single tree

    if len(tree_shas) > 3:
        raise ValueError("Cannot handle %i trees at once" % len(tree_shas))

    # Three trees.
    for base, ours, theirs in traverse_trees_recursive(odb, tree_shas, ""):
        if base is not None:
            # Base version exists.
            if ours is not None:
                # Ours exists.
                if theirs is not None:
                    # It exists in all branches. Ff it was changed in both
                    # its a conflict. Otherwise, we take the changed version.
                    # This should be the most common branch, so it comes first.
                    if (base[0] != ours[0] and base[0] != theirs[0] and ours[0] != theirs[0]) or (
                        base[1] != ours[1] and base[1] != theirs[1] and ours[1] != theirs[1]
                    ):
                        # Changed by both.
                        out.append(_tree_entry_to_baseindexentry(base, 1))
                        out.append(_tree_entry_to_baseindexentry(ours, 2))
                        out.append(_tree_entry_to_baseindexentry(theirs, 3))
                    elif base[0] != ours[0] or base[1] != ours[1]:
                        # Only we changed it.
                        out.append(_tree_entry_to_baseindexentry(ours, 0))
                    else:
                        # Either nobody changed it, or they did. In either
                        # case, use theirs.
                        out.append(_tree_entry_to_baseindexentry(theirs, 0))
                    # END handle modification
                else:
                    if ours[0] != base[0] or ours[1] != base[1]:
                        # They deleted it, we changed it, conflict.
                        out.append(_tree_entry_to_baseindexentry(base, 1))
                        out.append(_tree_entry_to_baseindexentry(ours, 2))
                    # else:
                    #   # We didn't change it, ignore.
                    #   pass
                    # END handle our change
                # END handle theirs
            else:
                if theirs is None:
                    # Deleted in both, its fine - it's out.
                    pass
                else:
                    if theirs[0] != base[0] or theirs[1] != base[1]:
                        # Deleted in ours, changed theirs, conflict.
                        out.append(_tree_entry_to_baseindexentry(base, 1))
                        out.append(_tree_entry_to_baseindexentry(theirs, 3))
                    # END theirs changed
                    # else:
                    #   # Theirs didn't change.
                    #   pass
                # END handle theirs
            # END handle ours
        else:
            # All three can't be None.
            if ours is None:
                # Added in their branch.
                assert theirs is not None
                out.append(_tree_entry_to_baseindexentry(theirs, 0))
            elif theirs is None:
                # Added in our branch.
                out.append(_tree_entry_to_baseindexentry(ours, 0))
            else:
                # Both have it, except for the base, see whether it changed.
                if ours[0] != theirs[0] or ours[1] != theirs[1]:
                    out.append(_tree_entry_to_baseindexentry(ours, 2))
                    out.append(_tree_entry_to_baseindexentry(theirs, 3))
                else:
                    # It was added the same in both.
                    out.append(_tree_entry_to_baseindexentry(ours, 0))
                # END handle two items
            # END handle heads
        # END handle base exists
    # END for each entries tuple

    return out

# === NexusCore/openenv\Lib\site-packages\grpc\beta\_server_adaptations.py ===
# Copyright 2016 gRPC authors.
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
"""Translates gRPC's server-side API into gRPC's server-side Beta API."""

import collections
import threading

import grpc
from grpc import _common
from grpc.beta import _metadata
from grpc.beta import interfaces
from grpc.framework.common import cardinality
from grpc.framework.common import style
from grpc.framework.foundation import abandonment
from grpc.framework.foundation import logging_pool
from grpc.framework.foundation import stream
from grpc.framework.interfaces.face import face

# pylint: disable=too-many-return-statements

_DEFAULT_POOL_SIZE = 8


class _ServerProtocolContext(interfaces.GRPCServicerContext):
    def __init__(self, servicer_context):
        self._servicer_context = servicer_context

    def peer(self):
        return self._servicer_context.peer()

    def disable_next_response_compression(self):
        pass  # TODO(https://github.com/grpc/grpc/issues/4078): design, implement.


class _FaceServicerContext(face.ServicerContext):
    def __init__(self, servicer_context):
        self._servicer_context = servicer_context

    def is_active(self):
        return self._servicer_context.is_active()

    def time_remaining(self):
        return self._servicer_context.time_remaining()

    def add_abortion_callback(self, abortion_callback):
        raise NotImplementedError(
            "add_abortion_callback no longer supported server-side!"
        )

    def cancel(self):
        self._servicer_context.cancel()

    def protocol_context(self):
        return _ServerProtocolContext(self._servicer_context)

    def invocation_metadata(self):
        return _metadata.beta(self._servicer_context.invocation_metadata())

    def initial_metadata(self, initial_metadata):
        self._servicer_context.send_initial_metadata(
            _metadata.unbeta(initial_metadata)
        )

    def terminal_metadata(self, terminal_metadata):
        self._servicer_context.set_terminal_metadata(
            _metadata.unbeta(terminal_metadata)
        )

    def code(self, code):
        self._servicer_context.set_code(code)

    def details(self, details):
        self._servicer_context.set_details(details)


def _adapt_unary_request_inline(unary_request_inline):
    def adaptation(request, servicer_context):
        return unary_request_inline(
            request, _FaceServicerContext(servicer_context)
        )

    return adaptation


def _adapt_stream_request_inline(stream_request_inline):
    def adaptation(request_iterator, servicer_context):
        return stream_request_inline(
            request_iterator, _FaceServicerContext(servicer_context)
        )

    return adaptation


class _Callback(stream.Consumer):
    def __init__(self):
        self._condition = threading.Condition()
        self._values = []
        self._terminated = False
        self._cancelled = False

    def consume(self, value):
        with self._condition:
            self._values.append(value)
            self._condition.notify_all()

    def terminate(self):
        with self._condition:
            self._terminated = True
            self._condition.notify_all()

    def consume_and_terminate(self, value):
        with self._condition:
            self._values.append(value)
            self._terminated = True
            self._condition.notify_all()

    def cancel(self):
        with self._condition:
            self._cancelled = True
            self._condition.notify_all()

    def draw_one_value(self):
        with self._condition:
            while True:
                if self._cancelled:
                    raise abandonment.Abandoned()
                elif self._values:
                    return self._values.pop(0)
                elif self._terminated:
                    return None
                else:
                    self._condition.wait()

    def draw_all_values(self):
        with self._condition:
            while True:
                if self._cancelled:
                    raise abandonment.Abandoned()
                elif self._terminated:
                    all_values = tuple(self._values)
                    self._values = None
                    return all_values
                else:
                    self._condition.wait()


def _run_request_pipe_thread(
    request_iterator, request_consumer, servicer_context
):
    thread_joined = threading.Event()

    def pipe_requests():
        for request in request_iterator:
            if not servicer_context.is_active() or thread_joined.is_set():
                return
            request_consumer.consume(request)
            if not servicer_context.is_active() or thread_joined.is_set():
                return
        request_consumer.terminate()

    request_pipe_thread = threading.Thread(target=pipe_requests)
    request_pipe_thread.daemon = True
    request_pipe_thread.start()


def _adapt_unary_unary_event(unary_unary_event):
    def adaptation(request, servicer_context):
        callback = _Callback()
        if not servicer_context.add_callback(callback.cancel):
            raise abandonment.Abandoned()
        unary_unary_event(
            request,
            callback.consume_and_terminate,
            _FaceServicerContext(servicer_context),
        )
        return callback.draw_all_values()[0]

    return adaptation


def _adapt_unary_stream_event(unary_stream_event):
    def adaptation(request, servicer_context):
        callback = _Callback()
        if not servicer_context.add_callback(callback.cancel):
            raise abandonment.Abandoned()
        unary_stream_event(
            request, callback, _FaceServicerContext(servicer_context)
        )
        while True:
            response = callback.draw_one_value()
            if response is None:
                return
            else:
                yield response

    return adaptation


def _adapt_stream_unary_event(stream_unary_event):
    def adaptation(request_iterator, servicer_context):
        callback = _Callback()
        if not servicer_context.add_callback(callback.cancel):
            raise abandonment.Abandoned()
        request_consumer = stream_unary_event(
            callback.consume_and_terminate,
            _FaceServicerContext(servicer_context),
        )
        _run_request_pipe_thread(
            request_iterator, request_consumer, servicer_context
        )
        return callback.draw_all_values()[0]

    return adaptation


def _adapt_stream_stream_event(stream_stream_event):
    def adaptation(request_iterator, servicer_context):
        callback = _Callback()
        if not servicer_context.add_callback(callback.cancel):
            raise abandonment.Abandoned()
        request_consumer = stream_stream_event(
            callback, _FaceServicerContext(servicer_context)
        )
        _run_request_pipe_thread(
            request_iterator, request_consumer, servicer_context
        )
        while True:
            response = callback.draw_one_value()
            if response is None:
                return
            else:
                yield response

    return adaptation


class _SimpleMethodHandler(
    collections.namedtuple(
        "_MethodHandler",
        (
            "request_streaming",
            "response_streaming",
            "request_deserializer",
            "response_serializer",
            "unary_unary",
            "unary_stream",
            "stream_unary",
            "stream_stream",
        ),
    ),
    grpc.RpcMethodHandler,
):
    pass


def _simple_method_handler(
    implementation, request_deserializer, response_serializer
):
    if implementation.style is style.Service.INLINE:
        if implementation.cardinality is cardinality.Cardinality.UNARY_UNARY:
            return _SimpleMethodHandler(
                False,
                False,
                request_deserializer,
                response_serializer,
                _adapt_unary_request_inline(implementation.unary_unary_inline),
                None,
                None,
                None,
            )
        elif implementation.cardinality is cardinality.Cardinality.UNARY_STREAM:
            return _SimpleMethodHandler(
                False,
                True,
                request_deserializer,
                response_serializer,
                None,
                _adapt_unary_request_inline(implementation.unary_stream_inline),
                None,
                None,
            )
        elif implementation.cardinality is cardinality.Cardinality.STREAM_UNARY:
            return _SimpleMethodHandler(
                True,
                False,
                request_deserializer,
                response_serializer,
                None,
                None,
                _adapt_stream_request_inline(
                    implementation.stream_unary_inline
                ),
                None,
            )
        elif (
            implementation.cardinality is cardinality.Cardinality.STREAM_STREAM
        ):
            return _SimpleMethodHandler(
                True,
                True,
                request_deserializer,
                response_serializer,
                None,
                None,
                None,
                _adapt_stream_request_inline(
                    implementation.stream_stream_inline
                ),
            )
    elif implementation.style is style.Service.EVENT:
        if implementation.cardinality is cardinality.Cardinality.UNARY_UNARY:
            return _SimpleMethodHandler(
                False,
                False,
                request_deserializer,
                response_serializer,
                _adapt_unary_unary_event(implementation.unary_unary_event),
                None,
                None,
                None,
            )
        elif implementation.cardinality is cardinality.Cardinality.UNARY_STREAM:
            return _SimpleMethodHandler(
                False,
                True,
                request_deserializer,
                response_serializer,
                None,
                _adapt_unary_stream_event(implementation.unary_stream_event),
                None,
                None,
            )
        elif implementation.cardinality is cardinality.Cardinality.STREAM_UNARY:
            return _SimpleMethodHandler(
                True,
                False,
                request_deserializer,
                response_serializer,
                None,
                None,
                _adapt_stream_unary_event(implementation.stream_unary_event),
                None,
            )
        elif (
            implementation.cardinality is cardinality.Cardinality.STREAM_STREAM
        ):
            return _SimpleMethodHandler(
                True,
                True,
                request_deserializer,
                response_serializer,
                None,
                None,
                None,
                _adapt_stream_stream_event(implementation.stream_stream_event),
            )
    raise ValueError()


def _flatten_method_pair_map(method_pair_map):
    method_pair_map = method_pair_map or {}
    flat_map = {}
    for method_pair in method_pair_map:
        method = _common.fully_qualified_method(method_pair[0], method_pair[1])
        flat_map[method] = method_pair_map[method_pair]
    return flat_map


class _GenericRpcHandler(grpc.GenericRpcHandler):
    def __init__(
        self,
        method_implementations,
        multi_method_implementation,
        request_deserializers,
        response_serializers,
    ):
        self._method_implementations = _flatten_method_pair_map(
            method_implementations
        )
        self._request_deserializers = _flatten_method_pair_map(
            request_deserializers
        )
        self._response_serializers = _flatten_method_pair_map(
            response_serializers
        )
        self._multi_method_implementation = multi_method_implementation

    def service(self, handler_call_details):
        method_implementation = self._method_implementations.get(
            handler_call_details.method
        )
        if method_implementation is not None:
            return _simple_method_handler(
                method_implementation,
                self._request_deserializers.get(handler_call_details.method),
                self._response_serializers.get(handler_call_details.method),
            )
        elif self._multi_method_implementation is None:
            return None
        else:
            try:
                return None  # TODO(nathaniel): call the multimethod.
            except face.NoSuchMethodError:
                return None


class _Server(interfaces.Server):
    def __init__(self, grpc_server):
        self._grpc_server = grpc_server

    def add_insecure_port(self, address):
        return self._grpc_server.add_insecure_port(address)

    def add_secure_port(self, address, server_credentials):
        return self._grpc_server.add_secure_port(address, server_credentials)

    def start(self):
        self._grpc_server.start()

    def stop(self, grace):
        return self._grpc_server.stop(grace)

    def __enter__(self):
        self._grpc_server.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._grpc_server.stop(None)
        return False


def server(
    service_implementations,
    multi_method_implementation,
    request_deserializers,
    response_serializers,
    thread_pool,
    thread_pool_size,
):
    generic_rpc_handler = _GenericRpcHandler(
        service_implementations,
        multi_method_implementation,
        request_deserializers,
        response_serializers,
    )
    if thread_pool is None:
        effective_thread_pool = logging_pool.pool(
            _DEFAULT_POOL_SIZE if thread_pool_size is None else thread_pool_size
        )
    else:
        effective_thread_pool = thread_pool
    return _Server(
        grpc.server(effective_thread_pool, handlers=(generic_rpc_handler,))
    )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\ollama\completion\transformation.py ===
import json
import time
import uuid
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List, Optional, Union

from httpx._models import Headers, Response

import litellm
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    get_str_from_messages,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    convert_to_ollama_image,
    custom_prompt,
    ollama_pt,
)
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues, ChatCompletionUsageBlock
from litellm.types.utils import (
    GenericStreamingChunk,
    ModelInfoBase,
    ModelResponse,
    ModelResponseStream,
    ProviderField,
)

from ..common_utils import OllamaError, _convert_image

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OllamaConfig(BaseConfig):
    """
    Reference: https://github.com/ollama/ollama/blob/main/docs/api.md#parameters

    The class `OllamaConfig` provides the configuration for the Ollama's API interface. Below are the parameters:

    - `mirostat` (int): Enable Mirostat sampling for controlling perplexity. Default is 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0. Example usage: mirostat 0

    - `mirostat_eta` (float): Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive. Default: 0.1. Example usage: mirostat_eta 0.1

    - `mirostat_tau` (float): Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text. Default: 5.0. Example usage: mirostat_tau 5.0

    - `num_ctx` (int): Sets the size of the context window used to generate the next token. Default: 2048. Example usage: num_ctx 4096

    - `num_gqa` (int): The number of GQA groups in the transformer layer. Required for some models, for example it is 8 for llama2:70b. Example usage: num_gqa 1

    - `num_gpu` (int): The number of layers to send to the GPU(s). On macOS it defaults to 1 to enable metal support, 0 to disable. Example usage: num_gpu 0

    - `num_thread` (int): Sets the number of threads to use during computation. By default, Ollama will detect this for optimal performance. It is recommended to set this value to the number of physical CPU cores your system has (as opposed to the logical number of cores). Example usage: num_thread 8

    - `repeat_last_n` (int): Sets how far back for the model to look back to prevent repetition. Default: 64, 0 = disabled, -1 = num_ctx. Example usage: repeat_last_n 64

    - `repeat_penalty` (float): Sets how strongly to penalize repetitions. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. Default: 1.1. Example usage: repeat_penalty 1.1

    - `temperature` (float): The temperature of the model. Increasing the temperature will make the model answer more creatively. Default: 0.8. Example usage: temperature 0.7

    - `seed` (int): Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt. Example usage: seed 42

    - `stop` (string[]): Sets the stop sequences to use. Example usage: stop "AI assistant:"

    - `tfs_z` (float): Tail free sampling is used to reduce the impact of less probable tokens from the output. A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting. Default: 1. Example usage: tfs_z 1

    - `num_predict` (int): Maximum number of tokens to predict when generating text. Default: 128, -1 = infinite generation, -2 = fill context. Example usage: num_predict 42

    - `top_k` (int): Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative. Default: 40. Example usage: top_k 40

    - `top_p` (float): Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text. Default: 0.9. Example usage: top_p 0.9

    - `system` (string): system prompt for model (overrides what is defined in the Modelfile)

    - `template` (string): the full prompt or prompt template (overrides what is defined in the Modelfile)
    """

    mirostat: Optional[int] = None
    mirostat_eta: Optional[float] = None
    mirostat_tau: Optional[float] = None
    num_ctx: Optional[int] = None
    num_gqa: Optional[int] = None
    num_gpu: Optional[int] = None
    num_thread: Optional[int] = None
    repeat_last_n: Optional[int] = None
    repeat_penalty: Optional[float] = None
    temperature: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[
        list
    ] = None  # stop is a list based on this - https://github.com/ollama/ollama/pull/442
    tfs_z: Optional[float] = None
    num_predict: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    system: Optional[str] = None
    template: Optional[str] = None

    def __init__(
        self,
        mirostat: Optional[int] = None,
        mirostat_eta: Optional[float] = None,
        mirostat_tau: Optional[float] = None,
        num_ctx: Optional[int] = None,
        num_gqa: Optional[int] = None,
        num_gpu: Optional[int] = None,
        num_thread: Optional[int] = None,
        repeat_last_n: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        seed: Optional[int] = None,
        stop: Optional[list] = None,
        tfs_z: Optional[float] = None,
        num_predict: Optional[int] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        system: Optional[str] = None,
        template: Optional[str] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_required_params(self) -> List[ProviderField]:
        """For a given provider, return it's required fields with a description"""
        return [
            ProviderField(
                field_name="base_url",
                field_type="string",
                field_description="Your Ollama API Base",
                field_value="http://10.10.11.249:11434",
            )
        ]

    def get_supported_openai_params(self, model: str):
        return [
            "max_tokens",
            "stream",
            "top_p",
            "temperature",
            "seed",
            "frequency_penalty",
            "stop",
            "response_format",
            "max_completion_tokens",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "max_tokens" or param == "max_completion_tokens":
                optional_params["num_predict"] = value
            if param == "stream":
                optional_params["stream"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "seed":
                optional_params["seed"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            if param == "stop":
                optional_params["stop"] = value
            if param == "response_format" and isinstance(value, dict):
                if value["type"] == "json_object":
                    optional_params["format"] = "json"
                elif value["type"] == "json_schema":
                    optional_params["format"] = value["json_schema"]["schema"]

        return optional_params

    def _supports_function_calling(self, ollama_model_info: dict) -> bool:
        """
        Check if the 'template' field in the ollama_model_info contains a 'tools' or 'function' key.
        """
        _template: str = str(ollama_model_info.get("template", "") or "")
        return "tools" in _template.lower()

    def _get_max_tokens(self, ollama_model_info: dict) -> Optional[int]:
        _model_info: dict = ollama_model_info.get("model_info", {})

        for k, v in _model_info.items():
            if "context_length" in k:
                return v
        return None

    def get_model_info(self, model: str) -> ModelInfoBase:
        """
        curl http://localhost:11434/api/show -d '{
          "name": "mistral"
        }'
        """
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            model = model.split("/", 1)[1]
        api_base = get_secret_str("OLLAMA_API_BASE") or "http://localhost:11434"

        try:
            response = litellm.module_level_client.post(
                url=f"{api_base}/api/show",
                json={"name": model},
            )
        except Exception as e:
            raise Exception(
                f"OllamaError: Error getting model info for {model}. Set Ollama API Base via `OLLAMA_API_BASE` environment variable. Error: {e}"
            )

        model_info = response.json()

        _max_tokens: Optional[int] = self._get_max_tokens(model_info)

        return ModelInfoBase(
            key=model,
            litellm_provider="ollama",
            mode="chat",
            supports_function_calling=self._supports_function_calling(model_info),
            input_cost_per_token=0.0,
            output_cost_per_token=0.0,
            max_tokens=_max_tokens,
            max_input_tokens=_max_tokens,
            max_output_tokens=_max_tokens,
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return OllamaError(
            status_code=status_code, message=error_message, headers=headers
        )

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        response_json = raw_response.json()
        ## RESPONSE OBJECT
        model_response.choices[0].finish_reason = "stop"
        if request_data.get("format", "") == "json":
            response_content = json.loads(response_json["response"])

            # Check if this is a function call format with name/arguments structure
            if (
                isinstance(response_content, dict)
                and "name" in response_content
                and "arguments" in response_content
            ):
                # Handle as function call (original behavior)
                function_call = response_content
                message = litellm.Message(
                    content=None,
                    tool_calls=[
                        {
                            "id": f"call_{str(uuid.uuid4())}",
                            "function": {
                                "name": function_call["name"],
                                "arguments": json.dumps(function_call["arguments"]),
                            },
                            "type": "function",
                        }
                    ],
                )
                model_response.choices[0].message = message  # type: ignore
                model_response.choices[0].finish_reason = "tool_calls"
            else:
                # Handle as regular JSON (new behavior)
                message = litellm.Message(
                    content=json.dumps(response_content),
                )
                model_response.choices[0].message = message  # type: ignore
                model_response.choices[0].finish_reason = "stop"
        else:
            model_response.choices[0].message.content = response_json["response"]  # type: ignore
        model_response.created = int(time.time())
        model_response.model = "ollama/" + model
        _prompt = request_data.get("prompt", "")
        prompt_tokens = response_json.get(
            "prompt_eval_count", len(encoding.encode(_prompt, disallowed_special=()))  # type: ignore
        )
        completion_tokens = response_json.get(
            "eval_count", len(response_json.get("message", dict()).get("content", ""))
        )
        setattr(
            model_response,
            "usage",
            litellm.Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
        return model_response

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        custom_prompt_dict = (
            litellm_params.get("custom_prompt_dict") or litellm.custom_prompt_dict
        )

        text_completion_request = litellm_params.get("text_completion")
        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            ollama_prompt = custom_prompt(
                role_dict=model_prompt_details["roles"],
                initial_prompt_value=model_prompt_details["initial_prompt_value"],
                final_prompt_value=model_prompt_details["final_prompt_value"],
                messages=messages,
            )
        elif text_completion_request:  # handle `/completions` requests
            ollama_prompt = get_str_from_messages(messages=messages)
        else:  # handle `/chat/completions` requests
            modified_prompt = ollama_pt(model=model, messages=messages)
            if isinstance(modified_prompt, dict):
                ollama_prompt, images = (
                    modified_prompt["prompt"],
                    modified_prompt["images"],
                )
                optional_params["images"] = images
            else:
                ollama_prompt = modified_prompt
        stream = optional_params.pop("stream", False)
        format = optional_params.pop("format", None)
        images = optional_params.pop("images", None)
        data = {
            "model": model,
            "prompt": ollama_prompt,
            "options": optional_params,
            "stream": stream,
        }

        if format is not None:
            data["format"] = format
        if images is not None:
            data["images"] = [
                _convert_image(convert_to_ollama_image(image)) for image in images
            ]

        return data

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
        return headers

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        if api_base is None:
            api_base = "http://localhost:11434"
        if api_base.endswith("/api/generate"):
            url = api_base
        else:
            url = f"{api_base}/api/generate"

        return url

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return OllamaTextCompletionResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class OllamaTextCompletionResponseIterator(BaseModelResponseIterator):
    def _handle_string_chunk(
        self, str_line: str
    ) -> Union[GenericStreamingChunk, ModelResponseStream]:
        return self.chunk_parser(json.loads(str_line))

    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            if "error" in chunk:
                raise Exception(f"Ollama Error - {chunk}")

            text = ""
            is_finished = False
            finish_reason = None
            if chunk["done"] is True:
                text = ""
                is_finished = True
                finish_reason = "stop"
                prompt_eval_count: Optional[int] = chunk.get("prompt_eval_count", None)
                eval_count: Optional[int] = chunk.get("eval_count", None)

                usage: Optional[ChatCompletionUsageBlock] = None
                if prompt_eval_count is not None and eval_count is not None:
                    usage = ChatCompletionUsageBlock(
                        prompt_tokens=prompt_eval_count,
                        completion_tokens=eval_count,
                        total_tokens=prompt_eval_count + eval_count,
                    )
                return GenericStreamingChunk(
                    text=text,
                    is_finished=is_finished,
                    finish_reason=finish_reason,
                    usage=usage,
                )
            elif chunk["response"]:
                text = chunk["response"]
                return GenericStreamingChunk(
                    text=text,
                    is_finished=is_finished,
                    finish_reason="stop",
                    usage=None,
                )
            else:
                raise Exception(f"Unable to parse ollama chunk - {chunk}")
        except Exception as e:
            raise e

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\nombank.py ===
# Natural Language Toolkit: NomBank Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Paul Bedaride <paul.bedaride@gmail.com>
#          Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from functools import total_ordering
from xml.etree import ElementTree

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.internals import raise_unorderable_types
from nltk.tree import Tree


class NombankCorpusReader(CorpusReader):
    """
    Corpus reader for the nombank corpus, which augments the Penn
    Treebank with information about the predicate argument structure
    of every noun instance.  The corpus consists of two parts: the
    predicate-argument annotations themselves, and a set of "frameset
    files" which define the argument labels used by the annotations,
    on a per-noun basis.  Each "frameset file" contains one or more
    predicates, such as ``'turn'`` or ``'turn_on'``, each of which is
    divided into coarse-grained word senses called "rolesets".  For
    each "roleset", the frameset file provides descriptions of the
    argument roles, along with examples.
    """

    def __init__(
        self,
        root,
        nomfile,
        framefiles="",
        nounsfile=None,
        parse_fileid_xform=None,
        parse_corpus=None,
        encoding="utf8",
    ):
        """
        :param root: The root directory for this corpus.
        :param nomfile: The name of the file containing the predicate-
            argument annotations (relative to ``root``).
        :param framefiles: A list or regexp specifying the frameset
            fileids for this corpus.
        :param parse_fileid_xform: A transform that should be applied
            to the fileids in this corpus.  This should be a function
            of one argument (a fileid) that returns a string (the new
            fileid).
        :param parse_corpus: The corpus containing the parse trees
            corresponding to this corpus.  These parse trees are
            necessary to resolve the tree pointers used by nombank.
        """

        # If framefiles is specified as a regexp, expand it.
        if isinstance(framefiles, str):
            self._fileids = find_corpus_fileids(root, framefiles)
        self._fileids = list(framefiles)
        # Initialize the corpus reader.
        CorpusReader.__init__(self, root, framefiles, encoding)

        # Record our nom file & nouns file.
        self._nomfile = nomfile
        self._nounsfile = nounsfile
        self._parse_fileid_xform = parse_fileid_xform
        self._parse_corpus = parse_corpus

    def instances(self, baseform=None):
        """
        :return: a corpus view that acts as a list of
            ``NombankInstance`` objects, one for each noun in the corpus.
        """
        kwargs = {}
        if baseform is not None:
            kwargs["instance_filter"] = lambda inst: inst.baseform == baseform
        return StreamBackedCorpusView(
            self.abspath(self._nomfile),
            lambda stream: self._read_instance_block(stream, **kwargs),
            encoding=self.encoding(self._nomfile),
        )

    def lines(self):
        """
        :return: a corpus view that acts as a list of strings, one for
            each line in the predicate-argument annotation file.
        """
        return StreamBackedCorpusView(
            self.abspath(self._nomfile),
            read_line_block,
            encoding=self.encoding(self._nomfile),
        )

    def roleset(self, roleset_id):
        """
        :return: the xml description for the given roleset.
        """
        baseform = roleset_id.split(".")[0]
        baseform = baseform.replace("perc-sign", "%")
        baseform = baseform.replace("oneslashonezero", "1/10").replace(
            "1/10", "1-slash-10"
        )
        framefile = "frames/%s.xml" % baseform
        if framefile not in self.fileids():
            raise ValueError("Frameset file for %s not found" % roleset_id)

        # n.b.: The encoding for XML fileids is specified by the file
        # itself; so we ignore self._encoding here.
        with self.abspath(framefile).open() as fp:
            etree = ElementTree.parse(fp).getroot()
        for roleset in etree.findall("predicate/roleset"):
            if roleset.attrib["id"] == roleset_id:
                return roleset
        raise ValueError(f"Roleset {roleset_id} not found in {framefile}")

    def rolesets(self, baseform=None):
        """
        :return: list of xml descriptions for rolesets.
        """
        if baseform is not None:
            framefile = "frames/%s.xml" % baseform
            if framefile not in self.fileids():
                raise ValueError("Frameset file for %s not found" % baseform)
            framefiles = [framefile]
        else:
            framefiles = self.fileids()

        rsets = []
        for framefile in framefiles:
            # n.b.: The encoding for XML fileids is specified by the file
            # itself; so we ignore self._encoding here.
            with self.abspath(framefile).open() as fp:
                etree = ElementTree.parse(fp).getroot()
            rsets.append(etree.findall("predicate/roleset"))
        return LazyConcatenation(rsets)

    def nouns(self):
        """
        :return: a corpus view that acts as a list of all noun lemmas
            in this corpus (from the nombank.1.0.words file).
        """
        return StreamBackedCorpusView(
            self.abspath(self._nounsfile),
            read_line_block,
            encoding=self.encoding(self._nounsfile),
        )

    def _read_instance_block(self, stream, instance_filter=lambda inst: True):
        block = []

        # Read 100 at a time.
        for i in range(100):
            line = stream.readline().strip()
            if line:
                inst = NombankInstance.parse(
                    line, self._parse_fileid_xform, self._parse_corpus
                )
                if instance_filter(inst):
                    block.append(inst)

        return block


######################################################################
# { Nombank Instance & related datatypes
######################################################################


class NombankInstance:
    def __init__(
        self,
        fileid,
        sentnum,
        wordnum,
        baseform,
        sensenumber,
        predicate,
        predid,
        arguments,
        parse_corpus=None,
    ):
        self.fileid = fileid
        """The name of the file containing the parse tree for this
        instance's sentence."""

        self.sentnum = sentnum
        """The sentence number of this sentence within ``fileid``.
        Indexing starts from zero."""

        self.wordnum = wordnum
        """The word number of this instance's predicate within its
        containing sentence.  Word numbers are indexed starting from
        zero, and include traces and other empty parse elements."""

        self.baseform = baseform
        """The baseform of the predicate."""

        self.sensenumber = sensenumber
        """The sense number of the predicate."""

        self.predicate = predicate
        """A ``NombankTreePointer`` indicating the position of this
        instance's predicate within its containing sentence."""

        self.predid = predid
        """Identifier of the predicate."""

        self.arguments = tuple(arguments)
        """A list of tuples (argloc, argid), specifying the location
        and identifier for each of the predicate's argument in the
        containing sentence.  Argument identifiers are strings such as
        ``'ARG0'`` or ``'ARGM-TMP'``.  This list does *not* contain
        the predicate."""

        self.parse_corpus = parse_corpus
        """A corpus reader for the parse trees corresponding to the
        instances in this nombank corpus."""

    @property
    def roleset(self):
        """The name of the roleset used by this instance's predicate.
        Use ``nombank.roleset() <NombankCorpusReader.roleset>`` to
        look up information about the roleset."""
        r = self.baseform.replace("%", "perc-sign")
        r = r.replace("1/10", "1-slash-10").replace("1-slash-10", "oneslashonezero")
        return f"{r}.{self.sensenumber}"

    def __repr__(self):
        return "<NombankInstance: {}, sent {}, word {}>".format(
            self.fileid,
            self.sentnum,
            self.wordnum,
        )

    def __str__(self):
        s = "{} {} {} {} {}".format(
            self.fileid,
            self.sentnum,
            self.wordnum,
            self.baseform,
            self.sensenumber,
        )
        items = self.arguments + ((self.predicate, "rel"),)
        for argloc, argid in sorted(items):
            s += f" {argloc}-{argid}"
        return s

    def _get_tree(self):
        if self.parse_corpus is None:
            return None
        if self.fileid not in self.parse_corpus.fileids():
            return None
        return self.parse_corpus.parsed_sents(self.fileid)[self.sentnum]

    tree = property(
        _get_tree,
        doc="""
        The parse tree corresponding to this instance, or None if
        the corresponding tree is not available.""",
    )

    @staticmethod
    def parse(s, parse_fileid_xform=None, parse_corpus=None):
        pieces = s.split()
        if len(pieces) < 6:
            raise ValueError("Badly formatted nombank line: %r" % s)

        # Divide the line into its basic pieces.
        (fileid, sentnum, wordnum, baseform, sensenumber) = pieces[:5]

        args = pieces[5:]
        rel = [args.pop(i) for i, p in enumerate(args) if "-rel" in p]
        if len(rel) != 1:
            raise ValueError("Badly formatted nombank line: %r" % s)

        # Apply the fileid selector, if any.
        if parse_fileid_xform is not None:
            fileid = parse_fileid_xform(fileid)

        # Convert sentence & word numbers to ints.
        sentnum = int(sentnum)
        wordnum = int(wordnum)

        # Parse the predicate location.

        predloc, predid = rel[0].split("-", 1)
        predicate = NombankTreePointer.parse(predloc)

        # Parse the arguments.
        arguments = []
        for arg in args:
            argloc, argid = arg.split("-", 1)
            arguments.append((NombankTreePointer.parse(argloc), argid))

        # Put it all together.
        return NombankInstance(
            fileid,
            sentnum,
            wordnum,
            baseform,
            sensenumber,
            predicate,
            predid,
            arguments,
            parse_corpus,
        )


class NombankPointer:
    """
    A pointer used by nombank to identify one or more constituents in
    a parse tree.  ``NombankPointer`` is an abstract base class with
    three concrete subclasses:

    - ``NombankTreePointer`` is used to point to single constituents.
    - ``NombankSplitTreePointer`` is used to point to 'split'
      constituents, which consist of a sequence of two or more
      ``NombankTreePointer`` pointers.
    - ``NombankChainTreePointer`` is used to point to entire trace
      chains in a tree.  It consists of a sequence of pieces, which
      can be ``NombankTreePointer`` or ``NombankSplitTreePointer`` pointers.
    """

    def __init__(self):
        if self.__class__ == NombankPointer:
            raise NotImplementedError()


class NombankChainTreePointer(NombankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements may
           be either ``NombankSplitTreePointer`` or
           ``NombankTreePointer`` pointers."""

    def __str__(self):
        return "*".join("%s" % p for p in self.pieces)

    def __repr__(self):
        return "<NombankChainTreePointer: %s>" % self

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return Tree("*CHAIN*", [p.select(tree) for p in self.pieces])


class NombankSplitTreePointer(NombankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements are
           all ``NombankTreePointer`` pointers."""

    def __str__(self):
        return ",".join("%s" % p for p in self.pieces)

    def __repr__(self):
        return "<NombankSplitTreePointer: %s>" % self

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return Tree("*SPLIT*", [p.select(tree) for p in self.pieces])


@total_ordering
class NombankTreePointer(NombankPointer):
    """
    wordnum:height*wordnum:height*...
    wordnum:height,

    """

    def __init__(self, wordnum, height):
        self.wordnum = wordnum
        self.height = height

    @staticmethod
    def parse(s):
        # Deal with chains (xx*yy*zz)
        pieces = s.split("*")
        if len(pieces) > 1:
            return NombankChainTreePointer(
                [NombankTreePointer.parse(elt) for elt in pieces]
            )

        # Deal with split args (xx,yy,zz)
        pieces = s.split(",")
        if len(pieces) > 1:
            return NombankSplitTreePointer(
                [NombankTreePointer.parse(elt) for elt in pieces]
            )

        # Deal with normal pointers.
        pieces = s.split(":")
        if len(pieces) != 2:
            raise ValueError("bad nombank pointer %r" % s)
        return NombankTreePointer(int(pieces[0]), int(pieces[1]))

    def __str__(self):
        return f"{self.wordnum}:{self.height}"

    def __repr__(self):
        return "NombankTreePointer(%d, %d)" % (self.wordnum, self.height)

    def __eq__(self, other):
        while isinstance(other, (NombankChainTreePointer, NombankSplitTreePointer)):
            other = other.pieces[0]

        if not isinstance(other, NombankTreePointer):
            return self is other

        return self.wordnum == other.wordnum and self.height == other.height

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        while isinstance(other, (NombankChainTreePointer, NombankSplitTreePointer)):
            other = other.pieces[0]

        if not isinstance(other, NombankTreePointer):
            return id(self) < id(other)

        return (self.wordnum, -self.height) < (other.wordnum, -other.height)

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return tree[self.treepos(tree)]

    def treepos(self, tree):
        """
        Convert this pointer to a standard 'tree position' pointer,
        given that it points to the given tree.
        """
        if tree is None:
            raise ValueError("Parse tree not available")
        stack = [tree]
        treepos = []

        wordnum = 0
        while True:
            # tree node:
            if isinstance(stack[-1], Tree):
                # Select the next child.
                if len(treepos) < len(stack):
                    treepos.append(0)
                else:
                    treepos[-1] += 1
                # Update the stack.
                if treepos[-1] < len(stack[-1]):
                    stack.append(stack[-1][treepos[-1]])
                else:
                    # End of node's child list: pop up a level.
                    stack.pop()
                    treepos.pop()
            # word node:
            else:
                if wordnum == self.wordnum:
                    return tuple(treepos[: len(treepos) - self.height - 1])
                else:
                    wordnum += 1
                    stack.pop()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_oauth.py ===
import datetime
import hashlib
import logging
import os
import time
import urllib.parse
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from . import constants
from .hf_api import whoami
from .utils import experimental, get_token


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import fastapi


@dataclass
class OAuthOrgInfo:
    """
    Information about an organization linked to a user logged in with OAuth.

    Attributes:
        sub (`str`):
            Unique identifier for the org. OpenID Connect field.
        name (`str`):
            The org's full name. OpenID Connect field.
        preferred_username (`str`):
            The org's username. OpenID Connect field.
        picture (`str`):
            The org's profile picture URL. OpenID Connect field.
        is_enterprise (`bool`):
            Whether the org is an enterprise org. Hugging Face field.
        can_pay (`Optional[bool]`, *optional*):
            Whether the org has a payment method set up. Hugging Face field.
        role_in_org (`Optional[str]`, *optional*):
            The user's role in the org. Hugging Face field.
        pending_sso (`Optional[bool]`, *optional*):
            Indicates if the user granted the OAuth app access to the org but didn't complete SSO. Hugging Face field.
        missing_mfa (`Optional[bool]`, *optional*):
            Indicates if the user granted the OAuth app access to the org but didn't complete MFA. Hugging Face field.
    """

    sub: str
    name: str
    preferred_username: str
    picture: str
    is_enterprise: bool
    can_pay: Optional[bool] = None
    role_in_org: Optional[str] = None
    pending_sso: Optional[bool] = None
    missing_mfa: Optional[bool] = None


@dataclass
class OAuthUserInfo:
    """
    Information about a user logged in with OAuth.

    Attributes:
        sub (`str`):
            Unique identifier for the user, even in case of rename. OpenID Connect field.
        name (`str`):
            The user's full name. OpenID Connect field.
        preferred_username (`str`):
            The user's username. OpenID Connect field.
        email_verified (`Optional[bool]`, *optional*):
            Indicates if the user's email is verified. OpenID Connect field.
        email (`Optional[str]`, *optional*):
            The user's email address. OpenID Connect field.
        picture (`str`):
            The user's profile picture URL. OpenID Connect field.
        profile (`str`):
            The user's profile URL. OpenID Connect field.
        website (`Optional[str]`, *optional*):
            The user's website URL. OpenID Connect field.
        is_pro (`bool`):
            Whether the user is a pro user. Hugging Face field.
        can_pay (`Optional[bool]`, *optional*):
            Whether the user has a payment method set up. Hugging Face field.
        orgs (`Optional[List[OrgInfo]]`, *optional*):
            List of organizations the user is part of. Hugging Face field.
    """

    sub: str
    name: str
    preferred_username: str
    email_verified: Optional[bool]
    email: Optional[str]
    picture: str
    profile: str
    website: Optional[str]
    is_pro: bool
    can_pay: Optional[bool]
    orgs: Optional[List[OAuthOrgInfo]]


@dataclass
class OAuthInfo:
    """
    Information about the OAuth login.

    Attributes:
        access_token (`str`):
            The access token.
        access_token_expires_at (`datetime.datetime`):
            The expiration date of the access token.
        user_info ([`OAuthUserInfo`]):
            The user information.
        state (`str`, *optional*):
            State passed to the OAuth provider in the original request to the OAuth provider.
        scope (`str`):
            Granted scope.
    """

    access_token: str
    access_token_expires_at: datetime.datetime
    user_info: OAuthUserInfo
    state: Optional[str]
    scope: str


@experimental
def attach_huggingface_oauth(app: "fastapi.FastAPI", route_prefix: str = "/"):
    """
    Add OAuth endpoints to a FastAPI app to enable OAuth login with Hugging Face.

    How to use:
    - Call this method on your FastAPI app to add the OAuth endpoints.
    - Inside your route handlers, call `parse_huggingface_oauth(request)` to retrieve the OAuth info.
    - If user is logged in, an [`OAuthInfo`] object is returned with the user's info. If not, `None` is returned.
    - In your app, make sure to add links to `/oauth/huggingface/login` and `/oauth/huggingface/logout` for the user to log in and out.

    Example:
    ```py
    from huggingface_hub import attach_huggingface_oauth, parse_huggingface_oauth

    # Create a FastAPI app
    app = FastAPI()

    # Add OAuth endpoints to the FastAPI app
    attach_huggingface_oauth(app)

    # Add a route that greets the user if they are logged in
    @app.get("/")
    def greet_json(request: Request):
        # Retrieve the OAuth info from the request
        oauth_info = parse_huggingface_oauth(request)  # e.g. OAuthInfo dataclass
        if oauth_info is None:
            return {"msg": "Not logged in!"}
        return {"msg": f"Hello, {oauth_info.user_info.preferred_username}!"}
    ```
    """
    # TODO: handle generic case (handling OAuth in a non-Space environment with custom dev values) (low priority)

    # Add SessionMiddleware to the FastAPI app to store the OAuth info in the session.
    # Session Middleware requires a secret key to sign the cookies. Let's use a hash
    # of the OAuth secret key to make it unique to the Space + updated in case OAuth
    # config gets updated. When ran locally, we use an empty string as a secret key.
    try:
        from starlette.middleware.sessions import SessionMiddleware
    except ImportError as e:
        raise ImportError(
            "Cannot initialize OAuth to due a missing library. Please run `pip install huggingface_hub[oauth]` or add "
            "`huggingface_hub[oauth]` to your requirements.txt file in order to install the required dependencies."
        ) from e
    session_secret = (constants.OAUTH_CLIENT_SECRET or "") + "-v1"
    app.add_middleware(
        SessionMiddleware,  # type: ignore[arg-type]
        secret_key=hashlib.sha256(session_secret.encode()).hexdigest(),
        same_site="none",
        https_only=True,
    )  # type: ignore

    # Add OAuth endpoints to the FastAPI app:
    #   - {route_prefix}/oauth/huggingface/login
    #   - {route_prefix}/oauth/huggingface/callback
    #   - {route_prefix}/oauth/huggingface/logout
    # If the app is running in a Space, OAuth is enabled normally.
    # Otherwise, we mock the endpoints to make the user log in with a fake user profile - without any calls to hf.co.
    route_prefix = route_prefix.strip("/")
    if os.getenv("SPACE_ID") is not None:
        logger.info("OAuth is enabled in the Space. Adding OAuth routes.")
        _add_oauth_routes(app, route_prefix=route_prefix)
    else:
        logger.info("App is not running in a Space. Adding mocked OAuth routes.")
        _add_mocked_oauth_routes(app, route_prefix=route_prefix)


def parse_huggingface_oauth(request: "fastapi.Request") -> Optional[OAuthInfo]:
    """
    Returns the information from a logged in user as a [`OAuthInfo`] object.

    For flexibility and future-proofing, this method is very lax in its parsing and does not raise errors.
    Missing fields are set to `None` without a warning.

    Return `None`, if the user is not logged in (no info in session cookie).

    See [`attach_huggingface_oauth`] for an example on how to use this method.
    """
    if "oauth_info" not in request.session:
        logger.debug("No OAuth info in session.")
        return None

    logger.debug("Parsing OAuth info from session.")
    oauth_data = request.session["oauth_info"]
    user_data = oauth_data.get("userinfo", {})
    orgs_data = user_data.get("orgs", [])

    orgs = (
        [
            OAuthOrgInfo(
                sub=org.get("sub"),
                name=org.get("name"),
                preferred_username=org.get("preferred_username"),
                picture=org.get("picture"),
                is_enterprise=org.get("isEnterprise"),
                can_pay=org.get("canPay"),
                role_in_org=org.get("roleInOrg"),
                pending_sso=org.get("pendingSSO"),
                missing_mfa=org.get("missingMFA"),
            )
            for org in orgs_data
        ]
        if orgs_data
        else None
    )

    user_info = OAuthUserInfo(
        sub=user_data.get("sub"),
        name=user_data.get("name"),
        preferred_username=user_data.get("preferred_username"),
        email_verified=user_data.get("email_verified"),
        email=user_data.get("email"),
        picture=user_data.get("picture"),
        profile=user_data.get("profile"),
        website=user_data.get("website"),
        is_pro=user_data.get("isPro"),
        can_pay=user_data.get("canPay"),
        orgs=orgs,
    )

    return OAuthInfo(
        access_token=oauth_data.get("access_token"),
        access_token_expires_at=datetime.datetime.fromtimestamp(oauth_data.get("expires_at")),
        user_info=user_info,
        state=oauth_data.get("state"),
        scope=oauth_data.get("scope"),
    )


def _add_oauth_routes(app: "fastapi.FastAPI", route_prefix: str) -> None:
    """Add OAuth routes to the FastAPI app (login, callback handler and logout)."""
    try:
        import fastapi
        from authlib.integrations.base_client.errors import MismatchingStateError
        from authlib.integrations.starlette_client import OAuth
        from fastapi.responses import RedirectResponse
    except ImportError as e:
        raise ImportError(
            "Cannot initialize OAuth to due a missing library. Please run `pip install huggingface_hub[oauth]` or add "
            "`huggingface_hub[oauth]` to your requirements.txt file."
        ) from e

    # Check environment variables
    msg = (
        "OAuth is required but '{}' environment variable is not set. Make sure you've enabled OAuth in your Space by"
        " setting `hf_oauth: true` in the Space metadata."
    )
    if constants.OAUTH_CLIENT_ID is None:
        raise ValueError(msg.format("OAUTH_CLIENT_ID"))
    if constants.OAUTH_CLIENT_SECRET is None:
        raise ValueError(msg.format("OAUTH_CLIENT_SECRET"))
    if constants.OAUTH_SCOPES is None:
        raise ValueError(msg.format("OAUTH_SCOPES"))
    if constants.OPENID_PROVIDER_URL is None:
        raise ValueError(msg.format("OPENID_PROVIDER_URL"))

    # Register OAuth server
    oauth = OAuth()
    oauth.register(
        name="huggingface",
        client_id=constants.OAUTH_CLIENT_ID,
        client_secret=constants.OAUTH_CLIENT_SECRET,
        client_kwargs={"scope": constants.OAUTH_SCOPES},
        server_metadata_url=constants.OPENID_PROVIDER_URL + "/.well-known/openid-configuration",
    )

    login_uri, callback_uri, logout_uri = _get_oauth_uris(route_prefix)

    # Register OAuth endpoints
    @app.get(login_uri)
    async def oauth_login(request: fastapi.Request) -> RedirectResponse:
        """Endpoint that redirects to HF OAuth page."""
        redirect_uri = _generate_redirect_uri(request)
        return await oauth.huggingface.authorize_redirect(request, redirect_uri)  # type: ignore

    @app.get(callback_uri)
    async def oauth_redirect_callback(request: fastapi.Request) -> RedirectResponse:
        """Endpoint that handles the OAuth callback."""
        try:
            oauth_info = await oauth.huggingface.authorize_access_token(request)  # type: ignore
        except MismatchingStateError:
            # Parse query params
            nb_redirects = int(request.query_params.get("_nb_redirects", 0))
            target_url = request.query_params.get("_target_url")

            # Build redirect URI with the same query params as before and bump nb_redirects count
            query_params: Dict[str, Union[int, str]] = {"_nb_redirects": nb_redirects + 1}
            if target_url:
                query_params["_target_url"] = target_url

            redirect_uri = f"{login_uri}?{urllib.parse.urlencode(query_params)}"

            # If the user is redirected more than 3 times, it is very likely that the cookie is not working properly.
            # (e.g. browser is blocking third-party cookies in iframe). In this case, redirect the user in the
            # non-iframe view.
            if nb_redirects > constants.OAUTH_MAX_REDIRECTS:
                host = os.environ.get("SPACE_HOST")
                if host is None:  # cannot happen in a Space
                    raise RuntimeError(
                        "App is not running in a Space (SPACE_HOST environment variable is not set). Cannot redirect to non-iframe view."
                    ) from None
                host_url = "https://" + host.rstrip("/")
                return RedirectResponse(host_url + redirect_uri)

            # Redirect the user to the login page again
            return RedirectResponse(redirect_uri)

        # OAuth login worked => store the user info in the session and redirect
        logger.debug("Successfully logged in with OAuth. Storing user info in session.")
        request.session["oauth_info"] = oauth_info
        return RedirectResponse(_get_redirect_target(request))

    @app.get(logout_uri)
    async def oauth_logout(request: fastapi.Request) -> RedirectResponse:
        """Endpoint that logs out the user (e.g. delete info from cookie session)."""
        logger.debug("Logged out with OAuth. Removing user info from session.")
        request.session.pop("oauth_info", None)
        return RedirectResponse(_get_redirect_target(request))


def _add_mocked_oauth_routes(app: "fastapi.FastAPI", route_prefix: str = "/") -> None:
    """Add fake oauth routes if app is run locally and OAuth is enabled.

    Using OAuth will have the same behavior as in a Space but instead of authenticating with HF, a mocked user profile
    is added to the session.
    """
    try:
        import fastapi
        from fastapi.responses import RedirectResponse
        from starlette.datastructures import URL
    except ImportError as e:
        raise ImportError(
            "Cannot initialize OAuth to due a missing library. Please run `pip install huggingface_hub[oauth]` or add "
            "`huggingface_hub[oauth]` to your requirements.txt file."
        ) from e

    warnings.warn(
        "OAuth is not supported outside of a Space environment. To help you debug your app locally, the oauth endpoints"
        " are mocked to return your profile and token. To make it work, your machine must be logged in to Huggingface."
    )
    mocked_oauth_info = _get_mocked_oauth_info()

    login_uri, callback_uri, logout_uri = _get_oauth_uris(route_prefix)

    # Define OAuth routes
    @app.get(login_uri)
    async def oauth_login(request: fastapi.Request) -> RedirectResponse:
        """Fake endpoint that redirects to HF OAuth page."""
        # Define target (where to redirect after login)
        redirect_uri = _generate_redirect_uri(request)
        return RedirectResponse(callback_uri + "?" + urllib.parse.urlencode({"_target_url": redirect_uri}))

    @app.get(callback_uri)
    async def oauth_redirect_callback(request: fastapi.Request) -> RedirectResponse:
        """Endpoint that handles the OAuth callback."""
        request.session["oauth_info"] = mocked_oauth_info
        return RedirectResponse(_get_redirect_target(request))

    @app.get(logout_uri)
    async def oauth_logout(request: fastapi.Request) -> RedirectResponse:
        """Endpoint that logs out the user (e.g. delete cookie session)."""
        request.session.pop("oauth_info", None)
        logout_url = URL("/").include_query_params(**request.query_params)
        return RedirectResponse(url=logout_url, status_code=302)  # see https://github.com/gradio-app/gradio/pull/9659


def _generate_redirect_uri(request: "fastapi.Request") -> str:
    if "_target_url" in request.query_params:
        # if `_target_url` already in query params => respect it
        target = request.query_params["_target_url"]
    else:
        # otherwise => keep query params
        target = "/?" + urllib.parse.urlencode(request.query_params)

    redirect_uri = request.url_for("oauth_redirect_callback").include_query_params(_target_url=target)
    redirect_uri_as_str = str(redirect_uri)
    if redirect_uri.netloc.endswith(".hf.space"):
        # In Space, FastAPI redirect as http but we want https
        redirect_uri_as_str = redirect_uri_as_str.replace("http://", "https://")
    return redirect_uri_as_str


def _get_redirect_target(request: "fastapi.Request", default_target: str = "/") -> str:
    return request.query_params.get("_target_url", default_target)


def _get_mocked_oauth_info() -> Dict:
    token = get_token()
    if token is None:
        raise ValueError(
            "Your machine must be logged in to HF to debug an OAuth app locally. Please"
            " run `huggingface-cli login` or set `HF_TOKEN` as environment variable "
            "with one of your access token. You can generate a new token in your "
            "settings page (https://huggingface.co/settings/tokens)."
        )

    user = whoami()
    if user["type"] != "user":
        raise ValueError(
            "Your machine is not logged in with a personal account. Please use a "
            "personal access token. You can generate a new token in your settings page"
            " (https://huggingface.co/settings/tokens)."
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 8 * 60 * 60,  # 8 hours
        "id_token": "FOOBAR",
        "scope": "openid profile",
        "refresh_token": "hf_oauth__refresh_token",
        "expires_at": int(time.time()) + 8 * 60 * 60,  # 8 hours
        "userinfo": {
            "sub": "0123456789",
            "name": user["fullname"],
            "preferred_username": user["name"],
            "profile": f"https://huggingface.co/{user['name']}",
            "picture": user["avatarUrl"],
            "website": "",
            "aud": "00000000-0000-0000-0000-000000000000",
            "auth_time": 1691672844,
            "nonce": "aaaaaaaaaaaaaaaaaaa",
            "iat": 1691672844,
            "exp": 1691676444,
            "iss": "https://huggingface.co",
        },
    }


def _get_oauth_uris(route_prefix: str = "/") -> Tuple[str, str, str]:
    route_prefix = route_prefix.strip("/")
    if route_prefix:
        route_prefix = f"/{route_prefix}"
    return (
        f"{route_prefix}/oauth/huggingface/login",
        f"{route_prefix}/oauth/huggingface/callback",
        f"{route_prefix}/oauth/huggingface/logout",
    )

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\decorators.py ===
import contextlib
import functools
import inspect
import os
from platform import uname
from pathlib import Path
import shutil
import string
import sys
import warnings

from packaging.version import parse as parse_version

import matplotlib.style
import matplotlib.units
import matplotlib.testing
from matplotlib import _pylab_helpers, cbook, ft2font, pyplot as plt, ticker
from .compare import comparable_formats, compare_images, make_test_filename
from .exceptions import ImageComparisonFailure


@contextlib.contextmanager
def _cleanup_cm():
    orig_units_registry = matplotlib.units.registry.copy()
    try:
        with warnings.catch_warnings(), matplotlib.rc_context():
            yield
    finally:
        matplotlib.units.registry.clear()
        matplotlib.units.registry.update(orig_units_registry)
        plt.close("all")


def _check_freetype_version(ver):
    if ver is None:
        return True

    if isinstance(ver, str):
        ver = (ver, ver)
    ver = [parse_version(x) for x in ver]
    found = parse_version(ft2font.__freetype_version__)

    return ver[0] <= found <= ver[1]


def _checked_on_freetype_version(required_freetype_version):
    import pytest
    return pytest.mark.xfail(
        not _check_freetype_version(required_freetype_version),
        reason=f"Mismatched version of freetype. "
               f"Test requires '{required_freetype_version}', "
               f"you have '{ft2font.__freetype_version__}'",
        raises=ImageComparisonFailure, strict=False)


def remove_ticks_and_titles(figure):
    figure.suptitle("")
    null_formatter = ticker.NullFormatter()
    def remove_ticks(ax):
        """Remove ticks in *ax* and all its child Axes."""
        ax.set_title("")
        ax.xaxis.set_major_formatter(null_formatter)
        ax.xaxis.set_minor_formatter(null_formatter)
        ax.yaxis.set_major_formatter(null_formatter)
        ax.yaxis.set_minor_formatter(null_formatter)
        try:
            ax.zaxis.set_major_formatter(null_formatter)
            ax.zaxis.set_minor_formatter(null_formatter)
        except AttributeError:
            pass
        for child in ax.child_axes:
            remove_ticks(child)
    for ax in figure.get_axes():
        remove_ticks(ax)


@contextlib.contextmanager
def _collect_new_figures():
    """
    After::

        with _collect_new_figures() as figs:
            some_code()

    the list *figs* contains the figures that have been created during the
    execution of ``some_code``, sorted by figure number.
    """
    managers = _pylab_helpers.Gcf.figs
    preexisting = [manager for manager in managers.values()]
    new_figs = []
    try:
        yield new_figs
    finally:
        new_managers = sorted([manager for manager in managers.values()
                               if manager not in preexisting],
                              key=lambda manager: manager.num)
        new_figs[:] = [manager.canvas.figure for manager in new_managers]


def _raise_on_image_difference(expected, actual, tol):
    __tracebackhide__ = True

    err = compare_images(expected, actual, tol, in_decorator=True)
    if err:
        for key in ["actual", "expected", "diff"]:
            err[key] = os.path.relpath(err[key])
        raise ImageComparisonFailure(
            ('images not close (RMS %(rms).3f):'
                '\n\t%(actual)s\n\t%(expected)s\n\t%(diff)s') % err)


class _ImageComparisonBase:
    """
    Image comparison base class

    This class provides *just* the comparison-related functionality and avoids
    any code that would be specific to any testing framework.
    """

    def __init__(self, func, tol, remove_text, savefig_kwargs):
        self.func = func
        self.baseline_dir, self.result_dir = _image_directories(func)
        self.tol = tol
        self.remove_text = remove_text
        self.savefig_kwargs = savefig_kwargs

    def copy_baseline(self, baseline, extension):
        baseline_path = self.baseline_dir / baseline
        orig_expected_path = baseline_path.with_suffix(f'.{extension}')
        if extension == 'eps' and not orig_expected_path.exists():
            orig_expected_path = orig_expected_path.with_suffix('.pdf')
        expected_fname = make_test_filename(
            self.result_dir / orig_expected_path.name, 'expected')
        try:
            # os.symlink errors if the target already exists.
            with contextlib.suppress(OSError):
                os.remove(expected_fname)
            try:
                if 'microsoft' in uname().release.lower():
                    raise OSError  # On WSL, symlink breaks silently
                os.symlink(orig_expected_path, expected_fname)
            except OSError:  # On Windows, symlink *may* be unavailable.
                shutil.copyfile(orig_expected_path, expected_fname)
        except OSError as err:
            raise ImageComparisonFailure(
                f"Missing baseline image {expected_fname} because the "
                f"following file cannot be accessed: "
                f"{orig_expected_path}") from err
        return expected_fname

    def compare(self, fig, baseline, extension, *, _lock=False):
        __tracebackhide__ = True

        if self.remove_text:
            remove_ticks_and_titles(fig)

        actual_path = (self.result_dir / baseline).with_suffix(f'.{extension}')
        kwargs = self.savefig_kwargs.copy()
        if extension == 'pdf':
            kwargs.setdefault('metadata',
                              {'Creator': None, 'Producer': None,
                               'CreationDate': None})

        lock = (cbook._lock_path(actual_path)
                if _lock else contextlib.nullcontext())
        with lock:
            try:
                fig.savefig(actual_path, **kwargs)
            finally:
                # Matplotlib has an autouse fixture to close figures, but this
                # makes things more convenient for third-party users.
                plt.close(fig)
            expected_path = self.copy_baseline(baseline, extension)
            _raise_on_image_difference(expected_path, actual_path, self.tol)


def _pytest_image_comparison(baseline_images, extensions, tol,
                             freetype_version, remove_text, savefig_kwargs,
                             style):
    """
    Decorate function with image comparison for pytest.

    This function creates a decorator that wraps a figure-generating function
    with image comparison code.
    """
    import pytest

    KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY

    def decorator(func):
        old_sig = inspect.signature(func)

        @functools.wraps(func)
        @pytest.mark.parametrize('extension', extensions)
        @matplotlib.style.context(style)
        @_checked_on_freetype_version(freetype_version)
        @functools.wraps(func)
        def wrapper(*args, extension, request, **kwargs):
            __tracebackhide__ = True
            if 'extension' in old_sig.parameters:
                kwargs['extension'] = extension
            if 'request' in old_sig.parameters:
                kwargs['request'] = request

            if extension not in comparable_formats():
                reason = {
                    'pdf': 'because Ghostscript is not installed',
                    'eps': 'because Ghostscript is not installed',
                    'svg': 'because Inkscape is not installed',
                }.get(extension, 'on this system')
                pytest.skip(f"Cannot compare {extension} files {reason}")

            img = _ImageComparisonBase(func, tol=tol, remove_text=remove_text,
                                       savefig_kwargs=savefig_kwargs)
            matplotlib.testing.set_font_settings_for_testing()

            with _collect_new_figures() as figs:
                func(*args, **kwargs)

            # If the test is parametrized in any way other than applied via
            # this decorator, then we need to use a lock to prevent two
            # processes from touching the same output file.
            needs_lock = any(
                marker.args[0] != 'extension'
                for marker in request.node.iter_markers('parametrize'))

            if baseline_images is not None:
                our_baseline_images = baseline_images
            else:
                # Allow baseline image list to be produced on the fly based on
                # current parametrization.
                our_baseline_images = request.getfixturevalue(
                    'baseline_images')

            assert len(figs) == len(our_baseline_images), (
                f"Test generated {len(figs)} images but there are "
                f"{len(our_baseline_images)} baseline images")
            for fig, baseline in zip(figs, our_baseline_images):
                img.compare(fig, baseline, extension, _lock=needs_lock)

        parameters = list(old_sig.parameters.values())
        if 'extension' not in old_sig.parameters:
            parameters += [inspect.Parameter('extension', KEYWORD_ONLY)]
        if 'request' not in old_sig.parameters:
            parameters += [inspect.Parameter("request", KEYWORD_ONLY)]
        new_sig = old_sig.replace(parameters=parameters)
        wrapper.__signature__ = new_sig

        # Reach a bit into pytest internals to hoist the marks from our wrapped
        # function.
        new_marks = getattr(func, 'pytestmark', []) + wrapper.pytestmark
        wrapper.pytestmark = new_marks

        return wrapper

    return decorator


def image_comparison(baseline_images, extensions=None, tol=0,
                     freetype_version=None, remove_text=False,
                     savefig_kwarg=None,
                     # Default of mpl_test_settings fixture and cleanup too.
                     style=("classic", "_classic_test_patch")):
    """
    Compare images generated by the test with those specified in
    *baseline_images*, which must correspond, else an `.ImageComparisonFailure`
    exception will be raised.

    Parameters
    ----------
    baseline_images : list or None
        A list of strings specifying the names of the images generated by
        calls to `.Figure.savefig`.

        If *None*, the test function must use the ``baseline_images`` fixture,
        either as a parameter or with `pytest.mark.usefixtures`. This value is
        only allowed when using pytest.

    extensions : None or list of str
        The list of extensions to test, e.g. ``['png', 'pdf']``.

        If *None*, defaults to all supported extensions: png, pdf, and svg.

        When testing a single extension, it can be directly included in the
        names passed to *baseline_images*.  In that case, *extensions* must not
        be set.

        In order to keep the size of the test suite from ballooning, we only
        include the ``svg`` or ``pdf`` outputs if the test is explicitly
        exercising a feature dependent on that backend (see also the
        `check_figures_equal` decorator for that purpose).

    tol : float, default: 0
        The RMS threshold above which the test is considered failed.

        Due to expected small differences in floating-point calculations, on
        32-bit systems an additional 0.06 is added to this threshold.

    freetype_version : str or tuple
        The expected freetype version or range of versions for this test to
        pass.

    remove_text : bool
        Remove the title and tick text from the figure before comparison.  This
        is useful to make the baseline images independent of variations in text
        rendering between different versions of FreeType.

        This does not remove other, more deliberate, text, such as legends and
        annotations.

    savefig_kwarg : dict
        Optional arguments that are passed to the savefig method.

    style : str, dict, or list
        The optional style(s) to apply to the image test. The test itself
        can also apply additional styles if desired. Defaults to ``["classic",
        "_classic_test_patch"]``.
    """

    if baseline_images is not None:
        # List of non-empty filename extensions.
        baseline_exts = [*filter(None, {Path(baseline).suffix[1:]
                                        for baseline in baseline_images})]
        if baseline_exts:
            if extensions is not None:
                raise ValueError(
                    "When including extensions directly in 'baseline_images', "
                    "'extensions' cannot be set as well")
            if len(baseline_exts) > 1:
                raise ValueError(
                    "When including extensions directly in 'baseline_images', "
                    "all baselines must share the same suffix")
            extensions = baseline_exts
            baseline_images = [  # Chop suffix out from baseline_images.
                Path(baseline).stem for baseline in baseline_images]
    if extensions is None:
        # Default extensions to test, if not set via baseline_images.
        extensions = ['png', 'pdf', 'svg']
    if savefig_kwarg is None:
        savefig_kwarg = dict()  # default no kwargs to savefig
    if sys.maxsize <= 2**32:
        tol += 0.06
    return _pytest_image_comparison(
        baseline_images=baseline_images, extensions=extensions, tol=tol,
        freetype_version=freetype_version, remove_text=remove_text,
        savefig_kwargs=savefig_kwarg, style=style)


def check_figures_equal(*, extensions=("png", "pdf", "svg"), tol=0):
    """
    Decorator for test cases that generate and compare two figures.

    The decorated function must take two keyword arguments, *fig_test*
    and *fig_ref*, and draw the test and reference images on them.
    After the function returns, the figures are saved and compared.

    This decorator should be preferred over `image_comparison` when possible in
    order to keep the size of the test suite from ballooning.

    Parameters
    ----------
    extensions : list, default: ["png", "pdf", "svg"]
        The extensions to test.
    tol : float
        The RMS threshold above which the test is considered failed.

    Raises
    ------
    RuntimeError
        If any new figures are created (and not subsequently closed) inside
        the test function.

    Examples
    --------
    Check that calling `.Axes.plot` with a single argument plots it against
    ``[0, 1, 2, ...]``::

        @check_figures_equal()
        def test_plot(fig_test, fig_ref):
            fig_test.subplots().plot([1, 3, 5])
            fig_ref.subplots().plot([0, 1, 2], [1, 3, 5])

    """
    ALLOWED_CHARS = set(string.digits + string.ascii_letters + '_-[]()')
    KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY

    def decorator(func):
        import pytest

        _, result_dir = _image_directories(func)
        old_sig = inspect.signature(func)

        if not {"fig_test", "fig_ref"}.issubset(old_sig.parameters):
            raise ValueError("The decorated function must have at least the "
                             "parameters 'fig_test' and 'fig_ref', but your "
                             f"function has the signature {old_sig}")

        @pytest.mark.parametrize("ext", extensions)
        def wrapper(*args, ext, request, **kwargs):
            if 'ext' in old_sig.parameters:
                kwargs['ext'] = ext
            if 'request' in old_sig.parameters:
                kwargs['request'] = request

            file_name = "".join(c for c in request.node.name
                                if c in ALLOWED_CHARS)
            try:
                fig_test = plt.figure("test")
                fig_ref = plt.figure("reference")
                with _collect_new_figures() as figs:
                    func(*args, fig_test=fig_test, fig_ref=fig_ref, **kwargs)
                if figs:
                    raise RuntimeError('Number of open figures changed during '
                                       'test. Make sure you are plotting to '
                                       'fig_test or fig_ref, or if this is '
                                       'deliberate explicitly close the '
                                       'new figure(s) inside the test.')
                test_image_path = result_dir / (file_name + "." + ext)
                ref_image_path = result_dir / (file_name + "-expected." + ext)
                fig_test.savefig(test_image_path)
                fig_ref.savefig(ref_image_path)
                _raise_on_image_difference(
                    ref_image_path, test_image_path, tol=tol
                )
            finally:
                plt.close(fig_test)
                plt.close(fig_ref)

        parameters = [
            param
            for param in old_sig.parameters.values()
            if param.name not in {"fig_test", "fig_ref"}
        ]
        if 'ext' not in old_sig.parameters:
            parameters += [inspect.Parameter("ext", KEYWORD_ONLY)]
        if 'request' not in old_sig.parameters:
            parameters += [inspect.Parameter("request", KEYWORD_ONLY)]
        new_sig = old_sig.replace(parameters=parameters)
        wrapper.__signature__ = new_sig

        # reach a bit into pytest internals to hoist the marks from
        # our wrapped function
        new_marks = getattr(func, "pytestmark", []) + wrapper.pytestmark
        wrapper.pytestmark = new_marks

        return wrapper

    return decorator


def _image_directories(func):
    """
    Compute the baseline and result image directories for testing *func*.

    For test module ``foo.bar.test_baz``, the baseline directory is at
    ``foo/bar/baseline_images/test_baz`` and the result directory at
    ``$(pwd)/result_images/test_baz``.  The result directory is created if it
    doesn't exist.
    """
    module_path = Path(inspect.getfile(func))
    baseline_dir = module_path.parent / "baseline_images" / module_path.stem
    result_dir = Path().resolve() / "result_images" / module_path.stem
    result_dir.mkdir(parents=True, exist_ok=True)
    return baseline_dir, result_dir

# === NexusCore/openenv\Lib\site-packages\win32\Demos\win32gui_menu.py ===
# Demonstrates some advanced menu concepts using win32gui.
# This creates a taskbar icon which has some fancy menus (but note that
# selecting the menu items does nothing useful - see win32gui_taskbar.py
# for examples of this.

# NOTE: This is a work in progress.  Todo:
# * The "Checked" menu items don't work correctly - I'm not sure why.
# * No support for GetMenuItemInfo.

# Based on Andy McKay's demo code.

import os
import struct
import sys

import win32con
from win32api import GetSystemDirectory, GetSystemMetrics
from win32gui import (
    LOWORD,
    NIF_ICON,
    NIF_MESSAGE,
    NIF_TIP,
    NIM_ADD,
    NIM_DELETE,
    WNDCLASS,
    CheckMenuItem,
    CheckMenuRadioItem,
    CreateCompatibleBitmap,
    CreateCompatibleDC,
    CreateFontIndirect,
    CreatePopupMenu,
    CreateWindow,
    DeleteDC,
    DestroyIcon,
    DestroyWindow,
    DrawIconEx,
    ExtTextOut,
    FillRect,
    GetCursorPos,
    GetDC,
    GetMenuDefaultItem,
    GetMenuState,
    GetModuleHandle,
    GetSysColor,
    GetSysColorBrush,
    GetTextExtentPoint32,
    InsertMenu,
    InsertMenuItem,
    LoadIcon,
    LoadImage,
    PostMessage,
    PostQuitMessage,
    PumpMessages,
    PyGetMemory,
    PyMakeBuffer,
    PySetMemory,
    RegisterClass,
    ReleaseDC,
    SelectObject,
    SetBkColor,
    SetBkMode,
    SetForegroundWindow,
    SetMenuDefaultItem,
    SetTextColor,
    Shell_NotifyIcon,
    SystemParametersInfo,
    TrackPopupMenu,
    UpdateWindow,
)
from win32gui_struct import (
    EmptyMENUITEMINFO,
    PackMENUITEMINFO,
    UnpackMENUITEMINFO,
)

this_dir = os.path.split(sys.argv[0])[0]


class MainWindow:
    def __init__(self):
        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_USER + 20: self.OnTaskbarNotify,
            # owner-draw related handlers.
            win32con.WM_MEASUREITEM: self.OnMeasureItem,
            win32con.WM_DRAWITEM: self.OnDrawItem,
        }
        # Register the Window class.
        wc = WNDCLASS()
        hinst = wc.hInstance = GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbarDemo"
        wc.lpfnWndProc = message_map  # could also specify a wndproc.
        classAtom = RegisterClass(wc)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = CreateWindow(
            classAtom,
            "Taskbar Demo",
            style,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            hinst,
            None,
        )
        UpdateWindow(self.hwnd)
        iconPathName = os.path.abspath(os.path.join(sys.prefix, "pyc.ico"))
        if not os.path.isfile(iconPathName):
            # Look in the source tree.
            iconPathName = os.path.abspath(
                os.path.join(os.path.split(sys.executable)[0], "..\\PC\\pyc.ico")
            )
        if os.path.isfile(iconPathName):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = LoadImage(
                hinst, iconPathName, win32con.IMAGE_ICON, 0, 0, icon_flags
            )
        else:
            iconPathName = None
            print("Can't find a Python icon file - using default")
            hicon = LoadIcon(0, win32con.IDI_APPLICATION)
        self.iconPathName = iconPathName

        # Load up some information about menus needed by our owner-draw code.
        # The font to use on the menu.
        ncm = SystemParametersInfo(win32con.SPI_GETNONCLIENTMETRICS)
        self.font_menu = CreateFontIndirect(ncm["lfMenuFont"])
        # spacing for our ownerdraw menus - not sure exactly what constants
        # should be used (and if you owner-draw all items on the menu, it
        # doesn't matter!)
        self.menu_icon_height = GetSystemMetrics(win32con.SM_CYMENU) - 4
        self.menu_icon_width = self.menu_icon_height
        self.icon_x_pad = 8  # space from end of icon to start of text.
        # A map we use to stash away data we need for ownerdraw.  Keyed
        # by integer ID - that ID will be set in dwTypeData of the menu item.
        self.menu_item_map = {}

        # Finally, create the menu
        self.createMenu()

        flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, hicon, "Python Demo")
        Shell_NotifyIcon(NIM_ADD, nid)
        print("Please right-click on the Python icon in the taskbar")

    def createMenu(self):
        self.hmenu = menu = CreatePopupMenu()
        # Create our 'Exit' item with the standard, ugly 'close' icon.
        item, extras = PackMENUITEMINFO(
            text="Exit", hbmpItem=win32con.HBMMENU_MBAR_CLOSE, wID=1000
        )
        InsertMenuItem(menu, 0, 1, item)
        # Create a 'text only' menu via InsertMenuItem rather then
        # AppendMenu, just to prove we can!
        item, extras = PackMENUITEMINFO(text="Text only item", wID=1001)
        InsertMenuItem(menu, 0, 1, item)

        load_bmp_flags = win32con.LR_LOADFROMFILE | win32con.LR_LOADTRANSPARENT
        # These images are "over sized", so we load them scaled.
        hbmp = LoadImage(
            0,
            os.path.join(this_dir, "images/smiley.bmp"),
            win32con.IMAGE_BITMAP,
            20,
            20,
            load_bmp_flags,
        )

        # Create a top-level menu with a bitmap
        item, extras = PackMENUITEMINFO(
            text="Menu with bitmap", hbmpItem=hbmp, wID=1002
        )
        InsertMenuItem(menu, 0, 1, item)

        # Owner-draw menus mainly from:
        # https://learn.microsoft.com/en-ca/windows/win32/menurc/using-menus
        # and:
        # https://www.codeguru.com/cplusplus/owner-drawn-menu-with-icons/

        # Create one with an icon - this is *lots* more work - we do it
        # owner-draw!  The primary reason is to handle transparency better -
        # converting to a bitmap causes the background to be incorrect when
        # the menu item is selected.  I can't see a simpler way.
        # First, load the icon we want to use.
        ico_x = GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = GetSystemMetrics(win32con.SM_CYSMICON)
        if self.iconPathName:
            hicon = LoadImage(
                0,
                self.iconPathName,
                win32con.IMAGE_ICON,
                ico_x,
                ico_y,
                win32con.LR_LOADFROMFILE,
            )
        else:
            shell_dll = os.path.join(GetSystemDirectory(), "shell32.dll")
            large, small = win32gui.ExtractIconEx(shell_dll, 4, 1)
            hicon = small[0]
            DestroyIcon(large[0])

        # Stash away the text and hicon in our map, and add the owner-draw
        # item to the menu.
        index = 0
        self.menu_item_map[index] = (hicon, "Menu with owner-draw icon")
        item, extras = PackMENUITEMINFO(
            fType=win32con.MFT_OWNERDRAW, dwItemData=index, wID=1009
        )
        InsertMenuItem(menu, 0, 1, item)

        # Add another icon-based icon - but this time using HBMMENU_CALLBACK
        # in the hbmpItem elt, so we only need to draw the icon (ie, not the
        # text or checkmark)
        index = 1
        self.menu_item_map[index] = (hicon, None)
        item, extras = PackMENUITEMINFO(
            text="Menu with o-d icon 2",
            dwItemData=index,
            hbmpItem=win32con.HBMMENU_CALLBACK,
            wID=1010,
        )
        InsertMenuItem(menu, 0, 1, item)

        # Add another icon-based icon - this time by converting
        # via bitmap.  Note the icon background when selected is ugly :(
        hdcBitmap = CreateCompatibleDC(0)
        hdcScreen = GetDC(0)
        hbm = CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = SelectObject(hdcBitmap, hbm)
        SetBkMode(hdcBitmap, win32con.TRANSPARENT)
        # Fill the background.
        brush = GetSysColorBrush(win32con.COLOR_MENU)
        FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        # unclear if brush needs to be freed.  Best clue I can find is:
        # "GetSysColorBrush returns a cached brush instead of allocating a new
        # one." - implies no DeleteObject.
        # draw the icon
        DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        SelectObject(hdcBitmap, hbmOld)
        DeleteDC(hdcBitmap)
        item, extras = PackMENUITEMINFO(
            text="Menu with icon", hbmpItem=hbm.Detach(), wID=1011
        )
        InsertMenuItem(menu, 0, 1, item)

        # Create a sub-menu, and put a few funky ones there.
        self.sub_menu = sub_menu = CreatePopupMenu()
        # A 'checkbox' menu.
        item, extras = PackMENUITEMINFO(
            fState=win32con.MFS_CHECKED, text="Checkbox menu", hbmpItem=hbmp, wID=1003
        )
        InsertMenuItem(sub_menu, 0, 1, item)
        # A 'radio' menu.
        InsertMenu(sub_menu, 0, win32con.MF_BYPOSITION, win32con.MF_SEPARATOR, None)
        item, extras = PackMENUITEMINFO(
            fType=win32con.MFT_RADIOCHECK,
            fState=win32con.MFS_CHECKED,
            text="Checkbox menu - bullet 1",
            hbmpItem=hbmp,
            wID=1004,
        )
        InsertMenuItem(sub_menu, 0, 1, item)
        item, extras = PackMENUITEMINFO(
            fType=win32con.MFT_RADIOCHECK,
            fState=win32con.MFS_UNCHECKED,
            text="Checkbox menu - bullet 2",
            hbmpItem=hbmp,
            wID=1005,
        )
        InsertMenuItem(sub_menu, 0, 1, item)
        # And add the sub-menu to the top-level menu.
        item, extras = PackMENUITEMINFO(text="Sub-Menu", hSubMenu=sub_menu)
        InsertMenuItem(menu, 0, 1, item)

        # Set 'Exit' as the default option.
        SetMenuDefaultItem(menu, 1000, 0)

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        Shell_NotifyIcon(NIM_DELETE, nid)
        PostQuitMessage(0)  # Terminate the app.

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_RBUTTONUP:
            print("You right clicked me.")
            # display the menu at the cursor pos.
            pos = GetCursorPos()
            SetForegroundWindow(self.hwnd)
            TrackPopupMenu(
                self.hmenu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None
            )
            PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        elif lparam == win32con.WM_LBUTTONDBLCLK:
            print("You double-clicked me")
            # find the default menu item and fire it.
            cmd = GetMenuDefaultItem(self.hmenu, False, 0)
            if cmd == -1:
                print("Can't find a default!")
            # and just pretend it came from the menu
            self.OnCommand(hwnd, win32con.WM_COMMAND, cmd, 0)
        return 1

    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = LOWORD(wparam)
        if id == 1000:
            print("Goodbye")
            DestroyWindow(self.hwnd)
        elif id in (1003, 1004, 1005):
            # Our 'checkbox' and 'radio' items
            state = GetMenuState(self.sub_menu, id, win32con.MF_BYCOMMAND)
            if state == -1:
                raise RuntimeError("No item found")
            if state & win32con.MF_CHECKED:
                check_flags = win32con.MF_UNCHECKED
                print("Menu was checked - unchecking")
            else:
                check_flags = win32con.MF_CHECKED
                print("Menu was unchecked - checking")

            if id == 1003:
                # simple checkbox
                rc = CheckMenuItem(
                    self.sub_menu, id, win32con.MF_BYCOMMAND | check_flags
                )
            else:
                # radio button - must pass the first and last IDs in the
                # "group", and the ID in the group that is to be selected.
                rc = CheckMenuRadioItem(
                    self.sub_menu, 1004, 1005, id, win32con.MF_BYCOMMAND
                )
            # Get and check the new state - first the simple way...
            new_state = GetMenuState(self.sub_menu, id, win32con.MF_BYCOMMAND)
            if new_state & win32con.MF_CHECKED != check_flags:
                raise RuntimeError("The new item didn't get the new checked state!")
            # Now the long-winded way via GetMenuItemInfo...
            buf, extras = EmptyMENUITEMINFO()
            win32gui.GetMenuItemInfo(self.sub_menu, id, False, buf)
            (
                fType,
                fState,
                wID,
                hSubMenu,
                hbmpChecked,
                hbmpUnchecked,
                dwItemData,
                text,
                hbmpItem,
            ) = UnpackMENUITEMINFO(buf)

            if fState & win32con.MF_CHECKED != check_flags:
                raise RuntimeError("The new item didn't get the new checked state!")
        else:
            print("OnCommand for ID", id)

    # Owner-draw related functions.  We only have 1 owner-draw item, but
    # we pretend we have more than that :)
    def OnMeasureItem(self, hwnd, msg, wparam, lparam):
        ## Last item of MEASUREITEMSTRUCT is a ULONG_PTR
        fmt = "5iP"
        buf = PyMakeBuffer(struct.calcsize(fmt), lparam)
        data = struct.unpack(fmt, buf)
        ctlType, ctlID, itemID, itemWidth, itemHeight, itemData = data

        hicon, text = self.menu_item_map[itemData]
        if text is None:
            # Only drawing icon due to HBMMENU_CALLBACK
            cx = self.menu_icon_width
            cy = self.menu_icon_height
        else:
            # drawing the lot!
            dc = GetDC(hwnd)
            oldFont = SelectObject(dc, self.font_menu)
            cx, cy = GetTextExtentPoint32(dc, text)
            SelectObject(dc, oldFont)
            ReleaseDC(hwnd, dc)

            cx += GetSystemMetrics(win32con.SM_CXMENUCHECK)
            cx += self.menu_icon_width + self.icon_x_pad

            cy = GetSystemMetrics(win32con.SM_CYMENU)

        new_data = struct.pack(fmt, ctlType, ctlID, itemID, cx, cy, itemData)
        PySetMemory(lparam, new_data)
        return True

    def OnDrawItem(self, hwnd, msg, wparam, lparam):
        ## lparam is a DRAWITEMSTRUCT
        fmt = "5i2P4iP"
        data = struct.unpack(fmt, PyGetMemory(lparam, struct.calcsize(fmt)))
        (
            ctlType,
            ctlID,
            itemID,
            itemAction,
            itemState,
            hwndItem,
            hDC,
            left,
            top,
            right,
            bot,
            itemData,
        ) = data

        rect = left, top, right, bot
        hicon, text = self.menu_item_map[itemData]

        if text is None:
            # This means the menu-item had HBMMENU_CALLBACK - so all we
            # draw is the icon.  rect is the entire area we should use.
            DrawIconEx(
                hDC, left, top, hicon, right - left, bot - top, 0, 0, win32con.DI_NORMAL
            )
        else:
            # If the user has selected the item, use the selected
            # text and background colors to display the item.
            selected = itemState & win32con.ODS_SELECTED
            if selected:
                crText = SetTextColor(hDC, GetSysColor(win32con.COLOR_HIGHLIGHTTEXT))
                crBkgnd = SetBkColor(hDC, GetSysColor(win32con.COLOR_HIGHLIGHT))

            each_pad = self.icon_x_pad // 2
            x_icon = left + GetSystemMetrics(win32con.SM_CXMENUCHECK) + each_pad
            x_text = x_icon + self.menu_icon_width + each_pad

            # Draw text first, specifying a complete rect to fill - this sets
            # up the background (but overwrites anything else already there!)
            # Select the font, draw it, and restore the previous font.
            hfontOld = SelectObject(hDC, self.font_menu)
            ExtTextOut(hDC, x_text, top + 2, win32con.ETO_OPAQUE, rect, text)
            SelectObject(hDC, hfontOld)

            # Icon image next.  Icons are transparent - no need to handle
            # selection specially.
            DrawIconEx(
                hDC,
                x_icon,
                top + 2,
                hicon,
                self.menu_icon_width,
                self.menu_icon_height,
                0,
                0,
                win32con.DI_NORMAL,
            )

            # Return the text and background colors to their
            # normal state (not selected).
            if selected:
                SetTextColor(hDC, crText)
                SetBkColor(hDC, crBkgnd)


def main():
    w = MainWindow()
    PumpMessages()


if __name__ == "__main__":
    main()