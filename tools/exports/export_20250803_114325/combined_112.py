
# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\transports\rest.py ===
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

from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import PermissionServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class PermissionServiceRestInterceptor:
    """Interceptor for PermissionService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the PermissionServiceRestTransport.

    .. code-block:: python
        class MyCustomPermissionServiceInterceptor(PermissionServiceRestInterceptor):
            def pre_create_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_permissions(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_permissions(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_transfer_ownership(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_transfer_ownership(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_update_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = PermissionServiceRestTransport(interceptor=MyCustomPermissionServiceInterceptor())
        client = PermissionServiceClient(transport=transport)


    """

    def pre_create_permission(
        self,
        request: permission_service.CreatePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.CreatePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_create_permission(
        self, response: gag_permission.Permission
    ) -> gag_permission.Permission:
        """Post-rpc interceptor for create_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_permission(
        self,
        request: permission_service.DeletePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.DeletePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def pre_get_permission(
        self,
        request: permission_service.GetPermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.GetPermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_get_permission(
        self, response: permission.Permission
    ) -> permission.Permission:
        """Post-rpc interceptor for get_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_list_permissions(
        self,
        request: permission_service.ListPermissionsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.ListPermissionsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_permissions

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_list_permissions(
        self, response: permission_service.ListPermissionsResponse
    ) -> permission_service.ListPermissionsResponse:
        """Post-rpc interceptor for list_permissions

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_transfer_ownership(
        self,
        request: permission_service.TransferOwnershipRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.TransferOwnershipRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for transfer_ownership

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_transfer_ownership(
        self, response: permission_service.TransferOwnershipResponse
    ) -> permission_service.TransferOwnershipResponse:
        """Post-rpc interceptor for transfer_ownership

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_update_permission(
        self,
        request: permission_service.UpdatePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.UpdatePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for update_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_update_permission(
        self, response: gag_permission.Permission
    ) -> gag_permission.Permission:
        """Post-rpc interceptor for update_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class PermissionServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: PermissionServiceRestInterceptor


class PermissionServiceRestTransport(PermissionServiceTransport):
    """REST backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

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
        interceptor: Optional[PermissionServiceRestInterceptor] = None,
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
        self._interceptor = interceptor or PermissionServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CreatePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("CreatePermission")

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
            request: permission_service.CreatePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_permission.Permission:
            r"""Call the create permission method over HTTP.

            Args:
                request (~.permission_service.CreatePermissionRequest):
                    The request object. Request to create a ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_permission.Permission:
                    Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{parent=tunedModels/*}/permissions",
                    "body": "permission",
                },
            ]
            request, metadata = self._interceptor.pre_create_permission(
                request, metadata
            )
            pb_request = permission_service.CreatePermissionRequest.pb(request)
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
            resp = gag_permission.Permission()
            pb_resp = gag_permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_permission(resp)
            return resp

    class _DeletePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("DeletePermission")

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
            request: permission_service.DeletePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete permission method over HTTP.

            Args:
                request (~.permission_service.DeletePermissionRequest):
                    The request object. Request to delete the ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta3/{name=tunedModels/*/permissions/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_permission(
                request, metadata
            )
            pb_request = permission_service.DeletePermissionRequest.pb(request)
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

    class _GetPermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("GetPermission")

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
            request: permission_service.GetPermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission.Permission:
            r"""Call the get permission method over HTTP.

            Args:
                request (~.permission_service.GetPermissionRequest):
                    The request object. Request for getting information about a specific
                ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission.Permission:
                    Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/{name=tunedModels/*/permissions/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_permission(request, metadata)
            pb_request = permission_service.GetPermissionRequest.pb(request)
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
            resp = permission.Permission()
            pb_resp = permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_permission(resp)
            return resp

    class _ListPermissions(PermissionServiceRestStub):
        def __hash__(self):
            return hash("ListPermissions")

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
            request: permission_service.ListPermissionsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission_service.ListPermissionsResponse:
            r"""Call the list permissions method over HTTP.

            Args:
                request (~.permission_service.ListPermissionsRequest):
                    The request object. Request for listing permissions.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission_service.ListPermissionsResponse:
                    Response from ``ListPermissions`` containing a paginated
                list of permissions.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/{parent=tunedModels/*}/permissions",
                },
            ]
            request, metadata = self._interceptor.pre_list_permissions(
                request, metadata
            )
            pb_request = permission_service.ListPermissionsRequest.pb(request)
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
            resp = permission_service.ListPermissionsResponse()
            pb_resp = permission_service.ListPermissionsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_permissions(resp)
            return resp

    class _TransferOwnership(PermissionServiceRestStub):
        def __hash__(self):
            return hash("TransferOwnership")

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
            request: permission_service.TransferOwnershipRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission_service.TransferOwnershipResponse:
            r"""Call the transfer ownership method over HTTP.

            Args:
                request (~.permission_service.TransferOwnershipRequest):
                    The request object. Request to transfer the ownership of
                the tuned model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission_service.TransferOwnershipResponse:
                    Response from ``TransferOwnership``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{name=tunedModels/*}:transferOwnership",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_transfer_ownership(
                request, metadata
            )
            pb_request = permission_service.TransferOwnershipRequest.pb(request)
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
            resp = permission_service.TransferOwnershipResponse()
            pb_resp = permission_service.TransferOwnershipResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_transfer_ownership(resp)
            return resp

    class _UpdatePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("UpdatePermission")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {
            "updateMask": {},
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.UpdatePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_permission.Permission:
            r"""Call the update permission method over HTTP.

            Args:
                request (~.permission_service.UpdatePermissionRequest):
                    The request object. Request to update the ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_permission.Permission:
                    Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "patch",
                    "uri": "/v1beta3/{permission.name=tunedModels/*/permissions/*}",
                    "body": "permission",
                },
            ]
            request, metadata = self._interceptor.pre_update_permission(
                request, metadata
            )
            pb_request = permission_service.UpdatePermissionRequest.pb(request)
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
            resp = gag_permission.Permission()
            pb_resp = gag_permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_update_permission(resp)
            return resp

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest], gag_permission.Permission
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreatePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_permission(
        self,
    ) -> Callable[[permission_service.DeletePermissionRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeletePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_permission(
        self,
    ) -> Callable[[permission_service.GetPermissionRequest], permission.Permission]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetPermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        permission_service.ListPermissionsResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListPermissions(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        permission_service.TransferOwnershipResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._TransferOwnership(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest], gag_permission.Permission
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdatePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("PermissionServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\pretty.py ===
import builtins
import collections
import dataclasses
import inspect
import os
import reprlib
import sys
from array import array
from collections import Counter, UserDict, UserList, defaultdict, deque
from dataclasses import dataclass, fields, is_dataclass
from inspect import isclass
from itertools import islice
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from pip._vendor.rich.repr import RichReprResult

try:
    import attr as _attr_module

    _has_attrs = hasattr(_attr_module, "ib")
except ImportError:  # pragma: no cover
    _has_attrs = False

from . import get_console
from ._loop import loop_last
from ._pick import pick_bool
from .abc import RichRenderable
from .cells import cell_len
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin, JupyterRenderable
from .measure import Measurement
from .text import Text

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        HighlighterType,
        JustifyMethod,
        OverflowMethod,
        RenderResult,
    )


def _is_attr_object(obj: Any) -> bool:
    """Check if an object was created with attrs module."""
    return _has_attrs and _attr_module.has(type(obj))


def _get_attr_fields(obj: Any) -> Sequence["_attr_module.Attribute[Any]"]:
    """Get fields for an attrs object."""
    return _attr_module.fields(type(obj)) if _has_attrs else []


def _is_dataclass_repr(obj: object) -> bool:
    """Check if an instance of a dataclass contains the default repr.

    Args:
        obj (object): A dataclass instance.

    Returns:
        bool: True if the default repr is used, False if there is a custom repr.
    """
    # Digging in to a lot of internals here
    # Catching all exceptions in case something is missing on a non CPython implementation
    try:
        return obj.__repr__.__code__.co_filename in (
            dataclasses.__file__,
            reprlib.__file__,
        )
    except Exception:  # pragma: no coverage
        return False


_dummy_namedtuple = collections.namedtuple("_dummy_namedtuple", [])


def _has_default_namedtuple_repr(obj: object) -> bool:
    """Check if an instance of namedtuple contains the default repr

    Args:
        obj (object): A namedtuple

    Returns:
        bool: True if the default repr is used, False if there's a custom repr.
    """
    obj_file = None
    try:
        obj_file = inspect.getfile(obj.__repr__)
    except (OSError, TypeError):
        # OSError handles case where object is defined in __main__ scope, e.g. REPL - no filename available.
        # TypeError trapped defensively, in case of object without filename slips through.
        pass
    default_repr_file = inspect.getfile(_dummy_namedtuple.__repr__)
    return obj_file == default_repr_file


def _ipy_display_hook(
    value: Any,
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> Union[str, None]:
    # needed here to prevent circular import:
    from .console import ConsoleRenderable

    # always skip rich generated jupyter renderables or None values
    if _safe_isinstance(value, JupyterRenderable) or value is None:
        return None

    console = console or get_console()

    with console.capture() as capture:
        # certain renderables should start on a new line
        if _safe_isinstance(value, ConsoleRenderable):
            console.line()
        console.print(
            (
                value
                if _safe_isinstance(value, RichRenderable)
                else Pretty(
                    value,
                    overflow=overflow,
                    indent_guides=indent_guides,
                    max_length=max_length,
                    max_string=max_string,
                    max_depth=max_depth,
                    expand_all=expand_all,
                    margin=12,
                )
            ),
            crop=crop,
            new_line_start=True,
            end="",
        )
    # strip trailing newline, not usually part of a text repr
    # I'm not sure if this should be prevented at a lower level
    return capture.get().rstrip("\n")


def _safe_isinstance(
    obj: object, class_or_tuple: Union[type, Tuple[type, ...]]
) -> bool:
    """isinstance can fail in rare cases, for example types with no __class__"""
    try:
        return isinstance(obj, class_or_tuple)
    except Exception:
        return False


def install(
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """Install automatic pretty printing in the Python REPL.

    Args:
        console (Console, optional): Console instance or ``None`` to use global console. Defaults to None.
        overflow (Optional[OverflowMethod], optional): Overflow method. Defaults to "ignore".
        crop (Optional[bool], optional): Enable cropping of long lines. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        max_frames (int): Maximum number of frames to show in a traceback, 0 for no maximum. Defaults to 100.
    """
    from pip._vendor.rich import get_console

    console = console or get_console()
    assert console is not None

    def display_hook(value: Any) -> None:
        """Replacement sys.displayhook which prettifies objects with Rich."""
        if value is not None:
            assert console is not None
            builtins._ = None  # type: ignore[attr-defined]
            console.print(
                (
                    value
                    if _safe_isinstance(value, RichRenderable)
                    else Pretty(
                        value,
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                ),
                crop=crop,
            )
            builtins._ = value  # type: ignore[attr-defined]

    try:
        ip = get_ipython()  # type: ignore[name-defined]
    except NameError:
        sys.displayhook = display_hook
    else:
        from IPython.core.formatters import BaseFormatter

        class RichFormatter(BaseFormatter):  # type: ignore[misc]
            pprint: bool = True

            def __call__(self, value: Any) -> Any:
                if self.pprint:
                    return _ipy_display_hook(
                        value,
                        console=get_console(),
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                else:
                    return repr(value)

        # replace plain text formatter with rich formatter
        rich_formatter = RichFormatter()
        ip.display_formatter.formatters["text/plain"] = rich_formatter


class Pretty(JupyterMixin):
    """A rich renderable that pretty prints an object.

    Args:
        _object (Any): An object to pretty print.
        highlighter (HighlighterType, optional): Highlighter object to apply to result, or None for ReprHighlighter. Defaults to None.
        indent_size (int, optional): Number of spaces in indent. Defaults to 4.
        justify (JustifyMethod, optional): Justify method, or None for default. Defaults to None.
        overflow (OverflowMethod, optional): Overflow method, or None for default. Defaults to None.
        no_wrap (Optional[bool], optional): Disable word wrapping. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        margin (int, optional): Subtrace a margin from width to force containers to expand earlier. Defaults to 0.
        insert_line (bool, optional): Insert a new line if the output has multiple new lines. Defaults to False.
    """

    def __init__(
        self,
        _object: Any,
        highlighter: Optional["HighlighterType"] = None,
        *,
        indent_size: int = 4,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = False,
        indent_guides: bool = False,
        max_length: Optional[int] = None,
        max_string: Optional[int] = None,
        max_depth: Optional[int] = None,
        expand_all: bool = False,
        margin: int = 0,
        insert_line: bool = False,
    ) -> None:
        self._object = _object
        self.highlighter = highlighter or ReprHighlighter()
        self.indent_size = indent_size
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.indent_guides = indent_guides
        self.max_length = max_length
        self.max_string = max_string
        self.max_depth = max_depth
        self.expand_all = expand_all
        self.margin = margin
        self.insert_line = insert_line

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width - self.margin,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        pretty_text = Text.from_ansi(
            pretty_str,
            justify=self.justify or options.justify,
            overflow=self.overflow or options.overflow,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap),
            style="pretty",
        )
        pretty_text = (
            self.highlighter(pretty_text)
            if pretty_text
            else Text(
                f"{type(self._object)}.__repr__ returned empty string",
                style="dim italic",
            )
        )
        if self.indent_guides and not options.ascii_only:
            pretty_text = pretty_text.with_indent_guides(
                self.indent_size, style="repr.indent"
            )
        if self.insert_line and "\n" in pretty_text:
            yield ""
        yield pretty_text

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        text_width = (
            max(cell_len(line) for line in pretty_str.splitlines()) if pretty_str else 0
        )
        return Measurement(text_width, text_width)


def _get_braces_for_defaultdict(_object: DefaultDict[Any, Any]) -> Tuple[str, str, str]:
    return (
        f"defaultdict({_object.default_factory!r}, {{",
        "})",
        f"defaultdict({_object.default_factory!r}, {{}})",
    )


def _get_braces_for_deque(_object: Deque[Any]) -> Tuple[str, str, str]:
    if _object.maxlen is None:
        return ("deque([", "])", "deque()")
    return (
        "deque([",
        f"], maxlen={_object.maxlen})",
        f"deque(maxlen={_object.maxlen})",
    )


def _get_braces_for_array(_object: "array[Any]") -> Tuple[str, str, str]:
    return (f"array({_object.typecode!r}, [", "])", f"array({_object.typecode!r})")


_BRACES: Dict[type, Callable[[Any], Tuple[str, str, str]]] = {
    os._Environ: lambda _object: ("environ({", "})", "environ({})"),
    array: _get_braces_for_array,
    defaultdict: _get_braces_for_defaultdict,
    Counter: lambda _object: ("Counter({", "})", "Counter()"),
    deque: _get_braces_for_deque,
    dict: lambda _object: ("{", "}", "{}"),
    UserDict: lambda _object: ("{", "}", "{}"),
    frozenset: lambda _object: ("frozenset({", "})", "frozenset()"),
    list: lambda _object: ("[", "]", "[]"),
    UserList: lambda _object: ("[", "]", "[]"),
    set: lambda _object: ("{", "}", "set()"),
    tuple: lambda _object: ("(", ")", "()"),
    MappingProxyType: lambda _object: ("mappingproxy({", "})", "mappingproxy({})"),
}
_CONTAINERS = tuple(_BRACES.keys())
_MAPPING_CONTAINERS = (dict, os._Environ, MappingProxyType, UserDict)


def is_expandable(obj: Any) -> bool:
    """Check if an object may be expanded by pretty print."""
    return (
        _safe_isinstance(obj, _CONTAINERS)
        or (is_dataclass(obj))
        or (hasattr(obj, "__rich_repr__"))
        or _is_attr_object(obj)
    ) and not isclass(obj)


@dataclass
class Node:
    """A node in a repr tree. May be atomic or a container."""

    key_repr: str = ""
    value_repr: str = ""
    open_brace: str = ""
    close_brace: str = ""
    empty: str = ""
    last: bool = False
    is_tuple: bool = False
    is_namedtuple: bool = False
    children: Optional[List["Node"]] = None
    key_separator: str = ": "
    separator: str = ", "

    def iter_tokens(self) -> Iterable[str]:
        """Generate tokens for this node."""
        if self.key_repr:
            yield self.key_repr
            yield self.key_separator
        if self.value_repr:
            yield self.value_repr
        elif self.children is not None:
            if self.children:
                yield self.open_brace
                if self.is_tuple and not self.is_namedtuple and len(self.children) == 1:
                    yield from self.children[0].iter_tokens()
                    yield ","
                else:
                    for child in self.children:
                        yield from child.iter_tokens()
                        if not child.last:
                            yield self.separator
                yield self.close_brace
            else:
                yield self.empty

    def check_length(self, start_length: int, max_length: int) -> bool:
        """Check the length fits within a limit.

        Args:
            start_length (int): Starting length of the line (indent, prefix, suffix).
            max_length (int): Maximum length.

        Returns:
            bool: True if the node can be rendered within max length, otherwise False.
        """
        total_length = start_length
        for token in self.iter_tokens():
            total_length += cell_len(token)
            if total_length > max_length:
                return False
        return True

    def __str__(self) -> str:
        repr_text = "".join(self.iter_tokens())
        return repr_text

    def render(
        self, max_width: int = 80, indent_size: int = 4, expand_all: bool = False
    ) -> str:
        """Render the node to a pretty repr.

        Args:
            max_width (int, optional): Maximum width of the repr. Defaults to 80.
            indent_size (int, optional): Size of indents. Defaults to 4.
            expand_all (bool, optional): Expand all levels. Defaults to False.

        Returns:
            str: A repr string of the original object.
        """
        lines = [_Line(node=self, is_root=True)]
        line_no = 0
        while line_no < len(lines):
            line = lines[line_no]
            if line.expandable and not line.expanded:
                if expand_all or not line.check_length(max_width):
                    lines[line_no : line_no + 1] = line.expand(indent_size)
            line_no += 1

        repr_str = "\n".join(str(line) for line in lines)
        return repr_str


@dataclass
class _Line:
    """A line in repr output."""

    parent: Optional["_Line"] = None
    is_root: bool = False
    node: Optional[Node] = None
    text: str = ""
    suffix: str = ""
    whitespace: str = ""
    expanded: bool = False
    last: bool = False

    @property
    def expandable(self) -> bool:
        """Check if the line may be expanded."""
        return bool(self.node is not None and self.node.children)

    def check_length(self, max_length: int) -> bool:
        """Check this line fits within a given number of cells."""
        start_length = (
            len(self.whitespace) + cell_len(self.text) + cell_len(self.suffix)
        )
        assert self.node is not None
        return self.node.check_length(start_length, max_length)

    def expand(self, indent_size: int) -> Iterable["_Line"]:
        """Expand this line by adding children on their own line."""
        node = self.node
        assert node is not None
        whitespace = self.whitespace
        assert node.children
        if node.key_repr:
            new_line = yield _Line(
                text=f"{node.key_repr}{node.key_separator}{node.open_brace}",
                whitespace=whitespace,
            )
        else:
            new_line = yield _Line(text=node.open_brace, whitespace=whitespace)
        child_whitespace = self.whitespace + " " * indent_size
        tuple_of_one = node.is_tuple and len(node.children) == 1
        for last, child in loop_last(node.children):
            separator = "," if tuple_of_one else node.separator
            line = _Line(
                parent=new_line,
                node=child,
                whitespace=child_whitespace,
                suffix=separator,
                last=last and not tuple_of_one,
            )
            yield line

        yield _Line(
            text=node.close_brace,
            whitespace=whitespace,
            suffix=self.suffix,
            last=self.last,
        )

    def __str__(self) -> str:
        if self.last:
            return f"{self.whitespace}{self.text}{self.node or ''}"
        else:
            return (
                f"{self.whitespace}{self.text}{self.node or ''}{self.suffix.rstrip()}"
            )


def _is_namedtuple(obj: Any) -> bool:
    """Checks if an object is most likely a namedtuple. It is possible
    to craft an object that passes this check and isn't a namedtuple, but
    there is only a minuscule chance of this happening unintentionally.

    Args:
        obj (Any): The object to test

    Returns:
        bool: True if the object is a namedtuple. False otherwise.
    """
    try:
        fields = getattr(obj, "_fields", None)
    except Exception:
        # Being very defensive - if we cannot get the attr then its not a namedtuple
        return False
    return isinstance(obj, tuple) and isinstance(fields, tuple)


def traverse(
    _object: Any,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> Node:
    """Traverse object and generate a tree.

    Args:
        _object (Any): Object to be traversed.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of data structures, or None for no maximum.
            Defaults to None.

    Returns:
        Node: The root of a tree structure which can be used to render a pretty repr.
    """

    def to_repr(obj: Any) -> str:
        """Get repr string for an object, but catch errors."""
        if (
            max_string is not None
            and _safe_isinstance(obj, (bytes, str))
            and len(obj) > max_string
        ):
            truncated = len(obj) - max_string
            obj_repr = f"{obj[:max_string]!r}+{truncated}"
        else:
            try:
                obj_repr = repr(obj)
            except Exception as error:
                obj_repr = f"<repr-error {str(error)!r}>"
        return obj_repr

    visited_ids: Set[int] = set()
    push_visited = visited_ids.add
    pop_visited = visited_ids.remove

    def _traverse(obj: Any, root: bool = False, depth: int = 0) -> Node:
        """Walk the object depth first."""

        obj_id = id(obj)
        if obj_id in visited_ids:
            # Recursion detected
            return Node(value_repr="...")

        obj_type = type(obj)
        children: List[Node]
        reached_max_depth = max_depth is not None and depth >= max_depth

        def iter_rich_args(rich_args: Any) -> Iterable[Union[Any, Tuple[str, Any]]]:
            for arg in rich_args:
                if _safe_isinstance(arg, tuple):
                    if len(arg) == 3:
                        key, child, default = arg
                        if default == child:
                            continue
                        yield key, child
                    elif len(arg) == 2:
                        key, child = arg
                        yield key, child
                    elif len(arg) == 1:
                        yield arg[0]
                else:
                    yield arg

        try:
            fake_attributes = hasattr(
                obj, "awehoi234_wdfjwljet234_234wdfoijsdfmmnxpi492"
            )
        except Exception:
            fake_attributes = False

        rich_repr_result: Optional[RichReprResult] = None
        if not fake_attributes:
            try:
                if hasattr(obj, "__rich_repr__") and not isclass(obj):
                    rich_repr_result = obj.__rich_repr__()
            except Exception:
                pass

        if rich_repr_result is not None:
            push_visited(obj_id)
            angular = getattr(obj.__rich_repr__, "angular", False)
            args = list(iter_rich_args(rich_repr_result))
            class_name = obj.__class__.__name__

            if args:
                children = []
                append = children.append

                if reached_max_depth:
                    if angular:
                        node = Node(value_repr=f"<{class_name}...>")
                    else:
                        node = Node(value_repr=f"{class_name}(...)")
                else:
                    if angular:
                        node = Node(
                            open_brace=f"<{class_name} ",
                            close_brace=">",
                            children=children,
                            last=root,
                            separator=" ",
                        )
                    else:
                        node = Node(
                            open_brace=f"{class_name}(",
                            close_brace=")",
                            children=children,
                            last=root,
                        )
                    for last, arg in loop_last(args):
                        if _safe_isinstance(arg, tuple):
                            key, child = arg
                            child_node = _traverse(child, depth=depth + 1)
                            child_node.last = last
                            child_node.key_repr = key
                            child_node.key_separator = "="
                            append(child_node)
                        else:
                            child_node = _traverse(arg, depth=depth + 1)
                            child_node.last = last
                            append(child_node)
            else:
                node = Node(
                    value_repr=f"<{class_name}>" if angular else f"{class_name}()",
                    children=[],
                    last=root,
                )
            pop_visited(obj_id)
        elif _is_attr_object(obj) and not fake_attributes:
            push_visited(obj_id)
            children = []
            append = children.append

            attr_fields = _get_attr_fields(obj)
            if attr_fields:
                if reached_max_depth:
                    node = Node(value_repr=f"{obj.__class__.__name__}(...)")
                else:
                    node = Node(
                        open_brace=f"{obj.__class__.__name__}(",
                        close_brace=")",
                        children=children,
                        last=root,
                    )

                    def iter_attrs() -> (
                        Iterable[Tuple[str, Any, Optional[Callable[[Any], str]]]]
                    ):
                        """Iterate over attr fields and values."""
                        for attr in attr_fields:
                            if attr.repr:
                                try:
                                    value = getattr(obj, attr.name)
                                except Exception as error:
                                    # Can happen, albeit rarely
                                    yield (attr.name, error, None)
                                else:
                                    yield (
                                        attr.name,
                                        value,
                                        attr.repr if callable(attr.repr) else None,
                                    )

                    for last, (name, value, repr_callable) in loop_last(iter_attrs()):
                        if repr_callable:
                            child_node = Node(value_repr=str(repr_callable(value)))
                        else:
                            child_node = _traverse(value, depth=depth + 1)
                        child_node.last = last
                        child_node.key_repr = name
                        child_node.key_separator = "="
                        append(child_node)
            else:
                node = Node(
                    value_repr=f"{obj.__class__.__name__}()", children=[], last=root
                )
            pop_visited(obj_id)
        elif (
            is_dataclass(obj)
            and not _safe_isinstance(obj, type)
            and not fake_attributes
            and _is_dataclass_repr(obj)
        ):
            push_visited(obj_id)
            children = []
            append = children.append
            if reached_max_depth:
                node = Node(value_repr=f"{obj.__class__.__name__}(...)")
            else:
                node = Node(
                    open_brace=f"{obj.__class__.__name__}(",
                    close_brace=")",
                    children=children,
                    last=root,
                    empty=f"{obj.__class__.__name__}()",
                )

                for last, field in loop_last(
                    field
                    for field in fields(obj)
                    if field.repr and hasattr(obj, field.name)
                ):
                    child_node = _traverse(getattr(obj, field.name), depth=depth + 1)
                    child_node.key_repr = field.name
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)

            pop_visited(obj_id)
        elif _is_namedtuple(obj) and _has_default_namedtuple_repr(obj):
            push_visited(obj_id)
            class_name = obj.__class__.__name__
            if reached_max_depth:
                # If we've reached the max depth, we still show the class name, but not its contents
                node = Node(
                    value_repr=f"{class_name}(...)",
                )
            else:
                children = []
                append = children.append
                node = Node(
                    open_brace=f"{class_name}(",
                    close_brace=")",
                    children=children,
                    empty=f"{class_name}()",
                )
                for last, (key, value) in loop_last(obj._asdict().items()):
                    child_node = _traverse(value, depth=depth + 1)
                    child_node.key_repr = key
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)
            pop_visited(obj_id)
        elif _safe_isinstance(obj, _CONTAINERS):
            for container_type in _CONTAINERS:
                if _safe_isinstance(obj, container_type):
                    obj_type = container_type
                    break

            push_visited(obj_id)

            open_brace, close_brace, empty = _BRACES[obj_type](obj)

            if reached_max_depth:
                node = Node(value_repr=f"{open_brace}...{close_brace}")
            elif obj_type.__repr__ != type(obj).__repr__:
                node = Node(value_repr=to_repr(obj), last=root)
            elif obj:
                children = []
                node = Node(
                    open_brace=open_brace,
                    close_brace=close_brace,
                    children=children,
                    last=root,
                )
                append = children.append
                num_items = len(obj)
                last_item_index = num_items - 1

                if _safe_isinstance(obj, _MAPPING_CONTAINERS):
                    iter_items = iter(obj.items())
                    if max_length is not None:
                        iter_items = islice(iter_items, max_length)
                    for index, (key, child) in enumerate(iter_items):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.key_repr = to_repr(key)
                        child_node.last = index == last_item_index
                        append(child_node)
                else:
                    iter_values = iter(obj)
                    if max_length is not None:
                        iter_values = islice(iter_values, max_length)
                    for index, child in enumerate(iter_values):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.last = index == last_item_index
                        append(child_node)
                if max_length is not None and num_items > max_length:
                    append(Node(value_repr=f"... +{num_items - max_length}", last=True))
            else:
                node = Node(empty=empty, children=[], last=root)

            pop_visited(obj_id)
        else:
            node = Node(value_repr=to_repr(obj), last=root)
        node.is_tuple = type(obj) == tuple
        node.is_namedtuple = _is_namedtuple(obj)
        return node

    node = _traverse(_object, root=True)
    return node


def pretty_repr(
    _object: Any,
    *,
    max_width: int = 80,
    indent_size: int = 4,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> str:
    """Prettify repr string by expanding on to new lines to fit within a given width.

    Args:
        _object (Any): Object to repr.
        max_width (int, optional): Desired maximum width of repr string. Defaults to 80.
        indent_size (int, optional): Number of spaces to indent. Defaults to 4.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structure, or None for no depth.
            Defaults to None.
        expand_all (bool, optional): Expand all containers regardless of available width. Defaults to False.

    Returns:
        str: A possibly multi-line representation of the object.
    """

    if _safe_isinstance(_object, Node):
        node = _object
    else:
        node = traverse(
            _object, max_length=max_length, max_string=max_string, max_depth=max_depth
        )
    repr_str: str = node.render(
        max_width=max_width, indent_size=indent_size, expand_all=expand_all
    )
    return repr_str


def pprint(
    _object: Any,
    *,
    console: Optional["Console"] = None,
    indent_guides: bool = True,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """A convenience function for pretty printing.

    Args:
        _object (Any): Object to pretty print.
        console (Console, optional): Console instance, or None to use default. Defaults to None.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of strings before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth for nested data structures, or None for unlimited depth. Defaults to None.
        indent_guides (bool, optional): Enable indentation guides. Defaults to True.
        expand_all (bool, optional): Expand all containers. Defaults to False.
    """
    _console = get_console() if console is None else console
    _console.print(
        Pretty(
            _object,
            max_length=max_length,
            max_string=max_string,
            max_depth=max_depth,
            indent_guides=indent_guides,
            expand_all=expand_all,
            overflow="ignore",
        ),
        soft_wrap=True,
    )


if __name__ == "__main__":  # pragma: no cover

    class BrokenRepr:
        def __repr__(self) -> str:
            1 / 0
            return "this will fail"

    from typing import NamedTuple

    class StockKeepingUnit(NamedTuple):
        name: str
        description: str
        price: float
        category: str
        reviews: List[str]

    d = defaultdict(int)
    d["foo"] = 5
    data = {
        "foo": [
            1,
            "Hello World!",
            100.123,
            323.232,
            432324.0,
            {5, 6, 7, (1, 2, 3, 4), 8},
        ],
        "bar": frozenset({1, 2, 3}),
        "defaultdict": defaultdict(
            list, {"crumble": ["apple", "rhubarb", "butter", "sugar", "flour"]}
        ),
        "counter": Counter(
            [
                "apple",
                "orange",
                "pear",
                "kumquat",
                "kumquat",
                "durian" * 100,
            ]
        ),
        "atomic": (False, True, None),
        "namedtuple": StockKeepingUnit(
            "Sparkling British Spring Water",
            "Carbonated spring water",
            0.9,
            "water",
            ["its amazing!", "its terrible!"],
        ),
        "Broken": BrokenRepr(),
    }
    data["foo"].append(data)  # type: ignore[attr-defined]

    from pip._vendor.rich import print

    print(Pretty(data, indent_guides=True, max_string=20))

    class Thing:
        def __repr__(self) -> str:
            return "Hello\x1b[38;5;239m World!"

    print(Pretty(Thing()))

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\processors.py ===
"""
Processors are little transformation blocks that transform the fragments list
from a buffer before the BufferControl will render it to the screen.

They can insert fragments before or after, or highlight fragments by replacing the
fragment types.
"""

from __future__ import annotations

import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, Hashable, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.document import Document
from prompt_toolkit.filters import FilterOrBool, to_filter, vi_insert_multiple_mode
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import fragment_list_len, fragment_list_to_text
from prompt_toolkit.search import SearchDirection
from prompt_toolkit.utils import to_int, to_str

from .utils import explode_text_fragments

if TYPE_CHECKING:
    from .controls import BufferControl, UIContent

__all__ = [
    "Processor",
    "TransformationInput",
    "Transformation",
    "DummyProcessor",
    "HighlightSearchProcessor",
    "HighlightIncrementalSearchProcessor",
    "HighlightSelectionProcessor",
    "PasswordProcessor",
    "HighlightMatchingBracketProcessor",
    "DisplayMultipleCursors",
    "BeforeInput",
    "ShowArg",
    "AfterInput",
    "AppendAutoSuggestion",
    "ConditionalProcessor",
    "ShowLeadingWhiteSpaceProcessor",
    "ShowTrailingWhiteSpaceProcessor",
    "TabsProcessor",
    "ReverseSearchProcessor",
    "DynamicProcessor",
    "merge_processors",
]


class Processor(metaclass=ABCMeta):
    """
    Manipulate the fragments for a given line in a
    :class:`~prompt_toolkit.layout.controls.BufferControl`.
    """

    @abstractmethod
    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        """
        Apply transformation. Returns a :class:`.Transformation` instance.

        :param transformation_input: :class:`.TransformationInput` object.
        """
        return Transformation(transformation_input.fragments)


SourceToDisplay = Callable[[int], int]
DisplayToSource = Callable[[int], int]


class TransformationInput:
    """
    :param buffer_control: :class:`.BufferControl` instance.
    :param lineno: The number of the line to which we apply the processor.
    :param source_to_display: A function that returns the position in the
        `fragments` for any position in the source string. (This takes
        previous processors into account.)
    :param fragments: List of fragments that we can transform. (Received from the
        previous processor.)
    :param get_line: Optional ; a callable that returns the fragments of another
        line in the  current buffer; This can be used to create processors capable
        of affecting transforms across multiple lines.
    """

    def __init__(
        self,
        buffer_control: BufferControl,
        document: Document,
        lineno: int,
        source_to_display: SourceToDisplay,
        fragments: StyleAndTextTuples,
        width: int,
        height: int,
        get_line: Callable[[int], StyleAndTextTuples] | None = None,
    ) -> None:
        self.buffer_control = buffer_control
        self.document = document
        self.lineno = lineno
        self.source_to_display = source_to_display
        self.fragments = fragments
        self.width = width
        self.height = height
        self.get_line = get_line

    def unpack(
        self,
    ) -> tuple[
        BufferControl, Document, int, SourceToDisplay, StyleAndTextTuples, int, int
    ]:
        return (
            self.buffer_control,
            self.document,
            self.lineno,
            self.source_to_display,
            self.fragments,
            self.width,
            self.height,
        )


class Transformation:
    """
    Transformation result, as returned by :meth:`.Processor.apply_transformation`.

    Important: Always make sure that the length of `document.text` is equal to
               the length of all the text in `fragments`!

    :param fragments: The transformed fragments. To be displayed, or to pass to
        the next processor.
    :param source_to_display: Cursor position transformation from original
        string to transformed string.
    :param display_to_source: Cursor position transformed from source string to
        original string.
    """

    def __init__(
        self,
        fragments: StyleAndTextTuples,
        source_to_display: SourceToDisplay | None = None,
        display_to_source: DisplayToSource | None = None,
    ) -> None:
        self.fragments = fragments
        self.source_to_display = source_to_display or (lambda i: i)
        self.display_to_source = display_to_source or (lambda i: i)


class DummyProcessor(Processor):
    """
    A `Processor` that doesn't do anything.
    """

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        return Transformation(transformation_input.fragments)


class HighlightSearchProcessor(Processor):
    """
    Processor that highlights search matches in the document.
    Note that this doesn't support multiline search matches yet.

    The style classes 'search' and 'search.current' will be applied to the
    content.
    """

    _classname = "search"
    _classname_current = "search.current"

    def _get_search_text(self, buffer_control: BufferControl) -> str:
        """
        The text we are searching for.
        """
        return buffer_control.search_state.text

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        (
            buffer_control,
            document,
            lineno,
            source_to_display,
            fragments,
            _,
            _,
        ) = transformation_input.unpack()

        search_text = self._get_search_text(buffer_control)
        searchmatch_fragment = f" class:{self._classname} "
        searchmatch_current_fragment = f" class:{self._classname_current} "

        if search_text and not get_app().is_done:
            # For each search match, replace the style string.
            line_text = fragment_list_to_text(fragments)
            fragments = explode_text_fragments(fragments)

            if buffer_control.search_state.ignore_case():
                flags = re.IGNORECASE
            else:
                flags = re.RegexFlag(0)

            # Get cursor column.
            cursor_column: int | None
            if document.cursor_position_row == lineno:
                cursor_column = source_to_display(document.cursor_position_col)
            else:
                cursor_column = None

            for match in re.finditer(re.escape(search_text), line_text, flags=flags):
                if cursor_column is not None:
                    on_cursor = match.start() <= cursor_column < match.end()
                else:
                    on_cursor = False

                for i in range(match.start(), match.end()):
                    old_fragment, text, *_ = fragments[i]
                    if on_cursor:
                        fragments[i] = (
                            old_fragment + searchmatch_current_fragment,
                            fragments[i][1],
                        )
                    else:
                        fragments[i] = (
                            old_fragment + searchmatch_fragment,
                            fragments[i][1],
                        )

        return Transformation(fragments)


class HighlightIncrementalSearchProcessor(HighlightSearchProcessor):
    """
    Highlight the search terms that are used for highlighting the incremental
    search. The style class 'incsearch' will be applied to the content.

    Important: this requires the `preview_search=True` flag to be set for the
    `BufferControl`. Otherwise, the cursor position won't be set to the search
    match while searching, and nothing happens.
    """

    _classname = "incsearch"
    _classname_current = "incsearch.current"

    def _get_search_text(self, buffer_control: BufferControl) -> str:
        """
        The text we are searching for.
        """
        # When the search buffer has focus, take that text.
        search_buffer = buffer_control.search_buffer
        if search_buffer is not None and search_buffer.text:
            return search_buffer.text
        return ""


class HighlightSelectionProcessor(Processor):
    """
    Processor that highlights the selection in the document.
    """

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        (
            buffer_control,
            document,
            lineno,
            source_to_display,
            fragments,
            _,
            _,
        ) = transformation_input.unpack()

        selected_fragment = " class:selected "

        # In case of selection, highlight all matches.
        selection_at_line = document.selection_range_at_line(lineno)

        if selection_at_line:
            from_, to = selection_at_line
            from_ = source_to_display(from_)
            to = source_to_display(to)

            fragments = explode_text_fragments(fragments)

            if from_ == 0 and to == 0 and len(fragments) == 0:
                # When this is an empty line, insert a space in order to
                # visualize the selection.
                return Transformation([(selected_fragment, " ")])
            else:
                for i in range(from_, to):
                    if i < len(fragments):
                        old_fragment, old_text, *_ = fragments[i]
                        fragments[i] = (old_fragment + selected_fragment, old_text)
                    elif i == len(fragments):
                        fragments.append((selected_fragment, " "))

        return Transformation(fragments)


class PasswordProcessor(Processor):
    """
    Processor that masks the input. (For passwords.)

    :param char: (string) Character to be used. "*" by default.
    """

    def __init__(self, char: str = "*") -> None:
        self.char = char

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        fragments: StyleAndTextTuples = cast(
            StyleAndTextTuples,
            [
                (style, self.char * len(text), *handler)
                for style, text, *handler in ti.fragments
            ],
        )

        return Transformation(fragments)


class HighlightMatchingBracketProcessor(Processor):
    """
    When the cursor is on or right after a bracket, it highlights the matching
    bracket.

    :param max_cursor_distance: Only highlight matching brackets when the
        cursor is within this distance. (From inside a `Processor`, we can't
        know which lines will be visible on the screen. But we also don't want
        to scan the whole document for matching brackets on each key press, so
        we limit to this value.)
    """

    _closing_braces = "])}>"

    def __init__(
        self, chars: str = "[](){}<>", max_cursor_distance: int = 1000
    ) -> None:
        self.chars = chars
        self.max_cursor_distance = max_cursor_distance

        self._positions_cache: SimpleCache[Hashable, list[tuple[int, int]]] = (
            SimpleCache(maxsize=8)
        )

    def _get_positions_to_highlight(self, document: Document) -> list[tuple[int, int]]:
        """
        Return a list of (row, col) tuples that need to be highlighted.
        """
        pos: int | None

        # Try for the character under the cursor.
        if document.current_char and document.current_char in self.chars:
            pos = document.find_matching_bracket_position(
                start_pos=document.cursor_position - self.max_cursor_distance,
                end_pos=document.cursor_position + self.max_cursor_distance,
            )

        # Try for the character before the cursor.
        elif (
            document.char_before_cursor
            and document.char_before_cursor in self._closing_braces
            and document.char_before_cursor in self.chars
        ):
            document = Document(document.text, document.cursor_position - 1)

            pos = document.find_matching_bracket_position(
                start_pos=document.cursor_position - self.max_cursor_distance,
                end_pos=document.cursor_position + self.max_cursor_distance,
            )
        else:
            pos = None

        # Return a list of (row, col) tuples that need to be highlighted.
        if pos:
            pos += document.cursor_position  # pos is relative.
            row, col = document.translate_index_to_position(pos)
            return [
                (row, col),
                (document.cursor_position_row, document.cursor_position_col),
            ]
        else:
            return []

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        (
            buffer_control,
            document,
            lineno,
            source_to_display,
            fragments,
            _,
            _,
        ) = transformation_input.unpack()

        # When the application is in the 'done' state, don't highlight.
        if get_app().is_done:
            return Transformation(fragments)

        # Get the highlight positions.
        key = (get_app().render_counter, document.text, document.cursor_position)
        positions = self._positions_cache.get(
            key, lambda: self._get_positions_to_highlight(document)
        )

        # Apply if positions were found at this line.
        if positions:
            for row, col in positions:
                if row == lineno:
                    col = source_to_display(col)
                    fragments = explode_text_fragments(fragments)
                    style, text, *_ = fragments[col]

                    if col == document.cursor_position_col:
                        style += " class:matching-bracket.cursor "
                    else:
                        style += " class:matching-bracket.other "

                    fragments[col] = (style, text)

        return Transformation(fragments)


class DisplayMultipleCursors(Processor):
    """
    When we're in Vi block insert mode, display all the cursors.
    """

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        (
            buffer_control,
            document,
            lineno,
            source_to_display,
            fragments,
            _,
            _,
        ) = transformation_input.unpack()

        buff = buffer_control.buffer

        if vi_insert_multiple_mode():
            cursor_positions = buff.multiple_cursor_positions
            fragments = explode_text_fragments(fragments)

            # If any cursor appears on the current line, highlight that.
            start_pos = document.translate_row_col_to_index(lineno, 0)
            end_pos = start_pos + len(document.lines[lineno])

            fragment_suffix = " class:multiple-cursors"

            for p in cursor_positions:
                if start_pos <= p <= end_pos:
                    column = source_to_display(p - start_pos)

                    # Replace fragment.
                    try:
                        style, text, *_ = fragments[column]
                    except IndexError:
                        # Cursor needs to be displayed after the current text.
                        fragments.append((fragment_suffix, " "))
                    else:
                        style += fragment_suffix
                        fragments[column] = (style, text)

            return Transformation(fragments)
        else:
            return Transformation(fragments)


class BeforeInput(Processor):
    """
    Insert text before the input.

    :param text: This can be either plain text or formatted text
        (or a callable that returns any of those).
    :param style: style to be applied to this prompt/prefix.
    """

    def __init__(self, text: AnyFormattedText, style: str = "") -> None:
        self.text = text
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        source_to_display: SourceToDisplay | None
        display_to_source: DisplayToSource | None

        if ti.lineno == 0:
            # Get fragments.
            fragments_before = to_formatted_text(self.text, self.style)
            fragments = fragments_before + ti.fragments

            shift_position = fragment_list_len(fragments_before)
            source_to_display = lambda i: i + shift_position
            display_to_source = lambda i: i - shift_position
        else:
            fragments = ti.fragments
            source_to_display = None
            display_to_source = None

        return Transformation(
            fragments,
            source_to_display=source_to_display,
            display_to_source=display_to_source,
        )

    def __repr__(self) -> str:
        return f"BeforeInput({self.text!r}, {self.style!r})"


class ShowArg(BeforeInput):
    """
    Display the 'arg' in front of the input.

    This was used by the `PromptSession`, but now it uses the
    `Window.get_line_prefix` function instead.
    """

    def __init__(self) -> None:
        super().__init__(self._get_text_fragments)

    def _get_text_fragments(self) -> StyleAndTextTuples:
        app = get_app()
        if app.key_processor.arg is None:
            return []
        else:
            arg = app.key_processor.arg

            return [
                ("class:prompt.arg", "(arg: "),
                ("class:prompt.arg.text", str(arg)),
                ("class:prompt.arg", ") "),
            ]

    def __repr__(self) -> str:
        return "ShowArg()"


class AfterInput(Processor):
    """
    Insert text after the input.

    :param text: This can be either plain text or formatted text
        (or a callable that returns any of those).
    :param style: style to be applied to this prompt/prefix.
    """

    def __init__(self, text: AnyFormattedText, style: str = "") -> None:
        self.text = text
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        # Insert fragments after the last line.
        if ti.lineno == ti.document.line_count - 1:
            # Get fragments.
            fragments_after = to_formatted_text(self.text, self.style)
            return Transformation(fragments=ti.fragments + fragments_after)
        else:
            return Transformation(fragments=ti.fragments)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.text!r}, style={self.style!r})"


class AppendAutoSuggestion(Processor):
    """
    Append the auto suggestion to the input.
    (The user can then press the right arrow the insert the suggestion.)
    """

    def __init__(self, style: str = "class:auto-suggestion") -> None:
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        # Insert fragments after the last line.
        if ti.lineno == ti.document.line_count - 1:
            buffer = ti.buffer_control.buffer

            if buffer.suggestion and ti.document.is_cursor_at_the_end:
                suggestion = buffer.suggestion.text
            else:
                suggestion = ""

            return Transformation(fragments=ti.fragments + [(self.style, suggestion)])
        else:
            return Transformation(fragments=ti.fragments)


class ShowLeadingWhiteSpaceProcessor(Processor):
    """
    Make leading whitespace visible.

    :param get_char: Callable that returns one character.
    """

    def __init__(
        self,
        get_char: Callable[[], str] | None = None,
        style: str = "class:leading-whitespace",
    ) -> None:
        def default_get_char() -> str:
            if "\xb7".encode(get_app().output.encoding(), "replace") == b"?":
                return "."
            else:
                return "\xb7"

        self.style = style
        self.get_char = get_char or default_get_char

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        fragments = ti.fragments

        # Walk through all te fragments.
        if fragments and fragment_list_to_text(fragments).startswith(" "):
            t = (self.style, self.get_char())
            fragments = explode_text_fragments(fragments)

            for i in range(len(fragments)):
                if fragments[i][1] == " ":
                    fragments[i] = t
                else:
                    break

        return Transformation(fragments)


class ShowTrailingWhiteSpaceProcessor(Processor):
    """
    Make trailing whitespace visible.

    :param get_char: Callable that returns one character.
    """

    def __init__(
        self,
        get_char: Callable[[], str] | None = None,
        style: str = "class:training-whitespace",
    ) -> None:
        def default_get_char() -> str:
            if "\xb7".encode(get_app().output.encoding(), "replace") == b"?":
                return "."
            else:
                return "\xb7"

        self.style = style
        self.get_char = get_char or default_get_char

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        fragments = ti.fragments

        if fragments and fragments[-1][1].endswith(" "):
            t = (self.style, self.get_char())
            fragments = explode_text_fragments(fragments)

            # Walk backwards through all te fragments and replace whitespace.
            for i in range(len(fragments) - 1, -1, -1):
                char = fragments[i][1]
                if char == " ":
                    fragments[i] = t
                else:
                    break

        return Transformation(fragments)


class TabsProcessor(Processor):
    """
    Render tabs as spaces (instead of ^I) or make them visible (for instance,
    by replacing them with dots.)

    :param tabstop: Horizontal space taken by a tab. (`int` or callable that
        returns an `int`).
    :param char1: Character or callable that returns a character (text of
        length one). This one is used for the first space taken by the tab.
    :param char2: Like `char1`, but for the rest of the space.
    """

    def __init__(
        self,
        tabstop: int | Callable[[], int] = 4,
        char1: str | Callable[[], str] = "|",
        char2: str | Callable[[], str] = "\u2508",
        style: str = "class:tab",
    ) -> None:
        self.char1 = char1
        self.char2 = char2
        self.tabstop = tabstop
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        tabstop = to_int(self.tabstop)
        style = self.style

        # Create separator for tabs.
        separator1 = to_str(self.char1)
        separator2 = to_str(self.char2)

        # Transform fragments.
        fragments = explode_text_fragments(ti.fragments)

        position_mappings = {}
        result_fragments: StyleAndTextTuples = []
        pos = 0

        for i, fragment_and_text in enumerate(fragments):
            position_mappings[i] = pos

            if fragment_and_text[1] == "\t":
                # Calculate how many characters we have to insert.
                count = tabstop - (pos % tabstop)
                if count == 0:
                    count = tabstop

                # Insert tab.
                result_fragments.append((style, separator1))
                result_fragments.append((style, separator2 * (count - 1)))
                pos += count
            else:
                result_fragments.append(fragment_and_text)
                pos += 1

        position_mappings[len(fragments)] = pos
        # Add `pos+1` to mapping, because the cursor can be right after the
        # line as well.
        position_mappings[len(fragments) + 1] = pos + 1

        def source_to_display(from_position: int) -> int:
            "Maps original cursor position to the new one."
            return position_mappings[from_position]

        def display_to_source(display_pos: int) -> int:
            "Maps display cursor position to the original one."
            position_mappings_reversed = {v: k for k, v in position_mappings.items()}

            while display_pos >= 0:
                try:
                    return position_mappings_reversed[display_pos]
                except KeyError:
                    display_pos -= 1
            return 0

        return Transformation(
            result_fragments,
            source_to_display=source_to_display,
            display_to_source=display_to_source,
        )


class ReverseSearchProcessor(Processor):
    """
    Process to display the "(reverse-i-search)`...`:..." stuff around
    the search buffer.

    Note: This processor is meant to be applied to the BufferControl that
    contains the search buffer, it's not meant for the original input.
    """

    _excluded_input_processors: list[type[Processor]] = [
        HighlightSearchProcessor,
        HighlightSelectionProcessor,
        BeforeInput,
        AfterInput,
    ]

    def _get_main_buffer(self, buffer_control: BufferControl) -> BufferControl | None:
        from prompt_toolkit.layout.controls import BufferControl

        prev_control = get_app().layout.search_target_buffer_control
        if (
            isinstance(prev_control, BufferControl)
            and prev_control.search_buffer_control == buffer_control
        ):
            return prev_control
        return None

    def _content(
        self, main_control: BufferControl, ti: TransformationInput
    ) -> UIContent:
        from prompt_toolkit.layout.controls import BufferControl

        # Emulate the BufferControl through which we are searching.
        # For this we filter out some of the input processors.
        excluded_processors = tuple(self._excluded_input_processors)

        def filter_processor(item: Processor) -> Processor | None:
            """Filter processors from the main control that we want to disable
            here. This returns either an accepted processor or None."""
            # For a `_MergedProcessor`, check each individual processor, recursively.
            if isinstance(item, _MergedProcessor):
                accepted_processors = [filter_processor(p) for p in item.processors]
                return merge_processors(
                    [p for p in accepted_processors if p is not None]
                )

            # For a `ConditionalProcessor`, check the body.
            elif isinstance(item, ConditionalProcessor):
                p = filter_processor(item.processor)
                if p:
                    return ConditionalProcessor(p, item.filter)

            # Otherwise, check the processor itself.
            else:
                if not isinstance(item, excluded_processors):
                    return item

            return None

        filtered_processor = filter_processor(
            merge_processors(main_control.input_processors or [])
        )
        highlight_processor = HighlightIncrementalSearchProcessor()

        if filtered_processor:
            new_processors = [filtered_processor, highlight_processor]
        else:
            new_processors = [highlight_processor]

        from .controls import SearchBufferControl

        assert isinstance(ti.buffer_control, SearchBufferControl)

        buffer_control = BufferControl(
            buffer=main_control.buffer,
            input_processors=new_processors,
            include_default_input_processors=False,
            lexer=main_control.lexer,
            preview_search=True,
            search_buffer_control=ti.buffer_control,
        )

        return buffer_control.create_content(ti.width, ti.height, preview_search=True)

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        from .controls import SearchBufferControl

        assert isinstance(ti.buffer_control, SearchBufferControl), (
            "`ReverseSearchProcessor` should be applied to a `SearchBufferControl` only."
        )

        source_to_display: SourceToDisplay | None
        display_to_source: DisplayToSource | None

        main_control = self._get_main_buffer(ti.buffer_control)

        if ti.lineno == 0 and main_control:
            content = self._content(main_control, ti)

            # Get the line from the original document for this search.
            line_fragments = content.get_line(content.cursor_position.y)

            if main_control.search_state.direction == SearchDirection.FORWARD:
                direction_text = "i-search"
            else:
                direction_text = "reverse-i-search"

            fragments_before: StyleAndTextTuples = [
                ("class:prompt.search", "("),
                ("class:prompt.search", direction_text),
                ("class:prompt.search", ")`"),
            ]

            fragments = (
                fragments_before
                + [
                    ("class:prompt.search.text", fragment_list_to_text(ti.fragments)),
                    ("", "': "),
                ]
                + line_fragments
            )

            shift_position = fragment_list_len(fragments_before)
            source_to_display = lambda i: i + shift_position
            display_to_source = lambda i: i - shift_position
        else:
            source_to_display = None
            display_to_source = None
            fragments = ti.fragments

        return Transformation(
            fragments,
            source_to_display=source_to_display,
            display_to_source=display_to_source,
        )


class ConditionalProcessor(Processor):
    """
    Processor that applies another processor, according to a certain condition.
    Example::

        # Create a function that returns whether or not the processor should
        # currently be applied.
        def highlight_enabled():
            return true_or_false

        # Wrapped it in a `ConditionalProcessor` for usage in a `BufferControl`.
        BufferControl(input_processors=[
            ConditionalProcessor(HighlightSearchProcessor(),
                                 Condition(highlight_enabled))])

    :param processor: :class:`.Processor` instance.
    :param filter: :class:`~prompt_toolkit.filters.Filter` instance.
    """

    def __init__(self, processor: Processor, filter: FilterOrBool) -> None:
        self.processor = processor
        self.filter = to_filter(filter)

    def apply_transformation(
        self, transformation_input: TransformationInput
    ) -> Transformation:
        # Run processor when enabled.
        if self.filter():
            return self.processor.apply_transformation(transformation_input)
        else:
            return Transformation(transformation_input.fragments)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(processor={self.processor!r}, filter={self.filter!r})"


class DynamicProcessor(Processor):
    """
    Processor class that dynamically returns any Processor.

    :param get_processor: Callable that returns a :class:`.Processor` instance.
    """

    def __init__(self, get_processor: Callable[[], Processor | None]) -> None:
        self.get_processor = get_processor

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        processor = self.get_processor() or DummyProcessor()
        return processor.apply_transformation(ti)


def merge_processors(processors: list[Processor]) -> Processor:
    """
    Merge multiple `Processor` objects into one.
    """
    if len(processors) == 0:
        return DummyProcessor()

    if len(processors) == 1:
        return processors[0]  # Nothing to merge.

    return _MergedProcessor(processors)


class _MergedProcessor(Processor):
    """
    Processor that groups multiple other `Processor` objects, but exposes an
    API as if it is one `Processor`.
    """

    def __init__(self, processors: list[Processor]):
        self.processors = processors

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        source_to_display_functions = [ti.source_to_display]
        display_to_source_functions = []
        fragments = ti.fragments

        def source_to_display(i: int) -> int:
            """Translate x position from the buffer to the x position in the
            processor fragments list."""
            for f in source_to_display_functions:
                i = f(i)
            return i

        for p in self.processors:
            transformation = p.apply_transformation(
                TransformationInput(
                    ti.buffer_control,
                    ti.document,
                    ti.lineno,
                    source_to_display,
                    fragments,
                    ti.width,
                    ti.height,
                    ti.get_line,
                )
            )
            fragments = transformation.fragments
            display_to_source_functions.append(transformation.display_to_source)
            source_to_display_functions.append(transformation.source_to_display)

        def display_to_source(i: int) -> int:
            for f in reversed(display_to_source_functions):
                i = f(i)
            return i

        # In the case of a nested _MergedProcessor, each processor wants to
        # receive a 'source_to_display' function (as part of the
        # TransformationInput) that has everything in the chain before
        # included, because it can be called as part of the
        # `apply_transformation` function. However, this first
        # `source_to_display` should not be part of the output that we are
        # returning. (This is the most consistent with `display_to_source`.)
        del source_to_display_functions[:1]

        return Transformation(fragments, source_to_display, display_to_source)

# === NexusCore/openenv\Lib\site-packages\cffi\cparser.py ===
from . import model
from .commontypes import COMMON_TYPES, resolve_common_type
from .error import FFIError, CDefError
try:
    from . import _pycparser as pycparser
except ImportError:
    import pycparser
import weakref, re, sys

try:
    if sys.version_info < (3,):
        import thread as _thread
    else:
        import _thread
    lock = _thread.allocate_lock()
except ImportError:
    lock = None

def _workaround_for_static_import_finders():
    # Issue #392: packaging tools like cx_Freeze can not find these
    # because pycparser uses exec dynamic import.  This is an obscure
    # workaround.  This function is never called.
    import pycparser.yacctab
    import pycparser.lextab

CDEF_SOURCE_STRING = "<cdef source string>"
_r_comment = re.compile(r"/\*.*?\*/|//([^\n\\]|\\.)*?$",
                        re.DOTALL | re.MULTILINE)
_r_define  = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z_0-9]*)"
                        r"\b((?:[^\n\\]|\\.)*?)$",
                        re.DOTALL | re.MULTILINE)
