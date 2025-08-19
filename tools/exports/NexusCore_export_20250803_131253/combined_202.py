
# === NexusCore/tools\exports\export_20250803_114325\combined_232.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_plugins\extensions\types\pydevd_plugin_pandas_types.py ===
import sys

from _pydevd_bundle.pydevd_constants import PANDAS_MAX_ROWS, PANDAS_MAX_COLS, PANDAS_MAX_COLWIDTH
from _pydevd_bundle.pydevd_extension_api import TypeResolveProvider, StrPresentationProvider
from _pydevd_bundle.pydevd_resolver import inspect, MethodWrapperType
from _pydevd_bundle.pydevd_utils import Timer

from .pydevd_helpers import find_mod_attr
from contextlib import contextmanager


def _get_dictionary(obj, replacements):
    ret = dict()
    cls = obj.__class__
    for attr_name in dir(obj):
        # This is interesting but it actually hides too much info from the dataframe.
        # attr_type_in_cls = type(getattr(cls, attr_name, None))
        # if attr_type_in_cls == property:
        #     ret[attr_name] = '<property (not computed)>'
        #     continue

        timer = Timer()
        try:
            replacement = replacements.get(attr_name)
            if replacement is not None:
                ret[attr_name] = replacement
                continue

            attr_value = getattr(obj, attr_name, "<unable to get>")
            if inspect.isroutine(attr_value) or isinstance(attr_value, MethodWrapperType):
                continue
            ret[attr_name] = attr_value
        except Exception as e:
            ret[attr_name] = "<error getting: %s>" % (e,)
        finally:
            timer.report_if_getting_attr_slow(cls, attr_name)

    return ret


@contextmanager
def customize_pandas_options():
    # The default repr depends on the settings of:
    #
    # pandas.set_option('display.max_columns', None)
    # pandas.set_option('display.max_rows', None)
    #
    # which can make the repr **very** slow on some cases, so, we customize pandas to have
    # smaller values if the current values are too big.
    custom_options = []

    from pandas import get_option

    max_rows = get_option("display.max_rows")
    max_cols = get_option("display.max_columns")
    max_colwidth = get_option("display.max_colwidth")

    if max_rows is None or max_rows > PANDAS_MAX_ROWS:
        custom_options.append("display.max_rows")
        custom_options.append(PANDAS_MAX_ROWS)

    if max_cols is None or max_cols > PANDAS_MAX_COLS:
        custom_options.append("display.max_columns")
        custom_options.append(PANDAS_MAX_COLS)

    if max_colwidth is None or max_colwidth > PANDAS_MAX_COLWIDTH:
        custom_options.append("display.max_colwidth")
        custom_options.append(PANDAS_MAX_COLWIDTH)

    if custom_options:
        from pandas import option_context

        with option_context(*custom_options):
            yield
    else:
        yield


class PandasDataFrameTypeResolveProvider(object):
    def can_provide(self, type_object, type_name):
        data_frame_class = find_mod_attr("pandas.core.frame", "DataFrame")
        return data_frame_class is not None and issubclass(type_object, data_frame_class)

    def resolve(self, obj, attribute):
        return getattr(obj, attribute)

    def get_dictionary(self, obj):
        replacements = {
            # This actually calls: DataFrame.transpose(), which can be expensive, so,
            # let's just add some string representation for it.
            "T": "<transposed dataframe -- debugger:skipped eval>",
            # This creates a whole new dict{index: Series) for each column. Doing a
            # subsequent repr() from this dict can be very slow, so, don't return it.
            "_series": "<dict[index:Series] -- debugger:skipped eval>",
            "style": "<pandas.io.formats.style.Styler -- debugger: skipped eval>",
        }
        return _get_dictionary(obj, replacements)

    def get_str_in_context(self, df, context: str):
        """
        :param context:
            This is the context in which the variable is being requested. Valid values:
                "watch",
                "repl",
                "hover",
                "clipboard"
        """
        if context in ("repl", "clipboard"):
            return repr(df)
        return self.get_str(df)

    def get_str(self, df):
        with customize_pandas_options():
            return repr(df)


class PandasSeriesTypeResolveProvider(object):
    def can_provide(self, type_object, type_name):
        series_class = find_mod_attr("pandas.core.series", "Series")
        return series_class is not None and issubclass(type_object, series_class)

    def resolve(self, obj, attribute):
        return getattr(obj, attribute)

    def get_dictionary(self, obj):
        replacements = {
            # This actually calls: DataFrame.transpose(), which can be expensive, so,
            # let's just add some string representation for it.
            "T": "<transposed dataframe -- debugger:skipped eval>",
            # This creates a whole new dict{index: Series) for each column. Doing a
            # subsequent repr() from this dict can be very slow, so, don't return it.
            "_series": "<dict[index:Series] -- debugger:skipped eval>",
            "style": "<pandas.io.formats.style.Styler -- debugger: skipped eval>",
        }
        return _get_dictionary(obj, replacements)

    def get_str_in_context(self, df, context: str):
        """
        :param context:
            This is the context in which the variable is being requested. Valid values:
                "watch",
                "repl",
                "hover",
                "clipboard"
        """
        if context in ("repl", "clipboard"):
            return repr(df)
        return self.get_str(df)

    def get_str(self, series):
        with customize_pandas_options():
            return repr(series)


class PandasStylerTypeResolveProvider(object):
    def can_provide(self, type_object, type_name):
        series_class = find_mod_attr("pandas.io.formats.style", "Styler")
        return series_class is not None and issubclass(type_object, series_class)

    def resolve(self, obj, attribute):
        return getattr(obj, attribute)

    def get_dictionary(self, obj):
        replacements = {
            "data": "<Styler data -- debugger:skipped eval>",
            "__dict__": "<dict -- debugger: skipped eval>",
        }
        return _get_dictionary(obj, replacements)


if not sys.platform.startswith("java"):
    TypeResolveProvider.register(PandasDataFrameTypeResolveProvider)
    StrPresentationProvider.register(PandasDataFrameTypeResolveProvider)

    TypeResolveProvider.register(PandasSeriesTypeResolveProvider)
    StrPresentationProvider.register(PandasSeriesTypeResolveProvider)

    TypeResolveProvider.register(PandasStylerTypeResolveProvider)

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\conftest.py ===
import pytest
import sys
import matplotlib
from matplotlib import _api


def pytest_configure(config):
    # config is initialized here rather than in pytest.ini so that `pytest
    # --pyargs matplotlib` (which would not find pytest.ini) works.  The only
    # entries in pytest.ini set minversion (which is checked earlier),
    # testpaths/python_files, as they are required to properly find the tests
    for key, value in [
        ("markers", "flaky: (Provided by pytest-rerunfailures.)"),
        ("markers", "timeout: (Provided by pytest-timeout.)"),
        ("markers", "backend: Set alternate Matplotlib backend temporarily."),
        ("markers", "baseline_images: Compare output against references."),
        ("markers", "pytz: Tests that require pytz to be installed."),
        ("filterwarnings", "error"),
        ("filterwarnings",
         "ignore:.*The py23 module has been deprecated:DeprecationWarning"),
        ("filterwarnings",
         r"ignore:DynamicImporter.find_spec\(\) not found; "
         r"falling back to find_module\(\):ImportWarning"),
    ]:
        config.addinivalue_line(key, value)

    matplotlib.use('agg', force=True)
    matplotlib._called_from_pytest = True
    matplotlib._init_tests()


def pytest_unconfigure(config):
    matplotlib._called_from_pytest = False


@pytest.fixture(autouse=True)
def mpl_test_settings(request):
    from matplotlib.testing.decorators import _cleanup_cm

    with _cleanup_cm():

        backend = None
        backend_marker = request.node.get_closest_marker('backend')
        prev_backend = matplotlib.get_backend()
        if backend_marker is not None:
            assert len(backend_marker.args) == 1, \
                "Marker 'backend' must specify 1 backend."
            backend, = backend_marker.args
            skip_on_importerror = backend_marker.kwargs.get(
                'skip_on_importerror', False)

            # special case Qt backend importing to avoid conflicts
            if backend.lower().startswith('qt5'):
                if any(sys.modules.get(k) for k in ('PyQt4', 'PySide')):
                    pytest.skip('Qt4 binding already imported')

        matplotlib.testing.setup()
        with _api.suppress_matplotlib_deprecation_warning():
            if backend is not None:
                # This import must come after setup() so it doesn't load the
                # default backend prematurely.
                import matplotlib.pyplot as plt
                try:
                    plt.switch_backend(backend)
                except ImportError as exc:
                    # Should only occur for the cairo backend tests, if neither
                    # pycairo nor cairocffi are installed.
                    if 'cairo' in backend.lower() or skip_on_importerror:
                        pytest.skip("Failed to switch to backend "
                                    f"{backend} ({exc}).")
                    else:
                        raise
            # Default of cleanup and image_comparison too.
            matplotlib.style.use(["classic", "_classic_test_patch"])
        try:
            yield
        finally:
            if backend is not None:
                plt.close("all")
                matplotlib.use(prev_backend)


@pytest.fixture
def pd():
    """
    Fixture to import and configure pandas. Using this fixture, the test is skipped when
    pandas is not installed. Use this fixture instead of importing pandas in test files.

    Examples
    --------
    Request the pandas fixture by passing in ``pd`` as an argument to the test ::

        def test_matshow_pandas(pd):

            df = pd.DataFrame({'x':[1,2,3], 'y':[4,5,6]})
            im = plt.figure().subplots().matshow(df)
            np.testing.assert_array_equal(im.get_array(), df)
    """
    pd = pytest.importorskip('pandas')
    try:
        from pandas.plotting import (
            deregister_matplotlib_converters as deregister)
        deregister()
    except ImportError:
        pass
    return pd


@pytest.fixture
def xr():
    """
    Fixture to import xarray so that the test is skipped when xarray is not installed.
    Use this fixture instead of importing xrray in test files.

    Examples
    --------
    Request the xarray fixture by passing in ``xr`` as an argument to the test ::

        def test_imshow_xarray(xr):

            ds = xr.DataArray(np.random.randn(2, 3))
            im = plt.figure().subplots().imshow(ds)
            np.testing.assert_array_equal(im.get_array(), ds)
    """

    xr = pytest.importorskip('xarray')
    return xr


@pytest.fixture
def text_placeholders(monkeypatch):
    """
    Replace texts with placeholder rectangles.

    The rectangle size only depends on the font size and the number of characters. It is
    thus insensitive to font properties and rendering details. This should be used for
    tests that depend on text geometries but not the actual text rendering, e.g. layout
    tests.
    """
    from matplotlib.patches import Rectangle

    def patched_get_text_metrics_with_cache(renderer, text, fontprop, ismath, dpi):
        """
        Replace ``_get_text_metrics_with_cache`` with fixed results.

        The usual ``renderer.get_text_width_height_descent`` would depend on font
        metrics; instead the fixed results are based on font size and the length of the
        string only.
        """
        # While get_window_extent returns pixels and font size is in points, font size
        # includes ascenders and descenders. Leaving out this factor and setting
        # descent=0 ends up with a box that is relatively close to DejaVu Sans.
        height = fontprop.get_size()
        width = len(text) * height / 1.618  # Golden ratio for character size.
        descent = 0
        return width, height, descent

    def patched_text_draw(self, renderer):
        """
        Replace ``Text.draw`` with a fixed bounding box Rectangle.

        The bounding box corresponds to ``Text.get_window_extent``, which ultimately
        depends on the above patched ``_get_text_metrics_with_cache``.
        """
        if renderer is not None:
            self._renderer = renderer
        if not self.get_visible():
            return
        if self.get_text() == '':
            return
        bbox = self.get_window_extent()
        rect = Rectangle(bbox.p0, bbox.width, bbox.height,
                         facecolor=self.get_color(), edgecolor='none')
        rect.draw(renderer)

    monkeypatch.setattr('matplotlib.text._get_text_metrics_with_cache',
                        patched_get_text_metrics_with_cache)
    monkeypatch.setattr('matplotlib.text.Text.draw', patched_text_draw)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_transport.py ===
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

import asyncio
import io
import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Union

from playwright._impl._driver import compute_driver_executable, get_driver_env
from playwright._impl._helper import ParsedMessagePayload


# Sourced from: https://github.com/pytest-dev/pytest/blob/da01ee0a4bb0af780167ecd228ab3ad249511302/src/_pytest/faulthandler.py#L69-L77
def _get_stderr_fileno() -> Optional[int]:
    try:
        # when using pythonw, sys.stderr is None.
        # when Pyinstaller is used, there is no closed attribute because Pyinstaller monkey-patches it with a NullWriter class
        if sys.stderr is None or not hasattr(sys.stderr, "closed"):
            return None
        if sys.stderr.closed:
            return None

        return sys.stderr.fileno()
    except (NotImplementedError, AttributeError, io.UnsupportedOperation):
        # pytest-xdist monkeypatches sys.stderr with an object that is not an actual file.
        # https://docs.python.org/3/library/faulthandler.html#issue-with-file-descriptors
        # This is potentially dangerous, but the best we can do.
        if not hasattr(sys, "__stderr__") or not sys.__stderr__:
            return None
        return sys.__stderr__.fileno()


class Transport(ABC):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self.on_message: Callable[[ParsedMessagePayload], None] = lambda _: None
        self.on_error_future: asyncio.Future = loop.create_future()

    @abstractmethod
    def request_stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass

    @abstractmethod
    async def wait_until_stopped(self) -> None:
        pass

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def run(self) -> None:
        pass

    @abstractmethod
    def send(self, message: Dict) -> None:
        pass

    def serialize_message(self, message: Dict) -> bytes:
        msg = json.dumps(message)
        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[32mSEND>\x1b[0m", json.dumps(message, indent=2))
        return msg.encode()

    def deserialize_message(self, data: Union[str, bytes]) -> ParsedMessagePayload:
        obj = json.loads(data)

        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[33mRECV>\x1b[0m", json.dumps(obj, indent=2))
        return obj


class PipeTransport(Transport):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(loop)
        self._stopped = False

    def request_stop(self) -> None:
        assert self._output
        self._stopped = True
        self._output.close()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future

    async def connect(self) -> None:
        self._stopped_future: asyncio.Future = asyncio.Future()

        try:
            # For pyinstaller and Nuitka
            env = get_driver_env()
            if getattr(sys, "frozen", False) or globals().get("__compiled__"):
                env.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            executable_path, entrypoint_path = compute_driver_executable()
            self._proc = await asyncio.create_subprocess_exec(
                executable_path,
                entrypoint_path,
                "run-driver",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=_get_stderr_fileno(),
                limit=32768,
                env=env,
                startupinfo=startupinfo,
            )
        except Exception as exc:
            self.on_error_future.set_exception(exc)
            raise exc

        self._output = self._proc.stdin

    async def run(self) -> None:
        assert self._proc.stdout
        assert self._proc.stdin
        while not self._stopped:
            try:
                buffer = await self._proc.stdout.readexactly(4)
                if self._stopped:
                    break
                length = int.from_bytes(buffer, byteorder="little", signed=False)
                buffer = bytes(0)
                while length:
                    to_read = min(length, 32768)
                    data = await self._proc.stdout.readexactly(to_read)
                    if self._stopped:
                        break
                    length -= to_read
                    if len(buffer):
                        buffer = buffer + data
                    else:
                        buffer = data
                if self._stopped:
                    break

                obj = self.deserialize_message(buffer)
                self.on_message(obj)
            except asyncio.IncompleteReadError:
                if not self._stopped:
                    self.on_error_future.set_exception(
                        Exception("Connection closed while reading from the driver")
                    )
                break
            await asyncio.sleep(0)

        await self._proc.communicate()
        self._stopped_future.set_result(None)

    def send(self, message: Dict) -> None:
        assert self._output
        data = self.serialize_message(message)
        self._output.write(
            len(data).to_bytes(4, byteorder="little", signed=False) + data
        )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\ssh\server.py ===
"""
Utility for running a prompt_toolkit application in an asyncssh server.
"""

from __future__ import annotations

import asyncio
import traceback
from asyncio import get_running_loop
from typing import Any, Callable, Coroutine, TextIO, cast

import asyncssh

from prompt_toolkit.application.current import AppSession, create_app_session
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output.vt100 import Vt100_Output

__all__ = ["PromptToolkitSSHSession", "PromptToolkitSSHServer"]


class PromptToolkitSSHSession(asyncssh.SSHServerSession):  # type: ignore
    def __init__(
        self,
        interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]],
        *,
        enable_cpr: bool,
    ) -> None:
        self.interact = interact
        self.enable_cpr = enable_cpr
        self.interact_task: asyncio.Task[None] | None = None
        self._chan: Any | None = None
        self.app_session: AppSession | None = None

        # PipInput object, for sending input in the CLI.
        # (This is something that we can use in the prompt_toolkit event loop,
        # but still write date in manually.)
        self._input: PipeInput | None = None
        self._output: Vt100_Output | None = None

        # Output object. Don't render to the real stdout, but write everything
        # in the SSH channel.
        class Stdout:
            def write(s, data: str) -> None:
                try:
                    if self._chan is not None:
                        self._chan.write(data.replace("\n", "\r\n"))
                except BrokenPipeError:
                    pass  # Channel not open for sending.

            def isatty(s) -> bool:
                return True

            def flush(s) -> None:
                pass

            @property
            def encoding(s) -> str:
                assert self._chan is not None
                return str(self._chan._orig_chan.get_encoding()[0])

        self.stdout = cast(TextIO, Stdout())

    def _get_size(self) -> Size:
        """
        Callable that returns the current `Size`, required by Vt100_Output.
        """
        if self._chan is None:
            return Size(rows=20, columns=79)
        else:
            width, height, pixwidth, pixheight = self._chan.get_terminal_size()
            return Size(rows=height, columns=width)

    def connection_made(self, chan: Any) -> None:
        self._chan = chan

    def shell_requested(self) -> bool:
        return True

    def session_started(self) -> None:
        self.interact_task = get_running_loop().create_task(self._interact())

    async def _interact(self) -> None:
        if self._chan is None:
            # Should not happen.
            raise Exception("`_interact` called before `connection_made`.")

        if hasattr(self._chan, "set_line_mode") and self._chan._editor is not None:
            # Disable the line editing provided by asyncssh. Prompt_toolkit
            # provides the line editing.
            self._chan.set_line_mode(False)

        term = self._chan.get_terminal_type()

        self._output = Vt100_Output(
            self.stdout, self._get_size, term=term, enable_cpr=self.enable_cpr
        )

        with create_pipe_input() as self._input:
            with create_app_session(input=self._input, output=self._output) as session:
                self.app_session = session
                try:
                    await self.interact(self)
                except BaseException:
                    traceback.print_exc()
                finally:
                    # Close the connection.
                    self._chan.close()
                    self._input.close()

    def terminal_size_changed(
        self, width: int, height: int, pixwidth: object, pixheight: object
    ) -> None:
        # Send resize event to the current application.
        if self.app_session and self.app_session.app:
            self.app_session.app._on_resize()

    def data_received(self, data: str, datatype: object) -> None:
        if self._input is None:
            # Should not happen.
            return

        self._input.send_text(data)


class PromptToolkitSSHServer(asyncssh.SSHServer):
    """
    Run a prompt_toolkit application over an asyncssh server.

    This takes one argument, an `interact` function, which is called for each
    connection. This should be an asynchronous function that runs the
    prompt_toolkit applications. This function runs in an `AppSession`, which
    means that we can have multiple UI interactions concurrently.

    Example usage:

    .. code:: python

        async def interact(ssh_session: PromptToolkitSSHSession) -> None:
            await yes_no_dialog("my title", "my text").run_async()

            prompt_session = PromptSession()
            text = await prompt_session.prompt_async("Type something: ")
            print_formatted_text('You said: ', text)

        server = PromptToolkitSSHServer(interact=interact)
        loop = get_running_loop()
        loop.run_until_complete(
            asyncssh.create_server(
                lambda: MySSHServer(interact),
                "",
                port,
                server_host_keys=["/etc/ssh/..."],
            )
        )
        loop.run_forever()

    :param enable_cpr: When `True`, the default, try to detect whether the SSH
        client runs in a terminal that responds to "cursor position requests".
        That way, we can properly determine how much space there is available
        for the UI (especially for drop down menus) to render.
    """

    def __init__(
        self,
        interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]],
        *,
        enable_cpr: bool = True,
    ) -> None:
        self.interact = interact
        self.enable_cpr = enable_cpr

    def begin_auth(self, username: str) -> bool:
        # No authentication.
        return False

    def session_requested(self) -> PromptToolkitSSHSession:
        return PromptToolkitSSHSession(self.interact, enable_cpr=self.enable_cpr)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\asn1.py ===
"""
    pygments.lexers.asn1
    ~~~~~~~~~~~~~~~~~~~~

    Pygments lexers for ASN.1.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.token import  Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace
from pygments.lexer import RegexLexer, words, bygroups

__all__ = ['Asn1Lexer']

SINGLE_WORD_KEYWORDS = [
    "ENCODED",
    "ABSTRACT-SYNTAX",
    "END",
    "APPLICATION",
    "EXPLICIT",
    "IMPLICIT",
    "AUTOMATIC",
    "TAGS",
    "BEGIN",
    "EXTENSIBILITY",
    "BY",
    "FROM",
    "COMPONENT",
    "UNIVERSAL",
    "COMPONENTS",
    "CONSTRAINED",
    "IMPLIED",
    "DEFINITIONS",
    "INCLUDES",
    "PRIVATE",
    "WITH",
    "OF",
]

OPERATOR_WORDS = [
    "EXCEPT",
    "UNION",
    "INTERSECTION",
]

SINGLE_WORD_NAMESPACE_KEYWORDS = [
    "EXPORTS",
    "IMPORTS",
]

MULTI_WORDS_DECLARATIONS = [
    "SEQUENCE OF",
    "SET OF",
    "INSTANCE OF",
    "WITH SYNTAX",
]

SINGLE_WORDS_DECLARATIONS = [
    "SIZE",
    "SEQUENCE",
    "SET",
    "CLASS",
    "UNIQUE",
    "DEFAULT",
    "CHOICE",
    "PATTERN",
    "OPTIONAL",
    "PRESENT",
    "ABSENT",
    "CONTAINING",
    "ENUMERATED",
    "ALL",
]

TWO_WORDS_TYPES = [
    "OBJECT IDENTIFIER",
    "BIT STRING",
    "OCTET STRING",
    "CHARACTER STRING",
    "EMBEDDED PDV",
]

SINGLE_WORD_TYPES = [
    "RELATIVE-OID",
    "TYPE-IDENTIFIER",
    "ObjectDescriptor",
    "IA5String",
    "INTEGER",
    "ISO646String",
    "T61String",
    "BMPString",
    "NumericString",
    "TeletexString",
    "GeneralizedTime",
    "REAL",
    "BOOLEAN",
    "GeneralString",
    "GraphicString",
    "UniversalString",
    "UTCTime",
    "VisibleString",
    "UTF8String",
    "PrintableString",
    "VideotexString",
    "EXTERNAL",
]


def word_sequences(tokens):
    return "(" + '|'.join(token.replace(' ', r'\s+') for token in tokens) + r')\b'


class Asn1Lexer(RegexLexer):

    """
    Lexer for ASN.1 module definition
    """

    flags = re.MULTILINE

    name = 'ASN.1'
    aliases = ['asn1']
    filenames = ["*.asn1"]
    url = "https://www.itu.int/ITU-T/studygroups/com17/languages/X.680-0207.pdf"
    version_added = '2.16'

    tokens = {
       'root': [
            # Whitespace:
            (r'\s+', Whitespace),
            # Comments:
            (r'--.*$', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),
            #  Numbers:
            (r'\d+\.\d*([eE][-+]?\d+)?', Number.Float),
            (r'\d+', Number.Integer),
            # Identifier:
            (r"&?[a-z][-a-zA-Z0-9]*[a-zA-Z0-9]\b", Name.Variable),
            # Constants:
            (words(("TRUE", "FALSE", "NULL", "MINUS-INFINITY", "PLUS-INFINITY", "MIN", "MAX"), suffix=r'\b'), Keyword.Constant),
            # Builtin types:
            (word_sequences(TWO_WORDS_TYPES), Keyword.Type),
            (words(SINGLE_WORD_TYPES, suffix=r'\b'), Keyword.Type),
            # Other keywords:
            (r"EXPORTS\s+ALL\b", Keyword.Namespace),
            (words(SINGLE_WORD_NAMESPACE_KEYWORDS, suffix=r'\b'), Operator.Namespace),
            (word_sequences(MULTI_WORDS_DECLARATIONS), Keyword.Declaration),
            (words(SINGLE_WORDS_DECLARATIONS, suffix=r'\b'), Keyword.Declaration),
            (words(OPERATOR_WORDS, suffix=r'\b'), Operator.Word),
            (words(SINGLE_WORD_KEYWORDS), Keyword),
            # Type identifier:
            (r"&?[A-Z][-a-zA-Z0-9]*[a-zA-Z0-9]\b", Name.Type),
            # Operators:
            (r"(::=|\.\.\.|\.\.|\[\[|\]\]|\||\^)", Operator),
            # Punctuation:
            (r"(\.|,|\{|\}|\(|\)|\[|\])", Punctuation),
            # String:
            (r'"', String, 'string'),
            # Binary string:
            (r"('[01 ]*')(B)\b", bygroups(String, String.Affix)),
            (r"('[0-9A-F ]*')(H)\b",bygroups(String, String.Affix)),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'string': [
            (r'""', String),
            (r'"', String, "#pop"),
            (r'[^"]', String),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\forth.py ===
"""
    pygments.lexers.forth
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Forth language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Text, Comment, Keyword, Name, String, Number, \
    Whitespace


__all__ = ['ForthLexer']


class ForthLexer(RegexLexer):
    """
    Lexer for Forth files.
    """
    name = 'Forth'
    url = 'https://www.forth.com/forth/'
    aliases = ['forth']
    filenames = ['*.frt', '*.fs']
    mimetypes = ['application/x-forth']
    version_added = '2.2'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            # All comment types
            (r'\\.*?$', Comment.Single),
            (r'\([\s].*?\)', Comment.Single),
            # defining words. The next word is a new command name
            (r'(:|variable|constant|value|buffer:)(\s+)',
             bygroups(Keyword.Namespace, Whitespace), 'worddef'),
            # strings are rather simple
            (r'([.sc]")(\s+?)', bygroups(String, Whitespace), 'stringdef'),
            # keywords from the various wordsets
            # *** Wordset BLOCK
            (r'(blk|block|buffer|evaluate|flush|load|save-buffers|update|'
             # *** Wordset BLOCK-EXT
             r'empty-buffers|list|refill|scr|thru|'
             # *** Wordset CORE
             r'\#s|\*\/mod|\+loop|\/mod|0<|0=|1\+|1-|2!|'
             r'2\*|2\/|2@|2drop|2dup|2over|2swap|>body|'
             r'>in|>number|>r|\?dup|abort|abort\"|abs|'
             r'accept|align|aligned|allot|and|base|begin|'
             r'bl|c!|c,|c@|cell\+|cells|char|char\+|'
             r'chars|constant|count|cr|create|decimal|'
             r'depth|do|does>|drop|dup|else|emit|environment\?|'
             r'evaluate|execute|exit|fill|find|fm\/mod|'
             r'here|hold|i|if|immediate|invert|j|key|'
             r'leave|literal|loop|lshift|m\*|max|min|'
             r'mod|move|negate|or|over|postpone|quit|'
             r'r>|r@|recurse|repeat|rot|rshift|s\"|s>d|'
             r'sign|sm\/rem|source|space|spaces|state|swap|'
             r'then|type|u\.|u\<|um\*|um\/mod|unloop|until|'
             r'variable|while|word|xor|\[char\]|\[\'\]|'
             r'@|!|\#|<\#|\#>|:|;|\+|-|\*|\/|,|<|>|\|1\+|1-|\.|'
             # *** Wordset CORE-EXT
             r'\.r|0<>|'
             r'0>|2>r|2r>|2r@|:noname|\?do|again|c\"|'
             r'case|compile,|endcase|endof|erase|false|'
             r'hex|marker|nip|of|pad|parse|pick|refill|'
             r'restore-input|roll|save-input|source-id|to|'
             r'true|tuck|u\.r|u>|unused|value|within|'
             r'\[compile\]|'
             # *** Wordset CORE-EXT-obsolescent
             r'\#tib|convert|expect|query|span|'
             r'tib|'
             # *** Wordset DOUBLE
             r'2constant|2literal|2variable|d\+|d-|'
             r'd\.|d\.r|d0<|d0=|d2\*|d2\/|d<|d=|d>s|'
             r'dabs|dmax|dmin|dnegate|m\*\/|m\+|'
             # *** Wordset DOUBLE-EXT
             r'2rot|du<|'
             # *** Wordset EXCEPTION
             r'catch|throw|'
             # *** Wordset EXCEPTION-EXT
             r'abort|abort\"|'
             # *** Wordset FACILITY
             r'at-xy|key\?|page|'
             # *** Wordset FACILITY-EXT
             r'ekey|ekey>char|ekey\?|emit\?|ms|time&date|'
             # *** Wordset FILE
             r'BIN|CLOSE-FILE|CREATE-FILE|DELETE-FILE|FILE-POSITION|'
             r'FILE-SIZE|INCLUDE-FILE|INCLUDED|OPEN-FILE|R\/O|'
             r'R\/W|READ-FILE|READ-LINE|REPOSITION-FILE|RESIZE-FILE|'
             r'S\"|SOURCE-ID|W/O|WRITE-FILE|WRITE-LINE|'
             # *** Wordset FILE-EXT
             r'FILE-STATUS|FLUSH-FILE|REFILL|RENAME-FILE|'
             # *** Wordset FLOAT
             r'>float|d>f|'
             r'f!|f\*|f\+|f-|f\/|f0<|f0=|f<|f>d|f@|'
             r'falign|faligned|fconstant|fdepth|fdrop|fdup|'
             r'fliteral|float\+|floats|floor|fmax|fmin|'
             r'fnegate|fover|frot|fround|fswap|fvariable|'
             r'represent|'
             # *** Wordset FLOAT-EXT
             r'df!|df@|dfalign|dfaligned|dfloat\+|'
             r'dfloats|f\*\*|f\.|fabs|facos|facosh|falog|'
             r'fasin|fasinh|fatan|fatan2|fatanh|fcos|fcosh|'
             r'fe\.|fexp|fexpm1|fln|flnp1|flog|fs\.|fsin|'
             r'fsincos|fsinh|fsqrt|ftan|ftanh|f~|precision|'
             r'set-precision|sf!|sf@|sfalign|sfaligned|sfloat\+|'
             r'sfloats|'
             # *** Wordset LOCAL
             r'\(local\)|to|'
             # *** Wordset LOCAL-EXT
             r'locals\||'
             # *** Wordset MEMORY
             r'allocate|free|resize|'
             # *** Wordset SEARCH
             r'definitions|find|forth-wordlist|get-current|'
             r'get-order|search-wordlist|set-current|set-order|'
             r'wordlist|'
             # *** Wordset SEARCH-EXT
             r'also|forth|only|order|previous|'
             # *** Wordset STRING
             r'-trailing|\/string|blank|cmove|cmove>|compare|'
             r'search|sliteral|'
             # *** Wordset TOOLS
             r'.s|dump|see|words|'
             # *** Wordset TOOLS-EXT
             r';code|'
             r'ahead|assembler|bye|code|cs-pick|cs-roll|'
             r'editor|state|\[else\]|\[if\]|\[then\]|'
             # *** Wordset TOOLS-EXT-obsolescent
             r'forget|'
             # Forth 2012
             r'defer|defer@|defer!|action-of|begin-structure|field:|buffer:|'
             r'parse-name|buffer:|traverse-wordlist|n>r|nr>|2value|fvalue|'
             r'name>interpret|name>compile|name>string|'
             r'cfield:|end-structure)(?!\S)', Keyword),

            # Numbers
            (r'(\$[0-9A-F]+)', Number.Hex),
            (r'(\#|%|&|\-|\+)?[0-9]+', Number.Integer),
            (r'(\#|%|&|\-|\+)?[0-9.]+', Keyword.Type),
            # amforth specific
            (r'(@i|!i|@e|!e|pause|noop|turnkey|sleep|'
             r'itype|icompare|sp@|sp!|rp@|rp!|up@|up!|'
             r'>a|a>|a@|a!|a@+|a@-|>b|b>|b@|b!|b@+|b@-|'
             r'find-name|1ms|'
             r'sp0|rp0|\(evaluate\)|int-trap|int!)(?!\S)',
             Name.Constant),
            # a proposal
            (r'(do-recognizer|r:fail|recognizer:|get-recognizers|'
             r'set-recognizers|r:float|r>comp|r>int|r>post|'
             r'r:name|r:word|r:dnum|r:num|recognizer|forth-recognizer|'
             r'rec:num|rec:float|rec:word)(?!\S)', Name.Decorator),
            # defining words. The next word is a new command name
            (r'(Evalue|Rvalue|Uvalue|Edefer|Rdefer|Udefer)(\s+)',
             bygroups(Keyword.Namespace, Text), 'worddef'),

            (r'\S+', Name.Function),      # Anything else is executed

        ],
        'worddef': [
            (r'\S+', Name.Class, '#pop'),
        ],
        'stringdef': [
            (r'[^"]+', String, '#pop'),
        ],
    }

    def analyse_text(text):
        """Forth uses : COMMAND ; quite a lot in a single line, so we're trying
        to find that."""
        if re.search('\n:[^\n]+;\n', text):
            return 0.3

# === NexusCore/openenv\Lib\site-packages\starlette\middleware\cors.py ===
from __future__ import annotations

import functools
import re
import typing

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ALL_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
SAFELISTED_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}


class CORSMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: typing.Sequence[str] = (),
        allow_methods: typing.Sequence[str] = ("GET",),
        allow_headers: typing.Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        expose_headers: typing.Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        allow_all_origins = "*" in allow_origins
        allow_all_headers = "*" in allow_headers
        preflight_explicit_allow_origin = not allow_all_origins or allow_credentials

        simple_headers = {}
        if allow_all_origins:
            simple_headers["Access-Control-Allow-Origin"] = "*"
        if allow_credentials:
            simple_headers["Access-Control-Allow-Credentials"] = "true"
        if expose_headers:
            simple_headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)

        preflight_headers = {}
        if preflight_explicit_allow_origin:
            # The origin value will be set in preflight_response() if it is allowed.
            preflight_headers["Vary"] = "Origin"
        else:
            preflight_headers["Access-Control-Allow-Origin"] = "*"
        preflight_headers.update(
            {
                "Access-Control-Allow-Methods": ", ".join(allow_methods),
                "Access-Control-Max-Age": str(max_age),
            }
        )
        allow_headers = sorted(SAFELISTED_HEADERS | set(allow_headers))
        if allow_headers and not allow_all_headers:
            preflight_headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
        if allow_credentials:
            preflight_headers["Access-Control-Allow-Credentials"] = "true"

        self.app = app
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = [h.lower() for h in allow_headers]
        self.allow_all_origins = allow_all_origins
        self.allow_all_headers = allow_all_headers
        self.preflight_explicit_allow_origin = preflight_explicit_allow_origin
        self.allow_origin_regex = compiled_allow_origin_regex
        self.simple_headers = simple_headers
        self.preflight_headers = preflight_headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        headers = Headers(scope=scope)
        origin = headers.get("origin")

        if origin is None:
            await self.app(scope, receive, send)
            return

        if method == "OPTIONS" and "access-control-request-method" in headers:
            response = self.preflight_response(request_headers=headers)
            await response(scope, receive, send)
            return

        await self.simple_response(scope, receive, send, request_headers=headers)

    def is_allowed_origin(self, origin: str) -> bool:
        if self.allow_all_origins:
            return True

        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(
            origin
        ):
            return True

        return origin in self.allow_origins

    def preflight_response(self, request_headers: Headers) -> Response:
        requested_origin = request_headers["origin"]
        requested_method = request_headers["access-control-request-method"]
        requested_headers = request_headers.get("access-control-request-headers")

        headers = dict(self.preflight_headers)
        failures = []

        if self.is_allowed_origin(origin=requested_origin):
            if self.preflight_explicit_allow_origin:
                # The "else" case is already accounted for in self.preflight_headers
                # and the value would be "*".
                headers["Access-Control-Allow-Origin"] = requested_origin
        else:
            failures.append("origin")

        if requested_method not in self.allow_methods:
            failures.append("method")

        # If we allow all headers, then we have to mirror back any requested
        # headers in the response.
        if self.allow_all_headers and requested_headers is not None:
            headers["Access-Control-Allow-Headers"] = requested_headers
        elif requested_headers is not None:
            for header in [h.lower() for h in requested_headers.split(",")]:
                if header.strip() not in self.allow_headers:
                    failures.append("headers")
                    break

        # We don't strictly need to use 400 responses here, since its up to
        # the browser to enforce the CORS policy, but its more informative
        # if we do.
        if failures:
            failure_text = "Disallowed CORS " + ", ".join(failures)
            return PlainTextResponse(failure_text, status_code=400, headers=headers)

        return PlainTextResponse("OK", status_code=200, headers=headers)

    async def simple_response(
        self, scope: Scope, receive: Receive, send: Send, request_headers: Headers
    ) -> None:
        send = functools.partial(self.send, send=send, request_headers=request_headers)
        await self.app(scope, receive, send)

    async def send(
        self, message: Message, send: Send, request_headers: Headers
    ) -> None:
        if message["type"] != "http.response.start":
            await send(message)
            return

        message.setdefault("headers", [])
        headers = MutableHeaders(scope=message)
        headers.update(self.simple_headers)
        origin = request_headers["Origin"]
        has_cookie = "cookie" in request_headers

        # If request includes any cookie headers, then we must respond
        # with the specific origin instead of '*'.
        if self.allow_all_origins and has_cookie:
            self.allow_explicit_origin(headers, origin)

        # If we only allow specific origins, then we have to mirror back
        # the Origin header in the response.
        elif not self.allow_all_origins and self.is_allowed_origin(origin=origin):
            self.allow_explicit_origin(headers, origin)

        await send(message)

    @staticmethod
    def allow_explicit_origin(headers: MutableHeaders, origin: str) -> None:
        headers["Access-Control-Allow-Origin"] = origin
        headers.add_vary_header("Origin")

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\stackframe.py ===
"""Support for stack-frames.

Provides Implements a nearly complete wrapper for a stack frame.
"""

import pythoncom

from . import axdebug, expressions, gateways
from .util import RaiseNotImpl, _wrap, trace

# def trace(*args):
#     pass


class EnumDebugStackFrames(gateways.EnumDebugStackFrames):
    """A class that given a debugger object, can return an enumerator
    of DebugStackFrame objects.
    """

    def __init__(self, debugger):
        infos = []
        frame = debugger.currentframe
        # print("Stack check")
        while frame:
            # print(" Checking frame", frame.f_code.co_filename, frame.f_lineno-1, frame.f_trace)
            # Get a DebugCodeContext for the stack frame.  If we fail, then it
            # is not debuggable, and therefore not worth displaying.
            cc = debugger.codeContainerProvider.FromFileName(frame.f_code.co_filename)
            if cc is not None:
                try:
                    address = frame.f_locals["__axstack_address__"]
                except KeyError:
                    # print("Couldn't find stack address for",frame.f_code.co_filename, frame.f_lineno-1)
                    # Use this one, even tho it is wrong :-(
                    address = axdebug.GetStackAddress()
                frameInfo = (
                    DebugStackFrame(frame, frame.f_lineno - 1, cc),
                    address,
                    address + 1,
                    0,
                    None,
                )
                infos.append(frameInfo)
            #     print("- Kept!")
            # else:
            #     print("- rejected")
            frame = frame.f_back

        gateways.EnumDebugStackFrames.__init__(self, infos, 0)

    # def __del__(self):
    #     print("EnumDebugStackFrames dieing")

    def Next(self, count):
        return gateways.EnumDebugStackFrames.Next(self, count)

    # def _query_interface_(self, iid):
    #     from win32com.util import IIDToInterfaceName
    #     print(f"EnumDebugStackFrames QI with {IIDToInterfaceName(iid)} ({iid})")
    #     return 0
    def _wrap(self, obj):
        # This enum returns a tuple, with 2 com objects in it.
        obFrame, min, lim, fFinal, obFinal = obj
        obFrame = _wrap(obFrame, axdebug.IID_IDebugStackFrame)
        if obFinal:
            obFinal = _wrap(obFinal, pythoncom.IID_IUnknown)
        return obFrame, min, lim, fFinal, obFinal


class DebugStackFrame(gateways.DebugStackFrame):
    def __init__(self, frame, lineno, codeContainer):
        self.frame = frame
        self.lineno = lineno
        self.codeContainer = codeContainer
        self.expressionContext = None

    # def __del__(self):
    #     print("DSF dieing")
    def _query_interface_(self, iid):
        if iid == axdebug.IID_IDebugExpressionContext:
            if self.expressionContext is None:
                self.expressionContext = _wrap(
                    expressions.ExpressionContext(self.frame),
                    axdebug.IID_IDebugExpressionContext,
                )
            return self.expressionContext
        # from win32com.util import IIDToInterfaceName
        # print(f"DebugStackFrame QI with {IIDToInterfaceName(iid)} ({iid})")
        return 0

    #
    # The following need implementation
    def GetThread(self):
        """Returns the thread associated with this stack frame.

        Result must be a IDebugApplicationThread
        """
        RaiseNotImpl("GetThread")

    def GetCodeContext(self):
        offset = self.codeContainer.GetPositionOfLine(self.lineno)
        return self.codeContainer.GetCodeContextAtPosition(offset)

    #
    # The following are usefully implemented
    def GetDescriptionString(self, fLong):
        filename = self.frame.f_code.co_filename
        s = ""
        if 0:  # fLong:
            s += filename
        if self.frame.f_code.co_name:
            s += self.frame.f_code.co_name
        else:
            s += "<lambda>"
        return s

    def GetLanguageString(self, fLong):
        if fLong:
            return "Python ActiveX Scripting Engine"
        else:
            return "Python"

    def GetDebugProperty(self):
        return _wrap(StackFrameDebugProperty(self.frame), axdebug.IID_IDebugProperty)


class DebugStackFrameSniffer:
    _public_methods_ = ["EnumStackFrames"]
    _com_interfaces_ = [axdebug.IID_IDebugStackFrameSniffer]

    def __init__(self, debugger):
        self.debugger = debugger
        trace("DebugStackFrameSniffer instantiated")

    # def __del__(self):
    #     print("DSFS dieing")
    def EnumStackFrames(self):
        trace("DebugStackFrameSniffer.EnumStackFrames called")
        return _wrap(
            EnumDebugStackFrames(self.debugger), axdebug.IID_IEnumDebugStackFrames
        )


# A DebugProperty for a stack frame.
class StackFrameDebugProperty:
    _com_interfaces_ = [axdebug.IID_IDebugProperty]
    _public_methods_ = [
        "GetPropertyInfo",
        "GetExtendedInfo",
        "SetValueAsString",
        "EnumMembers",
        "GetParent",
    ]

    def __init__(self, frame):
        self.frame = frame

    def GetPropertyInfo(self, dwFieldSpec, nRadix):
        RaiseNotImpl("StackFrameDebugProperty::GetPropertyInfo")

    def GetExtendedInfo(self):  ### Note - not in the framework.
        RaiseNotImpl("StackFrameDebugProperty::GetExtendedInfo")

    def SetValueAsString(self, value, radix):
        #
        RaiseNotImpl("DebugProperty::SetValueAsString")

    def EnumMembers(self, dwFieldSpec, nRadix, iid):
        print("EnumMembers", dwFieldSpec, nRadix, iid)
        from . import expressions

        return expressions.MakeEnumDebugProperty(
            self.frame.f_locals, dwFieldSpec, nRadix, iid, self.frame
        )

    def GetParent(self):
        # return IDebugProperty
        RaiseNotImpl("DebugProperty::GetParent")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\__init__.py ===
"""Rich text and beautiful formatting in the terminal."""

import os
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, Union

from ._extension import load_ipython_extension  # noqa: F401

__all__ = ["get_console", "reconfigure", "print", "inspect", "print_json"]

if TYPE_CHECKING:
    from .console import Console

# Global console used by alternative print
_console: Optional["Console"] = None

try:
    _IMPORT_CWD = os.path.abspath(os.getcwd())
except FileNotFoundError:
    # Can happen if the cwd has been deleted
    _IMPORT_CWD = ""


def get_console() -> "Console":
    """Get a global :class:`~rich.console.Console` instance. This function is used when Rich requires a Console,
    and hasn't been explicitly given one.

    Returns:
        Console: A console instance.
    """
    global _console
    if _console is None:
        from .console import Console

        _console = Console()

    return _console


def reconfigure(*args: Any, **kwargs: Any) -> None:
    """Reconfigures the global console by replacing it with another.

    Args:
        *args (Any): Positional arguments for the replacement :class:`~rich.console.Console`.
        **kwargs (Any): Keyword arguments for the replacement :class:`~rich.console.Console`.
    """
    from pip._vendor.rich.console import Console

    new_console = Console(*args, **kwargs)
    _console = get_console()
    _console.__dict__ = new_console.__dict__


def print(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[IO[str]] = None,
    flush: bool = False,
) -> None:
    r"""Print object(s) supplied via positional arguments.
    This function has an identical signature to the built-in print.
    For more advanced features, see the :class:`~rich.console.Console` class.

    Args:
        sep (str, optional): Separator between printed objects. Defaults to " ".
        end (str, optional): Character to write at end of output. Defaults to "\\n".
        file (IO[str], optional): File to write to, or None for stdout. Defaults to None.
        flush (bool, optional): Has no effect as Rich always flushes output. Defaults to False.

    """
    from .console import Console

    write_console = get_console() if file is None else Console(file=file)
    return write_console.print(*objects, sep=sep, end=end)


def print_json(
    json: Optional[str] = None,
    *,
    data: Any = None,
    indent: Union[None, int, str] = 2,
    highlight: bool = True,
    skip_keys: bool = False,
    ensure_ascii: bool = False,
    check_circular: bool = True,
    allow_nan: bool = True,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
) -> None:
    """Pretty prints JSON. Output will be valid JSON.

    Args:
        json (str): A string containing JSON.
        data (Any): If json is not supplied, then encode this data.
        indent (int, optional): Number of spaces to indent. Defaults to 2.
        highlight (bool, optional): Enable highlighting of output: Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    get_console().print_json(
        json,
        data=data,
        indent=indent,
        highlight=highlight,
        skip_keys=skip_keys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        default=default,
        sort_keys=sort_keys,
    )


def inspect(
    obj: Any,
    *,
    console: Optional["Console"] = None,
    title: Optional[str] = None,
    help: bool = False,
    methods: bool = False,
    docs: bool = True,
    private: bool = False,
    dunder: bool = False,
    sort: bool = True,
    all: bool = False,
    value: bool = True,
) -> None:
    """Inspect any Python object.

    * inspect(<OBJECT>) to see summarized info.
    * inspect(<OBJECT>, methods=True) to see methods.
    * inspect(<OBJECT>, help=True) to see full (non-abbreviated) help.
    * inspect(<OBJECT>, private=True) to see private attributes (single underscore).
    * inspect(<OBJECT>, dunder=True) to see attributes beginning with double underscore.
    * inspect(<OBJECT>, all=True) to see all attributes.

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
        value (bool, optional): Pretty print value. Defaults to True.
    """
    _console = console or get_console()
    from pip._vendor.rich._inspect import Inspect

    # Special case for inspect(inspect)
    is_inspect = obj is inspect

    _inspect = Inspect(
        obj,
        title=title,
        help=is_inspect or help,
        methods=is_inspect or methods,
        docs=is_inspect or docs,
        private=private,
        dunder=dunder,
        sort=sort,
        all=all,
        value=value,
    )
    _console.print(_inspect)


if __name__ == "__main__":  # pragma: no cover
    print("Hello, **World**")

# === NexusCore/openenv\Lib\site-packages\litellm\_logging.py ===
import json
import logging
import os
import sys
from datetime import datetime
from logging import Formatter

set_verbose = False

if set_verbose is True:
    logging.warning(
        "`litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs."
    )
json_logs = bool(os.getenv("JSON_LOGS", False))
# Create a handler for the logger (you may need to adapt this based on your needs)
log_level = os.getenv("LITELLM_LOG", "DEBUG")
numeric_level: str = getattr(logging, log_level.upper())
handler = logging.StreamHandler()
handler.setLevel(numeric_level)


class JsonFormatter(Formatter):
    def __init__(self):
        super(JsonFormatter, self).__init__()

    def formatTime(self, record, datefmt=None):
        # Use datetime to format the timestamp in ISO 8601 format
        dt = datetime.fromtimestamp(record.created)
        return dt.isoformat()

    def format(self, record):
        json_record = {
            "message": record.getMessage(),
            "level": record.levelname,
            "timestamp": self.formatTime(record),
        }

        if record.exc_info:
            json_record["stacktrace"] = self.formatException(record.exc_info)

        return json.dumps(json_record)


# Function to set up exception handlers for JSON logging
def _setup_json_exception_handlers(formatter):
    # Create a handler with JSON formatting for exceptions
    error_handler = logging.StreamHandler()
    error_handler.setFormatter(formatter)

    # Setup excepthook for uncaught exceptions
    def json_excepthook(exc_type, exc_value, exc_traceback):
        record = logging.LogRecord(
            name="LiteLLM",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=str(exc_value),
            args=(),
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        error_handler.handle(record)

    sys.excepthook = json_excepthook

    # Configure asyncio exception handler if possible
    try:
        import asyncio

        def async_json_exception_handler(loop, context):
            exception = context.get("exception")
            if exception:
                record = logging.LogRecord(
                    name="LiteLLM",
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg=str(exception),
                    args=(),
                    exc_info=None,
                )
                error_handler.handle(record)
            else:
                loop.default_exception_handler(context)

        asyncio.get_event_loop().set_exception_handler(async_json_exception_handler)
    except Exception:
        pass


# Create a formatter and set it for the handler
if json_logs:
    handler.setFormatter(JsonFormatter())
    _setup_json_exception_handlers(JsonFormatter())
else:
    formatter = logging.Formatter(
        "\033[92m%(asctime)s - %(name)s:%(levelname)s\033[0m: %(filename)s:%(lineno)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    handler.setFormatter(formatter)

verbose_proxy_logger = logging.getLogger("LiteLLM Proxy")
verbose_router_logger = logging.getLogger("LiteLLM Router")
verbose_logger = logging.getLogger("LiteLLM")

# Add the handler to the logger
verbose_router_logger.addHandler(handler)
verbose_proxy_logger.addHandler(handler)
verbose_logger.addHandler(handler)

ALL_LOGGERS = [
    logging.getLogger(),
    verbose_logger,
    verbose_router_logger,
    verbose_proxy_logger,
]


def _initialize_loggers_with_handler(handler: logging.Handler):
    """
    Initialize all loggers with a handler

    - Adds a handler to each logger
    - Prevents bubbling to parent/root (critical to prevent duplicate JSON logs)
    """
    for lg in ALL_LOGGERS:
        lg.handlers.clear()  # remove any existing handlers
        lg.addHandler(handler)  # add JSON formatter handler
        lg.propagate = False  # prevent bubbling to parent/root


def _turn_on_json():
    """
    Turn on JSON logging

    - Adds a JSON formatter to all loggers
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    _initialize_loggers_with_handler(handler)
    # Set up exception handlers
    _setup_json_exception_handlers(JsonFormatter())


def _turn_on_debug():
    verbose_logger.setLevel(level=logging.DEBUG)  # set package log to debug
    verbose_router_logger.setLevel(level=logging.DEBUG)  # set router logs to debug
    verbose_proxy_logger.setLevel(level=logging.DEBUG)  # set proxy logs to debug


def _disable_debugging():
    verbose_logger.disabled = True
    verbose_router_logger.disabled = True
    verbose_proxy_logger.disabled = True


def _enable_debugging():
    verbose_logger.disabled = False
    verbose_router_logger.disabled = False
    verbose_proxy_logger.disabled = False


def print_verbose(print_statement):
    try:
        if set_verbose:
            print(print_statement)  # noqa
    except Exception:
        pass


def _is_debugging_on() -> bool:
    """
    Returns True if debugging is on
    """
    if verbose_logger.isEnabledFor(logging.DEBUG) or set_verbose is True:
        return True
    return False

# === NexusCore/openenv\Lib\site-packages\matplotlib\_enums.py ===
"""
Enums representing sets of strings that Matplotlib uses as input parameters.

Matplotlib often uses simple data types like strings or tuples to define a
concept; e.g. the line capstyle can be specified as one of 'butt', 'round',
or 'projecting'. The classes in this module are used internally and serve to
document these concepts formally.

As an end-user you will not use these classes directly, but only the values
they define.
"""

from enum import Enum
from matplotlib import _docstring


class JoinStyle(str, Enum):
    """
    Define how the connection between two line segments is drawn.

    For a visual impression of each *JoinStyle*, `view these docs online
    <JoinStyle>`, or run `JoinStyle.demo`.

    Lines in Matplotlib are typically defined by a 1D `~.path.Path` and a
    finite ``linewidth``, where the underlying 1D `~.path.Path` represents the
    center of the stroked line.

    By default, `~.backend_bases.GraphicsContextBase` defines the boundaries of
    a stroked line to simply be every point within some radius,
    ``linewidth/2``, away from any point of the center line. However, this
    results in corners appearing "rounded", which may not be the desired
    behavior if you are drawing, for example, a polygon or pointed star.

    **Supported values:**

    .. rst-class:: value-list

        'miter'
            the "arrow-tip" style. Each boundary of the filled-in area will
            extend in a straight line parallel to the tangent vector of the
            centerline at the point it meets the corner, until they meet in a
            sharp point.
        'round'
            stokes every point within a radius of ``linewidth/2`` of the center
            lines.
        'bevel'
            the "squared-off" style. It can be thought of as a rounded corner
            where the "circular" part of the corner has been cut off.

    .. note::

        Very long miter tips are cut off (to form a *bevel*) after a
        backend-dependent limit called the "miter limit", which specifies the
        maximum allowed ratio of miter length to line width. For example, the
        PDF backend uses the default value of 10 specified by the PDF standard,
        while the SVG backend does not even specify the miter limit, resulting
        in a default value of 4 per the SVG specification. Matplotlib does not
        currently allow the user to adjust this parameter.

        A more detailed description of the effect of a miter limit can be found
        in the `Mozilla Developer Docs
        <https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/stroke-miterlimit>`_

    .. plot::
        :alt: Demo of possible JoinStyle's

        from matplotlib._enums import JoinStyle
        JoinStyle.demo()

    """

    miter = "miter"
    round = "round"
    bevel = "bevel"

    @staticmethod
    def demo():
        """Demonstrate how each JoinStyle looks for various join angles."""
        import numpy as np
        import matplotlib.pyplot as plt

        def plot_angle(ax, x, y, angle, style):
            phi = np.radians(angle)
            xx = [x + .5, x, x + .5*np.cos(phi)]
            yy = [y, y, y + .5*np.sin(phi)]
            ax.plot(xx, yy, lw=12, color='tab:blue', solid_joinstyle=style)
            ax.plot(xx, yy, lw=1, color='black')
            ax.plot(xx[1], yy[1], 'o', color='tab:red', markersize=3)

        fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)
        ax.set_title('Join style')
        for x, style in enumerate(['miter', 'round', 'bevel']):
            ax.text(x, 5, style)
            for y, angle in enumerate([20, 45, 60, 90, 120]):
                plot_angle(ax, x, y, angle, style)
                if x == 0:
                    ax.text(-1.3, y, f'{angle} degrees')
        ax.set_xlim(-1.5, 2.75)
        ax.set_ylim(-.5, 5.5)
        ax.set_axis_off()
        fig.show()


JoinStyle.input_description = "{" \
        + ", ".join([f"'{js.name}'" for js in JoinStyle]) \
        + "}"


class CapStyle(str, Enum):
    r"""
    Define how the two endpoints (caps) of an unclosed line are drawn.

    How to draw the start and end points of lines that represent a closed curve
    (i.e. that end in a `~.path.Path.CLOSEPOLY`) is controlled by the line's
    `JoinStyle`. For all other lines, how the start and end points are drawn is
    controlled by the *CapStyle*.

    For a visual impression of each *CapStyle*, `view these docs online
    <CapStyle>` or run `CapStyle.demo`.

    By default, `~.backend_bases.GraphicsContextBase` draws a stroked line as
    squared off at its endpoints.

    **Supported values:**

    .. rst-class:: value-list

        'butt'
            the line is squared off at its endpoint.
        'projecting'
            the line is squared off as in *butt*, but the filled in area
            extends beyond the endpoint a distance of ``linewidth/2``.
        'round'
            like *butt*, but a semicircular cap is added to the end of the
            line, of radius ``linewidth/2``.

    .. plot::
        :alt: Demo of possible CapStyle's

        from matplotlib._enums import CapStyle
        CapStyle.demo()

    """
    butt = "butt"
    projecting = "projecting"
    round = "round"

    @staticmethod
    def demo():
        """Demonstrate how each CapStyle looks for a thick line segment."""
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(4, 1.2))
        ax = fig.add_axes([0, 0, 1, 0.8])
        ax.set_title('Cap style')

        for x, style in enumerate(['butt', 'round', 'projecting']):
            ax.text(x+0.25, 0.85, style, ha='center')
            xx = [x, x+0.5]
            yy = [0, 0]
            ax.plot(xx, yy, lw=12, color='tab:blue', solid_capstyle=style)
            ax.plot(xx, yy, lw=1, color='black')
            ax.plot(xx, yy, 'o', color='tab:red', markersize=3)

        ax.set_ylim(-.5, 1.5)
        ax.set_axis_off()
        fig.show()


CapStyle.input_description = "{" \
        + ", ".join([f"'{cs.name}'" for cs in CapStyle]) \
        + "}"

_docstring.interpd.register(
    JoinStyle=JoinStyle.input_description,
    CapStyle=CapStyle.input_description,
)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\auto_suggest.py ===
"""
`Fish-style <http://fishshell.com/>`_  like auto-suggestion.

While a user types input in a certain buffer, suggestions are generated
(asynchronously.) Usually, they are displayed after the input. When the cursor
presses the right arrow and the cursor is at the end of the input, the
suggestion will be inserted.

If you want the auto suggestions to be asynchronous (in a background thread),
because they take too much time, and could potentially block the event loop,
then wrap the :class:`.AutoSuggest` instance into a
:class:`.ThreadedAutoSuggest`.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable

from prompt_toolkit.eventloop import run_in_executor_with_context

from .document import Document
from .filters import Filter, to_filter

if TYPE_CHECKING:
    from .buffer import Buffer

__all__ = [
    "Suggestion",
    "AutoSuggest",
    "ThreadedAutoSuggest",
    "DummyAutoSuggest",
    "AutoSuggestFromHistory",
    "ConditionalAutoSuggest",
    "DynamicAutoSuggest",
]


class Suggestion:
    """
    Suggestion returned by an auto-suggest algorithm.

    :param text: The suggestion text.
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return f"Suggestion({self.text})"


class AutoSuggest(metaclass=ABCMeta):
    """
    Base class for auto suggestion implementations.
    """

    @abstractmethod
    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        """
        Return `None` or a :class:`.Suggestion` instance.

        We receive both :class:`~prompt_toolkit.buffer.Buffer` and
        :class:`~prompt_toolkit.document.Document`. The reason is that auto
        suggestions are retrieved asynchronously. (Like completions.) The
        buffer text could be changed in the meantime, but ``document`` contains
        the buffer document like it was at the start of the auto suggestion
        call. So, from here, don't access ``buffer.text``, but use
        ``document.text`` instead.

        :param buffer: The :class:`~prompt_toolkit.buffer.Buffer` instance.
        :param document: The :class:`~prompt_toolkit.document.Document` instance.
        """

    async def get_suggestion_async(
        self, buff: Buffer, document: Document
    ) -> Suggestion | None:
        """
        Return a :class:`.Future` which is set when the suggestions are ready.
        This function can be overloaded in order to provide an asynchronous
        implementation.
        """
        return self.get_suggestion(buff, document)


class ThreadedAutoSuggest(AutoSuggest):
    """
    Wrapper that runs auto suggestions in a thread.
    (Use this to prevent the user interface from becoming unresponsive if the
    generation of suggestions takes too much time.)
    """

    def __init__(self, auto_suggest: AutoSuggest) -> None:
        self.auto_suggest = auto_suggest

    def get_suggestion(self, buff: Buffer, document: Document) -> Suggestion | None:
        return self.auto_suggest.get_suggestion(buff, document)

    async def get_suggestion_async(
        self, buff: Buffer, document: Document
    ) -> Suggestion | None:
        """
        Run the `get_suggestion` function in a thread.
        """

        def run_get_suggestion_thread() -> Suggestion | None:
            return self.get_suggestion(buff, document)

        return await run_in_executor_with_context(run_get_suggestion_thread)


class DummyAutoSuggest(AutoSuggest):
    """
    AutoSuggest class that doesn't return any suggestion.
    """

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        return None  # No suggestion


class AutoSuggestFromHistory(AutoSuggest):
    """
    Give suggestions based on the lines in the history.
    """

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        history = buffer.history

        # Consider only the last line for the suggestion.
        text = document.text.rsplit("\n", 1)[-1]

        # Only create a suggestion when this is not an empty line.
        if text.strip():
            # Find first matching line in history.
            for string in reversed(list(history.get_strings())):
                for line in reversed(string.splitlines()):
                    if line.startswith(text):
                        return Suggestion(line[len(text) :])

        return None


class ConditionalAutoSuggest(AutoSuggest):
    """
    Auto suggest that can be turned on and of according to a certain condition.
    """

    def __init__(self, auto_suggest: AutoSuggest, filter: bool | Filter) -> None:
        self.auto_suggest = auto_suggest
        self.filter = to_filter(filter)

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion | None:
        if self.filter():
            return self.auto_suggest.get_suggestion(buffer, document)

        return None


class DynamicAutoSuggest(AutoSuggest):
    """
    Validator class that can dynamically returns any Validator.

    :param get_validator: Callable that returns a :class:`.Validator` instance.
    """

    def __init__(self, get_auto_suggest: Callable[[], AutoSuggest | None]) -> None:
        self.get_auto_suggest = get_auto_suggest

    def get_suggestion(self, buff: Buffer, document: Document) -> Suggestion | None:
        auto_suggest = self.get_auto_suggest() or DummyAutoSuggest()
        return auto_suggest.get_suggestion(buff, document)

    async def get_suggestion_async(
        self, buff: Buffer, document: Document
    ) -> Suggestion | None:
        auto_suggest = self.get_auto_suggest() or DummyAutoSuggest()
        return await auto_suggest.get_suggestion_async(buff, document)

# === NexusCore/openenv\Lib\site-packages\rich\__init__.py ===
"""Rich text and beautiful formatting in the terminal."""

import os
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, Union

from ._extension import load_ipython_extension  # noqa: F401

__all__ = ["get_console", "reconfigure", "print", "inspect", "print_json"]

if TYPE_CHECKING:
    from .console import Console

# Global console used by alternative print
_console: Optional["Console"] = None

try:
    _IMPORT_CWD = os.path.abspath(os.getcwd())
except FileNotFoundError:
    # Can happen if the cwd has been deleted
    _IMPORT_CWD = ""


def get_console() -> "Console":
    """Get a global :class:`~rich.console.Console` instance. This function is used when Rich requires a Console,
    and hasn't been explicitly given one.

    Returns:
        Console: A console instance.
    """
    global _console
    if _console is None:
        from .console import Console

        _console = Console()

    return _console


def reconfigure(*args: Any, **kwargs: Any) -> None:
    """Reconfigures the global console by replacing it with another.

    Args:
        *args (Any): Positional arguments for the replacement :class:`~rich.console.Console`.
        **kwargs (Any): Keyword arguments for the replacement :class:`~rich.console.Console`.
    """
    from rich.console import Console

    new_console = Console(*args, **kwargs)
    _console = get_console()
    _console.__dict__ = new_console.__dict__


def print(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[IO[str]] = None,
    flush: bool = False,
) -> None:
    r"""Print object(s) supplied via positional arguments.
    This function has an identical signature to the built-in print.
    For more advanced features, see the :class:`~rich.console.Console` class.

    Args:
        sep (str, optional): Separator between printed objects. Defaults to " ".
        end (str, optional): Character to write at end of output. Defaults to "\\n".
        file (IO[str], optional): File to write to, or None for stdout. Defaults to None.
        flush (bool, optional): Has no effect as Rich always flushes output. Defaults to False.

    """
    from .console import Console

    write_console = get_console() if file is None else Console(file=file)
    return write_console.print(*objects, sep=sep, end=end)


