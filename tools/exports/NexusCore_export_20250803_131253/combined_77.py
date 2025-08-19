
# === NexusCore/tools\exports\export_20250803_114325\combined_97.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\bedrock\_stream.py ===
from __future__ import annotations

from typing import TypeVar

import httpx

from ..._client import Anthropic, AsyncAnthropic
from ..._streaming import Stream, AsyncStream
from ._stream_decoder import AWSEventStreamDecoder

_T = TypeVar("_T")


class BedrockStream(Stream[_T]):
    def __init__(
        self,
        *,
        cast_to: type[_T],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        super().__init__(cast_to=cast_to, response=response, client=client)

        self._decoder = AWSEventStreamDecoder()


class AsyncBedrockStream(AsyncStream[_T]):
    def __init__(
        self,
        *,
        cast_to: type[_T],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        super().__init__(cast_to=cast_to, response=response, client=client)

        self._decoder = AWSEventStreamDecoder()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\client.py ===
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
from google.protobuf import duration_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.cache_service import pagers
from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content
from google.ai.generativelanguage_v1beta.types import content

from .transports.base import DEFAULT_CLIENT_INFO, CacheServiceTransport
from .transports.grpc import CacheServiceGrpcTransport
from .transports.grpc_asyncio import CacheServiceGrpcAsyncIOTransport
from .transports.rest import CacheServiceRestTransport


class CacheServiceClientMeta(type):
    """Metaclass for the CacheService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[CacheServiceTransport]]
    _transport_registry["grpc"] = CacheServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = CacheServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = CacheServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[CacheServiceTransport]:
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


class CacheServiceClient(metaclass=CacheServiceClientMeta):
    """API for managing cache of content (CachedContent resources)
    that can be used in GenerativeService requests. This way
    generate content requests can benefit from preprocessing work
    being done earlier, possibly lowering their computational cost.
    It is intended to be used with large contexts.
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
            CacheServiceClient: The constructed client.
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
            CacheServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> CacheServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            CacheServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def cached_content_path(
        id: str,
    ) -> str:
        """Returns a fully-qualified cached_content string."""
        return "cachedContents/{id}".format(
            id=id,
        )

    @staticmethod
    def parse_cached_content_path(path: str) -> Dict[str, str]:
        """Parses a cached_content path into its component segments."""
        m = re.match(r"^cachedContents/(?P<id>.+?)$", path)
        return m.groupdict() if m else {}

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
            _default_universe = CacheServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = CacheServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = CacheServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = CacheServiceClient._DEFAULT_UNIVERSE
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

        default_universe = CacheServiceClient._DEFAULT_UNIVERSE
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
            or CacheServiceClient._compare_universes(
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
            Union[str, CacheServiceTransport, Callable[..., CacheServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the cache service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,CacheServiceTransport,Callable[..., CacheServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the CacheServiceTransport constructor.
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
        ) = CacheServiceClient._read_environment_variables()
        self._client_cert_source = CacheServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = CacheServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, CacheServiceTransport)
        if transport_provided:
            # transport is a CacheServiceTransport instance.
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
            self._transport = cast(CacheServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or CacheServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
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
                Type[CacheServiceTransport], Callable[..., CacheServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., CacheServiceTransport], transport)
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

    def list_cached_contents(
        self,
        request: Optional[Union[cache_service.ListCachedContentsRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListCachedContentsPager:
        r"""Lists CachedContents.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_cached_contents():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListCachedContentsRequest(
                )

                # Make the request
                page_result = client.list_cached_contents(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListCachedContentsRequest, dict]):
                The request object. Request to list CachedContents.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.cache_service.pagers.ListCachedContentsPager:
                Response with CachedContents list.

                Iterating over this object will yield
                results and resolve additional pages
                automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.ListCachedContentsRequest):
            request = cache_service.ListCachedContentsRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_cached_contents]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListCachedContentsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def create_cached_content(
        self,
        request: Optional[Union[cache_service.CreateCachedContentRequest, dict]] = None,
        *,
        cached_content: Optional[gag_cached_content.CachedContent] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_cached_content.CachedContent:
        r"""Creates CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateCachedContentRequest(
                )

                # Make the request
                response = client.create_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateCachedContentRequest, dict]):
                The request object. Request to create CachedContent.
            cached_content (google.ai.generativelanguage_v1beta.types.CachedContent):
                Required. The cached content to
                create.

                This corresponds to the ``cached_content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([cached_content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.CreateCachedContentRequest):
            request = cache_service.CreateCachedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if cached_content is not None:
                request.cached_content = cached_content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_cached_content]

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

    def get_cached_content(
        self,
        request: Optional[Union[cache_service.GetCachedContentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> cached_content.CachedContent:
        r"""Reads CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetCachedContentRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetCachedContentRequest, dict]):
                The request object. Request to read CachedContent.
            name (str):
                Required. The resource name referring to the content
                cache entry. Format: ``cachedContents/{id}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

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
        if not isinstance(request, cache_service.GetCachedContentRequest):
            request = cache_service.GetCachedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_cached_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
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

    def update_cached_content(
        self,
        request: Optional[Union[cache_service.UpdateCachedContentRequest, dict]] = None,
        *,
        cached_content: Optional[gag_cached_content.CachedContent] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_cached_content.CachedContent:
        r"""Updates CachedContent resource (only expiration is
        updatable).

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateCachedContentRequest(
                )

                # Make the request
                response = client.update_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdateCachedContentRequest, dict]):
                The request object. Request to update CachedContent.
            cached_content (google.ai.generativelanguage_v1beta.types.CachedContent):
                Required. The content cache entry to
                update

                This corresponds to the ``cached_content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                The list of fields to update.
                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([cached_content, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.UpdateCachedContentRequest):
            request = cache_service.UpdateCachedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if cached_content is not None:
                request.cached_content = cached_content
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_cached_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("cached_content.name", request.cached_content.name),)
            ),
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

    def delete_cached_content(
        self,
        request: Optional[Union[cache_service.DeleteCachedContentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteCachedContentRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_cached_content(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteCachedContentRequest, dict]):
                The request object. Request to delete CachedContent.
            name (str):
                Required. The resource name referring to the content
                cache entry Format: ``cachedContents/{id}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
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
        if not isinstance(request, cache_service.DeleteCachedContentRequest):
            request = cache_service.DeleteCachedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_cached_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    def __enter__(self) -> "CacheServiceClient":
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


__all__ = ("CacheServiceClient",)

# === NexusCore/openenv\Lib\site-packages\multidict\_multidict_py.py ===
import enum
import functools
import reprlib
import sys
from array import array
from collections.abc import (
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    ValuesView,
)
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    NoReturn,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

from ._abc import MDArg, MultiMapping, MutableMultiMapping, SupportsKeys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class istr(str):
    """Case insensitive str."""

    __is_istr__ = True
    __istr_identity__: Optional[str] = None


_V = TypeVar("_V")
_T = TypeVar("_T")

_SENTINEL = enum.Enum("_SENTINEL", "sentinel")
sentinel = _SENTINEL.sentinel

_version = array("Q", [0])


class _Iter(Generic[_T]):
    __slots__ = ("_size", "_iter")

    def __init__(self, size: int, iterator: Iterator[_T]):
        self._size = size
        self._iter = iterator

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> _T:
        return next(self._iter)

    def __length_hint__(self) -> int:
        return self._size


class _ViewBase(Generic[_V]):
    def __init__(
        self,
        md: "MultiDict[_V]",
    ):
        self._md = md

    def __len__(self) -> int:
        return len(self._md)


class _ItemsView(_ViewBase[_V], ItemsView[str, _V]):
    def __contains__(self, item: object) -> bool:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            return False
        key, value = item
        try:
            identity = self._md._identity(key)
        except TypeError:
            return False
        hash_ = hash(identity)
        for slot, idx, e in self._md._keys.iter_hash(hash_):
            if e.identity == identity and value == e.value:
                return True
        return False

    def __iter__(self) -> _Iter[tuple[str, _V]]:
        return _Iter(len(self), self._iter(self._md._version))

    def _iter(self, version: int) -> Iterator[tuple[str, _V]]:
        for e in self._md._keys.iter_entries():
            if version != self._md._version:
                raise RuntimeError("Dictionary changed during iteration")
            yield self._md._key(e.key), e.value

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        lst = []
        for e in self._md._keys.iter_entries():
            lst.append(f"'{e.key}': {e.value!r}")
        body = ", ".join(lst)
        return f"<{self.__class__.__name__}({body})>"

    def _parse_item(
        self, arg: Union[tuple[str, _V], _T]
    ) -> Optional[tuple[int, str, str, _V]]:
        if not isinstance(arg, tuple):
            return None
        if len(arg) != 2:
            return None
        try:
            identity = self._md._identity(arg[0])
            return (hash(identity), identity, arg[0], arg[1])
        except TypeError:
            return None

    def _tmp_set(self, it: Iterable[_T]) -> set[tuple[str, _V]]:
        tmp = set()
        for arg in it:
            item = self._parse_item(arg)
            if item is None:
                continue
            else:
                tmp.add((item[1], item[3]))
        return tmp

    def __and__(self, other: Iterable[Any]) -> set[tuple[str, _V]]:
        ret = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for arg in it:
            item = self._parse_item(arg)
            if item is None:
                continue
            hash_, identity, key, value = item
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                e.hash = -1
                if e.identity == identity and e.value == value:
                    ret.add((e.key, e.value))
            self._md._keys.restore_hash(hash_)
        return ret

    def __rand__(self, other: Iterable[_T]) -> set[_T]:
        ret = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for arg in it:
            item = self._parse_item(arg)
            if item is None:
                continue
            hash_, identity, key, value = item
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity and e.value == value:
                    ret.add(arg)
                    break
        return ret

    def __or__(self, other: Iterable[_T]) -> set[Union[tuple[str, _V], _T]]:
        ret: set[Union[tuple[str, _V], _T]] = set(self)
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for arg in it:
            item: Optional[tuple[int, str, str, _V]] = self._parse_item(arg)
            if item is None:
                ret.add(arg)
                continue
            hash_, identity, key, value = item
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity and e.value == value:  # pragma: no branch
                    break
            else:
                ret.add(arg)
        return ret

    def __ror__(self, other: Iterable[_T]) -> set[Union[tuple[str, _V], _T]]:
        try:
            ret: set[Union[tuple[str, _V], _T]] = set(other)
        except TypeError:
            return NotImplemented
        tmp = self._tmp_set(ret)

        for e in self._md._keys.iter_entries():
            if (e.identity, e.value) not in tmp:
                ret.add((e.key, e.value))
        return ret

    def __sub__(self, other: Iterable[_T]) -> set[Union[tuple[str, _V], _T]]:
        ret: set[Union[tuple[str, _V], _T]] = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        tmp = self._tmp_set(it)

        for e in self._md._keys.iter_entries():
            if (e.identity, e.value) not in tmp:
                ret.add((e.key, e.value))

        return ret

    def __rsub__(self, other: Iterable[_T]) -> set[_T]:
        ret: set[_T] = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for arg in it:
            item = self._parse_item(arg)
            if item is None:
                ret.add(arg)
                continue

            hash_, identity, key, value = item
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity and e.value == value:  # pragma: no branch
                    break
            else:
                ret.add(arg)
        return ret

    def __xor__(self, other: Iterable[_T]) -> set[Union[tuple[str, _V], _T]]:
        try:
            rgt = set(other)
        except TypeError:
            return NotImplemented
        ret: set[Union[tuple[str, _V], _T]] = self - rgt
        ret |= rgt - self
        return ret

    __rxor__ = __xor__

    def isdisjoint(self, other: Iterable[tuple[str, _V]]) -> bool:
        for arg in other:
            item = self._parse_item(arg)
            if item is None:
                continue

            hash_, identity, key, value = item
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity and e.value == value:  # pragma: no branch
                    return False
        return True


class _ValuesView(_ViewBase[_V], ValuesView[_V]):
    def __contains__(self, value: object) -> bool:
        for e in self._md._keys.iter_entries():
            if e.value == value:
                return True
        return False

    def __iter__(self) -> _Iter[_V]:
        return _Iter(len(self), self._iter(self._md._version))

    def _iter(self, version: int) -> Iterator[_V]:
        for e in self._md._keys.iter_entries():
            if version != self._md._version:
                raise RuntimeError("Dictionary changed during iteration")
            yield e.value

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        lst = []
        for e in self._md._keys.iter_entries():
            lst.append(repr(e.value))
        body = ", ".join(lst)
        return f"<{self.__class__.__name__}({body})>"


class _KeysView(_ViewBase[_V], KeysView[str]):
    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        identity = self._md._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._md._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                return True
        return False

    def __iter__(self) -> _Iter[str]:
        return _Iter(len(self), self._iter(self._md._version))

    def _iter(self, version: int) -> Iterator[str]:
        for e in self._md._keys.iter_entries():
            if version != self._md._version:
                raise RuntimeError("Dictionary changed during iteration")
            yield self._md._key(e.key)

    def __repr__(self) -> str:
        lst = []
        for e in self._md._keys.iter_entries():
            lst.append(f"'{e.key}'")
        body = ", ".join(lst)
        return f"<{self.__class__.__name__}({body})>"

    def __and__(self, other: Iterable[object]) -> set[str]:
        ret = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for key in it:
            if not isinstance(key, str):
                continue
            identity = self._md._identity(key)
            hash_ = hash(identity)
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity:  # pragma: no branch
                    ret.add(e.key)
                    break
        return ret

    def __rand__(self, other: Iterable[_T]) -> set[_T]:
        ret = set()
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for key in it:
            if not isinstance(key, str):
                continue
            if key in self._md:
                ret.add(key)
        return cast(set[_T], ret)

    def __or__(self, other: Iterable[_T]) -> set[Union[str, _T]]:
        ret: set[Union[str, _T]] = set(self)
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for key in it:
            if not isinstance(key, str):
                ret.add(key)
                continue
            if key not in self._md:
                ret.add(key)
        return ret

    def __ror__(self, other: Iterable[_T]) -> set[Union[str, _T]]:
        try:
            ret: set[Union[str, _T]] = set(other)
        except TypeError:
            return NotImplemented

        tmp = set()
        for key in ret:
            if not isinstance(key, str):
                continue
            identity = self._md._identity(key)
            tmp.add(identity)

        for e in self._md._keys.iter_entries():
            if e.identity not in tmp:
                ret.add(e.key)
        return ret

    def __sub__(self, other: Iterable[object]) -> set[str]:
        ret = set(self)
        try:
            it = iter(other)
        except TypeError:
            return NotImplemented
        for key in it:
            if not isinstance(key, str):
                continue
            identity = self._md._identity(key)
            hash_ = hash(identity)
            for slot, idx, e in self._md._keys.iter_hash(hash_):
                if e.identity == identity:  # pragma: no branch
                    ret.discard(e.key)
                    break
        return ret

    def __rsub__(self, other: Iterable[_T]) -> set[_T]:
        try:
            ret: set[_T] = set(other)
        except TypeError:
            return NotImplemented
        for key in other:
            if not isinstance(key, str):
                continue
            if key in self._md:
                ret.discard(key)  # type: ignore[arg-type]
        return ret

    def __xor__(self, other: Iterable[_T]) -> set[Union[str, _T]]:
        try:
            rgt = set(other)
        except TypeError:
            return NotImplemented
        ret: set[Union[str, _T]] = self - rgt  # type: ignore[assignment]
        ret |= rgt - self
        return ret

    __rxor__ = __xor__

    def isdisjoint(self, other: Iterable[object]) -> bool:
        for key in other:
            if not isinstance(key, str):
                continue
            if key in self._md:
                return False
        return True


class _CSMixin:
    _ci: ClassVar[bool] = False

    def _key(self, key: str) -> str:
        return key

    def _identity(self, key: str) -> str:
        if isinstance(key, str):
            return key
        else:
            raise TypeError("MultiDict keys should be either str or subclasses of str")


class _CIMixin:
    _ci: ClassVar[bool] = True

    def _key(self, key: str) -> str:
        if type(key) is istr:
            return key
        else:
            return istr(key)

    def _identity(self, key: str) -> str:
        if isinstance(key, istr):
            ret = key.__istr_identity__
            if ret is None:
                ret = key.title()
                key.__istr_identity__ = ret
            return ret
        if isinstance(key, str):
            return key.title()
        else:
            raise TypeError("MultiDict keys should be either str or subclasses of str")


def estimate_log2_keysize(n: int) -> int:
    # 7 == HT_MINSIZE - 1
    return (((n * 3 + 1) // 2) | 7).bit_length()


@dataclass
class _Entry(Generic[_V]):
    hash: int
    identity: str
    key: str
    value: _V


@dataclass
class _HtKeys(Generic[_V]):  # type: ignore[misc]
    LOG_MINSIZE: ClassVar[int] = 3
    MINSIZE: ClassVar[int] = 8
    PREALLOCATED_INDICES: ClassVar[dict[int, array]] = {  # type: ignore[type-arg]
        log2_size: array(
            "b" if log2_size < 8 else "h", (-1 for i in range(1 << log2_size))
        )
        for log2_size in range(3, 10)
    }

    log2_size: int
    usable: int

    indices: array  # type: ignore[type-arg] # in py3.9 array is not generic
    entries: list[Optional[_Entry[_V]]]

    @functools.cached_property
    def nslots(self) -> int:
        return 1 << self.log2_size

    @functools.cached_property
    def mask(self) -> int:
        return self.nslots - 1

    if sys.implementation.name != "pypy":

        def __sizeof__(self) -> int:
            return (
                object.__sizeof__(self)
                + sys.getsizeof(self.indices)
                + sys.getsizeof(self.entries)
            )

    @classmethod
    def new(cls, log2_size: int, entries: list[Optional[_Entry[_V]]]) -> Self:
        size = 1 << log2_size
        usable = (size << 1) // 3
        if log2_size < 10:
            indices = cls.PREALLOCATED_INDICES[log2_size].__copy__()
        elif log2_size < 16:
            indices = array("h", (-1 for i in range(size)))
        elif log2_size < 32:
            indices = array("l", (-1 for i in range(size)))
        else:  # pragma: no cover  # don't test huge multidicts
            indices = array("q", (-1 for i in range(size)))
        ret = cls(
            log2_size=log2_size,
            usable=usable,
            indices=indices,
            entries=entries,
        )
        return ret

    def clone(self) -> "_HtKeys[_V]":
        entries = [
            _Entry(e.hash, e.identity, e.key, e.value) if e is not None else None
            for e in self.entries
        ]

        return _HtKeys(
            log2_size=self.log2_size,
            usable=self.usable,
            indices=self.indices.__copy__(),
            entries=entries,
        )

    def build_indices(self, update: bool) -> None:
        mask = self.mask
        indices = self.indices
        for idx, e in enumerate(self.entries):
            assert e is not None
            hash_ = e.hash
            if update:
                if hash_ == -1:
                    hash_ = hash(e.identity)
            else:
                assert hash_ != -1
            i = hash_ & mask
            perturb = hash_ & sys.maxsize
            while indices[i] != -1:
                perturb >>= 5
                i = mask & (i * 5 + perturb + 1)
            indices[i] = idx

    def find_empty_slot(self, hash_: int) -> int:
        mask = self.mask
        indices = self.indices
        i = hash_ & mask
        perturb = hash_ & sys.maxsize
        ix = indices[i]
        while ix != -1:
            perturb >>= 5
            i = (i * 5 + perturb + 1) & mask
            ix = indices[i]
        return i

    def iter_hash(self, hash_: int) -> Iterator[tuple[int, int, _Entry[_V]]]:
        mask = self.mask
        indices = self.indices
        entries = self.entries
        i = hash_ & mask
        perturb = hash_ & sys.maxsize
        ix = indices[i]
        while ix != -1:
            if ix != -2:
                e = entries[ix]
                if e.hash == hash_:
                    yield i, ix, e
            perturb >>= 5
            i = (i * 5 + perturb + 1) & mask
            ix = indices[i]

    def del_idx(self, hash_: int, idx: int) -> None:
        mask = self.mask
        indices = self.indices
        i = hash_ & mask
        perturb = hash_ & sys.maxsize
        ix = indices[i]
        while ix != idx:
            perturb >>= 5
            i = (i * 5 + perturb + 1) & mask
            ix = indices[i]
        indices[i] = -2

    def iter_entries(self) -> Iterator[_Entry[_V]]:
        return filter(None, self.entries)

    def restore_hash(self, hash_: int) -> None:
        mask = self.mask
        indices = self.indices
        entries = self.entries
        i = hash_ & mask
        perturb = hash_ & sys.maxsize
        ix = indices[i]
        while ix != -1:
            if ix != -2:
                entry = entries[ix]
                if entry.hash == -1:
                    entry.hash = hash_
            perturb >>= 5
            i = (i * 5 + perturb + 1) & mask
            ix = indices[i]


class MultiDict(_CSMixin, MutableMultiMapping[_V]):
    """Dictionary with the support for duplicate keys."""

    __slots__ = ("_keys", "_used", "_version")

    def __init__(self, arg: MDArg[_V] = None, /, **kwargs: _V):
        self._used = 0
        v = _version
        v[0] += 1
        self._version = v[0]
        if not kwargs:
            md = None
            if isinstance(arg, MultiDictProxy):
                md = arg._md
            elif isinstance(arg, MultiDict):
                md = arg
            if md is not None and md._ci is self._ci:
                self._from_md(md)
                return

        items = self._parse_args(arg, kwargs)
        log2_size = estimate_log2_keysize(len(items))
        if log2_size > 17:  # pragma: no cover
            # Don't overallocate really huge keys space in init
            log2_size = 17
        self._keys: _HtKeys[_V] = _HtKeys.new(log2_size, [])
        self._extend_items(items)

    def _from_md(self, md: "MultiDict[_V]") -> None:
        # Copy everything as-is without compacting the new multidict,
        # otherwise it requires reindexing
        self._keys = md._keys.clone()
        self._used = md._used

    @overload
    def getall(self, key: str) -> list[_V]: ...
    @overload
    def getall(self, key: str, default: _T) -> Union[list[_V], _T]: ...
    def getall(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[list[_V], _T]:
        """Return a list of all values matching the key."""
        identity = self._identity(key)
        hash_ = hash(identity)
        res = []

        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                res.append(e.value)
                e.hash = -1
        self._keys.restore_hash(hash_)

        if res:
            return res
        if not res and default is not sentinel:
            return default
        raise KeyError("Key not found: %r" % key)

    @overload
    def getone(self, key: str) -> _V: ...
    @overload
    def getone(self, key: str, default: _T) -> Union[_V, _T]: ...
    def getone(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[_V, _T]:
        """Get first value matching the key.

        Raises KeyError if the key is not found and no default is provided.
        """
        identity = self._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                return e.value
        if default is not sentinel:
            return default
        raise KeyError("Key not found: %r" % key)

    # Mapping interface #

    def __getitem__(self, key: str) -> _V:
        return self.getone(key)

    @overload
    def get(self, key: str, /) -> Union[_V, None]: ...
    @overload
    def get(self, key: str, /, default: _T) -> Union[_V, _T]: ...
    def get(self, key: str, default: Union[_T, None] = None) -> Union[_V, _T, None]:
        """Get first value matching the key.

        If the key is not found, returns the default (or None if no default is provided)
        """
        return self.getone(key, default)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return self._used

    def keys(self) -> KeysView[str]:
        """Return a new view of the dictionary's keys."""
        return _KeysView(self)

    def items(self) -> ItemsView[str, _V]:
        """Return a new view of the dictionary's items *(key, value) pairs)."""
        return _ItemsView(self)

    def values(self) -> _ValuesView[_V]:
        """Return a new view of the dictionary's values."""
        return _ValuesView(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return NotImplemented
        if isinstance(other, MultiDictProxy):
            return self == other._md
        if isinstance(other, MultiDict):
            lft = self._keys
            rht = other._keys
            if self._used != other._used:
                return False
            for e1, e2 in zip(lft.iter_entries(), rht.iter_entries()):
                if e1.identity != e2.identity or e1.value != e2.value:
                    return False
            return True
        if self._used != len(other):
            return False
        for k, v in self.items():
            nv = other.get(k, sentinel)
            if v != nv:
                return False
        return True

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        identity = self._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                return True
        return False

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        body = ", ".join(f"'{e.key}': {e.value!r}" for e in self._keys.iter_entries())
        return f"<{self.__class__.__name__}({body})>"

    if sys.implementation.name != "pypy":

        def __sizeof__(self) -> int:
            return object.__sizeof__(self) + sys.getsizeof(self._keys)

    def __reduce__(self) -> tuple[type[Self], tuple[list[tuple[str, _V]]]]:
        return (self.__class__, (list(self.items()),))

    def add(self, key: str, value: _V) -> None:
        identity = self._identity(key)
        hash_ = hash(identity)
        self._add_with_hash(_Entry(hash_, identity, key, value))
        self._incr_version()

    def copy(self) -> Self:
        """Return a copy of itself."""
        cls = self.__class__
        return cls(self)

    __copy__ = copy

    def extend(self, arg: MDArg[_V] = None, /, **kwargs: _V) -> None:
        """Extend current MultiDict with more values.

        This method must be used instead of update.
        """
        items = self._parse_args(arg, kwargs)
        newsize = self._used + len(items)
        self._resize(estimate_log2_keysize(newsize), False)
        self._extend_items(items)

    def _parse_args(
        self,
        arg: MDArg[_V],
        kwargs: Mapping[str, _V],
    ) -> list[_Entry[_V]]:
        identity_func = self._identity
        if arg:
            if isinstance(arg, MultiDictProxy):
                arg = arg._md
            if isinstance(arg, MultiDict):
                if self._ci is not arg._ci:
                    items = []
                    for e in arg._keys.iter_entries():
                        identity = identity_func(e.key)
                        items.append(_Entry(hash(identity), identity, e.key, e.value))
                else:
                    items = [
                        _Entry(e.hash, e.identity, e.key, e.value)
                        for e in arg._keys.iter_entries()
                    ]
                if kwargs:
                    for key, value in kwargs.items():
                        identity = identity_func(key)
                        items.append(_Entry(hash(identity), identity, key, value))
            else:
                if hasattr(arg, "keys"):
                    arg = cast(SupportsKeys[_V], arg)
                    arg = [(k, arg[k]) for k in arg.keys()]
                if kwargs:
                    arg = list(arg)
                    arg.extend(list(kwargs.items()))
                items = []
                for pos, item in enumerate(arg):
                    if not len(item) == 2:
                        raise ValueError(
                            f"multidict update sequence element #{pos}"
                            f"has length {len(item)}; 2 is required"
                        )
                    identity = identity_func(item[0])
                    items.append(_Entry(hash(identity), identity, item[0], item[1]))
        else:
            items = []
            for key, value in kwargs.items():
                identity = identity_func(key)
                items.append(_Entry(hash(identity), identity, key, value))

        return items

    def _extend_items(self, items: Iterable[_Entry[_V]]) -> None:
        for e in items:
            self._add_with_hash(e)
        self._incr_version()

    def clear(self) -> None:
        """Remove all items from MultiDict."""
        self._used = 0
        self._keys = _HtKeys.new(_HtKeys.LOG_MINSIZE, [])
        self._incr_version()

    # Mapping interface #

    def __setitem__(self, key: str, value: _V) -> None:
        identity = self._identity(key)
        hash_ = hash(identity)
        found = False

        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                if not found:
                    e.key = key
                    e.value = value
                    e.hash = -1
                    found = True
                    self._incr_version()
                elif e.hash != -1:  # pragma: no branch
                    self._del_at(slot, idx)

        if not found:
            self._add_with_hash(_Entry(hash_, identity, key, value))
        else:
            self._keys.restore_hash(hash_)

    def __delitem__(self, key: str) -> None:
        found = False
        identity = self._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                self._del_at(slot, idx)
                found = True
        if not found:
            raise KeyError(key)
        else:
            self._incr_version()

    @overload
    def setdefault(
        self: "MultiDict[Union[_T, None]]", key: str, default: None = None
    ) -> Union[_T, None]: ...
    @overload
    def setdefault(self, key: str, default: _V) -> _V: ...
    def setdefault(self, key: str, default: Union[_V, None] = None) -> Union[_V, None]:  # type: ignore[misc]
        """Return value for key, set value to default if key is not present."""
        identity = self._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                return e.value
        self.add(key, default)  # type: ignore[arg-type]
        return default

    @overload
    def popone(self, key: str) -> _V: ...
    @overload
    def popone(self, key: str, default: _T) -> Union[_V, _T]: ...
    def popone(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[_V, _T]:
        """Remove specified key and return the corresponding value.

        If key is not found, d is returned if given, otherwise
        KeyError is raised.

        """
        identity = self._identity(key)
        hash_ = hash(identity)
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                value = e.value
                self._del_at(slot, idx)
                self._incr_version()
                return value
        if default is sentinel:
            raise KeyError(key)
        else:
            return default

    # Type checking will inherit signature for pop() if we don't confuse it here.
    if not TYPE_CHECKING:
        pop = popone

    @overload
    def popall(self, key: str) -> list[_V]: ...
    @overload
    def popall(self, key: str, default: _T) -> Union[list[_V], _T]: ...
    def popall(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[list[_V], _T]:
        """Remove all occurrences of key and return the list of corresponding
        values.

        If key is not found, default is returned if given, otherwise
        KeyError is raised.

        """
        found = False
        identity = self._identity(key)
        hash_ = hash(identity)
        ret = []
        for slot, idx, e in self._keys.iter_hash(hash_):
            if e.identity == identity:  # pragma: no branch
                found = True
                ret.append(e.value)
                self._del_at(slot, idx)
                self._incr_version()

        if not found:
            if default is sentinel:
                raise KeyError(key)
            else:
                return default
        else:
            return ret

    def popitem(self) -> tuple[str, _V]:
        """Remove and return an arbitrary (key, value) pair."""
        if self._used <= 0:
            raise KeyError("empty multidict")

        pos = len(self._keys.entries) - 1
        entry = self._keys.entries.pop()

        while entry is None:
            pos -= 1
            entry = self._keys.entries.pop()

        ret = self._key(entry.key), entry.value
        self._keys.del_idx(entry.hash, pos)
        self._used -= 1
        self._incr_version()
        return ret

    def update(self, arg: MDArg[_V] = None, /, **kwargs: _V) -> None:
        """Update the dictionary from *other*, overwriting existing keys."""
        items = self._parse_args(arg, kwargs)
        newsize = self._used + len(items)
        log2_size = estimate_log2_keysize(newsize)
        if log2_size > 17:  # pragma: no cover
            # Don't overallocate really huge keys space in update,
            # duplicate keys could reduce the resulting anount of entries
            log2_size = 17
        if log2_size > self._keys.log2_size:
            self._resize(log2_size, False)
        self._update_items(items)

    def _update_items(self, items: list[_Entry[_V]]) -> None:
        if not items:
            return
        for entry in items:
            found = False
            hash_ = entry.hash
            identity = entry.identity
            for slot, idx, e in self._keys.iter_hash(hash_):
                if e.identity == identity:  # pragma: no branch
                    if not found:
                        found = True
                        e.key = entry.key
                        e.value = entry.value
                        e.hash = -1
                    else:
                        self._del_at_for_upd(e)
            if not found:
                self._add_with_hash_for_upd(entry)

        keys = self._keys
        indices = keys.indices
        entries = keys.entries
        for slot in range(keys.nslots):
            idx = indices[slot]
            if idx >= 0:
                e2 = entries[idx]
                assert e2 is not None
                if e2.key is None:
                    entries[idx] = None  # type: ignore[unreachable]
                    indices[slot] = -2
                    self._used -= 1
                if e2.hash == -1:
                    e2.hash = hash(e2.identity)

        self._incr_version()

    def _incr_version(self) -> None:
        v = _version
        v[0] += 1
        self._version = v[0]

    def _resize(self, log2_newsize: int, update: bool) -> None:
        oldkeys = self._keys
        newentries = self._used

        if len(oldkeys.entries) == newentries:
            entries = oldkeys.entries
        else:
            entries = [e for e in oldkeys.entries if e is not None]
        newkeys: _HtKeys[_V] = _HtKeys.new(log2_newsize, entries)
        newkeys.usable -= newentries
        newkeys.build_indices(update)
        self._keys = newkeys

    def _add_with_hash(self, entry: _Entry[_V]) -> None:
        if self._keys.usable <= 0:
            self._resize((self._used * 3 | _HtKeys.MINSIZE - 1).bit_length(), False)
        keys = self._keys
        slot = keys.find_empty_slot(entry.hash)
        keys.indices[slot] = len(keys.entries)
        keys.entries.append(entry)
        self._incr_version()
        self._used += 1
        keys.usable -= 1

    def _add_with_hash_for_upd(self, entry: _Entry[_V]) -> None:
        if self._keys.usable <= 0:
            self._resize((self._used * 3 | _HtKeys.MINSIZE - 1).bit_length(), True)
        keys = self._keys
        slot = keys.find_empty_slot(entry.hash)
        keys.indices[slot] = len(keys.entries)
        entry.hash = -1
        keys.entries.append(entry)
        self._incr_version()
        self._used += 1
        keys.usable -= 1

    def _del_at(self, slot: int, idx: int) -> None:
        self._keys.entries[idx] = None
        self._keys.indices[slot] = -2
        self._used -= 1

    def _del_at_for_upd(self, entry: _Entry[_V]) -> None:
        entry.key = None  # type: ignore[assignment]
        entry.value = None  # type: ignore[assignment]


class CIMultiDict(_CIMixin, MultiDict[_V]):
    """Dictionary with the support for duplicate case-insensitive keys."""


class MultiDictProxy(_CSMixin, MultiMapping[_V]):
    """Read-only proxy for MultiDict instance."""

    __slots__ = ("_md",)

    _md: MultiDict[_V]

    def __init__(self, arg: Union[MultiDict[_V], "MultiDictProxy[_V]"]):
        if not isinstance(arg, (MultiDict, MultiDictProxy)):
            raise TypeError(
                "ctor requires MultiDict or MultiDictProxy instance"
                f", not {type(arg)}"
            )
        if isinstance(arg, MultiDictProxy):
            self._md = arg._md
        else:
            self._md = arg

    def __reduce__(self) -> NoReturn:
        raise TypeError(f"can't pickle {self.__class__.__name__} objects")

    @overload
    def getall(self, key: str) -> list[_V]: ...
    @overload
    def getall(self, key: str, default: _T) -> Union[list[_V], _T]: ...
    def getall(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[list[_V], _T]:
        """Return a list of all values matching the key."""
        if default is not sentinel:
            return self._md.getall(key, default)
        else:
            return self._md.getall(key)

    @overload
    def getone(self, key: str) -> _V: ...
    @overload
    def getone(self, key: str, default: _T) -> Union[_V, _T]: ...
    def getone(
        self, key: str, default: Union[_T, _SENTINEL] = sentinel
    ) -> Union[_V, _T]:
        """Get first value matching the key.

        Raises KeyError if the key is not found and no default is provided.
        """
        if default is not sentinel:
            return self._md.getone(key, default)
        else:
            return self._md.getone(key)

    # Mapping interface #

    def __getitem__(self, key: str) -> _V:
        return self.getone(key)

    @overload
    def get(self, key: str, /) -> Union[_V, None]: ...
    @overload
    def get(self, key: str, /, default: _T) -> Union[_V, _T]: ...
    def get(self, key: str, default: Union[_T, None] = None) -> Union[_V, _T, None]:
        """Get first value matching the key.

        If the key is not found, returns the default (or None if no default is provided)
        """
        return self._md.getone(key, default)

    def __iter__(self) -> Iterator[str]:
        return iter(self._md.keys())

    def __len__(self) -> int:
        return len(self._md)

    def keys(self) -> KeysView[str]:
        """Return a new view of the dictionary's keys."""
        return self._md.keys()

    def items(self) -> ItemsView[str, _V]:
        """Return a new view of the dictionary's items *(key, value) pairs)."""
        return self._md.items()

    def values(self) -> _ValuesView[_V]:
        """Return a new view of the dictionary's values."""
        return self._md.values()

    def __eq__(self, other: object) -> bool:
        return self._md == other

    def __contains__(self, key: object) -> bool:
        return key in self._md

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        body = ", ".join(f"'{k}': {v!r}" for k, v in self.items())
        return f"<{self.__class__.__name__}({body})>"

    def copy(self) -> MultiDict[_V]:
        """Return a copy of itself."""
        return MultiDict(self._md)


class CIMultiDictProxy(_CIMixin, MultiDictProxy[_V]):
    """Read-only proxy for CIMultiDict instance."""

    def __init__(self, arg: Union[MultiDict[_V], MultiDictProxy[_V]]):
        if not isinstance(arg, (CIMultiDict, CIMultiDictProxy)):
            raise TypeError(
                "ctor requires CIMultiDict or CIMultiDictProxy instance"
                f", not {type(arg)}"
            )

        super().__init__(arg)

    def copy(self) -> CIMultiDict[_V]:
        """Return a copy of itself."""
        return CIMultiDict(self._md)


def getversion(md: Union[MultiDict[object], MultiDictProxy[object]]) -> int:
    if isinstance(md, MultiDictProxy):
        md = md._md
    elif not isinstance(md, MultiDict):
        raise TypeError("Parameter should be multidict or proxy")
    return md._version

# === NexusCore/openenv\Lib\site-packages\pydantic\config.py ===
"""Configuration for Pydantic models."""

from __future__ import annotations as _annotations

import warnings
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar, Union, cast, overload

from typing_extensions import TypeAlias, TypedDict, Unpack, deprecated

from ._migration import getattr_migration
from .aliases import AliasGenerator
from .errors import PydanticUserError
from .warnings import PydanticDeprecatedSince211

if TYPE_CHECKING:
    from ._internal._generate_schema import GenerateSchema as _GenerateSchema
    from .fields import ComputedFieldInfo, FieldInfo

__all__ = ('ConfigDict', 'with_config')


JsonValue: TypeAlias = Union[int, float, str, bool, None, list['JsonValue'], 'JsonDict']
JsonDict: TypeAlias = dict[str, JsonValue]

JsonEncoder = Callable[[Any], Any]

JsonSchemaExtraCallable: TypeAlias = Union[
    Callable[[JsonDict], None],
    Callable[[JsonDict, type[Any]], None],
]

ExtraValues = Literal['allow', 'ignore', 'forbid']


class ConfigDict(TypedDict, total=False):
    """A TypedDict for configuring Pydantic behaviour."""

    title: str | None
    """The title for the generated JSON schema, defaults to the model's name"""

    model_title_generator: Callable[[type], str] | None
    """A callable that takes a model class and returns the title for it. Defaults to `None`."""

    field_title_generator: Callable[[str, FieldInfo | ComputedFieldInfo], str] | None
    """A callable that takes a field's name and info and returns title for it. Defaults to `None`."""

    str_to_lower: bool
    """Whether to convert all characters to lowercase for str types. Defaults to `False`."""

    str_to_upper: bool
    """Whether to convert all characters to uppercase for str types. Defaults to `False`."""

    str_strip_whitespace: bool
    """Whether to strip leading and trailing whitespace for str types."""

    str_min_length: int
    """The minimum length for str types. Defaults to `None`."""

    str_max_length: int | None
    """The maximum length for str types. Defaults to `None`."""

    extra: ExtraValues | None
    '''
    Whether to ignore, allow, or forbid extra data during model initialization. Defaults to `'ignore'`.

    Three configuration values are available:

    - `'ignore'`: Providing extra data is ignored (the default):
      ```python
      from pydantic import BaseModel, ConfigDict

      class User(BaseModel):
          model_config = ConfigDict(extra='ignore')  # (1)!

          name: str

      user = User(name='John Doe', age=20)  # (2)!
      print(user)
      #> name='John Doe'
      ```

        1. This is the default behaviour.
        2. The `age` argument is ignored.

    - `'forbid'`: Providing extra data is not permitted, and a [`ValidationError`][pydantic_core.ValidationError]
      will be raised if this is the case:
      ```python
      from pydantic import BaseModel, ConfigDict, ValidationError


      class Model(BaseModel):
          x: int

          model_config = ConfigDict(extra='forbid')


      try:
          Model(x=1, y='a')
      except ValidationError as exc:
          print(exc)
          """
          1 validation error for Model
          y
            Extra inputs are not permitted [type=extra_forbidden, input_value='a', input_type=str]
          """
      ```

    - `'allow'`: Providing extra data is allowed and stored in the `__pydantic_extra__` dictionary attribute:
      ```python
      from pydantic import BaseModel, ConfigDict


      class Model(BaseModel):
          x: int

          model_config = ConfigDict(extra='allow')


      m = Model(x=1, y='a')
      assert m.__pydantic_extra__ == {'y': 'a'}
      ```
      By default, no validation will be applied to these extra items, but you can set a type for the values by overriding
      the type annotation for `__pydantic_extra__`:
      ```python
      from pydantic import BaseModel, ConfigDict, Field, ValidationError


      class Model(BaseModel):
          __pydantic_extra__: dict[str, int] = Field(init=False)  # (1)!

          x: int

          model_config = ConfigDict(extra='allow')


      try:
          Model(x=1, y='a')
      except ValidationError as exc:
          print(exc)
          """
          1 validation error for Model
          y
            Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='a', input_type=str]
          """

      m = Model(x=1, y='2')
      assert m.x == 1
      assert m.y == 2
      assert m.model_dump() == {'x': 1, 'y': 2}
      assert m.__pydantic_extra__ == {'y': 2}
      ```

        1. The `= Field(init=False)` does not have any effect at runtime, but prevents the `__pydantic_extra__` field from
           being included as a parameter to the model's `__init__` method by type checkers.
    '''

    frozen: bool
    """
    Whether models are faux-immutable, i.e. whether `__setattr__` is allowed, and also generates
    a `__hash__()` method for the model. This makes instances of the model potentially hashable if all the
    attributes are hashable. Defaults to `False`.

    Note:
        On V1, the inverse of this setting was called `allow_mutation`, and was `True` by default.
    """

    populate_by_name: bool
    """
    Whether an aliased field may be populated by its name as given by the model
    attribute, as well as the alias. Defaults to `False`.

    !!! warning
        `populate_by_name` usage is not recommended in v2.11+ and will be deprecated in v3.
        Instead, you should use the [`validate_by_name`][pydantic.config.ConfigDict.validate_by_name] configuration setting.

        When `validate_by_name=True` and `validate_by_alias=True`, this is strictly equivalent to the
        previous behavior of `populate_by_name=True`.

        In v2.11, we also introduced a [`validate_by_alias`][pydantic.config.ConfigDict.validate_by_alias] setting that introduces more fine grained
        control for validation behavior.

        Here's how you might go about using the new settings to achieve the same behavior:

        ```python
        from pydantic import BaseModel, ConfigDict, Field

        class Model(BaseModel):
            model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

            my_field: str = Field(alias='my_alias')  # (1)!

        m = Model(my_alias='foo')  # (2)!
        print(m)
        #> my_field='foo'

        m = Model(my_alias='foo')  # (3)!
        print(m)
        #> my_field='foo'
        ```

        1. The field `'my_field'` has an alias `'my_alias'`.
        2. The model is populated by the alias `'my_alias'`.
        3. The model is populated by the attribute name `'my_field'`.
    """

    use_enum_values: bool
    """
    Whether to populate models with the `value` property of enums, rather than the raw enum.
    This may be useful if you want to serialize `model.model_dump()` later. Defaults to `False`.

    !!! note
        If you have an `Optional[Enum]` value that you set a default for, you need to use `validate_default=True`
        for said Field to ensure that the `use_enum_values` flag takes effect on the default, as extracting an
        enum's value occurs during validation, not serialization.

    ```python
    from enum import Enum
    from typing import Optional

    from pydantic import BaseModel, ConfigDict, Field

    class SomeEnum(Enum):
        FOO = 'foo'
        BAR = 'bar'
        BAZ = 'baz'

    class SomeModel(BaseModel):
        model_config = ConfigDict(use_enum_values=True)

        some_enum: SomeEnum
        another_enum: Optional[SomeEnum] = Field(
            default=SomeEnum.FOO, validate_default=True
        )

    model1 = SomeModel(some_enum=SomeEnum.BAR)
    print(model1.model_dump())
    #> {'some_enum': 'bar', 'another_enum': 'foo'}

    model2 = SomeModel(some_enum=SomeEnum.BAR, another_enum=SomeEnum.BAZ)
    print(model2.model_dump())
    #> {'some_enum': 'bar', 'another_enum': 'baz'}
    ```
    """

    validate_assignment: bool
    """
    Whether to validate the data when the model is changed. Defaults to `False`.

    The default behavior of Pydantic is to validate the data when the model is created.

    In case the user changes the data after the model is created, the model is _not_ revalidated.

    ```python
    from pydantic import BaseModel

    class User(BaseModel):
        name: str

    user = User(name='John Doe')  # (1)!
    print(user)
    #> name='John Doe'
    user.name = 123  # (1)!
    print(user)
    #> name=123
    ```

    1. The validation happens only when the model is created.
    2. The validation does not happen when the data is changed.

    In case you want to revalidate the model when the data is changed, you can use `validate_assignment=True`:

    ```python
    from pydantic import BaseModel, ValidationError

    class User(BaseModel, validate_assignment=True):  # (1)!
        name: str

    user = User(name='John Doe')  # (2)!
    print(user)
    #> name='John Doe'
    try:
        user.name = 123  # (3)!
    except ValidationError as e:
        print(e)
        '''
        1 validation error for User
        name
          Input should be a valid string [type=string_type, input_value=123, input_type=int]
        '''
    ```

    1. You can either use class keyword arguments, or `model_config` to set `validate_assignment=True`.
    2. The validation happens when the model is created.
    3. The validation _also_ happens when the data is changed.
    """

    arbitrary_types_allowed: bool
    """
    Whether arbitrary types are allowed for field types. Defaults to `False`.

    ```python
    from pydantic import BaseModel, ConfigDict, ValidationError

    # This is not a pydantic model, it's an arbitrary class
    class Pet:
        def __init__(self, name: str):
            self.name = name

    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        pet: Pet
        owner: str

    pet = Pet(name='Hedwig')
    # A simple check of instance type is used to validate the data
    model = Model(owner='Harry', pet=pet)
    print(model)
    #> pet=<__main__.Pet object at 0x0123456789ab> owner='Harry'
    print(model.pet)
    #> <__main__.Pet object at 0x0123456789ab>
    print(model.pet.name)
    #> Hedwig
    print(type(model.pet))
    #> <class '__main__.Pet'>
    try:
        # If the value is not an instance of the type, it's invalid
        Model(owner='Harry', pet='Hedwig')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        pet
          Input should be an instance of Pet [type=is_instance_of, input_value='Hedwig', input_type=str]
        '''

    # Nothing in the instance of the arbitrary type is checked
    # Here name probably should have been a str, but it's not validated
    pet2 = Pet(name=42)
    model2 = Model(owner='Harry', pet=pet2)
    print(model2)
    #> pet=<__main__.Pet object at 0x0123456789ab> owner='Harry'
    print(model2.pet)
    #> <__main__.Pet object at 0x0123456789ab>
    print(model2.pet.name)
    #> 42
    print(type(model2.pet))
    #> <class '__main__.Pet'>
    ```
    """

    from_attributes: bool
    """
    Whether to build models and look up discriminators of tagged unions using python object attributes.
    """

    loc_by_alias: bool
    """Whether to use the actual key provided in the data (e.g. alias) for error `loc`s rather than the field's name. Defaults to `True`."""

    alias_generator: Callable[[str], str] | AliasGenerator | None
    """
    A callable that takes a field name and returns an alias for it
    or an instance of [`AliasGenerator`][pydantic.aliases.AliasGenerator]. Defaults to `None`.

    When using a callable, the alias generator is used for both validation and serialization.
    If you want to use different alias generators for validation and serialization, you can use
    [`AliasGenerator`][pydantic.aliases.AliasGenerator] instead.

    If data source field names do not match your code style (e. g. CamelCase fields),
    you can automatically generate aliases using `alias_generator`. Here's an example with
    a basic callable:

    ```python
    from pydantic import BaseModel, ConfigDict
    from pydantic.alias_generators import to_pascal

    class Voice(BaseModel):
        model_config = ConfigDict(alias_generator=to_pascal)

        name: str
        language_code: str

    voice = Voice(Name='Filiz', LanguageCode='tr-TR')
    print(voice.language_code)
    #> tr-TR
    print(voice.model_dump(by_alias=True))
    #> {'Name': 'Filiz', 'LanguageCode': 'tr-TR'}
    ```

    If you want to use different alias generators for validation and serialization, you can use
    [`AliasGenerator`][pydantic.aliases.AliasGenerator].

    ```python
    from pydantic import AliasGenerator, BaseModel, ConfigDict
    from pydantic.alias_generators import to_camel, to_pascal

    class Athlete(BaseModel):
        first_name: str
        last_name: str
        sport: str

        model_config = ConfigDict(
            alias_generator=AliasGenerator(
                validation_alias=to_camel,
                serialization_alias=to_pascal,
            )
        )

    athlete = Athlete(firstName='John', lastName='Doe', sport='track')
    print(athlete.model_dump(by_alias=True))
    #> {'FirstName': 'John', 'LastName': 'Doe', 'Sport': 'track'}
    ```

    Note:
        Pydantic offers three built-in alias generators: [`to_pascal`][pydantic.alias_generators.to_pascal],
        [`to_camel`][pydantic.alias_generators.to_camel], and [`to_snake`][pydantic.alias_generators.to_snake].
    """

    ignored_types: tuple[type, ...]
    """A tuple of types that may occur as values of class attributes without annotations. This is
    typically used for custom descriptors (classes that behave like `property`). If an attribute is set on a
    class without an annotation and has a type that is not in this tuple (or otherwise recognized by
    _pydantic_), an error will be raised. Defaults to `()`.
    """

    allow_inf_nan: bool
    """Whether to allow infinity (`+inf` an `-inf`) and NaN values to float and decimal fields. Defaults to `True`."""

    json_schema_extra: JsonDict | JsonSchemaExtraCallable | None
    """A dict or callable to provide extra JSON schema properties. Defaults to `None`."""

    json_encoders: dict[type[object], JsonEncoder] | None
    """
    A `dict` of custom JSON encoders for specific types. Defaults to `None`.

    !!! warning "Deprecated"
        This config option is a carryover from v1.
        We originally planned to remove it in v2 but didn't have a 1:1 replacement so we are keeping it for now.
        It is still deprecated and will likely be removed in the future.
    """

    # new in V2
    strict: bool
    """
    _(new in V2)_ If `True`, strict validation is applied to all fields on the model.

    By default, Pydantic attempts to coerce values to the correct type, when possible.

    There are situations in which you may want to disable this behavior, and instead raise an error if a value's type
    does not match the field's type annotation.

    To configure strict mode for all fields on a model, you can set `strict=True` on the model.

    ```python
    from pydantic import BaseModel, ConfigDict

    class Model(BaseModel):
        model_config = ConfigDict(strict=True)

        name: str
        age: int
    ```

    See [Strict Mode](../concepts/strict_mode.md) for more details.

    See the [Conversion Table](../concepts/conversion_table.md) for more details on how Pydantic converts data in both
    strict and lax modes.
    """
    # whether instances of models and dataclasses (including subclass instances) should re-validate, default 'never'
    revalidate_instances: Literal['always', 'never', 'subclass-instances']
    """
    When and how to revalidate models and dataclasses during validation. Accepts the string
    values of `'never'`, `'always'` and `'subclass-instances'`. Defaults to `'never'`.

    - `'never'` will not revalidate models and dataclasses during validation
    - `'always'` will revalidate models and dataclasses during validation
    - `'subclass-instances'` will revalidate models and dataclasses during validation if the instance is a
        subclass of the model or dataclass

    By default, model and dataclass instances are not revalidated during validation.

    ```python
    from pydantic import BaseModel

    class User(BaseModel, revalidate_instances='never'):  # (1)!
        hobbies: list[str]

    class SubUser(User):
        sins: list[str]

    class Transaction(BaseModel):
        user: User

    my_user = User(hobbies=['reading'])
    t = Transaction(user=my_user)
    print(t)
    #> user=User(hobbies=['reading'])

    my_user.hobbies = [1]  # (2)!
    t = Transaction(user=my_user)  # (3)!
    print(t)
    #> user=User(hobbies=[1])

    my_sub_user = SubUser(hobbies=['scuba diving'], sins=['lying'])
    t = Transaction(user=my_sub_user)
    print(t)
    #> user=SubUser(hobbies=['scuba diving'], sins=['lying'])
    ```

    1. `revalidate_instances` is set to `'never'` by **default.
    2. The assignment is not validated, unless you set `validate_assignment` to `True` in the model's config.
    3. Since `revalidate_instances` is set to `never`, this is not revalidated.

    If you want to revalidate instances during validation, you can set `revalidate_instances` to `'always'`
    in the model's config.

    ```python
    from pydantic import BaseModel, ValidationError

    class User(BaseModel, revalidate_instances='always'):  # (1)!
        hobbies: list[str]

    class SubUser(User):
        sins: list[str]

    class Transaction(BaseModel):
        user: User

    my_user = User(hobbies=['reading'])
    t = Transaction(user=my_user)
    print(t)
    #> user=User(hobbies=['reading'])

    my_user.hobbies = [1]
    try:
        t = Transaction(user=my_user)  # (2)!
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Transaction
        user.hobbies.0
          Input should be a valid string [type=string_type, input_value=1, input_type=int]
        '''

    my_sub_user = SubUser(hobbies=['scuba diving'], sins=['lying'])
    t = Transaction(user=my_sub_user)
    print(t)  # (3)!
    #> user=User(hobbies=['scuba diving'])
    ```

    1. `revalidate_instances` is set to `'always'`.
    2. The model is revalidated, since `revalidate_instances` is set to `'always'`.
    3. Using `'never'` we would have gotten `user=SubUser(hobbies=['scuba diving'], sins=['lying'])`.

    It's also possible to set `revalidate_instances` to `'subclass-instances'` to only revalidate instances
    of subclasses of the model.

    ```python
    from pydantic import BaseModel

    class User(BaseModel, revalidate_instances='subclass-instances'):  # (1)!
        hobbies: list[str]

    class SubUser(User):
        sins: list[str]

    class Transaction(BaseModel):
        user: User

    my_user = User(hobbies=['reading'])
    t = Transaction(user=my_user)
    print(t)
    #> user=User(hobbies=['reading'])

    my_user.hobbies = [1]
    t = Transaction(user=my_user)  # (2)!
    print(t)
    #> user=User(hobbies=[1])

    my_sub_user = SubUser(hobbies=['scuba diving'], sins=['lying'])
    t = Transaction(user=my_sub_user)
    print(t)  # (3)!
    #> user=User(hobbies=['scuba diving'])
    ```

    1. `revalidate_instances` is set to `'subclass-instances'`.
    2. This is not revalidated, since `my_user` is not a subclass of `User`.
    3. Using `'never'` we would have gotten `user=SubUser(hobbies=['scuba diving'], sins=['lying'])`.
    """

    ser_json_timedelta: Literal['iso8601', 'float']
    """
    The format of JSON serialized timedeltas. Accepts the string values of `'iso8601'` and
    `'float'`. Defaults to `'iso8601'`.

    - `'iso8601'` will serialize timedeltas to ISO 8601 durations.
    - `'float'` will serialize timedeltas to the total number of seconds.
    """

    ser_json_bytes: Literal['utf8', 'base64', 'hex']
    """
    The encoding of JSON serialized bytes. Defaults to `'utf8'`.
    Set equal to `val_json_bytes` to get back an equal value after serialization round trip.

    - `'utf8'` will serialize bytes to UTF-8 strings.
    - `'base64'` will serialize bytes to URL safe base64 strings.
    - `'hex'` will serialize bytes to hexadecimal strings.
    """

    val_json_bytes: Literal['utf8', 'base64', 'hex']
    """
    The encoding of JSON serialized bytes to decode. Defaults to `'utf8'`.
    Set equal to `ser_json_bytes` to get back an equal value after serialization round trip.

    - `'utf8'` will deserialize UTF-8 strings to bytes.
    - `'base64'` will deserialize URL safe base64 strings to bytes.
    - `'hex'` will deserialize hexadecimal strings to bytes.
    """

    ser_json_inf_nan: Literal['null', 'constants', 'strings']
    """
    The encoding of JSON serialized infinity and NaN float values. Defaults to `'null'`.

    - `'null'` will serialize infinity and NaN values as `null`.
    - `'constants'` will serialize infinity and NaN values as `Infinity` and `NaN`.
    - `'strings'` will serialize infinity as string `"Infinity"` and NaN as string `"NaN"`.
    """

    # whether to validate default values during validation, default False
    validate_default: bool
    """Whether to validate default values during validation. Defaults to `False`."""

    validate_return: bool
    """Whether to validate the return value from call validators. Defaults to `False`."""

    protected_namespaces: tuple[str | Pattern[str], ...]
    """
    A `tuple` of strings and/or patterns that prevent models from having fields with names that conflict with them.
    For strings, we match on a prefix basis. Ex, if 'dog' is in the protected namespace, 'dog_name' will be protected.
    For patterns, we match on the entire field name. Ex, if `re.compile(r'^dog$')` is in the protected namespace, 'dog' will be protected, but 'dog_name' will not be.
    Defaults to `('model_validate', 'model_dump',)`.

    The reason we've selected these is to prevent collisions with other validation / dumping formats
    in the future - ex, `model_validate_{some_newly_supported_format}`.

    Before v2.10, Pydantic used `('model_',)` as the default value for this setting to
    prevent collisions between model attributes and `BaseModel`'s own methods. This was changed
    in v2.10 given feedback that this restriction was limiting in AI and data science contexts,
    where it is common to have fields with names like `model_id`, `model_input`, `model_output`, etc.

    For more details, see https://github.com/pydantic/pydantic/issues/10315.

    ```python
    import warnings

    from pydantic import BaseModel

    warnings.filterwarnings('error')  # Raise warnings as errors

    try:

        class Model(BaseModel):
            model_dump_something: str

    except UserWarning as e:
        print(e)
        '''
        Field "model_dump_something" in Model has conflict with protected namespace "model_dump".

        You may be able to resolve this warning by setting `model_config['protected_namespaces'] = ('model_validate',)`.
        '''
    ```

    You can customize this behavior using the `protected_namespaces` setting:

    ```python {test="skip"}
    import re
    import warnings

    from pydantic import BaseModel, ConfigDict

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter('always')  # Catch all warnings

        class Model(BaseModel):
            safe_field: str
            also_protect_field: str
            protect_this: str

            model_config = ConfigDict(
                protected_namespaces=(
                    'protect_me_',
                    'also_protect_',
                    re.compile('^protect_this$'),
                )
            )

    for warning in caught_warnings:
        print(f'{warning.message}')
        '''
        Field "also_protect_field" in Model has conflict with protected namespace "also_protect_".
        You may be able to resolve this warning by setting `model_config['protected_namespaces'] = ('protect_me_', re.compile('^protect_this$'))`.

        Field "protect_this" in Model has conflict with protected namespace "re.compile('^protect_this$')".
        You may be able to resolve this warning by setting `model_config['protected_namespaces'] = ('protect_me_', 'also_protect_')`.
        '''
    ```

    While Pydantic will only emit a warning when an item is in a protected namespace but does not actually have a collision,
    an error _is_ raised if there is an actual collision with an existing attribute:

    ```python
    from pydantic import BaseModel, ConfigDict

    try:

        class Model(BaseModel):
            model_validate: str

            model_config = ConfigDict(protected_namespaces=('model_',))

    except NameError as e:
        print(e)
        '''
        Field "model_validate" conflicts with member <bound method BaseModel.model_validate of <class 'pydantic.main.BaseModel'>> of protected namespace "model_".
        '''
    ```
    """

    hide_input_in_errors: bool
    """
    Whether to hide inputs when printing errors. Defaults to `False`.

    Pydantic shows the input value and type when it raises `ValidationError` during the validation.

    ```python
    from pydantic import BaseModel, ValidationError

    class Model(BaseModel):
        a: str

    try:
        Model(a=123)
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        a
          Input should be a valid string [type=string_type, input_value=123, input_type=int]
        '''
    ```

    You can hide the input value and type by setting the `hide_input_in_errors` config to `True`.

    ```python
    from pydantic import BaseModel, ConfigDict, ValidationError

    class Model(BaseModel):
        a: str
        model_config = ConfigDict(hide_input_in_errors=True)

    try:
        Model(a=123)
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        a
          Input should be a valid string [type=string_type]
        '''
    ```
    """

    defer_build: bool
    """
    Whether to defer model validator and serializer construction until the first model validation. Defaults to False.

    This can be useful to avoid the overhead of building models which are only
    used nested within other models, or when you want to manually define type namespace via
    [`Model.model_rebuild(_types_namespace=...)`][pydantic.BaseModel.model_rebuild].

    Since v2.10, this setting also applies to pydantic dataclasses and TypeAdapter instances.
    """

    plugin_settings: dict[str, object] | None
    """A `dict` of settings for plugins. Defaults to `None`."""

    schema_generator: type[_GenerateSchema] | None
    """
    !!! warning
        `schema_generator` is deprecated in v2.10.

        Prior to v2.10, this setting was advertised as highly subject to change.
        It's possible that this interface may once again become public once the internal core schema generation
        API is more stable, but that will likely come after significant performance improvements have been made.
    """

    json_schema_serialization_defaults_required: bool
    """
    Whether fields with default values should be marked as required in the serialization schema. Defaults to `False`.

    This ensures that the serialization schema will reflect the fact a field with a default will always be present
    when serializing the model, even though it is not required for validation.

    However, there are scenarios where this may be undesirable — in particular, if you want to share the schema
    between validation and serialization, and don't mind fields with defaults being marked as not required during
    serialization. See [#7209](https://github.com/pydantic/pydantic/issues/7209) for more details.

    ```python
    from pydantic import BaseModel, ConfigDict

    class Model(BaseModel):
        a: str = 'a'

        model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    print(Model.model_json_schema(mode='validation'))
    '''
    {
        'properties': {'a': {'default': 'a', 'title': 'A', 'type': 'string'}},
        'title': 'Model',
        'type': 'object',
    }
    '''
    print(Model.model_json_schema(mode='serialization'))
    '''
    {
        'properties': {'a': {'default': 'a', 'title': 'A', 'type': 'string'}},
        'required': ['a'],
        'title': 'Model',
        'type': 'object',
    }
    '''
    ```
    """

    json_schema_mode_override: Literal['validation', 'serialization', None]
    """
    If not `None`, the specified mode will be used to generate the JSON schema regardless of what `mode` was passed to
    the function call. Defaults to `None`.

    This provides a way to force the JSON schema generation to reflect a specific mode, e.g., to always use the
    validation schema.

    It can be useful when using frameworks (such as FastAPI) that may generate different schemas for validation
    and serialization that must both be referenced from the same schema; when this happens, we automatically append
    `-Input` to the definition reference for the validation schema and `-Output` to the definition reference for the
    serialization schema. By specifying a `json_schema_mode_override` though, this prevents the conflict between
    the validation and serialization schemas (since both will use the specified schema), and so prevents the suffixes
    from being added to the definition references.

    ```python
    from pydantic import BaseModel, ConfigDict, Json

    class Model(BaseModel):
        a: Json[int]  # requires a string to validate, but will dump an int

    print(Model.model_json_schema(mode='serialization'))
    '''
    {
        'properties': {'a': {'title': 'A', 'type': 'integer'}},
        'required': ['a'],
        'title': 'Model',
        'type': 'object',
    }
    '''

    class ForceInputModel(Model):
        # the following ensures that even with mode='serialization', we
        # will get the schema that would be generated for validation.
        model_config = ConfigDict(json_schema_mode_override='validation')

    print(ForceInputModel.model_json_schema(mode='serialization'))
    '''
    {
        'properties': {
            'a': {
                'contentMediaType': 'application/json',
                'contentSchema': {'type': 'integer'},
                'title': 'A',
                'type': 'string',
            }
        },
        'required': ['a'],
        'title': 'ForceInputModel',
        'type': 'object',
    }
    '''
    ```
    """

    coerce_numbers_to_str: bool
    """
    If `True`, enables automatic coercion of any `Number` type to `str` in "lax" (non-strict) mode. Defaults to `False`.

    Pydantic doesn't allow number types (`int`, `float`, `Decimal`) to be coerced as type `str` by default.

    ```python
    from decimal import Decimal

    from pydantic import BaseModel, ConfigDict, ValidationError

    class Model(BaseModel):
        value: str

    try:
        print(Model(value=42))
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        value
          Input should be a valid string [type=string_type, input_value=42, input_type=int]
        '''

    class Model(BaseModel):
        model_config = ConfigDict(coerce_numbers_to_str=True)

        value: str

    repr(Model(value=42).value)
    #> "42"
    repr(Model(value=42.13).value)
    #> "42.13"
    repr(Model(value=Decimal('42.13')).value)
    #> "42.13"
    ```
    """

    regex_engine: Literal['rust-regex', 'python-re']
    """
    The regex engine to be used for pattern validation.
    Defaults to `'rust-regex'`.

    - `rust-regex` uses the [`regex`](https://docs.rs/regex) Rust crate,
      which is non-backtracking and therefore more DDoS resistant, but does not support all regex features.
    - `python-re` use the [`re`](https://docs.python.org/3/library/re.html) module,
      which supports all regex features, but may be slower.

    !!! note
        If you use a compiled regex pattern, the python-re engine will be used regardless of this setting.
        This is so that flags such as `re.IGNORECASE` are respected.

    ```python
    from pydantic import BaseModel, ConfigDict, Field, ValidationError

    class Model(BaseModel):
        model_config = ConfigDict(regex_engine='python-re')

        value: str = Field(pattern=r'^abc(?=def)')

    print(Model(value='abcdef').value)
    #> abcdef

    try:
        print(Model(value='abxyzcdef'))
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        value
          String should match pattern '^abc(?=def)' [type=string_pattern_mismatch, input_value='abxyzcdef', input_type=str]
        '''
    ```
    """

    validation_error_cause: bool
    """
    If `True`, Python exceptions that were part of a validation failure will be shown as an exception group as a cause. Can be useful for debugging. Defaults to `False`.

    Note:
        Python 3.10 and older don't support exception groups natively. <=3.10, backport must be installed: `pip install exceptiongroup`.

    Note:
        The structure of validation errors are likely to change in future Pydantic versions. Pydantic offers no guarantees about their structure. Should be used for visual traceback debugging only.
    """

    use_attribute_docstrings: bool
    '''
    Whether docstrings of attributes (bare string literals immediately following the attribute declaration)
    should be used for field descriptions. Defaults to `False`.

    Available in Pydantic v2.7+.

    ```python
    from pydantic import BaseModel, ConfigDict, Field


    class Model(BaseModel):
        model_config = ConfigDict(use_attribute_docstrings=True)

        x: str
        """
        Example of an attribute docstring
        """

        y: int = Field(description="Description in Field")
        """
        Description in Field overrides attribute docstring
        """


    print(Model.model_fields["x"].description)
    # > Example of an attribute docstring
    print(Model.model_fields["y"].description)
    # > Description in Field
    ```
    This requires the source code of the class to be available at runtime.

    !!! warning "Usage with `TypedDict` and stdlib dataclasses"
        Due to current limitations, attribute docstrings detection may not work as expected when using
        [`TypedDict`][typing.TypedDict] and stdlib dataclasses, in particular when:

        - inheritance is being used.
        - multiple classes have the same name in the same source file.
    '''

    cache_strings: bool | Literal['all', 'keys', 'none']
    """
    Whether to cache strings to avoid constructing new Python objects. Defaults to True.

    Enabling this setting should significantly improve validation performance while increasing memory usage slightly.

    - `True` or `'all'` (the default): cache all strings
    - `'keys'`: cache only dictionary keys
    - `False` or `'none'`: no caching

    !!! note
        `True` or `'all'` is required to cache strings during general validation because
        validators don't know if they're in a key or a value.

    !!! tip
        If repeated strings are rare, it's recommended to use `'keys'` or `'none'` to reduce memory usage,
        as the performance difference is minimal if repeated strings are rare.
    """

    validate_by_alias: bool
    """
    Whether an aliased field may be populated by its alias. Defaults to `True`.

    !!! note
        In v2.11, `validate_by_alias` was introduced in conjunction with [`validate_by_name`][pydantic.ConfigDict.validate_by_name]
        to empower users with more fine grained validation control. In <v2.11, disabling validation by alias was not possible.

    Here's an example of disabling validation by alias:

    ```py
    from pydantic import BaseModel, ConfigDict, Field

    class Model(BaseModel):
        model_config = ConfigDict(validate_by_name=True, validate_by_alias=False)

        my_field: str = Field(validation_alias='my_alias')  # (1)!

    m = Model(my_field='foo')  # (2)!
    print(m)
    #> my_field='foo'
    ```

    1. The field `'my_field'` has an alias `'my_alias'`.
    2. The model can only be populated by the attribute name `'my_field'`.

    !!! warning
        You cannot set both `validate_by_alias` and `validate_by_name` to `False`.
        This would make it impossible to populate an attribute.

        See [usage errors](../errors/usage_errors.md#validate-by-alias-and-name-false) for an example.

        If you set `validate_by_alias` to `False`, under the hood, Pydantic dynamically sets
        `validate_by_name` to `True` to ensure that validation can still occur.
    """

    validate_by_name: bool
    """
    Whether an aliased field may be populated by its name as given by the model
    attribute. Defaults to `False`.

    !!! note
        In v2.0-v2.10, the `populate_by_name` configuration setting was used to specify
        whether or not a field could be populated by its name **and** alias.

        In v2.11, `validate_by_name` was introduced in conjunction with [`validate_by_alias`][pydantic.ConfigDict.validate_by_alias]
        to empower users with more fine grained validation behavior control.

    ```python
    from pydantic import BaseModel, ConfigDict, Field

    class Model(BaseModel):
        model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

        my_field: str = Field(validation_alias='my_alias')  # (1)!

    m = Model(my_alias='foo')  # (2)!
    print(m)
    #> my_field='foo'

    m = Model(my_field='foo')  # (3)!
    print(m)
    #> my_field='foo'
    ```

    1. The field `'my_field'` has an alias `'my_alias'`.
    2. The model is populated by the alias `'my_alias'`.
    3. The model is populated by the attribute name `'my_field'`.

    !!! warning
        You cannot set both `validate_by_alias` and `validate_by_name` to `False`.
        This would make it impossible to populate an attribute.

        See [usage errors](../errors/usage_errors.md#validate-by-alias-and-name-false) for an example.
    """

    serialize_by_alias: bool
    """
    Whether an aliased field should be serialized by its alias. Defaults to `False`.

    Note: In v2.11, `serialize_by_alias` was introduced to address the
    [popular request](https://github.com/pydantic/pydantic/issues/8379)
    for consistency with alias behavior for validation and serialization settings.
    In v3, the default value is expected to change to `True` for consistency with the validation default.

    ```python
    from pydantic import BaseModel, ConfigDict, Field

    class Model(BaseModel):
        model_config = ConfigDict(serialize_by_alias=True)

        my_field: str = Field(serialization_alias='my_alias')  # (1)!

    m = Model(my_field='foo')
    print(m.model_dump())  # (2)!
    #> {'my_alias': 'foo'}
    ```

    1. The field `'my_field'` has an alias `'my_alias'`.
    2. The model is serialized using the alias `'my_alias'` for the `'my_field'` attribute.
    """


_TypeT = TypeVar('_TypeT', bound=type)


@overload
@deprecated('Passing `config` as a keyword argument is deprecated. Pass `config` as a positional argument instead.')
def with_config(*, config: ConfigDict) -> Callable[[_TypeT], _TypeT]: ...


@overload
def with_config(config: ConfigDict, /) -> Callable[[_TypeT], _TypeT]: ...


@overload
def with_config(**config: Unpack[ConfigDict]) -> Callable[[_TypeT], _TypeT]: ...


def with_config(config: ConfigDict | None = None, /, **kwargs: Any) -> Callable[[_TypeT], _TypeT]:
    """!!! abstract "Usage Documentation"
        [Configuration with other types](../concepts/config.md#configuration-on-other-supported-types)

    A convenience decorator to set a [Pydantic configuration](config.md) on a `TypedDict` or a `dataclass` from the standard library.

    Although the configuration can be set using the `__pydantic_config__` attribute, it does not play well with type checkers,
    especially with `TypedDict`.

    !!! example "Usage"

        ```python
        from typing_extensions import TypedDict

        from pydantic import ConfigDict, TypeAdapter, with_config

        @with_config(ConfigDict(str_to_lower=True))
        class TD(TypedDict):
            x: str

        ta = TypeAdapter(TD)

        print(ta.validate_python({'x': 'ABC'}))
        #> {'x': 'abc'}
        ```
    """
    if config is not None and kwargs:
        raise ValueError('Cannot specify both `config` and keyword arguments')

    if len(kwargs) == 1 and (kwargs_conf := kwargs.get('config')) is not None:
        warnings.warn(
            'Passing `config` as a keyword argument is deprecated. Pass `config` as a positional argument instead',
            category=PydanticDeprecatedSince211,
            stacklevel=2,
        )
        final_config = cast(ConfigDict, kwargs_conf)
    else:
        final_config = config if config is not None else cast(ConfigDict, kwargs)

    def inner(class_: _TypeT, /) -> _TypeT:
        # Ideally, we would check for `class_` to either be a `TypedDict` or a stdlib dataclass.
        # However, the `@with_config` decorator can be applied *after* `@dataclass`. To avoid
        # common mistakes, we at least check for `class_` to not be a Pydantic model.
        from ._internal._utils import is_model_class

        if is_model_class(class_):
            raise PydanticUserError(
                f'Cannot use `with_config` on {class_.__name__} as it is a Pydantic model',
                code='with-config-on-model',
            )
        class_.__pydantic_config__ = final_config
        return class_

    return inner


__getattr__ = getattr_migration(__name__)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\interpolatable.py ===
"""
Tool to find wrong contour order between different masters, and
other interpolatability (or lack thereof) issues.

Call as:
$ fonttools varLib.interpolatable font1 font2 ...
"""

from .interpolatableHelpers import *
from .interpolatableTestContourOrder import test_contour_order
from .interpolatableTestStartingPoint import test_starting_point
from fontTools.pens.recordingPen import (
    RecordingPen,
    DecomposingRecordingPen,
    lerpRecordings,
)
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.statisticsPen import StatisticsPen, StatisticsControlPen
from fontTools.pens.momentsPen import OpenContourError
from fontTools.varLib.models import piecewiseLinearMap, normalizeLocation
from fontTools.misc.fixedTools import floatToFixedToStr
from fontTools.misc.transform import Transform
from collections import defaultdict
from types import SimpleNamespace
from functools import wraps
from pprint import pformat
from math import sqrt, atan2, pi
import logging
import os

log = logging.getLogger("fontTools.varLib.interpolatable")

DEFAULT_TOLERANCE = 0.95
DEFAULT_KINKINESS = 0.5
DEFAULT_KINKINESS_LENGTH = 0.002  # ratio of UPEM
DEFAULT_UPEM = 1000


class Glyph:
    ITEMS = (
        "recordings",
        "greenStats",
        "controlStats",
        "greenVectors",
        "controlVectors",
        "nodeTypes",
        "isomorphisms",
        "points",
        "openContours",
    )

    def __init__(self, glyphname, glyphset):
        self.name = glyphname
        for item in self.ITEMS:
            setattr(self, item, [])
        self._populate(glyphset)

    def _fill_in(self, ix):
        for item in self.ITEMS:
            if len(getattr(self, item)) == ix:
                getattr(self, item).append(None)

    def _populate(self, glyphset):
        glyph = glyphset[self.name]
        self.doesnt_exist = glyph is None
        if self.doesnt_exist:
            return

        perContourPen = PerContourOrComponentPen(RecordingPen, glyphset=glyphset)
        try:
            glyph.draw(perContourPen, outputImpliedClosingLine=True)
        except TypeError:
            glyph.draw(perContourPen)
        self.recordings = perContourPen.value
        del perContourPen

        for ix, contour in enumerate(self.recordings):
            nodeTypes = [op for op, arg in contour.value]
            self.nodeTypes.append(nodeTypes)

            greenStats = StatisticsPen(glyphset=glyphset)
            controlStats = StatisticsControlPen(glyphset=glyphset)
            try:
                contour.replay(greenStats)
                contour.replay(controlStats)
                self.openContours.append(False)
            except OpenContourError as e:
                self.openContours.append(True)
                self._fill_in(ix)
                continue
            self.greenStats.append(greenStats)
            self.controlStats.append(controlStats)
            self.greenVectors.append(contour_vector_from_stats(greenStats))
            self.controlVectors.append(contour_vector_from_stats(controlStats))

            # Check starting point
            if nodeTypes[0] == "addComponent":
                self._fill_in(ix)
                continue

            assert nodeTypes[0] == "moveTo"
            assert nodeTypes[-1] in ("closePath", "endPath")
            points = SimpleRecordingPointPen()
            converter = SegmentToPointPen(points, False)
            contour.replay(converter)
            # points.value is a list of pt,bool where bool is true if on-curve and false if off-curve;
            # now check all rotations and mirror-rotations of the contour and build list of isomorphic
            # possible starting points.
            self.points.append(points.value)

            isomorphisms = []
            self.isomorphisms.append(isomorphisms)

            # Add rotations
            add_isomorphisms(points.value, isomorphisms, False)
            # Add mirrored rotations
            add_isomorphisms(points.value, isomorphisms, True)

    def draw(self, pen, countor_idx=None):
        if countor_idx is None:
            for contour in self.recordings:
                contour.draw(pen)
        else:
            self.recordings[countor_idx].draw(pen)


def test_gen(
    glyphsets,
    glyphs=None,
    names=None,
    ignore_missing=False,
    *,
    locations=None,
    tolerance=DEFAULT_TOLERANCE,
    kinkiness=DEFAULT_KINKINESS,
    upem=DEFAULT_UPEM,
    show_all=False,
    discrete_axes=[],
):
    if tolerance >= 10:
        tolerance *= 0.01
    assert 0 <= tolerance <= 1
    if kinkiness >= 10:
        kinkiness *= 0.01
    assert 0 <= kinkiness

    names = names or [repr(g) for g in glyphsets]

    if glyphs is None:
        # `glyphs = glyphsets[0].keys()` is faster, certainly, but doesn't allow for sparse TTFs/OTFs given out of order
        # ... risks the sparse master being the first one, and only processing a subset of the glyphs
        glyphs = {g for glyphset in glyphsets for g in glyphset.keys()}

    parents, order = find_parents_and_order(
        glyphsets, locations, discrete_axes=discrete_axes
    )

    def grand_parent(i, glyphname):
        if i is None:
            return None
        i = parents[i]
        if i is None:
            return None
        while parents[i] is not None and glyphsets[i][glyphname] is None:
            i = parents[i]
        return i

    for glyph_name in glyphs:
        log.info("Testing glyph %s", glyph_name)
        allGlyphs = [Glyph(glyph_name, glyphset) for glyphset in glyphsets]
        if len([1 for glyph in allGlyphs if glyph is not None]) <= 1:
            continue
        for master_idx, (glyph, glyphset, name) in enumerate(
            zip(allGlyphs, glyphsets, names)
        ):
            if glyph.doesnt_exist:
                if not ignore_missing:
                    yield (
                        glyph_name,
                        {
                            "type": InterpolatableProblem.MISSING,
                            "master": name,
                            "master_idx": master_idx,
                        },
                    )
                continue

            has_open = False
            for ix, open in enumerate(glyph.openContours):
                if not open:
                    continue
                has_open = True
                yield (
                    glyph_name,
                    {
                        "type": InterpolatableProblem.OPEN_PATH,
                        "master": name,
                        "master_idx": master_idx,
                        "contour": ix,
                    },
                )
            if has_open:
                continue

        matchings = [None] * len(glyphsets)

        for m1idx in order:
            glyph1 = allGlyphs[m1idx]
            if glyph1 is None or not glyph1.nodeTypes:
                continue
            m0idx = grand_parent(m1idx, glyph_name)
            if m0idx is None:
                continue
            glyph0 = allGlyphs[m0idx]
            if glyph0 is None or not glyph0.nodeTypes:
                continue

            #
            # Basic compatibility checks
            #

            m1 = glyph0.nodeTypes
            m0 = glyph1.nodeTypes
            if len(m0) != len(m1):
                yield (
                    glyph_name,
                    {
                        "type": InterpolatableProblem.PATH_COUNT,
                        "master_1": names[m0idx],
                        "master_2": names[m1idx],
                        "master_1_idx": m0idx,
                        "master_2_idx": m1idx,
                        "value_1": len(m0),
                        "value_2": len(m1),
                    },
                )
                continue

            if m0 != m1:
                for pathIx, (nodes1, nodes2) in enumerate(zip(m0, m1)):
                    if nodes1 == nodes2:
                        continue
                    if len(nodes1) != len(nodes2):
                        yield (
                            glyph_name,
                            {
                                "type": InterpolatableProblem.NODE_COUNT,
                                "path": pathIx,
                                "master_1": names[m0idx],
                                "master_2": names[m1idx],
                                "master_1_idx": m0idx,
                                "master_2_idx": m1idx,
                                "value_1": len(nodes1),
                                "value_2": len(nodes2),
                            },
                        )
                        continue
                    for nodeIx, (n1, n2) in enumerate(zip(nodes1, nodes2)):
                        if n1 != n2:
                            yield (
                                glyph_name,
                                {
                                    "type": InterpolatableProblem.NODE_INCOMPATIBILITY,
                                    "path": pathIx,
                                    "node": nodeIx,
                                    "master_1": names[m0idx],
                                    "master_2": names[m1idx],
                                    "master_1_idx": m0idx,
                                    "master_2_idx": m1idx,
                                    "value_1": n1,
                                    "value_2": n2,
                                },
                            )
                            continue

            #
            # InterpolatableProblem.CONTOUR_ORDER check
            #

            this_tolerance, matching = test_contour_order(glyph0, glyph1)
            if this_tolerance < tolerance:
                yield (
                    glyph_name,
                    {
                        "type": InterpolatableProblem.CONTOUR_ORDER,
                        "master_1": names[m0idx],
                        "master_2": names[m1idx],
                        "master_1_idx": m0idx,
                        "master_2_idx": m1idx,
                        "value_1": list(range(len(matching))),
                        "value_2": matching,
                        "tolerance": this_tolerance,
                    },
                )
                matchings[m1idx] = matching

            #
            # wrong-start-point / weight check
            #

            m0Isomorphisms = glyph0.isomorphisms
            m1Isomorphisms = glyph1.isomorphisms
            m0Vectors = glyph0.greenVectors
            m1Vectors = glyph1.greenVectors
            recording0 = glyph0.recordings
            recording1 = glyph1.recordings

            # If contour-order is wrong, adjust it
            matching = matchings[m1idx]
            if (
                matching is not None and m1Isomorphisms
            ):  # m1 is empty for composite glyphs
                m1Isomorphisms = [m1Isomorphisms[i] for i in matching]
                m1Vectors = [m1Vectors[i] for i in matching]
                recording1 = [recording1[i] for i in matching]

            midRecording = []
            for c0, c1 in zip(recording0, recording1):
                try:
                    r = RecordingPen()
                    r.value = list(lerpRecordings(c0.value, c1.value))
                    midRecording.append(r)
                except ValueError:
                    # Mismatch because of the reordering above
                    midRecording.append(None)

            for ix, (contour0, contour1) in enumerate(
                zip(m0Isomorphisms, m1Isomorphisms)
            ):
                if (
                    contour0 is None
                    or contour1 is None
                    or len(contour0) == 0
                    or len(contour0) != len(contour1)
                ):
                    # We already reported this; or nothing to do; or not compatible
                    # after reordering above.
                    continue

                this_tolerance, proposed_point, reverse = test_starting_point(
                    glyph0, glyph1, ix, tolerance, matching
                )

                if this_tolerance < tolerance:
                    yield (
                        glyph_name,
                        {
                            "type": InterpolatableProblem.WRONG_START_POINT,
                            "contour": ix,
                            "master_1": names[m0idx],
                            "master_2": names[m1idx],
                            "master_1_idx": m0idx,
                            "master_2_idx": m1idx,
                            "value_1": 0,
                            "value_2": proposed_point,
                            "reversed": reverse,
                            "tolerance": this_tolerance,
                        },
                    )

                # Weight check.
                #
                # If contour could be mid-interpolated, and the two
                # contours have the same area sign, proceeed.
                #
                # The sign difference can happen if it's a weirdo
                # self-intersecting contour; ignore it.
                contour = midRecording[ix]

                if contour and (m0Vectors[ix][0] < 0) == (m1Vectors[ix][0] < 0):
                    midStats = StatisticsPen(glyphset=None)
                    contour.replay(midStats)

                    midVector = contour_vector_from_stats(midStats)

                    m0Vec = m0Vectors[ix]
                    m1Vec = m1Vectors[ix]
                    size0 = m0Vec[0] * m0Vec[0]
                    size1 = m1Vec[0] * m1Vec[0]
                    midSize = midVector[0] * midVector[0]

                    for overweight, problem_type in enumerate(
                        (
                            InterpolatableProblem.UNDERWEIGHT,
                            InterpolatableProblem.OVERWEIGHT,
                        )
                    ):
                        if overweight:
                            expectedSize = max(size0, size1)
                            continue
                        else:
                            expectedSize = sqrt(size0 * size1)

                        log.debug(
                            "%s: actual size %g; threshold size %g, master sizes: %g, %g",
                            problem_type,
                            midSize,
                            expectedSize,
                            size0,
                            size1,
                        )

                        if (
                            not overweight and expectedSize * tolerance > midSize + 1e-5
                        ) or (overweight and 1e-5 + expectedSize / tolerance < midSize):
                            try:
                                if overweight:
                                    this_tolerance = expectedSize / midSize
                                else:
                                    this_tolerance = midSize / expectedSize
                            except ZeroDivisionError:
                                this_tolerance = 0
                            log.debug("tolerance %g", this_tolerance)
                            yield (
                                glyph_name,
                                {
                                    "type": problem_type,
                                    "contour": ix,
                                    "master_1": names[m0idx],
                                    "master_2": names[m1idx],
                                    "master_1_idx": m0idx,
                                    "master_2_idx": m1idx,
                                    "tolerance": this_tolerance,
                                },
                            )

            #
            # "kink" detector
            #
            m0 = glyph0.points
            m1 = glyph1.points

            # If contour-order is wrong, adjust it
            if matchings[m1idx] is not None and m1:  # m1 is empty for composite glyphs
                m1 = [m1[i] for i in matchings[m1idx]]

            t = 0.1  # ~sin(radian(6)) for tolerance 0.95
            deviation_threshold = (
                upem * DEFAULT_KINKINESS_LENGTH * DEFAULT_KINKINESS / kinkiness
            )

            for ix, (contour0, contour1) in enumerate(zip(m0, m1)):
                if (
                    contour0 is None
                    or contour1 is None
                    or len(contour0) == 0
                    or len(contour0) != len(contour1)
                ):
                    # We already reported this; or nothing to do; or not compatible
                    # after reordering above.
                    continue

                # Walk the contour, keeping track of three consecutive points, with
                # middle one being an on-curve. If the three are co-linear then
                # check for kinky-ness.
                for i in range(len(contour0)):
                    pt0 = contour0[i]
                    pt1 = contour1[i]
                    if not pt0[1] or not pt1[1]:
                        # Skip off-curves
                        continue
                    pt0_prev = contour0[i - 1]
                    pt1_prev = contour1[i - 1]
                    pt0_next = contour0[(i + 1) % len(contour0)]
                    pt1_next = contour1[(i + 1) % len(contour1)]

                    if pt0_prev[1] and pt1_prev[1]:
                        # At least one off-curve is required
                        continue
                    if pt0_prev[1] and pt1_prev[1]:
                        # At least one off-curve is required
                        continue

                    pt0 = complex(*pt0[0])
                    pt1 = complex(*pt1[0])
                    pt0_prev = complex(*pt0_prev[0])
                    pt1_prev = complex(*pt1_prev[0])
                    pt0_next = complex(*pt0_next[0])
                    pt1_next = complex(*pt1_next[0])

                    # We have three consecutive points. Check whether
                    # they are colinear.
                    d0_prev = pt0 - pt0_prev
                    d0_next = pt0_next - pt0
                    d1_prev = pt1 - pt1_prev
                    d1_next = pt1_next - pt1

                    sin0 = d0_prev.real * d0_next.imag - d0_prev.imag * d0_next.real
                    sin1 = d1_prev.real * d1_next.imag - d1_prev.imag * d1_next.real
                    try:
                        sin0 /= abs(d0_prev) * abs(d0_next)
                        sin1 /= abs(d1_prev) * abs(d1_next)
                    except ZeroDivisionError:
                        continue

                    if abs(sin0) > t or abs(sin1) > t:
                        # Not colinear / not smooth.
                        continue

                    # Check the mid-point is actually, well, in the middle.
                    dot0 = d0_prev.real * d0_next.real + d0_prev.imag * d0_next.imag
                    dot1 = d1_prev.real * d1_next.real + d1_prev.imag * d1_next.imag
                    if dot0 < 0 or dot1 < 0:
                        # Sharp corner.
                        continue

                    # Fine, if handle ratios are similar...
                    r0 = abs(d0_prev) / (abs(d0_prev) + abs(d0_next))
                    r1 = abs(d1_prev) / (abs(d1_prev) + abs(d1_next))
                    r_diff = abs(r0 - r1)
                    if abs(r_diff) < t:
                        # Smooth enough.
                        continue

                    mid = (pt0 + pt1) / 2
                    mid_prev = (pt0_prev + pt1_prev) / 2
                    mid_next = (pt0_next + pt1_next) / 2

                    mid_d0 = mid - mid_prev
                    mid_d1 = mid_next - mid

                    sin_mid = mid_d0.real * mid_d1.imag - mid_d0.imag * mid_d1.real
                    try:
                        sin_mid /= abs(mid_d0) * abs(mid_d1)
                    except ZeroDivisionError:
                        continue

                    # ...or if the angles are similar.
                    if abs(sin_mid) * (tolerance * kinkiness) <= t:
                        # Smooth enough.
                        continue

                    # How visible is the kink?

                    cross = sin_mid * abs(mid_d0) * abs(mid_d1)
                    arc_len = abs(mid_d0 + mid_d1)
                    deviation = abs(cross / arc_len)
                    if deviation < deviation_threshold:
                        continue
                    deviation_ratio = deviation / arc_len
                    if deviation_ratio > t:
                        continue

                    this_tolerance = t / (abs(sin_mid) * kinkiness)

                    log.debug(
                        "kink: deviation %g; deviation_ratio %g; sin_mid %g; r_diff %g",
                        deviation,
                        deviation_ratio,
                        sin_mid,
                        r_diff,
                    )
                    log.debug("tolerance %g", this_tolerance)
                    yield (
                        glyph_name,
                        {
                            "type": InterpolatableProblem.KINK,
                            "contour": ix,
                            "master_1": names[m0idx],
                            "master_2": names[m1idx],
                            "master_1_idx": m0idx,
                            "master_2_idx": m1idx,
                            "value": i,
                            "tolerance": this_tolerance,
                        },
                    )

            #
            # --show-all
            #

            if show_all:
                yield (
                    glyph_name,
                    {
                        "type": InterpolatableProblem.NOTHING,
                        "master_1": names[m0idx],
                        "master_2": names[m1idx],
                        "master_1_idx": m0idx,
                        "master_2_idx": m1idx,
                    },
                )


@wraps(test_gen)
def test(*args, **kwargs):
    problems = defaultdict(list)
    for glyphname, problem in test_gen(*args, **kwargs):
        problems[glyphname].append(problem)
    return problems


def recursivelyAddGlyph(glyphname, glyphset, ttGlyphSet, glyf):
    if glyphname in glyphset:
        return
    glyphset[glyphname] = ttGlyphSet[glyphname]

    for component in getattr(glyf[glyphname], "components", []):
        recursivelyAddGlyph(component.glyphName, glyphset, ttGlyphSet, glyf)


def ensure_parent_dir(path):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    return path


def main(args=None):
    """Test for interpolatability issues between fonts"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        "fonttools varLib.interpolatable",
        description=main.__doc__,
    )
    parser.add_argument(
        "--glyphs",
        action="store",
        help="Space-separate name of glyphs to check",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all glyph pairs, even if no problems are found",
    )
    parser.add_argument(
        "--tolerance",
        action="store",
        type=float,
        help="Error tolerance. Between 0 and 1. Default %s" % DEFAULT_TOLERANCE,
    )
    parser.add_argument(
        "--kinkiness",
        action="store",
        type=float,
        help="How aggressively report kinks. Default %s" % DEFAULT_KINKINESS,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format",
    )
    parser.add_argument(
        "--pdf",
        action="store",
        help="Output report in PDF format",
    )
    parser.add_argument(
        "--ps",
        action="store",
        help="Output report in PostScript format",
    )
    parser.add_argument(
        "--html",
        action="store",
        help="Output report in HTML format",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only exit with code 1 or 0, no output",
    )
    parser.add_argument(
        "--output",
        action="store",
        help="Output file for the problem report; Default: stdout",
    )
    parser.add_argument(
        "--ignore-missing",
        action="store_true",
        help="Will not report glyphs missing from sparse masters as errors",
    )
    parser.add_argument(
        "inputs",
        metavar="FILE",
        type=str,
        nargs="+",
        help="Input a single variable font / DesignSpace / Glyphs file, or multiple TTF/UFO files",
    )
    parser.add_argument(
        "--name",
        metavar="NAME",
        type=str,
        action="append",
        help="Name of the master to use in the report. If not provided, all are used.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Run verbosely.")
    parser.add_argument("--debug", action="store_true", help="Run with debug output.")

    args = parser.parse_args(args)

    from fontTools import configLogger

    configLogger(level=("INFO" if args.verbose else "WARNING"))
    if args.debug:
        configLogger(level="DEBUG")

    glyphs = args.glyphs.split() if args.glyphs else None

    from os.path import basename

    fonts = []
    names = []
    locations = []
    discrete_axes = set()
    upem = DEFAULT_UPEM

    original_args_inputs = tuple(args.inputs)

    if len(args.inputs) == 1:
        designspace = None
        if args.inputs[0].endswith(".designspace"):
            from fontTools.designspaceLib import DesignSpaceDocument

            designspace = DesignSpaceDocument.fromfile(args.inputs[0])
            args.inputs = [master.path for master in designspace.sources]
            locations = [master.location for master in designspace.sources]
            discrete_axes = {
                a.name for a in designspace.axes if not hasattr(a, "minimum")
            }
            axis_triples = {
                a.name: (a.minimum, a.default, a.maximum)
                for a in designspace.axes
                if a.name not in discrete_axes
            }
            axis_mappings = {a.name: a.map for a in designspace.axes}
            axis_triples = {
                k: tuple(piecewiseLinearMap(v, dict(axis_mappings[k])) for v in vv)
                for k, vv in axis_triples.items()
            }

        elif args.inputs[0].endswith((".glyphs", ".glyphspackage")):
            from glyphsLib import GSFont, to_designspace

            gsfont = GSFont(args.inputs[0])
            upem = gsfont.upm
            designspace = to_designspace(gsfont)
            fonts = [source.font for source in designspace.sources]
            names = ["%s-%s" % (f.info.familyName, f.info.styleName) for f in fonts]
            args.inputs = []
            locations = [master.location for master in designspace.sources]
            axis_triples = {
                a.name: (a.minimum, a.default, a.maximum) for a in designspace.axes
            }
            axis_mappings = {a.name: a.map for a in designspace.axes}
            axis_triples = {
                k: tuple(piecewiseLinearMap(v, dict(axis_mappings[k])) for v in vv)
                for k, vv in axis_triples.items()
            }

        elif args.inputs[0].endswith(".ttf") or args.inputs[0].endswith(".otf"):
            from fontTools.ttLib import TTFont

            # Is variable font?

            font = TTFont(args.inputs[0])
            upem = font["head"].unitsPerEm

            fvar = font["fvar"]
            axisMapping = {}
            for axis in fvar.axes:
                axisMapping[axis.axisTag] = {
                    -1: axis.minValue,
                    0: axis.defaultValue,
                    1: axis.maxValue,
                }
            normalized = False
            if "avar" in font:
                avar = font["avar"]
                if getattr(avar.table, "VarStore", None):
                    axisMapping = {tag: {-1: -1, 0: 0, 1: 1} for tag in axisMapping}
                    normalized = True
                else:
                    for axisTag, segments in avar.segments.items():
                        fvarMapping = axisMapping[axisTag].copy()
                        for location, value in segments.items():
                            axisMapping[axisTag][value] = piecewiseLinearMap(
                                location, fvarMapping
                            )

            # Gather all glyphs at their "master" locations
            ttGlyphSets = {}
            glyphsets = defaultdict(dict)

            if "gvar" in font:
                gvar = font["gvar"]
                glyf = font["glyf"]

                if glyphs is None:
                    glyphs = sorted(gvar.variations.keys())
                for glyphname in glyphs:
                    for var in gvar.variations[glyphname]:
                        locDict = {}
                        loc = []
                        for tag, val in sorted(var.axes.items()):
                            locDict[tag] = val[1]
                            loc.append((tag, val[1]))

                        locTuple = tuple(loc)
                        if locTuple not in ttGlyphSets:
                            ttGlyphSets[locTuple] = font.getGlyphSet(
                                location=locDict, normalized=True, recalcBounds=False
                            )

                        recursivelyAddGlyph(
                            glyphname, glyphsets[locTuple], ttGlyphSets[locTuple], glyf
                        )

            elif "CFF2" in font:
                fvarAxes = font["fvar"].axes
                cff2 = font["CFF2"].cff.topDictIndex[0]
                charstrings = cff2.CharStrings

                if glyphs is None:
                    glyphs = sorted(charstrings.keys())
                for glyphname in glyphs:
                    cs = charstrings[glyphname]
                    private = cs.private

                    # Extract vsindex for the glyph
                    vsindices = {getattr(private, "vsindex", 0)}
                    vsindex = getattr(private, "vsindex", 0)
                    last_op = 0
                    # The spec says vsindex can only appear once and must be the first
                    # operator in the charstring, but we support multiple.
                    # https://github.com/harfbuzz/boring-expansion-spec/issues/158
                    for op in enumerate(cs.program):
                        if op == "blend":
                            vsindices.add(vsindex)
                        elif op == "vsindex":
                            assert isinstance(last_op, int)
                            vsindex = last_op
                        last_op = op

                    if not hasattr(private, "vstore"):
                        continue

                    varStore = private.vstore.otVarStore
                    for vsindex in vsindices:
                        varData = varStore.VarData[vsindex]
                        for regionIndex in varData.VarRegionIndex:
                            region = varStore.VarRegionList.Region[regionIndex]

                            locDict = {}
                            loc = []
                            for axisIndex, axis in enumerate(region.VarRegionAxis):
                                tag = fvarAxes[axisIndex].axisTag
                                val = axis.PeakCoord
                                locDict[tag] = val
                                loc.append((tag, val))

                            locTuple = tuple(loc)
                            if locTuple not in ttGlyphSets:
                                ttGlyphSets[locTuple] = font.getGlyphSet(
                                    location=locDict,
                                    normalized=True,
                                    recalcBounds=False,
                                )

                            glyphset = glyphsets[locTuple]
                            glyphset[glyphname] = ttGlyphSets[locTuple][glyphname]

            names = ["''"]
            fonts = [font.getGlyphSet()]
            locations = [{}]
            axis_triples = {a: (-1, 0, +1) for a in sorted(axisMapping.keys())}
            for locTuple in sorted(glyphsets.keys(), key=lambda v: (len(v), v)):
                name = (
                    "'"
                    + " ".join(
                        "%s=%s"
                        % (
                            k,
                            floatToFixedToStr(
                                piecewiseLinearMap(v, axisMapping[k]), 14
                            ),
                        )
                        for k, v in locTuple
                    )
                    + "'"
                )
                if normalized:
                    name += " (normalized)"
                names.append(name)
                fonts.append(glyphsets[locTuple])
                locations.append(dict(locTuple))

            args.ignore_missing = True
            args.inputs = []

    if not locations:
        locations = [{} for _ in fonts]

    for filename in args.inputs:
        if filename.endswith(".ufo"):
            from fontTools.ufoLib import UFOReader

            font = UFOReader(filename)
            info = SimpleNamespace()
            font.readInfo(info)
            upem = info.unitsPerEm
            fonts.append(font)
        else:
            from fontTools.ttLib import TTFont

            font = TTFont(filename)
            upem = font["head"].unitsPerEm
            fonts.append(font)

        names.append(basename(filename).rsplit(".", 1)[0])

    if len(fonts) < 2:
        log.warning("Font file does not seem to be variable. Nothing to check.")
        return

    glyphsets = []
    for font in fonts:
        if hasattr(font, "getGlyphSet"):
            glyphset = font.getGlyphSet()
        else:
            glyphset = font
        glyphsets.append({k: glyphset[k] for k in glyphset.keys()})

    if args.name:
        accepted_names = set(args.name)
        glyphsets = [
            glyphset
            for name, glyphset in zip(names, glyphsets)
            if name in accepted_names
        ]
        locations = [
            location
            for name, location in zip(names, locations)
            if name in accepted_names
        ]
        names = [name for name in names if name in accepted_names]

    if not glyphs:
        glyphs = sorted(set([gn for glyphset in glyphsets for gn in glyphset.keys()]))

    glyphsSet = set(glyphs)
    for glyphset in glyphsets:
        glyphSetGlyphNames = set(glyphset.keys())
        diff = glyphsSet - glyphSetGlyphNames
        if diff:
            for gn in diff:
                glyphset[gn] = None

    # Normalize locations
    locations = [
        {
            **normalizeLocation(loc, axis_triples),
            **{k: v for k, v in loc.items() if k in discrete_axes},
        }
        for loc in locations
    ]
    tolerance = args.tolerance or DEFAULT_TOLERANCE
    kinkiness = args.kinkiness if args.kinkiness is not None else DEFAULT_KINKINESS

    try:
        log.info("Running on %d glyphsets", len(glyphsets))
        log.info("Locations: %s", pformat(locations))
        problems_gen = test_gen(
            glyphsets,
            glyphs=glyphs,
            names=names,
            locations=locations,
            upem=upem,
            ignore_missing=args.ignore_missing,
            tolerance=tolerance,
            kinkiness=kinkiness,
            show_all=args.show_all,
            discrete_axes=discrete_axes,
        )
        problems = defaultdict(list)

        f = (
            sys.stdout
            if args.output is None
            else open(ensure_parent_dir(args.output), "w")
        )

        if not args.quiet:
            if args.json:
                import json

                for glyphname, problem in problems_gen:
                    problems[glyphname].append(problem)

                print(json.dumps(problems), file=f)
            else:
                last_glyphname = None
                for glyphname, p in problems_gen:
                    problems[glyphname].append(p)

                    if glyphname != last_glyphname:
                        print(f"Glyph {glyphname} was not compatible:", file=f)
                        last_glyphname = glyphname
                        last_master_idxs = None

                    master_idxs = (
                        (p["master_idx"],)
                        if "master_idx" in p
                        else (p["master_1_idx"], p["master_2_idx"])
                    )
                    if master_idxs != last_master_idxs:
                        master_names = (
                            (p["master"],)
                            if "master" in p
                            else (p["master_1"], p["master_2"])
                        )
                        print(f"  Masters: %s:" % ", ".join(master_names), file=f)
                        last_master_idxs = master_idxs

                    if p["type"] == InterpolatableProblem.MISSING:
                        print(
                            "    Glyph was missing in master %s" % p["master"], file=f
                        )
                    elif p["type"] == InterpolatableProblem.OPEN_PATH:
                        print(
                            "    Glyph has an open path in master %s" % p["master"],
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.PATH_COUNT:
                        print(
                            "    Path count differs: %i in %s, %i in %s"
                            % (
                                p["value_1"],
                                p["master_1"],
                                p["value_2"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.NODE_COUNT:
                        print(
                            "    Node count differs in path %i: %i in %s, %i in %s"
                            % (
                                p["path"],
                                p["value_1"],
                                p["master_1"],
                                p["value_2"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.NODE_INCOMPATIBILITY:
                        print(
                            "    Node %o incompatible in path %i: %s in %s, %s in %s"
                            % (
                                p["node"],
                                p["path"],
                                p["value_1"],
                                p["master_1"],
                                p["value_2"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.CONTOUR_ORDER:
                        print(
                            "    Contour order differs: %s in %s, %s in %s"
                            % (
                                p["value_1"],
                                p["master_1"],
                                p["value_2"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.WRONG_START_POINT:
                        print(
                            "    Contour %d start point differs: %s in %s, %s in %s; reversed: %s"
                            % (
                                p["contour"],
                                p["value_1"],
                                p["master_1"],
                                p["value_2"],
                                p["master_2"],
                                p["reversed"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.UNDERWEIGHT:
                        print(
                            "    Contour %d interpolation is underweight: %s, %s"
                            % (
                                p["contour"],
                                p["master_1"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.OVERWEIGHT:
                        print(
                            "    Contour %d interpolation is overweight: %s, %s"
                            % (
                                p["contour"],
                                p["master_1"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.KINK:
                        print(
                            "    Contour %d has a kink at %s: %s, %s"
                            % (
                                p["contour"],
                                p["value"],
                                p["master_1"],
                                p["master_2"],
                            ),
                            file=f,
                        )
                    elif p["type"] == InterpolatableProblem.NOTHING:
                        print(
                            "    Showing %s and %s"
                            % (
                                p["master_1"],
                                p["master_2"],
                            ),
                            file=f,
                        )
        else:
            for glyphname, problem in problems_gen:
                problems[glyphname].append(problem)

        problems = sort_problems(problems)

        for p in "ps", "pdf":
            arg = getattr(args, p)
            if arg is None:
                continue
            log.info("Writing %s to %s", p.upper(), arg)
            from .interpolatablePlot import InterpolatablePS, InterpolatablePDF

            PlotterClass = InterpolatablePS if p == "ps" else InterpolatablePDF

            with PlotterClass(
                ensure_parent_dir(arg), glyphsets=glyphsets, names=names
            ) as doc:
                doc.add_title_page(
                    original_args_inputs, tolerance=tolerance, kinkiness=kinkiness
                )
                if problems:
                    doc.add_summary(problems)
                doc.add_problems(problems)
                if not problems and not args.quiet:
                    doc.draw_cupcake()
                if problems:
                    doc.add_index()
                    doc.add_table_of_contents()

        if args.html:
            log.info("Writing HTML to %s", args.html)
            from .interpolatablePlot import InterpolatableSVG

            svgs = []
            glyph_starts = {}
            with InterpolatableSVG(svgs, glyphsets=glyphsets, names=names) as svg:
                svg.add_title_page(
                    original_args_inputs,
                    show_tolerance=False,
                    tolerance=tolerance,
                    kinkiness=kinkiness,
                )
                for glyph, glyph_problems in problems.items():
                    glyph_starts[len(svgs)] = glyph
                    svg.add_problems(
                        {glyph: glyph_problems},
                        show_tolerance=False,
                        show_page_number=False,
                    )
                if not problems and not args.quiet:
                    svg.draw_cupcake()

            import base64

            with open(ensure_parent_dir(args.html), "wb") as f:
                f.write(b"<!DOCTYPE html>\n")
                f.write(
                    b'<html><body align="center" style="font-family: sans-serif; text-color: #222">\n'
                )
                f.write(b"<title>fonttools varLib.interpolatable report</title>\n")
                for i, svg in enumerate(svgs):
                    if i in glyph_starts:
                        f.write(f"<h1>Glyph {glyph_starts[i]}</h1>\n".encode("utf-8"))
                    f.write("<img src='data:image/svg+xml;base64,".encode("utf-8"))
                    f.write(base64.b64encode(svg))
                    f.write(b"' />\n")
                    f.write(b"<hr>\n")
                f.write(b"</body></html>\n")

    except Exception as e:
        e.args += original_args_inputs
        log.error(e)
        raise

    if problems:
        return problems


if __name__ == "__main__":
    import sys

    problems = main()
    sys.exit(int(bool(problems)))

# === NexusCore/openenv\Lib\site-packages\PIL\GifImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# GIF file handling
#
# History:
# 1995-09-01 fl   Created
# 1996-12-14 fl   Added interlace support
# 1996-12-30 fl   Added animation support
# 1997-01-05 fl   Added write support, fixed local colour map bug
# 1997-02-23 fl   Make sure to load raster data in getdata()
# 1997-07-05 fl   Support external decoder (0.4)
# 1998-07-09 fl   Handle all modes when saving (0.5)
# 1998-07-15 fl   Renamed offset attribute to avoid name clash
# 2001-04-16 fl   Added rewind support (seek to frame 0) (0.6)
# 2001-04-17 fl   Added palette optimization (0.7)
# 2002-06-06 fl   Added transparency support for save (0.8)
# 2004-02-24 fl   Disable interlacing for small images
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1995-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import itertools
import math
import os
import subprocess
from enum import IntEnum
from functools import cached_property
from typing import IO, Any, Literal, NamedTuple, Union

from . import (
    Image,
    ImageChops,
    ImageFile,
    ImageMath,
    ImageOps,
    ImagePalette,
    ImageSequence,
)
from ._binary import i16le as i16
from ._binary import o8
from ._binary import o16le as o16
from ._util import DeferredError

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import _imaging
    from ._typing import Buffer


class LoadingStrategy(IntEnum):
    """.. versionadded:: 9.1.0"""

    RGB_AFTER_FIRST = 0
    RGB_AFTER_DIFFERENT_PALETTE_ONLY = 1
    RGB_ALWAYS = 2


#: .. versionadded:: 9.1.0
LOADING_STRATEGY = LoadingStrategy.RGB_AFTER_FIRST

# --------------------------------------------------------------------
# Identify/read GIF files


def _accept(prefix: bytes) -> bool:
    return prefix.startswith((b"GIF87a", b"GIF89a"))


##
# Image plugin for GIF images.  This plugin supports both GIF87 and
# GIF89 images.


class GifImageFile(ImageFile.ImageFile):
    format = "GIF"
    format_description = "Compuserve GIF"
    _close_exclusive_fp_after_loading = False

    global_palette = None

    def data(self) -> bytes | None:
        s = self.fp.read(1)
        if s and s[0]:
            return self.fp.read(s[0])
        return None

    def _is_palette_needed(self, p: bytes) -> bool:
        for i in range(0, len(p), 3):
            if not (i // 3 == p[i] == p[i + 1] == p[i + 2]):
                return True
        return False

    def _open(self) -> None:
        # Screen
        s = self.fp.read(13)
        if not _accept(s):
            msg = "not a GIF file"
            raise SyntaxError(msg)

        self.info["version"] = s[:6]
        self._size = i16(s, 6), i16(s, 8)
        flags = s[10]
        bits = (flags & 7) + 1

        if flags & 128:
            # get global palette
            self.info["background"] = s[11]
            # check if palette contains colour indices
            p = self.fp.read(3 << bits)
            if self._is_palette_needed(p):
                p = ImagePalette.raw("RGB", p)
                self.global_palette = self.palette = p

        self._fp = self.fp  # FIXME: hack
        self.__rewind = self.fp.tell()
        self._n_frames: int | None = None
        self._seek(0)  # get ready to read first frame

    @property
    def n_frames(self) -> int:
        if self._n_frames is None:
            current = self.tell()
            try:
                while True:
                    self._seek(self.tell() + 1, False)
            except EOFError:
                self._n_frames = self.tell() + 1
            self.seek(current)
        return self._n_frames

    @cached_property
    def is_animated(self) -> bool:
        if self._n_frames is not None:
            return self._n_frames != 1

        current = self.tell()
        if current:
            return True

        try:
            self._seek(1, False)
            is_animated = True
        except EOFError:
            is_animated = False

        self.seek(current)
        return is_animated

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        if frame < self.__frame:
            self._im = None
            self._seek(0)

        last_frame = self.__frame
        for f in range(self.__frame + 1, frame + 1):
            try:
                self._seek(f)
            except EOFError as e:
                self.seek(last_frame)
                msg = "no more images in GIF file"
                raise EOFError(msg) from e

    def _seek(self, frame: int, update_image: bool = True) -> None:
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex
        if frame == 0:
            # rewind
            self.__offset = 0
            self.dispose: _imaging.ImagingCore | None = None
            self.__frame = -1
            self._fp.seek(self.__rewind)
            self.disposal_method = 0
            if "comment" in self.info:
                del self.info["comment"]
        else:
            # ensure that the previous frame was loaded
            if self.tile and update_image:
                self.load()

        if frame != self.__frame + 1:
            msg = f"cannot seek to frame {frame}"
            raise ValueError(msg)

        self.fp = self._fp
        if self.__offset:
            # backup to last frame
            self.fp.seek(self.__offset)
            while self.data():
                pass
            self.__offset = 0

        s = self.fp.read(1)
        if not s or s == b";":
            msg = "no more images in GIF file"
            raise EOFError(msg)

        palette: ImagePalette.ImagePalette | Literal[False] | None = None

        info: dict[str, Any] = {}
        frame_transparency = None
        interlace = None
        frame_dispose_extent = None
        while True:
            if not s:
                s = self.fp.read(1)
            if not s or s == b";":
                break

            elif s == b"!":
                #
                # extensions
                #
                s = self.fp.read(1)
                block = self.data()
                if s[0] == 249 and block is not None:
                    #
                    # graphic control extension
                    #
                    flags = block[0]
                    if flags & 1:
                        frame_transparency = block[3]
                    info["duration"] = i16(block, 1) * 10

                    # disposal method - find the value of bits 4 - 6
                    dispose_bits = 0b00011100 & flags
                    dispose_bits = dispose_bits >> 2
                    if dispose_bits:
                        # only set the dispose if it is not
                        # unspecified. I'm not sure if this is
                        # correct, but it seems to prevent the last
                        # frame from looking odd for some animations
                        self.disposal_method = dispose_bits
                elif s[0] == 254:
                    #
                    # comment extension
                    #
                    comment = b""

                    # Read this comment block
                    while block:
                        comment += block
                        block = self.data()

                    if "comment" in info:
                        # If multiple comment blocks in frame, separate with \n
                        info["comment"] += b"\n" + comment
                    else:
                        info["comment"] = comment
                    s = None
                    continue
                elif s[0] == 255 and frame == 0 and block is not None:
                    #
                    # application extension
                    #
                    info["extension"] = block, self.fp.tell()
                    if block.startswith(b"NETSCAPE2.0"):
                        block = self.data()
                        if block and len(block) >= 3 and block[0] == 1:
                            self.info["loop"] = i16(block, 1)
                while self.data():
                    pass

            elif s == b",":
                #
                # local image
                #
                s = self.fp.read(9)

                # extent
                x0, y0 = i16(s, 0), i16(s, 2)
                x1, y1 = x0 + i16(s, 4), y0 + i16(s, 6)
                if (x1 > self.size[0] or y1 > self.size[1]) and update_image:
                    self._size = max(x1, self.size[0]), max(y1, self.size[1])
                    Image._decompression_bomb_check(self._size)
                frame_dispose_extent = x0, y0, x1, y1
                flags = s[8]

                interlace = (flags & 64) != 0

                if flags & 128:
                    bits = (flags & 7) + 1
                    p = self.fp.read(3 << bits)
                    if self._is_palette_needed(p):
                        palette = ImagePalette.raw("RGB", p)
                    else:
                        palette = False

                # image data
                bits = self.fp.read(1)[0]
                self.__offset = self.fp.tell()
                break
            s = None

        if interlace is None:
            msg = "image not found in GIF frame"
            raise EOFError(msg)

        self.__frame = frame
        if not update_image:
            return

        self.tile = []

        if self.dispose:
            self.im.paste(self.dispose, self.dispose_extent)

        self._frame_palette = palette if palette is not None else self.global_palette
        self._frame_transparency = frame_transparency
        if frame == 0:
            if self._frame_palette:
                if LOADING_STRATEGY == LoadingStrategy.RGB_ALWAYS:
                    self._mode = "RGBA" if frame_transparency is not None else "RGB"
                else:
                    self._mode = "P"
            else:
                self._mode = "L"

            if palette:
                self.palette = palette
            elif self.global_palette:
                from copy import copy

                self.palette = copy(self.global_palette)
            else:
                self.palette = None
        else:
            if self.mode == "P":
                if (
                    LOADING_STRATEGY != LoadingStrategy.RGB_AFTER_DIFFERENT_PALETTE_ONLY
                    or palette
                ):
                    if "transparency" in self.info:
                        self.im.putpalettealpha(self.info["transparency"], 0)
                        self.im = self.im.convert("RGBA", Image.Dither.FLOYDSTEINBERG)
                        self._mode = "RGBA"
                        del self.info["transparency"]
                    else:
                        self._mode = "RGB"
                        self.im = self.im.convert("RGB", Image.Dither.FLOYDSTEINBERG)

        def _rgb(color: int) -> tuple[int, int, int]:
            if self._frame_palette:
                if color * 3 + 3 > len(self._frame_palette.palette):
                    color = 0
                return tuple(self._frame_palette.palette[color * 3 : color * 3 + 3])
            else:
                return (color, color, color)

        self.dispose = None
        self.dispose_extent = frame_dispose_extent
        if self.dispose_extent and self.disposal_method >= 2:
            try:
                if self.disposal_method == 2:
                    # replace with background colour

                    # only dispose the extent in this frame
                    x0, y0, x1, y1 = self.dispose_extent
                    dispose_size = (x1 - x0, y1 - y0)

                    Image._decompression_bomb_check(dispose_size)

                    # by convention, attempt to use transparency first
                    dispose_mode = "P"
                    color = self.info.get("transparency", frame_transparency)
                    if color is not None:
                        if self.mode in ("RGB", "RGBA"):
                            dispose_mode = "RGBA"
                            color = _rgb(color) + (0,)
                    else:
                        color = self.info.get("background", 0)
                        if self.mode in ("RGB", "RGBA"):
                            dispose_mode = "RGB"
                            color = _rgb(color)
                    self.dispose = Image.core.fill(dispose_mode, dispose_size, color)
                else:
                    # replace with previous contents
                    if self._im is not None:
                        # only dispose the extent in this frame
                        self.dispose = self._crop(self.im, self.dispose_extent)
                    elif frame_transparency is not None:
                        x0, y0, x1, y1 = self.dispose_extent
                        dispose_size = (x1 - x0, y1 - y0)

                        Image._decompression_bomb_check(dispose_size)
                        dispose_mode = "P"
                        color = frame_transparency
                        if self.mode in ("RGB", "RGBA"):
                            dispose_mode = "RGBA"
                            color = _rgb(frame_transparency) + (0,)
                        self.dispose = Image.core.fill(
                            dispose_mode, dispose_size, color
                        )
            except AttributeError:
                pass

        if interlace is not None:
            transparency = -1
            if frame_transparency is not None:
                if frame == 0:
                    if LOADING_STRATEGY != LoadingStrategy.RGB_ALWAYS:
                        self.info["transparency"] = frame_transparency
                elif self.mode not in ("RGB", "RGBA"):
                    transparency = frame_transparency
            self.tile = [
                ImageFile._Tile(
                    "gif",
                    (x0, y0, x1, y1),
                    self.__offset,
                    (bits, interlace, transparency),
                )
            ]

        if info.get("comment"):
            self.info["comment"] = info["comment"]
        for k in ["duration", "extension"]:
            if k in info:
                self.info[k] = info[k]
            elif k in self.info:
                del self.info[k]

    def load_prepare(self) -> None:
        temp_mode = "P" if self._frame_palette else "L"
        self._prev_im = None
        if self.__frame == 0:
            if self._frame_transparency is not None:
                self.im = Image.core.fill(
                    temp_mode, self.size, self._frame_transparency
                )
        elif self.mode in ("RGB", "RGBA"):
            self._prev_im = self.im
            if self._frame_palette:
                self.im = Image.core.fill("P", self.size, self._frame_transparency or 0)
                self.im.putpalette("RGB", *self._frame_palette.getdata())
            else:
                self._im = None
        if not self._prev_im and self._im is not None and self.size != self.im.size:
            expanded_im = Image.core.fill(self.im.mode, self.size)
            if self._frame_palette:
                expanded_im.putpalette("RGB", *self._frame_palette.getdata())
            expanded_im.paste(self.im, (0, 0) + self.im.size)

            self.im = expanded_im
        self._mode = temp_mode
        self._frame_palette = None

        super().load_prepare()

    def load_end(self) -> None:
        if self.__frame == 0:
            if self.mode == "P" and LOADING_STRATEGY == LoadingStrategy.RGB_ALWAYS:
                if self._frame_transparency is not None:
                    self.im.putpalettealpha(self._frame_transparency, 0)
                    self._mode = "RGBA"
                else:
                    self._mode = "RGB"
                self.im = self.im.convert(self.mode, Image.Dither.FLOYDSTEINBERG)
            return
        if not self._prev_im:
            return
        if self.size != self._prev_im.size:
            if self._frame_transparency is not None:
                expanded_im = Image.core.fill("RGBA", self.size)
            else:
                expanded_im = Image.core.fill("P", self.size)
                expanded_im.putpalette("RGB", "RGB", self.im.getpalette())
                expanded_im = expanded_im.convert("RGB")
            expanded_im.paste(self._prev_im, (0, 0) + self._prev_im.size)

            self._prev_im = expanded_im
            assert self._prev_im is not None
        if self._frame_transparency is not None:
            self.im.putpalettealpha(self._frame_transparency, 0)
            frame_im = self.im.convert("RGBA")
        else:
            frame_im = self.im.convert("RGB")

        assert self.dispose_extent is not None
        frame_im = self._crop(frame_im, self.dispose_extent)

        self.im = self._prev_im
        self._mode = self.im.mode
        if frame_im.mode == "RGBA":
            self.im.paste(frame_im, self.dispose_extent, frame_im)
        else:
            self.im.paste(frame_im, self.dispose_extent)

    def tell(self) -> int:
        return self.__frame


# --------------------------------------------------------------------
# Write GIF files


RAWMODE = {"1": "L", "L": "L", "P": "P"}


def _normalize_mode(im: Image.Image) -> Image.Image:
    """
    Takes an image (or frame), returns an image in a mode that is appropriate
    for saving in a Gif.

    It may return the original image, or it may return an image converted to
    palette or 'L' mode.

    :param im: Image object
    :returns: Image object
    """
    if im.mode in RAWMODE:
        im.load()
        return im
    if Image.getmodebase(im.mode) == "RGB":
        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
        assert im.palette is not None
        if im.palette.mode == "RGBA":
            for rgba in im.palette.colors:
                if rgba[3] == 0:
                    im.info["transparency"] = im.palette.colors[rgba]
                    break
        return im
    return im.convert("L")


_Palette = Union[bytes, bytearray, list[int], ImagePalette.ImagePalette]


def _normalize_palette(
    im: Image.Image, palette: _Palette | None, info: dict[str, Any]
) -> Image.Image:
    """
    Normalizes the palette for image.
      - Sets the palette to the incoming palette, if provided.
      - Ensures that there's a palette for L mode images
      - Optimizes the palette if necessary/desired.

    :param im: Image object
    :param palette: bytes object containing the source palette, or ....
    :param info: encoderinfo
    :returns: Image object
    """
    source_palette = None
    if palette:
        # a bytes palette
        if isinstance(palette, (bytes, bytearray, list)):
            source_palette = bytearray(palette[:768])
        if isinstance(palette, ImagePalette.ImagePalette):
            source_palette = bytearray(palette.palette)

    if im.mode == "P":
        if not source_palette:
            im_palette = im.getpalette(None)
            assert im_palette is not None
            source_palette = bytearray(im_palette)
    else:  # L-mode
        if not source_palette:
            source_palette = bytearray(i // 3 for i in range(768))
        im.palette = ImagePalette.ImagePalette("RGB", palette=source_palette)
    assert source_palette is not None

    if palette:
        used_palette_colors: list[int | None] = []
        assert im.palette is not None
        for i in range(0, len(source_palette), 3):
            source_color = tuple(source_palette[i : i + 3])
            index = im.palette.colors.get(source_color)
            if index in used_palette_colors:
                index = None
            used_palette_colors.append(index)
        for i, index in enumerate(used_palette_colors):
            if index is None:
                for j in range(len(used_palette_colors)):
                    if j not in used_palette_colors:
                        used_palette_colors[i] = j
                        break
        dest_map: list[int] = []
        for index in used_palette_colors:
            assert index is not None
            dest_map.append(index)
        im = im.remap_palette(dest_map)
    else:
        optimized_palette_colors = _get_optimize(im, info)
        if optimized_palette_colors is not None:
            im = im.remap_palette(optimized_palette_colors, source_palette)
            if "transparency" in info:
                try:
                    info["transparency"] = optimized_palette_colors.index(
                        info["transparency"]
                    )
                except ValueError:
                    del info["transparency"]
            return im

    assert im.palette is not None
    im.palette.palette = source_palette
    return im


def _write_single_frame(
    im: Image.Image,
    fp: IO[bytes],
    palette: _Palette | None,
) -> None:
    im_out = _normalize_mode(im)
    for k, v in im_out.info.items():
        if isinstance(k, str):
            im.encoderinfo.setdefault(k, v)
    im_out = _normalize_palette(im_out, palette, im.encoderinfo)

    for s in _get_global_header(im_out, im.encoderinfo):
        fp.write(s)

    # local image header
    flags = 0
    if get_interlace(im):
        flags = flags | 64
    _write_local_header(fp, im, (0, 0), flags)

    im_out.encoderconfig = (8, get_interlace(im))
    ImageFile._save(
        im_out, fp, [ImageFile._Tile("gif", (0, 0) + im.size, 0, RAWMODE[im_out.mode])]
    )

    fp.write(b"\0")  # end of image data


def _getbbox(
    base_im: Image.Image, im_frame: Image.Image
) -> tuple[Image.Image, tuple[int, int, int, int] | None]:
    palette_bytes = [
        bytes(im.palette.palette) if im.palette else b"" for im in (base_im, im_frame)
    ]
    if palette_bytes[0] != palette_bytes[1]:
        im_frame = im_frame.convert("RGBA")
        base_im = base_im.convert("RGBA")
    delta = ImageChops.subtract_modulo(im_frame, base_im)
    return delta, delta.getbbox(alpha_only=False)


class _Frame(NamedTuple):
    im: Image.Image
    bbox: tuple[int, int, int, int] | None
    encoderinfo: dict[str, Any]


def _write_multiple_frames(
    im: Image.Image, fp: IO[bytes], palette: _Palette | None
) -> bool:
    duration = im.encoderinfo.get("duration")
    disposal = im.encoderinfo.get("disposal", im.info.get("disposal"))

    im_frames: list[_Frame] = []
    previous_im: Image.Image | None = None
    frame_count = 0
    background_im = None
    for imSequence in itertools.chain([im], im.encoderinfo.get("append_images", [])):
        for im_frame in ImageSequence.Iterator(imSequence):
            # a copy is required here since seek can still mutate the image
            im_frame = _normalize_mode(im_frame.copy())
            if frame_count == 0:
                for k, v in im_frame.info.items():
                    if k == "transparency":
                        continue
                    if isinstance(k, str):
                        im.encoderinfo.setdefault(k, v)

            encoderinfo = im.encoderinfo.copy()
            if "transparency" in im_frame.info:
                encoderinfo.setdefault("transparency", im_frame.info["transparency"])
            im_frame = _normalize_palette(im_frame, palette, encoderinfo)
            if isinstance(duration, (list, tuple)):
                encoderinfo["duration"] = duration[frame_count]
            elif duration is None and "duration" in im_frame.info:
                encoderinfo["duration"] = im_frame.info["duration"]
            if isinstance(disposal, (list, tuple)):
                encoderinfo["disposal"] = disposal[frame_count]
            frame_count += 1

            diff_frame = None
            if im_frames and previous_im:
                # delta frame
                delta, bbox = _getbbox(previous_im, im_frame)
                if not bbox:
                    # This frame is identical to the previous frame
                    if encoderinfo.get("duration"):
                        im_frames[-1].encoderinfo["duration"] += encoderinfo["duration"]
                    continue
                if im_frames[-1].encoderinfo.get("disposal") == 2:
                    # To appear correctly in viewers using a convention,
                    # only consider transparency, and not background color
                    color = im.encoderinfo.get(
                        "transparency", im.info.get("transparency")
                    )
                    if color is not None:
                        if background_im is None:
                            background = _get_background(im_frame, color)
                            background_im = Image.new("P", im_frame.size, background)
                            first_palette = im_frames[0].im.palette
                            assert first_palette is not None
                            background_im.putpalette(first_palette, first_palette.mode)
                        bbox = _getbbox(background_im, im_frame)[1]
                    else:
                        bbox = (0, 0) + im_frame.size
                elif encoderinfo.get("optimize") and im_frame.mode != "1":
                    if "transparency" not in encoderinfo:
                        assert im_frame.palette is not None
                        try:
                            encoderinfo["transparency"] = (
                                im_frame.palette._new_color_index(im_frame)
                            )
                        except ValueError:
                            pass
                    if "transparency" in encoderinfo:
                        # When the delta is zero, fill the image with transparency
                        diff_frame = im_frame.copy()
                        fill = Image.new("P", delta.size, encoderinfo["transparency"])
                        if delta.mode == "RGBA":
                            r, g, b, a = delta.split()
                            mask = ImageMath.lambda_eval(
                                lambda args: args["convert"](
                                    args["max"](
                                        args["max"](
                                            args["max"](args["r"], args["g"]), args["b"]
                                        ),
                                        args["a"],
                                    )
                                    * 255,
                                    "1",
                                ),
                                r=r,
                                g=g,
                                b=b,
                                a=a,
                            )
                        else:
                            if delta.mode == "P":
                                # Convert to L without considering palette
                                delta_l = Image.new("L", delta.size)
                                delta_l.putdata(delta.getdata())
                                delta = delta_l
                            mask = ImageMath.lambda_eval(
                                lambda args: args["convert"](args["im"] * 255, "1"),
                                im=delta,
                            )
                        diff_frame.paste(fill, mask=ImageOps.invert(mask))
            else:
                bbox = None
            previous_im = im_frame
            im_frames.append(_Frame(diff_frame or im_frame, bbox, encoderinfo))

    if len(im_frames) == 1:
        if "duration" in im.encoderinfo:
            # Since multiple frames will not be written, use the combined duration
            im.encoderinfo["duration"] = im_frames[0].encoderinfo["duration"]
        return False

    for frame_data in im_frames:
        im_frame = frame_data.im
        if not frame_data.bbox:
            # global header
            for s in _get_global_header(im_frame, frame_data.encoderinfo):
                fp.write(s)
            offset = (0, 0)
        else:
            # compress difference
            if not palette:
                frame_data.encoderinfo["include_color_table"] = True

            if frame_data.bbox != (0, 0) + im_frame.size:
                im_frame = im_frame.crop(frame_data.bbox)
            offset = frame_data.bbox[:2]
        _write_frame_data(fp, im_frame, offset, frame_data.encoderinfo)
    return True


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, save_all=True)


def _save(
    im: Image.Image, fp: IO[bytes], filename: str | bytes, save_all: bool = False
) -> None:
    # header
    if "palette" in im.encoderinfo or "palette" in im.info:
        palette = im.encoderinfo.get("palette", im.info.get("palette"))
    else:
        palette = None
        im.encoderinfo.setdefault("optimize", True)

    if not save_all or not _write_multiple_frames(im, fp, palette):
        _write_single_frame(im, fp, palette)

    fp.write(b";")  # end of file

    if hasattr(fp, "flush"):
        fp.flush()


def get_interlace(im: Image.Image) -> int:
    interlace = im.encoderinfo.get("interlace", 1)

    # workaround for @PIL153
    if min(im.size) < 16:
        interlace = 0

    return interlace


def _write_local_header(
    fp: IO[bytes], im: Image.Image, offset: tuple[int, int], flags: int
) -> None:
    try:
        transparency = im.encoderinfo["transparency"]
    except KeyError:
        transparency = None

    if "duration" in im.encoderinfo:
        duration = int(im.encoderinfo["duration"] / 10)
    else:
        duration = 0

    disposal = int(im.encoderinfo.get("disposal", 0))

    if transparency is not None or duration != 0 or disposal:
        packed_flag = 1 if transparency is not None else 0
        packed_flag |= disposal << 2

        fp.write(
            b"!"
            + o8(249)  # extension intro
            + o8(4)  # length
            + o8(packed_flag)  # packed fields
            + o16(duration)  # duration
            + o8(transparency or 0)  # transparency index
            + o8(0)
        )

    include_color_table = im.encoderinfo.get("include_color_table")
    if include_color_table:
        palette_bytes = _get_palette_bytes(im)
        color_table_size = _get_color_table_size(palette_bytes)
        if color_table_size:
            flags = flags | 128  # local color table flag
            flags = flags | color_table_size

    fp.write(
        b","
        + o16(offset[0])  # offset
        + o16(offset[1])
        + o16(im.size[0])  # size
        + o16(im.size[1])
        + o8(flags)  # flags
    )
    if include_color_table and color_table_size:
        fp.write(_get_header_palette(palette_bytes))
    fp.write(o8(8))  # bits


def _save_netpbm(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    # Unused by default.
    # To use, uncomment the register_save call at the end of the file.
    #
    # If you need real GIF compression and/or RGB quantization, you
    # can use the external NETPBM/PBMPLUS utilities.  See comments
    # below for information on how to enable this.
    tempfile = im._dump()

    try:
        with open(filename, "wb") as f:
            if im.mode != "RGB":
                subprocess.check_call(
                    ["ppmtogif", tempfile], stdout=f, stderr=subprocess.DEVNULL
                )
            else:
                # Pipe ppmquant output into ppmtogif
                # "ppmquant 256 %s | ppmtogif > %s" % (tempfile, filename)
                quant_cmd = ["ppmquant", "256", tempfile]
                togif_cmd = ["ppmtogif"]
                quant_proc = subprocess.Popen(
                    quant_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                togif_proc = subprocess.Popen(
                    togif_cmd,
                    stdin=quant_proc.stdout,
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                )

                # Allow ppmquant to receive SIGPIPE if ppmtogif exits
                assert quant_proc.stdout is not None
                quant_proc.stdout.close()

                retcode = quant_proc.wait()
                if retcode:
                    raise subprocess.CalledProcessError(retcode, quant_cmd)

                retcode = togif_proc.wait()
                if retcode:
                    raise subprocess.CalledProcessError(retcode, togif_cmd)
    finally:
        try:
            os.unlink(tempfile)
        except OSError:
            pass


# Force optimization so that we can test performance against
# cases where it took lots of memory and time previously.
_FORCE_OPTIMIZE = False


def _get_optimize(im: Image.Image, info: dict[str, Any]) -> list[int] | None:
    """
    Palette optimization is a potentially expensive operation.

    This function determines if the palette should be optimized using
    some heuristics, then returns the list of palette entries in use.

    :param im: Image object
    :param info: encoderinfo
    :returns: list of indexes of palette entries in use, or None
    """
    if im.mode in ("P", "L") and info and info.get("optimize"):
        # Potentially expensive operation.

        # The palette saves 3 bytes per color not used, but palette
        # lengths are restricted to 3*(2**N) bytes. Max saving would
        # be 768 -> 6 bytes if we went all the way down to 2 colors.
        # * If we're over 128 colors, we can't save any space.
        # * If there aren't any holes, it's not worth collapsing.
        # * If we have a 'large' image, the palette is in the noise.

        # create the new palette if not every color is used
        optimise = _FORCE_OPTIMIZE or im.mode == "L"
        if optimise or im.width * im.height < 512 * 512:
            # check which colors are used
            used_palette_colors = []
            for i, count in enumerate(im.histogram()):
                if count:
                    used_palette_colors.append(i)

            if optimise or max(used_palette_colors) >= len(used_palette_colors):
                return used_palette_colors

            assert im.palette is not None
            num_palette_colors = len(im.palette.palette) // Image.getmodebands(
                im.palette.mode
            )
            current_palette_size = 1 << (num_palette_colors - 1).bit_length()
            if (
                # check that the palette would become smaller when saved
                len(used_palette_colors) <= current_palette_size // 2
                # check that the palette is not already the smallest possible size
                and current_palette_size > 2
            ):
                return used_palette_colors
    return None


def _get_color_table_size(palette_bytes: bytes) -> int:
    # calculate the palette size for the header
    if not palette_bytes:
        return 0
    elif len(palette_bytes) < 9:
        return 1
    else:
        return math.ceil(math.log(len(palette_bytes) // 3, 2)) - 1


def _get_header_palette(palette_bytes: bytes) -> bytes:
    """
    Returns the palette, null padded to the next power of 2 (*3) bytes
    suitable for direct inclusion in the GIF header

    :param palette_bytes: Unpadded palette bytes, in RGBRGB form
    :returns: Null padded palette
    """
    color_table_size = _get_color_table_size(palette_bytes)

    # add the missing amount of bytes
    # the palette has to be 2<<n in size
    actual_target_size_diff = (2 << color_table_size) - len(palette_bytes) // 3
    if actual_target_size_diff > 0:
        palette_bytes += o8(0) * 3 * actual_target_size_diff
    return palette_bytes


def _get_palette_bytes(im: Image.Image) -> bytes:
    """
    Gets the palette for inclusion in the gif header

    :param im: Image object
    :returns: Bytes, len<=768 suitable for inclusion in gif header
    """
    if not im.palette:
        return b""

    palette = bytes(im.palette.palette)
    if im.palette.mode == "RGBA":
        palette = b"".join(palette[i * 4 : i * 4 + 3] for i in range(len(palette) // 3))
    return palette


def _get_background(
    im: Image.Image,
    info_background: int | tuple[int, int, int] | tuple[int, int, int, int] | None,
) -> int:
    background = 0
    if info_background:
        if isinstance(info_background, tuple):
            # WebPImagePlugin stores an RGBA value in info["background"]
            # So it must be converted to the same format as GifImagePlugin's
            # info["background"] - a global color table index
            assert im.palette is not None
            try:
                background = im.palette.getcolor(info_background, im)
            except ValueError as e:
                if str(e) not in (
                    # If all 256 colors are in use,
                    # then there is no need for the background color
                    "cannot allocate more than 256 colors",
                    # Ignore non-opaque WebP background
                    "cannot add non-opaque RGBA color to RGB palette",
                ):
                    raise
        else:
            background = info_background
    return background


def _get_global_header(im: Image.Image, info: dict[str, Any]) -> list[bytes]:
    """Return a list of strings representing a GIF header"""

    # Header Block
    # https://www.matthewflickinger.com/lab/whatsinagif/bits_and_bytes.asp

    version = b"87a"
    if im.info.get("version") == b"89a" or (
        info
        and (
            "transparency" in info
            or info.get("loop") is not None
            or info.get("duration")
            or info.get("comment")
        )
    ):
        version = b"89a"

    background = _get_background(im, info.get("background"))

    palette_bytes = _get_palette_bytes(im)
    color_table_size = _get_color_table_size(palette_bytes)

    header = [
        b"GIF"  # signature
        + version  # version
        + o16(im.size[0])  # canvas width
        + o16(im.size[1]),  # canvas height
        # Logical Screen Descriptor
        # size of global color table + global color table flag
        o8(color_table_size + 128),  # packed fields
        # background + reserved/aspect
        o8(background) + o8(0),
        # Global Color Table
        _get_header_palette(palette_bytes),
    ]
    if info.get("loop") is not None:
        header.append(
            b"!"
            + o8(255)  # extension intro
            + o8(11)
            + b"NETSCAPE2.0"
            + o8(3)
            + o8(1)
            + o16(info["loop"])  # number of loops
            + o8(0)
        )
    if info.get("comment"):
        comment_block = b"!" + o8(254)  # extension intro

        comment = info["comment"]
        if isinstance(comment, str):
            comment = comment.encode()
        for i in range(0, len(comment), 255):
            subblock = comment[i : i + 255]
            comment_block += o8(len(subblock)) + subblock

        comment_block += o8(0)
        header.append(comment_block)
    return header


def _write_frame_data(
    fp: IO[bytes],
    im_frame: Image.Image,
    offset: tuple[int, int],
    params: dict[str, Any],
) -> None:
    try:
        im_frame.encoderinfo = params

        # local image header
        _write_local_header(fp, im_frame, offset, 0)

        ImageFile._save(
            im_frame,
            fp,
            [ImageFile._Tile("gif", (0, 0) + im_frame.size, 0, RAWMODE[im_frame.mode])],
        )

        fp.write(b"\0")  # end of image data
    finally:
        del im_frame.encoderinfo


# --------------------------------------------------------------------
# Legacy GIF utilities


def getheader(
    im: Image.Image, palette: _Palette | None = None, info: dict[str, Any] | None = None
) -> tuple[list[bytes], list[int] | None]:
    """
    Legacy Method to get Gif data from image.

    Warning:: May modify image data.

    :param im: Image object
    :param palette: bytes object containing the source palette, or ....
    :param info: encoderinfo
    :returns: tuple of(list of header items, optimized palette)

    """
    if info is None:
        info = {}

    used_palette_colors = _get_optimize(im, info)

    if "background" not in info and "background" in im.info:
        info["background"] = im.info["background"]

    im_mod = _normalize_palette(im, palette, info)
    im.palette = im_mod.palette
    im.im = im_mod.im
    header = _get_global_header(im, info)

    return header, used_palette_colors


def getdata(
    im: Image.Image, offset: tuple[int, int] = (0, 0), **params: Any
) -> list[bytes]:
    """
    Legacy Method

    Return a list of strings representing this image.
    The first string is a local image header, the rest contains
    encoded image data.

    To specify duration, add the time in milliseconds,
    e.g. ``getdata(im_frame, duration=1000)``

    :param im: Image object
    :param offset: Tuple of (x, y) pixels. Defaults to (0, 0)
    :param \\**params: e.g. duration or other encoder info parameters
    :returns: List of bytes containing GIF encoded frame data

    """
    from io import BytesIO

    class Collector(BytesIO):
        data = []

        def write(self, data: Buffer) -> int:
            self.data.append(data)
            return len(data)

    im.load()  # make sure raster data is available

    fp = Collector()

    _write_frame_data(fp, im, offset, params)

    return fp.data


# --------------------------------------------------------------------
# Registry

Image.register_open(GifImageFile.format, GifImageFile, _accept)
Image.register_save(GifImageFile.format, _save)
Image.register_save_all(GifImageFile.format, _save_all)
Image.register_extension(GifImageFile.format, ".gif")
Image.register_mime(GifImageFile.format, "image/gif")

#
# Uncomment the following line if you wish to use NETPBM/PBMPLUS
# instead of the built-in "uncompressed" GIF encoder

# Image.register_save(GifImageFile.format, _save_netpbm)

# === NexusCore/openenv\Lib\site-packages\jinja2\nodes.py ===
"""AST nodes generated by the parser for the compiler. Also provides
some node tree helper functions used by the parser and compiler in order
to normalize nodes.
"""

import inspect
import operator
import typing as t
from collections import deque

from markupsafe import Markup

from .utils import _PassArg

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .environment import Environment

_NodeBound = t.TypeVar("_NodeBound", bound="Node")

_binop_to_func: t.Dict[str, t.Callable[[t.Any, t.Any], t.Any]] = {
    "*": operator.mul,
    "/": operator.truediv,
    "//": operator.floordiv,
    "**": operator.pow,
    "%": operator.mod,
    "+": operator.add,
    "-": operator.sub,
}

_uaop_to_func: t.Dict[str, t.Callable[[t.Any], t.Any]] = {
    "not": operator.not_,
    "+": operator.pos,
    "-": operator.neg,
}

_cmpop_to_func: t.Dict[str, t.Callable[[t.Any, t.Any], t.Any]] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gteq": operator.ge,
    "lt": operator.lt,
    "lteq": operator.le,
    "in": lambda a, b: a in b,
    "notin": lambda a, b: a not in b,
}


class Impossible(Exception):
    """Raised if the node could not perform a requested action."""


class NodeType(type):
    """A metaclass for nodes that handles the field and attribute
    inheritance.  fields and attributes from the parent class are
    automatically forwarded to the child."""

    def __new__(mcs, name, bases, d):  # type: ignore
        for attr in "fields", "attributes":
            storage: t.List[t.Tuple[str, ...]] = []
            storage.extend(getattr(bases[0] if bases else object, attr, ()))
            storage.extend(d.get(attr, ()))
            assert len(bases) <= 1, "multiple inheritance not allowed"
            assert len(storage) == len(set(storage)), "layout conflict"
            d[attr] = tuple(storage)
        d.setdefault("abstract", False)
        return type.__new__(mcs, name, bases, d)


class EvalContext:
    """Holds evaluation time information.  Custom attributes can be attached
    to it in extensions.
    """

    def __init__(
        self, environment: "Environment", template_name: t.Optional[str] = None
    ) -> None:
        self.environment = environment
        if callable(environment.autoescape):
            self.autoescape = environment.autoescape(template_name)
        else:
            self.autoescape = environment.autoescape
        self.volatile = False

    def save(self) -> t.Mapping[str, t.Any]:
        return self.__dict__.copy()

    def revert(self, old: t.Mapping[str, t.Any]) -> None:
        self.__dict__.clear()
        self.__dict__.update(old)


def get_eval_context(node: "Node", ctx: t.Optional[EvalContext]) -> EvalContext:
    if ctx is None:
        if node.environment is None:
            raise RuntimeError(
                "if no eval context is passed, the node must have an"
                " attached environment."
            )
        return EvalContext(node.environment)
    return ctx


class Node(metaclass=NodeType):
    """Baseclass for all Jinja nodes.  There are a number of nodes available
    of different types.  There are four major types:

    -   :class:`Stmt`: statements
    -   :class:`Expr`: expressions
    -   :class:`Helper`: helper nodes
    -   :class:`Template`: the outermost wrapper node

    All nodes have fields and attributes.  Fields may be other nodes, lists,
    or arbitrary values.  Fields are passed to the constructor as regular
    positional arguments, attributes as keyword arguments.  Each node has
    two attributes: `lineno` (the line number of the node) and `environment`.
    The `environment` attribute is set at the end of the parsing process for
    all nodes automatically.
    """

    fields: t.Tuple[str, ...] = ()
    attributes: t.Tuple[str, ...] = ("lineno", "environment")
    abstract = True

    lineno: int
    environment: t.Optional["Environment"]

    def __init__(self, *fields: t.Any, **attributes: t.Any) -> None:
        if self.abstract:
            raise TypeError("abstract nodes are not instantiable")
        if fields:
            if len(fields) != len(self.fields):
                if not self.fields:
                    raise TypeError(f"{type(self).__name__!r} takes 0 arguments")
                raise TypeError(
                    f"{type(self).__name__!r} takes 0 or {len(self.fields)}"
                    f" argument{'s' if len(self.fields) != 1 else ''}"
                )
            for name, arg in zip(self.fields, fields):
                setattr(self, name, arg)
        for attr in self.attributes:
            setattr(self, attr, attributes.pop(attr, None))
        if attributes:
            raise TypeError(f"unknown attribute {next(iter(attributes))!r}")

    def iter_fields(
        self,
        exclude: t.Optional[t.Container[str]] = None,
        only: t.Optional[t.Container[str]] = None,
    ) -> t.Iterator[t.Tuple[str, t.Any]]:
        """This method iterates over all fields that are defined and yields
        ``(key, value)`` tuples.  Per default all fields are returned, but
        it's possible to limit that to some fields by providing the `only`
        parameter or to exclude some using the `exclude` parameter.  Both
        should be sets or tuples of field names.
        """
        for name in self.fields:
            if (
                (exclude is None and only is None)
                or (exclude is not None and name not in exclude)
                or (only is not None and name in only)
            ):
                try:
                    yield name, getattr(self, name)
                except AttributeError:
                    pass

    def iter_child_nodes(
        self,
        exclude: t.Optional[t.Container[str]] = None,
        only: t.Optional[t.Container[str]] = None,
    ) -> t.Iterator["Node"]:
        """Iterates over all direct child nodes of the node.  This iterates
        over all fields and yields the values of they are nodes.  If the value
        of a field is a list all the nodes in that list are returned.
        """
        for _, item in self.iter_fields(exclude, only):
            if isinstance(item, list):
                for n in item:
                    if isinstance(n, Node):
                        yield n
            elif isinstance(item, Node):
                yield item

    def find(self, node_type: t.Type[_NodeBound]) -> t.Optional[_NodeBound]:
        """Find the first node of a given type.  If no such node exists the
        return value is `None`.
        """
        for result in self.find_all(node_type):
            return result

        return None

    def find_all(
        self, node_type: t.Union[t.Type[_NodeBound], t.Tuple[t.Type[_NodeBound], ...]]
    ) -> t.Iterator[_NodeBound]:
        """Find all the nodes of a given type.  If the type is a tuple,
        the check is performed for any of the tuple items.
        """
        for child in self.iter_child_nodes():
            if isinstance(child, node_type):
                yield child  # type: ignore
            yield from child.find_all(node_type)

    def set_ctx(self, ctx: str) -> "Node":
        """Reset the context of a node and all child nodes.  Per default the
        parser will all generate nodes that have a 'load' context as it's the
        most common one.  This method is used in the parser to set assignment
        targets and other nodes to a store context.
        """
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if "ctx" in node.fields:
                node.ctx = ctx  # type: ignore
            todo.extend(node.iter_child_nodes())
        return self

    def set_lineno(self, lineno: int, override: bool = False) -> "Node":
        """Set the line numbers of the node and children."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if "lineno" in node.attributes:
                if node.lineno is None or override:
                    node.lineno = lineno
            todo.extend(node.iter_child_nodes())
        return self

    def set_environment(self, environment: "Environment") -> "Node":
        """Set the environment for all nodes."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            node.environment = environment
            todo.extend(node.iter_child_nodes())
        return self

    def __eq__(self, other: t.Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented

        return tuple(self.iter_fields()) == tuple(other.iter_fields())

    __hash__ = object.__hash__

    def __repr__(self) -> str:
        args_str = ", ".join(f"{a}={getattr(self, a, None)!r}" for a in self.fields)
        return f"{type(self).__name__}({args_str})"

    def dump(self) -> str:
        def _dump(node: t.Union[Node, t.Any]) -> None:
            if not isinstance(node, Node):
                buf.append(repr(node))
                return

            buf.append(f"nodes.{type(node).__name__}(")
            if not node.fields:
                buf.append(")")
                return
            for idx, field in enumerate(node.fields):
                if idx:
                    buf.append(", ")
                value = getattr(node, field)
                if isinstance(value, list):
                    buf.append("[")
                    for idx, item in enumerate(value):
                        if idx:
                            buf.append(", ")
                        _dump(item)
                    buf.append("]")
                else:
                    _dump(value)
            buf.append(")")

        buf: t.List[str] = []
        _dump(self)
        return "".join(buf)


class Stmt(Node):
    """Base node for all statements."""

    abstract = True


class Helper(Node):
    """Nodes that exist in a specific context only."""

    abstract = True


class Template(Node):
    """Node that represents a template.  This must be the outermost node that
    is passed to the compiler.
    """

    fields = ("body",)
    body: t.List[Node]


class Output(Stmt):
    """A node that holds multiple expressions which are then printed out.
    This is used both for the `print` statement and the regular template data.
    """

    fields = ("nodes",)
    nodes: t.List["Expr"]


class Extends(Stmt):
    """Represents an extends statement."""

    fields = ("template",)
    template: "Expr"


class For(Stmt):
    """The for loop.  `target` is the target for the iteration (usually a
    :class:`Name` or :class:`Tuple`), `iter` the iterable.  `body` is a list
    of nodes that are used as loop-body, and `else_` a list of nodes for the
    `else` block.  If no else node exists it has to be an empty list.

    For filtered nodes an expression can be stored as `test`, otherwise `None`.
    """

    fields = ("target", "iter", "body", "else_", "test", "recursive")
    target: Node
    iter: Node
    body: t.List[Node]
    else_: t.List[Node]
    test: t.Optional[Node]
    recursive: bool


class If(Stmt):
    """If `test` is true, `body` is rendered, else `else_`."""

    fields = ("test", "body", "elif_", "else_")
    test: Node
    body: t.List[Node]
    elif_: t.List["If"]
    else_: t.List[Node]


class Macro(Stmt):
    """A macro definition.  `name` is the name of the macro, `args` a list of
    arguments and `defaults` a list of defaults if there are any.  `body` is
    a list of nodes for the macro body.
    """

    fields = ("name", "args", "defaults", "body")
    name: str
    args: t.List["Name"]
    defaults: t.List["Expr"]
    body: t.List[Node]


class CallBlock(Stmt):
    """Like a macro without a name but a call instead.  `call` is called with
    the unnamed macro as `caller` argument this node holds.
    """

    fields = ("call", "args", "defaults", "body")
    call: "Call"
    args: t.List["Name"]
    defaults: t.List["Expr"]
    body: t.List[Node]


class FilterBlock(Stmt):
    """Node for filter sections."""

    fields = ("body", "filter")
    body: t.List[Node]
    filter: "Filter"


class With(Stmt):
    """Specific node for with statements.  In older versions of Jinja the
    with statement was implemented on the base of the `Scope` node instead.

    .. versionadded:: 2.9.3
    """

    fields = ("targets", "values", "body")
    targets: t.List["Expr"]
    values: t.List["Expr"]
    body: t.List[Node]


class Block(Stmt):
    """A node that represents a block.

    .. versionchanged:: 3.0.0
        the `required` field was added.
    """

    fields = ("name", "body", "scoped", "required")
    name: str
    body: t.List[Node]
    scoped: bool
    required: bool


class Include(Stmt):
    """A node that represents the include tag."""

    fields = ("template", "with_context", "ignore_missing")
    template: "Expr"
    with_context: bool
    ignore_missing: bool


class Import(Stmt):
    """A node that represents the import tag."""

    fields = ("template", "target", "with_context")
    template: "Expr"
    target: str
    with_context: bool


class FromImport(Stmt):
    """A node that represents the from import tag.  It's important to not
    pass unsafe names to the name attribute.  The compiler translates the
    attribute lookups directly into getattr calls and does *not* use the
    subscript callback of the interface.  As exported variables may not
    start with double underscores (which the parser asserts) this is not a
    problem for regular Jinja code, but if this node is used in an extension
    extra care must be taken.

    The list of names may contain tuples if aliases are wanted.
    """

    fields = ("template", "names", "with_context")
    template: "Expr"
    names: t.List[t.Union[str, t.Tuple[str, str]]]
    with_context: bool


class ExprStmt(Stmt):
    """A statement that evaluates an expression and discards the result."""

    fields = ("node",)
    node: Node


class Assign(Stmt):
    """Assigns an expression to a target."""

    fields = ("target", "node")
    target: "Expr"
    node: Node


class AssignBlock(Stmt):
    """Assigns a block to a target."""

    fields = ("target", "filter", "body")
    target: "Expr"
    filter: t.Optional["Filter"]
    body: t.List[Node]


class Expr(Node):
    """Baseclass for all expressions."""

    abstract = True

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        """Return the value of the expression as constant or raise
        :exc:`Impossible` if this was not possible.

        An :class:`EvalContext` can be provided, if none is given
        a default context is created which requires the nodes to have
        an attached environment.

        .. versionchanged:: 2.4
           the `eval_ctx` parameter was added.
        """
        raise Impossible()

    def can_assign(self) -> bool:
        """Check if it's possible to assign something to this node."""
        return False


class BinExpr(Expr):
    """Baseclass for all binary expressions."""

    fields = ("left", "right")
    left: Expr
    right: Expr
    operator: str
    abstract = True

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)

        # intercepted operators cannot be folded at compile time
        if (
            eval_ctx.environment.sandboxed
            and self.operator in eval_ctx.environment.intercepted_binops  # type: ignore
        ):
            raise Impossible()
        f = _binop_to_func[self.operator]
        try:
            return f(self.left.as_const(eval_ctx), self.right.as_const(eval_ctx))
        except Exception as e:
            raise Impossible() from e


class UnaryExpr(Expr):
    """Baseclass for all unary expressions."""

    fields = ("node",)
    node: Expr
    operator: str
    abstract = True

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)

        # intercepted operators cannot be folded at compile time
        if (
            eval_ctx.environment.sandboxed
            and self.operator in eval_ctx.environment.intercepted_unops  # type: ignore
        ):
            raise Impossible()
        f = _uaop_to_func[self.operator]
        try:
            return f(self.node.as_const(eval_ctx))
        except Exception as e:
            raise Impossible() from e


class Name(Expr):
    """Looks up a name or stores a value in a name.
    The `ctx` of the node can be one of the following values:

    -   `store`: store a value in the name
    -   `load`: load that name
    -   `param`: like `store` but if the name was defined as function parameter.
    """

    fields = ("name", "ctx")
    name: str
    ctx: str

    def can_assign(self) -> bool:
        return self.name not in {"true", "false", "none", "True", "False", "None"}


class NSRef(Expr):
    """Reference to a namespace value assignment"""

    fields = ("name", "attr")
    name: str
    attr: str

    def can_assign(self) -> bool:
        # We don't need any special checks here; NSRef assignments have a
        # runtime check to ensure the target is a namespace object which will
        # have been checked already as it is created using a normal assignment
        # which goes through a `Name` node.
        return True


class Literal(Expr):
    """Baseclass for literals."""

    abstract = True


class Const(Literal):
    """All constant values.  The parser will return this node for simple
    constants such as ``42`` or ``"foo"`` but it can be used to store more
    complex values such as lists too.  Only constants with a safe
    representation (objects where ``eval(repr(x)) == x`` is true).
    """

    fields = ("value",)
    value: t.Any

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        return self.value

    @classmethod
    def from_untrusted(
        cls,
        value: t.Any,
        lineno: t.Optional[int] = None,
        environment: "t.Optional[Environment]" = None,
    ) -> "Const":
        """Return a const object if the value is representable as
        constant value in the generated code, otherwise it will raise
        an `Impossible` exception.
        """
        from .compiler import has_safe_repr

        if not has_safe_repr(value):
            raise Impossible()
        return cls(value, lineno=lineno, environment=environment)


class TemplateData(Literal):
    """A constant template string."""

    fields = ("data",)
    data: str

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> str:
        eval_ctx = get_eval_context(self, eval_ctx)
        if eval_ctx.volatile:
            raise Impossible()
        if eval_ctx.autoescape:
            return Markup(self.data)
        return self.data


class Tuple(Literal):
    """For loop unpacking and some other things like multiple arguments
    for subscripts.  Like for :class:`Name` `ctx` specifies if the tuple
    is used for loading the names or storing.
    """

    fields = ("items", "ctx")
    items: t.List[Expr]
    ctx: str

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Tuple[t.Any, ...]:
        eval_ctx = get_eval_context(self, eval_ctx)
        return tuple(x.as_const(eval_ctx) for x in self.items)

    def can_assign(self) -> bool:
        for item in self.items:
            if not item.can_assign():
                return False
        return True


class List(Literal):
    """Any list literal such as ``[1, 2, 3]``"""

    fields = ("items",)
    items: t.List[Expr]

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.List[t.Any]:
        eval_ctx = get_eval_context(self, eval_ctx)
        return [x.as_const(eval_ctx) for x in self.items]


class Dict(Literal):
    """Any dict literal such as ``{1: 2, 3: 4}``.  The items must be a list of
    :class:`Pair` nodes.
    """

    fields = ("items",)
    items: t.List["Pair"]

    def as_const(
        self, eval_ctx: t.Optional[EvalContext] = None
    ) -> t.Dict[t.Any, t.Any]:
        eval_ctx = get_eval_context(self, eval_ctx)
        return dict(x.as_const(eval_ctx) for x in self.items)


class Pair(Helper):
    """A key, value pair for dicts."""

    fields = ("key", "value")
    key: Expr
    value: Expr

    def as_const(
        self, eval_ctx: t.Optional[EvalContext] = None
    ) -> t.Tuple[t.Any, t.Any]:
        eval_ctx = get_eval_context(self, eval_ctx)
        return self.key.as_const(eval_ctx), self.value.as_const(eval_ctx)


class Keyword(Helper):
    """A key, value pair for keyword arguments where key is a string."""

    fields = ("key", "value")
    key: str
    value: Expr

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Tuple[str, t.Any]:
        eval_ctx = get_eval_context(self, eval_ctx)
        return self.key, self.value.as_const(eval_ctx)


class CondExpr(Expr):
    """A conditional expression (inline if expression).  (``{{
    foo if bar else baz }}``)
    """

    fields = ("test", "expr1", "expr2")
    test: Expr
    expr1: Expr
    expr2: t.Optional[Expr]

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)
        if self.test.as_const(eval_ctx):
            return self.expr1.as_const(eval_ctx)

        # if we evaluate to an undefined object, we better do that at runtime
        if self.expr2 is None:
            raise Impossible()

        return self.expr2.as_const(eval_ctx)


def args_as_const(
    node: t.Union["_FilterTestCommon", "Call"], eval_ctx: t.Optional[EvalContext]
) -> t.Tuple[t.List[t.Any], t.Dict[t.Any, t.Any]]:
    args = [x.as_const(eval_ctx) for x in node.args]
    kwargs = dict(x.as_const(eval_ctx) for x in node.kwargs)

    if node.dyn_args is not None:
        try:
            args.extend(node.dyn_args.as_const(eval_ctx))
        except Exception as e:
            raise Impossible() from e

    if node.dyn_kwargs is not None:
        try:
            kwargs.update(node.dyn_kwargs.as_const(eval_ctx))
        except Exception as e:
            raise Impossible() from e

    return args, kwargs


class _FilterTestCommon(Expr):
    fields = ("node", "name", "args", "kwargs", "dyn_args", "dyn_kwargs")
    node: Expr
    name: str
    args: t.List[Expr]
    kwargs: t.List[Pair]
    dyn_args: t.Optional[Expr]
    dyn_kwargs: t.Optional[Expr]
    abstract = True
    _is_filter = True

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)

        if eval_ctx.volatile:
            raise Impossible()

        if self._is_filter:
            env_map = eval_ctx.environment.filters
        else:
            env_map = eval_ctx.environment.tests

        func = env_map.get(self.name)
        pass_arg = _PassArg.from_obj(func)  # type: ignore

        if func is None or pass_arg is _PassArg.context:
            raise Impossible()

        if eval_ctx.environment.is_async and (
            getattr(func, "jinja_async_variant", False) is True
            or inspect.iscoroutinefunction(func)
        ):
            raise Impossible()

        args, kwargs = args_as_const(self, eval_ctx)
        args.insert(0, self.node.as_const(eval_ctx))

        if pass_arg is _PassArg.eval_context:
            args.insert(0, eval_ctx)
        elif pass_arg is _PassArg.environment:
            args.insert(0, eval_ctx.environment)

        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise Impossible() from e


class Filter(_FilterTestCommon):
    """Apply a filter to an expression. ``name`` is the name of the
    filter, the other fields are the same as :class:`Call`.

    If ``node`` is ``None``, the filter is being used in a filter block
    and is applied to the content of the block.
    """

    node: t.Optional[Expr]  # type: ignore

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        if self.node is None:
            raise Impossible()

        return super().as_const(eval_ctx=eval_ctx)


class Test(_FilterTestCommon):
    """Apply a test to an expression. ``name`` is the name of the test,
    the other field are the same as :class:`Call`.

    .. versionchanged:: 3.0
        ``as_const`` shares the same logic for filters and tests. Tests
        check for volatile, async, and ``@pass_context`` etc.
        decorators.
    """

    _is_filter = False


class Call(Expr):
    """Calls an expression.  `args` is a list of arguments, `kwargs` a list
    of keyword arguments (list of :class:`Keyword` nodes), and `dyn_args`
    and `dyn_kwargs` has to be either `None` or a node that is used as
    node for dynamic positional (``*args``) or keyword (``**kwargs``)
    arguments.
    """

    fields = ("node", "args", "kwargs", "dyn_args", "dyn_kwargs")
    node: Expr
    args: t.List[Expr]
    kwargs: t.List[Keyword]
    dyn_args: t.Optional[Expr]
    dyn_kwargs: t.Optional[Expr]


class Getitem(Expr):
    """Get an attribute or item from an expression and prefer the item."""

    fields = ("node", "arg", "ctx")
    node: Expr
    arg: Expr
    ctx: str

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        if self.ctx != "load":
            raise Impossible()

        eval_ctx = get_eval_context(self, eval_ctx)

        try:
            return eval_ctx.environment.getitem(
                self.node.as_const(eval_ctx), self.arg.as_const(eval_ctx)
            )
        except Exception as e:
            raise Impossible() from e


class Getattr(Expr):
    """Get an attribute or item from an expression that is a ascii-only
    bytestring and prefer the attribute.
    """

    fields = ("node", "attr", "ctx")
    node: Expr
    attr: str
    ctx: str

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        if self.ctx != "load":
            raise Impossible()

        eval_ctx = get_eval_context(self, eval_ctx)

        try:
            return eval_ctx.environment.getattr(self.node.as_const(eval_ctx), self.attr)
        except Exception as e:
            raise Impossible() from e


class Slice(Expr):
    """Represents a slice object.  This must only be used as argument for
    :class:`Subscript`.
    """

    fields = ("start", "stop", "step")
    start: t.Optional[Expr]
    stop: t.Optional[Expr]
    step: t.Optional[Expr]

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> slice:
        eval_ctx = get_eval_context(self, eval_ctx)

        def const(obj: t.Optional[Expr]) -> t.Optional[t.Any]:
            if obj is None:
                return None
            return obj.as_const(eval_ctx)

        return slice(const(self.start), const(self.stop), const(self.step))


class Concat(Expr):
    """Concatenates the list of expressions provided after converting
    them to strings.
    """

    fields = ("nodes",)
    nodes: t.List[Expr]

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> str:
        eval_ctx = get_eval_context(self, eval_ctx)
        return "".join(str(x.as_const(eval_ctx)) for x in self.nodes)


class Compare(Expr):
    """Compares an expression with some other expressions.  `ops` must be a
    list of :class:`Operand`\\s.
    """

    fields = ("expr", "ops")
    expr: Expr
    ops: t.List["Operand"]

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)
        result = value = self.expr.as_const(eval_ctx)

        try:
            for op in self.ops:
                new_value = op.expr.as_const(eval_ctx)
                result = _cmpop_to_func[op.op](value, new_value)

                if not result:
                    return False

                value = new_value
        except Exception as e:
            raise Impossible() from e

        return result


class Operand(Helper):
    """Holds an operator and an expression."""

    fields = ("op", "expr")
    op: str
    expr: Expr


class Mul(BinExpr):
    """Multiplies the left with the right node."""

    operator = "*"


class Div(BinExpr):
    """Divides the left by the right node."""

    operator = "/"


class FloorDiv(BinExpr):
    """Divides the left by the right node and converts the
    result into an integer by truncating.
    """

    operator = "//"


class Add(BinExpr):
    """Add the left to the right node."""

    operator = "+"


class Sub(BinExpr):
    """Subtract the right from the left node."""

    operator = "-"


class Mod(BinExpr):
    """Left modulo right."""

    operator = "%"


class Pow(BinExpr):
    """Left to the power of right."""

    operator = "**"


class And(BinExpr):
    """Short circuited AND."""

    operator = "and"

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)
        return self.left.as_const(eval_ctx) and self.right.as_const(eval_ctx)


class Or(BinExpr):
    """Short circuited OR."""

    operator = "or"

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> t.Any:
        eval_ctx = get_eval_context(self, eval_ctx)
        return self.left.as_const(eval_ctx) or self.right.as_const(eval_ctx)


class Not(UnaryExpr):
    """Negate the expression."""

    operator = "not"


class Neg(UnaryExpr):
    """Make the expression negative."""

    operator = "-"


class Pos(UnaryExpr):
    """Make the expression positive (noop for most expressions)"""

    operator = "+"


# Helpers for extensions


class EnvironmentAttribute(Expr):
    """Loads an attribute from the environment object.  This is useful for
    extensions that want to call a callback stored on the environment.
    """

    fields = ("name",)
    name: str


class ExtensionAttribute(Expr):
    """Returns the attribute of an extension bound to the environment.
    The identifier is the identifier of the :class:`Extension`.

    This node is usually constructed by calling the
    :meth:`~jinja2.ext.Extension.attr` method on an extension.
    """

    fields = ("identifier", "name")
    identifier: str
    name: str


class ImportedName(Expr):
    """If created with an import name the import name is returned on node
    access.  For example ``ImportedName('cgi.escape')`` returns the `escape`
    function from the cgi module on evaluation.  Imports are optimized by the
    compiler so there is no need to assign them to local variables.
    """

    fields = ("importname",)
    importname: str


class InternalName(Expr):
    """An internal name in the compiler.  You cannot create these nodes
    yourself but the parser provides a
    :meth:`~jinja2.parser.Parser.free_identifier` method that creates
    a new identifier for you.  This identifier is not available from the
    template and is not treated specially by the compiler.
    """

    fields = ("name",)
    name: str

    def __init__(self) -> None:
        raise TypeError(
            "Can't create internal names.  Use the "
            "`free_identifier` method on a parser."
        )


class MarkSafe(Expr):
    """Mark the wrapped expression as safe (wrap it as `Markup`)."""

    fields = ("expr",)
    expr: Expr

    def as_const(self, eval_ctx: t.Optional[EvalContext] = None) -> Markup:
        eval_ctx = get_eval_context(self, eval_ctx)
        return Markup(self.expr.as_const(eval_ctx))


class MarkSafeIfAutoescape(Expr):
    """Mark the wrapped expression as safe (wrap it as `Markup`) but
    only if autoescaping is active.

    .. versionadded:: 2.5
    """

    fields = ("expr",)
    expr: Expr

    def as_const(
        self, eval_ctx: t.Optional[EvalContext] = None
    ) -> t.Union[Markup, t.Any]:
        eval_ctx = get_eval_context(self, eval_ctx)
        if eval_ctx.volatile:
            raise Impossible()
        expr = self.expr.as_const(eval_ctx)
        if eval_ctx.autoescape:
            return Markup(expr)
        return expr


class ContextReference(Expr):
    """Returns the current template context.  It can be used like a
    :class:`Name` node, with a ``'load'`` ctx and will return the
    current :class:`~jinja2.runtime.Context` object.

    Here an example that assigns the current template name to a
    variable named `foo`::

        Assign(Name('foo', ctx='store'),
               Getattr(ContextReference(), 'name'))

    This is basically equivalent to using the
    :func:`~jinja2.pass_context` decorator when using the high-level
    API, which causes a reference to the context to be passed as the
    first argument to a function.
    """


class DerivedContextReference(Expr):
    """Return the current template context including locals. Behaves
    exactly like :class:`ContextReference`, but includes local
    variables, such as from a ``for`` loop.

    .. versionadded:: 2.11
    """


class Continue(Stmt):
    """Continue a loop."""


class Break(Stmt):
    """Break a loop."""


class Scope(Stmt):
    """An artificial scope."""

    fields = ("body",)
    body: t.List[Node]


class OverlayScope(Stmt):
    """An overlay scope for extensions.  This is a largely unoptimized scope
    that however can be used to introduce completely arbitrary variables into
    a sub scope from a dictionary or dictionary like object.  The `context`
    field has to evaluate to a dictionary object.

    Example usage::

        OverlayScope(context=self.call_method('get_context'),
                     body=[...])

    .. versionadded:: 2.10
    """

    fields = ("context", "body")
    context: Expr
    body: t.List[Node]


class EvalContextModifier(Stmt):
    """Modifies the eval context.  For each option that should be modified,
    a :class:`Keyword` has to be added to the :attr:`options` list.

    Example to change the `autoescape` setting::

        EvalContextModifier(options=[Keyword('autoescape', Const(True))])
    """

    fields = ("options",)
    options: t.List[Keyword]


class ScopedEvalContextModifier(EvalContextModifier):
    """Modifies the eval context and reverts it later.  Works exactly like
    :class:`EvalContextModifier` but will only modify the
    :class:`~jinja2.nodes.EvalContext` for nodes in the :attr:`body`.
    """

    fields = ("body",)
    body: t.List[Node]


# make sure nobody creates custom nodes
def _failing_new(*args: t.Any, **kwargs: t.Any) -> "te.NoReturn":
    raise TypeError("can't create custom node types")


NodeType.__new__ = staticmethod(_failing_new)  # type: ignore
del _failing_new

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_spend_update_writer.py ===
"""
Module responsible for

1. Writing spend increments to either in memory list of transactions or to redis
2. Reading increments from redis or in memory list of transactions and committing them to db
"""

import asyncio
import json
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union, cast, overload

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache, RedisCache
from litellm.constants import DB_SPEND_UPDATE_JOB_NAME
from litellm.proxy._types import (
    DB_CONNECTION_ERROR_TYPES,
    BaseDailySpendTransaction,
    DailyTagSpendTransaction,
    DailyTeamSpendTransaction,
    DailyUserSpendTransaction,
    DBSpendUpdateTransactions,
    Litellm_EntityType,
    LiteLLM_UserTable,
    SpendLogsMetadata,
    SpendLogsPayload,
    SpendUpdateQueueItem,
)
from litellm.proxy.db.db_transaction_queue.daily_spend_update_queue import (
    DailySpendUpdateQueue,
)
from litellm.proxy.db.db_transaction_queue.pod_lock_manager import PodLockManager
from litellm.proxy.db.db_transaction_queue.redis_update_buffer import RedisUpdateBuffer
from litellm.proxy.db.db_transaction_queue.spend_update_queue import SpendUpdateQueue

if TYPE_CHECKING:
    from litellm.proxy.utils import PrismaClient, ProxyLogging
else:
    PrismaClient = Any
    ProxyLogging = Any


class DBSpendUpdateWriter:
    """
    Module responsible for

    1. Writing spend increments to either in memory list of transactions or to redis
    2. Reading increments from redis or in memory list of transactions and committing them to db
    """

    def __init__(
        self,
        redis_cache: Optional[RedisCache] = None,
    ):
        self.redis_cache = redis_cache
        self.redis_update_buffer = RedisUpdateBuffer(redis_cache=self.redis_cache)
        self.pod_lock_manager = PodLockManager()
        self.spend_update_queue = SpendUpdateQueue()
        self.daily_spend_update_queue = DailySpendUpdateQueue()
        self.daily_team_spend_update_queue = DailySpendUpdateQueue()
        self.daily_tag_spend_update_queue = DailySpendUpdateQueue()

    async def update_database(
        # LiteLLM management object fields
        self,
        token: Optional[str],
        user_id: Optional[str],
        end_user_id: Optional[str],
        team_id: Optional[str],
        org_id: Optional[str],
        # Completion object fields
        kwargs: Optional[dict],
        completion_response: Optional[Union[litellm.ModelResponse, Any, Exception]],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        response_cost: Optional[float],
    ):
        from litellm.proxy.proxy_server import (
            disable_spend_logs,
            litellm_proxy_budget_name,
            prisma_client,
            user_api_key_cache,
        )
        from litellm.proxy.utils import ProxyUpdateSpend, hash_token

        try:
            verbose_proxy_logger.debug(
                f"Enters prisma db call, response_cost: {response_cost}, token: {token}; user_id: {user_id}; team_id: {team_id}"
            )
            if ProxyUpdateSpend.disable_spend_updates() is True:
                return
            if token is not None and isinstance(token, str) and token.startswith("sk-"):
                hashed_token = hash_token(token=token)
            else:
                hashed_token = token

            ## CREATE SPEND LOG PAYLOAD ##
            from litellm.proxy.spend_tracking.spend_tracking_utils import (
                get_logging_payload,
            )

            payload = get_logging_payload(
                kwargs=kwargs,
                response_obj=completion_response,
                start_time=start_time,
                end_time=end_time,
            )
            payload["spend"] = response_cost or 0.0
            if isinstance(payload["startTime"], datetime):
                payload["startTime"] = payload["startTime"].isoformat()
            if isinstance(payload["endTime"], datetime):
                payload["endTime"] = payload["endTime"].isoformat()

            asyncio.create_task(
                self._update_user_db(
                    response_cost=response_cost,
                    user_id=user_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    litellm_proxy_budget_name=litellm_proxy_budget_name,
                    end_user_id=end_user_id,
                )
            )
            asyncio.create_task(
                self._update_key_db(
                    response_cost=response_cost,
                    hashed_token=hashed_token,
                    prisma_client=prisma_client,
                )
            )
            asyncio.create_task(
                self._update_team_db(
                    response_cost=response_cost,
                    team_id=team_id,
                    user_id=user_id,
                    prisma_client=prisma_client,
                )
            )
            asyncio.create_task(
                self._update_org_db(
                    response_cost=response_cost,
                    org_id=org_id,
                    prisma_client=prisma_client,
                )
            )

            if disable_spend_logs is False:
                await self._insert_spend_log_to_db(
                    payload=payload,
                    prisma_client=prisma_client,
                )
            else:
                verbose_proxy_logger.info(
                    "disable_spend_logs=True. Skipping writing spend logs to db. Other spend updates - Key/User/Team table will still occur."
                )

            asyncio.create_task(
                self.add_spend_log_transaction_to_daily_user_transaction(
                    payload=payload,
                    prisma_client=prisma_client,
                )
            )

            asyncio.create_task(
                self.add_spend_log_transaction_to_daily_team_transaction(
                    payload=payload,
                    prisma_client=prisma_client,
                )
            )

            asyncio.create_task(
                self.add_spend_log_transaction_to_daily_tag_transaction(
                    payload=payload,
                    prisma_client=prisma_client,
                )
            )

            verbose_proxy_logger.debug("Runs spend update on all tables")
        except Exception:
            verbose_proxy_logger.debug(
                f"Error updating Prisma database: {traceback.format_exc()}"
            )

    async def _update_key_db(
        self,
        response_cost: Optional[float],
        hashed_token: Optional[str],
        prisma_client: Optional[PrismaClient],
    ):
        try:
            if hashed_token is None or prisma_client is None:
                return

            await self.spend_update_queue.add_update(
                update=SpendUpdateQueueItem(
                    entity_type=Litellm_EntityType.KEY,
                    entity_id=hashed_token,
                    response_cost=response_cost,
                )
            )
        except Exception as e:
            verbose_proxy_logger.exception(
                f"Update Key DB Call failed to execute - {str(e)}"
            )
            raise e

    async def _update_user_db(
        self,
        response_cost: Optional[float],
        user_id: Optional[str],
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        litellm_proxy_budget_name: Optional[str],
        end_user_id: Optional[str] = None,
    ):
        """
        - Update that user's row
        - Update litellm-proxy-budget row (global proxy spend)
        """
        ## if an end-user is passed in, do an upsert - we can't guarantee they already exist in db
        existing_user_obj = await user_api_key_cache.async_get_cache(key=user_id)
        if existing_user_obj is not None and isinstance(existing_user_obj, dict):
            existing_user_obj = LiteLLM_UserTable(**existing_user_obj)
        try:
            if prisma_client is not None:  # update
                user_ids = [user_id]
                if (
                    litellm.max_budget > 0
                ):  # track global proxy budget, if user set max budget
                    user_ids.append(litellm_proxy_budget_name)

                for _id in user_ids:
                    if _id is not None:
                        await self.spend_update_queue.add_update(
                            update=SpendUpdateQueueItem(
                                entity_type=Litellm_EntityType.USER,
                                entity_id=_id,
                                response_cost=response_cost,
                            )
                        )

                if end_user_id is not None:
                    await self.spend_update_queue.add_update(
                        update=SpendUpdateQueueItem(
                            entity_type=Litellm_EntityType.END_USER,
                            entity_id=end_user_id,
                            response_cost=response_cost,
                        )
                    )
        except Exception as e:
            verbose_proxy_logger.info(
                "\033[91m"
                + f"Update User DB call failed to execute {str(e)}\n{traceback.format_exc()}"
            )

    async def _update_team_db(
        self,
        response_cost: Optional[float],
        team_id: Optional[str],
        user_id: Optional[str],
        prisma_client: Optional[PrismaClient],
    ):
        try:
            if team_id is None or prisma_client is None:
                verbose_proxy_logger.debug(
                    "track_cost_callback: team_id is None or prisma_client is None. Not tracking spend for team"
                )
                return

            await self.spend_update_queue.add_update(
                update=SpendUpdateQueueItem(
                    entity_type=Litellm_EntityType.TEAM,
                    entity_id=team_id,
                    response_cost=response_cost,
                )
            )

            try:
                # Track spend of the team member within this team
                if user_id is not None:
                    # key is "team_id::<value>::user_id::<value>"
                    team_member_key = f"team_id::{team_id}::user_id::{user_id}"
                    await self.spend_update_queue.add_update(
                        update=SpendUpdateQueueItem(
                            entity_type=Litellm_EntityType.TEAM_MEMBER,
                            entity_id=team_member_key,
                            response_cost=response_cost,
                        )
                    )
            except Exception:
                pass
        except Exception as e:
            verbose_proxy_logger.info(
                f"Update Team DB failed to execute - {str(e)}\n{traceback.format_exc()}"
            )
            raise e

    async def _update_org_db(
        self,
        response_cost: Optional[float],
        org_id: Optional[str],
        prisma_client: Optional[PrismaClient],
    ):
        try:
            if org_id is None or prisma_client is None:
                verbose_proxy_logger.debug(
                    "track_cost_callback: org_id is None or prisma_client is None. Not tracking spend for org"
                )
                return

            await self.spend_update_queue.add_update(
                update=SpendUpdateQueueItem(
                    entity_type=Litellm_EntityType.ORGANIZATION,
                    entity_id=org_id,
                    response_cost=response_cost,
                )
            )
        except Exception as e:
            verbose_proxy_logger.info(
                f"Update Org DB failed to execute - {str(e)}\n{traceback.format_exc()}"
            )
            raise e

    async def _insert_spend_log_to_db(
        self,
        payload: Union[dict, SpendLogsPayload],
        prisma_client: Optional[PrismaClient] = None,
        spend_logs_url: Optional[str] = os.getenv("SPEND_LOGS_URL"),
    ) -> Optional[PrismaClient]:
        verbose_proxy_logger.info(
            "Writing spend log to db - request_id: {}, spend: {}".format(
                payload.get("request_id"), payload.get("spend")
            )
        )
        if prisma_client is not None and spend_logs_url is not None:
            prisma_client.spend_log_transactions.append(payload)
        elif prisma_client is not None:
            prisma_client.spend_log_transactions.append(payload)
        else:
            verbose_proxy_logger.debug(
                "prisma_client is None. Skipping writing spend logs to db."
            )

        return prisma_client

    async def db_update_spend_transaction_handler(
        self,
        prisma_client: PrismaClient,
        n_retry_times: int,
        proxy_logging_obj: ProxyLogging,
    ):
        """
        Handles commiting update spend transactions to db

        `UPDATES` can lead to deadlocks, hence we handle them separately

        Args:
            prisma_client: PrismaClient object
            n_retry_times: int, number of retry times
            proxy_logging_obj: ProxyLogging object

        How this works:
        - Check `general_settings.use_redis_transaction_buffer`
            - If enabled, write in-memory transactions to Redis
            - Check if this Pod should read from the DB
        else:
            - Regular flow of this method
        """
        if RedisUpdateBuffer._should_commit_spend_updates_to_redis():
            await self._commit_spend_updates_to_db_with_redis(
                prisma_client=prisma_client,
                n_retry_times=n_retry_times,
                proxy_logging_obj=proxy_logging_obj,
            )

        else:
            await self._commit_spend_updates_to_db_without_redis_buffer(
                prisma_client=prisma_client,
                n_retry_times=n_retry_times,
                proxy_logging_obj=proxy_logging_obj,
            )

    async def _commit_spend_updates_to_db_with_redis(
        self,
        prisma_client: PrismaClient,
        n_retry_times: int,
        proxy_logging_obj: ProxyLogging,
    ):
        """
        Handler to commit spend updates to Redis and attempt to acquire lock to commit to db

        This is a v2 scalable approach to first commit spend updates to redis, then commit to db

        This minimizes DB Deadlocks since
            - All pods only need to write their spend updates to redis
            - Only 1 pod will commit to db at a time (based on if it can acquire the lock over writing to DB)
        """
        await self.redis_update_buffer.store_in_memory_spend_updates_in_redis(
            spend_update_queue=self.spend_update_queue,
            daily_spend_update_queue=self.daily_spend_update_queue,
            daily_team_spend_update_queue=self.daily_team_spend_update_queue,
            daily_tag_spend_update_queue=self.daily_tag_spend_update_queue,
        )

        # Only commit from redis to db if this pod is the leader
        if await self.pod_lock_manager.acquire_lock(
            cronjob_id=DB_SPEND_UPDATE_JOB_NAME,
        ):
            verbose_proxy_logger.debug("acquired lock for spend updates")

            try:
                db_spend_update_transactions = (
                    await self.redis_update_buffer.get_all_update_transactions_from_redis_buffer()
                )
                if db_spend_update_transactions is not None:
                    await self._commit_spend_updates_to_db(
                        prisma_client=prisma_client,
                        n_retry_times=n_retry_times,
                        proxy_logging_obj=proxy_logging_obj,
                        db_spend_update_transactions=db_spend_update_transactions,
                    )

                daily_spend_update_transactions = (
                    await self.redis_update_buffer.get_all_daily_spend_update_transactions_from_redis_buffer()
                )
                if daily_spend_update_transactions is not None:
                    await DBSpendUpdateWriter.update_daily_user_spend(
                        n_retry_times=n_retry_times,
                        prisma_client=prisma_client,
                        proxy_logging_obj=proxy_logging_obj,
                        daily_spend_transactions=daily_spend_update_transactions,
                    )
                daily_team_spend_update_transactions = (
                    await self.redis_update_buffer.get_all_daily_team_spend_update_transactions_from_redis_buffer()
                )
                if daily_team_spend_update_transactions is not None:
                    await DBSpendUpdateWriter.update_daily_team_spend(
                        n_retry_times=n_retry_times,
                        prisma_client=prisma_client,
                        proxy_logging_obj=proxy_logging_obj,
                        daily_spend_transactions=daily_team_spend_update_transactions,
                    )

                daily_tag_spend_update_transactions = (
                    await self.redis_update_buffer.get_all_daily_tag_spend_update_transactions_from_redis_buffer()
                )
                if daily_tag_spend_update_transactions is not None:
                    await DBSpendUpdateWriter.update_daily_tag_spend(
                        n_retry_times=n_retry_times,
                        prisma_client=prisma_client,
                        proxy_logging_obj=proxy_logging_obj,
                        daily_spend_transactions=daily_tag_spend_update_transactions,
                    )
            except Exception as e:
                verbose_proxy_logger.error(f"Error committing spend updates: {e}")
            finally:
                await self.pod_lock_manager.release_lock(
                    cronjob_id=DB_SPEND_UPDATE_JOB_NAME,
                )

    async def _commit_spend_updates_to_db_without_redis_buffer(
        self,
        prisma_client: PrismaClient,
        n_retry_times: int,
        proxy_logging_obj: ProxyLogging,
    ):
        """
        Commits all the spend `UPDATE` transactions to the Database

        This is the regular flow of committing to db without using a redis buffer

        Note: This flow causes Deadlocks in production (1K RPS+). Use self._commit_spend_updates_to_db_with_redis() instead if you expect 1K+ RPS.
        """

        # Aggregate all in memory spend updates (key, user, end_user, team, team_member, org) and commit to db
        ################## Spend Update Transactions ##################
        db_spend_update_transactions = (
            await self.spend_update_queue.flush_and_get_aggregated_db_spend_update_transactions()
        )
        await self._commit_spend_updates_to_db(
            prisma_client=prisma_client,
            n_retry_times=n_retry_times,
            proxy_logging_obj=proxy_logging_obj,
            db_spend_update_transactions=db_spend_update_transactions,
        )

        ################## Daily Spend Update Transactions ##################
        # Aggregate all in memory daily spend transactions and commit to db
        daily_spend_update_transactions = cast(
            Dict[str, DailyUserSpendTransaction],
            await self.daily_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions(),
        )

        await DBSpendUpdateWriter.update_daily_user_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_spend_update_transactions,
        )

        ################## Daily Team Spend Update Transactions ##################
        # Aggregate all in memory daily team spend transactions and commit to db
        daily_team_spend_update_transactions = cast(
            Dict[str, DailyTeamSpendTransaction],
            await self.daily_team_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions(),
        )

        await DBSpendUpdateWriter.update_daily_team_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_team_spend_update_transactions,
        )

        ################## Daily Tag Spend Update Transactions ##################
        # Aggregate all in memory daily tag spend transactions and commit to db
        daily_tag_spend_update_transactions = cast(
            Dict[str, DailyTagSpendTransaction],
            await self.daily_tag_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions(),
        )

        await DBSpendUpdateWriter.update_daily_tag_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_tag_spend_update_transactions,
        )

    async def _commit_spend_updates_to_db(  # noqa: PLR0915
        self,
        prisma_client: PrismaClient,
        n_retry_times: int,
        proxy_logging_obj: ProxyLogging,
        db_spend_update_transactions: DBSpendUpdateTransactions,
    ):
        """
        Commits all the spend `UPDATE` transactions to the Database

        """
        from litellm.proxy.utils import (
            ProxyUpdateSpend,
            _raise_failed_update_spend_exception,
        )

        ### UPDATE USER TABLE ###
        user_list_transactions = db_spend_update_transactions["user_list_transactions"]
        verbose_proxy_logger.debug(
            "User Spend transactions: {}".format(user_list_transactions)
        )
        if (
            user_list_transactions is not None
            and len(user_list_transactions.keys()) > 0
        ):
            for i in range(n_retry_times + 1):
                start_time = time.time()
                try:
                    async with prisma_client.db.tx(
                        timeout=timedelta(seconds=60)
                    ) as transaction:
                        async with transaction.batch_() as batcher:
                            for (
                                user_id,
                                response_cost,
                            ) in user_list_transactions.items():
                                batcher.litellm_usertable.update_many(
                                    where={"user_id": user_id},
                                    data={"spend": {"increment": response_cost}},
                                )
                    break
                except DB_CONNECTION_ERROR_TYPES as e:
                    if (
                        i >= n_retry_times
                    ):  # If we've reached the maximum number of retries
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    # Optionally, sleep for a bit before retrying
                    await asyncio.sleep(2**i)  # Exponential backoff
                except Exception as e:
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )

        ### UPDATE END-USER TABLE ###
        end_user_list_transactions = db_spend_update_transactions[
            "end_user_list_transactions"
        ]
        verbose_proxy_logger.debug(
            "End-User Spend transactions: {}".format(end_user_list_transactions)
        )
        if (
            end_user_list_transactions is not None
            and len(end_user_list_transactions.keys()) > 0
        ):
            await ProxyUpdateSpend.update_end_user_spend(
                n_retry_times=n_retry_times,
                prisma_client=prisma_client,
                proxy_logging_obj=proxy_logging_obj,
                end_user_list_transactions=end_user_list_transactions,
            )
        ### UPDATE KEY TABLE ###
        key_list_transactions = db_spend_update_transactions["key_list_transactions"]
        verbose_proxy_logger.debug(
            "KEY Spend transactions: {}".format(key_list_transactions)
        )
        if key_list_transactions is not None and len(key_list_transactions.keys()) > 0:
            for i in range(n_retry_times + 1):
                start_time = time.time()
                try:
                    async with prisma_client.db.tx(
                        timeout=timedelta(seconds=60)
                    ) as transaction:
                        async with transaction.batch_() as batcher:
                            for (
                                token,
                                response_cost,
                            ) in key_list_transactions.items():
                                batcher.litellm_verificationtoken.update_many(  # 'update_many' prevents error from being raised if no row exists
                                    where={"token": token},
                                    data={"spend": {"increment": response_cost}},
                                )
                    break
                except DB_CONNECTION_ERROR_TYPES as e:
                    if (
                        i >= n_retry_times
                    ):  # If we've reached the maximum number of retries
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    # Optionally, sleep for a bit before retrying
                    await asyncio.sleep(2**i)  # Exponential backoff
                except Exception as e:
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )

        ### UPDATE TEAM TABLE ###
        team_list_transactions = db_spend_update_transactions["team_list_transactions"]
        verbose_proxy_logger.debug(
            "Team Spend transactions: {}".format(team_list_transactions)
        )
        if (
            team_list_transactions is not None
            and len(team_list_transactions.keys()) > 0
        ):
            for i in range(n_retry_times + 1):
                start_time = time.time()
                try:
                    async with prisma_client.db.tx(
                        timeout=timedelta(seconds=60)
                    ) as transaction:
                        async with transaction.batch_() as batcher:
                            for (
                                team_id,
                                response_cost,
                            ) in team_list_transactions.items():
                                verbose_proxy_logger.debug(
                                    "Updating spend for team id={} by {}".format(
                                        team_id, response_cost
                                    )
                                )
                                batcher.litellm_teamtable.update_many(  # 'update_many' prevents error from being raised if no row exists
                                    where={"team_id": team_id},
                                    data={"spend": {"increment": response_cost}},
                                )
                    break
                except DB_CONNECTION_ERROR_TYPES as e:
                    if (
                        i >= n_retry_times
                    ):  # If we've reached the maximum number of retries
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    # Optionally, sleep for a bit before retrying
                    await asyncio.sleep(2**i)  # Exponential backoff
                except Exception as e:
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )

        ### UPDATE TEAM Membership TABLE with spend ###
        team_member_list_transactions = db_spend_update_transactions[
            "team_member_list_transactions"
        ]
        verbose_proxy_logger.debug(
            "Team Membership Spend transactions: {}".format(
                team_member_list_transactions
            )
        )
        if (
            team_member_list_transactions is not None
            and len(team_member_list_transactions.keys()) > 0
        ):
            for i in range(n_retry_times + 1):
                start_time = time.time()
                try:
                    async with prisma_client.db.tx(
                        timeout=timedelta(seconds=60)
                    ) as transaction:
                        async with transaction.batch_() as batcher:
                            for (
                                key,
                                response_cost,
                            ) in team_member_list_transactions.items():
                                # key is "team_id::<value>::user_id::<value>"
                                team_id = key.split("::")[1]
                                user_id = key.split("::")[3]

                                batcher.litellm_teammembership.update_many(  # 'update_many' prevents error from being raised if no row exists
                                    where={"team_id": team_id, "user_id": user_id},
                                    data={"spend": {"increment": response_cost}},
                                )
                    break
                except DB_CONNECTION_ERROR_TYPES as e:
                    if (
                        i >= n_retry_times
                    ):  # If we've reached the maximum number of retries
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    # Optionally, sleep for a bit before retrying
                    await asyncio.sleep(2**i)  # Exponential backoff
                except Exception as e:
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )

        ### UPDATE ORG TABLE ###
        org_list_transactions = db_spend_update_transactions["org_list_transactions"]
        verbose_proxy_logger.debug(
            "Org Spend transactions: {}".format(org_list_transactions)
        )
        if org_list_transactions is not None and len(org_list_transactions.keys()) > 0:
            for i in range(n_retry_times + 1):
                start_time = time.time()
                try:
                    async with prisma_client.db.tx(
                        timeout=timedelta(seconds=60)
                    ) as transaction:
                        async with transaction.batch_() as batcher:
                            for (
                                org_id,
                                response_cost,
                            ) in org_list_transactions.items():
                                batcher.litellm_organizationtable.update_many(  # 'update_many' prevents error from being raised if no row exists
                                    where={"organization_id": org_id},
                                    data={"spend": {"increment": response_cost}},
                                )
                    break
                except DB_CONNECTION_ERROR_TYPES as e:
                    if (
                        i >= n_retry_times
                    ):  # If we've reached the maximum number of retries
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    # Optionally, sleep for a bit before retrying
                    await asyncio.sleep(2**i)  # Exponential backoff
                except Exception as e:
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )

    @overload
    @staticmethod
    async def _update_daily_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyUserSpendTransaction],
        entity_type: Literal["user"],
        entity_id_field: str,
        table_name: str,
        unique_constraint_name: str,
    ) -> None:
        ...

    @overload
    @staticmethod
    async def _update_daily_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyTeamSpendTransaction],
        entity_type: Literal["team"],
        entity_id_field: str,
        table_name: str,
        unique_constraint_name: str,
    ) -> None:
        ...

    @overload
    @staticmethod
    async def _update_daily_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyTagSpendTransaction],
        entity_type: Literal["tag"],
        entity_id_field: str,
        table_name: str,
        unique_constraint_name: str,
    ) -> None:
        ...

    @staticmethod
    async def _update_daily_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Union[
            Dict[str, DailyUserSpendTransaction],
            Dict[str, DailyTeamSpendTransaction],
            Dict[str, DailyTagSpendTransaction],
        ],
        entity_type: Literal["user", "team", "tag"],
        entity_id_field: str,
        table_name: str,
        unique_constraint_name: str,
    ) -> None:
        """
        Generic function to update daily spend for any entity type (user, team, tag)
        """
        from litellm.proxy.utils import _raise_failed_update_spend_exception

        verbose_proxy_logger.debug(
            f"Daily {entity_type.capitalize()} Spend transactions: {len(daily_spend_transactions)}"
        )
        BATCH_SIZE = 100
        start_time = time.time()

        try:
            for i in range(n_retry_times + 1):
                try:
                    transactions_to_process = dict(
                        list(daily_spend_transactions.items())[:BATCH_SIZE]
                    )

                    if len(transactions_to_process) == 0:
                        verbose_proxy_logger.debug(
                            f"No new transactions to process for daily {entity_type} spend update"
                        )
                        break

                    async with prisma_client.db.batch_() as batcher:
                        for _, transaction in transactions_to_process.items():
                            entity_id = transaction.get(entity_id_field)

                            # Construct the where clause dynamically
                            where_clause = {
                                unique_constraint_name: {
                                    entity_id_field: entity_id,
                                    "date": transaction["date"],
                                    "api_key": transaction["api_key"],
                                    "model": transaction["model"],
                                    "custom_llm_provider": transaction.get(
                                        "custom_llm_provider"
                                    ),
                                }
                            }

                            # Get the table dynamically
                            table = getattr(batcher, table_name)

                            # Common data structure for both create and update
                            common_data = {
                                entity_id_field: entity_id,
                                "date": transaction["date"],
                                "api_key": transaction["api_key"],
                                "model": transaction["model"],
                                "model_group": transaction.get("model_group"),
                                "custom_llm_provider": transaction.get(
                                    "custom_llm_provider"
                                ),
                                "prompt_tokens": transaction["prompt_tokens"],
                                "completion_tokens": transaction["completion_tokens"],
                                "spend": transaction["spend"],
                                "api_requests": transaction["api_requests"],
                                "successful_requests": transaction[
                                    "successful_requests"
                                ],
                                "failed_requests": transaction["failed_requests"],
                            }

                            # Add cache-related fields if they exist
                            if "cache_read_input_tokens" in transaction:
                                common_data[
                                    "cache_read_input_tokens"
                                ] = transaction.get("cache_read_input_tokens", 0)
                            if "cache_creation_input_tokens" in transaction:
                                common_data[
                                    "cache_creation_input_tokens"
                                ] = transaction.get("cache_creation_input_tokens", 0)

                            # Create update data structure
                            update_data = {
                                "prompt_tokens": {
                                    "increment": transaction["prompt_tokens"]
                                },
                                "completion_tokens": {
                                    "increment": transaction["completion_tokens"]
                                },
                                "spend": {"increment": transaction["spend"]},
                                "api_requests": {
                                    "increment": transaction["api_requests"]
                                },
                                "successful_requests": {
                                    "increment": transaction["successful_requests"]
                                },
                                "failed_requests": {
                                    "increment": transaction["failed_requests"]
                                },
                            }

                            # Add cache-related fields to update if they exist
                            if "cache_read_input_tokens" in transaction:
                                update_data["cache_read_input_tokens"] = {
                                    "increment": transaction.get(
                                        "cache_read_input_tokens", 0
                                    )
                                }
                            if "cache_creation_input_tokens" in transaction:
                                update_data["cache_creation_input_tokens"] = {
                                    "increment": transaction.get(
                                        "cache_creation_input_tokens", 0
                                    )
                                }

                            table.upsert(
                                where=where_clause,
                                data={
                                    "create": common_data,
                                    "update": update_data,
                                },
                            )

                    verbose_proxy_logger.info(
                        f"Processed {len(transactions_to_process)} daily {entity_type} transactions in {time.time() - start_time:.2f}s"
                    )

                    # Remove processed transactions
                    for key in transactions_to_process.keys():
                        daily_spend_transactions.pop(key, None)

                    break

                except DB_CONNECTION_ERROR_TYPES as e:
                    if i >= n_retry_times:
                        _raise_failed_update_spend_exception(
                            e=e,
                            start_time=start_time,
                            proxy_logging_obj=proxy_logging_obj,
                        )
                    await asyncio.sleep(2**i)

        except Exception as e:
            if "transactions_to_process" in locals():
                for key in transactions_to_process.keys():  # type: ignore
                    daily_spend_transactions.pop(key, None)
            _raise_failed_update_spend_exception(
                e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
            )

    @staticmethod
    async def update_daily_user_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyUserSpendTransaction],
    ):
        """
        Batch job to update LiteLLM_DailyUserSpend table using in-memory daily_spend_transactions
        """
        await DBSpendUpdateWriter._update_daily_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_spend_transactions,
            entity_type="user",
            entity_id_field="user_id",
            table_name="litellm_dailyuserspend",
            unique_constraint_name="user_id_date_api_key_model_custom_llm_provider",
        )

    @staticmethod
    async def update_daily_team_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyTeamSpendTransaction],
    ):
        """
        Batch job to update LiteLLM_DailyTeamSpend table using in-memory daily_spend_transactions
        """
        await DBSpendUpdateWriter._update_daily_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_spend_transactions,
            entity_type="team",
            entity_id_field="team_id",
            table_name="litellm_dailyteamspend",
            unique_constraint_name="team_id_date_api_key_model_custom_llm_provider",
        )

    @staticmethod
    async def update_daily_tag_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        daily_spend_transactions: Dict[str, DailyTagSpendTransaction],
    ):
        """
        Batch job to update LiteLLM_DailyTagSpend table using in-memory daily_spend_transactions
        """
        await DBSpendUpdateWriter._update_daily_spend(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            daily_spend_transactions=daily_spend_transactions,
            entity_type="tag",
            entity_id_field="tag",
            table_name="litellm_dailytagspend",
            unique_constraint_name="tag_date_api_key_model_custom_llm_provider",
        )

    async def _common_add_spend_log_transaction_to_daily_transaction(
        self,
        payload: Union[dict, SpendLogsPayload],
        prisma_client: PrismaClient,
        type: Literal["user", "team", "request_tags"] = "user",
    ) -> Optional[BaseDailySpendTransaction]:
        common_expected_keys = ["startTime", "api_key", "model", "custom_llm_provider"]
        if type == "user":
            expected_keys = ["user", *common_expected_keys]
        elif type == "team":
            expected_keys = ["team_id", *common_expected_keys]
        elif type == "request_tags":
            expected_keys = ["request_tags", *common_expected_keys]
        else:
            raise ValueError(f"Invalid type: {type}")

        if not all(key in payload for key in expected_keys):
            verbose_proxy_logger.debug(
                f"Missing expected keys: {expected_keys}, in payload, skipping from daily_user_spend_transactions"
            )
            return None

        request_status = prisma_client.get_request_status(payload)
        verbose_proxy_logger.info(f"Logged request status: {request_status}")
        _metadata: SpendLogsMetadata = json.loads(payload["metadata"])
        usage_obj = _metadata.get("usage_object", {}) or {}
        if isinstance(payload["startTime"], datetime):
            start_time = payload["startTime"].isoformat()
            date = start_time.split("T")[0]
        elif isinstance(payload["startTime"], str):
            date = payload["startTime"].split("T")[0]
        else:
            verbose_proxy_logger.debug(
                f"Invalid start time: {payload['startTime']}, skipping from daily_user_spend_transactions"
            )
            return None
        try:
            daily_transaction = BaseDailySpendTransaction(
                date=date,
                api_key=payload["api_key"],
                model=payload["model"],
                model_group=payload["model_group"],
                custom_llm_provider=payload["custom_llm_provider"],
                prompt_tokens=payload["prompt_tokens"],
                completion_tokens=payload["completion_tokens"],
                spend=payload["spend"],
                api_requests=1,
                successful_requests=1 if request_status == "success" else 0,
                failed_requests=1 if request_status != "success" else 0,
                cache_read_input_tokens=usage_obj.get("cache_read_input_tokens", 0)
                or 0,
                cache_creation_input_tokens=usage_obj.get(
                    "cache_creation_input_tokens", 0
                )
                or 0,
            )
            return daily_transaction
        except Exception as e:
            raise e

    async def add_spend_log_transaction_to_daily_user_transaction(
        self,
        payload: Union[dict, SpendLogsPayload],
        prisma_client: Optional[PrismaClient] = None,
    ):
        """
        Add a spend log transaction to the `daily_spend_update_queue`

        Key = @@unique([user_id, date, api_key, model, custom_llm_provider])    )

        If key exists, update the transaction with the new spend and usage
        """
        if prisma_client is None:
            verbose_proxy_logger.debug(
                "prisma_client is None. Skipping writing spend logs to db."
            )
            return

        base_daily_transaction = (
            await self._common_add_spend_log_transaction_to_daily_transaction(
                payload, prisma_client, "user"
            )
        )
        if base_daily_transaction is None:
            return

        daily_transaction_key = f"{payload['user']}_{base_daily_transaction['date']}_{payload['api_key']}_{payload['model']}_{payload['custom_llm_provider']}"
        daily_transaction = DailyUserSpendTransaction(
            user_id=payload["user"], **base_daily_transaction
        )
        await self.daily_spend_update_queue.add_update(
            update={daily_transaction_key: daily_transaction}
        )

    async def add_spend_log_transaction_to_daily_team_transaction(
        self,
        payload: SpendLogsPayload,
        prisma_client: Optional[PrismaClient] = None,
    ) -> None:
        if prisma_client is None:
            verbose_proxy_logger.debug(
                "prisma_client is None. Skipping writing spend logs to db."
            )
            return

        base_daily_transaction = (
            await self._common_add_spend_log_transaction_to_daily_transaction(
                payload, prisma_client, "team"
            )
        )
        if base_daily_transaction is None:
            return
        if payload["team_id"] is None:
            verbose_proxy_logger.debug(
                "team_id is None for request. Skipping incrementing team spend."
            )
            return

        daily_transaction_key = f"{payload['team_id']}_{base_daily_transaction['date']}_{payload['api_key']}_{payload['model']}_{payload['custom_llm_provider']}"
        daily_transaction = DailyTeamSpendTransaction(
            team_id=payload["team_id"], **base_daily_transaction
        )
        await self.daily_team_spend_update_queue.add_update(
            update={daily_transaction_key: daily_transaction}
        )

    async def add_spend_log_transaction_to_daily_tag_transaction(
        self,
        payload: SpendLogsPayload,
        prisma_client: Optional[PrismaClient] = None,
    ) -> None:
        if prisma_client is None:
            verbose_proxy_logger.debug(
                "prisma_client is None. Skipping writing spend logs to db."
            )
            return

        base_daily_transaction = (
            await self._common_add_spend_log_transaction_to_daily_transaction(
                payload, prisma_client, "request_tags"
            )
        )
        if base_daily_transaction is None:
            return
        if payload["request_tags"] is None:
            verbose_proxy_logger.debug(
                "request_tags is None for request. Skipping incrementing tag spend."
            )
            return

        request_tags = []
        if isinstance(payload["request_tags"], str):
            request_tags = json.loads(payload["request_tags"])
        elif isinstance(payload["request_tags"], list):
            request_tags = payload["request_tags"]
        else:
            raise ValueError(f"Invalid request_tags: {payload['request_tags']}")
        for tag in request_tags:
            daily_transaction_key = f"{tag}_{base_daily_transaction['date']}_{payload['api_key']}_{payload['model']}_{payload['custom_llm_provider']}"
            daily_transaction = DailyTagSpendTransaction(
                tag=tag, **base_daily_transaction
            )

            await self.daily_tag_spend_update_queue.add_update(
                update={daily_transaction_key: daily_transaction}
            )

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\types.py ===
import abc
import math
import re
import warnings
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from types import new_class
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    List,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from uuid import UUID
from weakref import WeakSet

