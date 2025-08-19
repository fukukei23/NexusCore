
# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\client.py ===
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
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.retriever_service import pagers
from google.ai.generativelanguage_v1beta.types import retriever, retriever_service

from .transports.base import DEFAULT_CLIENT_INFO, RetrieverServiceTransport
from .transports.grpc import RetrieverServiceGrpcTransport
from .transports.grpc_asyncio import RetrieverServiceGrpcAsyncIOTransport
from .transports.rest import RetrieverServiceRestTransport


class RetrieverServiceClientMeta(type):
    """Metaclass for the RetrieverService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[RetrieverServiceTransport]]
    _transport_registry["grpc"] = RetrieverServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = RetrieverServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = RetrieverServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[RetrieverServiceTransport]:
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


class RetrieverServiceClient(metaclass=RetrieverServiceClientMeta):
    """An API for semantic search over a corpus of user uploaded
    content.
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
            RetrieverServiceClient: The constructed client.
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
            RetrieverServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> RetrieverServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            RetrieverServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def chunk_path(
        corpus: str,
        document: str,
        chunk: str,
    ) -> str:
        """Returns a fully-qualified chunk string."""
        return "corpora/{corpus}/documents/{document}/chunks/{chunk}".format(
            corpus=corpus,
            document=document,
            chunk=chunk,
        )

    @staticmethod
    def parse_chunk_path(path: str) -> Dict[str, str]:
        """Parses a chunk path into its component segments."""
        m = re.match(
            r"^corpora/(?P<corpus>.+?)/documents/(?P<document>.+?)/chunks/(?P<chunk>.+?)$",
            path,
        )
        return m.groupdict() if m else {}

    @staticmethod
    def corpus_path(
        corpus: str,
    ) -> str:
        """Returns a fully-qualified corpus string."""
        return "corpora/{corpus}".format(
            corpus=corpus,
        )

    @staticmethod
    def parse_corpus_path(path: str) -> Dict[str, str]:
        """Parses a corpus path into its component segments."""
        m = re.match(r"^corpora/(?P<corpus>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def document_path(
        corpus: str,
        document: str,
    ) -> str:
        """Returns a fully-qualified document string."""
        return "corpora/{corpus}/documents/{document}".format(
            corpus=corpus,
            document=document,
        )

    @staticmethod
    def parse_document_path(path: str) -> Dict[str, str]:
        """Parses a document path into its component segments."""
        m = re.match(r"^corpora/(?P<corpus>.+?)/documents/(?P<document>.+?)$", path)
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
            _default_universe = RetrieverServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = RetrieverServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = RetrieverServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = RetrieverServiceClient._DEFAULT_UNIVERSE
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

        default_universe = RetrieverServiceClient._DEFAULT_UNIVERSE
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
            or RetrieverServiceClient._compare_universes(
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
            Union[
                str, RetrieverServiceTransport, Callable[..., RetrieverServiceTransport]
            ]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the retriever service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,RetrieverServiceTransport,Callable[..., RetrieverServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the RetrieverServiceTransport constructor.
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
        ) = RetrieverServiceClient._read_environment_variables()
        self._client_cert_source = RetrieverServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = RetrieverServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, RetrieverServiceTransport)
        if transport_provided:
            # transport is a RetrieverServiceTransport instance.
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
            self._transport = cast(RetrieverServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or RetrieverServiceClient._get_api_endpoint(
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
                Type[RetrieverServiceTransport],
                Callable[..., RetrieverServiceTransport],
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., RetrieverServiceTransport], transport)
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

    def create_corpus(
        self,
        request: Optional[Union[retriever_service.CreateCorpusRequest, dict]] = None,
        *,
        corpus: Optional[retriever.Corpus] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Creates an empty ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateCorpusRequest(
                )

                # Make the request
                response = client.create_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateCorpusRequest, dict]):
                The request object. Request to create a ``Corpus``.
            corpus (google.ai.generativelanguage_v1beta.types.Corpus):
                Required. The ``Corpus`` to create.
                This corresponds to the ``corpus`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([corpus])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateCorpusRequest):
            request = retriever_service.CreateCorpusRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if corpus is not None:
                request.corpus = corpus

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_corpus]

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

    def get_corpus(
        self,
        request: Optional[Union[retriever_service.GetCorpusRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Gets information about a specific ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetCorpusRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetCorpusRequest, dict]):
                The request object. Request for getting information about a specific
                ``Corpus``.
            name (str):
                Required. The name of the ``Corpus``. Example:
                ``corpora/my-corpus-123``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

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
        if not isinstance(request, retriever_service.GetCorpusRequest):
            request = retriever_service.GetCorpusRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_corpus]

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

    def update_corpus(
        self,
        request: Optional[Union[retriever_service.UpdateCorpusRequest, dict]] = None,
        *,
        corpus: Optional[retriever.Corpus] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Updates a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateCorpusRequest(
                )

                # Make the request
                response = client.update_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdateCorpusRequest, dict]):
                The request object. Request to update a ``Corpus``.
            corpus (google.ai.generativelanguage_v1beta.types.Corpus):
                Required. The ``Corpus`` to update.
                This corresponds to the ``corpus`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to update. Currently, this
                only supports updating ``display_name``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([corpus, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateCorpusRequest):
            request = retriever_service.UpdateCorpusRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if corpus is not None:
                request.corpus = corpus
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_corpus]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("corpus.name", request.corpus.name),)
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

    def delete_corpus(
        self,
        request: Optional[Union[retriever_service.DeleteCorpusRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteCorpusRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_corpus(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteCorpusRequest, dict]):
                The request object. Request to delete a ``Corpus``.
            name (str):
                Required. The resource name of the ``Corpus``. Example:
                ``corpora/my-corpus-123``

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
        if not isinstance(request, retriever_service.DeleteCorpusRequest):
            request = retriever_service.DeleteCorpusRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_corpus]

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

    def list_corpora(
        self,
        request: Optional[Union[retriever_service.ListCorporaRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListCorporaPager:
        r"""Lists all ``Corpora`` owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_corpora():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListCorporaRequest(
                )

                # Make the request
                page_result = client.list_corpora(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListCorporaRequest, dict]):
                The request object. Request for listing ``Corpora``.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListCorporaPager:
                Response from ListCorpora containing a paginated list of Corpora.
                   The results are sorted by ascending
                   corpus.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListCorporaRequest):
            request = retriever_service.ListCorporaRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_corpora]

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
        response = pagers.ListCorporaPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def query_corpus(
        self,
        request: Optional[Union[retriever_service.QueryCorpusRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.QueryCorpusResponse:
        r"""Performs semantic search over a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_query_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.QueryCorpusRequest(
                    name="name_value",
                    query="query_value",
                )

                # Make the request
                response = client.query_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.QueryCorpusRequest, dict]):
                The request object. Request for querying a ``Corpus``.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.QueryCorpusResponse:
                Response from QueryCorpus containing a list of relevant
                chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.QueryCorpusRequest):
            request = retriever_service.QueryCorpusRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.query_corpus]

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

    def create_document(
        self,
        request: Optional[Union[retriever_service.CreateDocumentRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        document: Optional[retriever.Document] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Creates an empty ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateDocumentRequest(
                    parent="parent_value",
                )

                # Make the request
                response = client.create_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateDocumentRequest, dict]):
                The request object. Request to create a ``Document``.
            parent (str):
                Required. The name of the ``Corpus`` where this
                ``Document`` will be created. Example:
                ``corpora/my-corpus-123``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            document (google.ai.generativelanguage_v1beta.types.Document):
                Required. The ``Document`` to create.
                This corresponds to the ``document`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, document])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateDocumentRequest):
            request = retriever_service.CreateDocumentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent
            if document is not None:
                request.document = document

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_document]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

    def get_document(
        self,
        request: Optional[Union[retriever_service.GetDocumentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Gets information about a specific ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetDocumentRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetDocumentRequest, dict]):
                The request object. Request for getting information about a specific
                ``Document``.
            name (str):
                Required. The name of the ``Document`` to retrieve.
                Example: ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

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
        if not isinstance(request, retriever_service.GetDocumentRequest):
            request = retriever_service.GetDocumentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_document]

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

    def update_document(
        self,
        request: Optional[Union[retriever_service.UpdateDocumentRequest, dict]] = None,
        *,
        document: Optional[retriever.Document] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Updates a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateDocumentRequest(
                )

                # Make the request
                response = client.update_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdateDocumentRequest, dict]):
                The request object. Request to update a ``Document``.
            document (google.ai.generativelanguage_v1beta.types.Document):
                Required. The ``Document`` to update.
                This corresponds to the ``document`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to update. Currently, this
                only supports updating ``display_name`` and
                ``custom_metadata``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([document, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateDocumentRequest):
            request = retriever_service.UpdateDocumentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if document is not None:
                request.document = document
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_document]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("document.name", request.document.name),)
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

    def delete_document(
        self,
        request: Optional[Union[retriever_service.DeleteDocumentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteDocumentRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_document(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteDocumentRequest, dict]):
                The request object. Request to delete a ``Document``.
            name (str):
                Required. The resource name of the ``Document`` to
                delete. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

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
        if not isinstance(request, retriever_service.DeleteDocumentRequest):
            request = retriever_service.DeleteDocumentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_document]

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

    def list_documents(
        self,
        request: Optional[Union[retriever_service.ListDocumentsRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListDocumentsPager:
        r"""Lists all ``Document``\ s in a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_documents():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListDocumentsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_documents(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListDocumentsRequest, dict]):
                The request object. Request for listing ``Document``\ s.
            parent (str):
                Required. The name of the ``Corpus`` containing
                ``Document``\ s. Example: ``corpora/my-corpus-123``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListDocumentsPager:
                Response from ListDocuments containing a paginated list of Documents.
                   The Documents are sorted by ascending
                   document.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListDocumentsRequest):
            request = retriever_service.ListDocumentsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_documents]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListDocumentsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def query_document(
        self,
        request: Optional[Union[retriever_service.QueryDocumentRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.QueryDocumentResponse:
        r"""Performs semantic search over a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_query_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.QueryDocumentRequest(
                    name="name_value",
                    query="query_value",
                )

                # Make the request
                response = client.query_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.QueryDocumentRequest, dict]):
                The request object. Request for querying a ``Document``.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.QueryDocumentResponse:
                Response from QueryDocument containing a list of
                relevant chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.QueryDocumentRequest):
            request = retriever_service.QueryDocumentRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.query_document]

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

    def create_chunk(
        self,
        request: Optional[Union[retriever_service.CreateChunkRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        chunk: Optional[retriever.Chunk] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Creates a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                chunk = generativelanguage_v1beta.Chunk()
                chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.CreateChunkRequest(
                    parent="parent_value",
                    chunk=chunk,
                )

                # Make the request
                response = client.create_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateChunkRequest, dict]):
                The request object. Request to create a ``Chunk``.
            parent (str):
                Required. The name of the ``Document`` where this
                ``Chunk`` will be created. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            chunk (google.ai.generativelanguage_v1beta.types.Chunk):
                Required. The ``Chunk`` to create.
                This corresponds to the ``chunk`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, chunk])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateChunkRequest):
            request = retriever_service.CreateChunkRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent
            if chunk is not None:
                request.chunk = chunk

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_chunk]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

    def batch_create_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchCreateChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.BatchCreateChunksResponse:
        r"""Batch create ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_batch_create_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.CreateChunkRequest()
                requests.parent = "parent_value"
                requests.chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.BatchCreateChunksRequest(
                    requests=requests,
                )

                # Make the request
                response = client.batch_create_chunks(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.BatchCreateChunksRequest, dict]):
                The request object. Request to batch create ``Chunk``\ s.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchCreateChunksResponse:
                Response from BatchCreateChunks containing a list of
                created Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchCreateChunksRequest):
            request = retriever_service.BatchCreateChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_create_chunks]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

    def get_chunk(
        self,
        request: Optional[Union[retriever_service.GetChunkRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Gets information about a specific ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetChunkRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetChunkRequest, dict]):
                The request object. Request for getting information about a specific
                ``Chunk``.
            name (str):
                Required. The name of the ``Chunk`` to retrieve.
                Example:
                ``corpora/my-corpus-123/documents/the-doc-abc/chunks/some-chunk``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

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
        if not isinstance(request, retriever_service.GetChunkRequest):
            request = retriever_service.GetChunkRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_chunk]

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

    def update_chunk(
        self,
        request: Optional[Union[retriever_service.UpdateChunkRequest, dict]] = None,
        *,
        chunk: Optional[retriever.Chunk] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Updates a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                chunk = generativelanguage_v1beta.Chunk()
                chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.UpdateChunkRequest(
                    chunk=chunk,
                )

                # Make the request
                response = client.update_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdateChunkRequest, dict]):
                The request object. Request to update a ``Chunk``.
            chunk (google.ai.generativelanguage_v1beta.types.Chunk):
                Required. The ``Chunk`` to update.
                This corresponds to the ``chunk`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to update. Currently, this
                only supports updating ``custom_metadata`` and ``data``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([chunk, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateChunkRequest):
            request = retriever_service.UpdateChunkRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if chunk is not None:
                request.chunk = chunk
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_chunk]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("chunk.name", request.chunk.name),)
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

    def batch_update_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchUpdateChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.BatchUpdateChunksResponse:
        r"""Batch update ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_batch_update_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.UpdateChunkRequest()
                requests.chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.BatchUpdateChunksRequest(
                    requests=requests,
                )

                # Make the request
                response = client.batch_update_chunks(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.BatchUpdateChunksRequest, dict]):
                The request object. Request to batch update ``Chunk``\ s.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchUpdateChunksResponse:
                Response from BatchUpdateChunks containing a list of
                updated Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchUpdateChunksRequest):
            request = retriever_service.BatchUpdateChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_update_chunks]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

    def delete_chunk(
        self,
        request: Optional[Union[retriever_service.DeleteChunkRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteChunkRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_chunk(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteChunkRequest, dict]):
                The request object. Request to delete a ``Chunk``.
            name (str):
                Required. The resource name of the ``Chunk`` to delete.
                Example:
                ``corpora/my-corpus-123/documents/the-doc-abc/chunks/some-chunk``

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
        if not isinstance(request, retriever_service.DeleteChunkRequest):
            request = retriever_service.DeleteChunkRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_chunk]

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

    def batch_delete_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchDeleteChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Batch delete ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_batch_delete_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.DeleteChunkRequest()
                requests.name = "name_value"

                request = generativelanguage_v1beta.BatchDeleteChunksRequest(
                    requests=requests,
                )

                # Make the request
                client.batch_delete_chunks(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.BatchDeleteChunksRequest, dict]):
                The request object. Request to batch delete ``Chunk``\ s.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchDeleteChunksRequest):
            request = retriever_service.BatchDeleteChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_delete_chunks]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

    def list_chunks(
        self,
        request: Optional[Union[retriever_service.ListChunksRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListChunksPager:
        r"""Lists all ``Chunk``\ s in a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListChunksRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_chunks(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListChunksRequest, dict]):
                The request object. Request for listing ``Chunk``\ s.
            parent (str):
                Required. The name of the ``Document`` containing
                ``Chunk``\ s. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListChunksPager:
                Response from ListChunks containing a paginated list of Chunks.
                   The Chunks are sorted by ascending chunk.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListChunksRequest):
            request = retriever_service.ListChunksRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_chunks]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
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

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListChunksPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "RetrieverServiceClient":
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


__all__ = ("RetrieverServiceClient",)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\otTables.py ===
# coding: utf-8
"""fontTools.ttLib.tables.otTables -- A collection of classes representing the various
OpenType subtables.

Most are constructed upon import from data in otData.py, all are populated with
converter objects from otConverters.py.
"""
import copy
from enum import IntEnum
from functools import reduce
from math import radians
import itertools
from collections import defaultdict, namedtuple
from fontTools.ttLib import OPTIMIZE_FONT_SPEED
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.ttLib.tables.otTraverse import dfs_base_table
from fontTools.misc.arrayTools import quantizeRect
from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform, Identity, DecomposedTransform
from fontTools.misc.textTools import bytesjoin, pad, safeEval
from fontTools.misc.vector import Vector
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.transformPen import TransformPen
from .otBase import (
    BaseTable,
    FormatSwitchingBaseTable,
    ValueRecord,
    CountReference,
    getFormatSwitchingBaseTableClass,
)
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
)
from fontTools.feaLib.lookupDebugInfo import LookupDebugInfo, LOOKUP_DEBUG_INFO_KEY
import logging
import struct
import array
import sys
from enum import IntFlag
from typing import TYPE_CHECKING, Iterator, List, Optional, Set

if TYPE_CHECKING:
    from fontTools.ttLib.ttGlyphSet import _TTGlyphSet


log = logging.getLogger(__name__)


class VarComponentFlags(IntFlag):
    RESET_UNSPECIFIED_AXES = 1 << 0

    HAVE_AXES = 1 << 1

    AXIS_VALUES_HAVE_VARIATION = 1 << 2
    TRANSFORM_HAS_VARIATION = 1 << 3

    HAVE_TRANSLATE_X = 1 << 4
    HAVE_TRANSLATE_Y = 1 << 5
    HAVE_ROTATION = 1 << 6

    HAVE_CONDITION = 1 << 7

    HAVE_SCALE_X = 1 << 8
    HAVE_SCALE_Y = 1 << 9
    HAVE_TCENTER_X = 1 << 10
    HAVE_TCENTER_Y = 1 << 11

    GID_IS_24BIT = 1 << 12

    HAVE_SKEW_X = 1 << 13
    HAVE_SKEW_Y = 1 << 14

    RESERVED_MASK = (1 << 32) - (1 << 15)


VarTransformMappingValues = namedtuple(
    "VarTransformMappingValues",
    ["flag", "fractionalBits", "scale", "defaultValue"],
)

VAR_TRANSFORM_MAPPING = {
    "translateX": VarTransformMappingValues(
        VarComponentFlags.HAVE_TRANSLATE_X, 0, 1, 0
    ),
    "translateY": VarTransformMappingValues(
        VarComponentFlags.HAVE_TRANSLATE_Y, 0, 1, 0
    ),
    "rotation": VarTransformMappingValues(VarComponentFlags.HAVE_ROTATION, 12, 180, 0),
    "scaleX": VarTransformMappingValues(VarComponentFlags.HAVE_SCALE_X, 10, 1, 1),
    "scaleY": VarTransformMappingValues(VarComponentFlags.HAVE_SCALE_Y, 10, 1, 1),
    "skewX": VarTransformMappingValues(VarComponentFlags.HAVE_SKEW_X, 12, -180, 0),
    "skewY": VarTransformMappingValues(VarComponentFlags.HAVE_SKEW_Y, 12, 180, 0),
    "tCenterX": VarTransformMappingValues(VarComponentFlags.HAVE_TCENTER_X, 0, 1, 0),
    "tCenterY": VarTransformMappingValues(VarComponentFlags.HAVE_TCENTER_Y, 0, 1, 0),
}

# Probably should be somewhere in fontTools.misc
_packer = {
    1: lambda v: struct.pack(">B", v),
    2: lambda v: struct.pack(">H", v),
    3: lambda v: struct.pack(">L", v)[1:],
    4: lambda v: struct.pack(">L", v),
}
_unpacker = {
    1: lambda v: struct.unpack(">B", v)[0],
    2: lambda v: struct.unpack(">H", v)[0],
    3: lambda v: struct.unpack(">L", b"\0" + v)[0],
    4: lambda v: struct.unpack(">L", v)[0],
}


def _read_uint32var(data, i):
    """Read a variable-length number from data starting at index i.

    Return the number and the next index.
    """

    b0 = data[i]
    if b0 < 0x80:
        return b0, i + 1
    elif b0 < 0xC0:
        return (b0 - 0x80) << 8 | data[i + 1], i + 2
    elif b0 < 0xE0:
        return (b0 - 0xC0) << 16 | data[i + 1] << 8 | data[i + 2], i + 3
    elif b0 < 0xF0:
        return (b0 - 0xE0) << 24 | data[i + 1] << 16 | data[i + 2] << 8 | data[
            i + 3
        ], i + 4
    else:
        return (b0 - 0xF0) << 32 | data[i + 1] << 24 | data[i + 2] << 16 | data[
            i + 3
        ] << 8 | data[i + 4], i + 5


def _write_uint32var(v):
    """Write a variable-length number.

    Return the data.
    """
    if v < 0x80:
        return struct.pack(">B", v)
    elif v < 0x4000:
        return struct.pack(">H", (v | 0x8000))
    elif v < 0x200000:
        return struct.pack(">L", (v | 0xC00000))[1:]
    elif v < 0x10000000:
        return struct.pack(">L", (v | 0xE0000000))
    else:
        return struct.pack(">B", 0xF0) + struct.pack(">L", v)


class VarComponent:
    def __init__(self):
        self.populateDefaults()

    def populateDefaults(self, propagator=None):
        self.flags = 0
        self.glyphName = None
        self.conditionIndex = None
        self.axisIndicesIndex = None
        self.axisValues = ()
        self.axisValuesVarIndex = NO_VARIATION_INDEX
        self.transformVarIndex = NO_VARIATION_INDEX
        self.transform = DecomposedTransform()

    def decompile(self, data, font, localState):
        i = 0
        self.flags, i = _read_uint32var(data, i)
        flags = self.flags

        gidSize = 3 if flags & VarComponentFlags.GID_IS_24BIT else 2
        glyphID = _unpacker[gidSize](data[i : i + gidSize])
        i += gidSize
        self.glyphName = font.glyphOrder[glyphID]

        if flags & VarComponentFlags.HAVE_CONDITION:
            self.conditionIndex, i = _read_uint32var(data, i)

        if flags & VarComponentFlags.HAVE_AXES:
            self.axisIndicesIndex, i = _read_uint32var(data, i)
        else:
            self.axisIndicesIndex = None

        if self.axisIndicesIndex is None:
            numAxes = 0
        else:
            axisIndices = localState["AxisIndicesList"].Item[self.axisIndicesIndex]
            numAxes = len(axisIndices)

        if flags & VarComponentFlags.HAVE_AXES:
            axisValues, i = TupleVariation.decompileDeltas_(numAxes, data, i)
            self.axisValues = tuple(fi2fl(v, 14) for v in axisValues)
        else:
            self.axisValues = ()
        assert len(self.axisValues) == numAxes

        if flags & VarComponentFlags.AXIS_VALUES_HAVE_VARIATION:
            self.axisValuesVarIndex, i = _read_uint32var(data, i)
        else:
            self.axisValuesVarIndex = NO_VARIATION_INDEX
        if flags & VarComponentFlags.TRANSFORM_HAS_VARIATION:
            self.transformVarIndex, i = _read_uint32var(data, i)
        else:
            self.transformVarIndex = NO_VARIATION_INDEX

        self.transform = DecomposedTransform()

        def read_transform_component(values):
            nonlocal i
            if flags & values.flag:
                v = (
                    fi2fl(
                        struct.unpack(">h", data[i : i + 2])[0], values.fractionalBits
                    )
                    * values.scale
                )
                i += 2
                return v
            else:
                return values.defaultValue

        for attr_name, mapping_values in VAR_TRANSFORM_MAPPING.items():
            value = read_transform_component(mapping_values)
            setattr(self.transform, attr_name, value)

        if not (flags & VarComponentFlags.HAVE_SCALE_Y):
            self.transform.scaleY = self.transform.scaleX

        n = flags & VarComponentFlags.RESERVED_MASK
        while n:
            _, i = _read_uint32var(data, i)
            n &= n - 1

        return data[i:]

    def compile(self, font):
        optimizeSpeed = font.cfg[OPTIMIZE_FONT_SPEED]

        data = []

        flags = self.flags

        glyphID = font.getGlyphID(self.glyphName)
        if glyphID > 65535:
            flags |= VarComponentFlags.GID_IS_24BIT
            data.append(_packer[3](glyphID))
        else:
            flags &= ~VarComponentFlags.GID_IS_24BIT
            data.append(_packer[2](glyphID))

        if self.conditionIndex is not None:
            flags |= VarComponentFlags.HAVE_CONDITION
            data.append(_write_uint32var(self.conditionIndex))

        numAxes = len(self.axisValues)

        if numAxes:
            flags |= VarComponentFlags.HAVE_AXES
            data.append(_write_uint32var(self.axisIndicesIndex))
            data.append(
                TupleVariation.compileDeltaValues_(
                    [fl2fi(v, 14) for v in self.axisValues],
                    optimizeSize=not optimizeSpeed,
                )
            )
        else:
            flags &= ~VarComponentFlags.HAVE_AXES

        if self.axisValuesVarIndex != NO_VARIATION_INDEX:
            flags |= VarComponentFlags.AXIS_VALUES_HAVE_VARIATION
            data.append(_write_uint32var(self.axisValuesVarIndex))
        else:
            flags &= ~VarComponentFlags.AXIS_VALUES_HAVE_VARIATION
        if self.transformVarIndex != NO_VARIATION_INDEX:
            flags |= VarComponentFlags.TRANSFORM_HAS_VARIATION
            data.append(_write_uint32var(self.transformVarIndex))
        else:
            flags &= ~VarComponentFlags.TRANSFORM_HAS_VARIATION

        def write_transform_component(value, values):
            if flags & values.flag:
                return struct.pack(
                    ">h", fl2fi(value / values.scale, values.fractionalBits)
                )
            else:
                return b""

        for attr_name, mapping_values in VAR_TRANSFORM_MAPPING.items():
            value = getattr(self.transform, attr_name)
            data.append(write_transform_component(value, mapping_values))

        return _write_uint32var(flags) + bytesjoin(data)

    def toXML(self, writer, ttFont, attrs):
        writer.begintag("VarComponent", attrs)
        writer.newline()

        def write(name, value, attrs=()):
            if value is not None:
                writer.simpletag(name, (("value", value),) + attrs)
                writer.newline()

        write("glyphName", self.glyphName)

        if self.conditionIndex is not None:
            write("conditionIndex", self.conditionIndex)
        if self.axisIndicesIndex is not None:
            write("axisIndicesIndex", self.axisIndicesIndex)
        if (
            self.axisIndicesIndex is not None
            or self.flags & VarComponentFlags.RESET_UNSPECIFIED_AXES
        ):
            if self.flags & VarComponentFlags.RESET_UNSPECIFIED_AXES:
                attrs = (("resetUnspecifiedAxes", 1),)
            else:
                attrs = ()
            write("axisValues", [float(fl2str(v, 14)) for v in self.axisValues], attrs)

        if self.axisValuesVarIndex != NO_VARIATION_INDEX:
            write("axisValuesVarIndex", self.axisValuesVarIndex)
        if self.transformVarIndex != NO_VARIATION_INDEX:
            write("transformVarIndex", self.transformVarIndex)

        # Only write transform components that are specified in the
        # flags, even if they are the default value.
        for attr_name, mapping in VAR_TRANSFORM_MAPPING.items():
            if not (self.flags & mapping.flag):
                continue
            v = getattr(self.transform, attr_name)
            write(attr_name, fl2str(v, mapping.fractionalBits))

        writer.endtag("VarComponent")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        content = [c for c in content if isinstance(c, tuple)]

        self.populateDefaults()

        for name, attrs, content in content:
            assert not content
            v = attrs["value"]

            if name == "glyphName":
                self.glyphName = v
            elif name == "conditionIndex":
                self.conditionIndex = safeEval(v)
            elif name == "axisIndicesIndex":
                self.axisIndicesIndex = safeEval(v)
            elif name == "axisValues":
                self.axisValues = tuple(str2fl(v, 14) for v in safeEval(v))
                if safeEval(attrs.get("resetUnspecifiedAxes", "0")):
                    self.flags |= VarComponentFlags.RESET_UNSPECIFIED_AXES
            elif name == "axisValuesVarIndex":
                self.axisValuesVarIndex = safeEval(v)
            elif name == "transformVarIndex":
                self.transformVarIndex = safeEval(v)
            elif name in VAR_TRANSFORM_MAPPING:
                setattr(
                    self.transform,
                    name,
                    safeEval(v),
                )
                self.flags |= VAR_TRANSFORM_MAPPING[name].flag
            else:
                assert False, name

    def applyTransformDeltas(self, deltas):
        i = 0

        def read_transform_component_delta(values):
            nonlocal i
            if self.flags & values.flag:
                v = fi2fl(deltas[i], values.fractionalBits) * values.scale
                i += 1
                return v
            else:
                return 0

        for attr_name, mapping_values in VAR_TRANSFORM_MAPPING.items():
            value = read_transform_component_delta(mapping_values)
            setattr(
                self.transform, attr_name, getattr(self.transform, attr_name) + value
            )

        if not (self.flags & VarComponentFlags.HAVE_SCALE_Y):
            self.transform.scaleY = self.transform.scaleX

        assert i == len(deltas), (i, len(deltas))

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result


class VarCompositeGlyph:
    def __init__(self, components=None):
        self.components = components if components is not None else []

    def decompile(self, data, font, localState):
        self.components = []
        while data:
            component = VarComponent()
            data = component.decompile(data, font, localState)
            self.components.append(component)

    def compile(self, font):
        data = []
        for component in self.components:
            data.append(component.compile(font))
        return bytesjoin(data)

    def toXML(self, xmlWriter, font, attrs, name):
        xmlWriter.begintag("VarCompositeGlyph", attrs)
        xmlWriter.newline()
        for i, component in enumerate(self.components):
            component.toXML(xmlWriter, font, [("index", i)])
        xmlWriter.endtag("VarCompositeGlyph")
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        content = [c for c in content if isinstance(c, tuple)]
        for name, attrs, content in content:
            assert name == "VarComponent"
            component = VarComponent()
            component.fromXML(name, attrs, content, font)
            self.components.append(component)


class AATStateTable(object):
    def __init__(self):
        self.GlyphClasses = {}  # GlyphID --> GlyphClass
        self.States = []  # List of AATState, indexed by state number
        self.PerGlyphLookups = []  # [{GlyphID:GlyphID}, ...]


class AATState(object):
    def __init__(self):
        self.Transitions = {}  # GlyphClass --> AATAction


class AATAction(object):
    _FLAGS = None

    @staticmethod
    def compileActions(font, states):
        return (None, None)

    def _writeFlagsToXML(self, xmlWriter):
        flags = [f for f in self._FLAGS if self.__dict__[f]]
        if flags:
            xmlWriter.simpletag("Flags", value=",".join(flags))
            xmlWriter.newline()
        if self.ReservedFlags != 0:
            xmlWriter.simpletag("ReservedFlags", value="0x%04X" % self.ReservedFlags)
            xmlWriter.newline()

    def _setFlag(self, flag):
        assert flag in self._FLAGS, "unsupported flag %s" % flag
        self.__dict__[flag] = True


class RearrangementMorphAction(AATAction):
    staticSize = 4
    actionHeaderSize = 0
    _FLAGS = ["MarkFirst", "DontAdvance", "MarkLast"]

    _VERBS = {
        0: "no change",
        1: "Ax ⇒ xA",
        2: "xD ⇒ Dx",
        3: "AxD ⇒ DxA",
        4: "ABx ⇒ xAB",
        5: "ABx ⇒ xBA",
        6: "xCD ⇒ CDx",
        7: "xCD ⇒ DCx",
        8: "AxCD ⇒ CDxA",
        9: "AxCD ⇒ DCxA",
        10: "ABxD ⇒ DxAB",
        11: "ABxD ⇒ DxBA",
        12: "ABxCD ⇒ CDxAB",
        13: "ABxCD ⇒ CDxBA",
        14: "ABxCD ⇒ DCxAB",
        15: "ABxCD ⇒ DCxBA",
    }

    def __init__(self):
        self.NewState = 0
        self.Verb = 0
        self.MarkFirst = False
        self.DontAdvance = False
        self.MarkLast = False
        self.ReservedFlags = 0

    def compile(self, writer, font, actionIndex):
        assert actionIndex is None
        writer.writeUShort(self.NewState)
        assert self.Verb >= 0 and self.Verb <= 15, self.Verb
        flags = self.Verb | self.ReservedFlags
        if self.MarkFirst:
            flags |= 0x8000
        if self.DontAdvance:
            flags |= 0x4000
        if self.MarkLast:
            flags |= 0x2000
        writer.writeUShort(flags)

    def decompile(self, reader, font, actionReader):
        assert actionReader is None
        self.NewState = reader.readUShort()
        flags = reader.readUShort()
        self.Verb = flags & 0xF
        self.MarkFirst = bool(flags & 0x8000)
        self.DontAdvance = bool(flags & 0x4000)
        self.MarkLast = bool(flags & 0x2000)
        self.ReservedFlags = flags & 0x1FF0

    def toXML(self, xmlWriter, font, attrs, name):
        xmlWriter.begintag(name, **attrs)
        xmlWriter.newline()
        xmlWriter.simpletag("NewState", value=self.NewState)
        xmlWriter.newline()
        self._writeFlagsToXML(xmlWriter)
        xmlWriter.simpletag("Verb", value=self.Verb)
        verbComment = self._VERBS.get(self.Verb)
        if verbComment is not None:
            xmlWriter.comment(verbComment)
        xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        self.NewState = self.Verb = self.ReservedFlags = 0
        self.MarkFirst = self.DontAdvance = self.MarkLast = False
        content = [t for t in content if isinstance(t, tuple)]
        for eltName, eltAttrs, eltContent in content:
            if eltName == "NewState":
                self.NewState = safeEval(eltAttrs["value"])
            elif eltName == "Verb":
                self.Verb = safeEval(eltAttrs["value"])
            elif eltName == "ReservedFlags":
                self.ReservedFlags = safeEval(eltAttrs["value"])
            elif eltName == "Flags":
                for flag in eltAttrs["value"].split(","):
                    self._setFlag(flag.strip())