def print_json(
    json: Optional[str] = None,
    *,
    data: Any = None,
    indent: Union[None, int, str] = 2,
    highlight: bool = True,
    skip_keys: bool = False,
    ensure_ascii: bool = False,
    check_circular: bool = True,
    allow_nan: bool = True,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
) -> None:
    """Pretty prints JSON. Output will be valid JSON.

    Args:
        json (str): A string containing JSON.
        data (Any): If json is not supplied, then encode this data.
        indent (int, optional): Number of spaces to indent. Defaults to 2.
        highlight (bool, optional): Enable highlighting of output: Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    get_console().print_json(
        json,
        data=data,
        indent=indent,
        highlight=highlight,
        skip_keys=skip_keys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        default=default,
        sort_keys=sort_keys,
    )


def inspect(
    obj: Any,
    *,
    console: Optional["Console"] = None,
    title: Optional[str] = None,
    help: bool = False,
    methods: bool = False,
    docs: bool = True,
    private: bool = False,
    dunder: bool = False,
    sort: bool = True,
    all: bool = False,
    value: bool = True,
) -> None:
    """Inspect any Python object.

    * inspect(<OBJECT>) to see summarized info.
    * inspect(<OBJECT>, methods=True) to see methods.
    * inspect(<OBJECT>, help=True) to see full (non-abbreviated) help.
    * inspect(<OBJECT>, private=True) to see private attributes (single underscore).
    * inspect(<OBJECT>, dunder=True) to see attributes beginning with double underscore.
    * inspect(<OBJECT>, all=True) to see all attributes.

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
        value (bool, optional): Pretty print value. Defaults to True.
    """
    _console = console or get_console()
    from rich._inspect import Inspect

    # Special case for inspect(inspect)
    is_inspect = obj is inspect

    _inspect = Inspect(
        obj,
        title=title,
        help=is_inspect or help,
        methods=is_inspect or methods,
        docs=is_inspect or docs,
        private=private,
        dunder=dunder,
        sort=sort,
        all=all,
        value=value,
    )
    _console.print(_inspect)


if __name__ == "__main__":  # pragma: no cover
    print("Hello, **World**")

# === NexusCore/openenv\Lib\site-packages\setuptools\extension.py ===
from __future__ import annotations

import functools
import re
from typing import TYPE_CHECKING

from setuptools._path import StrPath

from .monkey import get_unpatched

import distutils.core
import distutils.errors
import distutils.extension


def _have_cython():
    """
    Return True if Cython can be imported.
    """
    cython_impl = 'Cython.Distutils.build_ext'
    try:
        # from (cython_impl) import build_ext
        __import__(cython_impl, fromlist=['build_ext']).build_ext
    except Exception:
        return False
    return True


# for compatibility
have_pyrex = _have_cython
if TYPE_CHECKING:
    # Work around a mypy issue where type[T] can't be used as a base: https://github.com/python/mypy/issues/10962
    from distutils.core import Extension as _Extension
else:
    _Extension = get_unpatched(distutils.core.Extension)


class Extension(_Extension):
    """
    Describes a single extension module.

    This means that all source files will be compiled into a single binary file
    ``<module path>.<suffix>`` (with ``<module path>`` derived from ``name`` and
    ``<suffix>`` defined by one of the values in
    ``importlib.machinery.EXTENSION_SUFFIXES``).

    In the case ``.pyx`` files are passed as ``sources and`` ``Cython`` is **not**
    installed in the build environment, ``setuptools`` may also try to look for the
    equivalent ``.cpp`` or ``.c`` files.

    :arg str name:
      the full name of the extension, including any packages -- ie.
      *not* a filename or pathname, but Python dotted name

    :arg list[str|os.PathLike[str]] sources:
      list of source filenames, relative to the distribution root
      (where the setup script lives), in Unix form (slash-separated)
      for portability.  Source files may be C, C++, SWIG (.i),
      platform-specific resource files, or whatever else is recognized
      by the "build_ext" command as source for a Python extension.

    :keyword list[str] include_dirs:
      list of directories to search for C/C++ header files (in Unix
      form for portability)

    :keyword list[tuple[str, str|None]] define_macros:
      list of macros to define; each macro is defined using a 2-tuple:
      the first item corresponding to the name of the macro and the second
      item either a string with its value or None to
      define it without a particular value (equivalent of "#define
      FOO" in source or -DFOO on Unix C compiler command line)

    :keyword list[str] undef_macros:
      list of macros to undefine explicitly

    :keyword list[str] library_dirs:
      list of directories to search for C/C++ libraries at link time

    :keyword list[str] libraries:
      list of library names (not filenames or paths) to link against

    :keyword list[str] runtime_library_dirs:
      list of directories to search for C/C++ libraries at run time
      (for shared extensions, this is when the extension is loaded).
      Setting this will cause an exception during build on Windows
      platforms.

    :keyword list[str] extra_objects:
      list of extra files to link with (eg. object files not implied
      by 'sources', static library that must be explicitly specified,
      binary resource files, etc.)

    :keyword list[str] extra_compile_args:
      any extra platform- and compiler-specific information to use
      when compiling the source files in 'sources'.  For platforms and
      compilers where "command line" makes sense, this is typically a
      list of command-line arguments, but for other platforms it could
      be anything.

    :keyword list[str] extra_link_args:
      any extra platform- and compiler-specific information to use
      when linking object files together to create the extension (or
      to create a new static Python interpreter).  Similar
      interpretation as for 'extra_compile_args'.

    :keyword list[str] export_symbols:
      list of symbols to be exported from a shared extension.  Not
      used on all platforms, and not generally necessary for Python
      extensions, which typically export exactly one symbol: "init" +
      extension_name.

    :keyword list[str] swig_opts:
      any extra options to pass to SWIG if a source file has the .i
      extension.

    :keyword list[str] depends:
      list of files that the extension depends on

    :keyword str language:
      extension language (i.e. "c", "c++", "objc"). Will be detected
      from the source extensions if not provided.

    :keyword bool optional:
      specifies that a build failure in the extension should not abort the
      build process, but simply not install the failing extension.

    :keyword bool py_limited_api:
      opt-in flag for the usage of :doc:`Python's limited API <python:c-api/stable>`.

    :raises setuptools.errors.PlatformError: if ``runtime_library_dirs`` is
      specified on Windows. (since v63)
    """

    # These 4 are set and used in setuptools/command/build_ext.py
    # The lack of a default value and risk of `AttributeError` is purposeful
    # to avoid people forgetting to call finalize_options if they modify the extension list.
    # See example/rationale in https://github.com/pypa/setuptools/issues/4529.
    _full_name: str  #: Private API, internal use only.
    _links_to_dynamic: bool  #: Private API, internal use only.
    _needs_stub: bool  #: Private API, internal use only.
    _file_name: str  #: Private API, internal use only.

    def __init__(
        self,
        name: str,
        sources: list[StrPath],
        *args,
        py_limited_api: bool = False,
        **kw,
    ) -> None:
        # The *args is needed for compatibility as calls may use positional
        # arguments. py_limited_api may be set only via keyword.
        self.py_limited_api = py_limited_api
        super().__init__(
            name,
            sources,  # type: ignore[arg-type] # Vendored version of setuptools supports PathLike
            *args,
            **kw,
        )

    def _convert_pyx_sources_to_lang(self):
        """
        Replace sources with .pyx extensions to sources with the target
        language extension. This mechanism allows language authors to supply
        pre-converted sources but to prefer the .pyx sources.
        """
        if _have_cython():
            # the build has Cython, so allow it to compile the .pyx files
            return
        lang = self.language or ''
        target_ext = '.cpp' if lang.lower() == 'c++' else '.c'
        sub = functools.partial(re.sub, '.pyx$', target_ext)
        self.sources = list(map(sub, self.sources))


class Library(Extension):
    """Just like a regular Extension, but built as a library instead"""

# === NexusCore/openenv\Lib\site-packages\setuptools\_normalization.py ===
"""
Helpers for normalization as expected in wheel/sdist/module file names
and core metadata
"""

import re
from typing import TYPE_CHECKING

import packaging

# https://packaging.python.org/en/latest/specifications/core-metadata/#name
_VALID_NAME = re.compile(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.I)
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Z0-9._-]+", re.I)
_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+", re.I)
_PEP440_FALLBACK = re.compile(r"^v?(?P<safe>(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*)", re.I)


def safe_identifier(name: str) -> str:
    """Make a string safe to be used as Python identifier.
    >>> safe_identifier("12abc")
    '_12abc'
    >>> safe_identifier("__editable__.myns.pkg-78.9.3_local")
    '__editable___myns_pkg_78_9_3_local'
    """
    safe = re.sub(r'\W|^(?=\d)', '_', name)
    assert safe.isidentifier()
    return safe


def safe_name(component: str) -> str:
    """Escape a component used as a project name according to Core Metadata.
    >>> safe_name("hello world")
    'hello-world'
    >>> safe_name("hello?world")
    'hello-world'
    >>> safe_name("hello_world")
    'hello_world'
    """
    return _UNSAFE_NAME_CHARS.sub("-", component)


def safe_version(version: str) -> str:
    """Convert an arbitrary string into a valid version string.
    Can still raise an ``InvalidVersion`` exception.
    To avoid exceptions use ``best_effort_version``.
    >>> safe_version("1988 12 25")
    '1988.12.25'
    >>> safe_version("v0.2.1")
    '0.2.1'
    >>> safe_version("v0.2?beta")
    '0.2b0'
    >>> safe_version("v0.2 beta")
    '0.2b0'
    >>> safe_version("ubuntu lts")
    Traceback (most recent call last):
    ...
    packaging.version.InvalidVersion: Invalid version: 'ubuntu.lts'
    """
    v = version.replace(' ', '.')
    try:
        return str(packaging.version.Version(v))
    except packaging.version.InvalidVersion:
        attempt = _UNSAFE_NAME_CHARS.sub("-", v)
        return str(packaging.version.Version(attempt))


def best_effort_version(version: str) -> str:
    """Convert an arbitrary string into a version-like string.
    Fallback when ``safe_version`` is not safe enough.
    >>> best_effort_version("v0.2 beta")
    '0.2b0'
    >>> best_effort_version("ubuntu lts")
    '0.dev0+sanitized.ubuntu.lts'
    >>> best_effort_version("0.23ubuntu1")
    '0.23.dev0+sanitized.ubuntu1'
    >>> best_effort_version("0.23-")
    '0.23.dev0+sanitized'
    >>> best_effort_version("0.-_")
    '0.dev0+sanitized'
    >>> best_effort_version("42.+?1")
    '42.dev0+sanitized.1'
    """
    try:
        return safe_version(version)
    except packaging.version.InvalidVersion:
        v = version.replace(' ', '.')
        match = _PEP440_FALLBACK.search(v)
        if match:
            safe = match["safe"]
            rest = v[len(safe) :]
        else:
            safe = "0"
            rest = version
        safe_rest = _NON_ALPHANUMERIC.sub(".", rest).strip(".")
        local = f"sanitized.{safe_rest}".strip(".")
        return safe_version(f"{safe}.dev0+{local}")


def safe_extra(extra: str) -> str:
    """Normalize extra name according to PEP 685
    >>> safe_extra("_FrIeNdLy-._.-bArD")
    'friendly-bard'
    >>> safe_extra("FrIeNdLy-._.-bArD__._-")
    'friendly-bard'
    """
    return _NON_ALPHANUMERIC.sub("-", extra).strip("-").lower()


def filename_component(value: str) -> str:
    """Normalize each component of a filename (e.g. distribution/version part of wheel)
    Note: ``value`` needs to be already normalized.
    >>> filename_component("my-pkg")
    'my_pkg'
    """
    return value.replace("-", "_").strip("_")


def filename_component_broken(value: str) -> str:
    """
    Produce the incorrect filename component for compatibility.

    See pypa/setuptools#4167 for detailed analysis.

    TODO: replace this with filename_component after pip 24 is
    nearly-ubiquitous.

    >>> filename_component_broken('foo_bar-baz')
    'foo-bar-baz'
    """
    return value.replace('_', '-')


def safer_name(value: str) -> str:
    """Like ``safe_name`` but can be used as filename component for wheel"""
    # See bdist_wheel.safer_name
    return (
        # Per https://packaging.python.org/en/latest/specifications/name-normalization/#name-normalization
        re.sub(r"[-_.]+", "-", safe_name(value))
        .lower()
        # Per https://packaging.python.org/en/latest/specifications/binary-distribution-format/#escaping-and-unicode
        .replace("-", "_")
    )


def safer_best_effort_version(value: str) -> str:
    """Like ``best_effort_version`` but can be used as filename component for wheel"""
    # See bdist_wheel.safer_verion
    # TODO: Replace with only safe_version in the future (no need for best effort)
    return filename_component(best_effort_version(value))


def _missing_canonicalize_license_expression(expression: str) -> str:
    """
    Defer import error to affect only users that actually use it
    https://github.com/pypa/setuptools/issues/4894
    >>> _missing_canonicalize_license_expression("a OR b")
    Traceback (most recent call last):
    ...
    ImportError: ...Cannot import `packaging.licenses`...
    """
    raise ImportError(
        "Cannot import `packaging.licenses`."
        """
        Setuptools>=77.0.0 requires "packaging>=24.2" to work properly.
        Please make sure you have a suitable version installed.
        """
    )


try:
    from packaging.licenses import (
        canonicalize_license_expression as _canonicalize_license_expression,
    )
except ImportError:  # pragma: nocover
    if not TYPE_CHECKING:
        # XXX: pyright is still upset even with # pyright: ignore[reportAssignmentType]
        _canonicalize_license_expression = _missing_canonicalize_license_expression

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\sbixStrike.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
from .sbixGlyph import Glyph
import struct

sbixStrikeHeaderFormat = """
	>
	ppem:          H	# The PPEM for which this strike was designed (e.g., 9,
						# 12, 24)
	resolution:    H	# The screen resolution (in dpi) for which this strike
						# was designed (e.g., 72)
"""

sbixGlyphDataOffsetFormat = """
	>
	glyphDataOffset:   L	# Offset from the beginning of the strike data record
							# to data for the individual glyph
"""

sbixStrikeHeaderFormatSize = sstruct.calcsize(sbixStrikeHeaderFormat)
sbixGlyphDataOffsetFormatSize = sstruct.calcsize(sbixGlyphDataOffsetFormat)


class Strike(object):
    def __init__(self, rawdata=None, ppem=0, resolution=72):
        self.data = rawdata
        self.ppem = ppem
        self.resolution = resolution
        self.glyphs = {}

    def decompile(self, ttFont):
        if self.data is None:
            from fontTools import ttLib

            raise ttLib.TTLibError
        if len(self.data) < sbixStrikeHeaderFormatSize:
            from fontTools import ttLib

            raise (
                ttLib.TTLibError,
                "Strike header too short: Expected %x, got %x.",
            ) % (sbixStrikeHeaderFormatSize, len(self.data))

        # read Strike header from raw data
        sstruct.unpack(
            sbixStrikeHeaderFormat, self.data[:sbixStrikeHeaderFormatSize], self
        )

        # calculate number of glyphs
        (firstGlyphDataOffset,) = struct.unpack(
            ">L",
            self.data[
                sbixStrikeHeaderFormatSize : sbixStrikeHeaderFormatSize
                + sbixGlyphDataOffsetFormatSize
            ],
        )
        self.numGlyphs = (
            firstGlyphDataOffset - sbixStrikeHeaderFormatSize
        ) // sbixGlyphDataOffsetFormatSize - 1
        # ^ -1 because there's one more offset than glyphs

        # build offset list for single glyph data offsets
        self.glyphDataOffsets = []
        for i in range(
            self.numGlyphs + 1
        ):  # + 1 because there's one more offset than glyphs
            start = i * sbixGlyphDataOffsetFormatSize + sbixStrikeHeaderFormatSize
            (current_offset,) = struct.unpack(
                ">L", self.data[start : start + sbixGlyphDataOffsetFormatSize]
            )
            self.glyphDataOffsets.append(current_offset)

        # iterate through offset list and slice raw data into glyph data records
        for i in range(self.numGlyphs):
            current_glyph = Glyph(
                rawdata=self.data[
                    self.glyphDataOffsets[i] : self.glyphDataOffsets[i + 1]
                ],
                gid=i,
            )
            current_glyph.decompile(ttFont)
            self.glyphs[current_glyph.glyphName] = current_glyph
        del self.glyphDataOffsets
        del self.numGlyphs
        del self.data

    def compile(self, ttFont):
        self.glyphDataOffsets = b""
        self.bitmapData = b""

        glyphOrder = ttFont.getGlyphOrder()

        # first glyph starts right after the header
        currentGlyphDataOffset = (
            sbixStrikeHeaderFormatSize
            + sbixGlyphDataOffsetFormatSize * (len(glyphOrder) + 1)
        )
        for glyphName in glyphOrder:
            if glyphName in self.glyphs:
                # we have glyph data for this glyph
                current_glyph = self.glyphs[glyphName]
            else:
                # must add empty glyph data record for this glyph
                current_glyph = Glyph(glyphName=glyphName)
            current_glyph.compile(ttFont)
            current_glyph.glyphDataOffset = currentGlyphDataOffset
            self.bitmapData += current_glyph.rawdata
            currentGlyphDataOffset += len(current_glyph.rawdata)
            self.glyphDataOffsets += sstruct.pack(
                sbixGlyphDataOffsetFormat, current_glyph
            )

        # add last "offset", really the end address of the last glyph data record
        dummy = Glyph()
        dummy.glyphDataOffset = currentGlyphDataOffset
        self.glyphDataOffsets += sstruct.pack(sbixGlyphDataOffsetFormat, dummy)

        # pack header
        self.data = sstruct.pack(sbixStrikeHeaderFormat, self)
        # add offsets and image data after header
        self.data += self.glyphDataOffsets + self.bitmapData

    def toXML(self, xmlWriter, ttFont):
        xmlWriter.begintag("strike")
        xmlWriter.newline()
        xmlWriter.simpletag("ppem", value=self.ppem)
        xmlWriter.newline()
        xmlWriter.simpletag("resolution", value=self.resolution)
        xmlWriter.newline()
        glyphOrder = ttFont.getGlyphOrder()
        for i in range(len(glyphOrder)):
            if glyphOrder[i] in self.glyphs:
                self.glyphs[glyphOrder[i]].toXML(xmlWriter, ttFont)
                # TODO: what if there are more glyph data records than (glyf table) glyphs?
        xmlWriter.endtag("strike")
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name in ["ppem", "resolution"]:
            setattr(self, name, safeEval(attrs["value"]))
        elif name == "glyph":
            if "graphicType" in attrs:
                myFormat = safeEval("'''" + attrs["graphicType"] + "'''")
            else:
                myFormat = None
            if "glyphname" in attrs:
                myGlyphName = safeEval("'''" + attrs["glyphname"] + "'''")
            elif "name" in attrs:
                myGlyphName = safeEval("'''" + attrs["name"] + "'''")
            else:
                from fontTools import ttLib

                raise ttLib.TTLibError("Glyph must have a glyph name.")
            if "originOffsetX" in attrs:
                myOffsetX = safeEval(attrs["originOffsetX"])
            else:
                myOffsetX = 0
            if "originOffsetY" in attrs:
                myOffsetY = safeEval(attrs["originOffsetY"])
            else:
                myOffsetY = 0
            current_glyph = Glyph(
                glyphName=myGlyphName,
                graphicType=myFormat,
                originOffsetX=myOffsetX,
                originOffsetY=myOffsetY,
            )
            for element in content:
                if isinstance(element, tuple):
                    name, attrs, content = element
                    current_glyph.fromXML(name, attrs, content, ttFont)
                    current_glyph.compile(ttFont)
            self.glyphs[current_glyph.glyphName] = current_glyph
        else:
            from fontTools import ttLib

            raise ttLib.TTLibError("can't handle '%s' element" % name)

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\zip.py ===
import os
import zipfile

import fsspec
from fsspec.archive import AbstractArchiveFileSystem


class ZipFileSystem(AbstractArchiveFileSystem):
    """Read/Write contents of ZIP archive as a file-system

    Keeps file object open while instance lives.

    This class is pickleable, but not necessarily thread-safe
    """

    root_marker = ""
    protocol = "zip"
    cachable = False

    def __init__(
        self,
        fo="",
        mode="r",
        target_protocol=None,
        target_options=None,
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
        compresslevel=None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        fo: str or file-like
            Contains ZIP, and must exist. If a str, will fetch file using
            :meth:`~fsspec.open_files`, which must return one file exactly.
        mode: str
            Accept: "r", "w", "a"
        target_protocol: str (optional)
            If ``fo`` is a string, this value can be used to override the
            FS protocol inferred from a URL
        target_options: dict (optional)
            Kwargs passed when instantiating the target FS, if ``fo`` is
            a string.
        compression, allowZip64, compresslevel: passed to ZipFile
            Only relevant when creating a ZIP
        """
        super().__init__(self, **kwargs)
        if mode not in set("rwa"):
            raise ValueError(f"mode '{mode}' no understood")
        self.mode = mode
        if isinstance(fo, (str, os.PathLike)):
            if mode == "a":
                m = "r+b"
            else:
                m = mode + "b"
            fo = fsspec.open(
                fo, mode=m, protocol=target_protocol, **(target_options or {})
            )
        self.force_zip_64 = allowZip64
        self.of = fo
        self.fo = fo.__enter__()  # the whole instance is a context
        self.zip = zipfile.ZipFile(
            self.fo,
            mode=mode,
            compression=compression,
            allowZip64=allowZip64,
            compresslevel=compresslevel,
        )
        self.dir_cache = None

    @classmethod
    def _strip_protocol(cls, path):
        # zip file paths are always relative to the archive root
        return super()._strip_protocol(path).lstrip("/")

    def __del__(self):
        if hasattr(self, "zip"):
            self.close()
            del self.zip

    def close(self):
        """Commits any write changes to the file. Done on ``del`` too."""
        self.zip.close()

    def _get_dirs(self):
        if self.dir_cache is None or self.mode in set("wa"):
            # when writing, dir_cache is always in the ZipFile's attributes,
            # not read from the file.
            files = self.zip.infolist()
            self.dir_cache = {
                dirname.rstrip("/"): {
                    "name": dirname.rstrip("/"),
                    "size": 0,
                    "type": "directory",
                }
                for dirname in self._all_dirnames(self.zip.namelist())
            }
            for z in files:
                f = {s: getattr(z, s, None) for s in zipfile.ZipInfo.__slots__}
                f.update(
                    {
                        "name": z.filename.rstrip("/"),
                        "size": z.file_size,
                        "type": ("directory" if z.is_dir() else "file"),
                    }
                )
                self.dir_cache[f["name"]] = f

    def pipe_file(self, path, value, **kwargs):
        # override upstream, because we know the exact file size in this case
        self.zip.writestr(path, value, **kwargs)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        path = self._strip_protocol(path)
        if "r" in mode and self.mode in set("wa"):
            if self.exists(path):
                raise OSError("ZipFS can only be open for reading or writing, not both")
            raise FileNotFoundError(path)
        if "r" in self.mode and "w" in mode:
            raise OSError("ZipFS can only be open for reading or writing, not both")
        out = self.zip.open(path, mode.strip("b"), force_zip64=self.force_zip_64)
        if "r" in mode:
            info = self.info(path)
            out.size = info["size"]
            out.name = info["name"]
        return out

    def find(self, path, maxdepth=None, withdirs=False, detail=False, **kwargs):
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        # Remove the leading slash, as the zip file paths are always
        # given without a leading slash
        path = path.lstrip("/")
        path_parts = list(filter(lambda s: bool(s), path.split("/")))

        def _matching_starts(file_path):
            file_parts = filter(lambda s: bool(s), file_path.split("/"))
            return all(a == b for a, b in zip(path_parts, file_parts))

        self._get_dirs()

        result = {}
        # To match posix find, if an exact file name is given, we should
        # return only that file
        if path in self.dir_cache and self.dir_cache[path]["type"] == "file":
            result[path] = self.dir_cache[path]
            return result if detail else [path]

        for file_path, file_info in self.dir_cache.items():
            if not (path == "" or _matching_starts(file_path)):
                continue

            if file_info["type"] == "directory":
                if withdirs:
                    if file_path not in result:
                        result[file_path.strip("/")] = file_info
                continue

            if file_path not in result:
                result[file_path] = file_info if detail else None

        if maxdepth:
            path_depth = path.count("/")
            result = {
                k: v for k, v in result.items() if k.count("/") - path_depth < maxdepth
            }
        return result if detail else sorted(result)

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\edge.py ===
from .chromium import ChromiumHeadless
from .search_utils import get_command_origin, find_first_defined_env_var

import subprocess
import platform
import os
import shutil

ENV_VAR_LOOKUP_TOGGLE = 'HTML2IMAGE_TOGGLE_ENV_VAR_LOOKUP'

EDGE_EXECUTABLE_ENV_VAR_CANDIDATES = [
    'HTML2IMAGE_EDGE_BIN',
    'HTML2IMAGE_EDGE_EXE',
    'EDGE_BIN',
    'EDGE_EXE',
]


def _find_edge(user_given_executable=None):
    """ Finds a edge executable.

    Search Edge on a given path. If no path given,
    try to find Edge or Chromium-browser on a Windows or Unix system.

    Parameters
    ----------
    - `user_given_executable`: str (optional)
        + A filepath leading to a Edge executable
        + Or a filename found in the current working directory
        + Or a keyword that executes Edge/ Chromium, ex:
            - 'msedge' on linux and windows systems (typing `start msedge` in a windows cmd works)

    Raises
    ------
    - `FileNotFoundError`
        + If a suitable edge executable could not be found.

    Returns
    -------
    - str
        + Path of the edge executable on the current machine.
    """

    # try to find a edge bin/exe in ENV
    path_from_env = find_first_defined_env_var(
        env_var_list=EDGE_EXECUTABLE_ENV_VAR_CANDIDATES,
        toggle=ENV_VAR_LOOKUP_TOGGLE
    )

    if path_from_env:
        print(
            f'Found a potential edge executable in the {path_from_env} '
            f'environment variable:\n{path_from_env}\n'
        )
        return path_from_env

    # if an executable is given, try to use it
    if user_given_executable is not None:

        # On Windows, we cannot "safely" validate that user_given_executable
        # seems to be a edge executable, as we cannot run it with
        # the --version flag.
        # https://bugs.chromium.org/p/chromium/issues/detail?id=158372
        #
        # We thus do the "bare minimum" and check if user_given_executable
        # is a file, a filepath, or corresponds to a keyword that can be used
        # with the start command, like so: `start user_given_executable`
        if platform.system() == 'Windows':
            command_origin = get_command_origin(user_given_executable)
            if command_origin:
                return command_origin

            # cannot validate user_given_executable
            raise FileNotFoundError()

        # On a non-Windows OS, we can validate in a basic way that
        # user_given_executable leads to a Edge executable,
        # or is a command, using the --version flag
        else:
            try:
                if 'edge' in subprocess.check_output(
                    [user_given_executable, '--version']
                ).decode('utf-8').lower():
                    return user_given_executable
            except Exception:
                pass

        # We got a user_given_executable but couldn't validate it
        raise FileNotFoundError(
            'Failed to find a seemingly valid edge executable '
            'in the given path.'
        )

    # Executable not in ENV or given by the user, try to find it
    # Search for executable on a Windows OS
    if platform.system() == 'Windows':
        prefixes = [
            os.getenv('PROGRAMFILES(X86)'),
            os.getenv('PROGRAMFILES'),
            os.getenv('LOCALAPPDATA'),
        ]

        suffix = "Microsoft\\Edge\\Application\\msedge.exe"

        for prefix in prefixes:
            path_candidate = os.path.join(prefix, suffix)
            if os.path.isfile(path_candidate):
                return path_candidate

    # Search for executable on a Linux OS
    elif platform.system() == "Linux":

        edge_commands = [
            'msedge',
            '/opt/microsoft/msedge/msedge'
        ]

        for edge_command in edge_commands:
            if shutil.which(edge_command):
                # check the --version for "edge" ?
                return edge_command

    # Search for executable on MacOS
    elif platform.system() == "Darwin":
        # MacOS system
        edge_app = (
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
        )

        try:
            version_result = subprocess.check_output(
                [edge_app, "--version"]
            )
            if "Microsoft Edge" in str(version_result):
                return edge_app
        except Exception:
            pass

    # Couldn't find an executable (or OS not in Windows, Linux or Mac)
    raise FileNotFoundError(
        'Could not find a Edge executable on this '
        'machine, please specify it yourself.'
    )

class EdgeHeadless(ChromiumHeadless):
    """
        Edge browser wrapper.

        Parameters
        ----------
        - `executable` : str, optional
            + Path to a edge executable.
        - `flags` : list of str
            + Flags to be used by the headless browser.
            + Default flags are :
                - '--default-background-color=00000000'
                - '--hide-scrollbars'
        - `print_command` : bool
            + Whether or not to print the command used to take a screenshot.
        - `disable_logging` : bool
            + Whether or not to disable Chrome's output.
        - `use_new_headless` : bool, optional
            + Whether or not to use the new headless mode.
            + By default, the old headless mode is used.
            + You can also keep the original behavior to backward compatibility by setting this to `None`.
    """

    def __init__(self, executable=None, flags=None, print_command=False, disable_logging=False, use_new_headless=None,):
        super().__init__(executable=executable, flags=flags, print_command=print_command, disable_logging=disable_logging, use_new_headless=use_new_headless)

    @property
    def executable(self):
        return self._executable

    @executable.setter
    def executable(self, value):
        self._executable = _find_edge(value)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\sagemaker\chat\handler.py ===
import json
from copy import deepcopy
from typing import Callable, Optional, Union

import httpx

from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.utils import ModelResponse, get_secret

from ..common_utils import AWSEventStreamDecoder
from .transformation import SagemakerChatConfig


class SagemakerChatHandler(BaseAWSLLM):
    def _load_credentials(
        self,
        optional_params: dict,
    ):
        try:
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_session_token, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_region_name = optional_params.pop("aws_region_name", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        optional_params.pop(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)

        ### SET REGION NAME ###
        if aws_region_name is None:
            # check env #
            litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)

            if litellm_aws_region_name is not None and isinstance(
                litellm_aws_region_name, str
            ):
                aws_region_name = litellm_aws_region_name

            standard_aws_region_name = get_secret("AWS_REGION", None)
            if standard_aws_region_name is not None and isinstance(
                standard_aws_region_name, str
            ):
                aws_region_name = standard_aws_region_name

            if aws_region_name is None:
                aws_region_name = "us-west-2"

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
        return credentials, aws_region_name

    def _prepare_request(
        self,
        credentials,
        model: str,
        data: dict,
        optional_params: dict,
        aws_region_name: str,
        extra_headers: Optional[dict] = None,
    ):
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        sigv4 = SigV4Auth(credentials, "sagemaker", aws_region_name)
        if optional_params.get("stream") is True:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations-response-stream"
        else:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations"

        sagemaker_base_url = optional_params.get("sagemaker_base_url", None)
        if sagemaker_base_url is not None:
            api_base = sagemaker_base_url

        encoded_data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}
        request = AWSRequest(
            method="POST", url=api_base, data=encoded_data, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]

        prepped_request = request.prepare()

        return prepped_request

    def completion(
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        optional_params: dict,
        litellm_params: dict,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        custom_prompt_dict={},
        logger_fn=None,
        acompletion: bool = False,
        headers: dict = {},
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ):
        # pop streaming if it's in the optional params as 'stream' raises an error with sagemaker
        credentials, aws_region_name = self._load_credentials(optional_params)
        inference_params = deepcopy(optional_params)
        stream = inference_params.pop("stream", None)

        from litellm.llms.openai_like.chat.handler import OpenAILikeChatHandler

        openai_like_chat_completions = OpenAILikeChatHandler()
        inference_params["stream"] = True if stream is True else False
        _data = SagemakerChatConfig().transform_request(
            model=model,
            messages=messages,
            optional_params=inference_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        prepared_request = self._prepare_request(
            model=model,
            data=_data,
            optional_params=optional_params,
            credentials=credentials,
            aws_region_name=aws_region_name,
        )

        custom_stream_decoder = AWSEventStreamDecoder(model="", is_messages_api=True)

        return openai_like_chat_completions.completion(
            model=model,
            messages=messages,
            api_base=prepared_request.url,
            api_key=None,
            custom_prompt_dict=custom_prompt_dict,
            model_response=model_response,
            print_verbose=print_verbose,
            logging_obj=logging_obj,
            optional_params=inference_params,
            acompletion=acompletion,
            litellm_params=litellm_params,
            logger_fn=logger_fn,
            timeout=timeout,
            encoding=encoding,
            headers=prepared_request.headers,  # type: ignore
            custom_endpoint=True,
            custom_llm_provider="sagemaker_chat",
            streaming_decoder=custom_stream_decoder,  # type: ignore
            client=client,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\assistant_update_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, TypedDict

from .assistant_tool_param import AssistantToolParam
from ..shared_params.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from .assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = ["AssistantUpdateParams", "ToolResources", "ToolResourcesCodeInterpreter", "ToolResourcesFileSearch"]


class AssistantUpdateParams(TypedDict, total=False):
    description: Optional[str]
    """The description of the assistant. The maximum length is 512 characters."""

    instructions: Optional[str]
    """The system instructions that the assistant uses.

    The maximum length is 256,000 characters.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

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
    """ID of the model to use.

    You can use the
    [List models](https://platform.openai.com/docs/api-reference/models/list) API to
    see all of your available models, or see our
    [Model overview](https://platform.openai.com/docs/models) for descriptions of
    them.
    """

    name: Optional[str]
    """The name of the assistant. The maximum length is 256 characters."""

    reasoning_effort: Optional[ReasoningEffort]
    """**o-series models only**

    Constrains effort on reasoning for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
    supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
    result in faster responses and fewer tokens used on reasoning in a response.
    """

    response_format: Optional[AssistantResponseFormatOptionParam]
    """Specifies the format that the model must output.

    Compatible with [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
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
    """

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic.
    """

    tool_resources: Optional[ToolResources]
    """A set of resources that are used by the assistant's tools.

    The resources are specific to the type of tool. For example, the
    `code_interpreter` tool requires a list of file IDs, while the `file_search`
    tool requires a list of vector store IDs.
    """

    tools: Iterable[AssistantToolParam]
    """A list of tool enabled on the assistant.

    There can be a maximum of 128 tools per assistant. Tools can be of types
    `code_interpreter`, `file_search`, or `function`.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or temperature but not both.
    """


class ToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    Overrides the list of
    [file](https://platform.openai.com/docs/api-reference/files) IDs made available
    to the `code_interpreter` tool. There can be a maximum of 20 files associated
    with the tool.
    """


class ToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    Overrides the
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this assistant. There can be a maximum of 1 vector store attached to
    the assistant.
    """


class ToolResources(TypedDict, total=False):
    code_interpreter: ToolResourcesCodeInterpreter

    file_search: ToolResourcesFileSearch

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\__init__.py ===
"""Rich text and beautiful formatting in the terminal."""

import os
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, Union

from ._extension import load_ipython_extension  # noqa: F401

__all__ = ["get_console", "reconfigure", "print", "inspect", "print_json"]

if TYPE_CHECKING:
    from .console import Console

# Global console used by alternative print
_console: Optional["Console"] = None

try:
    _IMPORT_CWD = os.path.abspath(os.getcwd())
except FileNotFoundError:
    # Can happen if the cwd has been deleted
    _IMPORT_CWD = ""


def get_console() -> "Console":
    """Get a global :class:`~rich.console.Console` instance. This function is used when Rich requires a Console,
    and hasn't been explicitly given one.

    Returns:
        Console: A console instance.
    """
    global _console
    if _console is None:
        from .console import Console

        _console = Console()

    return _console


def reconfigure(*args: Any, **kwargs: Any) -> None:
    """Reconfigures the global console by replacing it with another.

    Args:
        *args (Any): Positional arguments for the replacement :class:`~rich.console.Console`.
        **kwargs (Any): Keyword arguments for the replacement :class:`~rich.console.Console`.
    """
    from pip._vendor.rich.console import Console

    new_console = Console(*args, **kwargs)
    _console = get_console()
    _console.__dict__ = new_console.__dict__


def print(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[IO[str]] = None,
    flush: bool = False,
) -> None:
    r"""Print object(s) supplied via positional arguments.
    This function has an identical signature to the built-in print.
    For more advanced features, see the :class:`~rich.console.Console` class.

    Args:
        sep (str, optional): Separator between printed objects. Defaults to " ".
        end (str, optional): Character to write at end of output. Defaults to "\\n".
        file (IO[str], optional): File to write to, or None for stdout. Defaults to None.
        flush (bool, optional): Has no effect as Rich always flushes output. Defaults to False.

    """
    from .console import Console

    write_console = get_console() if file is None else Console(file=file)
    return write_console.print(*objects, sep=sep, end=end)


def print_json(
    json: Optional[str] = None,
    *,
    data: Any = None,
    indent: Union[None, int, str] = 2,
    highlight: bool = True,
    skip_keys: bool = False,
    ensure_ascii: bool = False,
    check_circular: bool = True,
    allow_nan: bool = True,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
) -> None:
    """Pretty prints JSON. Output will be valid JSON.

    Args:
        json (str): A string containing JSON.
        data (Any): If json is not supplied, then encode this data.
        indent (int, optional): Number of spaces to indent. Defaults to 2.
        highlight (bool, optional): Enable highlighting of output: Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    get_console().print_json(
        json,
        data=data,
        indent=indent,
        highlight=highlight,
        skip_keys=skip_keys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        default=default,
        sort_keys=sort_keys,
    )


def inspect(
    obj: Any,
    *,
    console: Optional["Console"] = None,
    title: Optional[str] = None,
    help: bool = False,
    methods: bool = False,
    docs: bool = True,
    private: bool = False,
    dunder: bool = False,
    sort: bool = True,
    all: bool = False,
    value: bool = True,
) -> None:
    """Inspect any Python object.

    * inspect(<OBJECT>) to see summarized info.
    * inspect(<OBJECT>, methods=True) to see methods.
    * inspect(<OBJECT>, help=True) to see full (non-abbreviated) help.
    * inspect(<OBJECT>, private=True) to see private attributes (single underscore).
    * inspect(<OBJECT>, dunder=True) to see attributes beginning with double underscore.
    * inspect(<OBJECT>, all=True) to see all attributes.

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
        value (bool, optional): Pretty print value. Defaults to True.
    """
    _console = console or get_console()
    from pip._vendor.rich._inspect import Inspect

    # Special case for inspect(inspect)
    is_inspect = obj is inspect

    _inspect = Inspect(
        obj,
        title=title,
        help=is_inspect or help,
        methods=is_inspect or methods,
        docs=is_inspect or docs,
        private=private,
        dunder=dunder,
        sort=sort,
        all=all,
        value=value,
    )
    _console.print(_inspect)


if __name__ == "__main__":  # pragma: no cover
    print("Hello, **World**")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\tablegen.py ===
"""
    pygments.lexers.tablegen
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for LLVM's TableGen DSL.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words, using
from pygments.lexers.c_cpp import CppLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, \
    Punctuation, String, Text, Whitespace, Error

__all__ = ['TableGenLexer']

KEYWORDS = (
    'assert',
    'class',
    'code',
    'def',
    'dump',
    'else',
    'foreach',
    'defm',
    'defset',
    'defvar',
    'field',
    'if',
    'in',
    'include',
    'let',
    'multiclass',
    'then',
)

KEYWORDS_CONST = (
    'false',
    'true',
)
KEYWORDS_TYPE = (
    'bit',
    'bits',
    'dag',
    'int',
    'list',
    'string',
)

BANG_OPERATORS = (
    'add',
    'and',
    'cast',
    'con',
    'cond',
    'dag',
    'div',
    'empty',
    'eq',
    'exists',
    'filter',
    'find',
    'foldl',
    'foreach',
    'ge',
    'getdagarg',
    'getdagname',
    'getdagop',
    'gt',
    'head',
    'if',
    'interleave',
    'isa',
    'le',
    'listconcat',
    'listremove',
    'listsplat',
    'logtwo',
    'lt',
    'mul',
    'ne',
    'not',
    'or',
    'range',
    'repr',
    'setdagarg',
    'setdagname',
    'setdagop',
    'shl',
    'size',
    'sra',
    'srl',
    'strconcat',
    'sub',
    'subst',
    'substr',
    'tail',
    'tolower',
    'toupper',
    'xor',
)

class TableGenLexer(RegexLexer):
    """
    Lexer for TableGen
    """

    name = 'TableGen'
    url = 'https://llvm.org/docs/TableGen/ProgRef.html'
    aliases = ['tablegen', 'td']
    filenames = ['*.td']

    version_added = '2.19'

    tokens = {
        'root': [
            (r'\s+', Whitespace),

            (r'/\*', Comment.Multiline, 'comment'),
            (r'//.*?$', Comment.SingleLine),
            (r'#(define|ifdef|ifndef|else|endif)', Comment.Preproc),

            # Binary/hex numbers. Note that these take priority over names,
            # which may begin with numbers.
            (r'0b[10]+', Number.Bin),
            (r'0x[0-9a-fA-F]+', Number.Hex),

            # Keywords
            (words(KEYWORDS, suffix=r'\b'), Keyword),
            (words(KEYWORDS_CONST, suffix=r'\b'), Keyword.Constant),
            (words(KEYWORDS_TYPE, suffix=r'\b'), Keyword.Type),

            # Bang operators
            (words(BANG_OPERATORS, prefix=r'\!', suffix=r'\b'), Operator),
            # Unknown bang operators are an error
            (r'![a-zA-Z]+', Error),

            # Names and identifiers
            (r'[0-9]*[a-zA-Z_][a-zA-Z_0-9]*', Name),
            (r'\$[a-zA-Z_][a-zA-Z_0-9]*', Name.Variable),

            # Place numbers after keywords. Names/identifiers may begin with
            # numbers, and we want to parse 1X as one name token as opposed to
            # a number and a name.
            (r'[-\+]?[0-9]+', Number.Integer),

            # String literals
            (r'"', String, 'dqs'),
            (r'\[\{', Text, 'codeblock'),

            # Misc. punctuation
            (r'[-+\[\]{}()<>\.,;:=?#]+', Punctuation),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'strings': [
            (r'\\[\\\'"tn]', String.Escape),
            (r'[^\\"]+', String),
        ],
        # Double-quoted string, a la C
        'dqs': [
            (r'"', String, '#pop'),
            include('strings'),
        ],
        # No escaping inside a code block - everything is literal
        # Assume that the code inside a code block is C++. This isn't always
        # true in TableGen, but is the far most common scenario.
        'codeblock': [
            (r'\}\]', Text, '#pop'),
            (r'([^}]+|\}[^]])*', using(CppLexer)),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\server.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import collections
import os
import re
import shutil
import socket
import subprocess
import time
import urllib

from selenium.webdriver.common.selenium_manager import SeleniumManager


class Server:
    """Manage a Selenium Grid (Remote) Server in standalone mode.

    This class contains functionality for downloading the server and starting/stopping it.

    For more information on Selenium Grid, see:
        - https://www.selenium.dev/documentation/grid/getting_started/

    Parameters:
    -----------
    host : str
        Hostname or IP address to bind to (determined automatically if not specified)
    port : int or str
        Port to listen on (4444 if not specified)
    path : str
        Path/filename of existing server .jar file (Selenium Manager is used if not specified)
    version : str
        Version of server to download (latest version if not specified)
    log_level : str
        Logging level to control logging output ("INFO" if not specified)
        Available levels: "SEVERE", "WARNING", "INFO", "CONFIG", "FINE", "FINER", "FINEST"
    env: collections.abc.Mapping
        Mapping that defines the environment variables for the server process
    """

    def __init__(self, host=None, port=4444, path=None, version=None, log_level="INFO", env=None):
        if path and version:
            raise TypeError("Not allowed to specify a version when using an existing server path")

        self.host = host
        self.port = self._validate_port(port)
        self.path = self._validate_path(path)
        self.version = self._validate_version(version)
        self.log_level = self._validate_log_level(log_level)
        self.env = self._validate_env(env)

        self.process = None
        self.status_url = self._get_status_url()

    def _get_status_url(self):
        host = self.host if self.host is not None else "localhost"
        return f"http://{host}:{self.port}/status"

    def _validate_path(self, path):
        if path and not os.path.exists(path):
            raise OSError(f"Can't find server .jar located at {path}")
        return path

    def _validate_port(self, port):
        try:
            port = int(port)
        except ValueError:
            raise TypeError(f"{__class__.__name__}.__init__() got an invalid port: '{port}'")
        if not (0 <= port <= 65535):
            raise ValueError("port must be 0-65535")
        return port

    def _validate_version(self, version):
        if version:
            if not re.match(r"^\d+\.\d+\.\d+$", str(version)):
                raise TypeError(f"{__class__.__name__}.__init__() got an invalid version: '{version}'")
        return version

    def _validate_log_level(self, log_level):
        levels = ("SEVERE", "WARNING", "INFO", "CONFIG", "FINE", "FINER", "FINEST")
        if log_level not in levels:
            raise TypeError(f"log_level must be one of: {', '.join(levels)}")
        return log_level

    def _validate_env(self, env):
        if env is not None and not isinstance(env, collections.abc.Mapping):
            raise TypeError("env must be a mapping of environment variables")
        return env

    def _wait_for_server(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                urllib.request.urlopen(self.status_url)
                return True
            except urllib.error.URLError:
                time.sleep(0.2)
        return False

    def download_if_needed(self, version=None):
        """Download the server if it doesn't already exist.

        Latest version is downloaded unless specified.
        """
        args = ["--grid"]
        if version is not None:
            args.append(version)
        return SeleniumManager().binary_paths(args)["driver_path"]

    def start(self):
        """Start the server.

        Selenium Manager will detect the server location and download it if necessary,
        unless an existing server path was specified.
        """
        path = self.download_if_needed(self.version) if self.path is None else self.path

        java_path = shutil.which("java")
        if java_path is None:
            raise OSError("Can't find java on system PATH. JRE is required to run the Selenium server")

        command = [
            java_path,
            "-jar",
            path,
            "standalone",
            "--port",
            str(self.port),
            "--log-level",
            self.log_level,
            "--selenium-manager",
            "true",
            "--enable-managed-downloads",
            "true",
        ]
        if self.host is not None:
            command.extend(["--host", self.host])

        host = self.host if self.host is not None else "localhost"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, self.port))
            raise ConnectionError(f"Selenium server is already running, or something else is using port {self.port}")
        except ConnectionRefusedError:
            print("Starting Selenium server...")
            self.process = subprocess.Popen(command, env=self.env)
            print(f"Selenium server running as process: {self.process.pid}")
            if not self._wait_for_server():
                raise TimeoutError(f"Timed out waiting for Selenium server at {self.status_url}")
            print("Selenium server is ready")
        return self.process

    def stop(self):
        """Stop the server."""
        if self.process is None:
            raise RuntimeError("Selenium server isn't running")
        else:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait()
            self.process = None
            print("Selenium server has been terminated")

# === NexusCore/openenv\Lib\site-packages\win32\Demos\win32gui_demo.py ===
# The start of a win32gui generic demo.
# Feel free to contribute more demos back ;-)

import math
import random
import time

import win32api
import win32con
import win32gui


def _MyCallback(hwnd, extra):
    hwnds, classes = extra
    hwnds.append(hwnd)
    classes[win32gui.GetClassName(hwnd)] = 1


def TestEnumWindows():
    windows = []
    classes = {}
    win32gui.EnumWindows(_MyCallback, (windows, classes))
    print(
        "Enumerated a total of %d windows with %d classes"
        % (len(windows), len(classes))
    )
    if "tooltips_class32" not in classes:
        print("Hrmmmm - I'm very surprised to not find a 'tooltips_class32' class.")


def OnPaint_1(hwnd, msg, wp, lp):
    dc, ps = win32gui.BeginPaint(hwnd)
    win32gui.SetGraphicsMode(dc, win32con.GM_ADVANCED)
    br = win32gui.CreateSolidBrush(win32api.RGB(255, 0, 0))
    win32gui.SelectObject(dc, br)
    angle = win32gui.GetWindowLong(hwnd, win32con.GWL_USERDATA)
    win32gui.SetWindowLong(hwnd, win32con.GWL_USERDATA, angle + 2)
    r_angle = angle * (math.pi / 180)
    win32gui.SetWorldTransform(
        dc,
        {
            "M11": math.cos(r_angle),
            "M12": math.sin(r_angle),
            "M21": math.sin(r_angle) * -1,
            "M22": math.cos(r_angle),
            "Dx": 250,
            "Dy": 250,
        },
    )
    win32gui.MoveToEx(dc, 250, 250)
    win32gui.BeginPath(dc)
    win32gui.Pie(dc, 10, 70, 200, 200, 350, 350, 75, 10)
    win32gui.Chord(dc, 200, 200, 850, 0, 350, 350, 75, 10)
    win32gui.LineTo(dc, 300, 300)
    win32gui.LineTo(dc, 100, 20)
    win32gui.LineTo(dc, 20, 100)
    win32gui.LineTo(dc, 400, 0)
    win32gui.LineTo(dc, 0, 400)
    win32gui.EndPath(dc)
    win32gui.StrokeAndFillPath(dc)
    win32gui.EndPaint(hwnd, ps)
    return 0


wndproc_1 = {win32con.WM_PAINT: OnPaint_1}


def OnPaint_2(hwnd, msg, wp, lp):
    dc, ps = win32gui.BeginPaint(hwnd)
    win32gui.SetGraphicsMode(dc, win32con.GM_ADVANCED)
    l, t, r, b = win32gui.GetClientRect(hwnd)

    for x in range(25):
        vertices = (
            {
                "x": int(random.random() * r),
                "y": int(random.random() * b),
                "Red": int(random.random() * 0xFF00),
                "Green": 0,
                "Blue": 0,
                "Alpha": 0,
            },
            {
                "x": int(random.random() * r),
                "y": int(random.random() * b),
                "Red": 0,
                "Green": int(random.random() * 0xFF00),
                "Blue": 0,
                "Alpha": 0,
            },
            {
                "x": int(random.random() * r),
                "y": int(random.random() * b),
                "Red": 0,
                "Green": 0,
                "Blue": int(random.random() * 0xFF00),
                "Alpha": 0,
            },
        )
        mesh = ((0, 1, 2),)
        win32gui.GradientFill(dc, vertices, mesh, win32con.GRADIENT_FILL_TRIANGLE)
    win32gui.EndPaint(hwnd, ps)
    return 0


wndproc_2 = {win32con.WM_PAINT: OnPaint_2}


def TestSetWorldTransform():
    wc = win32gui.WNDCLASS()
    wc.lpszClassName = "test_win32gui_1"
    wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
    wc.hbrBackground = win32con.COLOR_WINDOW + 1
    wc.lpfnWndProc = wndproc_1
    class_atom = win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindow(
        wc.lpszClassName,
        "Spin the Lobster!",
        win32con.WS_CAPTION | win32con.WS_VISIBLE,
        100,
        100,
        900,
        900,
        0,
        0,
        0,
        None,
    )
    for x in range(500):
        win32gui.InvalidateRect(hwnd, None, True)
        win32gui.PumpWaitingMessages()
        time.sleep(0.01)
    win32gui.DestroyWindow(hwnd)
    win32gui.UnregisterClass(wc.lpszClassName, None)


def TestGradientFill():
    wc = win32gui.WNDCLASS()
    wc.lpszClassName = "test_win32gui_2"
    wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
    wc.hbrBackground = win32con.COLOR_WINDOW + 1
    wc.lpfnWndProc = wndproc_2
    class_atom = win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindowEx(
        0,
        class_atom,
        "Kaleidoscope",
        win32con.WS_CAPTION
        | win32con.WS_VISIBLE
        | win32con.WS_THICKFRAME
        | win32con.WS_SYSMENU,
        100,
        100,
        900,
        900,
        0,
        0,
        0,
        None,
    )
    s = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, s | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, 0, 175, win32con.LWA_ALPHA)
    for x in range(30):
        win32gui.InvalidateRect(hwnd, None, True)
        win32gui.PumpWaitingMessages()
        time.sleep(0.3)
    win32gui.DestroyWindow(hwnd)
    win32gui.UnregisterClass(class_atom, None)


print("Enumerating all windows...")
TestEnumWindows()
print("Testing drawing functions ...")
TestSetWorldTransform()
TestGradientFill()
print("All tests done!")

# === NexusCore/evaluation\evalplus\codegen\generate.py ===
import os
from os import PathLike
from typing import List

from model import DecoderBase, make_model
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)


def construct_contract_prompt(prompt: str, contract_type: str, contract: str) -> str:
    if contract_type == "none":
        return prompt
    elif contract_type == "docstring":
        # embed within the docstring
        sep = ""
        if '"""' in prompt:
            sep = '"""'
        elif "'''" in prompt:
            sep = "'''"
        assert sep != ""
        l = prompt.split(sep)
        contract = "\n".join([x.split("#")[0] for x in contract.splitlines()])
        l[1] = (
            l[1] + contract + "\n" + " " * (len(contract) - len(contract.lstrip()) - 1)
        )
        return sep.join(l)
    elif contract_type == "code":
        # at the beginning of the function
        contract = "\n".join([x.split("#")[0] for x in contract.splitlines()])
        return prompt + contract


def codegen(
    workdir: PathLike,
    model: DecoderBase,
    dataset: str,
    greedy=False,
    n_samples=1,
    id_range=None,
    version="default",
    resume=True,
):
    with Progress(
        TextColumn(f"{dataset} •" + "[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ) as p:
        if dataset == "humaneval":
            from evalplus.data import get_human_eval_plus

            dataset = get_human_eval_plus(version=version)
        elif dataset == "mbpp":
            from evalplus.data import get_mbpp_plus

            dataset = get_mbpp_plus(version=version)

        for task_id, task in p.track(dataset.items()):
            if id_range is not None:
                id_num = int(task_id.split("/")[1])
                low, high = id_range
                if id_num < low or id_num >= high:
                    p.console.print(f"Skipping {task_id} as it is not in {id_range}")
                    continue

            p_name = task_id.replace("/", "_")
            os.makedirs(os.path.join(workdir, p_name), exist_ok=True)
            log = f"Codegen: {p_name} @ {model}"
            n_existing = 0
            if resume:
                # count existing .py files
                n_existing = len(
                    [
                        f
                        for f in os.listdir(os.path.join(workdir, p_name))
                        if f.endswith(".py")
                    ]
                )
                if n_existing > 0:
                    log += f" (resuming from {n_existing})"

            nsamples = n_samples - n_existing
            p.console.print(log)

            sidx = n_samples - nsamples
            while sidx < n_samples:
                outputs = model.codegen(
                    task["prompt"],
                    do_sample=not greedy,
                    num_samples=n_samples - sidx,
                )
                assert outputs, "No outputs from model!"
                for impl in outputs:
                    try:
                        with open(
                            os.path.join(workdir, p_name, f"{sidx}.py"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            if model.is_direct_completion():
                                f.write(task["prompt"] + impl)
                            else:
                                f.write(impl)
                    except UnicodeEncodeError:
                        continue
                    sidx += 1


def main(
    model: str,
    dataset: str,
    root: str,
    bs: int = 1,
    n_samples: int = 1,
    temperature: float = 0.0,
    resume: bool = True,
    greedy: bool = False,
    id_range: List = None,
    version: str = "default",
    backend: str = "vllm",
    base_url: str = None,
    tp: int = 1,
):
    assert dataset in ["humaneval", "mbpp"], f"Invalid dataset {dataset}"
    assert backend in ["vllm", "hf", "openai"]

    if greedy and (temperature != 0 or bs != 1 or n_samples != 1):
        temperature = 0
        bs = 1
        n_samples = 1
        print("Greedy decoding ON (--greedy): setting bs=1, n_samples=1, temperature=0")

    if id_range is not None:
        assert len(id_range) == 2, "id_range must be a list of length 2"
        assert id_range[0] < id_range[1], "id_range must be increasing"
        id_range = tuple(id_range)

    # Make project dir
    os.makedirs(root, exist_ok=True)
    # Make dataset dir
    os.makedirs(os.path.join(root, dataset), exist_ok=True)
    # Make dir for codes generated by each model
    model_runner = make_model(
        model=model,
        backend=backend,
        batch_size=bs,
        temperature=temperature,
        dataset=dataset,
        base_url=base_url,
        tp=tp,
    )
    identifier = model.replace("/", "--") + f"_{backend}_temp_{temperature}"
    workdir = os.path.join(root, dataset, identifier)
    os.makedirs(workdir, exist_ok=True)
    codegen(
        workdir=workdir,
        dataset=dataset,
        greedy=greedy,
        model=model_runner,
        n_samples=n_samples,
        resume=resume,
        id_range=id_range,
        version=version,
    )


if __name__ == "__main__":
    from fire import Fire

    Fire(main)

# === NexusCore/exported_projects\app_20250703_223016\tools\research_tool.py ===
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import random
import os
import re
from urllib.parse import urljoin

# ====================
# 設定部分（必要に応じて変更）
# ====================
BASE_URL = "https://www.buyma.com/r/_%s/"  # ブランド名を%sに挿入
BRANDS = ["GUCCI", "PRADA"]                # 対象ブランドリスト
MAX_PAGES = 2                              # 最大取得ページ数
DELAY_RANGE = (10, 30)                     # ランダム待機時間（秒）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)..."
]
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
]

# ====================
# Chrome設定
# ====================
def setup_driver():
    chrome_options = Options()
    
    # Headlessモード
    chrome_options.add_argument("--headless=new")
    
    # プロキシ設定
    chrome_options.add_argument(f"--proxy-server={random.choice(PROXIES)}")
    
    # ユーザーエージェントローテーション
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # 基本設定
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=chrome_options)

# ====================
# 商品詳細取得関数
# ====================
def get_product_details(driver, product_url):
    """商品詳細ページから追加情報を取得"""
    try:
        driver.get(product_url)
        time.sleep(random.uniform(*DELAY_RANGE))
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_detail"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 追加情報取得例
        description = soup.select_one('div.product_description').text.strip()[:200] + "..." if soup.select_one('div.product_description') else ""
        seller_info = soup.select_one('div.seller_profile').text.strip()[:100] + "..." if soup.select_one('div.seller_profile') else ""
        
        return {
            'description': description,
            'seller_info': seller_info
        }
        
    except Exception as e:
        print(f"詳細ページエラー: {str(e)}")
        return {}

# ====================
# メインスクレイピング関数
# ====================
def scrape_brand(driver, brand):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', f'buyma_{brand.lower()}_products.csv')
    products = []
    
    for page in range(1, MAX_PAGES + 1):
        try:
            # ページアクセス
            url = BASE_URL % brand + f"?pageno={page}"
            driver.get(url)
            time.sleep(random.uniform(*DELAY_RANGE))
            
            # 商品コンテナ待機
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_body"))
            )
            
            # ページネーション確認
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            next_page = soup.select_one('a.pagination_next:not(.disabled)')
            if not next_page and page != 1:
                break
                
            # 商品情報取得
            for item in soup.select('div.product_body'):
                # 基本情報
                name_elem = item.select_one('div.product_name')
                name = name_elem.text.strip()[:50] + "..." if name_elem else "商品名不明"
                name = re.sub(r'★|即発送|SALE\!|即納|新品', '', name).strip()

                # 価格
                price_elem = item.select_one('span.Price_Txt') or \
                            item.select_one('div.product_price span') or \
                            item.select_one('.price')
                price = re.sub(r'[^\d,]', '', price_elem.text.strip()).replace(',', '') if price_elem else "0"

                # 画像URL
                image_elem = item.select_one('img[loading="lazy"]')
                image_url = ""
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = urljoin(url, image_url)

                # 詳細情報（確率制限）
                details = {}
                if random.random() < 0.3:
                    detail_link = item.select_one('a.product_name')['href']
                    details = get_product_details(driver, urljoin(url, detail_link)) if detail_link else {}
                
                products.append({
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    **details
                })

        except Exception as e:
            print(f"ページ{page}処理中にエラー: {str(e)}")
            continue

    # CSV保存
    if products:
        with open(csv_path, 'w', newline='', encoding='cp932', errors='replace') as f:
            writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'image_url', 'description', 'seller_info'])
            writer.writeheader()
            writer.writerows(products)
        print(f"{brand} - {len(products)}件の商品を保存しました")
    else:
        print(f"{brand} - 商品データが0件のため保存をスキップしました")

# ====================
# メイン実行
# ====================
def main():
    driver = setup_driver()
    try:
        for brand in BRANDS:
            start_time = time.time()
            scrape_brand(driver, brand)
            elapsed_time = time.time() - start_time
            sleep_time = max(random.randint(*DELAY_RANGE) - elapsed_time, 5)
            time.sleep(sleep_time)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

# === NexusCore/exported_projects\project_export_m73owrzi\tools\research_tool.py ===
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import random
import os
import re
from urllib.parse import urljoin

# ====================
# 設定部分（必要に応じて変更）
# ====================
BASE_URL = "https://www.buyma.com/r/_%s/"  # ブランド名を%sに挿入
BRANDS = ["GUCCI", "PRADA"]                # 対象ブランドリスト
MAX_PAGES = 2                              # 最大取得ページ数
DELAY_RANGE = (10, 30)                     # ランダム待機時間（秒）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)..."
]
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
]

# ====================
# Chrome設定
# ====================
def setup_driver():
    chrome_options = Options()
    
    # Headlessモード
    chrome_options.add_argument("--headless=new")
    
    # プロキシ設定
    chrome_options.add_argument(f"--proxy-server={random.choice(PROXIES)}")
    
    # ユーザーエージェントローテーション
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # 基本設定
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=chrome_options)

# ====================
# 商品詳細取得関数
# ====================
def get_product_details(driver, product_url):
    """商品詳細ページから追加情報を取得"""
    try:
        driver.get(product_url)
        time.sleep(random.uniform(*DELAY_RANGE))
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_detail"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 追加情報取得例
        description = soup.select_one('div.product_description').text.strip()[:200] + "..." if soup.select_one('div.product_description') else ""
        seller_info = soup.select_one('div.seller_profile').text.strip()[:100] + "..." if soup.select_one('div.seller_profile') else ""
        
        return {
            'description': description,
            'seller_info': seller_info
        }
        
    except Exception as e:
        print(f"詳細ページエラー: {str(e)}")
        return {}

# ====================
# メインスクレイピング関数
# ====================
def scrape_brand(driver, brand):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', f'buyma_{brand.lower()}_products.csv')
    products = []
    
    for page in range(1, MAX_PAGES + 1):
        try:
            # ページアクセス
            url = BASE_URL % brand + f"?pageno={page}"
            driver.get(url)
            time.sleep(random.uniform(*DELAY_RANGE))
            
            # 商品コンテナ待機
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_body"))
            )
            
            # ページネーション確認
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            next_page = soup.select_one('a.pagination_next:not(.disabled)')
            if not next_page and page != 1:
                break
                
            # 商品情報取得
            for item in soup.select('div.product_body'):
                # 基本情報
                name_elem = item.select_one('div.product_name')
                name = name_elem.text.strip()[:50] + "..." if name_elem else "商品名不明"
                name = re.sub(r'★|即発送|SALE\!|即納|新品', '', name).strip()

                # 価格
                price_elem = item.select_one('span.Price_Txt') or \
                            item.select_one('div.product_price span') or \
                            item.select_one('.price')
                price = re.sub(r'[^\d,]', '', price_elem.text.strip()).replace(',', '') if price_elem else "0"

                # 画像URL
                image_elem = item.select_one('img[loading="lazy"]')
                image_url = ""
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = urljoin(url, image_url)

                # 詳細情報（確率制限）
                details = {}
                if random.random() < 0.3:
                    detail_link = item.select_one('a.product_name')['href']
                    details = get_product_details(driver, urljoin(url, detail_link)) if detail_link else {}
                
                products.append({
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    **details
                })

        except Exception as e:
            print(f"ページ{page}処理中にエラー: {str(e)}")
            continue

    # CSV保存
    if products:
        with open(csv_path, 'w', newline='', encoding='cp932', errors='replace') as f:
            writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'image_url', 'description', 'seller_info'])
            writer.writeheader()
            writer.writerows(products)
        print(f"{brand} - {len(products)}件の商品を保存しました")
    else:
        print(f"{brand} - 商品データが0件のため保存をスキップしました")