from pydantic.v1 import errors
from pydantic.v1.datetime_parse import parse_date
from pydantic.v1.utils import import_string, update_not_none
from pydantic.v1.validators import (
    bytes_validator,
    constr_length_validator,
    constr_lower,
    constr_strip_whitespace,
    constr_upper,
    decimal_validator,
    float_finite_validator,
    float_validator,
    frozenset_validator,
    int_validator,
    list_validator,
    number_multiple_validator,
    number_size_validator,
    path_exists_validator,
    path_validator,
    set_validator,
    str_validator,
    strict_bytes_validator,
    strict_float_validator,
    strict_int_validator,
    strict_str_validator,
)

__all__ = [
    'NoneStr',
    'NoneBytes',
    'StrBytes',
    'NoneStrBytes',
    'StrictStr',
    'ConstrainedBytes',
    'conbytes',
    'ConstrainedList',
    'conlist',
    'ConstrainedSet',
    'conset',
    'ConstrainedFrozenSet',
    'confrozenset',
    'ConstrainedStr',
    'constr',
    'PyObject',
    'ConstrainedInt',
    'conint',
    'PositiveInt',
    'NegativeInt',
    'NonNegativeInt',
    'NonPositiveInt',
    'ConstrainedFloat',
    'confloat',
    'PositiveFloat',
    'NegativeFloat',
    'NonNegativeFloat',
    'NonPositiveFloat',
    'FiniteFloat',
    'ConstrainedDecimal',
    'condecimal',
    'UUID1',
    'UUID3',
    'UUID4',
    'UUID5',
    'FilePath',
    'DirectoryPath',
    'Json',
    'JsonWrapper',
    'SecretField',
    'SecretStr',
    'SecretBytes',
    'StrictBool',
    'StrictBytes',
    'StrictInt',
    'StrictFloat',
    'PaymentCardNumber',
    'ByteSize',
    'PastDate',
    'FutureDate',
    'ConstrainedDate',
    'condate',
]

