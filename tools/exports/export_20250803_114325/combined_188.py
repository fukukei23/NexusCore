
# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\transports\grpc.py ===
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
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content

from .base import DEFAULT_CLIENT_INFO, CacheServiceTransport


class CacheServiceGrpcTransport(CacheServiceTransport):
    """gRPC backend transport for CacheService.

    API for managing cache of content (CachedContent resources)
    that can be used in GenerativeService requests. This way
    generate content requests can benefit from preprocessing work
    being done earlier, possibly lowering their computational cost.
    It is intended to be used with large contexts.

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
    def list_cached_contents(
        self,
    ) -> Callable[
        [cache_service.ListCachedContentsRequest],
        cache_service.ListCachedContentsResponse,
    ]:
        r"""Return a callable for the list cached contents method over gRPC.

        Lists CachedContents.

        Returns:
            Callable[[~.ListCachedContentsRequest],
                    ~.ListCachedContentsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_cached_contents" not in self._stubs:
            self._stubs["list_cached_contents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/ListCachedContents",
                request_serializer=cache_service.ListCachedContentsRequest.serialize,
                response_deserializer=cache_service.ListCachedContentsResponse.deserialize,
            )
        return self._stubs["list_cached_contents"]

    @property
    def create_cached_content(
        self,
    ) -> Callable[
        [cache_service.CreateCachedContentRequest], gag_cached_content.CachedContent
    ]:
        r"""Return a callable for the create cached content method over gRPC.

        Creates CachedContent resource.

        Returns:
            Callable[[~.CreateCachedContentRequest],
                    ~.CachedContent]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_cached_content" not in self._stubs:
            self._stubs["create_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/CreateCachedContent",
                request_serializer=cache_service.CreateCachedContentRequest.serialize,
                response_deserializer=gag_cached_content.CachedContent.deserialize,
            )
        return self._stubs["create_cached_content"]

    @property
    def get_cached_content(
        self,
    ) -> Callable[
        [cache_service.GetCachedContentRequest], cached_content.CachedContent
    ]:
        r"""Return a callable for the get cached content method over gRPC.

        Reads CachedContent resource.

        Returns:
            Callable[[~.GetCachedContentRequest],
                    ~.CachedContent]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_cached_content" not in self._stubs:
            self._stubs["get_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/GetCachedContent",
                request_serializer=cache_service.GetCachedContentRequest.serialize,
                response_deserializer=cached_content.CachedContent.deserialize,
            )
        return self._stubs["get_cached_content"]

    @property
    def update_cached_content(
        self,
    ) -> Callable[
        [cache_service.UpdateCachedContentRequest], gag_cached_content.CachedContent
    ]:
        r"""Return a callable for the update cached content method over gRPC.

        Updates CachedContent resource (only expiration is
        updatable).

        Returns:
            Callable[[~.UpdateCachedContentRequest],
                    ~.CachedContent]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_cached_content" not in self._stubs:
            self._stubs["update_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/UpdateCachedContent",
                request_serializer=cache_service.UpdateCachedContentRequest.serialize,
                response_deserializer=gag_cached_content.CachedContent.deserialize,
            )
        return self._stubs["update_cached_content"]

    @property
    def delete_cached_content(
        self,
    ) -> Callable[[cache_service.DeleteCachedContentRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete cached content method over gRPC.

        Deletes CachedContent resource.

        Returns:
            Callable[[~.DeleteCachedContentRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_cached_content" not in self._stubs:
            self._stubs["delete_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/DeleteCachedContent",
                request_serializer=cache_service.DeleteCachedContentRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_cached_content"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("CacheServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_runtime.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Check presence of installed packages at runtime."""

import importlib.metadata
import os
import platform
import sys
import warnings
from typing import Any, Dict

from .. import __version__, constants


_PY_VERSION: str = sys.version.split()[0].rstrip("+")

_package_versions = {}

_CANDIDATES = {
    "aiohttp": {"aiohttp"},
    "fastai": {"fastai"},
    "fastapi": {"fastapi"},
    "fastcore": {"fastcore"},
    "gradio": {"gradio"},
    "graphviz": {"graphviz"},
    "hf_transfer": {"hf_transfer"},
    "hf_xet": {"hf_xet"},
    "jinja": {"Jinja2"},
    "keras": {"keras"},
    "numpy": {"numpy"},
    "pillow": {"Pillow"},
    "pydantic": {"pydantic"},
    "pydot": {"pydot"},
    "safetensors": {"safetensors"},
    "tensorboard": {"tensorboardX"},
    "tensorflow": (
        "tensorflow",
        "tensorflow-cpu",
        "tensorflow-gpu",
        "tf-nightly",
        "tf-nightly-cpu",
        "tf-nightly-gpu",
        "intel-tensorflow",
        "intel-tensorflow-avx512",
        "tensorflow-rocm",
        "tensorflow-macos",
    ),
    "torch": {"torch"},
}

# Check once at runtime
for candidate_name, package_names in _CANDIDATES.items():
    _package_versions[candidate_name] = "N/A"
    for name in package_names:
        try:
            _package_versions[candidate_name] = importlib.metadata.version(name)
            break
        except importlib.metadata.PackageNotFoundError:
            pass


def _get_version(package_name: str) -> str:
    return _package_versions.get(package_name, "N/A")


def is_package_available(package_name: str) -> bool:
    return _get_version(package_name) != "N/A"


# Python
def get_python_version() -> str:
    return _PY_VERSION


# Huggingface Hub
def get_hf_hub_version() -> str:
    return __version__


# aiohttp
def is_aiohttp_available() -> bool:
    return is_package_available("aiohttp")


def get_aiohttp_version() -> str:
    return _get_version("aiohttp")


# FastAI
def is_fastai_available() -> bool:
    return is_package_available("fastai")


def get_fastai_version() -> str:
    return _get_version("fastai")


# FastAPI
def is_fastapi_available() -> bool:
    return is_package_available("fastapi")


def get_fastapi_version() -> str:
    return _get_version("fastapi")


# Fastcore
def is_fastcore_available() -> bool:
    return is_package_available("fastcore")


def get_fastcore_version() -> str:
    return _get_version("fastcore")


# FastAI
def is_gradio_available() -> bool:
    return is_package_available("gradio")


def get_gradio_version() -> str:
    return _get_version("gradio")


# Graphviz
def is_graphviz_available() -> bool:
    return is_package_available("graphviz")


def get_graphviz_version() -> str:
    return _get_version("graphviz")


# hf_transfer
def is_hf_transfer_available() -> bool:
    return is_package_available("hf_transfer")


def get_hf_transfer_version() -> str:
    return _get_version("hf_transfer")


# xet
def is_xet_available() -> bool:
    # since hf_xet is automatically used if available, allow explicit disabling via environment variable
    if constants._is_true(os.environ.get("HF_HUB_DISABLE_XET")):  # type: ignore
        return False

    return is_package_available("hf_xet")


def get_xet_version() -> str:
    return _get_version("hf_xet")


# keras
def is_keras_available() -> bool:
    return is_package_available("keras")


def get_keras_version() -> str:
    return _get_version("keras")


# Numpy
def is_numpy_available() -> bool:
    return is_package_available("numpy")


def get_numpy_version() -> str:
    return _get_version("numpy")


# Jinja
def is_jinja_available() -> bool:
    return is_package_available("jinja")


def get_jinja_version() -> str:
    return _get_version("jinja")


# Pillow
def is_pillow_available() -> bool:
    return is_package_available("pillow")


def get_pillow_version() -> str:
    return _get_version("pillow")


# Pydantic
def is_pydantic_available() -> bool:
    if not is_package_available("pydantic"):
        return False
    # For Pydantic, we add an extra check to test whether it is correctly installed or not. If both pydantic 2.x and
    # typing_extensions<=4.5.0 are installed, then pydantic will fail at import time. This should not happen when
    # it is installed with `pip install huggingface_hub[inference]` but it can happen when it is installed manually
    # by the user in an environment that we don't control.
    #
    # Usually we won't need to do this kind of check on optional dependencies. However, pydantic is a special case
    # as it is automatically imported when doing `from huggingface_hub import ...` even if the user doesn't use it.
    #
    # See https://github.com/huggingface/huggingface_hub/pull/1829 for more details.
    try:
        from pydantic import validator  # noqa: F401
    except ImportError:
        # Example: "ImportError: cannot import name 'TypeAliasType' from 'typing_extensions'"
        warnings.warn(
            "Pydantic is installed but cannot be imported. Please check your installation. `huggingface_hub` will "
            "default to not using Pydantic. Error message: '{e}'"
        )
        return False
    return True


def get_pydantic_version() -> str:
    return _get_version("pydantic")


# Pydot
def is_pydot_available() -> bool:
    return is_package_available("pydot")


def get_pydot_version() -> str:
    return _get_version("pydot")


# Tensorboard
def is_tensorboard_available() -> bool:
    return is_package_available("tensorboard")


def get_tensorboard_version() -> str:
    return _get_version("tensorboard")


# Tensorflow
def is_tf_available() -> bool:
    return is_package_available("tensorflow")


def get_tf_version() -> str:
    return _get_version("tensorflow")


# Torch
def is_torch_available() -> bool:
    return is_package_available("torch")


def get_torch_version() -> str:
    return _get_version("torch")


# Safetensors
def is_safetensors_available() -> bool:
    return is_package_available("safetensors")


# Shell-related helpers
try:
    # Set to `True` if script is running in a Google Colab notebook.
    # If running in Google Colab, git credential store is set globally which makes the
    # warning disappear. See https://github.com/huggingface/huggingface_hub/issues/1043
    #
    # Taken from https://stackoverflow.com/a/63519730.
    _is_google_colab = "google.colab" in str(get_ipython())  # type: ignore # noqa: F821
except NameError:
    _is_google_colab = False


def is_notebook() -> bool:
    """Return `True` if code is executed in a notebook (Jupyter, Colab, QTconsole).

    Taken from https://stackoverflow.com/a/39662359.
    Adapted to make it work with Google colab as well.
    """
    try:
        shell_class = get_ipython().__class__  # type: ignore # noqa: F821
        for parent_class in shell_class.__mro__:  # e.g. "is subclass of"
            if parent_class.__name__ == "ZMQInteractiveShell":
                return True  # Jupyter notebook, Google colab or qtconsole
        return False
    except NameError:
        return False  # Probably standard Python interpreter


def is_google_colab() -> bool:
    """Return `True` if code is executed in a Google colab.

    Taken from https://stackoverflow.com/a/63519730.
    """
    return _is_google_colab


def is_colab_enterprise() -> bool:
    """Return `True` if code is executed in a Google Colab Enterprise environment."""
    return os.environ.get("VERTEX_PRODUCT") == "COLAB_ENTERPRISE"


def dump_environment_info() -> Dict[str, Any]:
    """Dump information about the machine to help debugging issues.

    Similar helper exist in:
    - `datasets` (https://github.com/huggingface/datasets/blob/main/src/datasets/commands/env.py)
    - `diffusers` (https://github.com/huggingface/diffusers/blob/main/src/diffusers/commands/env.py)
    - `transformers` (https://github.com/huggingface/transformers/blob/main/src/transformers/commands/env.py)
    """
    from huggingface_hub import get_token, whoami
    from huggingface_hub.utils import list_credential_helpers

    token = get_token()

    # Generic machine info
    info: Dict[str, Any] = {
        "huggingface_hub version": get_hf_hub_version(),
        "Platform": platform.platform(),
        "Python version": get_python_version(),
    }

    # Interpreter info
    try:
        shell_class = get_ipython().__class__  # type: ignore # noqa: F821
        info["Running in iPython ?"] = "Yes"
        info["iPython shell"] = shell_class.__name__
    except NameError:
        info["Running in iPython ?"] = "No"
    info["Running in notebook ?"] = "Yes" if is_notebook() else "No"
    info["Running in Google Colab ?"] = "Yes" if is_google_colab() else "No"
    info["Running in Google Colab Enterprise ?"] = "Yes" if is_colab_enterprise() else "No"
    # Login info
    info["Token path ?"] = constants.HF_TOKEN_PATH
    info["Has saved token ?"] = token is not None
    if token is not None:
        try:
            info["Who am I ?"] = whoami()["name"]
        except Exception:
            pass

    try:
        info["Configured git credential helpers"] = ", ".join(list_credential_helpers())
    except Exception:
        pass

    # Installed dependencies
    info["FastAI"] = get_fastai_version()
    info["Tensorflow"] = get_tf_version()
    info["Torch"] = get_torch_version()
    info["Jinja2"] = get_jinja_version()
    info["Graphviz"] = get_graphviz_version()
    info["keras"] = get_keras_version()
    info["Pydot"] = get_pydot_version()
    info["Pillow"] = get_pillow_version()
    info["hf_transfer"] = get_hf_transfer_version()
    info["gradio"] = get_gradio_version()
    info["tensorboard"] = get_tensorboard_version()
    info["numpy"] = get_numpy_version()
    info["pydantic"] = get_pydantic_version()
    info["aiohttp"] = get_aiohttp_version()
    info["hf_xet"] = get_xet_version()

    # Environment variables
    info["ENDPOINT"] = constants.ENDPOINT
    info["HF_HUB_CACHE"] = constants.HF_HUB_CACHE
    info["HF_ASSETS_CACHE"] = constants.HF_ASSETS_CACHE
    info["HF_TOKEN_PATH"] = constants.HF_TOKEN_PATH
    info["HF_STORED_TOKENS_PATH"] = constants.HF_STORED_TOKENS_PATH
    info["HF_HUB_OFFLINE"] = constants.HF_HUB_OFFLINE
    info["HF_HUB_DISABLE_TELEMETRY"] = constants.HF_HUB_DISABLE_TELEMETRY
    info["HF_HUB_DISABLE_PROGRESS_BARS"] = constants.HF_HUB_DISABLE_PROGRESS_BARS
    info["HF_HUB_DISABLE_SYMLINKS_WARNING"] = constants.HF_HUB_DISABLE_SYMLINKS_WARNING
    info["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = constants.HF_HUB_DISABLE_EXPERIMENTAL_WARNING
    info["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = constants.HF_HUB_DISABLE_IMPLICIT_TOKEN
    info["HF_HUB_ENABLE_HF_TRANSFER"] = constants.HF_HUB_ENABLE_HF_TRANSFER
    info["HF_HUB_ETAG_TIMEOUT"] = constants.HF_HUB_ETAG_TIMEOUT
    info["HF_HUB_DOWNLOAD_TIMEOUT"] = constants.HF_HUB_DOWNLOAD_TIMEOUT

    print("\nCopy-and-paste the text below in your GitHub issue.\n")
    print("\n".join([f"- {prop}: {val}" for prop, val in info.items()]) + "\n")
    return info

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\angle_helper.py ===
import numpy as np
import math

from mpl_toolkits.axisartist.grid_finder import ExtremeFinderSimple


def select_step_degree(dv):

    degree_limits_ = [1.5, 3, 7, 13, 20, 40, 70, 120, 270, 520]
    degree_steps_  = [1,   2, 5, 10, 15, 30, 45,  90, 180, 360]
    degree_factors = [1.] * len(degree_steps_)

    minsec_limits_ = [1.5, 2.5, 3.5, 8, 11, 18, 25, 45]
    minsec_steps_  = [1,   2,   3,   5, 10, 15, 20, 30]

    minute_limits_ = np.array(minsec_limits_) / 60
    minute_factors = [60.] * len(minute_limits_)

    second_limits_ = np.array(minsec_limits_) / 3600
    second_factors = [3600.] * len(second_limits_)

    degree_limits = [*second_limits_, *minute_limits_, *degree_limits_]
    degree_steps = [*minsec_steps_, *minsec_steps_, *degree_steps_]
    degree_factors = [*second_factors, *minute_factors, *degree_factors]

    n = np.searchsorted(degree_limits, dv)
    step = degree_steps[n]
    factor = degree_factors[n]

    return step, factor


def select_step_hour(dv):

    hour_limits_ = [1.5, 2.5, 3.5, 5, 7, 10, 15, 21, 36]
    hour_steps_  = [1,   2,   3,   4, 6,  8, 12, 18, 24]
    hour_factors = [1.] * len(hour_steps_)

    minsec_limits_ = [1.5, 2.5, 3.5, 4.5, 5.5, 8, 11, 14, 18, 25, 45]
    minsec_steps_  = [1,   2,   3,   4,   5,   6, 10, 12, 15, 20, 30]

    minute_limits_ = np.array(minsec_limits_) / 60
    minute_factors = [60.] * len(minute_limits_)

    second_limits_ = np.array(minsec_limits_) / 3600
    second_factors = [3600.] * len(second_limits_)

    hour_limits = [*second_limits_, *minute_limits_, *hour_limits_]
    hour_steps = [*minsec_steps_, *minsec_steps_, *hour_steps_]
    hour_factors = [*second_factors, *minute_factors, *hour_factors]

    n = np.searchsorted(hour_limits, dv)
    step = hour_steps[n]
    factor = hour_factors[n]

    return step, factor


def select_step_sub(dv):

    # subarcsec or degree
    tmp = 10.**(int(math.log10(dv))-1.)

    factor = 1./tmp

    if 1.5*tmp >= dv:
        step = 1
    elif 3.*tmp >= dv:
        step = 2
    elif 7.*tmp >= dv:
        step = 5
    else:
        step = 1
        factor = 0.1*factor

    return step, factor


def select_step(v1, v2, nv, hour=False, include_last=True,
                threshold_factor=3600.):

    if v1 > v2:
        v1, v2 = v2, v1

    dv = (v2 - v1) / nv

    if hour:
        _select_step = select_step_hour
        cycle = 24.
    else:
        _select_step = select_step_degree
        cycle = 360.

    # for degree
    if dv > 1 / threshold_factor:
        step, factor = _select_step(dv)
    else:
        step, factor = select_step_sub(dv*threshold_factor)

        factor = factor * threshold_factor

    levs = np.arange(np.floor(v1 * factor / step),
                     np.ceil(v2 * factor / step) + 0.5,
                     dtype=int) * step

    # n : number of valid levels. If there is a cycle, e.g., [0, 90, 180,
    # 270, 360], the grid line needs to be extended from 0 to 360, so
    # we need to return the whole array. However, the last level (360)
    # needs to be ignored often. In this case, so we return n=4.

    n = len(levs)

    # we need to check the range of values
    # for example, -90 to 90, 0 to 360,

    if factor == 1. and levs[-1] >= levs[0] + cycle:  # check for cycle
        nv = int(cycle / step)
        if include_last:
            levs = levs[0] + np.arange(0, nv+1, 1) * step
        else:
            levs = levs[0] + np.arange(0, nv, 1) * step

        n = len(levs)

    return np.array(levs), n, factor


def select_step24(v1, v2, nv, include_last=True, threshold_factor=3600):
    v1, v2 = v1 / 15, v2 / 15
    levs, n, factor = select_step(v1, v2, nv, hour=True,
                                  include_last=include_last,
                                  threshold_factor=threshold_factor)
    return levs * 15, n, factor


def select_step360(v1, v2, nv, include_last=True, threshold_factor=3600):
    return select_step(v1, v2, nv, hour=False,
                       include_last=include_last,
                       threshold_factor=threshold_factor)


class LocatorBase:
    def __init__(self, nbins, include_last=True):
        self.nbins = nbins
        self._include_last = include_last

    def set_params(self, nbins=None):
        if nbins is not None:
            self.nbins = int(nbins)


class LocatorHMS(LocatorBase):
    def __call__(self, v1, v2):
        return select_step24(v1, v2, self.nbins, self._include_last)


class LocatorHM(LocatorBase):
    def __call__(self, v1, v2):
        return select_step24(v1, v2, self.nbins, self._include_last,
                             threshold_factor=60)


class LocatorH(LocatorBase):
    def __call__(self, v1, v2):
        return select_step24(v1, v2, self.nbins, self._include_last,
                             threshold_factor=1)


class LocatorDMS(LocatorBase):
    def __call__(self, v1, v2):
        return select_step360(v1, v2, self.nbins, self._include_last)


class LocatorDM(LocatorBase):
    def __call__(self, v1, v2):
        return select_step360(v1, v2, self.nbins, self._include_last,
                              threshold_factor=60)


class LocatorD(LocatorBase):
    def __call__(self, v1, v2):
        return select_step360(v1, v2, self.nbins, self._include_last,
                              threshold_factor=1)


class FormatterDMS:
    deg_mark = r"^{\circ}"
    min_mark = r"^{\prime}"
    sec_mark = r"^{\prime\prime}"

    fmt_d = "$%d" + deg_mark + "$"
    fmt_ds = r"$%d.%s" + deg_mark + "$"

    # %s for sign
    fmt_d_m = r"$%s%d" + deg_mark + r"\,%02d" + min_mark + "$"
    fmt_d_ms = r"$%s%d" + deg_mark + r"\,%02d.%s" + min_mark + "$"

    fmt_d_m_partial = "$%s%d" + deg_mark + r"\,%02d" + min_mark + r"\,"
    fmt_s_partial = "%02d" + sec_mark + "$"
    fmt_ss_partial = "%02d.%s" + sec_mark + "$"

    def _get_number_fraction(self, factor):
        ## check for fractional numbers
        number_fraction = None
        # check for 60

        for threshold in [1, 60, 3600]:
            if factor <= threshold:
                break

            d = factor // threshold
            int_log_d = int(np.floor(np.log10(d)))
            if 10**int_log_d == d and d != 1:
                number_fraction = int_log_d
                factor = factor // 10**int_log_d
                return factor, number_fraction

        return factor, number_fraction

    def __call__(self, direction, factor, values):
        if len(values) == 0:
            return []

        ss = np.sign(values)
        signs = ["-" if v < 0 else "" for v in values]

        factor, number_fraction = self._get_number_fraction(factor)

        values = np.abs(values)

        if number_fraction is not None:
            values, frac_part = divmod(values, 10 ** number_fraction)
            frac_fmt = "%%0%dd" % (number_fraction,)
            frac_str = [frac_fmt % (f1,) for f1 in frac_part]

        if factor == 1:
            if number_fraction is None:
                return [self.fmt_d % (s * int(v),) for s, v in zip(ss, values)]
            else:
                return [self.fmt_ds % (s * int(v), f1)
                        for s, v, f1 in zip(ss, values, frac_str)]
        elif factor == 60:
            deg_part, min_part = divmod(values, 60)
            if number_fraction is None:
                return [self.fmt_d_m % (s1, d1, m1)
                        for s1, d1, m1 in zip(signs, deg_part, min_part)]
            else:
                return [self.fmt_d_ms % (s, d1, m1, f1)
                        for s, d1, m1, f1
                        in zip(signs, deg_part, min_part, frac_str)]

        elif factor == 3600:
            if ss[-1] == -1:
                inverse_order = True
                values = values[::-1]
                signs = signs[::-1]
            else:
                inverse_order = False

            l_hm_old = ""
            r = []

            deg_part, min_part_ = divmod(values, 3600)
            min_part, sec_part = divmod(min_part_, 60)

            if number_fraction is None:
                sec_str = [self.fmt_s_partial % (s1,) for s1 in sec_part]
            else:
                sec_str = [self.fmt_ss_partial % (s1, f1)
                           for s1, f1 in zip(sec_part, frac_str)]

            for s, d1, m1, s1 in zip(signs, deg_part, min_part, sec_str):
                l_hm = self.fmt_d_m_partial % (s, d1, m1)
                if l_hm != l_hm_old:
                    l_hm_old = l_hm
                    l = l_hm + s1
                else:
                    l = "$" + s + s1
                r.append(l)

            if inverse_order:
                return r[::-1]
            else:
                return r

        else:  # factor > 3600.
            return [r"$%s^{\circ}$" % v for v in ss*values]


class FormatterHMS(FormatterDMS):
    deg_mark = r"^\mathrm{h}"
    min_mark = r"^\mathrm{m}"
    sec_mark = r"^\mathrm{s}"

    fmt_d = "$%d" + deg_mark + "$"
    fmt_ds = r"$%d.%s" + deg_mark + "$"

    # %s for sign
    fmt_d_m = r"$%s%d" + deg_mark + r"\,%02d" + min_mark+"$"
    fmt_d_ms = r"$%s%d" + deg_mark + r"\,%02d.%s" + min_mark+"$"

    fmt_d_m_partial = "$%s%d" + deg_mark + r"\,%02d" + min_mark + r"\,"
    fmt_s_partial = "%02d" + sec_mark + "$"
    fmt_ss_partial = "%02d.%s" + sec_mark + "$"

    def __call__(self, direction, factor, values):  # hour
        return super().__call__(direction, factor, np.asarray(values) / 15)


class ExtremeFinderCycle(ExtremeFinderSimple):
    # docstring inherited

    def __init__(self, nx, ny,
                 lon_cycle=360., lat_cycle=None,
                 lon_minmax=None, lat_minmax=(-90, 90)):
        """
        This subclass handles the case where one or both coordinates should be
        taken modulo 360, or be restricted to not exceed a specific range.

        Parameters
        ----------
        nx, ny : int
            The number of samples in each direction.

        lon_cycle, lat_cycle : 360 or None
            If not None, values in the corresponding direction are taken modulo
            *lon_cycle* or *lat_cycle*; in theory this can be any number but
            the implementation actually assumes that it is 360 (if not None);
            other values give nonsensical results.

            This is done by "unwrapping" the transformed grid coordinates so
            that jumps are less than a half-cycle; then normalizing the span to
            no more than a full cycle.

            For example, if values are in the union of the [0, 2] and
            [358, 360] intervals (typically, angles measured modulo 360), the
            values in the second interval are normalized to [-2, 0] instead so
            that the values now cover [-2, 2].  If values are in a range of
            [5, 1000], this gets normalized to [5, 365].

        lon_minmax, lat_minmax : (float, float) or None
            If not None, the computed bounding box is clipped to the given
            range in the corresponding direction.
        """
        self.nx, self.ny = nx, ny
        self.lon_cycle, self.lat_cycle = lon_cycle, lat_cycle
        self.lon_minmax = lon_minmax
        self.lat_minmax = lat_minmax

    def __call__(self, transform_xy, x1, y1, x2, y2):
        # docstring inherited
        x, y = np.meshgrid(
            np.linspace(x1, x2, self.nx), np.linspace(y1, y2, self.ny))
        lon, lat = transform_xy(np.ravel(x), np.ravel(y))

        # iron out jumps, but algorithm should be improved.
        # This is just naive way of doing and my fail for some cases.
        # Consider replacing this with numpy.unwrap
        # We are ignoring invalid warnings. They are triggered when
        # comparing arrays with NaNs using > We are already handling
        # that correctly using np.nanmin and np.nanmax
        with np.errstate(invalid='ignore'):
            if self.lon_cycle is not None:
                lon0 = np.nanmin(lon)
                lon -= 360. * ((lon - lon0) > 180.)
            if self.lat_cycle is not None:
                lat0 = np.nanmin(lat)
                lat -= 360. * ((lat - lat0) > 180.)

        lon_min, lon_max = np.nanmin(lon), np.nanmax(lon)
        lat_min, lat_max = np.nanmin(lat), np.nanmax(lat)

        lon_min, lon_max, lat_min, lat_max = \
            self._add_pad(lon_min, lon_max, lat_min, lat_max)

        # check cycle
        if self.lon_cycle:
            lon_max = min(lon_max, lon_min + self.lon_cycle)
        if self.lat_cycle:
            lat_max = min(lat_max, lat_min + self.lat_cycle)

        if self.lon_minmax is not None:
            min0 = self.lon_minmax[0]
            lon_min = max(min0, lon_min)
            max0 = self.lon_minmax[1]
            lon_max = min(max0, lon_max)

        if self.lat_minmax is not None:
            min0 = self.lat_minmax[0]
            lat_min = max(min0, lat_min)
            max0 = self.lat_minmax[1]
            lat_max = min(max0, lat_max)

        return lon_min, lon_max, lat_min, lat_max

# === NexusCore/openenv\Lib\site-packages\httpx\_decoders.py ===
"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""

from __future__ import annotations

import codecs
import io
import typing
import zlib

from ._exceptions import DecodingError

# Brotli support is optional
try:
    # The C bindings in `brotli` are recommended for CPython.
    import brotli
except ImportError:  # pragma: no cover
    try:
        # The CFFI bindings in `brotlicffi` are recommended for PyPy
        # and other environments.
        import brotlicffi as brotli
    except ImportError:
        brotli = None


# Zstandard support is optional
try:
    import zstandard
except ImportError:  # pragma: no cover
    zstandard = None  # type: ignore


class ContentDecoder:
    def decode(self, data: bytes) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    def flush(self) -> bytes:
        raise NotImplementedError()  # pragma: no cover


class IdentityDecoder(ContentDecoder):
    """
    Handle unencoded data.
    """

    def decode(self, data: bytes) -> bytes:
        return data

    def flush(self) -> bytes:
        return b""


class DeflateDecoder(ContentDecoder):
    """
    Handle 'deflate' decoding.

    See: https://stackoverflow.com/questions/1838699
    """

    def __init__(self) -> None:
        self.first_attempt = True
        self.decompressor = zlib.decompressobj()

    def decode(self, data: bytes) -> bytes:
        was_first_attempt = self.first_attempt
        self.first_attempt = False
        try:
            return self.decompressor.decompress(data)
        except zlib.error as exc:
            if was_first_attempt:
                self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                return self.decode(data)
            raise DecodingError(str(exc)) from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: no cover
            raise DecodingError(str(exc)) from exc


class GZipDecoder(ContentDecoder):
    """
    Handle 'gzip' decoding.

    See: https://stackoverflow.com/questions/1838699
    """

    def __init__(self) -> None:
        self.decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)

    def decode(self, data: bytes) -> bytes:
        try:
            return self.decompressor.decompress(data)
        except zlib.error as exc:
            raise DecodingError(str(exc)) from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: no cover
            raise DecodingError(str(exc)) from exc


class BrotliDecoder(ContentDecoder):
    """
    Handle 'brotli' decoding.

    Requires `pip install brotlipy`. See: https://brotlipy.readthedocs.io/
        or   `pip install brotli`. See https://github.com/google/brotli
    Supports both 'brotlipy' and 'Brotli' packages since they share an import
    name. The top branches are for 'brotlipy' and bottom branches for 'Brotli'
    """

    def __init__(self) -> None:
        if brotli is None:  # pragma: no cover
            raise ImportError(
                "Using 'BrotliDecoder', but neither of the 'brotlicffi' or 'brotli' "
                "packages have been installed. "
                "Make sure to install httpx using `pip install httpx[brotli]`."
            ) from None

        self.decompressor = brotli.Decompressor()
        self.seen_data = False
        self._decompress: typing.Callable[[bytes], bytes]
        if hasattr(self.decompressor, "decompress"):
            # The 'brotlicffi' package.
            self._decompress = self.decompressor.decompress  # pragma: no cover
        else:
            # The 'brotli' package.
            self._decompress = self.decompressor.process  # pragma: no cover

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b""
        self.seen_data = True
        try:
            return self._decompress(data)
        except brotli.error as exc:
            raise DecodingError(str(exc)) from exc

    def flush(self) -> bytes:
        if not self.seen_data:
            return b""
        try:
            if hasattr(self.decompressor, "finish"):
                # Only available in the 'brotlicffi' package.

                # As the decompressor decompresses eagerly, this
                # will never actually emit any data. However, it will potentially throw
                # errors if a truncated or damaged data stream has been used.
                self.decompressor.finish()  # pragma: no cover
            return b""
        except brotli.error as exc:  # pragma: no cover
            raise DecodingError(str(exc)) from exc


class ZStandardDecoder(ContentDecoder):
    """
    Handle 'zstd' RFC 8878 decoding.

    Requires `pip install zstandard`.
    Can be installed as a dependency of httpx using `pip install httpx[zstd]`.
    """

    # inspired by the ZstdDecoder implementation in urllib3
    def __init__(self) -> None:
        if zstandard is None:  # pragma: no cover
            raise ImportError(
                "Using 'ZStandardDecoder', ..."
                "Make sure to install httpx using `pip install httpx[zstd]`."
            ) from None

        self.decompressor = zstandard.ZstdDecompressor().decompressobj()
        self.seen_data = False

    def decode(self, data: bytes) -> bytes:
        assert zstandard is not None
        self.seen_data = True
        output = io.BytesIO()
        try:
            output.write(self.decompressor.decompress(data))
            while self.decompressor.eof and self.decompressor.unused_data:
                unused_data = self.decompressor.unused_data
                self.decompressor = zstandard.ZstdDecompressor().decompressobj()
                output.write(self.decompressor.decompress(unused_data))
        except zstandard.ZstdError as exc:
            raise DecodingError(str(exc)) from exc
        return output.getvalue()

    def flush(self) -> bytes:
        if not self.seen_data:
            return b""
        ret = self.decompressor.flush()  # note: this is a no-op
        if not self.decompressor.eof:
            raise DecodingError("Zstandard data is incomplete")  # pragma: no cover
        return bytes(ret)


class MultiDecoder(ContentDecoder):
    """
    Handle the case where multiple encodings have been applied.
    """

    def __init__(self, children: typing.Sequence[ContentDecoder]) -> None:
        """
        'children' should be a sequence of decoders in the order in which
        each was applied.
        """
        # Note that we reverse the order for decoding.
        self.children = list(reversed(children))

    def decode(self, data: bytes) -> bytes:
        for child in self.children:
            data = child.decode(data)
        return data

    def flush(self) -> bytes:
        data = b""
        for child in self.children:
            data = child.decode(data) + child.flush()
        return data


class ByteChunker:
    """
    Handles returning byte content in fixed-size chunks.
    """

    def __init__(self, chunk_size: int | None = None) -> None:
        self._buffer = io.BytesIO()
        self._chunk_size = chunk_size

    def decode(self, content: bytes) -> list[bytes]:
        if self._chunk_size is None:
            return [content] if content else []

        self._buffer.write(content)
        if self._buffer.tell() >= self._chunk_size:
            value = self._buffer.getvalue()
            chunks = [
                value[i : i + self._chunk_size]
                for i in range(0, len(value), self._chunk_size)
            ]
            if len(chunks[-1]) == self._chunk_size:
                self._buffer.seek(0)
                self._buffer.truncate()
                return chunks
            else:
                self._buffer.seek(0)
                self._buffer.write(chunks[-1])
                self._buffer.truncate()
                return chunks[:-1]
        else:
            return []

    def flush(self) -> list[bytes]:
        value = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate()
        return [value] if value else []


class TextChunker:
    """
    Handles returning text content in fixed-size chunks.
    """

    def __init__(self, chunk_size: int | None = None) -> None:
        self._buffer = io.StringIO()
        self._chunk_size = chunk_size

    def decode(self, content: str) -> list[str]:
        if self._chunk_size is None:
            return [content] if content else []

        self._buffer.write(content)
        if self._buffer.tell() >= self._chunk_size:
            value = self._buffer.getvalue()
            chunks = [
                value[i : i + self._chunk_size]
                for i in range(0, len(value), self._chunk_size)
            ]
            if len(chunks[-1]) == self._chunk_size:
                self._buffer.seek(0)
                self._buffer.truncate()
                return chunks
            else:
                self._buffer.seek(0)
                self._buffer.write(chunks[-1])
                self._buffer.truncate()
                return chunks[:-1]
        else:
            return []

    def flush(self) -> list[str]:
        value = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate()
        return [value] if value else []


class TextDecoder:
    """
    Handles incrementally decoding bytes into text
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        self.decoder = codecs.getincrementaldecoder(encoding)(errors="replace")

    def decode(self, data: bytes) -> str:
        return self.decoder.decode(data)

    def flush(self) -> str:
        return self.decoder.decode(b"", True)


class LineDecoder:
    """
    Handles incrementally reading lines from text.

    Has the same behaviour as the stdllib splitlines,
    but handling the input iteratively.
    """

    def __init__(self) -> None:
        self.buffer: list[str] = []
        self.trailing_cr: bool = False

    def decode(self, text: str) -> list[str]:
        # See https://docs.python.org/3/library/stdtypes.html#str.splitlines
        NEWLINE_CHARS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"

        # We always push a trailing `\r` into the next decode iteration.
        if self.trailing_cr:
            text = "\r" + text
            self.trailing_cr = False
        if text.endswith("\r"):
            self.trailing_cr = True
            text = text[:-1]

        if not text:
            # NOTE: the edge case input of empty text doesn't occur in practice,
            # because other httpx internals filter out this value
            return []  # pragma: no cover

        trailing_newline = text[-1] in NEWLINE_CHARS
        lines = text.splitlines()

        if len(lines) == 1 and not trailing_newline:
            # No new lines, buffer the input and continue.
            self.buffer.append(lines[0])
            return []

        if self.buffer:
            # Include any existing buffer in the first portion of the
            # splitlines result.
            lines = ["".join(self.buffer) + lines[0]] + lines[1:]
            self.buffer = []

        if not trailing_newline:
            # If the last segment of splitlines is not newline terminated,
            # then drop it from our output and start a new buffer.
            self.buffer = [lines.pop()]

        return lines

    def flush(self) -> list[str]:
        if not self.buffer and not self.trailing_cr:
            return []

        lines = ["".join(self.buffer)]
        self.buffer = []
        self.trailing_cr = False
        return lines


SUPPORTED_DECODERS = {
    "identity": IdentityDecoder,
    "gzip": GZipDecoder,
    "deflate": DeflateDecoder,
    "br": BrotliDecoder,
    "zstd": ZStandardDecoder,
}


if brotli is None:
    SUPPORTED_DECODERS.pop("br")  # pragma: no cover
if zstandard is None:
    SUPPORTED_DECODERS.pop("zstd")  # pragma: no cover

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\removeOverlaps.py ===
""" Simplify TrueType glyphs by merging overlapping contours/components.

Requires https://github.com/fonttools/skia-pathops
"""

import itertools
import logging
from typing import Callable, Iterable, Optional, Mapping

from fontTools.cffLib import CFFFontSet
from fontTools.ttLib import ttFont
from fontTools.ttLib.tables import _g_l_y_f
from fontTools.ttLib.tables import _h_m_t_x
from fontTools.misc.psCharStrings import T2CharString
from fontTools.misc.roundTools import otRound, noRound
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

import pathops


__all__ = ["removeOverlaps"]


class RemoveOverlapsError(Exception):
    pass


log = logging.getLogger("fontTools.ttLib.removeOverlaps")

_TTGlyphMapping = Mapping[str, ttFont._TTGlyph]


def skPathFromGlyph(glyphName: str, glyphSet: _TTGlyphMapping) -> pathops.Path:
    path = pathops.Path()
    pathPen = path.getPen(glyphSet=glyphSet)
    glyphSet[glyphName].draw(pathPen)
    return path


def skPathFromGlyphComponent(
    component: _g_l_y_f.GlyphComponent, glyphSet: _TTGlyphMapping
):
    baseGlyphName, transformation = component.getComponentInfo()
    path = skPathFromGlyph(baseGlyphName, glyphSet)
    return path.transform(*transformation)


def componentsOverlap(glyph: _g_l_y_f.Glyph, glyphSet: _TTGlyphMapping) -> bool:
    if not glyph.isComposite():
        raise ValueError("This method only works with TrueType composite glyphs")
    if len(glyph.components) < 2:
        return False  # single component, no overlaps

    component_paths = {}

    def _get_nth_component_path(index: int) -> pathops.Path:
        if index not in component_paths:
            component_paths[index] = skPathFromGlyphComponent(
                glyph.components[index], glyphSet
            )
        return component_paths[index]

    return any(
        pathops.op(
            _get_nth_component_path(i),
            _get_nth_component_path(j),
            pathops.PathOp.INTERSECTION,
            fix_winding=False,
            keep_starting_points=False,
        )
        for i, j in itertools.combinations(range(len(glyph.components)), 2)
    )


def ttfGlyphFromSkPath(path: pathops.Path) -> _g_l_y_f.Glyph:
    # Skia paths have no 'components', no need for glyphSet
    ttPen = TTGlyphPen(glyphSet=None)
    path.draw(ttPen)
    glyph = ttPen.glyph()
    assert not glyph.isComposite()
    # compute glyph.xMin (glyfTable parameter unused for non composites)
    glyph.recalcBounds(glyfTable=None)
    return glyph


def _charString_from_SkPath(
    path: pathops.Path, charString: T2CharString
) -> T2CharString:
    if charString.width == charString.private.defaultWidthX:
        width = None
    else:
        width = charString.width - charString.private.nominalWidthX
    t2Pen = T2CharStringPen(width=width, glyphSet=None)
    path.draw(t2Pen)
    return t2Pen.getCharString(charString.private, charString.globalSubrs)


def _round_path(
    path: pathops.Path, round: Callable[[float], float] = otRound
) -> pathops.Path:
    rounded_path = pathops.Path()
    for verb, points in path:
        rounded_path.add(verb, *((round(p[0]), round(p[1])) for p in points))
    return rounded_path


def _simplify(
    path: pathops.Path,
    debugGlyphName: str,
    *,
    round: Callable[[float], float] = otRound,
) -> pathops.Path:
    # skia-pathops has a bug where it sometimes fails to simplify paths when there
    # are float coordinates and control points are very close to one another.
    # Rounding coordinates to integers works around the bug.
    # Since we are going to round glyf coordinates later on anyway, here it is
    # ok(-ish) to also round before simplify. Better than failing the whole process
    # for the entire font.
    # https://bugs.chromium.org/p/skia/issues/detail?id=11958
    # https://github.com/google/fonts/issues/3365
    # TODO(anthrotype): remove once this Skia bug is fixed
    try:
        return pathops.simplify(path, clockwise=path.clockwise)
    except pathops.PathOpsError:
        pass

    path = _round_path(path, round=round)
    try:
        path = pathops.simplify(path, clockwise=path.clockwise)
        log.debug(
            "skia-pathops failed to simplify '%s' with float coordinates, "
            "but succeded using rounded integer coordinates",
            debugGlyphName,
        )
        return path
    except pathops.PathOpsError as e:
        if log.isEnabledFor(logging.DEBUG):
            path.dump()
        raise RemoveOverlapsError(
            f"Failed to remove overlaps from glyph {debugGlyphName!r}"
        ) from e

    raise AssertionError("Unreachable")


def _same_path(path1: pathops.Path, path2: pathops.Path) -> bool:
    return {tuple(c) for c in path1.contours} == {tuple(c) for c in path2.contours}


def removeTTGlyphOverlaps(
    glyphName: str,
    glyphSet: _TTGlyphMapping,
    glyfTable: _g_l_y_f.table__g_l_y_f,
    hmtxTable: _h_m_t_x.table__h_m_t_x,
    removeHinting: bool = True,
) -> bool:
    glyph = glyfTable[glyphName]
    # decompose composite glyphs only if components overlap each other
    if (
        glyph.numberOfContours > 0
        or glyph.isComposite()
        and componentsOverlap(glyph, glyphSet)
    ):
        path = skPathFromGlyph(glyphName, glyphSet)

        # remove overlaps
        path2 = _simplify(path, glyphName)

        # replace TTGlyph if simplified path is different (ignoring contour order)
        if not _same_path(path, path2):
            glyfTable[glyphName] = glyph = ttfGlyphFromSkPath(path2)
            # simplified glyph is always unhinted
            assert not glyph.program
            # also ensure hmtx LSB == glyph.xMin so glyph origin is at x=0
            width, lsb = hmtxTable[glyphName]
            if lsb != glyph.xMin:
                hmtxTable[glyphName] = (width, glyph.xMin)
            return True

    if removeHinting:
        glyph.removeHinting()
    return False


def _remove_glyf_overlaps(
    *,
    font: ttFont.TTFont,
    glyphNames: Iterable[str],
    glyphSet: _TTGlyphMapping,
    removeHinting: bool,
    ignoreErrors: bool,
) -> None:
    glyfTable = font["glyf"]
    hmtxTable = font["hmtx"]

    # process all simple glyphs first, then composites with increasing component depth,
    # so that by the time we test for component intersections the respective base glyphs
    # have already been simplified
    glyphNames = sorted(
        glyphNames,
        key=lambda name: (
            (
                glyfTable[name].getCompositeMaxpValues(glyfTable).maxComponentDepth
                if glyfTable[name].isComposite()
                else 0
            ),
            name,
        ),
    )
    modified = set()
    for glyphName in glyphNames:
        try:
            if removeTTGlyphOverlaps(
                glyphName, glyphSet, glyfTable, hmtxTable, removeHinting
            ):
                modified.add(glyphName)
        except RemoveOverlapsError:
            if not ignoreErrors:
                raise
            log.error("Failed to remove overlaps for '%s'", glyphName)

    log.debug("Removed overlaps for %s glyphs:\n%s", len(modified), " ".join(modified))


def _remove_charstring_overlaps(
    *,
    glyphName: str,
    glyphSet: _TTGlyphMapping,
    cffFontSet: CFFFontSet,
) -> bool:
    path = skPathFromGlyph(glyphName, glyphSet)

    # remove overlaps
    path2 = _simplify(path, glyphName, round=noRound)

    # replace TTGlyph if simplified path is different (ignoring contour order)
    if not _same_path(path, path2):
        charStrings = cffFontSet[0].CharStrings
        charStrings[glyphName] = _charString_from_SkPath(path2, charStrings[glyphName])
        return True

    return False


def _remove_cff_overlaps(
    *,
    font: ttFont.TTFont,
    glyphNames: Iterable[str],
    glyphSet: _TTGlyphMapping,
    removeHinting: bool,
    ignoreErrors: bool,
    removeUnusedSubroutines: bool = True,
) -> None:
    cffFontSet = font["CFF "].cff
    modified = set()
    for glyphName in glyphNames:
        try:
            if _remove_charstring_overlaps(
                glyphName=glyphName,
                glyphSet=glyphSet,
                cffFontSet=cffFontSet,
            ):
                modified.add(glyphName)
        except RemoveOverlapsError:
            if not ignoreErrors:
                raise
            log.error("Failed to remove overlaps for '%s'", glyphName)

    if not modified:
        log.debug("No overlaps found in the specified CFF glyphs")
        return

    if removeHinting:
        cffFontSet.remove_hints()

    if removeUnusedSubroutines:
        cffFontSet.remove_unused_subroutines()

    log.debug("Removed overlaps for %s glyphs:\n%s", len(modified), " ".join(modified))


def removeOverlaps(
    font: ttFont.TTFont,
    glyphNames: Optional[Iterable[str]] = None,
    removeHinting: bool = True,
    ignoreErrors: bool = False,
    *,
    removeUnusedSubroutines: bool = True,
) -> None:
    """Simplify glyphs in TTFont by merging overlapping contours.

    Overlapping components are first decomposed to simple contours, then merged.

    Currently this only works for fonts with 'glyf' or 'CFF ' tables.
    Raises NotImplementedError if 'glyf' or 'CFF ' tables are absent.

    Note that removing overlaps invalidates the hinting. By default we drop hinting
    from all glyphs whether or not overlaps are removed from a given one, as it would
    look weird if only some glyphs are left (un)hinted.

    Args:
        font: input TTFont object, modified in place.
        glyphNames: optional iterable of glyph names (str) to remove overlaps from.
            By default, all glyphs in the font are processed.
        removeHinting (bool): set to False to keep hinting for unmodified glyphs.
        ignoreErrors (bool): set to True to ignore errors while removing overlaps,
            thus keeping the tricky glyphs unchanged (fonttools/fonttools#2363).
        removeUnusedSubroutines (bool): set to False to keep unused subroutines
            in CFF table after removing overlaps. Default is to remove them if
            any glyphs are modified.
    """

    if "glyf" not in font and "CFF " not in font:
        raise NotImplementedError(
            "No outline data found in the font: missing 'glyf' or 'CFF ' table"
        )

    if glyphNames is None:
        glyphNames = font.getGlyphOrder()

    # Wraps the underlying glyphs, takes care of interfacing with drawing pens
    glyphSet = font.getGlyphSet()

    if "glyf" in font:
        _remove_glyf_overlaps(
            font=font,
            glyphNames=glyphNames,
            glyphSet=glyphSet,
            removeHinting=removeHinting,
            ignoreErrors=ignoreErrors,
        )

    if "CFF " in font:
        _remove_cff_overlaps(
            font=font,
            glyphNames=glyphNames,
            glyphSet=glyphSet,
            removeHinting=removeHinting,
            ignoreErrors=ignoreErrors,
            removeUnusedSubroutines=removeUnusedSubroutines,
        )


def main(args=None):
    """Simplify glyphs in TTFont by merging overlapping contours."""

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools ttLib.removeOverlaps", description=__doc__
    )

    parser.add_argument("input", metavar="INPUT.ttf", help="Input font file")
    parser.add_argument("output", metavar="OUTPUT.ttf", help="Output font file")
    parser.add_argument(
        "glyphs",
        metavar="GLYPHS",
        nargs="*",
        help="Optional list of glyph names to remove overlaps from",
    )
    parser.add_argument(
        "--keep-hinting",
        action="store_true",
        help="Keep hinting for unmodified glyphs, default is to drop hinting",
    )
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="ignore errors while removing overlaps, "
        "thus keeping the tricky glyphs unchanged",
    )
    parser.add_argument(
        "--keep-unused-subroutines",
        action="store_true",
        help="Keep unused subroutines in CFF table after removing overlaps, "
        "default is to remove them if any glyphs are modified",
    )
    args = parser.parse_args(args)

    with ttFont.TTFont(args.input) as font:
        removeOverlaps(
            font=font,
            glyphNames=args.glyphs or None,
            removeHinting=not args.keep_hinting,
            ignoreErrors=args.ignore_errors,
            removeUnusedSubroutines=not args.keep_unused_subroutines,
        )
        font.save(args.output)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\script.py ===
"""Magic functions for running cells in various scripts."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import asyncio
import asyncio.exceptions
import atexit
import errno
import os
import signal
import sys
import time
from subprocess import CalledProcessError
from threading import Thread

from traitlets import Any, Dict, List, default

from IPython.core import magic_arguments
from IPython.core.async_helpers import _AsyncIOProxy
from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
from IPython.utils.process import arg_split

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

def script_args(f):
    """single decorator for adding script args"""
    args = [
        magic_arguments.argument(
            '--out', type=str,
            help="""The variable in which to store stdout from the script.
            If the script is backgrounded, this will be the stdout *pipe*,
            instead of the stderr text itself and will not be auto closed.
            """
        ),
        magic_arguments.argument(
            '--err', type=str,
            help="""The variable in which to store stderr from the script.
            If the script is backgrounded, this will be the stderr *pipe*,
            instead of the stderr text itself and will not be autoclosed.
            """
        ),
        magic_arguments.argument(
            '--bg', action="store_true",
            help="""Whether to run the script in the background.
            If given, the only way to see the output of the command is
            with --out/err.
            """
        ),
        magic_arguments.argument(
            '--proc', type=str,
            help="""The variable in which to store Popen instance.
            This is used only when --bg option is given.
            """
        ),
        magic_arguments.argument(
            '--no-raise-error', action="store_false", dest='raise_error',
            help="""Whether you should raise an error message in addition to
            a stream on stderr if you get a nonzero exit code.
            """,
        ),
    ]
    for arg in args:
        f = arg(f)
    return f


class RaiseAfterInterrupt(Exception):
    pass


@magics_class
class ScriptMagics(Magics):
    """Magics for talking to scripts
    
    This defines a base `%%script` cell magic for running a cell
    with a program in a subprocess, and registers a few top-level
    magics that call %%script with common interpreters.
    """

    event_loop = Any(
        help="""
        The event loop on which to run subprocesses

        Not the main event loop,
        because we want to be able to make blocking calls
        and have certain requirements we don't want to impose on the main loop.
        """
    )

    script_magics: List = List(
        help="""Extra script cell magics to define
        
        This generates simple wrappers of `%%script foo` as `%%foo`.
        
        If you want to add script magics that aren't on your path,
        specify them in script_paths
        """,
    ).tag(config=True)

    @default('script_magics')
    def _script_magics_default(self):
        """default to a common list of programs"""
        
        defaults = [
            'sh',
            'bash',
            'perl',
            'ruby',
            'python',
            'python2',
            'python3',
            'pypy',
        ]
        if os.name == 'nt':
            defaults.extend([
                'cmd',
            ])
        
        return defaults
    
    script_paths = Dict(
        help="""Dict mapping short 'ruby' names to full paths, such as '/opt/secret/bin/ruby'
        
        Only necessary for items in script_magics where the default path will not
        find the right interpreter.
        """
    ).tag(config=True)
    
    def __init__(self, shell=None):
        super(ScriptMagics, self).__init__(shell=shell)
        self._generate_script_magics()
        self.bg_processes = []
        atexit.register(self.kill_bg_processes)

    def __del__(self):
        self.kill_bg_processes()
    
    def _generate_script_magics(self):
        cell_magics = self.magics['cell']
        for name in self.script_magics:
            cell_magics[name] = self._make_script_magic(name)
    
    def _make_script_magic(self, name):
        """make a named magic, that calls %%script with a particular program"""
        # expand to explicit path if necessary:
        script = self.script_paths.get(name, name)
        
        @magic_arguments.magic_arguments()
        @script_args
        def named_script_magic(line, cell):
            # if line, add it as cl-flags
            if line:
                line = "%s %s" % (script, line)
            else:
                line = script
            return self.shebang(line, cell)
        
        # write a basic docstring:
        named_script_magic.__doc__ = \
        """%%{name} script magic
        
        Run cells with {script} in a subprocess.
        
        This is a shortcut for `%%script {script}`
        """.format(**locals())
        
        return named_script_magic
    
    @magic_arguments.magic_arguments()
    @script_args
    @cell_magic("script")
    def shebang(self, line, cell):
        """Run a cell via a shell command

        The `%%script` line is like the #! line of script,
        specifying a program (bash, perl, ruby, etc.) with which to run.

        The rest of the cell is run by that program.

        .. versionchanged:: 9.0
          Interrupting the script executed without `--bg` will end in
          raising an exception (unless `--no-raise-error` is passed).

        Examples
        --------
        ::

            In [1]: %%script bash
               ...: for i in 1 2 3; do
               ...:   echo $i
               ...: done
            1
            2
            3
        """

        # Create the event loop in which to run script magics
        # this operates on a background thread
        if self.event_loop is None:
            if sys.platform == "win32":
                # don't override the current policy,
                # just create an event loop
                event_loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
            else:
                event_loop = asyncio.new_event_loop()
            self.event_loop = event_loop

            # start the loop in a background thread
            asyncio_thread = Thread(target=event_loop.run_forever, daemon=True)
            asyncio_thread.start()
        else:
            event_loop = self.event_loop

        def in_thread(coro):
            """Call a coroutine on the asyncio thread"""
            return asyncio.run_coroutine_threadsafe(coro, event_loop).result()

        async def _readchunk(stream):
            try:
                return await stream.read(100)
            except asyncio.exceptions.IncompleteReadError as e:
                return e.partial
            except asyncio.exceptions.LimitOverrunError as e:
                return await stream.read(e.consumed)

        async def _handle_stream(stream, stream_arg, file_object):
            while True:
                chunk = (await _readchunk(stream)).decode("utf8", errors="replace")
                if not chunk:
                    break
                if stream_arg:
                    self.shell.user_ns[stream_arg] = chunk
                else:
                    file_object.write(chunk)
                    file_object.flush()

        async def _stream_communicate(process, cell):
            process.stdin.write(cell)
            process.stdin.close()
            stdout_task = asyncio.create_task(
                _handle_stream(process.stdout, args.out, sys.stdout)
            )
            stderr_task = asyncio.create_task(
                _handle_stream(process.stderr, args.err, sys.stderr)
            )
            await asyncio.wait([stdout_task, stderr_task])
            await process.wait()

        argv = arg_split(line, posix=not sys.platform.startswith("win"))
        args, cmd = self.shebang.parser.parse_known_args(argv)

        try:
            p = in_thread(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE,
                )
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("Couldn't find program: %r" % cmd[0])
                return
            else:
                raise

        if not cell.endswith('\n'):
            cell += '\n'
        cell = cell.encode('utf8', 'replace')
        if args.bg:
            self.bg_processes.append(p)
            self._gc_bg_processes()
            to_close = []
            if args.out:
                self.shell.user_ns[args.out] = _AsyncIOProxy(p.stdout, event_loop)
            else:
                to_close.append(p.stdout)
            if args.err:
                self.shell.user_ns[args.err] = _AsyncIOProxy(p.stderr, event_loop)
            else:
                to_close.append(p.stderr)
            event_loop.call_soon_threadsafe(
                lambda: asyncio.Task(self._run_script(p, cell, to_close))
            )
            if args.proc:
                proc_proxy = _AsyncIOProxy(p, event_loop)
                proc_proxy.stdout = _AsyncIOProxy(p.stdout, event_loop)
                proc_proxy.stderr = _AsyncIOProxy(p.stderr, event_loop)
                self.shell.user_ns[args.proc] = proc_proxy
            return

        try:
            in_thread(_stream_communicate(p, cell))
        except KeyboardInterrupt:
            try:
                p.send_signal(signal.SIGINT)
                in_thread(asyncio.wait_for(p.wait(), timeout=0.1))
                if p.returncode is not None:
                    print("Process was interrupted.")
                    if args.raise_error:
                        raise RaiseAfterInterrupt()
                    else:
                        return
                p.terminate()
                in_thread(asyncio.wait_for(p.wait(), timeout=0.1))
                if p.returncode is not None:
                    print("Process was terminated.")
                    if args.raise_error:
                        raise RaiseAfterInterrupt()
                    else:
                        return
                p.kill()
                print("Process was killed.")
                if args.raise_error:
                    raise RaiseAfterInterrupt()
            except RaiseAfterInterrupt:
                pass
            except OSError:
                pass
            except Exception as e:
                print("Error while terminating subprocess (pid=%i): %s" % (p.pid, e))
            if args.raise_error:
                raise CalledProcessError(p.returncode, cell) from None
            else:
                return

        if args.raise_error and p.returncode != 0:
            # If we get here and p.returncode is still None, we must have
            # killed it but not yet seen its return code. We don't wait for it,
            # in case it's stuck in uninterruptible sleep. -9 = SIGKILL
            rc = p.returncode or -9
            raise CalledProcessError(rc, cell)

    shebang.__skip_doctest__ = os.name != "posix"

    async def _run_script(self, p, cell, to_close):
        """callback for running the script in the background"""

        p.stdin.write(cell)
        await p.stdin.drain()
        p.stdin.close()
        await p.stdin.wait_closed()
        await p.wait()
        # asyncio read pipes have no close
        # but we should drain the data anyway
        for s in to_close:
            await s.read()
        self._gc_bg_processes()

    @line_magic("killbgscripts")
    def killbgscripts(self, _nouse_=''):
        """Kill all BG processes started by %%script and its family."""
        self.kill_bg_processes()
        print("All background processes were killed.")

    def kill_bg_processes(self):
        """Kill all BG processes which are still running."""
        if not self.bg_processes:
            return
        for p in self.bg_processes:
            if p.returncode is None:
                try:
                    p.send_signal(signal.SIGINT)
                except:
                    pass
        time.sleep(0.1)
        self._gc_bg_processes()
        if not self.bg_processes:
            return
        for p in self.bg_processes:
            if p.returncode is None:
                try:
                    p.terminate()
                except:
                    pass
        time.sleep(0.1)
        self._gc_bg_processes()
        if not self.bg_processes:
            return
        for p in self.bg_processes:
            if p.returncode is None:
                try:
                    p.kill()
                except:
                    pass
        self._gc_bg_processes()

    def _gc_bg_processes(self):
        self.bg_processes = [p for p in self.bg_processes if p.returncode is None]

# === NexusCore/openenv\Lib\site-packages\nltk\parse\malt.py ===
# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
# Contributor: Liling Tan, Mustufain, osamamukhtar11
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import inspect
import os
import subprocess
import sys
import tempfile

from nltk.data import ZipFilePathPointer
from nltk.internals import find_dir, find_file, find_jars_within_path
from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.parse.util import taggedsents_to_conll


def malt_regex_tagger():
    from nltk.tag import RegexpTagger

    _tagger = RegexpTagger(
        [
            (r"\.$", "."),
            (r"\,$", ","),
            (r"\?$", "?"),  # fullstop, comma, Qmark
            (r"\($", "("),
            (r"\)$", ")"),  # round brackets
            (r"\[$", "["),
            (r"\]$", "]"),  # square brackets
            (r"^-?[0-9]+(\.[0-9]+)?$", "CD"),  # cardinal numbers
            (r"(The|the|A|a|An|an)$", "DT"),  # articles
            (r"(He|he|She|she|It|it|I|me|Me|You|you)$", "PRP"),  # pronouns
            (r"(His|his|Her|her|Its|its)$", "PRP$"),  # possessive
            (r"(my|Your|your|Yours|yours)$", "PRP$"),  # possessive
            (r"(on|On|in|In|at|At|since|Since)$", "IN"),  # time prepopsitions
            (r"(for|For|ago|Ago|before|Before)$", "IN"),  # time prepopsitions
            (r"(till|Till|until|Until)$", "IN"),  # time prepopsitions
            (r"(by|By|beside|Beside)$", "IN"),  # space prepopsitions
            (r"(under|Under|below|Below)$", "IN"),  # space prepopsitions
            (r"(over|Over|above|Above)$", "IN"),  # space prepopsitions
            (r"(across|Across|through|Through)$", "IN"),  # space prepopsitions
            (r"(into|Into|towards|Towards)$", "IN"),  # space prepopsitions
            (r"(onto|Onto|from|From)$", "IN"),  # space prepopsitions
            (r".*able$", "JJ"),  # adjectives
            (r".*ness$", "NN"),  # nouns formed from adjectives
            (r".*ly$", "RB"),  # adverbs
            (r".*s$", "NNS"),  # plural nouns
            (r".*ing$", "VBG"),  # gerunds
            (r".*ed$", "VBD"),  # past tense verbs
            (r".*", "NN"),  # nouns (default)
        ]
    )
    return _tagger.tag


def find_maltparser(parser_dirname):
    """
    A module to find MaltParser .jar file and its dependencies.
    """
    if os.path.exists(parser_dirname):  # If a full path is given.
        _malt_dir = parser_dirname
    else:  # Try to find path to maltparser directory in environment variables.
        _malt_dir = find_dir(parser_dirname, env_vars=("MALT_PARSER",))
    # Checks that that the found directory contains all the necessary .jar
    malt_dependencies = ["", "", ""]
    _malt_jars = set(find_jars_within_path(_malt_dir))
    _jars = {os.path.split(jar)[1] for jar in _malt_jars}
    malt_dependencies = {"log4j.jar", "libsvm.jar", "liblinear-1.8.jar"}

    assert malt_dependencies.issubset(_jars)
    assert any(
        filter(lambda i: i.startswith("maltparser-") and i.endswith(".jar"), _jars)
    )
    return list(_malt_jars)


def find_malt_model(model_filename):
    """
    A module to find pre-trained MaltParser model.
    """
    if model_filename is None:
        return "malt_temp.mco"
    elif os.path.exists(model_filename):  # If a full path is given.
        return model_filename
    else:  # Try to find path to malt model in environment variables.
        return find_file(model_filename, env_vars=("MALT_MODEL",), verbose=False)


class MaltParser(ParserI):
    """
    A class for dependency parsing with MaltParser. The input is the paths to:
    - (optionally) a maltparser directory
    - (optionally) the path to a pre-trained MaltParser .mco model file
    - (optionally) the tagger to use for POS tagging before parsing
    - (optionally) additional Java arguments

    Example:
        >>> from nltk.parse import malt
        >>> # With MALT_PARSER and MALT_MODEL environment set.
        >>> mp = malt.MaltParser(model_filename='engmalt.linear-1.7.mco') # doctest: +SKIP
        >>> mp.parse_one('I shot an elephant in my pajamas .'.split()).tree() # doctest: +SKIP
        (shot I (elephant an) (in (pajamas my)) .)
        >>> # Without MALT_PARSER and MALT_MODEL environment.
        >>> mp = malt.MaltParser('/home/user/maltparser-1.9.2/', '/home/user/engmalt.linear-1.7.mco') # doctest: +SKIP
        >>> mp.parse_one('I shot an elephant in my pajamas .'.split()).tree() # doctest: +SKIP
        (shot I (elephant an) (in (pajamas my)) .)
    """

    def __init__(
        self,
        parser_dirname="",
        model_filename=None,
        tagger=None,
        additional_java_args=None,
    ):
        """
        An interface for parsing with the Malt Parser.

        :param parser_dirname: The path to the maltparser directory that
            contains the maltparser-1.x.jar
        :type parser_dirname: str
        :param model_filename: The name of the pre-trained model with .mco file
            extension. If provided, training will not be required.
            (see http://www.maltparser.org/mco/mco.html and
            see http://www.patful.com/chalk/node/185)
        :type model_filename: str
        :param tagger: The tagger used to POS tag the raw string before
            formatting to CONLL format. It should behave like `nltk.pos_tag`
        :type tagger: function
        :param additional_java_args: This is the additional Java arguments that
            one can use when calling Maltparser, usually this is the heapsize
            limits, e.g. `additional_java_args=['-Xmx1024m']`
            (see https://goo.gl/mpDBvQ)
        :type additional_java_args: list
        """

        # Find all the necessary jar files for MaltParser.
        self.malt_jars = find_maltparser(parser_dirname)
        # Initialize additional java arguments.
        self.additional_java_args = (
            additional_java_args if additional_java_args is not None else []
        )
        # Initialize model.
        self.model = find_malt_model(model_filename)
        self._trained = self.model != "malt_temp.mco"
        # Set the working_dir parameters i.e. `-w` from MaltParser's option.
        self.working_dir = tempfile.gettempdir()
        # Initialize POS tagger.
        self.tagger = tagger if tagger is not None else malt_regex_tagger()

    def parse_tagged_sents(self, sentences, verbose=False, top_relation_label="null"):
        """
        Use MaltParser to parse multiple POS tagged sentences. Takes multiple
        sentences where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentence: list(list(tuple(str, str)))
        :return: iter(iter(``DependencyGraph``)) the dependency graph
            representation of each sentence
        """
        if not self._trained:
            raise Exception("Parser has not been trained. Call train() first.")

        with tempfile.NamedTemporaryFile(
            prefix="malt_input.conll.", dir=self.working_dir, mode="w", delete=False
        ) as input_file:
            with tempfile.NamedTemporaryFile(
                prefix="malt_output.conll.",
                dir=self.working_dir,
                mode="w",
                delete=False,
            ) as output_file:
                # Convert list of sentences to CONLL format.
                for line in taggedsents_to_conll(sentences):
                    input_file.write(str(line))
                input_file.close()

                # Generate command to run maltparser.
                cmd = self.generate_malt_command(
                    input_file.name, output_file.name, mode="parse"
                )

                # This is a maltparser quirk, it needs to be run
                # where the model file is. otherwise it goes into an awkward
                # missing .jars or strange -w working_dir problem.
                _current_path = os.getcwd()  # Remembers the current path.
                try:  # Change to modelfile path
                    os.chdir(os.path.split(self.model)[0])
                except:
                    pass
                ret = self._execute(cmd, verbose)  # Run command.
                os.chdir(_current_path)  # Change back to current path.

                if ret != 0:
                    raise Exception(
                        "MaltParser parsing (%s) failed with exit "
                        "code %d" % (" ".join(cmd), ret)
                    )

                # Must return iter(iter(Tree))
                with open(output_file.name) as infile:
                    for tree_str in infile.read().split("\n\n"):
                        yield (
                            iter(
                                [
                                    DependencyGraph(
                                        tree_str, top_relation_label=top_relation_label
                                    )
                                ]
                            )
                        )

        os.remove(input_file.name)
        os.remove(output_file.name)

    def parse_sents(self, sentences, verbose=False, top_relation_label="null"):
        """
        Use MaltParser to parse multiple sentences.
        Takes a list of sentences, where each sentence is a list of words.
        Each sentence will be automatically tagged with this
        MaltParser instance's tagger.

        :param sentences: Input sentences to parse
        :type sentence: list(list(str))
        :return: iter(DependencyGraph)
        """
        tagged_sentences = (self.tagger(sentence) for sentence in sentences)
        return self.parse_tagged_sents(
            tagged_sentences, verbose, top_relation_label=top_relation_label
        )

    def generate_malt_command(self, inputfilename, outputfilename=None, mode=None):
        """
        This function generates the maltparser command use at the terminal.

        :param inputfilename: path to the input file
        :type inputfilename: str
        :param outputfilename: path to the output file
        :type outputfilename: str
        """

        cmd = ["java"]
        cmd += self.additional_java_args  # Adds additional java arguments
        # Joins classpaths with ";" if on Windows and on Linux/Mac use ":"
        classpaths_separator = ";" if sys.platform.startswith("win") else ":"
        cmd += [
            "-cp",
            classpaths_separator.join(self.malt_jars),
        ]  # Adds classpaths for jars
        cmd += ["org.maltparser.Malt"]  # Adds the main function.

        # Adds the model file.
        if os.path.exists(self.model):  # when parsing
            cmd += ["-c", os.path.split(self.model)[-1]]
        else:  # when learning
            cmd += ["-c", self.model]

        cmd += ["-i", inputfilename]
        if mode == "parse":
            cmd += ["-o", outputfilename]
        cmd += ["-m", mode]  # mode use to generate parses.
        return cmd

    @staticmethod
    def _execute(cmd, verbose=False):
        output = None if verbose else subprocess.PIPE
        p = subprocess.Popen(cmd, stdout=output, stderr=output)
        return p.wait()

    def train(self, depgraphs, verbose=False):
        """
        Train MaltParser from a list of ``DependencyGraph`` objects

        :param depgraphs: list of ``DependencyGraph`` objects for training input data
        :type depgraphs: DependencyGraph
        """

        # Write the conll_str to malt_train.conll file in /tmp/
        with tempfile.NamedTemporaryFile(
            prefix="malt_train.conll.", dir=self.working_dir, mode="w", delete=False
        ) as input_file:
            input_str = "\n".join(dg.to_conll(10) for dg in depgraphs)
            input_file.write(str(input_str))
        # Trains the model with the malt_train.conll
        self.train_from_file(input_file.name, verbose=verbose)
        # Removes the malt_train.conll once training finishes.
        os.remove(input_file.name)

    def train_from_file(self, conll_file, verbose=False):
        """
        Train MaltParser from a file
        :param conll_file: str for the filename of the training input data
        :type conll_file: str
        """

        # If conll_file is a ZipFilePathPointer,
        # then we need to do some extra massaging
        if isinstance(conll_file, ZipFilePathPointer):
            with tempfile.NamedTemporaryFile(
                prefix="malt_train.conll.", dir=self.working_dir, mode="w", delete=False
            ) as input_file:
                with conll_file.open() as conll_input_file:
                    conll_str = conll_input_file.read()
                    input_file.write(str(conll_str))
                return self.train_from_file(input_file.name, verbose=verbose)

        # Generate command to run maltparser.
        cmd = self.generate_malt_command(conll_file, mode="learn")
        ret = self._execute(cmd, verbose)
        if ret != 0:
            raise Exception(
                "MaltParser training (%s) failed with exit "
                "code %d" % (" ".join(cmd), ret)
            )
        self._trained = True


if __name__ == "__main__":
    """
    A demonstration function to show how NLTK users can use the malt parser API.

    >>> from nltk import pos_tag
    >>> assert 'MALT_PARSER' in os.environ, str(
    ... "Please set MALT_PARSER in your global environment, e.g.:\n"
    ... "$ export MALT_PARSER='/home/user/maltparser-1.9.2/'")
    >>>
    >>> assert 'MALT_MODEL' in os.environ, str(
    ... "Please set MALT_MODEL in your global environment, e.g.:\n"
    ... "$ export MALT_MODEL='/home/user/engmalt.linear-1.7.mco'")
    >>>
    >>> _dg1_str = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
    ...             "2    sees    _    VB    _    _    0    ROOT    _    _\n"
    ...             "3    a       _    DT    _    _    4    SPEC    _    _\n"
    ...             "4    dog     _    NN    _    _    2    OBJ     _    _\n"
    ...             "5    .     _    .    _    _    2    PUNCT     _    _\n")
    >>>
    >>>
    >>> _dg2_str  = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
    ...             "2    walks   _    VB    _    _    0    ROOT    _    _\n"
    ...             "3    .     _    .    _    _    2    PUNCT     _    _\n")
    >>> dg1 = DependencyGraph(_dg1_str)
    >>> dg2 = DependencyGraph(_dg2_str)
    >>> # Initialize a MaltParser object
    >>> mp = MaltParser()
    >>>
    >>> # Trains a model.
    >>> mp.train([dg1,dg2], verbose=False)
    >>> sent1 = ['John','sees','Mary', '.']
    >>> sent2 = ['John', 'walks', 'a', 'dog', '.']
    >>>
    >>> # Parse a single sentence.
    >>> parsed_sent1 = mp.parse_one(sent1)
    >>> parsed_sent2 = mp.parse_one(sent2)
    >>> print(parsed_sent1.tree())
    (sees John Mary .)
    >>> print(parsed_sent2.tree())
    (walks John (dog a) .)
    >>>
    >>> # Parsing multiple sentences.
    >>> sentences = [sent1,sent2]
    >>> parsed_sents = mp.parse_sents(sentences)
    >>> print(next(next(parsed_sents)).tree())
    (sees John Mary .)
    >>> print(next(next(parsed_sents)).tree())
    (walks John (dog a) .)
    >>>
    >>> # Initialize a MaltParser object with an English pre-trained model.
    >>> parser_dirname = 'maltparser-1.9.2'
    >>> model_name = 'engmalt.linear-1.7.mco'
    >>> mp = MaltParser(parser_dirname=parser_dirname, model_filename=model_name, tagger=pos_tag)
    >>> sent1 = 'I shot an elephant in my pajamas .'.split()
    >>> sent2 = 'Time flies like banana .'.split()
    >>> # Parse a single sentence.
    >>> print(mp.parse_one(sent1).tree())
    (shot I (elephant an) (in (pajamas my)) .)
    # Parsing multiple sentences
    >>> sentences = [sent1,sent2]
    >>> parsed_sents = mp.parse_sents(sentences)
    >>> print(next(next(parsed_sents)).tree())
    (shot I (elephant an) (in (pajamas my)) .)
    >>> print(next(next(parsed_sents)).tree())
    (flies Time (like banana) .)
    """

    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_known_annotated_metadata.py ===
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from copy import copy
from functools import lru_cache, partial
from typing import TYPE_CHECKING, Any

from pydantic_core import CoreSchema, PydanticCustomError, ValidationError, to_jsonable_python
from pydantic_core import core_schema as cs

from ._fields import PydanticMetadata
from ._import_utils import import_cached_field_info

if TYPE_CHECKING:
    pass

STRICT = {'strict'}
FAIL_FAST = {'fail_fast'}
LENGTH_CONSTRAINTS = {'min_length', 'max_length'}
INEQUALITY = {'le', 'ge', 'lt', 'gt'}
NUMERIC_CONSTRAINTS = {'multiple_of', *INEQUALITY}
ALLOW_INF_NAN = {'allow_inf_nan'}

STR_CONSTRAINTS = {
    *LENGTH_CONSTRAINTS,
    *STRICT,
    'strip_whitespace',
    'to_lower',
    'to_upper',
    'pattern',
    'coerce_numbers_to_str',
}
BYTES_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}

LIST_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
TUPLE_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
SET_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT, *FAIL_FAST}
DICT_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}
GENERATOR_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *STRICT}
SEQUENCE_CONSTRAINTS = {*LENGTH_CONSTRAINTS, *FAIL_FAST}