_r_line_directive = re.compile(r"^[ \t]*#[ \t]*(?:line|\d+)\b.*$", re.MULTILINE)
_r_partial_enum = re.compile(r"=\s*\.\.\.\s*[,}]|\.\.\.\s*\}")
_r_enum_dotdotdot = re.compile(r"__dotdotdot\d+__$")
_r_partial_array = re.compile(r"\[\s*\.\.\.\s*\]")
_r_words = re.compile(r"\w+|\S")
_parser_cache = None
_r_int_literal = re.compile(r"-?0?x?[0-9a-f]+[lu]*$", re.IGNORECASE)
_r_stdcall1 = re.compile(r"\b(__stdcall|WINAPI)\b")
_r_stdcall2 = re.compile(r"[(]\s*(__stdcall|WINAPI)\b")
_r_cdecl = re.compile(r"\b__cdecl\b")
_r_extern_python = re.compile(r'\bextern\s*"'
                              r'(Python|Python\s*\+\s*C|C\s*\+\s*Python)"\s*.')
_r_star_const_space = re.compile(       # matches "* const "
    r"[*]\s*((const|volatile|restrict)\b\s*)+")
_r_int_dotdotdot = re.compile(r"(\b(int|long|short|signed|unsigned|char)\s*)+"
                              r"\.\.\.")
