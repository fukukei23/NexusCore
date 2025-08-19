
# === NexusCore/openenv\Lib\site-packages\anyio\pytest_plugin.py ===
from __future__ import annotations

import socket
import sys
from collections.abc import Callable, Generator, Iterator
from contextlib import ExitStack, contextmanager
from inspect import isasyncgenfunction, iscoroutinefunction, ismethod
from typing import Any, cast

import pytest
import sniffio
from _pytest.fixtures import SubRequest
from _pytest.outcomes import Exit

from ._core._eventloop import get_all_backends, get_async_backend
from ._core._exceptions import iterate_exceptions
from .abc import TestRunner

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

_current_runner: TestRunner | None = None
_runner_stack: ExitStack | None = None
_runner_leases = 0


def extract_backend_and_options(backend: object) -> tuple[str, dict[str, Any]]:
    if isinstance(backend, str):
        return backend, {}
    elif isinstance(backend, tuple) and len(backend) == 2:
        if isinstance(backend[0], str) and isinstance(backend[1], dict):
            return cast(tuple[str, dict[str, Any]], backend)

    raise TypeError("anyio_backend must be either a string or tuple of (string, dict)")


@contextmanager
def get_runner(
    backend_name: str, backend_options: dict[str, Any]
) -> Iterator[TestRunner]:
    global _current_runner, _runner_leases, _runner_stack
    if _current_runner is None:
        asynclib = get_async_backend(backend_name)
        _runner_stack = ExitStack()
        if sniffio.current_async_library_cvar.get(None) is None:
            # Since we're in control of the event loop, we can cache the name of the
            # async library
            token = sniffio.current_async_library_cvar.set(backend_name)
            _runner_stack.callback(sniffio.current_async_library_cvar.reset, token)

        backend_options = backend_options or {}
        _current_runner = _runner_stack.enter_context(
            asynclib.create_test_runner(backend_options)
        )

    _runner_leases += 1
    try:
        yield _current_runner
    finally:
        _runner_leases -= 1
        if not _runner_leases:
            assert _runner_stack is not None
            _runner_stack.close()
            _runner_stack = _current_runner = None


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "anyio: mark the (coroutine function) test to be run asynchronously via anyio.",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef: Any, request: Any) -> Generator[Any]:
    def wrapper(
        *args: Any, anyio_backend: Any, request: SubRequest, **kwargs: Any
    ) -> Any:
        # Rebind any fixture methods to the request instance
        if (
            request.instance
            and ismethod(func)
            and type(func.__self__) is type(request.instance)
        ):
            local_func = func.__func__.__get__(request.instance)
        else:
            local_func = func

        backend_name, backend_options = extract_backend_and_options(anyio_backend)
        if has_backend_arg:
            kwargs["anyio_backend"] = anyio_backend

        if has_request_arg:
            kwargs["request"] = request

        with get_runner(backend_name, backend_options) as runner:
            if isasyncgenfunction(local_func):
                yield from runner.run_asyncgen_fixture(local_func, kwargs)
            else:
                yield runner.run_fixture(local_func, kwargs)

    # Only apply this to coroutine functions and async generator functions in requests
    # that involve the anyio_backend fixture
    func = fixturedef.func
    if isasyncgenfunction(func) or iscoroutinefunction(func):
        if "anyio_backend" in request.fixturenames:
            fixturedef.func = wrapper
            original_argname = fixturedef.argnames

            if not (has_backend_arg := "anyio_backend" in fixturedef.argnames):
                fixturedef.argnames += ("anyio_backend",)

            if not (has_request_arg := "request" in fixturedef.argnames):
                fixturedef.argnames += ("request",)

            try:
                return (yield)
            finally:
                fixturedef.func = func
                fixturedef.argnames = original_argname

    return (yield)


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector: Any, name: Any, obj: Any) -> None:
    if collector.istestfunction(obj, name):
        inner_func = obj.hypothesis.inner_test if hasattr(obj, "hypothesis") else obj
        if iscoroutinefunction(inner_func):
            marker = collector.get_closest_marker("anyio")
            own_markers = getattr(obj, "pytestmark", ())
            if marker or any(marker.name == "anyio" for marker in own_markers):
                pytest.mark.usefixtures("anyio_backend")(obj)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: Any) -> bool | None:
    def run_with_hypothesis(**kwargs: Any) -> None:
        with get_runner(backend_name, backend_options) as runner:
            runner.run_test(original_func, kwargs)

    backend = pyfuncitem.funcargs.get("anyio_backend")
    if backend:
        backend_name, backend_options = extract_backend_and_options(backend)

        if hasattr(pyfuncitem.obj, "hypothesis"):
            # Wrap the inner test function unless it's already wrapped
            original_func = pyfuncitem.obj.hypothesis.inner_test
            if original_func.__qualname__ != run_with_hypothesis.__qualname__:
                if iscoroutinefunction(original_func):
                    pyfuncitem.obj.hypothesis.inner_test = run_with_hypothesis

            return None

        if iscoroutinefunction(pyfuncitem.obj):
            funcargs = pyfuncitem.funcargs
            testargs = {arg: funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
            with get_runner(backend_name, backend_options) as runner:
                try:
                    runner.run_test(pyfuncitem.obj, testargs)
                except ExceptionGroup as excgrp:
                    for exc in iterate_exceptions(excgrp):
                        if isinstance(exc, (Exit, KeyboardInterrupt, SystemExit)):
                            raise exc from excgrp

                    raise

            return True

    return None


@pytest.fixture(scope="module", params=get_all_backends())
def anyio_backend(request: Any) -> Any:
    return request.param


@pytest.fixture
def anyio_backend_name(anyio_backend: Any) -> str:
    if isinstance(anyio_backend, str):
        return anyio_backend
    else:
        return anyio_backend[0]


@pytest.fixture
def anyio_backend_options(anyio_backend: Any) -> dict[str, Any]:
    if isinstance(anyio_backend, str):
        return {}
    else:
        return anyio_backend[1]


class FreePortFactory:
    """
    Manages port generation based on specified socket kind, ensuring no duplicate
    ports are generated.

    This class provides functionality for generating available free ports on the
    system. It is initialized with a specific socket kind and can generate ports
    for given address families while avoiding reuse of previously generated ports.

    Users should not instantiate this class directly, but use the
    ``free_tcp_port_factory`` and ``free_udp_port_factory`` fixtures instead. For simple
    uses cases, ``free_tcp_port`` and ``free_udp_port`` can be used instead.
    """

    def __init__(self, kind: socket.SocketKind) -> None:
        self._kind = kind
        self._generated = set[int]()

    @property
    def kind(self) -> socket.SocketKind:
        """
        The type of socket connection (e.g., :data:`~socket.SOCK_STREAM` or
        :data:`~socket.SOCK_DGRAM`) used to bind for checking port availability

        """
        return self._kind

    def __call__(self, family: socket.AddressFamily | None = None) -> int:
        """
        Return an unbound port for the given address family.

        :param family: if omitted, both IPv4 and IPv6 addresses will be tried
        :return: a port number

        """
        if family is not None:
            families = [family]
        else:
            families = [socket.AF_INET]
            if socket.has_ipv6:
                families.append(socket.AF_INET6)

        while True:
            port = 0
            with ExitStack() as stack:
                for family in families:
                    sock = stack.enter_context(socket.socket(family, self._kind))
                    addr = "::1" if family == socket.AF_INET6 else "127.0.0.1"
                    try:
                        sock.bind((addr, port))
                    except OSError:
                        break

                    if not port:
                        port = sock.getsockname()[1]
                else:
                    if port not in self._generated:
                        self._generated.add(port)
                        return port


@pytest.fixture(scope="session")
def free_tcp_port_factory() -> FreePortFactory:
    return FreePortFactory(socket.SOCK_STREAM)


@pytest.fixture(scope="session")
def free_udp_port_factory() -> FreePortFactory:
    return FreePortFactory(socket.SOCK_DGRAM)


@pytest.fixture
def free_tcp_port(free_tcp_port_factory: Callable[[], int]) -> int:
    return free_tcp_port_factory()


@pytest.fixture
def free_udp_port(free_udp_port_factory: Callable[[], int]) -> int:
    return free_udp_port_factory()

# === NexusCore/openenv\Lib\site-packages\platformdirs\unix.py ===
"""Unix."""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Iterator

if sys.platform == "win32":

    def getuid() -> NoReturn:
        msg = "should only be used on Unix"
        raise RuntimeError(msg)

else:
    from os import getuid


class Unix(PlatformDirsABC):  # noqa: PLR0904
    """
    On Unix/Linux, we follow the `XDG Basedir Spec <https://specifications.freedesktop.org/basedir-spec/basedir-spec-
    latest.html>`_.

    The spec allows overriding directories with environment variables. The examples shown are the default values,
    alongside the name of the environment variable that overrides them. Makes use of the `appname
    <platformdirs.api.PlatformDirsABC.appname>`, `version <platformdirs.api.PlatformDirsABC.version>`, `multipath
    <platformdirs.api.PlatformDirsABC.multipath>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g. ``~/.local/share/$appname/$version`` or
         ``$XDG_DATA_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_DATA_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/share")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_data_dirs(self) -> list[str]:
        path = os.environ.get("XDG_DATA_DIRS", "")
        if not path.strip():
            path = f"/usr/local/share{os.pathsep}/usr/share"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>` is
         enabled and ``XDG_DATA_DIRS`` is set and a multi path the response is also a multi path separated by the
         OS path separator), e.g. ``/usr/local/share/$appname/$version`` or ``/usr/share/$appname/$version``
        """
        # XDG default for $XDG_DATA_DIRS; only first, if multipath is False
        dirs = self._site_data_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. ``~/.config/$appname/$version`` or
         ``$XDG_CONFIG_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CONFIG_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.config")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_config_dirs(self) -> list[str]:
        path = os.environ.get("XDG_CONFIG_DIRS", "")
        if not path.strip():
            path = "/etc/xdg"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_config_dir(self) -> str:
        """
        :return: config directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>`
         is enabled and ``XDG_CONFIG_DIRS`` is set and a multi path the response is also a multi path separated by
         the OS path separator), e.g. ``/etc/xdg/$appname/$version``
        """
        # XDG default for $XDG_CONFIG_DIRS only first, if multipath is False
        dirs = self._site_config_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user, e.g. ``~/.cache/$appname/$version`` or
         ``~/$XDG_CACHE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CACHE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.cache")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``/var/cache/$appname/$version``"""
        return self._append_app_name_and_version("/var/cache")

    @property
    def user_state_dir(self) -> str:
        """
        :return: state directory tied to the user, e.g. ``~/.local/state/$appname/$version`` or
         ``$XDG_STATE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_STATE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/state")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_state_dir` if not opinionated else ``log`` in it"""
        path = self.user_state_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return _get_user_media_dir("XDG_DOCUMENTS_DIR", "~/Documents")

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return _get_user_media_dir("XDG_DOWNLOAD_DIR", "~/Downloads")

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return _get_user_media_dir("XDG_PICTURES_DIR", "~/Pictures")

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Videos``"""
        return _get_user_media_dir("XDG_VIDEOS_DIR", "~/Videos")

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return _get_user_media_dir("XDG_MUSIC_DIR", "~/Music")

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return _get_user_media_dir("XDG_DESKTOP_DIR", "~/Desktop")

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g. ``/run/user/$(id -u)/$appname/$version`` or
         ``$XDG_RUNTIME_DIR/$appname/$version``.

         For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/user/$(id -u)/$appname/$version`` if
         exists, otherwise ``/tmp/runtime-$(id -u)/$appname/$version``, if``$XDG_RUNTIME_DIR``
         is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = f"/var/run/user/{getuid()}"
                if not Path(path).exists():
                    path = f"/tmp/runtime-{getuid()}"  # noqa: S108
            else:
                path = f"/run/user/{getuid()}"
        return self._append_app_name_and_version(path)

    @property
    def site_runtime_dir(self) -> str:
        """
        :return: runtime directory shared by users, e.g. ``/run/$appname/$version`` or \
        ``$XDG_RUNTIME_DIR/$appname/$version``.

        Note that this behaves almost exactly like `user_runtime_dir` if ``$XDG_RUNTIME_DIR`` is set, but will
        fall back to paths associated to the root user instead of a regular logged-in user if it's not set.

        If you wish to ensure that a logged-in root user path is returned e.g. ``/run/user/0``, use `user_runtime_dir`
        instead.

        For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/$appname/$version`` if ``$XDG_RUNTIME_DIR`` is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = "/var/run"
            else:
                path = "/run"
        return self._append_app_name_and_version(path)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users, returns the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_config_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield from self._site_config_dirs

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield from self._site_data_dirs


def _get_user_media_dir(env_var: str, fallback_tilde_path: str) -> str:
    media_dir = _get_user_dirs_folder(env_var)
    if media_dir is None:
        media_dir = os.environ.get(env_var, "").strip()
        if not media_dir:
            media_dir = os.path.expanduser(fallback_tilde_path)  # noqa: PTH111

    return media_dir


def _get_user_dirs_folder(key: str) -> str | None:
    """
    Return directory from user-dirs.dirs config file.

    See https://freedesktop.org/wiki/Software/xdg-user-dirs/.

    """
    user_dirs_config_path = Path(Unix().user_config_dir) / "user-dirs.dirs"
    if user_dirs_config_path.exists():
        parser = ConfigParser()

        with user_dirs_config_path.open() as stream:
            # Add fake section header, so ConfigParser doesn't complain
            parser.read_string(f"[top]\n{stream.read()}")

        if key not in parser["top"]:
            return None

        path = parser["top"][key].strip('"')
        # Handle relative home paths
        return path.replace("$HOME", os.path.expanduser("~"))  # noqa: PTH111

    return None


__all__ = [
    "Unix",
]

# === NexusCore/openenv\Lib\site-packages\platformdirs\windows.py ===
"""Windows."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Callable


class Windows(PlatformDirsABC):
    """
    `MSDN on where to store app data files <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `appauthor
    <platformdirs.api.PlatformDirsABC.appauthor>`, `version <platformdirs.api.PlatformDirsABC.version>`, `roaming
    <platformdirs.api.PlatformDirsABC.roaming>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname`` (not roaming) or
         ``%USERPROFILE%\\AppData\\Roaming\\$appauthor\\$appname`` (roaming)
        """
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._append_parts(path)

    def _append_parts(self, path: str, *, opinion_value: str | None = None) -> str:
        params = []
        if self.appname:
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                params.append(author)
            params.append(self.appname)
            if opinion_value is not None and self.opinion:
                params.append(opinion_value)
            if self.version:
                params.append(self.version)
        path = os.path.join(path, *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname\\Cache\\$version``
        """
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname\\Cache\\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``%USERPROFILE%\\Documents``"""
        return os.path.normpath(get_win_folder("CSIDL_PERSONAL"))

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``%USERPROFILE%\\Downloads``"""
        return os.path.normpath(get_win_folder("CSIDL_DOWNLOADS"))

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``%USERPROFILE%\\Pictures``"""
        return os.path.normpath(get_win_folder("CSIDL_MYPICTURES"))

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``%USERPROFILE%\\Videos``"""
        return os.path.normpath(get_win_folder("CSIDL_MYVIDEO"))

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``%USERPROFILE%\\Music``"""
        return os.path.normpath(get_win_folder("CSIDL_MYMUSIC"))

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``%USERPROFILE%\\Desktop``"""
        return os.path.normpath(get_win_folder("CSIDL_DESKTOPDIRECTORY"))

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\Temp\\$appauthor\\$appname``
        """
        path = os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Temp"))  # noqa: PTH118
        return self._append_parts(path)

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    if result is not None:
        return result

    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    result = os.environ.get(env_var_name)
    if result is None:
        msg = f"Unset environment variable: {env_var_name}"
        raise ValueError(msg)
    return result


def get_win_folder_if_csidl_name_not_env_var(csidl_name: str) -> str | None:
    """Get a folder for a CSIDL name that does not exist as an environment variable."""
    if csidl_name == "CSIDL_PERSONAL":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Documents")  # noqa: PTH118

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Downloads")  # noqa: PTH118

    if csidl_name == "CSIDL_MYPICTURES":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Pictures")  # noqa: PTH118

    if csidl_name == "CSIDL_MYVIDEO":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Videos")  # noqa: PTH118

    if csidl_name == "CSIDL_MYMUSIC":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Music")  # noqa: PTH118
    return None


def get_win_folder_from_registry(csidl_name: str) -> str:
    """
    Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the registry for these guarantees us the correct answer
    for all CSIDL_* names.

    """
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PERSONAL": "Personal",
        "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
        "CSIDL_MYPICTURES": "My Pictures",
        "CSIDL_MYVIDEO": "My Video",
        "CSIDL_MYMUSIC": "My Music",
    }.get(csidl_name)
    if shell_folder_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    if sys.platform != "win32":  # only needed for mypy type checker to know that this code runs only on Windows
        raise NotImplementedError
    import winreg  # noqa: PLC0415

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder with ctypes."""
    # There is no 'CSIDL_DOWNLOADS'.
    # Use 'CSIDL_PROFILE' (40) and append the default folder 'Downloads' instead.
    # https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

    import ctypes  # noqa: PLC0415

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
        "CSIDL_PERSONAL": 5,
        "CSIDL_MYPICTURES": 39,
        "CSIDL_MYVIDEO": 14,
        "CSIDL_MYMUSIC": 13,
        "CSIDL_DOWNLOADS": 40,
        "CSIDL_DESKTOPDIRECTORY": 16,
    }.get(csidl_name)
    if csidl_const is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)

    buf = ctypes.create_unicode_buffer(1024)
    windll = getattr(ctypes, "windll")  # noqa: B009 # using getattr to avoid false positive with mypy type checker
    windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if it has high-bit chars.
    if any(ord(c) > 255 for c in buf):  # noqa: PLR2004
        buf2 = ctypes.create_unicode_buffer(1024)
        if windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(buf.value, "Downloads")  # noqa: PTH118

    return buf.value


def _pick_get_win_folder() -> Callable[[str], str]:
    try:
        import ctypes  # noqa: PLC0415
    except ImportError:
        pass
    else:
        if hasattr(ctypes, "windll"):
            return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: PLC0415, F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


get_win_folder = lru_cache(maxsize=None)(_pick_get_win_folder())

__all__ = [
    "Windows",
]

# === NexusCore/openenv\Lib\site-packages\google\protobuf\service_reflection.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains metaclasses used to create protocol service and service stub
classes from ServiceDescriptor objects at runtime.

The GeneratedServiceType and GeneratedServiceStubType metaclasses are used to
inject all useful functionality into the classes output by the protocol
compiler at compile-time.
"""

__author__ = 'petar@google.com (Petar Petrov)'


class GeneratedServiceType(type):

  """Metaclass for service classes created at runtime from ServiceDescriptors.

  Implementations for all methods described in the Service class are added here
  by this class. We also create properties to allow getting/setting all fields
  in the protocol message.

  The protocol compiler currently uses this metaclass to create protocol service
  classes at runtime. Clients can also manually create their own classes at
  runtime, as in this example::

    mydescriptor = ServiceDescriptor(.....)
    class MyProtoService(service.Service):
      __metaclass__ = GeneratedServiceType
      DESCRIPTOR = mydescriptor
    myservice_instance = MyProtoService()
    # ...
  """

  _DESCRIPTOR_KEY = 'DESCRIPTOR'

  def __init__(cls, name, bases, dictionary):
    """Creates a message service class.

    Args:
      name: Name of the class (ignored, but required by the metaclass
        protocol).
      bases: Base classes of the class being constructed.
      dictionary: The class dictionary of the class being constructed.
        dictionary[_DESCRIPTOR_KEY] must contain a ServiceDescriptor object
        describing this protocol service type.
    """
    # Don't do anything if this class doesn't have a descriptor. This happens
    # when a service class is subclassed.
    if GeneratedServiceType._DESCRIPTOR_KEY not in dictionary:
      return

    descriptor = dictionary[GeneratedServiceType._DESCRIPTOR_KEY]
    service_builder = _ServiceBuilder(descriptor)
    service_builder.BuildService(cls)
    cls.DESCRIPTOR = descriptor


class GeneratedServiceStubType(GeneratedServiceType):

  """Metaclass for service stubs created at runtime from ServiceDescriptors.

  This class has similar responsibilities as GeneratedServiceType, except that
  it creates the service stub classes.
  """

  _DESCRIPTOR_KEY = 'DESCRIPTOR'

  def __init__(cls, name, bases, dictionary):
    """Creates a message service stub class.

    Args:
      name: Name of the class (ignored, here).
      bases: Base classes of the class being constructed.
      dictionary: The class dictionary of the class being constructed.
        dictionary[_DESCRIPTOR_KEY] must contain a ServiceDescriptor object
        describing this protocol service type.
    """
    super(GeneratedServiceStubType, cls).__init__(name, bases, dictionary)
    # Don't do anything if this class doesn't have a descriptor. This happens
    # when a service stub is subclassed.
    if GeneratedServiceStubType._DESCRIPTOR_KEY not in dictionary:
      return

    descriptor = dictionary[GeneratedServiceStubType._DESCRIPTOR_KEY]
    service_stub_builder = _ServiceStubBuilder(descriptor)
    service_stub_builder.BuildServiceStub(cls)


class _ServiceBuilder(object):

  """This class constructs a protocol service class using a service descriptor.

  Given a service descriptor, this class constructs a class that represents
  the specified service descriptor. One service builder instance constructs
  exactly one service class. That means all instances of that class share the
  same builder.
  """

  def __init__(self, service_descriptor):
    """Initializes an instance of the service class builder.

    Args:
      service_descriptor: ServiceDescriptor to use when constructing the
        service class.
    """
    self.descriptor = service_descriptor

  def BuildService(builder, cls):
    """Constructs the service class.

    Args:
      cls: The class that will be constructed.
    """

    # CallMethod needs to operate with an instance of the Service class. This
    # internal wrapper function exists only to be able to pass the service
    # instance to the method that does the real CallMethod work.
    # Making sure to use exact argument names from the abstract interface in
    # service.py to match the type signature
    def _WrapCallMethod(self, method_descriptor, rpc_controller, request, done):
      return builder._CallMethod(self, method_descriptor, rpc_controller,
                                 request, done)

    def _WrapGetRequestClass(self, method_descriptor):
      return builder._GetRequestClass(method_descriptor)

    def _WrapGetResponseClass(self, method_descriptor):
      return builder._GetResponseClass(method_descriptor)

    builder.cls = cls
    cls.CallMethod = _WrapCallMethod
    cls.GetDescriptor = staticmethod(lambda: builder.descriptor)
    cls.GetDescriptor.__doc__ = 'Returns the service descriptor.'
    cls.GetRequestClass = _WrapGetRequestClass
    cls.GetResponseClass = _WrapGetResponseClass
    for method in builder.descriptor.methods:
      setattr(cls, method.name, builder._GenerateNonImplementedMethod(method))

  def _CallMethod(self, srvc, method_descriptor,
                  rpc_controller, request, callback):
    """Calls the method described by a given method descriptor.

    Args:
      srvc: Instance of the service for which this method is called.
      method_descriptor: Descriptor that represent the method to call.
      rpc_controller: RPC controller to use for this method's execution.
      request: Request protocol message.
      callback: A callback to invoke after the method has completed.
    """
    if method_descriptor.containing_service != self.descriptor:
      raise RuntimeError(
          'CallMethod() given method descriptor for wrong service type.')
    method = getattr(srvc, method_descriptor.name)
    return method(rpc_controller, request, callback)

  def _GetRequestClass(self, method_descriptor):
    """Returns the class of the request protocol message.

    Args:
      method_descriptor: Descriptor of the method for which to return the
        request protocol message class.

    Returns:
      A class that represents the input protocol message of the specified
      method.
    """
    if method_descriptor.containing_service != self.descriptor:
      raise RuntimeError(
          'GetRequestClass() given method descriptor for wrong service type.')
    return method_descriptor.input_type._concrete_class

  def _GetResponseClass(self, method_descriptor):
    """Returns the class of the response protocol message.

    Args:
      method_descriptor: Descriptor of the method for which to return the
        response protocol message class.

    Returns:
      A class that represents the output protocol message of the specified
      method.
    """
    if method_descriptor.containing_service != self.descriptor:
      raise RuntimeError(
          'GetResponseClass() given method descriptor for wrong service type.')
    return method_descriptor.output_type._concrete_class

  def _GenerateNonImplementedMethod(self, method):
    """Generates and returns a method that can be set for a service methods.

    Args:
      method: Descriptor of the service method for which a method is to be
        generated.

    Returns:
      A method that can be added to the service class.
    """
    return lambda inst, rpc_controller, request, callback: (
        self._NonImplementedMethod(method.name, rpc_controller, callback))

  def _NonImplementedMethod(self, method_name, rpc_controller, callback):
    """The body of all methods in the generated service class.

    Args:
      method_name: Name of the method being executed.
      rpc_controller: RPC controller used to execute this method.
      callback: A callback which will be invoked when the method finishes.
    """
    rpc_controller.SetFailed('Method %s not implemented.' % method_name)
    callback(None)


class _ServiceStubBuilder(object):

  """Constructs a protocol service stub class using a service descriptor.

  Given a service descriptor, this class constructs a suitable stub class.
  A stub is just a type-safe wrapper around an RpcChannel which emulates a
  local implementation of the service.

  One service stub builder instance constructs exactly one class. It means all
  instances of that class share the same service stub builder.
  """

  def __init__(self, service_descriptor):
    """Initializes an instance of the service stub class builder.

    Args:
      service_descriptor: ServiceDescriptor to use when constructing the
        stub class.
    """
    self.descriptor = service_descriptor

  def BuildServiceStub(self, cls):
    """Constructs the stub class.

    Args:
      cls: The class that will be constructed.
    """

    def _ServiceStubInit(stub, rpc_channel):
      stub.rpc_channel = rpc_channel
    self.cls = cls
    cls.__init__ = _ServiceStubInit
    for method in self.descriptor.methods:
      setattr(cls, method.name, self._GenerateStubMethod(method))

  def _GenerateStubMethod(self, method):
    return (lambda inst, rpc_controller, request, callback=None:
        self._StubMethod(inst, method, rpc_controller, request, callback))

  def _StubMethod(self, stub, method_descriptor,
                  rpc_controller, request, callback):
    """The body of all service methods in the generated stub class.

    Args:
      stub: Stub instance.
      method_descriptor: Descriptor of the invoked method.
      rpc_controller: Rpc controller to execute the method.
      request: Request protocol message.
      callback: A callback to execute when the method finishes.
    Returns:
      Response message (in case of blocking call).
    """
    return stub.rpc_channel.CallMethod(
        method_descriptor, rpc_controller, request,
        method_descriptor.output_type._concrete_class, callback)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\sys_path.py ===
import os
import re
from pathlib import Path
from importlib.machinery import all_suffixes

from jedi.inference.cache import inference_state_method_cache
from jedi.inference.base_value import ContextualizedNode
from jedi.inference.helpers import is_string, get_str_or_none
from jedi.parser_utils import get_cached_code_lines
from jedi.file_io import FileIO
from jedi import settings
from jedi import debug

_BUILDOUT_PATH_INSERTION_LIMIT = 10


def _abs_path(module_context, str_path: str):
    path = Path(str_path)
    if path.is_absolute():
        return path

    module_path = module_context.py__file__()
    if module_path is None:
        # In this case we have no idea where we actually are in the file
        # system.
        return None

    base_dir = module_path.parent
    return base_dir.joinpath(path).absolute()


def _paths_from_assignment(module_context, expr_stmt):
    """
    Extracts the assigned strings from an assignment that looks as follows::

        sys.path[0:0] = ['module/path', 'another/module/path']

    This function is in general pretty tolerant (and therefore 'buggy').
    However, it's not a big issue usually to add more paths to Jedi's sys_path,
    because it will only affect Jedi in very random situations and by adding
    more paths than necessary, it usually benefits the general user.
    """
    for assignee, operator in zip(expr_stmt.children[::2], expr_stmt.children[1::2]):
        try:
            assert operator in ['=', '+=']
            assert assignee.type in ('power', 'atom_expr') and \
                len(assignee.children) > 1
            c = assignee.children
            assert c[0].type == 'name' and c[0].value == 'sys'
            trailer = c[1]
            assert trailer.children[0] == '.' and trailer.children[1].value == 'path'
            # TODO Essentially we're not checking details on sys.path
            # manipulation. Both assigment of the sys.path and changing/adding
            # parts of the sys.path are the same: They get added to the end of
            # the current sys.path.
            """
            execution = c[2]
            assert execution.children[0] == '['
            subscript = execution.children[1]
            assert subscript.type == 'subscript'
            assert ':' in subscript.children
            """
        except AssertionError:
            continue

        cn = ContextualizedNode(module_context.create_context(expr_stmt), expr_stmt)
        for lazy_value in cn.infer().iterate(cn):
            for value in lazy_value.infer():
                if is_string(value):
                    abs_path = _abs_path(module_context, value.get_safe_value())
                    if abs_path is not None:
                        yield abs_path


def _paths_from_list_modifications(module_context, trailer1, trailer2):
    """ extract the path from either "sys.path.append" or "sys.path.insert" """
    # Guarantee that both are trailers, the first one a name and the second one
    # a function execution with at least one param.
    if not (trailer1.type == 'trailer' and trailer1.children[0] == '.'
            and trailer2.type == 'trailer' and trailer2.children[0] == '('
            and len(trailer2.children) == 3):
        return

    name = trailer1.children[1].value
    if name not in ['insert', 'append']:
        return
    arg = trailer2.children[1]
    if name == 'insert' and len(arg.children) in (3, 4):  # Possible trailing comma.
        arg = arg.children[2]

    for value in module_context.create_context(arg).infer_node(arg):
        p = get_str_or_none(value)
        if p is None:
            continue
        abs_path = _abs_path(module_context, p)
        if abs_path is not None:
            yield abs_path


@inference_state_method_cache(default=[])
def check_sys_path_modifications(module_context):
    """
    Detect sys.path modifications within module.
    """
    def get_sys_path_powers(names):
        for name in names:
            power = name.parent.parent
            if power is not None and power.type in ('power', 'atom_expr'):
                c = power.children
                if c[0].type == 'name' and c[0].value == 'sys' \
                        and c[1].type == 'trailer':
                    n = c[1].children[1]
                    if n.type == 'name' and n.value == 'path':
                        yield name, power

    if module_context.tree_node is None:
        return []

    added = []
    try:
        possible_names = module_context.tree_node.get_used_names()['path']
    except KeyError:
        pass
    else:
        for name, power in get_sys_path_powers(possible_names):
            expr_stmt = power.parent
            if len(power.children) >= 4:
                added.extend(
                    _paths_from_list_modifications(
                        module_context, *power.children[2:4]
                    )
                )
            elif expr_stmt is not None and expr_stmt.type == 'expr_stmt':
                added.extend(_paths_from_assignment(module_context, expr_stmt))
    return added


def discover_buildout_paths(inference_state, script_path):
    buildout_script_paths = set()

    for buildout_script_path in _get_buildout_script_paths(script_path):
        for path in _get_paths_from_buildout_script(inference_state, buildout_script_path):
            buildout_script_paths.add(path)
            if len(buildout_script_paths) >= _BUILDOUT_PATH_INSERTION_LIMIT:
                break

    return buildout_script_paths


def _get_paths_from_buildout_script(inference_state, buildout_script_path):
    file_io = FileIO(str(buildout_script_path))
    try:
        module_node = inference_state.parse(
            file_io=file_io,
            cache=True,
            cache_path=settings.cache_directory
        )
    except IOError:
        debug.warning('Error trying to read buildout_script: %s', buildout_script_path)
        return

    from jedi.inference.value import ModuleValue
    module_context = ModuleValue(
        inference_state, module_node,
        file_io=file_io,
        string_names=None,
        code_lines=get_cached_code_lines(inference_state.grammar, buildout_script_path),
    ).as_context()
    yield from check_sys_path_modifications(module_context)


def _get_parent_dir_with_file(path: Path, filename):
    for parent in path.parents:
        try:
            if parent.joinpath(filename).is_file():
                return parent
        except OSError:
            continue
    return None


def _get_buildout_script_paths(search_path: Path):
    """
    if there is a 'buildout.cfg' file in one of the parent directories of the
    given module it will return a list of all files in the buildout bin
    directory that look like python files.

    :param search_path: absolute path to the module.
    """
    project_root = _get_parent_dir_with_file(search_path, 'buildout.cfg')
    if not project_root:
        return
    bin_path = project_root.joinpath('bin')
    if not bin_path.exists():
        return

    for filename in os.listdir(bin_path):
        try:
            filepath = bin_path.joinpath(filename)
            with open(filepath, 'r') as f:
                firstline = f.readline()
                if firstline.startswith('#!') and 'python' in firstline:
                    yield filepath
        except (UnicodeDecodeError, IOError) as e:
            # Probably a binary file; permission error or race cond. because
            # file got deleted. Ignore it.
            debug.warning(str(e))
            continue


def remove_python_path_suffix(path):
    for suffix in all_suffixes() + ['.pyi']:
        if path.suffix == suffix:
            path = path.with_name(path.stem)
            break
    return path


def transform_path_to_dotted(sys_path, module_path):
    """
    Returns the dotted path inside a sys.path as a list of names. e.g.

    >>> transform_path_to_dotted([str(Path("/foo").absolute())], Path('/foo/bar/baz.py').absolute())
    (('bar', 'baz'), False)

    Returns (None, False) if the path doesn't really resolve to anything.
    The second return part is if it is a package.
    """
    # First remove the suffix.
    module_path = remove_python_path_suffix(module_path)
    if module_path.name.startswith('.'):
        return None, False

    # Once the suffix was removed we are using the files as we know them. This
    # means that if someone uses an ending like .vim for a Python file, .vim
    # will be part of the returned dotted part.

    is_package = module_path.name == '__init__'
    if is_package:
        module_path = module_path.parent

    def iter_potential_solutions():
        for p in sys_path:
            if str(module_path).startswith(p):
                # Strip the trailing slash/backslash
                rest = str(module_path)[len(p):]
                # On Windows a path can also use a slash.
                if rest.startswith(os.path.sep) or rest.startswith('/'):
                    # Remove a slash in cases it's still there.
                    rest = rest[1:]

                if rest:
                    split = rest.split(os.path.sep)
                    if not all(split):
                        # This means that part of the file path was empty, this
                        # is very strange and is probably a file that is called
                        # `.py`.
                        return
                    # Stub folders for foo can end with foo-stubs. Just remove
                    # it.
                    yield tuple(re.sub(r'-stubs$', '', s) for s in split)

    potential_solutions = tuple(iter_potential_solutions())
    if not potential_solutions:
        return None, False
    # Try to find the shortest path, this makes more sense usually, because the
    # user usually has venvs somewhere. This means that a path like
    # .tox/py37/lib/python3.7/os.py can be normal for a file. However in that
    # case we definitely want to return ['os'] as a path and not a crazy
    # ['.tox', 'py37', 'lib', 'python3.7', 'os']. Keep in mind that this is a
    # heuristic and there's now ay to "always" do it right.
    return sorted(potential_solutions, key=lambda p: len(p))[0], is_package

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\mlflow.py ===
import json
import threading
from typing import Optional

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger


class MlflowLogger(CustomLogger):
    def __init__(self):
        from mlflow.tracking import MlflowClient

        self._client = MlflowClient()

        self._stream_id_to_span = {}
        self._lock = threading.Lock()  # lock for _stream_id_to_span

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_success(kwargs, response_obj, start_time, end_time)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_success(kwargs, response_obj, start_time, end_time)

    def _handle_success(self, kwargs, response_obj, start_time, end_time):
        """
        Log the success event as an MLflow span.
        Note that this method is called asynchronously in the background thread.
        """
        from mlflow.entities import SpanStatusCode

        try:
            verbose_logger.debug("MLflow logging start for success event")

            if kwargs.get("stream"):
                self._handle_stream_event(kwargs, response_obj, start_time, end_time)
            else:
                span = self._start_span_or_trace(kwargs, start_time)
                end_time_ns = int(end_time.timestamp() * 1e9)
                self._extract_and_set_chat_attributes(span, kwargs, response_obj)
                self._end_span_or_trace(
                    span=span,
                    outputs=response_obj,
                    status=SpanStatusCode.OK,
                    end_time_ns=end_time_ns,
                )
        except Exception:
            verbose_logger.debug("MLflow Logging Error", stack_info=True)

    def _extract_and_set_chat_attributes(self, span, kwargs, response_obj):
        try:
            from mlflow.tracing.utils import set_span_chat_messages  # type: ignore
            from mlflow.tracing.utils import set_span_chat_tools  # type: ignore
        except ImportError:
            return

        inputs = self._construct_input(kwargs)
        input_messages = inputs.get("messages", [])
        output_messages = [
            c.message.model_dump(exclude_none=True)
            for c in getattr(response_obj, "choices", [])
        ]
        if messages := [*input_messages, *output_messages]:
            set_span_chat_messages(span, messages)
        if tools := inputs.get("tools"):
            set_span_chat_tools(span, tools)

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    def _handle_failure(self, kwargs, response_obj, start_time, end_time):
        """
        Log the failure event as an MLflow span.
        Note that this method is called *synchronously* unlike the success handler.
        """
        from mlflow.entities import SpanEvent, SpanStatusCode

        try:
            span = self._start_span_or_trace(kwargs, start_time)

            end_time_ns = int(end_time.timestamp() * 1e9)

            # Record exception info as event
            if exception := kwargs.get("exception"):
                span.add_event(SpanEvent.from_exception(exception))  # type: ignore

            self._extract_and_set_chat_attributes(span, kwargs, response_obj)
            self._end_span_or_trace(
                span=span,
                outputs=response_obj,
                status=SpanStatusCode.ERROR,
                end_time_ns=end_time_ns,
            )

        except Exception as e:
            verbose_logger.debug(f"MLflow Logging Error - {e}", stack_info=True)

    def _handle_stream_event(self, kwargs, response_obj, start_time, end_time):
        """
        Handle the success event for a streaming response. For streaming calls,
        log_success_event handle is triggered for every chunk of the stream.
        We create a single span for the entire stream request as follows:

        1. For the first chunk, start a new span and store it in the map.
        2. For subsequent chunks, add the chunk as an event to the span.
        3. For the final chunk, end the span and remove the span from the map.
        """
        from mlflow.entities import SpanStatusCode

        litellm_call_id = kwargs.get("litellm_call_id")

        if litellm_call_id not in self._stream_id_to_span:
            with self._lock:
                # Check again after acquiring lock
                if litellm_call_id not in self._stream_id_to_span:
                    # Start a new span for the first chunk of the stream
                    span = self._start_span_or_trace(kwargs, start_time)
                    self._stream_id_to_span[litellm_call_id] = span

        # Add chunk as event to the span
        span = self._stream_id_to_span[litellm_call_id]
        self._add_chunk_events(span, response_obj)

        # If this is the final chunk, end the span. The final chunk
        # has complete_streaming_response that gathers the full response.
        if final_response := kwargs.get("complete_streaming_response"):
            end_time_ns = int(end_time.timestamp() * 1e9)

            self._extract_and_set_chat_attributes(span, kwargs, final_response)
            self._end_span_or_trace(
                span=span,
                outputs=final_response,
                status=SpanStatusCode.OK,
                end_time_ns=end_time_ns,
            )

            # Remove the stream_id from the map
            with self._lock:
                self._stream_id_to_span.pop(litellm_call_id)

    def _add_chunk_events(self, span, response_obj):
        from mlflow.entities import SpanEvent

        try:
            for choice in response_obj.choices:
                span.add_event(
                    SpanEvent(
                        name="streaming_chunk",
                        attributes={"delta": json.dumps(choice.delta.model_dump())},
                    )
                )
        except Exception:
            verbose_logger.debug("Error adding chunk events to span", stack_info=True)

    def _construct_input(self, kwargs):
        """Construct span inputs with optional parameters"""
        inputs = {"messages": kwargs.get("messages")}
        if tools := kwargs.get("tools"):
            inputs["tools"] = tools

        for key in ["functions", "tools", "stream", "tool_choice", "user"]:
            if value := kwargs.get("optional_params", {}).pop(key, None):
                inputs[key] = value
        return inputs

    def _extract_attributes(self, kwargs):
        """
        Extract span attributes from kwargs.

        With the latest version of litellm, the standard_logging_object contains
        canonical information for logging. If it is not present, we extract
        subset of attributes from other kwargs.
        """
        attributes = {
            "litellm_call_id": kwargs.get("litellm_call_id"),
            "call_type": kwargs.get("call_type"),
            "model": kwargs.get("model"),
        }
        standard_obj = kwargs.get("standard_logging_object")
        if standard_obj:
            attributes.update(
                {
                    "api_base": standard_obj.get("api_base"),
                    "cache_hit": standard_obj.get("cache_hit"),
                    "usage": {
                        "completion_tokens": standard_obj.get("completion_tokens"),
                        "prompt_tokens": standard_obj.get("prompt_tokens"),
                        "total_tokens": standard_obj.get("total_tokens"),
                    },
                    "raw_llm_response": standard_obj.get("response"),
                    "response_cost": standard_obj.get("response_cost"),
                    "saved_cache_cost": standard_obj.get("saved_cache_cost"),
                }
            )
        else:
            litellm_params = kwargs.get("litellm_params", {})
            attributes.update(
                {
                    "model": kwargs.get("model"),
                    "cache_hit": kwargs.get("cache_hit"),
                    "custom_llm_provider": kwargs.get("custom_llm_provider"),
                    "api_base": litellm_params.get("api_base"),
                    "response_cost": kwargs.get("response_cost"),
                }
            )
        return attributes

    def _get_span_type(self, call_type: Optional[str]) -> str:
        from mlflow.entities import SpanType

        if call_type in ["completion", "acompletion"]:
            return SpanType.LLM
        elif call_type == "embeddings":
            return SpanType.EMBEDDING
        else:
            return SpanType.LLM

    def _start_span_or_trace(self, kwargs, start_time):
        """
        Start an MLflow span or a trace.

        If there is an active span, we start a new span as a child of
        that span. Otherwise, we start a new trace.
        """
        import mlflow

        call_type = kwargs.get("call_type", "completion")
        span_name = f"litellm-{call_type}"
        span_type = self._get_span_type(call_type)
        start_time_ns = int(start_time.timestamp() * 1e9)

        inputs = self._construct_input(kwargs)
        attributes = self._extract_attributes(kwargs)

        if active_span := mlflow.get_current_active_span():  # type: ignore
            return self._client.start_span(
                name=span_name,
                request_id=active_span.request_id,
                parent_id=active_span.span_id,
                span_type=span_type,
                inputs=inputs,
                attributes=attributes,
                start_time_ns=start_time_ns,
            )
        else:
            return self._client.start_trace(
                name=span_name,
                span_type=span_type,
                inputs=inputs,
                attributes=attributes,
                start_time_ns=start_time_ns,
            )

    def _end_span_or_trace(self, span, outputs, end_time_ns, status):
        """End an MLflow span or a trace."""
        if span.parent_id is None:
            self._client.end_trace(
                request_id=span.request_id,
                outputs=outputs,
                status=status,
                end_time_ns=end_time_ns,
            )
        else:
            self._client.end_span(
                request_id=span.request_id,
                span_id=span.span_id,
                outputs=outputs,
                status=status,
                end_time_ns=end_time_ns,
            )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\success_handler.py ===
import json
from datetime import datetime
from typing import Optional, Union
from urllib.parse import urlparse

import httpx

from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.proxy._types import PassThroughEndpointLoggingResultValues
from litellm.types.passthrough_endpoints.pass_through_endpoints import (
    PassthroughStandardLoggingPayload,
)
from litellm.types.utils import StandardPassThroughResponseObject
from litellm.utils import executor as thread_pool_executor

from .llm_provider_handlers.anthropic_passthrough_logging_handler import (
    AnthropicPassthroughLoggingHandler,
)
from .llm_provider_handlers.assembly_passthrough_logging_handler import (
    AssemblyAIPassthroughLoggingHandler,
)
from .llm_provider_handlers.cohere_passthrough_logging_handler import (
    CoherePassthroughLoggingHandler,
)
from .llm_provider_handlers.vertex_passthrough_logging_handler import (
    VertexPassthroughLoggingHandler,
)

cohere_passthrough_logging_handler = CoherePassthroughLoggingHandler()


class PassThroughEndpointLogging:
    def __init__(self):
        self.TRACKED_VERTEX_ROUTES = [
            "generateContent",
            "streamGenerateContent",
            "predict",
            "rawPredict",
            "streamRawPredict",
        ]

        # Anthropic
        self.TRACKED_ANTHROPIC_ROUTES = ["/messages"]

        # Cohere
        self.TRACKED_COHERE_ROUTES = ["/v2/chat"]
        self.assemblyai_passthrough_logging_handler = (
            AssemblyAIPassthroughLoggingHandler()
        )

        # Langfuse
        self.TRACKED_LANGFUSE_ROUTES = ["/langfuse/"]

    async def _handle_logging(
        self,
        logging_obj: LiteLLMLoggingObj,
        standard_logging_response_object: Union[
            StandardPassThroughResponseObject,
            PassThroughEndpointLoggingResultValues,
            dict,
        ],
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ):
        """Helper function to handle both sync and async logging operations"""
        # Submit to thread pool for sync logging
        thread_pool_executor.submit(
            logging_obj.success_handler,
            standard_logging_response_object,
            start_time,
            end_time,
            cache_hit,
            **kwargs,
        )

        # Handle async logging
        await logging_obj.async_success_handler(
            result=(
                json.dumps(result)
                if isinstance(result, dict)
                else standard_logging_response_object
            ),
            start_time=start_time,
            end_time=end_time,
            cache_hit=False,
            **kwargs,
        )
    


    async def pass_through_async_success_handler(
        self,
        httpx_response: httpx.Response,
        response_body: Optional[dict],
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        request_body: dict,
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
        **kwargs,
    ):
        standard_logging_response_object: Optional[
            PassThroughEndpointLoggingResultValues
        ] = None
        logging_obj.model_call_details["passthrough_logging_payload"] = (
            passthrough_logging_payload
        )
        if self.is_vertex_route(url_route):
            vertex_passthrough_logging_handler_result = (
                VertexPassthroughLoggingHandler.vertex_passthrough_handler(
                    httpx_response=httpx_response,
                    logging_obj=logging_obj,
                    url_route=url_route,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    cache_hit=cache_hit,
                    **kwargs,
                )
            )
            standard_logging_response_object = (
                vertex_passthrough_logging_handler_result["result"]
            )
            kwargs = vertex_passthrough_logging_handler_result["kwargs"]
        elif self.is_anthropic_route(url_route):
            anthropic_passthrough_logging_handler_result = (
                AnthropicPassthroughLoggingHandler.anthropic_passthrough_handler(
                    httpx_response=httpx_response,
                    response_body=response_body or {},
                    logging_obj=logging_obj,
                    url_route=url_route,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    cache_hit=cache_hit,
                    **kwargs,
                )
            )

            standard_logging_response_object = (
                anthropic_passthrough_logging_handler_result["result"]
            )
            kwargs = anthropic_passthrough_logging_handler_result["kwargs"]
        elif self.is_cohere_route(url_route):
            cohere_passthrough_logging_handler_result = (
                cohere_passthrough_logging_handler.passthrough_chat_handler(
                    httpx_response=httpx_response,
                    response_body=response_body or {},
                    logging_obj=logging_obj,
                    url_route=url_route,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    cache_hit=cache_hit,
                    request_body=request_body,
                    **kwargs,
                )
            )
            standard_logging_response_object = (
                cohere_passthrough_logging_handler_result["result"]
            )
            kwargs = cohere_passthrough_logging_handler_result["kwargs"]
        elif self.is_assemblyai_route(url_route):
            if (
                AssemblyAIPassthroughLoggingHandler._should_log_request(
                    httpx_response.request.method
                )
                is not True
            ):
                return
            self.assemblyai_passthrough_logging_handler.assemblyai_passthrough_logging_handler(
                httpx_response=httpx_response,
                response_body=response_body or {},
                logging_obj=logging_obj,
                url_route=url_route,
                result=result,
                start_time=start_time,
                end_time=end_time,
                cache_hit=cache_hit,
                **kwargs,
            )
            return
        elif self.is_langfuse_route(url_route):
            # Don't log langfuse pass-through requests
            return

        if standard_logging_response_object is None:
            standard_logging_response_object = StandardPassThroughResponseObject(
                response=httpx_response.text
            )
        
        kwargs = self._set_cost_per_request(
            logging_obj=logging_obj,
            passthrough_logging_payload=passthrough_logging_payload,
            kwargs=kwargs,
        )
        

        await self._handle_logging(
            logging_obj=logging_obj,
            standard_logging_response_object=standard_logging_response_object,
            result=result,
            start_time=start_time,
            end_time=end_time,
            cache_hit=cache_hit,
            standard_pass_through_logging_payload=passthrough_logging_payload,
            **kwargs,
        )

    def is_vertex_route(self, url_route: str):
        for route in self.TRACKED_VERTEX_ROUTES:
            if route in url_route:
                return True
        return False

    def is_anthropic_route(self, url_route: str):
        for route in self.TRACKED_ANTHROPIC_ROUTES:
            if route in url_route:
                return True
        return False

    def is_cohere_route(self, url_route: str):
        for route in self.TRACKED_COHERE_ROUTES:
            if route in url_route:
                return True

    def is_assemblyai_route(self, url_route: str):
        parsed_url = urlparse(url_route)
        if parsed_url.hostname == "api.assemblyai.com":
            return True
        elif "/transcript" in parsed_url.path:
            return True
        return False

    def is_langfuse_route(self, url_route: str):
        parsed_url = urlparse(url_route)
        for route in self.TRACKED_LANGFUSE_ROUTES:
            if route in parsed_url.path:
                return True
        return False
    

    def _set_cost_per_request(
        self, 
        logging_obj: LiteLLMLoggingObj, 
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
        kwargs: dict,
    ):
        """
        Helper function to set the cost per request in the logging object

        Only set the cost per request if it's set in the passthrough logging payload.
        If it's not set, don't set it in the logging object.
        """
        #########################################################
        # Check if cost per request is set
        #########################################################
        if passthrough_logging_payload.get("cost_per_request") is not None:
            kwargs["response_cost"] = passthrough_logging_payload.get(
                "cost_per_request"
            )
            logging_obj.model_call_details["response_cost"] = passthrough_logging_payload.get(
                "cost_per_request"
            )
        
        return kwargs

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\windows.py ===
"""Windows."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Callable