class ContextualMorphAction(AATAction):
    staticSize = 8
    actionHeaderSize = 0
    _FLAGS = ["SetMark", "DontAdvance"]

    def __init__(self):
        self.NewState = 0
        self.SetMark, self.DontAdvance = False, False
        self.ReservedFlags = 0
        self.MarkIndex, self.CurrentIndex = 0xFFFF, 0xFFFF

    def compile(self, writer, font, actionIndex):
        assert actionIndex is None
        writer.writeUShort(self.NewState)
        flags = self.ReservedFlags
        if self.SetMark:
            flags |= 0x8000
        if self.DontAdvance:
            flags |= 0x4000
        writer.writeUShort(flags)
        writer.writeUShort(self.MarkIndex)
        writer.writeUShort(self.CurrentIndex)

    def decompile(self, reader, font, actionReader):
        assert actionReader is None
        self.NewState = reader.readUShort()
        flags = reader.readUShort()
        self.SetMark = bool(flags & 0x8000)
        self.DontAdvance = bool(flags & 0x4000)
        self.ReservedFlags = flags & 0x3FFF
        self.MarkIndex = reader.readUShort()
        self.CurrentIndex = reader.readUShort()

    def toXML(self, xmlWriter, font, attrs, name):
        xmlWriter.begintag(name, **attrs)
        xmlWriter.newline()
        xmlWriter.simpletag("NewState", value=self.NewState)
        xmlWriter.newline()
        self._writeFlagsToXML(xmlWriter)
        xmlWriter.simpletag("MarkIndex", value=self.MarkIndex)
        xmlWriter.newline()
        xmlWriter.simpletag("CurrentIndex", value=self.CurrentIndex)
        xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        self.NewState = self.ReservedFlags = 0
        self.SetMark = self.DontAdvance = False
        self.MarkIndex, self.CurrentIndex = 0xFFFF, 0xFFFF
        content = [t for t in content if isinstance(t, tuple)]
        for eltName, eltAttrs, eltContent in content:
            if eltName == "NewState":
                self.NewState = safeEval(eltAttrs["value"])
            elif eltName == "Flags":
                for flag in eltAttrs["value"].split(","):
                    self._setFlag(flag.strip())
            elif eltName == "ReservedFlags":
                self.ReservedFlags = safeEval(eltAttrs["value"])
            elif eltName == "MarkIndex":
                self.MarkIndex = safeEval(eltAttrs["value"])
            elif eltName == "CurrentIndex":
                self.CurrentIndex = safeEval(eltAttrs["value"])


class LigAction(object):
    def __init__(self):
        self.Store = False
        # GlyphIndexDelta is a (possibly negative) delta that gets
        # added to the glyph ID at the top of the AAT runtime
        # execution stack. It is *not* a byte offset into the
        # morx table. The result of the addition, which is performed
        # at run time by the shaping engine, is an index into
        # the ligature components table. See 'morx' specification.
        # In the AAT specification, this field is called Offset;
        # but its meaning is quite different from other offsets
        # in either AAT or OpenType, so we use a different name.
        self.GlyphIndexDelta = 0


class LigatureMorphAction(AATAction):
    staticSize = 6

    # 4 bytes for each of {action,ligComponents,ligatures}Offset
    actionHeaderSize = 12

    _FLAGS = ["SetComponent", "DontAdvance"]

    def __init__(self):
        self.NewState = 0
        self.SetComponent, self.DontAdvance = False, False
        self.ReservedFlags = 0
        self.Actions = []

    def compile(self, writer, font, actionIndex):
        assert actionIndex is not None
        writer.writeUShort(self.NewState)
        flags = self.ReservedFlags
        if self.SetComponent:
            flags |= 0x8000
        if self.DontAdvance:
            flags |= 0x4000
        if len(self.Actions) > 0:
            flags |= 0x2000
        writer.writeUShort(flags)
        if len(self.Actions) > 0:
            actions = self.compileLigActions()
            writer.writeUShort(actionIndex[actions])
        else:
            writer.writeUShort(0)

    def decompile(self, reader, font, actionReader):
        assert actionReader is not None
        self.NewState = reader.readUShort()
        flags = reader.readUShort()
        self.SetComponent = bool(flags & 0x8000)
        self.DontAdvance = bool(flags & 0x4000)
        performAction = bool(flags & 0x2000)
        # As of 2017-09-12, the 'morx' specification says that
        # the reserved bitmask in ligature subtables is 0x3FFF.
        # However, the specification also defines a flag 0x2000,
        # so the reserved value should actually be 0x1FFF.
        # TODO: Report this specification bug to Apple.
        self.ReservedFlags = flags & 0x1FFF
        actionIndex = reader.readUShort()
        if performAction:
            self.Actions = self._decompileLigActions(actionReader, actionIndex)
        else:
            self.Actions = []

    @staticmethod
    def compileActions(font, states):
        result, actions, actionIndex = b"", set(), {}
        for state in states:
            for _glyphClass, trans in state.Transitions.items():
                actions.add(trans.compileLigActions())
        # Sort the compiled actions in decreasing order of
        # length, so that the longer sequence come before the
        # shorter ones.  For each compiled action ABCD, its
        # suffixes BCD, CD, and D do not be encoded separately
        # (in case they occur); instead, we can just store an
        # index that points into the middle of the longer
        # sequence. Every compiled AAT ligature sequence is
        # terminated with an end-of-sequence flag, which can
        # only be set on the last element of the sequence.
        # Therefore, it is sufficient to consider just the
        # suffixes.
        for a in sorted(actions, key=lambda x: (-len(x), x)):
            if a not in actionIndex:
                for i in range(0, len(a), 4):
                    suffix = a[i:]
                    suffixIndex = (len(result) + i) // 4
                    actionIndex.setdefault(suffix, suffixIndex)
                result += a
        result = pad(result, 4)
        return (result, actionIndex)

    def compileLigActions(self):
        result = []
        for i, action in enumerate(self.Actions):
            last = i == len(self.Actions) - 1
            value = action.GlyphIndexDelta & 0x3FFFFFFF
            value |= 0x80000000 if last else 0
            value |= 0x40000000 if action.Store else 0
            result.append(struct.pack(">L", value))
        return bytesjoin(result)

    def _decompileLigActions(self, actionReader, actionIndex):
        actions = []
        last = False
        reader = actionReader.getSubReader(actionReader.pos + actionIndex * 4)
        while not last:
            value = reader.readULong()
            last = bool(value & 0x80000000)
            action = LigAction()
            actions.append(action)
            action.Store = bool(value & 0x40000000)
            delta = value & 0x3FFFFFFF
            if delta >= 0x20000000:  # sign-extend 30-bit value
                delta = -0x40000000 + delta
            action.GlyphIndexDelta = delta
        return actions

    def fromXML(self, name, attrs, content, font):
        self.NewState = self.ReservedFlags = 0
        self.SetComponent = self.DontAdvance = False
        self.ReservedFlags = 0
        self.Actions = []
        content = [t for t in content if isinstance(t, tuple)]
        for eltName, eltAttrs, eltContent in content:
            if eltName == "NewState":
                self.NewState = safeEval(eltAttrs["value"])
            elif eltName == "Flags":
                for flag in eltAttrs["value"].split(","):
                    self._setFlag(flag.strip())
            elif eltName == "ReservedFlags":
                self.ReservedFlags = safeEval(eltAttrs["value"])
            elif eltName == "Action":
                action = LigAction()
                flags = eltAttrs.get("Flags", "").split(",")
                flags = [f.strip() for f in flags]
                action.Store = "Store" in flags
                action.GlyphIndexDelta = safeEval(eltAttrs["GlyphIndexDelta"])
                self.Actions.append(action)

    def toXML(self, xmlWriter, font, attrs, name):
        xmlWriter.begintag(name, **attrs)
        xmlWriter.newline()
        xmlWriter.simpletag("NewState", value=self.NewState)
        xmlWriter.newline()
        self._writeFlagsToXML(xmlWriter)
        for action in self.Actions:
            attribs = [("GlyphIndexDelta", action.GlyphIndexDelta)]
            if action.Store:
                attribs.append(("Flags", "Store"))
            xmlWriter.simpletag("Action", attribs)
            xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()