FLOAT_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *ALLOW_INF_NAN, *STRICT}
DECIMAL_CONSTRAINTS = {'max_digits', 'decimal_places', *FLOAT_CONSTRAINTS}
INT_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *ALLOW_INF_NAN, *STRICT}
BOOL_CONSTRAINTS = STRICT
UUID_CONSTRAINTS = STRICT

DATE_TIME_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
TIMEDELTA_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
TIME_CONSTRAINTS = {*NUMERIC_CONSTRAINTS, *STRICT}
LAX_OR_STRICT_CONSTRAINTS = STRICT
ENUM_CONSTRAINTS = STRICT
COMPLEX_CONSTRAINTS = STRICT

UNION_CONSTRAINTS = {'union_mode'}
URL_CONSTRAINTS = {
    'max_length',
    'allowed_schemes',
    'host_required',
    'default_host',
    'default_port',
    'default_path',
}

TEXT_SCHEMA_TYPES = ('str', 'bytes', 'url', 'multi-host-url')
SEQUENCE_SCHEMA_TYPES = ('list', 'tuple', 'set', 'frozenset', 'generator', *TEXT_SCHEMA_TYPES)
NUMERIC_SCHEMA_TYPES = ('float', 'int', 'date', 'time', 'timedelta', 'datetime')