class Windows(PlatformDirsABC):
    """
    `MSDN on where to store app data files <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `appauthor
    <platformdirs.api.PlatformDirsABC.appauthor>`, `version <platformdirs.api.PlatformDirsABC.version>`, `roaming
    <platformdirs.api.PlatformDirsABC.roaming>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname`` (not roaming) or
         ``%USERPROFILE%\\AppData\\Roaming\\$appauthor\\$appname`` (roaming)
        """
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._append_parts(path)

    def _append_parts(self, path: str, *, opinion_value: str | None = None) -> str:
        params = []
        if self.appname:
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                params.append(author)
            params.append(self.appname)
            if opinion_value is not None and self.opinion:
                params.append(opinion_value)
            if self.version:
                params.append(self.version)
        path = os.path.join(path, *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname\\Cache\\$version``
        """
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname\\Cache\\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``%USERPROFILE%\\Documents``"""
        return os.path.normpath(get_win_folder("CSIDL_PERSONAL"))

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``%USERPROFILE%\\Downloads``"""
        return os.path.normpath(get_win_folder("CSIDL_DOWNLOADS"))

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``%USERPROFILE%\\Pictures``"""
        return os.path.normpath(get_win_folder("CSIDL_MYPICTURES"))

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``%USERPROFILE%\\Videos``"""
        return os.path.normpath(get_win_folder("CSIDL_MYVIDEO"))

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``%USERPROFILE%\\Music``"""
        return os.path.normpath(get_win_folder("CSIDL_MYMUSIC"))

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``%USERPROFILE%\\Desktop``"""
        return os.path.normpath(get_win_folder("CSIDL_DESKTOPDIRECTORY"))

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\Temp\\$appauthor\\$appname``
        """
        path = os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Temp"))  # noqa: PTH118
        return self._append_parts(path)

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    if result is not None:
        return result

    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    result = os.environ.get(env_var_name)
    if result is None:
        msg = f"Unset environment variable: {env_var_name}"
        raise ValueError(msg)
    return result


def get_win_folder_if_csidl_name_not_env_var(csidl_name: str) -> str | None:
    """Get a folder for a CSIDL name that does not exist as an environment variable."""
    if csidl_name == "CSIDL_PERSONAL":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Documents")  # noqa: PTH118

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Downloads")  # noqa: PTH118

    if csidl_name == "CSIDL_MYPICTURES":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Pictures")  # noqa: PTH118

    if csidl_name == "CSIDL_MYVIDEO":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Videos")  # noqa: PTH118

    if csidl_name == "CSIDL_MYMUSIC":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Music")  # noqa: PTH118
    return None


def get_win_folder_from_registry(csidl_name: str) -> str:
    """
    Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the registry for these guarantees us the correct answer
    for all CSIDL_* names.

    """
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PERSONAL": "Personal",
        "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
        "CSIDL_MYPICTURES": "My Pictures",
        "CSIDL_MYVIDEO": "My Video",
        "CSIDL_MYMUSIC": "My Music",
    }.get(csidl_name)
    if shell_folder_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    if sys.platform != "win32":  # only needed for mypy type checker to know that this code runs only on Windows
        raise NotImplementedError
    import winreg  # noqa: PLC0415

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder with ctypes."""
    # There is no 'CSIDL_DOWNLOADS'.
    # Use 'CSIDL_PROFILE' (40) and append the default folder 'Downloads' instead.
    # https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

    import ctypes  # noqa: PLC0415

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
        "CSIDL_PERSONAL": 5,
        "CSIDL_MYPICTURES": 39,
        "CSIDL_MYVIDEO": 14,
        "CSIDL_MYMUSIC": 13,
        "CSIDL_DOWNLOADS": 40,
        "CSIDL_DESKTOPDIRECTORY": 16,
    }.get(csidl_name)
    if csidl_const is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)

    buf = ctypes.create_unicode_buffer(1024)
    windll = getattr(ctypes, "windll")  # noqa: B009 # using getattr to avoid false positive with mypy type checker
    windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if it has high-bit chars.
    if any(ord(c) > 255 for c in buf):  # noqa: PLR2004
        buf2 = ctypes.create_unicode_buffer(1024)
        if windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(buf.value, "Downloads")  # noqa: PTH118

    return buf.value


def _pick_get_win_folder() -> Callable[[str], str]:
    try:
        import ctypes  # noqa: PLC0415
    except ImportError:
        pass
    else:
        if hasattr(ctypes, "windll"):
            return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: PLC0415, F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


get_win_folder = lru_cache(maxsize=None)(_pick_get_win_folder())

__all__ = [
    "Windows",
]

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\platformdirs\windows.py ===
"""Windows."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Callable


