
# === NexusCore/tools\exports\export_20250803_114325\combined_130.py ===

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\transports\rest.py ===
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
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content

from .base import CacheServiceTransport
from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class CacheServiceRestInterceptor:
    """Interceptor for CacheService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the CacheServiceRestTransport.

    .. code-block:: python
        class MyCustomCacheServiceInterceptor(CacheServiceRestInterceptor):
            def pre_create_cached_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_cached_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_cached_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_cached_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_cached_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_cached_contents(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_cached_contents(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_update_cached_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_cached_content(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = CacheServiceRestTransport(interceptor=MyCustomCacheServiceInterceptor())
        client = CacheServiceClient(transport=transport)


    """

    def pre_create_cached_content(
        self,
        request: cache_service.CreateCachedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[cache_service.CreateCachedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_cached_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the CacheService server.
        """
        return request, metadata

    def post_create_cached_content(
        self, response: gag_cached_content.CachedContent
    ) -> gag_cached_content.CachedContent:
        """Post-rpc interceptor for create_cached_content

        Override in a subclass to manipulate the response
        after it is returned by the CacheService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_cached_content(
        self,
        request: cache_service.DeleteCachedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[cache_service.DeleteCachedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_cached_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the CacheService server.
        """
        return request, metadata

    def pre_get_cached_content(
        self,
        request: cache_service.GetCachedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[cache_service.GetCachedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_cached_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the CacheService server.
        """
        return request, metadata

    def post_get_cached_content(
        self, response: cached_content.CachedContent
    ) -> cached_content.CachedContent:
        """Post-rpc interceptor for get_cached_content

        Override in a subclass to manipulate the response
        after it is returned by the CacheService server but before
        it is returned to user code.
        """
        return response

    def pre_list_cached_contents(
        self,
        request: cache_service.ListCachedContentsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[cache_service.ListCachedContentsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_cached_contents

        Override in a subclass to manipulate the request or metadata
        before they are sent to the CacheService server.
        """
        return request, metadata

    def post_list_cached_contents(
        self, response: cache_service.ListCachedContentsResponse
    ) -> cache_service.ListCachedContentsResponse:
        """Post-rpc interceptor for list_cached_contents

        Override in a subclass to manipulate the response
        after it is returned by the CacheService server but before
        it is returned to user code.
        """
        return response

    def pre_update_cached_content(
        self,
        request: cache_service.UpdateCachedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[cache_service.UpdateCachedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for update_cached_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the CacheService server.
        """
        return request, metadata

    def post_update_cached_content(
        self, response: gag_cached_content.CachedContent
    ) -> gag_cached_content.CachedContent:
        """Post-rpc interceptor for update_cached_content

        Override in a subclass to manipulate the response
        after it is returned by the CacheService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class CacheServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: CacheServiceRestInterceptor


class CacheServiceRestTransport(CacheServiceTransport):
    """REST backend transport for CacheService.

    API for managing cache of content (CachedContent resources)
    that can be used in GenerativeService requests. This way
    generate content requests can benefit from preprocessing work
    being done earlier, possibly lowering their computational cost.
    It is intended to be used with large contexts.

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
        interceptor: Optional[CacheServiceRestInterceptor] = None,
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
        self._interceptor = interceptor or CacheServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CreateCachedContent(CacheServiceRestStub):
        def __hash__(self):
            return hash("CreateCachedContent")

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
            request: cache_service.CreateCachedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_cached_content.CachedContent:
            r"""Call the create cached content method over HTTP.

            Args:
                request (~.cache_service.CreateCachedContentRequest):
                    The request object. Request to create CachedContent.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_cached_content.CachedContent:
                    Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/cachedContents",
                    "body": "cached_content",
                },
            ]
            request, metadata = self._interceptor.pre_create_cached_content(
                request, metadata
            )
            pb_request = cache_service.CreateCachedContentRequest.pb(request)
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
            resp = gag_cached_content.CachedContent()
            pb_resp = gag_cached_content.CachedContent.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_cached_content(resp)
            return resp

    class _DeleteCachedContent(CacheServiceRestStub):
        def __hash__(self):
            return hash("DeleteCachedContent")

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
            request: cache_service.DeleteCachedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete cached content method over HTTP.

            Args:
                request (~.cache_service.DeleteCachedContentRequest):
                    The request object. Request to delete CachedContent.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta/{name=cachedContents/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_cached_content(
                request, metadata
            )
            pb_request = cache_service.DeleteCachedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

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
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

    class _GetCachedContent(CacheServiceRestStub):
        def __hash__(self):
            return hash("GetCachedContent")

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
            request: cache_service.GetCachedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> cached_content.CachedContent:
            r"""Call the get cached content method over HTTP.

            Args:
                request (~.cache_service.GetCachedContentRequest):
                    The request object. Request to read CachedContent.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.cached_content.CachedContent:
                    Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{name=cachedContents/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_cached_content(
                request, metadata
            )
            pb_request = cache_service.GetCachedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

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
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = cached_content.CachedContent()
            pb_resp = cached_content.CachedContent.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_cached_content(resp)
            return resp

    class _ListCachedContents(CacheServiceRestStub):
        def __hash__(self):
            return hash("ListCachedContents")

        def __call__(
            self,
            request: cache_service.ListCachedContentsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> cache_service.ListCachedContentsResponse:
            r"""Call the list cached contents method over HTTP.

            Args:
                request (~.cache_service.ListCachedContentsRequest):
                    The request object. Request to list CachedContents.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.cache_service.ListCachedContentsResponse:
                    Response with CachedContents list.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/cachedContents",
                },
            ]
            request, metadata = self._interceptor.pre_list_cached_contents(
                request, metadata
            )
            pb_request = cache_service.ListCachedContentsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = cache_service.ListCachedContentsResponse()
            pb_resp = cache_service.ListCachedContentsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_cached_contents(resp)
            return resp

    class _UpdateCachedContent(CacheServiceRestStub):
        def __hash__(self):
            return hash("UpdateCachedContent")

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
            request: cache_service.UpdateCachedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_cached_content.CachedContent:
            r"""Call the update cached content method over HTTP.

            Args:
                request (~.cache_service.UpdateCachedContentRequest):
                    The request object. Request to update CachedContent.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_cached_content.CachedContent:
                    Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "patch",
                    "uri": "/v1beta/{cached_content.name=cachedContents/*}",
                    "body": "cached_content",
                },
            ]
            request, metadata = self._interceptor.pre_update_cached_content(
                request, metadata
            )
            pb_request = cache_service.UpdateCachedContentRequest.pb(request)
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
            resp = gag_cached_content.CachedContent()
            pb_resp = gag_cached_content.CachedContent.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_update_cached_content(resp)
            return resp

    @property
    def create_cached_content(
        self,
    ) -> Callable[
        [cache_service.CreateCachedContentRequest], gag_cached_content.CachedContent
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateCachedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_cached_content(
        self,
    ) -> Callable[[cache_service.DeleteCachedContentRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteCachedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_cached_content(
        self,
    ) -> Callable[
        [cache_service.GetCachedContentRequest], cached_content.CachedContent
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetCachedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_cached_contents(
        self,
    ) -> Callable[
        [cache_service.ListCachedContentsRequest],
        cache_service.ListCachedContentsResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListCachedContents(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def update_cached_content(
        self,
    ) -> Callable[
        [cache_service.UpdateCachedContentRequest], gag_cached_content.CachedContent
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateCachedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("CacheServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\budget_limiter.py ===
"""
Provider budget limiting

Use this if you want to set $ budget limits for each provider.

Note: This is a filter, like tag-routing. Meaning it will accept healthy deployments and then filter out deployments that have exceeded their budget limit.

This means you can use this with weighted-pick, lowest-latency, simple-shuffle, routing etc

Example:
```
openai:
	budget_limit: 0.000000000001
	time_period: 1d
anthropic:
	budget_limit: 100
	time_period: 7d
```
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import litellm
from litellm._logging import verbose_router_logger
from litellm.caching.caching import DualCache
from litellm.caching.redis_cache import RedisPipelineIncrementOperation
from litellm.integrations.custom_logger import CustomLogger, Span
from litellm.litellm_core_utils.duration_parser import duration_in_seconds
from litellm.router_strategy.tag_based_routing import _get_tags_from_request_kwargs
from litellm.router_utils.cooldown_callbacks import (
    _get_prometheus_logger_from_callbacks,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.router import DeploymentTypedDict, LiteLLM_Params, RouterErrors
from litellm.types.utils import BudgetConfig
from litellm.types.utils import BudgetConfig as GenericBudgetInfo
from litellm.types.utils import GenericBudgetConfigType, StandardLoggingPayload

DEFAULT_REDIS_SYNC_INTERVAL = 1


class RouterBudgetLimiting(CustomLogger):
    def __init__(
        self,
        dual_cache: DualCache,
        provider_budget_config: Optional[dict],
        model_list: Optional[
            Union[List[DeploymentTypedDict], List[Dict[str, Any]]]
        ] = None,
    ):
        self.dual_cache = dual_cache
        self.redis_increment_operation_queue: List[RedisPipelineIncrementOperation] = []
        asyncio.create_task(self.periodic_sync_in_memory_spend_with_redis())
        self.provider_budget_config: Optional[
            GenericBudgetConfigType
        ] = provider_budget_config
        self.deployment_budget_config: Optional[GenericBudgetConfigType] = None
        self.tag_budget_config: Optional[GenericBudgetConfigType] = None
        self._init_provider_budgets()
        self._init_deployment_budgets(model_list=model_list)
        self._init_tag_budgets()

        # Add self to litellm callbacks if it's a list
        if isinstance(litellm.callbacks, list):
            litellm.logging_callback_manager.add_litellm_callback(self)  # type: ignore

    async def async_filter_deployments(
        self,
        model: str,
        healthy_deployments: List,
        messages: Optional[List[AllMessageValues]],
        request_kwargs: Optional[dict] = None,
        parent_otel_span: Optional[Span] = None,  # type: ignore
    ) -> List[dict]:
        """
        Filter out deployments that have exceeded their provider budget limit.


        Example:
        if deployment = openai/gpt-3.5-turbo
            and openai spend > openai budget limit
                then skip this deployment
        """

        # If a single deployment is passed, convert it to a list
        if isinstance(healthy_deployments, dict):
            healthy_deployments = [healthy_deployments]

        # Don't do any filtering if there are no healthy deployments
        if len(healthy_deployments) == 0:
            return healthy_deployments

        potential_deployments: List[Dict] = []

        (
            cache_keys,
            provider_configs,
            deployment_configs,
        ) = await self._async_get_cache_keys_for_router_budget_limiting(
            healthy_deployments=healthy_deployments,
            request_kwargs=request_kwargs,
        )

        # Single cache read for all spend values
        if len(cache_keys) > 0:
            _current_spends = await self.dual_cache.async_batch_get_cache(
                keys=cache_keys,
                parent_otel_span=parent_otel_span,
            )
            current_spends: List = _current_spends or [0.0] * len(cache_keys)

            # Map spends to their respective keys
            spend_map: Dict[str, float] = {}
            for idx, key in enumerate(cache_keys):
                spend_map[key] = float(current_spends[idx] or 0.0)

            (
                potential_deployments,
                deployment_above_budget_info,
            ) = self._filter_out_deployments_above_budget(
                healthy_deployments=healthy_deployments,
                provider_configs=provider_configs,
                deployment_configs=deployment_configs,
                spend_map=spend_map,
                potential_deployments=potential_deployments,
                request_tags=_get_tags_from_request_kwargs(
                    request_kwargs=request_kwargs
                ),
            )

            if len(potential_deployments) == 0:
                raise ValueError(
                    f"{RouterErrors.no_deployments_with_provider_budget_routing.value}: {deployment_above_budget_info}"
                )

            return potential_deployments
        else:
            return healthy_deployments

    def _filter_out_deployments_above_budget(
        self,
        potential_deployments: List[Dict[str, Any]],
        healthy_deployments: List[Dict[str, Any]],
        provider_configs: Dict[str, GenericBudgetInfo],
        deployment_configs: Dict[str, GenericBudgetInfo],
        spend_map: Dict[str, float],
        request_tags: List[str],
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Filter out deployments that have exceeded their budget limit.
        Follow budget checks are run here:
            - Provider budget
            - Deployment budget
            - Request tags budget
        Returns:
            Tuple[List[Dict[str, Any]], str]:
                - A tuple containing the filtered deployments
                - A string containing debug information about deployments that exceeded their budget limit.
        """
        # Filter deployments based on both provider and deployment budgets
        deployment_above_budget_info: str = ""
        for deployment in healthy_deployments:
            is_within_budget = True

            # Check provider budget
            if self.provider_budget_config:
                provider = self._get_llm_provider_for_deployment(deployment)
                if provider in provider_configs:
                    config = provider_configs[provider]
                    if config.max_budget is None:
                        continue
                    current_spend = spend_map.get(
                        f"provider_spend:{provider}:{config.budget_duration}", 0.0
                    )
                    self._track_provider_remaining_budget_prometheus(
                        provider=provider,
                        spend=current_spend,
                        budget_limit=config.max_budget,
                    )

                    if config.max_budget and current_spend >= config.max_budget:
                        debug_msg = f"Exceeded budget for provider {provider}: {current_spend} >= {config.max_budget}"
                        deployment_above_budget_info += f"{debug_msg}\n"
                        is_within_budget = False
                        continue

            # Check deployment budget
            if self.deployment_budget_config and is_within_budget:
                _model_name = deployment.get("model_name")
                _litellm_params = deployment.get("litellm_params") or {}
                _litellm_model_name = _litellm_params.get("model")
                model_id = deployment.get("model_info", {}).get("id")
                if model_id in deployment_configs:
                    config = deployment_configs[model_id]
                    current_spend = spend_map.get(
                        f"deployment_spend:{model_id}:{config.budget_duration}", 0.0
                    )
                    if config.max_budget and current_spend >= config.max_budget:
                        debug_msg = f"Exceeded budget for deployment model_name: {_model_name}, litellm_params.model: {_litellm_model_name}, model_id: {model_id}: {current_spend} >= {config.budget_duration}"
                        verbose_router_logger.debug(debug_msg)
                        deployment_above_budget_info += f"{debug_msg}\n"
                        is_within_budget = False
                        continue
            # Check tag budget
            if self.tag_budget_config and is_within_budget:
                for _tag in request_tags:
                    _tag_budget_config = self._get_budget_config_for_tag(_tag)
                    if _tag_budget_config:
                        _tag_spend = spend_map.get(
                            f"tag_spend:{_tag}:{_tag_budget_config.budget_duration}",
                            0.0,
                        )
                        if (
                            _tag_budget_config.max_budget
                            and _tag_spend >= _tag_budget_config.max_budget
                        ):
                            debug_msg = f"Exceeded budget for tag='{_tag}', tag_spend={_tag_spend}, tag_budget_limit={_tag_budget_config.max_budget}"
                            verbose_router_logger.debug(debug_msg)
                            deployment_above_budget_info += f"{debug_msg}\n"
                            is_within_budget = False
                            continue
            if is_within_budget:
                potential_deployments.append(deployment)

        return potential_deployments, deployment_above_budget_info

    async def _async_get_cache_keys_for_router_budget_limiting(
        self,
        healthy_deployments: List[Dict[str, Any]],
        request_kwargs: Optional[Dict] = None,
    ) -> Tuple[List[str], Dict[str, GenericBudgetInfo], Dict[str, GenericBudgetInfo]]:
        """
        Returns list of cache keys to fetch from router cache for budget limiting and provider and deployment configs

        Returns:
            Tuple[List[str], Dict[str, GenericBudgetInfo], Dict[str, GenericBudgetInfo]]:
                - List of cache keys to fetch from router cache for budget limiting
                - Dict of provider budget configs `provider_configs`
                - Dict of deployment budget configs `deployment_configs`
        """
        cache_keys: List[str] = []
        provider_configs: Dict[str, GenericBudgetInfo] = {}
        deployment_configs: Dict[str, GenericBudgetInfo] = {}

        for deployment in healthy_deployments:
            # Check provider budgets
            if self.provider_budget_config:
                provider = self._get_llm_provider_for_deployment(deployment)
                if provider is not None:
                    budget_config = self._get_budget_config_for_provider(provider)
                    if (
                        budget_config is not None
                        and budget_config.budget_duration is not None
                    ):
                        provider_configs[provider] = budget_config
                        cache_keys.append(
                            f"provider_spend:{provider}:{budget_config.budget_duration}"
                        )

            # Check deployment budgets
            if self.deployment_budget_config:
                model_id = deployment.get("model_info", {}).get("id")
                if model_id is not None:
                    budget_config = self._get_budget_config_for_deployment(model_id)
                    if budget_config is not None:
                        deployment_configs[model_id] = budget_config
                        cache_keys.append(
                            f"deployment_spend:{model_id}:{budget_config.budget_duration}"
                        )
            # Check tag budgets
            if self.tag_budget_config:
                request_tags = _get_tags_from_request_kwargs(
                    request_kwargs=request_kwargs
                )
                for _tag in request_tags:
                    _tag_budget_config = self._get_budget_config_for_tag(_tag)
                    if _tag_budget_config:
                        cache_keys.append(
                            f"tag_spend:{_tag}:{_tag_budget_config.budget_duration}"
                        )
        return cache_keys, provider_configs, deployment_configs

    async def _get_or_set_budget_start_time(
        self, start_time_key: str, current_time: float, ttl_seconds: int
    ) -> float:
        """
        Checks if the key = `provider_budget_start_time:{provider}` exists in cache.

        If it does, return the value.
        If it does not, set the key to `current_time` and return the value.
        """
        budget_start = await self.dual_cache.async_get_cache(start_time_key)
        if budget_start is None:
            await self.dual_cache.async_set_cache(
                key=start_time_key, value=current_time, ttl=ttl_seconds
            )
            return current_time
        return float(budget_start)

    async def _handle_new_budget_window(
        self,
        spend_key: str,
        start_time_key: str,
        current_time: float,
        response_cost: float,
        ttl_seconds: int,
    ) -> float:
        """
        Handle start of new budget window by resetting spend and start time

        Enters this when:
        - The budget does not exist in cache, so we need to set it
        - The budget window has expired, so we need to reset everything

        Does 2 things:
        - stores key: `provider_spend:{provider}:1d`, value: response_cost
        - stores key: `provider_budget_start_time:{provider}`, value: current_time.
            This stores the start time of the new budget window
        """
        await self.dual_cache.async_set_cache(
            key=spend_key, value=response_cost, ttl=ttl_seconds
        )
        await self.dual_cache.async_set_cache(
            key=start_time_key, value=current_time, ttl=ttl_seconds
        )
        return current_time

    async def _increment_spend_in_current_window(
        self, spend_key: str, response_cost: float, ttl: int
    ):
        """
        Increment spend within existing budget window

        Runs once the budget start time exists in Redis Cache (on the 2nd and subsequent requests to the same provider)

        - Increments the spend in memory cache (so spend instantly updated in memory)
        - Queues the increment operation to Redis Pipeline (using batched pipeline to optimize performance. Using Redis for multi instance environment of LiteLLM)
        """
        await self.dual_cache.in_memory_cache.async_increment(
            key=spend_key,
            value=response_cost,
            ttl=ttl,
        )
        increment_op = RedisPipelineIncrementOperation(
            key=spend_key,
            increment_value=response_cost,
            ttl=ttl,
        )
        self.redis_increment_operation_queue.append(increment_op)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Original method now uses helper functions"""
        verbose_router_logger.debug("in RouterBudgetLimiting.async_log_success_event")
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object", None
        )
        if standard_logging_payload is None:
            raise ValueError("standard_logging_payload is required")

        response_cost: float = standard_logging_payload.get("response_cost", 0)
        model_id: str = str(standard_logging_payload.get("model_id", ""))
        custom_llm_provider: str = kwargs.get("litellm_params", {}).get(
            "custom_llm_provider", None
        )
        if custom_llm_provider is None:
            raise ValueError("custom_llm_provider is required")

        budget_config = self._get_budget_config_for_provider(custom_llm_provider)
        if budget_config:
            # increment spend for provider
            spend_key = (
                f"provider_spend:{custom_llm_provider}:{budget_config.budget_duration}"
            )
            start_time_key = f"provider_budget_start_time:{custom_llm_provider}"
            await self._increment_spend_for_key(
                budget_config=budget_config,
                spend_key=spend_key,
                start_time_key=start_time_key,
                response_cost=response_cost,
            )

        deployment_budget_config = self._get_budget_config_for_deployment(model_id)
        if deployment_budget_config:
            # increment spend for specific deployment id
            deployment_spend_key = f"deployment_spend:{model_id}:{deployment_budget_config.budget_duration}"
            deployment_start_time_key = f"deployment_budget_start_time:{model_id}"
            await self._increment_spend_for_key(
                budget_config=deployment_budget_config,
                spend_key=deployment_spend_key,
                start_time_key=deployment_start_time_key,
                response_cost=response_cost,
            )

        request_tags = _get_tags_from_request_kwargs(kwargs)
        if len(request_tags) > 0:
            for _tag in request_tags:
                _tag_budget_config = self._get_budget_config_for_tag(_tag)
                if _tag_budget_config:
                    _tag_spend_key = (
                        f"tag_spend:{_tag}:{_tag_budget_config.budget_duration}"
                    )
                    _tag_start_time_key = f"tag_budget_start_time:{_tag}"
                    await self._increment_spend_for_key(
                        budget_config=_tag_budget_config,
                        spend_key=_tag_spend_key,
                        start_time_key=_tag_start_time_key,
                        response_cost=response_cost,
                    )

    async def _increment_spend_for_key(
        self,
        budget_config: GenericBudgetInfo,
        spend_key: str,
        start_time_key: str,
        response_cost: float,
    ):
        if budget_config.budget_duration is None:
            return

        current_time = datetime.now(timezone.utc).timestamp()
        ttl_seconds = duration_in_seconds(budget_config.budget_duration)

        budget_start = await self._get_or_set_budget_start_time(
            start_time_key=start_time_key,
            current_time=current_time,
            ttl_seconds=ttl_seconds,
        )

        if budget_start is None:
            # First spend for this provider
            budget_start = await self._handle_new_budget_window(
                spend_key=spend_key,
                start_time_key=start_time_key,
                current_time=current_time,
                response_cost=response_cost,
                ttl_seconds=ttl_seconds,
            )
        elif (current_time - budget_start) > ttl_seconds:
            # Budget window expired - reset everything
            verbose_router_logger.debug("Budget window expired - resetting everything")
            budget_start = await self._handle_new_budget_window(
                spend_key=spend_key,
                start_time_key=start_time_key,
                current_time=current_time,
                response_cost=response_cost,
                ttl_seconds=ttl_seconds,
            )
        else:
            # Within existing window - increment spend
            remaining_time = ttl_seconds - (current_time - budget_start)
            ttl_for_increment = int(remaining_time)

            await self._increment_spend_in_current_window(
                spend_key=spend_key, response_cost=response_cost, ttl=ttl_for_increment
            )

        verbose_router_logger.debug(
            f"Incremented spend for {spend_key} by {response_cost}"
        )

    async def periodic_sync_in_memory_spend_with_redis(self):
        """
        Handler that triggers sync_in_memory_spend_with_redis every DEFAULT_REDIS_SYNC_INTERVAL seconds

        Required for multi-instance environment usage of provider budgets
        """
        while True:
            try:
                await self._sync_in_memory_spend_with_redis()
                await asyncio.sleep(
                    DEFAULT_REDIS_SYNC_INTERVAL
                )  # Wait for DEFAULT_REDIS_SYNC_INTERVAL seconds before next sync
            except Exception as e:
                verbose_router_logger.error(f"Error in periodic sync task: {str(e)}")
                await asyncio.sleep(
                    DEFAULT_REDIS_SYNC_INTERVAL
                )  # Still wait DEFAULT_REDIS_SYNC_INTERVAL seconds on error before retrying

    async def _push_in_memory_increments_to_redis(self):
        """
        How this works:
        - async_log_success_event collects all provider spend increments in `redis_increment_operation_queue`
        - This function pushes all increments to Redis in a batched pipeline to optimize performance

        Only runs if Redis is initialized
        """
        try:
            if not self.dual_cache.redis_cache:
                return  # Redis is not initialized

            verbose_router_logger.debug(
                "Pushing Redis Increment Pipeline for queue: %s",
                self.redis_increment_operation_queue,
            )
            if len(self.redis_increment_operation_queue) > 0:
                asyncio.create_task(
                    self.dual_cache.redis_cache.async_increment_pipeline(
                        increment_list=self.redis_increment_operation_queue,
                    )
                )

            self.redis_increment_operation_queue = []

        except Exception as e:
            verbose_router_logger.error(
                f"Error syncing in-memory cache with Redis: {str(e)}"
            )

    async def _sync_in_memory_spend_with_redis(self):
        """
        Ensures in-memory cache is updated with latest Redis values for all provider spends.

        Why Do we need this?
        - Optimization to hit sub 100ms latency. Performance was impacted when redis was used for read/write per request
        - Use provider budgets in multi-instance environment, we use Redis to sync spend across all instances

        What this does:
        1. Push all provider spend increments to Redis
        2. Fetch all current provider spend from Redis to update in-memory cache
        """

        try:
            # No need to sync if Redis cache is not initialized
            if self.dual_cache.redis_cache is None:
                return

            # 1. Push all provider spend increments to Redis
            await self._push_in_memory_increments_to_redis()

            # 2. Fetch all current provider spend from Redis to update in-memory cache
            cache_keys = []

            if self.provider_budget_config is not None:
                for provider, config in self.provider_budget_config.items():
                    if config is None:
                        continue
                    cache_keys.append(
                        f"provider_spend:{provider}:{config.budget_duration}"
                    )

            if self.deployment_budget_config is not None:
                for model_id, config in self.deployment_budget_config.items():
                    if config is None:
                        continue
                    cache_keys.append(
                        f"deployment_spend:{model_id}:{config.budget_duration}"
                    )

            if self.tag_budget_config is not None:
                for tag, config in self.tag_budget_config.items():
                    if config is None:
                        continue
                    cache_keys.append(f"tag_spend:{tag}:{config.budget_duration}")

            # Batch fetch current spend values from Redis
            redis_values = await self.dual_cache.redis_cache.async_batch_get_cache(
                key_list=cache_keys
            )

            # Update in-memory cache with Redis values
            if isinstance(redis_values, dict):  # Check if redis_values is a dictionary
                for key, value in redis_values.items():
                    if value is not None:
                        await self.dual_cache.in_memory_cache.async_set_cache(
                            key=key, value=float(value)
                        )
                        verbose_router_logger.debug(
                            f"Updated in-memory cache for {key}: {value}"
                        )

        except Exception as e:
            verbose_router_logger.error(
                f"Error syncing in-memory cache with Redis: {str(e)}"
            )

    def _get_budget_config_for_deployment(
        self,
        model_id: str,
    ) -> Optional[GenericBudgetInfo]:
        if self.deployment_budget_config is None:
            return None
        return self.deployment_budget_config.get(model_id, None)

    def _get_budget_config_for_provider(
        self, provider: str
    ) -> Optional[GenericBudgetInfo]:
        if self.provider_budget_config is None:
            return None
        return self.provider_budget_config.get(provider, None)

    def _get_budget_config_for_tag(self, tag: str) -> Optional[GenericBudgetInfo]:
        if self.tag_budget_config is None:
            return None
        return self.tag_budget_config.get(tag, None)

    def _get_llm_provider_for_deployment(self, deployment: Dict) -> Optional[str]:
        try:
            _litellm_params: LiteLLM_Params = LiteLLM_Params(
                **deployment.get("litellm_params", {"model": ""})
            )
            _, custom_llm_provider, _, _ = litellm.get_llm_provider(
                model=_litellm_params.model,
                litellm_params=_litellm_params,
            )
        except Exception:
            verbose_router_logger.error(
                f"Error getting LLM provider for deployment: {deployment}"
            )
            return None
        return custom_llm_provider

    def _track_provider_remaining_budget_prometheus(
        self, provider: str, spend: float, budget_limit: float
    ):
        """
        Optional helper - emit provider remaining budget metric to Prometheus

        This is helpful for debugging and monitoring provider budget limits.
        """

        prometheus_logger = _get_prometheus_logger_from_callbacks()
        if prometheus_logger:
            prometheus_logger.track_provider_remaining_budget(
                provider=provider,
                spend=spend,
                budget_limit=budget_limit,
            )

    async def _get_current_provider_spend(self, provider: str) -> Optional[float]:
        """
        GET the current spend for a provider from cache

        used for GET /provider/budgets endpoint in spend_management_endpoints.py

        Args:
            provider (str): The provider to get spend for (e.g., "openai", "anthropic")

        Returns:
            Optional[float]: The current spend for the provider, or None if not found
        """
        budget_config = self._get_budget_config_for_provider(provider)
        if budget_config is None:
            return None

        spend_key = f"provider_spend:{provider}:{budget_config.budget_duration}"

        if self.dual_cache.redis_cache:
            # use Redis as source of truth since that has spend across all instances
            current_spend = await self.dual_cache.redis_cache.async_get_cache(spend_key)
        else:
            # use in-memory cache if Redis is not initialized
            current_spend = await self.dual_cache.async_get_cache(spend_key)
        return float(current_spend) if current_spend is not None else 0.0

    async def _get_current_provider_budget_reset_at(
        self, provider: str
    ) -> Optional[str]:
        budget_config = self._get_budget_config_for_provider(provider)
        if budget_config is None:
            return None

        spend_key = f"provider_spend:{provider}:{budget_config.budget_duration}"
        if self.dual_cache.redis_cache:
            ttl_seconds = await self.dual_cache.redis_cache.async_get_ttl(spend_key)
        else:
            ttl_seconds = await self.dual_cache.async_get_ttl(spend_key)

        if ttl_seconds is None:
            return None

        return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()

    async def _init_provider_budget_in_cache(
        self, provider: str, budget_config: GenericBudgetInfo
    ):
        """
        Initialize provider budget in cache by storing the following keys if they don't exist:
        - provider_spend:{provider}:{budget_config.time_period} - stores the current spend
        - provider_budget_start_time:{provider} - stores the start time of the budget window

        """

        spend_key = f"provider_spend:{provider}:{budget_config.budget_duration}"
        start_time_key = f"provider_budget_start_time:{provider}"
        ttl_seconds: Optional[int] = None
        if budget_config.budget_duration is not None:
            ttl_seconds = duration_in_seconds(budget_config.budget_duration)

        budget_start = await self.dual_cache.async_get_cache(start_time_key)
        if budget_start is None:
            budget_start = datetime.now(timezone.utc).timestamp()
            await self.dual_cache.async_set_cache(
                key=start_time_key, value=budget_start, ttl=ttl_seconds
            )

        _spend_key = await self.dual_cache.async_get_cache(spend_key)
        if _spend_key is None:
            await self.dual_cache.async_set_cache(
                key=spend_key, value=0.0, ttl=ttl_seconds
            )

    @staticmethod
    def should_init_router_budget_limiter(
        provider_budget_config: Optional[dict],
        model_list: Optional[
            Union[List[DeploymentTypedDict], List[Dict[str, Any]]]
        ] = None,
    ):
        """
        Returns `True` if the router budget routing settings are set and RouterBudgetLimiting should be initialized

        Either:
         - provider_budget_config is set
         - budgets are set for deployments in the model_list
         - tag_budget_config is set
        """
        if provider_budget_config is not None:
            return True

        if litellm.tag_budget_config is not None:
            return True

        if model_list is None:
            return False

        for _model in model_list:
            _litellm_params = _model.get("litellm_params", {})
            if (
                _litellm_params.get("max_budget")
                or _litellm_params.get("budget_duration") is not None
            ):
                return True
        return False

    def _init_provider_budgets(self):
        if self.provider_budget_config is not None:
            # cast elements of provider_budget_config to GenericBudgetInfo
            for provider, config in self.provider_budget_config.items():
                if config is None:
                    raise ValueError(
                        f"No budget config found for provider {provider}, provider_budget_config: {self.provider_budget_config}"
                    )

                if not isinstance(config, GenericBudgetInfo):
                    self.provider_budget_config[provider] = GenericBudgetInfo(
                        budget_limit=config.get("budget_limit"),
                        time_period=config.get("time_period"),
                    )
                asyncio.create_task(
                    self._init_provider_budget_in_cache(
                        provider=provider,
                        budget_config=self.provider_budget_config[provider],
                    )
                )

            verbose_router_logger.debug(
                f"Initalized Provider budget config: {self.provider_budget_config}"
            )

    def _init_deployment_budgets(
        self,
        model_list: Optional[
            Union[List[DeploymentTypedDict], List[Dict[str, Any]]]
        ] = None,
    ):
        if model_list is None:
            return
        for _model in model_list:
            _litellm_params = _model.get("litellm_params", {})
            _model_info: Dict = _model.get("model_info") or {}
            _model_id = _model_info.get("id")
            _max_budget = _litellm_params.get("max_budget")
            _budget_duration = _litellm_params.get("budget_duration")

            verbose_router_logger.debug(
                f"Init Deployment Budget: max_budget: {_max_budget}, budget_duration: {_budget_duration}, model_id: {_model_id}"
            )
            if (
                _max_budget is not None
                and _budget_duration is not None
                and _model_id is not None
            ):
                _budget_config = GenericBudgetInfo(
                    time_period=_budget_duration,
                    budget_limit=_max_budget,
                )
                if self.deployment_budget_config is None:
                    self.deployment_budget_config = {}
                self.deployment_budget_config[_model_id] = _budget_config

        verbose_router_logger.debug(
            f"Initialized Deployment Budget Config: {self.deployment_budget_config}"
        )

    def _init_tag_budgets(self):
        if litellm.tag_budget_config is None:
            return
        from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

        if premium_user is not True:
            raise ValueError(
                f"Tag budgets are an Enterprise only feature, {CommonProxyErrors.not_premium_user}"
            )

        if self.tag_budget_config is None:
            self.tag_budget_config = {}

        for _tag, _tag_budget_config in litellm.tag_budget_config.items():
            if isinstance(_tag_budget_config, dict):
                _tag_budget_config = BudgetConfig(**_tag_budget_config)
            _generic_budget_config = GenericBudgetInfo(
                time_period=_tag_budget_config.budget_duration,
                budget_limit=_tag_budget_config.max_budget,
            )
            self.tag_budget_config[_tag] = _generic_budget_config

        verbose_router_logger.debug(
            f"Initialized Tag Budget Config: {self.tag_budget_config}"
        )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\renderer.py ===
"""
Renders the command line on the console.
(Redraws parts of the input line that were changed.)
"""

from __future__ import annotations

from asyncio import FIRST_COMPLETED, Future, ensure_future, sleep, wait
from collections import deque
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, Hashable

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText, to_formatted_text
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, Screen, WritePosition
from prompt_toolkit.output import ColorDepth, Output
from prompt_toolkit.styles import (
    Attrs,
    BaseStyle,
    DummyStyleTransformation,
    StyleTransformation,
)

if TYPE_CHECKING:
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout.layout import Layout


__all__ = [
    "Renderer",
    "print_formatted_text",
]


def _output_screen_diff(
    app: Application[Any],
    output: Output,
    screen: Screen,
    current_pos: Point,
    color_depth: ColorDepth,
    previous_screen: Screen | None,
    last_style: str | None,
    is_done: bool,  # XXX: drop is_done
    full_screen: bool,
    attrs_for_style_string: _StyleStringToAttrsCache,
    style_string_has_style: _StyleStringHasStyleCache,
    size: Size,
    previous_width: int,
) -> tuple[Point, str | None]:
    """
    Render the diff between this screen and the previous screen.

    This takes two `Screen` instances. The one that represents the output like
    it was during the last rendering and one that represents the current
    output raster. Looking at these two `Screen` instances, this function will
    render the difference by calling the appropriate methods of the `Output`
    object that only paint the changes to the terminal.

    This is some performance-critical code which is heavily optimized.
    Don't change things without profiling first.

    :param current_pos: Current cursor position.
    :param last_style: The style string, used for drawing the last drawn
        character.  (Color/attributes.)
    :param attrs_for_style_string: :class:`._StyleStringToAttrsCache` instance.
    :param width: The width of the terminal.
    :param previous_width: The width of the terminal during the last rendering.
    """
    width, height = size.columns, size.rows

    #: Variable for capturing the output.
    write = output.write
    write_raw = output.write_raw

    # Create locals for the most used output methods.
    # (Save expensive attribute lookups.)
    _output_set_attributes = output.set_attributes
    _output_reset_attributes = output.reset_attributes
    _output_cursor_forward = output.cursor_forward
    _output_cursor_up = output.cursor_up
    _output_cursor_backward = output.cursor_backward

    # Hide cursor before rendering. (Avoid flickering.)
    output.hide_cursor()

    def reset_attributes() -> None:
        "Wrapper around Output.reset_attributes."
        nonlocal last_style
        _output_reset_attributes()
        last_style = None  # Forget last char after resetting attributes.

    def move_cursor(new: Point) -> Point:
        "Move cursor to this `new` point. Returns the given Point."
        current_x, current_y = current_pos.x, current_pos.y

        if new.y > current_y:
            # Use newlines instead of CURSOR_DOWN, because this might add new lines.
            # CURSOR_DOWN will never create new lines at the bottom.
            # Also reset attributes, otherwise the newline could draw a
            # background color.
            reset_attributes()
            write("\r\n" * (new.y - current_y))
            current_x = 0
            _output_cursor_forward(new.x)
            return new
        elif new.y < current_y:
            _output_cursor_up(current_y - new.y)

        if current_x >= width - 1:
            write("\r")
            _output_cursor_forward(new.x)
        elif new.x < current_x or current_x >= width - 1:
            _output_cursor_backward(current_x - new.x)
        elif new.x > current_x:
            _output_cursor_forward(new.x - current_x)

        return new

    def output_char(char: Char) -> None:
        """
        Write the output of this character.
        """
        nonlocal last_style

        # If the last printed character has the same style, don't output the
        # style again.
        if last_style == char.style:
            write(char.char)
        else:
            # Look up `Attr` for this style string. Only set attributes if different.
            # (Two style strings can still have the same formatting.)
            # Note that an empty style string can have formatting that needs to
            # be applied, because of style transformations.
            new_attrs = attrs_for_style_string[char.style]
            if not last_style or new_attrs != attrs_for_style_string[last_style]:
                _output_set_attributes(new_attrs, color_depth)

            write(char.char)
            last_style = char.style

    def get_max_column_index(row: dict[int, Char]) -> int:
        """
        Return max used column index, ignoring whitespace (without style) at
        the end of the line. This is important for people that copy/paste
        terminal output.

        There are two reasons we are sometimes seeing whitespace at the end:
        - `BufferControl` adds a trailing space to each line, because it's a
          possible cursor position, so that the line wrapping won't change if
          the cursor position moves around.
        - The `Window` adds a style class to the current line for highlighting
          (cursor-line).
        """
        numbers = (
            index
            for index, cell in row.items()
            if cell.char != " " or style_string_has_style[cell.style]
        )
        return max(numbers, default=0)

    # Render for the first time: reset styling.
    if not previous_screen:
        reset_attributes()

    # Disable autowrap. (When entering a the alternate screen, or anytime when
    # we have a prompt. - In the case of a REPL, like IPython, people can have
    # background threads, and it's hard for debugging if their output is not
    # wrapped.)
    if not previous_screen or not full_screen:
        output.disable_autowrap()

    # When the previous screen has a different size, redraw everything anyway.
    # Also when we are done. (We might take up less rows, so clearing is important.)
    if (
        is_done or not previous_screen or previous_width != width
    ):  # XXX: also consider height??
        current_pos = move_cursor(Point(x=0, y=0))
        reset_attributes()
        output.erase_down()

        previous_screen = Screen()

    # Get height of the screen.
    # (height changes as we loop over data_buffer, so remember the current value.)
    # (Also make sure to clip the height to the size of the output.)
    current_height = min(screen.height, height)

    # Loop over the rows.
    row_count = min(max(screen.height, previous_screen.height), height)

    for y in range(row_count):
        new_row = screen.data_buffer[y]
        previous_row = previous_screen.data_buffer[y]
        zero_width_escapes_row = screen.zero_width_escapes[y]

        new_max_line_len = min(width - 1, get_max_column_index(new_row))
        previous_max_line_len = min(width - 1, get_max_column_index(previous_row))

        # Loop over the columns.
        c = 0  # Column counter.
        while c <= new_max_line_len:
            new_char = new_row[c]
            old_char = previous_row[c]
            char_width = new_char.width or 1

            # When the old and new character at this position are different,
            # draw the output. (Because of the performance, we don't call
            # `Char.__ne__`, but inline the same expression.)
            if new_char.char != old_char.char or new_char.style != old_char.style:
                current_pos = move_cursor(Point(x=c, y=y))

                # Send injected escape sequences to output.
                if c in zero_width_escapes_row:
                    write_raw(zero_width_escapes_row[c])

                output_char(new_char)
                current_pos = Point(x=current_pos.x + char_width, y=current_pos.y)

            c += char_width

        # If the new line is shorter, trim it.
        if previous_screen and new_max_line_len < previous_max_line_len:
            current_pos = move_cursor(Point(x=new_max_line_len + 1, y=y))
            reset_attributes()
            output.erase_end_of_line()

    # Correctly reserve vertical space as required by the layout.
    # When this is a new screen (drawn for the first time), or for some reason
    # higher than the previous one. Move the cursor once to the bottom of the
    # output. That way, we're sure that the terminal scrolls up, even when the
    # lower lines of the canvas just contain whitespace.

    # The most obvious reason that we actually want this behavior is the avoid
    # the artifact of the input scrolling when the completion menu is shown.
    # (If the scrolling is actually wanted, the layout can still be build in a
    # way to behave that way by setting a dynamic height.)
    if current_height > previous_screen.height:
        current_pos = move_cursor(Point(x=0, y=current_height - 1))

    # Move cursor:
    if is_done:
        current_pos = move_cursor(Point(x=0, y=current_height))
        output.erase_down()
    else:
        current_pos = move_cursor(screen.get_cursor_position(app.layout.current_window))

    if is_done or not full_screen:
        output.enable_autowrap()

    # Always reset the color attributes. This is important because a background
    # thread could print data to stdout and we want that to be displayed in the
    # default colors. (Also, if a background color has been set, many terminals
    # give weird artifacts on resize events.)
    reset_attributes()

    if screen.show_cursor:
        output.show_cursor()

    return current_pos, last_style


class HeightIsUnknownError(Exception):
    "Information unavailable. Did not yet receive the CPR response."


class _StyleStringToAttrsCache(Dict[str, Attrs]):
    """
    A cache structure that maps style strings to :class:`.Attr`.
    (This is an important speed up.)
    """

    def __init__(
        self,
        get_attrs_for_style_str: Callable[[str], Attrs],
        style_transformation: StyleTransformation,
    ) -> None:
        self.get_attrs_for_style_str = get_attrs_for_style_str
        self.style_transformation = style_transformation

    def __missing__(self, style_str: str) -> Attrs:
        attrs = self.get_attrs_for_style_str(style_str)
        attrs = self.style_transformation.transform_attrs(attrs)

        self[style_str] = attrs
        return attrs


class _StyleStringHasStyleCache(Dict[str, bool]):
    """
    Cache for remember which style strings don't render the default output
    style (default fg/bg, no underline and no reverse and no blink). That way
    we know that we should render these cells, even when they're empty (when
    they contain a space).

    Note: we don't consider bold/italic/hidden because they don't change the
    output if there's no text in the cell.
    """

    def __init__(self, style_string_to_attrs: dict[str, Attrs]) -> None:
        self.style_string_to_attrs = style_string_to_attrs

    def __missing__(self, style_str: str) -> bool:
        attrs = self.style_string_to_attrs[style_str]
        is_default = bool(
            attrs.color
            or attrs.bgcolor
            or attrs.underline
            or attrs.strike
            or attrs.blink
            or attrs.reverse
        )

        self[style_str] = is_default
        return is_default


class CPR_Support(Enum):
    "Enum: whether or not CPR is supported."

    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"


class Renderer:
    """
    Typical usage:

    ::

        output = Vt100_Output.from_pty(sys.stdout)
        r = Renderer(style, output)
        r.render(app, layout=...)
    """

    CPR_TIMEOUT = 2  # Time to wait until we consider CPR to be not supported.

    def __init__(
        self,
        style: BaseStyle,
        output: Output,
        full_screen: bool = False,
        mouse_support: FilterOrBool = False,
        cpr_not_supported_callback: Callable[[], None] | None = None,
    ) -> None:
        self.style = style
        self.output = output
        self.full_screen = full_screen
        self.mouse_support = to_filter(mouse_support)
        self.cpr_not_supported_callback = cpr_not_supported_callback

        # TODO: Move following state flags into `Vt100_Output`, similar to
        #       `_cursor_shape_changed` and `_cursor_visible`. But then also
        #       adjust the `Win32Output` to not call win32 APIs if nothing has
        #       to be changed.

        self._in_alternate_screen = False
        self._mouse_support_enabled = False
        self._bracketed_paste_enabled = False
        self._cursor_key_mode_reset = False

        # Future set when we are waiting for a CPR flag.
        self._waiting_for_cpr_futures: deque[Future[None]] = deque()
        self.cpr_support = CPR_Support.UNKNOWN

        if not output.responds_to_cpr:
            self.cpr_support = CPR_Support.NOT_SUPPORTED

        # Cache for the style.
        self._attrs_for_style: _StyleStringToAttrsCache | None = None
        self._style_string_has_style: _StyleStringHasStyleCache | None = None
        self._last_style_hash: Hashable | None = None
        self._last_transformation_hash: Hashable | None = None
        self._last_color_depth: ColorDepth | None = None

        self.reset(_scroll=True)

    def reset(self, _scroll: bool = False, leave_alternate_screen: bool = True) -> None:
        # Reset position
        self._cursor_pos = Point(x=0, y=0)

        # Remember the last screen instance between renderers. This way,
        # we can create a `diff` between two screens and only output the
        # difference. It's also to remember the last height. (To show for
        # instance a toolbar at the bottom position.)
        self._last_screen: Screen | None = None
        self._last_size: Size | None = None
        self._last_style: str | None = None
        self._last_cursor_shape: CursorShape | None = None

        # Default MouseHandlers. (Just empty.)
        self.mouse_handlers = MouseHandlers()

        #: Space from the top of the layout, until the bottom of the terminal.
        #: We don't know this until a `report_absolute_cursor_row` call.
        self._min_available_height = 0

        # In case of Windows, also make sure to scroll to the current cursor
        # position. (Only when rendering the first time.)
        # It does nothing for vt100 terminals.
        if _scroll:
            self.output.scroll_buffer_to_prompt()

        # Quit alternate screen.
        if self._in_alternate_screen and leave_alternate_screen:
            self.output.quit_alternate_screen()
            self._in_alternate_screen = False

        # Disable mouse support.
        if self._mouse_support_enabled:
            self.output.disable_mouse_support()
            self._mouse_support_enabled = False

        # Disable bracketed paste.
        if self._bracketed_paste_enabled:
            self.output.disable_bracketed_paste()
            self._bracketed_paste_enabled = False

        self.output.reset_cursor_shape()
        self.output.show_cursor()

        # NOTE: No need to set/reset cursor key mode here.

        # Flush output. `disable_mouse_support` needs to write to stdout.
        self.output.flush()

    @property
    def last_rendered_screen(self) -> Screen | None:
        """
        The `Screen` class that was generated during the last rendering.
        This can be `None`.
        """
        return self._last_screen

    @property
    def height_is_known(self) -> bool:
        """
        True when the height from the cursor until the bottom of the terminal
        is known. (It's often nicer to draw bottom toolbars only if the height
        is known, in order to avoid flickering when the CPR response arrives.)
        """
        if self.full_screen or self._min_available_height > 0:
            return True
        try:
            self._min_available_height = self.output.get_rows_below_cursor_position()
            return True
        except NotImplementedError:
            return False

    @property
    def rows_above_layout(self) -> int:
        """
        Return the number of rows visible in the terminal above the layout.
        """
        if self._in_alternate_screen:
            return 0
        elif self._min_available_height > 0:
            total_rows = self.output.get_size().rows
            last_screen_height = self._last_screen.height if self._last_screen else 0
            return total_rows - max(self._min_available_height, last_screen_height)
        else:
            raise HeightIsUnknownError("Rows above layout is unknown.")

    def request_absolute_cursor_position(self) -> None:
        """
        Get current cursor position.

        We do this to calculate the minimum available height that we can
        consume for rendering the prompt. This is the available space below te
        cursor.

        For vt100: Do CPR request. (answer will arrive later.)
        For win32: Do API call. (Answer comes immediately.)
        """
        # Only do this request when the cursor is at the top row. (after a
        # clear or reset). We will rely on that in `report_absolute_cursor_row`.
        assert self._cursor_pos.y == 0

        # In full-screen mode, always use the total height as min-available-height.
        if self.full_screen:
            self._min_available_height = self.output.get_size().rows
            return

        # For Win32, we have an API call to get the number of rows below the
        # cursor.
        try:
            self._min_available_height = self.output.get_rows_below_cursor_position()
            return
        except NotImplementedError:
            pass

        # Use CPR.
        if self.cpr_support == CPR_Support.NOT_SUPPORTED:
            return

        def do_cpr() -> None:
            # Asks for a cursor position report (CPR).
            self._waiting_for_cpr_futures.append(Future())
            self.output.ask_for_cpr()

        if self.cpr_support == CPR_Support.SUPPORTED:
            do_cpr()
            return

        # If we don't know whether CPR is supported, only do a request if
        # none is pending, and test it, using a timer.
        if self.waiting_for_cpr:
            return

        do_cpr()

        async def timer() -> None:
            await sleep(self.CPR_TIMEOUT)

            # Not set in the meantime -> not supported.
            if self.cpr_support == CPR_Support.UNKNOWN:
                self.cpr_support = CPR_Support.NOT_SUPPORTED

                if self.cpr_not_supported_callback:
                    # Make sure to call this callback in the main thread.
                    self.cpr_not_supported_callback()

        get_app().create_background_task(timer())

    def report_absolute_cursor_row(self, row: int) -> None:
        """
        To be called when we know the absolute cursor position.
        (As an answer of a "Cursor Position Request" response.)
        """
        self.cpr_support = CPR_Support.SUPPORTED

        # Calculate the amount of rows from the cursor position until the
        # bottom of the terminal.
        total_rows = self.output.get_size().rows
        rows_below_cursor = total_rows - row + 1

        # Set the minimum available height.
        self._min_available_height = rows_below_cursor

        # Pop and set waiting for CPR future.
        try:
            f = self._waiting_for_cpr_futures.popleft()
        except IndexError:
            pass  # Received CPR response without having a CPR.
        else:
            f.set_result(None)

    @property
    def waiting_for_cpr(self) -> bool:
        """
        Waiting for CPR flag. True when we send the request, but didn't got a
        response.
        """
        return bool(self._waiting_for_cpr_futures)

    async def wait_for_cpr_responses(self, timeout: int = 1) -> None:
        """
        Wait for a CPR response.
        """
        cpr_futures = list(self._waiting_for_cpr_futures)  # Make copy.

        # When there are no CPRs in the queue. Don't do anything.
        if not cpr_futures or self.cpr_support == CPR_Support.NOT_SUPPORTED:
            return None

        async def wait_for_responses() -> None:
            for response_f in cpr_futures:
                await response_f

        async def wait_for_timeout() -> None:
            await sleep(timeout)

            # Got timeout, erase queue.
            for response_f in cpr_futures:
                response_f.cancel()
            self._waiting_for_cpr_futures = deque()

        tasks = {
            ensure_future(wait_for_responses()),
            ensure_future(wait_for_timeout()),
        }
        _, pending = await wait(tasks, return_when=FIRST_COMPLETED)
        for task in pending:
            task.cancel()

    def render(
        self, app: Application[Any], layout: Layout, is_done: bool = False
    ) -> None:
        """
        Render the current interface to the output.

        :param is_done: When True, put the cursor at the end of the interface. We
                won't print any changes to this part.
        """
        output = self.output

        # Enter alternate screen.
        if self.full_screen and not self._in_alternate_screen:
            self._in_alternate_screen = True
            output.enter_alternate_screen()

        # Enable bracketed paste.
        if not self._bracketed_paste_enabled:
            self.output.enable_bracketed_paste()
            self._bracketed_paste_enabled = True

        # Reset cursor key mode.
        if not self._cursor_key_mode_reset:
            self.output.reset_cursor_key_mode()
            self._cursor_key_mode_reset = True

        # Enable/disable mouse support.
        needs_mouse_support = self.mouse_support()

        if needs_mouse_support and not self._mouse_support_enabled:
            output.enable_mouse_support()
            self._mouse_support_enabled = True

        elif not needs_mouse_support and self._mouse_support_enabled:
            output.disable_mouse_support()
            self._mouse_support_enabled = False

        # Create screen and write layout to it.
        size = output.get_size()
        screen = Screen()
        screen.show_cursor = False  # Hide cursor by default, unless one of the
        # containers decides to display it.
        mouse_handlers = MouseHandlers()

        # Calculate height.
        if self.full_screen:
            height = size.rows
        elif is_done:
            # When we are done, we don't necessary want to fill up until the bottom.
            height = layout.container.preferred_height(
                size.columns, size.rows
            ).preferred
        else:
            last_height = self._last_screen.height if self._last_screen else 0
            height = max(
                self._min_available_height,
                last_height,
                layout.container.preferred_height(size.columns, size.rows).preferred,
            )

        height = min(height, size.rows)

        # When the size changes, don't consider the previous screen.
        if self._last_size != size:
            self._last_screen = None

        # When we render using another style or another color depth, do a full
        # repaint. (Forget about the previous rendered screen.)
        # (But note that we still use _last_screen to calculate the height.)
        if (
            self.style.invalidation_hash() != self._last_style_hash
            or app.style_transformation.invalidation_hash()
            != self._last_transformation_hash
            or app.color_depth != self._last_color_depth
        ):
            self._last_screen = None
            self._attrs_for_style = None
            self._style_string_has_style = None

        if self._attrs_for_style is None:
            self._attrs_for_style = _StyleStringToAttrsCache(
                self.style.get_attrs_for_style_str, app.style_transformation
            )
        if self._style_string_has_style is None:
            self._style_string_has_style = _StyleStringHasStyleCache(
                self._attrs_for_style
            )

        self._last_style_hash = self.style.invalidation_hash()
        self._last_transformation_hash = app.style_transformation.invalidation_hash()
        self._last_color_depth = app.color_depth

        layout.container.write_to_screen(
            screen,
            mouse_handlers,
            WritePosition(xpos=0, ypos=0, width=size.columns, height=height),
            parent_style="",
            erase_bg=False,
            z_index=None,
        )
        screen.draw_all_floats()

        # When grayed. Replace all styles in the new screen.
        if app.exit_style:
            screen.append_style_to_content(app.exit_style)

        # Process diff and write to output.
        self._cursor_pos, self._last_style = _output_screen_diff(
            app,
            output,
            screen,
            self._cursor_pos,
            app.color_depth,
            self._last_screen,
            self._last_style,
            is_done,
            full_screen=self.full_screen,
            attrs_for_style_string=self._attrs_for_style,
            style_string_has_style=self._style_string_has_style,
            size=size,
            previous_width=(self._last_size.columns if self._last_size else 0),
        )
        self._last_screen = screen
        self._last_size = size
        self.mouse_handlers = mouse_handlers

        # Handle cursor shapes.
        new_cursor_shape = app.cursor.get_cursor_shape(app)
        if (
            self._last_cursor_shape is None
            or self._last_cursor_shape != new_cursor_shape
        ):
            output.set_cursor_shape(new_cursor_shape)
            self._last_cursor_shape = new_cursor_shape

        # Flush buffered output.
        output.flush()

        # Set visible windows in layout.
        app.layout.visible_windows = screen.visible_windows

        if is_done:
            self.reset()

    def erase(self, leave_alternate_screen: bool = True) -> None:
        """
        Hide all output and put the cursor back at the first line. This is for
        instance used for running a system command (while hiding the CLI) and
        later resuming the same CLI.)

        :param leave_alternate_screen: When True, and when inside an alternate
            screen buffer, quit the alternate screen.
        """
        output = self.output

        output.cursor_backward(self._cursor_pos.x)
        output.cursor_up(self._cursor_pos.y)
        output.erase_down()
        output.reset_attributes()
        output.enable_autowrap()

        output.flush()

        self.reset(leave_alternate_screen=leave_alternate_screen)

    def clear(self) -> None:
        """
        Clear screen and go to 0,0
        """
        # Erase current output first.
        self.erase()

        # Send "Erase Screen" command and go to (0, 0).
        output = self.output

        output.erase_screen()
        output.cursor_goto(0, 0)
        output.flush()

        self.request_absolute_cursor_position()


def print_formatted_text(
    output: Output,
    formatted_text: AnyFormattedText,
    style: BaseStyle,
    style_transformation: StyleTransformation | None = None,
    color_depth: ColorDepth | None = None,
) -> None:
    """
    Print a list of (style_str, text) tuples in the given style to the output.
    """
    fragments = to_formatted_text(formatted_text)
    style_transformation = style_transformation or DummyStyleTransformation()
    color_depth = color_depth or output.get_default_color_depth()

    # Reset first.
    output.reset_attributes()
    output.enable_autowrap()
    last_attrs: Attrs | None = None

    # Print all (style_str, text) tuples.
    attrs_for_style_string = _StyleStringToAttrsCache(
        style.get_attrs_for_style_str, style_transformation
    )

    for style_str, text, *_ in fragments:
        attrs = attrs_for_style_string[style_str]

        # Set style attributes if something changed.
        if attrs != last_attrs:
            if attrs:
                output.set_attributes(attrs, color_depth)
            else:
                output.reset_attributes()
        last_attrs = attrs

        # Print escape sequences as raw output
        if "[ZeroWidthEscape]" in style_str:
            output.write_raw(text)
        else:
            # Eliminate carriage returns
            text = text.replace("\r", "")
            # Insert a carriage return before every newline (important when the
            # front-end is a telnet client).
            text = text.replace("\n", "\r\n")
            output.write(text)

    # Reset again.
    output.reset_attributes()
    output.flush()

# === NexusCore/openenv\Lib\site-packages\litellm\caching\caching.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import ast
import hashlib
import json
import time
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

import litellm
from litellm._logging import verbose_logger
from litellm.constants import CACHED_STREAMING_CHUNK_DELAY
from litellm.litellm_core_utils.model_param_helper import ModelParamHelper
from litellm.types.caching import *
from litellm.types.utils import EmbeddingResponse, all_litellm_params

from .base_cache import BaseCache
from .disk_cache import DiskCache
from .dual_cache import DualCache  # noqa
from .in_memory_cache import InMemoryCache
from .qdrant_semantic_cache import QdrantSemanticCache
from .redis_cache import RedisCache
from .redis_cluster_cache import RedisClusterCache
from .redis_semantic_cache import RedisSemanticCache
from .s3_cache import S3Cache


def print_verbose(print_statement):
    try:
        verbose_logger.debug(print_statement)
        if litellm.set_verbose:
            print(print_statement)  # noqa
    except Exception:
        pass


class CacheMode(str, Enum):
    default_on = "default_on"
    default_off = "default_off"


#### LiteLLM.Completion / Embedding Cache ####
class Cache:
    def __init__(
        self,
        type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
        mode: Optional[
            CacheMode
        ] = CacheMode.default_on,  # when default_on cache is always on, when default_off cache is opt in
        host: Optional[str] = None,
        port: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        ttl: Optional[float] = None,
        default_in_memory_ttl: Optional[float] = None,
        default_in_redis_ttl: Optional[float] = None,
        similarity_threshold: Optional[float] = None,
        supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
            "completion",
            "acompletion",
            "embedding",
            "aembedding",
            "atranscription",
            "transcription",
            "atext_completion",
            "text_completion",
            "arerank",
            "rerank",
        ],
        # s3 Bucket, boto3 configuration
        s3_bucket_name: Optional[str] = None,
        s3_region_name: Optional[str] = None,
        s3_api_version: Optional[str] = None,
        s3_use_ssl: Optional[bool] = True,
        s3_verify: Optional[Union[bool, str]] = None,
        s3_endpoint_url: Optional[str] = None,
        s3_aws_access_key_id: Optional[str] = None,
        s3_aws_secret_access_key: Optional[str] = None,
        s3_aws_session_token: Optional[str] = None,
        s3_config: Optional[Any] = None,
        s3_path: Optional[str] = None,
        redis_semantic_cache_embedding_model: str = "text-embedding-ada-002",
        redis_semantic_cache_index_name: Optional[str] = None,
        redis_flush_size: Optional[int] = None,
        redis_startup_nodes: Optional[List] = None,
        disk_cache_dir: Optional[str] = None,
        qdrant_api_base: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        qdrant_collection_name: Optional[str] = None,
        qdrant_quantization_config: Optional[str] = None,
        qdrant_semantic_cache_embedding_model: str = "text-embedding-ada-002",
        **kwargs,
    ):
        """
        Initializes the cache based on the given type.

        Args:
            type (str, optional): The type of cache to initialize. Can be "local", "redis", "redis-semantic", "qdrant-semantic", "s3" or "disk". Defaults to "local".

            # Redis Cache Args
            host (str, optional): The host address for the Redis cache. Required if type is "redis".
            port (int, optional): The port number for the Redis cache. Required if type is "redis".
            password (str, optional): The password for the Redis cache. Required if type is "redis".
            namespace (str, optional): The namespace for the Redis cache. Required if type is "redis".
            ttl (float, optional): The ttl for the Redis cache
            redis_flush_size (int, optional): The number of keys to flush at a time. Defaults to 1000. Only used if batch redis set caching is used.
            redis_startup_nodes (list, optional): The list of startup nodes for the Redis cache. Defaults to None.

            # Qdrant Cache Args
            qdrant_api_base (str, optional): The url for your qdrant cluster. Required if type is "qdrant-semantic".
            qdrant_api_key (str, optional): The api_key for the local or cloud qdrant cluster.
            qdrant_collection_name (str, optional): The name for your qdrant collection. Required if type is "qdrant-semantic".
            similarity_threshold (float, optional): The similarity threshold for semantic-caching, Required if type is "redis-semantic" or "qdrant-semantic".

            # Disk Cache Args
            disk_cache_dir (str, optional): The directory for the disk cache. Defaults to None.

            # S3 Cache Args
            s3_bucket_name (str, optional): The bucket name for the s3 cache. Defaults to None.
            s3_region_name (str, optional): The region name for the s3 cache. Defaults to None.
            s3_api_version (str, optional): The api version for the s3 cache. Defaults to None.
            s3_use_ssl (bool, optional): The use ssl for the s3 cache. Defaults to True.
            s3_verify (bool, optional): The verify for the s3 cache. Defaults to None.
            s3_endpoint_url (str, optional): The endpoint url for the s3 cache. Defaults to None.
            s3_aws_access_key_id (str, optional): The aws access key id for the s3 cache. Defaults to None.
            s3_aws_secret_access_key (str, optional): The aws secret access key for the s3 cache. Defaults to None.
            s3_aws_session_token (str, optional): The aws session token for the s3 cache. Defaults to None.
            s3_config (dict, optional): The config for the s3 cache. Defaults to None.

            # Common Cache Args
            supported_call_types (list, optional): List of call types to cache for. Defaults to cache == on for all call types.
            **kwargs: Additional keyword arguments for redis.Redis() cache

        Raises:
            ValueError: If an invalid cache type is provided.

        Returns:
            None. Cache is set as a litellm param
        """
        if type == LiteLLMCacheType.REDIS:
            if redis_startup_nodes:
                self.cache: BaseCache = RedisClusterCache(
                    host=host,
                    port=port,
                    password=password,
                    redis_flush_size=redis_flush_size,
                    startup_nodes=redis_startup_nodes,
                    **kwargs,
                )
            else:
                self.cache = RedisCache(
                    host=host,
                    port=port,
                    password=password,
                    redis_flush_size=redis_flush_size,
                    **kwargs,
                )
        elif type == LiteLLMCacheType.REDIS_SEMANTIC:
            self.cache = RedisSemanticCache(
                host=host,
                port=port,
                password=password,
                similarity_threshold=similarity_threshold,
                embedding_model=redis_semantic_cache_embedding_model,
                index_name=redis_semantic_cache_index_name,
                **kwargs,
            )
        elif type == LiteLLMCacheType.QDRANT_SEMANTIC:
            self.cache = QdrantSemanticCache(
                qdrant_api_base=qdrant_api_base,
                qdrant_api_key=qdrant_api_key,
                collection_name=qdrant_collection_name,
                similarity_threshold=similarity_threshold,
                quantization_config=qdrant_quantization_config,
                embedding_model=qdrant_semantic_cache_embedding_model,
            )
        elif type == LiteLLMCacheType.LOCAL:
            self.cache = InMemoryCache()
        elif type == LiteLLMCacheType.S3:
            self.cache = S3Cache(
                s3_bucket_name=s3_bucket_name,
                s3_region_name=s3_region_name,
                s3_api_version=s3_api_version,
                s3_use_ssl=s3_use_ssl,
                s3_verify=s3_verify,
                s3_endpoint_url=s3_endpoint_url,
                s3_aws_access_key_id=s3_aws_access_key_id,
                s3_aws_secret_access_key=s3_aws_secret_access_key,
                s3_aws_session_token=s3_aws_session_token,
                s3_config=s3_config,
                s3_path=s3_path,
                **kwargs,
            )
        elif type == LiteLLMCacheType.DISK:
            self.cache = DiskCache(disk_cache_dir=disk_cache_dir)
        if "cache" not in litellm.input_callback:
            litellm.input_callback.append("cache")
        if "cache" not in litellm.success_callback:
            litellm.logging_callback_manager.add_litellm_success_callback("cache")
        if "cache" not in litellm._async_success_callback:
            litellm.logging_callback_manager.add_litellm_async_success_callback("cache")
        self.supported_call_types = supported_call_types  # default to ["completion", "acompletion", "embedding", "aembedding"]
        self.type = type
        self.namespace = namespace
        self.redis_flush_size = redis_flush_size
        self.ttl = ttl
        self.mode: CacheMode = mode or CacheMode.default_on

        if self.type == LiteLLMCacheType.LOCAL and default_in_memory_ttl is not None:
            self.ttl = default_in_memory_ttl

        if (
            self.type == LiteLLMCacheType.REDIS
            or self.type == LiteLLMCacheType.REDIS_SEMANTIC
        ) and default_in_redis_ttl is not None:
            self.ttl = default_in_redis_ttl

        if self.namespace is not None and isinstance(self.cache, RedisCache):
            self.cache.namespace = self.namespace

    def get_cache_key(self, **kwargs) -> str:
        """
        Get the cache key for the given arguments.

        Args:
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            str: The cache key generated from the arguments, or None if no cache key could be generated.
        """
        cache_key = ""
        # verbose_logger.debug("\nGetting Cache key. Kwargs: %s", kwargs)

        preset_cache_key = self._get_preset_cache_key_from_kwargs(**kwargs)
        if preset_cache_key is not None:
            verbose_logger.debug("\nReturning preset cache key: %s", preset_cache_key)
            return preset_cache_key

        combined_kwargs = ModelParamHelper._get_all_llm_api_params()
        litellm_param_kwargs = all_litellm_params
        for param in kwargs:
            if param in combined_kwargs:
                param_value: Optional[str] = self._get_param_value(param, kwargs)
                if param_value is not None:
                    cache_key += f"{str(param)}: {str(param_value)}"
            elif (
                param not in litellm_param_kwargs
            ):  # check if user passed in optional param - e.g. top_k
                if (
                    litellm.enable_caching_on_provider_specific_optional_params is True
                ):  # feature flagged for now
                    if kwargs[param] is None:
                        continue  # ignore None params
                    param_value = kwargs[param]
                    cache_key += f"{str(param)}: {str(param_value)}"

        verbose_logger.debug("\nCreated cache key: %s", cache_key)
        hashed_cache_key = Cache._get_hashed_cache_key(cache_key)
        hashed_cache_key = self._add_namespace_to_cache_key(hashed_cache_key, **kwargs)
        self._set_preset_cache_key_in_kwargs(
            preset_cache_key=hashed_cache_key, **kwargs
        )
        return hashed_cache_key

    def _get_param_value(
        self,
        param: str,
        kwargs: dict,
    ) -> Optional[str]:
        """
        Get the value for the given param from kwargs
        """
        if param == "model":
            return self._get_model_param_value(kwargs)
        elif param == "file":
            return self._get_file_param_value(kwargs)
        return kwargs[param]

    def _get_model_param_value(self, kwargs: dict) -> str:
        """
        Handles getting the value for the 'model' param from kwargs

        1. If caching groups are set, then return the caching group as the model https://docs.litellm.ai/docs/routing#caching-across-model-groups
        2. Else if a model_group is set, then return the model_group as the model. This is used for all requests sent through the litellm.Router()
        3. Else use the `model` passed in kwargs
        """
        metadata: Dict = kwargs.get("metadata", {}) or {}
        litellm_params: Dict = kwargs.get("litellm_params", {}) or {}
        metadata_in_litellm_params: Dict = litellm_params.get("metadata", {}) or {}
        model_group: Optional[str] = metadata.get(
            "model_group"
        ) or metadata_in_litellm_params.get("model_group")
        caching_group = self._get_caching_group(metadata, model_group)
        return caching_group or model_group or kwargs["model"]

    def _get_caching_group(
        self, metadata: dict, model_group: Optional[str]
    ) -> Optional[str]:
        caching_groups: Optional[List] = metadata.get("caching_groups", [])
        if caching_groups:
            for group in caching_groups:
                if model_group in group:
                    return str(group)
        return None

    def _get_file_param_value(self, kwargs: dict) -> str:
        """
        Handles getting the value for the 'file' param from kwargs. Used for `transcription` requests
        """
        file = kwargs.get("file")
        metadata = kwargs.get("metadata", {})
        litellm_params = kwargs.get("litellm_params", {})
        return (
            metadata.get("file_checksum")
            or getattr(file, "name", None)
            or metadata.get("file_name")
            or litellm_params.get("file_name")
        )

    def _get_preset_cache_key_from_kwargs(self, **kwargs) -> Optional[str]:
        """
        Get the preset cache key from kwargs["litellm_params"]

        We use _get_preset_cache_keys for two reasons

        1. optional params like max_tokens, get transformed for bedrock -> max_new_tokens
        2. avoid doing duplicate / repeated work
        """
        if kwargs:
            if "litellm_params" in kwargs:
                return kwargs["litellm_params"].get("preset_cache_key", None)
        return None

    def _set_preset_cache_key_in_kwargs(self, preset_cache_key: str, **kwargs) -> None:
        """
        Set the calculated cache key in kwargs

        This is used to avoid doing duplicate / repeated work

        Placed in kwargs["litellm_params"]
        """
        if kwargs:
            if "litellm_params" in kwargs:
                kwargs["litellm_params"]["preset_cache_key"] = preset_cache_key

    @staticmethod
    def _get_hashed_cache_key(cache_key: str) -> str:
        """
        Get the hashed cache key for the given cache key.

        Use hashlib to create a sha256 hash of the cache key

        Args:
            cache_key (str): The cache key to hash.

        Returns:
            str: The hashed cache key.
        """
        hash_object = hashlib.sha256(cache_key.encode())
        # Hexadecimal representation of the hash
        hash_hex = hash_object.hexdigest()
        verbose_logger.debug("Hashed cache key (SHA-256): %s", hash_hex)
        return hash_hex

    def _add_namespace_to_cache_key(self, hash_hex: str, **kwargs) -> str:
        """
        If a redis namespace is provided, add it to the cache key

        Args:
            hash_hex (str): The hashed cache key.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The final hashed cache key with the redis namespace.
        """
        dynamic_cache_control: DynamicCacheControl = kwargs.get("cache", {})
        namespace = (
            dynamic_cache_control.get("namespace")
            or kwargs.get("metadata", {}).get("redis_namespace")
            or self.namespace
        )
        if namespace:
            hash_hex = f"{namespace}:{hash_hex}"
        verbose_logger.debug("Final hashed key: %s", hash_hex)
        return hash_hex

    def generate_streaming_content(self, content):
        chunk_size = 5  # Adjust the chunk size as needed
        for i in range(0, len(content), chunk_size):
            yield {
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": content[i : i + chunk_size],
                        }
                    }
                ]
            }
            time.sleep(CACHED_STREAMING_CHUNK_DELAY)

    def _get_cache_logic(
        self,
        cached_result: Optional[Any],
        max_age: Optional[float],
    ):
        """
        Common get cache logic across sync + async implementations
        """
        # Check if a timestamp was stored with the cached response
        if (
            cached_result is not None
            and isinstance(cached_result, dict)
            and "timestamp" in cached_result
        ):
            timestamp = cached_result["timestamp"]
            current_time = time.time()

            # Calculate age of the cached response
            response_age = current_time - timestamp

            # Check if the cached response is older than the max-age
            if max_age is not None and response_age > max_age:
                return None  # Cached response is too old

            # If the response is fresh, or there's no max-age requirement, return the cached response
            # cached_response is in `b{} convert it to ModelResponse
            cached_response = cached_result.get("response")
            try:
                if isinstance(cached_response, dict):
                    pass
                else:
                    cached_response = json.loads(
                        cached_response  # type: ignore
                    )  # Convert string to dictionary
            except Exception:
                cached_response = ast.literal_eval(cached_response)  # type: ignore
            return cached_response
        return cached_result

    def get_cache(self, **kwargs):
        """
        Retrieves the cached result for the given arguments.

        Args:
            *args: args to litellm.completion() or embedding()
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            The cached result if it exists, otherwise None.
        """
        try:  # never block execution
            if self.should_use_cache(**kwargs) is not True:
                return
            messages = kwargs.get("messages", [])
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(**kwargs)
            if cache_key is not None:
                cache_control_args: DynamicCacheControl = kwargs.get("cache", {})
                max_age = (
                    cache_control_args.get("s-maxage")
                    or cache_control_args.get("s-max-age")
                    or float("inf")
                )
                cached_result = self.cache.get_cache(cache_key, messages=messages)
                cached_result = self.cache.get_cache(cache_key, messages=messages)
                return self._get_cache_logic(
                    cached_result=cached_result, max_age=max_age
                )
        except Exception:
            print_verbose(f"An exception occurred: {traceback.format_exc()}")
            return None

    async def async_get_cache(self, **kwargs):
        """
        Async get cache implementation.

        Used for embedding calls in async wrapper
        """

        try:  # never block execution
            if self.should_use_cache(**kwargs) is not True:
                return

            kwargs.get("messages", [])
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(**kwargs)
            if cache_key is not None:
                cache_control_args = kwargs.get("cache", {})
                max_age = cache_control_args.get(
                    "s-max-age", cache_control_args.get("s-maxage", float("inf"))
                )
                cached_result = await self.cache.async_get_cache(cache_key, **kwargs)
                return self._get_cache_logic(
                    cached_result=cached_result, max_age=max_age
                )
        except Exception:
            print_verbose(f"An exception occurred: {traceback.format_exc()}")
            return None

    def _add_cache_logic(self, result, **kwargs):
        """
        Common implementation across sync + async add_cache functions
        """
        try:
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(**kwargs)
            if cache_key is not None:
                if isinstance(result, BaseModel):
                    result = result.model_dump_json()

                ## DEFAULT TTL ##
                if self.ttl is not None:
                    kwargs["ttl"] = self.ttl
                ## Get Cache-Controls ##
                _cache_kwargs = kwargs.get("cache", None)
                if isinstance(_cache_kwargs, dict):
                    for k, v in _cache_kwargs.items():
                        if k == "ttl":
                            kwargs["ttl"] = v

                cached_data = {"timestamp": time.time(), "response": result}
                return cache_key, cached_data, kwargs
            else:
                raise Exception("cache key is None")
        except Exception as e:
            raise e

    def add_cache(self, result, **kwargs):
        """
        Adds a result to the cache.

        Args:
            *args: args to litellm.completion() or embedding()
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            None
        """
        try:
            if self.should_use_cache(**kwargs) is not True:
                return
            cache_key, cached_data, kwargs = self._add_cache_logic(
                result=result, **kwargs
            )
            self.cache.set_cache(cache_key, cached_data, **kwargs)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    async def async_add_cache(self, result, **kwargs):
        """
        Async implementation of add_cache
        """
        try:
            if self.should_use_cache(**kwargs) is not True:
                return
            if self.type == "redis" and self.redis_flush_size is not None:
                # high traffic - fill in results in memory and then flush
                await self.batch_cache_write(result, **kwargs)
            else:
                cache_key, cached_data, kwargs = self._add_cache_logic(
                    result=result, **kwargs
                )

                await self.cache.async_set_cache(cache_key, cached_data, **kwargs)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    def add_embedding_response_to_cache(
        self,
        result: EmbeddingResponse,
        input: str,
        kwargs: dict,
        idx_in_result_data: int = 0,
    ) -> Tuple[str, dict, dict]:
        preset_cache_key = self.get_cache_key(**{**kwargs, "input": input})
        kwargs["cache_key"] = preset_cache_key
        embedding_response = result.data[idx_in_result_data]
        cache_key, cached_data, kwargs = self._add_cache_logic(
            result=embedding_response,
            **kwargs,
        )
        return cache_key, cached_data, kwargs

    async def async_add_cache_pipeline(self, result, **kwargs):
        """
        Async implementation of add_cache for Embedding calls

        Does a bulk write, to prevent using too many clients
        """
        try:
            if self.should_use_cache(**kwargs) is not True:
                return

            # set default ttl if not set
            if self.ttl is not None:
                kwargs["ttl"] = self.ttl

            cache_list = []
            if isinstance(kwargs["input"], list):
                for idx, i in enumerate(kwargs["input"]):
                    (
                        cache_key,
                        cached_data,
                        kwargs,
                    ) = self.add_embedding_response_to_cache(result, i, kwargs, idx)
                    cache_list.append((cache_key, cached_data))
            elif isinstance(kwargs["input"], str):
                cache_key, cached_data, kwargs = self.add_embedding_response_to_cache(
                    result, kwargs["input"], kwargs
                )
                cache_list.append((cache_key, cached_data))

            await self.cache.async_set_cache_pipeline(cache_list=cache_list, **kwargs)
            # if async_set_cache_pipeline:
            #     await async_set_cache_pipeline(cache_list=cache_list, **kwargs)
            # else:
            #     tasks = []
            #     for val in cache_list:
            #         tasks.append(self.cache.async_set_cache(val[0], val[1], **kwargs))
            #     await asyncio.gather(*tasks)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    def should_use_cache(self, **kwargs):
        """
        Returns true if we should use the cache for LLM API calls

        If cache is default_on then this is True
        If cache is default_off then this is only true when user has opted in to use cache
        """
        if self.mode == CacheMode.default_on:
            return True

        # when mode == default_off -> Cache is opt in only
        _cache = kwargs.get("cache", None)
        verbose_logger.debug("should_use_cache: kwargs: %s; _cache: %s", kwargs, _cache)
        if _cache and isinstance(_cache, dict):
            if _cache.get("use-cache", False) is True:
                return True
        return False

    async def batch_cache_write(self, result, **kwargs):
        cache_key, cached_data, kwargs = self._add_cache_logic(result=result, **kwargs)
        await self.cache.batch_cache_write(cache_key, cached_data, **kwargs)

    async def ping(self):
        cache_ping = getattr(self.cache, "ping")
        if cache_ping:
            return await cache_ping()
        return None

    async def delete_cache_keys(self, keys):
        cache_delete_cache_keys = getattr(self.cache, "delete_cache_keys")
        if cache_delete_cache_keys:
            return await cache_delete_cache_keys(keys)
        return None

    async def disconnect(self):
        if hasattr(self.cache, "disconnect"):
            await self.cache.disconnect()

    def _supports_async(self) -> bool:
        """
        Internal method to check if the cache type supports async get/set operations

        Only S3 Cache Does NOT support async operations

        """
        if self.type and self.type == LiteLLMCacheType.S3:
            return False
        return True


def enable_cache(
    type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
    host: Optional[str] = None,
    port: Optional[str] = None,
    password: Optional[str] = None,
    supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
        "completion",
        "acompletion",
        "embedding",
        "aembedding",
        "atranscription",
        "transcription",
        "atext_completion",
        "text_completion",
        "arerank",
        "rerank",
    ],
    **kwargs,
):
    """
    Enable cache with the specified configuration.

    Args:
        type (Optional[Literal["local", "redis", "s3", "disk"]]): The type of cache to enable. Defaults to "local".
        host (Optional[str]): The host address of the cache server. Defaults to None.
        port (Optional[str]): The port number of the cache server. Defaults to None.
        password (Optional[str]): The password for the cache server. Defaults to None.
        supported_call_types (Optional[List[Literal["completion", "acompletion", "embedding", "aembedding"]]]):
            The supported call types for the cache. Defaults to ["completion", "acompletion", "embedding", "aembedding"].
        **kwargs: Additional keyword arguments.

    Returns:
        None

    Raises:
        None
    """
    print_verbose("LiteLLM: Enabling Cache")
    if "cache" not in litellm.input_callback:
        litellm.input_callback.append("cache")
    if "cache" not in litellm.success_callback:
        litellm.logging_callback_manager.add_litellm_success_callback("cache")
    if "cache" not in litellm._async_success_callback:
        litellm.logging_callback_manager.add_litellm_async_success_callback("cache")

    if litellm.cache is None:
        litellm.cache = Cache(
            type=type,
            host=host,
            port=port,
            password=password,
            supported_call_types=supported_call_types,
            **kwargs,
        )
    print_verbose(f"LiteLLM: Cache enabled, litellm.cache={litellm.cache}")
    print_verbose(f"LiteLLM Cache: {vars(litellm.cache)}")


def update_cache(
    type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
    host: Optional[str] = None,
    port: Optional[str] = None,
    password: Optional[str] = None,
    supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
        "completion",
        "acompletion",
        "embedding",
        "aembedding",
        "atranscription",
        "transcription",
        "atext_completion",
        "text_completion",
        "arerank",
        "rerank",
    ],
    **kwargs,
):
    """
    Update the cache for LiteLLM.

    Args:
        type (Optional[Literal["local", "redis", "s3", "disk"]]): The type of cache. Defaults to "local".
        host (Optional[str]): The host of the cache. Defaults to None.
        port (Optional[str]): The port of the cache. Defaults to None.
        password (Optional[str]): The password for the cache. Defaults to None.
        supported_call_types (Optional[List[Literal["completion", "acompletion", "embedding", "aembedding"]]]):
            The supported call types for the cache. Defaults to ["completion", "acompletion", "embedding", "aembedding"].
        **kwargs: Additional keyword arguments for the cache.

    Returns:
        None

    """
    print_verbose("LiteLLM: Updating Cache")
    litellm.cache = Cache(
        type=type,
        host=host,
        port=port,
        password=password,
        supported_call_types=supported_call_types,
        **kwargs,
    )
    print_verbose(f"LiteLLM: Cache Updated, litellm.cache={litellm.cache}")
    print_verbose(f"LiteLLM Cache: {vars(litellm.cache)}")


def disable_cache():
    """
    Disable the cache used by LiteLLM.

    This function disables the cache used by the LiteLLM module. It removes the cache-related callbacks from the input_callback, success_callback, and _async_success_callback lists. It also sets the litellm.cache attribute to None.

    Parameters:
    None

    Returns:
    None
    """
    from contextlib import suppress

    print_verbose("LiteLLM: Disabling Cache")
    with suppress(ValueError):
        litellm.input_callback.remove("cache")
        litellm.success_callback.remove("cache")
        litellm._async_success_callback.remove("cache")

    litellm.cache = None
    print_verbose(f"LiteLLM: Cache disabled, litellm.cache={litellm.cache}")

# === NexusCore/openenv\Lib\site-packages\pyparsing\results.py ===
# results.py
from __future__ import annotations

import collections
from collections.abc import (
    MutableMapping,
    Mapping,
    MutableSequence,
    Iterator,
    Iterable,
)
import pprint
from typing import Any

from .util import replaced_by_pep8


str_type: tuple[type, ...] = (str, bytes)
_generator_type = type((_ for _ in ()))


class _ParseResultsWithOffset:
    tup: tuple[ParseResults, int]
    __slots__ = ["tup"]

    def __init__(self, p1: ParseResults, p2: int) -> None:
        self.tup: tuple[ParseResults, int] = (p1, p2)

    def __getitem__(self, i):
        return self.tup[i]

    def __getstate__(self):
        return self.tup

    def __setstate__(self, *args):
        self.tup = args[0]


class ParseResults:
    """Structured parse results, to provide multiple means of access to
    the parsed data:

    - as a list (``len(results)``)
    - by list index (``results[0], results[1]``, etc.)
    - by attribute (``results.<results_name>`` - see :class:`ParserElement.set_results_name`)

    Example::

        integer = Word(nums)
        date_str = (integer.set_results_name("year") + '/'
                    + integer.set_results_name("month") + '/'
                    + integer.set_results_name("day"))
        # equivalent form:
        # date_str = (integer("year") + '/'
        #             + integer("month") + '/'
        #             + integer("day"))

        # parse_string returns a ParseResults object
        result = date_str.parse_string("1999/12/31")

        def test(s, fn=repr):
            print(f"{s} -> {fn(eval(s))}")
        test("list(result)")
        test("result[0]")
        test("result['month']")
        test("result.day")
        test("'month' in result")
        test("'minutes' in result")
        test("result.dump()", str)

    prints::

        list(result) -> ['1999', '/', '12', '/', '31']
        result[0] -> '1999'
        result['month'] -> '12'
        result.day -> '31'
        'month' in result -> True
        'minutes' in result -> False
        result.dump() -> ['1999', '/', '12', '/', '31']
        - day: '31'
        - month: '12'
        - year: '1999'
    """

    _null_values: tuple[Any, ...] = (None, [], ())

    _name: str
    _parent: ParseResults
    _all_names: set[str]
    _modal: bool
    _toklist: list[Any]
    _tokdict: dict[str, Any]

    __slots__ = (
        "_name",
        "_parent",
        "_all_names",
        "_modal",
        "_toklist",
        "_tokdict",
    )

    class List(list):
        """
        Simple wrapper class to distinguish parsed list results that should be preserved
        as actual Python lists, instead of being converted to :class:`ParseResults`::

            LBRACK, RBRACK = map(pp.Suppress, "[]")
            element = pp.Forward()
            item = ppc.integer
            element_list = LBRACK + pp.DelimitedList(element) + RBRACK

            # add parse actions to convert from ParseResults to actual Python collection types
            def as_python_list(t):
                return pp.ParseResults.List(t.as_list())
            element_list.add_parse_action(as_python_list)

            element <<= item | element_list

            element.run_tests('''
                100
                [2,3,4]
                [[2, 1],3,4]
                [(2, 1),3,4]
                (2,3,4)
                ''', post_parse=lambda s, r: (r[0], type(r[0])))

        prints::

            100
            (100, <class 'int'>)

            [2,3,4]
            ([2, 3, 4], <class 'list'>)

            [[2, 1],3,4]
            ([[2, 1], 3, 4], <class 'list'>)

        (Used internally by :class:`Group` when `aslist=True`.)
        """

        def __new__(cls, contained=None):
            if contained is None:
                contained = []

            if not isinstance(contained, list):
                raise TypeError(
                    f"{cls.__name__} may only be constructed with a list, not {type(contained).__name__}"
                )

            return list.__new__(cls)

    def __new__(cls, toklist=None, name=None, **kwargs):
        if isinstance(toklist, ParseResults):
            return toklist
        self = object.__new__(cls)
        self._name = None
        self._parent = None
        self._all_names = set()

        if toklist is None:
            self._toklist = []
        elif isinstance(toklist, (list, _generator_type)):
            self._toklist = (
                [toklist[:]]
                if isinstance(toklist, ParseResults.List)
                else list(toklist)
            )
        else:
            self._toklist = [toklist]
        self._tokdict = dict()
        return self

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__(
        self, toklist=None, name=None, asList=True, modal=True, isinstance=isinstance
    ) -> None:
        self._tokdict: dict[str, _ParseResultsWithOffset]
        self._modal = modal

        if name is None or name == "":
            return

        if isinstance(name, int):
            name = str(name)

        if not modal:
            self._all_names = {name}

        self._name = name

        if toklist in self._null_values:
            return

        if isinstance(toklist, (str_type, type)):
            toklist = [toklist]

        if asList:
            if isinstance(toklist, ParseResults):
                self[name] = _ParseResultsWithOffset(ParseResults(toklist._toklist), 0)
            else:
                self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]), 0)
            self[name]._name = name
            return

        try:
            self[name] = toklist[0]
        except (KeyError, TypeError, IndexError):
            if toklist is not self:
                self[name] = toklist
            else:
                self._name = name

    def __getitem__(self, i):
        if isinstance(i, (int, slice)):
            return self._toklist[i]

        if i not in self._all_names:
            return self._tokdict[i][-1][0]

        return ParseResults([v[0] for v in self._tokdict[i]])

    def __setitem__(self, k, v, isinstance=isinstance):
        if isinstance(v, _ParseResultsWithOffset):
            self._tokdict[k] = self._tokdict.get(k, list()) + [v]
            sub = v[0]
        elif isinstance(k, (int, slice)):
            self._toklist[k] = v
            sub = v
        else:
            self._tokdict[k] = self._tokdict.get(k, []) + [
                _ParseResultsWithOffset(v, 0)
            ]
            sub = v
        if isinstance(sub, ParseResults):
            sub._parent = self

    def __delitem__(self, i):
        if not isinstance(i, (int, slice)):
            del self._tokdict[i]
            return

        mylen = len(self._toklist)
        del self._toklist[i]

        # convert int to slice
        if isinstance(i, int):
            if i < 0:
                i += mylen
            i = slice(i, i + 1)
        # get removed indices
        removed = list(range(*i.indices(mylen)))
        removed.reverse()
        # fixup indices in token dictionary
        for occurrences in self._tokdict.values():
            for j in removed:
                for k, (value, position) in enumerate(occurrences):
                    occurrences[k] = _ParseResultsWithOffset(
                        value, position - (position > j)
                    )

    def __contains__(self, k) -> bool:
        return k in self._tokdict

    def __len__(self) -> int:
        return len(self._toklist)

    def __bool__(self) -> bool:
        return not not (self._toklist or self._tokdict)

    def __iter__(self) -> Iterator:
        return iter(self._toklist)

    def __reversed__(self) -> Iterator:
        return iter(self._toklist[::-1])

    def keys(self):
        return iter(self._tokdict)

    def values(self):
        return (self[k] for k in self.keys())

    def items(self):
        return ((k, self[k]) for k in self.keys())

    def haskeys(self) -> bool:
        """
        Since ``keys()`` returns an iterator, this method is helpful in bypassing
        code that looks for the existence of any defined results names."""
        return not not self._tokdict

    def pop(self, *args, **kwargs):
        """
        Removes and returns item at specified index (default= ``last``).
        Supports both ``list`` and ``dict`` semantics for ``pop()``. If
        passed no argument or an integer argument, it will use ``list``
        semantics and pop tokens from the list of parsed tokens. If passed
        a non-integer argument (most likely a string), it will use ``dict``
        semantics and pop the corresponding value from any defined results
        names. A second default return value argument is supported, just as in
        ``dict.pop()``.

        Example::

            numlist = Word(nums)[...]
            print(numlist.parse_string("0 123 321")) # -> ['0', '123', '321']

            def remove_first(tokens):
                tokens.pop(0)
            numlist.add_parse_action(remove_first)
            print(numlist.parse_string("0 123 321")) # -> ['123', '321']

            label = Word(alphas)
            patt = label("LABEL") + Word(nums)[1, ...]
            print(patt.parse_string("AAB 123 321").dump())

            # Use pop() in a parse action to remove named result (note that corresponding value is not
            # removed from list form of results)
            def remove_LABEL(tokens):
                tokens.pop("LABEL")
                return tokens
            patt.add_parse_action(remove_LABEL)
            print(patt.parse_string("AAB 123 321").dump())

        prints::

            ['AAB', '123', '321']
            - LABEL: 'AAB'

            ['AAB', '123', '321']
        """
        if not args:
            args = [-1]
        for k, v in kwargs.items():
            if k == "default":
                args = (args[0], v)
            else:
                raise TypeError(f"pop() got an unexpected keyword argument {k!r}")
        if isinstance(args[0], int) or len(args) == 1 or args[0] in self:
            index = args[0]
            ret = self[index]
            del self[index]
            return ret
        else:
            defaultvalue = args[1]
            return defaultvalue

    def get(self, key, default_value=None):
        """
        Returns named result matching the given key, or if there is no
        such name, then returns the given ``default_value`` or ``None`` if no
        ``default_value`` is specified.

        Similar to ``dict.get()``.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parse_string("1999/12/31")
            print(result.get("year")) # -> '1999'
            print(result.get("hour", "not specified")) # -> 'not specified'
            print(result.get("hour")) # -> None
        """
        if key in self:
            return self[key]
        else:
            return default_value

    def insert(self, index, ins_string):
        """
        Inserts new element at location index in the list of parsed tokens.

        Similar to ``list.insert()``.

        Example::

            numlist = Word(nums)[...]
            print(numlist.parse_string("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to insert the parse location in the front of the parsed results
            def insert_locn(locn, tokens):
                tokens.insert(0, locn)
            numlist.add_parse_action(insert_locn)
            print(numlist.parse_string("0 123 321")) # -> [0, '0', '123', '321']
        """
        self._toklist.insert(index, ins_string)
        # fixup indices in token dictionary
        for occurrences in self._tokdict.values():
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(
                    value, position + (position > index)
                )

    def append(self, item):
        """
        Add single element to end of ``ParseResults`` list of elements.

        Example::

            numlist = Word(nums)[...]
            print(numlist.parse_string("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to compute the sum of the parsed integers, and add it to the end
            def append_sum(tokens):
                tokens.append(sum(map(int, tokens)))
            numlist.add_parse_action(append_sum)
            print(numlist.parse_string("0 123 321")) # -> ['0', '123', '321', 444]
        """
        self._toklist.append(item)

    def extend(self, itemseq):
        """
        Add sequence of elements to end of ``ParseResults`` list of elements.

        Example::

            patt = Word(alphas)[1, ...]

            # use a parse action to append the reverse of the matched strings, to make a palindrome
            def make_palindrome(tokens):
                tokens.extend(reversed([t[::-1] for t in tokens]))
                return ''.join(tokens)
            patt.add_parse_action(make_palindrome)
            print(patt.parse_string("lskdj sdlkjf lksd")) # -> 'lskdjsdlkjflksddsklfjkldsjdksl'
        """
        if isinstance(itemseq, ParseResults):
            self.__iadd__(itemseq)
        else:
            self._toklist.extend(itemseq)

    def clear(self):
        """
        Clear all elements and results names.
        """
        del self._toklist[:]
        self._tokdict.clear()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            if name.startswith("__"):
                raise AttributeError(name)
            return ""

    def __add__(self, other: ParseResults) -> ParseResults:
        ret = self.copy()
        ret += other
        return ret

    def __iadd__(self, other: ParseResults) -> ParseResults:
        if not other:
            return self

        if other._tokdict:
            offset = len(self._toklist)
            addoffset = lambda a: offset if a < 0 else a + offset
            otheritems = other._tokdict.items()
            otherdictitems = [
                (k, _ParseResultsWithOffset(v[0], addoffset(v[1])))
                for k, vlist in otheritems
                for v in vlist
            ]
            for k, v in otherdictitems:
                self[k] = v
                if isinstance(v[0], ParseResults):
                    v[0]._parent = self

        self._toklist += other._toklist
        self._all_names |= other._all_names
        return self

    def __radd__(self, other) -> ParseResults:
        if isinstance(other, int) and other == 0:
            # useful for merging many ParseResults using sum() builtin
            return self.copy()
        else:
            # this may raise a TypeError - so be it
            return other + self

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._toklist!r}, {self.as_dict()})"

    def __str__(self) -> str:
        return (
            "["
            + ", ".join(
                [
                    str(i) if isinstance(i, ParseResults) else repr(i)
                    for i in self._toklist
                ]
            )
            + "]"
        )

    def _asStringList(self, sep=""):
        out = []
        for item in self._toklist:
            if out and sep:
                out.append(sep)
            if isinstance(item, ParseResults):
                out += item._asStringList()
            else:
                out.append(str(item))
        return out

    def as_list(self, *, flatten: bool = False) -> list:
        """
        Returns the parse results as a nested list of matching tokens, all converted to strings.
        If flatten is True, all the nesting levels in the returned list are collapsed.

        Example::

            patt = Word(alphas)[1, ...]
            result = patt.parse_string("sldkj lsdkj sldkj")
            # even though the result prints in string-like form, it is actually a pyparsing ParseResults
            print(type(result), result) # -> <class 'pyparsing.ParseResults'> ['sldkj', 'lsdkj', 'sldkj']

            # Use as_list() to create an actual list
            result_list = result.as_list()
            print(type(result_list), result_list) # -> <class 'list'> ['sldkj', 'lsdkj', 'sldkj']
        """

        def flattened(pr):
            to_visit = collections.deque([*self])
            while to_visit:
                to_do = to_visit.popleft()
                if isinstance(to_do, ParseResults):
                    to_visit.extendleft(to_do[::-1])
                else:
                    yield to_do

        if flatten:
            return [*flattened(self)]
        else:
            return [
                res.as_list() if isinstance(res, ParseResults) else res
                for res in self._toklist
            ]

    def as_dict(self) -> dict:
        """
        Returns the named parse results as a nested dictionary.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parse_string('12/31/1999')
            print(type(result), repr(result)) # -> <class 'pyparsing.ParseResults'> (['12', '/', '31', '/', '1999'], {'day': [('1999', 4)], 'year': [('12', 0)], 'month': [('31', 2)]})

            result_dict = result.as_dict()
            print(type(result_dict), repr(result_dict)) # -> <class 'dict'> {'day': '1999', 'year': '12', 'month': '31'}

            # even though a ParseResults supports dict-like access, sometime you just need to have a dict
            import json
            print(json.dumps(result)) # -> Exception: TypeError: ... is not JSON serializable
            print(json.dumps(result.as_dict())) # -> {"month": "31", "day": "1999", "year": "12"}
        """

        def to_item(obj):
            if isinstance(obj, ParseResults):
                return obj.as_dict() if obj.haskeys() else [to_item(v) for v in obj]
            else:
                return obj

        return dict((k, to_item(v)) for k, v in self.items())

    def copy(self) -> ParseResults:
        """
        Returns a new shallow copy of a :class:`ParseResults` object. `ParseResults`
        items contained within the source are shared with the copy. Use
        :class:`ParseResults.deepcopy()` to create a copy with its own separate
        content values.
        """
        ret = ParseResults(self._toklist)
        ret._tokdict = self._tokdict.copy()
        ret._parent = self._parent
        ret._all_names |= self._all_names
        ret._name = self._name
        return ret

    def deepcopy(self) -> ParseResults:
        """
        Returns a new deep copy of a :class:`ParseResults` object.
        """
        ret = self.copy()
        # replace values with copies if they are of known mutable types
        for i, obj in enumerate(self._toklist):
            if isinstance(obj, ParseResults):
                ret._toklist[i] = obj.deepcopy()
            elif isinstance(obj, (str, bytes)):
                pass
            elif isinstance(obj, MutableMapping):
                ret._toklist[i] = dest = type(obj)()
                for k, v in obj.items():
                    dest[k] = v.deepcopy() if isinstance(v, ParseResults) else v
            elif isinstance(obj, Iterable):
                ret._toklist[i] = type(obj)(
                    v.deepcopy() if isinstance(v, ParseResults) else v for v in obj  # type: ignore[call-arg]
                )
        return ret

    def get_name(self) -> str | None:
        r"""
        Returns the results name for this token expression. Useful when several
        different expressions might match at a particular location.

        Example::

            integer = Word(nums)
            ssn_expr = Regex(r"\d\d\d-\d\d-\d\d\d\d")
            house_number_expr = Suppress('#') + Word(nums, alphanums)
            user_data = (Group(house_number_expr)("house_number")
                        | Group(ssn_expr)("ssn")
                        | Group(integer)("age"))
            user_info = user_data[1, ...]

            result = user_info.parse_string("22 111-22-3333 #221B")
            for item in result:
                print(item.get_name(), ':', item[0])

        prints::

            age : 22
            ssn : 111-22-3333
            house_number : 221B
        """
        if self._name:
            return self._name
        elif self._parent:
            par: ParseResults = self._parent
            parent_tokdict_items = par._tokdict.items()
            return next(
                (
                    k
                    for k, vlist in parent_tokdict_items
                    for v, loc in vlist
                    if v is self
                ),
                None,
            )
        elif (
            len(self) == 1
            and len(self._tokdict) == 1
            and next(iter(self._tokdict.values()))[0][1] in (0, -1)
        ):
            return next(iter(self._tokdict.keys()))
        else:
            return None

    def dump(self, indent="", full=True, include_list=True, _depth=0) -> str:
        """
        Diagnostic method for listing out the contents of
        a :class:`ParseResults`. Accepts an optional ``indent`` argument so
        that this string can be embedded in a nested display of other data.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parse_string('1999/12/31')
            print(result.dump())

        prints::

            ['1999', '/', '12', '/', '31']
            - day: '31'
            - month: '12'
            - year: '1999'
        """
        out = []
        NL = "\n"
        out.append(indent + str(self.as_list()) if include_list else "")

        if not full:
            return "".join(out)

        if self.haskeys():
            items = sorted((str(k), v) for k, v in self.items())
            for k, v in items:
                if out:
                    out.append(NL)
                out.append(f"{indent}{('  ' * _depth)}- {k}: ")
                if not isinstance(v, ParseResults):
                    out.append(repr(v))
                    continue

                if not v:
                    out.append(str(v))
                    continue

                out.append(
                    v.dump(
                        indent=indent,
                        full=full,
                        include_list=include_list,
                        _depth=_depth + 1,
                    )
                )
        if not any(isinstance(vv, ParseResults) for vv in self):
            return "".join(out)

        v = self
        incr = "  "
        nl = "\n"
        for i, vv in enumerate(v):
            if isinstance(vv, ParseResults):
                vv_dump = vv.dump(
                    indent=indent,
                    full=full,
                    include_list=include_list,
                    _depth=_depth + 1,
                )
                out.append(
                    f"{nl}{indent}{incr * _depth}[{i}]:{nl}{indent}{incr * (_depth + 1)}{vv_dump}"
                )
            else:
                out.append(
                    f"{nl}{indent}{incr * _depth}[{i}]:{nl}{indent}{incr * (_depth + 1)}{vv}"
                )

        return "".join(out)

    def pprint(self, *args, **kwargs):
        """
        Pretty-printer for parsed results as a list, using the
        `pprint <https://docs.python.org/3/library/pprint.html>`_ module.
        Accepts additional positional or keyword args as defined for
        `pprint.pprint <https://docs.python.org/3/library/pprint.html#pprint.pprint>`_ .

        Example::

            ident = Word(alphas, alphanums)
            num = Word(nums)
            func = Forward()
            term = ident | num | Group('(' + func + ')')
            func <<= ident + Group(Optional(DelimitedList(term)))
            result = func.parse_string("fna a,b,(fnb c,d,200),100")
            result.pprint(width=40)

        prints::

            ['fna',
             ['a',
              'b',
              ['(', 'fnb', ['c', 'd', '200'], ')'],
              '100']]
        """
        pprint.pprint(self.as_list(), *args, **kwargs)

    # add support for pickle protocol
    def __getstate__(self):
        return (
            self._toklist,
            (
                self._tokdict.copy(),
                None,
                self._all_names,
                self._name,
            ),
        )

    def __setstate__(self, state):
        self._toklist, (self._tokdict, par, inAccumNames, self._name) = state
        self._all_names = set(inAccumNames)
        self._parent = None

    def __getnewargs__(self):
        return self._toklist, self._name

    def __dir__(self):
        return dir(type(self)) + list(self.keys())

    @classmethod
    def from_dict(cls, other, name=None) -> ParseResults:
        """
        Helper classmethod to construct a ``ParseResults`` from a ``dict``, preserving the
        name-value relations as results names. If an optional ``name`` argument is
        given, a nested ``ParseResults`` will be returned.
        """

        def is_iterable(obj):
            try:
                iter(obj)
            except Exception:
                return False
            # str's are iterable, but in pyparsing, we don't want to iterate over them
            else:
                return not isinstance(obj, str_type)

        ret = cls([])
        for k, v in other.items():
            if isinstance(v, Mapping):
                ret += cls.from_dict(v, name=k)
            else:
                ret += cls([v], name=k, asList=is_iterable(v))
        if name is not None:
            ret = cls([ret], name=name)
        return ret

    asList = as_list
    """Deprecated - use :class:`as_list`"""
    asDict = as_dict
    """Deprecated - use :class:`as_dict`"""
    getName = get_name
    """Deprecated - use :class:`get_name`"""


MutableMapping.register(ParseResults)
MutableSequence.register(ParseResults)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\context_amd64.py ===
#!/usr/bin/env python
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
CONTEXT structure for amd64.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.version import ARCH_AMD64
from winappdbg.win32 import context_i386

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- CONTEXT structures and constants -----------------------------------------

# The following values specify the type of access in the first parameter
# of the exception record when the exception code specifies an access
# violation.
EXCEPTION_READ_FAULT = 0  # exception caused by a read
EXCEPTION_WRITE_FAULT = 1  # exception caused by a write
EXCEPTION_EXECUTE_FAULT = 8  # exception caused by an instruction fetch

CONTEXT_AMD64 = 0x00100000

CONTEXT_CONTROL = CONTEXT_AMD64 | long(0x1)
CONTEXT_INTEGER = CONTEXT_AMD64 | long(0x2)
CONTEXT_SEGMENTS = CONTEXT_AMD64 | long(0x4)
CONTEXT_FLOATING_POINT = CONTEXT_AMD64 | long(0x8)
CONTEXT_DEBUG_REGISTERS = CONTEXT_AMD64 | long(0x10)

CONTEXT_MMX_REGISTERS = CONTEXT_FLOATING_POINT

CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_FLOATING_POINT

CONTEXT_ALL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS | CONTEXT_FLOATING_POINT | CONTEXT_DEBUG_REGISTERS

CONTEXT_EXCEPTION_ACTIVE = 0x8000000
CONTEXT_SERVICE_ACTIVE = 0x10000000
CONTEXT_EXCEPTION_REQUEST = 0x40000000
CONTEXT_EXCEPTION_REPORTING = 0x80000000

INITIAL_MXCSR = 0x1F80  # initial MXCSR value
INITIAL_FPCSR = 0x027F  # initial FPCSR value


# typedef struct _XMM_SAVE_AREA32 {
#     WORD   ControlWord;
#     WORD   StatusWord;
#     BYTE  TagWord;
#     BYTE  Reserved1;
#     WORD   ErrorOpcode;
#     DWORD ErrorOffset;
#     WORD   ErrorSelector;
#     WORD   Reserved2;
#     DWORD DataOffset;
#     WORD   DataSelector;
#     WORD   Reserved3;
#     DWORD MxCsr;
#     DWORD MxCsr_Mask;
#     M128A FloatRegisters[8];
#     M128A XmmRegisters[16];
#     BYTE  Reserved4[96];
# } XMM_SAVE_AREA32, *PXMM_SAVE_AREA32;
class XMM_SAVE_AREA32(Structure):
    _pack_ = 1
    _fields_ = [
        ("ControlWord", WORD),
        ("StatusWord", WORD),
        ("TagWord", BYTE),
        ("Reserved1", BYTE),
        ("ErrorOpcode", WORD),
        ("ErrorOffset", DWORD),
        ("ErrorSelector", WORD),
        ("Reserved2", WORD),
        ("DataOffset", DWORD),
        ("DataSelector", WORD),
        ("Reserved3", WORD),
        ("MxCsr", DWORD),
        ("MxCsr_Mask", DWORD),
        ("FloatRegisters", M128A * 8),
        ("XmmRegisters", M128A * 16),
        ("Reserved4", BYTE * 96),
    ]

    def from_dict(self):
        raise NotImplementedError()

    def to_dict(self):
        d = dict()
        for name, type in self._fields_:
            if name in ("FloatRegisters", "XmmRegisters"):
                d[name] = tuple([(x.LowPart + (x.HighPart << 64)) for x in getattr(self, name)])
            elif name == "Reserved4":
                d[name] = tuple([chr(x) for x in getattr(self, name)])
            else:
                d[name] = getattr(self, name)
        return d


LEGACY_SAVE_AREA_LENGTH = sizeof(XMM_SAVE_AREA32)

PXMM_SAVE_AREA32 = ctypes.POINTER(XMM_SAVE_AREA32)
LPXMM_SAVE_AREA32 = PXMM_SAVE_AREA32

# //
# // Context Frame
# //
# //  This frame has a several purposes: 1) it is used as an argument to
# //  NtContinue, 2) is is used to constuct a call frame for APC delivery,
# //  and 3) it is used in the user level thread creation routines.
# //
# //
# // The flags field within this record controls the contents of a CONTEXT
# // record.
# //
# // If the context record is used as an input parameter, then for each
# // portion of the context record controlled by a flag whose value is
# // set, it is assumed that that portion of the context record contains
# // valid context. If the context record is being used to modify a threads
# // context, then only that portion of the threads context is modified.
# //
# // If the context record is used as an output parameter to capture the
# // context of a thread, then only those portions of the thread's context
# // corresponding to set flags will be returned.
# //
# // CONTEXT_CONTROL specifies SegSs, Rsp, SegCs, Rip, and EFlags.
# //
# // CONTEXT_INTEGER specifies Rax, Rcx, Rdx, Rbx, Rbp, Rsi, Rdi, and R8-R15.
# //
# // CONTEXT_SEGMENTS specifies SegDs, SegEs, SegFs, and SegGs.
# //
# // CONTEXT_DEBUG_REGISTERS specifies Dr0-Dr3 and Dr6-Dr7.
# //
# // CONTEXT_MMX_REGISTERS specifies the floating point and extended registers
# //     Mm0/St0-Mm7/St7 and Xmm0-Xmm15).
# //
#
# typedef struct DECLSPEC_ALIGN(16) _CONTEXT {
#
#     //
#     // Register parameter home addresses.
#     //
#     // N.B. These fields are for convience - they could be used to extend the
#     //      context record in the future.
#     //
#
#     DWORD64 P1Home;
#     DWORD64 P2Home;
#     DWORD64 P3Home;
#     DWORD64 P4Home;
#     DWORD64 P5Home;
#     DWORD64 P6Home;
#
#     //
#     // Control flags.
#     //
#
#     DWORD ContextFlags;
#     DWORD MxCsr;
#
#     //
#     // Segment Registers and processor flags.
#     //
#
#     WORD   SegCs;
#     WORD   SegDs;
#     WORD   SegEs;
#     WORD   SegFs;
#     WORD   SegGs;
#     WORD   SegSs;
#     DWORD EFlags;
#
#     //
#     // Debug registers
#     //
#
#     DWORD64 Dr0;
#     DWORD64 Dr1;
#     DWORD64 Dr2;
#     DWORD64 Dr3;
#     DWORD64 Dr6;
#     DWORD64 Dr7;
#
#     //
#     // Integer registers.
#     //
#
#     DWORD64 Rax;
#     DWORD64 Rcx;
#     DWORD64 Rdx;
#     DWORD64 Rbx;
#     DWORD64 Rsp;
#     DWORD64 Rbp;
#     DWORD64 Rsi;
#     DWORD64 Rdi;
#     DWORD64 R8;
#     DWORD64 R9;
#     DWORD64 R10;
#     DWORD64 R11;
#     DWORD64 R12;
#     DWORD64 R13;
#     DWORD64 R14;
#     DWORD64 R15;
#
#     //
#     // Program counter.
#     //
#
#     DWORD64 Rip;
#
#     //
#     // Floating point state.
#     //
#
#     union {
#         XMM_SAVE_AREA32 FltSave;
#         struct {
#             M128A Header[2];
#             M128A Legacy[8];
#             M128A Xmm0;
#             M128A Xmm1;
#             M128A Xmm2;
#             M128A Xmm3;
#             M128A Xmm4;
#             M128A Xmm5;
#             M128A Xmm6;
#             M128A Xmm7;
#             M128A Xmm8;
#             M128A Xmm9;
#             M128A Xmm10;
#             M128A Xmm11;
#             M128A Xmm12;
#             M128A Xmm13;
#             M128A Xmm14;
#             M128A Xmm15;
#         };
#     };
#
#     //
#     // Vector registers.
#     //
#
#     M128A VectorRegister[26];
#     DWORD64 VectorControl;
#
#     //
#     // Special debug control registers.
#     //
#
#     DWORD64 DebugControl;
#     DWORD64 LastBranchToRip;
#     DWORD64 LastBranchFromRip;
#     DWORD64 LastExceptionToRip;
#     DWORD64 LastExceptionFromRip;
# } CONTEXT, *PCONTEXT;


class _CONTEXT_FLTSAVE_STRUCT(Structure):
    _fields_ = [
        ("Header", M128A * 2),
        ("Legacy", M128A * 8),
        ("Xmm0", M128A),
        ("Xmm1", M128A),
        ("Xmm2", M128A),
        ("Xmm3", M128A),
        ("Xmm4", M128A),
        ("Xmm5", M128A),
        ("Xmm6", M128A),
        ("Xmm7", M128A),
        ("Xmm8", M128A),
        ("Xmm9", M128A),
        ("Xmm10", M128A),
        ("Xmm11", M128A),
        ("Xmm12", M128A),
        ("Xmm13", M128A),
        ("Xmm14", M128A),
        ("Xmm15", M128A),
    ]

    def from_dict(self):
        raise NotImplementedError()

    def to_dict(self):
        d = dict()
        for name, type in self._fields_:
            if name in ("Header", "Legacy"):
                d[name] = tuple([(x.Low + (x.High << 64)) for x in getattr(self, name)])
            else:
                x = getattr(self, name)
                d[name] = x.Low + (x.High << 64)
        return d


class _CONTEXT_FLTSAVE_UNION(Union):
    _fields_ = [
        ("flt", XMM_SAVE_AREA32),
        ("xmm", _CONTEXT_FLTSAVE_STRUCT),
    ]

    def from_dict(self):
        raise NotImplementedError()

    def to_dict(self):
        d = dict()
        d["flt"] = self.flt.to_dict()
        d["xmm"] = self.xmm.to_dict()
        return d


class CONTEXT(Structure):
    arch = ARCH_AMD64

    _pack_ = 16
    _fields_ = [
        # Register parameter home addresses.
        ("P1Home", DWORD64),
        ("P2Home", DWORD64),
        ("P3Home", DWORD64),
        ("P4Home", DWORD64),
        ("P5Home", DWORD64),
        ("P6Home", DWORD64),
        # Control flags.
        ("ContextFlags", DWORD),
        ("MxCsr", DWORD),
        # Segment Registers and processor flags.
        ("SegCs", WORD),
        ("SegDs", WORD),
        ("SegEs", WORD),
        ("SegFs", WORD),
        ("SegGs", WORD),
        ("SegSs", WORD),
        ("EFlags", DWORD),
        # Debug registers.
        ("Dr0", DWORD64),
        ("Dr1", DWORD64),
        ("Dr2", DWORD64),
        ("Dr3", DWORD64),
        ("Dr6", DWORD64),
        ("Dr7", DWORD64),
        # Integer registers.
        ("Rax", DWORD64),
        ("Rcx", DWORD64),
        ("Rdx", DWORD64),
        ("Rbx", DWORD64),
        ("Rsp", DWORD64),
        ("Rbp", DWORD64),
        ("Rsi", DWORD64),
        ("Rdi", DWORD64),
        ("R8", DWORD64),
        ("R9", DWORD64),
        ("R10", DWORD64),
        ("R11", DWORD64),
        ("R12", DWORD64),
        ("R13", DWORD64),
        ("R14", DWORD64),
        ("R15", DWORD64),
        # Program counter.
        ("Rip", DWORD64),
        # Floating point state.
        ("FltSave", _CONTEXT_FLTSAVE_UNION),
        # Vector registers.
        ("VectorRegister", M128A * 26),
        ("VectorControl", DWORD64),
        # Special debug control registers.
        ("DebugControl", DWORD64),
        ("LastBranchToRip", DWORD64),
        ("LastBranchFromRip", DWORD64),
        ("LastExceptionToRip", DWORD64),
        ("LastExceptionFromRip", DWORD64),
    ]

    _others = ("P1Home", "P2Home", "P3Home", "P4Home", "P5Home", "P6Home", "MxCsr", "VectorRegister", "VectorControl")
    _control = ("SegSs", "Rsp", "SegCs", "Rip", "EFlags")
    _integer = ("Rax", "Rcx", "Rdx", "Rbx", "Rsp", "Rbp", "Rsi", "Rdi", "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15")
    _segments = ("SegDs", "SegEs", "SegFs", "SegGs")
    _debug = (
        "Dr0",
        "Dr1",
        "Dr2",
        "Dr3",
        "Dr6",
        "Dr7",
        "DebugControl",
        "LastBranchToRip",
        "LastBranchFromRip",
        "LastExceptionToRip",
        "LastExceptionFromRip",
    )
    _mmx = (
        "Xmm0",
        "Xmm1",
        "Xmm2",
        "Xmm3",
        "Xmm4",
        "Xmm5",
        "Xmm6",
        "Xmm7",
        "Xmm8",
        "Xmm9",
        "Xmm10",
        "Xmm11",
        "Xmm12",
        "Xmm13",
        "Xmm14",
        "Xmm15",
    )

    # XXX TODO
    # Convert VectorRegister and Xmm0-Xmm15 to pure Python types!

    @classmethod
    def from_dict(cls, ctx):
        "Instance a new structure from a Python native type."
        ctx = Context(ctx)
        s = cls()
        ContextFlags = ctx["ContextFlags"]
        s.ContextFlags = ContextFlags
        for key in cls._others:
            if key != "VectorRegister":
                setattr(s, key, ctx[key])
            else:
                w = ctx[key]
                v = (M128A * len(w))()
                i = 0
                for x in w:
                    y = M128A()
                    y.High = x >> 64
                    y.Low = x - (x >> 64)
                    v[i] = y
                    i += 1
                setattr(s, key, v)
        if (ContextFlags & CONTEXT_CONTROL) == CONTEXT_CONTROL:
            for key in cls._control:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_INTEGER) == CONTEXT_INTEGER:
            for key in cls._integer:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_SEGMENTS) == CONTEXT_SEGMENTS:
            for key in cls._segments:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_DEBUG_REGISTERS) == CONTEXT_DEBUG_REGISTERS:
            for key in cls._debug:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_MMX_REGISTERS) == CONTEXT_MMX_REGISTERS:
            xmm = s.FltSave.xmm
            for key in cls._mmx:
                y = M128A()
                y.High = x >> 64
                y.Low = x - (x >> 64)
                setattr(xmm, key, y)
        return s

    def to_dict(self):
        "Convert a structure into a Python dictionary."
        ctx = Context()
        ContextFlags = self.ContextFlags
        ctx["ContextFlags"] = ContextFlags
        for key in self._others:
            if key != "VectorRegister":
                ctx[key] = getattr(self, key)
            else:
                ctx[key] = tuple([(x.Low + (x.High << 64)) for x in getattr(self, key)])
        if (ContextFlags & CONTEXT_CONTROL) == CONTEXT_CONTROL:
            for key in self._control:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_INTEGER) == CONTEXT_INTEGER:
            for key in self._integer:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_SEGMENTS) == CONTEXT_SEGMENTS:
            for key in self._segments:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_DEBUG_REGISTERS) == CONTEXT_DEBUG_REGISTERS:
            for key in self._debug:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_MMX_REGISTERS) == CONTEXT_MMX_REGISTERS:
            xmm = self.FltSave.xmm.to_dict()
            for key in self._mmx:
                ctx[key] = xmm.get(key)
        return ctx


PCONTEXT = ctypes.POINTER(CONTEXT)
LPCONTEXT = PCONTEXT


class Context(dict):
    """
    Register context dictionary for the amd64 architecture.
    """

    arch = CONTEXT.arch

    def __get_pc(self):
        return self["Rip"]

    def __set_pc(self, value):
        self["Rip"] = value

    pc = property(__get_pc, __set_pc)

    def __get_sp(self):
        return self["Rsp"]

    def __set_sp(self, value):
        self["Rsp"] = value

    sp = property(__get_sp, __set_sp)

    def __get_fp(self):
        return self["Rbp"]

    def __set_fp(self, value):
        self["Rbp"] = value

    fp = property(__get_fp, __set_fp)


# --- LDT_ENTRY structure ------------------------------------------------------

# typedef struct _LDT_ENTRY {
#   WORD LimitLow;
#   WORD BaseLow;
#   union {
#     struct {
#       BYTE BaseMid;
#       BYTE Flags1;
#       BYTE Flags2;
#       BYTE BaseHi;
#     } Bytes;
#     struct {
#       DWORD BaseMid  :8;
#       DWORD Type  :5;
#       DWORD Dpl  :2;
#       DWORD Pres  :1;
#       DWORD LimitHi  :4;
#       DWORD Sys  :1;
#       DWORD Reserved_0  :1;
#       DWORD Default_Big  :1;
#       DWORD Granularity  :1;
#       DWORD BaseHi  :8;
#     } Bits;
#   } HighWord;
# } LDT_ENTRY,
#  *PLDT_ENTRY;


class _LDT_ENTRY_BYTES_(Structure):
    _pack_ = 1
    _fields_ = [
        ("BaseMid", BYTE),
        ("Flags1", BYTE),
        ("Flags2", BYTE),
        ("BaseHi", BYTE),
    ]


class _LDT_ENTRY_BITS_(Structure):
    _pack_ = 1
    _fields_ = [
        ("BaseMid", DWORD, 8),
        ("Type", DWORD, 5),
        ("Dpl", DWORD, 2),
        ("Pres", DWORD, 1),
        ("LimitHi", DWORD, 4),
        ("Sys", DWORD, 1),
        ("Reserved_0", DWORD, 1),
        ("Default_Big", DWORD, 1),
        ("Granularity", DWORD, 1),
        ("BaseHi", DWORD, 8),
    ]


class _LDT_ENTRY_HIGHWORD_(Union):
    _pack_ = 1
    _fields_ = [
        ("Bytes", _LDT_ENTRY_BYTES_),
        ("Bits", _LDT_ENTRY_BITS_),
    ]


class LDT_ENTRY(Structure):
    _pack_ = 1
    _fields_ = [
        ("LimitLow", WORD),
        ("BaseLow", WORD),
        ("HighWord", _LDT_ENTRY_HIGHWORD_),
    ]


PLDT_ENTRY = POINTER(LDT_ENTRY)
LPLDT_ENTRY = PLDT_ENTRY

# --- WOW64 CONTEXT structure and constants ------------------------------------

# Value of SegCs in a Wow64 thread when running in 32 bits mode
WOW64_CS32 = 0x23

WOW64_CONTEXT_i386 = long(0x00010000)
WOW64_CONTEXT_i486 = long(0x00010000)

WOW64_CONTEXT_CONTROL = WOW64_CONTEXT_i386 | long(0x00000001)
WOW64_CONTEXT_INTEGER = WOW64_CONTEXT_i386 | long(0x00000002)
WOW64_CONTEXT_SEGMENTS = WOW64_CONTEXT_i386 | long(0x00000004)
WOW64_CONTEXT_FLOATING_POINT = WOW64_CONTEXT_i386 | long(0x00000008)
WOW64_CONTEXT_DEBUG_REGISTERS = WOW64_CONTEXT_i386 | long(0x00000010)
WOW64_CONTEXT_EXTENDED_REGISTERS = WOW64_CONTEXT_i386 | long(0x00000020)

WOW64_CONTEXT_FULL = WOW64_CONTEXT_CONTROL | WOW64_CONTEXT_INTEGER | WOW64_CONTEXT_SEGMENTS
WOW64_CONTEXT_ALL = (
    WOW64_CONTEXT_CONTROL
    | WOW64_CONTEXT_INTEGER
    | WOW64_CONTEXT_SEGMENTS
    | WOW64_CONTEXT_FLOATING_POINT
    | WOW64_CONTEXT_DEBUG_REGISTERS
    | WOW64_CONTEXT_EXTENDED_REGISTERS
)

WOW64_SIZE_OF_80387_REGISTERS = 80
WOW64_MAXIMUM_SUPPORTED_EXTENSION = 512


class WOW64_FLOATING_SAVE_AREA(context_i386.FLOATING_SAVE_AREA):
    pass


class WOW64_CONTEXT(context_i386.CONTEXT):
    pass


class WOW64_LDT_ENTRY(context_i386.LDT_ENTRY):
    pass


PWOW64_FLOATING_SAVE_AREA = POINTER(WOW64_FLOATING_SAVE_AREA)
PWOW64_CONTEXT = POINTER(WOW64_CONTEXT)
PWOW64_LDT_ENTRY = POINTER(WOW64_LDT_ENTRY)

###############################################################################


# BOOL WINAPI GetThreadSelectorEntry(
#   __in   HANDLE hThread,
#   __in   DWORD dwSelector,
#   __out  LPLDT_ENTRY lpSelectorEntry
# );
def GetThreadSelectorEntry(hThread, dwSelector):
    _GetThreadSelectorEntry = windll.kernel32.GetThreadSelectorEntry
    _GetThreadSelectorEntry.argtypes = [HANDLE, DWORD, LPLDT_ENTRY]
    _GetThreadSelectorEntry.restype = bool
    _GetThreadSelectorEntry.errcheck = RaiseIfZero

    ldt = LDT_ENTRY()
    _GetThreadSelectorEntry(hThread, dwSelector, byref(ldt))
    return ldt


# BOOL WINAPI GetThreadContext(
#   __in     HANDLE hThread,
#   __inout  LPCONTEXT lpContext
# );
def GetThreadContext(hThread, ContextFlags=None, raw=False):
    _GetThreadContext = windll.kernel32.GetThreadContext
    _GetThreadContext.argtypes = [HANDLE, LPCONTEXT]
    _GetThreadContext.restype = bool
    _GetThreadContext.errcheck = RaiseIfZero

    if ContextFlags is None:
        ContextFlags = CONTEXT_ALL | CONTEXT_AMD64
    Context = CONTEXT()
    Context.ContextFlags = ContextFlags
    _GetThreadContext(hThread, byref(Context))
    if raw:
        return Context
    return Context.to_dict()


# BOOL WINAPI SetThreadContext(
#   __in  HANDLE hThread,
#   __in  const CONTEXT* lpContext
# );
def SetThreadContext(hThread, lpContext):
    _SetThreadContext = windll.kernel32.SetThreadContext
    _SetThreadContext.argtypes = [HANDLE, LPCONTEXT]
    _SetThreadContext.restype = bool
    _SetThreadContext.errcheck = RaiseIfZero

    if isinstance(lpContext, dict):
        lpContext = CONTEXT.from_dict(lpContext)
    _SetThreadContext(hThread, byref(lpContext))


# BOOL Wow64GetThreadSelectorEntry(
#   __in   HANDLE hThread,
#   __in   DWORD dwSelector,
#   __out  PWOW64_LDT_ENTRY lpSelectorEntry
# );
def Wow64GetThreadSelectorEntry(hThread, dwSelector):
    _Wow64GetThreadSelectorEntry = windll.kernel32.Wow64GetThreadSelectorEntry
    _Wow64GetThreadSelectorEntry.argtypes = [HANDLE, DWORD, PWOW64_LDT_ENTRY]
    _Wow64GetThreadSelectorEntry.restype = bool
    _Wow64GetThreadSelectorEntry.errcheck = RaiseIfZero

    lpSelectorEntry = WOW64_LDT_ENTRY()
    _Wow64GetThreadSelectorEntry(hThread, dwSelector, byref(lpSelectorEntry))
    return lpSelectorEntry


# DWORD WINAPI Wow64ResumeThread(
#   __in  HANDLE hThread
# );
def Wow64ResumeThread(hThread):
    _Wow64ResumeThread = windll.kernel32.Wow64ResumeThread
    _Wow64ResumeThread.argtypes = [HANDLE]
    _Wow64ResumeThread.restype = DWORD

    previousCount = _Wow64ResumeThread(hThread)
    if previousCount == DWORD(-1).value:
        raise ctypes.WinError()
    return previousCount


# DWORD WINAPI Wow64SuspendThread(
#   __in  HANDLE hThread
# );
def Wow64SuspendThread(hThread):
    _Wow64SuspendThread = windll.kernel32.Wow64SuspendThread
    _Wow64SuspendThread.argtypes = [HANDLE]
    _Wow64SuspendThread.restype = DWORD

    previousCount = _Wow64SuspendThread(hThread)
    if previousCount == DWORD(-1).value:
        raise ctypes.WinError()
    return previousCount


# XXX TODO Use this http://www.nynaeve.net/Code/GetThreadWow64Context.cpp
# Also see http://www.woodmann.com/forum/archive/index.php/t-11162.html


# BOOL WINAPI Wow64GetThreadContext(
#   __in     HANDLE hThread,
#   __inout  PWOW64_CONTEXT lpContext
# );
def Wow64GetThreadContext(hThread, ContextFlags=None):
    _Wow64GetThreadContext = windll.kernel32.Wow64GetThreadContext
    _Wow64GetThreadContext.argtypes = [HANDLE, PWOW64_CONTEXT]
    _Wow64GetThreadContext.restype = bool
    _Wow64GetThreadContext.errcheck = RaiseIfZero

    # XXX doesn't exist in XP 64 bits

    Context = WOW64_CONTEXT()
    if ContextFlags is None:
        Context.ContextFlags = WOW64_CONTEXT_ALL | WOW64_CONTEXT_i386
    else:
        Context.ContextFlags = ContextFlags
    _Wow64GetThreadContext(hThread, byref(Context))
    return Context.to_dict()


# BOOL WINAPI Wow64SetThreadContext(
#   __in  HANDLE hThread,
#   __in  const WOW64_CONTEXT *lpContext
# );
def Wow64SetThreadContext(hThread, lpContext):
    _Wow64SetThreadContext = windll.kernel32.Wow64SetThreadContext
    _Wow64SetThreadContext.argtypes = [HANDLE, PWOW64_CONTEXT]
    _Wow64SetThreadContext.restype = bool
    _Wow64SetThreadContext.errcheck = RaiseIfZero

    # XXX doesn't exist in XP 64 bits

    if isinstance(lpContext, dict):
        lpContext = WOW64_CONTEXT.from_dict(lpContext)
    _Wow64SetThreadContext(hThread, byref(lpContext))


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\matplotlib\sankey.py ===
"""
Module for creating Sankey diagrams using Matplotlib.
"""

import logging
from types import SimpleNamespace

import numpy as np

import matplotlib as mpl
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
from matplotlib import _docstring

_log = logging.getLogger(__name__)

__author__ = "Kevin L. Davies"
__credits__ = ["Yannick Copin"]
__license__ = "BSD"
__version__ = "2011/09/16"

# Angles [deg/90]
RIGHT = 0
UP = 1
# LEFT = 2
DOWN = 3


class Sankey:
    """
    Sankey diagram.

      Sankey diagrams are a specific type of flow diagram, in which
      the width of the arrows is shown proportionally to the flow
      quantity.  They are typically used to visualize energy or
      material or cost transfers between processes.
      `Wikipedia (6/1/2011) <https://en.wikipedia.org/wiki/Sankey_diagram>`_

    """

    def __init__(self, ax=None, scale=1.0, unit='', format='%G', gap=0.25,
                 radius=0.1, shoulder=0.03, offset=0.15, head_angle=100,
                 margin=0.4, tolerance=1e-6, **kwargs):
        """
        Create a new Sankey instance.

        The optional arguments listed below are applied to all subdiagrams so
        that there is consistent alignment and formatting.

        In order to draw a complex Sankey diagram, create an instance of
        `Sankey` by calling it without any kwargs::

            sankey = Sankey()

        Then add simple Sankey sub-diagrams::

            sankey.add() # 1
            sankey.add() # 2
            #...
            sankey.add() # n

        Finally, create the full diagram::

            sankey.finish()

        Or, instead, simply daisy-chain those calls::

            Sankey().add().add...  .add().finish()

        Other Parameters
        ----------------
        ax : `~matplotlib.axes.Axes`
            Axes onto which the data should be plotted.  If *ax* isn't
            provided, new Axes will be created.
        scale : float
            Scaling factor for the flows.  *scale* sizes the width of the paths
            in order to maintain proper layout.  The same scale is applied to
            all subdiagrams.  The value should be chosen such that the product
            of the scale and the sum of the inputs is approximately 1.0 (and
            the product of the scale and the sum of the outputs is
            approximately -1.0).
        unit : str
            The physical unit associated with the flow quantities.  If *unit*
            is None, then none of the quantities are labeled.
        format : str or callable
            A Python number formatting string or callable used to label the
            flows with their quantities (i.e., a number times a unit, where the
            unit is given). If a format string is given, the label will be
            ``format % quantity``. If a callable is given, it will be called
            with ``quantity`` as an argument.
        gap : float
            Space between paths that break in/break away to/from the top or
            bottom.
        radius : float
            Inner radius of the vertical paths.
        shoulder : float
            Size of the shoulders of output arrows.
        offset : float
            Text offset (from the dip or tip of the arrow).
        head_angle : float
            Angle, in degrees, of the arrow heads (and negative of the angle of
            the tails).
        margin : float
            Minimum space between Sankey outlines and the edge of the plot
            area.
        tolerance : float
            Acceptable maximum of the magnitude of the sum of flows.  The
            magnitude of the sum of connected flows cannot be greater than
            *tolerance*.
        **kwargs
            Any additional keyword arguments will be passed to `add`, which
            will create the first subdiagram.

        See Also
        --------
        Sankey.add
        Sankey.finish

        Examples
        --------
        .. plot:: gallery/specialty_plots/sankey_basics.py
        """
        # Check the arguments.
        if gap < 0:
            raise ValueError(
                "'gap' is negative, which is not allowed because it would "
                "cause the paths to overlap")
        if radius > gap:
            raise ValueError(
                "'radius' is greater than 'gap', which is not allowed because "
                "it would cause the paths to overlap")
        if head_angle < 0:
            raise ValueError(
                "'head_angle' is negative, which is not allowed because it "
                "would cause inputs to look like outputs and vice versa")
        if tolerance < 0:
            raise ValueError(
                "'tolerance' is negative, but it must be a magnitude")

        # Create Axes if necessary.
        if ax is None:
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(1, 1, 1, xticks=[], yticks=[])

        self.diagrams = []

        # Store the inputs.
        self.ax = ax
        self.unit = unit
        self.format = format
        self.scale = scale
        self.gap = gap
        self.radius = radius
        self.shoulder = shoulder
        self.offset = offset
        self.margin = margin
        self.pitch = np.tan(np.pi * (1 - head_angle / 180.0) / 2.0)
        self.tolerance = tolerance

        # Initialize the vertices of tight box around the diagram(s).
        self.extent = np.array((np.inf, -np.inf, np.inf, -np.inf))

        # If there are any kwargs, create the first subdiagram.
        if len(kwargs):
            self.add(**kwargs)

    def _arc(self, quadrant=0, cw=True, radius=1, center=(0, 0)):
        """
        Return the codes and vertices for a rotated, scaled, and translated
        90 degree arc.

        Other Parameters
        ----------------
        quadrant : {0, 1, 2, 3}, default: 0
            Uses 0-based indexing (0, 1, 2, or 3).
        cw : bool, default: True
            If True, the arc vertices are produced clockwise; counter-clockwise
            otherwise.
        radius : float, default: 1
            The radius of the arc.
        center : (float, float), default: (0, 0)
            (x, y) tuple of the arc's center.
        """
        # Note:  It would be possible to use matplotlib's transforms to rotate,
        # scale, and translate the arc, but since the angles are discrete,
        # it's just as easy and maybe more efficient to do it here.
        ARC_CODES = [Path.LINETO,
                     Path.CURVE4,
                     Path.CURVE4,
                     Path.CURVE4,
                     Path.CURVE4,
                     Path.CURVE4,
                     Path.CURVE4]
        # Vertices of a cubic Bezier curve approximating a 90 deg arc
        # These can be determined by Path.arc(0, 90).
        ARC_VERTICES = np.array([[1.00000000e+00, 0.00000000e+00],
                                 [1.00000000e+00, 2.65114773e-01],
                                 [8.94571235e-01, 5.19642327e-01],
                                 [7.07106781e-01, 7.07106781e-01],
                                 [5.19642327e-01, 8.94571235e-01],
                                 [2.65114773e-01, 1.00000000e+00],
                                 # Insignificant
                                 # [6.12303177e-17, 1.00000000e+00]])
                                 [0.00000000e+00, 1.00000000e+00]])
        if quadrant in (0, 2):
            if cw:
                vertices = ARC_VERTICES
            else:
                vertices = ARC_VERTICES[:, ::-1]  # Swap x and y.
        else:  # 1, 3
            # Negate x.
            if cw:
                # Swap x and y.
                vertices = np.column_stack((-ARC_VERTICES[:, 1],
                                             ARC_VERTICES[:, 0]))
            else:
                vertices = np.column_stack((-ARC_VERTICES[:, 0],
                                             ARC_VERTICES[:, 1]))
        if quadrant > 1:
            radius = -radius  # Rotate 180 deg.
        return list(zip(ARC_CODES, radius * vertices +
                        np.tile(center, (ARC_VERTICES.shape[0], 1))))

    def _add_input(self, path, angle, flow, length):
        """
        Add an input to a path and return its tip and label locations.
        """
        if angle is None:
            return [0, 0], [0, 0]
        else:
            x, y = path[-1][1]  # Use the last point as a reference.
            dipdepth = (flow / 2) * self.pitch
            if angle == RIGHT:
                x -= length
                dip = [x + dipdepth, y + flow / 2.0]
                path.extend([(Path.LINETO, [x, y]),
                             (Path.LINETO, dip),
                             (Path.LINETO, [x, y + flow]),
                             (Path.LINETO, [x + self.gap, y + flow])])
                label_location = [dip[0] - self.offset, dip[1]]
            else:  # Vertical
                x -= self.gap
                if angle == UP:
                    sign = 1
                else:
                    sign = -1

                dip = [x - flow / 2, y - sign * (length - dipdepth)]
                if angle == DOWN:
                    quadrant = 2
                else:
                    quadrant = 1

                # Inner arc isn't needed if inner radius is zero
                if self.radius:
                    path.extend(self._arc(quadrant=quadrant,
                                          cw=angle == UP,
                                          radius=self.radius,
                                          center=(x + self.radius,
                                                  y - sign * self.radius)))
                else:
                    path.append((Path.LINETO, [x, y]))
                path.extend([(Path.LINETO, [x, y - sign * length]),
                             (Path.LINETO, dip),
                             (Path.LINETO, [x - flow, y - sign * length])])
                path.extend(self._arc(quadrant=quadrant,
                                      cw=angle == DOWN,
                                      radius=flow + self.radius,
                                      center=(x + self.radius,
                                              y - sign * self.radius)))
                path.append((Path.LINETO, [x - flow, y + sign * flow]))
                label_location = [dip[0], dip[1] - sign * self.offset]

            return dip, label_location

    def _add_output(self, path, angle, flow, length):
        """
        Append an output to a path and return its tip and label locations.

        .. note:: *flow* is negative for an output.
        """
        if angle is None:
            return [0, 0], [0, 0]
        else:
            x, y = path[-1][1]  # Use the last point as a reference.
            tipheight = (self.shoulder - flow / 2) * self.pitch
            if angle == RIGHT:
                x += length
                tip = [x + tipheight, y + flow / 2.0]
                path.extend([(Path.LINETO, [x, y]),
                             (Path.LINETO, [x, y + self.shoulder]),
                             (Path.LINETO, tip),
                             (Path.LINETO, [x, y - self.shoulder + flow]),
                             (Path.LINETO, [x, y + flow]),
                             (Path.LINETO, [x - self.gap, y + flow])])
                label_location = [tip[0] + self.offset, tip[1]]
            else:  # Vertical
                x += self.gap
                if angle == UP:
                    sign, quadrant = 1, 3
                else:
                    sign, quadrant = -1, 0

                tip = [x - flow / 2.0, y + sign * (length + tipheight)]
                # Inner arc isn't needed if inner radius is zero
                if self.radius:
                    path.extend(self._arc(quadrant=quadrant,
                                          cw=angle == UP,
                                          radius=self.radius,
                                          center=(x - self.radius,
                                                  y + sign * self.radius)))
                else:
                    path.append((Path.LINETO, [x, y]))
                path.extend([(Path.LINETO, [x, y + sign * length]),
                             (Path.LINETO, [x - self.shoulder,
                                            y + sign * length]),
                             (Path.LINETO, tip),
                             (Path.LINETO, [x + self.shoulder - flow,
                                            y + sign * length]),
                             (Path.LINETO, [x - flow, y + sign * length])])
                path.extend(self._arc(quadrant=quadrant,
                                      cw=angle == DOWN,
                                      radius=self.radius - flow,
                                      center=(x - self.radius,
                                              y + sign * self.radius)))
                path.append((Path.LINETO, [x - flow, y + sign * flow]))
                label_location = [tip[0], tip[1] + sign * self.offset]
            return tip, label_location

    def _revert(self, path, first_action=Path.LINETO):
        """
        A path is not simply reversible by path[::-1] since the code
        specifies an action to take from the **previous** point.
        """
        reverse_path = []
        next_code = first_action
        for code, position in path[::-1]:
            reverse_path.append((next_code, position))
            next_code = code
        return reverse_path
        # This might be more efficient, but it fails because 'tuple' object
        # doesn't support item assignment:
        # path[1] = path[1][-1:0:-1]
        # path[1][0] = first_action
        # path[2] = path[2][::-1]
        # return path

    @_docstring.interpd
    def add(self, patchlabel='', flows=None, orientations=None, labels='',
            trunklength=1.0, pathlengths=0.25, prior=None, connect=(0, 0),
            rotation=0, **kwargs):
        """
        Add a simple Sankey diagram with flows at the same hierarchical level.

        Parameters
        ----------
        patchlabel : str
            Label to be placed at the center of the diagram.
            Note that *label* (not *patchlabel*) can be passed as keyword
            argument to create an entry in the legend.

        flows : list of float
            Array of flow values.  By convention, inputs are positive and
            outputs are negative.

            Flows are placed along the top of the diagram from the inside out
            in order of their index within *flows*.  They are placed along the
            sides of the diagram from the top down and along the bottom from
            the outside in.

            If the sum of the inputs and outputs is
            nonzero, the discrepancy will appear as a cubic Bézier curve along
            the top and bottom edges of the trunk.

        orientations : list of {-1, 0, 1}
            List of orientations of the flows (or a single orientation to be
            used for all flows).  Valid values are 0 (inputs from
            the left, outputs to the right), 1 (from and to the top) or -1
            (from and to the bottom).

        labels : list of (str or None)
            List of labels for the flows (or a single label to be used for all
            flows).  Each label may be *None* (no label), or a labeling string.
            If an entry is a (possibly empty) string, then the quantity for the
            corresponding flow will be shown below the string.  However, if
            the *unit* of the main diagram is None, then quantities are never
            shown, regardless of the value of this argument.

        trunklength : float
            Length between the bases of the input and output groups (in
            data-space units).

        pathlengths : list of float
            List of lengths of the vertical arrows before break-in or after
            break-away.  If a single value is given, then it will be applied to
            the first (inside) paths on the top and bottom, and the length of
            all other arrows will be justified accordingly.  The *pathlengths*
            are not applied to the horizontal inputs and outputs.

        prior : int
            Index of the prior diagram to which this diagram should be
            connected.

        connect : (int, int)
            A (prior, this) tuple indexing the flow of the prior diagram and
            the flow of this diagram which should be connected.  If this is the
            first diagram or *prior* is *None*, *connect* will be ignored.

        rotation : float
            Angle of rotation of the diagram in degrees.  The interpretation of
            the *orientations* argument will be rotated accordingly (e.g., if
            *rotation* == 90, an *orientations* entry of 1 means to/from the
            left).  *rotation* is ignored if this diagram is connected to an
            existing one (using *prior* and *connect*).

        Returns
        -------
        Sankey
            The current `.Sankey` instance.

        Other Parameters
        ----------------
        **kwargs
           Additional keyword arguments set `matplotlib.patches.PathPatch`
           properties, listed below.  For example, one may want to use
           ``fill=False`` or ``label="A legend entry"``.

        %(Patch:kwdoc)s

        See Also
        --------
        Sankey.finish
        """
        # Check and preprocess the arguments.
        flows = np.array([1.0, -1.0]) if flows is None else np.array(flows)
        n = flows.shape[0]  # Number of flows
        if rotation is None:
            rotation = 0
        else:
            # In the code below, angles are expressed in deg/90.
            rotation /= 90.0
        if orientations is None:
            orientations = 0
        try:
            orientations = np.broadcast_to(orientations, n)
        except ValueError:
            raise ValueError(
                f"The shapes of 'flows' {np.shape(flows)} and 'orientations' "
                f"{np.shape(orientations)} are incompatible"
            ) from None
        try:
            labels = np.broadcast_to(labels, n)
        except ValueError:
            raise ValueError(
                f"The shapes of 'flows' {np.shape(flows)} and 'labels' "
                f"{np.shape(labels)} are incompatible"
            ) from None
        if trunklength < 0:
            raise ValueError(
                "'trunklength' is negative, which is not allowed because it "
                "would cause poor layout")
        if abs(np.sum(flows)) > self.tolerance:
            _log.info("The sum of the flows is nonzero (%f; patchlabel=%r); "
                      "is the system not at steady state?",
                      np.sum(flows), patchlabel)
        scaled_flows = self.scale * flows
        gain = sum(max(flow, 0) for flow in scaled_flows)
        loss = sum(min(flow, 0) for flow in scaled_flows)
        if prior is not None:
            if prior < 0:
                raise ValueError("The index of the prior diagram is negative")
            if min(connect) < 0:
                raise ValueError(
                    "At least one of the connection indices is negative")
            if prior >= len(self.diagrams):
                raise ValueError(
                    f"The index of the prior diagram is {prior}, but there "
                    f"are only {len(self.diagrams)} other diagrams")
            if connect[0] >= len(self.diagrams[prior].flows):
                raise ValueError(
                    "The connection index to the source diagram is {}, but "
                    "that diagram has only {} flows".format(
                        connect[0], len(self.diagrams[prior].flows)))
            if connect[1] >= n:
                raise ValueError(
                    f"The connection index to this diagram is {connect[1]}, "
                    f"but this diagram has only {n} flows")
            if self.diagrams[prior].angles[connect[0]] is None:
                raise ValueError(
                    f"The connection cannot be made, which may occur if the "
                    f"magnitude of flow {connect[0]} of diagram {prior} is "
                    f"less than the specified tolerance")
            flow_error = (self.diagrams[prior].flows[connect[0]] +
                          flows[connect[1]])
            if abs(flow_error) >= self.tolerance:
                raise ValueError(
                    f"The scaled sum of the connected flows is {flow_error}, "
                    f"which is not within the tolerance ({self.tolerance})")

        # Determine if the flows are inputs.
        are_inputs = [None] * n
        for i, flow in enumerate(flows):
            if flow >= self.tolerance:
                are_inputs[i] = True
            elif flow <= -self.tolerance:
                are_inputs[i] = False
            else:
                _log.info(
                    "The magnitude of flow %d (%f) is below the tolerance "
                    "(%f).\nIt will not be shown, and it cannot be used in a "
                    "connection.", i, flow, self.tolerance)

        # Determine the angles of the arrows (before rotation).
        angles = [None] * n
        for i, (orient, is_input) in enumerate(zip(orientations, are_inputs)):
            if orient == 1:
                if is_input:
                    angles[i] = DOWN
                elif is_input is False:
                    # Be specific since is_input can be None.
                    angles[i] = UP
            elif orient == 0:
                if is_input is not None:
                    angles[i] = RIGHT
            else:
                if orient != -1:
                    raise ValueError(
                        f"The value of orientations[{i}] is {orient}, "
                        f"but it must be -1, 0, or 1")
                if is_input:
                    angles[i] = UP
                elif is_input is False:
                    angles[i] = DOWN

        # Justify the lengths of the paths.
        if np.iterable(pathlengths):
            if len(pathlengths) != n:
                raise ValueError(
                    f"The lengths of 'flows' ({n}) and 'pathlengths' "
                    f"({len(pathlengths)}) are incompatible")
        else:  # Make pathlengths into a list.
            urlength = pathlengths
            ullength = pathlengths
            lrlength = pathlengths
            lllength = pathlengths
            d = dict(RIGHT=pathlengths)
            pathlengths = [d.get(angle, 0) for angle in angles]
            # Determine the lengths of the top-side arrows
            # from the middle outwards.
            for i, (angle, is_input, flow) in enumerate(zip(angles, are_inputs,
                                                            scaled_flows)):
                if angle == DOWN and is_input:
                    pathlengths[i] = ullength
                    ullength += flow
                elif angle == UP and is_input is False:
                    pathlengths[i] = urlength
                    urlength -= flow  # Flow is negative for outputs.
            # Determine the lengths of the bottom-side arrows
            # from the middle outwards.
            for i, (angle, is_input, flow) in enumerate(reversed(list(zip(
                  angles, are_inputs, scaled_flows)))):
                if angle == UP and is_input:
                    pathlengths[n - i - 1] = lllength
                    lllength += flow
                elif angle == DOWN and is_input is False:
                    pathlengths[n - i - 1] = lrlength
                    lrlength -= flow
            # Determine the lengths of the left-side arrows
            # from the bottom upwards.
            has_left_input = False
            for i, (angle, is_input, spec) in enumerate(reversed(list(zip(
                  angles, are_inputs, zip(scaled_flows, pathlengths))))):
                if angle == RIGHT:
                    if is_input:
                        if has_left_input:
                            pathlengths[n - i - 1] = 0
                        else:
                            has_left_input = True
            # Determine the lengths of the right-side arrows
            # from the top downwards.
            has_right_output = False
            for i, (angle, is_input, spec) in enumerate(zip(
                  angles, are_inputs, list(zip(scaled_flows, pathlengths)))):
                if angle == RIGHT:
                    if is_input is False:
                        if has_right_output:
                            pathlengths[i] = 0
                        else:
                            has_right_output = True

        # Begin the subpaths, and smooth the transition if the sum of the flows
        # is nonzero.
        urpath = [(Path.MOVETO, [(self.gap - trunklength / 2.0),  # Upper right
                                 gain / 2.0]),
                  (Path.LINETO, [(self.gap - trunklength / 2.0) / 2.0,
                                 gain / 2.0]),
                  (Path.CURVE4, [(self.gap - trunklength / 2.0) / 8.0,
                                 gain / 2.0]),
                  (Path.CURVE4, [(trunklength / 2.0 - self.gap) / 8.0,
                                 -loss / 2.0]),
                  (Path.LINETO, [(trunklength / 2.0 - self.gap) / 2.0,
                                 -loss / 2.0]),
                  (Path.LINETO, [(trunklength / 2.0 - self.gap),
                                 -loss / 2.0])]
        llpath = [(Path.LINETO, [(trunklength / 2.0 - self.gap),  # Lower left
                                 loss / 2.0]),
                  (Path.LINETO, [(trunklength / 2.0 - self.gap) / 2.0,
                                 loss / 2.0]),
                  (Path.CURVE4, [(trunklength / 2.0 - self.gap) / 8.0,
                                 loss / 2.0]),
                  (Path.CURVE4, [(self.gap - trunklength / 2.0) / 8.0,
                                 -gain / 2.0]),
                  (Path.LINETO, [(self.gap - trunklength / 2.0) / 2.0,
                                 -gain / 2.0]),
                  (Path.LINETO, [(self.gap - trunklength / 2.0),
                                 -gain / 2.0])]
        lrpath = [(Path.LINETO, [(trunklength / 2.0 - self.gap),  # Lower right
                                 loss / 2.0])]
        ulpath = [(Path.LINETO, [self.gap - trunklength / 2.0,  # Upper left
                                 gain / 2.0])]

        # Add the subpaths and assign the locations of the tips and labels.
        tips = np.zeros((n, 2))
        label_locations = np.zeros((n, 2))
        # Add the top-side inputs and outputs from the middle outwards.
        for i, (angle, is_input, spec) in enumerate(zip(
              angles, are_inputs, list(zip(scaled_flows, pathlengths)))):
            if angle == DOWN and is_input:
                tips[i, :], label_locations[i, :] = self._add_input(
                    ulpath, angle, *spec)
            elif angle == UP and is_input is False:
                tips[i, :], label_locations[i, :] = self._add_output(
                    urpath, angle, *spec)
        # Add the bottom-side inputs and outputs from the middle outwards.
        for i, (angle, is_input, spec) in enumerate(reversed(list(zip(
              angles, are_inputs, list(zip(scaled_flows, pathlengths)))))):
            if angle == UP and is_input:
                tip, label_location = self._add_input(llpath, angle, *spec)
                tips[n - i - 1, :] = tip
                label_locations[n - i - 1, :] = label_location
            elif angle == DOWN and is_input is False:
                tip, label_location = self._add_output(lrpath, angle, *spec)
                tips[n - i - 1, :] = tip
                label_locations[n - i - 1, :] = label_location
        # Add the left-side inputs from the bottom upwards.
        has_left_input = False
        for i, (angle, is_input, spec) in enumerate(reversed(list(zip(
              angles, are_inputs, list(zip(scaled_flows, pathlengths)))))):
            if angle == RIGHT and is_input:
                if not has_left_input:
                    # Make sure the lower path extends
                    # at least as far as the upper one.
                    if llpath[-1][1][0] > ulpath[-1][1][0]:
                        llpath.append((Path.LINETO, [ulpath[-1][1][0],
                                                     llpath[-1][1][1]]))
                    has_left_input = True
                tip, label_location = self._add_input(llpath, angle, *spec)
                tips[n - i - 1, :] = tip
                label_locations[n - i - 1, :] = label_location
        # Add the right-side outputs from the top downwards.
        has_right_output = False
        for i, (angle, is_input, spec) in enumerate(zip(
              angles, are_inputs, list(zip(scaled_flows, pathlengths)))):
            if angle == RIGHT and is_input is False:
                if not has_right_output:
                    # Make sure the upper path extends
                    # at least as far as the lower one.
                    if urpath[-1][1][0] < lrpath[-1][1][0]:
                        urpath.append((Path.LINETO, [lrpath[-1][1][0],
                                                     urpath[-1][1][1]]))
                    has_right_output = True
                tips[i, :], label_locations[i, :] = self._add_output(
                    urpath, angle, *spec)
        # Trim any hanging vertices.
        if not has_left_input:
            ulpath.pop()
            llpath.pop()
        if not has_right_output:
            lrpath.pop()
            urpath.pop()

        # Concatenate the subpaths in the correct order (clockwise from top).
        path = (urpath + self._revert(lrpath) + llpath + self._revert(ulpath) +
                [(Path.CLOSEPOLY, urpath[0][1])])

        # Create a patch with the Sankey outline.
        codes, vertices = zip(*path)
        vertices = np.array(vertices)

        def _get_angle(a, r):
            if a is None:
                return None
            else:
                return a + r

        if prior is None:
            if rotation != 0:  # By default, none of this is needed.
                angles = [_get_angle(angle, rotation) for angle in angles]
                rotate = Affine2D().rotate_deg(rotation * 90).transform_affine
                tips = rotate(tips)
                label_locations = rotate(label_locations)
                vertices = rotate(vertices)
            text = self.ax.text(0, 0, s=patchlabel, ha='center', va='center')
        else:
            rotation = (self.diagrams[prior].angles[connect[0]] -
                        angles[connect[1]])
            angles = [_get_angle(angle, rotation) for angle in angles]
            rotate = Affine2D().rotate_deg(rotation * 90).transform_affine
            tips = rotate(tips)
            offset = self.diagrams[prior].tips[connect[0]] - tips[connect[1]]
            translate = Affine2D().translate(*offset).transform_affine
            tips = translate(tips)
            label_locations = translate(rotate(label_locations))
            vertices = translate(rotate(vertices))
            kwds = dict(s=patchlabel, ha='center', va='center')
            text = self.ax.text(*offset, **kwds)
        if mpl.rcParams['_internal.classic_mode']:
            fc = kwargs.pop('fc', kwargs.pop('facecolor', '#bfd1d4'))
            lw = kwargs.pop('lw', kwargs.pop('linewidth', 0.5))
        else:
            fc = kwargs.pop('fc', kwargs.pop('facecolor', None))
            lw = kwargs.pop('lw', kwargs.pop('linewidth', None))
        if fc is None:
            fc = self.ax._get_patches_for_fill.get_next_color()
        patch = PathPatch(Path(vertices, codes), fc=fc, lw=lw, **kwargs)
        self.ax.add_patch(patch)

        # Add the path labels.
        texts = []
        for number, angle, label, location in zip(flows, angles, labels,
                                                  label_locations):
            if label is None or angle is None:
                label = ''
            elif self.unit is not None:
                if isinstance(self.format, str):
                    quantity = self.format % abs(number) + self.unit
                elif callable(self.format):
                    quantity = self.format(number)
                else:
                    raise TypeError(
                        'format must be callable or a format string')
                if label != '':
                    label += "\n"
                label += quantity
            texts.append(self.ax.text(x=location[0], y=location[1],
                                      s=label,
                                      ha='center', va='center'))
        # Text objects are placed even they are empty (as long as the magnitude
        # of the corresponding flow is larger than the tolerance) in case the
        # user wants to provide labels later.

        # Expand the size of the diagram if necessary.
        self.extent = (min(np.min(vertices[:, 0]),
                           np.min(label_locations[:, 0]),
                           self.extent[0]),
                       max(np.max(vertices[:, 0]),
                           np.max(label_locations[:, 0]),
                           self.extent[1]),
                       min(np.min(vertices[:, 1]),
                           np.min(label_locations[:, 1]),
                           self.extent[2]),
                       max(np.max(vertices[:, 1]),
                           np.max(label_locations[:, 1]),
                           self.extent[3]))
        # Include both vertices _and_ label locations in the extents; there are
        # where either could determine the margins (e.g., arrow shoulders).

        # Add this diagram as a subdiagram.
        self.diagrams.append(
            SimpleNamespace(patch=patch, flows=flows, angles=angles, tips=tips,
                            text=text, texts=texts))

        # Allow a daisy-chained call structure (see docstring for the class).
        return self

    def finish(self):
        """
        Adjust the Axes and return a list of information about the Sankey
        subdiagram(s).

        Returns a list of subdiagrams with the following fields:

        ========  =============================================================
        Field     Description
        ========  =============================================================
        *patch*   Sankey outline (a `~matplotlib.patches.PathPatch`).
        *flows*   Flow values (positive for input, negative for output).
        *angles*  List of angles of the arrows [deg/90].
                  For example, if the diagram has not been rotated,
                  an input to the top side has an angle of 3 (DOWN),
                  and an output from the top side has an angle of 1 (UP).
                  If a flow has been skipped (because its magnitude is less
                  than *tolerance*), then its angle will be *None*.
        *tips*    (N, 2)-array of the (x, y) positions of the tips (or "dips")
                  of the flow paths.
                  If the magnitude of a flow is less the *tolerance* of this
                  `Sankey` instance, the flow is skipped and its tip will be at
                  the center of the diagram.
        *text*    `.Text` instance for the diagram label.
        *texts*   List of `.Text` instances for the flow labels.
        ========  =============================================================

        See Also
        --------
        Sankey.add
        """
        self.ax.axis([self.extent[0] - self.margin,
                      self.extent[1] + self.margin,
                      self.extent[2] - self.margin,
                      self.extent[3] + self.margin])
        self.ax.set_aspect('equal', adjustable='datalim')
        return self.diagrams

# === NexusCore/openenv\Lib\site-packages\grpc\_interceptor.py ===
# Copyright 2017 gRPC authors.
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
"""Implementation of gRPC Python interceptors."""

import collections
import sys
import types
from typing import Any, Callable, Optional, Sequence, Tuple, Union

import grpc

from ._typing import DeserializingFunction
from ._typing import DoneCallbackType
from ._typing import MetadataType
from ._typing import RequestIterableType
from ._typing import SerializingFunction


class _ServicePipeline(object):
    interceptors: Tuple[grpc.ServerInterceptor]

    def __init__(self, interceptors: Sequence[grpc.ServerInterceptor]):
        self.interceptors = tuple(interceptors)

    def _continuation(self, thunk: Callable, index: int) -> Callable:
        return lambda context: self._intercept_at(thunk, index, context)

    def _intercept_at(
        self, thunk: Callable, index: int, context: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        if index < len(self.interceptors):
            interceptor = self.interceptors[index]
            thunk = self._continuation(thunk, index + 1)
            return interceptor.intercept_service(thunk, context)
        else:
            return thunk(context)

    def execute(
        self, thunk: Callable, context: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        return self._intercept_at(thunk, 0, context)


def service_pipeline(
    interceptors: Optional[Sequence[grpc.ServerInterceptor]],
) -> Optional[_ServicePipeline]:
    return _ServicePipeline(interceptors) if interceptors else None


class _ClientCallDetails(
    collections.namedtuple(
        "_ClientCallDetails",
        (
            "method",
            "timeout",
            "metadata",
            "credentials",
            "wait_for_ready",
            "compression",
        ),
    ),
    grpc.ClientCallDetails,
):
    pass


def _unwrap_client_call_details(
    call_details: grpc.ClientCallDetails,
    default_details: grpc.ClientCallDetails,
) -> Tuple[
    str, float, MetadataType, grpc.CallCredentials, bool, grpc.Compression
]:
    try:
        method = call_details.method  # pytype: disable=attribute-error
    except AttributeError:
        method = default_details.method  # pytype: disable=attribute-error

    try:
        timeout = call_details.timeout  # pytype: disable=attribute-error
    except AttributeError:
        timeout = default_details.timeout  # pytype: disable=attribute-error

    try:
        metadata = call_details.metadata  # pytype: disable=attribute-error
    except AttributeError:
        metadata = default_details.metadata  # pytype: disable=attribute-error

    try:
        credentials = (
            call_details.credentials
        )  # pytype: disable=attribute-error
    except AttributeError:
        credentials = (
            default_details.credentials
        )  # pytype: disable=attribute-error

    try:
        wait_for_ready = (
            call_details.wait_for_ready
        )  # pytype: disable=attribute-error
    except AttributeError:
        wait_for_ready = (
            default_details.wait_for_ready
        )  # pytype: disable=attribute-error

    try:
        compression = (
            call_details.compression
        )  # pytype: disable=attribute-error
    except AttributeError:
        compression = (
            default_details.compression
        )  # pytype: disable=attribute-error

    return method, timeout, metadata, credentials, wait_for_ready, compression


class _FailureOutcome(
    grpc.RpcError, grpc.Future, grpc.Call
):  # pylint: disable=too-many-ancestors
    _exception: Exception
    _traceback: types.TracebackType

    def __init__(self, exception: Exception, traceback: types.TracebackType):
        super(_FailureOutcome, self).__init__()
        self._exception = exception
        self._traceback = traceback

    def initial_metadata(self) -> Optional[MetadataType]:
        return None

    def trailing_metadata(self) -> Optional[MetadataType]:
        return None

    def code(self) -> Optional[grpc.StatusCode]:
        return grpc.StatusCode.INTERNAL

    def details(self) -> Optional[str]:
        return "Exception raised while intercepting the RPC"

    def cancel(self) -> bool:
        return False

    def cancelled(self) -> bool:
        return False

    def is_active(self) -> bool:
        return False

    def time_remaining(self) -> Optional[float]:
        return None

    def running(self) -> bool:
        return False

    def done(self) -> bool:
        return True

    def result(self, ignored_timeout: Optional[float] = None):
        raise self._exception

    def exception(
        self, ignored_timeout: Optional[float] = None
    ) -> Optional[Exception]:
        return self._exception

    def traceback(
        self, ignored_timeout: Optional[float] = None
    ) -> Optional[types.TracebackType]:
        return self._traceback

    def add_callback(self, unused_callback) -> bool:
        return False

    def add_done_callback(self, fn: DoneCallbackType) -> None:
        fn(self)

    def __iter__(self):
        return self

    def __next__(self):
        raise self._exception

    def next(self):
        return self.__next__()


class _UnaryOutcome(grpc.Call, grpc.Future):
    _response: Any
    _call: grpc.Call

    def __init__(self, response: Any, call: grpc.Call):
        self._response = response
        self._call = call

    def initial_metadata(self) -> Optional[MetadataType]:
        return self._call.initial_metadata()

    def trailing_metadata(self) -> Optional[MetadataType]:
        return self._call.trailing_metadata()

    def code(self) -> Optional[grpc.StatusCode]:
        return self._call.code()

    def details(self) -> Optional[str]:
        return self._call.details()

    def is_active(self) -> bool:
        return self._call.is_active()

    def time_remaining(self) -> Optional[float]:
        return self._call.time_remaining()

    def cancel(self) -> bool:
        return self._call.cancel()

    def add_callback(self, callback) -> bool:
        return self._call.add_callback(callback)

    def cancelled(self) -> bool:
        return False

    def running(self) -> bool:
        return False

    def done(self) -> bool:
        return True

    def result(self, ignored_timeout: Optional[float] = None):
        return self._response

    def exception(self, ignored_timeout: Optional[float] = None):
        return None

    def traceback(self, ignored_timeout: Optional[float] = None):
        return None

    def add_done_callback(self, fn: DoneCallbackType) -> None:
        fn(self)


class _UnaryUnaryMultiCallable(grpc.UnaryUnaryMultiCallable):
    _thunk: Callable
    _method: str
    _interceptor: grpc.UnaryUnaryClientInterceptor

    def __init__(
        self,
        thunk: Callable,
        method: str,
        interceptor: grpc.UnaryUnaryClientInterceptor,
    ):
        self._thunk = thunk
        self._method = method
        self._interceptor = interceptor

    def __call__(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        response, ignored_call = self._with_call(
            request,
            timeout=timeout,
            metadata=metadata,
            credentials=credentials,
            wait_for_ready=wait_for_ready,
            compression=compression,
        )
        return response

    def _with_call(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            try:
                response, call = self._thunk(new_method).with_call(
                    request,
                    timeout=new_timeout,
                    metadata=new_metadata,
                    credentials=new_credentials,
                    wait_for_ready=new_wait_for_ready,
                    compression=new_compression,
                )
                return _UnaryOutcome(response, call)
            except grpc.RpcError as rpc_error:
                return rpc_error
            except Exception as exception:  # pylint:disable=broad-except
                return _FailureOutcome(exception, sys.exc_info()[2])

        call = self._interceptor.intercept_unary_unary(
            continuation, client_call_details, request
        )
        return call.result(), call

    def with_call(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        return self._with_call(
            request,
            timeout=timeout,
            metadata=metadata,
            credentials=credentials,
            wait_for_ready=wait_for_ready,
            compression=compression,
        )

    def future(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            return self._thunk(new_method).future(
                request,
                timeout=new_timeout,
                metadata=new_metadata,
                credentials=new_credentials,
                wait_for_ready=new_wait_for_ready,
                compression=new_compression,
            )

        try:
            return self._interceptor.intercept_unary_unary(
                continuation, client_call_details, request
            )
        except Exception as exception:  # pylint:disable=broad-except
            return _FailureOutcome(exception, sys.exc_info()[2])


class _UnaryStreamMultiCallable(grpc.UnaryStreamMultiCallable):
    _thunk: Callable
    _method: str
    _interceptor: grpc.UnaryStreamClientInterceptor

    def __init__(
        self,
        thunk: Callable,
        method: str,
        interceptor: grpc.UnaryStreamClientInterceptor,
    ):
        self._thunk = thunk
        self._method = method
        self._interceptor = interceptor

    def __call__(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ):
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            return self._thunk(new_method)(
                request,
                timeout=new_timeout,
                metadata=new_metadata,
                credentials=new_credentials,
                wait_for_ready=new_wait_for_ready,
                compression=new_compression,
            )

        try:
            return self._interceptor.intercept_unary_stream(
                continuation, client_call_details, request
            )
        except Exception as exception:  # pylint:disable=broad-except
            return _FailureOutcome(exception, sys.exc_info()[2])


class _StreamUnaryMultiCallable(grpc.StreamUnaryMultiCallable):
    _thunk: Callable
    _method: str
    _interceptor: grpc.StreamUnaryClientInterceptor

    def __init__(
        self,
        thunk: Callable,
        method: str,
        interceptor: grpc.StreamUnaryClientInterceptor,
    ):
        self._thunk = thunk
        self._method = method
        self._interceptor = interceptor

    def __call__(
        self,
        request_iterator: RequestIterableType,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        response, ignored_call = self._with_call(
            request_iterator,
            timeout=timeout,
            metadata=metadata,
            credentials=credentials,
            wait_for_ready=wait_for_ready,
            compression=compression,
        )
        return response

    def _with_call(
        self,
        request_iterator: RequestIterableType,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request_iterator):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            try:
                response, call = self._thunk(new_method).with_call(
                    request_iterator,
                    timeout=new_timeout,
                    metadata=new_metadata,
                    credentials=new_credentials,
                    wait_for_ready=new_wait_for_ready,
                    compression=new_compression,
                )
                return _UnaryOutcome(response, call)
            except grpc.RpcError as rpc_error:
                return rpc_error
            except Exception as exception:  # pylint:disable=broad-except
                return _FailureOutcome(exception, sys.exc_info()[2])

        call = self._interceptor.intercept_stream_unary(
            continuation, client_call_details, request_iterator
        )
        return call.result(), call

    def with_call(
        self,
        request_iterator: RequestIterableType,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        return self._with_call(
            request_iterator,
            timeout=timeout,
            metadata=metadata,
            credentials=credentials,
            wait_for_ready=wait_for_ready,
            compression=compression,
        )

    def future(
        self,
        request_iterator: RequestIterableType,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request_iterator):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            return self._thunk(new_method).future(
                request_iterator,
                timeout=new_timeout,
                metadata=new_metadata,
                credentials=new_credentials,
                wait_for_ready=new_wait_for_ready,
                compression=new_compression,
            )

        try:
            return self._interceptor.intercept_stream_unary(
                continuation, client_call_details, request_iterator
            )
        except Exception as exception:  # pylint:disable=broad-except
            return _FailureOutcome(exception, sys.exc_info()[2])


class _StreamStreamMultiCallable(grpc.StreamStreamMultiCallable):
    _thunk: Callable
    _method: str
    _interceptor: grpc.StreamStreamClientInterceptor

    def __init__(
        self,
        thunk: Callable,
        method: str,
        interceptor: grpc.StreamStreamClientInterceptor,
    ):
        self._thunk = thunk
        self._method = method
        self._interceptor = interceptor

    def __call__(
        self,
        request_iterator: RequestIterableType,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ):
        client_call_details = _ClientCallDetails(
            self._method,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def continuation(new_details, request_iterator):
            (
                new_method,
                new_timeout,
                new_metadata,
                new_credentials,
                new_wait_for_ready,
                new_compression,
            ) = _unwrap_client_call_details(new_details, client_call_details)
            return self._thunk(new_method)(
                request_iterator,
                timeout=new_timeout,
                metadata=new_metadata,
                credentials=new_credentials,
                wait_for_ready=new_wait_for_ready,
                compression=new_compression,
            )

        try:
            return self._interceptor.intercept_stream_stream(
                continuation, client_call_details, request_iterator
            )
        except Exception as exception:  # pylint:disable=broad-except
            return _FailureOutcome(exception, sys.exc_info()[2])


class _Channel(grpc.Channel):
    _channel: grpc.Channel
    _interceptor: Union[
        grpc.UnaryUnaryClientInterceptor,
        grpc.UnaryStreamClientInterceptor,
        grpc.StreamStreamClientInterceptor,
        grpc.StreamUnaryClientInterceptor,
    ]

    def __init__(
        self,
        channel: grpc.Channel,
        interceptor: Union[
            grpc.UnaryUnaryClientInterceptor,
            grpc.UnaryStreamClientInterceptor,
            grpc.StreamStreamClientInterceptor,
            grpc.StreamUnaryClientInterceptor,
        ],
    ):
        self._channel = channel
        self._interceptor = interceptor

    def subscribe(
        self, callback: Callable, try_to_connect: Optional[bool] = False
    ):
        self._channel.subscribe(callback, try_to_connect=try_to_connect)

    def unsubscribe(self, callback: Callable):
        self._channel.unsubscribe(callback)

    # pylint: disable=arguments-differ
    def unary_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.UnaryUnaryMultiCallable:
        # pytype: disable=wrong-arg-count
        thunk = lambda m: self._channel.unary_unary(
            m,
            request_serializer,
            response_deserializer,
            _registered_method,
        )
        # pytype: enable=wrong-arg-count
        if isinstance(self._interceptor, grpc.UnaryUnaryClientInterceptor):
            return _UnaryUnaryMultiCallable(thunk, method, self._interceptor)
        else:
            return thunk(method)

    # pylint: disable=arguments-differ
    def unary_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.UnaryStreamMultiCallable:
        # pytype: disable=wrong-arg-count
        thunk = lambda m: self._channel.unary_stream(
            m,
            request_serializer,
            response_deserializer,
            _registered_method,
        )
        # pytype: enable=wrong-arg-count
        if isinstance(self._interceptor, grpc.UnaryStreamClientInterceptor):
            return _UnaryStreamMultiCallable(thunk, method, self._interceptor)
        else:
            return thunk(method)

    # pylint: disable=arguments-differ
    def stream_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.StreamUnaryMultiCallable:
        # pytype: disable=wrong-arg-count
        thunk = lambda m: self._channel.stream_unary(
            m,
            request_serializer,
            response_deserializer,
            _registered_method,
        )
        # pytype: enable=wrong-arg-count
        if isinstance(self._interceptor, grpc.StreamUnaryClientInterceptor):
            return _StreamUnaryMultiCallable(thunk, method, self._interceptor)
        else:
            return thunk(method)

    # pylint: disable=arguments-differ
    def stream_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.StreamStreamMultiCallable:
        # pytype: disable=wrong-arg-count
        thunk = lambda m: self._channel.stream_stream(
            m,
            request_serializer,
            response_deserializer,
            _registered_method,
        )
        # pytype: enable=wrong-arg-count
        if isinstance(self._interceptor, grpc.StreamStreamClientInterceptor):
            return _StreamStreamMultiCallable(thunk, method, self._interceptor)
        else:
            return thunk(method)

    def _close(self):
        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False

    def close(self):
        self._channel.close()


def intercept_channel(
    channel: grpc.Channel,
    *interceptors: Optional[
        Sequence[
            Union[
                grpc.UnaryUnaryClientInterceptor,
                grpc.UnaryStreamClientInterceptor,
                grpc.StreamStreamClientInterceptor,
                grpc.StreamUnaryClientInterceptor,
            ]
        ]
    ],
) -> grpc.Channel:
    for interceptor in reversed(list(interceptors)):
        if (
            not isinstance(interceptor, grpc.UnaryUnaryClientInterceptor)
            and not isinstance(interceptor, grpc.UnaryStreamClientInterceptor)
            and not isinstance(interceptor, grpc.StreamUnaryClientInterceptor)
            and not isinstance(interceptor, grpc.StreamStreamClientInterceptor)
        ):
            raise TypeError(
                "interceptor must be "
                "grpc.UnaryUnaryClientInterceptor or "
                "grpc.UnaryStreamClientInterceptor or "
                "grpc.StreamUnaryClientInterceptor or "
                "grpc.StreamStreamClientInterceptor or "
            )
        channel = _Channel(channel, interceptor)
    return channel

# === NexusCore/openenv\Lib\site-packages\matplotlib\legend_handler.py ===
"""
Default legend handlers.

.. important::

    This is a low-level legend API, which most end users do not need.

    We recommend that you are familiar with the :ref:`legend guide
    <legend_guide>` before reading this documentation.

Legend handlers are expected to be a callable object with a following
signature::

    legend_handler(legend, orig_handle, fontsize, handlebox)

Where *legend* is the legend itself, *orig_handle* is the original
plot, *fontsize* is the fontsize in pixels, and *handlebox* is an
`.OffsetBox` instance. Within the call, you should create relevant
artists (using relevant properties from the *legend* and/or
*orig_handle*) and add them into the *handlebox*. The artists need to
be scaled according to the *fontsize* (note that the size is in pixels,
i.e., this is dpi-scaled value).

This module includes definition of several legend handler classes
derived from the base class (HandlerBase) with the following method::

    def legend_artist(self, legend, orig_handle, fontsize, handlebox)
"""

from itertools import cycle

import numpy as np

from matplotlib import cbook
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.collections as mcoll


def update_from_first_child(tgt, src):
    first_child = next(iter(src.get_children()), None)
    if first_child is not None:
        tgt.update_from(first_child)


class HandlerBase:
    """
    A base class for default legend handlers.

    The derived classes are meant to override *create_artists* method, which
    has the following signature::

      def create_artists(self, legend, orig_handle,
                         xdescent, ydescent, width, height, fontsize,
                         trans):

    The overridden method needs to create artists of the given
    transform that fits in the given dimension (xdescent, ydescent,
    width, height) that are scaled by fontsize if necessary.

    """
    def __init__(self, xpad=0., ypad=0., update_func=None):
        """
        Parameters
        ----------
        xpad : float, optional
            Padding in x-direction.
        ypad : float, optional
            Padding in y-direction.
        update_func : callable, optional
            Function for updating the legend handler properties from another
            legend handler, used by `~HandlerBase.update_prop`.
        """
        self._xpad, self._ypad = xpad, ypad
        self._update_prop_func = update_func

    def _update_prop(self, legend_handle, orig_handle):
        if self._update_prop_func is None:
            self._default_update_prop(legend_handle, orig_handle)
        else:
            self._update_prop_func(legend_handle, orig_handle)

    def _default_update_prop(self, legend_handle, orig_handle):
        legend_handle.update_from(orig_handle)

    def update_prop(self, legend_handle, orig_handle, legend):

        self._update_prop(legend_handle, orig_handle)

        legend._set_artist_props(legend_handle)
        legend_handle.set_clip_box(None)
        legend_handle.set_clip_path(None)

    def adjust_drawing_area(self, legend, orig_handle,
                            xdescent, ydescent, width, height, fontsize,
                            ):
        xdescent = xdescent - self._xpad * fontsize
        ydescent = ydescent - self._ypad * fontsize
        width = width - self._xpad * fontsize
        height = height - self._ypad * fontsize
        return xdescent, ydescent, width, height

    def legend_artist(self, legend, orig_handle,
                      fontsize, handlebox):
        """
        Return the artist that this HandlerBase generates for the given
        original artist/handle.

        Parameters
        ----------
        legend : `~matplotlib.legend.Legend`
            The legend for which these legend artists are being created.
        orig_handle : :class:`matplotlib.artist.Artist` or similar
            The object for which these legend artists are being created.
        fontsize : int
            The fontsize in pixels. The artists being created should
            be scaled according to the given fontsize.
        handlebox : `~matplotlib.offsetbox.OffsetBox`
            The box which has been created to hold this legend entry's
            artists. Artists created in the `legend_artist` method must
            be added to this handlebox inside this method.

        """
        xdescent, ydescent, width, height = self.adjust_drawing_area(
                 legend, orig_handle,
                 handlebox.xdescent, handlebox.ydescent,
                 handlebox.width, handlebox.height,
                 fontsize)
        artists = self.create_artists(legend, orig_handle,
                                      xdescent, ydescent, width, height,
                                      fontsize, handlebox.get_transform())

        # create_artists will return a list of artists.
        for a in artists:
            handlebox.add_artist(a)

        # we only return the first artist
        return artists[0]

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        """
        Return the legend artists generated.

        Parameters
        ----------
        legend : `~matplotlib.legend.Legend`
            The legend for which these legend artists are being created.
        orig_handle : `~matplotlib.artist.Artist` or similar
            The object for which these legend artists are being created.
        xdescent, ydescent, width, height : int
            The rectangle (*xdescent*, *ydescent*, *width*, *height*) that the
            legend artists being created should fit within.
        fontsize : int
            The fontsize in pixels. The legend artists being created should
            be scaled according to the given fontsize.
        trans : `~matplotlib.transforms.Transform`
            The transform that is applied to the legend artists being created.
            Typically from unit coordinates in the handler box to screen
            coordinates.
        """
        raise NotImplementedError('Derived must override')


class HandlerNpoints(HandlerBase):
    """
    A legend handler that shows *numpoints* points in the legend entry.
    """

    def __init__(self, marker_pad=0.3, numpoints=None, **kwargs):
        """
        Parameters
        ----------
        marker_pad : float
            Padding between points in legend entry.
        numpoints : int
            Number of points to show in legend entry.
        **kwargs
            Keyword arguments forwarded to `.HandlerBase`.
        """
        super().__init__(**kwargs)

        self._numpoints = numpoints
        self._marker_pad = marker_pad

    def get_numpoints(self, legend):
        if self._numpoints is None:
            return legend.numpoints
        else:
            return self._numpoints

    def get_xdata(self, legend, xdescent, ydescent, width, height, fontsize):
        numpoints = self.get_numpoints(legend)
        if numpoints > 1:
            # we put some pad here to compensate the size of the marker
            pad = self._marker_pad * fontsize
            xdata = np.linspace(-xdescent + pad,
                                -xdescent + width - pad,
                                numpoints)
            xdata_marker = xdata
        else:
            xdata = [-xdescent, -xdescent + width]
            xdata_marker = [-xdescent + 0.5 * width]
        return xdata, xdata_marker


class HandlerNpointsYoffsets(HandlerNpoints):
    """
    A legend handler that shows *numpoints* in the legend, and allows them to
    be individually offset in the y-direction.
    """

    def __init__(self, numpoints=None, yoffsets=None, **kwargs):
        """
        Parameters
        ----------
        numpoints : int
            Number of points to show in legend entry.
        yoffsets : array of floats
            Length *numpoints* list of y offsets for each point in
            legend entry.
        **kwargs
            Keyword arguments forwarded to `.HandlerNpoints`.
        """
        super().__init__(numpoints=numpoints, **kwargs)
        self._yoffsets = yoffsets

    def get_ydata(self, legend, xdescent, ydescent, width, height, fontsize):
        if self._yoffsets is None:
            ydata = height * legend._scatteryoffsets
        else:
            ydata = height * np.asarray(self._yoffsets)

        return ydata


class HandlerLine2DCompound(HandlerNpoints):
    """
    Original handler for `.Line2D` instances, that relies on combining
    a line-only with a marker-only artist.  May be deprecated in the future.
    """

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)

        ydata = np.full_like(xdata, ((height - ydescent) / 2))
        legline = Line2D(xdata, ydata)

        self.update_prop(legline, orig_handle, legend)
        legline.set_drawstyle('default')
        legline.set_marker("")

        legline_marker = Line2D(xdata_marker, ydata[:len(xdata_marker)])
        self.update_prop(legline_marker, orig_handle, legend)
        legline_marker.set_linestyle('None')
        if legend.markerscale != 1:
            newsz = legline_marker.get_markersize() * legend.markerscale
            legline_marker.set_markersize(newsz)
        # we don't want to add this to the return list because
        # the texts and handles are assumed to be in one-to-one
        # correspondence.
        legline._legmarker = legline_marker

        legline.set_transform(trans)
        legline_marker.set_transform(trans)

        return [legline, legline_marker]


class HandlerLine2D(HandlerNpoints):
    """
    Handler for `.Line2D` instances.

    See Also
    --------
    HandlerLine2DCompound : An earlier handler implementation, which used one
                            artist for the line and another for the marker(s).
    """

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)

        markevery = None
        if self.get_numpoints(legend) == 1:
            # Special case: one wants a single marker in the center
            # and a line that extends on both sides. One will use a
            # 3 points line, but only mark the #1 (i.e. middle) point.
            xdata = np.linspace(xdata[0], xdata[-1], 3)
            markevery = [1]

        ydata = np.full_like(xdata, (height - ydescent) / 2)
        legline = Line2D(xdata, ydata, markevery=markevery)

        self.update_prop(legline, orig_handle, legend)

        if legend.markerscale != 1:
            newsz = legline.get_markersize() * legend.markerscale
            legline.set_markersize(newsz)

        legline.set_transform(trans)

        return [legline]


class HandlerPatch(HandlerBase):
    """
    Handler for `.Patch` instances.
    """

    def __init__(self, patch_func=None, **kwargs):
        """
        Parameters
        ----------
        patch_func : callable, optional
            The function that creates the legend key artist.
            *patch_func* should have the signature::

                def patch_func(legend=legend, orig_handle=orig_handle,
                               xdescent=xdescent, ydescent=ydescent,
                               width=width, height=height, fontsize=fontsize)

            Subsequently, the created artist will have its ``update_prop``
            method called and the appropriate transform will be applied.

        **kwargs
            Keyword arguments forwarded to `.HandlerBase`.
        """
        super().__init__(**kwargs)
        self._patch_func = patch_func

    def _create_patch(self, legend, orig_handle,
                      xdescent, ydescent, width, height, fontsize):
        if self._patch_func is None:
            p = Rectangle(xy=(-xdescent, -ydescent),
                          width=width, height=height)
        else:
            p = self._patch_func(legend=legend, orig_handle=orig_handle,
                                 xdescent=xdescent, ydescent=ydescent,
                                 width=width, height=height, fontsize=fontsize)
        return p

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # docstring inherited
        p = self._create_patch(legend, orig_handle,
                               xdescent, ydescent, width, height, fontsize)
        self.update_prop(p, orig_handle, legend)
        p.set_transform(trans)
        return [p]


class HandlerStepPatch(HandlerBase):
    """
    Handler for `~.matplotlib.patches.StepPatch` instances.
    """

    @staticmethod
    def _create_patch(orig_handle, xdescent, ydescent, width, height):
        return Rectangle(xy=(-xdescent, -ydescent), width=width,
                         height=height, color=orig_handle.get_facecolor())

    @staticmethod
    def _create_line(orig_handle, width, height):
        # Unfilled StepPatch should show as a line
        legline = Line2D([0, width], [height/2, height/2],
                         color=orig_handle.get_edgecolor(),
                         linestyle=orig_handle.get_linestyle(),
                         linewidth=orig_handle.get_linewidth(),
                         )

        # Overwrite manually because patch and line properties don't mix
        legline.set_drawstyle('default')
        legline.set_marker("")
        return legline

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # docstring inherited
        if orig_handle.get_fill() or (orig_handle.get_hatch() is not None):
            p = self._create_patch(orig_handle, xdescent, ydescent, width,
                                   height)
            self.update_prop(p, orig_handle, legend)
        else:
            p = self._create_line(orig_handle, width, height)
        p.set_transform(trans)
        return [p]


class HandlerLineCollection(HandlerLine2D):
    """
    Handler for `.LineCollection` instances.
    """
    def get_numpoints(self, legend):
        if self._numpoints is None:
            return legend.scatterpoints
        else:
            return self._numpoints

    def _default_update_prop(self, legend_handle, orig_handle):
        lw = orig_handle.get_linewidths()[0]
        dashes = orig_handle._us_linestyles[0]
        color = orig_handle.get_colors()[0]
        legend_handle.set_color(color)
        legend_handle.set_linestyle(dashes)
        legend_handle.set_linewidth(lw)

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # docstring inherited
        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)
        ydata = np.full_like(xdata, (height - ydescent) / 2)
        legline = Line2D(xdata, ydata)

        self.update_prop(legline, orig_handle, legend)
        legline.set_transform(trans)

        return [legline]


class HandlerRegularPolyCollection(HandlerNpointsYoffsets):
    r"""Handler for `.RegularPolyCollection`\s."""

    def __init__(self, yoffsets=None, sizes=None, **kwargs):
        super().__init__(yoffsets=yoffsets, **kwargs)

        self._sizes = sizes

    def get_numpoints(self, legend):
        if self._numpoints is None:
            return legend.scatterpoints
        else:
            return self._numpoints

    def get_sizes(self, legend, orig_handle,
                  xdescent, ydescent, width, height, fontsize):
        if self._sizes is None:
            handle_sizes = orig_handle.get_sizes()
            if not len(handle_sizes):
                handle_sizes = [1]
            size_max = max(handle_sizes) * legend.markerscale ** 2
            size_min = min(handle_sizes) * legend.markerscale ** 2

            numpoints = self.get_numpoints(legend)
            if numpoints < 4:
                sizes = [.5 * (size_max + size_min), size_max,
                         size_min][:numpoints]
            else:
                rng = (size_max - size_min)
                sizes = rng * np.linspace(0, 1, numpoints) + size_min
        else:
            sizes = self._sizes

        return sizes

    def update_prop(self, legend_handle, orig_handle, legend):

        self._update_prop(legend_handle, orig_handle)

        legend_handle.set_figure(legend.get_figure(root=False))
        # legend._set_artist_props(legend_handle)
        legend_handle.set_clip_box(None)
        legend_handle.set_clip_path(None)

    def create_collection(self, orig_handle, sizes, offsets, offset_transform):
        return type(orig_handle)(
            orig_handle.get_numsides(),
            rotation=orig_handle.get_rotation(), sizes=sizes,
            offsets=offsets, offset_transform=offset_transform,
        )

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)

        ydata = self.get_ydata(legend, xdescent, ydescent,
                               width, height, fontsize)

        sizes = self.get_sizes(legend, orig_handle, xdescent, ydescent,
                               width, height, fontsize)

        p = self.create_collection(
            orig_handle, sizes,
            offsets=list(zip(xdata_marker, ydata)), offset_transform=trans)

        self.update_prop(p, orig_handle, legend)
        p.set_offset_transform(trans)
        return [p]


class HandlerPathCollection(HandlerRegularPolyCollection):
    r"""Handler for `.PathCollection`\s, which are used by `~.Axes.scatter`."""

    def create_collection(self, orig_handle, sizes, offsets, offset_transform):
        return type(orig_handle)(
            [orig_handle.get_paths()[0]], sizes=sizes,
            offsets=offsets, offset_transform=offset_transform,
        )


class HandlerCircleCollection(HandlerRegularPolyCollection):
    r"""Handler for `.CircleCollection`\s."""

    def create_collection(self, orig_handle, sizes, offsets, offset_transform):
        return type(orig_handle)(
            sizes, offsets=offsets, offset_transform=offset_transform)


class HandlerErrorbar(HandlerLine2D):
    """Handler for Errorbars."""

    def __init__(self, xerr_size=0.5, yerr_size=None,
                 marker_pad=0.3, numpoints=None, **kwargs):

        self._xerr_size = xerr_size
        self._yerr_size = yerr_size

        super().__init__(marker_pad=marker_pad, numpoints=numpoints, **kwargs)

    def get_err_size(self, legend, xdescent, ydescent,
                     width, height, fontsize):
        xerr_size = self._xerr_size * fontsize

        if self._yerr_size is None:
            yerr_size = xerr_size
        else:
            yerr_size = self._yerr_size * fontsize

        return xerr_size, yerr_size

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        plotlines, caplines, barlinecols = orig_handle

        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)

        ydata = np.full_like(xdata, (height - ydescent) / 2)
        legline = Line2D(xdata, ydata)

        xdata_marker = np.asarray(xdata_marker)
        ydata_marker = np.asarray(ydata[:len(xdata_marker)])

        xerr_size, yerr_size = self.get_err_size(legend, xdescent, ydescent,
                                                 width, height, fontsize)

        legline_marker = Line2D(xdata_marker, ydata_marker)

        # when plotlines are None (only errorbars are drawn), we just
        # make legline invisible.
        if plotlines is None:
            legline.set_visible(False)
            legline_marker.set_visible(False)
        else:
            self.update_prop(legline, plotlines, legend)

            legline.set_drawstyle('default')
            legline.set_marker('none')

            self.update_prop(legline_marker, plotlines, legend)
            legline_marker.set_linestyle('None')

            if legend.markerscale != 1:
                newsz = legline_marker.get_markersize() * legend.markerscale
                legline_marker.set_markersize(newsz)

        handle_barlinecols = []
        handle_caplines = []

        if orig_handle.has_xerr:
            verts = [((x - xerr_size, y), (x + xerr_size, y))
                     for x, y in zip(xdata_marker, ydata_marker)]
            coll = mcoll.LineCollection(verts)
            self.update_prop(coll, barlinecols[0], legend)
            handle_barlinecols.append(coll)

            if caplines:
                capline_left = Line2D(xdata_marker - xerr_size, ydata_marker)
                capline_right = Line2D(xdata_marker + xerr_size, ydata_marker)
                self.update_prop(capline_left, caplines[0], legend)
                self.update_prop(capline_right, caplines[0], legend)
                capline_left.set_marker("|")
                capline_right.set_marker("|")

                handle_caplines.append(capline_left)
                handle_caplines.append(capline_right)

        if orig_handle.has_yerr:
            verts = [((x, y - yerr_size), (x, y + yerr_size))
                     for x, y in zip(xdata_marker, ydata_marker)]
            coll = mcoll.LineCollection(verts)
            self.update_prop(coll, barlinecols[0], legend)
            handle_barlinecols.append(coll)

            if caplines:
                capline_left = Line2D(xdata_marker, ydata_marker - yerr_size)
                capline_right = Line2D(xdata_marker, ydata_marker + yerr_size)
                self.update_prop(capline_left, caplines[0], legend)
                self.update_prop(capline_right, caplines[0], legend)
                capline_left.set_marker("_")
                capline_right.set_marker("_")

                handle_caplines.append(capline_left)
                handle_caplines.append(capline_right)

        artists = [
            *handle_barlinecols, *handle_caplines, legline, legline_marker,
        ]
        for artist in artists:
            artist.set_transform(trans)
        return artists


class HandlerStem(HandlerNpointsYoffsets):
    """
    Handler for plots produced by `~.Axes.stem`.
    """

    def __init__(self, marker_pad=0.3, numpoints=None,
                 bottom=None, yoffsets=None, **kwargs):
        """
        Parameters
        ----------
        marker_pad : float, default: 0.3
            Padding between points in legend entry.
        numpoints : int, optional
            Number of points to show in legend entry.
        bottom : float, optional

        yoffsets : array of floats, optional
            Length *numpoints* list of y offsets for each point in
            legend entry.
        **kwargs
            Keyword arguments forwarded to `.HandlerNpointsYoffsets`.
        """
        super().__init__(marker_pad=marker_pad, numpoints=numpoints,
                         yoffsets=yoffsets, **kwargs)
        self._bottom = bottom

    def get_ydata(self, legend, xdescent, ydescent, width, height, fontsize):
        if self._yoffsets is None:
            ydata = height * (0.5 * legend._scatteryoffsets + 0.5)
        else:
            ydata = height * np.asarray(self._yoffsets)

        return ydata

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        markerline, stemlines, baseline = orig_handle
        # Check to see if the stemcontainer is storing lines as a list or a
        # LineCollection. Eventually using a list will be removed, and this
        # logic can also be removed.
        using_linecoll = isinstance(stemlines, mcoll.LineCollection)

        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)

        ydata = self.get_ydata(legend, xdescent, ydescent,
                               width, height, fontsize)

        if self._bottom is None:
            bottom = 0.
        else:
            bottom = self._bottom

        leg_markerline = Line2D(xdata_marker, ydata[:len(xdata_marker)])
        self.update_prop(leg_markerline, markerline, legend)

        leg_stemlines = [Line2D([x, x], [bottom, y])
                         for x, y in zip(xdata_marker, ydata)]

        if using_linecoll:
            # change the function used by update_prop() from the default
            # to one that handles LineCollection
            with cbook._setattr_cm(
                    self, _update_prop_func=self._copy_collection_props):
                for line in leg_stemlines:
                    self.update_prop(line, stemlines, legend)

        else:
            for lm, m in zip(leg_stemlines, stemlines):
                self.update_prop(lm, m, legend)

        leg_baseline = Line2D([np.min(xdata), np.max(xdata)],
                              [bottom, bottom])
        self.update_prop(leg_baseline, baseline, legend)

        artists = [*leg_stemlines, leg_baseline, leg_markerline]
        for artist in artists:
            artist.set_transform(trans)
        return artists

    def _copy_collection_props(self, legend_handle, orig_handle):
        """
        Copy properties from the `.LineCollection` *orig_handle* to the
        `.Line2D` *legend_handle*.
        """
        legend_handle.set_color(orig_handle.get_color()[0])
        legend_handle.set_linestyle(orig_handle.get_linestyle()[0])


class HandlerTuple(HandlerBase):
    """
    Handler for Tuple.
    """

    def __init__(self, ndivide=1, pad=None, **kwargs):
        """
        Parameters
        ----------
        ndivide : int or None, default: 1
            The number of sections to divide the legend area into.  If None,
            use the length of the input tuple.
        pad : float, default: :rc:`legend.borderpad`
            Padding in units of fraction of font size.
        **kwargs
            Keyword arguments forwarded to `.HandlerBase`.
        """
        self._ndivide = ndivide
        self._pad = pad
        super().__init__(**kwargs)

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        # docstring inherited
        handler_map = legend.get_legend_handler_map()

        if self._ndivide is None:
            ndivide = len(orig_handle)
        else:
            ndivide = self._ndivide

        if self._pad is None:
            pad = legend.borderpad * fontsize
        else:
            pad = self._pad * fontsize

        if ndivide > 1:
            width = (width - pad * (ndivide - 1)) / ndivide

        xds_cycle = cycle(xdescent - (width + pad) * np.arange(ndivide))

        a_list = []
        for handle1 in orig_handle:
            handler = legend.get_legend_handler(handler_map, handle1)
            _a_list = handler.create_artists(
                legend, handle1,
                next(xds_cycle), ydescent, width, height, fontsize, trans)
            a_list.extend(_a_list)

        return a_list


class HandlerPolyCollection(HandlerBase):
    """
    Handler for `.PolyCollection` used in `~.Axes.fill_between` and
    `~.Axes.stackplot`.
    """
    def _update_prop(self, legend_handle, orig_handle):
        def first_color(colors):
            if colors.size == 0:
                return (0, 0, 0, 0)
            return tuple(colors[0])

        def get_first(prop_array):
            if len(prop_array):
                return prop_array[0]
            else:
                return None

        # orig_handle is a PolyCollection and legend_handle is a Patch.
        # Directly set Patch color attributes (must be RGBA tuples).
        legend_handle._facecolor = first_color(orig_handle.get_facecolor())
        legend_handle._edgecolor = first_color(orig_handle.get_edgecolor())
        legend_handle._original_facecolor = orig_handle._original_facecolor
        legend_handle._original_edgecolor = orig_handle._original_edgecolor
        legend_handle._fill = orig_handle.get_fill()
        legend_handle._hatch = orig_handle.get_hatch()
        # Hatch color is anomalous in having no getters and setters.
        legend_handle._hatch_color = orig_handle._hatch_color
        # Setters are fine for the remaining attributes.
        legend_handle.set_linewidth(get_first(orig_handle.get_linewidths()))
        legend_handle.set_linestyle(get_first(orig_handle.get_linestyles()))
        legend_handle.set_transform(get_first(orig_handle.get_transforms()))
        legend_handle.set_figure(orig_handle.get_figure())
        # Alpha is already taken into account by the color attributes.

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # docstring inherited
        p = Rectangle(xy=(-xdescent, -ydescent),
                      width=width, height=height)
        self.update_prop(p, orig_handle, legend)
        p.set_transform(trans)
        return [p]

# === NexusCore/openenv\Lib\site-packages\sortedcontainers\sorteddict.py ===
"""Sorted Dict
==============

:doc:`Sorted Containers<index>` is an Apache2 licensed Python sorted
collections library, written in pure-Python, and fast as C-extensions. The
:doc:`introduction<introduction>` is the best way to get started.

Sorted dict implementations:

.. currentmodule:: sortedcontainers

* :class:`SortedDict`
* :class:`SortedKeysView`
* :class:`SortedItemsView`
* :class:`SortedValuesView`

"""

import sys
import warnings

from itertools import chain

from .sortedlist import SortedList, recursive_repr
from .sortedset import SortedSet

###############################################################################
# BEGIN Python 2/3 Shims
###############################################################################

try:
    from collections.abc import (
        ItemsView, KeysView, Mapping, ValuesView, Sequence
    )
except ImportError:
    from collections import ItemsView, KeysView, Mapping, ValuesView, Sequence

###############################################################################
# END Python 2/3 Shims
###############################################################################


class SortedDict(dict):
    """Sorted dict is a sorted mutable mapping.

    Sorted dict keys are maintained in sorted order. The design of sorted dict
    is simple: sorted dict inherits from dict to store items and maintains a
    sorted list of keys.

    Sorted dict keys must be hashable and comparable. The hash and total
    ordering of keys must not change while they are stored in the sorted dict.

    Mutable mapping methods:

    * :func:`SortedDict.__getitem__` (inherited from dict)
    * :func:`SortedDict.__setitem__`
    * :func:`SortedDict.__delitem__`
    * :func:`SortedDict.__iter__`
    * :func:`SortedDict.__len__` (inherited from dict)

    Methods for adding items:

    * :func:`SortedDict.setdefault`
    * :func:`SortedDict.update`

    Methods for removing items:

    * :func:`SortedDict.clear`
    * :func:`SortedDict.pop`
    * :func:`SortedDict.popitem`

    Methods for looking up items:

    * :func:`SortedDict.__contains__` (inherited from dict)
    * :func:`SortedDict.get` (inherited from dict)
    * :func:`SortedDict.peekitem`

    Methods for views:

    * :func:`SortedDict.keys`
    * :func:`SortedDict.items`
    * :func:`SortedDict.values`

    Methods for miscellany:

    * :func:`SortedDict.copy`
    * :func:`SortedDict.fromkeys`
    * :func:`SortedDict.__reversed__`
    * :func:`SortedDict.__eq__` (inherited from dict)
    * :func:`SortedDict.__ne__` (inherited from dict)
    * :func:`SortedDict.__repr__`
    * :func:`SortedDict._check`

    Sorted list methods available (applies to keys):

    * :func:`SortedList.bisect_left`
    * :func:`SortedList.bisect_right`
    * :func:`SortedList.count`
    * :func:`SortedList.index`
    * :func:`SortedList.irange`
    * :func:`SortedList.islice`
    * :func:`SortedList._reset`

    Additional sorted list methods available, if key-function used:

    * :func:`SortedKeyList.bisect_key_left`
    * :func:`SortedKeyList.bisect_key_right`
    * :func:`SortedKeyList.irange_key`

    Sorted dicts may only be compared for equality and inequality.

    """
    def __init__(self, *args, **kwargs):
        """Initialize sorted dict instance.

        Optional key-function argument defines a callable that, like the `key`
        argument to the built-in `sorted` function, extracts a comparison key
        from each dictionary key. If no function is specified, the default
        compares the dictionary keys directly. The key-function argument must
        be provided as a positional argument and must come before all other
        arguments.

        Optional iterable argument provides an initial sequence of pairs to
        initialize the sorted dict. Each pair in the sequence defines the key
        and corresponding value. If a key is seen more than once, the last
        value associated with it is stored in the new sorted dict.

        Optional mapping argument provides an initial mapping of items to
        initialize the sorted dict.

        If keyword arguments are given, the keywords themselves, with their
        associated values, are added as items to the dictionary. If a key is
        specified both in the positional argument and as a keyword argument,
        the value associated with the keyword is stored in the
        sorted dict.

        Sorted dict keys must be hashable, per the requirement for Python's
        dictionaries. Keys (or the result of the key-function) must also be
        comparable, per the requirement for sorted lists.

        >>> d = {'alpha': 1, 'beta': 2}
        >>> SortedDict([('alpha', 1), ('beta', 2)]) == d
        True
        >>> SortedDict({'alpha': 1, 'beta': 2}) == d
        True
        >>> SortedDict(alpha=1, beta=2) == d
        True

        """
        if args and (args[0] is None or callable(args[0])):
            _key = self._key = args[0]
            args = args[1:]
        else:
            _key = self._key = None

        self._list = SortedList(key=_key)

        # Reaching through ``self._list`` repeatedly adds unnecessary overhead
        # so cache references to sorted list methods.

        _list = self._list
        self._list_add = _list.add
        self._list_clear = _list.clear
        self._list_iter = _list.__iter__
        self._list_reversed = _list.__reversed__
        self._list_pop = _list.pop
        self._list_remove = _list.remove
        self._list_update = _list.update

        # Expose some sorted list methods publicly.

        self.bisect_left = _list.bisect_left
        self.bisect = _list.bisect_right
        self.bisect_right = _list.bisect_right
        self.index = _list.index
        self.irange = _list.irange
        self.islice = _list.islice
        self._reset = _list._reset

        if _key is not None:
            self.bisect_key_left = _list.bisect_key_left
            self.bisect_key_right = _list.bisect_key_right
            self.bisect_key = _list.bisect_key
            self.irange_key = _list.irange_key

        self._update(*args, **kwargs)


    @property
    def key(self):
        """Function used to extract comparison key from keys.

        Sorted dict compares keys directly when the key function is none.

        """
        return self._key


    @property
    def iloc(self):
        """Cached reference of sorted keys view.

        Deprecated in version 2 of Sorted Containers. Use
        :func:`SortedDict.keys` instead.

        """
        # pylint: disable=attribute-defined-outside-init
        try:
            return self._iloc
        except AttributeError:
            warnings.warn(
                'sorted_dict.iloc is deprecated.'
                ' Use SortedDict.keys() instead.',
                DeprecationWarning,
                stacklevel=2,
            )
            _iloc = self._iloc = SortedKeysView(self)
            return _iloc


    def clear(self):

        """Remove all items from sorted dict.

        Runtime complexity: `O(n)`

        """
        dict.clear(self)
        self._list_clear()


    def __delitem__(self, key):
        """Remove item from sorted dict identified by `key`.

        ``sd.__delitem__(key)`` <==> ``del sd[key]``

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> del sd['b']
        >>> sd
        SortedDict({'a': 1, 'c': 3})
        >>> del sd['z']
        Traceback (most recent call last):
          ...
        KeyError: 'z'

        :param key: `key` for item lookup
        :raises KeyError: if key not found

        """
        dict.__delitem__(self, key)
        self._list_remove(key)


    def __iter__(self):
        """Return an iterator over the keys of the sorted dict.

        ``sd.__iter__()`` <==> ``iter(sd)``

        Iterating the sorted dict while adding or deleting items may raise a
        :exc:`RuntimeError` or fail to iterate over all keys.

        """
        return self._list_iter()


    def __reversed__(self):
        """Return a reverse iterator over the keys of the sorted dict.

        ``sd.__reversed__()`` <==> ``reversed(sd)``

        Iterating the sorted dict while adding or deleting items may raise a
        :exc:`RuntimeError` or fail to iterate over all keys.

        """
        return self._list_reversed()


    def __setitem__(self, key, value):
        """Store item in sorted dict with `key` and corresponding `value`.

        ``sd.__setitem__(key, value)`` <==> ``sd[key] = value``

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict()
        >>> sd['c'] = 3
        >>> sd['a'] = 1
        >>> sd['b'] = 2
        >>> sd
        SortedDict({'a': 1, 'b': 2, 'c': 3})

        :param key: key for item
        :param value: value for item

        """
        if key not in self:
            self._list_add(key)
        dict.__setitem__(self, key, value)

    _setitem = __setitem__


    def __or__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        items = chain(self.items(), other.items())
        return self.__class__(self._key, items)


    def __ror__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        items = chain(other.items(), self.items())
        return self.__class__(self._key, items)


    def __ior__(self, other):
        self._update(other)
        return self


    def copy(self):
        """Return a shallow copy of the sorted dict.

        Runtime complexity: `O(n)`

        :return: new sorted dict

        """
        return self.__class__(self._key, self.items())

    __copy__ = copy


    @classmethod
    def fromkeys(cls, iterable, value=None):
        """Return a new sorted dict initailized from `iterable` and `value`.

        Items in the sorted dict have keys from `iterable` and values equal to
        `value`.

        Runtime complexity: `O(n*log(n))`

        :return: new sorted dict

        """
        return cls((key, value) for key in iterable)


    def keys(self):
        """Return new sorted keys view of the sorted dict's keys.

        See :class:`SortedKeysView` for details.

        :return: new sorted keys view

        """
        return SortedKeysView(self)


    def items(self):
        """Return new sorted items view of the sorted dict's items.

        See :class:`SortedItemsView` for details.

        :return: new sorted items view

        """
        return SortedItemsView(self)


    def values(self):
        """Return new sorted values view of the sorted dict's values.

        See :class:`SortedValuesView` for details.

        :return: new sorted values view

        """
        return SortedValuesView(self)


    if sys.hexversion < 0x03000000:
        def __make_raise_attributeerror(original, alternate):
            # pylint: disable=no-self-argument
            message = (
                'SortedDict.{original}() is not implemented.'
                ' Use SortedDict.{alternate}() instead.'
            ).format(original=original, alternate=alternate)
            def method(self):
                # pylint: disable=missing-docstring,unused-argument
                raise AttributeError(message)
            method.__name__ = original  # pylint: disable=non-str-assignment-to-dunder-name
            method.__doc__ = message
            return property(method)

        iteritems = __make_raise_attributeerror('iteritems', 'items')
        iterkeys = __make_raise_attributeerror('iterkeys', 'keys')
        itervalues = __make_raise_attributeerror('itervalues', 'values')
        viewitems = __make_raise_attributeerror('viewitems', 'items')
        viewkeys = __make_raise_attributeerror('viewkeys', 'keys')
        viewvalues = __make_raise_attributeerror('viewvalues', 'values')


    class _NotGiven(object):
        # pylint: disable=too-few-public-methods
        def __repr__(self):
            return '<not-given>'

    __not_given = _NotGiven()

    def pop(self, key, default=__not_given):
        """Remove and return value for item identified by `key`.

        If the `key` is not found then return `default` if given. If `default`
        is not given then raise :exc:`KeyError`.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> sd.pop('c')
        3
        >>> sd.pop('z', 26)
        26
        >>> sd.pop('y')
        Traceback (most recent call last):
          ...
        KeyError: 'y'

        :param key: `key` for item
        :param default: `default` value if key not found (optional)
        :return: value for item
        :raises KeyError: if `key` not found and `default` not given

        """
        if key in self:
            self._list_remove(key)
            return dict.pop(self, key)
        else:
            if default is self.__not_given:
                raise KeyError(key)
            return default


    def popitem(self, index=-1):
        """Remove and return ``(key, value)`` pair at `index` from sorted dict.

        Optional argument `index` defaults to -1, the last item in the sorted
        dict. Specify ``index=0`` for the first item in the sorted dict.

        If the sorted dict is empty, raises :exc:`KeyError`.

        If the `index` is out of range, raises :exc:`IndexError`.

        Runtime complexity: `O(log(n))`

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> sd.popitem()
        ('c', 3)
        >>> sd.popitem(0)
        ('a', 1)
        >>> sd.popitem(100)
        Traceback (most recent call last):
          ...
        IndexError: list index out of range

        :param int index: `index` of item (default -1)
        :return: key and value pair
        :raises KeyError: if sorted dict is empty
        :raises IndexError: if `index` out of range

        """
        if not self:
            raise KeyError('popitem(): dictionary is empty')

        key = self._list_pop(index)
        value = dict.pop(self, key)
        return (key, value)


    def peekitem(self, index=-1):
        """Return ``(key, value)`` pair at `index` in sorted dict.

        Optional argument `index` defaults to -1, the last item in the sorted
        dict. Specify ``index=0`` for the first item in the sorted dict.

        Unlike :func:`SortedDict.popitem`, the sorted dict is not modified.

        If the `index` is out of range, raises :exc:`IndexError`.

        Runtime complexity: `O(log(n))`

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> sd.peekitem()
        ('c', 3)
        >>> sd.peekitem(0)
        ('a', 1)
        >>> sd.peekitem(100)
        Traceback (most recent call last):
          ...
        IndexError: list index out of range

        :param int index: index of item (default -1)
        :return: key and value pair
        :raises IndexError: if `index` out of range

        """
        key = self._list[index]
        return key, self[key]


    def setdefault(self, key, default=None):
        """Return value for item identified by `key` in sorted dict.

        If `key` is in the sorted dict then return its value. If `key` is not
        in the sorted dict then insert `key` with value `default` and return
        `default`.

        Optional argument `default` defaults to none.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict()
        >>> sd.setdefault('a', 1)
        1
        >>> sd.setdefault('a', 10)
        1
        >>> sd
        SortedDict({'a': 1})

        :param key: key for item
        :param default: value for item (default None)
        :return: value for item identified by `key`

        """
        if key in self:
            return self[key]
        dict.__setitem__(self, key, default)
        self._list_add(key)
        return default


    def update(self, *args, **kwargs):
        """Update sorted dict with items from `args` and `kwargs`.

        Overwrites existing items.

        Optional arguments `args` and `kwargs` may be a mapping, an iterable of
        pairs or keyword arguments. See :func:`SortedDict.__init__` for
        details.

        :param args: mapping or iterable of pairs
        :param kwargs: keyword arguments mapping

        """
        if not self:
            dict.update(self, *args, **kwargs)
            self._list_update(dict.__iter__(self))
            return

        if not kwargs and len(args) == 1 and isinstance(args[0], dict):
            pairs = args[0]
        else:
            pairs = dict(*args, **kwargs)

        if (10 * len(pairs)) > len(self):
            dict.update(self, pairs)
            self._list_clear()
            self._list_update(dict.__iter__(self))
        else:
            for key in pairs:
                self._setitem(key, pairs[key])

    _update = update


    def __reduce__(self):
        """Support for pickle.

        The tricks played with caching references in
        :func:`SortedDict.__init__` confuse pickle so customize the reducer.

        """
        items = dict.copy(self)
        return (type(self), (self._key, items))


    @recursive_repr()
    def __repr__(self):
        """Return string representation of sorted dict.

        ``sd.__repr__()`` <==> ``repr(sd)``

        :return: string representation

        """
        _key = self._key
        type_name = type(self).__name__
        key_arg = '' if _key is None else '{0!r}, '.format(_key)
        item_format = '{0!r}: {1!r}'.format
        items = ', '.join(item_format(key, self[key]) for key in self._list)
        return '{0}({1}{{{2}}})'.format(type_name, key_arg, items)


    def _check(self):
        """Check invariants of sorted dict.

        Runtime complexity: `O(n)`

        """
        _list = self._list
        _list._check()
        assert len(self) == len(_list)
        assert all(key in self for key in _list)


def _view_delitem(self, index):
    """Remove item at `index` from sorted dict.

    ``view.__delitem__(index)`` <==> ``del view[index]``

    Supports slicing.

    Runtime complexity: `O(log(n))` -- approximate.

    >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
    >>> view = sd.keys()
    >>> del view[0]
    >>> sd
    SortedDict({'b': 2, 'c': 3})
    >>> del view[-1]
    >>> sd
    SortedDict({'b': 2})
    >>> del view[:]
    >>> sd
    SortedDict({})

    :param index: integer or slice for indexing
    :raises IndexError: if index out of range

    """
    _mapping = self._mapping
    _list = _mapping._list
    dict_delitem = dict.__delitem__
    if isinstance(index, slice):
        keys = _list[index]
        del _list[index]
        for key in keys:
            dict_delitem(_mapping, key)
    else:
        key = _list.pop(index)
        dict_delitem(_mapping, key)


class SortedKeysView(KeysView, Sequence):
    """Sorted keys view is a dynamic view of the sorted dict's keys.

    When the sorted dict's keys change, the view reflects those changes.

    The keys view implements the set and sequence abstract base classes.

    """
    __slots__ = ()


    @classmethod
    def _from_iterable(cls, it):
        return SortedSet(it)


    def __getitem__(self, index):
        """Lookup key at `index` in sorted keys views.

        ``skv.__getitem__(index)`` <==> ``skv[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> skv = sd.keys()
        >>> skv[0]
        'a'
        >>> skv[-1]
        'c'
        >>> skv[:]
        ['a', 'b', 'c']
        >>> skv[100]
        Traceback (most recent call last):
          ...
        IndexError: list index out of range

        :param index: integer or slice for indexing
        :return: key or list of keys
        :raises IndexError: if index out of range

        """
        return self._mapping._list[index]


    __delitem__ = _view_delitem


class SortedItemsView(ItemsView, Sequence):
    """Sorted items view is a dynamic view of the sorted dict's items.

    When the sorted dict's items change, the view reflects those changes.

    The items view implements the set and sequence abstract base classes.

    """
    __slots__ = ()


    @classmethod
    def _from_iterable(cls, it):
        return SortedSet(it)


    def __getitem__(self, index):
        """Lookup item at `index` in sorted items view.

        ``siv.__getitem__(index)`` <==> ``siv[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> siv = sd.items()
        >>> siv[0]
        ('a', 1)
        >>> siv[-1]
        ('c', 3)
        >>> siv[:]
        [('a', 1), ('b', 2), ('c', 3)]
        >>> siv[100]
        Traceback (most recent call last):
          ...
        IndexError: list index out of range

        :param index: integer or slice for indexing
        :return: item or list of items
        :raises IndexError: if index out of range

        """
        _mapping = self._mapping
        _mapping_list = _mapping._list

        if isinstance(index, slice):
            keys = _mapping_list[index]
            return [(key, _mapping[key]) for key in keys]

        key = _mapping_list[index]
        return key, _mapping[key]


    __delitem__ = _view_delitem


class SortedValuesView(ValuesView, Sequence):
    """Sorted values view is a dynamic view of the sorted dict's values.

    When the sorted dict's values change, the view reflects those changes.

    The values view implements the sequence abstract base class.

    """
    __slots__ = ()


    def __getitem__(self, index):
        """Lookup value at `index` in sorted values view.

        ``siv.__getitem__(index)`` <==> ``siv[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sd = SortedDict({'a': 1, 'b': 2, 'c': 3})
        >>> svv = sd.values()
        >>> svv[0]
        1
        >>> svv[-1]
        3
        >>> svv[:]
        [1, 2, 3]
        >>> svv[100]
        Traceback (most recent call last):
          ...
        IndexError: list index out of range

        :param index: integer or slice for indexing
        :return: value or list of values
        :raises IndexError: if index out of range

        """
        _mapping = self._mapping
        _mapping_list = _mapping._list

        if isinstance(index, slice):
            keys = _mapping_list[index]
            return [_mapping[key] for key in keys]

        key = _mapping_list[index]
        return _mapping[key]


    __delitem__ = _view_delitem

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\build_ext.py ===
"""distutils.command.build_ext

Implements the Distutils 'build_ext' command, for building extension
modules (currently limited to C extensions, should accommodate C++
extensions ASAP)."""

from __future__ import annotations

import contextlib
import os
import re
import sys
from collections.abc import Callable
from distutils._log import log
from site import USER_BASE
from typing import ClassVar

from .._modified import newer_group
from ..ccompiler import new_compiler, show_compilers
from ..core import Command
from ..errors import (
    CCompilerError,
    CompileError,
    DistutilsError,
    DistutilsOptionError,
    DistutilsPlatformError,
    DistutilsSetupError,
)
from ..extension import Extension
from ..sysconfig import customize_compiler, get_config_h_filename, get_python_version
from ..util import get_platform, is_freethreaded, is_mingw

# An extension name is just a dot-separated list of Python NAMEs (ie.
# the same as a fully-qualified module name).
extension_name_re = re.compile(r'^[a-zA-Z_][a-zA-Z_0-9]*(\.[a-zA-Z_][a-zA-Z_0-9]*)*$')


class build_ext(Command):
    description = "build C/C++ extensions (compile/link to build directory)"

    # XXX thoughts on how to deal with complex command-line options like
    # these, i.e. how to make it so fancy_getopt can suck them off the
    # command line and make it look like setup.py defined the appropriate
    # lists of tuples of what-have-you.
    #   - each command needs a callback to process its command-line options
    #   - Command.__init__() needs access to its share of the whole
    #     command line (must ultimately come from
    #     Distribution.parse_command_line())
    #   - it then calls the current command class' option-parsing
    #     callback to deal with weird options like -D, which have to
    #     parse the option text and churn out some custom data
    #     structure
    #   - that data structure (in this case, a list of 2-tuples)
    #     will then be present in the command object by the time
    #     we get to finalize_options() (i.e. the constructor
    #     takes care of both command-line and client options
    #     in between initialize_options() and finalize_options())

    sep_by = f" (separated by '{os.pathsep}')"
    user_options = [
        ('build-lib=', 'b', "directory for compiled extension modules"),
        ('build-temp=', 't', "directory for temporary files (build by-products)"),
        (
            'plat-name=',
            'p',
            "platform name to cross-compile for, if supported "
            f"[default: {get_platform()}]",
        ),
        (
            'inplace',
            'i',
            "ignore build-lib and put compiled extensions into the source "
            "directory alongside your pure Python modules",
        ),
        (
            'include-dirs=',
            'I',
            "list of directories to search for header files" + sep_by,
        ),
        ('define=', 'D', "C preprocessor macros to define"),
        ('undef=', 'U', "C preprocessor macros to undefine"),
        ('libraries=', 'l', "external C libraries to link with"),
        (
            'library-dirs=',
            'L',
            "directories to search for external C libraries" + sep_by,
        ),
        ('rpath=', 'R', "directories to search for shared C libraries at runtime"),
        ('link-objects=', 'O', "extra explicit link objects to include in the link"),
        ('debug', 'g', "compile/link with debugging information"),
        ('force', 'f', "forcibly build everything (ignore file timestamps)"),
        ('compiler=', 'c', "specify the compiler type"),
        ('parallel=', 'j', "number of parallel build jobs"),
        ('swig-cpp', None, "make SWIG create C++ files (default is C)"),
        ('swig-opts=', None, "list of SWIG command line options"),
        ('swig=', None, "path to the SWIG executable"),
        ('user', None, "add user include, library and rpath"),
    ]

    boolean_options: ClassVar[list[str]] = [
        'inplace',
        'debug',
        'force',
        'swig-cpp',
        'user',
    ]

    help_options: ClassVar[list[tuple[str, str | None, str, Callable[[], object]]]] = [
        ('help-compiler', None, "list available compilers", show_compilers),
    ]

    def initialize_options(self):
        self.extensions = None
        self.build_lib = None
        self.plat_name = None
        self.build_temp = None
        self.inplace = False
        self.package = None

        self.include_dirs = None
        self.define = None
        self.undef = None
        self.libraries = None
        self.library_dirs = None
        self.rpath = None
        self.link_objects = None
        self.debug = None
        self.force = None
        self.compiler = None
        self.swig = None
        self.swig_cpp = None
        self.swig_opts = None
        self.user = None
        self.parallel = None

    @staticmethod
    def _python_lib_dir(sysconfig):
        """
        Resolve Python's library directory for building extensions
        that rely on a shared Python library.

        See python/cpython#44264 and python/cpython#48686
        """
        if not sysconfig.get_config_var('Py_ENABLE_SHARED'):
            return

        if sysconfig.python_build:
            yield '.'
            return

        if sys.platform == 'zos':
            # On z/OS, a user is not required to install Python to
            # a predetermined path, but can use Python portably
            installed_dir = sysconfig.get_config_var('base')
            lib_dir = sysconfig.get_config_var('platlibdir')
            yield os.path.join(installed_dir, lib_dir)
        else:
            # building third party extensions
            yield sysconfig.get_config_var('LIBDIR')

    def finalize_options(self) -> None:  # noqa: C901
        from distutils import sysconfig

        self.set_undefined_options(
            'build',
            ('build_lib', 'build_lib'),
            ('build_temp', 'build_temp'),
            ('compiler', 'compiler'),
            ('debug', 'debug'),
            ('force', 'force'),
            ('parallel', 'parallel'),
            ('plat_name', 'plat_name'),
        )

        if self.package is None:
            self.package = self.distribution.ext_package

        self.extensions = self.distribution.ext_modules

        # Make sure Python's include directories (for Python.h, pyconfig.h,
        # etc.) are in the include search path.
        py_include = sysconfig.get_python_inc()
        plat_py_include = sysconfig.get_python_inc(plat_specific=True)
        if self.include_dirs is None:
            self.include_dirs = self.distribution.include_dirs or []
        if isinstance(self.include_dirs, str):
            self.include_dirs = self.include_dirs.split(os.pathsep)

        # If in a virtualenv, add its include directory
        # Issue 16116
        if sys.exec_prefix != sys.base_exec_prefix:
            self.include_dirs.append(os.path.join(sys.exec_prefix, 'include'))

        # Put the Python "system" include dir at the end, so that
        # any local include dirs take precedence.
        self.include_dirs.extend(py_include.split(os.path.pathsep))
        if plat_py_include != py_include:
            self.include_dirs.extend(plat_py_include.split(os.path.pathsep))

        self.ensure_string_list('libraries')
        self.ensure_string_list('link_objects')

        # Life is easier if we're not forever checking for None, so
        # simplify these options to empty lists if unset
        if self.libraries is None:
            self.libraries = []
        if self.library_dirs is None:
            self.library_dirs = []
        elif isinstance(self.library_dirs, str):
            self.library_dirs = self.library_dirs.split(os.pathsep)

        if self.rpath is None:
            self.rpath = []
        elif isinstance(self.rpath, str):
            self.rpath = self.rpath.split(os.pathsep)

        # for extensions under windows use different directories
        # for Release and Debug builds.
        # also Python's library directory must be appended to library_dirs
        if os.name == 'nt' and not is_mingw():
            # the 'libs' directory is for binary installs - we assume that
            # must be the *native* platform.  But we don't really support
            # cross-compiling via a binary install anyway, so we let it go.
            self.library_dirs.append(os.path.join(sys.exec_prefix, 'libs'))
            if sys.base_exec_prefix != sys.prefix:  # Issue 16116
                self.library_dirs.append(os.path.join(sys.base_exec_prefix, 'libs'))
            if self.debug:
                self.build_temp = os.path.join(self.build_temp, "Debug")
            else:
                self.build_temp = os.path.join(self.build_temp, "Release")

            # Append the source distribution include and library directories,
            # this allows distutils on windows to work in the source tree
            self.include_dirs.append(os.path.dirname(get_config_h_filename()))
            self.library_dirs.append(sys.base_exec_prefix)

            # Use the .lib files for the correct architecture
            if self.plat_name == 'win32':
                suffix = 'win32'
            else:
                # win-amd64
                suffix = self.plat_name[4:]
            new_lib = os.path.join(sys.exec_prefix, 'PCbuild')
            if suffix:
                new_lib = os.path.join(new_lib, suffix)
            self.library_dirs.append(new_lib)

        # For extensions under Cygwin, Python's library directory must be
        # appended to library_dirs
        if sys.platform[:6] == 'cygwin':
            if not sysconfig.python_build:
                # building third party extensions
                self.library_dirs.append(
                    os.path.join(
                        sys.prefix, "lib", "python" + get_python_version(), "config"
                    )
                )
            else:
                # building python standard extensions
                self.library_dirs.append('.')

        self.library_dirs.extend(self._python_lib_dir(sysconfig))

        # The argument parsing will result in self.define being a string, but
        # it has to be a list of 2-tuples.  All the preprocessor symbols
        # specified by the 'define' option will be set to '1'.  Multiple
        # symbols can be separated with commas.

        if self.define:
            defines = self.define.split(',')
            self.define = [(symbol, '1') for symbol in defines]

        # The option for macros to undefine is also a string from the
        # option parsing, but has to be a list.  Multiple symbols can also
        # be separated with commas here.
        if self.undef:
            self.undef = self.undef.split(',')

        if self.swig_opts is None:
            self.swig_opts = []
        else:
            self.swig_opts = self.swig_opts.split(' ')

        # Finally add the user include and library directories if requested
        if self.user:
            user_include = os.path.join(USER_BASE, "include")
            user_lib = os.path.join(USER_BASE, "lib")
            if os.path.isdir(user_include):
                self.include_dirs.append(user_include)
            if os.path.isdir(user_lib):
                self.library_dirs.append(user_lib)
                self.rpath.append(user_lib)

        if isinstance(self.parallel, str):
            try:
                self.parallel = int(self.parallel)
            except ValueError:
                raise DistutilsOptionError("parallel should be an integer")

    def run(self) -> None:  # noqa: C901
        # 'self.extensions', as supplied by setup.py, is a list of
        # Extension instances.  See the documentation for Extension (in
        # distutils.extension) for details.
        #
        # For backwards compatibility with Distutils 0.8.2 and earlier, we
        # also allow the 'extensions' list to be a list of tuples:
        #    (ext_name, build_info)
        # where build_info is a dictionary containing everything that
        # Extension instances do except the name, with a few things being
        # differently named.  We convert these 2-tuples to Extension
        # instances as needed.

        if not self.extensions:
            return

        # If we were asked to build any C/C++ libraries, make sure that the
        # directory where we put them is in the library search path for
        # linking extensions.
        if self.distribution.has_c_libraries():
            build_clib = self.get_finalized_command('build_clib')
            self.libraries.extend(build_clib.get_library_names() or [])
            self.library_dirs.append(build_clib.build_clib)

        # Setup the CCompiler object that we'll use to do all the
        # compiling and linking
        self.compiler = new_compiler(
            compiler=self.compiler,
            verbose=self.verbose,
            dry_run=self.dry_run,
            force=self.force,
        )
        customize_compiler(self.compiler)
        # If we are cross-compiling, init the compiler now (if we are not
        # cross-compiling, init would not hurt, but people may rely on
        # late initialization of compiler even if they shouldn't...)
        if os.name == 'nt' and self.plat_name != get_platform():
            self.compiler.initialize(self.plat_name)

        # The official Windows free threaded Python installer doesn't set
        # Py_GIL_DISABLED because its pyconfig.h is shared with the
        # default build, so define it here (pypa/setuptools#4662).
        if os.name == 'nt' and is_freethreaded():
            self.compiler.define_macro('Py_GIL_DISABLED', '1')

        # And make sure that any compile/link-related options (which might
        # come from the command-line or from the setup script) are set in
        # that CCompiler object -- that way, they automatically apply to
        # all compiling and linking done here.
        if self.include_dirs is not None:
            self.compiler.set_include_dirs(self.include_dirs)
        if self.define is not None:
            # 'define' option is a list of (name,value) tuples
            for name, value in self.define:
                self.compiler.define_macro(name, value)
        if self.undef is not None:
            for macro in self.undef:
                self.compiler.undefine_macro(macro)
        if self.libraries is not None:
            self.compiler.set_libraries(self.libraries)
        if self.library_dirs is not None:
            self.compiler.set_library_dirs(self.library_dirs)
        if self.rpath is not None:
            self.compiler.set_runtime_library_dirs(self.rpath)
        if self.link_objects is not None:
            self.compiler.set_link_objects(self.link_objects)

        # Now actually compile and link everything.
        self.build_extensions()

    def check_extensions_list(self, extensions) -> None:  # noqa: C901
        """Ensure that the list of extensions (presumably provided as a
        command option 'extensions') is valid, i.e. it is a list of
        Extension objects.  We also support the old-style list of 2-tuples,
        where the tuples are (ext_name, build_info), which are converted to
        Extension instances here.

        Raise DistutilsSetupError if the structure is invalid anywhere;
        just returns otherwise.
        """
        if not isinstance(extensions, list):
            raise DistutilsSetupError(
                "'ext_modules' option must be a list of Extension instances"
            )

        for i, ext in enumerate(extensions):
            if isinstance(ext, Extension):
                continue  # OK! (assume type-checking done
                # by Extension constructor)

            if not isinstance(ext, tuple) or len(ext) != 2:
                raise DistutilsSetupError(
                    "each element of 'ext_modules' option must be an "
                    "Extension instance or 2-tuple"
                )

            ext_name, build_info = ext

            log.warning(
                "old-style (ext_name, build_info) tuple found in "
                "ext_modules for extension '%s' "
                "-- please convert to Extension instance",
                ext_name,
            )

            if not (isinstance(ext_name, str) and extension_name_re.match(ext_name)):
                raise DistutilsSetupError(
                    "first element of each tuple in 'ext_modules' "
                    "must be the extension name (a string)"
                )

            if not isinstance(build_info, dict):
                raise DistutilsSetupError(
                    "second element of each tuple in 'ext_modules' "
                    "must be a dictionary (build info)"
                )

            # OK, the (ext_name, build_info) dict is type-safe: convert it
            # to an Extension instance.
            ext = Extension(ext_name, build_info['sources'])

            # Easy stuff: one-to-one mapping from dict elements to
            # instance attributes.
            for key in (
                'include_dirs',
                'library_dirs',
                'libraries',
                'extra_objects',
                'extra_compile_args',
                'extra_link_args',
            ):
                val = build_info.get(key)
                if val is not None:
                    setattr(ext, key, val)

            # Medium-easy stuff: same syntax/semantics, different names.
            ext.runtime_library_dirs = build_info.get('rpath')
            if 'def_file' in build_info:
                log.warning("'def_file' element of build info dict no longer supported")

            # Non-trivial stuff: 'macros' split into 'define_macros'
            # and 'undef_macros'.
            macros = build_info.get('macros')
            if macros:
                ext.define_macros = []
                ext.undef_macros = []
                for macro in macros:
                    if not (isinstance(macro, tuple) and len(macro) in (1, 2)):
                        raise DistutilsSetupError(
                            "'macros' element of build info dict must be 1- or 2-tuple"
                        )
                    if len(macro) == 1:
                        ext.undef_macros.append(macro[0])
                    elif len(macro) == 2:
                        ext.define_macros.append(macro)

            extensions[i] = ext

    def get_source_files(self):
        self.check_extensions_list(self.extensions)
        filenames = []

        # Wouldn't it be neat if we knew the names of header files too...
        for ext in self.extensions:
            filenames.extend(ext.sources)
        return filenames

    def get_outputs(self):
        # Sanity check the 'extensions' list -- can't assume this is being
        # done in the same run as a 'build_extensions()' call (in fact, we
        # can probably assume that it *isn't*!).
        self.check_extensions_list(self.extensions)

        # And build the list of output (built) filenames.  Note that this
        # ignores the 'inplace' flag, and assumes everything goes in the
        # "build" tree.
        return [self.get_ext_fullpath(ext.name) for ext in self.extensions]

    def build_extensions(self) -> None:
        # First, sanity-check the 'extensions' list
        self.check_extensions_list(self.extensions)
        if self.parallel:
            self._build_extensions_parallel()
        else:
            self._build_extensions_serial()

    def _build_extensions_parallel(self):
        workers = self.parallel
        if self.parallel is True:
            workers = os.cpu_count()  # may return None
        try:
            from concurrent.futures import ThreadPoolExecutor
        except ImportError:
            workers = None

        if workers is None:
            self._build_extensions_serial()
            return

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.build_extension, ext) for ext in self.extensions
            ]
            for ext, fut in zip(self.extensions, futures):
                with self._filter_build_errors(ext):
                    fut.result()

    def _build_extensions_serial(self):
        for ext in self.extensions:
            with self._filter_build_errors(ext):
                self.build_extension(ext)

    @contextlib.contextmanager
    def _filter_build_errors(self, ext):
        try:
            yield
        except (CCompilerError, DistutilsError, CompileError) as e:
            if not ext.optional:
                raise
            self.warn(f'building extension "{ext.name}" failed: {e}')

    def build_extension(self, ext) -> None:
        sources = ext.sources
        if sources is None or not isinstance(sources, (list, tuple)):
            raise DistutilsSetupError(
                f"in 'ext_modules' option (extension '{ext.name}'), "
                "'sources' must be present and must be "
                "a list of source filenames"
            )
        # sort to make the resulting .so file build reproducible
        sources = sorted(sources)

        ext_path = self.get_ext_fullpath(ext.name)
        depends = sources + ext.depends
        if not (self.force or newer_group(depends, ext_path, 'newer')):
            log.debug("skipping '%s' extension (up-to-date)", ext.name)
            return
        else:
            log.info("building '%s' extension", ext.name)

        # First, scan the sources for SWIG definition files (.i), run
        # SWIG on 'em to create .c files, and modify the sources list
        # accordingly.
        sources = self.swig_sources(sources, ext)

        # Next, compile the source code to object files.

        # XXX not honouring 'define_macros' or 'undef_macros' -- the
        # CCompiler API needs to change to accommodate this, and I
        # want to do one thing at a time!

        # Two possible sources for extra compiler arguments:
        #   - 'extra_compile_args' in Extension object
        #   - CFLAGS environment variable (not particularly
        #     elegant, but people seem to expect it and I
        #     guess it's useful)
        # The environment variable should take precedence, and
        # any sensible compiler will give precedence to later
        # command line args.  Hence we combine them in order:
        extra_args = ext.extra_compile_args or []

        macros = ext.define_macros[:]
        for undef in ext.undef_macros:
            macros.append((undef,))

        objects = self.compiler.compile(
            sources,
            output_dir=self.build_temp,
            macros=macros,
            include_dirs=ext.include_dirs,
            debug=self.debug,
            extra_postargs=extra_args,
            depends=ext.depends,
        )

        # XXX outdated variable, kept here in case third-part code
        # needs it.
        self._built_objects = objects[:]

        # Now link the object files together into a "shared object" --
        # of course, first we have to figure out all the other things
        # that go into the mix.
        if ext.extra_objects:
            objects.extend(ext.extra_objects)
        extra_args = ext.extra_link_args or []

        # Detect target language, if not provided
        language = ext.language or self.compiler.detect_language(sources)

        self.compiler.link_shared_object(
            objects,
            ext_path,
            libraries=self.get_libraries(ext),
            library_dirs=ext.library_dirs,
            runtime_library_dirs=ext.runtime_library_dirs,
            extra_postargs=extra_args,
            export_symbols=self.get_export_symbols(ext),
            debug=self.debug,
            build_temp=self.build_temp,
            target_lang=language,
        )

    def swig_sources(self, sources, extension):
        """Walk the list of source files in 'sources', looking for SWIG
        interface (.i) files.  Run SWIG on all that are found, and
        return a modified 'sources' list with SWIG source files replaced
        by the generated C (or C++) files.
        """
        new_sources = []
        swig_sources = []
        swig_targets = {}

        # XXX this drops generated C/C++ files into the source tree, which
        # is fine for developers who want to distribute the generated
        # source -- but there should be an option to put SWIG output in
        # the temp dir.

        if self.swig_cpp:
            log.warning("--swig-cpp is deprecated - use --swig-opts=-c++")

        if (
            self.swig_cpp
            or ('-c++' in self.swig_opts)
            or ('-c++' in extension.swig_opts)
        ):
            target_ext = '.cpp'
        else:
            target_ext = '.c'

        for source in sources:
            (base, ext) = os.path.splitext(source)
            if ext == ".i":  # SWIG interface file
                new_sources.append(base + '_wrap' + target_ext)
                swig_sources.append(source)
                swig_targets[source] = new_sources[-1]
            else:
                new_sources.append(source)

        if not swig_sources:
            return new_sources

        swig = self.swig or self.find_swig()
        swig_cmd = [swig, "-python"]
        swig_cmd.extend(self.swig_opts)
        if self.swig_cpp:
            swig_cmd.append("-c++")

        # Do not override commandline arguments
        if not self.swig_opts:
            swig_cmd.extend(extension.swig_opts)

        for source in swig_sources:
            target = swig_targets[source]
            log.info("swigging %s to %s", source, target)
            self.spawn(swig_cmd + ["-o", target, source])

        return new_sources

    def find_swig(self):
        """Return the name of the SWIG executable.  On Unix, this is
        just "swig" -- it should be in the PATH.  Tries a bit harder on
        Windows.
        """
        if os.name == "posix":
            return "swig"
        elif os.name == "nt":
            # Look for SWIG in its standard installation directory on
            # Windows (or so I presume!).  If we find it there, great;
            # if not, act like Unix and assume it's in the PATH.
            for vers in ("1.3", "1.2", "1.1"):
                fn = os.path.join(f"c:\\swig{vers}", "swig.exe")
                if os.path.isfile(fn):
                    return fn
            else:
                return "swig.exe"
        else:
            raise DistutilsPlatformError(
                f"I don't know how to find (much less run) SWIG on platform '{os.name}'"
            )

    # -- Name generators -----------------------------------------------
    # (extension names, filenames, whatever)
    def get_ext_fullpath(self, ext_name: str) -> str:
        """Returns the path of the filename for a given extension.

        The file is located in `build_lib` or directly in the package
        (inplace option).
        """
        fullname = self.get_ext_fullname(ext_name)
        modpath = fullname.split('.')
        filename = self.get_ext_filename(modpath[-1])

        if not self.inplace:
            # no further work needed
            # returning :
            #   build_dir/package/path/filename
            filename = os.path.join(*modpath[:-1] + [filename])
            return os.path.join(self.build_lib, filename)

        # the inplace option requires to find the package directory
        # using the build_py command for that
        package = '.'.join(modpath[0:-1])
        build_py = self.get_finalized_command('build_py')
        package_dir = os.path.abspath(build_py.get_package_dir(package))

        # returning
        #   package_dir/filename
        return os.path.join(package_dir, filename)

    def get_ext_fullname(self, ext_name: str) -> str:
        """Returns the fullname of a given extension name.

        Adds the `package.` prefix"""
        if self.package is None:
            return ext_name
        else:
            return self.package + '.' + ext_name

    def get_ext_filename(self, ext_name: str) -> str:
        r"""Convert the name of an extension (eg. "foo.bar") into the name
        of the file from which it will be loaded (eg. "foo/bar.so", or
        "foo\bar.pyd").
        """
        from ..sysconfig import get_config_var

        ext_path = ext_name.split('.')
        ext_suffix = get_config_var('EXT_SUFFIX')
        return os.path.join(*ext_path) + ext_suffix

    def get_export_symbols(self, ext: Extension) -> list[str]:
        """Return the list of symbols that a shared extension has to
        export.  This either uses 'ext.export_symbols' or, if it's not
        provided, "PyInit_" + module_name.  Only relevant on Windows, where
        the .pyd file (DLL) must export the module "PyInit_" function.
        """
        name = self._get_module_name_for_symbol(ext)
        try:
            # Unicode module name support as defined in PEP-489
            # https://peps.python.org/pep-0489/#export-hook-name
            name.encode('ascii')
        except UnicodeEncodeError:
            suffix = 'U_' + name.encode('punycode').replace(b'-', b'_').decode('ascii')
        else:
            suffix = "_" + name

        initfunc_name = "PyInit" + suffix
        if initfunc_name not in ext.export_symbols:
            ext.export_symbols.append(initfunc_name)
        return ext.export_symbols

    def _get_module_name_for_symbol(self, ext):
        # Package name should be used for `__init__` modules
        # https://github.com/python/cpython/issues/80074
        # https://github.com/pypa/setuptools/issues/4826
        parts = ext.name.split(".")
        if parts[-1] == "__init__" and len(parts) >= 2:
            return parts[-2]
        return parts[-1]

    def get_libraries(self, ext: Extension) -> list[str]:  # noqa: C901
        """Return the list of libraries to link against when building a
        shared extension.  On most platforms, this is just 'ext.libraries';
        on Windows, we add the Python library (eg. python20.dll).
        """
        # The python library is always needed on Windows.  For MSVC, this
        # is redundant, since the library is mentioned in a pragma in
        # pyconfig.h that MSVC groks.  The other Windows compilers all seem
        # to need it mentioned explicitly, though, so that's what we do.
        # Append '_d' to the python import library on debug builds.
        if sys.platform == "win32" and not is_mingw():
            from .._msvccompiler import MSVCCompiler

            if not isinstance(self.compiler, MSVCCompiler):
                template = "python%d%d"
                if self.debug:
                    template = template + '_d'
                pythonlib = template % (
                    sys.hexversion >> 24,
                    (sys.hexversion >> 16) & 0xFF,
                )
                # don't extend ext.libraries, it may be shared with other
                # extensions, it is a reference to the original list
                return ext.libraries + [pythonlib]
        else:
            # On Android only the main executable and LD_PRELOADs are considered
            # to be RTLD_GLOBAL, all the dependencies of the main executable
            # remain RTLD_LOCAL and so the shared libraries must be linked with
            # libpython when python is built with a shared python library (issue
            # bpo-21536).
            # On Cygwin (and if required, other POSIX-like platforms based on
            # Windows like MinGW) it is simply necessary that all symbols in
            # shared libraries are resolved at link time.
            from ..sysconfig import get_config_var

            link_libpython = False
            if get_config_var('Py_ENABLE_SHARED'):
                # A native build on an Android device or on Cygwin
                if hasattr(sys, 'getandroidapilevel'):
                    link_libpython = True
                elif sys.platform == 'cygwin' or is_mingw():
                    link_libpython = True
                elif '_PYTHON_HOST_PLATFORM' in os.environ:
                    # We are cross-compiling for one of the relevant platforms
                    if get_config_var('ANDROID_API_LEVEL') != 0:
                        link_libpython = True
                    elif get_config_var('MACHDEP') == 'cygwin':
                        link_libpython = True

            if link_libpython:
                ldversion = get_config_var('LDVERSION')
                return ext.libraries + ['python' + ldversion]

        return ext.libraries

# === NexusCore/openenv\Lib\site-packages\tornado\test\ioloop_test.py ===
import asyncio
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures
from collections.abc import Generator
import contextlib
import datetime
import functools
import socket
import subprocess
import sys
import threading
import time
import types
from unittest import mock
import unittest

from tornado.escape import native_str
from tornado import gen
from tornado.ioloop import IOLoop, TimeoutError, PeriodicCallback
from tornado.log import app_log
from tornado.testing import (
    AsyncTestCase,
    bind_unused_port,
    ExpectLog,
    gen_test,
    setup_with_context_manager,
)
from tornado.test.util import (
    ignore_deprecation,
    skipIfNonUnix,
)
from tornado.concurrent import Future

import typing

if typing.TYPE_CHECKING:
    from typing import List  # noqa: F401


class TestIOLoop(AsyncTestCase):
    def test_add_callback_return_sequence(self):
        # A callback returning {} or [] shouldn't spin the CPU, see Issue #1803.
        self.calls = 0

        loop = self.io_loop
        test = self
        old_add_callback = loop.add_callback

        def add_callback(self, callback, *args, **kwargs):
            test.calls += 1
            old_add_callback(callback, *args, **kwargs)

        loop.add_callback = types.MethodType(add_callback, loop)  # type: ignore
        loop.add_callback(lambda: {})  # type: ignore
        loop.add_callback(lambda: [])  # type: ignore
        loop.add_timeout(datetime.timedelta(milliseconds=50), loop.stop)
        loop.start()
        self.assertLess(self.calls, 10)

    def test_add_callback_wakeup(self):
        # Make sure that add_callback from inside a running IOLoop
        # wakes up the IOLoop immediately instead of waiting for a timeout.
        def callback():
            self.called = True
            self.stop()

        def schedule_callback():
            self.called = False
            self.io_loop.add_callback(callback)
            # Store away the time so we can check if we woke up immediately
            self.start_time = time.time()

        self.io_loop.add_timeout(self.io_loop.time(), schedule_callback)
        self.wait()
        self.assertAlmostEqual(time.time(), self.start_time, places=2)
        self.assertTrue(self.called)

    def test_add_callback_wakeup_other_thread(self):
        def target():
            # sleep a bit to let the ioloop go into its poll loop
            time.sleep(0.01)
            self.stop_time = time.time()
            self.io_loop.add_callback(self.stop)

        thread = threading.Thread(target=target)
        self.io_loop.add_callback(thread.start)
        self.wait()
        delta = time.time() - self.stop_time
        self.assertLess(delta, 0.1)
        thread.join()

    def test_add_timeout_timedelta(self):
        self.io_loop.add_timeout(datetime.timedelta(microseconds=1), self.stop)
        self.wait()

    def test_multiple_add(self):
        sock, port = bind_unused_port()
        try:
            self.io_loop.add_handler(
                sock.fileno(), lambda fd, events: None, IOLoop.READ
            )
            # Attempting to add the same handler twice fails
            # (with a platform-dependent exception)
            self.assertRaises(
                Exception,
                self.io_loop.add_handler,
                sock.fileno(),
                lambda fd, events: None,
                IOLoop.READ,
            )
        finally:
            self.io_loop.remove_handler(sock.fileno())
            sock.close()

    def test_remove_without_add(self):
        # remove_handler should not throw an exception if called on an fd
        # was never added.
        sock, port = bind_unused_port()
        try:
            self.io_loop.remove_handler(sock.fileno())
        finally:
            sock.close()

    def test_add_callback_from_signal(self):
        # cheat a little bit and just run this normally, since we can't
        # easily simulate the races that happen with real signal handlers
        with ignore_deprecation():
            self.io_loop.add_callback_from_signal(self.stop)
        self.wait()

    def test_add_callback_from_signal_other_thread(self):
        # Very crude test, just to make sure that we cover this case.
        # This also happens to be the first test where we run an IOLoop in
        # a non-main thread.
        other_ioloop = IOLoop(make_current=False)
        thread = threading.Thread(target=other_ioloop.start)
        thread.start()
        with ignore_deprecation():
            other_ioloop.add_callback_from_signal(other_ioloop.stop)
        thread.join()
        other_ioloop.close()

    def test_add_callback_while_closing(self):
        # add_callback should not fail if it races with another thread
        # closing the IOLoop. The callbacks are dropped silently
        # without executing.
        closing = threading.Event()

        def target():
            other_ioloop.add_callback(other_ioloop.stop)
            other_ioloop.start()
            closing.set()
            other_ioloop.close(all_fds=True)

        other_ioloop = IOLoop(make_current=False)
        thread = threading.Thread(target=target)
        thread.start()
        closing.wait()
        for i in range(1000):
            other_ioloop.add_callback(lambda: None)

    @skipIfNonUnix  # just because socketpair is so convenient
    def test_read_while_writeable(self):
        # Ensure that write events don't come in while we're waiting for
        # a read and haven't asked for writeability. (the reverse is
        # difficult to test for)
        client, server = socket.socketpair()
        try:

            def handler(fd, events):
                self.assertEqual(events, IOLoop.READ)
                self.stop()

            self.io_loop.add_handler(client.fileno(), handler, IOLoop.READ)
            self.io_loop.add_timeout(
                self.io_loop.time() + 0.01, functools.partial(server.send, b"asdf")
            )
            self.wait()
            self.io_loop.remove_handler(client.fileno())
        finally:
            client.close()
            server.close()

    def test_remove_timeout_after_fire(self):
        # It is not an error to call remove_timeout after it has run.
        handle = self.io_loop.add_timeout(self.io_loop.time(), self.stop)
        self.wait()
        self.io_loop.remove_timeout(handle)

    def test_remove_timeout_cleanup(self):
        # Add and remove enough callbacks to trigger cleanup.
        # Not a very thorough test, but it ensures that the cleanup code
        # gets executed and doesn't blow up.  This test is only really useful
        # on PollIOLoop subclasses, but it should run silently on any
        # implementation.
        for i in range(2000):
            timeout = self.io_loop.add_timeout(self.io_loop.time() + 3600, lambda: None)
            self.io_loop.remove_timeout(timeout)
        # HACK: wait two IOLoop iterations for the GC to happen.
        self.io_loop.add_callback(lambda: self.io_loop.add_callback(self.stop))
        self.wait()

    def test_remove_timeout_from_timeout(self):
        calls = [False, False]

        # Schedule several callbacks and wait for them all to come due at once.
        # t2 should be cancelled by t1, even though it is already scheduled to
        # be run before the ioloop even looks at it.
        now = self.io_loop.time()

        def t1():
            calls[0] = True
            self.io_loop.remove_timeout(t2_handle)

        self.io_loop.add_timeout(now + 0.01, t1)

        def t2():
            calls[1] = True

        t2_handle = self.io_loop.add_timeout(now + 0.02, t2)
        self.io_loop.add_timeout(now + 0.03, self.stop)
        time.sleep(0.03)
        self.wait()
        self.assertEqual(calls, [True, False])

    def test_timeout_with_arguments(self):
        # This tests that all the timeout methods pass through *args correctly.
        results = []  # type: List[int]
        self.io_loop.add_timeout(self.io_loop.time(), results.append, 1)
        self.io_loop.add_timeout(datetime.timedelta(seconds=0), results.append, 2)
        self.io_loop.call_at(self.io_loop.time(), results.append, 3)
        self.io_loop.call_later(0, results.append, 4)
        self.io_loop.call_later(0, self.stop)
        self.wait()
        # The asyncio event loop does not guarantee the order of these
        # callbacks.
        self.assertEqual(sorted(results), [1, 2, 3, 4])

    def test_add_timeout_return(self):
        # All the timeout methods return non-None handles that can be
        # passed to remove_timeout.
        handle = self.io_loop.add_timeout(self.io_loop.time(), lambda: None)
        self.assertIsNotNone(handle)
        self.io_loop.remove_timeout(handle)

    def test_call_at_return(self):
        handle = self.io_loop.call_at(self.io_loop.time(), lambda: None)
        self.assertIsNotNone(handle)
        self.io_loop.remove_timeout(handle)

    def test_call_later_return(self):
        handle = self.io_loop.call_later(0, lambda: None)
        self.assertIsNotNone(handle)
        self.io_loop.remove_timeout(handle)

    def test_close_file_object(self):
        """When a file object is used instead of a numeric file descriptor,
        the object should be closed (by IOLoop.close(all_fds=True),
        not just the fd.
        """

        # Use a socket since they are supported by IOLoop on all platforms.
        # Unfortunately, sockets don't support the .closed attribute for
        # inspecting their close status, so we must use a wrapper.
        class SocketWrapper:
            def __init__(self, sockobj):
                self.sockobj = sockobj
                self.closed = False

            def fileno(self):
                return self.sockobj.fileno()

            def close(self):
                self.closed = True
                self.sockobj.close()

        sockobj, port = bind_unused_port()
        socket_wrapper = SocketWrapper(sockobj)
        io_loop = IOLoop(make_current=False)
        io_loop.run_sync(
            lambda: io_loop.add_handler(
                socket_wrapper, lambda fd, events: None, IOLoop.READ
            )
        )
        io_loop.close(all_fds=True)
        self.assertTrue(socket_wrapper.closed)

    def test_handler_callback_file_object(self):
        """The handler callback receives the same fd object it passed in."""
        server_sock, port = bind_unused_port()
        fds = []

        def handle_connection(fd, events):
            fds.append(fd)
            conn, addr = server_sock.accept()
            conn.close()
            self.stop()

        self.io_loop.add_handler(server_sock, handle_connection, IOLoop.READ)
        with contextlib.closing(socket.socket()) as client_sock:
            client_sock.connect(("127.0.0.1", port))
            self.wait()
        self.io_loop.remove_handler(server_sock)
        self.io_loop.add_handler(server_sock.fileno(), handle_connection, IOLoop.READ)
        with contextlib.closing(socket.socket()) as client_sock:
            client_sock.connect(("127.0.0.1", port))
            self.wait()
        self.assertIs(fds[0], server_sock)
        self.assertEqual(fds[1], server_sock.fileno())
        self.io_loop.remove_handler(server_sock.fileno())
        server_sock.close()

    def test_mixed_fd_fileobj(self):
        server_sock, port = bind_unused_port()

        def f(fd, events):
            pass

        self.io_loop.add_handler(server_sock, f, IOLoop.READ)
        with self.assertRaises(Exception):
            # The exact error is unspecified - some implementations use
            # IOError, others use ValueError.
            self.io_loop.add_handler(server_sock.fileno(), f, IOLoop.READ)
        self.io_loop.remove_handler(server_sock.fileno())
        server_sock.close()

    def test_reentrant(self):
        """Calling start() twice should raise an error, not deadlock."""
        returned_from_start = [False]
        got_exception = [False]

        def callback():
            try:
                self.io_loop.start()
                returned_from_start[0] = True
            except Exception:
                got_exception[0] = True
            self.stop()

        self.io_loop.add_callback(callback)
        self.wait()
        self.assertTrue(got_exception[0])
        self.assertFalse(returned_from_start[0])

    def test_exception_logging(self):
        """Uncaught exceptions get logged by the IOLoop."""
        self.io_loop.add_callback(lambda: 1 / 0)
        self.io_loop.add_callback(self.stop)
        with ExpectLog(app_log, "Exception in callback"):
            self.wait()

    def test_exception_logging_future(self):
        """The IOLoop examines exceptions from Futures and logs them."""

        @gen.coroutine
        def callback():
            self.io_loop.add_callback(self.stop)
            1 / 0

        self.io_loop.add_callback(callback)
        with ExpectLog(app_log, "Exception in callback"):
            self.wait()

    def test_exception_logging_native_coro(self):
        """The IOLoop examines exceptions from awaitables and logs them."""

        async def callback():
            # Stop the IOLoop two iterations after raising an exception
            # to give the exception time to be logged.
            self.io_loop.add_callback(self.io_loop.add_callback, self.stop)
            1 / 0

        self.io_loop.add_callback(callback)
        with ExpectLog(app_log, "Exception in callback"):
            self.wait()

    def test_spawn_callback(self):
        # Both add_callback and spawn_callback run directly on the IOLoop,
        # so their errors are logged without stopping the test.
        self.io_loop.add_callback(lambda: 1 / 0)
        self.io_loop.add_callback(self.stop)
        with ExpectLog(app_log, "Exception in callback"):
            self.wait()
        # A spawned callback is run directly on the IOLoop, so it will be
        # logged without stopping the test.
        self.io_loop.spawn_callback(lambda: 1 / 0)
        self.io_loop.add_callback(self.stop)
        with ExpectLog(app_log, "Exception in callback"):
            self.wait()

    @skipIfNonUnix
    def test_remove_handler_from_handler(self):
        # Create two sockets with simultaneous read events.
        client, server = socket.socketpair()
        try:
            client.send(b"abc")
            server.send(b"abc")

            # After reading from one fd, remove the other from the IOLoop.
            chunks = []

            def handle_read(fd, events):
                chunks.append(fd.recv(1024))
                if fd is client:
                    self.io_loop.remove_handler(server)
                else:
                    self.io_loop.remove_handler(client)

            self.io_loop.add_handler(client, handle_read, self.io_loop.READ)
            self.io_loop.add_handler(server, handle_read, self.io_loop.READ)
            self.io_loop.call_later(0.1, self.stop)
            self.wait()

            # Only one fd was read; the other was cleanly removed.
            self.assertEqual(chunks, [b"abc"])
        finally:
            client.close()
            server.close()

    @skipIfNonUnix
    @gen_test
    def test_init_close_race(self):
        # Regression test for #2367
        #
        # Skipped on windows because of what looks like a bug in the
        # proactor event loop when started and stopped on non-main
        # threads.
        def f():
            for i in range(10):
                loop = IOLoop(make_current=False)
                loop.close()

        yield gen.multi([self.io_loop.run_in_executor(None, f) for i in range(2)])

    def test_explicit_asyncio_loop(self):
        asyncio_loop = asyncio.new_event_loop()
        loop = IOLoop(asyncio_loop=asyncio_loop, make_current=False)
        assert loop.asyncio_loop is asyncio_loop  # type: ignore
        with self.assertRaises(RuntimeError):
            # Can't register two IOLoops with the same asyncio_loop
            IOLoop(asyncio_loop=asyncio_loop, make_current=False)
        loop.close()


# Deliberately not a subclass of AsyncTestCase so the IOLoop isn't
# automatically set as current.
class TestIOLoopCurrent(unittest.TestCase):
    def setUp(self):
        setup_with_context_manager(self, ignore_deprecation())
        self.io_loop = None  # type: typing.Optional[IOLoop]
        IOLoop.clear_current()

    def tearDown(self):
        if self.io_loop is not None:
            self.io_loop.close()

    def test_non_current(self):
        self.io_loop = IOLoop(make_current=False)
        # The new IOLoop is not initially made current.
        self.assertIsNone(IOLoop.current(instance=False))
        # Starting the IOLoop makes it current, and stopping the loop
        # makes it non-current. This process is repeatable.
        for i in range(3):

            def f():
                self.current_io_loop = IOLoop.current()
                assert self.io_loop is not None
                self.io_loop.stop()

            self.io_loop.add_callback(f)
            self.io_loop.start()
            self.assertIs(self.current_io_loop, self.io_loop)
            # Now that the loop is stopped, it is no longer current.
            self.assertIsNone(IOLoop.current(instance=False))

    def test_force_current(self):
        self.io_loop = IOLoop(make_current=True)
        self.assertIs(self.io_loop, IOLoop.current())


class TestIOLoopCurrentAsync(AsyncTestCase):
    def setUp(self):
        super().setUp()
        setup_with_context_manager(self, ignore_deprecation())

    @gen_test
    def test_clear_without_current(self):
        # If there is no current IOLoop, clear_current is a no-op (but
        # should not fail). Use a thread so we see the threading.Local
        # in a pristine state.
        with ThreadPoolExecutor(1) as e:
            yield e.submit(IOLoop.clear_current)


class TestIOLoopFutures(AsyncTestCase):
    def test_add_future_threads(self):
        with futures.ThreadPoolExecutor(1) as pool:

            def dummy():
                pass

            self.io_loop.add_future(
                pool.submit(dummy), lambda future: self.stop(future)
            )
            future = self.wait()
            self.assertTrue(future.done())
            self.assertIsNone(future.result())

    @gen_test
    def test_run_in_executor_gen(self):
        event1 = threading.Event()
        event2 = threading.Event()

        def sync_func(self_event, other_event):
            self_event.set()
            other_event.wait()
            # Note that return value doesn't actually do anything,
            # it is just passed through to our final assertion to
            # make sure it is passed through properly.
            return self_event

        # Run two synchronous functions, which would deadlock if not
        # run in parallel.
        res = yield [
            IOLoop.current().run_in_executor(None, sync_func, event1, event2),
            IOLoop.current().run_in_executor(None, sync_func, event2, event1),
        ]

        self.assertEqual([event1, event2], res)

    @gen_test
    def test_run_in_executor_native(self):
        event1 = threading.Event()
        event2 = threading.Event()

        def sync_func(self_event, other_event):
            self_event.set()
            other_event.wait()
            return self_event

        # Go through an async wrapper to ensure that the result of
        # run_in_executor works with await and not just gen.coroutine
        # (simply passing the underlying concurrent future would do that).
        async def async_wrapper(self_event, other_event):
            return await IOLoop.current().run_in_executor(
                None, sync_func, self_event, other_event
            )

        res = yield [async_wrapper(event1, event2), async_wrapper(event2, event1)]

        self.assertEqual([event1, event2], res)

    @gen_test
    def test_set_default_executor(self):
        count = [0]

        class MyExecutor(futures.ThreadPoolExecutor):
            def submit(self, func, *args):
                count[0] += 1
                return super().submit(func, *args)

        event = threading.Event()

        def sync_func():
            event.set()

        executor = MyExecutor(1)
        loop = IOLoop.current()
        loop.set_default_executor(executor)
        yield loop.run_in_executor(None, sync_func)
        self.assertEqual(1, count[0])
        self.assertTrue(event.is_set())


class TestIOLoopRunSync(unittest.TestCase):
    def setUp(self):
        self.io_loop = IOLoop(make_current=False)

    def tearDown(self):
        self.io_loop.close()

    def test_sync_result(self):
        with self.assertRaises(gen.BadYieldError):
            self.io_loop.run_sync(lambda: 42)

    def test_sync_exception(self):
        with self.assertRaises(ZeroDivisionError):
            self.io_loop.run_sync(lambda: 1 / 0)

    def test_async_result(self):
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return(42)

        self.assertEqual(self.io_loop.run_sync(f), 42)

    def test_async_exception(self):
        @gen.coroutine
        def f():
            yield gen.moment
            1 / 0

        with self.assertRaises(ZeroDivisionError):
            self.io_loop.run_sync(f)

    def test_current(self):
        def f():
            self.assertIs(IOLoop.current(), self.io_loop)

        self.io_loop.run_sync(f)

    def test_timeout(self):
        @gen.coroutine
        def f():
            yield gen.sleep(1)

        self.assertRaises(TimeoutError, self.io_loop.run_sync, f, timeout=0.01)

    def test_native_coroutine(self):
        @gen.coroutine
        def f1():
            yield gen.moment

        async def f2():
            await f1()

        self.io_loop.run_sync(f2)

    def test_stop_no_timeout(self):
        async def f():
            await asyncio.sleep(0.1)
            IOLoop.current().stop()
            await asyncio.sleep(10)

        with self.assertRaises(RuntimeError) as cm:
            self.io_loop.run_sync(f)
        assert "Event loop stopped" in str(cm.exception)


class TestPeriodicCallbackMath(unittest.TestCase):
    def simulate_calls(self, pc, durations):
        """Simulate a series of calls to the PeriodicCallback.

        Pass a list of call durations in seconds (negative values
        work to simulate clock adjustments during the call, or more or
        less equivalently, between calls). This method returns the
        times at which each call would be made.
        """
        calls = []
        now = 1000
        pc._next_timeout = now
        for d in durations:
            pc._update_next(now)
            calls.append(pc._next_timeout)
            now = pc._next_timeout + d
        return calls

    def dummy(self):
        pass

    def test_basic(self):
        pc = PeriodicCallback(self.dummy, 10000)
        self.assertEqual(
            self.simulate_calls(pc, [0] * 5), [1010, 1020, 1030, 1040, 1050]
        )

    def test_overrun(self):
        # If a call runs for too long, we skip entire cycles to get
        # back on schedule.
        call_durations = [9, 9, 10, 11, 20, 20, 35, 35, 0, 0, 0]
        expected = [
            1010,
            1020,
            1030,  # first 3 calls on schedule
            1050,
            1070,  # next 2 delayed one cycle
            1100,
            1130,  # next 2 delayed 2 cycles
            1170,
            1210,  # next 2 delayed 3 cycles
            1220,
            1230,  # then back on schedule.
        ]

        pc = PeriodicCallback(self.dummy, 10000)
        self.assertEqual(self.simulate_calls(pc, call_durations), expected)

    def test_clock_backwards(self):
        pc = PeriodicCallback(self.dummy, 10000)
        # Backwards jumps are ignored, potentially resulting in a
        # slightly slow schedule (although we assume that when
        # time.time() and time.monotonic() are different, time.time()
        # is getting adjusted by NTP and is therefore more accurate)
        self.assertEqual(
            self.simulate_calls(pc, [-2, -1, -3, -2, 0]), [1010, 1020, 1030, 1040, 1050]
        )

        # For big jumps, we should perhaps alter the schedule, but we
        # don't currently. This trace shows that we run callbacks
        # every 10s of time.time(), but the first and second calls are
        # 110s of real time apart because the backwards jump is
        # ignored.
        self.assertEqual(self.simulate_calls(pc, [-100, 0, 0]), [1010, 1020, 1030])

    def test_jitter(self):
        random_times = [0.5, 1, 0, 0.75]
        expected = [1010, 1022.5, 1030, 1041.25]
        call_durations = [0] * len(random_times)
        pc = PeriodicCallback(self.dummy, 10000, jitter=0.5)

        def mock_random():
            return random_times.pop(0)

        with mock.patch("random.random", mock_random):
            self.assertEqual(self.simulate_calls(pc, call_durations), expected)

    def test_timedelta(self):
        pc = PeriodicCallback(lambda: None, datetime.timedelta(minutes=1, seconds=23))
        expected_callback_time = 83000
        self.assertEqual(pc.callback_time, expected_callback_time)


class TestPeriodicCallbackAsync(AsyncTestCase):
    def test_periodic_plain(self):
        count = 0

        def callback() -> None:
            nonlocal count
            count += 1
            if count == 3:
                self.stop()

        pc = PeriodicCallback(callback, 10)
        pc.start()
        self.wait()
        pc.stop()
        self.assertEqual(count, 3)

    def test_periodic_coro(self) -> None:
        counts = [0, 0]

        @gen.coroutine
        def callback() -> "Generator[Future[None], object, None]":
            counts[0] += 1
            yield gen.sleep(0.025)
            counts[1] += 1
            if counts[1] == 3:
                pc.stop()
                self.io_loop.add_callback(self.stop)

        pc = PeriodicCallback(callback, 10)
        pc.start()
        self.wait()
        self.assertEqual(counts[0], 3)
        self.assertEqual(counts[1], 3)

    def test_periodic_async(self) -> None:
        counts = [0, 0]

        async def callback() -> None:
            counts[0] += 1
            await gen.sleep(0.025)
            counts[1] += 1
            if counts[1] == 3:
                pc.stop()
                self.io_loop.add_callback(self.stop)

        pc = PeriodicCallback(callback, 10)
        pc.start()
        self.wait()
        self.assertEqual(counts[0], 3)
        self.assertEqual(counts[1], 3)


class TestIOLoopConfiguration(unittest.TestCase):
    def run_python(self, *statements):
        stmt_list = [
            "from tornado.ioloop import IOLoop",
            "classname = lambda x: x.__class__.__name__",
        ] + list(statements)
        args = [sys.executable, "-c", "; ".join(stmt_list)]
        return native_str(subprocess.check_output(args)).strip()

    def test_default(self):
        # When asyncio is available, it is used by default.
        cls = self.run_python("print(classname(IOLoop.current()))")
        self.assertEqual(cls, "AsyncIOMainLoop")
        cls = self.run_python("print(classname(IOLoop()))")
        self.assertEqual(cls, "AsyncIOLoop")

    def test_asyncio(self):
        cls = self.run_python(
            'IOLoop.configure("tornado.platform.asyncio.AsyncIOLoop")',
            "print(classname(IOLoop.current()))",
        )
        self.assertEqual(cls, "AsyncIOMainLoop")

    @unittest.skipIf(
        sys.version_info >= (3, 14), "implicit event loop creation not available"
    )
    def test_asyncio_main(self):
        cls = self.run_python(
            "from tornado.platform.asyncio import AsyncIOMainLoop",
            "AsyncIOMainLoop().install()",
            "print(classname(IOLoop.current()))",
        )
        self.assertEqual(cls, "AsyncIOMainLoop")


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\capi_maps.py ===
"""
Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
from . import __version__

f2py_version = __version__.version

import copy
import os
import re

from . import cb_rules
from ._isocbind import iso_c2py_map, iso_c_binding_map, isoc_c2pycode_map

# The environment provided by auxfuncs.py is needed for some calls to eval.
# As the needed functions cannot be determined by static inspection of the
# code, it is safest to use import * pending a major refactoring of f2py.
from .auxfuncs import *
from .crackfortran import markoutercomma

__all__ = [
    'getctype', 'getstrlength', 'getarrdims', 'getpydocsign',
    'getarrdocsign', 'getinit', 'sign2map', 'routsign2map', 'modsign2map',
    'cb_sign2map', 'cb_routsign2map', 'common_sign2map', 'process_f2cmap_dict'
]


depargs = []
lcb_map = {}
lcb2_map = {}
# forced casting: mainly caused by the fact that Python or Numeric
#                 C/APIs do not support the corresponding C types.
c2py_map = {'double': 'float',
            'float': 'float',                          # forced casting
            'long_double': 'float',                    # forced casting
            'char': 'int',                             # forced casting
            'signed_char': 'int',                      # forced casting
            'unsigned_char': 'int',                    # forced casting
            'short': 'int',                            # forced casting
            'unsigned_short': 'int',                   # forced casting
            'int': 'int',                              # forced casting
            'long': 'int',
            'long_long': 'long',
            'unsigned': 'int',                         # forced casting
            'complex_float': 'complex',                # forced casting
            'complex_double': 'complex',
            'complex_long_double': 'complex',          # forced casting
            'string': 'string',
            'character': 'bytes',
            }

c2capi_map = {'double': 'NPY_DOUBLE',
                'float': 'NPY_FLOAT',
                'long_double': 'NPY_LONGDOUBLE',
                'char': 'NPY_BYTE',
                'unsigned_char': 'NPY_UBYTE',
                'signed_char': 'NPY_BYTE',
                'short': 'NPY_SHORT',
                'unsigned_short': 'NPY_USHORT',
                'int': 'NPY_INT',
                'unsigned': 'NPY_UINT',
                'long': 'NPY_LONG',
                'unsigned_long': 'NPY_ULONG',
                'long_long': 'NPY_LONGLONG',
                'unsigned_long_long': 'NPY_ULONGLONG',
                'complex_float': 'NPY_CFLOAT',
                'complex_double': 'NPY_CDOUBLE',
                'complex_long_double': 'NPY_CDOUBLE',
                'string': 'NPY_STRING',
                'character': 'NPY_STRING'}

c2pycode_map = {'double': 'd',
                'float': 'f',
                'long_double': 'g',
                'char': 'b',
                'unsigned_char': 'B',
                'signed_char': 'b',
                'short': 'h',
                'unsigned_short': 'H',
                'int': 'i',
                'unsigned': 'I',
                'long': 'l',
                'unsigned_long': 'L',
                'long_long': 'q',
                'unsigned_long_long': 'Q',
                'complex_float': 'F',
                'complex_double': 'D',
                'complex_long_double': 'G',
                'string': 'S',
                'character': 'c'}

# https://docs.python.org/3/c-api/arg.html#building-values
c2buildvalue_map = {'double': 'd',
                    'float': 'f',
                    'char': 'b',
                    'signed_char': 'b',
                    'short': 'h',
                    'int': 'i',
                    'long': 'l',
                    'long_long': 'L',
                    'complex_float': 'N',
                    'complex_double': 'N',
                    'complex_long_double': 'N',
                    'string': 'y',
                    'character': 'c'}

f2cmap_all = {'real': {'': 'float', '4': 'float', '8': 'double',
                       '12': 'long_double', '16': 'long_double'},
              'integer': {'': 'int', '1': 'signed_char', '2': 'short',
                          '4': 'int', '8': 'long_long',
                          '-1': 'unsigned_char', '-2': 'unsigned_short',
                          '-4': 'unsigned', '-8': 'unsigned_long_long'},
              'complex': {'': 'complex_float', '8': 'complex_float',
                          '16': 'complex_double', '24': 'complex_long_double',
                          '32': 'complex_long_double'},
              'complexkind': {'': 'complex_float', '4': 'complex_float',
                              '8': 'complex_double', '12': 'complex_long_double',
                              '16': 'complex_long_double'},
              'logical': {'': 'int', '1': 'char', '2': 'short', '4': 'int',
                          '8': 'long_long'},
              'double complex': {'': 'complex_double'},
              'double precision': {'': 'double'},
              'byte': {'': 'char'},
              }

# Add ISO_C handling
c2pycode_map.update(isoc_c2pycode_map)
c2py_map.update(iso_c2py_map)
f2cmap_all, _ = process_f2cmap_dict(f2cmap_all, iso_c_binding_map, c2py_map)
# End ISO_C handling
f2cmap_default = copy.deepcopy(f2cmap_all)

f2cmap_mapped = []

def load_f2cmap_file(f2cmap_file):
    global f2cmap_all, f2cmap_mapped

    f2cmap_all = copy.deepcopy(f2cmap_default)

    if f2cmap_file is None:
        # Default value
        f2cmap_file = '.f2py_f2cmap'
        if not os.path.isfile(f2cmap_file):
            return

    # User defined additions to f2cmap_all.
    # f2cmap_file must contain a dictionary of dictionaries, only. For
    # example, {'real':{'low':'float'}} means that Fortran 'real(low)' is
    # interpreted as C 'float'. This feature is useful for F90/95 users if
    # they use PARAMETERS in type specifications.
    try:
        outmess(f'Reading f2cmap from {f2cmap_file!r} ...\n')
        with open(f2cmap_file) as f:
            d = eval(f.read().lower(), {}, {})
        f2cmap_all, f2cmap_mapped = process_f2cmap_dict(f2cmap_all, d, c2py_map, True)
        outmess('Successfully applied user defined f2cmap changes\n')
    except Exception as msg:
        errmess(f'Failed to apply user defined f2cmap changes: {msg}. Skipping.\n')


cformat_map = {'double': '%g',
               'float': '%g',
               'long_double': '%Lg',
               'char': '%d',
               'signed_char': '%d',
               'unsigned_char': '%hhu',
               'short': '%hd',
               'unsigned_short': '%hu',
               'int': '%d',
               'unsigned': '%u',
               'long': '%ld',
               'unsigned_long': '%lu',
               'long_long': '%ld',
               'complex_float': '(%g,%g)',
               'complex_double': '(%g,%g)',
               'complex_long_double': '(%Lg,%Lg)',
               'string': '\\"%s\\"',
               'character': "'%c'",
               }

# Auxiliary functions


def getctype(var):
    """
    Determines C type
    """
    ctype = 'void'
    if isfunction(var):
        if 'result' in var:
            a = var['result']
        else:
            a = var['name']
        if a in var['vars']:
            return getctype(var['vars'][a])
        else:
            errmess(f'getctype: function {a} has no return value?!\n')
    elif issubroutine(var):
        return ctype
    elif ischaracter_or_characterarray(var):
        return 'character'
    elif isstring_or_stringarray(var):
        return 'string'
    elif 'typespec' in var and var['typespec'].lower() in f2cmap_all:
        typespec = var['typespec'].lower()
        f2cmap = f2cmap_all[typespec]
        ctype = f2cmap['']  # default type
        if 'kindselector' in var:
            if '*' in var['kindselector']:
                try:
                    ctype = f2cmap[var['kindselector']['*']]
                except KeyError:
                    errmess('getctype: "%s %s %s" not supported.\n' %
                            (var['typespec'], '*', var['kindselector']['*']))
            elif 'kind' in var['kindselector']:
                if typespec + 'kind' in f2cmap_all:
                    f2cmap = f2cmap_all[typespec + 'kind']
                try:
                    ctype = f2cmap[var['kindselector']['kind']]
                except KeyError:
                    if typespec in f2cmap_all:
                        f2cmap = f2cmap_all[typespec]
                    try:
                        ctype = f2cmap[str(var['kindselector']['kind'])]
                    except KeyError:
                        errmess('getctype: "%s(kind=%s)" is mapped to C "%s" (to override define dict(%s = dict(%s="<C typespec>")) in %s/.f2py_f2cmap file).\n'
                                % (typespec, var['kindselector']['kind'], ctype,
                                   typespec, var['kindselector']['kind'], os.getcwd()))
    elif not isexternal(var):
        errmess(f'getctype: No C-type found in "{var}", assuming void.\n')
    return ctype


def f2cexpr(expr):
    """Rewrite Fortran expression as f2py supported C expression.

    Due to the lack of a proper expression parser in f2py, this
    function uses a heuristic approach that assumes that Fortran
    arithmetic expressions are valid C arithmetic expressions when
    mapping Fortran function calls to the corresponding C function/CPP
    macros calls.

    """
    # TODO: support Fortran `len` function with optional kind parameter
    expr = re.sub(r'\blen\b', 'f2py_slen', expr)
    return expr


def getstrlength(var):
    if isstringfunction(var):
        if 'result' in var:
            a = var['result']
        else:
            a = var['name']
        if a in var['vars']:
            return getstrlength(var['vars'][a])
        else:
            errmess(f'getstrlength: function {a} has no return value?!\n')
    if not isstring(var):
        errmess(
            f'getstrlength: expected a signature of a string but got: {repr(var)}\n')
    len = '1'
    if 'charselector' in var:
        a = var['charselector']
        if '*' in a:
            len = a['*']
        elif 'len' in a:
            len = f2cexpr(a['len'])
    if re.match(r'\(\s*(\*|:)\s*\)', len) or re.match(r'(\*|:)', len):
        if isintent_hide(var):
            errmess('getstrlength:intent(hide): expected a string with defined length but got: %s\n' % (
                repr(var)))
        len = '-1'
    return len


def getarrdims(a, var, verbose=0):
    ret = {}
    if isstring(var) and not isarray(var):
        ret['size'] = getstrlength(var)
        ret['rank'] = '0'
        ret['dims'] = ''
    elif isscalar(var):
        ret['size'] = '1'
        ret['rank'] = '0'
        ret['dims'] = ''
    elif isarray(var):
        dim = copy.copy(var['dimension'])
        ret['size'] = '*'.join(dim)
        try:
            ret['size'] = repr(eval(ret['size']))
        except Exception:
            pass
        ret['dims'] = ','.join(dim)
        ret['rank'] = repr(len(dim))
        ret['rank*[-1]'] = repr(len(dim) * [-1])[1:-1]
        for i in range(len(dim)):  # solve dim for dependencies
            v = []
            if dim[i] in depargs:
                v = [dim[i]]
            else:
                for va in depargs:
                    if re.match(r'.*?\b%s\b.*' % va, dim[i]):
                        v.append(va)
            for va in v:
                if depargs.index(va) > depargs.index(a):
                    dim[i] = '*'
                    break
        ret['setdims'], i = '', -1
        for d in dim:
            i = i + 1
            if d not in ['*', ':', '(*)', '(:)']:
                ret['setdims'] = '%s#varname#_Dims[%d]=%s,' % (
                    ret['setdims'], i, d)
        if ret['setdims']:
            ret['setdims'] = ret['setdims'][:-1]
        ret['cbsetdims'], i = '', -1
        for d in var['dimension']:
            i = i + 1
            if d not in ['*', ':', '(*)', '(:)']:
                ret['cbsetdims'] = '%s#varname#_Dims[%d]=%s,' % (
                    ret['cbsetdims'], i, d)
            elif isintent_in(var):
                outmess('getarrdims:warning: assumed shape array, using 0 instead of %r\n'
                        % (d))
                ret['cbsetdims'] = '%s#varname#_Dims[%d]=%s,' % (
                    ret['cbsetdims'], i, 0)
            elif verbose:
                errmess(
                    f'getarrdims: If in call-back function: array argument {repr(a)} must have bounded dimensions: got {repr(d)}\n')
        if ret['cbsetdims']:
            ret['cbsetdims'] = ret['cbsetdims'][:-1]
#         if not isintent_c(var):
#             var['dimension'].reverse()
    return ret


def getpydocsign(a, var):
    global lcb_map
    if isfunction(var):
        if 'result' in var:
            af = var['result']
        else:
            af = var['name']
        if af in var['vars']:
            return getpydocsign(af, var['vars'][af])
        else:
            errmess(f'getctype: function {af} has no return value?!\n')
        return '', ''
    sig, sigout = a, a
    opt = ''
    if isintent_in(var):
        opt = 'input'
    elif isintent_inout(var):
        opt = 'in/output'
    out_a = a
    if isintent_out(var):
        for k in var['intent']:
            if k[:4] == 'out=':
                out_a = k[4:]
                break
    init = ''
    ctype = getctype(var)

    if hasinitvalue(var):
        init, showinit = getinit(a, var)
        init = f', optional\\n    Default: {showinit}'
    if isscalar(var):
        if isintent_inout(var):
            sig = '%s : %s rank-0 array(%s,\'%s\')%s' % (a, opt, c2py_map[ctype],
                                                         c2pycode_map[ctype], init)
        else:
            sig = f'{a} : {opt} {c2py_map[ctype]}{init}'
        sigout = f'{out_a} : {c2py_map[ctype]}'
    elif isstring(var):
        if isintent_inout(var):
            sig = '%s : %s rank-0 array(string(len=%s),\'c\')%s' % (
                a, opt, getstrlength(var), init)
        else:
            sig = f'{a} : {opt} string(len={getstrlength(var)}){init}'
        sigout = f'{out_a} : string(len={getstrlength(var)})'
    elif isarray(var):
        dim = var['dimension']
        rank = repr(len(dim))
        sig = '%s : %s rank-%s array(\'%s\') with bounds (%s)%s' % (a, opt, rank,
                                                                    c2pycode_map[
                                                                        ctype],
                                                                    ','.join(dim), init)
        if a == out_a:
            sigout = '%s : rank-%s array(\'%s\') with bounds (%s)'\
                % (a, rank, c2pycode_map[ctype], ','.join(dim))
        else:
            sigout = '%s : rank-%s array(\'%s\') with bounds (%s) and %s storage'\
                % (out_a, rank, c2pycode_map[ctype], ','.join(dim), a)
    elif isexternal(var):
        ua = ''
        if a in lcb_map and lcb_map[a] in lcb2_map and 'argname' in lcb2_map[lcb_map[a]]:
            ua = lcb2_map[lcb_map[a]]['argname']
            if not ua == a:
                ua = f' => {ua}'
            else:
                ua = ''
        sig = f'{a} : call-back function{ua}'
        sigout = sig
    else:
        errmess(
            f'getpydocsign: Could not resolve docsignature for "{a}".\n')
    return sig, sigout


def getarrdocsign(a, var):
    ctype = getctype(var)
    if isstring(var) and (not isarray(var)):
        sig = f'{a} : rank-0 array(string(len={getstrlength(var)}),\'c\')'
    elif isscalar(var):
        sig = f'{a} : rank-0 array({c2py_map[ctype]},\'{c2pycode_map[ctype]}\')'
    elif isarray(var):
        dim = var['dimension']
        rank = repr(len(dim))
        sig = '%s : rank-%s array(\'%s\') with bounds (%s)' % (a, rank,
                                                               c2pycode_map[
                                                                   ctype],
                                                               ','.join(dim))
    return sig


def getinit(a, var):
    if isstring(var):
        init, showinit = '""', "''"
    else:
        init, showinit = '', ''
    if hasinitvalue(var):
        init = var['=']
        showinit = init
        if iscomplex(var) or iscomplexarray(var):
            ret = {}

            try:
                v = var["="]
                if ',' in v:
                    ret['init.r'], ret['init.i'] = markoutercomma(
                        v[1:-1]).split('@,@')
                else:
                    v = eval(v, {}, {})
                    ret['init.r'], ret['init.i'] = str(v.real), str(v.imag)
            except Exception:
                raise ValueError(
                    f'getinit: expected complex number `(r,i)\' but got `{init}\' as initial value of {a!r}.')
            if isarray(var):
                init = f"(capi_c.r={ret['init.r']},capi_c.i={ret['init.i']},capi_c)"
        elif isstring(var):
            if not init:
                init, showinit = '""', "''"
            if init[0] == "'":
                init = '"%s"' % (init[1:-1].replace('"', '\\"'))
            if init[0] == '"':
                showinit = f"'{init[1:-1]}'"
    return init, showinit


def get_elsize(var):
    if isstring(var) or isstringarray(var):
        elsize = getstrlength(var)
        # override with user-specified length when available:
        elsize = var['charselector'].get('f2py_len', elsize)
        return elsize
    if ischaracter(var) or ischaracterarray(var):
        return '1'
    # for numerical types, PyArray_New* functions ignore specified
    # elsize, so we just return 1 and let elsize be determined at
    # runtime, see fortranobject.c
    return '1'


def sign2map(a, var):
    """
    varname,ctype,atype
    init,init.r,init.i,pytype
    vardebuginfo,vardebugshowvalue,varshowvalue
    varrformat

    intent
    """
    out_a = a
    if isintent_out(var):
        for k in var['intent']:
            if k[:4] == 'out=':
                out_a = k[4:]
                break
    ret = {'varname': a, 'outvarname': out_a, 'ctype': getctype(var)}
    intent_flags = []
    for f, s in isintent_dict.items():
        if f(var):
            intent_flags.append(f'F2PY_{s}')
    if intent_flags:
        # TODO: Evaluate intent_flags here.
        ret['intent'] = '|'.join(intent_flags)
    else:
        ret['intent'] = 'F2PY_INTENT_IN'
    if isarray(var):
        ret['varrformat'] = 'N'
    elif ret['ctype'] in c2buildvalue_map:
        ret['varrformat'] = c2buildvalue_map[ret['ctype']]
    else:
        ret['varrformat'] = 'O'
    ret['init'], ret['showinit'] = getinit(a, var)
    if hasinitvalue(var) and iscomplex(var) and not isarray(var):
        ret['init.r'], ret['init.i'] = markoutercomma(
            ret['init'][1:-1]).split('@,@')
    if isexternal(var):
        ret['cbnamekey'] = a
        if a in lcb_map:
            ret['cbname'] = lcb_map[a]
            ret['maxnofargs'] = lcb2_map[lcb_map[a]]['maxnofargs']
            ret['nofoptargs'] = lcb2_map[lcb_map[a]]['nofoptargs']
            ret['cbdocstr'] = lcb2_map[lcb_map[a]]['docstr']
            ret['cblatexdocstr'] = lcb2_map[lcb_map[a]]['latexdocstr']
        else:
            ret['cbname'] = a
            errmess('sign2map: Confused: external %s is not in lcb_map%s.\n' % (
                a, list(lcb_map.keys())))
    if isstring(var):
        ret['length'] = getstrlength(var)
    if isarray(var):
        ret = dictappend(ret, getarrdims(a, var))
        dim = copy.copy(var['dimension'])
    if ret['ctype'] in c2capi_map:
        ret['atype'] = c2capi_map[ret['ctype']]
        ret['elsize'] = get_elsize(var)
    # Debug info
    if debugcapi(var):
        il = [isintent_in, 'input', isintent_out, 'output',
              isintent_inout, 'inoutput', isrequired, 'required',
              isoptional, 'optional', isintent_hide, 'hidden',
              iscomplex, 'complex scalar',
              l_and(isscalar, l_not(iscomplex)), 'scalar',
              isstring, 'string', isarray, 'array',
              iscomplexarray, 'complex array', isstringarray, 'string array',
              iscomplexfunction, 'complex function',
              l_and(isfunction, l_not(iscomplexfunction)), 'function',
              isexternal, 'callback',
              isintent_callback, 'callback',
              isintent_aux, 'auxiliary',
              ]
        rl = []
        for i in range(0, len(il), 2):
            if il[i](var):
                rl.append(il[i + 1])
        if isstring(var):
            rl.append(f"slen({a})={ret['length']}")
        if isarray(var):
            ddim = ','.join(
                map(lambda x, y: f'{x}|{y}', var['dimension'], dim))
            rl.append(f'dims({ddim})')
        if isexternal(var):
            ret['vardebuginfo'] = f"debug-capi:{a}=>{ret['cbname']}:{','.join(rl)}"
        else:
            ret['vardebuginfo'] = 'debug-capi:%s %s=%s:%s' % (
                ret['ctype'], a, ret['showinit'], ','.join(rl))
        if isscalar(var):
            if ret['ctype'] in cformat_map:
                ret['vardebugshowvalue'] = f"debug-capi:{a}={cformat_map[ret['ctype']]}"
        if isstring(var):
            ret['vardebugshowvalue'] = 'debug-capi:slen(%s)=%%d %s=\\"%%s\\"' % (
                a, a)
        if isexternal(var):
            ret['vardebugshowvalue'] = f'debug-capi:{a}=%p'
    if ret['ctype'] in cformat_map:
        ret['varshowvalue'] = f"#name#:{a}={cformat_map[ret['ctype']]}"
        ret['showvalueformat'] = f"{cformat_map[ret['ctype']]}"
    if isstring(var):
        ret['varshowvalue'] = '#name#:slen(%s)=%%d %s=\\"%%s\\"' % (a, a)
    ret['pydocsign'], ret['pydocsignout'] = getpydocsign(a, var)
    if hasnote(var):
        ret['note'] = var['note']
    return ret


def routsign2map(rout):
    """
    name,NAME,begintitle,endtitle
    rname,ctype,rformat
    routdebugshowvalue
    """
    global lcb_map
    name = rout['name']
    fname = getfortranname(rout)
    ret = {'name': name,
           'texname': name.replace('_', '\\_'),
           'name_lower': name.lower(),
           'NAME': name.upper(),
           'begintitle': gentitle(name),
           'endtitle': gentitle(f'end of {name}'),
           'fortranname': fname,
           'FORTRANNAME': fname.upper(),
           'callstatement': getcallstatement(rout) or '',
           'usercode': getusercode(rout) or '',
           'usercode1': getusercode1(rout) or '',
           }
    if '_' in fname:
        ret['F_FUNC'] = 'F_FUNC_US'
    else:
        ret['F_FUNC'] = 'F_FUNC'
    if '_' in name:
        ret['F_WRAPPEDFUNC'] = 'F_WRAPPEDFUNC_US'
    else:
        ret['F_WRAPPEDFUNC'] = 'F_WRAPPEDFUNC'
    lcb_map = {}
    if 'use' in rout:
        for u in rout['use'].keys():
            if u in cb_rules.cb_map:
                for un in cb_rules.cb_map[u]:
                    ln = un[0]
                    if 'map' in rout['use'][u]:
                        for k in rout['use'][u]['map'].keys():
                            if rout['use'][u]['map'][k] == un[0]:
                                ln = k
                                break
                    lcb_map[ln] = un[1]
    elif rout.get('externals'):
        errmess('routsign2map: Confused: function %s has externals %s but no "use" statement.\n' % (
            ret['name'], repr(rout['externals'])))
    ret['callprotoargument'] = getcallprotoargument(rout, lcb_map) or ''
    if isfunction(rout):
        if 'result' in rout:
            a = rout['result']
        else:
            a = rout['name']
        ret['rname'] = a
        ret['pydocsign'], ret['pydocsignout'] = getpydocsign(a, rout)
        ret['ctype'] = getctype(rout['vars'][a])
        if hasresultnote(rout):
            ret['resultnote'] = rout['vars'][a]['note']
            rout['vars'][a]['note'] = ['See elsewhere.']
        if ret['ctype'] in c2buildvalue_map:
            ret['rformat'] = c2buildvalue_map[ret['ctype']]
        else:
            ret['rformat'] = 'O'
            errmess('routsign2map: no c2buildvalue key for type %s\n' %
                    (repr(ret['ctype'])))
        if debugcapi(rout):
            if ret['ctype'] in cformat_map:
                ret['routdebugshowvalue'] = 'debug-capi:%s=%s' % (
                    a, cformat_map[ret['ctype']])
            if isstringfunction(rout):
                ret['routdebugshowvalue'] = 'debug-capi:slen(%s)=%%d %s=\\"%%s\\"' % (
                    a, a)
        if isstringfunction(rout):
            ret['rlength'] = getstrlength(rout['vars'][a])
            if ret['rlength'] == '-1':
                errmess('routsign2map: expected explicit specification of the length of the string returned by the fortran function %s; taking 10.\n' % (
                    repr(rout['name'])))
                ret['rlength'] = '10'
    if hasnote(rout):
        ret['note'] = rout['note']
        rout['note'] = ['See elsewhere.']
    return ret


def modsign2map(m):
    """
    modulename
    """
    if ismodule(m):
        ret = {'f90modulename': m['name'],
               'F90MODULENAME': m['name'].upper(),
               'texf90modulename': m['name'].replace('_', '\\_')}
    else:
        ret = {'modulename': m['name'],
               'MODULENAME': m['name'].upper(),
               'texmodulename': m['name'].replace('_', '\\_')}
    ret['restdoc'] = getrestdoc(m) or []
    if hasnote(m):
        ret['note'] = m['note']
    ret['usercode'] = getusercode(m) or ''
    ret['usercode1'] = getusercode1(m) or ''
    if m['body']:
        ret['interface_usercode'] = getusercode(m['body'][0]) or ''
    else:
        ret['interface_usercode'] = ''
    ret['pymethoddef'] = getpymethoddef(m) or ''
    if 'gil_used' in m:
        ret['gil_used'] = m['gil_used']
    if 'coutput' in m:
        ret['coutput'] = m['coutput']
    if 'f2py_wrapper_output' in m:
        ret['f2py_wrapper_output'] = m['f2py_wrapper_output']
    return ret


def cb_sign2map(a, var, index=None):
    ret = {'varname': a}
    ret['varname_i'] = ret['varname']
    ret['ctype'] = getctype(var)
    if ret['ctype'] in c2capi_map:
        ret['atype'] = c2capi_map[ret['ctype']]
        ret['elsize'] = get_elsize(var)
    if ret['ctype'] in cformat_map:
        ret['showvalueformat'] = f"{cformat_map[ret['ctype']]}"
    if isarray(var):
        ret = dictappend(ret, getarrdims(a, var))
    ret['pydocsign'], ret['pydocsignout'] = getpydocsign(a, var)
    if hasnote(var):
        ret['note'] = var['note']
        var['note'] = ['See elsewhere.']
    return ret


def cb_routsign2map(rout, um):
    """
    name,begintitle,endtitle,argname
    ctype,rctype,maxnofargs,nofoptargs,returncptr
    """
    ret = {'name': f"cb_{rout['name']}_in_{um}",
           'returncptr': ''}
    if isintent_callback(rout):
        if '_' in rout['name']:
            F_FUNC = 'F_FUNC_US'
        else:
            F_FUNC = 'F_FUNC'
        ret['callbackname'] = f"{F_FUNC}({rout['name'].lower()},{rout['name'].upper()})"
        ret['static'] = 'extern'
    else:
        ret['callbackname'] = ret['name']
        ret['static'] = 'static'
    ret['argname'] = rout['name']
    ret['begintitle'] = gentitle(ret['name'])
    ret['endtitle'] = gentitle(f"end of {ret['name']}")
    ret['ctype'] = getctype(rout)
    ret['rctype'] = 'void'
    if ret['ctype'] == 'string':
        ret['rctype'] = 'void'
    else:
        ret['rctype'] = ret['ctype']
    if ret['rctype'] != 'void':
        if iscomplexfunction(rout):
            ret['returncptr'] = """
#ifdef F2PY_CB_RETURNCOMPLEX
return_value=
#endif
"""
        else:
            ret['returncptr'] = 'return_value='
    if ret['ctype'] in cformat_map:
        ret['showvalueformat'] = f"{cformat_map[ret['ctype']]}"
    if isstringfunction(rout):
        ret['strlength'] = getstrlength(rout)
    if isfunction(rout):
        if 'result' in rout:
            a = rout['result']
        else:
            a = rout['name']
        if hasnote(rout['vars'][a]):
            ret['note'] = rout['vars'][a]['note']
            rout['vars'][a]['note'] = ['See elsewhere.']
        ret['rname'] = a
        ret['pydocsign'], ret['pydocsignout'] = getpydocsign(a, rout)
        if iscomplexfunction(rout):
            ret['rctype'] = """
#ifdef F2PY_CB_RETURNCOMPLEX
#ctype#
#else
void
#endif
"""
    elif hasnote(rout):
        ret['note'] = rout['note']
        rout['note'] = ['See elsewhere.']
    nofargs = 0
    nofoptargs = 0
    if 'args' in rout and 'vars' in rout:
        for a in rout['args']:
            var = rout['vars'][a]
            if l_or(isintent_in, isintent_inout)(var):
                nofargs = nofargs + 1
                if isoptional(var):
                    nofoptargs = nofoptargs + 1
    ret['maxnofargs'] = repr(nofargs)
    ret['nofoptargs'] = repr(nofoptargs)
    if hasnote(rout) and isfunction(rout) and 'result' in rout:
        ret['routnote'] = rout['note']
        rout['note'] = ['See elsewhere.']
    return ret


def common_sign2map(a, var):  # obsolete
    ret = {'varname': a, 'ctype': getctype(var)}
    if isstringarray(var):
        ret['ctype'] = 'char'
    if ret['ctype'] in c2capi_map:
        ret['atype'] = c2capi_map[ret['ctype']]
        ret['elsize'] = get_elsize(var)
    if ret['ctype'] in cformat_map:
        ret['showvalueformat'] = f"{cformat_map[ret['ctype']]}"
    if isarray(var):
        ret = dictappend(ret, getarrdims(a, var))
    elif isstring(var):
        ret['size'] = getstrlength(var)
        ret['rank'] = '1'
    ret['pydocsign'], ret['pydocsignout'] = getpydocsign(a, var)
    if hasnote(var):
        ret['note'] = var['note']
        var['note'] = ['See elsewhere.']
    # for strings this returns 0-rank but actually is 1-rank
    ret['arrdocstr'] = getarrdocsign(a, var)
    return ret