# ====================
# メイン実行
# ====================
def main():
    driver = setup_driver()
    try:
        for brand in BRANDS:
            start_time = time.time()
            scrape_brand(driver, brand)
            elapsed_time = time.time() - start_time
            sleep_time = max(random.randint(*DELAY_RANGE) - elapsed_time, 5)
            time.sleep(sleep_time)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

# === NexusCore/exported_projects\project_export_xb_l70t8\tools\research_tool.py ===
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import random
import os
import re
from urllib.parse import urljoin

# ====================
# 設定部分（必要に応じて変更）
# ====================
BASE_URL = "https://www.buyma.com/r/_%s/"  # ブランド名を%sに挿入
BRANDS = ["GUCCI", "PRADA"]                # 対象ブランドリスト
MAX_PAGES = 2                              # 最大取得ページ数
DELAY_RANGE = (10, 30)                     # ランダム待機時間（秒）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)..."
]
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
]

# ====================
# Chrome設定
# ====================
def setup_driver():
    chrome_options = Options()
    
    # Headlessモード
    chrome_options.add_argument("--headless=new")
    
    # プロキシ設定
    chrome_options.add_argument(f"--proxy-server={random.choice(PROXIES)}")
    
    # ユーザーエージェントローテーション
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # 基本設定
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=chrome_options)

# ====================
# 商品詳細取得関数
# ====================
def get_product_details(driver, product_url):
    """商品詳細ページから追加情報を取得"""
    try:
        driver.get(product_url)
        time.sleep(random.uniform(*DELAY_RANGE))
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_detail"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 追加情報取得例
        description = soup.select_one('div.product_description').text.strip()[:200] + "..." if soup.select_one('div.product_description') else ""
        seller_info = soup.select_one('div.seller_profile').text.strip()[:100] + "..." if soup.select_one('div.seller_profile') else ""
        
        return {
            'description': description,
            'seller_info': seller_info
        }
        
    except Exception as e:
        print(f"詳細ページエラー: {str(e)}")
        return {}

# ====================
# メインスクレイピング関数
# ====================
def scrape_brand(driver, brand):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', f'buyma_{brand.lower()}_products.csv')
    products = []
    
    for page in range(1, MAX_PAGES + 1):
        try:
            # ページアクセス
            url = BASE_URL % brand + f"?pageno={page}"
            driver.get(url)
            time.sleep(random.uniform(*DELAY_RANGE))
            
            # 商品コンテナ待機
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_body"))
            )
            
            # ページネーション確認
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            next_page = soup.select_one('a.pagination_next:not(.disabled)')
            if not next_page and page != 1:
                break
                
            # 商品情報取得
            for item in soup.select('div.product_body'):
                # 基本情報
                name_elem = item.select_one('div.product_name')
                name = name_elem.text.strip()[:50] + "..." if name_elem else "商品名不明"
                name = re.sub(r'★|即発送|SALE\!|即納|新品', '', name).strip()

                # 価格
                price_elem = item.select_one('span.Price_Txt') or \
                            item.select_one('div.product_price span') or \
                            item.select_one('.price')
                price = re.sub(r'[^\d,]', '', price_elem.text.strip()).replace(',', '') if price_elem else "0"

                # 画像URL
                image_elem = item.select_one('img[loading="lazy"]')
                image_url = ""
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = urljoin(url, image_url)

                # 詳細情報（確率制限）
                details = {}
                if random.random() < 0.3:
                    detail_link = item.select_one('a.product_name')['href']
                    details = get_product_details(driver, urljoin(url, detail_link)) if detail_link else {}
                
                products.append({
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    **details
                })

        except Exception as e:
            print(f"ページ{page}処理中にエラー: {str(e)}")
            continue

    # CSV保存
    if products:
        with open(csv_path, 'w', newline='', encoding='cp932', errors='replace') as f:
            writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'image_url', 'description', 'seller_info'])
            writer.writeheader()
            writer.writerows(products)
        print(f"{brand} - {len(products)}件の商品を保存しました")
    else:
        print(f"{brand} - 商品データが0件のため保存をスキップしました")

# ====================
# メイン実行
# ====================
def main():
    driver = setup_driver()
    try:
        for brand in BRANDS:
            start_time = time.time()
            scrape_brand(driver, brand)
            elapsed_time = time.time() - start_time
            sleep_time = max(random.randint(*DELAY_RANGE) - elapsed_time, 5)
            time.sleep(sleep_time)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

# === NexusCore/exported_projects\project_export_y7xxp1v8\tools\research_tool.py ===
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import random
import os
import re
from urllib.parse import urljoin

# ====================
# 設定部分（必要に応じて変更）
# ====================
BASE_URL = "https://www.buyma.com/r/_%s/"  # ブランド名を%sに挿入
BRANDS = ["GUCCI", "PRADA"]                # 対象ブランドリスト
MAX_PAGES = 2                              # 最大取得ページ数
DELAY_RANGE = (10, 30)                     # ランダム待機時間（秒）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)..."
]
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
]

# ====================
# Chrome設定
# ====================
def setup_driver():
    chrome_options = Options()
    
    # Headlessモード
    chrome_options.add_argument("--headless=new")
    
    # プロキシ設定
    chrome_options.add_argument(f"--proxy-server={random.choice(PROXIES)}")
    
    # ユーザーエージェントローテーション
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # 基本設定
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=chrome_options)

# ====================
# 商品詳細取得関数
# ====================
def get_product_details(driver, product_url):
    """商品詳細ページから追加情報を取得"""
    try:
        driver.get(product_url)
        time.sleep(random.uniform(*DELAY_RANGE))
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_detail"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 追加情報取得例
        description = soup.select_one('div.product_description').text.strip()[:200] + "..." if soup.select_one('div.product_description') else ""
        seller_info = soup.select_one('div.seller_profile').text.strip()[:100] + "..." if soup.select_one('div.seller_profile') else ""
        
        return {
            'description': description,
            'seller_info': seller_info
        }
        
    except Exception as e:
        print(f"詳細ページエラー: {str(e)}")
        return {}

# ====================
# メインスクレイピング関数
# ====================
def scrape_brand(driver, brand):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', f'buyma_{brand.lower()}_products.csv')
    products = []
    
    for page in range(1, MAX_PAGES + 1):
        try:
            # ページアクセス
            url = BASE_URL % brand + f"?pageno={page}"
            driver.get(url)
            time.sleep(random.uniform(*DELAY_RANGE))
            
            # 商品コンテナ待機
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_body"))
            )
            
            # ページネーション確認
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            next_page = soup.select_one('a.pagination_next:not(.disabled)')
            if not next_page and page != 1:
                break
                
            # 商品情報取得
            for item in soup.select('div.product_body'):
                # 基本情報
                name_elem = item.select_one('div.product_name')
                name = name_elem.text.strip()[:50] + "..." if name_elem else "商品名不明"
                name = re.sub(r'★|即発送|SALE\!|即納|新品', '', name).strip()

                # 価格
                price_elem = item.select_one('span.Price_Txt') or \
                            item.select_one('div.product_price span') or \
                            item.select_one('.price')
                price = re.sub(r'[^\d,]', '', price_elem.text.strip()).replace(',', '') if price_elem else "0"

                # 画像URL
                image_elem = item.select_one('img[loading="lazy"]')
                image_url = ""
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = urljoin(url, image_url)

                # 詳細情報（確率制限）
                details = {}
                if random.random() < 0.3:
                    detail_link = item.select_one('a.product_name')['href']
                    details = get_product_details(driver, urljoin(url, detail_link)) if detail_link else {}
                
                products.append({
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    **details
                })

        except Exception as e:
            print(f"ページ{page}処理中にエラー: {str(e)}")
            continue

    # CSV保存
    if products:
        with open(csv_path, 'w', newline='', encoding='cp932', errors='replace') as f:
            writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'image_url', 'description', 'seller_info'])
            writer.writeheader()
            writer.writerows(products)
        print(f"{brand} - {len(products)}件の商品を保存しました")
    else:
        print(f"{brand} - 商品データが0件のため保存をスキップしました")