class Windows(PlatformDirsABC):
    """
    `MSDN on where to store app data files <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `appauthor
    <platformdirs.api.PlatformDirsABC.appauthor>`, `version <platformdirs.api.PlatformDirsABC.version>`, `roaming
    <platformdirs.api.PlatformDirsABC.roaming>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname`` (not roaming) or
         ``%USERPROFILE%\\AppData\\Roaming\\$appauthor\\$appname`` (roaming)
        """
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._append_parts(path)

    def _append_parts(self, path: str, *, opinion_value: str | None = None) -> str:
        params = []
        if self.appname:
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                params.append(author)
            params.append(self.appname)
            if opinion_value is not None and self.opinion:
                params.append(opinion_value)
            if self.version:
                params.append(self.version)
        path = os.path.join(path, *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname\\Cache\\$version``
        """
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname\\Cache\\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``%USERPROFILE%\\Documents``"""
        return os.path.normpath(get_win_folder("CSIDL_PERSONAL"))

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``%USERPROFILE%\\Downloads``"""
        return os.path.normpath(get_win_folder("CSIDL_DOWNLOADS"))

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``%USERPROFILE%\\Pictures``"""
        return os.path.normpath(get_win_folder("CSIDL_MYPICTURES"))

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``%USERPROFILE%\\Videos``"""
        return os.path.normpath(get_win_folder("CSIDL_MYVIDEO"))

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``%USERPROFILE%\\Music``"""
        return os.path.normpath(get_win_folder("CSIDL_MYMUSIC"))

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``%USERPROFILE%\\Desktop``"""
        return os.path.normpath(get_win_folder("CSIDL_DESKTOPDIRECTORY"))

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\Temp\\$appauthor\\$appname``
        """
        path = os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Temp"))  # noqa: PTH118
        return self._append_parts(path)

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    if result is not None:
        return result

    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    result = os.environ.get(env_var_name)
    if result is None:
        msg = f"Unset environment variable: {env_var_name}"
        raise ValueError(msg)
    return result


def get_win_folder_if_csidl_name_not_env_var(csidl_name: str) -> str | None:
    """Get a folder for a CSIDL name that does not exist as an environment variable."""
    if csidl_name == "CSIDL_PERSONAL":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Documents")  # noqa: PTH118

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Downloads")  # noqa: PTH118

    if csidl_name == "CSIDL_MYPICTURES":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Pictures")  # noqa: PTH118

    if csidl_name == "CSIDL_MYVIDEO":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Videos")  # noqa: PTH118

    if csidl_name == "CSIDL_MYMUSIC":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Music")  # noqa: PTH118
    return None


def get_win_folder_from_registry(csidl_name: str) -> str:
    """
    Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the registry for these guarantees us the correct answer
    for all CSIDL_* names.

    """
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PERSONAL": "Personal",
        "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
        "CSIDL_MYPICTURES": "My Pictures",
        "CSIDL_MYVIDEO": "My Video",
        "CSIDL_MYMUSIC": "My Music",
    }.get(csidl_name)
    if shell_folder_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    if sys.platform != "win32":  # only needed for mypy type checker to know that this code runs only on Windows
        raise NotImplementedError
    import winreg  # noqa: PLC0415

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder with ctypes."""
    # There is no 'CSIDL_DOWNLOADS'.
    # Use 'CSIDL_PROFILE' (40) and append the default folder 'Downloads' instead.
    # https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

    import ctypes  # noqa: PLC0415

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
        "CSIDL_PERSONAL": 5,
        "CSIDL_MYPICTURES": 39,
        "CSIDL_MYVIDEO": 14,
        "CSIDL_MYMUSIC": 13,
        "CSIDL_DOWNLOADS": 40,
        "CSIDL_DESKTOPDIRECTORY": 16,
    }.get(csidl_name)
    if csidl_const is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)

    buf = ctypes.create_unicode_buffer(1024)
    windll = getattr(ctypes, "windll")  # noqa: B009 # using getattr to avoid false positive with mypy type checker
    windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if it has high-bit chars.
    if any(ord(c) > 255 for c in buf):  # noqa: PLR2004
        buf2 = ctypes.create_unicode_buffer(1024)
        if windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(buf.value, "Downloads")  # noqa: PTH118

    return buf.value


def _pick_get_win_folder() -> Callable[[str], str]:
    try:
        import ctypes  # noqa: PLC0415
    except ImportError:
        pass
    else:
        if hasattr(ctypes, "windll"):
            return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: PLC0415, F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


get_win_folder = lru_cache(maxsize=None)(_pick_get_win_folder())

__all__ = [
    "Windows",
]

# === NexusCore/openenv\Lib\site-packages\trio\_core\_ki.py ===
from __future__ import annotations

import signal
import sys
import types
import weakref
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

import attrs

from .._util import is_main_thread
from ._run_context import GLOBAL_RUN_CONTEXT

if TYPE_CHECKING:
    import types
    from collections.abc import Callable

    from typing_extensions import Self, TypeGuard
# In ordinary single-threaded Python code, when you hit control-C, it raises
# an exception and automatically does all the regular unwinding stuff.
#
# In Trio code, we would like hitting control-C to raise an exception and
# automatically do all the regular unwinding stuff. In particular, we would
# like to maintain our invariant that all tasks always run to completion (one
# way or another), by unwinding all of them.
#
# But it's basically impossible to write the core task running code in such a
# way that it can maintain this invariant in the face of KeyboardInterrupt
# exceptions arising at arbitrary bytecode positions. Similarly, if a
# KeyboardInterrupt happened at the wrong moment inside pretty much any of our
# inter-task synchronization or I/O primitives, then the system state could
# get corrupted and prevent our being able to clean up properly.
#
# So, we need a way to defer KeyboardInterrupt processing from these critical
# sections.
#
# Things that don't work:
#
# - Listen for SIGINT and process it in a system task: works fine for
#   well-behaved programs that regularly pass through the event loop, but if
#   user-code goes into an infinite loop then it can't be interrupted. Which
#   is unfortunate, since dealing with infinite loops is what
#   KeyboardInterrupt is for!
#
# - Use pthread_sigmask to disable signal delivery during critical section:
#   (a) windows has no pthread_sigmask, (b) python threads start with all
#   signals unblocked, so if there are any threads around they'll receive the
#   signal and then tell the main thread to run the handler, even if the main
#   thread has that signal blocked.
#
# - Install a signal handler which checks a global variable to decide whether
#   to raise the exception immediately (if we're in a non-critical section),
#   or to schedule it on the event loop (if we're in a critical section). The
#   problem here is that it's impossible to transition safely out of user code:
#
#     with keyboard_interrupt_enabled:
#         msg = coro.send(value)
#
#   If this raises a KeyboardInterrupt, it might be because the coroutine got
#   interrupted and has unwound... or it might be the KeyboardInterrupt
#   arrived just *after* 'send' returned, so the coroutine is still running,
#   but we just lost the message it sent. (And worse, in our actual task
#   runner, the send is hidden inside a utility function etc.)
#
# Solution:
#
# Mark *stack frames* as being interrupt-safe or interrupt-unsafe, and from
# the signal handler check which kind of frame we're currently in when
# deciding whether to raise or schedule the exception.
#
# There are still some cases where this can fail, like if someone hits
# control-C while the process is in the event loop, and then it immediately
# enters an infinite loop in user code. In this case the user has to hit
# control-C a second time. And of course if the user code is written so that
# it doesn't actually exit after a task crashes and everything gets cancelled,
# then there's not much to be done. (Hitting control-C repeatedly might help,
# but in general the solution is to kill the process some other way, just like
# for any Python program that's written to catch and ignore
# KeyboardInterrupt.)

_T = TypeVar("_T")


class _IdRef(weakref.ref[_T]):
    __slots__ = ("_hash",)
    _hash: int

    def __new__(
        cls,
        ob: _T,
        callback: Callable[[Self], object] | None = None,
        /,
    ) -> Self:
        self: Self = weakref.ref.__new__(cls, ob, callback)
        self._hash = object.__hash__(ob)
        return self

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if not isinstance(other, _IdRef):
            return NotImplemented

        my_obj = None
        try:
            my_obj = self()
            return my_obj is not None and my_obj is other()
        finally:
            del my_obj

    # we're overriding a builtin so we do need this
    def __ne__(self, other: object) -> bool:
        return not self == other

    def __hash__(self) -> int:
        return self._hash


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


# see also: https://github.com/python/cpython/issues/88306
class WeakKeyIdentityDictionary(Generic[_KT, _VT]):
    def __init__(self) -> None:
        self._data: dict[_IdRef[_KT], _VT] = {}

        def remove(
            k: _IdRef[_KT],
            selfref: weakref.ref[
                WeakKeyIdentityDictionary[_KT, _VT]
            ] = weakref.ref(  # noqa: B008  # function-call-in-default-argument
                self,
            ),
        ) -> None:
            self = selfref()
            if self is not None:
                try:  # noqa: SIM105  # suppressible-exception
                    del self._data[k]
                except KeyError:
                    pass

        self._remove = remove

    def __getitem__(self, k: _KT) -> _VT:
        return self._data[_IdRef(k)]

    def __setitem__(self, k: _KT, v: _VT) -> None:
        self._data[_IdRef(k, self._remove)] = v


_CODE_KI_PROTECTION_STATUS_WMAP: WeakKeyIdentityDictionary[
    types.CodeType,
    bool,
] = WeakKeyIdentityDictionary()


# This is to support the async_generator package necessary for aclosing on <3.10
# functions decorated @async_generator are given this magic property that's a
# reference to the object itself
# see python-trio/async_generator/async_generator/_impl.py
def legacy_isasyncgenfunction(
    obj: object,
) -> TypeGuard[Callable[..., types.AsyncGeneratorType[object, object]]]:
    return getattr(obj, "_async_gen_function", None) == id(obj)


# NB: according to the signal.signal docs, 'frame' can be None on entry to
# this function:
def ki_protection_enabled(frame: types.FrameType | None) -> bool:
    try:
        task = GLOBAL_RUN_CONTEXT.task
    except AttributeError:
        task_ki_protected = False
        task_frame = None
    else:
        task_ki_protected = task._ki_protected
        task_frame = task.coro.cr_frame

    while frame is not None:
        try:
            v = _CODE_KI_PROTECTION_STATUS_WMAP[frame.f_code]
        except KeyError:
            pass
        else:
            return bool(v)
        if frame.f_code.co_name == "__del__":
            return True
        if frame is task_frame:
            return task_ki_protected
        frame = frame.f_back
    return True


def currently_ki_protected() -> bool:
    r"""Check whether the calling code has :exc:`KeyboardInterrupt` protection
    enabled.

    It's surprisingly easy to think that one's :exc:`KeyboardInterrupt`
    protection is enabled when it isn't, or vice-versa. This function tells
    you what Trio thinks of the matter, which makes it useful for ``assert``\s
    and unit tests.

    Returns:
      bool: True if protection is enabled, and False otherwise.

    """
    return ki_protection_enabled(sys._getframe())


class _SupportsCode(Protocol):
    __code__: types.CodeType


_T_supports_code = TypeVar("_T_supports_code", bound=_SupportsCode)


def enable_ki_protection(f: _T_supports_code, /) -> _T_supports_code:
    """Decorator to enable KI protection."""
    orig = f

    if legacy_isasyncgenfunction(f):
        f = f.__wrapped__  # type: ignore

    _CODE_KI_PROTECTION_STATUS_WMAP[f.__code__] = True
    return orig


def disable_ki_protection(f: _T_supports_code, /) -> _T_supports_code:
    """Decorator to disable KI protection."""
    orig = f

    if legacy_isasyncgenfunction(f):
        f = f.__wrapped__  # type: ignore

    _CODE_KI_PROTECTION_STATUS_WMAP[f.__code__] = False
    return orig


@attrs.define(slots=False)
class KIManager:
    handler: Callable[[int, types.FrameType | None], None] | None = None

    def install(
        self,
        deliver_cb: Callable[[], object],
        restrict_keyboard_interrupt_to_checkpoints: bool,
    ) -> None:
        assert self.handler is None
        if (
            not is_main_thread()
            or signal.getsignal(signal.SIGINT) != signal.default_int_handler
        ):
            return

        def handler(signum: int, frame: types.FrameType | None) -> None:
            assert signum == signal.SIGINT
            protection_enabled = ki_protection_enabled(frame)
            if protection_enabled or restrict_keyboard_interrupt_to_checkpoints:
                deliver_cb()
            else:
                raise KeyboardInterrupt

        self.handler = handler
        signal.signal(signal.SIGINT, handler)

    def close(self) -> None:
        if self.handler is not None:
            if signal.getsignal(signal.SIGINT) is self.handler:
                signal.signal(signal.SIGINT, signal.default_int_handler)
            self.handler = None

# === NexusCore/openenv\Lib\site-packages\win32\Demos\win32netdemo.py ===
import getopt
import sys
import traceback
from collections.abc import Callable

import win32api
import win32net
import win32netcon
import win32security

verbose_level = 0

server = None  # Run on local machine.


def verbose(msg):
    if verbose_level:
        print(msg)


def CreateUser():
    "Creates a new test user, then deletes the user"
    testName = "PyNetTestUser"
    try:
        win32net.NetUserDel(server, testName)
        print("Warning - deleted user before creating it!")
    except win32net.error:
        pass

    d = {}
    d["name"] = testName
    d["password"] = "deleteme"
    d["priv"] = win32netcon.USER_PRIV_USER
    d["comment"] = "Delete me - created by Python test code"
    d["flags"] = win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UF_SCRIPT
    win32net.NetUserAdd(server, 1, d)
    try:
        try:
            win32net.NetUserChangePassword(server, testName, "wrong", "new")
            print("ERROR: NetUserChangePassword worked with a wrong password!")
        except win32net.error:
            pass
        win32net.NetUserChangePassword(server, testName, "deleteme", "new")
    finally:
        win32net.NetUserDel(server, testName)
    print("Created a user, changed their password, and deleted them!")


def UserEnum():
    "Enumerates all the local users"
    resume = 0
    nuser = 0
    while 1:
        data, total, resume = win32net.NetUserEnum(
            server, 3, win32netcon.FILTER_NORMAL_ACCOUNT, resume
        )
        verbose(
            "Call to NetUserEnum obtained %d entries of %d total" % (len(data), total)
        )
        for user in data:
            verbose("Found user %s" % user["name"])
            nuser += 1
        if not resume:
            break
    assert nuser, "Could not find any users!"
    print("Enumerated all the local users")


def GroupEnum():
    "Enumerates all the domain groups"
    nmembers = 0
    resume = 0
    while 1:
        data, total, resume = win32net.NetGroupEnum(server, 1, resume)
        # print(f"Call to NetGroupEnum obtained {len(data)} entries of {total} total")
        for group in data:
            verbose("Found group {name}:{comment} ".format(**group))
            memberresume = 0
            while 1:
                memberdata, total, memberresume = win32net.NetGroupGetUsers(
                    server, group["name"], 0, resume
                )
                for member in memberdata:
                    verbose(" Member {name}".format(**member))
                    nmembers += 1
                if memberresume == 0:
                    break
        if not resume:
            break
    assert nmembers, "Couldn't find a single member in a single group!"
    print("Enumerated all the groups")


def LocalGroupEnum():
    "Enumerates all the local groups"
    resume = 0
    nmembers = 0
    while 1:
        data, total, resume = win32net.NetLocalGroupEnum(server, 1, resume)
        for group in data:
            verbose("Found group {name}:{comment} ".format(**group))
            memberresume = 0
            while 1:
                memberdata, total, memberresume = win32net.NetLocalGroupGetMembers(
                    server, group["name"], 2, resume
                )
                for member in memberdata:
                    # Just for the sake of it, we convert the SID to a username
                    username, domain, type = win32security.LookupAccountSid(
                        server, member["sid"]
                    )
                    nmembers += 1
                    verbose(" Member {} ({})".format(username, member["domainandname"]))
                if memberresume == 0:
                    break
        if not resume:
            break
    assert nmembers, "Couldn't find a single member in a single group!"
    print("Enumerated all the local groups")


def ServerEnum():
    "Enumerates all servers on the network"
    resume = 0
    while 1:
        data, total, resume = win32net.NetServerEnum(
            server, 100, win32netcon.SV_TYPE_ALL, None, resume
        )
        for s in data:
            verbose("Found server %s" % s["name"])
            # Now loop over the shares.
            shareresume = 0
            while 1:
                sharedata, total, shareresume = win32net.NetShareEnum(
                    server, 2, shareresume
                )
                for share in sharedata:
                    verbose(
                        " %(netname)s (%(path)s):%(remark)s - in use by %(current_uses)d users"
                        % share
                    )
                if not shareresume:
                    break
        if not resume:
            break
    print("Enumerated all the servers on the network")


def LocalGroup(uname=None):
    "Creates a local group, adds some members, deletes them, then removes the group"
    level = 3
    if uname is None:
        uname = win32api.GetUserName()
    if uname.find("\\") < 0:
        uname = win32api.GetDomainName() + "\\" + uname
    group = "python_test_group"
    # delete the group if it already exists
    try:
        win32net.NetLocalGroupDel(server, group)
        print("WARNING: existing local group '%s' has been deleted.")
    except win32net.error:
        pass
    group_data = {"name": group}
    win32net.NetLocalGroupAdd(server, 1, group_data)
    try:
        u = {"domainandname": uname}
        win32net.NetLocalGroupAddMembers(server, group, level, [u])
        mem, tot, res = win32net.NetLocalGroupGetMembers(server, group, level)
        print("members are", mem)
        if mem[0]["domainandname"] != uname:
            print(f"ERROR: LocalGroup just added {uname}, but members are {mem!r}")
        # Convert the list of dicts to a list of strings.
        win32net.NetLocalGroupDelMembers(
            server, group, [m["domainandname"] for m in mem]
        )
    finally:
        win32net.NetLocalGroupDel(server, group)
    print("Created a local group, added and removed members, then deleted the group")


def GetInfo(userName=None):
    "Dumps level 3 information about the current user"
    if userName is None:
        userName = win32api.GetUserName()
    print("Dumping level 3 information about user")
    info = win32net.NetUserGetInfo(server, userName, 3)
    for key, val in info.items():
        verbose(f"{key}={val}")


def SetInfo(userName=None):
    "Attempts to change the current users comment, then set it back"
    if userName is None:
        userName = win32api.GetUserName()
    oldData = win32net.NetUserGetInfo(server, userName, 3)
    try:
        d = oldData.copy()
        d["usr_comment"] = "Test comment"
        win32net.NetUserSetInfo(server, userName, 3, d)
        new = win32net.NetUserGetInfo(server, userName, 3)["usr_comment"]
        if str(new) != "Test comment":
            raise RuntimeError("Could not read the same comment back - got %s" % new)
        print("Changed the data for the user")
    finally:
        win32net.NetUserSetInfo(server, userName, 3, oldData)


def SetComputerInfo():
    "Doesn't actually change anything, just make sure we could ;-)"
    info = win32net.NetWkstaGetInfo(None, 502)
    # *sob* - but we can't!  Why not!!!
    # win32net.NetWkstaSetInfo(None, 502, info)


def usage(tests):
    import os

    print("Usage: %s [-s server ] [-v] [Test ...]" % os.path.basename(sys.argv[0]))
    print("  -v : Verbose - print more information")
    print("  -s : server - execute the tests against the named server")
    print("  -c : include the CreateUser test by default")
    print("where Test is one of:")
    for t in tests:
        print(t.__name__, ":", t.__doc__)
    print()
    print("If not tests are specified, all tests are run")
    sys.exit(1)


def main():
    tests = [ob for ob in globals().values() if isinstance(ob, Callable) and ob.__doc__]
    opts, args = getopt.getopt(sys.argv[1:], "s:hvc")
    create_user = False
    for opt, val in opts:
        if opt == "-s":
            global server
            server = val
        if opt == "-h":
            usage(tests)
        if opt == "-v":
            global verbose_level
            verbose_level += 1
        if opt == "-c":
            create_user = True

    if len(args) == 0:
        print("Running all tests - use '-h' to see command-line options...")
        dotests = tests
        if not create_user:
            dotests.remove(CreateUser)
    else:
        dotests = []
        for arg in args:
            for t in tests:
                if t.__name__ == arg:
                    dotests.append(t)
                    break
            else:
                print("Test '%s' unknown - skipping" % arg)
    if not len(dotests):
        print("Nothing to do!")
        usage(tests)
    for test in dotests:
        try:
            test()
        except:
            print("Test %s failed" % test.__name__)
            traceback.print_exc()


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\win32com\test\testShell.py ===
import datetime
import os
import struct
import sys

import pythoncom
import pywintypes
import win32com.test.util
import win32con
import win32timezone
from win32com.shell import shell
from win32com.shell.shellcon import *
from win32com.storagecon import *


class ShellTester(win32com.test.util.TestCase):
    def testShellLink(self):
        desktop = str(shell.SHGetSpecialFolderPath(0, CSIDL_DESKTOP))
        num = 0
        shellLink = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        persistFile = shellLink.QueryInterface(pythoncom.IID_IPersistFile)
        names = [os.path.join(desktop, n) for n in os.listdir(desktop)]
        programs = str(shell.SHGetSpecialFolderPath(0, CSIDL_PROGRAMS))
        names.extend([os.path.join(programs, n) for n in os.listdir(programs)])
        for name in names:
            try:
                persistFile.Load(name, STGM_READ)
            except pythoncom.com_error:
                continue
            # Resolve is slow - avoid it for our tests.
            # shellLink.Resolve(0, shell.SLR_ANY_MATCH | shell.SLR_NO_UI)
            fname, findData = shellLink.GetPath(0)
            unc = shellLink.GetPath(shell.SLGP_UNCPRIORITY)[0]
            num += 1
        if num == 0:
            # This isn't a fatal error, but is unlikely.
            print(
                "Could not find any links on your desktop or programs dir, which is unusual"
            )

    def testShellFolder(self):
        sf = shell.SHGetDesktopFolder()
        names_1 = []
        for i in sf:  # Magically calls EnumObjects
            name = sf.GetDisplayNameOf(i, SHGDN_NORMAL)
            names_1.append(name)

        # And get the enumerator manually
        enum = sf.EnumObjects(
            0, SHCONTF_FOLDERS | SHCONTF_NONFOLDERS | SHCONTF_INCLUDEHIDDEN
        )
        names_2 = []
        for i in enum:
            name = sf.GetDisplayNameOf(i, SHGDN_NORMAL)
            names_2.append(name)
        names_1.sort()
        names_2.sort()
        self.assertEqual(names_1, names_2)


class PIDLTester(win32com.test.util.TestCase):
    def _rtPIDL(self, pidl):
        pidl_str = shell.PIDLAsString(pidl)
        pidl_rt = shell.StringAsPIDL(pidl_str)
        self.assertEqual(pidl_rt, pidl)
        pidl_str_rt = shell.PIDLAsString(pidl_rt)
        self.assertEqual(pidl_str_rt, pidl_str)

    def _rtCIDA(self, parent, kids):
        cida = parent, kids
        cida_str = shell.CIDAAsString(cida)
        cida_rt = shell.StringAsCIDA(cida_str)
        self.assertEqual(cida, cida_rt)
        cida_str_rt = shell.CIDAAsString(cida_rt)
        self.assertEqual(cida_str_rt, cida_str)

    def testPIDL(self):
        # A PIDL of "\1" is: cb + pidl + cb
        expect = b"\03\00" + b"\1" + b"\0\0"
        self.assertEqual(shell.PIDLAsString([b"\1"]), expect)
        self._rtPIDL([b"\0"])
        self._rtPIDL([b"\1", b"\2", b"\3"])
        self._rtPIDL([b"\0" * 2048] * 2048)
        # PIDL must be a list
        self.assertRaises(TypeError, shell.PIDLAsString, "foo")

    def testCIDA(self):
        self._rtCIDA([b"\0"], [[b"\0"]])
        self._rtCIDA([b"\1"], [[b"\2"]])
        self._rtCIDA([b"\0"], [[b"\0"], [b"\1"], [b"\2"]])

    def testBadShortPIDL(self):
        # A too-short child element: cb + pidl + cb
        pidl = b"\01\00" + b"\1"
        self.assertRaises(ValueError, shell.StringAsPIDL, pidl)

        # ack - tried to test too long PIDLs, but a len of 0xFFFF may not
        # always fail.


class FILEGROUPDESCRIPTORTester(win32com.test.util.TestCase):
    def _getTestTimes(self):
        if issubclass(pywintypes.TimeType, datetime.datetime):
            ctime = win32timezone.now()
            # FILETIME only has ms precision...
            ctime = ctime.replace(microsecond=ctime.microsecond // 1000 * 1000)
            atime = ctime + datetime.timedelta(seconds=1)
            wtime = atime + datetime.timedelta(seconds=1)
        else:
            ctime = pywintypes.Time(11)
            atime = pywintypes.Time(12)
            wtime = pywintypes.Time(13)
        return ctime, atime, wtime

    def _testRT(self, fd):
        fgd_string = shell.FILEGROUPDESCRIPTORAsString([fd])
        fd2 = shell.StringAsFILEGROUPDESCRIPTOR(fgd_string)[0]

        fd = fd.copy()
        fd2 = fd2.copy()

        # The returned objects *always* have dwFlags and cFileName.
        if "dwFlags" not in fd:
            del fd2["dwFlags"]
        if "cFileName" not in fd:
            self.assertEqual(fd2["cFileName"], "")
            del fd2["cFileName"]

        self.assertEqual(fd, fd2)

    def _testSimple(self, make_unicode):
        fgd = shell.FILEGROUPDESCRIPTORAsString([], make_unicode)
        header = struct.pack("i", 0)
        self.assertEqual(header, fgd[: len(header)])
        self._testRT({})
        d = {}
        fgd = shell.FILEGROUPDESCRIPTORAsString([d], make_unicode)
        header = struct.pack("i", 1)
        self.assertEqual(header, fgd[: len(header)])
        self._testRT(d)

    def testSimpleBytes(self):
        self._testSimple(False)

    def testSimpleUnicode(self):
        self._testSimple(True)

    def testComplex(self):
        clsid = pythoncom.MakeIID("{CD637886-DB8B-4b04-98B5-25731E1495BE}")
        ctime, atime, wtime = self._getTestTimes()
        d = {
            "cFileName": "foo.txt",
            "clsid": clsid,
            "sizel": (1, 2),
            "pointl": (3, 4),
            "dwFileAttributes": win32con.FILE_ATTRIBUTE_NORMAL,
            "ftCreationTime": ctime,
            "ftLastAccessTime": atime,
            "ftLastWriteTime": wtime,
            "nFileSize": sys.maxsize + 1,
        }
        self._testRT(d)

    def testUnicode(self):
        # exercise a bug fixed in build 210 - multiple unicode objects failed.
        ctime, atime, wtime = self._getTestTimes()
        d = [
            {
                "cFileName": "foo.txt",
                "sizel": (1, 2),
                "pointl": (3, 4),
                "dwFileAttributes": win32con.FILE_ATTRIBUTE_NORMAL,
                "ftCreationTime": ctime,
                "ftLastAccessTime": atime,
                "ftLastWriteTime": wtime,
                "nFileSize": sys.maxsize + 1,
            },
            {
                "cFileName": "foo2.txt",
                "sizel": (1, 2),
                "pointl": (3, 4),
                "dwFileAttributes": win32con.FILE_ATTRIBUTE_NORMAL,
                "ftCreationTime": ctime,
                "ftLastAccessTime": atime,
                "ftLastWriteTime": wtime,
                "nFileSize": sys.maxsize + 1,
            },
            {
                "cFileName": "foo\xa9.txt",
                "sizel": (1, 2),
                "pointl": (3, 4),
                "dwFileAttributes": win32con.FILE_ATTRIBUTE_NORMAL,
                "ftCreationTime": ctime,
                "ftLastAccessTime": atime,
                "ftLastWriteTime": wtime,
                "nFileSize": sys.maxsize + 1,
            },
        ]
        s = shell.FILEGROUPDESCRIPTORAsString(d, 1)
        d2 = shell.StringAsFILEGROUPDESCRIPTOR(s)
        # clobber 'dwFlags' - they are not expected to be identical
        for t in d2:
            del t["dwFlags"]
        self.assertEqual(d, d2)


class FileOperationTester(win32com.test.util.TestCase):
    def setUp(self):
        import tempfile

        self.src_name = os.path.join(tempfile.gettempdir(), "pywin32_testshell")
        self.dest_name = os.path.join(tempfile.gettempdir(), "pywin32_testshell_dest")
        self.test_data = b"Hello from\0Python"
        f = open(self.src_name, "wb")
        f.write(self.test_data)
        f.close()
        try:
            os.unlink(self.dest_name)
        except OSError:
            pass

    def tearDown(self):
        for fname in (self.src_name, self.dest_name):
            if os.path.isfile(fname):
                os.unlink(fname)

    def testCopy(self):
        s = (0, FO_COPY, self.src_name, self.dest_name)  # hwnd,  # operation

        rc, aborted = shell.SHFileOperation(s)
        self.assertTrue(not aborted)
        self.assertEqual(0, rc)
        self.assertTrue(os.path.isfile(self.src_name))
        self.assertTrue(os.path.isfile(self.dest_name))

    def testRename(self):
        s = (0, FO_RENAME, self.src_name, self.dest_name)  # hwnd,  # operation
        rc, aborted = shell.SHFileOperation(s)
        self.assertTrue(not aborted)
        self.assertEqual(0, rc)
        self.assertTrue(os.path.isfile(self.dest_name))
        self.assertTrue(not os.path.isfile(self.src_name))

    def testMove(self):
        s = (0, FO_MOVE, self.src_name, self.dest_name)  # hwnd,  # operation
        rc, aborted = shell.SHFileOperation(s)
        self.assertTrue(not aborted)
        self.assertEqual(0, rc)
        self.assertTrue(os.path.isfile(self.dest_name))
        self.assertTrue(not os.path.isfile(self.src_name))

    def testDelete(self):
        s = (
            0,  # hwnd,
            FO_DELETE,  # operation
            self.src_name,
            None,
            FOF_NOCONFIRMATION,
        )
        rc, aborted = shell.SHFileOperation(s)
        self.assertTrue(not aborted)
        self.assertEqual(0, rc)
        self.assertTrue(not os.path.isfile(self.src_name))


if __name__ == "__main__":
    win32com.test.util.testmain()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\timeout.py ===
from __future__ import absolute_import

import time

# The default socket timeout, used by httplib to indicate that no timeout was; specified by the user
from socket import _GLOBAL_DEFAULT_TIMEOUT, getdefaulttimeout

from ..exceptions import TimeoutStateError

# A sentinel value to indicate that no timeout was specified by the user in
# urllib3
_Default = object()


# Use time.monotonic if available.
current_time = getattr(time, "monotonic", time.time)


class Timeout(object):
    """Timeout configuration.

    Timeouts can be defined as a default for a pool:

    .. code-block:: python

       timeout = Timeout(connect=2.0, read=7.0)
       http = PoolManager(timeout=timeout)
       response = http.request('GET', 'http://example.com/')

    Or per-request (which overrides the default for the pool):

    .. code-block:: python

       response = http.request('GET', 'http://example.com/', timeout=Timeout(10))

    Timeouts can be disabled by setting all the parameters to ``None``:

    .. code-block:: python

       no_timeout = Timeout(connect=None, read=None)
       response = http.request('GET', 'http://example.com/, timeout=no_timeout)


    :param total:
        This combines the connect and read timeouts into one; the read timeout
        will be set to the time leftover from the connect attempt. In the
        event that both a connect timeout and a total are specified, or a read
        timeout and a total are specified, the shorter timeout will be applied.

        Defaults to None.

    :type total: int, float, or None

    :param connect:
        The maximum amount of time (in seconds) to wait for a connection
        attempt to a server to succeed. Omitting the parameter will default the
        connect timeout to the system default, probably `the global default
        timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout for connection attempts.

    :type connect: int, float, or None

    :param read:
        The maximum amount of time (in seconds) to wait between consecutive
        read operations for a response from the server. Omitting the parameter
        will default the read timeout to the system default, probably `the
        global default timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout.

    :type read: int, float, or None

    .. note::

        Many factors can affect the total amount of time for urllib3 to return
        an HTTP response.

        For example, Python's DNS resolver does not obey the timeout specified
        on the socket. Other factors that can affect total request time include
        high CPU load, high swap, the program running at a low priority level,
        or other behaviors.

        In addition, the read and total timeouts only measure the time between
        read operations on the socket connecting the client and the server,
        not the total amount of time for the request to return a complete
        response. For most requests, the timeout is raised because the server
        has not sent the first byte in the specified time. This is not always
        the case; if a server streams one byte every fifteen seconds, a timeout
        of 20 seconds will not trigger, even though the request will take
        several minutes to complete.

        If your goal is to cut off any request after a set amount of wall clock
        time, consider having a second "watcher" thread to cut off a slow
        request.
    """

    #: A sentinel object representing the default timeout value
    DEFAULT_TIMEOUT = _GLOBAL_DEFAULT_TIMEOUT

    def __init__(self, total=None, connect=_Default, read=_Default):
        self._connect = self._validate_timeout(connect, "connect")
        self._read = self._validate_timeout(read, "read")
        self.total = self._validate_timeout(total, "total")
        self._start_connect = None

    def __repr__(self):
        return "%s(connect=%r, read=%r, total=%r)" % (
            type(self).__name__,
            self._connect,
            self._read,
            self.total,
        )

    # __str__ provided for backwards compatibility
    __str__ = __repr__

    @classmethod
    def resolve_default_timeout(cls, timeout):
        return getdefaulttimeout() if timeout is cls.DEFAULT_TIMEOUT else timeout

    @classmethod
    def _validate_timeout(cls, value, name):
        """Check that a timeout attribute is valid.

        :param value: The timeout value to validate
        :param name: The name of the timeout attribute to validate. This is
            used to specify in error messages.
        :return: The validated and casted version of the given value.
        :raises ValueError: If it is a numeric value less than or equal to
            zero, or the type is not an integer, float, or None.
        """
        if value is _Default:
            return cls.DEFAULT_TIMEOUT

        if value is None or value is cls.DEFAULT_TIMEOUT:
            return value

        if isinstance(value, bool):
            raise ValueError(
                "Timeout cannot be a boolean value. It must "
                "be an int, float or None."
            )
        try:
            float(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            )

        try:
            if value <= 0:
                raise ValueError(
                    "Attempted to set %s timeout to %s, but the "
                    "timeout cannot be set to a value less "
                    "than or equal to 0." % (name, value)
                )
        except TypeError:
            # Python 3
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            )

        return value

    @classmethod
    def from_float(cls, timeout):
        """Create a new Timeout from a legacy timeout value.

        The timeout value used by httplib.py sets the same timeout on the
        connect(), and recv() socket requests. This creates a :class:`Timeout`
        object that sets the individual timeouts to the ``timeout`` value
        passed to this function.

        :param timeout: The legacy timeout value.
        :type timeout: integer, float, sentinel default object, or None
        :return: Timeout object
        :rtype: :class:`Timeout`
        """
        return Timeout(read=timeout, connect=timeout)

    def clone(self):
        """Create a copy of the timeout object

        Timeout properties are stored per-pool but each request needs a fresh
        Timeout object to ensure each one has its own start/stop configured.

        :return: a copy of the timeout object
        :rtype: :class:`Timeout`
        """
        # We can't use copy.deepcopy because that will also create a new object
        # for _GLOBAL_DEFAULT_TIMEOUT, which socket.py uses as a sentinel to
        # detect the user default.
        return Timeout(connect=self._connect, read=self._read, total=self.total)

    def start_connect(self):
        """Start the timeout clock, used during a connect() attempt

        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to start a timer that has been started already.
        """
        if self._start_connect is not None:
            raise TimeoutStateError("Timeout timer has already been started.")
        self._start_connect = current_time()
        return self._start_connect

    def get_connect_duration(self):
        """Gets the time elapsed since the call to :meth:`start_connect`.

        :return: Elapsed time in seconds.
        :rtype: float
        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to get duration for a timer that hasn't been started.
        """
        if self._start_connect is None:
            raise TimeoutStateError(
                "Can't get connect duration for timer that has not started."
            )
        return current_time() - self._start_connect

    @property
    def connect_timeout(self):
        """Get the value to use when setting a connection timeout.

        This will be a positive float or integer, the value None
        (never timeout), or the default system timeout.

        :return: Connect timeout.
        :rtype: int, float, :attr:`Timeout.DEFAULT_TIMEOUT` or None
        """
        if self.total is None:
            return self._connect

        if self._connect is None or self._connect is self.DEFAULT_TIMEOUT:
            return self.total

        return min(self._connect, self.total)

    @property
    def read_timeout(self):
        """Get the value for the read timeout.

        This assumes some time has elapsed in the connection timeout and
        computes the read timeout appropriately.

        If self.total is set, the read timeout is dependent on the amount of
        time taken by the connect timeout. If the connection time has not been
        established, a :exc:`~urllib3.exceptions.TimeoutStateError` will be
        raised.

        :return: Value to use for the read timeout.
        :rtype: int, float, :attr:`Timeout.DEFAULT_TIMEOUT` or None
        :raises urllib3.exceptions.TimeoutStateError: If :meth:`start_connect`
            has not yet been called on this object.
        """
        if (
            self.total is not None
            and self.total is not self.DEFAULT_TIMEOUT
            and self._read is not None
            and self._read is not self.DEFAULT_TIMEOUT
        ):
            # In case the connect timeout has not yet been established.
            if self._start_connect is None:
                return self._read
            return max(0, min(self.total - self.get_connect_duration(), self._read))
        elif self.total is not None and self.total is not self.DEFAULT_TIMEOUT:
            return max(0, self.total - self.get_connect_duration())
        else:
            return self._read

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\standardGlyphOrder.py ===
#
# 'post' table formats 1.0 and 2.0 rely on this list of "standard"
# glyphs.
#
# My list is correct according to the Apple documentation for the 'post'  table:
# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6post.html
# (However, it seems that TTFdump (from MS) and FontLab disagree, at
# least with respect to the last glyph, which they list as 'dslash'
# instead of 'dcroat'.)
#

standardGlyphOrder = [
    ".notdef",  # 0
    ".null",  # 1
    "nonmarkingreturn",  # 2
    "space",  # 3
    "exclam",  # 4
    "quotedbl",  # 5
    "numbersign",  # 6
    "dollar",  # 7
    "percent",  # 8
    "ampersand",  # 9
    "quotesingle",  # 10
    "parenleft",  # 11
    "parenright",  # 12
    "asterisk",  # 13
    "plus",  # 14
    "comma",  # 15
    "hyphen",  # 16
    "period",  # 17
    "slash",  # 18
    "zero",  # 19
    "one",  # 20
    "two",  # 21
    "three",  # 22
    "four",  # 23
    "five",  # 24
    "six",  # 25
    "seven",  # 26
    "eight",  # 27
    "nine",  # 28
    "colon",  # 29
    "semicolon",  # 30
    "less",  # 31
    "equal",  # 32
    "greater",  # 33
    "question",  # 34
    "at",  # 35
    "A",  # 36
    "B",  # 37
    "C",  # 38
    "D",  # 39
    "E",  # 40
    "F",  # 41
    "G",  # 42
    "H",  # 43
    "I",  # 44
    "J",  # 45
    "K",  # 46
    "L",  # 47
    "M",  # 48
    "N",  # 49
    "O",  # 50
    "P",  # 51
    "Q",  # 52
    "R",  # 53
    "S",  # 54
    "T",  # 55
    "U",  # 56
    "V",  # 57
    "W",  # 58
    "X",  # 59
    "Y",  # 60
    "Z",  # 61
    "bracketleft",  # 62
    "backslash",  # 63
    "bracketright",  # 64
    "asciicircum",  # 65
    "underscore",  # 66
    "grave",  # 67
    "a",  # 68
    "b",  # 69
    "c",  # 70
    "d",  # 71
    "e",  # 72
    "f",  # 73
    "g",  # 74
    "h",  # 75
    "i",  # 76
    "j",  # 77
    "k",  # 78
    "l",  # 79
    "m",  # 80
    "n",  # 81
    "o",  # 82
    "p",  # 83
    "q",  # 84
    "r",  # 85
    "s",  # 86
    "t",  # 87
    "u",  # 88
    "v",  # 89
    "w",  # 90
    "x",  # 91
    "y",  # 92
    "z",  # 93
    "braceleft",  # 94
    "bar",  # 95
    "braceright",  # 96
    "asciitilde",  # 97
    "Adieresis",  # 98
    "Aring",  # 99
    "Ccedilla",  # 100
    "Eacute",  # 101
    "Ntilde",  # 102
    "Odieresis",  # 103
    "Udieresis",  # 104
    "aacute",  # 105
    "agrave",  # 106
    "acircumflex",  # 107
    "adieresis",  # 108
    "atilde",  # 109
    "aring",  # 110
    "ccedilla",  # 111
    "eacute",  # 112
    "egrave",  # 113
    "ecircumflex",  # 114
    "edieresis",  # 115
    "iacute",  # 116
    "igrave",  # 117
    "icircumflex",  # 118
    "idieresis",  # 119
    "ntilde",  # 120
    "oacute",  # 121
    "ograve",  # 122
    "ocircumflex",  # 123
    "odieresis",  # 124
    "otilde",  # 125
    "uacute",  # 126
    "ugrave",  # 127
    "ucircumflex",  # 128
    "udieresis",  # 129
    "dagger",  # 130
    "degree",  # 131
    "cent",  # 132
    "sterling",  # 133
    "section",  # 134
    "bullet",  # 135
    "paragraph",  # 136
    "germandbls",  # 137
    "registered",  # 138
    "copyright",  # 139
    "trademark",  # 140
    "acute",  # 141
    "dieresis",  # 142
    "notequal",  # 143
    "AE",  # 144
    "Oslash",  # 145
    "infinity",  # 146
    "plusminus",  # 147
    "lessequal",  # 148
    "greaterequal",  # 149
    "yen",  # 150
    "mu",  # 151
    "partialdiff",  # 152
    "summation",  # 153
    "product",  # 154
    "pi",  # 155
    "integral",  # 156
    "ordfeminine",  # 157
    "ordmasculine",  # 158
    "Omega",  # 159
    "ae",  # 160
    "oslash",  # 161
    "questiondown",  # 162
    "exclamdown",  # 163
    "logicalnot",  # 164
    "radical",  # 165
    "florin",  # 166
    "approxequal",  # 167
    "Delta",  # 168
    "guillemotleft",  # 169
    "guillemotright",  # 170
    "ellipsis",  # 171
    "nonbreakingspace",  # 172
    "Agrave",  # 173
    "Atilde",  # 174
    "Otilde",  # 175
    "OE",  # 176
    "oe",  # 177
    "endash",  # 178
    "emdash",  # 179
    "quotedblleft",  # 180
    "quotedblright",  # 181
    "quoteleft",  # 182
    "quoteright",  # 183
    "divide",  # 184
    "lozenge",  # 185
    "ydieresis",  # 186
    "Ydieresis",  # 187
    "fraction",  # 188
    "currency",  # 189
    "guilsinglleft",  # 190
    "guilsinglright",  # 191
    "fi",  # 192
    "fl",  # 193
    "daggerdbl",  # 194
    "periodcentered",  # 195
    "quotesinglbase",  # 196
    "quotedblbase",  # 197
    "perthousand",  # 198
    "Acircumflex",  # 199
    "Ecircumflex",  # 200
    "Aacute",  # 201
    "Edieresis",  # 202
    "Egrave",  # 203
    "Iacute",  # 204
    "Icircumflex",  # 205
    "Idieresis",  # 206
    "Igrave",  # 207
    "Oacute",  # 208
    "Ocircumflex",  # 209
    "apple",  # 210
    "Ograve",  # 211
    "Uacute",  # 212
    "Ucircumflex",  # 213
    "Ugrave",  # 214
    "dotlessi",  # 215
    "circumflex",  # 216
    "tilde",  # 217
    "macron",  # 218
    "breve",  # 219
    "dotaccent",  # 220
    "ring",  # 221
    "cedilla",  # 222
    "hungarumlaut",  # 223
    "ogonek",  # 224
    "caron",  # 225
    "Lslash",  # 226
    "lslash",  # 227
    "Scaron",  # 228
    "scaron",  # 229
    "Zcaron",  # 230
    "zcaron",  # 231
    "brokenbar",  # 232
    "Eth",  # 233
    "eth",  # 234
    "Yacute",  # 235
    "yacute",  # 236
    "Thorn",  # 237
    "thorn",  # 238
    "minus",  # 239
    "multiply",  # 240
    "onesuperior",  # 241
    "twosuperior",  # 242
    "threesuperior",  # 243
    "onehalf",  # 244
    "onequarter",  # 245
    "threequarters",  # 246
    "franc",  # 247
    "Gbreve",  # 248
    "gbreve",  # 249
    "Idotaccent",  # 250
    "Scedilla",  # 251
    "scedilla",  # 252
    "Cacute",  # 253
    "cacute",  # 254
    "Ccaron",  # 255
    "ccaron",  # 256
    "dcroat",  # 257
]

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\safety.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "HarmCategory",
        "ContentFilter",
        "SafetyFeedback",
        "SafetyRating",
        "SafetySetting",
    },
)


class HarmCategory(proto.Enum):
    r"""The category of a rating.

    These categories cover various kinds of harms that developers
    may wish to adjust.

    Values:
        HARM_CATEGORY_UNSPECIFIED (0):
            Category is unspecified.
        HARM_CATEGORY_DEROGATORY (1):
            Negative or harmful comments targeting
            identity and/or protected attribute.
        HARM_CATEGORY_TOXICITY (2):
            Content that is rude, disrespectful, or
            profane.
        HARM_CATEGORY_VIOLENCE (3):
            Describes scenarios depicting violence
            against an individual or group, or general
            descriptions of gore.
        HARM_CATEGORY_SEXUAL (4):
            Contains references to sexual acts or other
            lewd content.
        HARM_CATEGORY_MEDICAL (5):
            Promotes unchecked medical advice.
        HARM_CATEGORY_DANGEROUS (6):
            Dangerous content that promotes, facilitates,
            or encourages harmful acts.
        HARM_CATEGORY_HARASSMENT (7):
            Harasment content.
        HARM_CATEGORY_HATE_SPEECH (8):
            Hate speech and content.
        HARM_CATEGORY_SEXUALLY_EXPLICIT (9):
            Sexually explicit content.
        HARM_CATEGORY_DANGEROUS_CONTENT (10):
            Dangerous content.
    """
    HARM_CATEGORY_UNSPECIFIED = 0
    HARM_CATEGORY_DEROGATORY = 1
    HARM_CATEGORY_TOXICITY = 2
    HARM_CATEGORY_VIOLENCE = 3
    HARM_CATEGORY_SEXUAL = 4
    HARM_CATEGORY_MEDICAL = 5
    HARM_CATEGORY_DANGEROUS = 6
    HARM_CATEGORY_HARASSMENT = 7
    HARM_CATEGORY_HATE_SPEECH = 8
    HARM_CATEGORY_SEXUALLY_EXPLICIT = 9
    HARM_CATEGORY_DANGEROUS_CONTENT = 10


class ContentFilter(proto.Message):
    r"""Content filtering metadata associated with processing a
    single request.
    ContentFilter contains a reason and an optional supporting
    string. The reason may be unspecified.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        reason (google.ai.generativelanguage_v1beta.types.ContentFilter.BlockedReason):
            The reason content was blocked during request
            processing.
        message (str):
            A string that describes the filtering
            behavior in more detail.

            This field is a member of `oneof`_ ``_message``.
    """

    class BlockedReason(proto.Enum):
        r"""A list of reasons why content may have been blocked.

        Values:
            BLOCKED_REASON_UNSPECIFIED (0):
                A blocked reason was not specified.
            SAFETY (1):
                Content was blocked by safety settings.
            OTHER (2):
                Content was blocked, but the reason is
                uncategorized.
        """
        BLOCKED_REASON_UNSPECIFIED = 0
        SAFETY = 1
        OTHER = 2

    reason: BlockedReason = proto.Field(
        proto.ENUM,
        number=1,
        enum=BlockedReason,
    )
    message: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )


class SafetyFeedback(proto.Message):
    r"""Safety feedback for an entire request.

    This field is populated if content in the input and/or response
    is blocked due to safety settings. SafetyFeedback may not exist
    for every HarmCategory. Each SafetyFeedback will return the
    safety settings used by the request as well as the lowest
    HarmProbability that should be allowed in order to return a
    result.

    Attributes:
        rating (google.ai.generativelanguage_v1beta.types.SafetyRating):
            Safety rating evaluated from content.
        setting (google.ai.generativelanguage_v1beta.types.SafetySetting):
            Safety settings applied to the request.
    """

    rating: "SafetyRating" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="SafetyRating",
    )
    setting: "SafetySetting" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="SafetySetting",
    )


class SafetyRating(proto.Message):
    r"""Safety rating for a piece of content.

    The safety rating contains the category of harm and the harm
    probability level in that category for a piece of content.
    Content is classified for safety across a number of harm
    categories and the probability of the harm classification is
    included here.

    Attributes:
        category (google.ai.generativelanguage_v1beta.types.HarmCategory):
            Required. The category for this rating.
        probability (google.ai.generativelanguage_v1beta.types.SafetyRating.HarmProbability):
            Required. The probability of harm for this
            content.
        blocked (bool):
            Was this content blocked because of this
            rating?
    """

    class HarmProbability(proto.Enum):
        r"""The probability that a piece of content is harmful.

        The classification system gives the probability of the content
        being unsafe. This does not indicate the severity of harm for a
        piece of content.

        Values:
            HARM_PROBABILITY_UNSPECIFIED (0):
                Probability is unspecified.
            NEGLIGIBLE (1):
                Content has a negligible chance of being
                unsafe.
            LOW (2):
                Content has a low chance of being unsafe.
            MEDIUM (3):
                Content has a medium chance of being unsafe.
            HIGH (4):
                Content has a high chance of being unsafe.
        """
        HARM_PROBABILITY_UNSPECIFIED = 0
        NEGLIGIBLE = 1
        LOW = 2
        MEDIUM = 3
        HIGH = 4

    category: "HarmCategory" = proto.Field(
        proto.ENUM,
        number=3,
        enum="HarmCategory",
    )
    probability: HarmProbability = proto.Field(
        proto.ENUM,
        number=4,
        enum=HarmProbability,
    )
    blocked: bool = proto.Field(
        proto.BOOL,
        number=5,
    )


class SafetySetting(proto.Message):
    r"""Safety setting, affecting the safety-blocking behavior.

    Passing a safety setting for a category changes the allowed
    probability that content is blocked.

    Attributes:
        category (google.ai.generativelanguage_v1beta.types.HarmCategory):
            Required. The category for this setting.
        threshold (google.ai.generativelanguage_v1beta.types.SafetySetting.HarmBlockThreshold):
            Required. Controls the probability threshold
            at which harm is blocked.
    """

    class HarmBlockThreshold(proto.Enum):
        r"""Block at and beyond a specified harm probability.

        Values:
            HARM_BLOCK_THRESHOLD_UNSPECIFIED (0):
                Threshold is unspecified.
            BLOCK_LOW_AND_ABOVE (1):
                Content with NEGLIGIBLE will be allowed.
            BLOCK_MEDIUM_AND_ABOVE (2):
                Content with NEGLIGIBLE and LOW will be
                allowed.
            BLOCK_ONLY_HIGH (3):
                Content with NEGLIGIBLE, LOW, and MEDIUM will
                be allowed.
            BLOCK_NONE (4):
                All content will be allowed.
        """
        HARM_BLOCK_THRESHOLD_UNSPECIFIED = 0
        BLOCK_LOW_AND_ABOVE = 1
        BLOCK_MEDIUM_AND_ABOVE = 2
        BLOCK_ONLY_HIGH = 3
        BLOCK_NONE = 4

    category: "HarmCategory" = proto.Field(
        proto.ENUM,
        number=3,
        enum="HarmCategory",
    )
    threshold: HarmBlockThreshold = proto.Field(
        proto.ENUM,
        number=4,
        enum=HarmBlockThreshold,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\qt_editor\figureoptions.py ===
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# see the Matplotlib licenses directory for a copy of the license


"""Module that provides a GUI-based editor for Matplotlib's figure options."""

from itertools import chain
from matplotlib import cbook, cm, colors as mcolors, markers, image as mimage
from matplotlib.backends.qt_compat import QtGui
from matplotlib.backends.qt_editor import _formlayout
from matplotlib.dates import DateConverter, num2date

LINESTYLES = {'-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'None': 'None',
              }

DRAWSTYLES = {
    'default': 'Default',
    'steps-pre': 'Steps (Pre)', 'steps': 'Steps (Pre)',
    'steps-mid': 'Steps (Mid)',
    'steps-post': 'Steps (Post)'}

MARKERS = markers.MarkerStyle.markers


def figure_edit(axes, parent=None):
    """Edit matplotlib figure options"""
    sep = (None, None)  # separator

    # Get / General
    def convert_limits(lim, converter):
        """Convert axis limits for correct input editors."""
        if isinstance(converter, DateConverter):
            return map(num2date, lim)
        # Cast to builtin floats as they have nicer reprs.
        return map(float, lim)

    axis_map = axes._axis_map
    axis_limits = {
        name: tuple(convert_limits(
            getattr(axes, f'get_{name}lim')(), axis.get_converter()
        ))
        for name, axis in axis_map.items()
    }
    general = [
        ('Title', axes.get_title()),
        sep,
        *chain.from_iterable([
            (
                (None, f"<b>{name.title()}-Axis</b>"),
                ('Min', axis_limits[name][0]),
                ('Max', axis_limits[name][1]),
                ('Label', axis.label.get_text()),
                ('Scale', [axis.get_scale(),
                           'linear', 'log', 'symlog', 'logit']),
                sep,
            )
            for name, axis in axis_map.items()
        ]),
        ('(Re-)Generate automatic legend', False),
    ]

    # Save the converter and unit data
    axis_converter = {
        name: axis.get_converter()
        for name, axis in axis_map.items()
    }
    axis_units = {
        name: axis.get_units()
        for name, axis in axis_map.items()
    }

    # Get / Curves
    labeled_lines = []
    for line in axes.get_lines():
        label = line.get_label()
        if label == '_nolegend_':
            continue
        labeled_lines.append((label, line))
    curves = []

    def prepare_data(d, init):
        """
        Prepare entry for FormLayout.

        *d* is a mapping of shorthands to style names (a single style may
        have multiple shorthands, in particular the shorthands `None`,
        `"None"`, `"none"` and `""` are synonyms); *init* is one shorthand
        of the initial style.

        This function returns an list suitable for initializing a
        FormLayout combobox, namely `[initial_name, (shorthand,
        style_name), (shorthand, style_name), ...]`.
        """
        if init not in d:
            d = {**d, init: str(init)}
        # Drop duplicate shorthands from dict (by overwriting them during
        # the dict comprehension).
        name2short = {name: short for short, name in d.items()}
        # Convert back to {shorthand: name}.
        short2name = {short: name for name, short in name2short.items()}
        # Find the kept shorthand for the style specified by init.
        canonical_init = name2short[d[init]]
        # Sort by representation and prepend the initial value.
        return ([canonical_init] +
                sorted(short2name.items(),
                       key=lambda short_and_name: short_and_name[1]))

    for label, line in labeled_lines:
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        fc = mcolors.to_hex(
            mcolors.to_rgba(line.get_markerfacecolor(), line.get_alpha()),
            keep_alpha=True)
        curvedata = [
            ('Label', label),
            sep,
            (None, '<b>Line</b>'),
            ('Line style', prepare_data(LINESTYLES, line.get_linestyle())),
            ('Draw style', prepare_data(DRAWSTYLES, line.get_drawstyle())),
            ('Width', line.get_linewidth()),
            ('Color (RGBA)', color),
            sep,
            (None, '<b>Marker</b>'),
            ('Style', prepare_data(MARKERS, line.get_marker())),
            ('Size', line.get_markersize()),
            ('Face color (RGBA)', fc),
            ('Edge color (RGBA)', ec)]
        curves.append([curvedata, label, ""])
    # Is there a curve displayed?
    has_curve = bool(curves)

    # Get ScalarMappables.
    labeled_mappables = []
    for mappable in [*axes.images, *axes.collections]:
        label = mappable.get_label()
        if label == '_nolegend_' or mappable.get_array() is None:
            continue
        labeled_mappables.append((label, mappable))
    mappables = []
    cmaps = [(cmap, name) for name, cmap in sorted(cm._colormaps.items())]
    for label, mappable in labeled_mappables:
        cmap = mappable.get_cmap()
        if cmap.name not in cm._colormaps:
            cmaps = [(cmap, cmap.name), *cmaps]
        low, high = mappable.get_clim()
        mappabledata = [
            ('Label', label),
            ('Colormap', [cmap.name] + cmaps),
            ('Min. value', low),
            ('Max. value', high),
        ]
        if hasattr(mappable, "get_interpolation"):  # Images.
            interpolations = [
                (name, name) for name in sorted(mimage.interpolations_names)]
            mappabledata.append((
                'Interpolation',
                [mappable.get_interpolation(), *interpolations]))

            interpolation_stages = ['data', 'rgba', 'auto']
            mappabledata.append((
                'Interpolation stage',
                [mappable.get_interpolation_stage(), *interpolation_stages]))

        mappables.append([mappabledata, label, ""])
    # Is there a scalarmappable displayed?
    has_sm = bool(mappables)

    datalist = [(general, "Axes", "")]
    if curves:
        datalist.append((curves, "Curves", ""))
    if mappables:
        datalist.append((mappables, "Images, etc.", ""))

    def apply_callback(data):
        """A callback to apply changes."""
        orig_limits = {
            name: getattr(axes, f"get_{name}lim")()
            for name in axis_map
        }

        general = data.pop(0)
        curves = data.pop(0) if has_curve else []
        mappables = data.pop(0) if has_sm else []
        if data:
            raise ValueError("Unexpected field")

        title = general.pop(0)
        axes.set_title(title)
        generate_legend = general.pop()

        for i, (name, axis) in enumerate(axis_map.items()):
            axis_min = general[4*i]
            axis_max = general[4*i + 1]
            axis_label = general[4*i + 2]
            axis_scale = general[4*i + 3]
            if axis.get_scale() != axis_scale:
                getattr(axes, f"set_{name}scale")(axis_scale)

            axis._set_lim(axis_min, axis_max, auto=False)
            axis.set_label_text(axis_label)

            # Restore the unit data
            axis._set_converter(axis_converter[name])
            axis.set_units(axis_units[name])

        # Set / Curves
        for index, curve in enumerate(curves):
            line = labeled_lines[index][1]
            (label, linestyle, drawstyle, linewidth, color, marker, markersize,
             markerfacecolor, markeredgecolor) = curve
            line.set_label(label)
            line.set_linestyle(linestyle)
            line.set_drawstyle(drawstyle)
            line.set_linewidth(linewidth)
            rgba = mcolors.to_rgba(color)
            line.set_alpha(None)
            line.set_color(rgba)
            if marker != 'none':
                line.set_marker(marker)
                line.set_markersize(markersize)
                line.set_markerfacecolor(markerfacecolor)
                line.set_markeredgecolor(markeredgecolor)

        # Set ScalarMappables.
        for index, mappable_settings in enumerate(mappables):
            mappable = labeled_mappables[index][1]
            if len(mappable_settings) == 6:
                label, cmap, low, high, interpolation, interpolation_stage = \
                  mappable_settings
                mappable.set_interpolation(interpolation)
                mappable.set_interpolation_stage(interpolation_stage)
            elif len(mappable_settings) == 4:
                label, cmap, low, high = mappable_settings
            mappable.set_label(label)
            mappable.set_cmap(cmap)
            mappable.set_clim(*sorted([low, high]))

        # re-generate legend, if checkbox is checked
        if generate_legend:
            draggable = None
            ncols = 1
            if axes.legend_ is not None:
                old_legend = axes.get_legend()
                draggable = old_legend._draggable is not None
                ncols = old_legend._ncols
            new_legend = axes.legend(ncols=ncols)
            if new_legend:
                new_legend.set_draggable(draggable)

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()
        for name in axis_map:
            if getattr(axes, f"get_{name}lim")() != orig_limits[name]:
                figure.canvas.toolbar.push_current()
                break

    _formlayout.fedit(
        datalist, title="Figure options", parent=parent,
        icon=QtGui.QIcon(
            str(cbook._get_data_path('images', 'qt4_editor_options.svg'))),
        apply=apply_callback)

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\axes_size.py ===
"""
Provides classes of simple units that will be used with `.AxesDivider`
class (or others) to determine the size of each Axes. The unit
classes define `get_size` method that returns a tuple of two floats,
meaning relative and absolute sizes, respectively.

Note that this class is nothing more than a simple tuple of two
floats. Take a look at the Divider class to see how these two
values are used.

Once created, the unit classes can be modified by simple arithmetic
operations: addition /subtraction with another unit type or a real number and scaling
(multiplication or division) by a real number.
"""

from numbers import Real

from matplotlib import _api
from matplotlib.axes import Axes


class _Base:
    def __rmul__(self, other):
        return self * other

    def __mul__(self, other):
        if not isinstance(other, Real):
            return NotImplemented
        return Fraction(other, self)

    def __div__(self, other):
        return (1 / other) * self

    def __add__(self, other):
        if isinstance(other, _Base):
            return Add(self, other)
        else:
            return Add(self, Fixed(other))

    def __neg__(self):
        return -1 * self

    def __radd__(self, other):
        # other cannot be a _Base instance, because A + B would trigger
        # A.__add__(B) first.
        return Add(self, Fixed(other))

    def __sub__(self, other):
        return self + (-other)

    def get_size(self, renderer):
        """
        Return two-float tuple with relative and absolute sizes.
        """
        raise NotImplementedError("Subclasses must implement")


class Add(_Base):
    """
    Sum of two sizes.
    """

    def __init__(self, a, b):
        self._a = a
        self._b = b

    def get_size(self, renderer):
        a_rel_size, a_abs_size = self._a.get_size(renderer)
        b_rel_size, b_abs_size = self._b.get_size(renderer)
        return a_rel_size + b_rel_size, a_abs_size + b_abs_size


class Fixed(_Base):
    """
    Simple fixed size with absolute part = *fixed_size* and relative part = 0.
    """

    def __init__(self, fixed_size):
        _api.check_isinstance(Real, fixed_size=fixed_size)
        self.fixed_size = fixed_size

    def get_size(self, renderer):
        rel_size = 0.
        abs_size = self.fixed_size
        return rel_size, abs_size


class Scaled(_Base):
    """
    Simple scaled(?) size with absolute part = 0 and
    relative part = *scalable_size*.
    """

    def __init__(self, scalable_size):
        self._scalable_size = scalable_size

    def get_size(self, renderer):
        rel_size = self._scalable_size
        abs_size = 0.
        return rel_size, abs_size

Scalable = Scaled


def _get_axes_aspect(ax):
    aspect = ax.get_aspect()
    if aspect == "auto":
        aspect = 1.
    return aspect


class AxesX(_Base):
    """
    Scaled size whose relative part corresponds to the data width
    of the *axes* multiplied by the *aspect*.
    """

    def __init__(self, axes, aspect=1., ref_ax=None):
        self._axes = axes
        self._aspect = aspect
        if aspect == "axes" and ref_ax is None:
            raise ValueError("ref_ax must be set when aspect='axes'")
        self._ref_ax = ref_ax

    def get_size(self, renderer):
        l1, l2 = self._axes.get_xlim()
        if self._aspect == "axes":
            ref_aspect = _get_axes_aspect(self._ref_ax)
            aspect = ref_aspect / _get_axes_aspect(self._axes)
        else:
            aspect = self._aspect

        rel_size = abs(l2-l1)*aspect
        abs_size = 0.
        return rel_size, abs_size


class AxesY(_Base):
    """
    Scaled size whose relative part corresponds to the data height
    of the *axes* multiplied by the *aspect*.
    """

    def __init__(self, axes, aspect=1., ref_ax=None):
        self._axes = axes
        self._aspect = aspect
        if aspect == "axes" and ref_ax is None:
            raise ValueError("ref_ax must be set when aspect='axes'")
        self._ref_ax = ref_ax

    def get_size(self, renderer):
        l1, l2 = self._axes.get_ylim()

        if self._aspect == "axes":
            ref_aspect = _get_axes_aspect(self._ref_ax)
            aspect = _get_axes_aspect(self._axes)
        else:
            aspect = self._aspect

        rel_size = abs(l2-l1)*aspect
        abs_size = 0.
        return rel_size, abs_size


class MaxExtent(_Base):
    """
    Size whose absolute part is either the largest width or the largest height
    of the given *artist_list*.
    """

    def __init__(self, artist_list, w_or_h):
        self._artist_list = artist_list
        _api.check_in_list(["width", "height"], w_or_h=w_or_h)
        self._w_or_h = w_or_h

    def add_artist(self, a):
        self._artist_list.append(a)

    def get_size(self, renderer):
        rel_size = 0.
        extent_list = [
            getattr(a.get_window_extent(renderer), self._w_or_h) / a.figure.dpi
            for a in self._artist_list]
        abs_size = max(extent_list, default=0)
        return rel_size, abs_size


class MaxWidth(MaxExtent):
    """
    Size whose absolute part is the largest width of the given *artist_list*.
    """

    def __init__(self, artist_list):
        super().__init__(artist_list, "width")


class MaxHeight(MaxExtent):
    """
    Size whose absolute part is the largest height of the given *artist_list*.
    """

    def __init__(self, artist_list):
        super().__init__(artist_list, "height")


class Fraction(_Base):
    """
    An instance whose size is a *fraction* of the *ref_size*.

    >>> s = Fraction(0.3, AxesX(ax))
    """

    def __init__(self, fraction, ref_size):
        _api.check_isinstance(Real, fraction=fraction)
        self._fraction_ref = ref_size
        self._fraction = fraction

    def get_size(self, renderer):
        if self._fraction_ref is None:
            return self._fraction, 0.
        else:
            r, a = self._fraction_ref.get_size(renderer)
            rel_size = r*self._fraction
            abs_size = a*self._fraction
            return rel_size, abs_size


def from_any(size, fraction_ref=None):
    """
    Create a Fixed unit when the first argument is a float, or a
    Fraction unit if that is a string that ends with %. The second
    argument is only meaningful when Fraction unit is created.

    >>> from mpl_toolkits.axes_grid1.axes_size import from_any
    >>> a = from_any(1.2) # => Fixed(1.2)
    >>> from_any("50%", a) # => Fraction(0.5, a)
    """
    if isinstance(size, Real):
        return Fixed(size)
    elif isinstance(size, str):
        if size[-1] == "%":
            return Fraction(float(size[:-1]) / 100, fraction_ref)
    raise ValueError("Unknown format")


class _AxesDecorationsSize(_Base):
    """
    Fixed size, corresponding to the size of decorations on a given Axes side.
    """

    _get_size_map = {
        "left":   lambda tight_bb, axes_bb: axes_bb.xmin - tight_bb.xmin,
        "right":  lambda tight_bb, axes_bb: tight_bb.xmax - axes_bb.xmax,
        "bottom": lambda tight_bb, axes_bb: axes_bb.ymin - tight_bb.ymin,
        "top":    lambda tight_bb, axes_bb: tight_bb.ymax - axes_bb.ymax,
    }

    def __init__(self, ax, direction):
        _api.check_in_list(self._get_size_map, direction=direction)
        self._direction = direction
        self._ax_list = [ax] if isinstance(ax, Axes) else ax

    def get_size(self, renderer):
        sz = max([
            self._get_size_map[self._direction](
                ax.get_tightbbox(renderer, call_axes_locator=False), ax.bbox)
            for ax in self._ax_list])
        dpi = renderer.points_to_pixels(72)
        abs_size = sz / dpi
        rel_size = 0
        return rel_size, abs_size

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\timeout.py ===
from __future__ import absolute_import

import time

# The default socket timeout, used by httplib to indicate that no timeout was; specified by the user
from socket import _GLOBAL_DEFAULT_TIMEOUT, getdefaulttimeout

from ..exceptions import TimeoutStateError

# A sentinel value to indicate that no timeout was specified by the user in
# urllib3
_Default = object()


# Use time.monotonic if available.
current_time = getattr(time, "monotonic", time.time)


class Timeout(object):
    """Timeout configuration.

    Timeouts can be defined as a default for a pool:

    .. code-block:: python

       timeout = Timeout(connect=2.0, read=7.0)
       http = PoolManager(timeout=timeout)
       response = http.request('GET', 'http://example.com/')

    Or per-request (which overrides the default for the pool):

    .. code-block:: python

       response = http.request('GET', 'http://example.com/', timeout=Timeout(10))

    Timeouts can be disabled by setting all the parameters to ``None``:

    .. code-block:: python

       no_timeout = Timeout(connect=None, read=None)
       response = http.request('GET', 'http://example.com/, timeout=no_timeout)


    :param total:
        This combines the connect and read timeouts into one; the read timeout
        will be set to the time leftover from the connect attempt. In the
        event that both a connect timeout and a total are specified, or a read
        timeout and a total are specified, the shorter timeout will be applied.

        Defaults to None.

    :type total: int, float, or None

    :param connect:
        The maximum amount of time (in seconds) to wait for a connection
        attempt to a server to succeed. Omitting the parameter will default the
        connect timeout to the system default, probably `the global default
        timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout for connection attempts.

    :type connect: int, float, or None

    :param read:
        The maximum amount of time (in seconds) to wait between consecutive
        read operations for a response from the server. Omitting the parameter
        will default the read timeout to the system default, probably `the
        global default timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout.

    :type read: int, float, or None

    .. note::

        Many factors can affect the total amount of time for urllib3 to return
        an HTTP response.

        For example, Python's DNS resolver does not obey the timeout specified
        on the socket. Other factors that can affect total request time include
        high CPU load, high swap, the program running at a low priority level,
        or other behaviors.

        In addition, the read and total timeouts only measure the time between
        read operations on the socket connecting the client and the server,
        not the total amount of time for the request to return a complete
        response. For most requests, the timeout is raised because the server
        has not sent the first byte in the specified time. This is not always
        the case; if a server streams one byte every fifteen seconds, a timeout
        of 20 seconds will not trigger, even though the request will take
        several minutes to complete.

        If your goal is to cut off any request after a set amount of wall clock
        time, consider having a second "watcher" thread to cut off a slow
        request.
    """

    #: A sentinel object representing the default timeout value
    DEFAULT_TIMEOUT = _GLOBAL_DEFAULT_TIMEOUT

    def __init__(self, total=None, connect=_Default, read=_Default):
        self._connect = self._validate_timeout(connect, "connect")
        self._read = self._validate_timeout(read, "read")
        self.total = self._validate_timeout(total, "total")
        self._start_connect = None

    def __repr__(self):
        return "%s(connect=%r, read=%r, total=%r)" % (
            type(self).__name__,
            self._connect,
            self._read,
            self.total,
        )

    # __str__ provided for backwards compatibility
    __str__ = __repr__

    @classmethod
    def resolve_default_timeout(cls, timeout):
        return getdefaulttimeout() if timeout is cls.DEFAULT_TIMEOUT else timeout

    @classmethod
    def _validate_timeout(cls, value, name):
        """Check that a timeout attribute is valid.

        :param value: The timeout value to validate
        :param name: The name of the timeout attribute to validate. This is
            used to specify in error messages.
        :return: The validated and casted version of the given value.
        :raises ValueError: If it is a numeric value less than or equal to
            zero, or the type is not an integer, float, or None.
        """
        if value is _Default:
            return cls.DEFAULT_TIMEOUT

        if value is None or value is cls.DEFAULT_TIMEOUT:
            return value

        if isinstance(value, bool):
            raise ValueError(
                "Timeout cannot be a boolean value. It must "
                "be an int, float or None."
            )
        try:
            float(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            )

        try:
            if value <= 0:
                raise ValueError(
                    "Attempted to set %s timeout to %s, but the "
                    "timeout cannot be set to a value less "
                    "than or equal to 0." % (name, value)
                )
        except TypeError:
            # Python 3
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            )

        return value

    @classmethod
    def from_float(cls, timeout):
        """Create a new Timeout from a legacy timeout value.

        The timeout value used by httplib.py sets the same timeout on the
        connect(), and recv() socket requests. This creates a :class:`Timeout`
        object that sets the individual timeouts to the ``timeout`` value
        passed to this function.

        :param timeout: The legacy timeout value.
        :type timeout: integer, float, sentinel default object, or None
        :return: Timeout object
        :rtype: :class:`Timeout`
        """
        return Timeout(read=timeout, connect=timeout)

    def clone(self):
        """Create a copy of the timeout object

        Timeout properties are stored per-pool but each request needs a fresh
        Timeout object to ensure each one has its own start/stop configured.

        :return: a copy of the timeout object
        :rtype: :class:`Timeout`
        """
        # We can't use copy.deepcopy because that will also create a new object
        # for _GLOBAL_DEFAULT_TIMEOUT, which socket.py uses as a sentinel to
        # detect the user default.
        return Timeout(connect=self._connect, read=self._read, total=self.total)

    def start_connect(self):
        """Start the timeout clock, used during a connect() attempt

        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to start a timer that has been started already.
        """
        if self._start_connect is not None:
            raise TimeoutStateError("Timeout timer has already been started.")
        self._start_connect = current_time()
        return self._start_connect

    def get_connect_duration(self):
        """Gets the time elapsed since the call to :meth:`start_connect`.

        :return: Elapsed time in seconds.
        :rtype: float
        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to get duration for a timer that hasn't been started.
        """
        if self._start_connect is None:
            raise TimeoutStateError(
                "Can't get connect duration for timer that has not started."
            )
        return current_time() - self._start_connect

    @property
    def connect_timeout(self):
        """Get the value to use when setting a connection timeout.

        This will be a positive float or integer, the value None
        (never timeout), or the default system timeout.

        :return: Connect timeout.
        :rtype: int, float, :attr:`Timeout.DEFAULT_TIMEOUT` or None
        """
        if self.total is None:
            return self._connect

        if self._connect is None or self._connect is self.DEFAULT_TIMEOUT:
            return self.total

        return min(self._connect, self.total)

    @property
    def read_timeout(self):
        """Get the value for the read timeout.

        This assumes some time has elapsed in the connection timeout and
        computes the read timeout appropriately.

        If self.total is set, the read timeout is dependent on the amount of
        time taken by the connect timeout. If the connection time has not been
        established, a :exc:`~urllib3.exceptions.TimeoutStateError` will be
        raised.

        :return: Value to use for the read timeout.
        :rtype: int, float, :attr:`Timeout.DEFAULT_TIMEOUT` or None
        :raises urllib3.exceptions.TimeoutStateError: If :meth:`start_connect`
            has not yet been called on this object.
        """
        if (
            self.total is not None
            and self.total is not self.DEFAULT_TIMEOUT
            and self._read is not None
            and self._read is not self.DEFAULT_TIMEOUT
        ):
            # In case the connect timeout has not yet been established.
            if self._start_connect is None:
                return self._read
            return max(0, min(self.total - self.get_connect_duration(), self._read))
        elif self.total is not None and self.total is not self.DEFAULT_TIMEOUT:
            return max(0, self.total - self.get_connect_duration())
        else:
            return self._read