NoneStr = Optional[str]
NoneBytes = Optional[bytes]
StrBytes = Union[str, bytes]
NoneStrBytes = Optional[StrBytes]
OptionalInt = Optional[int]
OptionalIntFloat = Union[OptionalInt, float]
OptionalIntFloatDecimal = Union[OptionalIntFloat, Decimal]
OptionalDate = Optional[date]
StrIntFloat = Union[str, int, float]

if TYPE_CHECKING:
    from typing_extensions import Annotated

    from pydantic.v1.dataclasses import Dataclass
    from pydantic.v1.main import BaseModel
    from pydantic.v1.typing import CallableGenerator

    ModelOrDc = Type[Union[BaseModel, Dataclass]]

T = TypeVar('T')
_DEFINED_TYPES: 'WeakSet[type]' = WeakSet()


@overload
def _registered(typ: Type[T]) -> Type[T]:
    pass


@overload
def _registered(typ: 'ConstrainedNumberMeta') -> 'ConstrainedNumberMeta':
    pass


def _registered(typ: Union[Type[T], 'ConstrainedNumberMeta']) -> Union[Type[T], 'ConstrainedNumberMeta']:
    # In order to generate valid examples of constrained types, Hypothesis needs
    # to inspect the type object - so we keep a weakref to each contype object
    # until it can be registered.  When (or if) our Hypothesis plugin is loaded,
    # it monkeypatches this function.
    # If Hypothesis is never used, the total effect is to keep a weak reference
    # which has minimal memory usage and doesn't even affect garbage collection.
    _DEFINED_TYPES.add(typ)
    return typ