class InsertionMorphAction(AATAction):
    staticSize = 8
    actionHeaderSize = 4  # 4 bytes for actionOffset
    _FLAGS = [
        "SetMark",
        "DontAdvance",
        "CurrentIsKashidaLike",
        "MarkedIsKashidaLike",
        "CurrentInsertBefore",
        "MarkedInsertBefore",
    ]

    def __init__(self):
        self.NewState = 0
        for flag in self._FLAGS:
            setattr(self, flag, False)
        self.ReservedFlags = 0
        self.CurrentInsertionAction, self.MarkedInsertionAction = [], []

    def compile(self, writer, font, actionIndex):
        assert actionIndex is not None
        writer.writeUShort(self.NewState)
        flags = self.ReservedFlags
        if self.SetMark:
            flags |= 0x8000
        if self.DontAdvance:
            flags |= 0x4000
        if self.CurrentIsKashidaLike:
            flags |= 0x2000
        if self.MarkedIsKashidaLike:
            flags |= 0x1000
        if self.CurrentInsertBefore:
            flags |= 0x0800
        if self.MarkedInsertBefore:
            flags |= 0x0400
        flags |= len(self.CurrentInsertionAction) << 5
        flags |= len(self.MarkedInsertionAction)
        writer.writeUShort(flags)
        if len(self.CurrentInsertionAction) > 0:
            currentIndex = actionIndex[tuple(self.CurrentInsertionAction)]
        else:
            currentIndex = 0xFFFF
        writer.writeUShort(currentIndex)
        if len(self.MarkedInsertionAction) > 0:
            markedIndex = actionIndex[tuple(self.MarkedInsertionAction)]
        else:
            markedIndex = 0xFFFF
        writer.writeUShort(markedIndex)

    def decompile(self, reader, font, actionReader):
        assert actionReader is not None
        self.NewState = reader.readUShort()
        flags = reader.readUShort()
        self.SetMark = bool(flags & 0x8000)
        self.DontAdvance = bool(flags & 0x4000)
        self.CurrentIsKashidaLike = bool(flags & 0x2000)
        self.MarkedIsKashidaLike = bool(flags & 0x1000)
        self.CurrentInsertBefore = bool(flags & 0x0800)
        self.MarkedInsertBefore = bool(flags & 0x0400)
        self.CurrentInsertionAction = self._decompileInsertionAction(
            actionReader, font, index=reader.readUShort(), count=((flags & 0x03E0) >> 5)
        )
        self.MarkedInsertionAction = self._decompileInsertionAction(
            actionReader, font, index=reader.readUShort(), count=(flags & 0x001F)
        )

    def _decompileInsertionAction(self, actionReader, font, index, count):
        if index == 0xFFFF or count == 0:
            return []
        reader = actionReader.getSubReader(actionReader.pos + index * 2)
        return font.getGlyphNameMany(reader.readUShortArray(count))

    def toXML(self, xmlWriter, font, attrs, name):
        xmlWriter.begintag(name, **attrs)
        xmlWriter.newline()
        xmlWriter.simpletag("NewState", value=self.NewState)
        xmlWriter.newline()
        self._writeFlagsToXML(xmlWriter)
        for g in self.CurrentInsertionAction:
            xmlWriter.simpletag("CurrentInsertionAction", glyph=g)
            xmlWriter.newline()
        for g in self.MarkedInsertionAction:
            xmlWriter.simpletag("MarkedInsertionAction", glyph=g)
            xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        self.__init__()
        content = [t for t in content if isinstance(t, tuple)]
        for eltName, eltAttrs, eltContent in content:
            if eltName == "NewState":
                self.NewState = safeEval(eltAttrs["value"])
            elif eltName == "Flags":
                for flag in eltAttrs["value"].split(","):
                    self._setFlag(flag.strip())
            elif eltName == "CurrentInsertionAction":
                self.CurrentInsertionAction.append(eltAttrs["glyph"])
            elif eltName == "MarkedInsertionAction":
                self.MarkedInsertionAction.append(eltAttrs["glyph"])
            else:
                assert False, eltName

    @staticmethod
    def compileActions(font, states):
        actions, actionIndex, result = set(), {}, b""
        for state in states:
            for _glyphClass, trans in state.Transitions.items():
                if trans.CurrentInsertionAction is not None:
                    actions.add(tuple(trans.CurrentInsertionAction))
                if trans.MarkedInsertionAction is not None:
                    actions.add(tuple(trans.MarkedInsertionAction))
        # Sort the compiled actions in decreasing order of
        # length, so that the longer sequence come before the
        # shorter ones.
        for action in sorted(actions, key=lambda x: (-len(x), x)):
            # We insert all sub-sequences of the action glyph sequence
            # into actionIndex. For example, if one action triggers on
            # glyph sequence [A, B, C, D, E] and another action triggers
            # on [C, D], we return result=[A, B, C, D, E] (as list of
            # encoded glyph IDs), and actionIndex={('A','B','C','D','E'): 0,
            # ('C','D'): 2}.
            if action in actionIndex:
                continue
            for start in range(0, len(action)):
                startIndex = (len(result) // 2) + start
                for limit in range(start, len(action)):
                    glyphs = action[start : limit + 1]
                    actionIndex.setdefault(glyphs, startIndex)
            for glyph in action:
                glyphID = font.getGlyphID(glyph)
                result += struct.pack(">H", glyphID)
        return result, actionIndex


class FeatureParams(BaseTable):
    def compile(self, writer, font):
        assert (
            featureParamTypes.get(writer["FeatureTag"]) == self.__class__
        ), "Wrong FeatureParams type for feature '%s': %s" % (
            writer["FeatureTag"],
            self.__class__.__name__,
        )
        BaseTable.compile(self, writer, font)

    def toXML(self, xmlWriter, font, attrs=None, name=None):
        BaseTable.toXML(self, xmlWriter, font, attrs, name=self.__class__.__name__)


class FeatureParamsSize(FeatureParams):
    pass


class FeatureParamsStylisticSet(FeatureParams):
    pass


class FeatureParamsCharacterVariants(FeatureParams):
    pass


class Coverage(FormatSwitchingBaseTable):
    # manual implementation to get rid of glyphID dependencies

    def populateDefaults(self, propagator=None):
        if not hasattr(self, "glyphs"):
            self.glyphs = []

    def postRead(self, rawTable, font):
        if self.Format == 1:
            self.glyphs = rawTable["GlyphArray"]
        elif self.Format == 2:
            glyphs = self.glyphs = []
            ranges = rawTable["RangeRecord"]
            # Some SIL fonts have coverage entries that don't have sorted
            # StartCoverageIndex.  If it is so, fixup and warn.  We undo
            # this when writing font out.
            sorted_ranges = sorted(ranges, key=lambda a: a.StartCoverageIndex)
            if ranges != sorted_ranges:
                log.warning("GSUB/GPOS Coverage is not sorted by glyph ids.")
                ranges = sorted_ranges
            del sorted_ranges
            for r in ranges:
                start = r.Start
                end = r.End
                startID = font.getGlyphID(start)
                endID = font.getGlyphID(end) + 1
                glyphs.extend(font.getGlyphNameMany(range(startID, endID)))
        else:
            self.glyphs = []
            log.warning("Unknown Coverage format: %s", self.Format)
        del self.Format  # Don't need this anymore

    def preWrite(self, font):
        glyphs = getattr(self, "glyphs", None)
        if glyphs is None:
            glyphs = self.glyphs = []
        format = 1
        rawTable = {"GlyphArray": glyphs}
        if glyphs:
            # find out whether Format 2 is more compact or not
            glyphIDs = font.getGlyphIDMany(glyphs)
            brokenOrder = sorted(glyphIDs) != glyphIDs

            last = glyphIDs[0]
            ranges = [[last]]
            for glyphID in glyphIDs[1:]:
                if glyphID != last + 1:
                    ranges[-1].append(last)
                    ranges.append([glyphID])
                last = glyphID
            ranges[-1].append(last)

            if brokenOrder or len(ranges) * 3 < len(glyphs):  # 3 words vs. 1 word
                # Format 2 is more compact
                index = 0
                for i in range(len(ranges)):
                    start, end = ranges[i]
                    r = RangeRecord()
                    r.StartID = start
                    r.Start = font.getGlyphName(start)
                    r.End = font.getGlyphName(end)
                    r.StartCoverageIndex = index
                    ranges[i] = r
                    index = index + end - start + 1
                if brokenOrder:
                    log.warning("GSUB/GPOS Coverage is not sorted by glyph ids.")
                    ranges.sort(key=lambda a: a.StartID)
                for r in ranges:
                    del r.StartID
                format = 2
                rawTable = {"RangeRecord": ranges}
            # else:
            # 	fallthrough; Format 1 is more compact
        self.Format = format
        return rawTable

    def toXML2(self, xmlWriter, font):
        for glyphName in getattr(self, "glyphs", []):
            xmlWriter.simpletag("Glyph", value=glyphName)
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        glyphs = getattr(self, "glyphs", None)
        if glyphs is None:
            glyphs = []
            self.glyphs = glyphs
        glyphs.append(attrs["value"])


# The special 0xFFFFFFFF delta-set index is used to indicate that there
# is no variation data in the ItemVariationStore for a given variable field
NO_VARIATION_INDEX = 0xFFFFFFFF


class DeltaSetIndexMap(getFormatSwitchingBaseTableClass("uint8")):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "mapping"):
            self.mapping = []

    def postRead(self, rawTable, font):
        assert (rawTable["EntryFormat"] & 0xFFC0) == 0
        self.mapping = rawTable["mapping"]

    @staticmethod
    def getEntryFormat(mapping):
        ored = 0
        for idx in mapping:
            ored |= idx

        inner = ored & 0xFFFF
        innerBits = 0
        while inner:
            innerBits += 1
            inner >>= 1
        innerBits = max(innerBits, 1)
        assert innerBits <= 16

        ored = (ored >> (16 - innerBits)) | (ored & ((1 << innerBits) - 1))
        if ored <= 0x000000FF:
            entrySize = 1
        elif ored <= 0x0000FFFF:
            entrySize = 2
        elif ored <= 0x00FFFFFF:
            entrySize = 3
        else:
            entrySize = 4

        return ((entrySize - 1) << 4) | (innerBits - 1)

    def preWrite(self, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = self.mapping = []
        self.Format = 1 if len(mapping) > 0xFFFF else 0
        rawTable = self.__dict__.copy()
        rawTable["MappingCount"] = len(mapping)
        rawTable["EntryFormat"] = self.getEntryFormat(mapping)
        return rawTable

    def toXML2(self, xmlWriter, font):
        # Make xml dump less verbose, by omitting no-op entries like:
        #   <Map index="..." outer="65535" inner="65535"/>
        xmlWriter.comment("Omitted values default to 0xFFFF/0xFFFF (no variations)")
        xmlWriter.newline()
        for i, value in enumerate(getattr(self, "mapping", [])):
            attrs = [("index", i)]
            if value != NO_VARIATION_INDEX:
                attrs.extend(
                    [
                        ("outer", value >> 16),
                        ("inner", value & 0xFFFF),
                    ]
                )
            xmlWriter.simpletag("Map", attrs)
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            self.mapping = mapping = []
        index = safeEval(attrs["index"])
        outer = safeEval(attrs.get("outer", "0xFFFF"))
        inner = safeEval(attrs.get("inner", "0xFFFF"))
        assert inner <= 0xFFFF
        mapping.insert(index, (outer << 16) | inner)

    def __getitem__(self, i):
        return self.mapping[i] if i < len(self.mapping) else NO_VARIATION_INDEX


class VarIdxMap(BaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "mapping"):
            self.mapping = {}

    def postRead(self, rawTable, font):
        assert (rawTable["EntryFormat"] & 0xFFC0) == 0
        glyphOrder = font.getGlyphOrder()
        mapList = rawTable["mapping"]
        mapList.extend([mapList[-1]] * (len(glyphOrder) - len(mapList)))
        self.mapping = dict(zip(glyphOrder, mapList))

    def preWrite(self, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = self.mapping = {}

        glyphOrder = font.getGlyphOrder()
        mapping = [mapping[g] for g in glyphOrder]
        while len(mapping) > 1 and mapping[-2] == mapping[-1]:
            del mapping[-1]

        rawTable = {"mapping": mapping}
        rawTable["MappingCount"] = len(mapping)
        rawTable["EntryFormat"] = DeltaSetIndexMap.getEntryFormat(mapping)
        return rawTable

    def toXML2(self, xmlWriter, font):
        for glyph, value in sorted(getattr(self, "mapping", {}).items()):
            attrs = (
                ("glyph", glyph),
                ("outer", value >> 16),
                ("inner", value & 0xFFFF),
            )
            xmlWriter.simpletag("Map", attrs)
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = {}
            self.mapping = mapping
        try:
            glyph = attrs["glyph"]
        except:  # https://github.com/fonttools/fonttools/commit/21cbab8ce9ded3356fef3745122da64dcaf314e9#commitcomment-27649836
            glyph = font.getGlyphOrder()[attrs["index"]]
        outer = safeEval(attrs["outer"])
        inner = safeEval(attrs["inner"])
        assert inner <= 0xFFFF
        mapping[glyph] = (outer << 16) | inner

    def __getitem__(self, glyphName):
        return self.mapping.get(glyphName, NO_VARIATION_INDEX)


class VarRegionList(BaseTable):
    def preWrite(self, font):
        # The OT spec says VarStore.VarRegionList.RegionAxisCount should always
        # be equal to the fvar.axisCount, and OTS < v8.0.0 enforces this rule
        # even when the VarRegionList is empty. We can't treat RegionAxisCount
        # like a normal propagated count (== len(Region[i].VarRegionAxis)),
        # otherwise it would default to 0 if VarRegionList is empty.
        # Thus, we force it to always be equal to fvar.axisCount.
        # https://github.com/khaledhosny/ots/pull/192
        fvarTable = font.get("fvar")
        if fvarTable:
            self.RegionAxisCount = len(fvarTable.axes)
        return {
            **self.__dict__,
            "RegionAxisCount": CountReference(self.__dict__, "RegionAxisCount"),
        }


class SingleSubst(FormatSwitchingBaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "mapping"):
            self.mapping = {}

    def postRead(self, rawTable, font):
        mapping = {}
        input = _getGlyphsFromCoverageTable(rawTable["Coverage"])
        if self.Format == 1:
            delta = rawTable["DeltaGlyphID"]
            inputGIDS = font.getGlyphIDMany(input)
            outGIDS = [(glyphID + delta) % 65536 for glyphID in inputGIDS]
            outNames = font.getGlyphNameMany(outGIDS)
            for inp, out in zip(input, outNames):
                mapping[inp] = out
        elif self.Format == 2:
            assert (
                len(input) == rawTable["GlyphCount"]
            ), "invalid SingleSubstFormat2 table"
            subst = rawTable["Substitute"]
            for inp, sub in zip(input, subst):
                mapping[inp] = sub
        else:
            assert 0, "unknown format: %s" % self.Format
        self.mapping = mapping
        del self.Format  # Don't need this anymore

    def preWrite(self, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = self.mapping = {}
        items = list(mapping.items())
        getGlyphID = font.getGlyphID
        gidItems = [(getGlyphID(a), getGlyphID(b)) for a, b in items]
        sortableItems = sorted(zip(gidItems, items))

        # figure out format
        format = 2
        delta = None
        for inID, outID in gidItems:
            if delta is None:
                delta = (outID - inID) % 65536

            if (inID + delta) % 65536 != outID:
                break
        else:
            if delta is None:
                # the mapping is empty, better use format 2
                format = 2
            else:
                format = 1

        rawTable = {}
        self.Format = format
        cov = Coverage()
        input = [item[1][0] for item in sortableItems]
        subst = [item[1][1] for item in sortableItems]
        cov.glyphs = input
        rawTable["Coverage"] = cov
        if format == 1:
            assert delta is not None
            rawTable["DeltaGlyphID"] = delta
        else:
            rawTable["Substitute"] = subst
        return rawTable

    def toXML2(self, xmlWriter, font):
        items = sorted(self.mapping.items())
        for inGlyph, outGlyph in items:
            xmlWriter.simpletag("Substitution", [("in", inGlyph), ("out", outGlyph)])
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = {}
            self.mapping = mapping
        mapping[attrs["in"]] = attrs["out"]


class MultipleSubst(FormatSwitchingBaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "mapping"):
            self.mapping = {}

    def postRead(self, rawTable, font):
        mapping = {}
        if self.Format == 1:
            glyphs = _getGlyphsFromCoverageTable(rawTable["Coverage"])
            subst = [s.Substitute for s in rawTable["Sequence"]]
            mapping = dict(zip(glyphs, subst))
        else:
            assert 0, "unknown format: %s" % self.Format
        self.mapping = mapping
        del self.Format  # Don't need this anymore

    def preWrite(self, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = self.mapping = {}
        cov = Coverage()
        cov.glyphs = sorted(list(mapping.keys()), key=font.getGlyphID)
        self.Format = 1
        rawTable = {
            "Coverage": cov,
            "Sequence": [self.makeSequence_(mapping[glyph]) for glyph in cov.glyphs],
        }
        return rawTable

    def toXML2(self, xmlWriter, font):
        items = sorted(self.mapping.items())
        for inGlyph, outGlyphs in items:
            out = ",".join(outGlyphs)
            xmlWriter.simpletag("Substitution", [("in", inGlyph), ("out", out)])
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        mapping = getattr(self, "mapping", None)
        if mapping is None:
            mapping = {}
            self.mapping = mapping

        # TTX v3.0 and earlier.
        if name == "Coverage":
            self.old_coverage_ = []
            for element in content:
                if not isinstance(element, tuple):
                    continue
                element_name, element_attrs, _ = element
                if element_name == "Glyph":
                    self.old_coverage_.append(element_attrs["value"])
            return
        if name == "Sequence":
            index = int(attrs.get("index", len(mapping)))
            glyph = self.old_coverage_[index]
            glyph_mapping = mapping[glyph] = []
            for element in content:
                if not isinstance(element, tuple):
                    continue
                element_name, element_attrs, _ = element
                if element_name == "Substitute":
                    glyph_mapping.append(element_attrs["value"])
            return

            # TTX v3.1 and later.
        outGlyphs = attrs["out"].split(",") if attrs["out"] else []
        mapping[attrs["in"]] = [g.strip() for g in outGlyphs]

    @staticmethod
    def makeSequence_(g):
        seq = Sequence()
        seq.Substitute = g
        return seq


class ClassDef(FormatSwitchingBaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "classDefs"):
            self.classDefs = {}

    def postRead(self, rawTable, font):
        classDefs = {}

        if self.Format == 1:
            start = rawTable["StartGlyph"]
            classList = rawTable["ClassValueArray"]
            startID = font.getGlyphID(start)
            endID = startID + len(classList)
            glyphNames = font.getGlyphNameMany(range(startID, endID))
            for glyphName, cls in zip(glyphNames, classList):
                if cls:
                    classDefs[glyphName] = cls

        elif self.Format == 2:
            records = rawTable["ClassRangeRecord"]
            for rec in records:
                cls = rec.Class
                if not cls:
                    continue
                start = rec.Start
                end = rec.End
                startID = font.getGlyphID(start)
                endID = font.getGlyphID(end) + 1
                glyphNames = font.getGlyphNameMany(range(startID, endID))
                for glyphName in glyphNames:
                    classDefs[glyphName] = cls
        else:
            log.warning("Unknown ClassDef format: %s", self.Format)
        self.classDefs = classDefs
        del self.Format  # Don't need this anymore

    def _getClassRanges(self, font):
        classDefs = getattr(self, "classDefs", None)
        if classDefs is None:
            self.classDefs = {}
            return
        getGlyphID = font.getGlyphID
        items = []
        for glyphName, cls in classDefs.items():
            if not cls:
                continue
            items.append((getGlyphID(glyphName), glyphName, cls))
        if items:
            items.sort()
            last, lastName, lastCls = items[0]
            ranges = [[lastCls, last, lastName]]
            for glyphID, glyphName, cls in items[1:]:
                if glyphID != last + 1 or cls != lastCls:
                    ranges[-1].extend([last, lastName])
                    ranges.append([cls, glyphID, glyphName])
                last = glyphID
                lastName = glyphName
                lastCls = cls
            ranges[-1].extend([last, lastName])
            return ranges

    def preWrite(self, font):
        format = 2
        rawTable = {"ClassRangeRecord": []}
        ranges = self._getClassRanges(font)
        if ranges:
            startGlyph = ranges[0][1]
            endGlyph = ranges[-1][3]
            glyphCount = endGlyph - startGlyph + 1
            if len(ranges) * 3 < glyphCount + 1:
                # Format 2 is more compact
                for i in range(len(ranges)):
                    cls, start, startName, end, endName = ranges[i]
                    rec = ClassRangeRecord()
                    rec.Start = startName
                    rec.End = endName
                    rec.Class = cls
                    ranges[i] = rec
                format = 2
                rawTable = {"ClassRangeRecord": ranges}
            else:
                # Format 1 is more compact
                startGlyphName = ranges[0][2]
                classes = [0] * glyphCount
                for cls, start, startName, end, endName in ranges:
                    for g in range(start - startGlyph, end - startGlyph + 1):
                        classes[g] = cls
                format = 1
                rawTable = {"StartGlyph": startGlyphName, "ClassValueArray": classes}
        self.Format = format
        return rawTable

    def toXML2(self, xmlWriter, font):
        items = sorted(self.classDefs.items())
        for glyphName, cls in items:
            xmlWriter.simpletag("ClassDef", [("glyph", glyphName), ("class", cls)])
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        classDefs = getattr(self, "classDefs", None)
        if classDefs is None:
            classDefs = {}
            self.classDefs = classDefs
        classDefs[attrs["glyph"]] = int(attrs["class"])


class AlternateSubst(FormatSwitchingBaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "alternates"):
            self.alternates = {}

    def postRead(self, rawTable, font):
        alternates = {}
        if self.Format == 1:
            input = _getGlyphsFromCoverageTable(rawTable["Coverage"])
            alts = rawTable["AlternateSet"]
            assert len(input) == len(alts)
            for inp, alt in zip(input, alts):
                alternates[inp] = alt.Alternate
        else:
            assert 0, "unknown format: %s" % self.Format
        self.alternates = alternates
        del self.Format  # Don't need this anymore

    def preWrite(self, font):
        self.Format = 1
        alternates = getattr(self, "alternates", None)
        if alternates is None:
            alternates = self.alternates = {}
        items = list(alternates.items())
        for i in range(len(items)):
            glyphName, set = items[i]
            items[i] = font.getGlyphID(glyphName), glyphName, set
        items.sort()
        cov = Coverage()
        cov.glyphs = [item[1] for item in items]
        alternates = []
        setList = [item[-1] for item in items]
        for set in setList:
            alts = AlternateSet()
            alts.Alternate = set
            alternates.append(alts)
        # a special case to deal with the fact that several hundred Adobe Japan1-5
        # CJK fonts will overflow an offset if the coverage table isn't pushed to the end.
        # Also useful in that when splitting a sub-table because of an offset overflow
        # I don't need to calculate the change in the subtable offset due to the change in the coverage table size.
        # Allows packing more rules in subtable.
        self.sortCoverageLast = 1
        return {"Coverage": cov, "AlternateSet": alternates}

    def toXML2(self, xmlWriter, font):
        items = sorted(self.alternates.items())
        for glyphName, alternates in items:
            xmlWriter.begintag("AlternateSet", glyph=glyphName)
            xmlWriter.newline()
            for alt in alternates:
                xmlWriter.simpletag("Alternate", glyph=alt)
                xmlWriter.newline()
            xmlWriter.endtag("AlternateSet")
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        alternates = getattr(self, "alternates", None)
        if alternates is None:
            alternates = {}
            self.alternates = alternates
        glyphName = attrs["glyph"]
        set = []
        alternates[glyphName] = set
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            set.append(attrs["glyph"])


class LigatureSubst(FormatSwitchingBaseTable):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "ligatures"):
            self.ligatures = {}

    def postRead(self, rawTable, font):
        ligatures = {}
        if self.Format == 1:
            input = _getGlyphsFromCoverageTable(rawTable["Coverage"])
            ligSets = rawTable["LigatureSet"]
            assert len(input) == len(ligSets)
            for i in range(len(input)):
                ligatures[input[i]] = ligSets[i].Ligature
        else:
            assert 0, "unknown format: %s" % self.Format
        self.ligatures = ligatures
        del self.Format  # Don't need this anymore

    @staticmethod
    def _getLigatureSortKey(components):
        # Computes a key for ordering ligatures in a GSUB Type-4 lookup.

        # When building the OpenType lookup, we need to make sure that
        # the longest sequence of components is listed first, so we
        # use the negative length as the key for sorting.
        # Note, we no longer need to worry about deterministic order because the
        # ligature mapping `dict` remembers the insertion order, and this in
        # turn depends on the order in which the ligatures are written in the FEA.
        # Since python sort algorithm is stable, the ligatures of equal length
        # will keep the relative order in which they appear in the feature file.
        # For example, given the following ligatures (all starting with 'f' and
        # thus belonging to the same LigatureSet):
        #
        #   feature liga {
        #     sub f i by f_i;
        #     sub f f f by f_f_f;
        #     sub f f by f_f;
        #     sub f f i by f_f_i;
        #   } liga;
        #
        # this should sort to: f_f_f, f_f_i, f_i, f_f
        # This is also what fea-rs does, see:
        # https://github.com/adobe-type-tools/afdko/issues/1727
        # https://github.com/fonttools/fonttools/issues/3428
        # https://github.com/googlefonts/fontc/pull/680
        return -len(components)

    def preWrite(self, font):
        self.Format = 1
        ligatures = getattr(self, "ligatures", None)
        if ligatures is None:
            ligatures = self.ligatures = {}

        if ligatures and isinstance(next(iter(ligatures)), tuple):
            # New high-level API in v3.1 and later.  Note that we just support compiling this
            # for now.  We don't load to this API, and don't do XML with it.

            # ligatures is map from components-sequence to lig-glyph
            newLigatures = dict()
            for comps in sorted(ligatures.keys(), key=self._getLigatureSortKey):
                ligature = Ligature()
                ligature.Component = comps[1:]
                ligature.CompCount = len(comps)
                ligature.LigGlyph = ligatures[comps]
                newLigatures.setdefault(comps[0], []).append(ligature)
            ligatures = newLigatures

        items = list(ligatures.items())
        for i in range(len(items)):
            glyphName, set = items[i]
            items[i] = font.getGlyphID(glyphName), glyphName, set
        items.sort()
        cov = Coverage()
        cov.glyphs = [item[1] for item in items]

        ligSets = []
        setList = [item[-1] for item in items]
        for set in setList:
            ligSet = LigatureSet()
            ligs = ligSet.Ligature = []
            for lig in set:
                ligs.append(lig)
            ligSets.append(ligSet)
        # Useful in that when splitting a sub-table because of an offset overflow
        # I don't need to calculate the change in subtabl offset due to the coverage table size.
        # Allows packing more rules in subtable.
        self.sortCoverageLast = 1
        return {"Coverage": cov, "LigatureSet": ligSets}

    def toXML2(self, xmlWriter, font):
        items = sorted(self.ligatures.items())
        for glyphName, ligSets in items:
            xmlWriter.begintag("LigatureSet", glyph=glyphName)
            xmlWriter.newline()
            for lig in ligSets:
                xmlWriter.simpletag(
                    "Ligature", glyph=lig.LigGlyph, components=",".join(lig.Component)
                )
                xmlWriter.newline()
            xmlWriter.endtag("LigatureSet")
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        ligatures = getattr(self, "ligatures", None)
        if ligatures is None:
            ligatures = {}
            self.ligatures = ligatures
        glyphName = attrs["glyph"]
        ligs = []
        ligatures[glyphName] = ligs
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            lig = Ligature()
            lig.LigGlyph = attrs["glyph"]
            components = attrs["components"]
            lig.Component = components.split(",") if components else []
            lig.CompCount = len(lig.Component)
            ligs.append(lig)


class COLR(BaseTable):
    def decompile(self, reader, font):
        # COLRv0 is exceptional in that LayerRecordCount appears *after* the
        # LayerRecordArray it counts, but the parser logic expects Count fields
        # to always precede the arrays. Here we work around this by parsing the
        # LayerRecordCount before the rest of the table, and storing it in
        # the reader's local state.
        subReader = reader.getSubReader(offset=0)
        for conv in self.getConverters():
            if conv.name != "LayerRecordCount":
                subReader.advance(conv.staticSize)
                continue
            reader[conv.name] = conv.read(subReader, font, tableDict={})
            break
        else:
            raise AssertionError("LayerRecordCount converter not found")
        return BaseTable.decompile(self, reader, font)

    def preWrite(self, font):
        # The writer similarly assumes Count values precede the things counted,
        # thus here we pre-initialize a CountReference; the actual count value
        # will be set to the lenght of the array by the time this is assembled.
        self.LayerRecordCount = None
        return {
            **self.__dict__,
            "LayerRecordCount": CountReference(self.__dict__, "LayerRecordCount"),
        }

    def computeClipBoxes(self, glyphSet: "_TTGlyphSet", quantization: int = 1):
        if self.Version == 0:
            return

        clips = {}
        for rec in self.BaseGlyphList.BaseGlyphPaintRecord:
            try:
                clipBox = rec.Paint.computeClipBox(self, glyphSet, quantization)
            except Exception as e:
                from fontTools.ttLib import TTLibError

                raise TTLibError(
                    f"Failed to compute COLR ClipBox for {rec.BaseGlyph!r}"
                ) from e

            if clipBox is not None:
                clips[rec.BaseGlyph] = clipBox

        hasClipList = hasattr(self, "ClipList") and self.ClipList is not None
        if not clips:
            if hasClipList:
                self.ClipList = None
        else:
            if not hasClipList:
                self.ClipList = ClipList()
                self.ClipList.Format = 1
            self.ClipList.clips = clips


class LookupList(BaseTable):
    @property
    def table(self):
        for l in self.Lookup:
            for st in l.SubTable:
                if type(st).__name__.endswith("Subst"):
                    return "GSUB"
                if type(st).__name__.endswith("Pos"):
                    return "GPOS"
        raise ValueError

    def toXML2(self, xmlWriter, font):
        if (
            not font
            or "Debg" not in font
            or LOOKUP_DEBUG_INFO_KEY not in font["Debg"].data
        ):
            return super().toXML2(xmlWriter, font)
        debugData = font["Debg"].data[LOOKUP_DEBUG_INFO_KEY][self.table]
        for conv in self.getConverters():
            if conv.repeat:
                value = getattr(self, conv.name, [])
                for lookupIndex, item in enumerate(value):
                    if str(lookupIndex) in debugData:
                        info = LookupDebugInfo(*debugData[str(lookupIndex)])
                        tag = info.location
                        if info.name:
                            tag = f"{info.name}: {tag}"
                        if info.feature:
                            script, language, feature = info.feature
                            tag = f"{tag} in {feature} ({script}/{language})"
                        xmlWriter.comment(tag)
                        xmlWriter.newline()

                    conv.xmlWrite(
                        xmlWriter, font, item, conv.name, [("index", lookupIndex)]
                    )
            else:
                if conv.aux and not eval(conv.aux, None, vars(self)):
                    continue
                value = getattr(
                    self, conv.name, None
                )  # TODO Handle defaults instead of defaulting to None!
                conv.xmlWrite(xmlWriter, font, value, conv.name, [])


class BaseGlyphRecordArray(BaseTable):
    def preWrite(self, font):
        self.BaseGlyphRecord = sorted(
            self.BaseGlyphRecord, key=lambda rec: font.getGlyphID(rec.BaseGlyph)
        )
        return self.__dict__.copy()


class BaseGlyphList(BaseTable):
    def preWrite(self, font):
        self.BaseGlyphPaintRecord = sorted(
            self.BaseGlyphPaintRecord, key=lambda rec: font.getGlyphID(rec.BaseGlyph)
        )
        return self.__dict__.copy()


class ClipBoxFormat(IntEnum):
    Static = 1
    Variable = 2

    def is_variable(self):
        return self is self.Variable

    def as_variable(self):
        return self.Variable


class ClipBox(getFormatSwitchingBaseTableClass("uint8")):
    formatEnum = ClipBoxFormat

    def as_tuple(self):
        return tuple(getattr(self, conv.name) for conv in self.getConverters())

    def __repr__(self):
        return f"{self.__class__.__name__}{self.as_tuple()}"


class ClipList(getFormatSwitchingBaseTableClass("uint8")):
    def populateDefaults(self, propagator=None):
        if not hasattr(self, "clips"):
            self.clips = {}

    def postRead(self, rawTable, font):
        clips = {}
        glyphOrder = font.getGlyphOrder()
        for i, rec in enumerate(rawTable["ClipRecord"]):
            if rec.StartGlyphID > rec.EndGlyphID:
                log.warning(
                    "invalid ClipRecord[%i].StartGlyphID (%i) > "
                    "EndGlyphID (%i); skipped",
                    i,
                    rec.StartGlyphID,
                    rec.EndGlyphID,
                )
                continue
            redefinedGlyphs = []
            missingGlyphs = []
            for glyphID in range(rec.StartGlyphID, rec.EndGlyphID + 1):
                try:
                    glyph = glyphOrder[glyphID]
                except IndexError:
                    missingGlyphs.append(glyphID)
                    continue
                if glyph not in clips:
                    clips[glyph] = copy.copy(rec.ClipBox)
                else:
                    redefinedGlyphs.append(glyphID)
            if redefinedGlyphs:
                log.warning(
                    "ClipRecord[%i] overlaps previous records; "
                    "ignoring redefined clip boxes for the "
                    "following glyph ID range: [%i-%i]",
                    i,
                    min(redefinedGlyphs),
                    max(redefinedGlyphs),
                )
            if missingGlyphs:
                log.warning(
                    "ClipRecord[%i] range references missing " "glyph IDs: [%i-%i]",
                    i,
                    min(missingGlyphs),
                    max(missingGlyphs),
                )
        self.clips = clips

    def groups(self):
        glyphsByClip = defaultdict(list)
        uniqueClips = {}
        for glyphName, clipBox in self.clips.items():
            key = clipBox.as_tuple()
            glyphsByClip[key].append(glyphName)
            if key not in uniqueClips:
                uniqueClips[key] = clipBox
        return {
            frozenset(glyphs): uniqueClips[key] for key, glyphs in glyphsByClip.items()
        }

    def preWrite(self, font):
        if not hasattr(self, "clips"):
            self.clips = {}
        clipBoxRanges = {}
        glyphMap = font.getReverseGlyphMap()
        for glyphs, clipBox in self.groups().items():
            glyphIDs = sorted(
                glyphMap[glyphName] for glyphName in glyphs if glyphName in glyphMap
            )
            if not glyphIDs:
                continue
            last = glyphIDs[0]
            ranges = [[last]]
            for glyphID in glyphIDs[1:]:
                if glyphID != last + 1:
                    ranges[-1].append(last)
                    ranges.append([glyphID])
                last = glyphID
            ranges[-1].append(last)
            for start, end in ranges:
                assert (start, end) not in clipBoxRanges
                clipBoxRanges[(start, end)] = clipBox

        clipRecords = []
        for (start, end), clipBox in sorted(clipBoxRanges.items()):
            record = ClipRecord()
            record.StartGlyphID = start
            record.EndGlyphID = end
            record.ClipBox = clipBox
            clipRecords.append(record)
        rawTable = {
            "ClipCount": len(clipRecords),
            "ClipRecord": clipRecords,
        }
        return rawTable

    def toXML(self, xmlWriter, font, attrs=None, name=None):
        tableName = name if name else self.__class__.__name__
        if attrs is None:
            attrs = []
        if hasattr(self, "Format"):
            attrs.append(("Format", self.Format))
        xmlWriter.begintag(tableName, attrs)
        xmlWriter.newline()
        # sort clips alphabetically to ensure deterministic XML dump
        for glyphs, clipBox in sorted(
            self.groups().items(), key=lambda item: min(item[0])
        ):
            xmlWriter.begintag("Clip")
            xmlWriter.newline()
            for glyphName in sorted(glyphs):
                xmlWriter.simpletag("Glyph", value=glyphName)
                xmlWriter.newline()
            xmlWriter.begintag("ClipBox", [("Format", clipBox.Format)])
            xmlWriter.newline()
            clipBox.toXML2(xmlWriter, font)
            xmlWriter.endtag("ClipBox")
            xmlWriter.newline()
            xmlWriter.endtag("Clip")
            xmlWriter.newline()
        xmlWriter.endtag(tableName)
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        clips = getattr(self, "clips", None)
        if clips is None:
            self.clips = clips = {}
        assert name == "Clip"
        glyphs = []
        clipBox = None
        for elem in content:
            if not isinstance(elem, tuple):
                continue
            name, attrs, content = elem
            if name == "Glyph":
                glyphs.append(attrs["value"])
            elif name == "ClipBox":
                clipBox = ClipBox()
                clipBox.Format = safeEval(attrs["Format"])
                for elem in content:
                    if not isinstance(elem, tuple):
                        continue
                    name, attrs, content = elem
                    clipBox.fromXML(name, attrs, content, font)
        if clipBox:
            for glyphName in glyphs:
                clips[glyphName] = clipBox


class ExtendMode(IntEnum):
    PAD = 0
    REPEAT = 1
    REFLECT = 2


# Porter-Duff modes for COLRv1 PaintComposite:
# https://github.com/googlefonts/colr-gradients-spec/tree/off_sub_1#compositemode-enumeration
class CompositeMode(IntEnum):
    CLEAR = 0
    SRC = 1
    DEST = 2
    SRC_OVER = 3
    DEST_OVER = 4
    SRC_IN = 5
    DEST_IN = 6
    SRC_OUT = 7
    DEST_OUT = 8
    SRC_ATOP = 9
    DEST_ATOP = 10
    XOR = 11
    PLUS = 12
    SCREEN = 13
    OVERLAY = 14
    DARKEN = 15
    LIGHTEN = 16
    COLOR_DODGE = 17
    COLOR_BURN = 18
    HARD_LIGHT = 19
    SOFT_LIGHT = 20
    DIFFERENCE = 21
    EXCLUSION = 22
    MULTIPLY = 23
    HSL_HUE = 24
    HSL_SATURATION = 25
    HSL_COLOR = 26
    HSL_LUMINOSITY = 27


class PaintFormat(IntEnum):
    PaintColrLayers = 1
    PaintSolid = 2
    PaintVarSolid = 3
    PaintLinearGradient = 4
    PaintVarLinearGradient = 5
    PaintRadialGradient = 6
    PaintVarRadialGradient = 7
    PaintSweepGradient = 8
    PaintVarSweepGradient = 9
    PaintGlyph = 10
    PaintColrGlyph = 11
    PaintTransform = 12
    PaintVarTransform = 13
    PaintTranslate = 14
    PaintVarTranslate = 15
    PaintScale = 16
    PaintVarScale = 17
    PaintScaleAroundCenter = 18
    PaintVarScaleAroundCenter = 19
    PaintScaleUniform = 20
    PaintVarScaleUniform = 21
    PaintScaleUniformAroundCenter = 22
    PaintVarScaleUniformAroundCenter = 23
    PaintRotate = 24
    PaintVarRotate = 25
    PaintRotateAroundCenter = 26
    PaintVarRotateAroundCenter = 27
    PaintSkew = 28
    PaintVarSkew = 29
    PaintSkewAroundCenter = 30
    PaintVarSkewAroundCenter = 31
    PaintComposite = 32

    def is_variable(self):
        return self.name.startswith("PaintVar")

    def as_variable(self):
        if self.is_variable():
            return self
        try:
            return PaintFormat.__members__[f"PaintVar{self.name[5:]}"]
        except KeyError:
            return None


class Paint(getFormatSwitchingBaseTableClass("uint8")):
    formatEnum = PaintFormat

    def getFormatName(self):
        try:
            return self.formatEnum(self.Format).name
        except ValueError:
            raise NotImplementedError(f"Unknown Paint format: {self.Format}")

    def toXML(self, xmlWriter, font, attrs=None, name=None):
        tableName = name if name else self.__class__.__name__
        if attrs is None:
            attrs = []
        attrs.append(("Format", self.Format))
        xmlWriter.begintag(tableName, attrs)
        xmlWriter.comment(self.getFormatName())
        xmlWriter.newline()
        self.toXML2(xmlWriter, font)
        xmlWriter.endtag(tableName)
        xmlWriter.newline()

    def iterPaintSubTables(self, colr: COLR) -> Iterator[BaseTable.SubTableEntry]:
        if self.Format == PaintFormat.PaintColrLayers:
            # https://github.com/fonttools/fonttools/issues/2438: don't die when no LayerList exists
            layers = []
            if colr.LayerList is not None:
                layers = colr.LayerList.Paint
            yield from (
                BaseTable.SubTableEntry(name="Layers", value=v, index=i)
                for i, v in enumerate(
                    layers[self.FirstLayerIndex : self.FirstLayerIndex + self.NumLayers]
                )
            )
            return

        if self.Format == PaintFormat.PaintColrGlyph:
            for record in colr.BaseGlyphList.BaseGlyphPaintRecord:
                if record.BaseGlyph == self.Glyph:
                    yield BaseTable.SubTableEntry(name="BaseGlyph", value=record.Paint)
                    return
            else:
                raise KeyError(f"{self.Glyph!r} not in colr.BaseGlyphList")

        for conv in self.getConverters():
            if conv.tableClass is not None and issubclass(conv.tableClass, type(self)):
                value = getattr(self, conv.name)
                yield BaseTable.SubTableEntry(name=conv.name, value=value)

    def getChildren(self, colr) -> List["Paint"]:
        # this is kept for backward compatibility (e.g. it's used by the subsetter)
        return [p.value for p in self.iterPaintSubTables(colr)]

    def traverse(self, colr: COLR, callback):
        """Depth-first traversal of graph rooted at self, callback on each node."""
        if not callable(callback):
            raise TypeError("callback must be callable")

        for path in dfs_base_table(
            self, iter_subtables_fn=lambda paint: paint.iterPaintSubTables(colr)
        ):
            paint = path[-1].value
            callback(paint)

    def getTransform(self) -> Transform:
        if self.Format == PaintFormat.PaintTransform:
            t = self.Transform
            return Transform(t.xx, t.yx, t.xy, t.yy, t.dx, t.dy)
        elif self.Format == PaintFormat.PaintTranslate:
            return Identity.translate(self.dx, self.dy)
        elif self.Format == PaintFormat.PaintScale:
            return Identity.scale(self.scaleX, self.scaleY)
        elif self.Format == PaintFormat.PaintScaleAroundCenter:
            return (
                Identity.translate(self.centerX, self.centerY)
                .scale(self.scaleX, self.scaleY)
                .translate(-self.centerX, -self.centerY)
            )
        elif self.Format == PaintFormat.PaintScaleUniform:
            return Identity.scale(self.scale)
        elif self.Format == PaintFormat.PaintScaleUniformAroundCenter:
            return (
                Identity.translate(self.centerX, self.centerY)
                .scale(self.scale)
                .translate(-self.centerX, -self.centerY)
            )
        elif self.Format == PaintFormat.PaintRotate:
            return Identity.rotate(radians(self.angle))
        elif self.Format == PaintFormat.PaintRotateAroundCenter:
            return (
                Identity.translate(self.centerX, self.centerY)
                .rotate(radians(self.angle))
                .translate(-self.centerX, -self.centerY)
            )
        elif self.Format == PaintFormat.PaintSkew:
            return Identity.skew(radians(-self.xSkewAngle), radians(self.ySkewAngle))
        elif self.Format == PaintFormat.PaintSkewAroundCenter:
            return (
                Identity.translate(self.centerX, self.centerY)
                .skew(radians(-self.xSkewAngle), radians(self.ySkewAngle))
                .translate(-self.centerX, -self.centerY)
            )
        if PaintFormat(self.Format).is_variable():
            raise NotImplementedError(f"Variable Paints not supported: {self.Format}")

        return Identity

    def computeClipBox(
        self, colr: COLR, glyphSet: "_TTGlyphSet", quantization: int = 1
    ) -> Optional[ClipBox]:
        pen = ControlBoundsPen(glyphSet)
        for path in dfs_base_table(
            self, iter_subtables_fn=lambda paint: paint.iterPaintSubTables(colr)
        ):
            paint = path[-1].value
            if paint.Format == PaintFormat.PaintGlyph:
                transformation = reduce(
                    Transform.transform,
                    (st.value.getTransform() for st in path),
                    Identity,
                )
                glyphSet[paint.Glyph].draw(TransformPen(pen, transformation))

        if pen.bounds is None:
            return None

        cb = ClipBox()
        cb.Format = int(ClipBoxFormat.Static)
        cb.xMin, cb.yMin, cb.xMax, cb.yMax = quantizeRect(pen.bounds, quantization)
        return cb


# For each subtable format there is a class. However, we don't really distinguish
# between "field name" and "format name": often these are the same. Yet there's
# a whole bunch of fields with different names. The following dict is a mapping
# from "format name" to "field name". _buildClasses() uses this to create a
# subclass for each alternate field name.
#
_equivalents = {
    "MarkArray": ("Mark1Array",),
    "LangSys": ("DefaultLangSys",),
    "Coverage": (
        "MarkCoverage",
        "BaseCoverage",
        "LigatureCoverage",
        "Mark1Coverage",
        "Mark2Coverage",
        "BacktrackCoverage",
        "InputCoverage",
        "LookAheadCoverage",
        "VertGlyphCoverage",
        "HorizGlyphCoverage",
        "TopAccentCoverage",
        "ExtendedShapeCoverage",
        "MathKernCoverage",
    ),
    "ClassDef": (
        "ClassDef1",
        "ClassDef2",
        "BacktrackClassDef",
        "InputClassDef",
        "LookAheadClassDef",
        "GlyphClassDef",
        "MarkAttachClassDef",
    ),
    "Anchor": (
        "EntryAnchor",
        "ExitAnchor",
        "BaseAnchor",
        "LigatureAnchor",
        "Mark2Anchor",
        "MarkAnchor",
    ),
    "Device": (
        "XPlaDevice",
        "YPlaDevice",
        "XAdvDevice",
        "YAdvDevice",
        "XDeviceTable",
        "YDeviceTable",
        "DeviceTable",
    ),
    "Axis": (
        "HorizAxis",
        "VertAxis",
    ),
    "MinMax": ("DefaultMinMax",),
    "BaseCoord": (
        "MinCoord",
        "MaxCoord",
    ),
    "JstfLangSys": ("DefJstfLangSys",),
    "JstfGSUBModList": (
        "ShrinkageEnableGSUB",
        "ShrinkageDisableGSUB",
        "ExtensionEnableGSUB",
        "ExtensionDisableGSUB",
    ),
    "JstfGPOSModList": (
        "ShrinkageEnableGPOS",
        "ShrinkageDisableGPOS",
        "ExtensionEnableGPOS",
        "ExtensionDisableGPOS",
    ),
    "JstfMax": (
        "ShrinkageJstfMax",
        "ExtensionJstfMax",
    ),
    "MathKern": (
        "TopRightMathKern",
        "TopLeftMathKern",
        "BottomRightMathKern",
        "BottomLeftMathKern",
    ),
    "MathGlyphConstruction": ("VertGlyphConstruction", "HorizGlyphConstruction"),
}

#
# OverFlow logic, to automatically create ExtensionLookups
# XXX This should probably move to otBase.py
#


def fixLookupOverFlows(ttf, overflowRecord):
    """Either the offset from the LookupList to a lookup overflowed, or
    an offset from a lookup to a subtable overflowed.

    The table layout is::

      GPSO/GUSB
              Script List
              Feature List
              LookUpList
                      Lookup[0] and contents
                              SubTable offset list
                                      SubTable[0] and contents
                                      ...
                                      SubTable[n] and contents
                      ...
                      Lookup[n] and contents
                              SubTable offset list
                                      SubTable[0] and contents
                                      ...
                                      SubTable[n] and contents

    If the offset to a lookup overflowed (SubTableIndex is None)
            we must promote the *previous* lookup to an Extension type.

    If the offset from a lookup to subtable overflowed, then we must promote it
            to an Extension Lookup type.
    """
    ok = 0
    lookupIndex = overflowRecord.LookupListIndex
    if overflowRecord.SubTableIndex is None:
        lookupIndex = lookupIndex - 1
    if lookupIndex < 0:
        return ok
    if overflowRecord.tableType == "GSUB":
        extType = 7
    elif overflowRecord.tableType == "GPOS":
        extType = 9

    lookups = ttf[overflowRecord.tableType].table.LookupList.Lookup
    lookup = lookups[lookupIndex]
    # If the previous lookup is an extType, look further back. Very unlikely, but possible.
    while lookup.SubTable[0].__class__.LookupType == extType:
        lookupIndex = lookupIndex - 1
        if lookupIndex < 0:
            return ok
        lookup = lookups[lookupIndex]

    for lookupIndex in range(lookupIndex, len(lookups)):
        lookup = lookups[lookupIndex]
        if lookup.LookupType != extType:
            lookup.LookupType = extType
            for si in range(len(lookup.SubTable)):
                subTable = lookup.SubTable[si]
                extSubTableClass = lookupTypes[overflowRecord.tableType][extType]
                extSubTable = extSubTableClass()
                extSubTable.Format = 1
                extSubTable.ExtSubTable = subTable
                lookup.SubTable[si] = extSubTable
    ok = 1
    return ok


def splitMultipleSubst(oldSubTable, newSubTable, overflowRecord):
    ok = 1
    oldMapping = sorted(oldSubTable.mapping.items())
    oldLen = len(oldMapping)

    if overflowRecord.itemName in ["Coverage", "RangeRecord"]:
        # Coverage table is written last. Overflow is to or within the
        # the coverage table. We will just cut the subtable in half.
        newLen = oldLen // 2

    elif overflowRecord.itemName == "Sequence":
        # We just need to back up by two items from the overflowed
        # Sequence index to make sure the offset to the Coverage table
        # doesn't overflow.
        newLen = overflowRecord.itemIndex - 1

    newSubTable.mapping = {}
    for i in range(newLen, oldLen):
        item = oldMapping[i]
        key = item[0]
        newSubTable.mapping[key] = item[1]
        del oldSubTable.mapping[key]

    return ok


def splitAlternateSubst(oldSubTable, newSubTable, overflowRecord):
    ok = 1
    if hasattr(oldSubTable, "sortCoverageLast"):
        newSubTable.sortCoverageLast = oldSubTable.sortCoverageLast

    oldAlts = sorted(oldSubTable.alternates.items())
    oldLen = len(oldAlts)

    if overflowRecord.itemName in ["Coverage", "RangeRecord"]:
        # Coverage table is written last. overflow is to or within the
        # the coverage table. We will just cut the subtable in half.
        newLen = oldLen // 2

    elif overflowRecord.itemName == "AlternateSet":
        # We just need to back up by two items
        # from the overflowed AlternateSet index to make sure the offset
        # to the Coverage table doesn't overflow.
        newLen = overflowRecord.itemIndex - 1

    newSubTable.alternates = {}
    for i in range(newLen, oldLen):
        item = oldAlts[i]
        key = item[0]
        newSubTable.alternates[key] = item[1]
        del oldSubTable.alternates[key]

    return ok


def splitLigatureSubst(oldSubTable, newSubTable, overflowRecord):
    ok = 1
    oldLigs = sorted(oldSubTable.ligatures.items())
    oldLen = len(oldLigs)

    if overflowRecord.itemName in ["Coverage", "RangeRecord"]:
        # Coverage table is written last. overflow is to or within the
        # the coverage table. We will just cut the subtable in half.
        newLen = oldLen // 2

    elif overflowRecord.itemName == "LigatureSet":
        # We just need to back up by two items
        # from the overflowed AlternateSet index to make sure the offset
        # to the Coverage table doesn't overflow.
        newLen = overflowRecord.itemIndex - 1

    newSubTable.ligatures = {}
    for i in range(newLen, oldLen):
        item = oldLigs[i]
        key = item[0]
        newSubTable.ligatures[key] = item[1]
        del oldSubTable.ligatures[key]

    return ok


def splitPairPos(oldSubTable, newSubTable, overflowRecord):
    st = oldSubTable
    ok = False
    newSubTable.Format = oldSubTable.Format
    if oldSubTable.Format == 1 and len(oldSubTable.PairSet) > 1:
        for name in "ValueFormat1", "ValueFormat2":
            setattr(newSubTable, name, getattr(oldSubTable, name))

        # Move top half of coverage to new subtable

        newSubTable.Coverage = oldSubTable.Coverage.__class__()

        coverage = oldSubTable.Coverage.glyphs
        records = oldSubTable.PairSet

        oldCount = len(oldSubTable.PairSet) // 2

        oldSubTable.Coverage.glyphs = coverage[:oldCount]
        oldSubTable.PairSet = records[:oldCount]

        newSubTable.Coverage.glyphs = coverage[oldCount:]
        newSubTable.PairSet = records[oldCount:]

        oldSubTable.PairSetCount = len(oldSubTable.PairSet)
        newSubTable.PairSetCount = len(newSubTable.PairSet)

        ok = True

    elif oldSubTable.Format == 2 and len(oldSubTable.Class1Record) > 1:
        if not hasattr(oldSubTable, "Class2Count"):
            oldSubTable.Class2Count = len(oldSubTable.Class1Record[0].Class2Record)
        for name in "Class2Count", "ClassDef2", "ValueFormat1", "ValueFormat2":
            setattr(newSubTable, name, getattr(oldSubTable, name))

        # The two subtables will still have the same ClassDef2 and the table
        # sharing will still cause the sharing to overflow.  As such, disable
        # sharing on the one that is serialized second (that's oldSubTable).
        oldSubTable.DontShare = True

        # Move top half of class numbers to new subtable

        newSubTable.Coverage = oldSubTable.Coverage.__class__()
        newSubTable.ClassDef1 = oldSubTable.ClassDef1.__class__()

        coverage = oldSubTable.Coverage.glyphs
        classDefs = oldSubTable.ClassDef1.classDefs
        records = oldSubTable.Class1Record

        oldCount = len(oldSubTable.Class1Record) // 2
        newGlyphs = set(k for k, v in classDefs.items() if v >= oldCount)

        oldSubTable.Coverage.glyphs = [g for g in coverage if g not in newGlyphs]
        oldSubTable.ClassDef1.classDefs = {
            k: v for k, v in classDefs.items() if v < oldCount
        }
        oldSubTable.Class1Record = records[:oldCount]

        newSubTable.Coverage.glyphs = [g for g in coverage if g in newGlyphs]
        newSubTable.ClassDef1.classDefs = {
            k: (v - oldCount) for k, v in classDefs.items() if v > oldCount
        }
        newSubTable.Class1Record = records[oldCount:]

        oldSubTable.Class1Count = len(oldSubTable.Class1Record)
        newSubTable.Class1Count = len(newSubTable.Class1Record)

        ok = True

    return ok


def splitMarkBasePos(oldSubTable, newSubTable, overflowRecord):
    # split half of the mark classes to the new subtable
    classCount = oldSubTable.ClassCount
    if classCount < 2:
        # oh well, not much left to split...
        return False

    oldClassCount = classCount // 2
    newClassCount = classCount - oldClassCount

    oldMarkCoverage, oldMarkRecords = [], []
    newMarkCoverage, newMarkRecords = [], []
    for glyphName, markRecord in zip(
        oldSubTable.MarkCoverage.glyphs, oldSubTable.MarkArray.MarkRecord
    ):
        if markRecord.Class < oldClassCount:
            oldMarkCoverage.append(glyphName)
            oldMarkRecords.append(markRecord)
        else:
            markRecord.Class -= oldClassCount
            newMarkCoverage.append(glyphName)
            newMarkRecords.append(markRecord)

    oldBaseRecords, newBaseRecords = [], []
    for rec in oldSubTable.BaseArray.BaseRecord:
        oldBaseRecord, newBaseRecord = rec.__class__(), rec.__class__()
        oldBaseRecord.BaseAnchor = rec.BaseAnchor[:oldClassCount]
        newBaseRecord.BaseAnchor = rec.BaseAnchor[oldClassCount:]
        oldBaseRecords.append(oldBaseRecord)
        newBaseRecords.append(newBaseRecord)

    newSubTable.Format = oldSubTable.Format

    oldSubTable.MarkCoverage.glyphs = oldMarkCoverage
    newSubTable.MarkCoverage = oldSubTable.MarkCoverage.__class__()
    newSubTable.MarkCoverage.glyphs = newMarkCoverage

    # share the same BaseCoverage in both halves
    newSubTable.BaseCoverage = oldSubTable.BaseCoverage

    oldSubTable.ClassCount = oldClassCount
    newSubTable.ClassCount = newClassCount

    oldSubTable.MarkArray.MarkRecord = oldMarkRecords
    newSubTable.MarkArray = oldSubTable.MarkArray.__class__()
    newSubTable.MarkArray.MarkRecord = newMarkRecords

    oldSubTable.MarkArray.MarkCount = len(oldMarkRecords)
    newSubTable.MarkArray.MarkCount = len(newMarkRecords)

    oldSubTable.BaseArray.BaseRecord = oldBaseRecords
    newSubTable.BaseArray = oldSubTable.BaseArray.__class__()
    newSubTable.BaseArray.BaseRecord = newBaseRecords

    oldSubTable.BaseArray.BaseCount = len(oldBaseRecords)
    newSubTable.BaseArray.BaseCount = len(newBaseRecords)

    return True


splitTable = {
    "GSUB": {
        # 					1: splitSingleSubst,
        2: splitMultipleSubst,
        3: splitAlternateSubst,
        4: splitLigatureSubst,
        # 					5: splitContextSubst,
        # 					6: splitChainContextSubst,
        # 					7: splitExtensionSubst,
        # 					8: splitReverseChainSingleSubst,
    },
    "GPOS": {
        # 					1: splitSinglePos,
        2: splitPairPos,
        # 					3: splitCursivePos,
        4: splitMarkBasePos,
        # 					5: splitMarkLigPos,
        # 					6: splitMarkMarkPos,
        # 					7: splitContextPos,
        # 					8: splitChainContextPos,
        # 					9: splitExtensionPos,
    },
}


def fixSubTableOverFlows(ttf, overflowRecord):
    """
    An offset has overflowed within a sub-table. We need to divide this subtable into smaller parts.
    """
    table = ttf[overflowRecord.tableType].table
    lookup = table.LookupList.Lookup[overflowRecord.LookupListIndex]
    subIndex = overflowRecord.SubTableIndex
    subtable = lookup.SubTable[subIndex]

    # First, try not sharing anything for this subtable...
    if not hasattr(subtable, "DontShare"):
        subtable.DontShare = True
        return True

    if hasattr(subtable, "ExtSubTable"):
        # We split the subtable of the Extension table, and add a new Extension table
        # to contain the new subtable.

        subTableType = subtable.ExtSubTable.__class__.LookupType
        extSubTable = subtable
        subtable = extSubTable.ExtSubTable
        newExtSubTableClass = lookupTypes[overflowRecord.tableType][
            extSubTable.__class__.LookupType
        ]
        newExtSubTable = newExtSubTableClass()
        newExtSubTable.Format = extSubTable.Format
        toInsert = newExtSubTable

        newSubTableClass = lookupTypes[overflowRecord.tableType][subTableType]
        newSubTable = newSubTableClass()
        newExtSubTable.ExtSubTable = newSubTable
    else:
        subTableType = subtable.__class__.LookupType
        newSubTableClass = lookupTypes[overflowRecord.tableType][subTableType]
        newSubTable = newSubTableClass()
        toInsert = newSubTable

    if hasattr(lookup, "SubTableCount"):  # may not be defined yet.
        lookup.SubTableCount = lookup.SubTableCount + 1

    try:
        splitFunc = splitTable[overflowRecord.tableType][subTableType]
    except KeyError:
        log.error(
            "Don't know how to split %s lookup type %s",
            overflowRecord.tableType,
            subTableType,
        )
        return False

    ok = splitFunc(subtable, newSubTable, overflowRecord)
    if ok:
        lookup.SubTable.insert(subIndex + 1, toInsert)
    return ok


# End of OverFlow logic


def _buildClasses():
    import re
    from .otData import otData

    formatPat = re.compile(r"([A-Za-z0-9]+)Format(\d+)$")
    namespace = globals()

    # populate module with classes
    for name, table in otData:
        baseClass = BaseTable
        m = formatPat.match(name)
        if m:
            # XxxFormatN subtable, we only add the "base" table
            name = m.group(1)
            # the first row of a format-switching otData table describes the Format;
            # the first column defines the type of the Format field.
            # Currently this can be either 'uint16' or 'uint8'.
            formatType = table[0][0]
            baseClass = getFormatSwitchingBaseTableClass(formatType)
        if name not in namespace:
            # the class doesn't exist yet, so the base implementation is used.
            cls = type(name, (baseClass,), {})
            if name in ("GSUB", "GPOS"):
                cls.DontShare = True
            namespace[name] = cls

    # link Var{Table} <-> {Table} (e.g. ColorStop <-> VarColorStop, etc.)
    for name, _ in otData:
        if name.startswith("Var") and len(name) > 3 and name[3:] in namespace:
            varType = namespace[name]
            noVarType = namespace[name[3:]]
            varType.NoVarType = noVarType
            noVarType.VarType = varType

    for base, alts in _equivalents.items():
        base = namespace[base]
        for alt in alts:
            namespace[alt] = base

    global lookupTypes
    lookupTypes = {
        "GSUB": {
            1: SingleSubst,
            2: MultipleSubst,
            3: AlternateSubst,
            4: LigatureSubst,
            5: ContextSubst,
            6: ChainContextSubst,
            7: ExtensionSubst,
            8: ReverseChainSingleSubst,
        },
        "GPOS": {
            1: SinglePos,
            2: PairPos,
            3: CursivePos,
            4: MarkBasePos,
            5: MarkLigPos,
            6: MarkMarkPos,
            7: ContextPos,
            8: ChainContextPos,
            9: ExtensionPos,
        },
        "mort": {
            4: NoncontextualMorph,
        },
        "morx": {
            0: RearrangementMorph,
            1: ContextualMorph,
            2: LigatureMorph,
            # 3: Reserved,
            4: NoncontextualMorph,
            5: InsertionMorph,
        },
    }
    lookupTypes["JSTF"] = lookupTypes["GPOS"]  # JSTF contains GPOS
    for lookupEnum in lookupTypes.values():
        for enum, cls in lookupEnum.items():
            cls.LookupType = enum

    global featureParamTypes
    featureParamTypes = {
        "size": FeatureParamsSize,
    }
    for i in range(1, 20 + 1):
        featureParamTypes["ss%02d" % i] = FeatureParamsStylisticSet
    for i in range(1, 99 + 1):
        featureParamTypes["cv%02d" % i] = FeatureParamsCharacterVariants

    # add converters to classes
    from .otConverters import buildConverters

    for name, table in otData:
        m = formatPat.match(name)
        if m:
            # XxxFormatN subtable, add converter to "base" table
            name, format = m.groups()
            format = int(format)
            cls = namespace[name]
            if not hasattr(cls, "converters"):
                cls.converters = {}
                cls.convertersByName = {}
            converters, convertersByName = buildConverters(table[1:], namespace)
            cls.converters[format] = converters
            cls.convertersByName[format] = convertersByName
            # XXX Add staticSize?
        else:
            cls = namespace[name]
            cls.converters, cls.convertersByName = buildConverters(table, namespace)
            # XXX Add staticSize?


_buildClasses()


def _getGlyphsFromCoverageTable(coverage):
    if coverage is None:
        # empty coverage table
        return []
    else:
        return coverage.glyphs

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\team_endpoints.py ===
"""
TEAM MANAGEMENT

All /team management endpoints

/team/new
/team/info
/team/update
/team/delete
"""

import asyncio
import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import fastapi
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    BlockTeamRequest,
    CommonProxyErrors,
    DeleteTeamRequest,
    LiteLLM_AuditLogs,
    LiteLLM_ManagementEndpoint_MetadataFields_Premium,
    LiteLLM_ModelTable,
    LiteLLM_OrganizationTable,
    LiteLLM_TeamMembership,
    LiteLLM_TeamTable,
    LiteLLM_TeamTableCachedObj,
    LiteLLM_UserTable,
    LitellmTableNames,
    LitellmUserRoles,
    Member,
    NewTeamRequest,
    ProxyErrorTypes,
    ProxyException,
    SpecialManagementEndpointEnums,
    SpecialModelNames,
    SpecialProxyStrings,
    TeamAddMemberResponse,
    TeamInfoResponseObject,
    TeamInfoResponseObjectTeamTable,
    TeamListResponseObject,
    TeamMemberAddRequest,
    TeamMemberDeleteRequest,
    TeamMemberUpdateRequest,
    TeamMemberUpdateResponse,
    TeamModelAddRequest,
    TeamModelDeleteRequest,
    UpdateTeamRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.auth_checks import (
    allowed_route_check_inside_route,
    can_org_access_model,
    get_team_object,
    get_user_object,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.management_endpoints.common_utils import (
    _is_user_team_admin,
    _set_object_metadata_field,
    _upsert_budget_and_membership,
    _user_has_admin_view,
)
from litellm.proxy.management_endpoints.tag_management_endpoints import (
    get_daily_activity,
)
from litellm.proxy.management_helpers.object_permission_utils import (
    handle_update_object_permission_common,
)
from litellm.proxy.management_helpers.team_member_permission_checks import (
    TeamMemberPermissionChecks,
)
from litellm.proxy.management_helpers.utils import (
    add_new_member,
    management_endpoint_wrapper,
)
from litellm.proxy.utils import (
    PrismaClient,
    _premium_user_check,
    handle_exception_on_proxy,
)
from litellm.router import Router
from litellm.types.proxy.management_endpoints.common_daily_activity import (
    SpendAnalyticsPaginatedResponse,
)
from litellm.types.proxy.management_endpoints.team_endpoints import (
    GetTeamMemberPermissionsResponse,
    TeamListResponse,
    UpdateTeamMemberPermissionsRequest,
)

router = APIRouter()


def _is_available_team(team_id: str, user_api_key_dict: UserAPIKeyAuth) -> bool:
    if litellm.default_internal_user_params is None:
        return False
    if "available_teams" in litellm.default_internal_user_params:
        return team_id in litellm.default_internal_user_params["available_teams"]
    return False


async def get_all_team_memberships(
    prisma_client: PrismaClient, team_ids: List[str], user_id: Optional[str] = None
) -> List[LiteLLM_TeamMembership]:
    """Get all team memberships for a given user"""
    ## GET ALL MEMBERSHIPS ##
    where_obj: Dict[str, Dict[str, List[str]]] = {"team_id": {"in": team_ids}}
    if user_id is not None:
        where_obj["user_id"] = {"in": [user_id]}
    # if user_id is None:
    #     where_obj = {"team_id": {"in": team_id}}
    # else:
    #     where_obj = {"user_id": str(user_id), "team_id": {"in": team_id}}

    team_memberships = await prisma_client.db.litellm_teammembership.find_many(
        where=where_obj,
        include={"litellm_budget_table": True},
    )

    returned_tm: List[LiteLLM_TeamMembership] = []
    for tm in team_memberships:
        returned_tm.append(LiteLLM_TeamMembership(**tm.model_dump()))

    return returned_tm


async def _create_team_member_budget_table(
    data: Union[NewTeamRequest, LiteLLM_TeamTable],
    new_team_data_json: dict,
    user_api_key_dict: UserAPIKeyAuth,
    team_member_budget: float,
) -> dict:
    """Allows admin to create 1 budget, that applies to all team members"""
    from litellm.proxy._types import BudgetNewRequest
    from litellm.proxy.management_endpoints.budget_management_endpoints import (
        new_budget,
    )

    if data.team_alias is not None:
        budget_id = (
            f"team-{data.team_alias.replace(' ', '-')}-budget-{uuid.uuid4().hex}"
        )
    else:
        budget_id = f"team-budget-{uuid.uuid4().hex}"

    team_member_budget_table = await new_budget(
        budget_obj=BudgetNewRequest(
            max_budget=team_member_budget,
            budget_duration=data.budget_duration,
            budget_id=budget_id,
        ),
        user_api_key_dict=user_api_key_dict,
    )

    # Add team_member_budget_id as metadata field to team table
    if new_team_data_json.get("metadata") is None:
        new_team_data_json["metadata"] = {}
    new_team_data_json["metadata"][
        "team_member_budget_id"
    ] = team_member_budget_table.budget_id
    new_team_data_json.pop(
        "team_member_budget", None
    )  # remove team_member_budget from new_team_data_json

    return new_team_data_json


async def _upsert_team_member_budget_table(
    team_table: LiteLLM_TeamTable,
    user_api_key_dict: UserAPIKeyAuth,
    team_member_budget: float,
    updated_kv: dict,
) -> dict:
    """
    Add budget if none exists

    If budget exists, update it
    """
    from litellm.proxy._types import BudgetNewRequest
    from litellm.proxy.management_endpoints.budget_management_endpoints import (
        update_budget,
    )

    if team_table.metadata is None:
        team_table.metadata = {}

    team_member_budget_id = team_table.metadata.get("team_member_budget_id")
    if team_member_budget_id is not None and isinstance(team_member_budget_id, str):
        # Budget exists
        budget_row = await update_budget(
            budget_obj=BudgetNewRequest(
                budget_id=team_member_budget_id,
                max_budget=team_member_budget,
            ),
            user_api_key_dict=user_api_key_dict,
        )
        verbose_proxy_logger.info(
            f"Updated team member budget table: {budget_row.budget_id}, with team_member_budget={team_member_budget}"
        )
        if updated_kv.get("metadata") is None:
            updated_kv["metadata"] = {}
        updated_kv["metadata"]["team_member_budget_id"] = budget_row.budget_id
        updated_kv.pop("team_member_budget", None)
    else:  # budget does not exist
        updated_kv = await _create_team_member_budget_table(
            data=team_table,
            new_team_data_json=updated_kv,
            user_api_key_dict=user_api_key_dict,
            team_member_budget=team_member_budget,
        )
    return updated_kv


#### TEAM MANAGEMENT ####
@router.post(
    "/team/new",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=LiteLLM_TeamTable,
)
@management_endpoint_wrapper
async def new_team(  # noqa: PLR0915
    data: NewTeamRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Allow users to create a new team. Apply user permissions to their team.

    👉 [Detailed Doc on setting team budgets](https://docs.litellm.ai/docs/proxy/team_budgets)


    Parameters:
    - team_alias: Optional[str] - User defined team alias
    - team_id: Optional[str] - The team id of the user. If none passed, we'll generate it.
    - members_with_roles: List[{"role": "admin" or "user", "user_id": "<user-id>"}] - A list of users and their roles in the team. Get user_id when making a new user via `/user/new`.
    - team_member_permissions: Optional[List[str]] - A list of routes that non-admin team members can access. example: ["/key/generate", "/key/update", "/key/delete"]
    - metadata: Optional[dict] - Metadata for team, store information for team. Example metadata = {"extra_info": "some info"}
    - tpm_limit: Optional[int] - The TPM (Tokens Per Minute) limit for this team - all keys with this team_id will have at max this TPM limit
    - rpm_limit: Optional[int] - The RPM (Requests Per Minute) limit for this team - all keys associated with this team_id will have at max this RPM limit
    - max_budget: Optional[float] - The maximum budget allocated to the team - all keys for this team_id will have at max this max_budget
    - budget_duration: Optional[str] - The duration of the budget for the team. Doc [here](https://docs.litellm.ai/docs/proxy/team_budgets)
    - models: Optional[list] - A list of models associated with the team - all keys for this team_id will have at most, these models. If empty, assumes all models are allowed.
    - blocked: bool - Flag indicating if the team is blocked or not - will stop all calls from keys with this team_id.
    - members: Optional[List] - Control team members via `/team/member/add` and `/team/member/delete`.
    - tags: Optional[List[str]] - Tags for [tracking spend](https://litellm.vercel.app/docs/proxy/enterprise#tracking-spend-for-custom-tags) and/or doing [tag-based routing](https://litellm.vercel.app/docs/proxy/tag_routing).
    - organization_id: Optional[str] - The organization id of the team. Default is None. Create via `/organization/new`.
    - model_aliases: Optional[dict] - Model aliases for the team. [Docs](https://docs.litellm.ai/docs/proxy/team_based_routing#create-team-with-model-alias)
    - guardrails: Optional[List[str]] - Guardrails for the team. [Docs](https://docs.litellm.ai/docs/proxy/guardrails)
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - team-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    - team_member_budget: Optional[float] - The maximum budget allocated to an individual team member.
    
    Returns:
    - team_id: (str) Unique team id - used for tracking spend across multiple keys for same team id.

    _deprecated_params:
    - admins: list - A list of user_id's for the admin role
    - users: list - A list of user_id's for the user role

    Example Request:
    ```
    curl --location 'http://0.0.0.0:4000/team/new' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
      "team_alias": "my-new-team_2",
      "members_with_roles": [{"role": "admin", "user_id": "user-1234"},
        {"role": "user", "user_id": "user-2434"}]
    }'

    ```

     ```
    curl --location 'http://0.0.0.0:4000/team/new' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
                "team_alias": "QA Prod Bot",
                "max_budget": 0.000000001,
                "budget_duration": "1d"
            }'
    ```
    """
    try:
        from litellm.proxy.proxy_server import (
            _license_check,
            create_audit_log_for_update,
            litellm_proxy_admin_name,
            prisma_client,
        )

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})
        

        # Check if license is over limit
        total_teams = await prisma_client.db.litellm_teamtable.count()
        if total_teams and _license_check.is_team_count_over_limit(team_count=total_teams):
            raise HTTPException(
                status_code=403,
                detail="License is over limit. Please contact support@berri.ai to upgrade your license.",
            )

        if data.team_id is None:
            data.team_id = str(uuid.uuid4())
        else:
            # Check if team_id exists already
            _existing_team_id = await prisma_client.get_data(
                team_id=data.team_id, table_name="team", query_type="find_unique"
            )
            if _existing_team_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"Team id = {data.team_id} already exists. Please use a different team id."
                    },
                )

        if (
            user_api_key_dict.user_role is None
            or user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN
        ):  # don't restrict proxy admin
            if (
                data.tpm_limit is not None
                and user_api_key_dict.tpm_limit is not None
                and data.tpm_limit > user_api_key_dict.tpm_limit
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"tpm limit higher than user max. User tpm limit={user_api_key_dict.tpm_limit}. User role={user_api_key_dict.user_role}"
                    },
                )

            if (
                data.rpm_limit is not None
                and user_api_key_dict.rpm_limit is not None
                and data.rpm_limit > user_api_key_dict.rpm_limit
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"rpm limit higher than user max. User rpm limit={user_api_key_dict.rpm_limit}. User role={user_api_key_dict.user_role}"
                    },
                )

            if (
                data.max_budget is not None
                and user_api_key_dict.max_budget is not None
                and data.max_budget > user_api_key_dict.max_budget
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"max budget higher than user max. User max budget={user_api_key_dict.max_budget}. User role={user_api_key_dict.user_role}"
                    },
                )

            if data.models is not None and len(user_api_key_dict.models) > 0:
                for m in data.models:
                    if m not in user_api_key_dict.models:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": f"Model not in allowed user models. User allowed models={user_api_key_dict.models}. User id={user_api_key_dict.user_id}"
                            },
                        )

        if user_api_key_dict.user_id is not None:
            creating_user_in_list = False
            for member in data.members_with_roles:
                if member.user_id == user_api_key_dict.user_id:
                    creating_user_in_list = True

            if creating_user_in_list is False:
                data.members_with_roles.append(
                    Member(role="admin", user_id=user_api_key_dict.user_id)
                )

        ## ADD TO MODEL TABLE
        _model_id = None
        if data.model_aliases is not None and isinstance(data.model_aliases, dict):
            litellm_modeltable = LiteLLM_ModelTable(
                model_aliases=json.dumps(data.model_aliases),
                created_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
                updated_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
            )
            model_dict = await prisma_client.db.litellm_modeltable.create(
                {**litellm_modeltable.json(exclude_none=True)}  # type: ignore
            )  # type: ignore

            _model_id = model_dict.id

        ## Handle Object Permission - MCP, Vector Stores etc.
        object_permission_id = await _set_object_permission(
            data=data,
            prisma_client=prisma_client,
        )

        ## Create Team Member Budget Table
        data_json = data.json()
        if data.team_member_budget is not None:
            data_json = await _create_team_member_budget_table(
                data=data,
                new_team_data_json=data_json,
                user_api_key_dict=user_api_key_dict,
                team_member_budget=data.team_member_budget,
            )

        ## ADD TO TEAM TABLE
        complete_team_data = LiteLLM_TeamTable(
            **data_json,
            model_id=_model_id,
            object_permission_id=object_permission_id,
        )

        # Set Management Endpoint Metadata Fields
        for field in LiteLLM_ManagementEndpoint_MetadataFields_Premium:
            if getattr(data, field) is not None:
                _set_object_metadata_field(
                    object_data=complete_team_data,
                    field_name=field,
                    value=getattr(data, field),
                )

        # If budget_duration is set, set `budget_reset_at`
        if complete_team_data.budget_duration is not None:
            from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time

            complete_team_data.budget_reset_at = get_budget_reset_time(
                budget_duration=complete_team_data.budget_duration,
            )

        complete_team_data_dict = complete_team_data.model_dump(exclude_none=True)
        complete_team_data_dict = prisma_client.jsonify_team_object(
            db_data=complete_team_data_dict
        )
        team_row: LiteLLM_TeamTable = await prisma_client.db.litellm_teamtable.create(
            data=complete_team_data_dict,
            include={"litellm_model_table": True},  # type: ignore
        )

        ## ADD TEAM ID TO USER TABLE ##
        for user in complete_team_data.members_with_roles:
            ## add team id to user row ##
            await prisma_client.update_data(
                user_id=user.user_id,
                data={"user_id": user.user_id, "teams": [team_row.team_id]},
                update_key_values_custom_query={
                    "teams": {
                        "push ": [team_row.team_id],
                    }
                },
            )

        # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
        if litellm.store_audit_logs is True:
            _updated_values = complete_team_data.json(exclude_none=True)

            _updated_values = json.dumps(_updated_values, default=str)

            asyncio.create_task(
                create_audit_log_for_update(
                    request_data=LiteLLM_AuditLogs(
                        id=str(uuid.uuid4()),
                        updated_at=datetime.now(timezone.utc),
                        changed_by=litellm_changed_by
                        or user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                        changed_by_api_key=user_api_key_dict.api_key,
                        table_name=LitellmTableNames.TEAM_TABLE_NAME,
                        object_id=data.team_id,
                        action="created",
                        updated_values=_updated_values,
                        before_value=None,
                    )
                )
            )

        try:
            return team_row.model_dump()
        except Exception:
            return team_row.dict()
    except Exception as e:
        raise handle_exception_on_proxy(e)


async def _update_model_table(
    data: UpdateTeamRequest,
    model_id: Optional[str],
    prisma_client: PrismaClient,
    user_api_key_dict: UserAPIKeyAuth,
    litellm_proxy_admin_name: str,
) -> Optional[str]:
    """
    Upsert model table and return the model id
    """
    ## UPSERT MODEL TABLE
    _model_id = model_id
    if data.model_aliases is not None and isinstance(data.model_aliases, dict):
        litellm_modeltable = LiteLLM_ModelTable(
            model_aliases=json.dumps(data.model_aliases),
            created_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
            updated_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
        )
        if model_id is None:
            model_dict = await prisma_client.db.litellm_modeltable.create(
                data={**litellm_modeltable.json(exclude_none=True)}  # type: ignore
            )
        else:
            model_dict = await prisma_client.db.litellm_modeltable.upsert(
                where={"id": model_id},
                data={
                    "update": {**litellm_modeltable.json(exclude_none=True)},  # type: ignore
                    "create": {**litellm_modeltable.json(exclude_none=True)},  # type: ignore
                },
            )  # type: ignore

        _model_id = model_dict.id

    return _model_id


async def _set_object_permission(
    data: NewTeamRequest,
    prisma_client: Optional[PrismaClient],
) -> Optional[str]:
    """
    Creates the LiteLLM_ObjectPermissionTable record for the team.
    - Handles permissions for vector stores and mcp servers.

    Returns the object_permission_id if created, otherwise None.
    """
    if prisma_client is None:
        return None

    if data.object_permission is not None:
        created_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.create(
                data=data.object_permission.model_dump(exclude_none=True),
            )
        )
        del data.object_permission
        return created_object_permission.object_permission_id
    return None


def validate_team_org_change(
    team: LiteLLM_TeamTable, organization: LiteLLM_OrganizationTable, llm_router: Router
) -> bool:
    """
    Validate that a team can be moved to an organization.

    - The org must have access to the team's models
    - The team budget cannot be greater than the org max_budget
    - The team's user_id must be a member of the org
    - The team's tpm/rpm limit must be less than the org's tpm/rpm limit
    """

    # If the team's organization is the same as the new organization, return True
    # Since no changes are being made
    if team.organization_id == organization.organization_id:
        return True

    # Check if the org has access to the team's models
    if len(organization.models) > 0:
        if SpecialModelNames.all_proxy_models.value in organization.models:
            pass
        elif team.models is None or len(team.models) == 0:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Cannot move team to organization. Team has access to all proxy models, but the organization does not."
                },
            )
        else:
            for model in team.models:
                can_org_access_model(
                    model=model,
                    org_object=organization,
                    llm_router=llm_router,
                )

    # Check if the team's budget is less than the org's max_budget
    if (
        team.max_budget
        and organization.litellm_budget_table
        and organization.litellm_budget_table.max_budget
        and team.max_budget > organization.litellm_budget_table.max_budget
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"Cannot move team to organization. Team has max_budget {team.max_budget} that is greater than the organization's max_budget {organization.litellm_budget_table.max_budget}."
            },
        )

    # Check if the team's user_id is a member of the org
    team_members = [m.user_id for m in team.members_with_roles]
    org_members = [m.user_id for m in organization.users] if organization.users else []
    not_in_org = [
        m
        for m in team_members
        if m not in org_members and m != SpecialProxyStrings.default_user_id.value
    ]
    if len(not_in_org) > 0:
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"Cannot move team to organization. Team has user_id {not_in_org} that is not a member of the organization."
            },
        )

    # Check if the team's tpm/rpm limit is less than the org's tpm/rpm limit
    if (
        team.tpm_limit
        and organization.litellm_budget_table
        and organization.litellm_budget_table.tpm_limit
        and team.tpm_limit > organization.litellm_budget_table.tpm_limit
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"Cannot move team to organization. Team has tpm_limit {team.tpm_limit} that is greater than the organization's tpm_limit {organization.litellm_budget_table.tpm_limit}."
            },
        )
    if (
        team.rpm_limit
        and organization.litellm_budget_table
        and organization.litellm_budget_table.rpm_limit
        and team.rpm_limit > organization.litellm_budget_table.rpm_limit
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"Cannot move team to organization. Team has rpm_limit {team.rpm_limit} that is greater than the organization's rpm_limit {organization.litellm_budget_table.rpm_limit}."
            },
        )
    return True


@router.post(
    "/team/update", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def update_team(
    data: UpdateTeamRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Use `/team/member_add` AND `/team/member/delete` to add/remove new team members

    You can now update team budget / rate limits via /team/update

    Parameters:
    - team_id: str - The team id of the user. Required param.
    - team_alias: Optional[str] - User defined team alias
    - team_member_permissions: Optional[List[str]] - A list of routes that non-admin team members can access. example: ["/key/generate", "/key/update", "/key/delete"]
    - metadata: Optional[dict] - Metadata for team, store information for team. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
    - tpm_limit: Optional[int] - The TPM (Tokens Per Minute) limit for this team - all keys with this team_id will have at max this TPM limit
    - rpm_limit: Optional[int] - The RPM (Requests Per Minute) limit for this team - all keys associated with this team_id will have at max this RPM limit
    - max_budget: Optional[float] - The maximum budget allocated to the team - all keys for this team_id will have at max this max_budget
    - budget_duration: Optional[str] - The duration of the budget for the team. Doc [here](https://docs.litellm.ai/docs/proxy/team_budgets)
    - models: Optional[list] - A list of models associated with the team - all keys for this team_id will have at most, these models. If empty, assumes all models are allowed.
    - blocked: bool - Flag indicating if the team is blocked or not - will stop all calls from keys with this team_id.
    - tags: Optional[List[str]] - Tags for [tracking spend](https://litellm.vercel.app/docs/proxy/enterprise#tracking-spend-for-custom-tags) and/or doing [tag-based routing](https://litellm.vercel.app/docs/proxy/tag_routing).
    - organization_id: Optional[str] - The organization id of the team. Default is None. Create via `/organization/new`.
    - model_aliases: Optional[dict] - Model aliases for the team. [Docs](https://docs.litellm.ai/docs/proxy/team_based_routing#create-team-with-model-alias)
    - guardrails: Optional[List[str]] - Guardrails for the team. [Docs](https://docs.litellm.ai/docs/proxy/guardrails)
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - team-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    - team_member_budget: Optional[float] - The maximum budget allocated to an individual team member.
    Example - update team TPM Limit

    ```
    curl --location 'http://0.0.0.0:4000/team/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "team_id": "8d916b1c-510d-4894-a334-1c16a93344f5",
        "tpm_limit": 100
    }'
    ```

    Example - Update Team `max_budget` budget
    ```
    curl --location 'http://0.0.0.0:4000/team/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "team_id": "8d916b1c-510d-4894-a334-1c16a93344f5",
        "max_budget": 10
    }'
    ```
    """
    from litellm.proxy.auth.auth_checks import _cache_team_object
    from litellm.proxy.proxy_server import (
        create_audit_log_for_update,
        litellm_proxy_admin_name,
        llm_router,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if data.team_id is None:
        raise HTTPException(status_code=400, detail={"error": "No team id passed in"})
    verbose_proxy_logger.debug("/team/update - %s", data)

    existing_team_row = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": data.team_id}
    )

    if existing_team_row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found, passed team_id={data.team_id}"},
        )

    if (
        data.organization_id is not None and len(data.organization_id) > 0
    ):  # allow unsetting the organization_id
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        organization_row = await prisma_client.db.litellm_organizationtable.find_unique(
            where={"organization_id": data.organization_id},
            include={"litellm_budget_table": True, "users": True},
        )
        if organization_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Organization not found, passed organization_id={data.organization_id}"
                },
            )
        validate_team_org_change(
            team=LiteLLM_TeamTable(**existing_team_row.model_dump()),
            organization=LiteLLM_OrganizationTable(**organization_row.model_dump()),
            llm_router=llm_router,
        )
    elif data.organization_id is not None and len(data.organization_id) == 0:
        # unsetting the organization_id
        data.organization_id = None

    updated_kv = data.json(exclude_unset=True)

    # Check budget_duration and budget_reset_at
    if data.budget_duration is not None:
        from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time

        reset_at = get_budget_reset_time(budget_duration=data.budget_duration)

        # set the budget_reset_at in DB
        updated_kv["budget_reset_at"] = reset_at

    if data.team_member_budget is not None:
        updated_kv = await _upsert_team_member_budget_table(
            team_table=existing_team_row,
            updated_kv=updated_kv,
            team_member_budget=data.team_member_budget,
            user_api_key_dict=user_api_key_dict,
        )

    # Check object permission
    if data.object_permission is not None:
        updated_kv = await handle_update_object_permission(
            data_json=updated_kv,
            existing_team_row=existing_team_row,
        )

    # update team metadata fields
    _team_metadata_fields = LiteLLM_ManagementEndpoint_MetadataFields_Premium
    for field in _team_metadata_fields:
        if field in updated_kv and updated_kv[field] is not None:
            _update_team_metadata_field(
                updated_kv=updated_kv,
                field_name=field,
            )

    if "model_aliases" in updated_kv:
        updated_kv.pop("model_aliases")
        _model_id = await _update_model_table(
            data=data,
            model_id=existing_team_row.model_id,
            prisma_client=prisma_client,
            user_api_key_dict=user_api_key_dict,
            litellm_proxy_admin_name=litellm_proxy_admin_name,
        )
        if _model_id is not None:
            updated_kv["model_id"] = _model_id

    updated_kv = prisma_client.jsonify_team_object(db_data=updated_kv)
    team_row: Optional[LiteLLM_TeamTable] = (
        await prisma_client.db.litellm_teamtable.update(
            where={"team_id": data.team_id},
            data=updated_kv,
            include={"litellm_model_table": True},  # type: ignore
        )
    )

    if team_row is None or team_row.team_id is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Team doesn't exist. Got={}".format(team_row)},
        )

    verbose_proxy_logger.info("Successfully updated team - %s, info", team_row.team_id)
    await _cache_team_object(
        team_id=team_row.team_id,
        team_table=LiteLLM_TeamTableCachedObj(**team_row.model_dump()),
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )

    # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
    if litellm.store_audit_logs is True:
        _before_value = existing_team_row.json(exclude_none=True)
        _before_value = json.dumps(_before_value, default=str)
        _after_value: str = json.dumps(updated_kv, default=str)

        asyncio.create_task(
            create_audit_log_for_update(
                request_data=LiteLLM_AuditLogs(
                    id=str(uuid.uuid4()),
                    updated_at=datetime.now(timezone.utc),
                    changed_by=litellm_changed_by
                    or user_api_key_dict.user_id
                    or litellm_proxy_admin_name,
                    changed_by_api_key=user_api_key_dict.api_key,
                    table_name=LitellmTableNames.TEAM_TABLE_NAME,
                    object_id=data.team_id,
                    action="updated",
                    updated_values=_after_value,
                    before_value=_before_value,
                )
            )
        )

    return {"team_id": team_row.team_id, "data": team_row}


async def handle_update_object_permission(
    data_json: dict, existing_team_row: LiteLLM_TeamTable
) -> dict:
    """
    Handle the update of object permission for a team.

    - IF there's no object_permission_id, then create a new entry in LiteLLM_ObjectPermissionTable
    - IF there's an object_permission_id, then update the entry in LiteLLM_ObjectPermissionTable
    """
    from litellm.proxy.proxy_server import prisma_client

    # Use the common helper to handle the object permission update
    object_permission_id = await handle_update_object_permission_common(
        data_json=data_json,
        existing_object_permission_id=existing_team_row.object_permission_id,
        prisma_client=prisma_client,
    )

    # Add the object_permission_id to data_json if one was created/updated
    if object_permission_id is not None:
        data_json["object_permission_id"] = object_permission_id
        verbose_proxy_logger.debug(
            f"updated object_permission_id: {object_permission_id}"
        )

    return data_json


def _check_team_member_admin_add(
    member: Union[Member, List[Member]],
    premium_user: bool,
):
    if isinstance(member, Member) and member.role == "admin":
        if premium_user is not True:
            raise ValueError(
                f"Assigning team admins is a premium feature. {CommonProxyErrors.not_premium_user.value}"
            )
    elif isinstance(member, List):
        for m in member:
            if m.role == "admin":
                if premium_user is not True:
                    raise ValueError(
                        f"Assigning team admins is a premium feature. Got={m}. {CommonProxyErrors.not_premium_user.value}. "
                    )


def team_call_validation_checks(
    prisma_client: Optional[PrismaClient],
    data: TeamMemberAddRequest,
    premium_user: bool,
):
    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.team_id is None:
        raise HTTPException(status_code=400, detail={"error": "No team id passed in"})

    if data.member is None:
        raise HTTPException(
            status_code=400, detail={"error": "No member/members passed in"}
        )

    try:
        _check_team_member_admin_add(
            member=data.member,
            premium_user=premium_user,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


def team_member_add_duplication_check(
    data: TeamMemberAddRequest,
    existing_team_row: LiteLLM_TeamTable,
):
    def _check_member_duplication(member: Member):
        if member.user_id in [m.user_id for m in existing_team_row.members_with_roles]:
            raise ProxyException(
                message=f"User={member.user_id} already in team. Existing members={existing_team_row.members_with_roles}",
                type=ProxyErrorTypes.team_member_already_in_team,
                param="user_id",
                code="400",
            )

    if isinstance(data.member, Member):
        _check_member_duplication(data.member)
    elif isinstance(data.member, List):
        for m in data.member:
            _check_member_duplication(m)


@router.post(
    "/team/member_add",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=TeamAddMemberResponse,
)
@management_endpoint_wrapper
async def team_member_add(
    data: TeamMemberAddRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Add new members (either via user_email or user_id) to a team

    If user doesn't exist, new user row will also be added to User Table

    Only proxy_admin or admin of team, allowed to access this endpoint.
    ```

    curl -X POST 'http://0.0.0.0:4000/team/member_add' \
    -H 'Authorization: Bearer sk-1234' \
    -H 'Content-Type: application/json' \
    -d '{"team_id": "45e3e396-ee08-4a61-a88e-16b3ce7e0849", "member": {"role": "user", "user_id": "krrish247652@berri.ai"}}'

    ```
    """
    from litellm.proxy.proxy_server import (
        litellm_proxy_admin_name,
        premium_user,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    try:
        team_call_validation_checks(
            prisma_client=prisma_client,
            data=data,
            premium_user=premium_user,
        )
    except HTTPException as e:
        raise e

    prisma_client = cast(PrismaClient, prisma_client)

    existing_team_row = await get_team_object(
        team_id=data.team_id,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        parent_otel_span=None,
        proxy_logging_obj=proxy_logging_obj,
        check_cache_only=False,
        check_db_only=True,
    )
    if existing_team_row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Team not found for team_id={getattr(data, 'team_id', None)}"
            },
        )

    complete_team_data = LiteLLM_TeamTable(**existing_team_row.model_dump())

    team_member_add_duplication_check(
        data=data,
        existing_team_row=complete_team_data,
    )

    ## CHECK IF USER IS PROXY ADMIN OR TEAM ADMIN

    if (
        hasattr(user_api_key_dict, "user_role")
        and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=complete_team_data
        )
        and not _is_available_team(
            team_id=complete_team_data.team_id,
            user_api_key_dict=user_api_key_dict,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Call not allowed. User not proxy admin OR team admin. route={}, team_id={}".format(
                    "/team/member_add",
                    complete_team_data.team_id,
                )
            },
        )

    updated_users: List[LiteLLM_UserTable] = []
    updated_team_memberships: List[LiteLLM_TeamMembership] = []

    ## VALIDATE IF NEW MEMBER ##
    if isinstance(data.member, Member):
        try:
            updated_user, updated_tm = await add_new_member(
                new_member=data.member,
                max_budget_in_team=data.max_budget_in_team,
                prisma_client=prisma_client,
                user_api_key_dict=user_api_key_dict,
                litellm_proxy_admin_name=litellm_proxy_admin_name,
                team_id=data.team_id,
                default_team_budget_id=(
                    complete_team_data.metadata.get("team_member_budget_id")
                    if complete_team_data.metadata is not None
                    else None
                ),
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Unable to add user - {}, to team - {}, for reason - {}".format(
                        data.member, data.team_id, str(e)
                    )
                },
            )

        updated_users.append(updated_user)
        if updated_tm is not None:
            updated_team_memberships.append(updated_tm)
    elif isinstance(data.member, List):
        tasks: List = []
        for m in data.member:
            try:
                updated_user, updated_tm = await add_new_member(
                    new_member=m,
                    max_budget_in_team=data.max_budget_in_team,
                    prisma_client=prisma_client,
                    user_api_key_dict=user_api_key_dict,
                    litellm_proxy_admin_name=litellm_proxy_admin_name,
                    team_id=data.team_id,
                    default_team_budget_id=(
                        complete_team_data.metadata.get("team_member_budget_id")
                        if complete_team_data.metadata is not None
                        else None
                    ),
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Unable to add user - {}, to team - {}, for reason - {}".format(
                            data.member, data.team_id, str(e)
                        )
                    },
                )
            updated_users.append(updated_user)
            if updated_tm is not None:
                updated_team_memberships.append(updated_tm)

        await asyncio.gather(*tasks)

    ## ADD TO TEAM ##
    if isinstance(data.member, Member):
        # add to team db
        new_member = data.member

        # get user id
        if new_member.user_id is None and new_member.user_email is not None:
            for user in updated_users:
                if (
                    user.user_email is not None
                    and user.user_email == new_member.user_email
                ):
                    new_member.user_id = user.user_id

        complete_team_data.members_with_roles.append(new_member)

    elif isinstance(data.member, List):
        # add to team db
        new_members = data.member

        for nm in new_members:
            if nm.user_id is None and nm.user_email is not None:
                for user in updated_users:
                    if user.user_email is not None and user.user_email == nm.user_email:
                        nm.user_id = user.user_id

        complete_team_data.members_with_roles.extend(new_members)

    # ADD MEMBER TO TEAM
    _db_team_members = [m.model_dump() for m in complete_team_data.members_with_roles]
    updated_team = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id},
        data={"members_with_roles": json.dumps(_db_team_members)},  # type: ignore
    )

    # Check if updated_team is None
    if updated_team is None:
        raise HTTPException(
            status_code=404, detail={"error": f"Team with id {data.team_id} not found"}
        )
    return TeamAddMemberResponse(
        **updated_team.model_dump(),
        updated_users=updated_users,
        updated_team_memberships=updated_team_memberships,
    )


@router.post(
    "/team/member_delete",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def team_member_delete(
    data: TeamMemberDeleteRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA]

    delete members (either via user_email or user_id) from a team

    If user doesn't exist, an exception will be raised
    ```
    curl -X POST 'http://0.0.0.0:8000/team/member_delete' \

    -H 'Authorization: Bearer sk-1234' \

    -H 'Content-Type: application/json' \

    -d '{
        "team_id": "45e3e396-ee08-4a61-a88e-16b3ce7e0849",
        "user_id": "krrish247652@berri.ai"
    }'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.team_id is None:
        raise HTTPException(status_code=400, detail={"error": "No team id passed in"})

    if data.user_id is None and data.user_email is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Either user_id or user_email needs to be passed in"},
        )

    _existing_team_row = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": data.team_id}
    )

    if _existing_team_row is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Team id={} does not exist in db".format(data.team_id)},
        )
    existing_team_row = LiteLLM_TeamTable(**_existing_team_row.model_dump())

    ## CHECK IF USER IS PROXY ADMIN OR TEAM ADMIN

    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=existing_team_row
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Call not allowed. User not proxy admin OR team admin. route={}, team_id={}".format(
                    "/team/member_delete", existing_team_row.team_id
                )
            },
        )

    ## DELETE MEMBER FROM TEAM
    is_member_in_team = False
    new_team_members: List[Member] = []
    for m in existing_team_row.members_with_roles:
        if (
            data.user_id is not None
            and m.user_id is not None
            and data.user_id == m.user_id
        ):
            is_member_in_team = True
            continue
        elif (
            data.user_email is not None
            and m.user_email is not None
            and data.user_email == m.user_email
        ):
            is_member_in_team = True
            continue
        new_team_members.append(m)

    if not is_member_in_team:
        raise HTTPException(status_code=400, detail={"error": "User not found in team"})

    existing_team_row.members_with_roles = new_team_members

    _db_new_team_members: List[dict] = [m.model_dump() for m in new_team_members]

    _ = await prisma_client.db.litellm_teamtable.update(
        where={
            "team_id": data.team_id,
        },
        data={"members_with_roles": json.dumps(_db_new_team_members)},  # type: ignore
    )

    ## DELETE TEAM ID from USER ROW, IF EXISTS ##
    # get user row
    key_val = {}
    if data.user_id is not None:
        key_val["user_id"] = data.user_id
    elif data.user_email is not None:
        key_val["user_email"] = data.user_email
    existing_user_rows = await prisma_client.db.litellm_usertable.find_many(
        where=key_val  # type: ignore
    )

    if existing_user_rows is not None and (
        isinstance(existing_user_rows, list) and len(existing_user_rows) > 0
    ):
        for existing_user in existing_user_rows:
            team_list = []
            if data.team_id in existing_user.teams:
                team_list = existing_user.teams
                team_list.remove(data.team_id)
                await prisma_client.db.litellm_usertable.update(
                    where={
                        "user_id": existing_user.user_id,
                    },
                    data={"teams": {"set": team_list}},
                )

    return existing_team_row


@router.post(
    "/team/member_update",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=TeamMemberUpdateResponse,
)
@management_endpoint_wrapper
async def team_member_update(
    data: TeamMemberUpdateRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA]

    Update team member budgets and team member role
    """
    from litellm.proxy.proxy_server import premium_user, prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.team_id is None:
        raise HTTPException(status_code=400, detail={"error": "No team id passed in"})

    if data.role == "admin" and not premium_user:
        # exactly the same text your proxy throws for add:
        raise HTTPException(
            status_code=400,
            detail="Assigning team admins is a premium feature. You must be a LiteLLM Enterprise user to use this feature. If you have a license please set `LITELLM_LICENSE` in your env. Get a 7 day trial key here: https://www.litellm.ai/#trial. Pricing: https://www.litellm.ai/#pricing",
        )
    if data.user_id is None and data.user_email is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Either user_id or user_email needs to be passed in"},
        )

    _existing_team_row = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": data.team_id}
    )

    if _existing_team_row is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Team id={} does not exist in db".format(data.team_id)},
        )
    existing_team_row = LiteLLM_TeamTable(**_existing_team_row.model_dump())

    ## CHECK IF USER IS PROXY ADMIN OR TEAM ADMIN

    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=existing_team_row
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Call not allowed. User not proxy admin OR team admin. route={}, team_id={}".format(
                    "/team/member_delete", existing_team_row.team_id
                )
            },
        )

    returned_team_info: TeamInfoResponseObject = await team_info(
        http_request=http_request,
        team_id=data.team_id,
        user_api_key_dict=user_api_key_dict,
    )

    team_table = returned_team_info["team_info"]

    ## get user id
    received_user_id: Optional[str] = None
    if data.user_id is not None:
        received_user_id = data.user_id
    elif data.user_email is not None:
        for member in returned_team_info["team_info"].members_with_roles:
            if member.user_email is not None and member.user_email == data.user_email:
                received_user_id = member.user_id
                break

    if received_user_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "User id doesn't exist in team table. Data={}".format(data)
            },
        )
    ## find the relevant team membership
    identified_budget_id: Optional[str] = None
    for tm in returned_team_info["team_memberships"]:
        if tm.user_id == received_user_id:
            identified_budget_id = tm.budget_id
            break

    ### upsert new budget
    async with prisma_client.db.tx() as tx:
        await _upsert_budget_and_membership(
            tx=tx,
            team_id=data.team_id,
            user_id=received_user_id,
            max_budget=data.max_budget_in_team,
            existing_budget_id=identified_budget_id,
            user_api_key_dict=user_api_key_dict,
        )

    ### update team member role
    if data.role is not None:
        team_members: List[Member] = []
        for member in team_table.members_with_roles:
            if member.user_id == received_user_id:
                team_members.append(
                    Member(
                        user_id=member.user_id,
                        role=data.role,
                        user_email=data.user_email or member.user_email,
                    )
                )
            else:
                team_members.append(member)

        team_table.members_with_roles = team_members

        _db_team_members: List[dict] = [m.model_dump() for m in team_members]
        await prisma_client.db.litellm_teamtable.update(
            where={"team_id": data.team_id},
            data={"members_with_roles": json.dumps(_db_team_members)},  # type: ignore
        )

    return TeamMemberUpdateResponse(
        team_id=data.team_id,
        user_id=received_user_id,
        user_email=data.user_email,
        max_budget_in_team=data.max_budget_in_team,
    )