# === NexusCore/openenv\Lib\site-packages\urllib3\util\ssltransport.py ===
from __future__ import annotations

import io
import socket
import ssl
import typing

from ..exceptions import ProxySchemeUnsupported

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    from .ssl_ import _TYPE_PEER_CERT_RET, _TYPE_PEER_CERT_RET_DICT


_WriteBuffer = typing.Union[bytearray, memoryview]
_ReturnValue = typing.TypeVar("_ReturnValue")

SSL_BLOCKSIZE = 16384


class SSLTransport:
    """
    The SSLTransport wraps an existing socket and establishes an SSL connection.

    Contrary to Python's implementation of SSLSocket, it allows you to chain
    multiple TLS connections together. It's particularly useful if you need to
    implement TLS within TLS.

    The class supports most of the socket API operations.
    """

    @staticmethod
    def _validate_ssl_context_for_tls_in_tls(ssl_context: ssl.SSLContext) -> None:
        """
        Raises a ProxySchemeUnsupported if the provided ssl_context can't be used
        for TLS in TLS.

        The only requirement is that the ssl_context provides the 'wrap_bio'
        methods.
        """

        if not hasattr(ssl_context, "wrap_bio"):
            raise ProxySchemeUnsupported(
                "TLS in TLS requires SSLContext.wrap_bio() which isn't "
                "available on non-native SSLContext"
            )

    def __init__(
        self,
        socket: socket.socket,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        suppress_ragged_eofs: bool = True,
    ) -> None:
        """
        Create an SSLTransport around socket using the provided ssl_context.
        """
        self.incoming = ssl.MemoryBIO()
        self.outgoing = ssl.MemoryBIO()

        self.suppress_ragged_eofs = suppress_ragged_eofs
        self.socket = socket

        self.sslobj = ssl_context.wrap_bio(
            self.incoming, self.outgoing, server_hostname=server_hostname
        )

        # Perform initial handshake.
        self._ssl_io_loop(self.sslobj.do_handshake)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: typing.Any) -> None:
        self.close()

    def fileno(self) -> int:
        return self.socket.fileno()

    def read(self, len: int = 1024, buffer: typing.Any | None = None) -> int | bytes:
        return self._wrap_ssl_read(len, buffer)

    def recv(self, buflen: int = 1024, flags: int = 0) -> int | bytes:
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv")
        return self._wrap_ssl_read(buflen)

    def recv_into(
        self,
        buffer: _WriteBuffer,
        nbytes: int | None = None,
        flags: int = 0,
    ) -> None | int | bytes:
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv_into")
        if nbytes is None:
            nbytes = len(buffer)
        return self.read(nbytes, buffer)

    def sendall(self, data: bytes, flags: int = 0) -> None:
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to sendall")
        count = 0
        with memoryview(data) as view, view.cast("B") as byte_view:
            amount = len(byte_view)
            while count < amount:
                v = self.send(byte_view[count:])
                count += v

    def send(self, data: bytes, flags: int = 0) -> int:
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to send")
        return self._ssl_io_loop(self.sslobj.write, data)

    def makefile(
        self,
        mode: str,
        buffering: int | None = None,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> typing.BinaryIO | typing.TextIO | socket.SocketIO:
        """
        Python's httpclient uses makefile and buffered io when reading HTTP
        messages and we need to support it.

        This is unfortunately a copy and paste of socket.py makefile with small
        changes to point to the socket directly.
        """
        if not set(mode) <= {"r", "w", "b"}:
            raise ValueError(f"invalid mode {mode!r} (only r, w, b allowed)")

        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = socket.SocketIO(self, rawmode)  # type: ignore[arg-type]
        self.socket._io_refs += 1  # type: ignore[attr-defined]
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        buffer: typing.BinaryIO
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)  # type: ignore[assignment]
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode  # type: ignore[misc]
        return text

    def unwrap(self) -> None:
        self._ssl_io_loop(self.sslobj.unwrap)

    def close(self) -> None:
        self.socket.close()

    @typing.overload
    def getpeercert(
        self, binary_form: typing.Literal[False] = ...
    ) -> _TYPE_PEER_CERT_RET_DICT | None: ...

    @typing.overload
    def getpeercert(self, binary_form: typing.Literal[True]) -> bytes | None: ...

    def getpeercert(self, binary_form: bool = False) -> _TYPE_PEER_CERT_RET:
        return self.sslobj.getpeercert(binary_form)  # type: ignore[return-value]

    def version(self) -> str | None:
        return self.sslobj.version()

    def cipher(self) -> tuple[str, str, int] | None:
        return self.sslobj.cipher()

    def selected_alpn_protocol(self) -> str | None:
        return self.sslobj.selected_alpn_protocol()

    def shared_ciphers(self) -> list[tuple[str, str, int]] | None:
        return self.sslobj.shared_ciphers()

    def compression(self) -> str | None:
        return self.sslobj.compression()

    def settimeout(self, value: float | None) -> None:
        self.socket.settimeout(value)

    def gettimeout(self) -> float | None:
        return self.socket.gettimeout()

    def _decref_socketios(self) -> None:
        self.socket._decref_socketios()  # type: ignore[attr-defined]

    def _wrap_ssl_read(self, len: int, buffer: bytearray | None = None) -> int | bytes:
        try:
            return self._ssl_io_loop(self.sslobj.read, len, buffer)
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_EOF and self.suppress_ragged_eofs:
                return 0  # eof, return 0.
            else:
                raise

    # func is sslobj.do_handshake or sslobj.unwrap
    @typing.overload
    def _ssl_io_loop(self, func: typing.Callable[[], None]) -> None: ...

    # func is sslobj.write, arg1 is data
    @typing.overload
    def _ssl_io_loop(self, func: typing.Callable[[bytes], int], arg1: bytes) -> int: ...

    # func is sslobj.read, arg1 is len, arg2 is buffer
    @typing.overload
    def _ssl_io_loop(
        self,
        func: typing.Callable[[int, bytearray | None], bytes],
        arg1: int,
        arg2: bytearray | None,
    ) -> bytes: ...

    def _ssl_io_loop(
        self,
        func: typing.Callable[..., _ReturnValue],
        arg1: None | bytes | int = None,
        arg2: bytearray | None = None,
    ) -> _ReturnValue:
        """Performs an I/O loop between incoming/outgoing and the socket."""
        should_loop = True
        ret = None

        while should_loop:
            errno = None
            try:
                if arg1 is None and arg2 is None:
                    ret = func()
                elif arg2 is None:
                    ret = func(arg1)
                else:
                    ret = func(arg1, arg2)
            except ssl.SSLError as e:
                if e.errno not in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    # WANT_READ, and WANT_WRITE are expected, others are not.
                    raise e
                errno = e.errno

            buf = self.outgoing.read()
            self.socket.sendall(buf)

            if errno is None:
                should_loop = False
            elif errno == ssl.SSL_ERROR_WANT_READ:
                buf = self.socket.recv(SSL_BLOCKSIZE)
                if buf:
                    self.incoming.write(buf)
                else:
                    self.incoming.write_eof()
        return typing.cast(_ReturnValue, ret)

# === NexusCore/openenv\Lib\site-packages\joblib\hashing.py ===
"""
Fast cryptographic hash of Python objects, with a special case for fast
hashing of numpy arrays.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import decimal
import hashlib
import io
import pickle
import struct
import sys
import types

Pickler = pickle._Pickler


class _ConsistentSet(object):
    """Class used to ensure the hash of Sets is preserved
    whatever the order of its items.
    """

    def __init__(self, set_sequence):
        # Forces order of elements in set to ensure consistent hash.
        try:
            # Trying first to order the set assuming the type of elements is
            # consistent and orderable.
            # This fails on python 3 when elements are unorderable
            # but we keep it in a try as it's faster.
            self._sequence = sorted(set_sequence)
        except (TypeError, decimal.InvalidOperation):
            # If elements are unorderable, sorting them using their hash.
            # This is slower but works in any case.
            self._sequence = sorted((hash(e) for e in set_sequence))


class _MyHash(object):
    """Class used to hash objects that won't normally pickle"""

    def __init__(self, *args):
        self.args = args