CONSTRAINTS_TO_ALLOWED_SCHEMAS: dict[str, set[str]] = defaultdict(set)

constraint_schema_pairings: list[tuple[set[str], tuple[str, ...]]] = [
    (STR_CONSTRAINTS, TEXT_SCHEMA_TYPES),
    (BYTES_CONSTRAINTS, ('bytes',)),
    (LIST_CONSTRAINTS, ('list',)),
    (TUPLE_CONSTRAINTS, ('tuple',)),
    (SET_CONSTRAINTS, ('set', 'frozenset')),
    (DICT_CONSTRAINTS, ('dict',)),
    (GENERATOR_CONSTRAINTS, ('generator',)),
    (FLOAT_CONSTRAINTS, ('float',)),
    (INT_CONSTRAINTS, ('int',)),
    (DATE_TIME_CONSTRAINTS, ('date', 'time', 'datetime', 'timedelta')),
    # TODO: this is a bit redundant, we could probably avoid some of these
    (STRICT, (*TEXT_SCHEMA_TYPES, *SEQUENCE_SCHEMA_TYPES, *NUMERIC_SCHEMA_TYPES, 'typed-dict', 'model')),
    (UNION_CONSTRAINTS, ('union',)),
    (URL_CONSTRAINTS, ('url', 'multi-host-url')),
    (BOOL_CONSTRAINTS, ('bool',)),
    (UUID_CONSTRAINTS, ('uuid',)),
    (LAX_OR_STRICT_CONSTRAINTS, ('lax-or-strict',)),
    (ENUM_CONSTRAINTS, ('enum',)),
    (DECIMAL_CONSTRAINTS, ('decimal',)),
    (COMPLEX_CONSTRAINTS, ('complex',)),
]

for constraints, schemas in constraint_schema_pairings:
    for c in constraints:
        CONSTRAINTS_TO_ALLOWED_SCHEMAS[c].update(schemas)


def as_jsonable_value(v: Any) -> Any:
    if type(v) not in (int, str, float, bytes, bool, type(None)):
        return to_jsonable_python(v)
    return v


def expand_grouped_metadata(annotations: Iterable[Any]) -> Iterable[Any]:
    """Expand the annotations.

    Args:
        annotations: An iterable of annotations.

    Returns:
        An iterable of expanded annotations.

    Example:
        ```python
        from annotated_types import Ge, Len

        from pydantic._internal._known_annotated_metadata import expand_grouped_metadata

        print(list(expand_grouped_metadata([Ge(4), Len(5)])))
        #> [Ge(ge=4), MinLen(min_length=5)]
        ```
    """
    import annotated_types as at

    FieldInfo = import_cached_field_info()

    for annotation in annotations:
        if isinstance(annotation, at.GroupedMetadata):
            yield from annotation
        elif isinstance(annotation, FieldInfo):
            yield from annotation.metadata
            # this is a bit problematic in that it results in duplicate metadata
            # all of our "consumers" can handle it, but it is not ideal
            # we probably should split up FieldInfo into:
            # - annotated types metadata
            # - individual metadata known only to Pydantic
            annotation = copy(annotation)
            annotation.metadata = []
            yield annotation
        else:
            yield annotation


@lru_cache
def _get_at_to_constraint_map() -> dict[type, str]:
    """Return a mapping of annotated types to constraints.

    Normally, we would define a mapping like this in the module scope, but we can't do that
    because we don't permit module level imports of `annotated_types`, in an attempt to speed up
    the import time of `pydantic`. We still only want to have this dictionary defined in one place,
    so we use this function to cache the result.
    """
    import annotated_types as at

    return {
        at.Gt: 'gt',
        at.Ge: 'ge',
        at.Lt: 'lt',
        at.Le: 'le',
        at.MultipleOf: 'multiple_of',
        at.MinLen: 'min_length',
        at.MaxLen: 'max_length',
    }


def apply_known_metadata(annotation: Any, schema: CoreSchema) -> CoreSchema | None:  # noqa: C901
    """Apply `annotation` to `schema` if it is an annotation we know about (Gt, Le, etc.).
    Otherwise return `None`.

    This does not handle all known annotations. If / when it does, it can always
    return a CoreSchema and return the unmodified schema if the annotation should be ignored.

    Assumes that GroupedMetadata has already been expanded via `expand_grouped_metadata`.

    Args:
        annotation: The annotation.
        schema: The schema.

    Returns:
        An updated schema with annotation if it is an annotation we know about, `None` otherwise.

    Raises:
        PydanticCustomError: If `Predicate` fails.
    """
    import annotated_types as at

    from ._validators import NUMERIC_VALIDATOR_LOOKUP, forbid_inf_nan_check

    schema = schema.copy()
    schema_update, other_metadata = collect_known_metadata([annotation])
    schema_type = schema['type']

    chain_schema_constraints: set[str] = {
        'pattern',
        'strip_whitespace',
        'to_lower',
        'to_upper',
        'coerce_numbers_to_str',
    }
    chain_schema_steps: list[CoreSchema] = []

    for constraint, value in schema_update.items():
        if constraint not in CONSTRAINTS_TO_ALLOWED_SCHEMAS:
            raise ValueError(f'Unknown constraint {constraint}')
        allowed_schemas = CONSTRAINTS_TO_ALLOWED_SCHEMAS[constraint]

        # if it becomes necessary to handle more than one constraint
        # in this recursive case with function-after or function-wrap, we should refactor
        # this is a bit challenging because we sometimes want to apply constraints to the inner schema,
        # whereas other times we want to wrap the existing schema with a new one that enforces a new constraint.
        if schema_type in {'function-before', 'function-wrap', 'function-after'} and constraint == 'strict':
            schema['schema'] = apply_known_metadata(annotation, schema['schema'])  # type: ignore  # schema is function schema
            return schema

        # if we're allowed to apply constraint directly to the schema, like le to int, do that
        if schema_type in allowed_schemas:
            if constraint == 'union_mode' and schema_type == 'union':
                schema['mode'] = value  # type: ignore  # schema is UnionSchema
            else:
                schema[constraint] = value
            continue

        #  else, apply a function after validator to the schema to enforce the corresponding constraint
        if constraint in chain_schema_constraints:

            def _apply_constraint_with_incompatibility_info(
                value: Any, handler: cs.ValidatorFunctionWrapHandler
            ) -> Any:
                try:
                    x = handler(value)
                except ValidationError as ve:
                    # if the error is about the type, it's likely that the constraint is incompatible the type of the field
                    # for example, the following invalid schema wouldn't be caught during schema build, but rather at this point
                    # with a cryptic 'string_type' error coming from the string validator,
                    # that we'd rather express as a constraint incompatibility error (TypeError)
                    # Annotated[list[int], Field(pattern='abc')]
                    if 'type' in ve.errors()[0]['type']:
                        raise TypeError(
                            f"Unable to apply constraint '{constraint}' to supplied value {value} for schema of type '{schema_type}'"  # noqa: B023
                        )
                    raise ve
                return x

            chain_schema_steps.append(
                cs.no_info_wrap_validator_function(
                    _apply_constraint_with_incompatibility_info, cs.str_schema(**{constraint: value})
                )
            )
        elif constraint in NUMERIC_VALIDATOR_LOOKUP:
            if constraint in LENGTH_CONSTRAINTS:
                inner_schema = schema
                while inner_schema['type'] in {'function-before', 'function-wrap', 'function-after'}:
                    inner_schema = inner_schema['schema']  # type: ignore
                inner_schema_type = inner_schema['type']
                if inner_schema_type == 'list' or (
                    inner_schema_type == 'json-or-python' and inner_schema['json_schema']['type'] == 'list'  # type: ignore
                ):
                    js_constraint_key = 'minItems' if constraint == 'min_length' else 'maxItems'
                else:
                    js_constraint_key = 'minLength' if constraint == 'min_length' else 'maxLength'
            else:
                js_constraint_key = constraint

            schema = cs.no_info_after_validator_function(
                partial(NUMERIC_VALIDATOR_LOOKUP[constraint], **{constraint: value}), schema
            )
            metadata = schema.get('metadata', {})
            if (existing_json_schema_updates := metadata.get('pydantic_js_updates')) is not None:
                metadata['pydantic_js_updates'] = {
                    **existing_json_schema_updates,
                    **{js_constraint_key: as_jsonable_value(value)},
                }
            else:
                metadata['pydantic_js_updates'] = {js_constraint_key: as_jsonable_value(value)}
            schema['metadata'] = metadata
        elif constraint == 'allow_inf_nan' and value is False:
            schema = cs.no_info_after_validator_function(
                forbid_inf_nan_check,
                schema,
            )
        else:
            # It's rare that we'd get here, but it's possible if we add a new constraint and forget to handle it
            # Most constraint errors are caught at runtime during attempted application
            raise RuntimeError(f"Unable to apply constraint '{constraint}' to schema of type '{schema_type}'")

    for annotation in other_metadata:
        if (annotation_type := type(annotation)) in (at_to_constraint_map := _get_at_to_constraint_map()):
            constraint = at_to_constraint_map[annotation_type]
            validator = NUMERIC_VALIDATOR_LOOKUP.get(constraint)
            if validator is None:
                raise ValueError(f'Unknown constraint {constraint}')
            schema = cs.no_info_after_validator_function(
                partial(validator, {constraint: getattr(annotation, constraint)}), schema
            )
            continue
        elif isinstance(annotation, (at.Predicate, at.Not)):
            predicate_name = f'{annotation.func.__qualname__}' if hasattr(annotation.func, '__qualname__') else ''

            def val_func(v: Any) -> Any:
                predicate_satisfied = annotation.func(v)  # noqa: B023

                # annotation.func may also raise an exception, let it pass through
                if isinstance(annotation, at.Predicate):  # noqa: B023
                    if not predicate_satisfied:
                        raise PydanticCustomError(
                            'predicate_failed',
                            f'Predicate {predicate_name} failed',  # type: ignore  # noqa: B023
                        )
                else:
                    if predicate_satisfied:
                        raise PydanticCustomError(
                            'not_operation_failed',
                            f'Not of {predicate_name} failed',  # type: ignore  # noqa: B023
                        )

                return v

            schema = cs.no_info_after_validator_function(val_func, schema)
        else:
            # ignore any other unknown metadata
            return None

    if chain_schema_steps:
        chain_schema_steps = [schema] + chain_schema_steps
        return cs.chain_schema(chain_schema_steps)

    return schema


def collect_known_metadata(annotations: Iterable[Any]) -> tuple[dict[str, Any], list[Any]]:
    """Split `annotations` into known metadata and unknown annotations.

    Args:
        annotations: An iterable of annotations.

    Returns:
        A tuple contains a dict of known metadata and a list of unknown annotations.

    Example:
        ```python
        from annotated_types import Gt, Len

        from pydantic._internal._known_annotated_metadata import collect_known_metadata

        print(collect_known_metadata([Gt(1), Len(42), ...]))
        #> ({'gt': 1, 'min_length': 42}, [Ellipsis])
        ```
    """
    annotations = expand_grouped_metadata(annotations)

    res: dict[str, Any] = {}
    remaining: list[Any] = []

    for annotation in annotations:
        # isinstance(annotation, PydanticMetadata) also covers ._fields:_PydanticGeneralMetadata
        if isinstance(annotation, PydanticMetadata):
            res.update(annotation.__dict__)
        # we don't use dataclasses.asdict because that recursively calls asdict on the field values
        elif (annotation_type := type(annotation)) in (at_to_constraint_map := _get_at_to_constraint_map()):
            constraint = at_to_constraint_map[annotation_type]
            res[constraint] = getattr(annotation, constraint)
        elif isinstance(annotation, type) and issubclass(annotation, PydanticMetadata):
            # also support PydanticMetadata classes being used without initialisation,
            # e.g. `Annotated[int, Strict]` as well as `Annotated[int, Strict()]`
            res.update({k: v for k, v in vars(annotation).items() if not k.startswith('_')})
        else:
            remaining.append(annotation)
    # Nones can sneak in but pydantic-core will reject them
    # it'd be nice to clean things up so we don't put in None (we probably don't _need_ to, it was just easier)
    # but this is simple enough to kick that can down the road
    res = {k: v for k, v in res.items() if v is not None}
    return res, remaining


def check_metadata(metadata: dict[str, Any], allowed: Iterable[str], source_type: Any) -> None:
    """A small utility function to validate that the given metadata can be applied to the target.
    More than saving lines of code, this gives us a consistent error message for all of our internal implementations.

    Args:
        metadata: A dict of metadata.
        allowed: An iterable of allowed metadata.
        source_type: The source type.

    Raises:
        TypeError: If there is metadatas that can't be applied on source type.
    """
    unknown = metadata.keys() - set(allowed)
    if unknown:
        raise TypeError(
            f'The following constraints cannot be applied to {source_type!r}: {", ".join([f"{k!r}" for k in unknown])}'
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\watsonx\completion\transformation.py ===
import time
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

import httpx

from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.types.llms.openai import AllMessageValues, ChatCompletionUsageBlock
from litellm.types.llms.watsonx import WatsonXAIEndpoint
from litellm.types.utils import GenericStreamingChunk, ModelResponse, Usage
from litellm.utils import map_finish_reason

from ...base_llm.chat.transformation import BaseConfig
from ..common_utils import (
    IBMWatsonXMixin,
    WatsonXAIError,
    _get_api_params,
    convert_watsonx_messages_to_prompt,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class IBMWatsonXAIConfig(IBMWatsonXMixin, BaseConfig):
    """
    Reference: https://cloud.ibm.com/apidocs/watsonx-ai#text-generation
    (See ibm_watsonx_ai.metanames.GenTextParamsMetaNames for a list of all available params)

    Supported params for all available watsonx.ai foundational models.

    - `decoding_method` (str): One of "greedy" or "sample"

    - `temperature` (float): Sets the model temperature for sampling - not available when decoding_method='greedy'.

    - `max_new_tokens` (integer): Maximum length of the generated tokens.

    - `min_new_tokens` (integer): Maximum length of input tokens. Any more than this will be truncated.

    - `length_penalty` (dict): A dictionary with keys "decay_factor" and "start_index".

    - `stop_sequences` (string[]): list of strings to use as stop sequences.

    - `top_k` (integer): top k for sampling - not available when decoding_method='greedy'.

    - `top_p` (integer): top p for sampling - not available when decoding_method='greedy'.

    - `repetition_penalty` (float): token repetition penalty during text generation.

    - `truncate_input_tokens` (integer): Truncate input tokens to this length.

    - `include_stop_sequences` (bool): If True, the stop sequence will be included at the end of the generated text in the case of a match.

    - `return_options` (dict): A dictionary of options to return. Options include "input_text", "generated_tokens", "input_tokens", "token_ranks". Values are boolean.

    - `random_seed` (integer): Random seed for text generation.

    - `moderations` (dict): Dictionary of properties that control the moderations, for usages such as Hate and profanity (HAP) and PII filtering.

    - `stream` (bool): If True, the model will return a stream of responses.
    """

    decoding_method: Optional[str] = "sample"
    temperature: Optional[float] = None
    max_new_tokens: Optional[int] = None  # litellm.max_tokens
    min_new_tokens: Optional[int] = None
    length_penalty: Optional[dict] = None  # e.g {"decay_factor": 2.5, "start_index": 5}
    stop_sequences: Optional[List[str]] = None  # e.g ["}", ")", "."]
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    truncate_input_tokens: Optional[int] = None
    include_stop_sequences: Optional[bool] = False
    return_options: Optional[Dict[str, bool]] = None
    random_seed: Optional[int] = None  # e.g 42
    moderations: Optional[dict] = None
    stream: Optional[bool] = False

    def __init__(
        self,
        decoding_method: Optional[str] = None,
        temperature: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        min_new_tokens: Optional[int] = None,
        length_penalty: Optional[dict] = None,
        stop_sequences: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        truncate_input_tokens: Optional[int] = None,
        include_stop_sequences: Optional[bool] = None,
        return_options: Optional[dict] = None,
        random_seed: Optional[int] = None,
        moderations: Optional[dict] = None,
        stream: Optional[bool] = None,
        **kwargs,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def is_watsonx_text_param(self, param: str) -> bool:
        """
        Determine if user passed in a watsonx.ai text generation param
        """
        text_generation_params = [
            "decoding_method",
            "max_new_tokens",
            "min_new_tokens",
            "length_penalty",
            "stop_sequences",
            "top_k",
            "repetition_penalty",
            "truncate_input_tokens",
            "include_stop_sequences",
            "return_options",
            "random_seed",
            "moderations",
            "decoding_method",
            "min_tokens",
        ]

        return param in text_generation_params

    def get_supported_openai_params(self, model: str):
        return [
            "temperature",  # equivalent to temperature
            "max_tokens",  # equivalent to max_new_tokens
            "top_p",  # equivalent to top_p
            "frequency_penalty",  # equivalent to repetition_penalty
            "stop",  # equivalent to stop_sequences
            "seed",  # equivalent to random_seed
            "stream",  # equivalent to stream
        ]

    def map_openai_params(
        self,
        non_default_params: Dict,
        optional_params: Dict,
        model: str,
        drop_params: bool,
    ) -> Dict:
        extra_body = {}
        for k, v in non_default_params.items():
            if k == "max_tokens":
                optional_params["max_new_tokens"] = v
            elif k == "stream":
                optional_params["stream"] = v
            elif k == "temperature":
                optional_params["temperature"] = v
            elif k == "top_p":
                optional_params["top_p"] = v
            elif k == "frequency_penalty":
                optional_params["repetition_penalty"] = v
            elif k == "seed":
                optional_params["random_seed"] = v
            elif k == "stop":
                optional_params["stop_sequences"] = v
            elif k == "decoding_method":
                extra_body["decoding_method"] = v
            elif k == "min_tokens":
                extra_body["min_new_tokens"] = v
            elif k == "top_k":
                extra_body["top_k"] = v
            elif k == "truncate_input_tokens":
                extra_body["truncate_input_tokens"] = v
            elif k == "length_penalty":
                extra_body["length_penalty"] = v
            elif k == "time_limit":
                extra_body["time_limit"] = v
            elif k == "return_options":
                extra_body["return_options"] = v

        if extra_body:
            optional_params["extra_body"] = extra_body
        return optional_params

    def get_mapped_special_auth_params(self) -> dict:
        """
        Common auth params across bedrock/vertex_ai/azure/watsonx
        """
        return {
            "project": "watsonx_project",
            "region_name": "watsonx_region_name",
            "token": "watsonx_token",
        }

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        mapped_params = self.get_mapped_special_auth_params()

        for param, value in non_default_params.items():
            if param in mapped_params:
                optional_params[mapped_params[param]] = value
        return optional_params

    def get_eu_regions(self) -> List[str]:
        """
        Source: https://www.ibm.com/docs/en/watsonx/saas?topic=integrations-regional-availability
        """
        return [
            "eu-de",
            "eu-gb",
        ]

    def get_us_regions(self) -> List[str]:
        """
        Source: https://www.ibm.com/docs/en/watsonx/saas?topic=integrations-regional-availability
        """
        return [
            "us-south",
        ]

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        headers: Dict,
    ) -> Dict:
        provider = model.split("/")[0]
        prompt = convert_watsonx_messages_to_prompt(
            model=model,
            messages=messages,
            provider=provider,
            custom_prompt_dict={},
        )
        extra_body_params = optional_params.pop("extra_body", {})
        optional_params.update(extra_body_params)
        watsonx_api_params = _get_api_params(params=optional_params)

        watsonx_auth_payload = self._prepare_payload(
            model=model,
            api_params=watsonx_api_params,
        )

        # init the payload to the text generation call
        payload = {
            "input": prompt,
            "moderations": optional_params.pop("moderations", {}),
            "parameters": optional_params,
            **watsonx_auth_payload,
        }

        return payload

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response=raw_response.text,
        )

        json_resp = raw_response.json()

        if "results" not in json_resp:
            raise WatsonXAIError(
                status_code=500,
                message=f"Error: Invalid response from Watsonx.ai API: {json_resp}",
            )
        if model_response is None:
            model_response = ModelResponse(model=json_resp.get("model_id", None))
        generated_text = json_resp["results"][0]["generated_text"]
        prompt_tokens = json_resp["results"][0]["input_token_count"]
        completion_tokens = json_resp["results"][0]["generated_token_count"]
        model_response.choices[0].message.content = generated_text  # type: ignore
        model_response.choices[0].finish_reason = map_finish_reason(
            json_resp["results"][0]["stop_reason"]
        )
        if json_resp.get("created_at"):
            model_response.created = int(
                datetime.fromisoformat(json_resp["created_at"]).timestamp()
            )
        else:
            model_response.created = int(time.time())
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        url = self._get_base_url(api_base=api_base)
        if model.startswith("deployment/"):
            # deployment models are passed in as 'deployment/<deployment_id>'
            deployment_id = "/".join(model.split("/")[1:])
            endpoint = (
                WatsonXAIEndpoint.DEPLOYMENT_TEXT_GENERATION_STREAM.value
                if stream
                else WatsonXAIEndpoint.DEPLOYMENT_TEXT_GENERATION.value
            )
            endpoint = endpoint.format(deployment_id=deployment_id)
        else:
            endpoint = (
                WatsonXAIEndpoint.TEXT_GENERATION_STREAM
                if stream
                else WatsonXAIEndpoint.TEXT_GENERATION
            )
        url = url.rstrip("/") + endpoint

        ## add api version
        url = self._add_api_version_to_url(
            url=url, api_version=optional_params.pop("api_version", None)
        )
        return url

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return WatsonxTextCompletionResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class WatsonxTextCompletionResponseIterator(BaseModelResponseIterator):
    # def _handle_string_chunk(self, str_line: str) -> GenericStreamingChunk:
    #     return self.chunk_parser(json.loads(str_line))

    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            results = chunk.get("results", [])
            if len(results) > 0:
                text = results[0].get("generated_text", "")
                finish_reason = results[0].get("stop_reason")
                is_finished = finish_reason != "not_finished"

                return GenericStreamingChunk(
                    text=text,
                    is_finished=is_finished,
                    finish_reason=finish_reason,
                    usage=ChatCompletionUsageBlock(
                        prompt_tokens=results[0].get("input_token_count", 0),
                        completion_tokens=results[0].get("generated_token_count", 0),
                        total_tokens=results[0].get("input_token_count", 0)
                        + results[0].get("generated_token_count", 0),
                    ),
                )
            return GenericStreamingChunk(
                text="",
                is_finished=False,
                finish_reason="stop",
                usage=None,
            )
        except Exception as e:
            raise e

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\transports\grpc_asyncio.py ===
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

from google.ai.generativelanguage_v1beta3.types import text_service

from .base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .grpc import TextServiceGrpcTransport


class TextServiceGrpcAsyncIOTransport(TextServiceTransport):
    """gRPC AsyncIO backend transport for TextService.

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
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], Awaitable[text_service.GenerateTextResponse]
    ]:
        r"""Return a callable for the generate text method over gRPC.

        Generates a response from the model given an input
        message.

        Returns:
            Callable[[~.GenerateTextRequest],
                    Awaitable[~.GenerateTextResponse]]:
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
    ) -> Callable[
        [text_service.EmbedTextRequest], Awaitable[text_service.EmbedTextResponse]
    ]:
        r"""Return a callable for the embed text method over gRPC.

        Generates an embedding from the model given an input
        message.

        Returns:
            Callable[[~.EmbedTextRequest],
                    Awaitable[~.EmbedTextResponse]]:
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
        [text_service.BatchEmbedTextRequest],
        Awaitable[text_service.BatchEmbedTextResponse],
    ]:
        r"""Return a callable for the batch embed text method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedTextRequest],
                    Awaitable[~.BatchEmbedTextResponse]]:
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
        [text_service.CountTextTokensRequest],
        Awaitable[text_service.CountTextTokensResponse],
    ]:
        r"""Return a callable for the count text tokens method over gRPC.

        Runs a model's tokenizer on a text and returns the
        token count.

        Returns:
            Callable[[~.CountTextTokensRequest],
                    Awaitable[~.CountTextTokensResponse]]:
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

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_text: gapic_v1.method_async.wrap_method(
                self.generate_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.embed_text: gapic_v1.method_async.wrap_method(
                self.embed_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.batch_embed_text: gapic_v1.method_async.wrap_method(
                self.batch_embed_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.count_text_tokens: gapic_v1.method_async.wrap_method(
                self.count_text_tokens,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("TextServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\argilla.py ===
"""
Send logs to Argilla for annotation
"""

import asyncio
import json
import os
import random
import types
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel  # type: ignore

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.integrations.custom_logger import CustomLogger
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.argilla import (
    SUPPORTED_PAYLOAD_FIELDS,
    ArgillaCredentialsObject,
    ArgillaItem,
)
from litellm.types.utils import StandardLoggingPayload


def is_serializable(value):
    non_serializable_types = (
        types.CoroutineType,
        types.FunctionType,
        types.GeneratorType,
        BaseModel,
    )
    return not isinstance(value, non_serializable_types)


class ArgillaLogger(CustomBatchLogger):
    def __init__(
        self,
        argilla_api_key: Optional[str] = None,
        argilla_dataset_name: Optional[str] = None,
        argilla_base_url: Optional[str] = None,
        **kwargs,
    ):
        if litellm.argilla_transformation_object is None:
            raise Exception(
                "'litellm.argilla_transformation_object' is required, to log your payload to Argilla."
            )
        self.validate_argilla_transformation_object(
            litellm.argilla_transformation_object
        )
        self.argilla_transformation_object = litellm.argilla_transformation_object
        self.default_credentials = self.get_credentials_from_env(
            argilla_api_key=argilla_api_key,
            argilla_dataset_name=argilla_dataset_name,
            argilla_base_url=argilla_base_url,
        )
        self.sampling_rate: float = (
            float(os.getenv("ARGILLA_SAMPLING_RATE"))  # type: ignore
            if os.getenv("ARGILLA_SAMPLING_RATE") is not None
            and os.getenv("ARGILLA_SAMPLING_RATE").strip().isdigit()  # type: ignore
            else 1.0
        )

        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        _batch_size = (
            os.getenv("ARGILLA_BATCH_SIZE", None) or litellm.argilla_batch_size
        )
        if _batch_size:
            self.batch_size = int(_batch_size)
        asyncio.create_task(self.periodic_flush())
        self.flush_lock = asyncio.Lock()
        super().__init__(**kwargs, flush_lock=self.flush_lock)

    def validate_argilla_transformation_object(
        self, argilla_transformation_object: Dict[str, Any]
    ):
        if not isinstance(argilla_transformation_object, dict):
            raise Exception(
                "'argilla_transformation_object' must be a dictionary, to log your payload to Argilla."
            )

        for v in argilla_transformation_object.values():
            if v not in SUPPORTED_PAYLOAD_FIELDS:
                raise Exception(
                    f"All values in argilla_transformation_object must be a key in SUPPORTED_PAYLOAD_FIELDS, {v} is not a valid key."
                )

    def get_credentials_from_env(
        self,
        argilla_api_key: Optional[str],
        argilla_dataset_name: Optional[str],
        argilla_base_url: Optional[str],
    ) -> ArgillaCredentialsObject:
        _credentials_api_key = argilla_api_key or os.getenv("ARGILLA_API_KEY")
        if _credentials_api_key is None:
            raise Exception("Invalid Argilla API Key given. _credentials_api_key=None.")

        _credentials_base_url = (
            argilla_base_url
            or os.getenv("ARGILLA_BASE_URL")
            or "http://localhost:6900/"
        )
        if _credentials_base_url is None:
            raise Exception(
                "Invalid Argilla Base URL given. _credentials_base_url=None."
            )

        _credentials_dataset_name = (
            argilla_dataset_name
            or os.getenv("ARGILLA_DATASET_NAME")
            or "litellm-completion"
        )
        if _credentials_dataset_name is None:
            raise Exception("Invalid Argilla Dataset give. Value=None.")
        else:
            dataset_response = litellm.module_level_client.get(
                url=f"{_credentials_base_url}/api/v1/me/datasets?name={_credentials_dataset_name}",
                headers={"X-Argilla-Api-Key": _credentials_api_key},
            )
            json_response = dataset_response.json()
            if (
                "items" in json_response
                and isinstance(json_response["items"], list)
                and len(json_response["items"]) > 0
            ):
                _credentials_dataset_name = json_response["items"][0]["id"]

        return ArgillaCredentialsObject(
            ARGILLA_API_KEY=_credentials_api_key,
            ARGILLA_BASE_URL=_credentials_base_url,
            ARGILLA_DATASET_NAME=_credentials_dataset_name,
        )

    def get_chat_messages(
        self, payload: StandardLoggingPayload
    ) -> List[Dict[str, Any]]:
        payload_messages = payload.get("messages", None)

        if payload_messages is None:
            raise Exception("No chat messages found in payload.")

        if (
            isinstance(payload_messages, list)
            and len(payload_messages) > 0
            and isinstance(payload_messages[0], dict)
        ):
            return payload_messages
        elif isinstance(payload_messages, dict):
            return [payload_messages]
        else:
            raise Exception(f"Invalid chat messages format: {payload_messages}")

    def get_str_response(self, payload: StandardLoggingPayload) -> str:
        response = payload["response"]

        if response is None:
            raise Exception("No response found in payload.")

        if isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
        else:
            raise Exception(f"Invalid response format: {response}")

    def _prepare_log_data(
        self, kwargs, response_obj, start_time, end_time
    ) -> Optional[ArgillaItem]:
        try:
            # Ensure everything in the payload is converted to str
            payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )

            if payload is None:
                raise Exception("Error logging request payload. Payload=none.")

            argilla_message = self.get_chat_messages(payload)
            argilla_response = self.get_str_response(payload)
            argilla_item: ArgillaItem = {"fields": {}}
            for k, v in self.argilla_transformation_object.items():
                if v == "messages":
                    argilla_item["fields"][k] = argilla_message
                elif v == "response":
                    argilla_item["fields"][k] = argilla_response
                else:
                    argilla_item["fields"][k] = payload.get(v, None)

            return argilla_item
        except Exception:
            raise

    def _send_batch(self):
        if not self.log_queue:
            return

        argilla_api_base = self.default_credentials["ARGILLA_BASE_URL"]
        argilla_dataset_name = self.default_credentials["ARGILLA_DATASET_NAME"]

        url = f"{argilla_api_base}/api/v1/datasets/{argilla_dataset_name}/records/bulk"

        argilla_api_key = self.default_credentials["ARGILLA_API_KEY"]

        headers = {"X-Argilla-Api-Key": argilla_api_key}

        try:
            response = litellm.module_level_client.post(
                url=url,
                json=self.log_queue,
                headers=headers,
            )

            if response.status_code >= 300:
                verbose_logger.error(
                    f"Argilla Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.debug(
                    f"Batch of {len(self.log_queue)} runs successfully created"
                )

            self.log_queue.clear()
        except Exception:
            verbose_logger.exception("Argilla Layer Error - Error sending batch.")

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            sampling_rate = (
                float(os.getenv("LANGSMITH_SAMPLING_RATE"))  # type: ignore
                if os.getenv("LANGSMITH_SAMPLING_RATE") is not None
                and os.getenv("LANGSMITH_SAMPLING_RATE").strip().isdigit()  # type: ignore
                else 1.0
            )
            random_sample = random.random()
            if random_sample > sampling_rate:
                verbose_logger.info(
                    "Skipping Langsmith logging. Sampling rate={}, random_sample={}".format(
                        sampling_rate, random_sample
                    )
                )
                return  # Skip logging
            verbose_logger.debug(
                "Langsmith Sync Layer Logging - kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            if data is None:
                return

            self.log_queue.append(data)
            verbose_logger.debug(
                f"Langsmith, event added to queue. Will flush in {self.flush_interval} seconds..."
            )

            if len(self.log_queue) >= self.batch_size:
                self._send_batch()

        except Exception:
            verbose_logger.exception("Langsmith Layer Error - log_success_event error")

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            sampling_rate = self.sampling_rate
            random_sample = random.random()
            if random_sample > sampling_rate:
                verbose_logger.info(
                    "Skipping Langsmith logging. Sampling rate={}, random_sample={}".format(
                        sampling_rate, random_sample
                    )
                )
                return  # Skip logging
            verbose_logger.debug(
                "Langsmith Async Layer Logging - kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )
            payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )

            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)

            ## ALLOW CUSTOM LOGGERS TO MODIFY / FILTER DATA BEFORE LOGGING
            for callback in litellm.callbacks:
                if isinstance(callback, CustomLogger):
                    try:
                        if data is None:
                            break
                        data = await callback.async_dataset_hook(data, payload)
                    except NotImplementedError:
                        pass

            if data is None:
                return

            self.log_queue.append(data)
            verbose_logger.debug(
                "Langsmith logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                await self.flush_queue()
        except Exception:
            verbose_logger.exception(
                "Argilla Layer Error - error logging async success event."
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        sampling_rate = self.sampling_rate
        random_sample = random.random()
        if random_sample > sampling_rate:
            verbose_logger.info(
                "Skipping Langsmith logging. Sampling rate={}, random_sample={}".format(
                    sampling_rate, random_sample
                )
            )
            return  # Skip logging
        verbose_logger.info("Langsmith Failure Event Logging!")
        try:
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            self.log_queue.append(data)
            verbose_logger.debug(
                "Langsmith logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                await self.flush_queue()
        except Exception:
            verbose_logger.exception(
                "Langsmith Layer Error - error logging async failure event."
            )

    async def async_send_batch(self):
        """
        sends runs to /batch endpoint

        Sends runs from self.log_queue

        Returns: None

        Raises: Does not raise an exception, will only verbose_logger.exception()
        """
        if not self.log_queue:
            return

        argilla_api_base = self.default_credentials["ARGILLA_BASE_URL"]
        argilla_dataset_name = self.default_credentials["ARGILLA_DATASET_NAME"]

        url = f"{argilla_api_base}/api/v1/datasets/{argilla_dataset_name}/records/bulk"

        argilla_api_key = self.default_credentials["ARGILLA_API_KEY"]

        headers = {"X-Argilla-Api-Key": argilla_api_key}

        try:
            response = await self.async_httpx_client.put(
                url=url,
                data=json.dumps(
                    {
                        "items": self.log_queue,
                    }
                ),
                headers=headers,
                timeout=60000,
            )
            response.raise_for_status()

            if response.status_code >= 300:
                verbose_logger.error(
                    f"Argilla Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.debug(
                    "Batch of %s runs successfully created", len(self.log_queue)
                )
        except httpx.HTTPStatusError:
            verbose_logger.exception("Argilla HTTP Error")
        except Exception:
            verbose_logger.exception("Argilla Layer Error")

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\custom_guardrail.py ===
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.types.guardrails import (
    DynamicGuardrailParams,
    GuardrailEventHooks,
    LitellmParams,
    PiiEntityType,
)
from litellm.types.utils import StandardLoggingGuardrailInformation


class CustomGuardrail(CustomLogger):
    def __init__(
        self,
        guardrail_name: Optional[str] = None,
        supported_event_hooks: Optional[List[GuardrailEventHooks]] = None,
        event_hook: Optional[
            Union[GuardrailEventHooks, List[GuardrailEventHooks]]
        ] = None,
        default_on: bool = False,
        mask_request_content: bool = False,
        mask_response_content: bool = False,
        **kwargs,
    ):
        """
        Initialize the CustomGuardrail class

        Args:
            guardrail_name: The name of the guardrail. This is the name used in your requests.
            supported_event_hooks: The event hooks that the guardrail supports
            event_hook: The event hook to run the guardrail on
            default_on: If True, the guardrail will be run by default on all requests
            mask_request_content: If True, the guardrail will mask the request content
            mask_response_content: If True, the guardrail will mask the response content
        """
        self.guardrail_name = guardrail_name
        self.supported_event_hooks = supported_event_hooks
        self.event_hook: Optional[
            Union[GuardrailEventHooks, List[GuardrailEventHooks]]
        ] = event_hook
        self.default_on: bool = default_on
        self.mask_request_content: bool = mask_request_content
        self.mask_response_content: bool = mask_response_content

        if supported_event_hooks:
            ## validate event_hook is in supported_event_hooks
            self._validate_event_hook(event_hook, supported_event_hooks)
        super().__init__(**kwargs)

    def _validate_event_hook(
        self,
        event_hook: Optional[Union[GuardrailEventHooks, List[GuardrailEventHooks]]],
        supported_event_hooks: List[GuardrailEventHooks],
    ) -> None:
        if event_hook is None:
            return
        if isinstance(event_hook, list):
            for hook in event_hook:
                if hook not in supported_event_hooks:
                    raise ValueError(
                        f"Event hook {hook} is not in the supported event hooks {supported_event_hooks}"
                    )
        elif isinstance(event_hook, GuardrailEventHooks):
            if event_hook not in supported_event_hooks:
                raise ValueError(
                    f"Event hook {event_hook} is not in the supported event hooks {supported_event_hooks}"
                )

    def get_guardrail_from_metadata(
        self, data: dict
    ) -> Union[List[str], List[Dict[str, DynamicGuardrailParams]]]:
        """
        Returns the guardrail(s) to be run from the metadata
        """
        metadata = data.get("metadata") or {}
        requested_guardrails = metadata.get("guardrails") or []
        return requested_guardrails

    def _guardrail_is_in_requested_guardrails(
        self,
        requested_guardrails: Union[List[str], List[Dict[str, DynamicGuardrailParams]]],
    ) -> bool:
        for _guardrail in requested_guardrails:
            if isinstance(_guardrail, dict):
                if self.guardrail_name in _guardrail:
                    return True
            elif isinstance(_guardrail, str):
                if self.guardrail_name == _guardrail:
                    return True
        return False

    def should_run_guardrail(self, data, event_type: GuardrailEventHooks) -> bool:
        """
        Returns True if the guardrail should be run on the event_type
        """
        requested_guardrails = self.get_guardrail_from_metadata(data)

        verbose_logger.debug(
            "inside should_run_guardrail for guardrail=%s event_type= %s guardrail_supported_event_hooks= %s requested_guardrails= %s self.default_on= %s",
            self.guardrail_name,
            event_type,
            self.event_hook,
            requested_guardrails,
            self.default_on,
        )

        if self.default_on is True:
            if self._event_hook_is_event_type(event_type):
                return True
            return False

        if (
            self.event_hook
            and not self._guardrail_is_in_requested_guardrails(requested_guardrails)
            and event_type.value != "logging_only"
        ):
            return False

        if not self._event_hook_is_event_type(event_type):
            return False

        return True

    def _event_hook_is_event_type(self, event_type: GuardrailEventHooks) -> bool:
        """
        Returns True if the event_hook is the same as the event_type

        eg. if `self.event_hook == "pre_call" and event_type == "pre_call"` -> then True
        eg. if `self.event_hook == "pre_call" and event_type == "post_call"` -> then False
        """

        if self.event_hook is None:
            return True
        if isinstance(self.event_hook, list):
            return event_type.value in self.event_hook
        return self.event_hook == event_type.value

    def get_guardrail_dynamic_request_body_params(self, request_data: dict) -> dict:
        """
        Returns `extra_body` to be added to the request body for the Guardrail API call

        Use this to pass dynamic params to the guardrail API call - eg. success_threshold, failure_threshold, etc.

        ```
        [{"lakera_guard": {"extra_body": {"foo": "bar"}}}]
        ```

        Will return: for guardrail=`lakera-guard`:
        {
            "foo": "bar"
        }

        Args:
            request_data: The original `request_data` passed to LiteLLM Proxy
        """
        requested_guardrails = self.get_guardrail_from_metadata(request_data)

        # Look for the guardrail configuration matching self.guardrail_name
        for guardrail in requested_guardrails:
            if isinstance(guardrail, dict) and self.guardrail_name in guardrail:
                # Get the configuration for this guardrail
                guardrail_config: DynamicGuardrailParams = DynamicGuardrailParams(
                    **guardrail[self.guardrail_name]
                )
                if self._validate_premium_user() is not True:
                    return {}

                # Return the extra_body if it exists, otherwise empty dict
                return guardrail_config.get("extra_body", {})

        return {}

    def _validate_premium_user(self) -> bool:
        """
        Returns True if the user is a premium user
        """
        from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

        if premium_user is not True:
            verbose_logger.warning(
                f"Trying to use premium guardrail without premium user {CommonProxyErrors.not_premium_user.value}"
            )
            return False
        return True

    def add_standard_logging_guardrail_information_to_request_data(
        self,
        guardrail_json_response: Union[Exception, str, dict, List[dict]],
        request_data: dict,
        guardrail_status: Literal["success", "failure"],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        duration: Optional[float] = None,
        masked_entity_count: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Builds `StandardLoggingGuardrailInformation` and adds it to the request metadata so it can be used for logging to DataDog, Langfuse, etc.
        """
        if isinstance(guardrail_json_response, Exception):
            guardrail_json_response = str(guardrail_json_response)
        slg = StandardLoggingGuardrailInformation(
            guardrail_name=self.guardrail_name,
            guardrail_mode=self.event_hook,
            guardrail_response=guardrail_json_response,
            guardrail_status=guardrail_status,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            masked_entity_count=masked_entity_count,
        )
        if "metadata" in request_data:
            if request_data["metadata"] is None:
                request_data["metadata"] = {}
            request_data["metadata"]["standard_logging_guardrail_information"] = slg
        elif "litellm_metadata" in request_data:
            request_data["litellm_metadata"][
                "standard_logging_guardrail_information"
            ] = slg
        else:
            verbose_logger.warning(
                "unable to log guardrail information. No metadata found in request_data"
            )

    async def apply_guardrail(
        self,
        text: str,
        language: Optional[str] = None,
        entities: Optional[List[PiiEntityType]] = None,
    ) -> str:
        """
        Apply your guardrail logic to the given text

        Args:
            text: The text to apply the guardrail to
            language: The language of the text
            entities: The entities to mask, optional

        Any of the custom guardrails can override this method to provide custom guardrail logic

        Returns the text with the guardrail applied

        Raises:
            Exception:
                - If the guardrail raises an exception

        """
        return text

    def _process_response(
        self,
        response: Optional[Dict],
        request_data: dict,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        duration: Optional[float] = None,
    ):
        """
        Add StandardLoggingGuardrailInformation to the request data

        This gets logged on downsteam Langfuse, DataDog, etc.
        """
        # Convert None to empty dict to satisfy type requirements
        guardrail_response = {} if response is None else response
        self.add_standard_logging_guardrail_information_to_request_data(
            guardrail_json_response=guardrail_response,
            request_data=request_data,
            guardrail_status="success",
            duration=duration,
            start_time=start_time,
            end_time=end_time,
        )
        return response

    def _process_error(
        self,
        e: Exception,
        request_data: dict,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        duration: Optional[float] = None,
    ):
        """
        Add StandardLoggingGuardrailInformation to the request data

        This gets logged on downsteam Langfuse, DataDog, etc.
        """
        self.add_standard_logging_guardrail_information_to_request_data(
            guardrail_json_response=e,
            request_data=request_data,
            guardrail_status="failure",
            duration=duration,
            start_time=start_time,
            end_time=end_time,
        )
        raise e

    def mask_content_in_string(
        self,
        content_string: str,
        mask_string: str,
        start_index: int,
        end_index: int,
    ) -> str:
        """
        Mask the content in the string between the start and end indices.
        """

        # Do nothing if the start or end are not valid
        if not (0 <= start_index < end_index <= len(content_string)):
            return content_string

        # Mask the content
        return content_string[:start_index] + mask_string + content_string[end_index:]

    def update_in_memory_litellm_params(self, litellm_params: LitellmParams) -> None:
        """
        Update the guardrails litellm params in memory
        """
        pass