@router.post(
    "/team/delete", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def delete_team(
    data: DeleteTeamRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    delete team and associated team keys

    Parameters:
    - team_ids: List[str] - Required. List of team IDs to delete. Example: ["team-1234", "team-5678"]

    ```
    curl --location 'http://0.0.0.0:4000/team/delete' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "team_ids": ["8d916b1c-510d-4894-a334-1c16a93344f5"]
    }'
    ```
    """
    from litellm.proxy.proxy_server import (
        create_audit_log_for_update,
        litellm_proxy_admin_name,
        prisma_client,
    )

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.team_ids is None:
        raise HTTPException(status_code=400, detail={"error": "No team id passed in"})

    # check that all teams passed exist
    team_rows: List[LiteLLM_TeamTable] = []
    for team_id in data.team_ids:
        try:
            team_row_base: Optional[BaseModel] = (
                await prisma_client.db.litellm_teamtable.find_unique(
                    where={"team_id": team_id}
                )
            )
            if team_row_base is None:
                raise Exception
        except Exception:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Team not found, passed team_id={team_id}"},
            )
        team_row_pydantic = LiteLLM_TeamTable(**team_row_base.model_dump())
        team_rows.append(team_row_pydantic)

    # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
    # we do this after the first for loop, since first for loop is for validation. we only want this inserted after validation passes
    if litellm.store_audit_logs is True:
        # make an audit log for each team deleted
        for team_id in data.team_ids:
            team_row: Optional[LiteLLM_TeamTable] = await prisma_client.get_data(  # type: ignore
                team_id=team_id, table_name="team", query_type="find_unique"
            )

            if team_row is None:
                continue

            _team_row = team_row.json(exclude_none=True)

            asyncio.create_task(
                create_audit_log_for_update(
                    request_data=LiteLLM_AuditLogs(
                        id=str(uuid.uuid4()),
                        updated_at=datetime.now(timezone.utc),
                        changed_by=litellm_changed_by
                        or user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                        changed_by_api_key=user_api_key_dict.api_key,
                        table_name=LitellmTableNames.TEAM_TABLE_NAME,
                        object_id=team_id,
                        action="deleted",
                        updated_values="{}",
                        before_value=_team_row,
                    )
                )
            )

    # End of Audit logging

    ## DELETE ASSOCIATED KEYS
    await prisma_client.delete_data(team_id_list=data.team_ids, table_name="key")

    # ## DELETE TEAM MEMBERSHIPS
    for team_row in team_rows:
        ### get all team members
        team_members = team_row.members_with_roles
        ### call team_member_delete for each team member
        tasks = []
        for team_member in team_members:
            tasks.append(
                team_member_delete(
                    data=TeamMemberDeleteRequest(
                        team_id=team_row.team_id,
                        user_id=team_member.user_id,
                        user_email=team_member.user_email,
                    ),
                    user_api_key_dict=user_api_key_dict,
                )
            )
        await asyncio.gather(*tasks)

    ## DELETE TEAMS
    deleted_teams = await prisma_client.delete_data(
        team_id_list=data.team_ids, table_name="team"
    )
    return deleted_teams


def validate_membership(
    user_api_key_dict: UserAPIKeyAuth, team_table: LiteLLM_TeamTable
):
    if (
        user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value
        or user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY.value
    ):
        return

    if (
        user_api_key_dict.team_id == team_table.team_id
    ):  # allow team keys to check their info
        return

    if user_api_key_dict.user_id not in [
        m.user_id for m in team_table.members_with_roles
    ]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "User={} not authorized to access this team={}".format(
                    user_api_key_dict.user_id, team_table.team_id
                )
            },
        )


def _unfurl_all_proxy_models(
    team_info: LiteLLM_TeamTable, llm_router: Router
) -> LiteLLM_TeamTable:
    if (
        SpecialModelNames.all_proxy_models.value in team_info.models
        and llm_router is not None
    ):
        team_models: set[str] = set()  # make set to avoid duplicates
        for model in team_info.models:
            if model != SpecialModelNames.all_proxy_models.value:
                team_models.add(model)
        for model in llm_router.get_model_names():
            team_models.add(model)
        team_info.models = list(team_models)
    return team_info


async def _add_team_member_budget_table(
    team_member_budget_id: str,
    prisma_client: PrismaClient,
    team_info_response_object: TeamInfoResponseObjectTeamTable,
) -> TeamInfoResponseObjectTeamTable:
    try:
        team_budget = await prisma_client.db.litellm_budgettable.find_unique(
            where={"budget_id": team_member_budget_id}
        )
        team_info_response_object.team_member_budget_table = team_budget
    except Exception:
        verbose_proxy_logger.info(
            f"Team member budget table not found, passed team_member_budget_id={team_member_budget_id}"
        )

    return team_info_response_object


@router.get(
    "/team/info", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def team_info(
    http_request: Request,
    team_id: str = fastapi.Query(
        default=None, description="Team ID in the request parameters"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    get info on team + related keys

    Parameters:
    - team_id: str - Required. The unique identifier of the team to get info on.

    ```
    curl --location 'http://localhost:4000/team/info?team_id=your_team_id_here' \
    --header 'Authorization: Bearer your_api_key_here'
    ```
    """
    from litellm.proxy._types import TeamInfoResponseObjectTeamTable
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
                },
            )
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Malformed request. No team id passed in."},
            )

        try:
            team_info: Optional[BaseModel] = (
                await prisma_client.db.litellm_teamtable.find_unique(
                    where={"team_id": team_id},
                    include={"object_permission": True},
                )
            )
            if team_info is None:
                raise Exception
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Team not found, passed team id: {team_id}."},
            )
        validate_membership(
            user_api_key_dict=user_api_key_dict,
            team_table=LiteLLM_TeamTable(**team_info.model_dump()),
        )

        ## GET ALL KEYS ##
        keys = await prisma_client.get_data(
            team_id=team_id,
            table_name="key",
            query_type="find_all",
            expires=datetime.now(),
        )

        if keys is None:
            keys = []

        if team_info is None:
            ## make sure we still return a total spend ##
            spend = 0
            for k in keys:
                spend += getattr(k, "spend", 0)
            team_info = {"spend": spend}

        ## REMOVE HASHED TOKEN INFO before returning ##
        for key in keys:
            try:
                key = key.model_dump()  # noqa
            except Exception:
                # if using pydantic v1
                key = key.dict()
            key.pop("token", None)

        ## GET ALL MEMBERSHIPS ##
        returned_tm = await get_all_team_memberships(
            prisma_client, [team_id], user_id=None
        )

        if isinstance(team_info, dict):
            _team_info = TeamInfoResponseObjectTeamTable(**team_info)
        elif isinstance(team_info, BaseModel):
            _team_info = TeamInfoResponseObjectTeamTable(**team_info.model_dump())
        else:
            _team_info = TeamInfoResponseObjectTeamTable()

        ## GET TEAM BUDGET (if exists) ##
        team_member_budget_id = (
            _team_info.metadata.get("team_member_budget_id")
            if _team_info.metadata is not None
            else None
        )
        if team_member_budget_id is not None:
            _team_info = await _add_team_member_budget_table(
                team_member_budget_id=team_member_budget_id,
                prisma_client=prisma_client,
                team_info_response_object=_team_info,
            )

        # ## UNFURL 'all-proxy-models' into the team_info.models list ##
        # if llm_router is not None:
        #     _team_info = _unfurl_all_proxy_models(_team_info, llm_router)
        response_object = TeamInfoResponseObject(
            team_id=team_id,
            team_info=_team_info,
            keys=keys,
            team_memberships=returned_tm,
        )
        return response_object

    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.management_endpoints.team_endpoints.py::team_info - Exception occurred - {}\n{}".format(
                e, traceback.format_exc()
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