class ConstrainedNumberMeta(type):
    def __new__(cls, name: str, bases: Any, dct: Dict[str, Any]) -> 'ConstrainedInt':  # type: ignore
        new_cls = cast('ConstrainedInt', type.__new__(cls, name, bases, dct))

        if new_cls.gt is not None and new_cls.ge is not None:
            raise errors.ConfigError('bounds gt and ge cannot be specified at the same time')
        if new_cls.lt is not None and new_cls.le is not None:
            raise errors.ConfigError('bounds lt and le cannot be specified at the same time')

        return _registered(new_cls)  # type: ignore


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BOOLEAN TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    StrictBool = bool
else:

    class StrictBool(int):
        """
        StrictBool to allow for bools which are not type-coerced.
        """

        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(type='boolean')

        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> bool:
            """
            Ensure that we only allow bools.
            """
            if isinstance(value, bool):
                return value

            raise errors.StrictBoolError()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ INTEGER TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstrainedInt(int, metaclass=ConstrainedNumberMeta):
    strict: bool = False
    gt: OptionalInt = None
    ge: OptionalInt = None
    lt: OptionalInt = None
    le: OptionalInt = None
    multiple_of: OptionalInt = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            exclusiveMinimum=cls.gt,
            exclusiveMaximum=cls.lt,
            minimum=cls.ge,
            maximum=cls.le,
            multipleOf=cls.multiple_of,
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield strict_int_validator if cls.strict else int_validator
        yield number_size_validator
        yield number_multiple_validator