# ====================
# メイン実行
# ====================
def main():
    driver = setup_driver()
    try:
        for brand in BRANDS:
            start_time = time.time()
            scrape_brand(driver, brand)
            elapsed_time = time.time() - start_time
            sleep_time = max(random.randint(*DELAY_RANGE) - elapsed_time, 5)
            time.sleep(sleep_time)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\autocompletion.py ===
"""Logic that powers autocompletion installed by ``pip completion``.
"""

import optparse
import os
import sys
from itertools import chain
from typing import Any, Iterable, List, Optional

from pip._internal.cli.main_parser import create_main_parser
from pip._internal.commands import commands_dict, create_command
from pip._internal.metadata import get_default_environment


def autocomplete() -> None:
    """Entry Point for completion of main and subcommand options."""
    # Don't complete if user hasn't sourced bash_completion file.
    if "PIP_AUTO_COMPLETE" not in os.environ:
        return
    # Don't complete if autocompletion environment variables
    # are not present
    if not os.environ.get("COMP_WORDS") or not os.environ.get("COMP_CWORD"):
        return
    cwords = os.environ["COMP_WORDS"].split()[1:]
    cword = int(os.environ["COMP_CWORD"])
    try:
        current = cwords[cword - 1]
    except IndexError:
        current = ""

    parser = create_main_parser()
    subcommands = list(commands_dict)
    options = []

    # subcommand
    subcommand_name: Optional[str] = None
    for word in cwords:
        if word in subcommands:
            subcommand_name = word
            break
    # subcommand options
    if subcommand_name is not None:
        # special case: 'help' subcommand has no options
        if subcommand_name == "help":
            sys.exit(1)
        # special case: list locally installed dists for show and uninstall
        should_list_installed = not current.startswith("-") and subcommand_name in [
            "show",
            "uninstall",
        ]
        if should_list_installed:
            env = get_default_environment()
            lc = current.lower()
            installed = [
                dist.canonical_name
                for dist in env.iter_installed_distributions(local_only=True)
                if dist.canonical_name.startswith(lc)
                and dist.canonical_name not in cwords[1:]
            ]
            # if there are no dists installed, fall back to option completion
            if installed:
                for dist in installed:
                    print(dist)
                sys.exit(1)

        should_list_installables = (
            not current.startswith("-") and subcommand_name == "install"
        )
        if should_list_installables:
            for path in auto_complete_paths(current, "path"):
                print(path)
            sys.exit(1)

        subcommand = create_command(subcommand_name)

        for opt in subcommand.parser.option_list_all:
            if opt.help != optparse.SUPPRESS_HELP:
                options += [
                    (opt_str, opt.nargs) for opt_str in opt._long_opts + opt._short_opts
                ]

        # filter out previously specified options from available options
        prev_opts = [x.split("=")[0] for x in cwords[1 : cword - 1]]
        options = [(x, v) for (x, v) in options if x not in prev_opts]
        # filter options by current input
        options = [(k, v) for k, v in options if k.startswith(current)]
        # get completion type given cwords and available subcommand options
        completion_type = get_path_completion_type(
            cwords,
            cword,
            subcommand.parser.option_list_all,
        )
        # get completion files and directories if ``completion_type`` is
        # ``<file>``, ``<dir>`` or ``<path>``
        if completion_type:
            paths = auto_complete_paths(current, completion_type)
            options = [(path, 0) for path in paths]
        for option in options:
            opt_label = option[0]
            # append '=' to options which require args
            if option[1] and option[0][:2] == "--":
                opt_label += "="
            print(opt_label)
    else:
        # show main parser options only when necessary

        opts = [i.option_list for i in parser.option_groups]
        opts.append(parser.option_list)
        flattened_opts = chain.from_iterable(opts)
        if current.startswith("-"):
            for opt in flattened_opts:
                if opt.help != optparse.SUPPRESS_HELP:
                    subcommands += opt._long_opts + opt._short_opts
        else:
            # get completion type given cwords and all available options
            completion_type = get_path_completion_type(cwords, cword, flattened_opts)
            if completion_type:
                subcommands = list(auto_complete_paths(current, completion_type))

        print(" ".join([x for x in subcommands if x.startswith(current)]))
    sys.exit(1)


def get_path_completion_type(
    cwords: List[str], cword: int, opts: Iterable[Any]
) -> Optional[str]:
    """Get the type of path completion (``file``, ``dir``, ``path`` or None)

    :param cwords: same as the environmental variable ``COMP_WORDS``
    :param cword: same as the environmental variable ``COMP_CWORD``
    :param opts: The available options to check
    :return: path completion type (``file``, ``dir``, ``path`` or None)
    """
    if cword < 2 or not cwords[cword - 2].startswith("-"):
        return None
    for opt in opts:
        if opt.help == optparse.SUPPRESS_HELP:
            continue
        for o in str(opt).split("/"):
            if cwords[cword - 2].split("=")[0] == o:
                if not opt.metavar or any(
                    x in ("path", "file", "dir") for x in opt.metavar.split("/")
                ):
                    return opt.metavar
    return None


def auto_complete_paths(current: str, completion_type: str) -> Iterable[str]:
    """If ``completion_type`` is ``file`` or ``path``, list all regular files
    and directories starting with ``current``; otherwise only list directories
    starting with ``current``.

    :param current: The word to be completed
    :param completion_type: path completion type(``file``, ``path`` or ``dir``)
    :return: A generator of regular files and/or directories
    """
    directory, filename = os.path.split(current)
    current_path = os.path.abspath(directory)
    # Don't complete paths if they can't be accessed
    if not os.access(current_path, os.R_OK):
        return
    filename = os.path.normcase(filename)
    # list all files that start with ``filename``
    file_list = (
        x for x in os.listdir(current_path) if os.path.normcase(x).startswith(filename)
    )
    for f in file_list:
        opt = os.path.join(current_path, f)
        comp_file = os.path.normcase(os.path.join(directory, f))
        # complete regular files when there is not ``<dir>`` after option
        # complete directories when there is ``<file>``, ``<path>`` or
        # ``<dir>``after option
        if completion_type != "dir" and os.path.isfile(opt):
            yield comp_file
        elif os.path.isdir(opt):
            yield os.path.join(comp_file, "")

# === NexusCore/openenv\Lib\site-packages\markdown_it\utils.py ===
from __future__ import annotations

from collections.abc import MutableMapping as MutableMappingABC
from pathlib import Path
from typing import Any, Callable, Iterable, MutableMapping, TypedDict, cast

EnvType = MutableMapping[str, Any]  # note: could use TypeAlias in python 3.10
"""Type for the environment sandbox used in parsing and rendering,
which stores mutable variables for use by plugins and rules.
"""


class OptionsType(TypedDict):
    """Options for parsing."""

    maxNesting: int
    """Internal protection, recursion limit."""
    html: bool
    """Enable HTML tags in source."""
    linkify: bool
    """Enable autoconversion of URL-like texts to links."""
    typographer: bool
    """Enable smartquotes and replacements."""
    quotes: str
    """Quote characters."""
    xhtmlOut: bool
    """Use '/' to close single tags (<br />)."""
    breaks: bool
    """Convert newlines in paragraphs into <br>."""
    langPrefix: str
    """CSS language prefix for fenced blocks."""
    highlight: Callable[[str, str, str], str] | None
    """Highlighter function: (content, lang, attrs) -> str."""


class PresetType(TypedDict):
    """Preset configuration for markdown-it."""

    options: OptionsType
    """Options for parsing."""
    components: MutableMapping[str, MutableMapping[str, list[str]]]
    """Components for parsing and rendering."""


class OptionsDict(MutableMappingABC):  # type: ignore
    """A dictionary, with attribute access to core markdownit configuration options."""

    # Note: ideally we would probably just remove attribute access entirely,
    # but we keep it for backwards compatibility.

    def __init__(self, options: OptionsType) -> None:
        self._options = cast(OptionsType, dict(options))

    def __getitem__(self, key: str) -> Any:
        return self._options[key]  # type: ignore[literal-required]

    def __setitem__(self, key: str, value: Any) -> None:
        self._options[key] = value  # type: ignore[literal-required]

    def __delitem__(self, key: str) -> None:
        del self._options[key]  # type: ignore

    def __iter__(self) -> Iterable[str]:  # type: ignore
        return iter(self._options)

    def __len__(self) -> int:
        return len(self._options)

    def __repr__(self) -> str:
        return repr(self._options)

    def __str__(self) -> str:
        return str(self._options)

    @property
    def maxNesting(self) -> int:
        """Internal protection, recursion limit."""
        return self._options["maxNesting"]

    @maxNesting.setter
    def maxNesting(self, value: int) -> None:
        self._options["maxNesting"] = value

    @property
    def html(self) -> bool:
        """Enable HTML tags in source."""
        return self._options["html"]

    @html.setter
    def html(self, value: bool) -> None:
        self._options["html"] = value

    @property
    def linkify(self) -> bool:
        """Enable autoconversion of URL-like texts to links."""
        return self._options["linkify"]

    @linkify.setter
    def linkify(self, value: bool) -> None:
        self._options["linkify"] = value

    @property
    def typographer(self) -> bool:
        """Enable smartquotes and replacements."""
        return self._options["typographer"]

    @typographer.setter
    def typographer(self, value: bool) -> None:
        self._options["typographer"] = value

    @property
    def quotes(self) -> str:
        """Quote characters."""
        return self._options["quotes"]

    @quotes.setter
    def quotes(self, value: str) -> None:
        self._options["quotes"] = value

    @property
    def xhtmlOut(self) -> bool:
        """Use '/' to close single tags (<br />)."""
        return self._options["xhtmlOut"]

    @xhtmlOut.setter
    def xhtmlOut(self, value: bool) -> None:
        self._options["xhtmlOut"] = value

    @property
    def breaks(self) -> bool:
        """Convert newlines in paragraphs into <br>."""
        return self._options["breaks"]

    @breaks.setter
    def breaks(self, value: bool) -> None:
        self._options["breaks"] = value

    @property
    def langPrefix(self) -> str:
        """CSS language prefix for fenced blocks."""
        return self._options["langPrefix"]

    @langPrefix.setter
    def langPrefix(self, value: str) -> None:
        self._options["langPrefix"] = value

    @property
    def highlight(self) -> Callable[[str, str, str], str] | None:
        """Highlighter function: (content, langName, langAttrs) -> escaped HTML."""
        return self._options["highlight"]

    @highlight.setter
    def highlight(self, value: Callable[[str, str, str], str] | None) -> None:
        self._options["highlight"] = value


def read_fixture_file(path: str | Path) -> list[list[Any]]:
    text = Path(path).read_text(encoding="utf-8")
    tests = []
    section = 0
    last_pos = 0
    lines = text.splitlines(keepends=True)
    for i in range(len(lines)):
        if lines[i].rstrip() == ".":
            if section == 0:
                tests.append([i, lines[i - 1].strip()])
                section = 1
            elif section == 1:
                tests[-1].append("".join(lines[last_pos + 1 : i]))
                section = 2
            elif section == 2:
                tests[-1].append("".join(lines[last_pos + 1 : i]))
                section = 0

            last_pos = i
    return tests

# === NexusCore/openenv\Lib\site-packages\git\refs\reference.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["Reference"]

from git.util import IterableObj, LazyMixin

from .symbolic import SymbolicReference, T_References

# typing ------------------------------------------------------------------

from typing import Any, Callable, Iterator, TYPE_CHECKING, Type, Union

from git.types import AnyGitObject, PathLike, _T

if TYPE_CHECKING:
    from git.repo import Repo

# ------------------------------------------------------------------------------

# { Utilities


def require_remote_ref_path(func: Callable[..., _T]) -> Callable[..., _T]:
    """A decorator raising :exc:`ValueError` if we are not a valid remote, based on the
    path."""

    def wrapper(self: T_References, *args: Any) -> _T:
        if not self.is_remote():
            raise ValueError("ref path does not point to a remote reference: %s" % self.path)
        return func(self, *args)

    # END wrapper
    wrapper.__name__ = func.__name__
    return wrapper


# } END utilities


class Reference(SymbolicReference, LazyMixin, IterableObj):
    """A named reference to any object.

    Subclasses may apply restrictions though, e.g., a :class:`~git.refs.head.Head` can
    only point to commits.
    """

    __slots__ = ()

    _points_to_commits_only = False
    _resolve_ref_on_create = True
    _common_path_default = "refs"

    def __init__(self, repo: "Repo", path: PathLike, check_path: bool = True) -> None:
        """Initialize this instance.

        :param repo:
            Our parent repository.

        :param path:
            Path relative to the ``.git/`` directory pointing to the ref in question,
            e.g. ``refs/heads/master``.

        :param check_path:
            If ``False``, you can provide any path.
            Otherwise the path must start with the default path prefix of this type.
        """
        if check_path and not str(path).startswith(self._common_path_default + "/"):
            raise ValueError(f"Cannot instantiate {self.__class__.__name__!r} from path {path}")
        self.path: str  # SymbolicReference converts to string at the moment.
        super().__init__(repo, path)

    def __str__(self) -> str:
        return self.name

    # { Interface

    # @ReservedAssignment
    def set_object(
        self,
        object: Union[AnyGitObject, "SymbolicReference", str],
        logmsg: Union[str, None] = None,
    ) -> "Reference":
        """Special version which checks if the head-log needs an update as well.

        :return:
            self
        """
        oldbinsha = None
        if logmsg is not None:
            head = self.repo.head
            if not head.is_detached and head.ref == self:
                oldbinsha = self.commit.binsha
            # END handle commit retrieval
        # END handle message is set

        super().set_object(object, logmsg)

        if oldbinsha is not None:
            # From refs/files-backend.c in git-source:
            # /*
            #  * Special hack: If a branch is updated directly and HEAD
            #  * points to it (may happen on the remote side of a push
            #  * for example) then logically the HEAD reflog should be
            #  * updated too.
            #  * A generic solution implies reverse symref information,
            #  * but finding all symrefs pointing to the given branch
            #  * would be rather costly for this rare event (the direct
            #  * update of a branch) to be worth it.  So let's cheat and
            #  * check with HEAD only which should cover 99% of all usage
            #  * scenarios (even 100% of the default ones).
            #  */
            self.repo.head.log_append(oldbinsha, logmsg)
        # END check if the head

        return self

    # NOTE: No need to overwrite properties, as the will only work without a the log.

    @property
    def name(self) -> str:
        """
        :return:
            (shortest) Name of this reference - it may contain path components
        """
        # The first two path tokens can be removed as they are
        # refs/heads or refs/tags or refs/remotes.
        tokens = self.path.split("/")
        if len(tokens) < 3:
            return self.path  # could be refs/HEAD
        return "/".join(tokens[2:])

    @classmethod
    def iter_items(
        cls: Type[T_References],
        repo: "Repo",
        common_path: Union[PathLike, None] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator[T_References]:
        """Equivalent to
        :meth:`SymbolicReference.iter_items <git.refs.symbolic.SymbolicReference.iter_items>`,
        but will return non-detached references as well."""
        return cls._iter_items(repo, common_path)

    # } END interface

    # { Remote Interface

    @property
    @require_remote_ref_path
    def remote_name(self) -> str:
        """
        :return:
            Name of the remote we are a reference of, such as ``origin`` for a reference
            named ``origin/master``.
        """
        tokens = self.path.split("/")
        # /refs/remotes/<remote name>/<branch_name>
        return tokens[2]

    @property
    @require_remote_ref_path
    def remote_head(self) -> str:
        """
        :return:
            Name of the remote head itself, e.g. ``master``.

        :note:
            The returned name is usually not qualified enough to uniquely identify a
            branch.
        """
        tokens = self.path.split("/")
        return "/".join(tokens[3:])

    # } END remote interface

# === NexusCore/openenv\Lib\site-packages\google\oauth2\sts.py ===
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OAuth 2.0 Token Exchange Spec.

This module defines a token exchange utility based on the `OAuth 2.0 Token
Exchange`_ spec. This will be mainly used to exchange external credentials
for GCP access tokens in workload identity pools to access Google APIs.

The implementation will support various types of client authentication as
allowed in the spec.

A deviation on the spec will be for additional Google specific options that
cannot be easily mapped to parameters defined in the RFC.

The returned dictionary response will be based on the `rfc8693 section 2.2.1`_
spec JSON response.

.. _OAuth 2.0 Token Exchange: https://tools.ietf.org/html/rfc8693
.. _rfc8693 section 2.2.1: https://tools.ietf.org/html/rfc8693#section-2.2.1
"""

import http.client as http_client
import json
import urllib

from google.oauth2 import utils


_URLENCODED_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


class Client(utils.OAuthClientAuthHandler):
    """Implements the OAuth 2.0 token exchange spec based on
    https://tools.ietf.org/html/rfc8693.
    """

    def __init__(self, token_exchange_endpoint, client_authentication=None):
        """Initializes an STS client instance.

        Args:
            token_exchange_endpoint (str): The token exchange endpoint.
            client_authentication (Optional(google.oauth2.oauth2_utils.ClientAuthentication)):
                The optional OAuth client authentication credentials if available.
        """
        super(Client, self).__init__(client_authentication)
        self._token_exchange_endpoint = token_exchange_endpoint

    def _make_request(self, request, headers, request_body):
        # Initialize request headers.
        request_headers = _URLENCODED_HEADERS.copy()

        # Inject additional headers.
        if headers:
            for k, v in dict(headers).items():
                request_headers[k] = v

        # Apply OAuth client authentication.
        self.apply_client_authentication_options(request_headers, request_body)

        # Execute request.
        response = request(
            url=self._token_exchange_endpoint,
            method="POST",
            headers=request_headers,
            body=urllib.parse.urlencode(request_body).encode("utf-8"),
        )

        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        # If non-200 response received, translate to OAuthError exception.
        if response.status != http_client.OK:
            utils.handle_error_response(response_body)

        response_data = json.loads(response_body)

        # Return successful response.
        return response_data

    def exchange_token(
        self,
        request,
        grant_type,
        subject_token,
        subject_token_type,
        resource=None,
        audience=None,
        scopes=None,
        requested_token_type=None,
        actor_token=None,
        actor_token_type=None,
        additional_options=None,
        additional_headers=None,
    ):
        """Exchanges the provided token for another type of token based on the
        rfc8693 spec.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
            grant_type (str): The OAuth 2.0 token exchange grant type.
            subject_token (str): The OAuth 2.0 token exchange subject token.
            subject_token_type (str): The OAuth 2.0 token exchange subject token type.
            resource (Optional[str]): The optional OAuth 2.0 token exchange resource field.
            audience (Optional[str]): The optional OAuth 2.0 token exchange audience field.
            scopes (Optional[Sequence[str]]): The optional list of scopes to use.
            requested_token_type (Optional[str]): The optional OAuth 2.0 token exchange requested
                token type.
            actor_token (Optional[str]): The optional OAuth 2.0 token exchange actor token.
            actor_token_type (Optional[str]): The optional OAuth 2.0 token exchange actor token type.
            additional_options (Optional[Mapping[str, str]]): The optional additional
                non-standard Google specific options.
            additional_headers (Optional[Mapping[str, str]]): The optional additional
                headers to pass to the token exchange endpoint.

        Returns:
            Mapping[str, str]: The token exchange JSON-decoded response data containing
                the requested token and its expiration time.

        Raises:
            google.auth.exceptions.OAuthError: If the token endpoint returned
                an error.
        """
        # Initialize request body.
        request_body = {
            "grant_type": grant_type,
            "resource": resource,
            "audience": audience,
            "scope": " ".join(scopes or []),
            "requested_token_type": requested_token_type,
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "actor_token": actor_token,
            "actor_token_type": actor_token_type,
            "options": None,
        }
        # Add additional non-standard options.
        if additional_options:
            request_body["options"] = urllib.parse.quote(json.dumps(additional_options))
        # Remove empty fields in request body.
        for k, v in dict(request_body).items():
            if v is None or v == "":
                del request_body[k]

        return self._make_request(request, additional_headers, request_body)

    def refresh_token(self, request, refresh_token):
        """Exchanges a refresh token for an access token based on the
        RFC6749 spec.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
            subject_token (str): The OAuth 2.0 refresh token.
        """

        return self._make_request(
            request,
            None,
            {"grant_type": "refresh_token", "refresh_token": refresh_token},
        )

# === NexusCore/openenv\Lib\site-packages\litellm\secret_managers\base_secret_manager.py ===
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import httpx

from litellm import verbose_logger


class BaseSecretManager(ABC):
    """
    Abstract base class for secret management implementations.
    """

    @abstractmethod
    async def async_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Optional[str]:
        """
        Asynchronously read a secret from the secret manager.

        Args:
            secret_name (str): Name/path of the secret to read
            optional_params (Optional[dict]): Additional parameters specific to the secret manager
            timeout (Optional[Union[float, httpx.Timeout]]): Request timeout

        Returns:
            Optional[str]: The secret value if found, None otherwise
        """
        pass

    @abstractmethod
    def sync_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Optional[str]:
        """
        Synchronously read a secret from the secret manager.

        Args:
            secret_name (str): Name/path of the secret to read
            optional_params (Optional[dict]): Additional parameters specific to the secret manager
            timeout (Optional[Union[float, httpx.Timeout]]): Request timeout

        Returns:
            Optional[str]: The secret value if found, None otherwise
        """
        pass

    @abstractmethod
    async def async_write_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronously write a secret to the secret manager.

        Args:
            secret_name (str): Name/path of the secret to write
            secret_value (str): Value to store
            description (Optional[str]): Description of the secret. Some secret managers allow storing a description with the secret.
            optional_params (Optional[dict]): Additional parameters specific to the secret manager
            timeout (Optional[Union[float, httpx.Timeout]]): Request timeout
        Returns:
            Dict[str, Any]: Response from the secret manager containing write operation details
        """
        pass

    @abstractmethod
    async def async_delete_secret(
        self,
        secret_name: str,
        recovery_window_in_days: Optional[int] = 7,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> dict:
        """
        Async function to delete a secret from the secret manager

        Args:
            secret_name: Name of the secret to delete
            recovery_window_in_days: Number of days before permanent deletion (default: 7)
            optional_params: Additional parameters specific to the secret manager
            timeout: Request timeout

        Returns:
            dict: Response from the secret manager containing deletion details
        """
        pass

    async def async_rotate_secret(
        self,
        current_secret_name: str,
        new_secret_name: str,
        new_secret_value: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> dict:
        """
        Async function to rotate a secret by creating a new one and deleting the old one.
        This allows for both value and name changes during rotation.

        Args:
            current_secret_name: Current name of the secret
            new_secret_name: New name for the secret
            new_secret_value: New value for the secret
            optional_params: Additional AWS parameters
            timeout: Request timeout

        Returns:
            dict: Response containing the new secret details

        Raises:
            ValueError: If the secret doesn't exist or if there's an HTTP error
        """
        try:
            # First verify the old secret exists
            old_secret = await self.async_read_secret(
                secret_name=current_secret_name,
                optional_params=optional_params,
                timeout=timeout,
            )

            if old_secret is None:
                raise ValueError(f"Current secret {current_secret_name} not found")

            # Create new secret with new name and value
            create_response = await self.async_write_secret(
                secret_name=new_secret_name,
                secret_value=new_secret_value,
                description=f"Rotated from {current_secret_name}",
                optional_params=optional_params,
                timeout=timeout,
            )

            # Verify new secret was created successfully
            new_secret = await self.async_read_secret(
                secret_name=new_secret_name,
                optional_params=optional_params,
                timeout=timeout,
            )

            if new_secret is None:
                raise ValueError(f"Failed to verify new secret {new_secret_name}")

            # If everything is successful, delete the old secret
            await self.async_delete_secret(
                secret_name=current_secret_name,
                recovery_window_in_days=7,  # Keep for recovery if needed
                optional_params=optional_params,
                timeout=timeout,
            )

            return create_response

        except httpx.HTTPStatusError as err:
            verbose_logger.exception(
                "Error rotating secret in AWS Secrets Manager: %s",
                str(err.response.text),
            )
            raise ValueError(f"HTTP error occurred: {err.response.text}")
        except httpx.TimeoutException:
            raise ValueError("Timeout error occurred")
        except Exception as e:
            verbose_logger.exception(
                "Error rotating secret in AWS Secrets Manager: %s", str(e)
            )
            raise

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\chat\o_series_transformation.py ===
"""
Support for o1/o3 model family 

https://platform.openai.com/docs/guides/reasoning

Translations handled by LiteLLM:
- modalities: image => drop param (if user opts in to dropping param)  
- role: system ==> translate to role 'user' 
- streaming => faked by LiteLLM 
- Tools, response_format =>  drop param (if user opts in to dropping param) 
- Logprobs => drop param (if user opts in to dropping param) 
"""

from typing import Any, Coroutine, List, Literal, Optional, Union, cast, overload

import litellm
from litellm import verbose_logger
from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider
from litellm.types.llms.openai import AllMessageValues, ChatCompletionUserMessage
from litellm.utils import (
    supports_function_calling,
    supports_parallel_function_calling,
    supports_response_schema,
    supports_system_messages,
)

from .gpt_transformation import OpenAIGPTConfig


class OpenAIOSeriesConfig(OpenAIGPTConfig):
    """
    Reference: https://platform.openai.com/docs/guides/reasoning
    """

    @classmethod
    def get_config(cls):
        return super().get_config()

    def translate_developer_role_to_system_role(
        self, messages: List[AllMessageValues]
    ) -> List[AllMessageValues]:
        """
        O-series models support `developer` role.
        """
        return messages

    def get_supported_openai_params(self, model: str) -> list:
        """
        Get the supported OpenAI params for the given model

        """

        all_openai_params = super().get_supported_openai_params(model=model)
        non_supported_params = [
            "logprobs",
            "top_p",
            "presence_penalty",
            "frequency_penalty",
            "top_logprobs",
        ]

        o_series_only_param = ["reasoning_effort"]

        all_openai_params.extend(o_series_only_param)

        try:
            model, custom_llm_provider, api_base, api_key = get_llm_provider(
                model=model
            )
        except Exception:
            verbose_logger.debug(
                f"Unable to infer model provider for model={model}, defaulting to openai for o1 supported param check"
            )
            custom_llm_provider = "openai"

        _supports_function_calling = supports_function_calling(
            model, custom_llm_provider
        )
        _supports_response_schema = supports_response_schema(model, custom_llm_provider)
        _supports_parallel_tool_calls = supports_parallel_function_calling(
            model, custom_llm_provider
        )

        if not _supports_function_calling:
            non_supported_params.append("tools")
            non_supported_params.append("tool_choice")
            non_supported_params.append("function_call")
            non_supported_params.append("functions")

        if not _supports_parallel_tool_calls:
            non_supported_params.append("parallel_tool_calls")

        if not _supports_response_schema:
            non_supported_params.append("response_format")

        return [
            param for param in all_openai_params if param not in non_supported_params
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ):
        if "max_tokens" in non_default_params:
            optional_params["max_completion_tokens"] = non_default_params.pop(
                "max_tokens"
            )
        if "temperature" in non_default_params:
            temperature_value: Optional[float] = non_default_params.pop("temperature")
            if temperature_value is not None:
                if temperature_value == 1:
                    optional_params["temperature"] = temperature_value
                else:
                    ## UNSUPPORTED TOOL CHOICE VALUE
                    if litellm.drop_params is True or drop_params is True:
                        pass
                    else:
                        raise litellm.utils.UnsupportedParamsError(
                            message="O-series models don't support temperature={}. Only temperature=1 is supported. To drop unsupported openai params from the call, set `litellm.drop_params = True`".format(
                                temperature_value
                            ),
                            status_code=400,
                        )

        return super()._map_openai_params(
            non_default_params, optional_params, model, drop_params
        )

    def is_model_o_series_model(self, model: str) -> bool:
        model = model.split("/")[-1]  # could be "openai/o3" or "o3"
        return model in litellm.open_ai_chat_completion_models and any(
            model.startswith(pfx) for pfx in ("o1", "o3", "o4")
        )

    @overload
    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: Literal[True]
    ) -> Coroutine[Any, Any, List[AllMessageValues]]:
        ...

    @overload
    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
        is_async: Literal[False] = False,
    ) -> List[AllMessageValues]:
        ...

    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: bool = False
    ) -> Union[List[AllMessageValues], Coroutine[Any, Any, List[AllMessageValues]]]:
        """
        Handles limitations of O-1 model family.
        - modalities: image => drop param (if user opts in to dropping param)
        - role: system ==> translate to role 'user'
        """
        _supports_system_messages = supports_system_messages(model, "openai")
        for i, message in enumerate(messages):
            if message["role"] == "system" and not _supports_system_messages:
                new_message = ChatCompletionUserMessage(
                    content=message["content"], role="user"
                )
                messages[i] = new_message  # Replace the old message with the new one

        if is_async:
            return super()._transform_messages(
                messages, model, is_async=cast(Literal[True], True)
            )
        else:
            return super()._transform_messages(
                messages, model, is_async=cast(Literal[False], False)
            )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_transaction_queue\pod_lock_manager.py ===
import asyncio
import uuid
from typing import TYPE_CHECKING, Any, Optional

from litellm._logging import verbose_proxy_logger
from litellm.caching.redis_cache import RedisCache
from litellm.constants import DEFAULT_CRON_JOB_LOCK_TTL_SECONDS
from litellm.proxy.db.db_transaction_queue.base_update_queue import service_logger_obj
from litellm.types.services import ServiceTypes

if TYPE_CHECKING:
    ProxyLogging = Any
else:
    ProxyLogging = Any


class PodLockManager:
    """
    Manager for acquiring and releasing locks for cron jobs using Redis.

    Ensures that only one pod can run a cron job at a time.
    """

    def __init__(self, redis_cache: Optional[RedisCache] = None):
        self.pod_id = str(uuid.uuid4())
        self.redis_cache = redis_cache

    @staticmethod
    def get_redis_lock_key(cronjob_id: str) -> str:
        return f"cronjob_lock:{cronjob_id}"

    async def acquire_lock(
        self,
        cronjob_id: str,
    ) -> Optional[bool]:
        """
        Attempt to acquire the lock for a specific cron job using Redis.
        Uses the SET command with NX and EX options to ensure atomicity.
        
        Args:
            cronjob_id: The ID of the cron job to lock
        """
        if self.redis_cache is None:
            verbose_proxy_logger.debug("redis_cache is None, skipping acquire_lock")
            return None
        try:
            verbose_proxy_logger.debug(
                "Pod %s attempting to acquire Redis lock for cronjob_id=%s",
                self.pod_id,
                cronjob_id,
            )
            # Try to set the lock key with the pod_id as its value, only if it doesn't exist (NX)
            # and with an expiration (EX) to avoid deadlocks.
            lock_key = PodLockManager.get_redis_lock_key(cronjob_id)
            acquired = await self.redis_cache.async_set_cache(
                lock_key,
                self.pod_id,
                nx=True,
                ttl=DEFAULT_CRON_JOB_LOCK_TTL_SECONDS,
            )
            if acquired:
                verbose_proxy_logger.info(
                    "Pod %s successfully acquired Redis lock for cronjob_id=%s",
                    self.pod_id,
                    cronjob_id,
                )

                return True
            else:
                # Check if the current pod already holds the lock
                current_value = await self.redis_cache.async_get_cache(lock_key)
                if current_value is not None:
                    if isinstance(current_value, bytes):
                        current_value = current_value.decode("utf-8")
                    if current_value == self.pod_id:
                        verbose_proxy_logger.info(
                            "Pod %s already holds the Redis lock for cronjob_id=%s",
                            self.pod_id,
                            cronjob_id,
                        )
                        self._emit_acquired_lock_event(cronjob_id, self.pod_id)
                        return True
            return False
        except Exception as e:
            verbose_proxy_logger.error(
                f"Error acquiring Redis lock for {cronjob_id}: {e}"
            )
            return False

    async def release_lock(
        self,
        cronjob_id: str,
    ):
        """
        Release the lock if the current pod holds it.
        Uses get and delete commands to ensure that only the owner can release the lock.
        """
        if self.redis_cache is None:
            verbose_proxy_logger.debug("redis_cache is None, skipping release_lock")
            return
        try:
            cronjob_id = cronjob_id
            verbose_proxy_logger.debug(
                "Pod %s attempting to release Redis lock for cronjob_id=%s",
                self.pod_id,
                cronjob_id,
            )
            lock_key = PodLockManager.get_redis_lock_key(cronjob_id)

            current_value = await self.redis_cache.async_get_cache(lock_key)
            if current_value is not None:
                if isinstance(current_value, bytes):
                    current_value = current_value.decode("utf-8")
                if current_value == self.pod_id:
                    result = await self.redis_cache.async_delete_cache(lock_key)
                    if result == 1:
                        verbose_proxy_logger.info(
                            "Pod %s successfully released Redis lock for cronjob_id=%s",
                            self.pod_id,
                            cronjob_id,
                        )
                        self._emit_released_lock_event(
                            cronjob_id=cronjob_id,
                            pod_id=self.pod_id,
                        )
                    else:
                        verbose_proxy_logger.debug(
                            "Pod %s failed to release Redis lock for cronjob_id=%s",
                            self.pod_id,
                            cronjob_id,
                        )
                else:
                    verbose_proxy_logger.debug(
                        "Pod %s cannot release Redis lock for cronjob_id=%s because it is held by pod %s",
                        self.pod_id,
                        cronjob_id,
                        current_value,
                    )
            else:
                verbose_proxy_logger.debug(
                    "Pod %s attempted to release Redis lock for cronjob_id=%s, but no lock was found",
                    self.pod_id,
                    cronjob_id,
                )
        except Exception as e:
            verbose_proxy_logger.error(
                f"Error releasing Redis lock for {cronjob_id}: {e}"
            )

    @staticmethod
    def _emit_acquired_lock_event(cronjob_id: str, pod_id: str):
        asyncio.create_task(
            service_logger_obj.async_service_success_hook(
                service=ServiceTypes.POD_LOCK_MANAGER,
                duration=DEFAULT_CRON_JOB_LOCK_TTL_SECONDS,
                call_type="_emit_acquired_lock_event",
                event_metadata={
                    "gauge_labels": f"{cronjob_id}:{pod_id}",
                    "gauge_value": 1,
                },
            )
        )

    @staticmethod
    def _emit_released_lock_event(cronjob_id: str, pod_id: str):
        asyncio.create_task(
            service_logger_obj.async_service_success_hook(
                service=ServiceTypes.POD_LOCK_MANAGER,
                duration=DEFAULT_CRON_JOB_LOCK_TTL_SECONDS,
                call_type="_emit_released_lock_event",
                event_metadata={
                    "gauge_labels": f"{cronjob_id}:{pod_id}",
                    "gauge_value": 0,
                },
            )
        )