@router.post(
    "/team/block", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def block_team(
    data: BlockTeamRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Blocks all calls from keys with this team id.

    Parameters:
    - team_id: str - Required. The unique identifier of the team to block.

    Example:
    ```
    curl --location 'http://0.0.0.0:4000/team/block' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "team_id": "team-1234"
    }'
    ```

    Returns:
    - The updated team record with blocked=True



    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise Exception("No DB Connected.")

    record = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id}, data={"blocked": True}  # type: ignore
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found, passed team_id={data.team_id}"},
        )

    return record


@router.post(
    "/team/unblock", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def unblock_team(
    data: BlockTeamRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Blocks all calls from keys with this team id.

    Parameters:
    - team_id: str - Required. The unique identifier of the team to unblock.

    Example:
    ```
    curl --location 'http://0.0.0.0:4000/team/unblock' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "team_id": "team-1234"
    }'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise Exception("No DB Connected.")

    record = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id}, data={"blocked": False}  # type: ignore
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found, passed team_id={data.team_id}"},
        )

    return record


@router.get("/team/available")
async def list_available_teams(
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    response_model=List[LiteLLM_TeamTable],
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    available_teams = cast(
        Optional[List[str]],
        (
            litellm.default_internal_user_params.get("available_teams")
            if litellm.default_internal_user_params is not None
            else None
        ),
    )
    if available_teams is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No available teams for user to join. See how to set available teams here: https://docs.litellm.ai/docs/proxy/self_serve#all-settings-for-self-serve--sso-flow"
            },
        )

    # filter out teams that the user is already a member of
    user_info = await prisma_client.db.litellm_usertable.find_unique(
        where={"user_id": user_api_key_dict.user_id}
    )
    if user_info is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found"},
        )
    user_info_correct_type = LiteLLM_UserTable(**user_info.model_dump())

    available_teams = [
        team for team in available_teams if team not in user_info_correct_type.teams
    ]

    available_teams_db = await prisma_client.db.litellm_teamtable.find_many(
        where={"team_id": {"in": available_teams}}
    )

    available_teams_correct_type = [
        LiteLLM_TeamTable(**team.model_dump()) for team in available_teams_db
    ]

    return available_teams_correct_type


@router.get(
    "/v2/team/list",
    tags=["team management"],
    response_model=TeamListResponse,
    dependencies=[Depends(user_api_key_auth)],
)
async def list_team_v2(
    http_request: Request,
    user_id: Optional[str] = fastapi.Query(
        default=None, description="Only return teams which this 'user_id' belongs to"
    ),
    organization_id: Optional[str] = fastapi.Query(
        default=None,
        description="Only return teams which this 'organization_id' belongs to",
    ),
    team_id: Optional[str] = fastapi.Query(
        default=None, description="Only return teams which this 'team_id' belongs to"
    ),
    team_alias: Optional[str] = fastapi.Query(
        default=None,
        description="Only return teams which this 'team_alias' belongs to. Supports partial matching.",
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=10, description="Number of teams per page", ge=1, le=100
    ),
    sort_by: Optional[str] = fastapi.Query(
        default=None,
        description="Column to sort by (e.g. 'team_id', 'team_alias', 'created_at')",
    ),
    sort_order: str = fastapi.Query(
        default="asc", description="Sort order ('asc' or 'desc')"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get a paginated list of teams with filtering and sorting options.

    Parameters:
        user_id: Optional[str]
            Only return teams which this user belongs to
        organization_id: Optional[str]
            Only return teams which belong to this organization
        team_id: Optional[str]
            Filter teams by exact team_id match
        team_alias: Optional[str]
            Filter teams by partial team_alias match
        page: int
            The page number to return
        page_size: int
            The number of items per page
        sort_by: Optional[str]
            Column to sort by (e.g. 'team_id', 'team_alias', 'created_at')
        sort_order: str
            Sort order ('asc' or 'desc')
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": f"No db connected. prisma client={prisma_client}"},
        )

    if user_id is None and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
        user_id = user_api_key_dict.user_id

    # Calculate skip and take for pagination
    skip = (page - 1) * page_size

    # Build where conditions based on provided parameters
    where_conditions: Dict[str, Any] = {}

    if team_id:
        where_conditions["team_id"] = team_id

    if team_alias:
        where_conditions["team_alias"] = {
            "contains": team_alias,
            "mode": "insensitive",  # Case-insensitive search
        }

    if organization_id:
        where_conditions["organization_id"] = organization_id

    if user_id:
        try:
            user_object = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": user_id}
            )
        except Exception:
            raise HTTPException(
                status_code=404,
                detail={"error": f"User not found, passed user_id={user_id}"},
            )
        if user_object is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"User not found, passed user_id={user_id}"},
            )
        user_object_correct_type = LiteLLM_UserTable(**user_object.model_dump())
        # Find teams where this user is a member by checking members_with_roles array
        if team_id is None:
            where_conditions["team_id"] = {"in": user_object_correct_type.teams}
        elif team_id in user_object_correct_type.teams:
            where_conditions["team_id"] = team_id
        else:
            raise HTTPException(
                status_code=404,
                detail={"error": f"User is not a member of team_id={team_id}"},
            )

    # Build order_by conditions
    valid_sort_columns = ["team_id", "team_alias", "created_at"]
    order_by = None
    if sort_by and sort_by in valid_sort_columns:
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"
        order_by = {sort_by: sort_order.lower()}

    # Get teams with pagination
    teams = await prisma_client.db.litellm_teamtable.find_many(
        where=where_conditions,
        skip=skip,
        take=page_size,
        order=order_by if order_by else {"created_at": "desc"},  # Default sort
    )
    # Get total count for pagination
    total_count = await prisma_client.db.litellm_teamtable.count(where=where_conditions)

    # Calculate total pages
    total_pages = -(-total_count // page_size)  # Ceiling division

    return {
        "teams": [team.model_dump() for team in teams] if teams else [],
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/team/list", tags=["team management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def list_team(
    http_request: Request,
    user_id: Optional[str] = fastapi.Query(
        default=None, description="Only return teams which this 'user_id' belongs to"
    ),
    organization_id: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    ```
    curl --location --request GET 'http://0.0.0.0:4000/team/list' \
        --header 'Authorization: Bearer sk-1234'
    ```

    Parameters:
    - user_id: str - Optional. If passed will only return teams that the user_id is a member of.
    - organization_id: str - Optional. If passed will only return teams that belong to the organization_id. Pass 'default_organization' to get all teams without organization_id.
    """
    from litellm.proxy.proxy_server import prisma_client

    if not allowed_route_check_inside_route(
        user_api_key_dict=user_api_key_dict, requested_user_id=user_id
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Only admin users can query all teams/other teams. Your user role={}".format(
                    user_api_key_dict.user_role
                )
            },
        )

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    response = await prisma_client.db.litellm_teamtable.find_many(
        include={
            "litellm_model_table": True,
        }
    )

    filtered_response = []
    if user_id:
        for team in response:
            if team.members_with_roles:
                for member in team.members_with_roles:
                    if (
                        "user_id" in member
                        and member["user_id"] is not None
                        and member["user_id"] == user_id
                    ):
                        filtered_response.append(team)

    else:
        filtered_response = response

    _team_ids = [team.team_id for team in filtered_response]
    returned_tm = await get_all_team_memberships(
        prisma_client, _team_ids, user_id=user_id
    )

    returned_responses: List[TeamListResponseObject] = []
    for team in filtered_response:
        _team_memberships: List[LiteLLM_TeamMembership] = []
        for tm in returned_tm:
            if tm.team_id == team.team_id:
                _team_memberships.append(tm)

        # add all keys that belong to the team
        keys = await prisma_client.db.litellm_verificationtoken.find_many(
            where={"team_id": team.team_id}
        )

        try:
            returned_responses.append(
                TeamListResponseObject(
                    **team.model_dump(),
                    team_memberships=_team_memberships,
                    keys=keys,
                )
            )
        except Exception as e:
            team_exception = """Invalid team object for team_id: {}. team_object={}.
            Error: {}
            """.format(
                team.team_id, team.model_dump(), str(e)
            )
            verbose_proxy_logger.exception(team_exception)
            continue
    # Sort the responses by team_alias
    returned_responses.sort(key=lambda x: (getattr(x, "team_alias", "") or ""))

    if organization_id is not None:
        if organization_id == SpecialManagementEndpointEnums.DEFAULT_ORGANIZATION.value:
            returned_responses = [
                team for team in returned_responses if team.organization_id is None
            ]
        else:
            returned_responses = [
                team
                for team in returned_responses
                if team.organization_id == organization_id
            ]

    return returned_responses


async def get_paginated_teams(
    prisma_client: PrismaClient,
    page_size: int = 10,
    page: int = 1,
) -> Tuple[List[LiteLLM_TeamTable], int]:
    """
    Get paginated list of teams from team table

    Parameters:
        prisma_client: PrismaClient - The database client
        page_size: int - Number of teams per page
        page: int - Page number (1-based)

    Returns:
        Tuple[List[LiteLLM_TeamTable], int] - (list of teams, total count)
    """
    try:
        # Calculate skip for pagination
        skip = (page - 1) * page_size
        # Get total count
        total_count = await prisma_client.db.litellm_teamtable.count()

        # Get paginated teams
        teams = await prisma_client.db.litellm_teamtable.find_many(
            skip=skip, take=page_size, order={"team_alias": "asc"}  # Sort by team_alias
        )
        return teams, total_count
    except Exception as e:
        verbose_proxy_logger.exception(
            f"[Non-Blocking] Error getting paginated teams: {e}"
        )
        return [], 0


def _update_team_metadata_field(updated_kv: dict, field_name: str) -> None:
    """
    Helper function to update metadata fields that require premium user checks in the update endpoint

    Args:
        updated_kv: The key-value dict being used for the update
        field_name: Name of the metadata field being updated
    """
    if field_name in LiteLLM_ManagementEndpoint_MetadataFields_Premium:
        _premium_user_check()

    if field_name in updated_kv and updated_kv[field_name] is not None:
        # remove field from updated_kv
        _value = updated_kv.pop(field_name)
        if "metadata" in updated_kv and updated_kv["metadata"] is not None:
            updated_kv["metadata"][field_name] = _value
        else:
            updated_kv["metadata"] = {field_name: _value}


@router.get(
    "/team/filter/ui",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_TeamTable]},
    },
)
async def ui_view_teams(
    team_id: Optional[str] = fastapi.Query(
        default=None, description="Team ID in the request parameters"
    ),
    team_alias: Optional[str] = fastapi.Query(
        default=None, description="Team alias in the request parameters"
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=50, description="Number of items per page", ge=1, le=100
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [PROXY-ADMIN ONLY] Filter teams based on partial match of team_id or team_alias with pagination.

    Args:
        user_id (Optional[str]): Partial user ID to search for
        user_email (Optional[str]): Partial email to search for
        page (int): Page number for pagination (starts at 1)
        page_size (int): Number of items per page (max 100)
        user_api_key_dict (UserAPIKeyAuth): User authentication information

    Returns:
        List[LiteLLM_SpendLogs]: Paginated list of matching user records
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size

        # Build where conditions based on provided parameters
        where_conditions = {}

        if team_id:
            where_conditions["team_id"] = {
                "contains": team_id,
                "mode": "insensitive",  # Case-insensitive search
            }

        if team_alias:
            where_conditions["team_alias"] = {
                "contains": team_alias,
                "mode": "insensitive",  # Case-insensitive search
            }

        # Query users with pagination and filters
        teams = await prisma_client.db.litellm_teamtable.find_many(
            where=where_conditions,
            skip=skip,
            take=page_size,
            order={"created_at": "desc"},
        )

        if not teams:
            return []

        return teams

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching teams: {str(e)}")


@router.post(
    "/team/model/add",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def team_model_add(
    data: TeamModelAddRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Add models to a team's allowed model list. Only proxy admin or team admin can add models.

    Parameters:
    - team_id: str - Required. The team to add models to
    - models: List[str] - Required. List of models to add to the team

    Example Request:
    ```
    curl --location 'http://0.0.0.0:4000/team/model/add' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "team_id": "team-1234",
        "models": ["gpt-4", "claude-2"]
    }'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    # Get existing team
    team_row = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": data.team_id}
    )

    if team_row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found, passed team_id={data.team_id}"},
        )

    team_obj = LiteLLM_TeamTable(**team_row.model_dump())

    # Authorization check - only proxy admin or team admin can add models
    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=team_obj
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={"error": "Only proxy admin or team admin can modify team models"},
        )

    # Get current models list
    current_models = team_obj.models or []

    # Add new models (avoid duplicates)
    updated_models = list(set(current_models + data.models))

    # Update team
    updated_team = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id}, data={"models": updated_models}
    )

    return updated_team