class Hasher(Pickler):
    """A subclass of pickler, to do cryptographic hashing, rather than
    pickling. This is used to produce a unique hash of the given
    Python object that is not necessarily cryptographically secure.
    """

    def __init__(self, hash_name="md5"):
        self.stream = io.BytesIO()
        # By default we want a pickle protocol that only changes with
        # the major python version and not the minor one
        protocol = 3
        Pickler.__init__(self, self.stream, protocol=protocol)
        # Initialise the hash obj
        self._hash = hashlib.new(hash_name, usedforsecurity=False)

    def hash(self, obj, return_digest=True):
        try:
            self.dump(obj)
        except pickle.PicklingError as e:
            e.args += ("PicklingError while hashing %r: %r" % (obj, e),)
            raise
        dumps = self.stream.getvalue()
        self._hash.update(dumps)
        if return_digest:
            return self._hash.hexdigest()

    def save(self, obj):
        if isinstance(obj, (types.MethodType, type({}.pop))):
            # the Pickler cannot pickle instance methods; here we decompose
            # them into components that make them uniquely identifiable
            if hasattr(obj, "__func__"):
                func_name = obj.__func__.__name__
            else:
                func_name = obj.__name__
            inst = obj.__self__
            if type(inst) is type(pickle):
                obj = _MyHash(func_name, inst.__name__)
            elif inst is None:
                # type(None) or type(module) do not pickle
                obj = _MyHash(func_name, inst)
            else:
                cls = obj.__self__.__class__
                obj = _MyHash(func_name, inst, cls)
        Pickler.save(self, obj)

    def memoize(self, obj):
        # We want hashing to be sensitive to value instead of reference.
        # For example we want ['aa', 'aa'] and ['aa', 'aaZ'[:2]]
        # to hash to the same value and that's why we disable memoization
        # for strings
        if isinstance(obj, (bytes, str)):
            return
        Pickler.memoize(self, obj)

    # The dispatch table of the pickler is not accessible in Python
    # 3, as these lines are only bugware for IPython, we skip them.
    def save_global(self, obj, name=None, pack=struct.pack):
        # We have to override this method in order to deal with objects
        # defined interactively in IPython that are not injected in
        # __main__
        kwargs = dict(name=name, pack=pack)
        del kwargs["pack"]
        try:
            Pickler.save_global(self, obj, **kwargs)
        except pickle.PicklingError:
            Pickler.save_global(self, obj, **kwargs)
            module = getattr(obj, "__module__", None)
            if module == "__main__":
                my_name = name
                if my_name is None:
                    my_name = obj.__name__
                mod = sys.modules[module]
                if not hasattr(mod, my_name):
                    # IPython doesn't inject the variables define
                    # interactively in __main__
                    setattr(mod, my_name, obj)

    dispatch = Pickler.dispatch.copy()
    # builtin
    dispatch[type(len)] = save_global
    # type
    dispatch[type(object)] = save_global
    # classobj
    dispatch[type(Pickler)] = save_global
    # function
    dispatch[type(pickle.dump)] = save_global

    # We use *args in _batch_setitems signature because _batch_setitems has an
    # additional 'obj' argument in Python 3.14
    def _batch_setitems(self, items, *args):
        # forces order of keys in dict to ensure consistent hash.
        try:
            # Trying first to compare dict assuming the type of keys is
            # consistent and orderable.
            # This fails on python 3 when keys are unorderable
            # but we keep it in a try as it's faster.
            Pickler._batch_setitems(self, iter(sorted(items)), *args)
        except TypeError:
            # If keys are unorderable, sorting them using their hash. This is
            # slower but works in any case.
            Pickler._batch_setitems(
                self, iter(sorted((hash(k), v) for k, v in items)), *args
            )

    def save_set(self, set_items):
        # forces order of items in Set to ensure consistent hash
        Pickler.save(self, _ConsistentSet(set_items))

    dispatch[type(set())] = save_set


class NumpyHasher(Hasher):
    """Special case the hasher for when numpy is loaded."""

    def __init__(self, hash_name="md5", coerce_mmap=False):
        """
        Parameters
        ----------
        hash_name: string
            The hash algorithm to be used
        coerce_mmap: boolean
            Make no difference between np.memmap and np.ndarray
            objects.
        """
        self.coerce_mmap = coerce_mmap
        Hasher.__init__(self, hash_name=hash_name)
        # delayed import of numpy, to avoid tight coupling
        import numpy as np

        self.np = np
        if hasattr(np, "getbuffer"):
            self._getbuffer = np.getbuffer
        else:
            self._getbuffer = memoryview

    def save(self, obj):
        """Subclass the save method, to hash ndarray subclass, rather
        than pickling them. Off course, this is a total abuse of
        the Pickler class.
        """
        if isinstance(obj, self.np.ndarray) and not obj.dtype.hasobject:
            # Compute a hash of the object
            # The update function of the hash requires a c_contiguous buffer.
            if obj.shape == ():
                # 0d arrays need to be flattened because viewing them as bytes
                # raises a ValueError exception.
                obj_c_contiguous = obj.flatten()
            elif obj.flags.c_contiguous:
                obj_c_contiguous = obj
            elif obj.flags.f_contiguous:
                obj_c_contiguous = obj.T
            else:
                # Cater for non-single-segment arrays: this creates a
                # copy, and thus alleviates this issue.
                # XXX: There might be a more efficient way of doing this
                obj_c_contiguous = obj.flatten()

            # memoryview is not supported for some dtypes, e.g. datetime64, see
            # https://github.com/numpy/numpy/issues/4983. The
            # workaround is to view the array as bytes before
            # taking the memoryview.
            self._hash.update(self._getbuffer(obj_c_contiguous.view(self.np.uint8)))

            # We store the class, to be able to distinguish between
            # Objects with the same binary content, but different
            # classes.
            if self.coerce_mmap and isinstance(obj, self.np.memmap):
                # We don't make the difference between memmap and
                # normal ndarrays, to be able to reload previously
                # computed results with memmap.
                klass = self.np.ndarray
            else:
                klass = obj.__class__
            # We also return the dtype and the shape, to distinguish
            # different views on the same data with different dtypes.

            # The object will be pickled by the pickler hashed at the end.
            obj = (klass, ("HASHED", obj.dtype, obj.shape, obj.strides))
        elif isinstance(obj, self.np.dtype):
            # numpy.dtype consistent hashing is tricky to get right. This comes
            # from the fact that atomic np.dtype objects are interned:
            # ``np.dtype('f4') is np.dtype('f4')``. The situation is
            # complicated by the fact that this interning does not resist a
            # simple pickle.load/dump roundtrip:
            # ``pickle.loads(pickle.dumps(np.dtype('f4'))) is not
            # np.dtype('f4') Because pickle relies on memoization during
            # pickling, it is easy to
            # produce different hashes for seemingly identical objects, such as
            # ``[np.dtype('f4'), np.dtype('f4')]``
            # and ``[np.dtype('f4'), pickle.loads(pickle.dumps('f4'))]``.
            # To prevent memoization from interfering with hashing, we isolate
            # the serialization (and thus the pickle memoization) of each dtype
            # using each time a different ``pickle.dumps`` call unrelated to
            # the current Hasher instance.
            self._hash.update("_HASHED_DTYPE".encode("utf-8"))
            self._hash.update(pickle.dumps(obj))
            return
        Hasher.save(self, obj)


def hash(obj, hash_name="md5", coerce_mmap=False):
    """Quick calculation of a hash to identify uniquely Python objects
    containing numpy arrays.

    Parameters
    ----------
    hash_name: 'md5' or 'sha1'
        Hashing algorithm used. sha1 is supposedly safer, but md5 is
        faster.
    coerce_mmap: boolean
        Make no difference between np.memmap and np.ndarray
    """
    valid_hash_names = ("md5", "sha1")
    if hash_name not in valid_hash_names:
        raise ValueError(
            "Valid options for 'hash_name' are {}. Got hash_name={!r} instead.".format(
                valid_hash_names, hash_name
            )
        )
    if "numpy" in sys.modules:
        hasher = NumpyHasher(hash_name=hash_name, coerce_mmap=coerce_mmap)
    else:
        hasher = Hasher(hash_name=hash_name)
    return hasher.hash(obj)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\deepgram\audio_transcription\transformation.py ===
"""
Translates from OpenAI's `/v1/audio/transcriptions` to Deepgram's `/v1/listen`
"""

import io
from typing import List, Optional, Union
from urllib.parse import urlencode

from httpx import Headers, Response

from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import (
    AllMessageValues,
    OpenAIAudioTranscriptionOptionalParams,
)
from litellm.types.utils import FileTypes, TranscriptionResponse

from ...base_llm.audio_transcription.transformation import (
    BaseAudioTranscriptionConfig,
    LiteLLMLoggingObj,
)
from ..common_utils import DeepgramException