def log_guardrail_information(func):
    """
    Decorator to add standard logging guardrail information to any function

    Add this decorator to ensure your guardrail response is logged to DataDog, OTEL, s3, GCS etc.

    Logs for:
        - pre_call
        - during_call
        - TODO: log post_call. This is more involved since the logs are sent to DD, s3 before the guardrail is even run
    """
    import asyncio
    import functools

    start_time = datetime.now()

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        self: CustomGuardrail = args[0]
        request_data: Optional[dict] = (
            kwargs.get("data") or kwargs.get("request_data") or {}
        )
        try:
            response = await func(*args, **kwargs)
            return self._process_response(
                response=response,
                request_data=request_data,
                start_time=start_time.timestamp(),
                end_time=datetime.now().timestamp(),
                duration=(datetime.now() - start_time).total_seconds(),
            )
        except Exception as e:
            return self._process_error(
                e=e,
                request_data=request_data,
                start_time=start_time.timestamp(),
                end_time=datetime.now().timestamp(),
                duration=(datetime.now() - start_time).total_seconds(),
            )

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        self: CustomGuardrail = args[0]
        request_data: Optional[dict] = (
            kwargs.get("data") or kwargs.get("request_data") or {}
        )
        try:
            response = func(*args, **kwargs)
            return self._process_response(
                response=response,
                request_data=request_data,
                duration=(datetime.now() - start_time).total_seconds(),
            )
        except Exception as e:
            return self._process_error(
                e=e,
                request_data=request_data,
                duration=(datetime.now() - start_time).total_seconds(),
            )

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return async_wrapper(*args, **kwargs)
        return sync_wrapper(*args, **kwargs)

    return wrapper

# === NexusCore/openenv\Lib\site-packages\matplotlib\_api\__init__.py ===
"""
Helper functions for managing the Matplotlib API.

This documentation is only relevant for Matplotlib developers, not for users.

.. warning::

    This module and its submodules are for internal use only.  Do not use them
    in your own code.  We may change the API at any time with no warning.

"""

import functools
import itertools
import pathlib
import re
import sys
import warnings

from .deprecation import (  # noqa: F401
    deprecated, warn_deprecated,
    rename_parameter, delete_parameter, make_keyword_only,
    deprecate_method_override, deprecate_privatize_attribute,
    suppress_matplotlib_deprecation_warning,
    MatplotlibDeprecationWarning)


class classproperty:
    """
    Like `property`, but also triggers on access via the class, and it is the
    *class* that's passed as argument.

    Examples
    --------
    ::

        class C:
            @classproperty
            def foo(cls):
                return cls.__name__

        assert C.foo == "C"
    """

    def __init__(self, fget, fset=None, fdel=None, doc=None):
        self._fget = fget
        if fset is not None or fdel is not None:
            raise ValueError('classproperty only implements fget.')
        self.fset = fset
        self.fdel = fdel
        # docs are ignored for now
        self._doc = doc

    def __get__(self, instance, owner):
        return self._fget(owner)

    @property
    def fget(self):
        return self._fget


# In the following check_foo() functions, the first parameter is positional-only to make
# e.g. `_api.check_isinstance([...], types=foo)` work.

def check_isinstance(types, /, **kwargs):
    """
    For each *key, value* pair in *kwargs*, check that *value* is an instance
    of one of *types*; if not, raise an appropriate TypeError.

    As a special case, a ``None`` entry in *types* is treated as NoneType.

    Examples
    --------
    >>> _api.check_isinstance((SomeClass, None), arg=arg)
    """
    none_type = type(None)
    types = ((types,) if isinstance(types, type) else
             (none_type,) if types is None else
             tuple(none_type if tp is None else tp for tp in types))

    def type_name(tp):
        return ("None" if tp is none_type
                else tp.__qualname__ if tp.__module__ == "builtins"
                else f"{tp.__module__}.{tp.__qualname__}")

    for k, v in kwargs.items():
        if not isinstance(v, types):
            names = [*map(type_name, types)]
            if "None" in names:  # Move it to the end for better wording.
                names.remove("None")
                names.append("None")
            raise TypeError(
                "{!r} must be an instance of {}, not a {}".format(
                    k,
                    ", ".join(names[:-1]) + " or " + names[-1]
                    if len(names) > 1 else names[0],
                    type_name(type(v))))


def check_in_list(values, /, *, _print_supported_values=True, **kwargs):
    """
    For each *key, value* pair in *kwargs*, check that *value* is in *values*;
    if not, raise an appropriate ValueError.

    Parameters
    ----------
    values : iterable
        Sequence of values to check on.
    _print_supported_values : bool, default: True
        Whether to print *values* when raising ValueError.
    **kwargs : dict
        *key, value* pairs as keyword arguments to find in *values*.

    Raises
    ------
    ValueError
        If any *value* in *kwargs* is not found in *values*.

    Examples
    --------
    >>> _api.check_in_list(["foo", "bar"], arg=arg, other_arg=other_arg)
    """
    if not kwargs:
        raise TypeError("No argument to check!")
    for key, val in kwargs.items():
        if val not in values:
            msg = f"{val!r} is not a valid value for {key}"
            if _print_supported_values:
                msg += f"; supported values are {', '.join(map(repr, values))}"
            raise ValueError(msg)


def check_shape(shape, /, **kwargs):
    """
    For each *key, value* pair in *kwargs*, check that *value* has the shape *shape*;
    if not, raise an appropriate ValueError.

    *None* in the shape is treated as a "free" size that can have any length.
    e.g. (None, 2) -> (N, 2)

    The values checked must be numpy arrays.

    Examples
    --------
    To check for (N, 2) shaped arrays

    >>> _api.check_shape((None, 2), arg=arg, other_arg=other_arg)
    """
    for k, v in kwargs.items():
        data_shape = v.shape

        if (len(data_shape) != len(shape)
                or any(s != t and t is not None for s, t in zip(data_shape, shape))):
            dim_labels = iter(itertools.chain(
                'NMLKJIH',
                (f"D{i}" for i in itertools.count())))
            text_shape = ", ".join([str(n) if n is not None else next(dim_labels)
                                    for n in shape[::-1]][::-1])
            if len(shape) == 1:
                text_shape += ","

            raise ValueError(
                f"{k!r} must be {len(shape)}D with shape ({text_shape}), "
                f"but your input has shape {v.shape}"
            )


def check_getitem(mapping, /, **kwargs):
    """
    *kwargs* must consist of a single *key, value* pair.  If *key* is in
    *mapping*, return ``mapping[value]``; else, raise an appropriate
    ValueError.

    Examples
    --------
    >>> _api.check_getitem({"foo": "bar"}, arg=arg)
    """
    if len(kwargs) != 1:
        raise ValueError("check_getitem takes a single keyword argument")
    (k, v), = kwargs.items()
    try:
        return mapping[v]
    except KeyError:
        raise ValueError(
            f"{v!r} is not a valid value for {k}; supported values are "
            f"{', '.join(map(repr, mapping))}") from None


def caching_module_getattr(cls):
    """
    Helper decorator for implementing module-level ``__getattr__`` as a class.

    This decorator must be used at the module toplevel as follows::

        @caching_module_getattr
        class __getattr__:  # The class *must* be named ``__getattr__``.
            @property  # Only properties are taken into account.
            def name(self): ...

    The ``__getattr__`` class will be replaced by a ``__getattr__``
    function such that trying to access ``name`` on the module will
    resolve the corresponding property (which may be decorated e.g. with
    ``_api.deprecated`` for deprecating module globals).  The properties are
    all implicitly cached.  Moreover, a suitable AttributeError is generated
    and raised if no property with the given name exists.
    """

    assert cls.__name__ == "__getattr__"
    # Don't accidentally export cls dunders.
    props = {name: prop for name, prop in vars(cls).items()
             if isinstance(prop, property)}
    instance = cls()

    @functools.cache
    def __getattr__(name):
        if name in props:
            return props[name].__get__(instance)
        raise AttributeError(
            f"module {cls.__module__!r} has no attribute {name!r}")

    return __getattr__


def define_aliases(alias_d, cls=None):
    """
    Class decorator for defining property aliases.

    Use as ::

        @_api.define_aliases({"property": ["alias", ...], ...})
        class C: ...

    For each property, if the corresponding ``get_property`` is defined in the
    class so far, an alias named ``get_alias`` will be defined; the same will
    be done for setters.  If neither the getter nor the setter exists, an
    exception will be raised.

    The alias map is stored as the ``_alias_map`` attribute on the class and
    can be used by `.normalize_kwargs` (which assumes that higher priority
    aliases come last).
    """
    if cls is None:  # Return the actual class decorator.
        return functools.partial(define_aliases, alias_d)

    def make_alias(name):  # Enforce a closure over *name*.
        @functools.wraps(getattr(cls, name))
        def method(self, *args, **kwargs):
            return getattr(self, name)(*args, **kwargs)
        return method

    for prop, aliases in alias_d.items():
        exists = False
        for prefix in ["get_", "set_"]:
            if prefix + prop in vars(cls):
                exists = True
                for alias in aliases:
                    method = make_alias(prefix + prop)
                    method.__name__ = prefix + alias
                    method.__doc__ = f"Alias for `{prefix + prop}`."
                    setattr(cls, prefix + alias, method)
        if not exists:
            raise ValueError(
                f"Neither getter nor setter exists for {prop!r}")

    def get_aliased_and_aliases(d):
        return {*d, *(alias for aliases in d.values() for alias in aliases)}

    preexisting_aliases = getattr(cls, "_alias_map", {})
    conflicting = (get_aliased_and_aliases(preexisting_aliases)
                   & get_aliased_and_aliases(alias_d))
    if conflicting:
        # Need to decide on conflict resolution policy.
        raise NotImplementedError(
            f"Parent class already defines conflicting aliases: {conflicting}")
    cls._alias_map = {**preexisting_aliases, **alias_d}
    return cls


def select_matching_signature(funcs, *args, **kwargs):
    """
    Select and call the function that accepts ``*args, **kwargs``.

    *funcs* is a list of functions which should not raise any exception (other
    than `TypeError` if the arguments passed do not match their signature).

    `select_matching_signature` tries to call each of the functions in *funcs*
    with ``*args, **kwargs`` (in the order in which they are given).  Calls
    that fail with a `TypeError` are silently skipped.  As soon as a call
    succeeds, `select_matching_signature` returns its return value.  If no
    function accepts ``*args, **kwargs``, then the `TypeError` raised by the
    last failing call is re-raised.

    Callers should normally make sure that any ``*args, **kwargs`` can only
    bind a single *func* (to avoid any ambiguity), although this is not checked
    by `select_matching_signature`.

    Notes
    -----
    `select_matching_signature` is intended to help implementing
    signature-overloaded functions.  In general, such functions should be
    avoided, except for back-compatibility concerns.  A typical use pattern is
    ::

        def my_func(*args, **kwargs):
            params = select_matching_signature(
                [lambda old1, old2: locals(), lambda new: locals()],
                *args, **kwargs)
            if "old1" in params:
                warn_deprecated(...)
                old1, old2 = params.values()  # note that locals() is ordered.
            else:
                new, = params.values()
            # do things with params

    which allows *my_func* to be called either with two parameters (*old1* and
    *old2*) or a single one (*new*).  Note that the new signature is given
    last, so that callers get a `TypeError` corresponding to the new signature
    if the arguments they passed in do not match any signature.
    """
    # Rather than relying on locals() ordering, one could have just used func's
    # signature (``bound = inspect.signature(func).bind(*args, **kwargs);
    # bound.apply_defaults(); return bound``) but that is significantly slower.
    for i, func in enumerate(funcs):
        try:
            return func(*args, **kwargs)
        except TypeError:
            if i == len(funcs) - 1:
                raise


def nargs_error(name, takes, given):
    """Generate a TypeError to be raised by function calls with wrong arity."""
    return TypeError(f"{name}() takes {takes} positional arguments but "
                     f"{given} were given")


def kwarg_error(name, kw):
    """
    Generate a TypeError to be raised by function calls with wrong kwarg.

    Parameters
    ----------
    name : str
        The name of the calling function.
    kw : str or Iterable[str]
        Either the invalid keyword argument name, or an iterable yielding
        invalid keyword arguments (e.g., a ``kwargs`` dict).
    """
    if not isinstance(kw, str):
        kw = next(iter(kw))
    return TypeError(f"{name}() got an unexpected keyword argument '{kw}'")


def recursive_subclasses(cls):
    """Yield *cls* and direct and indirect subclasses of *cls*."""
    yield cls
    for subcls in cls.__subclasses__():
        yield from recursive_subclasses(subcls)