@router.post(
    "/team/model/delete",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def team_model_delete(
    data: TeamModelDeleteRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Remove models from a team's allowed model list. Only proxy admin or team admin can remove models.

    Parameters:
    - team_id: str - Required. The team to remove models from
    - models: List[str] - Required. List of models to remove from the team

    Example Request:
    ```
    curl --location 'http://0.0.0.0:4000/team/model/delete' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "team_id": "team-1234",
        "models": ["gpt-4"]
    }'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    # Get existing team
    team_row = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": data.team_id}
    )

    if team_row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found, passed team_id={data.team_id}"},
        )

    team_obj = LiteLLM_TeamTable(**team_row.model_dump())

    # Authorization check - only proxy admin or team admin can remove models
    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=team_obj
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={"error": "Only proxy admin or team admin can modify team models"},
        )

    # Get current models list
    current_models = team_obj.models or []

    # Remove specified models
    updated_models = [m for m in current_models if m not in data.models]

    # Update team
    updated_team = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id}, data={"models": updated_models}
    )

    return updated_team


@router.get(
    "/team/permissions_list",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def team_member_permissions(
    team_id: str = fastapi.Query(
        default=None, description="Team ID in the request parameters"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> GetTeamMemberPermissionsResponse:
    """
    Get the team member permissions for a team
    """
    from litellm.proxy.proxy_server import (
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    ## CHECK IF USER IS PROXY ADMIN OR TEAM ADMIN
    existing_team_row = await get_team_object(
        team_id=team_id,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        parent_otel_span=None,
        proxy_logging_obj=proxy_logging_obj,
        check_cache_only=False,
        check_db_only=True,
    )
    if existing_team_row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found for team_id={team_id}"},
        )

    complete_team_data = LiteLLM_TeamTable(**existing_team_row.model_dump())

    if (
        hasattr(user_api_key_dict, "user_role")
        and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=complete_team_data
        )
        and not _is_available_team(
            team_id=complete_team_data.team_id,
            user_api_key_dict=user_api_key_dict,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Call not allowed. User not proxy admin OR team admin. route={}, team_id={}".format(
                    "/team/member_add",
                    complete_team_data.team_id,
                )
            },
        )

    if existing_team_row.team_member_permissions is None:
        existing_team_row.team_member_permissions = (
            TeamMemberPermissionChecks.default_team_member_permissions()
        )

    return GetTeamMemberPermissionsResponse(
        team_id=team_id,
        team_member_permissions=existing_team_row.team_member_permissions,
        all_available_permissions=TeamMemberPermissionChecks.get_all_available_team_member_permissions(),
    )


@router.post(
    "/team/permissions_update",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_team_member_permissions(
    data: UpdateTeamMemberPermissionsRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> LiteLLM_TeamTable:
    """
    Update the team member permissions for a team
    """
    from litellm.proxy.proxy_server import (
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    ## CHECK IF USER IS PROXY ADMIN OR TEAM ADMIN
    existing_team_row = await get_team_object(
        team_id=data.team_id,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        parent_otel_span=None,
        proxy_logging_obj=proxy_logging_obj,
        check_cache_only=False,
        check_db_only=True,
    )
    if existing_team_row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Team not found for team_id={data.team_id}"},
        )

    complete_team_data = LiteLLM_TeamTable(**existing_team_row.model_dump())

    if (
        hasattr(user_api_key_dict, "user_role")
        and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN.value
        and not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=complete_team_data
        )
        and not _is_available_team(
            team_id=complete_team_data.team_id,
            user_api_key_dict=user_api_key_dict,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Call not allowed. User not proxy admin OR team admin. route={}, team_id={}".format(
                    "/team/member_add",
                    complete_team_data.team_id,
                )
            },
        )
    # Update the team member permissions
    updated_team = await prisma_client.db.litellm_teamtable.update(
        where={"team_id": data.team_id},
        data={"team_member_permissions": data.team_member_permissions},
    )

    return updated_team


@router.get(
    "/team/daily/activity",
    response_model=SpendAnalyticsPaginatedResponse,
    tags=["team management"],
)
async def get_team_daily_activity(
    team_ids: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    exclude_team_ids: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get daily activity for specific teams or all teams.

    Args:
        team_ids (Optional[str]): Comma-separated list of team IDs to filter by. If not provided, returns data for all teams.
        start_date (Optional[str]): Start date for the activity period (YYYY-MM-DD).
        end_date (Optional[str]): End date for the activity period (YYYY-MM-DD).
        model (Optional[str]): Filter by model name.
        api_key (Optional[str]): Filter by API key.
        page (int): Page number for pagination.
        page_size (int): Number of items per page.
        exclude_team_ids (Optional[str]): Comma-separated list of team IDs to exclude.
    Returns:
        SpendAnalyticsPaginatedResponse: Paginated response containing daily activity data.
    """
    from litellm.proxy.proxy_server import (
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    # Convert comma-separated tags string to list if provided
    team_ids_list = team_ids.split(",") if team_ids else None
    exclude_team_ids_list: Optional[List[str]] = None

    if exclude_team_ids:
        exclude_team_ids_list = (
            exclude_team_ids.split(",") if exclude_team_ids else None
        )

    if not _user_has_admin_view(user_api_key_dict):
        user_info = await get_user_object(
            user_id=user_api_key_dict.user_id,
            prisma_client=prisma_client,
            user_id_upsert=False,
            user_api_key_cache=user_api_key_cache,
            parent_otel_span=user_api_key_dict.parent_otel_span,
            proxy_logging_obj=proxy_logging_obj,
            check_db_only=True,
        )
        if user_info is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "User= {} not found".format(user_api_key_dict.user_id)
                },
            )

        if team_ids_list is None:
            team_ids_list = user_info.teams
        else:
            # check if all team_ids are in user_info.teams
            for team_id in team_ids_list:
                if team_id not in user_info.teams:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "User does not belong to Team= {}. Call `/user/info` to see user's teams".format(
                                team_id
                            )
                        },
                    )

    ## Fetch team aliases
    where_condition = {}
    if team_ids_list:
        where_condition["team_id"] = {"in": list(team_ids_list)}
    team_aliases = await prisma_client.db.litellm_teamtable.find_many(
        where=where_condition
    )
    team_alias_metadata = {
        t.team_id: {"team_alias": t.team_alias} for t in team_aliases
    }

    return await get_daily_activity(
        prisma_client=prisma_client,
        table_name="litellm_dailyteamspend",
        entity_id_field="team_id",
        entity_id=team_ids_list,
        entity_metadata_field=team_alias_metadata,
        exclude_entity_ids=exclude_team_ids_list,
        start_date=start_date,
        end_date=end_date,
        model=model,
        api_key=api_key,
        page=page,
        page_size=page_size,
    )

# === NexusCore/openenv\Lib\site-packages\pydantic\json_schema.py ===
"""!!! abstract "Usage Documentation"
    [JSON Schema](../concepts/json_schema.md)

The `json_schema` module contains classes and functions to allow the way [JSON Schema](https://json-schema.org/)
is generated to be customized.

In general you shouldn't need to use this module directly; instead, you can use
[`BaseModel.model_json_schema`][pydantic.BaseModel.model_json_schema] and
[`TypeAdapter.json_schema`][pydantic.TypeAdapter.json_schema].
"""

from __future__ import annotations as _annotations

import dataclasses
import inspect
import math
import os
import re
import warnings
from collections import Counter, defaultdict
from collections.abc import Hashable, Iterable, Sequence
from copy import deepcopy
from enum import Enum
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Literal,
    NewType,
    TypeVar,
    Union,
    cast,
    overload,
)

import pydantic_core
from pydantic_core import CoreSchema, PydanticOmit, core_schema, to_jsonable_python
from pydantic_core.core_schema import ComputedField
from typing_extensions import TypeAlias, assert_never, deprecated, final
from typing_inspection.introspection import get_literal_values

from pydantic.warnings import PydanticDeprecatedSince26, PydanticDeprecatedSince29

from ._internal import (
    _config,
    _core_metadata,
    _core_utils,
    _decorators,
    _internal_dataclass,
    _mock_val_ser,
    _schema_generation_shared,
)
from .annotated_handlers import GetJsonSchemaHandler
from .config import JsonDict, JsonValue
from .errors import PydanticInvalidForJsonSchema, PydanticSchemaGenerationError, PydanticUserError

if TYPE_CHECKING:
    from . import ConfigDict
    from ._internal._core_utils import CoreSchemaField, CoreSchemaOrField
    from ._internal._dataclasses import PydanticDataclass
    from ._internal._schema_generation_shared import GetJsonSchemaFunction
    from .main import BaseModel


CoreSchemaOrFieldType = Literal[core_schema.CoreSchemaType, core_schema.CoreSchemaFieldType]
"""
A type alias for defined schema types that represents a union of
`core_schema.CoreSchemaType` and
`core_schema.CoreSchemaFieldType`.
"""

JsonSchemaValue = dict[str, Any]
"""
A type alias for a JSON schema value. This is a dictionary of string keys to arbitrary JSON values.
"""

JsonSchemaMode = Literal['validation', 'serialization']
"""
A type alias that represents the mode of a JSON schema; either 'validation' or 'serialization'.

For some types, the inputs to validation differ from the outputs of serialization. For example,
computed fields will only be present when serializing, and should not be provided when
validating. This flag provides a way to indicate whether you want the JSON schema required
for validation inputs, or that will be matched by serialization outputs.
"""

_MODE_TITLE_MAPPING: dict[JsonSchemaMode, str] = {'validation': 'Input', 'serialization': 'Output'}


JsonSchemaWarningKind = Literal['skipped-choice', 'non-serializable-default', 'skipped-discriminator']
"""
A type alias representing the kinds of warnings that can be emitted during JSON schema generation.

See [`GenerateJsonSchema.render_warning_message`][pydantic.json_schema.GenerateJsonSchema.render_warning_message]
for more details.
"""


class PydanticJsonSchemaWarning(UserWarning):
    """This class is used to emit warnings produced during JSON schema generation.
    See the [`GenerateJsonSchema.emit_warning`][pydantic.json_schema.GenerateJsonSchema.emit_warning] and
    [`GenerateJsonSchema.render_warning_message`][pydantic.json_schema.GenerateJsonSchema.render_warning_message]
    methods for more details; these can be overridden to control warning behavior.
    """


NoDefault = object()
"""A sentinel value used to indicate that no default value should be used when generating a JSON Schema
for a core schema with a default value.
"""


# ##### JSON Schema Generation #####
DEFAULT_REF_TEMPLATE = '#/$defs/{model}'
"""The default format string used to generate reference names."""

# There are three types of references relevant to building JSON schemas:
#   1. core_schema "ref" values; these are not exposed as part of the JSON schema
#       * these might look like the fully qualified path of a model, its id, or something similar
CoreRef = NewType('CoreRef', str)
#   2. keys of the "definitions" object that will eventually go into the JSON schema
#       * by default, these look like "MyModel", though may change in the presence of collisions
#       * eventually, we may want to make it easier to modify the way these names are generated
DefsRef = NewType('DefsRef', str)
#   3. the values corresponding to the "$ref" key in the schema
#       * By default, these look like "#/$defs/MyModel", as in {"$ref": "#/$defs/MyModel"}
JsonRef = NewType('JsonRef', str)

CoreModeRef = tuple[CoreRef, JsonSchemaMode]
JsonSchemaKeyT = TypeVar('JsonSchemaKeyT', bound=Hashable)


@dataclasses.dataclass(**_internal_dataclass.slots_true)
class _DefinitionsRemapping:
    defs_remapping: dict[DefsRef, DefsRef]
    json_remapping: dict[JsonRef, JsonRef]

    @staticmethod
    def from_prioritized_choices(
        prioritized_choices: dict[DefsRef, list[DefsRef]],
        defs_to_json: dict[DefsRef, JsonRef],
        definitions: dict[DefsRef, JsonSchemaValue],
    ) -> _DefinitionsRemapping:
        """
        This function should produce a remapping that replaces complex DefsRef with the simpler ones from the
        prioritized_choices such that applying the name remapping would result in an equivalent JSON schema.
        """
        # We need to iteratively simplify the definitions until we reach a fixed point.
        # The reason for this is that outer definitions may reference inner definitions that get simplified
        # into an equivalent reference, and the outer definitions won't be equivalent until we've simplified
        # the inner definitions.
        copied_definitions = deepcopy(definitions)
        definitions_schema = {'$defs': copied_definitions}
        for _iter in range(100):  # prevent an infinite loop in the case of a bug, 100 iterations should be enough
            # For every possible remapped DefsRef, collect all schemas that that DefsRef might be used for:
            schemas_for_alternatives: dict[DefsRef, list[JsonSchemaValue]] = defaultdict(list)
            for defs_ref in copied_definitions:
                alternatives = prioritized_choices[defs_ref]
                for alternative in alternatives:
                    schemas_for_alternatives[alternative].append(copied_definitions[defs_ref])

            # Deduplicate the schemas for each alternative; the idea is that we only want to remap to a new DefsRef
            # if it introduces no ambiguity, i.e., there is only one distinct schema for that DefsRef.
            for defs_ref in schemas_for_alternatives:
                schemas_for_alternatives[defs_ref] = _deduplicate_schemas(schemas_for_alternatives[defs_ref])

            # Build the remapping
            defs_remapping: dict[DefsRef, DefsRef] = {}
            json_remapping: dict[JsonRef, JsonRef] = {}
            for original_defs_ref in definitions:
                alternatives = prioritized_choices[original_defs_ref]
                # Pick the first alternative that has only one schema, since that means there is no collision
                remapped_defs_ref = next(x for x in alternatives if len(schemas_for_alternatives[x]) == 1)
                defs_remapping[original_defs_ref] = remapped_defs_ref
                json_remapping[defs_to_json[original_defs_ref]] = defs_to_json[remapped_defs_ref]
            remapping = _DefinitionsRemapping(defs_remapping, json_remapping)
            new_definitions_schema = remapping.remap_json_schema({'$defs': copied_definitions})
            if definitions_schema == new_definitions_schema:
                # We've reached the fixed point
                return remapping
            definitions_schema = new_definitions_schema

        raise PydanticInvalidForJsonSchema('Failed to simplify the JSON schema definitions')

    def remap_defs_ref(self, ref: DefsRef) -> DefsRef:
        return self.defs_remapping.get(ref, ref)

    def remap_json_ref(self, ref: JsonRef) -> JsonRef:
        return self.json_remapping.get(ref, ref)

    def remap_json_schema(self, schema: Any) -> Any:
        """
        Recursively update the JSON schema replacing all $refs
        """
        if isinstance(schema, str):
            # Note: this may not really be a JsonRef; we rely on having no collisions between JsonRefs and other strings
            return self.remap_json_ref(JsonRef(schema))
        elif isinstance(schema, list):
            return [self.remap_json_schema(item) for item in schema]
        elif isinstance(schema, dict):
            for key, value in schema.items():
                if key == '$ref' and isinstance(value, str):
                    schema['$ref'] = self.remap_json_ref(JsonRef(value))
                elif key == '$defs':
                    schema['$defs'] = {
                        self.remap_defs_ref(DefsRef(key)): self.remap_json_schema(value)
                        for key, value in schema['$defs'].items()
                    }
                else:
                    schema[key] = self.remap_json_schema(value)
        return schema


class GenerateJsonSchema:
    """!!! abstract "Usage Documentation"
        [Customizing the JSON Schema Generation Process](../concepts/json_schema.md#customizing-the-json-schema-generation-process)

    A class for generating JSON schemas.

    This class generates JSON schemas based on configured parameters. The default schema dialect
    is [https://json-schema.org/draft/2020-12/schema](https://json-schema.org/draft/2020-12/schema).
    The class uses `by_alias` to configure how fields with
    multiple names are handled and `ref_template` to format reference names.

    Attributes:
        schema_dialect: The JSON schema dialect used to generate the schema. See
            [Declaring a Dialect](https://json-schema.org/understanding-json-schema/reference/schema.html#id4)
            in the JSON Schema documentation for more information about dialects.
        ignored_warning_kinds: Warnings to ignore when generating the schema. `self.render_warning_message` will
            do nothing if its argument `kind` is in `ignored_warning_kinds`;
            this value can be modified on subclasses to easily control which warnings are emitted.
        by_alias: Whether to use field aliases when generating the schema.
        ref_template: The format string used when generating reference names.
        core_to_json_refs: A mapping of core refs to JSON refs.
        core_to_defs_refs: A mapping of core refs to definition refs.
        defs_to_core_refs: A mapping of definition refs to core refs.
        json_to_defs_refs: A mapping of JSON refs to definition refs.
        definitions: Definitions in the schema.

    Args:
        by_alias: Whether to use field aliases in the generated schemas.
        ref_template: The format string to use when generating reference names.

    Raises:
        JsonSchemaError: If the instance of the class is inadvertently reused after generating a schema.
    """

    schema_dialect = 'https://json-schema.org/draft/2020-12/schema'

    # `self.render_warning_message` will do nothing if its argument `kind` is in `ignored_warning_kinds`;
    # this value can be modified on subclasses to easily control which warnings are emitted
    ignored_warning_kinds: set[JsonSchemaWarningKind] = {'skipped-choice'}

    def __init__(self, by_alias: bool = True, ref_template: str = DEFAULT_REF_TEMPLATE):
        self.by_alias = by_alias
        self.ref_template = ref_template

        self.core_to_json_refs: dict[CoreModeRef, JsonRef] = {}
        self.core_to_defs_refs: dict[CoreModeRef, DefsRef] = {}
        self.defs_to_core_refs: dict[DefsRef, CoreModeRef] = {}
        self.json_to_defs_refs: dict[JsonRef, DefsRef] = {}

        self.definitions: dict[DefsRef, JsonSchemaValue] = {}
        self._config_wrapper_stack = _config.ConfigWrapperStack(_config.ConfigWrapper({}))

        self._mode: JsonSchemaMode = 'validation'

        # The following includes a mapping of a fully-unique defs ref choice to a list of preferred
        # alternatives, which are generally simpler, such as only including the class name.
        # At the end of schema generation, we use these to produce a JSON schema with more human-readable
        # definitions, which would also work better in a generated OpenAPI client, etc.
        self._prioritized_defsref_choices: dict[DefsRef, list[DefsRef]] = {}
        self._collision_counter: dict[str, int] = defaultdict(int)
        self._collision_index: dict[str, int] = {}

        self._schema_type_to_method = self.build_schema_type_to_method()

        # When we encounter definitions we need to try to build them immediately
        # so that they are available schemas that reference them
        # But it's possible that CoreSchema was never going to be used
        # (e.g. because the CoreSchema that references short circuits is JSON schema generation without needing
        #  the reference) so instead of failing altogether if we can't build a definition we
        # store the error raised and re-throw it if we end up needing that def
        self._core_defs_invalid_for_json_schema: dict[DefsRef, PydanticInvalidForJsonSchema] = {}

        # This changes to True after generating a schema, to prevent issues caused by accidental reuse
        # of a single instance of a schema generator
        self._used = False

    @property
    def _config(self) -> _config.ConfigWrapper:
        return self._config_wrapper_stack.tail

    @property
    def mode(self) -> JsonSchemaMode:
        if self._config.json_schema_mode_override is not None:
            return self._config.json_schema_mode_override
        else:
            return self._mode

    def build_schema_type_to_method(
        self,
    ) -> dict[CoreSchemaOrFieldType, Callable[[CoreSchemaOrField], JsonSchemaValue]]:
        """Builds a dictionary mapping fields to methods for generating JSON schemas.

        Returns:
            A dictionary containing the mapping of `CoreSchemaOrFieldType` to a handler method.

        Raises:
            TypeError: If no method has been defined for generating a JSON schema for a given pydantic core schema type.
        """
        mapping: dict[CoreSchemaOrFieldType, Callable[[CoreSchemaOrField], JsonSchemaValue]] = {}
        core_schema_types: list[CoreSchemaOrFieldType] = list(get_literal_values(CoreSchemaOrFieldType))
        for key in core_schema_types:
            method_name = f'{key.replace("-", "_")}_schema'
            try:
                mapping[key] = getattr(self, method_name)
            except AttributeError as e:  # pragma: no cover
                if os.getenv('PYDANTIC_PRIVATE_ALLOW_UNHANDLED_SCHEMA_TYPES'):
                    continue
                raise TypeError(
                    f'No method for generating JsonSchema for core_schema.type={key!r} '
                    f'(expected: {type(self).__name__}.{method_name})'
                ) from e
        return mapping

    def generate_definitions(
        self, inputs: Sequence[tuple[JsonSchemaKeyT, JsonSchemaMode, core_schema.CoreSchema]]
    ) -> tuple[dict[tuple[JsonSchemaKeyT, JsonSchemaMode], JsonSchemaValue], dict[DefsRef, JsonSchemaValue]]:
        """Generates JSON schema definitions from a list of core schemas, pairing the generated definitions with a
        mapping that links the input keys to the definition references.

        Args:
            inputs: A sequence of tuples, where:

                - The first element is a JSON schema key type.
                - The second element is the JSON mode: either 'validation' or 'serialization'.
                - The third element is a core schema.

        Returns:
            A tuple where:

                - The first element is a dictionary whose keys are tuples of JSON schema key type and JSON mode, and
                    whose values are the JSON schema corresponding to that pair of inputs. (These schemas may have
                    JsonRef references to definitions that are defined in the second returned element.)
                - The second element is a dictionary whose keys are definition references for the JSON schemas
                    from the first returned element, and whose values are the actual JSON schema definitions.

        Raises:
            PydanticUserError: Raised if the JSON schema generator has already been used to generate a JSON schema.
        """
        if self._used:
            raise PydanticUserError(
                'This JSON schema generator has already been used to generate a JSON schema. '
                f'You must create a new instance of {type(self).__name__} to generate a new JSON schema.',
                code='json-schema-already-used',
            )

        for _, mode, schema in inputs:
            self._mode = mode
            self.generate_inner(schema)

        definitions_remapping = self._build_definitions_remapping()

        json_schemas_map: dict[tuple[JsonSchemaKeyT, JsonSchemaMode], DefsRef] = {}
        for key, mode, schema in inputs:
            self._mode = mode
            json_schema = self.generate_inner(schema)
            json_schemas_map[(key, mode)] = definitions_remapping.remap_json_schema(json_schema)

        json_schema = {'$defs': self.definitions}
        json_schema = definitions_remapping.remap_json_schema(json_schema)
        self._used = True
        return json_schemas_map, self.sort(json_schema['$defs'])  # type: ignore

    def generate(self, schema: CoreSchema, mode: JsonSchemaMode = 'validation') -> JsonSchemaValue:
        """Generates a JSON schema for a specified schema in a specified mode.

        Args:
            schema: A Pydantic model.
            mode: The mode in which to generate the schema. Defaults to 'validation'.

        Returns:
            A JSON schema representing the specified schema.

        Raises:
            PydanticUserError: If the JSON schema generator has already been used to generate a JSON schema.
        """
        self._mode = mode
        if self._used:
            raise PydanticUserError(
                'This JSON schema generator has already been used to generate a JSON schema. '
                f'You must create a new instance of {type(self).__name__} to generate a new JSON schema.',
                code='json-schema-already-used',
            )

        json_schema: JsonSchemaValue = self.generate_inner(schema)
        json_ref_counts = self.get_json_ref_counts(json_schema)

        ref = cast(JsonRef, json_schema.get('$ref'))
        while ref is not None:  # may need to unpack multiple levels
            ref_json_schema = self.get_schema_from_definitions(ref)
            if json_ref_counts[ref] == 1 and ref_json_schema is not None and len(json_schema) == 1:
                # "Unpack" the ref since this is the only reference and there are no sibling keys
                json_schema = ref_json_schema.copy()  # copy to prevent recursive dict reference
                json_ref_counts[ref] -= 1
                ref = cast(JsonRef, json_schema.get('$ref'))
            ref = None

        self._garbage_collect_definitions(json_schema)
        definitions_remapping = self._build_definitions_remapping()

        if self.definitions:
            json_schema['$defs'] = self.definitions

        json_schema = definitions_remapping.remap_json_schema(json_schema)

        # For now, we will not set the $schema key. However, if desired, this can be easily added by overriding
        # this method and adding the following line after a call to super().generate(schema):
        # json_schema['$schema'] = self.schema_dialect

        self._used = True
        return self.sort(json_schema)

    def generate_inner(self, schema: CoreSchemaOrField) -> JsonSchemaValue:  # noqa: C901
        """Generates a JSON schema for a given core schema.

        Args:
            schema: The given core schema.

        Returns:
            The generated JSON schema.

        TODO: the nested function definitions here seem like bad practice, I'd like to unpack these
        in a future PR. It'd be great if we could shorten the call stack a bit for JSON schema generation,
        and I think there's potential for that here.
        """
        # If a schema with the same CoreRef has been handled, just return a reference to it
        # Note that this assumes that it will _never_ be the case that the same CoreRef is used
        # on types that should have different JSON schemas
        if 'ref' in schema:
            core_ref = CoreRef(schema['ref'])  # type: ignore[typeddict-item]
            core_mode_ref = (core_ref, self.mode)
            if core_mode_ref in self.core_to_defs_refs and self.core_to_defs_refs[core_mode_ref] in self.definitions:
                return {'$ref': self.core_to_json_refs[core_mode_ref]}

        def populate_defs(core_schema: CoreSchema, json_schema: JsonSchemaValue) -> JsonSchemaValue:
            if 'ref' in core_schema:
                core_ref = CoreRef(core_schema['ref'])  # type: ignore[typeddict-item]
                defs_ref, ref_json_schema = self.get_cache_defs_ref_schema(core_ref)
                json_ref = JsonRef(ref_json_schema['$ref'])
                # Replace the schema if it's not a reference to itself
                # What we want to avoid is having the def be just a ref to itself
                # which is what would happen if we blindly assigned any
                if json_schema.get('$ref', None) != json_ref:
                    self.definitions[defs_ref] = json_schema
                    self._core_defs_invalid_for_json_schema.pop(defs_ref, None)
                json_schema = ref_json_schema
            return json_schema

        def handler_func(schema_or_field: CoreSchemaOrField) -> JsonSchemaValue:
            """Generate a JSON schema based on the input schema.

            Args:
                schema_or_field: The core schema to generate a JSON schema from.

            Returns:
                The generated JSON schema.

            Raises:
                TypeError: If an unexpected schema type is encountered.
            """
            # Generate the core-schema-type-specific bits of the schema generation:
            json_schema: JsonSchemaValue | None = None
            if self.mode == 'serialization' and 'serialization' in schema_or_field:
                # In this case, we skip the JSON Schema generation of the schema
                # and use the `'serialization'` schema instead (canonical example:
                # `Annotated[int, PlainSerializer(str)]`).
                ser_schema = schema_or_field['serialization']  # type: ignore
                json_schema = self.ser_schema(ser_schema)

                # It might be that the 'serialization'` is skipped depending on `when_used`.
                # This is only relevant for `nullable` schemas though, so we special case here.
                if (
                    json_schema is not None
                    and ser_schema.get('when_used') in ('unless-none', 'json-unless-none')
                    and schema_or_field['type'] == 'nullable'
                ):
                    json_schema = self.get_flattened_anyof([{'type': 'null'}, json_schema])
            if json_schema is None:
                if _core_utils.is_core_schema(schema_or_field) or _core_utils.is_core_schema_field(schema_or_field):
                    generate_for_schema_type = self._schema_type_to_method[schema_or_field['type']]
                    json_schema = generate_for_schema_type(schema_or_field)
                else:
                    raise TypeError(f'Unexpected schema type: schema={schema_or_field}')

            return json_schema

        current_handler = _schema_generation_shared.GenerateJsonSchemaHandler(self, handler_func)

        metadata = cast(_core_metadata.CoreMetadata, schema.get('metadata', {}))

        # TODO: I dislike that we have to wrap these basic dict updates in callables, is there any way around this?

        if js_updates := metadata.get('pydantic_js_updates'):

            def js_updates_handler_func(
                schema_or_field: CoreSchemaOrField,
                current_handler: GetJsonSchemaHandler = current_handler,
            ) -> JsonSchemaValue:
                json_schema = {**current_handler(schema_or_field), **js_updates}
                return json_schema

            current_handler = _schema_generation_shared.GenerateJsonSchemaHandler(self, js_updates_handler_func)

        if js_extra := metadata.get('pydantic_js_extra'):

            def js_extra_handler_func(
                schema_or_field: CoreSchemaOrField,
                current_handler: GetJsonSchemaHandler = current_handler,
            ) -> JsonSchemaValue:
                json_schema = current_handler(schema_or_field)
                if isinstance(js_extra, dict):
                    json_schema.update(to_jsonable_python(js_extra))
                elif callable(js_extra):
                    # similar to typing issue in _update_class_schema when we're working with callable js extra
                    js_extra(json_schema)  # type: ignore
                return json_schema

            current_handler = _schema_generation_shared.GenerateJsonSchemaHandler(self, js_extra_handler_func)

        for js_modify_function in metadata.get('pydantic_js_functions', ()):

            def new_handler_func(
                schema_or_field: CoreSchemaOrField,
                current_handler: GetJsonSchemaHandler = current_handler,
                js_modify_function: GetJsonSchemaFunction = js_modify_function,
            ) -> JsonSchemaValue:
                json_schema = js_modify_function(schema_or_field, current_handler)
                if _core_utils.is_core_schema(schema_or_field):
                    json_schema = populate_defs(schema_or_field, json_schema)
                original_schema = current_handler.resolve_ref_schema(json_schema)
                ref = json_schema.pop('$ref', None)
                if ref and json_schema:
                    original_schema.update(json_schema)
                return original_schema

            current_handler = _schema_generation_shared.GenerateJsonSchemaHandler(self, new_handler_func)

        for js_modify_function in metadata.get('pydantic_js_annotation_functions', ()):

            def new_handler_func(
                schema_or_field: CoreSchemaOrField,
                current_handler: GetJsonSchemaHandler = current_handler,
                js_modify_function: GetJsonSchemaFunction = js_modify_function,
            ) -> JsonSchemaValue:
                return js_modify_function(schema_or_field, current_handler)

            current_handler = _schema_generation_shared.GenerateJsonSchemaHandler(self, new_handler_func)

        json_schema = current_handler(schema)
        if _core_utils.is_core_schema(schema):
            json_schema = populate_defs(schema, json_schema)
        return json_schema

    def sort(self, value: JsonSchemaValue, parent_key: str | None = None) -> JsonSchemaValue:
        """Override this method to customize the sorting of the JSON schema (e.g., don't sort at all, sort all keys unconditionally, etc.)

        By default, alphabetically sort the keys in the JSON schema, skipping the 'properties' and 'default' keys to preserve field definition order.
        This sort is recursive, so it will sort all nested dictionaries as well.
        """
        sorted_dict: dict[str, JsonSchemaValue] = {}
        keys = value.keys()
        if parent_key not in ('properties', 'default'):
            keys = sorted(keys)
        for key in keys:
            sorted_dict[key] = self._sort_recursive(value[key], parent_key=key)
        return sorted_dict

    def _sort_recursive(self, value: Any, parent_key: str | None = None) -> Any:
        """Recursively sort a JSON schema value."""
        if isinstance(value, dict):
            sorted_dict: dict[str, JsonSchemaValue] = {}
            keys = value.keys()
            if parent_key not in ('properties', 'default'):
                keys = sorted(keys)
            for key in keys:
                sorted_dict[key] = self._sort_recursive(value[key], parent_key=key)
            return sorted_dict
        elif isinstance(value, list):
            sorted_list: list[JsonSchemaValue] = []
            for item in value:
                sorted_list.append(self._sort_recursive(item, parent_key))
            return sorted_list
        else:
            return value

    # ### Schema generation methods

    def invalid_schema(self, schema: core_schema.InvalidSchema) -> JsonSchemaValue:
        """Placeholder - should never be called."""

        raise RuntimeError('Cannot generate schema for invalid_schema. This is a bug! Please report it.')

    def any_schema(self, schema: core_schema.AnySchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches any value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {}

    def none_schema(self, schema: core_schema.NoneSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches `None`.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'null'}

    def bool_schema(self, schema: core_schema.BoolSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a bool value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'boolean'}

    def int_schema(self, schema: core_schema.IntSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches an int value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema: dict[str, Any] = {'type': 'integer'}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.numeric)
        json_schema = {k: v for k, v in json_schema.items() if v not in {math.inf, -math.inf}}
        return json_schema

    def float_schema(self, schema: core_schema.FloatSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a float value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema: dict[str, Any] = {'type': 'number'}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.numeric)
        json_schema = {k: v for k, v in json_schema.items() if v not in {math.inf, -math.inf}}
        return json_schema

    def decimal_schema(self, schema: core_schema.DecimalSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a decimal value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = self.str_schema(core_schema.str_schema())
        if self.mode == 'validation':
            multiple_of = schema.get('multiple_of')
            le = schema.get('le')
            ge = schema.get('ge')
            lt = schema.get('lt')
            gt = schema.get('gt')
            json_schema = {
                'anyOf': [
                    self.float_schema(
                        core_schema.float_schema(
                            allow_inf_nan=schema.get('allow_inf_nan'),
                            multiple_of=None if multiple_of is None else float(multiple_of),
                            le=None if le is None else float(le),
                            ge=None if ge is None else float(ge),
                            lt=None if lt is None else float(lt),
                            gt=None if gt is None else float(gt),
                        )
                    ),
                    json_schema,
                ],
            }
        return json_schema

    def str_schema(self, schema: core_schema.StringSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a string value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = {'type': 'string'}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.string)
        if isinstance(json_schema.get('pattern'), Pattern):
            # TODO: should we add regex flags to the pattern?
            json_schema['pattern'] = json_schema.get('pattern').pattern  # type: ignore
        return json_schema

    def bytes_schema(self, schema: core_schema.BytesSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a bytes value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = {'type': 'string', 'format': 'base64url' if self._config.ser_json_bytes == 'base64' else 'binary'}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.bytes)
        return json_schema

    def date_schema(self, schema: core_schema.DateSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a date value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'string', 'format': 'date'}

    def time_schema(self, schema: core_schema.TimeSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a time value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'string', 'format': 'time'}

    def datetime_schema(self, schema: core_schema.DatetimeSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a datetime value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'string', 'format': 'date-time'}

    def timedelta_schema(self, schema: core_schema.TimedeltaSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a timedelta value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if self._config.ser_json_timedelta == 'float':
            return {'type': 'number'}
        return {'type': 'string', 'format': 'duration'}

    def literal_schema(self, schema: core_schema.LiteralSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a literal value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        expected = [to_jsonable_python(v.value if isinstance(v, Enum) else v) for v in schema['expected']]

        result: dict[str, Any] = {}
        if len(expected) == 1:
            result['const'] = expected[0]
        else:
            result['enum'] = expected

        types = {type(e) for e in expected}
        if types == {str}:
            result['type'] = 'string'
        elif types == {int}:
            result['type'] = 'integer'
        elif types == {float}:
            result['type'] = 'number'
        elif types == {bool}:
            result['type'] = 'boolean'
        elif types == {list}:
            result['type'] = 'array'
        elif types == {type(None)}:
            result['type'] = 'null'
        return result

    def enum_schema(self, schema: core_schema.EnumSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches an Enum value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        enum_type = schema['cls']
        description = None if not enum_type.__doc__ else inspect.cleandoc(enum_type.__doc__)
        if (
            description == 'An enumeration.'
        ):  # This is the default value provided by enum.EnumMeta.__new__; don't use it
            description = None
        result: dict[str, Any] = {'title': enum_type.__name__, 'description': description}
        result = {k: v for k, v in result.items() if v is not None}

        expected = [to_jsonable_python(v.value) for v in schema['members']]

        result['enum'] = expected

        types = {type(e) for e in expected}
        if isinstance(enum_type, str) or types == {str}:
            result['type'] = 'string'
        elif isinstance(enum_type, int) or types == {int}:
            result['type'] = 'integer'
        elif isinstance(enum_type, float) or types == {float}:
            result['type'] = 'number'
        elif types == {bool}:
            result['type'] = 'boolean'
        elif types == {list}:
            result['type'] = 'array'

        return result

    def is_instance_schema(self, schema: core_schema.IsInstanceSchema) -> JsonSchemaValue:
        """Handles JSON schema generation for a core schema that checks if a value is an instance of a class.

        Unless overridden in a subclass, this raises an error.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.handle_invalid_for_json_schema(schema, f'core_schema.IsInstanceSchema ({schema["cls"]})')

    def is_subclass_schema(self, schema: core_schema.IsSubclassSchema) -> JsonSchemaValue:
        """Handles JSON schema generation for a core schema that checks if a value is a subclass of a class.

        For backwards compatibility with v1, this does not raise an error, but can be overridden to change this.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # Note: This is for compatibility with V1; you can override if you want different behavior.
        return {}

    def callable_schema(self, schema: core_schema.CallableSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a callable value.

        Unless overridden in a subclass, this raises an error.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.handle_invalid_for_json_schema(schema, 'core_schema.CallableSchema')

    def list_schema(self, schema: core_schema.ListSchema) -> JsonSchemaValue:
        """Returns a schema that matches a list schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        items_schema = {} if 'items_schema' not in schema else self.generate_inner(schema['items_schema'])
        json_schema = {'type': 'array', 'items': items_schema}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.array)
        return json_schema

    @deprecated('`tuple_positional_schema` is deprecated. Use `tuple_schema` instead.', category=None)
    @final
    def tuple_positional_schema(self, schema: core_schema.TupleSchema) -> JsonSchemaValue:
        """Replaced by `tuple_schema`."""
        warnings.warn(
            '`tuple_positional_schema` is deprecated. Use `tuple_schema` instead.',
            PydanticDeprecatedSince26,
            stacklevel=2,
        )
        return self.tuple_schema(schema)

    @deprecated('`tuple_variable_schema` is deprecated. Use `tuple_schema` instead.', category=None)
    @final
    def tuple_variable_schema(self, schema: core_schema.TupleSchema) -> JsonSchemaValue:
        """Replaced by `tuple_schema`."""
        warnings.warn(
            '`tuple_variable_schema` is deprecated. Use `tuple_schema` instead.',
            PydanticDeprecatedSince26,
            stacklevel=2,
        )
        return self.tuple_schema(schema)

    def tuple_schema(self, schema: core_schema.TupleSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a tuple schema e.g. `tuple[int,
        str, bool]` or `tuple[int, ...]`.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema: JsonSchemaValue = {'type': 'array'}
        if 'variadic_item_index' in schema:
            variadic_item_index = schema['variadic_item_index']
            if variadic_item_index > 0:
                json_schema['minItems'] = variadic_item_index
                json_schema['prefixItems'] = [
                    self.generate_inner(item) for item in schema['items_schema'][:variadic_item_index]
                ]
            if variadic_item_index + 1 == len(schema['items_schema']):
                # if the variadic item is the last item, then represent it faithfully
                json_schema['items'] = self.generate_inner(schema['items_schema'][variadic_item_index])
            else:
                # otherwise, 'items' represents the schema for the variadic
                # item plus the suffix, so just allow anything for simplicity
                # for now
                json_schema['items'] = True
        else:
            prefixItems = [self.generate_inner(item) for item in schema['items_schema']]
            if prefixItems:
                json_schema['prefixItems'] = prefixItems
            json_schema['minItems'] = len(prefixItems)
            json_schema['maxItems'] = len(prefixItems)
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.array)
        return json_schema

    def set_schema(self, schema: core_schema.SetSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a set schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self._common_set_schema(schema)

    def frozenset_schema(self, schema: core_schema.FrozenSetSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a frozenset schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self._common_set_schema(schema)

    def _common_set_schema(self, schema: core_schema.SetSchema | core_schema.FrozenSetSchema) -> JsonSchemaValue:
        items_schema = {} if 'items_schema' not in schema else self.generate_inner(schema['items_schema'])
        json_schema = {'type': 'array', 'uniqueItems': True, 'items': items_schema}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.array)
        return json_schema

    def generator_schema(self, schema: core_schema.GeneratorSchema) -> JsonSchemaValue:
        """Returns a JSON schema that represents the provided GeneratorSchema.

        Args:
            schema: The schema.

        Returns:
            The generated JSON schema.
        """
        items_schema = {} if 'items_schema' not in schema else self.generate_inner(schema['items_schema'])
        json_schema = {'type': 'array', 'items': items_schema}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.array)
        return json_schema

    def dict_schema(self, schema: core_schema.DictSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a dict schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema: JsonSchemaValue = {'type': 'object'}

        keys_schema = self.generate_inner(schema['keys_schema']).copy() if 'keys_schema' in schema else {}
        if '$ref' not in keys_schema:
            keys_pattern = keys_schema.pop('pattern', None)
            # Don't give a title to patternProperties/propertyNames:
            keys_schema.pop('title', None)
        else:
            # Here, we assume that if the keys schema is a definition reference,
            # it can't be a simple string core schema (and thus no pattern can exist).
            # However, this is only in practice (in theory, a definition reference core
            # schema could be generated for a simple string schema).
            # Note that we avoid calling `self.resolve_ref_schema`, as it might not exist yet.
            keys_pattern = None

        values_schema = self.generate_inner(schema['values_schema']).copy() if 'values_schema' in schema else {}
        # don't give a title to additionalProperties:
        values_schema.pop('title', None)

        if values_schema or keys_pattern is not None:
            if keys_pattern is None:
                json_schema['additionalProperties'] = values_schema
            else:
                json_schema['patternProperties'] = {keys_pattern: values_schema}
        else:  # for `dict[str, Any]`, we allow any key and any value, since `str` is the default key type
            json_schema['additionalProperties'] = True

        if (
            # The len check indicates that constraints are probably present:
            (keys_schema.get('type') == 'string' and len(keys_schema) > 1)
            # If this is a definition reference schema, it most likely has constraints:
            or '$ref' in keys_schema
        ):
            keys_schema.pop('type', None)
            json_schema['propertyNames'] = keys_schema

        self.update_with_validations(json_schema, schema, self.ValidationsMapping.object)
        return json_schema

    def function_before_schema(self, schema: core_schema.BeforeValidatorFunctionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a function-before schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if self.mode == 'validation' and (input_schema := schema.get('json_schema_input_schema')):
            return self.generate_inner(input_schema)

        return self.generate_inner(schema['schema'])

    def function_after_schema(self, schema: core_schema.AfterValidatorFunctionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a function-after schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def function_plain_schema(self, schema: core_schema.PlainValidatorFunctionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a function-plain schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if self.mode == 'validation' and (input_schema := schema.get('json_schema_input_schema')):
            return self.generate_inner(input_schema)

        return self.handle_invalid_for_json_schema(
            schema, f'core_schema.PlainValidatorFunctionSchema ({schema["function"]})'
        )

    def function_wrap_schema(self, schema: core_schema.WrapValidatorFunctionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a function-wrap schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if self.mode == 'validation' and (input_schema := schema.get('json_schema_input_schema')):
            return self.generate_inner(input_schema)

        return self.generate_inner(schema['schema'])

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema with a default value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = self.generate_inner(schema['schema'])

        default = self.get_default_value(schema)
        if default is NoDefault:
            return json_schema

        # we reflect the application of custom plain, no-info serializers to defaults for
        # JSON Schemas viewed in serialization mode:
        # TODO: improvements along with https://github.com/pydantic/pydantic/issues/8208
        if (
            self.mode == 'serialization'
            and (ser_schema := schema['schema'].get('serialization'))
            and (ser_func := ser_schema.get('function'))
            and ser_schema.get('type') == 'function-plain'
            and not ser_schema.get('info_arg')
            and not (default is None and ser_schema.get('when_used') in ('unless-none', 'json-unless-none'))
        ):
            try:
                default = ser_func(default)  # type: ignore
            except Exception:
                # It might be that the provided default needs to be validated (read: parsed) first
                # (assuming `validate_default` is enabled). However, we can't perform
                # such validation during JSON Schema generation so we don't support
                # this pattern for now.
                # (One example is when using `foo: ByteSize = '1MB'`, which validates and
                # serializes as an int. In this case, `ser_func` is `int` and `int('1MB')` fails).
                self.emit_warning(
                    'non-serializable-default',
                    f'Unable to serialize value {default!r} with the plain serializer; excluding default from JSON schema',
                )
                return json_schema

        try:
            encoded_default = self.encode_default(default)
        except pydantic_core.PydanticSerializationError:
            self.emit_warning(
                'non-serializable-default',
                f'Default value {default} is not JSON serializable; excluding default from JSON schema',
            )
            # Return the inner schema, as though there was no default
            return json_schema

        json_schema['default'] = encoded_default
        return json_schema

    def get_default_value(self, schema: core_schema.WithDefaultSchema) -> Any:
        """Get the default value to be used when generating a JSON Schema for a core schema with a default.

        The default implementation is to use the statically defined default value. This method can be overridden
        if you want to make use of the default factory.

        Args:
            schema: The `'with-default'` core schema.

        Returns:
            The default value to use, or [`NoDefault`][pydantic.json_schema.NoDefault] if no default
                value is available.
        """
        return schema.get('default', NoDefault)

    def nullable_schema(self, schema: core_schema.NullableSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that allows null values.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        null_schema = {'type': 'null'}
        inner_json_schema = self.generate_inner(schema['schema'])

        if inner_json_schema == null_schema:
            return null_schema
        else:
            # Thanks to the equality check against `null_schema` above, I think 'oneOf' would also be valid here;
            # I'll use 'anyOf' for now, but it could be changed it if it would work better with some external tooling
            return self.get_flattened_anyof([inner_json_schema, null_schema])

    def union_schema(self, schema: core_schema.UnionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that allows values matching any of the given schemas.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        generated: list[JsonSchemaValue] = []

        choices = schema['choices']
        for choice in choices:
            # choice will be a tuple if an explicit label was provided
            choice_schema = choice[0] if isinstance(choice, tuple) else choice
            try:
                generated.append(self.generate_inner(choice_schema))
            except PydanticOmit:
                continue
            except PydanticInvalidForJsonSchema as exc:
                self.emit_warning('skipped-choice', exc.message)
        if len(generated) == 1:
            return generated[0]
        return self.get_flattened_anyof(generated)

    def tagged_union_schema(self, schema: core_schema.TaggedUnionSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that allows values matching any of the given schemas, where
        the schemas are tagged with a discriminator field that indicates which schema should be used to validate
        the value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        generated: dict[str, JsonSchemaValue] = {}
        for k, v in schema['choices'].items():
            if isinstance(k, Enum):
                k = k.value
            try:
                # Use str(k) since keys must be strings for json; while not technically correct,
                # it's the closest that can be represented in valid JSON
                generated[str(k)] = self.generate_inner(v).copy()
            except PydanticOmit:
                continue
            except PydanticInvalidForJsonSchema as exc:
                self.emit_warning('skipped-choice', exc.message)

        one_of_choices = _deduplicate_schemas(generated.values())
        json_schema: JsonSchemaValue = {'oneOf': one_of_choices}

        # This reflects the v1 behavior; TODO: we should make it possible to exclude OpenAPI stuff from the JSON schema
        openapi_discriminator = self._extract_discriminator(schema, one_of_choices)
        if openapi_discriminator is not None:
            json_schema['discriminator'] = {
                'propertyName': openapi_discriminator,
                'mapping': {k: v.get('$ref', v) for k, v in generated.items()},
            }

        return json_schema

    def _extract_discriminator(
        self, schema: core_schema.TaggedUnionSchema, one_of_choices: list[JsonDict]
    ) -> str | None:
        """Extract a compatible OpenAPI discriminator from the schema and one_of choices that end up in the final
        schema."""
        openapi_discriminator: str | None = None

        if isinstance(schema['discriminator'], str):
            return schema['discriminator']

        if isinstance(schema['discriminator'], list):
            # If the discriminator is a single item list containing a string, that is equivalent to the string case
            if len(schema['discriminator']) == 1 and isinstance(schema['discriminator'][0], str):
                return schema['discriminator'][0]
            # When an alias is used that is different from the field name, the discriminator will be a list of single
            # str lists, one for the attribute and one for the actual alias. The logic here will work even if there is
            # more than one possible attribute, and looks for whether a single alias choice is present as a documented
            # property on all choices. If so, that property will be used as the OpenAPI discriminator.
            for alias_path in schema['discriminator']:
                if not isinstance(alias_path, list):
                    break  # this means that the discriminator is not a list of alias paths
                if len(alias_path) != 1:
                    continue  # this means that the "alias" does not represent a single field
                alias = alias_path[0]
                if not isinstance(alias, str):
                    continue  # this means that the "alias" does not represent a field
                alias_is_present_on_all_choices = True
                for choice in one_of_choices:
                    try:
                        choice = self.resolve_ref_schema(choice)
                    except RuntimeError as exc:
                        # TODO: fixme - this is a workaround for the fact that we can't always resolve refs
                        # for tagged union choices at this point in the schema gen process, we might need to do
                        # another pass at the end like we do for core schemas
                        self.emit_warning('skipped-discriminator', str(exc))
                        choice = {}
                    properties = choice.get('properties', {})
                    if not isinstance(properties, dict) or alias not in properties:
                        alias_is_present_on_all_choices = False
                        break
                if alias_is_present_on_all_choices:
                    openapi_discriminator = alias
                    break
        return openapi_discriminator

    def chain_schema(self, schema: core_schema.ChainSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a core_schema.ChainSchema.

        When generating a schema for validation, we return the validation JSON schema for the first step in the chain.
        For serialization, we return the serialization JSON schema for the last step in the chain.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        step_index = 0 if self.mode == 'validation' else -1  # use first step for validation, last for serialization
        return self.generate_inner(schema['steps'][step_index])

    def lax_or_strict_schema(self, schema: core_schema.LaxOrStrictSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that allows values matching either the lax schema or the
        strict schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # TODO: Need to read the default value off of model config or whatever
        use_strict = schema.get('strict', False)  # TODO: replace this default False
        # If your JSON schema fails to generate it is probably
        # because one of the following two branches failed.
        if use_strict:
            return self.generate_inner(schema['strict_schema'])
        else:
            return self.generate_inner(schema['lax_schema'])

    def json_or_python_schema(self, schema: core_schema.JsonOrPythonSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that allows values matching either the JSON schema or the
        Python schema.

        The JSON schema is used instead of the Python schema. If you want to use the Python schema, you should override
        this method.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['json_schema'])

    def typed_dict_schema(self, schema: core_schema.TypedDictSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a typed dict.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        total = schema.get('total', True)
        named_required_fields: list[tuple[str, bool, CoreSchemaField]] = [
            (name, self.field_is_required(field, total), field)
            for name, field in schema['fields'].items()
            if self.field_is_present(field)
        ]
        if self.mode == 'serialization':
            named_required_fields.extend(self._name_required_computed_fields(schema.get('computed_fields', [])))
        cls = schema.get('cls')
        config = _get_typed_dict_config(cls)
        with self._config_wrapper_stack.push(config):
            json_schema = self._named_required_fields_schema(named_required_fields)

        if cls is not None:
            self._update_class_schema(json_schema, cls, config)
        else:
            extra = config.get('extra')
            if extra == 'forbid':
                json_schema['additionalProperties'] = False
            elif extra == 'allow':
                json_schema['additionalProperties'] = True

        return json_schema

    @staticmethod
    def _name_required_computed_fields(
        computed_fields: list[ComputedField],
    ) -> list[tuple[str, bool, core_schema.ComputedField]]:
        return [(field['property_name'], True, field) for field in computed_fields]

    def _named_required_fields_schema(
        self, named_required_fields: Sequence[tuple[str, bool, CoreSchemaField]]
    ) -> JsonSchemaValue:
        properties: dict[str, JsonSchemaValue] = {}
        required_fields: list[str] = []
        for name, required, field in named_required_fields:
            if self.by_alias:
                name = self._get_alias_name(field, name)
            try:
                field_json_schema = self.generate_inner(field).copy()
            except PydanticOmit:
                continue
            if 'title' not in field_json_schema and self.field_title_should_be_set(field):
                title = self.get_title_from_name(name)
                field_json_schema['title'] = title
            field_json_schema = self.handle_ref_overrides(field_json_schema)
            properties[name] = field_json_schema
            if required:
                required_fields.append(name)

        json_schema = {'type': 'object', 'properties': properties}
        if required_fields:
            json_schema['required'] = required_fields
        return json_schema

    def _get_alias_name(self, field: CoreSchemaField, name: str) -> str:
        if field['type'] == 'computed-field':
            alias: Any = field.get('alias', name)
        elif self.mode == 'validation':
            alias = field.get('validation_alias', name)
        else:
            alias = field.get('serialization_alias', name)
        if isinstance(alias, str):
            name = alias
        elif isinstance(alias, list):
            alias = cast('list[str] | str', alias)
            for path in alias:
                if isinstance(path, list) and len(path) == 1 and isinstance(path[0], str):
                    # Use the first valid single-item string path; the code that constructs the alias array
                    # should ensure the first such item is what belongs in the JSON schema
                    name = path[0]
                    break
        else:
            assert_never(alias)
        return name

    def typed_dict_field_schema(self, schema: core_schema.TypedDictField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a typed dict field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def dataclass_field_schema(self, schema: core_schema.DataclassField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a dataclass field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def model_field_schema(self, schema: core_schema.ModelField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a model field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def computed_field_schema(self, schema: core_schema.ComputedField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a computed field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['return_schema'])

    def model_schema(self, schema: core_schema.ModelSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a model.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # We do not use schema['model'].model_json_schema() here
        # because it could lead to inconsistent refs handling, etc.
        cls = cast('type[BaseModel]', schema['cls'])
        config = cls.model_config

        with self._config_wrapper_stack.push(config):
            json_schema = self.generate_inner(schema['schema'])

        self._update_class_schema(json_schema, cls, config)

        return json_schema

    def _update_class_schema(self, json_schema: JsonSchemaValue, cls: type[Any], config: ConfigDict) -> None:
        """Update json_schema with the following, extracted from `config` and `cls`:

        * title
        * description
        * additional properties
        * json_schema_extra
        * deprecated

        Done in place, hence there's no return value as the original json_schema is mutated.
        No ref resolving is involved here, as that's not appropriate for simple updates.
        """
        from .main import BaseModel
        from .root_model import RootModel

        if (config_title := config.get('title')) is not None:
            json_schema.setdefault('title', config_title)
        elif model_title_generator := config.get('model_title_generator'):
            title = model_title_generator(cls)
            if not isinstance(title, str):
                raise TypeError(f'model_title_generator {model_title_generator} must return str, not {title.__class__}')
            json_schema.setdefault('title', title)
        if 'title' not in json_schema:
            json_schema['title'] = cls.__name__

        # BaseModel and dataclasses; don't use cls.__doc__ as it will contain the verbose class signature by default
        docstring = None if cls is BaseModel or dataclasses.is_dataclass(cls) else cls.__doc__

        if docstring:
            json_schema.setdefault('description', inspect.cleandoc(docstring))
        elif issubclass(cls, RootModel) and (root_description := cls.__pydantic_fields__['root'].description):
            json_schema.setdefault('description', root_description)

        extra = config.get('extra')
        if 'additionalProperties' not in json_schema:
            if extra == 'allow':
                json_schema['additionalProperties'] = True
            elif extra == 'forbid':
                json_schema['additionalProperties'] = False

        json_schema_extra = config.get('json_schema_extra')
        if issubclass(cls, BaseModel) and cls.__pydantic_root_model__:
            root_json_schema_extra = cls.model_fields['root'].json_schema_extra
            if json_schema_extra and root_json_schema_extra:
                raise ValueError(
                    '"model_config[\'json_schema_extra\']" and "Field.json_schema_extra" on "RootModel.root"'
                    ' field must not be set simultaneously'
                )
            if root_json_schema_extra:
                json_schema_extra = root_json_schema_extra

        if isinstance(json_schema_extra, (staticmethod, classmethod)):
            # In older versions of python, this is necessary to ensure staticmethod/classmethods are callable
            json_schema_extra = json_schema_extra.__get__(cls)

        if isinstance(json_schema_extra, dict):
            json_schema.update(json_schema_extra)
        elif callable(json_schema_extra):
            # FIXME: why are there type ignores here? We support two signatures for json_schema_extra callables...
            if len(inspect.signature(json_schema_extra).parameters) > 1:
                json_schema_extra(json_schema, cls)  # type: ignore
            else:
                json_schema_extra(json_schema)  # type: ignore
        elif json_schema_extra is not None:
            raise ValueError(
                f"model_config['json_schema_extra']={json_schema_extra} should be a dict, callable, or None"
            )

        if hasattr(cls, '__deprecated__'):
            json_schema['deprecated'] = True

    def resolve_ref_schema(self, json_schema: JsonSchemaValue) -> JsonSchemaValue:
        """Resolve a JsonSchemaValue to the non-ref schema if it is a $ref schema.

        Args:
            json_schema: The schema to resolve.

        Returns:
            The resolved schema.

        Raises:
            RuntimeError: If the schema reference can't be found in definitions.
        """
        while '$ref' in json_schema:
            ref = json_schema['$ref']
            schema_to_update = self.get_schema_from_definitions(JsonRef(ref))
            if schema_to_update is None:
                raise RuntimeError(f'Cannot update undefined schema for $ref={ref}')
            json_schema = schema_to_update
        return json_schema

    def model_fields_schema(self, schema: core_schema.ModelFieldsSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a model's fields.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        named_required_fields: list[tuple[str, bool, CoreSchemaField]] = [
            (name, self.field_is_required(field, total=True), field)
            for name, field in schema['fields'].items()
            if self.field_is_present(field)
        ]
        if self.mode == 'serialization':
            named_required_fields.extend(self._name_required_computed_fields(schema.get('computed_fields', [])))
        json_schema = self._named_required_fields_schema(named_required_fields)
        extras_schema = schema.get('extras_schema', None)
        if extras_schema is not None:
            schema_to_update = self.resolve_ref_schema(json_schema)
            schema_to_update['additionalProperties'] = self.generate_inner(extras_schema)
        return json_schema

    def field_is_present(self, field: CoreSchemaField) -> bool:
        """Whether the field should be included in the generated JSON schema.

        Args:
            field: The schema for the field itself.

        Returns:
            `True` if the field should be included in the generated JSON schema, `False` otherwise.
        """
        if self.mode == 'serialization':
            # If you still want to include the field in the generated JSON schema,
            # override this method and return True
            return not field.get('serialization_exclude')
        elif self.mode == 'validation':
            return True
        else:
            assert_never(self.mode)

    def field_is_required(
        self,
        field: core_schema.ModelField | core_schema.DataclassField | core_schema.TypedDictField,
        total: bool,
    ) -> bool:
        """Whether the field should be marked as required in the generated JSON schema.
        (Note that this is irrelevant if the field is not present in the JSON schema.).

        Args:
            field: The schema for the field itself.
            total: Only applies to `TypedDictField`s.
                Indicates if the `TypedDict` this field belongs to is total, in which case any fields that don't
                explicitly specify `required=False` are required.

        Returns:
            `True` if the field should be marked as required in the generated JSON schema, `False` otherwise.
        """
        if self.mode == 'serialization' and self._config.json_schema_serialization_defaults_required:
            return not field.get('serialization_exclude')
        else:
            if field['type'] == 'typed-dict-field':
                return field.get('required', total)
            else:
                return field['schema']['type'] != 'default'

    def dataclass_args_schema(self, schema: core_schema.DataclassArgsSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a dataclass's constructor arguments.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        named_required_fields: list[tuple[str, bool, CoreSchemaField]] = [
            (field['name'], self.field_is_required(field, total=True), field)
            for field in schema['fields']
            if self.field_is_present(field)
        ]
        if self.mode == 'serialization':
            named_required_fields.extend(self._name_required_computed_fields(schema.get('computed_fields', [])))
        return self._named_required_fields_schema(named_required_fields)

    def dataclass_schema(self, schema: core_schema.DataclassSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a dataclass.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        from ._internal._dataclasses import is_builtin_dataclass

        cls = schema['cls']
        config: ConfigDict = getattr(cls, '__pydantic_config__', cast('ConfigDict', {}))

        with self._config_wrapper_stack.push(config):
            json_schema = self.generate_inner(schema['schema']).copy()

        self._update_class_schema(json_schema, cls, config)

        # Dataclass-specific handling of description
        if is_builtin_dataclass(cls):
            # vanilla dataclass; don't use cls.__doc__ as it will contain the class signature by default
            description = None
        else:
            description = None if cls.__doc__ is None else inspect.cleandoc(cls.__doc__)
        if description:
            json_schema['description'] = description

        return json_schema

    def arguments_schema(self, schema: core_schema.ArgumentsSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's arguments.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        prefer_positional = schema.get('metadata', {}).get('pydantic_js_prefer_positional_arguments')

        arguments = schema['arguments_schema']
        kw_only_arguments = [a for a in arguments if a.get('mode') == 'keyword_only']
        kw_or_p_arguments = [a for a in arguments if a.get('mode') in {'positional_or_keyword', None}]
        p_only_arguments = [a for a in arguments if a.get('mode') == 'positional_only']
        var_args_schema = schema.get('var_args_schema')
        var_kwargs_schema = schema.get('var_kwargs_schema')

        if prefer_positional:
            positional_possible = not kw_only_arguments and not var_kwargs_schema
            if positional_possible:
                return self.p_arguments_schema(p_only_arguments + kw_or_p_arguments, var_args_schema)

        keyword_possible = not p_only_arguments and not var_args_schema
        if keyword_possible:
            return self.kw_arguments_schema(kw_or_p_arguments + kw_only_arguments, var_kwargs_schema)

        if not prefer_positional:
            positional_possible = not kw_only_arguments and not var_kwargs_schema
            if positional_possible:
                return self.p_arguments_schema(p_only_arguments + kw_or_p_arguments, var_args_schema)

        raise PydanticInvalidForJsonSchema(
            'Unable to generate JSON schema for arguments validator with positional-only and keyword-only arguments'
        )

    def kw_arguments_schema(
        self, arguments: list[core_schema.ArgumentsParameter], var_kwargs_schema: CoreSchema | None
    ) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's keyword arguments.

        Args:
            arguments: The core schema.

        Returns:
            The generated JSON schema.
        """
        properties: dict[str, JsonSchemaValue] = {}
        required: list[str] = []
        for argument in arguments:
            name = self.get_argument_name(argument)
            argument_schema = self.generate_inner(argument['schema']).copy()
            argument_schema['title'] = self.get_title_from_name(name)
            properties[name] = argument_schema

            if argument['schema']['type'] != 'default':
                # This assumes that if the argument has a default value,
                # the inner schema must be of type WithDefaultSchema.
                # I believe this is true, but I am not 100% sure
                required.append(name)

        json_schema: JsonSchemaValue = {'type': 'object', 'properties': properties}
        if required:
            json_schema['required'] = required

        if var_kwargs_schema:
            additional_properties_schema = self.generate_inner(var_kwargs_schema)
            if additional_properties_schema:
                json_schema['additionalProperties'] = additional_properties_schema
        else:
            json_schema['additionalProperties'] = False
        return json_schema

    def p_arguments_schema(
        self, arguments: list[core_schema.ArgumentsParameter], var_args_schema: CoreSchema | None
    ) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's positional arguments.

        Args:
            arguments: The core schema.

        Returns:
            The generated JSON schema.
        """
        prefix_items: list[JsonSchemaValue] = []
        min_items = 0

        for argument in arguments:
            name = self.get_argument_name(argument)

            argument_schema = self.generate_inner(argument['schema']).copy()
            argument_schema['title'] = self.get_title_from_name(name)
            prefix_items.append(argument_schema)

            if argument['schema']['type'] != 'default':
                # This assumes that if the argument has a default value,
                # the inner schema must be of type WithDefaultSchema.
                # I believe this is true, but I am not 100% sure
                min_items += 1

        json_schema: JsonSchemaValue = {'type': 'array'}
        if prefix_items:
            json_schema['prefixItems'] = prefix_items
        if min_items:
            json_schema['minItems'] = min_items

        if var_args_schema:
            items_schema = self.generate_inner(var_args_schema)
            if items_schema:
                json_schema['items'] = items_schema
        else:
            json_schema['maxItems'] = len(prefix_items)

        return json_schema

    def get_argument_name(self, argument: core_schema.ArgumentsParameter | core_schema.ArgumentsV3Parameter) -> str:
        """Retrieves the name of an argument.

        Args:
            argument: The core schema.

        Returns:
            The name of the argument.
        """
        name = argument['name']
        if self.by_alias:
            alias = argument.get('alias')
            if isinstance(alias, str):
                name = alias
            else:
                pass  # might want to do something else?
        return name

    def arguments_v3_schema(self, schema: core_schema.ArgumentsV3Schema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's arguments.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        arguments = schema['arguments_schema']
        properties: dict[str, JsonSchemaValue] = {}
        required: list[str] = []
        for argument in arguments:
            mode = argument.get('mode', 'positional_or_keyword')
            name = self.get_argument_name(argument)
            argument_schema = self.generate_inner(argument['schema']).copy()
            if mode == 'var_args':
                argument_schema = {'type': 'array', 'items': argument_schema}
            elif mode == 'var_kwargs_uniform':
                argument_schema = {'type': 'object', 'additionalProperties': argument_schema}

            argument_schema.setdefault('title', self.get_title_from_name(name))
            properties[name] = argument_schema

            if (
                (mode == 'var_kwargs_unpacked_typed_dict' and 'required' in argument_schema)
                or mode not in {'var_args', 'var_kwargs_uniform', 'var_kwargs_unpacked_typed_dict'}
                and argument['schema']['type'] != 'default'
            ):
                # This assumes that if the argument has a default value,
                # the inner schema must be of type WithDefaultSchema.
                # I believe this is true, but I am not 100% sure
                required.append(name)

        json_schema: JsonSchemaValue = {'type': 'object', 'properties': properties}
        if required:
            json_schema['required'] = required
        return json_schema

    def call_schema(self, schema: core_schema.CallSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function call.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['arguments_schema'])

    def custom_error_schema(self, schema: core_schema.CustomErrorSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a custom error.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def json_schema(self, schema: core_schema.JsonSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a JSON object.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        content_core_schema = schema.get('schema') or core_schema.any_schema()
        content_json_schema = self.generate_inner(content_core_schema)
        if self.mode == 'validation':
            return {'type': 'string', 'contentMediaType': 'application/json', 'contentSchema': content_json_schema}
        else:
            # self.mode == 'serialization'
            return content_json_schema

    def url_schema(self, schema: core_schema.UrlSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a URL.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = {'type': 'string', 'format': 'uri', 'minLength': 1}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.string)
        return json_schema

    def multi_host_url_schema(self, schema: core_schema.MultiHostUrlSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a URL that can be used with multiple hosts.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # Note: 'multi-host-uri' is a custom/pydantic-specific format, not part of the JSON Schema spec
        json_schema = {'type': 'string', 'format': 'multi-host-uri', 'minLength': 1}
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.string)
        return json_schema

    def uuid_schema(self, schema: core_schema.UuidSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a UUID.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'string', 'format': 'uuid'}

    def definitions_schema(self, schema: core_schema.DefinitionsSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a JSON object with definitions.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        for definition in schema['definitions']:
            try:
                self.generate_inner(definition)
            except PydanticInvalidForJsonSchema as e:
                core_ref: CoreRef = CoreRef(definition['ref'])  # type: ignore
                self._core_defs_invalid_for_json_schema[self.get_defs_ref((core_ref, self.mode))] = e
                continue
        return self.generate_inner(schema['schema'])

    def definition_ref_schema(self, schema: core_schema.DefinitionReferenceSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that references a definition.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        core_ref = CoreRef(schema['schema_ref'])
        _, ref_json_schema = self.get_cache_defs_ref_schema(core_ref)
        return ref_json_schema

    def ser_schema(
        self, schema: core_schema.SerSchema | core_schema.IncExSeqSerSchema | core_schema.IncExDictSerSchema
    ) -> JsonSchemaValue | None:
        """Generates a JSON schema that matches a schema that defines a serialized object.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        schema_type = schema['type']
        if schema_type == 'function-plain' or schema_type == 'function-wrap':
            # PlainSerializerFunctionSerSchema or WrapSerializerFunctionSerSchema
            return_schema = schema.get('return_schema')
            if return_schema is not None:
                return self.generate_inner(return_schema)
        elif schema_type == 'format' or schema_type == 'to-string':
            # FormatSerSchema or ToStringSerSchema
            return self.str_schema(core_schema.str_schema())
        elif schema['type'] == 'model':
            # ModelSerSchema
            return self.generate_inner(schema['schema'])
        return None

    def complex_schema(self, schema: core_schema.ComplexSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a complex number.

        JSON has no standard way to represent complex numbers. Complex number is not a numeric
        type. Here we represent complex number as strings following the rule defined by Python.
        For instance, '1+2j' is an accepted complex string. Details can be found in
        [Python's `complex` documentation][complex].

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return {'type': 'string'}

    # ### Utility methods

    def get_title_from_name(self, name: str) -> str:
        """Retrieves a title from a name.

        Args:
            name: The name to retrieve a title from.

        Returns:
            The title.
        """
        return name.title().replace('_', ' ').strip()

    def field_title_should_be_set(self, schema: CoreSchemaOrField) -> bool:
        """Returns true if a field with the given schema should have a title set based on the field name.

        Intuitively, we want this to return true for schemas that wouldn't otherwise provide their own title
        (e.g., int, float, str), and false for those that would (e.g., BaseModel subclasses).

        Args:
            schema: The schema to check.

        Returns:
            `True` if the field should have a title set, `False` otherwise.
        """
        if _core_utils.is_core_schema_field(schema):
            if schema['type'] == 'computed-field':
                field_schema = schema['return_schema']
            else:
                field_schema = schema['schema']
            return self.field_title_should_be_set(field_schema)

        elif _core_utils.is_core_schema(schema):
            if schema.get('ref'):  # things with refs, such as models and enums, should not have titles set
                return False
            if schema['type'] in {'default', 'nullable', 'definitions'}:
                return self.field_title_should_be_set(schema['schema'])  # type: ignore[typeddict-item]
            if _core_utils.is_function_with_inner_schema(schema):
                return self.field_title_should_be_set(schema['schema'])
            if schema['type'] == 'definition-ref':
                # Referenced schemas should not have titles set for the same reason
                # schemas with refs should not
                return False
            return True  # anything else should have title set

        else:
            raise PydanticInvalidForJsonSchema(f'Unexpected schema type: schema={schema}')  # pragma: no cover

    def normalize_name(self, name: str) -> str:
        """Normalizes a name to be used as a key in a dictionary.

        Args:
            name: The name to normalize.

        Returns:
            The normalized name.
        """
        return re.sub(r'[^a-zA-Z0-9.\-_]', '_', name).replace('.', '__')

    def get_defs_ref(self, core_mode_ref: CoreModeRef) -> DefsRef:
        """Override this method to change the way that definitions keys are generated from a core reference.

        Args:
            core_mode_ref: The core reference.

        Returns:
            The definitions key.
        """
        # Split the core ref into "components"; generic origins and arguments are each separate components
        core_ref, mode = core_mode_ref
        components = re.split(r'([\][,])', core_ref)
        # Remove IDs from each component
        components = [x.rsplit(':', 1)[0] for x in components]
        core_ref_no_id = ''.join(components)
        # Remove everything before the last period from each "component"
        components = [re.sub(r'(?:[^.[\]]+\.)+((?:[^.[\]]+))', r'\1', x) for x in components]
        short_ref = ''.join(components)

        mode_title = _MODE_TITLE_MAPPING[mode]

        # It is important that the generated defs_ref values be such that at least one choice will not
        # be generated for any other core_ref. Currently, this should be the case because we include
        # the id of the source type in the core_ref
        name = DefsRef(self.normalize_name(short_ref))
        name_mode = DefsRef(self.normalize_name(short_ref) + f'-{mode_title}')
        module_qualname = DefsRef(self.normalize_name(core_ref_no_id))
        module_qualname_mode = DefsRef(f'{module_qualname}-{mode_title}')
        module_qualname_id = DefsRef(self.normalize_name(core_ref))
        occurrence_index = self._collision_index.get(module_qualname_id)
        if occurrence_index is None:
            self._collision_counter[module_qualname] += 1
            occurrence_index = self._collision_index[module_qualname_id] = self._collision_counter[module_qualname]

        module_qualname_occurrence = DefsRef(f'{module_qualname}__{occurrence_index}')
        module_qualname_occurrence_mode = DefsRef(f'{module_qualname_mode}__{occurrence_index}')

        self._prioritized_defsref_choices[module_qualname_occurrence_mode] = [
            name,
            name_mode,
            module_qualname,
            module_qualname_mode,
            module_qualname_occurrence,
            module_qualname_occurrence_mode,
        ]

        return module_qualname_occurrence_mode

    def get_cache_defs_ref_schema(self, core_ref: CoreRef) -> tuple[DefsRef, JsonSchemaValue]:
        """This method wraps the get_defs_ref method with some cache-lookup/population logic,
        and returns both the produced defs_ref and the JSON schema that will refer to the right definition.

        Args:
            core_ref: The core reference to get the definitions reference for.

        Returns:
            A tuple of the definitions reference and the JSON schema that will refer to it.
        """
        core_mode_ref = (core_ref, self.mode)
        maybe_defs_ref = self.core_to_defs_refs.get(core_mode_ref)
        if maybe_defs_ref is not None:
            json_ref = self.core_to_json_refs[core_mode_ref]
            return maybe_defs_ref, {'$ref': json_ref}

        defs_ref = self.get_defs_ref(core_mode_ref)

        # populate the ref translation mappings
        self.core_to_defs_refs[core_mode_ref] = defs_ref
        self.defs_to_core_refs[defs_ref] = core_mode_ref

        json_ref = JsonRef(self.ref_template.format(model=defs_ref))
        self.core_to_json_refs[core_mode_ref] = json_ref
        self.json_to_defs_refs[json_ref] = defs_ref
        ref_json_schema = {'$ref': json_ref}
        return defs_ref, ref_json_schema

    def handle_ref_overrides(self, json_schema: JsonSchemaValue) -> JsonSchemaValue:
        """Remove any sibling keys that are redundant with the referenced schema.

        Args:
            json_schema: The schema to remove redundant sibling keys from.

        Returns:
            The schema with redundant sibling keys removed.
        """
        if '$ref' in json_schema:
            # prevent modifications to the input; this copy may be safe to drop if there is significant overhead
            json_schema = json_schema.copy()

            referenced_json_schema = self.get_schema_from_definitions(JsonRef(json_schema['$ref']))
            if referenced_json_schema is None:
                # This can happen when building schemas for models with not-yet-defined references.
                # It may be a good idea to do a recursive pass at the end of the generation to remove
                # any redundant override keys.
                return json_schema
            for k, v in list(json_schema.items()):
                if k == '$ref':
                    continue
                if k in referenced_json_schema and referenced_json_schema[k] == v:
                    del json_schema[k]  # redundant key

        return json_schema

    def get_schema_from_definitions(self, json_ref: JsonRef) -> JsonSchemaValue | None:
        try:
            def_ref = self.json_to_defs_refs[json_ref]
            if def_ref in self._core_defs_invalid_for_json_schema:
                raise self._core_defs_invalid_for_json_schema[def_ref]
            return self.definitions.get(def_ref, None)
        except KeyError:
            if json_ref.startswith(('http://', 'https://')):
                return None
            raise

    def encode_default(self, dft: Any) -> Any:
        """Encode a default value to a JSON-serializable value.

        This is used to encode default values for fields in the generated JSON schema.

        Args:
            dft: The default value to encode.

        Returns:
            The encoded default value.
        """
        from .type_adapter import TypeAdapter, _type_has_config

        config = self._config
        try:
            default = (
                dft
                if _type_has_config(type(dft))
                else TypeAdapter(type(dft), config=config.config_dict).dump_python(
                    dft, by_alias=self.by_alias, mode='json'
                )
            )
        except PydanticSchemaGenerationError:
            raise pydantic_core.PydanticSerializationError(f'Unable to encode default value {dft}')

        return pydantic_core.to_jsonable_python(
            default, timedelta_mode=config.ser_json_timedelta, bytes_mode=config.ser_json_bytes, by_alias=self.by_alias
        )

    def update_with_validations(
        self, json_schema: JsonSchemaValue, core_schema: CoreSchema, mapping: dict[str, str]
    ) -> None:
        """Update the json_schema with the corresponding validations specified in the core_schema,
        using the provided mapping to translate keys in core_schema to the appropriate keys for a JSON schema.

        Args:
            json_schema: The JSON schema to update.
            core_schema: The core schema to get the validations from.
            mapping: A mapping from core_schema attribute names to the corresponding JSON schema attribute names.
        """
        for core_key, json_schema_key in mapping.items():
            if core_key in core_schema:
                json_schema[json_schema_key] = core_schema[core_key]

    class ValidationsMapping:
        """This class just contains mappings from core_schema attribute names to the corresponding
        JSON schema attribute names. While I suspect it is unlikely to be necessary, you can in
        principle override this class in a subclass of GenerateJsonSchema (by inheriting from
        GenerateJsonSchema.ValidationsMapping) to change these mappings.
        """

        numeric = {
            'multiple_of': 'multipleOf',
            'le': 'maximum',
            'ge': 'minimum',
            'lt': 'exclusiveMaximum',
            'gt': 'exclusiveMinimum',
        }
        bytes = {
            'min_length': 'minLength',
            'max_length': 'maxLength',
        }
        string = {
            'min_length': 'minLength',
            'max_length': 'maxLength',
            'pattern': 'pattern',
        }
        array = {
            'min_length': 'minItems',
            'max_length': 'maxItems',
        }
        object = {
            'min_length': 'minProperties',
            'max_length': 'maxProperties',
        }

    def get_flattened_anyof(self, schemas: list[JsonSchemaValue]) -> JsonSchemaValue:
        members = []
        for schema in schemas:
            if len(schema) == 1 and 'anyOf' in schema:
                members.extend(schema['anyOf'])
            else:
                members.append(schema)
        members = _deduplicate_schemas(members)
        if len(members) == 1:
            return members[0]
        return {'anyOf': members}

    def get_json_ref_counts(self, json_schema: JsonSchemaValue) -> dict[JsonRef, int]:
        """Get all values corresponding to the key '$ref' anywhere in the json_schema."""
        json_refs: dict[JsonRef, int] = Counter()

        def _add_json_refs(schema: Any) -> None:
            if isinstance(schema, dict):
                if '$ref' in schema:
                    json_ref = JsonRef(schema['$ref'])
                    if not isinstance(json_ref, str):
                        return  # in this case, '$ref' might have been the name of a property
                    already_visited = json_ref in json_refs
                    json_refs[json_ref] += 1
                    if already_visited:
                        return  # prevent recursion on a definition that was already visited
                    try:
                        defs_ref = self.json_to_defs_refs[json_ref]
                        if defs_ref in self._core_defs_invalid_for_json_schema:
                            raise self._core_defs_invalid_for_json_schema[defs_ref]
                        _add_json_refs(self.definitions[defs_ref])
                    except KeyError:
                        if not json_ref.startswith(('http://', 'https://')):
                            raise

                for k, v in schema.items():
                    if k == 'examples' and isinstance(v, list):
                        # Skip examples that may contain arbitrary values and references
                        # (see the comment in `_get_all_json_refs` for more details).
                        continue
                    _add_json_refs(v)
            elif isinstance(schema, list):
                for v in schema:
                    _add_json_refs(v)

        _add_json_refs(json_schema)
        return json_refs

    def handle_invalid_for_json_schema(self, schema: CoreSchemaOrField, error_info: str) -> JsonSchemaValue:
        raise PydanticInvalidForJsonSchema(f'Cannot generate a JsonSchema for {error_info}')

    def emit_warning(self, kind: JsonSchemaWarningKind, detail: str) -> None:
        """This method simply emits PydanticJsonSchemaWarnings based on handling in the `warning_message` method."""
        message = self.render_warning_message(kind, detail)
        if message is not None:
            warnings.warn(message, PydanticJsonSchemaWarning)

    def render_warning_message(self, kind: JsonSchemaWarningKind, detail: str) -> str | None:
        """This method is responsible for ignoring warnings as desired, and for formatting the warning messages.

        You can override the value of `ignored_warning_kinds` in a subclass of GenerateJsonSchema
        to modify what warnings are generated. If you want more control, you can override this method;
        just return None in situations where you don't want warnings to be emitted.

        Args:
            kind: The kind of warning to render. It can be one of the following:

                - 'skipped-choice': A choice field was skipped because it had no valid choices.
                - 'non-serializable-default': A default value was skipped because it was not JSON-serializable.
            detail: A string with additional details about the warning.

        Returns:
            The formatted warning message, or `None` if no warning should be emitted.
        """
        if kind in self.ignored_warning_kinds:
            return None
        return f'{detail} [{kind}]'

    def _build_definitions_remapping(self) -> _DefinitionsRemapping:
        defs_to_json: dict[DefsRef, JsonRef] = {}
        for defs_refs in self._prioritized_defsref_choices.values():
            for defs_ref in defs_refs:
                json_ref = JsonRef(self.ref_template.format(model=defs_ref))
                defs_to_json[defs_ref] = json_ref

        return _DefinitionsRemapping.from_prioritized_choices(
            self._prioritized_defsref_choices, defs_to_json, self.definitions
        )

    def _garbage_collect_definitions(self, schema: JsonSchemaValue) -> None:
        visited_defs_refs: set[DefsRef] = set()
        unvisited_json_refs = _get_all_json_refs(schema)
        while unvisited_json_refs:
            next_json_ref = unvisited_json_refs.pop()
            try:
                next_defs_ref = self.json_to_defs_refs[next_json_ref]
                if next_defs_ref in visited_defs_refs:
                    continue
                visited_defs_refs.add(next_defs_ref)
                unvisited_json_refs.update(_get_all_json_refs(self.definitions[next_defs_ref]))
            except KeyError:
                if not next_json_ref.startswith(('http://', 'https://')):
                    raise

        self.definitions = {k: v for k, v in self.definitions.items() if k in visited_defs_refs}


# ##### Start JSON Schema Generation Functions #####


def model_json_schema(
    cls: type[BaseModel] | type[PydanticDataclass],
    by_alias: bool = True,
    ref_template: str = DEFAULT_REF_TEMPLATE,
    schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
    mode: JsonSchemaMode = 'validation',
) -> dict[str, Any]:
    """Utility function to generate a JSON Schema for a model.

    Args:
        cls: The model class to generate a JSON Schema for.
        by_alias: If `True` (the default), fields will be serialized according to their alias.
            If `False`, fields will be serialized according to their attribute name.
        ref_template: The template to use for generating JSON Schema references.
        schema_generator: The class to use for generating the JSON Schema.
        mode: The mode to use for generating the JSON Schema. It can be one of the following:

            - 'validation': Generate a JSON Schema for validating data.
            - 'serialization': Generate a JSON Schema for serializing data.

    Returns:
        The generated JSON Schema.
    """
    from .main import BaseModel

    schema_generator_instance = schema_generator(by_alias=by_alias, ref_template=ref_template)

    if isinstance(cls.__pydantic_core_schema__, _mock_val_ser.MockCoreSchema):
        cls.__pydantic_core_schema__.rebuild()

    if cls is BaseModel:
        raise AttributeError('model_json_schema() must be called on a subclass of BaseModel, not BaseModel itself.')

    assert not isinstance(cls.__pydantic_core_schema__, _mock_val_ser.MockCoreSchema), 'this is a bug! please report it'
    return schema_generator_instance.generate(cls.__pydantic_core_schema__, mode=mode)


def models_json_schema(
    models: Sequence[tuple[type[BaseModel] | type[PydanticDataclass], JsonSchemaMode]],
    *,
    by_alias: bool = True,
    title: str | None = None,
    description: str | None = None,
    ref_template: str = DEFAULT_REF_TEMPLATE,
    schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
) -> tuple[dict[tuple[type[BaseModel] | type[PydanticDataclass], JsonSchemaMode], JsonSchemaValue], JsonSchemaValue]:
    """Utility function to generate a JSON Schema for multiple models.

    Args:
        models: A sequence of tuples of the form (model, mode).
        by_alias: Whether field aliases should be used as keys in the generated JSON Schema.
        title: The title of the generated JSON Schema.
        description: The description of the generated JSON Schema.
        ref_template: The reference template to use for generating JSON Schema references.
        schema_generator: The schema generator to use for generating the JSON Schema.

    Returns:
        A tuple where:
            - The first element is a dictionary whose keys are tuples of JSON schema key type and JSON mode, and
                whose values are the JSON schema corresponding to that pair of inputs. (These schemas may have
                JsonRef references to definitions that are defined in the second returned element.)
            - The second element is a JSON schema containing all definitions referenced in the first returned
                    element, along with the optional title and description keys.
    """
    for cls, _ in models:
        if isinstance(cls.__pydantic_core_schema__, _mock_val_ser.MockCoreSchema):
            cls.__pydantic_core_schema__.rebuild()

    instance = schema_generator(by_alias=by_alias, ref_template=ref_template)
    inputs: list[tuple[type[BaseModel] | type[PydanticDataclass], JsonSchemaMode, CoreSchema]] = [
        (m, mode, m.__pydantic_core_schema__) for m, mode in models
    ]
    json_schemas_map, definitions = instance.generate_definitions(inputs)

    json_schema: dict[str, Any] = {}
    if definitions:
        json_schema['$defs'] = definitions
    if title:
        json_schema['title'] = title
    if description:
        json_schema['description'] = description

    return json_schemas_map, json_schema


# ##### End JSON Schema Generation Functions #####


_HashableJsonValue: TypeAlias = Union[
    int, float, str, bool, None, tuple['_HashableJsonValue', ...], tuple[tuple[str, '_HashableJsonValue'], ...]
]


def _deduplicate_schemas(schemas: Iterable[JsonDict]) -> list[JsonDict]:
    return list({_make_json_hashable(schema): schema for schema in schemas}.values())


def _make_json_hashable(value: JsonValue) -> _HashableJsonValue:
    if isinstance(value, dict):
        return tuple(sorted((k, _make_json_hashable(v)) for k, v in value.items()))
    elif isinstance(value, list):
        return tuple(_make_json_hashable(v) for v in value)
    else:
        return value


@dataclasses.dataclass(**_internal_dataclass.slots_true)
class WithJsonSchema:
    """!!! abstract "Usage Documentation"
        [`WithJsonSchema` Annotation](../concepts/json_schema.md#withjsonschema-annotation)

    Add this as an annotation on a field to override the (base) JSON schema that would be generated for that field.
    This provides a way to set a JSON schema for types that would otherwise raise errors when producing a JSON schema,
    such as Callable, or types that have an is-instance core schema, without needing to go so far as creating a
    custom subclass of pydantic.json_schema.GenerateJsonSchema.
    Note that any _modifications_ to the schema that would normally be made (such as setting the title for model fields)
    will still be performed.

    If `mode` is set this will only apply to that schema generation mode, allowing you
    to set different json schemas for validation and serialization.
    """

    json_schema: JsonSchemaValue | None
    mode: Literal['validation', 'serialization'] | None = None

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        mode = self.mode or handler.mode
        if mode != handler.mode:
            return handler(core_schema)
        if self.json_schema is None:
            # This exception is handled in pydantic.json_schema.GenerateJsonSchema._named_required_fields_schema
            raise PydanticOmit
        else:
            return self.json_schema.copy()

    def __hash__(self) -> int:
        return hash(type(self.mode))


class Examples:
    """Add examples to a JSON schema.

    If the JSON Schema already contains examples, the provided examples
    will be appended.

    If `mode` is set this will only apply to that schema generation mode,
    allowing you to add different examples for validation and serialization.
    """

    @overload
    @deprecated('Using a dict for `examples` is deprecated since v2.9 and will be removed in v3.0. Use a list instead.')
    def __init__(
        self, examples: dict[str, Any], mode: Literal['validation', 'serialization'] | None = None
    ) -> None: ...

    @overload
    def __init__(self, examples: list[Any], mode: Literal['validation', 'serialization'] | None = None) -> None: ...

    def __init__(
        self, examples: dict[str, Any] | list[Any], mode: Literal['validation', 'serialization'] | None = None
    ) -> None:
        if isinstance(examples, dict):
            warnings.warn(
                'Using a dict for `examples` is deprecated, use a list instead.',
                PydanticDeprecatedSince29,
                stacklevel=2,
            )
        self.examples = examples
        self.mode = mode

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        mode = self.mode or handler.mode
        json_schema = handler(core_schema)
        if mode != handler.mode:
            return json_schema
        examples = json_schema.get('examples')
        if examples is None:
            json_schema['examples'] = to_jsonable_python(self.examples)
        if isinstance(examples, dict):
            if isinstance(self.examples, list):
                warnings.warn(
                    'Updating existing JSON Schema examples of type dict with examples of type list. '
                    'Only the existing examples values will be retained. Note that dict support for '
                    'examples is deprecated and will be removed in v3.0.',
                    UserWarning,
                )
                json_schema['examples'] = to_jsonable_python(
                    [ex for value in examples.values() for ex in value] + self.examples
                )
            else:
                json_schema['examples'] = to_jsonable_python({**examples, **self.examples})
        if isinstance(examples, list):
            if isinstance(self.examples, list):
                json_schema['examples'] = to_jsonable_python(examples + self.examples)
            elif isinstance(self.examples, dict):
                warnings.warn(
                    'Updating existing JSON Schema examples of type list with examples of type dict. '
                    'Only the examples values will be retained. Note that dict support for '
                    'examples is deprecated and will be removed in v3.0.',
                    UserWarning,
                )
                json_schema['examples'] = to_jsonable_python(
                    examples + [ex for value in self.examples.values() for ex in value]
                )

        return json_schema

    def __hash__(self) -> int:
        return hash(type(self.mode))


def _get_all_json_refs(item: Any) -> set[JsonRef]:
    """Get all the definitions references from a JSON schema."""
    refs: set[JsonRef] = set()
    stack = [item]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key == 'examples' and isinstance(value, list):
                    # Skip examples that may contain arbitrary values and references
                    # (e.g. `{"examples": [{"$ref": "..."}]}`). Note: checking for value
                    # of type list is necessary to avoid skipping valid portions of the schema,
                    # for instance when "examples" is used as a property key. A more robust solution
                    # could be found, but would require more advanced JSON Schema parsing logic.
                    continue
                if key == '$ref' and isinstance(value, str):
                    refs.add(JsonRef(value))
                elif isinstance(value, dict):
                    stack.append(value)
                elif isinstance(value, list):
                    stack.extend(value)
        elif isinstance(current, list):
            stack.extend(current)

    return refs


AnyType = TypeVar('AnyType')

if TYPE_CHECKING:
    SkipJsonSchema = Annotated[AnyType, ...]
else:

    @dataclasses.dataclass(**_internal_dataclass.slots_true)
    class SkipJsonSchema:
        """!!! abstract "Usage Documentation"
            [`SkipJsonSchema` Annotation](../concepts/json_schema.md#skipjsonschema-annotation)

        Add this as an annotation on a field to skip generating a JSON schema for that field.

        Example:
            ```python
            from pprint import pprint
            from typing import Union

            from pydantic import BaseModel
            from pydantic.json_schema import SkipJsonSchema

            class Model(BaseModel):
                a: Union[int, None] = None  # (1)!
                b: Union[int, SkipJsonSchema[None]] = None  # (2)!
                c: SkipJsonSchema[Union[int, None]] = None  # (3)!

            pprint(Model.model_json_schema())
            '''
            {
                'properties': {
                    'a': {
                        'anyOf': [
                            {'type': 'integer'},
                            {'type': 'null'}
                        ],
                        'default': None,
                        'title': 'A'
                    },
                    'b': {
                        'default': None,
                        'title': 'B',
                        'type': 'integer'
                    }
                },
                'title': 'Model',
                'type': 'object'
            }
            '''
            ```

            1. The integer and null types are both included in the schema for `a`.
            2. The integer type is the only type included in the schema for `b`.
            3. The entirety of the `c` field is omitted from the schema.
        """

        def __class_getitem__(cls, item: AnyType) -> AnyType:
            return Annotated[item, cls()]

        def __get_pydantic_json_schema__(
            self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            raise PydanticOmit

        def __hash__(self) -> int:
            return hash(type(self))


def _get_typed_dict_config(cls: type[Any] | None) -> ConfigDict:
    if cls is not None:
        try:
            return _decorators.get_attribute_from_bases(cls, '__pydantic_config__')
        except AttributeError:
            pass
    return {}