# === NexusCore/openenv\Lib\site-packages\nltk\misc\sort.py ===
# Natural Language Toolkit: List Sorting
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides a variety of list sorting algorithms, to
illustrate the many different algorithms (recipes) for solving a
problem, and how to analyze algorithms experimentally.
"""
# These algorithms are taken from:
# Levitin (2004) The Design and Analysis of Algorithms

##################################################################
# Selection Sort
##################################################################


def selection(a):
    """
    Selection Sort: scan the list to find its smallest element, then
    swap it with the first element.  The remainder of the list is one
    element smaller; apply the same method to this list, and so on.
    """
    count = 0

    for i in range(len(a) - 1):
        min = i

        for j in range(i + 1, len(a)):
            if a[j] < a[min]:
                min = j

            count += 1

        a[min], a[i] = a[i], a[min]

    return count


##################################################################
# Bubble Sort
##################################################################


def bubble(a):
    """
    Bubble Sort: compare adjacent elements of the list left-to-right,
    and swap them if they are out of order.  After one pass through
    the list swapping adjacent items, the largest item will be in
    the rightmost position.  The remainder is one element smaller;
    apply the same method to this list, and so on.
    """
    count = 0
    for i in range(len(a) - 1):
        for j in range(len(a) - i - 1):
            if a[j + 1] < a[j]:
                a[j], a[j + 1] = a[j + 1], a[j]
                count += 1
    return count


##################################################################
# Merge Sort
##################################################################


def _merge_lists(b, c):
    count = 0
    i = j = 0
    a = []
    while i < len(b) and j < len(c):
        count += 1
        if b[i] <= c[j]:
            a.append(b[i])
            i += 1
        else:
            a.append(c[j])
            j += 1
    if i == len(b):
        a += c[j:]
    else:
        a += b[i:]
    return a, count


def merge(a):
    """
    Merge Sort: split the list in half, and sort each half, then
    combine the sorted halves.
    """
    count = 0
    if len(a) > 1:
        midpoint = len(a) // 2
        b = a[:midpoint]
        c = a[midpoint:]
        count_b = merge(b)
        count_c = merge(c)
        result, count_a = _merge_lists(b, c)
        a[:] = result  # copy the result back into a.
        count = count_a + count_b + count_c
    return count


##################################################################
# Quick Sort
##################################################################


def _partition(a, l, r):
    p = a[l]
    i = l
    j = r + 1
    count = 0
    while True:
        while i < r:
            i += 1
            if a[i] >= p:
                break
        while j > l:
            j -= 1
            if j < l or a[j] <= p:
                break
        a[i], a[j] = a[j], a[i]  # swap
        count += 1
        if i >= j:
            break
    a[i], a[j] = a[j], a[i]  # undo last swap
    a[l], a[j] = a[j], a[l]
    return j, count


def _quick(a, l, r):
    count = 0
    if l < r:
        s, count = _partition(a, l, r)
        count += _quick(a, l, s - 1)
        count += _quick(a, s + 1, r)
    return count


def quick(a):
    return _quick(a, 0, len(a) - 1)


##################################################################
# Demonstration
##################################################################


def demo():
    from random import shuffle

    for size in (10, 20, 50, 100, 200, 500, 1000):
        a = list(range(size))

        # various sort methods
        shuffle(a)
        count_selection = selection(a)
        shuffle(a)
        count_bubble = bubble(a)
        shuffle(a)
        count_merge = merge(a)
        shuffle(a)
        count_quick = quick(a)

        print(
            ("size=%5d:  selection=%8d,  bubble=%8d,  " "merge=%6d,  quick=%6d")
            % (size, count_selection, count_bubble, count_merge, count_quick)
        )


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\autocompletion.py ===
"""Logic that powers autocompletion installed by ``pip completion``.
"""

import optparse
import os
import sys
from itertools import chain
from typing import Any, Iterable, List, Optional

from pip._internal.cli.main_parser import create_main_parser
from pip._internal.commands import commands_dict, create_command
from pip._internal.metadata import get_default_environment


def autocomplete() -> None:
    """Entry Point for completion of main and subcommand options."""
    # Don't complete if user hasn't sourced bash_completion file.
    if "PIP_AUTO_COMPLETE" not in os.environ:
        return
    # Don't complete if autocompletion environment variables
    # are not present
    if not os.environ.get("COMP_WORDS") or not os.environ.get("COMP_CWORD"):
        return
    cwords = os.environ["COMP_WORDS"].split()[1:]
    cword = int(os.environ["COMP_CWORD"])
    try:
        current = cwords[cword - 1]
    except IndexError:
        current = ""

    parser = create_main_parser()
    subcommands = list(commands_dict)
    options = []

    # subcommand
    subcommand_name: Optional[str] = None
    for word in cwords:
        if word in subcommands:
            subcommand_name = word
            break
    # subcommand options
    if subcommand_name is not None:
        # special case: 'help' subcommand has no options
        if subcommand_name == "help":
            sys.exit(1)
        # special case: list locally installed dists for show and uninstall
        should_list_installed = not current.startswith("-") and subcommand_name in [
            "show",
            "uninstall",
        ]
        if should_list_installed:
            env = get_default_environment()
            lc = current.lower()
            installed = [
                dist.canonical_name
                for dist in env.iter_installed_distributions(local_only=True)
                if dist.canonical_name.startswith(lc)
                and dist.canonical_name not in cwords[1:]
            ]
            # if there are no dists installed, fall back to option completion
            if installed:
                for dist in installed:
                    print(dist)
                sys.exit(1)

        should_list_installables = (
            not current.startswith("-") and subcommand_name == "install"
        )
        if should_list_installables:
            for path in auto_complete_paths(current, "path"):
                print(path)
            sys.exit(1)

        subcommand = create_command(subcommand_name)

        for opt in subcommand.parser.option_list_all:
            if opt.help != optparse.SUPPRESS_HELP:
                options += [
                    (opt_str, opt.nargs) for opt_str in opt._long_opts + opt._short_opts
                ]

        # filter out previously specified options from available options
        prev_opts = [x.split("=")[0] for x in cwords[1 : cword - 1]]
        options = [(x, v) for (x, v) in options if x not in prev_opts]
        # filter options by current input
        options = [(k, v) for k, v in options if k.startswith(current)]
        # get completion type given cwords and available subcommand options
        completion_type = get_path_completion_type(
            cwords,
            cword,
            subcommand.parser.option_list_all,
        )
        # get completion files and directories if ``completion_type`` is
        # ``<file>``, ``<dir>`` or ``<path>``
        if completion_type:
            paths = auto_complete_paths(current, completion_type)
            options = [(path, 0) for path in paths]
        for option in options:
            opt_label = option[0]
            # append '=' to options which require args
            if option[1] and option[0][:2] == "--":
                opt_label += "="
            print(opt_label)
    else:
        # show main parser options only when necessary

        opts = [i.option_list for i in parser.option_groups]
        opts.append(parser.option_list)
        flattened_opts = chain.from_iterable(opts)
        if current.startswith("-"):
            for opt in flattened_opts:
                if opt.help != optparse.SUPPRESS_HELP:
                    subcommands += opt._long_opts + opt._short_opts
        else:
            # get completion type given cwords and all available options
            completion_type = get_path_completion_type(cwords, cword, flattened_opts)
            if completion_type:
                subcommands = list(auto_complete_paths(current, completion_type))

        print(" ".join([x for x in subcommands if x.startswith(current)]))
    sys.exit(1)


def get_path_completion_type(
    cwords: List[str], cword: int, opts: Iterable[Any]
) -> Optional[str]:
    """Get the type of path completion (``file``, ``dir``, ``path`` or None)

    :param cwords: same as the environmental variable ``COMP_WORDS``
    :param cword: same as the environmental variable ``COMP_CWORD``
    :param opts: The available options to check
    :return: path completion type (``file``, ``dir``, ``path`` or None)
    """
    if cword < 2 or not cwords[cword - 2].startswith("-"):
        return None
    for opt in opts:
        if opt.help == optparse.SUPPRESS_HELP:
            continue
        for o in str(opt).split("/"):
            if cwords[cword - 2].split("=")[0] == o:
                if not opt.metavar or any(
                    x in ("path", "file", "dir") for x in opt.metavar.split("/")
                ):
                    return opt.metavar
    return None


def auto_complete_paths(current: str, completion_type: str) -> Iterable[str]:
    """If ``completion_type`` is ``file`` or ``path``, list all regular files
    and directories starting with ``current``; otherwise only list directories
    starting with ``current``.

    :param current: The word to be completed
    :param completion_type: path completion type(``file``, ``path`` or ``dir``)
    :return: A generator of regular files and/or directories
    """
    directory, filename = os.path.split(current)
    current_path = os.path.abspath(directory)
    # Don't complete paths if they can't be accessed
    if not os.access(current_path, os.R_OK):
        return
    filename = os.path.normcase(filename)
    # list all files that start with ``filename``
    file_list = (
        x for x in os.listdir(current_path) if os.path.normcase(x).startswith(filename)
    )
    for f in file_list:
        opt = os.path.join(current_path, f)
        comp_file = os.path.normcase(os.path.join(directory, f))
        # complete regular files when there is not ``<dir>`` after option
        # complete directories when there is ``<file>``, ``<path>`` or
        # ``<dir>``after option
        if completion_type != "dir" and os.path.isfile(opt):
            yield comp_file
        elif os.path.isdir(opt):
            yield os.path.join(comp_file, "")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\graphql.py ===
"""
    pygments.lexers.graphql
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for GraphQL, an open-source data query and manipulation
    language for APIs.

    More information:
    https://graphql.org/

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, include, bygroups, default
from pygments.token import (Comment, Keyword, Name, Number, Punctuation, String,
                            Whitespace)


__all__ = ["GraphQLLexer"]

OPERATION_TYPES = ("query", "mutation", "subscription")
BUILTIN_TYPES = ("Int", "Float", "String", "Boolean", "ID")
BOOLEAN_VALUES = ("true", "false", "null")
KEYWORDS = (
    "type",
    "schema",
    "extend",
    "enum",
    "scalar",
    "implements",
    "interface",
    "union",
    "input",
    "directive",
    "QUERY",
    "MUTATION",
    "SUBSCRIPTION",
    "FIELD",
    "FRAGMENT_DEFINITION",
    "FRAGMENT_SPREAD",
    "INLINE_FRAGMENT",
    "SCHEMA",
    "SCALAR",
    "OBJECT",
    "FIELD_DEFINITION",
    "ARGUMENT_DEFINITION",
    "INTERFACE",
    "UNION",
    "ENUM",
    "ENUM_VALUE",
    "INPUT_OBJECT",
    "INPUT_FIELD_DEFINITION",
)