def warn_external(message, category=None):
    """
    `warnings.warn` wrapper that sets *stacklevel* to "outside Matplotlib".

    The original emitter of the warning can be obtained by patching this
    function back to `warnings.warn`, i.e. ``_api.warn_external =
    warnings.warn`` (or ``functools.partial(warnings.warn, stacklevel=2)``,
    etc.).
    """
    kwargs = {}
    if sys.version_info[:2] >= (3, 12):
        # Go to Python's `site-packages` or `lib` from an editable install.
        basedir = pathlib.Path(__file__).parents[2]
        kwargs['skip_file_prefixes'] = (str(basedir / 'matplotlib'),
                                        str(basedir / 'mpl_toolkits'))
    else:
        frame = sys._getframe()
        for stacklevel in itertools.count(1):
            if frame is None:
                # when called in embedded context may hit frame is None
                kwargs['stacklevel'] = stacklevel
                break
            if not re.match(r"\A(matplotlib|mpl_toolkits)(\Z|\.(?!tests\.))",
                            # Work around sphinx-gallery not setting __name__.
                            frame.f_globals.get("__name__", "")):
                kwargs['stacklevel'] = stacklevel
                break
            frame = frame.f_back
        # preemptively break reference cycle between locals and the frame
        del frame
    warnings.warn(message, category, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\_hypothesis_plugin.py ===
"""
Register Hypothesis strategies for Pydantic custom types.

This enables fully-automatic generation of test data for most Pydantic classes.

Note that this module has *no* runtime impact on Pydantic itself; instead it
is registered as a setuptools entry point and Hypothesis will import it if
Pydantic is installed.  See also:

https://hypothesis.readthedocs.io/en/latest/strategies.html#registering-strategies-via-setuptools-entry-points
https://hypothesis.readthedocs.io/en/latest/data.html#hypothesis.strategies.register_type_strategy
https://hypothesis.readthedocs.io/en/latest/strategies.html#interaction-with-pytest-cov
https://docs.pydantic.dev/usage/types/#pydantic-types

Note that because our motivation is to *improve user experience*, the strategies
are always sound (never generate invalid data) but sacrifice completeness for
maintainability (ie may be unable to generate some tricky but valid data).

Finally, this module makes liberal use of `# type: ignore[<code>]` pragmas.
This is because Hypothesis annotates `register_type_strategy()` with
`(T, SearchStrategy[T])`, but in most cases we register e.g. `ConstrainedInt`
to generate instances of the builtin `int` type which match the constraints.
"""

import contextlib
import datetime
import ipaddress
import json
import math
from fractions import Fraction
from typing import Callable, Dict, Type, Union, cast, overload

import hypothesis.strategies as st

import pydantic
import pydantic.color
import pydantic.types
from pydantic.v1.utils import lenient_issubclass

# FilePath and DirectoryPath are explicitly unsupported, as we'd have to create
# them on-disk, and that's unsafe in general without being told *where* to do so.
#
# URLs are unsupported because it's easy for users to define their own strategy for
# "normal" URLs, and hard for us to define a general strategy which includes "weird"
# URLs but doesn't also have unpredictable performance problems.
#
# conlist() and conset() are unsupported for now, because the workarounds for
# Cython and Hypothesis to handle parametrized generic types are incompatible.
# We are rethinking Hypothesis compatibility in Pydantic v2.

# Emails
try:
    import email_validator
except ImportError:  # pragma: no cover
    pass
else:

    def is_valid_email(s: str) -> bool:
        # Hypothesis' st.emails() occasionally generates emails like 0@A0--0.ac
        # that are invalid according to email-validator, so we filter those out.
        try:
            email_validator.validate_email(s, check_deliverability=False)
            return True
        except email_validator.EmailNotValidError:  # pragma: no cover
            return False

    # Note that these strategies deliberately stay away from any tricky Unicode
    # or other encoding issues; we're just trying to generate *something* valid.
    st.register_type_strategy(pydantic.EmailStr, st.emails().filter(is_valid_email))  # type: ignore[arg-type]
    st.register_type_strategy(
        pydantic.NameEmail,
        st.builds(
            '{} <{}>'.format,  # type: ignore[arg-type]
            st.from_regex('[A-Za-z0-9_]+( [A-Za-z0-9_]+){0,5}', fullmatch=True),
            st.emails().filter(is_valid_email),
        ),
    )

# PyObject - dotted names, in this case taken from the math module.
st.register_type_strategy(
    pydantic.PyObject,  # type: ignore[arg-type]
    st.sampled_from(
        [cast(pydantic.PyObject, f'math.{name}') for name in sorted(vars(math)) if not name.startswith('_')]
    ),
)

# CSS3 Colors; as name, hex, rgb(a) tuples or strings, or hsl strings
_color_regexes = (
    '|'.join(
        (
            pydantic.color.r_hex_short,
            pydantic.color.r_hex_long,
            pydantic.color.r_rgb,
            pydantic.color.r_rgba,
            pydantic.color.r_hsl,
            pydantic.color.r_hsla,
        )
    )
    # Use more precise regex patterns to avoid value-out-of-range errors
    .replace(pydantic.color._r_sl, r'(?:(\d\d?(?:\.\d+)?|100(?:\.0+)?)%)')
    .replace(pydantic.color._r_alpha, r'(?:(0(?:\.\d+)?|1(?:\.0+)?|\.\d+|\d{1,2}%))')
    .replace(pydantic.color._r_255, r'(?:((?:\d|\d\d|[01]\d\d|2[0-4]\d|25[0-4])(?:\.\d+)?|255(?:\.0+)?))')
)
st.register_type_strategy(
    pydantic.color.Color,
    st.one_of(
        st.sampled_from(sorted(pydantic.color.COLORS_BY_NAME)),
        st.tuples(
            st.integers(0, 255),
            st.integers(0, 255),
            st.integers(0, 255),
            st.none() | st.floats(0, 1) | st.floats(0, 100).map('{}%'.format),
        ),
        st.from_regex(_color_regexes, fullmatch=True),
    ),
)


# Card numbers, valid according to the Luhn algorithm


def add_luhn_digit(card_number: str) -> str:
    # See https://en.wikipedia.org/wiki/Luhn_algorithm
    for digit in '0123456789':
        with contextlib.suppress(Exception):
            pydantic.PaymentCardNumber.validate_luhn_check_digit(card_number + digit)
            return card_number + digit
    raise AssertionError('Unreachable')  # pragma: no cover


card_patterns = (
    # Note that these patterns omit the Luhn check digit; that's added by the function above
    '4[0-9]{14}',  # Visa
    '5[12345][0-9]{13}',  # Mastercard
    '3[47][0-9]{12}',  # American Express
    '[0-26-9][0-9]{10,17}',  # other (incomplete to avoid overlap)
)
st.register_type_strategy(
    pydantic.PaymentCardNumber,
    st.from_regex('|'.join(card_patterns), fullmatch=True).map(add_luhn_digit),  # type: ignore[arg-type]
)

# UUIDs
st.register_type_strategy(pydantic.UUID1, st.uuids(version=1))
st.register_type_strategy(pydantic.UUID3, st.uuids(version=3))
st.register_type_strategy(pydantic.UUID4, st.uuids(version=4))
st.register_type_strategy(pydantic.UUID5, st.uuids(version=5))

# Secrets
st.register_type_strategy(pydantic.SecretBytes, st.binary().map(pydantic.SecretBytes))
st.register_type_strategy(pydantic.SecretStr, st.text().map(pydantic.SecretStr))

# IP addresses, networks, and interfaces
st.register_type_strategy(pydantic.IPvAnyAddress, st.ip_addresses())  # type: ignore[arg-type]
st.register_type_strategy(
    pydantic.IPvAnyInterface,
    st.from_type(ipaddress.IPv4Interface) | st.from_type(ipaddress.IPv6Interface),  # type: ignore[arg-type]
)
st.register_type_strategy(
    pydantic.IPvAnyNetwork,
    st.from_type(ipaddress.IPv4Network) | st.from_type(ipaddress.IPv6Network),  # type: ignore[arg-type]
)

# We hook into the con***() functions and the ConstrainedNumberMeta metaclass,
# so here we only have to register subclasses for other constrained types which
# don't go via those mechanisms.  Then there are the registration hooks below.
st.register_type_strategy(pydantic.StrictBool, st.booleans())
st.register_type_strategy(pydantic.StrictStr, st.text())


# FutureDate, PastDate
st.register_type_strategy(pydantic.FutureDate, st.dates(min_value=datetime.date.today() + datetime.timedelta(days=1)))
st.register_type_strategy(pydantic.PastDate, st.dates(max_value=datetime.date.today() - datetime.timedelta(days=1)))


# Constrained-type resolver functions
#
# For these ones, we actually want to inspect the type in order to work out a
# satisfying strategy.  First up, the machinery for tracking resolver functions:

RESOLVERS: Dict[type, Callable[[type], st.SearchStrategy]] = {}  # type: ignore[type-arg]


@overload
def _registered(typ: Type[pydantic.types.T]) -> Type[pydantic.types.T]:
    pass


@overload
def _registered(typ: pydantic.types.ConstrainedNumberMeta) -> pydantic.types.ConstrainedNumberMeta:
    pass


def _registered(
    typ: Union[Type[pydantic.types.T], pydantic.types.ConstrainedNumberMeta]
) -> Union[Type[pydantic.types.T], pydantic.types.ConstrainedNumberMeta]:
    # This function replaces the version in `pydantic.types`, in order to
    # effect the registration of new constrained types so that Hypothesis
    # can generate valid examples.
    pydantic.types._DEFINED_TYPES.add(typ)
    for supertype, resolver in RESOLVERS.items():
        if issubclass(typ, supertype):
            st.register_type_strategy(typ, resolver(typ))  # type: ignore
            return typ
    raise NotImplementedError(f'Unknown type {typ!r} has no resolver to register')  # pragma: no cover


def resolves(
    typ: Union[type, pydantic.types.ConstrainedNumberMeta]
) -> Callable[[Callable[..., st.SearchStrategy]], Callable[..., st.SearchStrategy]]:  # type: ignore[type-arg]
    def inner(f):  # type: ignore
        assert f not in RESOLVERS
        RESOLVERS[typ] = f
        return f

    return inner


# Type-to-strategy resolver functions


@resolves(pydantic.JsonWrapper)
def resolve_json(cls):  # type: ignore[no-untyped-def]
    try:
        inner = st.none() if cls.inner_type is None else st.from_type(cls.inner_type)
    except Exception:  # pragma: no cover
        finite = st.floats(allow_infinity=False, allow_nan=False)
        inner = st.recursive(
            base=st.one_of(st.none(), st.booleans(), st.integers(), finite, st.text()),
            extend=lambda x: st.lists(x) | st.dictionaries(st.text(), x),  # type: ignore
        )
    inner_type = getattr(cls, 'inner_type', None)
    return st.builds(
        cls.inner_type.json if lenient_issubclass(inner_type, pydantic.BaseModel) else json.dumps,
        inner,
        ensure_ascii=st.booleans(),
        indent=st.none() | st.integers(0, 16),
        sort_keys=st.booleans(),
    )


@resolves(pydantic.ConstrainedBytes)
def resolve_conbytes(cls):  # type: ignore[no-untyped-def]  # pragma: no cover
    min_size = cls.min_length or 0
    max_size = cls.max_length
    if not cls.strip_whitespace:
        return st.binary(min_size=min_size, max_size=max_size)
    # Fun with regex to ensure we neither start nor end with whitespace
    repeats = '{{{},{}}}'.format(
        min_size - 2 if min_size > 2 else 0,
        max_size - 2 if (max_size or 0) > 2 else '',
    )
    if min_size >= 2:
        pattern = rf'\W.{repeats}\W'
    elif min_size == 1:
        pattern = rf'\W(.{repeats}\W)?'
    else:
        assert min_size == 0
        pattern = rf'(\W(.{repeats}\W)?)?'
    return st.from_regex(pattern.encode(), fullmatch=True)


@resolves(pydantic.ConstrainedDecimal)
def resolve_condecimal(cls):  # type: ignore[no-untyped-def]
    min_value = cls.ge
    max_value = cls.le
    if cls.gt is not None:
        assert min_value is None, 'Set `gt` or `ge`, but not both'
        min_value = cls.gt
    if cls.lt is not None:
        assert max_value is None, 'Set `lt` or `le`, but not both'
        max_value = cls.lt
    s = st.decimals(min_value, max_value, allow_nan=False, places=cls.decimal_places)
    if cls.lt is not None:
        s = s.filter(lambda d: d < cls.lt)
    if cls.gt is not None:
        s = s.filter(lambda d: cls.gt < d)
    return s


@resolves(pydantic.ConstrainedFloat)
def resolve_confloat(cls):  # type: ignore[no-untyped-def]
    min_value = cls.ge
    max_value = cls.le
    exclude_min = False
    exclude_max = False

    if cls.gt is not None:
        assert min_value is None, 'Set `gt` or `ge`, but not both'
        min_value = cls.gt
        exclude_min = True
    if cls.lt is not None:
        assert max_value is None, 'Set `lt` or `le`, but not both'
        max_value = cls.lt
        exclude_max = True

    if cls.multiple_of is None:
        return st.floats(min_value, max_value, exclude_min=exclude_min, exclude_max=exclude_max, allow_nan=False)

    if min_value is not None:
        min_value = math.ceil(min_value / cls.multiple_of)
        if exclude_min:
            min_value = min_value + 1
    if max_value is not None:
        assert max_value >= cls.multiple_of, 'Cannot build model with max value smaller than multiple of'
        max_value = math.floor(max_value / cls.multiple_of)
        if exclude_max:
            max_value = max_value - 1

    return st.integers(min_value, max_value).map(lambda x: x * cls.multiple_of)


@resolves(pydantic.ConstrainedInt)
def resolve_conint(cls):  # type: ignore[no-untyped-def]
    min_value = cls.ge
    max_value = cls.le
    if cls.gt is not None:
        assert min_value is None, 'Set `gt` or `ge`, but not both'
        min_value = cls.gt + 1
    if cls.lt is not None:
        assert max_value is None, 'Set `lt` or `le`, but not both'
        max_value = cls.lt - 1

    if cls.multiple_of is None or cls.multiple_of == 1:
        return st.integers(min_value, max_value)

    # These adjustments and the .map handle integer-valued multiples, while the
    # .filter handles trickier cases as for confloat.
    if min_value is not None:
        min_value = math.ceil(Fraction(min_value) / Fraction(cls.multiple_of))
    if max_value is not None:
        max_value = math.floor(Fraction(max_value) / Fraction(cls.multiple_of))
    return st.integers(min_value, max_value).map(lambda x: x * cls.multiple_of)


@resolves(pydantic.ConstrainedDate)
def resolve_condate(cls):  # type: ignore[no-untyped-def]
    if cls.ge is not None:
        assert cls.gt is None, 'Set `gt` or `ge`, but not both'
        min_value = cls.ge
    elif cls.gt is not None:
        min_value = cls.gt + datetime.timedelta(days=1)
    else:
        min_value = datetime.date.min
    if cls.le is not None:
        assert cls.lt is None, 'Set `lt` or `le`, but not both'
        max_value = cls.le
    elif cls.lt is not None:
        max_value = cls.lt - datetime.timedelta(days=1)
    else:
        max_value = datetime.date.max
    return st.dates(min_value, max_value)


@resolves(pydantic.ConstrainedStr)
def resolve_constr(cls):  # type: ignore[no-untyped-def]  # pragma: no cover
    min_size = cls.min_length or 0
    max_size = cls.max_length

    if cls.regex is None and not cls.strip_whitespace:
        return st.text(min_size=min_size, max_size=max_size)

    if cls.regex is not None:
        strategy = st.from_regex(cls.regex)
        if cls.strip_whitespace:
            strategy = strategy.filter(lambda s: s == s.strip())
    elif cls.strip_whitespace:
        repeats = '{{{},{}}}'.format(
            min_size - 2 if min_size > 2 else 0,
            max_size - 2 if (max_size or 0) > 2 else '',
        )
        if min_size >= 2:
            strategy = st.from_regex(rf'\W.{repeats}\W')
        elif min_size == 1:
            strategy = st.from_regex(rf'\W(.{repeats}\W)?')
        else:
            assert min_size == 0
            strategy = st.from_regex(rf'(\W(.{repeats}\W)?)?')

    if min_size == 0 and max_size is None:
        return strategy
    elif max_size is None:
        return strategy.filter(lambda s: min_size <= len(s))
    return strategy.filter(lambda s: min_size <= len(s) <= max_size)


# Finally, register all previously-defined types, and patch in our new function
for typ in list(pydantic.types._DEFINED_TYPES):
    _registered(typ)
pydantic.types._registered = _registered
st.register_type_strategy(pydantic.Json, resolve_json)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\minecraft.py ===
"""
    pygments.lexers.minecraft
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Minecraft related languages.

    SNBT. A data communication format used in Minecraft.
    wiki: https://minecraft.wiki/w/NBT_format

    MCFunction. The Function file for Minecraft Data packs and Add-ons.
    official: https://learn.microsoft.com/en-us/minecraft/creator/documents/functionsintroduction
    wiki: https://minecraft.wiki/w/Function

    MCSchema. A kind of data Schema for Minecraft Add-on Development.
    official: https://learn.microsoft.com/en-us/minecraft/creator/reference/content/schemasreference/
    community example: https://www.mcbe-dev.net/addons/data-driven/manifest.html

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, default, include, bygroups
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, \
    Punctuation, String, Text, Whitespace

__all__ = ['SNBTLexer', 'MCFunctionLexer', 'MCSchemaLexer']


class SNBTLexer(RegexLexer):
    """Lexer for stringified NBT, a data format used in Minecraft
    """

    name = "SNBT"
    url = "https://minecraft.wiki/w/NBT_format"
    aliases = ["snbt"]
    filenames = ["*.snbt"]
    mimetypes = ["text/snbt"]
    version_added = '2.12'

    tokens = {
        "root": [
            # We only look for the open bracket here since square bracket
            #  is only valid in NBT pathing (which is a mcfunction idea).
            (r"\{", Punctuation, "compound"),
            (r"[^\{]+", Text),
        ],

        "whitespace": [
            (r"\s+", Whitespace),
        ],

        "operators": [
            (r"[,:;]", Punctuation),
        ],

        "literals": [
            (r"(true|false)", Keyword.Constant),
            (r"-?\d+[eE]-?\d+", Number.Float),
            (r"-?\d*\.\d+[fFdD]?", Number.Float),
            (r"-?\d+[bBsSlLfFdD]?", Number.Integer),

            # Separate states for both types of strings so they don't entangle
            (r'"', String.Double, "literals.string_double"),
            (r"'", String.Single, "literals.string_single"),
        ],
        "literals.string_double": [
            (r"\\.", String.Escape),
            (r'[^\\"\n]+', String.Double),
            (r'"', String.Double, "#pop"),
        ],
        "literals.string_single": [
            (r"\\.", String.Escape),
            (r"[^\\'\n]+", String.Single),
            (r"'", String.Single, "#pop"),
        ],

        "compound": [
            # this handles the unquoted snbt keys
            #  note: stringified keys still work
            (r"[A-Z_a-z]+", Name.Attribute),
            include("operators"),
            include("whitespace"),
            include("literals"),
            (r"\{", Punctuation, "#push"),
            (r"\[", Punctuation, "list"),
            (r"\}", Punctuation, "#pop"),
        ],

        "list": [
            (r"[A-Z_a-z]+", Name.Attribute),
            include("literals"),
            include("operators"),
            include("whitespace"),
            (r"\[", Punctuation, "#push"),
            (r"\{", Punctuation, "compound"),
            (r"\]", Punctuation, "#pop"),
        ],
    }


class MCFunctionLexer(RegexLexer):
    """Lexer for the mcfunction scripting language used in Minecraft
    Modelled somewhat after the `GitHub mcfunction grammar <https://github.com/Arcensoth/language-mcfunction>`_.
    """

    name = "MCFunction"
    url = "https://minecraft.wiki/w/Commands"
    aliases = ["mcfunction", "mcf"]
    filenames = ["*.mcfunction"]
    mimetypes = ["text/mcfunction"]
    version_added = '2.12'

    # Used to denotate the start of a block comment, borrowed from Github's mcfunction
    _block_comment_prefix = "[>!]"

    tokens = {
        "root": [
            include("names"),
            include("comments"),
            include("literals"),
            include("whitespace"),
            include("property"),
            include("operators"),
            include("selectors"),
        ],

        "names": [
            # The start of a command (either beginning of line OR after the run keyword)
            #  We don't encode a list of keywords since mods, plugins, or even pre-processors
            #  may add new commands, so we have a 'close-enough' regex which catches them.
            (r"^(\s*)([a-z_]+)", bygroups(Whitespace, Name.Builtin)),
            (r"(?<=run)\s+[a-z_]+", Name.Builtin),

            # UUID
            (r"\b[0-9a-fA-F]+(?:-[0-9a-fA-F]+){4}\b", Name.Variable),
            include("resource-name"),
            # normal command names and scoreboards
            #  there's no way to know the differences unfortuntely
            (r"[A-Za-z_][\w.#%$]+", Keyword.Constant),
            (r"[#%$][\w.#%$]+", Name.Variable.Magic),
        ],

        "resource-name": [
            # resource names have to be lowercase
            (r"#?[a-z_][a-z_.-]*:[a-z0-9_./-]+", Name.Function),
            # similar to above except optional `:``
            #  a `/` must be present "somewhere"
            (r"#?[a-z0-9_\.\-]+\/[a-z0-9_\.\-\/]+", Name.Function),
        ],

        "whitespace": [
            (r"\s+", Whitespace),
        ],

        "comments": [
            (rf"^\s*(#{_block_comment_prefix})", Comment.Multiline,
             ("comments.block", "comments.block.emphasized")),
            (r"#.*$", Comment.Single),
        ],
        "comments.block": [
            (rf"^\s*#{_block_comment_prefix}", Comment.Multiline,
             "comments.block.emphasized"),
            (r"^\s*#", Comment.Multiline, "comments.block.normal"),
            default("#pop"),
        ],
        "comments.block.normal": [
            include("comments.block.special"),
            (r"\S+", Comment.Multiline),
            (r"\n", Text, "#pop"),
            include("whitespace"),
        ],
        "comments.block.emphasized": [
            include("comments.block.special"),
            (r"\S+", String.Doc),
            (r"\n", Text, "#pop"),
            include("whitespace"),
        ],
        "comments.block.special": [
            # Params
            (r"@\S+", Name.Decorator),

            include("resource-name"),

            # Scoreboard player names
            (r"[#%$][\w.#%$]+", Name.Variable.Magic),
        ],

        "operators": [
            (r"[\-~%^?!+*<>\\/|&=.]", Operator),
        ],

        "literals": [
            (r"\.\.", Literal),
            (r"(true|false)", Keyword.Pseudo),

            # these are like unquoted strings and appear in many places
            (r"[A-Za-z_]+", Name.Variable.Class),

            (r"[0-7]b", Number.Byte),
            (r"[+-]?\d*\.?\d+([eE]?[+-]?\d+)?[df]?\b", Number.Float),
            (r"[+-]?\d+\b", Number.Integer),
            (r'"', String.Double, "literals.string-double"),
            (r"'", String.Single, "literals.string-single"),
        ],
        "literals.string-double": [
            (r"\\.", String.Escape),
            (r'[^\\"\n]+', String.Double),
            (r'"', String.Double, "#pop"),
        ],
        "literals.string-single": [
            (r"\\.", String.Escape),
            (r"[^\\'\n]+", String.Single),
            (r"'", String.Single, "#pop"),
        ],

        "selectors": [
            (r"@[a-z]", Name.Variable),
        ],


        ## Generic Property Container
        # There are several, differing instances where the language accepts
        #  specific contained keys or contained key, value pairings.
        #
        # Property Maps:
        # - Starts with either `[` or `{`
        # - Key separated by `:` or `=`
        # - Deliminated by `,`
        #
        # Property Lists:
        # - Starts with `[`
        # - Deliminated by `,`
        #
        # For simplicity, these patterns match a generic, nestable structure
        #  which follow a key, value pattern. For normal lists, there's only keys.
        # This allow some "illegal" structures, but we'll accept those for
        #  sake of simplicity
        #
        # Examples:
        # - `[facing=up, powered=true]` (blockstate)
        # - `[name="hello world", nbt={key: 1b}]` (selector + nbt)
        # - `[{"text": "value"}, "literal"]` (json)
        ##
        "property": [
            # This state gets included in root and also several substates
            # We do this to shortcut the starting of new properties
            #  within other properties. Lists can have sublists and compounds
            #  and values can start a new property (see the `difficult_1.txt`
            #  snippet).
            (r"\{", Punctuation, ("property.curly", "property.key")),
            (r"\[", Punctuation, ("property.square", "property.key")),
        ],
        "property.curly": [
            include("whitespace"),
            include("property"),
            (r"\}", Punctuation, "#pop"),
        ],
        "property.square": [
            include("whitespace"),
            include("property"),
            (r"\]", Punctuation, "#pop"),

            # lists can have sequences of items
            (r",", Punctuation),
        ],
        "property.key": [
            include("whitespace"),

            # resource names (for advancements)
            #  can omit `:` to default `minecraft:`
            # must check if there is a future equals sign if `:` is in the name
            (r"#?[a-z_][a-z_\.\-]*\:[a-z0-9_\.\-/]+(?=\s*\=)", Name.Attribute, "property.delimiter"),
            (r"#?[a-z_][a-z0-9_\.\-/]+", Name.Attribute, "property.delimiter"),

            # unquoted NBT key
            (r"[A-Za-z_\-\+]+", Name.Attribute, "property.delimiter"),

            # quoted JSON or NBT key
            (r'"', Name.Attribute, "property.delimiter", "literals.string-double"),
            (r"'", Name.Attribute, "property.delimiter", "literals.string-single"),

            # index for a list
            (r"-?\d+", Number.Integer, "property.delimiter"),

            default("#pop"),
        ],
        "property.key.string-double": [
            (r"\\.", String.Escape),
            (r'[^\\"\n]+', Name.Attribute),
            (r'"', Name.Attribute, "#pop"),
        ],
        "property.key.string-single": [
            (r"\\.", String.Escape),
            (r"[^\\'\n]+", Name.Attribute),
            (r"'", Name.Attribute, "#pop"),
        ],
        "property.delimiter": [
            include("whitespace"),

            (r"[:=]!?", Punctuation, "property.value"),
            (r",", Punctuation),

            default("#pop"),
        ],
        "property.value": [
            include("whitespace"),

            # unquoted resource names are valid literals here
            (r"#?[a-z_][a-z_\.\-]*\:[a-z0-9_\.\-/]+", Name.Tag),
            (r"#?[a-z_][a-z0-9_\.\-/]+", Name.Tag),

            include("literals"),
            include("property"),

            default("#pop"),
        ],
    }


class MCSchemaLexer(RegexLexer):
    """Lexer for Minecraft Add-ons data Schemas, an interface structure standard used in Minecraft
    """

    name = 'MCSchema'
    url = 'https://learn.microsoft.com/en-us/minecraft/creator/reference/content/schemasreference/'
    aliases = ['mcschema']
    filenames = ['*.mcschema']
    mimetypes = ['text/mcschema']
    version_added = '2.14'

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'//.*?$', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Whitespace, '#pop')
        ],
        'singlestring': [
            (r'\\.', String.Escape),
            (r"'", String.Single, '#pop'),
            (r"[^\\']+", String.Single),
        ],
        'doublestring': [
            (r'\\.', String.Escape),
            (r'"', String.Double, '#pop'),
            (r'[^\\"]+', String.Double),
        ],
        'root': [
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),

            # keywords for optional word and field types
            (r'(?<=: )opt', Operator.Word),
            (r'(?<=\s)[\w-]*(?=(\s+"|\n))', Keyword.Declaration),

            # numeric literals
            (r'0[bB][01]+', Number.Bin),
            (r'0[oO]?[0-7]+', Number.Oct),
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            (r'\d+', Number.Integer),
            (r'(\.\d+|\d+\.\d*|\d+)([eE][-+]?\d+)?', Number.Float),

            # possible punctuations
            (r'\.\.\.|=>', Punctuation),
            (r'\+\+|--|~|\?\?=?|\?|:|\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|(?:\*\*|\|\||&&|[-<>+*%&|^/]))=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),

            # strings
            (r"'", String.Single, 'singlestring'),
            (r'"', String.Double, 'doublestring'),

            # title line
            (r'[\w-]*?(?=:\{?\n)', String.Symbol),
            # title line with a version code, formatted
            # `major.minor.patch-prerelease+buildmeta`
            (r'([\w-]*?)(:)(\d+)(?:(\.)(\d+)(?:(\.)(\d+)(?:(\-)((?:[^\W_]|-)*(?:\.(?:[^\W_]|-)*)*))?(?:(\+)((?:[^\W_]|-)+(?:\.(?:[^\W_]|-)+)*))?)?)?(?=:\{?\n)', bygroups(String.Symbol, Operator, Number.Integer, Operator, Number.Integer, Operator, Number.Integer, Operator, String, Operator, String)),

            (r'.*\n', Text),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\tornado\tcpserver.py ===
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking, single-threaded TCP server."""

import errno
import os
import socket
import ssl

from tornado import gen
from tornado.log import app_log
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream, SSLIOStream
from tornado.netutil import (
    bind_sockets,
    add_accept_handler,
    ssl_wrap_socket,
    _DEFAULT_BACKLOG,
)
from tornado import process
from tornado.util import errno_from_exception

import typing
from typing import Union, Dict, Any, Iterable, Optional, Awaitable

if typing.TYPE_CHECKING:
    from typing import Callable, List  # noqa: F401


class TCPServer:
    r"""A non-blocking, single-threaded TCP server.

    To use `TCPServer`, define a subclass which overrides the `handle_stream`
    method. For example, a simple echo server could be defined like this::

      from tornado.tcpserver import TCPServer
      from tornado.iostream import StreamClosedError

      class EchoServer(TCPServer):
          async def handle_stream(self, stream, address):
              while True:
                  try:
                      data = await stream.read_until(b"\n") await
                      stream.write(data)
                  except StreamClosedError:
                      break

    To make this server serve SSL traffic, send the ``ssl_options`` keyword
    argument with an `ssl.SSLContext` object. For compatibility with older
    versions of Python ``ssl_options`` may also be a dictionary of keyword
    arguments for the `ssl.SSLContext.wrap_socket` method.::

       ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
       ssl_ctx.load_cert_chain(os.path.join(data_dir, "mydomain.crt"),
                               os.path.join(data_dir, "mydomain.key"))
       TCPServer(ssl_options=ssl_ctx)

    `TCPServer` initialization follows one of three patterns:

    1. `listen`: single-process::

            async def main():
                server = TCPServer()
                server.listen(8888)
                await asyncio.Event().wait()

            asyncio.run(main())

       While this example does not create multiple processes on its own, when
       the ``reuse_port=True`` argument is passed to ``listen()`` you can run
       the program multiple times to create a multi-process service.

    2. `add_sockets`: multi-process::

            sockets = bind_sockets(8888)
            tornado.process.fork_processes(0)
            async def post_fork_main():
                server = TCPServer()
                server.add_sockets(sockets)
                await asyncio.Event().wait()
            asyncio.run(post_fork_main())

       The `add_sockets` interface is more complicated, but it can be used with
       `tornado.process.fork_processes` to run a multi-process service with all
       worker processes forked from a single parent.  `add_sockets` can also be
       used in single-process servers if you want to create your listening
       sockets in some way other than `~tornado.netutil.bind_sockets`.

       Note that when using this pattern, nothing that touches the event loop
       can be run before ``fork_processes``.

    3. `bind`/`start`: simple **deprecated** multi-process::

            server = TCPServer()
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.current().start()

       This pattern is deprecated because it requires interfaces in the
       `asyncio` module that have been deprecated since Python 3.10. Support for
       creating multiple processes in the ``start`` method will be removed in a
       future version of Tornado.

    .. versionadded:: 3.1
       The ``max_buffer_size`` argument.

    .. versionchanged:: 5.0
       The ``io_loop`` argument has been removed.
    """

    def __init__(
        self,
        ssl_options: Optional[Union[Dict[str, Any], ssl.SSLContext]] = None,
        max_buffer_size: Optional[int] = None,
        read_chunk_size: Optional[int] = None,
    ) -> None:
        self.ssl_options = ssl_options
        self._sockets = {}  # type: Dict[int, socket.socket]
        self._handlers = {}  # type: Dict[int, Callable[[], None]]
        self._pending_sockets = []  # type: List[socket.socket]
        self._started = False
        self._stopped = False
        self.max_buffer_size = max_buffer_size
        self.read_chunk_size = read_chunk_size

        # Verify the SSL options. Otherwise we don't get errors until clients
        # connect. This doesn't verify that the keys are legitimate, but
        # the SSL module doesn't do that until there is a connected socket
        # which seems like too much work
        if self.ssl_options is not None and isinstance(self.ssl_options, dict):
            # Only certfile is required: it can contain both keys
            if "certfile" not in self.ssl_options:
                raise KeyError('missing key "certfile" in ssl_options')

            if not os.path.exists(self.ssl_options["certfile"]):
                raise ValueError(
                    'certfile "%s" does not exist' % self.ssl_options["certfile"]
                )
            if "keyfile" in self.ssl_options and not os.path.exists(
                self.ssl_options["keyfile"]
            ):
                raise ValueError(
                    'keyfile "%s" does not exist' % self.ssl_options["keyfile"]
                )

    def listen(
        self,
        port: int,
        address: Optional[str] = None,
        family: socket.AddressFamily = socket.AF_UNSPEC,
        backlog: int = _DEFAULT_BACKLOG,
        flags: Optional[int] = None,
        reuse_port: bool = False,
    ) -> None:
        """Starts accepting connections on the given port.

        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately; it is not necessary to call
        `TCPServer.start` afterwards.  It is, however, necessary to start the
        event loop if it is not already running.

        All arguments have the same meaning as in
        `tornado.netutil.bind_sockets`.

        .. versionchanged:: 6.2

           Added ``family``, ``backlog``, ``flags``, and ``reuse_port``
           arguments to match `tornado.netutil.bind_sockets`.
        """
        sockets = bind_sockets(
            port,
            address=address,
            family=family,
            backlog=backlog,
            flags=flags,
            reuse_port=reuse_port,
        )
        self.add_sockets(sockets)

    def add_sockets(self, sockets: Iterable[socket.socket]) -> None:
        """Makes this server start accepting connections on the given sockets.

        The ``sockets`` parameter is a list of socket objects such as
        those returned by `~tornado.netutil.bind_sockets`.
        `add_sockets` is typically used in combination with that
        method and `tornado.process.fork_processes` to provide greater
        control over the initialization of a multi-process server.
        """
        for sock in sockets:
            self._sockets[sock.fileno()] = sock
            self._handlers[sock.fileno()] = add_accept_handler(
                sock, self._handle_connection
            )

    def add_socket(self, socket: socket.socket) -> None:
        """Singular version of `add_sockets`.  Takes a single socket object."""
        self.add_sockets([socket])

    def bind(
        self,
        port: int,
        address: Optional[str] = None,
        family: socket.AddressFamily = socket.AF_UNSPEC,
        backlog: int = _DEFAULT_BACKLOG,
        flags: Optional[int] = None,
        reuse_port: bool = False,
    ) -> None:
        """Binds this server to the given port on the given address.

        To start the server, call `start`. If you want to run this server in a
        single process, you can call `listen` as a shortcut to the sequence of
        `bind` and `start` calls.

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the name.
        Address may be an empty string or None to listen on all available
        interfaces.  Family may be set to either `socket.AF_INET` or
        `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise both
        will be used if available.

        The ``backlog`` argument has the same meaning as for `socket.listen
        <socket.socket.listen>`. The ``reuse_port`` argument has the same
        meaning as for `.bind_sockets`.

        This method may be called multiple times prior to `start` to listen on
        multiple ports or interfaces.

        .. versionchanged:: 4.4
           Added the ``reuse_port`` argument.

        .. versionchanged:: 6.2
           Added the ``flags`` argument to match `.bind_sockets`.

        .. deprecated:: 6.2
           Use either ``listen()`` or ``add_sockets()`` instead of ``bind()``
           and ``start()``.
        """
        sockets = bind_sockets(
            port,
            address=address,
            family=family,
            backlog=backlog,
            flags=flags,
            reuse_port=reuse_port,
        )
        if self._started:
            self.add_sockets(sockets)
        else:
            self._pending_sockets.extend(sockets)

    def start(
        self, num_processes: Optional[int] = 1, max_restarts: Optional[int] = None
    ) -> None:
        """Starts this server in the `.IOLoop`.

        By default, we run the server in this process and do not fork any
        additional child process.

        If num_processes is ``None`` or <= 0, we detect the number of cores
        available on this machine and fork that number of child
        processes. If num_processes is given and > 1, we fork that
        specific number of sub-processes.

        Since we use processes and not threads, there is no shared memory
        between any server code.

        Note that multiple processes are not compatible with the autoreload
        module (or the ``autoreload=True`` option to `tornado.web.Application`
        which defaults to True when ``debug=True``).
        When using multiple processes, no IOLoops can be created or
        referenced until after the call to ``TCPServer.start(n)``.

        Values of ``num_processes`` other than 1 are not supported on Windows.

        The ``max_restarts`` argument is passed to `.fork_processes`.

        .. versionchanged:: 6.0

           Added ``max_restarts`` argument.

        .. deprecated:: 6.2
           Use either ``listen()`` or ``add_sockets()`` instead of ``bind()``
           and ``start()``.
        """
        assert not self._started
        self._started = True
        if num_processes != 1:
            process.fork_processes(num_processes, max_restarts)
        sockets = self._pending_sockets
        self._pending_sockets = []
        self.add_sockets(sockets)

    def stop(self) -> None:
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        if self._stopped:
            return
        self._stopped = True
        for fd, sock in self._sockets.items():
            assert sock.fileno() == fd
            # Unregister socket from IOLoop
            self._handlers.pop(fd)()
            sock.close()

    def handle_stream(
        self, stream: IOStream, address: tuple
    ) -> Optional[Awaitable[None]]:
        """Override to handle a new `.IOStream` from an incoming connection.

        This method may be a coroutine; if so any exceptions it raises
        asynchronously will be logged. Accepting of incoming connections
        will not be blocked by this coroutine.

        If this `TCPServer` is configured for SSL, ``handle_stream``
        may be called before the SSL handshake has completed. Use
        `.SSLIOStream.wait_for_handshake` if you need to verify the client's
        certificate or use NPN/ALPN.

        .. versionchanged:: 4.2
           Added the option for this method to be a coroutine.
        """
        raise NotImplementedError()

    def _handle_connection(self, connection: socket.socket, address: Any) -> None:
        if self.ssl_options is not None:
            assert ssl, "OpenSSL required for SSL"
            try:
                connection = ssl_wrap_socket(
                    connection,
                    self.ssl_options,
                    server_side=True,
                    do_handshake_on_connect=False,
                )
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    return connection.close()
                else:
                    raise
            except OSError as err:
                # If the connection is closed immediately after it is created
                # (as in a port scan), we can get one of several errors.
                # wrap_socket makes an internal call to getpeername,
                # which may return either EINVAL (Mac OS X) or ENOTCONN
                # (Linux).  If it returns ENOTCONN, this error is
                # silently swallowed by the ssl module, so we need to
                # catch another error later on (AttributeError in
                # SSLIOStream._do_ssl_handshake).
                # To test this behavior, try nmap with the -sT flag.
                # https://github.com/tornadoweb/tornado/pull/750
                if errno_from_exception(err) in (errno.ECONNABORTED, errno.EINVAL):
                    return connection.close()
                else:
                    raise
        try:
            if self.ssl_options is not None:
                stream = SSLIOStream(
                    connection,
                    max_buffer_size=self.max_buffer_size,
                    read_chunk_size=self.read_chunk_size,
                )  # type: IOStream
            else:
                stream = IOStream(
                    connection,
                    max_buffer_size=self.max_buffer_size,
                    read_chunk_size=self.read_chunk_size,
                )

            future = self.handle_stream(stream, address)
            if future is not None:
                IOLoop.current().add_future(
                    gen.convert_yielded(future), lambda f: f.result()
                )
        except Exception:
            app_log.error("Error in connection callback", exc_info=True)

# === NexusCore/openenv\Lib\site-packages\yaml\__init__.py ===

from .error import *

from .tokens import *
from .events import *
from .nodes import *

from .loader import *
from .dumper import *

__version__ = '6.0.2'
try:
    from .cyaml import *
    __with_libyaml__ = True
except ImportError:
    __with_libyaml__ = False

import io

#------------------------------------------------------------------------------
# XXX "Warnings control" is now deprecated. Leaving in the API function to not
# break code that uses it.
#------------------------------------------------------------------------------
def warnings(settings=None):
    if settings is None:
        return {}

#------------------------------------------------------------------------------
def scan(stream, Loader=Loader):
    """
    Scan a YAML stream and produce scanning tokens.
    """
    loader = Loader(stream)
    try:
        while loader.check_token():
            yield loader.get_token()
    finally:
        loader.dispose()

def parse(stream, Loader=Loader):
    """
    Parse a YAML stream and produce parsing events.
    """
    loader = Loader(stream)
    try:
        while loader.check_event():
            yield loader.get_event()
    finally:
        loader.dispose()

def compose(stream, Loader=Loader):
    """
    Parse the first YAML document in a stream
    and produce the corresponding representation tree.
    """
    loader = Loader(stream)
    try:
        return loader.get_single_node()
    finally:
        loader.dispose()

def compose_all(stream, Loader=Loader):
    """
    Parse all YAML documents in a stream
    and produce corresponding representation trees.
    """
    loader = Loader(stream)
    try:
        while loader.check_node():
            yield loader.get_node()
    finally:
        loader.dispose()

def load(stream, Loader):
    """
    Parse the first YAML document in a stream
    and produce the corresponding Python object.
    """
    loader = Loader(stream)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()

def load_all(stream, Loader):
    """
    Parse all YAML documents in a stream
    and produce corresponding Python objects.
    """
    loader = Loader(stream)
    try:
        while loader.check_data():
            yield loader.get_data()
    finally:
        loader.dispose()

def full_load(stream):
    """
    Parse the first YAML document in a stream
    and produce the corresponding Python object.

    Resolve all tags except those known to be
    unsafe on untrusted input.
    """
    return load(stream, FullLoader)

def full_load_all(stream):
    """
    Parse all YAML documents in a stream
    and produce corresponding Python objects.

    Resolve all tags except those known to be
    unsafe on untrusted input.
    """
    return load_all(stream, FullLoader)

def safe_load(stream):
    """
    Parse the first YAML document in a stream
    and produce the corresponding Python object.

    Resolve only basic YAML tags. This is known
    to be safe for untrusted input.
    """
    return load(stream, SafeLoader)

def safe_load_all(stream):
    """
    Parse all YAML documents in a stream
    and produce corresponding Python objects.

    Resolve only basic YAML tags. This is known
    to be safe for untrusted input.
    """
    return load_all(stream, SafeLoader)

def unsafe_load(stream):
    """
    Parse the first YAML document in a stream
    and produce the corresponding Python object.

    Resolve all tags, even those known to be
    unsafe on untrusted input.
    """
    return load(stream, UnsafeLoader)

def unsafe_load_all(stream):
    """
    Parse all YAML documents in a stream
    and produce corresponding Python objects.

    Resolve all tags, even those known to be
    unsafe on untrusted input.
    """
    return load_all(stream, UnsafeLoader)

def emit(events, stream=None, Dumper=Dumper,
        canonical=None, indent=None, width=None,
        allow_unicode=None, line_break=None):
    """
    Emit YAML parsing events into a stream.
    If stream is None, return the produced string instead.
    """
    getvalue = None
    if stream is None:
        stream = io.StringIO()
        getvalue = stream.getvalue
    dumper = Dumper(stream, canonical=canonical, indent=indent, width=width,
            allow_unicode=allow_unicode, line_break=line_break)
    try:
        for event in events:
            dumper.emit(event)
    finally:
        dumper.dispose()
    if getvalue:
        return getvalue()

def serialize_all(nodes, stream=None, Dumper=Dumper,
        canonical=None, indent=None, width=None,
        allow_unicode=None, line_break=None,
        encoding=None, explicit_start=None, explicit_end=None,
        version=None, tags=None):
    """
    Serialize a sequence of representation trees into a YAML stream.
    If stream is None, return the produced string instead.
    """
    getvalue = None
    if stream is None:
        if encoding is None:
            stream = io.StringIO()
        else:
            stream = io.BytesIO()
        getvalue = stream.getvalue
    dumper = Dumper(stream, canonical=canonical, indent=indent, width=width,
            allow_unicode=allow_unicode, line_break=line_break,
            encoding=encoding, version=version, tags=tags,
            explicit_start=explicit_start, explicit_end=explicit_end)
    try:
        dumper.open()
        for node in nodes:
            dumper.serialize(node)
        dumper.close()
    finally:
        dumper.dispose()
    if getvalue:
        return getvalue()

def serialize(node, stream=None, Dumper=Dumper, **kwds):
    """
    Serialize a representation tree into a YAML stream.
    If stream is None, return the produced string instead.
    """
    return serialize_all([node], stream, Dumper=Dumper, **kwds)

def dump_all(documents, stream=None, Dumper=Dumper,
        default_style=None, default_flow_style=False,
        canonical=None, indent=None, width=None,
        allow_unicode=None, line_break=None,
        encoding=None, explicit_start=None, explicit_end=None,
        version=None, tags=None, sort_keys=True):
    """
    Serialize a sequence of Python objects into a YAML stream.
    If stream is None, return the produced string instead.
    """
    getvalue = None
    if stream is None:
        if encoding is None:
            stream = io.StringIO()
        else:
            stream = io.BytesIO()
        getvalue = stream.getvalue
    dumper = Dumper(stream, default_style=default_style,
            default_flow_style=default_flow_style,
            canonical=canonical, indent=indent, width=width,
            allow_unicode=allow_unicode, line_break=line_break,
            encoding=encoding, version=version, tags=tags,
            explicit_start=explicit_start, explicit_end=explicit_end, sort_keys=sort_keys)
    try:
        dumper.open()
        for data in documents:
            dumper.represent(data)
        dumper.close()
    finally:
        dumper.dispose()
    if getvalue:
        return getvalue()

def dump(data, stream=None, Dumper=Dumper, **kwds):
    """
    Serialize a Python object into a YAML stream.
    If stream is None, return the produced string instead.
    """
    return dump_all([data], stream, Dumper=Dumper, **kwds)

def safe_dump_all(documents, stream=None, **kwds):
    """
    Serialize a sequence of Python objects into a YAML stream.
    Produce only basic YAML tags.
    If stream is None, return the produced string instead.
    """
    return dump_all(documents, stream, Dumper=SafeDumper, **kwds)

def safe_dump(data, stream=None, **kwds):
    """
    Serialize a Python object into a YAML stream.
    Produce only basic YAML tags.
    If stream is None, return the produced string instead.
    """
    return dump_all([data], stream, Dumper=SafeDumper, **kwds)

def add_implicit_resolver(tag, regexp, first=None,
        Loader=None, Dumper=Dumper):
    """
    Add an implicit scalar detector.
    If an implicit scalar value matches the given regexp,
    the corresponding tag is assigned to the scalar.
    first is a sequence of possible initial characters or None.
    """
    if Loader is None:
        loader.Loader.add_implicit_resolver(tag, regexp, first)
        loader.FullLoader.add_implicit_resolver(tag, regexp, first)
        loader.UnsafeLoader.add_implicit_resolver(tag, regexp, first)
    else:
        Loader.add_implicit_resolver(tag, regexp, first)
    Dumper.add_implicit_resolver(tag, regexp, first)

def add_path_resolver(tag, path, kind=None, Loader=None, Dumper=Dumper):
    """
    Add a path based resolver for the given tag.
    A path is a list of keys that forms a path
    to a node in the representation tree.
    Keys can be string values, integers, or None.
    """
    if Loader is None:
        loader.Loader.add_path_resolver(tag, path, kind)
        loader.FullLoader.add_path_resolver(tag, path, kind)
        loader.UnsafeLoader.add_path_resolver(tag, path, kind)
    else:
        Loader.add_path_resolver(tag, path, kind)
    Dumper.add_path_resolver(tag, path, kind)

def add_constructor(tag, constructor, Loader=None):
    """
    Add a constructor for the given tag.
    Constructor is a function that accepts a Loader instance
    and a node object and produces the corresponding Python object.
    """
    if Loader is None:
        loader.Loader.add_constructor(tag, constructor)
        loader.FullLoader.add_constructor(tag, constructor)
        loader.UnsafeLoader.add_constructor(tag, constructor)
    else:
        Loader.add_constructor(tag, constructor)

def add_multi_constructor(tag_prefix, multi_constructor, Loader=None):
    """
    Add a multi-constructor for the given tag prefix.
    Multi-constructor is called for a node if its tag starts with tag_prefix.
    Multi-constructor accepts a Loader instance, a tag suffix,
    and a node object and produces the corresponding Python object.
    """
    if Loader is None:
        loader.Loader.add_multi_constructor(tag_prefix, multi_constructor)
        loader.FullLoader.add_multi_constructor(tag_prefix, multi_constructor)
        loader.UnsafeLoader.add_multi_constructor(tag_prefix, multi_constructor)
    else:
        Loader.add_multi_constructor(tag_prefix, multi_constructor)

def add_representer(data_type, representer, Dumper=Dumper):
    """
    Add a representer for the given type.
    Representer is a function accepting a Dumper instance
    and an instance of the given data type
    and producing the corresponding representation node.
    """
    Dumper.add_representer(data_type, representer)

def add_multi_representer(data_type, multi_representer, Dumper=Dumper):
    """
    Add a representer for the given type.
    Multi-representer is a function accepting a Dumper instance
    and an instance of the given data type or subtype
    and producing the corresponding representation node.
    """
    Dumper.add_multi_representer(data_type, multi_representer)

class YAMLObjectMetaclass(type):
    """
    The metaclass for YAMLObject.
    """
    def __init__(cls, name, bases, kwds):
        super(YAMLObjectMetaclass, cls).__init__(name, bases, kwds)
        if 'yaml_tag' in kwds and kwds['yaml_tag'] is not None:
            if isinstance(cls.yaml_loader, list):
                for loader in cls.yaml_loader:
                    loader.add_constructor(cls.yaml_tag, cls.from_yaml)
            else:
                cls.yaml_loader.add_constructor(cls.yaml_tag, cls.from_yaml)

            cls.yaml_dumper.add_representer(cls, cls.to_yaml)

class YAMLObject(metaclass=YAMLObjectMetaclass):
    """
    An object that can dump itself to a YAML stream
    and load itself from a YAML stream.
    """

    __slots__ = ()  # no direct instantiation, so allow immutable subclasses

    yaml_loader = [Loader, FullLoader, UnsafeLoader]
    yaml_dumper = Dumper

    yaml_tag = None
    yaml_flow_style = None

    @classmethod
    def from_yaml(cls, loader, node):
        """
        Convert a representation node to a Python object.
        """
        return loader.construct_yaml_object(node, cls)

    @classmethod
    def to_yaml(cls, dumper, data):
        """
        Convert a Python object to a representation node.
        """
        return dumper.represent_yaml_object(cls.yaml_tag, data, cls,
                flow_style=cls.yaml_flow_style)


# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\klass.py ===
"""
Like described in the :mod:`parso.python.tree` module,
there's a need for an ast like module to represent the states of parsed
modules.

But now there are also structures in Python that need a little bit more than
that. An ``Instance`` for example is only a ``Class`` before it is
instantiated. This class represents these cases.

So, why is there also a ``Class`` class here? Well, there are decorators and
they change classes in Python 3.

Representation modules also define "magic methods". Those methods look like
``py__foo__`` and are typically mappable to the Python equivalents ``__call__``
and others. Here's a list:

====================================== ========================================
**Method**                             **Description**
-------------------------------------- ----------------------------------------
py__call__(arguments: Array)           On callable objects, returns types.
py__bool__()                           Returns True/False/None; None means that
                                       there's no certainty.
py__bases__()                          Returns a list of base classes.
py__iter__()                           Returns a generator of a set of types.
py__class__()                          Returns the class of an instance.
py__simple_getitem__(index: int/str)   Returns a a set of types of the index.
                                       Can raise an IndexError/KeyError.
py__getitem__(indexes: ValueSet)       Returns a a set of types of the index.
py__file__()                           Only on modules. Returns None if does
                                       not exist.
py__package__() -> List[str]           Only on modules. For the import system.
py__path__()                           Only on modules. For the import system.
py__get__(call_object)                 Only on instances. Simulates
                                       descriptors.
py__doc__()                            Returns the docstring for a value.
====================================== ========================================

"""
from jedi import debug
from jedi.parser_utils import get_cached_parent_scope, expr_is_dotted, \
    function_is_property
from jedi.inference.cache import inference_state_method_cache, CachedMetaClass, \
    inference_state_method_generator_cache
from jedi.inference import compiled
from jedi.inference.lazy_value import LazyKnownValues, LazyTreeValue
from jedi.inference.filters import ParserTreeFilter
from jedi.inference.names import TreeNameDefinition, ValueName
from jedi.inference.arguments import unpack_arglist, ValuesArguments
from jedi.inference.base_value import ValueSet, iterator_to_value_set, \
    NO_VALUES
from jedi.inference.context import ClassContext
from jedi.inference.value.function import FunctionAndClassBase
from jedi.inference.gradual.generics import LazyGenericManager, TupleGenericManager
from jedi.plugins import plugin_manager


class ClassName(TreeNameDefinition):
    def __init__(self, class_value, tree_name, name_context, apply_decorators):
        super().__init__(name_context, tree_name)
        self._apply_decorators = apply_decorators
        self._class_value = class_value

    @iterator_to_value_set
    def infer(self):
        # We're using a different value to infer, so we cannot call super().
        from jedi.inference.syntax_tree import tree_name_to_values
        inferred = tree_name_to_values(
            self.parent_context.inference_state, self.parent_context, self.tree_name)

        for result_value in inferred:
            if self._apply_decorators:
                yield from result_value.py__get__(instance=None, class_value=self._class_value)
            else:
                yield result_value

    @property
    def api_type(self):
        type_ = super().api_type
        if type_ == 'function':
            definition = self.tree_name.get_definition()
            if definition is None:
                return type_
            if function_is_property(definition):
                # This essentially checks if there is an @property before
                # the function. @property could be something different, but
                # any programmer that redefines property as something that
                # is not really a property anymore, should be shot. (i.e.
                # this is a heuristic).
                return 'property'
        return type_


class ClassFilter(ParserTreeFilter):
    def __init__(self, class_value, node_context=None, until_position=None,
                 origin_scope=None, is_instance=False):
        super().__init__(
            class_value.as_context(), node_context,
            until_position=until_position,
            origin_scope=origin_scope,
        )
        self._class_value = class_value
        self._is_instance = is_instance

    def _convert_names(self, names):
        return [
            ClassName(
                class_value=self._class_value,
                tree_name=name,
                name_context=self._node_context,
                apply_decorators=not self._is_instance,
            ) for name in names
        ]

    def _equals_origin_scope(self):
        node = self._origin_scope
        while node is not None:
            if node == self._parser_scope or node == self.parent_context:
                return True
            node = get_cached_parent_scope(self._parso_cache_node, node)
        return False

    def _access_possible(self, name):
        # Filter for name mangling of private variables like __foo
        return not name.value.startswith('__') or name.value.endswith('__') \
            or self._equals_origin_scope()

    def _filter(self, names):
        names = super()._filter(names)
        return [name for name in names if self._access_possible(name)]


class ClassMixin:
    def is_class(self):
        return True

    def is_class_mixin(self):
        return True

    def py__call__(self, arguments):
        from jedi.inference.value import TreeInstance

        from jedi.inference.gradual.typing import TypedDict
        if self.is_typeddict():
            return ValueSet([TypedDict(self)])
        return ValueSet([TreeInstance(self.inference_state, self.parent_context, self, arguments)])

    def py__class__(self):
        return compiled.builtin_from_name(self.inference_state, 'type')

    @property
    def name(self):
        return ValueName(self, self.tree_node.name)

    def py__name__(self):
        return self.name.string_name

    @inference_state_method_generator_cache()
    def py__mro__(self):
        mro = [self]
        yield self
        # TODO Do a proper mro resolution. Currently we are just listing
        # classes. However, it's a complicated algorithm.
        for lazy_cls in self.py__bases__():
            # TODO there's multiple different mro paths possible if this yields
            # multiple possibilities. Could be changed to be more correct.
            for cls in lazy_cls.infer():
                # TODO detect for TypeError: duplicate base class str,
                # e.g.  `class X(str, str): pass`
                try:
                    mro_method = cls.py__mro__
                except AttributeError:
                    # TODO add a TypeError like:
                    """
                    >>> class Y(lambda: test): pass
                    Traceback (most recent call last):
                      File "<stdin>", line 1, in <module>
                    TypeError: function() argument 1 must be code, not str
                    >>> class Y(1): pass
                    Traceback (most recent call last):
                      File "<stdin>", line 1, in <module>
                    TypeError: int() takes at most 2 arguments (3 given)
                    """
                    debug.warning('Super class of %s is not a class: %s', self, cls)
                else:
                    for cls_new in mro_method():
                        if cls_new not in mro:
                            mro.append(cls_new)
                            yield cls_new

    def get_filters(self, origin_scope=None, is_instance=False,
                    include_metaclasses=True, include_type_when_class=True):
        if include_metaclasses:
            metaclasses = self.get_metaclasses()
            if metaclasses:
                yield from self.get_metaclass_filters(metaclasses, is_instance)

        for cls in self.py__mro__():
            if cls.is_compiled():
                yield from cls.get_filters(is_instance=is_instance)
            else:
                yield ClassFilter(
                    self, node_context=cls.as_context(),
                    origin_scope=origin_scope,
                    is_instance=is_instance
                )
        if not is_instance and include_type_when_class:
            from jedi.inference.compiled import builtin_from_name
            type_ = builtin_from_name(self.inference_state, 'type')
            assert isinstance(type_, ClassValue)
            if type_ != self:
                # We are not using execute_with_values here, because the
                # plugin function for type would get executed instead of an
                # instance creation.
                args = ValuesArguments([])
                for instance in type_.py__call__(args):
                    instance_filters = instance.get_filters()
                    # Filter out self filters
                    next(instance_filters, None)
                    next(instance_filters, None)
                    x = next(instance_filters, None)
                    assert x is not None
                    yield x

    def get_signatures(self):
        # Since calling staticmethod without a function is illegal, the Jedi
        # plugin doesn't return anything. Therefore call directly and get what
        # we want: An instance of staticmethod.
        metaclasses = self.get_metaclasses()
        if metaclasses:
            sigs = self.get_metaclass_signatures(metaclasses)
            if sigs:
                return sigs
        args = ValuesArguments([])
        init_funcs = self.py__call__(args).py__getattribute__('__init__')
        return [sig.bind(self) for sig in init_funcs.get_signatures()]

    def _as_context(self):
        return ClassContext(self)

    def get_type_hint(self, add_class_info=True):
        if add_class_info:
            return 'Type[%s]' % self.py__name__()
        return self.py__name__()

    @inference_state_method_cache(default=False)
    def is_typeddict(self):
        # TODO Do a proper mro resolution. Currently we are just listing
        # classes. However, it's a complicated algorithm.
        from jedi.inference.gradual.typing import TypedDictClass
        for lazy_cls in self.py__bases__():
            if not isinstance(lazy_cls, LazyTreeValue):
                return False
            tree_node = lazy_cls.data
            # Only resolve simple classes, stuff like Iterable[str] are more
            # intensive to resolve and if generics are involved, we know it's
            # not a TypedDict.
            if not expr_is_dotted(tree_node):
                return False

            for cls in lazy_cls.infer():
                if isinstance(cls, TypedDictClass):
                    return True
                try:
                    method = cls.is_typeddict
                except AttributeError:
                    # We're only dealing with simple classes, so just returning
                    # here should be fine. This only happens with e.g. compiled
                    # classes.
                    return False
                else:
                    if method():
                        return True
        return False

    def py__getitem__(self, index_value_set, contextualized_node):
        from jedi.inference.gradual.base import GenericClass
        if not index_value_set:
            debug.warning('Class indexes inferred to nothing. Returning class instead')
            return ValueSet([self])
        return ValueSet(
            GenericClass(
                self,
                LazyGenericManager(
                    context_of_index=contextualized_node.context,
                    index_value=index_value,
                )
            )
            for index_value in index_value_set
        )

    def with_generics(self, generics_tuple):
        from jedi.inference.gradual.base import GenericClass
        return GenericClass(
            self,
            TupleGenericManager(generics_tuple)
        )

    def define_generics(self, type_var_dict):
        from jedi.inference.gradual.base import GenericClass

        def remap_type_vars():
            """
            The TypeVars in the resulting classes have sometimes different names
            and we need to check for that, e.g. a signature can be:

            def iter(iterable: Iterable[_T]) -> Iterator[_T]: ...

            However, the iterator is defined as Iterator[_T_co], which means it has
            a different type var name.
            """
            for type_var in self.list_type_vars():
                yield type_var_dict.get(type_var.py__name__(), NO_VALUES)

        if type_var_dict:
            return ValueSet([GenericClass(
                self,
                TupleGenericManager(tuple(remap_type_vars()))
            )])
        return ValueSet({self})


class ClassValue(ClassMixin, FunctionAndClassBase, metaclass=CachedMetaClass):
    api_type = 'class'

    @inference_state_method_cache()
    def list_type_vars(self):
        found = []
        arglist = self.tree_node.get_super_arglist()
        if arglist is None:
            return []

        for stars, node in unpack_arglist(arglist):
            if stars:
                continue  # These are not relevant for this search.

            from jedi.inference.gradual.annotation import find_unknown_type_vars
            for type_var in find_unknown_type_vars(self.parent_context, node):
                if type_var not in found:
                    # The order matters and it's therefore a list.
                    found.append(type_var)
        return found

    def _get_bases_arguments(self):
        arglist = self.tree_node.get_super_arglist()
        if arglist:
            from jedi.inference import arguments
            return arguments.TreeArguments(self.inference_state, self.parent_context, arglist)
        return None

    @inference_state_method_cache(default=())
    def py__bases__(self):
        args = self._get_bases_arguments()
        if args is not None:
            lst = [value for key, value in args.unpack() if key is None]
            if lst:
                return lst

        if self.py__name__() == 'object' \
                and self.parent_context.is_builtins_module():
            return []
        return [LazyKnownValues(
            self.inference_state.builtins_module.py__getattribute__('object')
        )]

    @plugin_manager.decorate()
    def get_metaclass_filters(self, metaclasses, is_instance):
        debug.warning('Unprocessed metaclass %s', metaclasses)
        return []

    @inference_state_method_cache(default=NO_VALUES)
    def get_metaclasses(self):
        args = self._get_bases_arguments()
        if args is not None:
            m = [value for key, value in args.unpack() if key == 'metaclass']
            metaclasses = ValueSet.from_sets(lazy_value.infer() for lazy_value in m)
            metaclasses = ValueSet(m for m in metaclasses if m.is_class())
            if metaclasses:
                return metaclasses

        for lazy_base in self.py__bases__():
            for value in lazy_base.infer():
                if value.is_class():
                    values = value.get_metaclasses()
                    if values:
                        return values
        return NO_VALUES

    @plugin_manager.decorate()
    def get_metaclass_signatures(self, metaclasses):
        return []

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_add_newdocs_scalars.py ===
"""
This file is separate from ``_add_newdocs.py`` so that it can be mocked out by
our sphinx ``conf.py`` during doc builds, where we want to avoid showing
platform-dependent information.
"""
import os
import sys

from numpy._core import dtype
from numpy._core import numerictypes as _numerictypes
from numpy._core.function_base import add_newdoc

##############################################################################
#
# Documentation for concrete scalar classes
#
##############################################################################

def numeric_type_aliases(aliases):
    def type_aliases_gen():
        for alias, doc in aliases:
            try:
                alias_type = getattr(_numerictypes, alias)
            except AttributeError:
                # The set of aliases that actually exist varies between platforms
                pass
            else:
                yield (alias_type, alias, doc)
    return list(type_aliases_gen())


possible_aliases = numeric_type_aliases([
    ('int8', '8-bit signed integer (``-128`` to ``127``)'),
    ('int16', '16-bit signed integer (``-32_768`` to ``32_767``)'),
    ('int32', '32-bit signed integer (``-2_147_483_648`` to ``2_147_483_647``)'),
    ('int64', '64-bit signed integer (``-9_223_372_036_854_775_808`` to ``9_223_372_036_854_775_807``)'),
    ('intp', 'Signed integer large enough to fit pointer, compatible with C ``intptr_t``'),
    ('uint8', '8-bit unsigned integer (``0`` to ``255``)'),
    ('uint16', '16-bit unsigned integer (``0`` to ``65_535``)'),
    ('uint32', '32-bit unsigned integer (``0`` to ``4_294_967_295``)'),
    ('uint64', '64-bit unsigned integer (``0`` to ``18_446_744_073_709_551_615``)'),
    ('uintp', 'Unsigned integer large enough to fit pointer, compatible with C ``uintptr_t``'),
    ('float16', '16-bit-precision floating-point number type: sign bit, 5 bits exponent, 10 bits mantissa'),
    ('float32', '32-bit-precision floating-point number type: sign bit, 8 bits exponent, 23 bits mantissa'),
    ('float64', '64-bit precision floating-point number type: sign bit, 11 bits exponent, 52 bits mantissa'),
    ('float96', '96-bit extended-precision floating-point number type'),
    ('float128', '128-bit extended-precision floating-point number type'),
    ('complex64', 'Complex number type composed of 2 32-bit-precision floating-point numbers'),
    ('complex128', 'Complex number type composed of 2 64-bit-precision floating-point numbers'),
    ('complex192', 'Complex number type composed of 2 96-bit extended-precision floating-point numbers'),
    ('complex256', 'Complex number type composed of 2 128-bit extended-precision floating-point numbers'),
    ])


def _get_platform_and_machine():
    try:
        system, _, _, _, machine = os.uname()
    except AttributeError:
        system = sys.platform
        if system == 'win32':
            machine = os.environ.get('PROCESSOR_ARCHITEW6432', '') \
                    or os.environ.get('PROCESSOR_ARCHITECTURE', '')
        else:
            machine = 'unknown'
    return system, machine


_system, _machine = _get_platform_and_machine()
_doc_alias_string = f":Alias on this platform ({_system} {_machine}):"


def add_newdoc_for_scalar_type(obj, fixed_aliases, doc):
    # note: `:field: value` is rST syntax which renders as field lists.
    o = getattr(_numerictypes, obj)

    character_code = dtype(o).char
    canonical_name_doc = "" if obj == o.__name__ else \
                        f":Canonical name: `numpy.{obj}`\n    "
    if fixed_aliases:
        alias_doc = ''.join(f":Alias: `numpy.{alias}`\n    "
                            for alias in fixed_aliases)
    else:
        alias_doc = ''
    alias_doc += ''.join(f"{_doc_alias_string} `numpy.{alias}`: {doc}.\n    "
                         for (alias_type, alias, doc) in possible_aliases if alias_type is o)

    docstring = f"""
    {doc.strip()}

    :Character code: ``'{character_code}'``
    {canonical_name_doc}{alias_doc}
    """

    add_newdoc('numpy._core.numerictypes', obj, docstring)


_bool_docstring = (
    """
    Boolean type (True or False), stored as a byte.

    .. warning::

       The :class:`bool` type is not a subclass of the :class:`int_` type
       (the :class:`bool` is not even a number type). This is different
       than Python's default implementation of :class:`bool` as a
       sub-class of :class:`int`.
    """
)

add_newdoc_for_scalar_type('bool', [], _bool_docstring)

add_newdoc_for_scalar_type('bool_', [], _bool_docstring)

add_newdoc_for_scalar_type('byte', [],
    """
    Signed integer type, compatible with C ``char``.
    """)

add_newdoc_for_scalar_type('short', [],
    """
    Signed integer type, compatible with C ``short``.
    """)

add_newdoc_for_scalar_type('intc', [],
    """
    Signed integer type, compatible with C ``int``.
    """)

# TODO: These docs probably need an if to highlight the default rather than
#       the C-types (and be correct).
add_newdoc_for_scalar_type('int_', [],
    """
    Default signed integer type, 64bit on 64bit systems and 32bit on 32bit
    systems.
    """)

add_newdoc_for_scalar_type('longlong', [],
    """
    Signed integer type, compatible with C ``long long``.
    """)

add_newdoc_for_scalar_type('ubyte', [],
    """
    Unsigned integer type, compatible with C ``unsigned char``.
    """)

add_newdoc_for_scalar_type('ushort', [],
    """
    Unsigned integer type, compatible with C ``unsigned short``.
    """)

add_newdoc_for_scalar_type('uintc', [],
    """
    Unsigned integer type, compatible with C ``unsigned int``.
    """)

add_newdoc_for_scalar_type('uint', [],
    """
    Unsigned signed integer type, 64bit on 64bit systems and 32bit on 32bit
    systems.
    """)

add_newdoc_for_scalar_type('ulonglong', [],
    """
    Signed integer type, compatible with C ``unsigned long long``.
    """)

add_newdoc_for_scalar_type('half', [],
    """
    Half-precision floating-point number type.
    """)

add_newdoc_for_scalar_type('single', [],
    """
    Single-precision floating-point number type, compatible with C ``float``.
    """)

add_newdoc_for_scalar_type('double', [],
    """
    Double-precision floating-point number type, compatible with Python
    :class:`float` and C ``double``.
    """)

add_newdoc_for_scalar_type('longdouble', [],
    """
    Extended-precision floating-point number type, compatible with C
    ``long double`` but not necessarily with IEEE 754 quadruple-precision.
    """)

add_newdoc_for_scalar_type('csingle', [],
    """
    Complex number type composed of two single-precision floating-point
    numbers.
    """)

add_newdoc_for_scalar_type('cdouble', [],
    """
    Complex number type composed of two double-precision floating-point
    numbers, compatible with Python :class:`complex`.
    """)

add_newdoc_for_scalar_type('clongdouble', [],
    """
    Complex number type composed of two extended-precision floating-point
    numbers.
    """)

add_newdoc_for_scalar_type('object_', [],
    """
    Any Python object.
    """)

add_newdoc_for_scalar_type('str_', [],
    r"""
    A unicode string.

    This type strips trailing null codepoints.

    >>> s = np.str_("abc\x00")
    >>> s
    'abc'

    Unlike the builtin :class:`str`, this supports the
    :ref:`python:bufferobjects`, exposing its contents as UCS4:

    >>> m = memoryview(np.str_("abc"))
    >>> m.format
    '3w'
    >>> m.tobytes()
    b'a\x00\x00\x00b\x00\x00\x00c\x00\x00\x00'
    """)

add_newdoc_for_scalar_type('bytes_', [],
    r"""
    A byte string.

    When used in arrays, this type strips trailing null bytes.
    """)

add_newdoc_for_scalar_type('void', [],
    r"""
    np.void(length_or_data, /, dtype=None)

    Create a new structured or unstructured void scalar.

    Parameters
    ----------
    length_or_data : int, array-like, bytes-like, object
       One of multiple meanings (see notes).  The length or
       bytes data of an unstructured void.  Or alternatively,
       the data to be stored in the new scalar when `dtype`
       is provided.
       This can be an array-like, in which case an array may
       be returned.
    dtype : dtype, optional
       If provided the dtype of the new scalar.  This dtype must
       be "void" dtype (i.e. a structured or unstructured void,
       see also :ref:`defining-structured-types`).

       .. versionadded:: 1.24

    Notes
    -----
    For historical reasons and because void scalars can represent both
    arbitrary byte data and structured dtypes, the void constructor
    has three calling conventions:

    1. ``np.void(5)`` creates a ``dtype="V5"`` scalar filled with five
       ``\0`` bytes.  The 5 can be a Python or NumPy integer.
    2. ``np.void(b"bytes-like")`` creates a void scalar from the byte string.
       The dtype itemsize will match the byte string length, here ``"V10"``.
    3. When a ``dtype=`` is passed the call is roughly the same as an
       array creation.  However, a void scalar rather than array is returned.

    Please see the examples which show all three different conventions.

    Examples
    --------
    >>> np.void(5)
    np.void(b'\x00\x00\x00\x00\x00')
    >>> np.void(b'abcd')
    np.void(b'\x61\x62\x63\x64')
    >>> np.void((3.2, b'eggs'), dtype="d,S5")
    np.void((3.2, b'eggs'), dtype=[('f0', '<f8'), ('f1', 'S5')])
    >>> np.void(3, dtype=[('x', np.int8), ('y', np.int8)])
    np.void((3, 3), dtype=[('x', 'i1'), ('y', 'i1')])

    """)

add_newdoc_for_scalar_type('datetime64', [],
    """
    If created from a 64-bit integer, it represents an offset from
    ``1970-01-01T00:00:00``.
    If created from string, the string can be in ISO 8601 date
    or datetime format.

    When parsing a string to create a datetime object, if the string contains
    a trailing timezone (A 'Z' or a timezone offset), the timezone will be
    dropped and a User Warning is given.

    Datetime64 objects should be considered to be UTC and therefore have an
    offset of +0000.

    >>> np.datetime64(10, 'Y')
    np.datetime64('1980')
    >>> np.datetime64('1980', 'Y')
    np.datetime64('1980')
    >>> np.datetime64(10, 'D')
    np.datetime64('1970-01-11')

    See :ref:`arrays.datetime` for more information.
    """)

add_newdoc_for_scalar_type('timedelta64', [],
    """
    A timedelta stored as a 64-bit integer.

    See :ref:`arrays.datetime` for more information.
    """)

add_newdoc('numpy._core.numerictypes', "integer", ('is_integer',
    """
    integer.is_integer() -> bool

    Return ``True`` if the number is finite with integral value.

    .. versionadded:: 1.22

    Examples
    --------
    >>> import numpy as np
    >>> np.int64(-2).is_integer()
    True
    >>> np.uint32(5).is_integer()
    True
    """))

# TODO: work out how to put this on the base class, np.floating
for float_name in ('half', 'single', 'double', 'longdouble'):
    add_newdoc('numpy._core.numerictypes', float_name, ('as_integer_ratio',
        f"""
        {float_name}.as_integer_ratio() -> (int, int)

        Return a pair of integers, whose ratio is exactly equal to the original
        floating point number, and with a positive denominator.
        Raise `OverflowError` on infinities and a `ValueError` on NaNs.

        >>> np.{float_name}(10.0).as_integer_ratio()
        (10, 1)
        >>> np.{float_name}(0.0).as_integer_ratio()
        (0, 1)
        >>> np.{float_name}(-.25).as_integer_ratio()
        (-1, 4)
        """))

    add_newdoc('numpy._core.numerictypes', float_name, ('is_integer',
        f"""
        {float_name}.is_integer() -> bool

        Return ``True`` if the floating point number is finite with integral
        value, and ``False`` otherwise.

        .. versionadded:: 1.22

        Examples
        --------
        >>> np.{float_name}(-2.0).is_integer()
        True
        >>> np.{float_name}(3.2).is_integer()
        False
        """))

for int_name in ('int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32',
        'int64', 'uint64', 'int64', 'uint64', 'int64', 'uint64'):
    # Add negative examples for signed cases by checking typecode
    add_newdoc('numpy._core.numerictypes', int_name, ('bit_count',
        f"""
        {int_name}.bit_count() -> int

        Computes the number of 1-bits in the absolute value of the input.
        Analogous to the builtin `int.bit_count` or ``popcount`` in C++.

        Examples
        --------
        >>> np.{int_name}(127).bit_count()
        7""" +
        (f"""
        >>> np.{int_name}(-127).bit_count()
        7
        """ if dtype(int_name).char.islower() else "")))

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_parking_lot.py ===
from __future__ import annotations

import re
from typing import TypeVar

import pytest

import trio
from trio.lowlevel import (
    add_parking_lot_breaker,
    current_task,
    remove_parking_lot_breaker,
)
from trio.testing import Matcher, RaisesGroup

from ... import _core
from ...testing import wait_all_tasks_blocked
from .._parking_lot import ParkingLot
from .tutil import check_sequence_matches

T = TypeVar("T")


async def test_parking_lot_basic() -> None:
    record = []

    async def waiter(i: int, lot: ParkingLot) -> None:
        record.append(f"sleep {i}")
        await lot.park()
        record.append(f"wake {i}")

    async with _core.open_nursery() as nursery:
        lot = ParkingLot()
        assert not lot
        assert len(lot) == 0
        assert lot.statistics().tasks_waiting == 0
        for i in range(3):
            nursery.start_soon(waiter, i, lot)
        await wait_all_tasks_blocked()
        assert len(record) == 3
        assert bool(lot)
        assert len(lot) == 3
        assert lot.statistics().tasks_waiting == 3
        lot.unpark_all()
        assert lot.statistics().tasks_waiting == 0
        await wait_all_tasks_blocked()
        assert len(record) == 6

    check_sequence_matches(
        record,
        [{"sleep 0", "sleep 1", "sleep 2"}, {"wake 0", "wake 1", "wake 2"}],
    )

    async with _core.open_nursery() as nursery:
        record = []
        for i in range(3):
            nursery.start_soon(waiter, i, lot)
            await wait_all_tasks_blocked()
        assert len(record) == 3
        for _ in range(3):
            lot.unpark()
            await wait_all_tasks_blocked()
        # 1-by-1 wakeups are strict FIFO
        assert record == [
            "sleep 0",
            "sleep 1",
            "sleep 2",
            "wake 0",
            "wake 1",
            "wake 2",
        ]

    # It's legal (but a no-op) to try and unpark while there's nothing parked
    lot.unpark()
    lot.unpark(count=1)
    lot.unpark(count=100)

    # Check unpark with count
    async with _core.open_nursery() as nursery:
        record = []
        for i in range(3):
            nursery.start_soon(waiter, i, lot)
            await wait_all_tasks_blocked()
        lot.unpark(count=2)
        await wait_all_tasks_blocked()
        check_sequence_matches(
            record,
            ["sleep 0", "sleep 1", "sleep 2", {"wake 0", "wake 1"}],
        )
        lot.unpark_all()

    with pytest.raises(
        ValueError,
        match=r"^Cannot pop a non-integer number of tasks\.$",
    ):
        lot.unpark(count=1.5)


async def cancellable_waiter(
    name: T,
    lot: ParkingLot,
    scopes: dict[T, _core.CancelScope],
    record: list[str],
) -> None:
    with _core.CancelScope() as scope:
        scopes[name] = scope
        record.append(f"sleep {name}")
        try:
            await lot.park()
        except _core.Cancelled:
            record.append(f"cancelled {name}")
        else:
            record.append(f"wake {name}")


async def test_parking_lot_cancel() -> None:
    record: list[str] = []
    scopes: dict[int, _core.CancelScope] = {}

    async with _core.open_nursery() as nursery:
        lot = ParkingLot()
        nursery.start_soon(cancellable_waiter, 1, lot, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 2, lot, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 3, lot, scopes, record)
        await wait_all_tasks_blocked()
        assert len(record) == 3

        scopes[2].cancel()
        await wait_all_tasks_blocked()
        assert len(record) == 4
        lot.unpark_all()
        await wait_all_tasks_blocked()
        assert len(record) == 6

    check_sequence_matches(
        record,
        ["sleep 1", "sleep 2", "sleep 3", "cancelled 2", {"wake 1", "wake 3"}],
    )


async def test_parking_lot_repark() -> None:
    record: list[str] = []
    scopes: dict[int, _core.CancelScope] = {}
    lot1 = ParkingLot()
    lot2 = ParkingLot()

    with pytest.raises(TypeError):
        lot1.repark([])  # type: ignore[arg-type]

    async with _core.open_nursery() as nursery:
        nursery.start_soon(cancellable_waiter, 1, lot1, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 2, lot1, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 3, lot1, scopes, record)
        await wait_all_tasks_blocked()
        assert len(record) == 3

        assert len(lot1) == 3
        lot1.repark(lot2)
        assert len(lot1) == 2
        assert len(lot2) == 1
        lot2.unpark_all()
        await wait_all_tasks_blocked()
        assert len(record) == 4
        assert record == ["sleep 1", "sleep 2", "sleep 3", "wake 1"]

        lot1.repark_all(lot2)
        assert len(lot1) == 0
        assert len(lot2) == 2

        scopes[2].cancel()
        await wait_all_tasks_blocked()
        assert len(lot2) == 1
        assert record == [
            "sleep 1",
            "sleep 2",
            "sleep 3",
            "wake 1",
            "cancelled 2",
        ]

        lot2.unpark_all()
        await wait_all_tasks_blocked()
        assert record == [
            "sleep 1",
            "sleep 2",
            "sleep 3",
            "wake 1",
            "cancelled 2",
            "wake 3",
        ]


async def test_parking_lot_repark_with_count() -> None:
    record: list[str] = []
    scopes: dict[int, _core.CancelScope] = {}
    lot1 = ParkingLot()
    lot2 = ParkingLot()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(cancellable_waiter, 1, lot1, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 2, lot1, scopes, record)
        await wait_all_tasks_blocked()
        nursery.start_soon(cancellable_waiter, 3, lot1, scopes, record)
        await wait_all_tasks_blocked()
        assert len(record) == 3

        assert len(lot1) == 3
        assert len(lot2) == 0
        lot1.repark(lot2, count=2)
        assert len(lot1) == 1
        assert len(lot2) == 2
        while lot2:
            lot2.unpark()
            await wait_all_tasks_blocked()
        assert record == [
            "sleep 1",
            "sleep 2",
            "sleep 3",
            "wake 1",
            "wake 2",
        ]
        lot1.unpark_all()


async def dummy_task(
    task_status: _core.TaskStatus[_core.Task] = trio.TASK_STATUS_IGNORED,
) -> None:
    task_status.started(_core.current_task())
    await trio.sleep_forever()


async def test_parking_lot_breaker_basic() -> None:
    """Test basic functionality for breaking lots."""
    lot = ParkingLot()
    task = current_task()

    # defaults to current task
    lot.break_lot()
    assert lot.broken_by == [task]

    # breaking the lot again with the same task appends another copy in `broken_by`
    lot.break_lot()
    assert lot.broken_by == [task, task]

    # trying to park in broken lot errors
    broken_by_str = re.escape(str([task, task]))
    with pytest.raises(
        _core.BrokenResourceError,
        match=f"^Attempted to park in parking lot broken by {broken_by_str}$",
    ):
        await lot.park()


async def test_parking_lot_break_parking_tasks() -> None:
    """Checks that tasks currently waiting to park raise an error when the breaker exits."""

    async def bad_parker(lot: ParkingLot, scope: _core.CancelScope) -> None:
        add_parking_lot_breaker(current_task(), lot)
        with scope:
            await trio.sleep_forever()

    lot = ParkingLot()
    cs = _core.CancelScope()

    # check that parked task errors
    with RaisesGroup(
        Matcher(_core.BrokenResourceError, match="^Parking lot broken by"),
    ):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(bad_parker, lot, cs)
            await wait_all_tasks_blocked()

            nursery.start_soon(lot.park)
            await wait_all_tasks_blocked()

            cs.cancel()


async def test_parking_lot_breaker_registration() -> None:
    lot = ParkingLot()
    task = current_task()

    with pytest.raises(
        RuntimeError,
        match="Attempted to remove task as breaker for a lot it is not registered for",
    ):
        remove_parking_lot_breaker(task, lot)

    # check that a task can be registered as breaker for the same lot multiple times
    add_parking_lot_breaker(task, lot)
    add_parking_lot_breaker(task, lot)
    remove_parking_lot_breaker(task, lot)
    remove_parking_lot_breaker(task, lot)

    with pytest.raises(
        RuntimeError,
        match="Attempted to remove task as breaker for a lot it is not registered for",
    ):
        remove_parking_lot_breaker(task, lot)

    # registering a task as breaker on an already broken lot is fine
    lot.break_lot()
    child_task: _core.Task | None = None
    async with trio.open_nursery() as nursery:
        child_task = await nursery.start(dummy_task)
        assert isinstance(child_task, _core.Task)
        add_parking_lot_breaker(child_task, lot)
        nursery.cancel_scope.cancel()
    assert lot.broken_by == [task, child_task]

    # manually breaking a lot with an already exited task is fine
    lot = ParkingLot()
    lot.break_lot(child_task)
    assert lot.broken_by == [child_task]


async def test_parking_lot_breaker_rebreak() -> None:
    lot = ParkingLot()
    task = current_task()
    lot.break_lot()

    # breaking an already broken lot with a different task is allowed
    # The nursery is only to create a task we can pass to lot.break_lot
    async with trio.open_nursery() as nursery:
        child_task = await nursery.start(dummy_task)
        lot.break_lot(child_task)
        nursery.cancel_scope.cancel()

    assert lot.broken_by == [task, child_task]


async def test_parking_lot_multiple_breakers_exit() -> None:
    # register multiple tasks as lot breakers, then have them all exit
    lot = ParkingLot()
    async with trio.open_nursery() as nursery:
        child_task1 = await nursery.start(dummy_task)
        child_task2 = await nursery.start(dummy_task)
        child_task3 = await nursery.start(dummy_task)
        assert isinstance(child_task1, _core.Task)
        assert isinstance(child_task2, _core.Task)
        assert isinstance(child_task3, _core.Task)
        add_parking_lot_breaker(child_task1, lot)
        add_parking_lot_breaker(child_task2, lot)
        add_parking_lot_breaker(child_task3, lot)
        nursery.cancel_scope.cancel()

    # I think the order is guaranteed currently, but doesn't hurt to be safe.
    assert set(lot.broken_by) == {child_task1, child_task2, child_task3}


async def test_parking_lot_breaker_register_exited_task() -> None:
    lot = ParkingLot()
    child_task: _core.Task | None = None
    async with trio.open_nursery() as nursery:
        value = await nursery.start(dummy_task)
        assert isinstance(value, _core.Task)
        child_task = value
        nursery.cancel_scope.cancel()
    # trying to register an exited task as lot breaker errors
    with pytest.raises(
        trio.BrokenResourceError,
        match=r"^Attempted to add already exited task as lot breaker.$",
    ):
        add_parking_lot_breaker(child_task, lot)


async def test_parking_lot_break_itself() -> None:
    """Break a parking lot, where the breakee is parked.
    Doing this is weird, but should probably be supported.
    """

    async def return_me_and_park(
        lot: ParkingLot,
        *,
        task_status: _core.TaskStatus[_core.Task] = trio.TASK_STATUS_IGNORED,
    ) -> None:
        task_status.started(_core.current_task())
        await lot.park()

    lot = ParkingLot()
    with RaisesGroup(
        Matcher(_core.BrokenResourceError, match="^Parking lot broken by"),
    ):
        async with _core.open_nursery() as nursery:
            child_task = await nursery.start(return_me_and_park, lot)
            lot.break_lot(child_task)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pyproject_hooks\_in_process\_in_process.py ===
"""This is invoked in a subprocess to call the build backend hooks.

It expects:
- Command line args: hook_name, control_dir
- Environment variables:
      _PYPROJECT_HOOKS_BUILD_BACKEND=entry.point:spec
      _PYPROJECT_HOOKS_BACKEND_PATH=paths (separated with os.pathsep)
- control_dir/input.json:
  - {"kwargs": {...}}

Results:
- control_dir/output.json
  - {"return_val": ...}
"""
import json
import os
import os.path
import re
import shutil
import sys
import traceback
from glob import glob
from importlib import import_module
from importlib.machinery import PathFinder
from os.path import join as pjoin

# This file is run as a script, and `import wrappers` is not zip-safe, so we
# include write_json() and read_json() from wrappers.py.


def write_json(obj, path, **kwargs):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kwargs)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class BackendUnavailable(Exception):
    """Raised if we cannot import the backend"""

    def __init__(self, message, traceback=None):
        super().__init__(message)
        self.message = message
        self.traceback = traceback