_r_float_dotdotdot = re.compile(r"\b(double|float)\s*\.\.\.")

def _get_parser():
    global _parser_cache
    if _parser_cache is None:
        _parser_cache = pycparser.CParser()
    return _parser_cache

def _workaround_for_old_pycparser(csource):
    # Workaround for a pycparser issue (fixed between pycparser 2.10 and
    # 2.14): "char*const***" gives us a wrong syntax tree, the same as
    # for "char***(*const)".  This means we can't tell the difference
    # afterwards.  But "char(*const(***))" gives us the right syntax
    # tree.  The issue only occurs if there are several stars in
    # sequence with no parenthesis inbetween, just possibly qualifiers.
    # Attempt to fix it by adding some parentheses in the source: each
    # time we see "* const" or "* const *", we add an opening
    # parenthesis before each star---the hard part is figuring out where
    # to close them.
    parts = []
    while True:
        match = _r_star_const_space.search(csource)
        if not match:
            break
        #print repr(''.join(parts)+csource), '=>',
        parts.append(csource[:match.start()])
        parts.append('('); closing = ')'
        parts.append(match.group())   # e.g. "* const "
        endpos = match.end()
        if csource.startswith('*', endpos):
            parts.append('('); closing += ')'
        level = 0
        i = endpos
        while i < len(csource):
            c = csource[i]
            if c == '(':
                level += 1
            elif c == ')':
                if level == 0:
                    break
                level -= 1
            elif c in ',;=':
                if level == 0:
                    break
            i += 1
        csource = csource[endpos:i] + closing + csource[i:]
        #print repr(''.join(parts)+csource)
    parts.append(csource)
    return ''.join(parts)

def _preprocess_extern_python(csource):
    # input: `extern "Python" int foo(int);` or
    #        `extern "Python" { int foo(int); }`
    # output:
    #     void __cffi_extern_python_start;
    #     int foo(int);
    #     void __cffi_extern_python_stop;
    #
    # input: `extern "Python+C" int foo(int);`
    # output:
    #     void __cffi_extern_python_plus_c_start;
    #     int foo(int);
    #     void __cffi_extern_python_stop;
    parts = []
    while True:
        match = _r_extern_python.search(csource)
        if not match:
            break
        endpos = match.end() - 1
        #print
        #print ''.join(parts)+csource
        #print '=>'
        parts.append(csource[:match.start()])
        if 'C' in match.group(1):
            parts.append('void __cffi_extern_python_plus_c_start; ')
        else:
            parts.append('void __cffi_extern_python_start; ')
        if csource[endpos] == '{':
            # grouping variant
            closing = csource.find('}', endpos)
            if closing < 0:
                raise CDefError("'extern \"Python\" {': no '}' found")
            if csource.find('{', endpos + 1, closing) >= 0:
                raise NotImplementedError("cannot use { } inside a block "
                                          "'extern \"Python\" { ... }'")
            parts.append(csource[endpos+1:closing])
            csource = csource[closing+1:]
        else:
            # non-grouping variant
            semicolon = csource.find(';', endpos)
            if semicolon < 0:
                raise CDefError("'extern \"Python\": no ';' found")
            parts.append(csource[endpos:semicolon+1])
            csource = csource[semicolon+1:]
        parts.append(' void __cffi_extern_python_stop;')
        #print ''.join(parts)+csource
        #print
    parts.append(csource)
    return ''.join(parts)

def _warn_for_string_literal(csource):
    if '"' not in csource:
        return
    for line in csource.splitlines():
        if '"' in line and not line.lstrip().startswith('#'):
            import warnings
            warnings.warn("String literal found in cdef() or type source. "
                          "String literals are ignored here, but you should "
                          "remove them anyway because some character sequences "
                          "confuse pre-parsing.")
            break

def _warn_for_non_extern_non_static_global_variable(decl):
    if not decl.storage:
        import warnings
        warnings.warn("Global variable '%s' in cdef(): for consistency "
                      "with C it should have a storage class specifier "
                      "(usually 'extern')" % (decl.name,))

def _remove_line_directives(csource):
    # _r_line_directive matches whole lines, without the final \n, if they
    # start with '#line' with some spacing allowed, or '#NUMBER'.  This
    # function stores them away and replaces them with exactly the string
    # '#line@N', where N is the index in the list 'line_directives'.
    line_directives = []
    def replace(m):
        i = len(line_directives)
        line_directives.append(m.group())
        return '#line@%d' % i
    csource = _r_line_directive.sub(replace, csource)
    return csource, line_directives