class GraphQLLexer(RegexLexer):
    """
    Lexer for GraphQL syntax
    """
    name = "GraphQL"
    aliases = ["graphql"]
    filenames = ["*.graphql"]
    url = "https://graphql.org"
    version_added = '2.16'

    tokens = {
        "ignored_tokens": [
            (r"\s+", Whitespace),  # Whitespaces
            (r"#.*$", Comment),
            (",", Punctuation),  # Insignificant commas
        ],
        "value": [
            include("ignored_tokens"),
            (r"-?\d+(?![.eE])", Number.Integer, "#pop"),
            (
                r"-?\d+(\.\d+)?([eE][+-]?\d+)?",
                Number.Float,
                "#pop",
            ),
            (r'"', String, ("#pop", "string")),
            (words(BOOLEAN_VALUES, suffix=r"\b"), Name.Builtin, "#pop"),
            (r"\$[a-zA-Z_]\w*", Name.Variable, "#pop"),
            (r"[a-zA-Z_]\w*", Name.Constant, "#pop"),
            (r"\[", Punctuation, ("#pop", "list_value")),
            (r"\{", Punctuation, ("#pop", "object_value")),
        ],
        "list_value": [
            include("ignored_tokens"),
            ("]", Punctuation, "#pop"),
            default("value"),
        ],
        "object_value": [
            include("ignored_tokens"),
            (r"[a-zA-Z_]\w*", Name),
            (r":", Punctuation, "value"),
            (r"\}", Punctuation, "#pop"),
        ],
        "string": [
            (r'\\(["\\/bfnrt]|u[a-fA-F0-9]{4})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'"', String, "#pop"),
        ],
        "root": [
            include("ignored_tokens"),
            (words(OPERATION_TYPES, suffix=r"\b"), Keyword, "operation"),
            (words(KEYWORDS, suffix=r"\b"), Keyword),
            (r"\{", Punctuation, "selection_set"),
            (r"fragment\b", Keyword, "fragment_definition"),
        ],
        "operation": [
            include("ignored_tokens"),
            (r"[a-zA-Z_]\w*", Name.Function),
            (r"\(", Punctuation, "variable_definition"),
            (r"\{", Punctuation, ("#pop", "selection_set")),
        ],
        "variable_definition": [
            include("ignored_tokens"),
            (r"\$[a-zA-Z_]\w*", Name.Variable),
            (r"[\]!]", Punctuation),
            (r":", Punctuation, "type"),
            (r"=", Punctuation, "value"),
            (r"\)", Punctuation, "#pop"),
        ],
        "type": [
            include("ignored_tokens"),
            (r"\[", Punctuation),
            (words(BUILTIN_TYPES, suffix=r"\b"), Name.Builtin, "#pop"),
            (r"[a-zA-Z_]\w*", Name.Class, "#pop"),
        ],
        "selection_set": [
            include("ignored_tokens"),
            (r"([a-zA-Z_]\w*)(\s*)(:)", bygroups(Name.Label, Whitespace, Punctuation)),
            (r"[a-zA-Z_]\w*", Name),  # Field
            (
                r"(\.\.\.)(\s+)(on)\b",
                bygroups(Punctuation, Whitespace, Keyword),
                "inline_fragment",
            ),
            (r"\.\.\.", Punctuation, "fragment_spread"),
            (r"\(", Punctuation, "arguments"),
            (r"@[a-zA-Z_]\w*", Name.Decorator, "directive"),
            (r"\{", Punctuation, "selection_set"),
            (r"\}", Punctuation, "#pop"),
        ],
        "directive": [
            include("ignored_tokens"),
            (r"\(", Punctuation, ("#pop", "arguments")),
        ],
        "arguments": [
            include("ignored_tokens"),
            (r"[a-zA-Z_]\w*", Name),
            (r":", Punctuation, "value"),
            (r"\)", Punctuation, "#pop"),
        ],
        # Fragments
        "fragment_definition": [
            include("ignored_tokens"),
            (r"[\]!]", Punctuation),  # For NamedType
            (r"on\b", Keyword, "type"),
            (r"[a-zA-Z_]\w*", Name.Function),
            (r"@[a-zA-Z_]\w*", Name.Decorator, "directive"),
            (r"\{", Punctuation, ("#pop", "selection_set")),
        ],
        "fragment_spread": [
            include("ignored_tokens"),
            (r"@[a-zA-Z_]\w*", Name.Decorator, "directive"),
            (r"[a-zA-Z_]\w*", Name, "#pop"),  # Fragment name
        ],
        "inline_fragment": [
            include("ignored_tokens"),
            (r"[a-zA-Z_]\w*", Name.Class),  # Type condition
            (r"@[a-zA-Z_]\w*", Name.Decorator, "directive"),
            (r"\{", Punctuation, ("#pop", "selection_set")),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\promql.py ===
"""
    pygments.lexers.promql
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Prometheus Query Language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, default, words
from pygments.token import Comment, Keyword, Name, Number, Operator, \
    Punctuation, String, Whitespace

__all__ = ["PromQLLexer"]


class PromQLLexer(RegexLexer):
    """
    For PromQL queries.

    For details about the grammar see:
    https://github.com/prometheus/prometheus/tree/master/promql/parser

    .. versionadded: 2.7
    """

    name = "PromQL"
    url = 'https://prometheus.io/docs/prometheus/latest/querying/basics/'
    aliases = ["promql"]
    filenames = ["*.promql"]
    version_added = ''

    base_keywords = (
        words(
            (
                "bool",
                "by",
                "group_left",
                "group_right",
                "ignoring",
                "offset",
                "on",
                "without",
            ),
            suffix=r"\b",
        ),
        Keyword,
    )

    aggregator_keywords = (
        words(
            (
                "sum",
                "min",
                "max",
                "avg",
                "group",
                "stddev",
                "stdvar",
                "count",
                "count_values",
                "bottomk",
                "topk",
                "quantile",
            ),
            suffix=r"\b",
        ),
        Keyword,
    )

    function_keywords = (
        words(
            (
                "abs",
                "absent",
                "absent_over_time",
                "avg_over_time",
                "ceil",
                "changes",
                "clamp_max",
                "clamp_min",
                "count_over_time",
                "day_of_month",
                "day_of_week",
                "days_in_month",
                "delta",
                "deriv",
                "exp",
                "floor",
                "histogram_quantile",
                "holt_winters",
                "hour",
                "idelta",
                "increase",
                "irate",
                "label_join",
                "label_replace",
                "ln",
                "log10",
                "log2",
                "max_over_time",
                "min_over_time",
                "minute",
                "month",
                "predict_linear",
                "quantile_over_time",
                "rate",
                "resets",
                "round",
                "scalar",
                "sort",
                "sort_desc",
                "sqrt",
                "stddev_over_time",
                "stdvar_over_time",
                "sum_over_time",
                "time",
                "timestamp",
                "vector",
                "year",
            ),
            suffix=r"\b",
        ),
        Keyword.Reserved,
    )

    tokens = {
        "root": [
            (r"\n", Whitespace),
            (r"\s+", Whitespace),
            (r",", Punctuation),
            # Keywords
            base_keywords,
            aggregator_keywords,
            function_keywords,
            # Offsets
            (r"[1-9][0-9]*[smhdwy]", String),
            # Numbers
            (r"-?[0-9]+\.[0-9]+", Number.Float),
            (r"-?[0-9]+", Number.Integer),
            # Comments
            (r"#.*?$", Comment.Single),
            # Operators
            (r"(\+|\-|\*|\/|\%|\^)", Operator),
            (r"==|!=|>=|<=|<|>", Operator),
            (r"and|or|unless", Operator.Word),
            # Metrics
            (r"[_a-zA-Z][a-zA-Z0-9_]+", Name.Variable),
            # Params
            (r'(["\'])(.*?)(["\'])', bygroups(Punctuation, String, Punctuation)),
            # Other states
            (r"\(", Operator, "function"),
            (r"\)", Operator),
            (r"\{", Punctuation, "labels"),
            (r"\[", Punctuation, "range"),
        ],
        "labels": [
            (r"\}", Punctuation, "#pop"),
            (r"\n", Whitespace),
            (r"\s+", Whitespace),
            (r",", Punctuation),
            (r'([_a-zA-Z][a-zA-Z0-9_]*?)(\s*?)(=~|!=|=|!~)(\s*?)("|\')(.*?)("|\')',
             bygroups(Name.Label, Whitespace, Operator, Whitespace,
                      Punctuation, String, Punctuation)),
        ],
        "range": [
            (r"\]", Punctuation, "#pop"),
            (r"[1-9][0-9]*[smhdwy]", String),
        ],
        "function": [
            (r"\)", Operator, "#pop"),
            (r"\(", Operator, "#push"),
            default("#pop"),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\dotenv\parser.py ===
import codecs
import re
from typing import (IO, Iterator, Match, NamedTuple, Optional,  # noqa:F401
                    Pattern, Sequence, Tuple)


def make_regex(string: str, extra_flags: int = 0) -> Pattern[str]:
    return re.compile(string, re.UNICODE | extra_flags)


_newline = make_regex(r"(\r\n|\n|\r)")
_multiline_whitespace = make_regex(r"\s*", extra_flags=re.MULTILINE)
_whitespace = make_regex(r"[^\S\r\n]*")
_export = make_regex(r"(?:export[^\S\r\n]+)?")
_single_quoted_key = make_regex(r"'([^']+)'")
_unquoted_key = make_regex(r"([^=\#\s]+)")
_equal_sign = make_regex(r"(=[^\S\r\n]*)")
_single_quoted_value = make_regex(r"'((?:\\'|[^'])*)'")
_double_quoted_value = make_regex(r'"((?:\\"|[^"])*)"')
_unquoted_value = make_regex(r"([^\r\n]*)")
_comment = make_regex(r"(?:[^\S\r\n]*#[^\r\n]*)?")
_end_of_line = make_regex(r"[^\S\r\n]*(?:\r\n|\n|\r|$)")
_rest_of_line = make_regex(r"[^\r\n]*(?:\r|\n|\r\n)?")
_double_quote_escapes = make_regex(r"\\[\\'\"abfnrtv]")
_single_quote_escapes = make_regex(r"\\[\\']")


class Original(NamedTuple):
    string: str
    line: int


class Binding(NamedTuple):
    key: Optional[str]
    value: Optional[str]
    original: Original
    error: bool


class Position:
    def __init__(self, chars: int, line: int) -> None:
        self.chars = chars
        self.line = line

    @classmethod
    def start(cls) -> "Position":
        return cls(chars=0, line=1)

    def set(self, other: "Position") -> None:
        self.chars = other.chars
        self.line = other.line

    def advance(self, string: str) -> None:
        self.chars += len(string)
        self.line += len(re.findall(_newline, string))


class Error(Exception):
    pass


class Reader:
    def __init__(self, stream: IO[str]) -> None:
        self.string = stream.read()
        self.position = Position.start()
        self.mark = Position.start()

    def has_next(self) -> bool:
        return self.position.chars < len(self.string)

    def set_mark(self) -> None:
        self.mark.set(self.position)

    def get_marked(self) -> Original:
        return Original(
            string=self.string[self.mark.chars:self.position.chars],
            line=self.mark.line,
        )

    def peek(self, count: int) -> str:
        return self.string[self.position.chars:self.position.chars + count]

    def read(self, count: int) -> str:
        result = self.string[self.position.chars:self.position.chars + count]
        if len(result) < count:
            raise Error("read: End of string")
        self.position.advance(result)
        return result

    def read_regex(self, regex: Pattern[str]) -> Sequence[str]:
        match = regex.match(self.string, self.position.chars)
        if match is None:
            raise Error("read_regex: Pattern not found")
        self.position.advance(self.string[match.start():match.end()])
        return match.groups()


def decode_escapes(regex: Pattern[str], string: str) -> str:
    def decode_match(match: Match[str]) -> str:
        return codecs.decode(match.group(0), 'unicode-escape')  # type: ignore

    return regex.sub(decode_match, string)


def parse_key(reader: Reader) -> Optional[str]:
    char = reader.peek(1)
    if char == "#":
        return None
    elif char == "'":
        (key,) = reader.read_regex(_single_quoted_key)
    else:
        (key,) = reader.read_regex(_unquoted_key)
    return key


def parse_unquoted_value(reader: Reader) -> str:
    (part,) = reader.read_regex(_unquoted_value)
    return re.sub(r"\s+#.*", "", part).rstrip()


def parse_value(reader: Reader) -> str:
    char = reader.peek(1)
    if char == u"'":
        (value,) = reader.read_regex(_single_quoted_value)
        return decode_escapes(_single_quote_escapes, value)
    elif char == u'"':
        (value,) = reader.read_regex(_double_quoted_value)
        return decode_escapes(_double_quote_escapes, value)
    elif char in (u"", u"\n", u"\r"):
        return u""
    else:
        return parse_unquoted_value(reader)


def parse_binding(reader: Reader) -> Binding:
    reader.set_mark()
    try:
        reader.read_regex(_multiline_whitespace)
        if not reader.has_next():
            return Binding(
                key=None,
                value=None,
                original=reader.get_marked(),
                error=False,
            )
        reader.read_regex(_export)
        key = parse_key(reader)
        reader.read_regex(_whitespace)
        if reader.peek(1) == "=":
            reader.read_regex(_equal_sign)
            value: Optional[str] = parse_value(reader)
        else:
            value = None
        reader.read_regex(_comment)
        reader.read_regex(_end_of_line)
        return Binding(
            key=key,
            value=value,
            original=reader.get_marked(),
            error=False,
        )
    except Error:
        reader.read_regex(_rest_of_line)
        return Binding(
            key=None,
            value=None,
            original=reader.get_marked(),
            error=True,
        )


def parse_stream(stream: IO[str]) -> Iterator[Binding]:
    reader = Reader(stream)
    while reader.has_next():
        yield parse_binding(reader)

# === NexusCore/openenv\Lib\site-packages\fsspec\compression.py ===
"""Helper functions for a standard streaming compression API"""

from zipfile import ZipFile

import fsspec.utils
from fsspec.spec import AbstractBufferedFile


def noop_file(file, mode, **kwargs):
    return file


# TODO: files should also be available as contexts
# should be functions of the form func(infile, mode=, **kwargs) -> file-like
compr = {None: noop_file}


def register_compression(name, callback, extensions, force=False):
    """Register an "inferable" file compression type.

    Registers transparent file compression type for use with fsspec.open.
    Compression can be specified by name in open, or "infer"-ed for any files
    ending with the given extensions.

    Args:
        name: (str) The compression type name. Eg. "gzip".
        callback: A callable of form (infile, mode, **kwargs) -> file-like.
            Accepts an input file-like object, the target mode and kwargs.
            Returns a wrapped file-like object.
        extensions: (str, Iterable[str]) A file extension, or list of file
            extensions for which to infer this compression scheme. Eg. "gz".
        force: (bool) Force re-registration of compression type or extensions.

    Raises:
        ValueError: If name or extensions already registered, and not force.

    """
    if isinstance(extensions, str):
        extensions = [extensions]

    # Validate registration
    if name in compr and not force:
        raise ValueError(f"Duplicate compression registration: {name}")

    for ext in extensions:
        if ext in fsspec.utils.compressions and not force:
            raise ValueError(f"Duplicate compression file extension: {ext} ({name})")

    compr[name] = callback

    for ext in extensions:
        fsspec.utils.compressions[ext] = name


def unzip(infile, mode="rb", filename=None, **kwargs):
    if "r" not in mode:
        filename = filename or "file"
        z = ZipFile(infile, mode="w", **kwargs)
        fo = z.open(filename, mode="w")
        fo.close = lambda closer=fo.close: closer() or z.close()
        return fo
    z = ZipFile(infile)
    if filename is None:
        filename = z.namelist()[0]
    return z.open(filename, mode="r", **kwargs)


register_compression("zip", unzip, "zip")

try:
    from bz2 import BZ2File
except ImportError:
    pass
else:
    register_compression("bz2", BZ2File, "bz2")

try:  # pragma: no cover
    from isal import igzip

    def isal(infile, mode="rb", **kwargs):
        return igzip.IGzipFile(fileobj=infile, mode=mode, **kwargs)

    register_compression("gzip", isal, "gz")
except ImportError:
    from gzip import GzipFile

    register_compression(
        "gzip", lambda f, **kwargs: GzipFile(fileobj=f, **kwargs), "gz"
    )

try:
    from lzma import LZMAFile

    register_compression("lzma", LZMAFile, "lzma")
    register_compression("xz", LZMAFile, "xz")
except ImportError:
    pass

try:
    import lzmaffi

    register_compression("lzma", lzmaffi.LZMAFile, "lzma", force=True)
    register_compression("xz", lzmaffi.LZMAFile, "xz", force=True)
except ImportError:
    pass


class SnappyFile(AbstractBufferedFile):
    def __init__(self, infile, mode, **kwargs):
        import snappy

        super().__init__(
            fs=None, path="snappy", mode=mode.strip("b") + "b", size=999999999, **kwargs
        )
        self.infile = infile
        if "r" in mode:
            self.codec = snappy.StreamDecompressor()
        else:
            self.codec = snappy.StreamCompressor()

    def _upload_chunk(self, final=False):
        self.buffer.seek(0)
        out = self.codec.add_chunk(self.buffer.read())
        self.infile.write(out)
        return True

    def seek(self, loc, whence=0):
        raise NotImplementedError("SnappyFile is not seekable")

    def seekable(self):
        return False

    def _fetch_range(self, start, end):
        """Get the specified set of bytes from remote"""
        data = self.infile.read(end - start)
        return self.codec.decompress(data)


try:
    import snappy

    snappy.compress(b"")
    # Snappy may use the .sz file extension, but this is not part of the
    # standard implementation.
    register_compression("snappy", SnappyFile, [])

except (ImportError, NameError, AttributeError):
    pass

try:
    import lz4.frame

    register_compression("lz4", lz4.frame.open, "lz4")
except ImportError:
    pass

try:
    import zstandard as zstd

    def zstandard_file(infile, mode="rb"):
        if "r" in mode:
            cctx = zstd.ZstdDecompressor()
            return cctx.stream_reader(infile)
        else:
            cctx = zstd.ZstdCompressor(level=10)
            return cctx.stream_writer(infile)

    register_compression("zstd", zstandard_file, "zst")
except ImportError:
    pass


def available_compressions():
    """Return a list of the implemented compressions."""
    return list(compr)

# === NexusCore/openenv\Lib\site-packages\google\api_core\gapic_v1\config.py ===
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

"""Helpers for loading gapic configuration data.

The Google API generator creates supplementary configuration for each RPC
method to tell the client library how to deal with retries and timeouts.
"""

import collections

import grpc

from google.api_core import exceptions
from google.api_core import retry
from google.api_core import timeout


_MILLIS_PER_SECOND = 1000.0


def _exception_class_for_grpc_status_name(name):
    """Returns the Google API exception class for a gRPC error code name.

    DEPRECATED: use ``exceptions.exception_class_for_grpc_status`` method
    directly instead.

    Args:
        name (str): The name of the gRPC status code, for example,
            ``UNAVAILABLE``.

    Returns:
        :func:`type`: The appropriate subclass of
            :class:`google.api_core.exceptions.GoogleAPICallError`.
    """
    return exceptions.exception_class_for_grpc_status(getattr(grpc.StatusCode, name))


def _retry_from_retry_config(retry_params, retry_codes, retry_impl=retry.Retry):
    """Creates a Retry object given a gapic retry configuration.

    DEPRECATED: instantiate retry and timeout classes directly instead.

    Args:
        retry_params (dict): The retry parameter values, for example::

            {
                "initial_retry_delay_millis": 1000,
                "retry_delay_multiplier": 2.5,
                "max_retry_delay_millis": 120000,
                "initial_rpc_timeout_millis": 120000,
                "rpc_timeout_multiplier": 1.0,
                "max_rpc_timeout_millis": 120000,
                "total_timeout_millis": 600000
            }

        retry_codes (sequence[str]): The list of retryable gRPC error code
            names.

    Returns:
        google.api_core.retry.Retry: The default retry object for the method.
    """
    exception_classes = [
        _exception_class_for_grpc_status_name(code) for code in retry_codes
    ]
    return retry_impl(
        retry.if_exception_type(*exception_classes),
        initial=(retry_params["initial_retry_delay_millis"] / _MILLIS_PER_SECOND),
        maximum=(retry_params["max_retry_delay_millis"] / _MILLIS_PER_SECOND),
        multiplier=retry_params["retry_delay_multiplier"],
        deadline=retry_params["total_timeout_millis"] / _MILLIS_PER_SECOND,
    )


def _timeout_from_retry_config(retry_params):
    """Creates a ExponentialTimeout object given a gapic retry configuration.

    DEPRECATED: instantiate retry and timeout classes directly instead.

    Args:
        retry_params (dict): The retry parameter values, for example::

            {
                "initial_retry_delay_millis": 1000,
                "retry_delay_multiplier": 2.5,
                "max_retry_delay_millis": 120000,
                "initial_rpc_timeout_millis": 120000,
                "rpc_timeout_multiplier": 1.0,
                "max_rpc_timeout_millis": 120000,
                "total_timeout_millis": 600000
            }

    Returns:
        google.api_core.retry.ExponentialTimeout: The default time object for
            the method.
    """
    return timeout.ExponentialTimeout(
        initial=(retry_params["initial_rpc_timeout_millis"] / _MILLIS_PER_SECOND),
        maximum=(retry_params["max_rpc_timeout_millis"] / _MILLIS_PER_SECOND),
        multiplier=retry_params["rpc_timeout_multiplier"],
        deadline=(retry_params["total_timeout_millis"] / _MILLIS_PER_SECOND),
    )


MethodConfig = collections.namedtuple("MethodConfig", ["retry", "timeout"])


def parse_method_configs(interface_config, retry_impl=retry.Retry):
    """Creates default retry and timeout objects for each method in a gapic
    interface config.

    DEPRECATED: instantiate retry and timeout classes directly instead.

    Args:
        interface_config (Mapping): The interface config section of the full
            gapic library config. For example, If the full configuration has
            an interface named ``google.example.v1.ExampleService`` you would
            pass in just that interface's configuration, for example
            ``gapic_config['interfaces']['google.example.v1.ExampleService']``.
        retry_impl (Callable): The constructor that creates a retry decorator
            that will be applied to the method based on method configs.

    Returns:
        Mapping[str, MethodConfig]: A mapping of RPC method names to their
            configuration.
    """
    # Grab all the retry codes
    retry_codes_map = {
        name: retry_codes
        for name, retry_codes in interface_config.get("retry_codes", {}).items()
    }

    # Grab all of the retry params
    retry_params_map = {
        name: retry_params
        for name, retry_params in interface_config.get("retry_params", {}).items()
    }

    # Iterate through all the API methods and create a flat MethodConfig
    # instance for each one.
    method_configs = {}

    for method_name, method_params in interface_config.get("methods", {}).items():
        retry_params_name = method_params.get("retry_params_name")

        if retry_params_name is not None:
            retry_params = retry_params_map[retry_params_name]
            retry_ = _retry_from_retry_config(
                retry_params,
                retry_codes_map[method_params["retry_codes_name"]],
                retry_impl,
            )
            timeout_ = _timeout_from_retry_config(retry_params)

        # No retry config, so this is a non-retryable method.
        else:
            retry_ = None
            timeout_ = timeout.ConstantTimeout(
                method_params["timeout_millis"] / _MILLIS_PER_SECOND
            )

        method_configs[method_name] = MethodConfig(retry=retry_, timeout=timeout_)

    return method_configs

# === NexusCore/openenv\Lib\site-packages\google\auth\crypt\es256.py ===
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ECDSA (ES256) verifier and signer that use the ``cryptography`` library.
"""

from cryptography import utils  # type: ignore
import cryptography.exceptions
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
import cryptography.x509

from google.auth import _helpers
from google.auth.crypt import base


_CERTIFICATE_MARKER = b"-----BEGIN CERTIFICATE-----"
_BACKEND = backends.default_backend()
_PADDING = padding.PKCS1v15()


class ES256Verifier(base.Verifier):
    """Verifies ECDSA cryptographic signatures using public keys.

    Args:
        public_key (
                cryptography.hazmat.primitives.asymmetric.ec.ECDSAPublicKey):
            The public key used to verify signatures.
    """

    def __init__(self, public_key):
        self._pubkey = public_key

    @_helpers.copy_docstring(base.Verifier)
    def verify(self, message, signature):
        # First convert (r||s) raw signature to ASN1 encoded signature.
        sig_bytes = _helpers.to_bytes(signature)
        if len(sig_bytes) != 64:
            return False
        r = (
            int.from_bytes(sig_bytes[:32], byteorder="big")
            if _helpers.is_python_3()
            else utils.int_from_bytes(sig_bytes[:32], byteorder="big")
        )
        s = (
            int.from_bytes(sig_bytes[32:], byteorder="big")
            if _helpers.is_python_3()
            else utils.int_from_bytes(sig_bytes[32:], byteorder="big")
        )
        asn1_sig = encode_dss_signature(r, s)

        message = _helpers.to_bytes(message)
        try:
            self._pubkey.verify(asn1_sig, message, ec.ECDSA(hashes.SHA256()))
            return True
        except (ValueError, cryptography.exceptions.InvalidSignature):
            return False

    @classmethod
    def from_string(cls, public_key):
        """Construct an Verifier instance from a public key or public
        certificate string.

        Args:
            public_key (Union[str, bytes]): The public key in PEM format or the
                x509 public key certificate.

        Returns:
            Verifier: The constructed verifier.

        Raises:
            ValueError: If the public key can't be parsed.
        """
        public_key_data = _helpers.to_bytes(public_key)

        if _CERTIFICATE_MARKER in public_key_data:
            cert = cryptography.x509.load_pem_x509_certificate(
                public_key_data, _BACKEND
            )
            pubkey = cert.public_key()

        else:
            pubkey = serialization.load_pem_public_key(public_key_data, _BACKEND)

        return cls(pubkey)


class ES256Signer(base.Signer, base.FromServiceAccountMixin):
    """Signs messages with an ECDSA private key.

    Args:
        private_key (
                cryptography.hazmat.primitives.asymmetric.ec.ECDSAPrivateKey):
            The private key to sign with.
        key_id (str): Optional key ID used to identify this private key. This
            can be useful to associate the private key with its associated
            public key or certificate.
    """

    def __init__(self, private_key, key_id=None):
        self._key = private_key
        self._key_id = key_id

    @property  # type: ignore
    @_helpers.copy_docstring(base.Signer)
    def key_id(self):
        return self._key_id

    @_helpers.copy_docstring(base.Signer)
    def sign(self, message):
        message = _helpers.to_bytes(message)
        asn1_signature = self._key.sign(message, ec.ECDSA(hashes.SHA256()))

        # Convert ASN1 encoded signature to (r||s) raw signature.
        (r, s) = decode_dss_signature(asn1_signature)
        return (
            (r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big"))
            if _helpers.is_python_3()
            else (utils.int_to_bytes(r, 32) + utils.int_to_bytes(s, 32))
        )

    @classmethod
    def from_string(cls, key, key_id=None):
        """Construct a RSASigner from a private key in PEM format.

        Args:
            key (Union[bytes, str]): Private key in PEM format.
            key_id (str): An optional key id used to identify the private key.

        Returns:
            google.auth.crypt._cryptography_rsa.RSASigner: The
            constructed signer.

        Raises:
            ValueError: If ``key`` is not ``bytes`` or ``str`` (unicode).
            UnicodeDecodeError: If ``key`` is ``bytes`` but cannot be decoded
                into a UTF-8 ``str``.
            ValueError: If ``cryptography`` "Could not deserialize key data."
        """
        key = _helpers.to_bytes(key)
        private_key = serialization.load_pem_private_key(
            key, password=None, backend=_BACKEND
        )
        return cls(private_key, key_id=key_id)

    def __getstate__(self):
        """Pickle helper that serializes the _key attribute."""
        state = self.__dict__.copy()
        state["_key"] = self._key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return state

    def __setstate__(self, state):
        """Pickle helper that deserializes the _key attribute."""
        state["_key"] = serialization.load_pem_private_key(state["_key"], None)
        self.__dict__.update(state)

# === NexusCore/openenv\Lib\site-packages\google\auth\crypt\_python_rsa.py ===
# Copyright 2016 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pure-Python RSA cryptography implementation.

Uses the ``rsa``, ``pyasn1`` and ``pyasn1_modules`` packages
to parse PEM files storing PKCS#1 or PKCS#8 keys as well as
certificates. There is no support for p12 files.
"""

from __future__ import absolute_import

import io

from pyasn1.codec.der import decoder  # type: ignore
from pyasn1_modules import pem  # type: ignore
from pyasn1_modules.rfc2459 import Certificate  # type: ignore
from pyasn1_modules.rfc5208 import PrivateKeyInfo  # type: ignore
import rsa  # type: ignore

from google.auth import _helpers
from google.auth import exceptions
from google.auth.crypt import base

_POW2 = (128, 64, 32, 16, 8, 4, 2, 1)
_CERTIFICATE_MARKER = b"-----BEGIN CERTIFICATE-----"
_PKCS1_MARKER = ("-----BEGIN RSA PRIVATE KEY-----", "-----END RSA PRIVATE KEY-----")
_PKCS8_MARKER = ("-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----")
_PKCS8_SPEC = PrivateKeyInfo()


def _bit_list_to_bytes(bit_list):
    """Converts an iterable of 1s and 0s to bytes.

    Combines the list 8 at a time, treating each group of 8 bits
    as a single byte.

    Args:
        bit_list (Sequence): Sequence of 1s and 0s.

    Returns:
        bytes: The decoded bytes.
    """
    num_bits = len(bit_list)
    byte_vals = bytearray()
    for start in range(0, num_bits, 8):
        curr_bits = bit_list[start : start + 8]
        char_val = sum(val * digit for val, digit in zip(_POW2, curr_bits))
        byte_vals.append(char_val)
    return bytes(byte_vals)


class RSAVerifier(base.Verifier):
    """Verifies RSA cryptographic signatures using public keys.

    Args:
        public_key (rsa.key.PublicKey): The public key used to verify
            signatures.
    """

    def __init__(self, public_key):
        self._pubkey = public_key

    @_helpers.copy_docstring(base.Verifier)
    def verify(self, message, signature):
        message = _helpers.to_bytes(message)
        try:
            return rsa.pkcs1.verify(message, signature, self._pubkey)
        except (ValueError, rsa.pkcs1.VerificationError):
            return False

    @classmethod
    def from_string(cls, public_key):
        """Construct an Verifier instance from a public key or public
        certificate string.

        Args:
            public_key (Union[str, bytes]): The public key in PEM format or the
                x509 public key certificate.

        Returns:
            google.auth.crypt._python_rsa.RSAVerifier: The constructed verifier.

        Raises:
            ValueError: If the public_key can't be parsed.
        """
        public_key = _helpers.to_bytes(public_key)
        is_x509_cert = _CERTIFICATE_MARKER in public_key

        # If this is a certificate, extract the public key info.
        if is_x509_cert:
            der = rsa.pem.load_pem(public_key, "CERTIFICATE")
            asn1_cert, remaining = decoder.decode(der, asn1Spec=Certificate())
            if remaining != b"":
                raise exceptions.InvalidValue("Unused bytes", remaining)

            cert_info = asn1_cert["tbsCertificate"]["subjectPublicKeyInfo"]
            key_bytes = _bit_list_to_bytes(cert_info["subjectPublicKey"])
            pubkey = rsa.PublicKey.load_pkcs1(key_bytes, "DER")
        else:
            pubkey = rsa.PublicKey.load_pkcs1(public_key, "PEM")
        return cls(pubkey)


class RSASigner(base.Signer, base.FromServiceAccountMixin):
    """Signs messages with an RSA private key.

    Args:
        private_key (rsa.key.PrivateKey): The private key to sign with.
        key_id (str): Optional key ID used to identify this private key. This
            can be useful to associate the private key with its associated
            public key or certificate.
    """

    def __init__(self, private_key, key_id=None):
        self._key = private_key
        self._key_id = key_id

    @property  # type: ignore
    @_helpers.copy_docstring(base.Signer)
    def key_id(self):
        return self._key_id

    @_helpers.copy_docstring(base.Signer)
    def sign(self, message):
        message = _helpers.to_bytes(message)
        return rsa.pkcs1.sign(message, self._key, "SHA-256")

    @classmethod
    def from_string(cls, key, key_id=None):
        """Construct an Signer instance from a private key in PEM format.

        Args:
            key (str): Private key in PEM format.
            key_id (str): An optional key id used to identify the private key.

        Returns:
            google.auth.crypt.Signer: The constructed signer.

        Raises:
            ValueError: If the key cannot be parsed as PKCS#1 or PKCS#8 in
                PEM format.
        """
        key = _helpers.from_bytes(key)  # PEM expects str in Python 3
        marker_id, key_bytes = pem.readPemBlocksFromFile(
            io.StringIO(key), _PKCS1_MARKER, _PKCS8_MARKER
        )

        # Key is in pkcs1 format.
        if marker_id == 0:
            private_key = rsa.key.PrivateKey.load_pkcs1(key_bytes, format="DER")
        # Key is in pkcs8.
        elif marker_id == 1:
            key_info, remaining = decoder.decode(key_bytes, asn1Spec=_PKCS8_SPEC)
            if remaining != b"":
                raise exceptions.InvalidValue("Unused bytes", remaining)
            private_key_info = key_info.getComponentByName("privateKey")
            private_key = rsa.key.PrivateKey.load_pkcs1(
                private_key_info.asOctets(), format="DER"
            )
        else:
            raise exceptions.MalformedError("No key could be detected.")

        return cls(private_key, key_id=key_id)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\vision\vision.py ===
import base64
import contextlib
import io
import os
import tempfile

from PIL import Image

from ...utils.lazy_import import lazy_import
from ..utils.computer_vision import pytesseract_get_text

# transformers = lazy_import("transformers") # Doesn't work for some reason! We import it later.


class Vision:
    def __init__(self, computer):
        self.computer = computer
        self.model = None  # Will load upon first use
        self.tokenizer = None  # Will load upon first use
        self.easyocr = None

    def load(self, load_moondream=True, load_easyocr=True):
        # print("Loading vision models (Moondream, EasyOCR)...\n")

        with contextlib.redirect_stdout(
            open(os.devnull, "w")
        ), contextlib.redirect_stderr(open(os.devnull, "w")):
            if self.easyocr == None and load_easyocr:
                import easyocr

                self.easyocr = easyocr.Reader(
                    ["en"]
                )  # this needs to run only once to load the model into memory

            if self.model == None and load_moondream:
                import transformers  # Wait until we use it. Transformers can't be lazy loaded for some reason!

                os.environ["TOKENIZERS_PARALLELISM"] = "false"

                if self.computer.debug:
                    print(
                        "Open Interpreter will use Moondream (tiny vision model) to describe images to the language model. Set `interpreter.llm.vision_renderer = None` to disable this behavior."
                    )
                    print(
                        "Alternatively, you can use a vision-supporting LLM and set `interpreter.llm.supports_vision = True`."
                    )
                model_id = "vikhyatk/moondream2"
                revision = "2024-04-02"
                print("loading model")

                self.model = transformers.AutoModelForCausalLM.from_pretrained(
                    model_id, trust_remote_code=True, revision=revision
                )
                self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                    model_id, revision=revision
                )
                return True

    def ocr(
        self,
        base_64=None,
        path=None,
        lmc=None,
        pil_image=None,
    ):
        """
        Gets OCR of image.
        """

        if lmc:
            if "base64" in lmc["format"]:
                # # Extract the extension from the format, default to 'png' if not specified
                # if "." in lmc["format"]:
                #     extension = lmc["format"].split(".")[-1]
                # else:
                #     extension = "png"
                # Save the base64 content as a temporary file
                img_data = base64.b64decode(lmc["content"])
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png"
                ) as temp_file:
                    temp_file.write(img_data)
                    temp_file_path = temp_file.name

                # Set path to the path of the temporary file
                path = temp_file_path

            elif lmc["format"] == "path":
                # Convert to base64
                path = lmc["content"]
        elif base_64:
            # Save the base64 content as a temporary file
            img_data = base64.b64decode(base_64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(img_data)
                temp_file_path = temp_file.name

            # Set path to the path of the temporary file
            path = temp_file_path
        elif path:
            pass
        elif pil_image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                pil_image.save(temp_file, format="PNG")
                temp_file_path = temp_file.name

            # Set path to the path of the temporary file
            path = temp_file_path

        try:
            if not self.easyocr:
                self.load(load_moondream=False)
            result = self.easyocr.readtext(path)
            text = " ".join([item[1] for item in result])
            return text.strip()
        except ImportError:
            print(
                "\nTo use local vision, run `pip install 'open-interpreter[local]'`.\n"
            )
            return ""

    def query(
        self,
        query="Describe this image. Also tell me what text is in the image, if any.",
        base_64=None,
        path=None,
        lmc=None,
        pil_image=None,
    ):
        """
        Uses Moondream to ask query of the image (which can be a base64, path, or lmc message)
        """

        if self.model == None and self.tokenizer == None:
            try:
                success = self.load(load_easyocr=False)
            except ImportError:
                print(
                    "\nTo use local vision, run `pip install 'open-interpreter[local]'`.\n"
                )
                return ""
            if not success:
                return ""

        if lmc:
            if "base64" in lmc["format"]:
                # # Extract the extension from the format, default to 'png' if not specified
                # if "." in lmc["format"]:
                #     extension = lmc["format"].split(".")[-1]
                # else:
                #     extension = "png"

                # Decode the base64 image
                img_data = base64.b64decode(lmc["content"])
                img = Image.open(io.BytesIO(img_data))

            elif lmc["format"] == "path":
                # Convert to base64
                image_path = lmc["content"]
                img = Image.open(image_path)
        elif base_64:
            img_data = base64.b64decode(base_64)
            img = Image.open(io.BytesIO(img_data))
        elif path:
            img = Image.open(path)
        elif pil_image:
            img = pil_image

        with contextlib.redirect_stdout(open(os.devnull, "w")):
            enc_image = self.model.encode_image(img)
            answer = self.model.answer_question(
                enc_image, query, self.tokenizer, max_length=400
            )

        return answer

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\deepeval\deepeval.py ===
import os
import uuid
from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.deepeval.api import Api, Endpoints, HttpMethods
from litellm.integrations.deepeval.types import (
    BaseApiSpan,
    SpanApiType,
    TraceApi,
    TraceSpanApiStatus,
)
from litellm.integrations.deepeval.utils import (
    to_zod_compatible_iso,
    validate_environment,
)
from litellm._logging import verbose_logger


# This file includes the custom callbacks for LiteLLM Proxy
# Once defined, these can be passed in proxy_config.yaml
class DeepEvalLogger(CustomLogger):
    """Logs litellm traces to DeepEval's platform."""

    def __init__(self, *args, **kwargs):
        api_key = os.getenv("CONFIDENT_API_KEY")
        self.litellm_environment = os.getenv("LITELM_ENVIRONMENT", "development")
        validate_environment(self.litellm_environment)
        if not api_key:
            raise ValueError(
                "Please set 'CONFIDENT_API_KEY=<>' in your environment variables."
            )
        self.api = Api(api_key=api_key)
        super().__init__(*args, **kwargs)

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Logs a success event to DeepEval's platform."""
        self._sync_event_handler(
            kwargs, response_obj, start_time, end_time, is_success=True
        )

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Logs a failure event to DeepEval's platform."""
        self._sync_event_handler(
            kwargs, response_obj, start_time, end_time, is_success=False
        )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Logs a failure event to DeepEval's platform."""
        await self._async_event_handler(
            kwargs, response_obj, start_time, end_time, is_success=False
        )

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Logs a success event to DeepEval's platform."""
        await self._async_event_handler(
            kwargs, response_obj, start_time, end_time, is_success=True
        )

    def _prepare_trace_api(
        self, kwargs, response_obj, start_time, end_time, is_success
    ):
        _start_time = to_zod_compatible_iso(start_time)
        _end_time = to_zod_compatible_iso(end_time)
        _standard_logging_object = kwargs.get("standard_logging_object", {})
        base_api_span = self._create_base_api_span(
            kwargs,
            standard_logging_object=_standard_logging_object,
            start_time=_start_time,
            end_time=_end_time,
            is_success=is_success,
        )
        trace_api = self._create_trace_api(
            base_api_span,
            standard_logging_object=_standard_logging_object,
            start_time=_start_time,
            end_time=_end_time,
            litellm_environment=self.litellm_environment,
        )

        body = {}

        try:
            body = trace_api.model_dump(by_alias=True, exclude_none=True)
        except AttributeError:
            # Pydantic version below 2.0
            body = trace_api.dict(by_alias=True, exclude_none=True)
        return body

    def _sync_event_handler(
        self, kwargs, response_obj, start_time, end_time, is_success
    ):
        body = self._prepare_trace_api(
            kwargs, response_obj, start_time, end_time, is_success
        )
        try:
            response = self.api.send_request(
                method=HttpMethods.POST,
                endpoint=Endpoints.TRACING_ENDPOINT,
                body=body,
            )
        except Exception as e:
            raise e
        verbose_logger.debug(
            "DeepEvalLogger: sync_log_failure_event: Api response", response
        )

    async def _async_event_handler(
        self, kwargs, response_obj, start_time, end_time, is_success
    ):
        body = self._prepare_trace_api(
            kwargs, response_obj, start_time, end_time, is_success
        )
        response = await self.api.a_send_request(
            method=HttpMethods.POST,
            endpoint=Endpoints.TRACING_ENDPOINT,
            body=body,
        )

        verbose_logger.debug(
            "DeepEvalLogger: async_event_handler: Api response", response
        )

    def _create_base_api_span(
        self, kwargs, standard_logging_object, start_time, end_time, is_success
    ):
        # extract usage
        usage = standard_logging_object.get("response", {}).get("usage", {})
        if is_success:
            output = (
                standard_logging_object.get("response", {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "NO_OUTPUT")
            )
        else:
            output = str(standard_logging_object.get("error_string", ""))
        return BaseApiSpan(
            uuid=standard_logging_object.get("id", uuid.uuid4()),
            name=(
                "litellm_success_callback" if is_success else "litellm_failure_callback"
            ),
            status=(
                TraceSpanApiStatus.SUCCESS if is_success else TraceSpanApiStatus.ERRORED
            ),
            type=SpanApiType.LLM,
            traceUuid=standard_logging_object.get("trace_id", uuid.uuid4()),
            startTime=str(start_time),
            endTime=str(end_time),
            input=kwargs.get("input", "NO_INPUT"),
            output=output,
            model=standard_logging_object.get("model", None),
            inputTokenCount=usage.get("prompt_tokens", None) if is_success else None,
            outputTokenCount=(
                usage.get("completion_tokens", None) if is_success else None
            ),
        )

    def _create_trace_api(
        self,
        base_api_span,
        standard_logging_object,
        start_time,
        end_time,
        litellm_environment,
    ):
        return TraceApi(
            uuid=standard_logging_object.get("trace_id", uuid.uuid4()),
            baseSpans=[],
            agentSpans=[],
            llmSpans=[base_api_span],
            retrieverSpans=[],
            toolSpans=[],
            startTime=str(start_time),
            endTime=str(end_time),
            environment=litellm_environment,
        )

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\email_templates\user_invitation_email.py ===
"""
Modern Email Templates for LiteLLM Email Service with professional styling
"""

USER_INVITATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to LiteLLM</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #333333;
            background-color: #f8f8f8;
            line-height: 1.5;
        }}
        .container {{
            max-width: 560px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .logo {{
            padding: 24px 0 0 24px;
            text-align: left;
        }}
        .greeting {{
            font-size: 16px;
            margin-bottom: 20px;
            color: #333333;
        }}
        .content {{
            padding: 24px 40px 32px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            margin-top: 24px;
            margin-bottom: 16px;
            color: #333333;
        }}
        p {{
            font-size: 16px;
            color: #333333;
            margin-bottom: 16px;
            line-height: 1.5;
        }}
        .intro-text {{
            margin-bottom: 24px;
        }}
        .link {{
            color: #6366f1;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{
            text-decoration: underline;
        }}
        .link-with-arrow {{
            display: inline-flex;
            align-items: center;
            color: #6366f1;
            text-decoration: none;
            font-weight: 500;
            margin-bottom: 20px;
        }}
        .link-with-arrow:hover {{
            text-decoration: underline;
        }}
        .arrow {{
            margin-left: 6px;
        }}
        .divider {{
            height: 1px;
            background-color: #f1f1f1;
            margin: 24px 0;
        }}
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #5c5ce0;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            margin-top: 12px;
            text-align: center;
            font-size: 15px;
            transition: background-color 0.2s ease;
        }}
        .btn:hover {{
            background-color: #4b4bb3;
        }}
        .btn-container {{
            text-align: center;
            margin: 24px 0;
        }}
        .footer {{
            padding: 24px 40px 32px;
            text-align: left;
            color: #666;
            font-size: 14px;
        }}
        .quickstart {{
            margin-top: 32px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="{email_logo_url}" alt="LiteLLM Logo" style="height: 32px; width: auto;">
        </div>
        <div class="content">
            <h1>Welcome to LiteLLM</h1>

            <div class="greeting">
                <p>Hi {recipient_email},</p>
            </div>
            
            <div class="intro-text">
                <p>LiteLLM allows you to call 100+ LLM providers in the OpenAI API format. Get started by accepting your invitation.</p>
            </div>

            <div class="btn-container">
                <a href="{base_url}" class="btn">Accept Invitation</a>
            </div>
            
            <div class="quickstart">
                <p>Here's a quickstart guide to get you started:</p>
            </div>
            
            <div class="divider"></div>
            
            <a href="https://docs.litellm.ai/docs/proxy/user_keys" class="link-with-arrow">
                Make your first LLM request →
                <span class="arrow"></span>
            </a>
            
            <p>Making LLM requests with OpenAI SDK, Langchain, LlamaIndex, and more.</p>
            
            <div class="divider"></div>
            
            <a href="https://docs.litellm.ai/docs/supported_endpoints" class="link-with-arrow">
                Supported Endpoints →
                <span class="arrow"></span>
            </a>
            
            <p>View all supported LLM endpoints on LiteLLM (/chat/completions, /embeddings, /responses etc.)</p>
            
            <div class="divider"></div>
            
            <a href="https://docs.litellm.ai/docs/pass_through/vertex_ai" class="link-with-arrow">
                Passthrough Endpoints →
                <span class="arrow"></span>
            </a>
            
            <p>We support calling VertexAI, Anthropic, and other providers in their native API format.</p>
            
            <div class="divider"></div>
            
            <p>Thanks for signing up. We're here to help you and your team. If you have any questions, contact us at {email_support_contact}</p>

        </div>
        {email_footer}
    </div>
</body>
</html>
"""

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\SlackAlerting\hanging_request_check.py ===
"""
Class to check for LLM API hanging requests


Notes:
- Do not create tasks that sleep, that can saturate the event loop
- Do not store large objects (eg. messages in memory) that can increase RAM usage
"""

import asyncio
from typing import TYPE_CHECKING, Any, Optional

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.in_memory_cache import InMemoryCache
from litellm.litellm_core_utils.core_helpers import get_litellm_metadata_from_kwargs
from litellm.types.integrations.slack_alerting import (
    HANGING_ALERT_BUFFER_TIME_SECONDS,
    MAX_OLDEST_HANGING_REQUESTS_TO_CHECK,
    HangingRequestData,
)

if TYPE_CHECKING:
    from litellm.integrations.SlackAlerting.slack_alerting import SlackAlerting
else:
    SlackAlerting = Any


class AlertingHangingRequestCheck:
    """
    Class to safely handle checking hanging requests alerts
    """

    def __init__(
        self,
        slack_alerting_object: SlackAlerting,
    ):
        self.slack_alerting_object = slack_alerting_object
        self.hanging_request_cache = InMemoryCache(
            default_ttl=int(
                self.slack_alerting_object.alerting_threshold
                + HANGING_ALERT_BUFFER_TIME_SECONDS
            ),
        )

    async def add_request_to_hanging_request_check(
        self,
        request_data: Optional[dict] = None,
    ):
        """
        Add a request to the hanging request cache. This is the list of request_ids that gets periodicall checked for hanging requests
        """
        if request_data is None:
            return

        request_metadata = get_litellm_metadata_from_kwargs(kwargs=request_data)
        model = request_data.get("model", "")
        api_base: Optional[str] = None

        if request_data.get("deployment", None) is not None and isinstance(
            request_data["deployment"], dict
        ):
            api_base = litellm.get_api_base(
                model=model,
                optional_params=request_data["deployment"].get("litellm_params", {}),
            )

        hanging_request_data = HangingRequestData(
            request_id=request_data.get("litellm_call_id", ""),
            model=model,
            api_base=api_base,
            key_alias=request_metadata.get("user_api_key_alias", ""),
            team_alias=request_metadata.get("user_api_key_team_alias", ""),
        )

        await self.hanging_request_cache.async_set_cache(
            key=hanging_request_data.request_id,
            value=hanging_request_data,
            ttl=int(
                self.slack_alerting_object.alerting_threshold
                + HANGING_ALERT_BUFFER_TIME_SECONDS
            ),
        )
        return

    async def send_alerts_for_hanging_requests(self):
        """
        Send alerts for hanging requests
        """
        from litellm.proxy.proxy_server import proxy_logging_obj

        #########################################################
        # Find all requests that have been hanging for more than the alerting threshold
        # Get the last 50 oldest items in the cache and check if they have completed
        #########################################################
        # check if request_id is in internal usage cache
        if proxy_logging_obj.internal_usage_cache is None:
            return

        hanging_requests = await self.hanging_request_cache.async_get_oldest_n_keys(
            n=MAX_OLDEST_HANGING_REQUESTS_TO_CHECK,
        )

        for request_id in hanging_requests:
            hanging_request_data: Optional[HangingRequestData] = (
                await self.hanging_request_cache.async_get_cache(
                    key=request_id,
                )
            )

            if hanging_request_data is None:
                continue

            request_status = (
                await proxy_logging_obj.internal_usage_cache.async_get_cache(
                    key="request_status:{}".format(hanging_request_data.request_id),
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
            )
            # this means the request status was either success or fail
            # and is not hanging
            if request_status is not None:
                # clear this request from hanging request cache since the request was either success or failed
                self.hanging_request_cache._remove_key(
                    key=request_id,
                )
                continue

            ################
            # Send the Alert on Slack
            ################
            await self.send_hanging_request_alert(
                hanging_request_data=hanging_request_data
            )

        return

    async def check_for_hanging_requests(
        self,
    ):
        """
        Background task that checks all request ids in self.hanging_request_cache to check if they have completed

        Runs every alerting_threshold/2 seconds to check for hanging requests
        """
        while True:
            verbose_proxy_logger.debug("Checking for hanging requests....")
            await self.send_alerts_for_hanging_requests()
            await asyncio.sleep(self.slack_alerting_object.alerting_threshold / 2)

    async def send_hanging_request_alert(
        self,
        hanging_request_data: HangingRequestData,
    ):
        """
        Send a hanging request alert
        """
        from litellm.integrations.SlackAlerting.slack_alerting import AlertType

        ################
        # Send the Alert on Slack
        ################
        request_info = f"""Request Model: `{hanging_request_data.model}`
API Base: `{hanging_request_data.api_base}`
Key Alias: `{hanging_request_data.key_alias}`
Team Alias: `{hanging_request_data.team_alias}`"""

        alerting_message = f"`Requests are hanging - {self.slack_alerting_object.alerting_threshold}s+ request time`"
        await self.slack_alerting_object.send_alert(
            message=alerting_message + "\n" + request_info,
            level="Medium",
            alert_type=AlertType.llm_requests_hanging,
            alerting_metadata=hanging_request_data.alerting_metadata or {},
        )

# === NexusCore/openenv\Lib\site-packages\nltk\classify\senna.py ===
# Natural Language Toolkit: Senna Interface
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A general interface to the SENNA pipeline that supports any of the
operations specified in SUPPORTED_OPERATIONS.

Applying multiple operations at once has the speed advantage. For example,
Senna will automatically determine POS tags if you are extracting named
entities. Applying both of the operations will cost only the time of
extracting the named entities.

The SENNA pipeline has a fixed maximum size of the sentences that it can read.
By default it is 1024 token/sentence. If you have larger sentences, changing
the MAX_SENTENCE_SIZE value in SENNA_main.c should be considered and your
system specific binary should be rebuilt. Otherwise this could introduce
misalignment errors.

The input is:

- path to the directory that contains SENNA executables. If the path is incorrect,
  Senna will automatically search for executable file specified in SENNA environment variable
- List of the operations needed to be performed.
- (optionally) the encoding of the input data (default:utf-8)

Note: Unit tests for this module can be found in test/unit/test_senna.py

>>> from nltk.classify import Senna
>>> pipeline = Senna('/usr/share/senna-v3.0', ['pos', 'chk', 'ner'])  # doctest: +SKIP
>>> sent = 'Dusseldorf is an international business center'.split()
>>> [(token['word'], token['chk'], token['ner'], token['pos']) for token in pipeline.tag(sent)]  # doctest: +SKIP
[('Dusseldorf', 'B-NP', 'B-LOC', 'NNP'), ('is', 'B-VP', 'O', 'VBZ'), ('an', 'B-NP', 'O', 'DT'),
('international', 'I-NP', 'O', 'JJ'), ('business', 'I-NP', 'O', 'NN'), ('center', 'I-NP', 'O', 'NN')]
"""

from os import environ, path, sep
from platform import architecture, system
from subprocess import PIPE, Popen

from nltk.tag.api import TaggerI


class Senna(TaggerI):
    SUPPORTED_OPERATIONS = ["pos", "chk", "ner"]

    def __init__(self, senna_path, operations, encoding="utf-8"):
        self._encoding = encoding
        self._path = path.normpath(senna_path) + sep

        # Verifies the existence of the executable on the self._path first
        # senna_binary_file_1 = self.executable(self._path)
        exe_file_1 = self.executable(self._path)
        if not path.isfile(exe_file_1):
            # Check for the system environment
            if "SENNA" in environ:
                # self._path = path.join(environ['SENNA'],'')
                self._path = path.normpath(environ["SENNA"]) + sep
                exe_file_2 = self.executable(self._path)
                if not path.isfile(exe_file_2):
                    raise LookupError(
                        "Senna executable expected at %s or %s but not found"
                        % (exe_file_1, exe_file_2)
                    )

        self.operations = operations

    def executable(self, base_path):
        """
        The function that determines the system specific binary that should be
        used in the pipeline. In case, the system is not known the default senna binary will
        be used.
        """
        os_name = system()
        if os_name == "Linux":
            bits = architecture()[0]
            if bits == "64bit":
                return path.join(base_path, "senna-linux64")
            return path.join(base_path, "senna-linux32")
        if os_name == "Windows":
            return path.join(base_path, "senna-win32.exe")
        if os_name == "Darwin":
            return path.join(base_path, "senna-osx")
        return path.join(base_path, "senna")

    def _map(self):
        """
        A method that calculates the order of the columns that SENNA pipeline
        will output the tags into. This depends on the operations being ordered.
        """
        _map = {}
        i = 1
        for operation in Senna.SUPPORTED_OPERATIONS:
            if operation in self.operations:
                _map[operation] = i
                i += 1
        return _map

    def tag(self, tokens):
        """
        Applies the specified operation(s) on a list of tokens.
        """
        return self.tag_sents([tokens])[0]

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return a
        list of dictionaries. Every dictionary will contain a word with its
        calculated annotations/tags.
        """
        encoding = self._encoding

        if not path.isfile(self.executable(self._path)):
            raise LookupError(
                "Senna executable expected at %s but not found"
                % self.executable(self._path)
            )

        # Build the senna command to run the tagger
        _senna_cmd = [
            self.executable(self._path),
            "-path",
            self._path,
            "-usrtokens",
            "-iobtags",
        ]
        _senna_cmd.extend(["-" + op for op in self.operations])

        # Serialize the actual sentences to a temporary string
        _input = "\n".join(" ".join(x) for x in sentences) + "\n"
        if isinstance(_input, str) and encoding:
            _input = _input.encode(encoding)

        # Run the tagger and get the output
        p = Popen(_senna_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate(input=_input)
        senna_output = stdout

        # Check the return code.
        if p.returncode != 0:
            raise RuntimeError("Senna command failed! Details: %s" % stderr)

        if encoding:
            senna_output = stdout.decode(encoding)

        # Output the tagged sentences
        map_ = self._map()
        tagged_sentences = [[]]
        sentence_index = 0
        token_index = 0
        for tagged_word in senna_output.strip().split("\n"):
            if not tagged_word:
                tagged_sentences.append([])
                sentence_index += 1
                token_index = 0
                continue
            tags = tagged_word.split("\t")
            result = {}
            for tag in map_:
                result[tag] = tags[map_[tag]].strip()
            try:
                result["word"] = sentences[sentence_index][token_index]
            except IndexError as e:
                raise IndexError(
                    "Misalignment error occurred at sentence number %d. Possible reason"
                    " is that the sentence size exceeded the maximum size. Check the "
                    "documentation of Senna class for more information."
                    % sentence_index
                ) from e
            tagged_sentences[-1].append(result)
            token_index += 1
        return tagged_sentences

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\beta.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from ..._compat import cached_property
from .chat.chat import Chat, AsyncChat
from .assistants import (
    Assistants,
    AsyncAssistants,
    AssistantsWithRawResponse,
    AsyncAssistantsWithRawResponse,
    AssistantsWithStreamingResponse,
    AsyncAssistantsWithStreamingResponse,
)
from ..._resource import SyncAPIResource, AsyncAPIResource
from .threads.threads import (
    Threads,
    AsyncThreads,
    ThreadsWithRawResponse,
    AsyncThreadsWithRawResponse,
    ThreadsWithStreamingResponse,
    AsyncThreadsWithStreamingResponse,
)
from .realtime.realtime import (
    Realtime,
    AsyncRealtime,
    RealtimeWithRawResponse,
    AsyncRealtimeWithRawResponse,
    RealtimeWithStreamingResponse,
    AsyncRealtimeWithStreamingResponse,
)

__all__ = ["Beta", "AsyncBeta"]


class Beta(SyncAPIResource):
    @cached_property
    def chat(self) -> Chat:
        return Chat(self._client)

    @cached_property
    def realtime(self) -> Realtime:
        return Realtime(self._client)

    @cached_property
    def assistants(self) -> Assistants:
        return Assistants(self._client)

    @cached_property
    def threads(self) -> Threads:
        return Threads(self._client)

    @cached_property
    def with_raw_response(self) -> BetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return BetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return BetaWithStreamingResponse(self)


class AsyncBeta(AsyncAPIResource):
    @cached_property
    def chat(self) -> AsyncChat:
        return AsyncChat(self._client)

    @cached_property
    def realtime(self) -> AsyncRealtime:
        return AsyncRealtime(self._client)

    @cached_property
    def assistants(self) -> AsyncAssistants:
        return AsyncAssistants(self._client)

    @cached_property
    def threads(self) -> AsyncThreads:
        return AsyncThreads(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncBetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncBetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncBetaWithStreamingResponse(self)


class BetaWithRawResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def realtime(self) -> RealtimeWithRawResponse:
        return RealtimeWithRawResponse(self._beta.realtime)

    @cached_property
    def assistants(self) -> AssistantsWithRawResponse:
        return AssistantsWithRawResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> ThreadsWithRawResponse:
        return ThreadsWithRawResponse(self._beta.threads)


class AsyncBetaWithRawResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def realtime(self) -> AsyncRealtimeWithRawResponse:
        return AsyncRealtimeWithRawResponse(self._beta.realtime)

    @cached_property
    def assistants(self) -> AsyncAssistantsWithRawResponse:
        return AsyncAssistantsWithRawResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> AsyncThreadsWithRawResponse:
        return AsyncThreadsWithRawResponse(self._beta.threads)


class BetaWithStreamingResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def realtime(self) -> RealtimeWithStreamingResponse:
        return RealtimeWithStreamingResponse(self._beta.realtime)

    @cached_property
    def assistants(self) -> AssistantsWithStreamingResponse:
        return AssistantsWithStreamingResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> ThreadsWithStreamingResponse:
        return ThreadsWithStreamingResponse(self._beta.threads)


class AsyncBetaWithStreamingResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def realtime(self) -> AsyncRealtimeWithStreamingResponse:
        return AsyncRealtimeWithStreamingResponse(self._beta.realtime)

    @cached_property
    def assistants(self) -> AsyncAssistantsWithStreamingResponse:
        return AsyncAssistantsWithStreamingResponse(self._beta.assistants)

    @cached_property
    def threads(self) -> AsyncThreadsWithStreamingResponse:
        return AsyncThreadsWithStreamingResponse(self._beta.threads)

# === NexusCore/openenv\Lib\site-packages\openai\types\fine_tuning\job_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypedDict

from .dpo_method_param import DpoMethodParam
from ..shared_params.metadata import Metadata
from .supervised_method_param import SupervisedMethodParam
from .reinforcement_method_param import ReinforcementMethodParam

__all__ = ["JobCreateParams", "Hyperparameters", "Integration", "IntegrationWandb", "Method"]


class JobCreateParams(TypedDict, total=False):
    model: Required[Union[str, Literal["babbage-002", "davinci-002", "gpt-3.5-turbo", "gpt-4o-mini"]]]
    """The name of the model to fine-tune.

    You can select one of the
    [supported models](https://platform.openai.com/docs/guides/fine-tuning#which-models-can-be-fine-tuned).
    """

    training_file: Required[str]
    """The ID of an uploaded file that contains training data.

    See [upload file](https://platform.openai.com/docs/api-reference/files/create)
    for how to upload a file.

    Your dataset must be formatted as a JSONL file. Additionally, you must upload
    your file with the purpose `fine-tune`.

    The contents of the file should differ depending on if the model uses the
    [chat](https://platform.openai.com/docs/api-reference/fine-tuning/chat-input),
    [completions](https://platform.openai.com/docs/api-reference/fine-tuning/completions-input)
    format, or if the fine-tuning method uses the
    [preference](https://platform.openai.com/docs/api-reference/fine-tuning/preference-input)
    format.

    See the
    [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
    for more details.
    """

    hyperparameters: Hyperparameters
    """
    The hyperparameters used for the fine-tuning job. This value is now deprecated
    in favor of `method`, and should be passed in under the `method` parameter.
    """

    integrations: Optional[Iterable[Integration]]
    """A list of integrations to enable for your fine-tuning job."""

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    method: Method
    """The method used for fine-tuning."""

    seed: Optional[int]
    """The seed controls the reproducibility of the job.

    Passing in the same seed and job parameters should produce the same results, but
    may differ in rare cases. If a seed is not specified, one will be generated for
    you.
    """

    suffix: Optional[str]
    """
    A string of up to 64 characters that will be added to your fine-tuned model
    name.

    For example, a `suffix` of "custom-model-name" would produce a model name like
    `ft:gpt-4o-mini:openai:custom-model-name:7p4lURel`.
    """

    validation_file: Optional[str]
    """The ID of an uploaded file that contains validation data.

    If you provide this file, the data is used to generate validation metrics
    periodically during fine-tuning. These metrics can be viewed in the fine-tuning
    results file. The same data should not be present in both train and validation
    files.

    Your dataset must be formatted as a JSONL file. You must upload your file with
    the purpose `fine-tune`.

    See the
    [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
    for more details.
    """


class Hyperparameters(TypedDict, total=False):
    batch_size: Union[Literal["auto"], int]
    """Number of examples in each batch.

    A larger batch size means that model parameters are updated less frequently, but
    with lower variance.
    """

    learning_rate_multiplier: Union[Literal["auto"], float]
    """Scaling factor for the learning rate.

    A smaller learning rate may be useful to avoid overfitting.
    """

    n_epochs: Union[Literal["auto"], int]
    """The number of epochs to train the model for.

    An epoch refers to one full cycle through the training dataset.
    """


class IntegrationWandb(TypedDict, total=False):
    project: Required[str]
    """The name of the project that the new run will be created under."""

    entity: Optional[str]
    """The entity to use for the run.

    This allows you to set the team or username of the WandB user that you would
    like associated with the run. If not set, the default entity for the registered
    WandB API key is used.
    """

    name: Optional[str]
    """A display name to set for the run.

    If not set, we will use the Job ID as the name.
    """

    tags: List[str]
    """A list of tags to be attached to the newly created run.

    These tags are passed through directly to WandB. Some default tags are generated
    by OpenAI: "openai/finetune", "openai/{base-model}", "openai/{ftjob-abcdef}".
    """


class Integration(TypedDict, total=False):
    type: Required[Literal["wandb"]]
    """The type of integration to enable.

    Currently, only "wandb" (Weights and Biases) is supported.
    """

    wandb: Required[IntegrationWandb]
    """The settings for your integration with Weights and Biases.

    This payload specifies the project that metrics will be sent to. Optionally, you
    can set an explicit display name for your run, add tags to your run, and set a
    default entity (team, username, etc) to be associated with your run.
    """


class Method(TypedDict, total=False):
    type: Required[Literal["supervised", "dpo", "reinforcement"]]
    """The type of method. Is either `supervised`, `dpo`, or `reinforcement`."""

    dpo: DpoMethodParam
    """Configuration for the DPO fine-tuning method."""

    reinforcement: ReinforcementMethodParam
    """Configuration for the reinforcement fine-tuning method."""

    supervised: SupervisedMethodParam
    """Configuration for the supervised fine-tuning method."""

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\elpi.py ===
"""
    pygments.lexers.elpi
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for the `Elpi <http://github.com/LPCIC/elpi>`_ programming language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, include, using
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['ElpiLexer']

from pygments.lexers.theorem import CoqLexer

class ElpiLexer(RegexLexer):
    """
    Lexer for the Elpi programming language.
    """

    name = 'Elpi'
    url = 'http://github.com/LPCIC/elpi'
    aliases = ['elpi']
    filenames = ['*.elpi']
    mimetypes = ['text/x-elpi']
    version_added = '2.11'

    lcase_re = r"[a-z]"
    ucase_re = r"[A-Z]"
    digit_re = r"[0-9]"
    schar2_re = r"([+*^?/<>`'@#~=&!])"
    schar_re = rf"({schar2_re}|-|\$|_)"
    idchar_re = rf"({lcase_re}|{ucase_re}|{digit_re}|{schar_re})"
    idcharstarns_re = rf"({idchar_re}*(\.({lcase_re}|{ucase_re}){idchar_re}*)*)"
    symbchar_re = rf"({lcase_re}|{ucase_re}|{digit_re}|{schar_re}|:)"
    constant_re = rf"({ucase_re}{idchar_re}*|{lcase_re}{idcharstarns_re}|{schar2_re}{symbchar_re}*|_{idchar_re}+)"
    symbol_re = r"(,|<=>|->|:-|;|\?-|->|&|=>|\bas\b|\buvar\b|<|=<|=|==|>=|>|\bi<|\bi=<|\bi>=|\bi>|\bis\b|\br<|\br=<|\br>=|\br>|\bs<|\bs=<|\bs>=|\bs>|@|::|\[\]|`->|`:|`:=|\^|-|\+|\bi-|\bi\+|r-|r\+|/|\*|\bdiv\b|\bi\*|\bmod\b|\br\*|~|\bi~|\br~)"
    escape_re = rf"\(({constant_re}|{symbol_re})\)"
    const_sym_re = rf"({constant_re}|{symbol_re}|{escape_re})"

    tokens = {
        'root': [
            include('elpi')
        ],

        'elpi': [
            include('_elpi-comment'),

            (r"(:before|:after|:if|:name)(\s*)(\")",
             bygroups(Keyword.Mode, Text.Whitespace, String.Double),
             'elpi-string'),
            (r"(:index)(\s*)(\()", bygroups(Keyword.Mode, Text.Whitespace, Punctuation),
             'elpi-indexing-expr'),
            (rf"\b(external pred|pred)(\s+)({const_sym_re})",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-pred-item'),
            (rf"\b(external type|type)(\s+)(({const_sym_re}(,\s*)?)+)",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-type'),
            (rf"\b(kind)(\s+)(({const_sym_re}|,)+)",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-type'),
            (rf"\b(typeabbrev)(\s+)({const_sym_re})",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-type'),
            (r"\b(typeabbrev)(\s+)(\([^)]+\))",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-type'),
            (r"\b(accumulate)(\s+)(\")",
             bygroups(Keyword.Declaration, Text.Whitespace, String.Double),
             'elpi-string'),
            (rf"\b(accumulate|namespace|local)(\s+)({constant_re})",
             bygroups(Keyword.Declaration, Text.Whitespace, Text)),
            (rf"\b(shorten)(\s+)({constant_re}\.)",
             bygroups(Keyword.Declaration, Text.Whitespace, Text)),
            (r"\b(pi|sigma)(\s+)([a-zA-Z][A-Za-z0-9_ ]*)(\\)",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Variable, Text)),
            (rf"\b(constraint)(\s+)(({const_sym_re}(\s+)?)+)",
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Function),
             'elpi-chr-rule-start'),

            (rf"(?=[A-Z_]){constant_re}", Name.Variable),
            (rf"(?=[a-z_])({constant_re}|_)\\", Name.Variable),
            (r"_", Name.Variable),
            (rf"({symbol_re}|!|=>|;)", Keyword.Declaration),
            (constant_re, Text),
            (r"\[|\]|\||=>", Keyword.Declaration),
            (r'"', String.Double, 'elpi-string'),
            (r'`', String.Double, 'elpi-btick'),
            (r'\'', String.Double, 'elpi-tick'),
            (r'\{\{', Punctuation, 'elpi-quote'),
            (r'\{[^\{]', Text, 'elpi-spill'),
            (r"\(", Punctuation, 'elpi-in-parens'),
            (r'\d[\d_]*', Number.Integer),
            (r'-?\d[\d_]*(.[\d_]*)?([eE][+\-]?\d[\d_]*)', Number.Float),
            (r"[\+\*\-/\^\.]", Operator),
        ],
        '_elpi-comment': [
            (r'%[^\n]*\n', Comment),
            (r'/(?:\\\n)?[*](?:[^*]|[*](?!(?:\\\n)?/))*[*](?:\\\n)?/', Comment),
            (r"\s+", Text.Whitespace),
        ],
        'elpi-indexing-expr':[
            (r'[0-9 _]+', Number.Integer),
            (r'\)', Punctuation, '#pop'),
        ],
        'elpi-type': [
            (r"(ctype\s+)(\")", bygroups(Keyword.Type, String.Double), 'elpi-string'),
            (r'->', Keyword.Type),
            (constant_re, Keyword.Type),
            (r"\(|\)", Keyword.Type),
            (r"\.", Text, '#pop'),
            include('_elpi-comment'),
        ],
        'elpi-chr-rule-start': [
            (r"\{", Punctuation, 'elpi-chr-rule'),
            include('_elpi-comment'),
        ],
        'elpi-chr-rule': [
           (r"\brule\b", Keyword.Declaration),
           (r"\\", Keyword.Declaration),
           (r"\}", Punctuation, '#pop:2'),
           include('elpi'),
        ],
        'elpi-pred-item': [
            (r"[io]:", Keyword.Mode, 'elpi-ctype'),
            (r"\.", Text, '#pop'),
            include('_elpi-comment'),
        ],
        'elpi-ctype': [
            (r"(ctype\s+)(\")", bygroups(Keyword.Type, String.Double), 'elpi-string'),
            (r'->', Keyword.Type),
            (constant_re, Keyword.Type),
            (r"\(|\)", Keyword.Type),
            (r",", Text, '#pop'),
            (r"\.", Text, '#pop:2'),
            include('_elpi-comment'),
        ],
        'elpi-btick': [
            (r'[^` ]+', String.Double),
            (r'`', String.Double, '#pop'),
        ],
        'elpi-tick': [
            (r'[^\' ]+', String.Double),
            (r'\'', String.Double, '#pop'),
        ],
        'elpi-string': [
            (r'[^\"]+', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'elpi-quote': [
            (r'\}\}', Punctuation, '#pop'),
            (r"\s+", Text.Whitespace),
            (r"(lp:)(\{\{)", bygroups(Number, Punctuation), 'elpi-quote-exit'),
            (rf"(lp:)((?=[A-Z_]){constant_re})", bygroups(Number, Name.Variable)),
            (r"((?!lp:|\}\}).)+", using(CoqLexer)),
        ],
        'elpi-quote-exit': [
            include('elpi'),
            (r'\}\}', Punctuation, '#pop'),
        ],
        'elpi-spill': [
            (r'\{[^\{]', Text, '#push'),
            (r'\}[^\}]', Text, '#pop'),
            include('elpi'),
        ],
        'elpi-in-parens': [
            (r"\(", Punctuation, '#push'),
            include('elpi'),
            (r"\)", Punctuation, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\versionpredicate.py ===
"""Module for parsing and testing package version predicate strings."""

import operator
import re

from . import version

re_validPackage = re.compile(r"(?i)^\s*([a-z_]\w*(?:\.[a-z_]\w*)*)(.*)", re.ASCII)
# (package) (rest)

re_paren = re.compile(r"^\s*\((.*)\)\s*$")  # (list) inside of parentheses
re_splitComparison = re.compile(r"^\s*(<=|>=|<|>|!=|==)\s*([^\s,]+)\s*$")
# (comp) (version)


def splitUp(pred):
    """Parse a single version comparison.

    Return (comparison string, StrictVersion)
    """
    res = re_splitComparison.match(pred)
    if not res:
        raise ValueError(f"bad package restriction syntax: {pred!r}")
    comp, verStr = res.groups()
    with version.suppress_known_deprecation():
        other = version.StrictVersion(verStr)
    return (comp, other)


compmap = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
}


class VersionPredicate:
    """Parse and test package version predicates.

    >>> v = VersionPredicate('pyepat.abc (>1.0, <3333.3a1, !=1555.1b3)')

    The `name` attribute provides the full dotted name that is given::

    >>> v.name
    'pyepat.abc'

    The str() of a `VersionPredicate` provides a normalized
    human-readable version of the expression::

    >>> print(v)
    pyepat.abc (> 1.0, < 3333.3a1, != 1555.1b3)

    The `satisfied_by()` method can be used to determine with a given
    version number is included in the set described by the version
    restrictions::

    >>> v.satisfied_by('1.1')
    True
    >>> v.satisfied_by('1.4')
    True
    >>> v.satisfied_by('1.0')
    False
    >>> v.satisfied_by('4444.4')
    False
    >>> v.satisfied_by('1555.1b3')
    False

    `VersionPredicate` is flexible in accepting extra whitespace::

    >>> v = VersionPredicate(' pat( ==  0.1  )  ')
    >>> v.name
    'pat'
    >>> v.satisfied_by('0.1')
    True
    >>> v.satisfied_by('0.2')
    False

    If any version numbers passed in do not conform to the
    restrictions of `StrictVersion`, a `ValueError` is raised::

    >>> v = VersionPredicate('p1.p2.p3.p4(>=1.0, <=1.3a1, !=1.2zb3)')
    Traceback (most recent call last):
      ...
    ValueError: invalid version number '1.2zb3'

    It the module or package name given does not conform to what's
    allowed as a legal module or package name, `ValueError` is
    raised::

    >>> v = VersionPredicate('foo-bar')
    Traceback (most recent call last):
      ...
    ValueError: expected parenthesized list: '-bar'

    >>> v = VersionPredicate('foo bar (12.21)')
    Traceback (most recent call last):
      ...
    ValueError: expected parenthesized list: 'bar (12.21)'

    """

    def __init__(self, versionPredicateStr):
        """Parse a version predicate string."""
        # Fields:
        #    name:  package name
        #    pred:  list of (comparison string, StrictVersion)

        versionPredicateStr = versionPredicateStr.strip()
        if not versionPredicateStr:
            raise ValueError("empty package restriction")
        match = re_validPackage.match(versionPredicateStr)
        if not match:
            raise ValueError(f"bad package name in {versionPredicateStr!r}")
        self.name, paren = match.groups()
        paren = paren.strip()
        if paren:
            match = re_paren.match(paren)
            if not match:
                raise ValueError(f"expected parenthesized list: {paren!r}")
            str = match.groups()[0]
            self.pred = [splitUp(aPred) for aPred in str.split(",")]
            if not self.pred:
                raise ValueError(f"empty parenthesized list in {versionPredicateStr!r}")
        else:
            self.pred = []

    def __str__(self):
        if self.pred:
            seq = [cond + " " + str(ver) for cond, ver in self.pred]
            return self.name + " (" + ", ".join(seq) + ")"
        else:
            return self.name

    def satisfied_by(self, version):
        """True if version is compatible with all the predicates in self.
        The parameter version must be acceptable to the StrictVersion
        constructor.  It may be either a string or StrictVersion.
        """
        for cond, ver in self.pred:
            if not compmap[cond](version, ver):
                return False
        return True


_provision_rx = None


def split_provision(value):
    """Return the name and optional version number of a provision.

    The version number, if given, will be returned as a `StrictVersion`
    instance, otherwise it will be `None`.

    >>> split_provision('mypkg')
    ('mypkg', None)
    >>> split_provision(' mypkg( 1.2 ) ')
    ('mypkg', StrictVersion ('1.2'))
    """
    global _provision_rx
    if _provision_rx is None:
        _provision_rx = re.compile(
            r"([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)(?:\s*\(\s*([^)\s]+)\s*\))?$", re.ASCII
        )
    value = value.strip()
    m = _provision_rx.match(value)
    if not m:
        raise ValueError(f"illegal provides specification: {value!r}")
    ver = m.group(2) or None
    if ver:
        with version.suppress_known_deprecation():
            ver = version.StrictVersion(ver)
    return m.group(1), ver

# === NexusCore/openenv\Lib\site-packages\win32\test\handles.py ===
import sys
import unittest

import pywintypes
import win32api


class TestError1(Exception):
    pass


class TestError2(Exception):
    pass


# A class that will never die vie refcounting, but will die via GC.
class Cycle:
    def __init__(self, handle):
        self.cycle = self
        self.handle = handle


class PyHandleTestCase(unittest.TestCase):
    def testCleanup1(self):
        # We used to clobber all outstanding exceptions.
        def f1(invalidate):
            import win32event

            h = win32event.CreateEvent(None, 0, 0, None)
            if invalidate:
                win32api.CloseHandle(int(h))
            raise TestError1
            # If we invalidated, then the object destruction code will attempt
            # to close an invalid handle.  We don't wan't an exception in
            # this case

        def f2(invalidate):
            """This function should throw an OSError."""
            try:
                f1(invalidate)
            except TestError1:
                raise TestError2

        self.assertRaises(TestError2, f2, False)
        # Now do it again, but so the auto object destruction
        # actually fails.
        self.assertRaises(TestError2, f2, True)

    def testCleanup2(self):
        # Cause an exception during object destruction.
        # The worst this does is cause an ".XXX undetected error (why=3)"
        # So avoiding that is the goal
        import win32event

        h = win32event.CreateEvent(None, 0, 0, None)
        # Close the handle underneath the object.
        win32api.CloseHandle(int(h))
        # Object destructor runs with the implicit close failing
        h = None

    def testCleanup3(self):
        # And again with a class - no __del__
        import win32event

        class Test:
            def __init__(self):
                self.h = win32event.CreateEvent(None, 0, 0, None)
                win32api.CloseHandle(int(self.h))

        t = Test()
        t = None

    def testCleanupGood(self):
        # And check that normal error semantics *do* work.
        import win32event

        h = win32event.CreateEvent(None, 0, 0, None)
        win32api.CloseHandle(int(h))
        self.assertRaises(win32api.error, h.Close)
        # A following Close is documented as working
        h.Close()

    def testInvalid(self):
        h = pywintypes.HANDLE(-2)
        try:
            h.Close()
            # Ideally, we'd:
            #     self.assertRaises(win32api.error, h.Close)
            # and everywhere markh has tried, that would pass - but not on
            # github automation, where the .Close apparently works fine.
            # (same for -1. Using 0 appears to work fine everywhere)
            # There still seems value in testing it though, so we just accept
            # either working or failing.
        except win32api.error:
            pass

    def testOtherHandle(self):
        h = pywintypes.HANDLE(1)
        h2 = pywintypes.HANDLE(h)
        self.assertEqual(h, h2)
        # but the above doesn't really test everything - we want a way to
        # pass the handle directly into PyWinLong_AsVoidPtr.  One way to
        # to that is to abuse win32api.GetProcAddress() - the 2nd param
        # is passed to PyWinLong_AsVoidPtr() if it's not a string.
        # passing a handle value of '1' should work - there is something
        # at that ordinal
        win32api.GetProcAddress(sys.dllhandle, h)

    def testHandleInDict(self):
        h = pywintypes.HANDLE(1)
        d = {"foo": h}
        self.assertEqual(d["foo"], h)

    def testHandleInDictThenInt(self):
        h = pywintypes.HANDLE(1)
        d = {"foo": h}
        self.assertEqual(d["foo"], 1)

    def testHandleCompareNone(self):
        h = pywintypes.HANDLE(1)
        self.assertNotEqual(h, None)
        self.assertNotEqual(None, h)
        # ensure we use both __eq__ and __ne__ ops
        self.assertFalse(h is None)
        self.assertTrue(h is not None)

    def testHandleCompareInt(self):
        h = pywintypes.HANDLE(1)
        self.assertNotEqual(h, 0)
        self.assertEqual(h, 1)
        # ensure we use both __eq__ and __ne__ ops
        self.assertTrue(h == 1)
        self.assertTrue(1 == h)
        self.assertFalse(h != 1)
        self.assertFalse(1 != h)
        self.assertFalse(h == 0)
        self.assertFalse(0 == h)
        self.assertTrue(h != 0)
        self.assertTrue(0 != h)

    def testHandleNonZero(self):
        h = pywintypes.HANDLE(0)
        self.assertFalse(h)

        h = pywintypes.HANDLE(1)
        self.assertTrue(h)

    def testLong(self):
        # sys.maxsize+1 should always be a 'valid' handle, treated as an
        # unsigned int, even though it is a long. Although pywin32 should not
        # directly create such longs, using struct.unpack() with a P format
        # may well return them. eg:
        # >>> struct.unpack("P", struct.pack("P", -1))
        # (4294967295L,)
        pywintypes.HANDLE(sys.maxsize + 1)

    def testGC(self):
        # This used to provoke:
        # Fatal Python error: unexpected exception during garbage collection
        def make():
            h = pywintypes.HANDLE(-2)
            c = Cycle(h)

        import gc

        make()
        gc.collect()

    def testTypes(self):
        self.assertRaises(TypeError, pywintypes.HANDLE, "foo")
        self.assertRaises(TypeError, pywintypes.HANDLE, ())


if __name__ == "__main__":
    unittest.main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\found_candidates.py ===
"""Utilities to lazily create and visit candidates found.

Creating and visiting a candidate is a *very* costly operation. It involves
fetching, extracting, potentially building modules from source, and verifying
distribution metadata. It is therefore crucial for performance to keep
everything here lazy all the way down, so we only touch candidates that we
absolutely need, and not "download the world" when we only need one version of
something.
"""

import functools
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Set, Tuple

from pip._vendor.packaging.version import _BaseVersion

from pip._internal.exceptions import MetadataInvalid

from .base import Candidate

logger = logging.getLogger(__name__)

IndexCandidateInfo = Tuple[_BaseVersion, Callable[[], Optional[Candidate]]]

if TYPE_CHECKING:
    SequenceCandidate = Sequence[Candidate]
else:
    # For compatibility: Python before 3.9 does not support using [] on the
    # Sequence class.
    #
    # >>> from collections.abc import Sequence
    # >>> Sequence[str]
    # Traceback (most recent call last):
    #   File "<stdin>", line 1, in <module>
    # TypeError: 'ABCMeta' object is not subscriptable
    #
    # TODO: Remove this block after dropping Python 3.8 support.
    SequenceCandidate = Sequence


def _iter_built(infos: Iterator[IndexCandidateInfo]) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the package is not already installed. Candidates
    from index come later in their normal ordering.
    """
    versions_found: Set[_BaseVersion] = set()
    for version, func in infos:
        if version in versions_found:
            continue
        try:
            candidate = func()
        except MetadataInvalid as e:
            logger.warning(
                "Ignoring version %s of %s since it has invalid metadata:\n"
                "%s\n"
                "Please use pip<24.1 if you need to use this version.",
                version,
                e.ireq.name,
                e,
            )
            # Mark version as found to avoid trying other candidates with the same
            # version, since they most likely have invalid metadata as well.
            versions_found.add(version)
        else:
            if candidate is None:
                continue
            yield candidate
            versions_found.add(version)


def _iter_built_with_prepended(
    installed: Candidate, infos: Iterator[IndexCandidateInfo]
) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers the already-installed
    candidate and NOT to upgrade. The installed candidate is therefore
    always yielded first, and candidates from index come later in their
    normal ordering, except skipped when the version is already installed.
    """
    yield installed
    versions_found: Set[_BaseVersion] = {installed.version}
    for version, func in infos:
        if version in versions_found:
            continue
        candidate = func()
        if candidate is None:
            continue
        yield candidate
        versions_found.add(version)


def _iter_built_with_inserted(
    installed: Candidate, infos: Iterator[IndexCandidateInfo]
) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers to upgrade an
    already-installed package. Candidates from index are returned in their
    normal ordering, except replaced when the version is already installed.

    The implementation iterates through and yields other candidates, inserting
    the installed candidate exactly once before we start yielding older or
    equivalent candidates, or after all other candidates if they are all newer.
    """
    versions_found: Set[_BaseVersion] = set()
    for version, func in infos:
        if version in versions_found:
            continue
        # If the installed candidate is better, yield it first.
        if installed.version >= version:
            yield installed
            versions_found.add(installed.version)
        candidate = func()
        if candidate is None:
            continue
        yield candidate
        versions_found.add(version)

    # If the installed candidate is older than all other candidates.
    if installed.version not in versions_found:
        yield installed


class FoundCandidates(SequenceCandidate):
    """A lazy sequence to provide candidates to the resolver.

    The intended usage is to return this from `find_matches()` so the resolver
    can iterate through the sequence multiple times, but only access the index
    page when remote packages are actually needed. This improve performances
    when suitable candidates are already installed on disk.
    """

    def __init__(
        self,
        get_infos: Callable[[], Iterator[IndexCandidateInfo]],
        installed: Optional[Candidate],
        prefers_installed: bool,
        incompatible_ids: Set[int],
    ):
        self._get_infos = get_infos
        self._installed = installed
        self._prefers_installed = prefers_installed
        self._incompatible_ids = incompatible_ids

    def __getitem__(self, index: Any) -> Any:
        # Implemented to satisfy the ABC check. This is not needed by the
        # resolver, and should not be used by the provider either (for
        # performance reasons).
        raise NotImplementedError("don't do this")

    def __iter__(self) -> Iterator[Candidate]:
        infos = self._get_infos()
        if not self._installed:
            iterator = _iter_built(infos)
        elif self._prefers_installed:
            iterator = _iter_built_with_prepended(self._installed, infos)
        else:
            iterator = _iter_built_with_inserted(self._installed, infos)
        return (c for c in iterator if id(c) not in self._incompatible_ids)

    def __len__(self) -> int:
        # Implemented to satisfy the ABC check. This is not needed by the
        # resolver, and should not be used by the provider either (for
        # performance reasons).
        raise NotImplementedError("don't do this")

    @functools.lru_cache(maxsize=1)
    def __bool__(self) -> bool:
        if self._prefers_installed and self._installed:
            return True
        return any(self)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\cells.py ===
from __future__ import annotations

from functools import lru_cache
from typing import Callable

from ._cell_widths import CELL_WIDTHS

# Ranges of unicode ordinals that produce a 1-cell wide character
# This is non-exhaustive, but covers most common Western characters
_SINGLE_CELL_UNICODE_RANGES: list[tuple[int, int]] = [
    (0x20, 0x7E),  # Latin (excluding non-printable)
    (0xA0, 0xAC),
    (0xAE, 0x002FF),
    (0x00370, 0x00482),  # Greek / Cyrillic
    (0x02500, 0x025FC),  # Box drawing, box elements, geometric shapes
    (0x02800, 0x028FF),  # Braille
]

# A set of characters that are a single cell wide
_SINGLE_CELLS = frozenset(
    [
        character
        for _start, _end in _SINGLE_CELL_UNICODE_RANGES
        for character in map(chr, range(_start, _end + 1))
    ]
)

# When called with a string this will return True if all
# characters are single-cell, otherwise False
_is_single_cell_widths: Callable[[str], bool] = _SINGLE_CELLS.issuperset


@lru_cache(4096)
def cached_cell_len(text: str) -> int:
    """Get the number of cells required to display text.

    This method always caches, which may use up a lot of memory. It is recommended to use
    `cell_len` over this method.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


def cell_len(text: str, _cell_len: Callable[[str], int] = cached_cell_len) -> int:
    """Get the number of cells required to display text.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if len(text) < 512:
        return _cell_len(text)
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


@lru_cache(maxsize=4096)
def get_character_cell_size(character: str) -> int:
    """Get the cell size of a character.

    Args:
        character (str): A single character.

    Returns:
        int: Number of cells (0, 1 or 2) occupied by that character.
    """
    codepoint = ord(character)
    _table = CELL_WIDTHS
    lower_bound = 0
    upper_bound = len(_table) - 1
    index = (lower_bound + upper_bound) // 2
    while True:
        start, end, width = _table[index]
        if codepoint < start:
            upper_bound = index - 1
        elif codepoint > end:
            lower_bound = index + 1
        else:
            return 0 if width == -1 else width
        if upper_bound < lower_bound:
            break
        index = (lower_bound + upper_bound) // 2
    return 1


def set_cell_size(text: str, total: int) -> str:
    """Set the length of a string to fit within given number of cells."""

    if _is_single_cell_widths(text):
        size = len(text)
        if size < total:
            return text + " " * (total - size)
        return text[:total]

    if total <= 0:
        return ""
    cell_size = cell_len(text)
    if cell_size == total:
        return text
    if cell_size < total:
        return text + " " * (total - cell_size)

    start = 0
    end = len(text)

    # Binary search until we find the right size
    while True:
        pos = (start + end) // 2
        before = text[: pos + 1]
        before_len = cell_len(before)
        if before_len == total + 1 and cell_len(before[-1]) == 2:
            return before[:-1] + " "
        if before_len == total:
            return before
        if before_len > total:
            end = pos
        else:
            start = pos


def chop_cells(
    text: str,
    width: int,
) -> list[str]:
    """Split text into lines such that each line fits within the available (cell) width.

    Args:
        text: The text to fold such that it fits in the given width.
        width: The width available (number of cells).

    Returns:
        A list of strings such that each string in the list has cell width
        less than or equal to the available width.
    """
    _get_character_cell_size = get_character_cell_size
    lines: list[list[str]] = [[]]

    append_new_line = lines.append
    append_to_last_line = lines[-1].append

    total_width = 0

    for character in text:
        cell_width = _get_character_cell_size(character)
        char_doesnt_fit = total_width + cell_width > width

        if char_doesnt_fit:
            append_new_line([character])
            append_to_last_line = lines[-1].append
            total_width = cell_width
        else:
            append_to_last_line(character)
            total_width += cell_width

    return ["".join(line) for line in lines]


if __name__ == "__main__":  # pragma: no cover
    print(get_character_cell_size("😽"))
    for line in chop_cells("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", 8):
        print(line)
    for n in range(80, 1, -1):
        print(set_cell_size("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", n) + "|")
        print("x" * n)