class HookMissing(Exception):
    """Raised if a hook is missing and we are not executing the fallback"""

    def __init__(self, hook_name=None):
        super().__init__(hook_name)
        self.hook_name = hook_name


def _build_backend():
    """Find and load the build backend"""
    backend_path = os.environ.get("_PYPROJECT_HOOKS_BACKEND_PATH")
    ep = os.environ["_PYPROJECT_HOOKS_BUILD_BACKEND"]
    mod_path, _, obj_path = ep.partition(":")

    if backend_path:
        # Ensure in-tree backend directories have the highest priority when importing.
        extra_pathitems = backend_path.split(os.pathsep)
        sys.meta_path.insert(0, _BackendPathFinder(extra_pathitems, mod_path))

    try:
        obj = import_module(mod_path)
    except ImportError:
        msg = f"Cannot import {mod_path!r}"
        raise BackendUnavailable(msg, traceback.format_exc())

    if obj_path:
        for path_part in obj_path.split("."):
            obj = getattr(obj, path_part)
    return obj


class _BackendPathFinder:
    """Implements the MetaPathFinder interface to locate modules in ``backend-path``.

    Since the environment provided by the frontend can contain all sorts of
    MetaPathFinders, the only way to ensure the backend is loaded from the
    right place is to prepend our own.
    """

    def __init__(self, backend_path, backend_module):
        self.backend_path = backend_path
        self.backend_module = backend_module
        self.backend_parent, _, _ = backend_module.partition(".")

    def find_spec(self, fullname, _path, _target=None):
        if "." in fullname:
            # Rely on importlib to find nested modules based on parent's path
            return None

        # Ignore other items in _path or sys.path and use backend_path instead:
        spec = PathFinder.find_spec(fullname, path=self.backend_path)
        if spec is None and fullname == self.backend_parent:
            # According to the spec, the backend MUST be loaded from backend-path.
            # Therefore, we can halt the import machinery and raise a clean error.
            msg = f"Cannot find module {self.backend_module!r} in {self.backend_path!r}"
            raise BackendUnavailable(msg)

        return spec

    if sys.version_info >= (3, 8):

        def find_distributions(self, context=None):
            # Delayed import: Python 3.7 does not contain importlib.metadata
            from importlib.metadata import DistributionFinder, MetadataPathFinder

            context = DistributionFinder.Context(path=self.backend_path)
            return MetadataPathFinder.find_distributions(context=context)