def _put_back_line_directives(csource, line_directives):
    def replace(m):
        s = m.group()
        if not s.startswith('#line@'):
            raise AssertionError("unexpected #line directive "
                                 "(should have been processed and removed")
        return line_directives[int(s[6:])]
    return _r_line_directive.sub(replace, csource)

def _preprocess(csource):
    # First, remove the lines of the form '#line N "filename"' because
    # the "filename" part could confuse the rest
    csource, line_directives = _remove_line_directives(csource)
    # Remove comments.  NOTE: this only work because the cdef() section
    # should not contain any string literals (except in line directives)!
    def replace_keeping_newlines(m):
        return ' ' + m.group().count('\n') * '\n'
    csource = _r_comment.sub(replace_keeping_newlines, csource)
    # Remove the "#define FOO x" lines
    macros = {}
    for match in _r_define.finditer(csource):
        macroname, macrovalue = match.groups()
        macrovalue = macrovalue.replace('\\\n', '').strip()
        macros[macroname] = macrovalue
    csource = _r_define.sub('', csource)
    #
    if pycparser.__version__ < '2.14':
        csource = _workaround_for_old_pycparser(csource)
    #
    # BIG HACK: replace WINAPI or __stdcall with "volatile const".
    # It doesn't make sense for the return type of a function to be
    # "volatile volatile const", so we abuse it to detect __stdcall...
    # Hack number 2 is that "int(volatile *fptr)();" is not valid C
    # syntax, so we place the "volatile" before the opening parenthesis.
    csource = _r_stdcall2.sub(' volatile volatile const(', csource)
    csource = _r_stdcall1.sub(' volatile volatile const ', csource)
    csource = _r_cdecl.sub(' ', csource)
    #
    # Replace `extern "Python"` with start/end markers
    csource = _preprocess_extern_python(csource)
    #
    # Now there should not be any string literal left; warn if we get one
    _warn_for_string_literal(csource)
    #
    # Replace "[...]" with "[__dotdotdotarray__]"
    csource = _r_partial_array.sub('[__dotdotdotarray__]', csource)
    #
    # Replace "...}" with "__dotdotdotNUM__}".  This construction should
    # occur only at the end of enums; at the end of structs we have "...;}"
    # and at the end of vararg functions "...);".  Also replace "=...[,}]"
    # with ",__dotdotdotNUM__[,}]": this occurs in the enums too, when
    # giving an unknown value.
    matches = list(_r_partial_enum.finditer(csource))
    for number, match in enumerate(reversed(matches)):
        p = match.start()
        if csource[p] == '=':
            p2 = csource.find('...', p, match.end())
            assert p2 > p
            csource = '%s,__dotdotdot%d__ %s' % (csource[:p], number,
                                                 csource[p2+3:])
        else:
            assert csource[p:p+3] == '...'
            csource = '%s __dotdotdot%d__ %s' % (csource[:p], number,
                                                 csource[p+3:])
    # Replace "int ..." or "unsigned long int..." with "__dotdotdotint__"
    csource = _r_int_dotdotdot.sub(' __dotdotdotint__ ', csource)
    # Replace "float ..." or "double..." with "__dotdotdotfloat__"
    csource = _r_float_dotdotdot.sub(' __dotdotdotfloat__ ', csource)
    # Replace all remaining "..." with the same name, "__dotdotdot__",
    # which is declared with a typedef for the purpose of C parsing.
    csource = csource.replace('...', ' __dotdotdot__ ')
    # Finally, put back the line directives
    csource = _put_back_line_directives(csource, line_directives)
    return csource, macros

def _common_type_names(csource):
    # Look in the source for what looks like usages of types from the
    # list of common types.  A "usage" is approximated here as the
    # appearance of the word, minus a "definition" of the type, which
    # is the last word in a "typedef" statement.  Approximative only
    # but should be fine for all the common types.
    look_for_words = set(COMMON_TYPES)
    look_for_words.add(';')
    look_for_words.add(',')
    look_for_words.add('(')
    look_for_words.add(')')
    look_for_words.add('typedef')
    words_used = set()
    is_typedef = False
    paren = 0
    previous_word = ''
    for word in _r_words.findall(csource):
        if word in look_for_words:
            if word == ';':
                if is_typedef:
                    words_used.discard(previous_word)
                    look_for_words.discard(previous_word)
                    is_typedef = False
            elif word == 'typedef':
                is_typedef = True
                paren = 0
            elif word == '(':
                paren += 1
            elif word == ')':
                paren -= 1
            elif word == ',':
                if is_typedef and paren == 0:
                    words_used.discard(previous_word)
                    look_for_words.discard(previous_word)
            else:   # word in COMMON_TYPES
                words_used.add(word)
        previous_word = word
    return words_used


class Parser(object):

    def __init__(self):
        self._declarations = {}
        self._included_declarations = set()
        self._anonymous_counter = 0
        self._structnode2type = weakref.WeakKeyDictionary()
        self._options = {}
        self._int_constants = {}
        self._recomplete = []
        self._uses_new_feature = None

    def _parse(self, csource):
        csource, macros = _preprocess(csource)
        # XXX: for more efficiency we would need to poke into the
        # internals of CParser...  the following registers the
        # typedefs, because their presence or absence influences the
        # parsing itself (but what they are typedef'ed to plays no role)
        ctn = _common_type_names(csource)
        typenames = []
        for name in sorted(self._declarations):
            if name.startswith('typedef '):
                name = name[8:]
                typenames.append(name)
                ctn.discard(name)
        typenames += sorted(ctn)
        #
        csourcelines = []
        csourcelines.append('# 1 "<cdef automatic initialization code>"')
        for typename in typenames:
            csourcelines.append('typedef int %s;' % typename)
        csourcelines.append('typedef int __dotdotdotint__, __dotdotdotfloat__,'
                            ' __dotdotdot__;')
        # this forces pycparser to consider the following in the file
        # called <cdef source string> from line 1
        csourcelines.append('# 1 "%s"' % (CDEF_SOURCE_STRING,))
        csourcelines.append(csource)
        csourcelines.append('')   # see test_missing_newline_bug
        fullcsource = '\n'.join(csourcelines)
        if lock is not None:
            lock.acquire()     # pycparser is not thread-safe...
        try:
            ast = _get_parser().parse(fullcsource)
        except pycparser.c_parser.ParseError as e:
            self.convert_pycparser_error(e, csource)
        finally:
            if lock is not None:
                lock.release()
        # csource will be used to find buggy source text
        return ast, macros, csource

    def _convert_pycparser_error(self, e, csource):
        # xxx look for "<cdef source string>:NUM:" at the start of str(e)
        # and interpret that as a line number.  This will not work if
        # the user gives explicit ``# NUM "FILE"`` directives.
        line = None
        msg = str(e)
        match = re.match(r"%s:(\d+):" % (CDEF_SOURCE_STRING,), msg)
        if match:
            linenum = int(match.group(1), 10)
            csourcelines = csource.splitlines()
            if 1 <= linenum <= len(csourcelines):
                line = csourcelines[linenum-1]
        return line

    def convert_pycparser_error(self, e, csource):
        line = self._convert_pycparser_error(e, csource)

        msg = str(e)
        if line:
            msg = 'cannot parse "%s"\n%s' % (line.strip(), msg)
        else:
            msg = 'parse error\n%s' % (msg,)
        raise CDefError(msg)

    def parse(self, csource, override=False, packed=False, pack=None,
                    dllexport=False):
        if packed:
            if packed != True:
                raise ValueError("'packed' should be False or True; use "
                                 "'pack' to give another value")
            if pack:
                raise ValueError("cannot give both 'pack' and 'packed'")
            pack = 1
        elif pack:
            if pack & (pack - 1):
                raise ValueError("'pack' must be a power of two, not %r" %
                    (pack,))
        else:
            pack = 0
        prev_options = self._options
        try:
            self._options = {'override': override,
                             'packed': pack,
                             'dllexport': dllexport}
            self._internal_parse(csource)
        finally:
            self._options = prev_options

    def _internal_parse(self, csource):
        ast, macros, csource = self._parse(csource)
        # add the macros
        self._process_macros(macros)
        # find the first "__dotdotdot__" and use that as a separator
        # between the repeated typedefs and the real csource
        iterator = iter(ast.ext)
        for decl in iterator:
            if decl.name == '__dotdotdot__':
                break
        else:
            assert 0
        current_decl = None
        #
        try:
            self._inside_extern_python = '__cffi_extern_python_stop'
            for decl in iterator:
                current_decl = decl
                if isinstance(decl, pycparser.c_ast.Decl):
                    self._parse_decl(decl)
                elif isinstance(decl, pycparser.c_ast.Typedef):
                    if not decl.name:
                        raise CDefError("typedef does not declare any name",
                                        decl)
                    quals = 0
                    if (isinstance(decl.type.type, pycparser.c_ast.IdentifierType) and
                            decl.type.type.names[-1].startswith('__dotdotdot')):
                        realtype = self._get_unknown_type(decl)
                    elif (isinstance(decl.type, pycparser.c_ast.PtrDecl) and
                          isinstance(decl.type.type, pycparser.c_ast.TypeDecl) and
                          isinstance(decl.type.type.type,
                                     pycparser.c_ast.IdentifierType) and
                          decl.type.type.type.names[-1].startswith('__dotdotdot')):
                        realtype = self._get_unknown_ptr_type(decl)
                    else:
                        realtype, quals = self._get_type_and_quals(
                            decl.type, name=decl.name, partial_length_ok=True,
                            typedef_example="*(%s *)0" % (decl.name,))
                    self._declare('typedef ' + decl.name, realtype, quals=quals)
                elif decl.__class__.__name__ == 'Pragma':
                    # skip pragma, only in pycparser 2.15
                    import warnings
                    warnings.warn(
                        "#pragma in cdef() are entirely ignored. "
                        "They should be removed for now, otherwise your "
                        "code might behave differently in a future version "
                        "of CFFI if #pragma support gets added. Note that "
                        "'#pragma pack' needs to be replaced with the "
                        "'packed' keyword argument to cdef().")
                else:
                    raise CDefError("unexpected <%s>: this construct is valid "
                                    "C but not valid in cdef()" %
                                    decl.__class__.__name__, decl)
        except CDefError as e:
            if len(e.args) == 1:
                e.args = e.args + (current_decl,)
            raise
        except FFIError as e:
            msg = self._convert_pycparser_error(e, csource)
            if msg:
                e.args = (e.args[0] + "\n    *** Err: %s" % msg,)
            raise

    def _add_constants(self, key, val):
        if key in self._int_constants:
            if self._int_constants[key] == val:
                return     # ignore identical double declarations
            raise FFIError(
                "multiple declarations of constant: %s" % (key,))
        self._int_constants[key] = val

    def _add_integer_constant(self, name, int_str):
        int_str = int_str.lower().rstrip("ul")
        neg = int_str.startswith('-')
        if neg:
            int_str = int_str[1:]
        # "010" is not valid oct in py3
        if (int_str.startswith("0") and int_str != '0'
                and not int_str.startswith("0x")):
            int_str = "0o" + int_str[1:]
        pyvalue = int(int_str, 0)
        if neg:
            pyvalue = -pyvalue
        self._add_constants(name, pyvalue)
        self._declare('macro ' + name, pyvalue)

    def _process_macros(self, macros):
        for key, value in macros.items():
            value = value.strip()
            if _r_int_literal.match(value):
                self._add_integer_constant(key, value)
            elif value == '...':
                self._declare('macro ' + key, value)
            else:
                raise CDefError(
                    'only supports one of the following syntax:\n'
                    '  #define %s ...     (literally dot-dot-dot)\n'
                    '  #define %s NUMBER  (with NUMBER an integer'
                                    ' constant, decimal/hex/octal)\n'
                    'got:\n'
                    '  #define %s %s'
                    % (key, key, key, value))

    def _declare_function(self, tp, quals, decl):
        tp = self._get_type_pointer(tp, quals)
        if self._options.get('dllexport'):
            tag = 'dllexport_python '
        elif self._inside_extern_python == '__cffi_extern_python_start':
            tag = 'extern_python '
        elif self._inside_extern_python == '__cffi_extern_python_plus_c_start':
            tag = 'extern_python_plus_c '
        else:
            tag = 'function '
        self._declare(tag + decl.name, tp)

    def _parse_decl(self, decl):
        node = decl.type
        if isinstance(node, pycparser.c_ast.FuncDecl):
            tp, quals = self._get_type_and_quals(node, name=decl.name)
            assert isinstance(tp, model.RawFunctionType)
            self._declare_function(tp, quals, decl)
        else:
            if isinstance(node, pycparser.c_ast.Struct):
                self._get_struct_union_enum_type('struct', node)
            elif isinstance(node, pycparser.c_ast.Union):
                self._get_struct_union_enum_type('union', node)
            elif isinstance(node, pycparser.c_ast.Enum):
                self._get_struct_union_enum_type('enum', node)
            elif not decl.name:
                raise CDefError("construct does not declare any variable",
                                decl)
            #
            if decl.name:
                tp, quals = self._get_type_and_quals(node,
                                                     partial_length_ok=True)
                if tp.is_raw_function:
                    self._declare_function(tp, quals, decl)
                elif (tp.is_integer_type() and
                        hasattr(decl, 'init') and
                        hasattr(decl.init, 'value') and
                        _r_int_literal.match(decl.init.value)):
                    self._add_integer_constant(decl.name, decl.init.value)
                elif (tp.is_integer_type() and
                        isinstance(decl.init, pycparser.c_ast.UnaryOp) and
                        decl.init.op == '-' and
                        hasattr(decl.init.expr, 'value') and
                        _r_int_literal.match(decl.init.expr.value)):
                    self._add_integer_constant(decl.name,
                                               '-' + decl.init.expr.value)
                elif (tp is model.void_type and
                      decl.name.startswith('__cffi_extern_python_')):
                    # hack: `extern "Python"` in the C source is replaced
                    # with "void __cffi_extern_python_start;" and
                    # "void __cffi_extern_python_stop;"
                    self._inside_extern_python = decl.name
                else:
                    if self._inside_extern_python !='__cffi_extern_python_stop':
                        raise CDefError(
                            "cannot declare constants or "
                            "variables with 'extern \"Python\"'")
                    if (quals & model.Q_CONST) and not tp.is_array_type:
                        self._declare('constant ' + decl.name, tp, quals=quals)
                    else:
                        _warn_for_non_extern_non_static_global_variable(decl)
                        self._declare('variable ' + decl.name, tp, quals=quals)

    def parse_type(self, cdecl):
        return self.parse_type_and_quals(cdecl)[0]

    def parse_type_and_quals(self, cdecl):
        ast, macros = self._parse('void __dummy(\n%s\n);' % cdecl)[:2]
        assert not macros
        exprnode = ast.ext[-1].type.args.params[0]
        if isinstance(exprnode, pycparser.c_ast.ID):
            raise CDefError("unknown identifier '%s'" % (exprnode.name,))
        return self._get_type_and_quals(exprnode.type)

    def _declare(self, name, obj, included=False, quals=0):
        if name in self._declarations:
            prevobj, prevquals = self._declarations[name]
            if prevobj is obj and prevquals == quals:
                return
            if not self._options.get('override'):
                raise FFIError(
                    "multiple declarations of %s (for interactive usage, "
                    "try cdef(xx, override=True))" % (name,))
        assert '__dotdotdot__' not in name.split()
        self._declarations[name] = (obj, quals)
        if included:
            self._included_declarations.add(obj)

    def _extract_quals(self, type):
        quals = 0
        if isinstance(type, (pycparser.c_ast.TypeDecl,
                             pycparser.c_ast.PtrDecl)):
            if 'const' in type.quals:
                quals |= model.Q_CONST
            if 'volatile' in type.quals:
                quals |= model.Q_VOLATILE
            if 'restrict' in type.quals:
                quals |= model.Q_RESTRICT
        return quals

    def _get_type_pointer(self, type, quals, declname=None):
        if isinstance(type, model.RawFunctionType):
            return type.as_function_pointer()
        if (isinstance(type, model.StructOrUnionOrEnum) and
                type.name.startswith('$') and type.name[1:].isdigit() and
                type.forcename is None and declname is not None):
            return model.NamedPointerType(type, declname, quals)
        return model.PointerType(type, quals)

    def _get_type_and_quals(self, typenode, name=None, partial_length_ok=False,
                            typedef_example=None):
        # first, dereference typedefs, if we have it already parsed, we're good
        if (isinstance(typenode, pycparser.c_ast.TypeDecl) and
            isinstance(typenode.type, pycparser.c_ast.IdentifierType) and
            len(typenode.type.names) == 1 and
            ('typedef ' + typenode.type.names[0]) in self._declarations):
            tp, quals = self._declarations['typedef ' + typenode.type.names[0]]
            quals |= self._extract_quals(typenode)
            return tp, quals
        #
        if isinstance(typenode, pycparser.c_ast.ArrayDecl):
            # array type
            if typenode.dim is None:
                length = None
            else:
                length = self._parse_constant(
                    typenode.dim, partial_length_ok=partial_length_ok)
            # a hack: in 'typedef int foo_t[...][...];', don't use '...' as
            # the length but use directly the C expression that would be
            # generated by recompiler.py.  This lets the typedef be used in
            # many more places within recompiler.py
            if typedef_example is not None:
                if length == '...':
                    length = '_cffi_array_len(%s)' % (typedef_example,)
                typedef_example = "*" + typedef_example
            #
            tp, quals = self._get_type_and_quals(typenode.type,
                                partial_length_ok=partial_length_ok,
                                typedef_example=typedef_example)
            return model.ArrayType(tp, length), quals
        #
        if isinstance(typenode, pycparser.c_ast.PtrDecl):
            # pointer type
            itemtype, itemquals = self._get_type_and_quals(typenode.type)
            tp = self._get_type_pointer(itemtype, itemquals, declname=name)
            quals = self._extract_quals(typenode)
            return tp, quals
        #
        if isinstance(typenode, pycparser.c_ast.TypeDecl):
            quals = self._extract_quals(typenode)
            type = typenode.type
            if isinstance(type, pycparser.c_ast.IdentifierType):
                # assume a primitive type.  get it from .names, but reduce
                # synonyms to a single chosen combination
                names = list(type.names)
                if names != ['signed', 'char']:    # keep this unmodified
                    prefixes = {}
                    while names:
                        name = names[0]
                        if name in ('short', 'long', 'signed', 'unsigned'):
                            prefixes[name] = prefixes.get(name, 0) + 1
                            del names[0]
                        else:
                            break
                    # ignore the 'signed' prefix below, and reorder the others
                    newnames = []
                    for prefix in ('unsigned', 'short', 'long'):
                        for i in range(prefixes.get(prefix, 0)):
                            newnames.append(prefix)
                    if not names:
                        names = ['int']    # implicitly
                    if names == ['int']:   # but kill it if 'short' or 'long'
                        if 'short' in prefixes or 'long' in prefixes:
                            names = []
                    names = newnames + names
                ident = ' '.join(names)
                if ident == 'void':
                    return model.void_type, quals
                if ident == '__dotdotdot__':
                    raise FFIError(':%d: bad usage of "..."' %
                            typenode.coord.line)
                tp0, quals0 = resolve_common_type(self, ident)
                return tp0, (quals | quals0)
            #
            if isinstance(type, pycparser.c_ast.Struct):
                # 'struct foobar'
                tp = self._get_struct_union_enum_type('struct', type, name)
                return tp, quals
            #
            if isinstance(type, pycparser.c_ast.Union):
                # 'union foobar'
                tp = self._get_struct_union_enum_type('union', type, name)
                return tp, quals
            #
            if isinstance(type, pycparser.c_ast.Enum):
                # 'enum foobar'
                tp = self._get_struct_union_enum_type('enum', type, name)
                return tp, quals
        #
        if isinstance(typenode, pycparser.c_ast.FuncDecl):
            # a function type
            return self._parse_function_type(typenode, name), 0
        #
        # nested anonymous structs or unions end up here
        if isinstance(typenode, pycparser.c_ast.Struct):
            return self._get_struct_union_enum_type('struct', typenode, name,
                                                    nested=True), 0
        if isinstance(typenode, pycparser.c_ast.Union):
            return self._get_struct_union_enum_type('union', typenode, name,
                                                    nested=True), 0
        #
        raise FFIError(":%d: bad or unsupported type declaration" %
                typenode.coord.line)

    def _parse_function_type(self, typenode, funcname=None):
        params = list(getattr(typenode.args, 'params', []))
        for i, arg in enumerate(params):
            if not hasattr(arg, 'type'):
                raise CDefError("%s arg %d: unknown type '%s'"
                    " (if you meant to use the old C syntax of giving"
                    " untyped arguments, it is not supported)"
                    % (funcname or 'in expression', i + 1,
                       getattr(arg, 'name', '?')))
        ellipsis = (
            len(params) > 0 and
            isinstance(params[-1].type, pycparser.c_ast.TypeDecl) and
            isinstance(params[-1].type.type,
                       pycparser.c_ast.IdentifierType) and
            params[-1].type.type.names == ['__dotdotdot__'])
        if ellipsis:
            params.pop()
            if not params:
                raise CDefError(
                    "%s: a function with only '(...)' as argument"
                    " is not correct C" % (funcname or 'in expression'))
        args = [self._as_func_arg(*self._get_type_and_quals(argdeclnode.type))
                for argdeclnode in params]
        if not ellipsis and args == [model.void_type]:
            args = []
        result, quals = self._get_type_and_quals(typenode.type)
        # the 'quals' on the result type are ignored.  HACK: we absure them
        # to detect __stdcall functions: we textually replace "__stdcall"
        # with "volatile volatile const" above.
        abi = None
        if hasattr(typenode.type, 'quals'): # else, probable syntax error anyway
            if typenode.type.quals[-3:] == ['volatile', 'volatile', 'const']:
                abi = '__stdcall'
        return model.RawFunctionType(tuple(args), result, ellipsis, abi)

    def _as_func_arg(self, type, quals):
        if isinstance(type, model.ArrayType):
            return model.PointerType(type.item, quals)
        elif isinstance(type, model.RawFunctionType):
            return type.as_function_pointer()
        else:
            return type

    def _get_struct_union_enum_type(self, kind, type, name=None, nested=False):
        # First, a level of caching on the exact 'type' node of the AST.
        # This is obscure, but needed because pycparser "unrolls" declarations
        # such as "typedef struct { } foo_t, *foo_p" and we end up with
        # an AST that is not a tree, but a DAG, with the "type" node of the
        # two branches foo_t and foo_p of the trees being the same node.
        # It's a bit silly but detecting "DAG-ness" in the AST tree seems
        # to be the only way to distinguish this case from two independent
        # structs.  See test_struct_with_two_usages.
        try:
            return self._structnode2type[type]
        except KeyError:
            pass
        #
        # Note that this must handle parsing "struct foo" any number of
        # times and always return the same StructType object.  Additionally,
        # one of these times (not necessarily the first), the fields of
        # the struct can be specified with "struct foo { ...fields... }".
        # If no name is given, then we have to create a new anonymous struct
        # with no caching; in this case, the fields are either specified
        # right now or never.
        #
        force_name = name
        name = type.name
        #
        # get the type or create it if needed
        if name is None:
            # 'force_name' is used to guess a more readable name for
            # anonymous structs, for the common case "typedef struct { } foo".
            if force_name is not None:
                explicit_name = '$%s' % force_name
            else:
                self._anonymous_counter += 1
                explicit_name = '$%d' % self._anonymous_counter
            tp = None
        else:
            explicit_name = name
            key = '%s %s' % (kind, name)
            tp, _ = self._declarations.get(key, (None, None))
        #
        if tp is None:
            if kind == 'struct':
                tp = model.StructType(explicit_name, None, None, None)
            elif kind == 'union':
                tp = model.UnionType(explicit_name, None, None, None)
            elif kind == 'enum':
                if explicit_name == '__dotdotdot__':
                    raise CDefError("Enums cannot be declared with ...")
                tp = self._build_enum_type(explicit_name, type.values)
            else:
                raise AssertionError("kind = %r" % (kind,))
            if name is not None:
                self._declare(key, tp)
        else:
            if kind == 'enum' and type.values is not None:
                raise NotImplementedError(
                    "enum %s: the '{}' declaration should appear on the first "
                    "time the enum is mentioned, not later" % explicit_name)
        if not tp.forcename:
            tp.force_the_name(force_name)
        if tp.forcename and '$' in tp.name:
            self._declare('anonymous %s' % tp.forcename, tp)
        #
        self._structnode2type[type] = tp
        #
        # enums: done here
        if kind == 'enum':
            return tp
        #
        # is there a 'type.decls'?  If yes, then this is the place in the
        # C sources that declare the fields.  If no, then just return the
        # existing type, possibly still incomplete.
        if type.decls is None:
            return tp
        #
        if tp.fldnames is not None:
            raise CDefError("duplicate declaration of struct %s" % name)
        fldnames = []
        fldtypes = []
        fldbitsize = []
        fldquals = []
        for decl in type.decls:
            if (isinstance(decl.type, pycparser.c_ast.IdentifierType) and
                    ''.join(decl.type.names) == '__dotdotdot__'):
                # XXX pycparser is inconsistent: 'names' should be a list
                # of strings, but is sometimes just one string.  Use
                # str.join() as a way to cope with both.
                self._make_partial(tp, nested)
                continue
            if decl.bitsize is None:
                bitsize = -1
            else:
                bitsize = self._parse_constant(decl.bitsize)
            self._partial_length = False
            type, fqual = self._get_type_and_quals(decl.type,
                                                   partial_length_ok=True)
            if self._partial_length:
                self._make_partial(tp, nested)
            if isinstance(type, model.StructType) and type.partial:
                self._make_partial(tp, nested)
            fldnames.append(decl.name or '')
            fldtypes.append(type)
            fldbitsize.append(bitsize)
            fldquals.append(fqual)
        tp.fldnames = tuple(fldnames)
        tp.fldtypes = tuple(fldtypes)
        tp.fldbitsize = tuple(fldbitsize)
        tp.fldquals = tuple(fldquals)
        if fldbitsize != [-1] * len(fldbitsize):
            if isinstance(tp, model.StructType) and tp.partial:
                raise NotImplementedError("%s: using both bitfields and '...;'"
                                          % (tp,))
        tp.packed = self._options.get('packed')
        if tp.completed:    # must be re-completed: it is not opaque any more
            tp.completed = 0
            self._recomplete.append(tp)
        return tp

    def _make_partial(self, tp, nested):
        if not isinstance(tp, model.StructOrUnion):
            raise CDefError("%s cannot be partial" % (tp,))
        if not tp.has_c_name() and not nested:
            raise NotImplementedError("%s is partial but has no C name" %(tp,))
        tp.partial = True

    def _parse_constant(self, exprnode, partial_length_ok=False):
        # for now, limited to expressions that are an immediate number
        # or positive/negative number
        if isinstance(exprnode, pycparser.c_ast.Constant):
            s = exprnode.value
            if '0' <= s[0] <= '9':
                s = s.rstrip('uUlL')
                try:
                    if s.startswith('0'):
                        return int(s, 8)
                    else:
                        return int(s, 10)
                except ValueError:
                    if len(s) > 1:
                        if s.lower()[0:2] == '0x':
                            return int(s, 16)
                        elif s.lower()[0:2] == '0b':
                            return int(s, 2)
                raise CDefError("invalid constant %r" % (s,))
            elif s[0] == "'" and s[-1] == "'" and (
                    len(s) == 3 or (len(s) == 4 and s[1] == "\\")):
                return ord(s[-2])
            else:
                raise CDefError("invalid constant %r" % (s,))
        #
        if (isinstance(exprnode, pycparser.c_ast.UnaryOp) and
                exprnode.op == '+'):
            return self._parse_constant(exprnode.expr)
        #
        if (isinstance(exprnode, pycparser.c_ast.UnaryOp) and
                exprnode.op == '-'):
            return -self._parse_constant(exprnode.expr)
        # load previously defined int constant
        if (isinstance(exprnode, pycparser.c_ast.ID) and
                exprnode.name in self._int_constants):
            return self._int_constants[exprnode.name]
        #
        if (isinstance(exprnode, pycparser.c_ast.ID) and
                    exprnode.name == '__dotdotdotarray__'):
            if partial_length_ok:
                self._partial_length = True
                return '...'
            raise FFIError(":%d: unsupported '[...]' here, cannot derive "
                           "the actual array length in this context"
                           % exprnode.coord.line)
        #
        if isinstance(exprnode, pycparser.c_ast.BinaryOp):
            left = self._parse_constant(exprnode.left)
            right = self._parse_constant(exprnode.right)
            if exprnode.op == '+':
                return left + right
            elif exprnode.op == '-':
                return left - right
            elif exprnode.op == '*':
                return left * right
            elif exprnode.op == '/':
                return self._c_div(left, right)
            elif exprnode.op == '%':
                return left - self._c_div(left, right) * right
            elif exprnode.op == '<<':
                return left << right
            elif exprnode.op == '>>':
                return left >> right
            elif exprnode.op == '&':
                return left & right
            elif exprnode.op == '|':
                return left | right
            elif exprnode.op == '^':
                return left ^ right
        #
        raise FFIError(":%d: unsupported expression: expected a "
                       "simple numeric constant" % exprnode.coord.line)

    def _c_div(self, a, b):
        result = a // b
        if ((a < 0) ^ (b < 0)) and (a % b) != 0:
            result += 1
        return result

    def _build_enum_type(self, explicit_name, decls):
        if decls is not None:
            partial = False
            enumerators = []
            enumvalues = []
            nextenumvalue = 0
            for enum in decls.enumerators:
                if _r_enum_dotdotdot.match(enum.name):
                    partial = True
                    continue
                if enum.value is not None:
                    nextenumvalue = self._parse_constant(enum.value)
                enumerators.append(enum.name)
                enumvalues.append(nextenumvalue)
                self._add_constants(enum.name, nextenumvalue)
                nextenumvalue += 1
            enumerators = tuple(enumerators)
            enumvalues = tuple(enumvalues)
            tp = model.EnumType(explicit_name, enumerators, enumvalues)
            tp.partial = partial
        else:   # opaque enum
            tp = model.EnumType(explicit_name, (), ())
        return tp

    def include(self, other):
        for name, (tp, quals) in other._declarations.items():
            if name.startswith('anonymous $enum_$'):
                continue   # fix for test_anonymous_enum_include
            kind = name.split(' ', 1)[0]
            if kind in ('struct', 'union', 'enum', 'anonymous', 'typedef'):
                self._declare(name, tp, included=True, quals=quals)
        for k, v in other._int_constants.items():
            self._add_constants(k, v)

    def _get_unknown_type(self, decl):
        typenames = decl.type.type.names
        if typenames == ['__dotdotdot__']:
            return model.unknown_type(decl.name)

        if typenames == ['__dotdotdotint__']:
            if self._uses_new_feature is None:
                self._uses_new_feature = "'typedef int... %s'" % decl.name
            return model.UnknownIntegerType(decl.name)

        if typenames == ['__dotdotdotfloat__']:
            # note: not for 'long double' so far
            if self._uses_new_feature is None:
                self._uses_new_feature = "'typedef float... %s'" % decl.name
            return model.UnknownFloatType(decl.name)

        raise FFIError(':%d: unsupported usage of "..." in typedef'
                       % decl.coord.line)

    def _get_unknown_ptr_type(self, decl):
        if decl.type.type.type.names == ['__dotdotdot__']:
            return model.unknown_ptr_type(decl.name)
        raise FFIError(':%d: unsupported usage of "..." in typedef'
                       % decl.coord.line)

