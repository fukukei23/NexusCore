
# === NexusCore/openenv\Lib\site-packages\grpc\_observability.py ===
# Copyright 2023 The gRPC authors.
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

import abc
import contextlib
import logging
import threading
from typing import Any, Generator, Generic, List, Optional, TypeVar

from grpc._cython import cygrpc as _cygrpc
from grpc._typing import ChannelArgumentType

_LOGGER = logging.getLogger(__name__)

_channel = Any  # _channel.py imports this module.
ClientCallTracerCapsule = TypeVar("ClientCallTracerCapsule")
ServerCallTracerFactoryCapsule = TypeVar("ServerCallTracerFactoryCapsule")

_plugin_lock: threading.RLock = threading.RLock()
_OBSERVABILITY_PLUGIN: Optional["ObservabilityPlugin"] = None
_SERVICES_TO_EXCLUDE: List[bytes] = [
    b"google.monitoring.v3.MetricService",
    b"google.devtools.cloudtrace.v2.TraceService",
]


class ServerCallTracerFactory:
    """An encapsulation of a ServerCallTracerFactory.

    Instances of this class can be passed to a Channel as values for the
    grpc.experimental.server_call_tracer_factory option
    """

    def __init__(self, address):
        self._address = address

    def __int__(self):
        return self._address


class ObservabilityPlugin(
    Generic[ClientCallTracerCapsule, ServerCallTracerFactoryCapsule],
    metaclass=abc.ABCMeta,
):
    """Abstract base class for observability plugin.

    *This is a semi-private class that was intended for the exclusive use of
     the gRPC team.*

    The ClientCallTracerCapsule and ClientCallTracerCapsule created by this
    plugin should be injected to gRPC core using observability_init at the
    start of a program, before any channels/servers are built.

    Any future methods added to this interface cannot have the
    @abc.abstractmethod annotation.

    Attributes:
      _stats_enabled: A bool indicates whether tracing is enabled.
      _tracing_enabled: A bool indicates whether stats(metrics) is enabled.
      _registered_methods: A set which stores the registered method names in
        bytes.
    """

    _tracing_enabled: bool = False
    _stats_enabled: bool = False

    @abc.abstractmethod
    def create_client_call_tracer(
        self, method_name: bytes, target: bytes
    ) -> ClientCallTracerCapsule:
        """Creates a ClientCallTracerCapsule.

        After register the plugin, if tracing or stats is enabled, this method
        will be called after a call was created, the ClientCallTracer created
        by this method will be saved to call context.

        The ClientCallTracer is an object which implements `grpc_core::ClientCallTracer`
        interface and wrapped in a PyCapsule using `client_call_tracer` as name.

        Args:
          method_name: The method name of the call in byte format.
          target: The channel target of the call in byte format.
          registered_method: Whether this method is pre-registered.

        Returns:
          A PyCapsule which stores a ClientCallTracer object.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def save_trace_context(
        self, trace_id: str, span_id: str, is_sampled: bool
    ) -> None:
        """Saves the trace_id and span_id related to the current span.

        After register the plugin, if tracing is enabled, this method will be
        called after the server finished sending response.

        This method can be used to propagate census context.

        Args:
          trace_id: The identifier for the trace associated with the span as a
            32-character hexadecimal encoded string,
            e.g. 26ed0036f2eff2b7317bccce3e28d01f
          span_id: The identifier for the span as a 16-character hexadecimal encoded
            string. e.g. 113ec879e62583bc
          is_sampled: A bool indicates whether the span is sampled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def create_server_call_tracer_factory(
        self,
        *,
        xds: bool = False,
    ) -> Optional[ServerCallTracerFactoryCapsule]:
        """Creates a ServerCallTracerFactoryCapsule.

        This method will be called at server initialization time to create a
        ServerCallTracerFactory, which will be registered to gRPC core.

        The ServerCallTracerFactory is an object which implements
        `grpc_core::ServerCallTracerFactory` interface and wrapped in a PyCapsule
        using `server_call_tracer_factory` as name.

        Args:
          xds: Whether the server is xds server.
        Returns:
          A PyCapsule which stores a ServerCallTracerFactory object. Or None if
        plugin decides not to create ServerCallTracerFactory.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def record_rpc_latency(
        self, method: str, target: str, rpc_latency: float, status_code: Any
    ) -> None:
        """Record the latency of the RPC.

        After register the plugin, if stats is enabled, this method will be
        called at the end of each RPC.

        Args:
          method: The fully-qualified name of the RPC method being invoked.
          target: The target name of the RPC method being invoked.
          rpc_latency: The latency for the RPC in seconds, equals to the time between
            when the client invokes the RPC and when the client receives the status.
          status_code: An element of grpc.StatusCode in string format representing the
            final status for the RPC.
        """
        raise NotImplementedError()

    def set_tracing(self, enable: bool) -> None:
        """Enable or disable tracing.

        Args:
          enable: A bool indicates whether tracing should be enabled.
        """
        self._tracing_enabled = enable

    def set_stats(self, enable: bool) -> None:
        """Enable or disable stats(metrics).

        Args:
          enable: A bool indicates whether stats should be enabled.
        """
        self._stats_enabled = enable

    def save_registered_method(self, method_name: bytes) -> None:
        """Saves the method name to registered_method list.

        When exporting metrics, method name for unregistered methods will be replaced
        with 'other' by default.

        Args:
          method_name: The method name in bytes.
        """
        raise NotImplementedError()

    @property
    def tracing_enabled(self) -> bool:
        return self._tracing_enabled

    @property
    def stats_enabled(self) -> bool:
        return self._stats_enabled

    @property
    def observability_enabled(self) -> bool:
        return self.tracing_enabled or self.stats_enabled


@contextlib.contextmanager
def get_plugin() -> Generator[Optional[ObservabilityPlugin], None, None]:
    """Get the ObservabilityPlugin in _observability module.

    Returns:
      The ObservabilityPlugin currently registered with the _observability
    module. Or None if no plugin exists at the time of calling this method.
    """
    with _plugin_lock:
        yield _OBSERVABILITY_PLUGIN


def set_plugin(observability_plugin: Optional[ObservabilityPlugin]) -> None:
    """Save ObservabilityPlugin to _observability module.

    Args:
      observability_plugin: The ObservabilityPlugin to save.

    Raises:
      ValueError: If an ObservabilityPlugin was already registered at the
    time of calling this method.
    """
    global _OBSERVABILITY_PLUGIN  # pylint: disable=global-statement
    with _plugin_lock:
        if observability_plugin and _OBSERVABILITY_PLUGIN:
            raise ValueError("observability_plugin was already set!")
        _OBSERVABILITY_PLUGIN = observability_plugin


def observability_init(observability_plugin: ObservabilityPlugin) -> None:
    """Initialize observability with provided ObservabilityPlugin.

    This method have to be called at the start of a program, before any
    channels/servers are built.

    Args:
      observability_plugin: The ObservabilityPlugin to use.

    Raises:
      ValueError: If an ObservabilityPlugin was already registered at the
    time of calling this method.
    """
    set_plugin(observability_plugin)


def observability_deinit() -> None:
    """Clear the observability context, including ObservabilityPlugin and
    ServerCallTracerFactory

    This method have to be called after exit observability context so that
    it's possible to re-initialize again.
    """
    set_plugin(None)
    _cygrpc.clear_server_call_tracer_factory()


def maybe_record_rpc_latency(state: "_channel._RPCState") -> None:
    """Record the latency of the RPC, if the plugin is registered and stats is enabled.

    This method will be called at the end of each RPC.

    Args:
      state: a grpc._channel._RPCState object which contains the stats related to the
    RPC.
    """
    # TODO(xuanwn): use channel args to exclude those metrics.
    for exclude_prefix in _SERVICES_TO_EXCLUDE:
        if exclude_prefix in state.method.encode("utf8"):
            return
    with get_plugin() as plugin:
        if plugin and plugin.stats_enabled:
            rpc_latency_s = state.rpc_end_time - state.rpc_start_time
            rpc_latency_ms = rpc_latency_s * 1000
            plugin.record_rpc_latency(
                state.method, state.target, rpc_latency_ms, state.code
            )


def create_server_call_tracer_factory_option(xds: bool) -> ChannelArgumentType:
    with get_plugin() as plugin:
        if plugin and plugin.stats_enabled:
            server_call_tracer_factory_address = (
                _cygrpc.get_server_call_tracer_factory_address(plugin, xds)
            )
            if server_call_tracer_factory_address:
                return (
                    (
                        "grpc.experimental.server_call_tracer_factory",
                        ServerCallTracerFactory(
                            server_call_tracer_factory_address
                        ),
                    ),
                )
        return ()

# === NexusCore/openenv\Lib\site-packages\platformdirs\api.py ===
"""Base API."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal


class PlatformDirsABC(ABC):  # noqa: PLR0904
    """Abstract base class for platform directories."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        appname: str | None = None,
        appauthor: str | Literal[False] | None = None,
        version: str | None = None,
        roaming: bool = False,  # noqa: FBT001, FBT002
        multipath: bool = False,  # noqa: FBT001, FBT002
        opinion: bool = True,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Create a new platform directory.

        :param appname: See `appname`.
        :param appauthor: See `appauthor`.
        :param version: See `version`.
        :param roaming: See `roaming`.
        :param multipath: See `multipath`.
        :param opinion: See `opinion`.
        :param ensure_exists: See `ensure_exists`.

        """
        self.appname = appname  #: The name of application.
        self.appauthor = appauthor
        """
        The name of the app author or distributing body for this application.

        Typically, it is the owning company name. Defaults to `appname`. You may pass ``False`` to disable it.

        """
        self.version = version
        """
        An optional version path element to append to the path.

        You might want to use this if you want multiple versions of your app to be able to run independently. If used,
        this would typically be ``<major>.<minor>``.

        """
        self.roaming = roaming
        """
        Whether to use the roaming appdata directory on Windows.

        That means that for users on a Windows network setup for roaming profiles, this user data will be synced on
        login (see
        `here <https://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>`_).

        """
        self.multipath = multipath
        """
        An optional parameter which indicates that the entire list of data dirs should be returned.

        By default, the first item would only be returned.

        """
        self.opinion = opinion  #: A flag to indicating to use opinionated values.
        self.ensure_exists = ensure_exists
        """
        Optionally create the directory (and any missing parents) upon access if it does not exist.

        By default, no directories are created.

        """

    def _append_app_name_and_version(self, *base: str) -> str:
        params = list(base[1:])
        if self.appname:
            params.append(self.appname)
            if self.version:
                params.append(self.version)
        path = os.path.join(base[0], *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    def _optionally_create_directory(self, path: str) -> None:
        if self.ensure_exists:
            Path(path).mkdir(parents=True, exist_ok=True)

    def _first_item_as_path_if_multipath(self, directory: str) -> Path:
        if self.multipath:
            # If multipath is True, the first path is returned.
            directory = directory.split(os.pathsep)[0]
        return Path(directory)

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user"""

    @property
    @abstractmethod
    def site_data_dir(self) -> str:
        """:return: data directory shared by users"""

    @property
    @abstractmethod
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user"""

    @property
    @abstractmethod
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users"""

    @property
    @abstractmethod
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user"""

    @property
    @abstractmethod
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users"""

    @property
    @abstractmethod
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user"""

    @property
    @abstractmethod
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user"""

    @property
    @abstractmethod
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user"""

    @property
    @abstractmethod
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user"""

    @property
    @abstractmethod
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user"""

    @property
    @abstractmethod
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user"""

    @property
    @abstractmethod
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user"""

    @property
    @abstractmethod
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user"""

    @property
    @abstractmethod
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user"""

    @property
    @abstractmethod
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users"""

    @property
    def user_data_path(self) -> Path:
        """:return: data path tied to the user"""
        return Path(self.user_data_dir)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users"""
        return Path(self.site_data_dir)

    @property
    def user_config_path(self) -> Path:
        """:return: config path tied to the user"""
        return Path(self.user_config_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users"""
        return Path(self.site_config_dir)

    @property
    def user_cache_path(self) -> Path:
        """:return: cache path tied to the user"""
        return Path(self.user_cache_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users"""
        return Path(self.site_cache_dir)

    @property
    def user_state_path(self) -> Path:
        """:return: state path tied to the user"""
        return Path(self.user_state_dir)

    @property
    def user_log_path(self) -> Path:
        """:return: log path tied to the user"""
        return Path(self.user_log_dir)

    @property
    def user_documents_path(self) -> Path:
        """:return: documents a path tied to the user"""
        return Path(self.user_documents_dir)

    @property
    def user_downloads_path(self) -> Path:
        """:return: downloads path tied to the user"""
        return Path(self.user_downloads_dir)

    @property
    def user_pictures_path(self) -> Path:
        """:return: pictures path tied to the user"""
        return Path(self.user_pictures_dir)

    @property
    def user_videos_path(self) -> Path:
        """:return: videos path tied to the user"""
        return Path(self.user_videos_dir)

    @property
    def user_music_path(self) -> Path:
        """:return: music path tied to the user"""
        return Path(self.user_music_dir)

    @property
    def user_desktop_path(self) -> Path:
        """:return: desktop path tied to the user"""
        return Path(self.user_desktop_dir)

    @property
    def user_runtime_path(self) -> Path:
        """:return: runtime path tied to the user"""
        return Path(self.user_runtime_dir)

    @property
    def site_runtime_path(self) -> Path:
        """:return: runtime path shared by users"""
        return Path(self.site_runtime_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield self.site_config_dir

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield self.site_data_dir

    def iter_cache_dirs(self) -> Iterator[str]:
        """:yield: all user and site cache directories."""
        yield self.user_cache_dir
        yield self.site_cache_dir

    def iter_runtime_dirs(self) -> Iterator[str]:
        """:yield: all user and site runtime directories."""
        yield self.user_runtime_dir
        yield self.site_runtime_dir

    def iter_config_paths(self) -> Iterator[Path]:
        """:yield: all user and site configuration paths."""
        for path in self.iter_config_dirs():
            yield Path(path)

    def iter_data_paths(self) -> Iterator[Path]:
        """:yield: all user and site data paths."""
        for path in self.iter_data_dirs():
            yield Path(path)

    def iter_cache_paths(self) -> Iterator[Path]:
        """:yield: all user and site cache paths."""
        for path in self.iter_cache_dirs():
            yield Path(path)

    def iter_runtime_paths(self) -> Iterator[Path]:
        """:yield: all user and site runtime paths."""
        for path in self.iter_runtime_dirs():
            yield Path(path)

# === NexusCore/openenv\Lib\site-packages\typer\cli.py ===
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import click
import typer
import typer.core
from click import Command, Group, Option

from . import __version__

default_app_names = ("app", "cli", "main")
default_func_names = ("main", "cli", "app")

app = typer.Typer()
utils_app = typer.Typer(help="Extra utility commands for Typer apps.")
app.add_typer(utils_app, name="utils")


class State:
    def __init__(self) -> None:
        self.app: Optional[str] = None
        self.func: Optional[str] = None
        self.file: Optional[Path] = None
        self.module: Optional[str] = None


state = State()


def maybe_update_state(ctx: click.Context) -> None:
    path_or_module = ctx.params.get("path_or_module")
    if path_or_module:
        file_path = Path(path_or_module)
        if file_path.exists() and file_path.is_file():
            state.file = file_path
        else:
            if not re.fullmatch(r"[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*", path_or_module):
                typer.echo(
                    f"Not a valid file or Python module: {path_or_module}", err=True
                )
                sys.exit(1)
            state.module = path_or_module
    app_name = ctx.params.get("app")
    if app_name:
        state.app = app_name
    func_name = ctx.params.get("func")
    if func_name:
        state.func = func_name


class TyperCLIGroup(typer.core.TyperGroup):
    def list_commands(self, ctx: click.Context) -> List[str]:
        self.maybe_add_run(ctx)
        return super().list_commands(ctx)

    def get_command(self, ctx: click.Context, name: str) -> Optional[Command]:
        self.maybe_add_run(ctx)
        return super().get_command(ctx, name)

    def invoke(self, ctx: click.Context) -> Any:
        self.maybe_add_run(ctx)
        return super().invoke(ctx)

    def maybe_add_run(self, ctx: click.Context) -> None:
        maybe_update_state(ctx)
        maybe_add_run_to_cli(self)


def get_typer_from_module(module: Any) -> Optional[typer.Typer]:
    # Try to get defined app
    if state.app:
        obj = getattr(module, state.app, None)
        if not isinstance(obj, typer.Typer):
            typer.echo(f"Not a Typer object: --app {state.app}", err=True)
            sys.exit(1)
        return obj
    # Try to get defined function
    if state.func:
        func_obj = getattr(module, state.func, None)
        if not callable(func_obj):
            typer.echo(f"Not a function: --func {state.func}", err=True)
            sys.exit(1)
        sub_app = typer.Typer()
        sub_app.command()(func_obj)
        return sub_app
    # Iterate and get a default object to use as CLI
    local_names = dir(module)
    local_names_set = set(local_names)
    # Try to get a default Typer app
    for name in default_app_names:
        if name in local_names_set:
            obj = getattr(module, name, None)
            if isinstance(obj, typer.Typer):
                return obj
    # Try to get any Typer app
    for name in local_names_set - set(default_app_names):
        obj = getattr(module, name)
        if isinstance(obj, typer.Typer):
            return obj
    # Try to get a default function
    for func_name in default_func_names:
        func_obj = getattr(module, func_name, None)
        if callable(func_obj):
            sub_app = typer.Typer()
            sub_app.command()(func_obj)
            return sub_app
    # Try to get any func app
    for func_name in local_names_set - set(default_func_names):
        func_obj = getattr(module, func_name)
        if callable(func_obj):
            sub_app = typer.Typer()
            sub_app.command()(func_obj)
            return sub_app
    return None


def get_typer_from_state() -> Optional[typer.Typer]:
    spec = None
    if state.file:
        module_name = state.file.name
        spec = importlib.util.spec_from_file_location(module_name, str(state.file))
    elif state.module:
        spec = importlib.util.find_spec(state.module)
    if spec is None:
        if state.file:
            typer.echo(f"Could not import as Python file: {state.file}", err=True)
        else:
            typer.echo(f"Could not import as Python module: {state.module}", err=True)
        sys.exit(1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    obj = get_typer_from_module(module)
    return obj


def maybe_add_run_to_cli(cli: click.Group) -> None:
    if "run" not in cli.commands:
        if state.file or state.module:
            obj = get_typer_from_state()
            if obj:
                obj._add_completion = False
                click_obj = typer.main.get_command(obj)
                click_obj.name = "run"
                if not click_obj.help:
                    click_obj.help = "Run the provided Typer app."
                cli.add_command(click_obj)


def print_version(ctx: click.Context, param: Option, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    typer.echo(f"Typer version: {__version__}")
    raise typer.Exit()


@app.callback(cls=TyperCLIGroup, no_args_is_help=True)
def callback(
    ctx: typer.Context,
    *,
    path_or_module: str = typer.Argument(None),
    app: str = typer.Option(None, help="The typer app object/variable to use."),
    func: str = typer.Option(None, help="The function to convert to Typer."),
    version: bool = typer.Option(
        False,
        "--version",
        help="Print version and exit.",
        callback=print_version,
    ),
) -> None:
    """
    Run Typer scripts with completion, without having to create a package.

    You probably want to install completion for the typer command:

    $ typer --install-completion

    https://typer.tiangolo.com/
    """
    maybe_update_state(ctx)


def get_docs_for_click(
    *,
    obj: Command,
    ctx: typer.Context,
    indent: int = 0,
    name: str = "",
    call_prefix: str = "",
    title: Optional[str] = None,
) -> str:
    docs = "#" * (1 + indent)
    command_name = name or obj.name
    if call_prefix:
        command_name = f"{call_prefix} {command_name}"
    if not title:
        title = f"`{command_name}`" if command_name else "CLI"
    docs += f" {title}\n\n"
    if obj.help:
        docs += f"{obj.help}\n\n"
    usage_pieces = obj.collect_usage_pieces(ctx)
    if usage_pieces:
        docs += "**Usage**:\n\n"
        docs += "```console\n"
        docs += "$ "
        if command_name:
            docs += f"{command_name} "
        docs += f"{' '.join(usage_pieces)}\n"
        docs += "```\n\n"
    args = []
    opts = []
    for param in obj.get_params(ctx):
        rv = param.get_help_record(ctx)
        if rv is not None:
            if param.param_type_name == "argument":
                args.append(rv)
            elif param.param_type_name == "option":
                opts.append(rv)
    if args:
        docs += "**Arguments**:\n\n"
        for arg_name, arg_help in args:
            docs += f"* `{arg_name}`"
            if arg_help:
                docs += f": {arg_help}"
            docs += "\n"
        docs += "\n"
    if opts:
        docs += "**Options**:\n\n"
        for opt_name, opt_help in opts:
            docs += f"* `{opt_name}`"
            if opt_help:
                docs += f": {opt_help}"
            docs += "\n"
        docs += "\n"
    if obj.epilog:
        docs += f"{obj.epilog}\n\n"
    if isinstance(obj, Group):
        group = obj
        commands = group.list_commands(ctx)
        if commands:
            docs += "**Commands**:\n\n"
            for command in commands:
                command_obj = group.get_command(ctx, command)
                assert command_obj
                docs += f"* `{command_obj.name}`"
                command_help = command_obj.get_short_help_str()
                if command_help:
                    docs += f": {command_help}"
                docs += "\n"
            docs += "\n"
        for command in commands:
            command_obj = group.get_command(ctx, command)
            assert command_obj
            use_prefix = ""
            if command_name:
                use_prefix += f"{command_name}"
            docs += get_docs_for_click(
                obj=command_obj, ctx=ctx, indent=indent + 1, call_prefix=use_prefix
            )
    return docs


@utils_app.command()
def docs(
    ctx: typer.Context,
    name: str = typer.Option("", help="The name of the CLI program to use in docs."),
    output: Optional[Path] = typer.Option(
        None,
        help="An output file to write docs to, like README.md.",
        file_okay=True,
        dir_okay=False,
    ),
    title: Optional[str] = typer.Option(
        None,
        help="The title for the documentation page. If not provided, the name of "
        "the program is used.",
    ),
) -> None:
    """
    Generate Markdown docs for a Typer app.
    """
    typer_obj = get_typer_from_state()
    if not typer_obj:
        typer.echo("No Typer app found", err=True)
        raise typer.Abort()
    click_obj = typer.main.get_command(typer_obj)
    docs = get_docs_for_click(obj=click_obj, ctx=ctx, name=name, title=title)
    clean_docs = f"{docs.strip()}\n"
    if output:
        output.write_text(clean_docs)
        typer.echo(f"Docs saved to: {output}")
    else:
        typer.echo(clean_docs)


def main() -> Any:
    return app()

# === NexusCore/openenv\Lib\site-packages\IPython\testing\plugin\ipdoctest.py ===
"""Nose Plugin that supports IPython doctests.

Limitations:

- When generating examples for use as doctests, make sure that you have
  pretty-printing OFF.  This can be done either by setting the
  ``PlainTextFormatter.pprint`` option in your configuration file to  False, or
  by interactively disabling it with  %Pprint.  This is required so that IPython
  output matches that of normal Python, which is used by doctest for internal
  execution.

- Do not rely on specific prompt numbers for results (such as using
  '_34==True', for example).  For IPython tests run via an external process the
  prompt numbers may be different, and IPython tests run as normal python code
  won't even have these special _NN variables set at all.
"""

#-----------------------------------------------------------------------------
# Module imports

# From the standard library
import doctest
import logging
import re

from testpath import modified_env

#-----------------------------------------------------------------------------
# Module globals and other constants
#-----------------------------------------------------------------------------

log = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------


class DocTestFinder(doctest.DocTestFinder):
    def _get_test(self, obj, name, module, globs, source_lines):
        test = super()._get_test(obj, name, module, globs, source_lines)

        if bool(getattr(obj, "__skip_doctest__", False)) and test is not None:
            for example in test.examples:
                example.options[doctest.SKIP] = True

        return test


class IPDoctestOutputChecker(doctest.OutputChecker):
    """Second-chance checker with support for random tests.

    If the default comparison doesn't pass, this checker looks in the expected
    output string for flags that tell us to ignore the output.
    """

    random_re = re.compile(r'#\s*random\s+')

    def check_output(self, want, got, optionflags):
        """Check output, accepting special markers embedded in the output.

        If the output didn't pass the default validation but the special string
        '#random' is included, we accept it."""

        # Let the original tester verify first, in case people have valid tests
        # that happen to have a comment saying '#random' embedded in.
        ret = doctest.OutputChecker.check_output(self, want, got,
                                                 optionflags)
        if not ret and self.random_re.search(want):
            # print('RANDOM OK:',want, file=sys.stderr)  # dbg
            return True

        return ret


# A simple subclassing of the original with a different class name, so we can
# distinguish and treat differently IPython examples from pure python ones.
class IPExample(doctest.Example): pass


class IPDocTestParser(doctest.DocTestParser):
    """
    A class used to parse strings containing doctest examples.

    Note: This is a version modified to properly recognize IPython input and
    convert any IPython examples into valid Python ones.
    """
    # This regular expression is used to find doctest examples in a
    # string.  It defines three groups: `source` is the source code
    # (including leading indentation and prompts); `indent` is the
    # indentation of the first (PS1) line of the source code; and
    # `want` is the expected output (including leading indentation).

    # Classic Python prompts or default IPython ones
    _PS1_PY = r'>>>'
    _PS2_PY = r'\.\.\.'

    _PS1_IP = r'In\ \[\d+\]:'
    _PS2_IP = r'\ \ \ \.\.\.+:'

    _RE_TPL = r'''
        # Source consists of a PS1 line followed by zero or more PS2 lines.
        (?P<source>
            (?:^(?P<indent> [ ]*) (?P<ps1> %s) .*)    # PS1 line
            (?:\n           [ ]*  (?P<ps2> %s) .*)*)  # PS2 lines
        \n? # a newline
        # Want consists of any non-blank lines that do not start with PS1.
        (?P<want> (?:(?![ ]*$)    # Not a blank line
                     (?![ ]*%s)   # Not a line starting with PS1
                     (?![ ]*%s)   # Not a line starting with PS2
                     .*$\n?       # But any other line
                  )*)
                  '''

    _EXAMPLE_RE_PY = re.compile( _RE_TPL % (_PS1_PY,_PS2_PY,_PS1_PY,_PS2_PY),
                                 re.MULTILINE | re.VERBOSE)

    _EXAMPLE_RE_IP = re.compile( _RE_TPL % (_PS1_IP,_PS2_IP,_PS1_IP,_PS2_IP),
                                 re.MULTILINE | re.VERBOSE)

    # Mark a test as being fully random.  In this case, we simply append the
    # random marker ('#random') to each individual example's output.  This way
    # we don't need to modify any other code.
    _RANDOM_TEST = re.compile(r'#\s*all-random\s+')

    def ip2py(self,source):
        """Convert input IPython source into valid Python."""
        block = _ip.input_transformer_manager.transform_cell(source)
        if len(block.splitlines()) == 1:
            return _ip.prefilter(block)
        else:
            return block

    def parse(self, string, name='<string>'):
        """
        Divide the given string into examples and intervening text,
        and return them as a list of alternating Examples and strings.
        Line numbers for the Examples are 0-based.  The optional
        argument `name` is a name identifying this string, and is only
        used for error messages.
        """

        # print('Parse string:\n',string)  # dbg

        string = string.expandtabs()
        # If all lines begin with the same indentation, then strip it.
        min_indent = self._min_indent(string)
        if min_indent > 0:
            string = '\n'.join([l[min_indent:] for l in string.split('\n')])

        output = []
        charno, lineno = 0, 0

        # We make 'all random' tests by adding the '# random' mark to every
        # block of output in the test.
        if self._RANDOM_TEST.search(string):
            random_marker = '\n# random'
        else:
            random_marker = ''

        # Whether to convert the input from ipython to python syntax
        ip2py = False
        # Find all doctest examples in the string.  First, try them as Python
        # examples, then as IPython ones
        terms = list(self._EXAMPLE_RE_PY.finditer(string))
        if terms:
            # Normal Python example
            Example = doctest.Example
        else:
            # It's an ipython example.
            terms = list(self._EXAMPLE_RE_IP.finditer(string))
            Example = IPExample
            ip2py = True

        for m in terms:
            # Add the pre-example text to `output`.
            output.append(string[charno:m.start()])
            # Update lineno (lines before this example)
            lineno += string.count('\n', charno, m.start())
            # Extract info from the regexp match.
            (source, options, want, exc_msg) = \
                     self._parse_example(m, name, lineno,ip2py)

            # Append the random-output marker (it defaults to empty in most
            # cases, it's only non-empty for 'all-random' tests):
            want += random_marker

            # Create an Example, and add it to the list.
            if not self._IS_BLANK_OR_COMMENT(source):
                output.append(Example(source, want, exc_msg,
                                      lineno=lineno,
                                      indent=min_indent+len(m.group('indent')),
                                      options=options))
            # Update lineno (lines inside this example)
            lineno += string.count('\n', m.start(), m.end())
            # Update charno.
            charno = m.end()
        # Add any remaining post-example text to `output`.
        output.append(string[charno:])
        return output

    def _parse_example(self, m, name, lineno,ip2py=False):
        """
        Given a regular expression match from `_EXAMPLE_RE` (`m`),
        return a pair `(source, want)`, where `source` is the matched
        example's source code (with prompts and indentation stripped);
        and `want` is the example's expected output (with indentation
        stripped).

        `name` is the string's name, and `lineno` is the line number
        where the example starts; both are used for error messages.

        Optional:
        `ip2py`: if true, filter the input via IPython to convert the syntax
        into valid python.
        """

        # Get the example's indentation level.
        indent = len(m.group('indent'))

        # Divide source into lines; check that they're properly
        # indented; and then strip their indentation & prompts.
        source_lines = m.group('source').split('\n')

        # We're using variable-length input prompts
        ps1 = m.group('ps1')
        ps2 = m.group('ps2')
        ps1_len = len(ps1)

        self._check_prompt_blank(source_lines, indent, name, lineno,ps1_len)
        if ps2:
            self._check_prefix(source_lines[1:], ' '*indent + ps2, name, lineno)

        source = '\n'.join([sl[indent+ps1_len+1:] for sl in source_lines])

        if ip2py:
            # Convert source input from IPython into valid Python syntax
            source = self.ip2py(source)

        # Divide want into lines; check that it's properly indented; and
        # then strip the indentation.  Spaces before the last newline should
        # be preserved, so plain rstrip() isn't good enough.
        want = m.group('want')
        want_lines = want.split('\n')
        if len(want_lines) > 1 and re.match(r' *$', want_lines[-1]):
            del want_lines[-1]  # forget final newline & spaces after it
        self._check_prefix(want_lines, ' '*indent, name,
                           lineno + len(source_lines))

        # Remove ipython output prompt that might be present in the first line
        want_lines[0] = re.sub(r'Out\[\d+\]: \s*?\n?','',want_lines[0])

        want = '\n'.join([wl[indent:] for wl in want_lines])

        # If `want` contains a traceback message, then extract it.
        m = self._EXCEPTION_RE.match(want)
        if m:
            exc_msg = m.group('msg')
        else:
            exc_msg = None

        # Extract options from the source.
        options = self._find_options(source, name, lineno)

        return source, options, want, exc_msg

    def _check_prompt_blank(self, lines, indent, name, lineno, ps1_len):
        """
        Given the lines of a source string (including prompts and
        leading indentation), check to make sure that every prompt is
        followed by a space character.  If any line is not followed by
        a space character, then raise ValueError.

        Note: IPython-modified version which takes the input prompt length as a
        parameter, so that prompts of variable length can be dealt with.
        """
        space_idx = indent+ps1_len
        min_len = space_idx+1
        for i, line in enumerate(lines):
            if len(line) >=  min_len and line[space_idx] != ' ':
                raise ValueError('line %r of the docstring for %s '
                                 'lacks blank after %s: %r' %
                                 (lineno+i+1, name,
                                  line[indent:space_idx], line))


SKIP = doctest.register_optionflag('SKIP')


class IPDocTestRunner(doctest.DocTestRunner):
    """Test runner that synchronizes the IPython namespace with test globals.
    """

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        # Override terminal size to standardise traceback format
        with modified_env({'COLUMNS': '80', 'LINES': '24'}):
            return super(IPDocTestRunner,self).run(test,
                                                   compileflags,out,clear_globs)

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_block\blockquote.py ===
# Block quotes
from __future__ import annotations

import logging

from ..common.utils import isStrSpace
from .state_block import StateBlock

LOGGER = logging.getLogger(__name__)


def blockquote(state: StateBlock, startLine: int, endLine: int, silent: bool) -> bool:
    LOGGER.debug(
        "entering blockquote: %s, %s, %s, %s", state, startLine, endLine, silent
    )

    oldLineMax = state.lineMax
    pos = state.bMarks[startLine] + state.tShift[startLine]
    max = state.eMarks[startLine]

    if state.is_code_block(startLine):
        return False

    # check the block quote marker
    try:
        if state.src[pos] != ">":
            return False
    except IndexError:
        return False
    pos += 1

    # we know that it's going to be a valid blockquote,
    # so no point trying to find the end of it in silent mode
    if silent:
        return True

    # set offset past spaces and ">"
    initial = offset = state.sCount[startLine] + 1

    try:
        second_char: str | None = state.src[pos]
    except IndexError:
        second_char = None

    # skip one optional space after '>'
    if second_char == " ":
        # ' >   test '
        #     ^ -- position start of line here:
        pos += 1
        initial += 1
        offset += 1
        adjustTab = False
        spaceAfterMarker = True
    elif second_char == "\t":
        spaceAfterMarker = True

        if (state.bsCount[startLine] + offset) % 4 == 3:
            # '  >\t  test '
            #       ^ -- position start of line here (tab has width==1)
            pos += 1
            initial += 1
            offset += 1
            adjustTab = False
        else:
            # ' >\t  test '
            #    ^ -- position start of line here + shift bsCount slightly
            #         to make extra space appear
            adjustTab = True

    else:
        spaceAfterMarker = False

    oldBMarks = [state.bMarks[startLine]]
    state.bMarks[startLine] = pos

    while pos < max:
        ch = state.src[pos]

        if isStrSpace(ch):
            if ch == "\t":
                offset += (
                    4
                    - (offset + state.bsCount[startLine] + (1 if adjustTab else 0)) % 4
                )
            else:
                offset += 1

        else:
            break

        pos += 1

    oldBSCount = [state.bsCount[startLine]]
    state.bsCount[startLine] = (
        state.sCount[startLine] + 1 + (1 if spaceAfterMarker else 0)
    )

    lastLineEmpty = pos >= max

    oldSCount = [state.sCount[startLine]]
    state.sCount[startLine] = offset - initial

    oldTShift = [state.tShift[startLine]]
    state.tShift[startLine] = pos - state.bMarks[startLine]

    terminatorRules = state.md.block.ruler.getRules("blockquote")

    oldParentType = state.parentType
    state.parentType = "blockquote"

    # Search the end of the block
    #
    # Block ends with either:
    #  1. an empty line outside:
    #     ```
    #     > test
    #
    #     ```
    #  2. an empty line inside:
    #     ```
    #     >
    #     test
    #     ```
    #  3. another tag:
    #     ```
    #     > test
    #      - - -
    #     ```

    # for (nextLine = startLine + 1; nextLine < endLine; nextLine++) {
    nextLine = startLine + 1
    while nextLine < endLine:
        # check if it's outdented, i.e. it's inside list item and indented
        # less than said list item:
        #
        # ```
        # 1. anything
        #    > current blockquote
        # 2. checking this line
        # ```
        isOutdented = state.sCount[nextLine] < state.blkIndent

        pos = state.bMarks[nextLine] + state.tShift[nextLine]
        max = state.eMarks[nextLine]

        if pos >= max:
            # Case 1: line is not inside the blockquote, and this line is empty.
            break

        evaluatesTrue = state.src[pos] == ">" and not isOutdented
        pos += 1
        if evaluatesTrue:
            # This line is inside the blockquote.

            # set offset past spaces and ">"
            initial = offset = state.sCount[nextLine] + 1

            try:
                next_char: str | None = state.src[pos]
            except IndexError:
                next_char = None

            # skip one optional space after '>'
            if next_char == " ":
                # ' >   test '
                #     ^ -- position start of line here:
                pos += 1
                initial += 1
                offset += 1
                adjustTab = False
                spaceAfterMarker = True
            elif next_char == "\t":
                spaceAfterMarker = True

                if (state.bsCount[nextLine] + offset) % 4 == 3:
                    # '  >\t  test '
                    #       ^ -- position start of line here (tab has width==1)
                    pos += 1
                    initial += 1
                    offset += 1
                    adjustTab = False
                else:
                    # ' >\t  test '
                    #    ^ -- position start of line here + shift bsCount slightly
                    #         to make extra space appear
                    adjustTab = True

            else:
                spaceAfterMarker = False

            oldBMarks.append(state.bMarks[nextLine])
            state.bMarks[nextLine] = pos

            while pos < max:
                ch = state.src[pos]

                if isStrSpace(ch):
                    if ch == "\t":
                        offset += (
                            4
                            - (
                                offset
                                + state.bsCount[nextLine]
                                + (1 if adjustTab else 0)
                            )
                            % 4
                        )
                    else:
                        offset += 1
                else:
                    break

                pos += 1

            lastLineEmpty = pos >= max

            oldBSCount.append(state.bsCount[nextLine])
            state.bsCount[nextLine] = (
                state.sCount[nextLine] + 1 + (1 if spaceAfterMarker else 0)
            )

            oldSCount.append(state.sCount[nextLine])
            state.sCount[nextLine] = offset - initial

            oldTShift.append(state.tShift[nextLine])
            state.tShift[nextLine] = pos - state.bMarks[nextLine]

            nextLine += 1
            continue

        # Case 2: line is not inside the blockquote, and the last line was empty.
        if lastLineEmpty:
            break

        # Case 3: another tag found.
        terminate = False

        for terminatorRule in terminatorRules:
            if terminatorRule(state, nextLine, endLine, True):
                terminate = True
                break

        if terminate:
            # Quirk to enforce "hard termination mode" for paragraphs;
            # normally if you call `tokenize(state, startLine, nextLine)`,
            # paragraphs will look below nextLine for paragraph continuation,
            # but if blockquote is terminated by another tag, they shouldn't
            state.lineMax = nextLine

            if state.blkIndent != 0:
                # state.blkIndent was non-zero, we now set it to zero,
                # so we need to re-calculate all offsets to appear as
                # if indent wasn't changed
                oldBMarks.append(state.bMarks[nextLine])
                oldBSCount.append(state.bsCount[nextLine])
                oldTShift.append(state.tShift[nextLine])
                oldSCount.append(state.sCount[nextLine])
                state.sCount[nextLine] -= state.blkIndent

            break

        oldBMarks.append(state.bMarks[nextLine])
        oldBSCount.append(state.bsCount[nextLine])
        oldTShift.append(state.tShift[nextLine])
        oldSCount.append(state.sCount[nextLine])

        # A negative indentation means that this is a paragraph continuation
        #
        state.sCount[nextLine] = -1

        nextLine += 1

    oldIndent = state.blkIndent
    state.blkIndent = 0

    token = state.push("blockquote_open", "blockquote", 1)
    token.markup = ">"
    token.map = lines = [startLine, 0]

    state.md.block.tokenize(state, startLine, nextLine)

    token = state.push("blockquote_close", "blockquote", -1)
    token.markup = ">"

    state.lineMax = oldLineMax
    state.parentType = oldParentType
    lines[1] = state.line

    # Restore original tShift; this might not be necessary since the parser
    # has already been here, but just to make sure we can do that.
    for i, item in enumerate(oldTShift):
        state.bMarks[i + startLine] = oldBMarks[i]
        state.tShift[i + startLine] = item
        state.sCount[i + startLine] = oldSCount[i]
        state.bsCount[i + startLine] = oldBSCount[i]

    state.blkIndent = oldIndent

    return True

# === NexusCore/openenv\Lib\site-packages\nltk\parse\bllip.py ===
# Natural Language Toolkit: Interface to BLLIP Parser
#
# Author: David McClosky <dmcc@bigasterisk.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.parse.api import ParserI
from nltk.tree import Tree

"""
Interface for parsing with BLLIP Parser. Requires the Python
bllipparser module. BllipParser objects can be constructed with the
``BllipParser.from_unified_model_dir`` class method or manually using the
``BllipParser`` constructor. The former is generally easier if you have
a BLLIP Parser unified model directory -- a basic model can be obtained
from NLTK's downloader. More unified parsing models can be obtained with
BLLIP Parser's ModelFetcher (run ``python -m bllipparser.ModelFetcher``
or see docs for ``bllipparser.ModelFetcher.download_and_install_model``).

Basic usage::

    # download and install a basic unified parsing model (Wall Street Journal)
    # sudo python -m nltk.downloader bllip_wsj_no_aux

    >>> from nltk.data import find
    >>> model_dir = find('models/bllip_wsj_no_aux').path
    >>> bllip = BllipParser.from_unified_model_dir(model_dir)

    # 1-best parsing
    >>> sentence1 = 'British left waffles on Falklands .'.split()
    >>> top_parse = bllip.parse_one(sentence1)
    >>> print(top_parse)
    (S1
      (S
        (NP (JJ British) (NN left))
        (VP (VBZ waffles) (PP (IN on) (NP (NNP Falklands))))
        (. .)))

    # n-best parsing
    >>> sentence2 = 'Time flies'.split()
    >>> all_parses = bllip.parse_all(sentence2)
    >>> print(len(all_parses))
    50
    >>> print(all_parses[0])
    (S1 (S (NP (NNP Time)) (VP (VBZ flies))))

    # incorporating external tagging constraints (None means unconstrained tag)
    >>> constrained1 = bllip.tagged_parse([('Time', 'VB'), ('flies', 'NNS')])
    >>> print(next(constrained1))
    (S1 (NP (VB Time) (NNS flies)))
    >>> constrained2 = bllip.tagged_parse([('Time', 'NN'), ('flies', None)])
    >>> print(next(constrained2))
    (S1 (NP (NN Time) (VBZ flies)))

References
----------

- Charniak, Eugene. "A maximum-entropy-inspired parser." Proceedings of
  the 1st North American chapter of the Association for Computational
  Linguistics conference. Association for Computational Linguistics,
  2000.

- Charniak, Eugene, and Mark Johnson. "Coarse-to-fine n-best parsing
  and MaxEnt discriminative reranking." Proceedings of the 43rd Annual
  Meeting on Association for Computational Linguistics. Association
  for Computational Linguistics, 2005.

Known issues
------------

Note that BLLIP Parser is not currently threadsafe. Since this module
uses a SWIG interface, it is potentially unsafe to create multiple
``BllipParser`` objects in the same process. BLLIP Parser currently
has issues with non-ASCII text and will raise an error if given any.

See https://pypi.python.org/pypi/bllipparser/ for more information
on BLLIP Parser's Python interface.
"""

__all__ = ["BllipParser"]

# this block allows this module to be imported even if bllipparser isn't
# available
try:
    from bllipparser import RerankingParser
    from bllipparser.RerankingParser import get_unified_model_parameters

    def _ensure_bllip_import_or_error():
        pass

except ImportError as ie:

    def _ensure_bllip_import_or_error(ie=ie):
        raise ImportError("Couldn't import bllipparser module: %s" % ie)


def _ensure_ascii(words):
    try:
        for i, word in enumerate(words):
            word.encode("ascii")
    except UnicodeEncodeError as e:
        raise ValueError(
            f"Token {i} ({word!r}) is non-ASCII. BLLIP Parser "
            "currently doesn't support non-ASCII inputs."
        ) from e


def _scored_parse_to_nltk_tree(scored_parse):
    return Tree.fromstring(str(scored_parse.ptb_parse))


class BllipParser(ParserI):
    """
    Interface for parsing with BLLIP Parser. BllipParser objects can be
    constructed with the ``BllipParser.from_unified_model_dir`` class
    method or manually using the ``BllipParser`` constructor.
    """

    def __init__(
        self,
        parser_model=None,
        reranker_features=None,
        reranker_weights=None,
        parser_options=None,
        reranker_options=None,
    ):
        """
        Load a BLLIP Parser model from scratch. You'll typically want to
        use the ``from_unified_model_dir()`` class method to construct
        this object.

        :param parser_model: Path to parser model directory
        :type parser_model: str

        :param reranker_features: Path the reranker model's features file
        :type reranker_features: str

        :param reranker_weights: Path the reranker model's weights file
        :type reranker_weights: str

        :param parser_options: optional dictionary of parser options, see
            ``bllipparser.RerankingParser.RerankingParser.load_parser_options()``
            for more information.
        :type parser_options: dict(str)

        :param reranker_options: optional
            dictionary of reranker options, see
            ``bllipparser.RerankingParser.RerankingParser.load_reranker_model()``
            for more information.
        :type reranker_options: dict(str)
        """
        _ensure_bllip_import_or_error()

        parser_options = parser_options or {}
        reranker_options = reranker_options or {}

        self.rrp = RerankingParser()
        self.rrp.load_parser_model(parser_model, **parser_options)
        if reranker_features and reranker_weights:
            self.rrp.load_reranker_model(
                features_filename=reranker_features,
                weights_filename=reranker_weights,
                **reranker_options,
            )

    def parse(self, sentence):
        """
        Use BLLIP Parser to parse a sentence. Takes a sentence as a list
        of words; it will be automatically tagged with this BLLIP Parser
        instance's tagger.

        :return: An iterator that generates parse trees for the sentence
            from most likely to least likely.

        :param sentence: The sentence to be parsed
        :type sentence: list(str)
        :rtype: iter(Tree)
        """
        _ensure_ascii(sentence)
        nbest_list = self.rrp.parse(sentence)
        for scored_parse in nbest_list:
            yield _scored_parse_to_nltk_tree(scored_parse)

    def tagged_parse(self, word_and_tag_pairs):
        """
        Use BLLIP to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized
        and tagged. BLLIP will attempt to use the tags provided but may
        use others if it can't come up with a complete parse subject
        to those constraints. You may also specify a tag as ``None``
        to leave a token's tag unconstrained.

        :return: An iterator that generates parse trees for the sentence
            from most likely to least likely.

        :param sentence: Input sentence to parse as (word, tag) pairs
        :type sentence: list(tuple(str, str))
        :rtype: iter(Tree)
        """
        words = []
        tag_map = {}
        for i, (word, tag) in enumerate(word_and_tag_pairs):
            words.append(word)
            if tag is not None:
                tag_map[i] = tag

        _ensure_ascii(words)
        nbest_list = self.rrp.parse_tagged(words, tag_map)
        for scored_parse in nbest_list:
            yield _scored_parse_to_nltk_tree(scored_parse)

    @classmethod
    def from_unified_model_dir(
        cls, model_dir, parser_options=None, reranker_options=None
    ):
        """
        Create a ``BllipParser`` object from a unified parsing model
        directory. Unified parsing model directories are a standardized
        way of storing BLLIP parser and reranker models together on disk.
        See ``bllipparser.RerankingParser.get_unified_model_parameters()``
        for more information about unified model directories.

        :return: A ``BllipParser`` object using the parser and reranker
            models in the model directory.

        :param model_dir: Path to the unified model directory.
        :type model_dir: str
        :param parser_options: optional dictionary of parser options, see
            ``bllipparser.RerankingParser.RerankingParser.load_parser_options()``
            for more information.
        :type parser_options: dict(str)
        :param reranker_options: optional dictionary of reranker options, see
            ``bllipparser.RerankingParser.RerankingParser.load_reranker_model()``
            for more information.
        :type reranker_options: dict(str)
        :rtype: BllipParser
        """
        (
            parser_model_dir,
            reranker_features_filename,
            reranker_weights_filename,
        ) = get_unified_model_parameters(model_dir)
        return cls(
            parser_model_dir,
            reranker_features_filename,
            reranker_weights_filename,
            parser_options,
            reranker_options,
        )


def demo():
    """This assumes the Python module bllipparser is installed."""

    # download and install a basic unified parsing model (Wall Street Journal)
    # sudo python -m nltk.downloader bllip_wsj_no_aux

    from nltk.data import find

    model_dir = find("models/bllip_wsj_no_aux").path

    print("Loading BLLIP Parsing models...")
    # the easiest way to get started is to use a unified model
    bllip = BllipParser.from_unified_model_dir(model_dir)
    print("Done.")

    sentence1 = "British left waffles on Falklands .".split()
    sentence2 = "I saw the man with the telescope .".split()
    # this sentence is known to fail under the WSJ parsing model
    fail1 = "# ! ? : -".split()
    for sentence in (sentence1, sentence2, fail1):
        print("Sentence: %r" % " ".join(sentence))
        try:
            tree = next(bllip.parse(sentence))
            print(tree)
        except StopIteration:
            print("(parse failed)")

    # n-best parsing demo
    for i, parse in enumerate(bllip.parse(sentence1)):
        print("parse %d:\n%s" % (i, parse))

    # using external POS tag constraints
    print(
        "forcing 'tree' to be 'NN':",
        next(bllip.tagged_parse([("A", None), ("tree", "NN")])),
    )
    print(
        "forcing 'A' to be 'DT' and 'tree' to be 'NNP':",
        next(bllip.tagged_parse([("A", "DT"), ("tree", "NNP")])),
    )
    # constraints don't have to make sense... (though on more complicated
    # sentences, they may cause the parse to fail)
    print(
        "forcing 'A' to be 'NNP':",
        next(bllip.tagged_parse([("A", "NNP"), ("tree", None)])),
    )

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_api_structures.py ===
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

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict, Union

# These are the structures that we like keeping in a JSON form for their potential
# reuse between SDKs / services. They are public and are a part of the
# stable API.

# Explicitly mark optional params as such for the documentation
# If there is at least one optional param, set total=False for better mypy handling.


class Cookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]


# TODO: We are waiting for PEP705 so SetCookieParam can be readonly and matches Cookie.
class SetCookieParam(TypedDict, total=False):
    name: str
    value: str
    url: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    expires: Optional[float]
    httpOnly: Optional[bool]
    secure: Optional[bool]
    sameSite: Optional[Literal["Lax", "None", "Strict"]]


class FloatRect(TypedDict):
    x: float
    y: float
    width: float
    height: float


class Geolocation(TypedDict, total=False):
    latitude: float
    longitude: float
    accuracy: Optional[float]


class HttpCredentials(TypedDict, total=False):
    username: str
    password: str
    origin: Optional[str]
    send: Optional[Literal["always", "unauthorized"]]


class LocalStorageEntry(TypedDict):
    name: str
    value: str


class OriginState(TypedDict):
    origin: str
    localStorage: List[LocalStorageEntry]


class PdfMargins(TypedDict, total=False):
    top: Optional[Union[str, float]]
    right: Optional[Union[str, float]]
    bottom: Optional[Union[str, float]]
    left: Optional[Union[str, float]]


class Position(TypedDict):
    x: float
    y: float


class ProxySettings(TypedDict, total=False):
    server: str
    bypass: Optional[str]
    username: Optional[str]
    password: Optional[str]


class StorageState(TypedDict, total=False):
    cookies: List[Cookie]
    origins: List[OriginState]


class ClientCertificate(TypedDict, total=False):
    origin: str
    certPath: Optional[Union[str, Path]]
    cert: Optional[bytes]
    keyPath: Optional[Union[str, Path]]
    key: Optional[bytes]
    pfxPath: Optional[Union[str, Path]]
    pfx: Optional[bytes]
    passphrase: Optional[str]


class ResourceTiming(TypedDict):
    startTime: float
    domainLookupStart: float
    domainLookupEnd: float
    connectStart: float
    secureConnectionStart: float
    connectEnd: float
    requestStart: float
    responseStart: float
    responseEnd: float


class RequestSizes(TypedDict):
    requestBodySize: int
    requestHeadersSize: int
    responseBodySize: int
    responseHeadersSize: int


class ViewportSize(TypedDict):
    width: int
    height: int


class SourceLocation(TypedDict):
    url: str
    lineNumber: int
    columnNumber: int


class FilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: bytes


class RemoteAddr(TypedDict):
    ipAddress: str
    port: int


class SecurityDetails(TypedDict):
    issuer: Optional[str]
    protocol: Optional[str]
    subjectName: Optional[str]
    validFrom: Optional[float]
    validTo: Optional[float]


class NameValue(TypedDict):
    name: str
    value: str


HeadersArray = List[NameValue]
Headers = Dict[str, str]


class ServerFilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: str


class FormField(TypedDict, total=False):
    name: str
    value: Optional[str]
    file: Optional[ServerFilePayload]


class ExpectedTextValue(TypedDict, total=False):
    string: str
    regexSource: str
    regexFlags: str
    matchSubstring: bool
    normalizeWhiteSpace: bool
    ignoreCase: Optional[bool]


class FrameExpectOptions(TypedDict, total=False):
    expressionArg: Any
    expectedText: Optional[Sequence[ExpectedTextValue]]
    expectedNumber: Optional[float]
    expectedValue: Optional[Any]
    useInnerText: Optional[bool]
    isNot: bool
    timeout: Optional[float]


class FrameExpectResult(TypedDict):
    matches: bool
    received: Any
    log: List[str]


AriaRole = Literal[
    "alert",
    "alertdialog",
    "application",
    "article",
    "banner",
    "blockquote",
    "button",
    "caption",
    "cell",
    "checkbox",
    "code",
    "columnheader",
    "combobox",
    "complementary",
    "contentinfo",
    "definition",
    "deletion",
    "dialog",
    "directory",
    "document",
    "emphasis",
    "feed",
    "figure",
    "form",
    "generic",
    "grid",
    "gridcell",
    "group",
    "heading",
    "img",
    "insertion",
    "link",
    "list",
    "listbox",
    "listitem",
    "log",
    "main",
    "marquee",
    "math",
    "menu",
    "menubar",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "meter",
    "navigation",
    "none",
    "note",
    "option",
    "paragraph",
    "presentation",
    "progressbar",
    "radio",
    "radiogroup",
    "region",
    "row",
    "rowgroup",
    "rowheader",
    "scrollbar",
    "search",
    "searchbox",
    "separator",
    "slider",
    "spinbutton",
    "status",
    "strong",
    "subscript",
    "superscript",
    "switch",
    "tab",
    "table",
    "tablist",
    "tabpanel",
    "term",
    "textbox",
    "time",
    "timer",
    "toolbar",
    "tooltip",
    "tree",
    "treegrid",
    "treeitem",
]


class TracingGroupLocation(TypedDict):
    file: str
    line: Optional[int]
    column: Optional[int]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\algebra.py ===
"""
    pygments.lexers.algebra
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for computer algebra systems.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, bygroups, do_insertions, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace

__all__ = ['GAPLexer', 'GAPConsoleLexer', 'MathematicaLexer', 'MuPADLexer',
           'BCLexer']


class GAPLexer(RegexLexer):
    """
    For GAP source code.
    """
    name = 'GAP'
    url = 'https://www.gap-system.org'
    aliases = ['gap']
    filenames = ['*.g', '*.gd', '*.gi', '*.gap']
    version_added = '2.0'

    tokens = {
        'root': [
            (r'#.*$', Comment.Single),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'\(|\)|\[|\]|\{|\}', Punctuation),
            (r'''(?x)\b(?:
                if|then|elif|else|fi|
                for|while|do|od|
                repeat|until|
                break|continue|
                function|local|return|end|
                rec|
                quit|QUIT|
                IsBound|Unbind|
                TryNextMethod|
                Info|Assert
              )\b''', Keyword),
            (r'''(?x)\b(?:
                true|false|fail|infinity
              )\b''',
             Name.Constant),
            (r'''(?x)\b(?:
                (Declare|Install)([A-Z][A-Za-z]+)|
                   BindGlobal|BIND_GLOBAL
              )\b''',
             Name.Builtin),
            (r'\.|,|:=|;|=|\+|-|\*|/|\^|>|<', Operator),
            (r'''(?x)\b(?:
                and|or|not|mod|in
              )\b''',
             Operator.Word),
            (r'''(?x)
              (?:\w+|`[^`]*`)
              (?:::\w+|`[^`]*`)*''', Name.Variable),
            (r'[0-9]+(?:\.[0-9]*)?(?:e[0-9]+)?', Number),
            (r'\.[0-9]+(?:e[0-9]+)?', Number),
            (r'.', Text)
        ],
    }

    def analyse_text(text):
        score = 0.0

        # Declaration part
        if re.search(
            r"(InstallTrueMethod|Declare(Attribute|Category|Filter|Operation" +
            r"|GlobalFunction|Synonym|SynonymAttr|Property))", text
        ):
            score += 0.7

        # Implementation part
        if re.search(
            r"(DeclareRepresentation|Install(GlobalFunction|Method|" +
            r"ImmediateMethod|OtherMethod)|New(Family|Type)|Objectify)", text
        ):
            score += 0.7

        return min(score, 1.0)


class GAPConsoleLexer(Lexer):
    """
    For GAP console sessions. Modeled after JuliaConsoleLexer.
    """
    name = 'GAP session'
    aliases = ['gap-console', 'gap-repl']
    filenames = ['*.tst']
    url = 'https://www.gap-system.org'
    version_added = '2.14'
    _example = "gap-repl/euclidean.tst"

    def get_tokens_unprocessed(self, text):
        gaplexer = GAPLexer(**self.options)
        start = 0
        curcode = ''
        insertions = []
        output = False
        error = False

        for line in text.splitlines(keepends=True):
            if line.startswith('gap> ') or line.startswith('brk> '):
                insertions.append((len(curcode), [(0, Generic.Prompt, line[:5])]))
                curcode += line[5:]
                output = False
                error = False
            elif not output and line.startswith('> '):
                insertions.append((len(curcode), [(0, Generic.Prompt, line[:2])]))
                curcode += line[2:]
            else:
                if curcode:
                    yield from do_insertions(
                        insertions, gaplexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                if line.startswith('Error, ') or error:
                    yield start, Generic.Error, line
                    error = True
                else:
                    yield start, Generic.Output, line
                output = True
            start += len(line)

        if curcode:
            yield from do_insertions(
                insertions, gaplexer.get_tokens_unprocessed(curcode))

    # the following is needed to distinguish Scilab and GAP .tst files
    def analyse_text(text):
        # GAP prompts are a dead give away, although hypothetical;y a
        # file in another language could be trying to compare a variable
        # "gap" as in "gap> 0.1". But that this should happen at the
        # start of a line seems unlikely...
        if re.search(r"^gap> ", text):
            return 0.9
        else:
            return 0.0


class MathematicaLexer(RegexLexer):
    """
    Lexer for Mathematica source code.
    """
    name = 'Mathematica'
    url = 'http://www.wolfram.com/mathematica/'
    aliases = ['mathematica', 'mma', 'nb']
    filenames = ['*.nb', '*.cdf', '*.nbp', '*.ma']
    mimetypes = ['application/mathematica',
                 'application/vnd.wolfram.mathematica',
                 'application/vnd.wolfram.mathematica.package',
                 'application/vnd.wolfram.cdf']
    version_added = '2.0'

    # http://reference.wolfram.com/mathematica/guide/Syntax.html
    operators = (
        ";;", "=", "=.", "!=" "==", ":=", "->", ":>", "/.", "+", "-", "*", "/",
        "^", "&&", "||", "!", "<>", "|", "/;", "?", "@", "//", "/@", "@@",
        "@@@", "~~", "===", "&", "<", ">", "<=", ">=",
    )

    punctuation = (",", ";", "(", ")", "[", "]", "{", "}")

    def _multi_escape(entries):
        return '({})'.format('|'.join(re.escape(entry) for entry in entries))

    tokens = {
        'root': [
            (r'(?s)\(\*.*?\*\)', Comment),

            (r'([a-zA-Z]+[A-Za-z0-9]*`)', Name.Namespace),
            (r'([A-Za-z0-9]*_+[A-Za-z0-9]*)', Name.Variable),
            (r'#\d*', Name.Variable),
            (r'([a-zA-Z]+[a-zA-Z0-9]*)', Name),

            (r'-?\d+\.\d*', Number.Float),
            (r'-?\d*\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            (words(operators), Operator),
            (words(punctuation), Punctuation),
            (r'".*?"', String),
            (r'\s+', Text.Whitespace),
        ],
    }


class MuPADLexer(RegexLexer):
    """
    A MuPAD lexer.
    Contributed by Christopher Creutzig <christopher@creutzig.de>.
    """
    name = 'MuPAD'
    url = 'http://www.mupad.com'
    aliases = ['mupad']
    filenames = ['*.mu']
    version_added = '0.8'

    tokens = {
        'root': [
            (r'//.*?$', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'\(|\)|\[|\]|\{|\}', Punctuation),
            (r'''(?x)\b(?:
                next|break|end|
                axiom|end_axiom|category|end_category|domain|end_domain|inherits|
                if|%if|then|elif|else|end_if|
                case|of|do|otherwise|end_case|
                while|end_while|
                repeat|until|end_repeat|
                for|from|to|downto|step|end_for|
                proc|local|option|save|begin|end_proc|
                delete|frame
              )\b''', Keyword),
            (r'''(?x)\b(?:
                DOM_ARRAY|DOM_BOOL|DOM_COMPLEX|DOM_DOMAIN|DOM_EXEC|DOM_EXPR|
                DOM_FAIL|DOM_FLOAT|DOM_FRAME|DOM_FUNC_ENV|DOM_HFARRAY|DOM_IDENT|
                DOM_INT|DOM_INTERVAL|DOM_LIST|DOM_NIL|DOM_NULL|DOM_POLY|DOM_PROC|
                DOM_PROC_ENV|DOM_RAT|DOM_SET|DOM_STRING|DOM_TABLE|DOM_VAR
              )\b''', Name.Class),
            (r'''(?x)\b(?:
                PI|EULER|E|CATALAN|
                NIL|FAIL|undefined|infinity|
                TRUE|FALSE|UNKNOWN
              )\b''',
             Name.Constant),
            (r'\b(?:dom|procname)\b', Name.Builtin.Pseudo),
            (r'\.|,|:|;|=|\+|-|\*|/|\^|@|>|<|\$|\||!|\'|%|~=', Operator),
            (r'''(?x)\b(?:
                and|or|not|xor|
                assuming|
                div|mod|
                union|minus|intersect|in|subset
              )\b''',
             Operator.Word),
            (r'\b(?:I|RDN_INF|RD_NINF|RD_NAN)\b', Number),
            # (r'\b(?:adt|linalg|newDomain|hold)\b', Name.Builtin),
            (r'''(?x)
              ((?:[a-zA-Z_#][\w#]*|`[^`]*`)
              (?:::[a-zA-Z_#][\w#]*|`[^`]*`)*)(\s*)([(])''',
             bygroups(Name.Function, Text, Punctuation)),
            (r'''(?x)
              (?:[a-zA-Z_#][\w#]*|`[^`]*`)
              (?:::[a-zA-Z_#][\w#]*|`[^`]*`)*''', Name.Variable),
            (r'[0-9]+(?:\.[0-9]*)?(?:e[0-9]+)?', Number),
            (r'\.[0-9]+(?:e[0-9]+)?', Number),
            (r'\s+', Whitespace),
            (r'.', Text)
        ],
        'comment': [
            (r'[^/*]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
    }


class BCLexer(RegexLexer):
    """
    A BC lexer.
    """
    name = 'BC'
    url = 'https://www.gnu.org/software/bc/'
    aliases = ['bc']
    filenames = ['*.bc']
    version_added = '2.1'

    tokens = {
        'root': [
            (r'/\*', Comment.Multiline, 'comment'),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'[{}();,]', Punctuation),
            (words(('if', 'else', 'while', 'for', 'break', 'continue',
                    'halt', 'return', 'define', 'auto', 'print', 'read',
                    'length', 'scale', 'sqrt', 'limits', 'quit',
                    'warranty'), suffix=r'\b'), Keyword),
            (r'\+\+|--|\|\||&&|'
             r'([-<>+*%\^/!=])=?', Operator),
            # bc doesn't support exponential
            (r'[0-9]+(\.[0-9]*)?', Number),
            (r'\.[0-9]+', Number),
            (r'.', Text)
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\configui.py ===
import pywin.scintilla.config
import win32api
import win32con
import win32ui
from pywin.framework.editor import DeleteEditorOption, GetEditorOption, SetEditorOption
from pywin.mfc import dialog

from . import document

# The standard 16 color VGA palette should always be possible
paletteVGA = (
    ("Black", 0, 0, 0),
    ("Navy", 0, 0, 128),
    ("Green", 0, 128, 0),
    ("Cyan", 0, 128, 128),
    ("Maroon", 128, 0, 0),
    ("Purple", 128, 0, 128),
    ("Olive", 128, 128, 0),
    ("Gray", 128, 128, 128),
    ("Silver", 192, 192, 192),
    ("Blue", 0, 0, 255),
    ("Lime", 0, 255, 0),
    ("Aqua", 0, 255, 255),
    ("Red", 255, 0, 0),
    ("Fuchsia", 255, 0, 255),
    ("Yellow", 255, 255, 0),
    ("White", 255, 255, 255),
)


######################################################
#
# Property Page for editor options
#
class EditorPropertyPage(dialog.PropertyPage):
    def __init__(self):
        dialog.PropertyPage.__init__(self, win32ui.IDD_PP_EDITOR)
        self.autooptions = []
        self._AddEditorOption(win32ui.IDC_AUTO_RELOAD, "i", "Auto Reload", 1)
        self._AddEditorOption(
            win32ui.IDC_COMBO1, "i", "Backup Type", document.BAK_DOT_BAK_BAK_DIR
        )
        self._AddEditorOption(
            win32ui.IDC_AUTOCOMPLETE, "i", "Autocomplete Attributes", 1
        )
        self._AddEditorOption(win32ui.IDC_CALLTIPS, "i", "Show Call Tips", 1)
        self._AddEditorOption(
            win32ui.IDC_MARGIN_LINENUMBER, "i", "Line Number Margin Width", 0
        )
        self._AddEditorOption(win32ui.IDC_RADIO1, "i", "MarkersInMargin", None)
        self._AddEditorOption(
            win32ui.IDC_MARGIN_MARKER, "i", "Marker Margin Width", None
        )
        self["Marker Margin Width"] = GetEditorOption("Marker Margin Width", 16)

        # Folding
        self._AddEditorOption(win32ui.IDC_MARGIN_FOLD, "i", "Fold Margin Width", 12)
        self._AddEditorOption(win32ui.IDC_FOLD_ENABLE, "i", "Enable Folding", 1)
        self._AddEditorOption(win32ui.IDC_FOLD_ON_OPEN, "i", "Fold On Open", 0)
        self._AddEditorOption(win32ui.IDC_FOLD_SHOW_LINES, "i", "Fold Lines", 1)

        # Right edge.
        self._AddEditorOption(
            win32ui.IDC_RIGHTEDGE_ENABLE, "i", "Right Edge Enabled", 0
        )
        self._AddEditorOption(
            win32ui.IDC_RIGHTEDGE_COLUMN, "i", "Right Edge Column", 75
        )

        # Source control, etc
        self.AddDDX(win32ui.IDC_VSS_INTEGRATE, "bVSS")
        self.AddDDX(win32ui.IDC_KEYBOARD_CONFIG, "Configs", "l")
        self["Configs"] = pywin.scintilla.config.find_config_files()

    def _AddEditorOption(self, idd, typ, optionName, defaultVal):
        self.AddDDX(idd, optionName, typ)
        # some options are "derived" - ie, can be implied from others
        # (eg, "view markers in background" is implied from "markerMarginWidth==0"
        # So we don't actually store these values, but they do still get DDX support.
        if defaultVal is not None:
            self[optionName] = GetEditorOption(optionName, defaultVal)
            self.autooptions.append((optionName, defaultVal))

    def OnInitDialog(self):
        for name, val in self.autooptions:
            self[name] = GetEditorOption(name, val)

        # Note that these MUST be in the same order as the BAK constants.
        cbo = self.GetDlgItem(win32ui.IDC_COMBO1)
        cbo.AddString("None")
        cbo.AddString(".BAK File")
        cbo.AddString("TEMP dir")
        cbo.AddString("Own dir")

        # Source Safe
        bVSS = (
            GetEditorOption("Source Control Module", "") == "pywin.framework.editor.vss"
        )
        self["bVSS"] = bVSS

        edit = self.GetDlgItem(win32ui.IDC_RIGHTEDGE_SAMPLE)
        edit.SetWindowText("Sample Color")

        rc = dialog.PropertyPage.OnInitDialog(self)

        try:
            self.GetDlgItem(win32ui.IDC_KEYBOARD_CONFIG).SelectString(
                -1, GetEditorOption("Keyboard Config", "default")
            )
        except win32ui.error:
            import traceback

            traceback.print_exc()

        self.HookCommand(self.OnButSimple, win32ui.IDC_FOLD_ENABLE)
        self.HookCommand(self.OnButSimple, win32ui.IDC_RADIO1)
        self.HookCommand(self.OnButSimple, win32ui.IDC_RADIO2)
        self.HookCommand(self.OnButSimple, win32ui.IDC_RIGHTEDGE_ENABLE)
        self.HookCommand(self.OnButEdgeColor, win32ui.IDC_RIGHTEDGE_DEFINE)

        butMarginEnabled = self["Marker Margin Width"] > 0
        self.GetDlgItem(win32ui.IDC_RADIO1).SetCheck(butMarginEnabled)
        self.GetDlgItem(win32ui.IDC_RADIO2).SetCheck(not butMarginEnabled)

        self.edgeColor = self.initialEdgeColor = GetEditorOption(
            "Right Edge Color", win32api.RGB(0xEF, 0xEF, 0xEF)
        )
        for spinner_id in (win32ui.IDC_SPIN1, win32ui.IDC_SPIN2, win32ui.IDC_SPIN3):
            spinner = self.GetDlgItem(spinner_id)
            spinner.SetRange(0, 100)
        self.UpdateUIForState()

        return rc

    def OnButSimple(self, id, code):
        if code == win32con.BN_CLICKED:
            self.UpdateUIForState()

    def OnButEdgeColor(self, id, code):
        if code == win32con.BN_CLICKED:
            d = win32ui.CreateColorDialog(self.edgeColor, 0, self)
            # Ensure the current color is a custom color (as it may not be in the swatch)
            # plus some other nice gray scales.
            ccs = [self.edgeColor]
            for c in range(0xEF, 0x4F, -0x10):
                ccs.append(win32api.RGB(c, c, c))
            d.SetCustomColors(ccs)
            if d.DoModal() == win32con.IDOK:
                self.edgeColor = d.GetColor()
                self.UpdateUIForState()

    def UpdateUIForState(self):
        folding = self.GetDlgItem(win32ui.IDC_FOLD_ENABLE).GetCheck()
        self.GetDlgItem(win32ui.IDC_FOLD_ON_OPEN).EnableWindow(folding)
        self.GetDlgItem(win32ui.IDC_FOLD_SHOW_LINES).EnableWindow(folding)

        widthEnabled = self.GetDlgItem(win32ui.IDC_RADIO1).GetCheck()
        self.GetDlgItem(win32ui.IDC_MARGIN_MARKER).EnableWindow(widthEnabled)
        self.UpdateData()  # Ensure self[] is up to date with the control data.
        if widthEnabled and self["Marker Margin Width"] == 0:
            self["Marker Margin Width"] = 16
            self.UpdateData(0)  # Ensure control up to date with self[]

        # Right edge
        edgeEnabled = self.GetDlgItem(win32ui.IDC_RIGHTEDGE_ENABLE).GetCheck()
        self.GetDlgItem(win32ui.IDC_RIGHTEDGE_COLUMN).EnableWindow(edgeEnabled)
        self.GetDlgItem(win32ui.IDC_RIGHTEDGE_SAMPLE).EnableWindow(edgeEnabled)
        self.GetDlgItem(win32ui.IDC_RIGHTEDGE_DEFINE).EnableWindow(edgeEnabled)

        edit = self.GetDlgItem(win32ui.IDC_RIGHTEDGE_SAMPLE)
        edit.SetBackgroundColor(0, self.edgeColor)

    def OnOK(self):
        for name, defVal in self.autooptions:
            SetEditorOption(name, self[name])
        # Margin width gets handled differently.
        if self["MarkersInMargin"] == 0:
            SetEditorOption("Marker Margin Width", self["Marker Margin Width"])
        else:
            SetEditorOption("Marker Margin Width", 0)
        if self.edgeColor != self.initialEdgeColor:
            SetEditorOption("Right Edge Color", self.edgeColor)
        if self["bVSS"]:
            SetEditorOption("Source Control Module", "pywin.framework.editor.vss")
        else:
            if (
                GetEditorOption("Source Control Module", "")
                == "pywin.framework.editor.vss"
            ):
                SetEditorOption("Source Control Module", "")
        # Keyboard config
        configname = self.GetDlgItem(win32ui.IDC_KEYBOARD_CONFIG).GetWindowText()
        if configname:
            if configname == "default":
                DeleteEditorOption("Keyboard Config")
            else:
                SetEditorOption("Keyboard Config", configname)

            import pywin.scintilla.view

            pywin.scintilla.view.LoadConfiguration()

        # Now tell all views we have changed.
        ##		for doc in editorTemplate.GetDocumentList():
        ##			for view in doc.GetAllViews():
        ##				try:
        ##					fn = view.OnConfigChange
        ##				except AttributeError:
        ##					continue
        ##				fn()
        return 1


class EditorWhitespacePropertyPage(dialog.PropertyPage):
    def __init__(self):
        dialog.PropertyPage.__init__(self, win32ui.IDD_PP_TABS)
        self.autooptions = []
        self._AddEditorOption(win32ui.IDC_TAB_SIZE, "i", "Tab Size", 4)
        self._AddEditorOption(win32ui.IDC_INDENT_SIZE, "i", "Indent Size", 4)
        self._AddEditorOption(win32ui.IDC_USE_SMART_TABS, "i", "Smart Tabs", 1)
        self._AddEditorOption(win32ui.IDC_VIEW_WHITESPACE, "i", "View Whitespace", 0)
        self._AddEditorOption(win32ui.IDC_VIEW_EOL, "i", "View EOL", 0)
        self._AddEditorOption(
            win32ui.IDC_VIEW_INDENTATIONGUIDES, "i", "View Indentation Guides", 0
        )

    def _AddEditorOption(self, idd, typ, optionName, defaultVal):
        self.AddDDX(idd, optionName, typ)
        self[optionName] = GetEditorOption(optionName, defaultVal)
        self.autooptions.append((optionName, defaultVal))

    def OnInitDialog(self):
        for name, val in self.autooptions:
            self[name] = GetEditorOption(name, val)

        rc = dialog.PropertyPage.OnInitDialog(self)

        idc = win32ui.IDC_TABTIMMY_NONE
        if GetEditorOption("Use Tab Timmy", 1):
            idc = win32ui.IDC_TABTIMMY_IND
        self.GetDlgItem(idc).SetCheck(1)

        idc = win32ui.IDC_RADIO1
        if GetEditorOption("Use Tabs", 0):
            idc = win32ui.IDC_USE_TABS
        self.GetDlgItem(idc).SetCheck(1)

        tt_color = GetEditorOption("Tab Timmy Color", win32api.RGB(0xFF, 0, 0))
        self.cbo = self.GetDlgItem(win32ui.IDC_COMBO1)
        for c in paletteVGA:
            self.cbo.AddString(c[0])
        sel = 0
        for c in paletteVGA:
            if tt_color == win32api.RGB(c[1], c[2], c[3]):
                break
            sel += 1
        else:
            sel = -1
        self.cbo.SetCurSel(sel)
        self.HookCommand(self.OnButSimple, win32ui.IDC_TABTIMMY_NONE)
        self.HookCommand(self.OnButSimple, win32ui.IDC_TABTIMMY_IND)
        self.HookCommand(self.OnButSimple, win32ui.IDC_TABTIMMY_BG)
        # Set ranges for the spinners.
        for spinner_id in [win32ui.IDC_SPIN1, win32ui.IDC_SPIN2]:
            spinner = self.GetDlgItem(spinner_id)
            spinner.SetRange(1, 16)
        return rc

    def OnButSimple(self, id, code):
        if code == win32con.BN_CLICKED:
            self.UpdateUIForState()

    def UpdateUIForState(self):
        timmy = self.GetDlgItem(win32ui.IDC_TABTIMMY_NONE).GetCheck()
        self.GetDlgItem(win32ui.IDC_COMBO1).EnableWindow(not timmy)

    def OnOK(self):
        for name, defVal in self.autooptions:
            SetEditorOption(name, self[name])

        SetEditorOption("Use Tabs", self.GetDlgItem(win32ui.IDC_USE_TABS).GetCheck())

        SetEditorOption(
            "Use Tab Timmy", self.GetDlgItem(win32ui.IDC_TABTIMMY_IND).GetCheck()
        )
        c = paletteVGA[self.cbo.GetCurSel()]
        SetEditorOption("Tab Timmy Color", win32api.RGB(c[1], c[2], c[3]))

        return 1


def testpp():
    ps = dialog.PropertySheet("Editor Options")
    ps.AddPage(EditorWhitespacePropertyPage())
    ps.DoModal()


if __name__ == "__main__":
    testpp()

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_windows.py ===
from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest

on_windows = os.name == "nt"
# Mark all the tests in this file as being windows-only
pytestmark = pytest.mark.skipif(not on_windows, reason="windows only")

assert (
    sys.platform == "win32" or not TYPE_CHECKING
)  # Skip type checking when not on Windows

from ... import _core, sleep
from ...testing import wait_all_tasks_blocked
from .tutil import gc_collect_harder, restore_unraisablehook, slow

if TYPE_CHECKING:
    from collections.abc import Generator
    from io import BufferedWriter

if on_windows:
    from .._windows_cffi import (
        INVALID_HANDLE_VALUE,
        FileFlags,
        Handle,
        ffi,
        kernel32,
        raise_winerror,
    )


def test_winerror(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = create_autospec(ffi.getwinerror)
    monkeypatch.setattr(ffi, "getwinerror", mock)

    # Returning none = no error, should not happen.
    mock.return_value = None
    with pytest.raises(RuntimeError, match=r"^No error set\?$"):
        raise_winerror()
    mock.assert_called_once_with()
    mock.reset_mock()

    with pytest.raises(RuntimeError, match=r"^No error set\?$"):
        raise_winerror(38)
    mock.assert_called_once_with(38)
    mock.reset_mock()

    mock.return_value = (12, "test error")
    with pytest.raises(
        OSError,
        match=r"^\[WinError 12\] test error: 'file_1' -> 'file_2'$",
    ) as exc:
        raise_winerror(filename="file_1", filename2="file_2")
    mock.assert_called_once_with()
    mock.reset_mock()
    assert exc.value.winerror == 12
    assert exc.value.strerror == "test error"
    assert exc.value.filename == "file_1"
    assert exc.value.filename2 == "file_2"

    # With an explicit number passed in, it overrides what getwinerror() returns.
    with pytest.raises(
        OSError,
        match=r"^\[WinError 18\] test error: 'a/file' -> 'b/file'$",
    ) as exc:
        raise_winerror(18, filename="a/file", filename2="b/file")
    mock.assert_called_once_with(18)
    mock.reset_mock()
    assert exc.value.winerror == 18
    assert exc.value.strerror == "test error"
    assert exc.value.filename == "a/file"
    assert exc.value.filename2 == "b/file"


# The undocumented API that this is testing should be changed to stop using
# UnboundedQueue (or just removed until we have time to redo it), but until
# then we filter out the warning.
@pytest.mark.filterwarnings("ignore:.*UnboundedQueue:trio.TrioDeprecationWarning")
async def test_completion_key_listen() -> None:
    from .. import _io_windows

    async def post(key: int) -> None:
        iocp = Handle(ffi.cast("HANDLE", _core.current_iocp()))
        for i in range(10):
            print("post", i)
            if i % 3 == 0:
                await _core.checkpoint()
            success = kernel32.PostQueuedCompletionStatus(iocp, i, key, ffi.NULL)
            assert success

    with _core.monitor_completion_key() as (key, queue):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(post, key)
            i = 0
            print("loop")
            async for batch in queue:  # pragma: no branch
                print("got some", batch)
                for info in batch:
                    assert isinstance(info, _io_windows.CompletionKeyEventInfo)
                    assert info.lpOverlapped == 0
                    assert info.dwNumberOfBytesTransferred == i
                    i += 1
                if i == 10:
                    break
            print("end loop")


async def test_readinto_overlapped() -> None:
    data = b"1" * 1024 + b"2" * 1024 + b"3" * 1024 + b"4" * 1024
    buffer = bytearray(len(data))

    with tempfile.TemporaryDirectory() as tdir:
        tfile = os.path.join(tdir, "numbers.txt")
        with open(  # noqa: ASYNC230  # This is a test, synchronous is ok
            tfile,
            "wb",
        ) as fp:
            fp.write(data)
            fp.flush()

        rawname = tfile.encode("utf-16le") + b"\0\0"
        rawname_buf = ffi.from_buffer(rawname)
        handle = kernel32.CreateFileW(
            ffi.cast("LPCWSTR", rawname_buf),
            FileFlags.GENERIC_READ,
            FileFlags.FILE_SHARE_READ,
            ffi.NULL,  # no security attributes
            FileFlags.OPEN_EXISTING,
            FileFlags.FILE_FLAG_OVERLAPPED,
            ffi.NULL,  # no template file
        )
        if handle == INVALID_HANDLE_VALUE:  # pragma: no cover
            raise_winerror()

        try:
            with memoryview(buffer) as buffer_view:

                async def read_region(start: int, end: int) -> None:
                    await _core.readinto_overlapped(
                        handle,
                        buffer_view[start:end],
                        start,
                    )

                _core.register_with_iocp(handle)
                async with _core.open_nursery() as nursery:
                    for start in range(0, 4096, 512):
                        nursery.start_soon(read_region, start, start + 512)

                assert buffer == data

                with pytest.raises((BufferError, TypeError)):
                    await _core.readinto_overlapped(handle, b"immutable")
        finally:
            kernel32.CloseHandle(handle)


@contextmanager
def pipe_with_overlapped_read() -> Generator[tuple[BufferedWriter, int], None, None]:
    import msvcrt
    from asyncio.windows_utils import pipe

    read_handle, write_handle = pipe(overlapped=(True, False))
    try:
        write_fd = msvcrt.open_osfhandle(write_handle, 0)
        yield os.fdopen(write_fd, "wb", closefd=False), read_handle
    finally:
        kernel32.CloseHandle(Handle(ffi.cast("HANDLE", read_handle)))
        kernel32.CloseHandle(Handle(ffi.cast("HANDLE", write_handle)))


@restore_unraisablehook()
def test_forgot_to_register_with_iocp() -> None:
    with pipe_with_overlapped_read() as (write_fp, read_handle):
        with write_fp:
            write_fp.write(b"test\n")

        left_run_yet = False

        async def main() -> None:
            target = bytearray(1)
            try:
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(
                        _core.readinto_overlapped,
                        read_handle,
                        target,
                        name="xyz",
                    )
                    await wait_all_tasks_blocked()
                    nursery.cancel_scope.cancel()
            finally:
                # Run loop is exited without unwinding running tasks, so
                # we don't get here until the main() coroutine is GC'ed
                assert left_run_yet

        with pytest.raises(_core.TrioInternalError) as exc_info:
            _core.run(main)
        left_run_yet = True
        assert "Failed to cancel overlapped I/O in xyz " in str(exc_info.value)
        assert "forget to call register_with_iocp()?" in str(exc_info.value)

        # Make sure the Nursery.__del__ assertion about dangling children
        # gets put with the correct test
        del exc_info
        gc_collect_harder()


@slow
async def test_too_late_to_cancel() -> None:
    import time

    with pipe_with_overlapped_read() as (write_fp, read_handle):
        _core.register_with_iocp(read_handle)
        target = bytearray(6)
        async with _core.open_nursery() as nursery:
            # Start an async read in the background
            nursery.start_soon(_core.readinto_overlapped, read_handle, target)
            await wait_all_tasks_blocked()

            # Synchronous write to the other end of the pipe
            with write_fp:
                write_fp.write(b"test1\ntest2\n")

            # Note: not trio.sleep! We're making sure the OS level
            # ReadFile completes, before Trio has a chance to execute
            # another checkpoint and notice it completed.
            time.sleep(1)  # noqa: ASYNC251
            nursery.cancel_scope.cancel()
        assert target[:6] == b"test1\n"

        # Do another I/O to make sure we've actually processed the
        # fallback completion that was posted when CancelIoEx failed.
        assert await _core.readinto_overlapped(read_handle, target) == 6
        assert target[:6] == b"test2\n"


def test_lsp_that_hooks_select_gives_good_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .. import _io_windows
    from .._windows_cffi import CData, WSAIoctls, _handle

    def patched_get_underlying(
        sock: int | CData,
        *,
        which: int = WSAIoctls.SIO_BASE_HANDLE,
    ) -> CData:
        if hasattr(sock, "fileno"):  # pragma: no branch
            sock = sock.fileno()
        if which == WSAIoctls.SIO_BSP_HANDLE_SELECT:
            return _handle(sock + 1)
        else:
            return _handle(sock)

    monkeypatch.setattr(_io_windows, "_get_underlying_socket", patched_get_underlying)
    with pytest.raises(
        RuntimeError,
        match="SIO_BASE_HANDLE and SIO_BSP_HANDLE_SELECT differ",
    ):
        _core.run(sleep, 0)


def test_lsp_that_completely_hides_base_socket_gives_good_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This tests behavior with an LSP that fails SIO_BASE_HANDLE and returns
    # self for SIO_BSP_HANDLE_SELECT (like Komodia), but also returns
    # self for SIO_BSP_HANDLE_POLL. No known LSP does this, but we want to
    # make sure we get an error rather than an infinite loop.

    from .. import _io_windows
    from .._windows_cffi import CData, WSAIoctls, _handle

    def patched_get_underlying(
        sock: int | CData,
        *,
        which: int = WSAIoctls.SIO_BASE_HANDLE,
    ) -> CData:
        if hasattr(sock, "fileno"):  # pragma: no branch
            sock = sock.fileno()
        if which == WSAIoctls.SIO_BASE_HANDLE:
            raise OSError("nope")
        else:
            return _handle(sock)

    monkeypatch.setattr(_io_windows, "_get_underlying_socket", patched_get_underlying)
    with pytest.raises(
        RuntimeError,
        match="SIO_BASE_HANDLE failed and SIO_BSP_HANDLE_POLL didn't return a diff",
    ):
        _core.run(sleep, 0)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\api.py ===
"""Base API."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterator, Literal


class PlatformDirsABC(ABC):  # noqa: PLR0904
    """Abstract base class for platform directories."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        appname: str | None = None,
        appauthor: str | None | Literal[False] = None,
        version: str | None = None,
        roaming: bool = False,  # noqa: FBT001, FBT002
        multipath: bool = False,  # noqa: FBT001, FBT002
        opinion: bool = True,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Create a new platform directory.

        :param appname: See `appname`.
        :param appauthor: See `appauthor`.
        :param version: See `version`.
        :param roaming: See `roaming`.
        :param multipath: See `multipath`.
        :param opinion: See `opinion`.
        :param ensure_exists: See `ensure_exists`.

        """
        self.appname = appname  #: The name of application.
        self.appauthor = appauthor
        """
        The name of the app author or distributing body for this application.

        Typically, it is the owning company name. Defaults to `appname`. You may pass ``False`` to disable it.

        """
        self.version = version
        """
        An optional version path element to append to the path.

        You might want to use this if you want multiple versions of your app to be able to run independently. If used,
        this would typically be ``<major>.<minor>``.

        """
        self.roaming = roaming
        """
        Whether to use the roaming appdata directory on Windows.

        That means that for users on a Windows network setup for roaming profiles, this user data will be synced on
        login (see
        `here <https://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>`_).

        """
        self.multipath = multipath
        """
        An optional parameter which indicates that the entire list of data dirs should be returned.

        By default, the first item would only be returned.

        """
        self.opinion = opinion  #: A flag to indicating to use opinionated values.
        self.ensure_exists = ensure_exists
        """
        Optionally create the directory (and any missing parents) upon access if it does not exist.

        By default, no directories are created.

        """

    def _append_app_name_and_version(self, *base: str) -> str:
        params = list(base[1:])
        if self.appname:
            params.append(self.appname)
            if self.version:
                params.append(self.version)
        path = os.path.join(base[0], *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    def _optionally_create_directory(self, path: str) -> None:
        if self.ensure_exists:
            Path(path).mkdir(parents=True, exist_ok=True)

    def _first_item_as_path_if_multipath(self, directory: str) -> Path:
        if self.multipath:
            # If multipath is True, the first path is returned.
            directory = directory.split(os.pathsep)[0]
        return Path(directory)

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user"""

    @property
    @abstractmethod
    def site_data_dir(self) -> str:
        """:return: data directory shared by users"""

    @property
    @abstractmethod
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user"""

    @property
    @abstractmethod
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users"""

    @property
    @abstractmethod
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user"""

    @property
    @abstractmethod
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users"""

    @property
    @abstractmethod
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user"""

    @property
    @abstractmethod
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user"""

    @property
    @abstractmethod
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user"""

    @property
    @abstractmethod
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user"""

    @property
    @abstractmethod
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user"""

    @property
    @abstractmethod
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user"""

    @property
    @abstractmethod
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user"""

    @property
    @abstractmethod
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user"""

    @property
    @abstractmethod
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user"""

    @property
    @abstractmethod
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users"""

    @property
    def user_data_path(self) -> Path:
        """:return: data path tied to the user"""
        return Path(self.user_data_dir)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users"""
        return Path(self.site_data_dir)

    @property
    def user_config_path(self) -> Path:
        """:return: config path tied to the user"""
        return Path(self.user_config_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users"""
        return Path(self.site_config_dir)

    @property
    def user_cache_path(self) -> Path:
        """:return: cache path tied to the user"""
        return Path(self.user_cache_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users"""
        return Path(self.site_cache_dir)

    @property
    def user_state_path(self) -> Path:
        """:return: state path tied to the user"""
        return Path(self.user_state_dir)

    @property
    def user_log_path(self) -> Path:
        """:return: log path tied to the user"""
        return Path(self.user_log_dir)

    @property
    def user_documents_path(self) -> Path:
        """:return: documents a path tied to the user"""
        return Path(self.user_documents_dir)

    @property
    def user_downloads_path(self) -> Path:
        """:return: downloads path tied to the user"""
        return Path(self.user_downloads_dir)

    @property
    def user_pictures_path(self) -> Path:
        """:return: pictures path tied to the user"""
        return Path(self.user_pictures_dir)

    @property
    def user_videos_path(self) -> Path:
        """:return: videos path tied to the user"""
        return Path(self.user_videos_dir)

    @property
    def user_music_path(self) -> Path:
        """:return: music path tied to the user"""
        return Path(self.user_music_dir)

    @property
    def user_desktop_path(self) -> Path:
        """:return: desktop path tied to the user"""
        return Path(self.user_desktop_dir)

    @property
    def user_runtime_path(self) -> Path:
        """:return: runtime path tied to the user"""
        return Path(self.user_runtime_dir)

    @property
    def site_runtime_path(self) -> Path:
        """:return: runtime path shared by users"""
        return Path(self.site_runtime_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield self.site_config_dir

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield self.site_data_dir

    def iter_cache_dirs(self) -> Iterator[str]:
        """:yield: all user and site cache directories."""
        yield self.user_cache_dir
        yield self.site_cache_dir

    def iter_runtime_dirs(self) -> Iterator[str]:
        """:yield: all user and site runtime directories."""
        yield self.user_runtime_dir
        yield self.site_runtime_dir

    def iter_config_paths(self) -> Iterator[Path]:
        """:yield: all user and site configuration paths."""
        for path in self.iter_config_dirs():
            yield Path(path)

    def iter_data_paths(self) -> Iterator[Path]:
        """:yield: all user and site data paths."""
        for path in self.iter_data_dirs():
            yield Path(path)

    def iter_cache_paths(self) -> Iterator[Path]:
        """:yield: all user and site cache paths."""
        for path in self.iter_cache_dirs():
            yield Path(path)

    def iter_runtime_paths(self) -> Iterator[Path]:
        """:yield: all user and site runtime paths."""
        for path in self.iter_runtime_dirs():
            yield Path(path)

# === NexusCore/openenv\Lib\site-packages\google\api_core\datetime_helpers.py ===
# Copyright 2017 Google LLC
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

"""Helpers for :mod:`datetime`."""

import calendar
import datetime
import re

from google.protobuf import timestamp_pb2


_UTC_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
_RFC3339_MICROS = "%Y-%m-%dT%H:%M:%S.%fZ"
_RFC3339_NO_FRACTION = "%Y-%m-%dT%H:%M:%S"
# datetime.strptime cannot handle nanosecond precision:  parse w/ regex
_RFC3339_NANOS = re.compile(
    r"""
    (?P<no_fraction>
        \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}  # YYYY-MM-DDTHH:MM:SS
    )
    (                                        # Optional decimal part
     \.                                      # decimal point
     (?P<nanos>\d{1,9})                      # nanoseconds, maybe truncated
    )?
    Z                                        # Zulu
""",
    re.VERBOSE,
)


def utcnow():
    """A :meth:`datetime.datetime.utcnow()` alias to allow mocking in tests."""
    return datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)


def to_milliseconds(value):
    """Convert a zone-aware datetime to milliseconds since the unix epoch.

    Args:
        value (datetime.datetime): The datetime to covert.

    Returns:
        int: Milliseconds since the unix epoch.
    """
    micros = to_microseconds(value)
    return micros // 1000


def from_microseconds(value):
    """Convert timestamp in microseconds since the unix epoch to datetime.

    Args:
        value (float): The timestamp to convert, in microseconds.

    Returns:
        datetime.datetime: The datetime object equivalent to the timestamp in
            UTC.
    """
    return _UTC_EPOCH + datetime.timedelta(microseconds=value)


def to_microseconds(value):
    """Convert a datetime to microseconds since the unix epoch.

    Args:
        value (datetime.datetime): The datetime to covert.

    Returns:
        int: Microseconds since the unix epoch.
    """
    if not value.tzinfo:
        value = value.replace(tzinfo=datetime.timezone.utc)
    # Regardless of what timezone is on the value, convert it to UTC.
    value = value.astimezone(datetime.timezone.utc)
    # Convert the datetime to a microsecond timestamp.
    return int(calendar.timegm(value.timetuple()) * 1e6) + value.microsecond


def from_iso8601_date(value):
    """Convert a ISO8601 date string to a date.

    Args:
        value (str): The ISO8601 date string.

    Returns:
        datetime.date: A date equivalent to the date string.
    """
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def from_iso8601_time(value):
    """Convert a zoneless ISO8601 time string to a time.

    Args:
        value (str): The ISO8601 time string.

    Returns:
        datetime.time: A time equivalent to the time string.
    """
    return datetime.datetime.strptime(value, "%H:%M:%S").time()


def from_rfc3339(value):
    """Convert an RFC3339-format timestamp to a native datetime.

    Supported formats include those without fractional seconds, or with
    any fraction up to nanosecond precision.

    .. note::
        Python datetimes do not support nanosecond precision; this function
        therefore truncates such values to microseconds.

    Args:
        value (str): The RFC3339 string to convert.

    Returns:
        datetime.datetime: The datetime object equivalent to the timestamp
        in UTC.

    Raises:
        ValueError: If the timestamp does not match the RFC3339
            regular expression.
    """
    with_nanos = _RFC3339_NANOS.match(value)

    if with_nanos is None:
        raise ValueError(
            "Timestamp: {!r}, does not match pattern: {!r}".format(
                value, _RFC3339_NANOS.pattern
            )
        )

    bare_seconds = datetime.datetime.strptime(
        with_nanos.group("no_fraction"), _RFC3339_NO_FRACTION
    )
    fraction = with_nanos.group("nanos")

    if fraction is None:
        micros = 0
    else:
        scale = 9 - len(fraction)
        nanos = int(fraction) * (10**scale)
        micros = nanos // 1000

    return bare_seconds.replace(microsecond=micros, tzinfo=datetime.timezone.utc)


from_rfc3339_nanos = from_rfc3339  # from_rfc3339_nanos method was deprecated.


def to_rfc3339(value, ignore_zone=True):
    """Convert a datetime to an RFC3339 timestamp string.

    Args:
        value (datetime.datetime):
            The datetime object to be converted to a string.
        ignore_zone (bool): If True, then the timezone (if any) of the
            datetime object is ignored and the datetime is treated as UTC.

    Returns:
        str: The RFC3339 formatted string representing the datetime.
    """
    if not ignore_zone and value.tzinfo is not None:
        # Convert to UTC and remove the time zone info.
        value = value.replace(tzinfo=None) - value.utcoffset()

    return value.strftime(_RFC3339_MICROS)


class DatetimeWithNanoseconds(datetime.datetime):
    """Track nanosecond in addition to normal datetime attrs.

    Nanosecond can be passed only as a keyword argument.
    """

    __slots__ = ("_nanosecond",)

    # pylint: disable=arguments-differ
    def __new__(cls, *args, **kw):
        nanos = kw.pop("nanosecond", 0)
        if nanos > 0:
            if "microsecond" in kw:
                raise TypeError("Specify only one of 'microsecond' or 'nanosecond'")
            kw["microsecond"] = nanos // 1000
        inst = datetime.datetime.__new__(cls, *args, **kw)
        inst._nanosecond = nanos or 0
        return inst

    # pylint: disable=arguments-differ

    @property
    def nanosecond(self):
        """Read-only: nanosecond precision."""
        return self._nanosecond

    def rfc3339(self):
        """Return an RFC3339-compliant timestamp.

        Returns:
            (str): Timestamp string according to RFC3339 spec.
        """
        if self._nanosecond == 0:
            return to_rfc3339(self)
        nanos = str(self._nanosecond).rjust(9, "0").rstrip("0")
        return "{}.{}Z".format(self.strftime(_RFC3339_NO_FRACTION), nanos)

    @classmethod
    def from_rfc3339(cls, stamp):
        """Parse RFC3339-compliant timestamp, preserving nanoseconds.

        Args:
            stamp (str): RFC3339 stamp, with up to nanosecond precision

        Returns:
            :class:`DatetimeWithNanoseconds`:
                an instance matching the timestamp string

        Raises:
            ValueError: if `stamp` does not match the expected format
        """
        with_nanos = _RFC3339_NANOS.match(stamp)
        if with_nanos is None:
            raise ValueError(
                "Timestamp: {}, does not match pattern: {}".format(
                    stamp, _RFC3339_NANOS.pattern
                )
            )
        bare = datetime.datetime.strptime(
            with_nanos.group("no_fraction"), _RFC3339_NO_FRACTION
        )
        fraction = with_nanos.group("nanos")
        if fraction is None:
            nanos = 0
        else:
            scale = 9 - len(fraction)
            nanos = int(fraction) * (10**scale)
        return cls(
            bare.year,
            bare.month,
            bare.day,
            bare.hour,
            bare.minute,
            bare.second,
            nanosecond=nanos,
            tzinfo=datetime.timezone.utc,
        )

    def timestamp_pb(self):
        """Return a timestamp message.

        Returns:
            (:class:`~google.protobuf.timestamp_pb2.Timestamp`): Timestamp message
        """
        inst = (
            self
            if self.tzinfo is not None
            else self.replace(tzinfo=datetime.timezone.utc)
        )
        delta = inst - _UTC_EPOCH
        seconds = int(delta.total_seconds())
        nanos = self._nanosecond or self.microsecond * 1000
        return timestamp_pb2.Timestamp(seconds=seconds, nanos=nanos)

    @classmethod
    def from_timestamp_pb(cls, stamp):
        """Parse RFC3339-compliant timestamp, preserving nanoseconds.

        Args:
            stamp (:class:`~google.protobuf.timestamp_pb2.Timestamp`): timestamp message

        Returns:
            :class:`DatetimeWithNanoseconds`:
                an instance matching the timestamp message
        """
        microseconds = int(stamp.seconds * 1e6)
        bare = from_microseconds(microseconds)
        return cls(
            bare.year,
            bare.month,
            bare.day,
            bare.hour,
            bare.minute,
            bare.second,
            nanosecond=stamp.nanos,
            tzinfo=datetime.timezone.utc,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\session_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, TypeAlias, TypedDict

__all__ = [
    "SessionCreateParams",
    "ClientSecret",
    "ClientSecretExpiresAt",
    "InputAudioNoiseReduction",
    "InputAudioTranscription",
    "Tool",
    "Tracing",
    "TracingTracingConfiguration",
    "TurnDetection",
]


class SessionCreateParams(TypedDict, total=False):
    client_secret: ClientSecret
    """Configuration options for the generated client secret."""

    input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: InputAudioNoiseReduction
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: InputAudioTranscription
    """
    Configuration for input audio transcription, defaults to off and can be set to
    `null` to turn off once on. Input audio transcription is not native to the
    model, since the model consumes audio directly. Transcription runs
    asynchronously through
    [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
    and should be treated as guidance of input audio content rather than precisely
    what the model heard. The client can optionally set the language and prompt for
    transcription, these offer additional guidance to the transcription service.
    """

    instructions: str
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"]]
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    modalities: List[Literal["text", "audio"]]
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    model: Literal[
        "gpt-4o-realtime-preview",
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview-2025-06-03",
        "gpt-4o-mini-realtime-preview",
        "gpt-4o-mini-realtime-preview-2024-12-17",
    ]
    """The Realtime model used for this session."""

    output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of output audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, output audio is
    sampled at a rate of 24kHz.
    """

    speed: float
    """The speed of the model's spoken response.

    1.0 is the default speed. 0.25 is the minimum speed. 1.5 is the maximum speed.
    This value can only be changed in between model turns, not while a response is
    in progress.
    """

    temperature: float
    """Sampling temperature for the model, limited to [0.6, 1.2].

    For audio models a temperature of 0.8 is highly recommended for best
    performance.
    """

    tool_choice: str
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function.
    """

    tools: Iterable[Tool]
    """Tools (functions) available to the model."""

    tracing: Tracing
    """Configuration options for tracing.

    Set to null to disable tracing. Once tracing is enabled for a session, the
    configuration cannot be modified.

    `auto` will create a trace for the session with default values for the workflow
    name, group id, and metadata.
    """

    turn_detection: TurnDetection
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """

    voice: Union[
        str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
    ]
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and `verse`.
    """


class ClientSecretExpiresAt(TypedDict, total=False):
    anchor: Literal["created_at"]
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: int
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class ClientSecret(TypedDict, total=False):
    expires_at: ClientSecretExpiresAt
    """Configuration for the ephemeral token expiration."""


class InputAudioNoiseReduction(TypedDict, total=False):
    type: Literal["near_field", "far_field"]
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class InputAudioTranscription(TypedDict, total=False):
    language: str
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: str
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: str
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class Tool(TypedDict, total=False):
    description: str
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: str
    """The name of the function."""

    parameters: object
    """Parameters of the function in JSON Schema."""

    type: Literal["function"]
    """The type of the tool, i.e. `function`."""


class TracingTracingConfiguration(TypedDict, total=False):
    group_id: str
    """
    The group id to attach to this trace to enable filtering and grouping in the
    traces dashboard.
    """

    metadata: object
    """
    The arbitrary metadata to attach to this trace to enable filtering in the traces
    dashboard.
    """

    workflow_name: str
    """The name of the workflow to attach to this trace.

    This is used to name the trace in the traces dashboard.
    """


Tracing: TypeAlias = Union[Literal["auto"], TracingTracingConfiguration]


class TurnDetection(TypedDict, total=False):
    create_response: bool
    """
    Whether or not to automatically generate a response when a VAD stop event
    occurs.
    """

    eagerness: Literal["low", "medium", "high", "auto"]
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: bool
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs.
    """

    prefix_padding_ms: int
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: int
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: float
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Literal["server_vad", "semantic_vad"]
    """Type of turn detection."""

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\api.py ===
"""Base API."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterator, Literal


class PlatformDirsABC(ABC):  # noqa: PLR0904
    """Abstract base class for platform directories."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        appname: str | None = None,
        appauthor: str | None | Literal[False] = None,
        version: str | None = None,
        roaming: bool = False,  # noqa: FBT001, FBT002
        multipath: bool = False,  # noqa: FBT001, FBT002
        opinion: bool = True,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Create a new platform directory.

        :param appname: See `appname`.
        :param appauthor: See `appauthor`.
        :param version: See `version`.
        :param roaming: See `roaming`.
        :param multipath: See `multipath`.
        :param opinion: See `opinion`.
        :param ensure_exists: See `ensure_exists`.

        """
        self.appname = appname  #: The name of application.
        self.appauthor = appauthor
        """
        The name of the app author or distributing body for this application.

        Typically, it is the owning company name. Defaults to `appname`. You may pass ``False`` to disable it.

        """
        self.version = version
        """
        An optional version path element to append to the path.

        You might want to use this if you want multiple versions of your app to be able to run independently. If used,
        this would typically be ``<major>.<minor>``.

        """
        self.roaming = roaming
        """
        Whether to use the roaming appdata directory on Windows.

        That means that for users on a Windows network setup for roaming profiles, this user data will be synced on
        login (see
        `here <https://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>`_).

        """
        self.multipath = multipath
        """
        An optional parameter which indicates that the entire list of data dirs should be returned.

        By default, the first item would only be returned.

        """
        self.opinion = opinion  #: A flag to indicating to use opinionated values.
        self.ensure_exists = ensure_exists
        """
        Optionally create the directory (and any missing parents) upon access if it does not exist.

        By default, no directories are created.

        """

    def _append_app_name_and_version(self, *base: str) -> str:
        params = list(base[1:])
        if self.appname:
            params.append(self.appname)
            if self.version:
                params.append(self.version)
        path = os.path.join(base[0], *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    def _optionally_create_directory(self, path: str) -> None:
        if self.ensure_exists:
            Path(path).mkdir(parents=True, exist_ok=True)

    def _first_item_as_path_if_multipath(self, directory: str) -> Path:
        if self.multipath:
            # If multipath is True, the first path is returned.
            directory = directory.split(os.pathsep)[0]
        return Path(directory)

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user"""

    @property
    @abstractmethod
    def site_data_dir(self) -> str:
        """:return: data directory shared by users"""

    @property
    @abstractmethod
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user"""

    @property
    @abstractmethod
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users"""

    @property
    @abstractmethod
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user"""

    @property
    @abstractmethod
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users"""

    @property
    @abstractmethod
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user"""

    @property
    @abstractmethod
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user"""

    @property
    @abstractmethod
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user"""

    @property
    @abstractmethod
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user"""

    @property
    @abstractmethod
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user"""

    @property
    @abstractmethod
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user"""

    @property
    @abstractmethod
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user"""

    @property
    @abstractmethod
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user"""

    @property
    @abstractmethod
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user"""

    @property
    @abstractmethod
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users"""

    @property
    def user_data_path(self) -> Path:
        """:return: data path tied to the user"""
        return Path(self.user_data_dir)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users"""
        return Path(self.site_data_dir)

    @property
    def user_config_path(self) -> Path:
        """:return: config path tied to the user"""
        return Path(self.user_config_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users"""
        return Path(self.site_config_dir)

    @property
    def user_cache_path(self) -> Path:
        """:return: cache path tied to the user"""
        return Path(self.user_cache_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users"""
        return Path(self.site_cache_dir)

    @property
    def user_state_path(self) -> Path:
        """:return: state path tied to the user"""
        return Path(self.user_state_dir)

    @property
    def user_log_path(self) -> Path:
        """:return: log path tied to the user"""
        return Path(self.user_log_dir)

    @property
    def user_documents_path(self) -> Path:
        """:return: documents a path tied to the user"""
        return Path(self.user_documents_dir)

    @property
    def user_downloads_path(self) -> Path:
        """:return: downloads path tied to the user"""
        return Path(self.user_downloads_dir)

    @property
    def user_pictures_path(self) -> Path:
        """:return: pictures path tied to the user"""
        return Path(self.user_pictures_dir)

    @property
    def user_videos_path(self) -> Path:
        """:return: videos path tied to the user"""
        return Path(self.user_videos_dir)

    @property
    def user_music_path(self) -> Path:
        """:return: music path tied to the user"""
        return Path(self.user_music_dir)

    @property
    def user_desktop_path(self) -> Path:
        """:return: desktop path tied to the user"""
        return Path(self.user_desktop_dir)

    @property
    def user_runtime_path(self) -> Path:
        """:return: runtime path tied to the user"""
        return Path(self.user_runtime_dir)

    @property
    def site_runtime_path(self) -> Path:
        """:return: runtime path shared by users"""
        return Path(self.site_runtime_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield self.site_config_dir

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield self.site_data_dir

    def iter_cache_dirs(self) -> Iterator[str]:
        """:yield: all user and site cache directories."""
        yield self.user_cache_dir
        yield self.site_cache_dir

    def iter_runtime_dirs(self) -> Iterator[str]:
        """:yield: all user and site runtime directories."""
        yield self.user_runtime_dir
        yield self.site_runtime_dir

    def iter_config_paths(self) -> Iterator[Path]:
        """:yield: all user and site configuration paths."""
        for path in self.iter_config_dirs():
            yield Path(path)

    def iter_data_paths(self) -> Iterator[Path]:
        """:yield: all user and site data paths."""
        for path in self.iter_data_dirs():
            yield Path(path)

    def iter_cache_paths(self) -> Iterator[Path]:
        """:yield: all user and site cache paths."""
        for path in self.iter_cache_dirs():
            yield Path(path)

    def iter_runtime_paths(self) -> Iterator[Path]:
        """:yield: all user and site runtime paths."""
        for path in self.iter_runtime_dirs():
            yield Path(path)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\webidl.py ===
"""
    pygments.lexers.webidl
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Web IDL, including some extensions.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, default, include, words
from pygments.token import Comment, Keyword, Name, Number, Punctuation, \
    String, Text

__all__ = ['WebIDLLexer']

_builtin_types = (
    # primitive types
    'byte', 'octet', 'boolean',
    r'(?:unsigned\s+)?(?:short|long(?:\s+long)?)',
    r'(?:unrestricted\s+)?(?:float|double)',
    # string types
    'DOMString', 'ByteString', 'USVString',
    # exception types
    'Error', 'DOMException',
    # typed array types
    'Uint8Array', 'Uint16Array', 'Uint32Array', 'Uint8ClampedArray',
    'Float32Array', 'Float64Array',
    # buffer source types
    'ArrayBuffer', 'DataView', 'Int8Array', 'Int16Array', 'Int32Array',
    # other
    'any', 'void', 'object', 'RegExp',
)
_identifier = r'_?[A-Za-z][a-zA-Z0-9_-]*'
_keyword_suffix = r'(?![\w-])'
_string = r'"[^"]*"'


class WebIDLLexer(RegexLexer):
    """
    For Web IDL.
    """

    name = 'Web IDL'
    url = 'https://www.w3.org/wiki/Web_IDL'
    aliases = ['webidl']
    filenames = ['*.webidl']
    version_added = '2.6'

    tokens = {
        'common': [
            (r'\s+', Text),
            (r'(?s)/\*.*?\*/', Comment.Multiline),
            (r'//.*', Comment.Single),
            (r'^#.*', Comment.Preproc),
        ],
        'root': [
            include('common'),
            (r'\[', Punctuation, 'extended_attributes'),
            (r'partial' + _keyword_suffix, Keyword),
            (r'typedef' + _keyword_suffix, Keyword, ('typedef', 'type')),
            (r'interface' + _keyword_suffix, Keyword, 'interface_rest'),
            (r'enum' + _keyword_suffix, Keyword, 'enum_rest'),
            (r'callback' + _keyword_suffix, Keyword, 'callback_rest'),
            (r'dictionary' + _keyword_suffix, Keyword, 'dictionary_rest'),
            (r'namespace' + _keyword_suffix, Keyword, 'namespace_rest'),
            (_identifier, Name.Class, 'implements_rest'),
        ],
        'extended_attributes': [
            include('common'),
            (r',', Punctuation),
            (_identifier, Name.Decorator),
            (r'=', Punctuation, 'extended_attribute_rest'),
            (r'\(', Punctuation, 'argument_list'),
            (r'\]', Punctuation, '#pop'),
        ],
        'extended_attribute_rest': [
            include('common'),
            (_identifier, Name, 'extended_attribute_named_rest'),
            (_string, String),
            (r'\(', Punctuation, 'identifier_list'),
            default('#pop'),
        ],
        'extended_attribute_named_rest': [
            include('common'),
            (r'\(', Punctuation, 'argument_list'),
            default('#pop'),
        ],
        'argument_list': [
            include('common'),
            (r'\)', Punctuation, '#pop'),
            default('argument'),
        ],
        'argument': [
            include('common'),
            (r'optional' + _keyword_suffix, Keyword),
            (r'\[', Punctuation, 'extended_attributes'),
            (r',', Punctuation, '#pop'),
            (r'\)', Punctuation, '#pop:2'),
            default(('argument_rest', 'type'))
        ],
        'argument_rest': [
            include('common'),
            (_identifier, Name.Variable),
            (r'\.\.\.', Punctuation),
            (r'=', Punctuation, 'default_value'),
            default('#pop'),
        ],
        'identifier_list': [
            include('common'),
            (_identifier, Name.Class),
            (r',', Punctuation),
            (r'\)', Punctuation, '#pop'),
        ],
        'type': [
            include('common'),
            (r'(?:' + r'|'.join(_builtin_types) + r')' + _keyword_suffix,
             Keyword.Type, 'type_null'),
            (words(('sequence', 'Promise', 'FrozenArray'),
                   suffix=_keyword_suffix), Keyword.Type, 'type_identifier'),
            (_identifier, Name.Class, 'type_identifier'),
            (r'\(', Punctuation, 'union_type'),
        ],
        'union_type': [
            include('common'),
            (r'or' + _keyword_suffix, Keyword),
            (r'\)', Punctuation, ('#pop', 'type_null')),
            default('type'),
        ],
        'type_identifier': [
            (r'<', Punctuation, 'type_list'),
            default(('#pop', 'type_null'))
        ],
        'type_null': [
            (r'\?', Punctuation),
            default('#pop:2'),
        ],
        'default_value': [
            include('common'),
            include('const_value'),
            (_string, String, '#pop'),
            (r'\[\s*\]', Punctuation, '#pop'),
        ],
        'const_value': [
            include('common'),
            (words(('true', 'false', '-Infinity', 'Infinity', 'NaN', 'null'),
                   suffix=_keyword_suffix), Keyword.Constant, '#pop'),
            (r'-?(?:(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)(?:[Ee][+-]?[0-9]+)?' +
             r'|[0-9]+[Ee][+-]?[0-9]+)', Number.Float, '#pop'),
            (r'-?[1-9][0-9]*', Number.Integer, '#pop'),
            (r'-?0[Xx][0-9A-Fa-f]+', Number.Hex, '#pop'),
            (r'-?0[0-7]*', Number.Oct, '#pop'),
        ],
        'typedef': [
            include('common'),
            (_identifier, Name.Class),
            (r';', Punctuation, '#pop'),
        ],
        'namespace_rest': [
            include('common'),
            (_identifier, Name.Namespace),
            (r'\{', Punctuation, 'namespace_body'),
            (r';', Punctuation, '#pop'),
        ],
        'namespace_body': [
            include('common'),
            (r'\[', Punctuation, 'extended_attributes'),
            (r'readonly' + _keyword_suffix, Keyword),
            (r'attribute' + _keyword_suffix,
             Keyword, ('attribute_rest', 'type')),
            (r'const' + _keyword_suffix, Keyword, ('const_rest', 'type')),
            (r'\}', Punctuation, '#pop'),
            default(('operation_rest', 'type')),
        ],
        'interface_rest': [
            include('common'),
            (_identifier, Name.Class),
            (r':', Punctuation),
            (r'\{', Punctuation, 'interface_body'),
            (r';', Punctuation, '#pop'),
        ],
        'interface_body': [
            (words(('iterable', 'maplike', 'setlike'), suffix=_keyword_suffix),
             Keyword, 'iterable_maplike_setlike_rest'),
            (words(('setter', 'getter', 'creator', 'deleter', 'legacycaller',
                    'inherit', 'static', 'stringifier', 'jsonifier'),
                   suffix=_keyword_suffix), Keyword),
            (r'serializer' + _keyword_suffix, Keyword, 'serializer_rest'),
            (r';', Punctuation),
            include('namespace_body'),
        ],
        'attribute_rest': [
            include('common'),
            (_identifier, Name.Variable),
            (r';', Punctuation, '#pop'),
        ],
        'const_rest': [
            include('common'),
            (_identifier, Name.Constant),
            (r'=', Punctuation, 'const_value'),
            (r';', Punctuation, '#pop'),
        ],
        'operation_rest': [
            include('common'),
            (r';', Punctuation, '#pop'),
            default('operation'),
        ],
        'operation': [
            include('common'),
            (_identifier, Name.Function),
            (r'\(', Punctuation, 'argument_list'),
            (r';', Punctuation, '#pop:2'),
        ],
        'iterable_maplike_setlike_rest': [
            include('common'),
            (r'<', Punctuation, 'type_list'),
            (r';', Punctuation, '#pop'),
        ],
        'type_list': [
            include('common'),
            (r',', Punctuation),
            (r'>', Punctuation, '#pop'),
            default('type'),
        ],
        'serializer_rest': [
            include('common'),
            (r'=', Punctuation, 'serialization_pattern'),
            (r';', Punctuation, '#pop'),
            default('operation'),
        ],
        'serialization_pattern': [
            include('common'),
            (_identifier, Name.Variable, '#pop'),
            (r'\{', Punctuation, 'serialization_pattern_map'),
            (r'\[', Punctuation, 'serialization_pattern_list'),
        ],
        'serialization_pattern_map': [
            include('common'),
            (words(('getter', 'inherit', 'attribute'),
                   suffix=_keyword_suffix), Keyword),
            (r',', Punctuation),
            (_identifier, Name.Variable),
            (r'\}', Punctuation, '#pop:2'),
        ],
        'serialization_pattern_list': [
            include('common'),
            (words(('getter', 'attribute'), suffix=_keyword_suffix), Keyword),
            (r',', Punctuation),
            (_identifier, Name.Variable),
            (r']', Punctuation, '#pop:2'),
        ],
        'enum_rest': [
            include('common'),
            (_identifier, Name.Class),
            (r'\{', Punctuation, 'enum_body'),
            (r';', Punctuation, '#pop'),
        ],
        'enum_body': [
            include('common'),
            (_string, String),
            (r',', Punctuation),
            (r'\}', Punctuation, '#pop'),
        ],
        'callback_rest': [
            include('common'),
            (r'interface' + _keyword_suffix,
             Keyword, ('#pop', 'interface_rest')),
            (_identifier, Name.Class),
            (r'=', Punctuation, ('operation', 'type')),
            (r';', Punctuation, '#pop'),
        ],
        'dictionary_rest': [
            include('common'),
            (_identifier, Name.Class),
            (r':', Punctuation),
            (r'\{', Punctuation, 'dictionary_body'),
            (r';', Punctuation, '#pop'),
        ],
        'dictionary_body': [
            include('common'),
            (r'\[', Punctuation, 'extended_attributes'),
            (r'required' + _keyword_suffix, Keyword),
            (r'\}', Punctuation, '#pop'),
            default(('dictionary_item', 'type')),
        ],
        'dictionary_item': [
            include('common'),
            (_identifier, Name.Variable),
            (r'=', Punctuation, 'default_value'),
            (r';', Punctuation, '#pop'),
        ],
        'implements_rest': [
            include('common'),
            (r'implements' + _keyword_suffix, Keyword),
            (_identifier, Name.Class),
            (r';', Punctuation, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\tornado\test\asyncio_test.py ===
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

import asyncio
import contextvars
import threading
import time
import unittest
import warnings

from concurrent.futures import ThreadPoolExecutor
import tornado.platform.asyncio
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import (
    AsyncIOLoop,
    to_asyncio_future,
    AddThreadSelectorEventLoop,
)
from tornado.testing import (
    AsyncTestCase,
    gen_test,
    setup_with_context_manager,
    AsyncHTTPTestCase,
)
from tornado.test.util import ignore_deprecation
from tornado.web import Application, RequestHandler


class AsyncIOLoopTest(AsyncTestCase):
    @property
    def asyncio_loop(self):
        return self.io_loop.asyncio_loop  # type: ignore

    def test_asyncio_callback(self):
        # Basic test that the asyncio loop is set up correctly.
        async def add_callback():
            asyncio.get_event_loop().call_soon(self.stop)

        self.asyncio_loop.run_until_complete(add_callback())
        self.wait()

    @gen_test
    def test_asyncio_future(self):
        # Test that we can yield an asyncio future from a tornado coroutine.
        # Without 'yield from', we must wrap coroutines in ensure_future.
        x = yield asyncio.ensure_future(
            asyncio.get_event_loop().run_in_executor(None, lambda: 42)
        )
        self.assertEqual(x, 42)

    @gen_test
    def test_asyncio_yield_from(self):
        @gen.coroutine
        def f():
            event_loop = asyncio.get_event_loop()
            x = yield from event_loop.run_in_executor(None, lambda: 42)
            return x

        result = yield f()
        self.assertEqual(result, 42)

    def test_asyncio_adapter(self):
        # This test demonstrates that when using the asyncio coroutine
        # runner (i.e. run_until_complete), the to_asyncio_future
        # adapter is needed. No adapter is needed in the other direction,
        # as demonstrated by other tests in the package.
        @gen.coroutine
        def tornado_coroutine():
            yield gen.moment
            raise gen.Return(42)

        async def native_coroutine_without_adapter():
            return await tornado_coroutine()

        async def native_coroutine_with_adapter():
            return await to_asyncio_future(tornado_coroutine())

        # Use the adapter, but two degrees from the tornado coroutine.
        async def native_coroutine_with_adapter2():
            return await to_asyncio_future(native_coroutine_without_adapter())

        # Tornado supports native coroutines both with and without adapters
        self.assertEqual(self.io_loop.run_sync(native_coroutine_without_adapter), 42)
        self.assertEqual(self.io_loop.run_sync(native_coroutine_with_adapter), 42)
        self.assertEqual(self.io_loop.run_sync(native_coroutine_with_adapter2), 42)

        # Asyncio only supports coroutines that yield asyncio-compatible
        # Futures (which our Future is since 5.0).
        self.assertEqual(
            self.asyncio_loop.run_until_complete(native_coroutine_without_adapter()),
            42,
        )
        self.assertEqual(
            self.asyncio_loop.run_until_complete(native_coroutine_with_adapter()),
            42,
        )
        self.assertEqual(
            self.asyncio_loop.run_until_complete(native_coroutine_with_adapter2()),
            42,
        )

    def test_add_thread_close_idempotent(self):
        loop = AddThreadSelectorEventLoop(asyncio.get_event_loop())  # type: ignore
        loop.close()
        loop.close()


class LeakTest(unittest.TestCase):
    def setUp(self):
        # Trigger a cleanup of the mapping so we start with a clean slate.
        AsyncIOLoop(make_current=False).close()

    def tearDown(self):
        try:
            loop = asyncio.get_event_loop_policy().get_event_loop()
        except Exception:
            # We may not have a current event loop at this point.
            pass
        else:
            loop.close()

    def test_ioloop_close_leak(self):
        orig_count = len(IOLoop._ioloop_for_asyncio)
        for i in range(10):
            # Create and close an AsyncIOLoop using Tornado interfaces.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                loop = AsyncIOLoop()
                loop.close()
        new_count = len(IOLoop._ioloop_for_asyncio) - orig_count
        self.assertEqual(new_count, 0)

    def test_asyncio_close_leak(self):
        orig_count = len(IOLoop._ioloop_for_asyncio)
        for i in range(10):
            # Create and close an AsyncIOMainLoop using asyncio interfaces.
            loop = asyncio.new_event_loop()
            loop.call_soon(IOLoop.current)
            loop.call_soon(loop.stop)
            loop.run_forever()
            loop.close()
        new_count = len(IOLoop._ioloop_for_asyncio) - orig_count
        # Because the cleanup is run on new loop creation, we have one
        # dangling entry in the map (but only one).
        self.assertEqual(new_count, 1)


class SelectorThreadLeakTest(unittest.TestCase):
    # These tests are only relevant on windows, but they should pass anywhere.
    def setUp(self):
        # As a precaution, ensure that we've run an event loop at least once
        # so if it spins up any singleton threads they're already there.
        asyncio.run(self.dummy_tornado_coroutine())
        self.orig_thread_count = threading.active_count()

    def assert_no_thread_leak(self):
        # For some reason we see transient failures here, but I haven't been able
        # to catch it to identify which thread is causing it. Whatever thread it
        # is, it appears to quickly clean up on its own, so just retry a few times.
        # At least some of the time the errant thread was running at the time we
        # captured self.orig_thread_count, so use inequalities.
        deadline = time.time() + 1
        while time.time() < deadline:
            threads = list(threading.enumerate())
            if len(threads) <= self.orig_thread_count:
                break
            time.sleep(0.1)
        self.assertLessEqual(len(threads), self.orig_thread_count, threads)

    async def dummy_tornado_coroutine(self):
        # Just access the IOLoop to initialize the selector thread.
        IOLoop.current()

    def test_asyncio_run(self):
        for i in range(10):
            # asyncio.run calls shutdown_asyncgens for us.
            asyncio.run(self.dummy_tornado_coroutine())
        self.assert_no_thread_leak()

    def test_asyncio_manual(self):
        for i in range(10):
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.dummy_tornado_coroutine())
            # Without this step, we'd leak the thread.
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        self.assert_no_thread_leak()

    def test_tornado(self):
        for i in range(10):
            # The IOLoop interfaces are aware of the selector thread and
            # (synchronously) shut it down.
            loop = IOLoop(make_current=False)
            loop.run_sync(self.dummy_tornado_coroutine)
            loop.close()
        self.assert_no_thread_leak()


class AnyThreadEventLoopPolicyTest(unittest.TestCase):
    def setUp(self):
        setup_with_context_manager(self, ignore_deprecation())
        # Referencing the event loop policy attributes raises deprecation warnings,
        # so instead of importing this at the top of the file we capture it here.
        self.AnyThreadEventLoopPolicy = (
            tornado.platform.asyncio.AnyThreadEventLoopPolicy
        )
        self.orig_policy = asyncio.get_event_loop_policy()
        self.executor = ThreadPoolExecutor(1)

    def tearDown(self):
        asyncio.set_event_loop_policy(self.orig_policy)
        self.executor.shutdown()

    def get_event_loop_on_thread(self):
        def get_and_close_event_loop():
            """Get the event loop. Close it if one is returned.

            Returns the (closed) event loop. This is a silly thing
            to do and leaves the thread in a broken state, but it's
            enough for this test. Closing the loop avoids resource
            leak warnings.
            """
            loop = asyncio.get_event_loop()
            loop.close()
            return loop

        future = self.executor.submit(get_and_close_event_loop)
        return future.result()

    def test_asyncio_accessor(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # With the default policy, non-main threads don't get an event
            # loop.
            self.assertRaises(
                RuntimeError, self.executor.submit(asyncio.get_event_loop).result
            )
            # Set the policy and we can get a loop.
            asyncio.set_event_loop_policy(self.AnyThreadEventLoopPolicy())
            self.assertIsInstance(
                self.executor.submit(asyncio.get_event_loop).result(),
                asyncio.AbstractEventLoop,
            )
            # Clean up to silence leak warnings. Always use asyncio since
            # IOLoop doesn't (currently) close the underlying loop.
            self.executor.submit(lambda: asyncio.get_event_loop().close()).result()  # type: ignore

    def test_tornado_accessor(self):
        # Tornado's IOLoop.current() API can create a loop for any thread,
        # regardless of this event loop policy.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.assertIsInstance(self.executor.submit(IOLoop.current).result(), IOLoop)
            # Clean up to silence leak warnings. Always use asyncio since
            # IOLoop doesn't (currently) close the underlying loop.
            self.executor.submit(lambda: asyncio.get_event_loop().close()).result()  # type: ignore

            asyncio.set_event_loop_policy(self.AnyThreadEventLoopPolicy())
            self.assertIsInstance(self.executor.submit(IOLoop.current).result(), IOLoop)
            self.executor.submit(lambda: asyncio.get_event_loop().close()).result()  # type: ignore


class SelectorThreadContextvarsTest(AsyncHTTPTestCase):
    ctx_value = "foo"
    test_endpoint = "/"
    tornado_test_ctx = contextvars.ContextVar("tornado_test_ctx", default="default")
    tornado_test_ctx.set(ctx_value)

    def get_app(self) -> Application:
        tornado_test_ctx = self.tornado_test_ctx

        class Handler(RequestHandler):
            async def get(self):
                # On the Windows platform,
                # when a asyncio.events.Handle is created
                # in the SelectorThread without providing a context,
                # it will copy the current thread's context,
                # which can lead to the loss of the main thread's context
                # when executing the handle.
                # Therefore, it is necessary to
                # save a copy of the main thread's context in the SelectorThread
                # for creating the handle.
                self.write(tornado_test_ctx.get())

        return Application([(self.test_endpoint, Handler)])

    def test_context_vars(self):
        self.assertEqual(self.ctx_value, self.fetch(self.test_endpoint).body.decode())

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\logging.py ===
import logging
from datetime import datetime
from logging import Handler, LogRecord
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Iterable, List, Optional, Type, Union

from pip._vendor.rich._null_file import NullFile

from . import get_console
from ._log_render import FormatTimeCallable, LogRender
from .console import Console, ConsoleRenderable
from .highlighter import Highlighter, ReprHighlighter
from .text import Text
from .traceback import Traceback


class RichHandler(Handler):
    """A logging handler that renders output with Rich. The time / level / message and file are displayed in columns.
    The level is color coded, and the message is syntax highlighted.

    Note:
        Be careful when enabling console markup in log messages if you have configured logging for libraries not
        under your control. If a dependency writes messages containing square brackets, it may not produce the intended output.

    Args:
        level (Union[int, str], optional): Log level. Defaults to logging.NOTSET.
        console (:class:`~rich.console.Console`, optional): Optional console instance to write logs.
            Default will use a global console instance writing to stdout.
        show_time (bool, optional): Show a column for the time. Defaults to True.
        omit_repeated_times (bool, optional): Omit repetition of the same time. Defaults to True.
        show_level (bool, optional): Show a column for the level. Defaults to True.
        show_path (bool, optional): Show the path to the original log call. Defaults to True.
        enable_link_path (bool, optional): Enable terminal link of path column to file. Defaults to True.
        highlighter (Highlighter, optional): Highlighter to style log messages, or None to use ReprHighlighter. Defaults to None.
        markup (bool, optional): Enable console markup in log messages. Defaults to False.
        rich_tracebacks (bool, optional): Enable rich tracebacks with syntax highlighting and formatting. Defaults to False.
        tracebacks_width (Optional[int], optional): Number of characters used to render tracebacks, or None for full width. Defaults to None.
        tracebacks_code_width (int, optional): Number of code characters used to render tracebacks, or None for full width. Defaults to 88.
        tracebacks_extra_lines (int, optional): Additional lines of code to render tracebacks, or None for full width. Defaults to None.
        tracebacks_theme (str, optional): Override pygments theme used in traceback.
        tracebacks_word_wrap (bool, optional): Enable word wrapping of long tracebacks lines. Defaults to True.
        tracebacks_show_locals (bool, optional): Enable display of locals in tracebacks. Defaults to False.
        tracebacks_suppress (Sequence[Union[str, ModuleType]]): Optional sequence of modules or paths to exclude from traceback.
        tracebacks_max_frames (int, optional): Optional maximum number of frames returned by traceback.
        locals_max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to 10.
        locals_max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to 80.
        log_time_format (Union[str, TimeFormatterCallable], optional): If ``log_time`` is enabled, either string for strftime or callable that formats the time. Defaults to "[%x %X] ".
        keywords (List[str], optional): List of words to highlight instead of ``RichHandler.KEYWORDS``.
    """

    KEYWORDS: ClassVar[Optional[List[str]]] = [
        "GET",
        "POST",
        "HEAD",
        "PUT",
        "DELETE",
        "OPTIONS",
        "TRACE",
        "PATCH",
    ]
    HIGHLIGHTER_CLASS: ClassVar[Type[Highlighter]] = ReprHighlighter

    def __init__(
        self,
        level: Union[int, str] = logging.NOTSET,
        console: Optional[Console] = None,
        *,
        show_time: bool = True,
        omit_repeated_times: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        enable_link_path: bool = True,
        highlighter: Optional[Highlighter] = None,
        markup: bool = False,
        rich_tracebacks: bool = False,
        tracebacks_width: Optional[int] = None,
        tracebacks_code_width: int = 88,
        tracebacks_extra_lines: int = 3,
        tracebacks_theme: Optional[str] = None,
        tracebacks_word_wrap: bool = True,
        tracebacks_show_locals: bool = False,
        tracebacks_suppress: Iterable[Union[str, ModuleType]] = (),
        tracebacks_max_frames: int = 100,
        locals_max_length: int = 10,
        locals_max_string: int = 80,
        log_time_format: Union[str, FormatTimeCallable] = "[%x %X]",
        keywords: Optional[List[str]] = None,
    ) -> None:
        super().__init__(level=level)
        self.console = console or get_console()
        self.highlighter = highlighter or self.HIGHLIGHTER_CLASS()
        self._log_render = LogRender(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            time_format=log_time_format,
            omit_repeated_times=omit_repeated_times,
            level_width=None,
        )
        self.enable_link_path = enable_link_path
        self.markup = markup
        self.rich_tracebacks = rich_tracebacks
        self.tracebacks_width = tracebacks_width
        self.tracebacks_extra_lines = tracebacks_extra_lines
        self.tracebacks_theme = tracebacks_theme
        self.tracebacks_word_wrap = tracebacks_word_wrap
        self.tracebacks_show_locals = tracebacks_show_locals
        self.tracebacks_suppress = tracebacks_suppress
        self.tracebacks_max_frames = tracebacks_max_frames
        self.tracebacks_code_width = tracebacks_code_width
        self.locals_max_length = locals_max_length
        self.locals_max_string = locals_max_string
        self.keywords = keywords

    def get_level_text(self, record: LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name.ljust(8), f"logging.level.{level_name.lower()}"
        )
        return level_text

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        message = self.format(record)
        traceback = None
        if (
            self.rich_tracebacks
            and record.exc_info
            and record.exc_info != (None, None, None)
        ):
            exc_type, exc_value, exc_traceback = record.exc_info
            assert exc_type is not None
            assert exc_value is not None
            traceback = Traceback.from_exception(
                exc_type,
                exc_value,
                exc_traceback,
                width=self.tracebacks_width,
                code_width=self.tracebacks_code_width,
                extra_lines=self.tracebacks_extra_lines,
                theme=self.tracebacks_theme,
                word_wrap=self.tracebacks_word_wrap,
                show_locals=self.tracebacks_show_locals,
                locals_max_length=self.locals_max_length,
                locals_max_string=self.locals_max_string,
                suppress=self.tracebacks_suppress,
                max_frames=self.tracebacks_max_frames,
            )
            message = record.getMessage()
            if self.formatter:
                record.message = record.getMessage()
                formatter = self.formatter
                if hasattr(formatter, "usesTime") and formatter.usesTime():
                    record.asctime = formatter.formatTime(record, formatter.datefmt)
                message = formatter.formatMessage(record)

        message_renderable = self.render_message(record, message)
        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log record
            # even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        use_markup = getattr(record, "markup", self.markup)
        message_text = Text.from_markup(message) if use_markup else Text(message)

        highlighter = getattr(record, "highlighter", self.highlighter)
        if highlighter:
            message_text = highlighter(message_text)

        if self.keywords is None:
            self.keywords = self.KEYWORDS

        if self.keywords:
            message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render(
        self,
        *,
        record: LogRecord,
        traceback: Optional[Traceback],
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Render log for display.

        Args:
            record (LogRecord): logging Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text) containing log message contents.

        Returns:
            ConsoleRenderable: Renderable to display log.
        """
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)

        log_renderable = self._log_render(
            self.console,
            [message_renderable] if not traceback else [message_renderable, traceback],
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=path,
            line_no=record.lineno,
            link_path=record.pathname if self.enable_link_path else None,
        )
        return log_renderable


if __name__ == "__main__":  # pragma: no cover
    from time import sleep

    FORMAT = "%(message)s"
    # FORMAT = "%(asctime)-15s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level="NOTSET",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
    )
    log = logging.getLogger("rich")

    log.info("Server starting...")
    log.info("Listening on http://127.0.0.1:8080")
    sleep(1)

    log.info("GET /index.html 200 1298")
    log.info("GET /imgs/backgrounds/back1.jpg 200 54386")
    log.info("GET /css/styles.css 200 54386")
    log.warning("GET /favicon.ico 404 242")
    sleep(1)

    log.debug(
        "JSONRPC request\n--> %r\n<-- %r",
        {
            "version": "1.1",
            "method": "confirmFruitPurchase",
            "params": [["apple", "orange", "mangoes", "pomelo"], 1.123],
            "id": "194521489",
        },
        {"version": "1.1", "result": True, "error": None, "id": "194521489"},
    )
    log.debug(
        "Loading configuration file /adasd/asdasd/qeqwe/qwrqwrqwr/sdgsdgsdg/werwerwer/dfgerert/ertertert/ertetert/werwerwer"
    )
    log.error("Unable to find 'pomelo' in database!")
    log.info("POST /jsonrpc/ 200 65532")
    log.info("POST /admin/ 401 42234")
    log.warning("password was rejected for admin site.")

    def divide() -> None:
        number = 1
        divisor = 0
        foos = ["foo"] * 100
        log.debug("in divide")
        try:
            number / divisor
        except:
            log.exception("An error of some kind occurred!")

    divide()
    sleep(1)
    log.critical("Out of memory!")
    log.info("Server exited with code=-1")
    log.info("[bold]EXITING...[/bold]", extra=dict(markup=True))

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\patch_stdout.py ===
"""
patch_stdout
============

This implements a context manager that ensures that print statements within
it won't destroy the user interface. The context manager will replace
`sys.stdout` by something that draws the output above the current prompt,
rather than overwriting the UI.

Usage::

    with patch_stdout(application):
        ...
        application.run()
        ...

Multiple applications can run in the body of the context manager, one after the
other.
"""

from __future__ import annotations

import asyncio
import queue
import sys
import threading
import time
from contextlib import contextmanager
from typing import Generator, TextIO, cast

from .application import get_app_session, run_in_terminal
from .output import Output

__all__ = [
    "patch_stdout",
    "StdoutProxy",
]


@contextmanager
def patch_stdout(raw: bool = False) -> Generator[None, None, None]:
    """
    Replace `sys.stdout` by an :class:`_StdoutProxy` instance.

    Writing to this proxy will make sure that the text appears above the
    prompt, and that it doesn't destroy the output from the renderer.  If no
    application is curring, the behavior should be identical to writing to
    `sys.stdout` directly.

    Warning: If a new event loop is installed using `asyncio.set_event_loop()`,
        then make sure that the context manager is applied after the event loop
        is changed. Printing to stdout will be scheduled in the event loop
        that's active when the context manager is created.

    :param raw: (`bool`) When True, vt100 terminal escape sequences are not
                removed/escaped.
    """
    with StdoutProxy(raw=raw) as proxy:
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # Enter.
        sys.stdout = cast(TextIO, proxy)
        sys.stderr = cast(TextIO, proxy)

        try:
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


class _Done:
    "Sentinel value for stopping the stdout proxy."


class StdoutProxy:
    """
    File-like object, which prints everything written to it, output above the
    current application/prompt. This class is compatible with other file
    objects and can be used as a drop-in replacement for `sys.stdout` or can
    for instance be passed to `logging.StreamHandler`.

    The current application, above which we print, is determined by looking
    what application currently runs in the `AppSession` that is active during
    the creation of this instance.

    This class can be used as a context manager.

    In order to avoid having to repaint the prompt continuously for every
    little write, a short delay of `sleep_between_writes` seconds will be added
    between writes in order to bundle many smaller writes in a short timespan.
    """

    def __init__(
        self,
        sleep_between_writes: float = 0.2,
        raw: bool = False,
    ) -> None:
        self.sleep_between_writes = sleep_between_writes
        self.raw = raw

        self._lock = threading.RLock()
        self._buffer: list[str] = []

        # Keep track of the curret app session.
        self.app_session = get_app_session()

        # See what output is active *right now*. We should do it at this point,
        # before this `StdoutProxy` instance is possibly assigned to `sys.stdout`.
        # Otherwise, if `patch_stdout` is used, and no `Output` instance has
        # been created, then the default output creation code will see this
        # proxy object as `sys.stdout`, and get in a recursive loop trying to
        # access `StdoutProxy.isatty()` which will again retrieve the output.
        self._output: Output = self.app_session.output

        # Flush thread
        self._flush_queue: queue.Queue[str | _Done] = queue.Queue()
        self._flush_thread = self._start_write_thread()
        self.closed = False

    def __enter__(self) -> StdoutProxy:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """
        Stop `StdoutProxy` proxy.

        This will terminate the write thread, make sure everything is flushed
        and wait for the write thread to finish.
        """
        if not self.closed:
            self._flush_queue.put(_Done())
            self._flush_thread.join()
            self.closed = True

    def _start_write_thread(self) -> threading.Thread:
        thread = threading.Thread(
            target=self._write_thread,
            name="patch-stdout-flush-thread",
            daemon=True,
        )
        thread.start()
        return thread

    def _write_thread(self) -> None:
        done = False

        while not done:
            item = self._flush_queue.get()

            if isinstance(item, _Done):
                break

            # Don't bother calling when we got an empty string.
            if not item:
                continue

            text = []
            text.append(item)

            # Read the rest of the queue if more data was queued up.
            while True:
                try:
                    item = self._flush_queue.get_nowait()
                except queue.Empty:
                    break
                else:
                    if isinstance(item, _Done):
                        done = True
                    else:
                        text.append(item)

            app_loop = self._get_app_loop()
            self._write_and_flush(app_loop, "".join(text))

            # If an application was running that requires repainting, then wait
            # for a very short time, in order to bundle actual writes and avoid
            # having to repaint to often.
            if app_loop is not None:
                time.sleep(self.sleep_between_writes)

    def _get_app_loop(self) -> asyncio.AbstractEventLoop | None:
        """
        Return the event loop for the application currently running in our
        `AppSession`.
        """
        app = self.app_session.app

        if app is None:
            return None

        return app.loop

    def _write_and_flush(
        self, loop: asyncio.AbstractEventLoop | None, text: str
    ) -> None:
        """
        Write the given text to stdout and flush.
        If an application is running, use `run_in_terminal`.
        """

        def write_and_flush() -> None:
            # Ensure that autowrap is enabled before calling `write`.
            # XXX: On Windows, the `Windows10_Output` enables/disables VT
            #      terminal processing for every flush. It turns out that this
            #      causes autowrap to be reset (disabled) after each flush. So,
            #      we have to enable it again before writing text.
            self._output.enable_autowrap()

            if self.raw:
                self._output.write_raw(text)
            else:
                self._output.write(text)

            self._output.flush()

        def write_and_flush_in_loop() -> None:
            # If an application is running, use `run_in_terminal`, otherwise
            # call it directly.
            run_in_terminal(write_and_flush, in_executor=False)

        if loop is None:
            # No loop, write immediately.
            write_and_flush()
        else:
            # Make sure `write_and_flush` is executed *in* the event loop, not
            # in another thread.
            loop.call_soon_threadsafe(write_and_flush_in_loop)

    def _write(self, data: str) -> None:
        """
        Note: print()-statements cause to multiple write calls.
              (write('line') and write('\n')). Of course we don't want to call
              `run_in_terminal` for every individual call, because that's too
              expensive, and as long as the newline hasn't been written, the
              text itself is again overwritten by the rendering of the input
              command line. Therefor, we have a little buffer which holds the
              text until a newline is written to stdout.
        """
        if "\n" in data:
            # When there is a newline in the data, write everything before the
            # newline, including the newline itself.
            before, after = data.rsplit("\n", 1)
            to_write = self._buffer + [before, "\n"]
            self._buffer = [after]

            text = "".join(to_write)
            self._flush_queue.put(text)
        else:
            # Otherwise, cache in buffer.
            self._buffer.append(data)

    def _flush(self) -> None:
        text = "".join(self._buffer)
        self._buffer = []
        self._flush_queue.put(text)

    def write(self, data: str) -> int:
        with self._lock:
            self._write(data)

        return len(data)  # Pretend everything was written.

    def flush(self) -> None:
        """
        Flush buffered output.
        """
        with self._lock:
            self._flush()

    @property
    def original_stdout(self) -> TextIO | None:
        return self._output.stdout or sys.__stdout__

    # Attributes for compatibility with sys.__stdout__:

    def fileno(self) -> int:
        return self._output.fileno()

    def isatty(self) -> bool:
        stdout = self._output.stdout
        if stdout is None:
            return False

        return stdout.isatty()

    @property
    def encoding(self) -> str:
        return self._output.encoding()

    @property
    def errors(self) -> str:
        return "strict"

# === NexusCore/openenv\Lib\site-packages\rich\logging.py ===
import logging
from datetime import datetime
from logging import Handler, LogRecord
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Iterable, List, Optional, Type, Union

from rich._null_file import NullFile

from . import get_console
from ._log_render import FormatTimeCallable, LogRender
from .console import Console, ConsoleRenderable
from .highlighter import Highlighter, ReprHighlighter
from .text import Text
from .traceback import Traceback


class RichHandler(Handler):
    """A logging handler that renders output with Rich. The time / level / message and file are displayed in columns.
    The level is color coded, and the message is syntax highlighted.

    Note:
        Be careful when enabling console markup in log messages if you have configured logging for libraries not
        under your control. If a dependency writes messages containing square brackets, it may not produce the intended output.

    Args:
        level (Union[int, str], optional): Log level. Defaults to logging.NOTSET.
        console (:class:`~rich.console.Console`, optional): Optional console instance to write logs.
            Default will use a global console instance writing to stdout.
        show_time (bool, optional): Show a column for the time. Defaults to True.
        omit_repeated_times (bool, optional): Omit repetition of the same time. Defaults to True.
        show_level (bool, optional): Show a column for the level. Defaults to True.
        show_path (bool, optional): Show the path to the original log call. Defaults to True.
        enable_link_path (bool, optional): Enable terminal link of path column to file. Defaults to True.
        highlighter (Highlighter, optional): Highlighter to style log messages, or None to use ReprHighlighter. Defaults to None.
        markup (bool, optional): Enable console markup in log messages. Defaults to False.
        rich_tracebacks (bool, optional): Enable rich tracebacks with syntax highlighting and formatting. Defaults to False.
        tracebacks_width (Optional[int], optional): Number of characters used to render tracebacks, or None for full width. Defaults to None.
        tracebacks_code_width (int, optional): Number of code characters used to render tracebacks, or None for full width. Defaults to 88.
        tracebacks_extra_lines (int, optional): Additional lines of code to render tracebacks, or None for full width. Defaults to None.
        tracebacks_theme (str, optional): Override pygments theme used in traceback.
        tracebacks_word_wrap (bool, optional): Enable word wrapping of long tracebacks lines. Defaults to True.
        tracebacks_show_locals (bool, optional): Enable display of locals in tracebacks. Defaults to False.
        tracebacks_suppress (Sequence[Union[str, ModuleType]]): Optional sequence of modules or paths to exclude from traceback.
        tracebacks_max_frames (int, optional): Optional maximum number of frames returned by traceback.
        locals_max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to 10.
        locals_max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to 80.
        log_time_format (Union[str, TimeFormatterCallable], optional): If ``log_time`` is enabled, either string for strftime or callable that formats the time. Defaults to "[%x %X] ".
        keywords (List[str], optional): List of words to highlight instead of ``RichHandler.KEYWORDS``.
    """

    KEYWORDS: ClassVar[Optional[List[str]]] = [
        "GET",
        "POST",
        "HEAD",
        "PUT",
        "DELETE",
        "OPTIONS",
        "TRACE",
        "PATCH",
    ]
    HIGHLIGHTER_CLASS: ClassVar[Type[Highlighter]] = ReprHighlighter

    def __init__(
        self,
        level: Union[int, str] = logging.NOTSET,
        console: Optional[Console] = None,
        *,
        show_time: bool = True,
        omit_repeated_times: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        enable_link_path: bool = True,
        highlighter: Optional[Highlighter] = None,
        markup: bool = False,
        rich_tracebacks: bool = False,
        tracebacks_width: Optional[int] = None,
        tracebacks_code_width: int = 88,
        tracebacks_extra_lines: int = 3,
        tracebacks_theme: Optional[str] = None,
        tracebacks_word_wrap: bool = True,
        tracebacks_show_locals: bool = False,
        tracebacks_suppress: Iterable[Union[str, ModuleType]] = (),
        tracebacks_max_frames: int = 100,
        locals_max_length: int = 10,
        locals_max_string: int = 80,
        log_time_format: Union[str, FormatTimeCallable] = "[%x %X]",
        keywords: Optional[List[str]] = None,
    ) -> None:
        super().__init__(level=level)
        self.console = console or get_console()
        self.highlighter = highlighter or self.HIGHLIGHTER_CLASS()
        self._log_render = LogRender(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            time_format=log_time_format,
            omit_repeated_times=omit_repeated_times,
            level_width=None,
        )
        self.enable_link_path = enable_link_path
        self.markup = markup
        self.rich_tracebacks = rich_tracebacks
        self.tracebacks_width = tracebacks_width
        self.tracebacks_extra_lines = tracebacks_extra_lines
        self.tracebacks_theme = tracebacks_theme
        self.tracebacks_word_wrap = tracebacks_word_wrap
        self.tracebacks_show_locals = tracebacks_show_locals
        self.tracebacks_suppress = tracebacks_suppress
        self.tracebacks_max_frames = tracebacks_max_frames
        self.tracebacks_code_width = tracebacks_code_width
        self.locals_max_length = locals_max_length
        self.locals_max_string = locals_max_string
        self.keywords = keywords

    def get_level_text(self, record: LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name.ljust(8), f"logging.level.{level_name.lower()}"
        )
        return level_text

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        message = self.format(record)
        traceback = None
        if (
            self.rich_tracebacks
            and record.exc_info
            and record.exc_info != (None, None, None)
        ):
            exc_type, exc_value, exc_traceback = record.exc_info
            assert exc_type is not None
            assert exc_value is not None
            traceback = Traceback.from_exception(
                exc_type,
                exc_value,
                exc_traceback,
                width=self.tracebacks_width,
                code_width=self.tracebacks_code_width,
                extra_lines=self.tracebacks_extra_lines,
                theme=self.tracebacks_theme,
                word_wrap=self.tracebacks_word_wrap,
                show_locals=self.tracebacks_show_locals,
                locals_max_length=self.locals_max_length,
                locals_max_string=self.locals_max_string,
                suppress=self.tracebacks_suppress,
                max_frames=self.tracebacks_max_frames,
            )
            message = record.getMessage()
            if self.formatter:
                record.message = record.getMessage()
                formatter = self.formatter
                if hasattr(formatter, "usesTime") and formatter.usesTime():
                    record.asctime = formatter.formatTime(record, formatter.datefmt)
                message = formatter.formatMessage(record)

        message_renderable = self.render_message(record, message)
        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log record
            # even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        use_markup = getattr(record, "markup", self.markup)
        message_text = Text.from_markup(message) if use_markup else Text(message)

        highlighter = getattr(record, "highlighter", self.highlighter)
        if highlighter:
            message_text = highlighter(message_text)

        if self.keywords is None:
            self.keywords = self.KEYWORDS

        if self.keywords:
            message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render(
        self,
        *,
        record: LogRecord,
        traceback: Optional[Traceback],
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Render log for display.

        Args:
            record (LogRecord): logging Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text) containing log message contents.

        Returns:
            ConsoleRenderable: Renderable to display log.
        """
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)

        log_renderable = self._log_render(
            self.console,
            [message_renderable] if not traceback else [message_renderable, traceback],
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=path,
            line_no=record.lineno,
            link_path=record.pathname if self.enable_link_path else None,
        )
        return log_renderable


if __name__ == "__main__":  # pragma: no cover
    from time import sleep

    FORMAT = "%(message)s"
    # FORMAT = "%(asctime)-15s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level="NOTSET",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
    )
    log = logging.getLogger("rich")

    log.info("Server starting...")
    log.info("Listening on http://127.0.0.1:8080")
    sleep(1)

    log.info("GET /index.html 200 1298")
    log.info("GET /imgs/backgrounds/back1.jpg 200 54386")
    log.info("GET /css/styles.css 200 54386")
    log.warning("GET /favicon.ico 404 242")
    sleep(1)

    log.debug(
        "JSONRPC request\n--> %r\n<-- %r",
        {
            "version": "1.1",
            "method": "confirmFruitPurchase",
            "params": [["apple", "orange", "mangoes", "pomelo"], 1.123],
            "id": "194521489",
        },
        {"version": "1.1", "result": True, "error": None, "id": "194521489"},
    )
    log.debug(
        "Loading configuration file /adasd/asdasd/qeqwe/qwrqwrqwr/sdgsdgsdg/werwerwer/dfgerert/ertertert/ertetert/werwerwer"
    )
    log.error("Unable to find 'pomelo' in database!")
    log.info("POST /jsonrpc/ 200 65532")
    log.info("POST /admin/ 401 42234")
    log.warning("password was rejected for admin site.")

    def divide() -> None:
        number = 1
        divisor = 0
        foos = ["foo"] * 100
        log.debug("in divide")
        try:
            number / divisor
        except:
            log.exception("An error of some kind occurred!")

    divide()
    sleep(1)
    log.critical("Out of memory!")
    log.info("Server exited with code=-1")
    log.info("[bold]EXITING...[/bold]", extra=dict(markup=True))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\multimodal_embeddings\transformation.py ===
from typing import List, Optional, Union, cast

from httpx import Headers, Response

from litellm.exceptions import InternalServerError
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.base_llm.embedding.transformation import LiteLLMLoggingObj
from litellm.types.llms.openai import AllEmbeddingInputValues, AllMessageValues
from litellm.types.llms.vertex_ai import (
    Instance,
    InstanceImage,
    InstanceVideo,
    MultimodalPredictions,
    VertexMultimodalEmbeddingRequest,
)
from litellm.types.utils import (
    Embedding,
    EmbeddingResponse,
    PromptTokensDetailsWrapper,
    Usage,
)
from litellm.utils import _count_characters, is_base64_encoded

from ...base_llm.embedding.transformation import BaseEmbeddingConfig
from ..common_utils import VertexAIError


class VertexAIMultimodalEmbeddingConfig(BaseEmbeddingConfig):
    def get_supported_openai_params(self, model: str) -> list:
        return ["dimensions"]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "dimensions":
                optional_params["outputDimensionality"] = value
        return optional_params

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
        default_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {api_key}",
        }
        headers.update(default_headers)
        return headers

    def _process_input_element(self, input_element: str) -> Instance:
        """
        Process the input element for multimodal embedding requests. checks if the if the input is gcs uri, base64 encoded image or plain text.

        Args:
            input_element (str): The input element to process.

        Returns:
            Dict[str, Any]: A dictionary representing the processed input element.
        """
        if len(input_element) == 0:
            return Instance(text=input_element)
        elif "gs://" in input_element:
            if "mp4" in input_element:
                return Instance(video=InstanceVideo(gcsUri=input_element))
            else:
                return Instance(image=InstanceImage(gcsUri=input_element))
        elif is_base64_encoded(s=input_element):
            return Instance(
                image=InstanceImage(
                    bytesBase64Encoded=(
                        input_element.split(",")[1]
                        if "," in input_element
                        else input_element
                    )
                )
            )
        else:
            return Instance(text=input_element)

    def process_openai_embedding_input(
        self, _input: Union[list, str]
    ) -> List[Instance]:
        """
        Process the input for multimodal embedding requests.

        Args:
            _input (Union[list, str]): The input data to process.

        Returns:
            Union[Instance, List[Instance]]: Either a single Instance or list of Instance objects.
        """
        _input_list = [_input] if not isinstance(_input, list) else _input
        processed_instances = []

        i = 0
        while i < len(_input_list):
            current = _input_list[i]

            # Look ahead for potential media elements
            next_elem = _input_list[i + 1] if i + 1 < len(_input_list) else None

            # If current is a text and next is a GCS URI, or current is a GCS URI
            if isinstance(current, str):
                instance_args: Instance = {}

                # Process current element
                if "gs://" not in current:
                    instance_args["text"] = current
                elif "mp4" in current:
                    instance_args["video"] = InstanceVideo(gcsUri=current)
                else:
                    instance_args["image"] = InstanceImage(gcsUri=current)

                # Check next element if it's a GCS URI
                if next_elem and isinstance(next_elem, str) and "gs://" in next_elem:
                    if "mp4" in next_elem:
                        instance_args["video"] = InstanceVideo(gcsUri=next_elem)
                    else:
                        instance_args["image"] = InstanceImage(gcsUri=next_elem)
                    i += 2  # Skip next element since we processed it
                else:
                    i += 1  # Move to next element

                processed_instances.append(instance_args)
                continue

            # Handle dict or other types
            if isinstance(current, dict):
                instance = Instance(**current)
                processed_instances.append(instance)
            else:
                raise ValueError(f"Unsupported input type: {type(current)}")
            i += 1

        return processed_instances

    def transform_embedding_request(
        self,
        model: str,
        input: AllEmbeddingInputValues,
        optional_params: dict,
        headers: dict,
    ) -> dict:
        optional_params = optional_params or {}

        request_data = VertexMultimodalEmbeddingRequest(instances=[])

        if "instances" in optional_params:
            request_data["instances"] = optional_params["instances"]
        elif isinstance(input, list):
            vertex_instances: List[Instance] = self.process_openai_embedding_input(
                _input=input
            )
            request_data["instances"] = vertex_instances

        else:
            # construct instances
            vertex_request_instance = Instance(**optional_params)

            if isinstance(input, str):
                vertex_request_instance = self._process_input_element(input)

            request_data["instances"] = [vertex_request_instance]

        return cast(dict, request_data)

    def transform_embedding_response(
        self,
        model: str,
        raw_response: Response,
        model_response: EmbeddingResponse,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        request_data: dict,
        optional_params: dict,
        litellm_params: dict,
    ) -> EmbeddingResponse:
        if raw_response.status_code != 200:
            raise Exception(f"Error: {raw_response.status_code} {raw_response.text}")

        _json_response = raw_response.json()
        if "predictions" not in _json_response:
            raise InternalServerError(
                message=f"embedding response does not contain 'predictions', got {_json_response}",
                llm_provider="vertex_ai",
                model=model,
            )
        _predictions = _json_response["predictions"]
        vertex_predictions = MultimodalPredictions(predictions=_predictions)
        model_response.data = self.transform_embedding_response_to_openai(
            predictions=vertex_predictions
        )
        model_response.model = model

        model_response.usage = self.calculate_usage(
            request_data=cast(VertexMultimodalEmbeddingRequest, request_data),
            vertex_predictions=vertex_predictions,
        )

        return model_response

    def calculate_usage(
        self,
        request_data: VertexMultimodalEmbeddingRequest,
        vertex_predictions: MultimodalPredictions,
    ) -> Usage:
        ## Calculate text embeddings usage
        prompt: Optional[str] = None
        character_count: Optional[int] = None

        for instance in request_data["instances"]:
            text = instance.get("text")
            if text:
                if prompt is None:
                    prompt = text
                else:
                    prompt += text

        if prompt is not None:
            character_count = _count_characters(prompt)

        ## Calculate image embeddings usage
        image_count = 0
        for instance in request_data["instances"]:
            if instance.get("image"):
                image_count += 1

        ## Calculate video embeddings usage
        video_length_seconds = 0
        for prediction in vertex_predictions["predictions"]:
            video_embeddings = prediction.get("videoEmbeddings")
            if video_embeddings:
                for embedding in video_embeddings:
                    duration = embedding["endOffsetSec"] - embedding["startOffsetSec"]
                    video_length_seconds += duration

        prompt_tokens_details = PromptTokensDetailsWrapper(
            character_count=character_count,
            image_count=image_count,
            video_length_seconds=video_length_seconds,
        )

        return Usage(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            prompt_tokens_details=prompt_tokens_details,
        )

    def transform_embedding_response_to_openai(
        self, predictions: MultimodalPredictions
    ) -> List[Embedding]:
        openai_embeddings: List[Embedding] = []
        if "predictions" in predictions:
            for idx, _prediction in enumerate(predictions["predictions"]):
                if _prediction:
                    if "textEmbedding" in _prediction:
                        openai_embedding_object = Embedding(
                            embedding=_prediction["textEmbedding"],
                            index=idx,
                            object="embedding",
                        )
                        openai_embeddings.append(openai_embedding_object)
                    elif "imageEmbedding" in _prediction:
                        openai_embedding_object = Embedding(
                            embedding=_prediction["imageEmbedding"],
                            index=idx,
                            object="embedding",
                        )
                        openai_embeddings.append(openai_embedding_object)
                    elif "videoEmbeddings" in _prediction:
                        for video_embedding in _prediction["videoEmbeddings"]:
                            openai_embedding_object = Embedding(
                                embedding=video_embedding["embedding"],
                                index=idx,
                                object="embedding",
                            )
                            openai_embeddings.append(openai_embedding_object)
        return openai_embeddings

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return VertexAIError(
            status_code=status_code, message=error_message, headers=headers
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\budget_management_endpoints.py ===
"""
BUDGET MANAGEMENT

All /budget management endpoints 

/budget/new   
/budget/info
/budget/update
/budget/delete
/budget/settings
/budget/list
"""

#### BUDGET TABLE MANAGEMENT ####
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from litellm.litellm_core_utils.duration_parser import duration_in_seconds
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.utils import jsonify_object

router = APIRouter()


@router.post(
    "/budget/new",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def new_budget(
    budget_obj: BudgetNewRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create a new budget object. Can apply this to teams, orgs, end-users, keys.

    Parameters:
    - budget_duration: Optional[str] - Budget reset period ("30d", "1h", etc.)
    - budget_id: Optional[str] - The id of the budget. If not provided, a new id will be generated.
    - max_budget: Optional[float] - The max budget for the budget.
    - soft_budget: Optional[float] - The soft budget for the budget.
    - max_parallel_requests: Optional[int] - The max number of parallel requests for the budget.
    - tpm_limit: Optional[int] - The tokens per minute limit for the budget.
    - rpm_limit: Optional[int] - The requests per minute limit for the budget.
    - model_max_budget: Optional[dict] - Specify max budget for a given model. Example: {"openai/gpt-4o-mini": {"max_budget": 100.0, "budget_duration": "1d", "tpm_limit": 100000, "rpm_limit": 100000}}
    - budget_reset_at: Optional[datetime] - Datetime when the initial budget is reset. Default is now.
    """
    from litellm.proxy.proxy_server import litellm_proxy_admin_name, prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    # if no budget_reset_at date is set, but a budget_duration is given, then set budget_reset_at initially to the first completed duration interval in future
    if budget_obj.budget_reset_at is None and budget_obj.budget_duration is not None:
        budget_obj.budget_reset_at = datetime.utcnow() + timedelta(
            seconds=duration_in_seconds(duration=budget_obj.budget_duration)
        )

    budget_obj_json = budget_obj.model_dump(exclude_none=True)
    budget_obj_jsonified = jsonify_object(budget_obj_json)  # json dump any dictionaries
    response = await prisma_client.db.litellm_budgettable.create(
        data={
            **budget_obj_jsonified,  # type: ignore
            "created_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
            "updated_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
        }  # type: ignore
    )

    return response


@router.post(
    "/budget/update",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_budget(
    budget_obj: BudgetNewRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update an existing budget object.

    Parameters:
    - budget_duration: Optional[str] - Budget reset period ("30d", "1h", etc.)
    - budget_id: Optional[str] - The id of the budget. If not provided, a new id will be generated.
    - max_budget: Optional[float] - The max budget for the budget.
    - soft_budget: Optional[float] - The soft budget for the budget.
    - max_parallel_requests: Optional[int] - The max number of parallel requests for the budget.
    - tpm_limit: Optional[int] - The tokens per minute limit for the budget.
    - rpm_limit: Optional[int] - The requests per minute limit for the budget.
    - model_max_budget: Optional[dict] - Specify max budget for a given model. Example: {"openai/gpt-4o-mini": {"max_budget": 100.0, "budget_duration": "1d", "tpm_limit": 100000, "rpm_limit": 100000}}
    - budget_reset_at: Optional[datetime] - Update the Datetime when the budget was last reset.
    """
    from litellm.proxy.proxy_server import litellm_proxy_admin_name, prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )
    if budget_obj.budget_id is None:
        raise HTTPException(status_code=400, detail={"error": "budget_id is required"})

    response = await prisma_client.db.litellm_budgettable.update(
        where={"budget_id": budget_obj.budget_id},
        data={
            **budget_obj.model_dump(exclude_none=True),  # type: ignore
            "updated_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
        },  # type: ignore
    )

    return response


@router.post(
    "/budget/info",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def info_budget(data: BudgetRequest):
    """
    Get the budget id specific information

    Parameters:
    - budgets: List[str] - The list of budget ids to get information for
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if len(data.budgets) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Specify list of budget id's to query. Passed in={data.budgets}"
            },
        )
    response = await prisma_client.db.litellm_budgettable.find_many(
        where={"budget_id": {"in": data.budgets}},
    )

    return response


@router.get(
    "/budget/settings",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def budget_settings(
    budget_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get list of configurable params + current value for a budget item + description of each field

    Used on Admin UI.

    Query Parameters:
    - budget_id: str - The budget id to get information for
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    ## get budget item from db
    db_budget_row = await prisma_client.db.litellm_budgettable.find_first(
        where={"budget_id": budget_id}
    )

    if db_budget_row is not None:
        db_budget_row_dict = db_budget_row.model_dump(exclude_none=True)
    else:
        db_budget_row_dict = {}

    allowed_args = {
        "max_parallel_requests": {"type": "Integer"},
        "tpm_limit": {"type": "Integer"},
        "rpm_limit": {"type": "Integer"},
        "budget_duration": {"type": "String"},
        "max_budget": {"type": "Float"},
        "soft_budget": {"type": "Float"},
    }

    return_val = []

    for field_name, field_info in BudgetNewRequest.model_fields.items():
        if field_name in allowed_args:
            _stored_in_db = True

            _response_obj = ConfigList(
                field_name=field_name,
                field_type=allowed_args[field_name]["type"],
                field_description=field_info.description or "",
                field_value=db_budget_row_dict.get(field_name, None),
                stored_in_db=_stored_in_db,
                field_default_value=field_info.default,
            )
            return_val.append(_response_obj)

    return return_val


@router.get(
    "/budget/list",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def list_budget(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """List all the created budgets in proxy db. Used on Admin UI."""
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    response = await prisma_client.db.litellm_budgettable.find_many()

    return response


@router.post(
    "/budget/delete",
    tags=["budget management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_budget(
    data: BudgetDeleteRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete budget

    Parameters:
    - id: str - The budget id to delete
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    response = await prisma_client.db.litellm_budgettable.delete(
        where={"budget_id": data.id}
    )

    return response

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\logging.py ===
import logging
from datetime import datetime
from logging import Handler, LogRecord
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Iterable, List, Optional, Type, Union

from pip._vendor.rich._null_file import NullFile

from . import get_console
from ._log_render import FormatTimeCallable, LogRender
from .console import Console, ConsoleRenderable
from .highlighter import Highlighter, ReprHighlighter
from .text import Text
from .traceback import Traceback


class RichHandler(Handler):
    """A logging handler that renders output with Rich. The time / level / message and file are displayed in columns.
    The level is color coded, and the message is syntax highlighted.

    Note:
        Be careful when enabling console markup in log messages if you have configured logging for libraries not
        under your control. If a dependency writes messages containing square brackets, it may not produce the intended output.

    Args:
        level (Union[int, str], optional): Log level. Defaults to logging.NOTSET.
        console (:class:`~rich.console.Console`, optional): Optional console instance to write logs.
            Default will use a global console instance writing to stdout.
        show_time (bool, optional): Show a column for the time. Defaults to True.
        omit_repeated_times (bool, optional): Omit repetition of the same time. Defaults to True.
        show_level (bool, optional): Show a column for the level. Defaults to True.
        show_path (bool, optional): Show the path to the original log call. Defaults to True.
        enable_link_path (bool, optional): Enable terminal link of path column to file. Defaults to True.
        highlighter (Highlighter, optional): Highlighter to style log messages, or None to use ReprHighlighter. Defaults to None.
        markup (bool, optional): Enable console markup in log messages. Defaults to False.
        rich_tracebacks (bool, optional): Enable rich tracebacks with syntax highlighting and formatting. Defaults to False.
        tracebacks_width (Optional[int], optional): Number of characters used to render tracebacks, or None for full width. Defaults to None.
        tracebacks_code_width (int, optional): Number of code characters used to render tracebacks, or None for full width. Defaults to 88.
        tracebacks_extra_lines (int, optional): Additional lines of code to render tracebacks, or None for full width. Defaults to None.
        tracebacks_theme (str, optional): Override pygments theme used in traceback.
        tracebacks_word_wrap (bool, optional): Enable word wrapping of long tracebacks lines. Defaults to True.
        tracebacks_show_locals (bool, optional): Enable display of locals in tracebacks. Defaults to False.
        tracebacks_suppress (Sequence[Union[str, ModuleType]]): Optional sequence of modules or paths to exclude from traceback.
        tracebacks_max_frames (int, optional): Optional maximum number of frames returned by traceback.
        locals_max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to 10.
        locals_max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to 80.
        log_time_format (Union[str, TimeFormatterCallable], optional): If ``log_time`` is enabled, either string for strftime or callable that formats the time. Defaults to "[%x %X] ".
        keywords (List[str], optional): List of words to highlight instead of ``RichHandler.KEYWORDS``.
    """

    KEYWORDS: ClassVar[Optional[List[str]]] = [
        "GET",
        "POST",
        "HEAD",
        "PUT",
        "DELETE",
        "OPTIONS",
        "TRACE",
        "PATCH",
    ]
    HIGHLIGHTER_CLASS: ClassVar[Type[Highlighter]] = ReprHighlighter

    def __init__(
        self,
        level: Union[int, str] = logging.NOTSET,
        console: Optional[Console] = None,
        *,
        show_time: bool = True,
        omit_repeated_times: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        enable_link_path: bool = True,
        highlighter: Optional[Highlighter] = None,
        markup: bool = False,
        rich_tracebacks: bool = False,
        tracebacks_width: Optional[int] = None,
        tracebacks_code_width: int = 88,
        tracebacks_extra_lines: int = 3,
        tracebacks_theme: Optional[str] = None,
        tracebacks_word_wrap: bool = True,
        tracebacks_show_locals: bool = False,
        tracebacks_suppress: Iterable[Union[str, ModuleType]] = (),
        tracebacks_max_frames: int = 100,
        locals_max_length: int = 10,
        locals_max_string: int = 80,
        log_time_format: Union[str, FormatTimeCallable] = "[%x %X]",
        keywords: Optional[List[str]] = None,
    ) -> None:
        super().__init__(level=level)
        self.console = console or get_console()
        self.highlighter = highlighter or self.HIGHLIGHTER_CLASS()
        self._log_render = LogRender(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            time_format=log_time_format,
            omit_repeated_times=omit_repeated_times,
            level_width=None,
        )
        self.enable_link_path = enable_link_path
        self.markup = markup
        self.rich_tracebacks = rich_tracebacks
        self.tracebacks_width = tracebacks_width
        self.tracebacks_extra_lines = tracebacks_extra_lines
        self.tracebacks_theme = tracebacks_theme
        self.tracebacks_word_wrap = tracebacks_word_wrap
        self.tracebacks_show_locals = tracebacks_show_locals
        self.tracebacks_suppress = tracebacks_suppress
        self.tracebacks_max_frames = tracebacks_max_frames
        self.tracebacks_code_width = tracebacks_code_width
        self.locals_max_length = locals_max_length
        self.locals_max_string = locals_max_string
        self.keywords = keywords

    def get_level_text(self, record: LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name.ljust(8), f"logging.level.{level_name.lower()}"
        )
        return level_text

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        message = self.format(record)
        traceback = None
        if (
            self.rich_tracebacks
            and record.exc_info
            and record.exc_info != (None, None, None)
        ):
            exc_type, exc_value, exc_traceback = record.exc_info
            assert exc_type is not None
            assert exc_value is not None
            traceback = Traceback.from_exception(
                exc_type,
                exc_value,
                exc_traceback,
                width=self.tracebacks_width,
                code_width=self.tracebacks_code_width,
                extra_lines=self.tracebacks_extra_lines,
                theme=self.tracebacks_theme,
                word_wrap=self.tracebacks_word_wrap,
                show_locals=self.tracebacks_show_locals,
                locals_max_length=self.locals_max_length,
                locals_max_string=self.locals_max_string,
                suppress=self.tracebacks_suppress,
                max_frames=self.tracebacks_max_frames,
            )
            message = record.getMessage()
            if self.formatter:
                record.message = record.getMessage()
                formatter = self.formatter
                if hasattr(formatter, "usesTime") and formatter.usesTime():
                    record.asctime = formatter.formatTime(record, formatter.datefmt)
                message = formatter.formatMessage(record)

        message_renderable = self.render_message(record, message)
        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log record
            # even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        use_markup = getattr(record, "markup", self.markup)
        message_text = Text.from_markup(message) if use_markup else Text(message)

        highlighter = getattr(record, "highlighter", self.highlighter)
        if highlighter:
            message_text = highlighter(message_text)

        if self.keywords is None:
            self.keywords = self.KEYWORDS

        if self.keywords:
            message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render(
        self,
        *,
        record: LogRecord,
        traceback: Optional[Traceback],
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Render log for display.

        Args:
            record (LogRecord): logging Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text) containing log message contents.

        Returns:
            ConsoleRenderable: Renderable to display log.
        """
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)

        log_renderable = self._log_render(
            self.console,
            [message_renderable] if not traceback else [message_renderable, traceback],
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=path,
            line_no=record.lineno,
            link_path=record.pathname if self.enable_link_path else None,
        )
        return log_renderable


if __name__ == "__main__":  # pragma: no cover
    from time import sleep

    FORMAT = "%(message)s"
    # FORMAT = "%(asctime)-15s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level="NOTSET",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
    )
    log = logging.getLogger("rich")

    log.info("Server starting...")
    log.info("Listening on http://127.0.0.1:8080")
    sleep(1)

    log.info("GET /index.html 200 1298")
    log.info("GET /imgs/backgrounds/back1.jpg 200 54386")
    log.info("GET /css/styles.css 200 54386")
    log.warning("GET /favicon.ico 404 242")
    sleep(1)

    log.debug(
        "JSONRPC request\n--> %r\n<-- %r",
        {
            "version": "1.1",
            "method": "confirmFruitPurchase",
            "params": [["apple", "orange", "mangoes", "pomelo"], 1.123],
            "id": "194521489",
        },
        {"version": "1.1", "result": True, "error": None, "id": "194521489"},
    )
    log.debug(
        "Loading configuration file /adasd/asdasd/qeqwe/qwrqwrqwr/sdgsdgsdg/werwerwer/dfgerert/ertertert/ertetert/werwerwer"
    )
    log.error("Unable to find 'pomelo' in database!")
    log.info("POST /jsonrpc/ 200 65532")
    log.info("POST /admin/ 401 42234")
    log.warning("password was rejected for admin site.")

    def divide() -> None:
        number = 1
        divisor = 0
        foos = ["foo"] * 100
        log.debug("in divide")
        try:
            number / divisor
        except:
            log.exception("An error of some kind occurred!")

    divide()
    sleep(1)
    log.critical("Out of memory!")
    log.info("Server exited with code=-1")
    log.info("[bold]EXITING...[/bold]", extra=dict(markup=True))

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\formatted_text\ansi.py ===
from __future__ import annotations

from string import Formatter
from typing import Generator

from prompt_toolkit.output.vt100 import BG_ANSI_COLORS, FG_ANSI_COLORS
from prompt_toolkit.output.vt100 import _256_colors as _256_colors_table

from .base import StyleAndTextTuples

__all__ = [
    "ANSI",
    "ansi_escape",
]


class ANSI:
    """
    ANSI formatted text.
    Take something ANSI escaped text, for use as a formatted string. E.g.

    ::

        ANSI('\\x1b[31mhello \\x1b[32mworld')

    Characters between ``\\001`` and ``\\002`` are supposed to have a zero width
    when printed, but these are literally sent to the terminal output. This can
    be used for instance, for inserting Final Term prompt commands.  They will
    be translated into a prompt_toolkit '[ZeroWidthEscape]' fragment.
    """

    def __init__(self, value: str) -> None:
        self.value = value
        self._formatted_text: StyleAndTextTuples = []

        # Default style attributes.
        self._color: str | None = None
        self._bgcolor: str | None = None
        self._bold = False
        self._underline = False
        self._strike = False
        self._italic = False
        self._blink = False
        self._reverse = False
        self._hidden = False

        # Process received text.
        parser = self._parse_corot()
        parser.send(None)  # type: ignore
        for c in value:
            parser.send(c)

    def _parse_corot(self) -> Generator[None, str, None]:
        """
        Coroutine that parses the ANSI escape sequences.
        """
        style = ""
        formatted_text = self._formatted_text

        while True:
            # NOTE: CSI is a special token within a stream of characters that
            #       introduces an ANSI control sequence used to set the
            #       style attributes of the following characters.
            csi = False

            c = yield

            # Everything between \001 and \002 should become a ZeroWidthEscape.
            if c == "\001":
                escaped_text = ""
                while c != "\002":
                    c = yield
                    if c == "\002":
                        formatted_text.append(("[ZeroWidthEscape]", escaped_text))
                        c = yield
                        break
                    else:
                        escaped_text += c

            # Check for CSI
            if c == "\x1b":
                # Start of color escape sequence.
                square_bracket = yield
                if square_bracket == "[":
                    csi = True
                else:
                    continue
            elif c == "\x9b":
                csi = True

            if csi:
                # Got a CSI sequence. Color codes are following.
                current = ""
                params = []

                while True:
                    char = yield

                    # Construct number
                    if char.isdigit():
                        current += char

                    # Eval number
                    else:
                        # Limit and save number value
                        params.append(min(int(current or 0), 9999))

                        # Get delimiter token if present
                        if char == ";":
                            current = ""

                        # Check and evaluate color codes
                        elif char == "m":
                            # Set attributes and token.
                            self._select_graphic_rendition(params)
                            style = self._create_style_string()
                            break

                        # Check and evaluate cursor forward
                        elif char == "C":
                            for i in range(params[0]):
                                # add <SPACE> using current style
                                formatted_text.append((style, " "))
                            break

                        else:
                            # Ignore unsupported sequence.
                            break
            else:
                # Add current character.
                # NOTE: At this point, we could merge the current character
                #       into the previous tuple if the style did not change,
                #       however, it's not worth the effort given that it will
                #       be "Exploded" once again when it's rendered to the
                #       output.
                formatted_text.append((style, c))

    def _select_graphic_rendition(self, attrs: list[int]) -> None:
        """
        Taken a list of graphics attributes and apply changes.
        """
        if not attrs:
            attrs = [0]
        else:
            attrs = list(attrs[::-1])

        while attrs:
            attr = attrs.pop()

            if attr in _fg_colors:
                self._color = _fg_colors[attr]
            elif attr in _bg_colors:
                self._bgcolor = _bg_colors[attr]
            elif attr == 1:
                self._bold = True
            # elif attr == 2:
            #   self._faint = True
            elif attr == 3:
                self._italic = True
            elif attr == 4:
                self._underline = True
            elif attr == 5:
                self._blink = True  # Slow blink
            elif attr == 6:
                self._blink = True  # Fast blink
            elif attr == 7:
                self._reverse = True
            elif attr == 8:
                self._hidden = True
            elif attr == 9:
                self._strike = True
            elif attr == 22:
                self._bold = False  # Normal intensity
            elif attr == 23:
                self._italic = False
            elif attr == 24:
                self._underline = False
            elif attr == 25:
                self._blink = False
            elif attr == 27:
                self._reverse = False
            elif attr == 28:
                self._hidden = False
            elif attr == 29:
                self._strike = False
            elif not attr:
                # Reset all style attributes
                self._color = None
                self._bgcolor = None
                self._bold = False
                self._underline = False
                self._strike = False
                self._italic = False
                self._blink = False
                self._reverse = False
                self._hidden = False

            elif attr in (38, 48) and len(attrs) > 1:
                n = attrs.pop()

                # 256 colors.
                if n == 5 and len(attrs) >= 1:
                    if attr == 38:
                        m = attrs.pop()
                        self._color = _256_colors.get(m)
                    elif attr == 48:
                        m = attrs.pop()
                        self._bgcolor = _256_colors.get(m)

                # True colors.
                if n == 2 and len(attrs) >= 3:
                    try:
                        color_str = (
                            f"#{attrs.pop():02x}{attrs.pop():02x}{attrs.pop():02x}"
                        )
                    except IndexError:
                        pass
                    else:
                        if attr == 38:
                            self._color = color_str
                        elif attr == 48:
                            self._bgcolor = color_str

    def _create_style_string(self) -> str:
        """
        Turn current style flags into a string for usage in a formatted text.
        """
        result = []
        if self._color:
            result.append(self._color)
        if self._bgcolor:
            result.append("bg:" + self._bgcolor)
        if self._bold:
            result.append("bold")
        if self._underline:
            result.append("underline")
        if self._strike:
            result.append("strike")
        if self._italic:
            result.append("italic")
        if self._blink:
            result.append("blink")
        if self._reverse:
            result.append("reverse")
        if self._hidden:
            result.append("hidden")

        return " ".join(result)

    def __repr__(self) -> str:
        return f"ANSI({self.value!r})"

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        return self._formatted_text

    def format(self, *args: str, **kwargs: str) -> ANSI:
        """
        Like `str.format`, but make sure that the arguments are properly
        escaped. (No ANSI escapes can be injected.)
        """
        return ANSI(FORMATTER.vformat(self.value, args, kwargs))

    def __mod__(self, value: object) -> ANSI:
        """
        ANSI('<b>%s</b>') % value
        """
        if not isinstance(value, tuple):
            value = (value,)

        value = tuple(ansi_escape(i) for i in value)
        return ANSI(self.value % value)


# Mapping of the ANSI color codes to their names.
_fg_colors = {v: k for k, v in FG_ANSI_COLORS.items()}
_bg_colors = {v: k for k, v in BG_ANSI_COLORS.items()}

# Mapping of the escape codes for 256colors to their 'ffffff' value.
_256_colors = {}

for i, (r, g, b) in enumerate(_256_colors_table.colors):
    _256_colors[i] = f"#{r:02x}{g:02x}{b:02x}"


def ansi_escape(text: object) -> str:
    """
    Replace characters with a special meaning.
    """
    return str(text).replace("\x1b", "?").replace("\b", "?")


class ANSIFormatter(Formatter):
    def format_field(self, value: object, format_spec: str) -> str:
        return ansi_escape(format(value, format_spec))


FORMATTER = ANSIFormatter()

# === NexusCore/openenv\Lib\site-packages\proto\marshal\marshal.py ===
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import enum

from google.protobuf import message
from google.protobuf import duration_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import field_mask_pb2
from google.protobuf import struct_pb2
from google.protobuf import wrappers_pb2

from proto.marshal import compat
from proto.marshal.collections import MapComposite
from proto.marshal.collections import Repeated
from proto.marshal.collections import RepeatedComposite

from proto.marshal.rules import bytes as pb_bytes
from proto.marshal.rules import stringy_numbers
from proto.marshal.rules import dates
from proto.marshal.rules import struct
from proto.marshal.rules import wrappers
from proto.marshal.rules import field_mask
from proto.primitives import ProtoType


class Rule(abc.ABC):
    """Abstract class definition for marshal rules."""

    @classmethod
    def __subclasshook__(cls, C):
        if hasattr(C, "to_python") and hasattr(C, "to_proto"):
            return True
        return NotImplemented


class BaseMarshal:
    """The base class to translate between protobuf and Python classes.

    Protocol buffers defines many common types (e.g. Timestamp, Duration)
    which also exist in the Python standard library. The marshal essentially
    translates between these: it keeps a registry of common protocol buffers
    and their Python representations, and translates back and forth.

    The protocol buffer class is always the "key" in this relationship; when
    presenting a message, the declared field types are used to determine
    whether a value should be transformed into another class. Similarly,
    when accepting a Python value (when setting a field, for example),
    the declared field type is still used. This means that, if appropriate,
    multiple protocol buffer types may use the same Python type.

    The primary implementation of this is :class:`Marshal`, which should
    usually be used instead of this class directly.
    """

    def __init__(self):
        self._rules = {}
        self._noop = NoopRule()
        self.reset()

    def register(self, proto_type: type, rule: Rule = None):
        """Register a rule against the given ``proto_type``.

        This function expects a ``proto_type`` (the descriptor class) and
        a ``rule``; an object with a ``to_python`` and ``to_proto`` method.
        Each method should return the appropriate Python or protocol buffer
        type, and be idempotent (e.g. accept either type as input).

        This function can also be used as a decorator::

            @marshal.register(timestamp_pb2.Timestamp)
            class TimestampRule:
                ...

        In this case, the class will be initialized for you with zero
        arguments.

        Args:
            proto_type (type): A protocol buffer message type.
            rule: A marshal object
        """
        # If a rule was provided, register it and be done.
        if rule:
            # Ensure the rule implements Rule.
            if not isinstance(rule, Rule):
                raise TypeError(
                    "Marshal rule instances must implement "
                    "`to_proto` and `to_python` methods."
                )

            # Register the rule.
            self._rules[proto_type] = rule
            return

        # Create an inner function that will register an instance of the
        # marshal class to this object's registry, and return it.
        def register_rule_class(rule_class: type):
            # Ensure the rule class is a valid rule.
            if not issubclass(rule_class, Rule):
                raise TypeError(
                    "Marshal rule subclasses must implement "
                    "`to_proto` and `to_python` methods."
                )

            # Register the rule class.
            self._rules[proto_type] = rule_class()
            return rule_class

        return register_rule_class

    def reset(self):
        """Reset the registry to its initial state."""
        self._rules.clear()

        # Register date and time wrappers.
        self.register(timestamp_pb2.Timestamp, dates.TimestampRule())
        self.register(duration_pb2.Duration, dates.DurationRule())

        # Register FieldMask wrappers.
        self.register(field_mask_pb2.FieldMask, field_mask.FieldMaskRule())

        # Register nullable primitive wrappers.
        self.register(wrappers_pb2.BoolValue, wrappers.BoolValueRule())
        self.register(wrappers_pb2.BytesValue, wrappers.BytesValueRule())
        self.register(wrappers_pb2.DoubleValue, wrappers.DoubleValueRule())
        self.register(wrappers_pb2.FloatValue, wrappers.FloatValueRule())
        self.register(wrappers_pb2.Int32Value, wrappers.Int32ValueRule())
        self.register(wrappers_pb2.Int64Value, wrappers.Int64ValueRule())
        self.register(wrappers_pb2.StringValue, wrappers.StringValueRule())
        self.register(wrappers_pb2.UInt32Value, wrappers.UInt32ValueRule())
        self.register(wrappers_pb2.UInt64Value, wrappers.UInt64ValueRule())

        # Register the google.protobuf.Struct wrappers.
        #
        # These are aware of the marshal that created them, because they
        # create RepeatedComposite and MapComposite instances directly and
        # need to pass the marshal to them.
        self.register(struct_pb2.Value, struct.ValueRule(marshal=self))
        self.register(struct_pb2.ListValue, struct.ListValueRule(marshal=self))
        self.register(struct_pb2.Struct, struct.StructRule(marshal=self))

        # Special case for bytes to allow base64 encode/decode
        self.register(ProtoType.BYTES, pb_bytes.BytesRule())

        # Special case for int64 from strings because of dict round trip.
        # See https://github.com/protocolbuffers/protobuf/issues/2679
        for rule_class in stringy_numbers.STRINGY_NUMBER_RULES:
            self.register(rule_class._proto_type, rule_class())

    def get_rule(self, proto_type):
        # Rules are needed to convert values between proto-plus and pb.
        # Retrieve the rule for the specified proto type.
        # The NoopRule will be used when a rule is not found.
        rule = self._rules.get(proto_type, self._noop)

        # If we don't find a rule, also check under `_instances`
        # in case there is a rule in another package.
        # See https://github.com/googleapis/proto-plus-python/issues/349
        if rule == self._noop and hasattr(self, "_instances"):
            for _, instance in self._instances.items():
                rule = instance._rules.get(proto_type, self._noop)
                if rule != self._noop:
                    break
        return rule

    def to_python(self, proto_type, value, *, absent: bool = None):
        # Internal protobuf has its own special type for lists of values.
        # Return a view around it that implements MutableSequence.
        value_type = type(value)  # Minor performance boost over isinstance
        if value_type in compat.repeated_composite_types:
            return RepeatedComposite(value, marshal=self)
        if value_type in compat.repeated_scalar_types:
            if isinstance(proto_type, type):
                return RepeatedComposite(value, marshal=self, proto_type=proto_type)
            else:
                return Repeated(value, marshal=self)

        # Same thing for maps of messages.
        # See https://github.com/protocolbuffers/protobuf/issues/16596
        # We need to look up the name of the type in compat.map_composite_type_names
        # as class `MessageMapContainer` is no longer exposed
        # This is done to avoid taking a breaking change in proto-plus.
        if (
            value_type in compat.map_composite_types
            or value_type.__name__ in compat.map_composite_type_names
        ):
            return MapComposite(value, marshal=self)
        return self.get_rule(proto_type=proto_type).to_python(value, absent=absent)

    def to_proto(self, proto_type, value, *, strict: bool = False):
        # The protos in google/protobuf/struct.proto are exceptional cases,
        # because they can and should represent themselves as lists and dicts.
        # These cases are handled in their rule classes.
        if proto_type not in (
            struct_pb2.Value,
            struct_pb2.ListValue,
            struct_pb2.Struct,
        ):
            # For our repeated and map view objects, simply return the
            # underlying pb.
            if isinstance(value, (Repeated, MapComposite)):
                return value.pb

            # Convert lists and tuples recursively.
            if isinstance(value, (list, tuple)):
                return type(value)(self.to_proto(proto_type, i) for i in value)

        # Convert dictionaries recursively when the proto type is a map.
        # This is slightly more complicated than converting a list or tuple
        # because we have to step through the magic that protocol buffers does.
        #
        # Essentially, a type of map<string, Foo> will show up here as
        # a FoosEntry with a `key` field, `value` field, and a `map_entry`
        # annotation. We need to do the conversion based on the `value`
        # field's type.
        if isinstance(value, dict) and (
            proto_type.DESCRIPTOR.has_options
            and proto_type.DESCRIPTOR.GetOptions().map_entry
        ):
            recursive_type = type(proto_type().value)
            return {k: self.to_proto(recursive_type, v) for k, v in value.items()}

        pb_value = self.get_rule(proto_type=proto_type).to_proto(value)

        # Sanity check: If we are in strict mode, did we get the value we want?
        if strict and not isinstance(pb_value, proto_type):
            raise TypeError(
                "Parameter must be instance of the same class; "
                "expected {expected}, got {got}".format(
                    expected=proto_type.__name__,
                    got=pb_value.__class__.__name__,
                ),
            )
        # Return the final value.
        return pb_value


class Marshal(BaseMarshal):
    """The translator between protocol buffer and Python instances.

    The bulk of the implementation is in :class:`BaseMarshal`. This class
    adds identity tracking: multiple instantiations of :class:`Marshal` with
    the same name will provide the same instance.
    """

    _instances = {}

    def __new__(cls, *, name: str):
        """Create a marshal instance.

        Args:
            name (str): The name of the marshal. Instantiating multiple
                marshals with the same ``name`` argument will provide the
                same marshal each time.
        """
        klass = cls._instances.get(name)
        if klass is None:
            klass = cls._instances[name] = super().__new__(cls)

        return klass

    def __init__(self, *, name: str):
        """Instantiate a marshal.

        Args:
            name (str): The name of the marshal. Instantiating multiple
                marshals with the same ``name`` argument will provide the
                same marshal each time.
        """
        self._name = name
        if not hasattr(self, "_rules"):
            super().__init__()


class NoopRule:
    """A catch-all rule that does nothing."""

    def to_python(self, pb_value, *, absent: bool = None):
        return pb_value

    def to_proto(self, value):
        return value


__all__ = ("Marshal",)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\temp_dir.py ===
import errno
import itertools
import logging
import os.path
import tempfile
import traceback
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    TypeVar,
    Union,
)

from pip._internal.utils.misc import enum, rmtree

logger = logging.getLogger(__name__)

_T = TypeVar("_T", bound="TempDirectory")


# Kinds of temporary directories. Only needed for ones that are
# globally-managed.
tempdir_kinds = enum(
    BUILD_ENV="build-env",
    EPHEM_WHEEL_CACHE="ephem-wheel-cache",
    REQ_BUILD="req-build",
)


_tempdir_manager: Optional[ExitStack] = None


@contextmanager
def global_tempdir_manager() -> Generator[None, None, None]:
    global _tempdir_manager
    with ExitStack() as stack:
        old_tempdir_manager, _tempdir_manager = _tempdir_manager, stack
        try:
            yield
        finally:
            _tempdir_manager = old_tempdir_manager


class TempDirectoryTypeRegistry:
    """Manages temp directory behavior"""

    def __init__(self) -> None:
        self._should_delete: Dict[str, bool] = {}

    def set_delete(self, kind: str, value: bool) -> None:
        """Indicate whether a TempDirectory of the given kind should be
        auto-deleted.
        """
        self._should_delete[kind] = value

    def get_delete(self, kind: str) -> bool:
        """Get configured auto-delete flag for a given TempDirectory type,
        default True.
        """
        return self._should_delete.get(kind, True)


_tempdir_registry: Optional[TempDirectoryTypeRegistry] = None


@contextmanager
def tempdir_registry() -> Generator[TempDirectoryTypeRegistry, None, None]:
    """Provides a scoped global tempdir registry that can be used to dictate
    whether directories should be deleted.
    """
    global _tempdir_registry
    old_tempdir_registry = _tempdir_registry
    _tempdir_registry = TempDirectoryTypeRegistry()
    try:
        yield _tempdir_registry
    finally:
        _tempdir_registry = old_tempdir_registry


class _Default:
    pass


_default = _Default()


class TempDirectory:
    """Helper class that owns and cleans up a temporary directory.

    This class can be used as a context manager or as an OO representation of a
    temporary directory.

    Attributes:
        path
            Location to the created temporary directory
        delete
            Whether the directory should be deleted when exiting
            (when used as a contextmanager)

    Methods:
        cleanup()
            Deletes the temporary directory

    When used as a context manager, if the delete attribute is True, on
    exiting the context the temporary directory is deleted.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        delete: Union[bool, None, _Default] = _default,
        kind: str = "temp",
        globally_managed: bool = False,
        ignore_cleanup_errors: bool = True,
    ):
        super().__init__()

        if delete is _default:
            if path is not None:
                # If we were given an explicit directory, resolve delete option
                # now.
                delete = False
            else:
                # Otherwise, we wait until cleanup and see what
                # tempdir_registry says.
                delete = None

        # The only time we specify path is in for editables where it
        # is the value of the --src option.
        if path is None:
            path = self._create(kind)

        self._path = path
        self._deleted = False
        self.delete = delete
        self.kind = kind
        self.ignore_cleanup_errors = ignore_cleanup_errors

        if globally_managed:
            assert _tempdir_manager is not None
            _tempdir_manager.enter_context(self)

    @property
    def path(self) -> str:
        assert not self._deleted, f"Attempted to access deleted path: {self._path}"
        return self._path

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.path!r}>"

    def __enter__(self: _T) -> _T:
        return self

    def __exit__(self, exc: Any, value: Any, tb: Any) -> None:
        if self.delete is not None:
            delete = self.delete
        elif _tempdir_registry:
            delete = _tempdir_registry.get_delete(self.kind)
        else:
            delete = True

        if delete:
            self.cleanup()

    def _create(self, kind: str) -> str:
        """Create a temporary directory and store its path in self.path"""
        # We realpath here because some systems have their default tmpdir
        # symlinked to another directory.  This tends to confuse build
        # scripts, so we canonicalize the path by traversing potential
        # symlinks here.
        path = os.path.realpath(tempfile.mkdtemp(prefix=f"pip-{kind}-"))
        logger.debug("Created temporary directory: %s", path)
        return path

    def cleanup(self) -> None:
        """Remove the temporary directory created and reset state"""
        self._deleted = True
        if not os.path.exists(self._path):
            return

        errors: List[BaseException] = []

        def onerror(
            func: Callable[..., Any],
            path: Path,
            exc_val: BaseException,
        ) -> None:
            """Log a warning for a `rmtree` error and continue"""
            formatted_exc = "\n".join(
                traceback.format_exception_only(type(exc_val), exc_val)
            )
            formatted_exc = formatted_exc.rstrip()  # remove trailing new line
            if func in (os.unlink, os.remove, os.rmdir):
                logger.debug(
                    "Failed to remove a temporary file '%s' due to %s.\n",
                    path,
                    formatted_exc,
                )
            else:
                logger.debug("%s failed with %s.", func.__qualname__, formatted_exc)
            errors.append(exc_val)

        if self.ignore_cleanup_errors:
            try:
                # first try with @retry; retrying to handle ephemeral errors
                rmtree(self._path, ignore_errors=False)
            except OSError:
                # last pass ignore/log all errors
                rmtree(self._path, onexc=onerror)
            if errors:
                logger.warning(
                    "Failed to remove contents in a temporary directory '%s'.\n"
                    "You can safely remove it manually.",
                    self._path,
                )
        else:
            rmtree(self._path)


class AdjacentTempDirectory(TempDirectory):
    """Helper class that creates a temporary directory adjacent to a real one.

    Attributes:
        original
            The original directory to create a temp directory for.
        path
            After calling create() or entering, contains the full
            path to the temporary directory.
        delete
            Whether the directory should be deleted when exiting
            (when used as a contextmanager)

    """

    # The characters that may be used to name the temp directory
    # We always prepend a ~ and then rotate through these until
    # a usable name is found.
    # pkg_resources raises a different error for .dist-info folder
    # with leading '-' and invalid metadata
    LEADING_CHARS = "-~.=%0123456789"

    def __init__(self, original: str, delete: Optional[bool] = None) -> None:
        self.original = original.rstrip("/\\")
        super().__init__(delete=delete)

    @classmethod
    def _generate_names(cls, name: str) -> Generator[str, None, None]:
        """Generates a series of temporary names.

        The algorithm replaces the leading characters in the name
        with ones that are valid filesystem characters, but are not
        valid package names (for both Python and pip definitions of
        package).
        """
        for i in range(1, len(name)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i - 1
            ):
                new_name = "~" + "".join(candidate) + name[i:]
                if new_name != name:
                    yield new_name

        # If we make it this far, we will have to make a longer name
        for i in range(len(cls.LEADING_CHARS)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i
            ):
                new_name = "~" + "".join(candidate) + name
                if new_name != name:
                    yield new_name

    def _create(self, kind: str) -> str:
        root, name = os.path.split(self.original)
        for candidate in self._generate_names(name):
            path = os.path.join(root, candidate)
            try:
                os.mkdir(path)
            except OSError as ex:
                # Continue if the name exists already
                if ex.errno != errno.EEXIST:
                    raise
            else:
                path = os.path.realpath(path)
                break
        else:
            # Final fallback on the default behavior.
            path = os.path.realpath(tempfile.mkdtemp(prefix=f"pip-{kind}-"))

        logger.debug("Created temporary directory: %s", path)
        return path

# === NexusCore/openenv\Lib\site-packages\click\_winconsole.py ===
# This module is based on the excellent work by Adam Bartoš who
# provided a lot of what went into the implementation here in
# the discussion to issue1602 in the Python bug tracker.
#
# There are some general differences in regards to how this works
# compared to the original patches as we do not need to patch
# the entire interpreter but just work in our little world of
# echo and prompt.
from __future__ import annotations

import collections.abc as cabc
import io
import sys
import time
import typing as t
from ctypes import Array
from ctypes import byref
from ctypes import c_char
from ctypes import c_char_p
from ctypes import c_int
from ctypes import c_ssize_t
from ctypes import c_ulong
from ctypes import c_void_p
from ctypes import POINTER
from ctypes import py_object
from ctypes import Structure
from ctypes.wintypes import DWORD
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LPCWSTR
from ctypes.wintypes import LPWSTR

from ._compat import _NonClosingTextIOWrapper

assert sys.platform == "win32"
import msvcrt  # noqa: E402
from ctypes import windll  # noqa: E402
from ctypes import WINFUNCTYPE  # noqa: E402

c_ssize_p = POINTER(c_ssize_t)

kernel32 = windll.kernel32
GetStdHandle = kernel32.GetStdHandle
ReadConsoleW = kernel32.ReadConsoleW
WriteConsoleW = kernel32.WriteConsoleW
GetConsoleMode = kernel32.GetConsoleMode
GetLastError = kernel32.GetLastError
GetCommandLineW = WINFUNCTYPE(LPWSTR)(("GetCommandLineW", windll.kernel32))
CommandLineToArgvW = WINFUNCTYPE(POINTER(LPWSTR), LPCWSTR, POINTER(c_int))(
    ("CommandLineToArgvW", windll.shell32)
)
LocalFree = WINFUNCTYPE(c_void_p, c_void_p)(("LocalFree", windll.kernel32))

STDIN_HANDLE = GetStdHandle(-10)
STDOUT_HANDLE = GetStdHandle(-11)
STDERR_HANDLE = GetStdHandle(-12)

PyBUF_SIMPLE = 0
PyBUF_WRITABLE = 1

ERROR_SUCCESS = 0
ERROR_NOT_ENOUGH_MEMORY = 8
ERROR_OPERATION_ABORTED = 995

STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2

EOF = b"\x1a"
MAX_BYTES_WRITTEN = 32767

if t.TYPE_CHECKING:
    try:
        # Using `typing_extensions.Buffer` instead of `collections.abc`
        # on Windows for some reason does not have `Sized` implemented.
        from collections.abc import Buffer  # type: ignore
    except ImportError:
        from typing_extensions import Buffer

try:
    from ctypes import pythonapi
except ImportError:
    # On PyPy we cannot get buffers so our ability to operate here is
    # severely limited.
    get_buffer = None
else:

    class Py_buffer(Structure):
        _fields_ = [  # noqa: RUF012
            ("buf", c_void_p),
            ("obj", py_object),
            ("len", c_ssize_t),
            ("itemsize", c_ssize_t),
            ("readonly", c_int),
            ("ndim", c_int),
            ("format", c_char_p),
            ("shape", c_ssize_p),
            ("strides", c_ssize_p),
            ("suboffsets", c_ssize_p),
            ("internal", c_void_p),
        ]

    PyObject_GetBuffer = pythonapi.PyObject_GetBuffer
    PyBuffer_Release = pythonapi.PyBuffer_Release

    def get_buffer(obj: Buffer, writable: bool = False) -> Array[c_char]:
        buf = Py_buffer()
        flags: int = PyBUF_WRITABLE if writable else PyBUF_SIMPLE
        PyObject_GetBuffer(py_object(obj), byref(buf), flags)

        try:
            buffer_type = c_char * buf.len
            out: Array[c_char] = buffer_type.from_address(buf.buf)
            return out
        finally:
            PyBuffer_Release(byref(buf))


class _WindowsConsoleRawIOBase(io.RawIOBase):
    def __init__(self, handle: int | None) -> None:
        self.handle = handle

    def isatty(self) -> t.Literal[True]:
        super().isatty()
        return True


class _WindowsConsoleReader(_WindowsConsoleRawIOBase):
    def readable(self) -> t.Literal[True]:
        return True

    def readinto(self, b: Buffer) -> int:
        bytes_to_be_read = len(b)
        if not bytes_to_be_read:
            return 0
        elif bytes_to_be_read % 2:
            raise ValueError(
                "cannot read odd number of bytes from UTF-16-LE encoded console"
            )

        buffer = get_buffer(b, writable=True)
        code_units_to_be_read = bytes_to_be_read // 2
        code_units_read = c_ulong()

        rv = ReadConsoleW(
            HANDLE(self.handle),
            buffer,
            code_units_to_be_read,
            byref(code_units_read),
            None,
        )
        if GetLastError() == ERROR_OPERATION_ABORTED:
            # wait for KeyboardInterrupt
            time.sleep(0.1)
        if not rv:
            raise OSError(f"Windows error: {GetLastError()}")

        if buffer[0] == EOF:
            return 0
        return 2 * code_units_read.value


class _WindowsConsoleWriter(_WindowsConsoleRawIOBase):
    def writable(self) -> t.Literal[True]:
        return True

    @staticmethod
    def _get_error_message(errno: int) -> str:
        if errno == ERROR_SUCCESS:
            return "ERROR_SUCCESS"
        elif errno == ERROR_NOT_ENOUGH_MEMORY:
            return "ERROR_NOT_ENOUGH_MEMORY"
        return f"Windows error {errno}"

    def write(self, b: Buffer) -> int:
        bytes_to_be_written = len(b)
        buf = get_buffer(b)
        code_units_to_be_written = min(bytes_to_be_written, MAX_BYTES_WRITTEN) // 2
        code_units_written = c_ulong()

        WriteConsoleW(
            HANDLE(self.handle),
            buf,
            code_units_to_be_written,
            byref(code_units_written),
            None,
        )
        bytes_written = 2 * code_units_written.value

        if bytes_written == 0 and bytes_to_be_written > 0:
            raise OSError(self._get_error_message(GetLastError()))
        return bytes_written


class ConsoleStream:
    def __init__(self, text_stream: t.TextIO, byte_stream: t.BinaryIO) -> None:
        self._text_stream = text_stream
        self.buffer = byte_stream

    @property
    def name(self) -> str:
        return self.buffer.name

    def write(self, x: t.AnyStr) -> int:
        if isinstance(x, str):
            return self._text_stream.write(x)
        try:
            self.flush()
        except Exception:
            pass
        return self.buffer.write(x)

    def writelines(self, lines: cabc.Iterable[t.AnyStr]) -> None:
        for line in lines:
            self.write(line)

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._text_stream, name)

    def isatty(self) -> bool:
        return self.buffer.isatty()

    def __repr__(self) -> str:
        return f"<ConsoleStream name={self.name!r} encoding={self.encoding!r}>"


def _get_text_stdin(buffer_stream: t.BinaryIO) -> t.TextIO:
    text_stream = _NonClosingTextIOWrapper(
        io.BufferedReader(_WindowsConsoleReader(STDIN_HANDLE)),
        "utf-16-le",
        "strict",
        line_buffering=True,
    )
    return t.cast(t.TextIO, ConsoleStream(text_stream, buffer_stream))


def _get_text_stdout(buffer_stream: t.BinaryIO) -> t.TextIO:
    text_stream = _NonClosingTextIOWrapper(
        io.BufferedWriter(_WindowsConsoleWriter(STDOUT_HANDLE)),
        "utf-16-le",
        "strict",
        line_buffering=True,
    )
    return t.cast(t.TextIO, ConsoleStream(text_stream, buffer_stream))


def _get_text_stderr(buffer_stream: t.BinaryIO) -> t.TextIO:
    text_stream = _NonClosingTextIOWrapper(
        io.BufferedWriter(_WindowsConsoleWriter(STDERR_HANDLE)),
        "utf-16-le",
        "strict",
        line_buffering=True,
    )
    return t.cast(t.TextIO, ConsoleStream(text_stream, buffer_stream))


_stream_factories: cabc.Mapping[int, t.Callable[[t.BinaryIO], t.TextIO]] = {
    0: _get_text_stdin,
    1: _get_text_stdout,
    2: _get_text_stderr,
}


def _is_console(f: t.TextIO) -> bool:
    if not hasattr(f, "fileno"):
        return False

    try:
        fileno = f.fileno()
    except (OSError, io.UnsupportedOperation):
        return False

    handle = msvcrt.get_osfhandle(fileno)
    return bool(GetConsoleMode(handle, byref(DWORD())))


def _get_windows_console_stream(
    f: t.TextIO, encoding: str | None, errors: str | None
) -> t.TextIO | None:
    if (
        get_buffer is None
        or encoding not in {"utf-16-le", None}
        or errors not in {"strict", None}
        or not _is_console(f)
    ):
        return None

    func = _stream_factories.get(f.fileno())
    if func is None:
        return None

    b = getattr(f, "buffer", None)

    if b is None:
        return None

    return func(b)

# === NexusCore/openenv\Lib\site-packages\jsonschema\cli.py ===
"""
The ``jsonschema`` command line.
"""

from importlib import metadata
from json import JSONDecodeError
from textwrap import dedent
import argparse
import json
import sys
import traceback
import warnings

try:
    from pkgutil import resolve_name
except ImportError:
    from pkgutil_resolve_name import resolve_name  # type: ignore[no-redef]

from attrs import define, field

from jsonschema.exceptions import SchemaError
from jsonschema.validators import _RefResolver, validator_for

warnings.warn(
    (
        "The jsonschema CLI is deprecated and will be removed in a future "
        "version. Please use check-jsonschema instead, which can be installed "
        "from https://pypi.org/project/check-jsonschema/"
    ),
    DeprecationWarning,
    stacklevel=2,
)


class _CannotLoadFile(Exception):
    pass


@define
class _Outputter:

    _formatter = field()
    _stdout = field()
    _stderr = field()

    @classmethod
    def from_arguments(cls, arguments, stdout, stderr):
        if arguments["output"] == "plain":
            formatter = _PlainFormatter(arguments["error_format"])
        elif arguments["output"] == "pretty":
            formatter = _PrettyFormatter()
        return cls(formatter=formatter, stdout=stdout, stderr=stderr)

    def load(self, path):
        try:
            file = open(path)  # noqa: SIM115, PTH123
        except FileNotFoundError as error:
            self.filenotfound_error(path=path, exc_info=sys.exc_info())
            raise _CannotLoadFile() from error

        with file:
            try:
                return json.load(file)
            except JSONDecodeError as error:
                self.parsing_error(path=path, exc_info=sys.exc_info())
                raise _CannotLoadFile() from error

    def filenotfound_error(self, **kwargs):
        self._stderr.write(self._formatter.filenotfound_error(**kwargs))

    def parsing_error(self, **kwargs):
        self._stderr.write(self._formatter.parsing_error(**kwargs))

    def validation_error(self, **kwargs):
        self._stderr.write(self._formatter.validation_error(**kwargs))

    def validation_success(self, **kwargs):
        self._stdout.write(self._formatter.validation_success(**kwargs))


@define
class _PrettyFormatter:

    _ERROR_MSG = dedent(
        """\
        ===[{type}]===({path})===

        {body}
        -----------------------------
        """,
    )
    _SUCCESS_MSG = "===[SUCCESS]===({path})===\n"

    def filenotfound_error(self, path, exc_info):
        return self._ERROR_MSG.format(
            path=path,
            type="FileNotFoundError",
            body=f"{path!r} does not exist.",
        )

    def parsing_error(self, path, exc_info):
        exc_type, exc_value, exc_traceback = exc_info
        exc_lines = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback),
        )
        return self._ERROR_MSG.format(
            path=path,
            type=exc_type.__name__,
            body=exc_lines,
        )

    def validation_error(self, instance_path, error):
        return self._ERROR_MSG.format(
            path=instance_path,
            type=error.__class__.__name__,
            body=error,
        )

    def validation_success(self, instance_path):
        return self._SUCCESS_MSG.format(path=instance_path)


@define
class _PlainFormatter:

    _error_format = field()

    def filenotfound_error(self, path, exc_info):
        return f"{path!r} does not exist.\n"

    def parsing_error(self, path, exc_info):
        return "Failed to parse {}: {}\n".format(
            "<stdin>" if path == "<stdin>" else repr(path),
            exc_info[1],
        )

    def validation_error(self, instance_path, error):
        return self._error_format.format(file_name=instance_path, error=error)

    def validation_success(self, instance_path):
        return ""


def _resolve_name_with_default(name):
    if "." not in name:
        name = "jsonschema." + name
    return resolve_name(name)


parser = argparse.ArgumentParser(
    description="JSON Schema Validation CLI",
)
parser.add_argument(
    "-i", "--instance",
    action="append",
    dest="instances",
    help="""
        a path to a JSON instance (i.e. filename.json) to validate (may
        be specified multiple times). If no instances are provided via this
        option, one will be expected on standard input.
    """,
)
parser.add_argument(
    "-F", "--error-format",
    help="""
        the format to use for each validation error message, specified
        in a form suitable for str.format. This string will be passed
        one formatted object named 'error' for each ValidationError.
        Only provide this option when using --output=plain, which is the
        default. If this argument is unprovided and --output=plain is
        used, a simple default representation will be used.
    """,
)
parser.add_argument(
    "-o", "--output",
    choices=["plain", "pretty"],
    default="plain",
    help="""
        an output format to use. 'plain' (default) will produce minimal
        text with one line for each error, while 'pretty' will produce
        more detailed human-readable output on multiple lines.
    """,
)
parser.add_argument(
    "-V", "--validator",
    type=_resolve_name_with_default,
    help="""
        the fully qualified object name of a validator to use, or, for
        validators that are registered with jsonschema, simply the name
        of the class.
    """,
)
parser.add_argument(
    "--base-uri",
    help="""
        a base URI to assign to the provided schema, even if it does not
        declare one (via e.g. $id). This option can be used if you wish to
        resolve relative references to a particular URI (or local path)
    """,
)
parser.add_argument(
    "--version",
    action="version",
    version=metadata.version("jsonschema"),
)
parser.add_argument(
    "schema",
    help="the path to a JSON Schema to validate with (i.e. schema.json)",
)


def parse_args(args):  # noqa: D103
    arguments = vars(parser.parse_args(args=args or ["--help"]))
    if arguments["output"] != "plain" and arguments["error_format"]:
        raise parser.error(
            "--error-format can only be used with --output plain",
        )
    if arguments["output"] == "plain" and arguments["error_format"] is None:
        arguments["error_format"] = "{error.instance}: {error.message}\n"
    return arguments


def _validate_instance(instance_path, instance, validator, outputter):
    invalid = False
    for error in validator.iter_errors(instance):
        invalid = True
        outputter.validation_error(instance_path=instance_path, error=error)

    if not invalid:
        outputter.validation_success(instance_path=instance_path)
    return invalid


def main(args=sys.argv[1:]):  # noqa: D103
    sys.exit(run(arguments=parse_args(args=args)))


def run(arguments, stdout=sys.stdout, stderr=sys.stderr, stdin=sys.stdin):  # noqa: D103
    outputter = _Outputter.from_arguments(
        arguments=arguments,
        stdout=stdout,
        stderr=stderr,
    )

    try:
        schema = outputter.load(arguments["schema"])
    except _CannotLoadFile:
        return 1

    Validator = arguments["validator"]
    if Validator is None:
        Validator = validator_for(schema)

    try:
        Validator.check_schema(schema)
    except SchemaError as error:
        outputter.validation_error(
            instance_path=arguments["schema"],
            error=error,
        )
        return 1

    if arguments["instances"]:
        load, instances = outputter.load, arguments["instances"]
    else:
        def load(_):
            try:
                return json.load(stdin)
            except JSONDecodeError as error:
                outputter.parsing_error(
                    path="<stdin>", exc_info=sys.exc_info(),
                )
                raise _CannotLoadFile() from error
        instances = ["<stdin>"]

    resolver = _RefResolver(
        base_uri=arguments["base_uri"],
        referrer=schema,
    ) if arguments["base_uri"] is not None else None

    validator = Validator(schema, resolver=resolver)
    exit_code = 0
    for each in instances:
        try:
            instance = load(each)
        except _CannotLoadFile:
            exit_code = 1
        else:
            exit_code |= _validate_instance(
                instance_path=each,
                instance=instance,
                validator=validator,
                outputter=outputter,
            )

    return exit_code

# === NexusCore/openenv\Lib\site-packages\jedi\plugins\django.py ===
"""
Module is used to infer Django model fields.
"""
from inspect import Parameter

from jedi import debug
from jedi.inference.cache import inference_state_function_cache
from jedi.inference.base_value import ValueSet, iterator_to_value_set, ValueWrapper
from jedi.inference.filters import DictFilter, AttributeOverwrite
from jedi.inference.names import NameWrapper, BaseTreeParamName
from jedi.inference.compiled.value import EmptyCompiledName
from jedi.inference.value.instance import TreeInstance
from jedi.inference.value.klass import ClassMixin
from jedi.inference.gradual.base import GenericClass
from jedi.inference.gradual.generics import TupleGenericManager
from jedi.inference.signature import AbstractSignature


mapping = {
    'IntegerField': (None, 'int'),
    'BigIntegerField': (None, 'int'),
    'PositiveIntegerField': (None, 'int'),
    'SmallIntegerField': (None, 'int'),
    'CharField': (None, 'str'),
    'TextField': (None, 'str'),
    'EmailField': (None, 'str'),
    'GenericIPAddressField': (None, 'str'),
    'URLField': (None, 'str'),
    'FloatField': (None, 'float'),
    'BinaryField': (None, 'bytes'),
    'BooleanField': (None, 'bool'),
    'DecimalField': ('decimal', 'Decimal'),
    'TimeField': ('datetime', 'time'),
    'DurationField': ('datetime', 'timedelta'),
    'DateField': ('datetime', 'date'),
    'DateTimeField': ('datetime', 'datetime'),
    'UUIDField': ('uuid', 'UUID'),
}

_FILTER_LIKE_METHODS = ('create', 'filter', 'exclude', 'update', 'get',
                        'get_or_create', 'update_or_create')


@inference_state_function_cache()
def _get_deferred_attributes(inference_state):
    return inference_state.import_module(
        ('django', 'db', 'models', 'query_utils')
    ).py__getattribute__('DeferredAttribute').execute_annotation()


def _infer_scalar_field(inference_state, field_name, field_tree_instance, is_instance):
    try:
        module_name, attribute_name = mapping[field_tree_instance.py__name__()]
    except KeyError:
        return None

    if not is_instance:
        return _get_deferred_attributes(inference_state)

    if module_name is None:
        module = inference_state.builtins_module
    else:
        module = inference_state.import_module((module_name,))

    for attribute in module.py__getattribute__(attribute_name):
        return attribute.execute_with_values()


@iterator_to_value_set
def _get_foreign_key_values(cls, field_tree_instance):
    if isinstance(field_tree_instance, TreeInstance):
        # TODO private access..
        argument_iterator = field_tree_instance._arguments.unpack()
        key, lazy_values = next(argument_iterator, (None, None))
        if key is None and lazy_values is not None:
            for value in lazy_values.infer():
                if value.py__name__() == 'str':
                    foreign_key_class_name = value.get_safe_value()
                    module = cls.get_root_context()
                    for v in module.py__getattribute__(foreign_key_class_name):
                        if v.is_class():
                            yield v
                elif value.is_class():
                    yield value


def _infer_field(cls, field_name, is_instance):
    inference_state = cls.inference_state
    result = field_name.infer()
    for field_tree_instance in result:
        scalar_field = _infer_scalar_field(
            inference_state, field_name, field_tree_instance, is_instance)
        if scalar_field is not None:
            return scalar_field

        name = field_tree_instance.py__name__()
        is_many_to_many = name == 'ManyToManyField'
        if name in ('ForeignKey', 'OneToOneField') or is_many_to_many:
            if not is_instance:
                return _get_deferred_attributes(inference_state)

            values = _get_foreign_key_values(cls, field_tree_instance)
            if is_many_to_many:
                return ValueSet(filter(None, [
                    _create_manager_for(v, 'RelatedManager') for v in values
                ]))
            else:
                return values.execute_with_values()

    debug.dbg('django plugin: fail to infer `%s` from class `%s`',
              field_name.string_name, cls.py__name__())
    return result


class DjangoModelName(NameWrapper):
    def __init__(self, cls, name, is_instance):
        super().__init__(name)
        self._cls = cls
        self._is_instance = is_instance

    def infer(self):
        return _infer_field(self._cls, self._wrapped_name, self._is_instance)


def _create_manager_for(cls, manager_cls='BaseManager'):
    managers = cls.inference_state.import_module(
        ('django', 'db', 'models', 'manager')
    ).py__getattribute__(manager_cls)
    for m in managers:
        if m.is_class_mixin():
            generics_manager = TupleGenericManager((ValueSet([cls]),))
            for c in GenericClass(m, generics_manager).execute_annotation():
                return c
    return None


def _new_dict_filter(cls, is_instance):
    filters = list(cls.get_filters(
        is_instance=is_instance,
        include_metaclasses=False,
        include_type_when_class=False)
    )
    dct = {
        name.string_name: DjangoModelName(cls, name, is_instance)
        for filter_ in reversed(filters)
        for name in filter_.values()
    }
    if is_instance:
        # Replace the objects with a name that amounts to nothing when accessed
        # in an instance. This is not perfect and still completes "objects" in
        # that case, but it at least not inferes stuff like `.objects.filter`.
        # It would be nicer to do that in a better way, so that it also doesn't
        # show up in completions, but it's probably just not worth doing that
        # for the extra amount of work.
        dct['objects'] = EmptyCompiledName(cls.inference_state, 'objects')

    return DictFilter(dct)


def is_django_model_base(value):
    return value.py__name__() == 'ModelBase' \
        and value.get_root_context().py__name__() == 'django.db.models.base'


def get_metaclass_filters(func):
    def wrapper(cls, metaclasses, is_instance):
        for metaclass in metaclasses:
            if is_django_model_base(metaclass):
                return [_new_dict_filter(cls, is_instance)]

        return func(cls, metaclasses, is_instance)
    return wrapper


def tree_name_to_values(func):
    def wrapper(inference_state, context, tree_name):
        result = func(inference_state, context, tree_name)
        if tree_name.value in _FILTER_LIKE_METHODS:
            # Here we try to overwrite stuff like User.objects.filter. We need
            # this to make sure that keyword param completion works on these
            # kind of methods.
            for v in result:
                if v.get_qualified_names() == ('_BaseQuerySet', tree_name.value) \
                        and v.parent_context.is_module() \
                        and v.parent_context.py__name__() == 'django.db.models.query':
                    qs = context.get_value()
                    generics = qs.get_generics()
                    if len(generics) >= 1:
                        return ValueSet(QuerySetMethodWrapper(v, model)
                                        for model in generics[0])

        elif tree_name.value == 'BaseManager' and context.is_module() \
                and context.py__name__() == 'django.db.models.manager':
            return ValueSet(ManagerWrapper(r) for r in result)

        elif tree_name.value == 'Field' and context.is_module() \
                and context.py__name__() == 'django.db.models.fields':
            return ValueSet(FieldWrapper(r) for r in result)
        return result
    return wrapper


def _find_fields(cls):
    for name in _new_dict_filter(cls, is_instance=False).values():
        for value in name.infer():
            if value.name.get_qualified_names(include_module_names=True) \
                    == ('django', 'db', 'models', 'query_utils', 'DeferredAttribute'):
                yield name


def _get_signatures(cls):
    return [DjangoModelSignature(cls, field_names=list(_find_fields(cls)))]


def get_metaclass_signatures(func):
    def wrapper(cls, metaclasses):
        for metaclass in metaclasses:
            if is_django_model_base(metaclass):
                return _get_signatures(cls)
        return func(cls, metaclass)
    return wrapper


class ManagerWrapper(ValueWrapper):
    def py__getitem__(self, index_value_set, contextualized_node):
        return ValueSet(
            GenericManagerWrapper(generic)
            for generic in self._wrapped_value.py__getitem__(
                index_value_set, contextualized_node)
        )


class GenericManagerWrapper(AttributeOverwrite, ClassMixin):
    def py__get__on_class(self, calling_instance, instance, class_value):
        return calling_instance.class_value.with_generics(
            (ValueSet({class_value}),)
        ).py__call__(calling_instance._arguments)

    def with_generics(self, generics_tuple):
        return self._wrapped_value.with_generics(generics_tuple)


class FieldWrapper(ValueWrapper):
    def py__getitem__(self, index_value_set, contextualized_node):
        return ValueSet(
            GenericFieldWrapper(generic)
            for generic in self._wrapped_value.py__getitem__(
                index_value_set, contextualized_node)
        )


class GenericFieldWrapper(AttributeOverwrite, ClassMixin):
    def py__get__on_class(self, calling_instance, instance, class_value):
        # This is mostly an optimization to avoid Jedi aborting inference,
        # because of too many function executions of Field.__get__.
        return ValueSet({calling_instance})


class DjangoModelSignature(AbstractSignature):
    def __init__(self, value, field_names):
        super().__init__(value)
        self._field_names = field_names

    def get_param_names(self, resolve_stars=False):
        return [DjangoParamName(name) for name in self._field_names]


class DjangoParamName(BaseTreeParamName):
    def __init__(self, field_name):
        super().__init__(field_name.parent_context, field_name.tree_name)
        self._field_name = field_name

    def get_kind(self):
        return Parameter.KEYWORD_ONLY

    def infer(self):
        return self._field_name.infer()


class QuerySetMethodWrapper(ValueWrapper):
    def __init__(self, method, model_cls):
        super().__init__(method)
        self._model_cls = model_cls

    def py__get__(self, instance, class_value):
        return ValueSet({QuerySetBoundMethodWrapper(v, self._model_cls)
                         for v in self._wrapped_value.py__get__(instance, class_value)})


class QuerySetBoundMethodWrapper(ValueWrapper):
    def __init__(self, method, model_cls):
        super().__init__(method)
        self._model_cls = model_cls

    def get_signatures(self):
        return _get_signatures(self._model_cls)

# === NexusCore/openenv\Lib\site-packages\nltk\tag\api.py ===
# Natural Language Toolkit: Tagger Interface
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interface for tagging each token in a sentence with supplementary
information, such as its part of speech.
"""
from abc import ABCMeta, abstractmethod
from functools import lru_cache
from itertools import chain
from typing import Dict

from nltk.internals import deprecated, overridden
from nltk.metrics import ConfusionMatrix, accuracy
from nltk.tag.util import untag


class TaggerI(metaclass=ABCMeta):
    """
    A processing interface for assigning a tag to each token in a list.
    Tags are case sensitive strings that identify some property of each
    token, such as its part of speech or its sense.

    Some taggers require specific types for their tokens.  This is
    generally indicated by the use of a sub-interface to ``TaggerI``.
    For example, featureset taggers, which are subclassed from
    ``FeaturesetTagger``, require that each token be a ``featureset``.

    Subclasses must define:
      - either ``tag()`` or ``tag_sents()`` (or both)
    """

    @abstractmethod
    def tag(self, tokens):
        """
        Determine the most appropriate tag sequence for the given
        token sequence, and return a corresponding list of tagged
        tokens.  A tagged token is encoded as a tuple ``(token, tag)``.

        :rtype: list(tuple(str, str))
        """
        if overridden(self.tag_sents):
            return self.tag_sents([tokens])[0]

    def tag_sents(self, sentences):
        """
        Apply ``self.tag()`` to each element of *sentences*.  I.e.::

            return [self.tag(sent) for sent in sentences]
        """
        return [self.tag(sent) for sent in sentences]

    @deprecated("Use accuracy(gold) instead.")
    def evaluate(self, gold):
        return self.accuracy(gold)

    def accuracy(self, gold):
        """
        Score the accuracy of the tagger against the gold standard.
        Strip the tags from the gold standard text, retag it using
        the tagger, then compute the accuracy score.

        :param gold: The list of tagged sentences to score the tagger on.
        :type gold: list(list(tuple(str, str)))
        :rtype: float
        """

        tagged_sents = self.tag_sents(untag(sent) for sent in gold)
        gold_tokens = list(chain.from_iterable(gold))
        test_tokens = list(chain.from_iterable(tagged_sents))
        return accuracy(gold_tokens, test_tokens)

    @lru_cache(maxsize=1)
    def _confusion_cached(self, gold):
        """
        Inner function used after ``gold`` is converted to a
        ``tuple(tuple(tuple(str, str)))``. That way, we can use caching on
        creating a ConfusionMatrix.

        :param gold: The list of tagged sentences to run the tagger with,
            also used as the reference values in the generated confusion matrix.
        :type gold: tuple(tuple(tuple(str, str)))
        :rtype: ConfusionMatrix
        """

        tagged_sents = self.tag_sents(untag(sent) for sent in gold)
        gold_tokens = [token for _word, token in chain.from_iterable(gold)]
        test_tokens = [token for _word, token in chain.from_iterable(tagged_sents)]
        return ConfusionMatrix(gold_tokens, test_tokens)

    def confusion(self, gold):
        """
        Return a ConfusionMatrix with the tags from ``gold`` as the reference
        values, with the predictions from ``tag_sents`` as the predicted values.

        >>> from nltk.tag import PerceptronTagger
        >>> from nltk.corpus import treebank
        >>> tagger = PerceptronTagger()
        >>> gold_data = treebank.tagged_sents()[:10]
        >>> print(tagger.confusion(gold_data))
               |        -                                                                                     |
               |        N                                                                                     |
               |        O                                               P                                     |
               |        N                       J  J        N  N  P  P  R     R           V  V  V  V  V  W    |
               |  '     E     C  C  D  E  I  J  J  J  M  N  N  N  O  R  P  R  B  R  T  V  B  B  B  B  B  D  ` |
               |  '  ,  -  .  C  D  T  X  N  J  R  S  D  N  P  S  S  P  $  B  R  P  O  B  D  G  N  P  Z  T  ` |
        -------+----------------------------------------------------------------------------------------------+
            '' | <1> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
             , |  .<15> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
        -NONE- |  .  . <.> .  .  2  .  .  .  2  .  .  .  5  1  .  .  .  .  2  .  .  .  .  .  .  .  .  .  .  . |
             . |  .  .  .<10> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            CC |  .  .  .  . <1> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            CD |  .  .  .  .  . <5> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            DT |  .  .  .  .  .  .<20> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            EX |  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            IN |  .  .  .  .  .  .  .  .<22> .  .  .  .  .  .  .  .  .  .  3  .  .  .  .  .  .  .  .  .  .  . |
            JJ |  .  .  .  .  .  .  .  .  .<16> .  .  .  .  1  .  .  .  .  1  .  .  .  .  .  .  .  .  .  .  . |
           JJR |  .  .  .  .  .  .  .  .  .  . <.> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
           JJS |  .  .  .  .  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            MD |  .  .  .  .  .  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
            NN |  .  .  .  .  .  .  .  .  .  .  .  .  .<28> 1  1  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
           NNP |  .  .  .  .  .  .  .  .  .  .  .  .  .  .<25> .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
           NNS |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .<19> .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
           POS |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  .  .  .  .  .  . |
           PRP |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <4> .  .  .  .  .  .  .  .  .  .  .  .  . |
          PRP$ |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <2> .  .  .  .  .  .  .  .  .  .  .  . |
            RB |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <4> .  .  .  .  .  .  .  .  .  .  . |
           RBR |  .  .  .  .  .  .  .  .  .  .  1  .  .  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  .  . |
            RP |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <1> .  .  .  .  .  .  .  .  . |
            TO |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <5> .  .  .  .  .  .  .  . |
            VB |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <3> .  .  .  .  .  .  . |
           VBD |  .  .  .  .  .  .  .  .  .  .  .  .  .  1  .  .  .  .  .  .  .  .  .  . <6> .  .  .  .  .  . |
           VBG |  .  .  .  .  .  .  .  .  .  .  .  .  .  1  .  .  .  .  .  .  .  .  .  .  . <4> .  .  .  .  . |
           VBN |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  1  . <4> .  .  .  . |
           VBP |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <3> .  .  . |
           VBZ |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <7> .  . |
           WDT |  .  .  .  .  .  .  .  .  2  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <.> . |
            `` |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . <1>|
        -------+----------------------------------------------------------------------------------------------+
        (row = reference; col = test)
        <BLANKLINE>

        :param gold: The list of tagged sentences to run the tagger with,
            also used as the reference values in the generated confusion matrix.
        :type gold: list(list(tuple(str, str)))
        :rtype: ConfusionMatrix
        """

        return self._confusion_cached(tuple(tuple(sent) for sent in gold))

    def recall(self, gold) -> Dict[str, float]:
        """
        Compute the recall for each tag from ``gold`` or from running ``tag``
        on the tokenized sentences from ``gold``. Then, return the dictionary
        with mappings from tag to recall. The recall is defined as:

        - *r* = true positive / (true positive + false positive)

        :param gold: The list of tagged sentences to score the tagger on.
        :type gold: list(list(tuple(str, str)))
        :return: A mapping from tags to recall
        :rtype: Dict[str, float]
        """

        cm = self.confusion(gold)
        return {tag: cm.recall(tag) for tag in cm._values}

    def precision(self, gold):
        """
        Compute the precision for each tag from ``gold`` or from running ``tag``
        on the tokenized sentences from ``gold``. Then, return the dictionary
        with mappings from tag to precision. The precision is defined as:

        - *p* = true positive / (true positive + false negative)

        :param gold: The list of tagged sentences to score the tagger on.
        :type gold: list(list(tuple(str, str)))
        :return: A mapping from tags to precision
        :rtype: Dict[str, float]
        """

        cm = self.confusion(gold)
        return {tag: cm.precision(tag) for tag in cm._values}

    def f_measure(self, gold, alpha=0.5):
        """
        Compute the f-measure for each tag from ``gold`` or from running ``tag``
        on the tokenized sentences from ``gold``. Then, return the dictionary
        with mappings from tag to f-measure. The f-measure is the harmonic mean
        of the ``precision`` and ``recall``, weighted by ``alpha``.
        In particular, given the precision *p* and recall *r* defined by:

        - *p* = true positive / (true positive + false negative)
        - *r* = true positive / (true positive + false positive)

        The f-measure is:

        - *1/(alpha/p + (1-alpha)/r)*

        With ``alpha = 0.5``, this reduces to:

        - *2pr / (p + r)*

        :param gold: The list of tagged sentences to score the tagger on.
        :type gold: list(list(tuple(str, str)))
        :param alpha: Ratio of the cost of false negative compared to false
            positives. Defaults to 0.5, where the costs are equal.
        :type alpha: float
        :return: A mapping from tags to precision
        :rtype: Dict[str, float]
        """
        cm = self.confusion(gold)
        return {tag: cm.f_measure(tag, alpha) for tag in cm._values}

    def evaluate_per_tag(self, gold, alpha=0.5, truncate=None, sort_by_count=False):
        """Tabulate the **recall**, **precision** and **f-measure**
        for each tag from ``gold`` or from running ``tag`` on the tokenized
        sentences from ``gold``.

        >>> from nltk.tag import PerceptronTagger
        >>> from nltk.corpus import treebank
        >>> tagger = PerceptronTagger()
        >>> gold_data = treebank.tagged_sents()[:10]
        >>> print(tagger.evaluate_per_tag(gold_data))
           Tag | Prec.  | Recall | F-measure
        -------+--------+--------+-----------
            '' | 1.0000 | 1.0000 | 1.0000
             , | 1.0000 | 1.0000 | 1.0000
        -NONE- | 0.0000 | 0.0000 | 0.0000
             . | 1.0000 | 1.0000 | 1.0000
            CC | 1.0000 | 1.0000 | 1.0000
            CD | 0.7143 | 1.0000 | 0.8333
            DT | 1.0000 | 1.0000 | 1.0000
            EX | 1.0000 | 1.0000 | 1.0000
            IN | 0.9167 | 0.8800 | 0.8980
            JJ | 0.8889 | 0.8889 | 0.8889
           JJR | 0.0000 | 0.0000 | 0.0000
           JJS | 1.0000 | 1.0000 | 1.0000
            MD | 1.0000 | 1.0000 | 1.0000
            NN | 0.8000 | 0.9333 | 0.8615
           NNP | 0.8929 | 1.0000 | 0.9434
           NNS | 0.9500 | 1.0000 | 0.9744
           POS | 1.0000 | 1.0000 | 1.0000
           PRP | 1.0000 | 1.0000 | 1.0000
          PRP$ | 1.0000 | 1.0000 | 1.0000
            RB | 0.4000 | 1.0000 | 0.5714
           RBR | 1.0000 | 0.5000 | 0.6667
            RP | 1.0000 | 1.0000 | 1.0000
            TO | 1.0000 | 1.0000 | 1.0000
            VB | 1.0000 | 1.0000 | 1.0000
           VBD | 0.8571 | 0.8571 | 0.8571
           VBG | 1.0000 | 0.8000 | 0.8889
           VBN | 1.0000 | 0.8000 | 0.8889
           VBP | 1.0000 | 1.0000 | 1.0000
           VBZ | 1.0000 | 1.0000 | 1.0000
           WDT | 0.0000 | 0.0000 | 0.0000
            `` | 1.0000 | 1.0000 | 1.0000
        <BLANKLINE>

        :param gold: The list of tagged sentences to score the tagger on.
        :type gold: list(list(tuple(str, str)))
        :param alpha: Ratio of the cost of false negative compared to false
            positives, as used in the f-measure computation. Defaults to 0.5,
            where the costs are equal.
        :type alpha: float
        :param truncate: If specified, then only show the specified
            number of values.  Any sorting (e.g., sort_by_count)
            will be performed before truncation. Defaults to None
        :type truncate: int, optional
        :param sort_by_count: Whether to sort the outputs on number of
            occurrences of that tag in the ``gold`` data, defaults to False
        :type sort_by_count: bool, optional
        :return: A tabulated recall, precision and f-measure string
        :rtype: str
        """
        cm = self.confusion(gold)
        return cm.evaluate(alpha=alpha, truncate=truncate, sort_by_count=sort_by_count)

    def _check_params(self, train, model):
        if (train and model) or (not train and not model):
            raise ValueError("Must specify either training data or trained model.")


class FeaturesetTaggerI(TaggerI):
    """
    A tagger that requires tokens to be ``featuresets``.  A featureset
    is a dictionary that maps from feature names to feature
    values.  See ``nltk.classify`` for more information about features
    and featuresets.
    """

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\semcor.py ===
# Natural Language Toolkit: SemCor Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Nathan Schneider <nschneid@cs.cmu.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the SemCor Corpus.
"""

__docformat__ = "epytext en"

from nltk.corpus.reader.api import *
from nltk.corpus.reader.xmldocs import XMLCorpusReader, XMLCorpusView
from nltk.tree import Tree


class SemcorCorpusReader(XMLCorpusReader):
    """
    Corpus reader for the SemCor Corpus.
    For access to the complete XML data structure, use the ``xml()``
    method.  For access to simple word lists and tagged word lists, use
    ``words()``, ``sents()``, ``tagged_words()``, and ``tagged_sents()``.
    """

    def __init__(self, root, fileids, wordnet, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy
        self._wordnet = wordnet

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return self._items(fileids, "word", False, False, False)

    def chunks(self, fileids=None):
        """
        :return: the given file(s) as a list of chunks,
            each of which is a list of words and punctuation symbols
            that form a unit.
        :rtype: list(list(str))
        """
        return self._items(fileids, "chunk", False, False, False)

    def tagged_chunks(self, fileids=None, tag=("pos" or "sem" or "both")):
        """
        :return: the given file(s) as a list of tagged chunks, represented
            in tree form.
        :rtype: list(Tree)

        :param tag: `'pos'` (part of speech), `'sem'` (semantic), or `'both'`
            to indicate the kind of tags to include.  Semantic tags consist of
            WordNet lemma IDs, plus an `'NE'` node if the chunk is a named entity
            without a specific entry in WordNet.  (Named entities of type 'other'
            have no lemma.  Other chunks not in WordNet have no semantic tag.
            Punctuation tokens have `None` for their part of speech tag.)
        """
        return self._items(fileids, "chunk", False, tag != "sem", tag != "pos")

    def sents(self, fileids=None):
        """
        :return: the given file(s) as a list of sentences, each encoded
            as a list of word strings.
        :rtype: list(list(str))
        """
        return self._items(fileids, "word", True, False, False)

    def chunk_sents(self, fileids=None):
        """
        :return: the given file(s) as a list of sentences, each encoded
            as a list of chunks.
        :rtype: list(list(list(str)))
        """
        return self._items(fileids, "chunk", True, False, False)

    def tagged_sents(self, fileids=None, tag=("pos" or "sem" or "both")):
        """
        :return: the given file(s) as a list of sentences. Each sentence
            is represented as a list of tagged chunks (in tree form).
        :rtype: list(list(Tree))

        :param tag: `'pos'` (part of speech), `'sem'` (semantic), or `'both'`
            to indicate the kind of tags to include.  Semantic tags consist of
            WordNet lemma IDs, plus an `'NE'` node if the chunk is a named entity
            without a specific entry in WordNet.  (Named entities of type 'other'
            have no lemma.  Other chunks not in WordNet have no semantic tag.
            Punctuation tokens have `None` for their part of speech tag.)
        """
        return self._items(fileids, "chunk", True, tag != "sem", tag != "pos")

    def _items(self, fileids, unit, bracket_sent, pos_tag, sem_tag):
        if unit == "word" and not bracket_sent:
            # the result of the SemcorWordView may be a multiword unit, so the
            # LazyConcatenation will make sure the sentence is flattened
            _ = lambda *args: LazyConcatenation(
                (SemcorWordView if self._lazy else self._words)(*args)
            )
        else:
            _ = SemcorWordView if self._lazy else self._words
        return concat(
            [
                _(fileid, unit, bracket_sent, pos_tag, sem_tag, self._wordnet)
                for fileid in self.abspaths(fileids)
            ]
        )

    def _words(self, fileid, unit, bracket_sent, pos_tag, sem_tag):
        """
        Helper used to implement the view methods -- returns a list of
        tokens, (segmented) words, chunks, or sentences. The tokens
        and chunks may optionally be tagged (with POS and sense
        information).

        :param fileid: The name of the underlying file.
        :param unit: One of `'token'`, `'word'`, or `'chunk'`.
        :param bracket_sent: If true, include sentence bracketing.
        :param pos_tag: Whether to include part-of-speech tags.
        :param sem_tag: Whether to include semantic tags, namely WordNet lemma
            and OOV named entity status.
        """
        assert unit in ("token", "word", "chunk")
        result = []

        xmldoc = ElementTree.parse(fileid).getroot()
        for xmlsent in xmldoc.findall(".//s"):
            sent = []
            for xmlword in _all_xmlwords_in(xmlsent):
                itm = SemcorCorpusReader._word(
                    xmlword, unit, pos_tag, sem_tag, self._wordnet
                )
                if unit == "word":
                    sent.extend(itm)
                else:
                    sent.append(itm)

            if bracket_sent:
                result.append(SemcorSentence(xmlsent.attrib["snum"], sent))
            else:
                result.extend(sent)

        assert None not in result
        return result

    @staticmethod
    def _word(xmlword, unit, pos_tag, sem_tag, wordnet):
        tkn = xmlword.text
        if not tkn:
            tkn = ""  # fixes issue 337?

        lemma = xmlword.get("lemma", tkn)  # lemma or NE class
        lexsn = xmlword.get("lexsn")  # lex_sense (locator for the lemma's sense)
        if lexsn is not None:
            sense_key = lemma + "%" + lexsn
            wnpos = ("n", "v", "a", "r", "s")[
                int(lexsn.split(":")[0]) - 1
            ]  # see http://wordnet.princeton.edu/man/senseidx.5WN.html
        else:
            sense_key = wnpos = None
        redef = xmlword.get(
            "rdf", tkn
        )  # redefinition--this indicates the lookup string
        # does not exactly match the enclosed string, e.g. due to typographical adjustments
        # or discontinuity of a multiword expression. If a redefinition has occurred,
        # the "rdf" attribute holds its inflected form and "lemma" holds its lemma.
        # For NEs, "rdf", "lemma", and "pn" all hold the same value (the NE class).
        sensenum = xmlword.get("wnsn")  # WordNet sense number
        isOOVEntity = "pn" in xmlword.keys()  # a "personal name" (NE) not in WordNet
        pos = xmlword.get(
            "pos"
        )  # part of speech for the whole chunk (None for punctuation)

        if unit == "token":
            if not pos_tag and not sem_tag:
                itm = tkn
            else:
                itm = (
                    (tkn,)
                    + ((pos,) if pos_tag else ())
                    + ((lemma, wnpos, sensenum, isOOVEntity) if sem_tag else ())
                )
            return itm
        else:
            ww = tkn.split("_")  # TODO: case where punctuation intervenes in MWE
            if unit == "word":
                return ww
            else:
                if sensenum is not None:
                    try:
                        sense = wordnet.lemma_from_key(sense_key)  # Lemma object
                    except Exception:
                        # cannot retrieve the wordnet.Lemma object. possible reasons:
                        #  (a) the wordnet corpus is not downloaded;
                        #  (b) a nonexistent sense is annotated: e.g., such.s.00 triggers:
                        #  nltk.corpus.reader.wordnet.WordNetError: No synset found for key u'such%5:00:01:specified:00'
                        # solution: just use the lemma name as a string
                        try:
                            sense = "%s.%s.%02d" % (
                                lemma,
                                wnpos,
                                int(sensenum),
                            )  # e.g.: reach.v.02
                        except ValueError:
                            sense = (
                                lemma + "." + wnpos + "." + sensenum
                            )  # e.g. the sense number may be "2;1"

                bottom = [Tree(pos, ww)] if pos_tag else ww

                if sem_tag and isOOVEntity:
                    if sensenum is not None:
                        return Tree(sense, [Tree("NE", bottom)])
                    else:  # 'other' NE
                        return Tree("NE", bottom)
                elif sem_tag and sensenum is not None:
                    return Tree(sense, bottom)
                elif pos_tag:
                    return bottom[0]
                else:
                    return bottom  # chunk as a list


def _all_xmlwords_in(elt, result=None):
    if result is None:
        result = []
    for child in elt:
        if child.tag in ("wf", "punc"):
            result.append(child)
        else:
            _all_xmlwords_in(child, result)
    return result


class SemcorSentence(list):
    """
    A list of words, augmented by an attribute ``num`` used to record
    the sentence identifier (the ``n`` attribute from the XML).
    """

    def __init__(self, num, items):
        self.num = num
        list.__init__(self, items)


class SemcorWordView(XMLCorpusView):
    """
    A stream backed corpus view specialized for use with the BNC corpus.
    """

    def __init__(self, fileid, unit, bracket_sent, pos_tag, sem_tag, wordnet):
        """
        :param fileid: The name of the underlying file.
        :param unit: One of `'token'`, `'word'`, or `'chunk'`.
        :param bracket_sent: If true, include sentence bracketing.
        :param pos_tag: Whether to include part-of-speech tags.
        :param sem_tag: Whether to include semantic tags, namely WordNet lemma
            and OOV named entity status.
        """
        if bracket_sent:
            tagspec = ".*/s"
        else:
            tagspec = ".*/s/(punc|wf)"

        self._unit = unit
        self._sent = bracket_sent
        self._pos_tag = pos_tag
        self._sem_tag = sem_tag
        self._wordnet = wordnet

        XMLCorpusView.__init__(self, fileid, tagspec)

    def handle_elt(self, elt, context):
        if self._sent:
            return self.handle_sent(elt)
        else:
            return self.handle_word(elt)

    def handle_word(self, elt):
        return SemcorCorpusReader._word(
            elt, self._unit, self._pos_tag, self._sem_tag, self._wordnet
        )

    def handle_sent(self, elt):
        sent = []
        for child in elt:
            if child.tag in ("wf", "punc"):
                itm = self.handle_word(child)
                if self._unit == "word":
                    sent.extend(itm)
                else:
                    sent.append(itm)
            else:
                raise ValueError("Unexpected element %s" % child.tag)
        return SemcorSentence(elt.attrib["snum"], sent)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\temp_dir.py ===
import errno
import itertools
import logging
import os.path
import tempfile
import traceback
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    TypeVar,
    Union,
)

from pip._internal.utils.misc import enum, rmtree

logger = logging.getLogger(__name__)

_T = TypeVar("_T", bound="TempDirectory")


# Kinds of temporary directories. Only needed for ones that are
# globally-managed.
tempdir_kinds = enum(
    BUILD_ENV="build-env",
    EPHEM_WHEEL_CACHE="ephem-wheel-cache",
    REQ_BUILD="req-build",
)


_tempdir_manager: Optional[ExitStack] = None


@contextmanager
def global_tempdir_manager() -> Generator[None, None, None]:
    global _tempdir_manager
    with ExitStack() as stack:
        old_tempdir_manager, _tempdir_manager = _tempdir_manager, stack
        try:
            yield
        finally:
            _tempdir_manager = old_tempdir_manager


class TempDirectoryTypeRegistry:
    """Manages temp directory behavior"""

    def __init__(self) -> None:
        self._should_delete: Dict[str, bool] = {}

    def set_delete(self, kind: str, value: bool) -> None:
        """Indicate whether a TempDirectory of the given kind should be
        auto-deleted.
        """
        self._should_delete[kind] = value

    def get_delete(self, kind: str) -> bool:
        """Get configured auto-delete flag for a given TempDirectory type,
        default True.
        """
        return self._should_delete.get(kind, True)


_tempdir_registry: Optional[TempDirectoryTypeRegistry] = None


@contextmanager
def tempdir_registry() -> Generator[TempDirectoryTypeRegistry, None, None]:
    """Provides a scoped global tempdir registry that can be used to dictate
    whether directories should be deleted.
    """
    global _tempdir_registry
    old_tempdir_registry = _tempdir_registry
    _tempdir_registry = TempDirectoryTypeRegistry()
    try:
        yield _tempdir_registry
    finally:
        _tempdir_registry = old_tempdir_registry


class _Default:
    pass


_default = _Default()


class TempDirectory:
    """Helper class that owns and cleans up a temporary directory.

    This class can be used as a context manager or as an OO representation of a
    temporary directory.

    Attributes:
        path
            Location to the created temporary directory
        delete
            Whether the directory should be deleted when exiting
            (when used as a contextmanager)

    Methods:
        cleanup()
            Deletes the temporary directory

    When used as a context manager, if the delete attribute is True, on
    exiting the context the temporary directory is deleted.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        delete: Union[bool, None, _Default] = _default,
        kind: str = "temp",
        globally_managed: bool = False,
        ignore_cleanup_errors: bool = True,
    ):
        super().__init__()

        if delete is _default:
            if path is not None:
                # If we were given an explicit directory, resolve delete option
                # now.
                delete = False
            else:
                # Otherwise, we wait until cleanup and see what
                # tempdir_registry says.
                delete = None

        # The only time we specify path is in for editables where it
        # is the value of the --src option.
        if path is None:
            path = self._create(kind)

        self._path = path
        self._deleted = False
        self.delete = delete
        self.kind = kind
        self.ignore_cleanup_errors = ignore_cleanup_errors

        if globally_managed:
            assert _tempdir_manager is not None
            _tempdir_manager.enter_context(self)

    @property
    def path(self) -> str:
        assert not self._deleted, f"Attempted to access deleted path: {self._path}"
        return self._path

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.path!r}>"

    def __enter__(self: _T) -> _T:
        return self

    def __exit__(self, exc: Any, value: Any, tb: Any) -> None:
        if self.delete is not None:
            delete = self.delete
        elif _tempdir_registry:
            delete = _tempdir_registry.get_delete(self.kind)
        else:
            delete = True

        if delete:
            self.cleanup()

    def _create(self, kind: str) -> str:
        """Create a temporary directory and store its path in self.path"""
        # We realpath here because some systems have their default tmpdir
        # symlinked to another directory.  This tends to confuse build
        # scripts, so we canonicalize the path by traversing potential
        # symlinks here.
        path = os.path.realpath(tempfile.mkdtemp(prefix=f"pip-{kind}-"))
        logger.debug("Created temporary directory: %s", path)
        return path

    def cleanup(self) -> None:
        """Remove the temporary directory created and reset state"""
        self._deleted = True
        if not os.path.exists(self._path):
            return

        errors: List[BaseException] = []

        def onerror(
            func: Callable[..., Any],
            path: Path,
            exc_val: BaseException,
        ) -> None:
            """Log a warning for a `rmtree` error and continue"""
            formatted_exc = "\n".join(
                traceback.format_exception_only(type(exc_val), exc_val)
            )
            formatted_exc = formatted_exc.rstrip()  # remove trailing new line
            if func in (os.unlink, os.remove, os.rmdir):
                logger.debug(
                    "Failed to remove a temporary file '%s' due to %s.\n",
                    path,
                    formatted_exc,
                )
            else:
                logger.debug("%s failed with %s.", func.__qualname__, formatted_exc)
            errors.append(exc_val)

        if self.ignore_cleanup_errors:
            try:
                # first try with @retry; retrying to handle ephemeral errors
                rmtree(self._path, ignore_errors=False)
            except OSError:
                # last pass ignore/log all errors
                rmtree(self._path, onexc=onerror)
            if errors:
                logger.warning(
                    "Failed to remove contents in a temporary directory '%s'.\n"
                    "You can safely remove it manually.",
                    self._path,
                )
        else:
            rmtree(self._path)


class AdjacentTempDirectory(TempDirectory):
    """Helper class that creates a temporary directory adjacent to a real one.

    Attributes:
        original
            The original directory to create a temp directory for.
        path
            After calling create() or entering, contains the full
            path to the temporary directory.
        delete
            Whether the directory should be deleted when exiting
            (when used as a contextmanager)

    """

    # The characters that may be used to name the temp directory
    # We always prepend a ~ and then rotate through these until
    # a usable name is found.
    # pkg_resources raises a different error for .dist-info folder
    # with leading '-' and invalid metadata
    LEADING_CHARS = "-~.=%0123456789"

    def __init__(self, original: str, delete: Optional[bool] = None) -> None:
        self.original = original.rstrip("/\\")
        super().__init__(delete=delete)

    @classmethod
    def _generate_names(cls, name: str) -> Generator[str, None, None]:
        """Generates a series of temporary names.

        The algorithm replaces the leading characters in the name
        with ones that are valid filesystem characters, but are not
        valid package names (for both Python and pip definitions of
        package).
        """
        for i in range(1, len(name)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i - 1
            ):
                new_name = "~" + "".join(candidate) + name[i:]
                if new_name != name:
                    yield new_name

        # If we make it this far, we will have to make a longer name
        for i in range(len(cls.LEADING_CHARS)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i
            ):
                new_name = "~" + "".join(candidate) + name
                if new_name != name:
                    yield new_name

    def _create(self, kind: str) -> str:
        root, name = os.path.split(self.original)
        for candidate in self._generate_names(name):
            path = os.path.join(root, candidate)
            try:
                os.mkdir(path)
            except OSError as ex:
                # Continue if the name exists already
                if ex.errno != errno.EEXIST:
                    raise
            else:
                path = os.path.realpath(path)
                break
        else:
            # Final fallback on the default behavior.
            path = os.path.realpath(tempfile.mkdtemp(prefix=f"pip-{kind}-"))

        logger.debug("Created temporary directory: %s", path)
        return path

# === NexusCore/openenv\Lib\site-packages\runs\__init__.py ===
"""
🏃 runs: a better subprocess 🏃
---------------------------------------------------------------------

`runs` has improved versions of `call()`, `check_call()`, `check_output()`,
and `run()` from Python's `subprocess` module that handle multiple commands and
blocks of text, fix some defects, and add some features.


    import runs

    runs('''
        ls
        df -k  # or perhaps -h?
        echo 'Done and done'
    ''')

---

`subprocess` is essential but:

* You can only run one command at a time

* Commands to subprocess must be either a sequence of strings or a string,
  depending on whether `shell=True` or not

* Results are returned by default as bytes and not strings

---

The `runs` functions let you run a block of text as a sequence of subprocess
calls.

`runs` provides call-compatible replacements for the functions
`subprocess.call()`, `subprocess.check_call()`, `subprocess.check_output()`,
and `subprocess.run()`

Each replacement function takes a block of text, which is split into individual
command lines, or a list of commands, and returns a list of values, one for
each command.  A block of text can contain line continuations, and comments,
which are ignored.

The replacement functions also add optional logging, error handling,
and lazy evaluation, and use UTF-8 encoding by default.

The module `runs` is callable - `runs()` is a synonym for `runs.run()`.

EXAMPLES:


    # `runs()` or `runs.run()` writes to stdout and stderr just as if you'd run
    # the commands from the terminal

    import runs

    runs('echo "hello, world!"')  # prints hello, world!

    # runs.check_output() returns a list, one string result for each command

    results = check_output('''
        echo  line   one  # Here's line one.
        echo   'line "  two  "'  # and two!
    ''')
    assert results == ['line one', 'line "  two  "']

    # Line continuations work too, either single or double
    runs('''
        ls -cail

        # One command that takes many lines.
        g++ -DDEBUG  -O0 -g -std=c++17 -pthread -I ./include -lm -lstdc++ \\
          -Wall -Wextra -Wno-strict-aliasing -Wpedantic \\\\
          -MMD -MP -MF -c src/tests.cpp -o build/./src/tests.cpp.o

        echo DONE
     ''')

NOTES:

Exactly like `subprocess`, `runs` differs from the shell in a few ways, so
you can't just paste your shell scripts in:

* Redirection doesn't work.


    result = runs.check_output('echo foo > bar.txt')
    assert result == ['foo > bar.txt\\n']

* Pipes don't work.


    result = runs.check_output('echo foo | wc')
    assert result == ['foo | wc \\n']

*  Environment variables are not expanded in command lines


    result = runs.check_output('echo $FOO', env={'FOO': 'bah!'})
    assert result == ['$FOO\\n']

Environment variables are exported to the subprocess, absolutely,
but no environment variable expension happens on command lines.
"""

import functools
import shlex
import subprocess
import sys
import typing as t

import xmod

__all__ = 'call', 'check_call', 'check_output', 'run', 'split_commands'


def _run(
    name: str,
    commands: t.Sequence[str],
    *args: t.Any,
    on_exception: t.Any = None,
    echo: t.Union[bool, str, None, t.Callable[..., t.Any]] = False,
    **kwargs: t.Any,
) -> t.Iterator[t.Any]:
    if echo is True:
        echo = '$'

    if echo == '':
        echo = print

    if echo and not callable(echo):
        echo = functools.partial(print, echo)

    if on_exception is True:
        on_exception = lambda *x: None  # noqa: E731

    if not callable(on_exception):
        on_exception = functools.partial(print, on_exception, file=sys.stderr)

    function = getattr(subprocess, name)
    shell = kwargs.get('shell')

    for line in split_commands(commands, echo):
        cmd: t.Union[str, t.Sequence[str]] = shlex.split(line, comments=True)
        if shell:
            cmd = ' '.join(shlex.quote(c) for c in cmd)

        try:
            result = function(cmd, *args, **kwargs)

        except Exception:
            if not on_exception:
                raise
            on_exception(line)

        else:
            yield result


def split_commands(lines: t.Sequence[str], echo: t.Any = None) -> t.Iterator[str]:
    waiting: t.List[str] = []

    def emit() -> t.Iterator[str]:
        parts = ''.join(waiting).strip()
        waiting.clear()
        if parts:
            yield parts

    if isinstance(lines, str):
        lines = lines.splitlines()

    for line in lines:
        echo and echo(line)

        if line.endswith('\\'):
            no_comments = ' '.join(shlex.split(line[:-1], comments=True))
            if line.count('#') > no_comments.count('#'):
                raise ValueError('Comments cannot contain a line continuation')

            waiting.append(line[:-1])

        else:
            waiting.append(line)
            yield from emit()

    yield from emit()


def _wrap(name: str, summary: str) -> t.Callable[..., t.Any]:
    def wrapped(
        commands: t.Sequence[str],
        *args: t.Any,
        iterate: bool = False,
        encoding: str = 'utf8',
        on_exception: t.Any = None,
        echo: bool = False,
        merge: bool = False,
        always_list: bool = False,
        **kwargs: t.Any,
    ) -> t.Union[t.Iterable[str], str]:
        kwargs.update(echo=echo, encoding=encoding, on_exception=on_exception)
        if merge:
            kwargs.update(stderr=subprocess.STDOUT)
        it = _run(name, commands, *args, **kwargs)
        if iterate:
            return it
        result = list(it)
        return result if always_list or len(result) != 1 else result[0]

    wrapped.__name__ = name
    wrapped.__doc__ = _ARGS.format(function=name, summary=summary)

    return wrapped


_ARGS = """
{summary}
See the help for `subprocess.{function}()` for more information.

Arguments:
  commands:
    A string, which gets split into lines on line endings, or a list of
    strings.

  args:
    Positional arguments to `subprocess.{function}()` (but prefer keyword
    arguments!)

  on_exception:
    If `on_exception` is `False`, the default, exceptions from
    `subprocess.{function}()` are raised as usual.

    If `on_exception` is True, they are ignored.

    If `on_exception` is a callable, the line that caused the exception is
    passed to it.

    If `on_exception` is a string, the line causing the exception
    is printed, prefixed with that string.

  echo:
    If `echo` is `False`, the default, then commands are silently executed.
    If `echo` is `True`, commands are printed prefixed with `$`
    If `echo` is a string, commands are printed prefixed with that string
    If `echo` is callable, then each command is passed to it.

  merge:
    If True, stderr is set to be subprocess.STDOUT

  always_list:
    If True, the result is always a list.
    If False, the result is a list, unless the input is of length 1, when
    the first element is returned.

  iterate:
    If `iterate` is `False`, the default, then a list of results is
    returned.

    Otherwise an iterator of results which is returned, allowing for lazy
    evaluation.

  encoding:
    Like the argument to `subprocess.{function}()`, except the default  is
    `'utf8'`

  kwargs:
    Named arguments passed on to `subprocess.{function}()`
"""

call = _wrap(
    'call',
    """Call `subprocess.call()` on each command.
Return a list of integer returncodes, one for each command executed.""",
)

check_call = _wrap(
    'check_call',
    """Call `subprocess.check_call()` on each command.
If any command has a non-zero returncode, raise `subprocess.CallProcessError`.
""",
)

check_output = _wrap(
    'check_output',
    """Call `subprocess.check_output()` on each command.
If a command has a non-zero exit code, raise a `subprocess.CallProcessError`.
Otherwise, return the results as a list of strings, one for each command.""",
)

run = _wrap(
    'run',
    """Call `subprocess.run()` on each command.
Return a list of `subprocess.CompletedProcess` instances.""",
)

xmod.xmod(run, __name__, mutable=True)

# === NexusCore/openenv\Lib\site-packages\wsproto\events.py ===
"""
wsproto/events
~~~~~~~~~~~~~~

Events that result from processing data on a WebSocket connection.
"""
from abc import ABC
from dataclasses import dataclass, field
from typing import Generic, List, Optional, Sequence, TypeVar, Union

from .extensions import Extension
from .typing import Headers


class Event(ABC):
    """
    Base class for wsproto events.
    """

    pass  # noqa


@dataclass(frozen=True)
class Request(Event):
    """The beginning of a Websocket connection, the HTTP Upgrade request

    This event is fired when a SERVER connection receives a WebSocket
    handshake request (HTTP with upgrade header).

    Fields:

    .. attribute:: host

       (Required) The hostname, or host header value.

    .. attribute:: target

       (Required) The request target (path and query string)

    .. attribute:: extensions

       The proposed extensions.

    .. attribute:: extra_headers

       The additional request headers, excluding extensions, host, subprotocols,
       and version headers.

    .. attribute:: subprotocols

       A list of the subprotocols proposed in the request, as a list
       of strings.
    """

    host: str
    target: str
    extensions: Union[Sequence[Extension], Sequence[str]] = field(  # type: ignore[assignment]
        default_factory=list
    )
    extra_headers: Headers = field(default_factory=list)
    subprotocols: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptConnection(Event):
    """The acceptance of a Websocket upgrade request.

    This event is fired when a CLIENT receives an acceptance response
    from a server. It is also used to accept an upgrade request when
    acting as a SERVER.

    Fields:

    .. attribute:: extra_headers

       Any additional (non websocket related) headers present in the
       acceptance response.

    .. attribute:: subprotocol

       The accepted subprotocol to use.

    """

    subprotocol: Optional[str] = None
    extensions: List[Extension] = field(default_factory=list)
    extra_headers: Headers = field(default_factory=list)


@dataclass(frozen=True)
class RejectConnection(Event):
    """The rejection of a Websocket upgrade request, the HTTP response.

    The ``RejectConnection`` event sends the appropriate HTTP headers to
    communicate to the peer that the handshake has been rejected. You may also
    send an HTTP body by setting the ``has_body`` attribute to ``True`` and then
    sending one or more :class:`RejectData` events after this one. When sending
    a response body, the caller should set the ``Content-Length``,
    ``Content-Type``, and/or ``Transfer-Encoding`` headers as appropriate.

    When receiving a ``RejectConnection`` event, the ``has_body`` attribute will
    in almost all cases be ``True`` (even if the server set it to ``False``) and
    will be followed by at least one ``RejectData`` events, even though the data
    itself might be just ``b""``. (The only scenario in which the caller
    receives a ``RejectConnection`` with ``has_body == False`` is if the peer
    violates sends an informational status code (1xx) other than 101.)

    The ``has_body`` attribute should only be used when receiving the event. (It
    has ) is False the headers must include a
    content-length or transfer encoding.

    Fields:

    .. attribute:: headers (Headers)

       The headers to send with the response.

    .. attribute:: has_body

       This defaults to False, but set to True if there is a body. See
       also :class:`~RejectData`.

    .. attribute:: status_code

       The response status code.

    """

    status_code: int = 400
    headers: Headers = field(default_factory=list)
    has_body: bool = False


@dataclass(frozen=True)
class RejectData(Event):
    """The rejection HTTP response body.

    The caller may send multiple ``RejectData`` events. The final event should
    have the ``body_finished`` attribute set to ``True``.

    Fields:

    .. attribute:: body_finished

       True if this is the final chunk of the body data.

    .. attribute:: data (bytes)

       (Required) The raw body data.

    """

    data: bytes
    body_finished: bool = True


@dataclass(frozen=True)
class CloseConnection(Event):

    """The end of a Websocket connection, represents a closure frame.

    **wsproto does not automatically send a response to a close event.** To
    comply with the RFC you MUST send a close event back to the remote WebSocket
    if you have not already sent one. The :meth:`response` method provides a
    suitable event for this purpose, and you should check if a response needs
    to be sent by checking :func:`wsproto.WSConnection.state`.

    Fields:

    .. attribute:: code

       (Required) The integer close code to indicate why the connection
       has closed.

    .. attribute:: reason

       Additional reasoning for why the connection has closed.

    """

    code: int
    reason: Optional[str] = None

    def response(self) -> "CloseConnection":
        """Generate an RFC-compliant close frame to send back to the peer."""
        return CloseConnection(code=self.code, reason=self.reason)


T = TypeVar("T", bytes, str)


@dataclass(frozen=True)
class Message(Event, Generic[T]):
    """The websocket data message.

    Fields:

    .. attribute:: data

       (Required) The message data as byte string, can be decoded as UTF-8 for
       TEXT messages.  This only represents a single chunk of data and
       not a full WebSocket message.  You need to buffer and
       reassemble these chunks to get the full message.

    .. attribute:: frame_finished

       This has no semantic content, but is provided just in case some
       weird edge case user wants to be able to reconstruct the
       fragmentation pattern of the original stream.

    .. attribute:: message_finished

       True if this frame is the last one of this message, False if
       more frames are expected.

    """

    data: T
    frame_finished: bool = True
    message_finished: bool = True


@dataclass(frozen=True)
class TextMessage(Message[str]):  # pylint: disable=unsubscriptable-object
    """This event is fired when a data frame with TEXT payload is received.

    Fields:

    .. attribute:: data

       The message data as string, This only represents a single chunk
       of data and not a full WebSocket message.  You need to buffer
       and reassemble these chunks to get the full message.

    """

    # https://github.com/python/mypy/issues/5744
    data: str


@dataclass(frozen=True)
class BytesMessage(Message[bytes]):  # pylint: disable=unsubscriptable-object
    """This event is fired when a data frame with BINARY payload is
    received.

    Fields:

    .. attribute:: data

       The message data as byte string, can be decoded as UTF-8 for
       TEXT messages.  This only represents a single chunk of data and
       not a full WebSocket message.  You need to buffer and
       reassemble these chunks to get the full message.
    """

    # https://github.com/python/mypy/issues/5744
    data: bytes


@dataclass(frozen=True)
class Ping(Event):
    """The Ping event can be sent to trigger a ping frame and is fired
    when a Ping is received.

    **wsproto does not automatically send a pong response to a ping event.** To
    comply with the RFC you MUST send a pong even as soon as is practical. The
    :meth:`response` method provides a suitable event for this purpose.

    Fields:

    .. attribute:: payload

       An optional payload to emit with the ping frame.
    """

    payload: bytes = b""

    def response(self) -> "Pong":
        """Generate an RFC-compliant :class:`Pong` response to this ping."""
        return Pong(payload=self.payload)


@dataclass(frozen=True)
class Pong(Event):
    """The Pong event is fired when a Pong is received.

    Fields:

    .. attribute:: payload

       An optional payload to emit with the pong frame.

    """

    payload: bytes = b""

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\transports\grpc.py ===
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
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta2.types import model, model_service

from .base import DEFAULT_CLIENT_INFO, ModelServiceTransport


class ModelServiceGrpcTransport(ModelServiceTransport):
    """gRPC backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

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
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        r"""Return a callable for the get model method over gRPC.

        Gets information about a specific Model.

        Returns:
            Callable[[~.GetModelRequest],
                    ~.Model]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_model" not in self._stubs:
            self._stubs["get_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.ModelService/GetModel",
                request_serializer=model_service.GetModelRequest.serialize,
                response_deserializer=model.Model.deserialize,
            )
        return self._stubs["get_model"]

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        r"""Return a callable for the list models method over gRPC.

        Lists models available through the API.

        Returns:
            Callable[[~.ListModelsRequest],
                    ~.ListModelsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_models" not in self._stubs:
            self._stubs["list_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("ModelServiceGrpcTransport",)