def _supported_features():
    """Return the list of options features supported by the backend.

    Returns a list of strings.
    The only possible value is 'build_editable'.
    """
    backend = _build_backend()
    features = []
    if hasattr(backend, "build_editable"):
        features.append("build_editable")
    return features


def get_requires_for_build_wheel(config_settings):
    """Invoke the optional get_requires_for_build_wheel hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_wheel
    except AttributeError:
        return []
    else:
        return hook(config_settings)


def get_requires_for_build_editable(config_settings):
    """Invoke the optional get_requires_for_build_editable hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_editable
    except AttributeError:
        return []
    else:
        return hook(config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory, config_settings, _allow_fallback
):
    """Invoke optional prepare_metadata_for_build_wheel

    Implements a fallback by building a wheel if the hook isn't defined,
    unless _allow_fallback is False in which case HookMissing is raised.
    """
    backend = _build_backend()
    try:
        hook = backend.prepare_metadata_for_build_wheel
    except AttributeError:
        if not _allow_fallback:
            raise HookMissing()
    else:
        return hook(metadata_directory, config_settings)
    # fallback to build_wheel outside the try block to avoid exception chaining
    # which can be confusing to users and is not relevant
    whl_basename = backend.build_wheel(metadata_directory, config_settings)
    return _get_wheel_metadata_from_wheel(
        whl_basename, metadata_directory, config_settings
    )


def prepare_metadata_for_build_editable(
    metadata_directory, config_settings, _allow_fallback
):
    """Invoke optional prepare_metadata_for_build_editable

    Implements a fallback by building an editable wheel if the hook isn't
    defined, unless _allow_fallback is False in which case HookMissing is
    raised.
    """
    backend = _build_backend()
    try:
        hook = backend.prepare_metadata_for_build_editable
    except AttributeError:
        if not _allow_fallback:
            raise HookMissing()
        try:
            build_hook = backend.build_editable
        except AttributeError:
            raise HookMissing(hook_name="build_editable")
        else:
            whl_basename = build_hook(metadata_directory, config_settings)
            return _get_wheel_metadata_from_wheel(
                whl_basename, metadata_directory, config_settings
            )
    else:
        return hook(metadata_directory, config_settings)


WHEEL_BUILT_MARKER = "PYPROJECT_HOOKS_ALREADY_BUILT_WHEEL"


def _dist_info_files(whl_zip):
    """Identify the .dist-info folder inside a wheel ZipFile."""
    res = []
    for path in whl_zip.namelist():
        m = re.match(r"[^/\\]+-[^/\\]+\.dist-info/", path)
        if m:
            res.append(path)
    if res:
        return res
    raise Exception("No .dist-info folder found in wheel")


def _get_wheel_metadata_from_wheel(whl_basename, metadata_directory, config_settings):
    """Extract the metadata from a wheel.

    Fallback for when the build backend does not
    define the 'get_wheel_metadata' hook.
    """
    from zipfile import ZipFile

    with open(os.path.join(metadata_directory, WHEEL_BUILT_MARKER), "wb"):
        pass  # Touch marker file

    whl_file = os.path.join(metadata_directory, whl_basename)
    with ZipFile(whl_file) as zipf:
        dist_info = _dist_info_files(zipf)
        zipf.extractall(path=metadata_directory, members=dist_info)
    return dist_info[0].split("/")[0]


def _find_already_built_wheel(metadata_directory):
    """Check for a wheel already built during the get_wheel_metadata hook."""
    if not metadata_directory:
        return None
    metadata_parent = os.path.dirname(metadata_directory)
    if not os.path.isfile(pjoin(metadata_parent, WHEEL_BUILT_MARKER)):
        return None

    whl_files = glob(os.path.join(metadata_parent, "*.whl"))
    if not whl_files:
        print("Found wheel built marker, but no .whl files")
        return None
    if len(whl_files) > 1:
        print(
            "Found multiple .whl files; unspecified behaviour. "
            "Will call build_wheel."
        )
        return None

    # Exactly one .whl file
    return whl_files[0]


def build_wheel(wheel_directory, config_settings, metadata_directory=None):
    """Invoke the mandatory build_wheel hook.

    If a wheel was already built in the
    prepare_metadata_for_build_wheel fallback, this
    will copy it rather than rebuilding the wheel.
    """
    prebuilt_whl = _find_already_built_wheel(metadata_directory)
    if prebuilt_whl:
        shutil.copy2(prebuilt_whl, wheel_directory)
        return os.path.basename(prebuilt_whl)

    return _build_backend().build_wheel(
        wheel_directory, config_settings, metadata_directory
    )