# === NexusCore/openenv\Lib\site-packages\grpc\beta\_client_adaptations.py ===
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
"""Translates gRPC's client-side API into gRPC's client-side Beta API."""

import grpc
from grpc import _common
from grpc.beta import _metadata
from grpc.beta import interfaces
from grpc.framework.common import cardinality
from grpc.framework.foundation import future
from grpc.framework.interfaces.face import face

# pylint: disable=too-many-arguments,too-many-locals,unused-argument

_STATUS_CODE_TO_ABORTION_KIND_AND_ABORTION_ERROR_CLASS = {
    grpc.StatusCode.CANCELLED: (
        face.Abortion.Kind.CANCELLED,
        face.CancellationError,
    ),
    grpc.StatusCode.UNKNOWN: (
        face.Abortion.Kind.REMOTE_FAILURE,
        face.RemoteError,
    ),
    grpc.StatusCode.DEADLINE_EXCEEDED: (
        face.Abortion.Kind.EXPIRED,
        face.ExpirationError,
    ),
    grpc.StatusCode.UNIMPLEMENTED: (
        face.Abortion.Kind.LOCAL_FAILURE,
        face.LocalError,
    ),
}


def _effective_metadata(metadata, metadata_transformer):
    non_none_metadata = () if metadata is None else metadata
    if metadata_transformer is None:
        return non_none_metadata
    else:
        return metadata_transformer(non_none_metadata)


def _credentials(grpc_call_options):
    return None if grpc_call_options is None else grpc_call_options.credentials


def _abortion(rpc_error_call):
    code = rpc_error_call.code()
    pair = _STATUS_CODE_TO_ABORTION_KIND_AND_ABORTION_ERROR_CLASS.get(code)
    error_kind = face.Abortion.Kind.LOCAL_FAILURE if pair is None else pair[0]
    return face.Abortion(
        error_kind,
        rpc_error_call.initial_metadata(),
        rpc_error_call.trailing_metadata(),
        code,
        rpc_error_call.details(),
    )


def _abortion_error(rpc_error_call):
    code = rpc_error_call.code()
    pair = _STATUS_CODE_TO_ABORTION_KIND_AND_ABORTION_ERROR_CLASS.get(code)
    exception_class = face.AbortionError if pair is None else pair[1]
    return exception_class(
        rpc_error_call.initial_metadata(),
        rpc_error_call.trailing_metadata(),
        code,
        rpc_error_call.details(),
    )


class _InvocationProtocolContext(interfaces.GRPCInvocationContext):
    def disable_next_request_compression(self):
        pass  # TODO(https://github.com/grpc/grpc/issues/4078): design, implement.


class _Rendezvous(future.Future, face.Call):
    def __init__(self, response_future, response_iterator, call):
        self._future = response_future
        self._iterator = response_iterator
        self._call = call

    def cancel(self):
        return self._call.cancel()

    def cancelled(self):
        return self._future.cancelled()

    def running(self):
        return self._future.running()

    def done(self):
        return self._future.done()

    def result(self, timeout=None):
        try:
            return self._future.result(timeout=timeout)
        except grpc.RpcError as rpc_error_call:
            raise _abortion_error(rpc_error_call)
        except grpc.FutureTimeoutError:
            raise future.TimeoutError()
        except grpc.FutureCancelledError:
            raise future.CancelledError()

    def exception(self, timeout=None):
        try:
            rpc_error_call = self._future.exception(timeout=timeout)
            if rpc_error_call is None:
                return None
            else:
                return _abortion_error(rpc_error_call)
        except grpc.FutureTimeoutError:
            raise future.TimeoutError()
        except grpc.FutureCancelledError:
            raise future.CancelledError()

    def traceback(self, timeout=None):
        try:
            return self._future.traceback(timeout=timeout)
        except grpc.FutureTimeoutError:
            raise future.TimeoutError()
        except grpc.FutureCancelledError:
            raise future.CancelledError()

    def add_done_callback(self, fn):
        self._future.add_done_callback(lambda ignored_callback: fn(self))

    def __iter__(self):
        return self

    def _next(self):
        try:
            return next(self._iterator)
        except grpc.RpcError as rpc_error_call:
            raise _abortion_error(rpc_error_call)

    def __next__(self):
        return self._next()

    def next(self):
        return self._next()

    def is_active(self):
        return self._call.is_active()

    def time_remaining(self):
        return self._call.time_remaining()

    def add_abortion_callback(self, abortion_callback):
        def done_callback():
            if self.code() is not grpc.StatusCode.OK:
                abortion_callback(_abortion(self._call))

        registered = self._call.add_callback(done_callback)
        return None if registered else done_callback()

    def protocol_context(self):
        return _InvocationProtocolContext()

    def initial_metadata(self):
        return _metadata.beta(self._call.initial_metadata())

    def terminal_metadata(self):
        return _metadata.beta(self._call.terminal_metadata())

    def code(self):
        return self._call.code()

    def details(self):
        return self._call.details()


def _blocking_unary_unary(
    channel,
    group,
    method,
    timeout,
    with_call,
    protocol_options,
    metadata,
    metadata_transformer,
    request,
    request_serializer,
    response_deserializer,
):
    try:
        multi_callable = channel.unary_unary(
            _common.fully_qualified_method(group, method),
            request_serializer=request_serializer,
            response_deserializer=response_deserializer,
        )
        effective_metadata = _effective_metadata(metadata, metadata_transformer)
        if with_call:
            response, call = multi_callable.with_call(
                request,
                timeout=timeout,
                metadata=_metadata.unbeta(effective_metadata),
                credentials=_credentials(protocol_options),
            )
            return response, _Rendezvous(None, None, call)
        else:
            return multi_callable(
                request,
                timeout=timeout,
                metadata=_metadata.unbeta(effective_metadata),
                credentials=_credentials(protocol_options),
            )
    except grpc.RpcError as rpc_error_call:
        raise _abortion_error(rpc_error_call)


def _future_unary_unary(
    channel,
    group,
    method,
    timeout,
    protocol_options,
    metadata,
    metadata_transformer,
    request,
    request_serializer,
    response_deserializer,
):
    multi_callable = channel.unary_unary(
        _common.fully_qualified_method(group, method),
        request_serializer=request_serializer,
        response_deserializer=response_deserializer,
    )
    effective_metadata = _effective_metadata(metadata, metadata_transformer)
    response_future = multi_callable.future(
        request,
        timeout=timeout,
        metadata=_metadata.unbeta(effective_metadata),
        credentials=_credentials(protocol_options),
    )
    return _Rendezvous(response_future, None, response_future)


def _unary_stream(
    channel,
    group,
    method,
    timeout,
    protocol_options,
    metadata,
    metadata_transformer,
    request,
    request_serializer,
    response_deserializer,
):
    multi_callable = channel.unary_stream(
        _common.fully_qualified_method(group, method),
        request_serializer=request_serializer,
        response_deserializer=response_deserializer,
    )
    effective_metadata = _effective_metadata(metadata, metadata_transformer)
    response_iterator = multi_callable(
        request,
        timeout=timeout,
        metadata=_metadata.unbeta(effective_metadata),
        credentials=_credentials(protocol_options),
    )
    return _Rendezvous(None, response_iterator, response_iterator)


def _blocking_stream_unary(
    channel,
    group,
    method,
    timeout,
    with_call,
    protocol_options,
    metadata,
    metadata_transformer,
    request_iterator,
    request_serializer,
    response_deserializer,
):
    try:
        multi_callable = channel.stream_unary(
            _common.fully_qualified_method(group, method),
            request_serializer=request_serializer,
            response_deserializer=response_deserializer,
        )
        effective_metadata = _effective_metadata(metadata, metadata_transformer)
        if with_call:
            response, call = multi_callable.with_call(
                request_iterator,
                timeout=timeout,
                metadata=_metadata.unbeta(effective_metadata),
                credentials=_credentials(protocol_options),
            )
            return response, _Rendezvous(None, None, call)
        else:
            return multi_callable(
                request_iterator,
                timeout=timeout,
                metadata=_metadata.unbeta(effective_metadata),
                credentials=_credentials(protocol_options),
            )
    except grpc.RpcError as rpc_error_call:
        raise _abortion_error(rpc_error_call)


def _future_stream_unary(
    channel,
    group,
    method,
    timeout,
    protocol_options,
    metadata,
    metadata_transformer,
    request_iterator,
    request_serializer,
    response_deserializer,
):
    multi_callable = channel.stream_unary(
        _common.fully_qualified_method(group, method),
        request_serializer=request_serializer,
        response_deserializer=response_deserializer,
    )
    effective_metadata = _effective_metadata(metadata, metadata_transformer)
    response_future = multi_callable.future(
        request_iterator,
        timeout=timeout,
        metadata=_metadata.unbeta(effective_metadata),
        credentials=_credentials(protocol_options),
    )
    return _Rendezvous(response_future, None, response_future)


def _stream_stream(
    channel,
    group,
    method,
    timeout,
    protocol_options,
    metadata,
    metadata_transformer,
    request_iterator,
    request_serializer,
    response_deserializer,
):
    multi_callable = channel.stream_stream(
        _common.fully_qualified_method(group, method),
        request_serializer=request_serializer,
        response_deserializer=response_deserializer,
    )
    effective_metadata = _effective_metadata(metadata, metadata_transformer)
    response_iterator = multi_callable(
        request_iterator,
        timeout=timeout,
        metadata=_metadata.unbeta(effective_metadata),
        credentials=_credentials(protocol_options),
    )
    return _Rendezvous(None, response_iterator, response_iterator)