def conint(
    *,
    strict: bool = False,
    gt: Optional[int] = None,
    ge: Optional[int] = None,
    lt: Optional[int] = None,
    le: Optional[int] = None,
    multiple_of: Optional[int] = None,
) -> Type[int]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(strict=strict, gt=gt, ge=ge, lt=lt, le=le, multiple_of=multiple_of)
    return type('ConstrainedIntValue', (ConstrainedInt,), namespace)


if TYPE_CHECKING:
    PositiveInt = int
    NegativeInt = int
    NonPositiveInt = int
    NonNegativeInt = int
    StrictInt = int
else:

    class PositiveInt(ConstrainedInt):
        gt = 0

    class NegativeInt(ConstrainedInt):
        lt = 0

    class NonPositiveInt(ConstrainedInt):
        le = 0

    class NonNegativeInt(ConstrainedInt):
        ge = 0

    class StrictInt(ConstrainedInt):
        strict = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ FLOAT TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstrainedFloat(float, metaclass=ConstrainedNumberMeta):
    strict: bool = False
    gt: OptionalIntFloat = None
    ge: OptionalIntFloat = None
    lt: OptionalIntFloat = None
    le: OptionalIntFloat = None
    multiple_of: OptionalIntFloat = None
    allow_inf_nan: Optional[bool] = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            exclusiveMinimum=cls.gt,
            exclusiveMaximum=cls.lt,
            minimum=cls.ge,
            maximum=cls.le,
            multipleOf=cls.multiple_of,
        )
        # Modify constraints to account for differences between IEEE floats and JSON
        if field_schema.get('exclusiveMinimum') == -math.inf:
            del field_schema['exclusiveMinimum']
        if field_schema.get('minimum') == -math.inf:
            del field_schema['minimum']
        if field_schema.get('exclusiveMaximum') == math.inf:
            del field_schema['exclusiveMaximum']
        if field_schema.get('maximum') == math.inf:
            del field_schema['maximum']

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield strict_float_validator if cls.strict else float_validator
        yield number_size_validator
        yield number_multiple_validator
        yield float_finite_validator