def build_editable(wheel_directory, config_settings, metadata_directory=None):
    """Invoke the optional build_editable hook.

    If a wheel was already built in the
    prepare_metadata_for_build_editable fallback, this
    will copy it rather than rebuilding the wheel.
    """
    backend = _build_backend()
    try:
        hook = backend.build_editable
    except AttributeError:
        raise HookMissing()
    else:
        prebuilt_whl = _find_already_built_wheel(metadata_directory)
        if prebuilt_whl:
            shutil.copy2(prebuilt_whl, wheel_directory)
            return os.path.basename(prebuilt_whl)

        return hook(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_sdist(config_settings):
    """Invoke the optional get_requires_for_build_wheel hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_sdist
    except AttributeError:
        return []
    else:
        return hook(config_settings)


class _DummyException(Exception):
    """Nothing should ever raise this exception"""


class GotUnsupportedOperation(Exception):
    """For internal use when backend raises UnsupportedOperation"""

    def __init__(self, traceback):
        self.traceback = traceback


def build_sdist(sdist_directory, config_settings):
    """Invoke the mandatory build_sdist hook."""
    backend = _build_backend()
    try:
        return backend.build_sdist(sdist_directory, config_settings)
    except getattr(backend, "UnsupportedOperation", _DummyException):
        raise GotUnsupportedOperation(traceback.format_exc())


HOOK_NAMES = {
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "build_wheel",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_editable",
    "build_editable",
    "get_requires_for_build_sdist",
    "build_sdist",
    "_supported_features",
}


def main():
    if len(sys.argv) < 3:
        sys.exit("Needs args: hook_name, control_dir")
    hook_name = sys.argv[1]
    control_dir = sys.argv[2]
    if hook_name not in HOOK_NAMES:
        sys.exit("Unknown hook: %s" % hook_name)

    # Remove the parent directory from sys.path to avoid polluting the backend
    # import namespace with this directory.
    here = os.path.dirname(__file__)
    if here in sys.path:
        sys.path.remove(here)

    hook = globals()[hook_name]

    hook_input = read_json(pjoin(control_dir, "input.json"))

    json_out = {"unsupported": False, "return_val": None}
    try:
        json_out["return_val"] = hook(**hook_input["kwargs"])
    except BackendUnavailable as e:
        json_out["no_backend"] = True
        json_out["traceback"] = e.traceback
        json_out["backend_error"] = e.message
    except GotUnsupportedOperation as e:
        json_out["unsupported"] = True
        json_out["traceback"] = e.traceback
    except HookMissing as e:
        json_out["hook_missing"] = True
        json_out["missing_hook_name"] = e.hook_name or hook_name

    write_json(json_out, pjoin(control_dir, "output.json"), indent=2)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\PIL\ImImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# IFUNC IM file handling for PIL
#
# history:
# 1995-09-01 fl   Created.
# 1997-01-03 fl   Save palette images
# 1997-01-08 fl   Added sequence support
# 1997-01-23 fl   Added P and RGB save support
# 1997-05-31 fl   Read floating point images
# 1997-06-22 fl   Save floating point images
# 1997-08-27 fl   Read and save 1-bit images
# 1998-06-25 fl   Added support for RGB+LUT images
# 1998-07-02 fl   Added support for YCC images
# 1998-07-15 fl   Renamed offset attribute to avoid name clash
# 1998-12-29 fl   Added I;16 support
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.7)
# 2003-09-26 fl   Added LA/PA support
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2001 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import os
import re
from typing import IO, Any

from . import Image, ImageFile, ImagePalette
from ._util import DeferredError

# --------------------------------------------------------------------
# Standard tags

COMMENT = "Comment"
DATE = "Date"
EQUIPMENT = "Digitalization equipment"
FRAMES = "File size (no of images)"
LUT = "Lut"
NAME = "Name"
SCALE = "Scale (x,y)"
SIZE = "Image size (x*y)"
MODE = "Image type"

TAGS = {
    COMMENT: 0,
    DATE: 0,
    EQUIPMENT: 0,
    FRAMES: 0,
    LUT: 0,
    NAME: 0,
    SCALE: 0,
    SIZE: 0,
    MODE: 0,
}

OPEN = {
    # ifunc93/p3cfunc formats
    "0 1 image": ("1", "1"),
    "L 1 image": ("1", "1"),
    "Greyscale image": ("L", "L"),
    "Grayscale image": ("L", "L"),
    "RGB image": ("RGB", "RGB;L"),
    "RLB image": ("RGB", "RLB"),
    "RYB image": ("RGB", "RLB"),
    "B1 image": ("1", "1"),
    "B2 image": ("P", "P;2"),
    "B4 image": ("P", "P;4"),
    "X 24 image": ("RGB", "RGB"),
    "L 32 S image": ("I", "I;32"),
    "L 32 F image": ("F", "F;32"),
    # old p3cfunc formats
    "RGB3 image": ("RGB", "RGB;T"),
    "RYB3 image": ("RGB", "RYB;T"),
    # extensions
    "LA image": ("LA", "LA;L"),
    "PA image": ("LA", "PA;L"),
    "RGBA image": ("RGBA", "RGBA;L"),
    "RGBX image": ("RGB", "RGBX;L"),
    "CMYK image": ("CMYK", "CMYK;L"),
    "YCC image": ("YCbCr", "YCbCr;L"),
}

# ifunc95 extensions
for i in ["8", "8S", "16", "16S", "32", "32F"]:
    OPEN[f"L {i} image"] = ("F", f"F;{i}")
    OPEN[f"L*{i} image"] = ("F", f"F;{i}")
for i in ["16", "16L", "16B"]:
    OPEN[f"L {i} image"] = (f"I;{i}", f"I;{i}")
    OPEN[f"L*{i} image"] = (f"I;{i}", f"I;{i}")
for i in ["32S"]:
    OPEN[f"L {i} image"] = ("I", f"I;{i}")
    OPEN[f"L*{i} image"] = ("I", f"I;{i}")
for j in range(2, 33):
    OPEN[f"L*{j} image"] = ("F", f"F;{j}")


# --------------------------------------------------------------------
# Read IM directory

split = re.compile(rb"^([A-Za-z][^:]*):[ \t]*(.*)[ \t]*$")


def number(s: Any) -> float:
    try:
        return int(s)
    except ValueError:
        return float(s)


##
# Image plugin for the IFUNC IM file format.


class ImImageFile(ImageFile.ImageFile):
    format = "IM"
    format_description = "IFUNC Image Memory"
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        # Quick rejection: if there's not an LF among the first
        # 100 bytes, this is (probably) not a text header.

        if b"\n" not in self.fp.read(100):
            msg = "not an IM file"
            raise SyntaxError(msg)
        self.fp.seek(0)

        n = 0

        # Default values
        self.info[MODE] = "L"
        self.info[SIZE] = (512, 512)
        self.info[FRAMES] = 1

        self.rawmode = "L"

        while True:
            s = self.fp.read(1)

            # Some versions of IFUNC uses \n\r instead of \r\n...
            if s == b"\r":
                continue

            if not s or s == b"\0" or s == b"\x1a":
                break

            # FIXME: this may read whole file if not a text file
            s = s + self.fp.readline()

            if len(s) > 100:
                msg = "not an IM file"
                raise SyntaxError(msg)

            if s.endswith(b"\r\n"):
                s = s[:-2]
            elif s.endswith(b"\n"):
                s = s[:-1]

            try:
                m = split.match(s)
            except re.error as e:
                msg = "not an IM file"
                raise SyntaxError(msg) from e

            if m:
                k, v = m.group(1, 2)

                # Don't know if this is the correct encoding,
                # but a decent guess (I guess)
                k = k.decode("latin-1", "replace")
                v = v.decode("latin-1", "replace")

                # Convert value as appropriate
                if k in [FRAMES, SCALE, SIZE]:
                    v = v.replace("*", ",")
                    v = tuple(map(number, v.split(",")))
                    if len(v) == 1:
                        v = v[0]
                elif k == MODE and v in OPEN:
                    v, self.rawmode = OPEN[v]

                # Add to dictionary. Note that COMMENT tags are
                # combined into a list of strings.
                if k == COMMENT:
                    if k in self.info:
                        self.info[k].append(v)
                    else:
                        self.info[k] = [v]
                else:
                    self.info[k] = v

                if k in TAGS:
                    n += 1

            else:
                msg = f"Syntax error in IM header: {s.decode('ascii', 'replace')}"
                raise SyntaxError(msg)

        if not n:
            msg = "Not an IM file"
            raise SyntaxError(msg)

        # Basic attributes
        self._size = self.info[SIZE]
        self._mode = self.info[MODE]

        # Skip forward to start of image data
        while s and not s.startswith(b"\x1a"):
            s = self.fp.read(1)
        if not s:
            msg = "File truncated"
            raise SyntaxError(msg)

        if LUT in self.info:
            # convert lookup table to palette or lut attribute
            palette = self.fp.read(768)
            greyscale = 1  # greyscale palette
            linear = 1  # linear greyscale palette
            for i in range(256):
                if palette[i] == palette[i + 256] == palette[i + 512]:
                    if palette[i] != i:
                        linear = 0
                else:
                    greyscale = 0
            if self.mode in ["L", "LA", "P", "PA"]:
                if greyscale:
                    if not linear:
                        self.lut = list(palette[:256])
                else:
                    if self.mode in ["L", "P"]:
                        self._mode = self.rawmode = "P"
                    elif self.mode in ["LA", "PA"]:
                        self._mode = "PA"
                        self.rawmode = "PA;L"
                    self.palette = ImagePalette.raw("RGB;L", palette)
            elif self.mode == "RGB":
                if not greyscale or not linear:
                    self.lut = list(palette)

        self.frame = 0

        self.__offset = offs = self.fp.tell()

        self._fp = self.fp  # FIXME: hack

        if self.rawmode.startswith("F;"):
            # ifunc95 formats
            try:
                # use bit decoder (if necessary)
                bits = int(self.rawmode[2:])
                if bits not in [8, 16, 32]:
                    self.tile = [
                        ImageFile._Tile(
                            "bit", (0, 0) + self.size, offs, (bits, 8, 3, 0, -1)
                        )
                    ]
                    return
            except ValueError:
                pass

        if self.rawmode in ["RGB;T", "RYB;T"]:
            # Old LabEye/3PC files.  Would be very surprised if anyone
            # ever stumbled upon such a file ;-)
            size = self.size[0] * self.size[1]
            self.tile = [
                ImageFile._Tile("raw", (0, 0) + self.size, offs, ("G", 0, -1)),
                ImageFile._Tile("raw", (0, 0) + self.size, offs + size, ("R", 0, -1)),
                ImageFile._Tile(
                    "raw", (0, 0) + self.size, offs + 2 * size, ("B", 0, -1)
                ),
            ]
        else:
            # LabEye/IFUNC files
            self.tile = [
                ImageFile._Tile("raw", (0, 0) + self.size, offs, (self.rawmode, 0, -1))
            ]

    @property
    def n_frames(self) -> int:
        return self.info[FRAMES]

    @property
    def is_animated(self) -> bool:
        return self.info[FRAMES] > 1

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex

        self.frame = frame

        if self.mode == "1":
            bits = 1
        else:
            bits = 8 * len(self.mode)

        size = ((self.size[0] * bits + 7) // 8) * self.size[1]
        offs = self.__offset + frame * size

        self.fp = self._fp

        self.tile = [
            ImageFile._Tile("raw", (0, 0) + self.size, offs, (self.rawmode, 0, -1))
        ]

    def tell(self) -> int:
        return self.frame


#
# --------------------------------------------------------------------
# Save IM files


SAVE = {
    # mode: (im type, raw mode)
    "1": ("0 1", "1"),
    "L": ("Greyscale", "L"),
    "LA": ("LA", "LA;L"),
    "P": ("Greyscale", "P"),
    "PA": ("LA", "PA;L"),
    "I": ("L 32S", "I;32S"),
    "I;16": ("L 16", "I;16"),
    "I;16L": ("L 16L", "I;16L"),
    "I;16B": ("L 16B", "I;16B"),
    "F": ("L 32F", "F;32F"),
    "RGB": ("RGB", "RGB;L"),
    "RGBA": ("RGBA", "RGBA;L"),
    "RGBX": ("RGBX", "RGBX;L"),
    "CMYK": ("CMYK", "CMYK;L"),
    "YCbCr": ("YCC", "YCbCr;L"),
}


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    try:
        image_type, rawmode = SAVE[im.mode]
    except KeyError as e:
        msg = f"Cannot save {im.mode} images as IM"
        raise ValueError(msg) from e

    frames = im.encoderinfo.get("frames", 1)

    fp.write(f"Image type: {image_type} image\r\n".encode("ascii"))
    if filename:
        # Each line must be 100 characters or less,
        # or: SyntaxError("not an IM file")
        # 8 characters are used for "Name: " and "\r\n"
        # Keep just the filename, ditch the potentially overlong path
        if isinstance(filename, bytes):
            filename = filename.decode("ascii")
        name, ext = os.path.splitext(os.path.basename(filename))
        name = "".join([name[: 92 - len(ext)], ext])

        fp.write(f"Name: {name}\r\n".encode("ascii"))
    fp.write(f"Image size (x*y): {im.size[0]}*{im.size[1]}\r\n".encode("ascii"))
    fp.write(f"File size (no of images): {frames}\r\n".encode("ascii"))
    if im.mode in ["P", "PA"]:
        fp.write(b"Lut: 1\r\n")
    fp.write(b"\000" * (511 - fp.tell()) + b"\032")
    if im.mode in ["P", "PA"]:
        im_palette = im.im.getpalette("RGB", "RGB;L")
        colors = len(im_palette) // 3
        palette = b""
        for i in range(3):
            palette += im_palette[colors * i : colors * (i + 1)]
            palette += b"\x00" * (256 - colors)
        fp.write(palette)  # 768 bytes
    ImageFile._save(
        im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 0, (rawmode, 0, -1))]
    )


#
# --------------------------------------------------------------------
# Registry


Image.register_open(ImImageFile.format, ImImageFile)
Image.register_save(ImImageFile.format, _save)

Image.register_extension(ImImageFile.format, ".im")

# === NexusCore/openenv\Lib\site-packages\yaml\representer.py ===

__all__ = ['BaseRepresenter', 'SafeRepresenter', 'Representer',
    'RepresenterError']

from .error import *
from .nodes import *

import datetime, copyreg, types, base64, collections

class RepresenterError(YAMLError):
    pass

class BaseRepresenter:

    yaml_representers = {}
    yaml_multi_representers = {}

    def __init__(self, default_style=None, default_flow_style=False, sort_keys=True):
        self.default_style = default_style
        self.sort_keys = sort_keys
        self.default_flow_style = default_flow_style
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent(self, data):
        node = self.represent_data(data)
        self.serialize(node)
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent_data(self, data):
        if self.ignore_aliases(data):
            self.alias_key = None
        else:
            self.alias_key = id(data)
        if self.alias_key is not None:
            if self.alias_key in self.represented_objects:
                node = self.represented_objects[self.alias_key]
                #if node is None:
                #    raise RepresenterError("recursive objects are not allowed: %r" % data)
                return node
            #self.represented_objects[alias_key] = None
            self.object_keeper.append(data)
        data_types = type(data).__mro__
        if data_types[0] in self.yaml_representers:
            node = self.yaml_representers[data_types[0]](self, data)
        else:
            for data_type in data_types:
                if data_type in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[data_type](self, data)
                    break
            else:
                if None in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[None](self, data)
                elif None in self.yaml_representers:
                    node = self.yaml_representers[None](self, data)
                else:
                    node = ScalarNode(None, str(data))
        #if alias_key is not None:
        #    self.represented_objects[alias_key] = node
        return node

    @classmethod
    def add_representer(cls, data_type, representer):
        if not 'yaml_representers' in cls.__dict__:
            cls.yaml_representers = cls.yaml_representers.copy()
        cls.yaml_representers[data_type] = representer

    @classmethod
    def add_multi_representer(cls, data_type, representer):
        if not 'yaml_multi_representers' in cls.__dict__:
            cls.yaml_multi_representers = cls.yaml_multi_representers.copy()
        cls.yaml_multi_representers[data_type] = representer

    def represent_scalar(self, tag, value, style=None):
        if style is None:
            style = self.default_style
        node = ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    def represent_sequence(self, tag, sequence, flow_style=None):
        value = []
        node = SequenceNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        for item in sequence:
            node_item = self.represent_data(item)
            if not (isinstance(node_item, ScalarNode) and not node_item.style):
                best_style = False
            value.append(node_item)
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = list(mapping.items())
            if self.sort_keys:
                try:
                    mapping = sorted(mapping)
                except TypeError:
                    pass
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def ignore_aliases(self, data):
        return False

class SafeRepresenter(BaseRepresenter):

    def ignore_aliases(self, data):
        if data is None:
            return True
        if isinstance(data, tuple) and data == ():
            return True
        if isinstance(data, (str, bytes, bool, int, float)):
            return True

    def represent_none(self, data):
        return self.represent_scalar('tag:yaml.org,2002:null', 'null')

    def represent_str(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data)

    def represent_binary(self, data):
        if hasattr(base64, 'encodebytes'):
            data = base64.encodebytes(data).decode('ascii')
        else:
            data = base64.encodestring(data).decode('ascii')
        return self.represent_scalar('tag:yaml.org,2002:binary', data, style='|')

    def represent_bool(self, data):
        if data:
            value = 'true'
        else:
            value = 'false'
        return self.represent_scalar('tag:yaml.org,2002:bool', value)

    def represent_int(self, data):
        return self.represent_scalar('tag:yaml.org,2002:int', str(data))

    inf_value = 1e300
    while repr(inf_value) != repr(inf_value*inf_value):
        inf_value *= inf_value

    def represent_float(self, data):
        if data != data or (data == 0.0 and data == 1.0):
            value = '.nan'
        elif data == self.inf_value:
            value = '.inf'
        elif data == -self.inf_value:
            value = '-.inf'
        else:
            value = repr(data).lower()
            # Note that in some cases `repr(data)` represents a float number
            # without the decimal parts.  For instance:
            #   >>> repr(1e17)
            #   '1e17'
            # Unfortunately, this is not a valid float representation according
            # to the definition of the `!!float` tag.  We fix this by adding
            # '.0' before the 'e' symbol.
            if '.' not in value and 'e' in value:
                value = value.replace('e', '.0e', 1)
        return self.represent_scalar('tag:yaml.org,2002:float', value)

    def represent_list(self, data):
        #pairs = (len(data) > 0 and isinstance(data, list))
        #if pairs:
        #    for item in data:
        #        if not isinstance(item, tuple) or len(item) != 2:
        #            pairs = False
        #            break
        #if not pairs:
            return self.represent_sequence('tag:yaml.org,2002:seq', data)
        #value = []
        #for item_key, item_value in data:
        #    value.append(self.represent_mapping(u'tag:yaml.org,2002:map',
        #        [(item_key, item_value)]))
        #return SequenceNode(u'tag:yaml.org,2002:pairs', value)

    def represent_dict(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data)

    def represent_set(self, data):
        value = {}
        for key in data:
            value[key] = None
        return self.represent_mapping('tag:yaml.org,2002:set', value)

    def represent_date(self, data):
        value = data.isoformat()
        return self.represent_scalar('tag:yaml.org,2002:timestamp', value)

    def represent_datetime(self, data):
        value = data.isoformat(' ')
        return self.represent_scalar('tag:yaml.org,2002:timestamp', value)

    def represent_yaml_object(self, tag, data, cls, flow_style=None):
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__.copy()
        return self.represent_mapping(tag, state, flow_style=flow_style)

    def represent_undefined(self, data):
        raise RepresenterError("cannot represent an object", data)

SafeRepresenter.add_representer(type(None),
        SafeRepresenter.represent_none)

SafeRepresenter.add_representer(str,
        SafeRepresenter.represent_str)

SafeRepresenter.add_representer(bytes,
        SafeRepresenter.represent_binary)

SafeRepresenter.add_representer(bool,
        SafeRepresenter.represent_bool)

SafeRepresenter.add_representer(int,
        SafeRepresenter.represent_int)

SafeRepresenter.add_representer(float,
        SafeRepresenter.represent_float)

SafeRepresenter.add_representer(list,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(tuple,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(dict,
        SafeRepresenter.represent_dict)

SafeRepresenter.add_representer(set,
        SafeRepresenter.represent_set)

SafeRepresenter.add_representer(datetime.date,
        SafeRepresenter.represent_date)

SafeRepresenter.add_representer(datetime.datetime,
        SafeRepresenter.represent_datetime)

SafeRepresenter.add_representer(None,
        SafeRepresenter.represent_undefined)

class Representer(SafeRepresenter):

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = '%r' % data.real
        elif data.real == 0.0:
            data = '%rj' % data.imag
        elif data.imag > 0:
            data = '%r+%rj' % (data.real, data.imag)
        else:
            data = '%r%rj' % (data.real, data.imag)
        return self.represent_scalar('tag:yaml.org,2002:python/complex', data)

    def represent_tuple(self, data):
        return self.represent_sequence('tag:yaml.org,2002:python/tuple', data)

    def represent_name(self, data):
        name = '%s.%s' % (data.__module__, data.__name__)
        return self.represent_scalar('tag:yaml.org,2002:python/name:'+name, '')

    def represent_module(self, data):
        return self.represent_scalar(
                'tag:yaml.org,2002:python/module:'+data.__name__, '')

    def represent_object(self, data):
        # We use __reduce__ API to save the data. data.__reduce__ returns
        # a tuple of length 2-5:
        #   (function, args, state, listitems, dictitems)

        # For reconstructing, we calls function(*args), then set its state,
        # listitems, and dictitems if they are not None.

        # A special case is when function.__name__ == '__newobj__'. In this
        # case we create the object with args[0].__new__(*args).

        # Another special case is when __reduce__ returns a string - we don't
        # support it.

        # We produce a !!python/object, !!python/object/new or
        # !!python/object/apply node.

        cls = type(data)
        if cls in copyreg.dispatch_table:
            reduce = copyreg.dispatch_table[cls](data)
        elif hasattr(data, '__reduce_ex__'):
            reduce = data.__reduce_ex__(2)
        elif hasattr(data, '__reduce__'):
            reduce = data.__reduce__()
        else:
            raise RepresenterError("cannot represent an object", data)
        reduce = (list(reduce)+[None]*5)[:5]
        function, args, state, listitems, dictitems = reduce
        args = list(args)
        if state is None:
            state = {}
        if listitems is not None:
            listitems = list(listitems)
        if dictitems is not None:
            dictitems = dict(dictitems)
        if function.__name__ == '__newobj__':
            function = args[0]
            args = args[1:]
            tag = 'tag:yaml.org,2002:python/object/new:'
            newobj = True
        else:
            tag = 'tag:yaml.org,2002:python/object/apply:'
            newobj = False
        function_name = '%s.%s' % (function.__module__, function.__name__)
        if not args and not listitems and not dictitems \
                and isinstance(state, dict) and newobj:
            return self.represent_mapping(
                    'tag:yaml.org,2002:python/object:'+function_name, state)
        if not listitems and not dictitems  \
                and isinstance(state, dict) and not state:
            return self.represent_sequence(tag+function_name, args)
        value = {}
        if args:
            value['args'] = args
        if state or not isinstance(state, dict):
            value['state'] = state
        if listitems:
            value['listitems'] = listitems
        if dictitems:
            value['dictitems'] = dictitems
        return self.represent_mapping(tag+function_name, value)

    def represent_ordered_dict(self, data):
        # Provide uniform representation across different Python versions.
        data_type = type(data)
        tag = 'tag:yaml.org,2002:python/object/apply:%s.%s' \
                % (data_type.__module__, data_type.__name__)
        items = [[key, value] for key, value in data.items()]
        return self.represent_sequence(tag, [items])

Representer.add_representer(complex,
        Representer.represent_complex)

Representer.add_representer(tuple,
        Representer.represent_tuple)

Representer.add_multi_representer(type,
        Representer.represent_name)

Representer.add_representer(collections.OrderedDict,
        Representer.represent_ordered_dict)

Representer.add_representer(types.FunctionType,
        Representer.represent_name)

Representer.add_representer(types.BuiltinFunctionType,
        Representer.represent_name)

Representer.add_representer(types.ModuleType,
        Representer.represent_module)

Representer.add_multi_representer(object,
        Representer.represent_object)


# === NexusCore/openenv\Lib\site-packages\litellm\integrations\_types\open_inference.py ===
from enum import Enum


class SpanAttributes:
    OUTPUT_VALUE = "output.value"
    OUTPUT_MIME_TYPE = "output.mime_type"
    """
    The type of output.value. If unspecified, the type is plain text by default.
    If type is JSON, the value is a string representing a JSON object.
    """
    INPUT_VALUE = "input.value"
    INPUT_MIME_TYPE = "input.mime_type"
    """
    The type of input.value. If unspecified, the type is plain text by default.
    If type is JSON, the value is a string representing a JSON object.
    """

    EMBEDDING_EMBEDDINGS = "embedding.embeddings"
    """
    A list of objects containing embedding data, including the vector and represented piece of text.
    """
    EMBEDDING_MODEL_NAME = "embedding.model_name"
    """
    The name of the embedding model.
    """

    LLM_FUNCTION_CALL = "llm.function_call"
    """
    For models and APIs that support function calling. Records attributes such as the function
    name and arguments to the called function.
    """
    LLM_INVOCATION_PARAMETERS = "llm.invocation_parameters"
    """
    Invocation parameters passed to the LLM or API, such as the model name, temperature, etc.
    """
    LLM_INPUT_MESSAGES = "llm.input_messages"
    """
    Messages provided to a chat API.
    """
    LLM_OUTPUT_MESSAGES = "llm.output_messages"
    """
    Messages received from a chat API.
    """
    LLM_MODEL_NAME = "llm.model_name"
    """
    The name of the model being used.
    """
    LLM_PROVIDER = "llm.provider"
    """
    The provider of the model, such as OpenAI, Azure, Google, etc.
    """
    LLM_SYSTEM = "llm.system"
    """
    The AI product as identified by the client or server
    """
    LLM_PROMPTS = "llm.prompts"
    """
    Prompts provided to a completions API.
    """
    LLM_PROMPT_TEMPLATE = "llm.prompt_template.template"
    """
    The prompt template as a Python f-string.
    """
    LLM_PROMPT_TEMPLATE_VARIABLES = "llm.prompt_template.variables"
    """
    A list of input variables to the prompt template.
    """
    LLM_PROMPT_TEMPLATE_VERSION = "llm.prompt_template.version"
    """
    The version of the prompt template being used.
    """
    LLM_TOKEN_COUNT_PROMPT = "llm.token_count.prompt"
    """
    Number of tokens in the prompt.
    """
    LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_WRITE = "llm.token_count.prompt_details.cache_write"
    """
    Number of tokens in the prompt that were written to cache.
    """
    LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ = "llm.token_count.prompt_details.cache_read"
    """
    Number of tokens in the prompt that were read from cache.
    """
    LLM_TOKEN_COUNT_PROMPT_DETAILS_AUDIO = "llm.token_count.prompt_details.audio"
    """
    The number of audio input tokens presented in the prompt
    """
    LLM_TOKEN_COUNT_COMPLETION = "llm.token_count.completion"
    """
    Number of tokens in the completion.
    """
    LLM_TOKEN_COUNT_COMPLETION_DETAILS_REASONING = "llm.token_count.completion_details.reasoning"
    """
    Number of tokens used for reasoning steps in the completion.
    """
    LLM_TOKEN_COUNT_COMPLETION_DETAILS_AUDIO = "llm.token_count.completion_details.audio"
    """
    The number of audio input tokens generated by the model
    """
    LLM_TOKEN_COUNT_TOTAL = "llm.token_count.total"
    """
    Total number of tokens, including both prompt and completion.
    """

    LLM_TOOLS = "llm.tools"
    """
    List of tools that are advertised to the LLM to be able to call
    """

    TOOL_NAME = "tool.name"
    """
    Name of the tool being used.
    """
    TOOL_DESCRIPTION = "tool.description"
    """
    Description of the tool's purpose, typically used to select the tool.
    """
    TOOL_PARAMETERS = "tool.parameters"
    """
    Parameters of the tool represented a dictionary JSON string, e.g.
    see https://platform.openai.com/docs/guides/gpt/function-calling
    """

    RETRIEVAL_DOCUMENTS = "retrieval.documents"

    METADATA = "metadata"
    """
    Metadata attributes are used to store user-defined key-value pairs.
    For example, LangChain uses metadata to store user-defined attributes for a chain.
    """

    TAG_TAGS = "tag.tags"
    """
    Custom categorical tags for the span.
    """

    OPENINFERENCE_SPAN_KIND = "openinference.span.kind"

    SESSION_ID = "session.id"
    """
    The id of the session
    """
    USER_ID = "user.id"
    """
    The id of the user
    """

    PROMPT_VENDOR = "prompt.vendor"
    """
    The vendor or origin of the prompt, e.g. a prompt library, a specialized service, etc.
    """
    PROMPT_ID = "prompt.id"
    """
    A vendor-specific id used to locate the prompt.
    """
    PROMPT_URL = "prompt.url"
    """
    A vendor-specific url used to locate the prompt.
    """


class MessageAttributes:
    """
    Attributes for a message sent to or from an LLM
    """

    MESSAGE_ROLE = "message.role"
    """
    The role of the message, such as "user", "agent", "function".
    """
    MESSAGE_CONTENT = "message.content"
    """
    The content of the message to or from the llm, must be a string.
    """
    MESSAGE_CONTENTS = "message.contents"
    """
    The message contents to the llm, it is an array of
    `message_content` prefixed attributes.
    """
    MESSAGE_NAME = "message.name"
    """
    The name of the message, often used to identify the function
    that was used to generate the message.
    """
    MESSAGE_TOOL_CALLS = "message.tool_calls"
    """
    The tool calls generated by the model, such as function calls.
    """
    MESSAGE_FUNCTION_CALL_NAME = "message.function_call_name"
    """
    The function name that is a part of the message list.
    This is populated for role 'function' or 'agent' as a mechanism to identify
    the function that was called during the execution of a tool.
    """
    MESSAGE_FUNCTION_CALL_ARGUMENTS_JSON = "message.function_call_arguments_json"
    """
    The JSON string representing the arguments passed to the function
    during a function call.
    """
    MESSAGE_TOOL_CALL_ID = "message.tool_call_id"
    """
    The id of the tool call.
    """


class MessageContentAttributes:
    """
    Attributes for the contents of user messages sent to an LLM.
    """

    MESSAGE_CONTENT_TYPE = "message_content.type"
    """
    The type of the content, such as "text" or "image".
    """
    MESSAGE_CONTENT_TEXT = "message_content.text"
    """
    The text content of the message, if the type is "text".
    """
    MESSAGE_CONTENT_IMAGE = "message_content.image"
    """
    The image content of the message, if the type is "image".
    An image can be made available to the model by passing a link to
    the image or by passing the base64 encoded image directly in the
    request.
    """


class ImageAttributes:
    """
    Attributes for images
    """

    IMAGE_URL = "image.url"
    """
    An http or base64 image url
    """


class AudioAttributes:
    """
    Attributes for audio
    """

    AUDIO_URL = "audio.url"
    """
    The url to an audio file
    """
    AUDIO_MIME_TYPE = "audio.mime_type"
    """
    The mime type of the audio file
    """
    AUDIO_TRANSCRIPT = "audio.transcript"
    """
    The transcript of the audio file
    """


class DocumentAttributes:
    """
    Attributes for a document.
    """

    DOCUMENT_ID = "document.id"
    """
    The id of the document.
    """
    DOCUMENT_SCORE = "document.score"
    """
    The score of the document
    """
    DOCUMENT_CONTENT = "document.content"
    """
    The content of the document.
    """
    DOCUMENT_METADATA = "document.metadata"
    """
    The metadata of the document represented as a dictionary
    JSON string, e.g. `"{ 'title': 'foo' }"`
    """


class RerankerAttributes:
    """
    Attributes for a reranker
    """

    RERANKER_INPUT_DOCUMENTS = "reranker.input_documents"
    """
    List of documents as input to the reranker
    """
    RERANKER_OUTPUT_DOCUMENTS = "reranker.output_documents"
    """
    List of documents as output from the reranker
    """
    RERANKER_QUERY = "reranker.query"
    """
    Query string for the reranker
    """
    RERANKER_MODEL_NAME = "reranker.model_name"
    """
    Model name of the reranker
    """
    RERANKER_TOP_K = "reranker.top_k"
    """
    Top K parameter of the reranker
    """


class EmbeddingAttributes:
    """
    Attributes for an embedding
    """

    EMBEDDING_TEXT = "embedding.text"
    """
    The text represented by the embedding.
    """
    EMBEDDING_VECTOR = "embedding.vector"
    """
    The embedding vector.
    """


class ToolCallAttributes:
    """
    Attributes for a tool call
    """

    TOOL_CALL_ID = "tool_call.id"
    """
    The id of the tool call.
    """
    TOOL_CALL_FUNCTION_NAME = "tool_call.function.name"
    """
    The name of function that is being called during a tool call.
    """
    TOOL_CALL_FUNCTION_ARGUMENTS_JSON = "tool_call.function.arguments"
    """
    The JSON string representing the arguments passed to the function
    during a tool call.
    """


class ToolAttributes:
    """
    Attributes for a tools
    """

    TOOL_JSON_SCHEMA = "tool.json_schema"
    """
    The json schema of a tool input, It is RECOMMENDED that this be in the
    OpenAI tool calling format: https://platform.openai.com/docs/assistants/tools
    """


class OpenInferenceSpanKindValues(Enum):
    TOOL = "TOOL"
    CHAIN = "CHAIN"
    LLM = "LLM"
    RETRIEVER = "RETRIEVER"
    EMBEDDING = "EMBEDDING"
    AGENT = "AGENT"
    RERANKER = "RERANKER"
    UNKNOWN = "UNKNOWN"
    GUARDRAIL = "GUARDRAIL"
    EVALUATOR = "EVALUATOR"


class OpenInferenceMimeTypeValues(Enum):
    TEXT = "text/plain"
    JSON = "application/json"


class OpenInferenceLLMSystemValues(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    MISTRALAI = "mistralai"
    VERTEXAI = "vertexai"


class OpenInferenceLLMProviderValues(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    MISTRALAI = "mistralai"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\paice.py ===
# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Lauri Hallila <laurihallila@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""Counts Paice's performance statistics for evaluating stemming algorithms.

What is required:
 - A dictionary of words grouped by their real lemmas
 - A dictionary of words grouped by stems from a stemming algorithm

When these are given, Understemming Index (UI), Overstemming Index (OI),
Stemming Weight (SW) and Error-rate relative to truncation (ERRT) are counted.

References:
Chris D. Paice (1994). An evaluation method for stemming algorithms.
In Proceedings of SIGIR, 42--50.
"""

from math import sqrt


def get_words_from_dictionary(lemmas):
    """
    Get original set of words used for analysis.

    :param lemmas: A dictionary where keys are lemmas and values are sets
        or lists of words corresponding to that lemma.
    :type lemmas: dict(str): list(str)
    :return: Set of words that exist as values in the dictionary
    :rtype: set(str)
    """
    words = set()
    for lemma in lemmas:
        words.update(set(lemmas[lemma]))
    return words


def _truncate(words, cutlength):
    """Group words by stems defined by truncating them at given length.

    :param words: Set of words used for analysis
    :param cutlength: Words are stemmed by cutting at this length.
    :type words: set(str) or list(str)
    :type cutlength: int
    :return: Dictionary where keys are stems and values are sets of words
    corresponding to that stem.
    :rtype: dict(str): set(str)
    """
    stems = {}
    for word in words:
        stem = word[:cutlength]
        try:
            stems[stem].update([word])
        except KeyError:
            stems[stem] = {word}
    return stems


# Reference: https://en.wikipedia.org/wiki/Line-line_intersection
def _count_intersection(l1, l2):
    """Count intersection between two line segments defined by coordinate pairs.

    :param l1: Tuple of two coordinate pairs defining the first line segment
    :param l2: Tuple of two coordinate pairs defining the second line segment
    :type l1: tuple(float, float)
    :type l2: tuple(float, float)
    :return: Coordinates of the intersection
    :rtype: tuple(float, float)
    """
    x1, y1 = l1[0]
    x2, y2 = l1[1]
    x3, y3 = l2[0]
    x4, y4 = l2[1]

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if denominator == 0.0:  # lines are parallel
        if x1 == x2 == x3 == x4 == 0.0:
            # When lines are parallel, they must be on the y-axis.
            # We can ignore x-axis because we stop counting the
            # truncation line when we get there.
            # There are no other options as UI (x-axis) grows and
            # OI (y-axis) diminishes when we go along the truncation line.
            return (0.0, y4)

    x = (
        (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / denominator
    y = (
        (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / denominator
    return (x, y)


def _get_derivative(coordinates):
    """Get derivative of the line from (0,0) to given coordinates.

    :param coordinates: A coordinate pair
    :type coordinates: tuple(float, float)
    :return: Derivative; inf if x is zero
    :rtype: float
    """
    try:
        return coordinates[1] / coordinates[0]
    except ZeroDivisionError:
        return float("inf")


def _calculate_cut(lemmawords, stems):
    """Count understemmed and overstemmed pairs for (lemma, stem) pair with common words.

    :param lemmawords: Set or list of words corresponding to certain lemma.
    :param stems: A dictionary where keys are stems and values are sets
    or lists of words corresponding to that stem.
    :type lemmawords: set(str) or list(str)
    :type stems: dict(str): set(str)
    :return: Amount of understemmed and overstemmed pairs contributed by words
    existing in both lemmawords and stems.
    :rtype: tuple(float, float)
    """
    umt, wmt = 0.0, 0.0
    for stem in stems:
        cut = set(lemmawords) & set(stems[stem])
        if cut:
            cutcount = len(cut)
            stemcount = len(stems[stem])
            # Unachieved merge total
            umt += cutcount * (len(lemmawords) - cutcount)
            # Wrongly merged total
            wmt += cutcount * (stemcount - cutcount)
    return (umt, wmt)


def _calculate(lemmas, stems):
    """Calculate actual and maximum possible amounts of understemmed and overstemmed word pairs.

    :param lemmas: A dictionary where keys are lemmas and values are sets
    or lists of words corresponding to that lemma.
    :param stems: A dictionary where keys are stems and values are sets
    or lists of words corresponding to that stem.
    :type lemmas: dict(str): list(str)
    :type stems: dict(str): set(str)
    :return: Global unachieved merge total (gumt),
    global desired merge total (gdmt),
    global wrongly merged total (gwmt) and
    global desired non-merge total (gdnt).
    :rtype: tuple(float, float, float, float)
    """

    n = sum(len(lemmas[word]) for word in lemmas)

    gdmt, gdnt, gumt, gwmt = (0.0, 0.0, 0.0, 0.0)

    for lemma in lemmas:
        lemmacount = len(lemmas[lemma])

        # Desired merge total
        gdmt += lemmacount * (lemmacount - 1)

        # Desired non-merge total
        gdnt += lemmacount * (n - lemmacount)

        # For each (lemma, stem) pair with common words, count how many
        # pairs are understemmed and overstemmed.
        umt, wmt = _calculate_cut(lemmas[lemma], stems)

        # Add to total undesired and wrongly-merged totals
        gumt += umt
        gwmt += wmt

    # Each object is counted twice, so divide by two
    return (gumt / 2, gdmt / 2, gwmt / 2, gdnt / 2)


def _indexes(gumt, gdmt, gwmt, gdnt):
    """Count Understemming Index (UI), Overstemming Index (OI) and Stemming Weight (SW).

    :param gumt, gdmt, gwmt, gdnt: Global unachieved merge total (gumt),
    global desired merge total (gdmt),
    global wrongly merged total (gwmt) and
    global desired non-merge total (gdnt).
    :type gumt, gdmt, gwmt, gdnt: float
    :return: Understemming Index (UI),
    Overstemming Index (OI) and
    Stemming Weight (SW).
    :rtype: tuple(float, float, float)
    """
    # Calculate Understemming Index (UI),
    # Overstemming Index (OI) and Stemming Weight (SW)
    try:
        ui = gumt / gdmt
    except ZeroDivisionError:
        # If GDMT (max merge total) is 0, define UI as 0
        ui = 0.0
    try:
        oi = gwmt / gdnt
    except ZeroDivisionError:
        # IF GDNT (max non-merge total) is 0, define OI as 0
        oi = 0.0
    try:
        sw = oi / ui
    except ZeroDivisionError:
        if oi == 0.0:
            # OI and UI are 0, define SW as 'not a number'
            sw = float("nan")
        else:
            # UI is 0, define SW as infinity
            sw = float("inf")
    return (ui, oi, sw)


class Paice:
    """Class for storing lemmas, stems and evaluation metrics."""

    def __init__(self, lemmas, stems):
        """
        :param lemmas: A dictionary where keys are lemmas and values are sets
            or lists of words corresponding to that lemma.
        :param stems: A dictionary where keys are stems and values are sets
            or lists of words corresponding to that stem.
        :type lemmas: dict(str): list(str)
        :type stems: dict(str): set(str)
        """
        self.lemmas = lemmas
        self.stems = stems
        self.coords = []
        self.gumt, self.gdmt, self.gwmt, self.gdnt = (None, None, None, None)
        self.ui, self.oi, self.sw = (None, None, None)
        self.errt = None
        self.update()

    def __str__(self):
        text = ["Global Unachieved Merge Total (GUMT): %s\n" % self.gumt]
        text.append("Global Desired Merge Total (GDMT): %s\n" % self.gdmt)
        text.append("Global Wrongly-Merged Total (GWMT): %s\n" % self.gwmt)
        text.append("Global Desired Non-merge Total (GDNT): %s\n" % self.gdnt)
        text.append("Understemming Index (GUMT / GDMT): %s\n" % self.ui)
        text.append("Overstemming Index (GWMT / GDNT): %s\n" % self.oi)
        text.append("Stemming Weight (OI / UI): %s\n" % self.sw)
        text.append("Error-Rate Relative to Truncation (ERRT): %s\r\n" % self.errt)
        coordinates = " ".join(["(%s, %s)" % item for item in self.coords])
        text.append("Truncation line: %s" % coordinates)
        return "".join(text)

    def _get_truncation_indexes(self, words, cutlength):
        """Count (UI, OI) when stemming is done by truncating words at \'cutlength\'.

        :param words: Words used for the analysis
        :param cutlength: Words are stemmed by cutting them at this length
        :type words: set(str) or list(str)
        :type cutlength: int
        :return: Understemming and overstemming indexes
        :rtype: tuple(int, int)
        """

        truncated = _truncate(words, cutlength)
        gumt, gdmt, gwmt, gdnt = _calculate(self.lemmas, truncated)
        ui, oi = _indexes(gumt, gdmt, gwmt, gdnt)[:2]
        return (ui, oi)

    def _get_truncation_coordinates(self, cutlength=0):
        """Count (UI, OI) pairs for truncation points until we find the segment where (ui, oi) crosses the truncation line.

        :param cutlength: Optional parameter to start counting from (ui, oi)
        coordinates gotten by stemming at this length. Useful for speeding up
        the calculations when you know the approximate location of the
        intersection.
        :type cutlength: int
        :return: List of coordinate pairs that define the truncation line
        :rtype: list(tuple(float, float))
        """
        words = get_words_from_dictionary(self.lemmas)
        maxlength = max(len(word) for word in words)

        # Truncate words from different points until (0, 0) - (ui, oi) segment crosses the truncation line
        coords = []
        while cutlength <= maxlength:
            # Get (UI, OI) pair of current truncation point
            pair = self._get_truncation_indexes(words, cutlength)

            # Store only new coordinates so we'll have an actual
            # line segment when counting the intersection point
            if pair not in coords:
                coords.append(pair)
            if pair == (0.0, 0.0):
                # Stop counting if truncation line goes through origo;
                # length from origo to truncation line is 0
                return coords
            if len(coords) >= 2 and pair[0] > 0.0:
                derivative1 = _get_derivative(coords[-2])
                derivative2 = _get_derivative(coords[-1])
                # Derivative of the truncation line is a decreasing value;
                # when it passes Stemming Weight, we've found the segment
                # of truncation line intersecting with (0, 0) - (ui, oi) segment
                if derivative1 >= self.sw >= derivative2:
                    return coords
            cutlength += 1
        return coords

    def _errt(self):
        """Count Error-Rate Relative to Truncation (ERRT).

        :return: ERRT, length of the line from origo to (UI, OI) divided by
        the length of the line from origo to the point defined by the same
        line when extended until the truncation line.
        :rtype: float
        """
        # Count (UI, OI) pairs for truncation points until we find the segment where (ui, oi) crosses the truncation line
        self.coords = self._get_truncation_coordinates()
        if (0.0, 0.0) in self.coords:
            # Truncation line goes through origo, so ERRT cannot be counted
            if (self.ui, self.oi) != (0.0, 0.0):
                return float("inf")
            else:
                return float("nan")
        if (self.ui, self.oi) == (0.0, 0.0):
            # (ui, oi) is origo; define errt as 0.0
            return 0.0
        # Count the intersection point
        # Note that (self.ui, self.oi) cannot be (0.0, 0.0) and self.coords has different coordinates
        # so we have actual line segments instead of a line segment and a point
        intersection = _count_intersection(
            ((0, 0), (self.ui, self.oi)), self.coords[-2:]
        )
        # Count OP (length of the line from origo to (ui, oi))
        op = sqrt(self.ui**2 + self.oi**2)
        # Count OT (length of the line from origo to truncation line that goes through (ui, oi))
        ot = sqrt(intersection[0] ** 2 + intersection[1] ** 2)
        # OP / OT tells how well the stemming algorithm works compared to just truncating words
        return op / ot

    def update(self):
        """Update statistics after lemmas and stems have been set."""
        self.gumt, self.gdmt, self.gwmt, self.gdnt = _calculate(self.lemmas, self.stems)
        self.ui, self.oi, self.sw = _indexes(self.gumt, self.gdmt, self.gwmt, self.gdnt)
        self.errt = self._errt()


def demo():
    """Demonstration of the module."""
    # Some words with their real lemmas
    lemmas = {
        "kneel": ["kneel", "knelt"],
        "range": ["range", "ranged"],
        "ring": ["ring", "rang", "rung"],
    }
    # Same words with stems from a stemming algorithm
    stems = {
        "kneel": ["kneel"],
        "knelt": ["knelt"],
        "rang": ["rang", "range", "ranged"],
        "ring": ["ring"],
        "rung": ["rung"],
    }
    print("Words grouped by their lemmas:")
    for lemma in sorted(lemmas):
        print("{} => {}".format(lemma, " ".join(lemmas[lemma])))
    print()
    print("Same words grouped by a stemming algorithm:")
    for stem in sorted(stems):
        print("{} => {}".format(stem, " ".join(stems[stem])))
    print()
    p = Paice(lemmas, stems)
    print(p)
    print()
    # Let's "change" results from a stemming algorithm
    stems = {
        "kneel": ["kneel"],
        "knelt": ["knelt"],
        "rang": ["rang"],
        "range": ["range", "ranged"],
        "ring": ["ring"],
        "rung": ["rung"],
    }
    print("Counting stats after changing stemming results:")
    for stem in sorted(stems):
        print("{} => {}".format(stem, " ".join(stems[stem])))
    print()
    p.stems = stems
    p.update()
    print(p)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pyproject_hooks\_in_process\_in_process.py ===
"""This is invoked in a subprocess to call the build backend hooks.

It expects:
- Command line args: hook_name, control_dir
- Environment variables:
      _PYPROJECT_HOOKS_BUILD_BACKEND=entry.point:spec
      _PYPROJECT_HOOKS_BACKEND_PATH=paths (separated with os.pathsep)
- control_dir/input.json:
  - {"kwargs": {...}}

Results:
- control_dir/output.json
  - {"return_val": ...}
"""
import json
import os
import os.path
import re
import shutil
import sys
import traceback
from glob import glob
from importlib import import_module
from importlib.machinery import PathFinder
from os.path import join as pjoin

# This file is run as a script, and `import wrappers` is not zip-safe, so we
# include write_json() and read_json() from wrappers.py.


def write_json(obj, path, **kwargs):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kwargs)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class BackendUnavailable(Exception):
    """Raised if we cannot import the backend"""

    def __init__(self, message, traceback=None):
        super().__init__(message)
        self.message = message
        self.traceback = traceback


class HookMissing(Exception):
    """Raised if a hook is missing and we are not executing the fallback"""

    def __init__(self, hook_name=None):
        super().__init__(hook_name)
        self.hook_name = hook_name


def _build_backend():
    """Find and load the build backend"""
    backend_path = os.environ.get("_PYPROJECT_HOOKS_BACKEND_PATH")
    ep = os.environ["_PYPROJECT_HOOKS_BUILD_BACKEND"]
    mod_path, _, obj_path = ep.partition(":")

    if backend_path:
        # Ensure in-tree backend directories have the highest priority when importing.
        extra_pathitems = backend_path.split(os.pathsep)
        sys.meta_path.insert(0, _BackendPathFinder(extra_pathitems, mod_path))

    try:
        obj = import_module(mod_path)
    except ImportError:
        msg = f"Cannot import {mod_path!r}"
        raise BackendUnavailable(msg, traceback.format_exc())

    if obj_path:
        for path_part in obj_path.split("."):
            obj = getattr(obj, path_part)
    return obj


class _BackendPathFinder:
    """Implements the MetaPathFinder interface to locate modules in ``backend-path``.

    Since the environment provided by the frontend can contain all sorts of
    MetaPathFinders, the only way to ensure the backend is loaded from the
    right place is to prepend our own.
    """

    def __init__(self, backend_path, backend_module):
        self.backend_path = backend_path
        self.backend_module = backend_module
        self.backend_parent, _, _ = backend_module.partition(".")

    def find_spec(self, fullname, _path, _target=None):
        if "." in fullname:
            # Rely on importlib to find nested modules based on parent's path
            return None

        # Ignore other items in _path or sys.path and use backend_path instead:
        spec = PathFinder.find_spec(fullname, path=self.backend_path)
        if spec is None and fullname == self.backend_parent:
            # According to the spec, the backend MUST be loaded from backend-path.
            # Therefore, we can halt the import machinery and raise a clean error.
            msg = f"Cannot find module {self.backend_module!r} in {self.backend_path!r}"
            raise BackendUnavailable(msg)

        return spec

    if sys.version_info >= (3, 8):

        def find_distributions(self, context=None):
            # Delayed import: Python 3.7 does not contain importlib.metadata
            from importlib.metadata import DistributionFinder, MetadataPathFinder

            context = DistributionFinder.Context(path=self.backend_path)
            return MetadataPathFinder.find_distributions(context=context)


def _supported_features():
    """Return the list of options features supported by the backend.

    Returns a list of strings.
    The only possible value is 'build_editable'.
    """
    backend = _build_backend()
    features = []
    if hasattr(backend, "build_editable"):
        features.append("build_editable")
    return features


def get_requires_for_build_wheel(config_settings):
    """Invoke the optional get_requires_for_build_wheel hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_wheel
    except AttributeError:
        return []
    else:
        return hook(config_settings)


def get_requires_for_build_editable(config_settings):
    """Invoke the optional get_requires_for_build_editable hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_editable
    except AttributeError:
        return []
    else:
        return hook(config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory, config_settings, _allow_fallback
):
    """Invoke optional prepare_metadata_for_build_wheel

    Implements a fallback by building a wheel if the hook isn't defined,
    unless _allow_fallback is False in which case HookMissing is raised.
    """
    backend = _build_backend()
    try:
        hook = backend.prepare_metadata_for_build_wheel
    except AttributeError:
        if not _allow_fallback:
            raise HookMissing()
    else:
        return hook(metadata_directory, config_settings)
    # fallback to build_wheel outside the try block to avoid exception chaining
    # which can be confusing to users and is not relevant
    whl_basename = backend.build_wheel(metadata_directory, config_settings)
    return _get_wheel_metadata_from_wheel(
        whl_basename, metadata_directory, config_settings
    )


def prepare_metadata_for_build_editable(
    metadata_directory, config_settings, _allow_fallback
):
    """Invoke optional prepare_metadata_for_build_editable

    Implements a fallback by building an editable wheel if the hook isn't
    defined, unless _allow_fallback is False in which case HookMissing is
    raised.
    """
    backend = _build_backend()
    try:
        hook = backend.prepare_metadata_for_build_editable
    except AttributeError:
        if not _allow_fallback:
            raise HookMissing()
        try:
            build_hook = backend.build_editable
        except AttributeError:
            raise HookMissing(hook_name="build_editable")
        else:
            whl_basename = build_hook(metadata_directory, config_settings)
            return _get_wheel_metadata_from_wheel(
                whl_basename, metadata_directory, config_settings
            )
    else:
        return hook(metadata_directory, config_settings)


WHEEL_BUILT_MARKER = "PYPROJECT_HOOKS_ALREADY_BUILT_WHEEL"


def _dist_info_files(whl_zip):
    """Identify the .dist-info folder inside a wheel ZipFile."""
    res = []
    for path in whl_zip.namelist():
        m = re.match(r"[^/\\]+-[^/\\]+\.dist-info/", path)
        if m:
            res.append(path)
    if res:
        return res
    raise Exception("No .dist-info folder found in wheel")


def _get_wheel_metadata_from_wheel(whl_basename, metadata_directory, config_settings):
    """Extract the metadata from a wheel.

    Fallback for when the build backend does not
    define the 'get_wheel_metadata' hook.
    """
    from zipfile import ZipFile

    with open(os.path.join(metadata_directory, WHEEL_BUILT_MARKER), "wb"):
        pass  # Touch marker file

    whl_file = os.path.join(metadata_directory, whl_basename)
    with ZipFile(whl_file) as zipf:
        dist_info = _dist_info_files(zipf)
        zipf.extractall(path=metadata_directory, members=dist_info)
    return dist_info[0].split("/")[0]


def _find_already_built_wheel(metadata_directory):
    """Check for a wheel already built during the get_wheel_metadata hook."""
    if not metadata_directory:
        return None
    metadata_parent = os.path.dirname(metadata_directory)
    if not os.path.isfile(pjoin(metadata_parent, WHEEL_BUILT_MARKER)):
        return None

    whl_files = glob(os.path.join(metadata_parent, "*.whl"))
    if not whl_files:
        print("Found wheel built marker, but no .whl files")
        return None
    if len(whl_files) > 1:
        print(
            "Found multiple .whl files; unspecified behaviour. "
            "Will call build_wheel."
        )
        return None

    # Exactly one .whl file
    return whl_files[0]


def build_wheel(wheel_directory, config_settings, metadata_directory=None):
    """Invoke the mandatory build_wheel hook.

    If a wheel was already built in the
    prepare_metadata_for_build_wheel fallback, this
    will copy it rather than rebuilding the wheel.
    """
    prebuilt_whl = _find_already_built_wheel(metadata_directory)
    if prebuilt_whl:
        shutil.copy2(prebuilt_whl, wheel_directory)
        return os.path.basename(prebuilt_whl)

    return _build_backend().build_wheel(
        wheel_directory, config_settings, metadata_directory
    )


def build_editable(wheel_directory, config_settings, metadata_directory=None):
    """Invoke the optional build_editable hook.

    If a wheel was already built in the
    prepare_metadata_for_build_editable fallback, this
    will copy it rather than rebuilding the wheel.
    """
    backend = _build_backend()
    try:
        hook = backend.build_editable
    except AttributeError:
        raise HookMissing()
    else:
        prebuilt_whl = _find_already_built_wheel(metadata_directory)
        if prebuilt_whl:
            shutil.copy2(prebuilt_whl, wheel_directory)
            return os.path.basename(prebuilt_whl)

        return hook(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_sdist(config_settings):
    """Invoke the optional get_requires_for_build_wheel hook

    Returns [] if the hook is not defined.
    """
    backend = _build_backend()
    try:
        hook = backend.get_requires_for_build_sdist
    except AttributeError:
        return []
    else:
        return hook(config_settings)


class _DummyException(Exception):
    """Nothing should ever raise this exception"""


class GotUnsupportedOperation(Exception):
    """For internal use when backend raises UnsupportedOperation"""

    def __init__(self, traceback):
        self.traceback = traceback


def build_sdist(sdist_directory, config_settings):
    """Invoke the mandatory build_sdist hook."""
    backend = _build_backend()
    try:
        return backend.build_sdist(sdist_directory, config_settings)
    except getattr(backend, "UnsupportedOperation", _DummyException):
        raise GotUnsupportedOperation(traceback.format_exc())


HOOK_NAMES = {
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "build_wheel",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_editable",
    "build_editable",
    "get_requires_for_build_sdist",
    "build_sdist",
    "_supported_features",
}


def main():
    if len(sys.argv) < 3:
        sys.exit("Needs args: hook_name, control_dir")
    hook_name = sys.argv[1]
    control_dir = sys.argv[2]
    if hook_name not in HOOK_NAMES:
        sys.exit("Unknown hook: %s" % hook_name)

    # Remove the parent directory from sys.path to avoid polluting the backend
    # import namespace with this directory.
    here = os.path.dirname(__file__)
    if here in sys.path:
        sys.path.remove(here)

    hook = globals()[hook_name]

    hook_input = read_json(pjoin(control_dir, "input.json"))

    json_out = {"unsupported": False, "return_val": None}
    try:
        json_out["return_val"] = hook(**hook_input["kwargs"])
    except BackendUnavailable as e:
        json_out["no_backend"] = True
        json_out["traceback"] = e.traceback
        json_out["backend_error"] = e.message
    except GotUnsupportedOperation as e:
        json_out["unsupported"] = True
        json_out["traceback"] = e.traceback
    except HookMissing as e:
        json_out["hook_missing"] = True
        json_out["missing_hook_name"] = e.hook_name or hook_name

    write_json(json_out, pjoin(control_dir, "output.json"), indent=2)


if __name__ == "__main__":
    main()