class DeepgramAudioTranscriptionConfig(BaseAudioTranscriptionConfig):
    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAIAudioTranscriptionOptionalParams]:
        return ["language"]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        supported_params = self.get_supported_openai_params(model)
        for k, v in non_default_params.items():
            if k in supported_params:
                optional_params[k] = v
        return optional_params

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return DeepgramException(
            message=error_message, status_code=status_code, headers=headers
        )

    def transform_audio_transcription_request(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        litellm_params: dict,
    ) -> Union[dict, bytes]:
        """
        Processes the audio file input based on its type and returns the binary data.

        Args:
            audio_file: Can be a file path (str), a tuple (filename, file_content), or binary data (bytes).

        Returns:
            The binary data of the audio file.
        """
        binary_data: bytes  # Explicitly declare the type

        # Handle the audio file based on type
        if isinstance(audio_file, str):
            # If it's a file path
            with open(audio_file, "rb") as f:
                binary_data = f.read()  # `f.read()` always returns `bytes`
        elif isinstance(audio_file, tuple):
            # Handle tuple case
            _, file_content = audio_file[:2]
            if isinstance(file_content, str):
                with open(file_content, "rb") as f:
                    binary_data = f.read()  # `f.read()` always returns `bytes`
            elif isinstance(file_content, bytes):
                binary_data = file_content
            else:
                raise TypeError(
                    f"Unexpected type in tuple: {type(file_content)}. Expected str or bytes."
                )
        elif isinstance(audio_file, bytes):
            # Assume it's already binary data
            binary_data = audio_file
        elif isinstance(audio_file, io.BufferedReader) or isinstance(
            audio_file, io.BytesIO
        ):
            # Handle file-like objects
            binary_data = audio_file.read()

        else:
            raise TypeError(f"Unsupported type for audio_file: {type(audio_file)}")

        return binary_data

    def transform_audio_transcription_response(
        self,
        model: str,
        raw_response: Response,
        model_response: TranscriptionResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
    ) -> TranscriptionResponse:
        """
        Transforms the raw response from Deepgram to the TranscriptionResponse format
        """
        try:
            response_json = raw_response.json()

            # Get the first alternative from the first channel
            first_channel = response_json["results"]["channels"][0]
            first_alternative = first_channel["alternatives"][0]

            # Extract the full transcript
            text = first_alternative["transcript"]

            # Create TranscriptionResponse object
            response = TranscriptionResponse(text=text)

            # Add additional metadata matching OpenAI format
            response["task"] = "transcribe"
            response["language"] = (
                "english"  # Deepgram auto-detects but doesn't return language
            )
            response["duration"] = response_json["metadata"]["duration"]

            # Transform words to match OpenAI format
            if "words" in first_alternative:
                response["words"] = [
                    {"word": word["word"], "start": word["start"], "end": word["end"]}
                    for word in first_alternative["words"]
                ]

            # Store full response in hidden params
            response._hidden_params = response_json

            return response

        except Exception as e:
            raise ValueError(
                f"Error transforming Deepgram response: {str(e)}\nResponse: {raw_response.text}"
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
        if api_base is None:
            api_base = (
                get_secret_str("DEEPGRAM_API_BASE") or "https://api.deepgram.com/v1"
            )
        api_base = api_base.rstrip("/")  # Remove trailing slash if present

        # Build query parameters including the model
        all_query_params = {"model": model}

        # Add filtered optional parameters
        additional_params = self._build_query_params(optional_params, model)
        all_query_params.update(additional_params)

        # Construct URL with proper query string encoding
        base_url = f"{api_base}/listen"
        query_string = urlencode(all_query_params)
        url = f"{base_url}?{query_string}"

        return url

    def _should_exclude_param(
        self,
        param_name: str,
        model: str,
    ) -> bool:
        """
        Determines if a parameter should be excluded from the query string.

        Args:
            param_name: Parameter name
            model: Model name

        Returns:
            True if the parameter should be excluded
        """
        # Parameters that are handled elsewhere or not relevant to Deepgram API
        excluded_params = {
            "model",  # Already in the URL path
            "OPENAI_TRANSCRIPTION_PARAMS",  # Internal litellm parameter
        }

        # Skip if it's an excluded parameter
        if param_name in excluded_params:
            return True

        # Skip if it's an OpenAI-specific parameter that we handle separately
        if param_name in self.get_supported_openai_params(model):
            return True

        return False

    def _format_param_value(self, value) -> str:
        """
        Formats a parameter value for use in query string.

        Args:
            value: The parameter value to format

        Returns:
            Formatted string value
        """
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _build_query_params(self, optional_params: dict, model: str) -> dict:
        """
        Builds a dictionary of query parameters from optional_params.

        Args:
            optional_params: Dictionary of optional parameters
            model: Model name

        Returns:
            Dictionary of filtered and formatted query parameters
        """
        query_params = {}

        for key, value in optional_params.items():
            # Skip None values
            if value is None:
                continue

            # Skip excluded parameters
            if self._should_exclude_param(
                param_name=key,
                model=model,
            ):
                continue

            # Format and add the parameter
            formatted_value = self._format_param_value(value)
            query_params[key] = formatted_value

        return query_params

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
        api_key = api_key or get_secret_str("DEEPGRAM_API_KEY")
        return {
            "Authorization": f"Token {api_key}",
        }

# === NexusCore/openenv\Lib\site-packages\matplotlib\tri\_tricontour.py ===
import numpy as np

from matplotlib import _docstring
from matplotlib.contour import ContourSet
from matplotlib.tri._triangulation import Triangulation


@_docstring.interpd
class TriContourSet(ContourSet):
    """
    Create and store a set of contour lines or filled regions for
    a triangular grid.

    This class is typically not instantiated directly by the user but by
    `~.Axes.tricontour` and `~.Axes.tricontourf`.

    %(contour_set_attributes)s
    """
    def __init__(self, ax, *args, **kwargs):
        """
        Draw triangular grid contour lines or filled regions,
        depending on whether keyword arg *filled* is False
        (default) or True.

        The first argument of the initializer must be an `~.axes.Axes`
        object.  The remaining arguments and keyword arguments
        are described in the docstring of `~.Axes.tricontour`.
        """
        super().__init__(ax, *args, **kwargs)

    def _process_args(self, *args, **kwargs):
        """
        Process args and kwargs.
        """
        if isinstance(args[0], TriContourSet):
            C = args[0]._contour_generator
            if self.levels is None:
                self.levels = args[0].levels
            self.zmin = args[0].zmin
            self.zmax = args[0].zmax
            self._mins = args[0]._mins
            self._maxs = args[0]._maxs
        else:
            from matplotlib import _tri
            tri, z = self._contour_args(args, kwargs)
            C = _tri.TriContourGenerator(tri.get_cpp_triangulation(), z)
            self._mins = [tri.x.min(), tri.y.min()]
            self._maxs = [tri.x.max(), tri.y.max()]

        self._contour_generator = C
        return kwargs

    def _contour_args(self, args, kwargs):
        tri, args, kwargs = Triangulation.get_from_args_and_kwargs(*args,
                                                                   **kwargs)
        z, *args = args
        z = np.ma.asarray(z)
        if z.shape != tri.x.shape:
            raise ValueError('z array must have same length as triangulation x'
                             ' and y arrays')

        # z values must be finite, only need to check points that are included
        # in the triangulation.
        z_check = z[np.unique(tri.get_masked_triangles())]
        if np.ma.is_masked(z_check):
            raise ValueError('z must not contain masked points within the '
                             'triangulation')
        if not np.isfinite(z_check).all():
            raise ValueError('z array must not contain non-finite values '
                             'within the triangulation')

        z = np.ma.masked_invalid(z, copy=False)
        self.zmax = float(z_check.max())
        self.zmin = float(z_check.min())
        if self.logscale and self.zmin <= 0:
            func = 'contourf' if self.filled else 'contour'
            raise ValueError(f'Cannot {func} log of negative values.')
        self._process_contour_level_args(args, z.dtype)
        return (tri, z)


_docstring.interpd.register(_tricontour_doc="""
Draw contour %%(type)s on an unstructured triangular grid.

Call signatures::

    %%(func)s(triangulation, z, [levels], ...)
    %%(func)s(x, y, z, [levels], *, [triangles=triangles], [mask=mask], ...)

The triangular grid can be specified either by passing a `.Triangulation`
object as the first parameter, or by passing the points *x*, *y* and
optionally the *triangles* and a *mask*. See `.Triangulation` for an
explanation of these parameters. If neither of *triangulation* or
*triangles* are given, the triangulation is calculated on the fly.

It is possible to pass *triangles* positionally, i.e.
``%%(func)s(x, y, triangles, z, ...)``. However, this is discouraged. For more
clarity, pass *triangles* via keyword argument.

Parameters
----------
triangulation : `.Triangulation`, optional
    An already created triangular grid.

x, y, triangles, mask
    Parameters defining the triangular grid. See `.Triangulation`.
    This is mutually exclusive with specifying *triangulation*.

z : array-like
    The height values over which the contour is drawn.  Color-mapping is
    controlled by *cmap*, *norm*, *vmin*, and *vmax*.

    .. note::
        All values in *z* must be finite. Hence, nan and inf values must
        either be removed or `~.Triangulation.set_mask` be used.

levels : int or array-like, optional
    Determines the number and positions of the contour lines / regions.

    If an int *n*, use `~matplotlib.ticker.MaxNLocator`, which tries to
    automatically choose no more than *n+1* "nice" contour levels between
    between minimum and maximum numeric values of *Z*.

    If array-like, draw contour lines at the specified levels.  The values must
    be in increasing order.

Returns
-------
`~matplotlib.tri.TriContourSet`

Other Parameters
----------------
colors : :mpltype:`color` or list of :mpltype:`color`, optional
    The colors of the levels, i.e., the contour %%(type)s.

    The sequence is cycled for the levels in ascending order. If the sequence
    is shorter than the number of levels, it is repeated.

    As a shortcut, single color strings may be used in place of one-element
    lists, i.e. ``'red'`` instead of ``['red']`` to color all levels with the
    same color. This shortcut does only work for color strings, not for other
    ways of specifying colors.

    By default (value *None*), the colormap specified by *cmap* will be used.

alpha : float, default: 1
    The alpha blending value, between 0 (transparent) and 1 (opaque).

%(cmap_doc)s

    This parameter is ignored if *colors* is set.

%(norm_doc)s

    This parameter is ignored if *colors* is set.

%(vmin_vmax_doc)s

    If *vmin* or *vmax* are not given, the default color scaling is based on
    *levels*.

    This parameter is ignored if *colors* is set.

origin : {*None*, 'upper', 'lower', 'image'}, default: None
    Determines the orientation and exact position of *z* by specifying the
    position of ``z[0, 0]``.  This is only relevant, if *X*, *Y* are not given.

    - *None*: ``z[0, 0]`` is at X=0, Y=0 in the lower left corner.
    - 'lower': ``z[0, 0]`` is at X=0.5, Y=0.5 in the lower left corner.
    - 'upper': ``z[0, 0]`` is at X=N+0.5, Y=0.5 in the upper left corner.
    - 'image': Use the value from :rc:`image.origin`.

extent : (x0, x1, y0, y1), optional
    If *origin* is not *None*, then *extent* is interpreted as in `.imshow`: it
    gives the outer pixel boundaries. In this case, the position of z[0, 0] is
    the center of the pixel, not a corner. If *origin* is *None*, then
    (*x0*, *y0*) is the position of z[0, 0], and (*x1*, *y1*) is the position
    of z[-1, -1].

    This argument is ignored if *X* and *Y* are specified in the call to
    contour.

locator : ticker.Locator subclass, optional
    The locator is used to determine the contour levels if they are not given
    explicitly via *levels*.
    Defaults to `~.ticker.MaxNLocator`.

extend : {'neither', 'both', 'min', 'max'}, default: 'neither'
    Determines the ``%%(func)s``-coloring of values that are outside the
    *levels* range.

    If 'neither', values outside the *levels* range are not colored.  If 'min',
    'max' or 'both', color the values below, above or below and above the
    *levels* range.

    Values below ``min(levels)`` and above ``max(levels)`` are mapped to the
    under/over values of the `.Colormap`. Note that most colormaps do not have
    dedicated colors for these by default, so that the over and under values
    are the edge values of the colormap.  You may want to set these values
    explicitly using `.Colormap.set_under` and `.Colormap.set_over`.

    .. note::

        An existing `.TriContourSet` does not get notified if properties of its
        colormap are changed. Therefore, an explicit call to
        `.ContourSet.changed()` is needed after modifying the colormap. The
        explicit call can be left out, if a colorbar is assigned to the
        `.TriContourSet` because it internally calls `.ContourSet.changed()`.

xunits, yunits : registered units, optional
    Override axis units by specifying an instance of a
    :class:`matplotlib.units.ConversionInterface`.

antialiased : bool, optional
    Enable antialiasing, overriding the defaults.  For
    filled contours, the default is *True*.  For line contours,
    it is taken from :rc:`lines.antialiased`.""" % _docstring.interpd.params)


@_docstring.Substitution(func='tricontour', type='lines')
@_docstring.interpd
def tricontour(ax, *args, **kwargs):
    """
    %(_tricontour_doc)s

    linewidths : float or array-like, default: :rc:`contour.linewidth`
        The line width of the contour lines.

        If a number, all levels will be plotted with this linewidth.

        If a sequence, the levels in ascending order will be plotted with
        the linewidths in the order specified.

        If None, this falls back to :rc:`lines.linewidth`.

    linestyles : {*None*, 'solid', 'dashed', 'dashdot', 'dotted'}, optional
        If *linestyles* is *None*, the default is 'solid' unless the lines are
        monochrome.  In that case, negative contours will take their linestyle
        from :rc:`contour.negative_linestyle` setting.

        *linestyles* can also be an iterable of the above strings specifying a
        set of linestyles to be used. If this iterable is shorter than the
        number of contour levels it will be repeated as necessary.
    """
    kwargs['filled'] = False
    return TriContourSet(ax, *args, **kwargs)


@_docstring.Substitution(func='tricontourf', type='regions')
@_docstring.interpd
def tricontourf(ax, *args, **kwargs):
    """
    %(_tricontour_doc)s

    hatches : list[str], optional
        A list of crosshatch patterns to use on the filled areas.
        If None, no hatching will be added to the contour.

    Notes
    -----
    `.tricontourf` fills intervals that are closed at the top; that is, for
    boundaries *z1* and *z2*, the filled region is::

        z1 < Z <= z2

    except for the lowest interval, which is closed on both sides (i.e. it
    includes the lowest value).
    """
    kwargs['filled'] = True
    return TriContourSet(ax, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\nltk\twitter\common.py ===
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions for the `twitterclient` module which do not require
the `twython` library to have been installed.
"""
import csv
import gzip
import json

from nltk.internals import deprecated

HIER_SEPARATOR = "."


def extract_fields(tweet, fields):
    """
    Extract field values from a full tweet and return them as a list

    :param json tweet: The tweet in JSON format
    :param list fields: The fields to be extracted from the tweet
    :rtype: list(str)
    """
    out = []
    for field in fields:
        try:
            _add_field_to_out(tweet, field, out)
        except TypeError as e:
            raise RuntimeError(
                "Fatal error when extracting fields. Cannot find field ", field
            ) from e
    return out


def _add_field_to_out(json, field, out):
    if _is_composed_key(field):
        key, value = _get_key_value_composed(field)
        _add_field_to_out(json[key], value, out)
    else:
        out += [json[field]]


def _is_composed_key(field):
    return HIER_SEPARATOR in field


def _get_key_value_composed(field):
    out = field.split(HIER_SEPARATOR)
    # there could be up to 3 levels
    key = out[0]
    value = HIER_SEPARATOR.join(out[1:])
    return key, value


def _get_entity_recursive(json, entity):
    if not json:
        return None
    elif isinstance(json, dict):
        for key, value in json.items():
            if key == entity:
                return value
            # 'entities' and 'extended_entities' are wrappers in Twitter json
            # structure that contain other Twitter objects. See:
            # https://dev.twitter.com/overview/api/entities-in-twitter-objects

            if key == "entities" or key == "extended_entities":
                candidate = _get_entity_recursive(value, entity)
                if candidate is not None:
                    return candidate
        return None
    elif isinstance(json, list):
        for item in json:
            candidate = _get_entity_recursive(item, entity)
            if candidate is not None:
                return candidate
        return None
    else:
        return None


def json2csv(
    fp, outfile, fields, encoding="utf8", errors="replace", gzip_compress=False
):
    """
    Extract selected fields from a file of line-separated JSON tweets and
    write to a file in CSV format.

    This utility function allows a file of full tweets to be easily converted
    to a CSV file for easier processing. For example, just TweetIDs or
    just the text content of the Tweets can be extracted.

    Additionally, the function allows combinations of fields of other Twitter
    objects (mainly the users, see below).

    For Twitter entities (e.g. hashtags of a Tweet), and for geolocation, see
    `json2csv_entities`

    :param str infile: The name of the file containing full tweets

    :param str outfile: The name of the text file where results should be\
    written

    :param list fields: The list of fields to be extracted. Useful examples\
    are 'id_str' for the tweetID and 'text' for the text of the tweet. See\
    <https://dev.twitter.com/overview/api/tweets> for a full list of fields.\
    e. g.: ['id_str'], ['id', 'text', 'favorite_count', 'retweet_count']\
    Additionally, it allows IDs from other Twitter objects, e. g.,\
    ['id', 'text', 'user.id', 'user.followers_count', 'user.friends_count']

    :param error: Behaviour for encoding errors, see\
    https://docs.python.org/3/library/codecs.html#codec-base-classes

    :param gzip_compress: if `True`, output files are compressed with gzip
    """
    (writer, outf) = _outf_writer(outfile, encoding, errors, gzip_compress)
    # write the list of fields as header
    writer.writerow(fields)
    # process the file
    for line in fp:
        tweet = json.loads(line)
        row = extract_fields(tweet, fields)
        writer.writerow(row)
    outf.close()


@deprecated("Use open() and csv.writer() directly instead.")
def outf_writer_compat(outfile, encoding, errors, gzip_compress=False):
    """Get a CSV writer with optional compression."""
    return _outf_writer(outfile, encoding, errors, gzip_compress)


def _outf_writer(outfile, encoding, errors, gzip_compress=False):
    if gzip_compress:
        outf = gzip.open(outfile, "wt", newline="", encoding=encoding, errors=errors)
    else:
        outf = open(outfile, "w", newline="", encoding=encoding, errors=errors)
    writer = csv.writer(outf)
    return (writer, outf)


def json2csv_entities(
    tweets_file,
    outfile,
    main_fields,
    entity_type,
    entity_fields,
    encoding="utf8",
    errors="replace",
    gzip_compress=False,
):
    """
    Extract selected fields from a file of line-separated JSON tweets and
    write to a file in CSV format.

    This utility function allows a file of full Tweets to be easily converted
    to a CSV file for easier processing of Twitter entities. For example, the
    hashtags or media elements of a tweet can be extracted.

    It returns one line per entity of a Tweet, e.g. if a tweet has two hashtags
    there will be two lines in the output file, one per hashtag

    :param tweets_file: the file-like object containing full Tweets

    :param str outfile: The path of the text file where results should be\
        written

    :param list main_fields: The list of fields to be extracted from the main\
        object, usually the tweet. Useful examples: 'id_str' for the tweetID. See\
        <https://dev.twitter.com/overview/api/tweets> for a full list of fields.
        e. g.: ['id_str'], ['id', 'text', 'favorite_count', 'retweet_count']
        If `entity_type` is expressed with hierarchy, then it is the list of\
        fields of the object that corresponds to the key of the entity_type,\
        (e.g., for entity_type='user.urls', the fields in the main_fields list\
        belong to the user object; for entity_type='place.bounding_box', the\
        files in the main_field list belong to the place object of the tweet).

    :param list entity_type: The name of the entity: 'hashtags', 'media',\
        'urls' and 'user_mentions' for the tweet object. For a user object,\
        this needs to be expressed with a hierarchy: `'user.urls'`. For the\
        bounding box of the Tweet location, use `'place.bounding_box'`.

    :param list entity_fields: The list of fields to be extracted from the\
        entity. E.g. `['text']` (of the Tweet)

    :param error: Behaviour for encoding errors, see\
        https://docs.python.org/3/library/codecs.html#codec-base-classes

    :param gzip_compress: if `True`, output files are compressed with gzip
    """

    (writer, outf) = _outf_writer(outfile, encoding, errors, gzip_compress)
    header = get_header_field_list(main_fields, entity_type, entity_fields)
    writer.writerow(header)
    for line in tweets_file:
        tweet = json.loads(line)
        if _is_composed_key(entity_type):
            key, value = _get_key_value_composed(entity_type)
            object_json = _get_entity_recursive(tweet, key)
            if not object_json:
                # this can happen in the case of "place"
                continue
            object_fields = extract_fields(object_json, main_fields)
            items = _get_entity_recursive(object_json, value)
            _write_to_file(object_fields, items, entity_fields, writer)
        else:
            tweet_fields = extract_fields(tweet, main_fields)
            items = _get_entity_recursive(tweet, entity_type)
            _write_to_file(tweet_fields, items, entity_fields, writer)
    outf.close()


def get_header_field_list(main_fields, entity_type, entity_fields):
    if _is_composed_key(entity_type):
        key, value = _get_key_value_composed(entity_type)
        main_entity = key
        sub_entity = value
    else:
        main_entity = None
        sub_entity = entity_type

    if main_entity:
        output1 = [HIER_SEPARATOR.join([main_entity, x]) for x in main_fields]
    else:
        output1 = main_fields
    output2 = [HIER_SEPARATOR.join([sub_entity, x]) for x in entity_fields]
    return output1 + output2


def _write_to_file(object_fields, items, entity_fields, writer):
    if not items:
        # it could be that the entity is just not present for the tweet
        # e.g. tweet hashtag is always present, even as [], however
        # tweet media may not be present
        return
    if isinstance(items, dict):
        # this happens e.g. for "place" of a tweet
        row = object_fields
        # there might be composed keys in de list of required fields
        entity_field_values = [x for x in entity_fields if not _is_composed_key(x)]
        entity_field_composed = [x for x in entity_fields if _is_composed_key(x)]
        for field in entity_field_values:
            value = items[field]
            if isinstance(value, list):
                row += value
            else:
                row += [value]
        # now check required dictionaries
        for d in entity_field_composed:
            kd, vd = _get_key_value_composed(d)
            json_dict = items[kd]
            if not isinstance(json_dict, dict):
                raise RuntimeError(
                    """Key {} does not contain a dictionary
                in the json file""".format(
                        kd
                    )
                )
            row += [json_dict[vd]]
        writer.writerow(row)
        return
    # in general it is a list
    for item in items:
        row = object_fields + extract_fields(item, entity_fields)
        writer.writerow(row)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\tnt.py ===
"""
    pygments.lexers.tnt
    ~~~~~~~~~~~~~~~~~~~

    Lexer for Typographic Number Theory.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer
from pygments.token import Text, Comment, Operator, Keyword, Name, Number, \
    Punctuation, Error

__all__ = ['TNTLexer']


class TNTLexer(Lexer):
    """
    Lexer for Typographic Number Theory, as described in the book
    Gödel, Escher, Bach, by Douglas R. Hofstadter
    """

    name = 'Typographic Number Theory'
    url = 'https://github.com/Kenny2github/language-tnt'
    aliases = ['tnt']
    filenames = ['*.tnt']
    version_added = '2.7'

    cur = []

    LOGIC = set('⊃→]&∧^|∨Vv')
    OPERATORS = set('+.⋅*')
    VARIABLES = set('abcde')
    PRIMES = set("'′")
    NEGATORS = set('~!')
    QUANTIFIERS = set('AE∀∃')
    NUMBERS = set('0123456789')
    WHITESPACE = set('\t \v\n')

    RULES = re.compile('''(?xi)
        joining | separation | double-tilde | fantasy\\ rule
        | carry[- ]over(?:\\ of)?(?:\\ line)?\\ ([0-9]+) | detachment
        | contrapositive | De\\ Morgan | switcheroo
        | specification | generalization | interchange
        | existence | symmetry | transitivity
        | add\\ S | drop\\ S | induction
        | axiom\\ ([1-5]) | premise | push | pop
    ''')
    LINENOS = re.compile(r'(?:[0-9]+)(?:(?:, ?|,? and )(?:[0-9]+))*')
    COMMENT = re.compile(r'\[[^\n\]]+\]')

    def __init__(self, *args, **kwargs):
        Lexer.__init__(self, *args, **kwargs)
        self.cur = []

    def whitespace(self, start, text, required=False):
        """Tokenize whitespace."""
        end = start
        try:
            while text[end] in self.WHITESPACE:
                end += 1
        except IndexError:
            end = len(text)
        if required and end == start:
            raise AssertionError
        if end != start:
            self.cur.append((start, Text, text[start:end]))
        return end

    def variable(self, start, text):
        """Tokenize a variable."""
        if text[start] not in self.VARIABLES:
            raise AssertionError
        end = start+1
        while text[end] in self.PRIMES:
            end += 1
        self.cur.append((start, Name.Variable, text[start:end]))
        return end

    def term(self, start, text):
        """Tokenize a term."""
        if text[start] == 'S':  # S...S(...) or S...0
            end = start+1
            while text[end] == 'S':
                end += 1
            self.cur.append((start, Number.Integer, text[start:end]))
            return self.term(end, text)
        if text[start] == '0':  # the singleton 0
            self.cur.append((start, Number.Integer, text[start]))
            return start+1
        if text[start] in self.VARIABLES:  # a''...
            return self.variable(start, text)
        if text[start] == '(':  # (...+...)
            self.cur.append((start, Punctuation, text[start]))
            start = self.term(start+1, text)
            if text[start] not in self.OPERATORS:
                raise AssertionError
            self.cur.append((start, Operator, text[start]))
            start = self.term(start+1, text)
            if text[start] != ')':
                raise AssertionError
            self.cur.append((start, Punctuation, text[start]))
            return start+1
        raise AssertionError  # no matches

    def formula(self, start, text):
        """Tokenize a formula."""
        if text[start] in self.NEGATORS:  # ~<...>
            end = start+1
            while text[end] in self.NEGATORS:
                end += 1
            self.cur.append((start, Operator, text[start:end]))
            return self.formula(end, text)
        if text[start] in self.QUANTIFIERS:  # Aa:<...>
            self.cur.append((start, Keyword.Declaration, text[start]))
            start = self.variable(start+1, text)
            if text[start] != ':':
                raise AssertionError
            self.cur.append((start, Punctuation, text[start]))
            return self.formula(start+1, text)
        if text[start] == '<':  # <...&...>
            self.cur.append((start, Punctuation, text[start]))
            start = self.formula(start+1, text)
            if text[start] not in self.LOGIC:
                raise AssertionError
            self.cur.append((start, Operator, text[start]))
            start = self.formula(start+1, text)
            if text[start] != '>':
                raise AssertionError
            self.cur.append((start, Punctuation, text[start]))
            return start+1
        # ...=...
        start = self.term(start, text)
        if text[start] != '=':
            raise AssertionError
        self.cur.append((start, Operator, text[start]))
        start = self.term(start+1, text)
        return start

    def rule(self, start, text):
        """Tokenize a rule."""
        match = self.RULES.match(text, start)
        if match is None:
            raise AssertionError
        groups = sorted(match.regs[1:])  # exclude whole match
        for group in groups:
            if group[0] >= 0:  # this group matched
                self.cur.append((start, Keyword, text[start:group[0]]))
                self.cur.append((group[0], Number.Integer,
                                 text[group[0]:group[1]]))
                if group[1] != match.end():
                    self.cur.append((group[1], Keyword,
                                     text[group[1]:match.end()]))
                break
        else:
            self.cur.append((start, Keyword, text[start:match.end()]))
        return match.end()

    def lineno(self, start, text):
        """Tokenize a line referral."""
        end = start
        while text[end] not in self.NUMBERS:
            end += 1
        self.cur.append((start, Punctuation, text[start]))
        self.cur.append((start+1, Text, text[start+1:end]))
        start = end
        match = self.LINENOS.match(text, start)
        if match is None:
            raise AssertionError
        if text[match.end()] != ')':
            raise AssertionError
        self.cur.append((match.start(), Number.Integer, match.group(0)))
        self.cur.append((match.end(), Punctuation, text[match.end()]))
        return match.end() + 1

    def error_till_line_end(self, start, text):
        """Mark everything from ``start`` to the end of the line as Error."""
        end = start
        try:
            while text[end] != '\n':  # there's whitespace in rules
                end += 1
        except IndexError:
            end = len(text)
        if end != start:
            self.cur.append((start, Error, text[start:end]))
        end = self.whitespace(end, text)
        return end

    def get_tokens_unprocessed(self, text):
        """Returns a list of TNT tokens."""
        self.cur = []
        start = end = self.whitespace(0, text)
        while start <= end < len(text):
            try:
                # try line number
                while text[end] in self.NUMBERS:
                    end += 1
                if end != start:  # actual number present
                    self.cur.append((start, Number.Integer, text[start:end]))
                    # whitespace is required after a line number
                    orig = len(self.cur)
                    try:
                        start = end = self.whitespace(end, text, True)
                    except AssertionError:
                        del self.cur[orig:]
                        start = end = self.error_till_line_end(end, text)
                        continue
                # at this point it could be a comment
                match = self.COMMENT.match(text, start)
                if match is not None:
                    self.cur.append((start, Comment, text[start:match.end()]))
                    start = end = match.end()
                    # anything after the closing bracket is invalid
                    start = end = self.error_till_line_end(start, text)
                    # do not attempt to process the rest
                    continue
                del match
                if text[start] in '[]':  # fantasy push or pop
                    self.cur.append((start, Keyword, text[start]))
                    start += 1
                    end += 1
                else:
                    # one formula, possibly containing subformulae
                    orig = len(self.cur)
                    try:
                        start = end = self.formula(start, text)
                    except (AssertionError, RecursionError):  # not well-formed
                        del self.cur[orig:]
                        while text[end] not in self.WHITESPACE:
                            end += 1
                        self.cur.append((start, Error, text[start:end]))
                        start = end
                # skip whitespace after formula
                orig = len(self.cur)
                try:
                    start = end = self.whitespace(end, text, True)
                except AssertionError:
                    del self.cur[orig:]
                    start = end = self.error_till_line_end(start, text)
                    continue
                # rule proving this formula a theorem
                orig = len(self.cur)
                try:
                    start = end = self.rule(start, text)
                except AssertionError:
                    del self.cur[orig:]
                    start = end = self.error_till_line_end(start, text)
                    continue
                # skip whitespace after rule
                start = end = self.whitespace(end, text)
                # line marker
                if text[start] == '(':
                    orig = len(self.cur)
                    try:
                        start = end = self.lineno(start, text)
                    except AssertionError:
                        del self.cur[orig:]
                        start = end = self.error_till_line_end(start, text)
                        continue
                    start = end = self.whitespace(start, text)
            except IndexError:
                try:
                    del self.cur[orig:]
                except NameError:
                    pass  # if orig was never defined, fine
                self.error_till_line_end(start, text)
        return self.cur

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\unix.py ===
"""Unix."""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Iterator, NoReturn

from .api import PlatformDirsABC

if sys.platform == "win32":

    def getuid() -> NoReturn:
        msg = "should only be used on Unix"
        raise RuntimeError(msg)

else:
    from os import getuid


class Unix(PlatformDirsABC):  # noqa: PLR0904
    """
    On Unix/Linux, we follow the `XDG Basedir Spec <https://specifications.freedesktop.org/basedir-spec/basedir-spec-
    latest.html>`_.

    The spec allows overriding directories with environment variables. The examples shown are the default values,
    alongside the name of the environment variable that overrides them. Makes use of the `appname
    <platformdirs.api.PlatformDirsABC.appname>`, `version <platformdirs.api.PlatformDirsABC.version>`, `multipath
    <platformdirs.api.PlatformDirsABC.multipath>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g. ``~/.local/share/$appname/$version`` or
         ``$XDG_DATA_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_DATA_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/share")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_data_dirs(self) -> list[str]:
        path = os.environ.get("XDG_DATA_DIRS", "")
        if not path.strip():
            path = f"/usr/local/share{os.pathsep}/usr/share"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>` is
         enabled and ``XDG_DATA_DIRS`` is set and a multi path the response is also a multi path separated by the
         OS path separator), e.g. ``/usr/local/share/$appname/$version`` or ``/usr/share/$appname/$version``
        """
        # XDG default for $XDG_DATA_DIRS; only first, if multipath is False
        dirs = self._site_data_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. ``~/.config/$appname/$version`` or
         ``$XDG_CONFIG_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CONFIG_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.config")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_config_dirs(self) -> list[str]:
        path = os.environ.get("XDG_CONFIG_DIRS", "")
        if not path.strip():
            path = "/etc/xdg"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_config_dir(self) -> str:
        """
        :return: config directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>`
         is enabled and ``XDG_CONFIG_DIRS`` is set and a multi path the response is also a multi path separated by
         the OS path separator), e.g. ``/etc/xdg/$appname/$version``
        """
        # XDG default for $XDG_CONFIG_DIRS only first, if multipath is False
        dirs = self._site_config_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user, e.g. ``~/.cache/$appname/$version`` or
         ``~/$XDG_CACHE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CACHE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.cache")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``/var/cache/$appname/$version``"""
        return self._append_app_name_and_version("/var/cache")

    @property
    def user_state_dir(self) -> str:
        """
        :return: state directory tied to the user, e.g. ``~/.local/state/$appname/$version`` or
         ``$XDG_STATE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_STATE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/state")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_state_dir` if not opinionated else ``log`` in it"""
        path = self.user_state_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return _get_user_media_dir("XDG_DOCUMENTS_DIR", "~/Documents")

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return _get_user_media_dir("XDG_DOWNLOAD_DIR", "~/Downloads")

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return _get_user_media_dir("XDG_PICTURES_DIR", "~/Pictures")

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Videos``"""
        return _get_user_media_dir("XDG_VIDEOS_DIR", "~/Videos")

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return _get_user_media_dir("XDG_MUSIC_DIR", "~/Music")

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return _get_user_media_dir("XDG_DESKTOP_DIR", "~/Desktop")

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g. ``/run/user/$(id -u)/$appname/$version`` or
         ``$XDG_RUNTIME_DIR/$appname/$version``.

         For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/user/$(id -u)/$appname/$version`` if
         exists, otherwise ``/tmp/runtime-$(id -u)/$appname/$version``, if``$XDG_RUNTIME_DIR``
         is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = f"/var/run/user/{getuid()}"
                if not Path(path).exists():
                    path = f"/tmp/runtime-{getuid()}"  # noqa: S108
            else:
                path = f"/run/user/{getuid()}"
        return self._append_app_name_and_version(path)

    @property
    def site_runtime_dir(self) -> str:
        """
        :return: runtime directory shared by users, e.g. ``/run/$appname/$version`` or \
        ``$XDG_RUNTIME_DIR/$appname/$version``.

        Note that this behaves almost exactly like `user_runtime_dir` if ``$XDG_RUNTIME_DIR`` is set, but will
        fall back to paths associated to the root user instead of a regular logged-in user if it's not set.

        If you wish to ensure that a logged-in root user path is returned e.g. ``/run/user/0``, use `user_runtime_dir`
        instead.

        For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/$appname/$version`` if ``$XDG_RUNTIME_DIR`` is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = "/var/run"
            else:
                path = "/run"
        return self._append_app_name_and_version(path)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users, returns the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_config_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield from self._site_config_dirs

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield from self._site_data_dirs


def _get_user_media_dir(env_var: str, fallback_tilde_path: str) -> str:
    media_dir = _get_user_dirs_folder(env_var)
    if media_dir is None:
        media_dir = os.environ.get(env_var, "").strip()
        if not media_dir:
            media_dir = os.path.expanduser(fallback_tilde_path)  # noqa: PTH111

    return media_dir


def _get_user_dirs_folder(key: str) -> str | None:
    """
    Return directory from user-dirs.dirs config file.

    See https://freedesktop.org/wiki/Software/xdg-user-dirs/.

    """
    user_dirs_config_path = Path(Unix().user_config_dir) / "user-dirs.dirs"
    if user_dirs_config_path.exists():
        parser = ConfigParser()

        with user_dirs_config_path.open() as stream:
            # Add fake section header, so ConfigParser doesn't complain
            parser.read_string(f"[top]\n{stream.read()}")

        if key not in parser["top"]:
            return None

        path = parser["top"][key].strip('"')
        # Handle relative home paths
        return path.replace("$HOME", os.path.expanduser("~"))  # noqa: PTH111

    return None


__all__ = [
    "Unix",
]

# === NexusCore/openenv\Lib\site-packages\matplotlib\inset.py ===
"""
The inset module defines the InsetIndicator class, which draws the rectangle and
connectors required for `.Axes.indicate_inset` and `.Axes.indicate_inset_zoom`.
"""

from . import _api, artist, transforms
from matplotlib.patches import ConnectionPatch, PathPatch, Rectangle
from matplotlib.path import Path


_shared_properties = ('alpha', 'edgecolor', 'linestyle', 'linewidth')


class InsetIndicator(artist.Artist):
    """
    An artist to highlight an area of interest.

    An inset indicator is a rectangle on the plot at the position indicated by
    *bounds* that optionally has lines that connect the rectangle to an inset
    Axes (`.Axes.inset_axes`).

    .. versionadded:: 3.10
    """
    zorder = 4.99

    def __init__(self, bounds=None, inset_ax=None, zorder=None, **kwargs):
        """
        Parameters
        ----------
        bounds : [x0, y0, width, height], optional
            Lower-left corner of rectangle to be marked, and its width
            and height.  If not set, the bounds will be calculated from the
            data limits of inset_ax, which must be supplied.

        inset_ax : `~.axes.Axes`, optional
            An optional inset Axes to draw connecting lines to.  Two lines are
            drawn connecting the indicator box to the inset Axes on corners
            chosen so as to not overlap with the indicator box.

        zorder : float, default: 4.99
            Drawing order of the rectangle and connector lines.  The default,
            4.99, is just below the default level of inset Axes.

        **kwargs
            Other keyword arguments are passed on to the `.Rectangle` patch.
        """
        if bounds is None and inset_ax is None:
            raise ValueError("At least one of bounds or inset_ax must be supplied")

        self._inset_ax = inset_ax

        if bounds is None:
            # Work out bounds from inset_ax
            self._auto_update_bounds = True
            bounds = self._bounds_from_inset_ax()
        else:
            self._auto_update_bounds = False

        x, y, width, height = bounds

        self._rectangle = Rectangle((x, y), width, height, clip_on=False, **kwargs)

        # Connector positions cannot be calculated till the artist has been added
        # to an axes, so just make an empty list for now.
        self._connectors = []

        super().__init__()
        self.set_zorder(zorder)

        # Initial style properties for the artist should match the rectangle.
        for prop in _shared_properties:
            setattr(self, f'_{prop}', artist.getp(self._rectangle, prop))

    def _shared_setter(self, prop, val):
        """
        Helper function to set the same style property on the artist and its children.
        """
        setattr(self, f'_{prop}', val)

        artist.setp([self._rectangle, *self._connectors], prop, val)

    def set_alpha(self, alpha):
        # docstring inherited
        self._shared_setter('alpha', alpha)

    def set_edgecolor(self, color):
        """
        Set the edge color of the rectangle and the connectors.

        Parameters
        ----------
        color : :mpltype:`color` or None
        """
        self._shared_setter('edgecolor', color)

    def set_color(self, c):
        """
        Set the edgecolor of the rectangle and the connectors, and the
        facecolor for the rectangle.

        Parameters
        ----------
        c : :mpltype:`color`
        """
        self._shared_setter('edgecolor', c)
        self._shared_setter('facecolor', c)

    def set_linewidth(self, w):
        """
        Set the linewidth in points of the rectangle and the connectors.

        Parameters
        ----------
        w : float or None
        """
        self._shared_setter('linewidth', w)

    def set_linestyle(self, ls):
        """
        Set the linestyle of the rectangle and the connectors.

        ==========================================  =================
        linestyle                                   description
        ==========================================  =================
        ``'-'`` or ``'solid'``                      solid line
        ``'--'`` or ``'dashed'``                    dashed line
        ``'-.'`` or ``'dashdot'``                   dash-dotted line
        ``':'`` or ``'dotted'``                     dotted line
        ``'none'``, ``'None'``, ``' '``, or ``''``  draw nothing
        ==========================================  =================

        Alternatively a dash tuple of the following form can be provided::

            (offset, onoffseq)

        where ``onoffseq`` is an even length tuple of on and off ink in points.

        Parameters
        ----------
        ls : {'-', '--', '-.', ':', '', (offset, on-off-seq), ...}
            The line style.
        """
        self._shared_setter('linestyle', ls)

    def _bounds_from_inset_ax(self):
        xlim = self._inset_ax.get_xlim()
        ylim = self._inset_ax.get_ylim()
        return (xlim[0], ylim[0], xlim[1] - xlim[0], ylim[1] - ylim[0])

    def _update_connectors(self):
        (x, y) = self._rectangle.get_xy()
        width = self._rectangle.get_width()
        height = self._rectangle.get_height()

        existing_connectors = self._connectors or [None] * 4

        # connect the inset_axes to the rectangle
        for xy_inset_ax, existing in zip([(0, 0), (0, 1), (1, 0), (1, 1)],
                                         existing_connectors):
            # inset_ax positions are in axes coordinates
            # The 0, 1 values define the four edges if the inset_ax
            # lower_left, upper_left, lower_right upper_right.
            ex, ey = xy_inset_ax
            if self.axes.xaxis.get_inverted():
                ex = 1 - ex
            if self.axes.yaxis.get_inverted():
                ey = 1 - ey
            xy_data = x + ex * width, y + ey * height
            if existing is None:
                # Create new connection patch with styles inherited from the
                # parent artist.
                p = ConnectionPatch(
                    xyA=xy_inset_ax, coordsA=self._inset_ax.transAxes,
                    xyB=xy_data, coordsB=self.axes.transData,
                    arrowstyle="-",
                    edgecolor=self._edgecolor, alpha=self.get_alpha(),
                    linestyle=self._linestyle, linewidth=self._linewidth)
                self._connectors.append(p)
            else:
                # Only update positioning of existing connection patch.  We
                # do not want to override any style settings made by the user.
                existing.xy1 = xy_inset_ax
                existing.xy2 = xy_data
                existing.coords1 = self._inset_ax.transAxes
                existing.coords2 = self.axes.transData

        if existing is None:
            # decide which two of the lines to keep visible....
            pos = self._inset_ax.get_position()
            bboxins = pos.transformed(self.get_figure(root=False).transSubfigure)
            rectbbox = transforms.Bbox.from_bounds(x, y, width, height).transformed(
                self._rectangle.get_transform())
            x0 = rectbbox.x0 < bboxins.x0
            x1 = rectbbox.x1 < bboxins.x1
            y0 = rectbbox.y0 < bboxins.y0
            y1 = rectbbox.y1 < bboxins.y1
            self._connectors[0].set_visible(x0 ^ y0)
            self._connectors[1].set_visible(x0 == y1)
            self._connectors[2].set_visible(x1 == y0)
            self._connectors[3].set_visible(x1 ^ y1)

    @property
    def rectangle(self):
        """`.Rectangle`: the indicator frame."""
        return self._rectangle

    @property
    def connectors(self):
        """
        4-tuple of `.patches.ConnectionPatch` or None
            The four connector lines connecting to (lower_left, upper_left,
            lower_right upper_right) corners of *inset_ax*. Two lines are
            set with visibility to *False*,  but the user can set the
            visibility to True if the automatic choice is not deemed correct.
        """
        if self._inset_ax is None:
            return

        if self._auto_update_bounds:
            self._rectangle.set_bounds(self._bounds_from_inset_ax())
        self._update_connectors()
        return tuple(self._connectors)

    def draw(self, renderer):
        # docstring inherited
        conn_same_style = []

        # Figure out which connectors have the same style as the box, so should
        # be drawn as a single path.
        for conn in self.connectors or []:
            if conn.get_visible():
                drawn = False
                for s in _shared_properties:
                    if artist.getp(self._rectangle, s) != artist.getp(conn, s):
                        # Draw this connector by itself
                        conn.draw(renderer)
                        drawn = True
                        break

                if not drawn:
                    # Connector has same style as box.
                    conn_same_style.append(conn)

        if conn_same_style:
            # Since at least one connector has the same style as the rectangle, draw
            # them as a compound path.
            artists = [self._rectangle] + conn_same_style
            paths = [a.get_transform().transform_path(a.get_path()) for a in artists]
            path = Path.make_compound_path(*paths)

            # Create a temporary patch to draw the path.
            p = PathPatch(path)
            p.update_from(self._rectangle)
            p.set_transform(transforms.IdentityTransform())
            p.draw(renderer)

            return

        # Just draw the rectangle
        self._rectangle.draw(renderer)

    @_api.deprecated(
        '3.10',
        message=('Since Matplotlib 3.10 indicate_inset_[zoom] returns a single '
                 'InsetIndicator artist with a rectangle property and a connectors '
                 'property.  From 3.12 it will no longer be possible to unpack the '
                 'return value into two elements.'))
    def __getitem__(self, key):
        return [self._rectangle, self.connectors][key]

# === NexusCore/openenv\Lib\site-packages\jedi\plugins\pytest.py ===
import sys
from typing import List
from pathlib import Path

from parso.tree import search_ancestor
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.imports import goto_import, load_module_from_path
from jedi.inference.filters import ParserTreeFilter
from jedi.inference.base_value import NO_VALUES, ValueSet
from jedi.inference.helpers import infer_call_of_leaf

_PYTEST_FIXTURE_MODULES = [
    ('_pytest', 'monkeypatch'),
    ('_pytest', 'capture'),
    ('_pytest', 'logging'),
    ('_pytest', 'tmpdir'),
    ('_pytest', 'pytester'),
]


def execute(callback):
    def wrapper(value, arguments):
        # This might not be necessary anymore in pytest 4/5, definitely needed
        # for pytest 3.
        if value.py__name__() == 'fixture' \
                and value.parent_context.py__name__() == '_pytest.fixtures':
            return NO_VALUES

        return callback(value, arguments)
    return wrapper


def infer_anonymous_param(func):
    def get_returns(value):
        if value.tree_node.annotation is not None:
            result = value.execute_with_values()
            if any(v.name.get_qualified_names(include_module_names=True)
                   == ('typing', 'Generator')
                   for v in result):
                return ValueSet.from_sets(
                    v.py__getattribute__('__next__').execute_annotation()
                    for v in result
                )
            return result

        # In pytest we need to differentiate between generators and normal
        # returns.
        # Parameters still need to be anonymous, .as_context() ensures that.
        function_context = value.as_context()
        if function_context.is_generator():
            return function_context.merge_yield_values()
        else:
            return function_context.get_return_values()

    def wrapper(param_name):
        # parameters with an annotation do not need special handling
        if param_name.annotation_node:
            return func(param_name)
        is_pytest_param, param_name_is_function_name = \
            _is_a_pytest_param_and_inherited(param_name)
        if is_pytest_param:
            module = param_name.get_root_context()
            fixtures = _goto_pytest_fixture(
                module,
                param_name.string_name,
                # This skips the current module, because we are basically
                # inheriting a fixture from somewhere else.
                skip_own_module=param_name_is_function_name,
            )
            if fixtures:
                return ValueSet.from_sets(
                    get_returns(value)
                    for fixture in fixtures
                    for value in fixture.infer()
                )
        return func(param_name)
    return wrapper


def goto_anonymous_param(func):
    def wrapper(param_name):
        is_pytest_param, param_name_is_function_name = \
            _is_a_pytest_param_and_inherited(param_name)
        if is_pytest_param:
            names = _goto_pytest_fixture(
                param_name.get_root_context(),
                param_name.string_name,
                skip_own_module=param_name_is_function_name,
            )
            if names:
                return names
        return func(param_name)
    return wrapper


def complete_param_names(func):
    def wrapper(context, func_name, decorator_nodes):
        module_context = context.get_root_context()
        if _is_pytest_func(func_name, decorator_nodes):
            names = []
            for module_context in _iter_pytest_modules(module_context):
                names += FixtureFilter(module_context).values()
            if names:
                return names
        return func(context, func_name, decorator_nodes)
    return wrapper


def _goto_pytest_fixture(module_context, name, skip_own_module):
    for module_context in _iter_pytest_modules(module_context, skip_own_module=skip_own_module):
        names = FixtureFilter(module_context).get(name)
        if names:
            return names


def _is_a_pytest_param_and_inherited(param_name):
    """
    Pytest params are either in a `test_*` function or have a pytest fixture
    with the decorator @pytest.fixture.

    This is a heuristic and will work in most cases.
    """
    funcdef = search_ancestor(param_name.tree_name, 'funcdef')
    if funcdef is None:  # A lambda
        return False, False
    decorators = funcdef.get_decorators()
    return _is_pytest_func(funcdef.name.value, decorators), \
        funcdef.name.value == param_name.string_name


def _is_pytest_func(func_name, decorator_nodes):
    return func_name.startswith('test') \
        or any('fixture' in n.get_code() for n in decorator_nodes)


def _find_pytest_plugin_modules() -> List[List[str]]:
    """
    Finds pytest plugin modules hooked by setuptools entry points

    See https://docs.pytest.org/en/stable/how-to/writing_plugins.html#setuptools-entry-points
    """
    if sys.version_info >= (3, 8):
        from importlib.metadata import entry_points

        if sys.version_info >= (3, 10):
            pytest_entry_points = entry_points(group="pytest11")
        else:
            pytest_entry_points = entry_points().get("pytest11", ())

        if sys.version_info >= (3, 9):
            return [ep.module.split(".") for ep in pytest_entry_points]
        else:
            # Python 3.8 doesn't have `EntryPoint.module`. Implement equivalent
            # to what Python 3.9 does (with additional None check to placate `mypy`)
            matches = [
                ep.pattern.match(ep.value)
                for ep in pytest_entry_points
            ]
            return [x.group('module').split(".") for x in matches if x]

    else:
        from pkg_resources import iter_entry_points
        return [ep.module_name.split(".") for ep in iter_entry_points(group="pytest11")]


@inference_state_method_cache()
def _iter_pytest_modules(module_context, skip_own_module=False):
    if not skip_own_module:
        yield module_context

    file_io = module_context.get_value().file_io
    if file_io is not None:
        folder = file_io.get_parent_folder()
        sys_path = module_context.inference_state.get_sys_path()

        # prevent an infinite loop when reaching the root of the current drive
        last_folder = None

        while any(folder.path.startswith(p) for p in sys_path):
            file_io = folder.get_file_io('conftest.py')
            if Path(file_io.path) != module_context.py__file__():
                try:
                    m = load_module_from_path(module_context.inference_state, file_io)
                    conftest_module = m.as_context()
                    yield conftest_module

                    plugins_list = m.tree_node.get_used_names().get("pytest_plugins")
                    if plugins_list:
                        name = conftest_module.create_name(plugins_list[0])
                        yield from _load_pytest_plugins(module_context, name)
                except FileNotFoundError:
                    pass
            folder = folder.get_parent_folder()

            # prevent an infinite for loop if the same parent folder is return twice
            if last_folder is not None and folder.path == last_folder.path:
                break
            last_folder = folder  # keep track of the last found parent name

    for names in _PYTEST_FIXTURE_MODULES + _find_pytest_plugin_modules():
        for module_value in module_context.inference_state.import_module(names):
            yield module_value.as_context()


def _load_pytest_plugins(module_context, name):
    from jedi.inference.helpers import get_str_or_none

    for inferred in name.infer():
        for seq_value in inferred.py__iter__():
            for value in seq_value.infer():
                fq_name = get_str_or_none(value)
                if fq_name:
                    names = fq_name.split(".")
                    for module_value in module_context.inference_state.import_module(names):
                        yield module_value.as_context()


class FixtureFilter(ParserTreeFilter):
    def _filter(self, names):
        for name in super()._filter(names):
            # look for fixture definitions of imported names
            if name.parent.type == "import_from":
                imported_names = goto_import(self.parent_context, name)
                if any(
                    self._is_fixture(iname.parent_context, iname.tree_name)
                    for iname in imported_names
                    # discard imports of whole modules, that have no tree_name
                    if iname.tree_name
                ):
                    yield name

            elif self._is_fixture(self.parent_context, name):
                yield name

    def _is_fixture(self, context, name):
        funcdef = name.parent
        # Class fixtures are not supported
        if funcdef.type != "funcdef":
            return False
        decorated = funcdef.parent
        if decorated.type != "decorated":
            return False
        decorators = decorated.children[0]
        if decorators.type == 'decorators':
            decorators = decorators.children
        else:
            decorators = [decorators]
        for decorator in decorators:
            dotted_name = decorator.children[1]
            # A heuristic, this makes it faster.
            if 'fixture' in dotted_name.get_code():
                if dotted_name.type == 'atom_expr':
                    # Since Python3.9 a decorator does not have dotted names
                    # anymore.
                    last_trailer = dotted_name.children[-1]
                    last_leaf = last_trailer.get_last_leaf()
                    if last_leaf == ')':
                        values = infer_call_of_leaf(
                            context, last_leaf, cut_own_trailer=True
                        )
                    else:
                        values = context.infer_node(dotted_name)
                else:
                    values = context.infer_node(dotted_name)
                for value in values:
                    if value.name.get_qualified_names(include_module_names=True) \
                            == ('_pytest', 'fixtures', 'fixture'):
                        return True
        return False

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\test_ibm_model.py ===
"""
Tests for common methods of IBM translation models
"""

import unittest
from collections import defaultdict

from nltk.translate import AlignedSent, IBMModel
from nltk.translate.ibm_model import AlignmentInfo


class TestIBMModel(unittest.TestCase):
    __TEST_SRC_SENTENCE = ["j'", "aime", "bien", "jambon"]
    __TEST_TRG_SENTENCE = ["i", "love", "ham"]

    def test_vocabularies_are_initialized(self):
        parallel_corpora = [
            AlignedSent(["one", "two", "three", "four"], ["un", "deux", "trois"]),
            AlignedSent(["five", "one", "six"], ["quatre", "cinq", "six"]),
            AlignedSent([], ["sept"]),
        ]

        ibm_model = IBMModel(parallel_corpora)
        self.assertEqual(len(ibm_model.src_vocab), 8)
        self.assertEqual(len(ibm_model.trg_vocab), 6)

    def test_vocabularies_are_initialized_even_with_empty_corpora(self):
        parallel_corpora = []

        ibm_model = IBMModel(parallel_corpora)
        self.assertEqual(len(ibm_model.src_vocab), 1)  # addition of NULL token
        self.assertEqual(len(ibm_model.trg_vocab), 0)

    def test_best_model2_alignment(self):
        # arrange
        sentence_pair = AlignedSent(
            TestIBMModel.__TEST_TRG_SENTENCE, TestIBMModel.__TEST_SRC_SENTENCE
        )
        # None and 'bien' have zero fertility
        translation_table = {
            "i": {"j'": 0.9, "aime": 0.05, "bien": 0.02, "jambon": 0.03, None: 0},
            "love": {"j'": 0.05, "aime": 0.9, "bien": 0.01, "jambon": 0.01, None: 0.03},
            "ham": {"j'": 0, "aime": 0.01, "bien": 0, "jambon": 0.99, None: 0},
        }
        alignment_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.2)))
        )

        ibm_model = IBMModel([])
        ibm_model.translation_table = translation_table
        ibm_model.alignment_table = alignment_table

        # act
        a_info = ibm_model.best_model2_alignment(sentence_pair)

        # assert
        self.assertEqual(a_info.alignment[1:], (1, 2, 4))  # 0th element unused
        self.assertEqual(a_info.cepts, [[], [1], [2], [], [3]])

    def test_best_model2_alignment_does_not_change_pegged_alignment(self):
        # arrange
        sentence_pair = AlignedSent(
            TestIBMModel.__TEST_TRG_SENTENCE, TestIBMModel.__TEST_SRC_SENTENCE
        )
        translation_table = {
            "i": {"j'": 0.9, "aime": 0.05, "bien": 0.02, "jambon": 0.03, None: 0},
            "love": {"j'": 0.05, "aime": 0.9, "bien": 0.01, "jambon": 0.01, None: 0.03},
            "ham": {"j'": 0, "aime": 0.01, "bien": 0, "jambon": 0.99, None: 0},
        }
        alignment_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.2)))
        )

        ibm_model = IBMModel([])
        ibm_model.translation_table = translation_table
        ibm_model.alignment_table = alignment_table

        # act: force 'love' to be pegged to 'jambon'
        a_info = ibm_model.best_model2_alignment(sentence_pair, 2, 4)
        # assert
        self.assertEqual(a_info.alignment[1:], (1, 4, 4))
        self.assertEqual(a_info.cepts, [[], [1], [], [], [2, 3]])

    def test_best_model2_alignment_handles_fertile_words(self):
        # arrange
        sentence_pair = AlignedSent(
            ["i", "really", ",", "really", "love", "ham"],
            TestIBMModel.__TEST_SRC_SENTENCE,
        )
        # 'bien' produces 2 target words: 'really' and another 'really'
        translation_table = {
            "i": {"j'": 0.9, "aime": 0.05, "bien": 0.02, "jambon": 0.03, None: 0},
            "really": {"j'": 0, "aime": 0, "bien": 0.9, "jambon": 0.01, None: 0.09},
            ",": {"j'": 0, "aime": 0, "bien": 0.3, "jambon": 0, None: 0.7},
            "love": {"j'": 0.05, "aime": 0.9, "bien": 0.01, "jambon": 0.01, None: 0.03},
            "ham": {"j'": 0, "aime": 0.01, "bien": 0, "jambon": 0.99, None: 0},
        }
        alignment_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.2)))
        )

        ibm_model = IBMModel([])
        ibm_model.translation_table = translation_table
        ibm_model.alignment_table = alignment_table

        # act
        a_info = ibm_model.best_model2_alignment(sentence_pair)

        # assert
        self.assertEqual(a_info.alignment[1:], (1, 3, 0, 3, 2, 4))
        self.assertEqual(a_info.cepts, [[3], [1], [5], [2, 4], [6]])

    def test_best_model2_alignment_handles_empty_src_sentence(self):
        # arrange
        sentence_pair = AlignedSent(TestIBMModel.__TEST_TRG_SENTENCE, [])
        ibm_model = IBMModel([])

        # act
        a_info = ibm_model.best_model2_alignment(sentence_pair)

        # assert
        self.assertEqual(a_info.alignment[1:], (0, 0, 0))
        self.assertEqual(a_info.cepts, [[1, 2, 3]])

    def test_best_model2_alignment_handles_empty_trg_sentence(self):
        # arrange
        sentence_pair = AlignedSent([], TestIBMModel.__TEST_SRC_SENTENCE)
        ibm_model = IBMModel([])

        # act
        a_info = ibm_model.best_model2_alignment(sentence_pair)

        # assert
        self.assertEqual(a_info.alignment[1:], ())
        self.assertEqual(a_info.cepts, [[], [], [], [], []])

    def test_neighboring_finds_neighbor_alignments(self):
        # arrange
        a_info = AlignmentInfo(
            (0, 3, 2),
            (None, "des", "œufs", "verts"),
            ("UNUSED", "green", "eggs"),
            [[], [], [2], [1]],
        )
        ibm_model = IBMModel([])

        # act
        neighbors = ibm_model.neighboring(a_info)

        # assert
        neighbor_alignments = set()
        for neighbor in neighbors:
            neighbor_alignments.add(neighbor.alignment)
        expected_alignments = {
            # moves
            (0, 0, 2),
            (0, 1, 2),
            (0, 2, 2),
            (0, 3, 0),
            (0, 3, 1),
            (0, 3, 3),
            # swaps
            (0, 2, 3),
            # original alignment
            (0, 3, 2),
        }
        self.assertEqual(neighbor_alignments, expected_alignments)

    def test_neighboring_sets_neighbor_alignment_info(self):
        # arrange
        a_info = AlignmentInfo(
            (0, 3, 2),
            (None, "des", "œufs", "verts"),
            ("UNUSED", "green", "eggs"),
            [[], [], [2], [1]],
        )
        ibm_model = IBMModel([])

        # act
        neighbors = ibm_model.neighboring(a_info)

        # assert: select a few particular alignments
        for neighbor in neighbors:
            if neighbor.alignment == (0, 2, 2):
                moved_alignment = neighbor
            elif neighbor.alignment == (0, 3, 2):
                swapped_alignment = neighbor

        self.assertEqual(moved_alignment.cepts, [[], [], [1, 2], []])
        self.assertEqual(swapped_alignment.cepts, [[], [], [2], [1]])

    def test_neighboring_returns_neighbors_with_pegged_alignment(self):
        # arrange
        a_info = AlignmentInfo(
            (0, 3, 2),
            (None, "des", "œufs", "verts"),
            ("UNUSED", "green", "eggs"),
            [[], [], [2], [1]],
        )
        ibm_model = IBMModel([])

        # act: peg 'eggs' to align with 'œufs'
        neighbors = ibm_model.neighboring(a_info, 2)

        # assert
        neighbor_alignments = set()
        for neighbor in neighbors:
            neighbor_alignments.add(neighbor.alignment)
        expected_alignments = {
            # moves
            (0, 0, 2),
            (0, 1, 2),
            (0, 2, 2),
            # no swaps
            # original alignment
            (0, 3, 2),
        }
        self.assertEqual(neighbor_alignments, expected_alignments)

    def test_hillclimb(self):
        # arrange
        initial_alignment = AlignmentInfo((0, 3, 2), None, None, None)

        def neighboring_mock(a, j):
            if a.alignment == (0, 3, 2):
                return {
                    AlignmentInfo((0, 2, 2), None, None, None),
                    AlignmentInfo((0, 1, 1), None, None, None),
                }
            elif a.alignment == (0, 2, 2):
                return {
                    AlignmentInfo((0, 3, 3), None, None, None),
                    AlignmentInfo((0, 4, 4), None, None, None),
                }
            return set()

        def prob_t_a_given_s_mock(a):
            prob_values = {
                (0, 3, 2): 0.5,
                (0, 2, 2): 0.6,
                (0, 1, 1): 0.4,
                (0, 3, 3): 0.6,
                (0, 4, 4): 0.7,
            }
            return prob_values.get(a.alignment, 0.01)

        ibm_model = IBMModel([])
        ibm_model.neighboring = neighboring_mock
        ibm_model.prob_t_a_given_s = prob_t_a_given_s_mock

        # act
        best_alignment = ibm_model.hillclimb(initial_alignment)

        # assert: hill climbing goes from (0, 3, 2) -> (0, 2, 2) -> (0, 4, 4)
        self.assertEqual(best_alignment.alignment, (0, 4, 4))

    def test_sample(self):
        # arrange
        sentence_pair = AlignedSent(
            TestIBMModel.__TEST_TRG_SENTENCE, TestIBMModel.__TEST_SRC_SENTENCE
        )
        ibm_model = IBMModel([])
        ibm_model.prob_t_a_given_s = lambda x: 0.001

        # act
        samples, best_alignment = ibm_model.sample(sentence_pair)

        # assert
        self.assertEqual(len(samples), 61)

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\f90mod_rules.py ===
"""
Build F90 module support for f2py2e.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
__version__ = "$Revision: 1.27 $"[10:-1]

f2py_version = 'See `f2py -v`'

import numpy as np

from . import capi_maps, func2subr

# The environment provided by auxfuncs.py is needed for some calls to eval.
# As the needed functions cannot be determined by static inspection of the
# code, it is safest to use import * pending a major refactoring of f2py.
from .auxfuncs import *
from .crackfortran import undo_rmbadname, undo_rmbadname1

options = {}


def findf90modules(m):
    if ismodule(m):
        return [m]
    if not hasbody(m):
        return []
    ret = []
    for b in m['body']:
        if ismodule(b):
            ret.append(b)
        else:
            ret = ret + findf90modules(b)
    return ret


fgetdims1 = """\
      external f2pysetdata
      logical ns
      integer r,i
      integer(%d) s(*)
      ns = .FALSE.
      if (allocated(d)) then
         do i=1,r
            if ((size(d,i).ne.s(i)).and.(s(i).ge.0)) then
               ns = .TRUE.
            end if
         end do
         if (ns) then
            deallocate(d)
         end if
      end if
      if ((.not.allocated(d)).and.(s(1).ge.1)) then""" % np.intp().itemsize

fgetdims2 = """\
      end if
      if (allocated(d)) then
         do i=1,r
            s(i) = size(d,i)
         end do
      end if
      flag = 1
      call f2pysetdata(d,allocated(d))"""

fgetdims2_sa = """\
      end if
      if (allocated(d)) then
         do i=1,r
            s(i) = size(d,i)
         end do
         !s(r) must be equal to len(d(1))
      end if
      flag = 2
      call f2pysetdata(d,allocated(d))"""


def buildhooks(pymod):
    from . import rules
    ret = {'f90modhooks': [], 'initf90modhooks': [], 'body': [],
           'need': ['F_FUNC', 'arrayobject.h'],
           'separatorsfor': {'includes0': '\n', 'includes': '\n'},
           'docs': ['"Fortran 90/95 modules:\\n"'],
           'latexdoc': []}
    fhooks = ['']

    def fadd(line, s=fhooks):
        s[0] = f'{s[0]}\n      {line}'
    doc = ['']

    def dadd(line, s=doc):
        s[0] = f'{s[0]}\n{line}'

    usenames = getuseblocks(pymod)
    for m in findf90modules(pymod):
        sargs, fargs, efargs, modobjs, notvars, onlyvars = [], [], [], [], [
            m['name']], []
        sargsp = []
        ifargs = []
        mfargs = []
        if hasbody(m):
            for b in m['body']:
                notvars.append(b['name'])
        for n in m['vars'].keys():
            var = m['vars'][n]

            if (n not in notvars and isvariable(var)) and (not l_or(isintent_hide, isprivate)(var)):
                onlyvars.append(n)
                mfargs.append(n)
        outmess(f"\t\tConstructing F90 module support for \"{m['name']}\"...\n")
        if len(onlyvars) == 0 and len(notvars) == 1 and m['name'] in notvars:
            outmess(f"\t\t\tSkipping {m['name']} since there are no public vars/func in this module...\n")
            continue

        # gh-25186
        if m['name'] in usenames and containscommon(m):
            outmess(f"\t\t\tSkipping {m['name']} since it is in 'use' and contains a common block...\n")
            continue
        # skip modules with derived types
        if m['name'] in usenames and containsderivedtypes(m):
            outmess(f"\t\t\tSkipping {m['name']} since it is in 'use' and contains a derived type...\n")
            continue
        if onlyvars:
            outmess(f"\t\t  Variables: {' '.join(onlyvars)}\n")
        chooks = ['']

        def cadd(line, s=chooks):
            s[0] = f'{s[0]}\n{line}'
        ihooks = ['']

        def iadd(line, s=ihooks):
            s[0] = f'{s[0]}\n{line}'

        vrd = capi_maps.modsign2map(m)
        cadd('static FortranDataDef f2py_%s_def[] = {' % (m['name']))
        dadd('\\subsection{Fortran 90/95 module \\texttt{%s}}\n' % (m['name']))
        if hasnote(m):
            note = m['note']
            if isinstance(note, list):
                note = '\n'.join(note)
            dadd(note)
        if onlyvars:
            dadd('\\begin{description}')
        for n in onlyvars:
            var = m['vars'][n]
            modobjs.append(n)
            ct = capi_maps.getctype(var)
            at = capi_maps.c2capi_map[ct]
            dm = capi_maps.getarrdims(n, var)
            dms = dm['dims'].replace('*', '-1').strip()
            dms = dms.replace(':', '-1').strip()
            if not dms:
                dms = '-1'
            use_fgetdims2 = fgetdims2
            cadd('\t{"%s",%s,{{%s}},%s, %s},' %
                 (undo_rmbadname1(n), dm['rank'], dms, at,
                  capi_maps.get_elsize(var)))
            dadd('\\item[]{{}\\verb@%s@{}}' %
                 (capi_maps.getarrdocsign(n, var)))
            if hasnote(var):
                note = var['note']
                if isinstance(note, list):
                    note = '\n'.join(note)
                dadd(f'--- {note}')
            if isallocatable(var):
                fargs.append(f"f2py_{m['name']}_getdims_{n}")
                efargs.append(fargs[-1])
                sargs.append(
                    f'void (*{n})(int*,npy_intp*,void(*)(char*,npy_intp*),int*)')
                sargsp.append('void (*)(int*,npy_intp*,void(*)(char*,npy_intp*),int*)')
                iadd(f"\tf2py_{m['name']}_def[i_f2py++].func = {n};")
                fadd(f'subroutine {fargs[-1]}(r,s,f2pysetdata,flag)')
                fadd(f"use {m['name']}, only: d => {undo_rmbadname1(n)}\n")
                fadd('integer flag\n')
                fhooks[0] = fhooks[0] + fgetdims1
                dms = range(1, int(dm['rank']) + 1)
                fadd(' allocate(d(%s))\n' %
                     (','.join(['s(%s)' % i for i in dms])))
                fhooks[0] = fhooks[0] + use_fgetdims2
                fadd(f'end subroutine {fargs[-1]}')
            else:
                fargs.append(n)
                sargs.append(f'char *{n}')
                sargsp.append('char*')
                iadd(f"\tf2py_{m['name']}_def[i_f2py++].data = {n};")
        if onlyvars:
            dadd('\\end{description}')
        if hasbody(m):
            for b in m['body']:
                if not isroutine(b):
                    outmess("f90mod_rules.buildhooks:"
                            f" skipping {b['block']} {b['name']}\n")
                    continue
                modobjs.append(f"{b['name']}()")
                b['modulename'] = m['name']
                api, wrap = rules.buildapi(b)
                if isfunction(b):
                    fhooks[0] = fhooks[0] + wrap
                    fargs.append(f"f2pywrap_{m['name']}_{b['name']}")
                    ifargs.append(func2subr.createfuncwrapper(b, signature=1))
                elif wrap:
                    fhooks[0] = fhooks[0] + wrap
                    fargs.append(f"f2pywrap_{m['name']}_{b['name']}")
                    ifargs.append(
                        func2subr.createsubrwrapper(b, signature=1))
                else:
                    fargs.append(b['name'])
                    mfargs.append(fargs[-1])
                api['externroutines'] = []
                ar = applyrules(api, vrd)
                ar['docs'] = []
                ar['docshort'] = []
                ret = dictappend(ret, ar)
                cadd(('\t{"%s",-1,{{-1}},0,0,NULL,(void *)'
                      'f2py_rout_#modulename#_%s_%s,'
                      'doc_f2py_rout_#modulename#_%s_%s},')
                     % (b['name'], m['name'], b['name'], m['name'], b['name']))
                sargs.append(f"char *{b['name']}")
                sargsp.append('char *')
                iadd(f"\tf2py_{m['name']}_def[i_f2py++].data = {b['name']};")
        cadd('\t{NULL}\n};\n')
        iadd('}')
        ihooks[0] = 'static void f2py_setup_%s(%s) {\n\tint i_f2py=0;%s' % (
            m['name'], ','.join(sargs), ihooks[0])
        if '_' in m['name']:
            F_FUNC = 'F_FUNC_US'
        else:
            F_FUNC = 'F_FUNC'
        iadd('extern void %s(f2pyinit%s,F2PYINIT%s)(void (*)(%s));'
             % (F_FUNC, m['name'], m['name'].upper(), ','.join(sargsp)))
        iadd('static void f2py_init_%s(void) {' % (m['name']))
        iadd('\t%s(f2pyinit%s,F2PYINIT%s)(f2py_setup_%s);'
             % (F_FUNC, m['name'], m['name'].upper(), m['name']))
        iadd('}\n')
        ret['f90modhooks'] = ret['f90modhooks'] + chooks + ihooks
        ret['initf90modhooks'] = ['\tPyDict_SetItemString(d, "%s", PyFortranObject_New(f2py_%s_def,f2py_init_%s));' % (
            m['name'], m['name'], m['name'])] + ret['initf90modhooks']
        fadd('')
        fadd(f"subroutine f2pyinit{m['name']}(f2pysetupfunc)")
        if mfargs:
            for a in undo_rmbadname(mfargs):
                fadd(f"use {m['name']}, only : {a}")
        if ifargs:
            fadd(' '.join(['interface'] + ifargs))
            fadd('end interface')
        fadd('external f2pysetupfunc')
        if efargs:
            for a in undo_rmbadname(efargs):
                fadd(f'external {a}')
        fadd(f"call f2pysetupfunc({','.join(undo_rmbadname(fargs))})")
        fadd(f"end subroutine f2pyinit{m['name']}\n")

        dadd('\n'.join(ret['latexdoc']).replace(
            r'\subsection{', r'\subsubsection{'))

        ret['latexdoc'] = []
        ret['docs'].append(f"\"\t{m['name']} --- {','.join(undo_rmbadname(modobjs))}\"")

    ret['routine_defs'] = ''
    ret['doc'] = []
    ret['docshort'] = []
    ret['latexdoc'] = doc[0]
    if len(ret['docs']) <= 1:
        ret['docs'] = ''
    return ret, fhooks[0]

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\unix.py ===
"""Unix."""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Iterator, NoReturn

from .api import PlatformDirsABC

if sys.platform == "win32":

    def getuid() -> NoReturn:
        msg = "should only be used on Unix"
        raise RuntimeError(msg)

else:
    from os import getuid


class Unix(PlatformDirsABC):  # noqa: PLR0904
    """
    On Unix/Linux, we follow the `XDG Basedir Spec <https://specifications.freedesktop.org/basedir-spec/basedir-spec-
    latest.html>`_.

    The spec allows overriding directories with environment variables. The examples shown are the default values,
    alongside the name of the environment variable that overrides them. Makes use of the `appname
    <platformdirs.api.PlatformDirsABC.appname>`, `version <platformdirs.api.PlatformDirsABC.version>`, `multipath
    <platformdirs.api.PlatformDirsABC.multipath>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g. ``~/.local/share/$appname/$version`` or
         ``$XDG_DATA_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_DATA_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/share")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_data_dirs(self) -> list[str]:
        path = os.environ.get("XDG_DATA_DIRS", "")
        if not path.strip():
            path = f"/usr/local/share{os.pathsep}/usr/share"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>` is
         enabled and ``XDG_DATA_DIRS`` is set and a multi path the response is also a multi path separated by the
         OS path separator), e.g. ``/usr/local/share/$appname/$version`` or ``/usr/share/$appname/$version``
        """
        # XDG default for $XDG_DATA_DIRS; only first, if multipath is False
        dirs = self._site_data_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. ``~/.config/$appname/$version`` or
         ``$XDG_CONFIG_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CONFIG_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.config")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_config_dirs(self) -> list[str]:
        path = os.environ.get("XDG_CONFIG_DIRS", "")
        if not path.strip():
            path = "/etc/xdg"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_config_dir(self) -> str:
        """
        :return: config directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>`
         is enabled and ``XDG_CONFIG_DIRS`` is set and a multi path the response is also a multi path separated by
         the OS path separator), e.g. ``/etc/xdg/$appname/$version``
        """
        # XDG default for $XDG_CONFIG_DIRS only first, if multipath is False
        dirs = self._site_config_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user, e.g. ``~/.cache/$appname/$version`` or
         ``~/$XDG_CACHE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CACHE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.cache")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``/var/cache/$appname/$version``"""
        return self._append_app_name_and_version("/var/cache")

    @property
    def user_state_dir(self) -> str:
        """
        :return: state directory tied to the user, e.g. ``~/.local/state/$appname/$version`` or
         ``$XDG_STATE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_STATE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/state")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_state_dir` if not opinionated else ``log`` in it"""
        path = self.user_state_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return _get_user_media_dir("XDG_DOCUMENTS_DIR", "~/Documents")

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return _get_user_media_dir("XDG_DOWNLOAD_DIR", "~/Downloads")

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return _get_user_media_dir("XDG_PICTURES_DIR", "~/Pictures")

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Videos``"""
        return _get_user_media_dir("XDG_VIDEOS_DIR", "~/Videos")

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return _get_user_media_dir("XDG_MUSIC_DIR", "~/Music")

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return _get_user_media_dir("XDG_DESKTOP_DIR", "~/Desktop")

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g. ``/run/user/$(id -u)/$appname/$version`` or
         ``$XDG_RUNTIME_DIR/$appname/$version``.

         For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/user/$(id -u)/$appname/$version`` if
         exists, otherwise ``/tmp/runtime-$(id -u)/$appname/$version``, if``$XDG_RUNTIME_DIR``
         is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = f"/var/run/user/{getuid()}"
                if not Path(path).exists():
                    path = f"/tmp/runtime-{getuid()}"  # noqa: S108
            else:
                path = f"/run/user/{getuid()}"
        return self._append_app_name_and_version(path)

    @property
    def site_runtime_dir(self) -> str:
        """
        :return: runtime directory shared by users, e.g. ``/run/$appname/$version`` or \
        ``$XDG_RUNTIME_DIR/$appname/$version``.

        Note that this behaves almost exactly like `user_runtime_dir` if ``$XDG_RUNTIME_DIR`` is set, but will
        fall back to paths associated to the root user instead of a regular logged-in user if it's not set.

        If you wish to ensure that a logged-in root user path is returned e.g. ``/run/user/0``, use `user_runtime_dir`
        instead.

        For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/$appname/$version`` if ``$XDG_RUNTIME_DIR`` is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = "/var/run"
            else:
                path = "/run"
        return self._append_app_name_and_version(path)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users, returns the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_config_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield from self._site_config_dirs

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield from self._site_data_dirs


def _get_user_media_dir(env_var: str, fallback_tilde_path: str) -> str:
    media_dir = _get_user_dirs_folder(env_var)
    if media_dir is None:
        media_dir = os.environ.get(env_var, "").strip()
        if not media_dir:
            media_dir = os.path.expanduser(fallback_tilde_path)  # noqa: PTH111

    return media_dir


def _get_user_dirs_folder(key: str) -> str | None:
    """
    Return directory from user-dirs.dirs config file.

    See https://freedesktop.org/wiki/Software/xdg-user-dirs/.

    """
    user_dirs_config_path = Path(Unix().user_config_dir) / "user-dirs.dirs"
    if user_dirs_config_path.exists():
        parser = ConfigParser()

        with user_dirs_config_path.open() as stream:
            # Add fake section header, so ConfigParser doesn't complain
            parser.read_string(f"[top]\n{stream.read()}")

        if key not in parser["top"]:
            return None

        path = parser["top"][key].strip('"')
        # Handle relative home paths
        return path.replace("$HOME", os.path.expanduser("~"))  # noqa: PTH111

    return None


__all__ = [
    "Unix",
]

# === NexusCore/openenv\Lib\site-packages\trio\_core\_generated_run.py ===
# ***********************************************************
# ******* WARNING: AUTOGENERATED! ALL EDITS WILL BE LOST ******
# *************************************************************
from __future__ import annotations

from typing import TYPE_CHECKING

from ._ki import enable_ki_protection
from ._run import _NO_SEND, GLOBAL_RUN_CONTEXT, RunStatistics, Task

if TYPE_CHECKING:
    import contextvars
    from collections.abc import Awaitable, Callable

    from outcome import Outcome
    from typing_extensions import Unpack

    from .._abc import Clock
    from ._entry_queue import TrioToken
    from ._run import PosArgT


__all__ = [
    "current_clock",
    "current_root_task",
    "current_statistics",
    "current_time",
    "current_trio_token",
    "reschedule",
    "spawn_system_task",
    "wait_all_tasks_blocked",
]


@enable_ki_protection
def current_statistics() -> RunStatistics:
    """Returns ``RunStatistics``, which contains run-loop-level debugging information.

    Currently, the following fields are defined:

    * ``tasks_living`` (int): The number of tasks that have been spawned
      and not yet exited.
    * ``tasks_runnable`` (int): The number of tasks that are currently
      queued on the run queue (as opposed to blocked waiting for something
      to happen).
    * ``seconds_to_next_deadline`` (float): The time until the next
      pending cancel scope deadline. May be negative if the deadline has
      expired but we haven't yet processed cancellations. May be
      :data:`~math.inf` if there are no pending deadlines.
    * ``run_sync_soon_queue_size`` (int): The number of
      unprocessed callbacks queued via
      :meth:`trio.lowlevel.TrioToken.run_sync_soon`.
    * ``io_statistics`` (object): Some statistics from Trio's I/O
      backend. This always has an attribute ``backend`` which is a string
      naming which operating-system-specific I/O backend is in use; the
      other attributes vary between backends.

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.current_statistics()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def current_time() -> float:
    """Returns the current time according to Trio's internal clock.

    Returns:
        float: The current time.

    Raises:
        RuntimeError: if not inside a call to :func:`trio.run`.

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.current_time()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def current_clock() -> Clock:
    """Returns the current :class:`~trio.abc.Clock`."""
    try:
        return GLOBAL_RUN_CONTEXT.runner.current_clock()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def current_root_task() -> Task | None:
    """Returns the current root :class:`Task`.

    This is the task that is the ultimate parent of all other tasks.

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.current_root_task()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def reschedule(task: Task, next_send: Outcome[object] = _NO_SEND) -> None:
    """Reschedule the given task with the given
    :class:`outcome.Outcome`.

    See :func:`wait_task_rescheduled` for the gory details.

    There must be exactly one call to :func:`reschedule` for every call to
    :func:`wait_task_rescheduled`. (And when counting, keep in mind that
    returning :data:`Abort.SUCCEEDED` from an abort callback is equivalent
    to calling :func:`reschedule` once.)

    Args:
      task (trio.lowlevel.Task): the task to be rescheduled. Must be blocked
          in a call to :func:`wait_task_rescheduled`.
      next_send (outcome.Outcome): the value (or error) to return (or
          raise) from :func:`wait_task_rescheduled`.

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.reschedule(task, next_send)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def spawn_system_task(
    async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
    *args: Unpack[PosArgT],
    name: object = None,
    context: contextvars.Context | None = None,
) -> Task:
    """Spawn a "system" task.

    System tasks have a few differences from regular tasks:

    * They don't need an explicit nursery; instead they go into the
      internal "system nursery".

    * If a system task raises an exception, then it's converted into a
      :exc:`~trio.TrioInternalError` and *all* tasks are cancelled. If you
      write a system task, you should be careful to make sure it doesn't
      crash.

    * System tasks are automatically cancelled when the main task exits.

    * By default, system tasks have :exc:`KeyboardInterrupt` protection
      *enabled*. If you want your task to be interruptible by control-C,
      then you need to use :func:`disable_ki_protection` explicitly (and
      come up with some plan for what to do with a
      :exc:`KeyboardInterrupt`, given that system tasks aren't allowed to
      raise exceptions).

    * System tasks do not inherit context variables from their creator.

    Towards the end of a call to :meth:`trio.run`, after the main
    task and all system tasks have exited, the system nursery
    becomes closed. At this point, new calls to
    :func:`spawn_system_task` will raise ``RuntimeError("Nursery
    is closed to new arrivals")`` instead of creating a system
    task. It's possible to encounter this state either in
    a ``finally`` block in an async generator, or in a callback
    passed to :meth:`TrioToken.run_sync_soon` at the right moment.

    Args:
      async_fn: An async callable.
      args: Positional arguments for ``async_fn``. If you want to pass
          keyword arguments, use :func:`functools.partial`.
      name: The name for this task. Only used for debugging/introspection
          (e.g. ``repr(task_obj)``). If this isn't a string,
          :func:`spawn_system_task` will try to make it one. A common use
          case is if you're wrapping a function before spawning a new
          task, you might pass the original function as the ``name=`` to
          make debugging easier.
      context: An optional ``contextvars.Context`` object with context variables
          to use for this task. You would normally get a copy of the current
          context with ``context = contextvars.copy_context()`` and then you would
          pass that ``context`` object here.

    Returns:
      Task: the newly spawned task

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.spawn_system_task(
            async_fn, *args, name=name, context=context
        )
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def current_trio_token() -> TrioToken:
    """Retrieve the :class:`TrioToken` for the current call to
    :func:`trio.run`.

    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.current_trio_token()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
async def wait_all_tasks_blocked(cushion: float = 0.0) -> None:
    """Block until there are no runnable tasks.

    This is useful in testing code when you want to give other tasks a
    chance to "settle down". The calling task is blocked, and doesn't wake
    up until all other tasks are also blocked for at least ``cushion``
    seconds. (Setting a non-zero ``cushion`` is intended to handle cases
    like two tasks talking to each other over a local socket, where we
    want to ignore the potential brief moment between a send and receive
    when all tasks are blocked.)

    Note that ``cushion`` is measured in *real* time, not the Trio clock
    time.

    If there are multiple tasks blocked in :func:`wait_all_tasks_blocked`,
    then the one with the shortest ``cushion`` is the one woken (and
    this task becoming unblocked resets the timers for the remaining
    tasks). If there are multiple tasks that have exactly the same
    ``cushion``, then all are woken.

    You should also consider :class:`trio.testing.Sequencer`, which
    provides a more explicit way to control execution ordering within a
    test, and will often produce more readable tests.

    Example:
      Here's an example of one way to test that Trio's locks are fair: we
      take the lock in the parent, start a child, wait for the child to be
      blocked waiting for the lock (!), and then check that we can't
      release and immediately re-acquire the lock::

         async def lock_taker(lock):
             await lock.acquire()
             lock.release()

         async def test_lock_fairness():
             lock = trio.Lock()
             await lock.acquire()
             async with trio.open_nursery() as nursery:
                 nursery.start_soon(lock_taker, lock)
                 # child hasn't run yet, we have the lock
                 assert lock.locked()
                 assert lock._owner is trio.lowlevel.current_task()
                 await trio.testing.wait_all_tasks_blocked()
                 # now the child has run and is blocked on lock.acquire(), we
                 # still have the lock
                 assert lock.locked()
                 assert lock._owner is trio.lowlevel.current_task()
                 lock.release()
                 try:
                     # The child has a prior claim, so we can't have it
                     lock.acquire_nowait()
                 except trio.WouldBlock:
                     assert lock._owner is not trio.lowlevel.current_task()
                     print("PASS")
                 else:
                     print("FAIL")

    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.wait_all_tasks_blocked(cushion)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_file_io.py ===
from __future__ import annotations

import importlib
import io
import os
import re
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import sentinel

import pytest

import trio
from trio import _core, _file_io
from trio._file_io import _FILE_ASYNC_METHODS, _FILE_SYNC_ATTRS, AsyncIOWrapper

if TYPE_CHECKING:
    import pathlib


@pytest.fixture
def path(tmp_path: pathlib.Path) -> str:
    return os.fspath(tmp_path / "test")


@pytest.fixture
def wrapped() -> mock.Mock:
    return mock.Mock(spec_set=io.StringIO)


@pytest.fixture
def async_file(wrapped: mock.Mock) -> AsyncIOWrapper[mock.Mock]:
    return trio.wrap_file(wrapped)


def test_wrap_invalid() -> None:
    with pytest.raises(TypeError):
        trio.wrap_file("")


def test_wrap_non_iobase() -> None:
    class FakeFile:
        def close(self) -> None:  # pragma: no cover
            pass

        def write(self) -> None:  # pragma: no cover
            pass

    wrapped = FakeFile()
    assert not isinstance(wrapped, io.IOBase)

    async_file = trio.wrap_file(wrapped)
    assert isinstance(async_file, AsyncIOWrapper)

    del FakeFile.write

    with pytest.raises(TypeError):
        trio.wrap_file(FakeFile())


def test_wrapped_property(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    assert async_file.wrapped is wrapped


def test_dir_matches_wrapped(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    attrs = _FILE_SYNC_ATTRS.union(_FILE_ASYNC_METHODS)

    # all supported attrs in wrapped should be available in async_file
    assert all(attr in dir(async_file) for attr in attrs if attr in dir(wrapped))
    # all supported attrs not in wrapped should not be available in async_file
    assert not any(
        attr in dir(async_file) for attr in attrs if attr not in dir(wrapped)
    )


def test_unsupported_not_forwarded() -> None:
    class FakeFile(io.RawIOBase):
        def unsupported_attr(self) -> None:  # pragma: no cover
            pass

    async_file = trio.wrap_file(FakeFile())

    assert hasattr(async_file.wrapped, "unsupported_attr")

    with pytest.raises(AttributeError):
        # B018 "useless expression"
        async_file.unsupported_attr  # type: ignore[attr-defined] # noqa: B018


def test_type_stubs_match_lists() -> None:
    """Check the manual stubs match the list of wrapped methods."""
    # Fetch the module's source code.
    assert _file_io.__spec__ is not None
    loader = _file_io.__spec__.loader
    assert isinstance(loader, importlib.abc.SourceLoader)
    source = io.StringIO(loader.get_source("trio._file_io"))

    # Find the class, then find the TYPE_CHECKING block.
    for line in source:
        if "class AsyncIOWrapper" in line:
            break
    else:  # pragma: no cover - should always find this
        pytest.fail("No class definition line?")

    for line in source:
        if "if TYPE_CHECKING" in line:
            break
    else:  # pragma: no cover - should always find this
        pytest.fail("No TYPE CHECKING line?")

    # Now we should be at the type checking block.
    found: list[tuple[str, str]] = []
    for line in source:  # pragma: no branch - expected to break early
        if line.strip() and not line.startswith(" " * 8):
            break  # Dedented out of the if TYPE_CHECKING block.
        match = re.match(r"\s*(async )?def ([a-zA-Z0-9_]+)\(", line)
        if match is not None:
            kind = "async" if match.group(1) is not None else "sync"
            found.append((match.group(2), kind))

    # Compare two lists so that we can easily see duplicates, and see what is different overall.
    expected = [(fname, "async") for fname in _FILE_ASYNC_METHODS]
    expected += [(fname, "sync") for fname in _FILE_SYNC_ATTRS]
    # Ignore order, error if duplicates are present.
    found.sort()
    expected.sort()
    assert found == expected


def test_sync_attrs_forwarded(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    for attr_name in _FILE_SYNC_ATTRS:
        if attr_name not in dir(async_file):
            continue

        assert getattr(async_file, attr_name) is getattr(wrapped, attr_name)


def test_sync_attrs_match_wrapper(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    for attr_name in _FILE_SYNC_ATTRS:
        if attr_name in dir(async_file):
            continue

        with pytest.raises(AttributeError):
            getattr(async_file, attr_name)

        with pytest.raises(AttributeError):
            getattr(wrapped, attr_name)


def test_async_methods_generated_once(async_file: AsyncIOWrapper[mock.Mock]) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name not in dir(async_file):
            continue

        assert getattr(async_file, meth_name) is getattr(async_file, meth_name)


# I gave up on typing this one
def test_async_methods_signature(async_file: AsyncIOWrapper[mock.Mock]) -> None:
    # use read as a representative of all async methods
    assert async_file.read.__name__ == "read"
    assert async_file.read.__qualname__ == "AsyncIOWrapper.read"

    assert async_file.read.__doc__ is not None
    assert "io.StringIO.read" in async_file.read.__doc__


async def test_async_methods_wrap(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name not in dir(async_file):
            continue

        meth = getattr(async_file, meth_name)
        wrapped_meth = getattr(wrapped, meth_name)

        value = await meth(sentinel.argument, keyword=sentinel.keyword)

        wrapped_meth.assert_called_once_with(
            sentinel.argument,
            keyword=sentinel.keyword,
        )
        assert value == wrapped_meth()

        wrapped.reset_mock()


def test_async_methods_match_wrapper(
    async_file: AsyncIOWrapper[mock.Mock],
    wrapped: mock.Mock,
) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name in dir(async_file):
            continue

        with pytest.raises(AttributeError):
            getattr(async_file, meth_name)

        with pytest.raises(AttributeError):
            getattr(wrapped, meth_name)


async def test_open(path: pathlib.Path) -> None:
    f = await trio.open_file(path, "w")

    assert isinstance(f, AsyncIOWrapper)

    await f.aclose()


async def test_open_context_manager(path: pathlib.Path) -> None:
    async with await trio.open_file(path, "w") as f:
        assert isinstance(f, AsyncIOWrapper)
        assert not f.closed

    assert f.closed


async def test_async_iter() -> None:
    async_file = trio.wrap_file(io.StringIO("test\nfoo\nbar"))
    expected = list(async_file.wrapped)
    async_file.wrapped.seek(0)

    result = [line async for line in async_file]

    assert result == expected


async def test_aclose_cancelled(path: pathlib.Path) -> None:
    with _core.CancelScope() as cscope:
        f = await trio.open_file(path, "w")
        cscope.cancel()

        with pytest.raises(_core.Cancelled):
            await f.write("a")

        with pytest.raises(_core.Cancelled):
            await f.aclose()

    assert f.closed


async def test_detach_rewraps_asynciobase(tmp_path: pathlib.Path) -> None:
    tmp_file = tmp_path / "filename"
    tmp_file.touch()
    # flake8-async does not like opening files in async mode
    with open(tmp_file, mode="rb", buffering=0) as raw:  # noqa: ASYNC230
        buffered = io.BufferedReader(raw)

        async_file = trio.wrap_file(buffered)

        detached = await async_file.detach()

        assert isinstance(detached, AsyncIOWrapper)
        assert detached.wrapped is raw

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_inspect.py ===
import inspect
from inspect import cleandoc, getdoc, getfile, isclass, ismodule, signature
from typing import Any, Collection, Iterable, Optional, Tuple, Type, Union

from .console import Group, RenderableType
from .control import escape_control_codes
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin
from .panel import Panel
from .pretty import Pretty
from .table import Table
from .text import Text, TextType


def _first_paragraph(doc: str) -> str:
    """Get the first paragraph from a docstring."""
    paragraph, _, _ = doc.partition("\n\n")
    return paragraph


class Inspect(JupyterMixin):
    """A renderable to inspect any Python Object.

    Args:
        obj (Any): An object to inspect.
        title (str, optional): Title to display over inspect result, or None use type. Defaults to None.
        help (bool, optional): Show full help text rather than just first paragraph. Defaults to False.
        methods (bool, optional): Enable inspection of callables. Defaults to False.
        docs (bool, optional): Also render doc strings. Defaults to True.
        private (bool, optional): Show private attributes (beginning with underscore). Defaults to False.
        dunder (bool, optional): Show attributes starting with double underscore. Defaults to False.
        sort (bool, optional): Sort attributes alphabetically. Defaults to True.
        all (bool, optional): Show all attributes. Defaults to False.
        value (bool, optional): Pretty print value of object. Defaults to True.
    """

    def __init__(
        self,
        obj: Any,
        *,
        title: Optional[TextType] = None,
        help: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all: bool = True,
        value: bool = True,
    ) -> None:
        self.highlighter = ReprHighlighter()
        self.obj = obj
        self.title = title or self._make_title(obj)
        if all:
            methods = private = dunder = True
        self.help = help
        self.methods = methods
        self.docs = docs or help
        self.private = private or dunder
        self.dunder = dunder
        self.sort = sort
        self.value = value

    def _make_title(self, obj: Any) -> Text:
        """Make a default title."""
        title_str = (
            str(obj)
            if (isclass(obj) or callable(obj) or ismodule(obj))
            else str(type(obj))
        )
        title_text = self.highlighter(title_str)
        return title_text

    def __rich__(self) -> Panel:
        return Panel.fit(
            Group(*self._render()),
            title=self.title,
            border_style="scope.border",
            padding=(0, 1),
        )

    def _get_signature(self, name: str, obj: Any) -> Optional[Text]:
        """Get a signature for a callable."""
        try:
            _signature = str(signature(obj)) + ":"
        except ValueError:
            _signature = "(...)"
        except TypeError:
            return None

        source_filename: Optional[str] = None
        try:
            source_filename = getfile(obj)
        except (OSError, TypeError):
            # OSError is raised if obj has no source file, e.g. when defined in REPL.
            pass

        callable_name = Text(name, style="inspect.callable")
        if source_filename:
            callable_name.stylize(f"link file://{source_filename}")
        signature_text = self.highlighter(_signature)

        qualname = name or getattr(obj, "__qualname__", name)

        # If obj is a module, there may be classes (which are callable) to display
        if inspect.isclass(obj):
            prefix = "class"
        elif inspect.iscoroutinefunction(obj):
            prefix = "async def"
        else:
            prefix = "def"

        qual_signature = Text.assemble(
            (f"{prefix} ", f"inspect.{prefix.replace(' ', '_')}"),
            (qualname, "inspect.callable"),
            signature_text,
        )

        return qual_signature

    def _render(self) -> Iterable[RenderableType]:
        """Render object."""

        def sort_items(item: Tuple[str, Any]) -> Tuple[bool, str]:
            key, (_error, value) = item
            return (callable(value), key.strip("_").lower())

        def safe_getattr(attr_name: str) -> Tuple[Any, Any]:
            """Get attribute or any exception."""
            try:
                return (None, getattr(obj, attr_name))
            except Exception as error:
                return (error, None)

        obj = self.obj
        keys = dir(obj)
        total_items = len(keys)
        if not self.dunder:
            keys = [key for key in keys if not key.startswith("__")]
        if not self.private:
            keys = [key for key in keys if not key.startswith("_")]
        not_shown_count = total_items - len(keys)
        items = [(key, safe_getattr(key)) for key in keys]
        if self.sort:
            items.sort(key=sort_items)

        items_table = Table.grid(padding=(0, 1), expand=False)
        items_table.add_column(justify="right")
        add_row = items_table.add_row
        highlighter = self.highlighter

        if callable(obj):
            signature = self._get_signature("", obj)
            if signature is not None:
                yield signature
                yield ""

        if self.docs:
            _doc = self._get_formatted_doc(obj)
            if _doc is not None:
                doc_text = Text(_doc, style="inspect.help")
                doc_text = highlighter(doc_text)
                yield doc_text
                yield ""

        if self.value and not (isclass(obj) or callable(obj) or ismodule(obj)):
            yield Panel(
                Pretty(obj, indent_guides=True, max_length=10, max_string=60),
                border_style="inspect.value.border",
            )
            yield ""

        for key, (error, value) in items:
            key_text = Text.assemble(
                (
                    key,
                    "inspect.attr.dunder" if key.startswith("__") else "inspect.attr",
                ),
                (" =", "inspect.equals"),
            )
            if error is not None:
                warning = key_text.copy()
                warning.stylize("inspect.error")
                add_row(warning, highlighter(repr(error)))
                continue

            if callable(value):
                if not self.methods:
                    continue

                _signature_text = self._get_signature(key, value)
                if _signature_text is None:
                    add_row(key_text, Pretty(value, highlighter=highlighter))
                else:
                    if self.docs:
                        docs = self._get_formatted_doc(value)
                        if docs is not None:
                            _signature_text.append("\n" if "\n" in docs else " ")
                            doc = highlighter(docs)
                            doc.stylize("inspect.doc")
                            _signature_text.append(doc)

                    add_row(key_text, _signature_text)
            else:
                add_row(key_text, Pretty(value, highlighter=highlighter))
        if items_table.row_count:
            yield items_table
        elif not_shown_count:
            yield Text.from_markup(
                f"[b cyan]{not_shown_count}[/][i] attribute(s) not shown.[/i] "
                f"Run [b][magenta]inspect[/]([not b]inspect[/])[/b] for options."
            )

    def _get_formatted_doc(self, object_: Any) -> Optional[str]:
        """
        Extract the docstring of an object, process it and returns it.
        The processing consists in cleaning up the doctring's indentation,
        taking only its 1st paragraph if `self.help` is not True,
        and escape its control codes.

        Args:
            object_ (Any): the object to get the docstring from.

        Returns:
            Optional[str]: the processed docstring, or None if no docstring was found.
        """
        docs = getdoc(object_)
        if docs is None:
            return None
        docs = cleandoc(docs).strip()
        if not self.help:
            docs = _first_paragraph(docs)
        return escape_control_codes(docs)


def get_object_types_mro(obj: Union[object, Type[Any]]) -> Tuple[type, ...]:
    """Returns the MRO of an object's class, or of the object itself if it's a class."""
    if not hasattr(obj, "__mro__"):
        # N.B. we cannot use `if type(obj) is type` here because it doesn't work with
        # some types of classes, such as the ones that use abc.ABCMeta.
        obj = type(obj)
    return getattr(obj, "__mro__", ())


def get_object_types_mro_as_strings(obj: object) -> Collection[str]:
    """
    Returns the MRO of an object's class as full qualified names, or of the object itself if it's a class.

    Examples:
        `object_types_mro_as_strings(JSONDecoder)` will return `['json.decoder.JSONDecoder', 'builtins.object']`
    """
    return [
        f'{getattr(type_, "__module__", "")}.{getattr(type_, "__qualname__", "")}'
        for type_ in get_object_types_mro(obj)
    ]


def is_object_one_of_types(
    obj: object, fully_qualified_types_names: Collection[str]
) -> bool:
    """
    Returns `True` if the given object's class (or the object itself, if it's a class) has one of the
    fully qualified names in its MRO.
    """
    for type_name in get_object_types_mro_as_strings(obj):
        if type_name in fully_qualified_types_names:
            return True
    return False

# === NexusCore/openenv\Lib\site-packages\aiohttp\abc.py ===
import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from collections.abc import Sized
from http.cookies import BaseCookie, Morsel
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from multidict import CIMultiDict
from yarl import URL

from ._cookie_helpers import parse_set_cookie_headers
from .typedefs import LooseCookies

if TYPE_CHECKING:
    from .web_app import Application
    from .web_exceptions import HTTPException
    from .web_request import BaseRequest, Request
    from .web_response import StreamResponse
else:
    BaseRequest = Request = Application = StreamResponse = None
    HTTPException = None


class AbstractRouter(ABC):
    def __init__(self) -> None:
        self._frozen = False

    def post_init(self, app: Application) -> None:
        """Post init stage.

        Not an abstract method for sake of backward compatibility,
        but if the router wants to be aware of the application
        it can override this.
        """

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        """Freeze router."""
        self._frozen = True

    @abstractmethod
    async def resolve(self, request: Request) -> "AbstractMatchInfo":
        """Return MATCH_INFO for given request"""


class AbstractMatchInfo(ABC):

    __slots__ = ()

    @property  # pragma: no branch
    @abstractmethod
    def handler(self) -> Callable[[Request], Awaitable[StreamResponse]]:
        """Execute matched request handler"""

    @property
    @abstractmethod
    def expect_handler(
        self,
    ) -> Callable[[Request], Awaitable[Optional[StreamResponse]]]:
        """Expect handler for 100-continue processing"""

    @property  # pragma: no branch
    @abstractmethod
    def http_exception(self) -> Optional[HTTPException]:
        """HTTPException instance raised on router's resolving, or None"""

    @abstractmethod  # pragma: no branch
    def get_info(self) -> Dict[str, Any]:
        """Return a dict with additional info useful for introspection"""

    @property  # pragma: no branch
    @abstractmethod
    def apps(self) -> Tuple[Application, ...]:
        """Stack of nested applications.

        Top level application is left-most element.

        """

    @abstractmethod
    def add_app(self, app: Application) -> None:
        """Add application to the nested apps stack."""

    @abstractmethod
    def freeze(self) -> None:
        """Freeze the match info.

        The method is called after route resolution.

        After the call .add_app() is forbidden.

        """


class AbstractView(ABC):
    """Abstract class based view."""

    def __init__(self, request: Request) -> None:
        self._request = request

    @property
    def request(self) -> Request:
        """Request instance."""
        return self._request

    @abstractmethod
    def __await__(self) -> Generator[Any, None, StreamResponse]:
        """Execute the view handler."""


class ResolveResult(TypedDict):
    """Resolve result.

    This is the result returned from an AbstractResolver's
    resolve method.

    :param hostname: The hostname that was provided.
    :param host: The IP address that was resolved.
    :param port: The port that was resolved.
    :param family: The address family that was resolved.
    :param proto: The protocol that was resolved.
    :param flags: The flags that were resolved.
    """

    hostname: str
    host: str
    port: int
    family: int
    proto: int
    flags: int


class AbstractResolver(ABC):
    """Abstract DNS resolver."""

    @abstractmethod
    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        """Return IP address for given hostname"""

    @abstractmethod
    async def close(self) -> None:
        """Release resolver"""


if TYPE_CHECKING:
    IterableBase = Iterable[Morsel[str]]
else:
    IterableBase = Iterable


ClearCookiePredicate = Callable[["Morsel[str]"], bool]


class AbstractCookieJar(Sized, IterableBase):
    """Abstract Cookie Jar."""

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_running_loop()

    @property
    @abstractmethod
    def quote_cookie(self) -> bool:
        """Return True if cookies should be quoted."""

    @abstractmethod
    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        """Clear all cookies if no predicate is passed."""

    @abstractmethod
    def clear_domain(self, domain: str) -> None:
        """Clear all cookies for domain and all subdomains."""

    @abstractmethod
    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        """Update cookies."""

    def update_cookies_from_headers(
        self, headers: Sequence[str], response_url: URL
    ) -> None:
        """Update cookies from raw Set-Cookie headers."""
        if headers and (cookies_to_update := parse_set_cookie_headers(headers)):
            self.update_cookies(cookies_to_update, response_url)

    @abstractmethod
    def filter_cookies(self, request_url: URL) -> "BaseCookie[str]":
        """Return the jar's cookies filtered by their attributes."""


class AbstractStreamWriter(ABC):
    """Abstract stream writer."""

    buffer_size: int = 0
    output_size: int = 0
    length: Optional[int] = 0

    @abstractmethod
    async def write(self, chunk: Union[bytes, bytearray, memoryview]) -> None:
        """Write chunk into stream."""

    @abstractmethod
    async def write_eof(self, chunk: bytes = b"") -> None:
        """Write last chunk."""

    @abstractmethod
    async def drain(self) -> None:
        """Flush the write buffer."""

    @abstractmethod
    def enable_compression(
        self, encoding: str = "deflate", strategy: Optional[int] = None
    ) -> None:
        """Enable HTTP body compression"""

    @abstractmethod
    def enable_chunking(self) -> None:
        """Enable HTTP chunked mode"""

    @abstractmethod
    async def write_headers(
        self, status_line: str, headers: "CIMultiDict[str]"
    ) -> None:
        """Write HTTP headers"""

    def send_headers(self) -> None:
        """Force sending buffered headers if not already sent.

        Required only if write_headers() buffers headers instead of sending immediately.
        For backwards compatibility, this method does nothing by default.
        """


class AbstractAccessLogger(ABC):
    """Abstract writer to access log."""

    __slots__ = ("logger", "log_format")

    def __init__(self, logger: logging.Logger, log_format: str) -> None:
        self.logger = logger
        self.log_format = log_format

    @abstractmethod
    def log(self, request: BaseRequest, response: StreamResponse, time: float) -> None:
        """Emit log to logger."""

    @property
    def enabled(self) -> bool:
        """Check if logger is enabled."""
        return True

# === NexusCore/openenv\Lib\site-packages\rich\_inspect.py ===
import inspect
from inspect import cleandoc, getdoc, getfile, isclass, ismodule, signature
from typing import Any, Collection, Iterable, Optional, Tuple, Type, Union

from .console import Group, RenderableType
from .control import escape_control_codes
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin
from .panel import Panel
from .pretty import Pretty
from .table import Table
from .text import Text, TextType


def _first_paragraph(doc: str) -> str:
    """Get the first paragraph from a docstring."""
    paragraph, _, _ = doc.partition("\n\n")
    return paragraph


class Inspect(JupyterMixin):
    """A renderable to inspect any Python Object.

    Args:
        obj (Any): An object to inspect.
        title (str, optional): Title to display over inspect result, or None use type. Defaults to None.
        help (bool, optional): Show full help text rather than just first paragraph. Defaults to False.
        methods (bool, optional): Enable inspection of callables. Defaults to False.
        docs (bool, optional): Also render doc strings. Defaults to True.
        private (bool, optional): Show private attributes (beginning with underscore). Defaults to False.
        dunder (bool, optional): Show attributes starting with double underscore. Defaults to False.
        sort (bool, optional): Sort attributes alphabetically. Defaults to True.
        all (bool, optional): Show all attributes. Defaults to False.
        value (bool, optional): Pretty print value of object. Defaults to True.
    """

    def __init__(
        self,
        obj: Any,
        *,
        title: Optional[TextType] = None,
        help: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all: bool = True,
        value: bool = True,
    ) -> None:
        self.highlighter = ReprHighlighter()
        self.obj = obj
        self.title = title or self._make_title(obj)
        if all:
            methods = private = dunder = True
        self.help = help
        self.methods = methods
        self.docs = docs or help
        self.private = private or dunder
        self.dunder = dunder
        self.sort = sort
        self.value = value

    def _make_title(self, obj: Any) -> Text:
        """Make a default title."""
        title_str = (
            str(obj)
            if (isclass(obj) or callable(obj) or ismodule(obj))
            else str(type(obj))
        )
        title_text = self.highlighter(title_str)
        return title_text

    def __rich__(self) -> Panel:
        return Panel.fit(
            Group(*self._render()),
            title=self.title,
            border_style="scope.border",
            padding=(0, 1),
        )

    def _get_signature(self, name: str, obj: Any) -> Optional[Text]:
        """Get a signature for a callable."""
        try:
            _signature = str(signature(obj)) + ":"
        except ValueError:
            _signature = "(...)"
        except TypeError:
            return None

        source_filename: Optional[str] = None
        try:
            source_filename = getfile(obj)
        except (OSError, TypeError):
            # OSError is raised if obj has no source file, e.g. when defined in REPL.
            pass

        callable_name = Text(name, style="inspect.callable")
        if source_filename:
            callable_name.stylize(f"link file://{source_filename}")
        signature_text = self.highlighter(_signature)

        qualname = name or getattr(obj, "__qualname__", name)

        # If obj is a module, there may be classes (which are callable) to display
        if inspect.isclass(obj):
            prefix = "class"
        elif inspect.iscoroutinefunction(obj):
            prefix = "async def"
        else:
            prefix = "def"

        qual_signature = Text.assemble(
            (f"{prefix} ", f"inspect.{prefix.replace(' ', '_')}"),
            (qualname, "inspect.callable"),
            signature_text,
        )

        return qual_signature

    def _render(self) -> Iterable[RenderableType]:
        """Render object."""

        def sort_items(item: Tuple[str, Any]) -> Tuple[bool, str]:
            key, (_error, value) = item
            return (callable(value), key.strip("_").lower())

        def safe_getattr(attr_name: str) -> Tuple[Any, Any]:
            """Get attribute or any exception."""
            try:
                return (None, getattr(obj, attr_name))
            except Exception as error:
                return (error, None)

        obj = self.obj
        keys = dir(obj)
        total_items = len(keys)
        if not self.dunder:
            keys = [key for key in keys if not key.startswith("__")]
        if not self.private:
            keys = [key for key in keys if not key.startswith("_")]
        not_shown_count = total_items - len(keys)
        items = [(key, safe_getattr(key)) for key in keys]
        if self.sort:
            items.sort(key=sort_items)

        items_table = Table.grid(padding=(0, 1), expand=False)
        items_table.add_column(justify="right")
        add_row = items_table.add_row
        highlighter = self.highlighter

        if callable(obj):
            signature = self._get_signature("", obj)
            if signature is not None:
                yield signature
                yield ""

        if self.docs:
            _doc = self._get_formatted_doc(obj)
            if _doc is not None:
                doc_text = Text(_doc, style="inspect.help")
                doc_text = highlighter(doc_text)
                yield doc_text
                yield ""

        if self.value and not (isclass(obj) or callable(obj) or ismodule(obj)):
            yield Panel(
                Pretty(obj, indent_guides=True, max_length=10, max_string=60),
                border_style="inspect.value.border",
            )
            yield ""

        for key, (error, value) in items:
            key_text = Text.assemble(
                (
                    key,
                    "inspect.attr.dunder" if key.startswith("__") else "inspect.attr",
                ),
                (" =", "inspect.equals"),
            )
            if error is not None:
                warning = key_text.copy()
                warning.stylize("inspect.error")
                add_row(warning, highlighter(repr(error)))
                continue

            if callable(value):
                if not self.methods:
                    continue

                _signature_text = self._get_signature(key, value)
                if _signature_text is None:
                    add_row(key_text, Pretty(value, highlighter=highlighter))
                else:
                    if self.docs:
                        docs = self._get_formatted_doc(value)
                        if docs is not None:
                            _signature_text.append("\n" if "\n" in docs else " ")
                            doc = highlighter(docs)
                            doc.stylize("inspect.doc")
                            _signature_text.append(doc)

                    add_row(key_text, _signature_text)
            else:
                add_row(key_text, Pretty(value, highlighter=highlighter))
        if items_table.row_count:
            yield items_table
        elif not_shown_count:
            yield Text.from_markup(
                f"[b cyan]{not_shown_count}[/][i] attribute(s) not shown.[/i] "
                f"Run [b][magenta]inspect[/]([not b]inspect[/])[/b] for options."
            )

    def _get_formatted_doc(self, object_: Any) -> Optional[str]:
        """
        Extract the docstring of an object, process it and returns it.
        The processing consists in cleaning up the doctring's indentation,
        taking only its 1st paragraph if `self.help` is not True,
        and escape its control codes.

        Args:
            object_ (Any): the object to get the docstring from.

        Returns:
            Optional[str]: the processed docstring, or None if no docstring was found.
        """
        docs = getdoc(object_)
        if docs is None:
            return None
        docs = cleandoc(docs).strip()
        if not self.help:
            docs = _first_paragraph(docs)
        return escape_control_codes(docs)


def get_object_types_mro(obj: Union[object, Type[Any]]) -> Tuple[type, ...]:
    """Returns the MRO of an object's class, or of the object itself if it's a class."""
    if not hasattr(obj, "__mro__"):
        # N.B. we cannot use `if type(obj) is type` here because it doesn't work with
        # some types of classes, such as the ones that use abc.ABCMeta.
        obj = type(obj)
    return getattr(obj, "__mro__", ())


def get_object_types_mro_as_strings(obj: object) -> Collection[str]:
    """
    Returns the MRO of an object's class as full qualified names, or of the object itself if it's a class.

    Examples:
        `object_types_mro_as_strings(JSONDecoder)` will return `['json.decoder.JSONDecoder', 'builtins.object']`
    """
    return [
        f'{getattr(type_, "__module__", "")}.{getattr(type_, "__qualname__", "")}'
        for type_ in get_object_types_mro(obj)
    ]


def is_object_one_of_types(
    obj: object, fully_qualified_types_names: Collection[str]
) -> bool:
    """
    Returns `True` if the given object's class (or the object itself, if it's a class) has one of the
    fully qualified names in its MRO.
    """
    for type_name in get_object_types_mro_as_strings(obj):
        if type_name in fully_qualified_types_names:
            return True
    return False

# === NexusCore/openenv\Lib\site-packages\tornado\wsgi.py ===
#
# Copyright 2009 Facebook
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

"""WSGI support for the Tornado web framework.

WSGI is the Python standard for web servers, and allows for interoperability
between Tornado and other Python web frameworks and servers.

This module provides WSGI support via the `WSGIContainer` class, which
makes it possible to run applications using other WSGI frameworks on
the Tornado HTTP server. The reverse is not supported; the Tornado
`.Application` and `.RequestHandler` classes are designed for use with
the Tornado `.HTTPServer` and cannot be used in a generic WSGI
container.

"""

import concurrent.futures
from io import BytesIO
import tornado
import sys

from tornado.concurrent import dummy_executor
from tornado import escape
from tornado import httputil
from tornado.ioloop import IOLoop
from tornado.log import access_log

from typing import List, Tuple, Optional, Callable, Any, Dict
from types import TracebackType
import typing

if typing.TYPE_CHECKING:
    from typing import Type  # noqa: F401
    from _typeshed.wsgi import WSGIApplication as WSGIAppType  # noqa: F401


# PEP 3333 specifies that WSGI on python 3 generally deals with byte strings
# that are smuggled inside objects of type unicode (via the latin1 encoding).
# This function is like those in the tornado.escape module, but defined
# here to minimize the temptation to use it in non-wsgi contexts.
def to_wsgi_str(s: bytes) -> str:
    assert isinstance(s, bytes)
    return s.decode("latin1")


class WSGIContainer:
    r"""Makes a WSGI-compatible application runnable on Tornado's HTTP server.

    .. warning::

       WSGI is a *synchronous* interface, while Tornado's concurrency model
       is based on single-threaded *asynchronous* execution.  Many of Tornado's
       distinguishing features are not available in WSGI mode, including efficient
       long-polling and websockets. The primary purpose of `WSGIContainer` is
       to support both WSGI applications and native Tornado ``RequestHandlers`` in
       a single process. WSGI-only applications are likely to be better off
       with a dedicated WSGI server such as ``gunicorn`` or ``uwsgi``.

    Wrap a WSGI application in a `WSGIContainer` to make it implement the Tornado
    `.HTTPServer` ``request_callback`` interface.  The `WSGIContainer` object can
    then be passed to classes from the `tornado.routing` module,
    `tornado.web.FallbackHandler`, or to `.HTTPServer` directly.

    This class is intended to let other frameworks (Django, Flask, etc)
    run on the Tornado HTTP server and I/O loop.

    Realistic usage will be more complicated, but the simplest possible example uses a
    hand-written WSGI application with `.HTTPServer`::

        def simple_app(environ, start_response):
            status = "200 OK"
            response_headers = [("Content-type", "text/plain")]
            start_response(status, response_headers)
            return [b"Hello world!\n"]

        async def main():
            container = tornado.wsgi.WSGIContainer(simple_app)
            http_server = tornado.httpserver.HTTPServer(container)
            http_server.listen(8888)
            await asyncio.Event().wait()

        asyncio.run(main())

    The recommended pattern is to use the `tornado.routing` module to set up routing
    rules between your WSGI application and, typically, a `tornado.web.Application`.
    Alternatively, `tornado.web.Application` can be used as the top-level router
    and `tornado.web.FallbackHandler` can embed a `WSGIContainer` within it.

    If the ``executor`` argument is provided, the WSGI application will be executed
    on that executor. This must be an instance of `concurrent.futures.Executor`,
    typically a ``ThreadPoolExecutor`` (``ProcessPoolExecutor`` is not supported).
    If no ``executor`` is given, the application will run on the event loop thread in
    Tornado 6.3; this will change to use an internal thread pool by default in
    Tornado 7.0.

    .. warning::
       By default, the WSGI application is executed on the event loop's thread. This
       limits the server to one request at a time (per process), making it less scalable
       than most other WSGI servers. It is therefore highly recommended that you pass
       a ``ThreadPoolExecutor`` when constructing the `WSGIContainer`, after verifying
       that your application is thread-safe. The default will change to use a
       ``ThreadPoolExecutor`` in Tornado 7.0.

    .. versionadded:: 6.3
       The ``executor`` parameter.

    .. deprecated:: 6.3
       The default behavior of running the WSGI application on the event loop thread
       is deprecated and will change in Tornado 7.0 to use a thread pool by default.
    """

    def __init__(
        self,
        wsgi_application: "WSGIAppType",
        executor: Optional[concurrent.futures.Executor] = None,
    ) -> None:
        self.wsgi_application = wsgi_application
        self.executor = dummy_executor if executor is None else executor

    def __call__(self, request: httputil.HTTPServerRequest) -> None:
        IOLoop.current().spawn_callback(self.handle_request, request)

    async def handle_request(self, request: httputil.HTTPServerRequest) -> None:
        data = {}  # type: Dict[str, Any]
        response = []  # type: List[bytes]

        def start_response(
            status: str,
            headers: List[Tuple[str, str]],
            exc_info: Optional[
                Tuple[
                    "Optional[Type[BaseException]]",
                    Optional[BaseException],
                    Optional[TracebackType],
                ]
            ] = None,
        ) -> Callable[[bytes], Any]:
            data["status"] = status
            data["headers"] = headers
            return response.append

        loop = IOLoop.current()
        app_response = await loop.run_in_executor(
            self.executor,
            self.wsgi_application,
            self.environ(request),
            start_response,
        )
        try:
            app_response_iter = iter(app_response)

            def next_chunk() -> Optional[bytes]:
                try:
                    return next(app_response_iter)
                except StopIteration:
                    # StopIteration is special and is not allowed to pass through
                    # coroutines normally.
                    return None

            while True:
                chunk = await loop.run_in_executor(self.executor, next_chunk)
                if chunk is None:
                    break
                response.append(chunk)
        finally:
            if hasattr(app_response, "close"):
                app_response.close()  # type: ignore
        body = b"".join(response)
        if not data:
            raise Exception("WSGI app did not call start_response")

        status_code_str, reason = data["status"].split(" ", 1)
        status_code = int(status_code_str)
        headers = data["headers"]  # type: List[Tuple[str, str]]
        header_set = {k.lower() for (k, v) in headers}
        body = escape.utf8(body)
        if status_code != 304:
            if "content-length" not in header_set:
                headers.append(("Content-Length", str(len(body))))
            if "content-type" not in header_set:
                headers.append(("Content-Type", "text/html; charset=UTF-8"))
        if "server" not in header_set:
            headers.append(("Server", "TornadoServer/%s" % tornado.version))

        start_line = httputil.ResponseStartLine("HTTP/1.1", status_code, reason)
        header_obj = httputil.HTTPHeaders()
        for key, value in headers:
            header_obj.add(key, value)
        assert request.connection is not None
        request.connection.write_headers(start_line, header_obj, chunk=body)
        request.connection.finish()
        self._log(status_code, request)

    def environ(self, request: httputil.HTTPServerRequest) -> Dict[str, Any]:
        """Converts a `tornado.httputil.HTTPServerRequest` to a WSGI environment.

        .. versionchanged:: 6.3
           No longer a static method.
        """
        hostport = request.host.split(":")
        if len(hostport) == 2:
            host = hostport[0]
            port = int(hostport[1])
        else:
            host = request.host
            port = 443 if request.protocol == "https" else 80
        environ = {
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": "",
            "PATH_INFO": to_wsgi_str(
                escape.url_unescape(request.path, encoding=None, plus=False)
            ),
            "QUERY_STRING": request.query,
            "REMOTE_ADDR": request.remote_ip,
            "SERVER_NAME": host,
            "SERVER_PORT": str(port),
            "SERVER_PROTOCOL": request.version,
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.protocol,
            "wsgi.input": BytesIO(escape.utf8(request.body)),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": self.executor is not dummy_executor,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
        }
        if "Content-Type" in request.headers:
            environ["CONTENT_TYPE"] = request.headers.pop("Content-Type")
        if "Content-Length" in request.headers:
            environ["CONTENT_LENGTH"] = request.headers.pop("Content-Length")
        for key, value in request.headers.items():
            environ["HTTP_" + key.replace("-", "_").upper()] = value
        return environ

    def _log(self, status_code: int, request: httputil.HTTPServerRequest) -> None:
        if status_code < 400:
            log_method = access_log.info
        elif status_code < 500:
            log_method = access_log.warning
        else:
            log_method = access_log.error
        request_time = 1000.0 * request.request_time()
        assert request.method is not None
        assert request.uri is not None
        summary = (
            request.method  # type: ignore[operator]
            + " "
            + request.uri
            + " ("
            + request.remote_ip
            + ")"
        )
        log_method("%d %s %.2fms", status_code, summary, request_time)


HTTPRequest = httputil.HTTPServerRequest

# === NexusCore/openenv\Lib\site-packages\gitdb\db\loose.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
from contextlib import suppress

from gitdb.db.base import (
    FileDBBase,
    ObjectDBR,
    ObjectDBW
)

from gitdb.exc import (
    BadObject,
    AmbiguousObjectName
)

from gitdb.stream import (
    DecompressMemMapReader,
    FDCompressedSha1Writer,
    FDStream,
    Sha1Writer
)

from gitdb.base import (
    OStream,
    OInfo
)

from gitdb.util import (
    file_contents_ro_filepath,
    ENOENT,
    hex_to_bin,
    bin_to_hex,
    exists,
    chmod,
    isfile,
    remove,
    rename,
    dirname,
    basename,
    join
)

from gitdb.fun import (
    chunk_size,
    loose_object_header_info,
    write_object,
    stream_copy
)

from gitdb.utils.encoding import force_bytes

import tempfile
import os
import sys
import time


__all__ = ('LooseObjectDB', )


class LooseObjectDB(FileDBBase, ObjectDBR, ObjectDBW):

    """A database which operates on loose object files"""

    # CONFIGURATION
    # chunks in which data will be copied between streams
    stream_chunk_size = chunk_size

    # On windows we need to keep it writable, otherwise it cannot be removed
    # either
    new_objects_mode = int("444", 8)
    if os.name == 'nt':
        new_objects_mode = int("644", 8)

    def __init__(self, root_path):
        super().__init__(root_path)
        self._hexsha_to_file = dict()
        # Additional Flags - might be set to 0 after the first failure
        # Depending on the root, this might work for some mounts, for others not, which
        # is why it is per instance
        self._fd_open_flags = getattr(os, 'O_NOATIME', 0)

    #{ Interface
    def object_path(self, hexsha):
        """
        :return: path at which the object with the given hexsha would be stored,
            relative to the database root"""
        return join(hexsha[:2], hexsha[2:])

    def readable_db_object_path(self, hexsha):
        """
        :return: readable object path to the object identified by hexsha
        :raise BadObject: If the object file does not exist"""
        with suppress(KeyError):
            return self._hexsha_to_file[hexsha]
        # END ignore cache misses

        # try filesystem
        path = self.db_path(self.object_path(hexsha))
        if exists(path):
            self._hexsha_to_file[hexsha] = path
            return path
        # END handle cache
        raise BadObject(hexsha)

    def partial_to_complete_sha_hex(self, partial_hexsha):
        """:return: 20 byte binary sha1 string which matches the given name uniquely
        :param name: hexadecimal partial name (bytes or ascii string)
        :raise AmbiguousObjectName:
        :raise BadObject: """
        candidate = None
        for binsha in self.sha_iter():
            if bin_to_hex(binsha).startswith(force_bytes(partial_hexsha)):
                # it can't ever find the same object twice
                if candidate is not None:
                    raise AmbiguousObjectName(partial_hexsha)
                candidate = binsha
        # END for each object
        if candidate is None:
            raise BadObject(partial_hexsha)
        return candidate

    #} END interface

    def _map_loose_object(self, sha):
        """
        :return: memory map of that file to allow random read access
        :raise BadObject: if object could not be located"""
        db_path = self.db_path(self.object_path(bin_to_hex(sha)))
        try:
            return file_contents_ro_filepath(db_path, flags=self._fd_open_flags)
        except OSError as e:
            if e.errno != ENOENT:
                # try again without noatime
                try:
                    return file_contents_ro_filepath(db_path)
                except OSError as new_e:
                    raise BadObject(sha) from new_e
                # didn't work because of our flag, don't try it again
                self._fd_open_flags = 0
            else:
                raise BadObject(sha) from e
            # END handle error
        # END exception handling

    def set_ostream(self, stream):
        """:raise TypeError: if the stream does not support the Sha1Writer interface"""
        if stream is not None and not isinstance(stream, Sha1Writer):
            raise TypeError("Output stream musst support the %s interface" % Sha1Writer.__name__)
        return super().set_ostream(stream)

    def info(self, sha):
        m = self._map_loose_object(sha)
        try:
            typ, size = loose_object_header_info(m)
            return OInfo(sha, typ, size)
        finally:
            if hasattr(m, 'close'):
                m.close()
        # END assure release of system resources

    def stream(self, sha):
        m = self._map_loose_object(sha)
        type, size, stream = DecompressMemMapReader.new(m, close_on_deletion=True)
        return OStream(sha, type, size, stream)

    def has_object(self, sha):
        try:
            self.readable_db_object_path(bin_to_hex(sha))
            return True
        except BadObject:
            return False
        # END check existence

    def store(self, istream):
        """note: The sha we produce will be hex by nature"""
        tmp_path = None
        writer = self.ostream()
        if writer is None:
            # open a tmp file to write the data to
            fd, tmp_path = tempfile.mkstemp(prefix='obj', dir=self._root_path)

            if istream.binsha is None:
                writer = FDCompressedSha1Writer(fd)
            else:
                writer = FDStream(fd)
            # END handle direct stream copies
        # END handle custom writer

        try:
            try:
                if istream.binsha is not None:
                    # copy as much as possible, the actual uncompressed item size might
                    # be smaller than the compressed version
                    stream_copy(istream.read, writer.write, sys.maxsize, self.stream_chunk_size)
                else:
                    # write object with header, we have to make a new one
                    write_object(istream.type, istream.size, istream.read, writer.write,
                                 chunk_size=self.stream_chunk_size)
                # END handle direct stream copies
            finally:
                if tmp_path:
                    writer.close()
            # END assure target stream is closed
        except:
            if tmp_path:
                remove(tmp_path)
            raise
        # END assure tmpfile removal on error

        hexsha = None
        if istream.binsha:
            hexsha = istream.hexsha
        else:
            hexsha = writer.sha(as_hex=True)
        # END handle sha

        if tmp_path:
            obj_path = self.db_path(self.object_path(hexsha))
            obj_dir = dirname(obj_path)
            os.makedirs(obj_dir, exist_ok=True)
            # END handle destination directory
            # rename onto existing doesn't work on NTFS
            if isfile(obj_path):
                remove(tmp_path)
            else:
                rename(tmp_path, obj_path)
            # end rename only if needed

            # Ensure rename is actually done and file is stable
            # Retry up to 14 times - exponential wait & retry in ms.
            # The total maximum wait time is 1000ms, which should be vastly enough for the
            # OS to return and commit the file to disk.
            for exp_backoff_ms in [1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 181]:
                with suppress(PermissionError):
                    # make sure its readable for all ! It started out as rw-- tmp file
                    # but needs to be rwrr
                    chmod(obj_path, self.new_objects_mode)
                    break
                time.sleep(exp_backoff_ms / 1000.0)
            else:
                raise PermissionError(
                    "Impossible to apply `chmod` to file {}".format(obj_path)
                )

        # END handle dry_run

        istream.binsha = hex_to_bin(hexsha)
        return istream

    def sha_iter(self):
        # find all files which look like an object, extract sha from there
        for root, dirs, files in os.walk(self.root_path()):
            root_base = basename(root)
            if len(root_base) != 2:
                continue

            for f in files:
                if len(f) != 38:
                    continue
                yield hex_to_bin(root_base + f)
            # END for each file
        # END for each walk iteration

    def size(self):
        return len(tuple(self.sha_iter()))