def confloat(
    *,
    strict: bool = False,
    gt: float = None,
    ge: float = None,
    lt: float = None,
    le: float = None,
    multiple_of: float = None,
    allow_inf_nan: Optional[bool] = None,
) -> Type[float]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(strict=strict, gt=gt, ge=ge, lt=lt, le=le, multiple_of=multiple_of, allow_inf_nan=allow_inf_nan)
    return type('ConstrainedFloatValue', (ConstrainedFloat,), namespace)


if TYPE_CHECKING:
    PositiveFloat = float
    NegativeFloat = float
    NonPositiveFloat = float
    NonNegativeFloat = float
    StrictFloat = float
    FiniteFloat = float
else:

    class PositiveFloat(ConstrainedFloat):
        gt = 0

    class NegativeFloat(ConstrainedFloat):
        lt = 0

    class NonPositiveFloat(ConstrainedFloat):
        le = 0

    class NonNegativeFloat(ConstrainedFloat):
        ge = 0

    class StrictFloat(ConstrainedFloat):
        strict = True

    class FiniteFloat(ConstrainedFloat):
        allow_inf_nan = False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BYTES TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstrainedBytes(bytes):
    strip_whitespace = False
    to_upper = False
    to_lower = False
    min_length: OptionalInt = None
    max_length: OptionalInt = None
    strict: bool = False

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, minLength=cls.min_length, maxLength=cls.max_length)

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield strict_bytes_validator if cls.strict else bytes_validator
        yield constr_strip_whitespace
        yield constr_upper
        yield constr_lower
        yield constr_length_validator