class _UnaryUnaryMultiCallable(face.UnaryUnaryMultiCallable):
    def __init__(
        self,
        channel,
        group,
        method,
        metadata_transformer,
        request_serializer,
        response_deserializer,
    ):
        self._channel = channel
        self._group = group
        self._method = method
        self._metadata_transformer = metadata_transformer
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(
        self,
        request,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        return _blocking_unary_unary(
            self._channel,
            self._group,
            self._method,
            timeout,
            with_call,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            self._request_serializer,
            self._response_deserializer,
        )

    def future(self, request, timeout, metadata=None, protocol_options=None):
        return _future_unary_unary(
            self._channel,
            self._group,
            self._method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            self._request_serializer,
            self._response_deserializer,
        )

    def event(
        self,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()


class _UnaryStreamMultiCallable(face.UnaryStreamMultiCallable):
    def __init__(
        self,
        channel,
        group,
        method,
        metadata_transformer,
        request_serializer,
        response_deserializer,
    ):
        self._channel = channel
        self._group = group
        self._method = method
        self._metadata_transformer = metadata_transformer
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self, request, timeout, metadata=None, protocol_options=None):
        return _unary_stream(
            self._channel,
            self._group,
            self._method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            self._request_serializer,
            self._response_deserializer,
        )

    def event(
        self,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()


class _StreamUnaryMultiCallable(face.StreamUnaryMultiCallable):
    def __init__(
        self,
        channel,
        group,
        method,
        metadata_transformer,
        request_serializer,
        response_deserializer,
    ):
        self._channel = channel
        self._group = group
        self._method = method
        self._metadata_transformer = metadata_transformer
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(
        self,
        request_iterator,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        return _blocking_stream_unary(
            self._channel,
            self._group,
            self._method,
            timeout,
            with_call,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            self._request_serializer,
            self._response_deserializer,
        )

    def future(
        self, request_iterator, timeout, metadata=None, protocol_options=None
    ):
        return _future_stream_unary(
            self._channel,
            self._group,
            self._method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            self._request_serializer,
            self._response_deserializer,
        )

    def event(
        self,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()


class _StreamStreamMultiCallable(face.StreamStreamMultiCallable):
    def __init__(
        self,
        channel,
        group,
        method,
        metadata_transformer,
        request_serializer,
        response_deserializer,
    ):
        self._channel = channel
        self._group = group
        self._method = method
        self._metadata_transformer = metadata_transformer
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(
        self, request_iterator, timeout, metadata=None, protocol_options=None
    ):
        return _stream_stream(
            self._channel,
            self._group,
            self._method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            self._request_serializer,
            self._response_deserializer,
        )

    def event(
        self,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()


class _GenericStub(face.GenericStub):
    def __init__(
        self,
        channel,
        metadata_transformer,
        request_serializers,
        response_deserializers,
    ):
        self._channel = channel
        self._metadata_transformer = metadata_transformer
        self._request_serializers = request_serializers or {}
        self._response_deserializers = response_deserializers or {}

    def blocking_unary_unary(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        with_call=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _blocking_unary_unary(
            self._channel,
            group,
            method,
            timeout,
            with_call,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            request_serializer,
            response_deserializer,
        )

    def future_unary_unary(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _future_unary_unary(
            self._channel,
            group,
            method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            request_serializer,
            response_deserializer,
        )

    def inline_unary_stream(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _unary_stream(
            self._channel,
            group,
            method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request,
            request_serializer,
            response_deserializer,
        )

    def blocking_stream_unary(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        with_call=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _blocking_stream_unary(
            self._channel,
            group,
            method,
            timeout,
            with_call,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            request_serializer,
            response_deserializer,
        )

    def future_stream_unary(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _future_stream_unary(
            self._channel,
            group,
            method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            request_serializer,
            response_deserializer,
        )

    def inline_stream_stream(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _stream_stream(
            self._channel,
            group,
            method,
            timeout,
            protocol_options,
            metadata,
            self._metadata_transformer,
            request_iterator,
            request_serializer,
            response_deserializer,
        )

    def event_unary_unary(
        self,
        group,
        method,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()

    def event_unary_stream(
        self,
        group,
        method,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()

    def event_stream_unary(
        self,
        group,
        method,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()

    def event_stream_stream(
        self,
        group,
        method,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        raise NotImplementedError()

    def unary_unary(self, group, method):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _UnaryUnaryMultiCallable(
            self._channel,
            group,
            method,
            self._metadata_transformer,
            request_serializer,
            response_deserializer,
        )

    def unary_stream(self, group, method):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _UnaryStreamMultiCallable(
            self._channel,
            group,
            method,
            self._metadata_transformer,
            request_serializer,
            response_deserializer,
        )

    def stream_unary(self, group, method):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _StreamUnaryMultiCallable(
            self._channel,
            group,
            method,
            self._metadata_transformer,
            request_serializer,
            response_deserializer,
        )

    def stream_stream(self, group, method):
        request_serializer = self._request_serializers.get(
            (
                group,
                method,
            )
        )
        response_deserializer = self._response_deserializers.get(
            (
                group,
                method,
            )
        )
        return _StreamStreamMultiCallable(
            self._channel,
            group,
            method,
            self._metadata_transformer,
            request_serializer,
            response_deserializer,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _DynamicStub(face.DynamicStub):
    def __init__(self, backing_generic_stub, group, cardinalities):
        self._generic_stub = backing_generic_stub
        self._group = group
        self._cardinalities = cardinalities

    def __getattr__(self, attr):
        method_cardinality = self._cardinalities.get(attr)
        if method_cardinality is cardinality.Cardinality.UNARY_UNARY:
            return self._generic_stub.unary_unary(self._group, attr)
        elif method_cardinality is cardinality.Cardinality.UNARY_STREAM:
            return self._generic_stub.unary_stream(self._group, attr)
        elif method_cardinality is cardinality.Cardinality.STREAM_UNARY:
            return self._generic_stub.stream_unary(self._group, attr)
        elif method_cardinality is cardinality.Cardinality.STREAM_STREAM:
            return self._generic_stub.stream_stream(self._group, attr)
        else:
            raise AttributeError(
                '_DynamicStub object has no attribute "%s"!' % attr
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def generic_stub(
    channel,
    host,
    metadata_transformer,
    request_serializers,
    response_deserializers,
):
    return _GenericStub(
        channel,
        metadata_transformer,
        request_serializers,
        response_deserializers,
    )


def dynamic_stub(
    channel,
    service,
    cardinalities,
    host,
    metadata_transformer,
    request_serializers,
    response_deserializers,
):
    return _DynamicStub(
        _GenericStub(
            channel,
            metadata_transformer,
            request_serializers,
            response_deserializers,
        ),
        service,
        cardinalities,
    )

# === NexusCore/openenv\Lib\site-packages\fontTools\fontBuilder.py ===
__all__ = ["FontBuilder"]

"""
This module is *experimental*, meaning it still may evolve and change.

The `FontBuilder` class is a convenient helper to construct working TTF or
OTF fonts from scratch.

Note that the various setup methods cannot be called in arbitrary order,
due to various interdependencies between OpenType tables. Here is an order
that works:

    fb = FontBuilder(...)
    fb.setupGlyphOrder(...)
    fb.setupCharacterMap(...)
    fb.setupGlyf(...) --or-- fb.setupCFF(...)
    fb.setupHorizontalMetrics(...)
    fb.setupHorizontalHeader()
    fb.setupNameTable(...)
    fb.setupOS2()
    fb.addOpenTypeFeatures(...)
    fb.setupPost()
    fb.save(...)

Here is how to build a minimal TTF:

```python
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def drawTestGlyph(pen):
    pen.moveTo((100, 100))
    pen.lineTo((100, 1000))
    pen.qCurveTo((200, 900), (400, 900), (500, 1000))
    pen.lineTo((500, 100))
    pen.closePath()


fb = FontBuilder(1024, isTTF=True)
fb.setupGlyphOrder([".notdef", ".null", "space", "A", "a"])
fb.setupCharacterMap({32: "space", 65: "A", 97: "a"})
advanceWidths = {".notdef": 600, "space": 500, "A": 600, "a": 600, ".null": 0}

familyName = "HelloTestFont"
styleName = "TotallyNormal"
version = "0.1"

nameStrings = dict(
    familyName=dict(en=familyName, nl="HalloTestFont"),
    styleName=dict(en=styleName, nl="TotaalNormaal"),
    uniqueFontIdentifier="fontBuilder: " + familyName + "." + styleName,
    fullName=familyName + "-" + styleName,
    psName=familyName + "-" + styleName,
    version="Version " + version,
)

pen = TTGlyphPen(None)
drawTestGlyph(pen)
glyph = pen.glyph()
glyphs = {".notdef": glyph, "space": glyph, "A": glyph, "a": glyph, ".null": glyph}
fb.setupGlyf(glyphs)
metrics = {}
glyphTable = fb.font["glyf"]
for gn, advanceWidth in advanceWidths.items():
    metrics[gn] = (advanceWidth, glyphTable[gn].xMin)
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=824, descent=-200)
fb.setupNameTable(nameStrings)
fb.setupOS2(sTypoAscender=824, usWinAscent=824, usWinDescent=200)
fb.setupPost()
fb.save("test.ttf")
```

And here's how to build a minimal OTF:

```python
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen


def drawTestGlyph(pen):
    pen.moveTo((100, 100))
    pen.lineTo((100, 1000))
    pen.curveTo((200, 900), (400, 900), (500, 1000))
    pen.lineTo((500, 100))
    pen.closePath()


fb = FontBuilder(1024, isTTF=False)
fb.setupGlyphOrder([".notdef", ".null", "space", "A", "a"])
fb.setupCharacterMap({32: "space", 65: "A", 97: "a"})
advanceWidths = {".notdef": 600, "space": 500, "A": 600, "a": 600, ".null": 0}

familyName = "HelloTestFont"
styleName = "TotallyNormal"
version = "0.1"

nameStrings = dict(
    familyName=dict(en=familyName, nl="HalloTestFont"),
    styleName=dict(en=styleName, nl="TotaalNormaal"),
    uniqueFontIdentifier="fontBuilder: " + familyName + "." + styleName,
    fullName=familyName + "-" + styleName,
    psName=familyName + "-" + styleName,
    version="Version " + version,
)

pen = T2CharStringPen(600, None)
drawTestGlyph(pen)
charString = pen.getCharString()
charStrings = {
    ".notdef": charString,
    "space": charString,
    "A": charString,
    "a": charString,
    ".null": charString,
}
fb.setupCFF(nameStrings["psName"], {"FullName": nameStrings["psName"]}, charStrings, {})
lsb = {gn: cs.calcBounds(None)[0] for gn, cs in charStrings.items()}
metrics = {}
for gn, advanceWidth in advanceWidths.items():
    metrics[gn] = (advanceWidth, lsb[gn])
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=824, descent=200)
fb.setupNameTable(nameStrings)
fb.setupOS2(sTypoAscender=824, usWinAscent=824, usWinDescent=200)
fb.setupPost()
fb.save("test.otf")
```
"""

from .ttLib import TTFont, newTable
from .ttLib.tables._c_m_a_p import cmap_classes
from .ttLib.tables._g_l_y_f import flagCubic
from .ttLib.tables.O_S_2f_2 import Panose
from .misc.timeTools import timestampNow
import struct
from collections import OrderedDict


_headDefaults = dict(
    tableVersion=1.0,
    fontRevision=1.0,
    checkSumAdjustment=0,
    magicNumber=0x5F0F3CF5,
    flags=0x0003,
    unitsPerEm=1000,
    created=0,
    modified=0,
    xMin=0,
    yMin=0,
    xMax=0,
    yMax=0,
    macStyle=0,
    lowestRecPPEM=3,
    fontDirectionHint=2,
    indexToLocFormat=0,
    glyphDataFormat=0,
)

_maxpDefaultsTTF = dict(
    tableVersion=0x00010000,
    numGlyphs=0,
    maxPoints=0,
    maxContours=0,
    maxCompositePoints=0,
    maxCompositeContours=0,
    maxZones=2,
    maxTwilightPoints=0,
    maxStorage=0,
    maxFunctionDefs=0,
    maxInstructionDefs=0,
    maxStackElements=0,
    maxSizeOfInstructions=0,
    maxComponentElements=0,
    maxComponentDepth=0,
)
_maxpDefaultsOTF = dict(
    tableVersion=0x00005000,
    numGlyphs=0,
)

_postDefaults = dict(
    formatType=3.0,
    italicAngle=0,
    underlinePosition=0,
    underlineThickness=0,
    isFixedPitch=0,
    minMemType42=0,
    maxMemType42=0,
    minMemType1=0,
    maxMemType1=0,
)

_hheaDefaults = dict(
    tableVersion=0x00010000,
    ascent=0,
    descent=0,
    lineGap=0,
    advanceWidthMax=0,
    minLeftSideBearing=0,
    minRightSideBearing=0,
    xMaxExtent=0,
    caretSlopeRise=1,
    caretSlopeRun=0,
    caretOffset=0,
    reserved0=0,
    reserved1=0,
    reserved2=0,
    reserved3=0,
    metricDataFormat=0,
    numberOfHMetrics=0,
)

_vheaDefaults = dict(
    tableVersion=0x00010000,
    ascent=0,
    descent=0,
    lineGap=0,
    advanceHeightMax=0,
    minTopSideBearing=0,
    minBottomSideBearing=0,
    yMaxExtent=0,
    caretSlopeRise=0,
    caretSlopeRun=0,
    reserved0=0,
    reserved1=0,
    reserved2=0,
    reserved3=0,
    reserved4=0,
    metricDataFormat=0,
    numberOfVMetrics=0,
)

_nameIDs = dict(
    copyright=0,
    familyName=1,
    styleName=2,
    uniqueFontIdentifier=3,
    fullName=4,
    version=5,
    psName=6,
    trademark=7,
    manufacturer=8,
    designer=9,
    description=10,
    vendorURL=11,
    designerURL=12,
    licenseDescription=13,
    licenseInfoURL=14,
    # reserved = 15,
    typographicFamily=16,
    typographicSubfamily=17,
    compatibleFullName=18,
    sampleText=19,
    postScriptCIDFindfontName=20,
    wwsFamilyName=21,
    wwsSubfamilyName=22,
    lightBackgroundPalette=23,
    darkBackgroundPalette=24,
    variationsPostScriptNamePrefix=25,
)

# to insert in setupNameTable doc string:
# print("\n".join(("%s (nameID %s)" % (k, v)) for k, v in sorted(_nameIDs.items(), key=lambda x: x[1])))

_panoseDefaults = Panose()

_OS2Defaults = dict(
    version=3,
    xAvgCharWidth=0,
    usWeightClass=400,
    usWidthClass=5,
    fsType=0x0004,  # default: Preview & Print embedding
    ySubscriptXSize=0,
    ySubscriptYSize=0,
    ySubscriptXOffset=0,
    ySubscriptYOffset=0,
    ySuperscriptXSize=0,
    ySuperscriptYSize=0,
    ySuperscriptXOffset=0,
    ySuperscriptYOffset=0,
    yStrikeoutSize=0,
    yStrikeoutPosition=0,
    sFamilyClass=0,
    panose=_panoseDefaults,
    ulUnicodeRange1=0,
    ulUnicodeRange2=0,
    ulUnicodeRange3=0,
    ulUnicodeRange4=0,
    achVendID="????",
    fsSelection=0,
    usFirstCharIndex=0,
    usLastCharIndex=0,
    sTypoAscender=0,
    sTypoDescender=0,
    sTypoLineGap=0,
    usWinAscent=0,
    usWinDescent=0,
    ulCodePageRange1=0,
    ulCodePageRange2=0,
    sxHeight=0,
    sCapHeight=0,
    usDefaultChar=0,  # .notdef
    usBreakChar=32,  # space
    usMaxContext=0,
    usLowerOpticalPointSize=0,
    usUpperOpticalPointSize=0,
)


class FontBuilder(object):
    def __init__(self, unitsPerEm=None, font=None, isTTF=True, glyphDataFormat=0):
        """Initialize a FontBuilder instance.

        If the `font` argument is not given, a new `TTFont` will be
        constructed, and `unitsPerEm` must be given. If `isTTF` is True,
        the font will be a glyf-based TTF; if `isTTF` is False it will be
        a CFF-based OTF.

        The `glyphDataFormat` argument corresponds to the `head` table field
        that defines the format of the TrueType `glyf` table (default=0).
        TrueType glyphs historically can only contain quadratic splines and static
        components, but there's a proposal to add support for cubic Bezier curves as well
        as variable composites/components at
        https://github.com/harfbuzz/boring-expansion-spec/blob/main/glyf1.md
        You can experiment with the new features by setting `glyphDataFormat` to 1.
        A ValueError is raised if `glyphDataFormat` is left at 0 but glyphs are added
        that contain cubic splines or varcomposites. This is to prevent accidentally
        creating fonts that are incompatible with existing TrueType implementations.

        If `font` is given, it must be a `TTFont` instance and `unitsPerEm`
        must _not_ be given. The `isTTF` and `glyphDataFormat` arguments will be ignored.
        """
        if font is None:
            self.font = TTFont(recalcTimestamp=False)
            self.isTTF = isTTF
            now = timestampNow()
            assert unitsPerEm is not None
            self.setupHead(
                unitsPerEm=unitsPerEm,
                created=now,
                modified=now,
                glyphDataFormat=glyphDataFormat,
            )
            self.setupMaxp()
        else:
            assert unitsPerEm is None
            self.font = font
            self.isTTF = "glyf" in font

    def save(self, file):
        """Save the font. The 'file' argument can be either a pathname or a
        writable file object.
        """
        self.font.save(file)

    def _initTableWithValues(self, tableTag, defaults, values):
        table = self.font[tableTag] = newTable(tableTag)
        for k, v in defaults.items():
            setattr(table, k, v)
        for k, v in values.items():
            setattr(table, k, v)
        return table

    def _updateTableWithValues(self, tableTag, values):
        table = self.font[tableTag]
        for k, v in values.items():
            setattr(table, k, v)

    def setupHead(self, **values):
        """Create a new `head` table and initialize it with default values,
        which can be overridden by keyword arguments.
        """
        self._initTableWithValues("head", _headDefaults, values)

    def updateHead(self, **values):
        """Update the head table with the fields and values passed as
        keyword arguments.
        """
        self._updateTableWithValues("head", values)

    def setupGlyphOrder(self, glyphOrder):
        """Set the glyph order for the font."""
        self.font.setGlyphOrder(glyphOrder)

    def setupCharacterMap(self, cmapping, uvs=None, allowFallback=False):
        """Build the `cmap` table for the font. The `cmapping` argument should
        be a dict mapping unicode code points as integers to glyph names.

        The `uvs` argument, when passed, must be a list of tuples, describing
        Unicode Variation Sequences. These tuples have three elements:
            (unicodeValue, variationSelector, glyphName)
        `unicodeValue` and `variationSelector` are integer code points.
        `glyphName` may be None, to indicate this is the default variation.
        Text processors will then use the cmap to find the glyph name.
        Each Unicode Variation Sequence should be an officially supported
        sequence, but this is not policed.
        """
        subTables = []
        highestUnicode = max(cmapping) if cmapping else 0
        if highestUnicode > 0xFFFF:
            cmapping_3_1 = dict((k, v) for k, v in cmapping.items() if k < 0x10000)
            subTable_3_10 = buildCmapSubTable(cmapping, 12, 3, 10)
            subTables.append(subTable_3_10)
        else:
            cmapping_3_1 = cmapping
        format = 4
        subTable_3_1 = buildCmapSubTable(cmapping_3_1, format, 3, 1)
        try:
            subTable_3_1.compile(self.font)
        except struct.error:
            # format 4 overflowed, fall back to format 12
            if not allowFallback:
                raise ValueError(
                    "cmap format 4 subtable overflowed; sort glyph order by unicode to fix."
                )
            format = 12
            subTable_3_1 = buildCmapSubTable(cmapping_3_1, format, 3, 1)
        subTables.append(subTable_3_1)
        subTable_0_3 = buildCmapSubTable(cmapping_3_1, format, 0, 3)
        subTables.append(subTable_0_3)

        if uvs is not None:
            uvsDict = {}
            for unicodeValue, variationSelector, glyphName in uvs:
                if cmapping.get(unicodeValue) == glyphName:
                    # this is a default variation
                    glyphName = None
                if variationSelector not in uvsDict:
                    uvsDict[variationSelector] = []
                uvsDict[variationSelector].append((unicodeValue, glyphName))
            uvsSubTable = buildCmapSubTable({}, 14, 0, 5)
            uvsSubTable.uvsDict = uvsDict
            subTables.append(uvsSubTable)

        self.font["cmap"] = newTable("cmap")
        self.font["cmap"].tableVersion = 0
        self.font["cmap"].tables = subTables

    def setupNameTable(self, nameStrings, windows=True, mac=True):
        """Create the `name` table for the font. The `nameStrings` argument must
        be a dict, mapping nameIDs or descriptive names for the nameIDs to name
        record values. A value is either a string, or a dict, mapping language codes
        to strings, to allow localized name table entries.

        By default, both Windows (platformID=3) and Macintosh (platformID=1) name
        records are added, unless any of `windows` or `mac` arguments is False.

        The following descriptive names are available for nameIDs:

            copyright (nameID 0)
            familyName (nameID 1)
            styleName (nameID 2)
            uniqueFontIdentifier (nameID 3)
            fullName (nameID 4)
            version (nameID 5)
            psName (nameID 6)
            trademark (nameID 7)
            manufacturer (nameID 8)
            designer (nameID 9)
            description (nameID 10)
            vendorURL (nameID 11)
            designerURL (nameID 12)
            licenseDescription (nameID 13)
            licenseInfoURL (nameID 14)
            typographicFamily (nameID 16)
            typographicSubfamily (nameID 17)
            compatibleFullName (nameID 18)
            sampleText (nameID 19)
            postScriptCIDFindfontName (nameID 20)
            wwsFamilyName (nameID 21)
            wwsSubfamilyName (nameID 22)
            lightBackgroundPalette (nameID 23)
            darkBackgroundPalette (nameID 24)
            variationsPostScriptNamePrefix (nameID 25)
        """
        nameTable = self.font["name"] = newTable("name")
        nameTable.names = []

        for nameName, nameValue in nameStrings.items():
            if isinstance(nameName, int):
                nameID = nameName
            else:
                nameID = _nameIDs[nameName]
            if isinstance(nameValue, str):
                nameValue = dict(en=nameValue)
            nameTable.addMultilingualName(
                nameValue, ttFont=self.font, nameID=nameID, windows=windows, mac=mac
            )

    def setupOS2(self, **values):
        """Create a new `OS/2` table and initialize it with default values,
        which can be overridden by keyword arguments.
        """
        self._initTableWithValues("OS/2", _OS2Defaults, values)
        if "xAvgCharWidth" not in values:
            assert (
                "hmtx" in self.font
            ), "the 'hmtx' table must be setup before the 'OS/2' table"
            self.font["OS/2"].recalcAvgCharWidth(self.font)
        if not (
            "ulUnicodeRange1" in values
            or "ulUnicodeRange2" in values
            or "ulUnicodeRange3" in values
            or "ulUnicodeRange3" in values
        ):
            assert (
                "cmap" in self.font
            ), "the 'cmap' table must be setup before the 'OS/2' table"
            self.font["OS/2"].recalcUnicodeRanges(self.font)

    def setupCFF(self, psName, fontInfo, charStringsDict, privateDict):
        from .cffLib import (
            CFFFontSet,
            TopDictIndex,
            TopDict,
            CharStrings,
            GlobalSubrsIndex,
            PrivateDict,
        )

        assert not self.isTTF
        self.font.sfntVersion = "OTTO"
        fontSet = CFFFontSet()
        fontSet.major = 1
        fontSet.minor = 0
        fontSet.otFont = self.font
        fontSet.fontNames = [psName]
        fontSet.topDictIndex = TopDictIndex()

        globalSubrs = GlobalSubrsIndex()
        fontSet.GlobalSubrs = globalSubrs
        private = PrivateDict()
        for key, value in privateDict.items():
            setattr(private, key, value)
        fdSelect = None
        fdArray = None

        topDict = TopDict()
        topDict.charset = self.font.getGlyphOrder()
        topDict.Private = private
        topDict.GlobalSubrs = fontSet.GlobalSubrs
        for key, value in fontInfo.items():
            setattr(topDict, key, value)
        if "FontMatrix" not in fontInfo:
            scale = 1 / self.font["head"].unitsPerEm
            topDict.FontMatrix = [scale, 0, 0, scale, 0, 0]

        charStrings = CharStrings(
            None, topDict.charset, globalSubrs, private, fdSelect, fdArray
        )
        for glyphName, charString in charStringsDict.items():
            charString.private = private
            charString.globalSubrs = globalSubrs
            charStrings[glyphName] = charString
        topDict.CharStrings = charStrings

        fontSet.topDictIndex.append(topDict)

        self.font["CFF "] = newTable("CFF ")
        self.font["CFF "].cff = fontSet

    def setupCFF2(self, charStringsDict, fdArrayList=None, regions=None):
        from .cffLib import (
            CFFFontSet,
            TopDictIndex,
            TopDict,
            CharStrings,
            GlobalSubrsIndex,
            PrivateDict,
            FDArrayIndex,
            FontDict,
        )

        assert not self.isTTF
        self.font.sfntVersion = "OTTO"
        fontSet = CFFFontSet()
        fontSet.major = 2
        fontSet.minor = 0

        cff2GetGlyphOrder = self.font.getGlyphOrder
        fontSet.topDictIndex = TopDictIndex(None, cff2GetGlyphOrder, None)

        globalSubrs = GlobalSubrsIndex()
        fontSet.GlobalSubrs = globalSubrs

        if fdArrayList is None:
            fdArrayList = [{}]
        fdSelect = None
        fdArray = FDArrayIndex()
        fdArray.strings = None
        fdArray.GlobalSubrs = globalSubrs
        for privateDict in fdArrayList:
            fontDict = FontDict()
            fontDict.setCFF2(True)
            private = PrivateDict()
            for key, value in privateDict.items():
                setattr(private, key, value)
            fontDict.Private = private
            fdArray.append(fontDict)

        topDict = TopDict()
        topDict.cff2GetGlyphOrder = cff2GetGlyphOrder
        topDict.FDArray = fdArray
        scale = 1 / self.font["head"].unitsPerEm
        topDict.FontMatrix = [scale, 0, 0, scale, 0, 0]

        private = fdArray[0].Private
        charStrings = CharStrings(None, None, globalSubrs, private, fdSelect, fdArray)
        for glyphName, charString in charStringsDict.items():
            charString.private = private
            charString.globalSubrs = globalSubrs
            charStrings[glyphName] = charString
        topDict.CharStrings = charStrings

        fontSet.topDictIndex.append(topDict)

        self.font["CFF2"] = newTable("CFF2")
        self.font["CFF2"].cff = fontSet

        if regions:
            self.setupCFF2Regions(regions)

    def setupCFF2Regions(self, regions):
        from .varLib.builder import buildVarRegionList, buildVarData, buildVarStore
        from .cffLib import VarStoreData

        assert "fvar" in self.font, "fvar must to be set up first"
        assert "CFF2" in self.font, "CFF2 must to be set up first"
        axisTags = [a.axisTag for a in self.font["fvar"].axes]
        varRegionList = buildVarRegionList(regions, axisTags)
        varData = buildVarData(list(range(len(regions))), None, optimize=False)
        varStore = buildVarStore(varRegionList, [varData])
        vstore = VarStoreData(otVarStore=varStore)
        topDict = self.font["CFF2"].cff.topDictIndex[0]
        topDict.VarStore = vstore
        for fontDict in topDict.FDArray:
            fontDict.Private.vstore = vstore

    def setupGlyf(self, glyphs, calcGlyphBounds=True, validateGlyphFormat=True):
        """Create the `glyf` table from a dict, that maps glyph names
        to `fontTools.ttLib.tables._g_l_y_f.Glyph` objects, for example
        as made by `fontTools.pens.ttGlyphPen.TTGlyphPen`.

        If `calcGlyphBounds` is True, the bounds of all glyphs will be
        calculated. Only pass False if your glyph objects already have
        their bounding box values set.

        If `validateGlyphFormat` is True, raise ValueError if any of the glyphs contains
        cubic curves or is a variable composite but head.glyphDataFormat=0.
        Set it to False to skip the check if you know in advance all the glyphs are
        compatible with the specified glyphDataFormat.
        """
        assert self.isTTF

        if validateGlyphFormat and self.font["head"].glyphDataFormat == 0:
            for name, g in glyphs.items():
                if g.numberOfContours > 0 and any(f & flagCubic for f in g.flags):
                    raise ValueError(
                        f"Glyph {name!r} has cubic Bezier outlines, but glyphDataFormat=0; "
                        "either convert to quadratics with cu2qu or set glyphDataFormat=1."
                    )

        self.font["loca"] = newTable("loca")
        self.font["glyf"] = newTable("glyf")
        self.font["glyf"].glyphs = glyphs
        if hasattr(self.font, "glyphOrder"):
            self.font["glyf"].glyphOrder = self.font.glyphOrder
        if calcGlyphBounds:
            self.calcGlyphBounds()

    def setupFvar(self, axes, instances):
        """Adds an font variations table to the font.

        Args:
            axes (list): See below.
            instances (list): See below.

        ``axes`` should be a list of axes, with each axis either supplied as
        a py:class:`.designspaceLib.AxisDescriptor` object, or a tuple in the
        format ```tupletag, minValue, defaultValue, maxValue, name``.
        The ``name`` is either a string, or a dict, mapping language codes
        to strings, to allow localized name table entries.

        ```instances`` should be a list of instances, with each instance either
        supplied as a py:class:`.designspaceLib.InstanceDescriptor` object, or a
        dict with keys ``location`` (mapping of axis tags to float values),
        ``stylename`` and (optionally) ``postscriptfontname``.
        The ``stylename`` is either a string, or a dict, mapping language codes
        to strings, to allow localized name table entries.
        """

        addFvar(self.font, axes, instances)

    def setupAvar(self, axes, mappings=None):
        """Adds an axis variations table to the font.

        Args:
            axes (list): A list of py:class:`.designspaceLib.AxisDescriptor` objects.
        """
        from .varLib import _add_avar

        if "fvar" not in self.font:
            raise KeyError("'fvar' table is missing; can't add 'avar'.")

        axisTags = [axis.axisTag for axis in self.font["fvar"].axes]
        axes = OrderedDict(enumerate(axes))  # Only values are used
        _add_avar(self.font, axes, mappings, axisTags)

    def setupGvar(self, variations):
        gvar = self.font["gvar"] = newTable("gvar")
        gvar.version = 1
        gvar.reserved = 0
        gvar.variations = variations

    def setupGVAR(self, variations):
        gvar = self.font["GVAR"] = newTable("GVAR")
        gvar.version = 1
        gvar.reserved = 0
        gvar.variations = variations

    def calcGlyphBounds(self):
        """Calculate the bounding boxes of all glyphs in the `glyf` table.
        This is usually not called explicitly by client code.
        """
        glyphTable = self.font["glyf"]
        for glyph in glyphTable.glyphs.values():
            glyph.recalcBounds(glyphTable)

    def setupHorizontalMetrics(self, metrics):
        """Create a new `hmtx` table, for horizontal metrics.

        The `metrics` argument must be a dict, mapping glyph names to
        `(width, leftSidebearing)` tuples.
        """
        self.setupMetrics("hmtx", metrics)

    def setupVerticalMetrics(self, metrics):
        """Create a new `vmtx` table, for horizontal metrics.

        The `metrics` argument must be a dict, mapping glyph names to
        `(height, topSidebearing)` tuples.
        """
        self.setupMetrics("vmtx", metrics)

    def setupMetrics(self, tableTag, metrics):
        """See `setupHorizontalMetrics()` and `setupVerticalMetrics()`."""
        assert tableTag in ("hmtx", "vmtx")
        mtxTable = self.font[tableTag] = newTable(tableTag)
        roundedMetrics = {}
        for gn in metrics:
            w, lsb = metrics[gn]
            roundedMetrics[gn] = int(round(w)), int(round(lsb))
        mtxTable.metrics = roundedMetrics

    def setupHorizontalHeader(self, **values):
        """Create a new `hhea` table initialize it with default values,
        which can be overridden by keyword arguments.
        """
        self._initTableWithValues("hhea", _hheaDefaults, values)

    def setupVerticalHeader(self, **values):
        """Create a new `vhea` table initialize it with default values,
        which can be overridden by keyword arguments.
        """
        self._initTableWithValues("vhea", _vheaDefaults, values)

    def setupVerticalOrigins(self, verticalOrigins, defaultVerticalOrigin=None):
        """Create a new `VORG` table. The `verticalOrigins` argument must be
        a dict, mapping glyph names to vertical origin values.

        The `defaultVerticalOrigin` argument should be the most common vertical
        origin value. If omitted, this value will be derived from the actual
        values in the `verticalOrigins` argument.
        """
        if defaultVerticalOrigin is None:
            # find the most frequent vorg value
            bag = {}
            for gn in verticalOrigins:
                vorg = verticalOrigins[gn]
                if vorg not in bag:
                    bag[vorg] = 1
                else:
                    bag[vorg] += 1
            defaultVerticalOrigin = sorted(
                bag, key=lambda vorg: bag[vorg], reverse=True
            )[0]
        self._initTableWithValues(
            "VORG",
            {},
            dict(VOriginRecords={}, defaultVertOriginY=defaultVerticalOrigin),
        )
        vorgTable = self.font["VORG"]
        vorgTable.majorVersion = 1
        vorgTable.minorVersion = 0
        for gn in verticalOrigins:
            vorgTable[gn] = verticalOrigins[gn]

    def setupPost(self, keepGlyphNames=True, **values):
        """Create a new `post` table and initialize it with default values,
        which can be overridden by keyword arguments.
        """
        isCFF2 = "CFF2" in self.font
        postTable = self._initTableWithValues("post", _postDefaults, values)
        if (self.isTTF or isCFF2) and keepGlyphNames:
            postTable.formatType = 2.0
            postTable.extraNames = []
            postTable.mapping = {}
        else:
            postTable.formatType = 3.0

    def setupMaxp(self):
        """Create a new `maxp` table. This is called implicitly by FontBuilder
        itself and is usually not called by client code.
        """
        if self.isTTF:
            defaults = _maxpDefaultsTTF
        else:
            defaults = _maxpDefaultsOTF
        self._initTableWithValues("maxp", defaults, {})

    def setupDummyDSIG(self):
        """This adds an empty DSIG table to the font to make some MS applications
        happy. This does not properly sign the font.
        """
        values = dict(
            ulVersion=1,
            usFlag=0,
            usNumSigs=0,
            signatureRecords=[],
        )
        self._initTableWithValues("DSIG", {}, values)

    def addOpenTypeFeatures(self, features, filename=None, tables=None, debug=False):
        """Add OpenType features to the font from a string containing
        Feature File syntax.

        The `filename` argument is used in error messages and to determine
        where to look for "include" files.

        The optional `tables` argument can be a list of OTL tables tags to
        build, allowing the caller to only build selected OTL tables. See
        `fontTools.feaLib` for details.

        The optional `debug` argument controls whether to add source debugging
        information to the font in the `Debg` table.
        """
        from .feaLib.builder import addOpenTypeFeaturesFromString

        addOpenTypeFeaturesFromString(
            self.font, features, filename=filename, tables=tables, debug=debug
        )

    def addFeatureVariations(self, conditionalSubstitutions, featureTag="rvrn"):
        """Add conditional substitutions to a Variable Font.

        See `fontTools.varLib.featureVars.addFeatureVariations`.
        """
        from .varLib import featureVars

        if "fvar" not in self.font:
            raise KeyError("'fvar' table is missing; can't add FeatureVariations.")

        featureVars.addFeatureVariations(
            self.font, conditionalSubstitutions, featureTag=featureTag
        )

    def setupCOLR(
        self,
        colorLayers,
        version=None,
        varStore=None,
        varIndexMap=None,
        clipBoxes=None,
        allowLayerReuse=True,
    ):
        """Build new COLR table using color layers dictionary.

        Cf. `fontTools.colorLib.builder.buildCOLR`.
        """
        from fontTools.colorLib.builder import buildCOLR

        glyphMap = self.font.getReverseGlyphMap()
        self.font["COLR"] = buildCOLR(
            colorLayers,
            version=version,
            glyphMap=glyphMap,
            varStore=varStore,
            varIndexMap=varIndexMap,
            clipBoxes=clipBoxes,
            allowLayerReuse=allowLayerReuse,
        )

    def setupCPAL(
        self,
        palettes,
        paletteTypes=None,
        paletteLabels=None,
        paletteEntryLabels=None,
    ):
        """Build new CPAL table using list of palettes.

        Optionally build CPAL v1 table using paletteTypes, paletteLabels and
        paletteEntryLabels.

        Cf. `fontTools.colorLib.builder.buildCPAL`.
        """
        from fontTools.colorLib.builder import buildCPAL

        self.font["CPAL"] = buildCPAL(
            palettes,
            paletteTypes=paletteTypes,
            paletteLabels=paletteLabels,
            paletteEntryLabels=paletteEntryLabels,
            nameTable=self.font.get("name"),
        )

    def setupStat(self, axes, locations=None, elidedFallbackName=2):
        """Build a new 'STAT' table.

        See `fontTools.otlLib.builder.buildStatTable` for details about
        the arguments.
        """
        from .otlLib.builder import buildStatTable

        assert "name" in self.font, "name must to be set up first"

        buildStatTable(
            self.font,
            axes,
            locations,
            elidedFallbackName,
            macNames=any(nr.platformID == 1 for nr in self.font["name"].names),
        )


def buildCmapSubTable(cmapping, format, platformID, platEncID):
    subTable = cmap_classes[format](format)
    subTable.cmap = cmapping
    subTable.platformID = platformID
    subTable.platEncID = platEncID
    subTable.language = 0
    return subTable


def addFvar(font, axes, instances):
    from .ttLib.tables._f_v_a_r import Axis, NamedInstance

    assert axes

    fvar = newTable("fvar")
    nameTable = font["name"]

    # if there are not currently any mac names don't add them here, that's inconsistent
    # https://github.com/fonttools/fonttools/issues/683
    macNames = any(nr.platformID == 1 for nr in getattr(nameTable, "names", ()))

    # we have all the best ways to express mac names
    platforms = ((3, 1, 0x409),)
    if macNames:
        platforms = ((1, 0, 0),) + platforms

    for axis_def in axes:
        axis = Axis()

        if isinstance(axis_def, tuple):
            (
                axis.axisTag,
                axis.minValue,
                axis.defaultValue,
                axis.maxValue,
                name,
            ) = axis_def
        else:
            (axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue, name) = (
                axis_def.tag,
                axis_def.minimum,
                axis_def.default,
                axis_def.maximum,
                axis_def.name,
            )
            if axis_def.hidden:
                axis.flags = 0x0001  # HIDDEN_AXIS

        if isinstance(name, str):
            name = dict(en=name)

        axis.axisNameID = nameTable.addMultilingualName(name, ttFont=font, mac=macNames)
        fvar.axes.append(axis)

    for instance in instances:
        if isinstance(instance, dict):
            coordinates = instance["location"]
            name = instance["stylename"]
            psname = instance.get("postscriptfontname")
        else:
            coordinates = instance.location
            name = instance.localisedStyleName or instance.styleName
            psname = instance.postScriptFontName

        if isinstance(name, str):
            name = dict(en=name)

        inst = NamedInstance()
        inst.subfamilyNameID = nameTable.addMultilingualName(
            name, ttFont=font, mac=macNames
        )
        if psname is not None:
            inst.postscriptNameID = nameTable.addName(psname, platforms=platforms)
        inst.coordinates = coordinates
        fvar.instances.append(inst)

    font["fvar"] = fvar

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\assistants.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union, Iterable, Optional
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...pagination import SyncCursorPage, AsyncCursorPage
from ...types.beta import (
    assistant_list_params,
    assistant_create_params,
    assistant_update_params,
)
from ..._base_client import AsyncPaginator, make_request_options
from ...types.beta.assistant import Assistant
from ...types.shared.chat_model import ChatModel
from ...types.beta.assistant_deleted import AssistantDeleted
from ...types.shared_params.metadata import Metadata
from ...types.shared.reasoning_effort import ReasoningEffort
from ...types.beta.assistant_tool_param import AssistantToolParam
from ...types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = ["Assistants", "AsyncAssistants"]


class Assistants(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AssistantsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AssistantsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AssistantsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AssistantsWithStreamingResponse(self)

    def create(
        self,
        *,
        model: Union[str, ChatModel],
        description: Optional[str] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[assistant_create_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Iterable[AssistantToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """
        Create an assistant with a model and instructions.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          description: The description of the assistant. The maximum length is 512 characters.

          instructions: The system instructions that the assistant uses. The maximum length is 256,000
              characters.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the assistant. The maximum length is 256 characters.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: A list of tool enabled on the assistant. There can be a maximum of 128 tools per
              assistant. Tools can be of types `code_interpreter`, `file_search`, or
              `function`.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/assistants",
            body=maybe_transform(
                {
                    "model": model,
                    "description": description,
                    "instructions": instructions,
                    "metadata": metadata,
                    "name": name,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                },
                assistant_create_params.AssistantCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    def retrieve(
        self,
        assistant_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """
        Retrieves an assistant.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/assistants/{assistant_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    def update(
        self,
        assistant_id: str,
        *,
        description: Optional[str] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[
            str,
            Literal[
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4.1-nano",
                "gpt-4.1-2025-04-14",
                "gpt-4.1-mini-2025-04-14",
                "gpt-4.1-nano-2025-04-14",
                "o3-mini",
                "o3-mini-2025-01-31",
                "o1",
                "o1-2024-12-17",
                "gpt-4o",
                "gpt-4o-2024-11-20",
                "gpt-4o-2024-08-06",
                "gpt-4o-2024-05-13",
                "gpt-4o-mini",
                "gpt-4o-mini-2024-07-18",
                "gpt-4.5-preview",
                "gpt-4.5-preview-2025-02-27",
                "gpt-4-turbo",
                "gpt-4-turbo-2024-04-09",
                "gpt-4-0125-preview",
                "gpt-4-turbo-preview",
                "gpt-4-1106-preview",
                "gpt-4-vision-preview",
                "gpt-4",
                "gpt-4-0314",
                "gpt-4-0613",
                "gpt-4-32k",
                "gpt-4-32k-0314",
                "gpt-4-32k-0613",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-1106",
                "gpt-3.5-turbo-0125",
                "gpt-3.5-turbo-16k-0613",
            ],
        ]
        | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[assistant_update_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Iterable[AssistantToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """Modifies an assistant.

        Args:
          description: The description of the assistant.

        The maximum length is 512 characters.

          instructions: The system instructions that the assistant uses. The maximum length is 256,000
              characters.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          name: The name of the assistant. The maximum length is 256 characters.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: A list of tool enabled on the assistant. There can be a maximum of 128 tools per
              assistant. Tools can be of types `code_interpreter`, `file_search`, or
              `function`.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/assistants/{assistant_id}",
            body=maybe_transform(
                {
                    "description": description,
                    "instructions": instructions,
                    "metadata": metadata,
                    "model": model,
                    "name": name,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                },
                assistant_update_params.AssistantUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[Assistant]:
        """Returns a list of assistants.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            "/assistants",
            page=SyncCursorPage[Assistant],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    assistant_list_params.AssistantListParams,
                ),
            ),
            model=Assistant,
        )

    def delete(
        self,
        assistant_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantDeleted:
        """
        Delete an assistant.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._delete(
            f"/assistants/{assistant_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=AssistantDeleted,
        )


class AsyncAssistants(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncAssistantsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncAssistantsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncAssistantsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncAssistantsWithStreamingResponse(self)

    async def create(
        self,
        *,
        model: Union[str, ChatModel],
        description: Optional[str] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[assistant_create_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Iterable[AssistantToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """
        Create an assistant with a model and instructions.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          description: The description of the assistant. The maximum length is 512 characters.

          instructions: The system instructions that the assistant uses. The maximum length is 256,000
              characters.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the assistant. The maximum length is 256 characters.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: A list of tool enabled on the assistant. There can be a maximum of 128 tools per
              assistant. Tools can be of types `code_interpreter`, `file_search`, or
              `function`.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/assistants",
            body=await async_maybe_transform(
                {
                    "model": model,
                    "description": description,
                    "instructions": instructions,
                    "metadata": metadata,
                    "name": name,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                },
                assistant_create_params.AssistantCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    async def retrieve(
        self,
        assistant_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """
        Retrieves an assistant.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/assistants/{assistant_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    async def update(
        self,
        assistant_id: str,
        *,
        description: Optional[str] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[
            str,
            Literal[
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4.1-nano",
                "gpt-4.1-2025-04-14",
                "gpt-4.1-mini-2025-04-14",
                "gpt-4.1-nano-2025-04-14",
                "o3-mini",
                "o3-mini-2025-01-31",
                "o1",
                "o1-2024-12-17",
                "gpt-4o",
                "gpt-4o-2024-11-20",
                "gpt-4o-2024-08-06",
                "gpt-4o-2024-05-13",
                "gpt-4o-mini",
                "gpt-4o-mini-2024-07-18",
                "gpt-4.5-preview",
                "gpt-4.5-preview-2025-02-27",
                "gpt-4-turbo",
                "gpt-4-turbo-2024-04-09",
                "gpt-4-0125-preview",
                "gpt-4-turbo-preview",
                "gpt-4-1106-preview",
                "gpt-4-vision-preview",
                "gpt-4",
                "gpt-4-0314",
                "gpt-4-0613",
                "gpt-4-32k",
                "gpt-4-32k-0314",
                "gpt-4-32k-0613",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-1106",
                "gpt-3.5-turbo-0125",
                "gpt-3.5-turbo-16k-0613",
            ],
        ]
        | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[assistant_update_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Iterable[AssistantToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Assistant:
        """Modifies an assistant.

        Args:
          description: The description of the assistant.

        The maximum length is 512 characters.

          instructions: The system instructions that the assistant uses. The maximum length is 256,000
              characters.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          name: The name of the assistant. The maximum length is 256 characters.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: A list of tool enabled on the assistant. There can be a maximum of 128 tools per
              assistant. Tools can be of types `code_interpreter`, `file_search`, or
              `function`.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/assistants/{assistant_id}",
            body=await async_maybe_transform(
                {
                    "description": description,
                    "instructions": instructions,
                    "metadata": metadata,
                    "model": model,
                    "name": name,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                },
                assistant_update_params.AssistantUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Assistant,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Assistant, AsyncCursorPage[Assistant]]:
        """Returns a list of assistants.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            "/assistants",
            page=AsyncCursorPage[Assistant],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    assistant_list_params.AssistantListParams,
                ),
            ),
            model=Assistant,
        )

    async def delete(
        self,
        assistant_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantDeleted:
        """
        Delete an assistant.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not assistant_id:
            raise ValueError(f"Expected a non-empty value for `assistant_id` but received {assistant_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._delete(
            f"/assistants/{assistant_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=AssistantDeleted,
        )


class AssistantsWithRawResponse:
    def __init__(self, assistants: Assistants) -> None:
        self._assistants = assistants

        self.create = _legacy_response.to_raw_response_wrapper(
            assistants.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            assistants.retrieve,
        )
        self.update = _legacy_response.to_raw_response_wrapper(
            assistants.update,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            assistants.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            assistants.delete,
        )


class AsyncAssistantsWithRawResponse:
    def __init__(self, assistants: AsyncAssistants) -> None:
        self._assistants = assistants

        self.create = _legacy_response.async_to_raw_response_wrapper(
            assistants.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            assistants.retrieve,
        )
        self.update = _legacy_response.async_to_raw_response_wrapper(
            assistants.update,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            assistants.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            assistants.delete,
        )


class AssistantsWithStreamingResponse:
    def __init__(self, assistants: Assistants) -> None:
        self._assistants = assistants

        self.create = to_streamed_response_wrapper(
            assistants.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            assistants.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            assistants.update,
        )
        self.list = to_streamed_response_wrapper(
            assistants.list,
        )
        self.delete = to_streamed_response_wrapper(
            assistants.delete,
        )


class AsyncAssistantsWithStreamingResponse:
    def __init__(self, assistants: AsyncAssistants) -> None:
        self._assistants = assistants

        self.create = async_to_streamed_response_wrapper(
            assistants.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            assistants.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            assistants.update,
        )
        self.list = async_to_streamed_response_wrapper(
            assistants.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            assistants.delete,
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import discuss_service, safety

from .transports.base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .transports.grpc import DiscussServiceGrpcTransport
from .transports.grpc_asyncio import DiscussServiceGrpcAsyncIOTransport
from .transports.rest import DiscussServiceRestTransport


class DiscussServiceClientMeta(type):
    """Metaclass for the DiscussService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[DiscussServiceTransport]]
    _transport_registry["grpc"] = DiscussServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = DiscussServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = DiscussServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[DiscussServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class DiscussServiceClient(metaclass=DiscussServiceClientMeta):
    """An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            DiscussServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            DiscussServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> DiscussServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            DiscussServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = DiscussServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = DiscussServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = DiscussServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = DiscussServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = DiscussServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or DiscussServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, DiscussServiceTransport, Callable[..., DiscussServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the discuss service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,DiscussServiceTransport,Callable[..., DiscussServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the DiscussServiceTransport constructor.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = DiscussServiceClient._read_environment_variables()
        self._client_cert_source = DiscussServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = DiscussServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, DiscussServiceTransport)
        if transport_provided:
            # transport is a DiscussServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(DiscussServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or DiscussServiceClient._get_api_endpoint(
                self._client_options.api_endpoint,
                self._client_cert_source,
                self._universe_domain,
                self._use_mtls_endpoint,
            )
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[DiscussServiceTransport], Callable[..., DiscussServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., DiscussServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def generate_message(
        self,
        request: Optional[Union[discuss_service.GenerateMessageRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.GenerateMessageResponse:
        r"""Generates a response from the model given an input
        ``MessagePrompt``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_generate_message():
                # Create a client
                client = generativelanguage_v1beta.DiscussServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta.GenerateMessageRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.generate_message(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GenerateMessageRequest, dict]):
                The request object. Request to generate a message
                response from the model.
            model (str):
                Required. The name of the model to use.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta.types.MessagePrompt):
                Required. The structured textual
                input given to the model as a prompt.
                Given a
                prompt, the model will return what it
                predicts is the next message in the
                discussion.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (float):
                Optional. Controls the randomness of the output.

                Values can range over ``[0.0,1.0]``, inclusive. A value
                closer to ``1.0`` will produce responses that are more
                varied, while a value closer to ``0.0`` will typically
                result in less surprising responses from the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (int):
                Optional. The number of generated response messages to
                return.

                This value must be between ``[1, 8]``, inclusive. If
                unset, this will default to ``1``.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (float):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Nucleus sampling considers the smallest set of tokens
                whose probability sum is at least ``top_p``.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (int):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateMessageResponse:
                The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [model, prompt, temperature, candidate_count, top_p, top_k]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.GenerateMessageRequest):
            request = discuss_service.GenerateMessageRequest(request)
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
            if top_p is not None:
                request.top_p = top_p
            if top_k is not None:
                request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_message]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def count_message_tokens(
        self,
        request: Optional[
            Union[discuss_service.CountMessageTokensRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.CountMessageTokensResponse:
        r"""Runs a model's tokenizer on a string and returns the
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

            def sample_count_message_tokens():
                # Create a client
                client = generativelanguage_v1beta.DiscussServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta.CountMessageTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.count_message_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CountMessageTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta.types.MessagePrompt):
                Required. The prompt, whose token
                count is to be returned.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountMessageTokensResponse:
                A response from CountMessageTokens.

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
        if not isinstance(request, discuss_service.CountMessageTokensRequest):
            request = discuss_service.CountMessageTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_message_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "DiscussServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("DiscussServiceClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import discuss_service, safety

from .transports.base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .transports.grpc import DiscussServiceGrpcTransport
from .transports.grpc_asyncio import DiscussServiceGrpcAsyncIOTransport
from .transports.rest import DiscussServiceRestTransport


class DiscussServiceClientMeta(type):
    """Metaclass for the DiscussService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[DiscussServiceTransport]]
    _transport_registry["grpc"] = DiscussServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = DiscussServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = DiscussServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[DiscussServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class DiscussServiceClient(metaclass=DiscussServiceClientMeta):
    """An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            DiscussServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            DiscussServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> DiscussServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            DiscussServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = DiscussServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = DiscussServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = DiscussServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = DiscussServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = DiscussServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or DiscussServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, DiscussServiceTransport, Callable[..., DiscussServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the discuss service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,DiscussServiceTransport,Callable[..., DiscussServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the DiscussServiceTransport constructor.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = DiscussServiceClient._read_environment_variables()
        self._client_cert_source = DiscussServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = DiscussServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, DiscussServiceTransport)
        if transport_provided:
            # transport is a DiscussServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(DiscussServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or DiscussServiceClient._get_api_endpoint(
                self._client_options.api_endpoint,
                self._client_cert_source,
                self._universe_domain,
                self._use_mtls_endpoint,
            )
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[DiscussServiceTransport], Callable[..., DiscussServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., DiscussServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def generate_message(
        self,
        request: Optional[Union[discuss_service.GenerateMessageRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.GenerateMessageResponse:
        r"""Generates a response from the model given an input
        ``MessagePrompt``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_generate_message():
                # Create a client
                client = generativelanguage_v1beta3.DiscussServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta3.GenerateMessageRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.generate_message(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.GenerateMessageRequest, dict]):
                The request object. Request to generate a message
                response from the model.
            model (str):
                Required. The name of the model to use.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta3.types.MessagePrompt):
                Required. The structured textual
                input given to the model as a prompt.
                Given a
                prompt, the model will return what it
                predicts is the next message in the
                discussion.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (float):
                Optional. Controls the randomness of the output.

                Values can range over ``[0.0,1.0]``, inclusive. A value
                closer to ``1.0`` will produce responses that are more
                varied, while a value closer to ``0.0`` will typically
                result in less surprising responses from the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (int):
                Optional. The number of generated response messages to
                return.

                This value must be between ``[1, 8]``, inclusive. If
                unset, this will default to ``1``.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (float):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Nucleus sampling considers the smallest set of tokens
                whose probability sum is at least ``top_p``.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (int):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.GenerateMessageResponse:
                The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [model, prompt, temperature, candidate_count, top_p, top_k]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.GenerateMessageRequest):
            request = discuss_service.GenerateMessageRequest(request)
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
            if top_p is not None:
                request.top_p = top_p
            if top_k is not None:
                request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_message]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def count_message_tokens(
        self,
        request: Optional[
            Union[discuss_service.CountMessageTokensRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.CountMessageTokensResponse:
        r"""Runs a model's tokenizer on a string and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_count_message_tokens():
                # Create a client
                client = generativelanguage_v1beta3.DiscussServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta3.CountMessageTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.count_message_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.CountMessageTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta3.types.MessagePrompt):
                Required. The prompt, whose token
                count is to be returned.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.CountMessageTokensResponse:
                A response from CountMessageTokens.

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
        if not isinstance(request, discuss_service.CountMessageTokensRequest):
            request = discuss_service.CountMessageTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_message_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "DiscussServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("DiscussServiceClient",)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\specifiers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from packaging.version import Version
"""

import abc
import itertools
import re
from typing import Callable, Iterable, Iterator, List, Optional, Tuple, TypeVar, Union

from .utils import canonicalize_version
from .version import Version

UnparsedVersion = Union[Version, str]
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)
CallableOperator = Callable[[Version, str], bool]


def _coerce_version(version: UnparsedVersion) -> Version:
    if not isinstance(version, Version):
        version = Version(version)
    return version


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> Optional[bool]:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: Optional[bool] = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @abc.abstractmethod
    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: Optional[bool] = None
    ) -> Iterator[UnparsedVersionVar]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).
    """

    _operator_regex_str = r"""
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = r"""
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \s*
                [^\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
        )
        """

    _regex = re.compile(
        r"^\s*" + _operator_regex_str + _version_regex_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: Optional[bool] = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        match = self._regex.search(spec)
        if not match:
            raise InvalidSpecifier(f"Invalid specifier: '{spec}'")

        self._spec: Tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

    # https://github.com/python/mypy/pull/13475#pullrequestreview-1079784515
    @property  # type: ignore[override]
    def prereleases(self) -> bool:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Look at all of our specifiers and determine if they are inclusive
        # operators, and if they are if they are including an explicit
        # prerelease.
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "==="]:
            # The == specifier can include a trailing .*, if it does we
            # want to remove before parsing.
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]

            # Parse the version, and if it is a pre-release than this
            # specifier allows pre-releases.
            if Version(version).is_prerelease:
                return True

        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> Tuple[str, str]:
        canonical_version = canonicalize_version(
            self._spec[1],
            strip_trailing_zero=(self._spec[0] != "~="),
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> CallableOperator:
        operator_callable: CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: Version, spec: str) -> bool:
        # Compatible releases have an equivalent combination of >= and ==. That
        # is that ~=2.2 is equivalent to >=2.2,==2.*. This allows us to
        # implement this in terms of the other specifiers instead of
        # implementing it ourselves. The only thing we need to do is construct
        # the other specifiers.

        # We want everything but the last item in the version, but we want to
        # ignore suffix segments.
        prefix = _version_join(
            list(itertools.takewhile(_is_not_suffix, _version_split(spec)))[:-1]
        )

        # Add the prefix notation to the end of our string
        prefix += ".*"

        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: Version, spec: str) -> bool:
        # We need special logic to handle prefix matching
        if spec.endswith(".*"):
            # In the case of prefix matching we want to ignore local segment.
            normalized_prospective = canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            # Get the normalized version string ignoring the trailing .*
            normalized_spec = canonicalize_version(spec[:-2], strip_trailing_zero=False)
            # Split the spec out by bangs and dots, and pretend that there is
            # an implicit dot in between a release segment and a pre-release segment.
            split_spec = _version_split(normalized_spec)

            # Split the prospective version out by bangs and dots, and pretend
            # that there is an implicit dot in between a release segment and
            # a pre-release segment.
            split_prospective = _version_split(normalized_prospective)

            # 0-pad the prospective version before shortening it to get the correct
            # shortened version.
            padded_prospective, _ = _pad_version(split_prospective, split_spec)

            # Shorten the prospective version to be the same length as the spec
            # so that we can determine if the specifier is a prefix of the
            # prospective version or not.
            shortened_prospective = padded_prospective[: len(split_spec)]

            return shortened_prospective == split_spec
        else:
            # Convert our spec string into a Version
            spec_version = Version(spec)

            # If the specifier does not have a local segment, then we want to
            # act as if the prospective version also does not have a local
            # segment.
            if not spec_version.local:
                prospective = Version(prospective.public)

            return prospective == spec_version

    def _compare_not_equal(self, prospective: Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) <= Version(spec)

    def _compare_greater_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) >= Version(spec)

    def _compare_less_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is less than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective < spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a pre-release version, that we do not accept pre-release
        # versions for the version mentioned in the specifier (e.g. <3.1 should
        # not match 3.1.dev0, but should match 3.0.dev0).
        if not spec.is_prerelease and prospective.is_prerelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # less than the spec version *and* it's not a pre-release of the same
        # version in the spec.
        return True

    def _compare_greater_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is greater than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective > spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a post-release version, that we do not accept
        # post-release versions for the version mentioned in the specifier
        # (e.g. >3.1 should not match 3.0.post0, but should match 3.2.post0).
        if not spec.is_postrelease and prospective.is_postrelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # Ensure that we do not allow a local version of the version mentioned
        # in the specifier, which is technically greater than, to match.
        if prospective.local is not None:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # greater than the spec version *and* it's not a pre-release of the
        # same version in the spec.
        return True

    def _compare_arbitrary(self, prospective: Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: Union[str, Version]) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self, item: UnparsedVersion, prereleases: Optional[bool] = None
    ) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3", prereleases=True).contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3").contains("1.3.0a1", prereleases=True)
        True
        """

        # Determine if prereleases are to be allowed or not.
        if prereleases is None:
            prereleases = self.prereleases

        # Normalize item to a Version, this allows us to have a shortcut for
        # "2.0" in Specifier(">=2")
        normalized_item = _coerce_version(item)

        # Determine if we should be supporting prereleases in this specifier
        # or not, if we do not support prereleases than we can short circuit
        # logic if this version is a prereleases.
        if normalized_item.is_prerelease and not prereleases:
            return False

        # Actually do the comparison to determine if this item is contained
        # within this Specifier or not.
        operator_callable: CallableOperator = self._get_operator(self.operator)
        return operator_callable(normalized_item, self.version)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: Optional[bool] = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(Specifier().contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        """

        yielded = False
        found_prereleases = []

        kw = {"prereleases": prereleases if prereleases is not None else True}

        # Attempt to iterate over all the values in the iterable and if any of
        # them match, yield them.
        for version in iterable:
            parsed_version = _coerce_version(version)

            if self.contains(parsed_version, **kw):
                # If our version is a prerelease, and we were not set to allow
                # prereleases, then we'll store it for later in case nothing
                # else matches this specifier.
                if parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                # Either this is not a prerelease, or we should have been
                # accepting prereleases from the beginning.
                else:
                    yielded = True
                    yield version

        # Now that we've iterated over everything, determine if we've yielded
        # any values, and if we have not and we have any prereleases stored up
        # then we will go ahead and yield the prereleases.
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def _version_split(version: str) -> List[str]:
    """Split version into components.

    The split components are intended for version comparison. The logic does
    not attempt to retain the original version string, so joining the
    components back with :func:`_version_join` may not produce the original
    version string.
    """
    result: List[str] = []

    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")

    for item in rest.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def _version_join(components: List[str]) -> str:
    """Join split version components into a version string.

    This function assumes the input came from :func:`_version_split`, where the
    first component must be the epoch (either empty or numeric), and all other
    components numeric.
    """
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def _is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def _pad_version(left: List[str], right: List[str]) -> Tuple[List[str], List[str]]:
    left_split, right_split = [], []

    # Get the release segment of our versions
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))

    # Get the rest of our versions
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])

    # Insert our padding
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))

    return (
        list(itertools.chain.from_iterable(left_split)),
        list(itertools.chain.from_iterable(right_split)),
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.
    """

    def __init__(
        self, specifiers: str = "", prereleases: Optional[bool] = None
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        """

        # Split on `,` to break each individual specifier into it's own item, and
        # strip each item to remove leading/trailing whitespace.
        split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

        # Make each individual specifier a Specifier and save in a frozen set for later.
        self._specs = frozenset(map(Specifier, split_specifiers))

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    @property
    def prereleases(self) -> Optional[bool]:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(self, other: Union["SpecifierSet", str]) -> "SpecifierSet":
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)

        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease "
                "overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._specs == other._specs

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: Optional[bool] = None,
        installed: Optional[bool] = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True).contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True
        """
        # Ensure that our item is a Version instance.
        if not isinstance(item, Version):
            item = Version(item)

        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # We can determine if we're going to allow pre-releases by looking to
        # see if any of the underlying items supports them. If none of them do
        # and this item is a pre-release then we do not allow it and we can
        # short circuit that here.
        # Note: This means that 1.0.dev1 would not be contained in something
        #       like >=1.0.devabc however it would be in >=1.0.debabc,>0.0.dev0
        if not prereleases and item.is_prerelease:
            return False

        if installed and item.is_prerelease:
            item = Version(item.base_version)

        # We simply dispatch to the underlying specs here to make sure that the
        # given version is contained within all of them.
        # Note: This use of all() here means that an empty set of specifiers
        #       will always return True, this is an explicit design decision.
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: Optional[bool] = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(SpecifierSet(...).contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        []
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # If we have any specifiers, then we want to wrap our iterable in the
        # filter method for each one, this will act as a logical AND amongst
        # each specifier.
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        # If we do not have any specifiers, then we need to have a rough filter
        # which will filter out any pre-releases, unless there are no final
        # releases.
        else:
            filtered: List[UnparsedVersionVar] = []
            found_prereleases: List[UnparsedVersionVar] = []

            for item in iterable:
                parsed_version = _coerce_version(item)

                # Store any item which is a pre-release for later unless we've
                # already found a final version or we are accepting prereleases
                if parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)

            # If we've found no items except for pre-releases, then we'll go
            # ahead and use the pre-releases
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)

            return iter(filtered)