def conbytes(
    *,
    strip_whitespace: bool = False,
    to_upper: bool = False,
    to_lower: bool = False,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    strict: bool = False,
) -> Type[bytes]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(
        strip_whitespace=strip_whitespace,
        to_upper=to_upper,
        to_lower=to_lower,
        min_length=min_length,
        max_length=max_length,
        strict=strict,
    )
    return _registered(type('ConstrainedBytesValue', (ConstrainedBytes,), namespace))


if TYPE_CHECKING:
    StrictBytes = bytes
else:

    class StrictBytes(ConstrainedBytes):
        strict = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ STRING TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstrainedStr(str):
    strip_whitespace = False
    to_upper = False
    to_lower = False
    min_length: OptionalInt = None
    max_length: OptionalInt = None
    curtail_length: OptionalInt = None
    regex: Optional[Union[str, Pattern[str]]] = None
    strict = False

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            minLength=cls.min_length,
            maxLength=cls.max_length,
            pattern=cls.regex and cls._get_pattern(cls.regex),
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield strict_str_validator if cls.strict else str_validator
        yield constr_strip_whitespace
        yield constr_upper
        yield constr_lower
        yield constr_length_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]

        if cls.regex:
            if not re.match(cls.regex, value):
                raise errors.StrRegexError(pattern=cls._get_pattern(cls.regex))

        return value

    @staticmethod
    def _get_pattern(regex: Union[str, Pattern[str]]) -> str:
        return regex if isinstance(regex, str) else regex.pattern


def constr(
    *,
    strip_whitespace: bool = False,
    to_upper: bool = False,
    to_lower: bool = False,
    strict: bool = False,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    curtail_length: Optional[int] = None,
    regex: Optional[str] = None,
) -> Type[str]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(
        strip_whitespace=strip_whitespace,
        to_upper=to_upper,
        to_lower=to_lower,
        strict=strict,
        min_length=min_length,
        max_length=max_length,
        curtail_length=curtail_length,
        regex=regex and re.compile(regex),
    )
    return _registered(type('ConstrainedStrValue', (ConstrainedStr,), namespace))


if TYPE_CHECKING:
    StrictStr = str
else:

    class StrictStr(ConstrainedStr):
        strict = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ SET TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# This types superclass should be Set[T], but cython chokes on that...
class ConstrainedSet(set):  # type: ignore
    # Needed for pydantic to detect that this is a set
    __origin__ = set
    __args__: Set[Type[T]]  # type: ignore

    min_items: Optional[int] = None
    max_items: Optional[int] = None
    item_type: Type[T]  # type: ignore

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.set_length_validator

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, minItems=cls.min_items, maxItems=cls.max_items)

    @classmethod
    def set_length_validator(cls, v: 'Optional[Set[T]]') -> 'Optional[Set[T]]':
        if v is None:
            return None

        v = set_validator(v)
        v_len = len(v)

        if cls.min_items is not None and v_len < cls.min_items:
            raise errors.SetMinLengthError(limit_value=cls.min_items)

        if cls.max_items is not None and v_len > cls.max_items:
            raise errors.SetMaxLengthError(limit_value=cls.max_items)

        return v


def conset(item_type: Type[T], *, min_items: Optional[int] = None, max_items: Optional[int] = None) -> Type[Set[T]]:
    # __args__ is needed to conform to typing generics api
    namespace = {'min_items': min_items, 'max_items': max_items, 'item_type': item_type, '__args__': [item_type]}
    # We use new_class to be able to deal with Generic types
    return new_class('ConstrainedSetValue', (ConstrainedSet,), {}, lambda ns: ns.update(namespace))


# This types superclass should be FrozenSet[T], but cython chokes on that...
class ConstrainedFrozenSet(frozenset):  # type: ignore
    # Needed for pydantic to detect that this is a set
    __origin__ = frozenset
    __args__: FrozenSet[Type[T]]  # type: ignore

    min_items: Optional[int] = None
    max_items: Optional[int] = None
    item_type: Type[T]  # type: ignore

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.frozenset_length_validator

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, minItems=cls.min_items, maxItems=cls.max_items)

    @classmethod
    def frozenset_length_validator(cls, v: 'Optional[FrozenSet[T]]') -> 'Optional[FrozenSet[T]]':
        if v is None:
            return None

        v = frozenset_validator(v)
        v_len = len(v)

        if cls.min_items is not None and v_len < cls.min_items:
            raise errors.FrozenSetMinLengthError(limit_value=cls.min_items)

        if cls.max_items is not None and v_len > cls.max_items:
            raise errors.FrozenSetMaxLengthError(limit_value=cls.max_items)

        return v


def confrozenset(
    item_type: Type[T], *, min_items: Optional[int] = None, max_items: Optional[int] = None
) -> Type[FrozenSet[T]]:
    # __args__ is needed to conform to typing generics api
    namespace = {'min_items': min_items, 'max_items': max_items, 'item_type': item_type, '__args__': [item_type]}
    # We use new_class to be able to deal with Generic types
    return new_class('ConstrainedFrozenSetValue', (ConstrainedFrozenSet,), {}, lambda ns: ns.update(namespace))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ LIST TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# This types superclass should be List[T], but cython chokes on that...
class ConstrainedList(list):  # type: ignore
    # Needed for pydantic to detect that this is a list
    __origin__ = list
    __args__: Tuple[Type[T], ...]  # type: ignore

    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: Optional[bool] = None
    item_type: Type[T]  # type: ignore

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.list_length_validator
        if cls.unique_items:
            yield cls.unique_items_validator

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, minItems=cls.min_items, maxItems=cls.max_items, uniqueItems=cls.unique_items)

    @classmethod
    def list_length_validator(cls, v: 'Optional[List[T]]') -> 'Optional[List[T]]':
        if v is None:
            return None

        v = list_validator(v)
        v_len = len(v)

        if cls.min_items is not None and v_len < cls.min_items:
            raise errors.ListMinLengthError(limit_value=cls.min_items)

        if cls.max_items is not None and v_len > cls.max_items:
            raise errors.ListMaxLengthError(limit_value=cls.max_items)

        return v

    @classmethod
    def unique_items_validator(cls, v: 'Optional[List[T]]') -> 'Optional[List[T]]':
        if v is None:
            return None

        for i, value in enumerate(v, start=1):
            if value in v[i:]:
                raise errors.ListUniqueItemsError()

        return v


def conlist(
    item_type: Type[T], *, min_items: Optional[int] = None, max_items: Optional[int] = None, unique_items: bool = None
) -> Type[List[T]]:
    # __args__ is needed to conform to typing generics api
    namespace = dict(
        min_items=min_items, max_items=max_items, unique_items=unique_items, item_type=item_type, __args__=(item_type,)
    )
    # We use new_class to be able to deal with Generic types
    return new_class('ConstrainedListValue', (ConstrainedList,), {}, lambda ns: ns.update(namespace))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PYOBJECT TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


if TYPE_CHECKING:
    PyObject = Callable[..., Any]
else:

    class PyObject:
        validate_always = True

        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> Any:
            if isinstance(value, Callable):
                return value

            try:
                value = str_validator(value)
            except errors.StrError:
                raise errors.PyObjectError(error_message='value is neither a valid import path not a valid callable')

            try:
                return import_string(value)
            except ImportError as e:
                raise errors.PyObjectError(error_message=str(e))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DECIMAL TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstrainedDecimal(Decimal, metaclass=ConstrainedNumberMeta):
    gt: OptionalIntFloatDecimal = None
    ge: OptionalIntFloatDecimal = None
    lt: OptionalIntFloatDecimal = None
    le: OptionalIntFloatDecimal = None
    max_digits: OptionalInt = None
    decimal_places: OptionalInt = None
    multiple_of: OptionalIntFloatDecimal = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            exclusiveMinimum=cls.gt,
            exclusiveMaximum=cls.lt,
            minimum=cls.ge,
            maximum=cls.le,
            multipleOf=cls.multiple_of,
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield decimal_validator
        yield number_size_validator
        yield number_multiple_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: Decimal) -> Decimal:
        try:
            normalized_value = value.normalize()
        except InvalidOperation:
            normalized_value = value
        digit_tuple, exponent = normalized_value.as_tuple()[1:]
        if exponent in {'F', 'n', 'N'}:
            raise errors.DecimalIsNotFiniteError()

        if exponent >= 0:
            # A positive exponent adds that many trailing zeros.
            digits = len(digit_tuple) + exponent
            decimals = 0
        else:
            # If the absolute value of the negative exponent is larger than the
            # number of digits, then it's the same as the number of digits,
            # because it'll consume all of the digits in digit_tuple and then
            # add abs(exponent) - len(digit_tuple) leading zeros after the
            # decimal point.
            if abs(exponent) > len(digit_tuple):
                digits = decimals = abs(exponent)
            else:
                digits = len(digit_tuple)
                decimals = abs(exponent)
        whole_digits = digits - decimals

        if cls.max_digits is not None and digits > cls.max_digits:
            raise errors.DecimalMaxDigitsError(max_digits=cls.max_digits)

        if cls.decimal_places is not None and decimals > cls.decimal_places:
            raise errors.DecimalMaxPlacesError(decimal_places=cls.decimal_places)

        if cls.max_digits is not None and cls.decimal_places is not None:
            expected = cls.max_digits - cls.decimal_places
            if whole_digits > expected:
                raise errors.DecimalWholeDigitsError(whole_digits=expected)

        return value


def condecimal(
    *,
    gt: Decimal = None,
    ge: Decimal = None,
    lt: Decimal = None,
    le: Decimal = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    multiple_of: Decimal = None,
) -> Type[Decimal]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(
        gt=gt, ge=ge, lt=lt, le=le, max_digits=max_digits, decimal_places=decimal_places, multiple_of=multiple_of
    )
    return type('ConstrainedDecimalValue', (ConstrainedDecimal,), namespace)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ UUID TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    UUID1 = UUID
    UUID3 = UUID
    UUID4 = UUID
    UUID5 = UUID
else:

    class UUID1(UUID):
        _required_version = 1

        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(type='string', format=f'uuid{cls._required_version}')

    class UUID3(UUID1):
        _required_version = 3

    class UUID4(UUID1):
        _required_version = 4

    class UUID5(UUID1):
        _required_version = 5


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PATH TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    FilePath = Path
    DirectoryPath = Path
else:

    class FilePath(Path):
        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(format='file-path')

        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield path_validator
            yield path_exists_validator
            yield cls.validate

        @classmethod
        def validate(cls, value: Path) -> Path:
            if not value.is_file():
                raise errors.PathNotAFileError(path=value)

            return value

    class DirectoryPath(Path):
        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(format='directory-path')

        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield path_validator
            yield path_exists_validator
            yield cls.validate

        @classmethod
        def validate(cls, value: Path) -> Path:
            if not value.is_dir():
                raise errors.PathNotADirectoryError(path=value)

            return value


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ JSON TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class JsonWrapper:
    pass


class JsonMeta(type):
    def __getitem__(self, t: Type[Any]) -> Type[JsonWrapper]:
        if t is Any:
            return Json  # allow Json[Any] to replecate plain Json
        return _registered(type('JsonWrapperValue', (JsonWrapper,), {'inner_type': t}))


if TYPE_CHECKING:
    Json = Annotated[T, ...]  # Json[list[str]] will be recognized by type checkers as list[str]

else:

    class Json(metaclass=JsonMeta):
        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(type='string', format='json-string')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ SECRET TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class SecretField(abc.ABC):
    """
    Note: this should be implemented as a generic like `SecretField(ABC, Generic[T])`,
          the `__init__()` should be part of the abstract class and the
          `get_secret_value()` method should use the generic `T` type.

          However Cython doesn't support very well generics at the moment and
          the generated code fails to be imported (see
          https://github.com/cython/cython/issues/2753).
    """

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.get_secret_value() == other.get_secret_value()

    def __str__(self) -> str:
        return '**********' if self.get_secret_value() else ''

    def __hash__(self) -> int:
        return hash(self.get_secret_value())

    @abc.abstractmethod
    def get_secret_value(self) -> Any:  # pragma: no cover
        ...


class SecretStr(SecretField):
    min_length: OptionalInt = None
    max_length: OptionalInt = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            type='string',
            writeOnly=True,
            format='password',
            minLength=cls.min_length,
            maxLength=cls.max_length,
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate
        yield constr_length_validator

    @classmethod
    def validate(cls, value: Any) -> 'SecretStr':
        if isinstance(value, cls):
            return value
        value = str_validator(value)
        return cls(value)

    def __init__(self, value: str):
        self._secret_value = value

    def __repr__(self) -> str:
        return f"SecretStr('{self}')"

    def __len__(self) -> int:
        return len(self._secret_value)

    def display(self) -> str:
        warnings.warn('`secret_str.display()` is deprecated, use `str(secret_str)` instead', DeprecationWarning)
        return str(self)

    def get_secret_value(self) -> str:
        return self._secret_value


class SecretBytes(SecretField):
    min_length: OptionalInt = None
    max_length: OptionalInt = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(
            field_schema,
            type='string',
            writeOnly=True,
            format='password',
            minLength=cls.min_length,
            maxLength=cls.max_length,
        )

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate
        yield constr_length_validator

    @classmethod
    def validate(cls, value: Any) -> 'SecretBytes':
        if isinstance(value, cls):
            return value
        value = bytes_validator(value)
        return cls(value)

    def __init__(self, value: bytes):
        self._secret_value = value

    def __repr__(self) -> str:
        return f"SecretBytes(b'{self}')"

    def __len__(self) -> int:
        return len(self._secret_value)

    def display(self) -> str:
        warnings.warn('`secret_bytes.display()` is deprecated, use `str(secret_bytes)` instead', DeprecationWarning)
        return str(self)

    def get_secret_value(self) -> bytes:
        return self._secret_value


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PAYMENT CARD TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PaymentCardBrand(str, Enum):
    # If you add another card type, please also add it to the
    # Hypothesis strategy in `pydantic._hypothesis_plugin`.
    amex = 'American Express'
    mastercard = 'Mastercard'
    visa = 'Visa'
    other = 'other'

    def __str__(self) -> str:
        return self.value


class PaymentCardNumber(str):
    """
    Based on: https://en.wikipedia.org/wiki/Payment_card_number
    """

    strip_whitespace: ClassVar[bool] = True
    min_length: ClassVar[int] = 12
    max_length: ClassVar[int] = 19
    bin: str
    last4: str
    brand: PaymentCardBrand

    def __init__(self, card_number: str):
        self.bin = card_number[:6]
        self.last4 = card_number[-4:]
        self.brand = self._get_brand(card_number)

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield str_validator
        yield constr_strip_whitespace
        yield constr_length_validator
        yield cls.validate_digits
        yield cls.validate_luhn_check_digit
        yield cls
        yield cls.validate_length_for_brand

    @property
    def masked(self) -> str:
        num_masked = len(self) - 10  # len(bin) + len(last4) == 10
        return f'{self.bin}{"*" * num_masked}{self.last4}'

    @classmethod
    def validate_digits(cls, card_number: str) -> str:
        if not card_number.isdigit():
            raise errors.NotDigitError
        return card_number

    @classmethod
    def validate_luhn_check_digit(cls, card_number: str) -> str:
        """
        Based on: https://en.wikipedia.org/wiki/Luhn_algorithm
        """
        sum_ = int(card_number[-1])
        length = len(card_number)
        parity = length % 2
        for i in range(length - 1):
            digit = int(card_number[i])
            if i % 2 == parity:
                digit *= 2
            if digit > 9:
                digit -= 9
            sum_ += digit
        valid = sum_ % 10 == 0
        if not valid:
            raise errors.LuhnValidationError
        return card_number

    @classmethod
    def validate_length_for_brand(cls, card_number: 'PaymentCardNumber') -> 'PaymentCardNumber':
        """
        Validate length based on BIN for major brands:
        https://en.wikipedia.org/wiki/Payment_card_number#Issuer_identification_number_(IIN)
        """
        required_length: Union[None, int, str] = None
        if card_number.brand in PaymentCardBrand.mastercard:
            required_length = 16
            valid = len(card_number) == required_length
        elif card_number.brand == PaymentCardBrand.visa:
            required_length = '13, 16 or 19'
            valid = len(card_number) in {13, 16, 19}
        elif card_number.brand == PaymentCardBrand.amex:
            required_length = 15
            valid = len(card_number) == required_length
        else:
            valid = True
        if not valid:
            raise errors.InvalidLengthForBrand(brand=card_number.brand, required_length=required_length)
        return card_number

    @staticmethod
    def _get_brand(card_number: str) -> PaymentCardBrand:
        if card_number[0] == '4':
            brand = PaymentCardBrand.visa
        elif 51 <= int(card_number[:2]) <= 55:
            brand = PaymentCardBrand.mastercard
        elif card_number[:2] in {'34', '37'}:
            brand = PaymentCardBrand.amex
        else:
            brand = PaymentCardBrand.other
        return brand


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BYTE SIZE TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BYTE_SIZES = {
    'b': 1,
    'kb': 10**3,
    'mb': 10**6,
    'gb': 10**9,
    'tb': 10**12,
    'pb': 10**15,
    'eb': 10**18,
    'kib': 2**10,
    'mib': 2**20,
    'gib': 2**30,
    'tib': 2**40,
    'pib': 2**50,
    'eib': 2**60,
}
BYTE_SIZES.update({k.lower()[0]: v for k, v in BYTE_SIZES.items() if 'i' not in k})
byte_string_re = re.compile(r'^\s*(\d*\.?\d+)\s*(\w+)?', re.IGNORECASE)


class ByteSize(int):
    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, v: StrIntFloat) -> 'ByteSize':
        try:
            return cls(int(v))
        except ValueError:
            pass

        str_match = byte_string_re.match(str(v))
        if str_match is None:
            raise errors.InvalidByteSize()

        scalar, unit = str_match.groups()
        if unit is None:
            unit = 'b'

        try:
            unit_mult = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise errors.InvalidByteSizeUnit(unit=unit)

        return cls(int(float(scalar) * unit_mult))

    def human_readable(self, decimal: bool = False) -> str:
        if decimal:
            divisor = 1000
            units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
            final_unit = 'EB'
        else:
            divisor = 1024
            units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
            final_unit = 'EiB'

        num = float(self)
        for unit in units:
            if abs(num) < divisor:
                return f'{num:0.1f}{unit}'
            num /= divisor

        return f'{num:0.1f}{final_unit}'

    def to(self, unit: str) -> float:
        try:
            unit_div = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise errors.InvalidByteSizeUnit(unit=unit)

        return self / unit_div


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DATE TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    PastDate = date
    FutureDate = date
else:

    class PastDate(date):
        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield parse_date
            yield cls.validate

        @classmethod
        def validate(cls, value: date) -> date:
            if value >= date.today():
                raise errors.DateNotInThePastError()

            return value

    class FutureDate(date):
        @classmethod
        def __get_validators__(cls) -> 'CallableGenerator':
            yield parse_date
            yield cls.validate

        @classmethod
        def validate(cls, value: date) -> date:
            if value <= date.today():
                raise errors.DateNotInTheFutureError()

            return value


class ConstrainedDate(date, metaclass=ConstrainedNumberMeta):
    gt: OptionalDate = None
    ge: OptionalDate = None
    lt: OptionalDate = None
    le: OptionalDate = None

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, exclusiveMinimum=cls.gt, exclusiveMaximum=cls.lt, minimum=cls.ge, maximum=cls.le)

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield parse_date
        yield number_size_validator


def condate(
    *,
    gt: date = None,
    ge: date = None,
    lt: date = None,
    le: date = None,
) -> Type[date]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(gt=gt, ge=ge, lt=lt, le=le)
    return type('ConstrainedDateValue', (ConstrainedDate,), namespace)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\python.py ===
"""
    pygments.lexers.python
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Python and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import keyword

from pygments.lexer import DelegatingLexer, RegexLexer, include, \
    bygroups, using, default, words, combined, this
from pygments.util import get_bool_opt, shebang_matches
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Other, Error, Whitespace
from pygments import unistring as uni

__all__ = ['PythonLexer', 'PythonConsoleLexer', 'PythonTracebackLexer',
           'Python2Lexer', 'Python2TracebackLexer',
           'CythonLexer', 'DgLexer', 'NumPyLexer']


class PythonLexer(RegexLexer):
    """
    For Python source code (version 3.x).

    .. versionchanged:: 2.5
       This is now the default ``PythonLexer``.  It is still available as the
       alias ``Python3Lexer``.
    """

    name = 'Python'
    url = 'https://www.python.org'
    aliases = ['python', 'py', 'sage', 'python3', 'py3', 'bazel', 'starlark', 'pyi']
    filenames = [
        '*.py',
        '*.pyw',
        # Type stubs
        '*.pyi',
        # Jython
        '*.jy',
        # Sage
        '*.sage',
        # SCons
        '*.sc',
        'SConstruct',
        'SConscript',
        # Skylark/Starlark (used by Bazel, Buck, and Pants)
        '*.bzl',
        'BUCK',
        'BUILD',
        'BUILD.bazel',
        'WORKSPACE',
        # Twisted Application infrastructure
        '*.tac',
    ]
    mimetypes = ['text/x-python', 'application/x-python',
                 'text/x-python3', 'application/x-python3']
    version_added = '0.10'

    uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting (still valid in Py3)
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsaux%]', String.Interpol),
            # the new style '{}'.format(...) string formatting
            (r'\{'
             r'((\w+)((\.\w+)|(\[[^\]]+\]))*)?'  # field name
             r'(\![sra])?'                       # conversion
             r'(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?'
             r'\}', String.Interpol),

            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%|(\{{1,2})', ttype)
            # newlines are an error (use "nl" state)
        ]

    def fstring_rules(ttype):
        return [
            # Assuming that a '}' is the closing brace after format specifier.
            # Sadly, this means that we won't detect syntax error. But it's
            # more important to parse correct syntax correctly, than to
            # highlight invalid syntax.
            (r'\}', String.Interpol),
            (r'\{', String.Interpol, 'expr-inside-fstring'),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'\\\n', Text),
            (r'\\', Text),
            include('keywords'),
            include('soft-keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Whitespace), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Whitespace),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Whitespace),
             'import'),
            include('expr'),
        ],
        'expr': [
            # raw f-strings
            ('(?i)(rf|fr)(""")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'tdqf')),
            ("(?i)(rf|fr)(''')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'tsqf')),
            ('(?i)(rf|fr)(")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'dqf')),
            ("(?i)(rf|fr)(')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'sqf')),
            # non-raw f-strings
            ('([fF])(""")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'tdqf')),
            ("([fF])(''')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'tsqf')),
            ('([fF])(")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'dqf')),
            ("([fF])(')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'sqf')),
            # raw bytes and strings
            ('(?i)(rb|br|r)(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("(?i)(rb|br|r)(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('(?i)(rb|br|r)(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("(?i)(rb|br|r)(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            # non-raw strings
            ('([uU]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uU]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uU]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uU]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            # non-raw bytes
            ('([bB])(""")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'tdqs')),
            ("([bB])(''')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'tsqs')),
            ('([bB])(")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'dqs')),
            ("([bB])(')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'sqs')),

            (r'[^\S\n]+', Text),
            include('numbers'),
            (r'!=|==|<<|>>|:=|[-~+/*%=<>&^|.]', Operator),
            (r'[]{}:(),;[]', Punctuation),
            (r'(in|is|and|or|not)\b', Operator.Word),
            include('expr-keywords'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('name'),
        ],
        'expr-inside-fstring': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            # without format specifier
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r'\}', String.Interpol, '#pop'),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r':', String.Interpol, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-inside-fstring-inner': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            (r'[])}]', Punctuation, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-keywords': [
            # Based on https://docs.python.org/3/reference/expressions.html
            (words((
                'async for', 'await', 'else', 'for', 'if', 'lambda',
                'yield', 'yield from'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'continue', 'del', 'elif',
                'else', 'except', 'finally', 'for', 'global', 'if', 'lambda',
                'pass', 'raise', 'nonlocal', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'soft-keywords': [
            # `match`, `case` and `_` soft keywords
            (r'(^[ \t]*)'              # at beginning of line + possible indentation
             r'(match|case)\b'         # a possible keyword
             r'(?![ \t]*(?:'           # not followed by...
             r'[:,;=^&|@~)\]}]|(?:' +  # characters and keywords that mean this isn't
                                       # pattern matching (but None/True/False is ok)
             r'|'.join(k for k in keyword.kwlist if k[0].islower()) + r')\b))',
             bygroups(Text, Keyword), 'soft-keywords-inner'),
        ],
        'soft-keywords-inner': [
            # optional `_` keyword
            (r'(\s+)([^\n_]*)(_\b)', bygroups(Whitespace, using(this), Keyword)),
            default('#pop')
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'aiter', 'all', 'any', 'bin', 'bool', 'bytearray',
                'breakpoint', 'bytes', 'callable', 'chr', 'classmethod', 'compile',
                'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
                'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
                'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
                'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
                'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
                'tuple', 'type', 'vars', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|Ellipsis|NotImplemented|cls)\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'BufferError', 'BytesWarning', 'DeprecationWarning',
                'EOFError', 'EnvironmentError', 'Exception', 'FloatingPointError',
                'FutureWarning', 'GeneratorExit', 'IOError', 'ImportError',
                'ImportWarning', 'IndentationError', 'IndexError', 'KeyError',
                'KeyboardInterrupt', 'LookupError', 'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError',
                'PendingDeprecationWarning', 'ReferenceError', 'ResourceWarning',
                'RuntimeError', 'RuntimeWarning', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError',
                'Warning', 'WindowsError', 'ZeroDivisionError',
                # new builtin exceptions from PEP 3151
                'BlockingIOError', 'ChildProcessError', 'ConnectionError',
                'BrokenPipeError', 'ConnectionAbortedError', 'ConnectionRefusedError',
                'ConnectionResetError', 'FileExistsError', 'FileNotFoundError',
                'InterruptedError', 'IsADirectoryError', 'NotADirectoryError',
                'PermissionError', 'ProcessLookupError', 'TimeoutError',
                # others new in Python 3
                'StopAsyncIteration', 'ModuleNotFoundError', 'RecursionError',
                'EncodingWarning'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__aenter__', '__aexit__', '__aiter__',
                '__and__', '__anext__', '__await__', '__bool__', '__bytes__',
                '__call__', '__complex__', '__contains__', '__del__', '__delattr__',
                '__delete__', '__delitem__', '__dir__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__format__',
                '__ge__', '__get__', '__getattr__', '__getattribute__',
                '__getitem__', '__gt__', '__hash__', '__iadd__', '__iand__',
                '__ifloordiv__', '__ilshift__', '__imatmul__', '__imod__',
                '__imul__', '__index__', '__init__', '__instancecheck__',
                '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
                '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__',
                '__len__', '__length_hint__', '__lshift__', '__lt__', '__matmul__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__',
                '__new__', '__next__', '__or__', '__pos__', '__pow__',
                '__prepare__', '__radd__', '__rand__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmatmul__',
                '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__',
                '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
                '__rxor__', '__set__', '__setattr__', '__setitem__', '__str__',
                '__sub__', '__subclasscheck__', '__truediv__',
                '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__annotations__', '__bases__', '__class__', '__closure__',
                '__code__', '__defaults__', '__dict__', '__doc__', '__file__',
                '__func__', '__globals__', '__kwdefaults__', '__module__',
                '__mro__', '__name__', '__objclass__', '__qualname__',
                '__self__', '__slots__', '__weakref__'), suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', Number.Float),
            (r'\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?', Number.Float),
            (r'0[oO](?:_?[0-7])+', Number.Oct),
            (r'0[bB](?:_?[01])+', Number.Bin),
            (r'0[xX](?:_?[a-fA-F0-9])+', Number.Hex),
            (r'\d(?:_?\d)*', Number.Integer),
        ],
        'name': [
            (r'@' + uni_name, Name.Decorator),
            (r'@', Operator),  # new matrix multiplication operator
            (uni_name, Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (uni_name, Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (uni_name, Name.Class, '#pop'),
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Whitespace, Keyword, Whitespace)),
            (r'\.', Name.Namespace),
            (uni_name, Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Whitespace, Operator, Whitespace)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(import)\b', bygroups(Whitespace, Keyword.Namespace), '#pop'),
            (r'\.', Name.Namespace),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Keyword.Constant, '#pop'),
            (uni_name, Name.Namespace),
            default('#pop'),
        ],
        'rfstringescape': [
            (r'\{\{', String.Escape),
            (r'\}\}', String.Escape),
        ],
        'fstringescape': [
            include('rfstringescape'),
            include('stringescape'),
        ],
        'bytesescape': [
            (r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'stringescape': [
            (r'\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})', String.Escape),
            include('bytesescape')
        ],
        'fstrings-single': fstring_rules(String.Single),
        'fstrings-double': fstring_rules(String.Double),
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqf': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('fstrings-double')
        ],
        'sqf': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('fstrings-single')
        ],
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqf': [
            (r'"""', String.Double, '#pop'),
            include('fstrings-double'),
            (r'\n', String.Double)
        ],
        'tsqf': [
            (r"'''", String.Single, '#pop'),
            include('fstrings-single'),
            (r'\n', String.Single)
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?(3(\.\d)?)?') or \
            'import ' in text[:1000]


Python3Lexer = PythonLexer


class Python2Lexer(RegexLexer):
    """
    For Python 2.x source code.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonLexer``.  ``PythonLexer`` now
       refers to the Python 3 variant.  File name patterns like ``*.py`` have
       been moved to Python 3 as well.
    """

    name = 'Python 2.x'
    url = 'https://www.python.org'
    aliases = ['python2', 'py2']
    filenames = []  # now taken over by PythonLexer (3.x)
    mimetypes = ['text/x-python2', 'application/x-python2']
    version_added = ''

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Text),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.]', Operator),
            include('keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Whitespace), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Whitespace),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Whitespace),
             'import'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('backtick'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            ('([uUbB]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uUbB]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uUbB]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uUbB]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'break', 'continue', 'del', 'elif', 'else', 'except',
                'exec', 'finally', 'for', 'global', 'if', 'lambda', 'pass',
                'print', 'raise', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
                'cmp', 'coerce', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
                'enumerate', 'eval', 'execfile', 'exit', 'file', 'filter', 'float',
                'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'hex', 'id',
                'input', 'int', 'intern', 'isinstance', 'issubclass', 'iter', 'len',
                'list', 'locals', 'long', 'map', 'max', 'min', 'next', 'object',
                'oct', 'open', 'ord', 'pow', 'property', 'range', 'raw_input', 'reduce',
                'reload', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
                'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type',
                'unichr', 'unicode', 'vars', 'xrange', 'zip'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|cls'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError',
                'RuntimeError', 'RuntimeWarning', 'StandardError', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError', 'Warning',
                'WindowsError', 'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
                '__complex__', '__contains__', '__del__', '__delattr__', '__delete__',
                '__delitem__', '__delslice__', '__div__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__ge__', '__get__',
                '__getattr__', '__getattribute__', '__getitem__', '__getslice__', '__gt__',
                '__hash__', '__hex__', '__iadd__', '__iand__', '__idiv__', '__ifloordiv__',
                '__ilshift__', '__imod__', '__imul__', '__index__', '__init__',
                '__instancecheck__', '__int__', '__invert__', '__iop__', '__ior__',
                '__ipow__', '__irshift__', '__isub__', '__iter__', '__itruediv__',
                '__ixor__', '__le__', '__len__', '__long__', '__lshift__', '__lt__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__',
                '__nonzero__', '__oct__', '__op__', '__or__', '__pos__', '__pow__',
                '__radd__', '__rand__', '__rcmp__', '__rdiv__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__',
                '__rop__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
                '__rtruediv__', '__rxor__', '__set__', '__setattr__', '__setitem__',
                '__setslice__', '__str__', '__sub__', '__subclasscheck__', '__truediv__',
                '__unicode__', '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__bases__', '__class__', '__closure__', '__code__', '__defaults__',
                '__dict__', '__doc__', '__file__', '__func__', '__globals__',
                '__metaclass__', '__module__', '__mro__', '__name__', '__self__',
                '__slots__', '__weakref__'),
                suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[bB][01]+', Number.Bin),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@[\w.]+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (r'[a-zA-Z_]\w*', Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'as\b', Keyword.Namespace),
            (r',', Operator),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'import\b', Keyword.Namespace, '#pop'),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Name.Builtin.Pseudo, '#pop'),
            # sadly, in "raise x from y" y will be highlighted as namespace too
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # anything else here also means "raise x from y" and is therefore
            # not an error
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?2(\.\d)?')


class _PythonConsoleLexerBase(RegexLexer):
    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']

    """Auxiliary lexer for `PythonConsoleLexer`.

    Code tokens are output as ``Token.Other.Code``, traceback tokens as
    ``Token.Other.Traceback``.
    """
    tokens = {
        'root': [
            (r'(>>> )(.*\n)', bygroups(Generic.Prompt, Other.Code), 'continuations'),
            # This happens, e.g., when tracebacks are embedded in documentation;
            # trailing whitespaces are often stripped in such contexts.
            (r'(>>>)(\n)', bygroups(Generic.Prompt, Whitespace)),
            (r'(\^C)?Traceback \(most recent call last\):\n', Other.Traceback, 'traceback'),
            # SyntaxError starts with this
            (r'  File "[^"]+", line \d+', Other.Traceback, 'traceback'),
            (r'.*\n', Generic.Output),
        ],
        'continuations': [
            (r'(\.\.\. )(.*\n)', bygroups(Generic.Prompt, Other.Code)),
            # See above.
            (r'(\.\.\.)(\n)', bygroups(Generic.Prompt, Whitespace)),
            default('#pop'),
        ],
        'traceback': [
            # As soon as we see a traceback, consume everything until the next
            # >>> prompt.
            (r'(?=>>>( |$))', Text, '#pop'),
            (r'(KeyboardInterrupt)(\n)', bygroups(Name.Class, Whitespace)),
            (r'.*\n', Other.Traceback),
        ],
    }


class PythonConsoleLexer(DelegatingLexer):
    """
    For Python console output or doctests, such as:

    .. sourcecode:: pycon

        >>> a = 'foo'
        >>> print(a)
        foo
        >>> 1 / 0
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        ZeroDivisionError: integer division or modulo by zero

    Additional options:

    `python3`
        Use Python 3 lexer for code.  Default is ``True``.

        .. versionadded:: 1.0
        .. versionchanged:: 2.5
           Now defaults to ``True``.
    """

    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']
    url = 'https://python.org'
    version_added = ''

    def __init__(self, **options):
        python3 = get_bool_opt(options, 'python3', True)
        if python3:
            pylexer = PythonLexer
            tblexer = PythonTracebackLexer
        else:
            pylexer = Python2Lexer
            tblexer = Python2TracebackLexer
        # We have two auxiliary lexers. Use DelegatingLexer twice with
        # different tokens.  TODO: DelegatingLexer should support this
        # directly, by accepting a tuplet of auxiliary lexers and a tuple of
        # distinguishing tokens. Then we wouldn't need this intermediary
        # class.
        class _ReplaceInnerCode(DelegatingLexer):
            def __init__(self, **options):
                super().__init__(pylexer, _PythonConsoleLexerBase, Other.Code, **options)
        super().__init__(tblexer, _ReplaceInnerCode, Other.Traceback, **options)


class PythonTracebackLexer(RegexLexer):
    """
    For Python 3.x tracebacks, with support for chained exceptions.

    .. versionchanged:: 2.5
       This is now the default ``PythonTracebackLexer``.  It is still available
       as the alias ``Python3TracebackLexer``.
    """

    name = 'Python Traceback'
    aliases = ['pytb', 'py3tb']
    filenames = ['*.pytb', '*.py3tb']
    mimetypes = ['text/x-python-traceback', 'text/x-python3-traceback']
    url = 'https://python.org'
    version_added = '1.0'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\^C)?Traceback \(most recent call last\):\n', Generic.Traceback, 'intb'),
            (r'^During handling of the above exception, another '
             r'exception occurred:\n\n', Generic.Traceback),
            (r'^The above exception was the direct cause of the '
             r'following exception:\n\n', Generic.Traceback),
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Whitespace, using(PythonLexer), Whitespace), 'markers'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Whitespace, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_][\w.]*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop'),
            default('#pop'),
        ],
        'markers': [
            # Either `PEP 657 <https://www.python.org/dev/peps/pep-0657/>`
            # error locations in Python 3.11+, or single-caret markers
            # for syntax errors before that.
            (r'^( {4,})([~^]+)(\n)',
             bygroups(Whitespace, Punctuation.Marker, Whitespace),
             '#pop'),
            default('#pop'),
        ],
    }


Python3TracebackLexer = PythonTracebackLexer


class Python2TracebackLexer(RegexLexer):
    """
    For Python tracebacks.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonTracebackLexer``.
       ``PythonTracebackLexer`` now refers to the Python 3 variant.
    """

    name = 'Python 2.x Traceback'
    aliases = ['py2tb']
    filenames = ['*.py2tb']
    mimetypes = ['text/x-python2-traceback']
    url = 'https://python.org'
    version_added = '0.7'

    tokens = {
        'root': [
            # Cover both (most recent call last) and (innermost last)
            # The optional ^C allows us to catch keyboard interrupt signals.
            (r'^(\^C)?(Traceback.*\n)',
             bygroups(Text, Generic.Traceback), 'intb'),
            # SyntaxError starts with this.
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Text, using(Python2Lexer), Whitespace), 'marker'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Text, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_]\w*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop')
        ],
        'marker': [
            # For syntax errors.
            (r'( {4,})(\^)', bygroups(Text, Punctuation.Marker), '#pop'),
            default('#pop'),
        ],
    }


class CythonLexer(RegexLexer):
    """
    For Pyrex and Cython source code.
    """

    name = 'Cython'
    url = 'https://cython.org'
    aliases = ['cython', 'pyx', 'pyrex']
    filenames = ['*.pyx', '*.pxd', '*.pxi']
    mimetypes = ['text/x-cython', 'application/x-cython']
    version_added = '1.1'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)("""(?:.|\n)*?""")', bygroups(Whitespace, String.Doc)),
            (r"^(\s*)('''(?:.|\n)*?''')", bygroups(Whitespace, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'#.*$', Comment),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Whitespace),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'(<)([a-zA-Z0-9.?]+)(>)',
             bygroups(Punctuation, Keyword.Type, Punctuation)),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.?]', Operator),
            (r'(from)(\d+)(<=)(\s+)(<)(\d+)(:)',
             bygroups(Keyword, Number.Integer, Operator, Whitespace, Operator,
                      Name, Punctuation)),
            include('keywords'),
            (r'(def|property)(\s+)', bygroups(Keyword, Whitespace), 'funcname'),
            (r'(cp?def)(\s+)', bygroups(Keyword, Whitespace), 'cdef'),
            # (should actually start a block with only cdefs)
            (r'(cdef)(:)', bygroups(Keyword, Punctuation)),
            (r'(class|struct)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'(from)(\s+)', bygroups(Keyword, Whitespace), 'fromimport'),
            (r'(c?import)(\s+)', bygroups(Keyword, Whitespace), 'import'),
            include('builtins'),
            include('backtick'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"""', String, 'tdqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'''", String, 'tsqs'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"', String, 'dqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'", String, 'sqs'),
            ('[uU]?"""', String, combined('stringescape', 'tdqs')),
            ("[uU]?'''", String, combined('stringescape', 'tsqs')),
            ('[uU]?"', String, combined('stringescape', 'dqs')),
            ("[uU]?'", String, combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'by', 'continue', 'ctypedef', 'del', 'elif',
                'else', 'except', 'except?', 'exec', 'finally', 'for', 'fused', 'gil',
                'global', 'if', 'include', 'lambda', 'nogil', 'pass', 'print',
                'raise', 'return', 'try', 'while', 'yield', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (r'(DEF|IF|ELIF|ELSE)\b', Comment.Preproc),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin', 'bint',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr',
                'classmethod', 'cmp', 'coerce', 'compile', 'complex', 'delattr',
                'dict', 'dir', 'divmod', 'enumerate', 'eval', 'execfile', 'exit',
                'file', 'filter', 'float', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'intern', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'long', 'map', 'max',
                'min', 'next', 'object', 'oct', 'open', 'ord', 'pow', 'property', 'Py_ssize_t',
                'range', 'raw_input', 'reduce', 'reload', 'repr', 'reversed',
                'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod',
                'str', 'sum', 'super', 'tuple', 'type', 'unichr', 'unicode', 'unsigned',
                'vars', 'xrange', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|NULL'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError', 'NotImplemented', 'NotImplementedError',
                'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError', 'RuntimeError',
                'RuntimeWarning', 'StandardError', 'StopIteration', 'SyntaxError',
                'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError',
                'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'Warning',
                'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'numbers': [
            (r'(\d+\.?\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'0\d+', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@\w+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            (r'[a-zA-Z_]\w*', Name.Function, '#pop')
        ],
        'cdef': [
            (r'(public|readonly|extern|api|inline)\b', Keyword.Reserved),
            (r'(struct|enum|union|class)\b', Keyword),
            (r'([a-zA-Z_]\w*)(\s*)(?=[(:#=]|$)',
             bygroups(Name.Function, Whitespace), '#pop'),
            (r'([a-zA-Z_]\w*)(\s*)(,)',
             bygroups(Name.Function, Whitespace, Punctuation)),
            (r'from\b', Keyword, '#pop'),
            (r'as\b', Keyword),
            (r':', Punctuation, '#pop'),
            (r'(?=["\'])', Text, '#pop'),
            (r'[a-zA-Z_]\w*', Keyword.Type),
            (r'.', Text),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Whitespace, Keyword, Whitespace)),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Whitespace, Operator, Whitespace)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(c?import)\b', bygroups(Whitespace, Keyword), '#pop'),
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # ``cdef foo from "header"``, or ``for foo from 0 < i < 10``
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'%(\([a-zA-Z0-9]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String)
            # newlines are an error (use "nl" state)
        ],
        'nl': [
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
            include('nl')
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            include('strings'),
            include('nl')
        ],
    }


class DgLexer(RegexLexer):
    """
    Lexer for dg,
    a functional and object-oriented programming language
    running on the CPython 3 VM.
    """
    name = 'dg'
    aliases = ['dg']
    filenames = ['*.dg']
    mimetypes = ['text/x-dg']
    url = 'http://pyos.github.io/dg'
    version_added = '1.6'

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#.*?$', Comment.Single),

            (r'(?i)0b[01]+', Number.Bin),
            (r'(?i)0o[0-7]+', Number.Oct),
            (r'(?i)0x[0-9a-f]+', Number.Hex),
            (r'(?i)[+-]?[0-9]+\.[0-9]+(e[+-]?[0-9]+)?j?', Number.Float),
            (r'(?i)[+-]?[0-9]+e[+-]?\d+j?', Number.Float),
            (r'(?i)[+-]?[0-9]+j?', Number.Integer),

            (r"(?i)(br|r?b?)'''", String, combined('stringescape', 'tsqs', 'string')),
            (r'(?i)(br|r?b?)"""', String, combined('stringescape', 'tdqs', 'string')),
            (r"(?i)(br|r?b?)'", String, combined('stringescape', 'sqs', 'string')),
            (r'(?i)(br|r?b?)"', String, combined('stringescape', 'dqs', 'string')),

            (r"`\w+'*`", Operator),
            (r'\b(and|in|is|or|where)\b', Operator.Word),
            (r'[!$%&*+\-./:<-@\\^|~;,]+', Operator),

            (words((
                'bool', 'bytearray', 'bytes', 'classmethod', 'complex', 'dict', 'dict\'',
                'float', 'frozenset', 'int', 'list', 'list\'', 'memoryview', 'object',
                'property', 'range', 'set', 'set\'', 'slice', 'staticmethod', 'str',
                'super', 'tuple', 'tuple\'', 'type'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (words((
                '__import__', 'abs', 'all', 'any', 'bin', 'bind', 'chr', 'cmp', 'compile',
                'complex', 'delattr', 'dir', 'divmod', 'drop', 'dropwhile', 'enumerate',
                'eval', 'exhaust', 'filter', 'flip', 'foldl1?', 'format', 'fst',
                'getattr', 'globals', 'hasattr', 'hash', 'head', 'hex', 'id', 'init',
                'input', 'isinstance', 'issubclass', 'iter', 'iterate', 'last', 'len',
                'locals', 'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow',
                'print', 'repr', 'reversed', 'round', 'setattr', 'scanl1?', 'snd',
                'sorted', 'sum', 'tail', 'take', 'takewhile', 'vars', 'zip'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (r"(?<!\.)(self|Ellipsis|NotImplemented|None|True|False)(?!['\w])",
             Name.Builtin.Pseudo),

            (r"(?<!\.)[A-Z]\w*(Error|Exception|Warning)'*(?!['\w])",
             Name.Exception),
            (r"(?<!\.)(Exception|GeneratorExit|KeyboardInterrupt|StopIteration|"
             r"SystemExit)(?!['\w])", Name.Exception),

            (r"(?<![\w.])(except|finally|for|if|import|not|otherwise|raise|"
             r"subclass|while|with|yield)(?!['\w])", Keyword.Reserved),

            (r"[A-Z_]+'*(?!['\w])", Name),
            (r"[A-Z]\w+'*(?!['\w])", Keyword.Type),
            (r"\w+'*", Name),

            (r'[()]', Punctuation),
            (r'.', Error),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'string': [
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String),
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop')
        ],
        'sqs': [
            (r"'", String, '#pop')
        ],
        'tdqs': [
            (r'"""', String, '#pop')
        ],
        'tsqs': [
            (r"'''", String, '#pop')
        ],
    }


class NumPyLexer(PythonLexer):
    """
    A Python lexer recognizing Numerical Python builtins.
    """

    name = 'NumPy'
    url = 'https://numpy.org/'
    aliases = ['numpy']
    version_added = '0.10'

    # override the mimetypes to not inherit them from python
    mimetypes = []
    filenames = []

    EXTRA_KEYWORDS = {
        'abs', 'absolute', 'accumulate', 'add', 'alen', 'all', 'allclose',
        'alltrue', 'alterdot', 'amax', 'amin', 'angle', 'any', 'append',
        'apply_along_axis', 'apply_over_axes', 'arange', 'arccos', 'arccosh',
        'arcsin', 'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax', 'argmin',
        'argsort', 'argwhere', 'around', 'array', 'array2string', 'array_equal',
        'array_equiv', 'array_repr', 'array_split', 'array_str', 'arrayrange',
        'asanyarray', 'asarray', 'asarray_chkfinite', 'ascontiguousarray',
        'asfarray', 'asfortranarray', 'asmatrix', 'asscalar', 'astype',
        'atleast_1d', 'atleast_2d', 'atleast_3d', 'average', 'bartlett',
        'base_repr', 'beta', 'binary_repr', 'bincount', 'binomial',
        'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor', 'blackman',
        'bmat', 'broadcast', 'byte_bounds', 'bytes', 'byteswap', 'c_',
        'can_cast', 'ceil', 'choose', 'clip', 'column_stack', 'common_type',
        'compare_chararrays', 'compress', 'concatenate', 'conj', 'conjugate',
        'convolve', 'copy', 'corrcoef', 'correlate', 'cos', 'cosh', 'cov',
        'cross', 'cumprod', 'cumproduct', 'cumsum', 'delete', 'deprecate',
        'diag', 'diagflat', 'diagonal', 'diff', 'digitize', 'disp', 'divide',
        'dot', 'dsplit', 'dstack', 'dtype', 'dump', 'dumps', 'ediff1d', 'empty',
        'empty_like', 'equal', 'exp', 'expand_dims', 'expm1', 'extract', 'eye',
        'fabs', 'fastCopyAndTranspose', 'fft', 'fftfreq', 'fftshift', 'fill',
        'finfo', 'fix', 'flat', 'flatnonzero', 'flatten', 'fliplr', 'flipud',
        'floor', 'floor_divide', 'fmod', 'frexp', 'fromarrays', 'frombuffer',
        'fromfile', 'fromfunction', 'fromiter', 'frompyfunc', 'fromstring',
        'generic', 'get_array_wrap', 'get_include', 'get_numarray_include',
        'get_numpy_include', 'get_printoptions', 'getbuffer', 'getbufsize',
        'geterr', 'geterrcall', 'geterrobj', 'getfield', 'gradient', 'greater',
        'greater_equal', 'gumbel', 'hamming', 'hanning', 'histogram',
        'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot', 'i0',
        'identity', 'ifft', 'imag', 'index_exp', 'indices', 'inf', 'info',
        'inner', 'insert', 'int_asbuffer', 'interp', 'intersect1d',
        'intersect1d_nu', 'inv', 'invert', 'iscomplex', 'iscomplexobj',
        'isfinite', 'isfortran', 'isinf', 'isnan', 'isneginf', 'isposinf',
        'isreal', 'isrealobj', 'isscalar', 'issctype', 'issubclass_',
        'issubdtype', 'issubsctype', 'item', 'itemset', 'iterable', 'ix_',
        'kaiser', 'kron', 'ldexp', 'left_shift', 'less', 'less_equal', 'lexsort',
        'linspace', 'load', 'loads', 'loadtxt', 'log', 'log10', 'log1p', 'log2',
        'logical_and', 'logical_not', 'logical_or', 'logical_xor', 'logspace',
        'lstsq', 'mat', 'matrix', 'max', 'maximum', 'maximum_sctype',
        'may_share_memory', 'mean', 'median', 'meshgrid', 'mgrid', 'min',
        'minimum', 'mintypecode', 'mod', 'modf', 'msort', 'multiply', 'nan',
        'nan_to_num', 'nanargmax', 'nanargmin', 'nanmax', 'nanmin', 'nansum',
        'ndenumerate', 'ndim', 'ndindex', 'negative', 'newaxis', 'newbuffer',
        'newbyteorder', 'nonzero', 'not_equal', 'obj2sctype', 'ogrid', 'ones',
        'ones_like', 'outer', 'permutation', 'piecewise', 'pinv', 'pkgload',
        'place', 'poisson', 'poly', 'poly1d', 'polyadd', 'polyder', 'polydiv',
        'polyfit', 'polyint', 'polymul', 'polysub', 'polyval', 'power', 'prod',
        'product', 'ptp', 'put', 'putmask', 'r_', 'randint', 'random_integers',
        'random_sample', 'ranf', 'rank', 'ravel', 'real', 'real_if_close',
        'recarray', 'reciprocal', 'reduce', 'remainder', 'repeat', 'require',
        'reshape', 'resize', 'restoredot', 'right_shift', 'rint', 'roll',
        'rollaxis', 'roots', 'rot90', 'round', 'round_', 'row_stack', 's_',
        'sample', 'savetxt', 'sctype2char', 'searchsorted', 'seed', 'select',
        'set_numeric_ops', 'set_printoptions', 'set_string_function',
        'setbufsize', 'setdiff1d', 'seterr', 'seterrcall', 'seterrobj',
        'setfield', 'setflags', 'setmember1d', 'setxor1d', 'shape',
        'show_config', 'shuffle', 'sign', 'signbit', 'sin', 'sinc', 'sinh',
        'size', 'slice', 'solve', 'sometrue', 'sort', 'sort_complex', 'source',
        'split', 'sqrt', 'square', 'squeeze', 'standard_normal', 'std',
        'subtract', 'sum', 'svd', 'swapaxes', 'take', 'tan', 'tanh', 'tensordot',
        'test', 'tile', 'tofile', 'tolist', 'tostring', 'trace', 'transpose',
        'trapz', 'tri', 'tril', 'trim_zeros', 'triu', 'true_divide', 'typeDict',
        'typename', 'uniform', 'union1d', 'unique', 'unique1d', 'unravel_index',
        'unwrap', 'vander', 'var', 'vdot', 'vectorize', 'view', 'vonmises',
        'vsplit', 'vstack', 'weibull', 'where', 'who', 'zeros', 'zeros_like'
    }

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                PythonLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.EXTRA_KEYWORDS:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value

    def analyse_text(text):
        ltext = text[:1000]
        return (shebang_matches(text, r'pythonw?(3(\.\d)?)?') or
                'import ' in ltext) \
            and ('import numpy' in ltext or 'from numpy import' in ltext)