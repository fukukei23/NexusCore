
# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_ipython_console_011.py ===
# TODO that would make IPython integration better
# - show output other times then when enter was pressed
# - support proper exit to allow IPython to cleanup (e.g. temp files created with %edit)
# - support Ctrl-D (Ctrl-Z on Windows)
# - use IPython (numbered) prompts in PyDev
# - better integration of IPython and PyDev completions
# - some of the semantics on handling the code completion are not correct:
#   eg: Start a line with % and then type c should give %cd as a completion by it doesn't
#       however type %c and request completions and %cd is given as an option
#   eg: Completing a magic when user typed it without the leading % causes the % to be inserted
#       to the left of what should be the first colon.
"""Interface to TerminalInteractiveShell for PyDev Interactive Console frontend
   for IPython 0.11 to 1.0+.
"""

from __future__ import print_function

import os
import sys
import codeop
import traceback

from IPython.core.error import UsageError
from IPython.core.completer import IPCompleter
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.core.usage import default_banner_parts
from IPython.utils.strdispatch import StrDispatch
import IPython.core.release as IPythonRelease
from IPython.terminal.interactiveshell import TerminalInteractiveShell

try:
    from traitlets import CBool, Unicode
except ImportError:
    from IPython.utils.traitlets import CBool, Unicode
from IPython.core import release

from _pydev_bundle.pydev_imports import xmlrpclib

default_pydev_banner_parts = default_banner_parts

default_pydev_banner = "".join(default_pydev_banner_parts)


def show_in_pager(self, strng, *args, **kwargs):
    """Run a string through pager"""
    # On PyDev we just output the string, there are scroll bars in the console
    # to handle "paging". This is the same behaviour as when TERM==dump (see
    # page.py)
    # for compatibility with mime-bundle form:
    if isinstance(strng, dict):
        strng = strng.get("text/plain", strng)
    print(strng)


def create_editor_hook(pydev_host, pydev_client_port):
    def call_editor(filename, line=0, wait=True):
        """Open an editor in PyDev"""
        if line is None:
            line = 0

        # Make sure to send an absolution path because unlike most editor hooks
        # we don't launch a process. This is more like what happens in the zmqshell
        filename = os.path.abspath(filename)

        # import sys
        # sys.__stderr__.write('Calling editor at: %s:%s\n' % (pydev_host, pydev_client_port))

        # Tell PyDev to open the editor
        server = xmlrpclib.Server("http://%s:%s" % (pydev_host, pydev_client_port))
        server.IPythonEditor(filename, str(line))

        if wait:
            input("Press Enter when done editing:")

    return call_editor


class PyDevIPCompleter(IPCompleter):
    def __init__(self, *args, **kwargs):
        """Create a Completer that reuses the advanced completion support of PyDev
        in addition to the completion support provided by IPython"""
        IPCompleter.__init__(self, *args, **kwargs)
        # Use PyDev for python matches, see getCompletions below
        if self.python_matches in self.matchers:
            # `self.python_matches` matches attributes or global python names
            self.matchers.remove(self.python_matches)


class PyDevIPCompleter6(IPCompleter):
    def __init__(self, *args, **kwargs):
        """Create a Completer that reuses the advanced completion support of PyDev
        in addition to the completion support provided by IPython"""
        IPCompleter.__init__(self, *args, **kwargs)

    @property
    def matchers(self):
        """All active matcher routines for completion"""
        # To remove python_matches we now have to override it as it's now a property in the superclass.
        return [
            self.file_matches,
            self.magic_matches,
            self.python_func_kw_matches,
            self.dict_key_matches,
        ]

    @matchers.setter
    def matchers(self, value):
        # To stop the init in IPCompleter raising an AttributeError we now have to specify a setter as it's now a property in the superclass.
        return


class PyDevTerminalInteractiveShell(TerminalInteractiveShell):
    banner1 = Unicode(default_pydev_banner, config=True, help="""The part of the banner to be printed before the profile""")

    # TODO term_title: (can PyDev's title be changed???, see terminal.py for where to inject code, in particular set_term_title as used by %cd)
    # for now, just disable term_title
    term_title = CBool(False)

    # Note in version 0.11 there is no guard in the IPython code about displaying a
    # warning, so with 0.11 you get:
    #  WARNING: Readline services not available or not loaded.
    #  WARNING: The auto-indent feature requires the readline library
    # Disable readline, readline type code is all handled by PyDev (on Java side)
    readline_use = CBool(False)
    # autoindent has no meaning in PyDev (PyDev always handles that on the Java side),
    # and attempting to enable it will print a warning in the absence of readline.
    autoindent = CBool(False)
    # Force console to not give warning about color scheme choice and default to NoColor.
    # TODO It would be nice to enable colors in PyDev but:
    # - The PyDev Console (Eclipse Console) does not support the full range of colors, so the
    #   effect isn't as nice anyway at the command line
    # - If done, the color scheme should default to LightBG, but actually be dependent on
    #   any settings the user has (such as if a dark theme is in use, then Linux is probably
    #   a better theme).
    colors_force = CBool(True)
    colors = Unicode("NoColor")
    # Since IPython 5 the terminal interface is not compatible with Emacs `inferior-shell` and
    # the `simple_prompt` flag is needed
    simple_prompt = CBool(True)

    # In the PyDev Console, GUI control is done via hookable XML-RPC server
    @staticmethod
    def enable_gui(gui=None, app=None):
        """Switch amongst GUI input hooks by name."""
        # Deferred import
        from pydev_ipython.inputhook import enable_gui as real_enable_gui

        try:
            return real_enable_gui(gui, app)
        except ValueError as e:
            raise UsageError("%s" % e)

    # -------------------------------------------------------------------------
    # Things related to hooks
    # -------------------------------------------------------------------------

    def init_history(self):
        # Disable history so that we don't have an additional thread for that
        # (and we don't use the history anyways).
        self.config.HistoryManager.enabled = False
        super(PyDevTerminalInteractiveShell, self).init_history()

    def init_hooks(self):
        super(PyDevTerminalInteractiveShell, self).init_hooks()
        self.set_hook("show_in_pager", show_in_pager)

    # -------------------------------------------------------------------------
    # Things related to exceptions
    # -------------------------------------------------------------------------

    def showtraceback(self, exc_tuple=None, *args, **kwargs):
        # IPython does a lot of clever stuff with Exceptions. However mostly
        # it is related to IPython running in a terminal instead of an IDE.
        # (e.g. it prints out snippets of code around the stack trace)
        # PyDev does a lot of clever stuff too, so leave exception handling
        # with default print_exc that PyDev can parse and do its clever stuff
        # with (e.g. it puts links back to the original source code)
        try:
            if exc_tuple is None:
                etype, value, tb = sys.exc_info()
            else:
                etype, value, tb = exc_tuple
        except ValueError:
            return

        if tb is not None:
            traceback.print_exception(etype, value, tb)

    # -------------------------------------------------------------------------
    # Things related to text completion
    # -------------------------------------------------------------------------

    # The way to construct an IPCompleter changed in most versions,
    # so we have a custom, per version implementation of the construction

    def _new_completer_100(self):
        completer = PyDevIPCompleter(
            shell=self,
            namespace=self.user_ns,
            global_namespace=self.user_global_ns,
            alias_table=self.alias_manager.alias_table,
            use_readline=self.has_readline,
            parent=self,
        )
        return completer

    def _new_completer_234(self):
        # correct for IPython versions 2.x, 3.x, 4.x
        completer = PyDevIPCompleter(
            shell=self,
            namespace=self.user_ns,
            global_namespace=self.user_global_ns,
            use_readline=self.has_readline,
            parent=self,
        )
        return completer

    def _new_completer_500(self):
        completer = PyDevIPCompleter(
            shell=self, namespace=self.user_ns, global_namespace=self.user_global_ns, use_readline=False, parent=self
        )
        return completer

    def _new_completer_600(self):
        completer = PyDevIPCompleter6(
            shell=self, namespace=self.user_ns, global_namespace=self.user_global_ns, use_readline=False, parent=self
        )
        return completer

    def add_completer_hooks(self):
        from IPython.core.completerlib import module_completer, magic_run_completer, cd_completer

        try:
            from IPython.core.completerlib import reset_completer
        except ImportError:
            # reset_completer was added for rel-0.13
            reset_completer = None
        self.configurables.append(self.Completer)

        # Add custom completers to the basic ones built into IPCompleter
        sdisp = self.strdispatchers.get("complete_command", StrDispatch())
        self.strdispatchers["complete_command"] = sdisp
        self.Completer.custom_completers = sdisp

        self.set_hook("complete_command", module_completer, str_key="import")
        self.set_hook("complete_command", module_completer, str_key="from")
        self.set_hook("complete_command", magic_run_completer, str_key="%run")
        self.set_hook("complete_command", cd_completer, str_key="%cd")
        if reset_completer:
            self.set_hook("complete_command", reset_completer, str_key="%reset")

    def init_completer(self):
        """Initialize the completion machinery.

        This creates a completer that provides the completions that are
        IPython specific. We use this to supplement PyDev's core code
        completions.
        """
        # PyDev uses its own completer and custom hooks so that it uses
        # most completions from PyDev's core completer which provides
        # extra information.
        # See getCompletions for where the two sets of results are merged

        if IPythonRelease._version_major >= 6:
            self.Completer = self._new_completer_600()
        elif IPythonRelease._version_major >= 5:
            self.Completer = self._new_completer_500()
        elif IPythonRelease._version_major >= 2:
            self.Completer = self._new_completer_234()
        elif IPythonRelease._version_major >= 1:
            self.Completer = self._new_completer_100()

        if hasattr(self.Completer, "use_jedi"):
            self.Completer.use_jedi = False

        self.add_completer_hooks()

        if IPythonRelease._version_major <= 3:
            # Only configure readline if we truly are using readline.  IPython can
            # do tab-completion over the network, in GUIs, etc, where readline
            # itself may be absent
            if self.has_readline:
                self.set_readline_completer()

    # -------------------------------------------------------------------------
    # Things related to aliases
    # -------------------------------------------------------------------------

    def init_alias(self):
        # InteractiveShell defines alias's we want, but TerminalInteractiveShell defines
        # ones we don't. So don't use super and instead go right to InteractiveShell
        InteractiveShell.init_alias(self)

    # -------------------------------------------------------------------------
    # Things related to exiting
    # -------------------------------------------------------------------------
    def ask_exit(self):
        """Ask the shell to exit. Can be overiden and used as a callback."""
        # TODO PyDev's console does not have support from the Python side to exit
        # the console. If user forces the exit (with sys.exit()) then the console
        # simply reports errors. e.g.:
        # >>> import sys
        # >>> sys.exit()
        # Failed to create input stream: Connection refused
        # >>>
        # Console already exited with value: 0 while waiting for an answer.
        # Error stream:
        # Output stream:
        # >>>
        #
        # Alternatively if you use the non-IPython shell this is what happens
        # >>> exit()
        # <type 'exceptions.SystemExit'>:None
        # >>>
        # <type 'exceptions.SystemExit'>:None
        # >>>
        #
        super(PyDevTerminalInteractiveShell, self).ask_exit()
        print("To exit the PyDev Console, terminate the console within IDE.")

    # -------------------------------------------------------------------------
    # Things related to magics
    # -------------------------------------------------------------------------

    def init_magics(self):
        super(PyDevTerminalInteractiveShell, self).init_magics()
        # TODO Any additional magics for PyDev?


InteractiveShellABC.register(PyDevTerminalInteractiveShell)  # @UndefinedVariable


# =======================================================================================================================
# _PyDevFrontEnd
# =======================================================================================================================
class _PyDevFrontEnd:
    version = release.__version__

    def __init__(self):
        # Create and initialize our IPython instance.
        if hasattr(PyDevTerminalInteractiveShell, "_instance") and PyDevTerminalInteractiveShell._instance is not None:
            self.ipython = PyDevTerminalInteractiveShell._instance
        else:
            self.ipython = PyDevTerminalInteractiveShell.instance()

        self._curr_exec_line = 0
        self._curr_exec_lines = []

    def show_banner(self):
        self.ipython.show_banner()

    def update(self, globals, locals):
        ns = self.ipython.user_ns

        for key, value in list(ns.items()):
            if key not in locals:
                locals[key] = value

        self.ipython.user_global_ns.clear()
        self.ipython.user_global_ns.update(globals)
        self.ipython.user_ns = locals

        if hasattr(self.ipython, "history_manager") and hasattr(self.ipython.history_manager, "save_thread"):
            self.ipython.history_manager.save_thread.pydev_do_not_trace = True  # don't trace ipython history saving thread

    def complete(self, string):
        try:
            if string:
                return self.ipython.complete(None, line=string, cursor_pos=string.__len__())
            else:
                return self.ipython.complete(string, string, 0)
        except:
            # Silence completer exceptions
            pass

    def is_complete(self, string):
        # Based on IPython 0.10.1

        if string in ("", "\n"):
            # Prefiltering, eg through ipython0, may return an empty
            # string although some operations have been accomplished. We
            # thus want to consider an empty string as a complete
            # statement.
            return True
        else:
            try:
                # Add line returns here, to make sure that the statement is
                # complete (except if '\' was used).
                # This should probably be done in a different place (like
                # maybe 'prefilter_input' method? For now, this works.
                clean_string = string.rstrip("\n")
                if not clean_string.endswith("\\"):
                    clean_string += "\n\n"

                is_complete = codeop.compile_command(clean_string, "<string>", "exec")
            except Exception:
                # XXX: Hack: return True so that the
                # code gets executed and the error captured.
                is_complete = True
            return is_complete

    def getCompletions(self, text, act_tok):
        # Get completions from IPython and from PyDev and merge the results
        # IPython only gives context free list of completions, while PyDev
        # gives detailed information about completions.
        try:
            TYPE_IPYTHON = "11"
            TYPE_IPYTHON_MAGIC = "12"
            _line, ipython_completions = self.complete(text)

            from _pydev_bundle._pydev_completer import Completer

            completer = Completer(self.get_namespace(), None)
            ret = completer.complete(act_tok)
            append = ret.append
            ip = self.ipython
            pydev_completions = set([f[0] for f in ret])
            for ipython_completion in ipython_completions:
                # PyCharm was not expecting completions with '%'...
                # Could be fixed in the backend, but it's probably better
                # fixing it at PyCharm.
                # if ipython_completion.startswith('%'):
                #    ipython_completion = ipython_completion[1:]

                if ipython_completion not in pydev_completions:
                    pydev_completions.add(ipython_completion)
                    inf = ip.object_inspect(ipython_completion)
                    if inf["type_name"] == "Magic function":
                        pydev_type = TYPE_IPYTHON_MAGIC
                    else:
                        pydev_type = TYPE_IPYTHON
                    pydev_doc = inf["docstring"]
                    if pydev_doc is None:
                        pydev_doc = ""
                    append((ipython_completion, pydev_doc, "", pydev_type))
            return ret
        except:
            import traceback

            traceback.print_exc()
            return []

    def get_namespace(self):
        return self.ipython.user_ns

    def clear_buffer(self):
        del self._curr_exec_lines[:]

    def add_exec(self, line):
        if self._curr_exec_lines:
            self._curr_exec_lines.append(line)

            buf = "\n".join(self._curr_exec_lines)

            if self.is_complete(buf):
                self._curr_exec_line += 1
                self.ipython.run_cell(buf)
                del self._curr_exec_lines[:]
                return False  # execute complete (no more)

            return True  # needs more
        else:
            if not self.is_complete(line):
                # Did not execute
                self._curr_exec_lines.append(line)
                return True  # needs more
            else:
                self._curr_exec_line += 1
                self.ipython.run_cell(line, store_history=True)
                # hist = self.ipython.history_manager.output_hist_reprs
                # rep = hist.get(self._curr_exec_line, None)
                # if rep is not None:
                #    print(rep)
                return False  # execute complete (no more)

    def is_automagic(self):
        return self.ipython.automagic

    def get_greeting_msg(self):
        return "PyDev console: using IPython %s\n" % self.version


class _PyDevFrontEndContainer:
    _instance = None
    _last_host_port = None


def get_pydev_frontend(pydev_host, pydev_client_port):
    if _PyDevFrontEndContainer._instance is None:
        _PyDevFrontEndContainer._instance = _PyDevFrontEnd()

    if _PyDevFrontEndContainer._last_host_port != (pydev_host, pydev_client_port):
        _PyDevFrontEndContainer._last_host_port = pydev_host, pydev_client_port

        # Back channel to PyDev to open editors (in the future other
        # info may go back this way. This is the same channel that is
        # used to get stdin, see StdIn in pydev_console_utils)
        _PyDevFrontEndContainer._instance.ipython.hooks["editor"] = create_editor_hook(pydev_host, pydev_client_port)

        # Note: setting the callback directly because setting it with set_hook would actually create a chain instead
        # of ovewriting at each new call).
        # _PyDevFrontEndContainer._instance.ipython.set_hook('editor', create_editor_hook(pydev_host, pydev_client_port))

    return _PyDevFrontEndContainer._instance

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\transports\grpc_asyncio.py ===
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
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

from .base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .grpc import PermissionServiceGrpcTransport


class PermissionServiceGrpcAsyncIOTransport(PermissionServiceTransport):
    """gRPC AsyncIO backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

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
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest],
        Awaitable[gag_permission.Permission],
    ]:
        r"""Return a callable for the create permission method over gRPC.

        Create a permission to a specific resource.

        Returns:
            Callable[[~.CreatePermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_permission" not in self._stubs:
            self._stubs["create_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/CreatePermission",
                request_serializer=permission_service.CreatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["create_permission"]

    @property
    def get_permission(
        self,
    ) -> Callable[
        [permission_service.GetPermissionRequest], Awaitable[permission.Permission]
    ]:
        r"""Return a callable for the get permission method over gRPC.

        Gets information about a specific Permission.

        Returns:
            Callable[[~.GetPermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_permission" not in self._stubs:
            self._stubs["get_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/GetPermission",
                request_serializer=permission_service.GetPermissionRequest.serialize,
                response_deserializer=permission.Permission.deserialize,
            )
        return self._stubs["get_permission"]

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        Awaitable[permission_service.ListPermissionsResponse],
    ]:
        r"""Return a callable for the list permissions method over gRPC.

        Lists permissions for the specific resource.

        Returns:
            Callable[[~.ListPermissionsRequest],
                    Awaitable[~.ListPermissionsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_permissions" not in self._stubs:
            self._stubs["list_permissions"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/ListPermissions",
                request_serializer=permission_service.ListPermissionsRequest.serialize,
                response_deserializer=permission_service.ListPermissionsResponse.deserialize,
            )
        return self._stubs["list_permissions"]

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest],
        Awaitable[gag_permission.Permission],
    ]:
        r"""Return a callable for the update permission method over gRPC.

        Updates the permission.

        Returns:
            Callable[[~.UpdatePermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_permission" not in self._stubs:
            self._stubs["update_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/UpdatePermission",
                request_serializer=permission_service.UpdatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["update_permission"]

    @property
    def delete_permission(
        self,
    ) -> Callable[
        [permission_service.DeletePermissionRequest], Awaitable[empty_pb2.Empty]
    ]:
        r"""Return a callable for the delete permission method over gRPC.

        Deletes the permission.

        Returns:
            Callable[[~.DeletePermissionRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_permission" not in self._stubs:
            self._stubs["delete_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/DeletePermission",
                request_serializer=permission_service.DeletePermissionRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_permission"]

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        Awaitable[permission_service.TransferOwnershipResponse],
    ]:
        r"""Return a callable for the transfer ownership method over gRPC.

        Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        Returns:
            Callable[[~.TransferOwnershipRequest],
                    Awaitable[~.TransferOwnershipResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "transfer_ownership" not in self._stubs:
            self._stubs["transfer_ownership"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.PermissionService/TransferOwnership",
                request_serializer=permission_service.TransferOwnershipRequest.serialize,
                response_deserializer=permission_service.TransferOwnershipResponse.deserialize,
            )
        return self._stubs["transfer_ownership"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.create_permission: gapic_v1.method_async.wrap_method(
                self.create_permission,
                default_retry=retries.AsyncRetry(
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
            self.get_permission: gapic_v1.method_async.wrap_method(
                self.get_permission,
                default_retry=retries.AsyncRetry(
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
            self.list_permissions: gapic_v1.method_async.wrap_method(
                self.list_permissions,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_permission: gapic_v1.method_async.wrap_method(
                self.update_permission,
                default_retry=retries.AsyncRetry(
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
            self.delete_permission: gapic_v1.method_async.wrap_method(
                self.delete_permission,
                default_retry=retries.AsyncRetry(
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
            self.transfer_ownership: gapic_v1.method_async.wrap_method(
                self.transfer_ownership,
                default_retry=retries.AsyncRetry(
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
        return self.grpc_channel.close()


__all__ = ("PermissionServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\transports\grpc_asyncio.py ===
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
from google.api_core import gapic_v1, grpc_helpers_async, operations_v1
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model, model_service
from google.ai.generativelanguage_v1beta3.types import tuned_model

from .base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .grpc import ModelServiceGrpcTransport


class ModelServiceGrpcAsyncIOTransport(ModelServiceTransport):
    """gRPC AsyncIO backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

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
        self._operations_client: Optional[operations_v1.OperationsAsyncClient] = None

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
    def operations_client(self) -> operations_v1.OperationsAsyncClient:
        """Create the client designed to process long-running operations.

        This property caches on the instance; repeated calls return the same
        client.
        """
        # Quick check: Only create a new client if we do not already have one.
        if self._operations_client is None:
            self._operations_client = operations_v1.OperationsAsyncClient(
                self.grpc_channel
            )

        # Return the client from cache.
        return self._operations_client

    @property
    def get_model(
        self,
    ) -> Callable[[model_service.GetModelRequest], Awaitable[model.Model]]:
        r"""Return a callable for the get model method over gRPC.

        Gets information about a specific Model.

        Returns:
            Callable[[~.GetModelRequest],
                    Awaitable[~.Model]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_model" not in self._stubs:
            self._stubs["get_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/GetModel",
                request_serializer=model_service.GetModelRequest.serialize,
                response_deserializer=model.Model.deserialize,
            )
        return self._stubs["get_model"]

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest], Awaitable[model_service.ListModelsResponse]
    ]:
        r"""Return a callable for the list models method over gRPC.

        Lists models available through the API.

        Returns:
            Callable[[~.ListModelsRequest],
                    Awaitable[~.ListModelsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_models" not in self._stubs:
            self._stubs["list_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    @property
    def get_tuned_model(
        self,
    ) -> Callable[
        [model_service.GetTunedModelRequest], Awaitable[tuned_model.TunedModel]
    ]:
        r"""Return a callable for the get tuned model method over gRPC.

        Gets information about a specific TunedModel.

        Returns:
            Callable[[~.GetTunedModelRequest],
                    Awaitable[~.TunedModel]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_tuned_model" not in self._stubs:
            self._stubs["get_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/GetTunedModel",
                request_serializer=model_service.GetTunedModelRequest.serialize,
                response_deserializer=tuned_model.TunedModel.deserialize,
            )
        return self._stubs["get_tuned_model"]

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest],
        Awaitable[model_service.ListTunedModelsResponse],
    ]:
        r"""Return a callable for the list tuned models method over gRPC.

        Lists tuned models owned by the user.

        Returns:
            Callable[[~.ListTunedModelsRequest],
                    Awaitable[~.ListTunedModelsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_tuned_models" not in self._stubs:
            self._stubs["list_tuned_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/ListTunedModels",
                request_serializer=model_service.ListTunedModelsRequest.serialize,
                response_deserializer=model_service.ListTunedModelsResponse.deserialize,
            )
        return self._stubs["list_tuned_models"]

    @property
    def create_tuned_model(
        self,
    ) -> Callable[
        [model_service.CreateTunedModelRequest], Awaitable[operations_pb2.Operation]
    ]:
        r"""Return a callable for the create tuned model method over gRPC.

        Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        Returns:
            Callable[[~.CreateTunedModelRequest],
                    Awaitable[~.Operation]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_tuned_model" not in self._stubs:
            self._stubs["create_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/CreateTunedModel",
                request_serializer=model_service.CreateTunedModelRequest.serialize,
                response_deserializer=operations_pb2.Operation.FromString,
            )
        return self._stubs["create_tuned_model"]

    @property
    def update_tuned_model(
        self,
    ) -> Callable[
        [model_service.UpdateTunedModelRequest], Awaitable[gag_tuned_model.TunedModel]
    ]:
        r"""Return a callable for the update tuned model method over gRPC.

        Updates a tuned model.

        Returns:
            Callable[[~.UpdateTunedModelRequest],
                    Awaitable[~.TunedModel]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_tuned_model" not in self._stubs:
            self._stubs["update_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/UpdateTunedModel",
                request_serializer=model_service.UpdateTunedModelRequest.serialize,
                response_deserializer=gag_tuned_model.TunedModel.deserialize,
            )
        return self._stubs["update_tuned_model"]

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[[model_service.DeleteTunedModelRequest], Awaitable[empty_pb2.Empty]]:
        r"""Return a callable for the delete tuned model method over gRPC.

        Deletes a tuned model.

        Returns:
            Callable[[~.DeleteTunedModelRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_tuned_model" not in self._stubs:
            self._stubs["delete_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.ModelService/DeleteTunedModel",
                request_serializer=model_service.DeleteTunedModelRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_tuned_model"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.get_model: gapic_v1.method_async.wrap_method(
                self.get_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method_async.wrap_method(
                self.list_models,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_tuned_model: gapic_v1.method_async.wrap_method(
                self.get_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_tuned_models: gapic_v1.method_async.wrap_method(
                self.list_tuned_models,
                default_timeout=None,
                client_info=client_info,
            ),
            self.create_tuned_model: gapic_v1.method_async.wrap_method(
                self.create_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_tuned_model: gapic_v1.method_async.wrap_method(
                self.update_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_tuned_model: gapic_v1.method_async.wrap_method(
                self.delete_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("ModelServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\ollama\chat\transformation.py ===
import json
import time
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Iterator,
    List,
    Optional,
    Union,
    cast,
)

from httpx._models import Headers, Response
from pydantic import BaseModel

import litellm
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.ollama import OllamaToolCall, OllamaToolCallFunction
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantToolCall,
    ChatCompletionUsageBlock,
)
from litellm.types.utils import ModelResponse, ModelResponseStream

from ..common_utils import OllamaError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OllamaChatConfig(BaseConfig):
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
    num_thread: Optional[int] = None
    repeat_last_n: Optional[int] = None
    repeat_penalty: Optional[float] = None
    seed: Optional[int] = None
    tfs_z: Optional[float] = None
    num_predict: Optional[int] = None
    top_k: Optional[int] = None
    system: Optional[str] = None
    template: Optional[str] = None

    def __init__(
        self,
        mirostat: Optional[int] = None,
        mirostat_eta: Optional[float] = None,
        mirostat_tau: Optional[float] = None,
        num_ctx: Optional[int] = None,
        num_gqa: Optional[int] = None,
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

    def get_supported_openai_params(self, model: str):
        return [
            "max_tokens",
            "max_completion_tokens",
            "stream",
            "top_p",
            "temperature",
            "seed",
            "frequency_penalty",
            "stop",
            "tools",
            "tool_choice",
            "functions",
            "response_format",
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
                optional_params["repeat_penalty"] = value
            if param == "stop":
                optional_params["stop"] = value
            if (
                param == "response_format"
                and isinstance(value, dict)
                and value.get("type") == "json_object"
            ):
                optional_params["format"] = "json"
            if (
                param == "response_format"
                and isinstance(value, dict)
                and value.get("type") == "json_schema"
            ):
                if value.get("json_schema") and value["json_schema"].get("schema"):
                    optional_params["format"] = value["json_schema"]["schema"]
            ### FUNCTION CALLING LOGIC ###
            if param == "tools":
                ## CHECK IF MODEL SUPPORTS TOOL CALLING ##
                try:
                    model_info = litellm.get_model_info(
                        model=model, custom_llm_provider="ollama"
                    )
                    if model_info.get("supports_function_calling") is True:
                        optional_params["tools"] = value
                    else:
                        raise Exception
                except Exception:
                    optional_params["format"] = "json"
                    litellm.add_function_to_prompt = (
                        True  # so that main.py adds the function call to the prompt
                    )
                    optional_params["functions_unsupported_model"] = value

                    if len(optional_params["functions_unsupported_model"]) == 1:
                        optional_params["function_name"] = optional_params[
                            "functions_unsupported_model"
                        ][0]["function"]["name"]

            if param == "functions":
                ## CHECK IF MODEL SUPPORTS TOOL CALLING ##
                try:
                    model_info = litellm.get_model_info(
                        model=model, custom_llm_provider="ollama"
                    )
                    if model_info.get("supports_function_calling") is True:
                        optional_params["tools"] = value
                    else:
                        raise Exception
                except Exception:
                    optional_params["format"] = "json"
                    litellm.add_function_to_prompt = (
                        True  # so that main.py adds the function call to the prompt
                    )
                    optional_params[
                        "functions_unsupported_model"
                    ] = non_default_params.get("functions")
        non_default_params.pop("tool_choice", None)  # causes ollama requests to hang
        non_default_params.pop("functions", None)  # causes ollama requests to hang
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
        if api_base.endswith("/api/chat"):
            url = api_base
        else:
            url = f"{api_base}/api/chat"

        return url

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        stream = optional_params.pop("stream", False)
        format = optional_params.pop("format", None)
        keep_alive = optional_params.pop("keep_alive", None)
        function_name = optional_params.pop("function_name", None)
        litellm_params["function_name"] = function_name
        tools = optional_params.pop("tools", None)

        new_messages = []
        for m in messages:
            if isinstance(
                m, BaseModel
            ):  # avoid message serialization issues - https://github.com/BerriAI/litellm/issues/5319
                m = m.model_dump(exclude_none=True)
            tool_calls = m.get("tool_calls")
            if tool_calls is not None and isinstance(tool_calls, list):
                new_tools: List[OllamaToolCall] = []
                for tool in tool_calls:
                    typed_tool = ChatCompletionAssistantToolCall(**tool)  # type: ignore
                    if typed_tool["type"] == "function":
                        arguments = {}
                        if "arguments" in typed_tool["function"]:
                            arguments = json.loads(typed_tool["function"]["arguments"])
                        ollama_tool_call = OllamaToolCall(
                            function=OllamaToolCallFunction(
                                name=typed_tool["function"].get("name") or "",
                                arguments=arguments,
                            )
                        )
                        new_tools.append(ollama_tool_call)
                cast(dict, m)["tool_calls"] = new_tools
            new_messages.append(m)

        data = {
            "model": model,
            "messages": new_messages,
            "options": optional_params,
            "stream": stream,
        }
        if format is not None:
            data["format"] = format
        if tools is not None:
            data["tools"] = tools
        if keep_alive is not None:
            data["keep_alive"] = keep_alive

        return data

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
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response=raw_response.text,
            additional_args={
                "headers": None,
                "api_base": litellm_params.get("api_base"),
            },
        )

        response_json = raw_response.json()

        ## RESPONSE OBJECT
        model_response.choices[0].finish_reason = "stop"
        if (
            request_data.get("format", "") == "json"
            and litellm_params.get("function_name") is not None
        ):
            function_call = json.loads(response_json["message"]["content"])
            message = litellm.Message(
                content=None,
                tool_calls=[
                    {
                        "id": f"call_{str(uuid.uuid4())}",
                        "function": {
                            "name": function_call.get(
                                "name", litellm_params.get("function_name")
                            ),
                            "arguments": json.dumps(
                                function_call.get("arguments", function_call)
                            ),
                        },
                        "type": "function",
                    }
                ],
            )
            model_response.choices[0].message = message  # type: ignore
            model_response.choices[0].finish_reason = "tool_calls"
        else:
            _message = litellm.Message(**response_json["message"])
            model_response.choices[0].message = _message  # type: ignore
        model_response.created = int(time.time())
        model_response.model = "ollama_chat/" + model
        prompt_tokens = response_json.get("prompt_eval_count", litellm.token_counter(messages=messages))  # type: ignore
        completion_tokens = response_json.get(
            "eval_count",
            litellm.token_counter(text=response_json["message"]["content"]),
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

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return OllamaError(
            status_code=status_code, message=error_message, headers=headers
        )

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return OllamaChatCompletionResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class OllamaChatCompletionResponseIterator(BaseModelResponseIterator):
    def _is_function_call_complete(self, function_args: Union[str, dict]) -> bool:
        if isinstance(function_args, dict):
            return True
        try:
            json.loads(function_args)
            return True
        except Exception:
            return False

    def chunk_parser(self, chunk: dict) -> ModelResponseStream:
        try:
            """
            Expected chunk format:
            {
                "model": "llama3.1",
                "created_at": "2025-05-24T02:12:05.859654Z",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "function": {
                            "name": "get_latest_album_ratings",
                            "arguments": {
                                "artist_name": "Taylor Swift"
                            }
                        }
                    }]
                },
                "done_reason": "stop",
                "done": true,
                ...
            }

            Need to:
            - convert 'message' to 'delta'
            - return finish_reason when done is true
            - return usage when done is true

            """
            from litellm.types.utils import Delta, StreamingChoices

            # process tool calls - if complete function arg - add id to tool call
            tool_calls = chunk["message"].get("tool_calls")
            if tool_calls is not None:
                for tool_call in tool_calls:
                    function_args = tool_call.get("function").get("arguments")
                    if function_args is not None and len(function_args) > 0:
                        is_function_call_complete = self._is_function_call_complete(
                            function_args
                        )
                        if is_function_call_complete:
                            tool_call["id"] = str(uuid.uuid4())

            delta = Delta(
                content=chunk["message"].get("content", ""),
                tool_calls=tool_calls,
            )

            if chunk["done"] is True:
                finish_reason = chunk.get("done_reason", "stop")
                choices = [
                    StreamingChoices(
                        delta=delta,
                        finish_reason=finish_reason,
                    )
                ]
            else:
                choices = [
                    StreamingChoices(
                        delta=delta,
                    )
                ]

            usage = ChatCompletionUsageBlock(
                prompt_tokens=chunk.get("prompt_eval_count", 0),
                completion_tokens=chunk.get("eval_count", 0),
                total_tokens=chunk.get("prompt_eval_count", 0)
                + chunk.get("eval_count", 0),
            )

            return ModelResponseStream(
                id=str(uuid.uuid4()),
                object="chat.completion.chunk",
                created=int(time.time()),  # ollama created_at is in UTC
                usage=usage,
                model=chunk["model"],
                choices=choices,
            )
        except KeyError as e:
            raise OllamaError(
                message=f"KeyError: {e}, Got unexpected response from Ollama: {chunk}",
                status_code=400,
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            raise e

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\ssl_.py ===
from __future__ import absolute_import

import hashlib
import hmac
import os
import sys
import warnings
from binascii import hexlify, unhexlify

from ..exceptions import (
    InsecurePlatformWarning,
    ProxySchemeUnsupported,
    SNIMissingWarning,
    SSLError,
)
from ..packages import six
from .url import BRACELESS_IPV6_ADDRZ_RE, IPV4_RE

SSLContext = None
SSLTransport = None
HAS_SNI = False
IS_PYOPENSSL = False
IS_SECURETRANSPORT = False
ALPN_PROTOCOLS = ["http/1.1"]

# Maps the length of a digest to a possible hash function producing this digest
HASHFUNC_MAP = {
    length: getattr(hashlib, algorithm, None)
    for length, algorithm in ((32, "md5"), (40, "sha1"), (64, "sha256"))
}


def _const_compare_digest_backport(a, b):
    """
    Compare two digests of equal length in constant time.

    The digests must be of type str/bytes.
    Returns True if the digests match, and False otherwise.
    """
    result = abs(len(a) - len(b))
    for left, right in zip(bytearray(a), bytearray(b)):
        result |= left ^ right
    return result == 0


_const_compare_digest = getattr(hmac, "compare_digest", _const_compare_digest_backport)

try:  # Test for SSL features
    import ssl
    from ssl import CERT_REQUIRED, wrap_socket
except ImportError:
    pass

try:
    from ssl import HAS_SNI  # Has SNI?
except ImportError:
    pass

try:
    from .ssltransport import SSLTransport
except ImportError:
    pass


try:  # Platform-specific: Python 3.6
    from ssl import PROTOCOL_TLS

    PROTOCOL_SSLv23 = PROTOCOL_TLS
except ImportError:
    try:
        from ssl import PROTOCOL_SSLv23 as PROTOCOL_TLS

        PROTOCOL_SSLv23 = PROTOCOL_TLS
    except ImportError:
        PROTOCOL_SSLv23 = PROTOCOL_TLS = 2

try:
    from ssl import PROTOCOL_TLS_CLIENT
except ImportError:
    PROTOCOL_TLS_CLIENT = PROTOCOL_TLS


try:
    from ssl import OP_NO_COMPRESSION, OP_NO_SSLv2, OP_NO_SSLv3
except ImportError:
    OP_NO_SSLv2, OP_NO_SSLv3 = 0x1000000, 0x2000000
    OP_NO_COMPRESSION = 0x20000


try:  # OP_NO_TICKET was added in Python 3.6
    from ssl import OP_NO_TICKET
except ImportError:
    OP_NO_TICKET = 0x4000


# A secure default.
# Sources for more information on TLS ciphers:
#
# - https://wiki.mozilla.org/Security/Server_Side_TLS
# - https://www.ssllabs.com/projects/best-practices/index.html
# - https://hynek.me/articles/hardening-your-web-servers-ssl-ciphers/
#
# The general intent is:
# - prefer cipher suites that offer perfect forward secrecy (DHE/ECDHE),
# - prefer ECDHE over DHE for better performance,
# - prefer any AES-GCM and ChaCha20 over any AES-CBC for better performance and
#   security,
# - prefer AES-GCM over ChaCha20 because hardware-accelerated AES is common,
# - disable NULL authentication, MD5 MACs, DSS, and other
#   insecure ciphers for security reasons.
# - NOTE: TLS 1.3 cipher suites are managed through a different interface
#   not exposed by CPython (yet!) and are enabled by default if they're available.
DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)

try:
    from ssl import SSLContext  # Modern SSL?
except ImportError:

    class SSLContext(object):  # Platform-specific: Python 2
        def __init__(self, protocol_version):
            self.protocol = protocol_version
            # Use default values from a real SSLContext
            self.check_hostname = False
            self.verify_mode = ssl.CERT_NONE
            self.ca_certs = None
            self.options = 0
            self.certfile = None
            self.keyfile = None
            self.ciphers = None

        def load_cert_chain(self, certfile, keyfile):
            self.certfile = certfile
            self.keyfile = keyfile

        def load_verify_locations(self, cafile=None, capath=None, cadata=None):
            self.ca_certs = cafile

            if capath is not None:
                raise SSLError("CA directories not supported in older Pythons")

            if cadata is not None:
                raise SSLError("CA data not supported in older Pythons")

        def set_ciphers(self, cipher_suite):
            self.ciphers = cipher_suite

        def wrap_socket(self, socket, server_hostname=None, server_side=False):
            warnings.warn(
                "A true SSLContext object is not available. This prevents "
                "urllib3 from configuring SSL appropriately and may cause "
                "certain SSL connections to fail. You can upgrade to a newer "
                "version of Python to solve this. For more information, see "
                "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                "#ssl-warnings",
                InsecurePlatformWarning,
            )
            kwargs = {
                "keyfile": self.keyfile,
                "certfile": self.certfile,
                "ca_certs": self.ca_certs,
                "cert_reqs": self.verify_mode,
                "ssl_version": self.protocol,
                "server_side": server_side,
            }
            return wrap_socket(socket, ciphers=self.ciphers, **kwargs)


def assert_fingerprint(cert, fingerprint):
    """
    Checks if given fingerprint matches the supplied certificate.

    :param cert:
        Certificate as bytes object.
    :param fingerprint:
        Fingerprint as string of hexdigits, can be interspersed by colons.
    """

    fingerprint = fingerprint.replace(":", "").lower()
    digest_length = len(fingerprint)
    if digest_length not in HASHFUNC_MAP:
        raise SSLError("Fingerprint of invalid length: {0}".format(fingerprint))
    hashfunc = HASHFUNC_MAP.get(digest_length)
    if hashfunc is None:
        raise SSLError(
            "Hash function implementation unavailable for fingerprint length: {0}".format(
                digest_length
            )
        )

    # We need encode() here for py32; works on py2 and p33.
    fingerprint_bytes = unhexlify(fingerprint.encode())

    cert_digest = hashfunc(cert).digest()

    if not _const_compare_digest(cert_digest, fingerprint_bytes):
        raise SSLError(
            'Fingerprints did not match. Expected "{0}", got "{1}".'.format(
                fingerprint, hexlify(cert_digest)
            )
        )


def resolve_cert_reqs(candidate):
    """
    Resolves the argument to a numeric constant, which can be passed to
    the wrap_socket function/method from the ssl module.
    Defaults to :data:`ssl.CERT_REQUIRED`.
    If given a string it is assumed to be the name of the constant in the
    :mod:`ssl` module or its abbreviation.
    (So you can specify `REQUIRED` instead of `CERT_REQUIRED`.
    If it's neither `None` nor a string we assume it is already the numeric
    constant which can directly be passed to wrap_socket.
    """
    if candidate is None:
        return CERT_REQUIRED

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "CERT_" + candidate)
        return res

    return candidate


def resolve_ssl_version(candidate):
    """
    like resolve_cert_reqs
    """
    if candidate is None:
        return PROTOCOL_TLS

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "PROTOCOL_" + candidate)
        return res

    return candidate


def create_urllib3_context(
    ssl_version=None, cert_reqs=None, options=None, ciphers=None
):
    """All arguments have the same meaning as ``ssl_wrap_socket``.

    By default, this function does a lot of the same work that
    ``ssl.create_default_context`` does on Python 3.4+. It:

    - Disables SSLv2, SSLv3, and compression
    - Sets a restricted set of server ciphers

    If you wish to enable SSLv3, you can do::

        from pip._vendor.urllib3.util import ssl_
        context = ssl_.create_urllib3_context()
        context.options &= ~ssl_.OP_NO_SSLv3

    You can do the same to enable compression (substituting ``COMPRESSION``
    for ``SSLv3`` in the last line above).

    :param ssl_version:
        The desired protocol version to use. This will default to
        PROTOCOL_SSLv23 which will negotiate the highest protocol that both
        the server and your installation of OpenSSL support.
    :param cert_reqs:
        Whether to require the certificate verification. This defaults to
        ``ssl.CERT_REQUIRED``.
    :param options:
        Specific OpenSSL options. These default to ``ssl.OP_NO_SSLv2``,
        ``ssl.OP_NO_SSLv3``, ``ssl.OP_NO_COMPRESSION``, and ``ssl.OP_NO_TICKET``.
    :param ciphers:
        Which cipher suites to allow the server to select.
    :returns:
        Constructed SSLContext object with specified options
    :rtype: SSLContext
    """
    # PROTOCOL_TLS is deprecated in Python 3.10
    if not ssl_version or ssl_version == PROTOCOL_TLS:
        ssl_version = PROTOCOL_TLS_CLIENT

    context = SSLContext(ssl_version)

    context.set_ciphers(ciphers or DEFAULT_CIPHERS)

    # Setting the default here, as we may have no ssl module on import
    cert_reqs = ssl.CERT_REQUIRED if cert_reqs is None else cert_reqs

    if options is None:
        options = 0
        # SSLv2 is easily broken and is considered harmful and dangerous
        options |= OP_NO_SSLv2
        # SSLv3 has several problems and is now dangerous
        options |= OP_NO_SSLv3
        # Disable compression to prevent CRIME attacks for OpenSSL 1.0+
        # (issue #309)
        options |= OP_NO_COMPRESSION
        # TLSv1.2 only. Unless set explicitly, do not request tickets.
        # This may save some bandwidth on wire, and although the ticket is encrypted,
        # there is a risk associated with it being on wire,
        # if the server is not rotating its ticketing keys properly.
        options |= OP_NO_TICKET

    context.options |= options

    # Enable post-handshake authentication for TLS 1.3, see GH #1634. PHA is
    # necessary for conditional client cert authentication with TLS 1.3.
    # The attribute is None for OpenSSL <= 1.1.0 or does not exist in older
    # versions of Python.  We only enable on Python 3.7.4+ or if certificate
    # verification is enabled to work around Python issue #37428
    # See: https://bugs.python.org/issue37428
    if (cert_reqs == ssl.CERT_REQUIRED or sys.version_info >= (3, 7, 4)) and getattr(
        context, "post_handshake_auth", None
    ) is not None:
        context.post_handshake_auth = True

    def disable_check_hostname():
        if (
            getattr(context, "check_hostname", None) is not None
        ):  # Platform-specific: Python 3.2
            # We do our own verification, including fingerprints and alternative
            # hostnames. So disable it here
            context.check_hostname = False

    # The order of the below lines setting verify_mode and check_hostname
    # matter due to safe-guards SSLContext has to prevent an SSLContext with
    # check_hostname=True, verify_mode=NONE/OPTIONAL. This is made even more
    # complex because we don't know whether PROTOCOL_TLS_CLIENT will be used
    # or not so we don't know the initial state of the freshly created SSLContext.
    if cert_reqs == ssl.CERT_REQUIRED:
        context.verify_mode = cert_reqs
        disable_check_hostname()
    else:
        disable_check_hostname()
        context.verify_mode = cert_reqs

    # Enable logging of TLS session keys via defacto standard environment variable
    # 'SSLKEYLOGFILE', if the feature is available (Python 3.8+). Skip empty values.
    if hasattr(context, "keylog_filename"):
        sslkeylogfile = os.environ.get("SSLKEYLOGFILE")
        if sslkeylogfile:
            context.keylog_filename = sslkeylogfile

    return context


def ssl_wrap_socket(
    sock,
    keyfile=None,
    certfile=None,
    cert_reqs=None,
    ca_certs=None,
    server_hostname=None,
    ssl_version=None,
    ciphers=None,
    ssl_context=None,
    ca_cert_dir=None,
    key_password=None,
    ca_cert_data=None,
    tls_in_tls=False,
):
    """
    All arguments except for server_hostname, ssl_context, and ca_cert_dir have
    the same meaning as they do when using :func:`ssl.wrap_socket`.

    :param server_hostname:
        When SNI is supported, the expected hostname of the certificate
    :param ssl_context:
        A pre-made :class:`SSLContext` object. If none is provided, one will
        be created using :func:`create_urllib3_context`.
    :param ciphers:
        A string of ciphers we wish the client to support.
    :param ca_cert_dir:
        A directory containing CA certificates in multiple separate files, as
        supported by OpenSSL's -CApath flag or the capath argument to
        SSLContext.load_verify_locations().
    :param key_password:
        Optional password if the keyfile is encrypted.
    :param ca_cert_data:
        Optional string containing CA certificates in PEM format suitable for
        passing as the cadata parameter to SSLContext.load_verify_locations()
    :param tls_in_tls:
        Use SSLTransport to wrap the existing socket.
    """
    context = ssl_context
    if context is None:
        # Note: This branch of code and all the variables in it are no longer
        # used by urllib3 itself. We should consider deprecating and removing
        # this code.
        context = create_urllib3_context(ssl_version, cert_reqs, ciphers=ciphers)

    if ca_certs or ca_cert_dir or ca_cert_data:
        try:
            context.load_verify_locations(ca_certs, ca_cert_dir, ca_cert_data)
        except (IOError, OSError) as e:
            raise SSLError(e)

    elif ssl_context is None and hasattr(context, "load_default_certs"):
        # try to load OS default certs; works well on Windows (require Python3.4+)
        context.load_default_certs()

    # Attempt to detect if we get the goofy behavior of the
    # keyfile being encrypted and OpenSSL asking for the
    # passphrase via the terminal and instead error out.
    if keyfile and key_password is None and _is_key_file_encrypted(keyfile):
        raise SSLError("Client private key is encrypted, password is required")

    if certfile:
        if key_password is None:
            context.load_cert_chain(certfile, keyfile)
        else:
            context.load_cert_chain(certfile, keyfile, key_password)

    try:
        if hasattr(context, "set_alpn_protocols"):
            context.set_alpn_protocols(ALPN_PROTOCOLS)
    except NotImplementedError:  # Defensive: in CI, we always have set_alpn_protocols
        pass

    # If we detect server_hostname is an IP address then the SNI
    # extension should not be used according to RFC3546 Section 3.1
    use_sni_hostname = server_hostname and not is_ipaddress(server_hostname)
    # SecureTransport uses server_hostname in certificate verification.
    send_sni = (use_sni_hostname and HAS_SNI) or (
        IS_SECURETRANSPORT and server_hostname
    )
    # Do not warn the user if server_hostname is an invalid SNI hostname.
    if not HAS_SNI and use_sni_hostname:
        warnings.warn(
            "An HTTPS request has been made, but the SNI (Server Name "
            "Indication) extension to TLS is not available on this platform. "
            "This may cause the server to present an incorrect TLS "
            "certificate, which can cause validation failures. You can upgrade to "
            "a newer version of Python to solve this. For more information, see "
            "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
            "#ssl-warnings",
            SNIMissingWarning,
        )

    if send_sni:
        ssl_sock = _ssl_wrap_socket_impl(
            sock, context, tls_in_tls, server_hostname=server_hostname
        )
    else:
        ssl_sock = _ssl_wrap_socket_impl(sock, context, tls_in_tls)
    return ssl_sock


def is_ipaddress(hostname):
    """Detects whether the hostname given is an IPv4 or IPv6 address.
    Also detects IPv6 addresses with Zone IDs.

    :param str hostname: Hostname to examine.
    :return: True if the hostname is an IP address, False otherwise.
    """
    if not six.PY2 and isinstance(hostname, bytes):
        # IDN A-label bytes are ASCII compatible.
        hostname = hostname.decode("ascii")
    return bool(IPV4_RE.match(hostname) or BRACELESS_IPV6_ADDRZ_RE.match(hostname))


def _is_key_file_encrypted(key_file):
    """Detects if a key file is encrypted or not."""
    with open(key_file, "r") as f:
        for line in f:
            # Look for Proc-Type: 4,ENCRYPTED
            if "ENCRYPTED" in line:
                return True

    return False


def _ssl_wrap_socket_impl(sock, ssl_context, tls_in_tls, server_hostname=None):
    if tls_in_tls:
        if not SSLTransport:
            # Import error, ssl is not available.
            raise ProxySchemeUnsupported(
                "TLS in TLS requires support for the 'ssl' module"
            )

        SSLTransport._validate_ssl_context_for_tls_in_tls(ssl_context)
        return SSLTransport(sock, ssl_context, server_hostname)

    if server_hostname:
        return ssl_context.wrap_socket(sock, server_hostname=server_hostname)
    else:
        return ssl_context.wrap_socket(sock)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\flag_def.py ===
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
"""Classes that define arguments for populating ArgumentParser.

The argparse module's ArgumentParser.add_argument() takes several parameters and
is quite customizable. However this can lead to bugs where arguments do not
behave as expected.

For better ease-of-use and better testability, define a set of classes for the
types of flags used by LLM Magics.

Sample usage:

  str_flag = SingleValueFlagDef(name="title", required=True)
  enum_flag = EnumFlagDef(name="colors", required=True, enum_type=ColorsEnum)

  str_flag.add_argument_to_parser(my_parser)
  enum_flag.add_argument_to_parser(my_parser)
"""
from __future__ import annotations

import abc
import argparse
import dataclasses
import enum
from typing import Any, Callable, Sequence, Tuple, Union

from google.generativeai.notebook.lib import llmfn_inputs_source
from google.generativeai.notebook.lib import llmfn_outputs

# These are the intermediate types that argparse.ArgumentParser.parse_args()
# will pass command line arguments into.
_PARSETYPES = Union[str, int, float]
# These are the final result types that the intermediate parsed values will be
# converted into. It is a superset of _PARSETYPES because we support converting
# the parsed type into a more precise type, e.g. from str to Enum.
_DESTTYPES = Union[
    _PARSETYPES,
    enum.Enum,
    Tuple[str, Callable[[str, str], Any]],
    Sequence[str],  # For --compare_fn
    llmfn_inputs_source.LLMFnInputsSource,  # For --ground_truth
    llmfn_outputs.LLMFnOutputsSink,  # For --inputs  # For --outputs
]

# The signature of a function that converts a command line argument from the
# intermediate parsed type to the result type.
_PARSEFN = Callable[[_PARSETYPES], _DESTTYPES]


def _get_type_name(x: type[Any]) -> str:
    try:
        return x.__name__
    except AttributeError:
        return str(x)


def _validate_flag_name(name: str) -> str:
    """Validation for long and short names for flags."""
    if not name:
        raise ValueError("Cannot be empty")
    if name[0] == "-":
        raise ValueError("Cannot start with dash")
    return name


@dataclasses.dataclass(frozen=True)
class FlagDef(abc.ABC):
    """Abstract base class for flag definitions.

    Attributes:
      name: Long name, e.g. "colors" will define the flag "--colors".
      required: Whether the flag must be provided on the command line.
      short_name: Optional short name.
      parse_type: The type that ArgumentParser should parse the command line
        argument to.
      dest_type: The type that the parsed value is converted to. This is used when
        we want ArgumentParser to parse as one type, then convert to a different
        type. E.g. for enums we parse as "str" then convert to the desired enum
        type in order to provide cleaner help messages.
      parse_to_dest_type_fn: If provided, this function will be used to convert
        the value from `parse_type` to `dest_type`. This can be used for
        validation as well.
      choices: If provided, limit the set of acceptable values to these choices.
      help_msg: If provided, adds help message when -h is used in the command
        line.
    """

    name: str
    required: bool = False

    short_name: str | None = None

    parse_type: type[_PARSETYPES] = str
    dest_type: type[_DESTTYPES] | None = None
    parse_to_dest_type_fn: _PARSEFN | None = None

    choices: list[_PARSETYPES] | None = None
    help_msg: str | None = None

    @abc.abstractmethod
    def add_argument_to_parser(self, parser: argparse.ArgumentParser) -> None:
        """Adds this flag as an argument to `parser`.

        Child classes should implement this as a call to parser.add_argument()
        with the appropriate parameters.

        Args:
          parser: The parser to which this argument will be added.
        """

    @abc.abstractmethod
    def _do_additional_validation(self) -> None:
        """For child classes to do additional validation."""

    def _get_dest_type(self) -> type[_DESTTYPES]:
        """Returns the final converted type."""
        return self.parse_type if self.dest_type is None else self.dest_type

    def _get_parse_to_dest_type_fn(
        self,
    ) -> _PARSEFN:
        """Returns a function to convert from parse_type to dest_type."""
        if self.parse_to_dest_type_fn is not None:
            return self.parse_to_dest_type_fn

        dest_type = self._get_dest_type()
        if dest_type == self.parse_type:
            return lambda x: x
        else:
            return dest_type

    def __post_init__(self):
        _validate_flag_name(self.name)
        if self.short_name is not None:
            _validate_flag_name(self.short_name)

        self._do_additional_validation()


def _has_non_default_value(
    namespace: argparse.Namespace,
    dest: str,
    has_default: bool = False,
    default_value: Any = None,
) -> bool:
    """Returns true if `namespace.dest` is set to a non-default value.

    Args:
      namespace: The Namespace that is populated by ArgumentParser.
      dest: The attribute in the Namespace to be populated.
      has_default: "None" is a valid default value so we use an additional
        `has_default` boolean to indicate that `default_value` is present.
      default_value: The default value to use when `has_default` is True.

    Returns:
      Whether namespace.dest is set to something other than the default value.
    """
    if not hasattr(namespace, dest):
        return False

    if not has_default:
        # No default value provided so `namespace.dest` cannot possibly be equal to
        # the default value.
        return True

    return getattr(namespace, dest) != default_value


class _SingleValueStoreAction(argparse.Action):
    """Custom Action for storing a value in an argparse.Namespace.

    This action checks that the flag is specified at-most once.
    """

    def __init__(
        self,
        option_strings,
        dest,
        dest_type: type[Any],
        parse_to_dest_type_fn: _PARSEFN,
        **kwargs,
    ):
        super().__init__(option_strings, dest, **kwargs)
        self._dest_type = dest_type
        self._parse_to_dest_type_fn = parse_to_dest_type_fn

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ):
        # Because `nargs` is set to 1, `values` must be a Sequence, rather
        # than a string.
        assert not isinstance(values, str) and not isinstance(values, bytes)

        if _has_non_default_value(
            namespace,
            self.dest,
            has_default=hasattr(self, "default"),
            default_value=getattr(self, "default"),
        ):
            raise argparse.ArgumentError(self, "Cannot set {} more than once".format(option_string))

        try:
            converted_value = self._parse_to_dest_type_fn(values[0])
        except Exception as e:
            raise argparse.ArgumentError(
                self,
                'Error with value "{}", got {}: {}'.format(values[0], _get_type_name(type(e)), e),
            )

        if not isinstance(converted_value, self._dest_type):
            raise RuntimeError(
                "Converted to wrong type, expected {} got {}".format(
                    _get_type_name(self._dest_type),
                    _get_type_name(type(converted_value)),
                )
            )
        setattr(namespace, self.dest, converted_value)


class _MultiValuesAppendAction(argparse.Action):
    """Custom Action for appending values in an argparse.Namespace.

    This action checks that the flag is specified at-most once.
    """

    def __init__(
        self,
        option_strings,
        dest,
        dest_type: type[Any],
        parse_to_dest_type_fn: _PARSEFN,
        **kwargs,
    ):
        super().__init__(option_strings, dest, **kwargs)
        self._dest_type = dest_type
        self._parse_to_dest_type_fn = parse_to_dest_type_fn

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ):
        # Because `nargs` is set to "+", `values` must be a Sequence, rather
        # than a string.
        assert not isinstance(values, str) and not isinstance(values, bytes)

        curr_value = getattr(namespace, self.dest)
        if curr_value:
            raise argparse.ArgumentError(self, "Cannot set {} more than once".format(option_string))

        for value in values:
            try:
                converted_value = self._parse_to_dest_type_fn(value)
            except Exception as e:
                raise argparse.ArgumentError(
                    self,
                    'Error with value "{}", got {}: {}'.format(
                        values[0], _get_type_name(type(e)), e
                    ),
                )

            if not isinstance(converted_value, self._dest_type):
                raise RuntimeError(
                    "Converted to wrong type, expected {} got {}".format(
                        self._dest_type, type(converted_value)
                    )
                )
            if converted_value in curr_value:
                raise argparse.ArgumentError(self, 'Duplicate values "{}"'.format(value))

            curr_value.append(converted_value)


class _BooleanValueStoreAction(argparse.Action):
    """Custom Action for setting a boolean value in argparse.Namespace.

    The boolean flag expects the default to be False and will set the value to
    True.
    This action checks that the flag is specified at-most once.
    """

    def __init__(
        self,
        option_strings,
        dest,
        **kwargs,
    ):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ):
        if _has_non_default_value(
            namespace,
            self.dest,
            has_default=True,
            default_value=False,
        ):
            raise argparse.ArgumentError(self, "Cannot set {} more than once".format(option_string))

        setattr(namespace, self.dest, True)


@dataclasses.dataclass(frozen=True)
class SingleValueFlagDef(FlagDef):
    """Definition for a flag that takes a single value.

    Sample usage:
      # This defines a flag that can be specified on the command line as:
      #   --count=10
      flag = SingleValueFlagDef(name="count", parse_type=int, required=True)
      flag.add_argument_to_parser(argument_parser)

    Attributes:
      default_value: Default value for optional flags.
    """

    class _DefaultValue(enum.Enum):
        """Special value to represent "no value provided".

        "None" can be used as a default value, so in order to differentiate between
        "None" and "no value provided", create a special value for "no value
        provided".
        """

        NOT_SET = None

    default_value: _DESTTYPES | _DefaultValue | None = _DefaultValue.NOT_SET

    def _has_default_value(self) -> bool:
        """Returns whether `default_value` has been provided."""
        return self.default_value != SingleValueFlagDef._DefaultValue.NOT_SET

    def add_argument_to_parser(self, parser: argparse.ArgumentParser) -> None:
        args = ["--" + self.name]
        if self.short_name is not None:
            args += ["-" + self.short_name]

        kwargs = {}
        if self._has_default_value():
            kwargs["default"] = self.default_value
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.help_msg is not None:
            kwargs["help"] = self.help_msg

        parser.add_argument(
            *args,
            action=_SingleValueStoreAction,
            type=self.parse_type,
            dest_type=self._get_dest_type(),
            parse_to_dest_type_fn=self._get_parse_to_dest_type_fn(),
            required=self.required,
            nargs=1,
            **kwargs,
        )

    def _do_additional_validation(self) -> None:
        if self.required:
            if self._has_default_value():
                raise ValueError("Required flags cannot have default value")
        else:
            if not self._has_default_value():
                raise ValueError("Optional flags must have a default value")

        if self._has_default_value() and self.default_value is not None:
            if not isinstance(self.default_value, self._get_dest_type()):
                raise ValueError("Default value must be of the same type as the destination type")


class EnumFlagDef(SingleValueFlagDef):
    """Definition for a flag that takes a value from an Enum.

    Sample usage:
      # This defines a flag that can be specified on the command line as:
      #   --color=red
      flag = SingleValueFlagDef(name="color", enum_type=ColorsEnum,
                                required=True)
      flag.add_argument_to_parser(argument_parser)
    """

    def __init__(self, *args, enum_type: type[enum.Enum], **kwargs):
        if not issubclass(enum_type, enum.Enum):
            raise TypeError('"enum_type" must be of type Enum')

        # These properties are set by "enum_type" so don"t let the caller set them.
        if "parse_type" in kwargs:
            raise ValueError('Cannot set "parse_type" for EnumFlagDef; set "enum_type" instead')
        kwargs["parse_type"] = str

        if "dest_type" in kwargs:
            raise ValueError('Cannot set "dest_type" for EnumFlagDef; set "enum_type" instead')
        kwargs["dest_type"] = enum_type

        if "choices" in kwargs:
            # Verify that entries in `choices` are valid enum values.
            for x in kwargs["choices"]:
                try:
                    enum_type(x)
                except ValueError:
                    raise ValueError('Invalid value in "choices": "{}"'.format(x)) from None
        else:
            kwargs["choices"] = [x.value for x in enum_type]

        super().__init__(*args, **kwargs)


class MultiValuesFlagDef(FlagDef):
    """Definition for a flag that takes multiple values.

    Sample usage:
      # This defines a flag that can be specified on the command line as:
      #   --colors=red green blue
      flag = MultiValuesFlagDef(name="colors", parse_type=str, required=True)
      flag.add_argument_to_parser(argument_parser)
    """

    def add_argument_to_parser(self, parser: argparse.ArgumentParser) -> None:
        args = ["--" + self.name]
        if self.short_name is not None:
            args += ["-" + self.short_name]

        kwargs = {}
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.help_msg is not None:
            kwargs["help"] = self.help_msg

        parser.add_argument(
            *args,
            action=_MultiValuesAppendAction,
            type=self.parse_type,
            dest_type=self._get_dest_type(),
            parse_to_dest_type_fn=self._get_parse_to_dest_type_fn(),
            required=self.required,
            default=[],
            nargs="+",
            **kwargs,
        )

    def _do_additional_validation(self) -> None:
        # No additional validation needed.
        pass


@dataclasses.dataclass(frozen=True)
class BooleanFlagDef(FlagDef):
    """Definition for a Boolean flag.

    A boolean flag is always optional with a default value of False. The flag does
    not take any values. Specifying the flag on the commandline will set it to
    True.
    """

    def _do_additional_validation(self) -> None:
        if self.dest_type is not None:
            raise ValueError("dest_type cannot be set for BooleanFlagDef")
        if self.parse_to_dest_type_fn is not None:
            raise ValueError("parse_to_dest_type_fn cannot be set for BooleanFlagDef")
        if self.choices is not None:
            raise ValueError("choices cannot be set for BooleanFlagDef")

    def add_argument_to_parser(self, parser: argparse.ArgumentParser) -> None:
        args = ["--" + self.name]
        if self.short_name is not None:
            args += ["-" + self.short_name]

        kwargs = {}
        if self.help_msg is not None:
            kwargs["help"] = self.help_msg

        parser.add_argument(
            *args,
            action=_BooleanValueStoreAction,
            type=bool,
            required=False,
            default=False,
            nargs=0,
            **kwargs,
        )

# === NexusCore/openenv\Lib\site-packages\pycparser\c_generator.py ===
#------------------------------------------------------------------------------
# pycparser: c_generator.py
#
# C code generator from pycparser AST nodes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------
from . import c_ast


class CGenerator(object):
    """ Uses the same visitor pattern as c_ast.NodeVisitor, but modified to
        return a value from each visit method, using string accumulation in
        generic_visit.
    """
    def __init__(self, reduce_parentheses=False):
        """ Constructs C-code generator

            reduce_parentheses:
                if True, eliminates needless parentheses on binary operators
        """
        # Statements start with indentation of self.indent_level spaces, using
        # the _make_indent method.
        self.indent_level = 0
        self.reduce_parentheses = reduce_parentheses

    def _make_indent(self):
        return ' ' * self.indent_level

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        return getattr(self, method, self.generic_visit)(node)

    def generic_visit(self, node):
        if node is None:
            return ''
        else:
            return ''.join(self.visit(c) for c_name, c in node.children())

    def visit_Constant(self, n):
        return n.value

    def visit_ID(self, n):
        return n.name

    def visit_Pragma(self, n):
        ret = '#pragma'
        if n.string:
            ret += ' ' + n.string
        return ret

    def visit_ArrayRef(self, n):
        arrref = self._parenthesize_unless_simple(n.name)
        return arrref + '[' + self.visit(n.subscript) + ']'

    def visit_StructRef(self, n):
        sref = self._parenthesize_unless_simple(n.name)
        return sref + n.type + self.visit(n.field)

    def visit_FuncCall(self, n):
        fref = self._parenthesize_unless_simple(n.name)
        return fref + '(' + self.visit(n.args) + ')'

    def visit_UnaryOp(self, n):
        if n.op == 'sizeof':
            # Always parenthesize the argument of sizeof since it can be
            # a name.
            return 'sizeof(%s)' % self.visit(n.expr)
        else:
            operand = self._parenthesize_unless_simple(n.expr)
            if n.op == 'p++':
                return '%s++' % operand
            elif n.op == 'p--':
                return '%s--' % operand
            else:
                return '%s%s' % (n.op, operand)

    # Precedence map of binary operators:
    precedence_map = {
        # Should be in sync with c_parser.CParser.precedence
        # Higher numbers are stronger binding
        '||': 0,  # weakest binding
        '&&': 1,
        '|': 2,
        '^': 3,
        '&': 4,
        '==': 5, '!=': 5,
        '>': 6, '>=': 6, '<': 6, '<=': 6,
        '>>': 7, '<<': 7,
        '+': 8, '-': 8,
        '*': 9, '/': 9, '%': 9  # strongest binding
    }

    def visit_BinaryOp(self, n):
        # Note: all binary operators are left-to-right associative
        #
        # If `n.left.op` has a stronger or equally binding precedence in
        # comparison to `n.op`, no parenthesis are needed for the left:
        # e.g., `(a*b) + c` is equivalent to `a*b + c`, as well as
        #       `(a+b) - c` is equivalent to `a+b - c` (same precedence).
        # If the left operator is weaker binding than the current, then
        # parentheses are necessary:
        # e.g., `(a+b) * c` is NOT equivalent to `a+b * c`.
        lval_str = self._parenthesize_if(
            n.left,
            lambda d: not (self._is_simple_node(d) or
                      self.reduce_parentheses and isinstance(d, c_ast.BinaryOp) and
                      self.precedence_map[d.op] >= self.precedence_map[n.op]))
        # If `n.right.op` has a stronger -but not equal- binding precedence,
        # parenthesis can be omitted on the right:
        # e.g., `a + (b*c)` is equivalent to `a + b*c`.
        # If the right operator is weaker or equally binding, then parentheses
        # are necessary:
        # e.g., `a * (b+c)` is NOT equivalent to `a * b+c` and
        #       `a - (b+c)` is NOT equivalent to `a - b+c` (same precedence).
        rval_str = self._parenthesize_if(
            n.right,
            lambda d: not (self._is_simple_node(d) or
                      self.reduce_parentheses and isinstance(d, c_ast.BinaryOp) and
                      self.precedence_map[d.op] > self.precedence_map[n.op]))
        return '%s %s %s' % (lval_str, n.op, rval_str)

    def visit_Assignment(self, n):
        rval_str = self._parenthesize_if(
                            n.rvalue,
                            lambda n: isinstance(n, c_ast.Assignment))
        return '%s %s %s' % (self.visit(n.lvalue), n.op, rval_str)

    def visit_IdentifierType(self, n):
        return ' '.join(n.names)

    def _visit_expr(self, n):
        if isinstance(n, c_ast.InitList):
            return '{' + self.visit(n) + '}'
        elif isinstance(n, c_ast.ExprList):
            return '(' + self.visit(n) + ')'
        else:
            return self.visit(n)

    def visit_Decl(self, n, no_type=False):
        # no_type is used when a Decl is part of a DeclList, where the type is
        # explicitly only for the first declaration in a list.
        #
        s = n.name if no_type else self._generate_decl(n)
        if n.bitsize: s += ' : ' + self.visit(n.bitsize)
        if n.init:
            s += ' = ' + self._visit_expr(n.init)
        return s

    def visit_DeclList(self, n):
        s = self.visit(n.decls[0])
        if len(n.decls) > 1:
            s += ', ' + ', '.join(self.visit_Decl(decl, no_type=True)
                                    for decl in n.decls[1:])
        return s

    def visit_Typedef(self, n):
        s = ''
        if n.storage: s += ' '.join(n.storage) + ' '
        s += self._generate_type(n.type)
        return s

    def visit_Cast(self, n):
        s = '(' + self._generate_type(n.to_type, emit_declname=False) + ')'
        return s + ' ' + self._parenthesize_unless_simple(n.expr)

    def visit_ExprList(self, n):
        visited_subexprs = []
        for expr in n.exprs:
            visited_subexprs.append(self._visit_expr(expr))
        return ', '.join(visited_subexprs)

    def visit_InitList(self, n):
        visited_subexprs = []
        for expr in n.exprs:
            visited_subexprs.append(self._visit_expr(expr))
        return ', '.join(visited_subexprs)

    def visit_Enum(self, n):
        return self._generate_struct_union_enum(n, name='enum')

    def visit_Alignas(self, n):
        return '_Alignas({})'.format(self.visit(n.alignment))

    def visit_Enumerator(self, n):
        if not n.value:
            return '{indent}{name},\n'.format(
                indent=self._make_indent(),
                name=n.name,
            )
        else:
            return '{indent}{name} = {value},\n'.format(
                indent=self._make_indent(),
                name=n.name,
                value=self.visit(n.value),
            )

    def visit_FuncDef(self, n):
        decl = self.visit(n.decl)
        self.indent_level = 0
        body = self.visit(n.body)
        if n.param_decls:
            knrdecls = ';\n'.join(self.visit(p) for p in n.param_decls)
            return decl + '\n' + knrdecls + ';\n' + body + '\n'
        else:
            return decl + '\n' + body + '\n'

    def visit_FileAST(self, n):
        s = ''
        for ext in n.ext:
            if isinstance(ext, c_ast.FuncDef):
                s += self.visit(ext)
            elif isinstance(ext, c_ast.Pragma):
                s += self.visit(ext) + '\n'
            else:
                s += self.visit(ext) + ';\n'
        return s

    def visit_Compound(self, n):
        s = self._make_indent() + '{\n'
        self.indent_level += 2
        if n.block_items:
            s += ''.join(self._generate_stmt(stmt) for stmt in n.block_items)
        self.indent_level -= 2
        s += self._make_indent() + '}\n'
        return s

    def visit_CompoundLiteral(self, n):
        return '(' + self.visit(n.type) + '){' + self.visit(n.init) + '}'


    def visit_EmptyStatement(self, n):
        return ';'

    def visit_ParamList(self, n):
        return ', '.join(self.visit(param) for param in n.params)

    def visit_Return(self, n):
        s = 'return'
        if n.expr: s += ' ' + self.visit(n.expr)
        return s + ';'

    def visit_Break(self, n):
        return 'break;'

    def visit_Continue(self, n):
        return 'continue;'

    def visit_TernaryOp(self, n):
        s  = '(' + self._visit_expr(n.cond) + ') ? '
        s += '(' + self._visit_expr(n.iftrue) + ') : '
        s += '(' + self._visit_expr(n.iffalse) + ')'
        return s

    def visit_If(self, n):
        s = 'if ('
        if n.cond: s += self.visit(n.cond)
        s += ')\n'
        s += self._generate_stmt(n.iftrue, add_indent=True)
        if n.iffalse:
            s += self._make_indent() + 'else\n'
            s += self._generate_stmt(n.iffalse, add_indent=True)
        return s

    def visit_For(self, n):
        s = 'for ('
        if n.init: s += self.visit(n.init)
        s += ';'
        if n.cond: s += ' ' + self.visit(n.cond)
        s += ';'
        if n.next: s += ' ' + self.visit(n.next)
        s += ')\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_While(self, n):
        s = 'while ('
        if n.cond: s += self.visit(n.cond)
        s += ')\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_DoWhile(self, n):
        s = 'do\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        s += self._make_indent() + 'while ('
        if n.cond: s += self.visit(n.cond)
        s += ');'
        return s

    def visit_StaticAssert(self, n):
        s = '_Static_assert('
        s += self.visit(n.cond)
        if n.message:
            s += ','
            s += self.visit(n.message)
        s += ')'
        return s

    def visit_Switch(self, n):
        s = 'switch (' + self.visit(n.cond) + ')\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_Case(self, n):
        s = 'case ' + self.visit(n.expr) + ':\n'
        for stmt in n.stmts:
            s += self._generate_stmt(stmt, add_indent=True)
        return s

    def visit_Default(self, n):
        s = 'default:\n'
        for stmt in n.stmts:
            s += self._generate_stmt(stmt, add_indent=True)
        return s

    def visit_Label(self, n):
        return n.name + ':\n' + self._generate_stmt(n.stmt)

    def visit_Goto(self, n):
        return 'goto ' + n.name + ';'

    def visit_EllipsisParam(self, n):
        return '...'

    def visit_Struct(self, n):
        return self._generate_struct_union_enum(n, 'struct')

    def visit_Typename(self, n):
        return self._generate_type(n.type)

    def visit_Union(self, n):
        return self._generate_struct_union_enum(n, 'union')

    def visit_NamedInitializer(self, n):
        s = ''
        for name in n.name:
            if isinstance(name, c_ast.ID):
                s += '.' + name.name
            else:
                s += '[' + self.visit(name) + ']'
        s += ' = ' + self._visit_expr(n.expr)
        return s

    def visit_FuncDecl(self, n):
        return self._generate_type(n)

    def visit_ArrayDecl(self, n):
        return self._generate_type(n, emit_declname=False)

    def visit_TypeDecl(self, n):
        return self._generate_type(n, emit_declname=False)

    def visit_PtrDecl(self, n):
        return self._generate_type(n, emit_declname=False)

    def _generate_struct_union_enum(self, n, name):
        """ Generates code for structs, unions, and enums. name should be
            'struct', 'union', or 'enum'.
        """
        if name in ('struct', 'union'):
            members = n.decls
            body_function = self._generate_struct_union_body
        else:
            assert name == 'enum'
            members = None if n.values is None else n.values.enumerators
            body_function = self._generate_enum_body
        s = name + ' ' + (n.name or '')
        if members is not None:
            # None means no members
            # Empty sequence means an empty list of members
            s += '\n'
            s += self._make_indent()
            self.indent_level += 2
            s += '{\n'
            s += body_function(members)
            self.indent_level -= 2
            s += self._make_indent() + '}'
        return s

    def _generate_struct_union_body(self, members):
        return ''.join(self._generate_stmt(decl) for decl in members)

    def _generate_enum_body(self, members):
        # `[:-2] + '\n'` removes the final `,` from the enumerator list
        return ''.join(self.visit(value) for value in members)[:-2] + '\n'

    def _generate_stmt(self, n, add_indent=False):
        """ Generation from a statement node. This method exists as a wrapper
            for individual visit_* methods to handle different treatment of
            some statements in this context.
        """
        typ = type(n)
        if add_indent: self.indent_level += 2
        indent = self._make_indent()
        if add_indent: self.indent_level -= 2

        if typ in (
                c_ast.Decl, c_ast.Assignment, c_ast.Cast, c_ast.UnaryOp,
                c_ast.BinaryOp, c_ast.TernaryOp, c_ast.FuncCall, c_ast.ArrayRef,
                c_ast.StructRef, c_ast.Constant, c_ast.ID, c_ast.Typedef,
                c_ast.ExprList):
            # These can also appear in an expression context so no semicolon
            # is added to them automatically
            #
            return indent + self.visit(n) + ';\n'
        elif typ in (c_ast.Compound,):
            # No extra indentation required before the opening brace of a
            # compound - because it consists of multiple lines it has to
            # compute its own indentation.
            #
            return self.visit(n)
        elif typ in (c_ast.If,):
            return indent + self.visit(n)
        else:
            return indent + self.visit(n) + '\n'

    def _generate_decl(self, n):
        """ Generation from a Decl node.
        """
        s = ''
        if n.funcspec: s = ' '.join(n.funcspec) + ' '
        if n.storage: s += ' '.join(n.storage) + ' '
        if n.align: s += self.visit(n.align[0]) + ' '
        s += self._generate_type(n.type)
        return s

    def _generate_type(self, n, modifiers=[], emit_declname = True):
        """ Recursive generation from a type node. n is the type node.
            modifiers collects the PtrDecl, ArrayDecl and FuncDecl modifiers
            encountered on the way down to a TypeDecl, to allow proper
            generation from it.
        """
        typ = type(n)
        #~ print(n, modifiers)

        if typ == c_ast.TypeDecl:
            s = ''
            if n.quals: s += ' '.join(n.quals) + ' '
            s += self.visit(n.type)

            nstr = n.declname if n.declname and emit_declname else ''
            # Resolve modifiers.
            # Wrap in parens to distinguish pointer to array and pointer to
            # function syntax.
            #
            for i, modifier in enumerate(modifiers):
                if isinstance(modifier, c_ast.ArrayDecl):
                    if (i != 0 and
                        isinstance(modifiers[i - 1], c_ast.PtrDecl)):
                            nstr = '(' + nstr + ')'
                    nstr += '['
                    if modifier.dim_quals:
                        nstr += ' '.join(modifier.dim_quals) + ' '
                    nstr += self.visit(modifier.dim) + ']'
                elif isinstance(modifier, c_ast.FuncDecl):
                    if (i != 0 and
                        isinstance(modifiers[i - 1], c_ast.PtrDecl)):
                            nstr = '(' + nstr + ')'
                    nstr += '(' + self.visit(modifier.args) + ')'
                elif isinstance(modifier, c_ast.PtrDecl):
                    if modifier.quals:
                        nstr = '* %s%s' % (' '.join(modifier.quals),
                                           ' ' + nstr if nstr else '')
                    else:
                        nstr = '*' + nstr
            if nstr: s += ' ' + nstr
            return s
        elif typ == c_ast.Decl:
            return self._generate_decl(n.type)
        elif typ == c_ast.Typename:
            return self._generate_type(n.type, emit_declname = emit_declname)
        elif typ == c_ast.IdentifierType:
            return ' '.join(n.names) + ' '
        elif typ in (c_ast.ArrayDecl, c_ast.PtrDecl, c_ast.FuncDecl):
            return self._generate_type(n.type, modifiers + [n],
                                       emit_declname = emit_declname)
        else:
            return self.visit(n)

    def _parenthesize_if(self, n, condition):
        """ Visits 'n' and returns its string representation, parenthesized
            if the condition function applied to the node returns True.
        """
        s = self._visit_expr(n)
        if condition(n):
            return '(' + s + ')'
        else:
            return s

    def _parenthesize_unless_simple(self, n):
        """ Common use case for _parenthesize_if
        """
        return self._parenthesize_if(n, lambda d: not self._is_simple_node(d))

    def _is_simple_node(self, n):
        """ Returns True for nodes that are "simple" - i.e. nodes that always
            have higher precedence than operators.
        """
        return isinstance(n, (c_ast.Constant, c_ast.ID, c_ast.ArrayRef,
                              c_ast.StructRef, c_ast.FuncCall))

# === NexusCore/openenv\Lib\site-packages\anthropic\_legacy_response.py ===
from __future__ import annotations

import os
import inspect
import logging
import datetime
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    Generic,
    TypeVar,
    Callable,
    Iterator,
    AsyncIterator,
    cast,
    overload,
)
from typing_extensions import Awaitable, ParamSpec, override, deprecated, get_origin

import anyio
import httpx
import pydantic

from ._types import NoneType
from ._utils import is_given, extract_type_arg, is_annotated_type
from ._models import BaseModel, is_basemodel
from ._constants import RAW_RESPONSE_HEADER
from ._streaming import Stream, AsyncStream, is_stream_class_type, extract_stream_chunk_type
from ._exceptions import APIResponseValidationError
from ._decoders.jsonl import JSONLDecoder, AsyncJSONLDecoder

if TYPE_CHECKING:
    from ._models import FinalRequestOptions
    from ._base_client import BaseClient


P = ParamSpec("P")
R = TypeVar("R")
_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)

log: logging.Logger = logging.getLogger(__name__)


class LegacyAPIResponse(Generic[R]):
    """This is a legacy class as it will be replaced by `APIResponse`
    and `AsyncAPIResponse` in the `_response.py` file in the next major
    release.

    For the sync client this will mostly be the same with the exception
    of `content` & `text` will be methods instead of properties. In the
    async client, all methods will be async.

    A migration script will be provided & the migration in general should
    be smooth.
    """

    _cast_to: type[R]
    _client: BaseClient[Any, Any]
    _parsed_by_type: dict[type[Any], Any]
    _stream: bool
    _stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None
    _options: FinalRequestOptions

    http_response: httpx.Response

    retries_taken: int
    """The number of retries made. If no retries happened this will be `0`"""

    def __init__(
        self,
        *,
        raw: httpx.Response,
        cast_to: type[R],
        client: BaseClient[Any, Any],
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        options: FinalRequestOptions,
        retries_taken: int = 0,
    ) -> None:
        self._cast_to = cast_to
        self._client = client
        self._parsed_by_type = {}
        self._stream = stream
        self._stream_cls = stream_cls
        self._options = options
        self.http_response = raw
        self.retries_taken = retries_taken

    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("request-id")  # type: ignore[no-any-return]

    @overload
    def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    def parse(self) -> R: ...

    def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        NOTE: For the async client: this will become a coroutine in the next major version.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from anthropic import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `int`
          - `float`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        self._parsed_by_type[cache_key] = parsed
        return parsed

    @property
    def headers(self) -> httpx.Headers:
        return self.http_response.headers

    @property
    def http_request(self) -> httpx.Request:
        return self.http_response.request

    @property
    def status_code(self) -> int:
        return self.http_response.status_code

    @property
    def url(self) -> httpx.URL:
        return self.http_response.url

    @property
    def method(self) -> str:
        return self.http_request.method

    @property
    def content(self) -> bytes:
        """Return the binary response content.

        NOTE: this will be removed in favour of `.read()` in the
        next major version.
        """
        return self.http_response.content

    @property
    def text(self) -> str:
        """Return the decoded response content.

        NOTE: this will be turned into a method in the next major version.
        """
        return self.http_response.text

    @property
    def http_version(self) -> str:
        return self.http_response.http_version

    @property
    def is_closed(self) -> bool:
        return self.http_response.is_closed

    @property
    def elapsed(self) -> datetime.timedelta:
        """The time taken for the complete request/response cycle to complete."""
        return self.http_response.elapsed

    def _parse(self, *, to: type[_T] | None = None) -> R | _T:
        # unwrap `Annotated[T, ...]` -> `T`
        if to and is_annotated_type(to):
            to = extract_type_arg(to, 0)

        cast_to = to if to is not None else self._cast_to
        origin = get_origin(cast_to) or cast_to

        if inspect.isclass(origin):
            if issubclass(origin, (JSONLDecoder)):
                return cast(
                    R,
                    cast("type[JSONLDecoder[Any]]", cast_to)(
                        raw_iterator=self.http_response.iter_bytes(chunk_size=4096),
                        line_type=extract_type_arg(cast_to, 0),
                        http_response=self.http_response,
                    ),
                )

            if issubclass(origin, AsyncJSONLDecoder):
                return cast(
                    R,
                    cast("type[AsyncJSONLDecoder[Any]]", cast_to)(
                        raw_iterator=self.http_response.aiter_bytes(chunk_size=4096),
                        line_type=extract_type_arg(cast_to, 0),
                        http_response=self.http_response,
                    ),
                )

        if self._stream:
            if to:
                if not is_stream_class_type(to):
                    raise TypeError(f"Expected custom parse type to be a subclass of {Stream} or {AsyncStream}")

                return cast(
                    _T,
                    to(
                        cast_to=extract_stream_chunk_type(
                            to,
                            failure_message="Expected custom stream type to be passed with a type argument, e.g. Stream[ChunkType]",
                        ),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            if self._stream_cls:
                return cast(
                    R,
                    self._stream_cls(
                        cast_to=extract_stream_chunk_type(self._stream_cls),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            stream_cls = cast("type[Stream[Any]] | type[AsyncStream[Any]] | None", self._client._default_stream_cls)
            if stream_cls is None:
                raise MissingStreamClassError()

            return cast(
                R,
                stream_cls(
                    cast_to=self._cast_to,
                    response=self.http_response,
                    client=cast(Any, self._client),
                ),
            )

        # unwrap `Annotated[T, ...]` -> `T`
        if is_annotated_type(cast_to):
            cast_to = extract_type_arg(cast_to, 0)

        if cast_to is NoneType:
            return cast(R, None)

        response = self.http_response
        if cast_to == str:
            return cast(R, response.text)

        if cast_to == int:
            return cast(R, int(response.text))

        if cast_to == float:
            return cast(R, float(response.text))

        if cast_to == bool:
            return cast(R, response.text.lower() == "true")

        origin = get_origin(cast_to) or cast_to

        if inspect.isclass(origin) and issubclass(origin, HttpxBinaryResponseContent):
            return cast(R, cast_to(response))  # type: ignore

        if origin == LegacyAPIResponse:
            raise RuntimeError("Unexpected state - cast_to is `APIResponse`")

        if inspect.isclass(origin) and issubclass(origin, httpx.Response):
            # Because of the invariance of our ResponseT TypeVar, users can subclass httpx.Response
            # and pass that class to our request functions. We cannot change the variance to be either
            # covariant or contravariant as that makes our usage of ResponseT illegal. We could construct
            # the response class ourselves but that is something that should be supported directly in httpx
            # as it would be easy to incorrectly construct the Response object due to the multitude of arguments.
            if cast_to != httpx.Response:
                raise ValueError(f"Subclasses of httpx.Response cannot be passed to `cast_to`")
            return cast(R, response)

        if inspect.isclass(origin) and not issubclass(origin, BaseModel) and issubclass(origin, pydantic.BaseModel):
            raise TypeError("Pydantic models must subclass our base model type, e.g. `from anthropic import BaseModel`")

        if (
            cast_to is not object
            and not origin is list
            and not origin is dict
            and not origin is Union
            and not issubclass(origin, BaseModel)
        ):
            raise RuntimeError(
                f"Unsupported type, expected {cast_to} to be a subclass of {BaseModel}, {dict}, {list}, {Union}, {NoneType}, {str} or {httpx.Response}."
            )

        # split is required to handle cases where additional information is included
        # in the response, e.g. application/json; charset=utf-8
        content_type, *_ = response.headers.get("content-type", "*").split(";")
        if content_type != "application/json":
            if is_basemodel(cast_to):
                try:
                    data = response.json()
                except Exception as exc:
                    log.debug("Could not read JSON from response data due to %s - %s", type(exc), exc)
                else:
                    return self._client._process_response_data(
                        data=data,
                        cast_to=cast_to,  # type: ignore
                        response=response,
                    )

            if self._client._strict_response_validation:
                raise APIResponseValidationError(
                    response=response,
                    message=f"Expected Content-Type response header to be `application/json` but received `{content_type}` instead.",
                    body=response.text,
                )

            # If the API responds with content that isn't JSON then we just return
            # the (decoded) text without performing any parsing so that you can still
            # handle the response however you need to.
            return response.text  # type: ignore

        data = response.json()

        return self._client._process_response_data(
            data=data,
            cast_to=cast_to,  # type: ignore
            response=response,
        )

    @override
    def __repr__(self) -> str:
        return f"<APIResponse [{self.status_code} {self.http_response.reason_phrase}] type={self._cast_to}>"


class MissingStreamClassError(TypeError):
    def __init__(self) -> None:
        super().__init__(
            "The `stream` argument was set to `True` but the `stream_cls` argument was not given. See `anthropic._streaming` for reference",
        )


def to_raw_response_wrapper(func: Callable[P, R]) -> Callable[P, LegacyAPIResponse[R]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> LegacyAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "true"

        kwargs["extra_headers"] = extra_headers

        return cast(LegacyAPIResponse[R], func(*args, **kwargs))

    return wrapped


def async_to_raw_response_wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[LegacyAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> LegacyAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "true"

        kwargs["extra_headers"] = extra_headers

        return cast(LegacyAPIResponse[R], await func(*args, **kwargs))

    return wrapped


class HttpxBinaryResponseContent:
    response: httpx.Response

    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    @property
    def content(self) -> bytes:
        return self.response.content

    @property
    def text(self) -> str:
        return self.response.text

    @property
    def encoding(self) -> str | None:
        return self.response.encoding

    @property
    def charset_encoding(self) -> str | None:
        return self.response.charset_encoding

    def json(self, **kwargs: Any) -> Any:
        return self.response.json(**kwargs)

    def read(self) -> bytes:
        return self.response.read()

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        return self.response.iter_bytes(chunk_size)

    def iter_text(self, chunk_size: int | None = None) -> Iterator[str]:
        return self.response.iter_text(chunk_size)

    def iter_lines(self) -> Iterator[str]:
        return self.response.iter_lines()

    def iter_raw(self, chunk_size: int | None = None) -> Iterator[bytes]:
        return self.response.iter_raw(chunk_size)

    def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `client.with_streaming_response.foo().stream_to_file('my_filename.txt')`
        """
        with open(file, mode="wb") as f:
            for data in self.response.iter_bytes():
                f.write(data)

    @deprecated(
        "Due to a bug, this method doesn't actually stream the response content, `.with_streaming_response.method()` should be used instead"
    )
    def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        with open(file, mode="wb") as f:
            for data in self.response.iter_bytes(chunk_size):
                f.write(data)

    def close(self) -> None:
        return self.response.close()

    async def aread(self) -> bytes:
        return await self.response.aread()

    async def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        return self.response.aiter_bytes(chunk_size)

    async def aiter_text(self, chunk_size: int | None = None) -> AsyncIterator[str]:
        return self.response.aiter_text(chunk_size)

    async def aiter_lines(self) -> AsyncIterator[str]:
        return self.response.aiter_lines()

    async def aiter_raw(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        return self.response.aiter_raw(chunk_size)

    @deprecated(
        "Due to a bug, this method doesn't actually stream the response content, `.with_streaming_response.method()` should be used instead"
    )
    async def astream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.response.aiter_bytes(chunk_size):
                await f.write(data)

    async def aclose(self) -> None:
        return await self.response.aclose()

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\mfc\afxres.py ===
# Generated by h2py from stdin
TCS_MULTILINE = 0x0200
CBRS_ALIGN_LEFT = 0x1000
CBRS_ALIGN_TOP = 0x2000
CBRS_ALIGN_RIGHT = 0x4000
CBRS_ALIGN_BOTTOM = 0x8000
CBRS_ALIGN_ANY = 0xF000
CBRS_BORDER_LEFT = 0x0100
CBRS_BORDER_TOP = 0x0200
CBRS_BORDER_RIGHT = 0x0400
CBRS_BORDER_BOTTOM = 0x0800
CBRS_BORDER_ANY = 0x0F00
CBRS_TOOLTIPS = 0x0010
CBRS_FLYBY = 0x0020
CBRS_FLOAT_MULTI = 0x0040
CBRS_BORDER_3D = 0x0080
CBRS_HIDE_INPLACE = 0x0008
CBRS_SIZE_DYNAMIC = 0x0004
CBRS_SIZE_FIXED = 0x0002
CBRS_FLOATING = 0x0001
CBRS_GRIPPER = 0x00400000
CBRS_ORIENT_HORZ = CBRS_ALIGN_TOP | CBRS_ALIGN_BOTTOM
CBRS_ORIENT_VERT = CBRS_ALIGN_LEFT | CBRS_ALIGN_RIGHT
CBRS_ORIENT_ANY = CBRS_ORIENT_HORZ | CBRS_ORIENT_VERT
CBRS_ALL = 0xFFFF
CBRS_NOALIGN = 0x00000000
CBRS_LEFT = CBRS_ALIGN_LEFT | CBRS_BORDER_RIGHT
CBRS_TOP = CBRS_ALIGN_TOP | CBRS_BORDER_BOTTOM
CBRS_RIGHT = CBRS_ALIGN_RIGHT | CBRS_BORDER_LEFT
CBRS_BOTTOM = CBRS_ALIGN_BOTTOM | CBRS_BORDER_TOP
SBPS_NORMAL = 0x0000
SBPS_NOBORDERS = 0x0100
SBPS_POPOUT = 0x0200
SBPS_OWNERDRAW = 0x1000
SBPS_DISABLED = 0x04000000
SBPS_STRETCH = 0x08000000
ID_INDICATOR_EXT = 0xE700
ID_INDICATOR_CAPS = 0xE701
ID_INDICATOR_NUM = 0xE702
ID_INDICATOR_SCRL = 0xE703
ID_INDICATOR_OVR = 0xE704
ID_INDICATOR_REC = 0xE705
ID_INDICATOR_KANA = 0xE706
ID_SEPARATOR = 0
AFX_IDW_CONTROLBAR_FIRST = 0xE800
AFX_IDW_CONTROLBAR_LAST = 0xE8FF
AFX_IDW_TOOLBAR = 0xE800
AFX_IDW_STATUS_BAR = 0xE801
AFX_IDW_PREVIEW_BAR = 0xE802
AFX_IDW_RESIZE_BAR = 0xE803
AFX_IDW_DOCKBAR_TOP = 0xE81B
AFX_IDW_DOCKBAR_LEFT = 0xE81C
AFX_IDW_DOCKBAR_RIGHT = 0xE81D
AFX_IDW_DOCKBAR_BOTTOM = 0xE81E
AFX_IDW_DOCKBAR_FLOAT = 0xE81F


def AFX_CONTROLBAR_MASK(nIDC):
    return 1 << (nIDC - AFX_IDW_CONTROLBAR_FIRST)


AFX_IDW_PANE_FIRST = 0xE900
AFX_IDW_PANE_LAST = 0xE9FF
AFX_IDW_HSCROLL_FIRST = 0xEA00
AFX_IDW_VSCROLL_FIRST = 0xEA10
AFX_IDW_SIZE_BOX = 0xEA20
AFX_IDW_PANE_SAVE = 0xEA21
AFX_IDS_APP_TITLE = 0xE000
AFX_IDS_IDLEMESSAGE = 0xE001
AFX_IDS_HELPMODEMESSAGE = 0xE002
AFX_IDS_APP_TITLE_EMBEDDING = 0xE003
AFX_IDS_COMPANY_NAME = 0xE004
AFX_IDS_OBJ_TITLE_INPLACE = 0xE005
ID_FILE_NEW = 0xE100
ID_FILE_OPEN = 0xE101
ID_FILE_CLOSE = 0xE102
ID_FILE_SAVE = 0xE103
ID_FILE_SAVE_AS = 0xE104
ID_FILE_PAGE_SETUP = 0xE105
ID_FILE_PRINT_SETUP = 0xE106
ID_FILE_PRINT = 0xE107
ID_FILE_PRINT_DIRECT = 0xE108
ID_FILE_PRINT_PREVIEW = 0xE109
ID_FILE_UPDATE = 0xE10A
ID_FILE_SAVE_COPY_AS = 0xE10B
ID_FILE_SEND_MAIL = 0xE10C
ID_FILE_MRU_FIRST = 0xE110
ID_FILE_MRU_FILE1 = 0xE110
ID_FILE_MRU_FILE2 = 0xE111
ID_FILE_MRU_FILE3 = 0xE112
ID_FILE_MRU_FILE4 = 0xE113
ID_FILE_MRU_FILE5 = 0xE114
ID_FILE_MRU_FILE6 = 0xE115
ID_FILE_MRU_FILE7 = 0xE116
ID_FILE_MRU_FILE8 = 0xE117
ID_FILE_MRU_FILE9 = 0xE118
ID_FILE_MRU_FILE10 = 0xE119
ID_FILE_MRU_FILE11 = 0xE11A
ID_FILE_MRU_FILE12 = 0xE11B
ID_FILE_MRU_FILE13 = 0xE11C
ID_FILE_MRU_FILE14 = 0xE11D
ID_FILE_MRU_FILE15 = 0xE11E
ID_FILE_MRU_FILE16 = 0xE11F
ID_FILE_MRU_LAST = 0xE11F
ID_EDIT_CLEAR = 0xE120
ID_EDIT_CLEAR_ALL = 0xE121
ID_EDIT_COPY = 0xE122
ID_EDIT_CUT = 0xE123
ID_EDIT_FIND = 0xE124
ID_EDIT_PASTE = 0xE125
ID_EDIT_PASTE_LINK = 0xE126
ID_EDIT_PASTE_SPECIAL = 0xE127
ID_EDIT_REPEAT = 0xE128
ID_EDIT_REPLACE = 0xE129
ID_EDIT_SELECT_ALL = 0xE12A
ID_EDIT_UNDO = 0xE12B
ID_EDIT_REDO = 0xE12C
ID_WINDOW_NEW = 0xE130
ID_WINDOW_ARRANGE = 0xE131
ID_WINDOW_CASCADE = 0xE132
ID_WINDOW_TILE_HORZ = 0xE133
ID_WINDOW_TILE_VERT = 0xE134
ID_WINDOW_SPLIT = 0xE135
AFX_IDM_WINDOW_FIRST = 0xE130
AFX_IDM_WINDOW_LAST = 0xE13F
AFX_IDM_FIRST_MDICHILD = 0xFF00
ID_APP_ABOUT = 0xE140
ID_APP_EXIT = 0xE141
ID_HELP_INDEX = 0xE142
ID_HELP_FINDER = 0xE143
ID_HELP_USING = 0xE144
ID_CONTEXT_HELP = 0xE145
ID_HELP = 0xE146
ID_DEFAULT_HELP = 0xE147
ID_NEXT_PANE = 0xE150
ID_PREV_PANE = 0xE151
ID_FORMAT_FONT = 0xE160
ID_OLE_INSERT_NEW = 0xE200
ID_OLE_EDIT_LINKS = 0xE201
ID_OLE_EDIT_CONVERT = 0xE202
ID_OLE_EDIT_CHANGE_ICON = 0xE203
ID_OLE_EDIT_PROPERTIES = 0xE204
ID_OLE_VERB_FIRST = 0xE210
ID_OLE_VERB_LAST = 0xE21F
AFX_ID_PREVIEW_CLOSE = 0xE300
AFX_ID_PREVIEW_NUMPAGE = 0xE301
AFX_ID_PREVIEW_NEXT = 0xE302
AFX_ID_PREVIEW_PREV = 0xE303
AFX_ID_PREVIEW_PRINT = 0xE304
AFX_ID_PREVIEW_ZOOMIN = 0xE305
AFX_ID_PREVIEW_ZOOMOUT = 0xE306
ID_VIEW_TOOLBAR = 0xE800
ID_VIEW_STATUS_BAR = 0xE801
ID_RECORD_FIRST = 0xE900
ID_RECORD_LAST = 0xE901
ID_RECORD_NEXT = 0xE902
ID_RECORD_PREV = 0xE903
IDC_STATIC = -1
AFX_IDS_SCFIRST = 0xEF00
AFX_IDS_SCSIZE = 0xEF00
AFX_IDS_SCMOVE = 0xEF01
AFX_IDS_SCMINIMIZE = 0xEF02
AFX_IDS_SCMAXIMIZE = 0xEF03
AFX_IDS_SCNEXTWINDOW = 0xEF04
AFX_IDS_SCPREVWINDOW = 0xEF05
AFX_IDS_SCCLOSE = 0xEF06
AFX_IDS_SCRESTORE = 0xEF12
AFX_IDS_SCTASKLIST = 0xEF13
AFX_IDS_MDICHILD = 0xEF1F
AFX_IDS_DESKACCESSORY = 0xEFDA
AFX_IDS_OPENFILE = 0xF000
AFX_IDS_SAVEFILE = 0xF001
AFX_IDS_ALLFILTER = 0xF002
AFX_IDS_UNTITLED = 0xF003
AFX_IDS_SAVEFILECOPY = 0xF004
AFX_IDS_PREVIEW_CLOSE = 0xF005
AFX_IDS_UNNAMED_FILE = 0xF006
AFX_IDS_ABOUT = 0xF010
AFX_IDS_HIDE = 0xF011
AFX_IDP_NO_ERROR_AVAILABLE = 0xF020
AFX_IDS_NOT_SUPPORTED_EXCEPTION = 0xF021
AFX_IDS_RESOURCE_EXCEPTION = 0xF022
AFX_IDS_MEMORY_EXCEPTION = 0xF023
AFX_IDS_USER_EXCEPTION = 0xF024
AFX_IDS_PRINTONPORT = 0xF040
AFX_IDS_ONEPAGE = 0xF041
AFX_IDS_TWOPAGE = 0xF042
AFX_IDS_PRINTPAGENUM = 0xF043
AFX_IDS_PREVIEWPAGEDESC = 0xF044
AFX_IDS_PRINTDEFAULTEXT = 0xF045
AFX_IDS_PRINTDEFAULT = 0xF046
AFX_IDS_PRINTFILTER = 0xF047
AFX_IDS_PRINTCAPTION = 0xF048
AFX_IDS_PRINTTOFILE = 0xF049
AFX_IDS_OBJECT_MENUITEM = 0xF080
AFX_IDS_EDIT_VERB = 0xF081
AFX_IDS_ACTIVATE_VERB = 0xF082
AFX_IDS_CHANGE_LINK = 0xF083
AFX_IDS_AUTO = 0xF084
AFX_IDS_MANUAL = 0xF085
AFX_IDS_FROZEN = 0xF086
AFX_IDS_ALL_FILES = 0xF087
AFX_IDS_SAVE_MENU = 0xF088
AFX_IDS_UPDATE_MENU = 0xF089
AFX_IDS_SAVE_AS_MENU = 0xF08A
AFX_IDS_SAVE_COPY_AS_MENU = 0xF08B
AFX_IDS_EXIT_MENU = 0xF08C
AFX_IDS_UPDATING_ITEMS = 0xF08D
AFX_IDS_METAFILE_FORMAT = 0xF08E
AFX_IDS_DIB_FORMAT = 0xF08F
AFX_IDS_BITMAP_FORMAT = 0xF090
AFX_IDS_LINKSOURCE_FORMAT = 0xF091
AFX_IDS_EMBED_FORMAT = 0xF092
AFX_IDS_PASTELINKEDTYPE = 0xF094
AFX_IDS_UNKNOWNTYPE = 0xF095
AFX_IDS_RTF_FORMAT = 0xF096
AFX_IDS_TEXT_FORMAT = 0xF097
AFX_IDS_INVALID_CURRENCY = 0xF098
AFX_IDS_INVALID_DATETIME = 0xF099
AFX_IDS_INVALID_DATETIMESPAN = 0xF09A
AFX_IDP_INVALID_FILENAME = 0xF100
AFX_IDP_FAILED_TO_OPEN_DOC = 0xF101
AFX_IDP_FAILED_TO_SAVE_DOC = 0xF102
AFX_IDP_ASK_TO_SAVE = 0xF103
AFX_IDP_FAILED_TO_CREATE_DOC = 0xF104
AFX_IDP_FILE_TOO_LARGE = 0xF105
AFX_IDP_FAILED_TO_START_PRINT = 0xF106
AFX_IDP_FAILED_TO_LAUNCH_HELP = 0xF107
AFX_IDP_INTERNAL_FAILURE = 0xF108
AFX_IDP_COMMAND_FAILURE = 0xF109
AFX_IDP_FAILED_MEMORY_ALLOC = 0xF10A
AFX_IDP_PARSE_INT = 0xF110
AFX_IDP_PARSE_REAL = 0xF111
AFX_IDP_PARSE_INT_RANGE = 0xF112
AFX_IDP_PARSE_REAL_RANGE = 0xF113
AFX_IDP_PARSE_STRING_SIZE = 0xF114
AFX_IDP_PARSE_RADIO_BUTTON = 0xF115
AFX_IDP_PARSE_BYTE = 0xF116
AFX_IDP_PARSE_UINT = 0xF117
AFX_IDP_PARSE_DATETIME = 0xF118
AFX_IDP_PARSE_CURRENCY = 0xF119
AFX_IDP_FAILED_INVALID_FORMAT = 0xF120
AFX_IDP_FAILED_INVALID_PATH = 0xF121
AFX_IDP_FAILED_DISK_FULL = 0xF122
AFX_IDP_FAILED_ACCESS_READ = 0xF123
AFX_IDP_FAILED_ACCESS_WRITE = 0xF124
AFX_IDP_FAILED_IO_ERROR_READ = 0xF125
AFX_IDP_FAILED_IO_ERROR_WRITE = 0xF126
AFX_IDP_STATIC_OBJECT = 0xF180
AFX_IDP_FAILED_TO_CONNECT = 0xF181
AFX_IDP_SERVER_BUSY = 0xF182
AFX_IDP_BAD_VERB = 0xF183
AFX_IDP_FAILED_TO_NOTIFY = 0xF185
AFX_IDP_FAILED_TO_LAUNCH = 0xF186
AFX_IDP_ASK_TO_UPDATE = 0xF187
AFX_IDP_FAILED_TO_UPDATE = 0xF188
AFX_IDP_FAILED_TO_REGISTER = 0xF189
AFX_IDP_FAILED_TO_AUTO_REGISTER = 0xF18A
AFX_IDP_FAILED_TO_CONVERT = 0xF18B
AFX_IDP_GET_NOT_SUPPORTED = 0xF18C
AFX_IDP_SET_NOT_SUPPORTED = 0xF18D
AFX_IDP_ASK_TO_DISCARD = 0xF18E
AFX_IDP_FAILED_TO_CREATE = 0xF18F
AFX_IDP_FAILED_MAPI_LOAD = 0xF190
AFX_IDP_INVALID_MAPI_DLL = 0xF191
AFX_IDP_FAILED_MAPI_SEND = 0xF192
AFX_IDP_FILE_NONE = 0xF1A0
AFX_IDP_FILE_GENERIC = 0xF1A1
AFX_IDP_FILE_NOT_FOUND = 0xF1A2
AFX_IDP_FILE_BAD_PATH = 0xF1A3
AFX_IDP_FILE_TOO_MANY_OPEN = 0xF1A4
AFX_IDP_FILE_ACCESS_DENIED = 0xF1A5
AFX_IDP_FILE_INVALID_FILE = 0xF1A6
AFX_IDP_FILE_REMOVE_CURRENT = 0xF1A7
AFX_IDP_FILE_DIR_FULL = 0xF1A8
AFX_IDP_FILE_BAD_SEEK = 0xF1A9
AFX_IDP_FILE_HARD_IO = 0xF1AA
AFX_IDP_FILE_SHARING = 0xF1AB
AFX_IDP_FILE_LOCKING = 0xF1AC
AFX_IDP_FILE_DISKFULL = 0xF1AD
AFX_IDP_FILE_EOF = 0xF1AE
AFX_IDP_ARCH_NONE = 0xF1B0
AFX_IDP_ARCH_GENERIC = 0xF1B1
AFX_IDP_ARCH_READONLY = 0xF1B2
AFX_IDP_ARCH_ENDOFFILE = 0xF1B3
AFX_IDP_ARCH_WRITEONLY = 0xF1B4
AFX_IDP_ARCH_BADINDEX = 0xF1B5
AFX_IDP_ARCH_BADCLASS = 0xF1B6
AFX_IDP_ARCH_BADSCHEMA = 0xF1B7
AFX_IDS_OCC_SCALEUNITS_PIXELS = 0xF1C0
AFX_IDS_STATUS_FONT = 0xF230
AFX_IDS_TOOLTIP_FONT = 0xF231
AFX_IDS_UNICODE_FONT = 0xF232
AFX_IDS_MINI_FONT = 0xF233
AFX_IDP_SQL_FIRST = 0xF280
AFX_IDP_SQL_CONNECT_FAIL = 0xF281
AFX_IDP_SQL_RECORDSET_FORWARD_ONLY = 0xF282
AFX_IDP_SQL_EMPTY_COLUMN_LIST = 0xF283
AFX_IDP_SQL_FIELD_SCHEMA_MISMATCH = 0xF284
AFX_IDP_SQL_ILLEGAL_MODE = 0xF285
AFX_IDP_SQL_MULTIPLE_ROWS_AFFECTED = 0xF286
AFX_IDP_SQL_NO_CURRENT_RECORD = 0xF287
AFX_IDP_SQL_NO_ROWS_AFFECTED = 0xF288
AFX_IDP_SQL_RECORDSET_READONLY = 0xF289
AFX_IDP_SQL_SQL_NO_TOTAL = 0xF28A
AFX_IDP_SQL_ODBC_LOAD_FAILED = 0xF28B
AFX_IDP_SQL_DYNASET_NOT_SUPPORTED = 0xF28C
AFX_IDP_SQL_SNAPSHOT_NOT_SUPPORTED = 0xF28D
AFX_IDP_SQL_API_CONFORMANCE = 0xF28E
AFX_IDP_SQL_SQL_CONFORMANCE = 0xF28F
AFX_IDP_SQL_NO_DATA_FOUND = 0xF290
AFX_IDP_SQL_ROW_UPDATE_NOT_SUPPORTED = 0xF291
AFX_IDP_SQL_ODBC_V2_REQUIRED = 0xF292
AFX_IDP_SQL_NO_POSITIONED_UPDATES = 0xF293
AFX_IDP_SQL_LOCK_MODE_NOT_SUPPORTED = 0xF294
AFX_IDP_SQL_DATA_TRUNCATED = 0xF295
AFX_IDP_SQL_ROW_FETCH = 0xF296
AFX_IDP_SQL_INCORRECT_ODBC = 0xF297
AFX_IDP_SQL_UPDATE_DELETE_FAILED = 0xF298
AFX_IDP_SQL_DYNAMIC_CURSOR_NOT_SUPPORTED = 0xF299
AFX_IDP_DAO_FIRST = 0xF2A0
AFX_IDP_DAO_ENGINE_INITIALIZATION = 0xF2A0
AFX_IDP_DAO_DFX_BIND = 0xF2A1
AFX_IDP_DAO_OBJECT_NOT_OPEN = 0xF2A2
AFX_IDP_DAO_ROWTOOSHORT = 0xF2A3
AFX_IDP_DAO_BADBINDINFO = 0xF2A4
AFX_IDP_DAO_COLUMNUNAVAILABLE = 0xF2A5
AFX_IDC_LISTBOX = 100
AFX_IDC_CHANGE = 101
AFX_IDC_PRINT_DOCNAME = 201
AFX_IDC_PRINT_PRINTERNAME = 202
AFX_IDC_PRINT_PORTNAME = 203
AFX_IDC_PRINT_PAGENUM = 204
ID_APPLY_NOW = 0x3021
ID_WIZBACK = 0x3023
ID_WIZNEXT = 0x3024
ID_WIZFINISH = 0x3025
AFX_IDC_TAB_CONTROL = 0x3020
AFX_IDD_FILEOPEN = 28676
AFX_IDD_FILESAVE = 28677
AFX_IDD_FONT = 28678
AFX_IDD_COLOR = 28679
AFX_IDD_PRINT = 28680
AFX_IDD_PRINTSETUP = 28681
AFX_IDD_FIND = 28682
AFX_IDD_REPLACE = 28683
AFX_IDD_NEWTYPEDLG = 30721
AFX_IDD_PRINTDLG = 30722
AFX_IDD_PREVIEW_TOOLBAR = 30723
AFX_IDD_PREVIEW_SHORTTOOLBAR = 30731
AFX_IDD_INSERTOBJECT = 30724
AFX_IDD_CHANGEICON = 30725
AFX_IDD_CONVERT = 30726
AFX_IDD_PASTESPECIAL = 30727
AFX_IDD_EDITLINKS = 30728
AFX_IDD_FILEBROWSE = 30729
AFX_IDD_BUSY = 30730
AFX_IDD_OBJECTPROPERTIES = 30732
AFX_IDD_CHANGESOURCE = 30733
AFX_IDC_CONTEXTHELP = 30977
AFX_IDC_MAGNIFY = 30978
AFX_IDC_SMALLARROWS = 30979
AFX_IDC_HSPLITBAR = 30980
AFX_IDC_VSPLITBAR = 30981
AFX_IDC_NODROPCRSR = 30982
AFX_IDC_TRACKNWSE = 30983
AFX_IDC_TRACKNESW = 30984
AFX_IDC_TRACKNS = 30985
AFX_IDC_TRACKWE = 30986
AFX_IDC_TRACK4WAY = 30987
AFX_IDC_MOVE4WAY = 30988
AFX_IDB_MINIFRAME_MENU = 30994
AFX_IDB_CHECKLISTBOX_NT = 30995
AFX_IDB_CHECKLISTBOX_95 = 30996
AFX_IDR_PREVIEW_ACCEL = 30997
AFX_IDI_STD_MDIFRAME = 31233
AFX_IDI_STD_FRAME = 31234
AFX_IDC_FONTPROP = 1000
AFX_IDC_FONTNAMES = 1001
AFX_IDC_FONTSTYLES = 1002
AFX_IDC_FONTSIZES = 1003
AFX_IDC_STRIKEOUT = 1004
AFX_IDC_UNDERLINE = 1005
AFX_IDC_SAMPLEBOX = 1006
AFX_IDC_COLOR_BLACK = 1100
AFX_IDC_COLOR_WHITE = 1101
AFX_IDC_COLOR_RED = 1102
AFX_IDC_COLOR_GREEN = 1103
AFX_IDC_COLOR_BLUE = 1104
AFX_IDC_COLOR_YELLOW = 1105
AFX_IDC_COLOR_MAGENTA = 1106
AFX_IDC_COLOR_CYAN = 1107
AFX_IDC_COLOR_GRAY = 1108
AFX_IDC_COLOR_LIGHTGRAY = 1109
AFX_IDC_COLOR_DARKRED = 1110
AFX_IDC_COLOR_DARKGREEN = 1111
AFX_IDC_COLOR_DARKBLUE = 1112
AFX_IDC_COLOR_LIGHTBROWN = 1113
AFX_IDC_COLOR_DARKMAGENTA = 1114
AFX_IDC_COLOR_DARKCYAN = 1115
AFX_IDC_COLORPROP = 1116
AFX_IDC_SYSTEMCOLORS = 1117
AFX_IDC_PROPNAME = 1201
AFX_IDC_PICTURE = 1202
AFX_IDC_BROWSE = 1203
AFX_IDC_CLEAR = 1204
AFX_IDD_PROPPAGE_COLOR = 32257
AFX_IDD_PROPPAGE_FONT = 32258
AFX_IDD_PROPPAGE_PICTURE = 32259
AFX_IDB_TRUETYPE = 32384
AFX_IDS_PROPPAGE_UNKNOWN = 0xFE01
AFX_IDS_COLOR_DESKTOP = 0xFE04
AFX_IDS_COLOR_APPWORKSPACE = 0xFE05
AFX_IDS_COLOR_WNDBACKGND = 0xFE06
AFX_IDS_COLOR_WNDTEXT = 0xFE07
AFX_IDS_COLOR_MENUBAR = 0xFE08
AFX_IDS_COLOR_MENUTEXT = 0xFE09
AFX_IDS_COLOR_ACTIVEBAR = 0xFE0A
AFX_IDS_COLOR_INACTIVEBAR = 0xFE0B
AFX_IDS_COLOR_ACTIVETEXT = 0xFE0C
AFX_IDS_COLOR_INACTIVETEXT = 0xFE0D
AFX_IDS_COLOR_ACTIVEBORDER = 0xFE0E
AFX_IDS_COLOR_INACTIVEBORDER = 0xFE0F
AFX_IDS_COLOR_WNDFRAME = 0xFE10
AFX_IDS_COLOR_SCROLLBARS = 0xFE11
AFX_IDS_COLOR_BTNFACE = 0xFE12
AFX_IDS_COLOR_BTNSHADOW = 0xFE13
AFX_IDS_COLOR_BTNTEXT = 0xFE14
AFX_IDS_COLOR_BTNHIGHLIGHT = 0xFE15
AFX_IDS_COLOR_DISABLEDTEXT = 0xFE16
AFX_IDS_COLOR_HIGHLIGHT = 0xFE17
AFX_IDS_COLOR_HIGHLIGHTTEXT = 0xFE18
AFX_IDS_REGULAR = 0xFE19
AFX_IDS_BOLD = 0xFE1A
AFX_IDS_ITALIC = 0xFE1B
AFX_IDS_BOLDITALIC = 0xFE1C
AFX_IDS_SAMPLETEXT = 0xFE1D
AFX_IDS_DISPLAYSTRING_FONT = 0xFE1E
AFX_IDS_DISPLAYSTRING_COLOR = 0xFE1F
AFX_IDS_DISPLAYSTRING_PICTURE = 0xFE20
AFX_IDS_PICTUREFILTER = 0xFE21
AFX_IDS_PICTYPE_UNKNOWN = 0xFE22
AFX_IDS_PICTYPE_NONE = 0xFE23
AFX_IDS_PICTYPE_BITMAP = 0xFE24
AFX_IDS_PICTYPE_METAFILE = 0xFE25
AFX_IDS_PICTYPE_ICON = 0xFE26
AFX_IDS_COLOR_PPG = 0xFE28
AFX_IDS_COLOR_PPG_CAPTION = 0xFE29
AFX_IDS_FONT_PPG = 0xFE2A
AFX_IDS_FONT_PPG_CAPTION = 0xFE2B
AFX_IDS_PICTURE_PPG = 0xFE2C
AFX_IDS_PICTURE_PPG_CAPTION = 0xFE2D
AFX_IDS_PICTUREBROWSETITLE = 0xFE30
AFX_IDS_BORDERSTYLE_0 = 0xFE31
AFX_IDS_BORDERSTYLE_1 = 0xFE32
AFX_IDS_VERB_EDIT = 0xFE40
AFX_IDS_VERB_PROPERTIES = 0xFE41
AFX_IDP_PICTURECANTOPEN = 0xFE83
AFX_IDP_PICTURECANTLOAD = 0xFE84
AFX_IDP_PICTURETOOLARGE = 0xFE85
AFX_IDP_PICTUREREADFAILED = 0xFE86
AFX_IDP_E_ILLEGALFUNCTIONCALL = 0xFEA0
AFX_IDP_E_OVERFLOW = 0xFEA1
AFX_IDP_E_OUTOFMEMORY = 0xFEA2
AFX_IDP_E_DIVISIONBYZERO = 0xFEA3
AFX_IDP_E_OUTOFSTRINGSPACE = 0xFEA4
AFX_IDP_E_OUTOFSTACKSPACE = 0xFEA5
AFX_IDP_E_BADFILENAMEORNUMBER = 0xFEA6
AFX_IDP_E_FILENOTFOUND = 0xFEA7
AFX_IDP_E_BADFILEMODE = 0xFEA8
AFX_IDP_E_FILEALREADYOPEN = 0xFEA9
AFX_IDP_E_DEVICEIOERROR = 0xFEAA
AFX_IDP_E_FILEALREADYEXISTS = 0xFEAB
AFX_IDP_E_BADRECORDLENGTH = 0xFEAC
AFX_IDP_E_DISKFULL = 0xFEAD
AFX_IDP_E_BADRECORDNUMBER = 0xFEAE
AFX_IDP_E_BADFILENAME = 0xFEAF
AFX_IDP_E_TOOMANYFILES = 0xFEB0
AFX_IDP_E_DEVICEUNAVAILABLE = 0xFEB1
AFX_IDP_E_PERMISSIONDENIED = 0xFEB2
AFX_IDP_E_DISKNOTREADY = 0xFEB3
AFX_IDP_E_PATHFILEACCESSERROR = 0xFEB4
AFX_IDP_E_PATHNOTFOUND = 0xFEB5
AFX_IDP_E_INVALIDPATTERNSTRING = 0xFEB6
AFX_IDP_E_INVALIDUSEOFNULL = 0xFEB7
AFX_IDP_E_INVALIDFILEFORMAT = 0xFEB8
AFX_IDP_E_INVALIDPROPERTYVALUE = 0xFEB9
AFX_IDP_E_INVALIDPROPERTYARRAYINDEX = 0xFEBA
AFX_IDP_E_SETNOTSUPPORTEDATRUNTIME = 0xFEBB
AFX_IDP_E_SETNOTSUPPORTED = 0xFEBC
AFX_IDP_E_NEEDPROPERTYARRAYINDEX = 0xFEBD
AFX_IDP_E_SETNOTPERMITTED = 0xFEBE
AFX_IDP_E_GETNOTSUPPORTEDATRUNTIME = 0xFEBF
AFX_IDP_E_GETNOTSUPPORTED = 0xFEC0
AFX_IDP_E_PROPERTYNOTFOUND = 0xFEC1
AFX_IDP_E_INVALIDCLIPBOARDFORMAT = 0xFEC2
AFX_IDP_E_INVALIDPICTURE = 0xFEC3
AFX_IDP_E_PRINTERERROR = 0xFEC4
AFX_IDP_E_CANTSAVEFILETOTEMP = 0xFEC5
AFX_IDP_E_SEARCHTEXTNOTFOUND = 0xFEC6
AFX_IDP_E_REPLACEMENTSTOOLONG = 0xFEC7

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\zipp\__init__.py ===
import io
import posixpath
import zipfile
import itertools
import contextlib
import pathlib
import re
import stat
import sys

from .compat.py310 import text_encoding
from .glob import Translator


__all__ = ['Path']


def _parents(path):
    """
    Given a path with elements separated by
    posixpath.sep, generate all parents of that path.

    >>> list(_parents('b/d'))
    ['b']
    >>> list(_parents('/b/d/'))
    ['/b']
    >>> list(_parents('b/d/f/'))
    ['b/d', 'b']
    >>> list(_parents('b'))
    []
    >>> list(_parents(''))
    []
    """
    return itertools.islice(_ancestry(path), 1, None)


def _ancestry(path):
    """
    Given a path with elements separated by
    posixpath.sep, generate all elements of that path

    >>> list(_ancestry('b/d'))
    ['b/d', 'b']
    >>> list(_ancestry('/b/d/'))
    ['/b/d', '/b']
    >>> list(_ancestry('b/d/f/'))
    ['b/d/f', 'b/d', 'b']
    >>> list(_ancestry('b'))
    ['b']
    >>> list(_ancestry(''))
    []
    """
    path = path.rstrip(posixpath.sep)
    while path and path != posixpath.sep:
        yield path
        path, tail = posixpath.split(path)


_dedupe = dict.fromkeys
"""Deduplicate an iterable in original order"""


def _difference(minuend, subtrahend):
    """
    Return items in minuend not in subtrahend, retaining order
    with O(1) lookup.
    """
    return itertools.filterfalse(set(subtrahend).__contains__, minuend)


class InitializedState:
    """
    Mix-in to save the initialization state for pickling.
    """

    def __init__(self, *args, **kwargs):
        self.__args = args
        self.__kwargs = kwargs
        super().__init__(*args, **kwargs)

    def __getstate__(self):
        return self.__args, self.__kwargs

    def __setstate__(self, state):
        args, kwargs = state
        super().__init__(*args, **kwargs)


class SanitizedNames:
    """
    ZipFile mix-in to ensure names are sanitized.
    """

    def namelist(self):
        return list(map(self._sanitize, super().namelist()))

    @staticmethod
    def _sanitize(name):
        r"""
        Ensure a relative path with posix separators and no dot names.

        Modeled after
        https://github.com/python/cpython/blob/bcc1be39cb1d04ad9fc0bd1b9193d3972835a57c/Lib/zipfile/__init__.py#L1799-L1813
        but provides consistent cross-platform behavior.

        >>> san = SanitizedNames._sanitize
        >>> san('/foo/bar')
        'foo/bar'
        >>> san('//foo.txt')
        'foo.txt'
        >>> san('foo/.././bar.txt')
        'foo/bar.txt'
        >>> san('foo../.bar.txt')
        'foo../.bar.txt'
        >>> san('\\foo\\bar.txt')
        'foo/bar.txt'
        >>> san('D:\\foo.txt')
        'D/foo.txt'
        >>> san('\\\\server\\share\\file.txt')
        'server/share/file.txt'
        >>> san('\\\\?\\GLOBALROOT\\Volume3')
        '?/GLOBALROOT/Volume3'
        >>> san('\\\\.\\PhysicalDrive1\\root')
        'PhysicalDrive1/root'

        Retain any trailing slash.
        >>> san('abc/')
        'abc/'

        Raises a ValueError if the result is empty.
        >>> san('../..')
        Traceback (most recent call last):
        ...
        ValueError: Empty filename
        """

        def allowed(part):
            return part and part not in {'..', '.'}

        # Remove the drive letter.
        # Don't use ntpath.splitdrive, because that also strips UNC paths
        bare = re.sub('^([A-Z]):', r'\1', name, flags=re.IGNORECASE)
        clean = bare.replace('\\', '/')
        parts = clean.split('/')
        joined = '/'.join(filter(allowed, parts))
        if not joined:
            raise ValueError("Empty filename")
        return joined + '/' * name.endswith('/')


class CompleteDirs(InitializedState, SanitizedNames, zipfile.ZipFile):
    """
    A ZipFile subclass that ensures that implied directories
    are always included in the namelist.

    >>> list(CompleteDirs._implied_dirs(['foo/bar.txt', 'foo/bar/baz.txt']))
    ['foo/', 'foo/bar/']
    >>> list(CompleteDirs._implied_dirs(['foo/bar.txt', 'foo/bar/baz.txt', 'foo/bar/']))
    ['foo/']
    """

    @staticmethod
    def _implied_dirs(names):
        parents = itertools.chain.from_iterable(map(_parents, names))
        as_dirs = (p + posixpath.sep for p in parents)
        return _dedupe(_difference(as_dirs, names))

    def namelist(self):
        names = super().namelist()
        return names + list(self._implied_dirs(names))

    def _name_set(self):
        return set(self.namelist())

    def resolve_dir(self, name):
        """
        If the name represents a directory, return that name
        as a directory (with the trailing slash).
        """
        names = self._name_set()
        dirname = name + '/'
        dir_match = name not in names and dirname in names
        return dirname if dir_match else name

    def getinfo(self, name):
        """
        Supplement getinfo for implied dirs.
        """
        try:
            return super().getinfo(name)
        except KeyError:
            if not name.endswith('/') or name not in self._name_set():
                raise
            return zipfile.ZipInfo(filename=name)

    @classmethod
    def make(cls, source):
        """
        Given a source (filename or zipfile), return an
        appropriate CompleteDirs subclass.
        """
        if isinstance(source, CompleteDirs):
            return source

        if not isinstance(source, zipfile.ZipFile):
            return cls(source)

        # Only allow for FastLookup when supplied zipfile is read-only
        if 'r' not in source.mode:
            cls = CompleteDirs

        source.__class__ = cls
        return source

    @classmethod
    def inject(cls, zf: zipfile.ZipFile) -> zipfile.ZipFile:
        """
        Given a writable zip file zf, inject directory entries for
        any directories implied by the presence of children.
        """
        for name in cls._implied_dirs(zf.namelist()):
            zf.writestr(name, b"")
        return zf


class FastLookup(CompleteDirs):
    """
    ZipFile subclass to ensure implicit
    dirs exist and are resolved rapidly.
    """

    def namelist(self):
        with contextlib.suppress(AttributeError):
            return self.__names
        self.__names = super().namelist()
        return self.__names

    def _name_set(self):
        with contextlib.suppress(AttributeError):
            return self.__lookup
        self.__lookup = super()._name_set()
        return self.__lookup


def _extract_text_encoding(encoding=None, *args, **kwargs):
    # compute stack level so that the caller of the caller sees any warning.
    is_pypy = sys.implementation.name == 'pypy'
    stack_level = 3 + is_pypy
    return text_encoding(encoding, stack_level), args, kwargs


class Path:
    """
    A :class:`importlib.resources.abc.Traversable` interface for zip files.

    Implements many of the features users enjoy from
    :class:`pathlib.Path`.

    Consider a zip file with this structure::

        .
        ├── a.txt
        └── b
            ├── c.txt
            └── d
                └── e.txt

    >>> data = io.BytesIO()
    >>> zf = zipfile.ZipFile(data, 'w')
    >>> zf.writestr('a.txt', 'content of a')
    >>> zf.writestr('b/c.txt', 'content of c')
    >>> zf.writestr('b/d/e.txt', 'content of e')
    >>> zf.filename = 'mem/abcde.zip'

    Path accepts the zipfile object itself or a filename

    >>> path = Path(zf)

    From there, several path operations are available.

    Directory iteration (including the zip file itself):

    >>> a, b = path.iterdir()
    >>> a
    Path('mem/abcde.zip', 'a.txt')
    >>> b
    Path('mem/abcde.zip', 'b/')

    name property:

    >>> b.name
    'b'

    join with divide operator:

    >>> c = b / 'c.txt'
    >>> c
    Path('mem/abcde.zip', 'b/c.txt')
    >>> c.name
    'c.txt'

    Read text:

    >>> c.read_text(encoding='utf-8')
    'content of c'

    existence:

    >>> c.exists()
    True
    >>> (b / 'missing.txt').exists()
    False

    Coercion to string:

    >>> import os
    >>> str(c).replace(os.sep, posixpath.sep)
    'mem/abcde.zip/b/c.txt'

    At the root, ``name``, ``filename``, and ``parent``
    resolve to the zipfile.

    >>> str(path)
    'mem/abcde.zip/'
    >>> path.name
    'abcde.zip'
    >>> path.filename == pathlib.Path('mem/abcde.zip')
    True
    >>> str(path.parent)
    'mem'

    If the zipfile has no filename, such ﻿attributes are not
    valid and accessing them will raise an Exception.

    >>> zf.filename = None
    >>> path.name
    Traceback (most recent call last):
    ...
    TypeError: ...

    >>> path.filename
    Traceback (most recent call last):
    ...
    TypeError: ...

    >>> path.parent
    Traceback (most recent call last):
    ...
    TypeError: ...

    # workaround python/cpython#106763
    >>> pass
    """

    __repr = "{self.__class__.__name__}({self.root.filename!r}, {self.at!r})"

    def __init__(self, root, at=""):
        """
        Construct a Path from a ZipFile or filename.

        Note: When the source is an existing ZipFile object,
        its type (__class__) will be mutated to a
        specialized type. If the caller wishes to retain the
        original type, the caller should either create a
        separate ZipFile object or pass a filename.
        """
        self.root = FastLookup.make(root)
        self.at = at

    def __eq__(self, other):
        """
        >>> Path(zipfile.ZipFile(io.BytesIO(), 'w')) == 'foo'
        False
        """
        if self.__class__ is not other.__class__:
            return NotImplemented
        return (self.root, self.at) == (other.root, other.at)

    def __hash__(self):
        return hash((self.root, self.at))

    def open(self, mode='r', *args, pwd=None, **kwargs):
        """
        Open this entry as text or binary following the semantics
        of ``pathlib.Path.open()`` by passing arguments through
        to io.TextIOWrapper().
        """
        if self.is_dir():
            raise IsADirectoryError(self)
        zip_mode = mode[0]
        if not self.exists() and zip_mode == 'r':
            raise FileNotFoundError(self)
        stream = self.root.open(self.at, zip_mode, pwd=pwd)
        if 'b' in mode:
            if args or kwargs:
                raise ValueError("encoding args invalid for binary operation")
            return stream
        # Text mode:
        encoding, args, kwargs = _extract_text_encoding(*args, **kwargs)
        return io.TextIOWrapper(stream, encoding, *args, **kwargs)

    def _base(self):
        return pathlib.PurePosixPath(self.at or self.root.filename)

    @property
    def name(self):
        return self._base().name

    @property
    def suffix(self):
        return self._base().suffix

    @property
    def suffixes(self):
        return self._base().suffixes

    @property
    def stem(self):
        return self._base().stem

    @property
    def filename(self):
        return pathlib.Path(self.root.filename).joinpath(self.at)

    def read_text(self, *args, **kwargs):
        encoding, args, kwargs = _extract_text_encoding(*args, **kwargs)
        with self.open('r', encoding, *args, **kwargs) as strm:
            return strm.read()

    def read_bytes(self):
        with self.open('rb') as strm:
            return strm.read()

    def _is_child(self, path):
        return posixpath.dirname(path.at.rstrip("/")) == self.at.rstrip("/")

    def _next(self, at):
        return self.__class__(self.root, at)

    def is_dir(self):
        return not self.at or self.at.endswith("/")

    def is_file(self):
        return self.exists() and not self.is_dir()

    def exists(self):
        return self.at in self.root._name_set()

    def iterdir(self):
        if not self.is_dir():
            raise ValueError("Can't listdir a file")
        subs = map(self._next, self.root.namelist())
        return filter(self._is_child, subs)

    def match(self, path_pattern):
        return pathlib.PurePosixPath(self.at).match(path_pattern)

    def is_symlink(self):
        """
        Return whether this path is a symlink.
        """
        info = self.root.getinfo(self.at)
        mode = info.external_attr >> 16
        return stat.S_ISLNK(mode)

    def glob(self, pattern):
        if not pattern:
            raise ValueError(f"Unacceptable pattern: {pattern!r}")

        prefix = re.escape(self.at)
        tr = Translator(seps='/')
        matches = re.compile(prefix + tr.translate(pattern)).fullmatch
        names = (data.filename for data in self.root.filelist)
        return map(self._next, filter(matches, names))

    def rglob(self, pattern):
        return self.glob(f'**/{pattern}')

    def relative_to(self, other, *extra):
        return posixpath.relpath(str(self), str(other.joinpath(*extra)))

    def __str__(self):
        return posixpath.join(self.root.filename, self.at)

    def __repr__(self):
        return self.__repr.format(self=self)

    def joinpath(self, *other):
        next = posixpath.join(self.at, *other)
        return self._next(self.root.resolve_dir(next))

    __truediv__ = joinpath

    @property
    def parent(self):
        if not self.at:
            return self.filename.parent
        parent_at = posixpath.dirname(self.at.rstrip('/'))
        if parent_at:
            parent_at += '/'
        return self._next(parent_at)

# === NexusCore/evaluation\evalplus\evalplus\_experimental\type_mut_for_eff.py ===
import copy
import math
import random
import string
from typing import Any, Dict, List, Optional, Set, Tuple

from multipledispatch import dispatch
from rich.progress import track

from evalplus._experimental.evaluate_runtime import (
    MAX_WARMUP_LIMIT,
    RUN_REPEAT,
    execute_for_runtime,
)
from evalplus.gen.mut_gen import MutateGen

MUTATE_BOUND_SIZE = 5
MAX_MULTI_STEP_SIZE = 1000
MAX_SEED_POOL = 10

NoneType = type(None)
MAX_SIZE = 80000
VALUE_MAX = 1000000


# decorator to use ingredients
class use_ingredient:
    def __init__(self, prob: float):
        assert 0 <= prob <= 0.95
        self.prob = prob

    def __call__(obj, func):
        def wrapper(self, seed_input):
            if random.random() < obj.prob and self.ingredients[type(seed_input)]:
                return random.choice(list(self.ingredients[type(seed_input)]))
            else:
                return func(self, seed_input)

        return wrapper


class TestInput:
    def __init__(self, inputs: List, runtime: float, sd: float):
        self.inputs = inputs
        self.sz = self.typed_size(inputs)
        self.runtime = runtime
        self.sd = sd
        self.rank_sd = self.rank_sz = 1

    def __str__(self):
        return str(self.inputs)

    @property
    def fluctuate_ratio(self) -> float:
        return self.sd / self.runtime * 100

    @property
    def rank(self) -> float:
        return self.rank_sd * (self.rank_sz**0.8) if self.sz <= 2000 else self.rank_sd

    @dispatch(NoneType)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(int)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(float)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(bool)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(str)
    def typed_size(self, s: str) -> int:
        return len(s)

    @dispatch(list)
    def typed_size(self, l: list) -> int:
        return sum(self.typed_size(x) for x in l)

    @dispatch(tuple)
    def typed_size(self, t: tuple) -> int:
        return sum(self.typed_size(x) for x in t)

    @dispatch(set)
    def typed_size(self, s: set) -> int:
        return sum(self.typed_size(x) for x in s)

    @dispatch(dict)
    def typed_size(self, d: dict) -> int:
        return sum(self.typed_size(x) for x in d.items())


class TypedMutEffGen(MutateGen):
    def __init__(self, inputs: List, signature: str, contract_code: str):
        super().__init__(inputs, signature, contract_code)

        self.base_inputs = copy.deepcopy(inputs)
        self.seed_pool: List[TestInput] = []
        self.seed_hash: Set[str] = set()
        for base_input in self.base_inputs:
            avg, sd = self.test_efficiency(base_input)
            assert avg != None and sd != None, "base inputs not correct"
            self.insert_input(TestInput(base_input, avg, sd))
            self.seed_hash.add(hash(str(base_input)))

        self.ingredients = {
            int: set(),
            float: set(),
            str: set(),
        }
        for x in inputs:
            self.fetch_ingredient(x)

    def insert_input(self, new_input: TestInput):
        new_input_hash = hash(str(new_input))
        if new_input_hash in self.seed_hash:
            return
        self.seed_pool.append(new_input)
        self.seed_pool.sort(key=lambda x: x.fluctuate_ratio)
        self.seed_hash.add(new_input_hash)

        if len(self.seed_pool) > MAX_SEED_POOL:
            self.seed_pool.sort(key=lambda x: x.fluctuate_ratio)
            for i in range(len(self.seed_pool)):
                self.seed_pool[i].rank_sd = i + 1
            self.seed_pool.sort(key=lambda x: -x.sz)
            for i in range(len(self.seed_pool)):
                self.seed_pool[i].rank_sz = i + 1
            self.seed_pool.sort(key=lambda x: x.rank)
            seed_deleted = self.seed_pool[-1]
            self.seed_hash.remove(hash(str(seed_deleted)))
            self.seed_pool = self.seed_pool[:-1]

    def test_efficiency(self, new_input: List) -> Tuple[Optional[float]]:
        warmups = []
        new_input_hash = hash(str(new_input))
        for input_list in self.base_inputs:
            if (
                len(warmups) < MAX_WARMUP_LIMIT
                and hash(str(input_list)) != new_input_hash
            ):
                warmups.append(input_list)
        runtime_list = [
            execute_for_runtime(self.contract_code, new_input, warmups, self.signature)
            for _ in range(RUN_REPEAT)
        ]
        if any(type(x) != float for x in runtime_list):
            return None, None
        avg = sum(runtime_list) / RUN_REPEAT
        sd = math.sqrt(sum((t - avg) ** 2 for t in runtime_list) / (RUN_REPEAT - 1))
        return avg, sd

    #########################
    # Type-aware generation #
    #########################
    @dispatch(NoneType)
    def typed_gen(self, _):
        return None

    @dispatch(int)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.randint(-VALUE_MAX, VALUE_MAX)

        return _impl(self, _)

    @dispatch(float)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.uniform(-VALUE_MAX, VALUE_MAX)

        return _impl(self, _)

    @dispatch(bool)
    def typed_gen(self, _):
        return random.choice([True, False])

    @dispatch(str)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return "".join(
                random.choice(string.ascii_letters)
                for _ in range(random.randint(0, 10))
            )

        return _impl(self, _)

    def any_gen(self):
        # weighted choose
        choice = random.choices(
            [
                True,
                1,
                1.1,
                "str",
                [],  # list
                tuple(),  # tuple
                dict(),  # dict
                None,  # None
            ],
            [0.2, 0.2, 0.2, 0.2, 0.05, 0.05, 0.05, 0.05],
        )[0]
        return self.typed_gen(choice)

    @dispatch(list)
    def typed_gen(self, _):
        ret = []
        size = random.randint(0, 10)
        if random.randint(0, 4) == 0:  # heterogeneous
            for _ in range(size):
                ret.append(self.any_gen())
        else:  # homogeneous
            t = random.choice([bool(), int(), float(), str()])
            for _ in range(size):
                ret.append(self.typed_gen(t))
        return ret

    @dispatch(tuple)
    def typed_gen(self, _):
        return tuple(self.typed_gen([]))

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_gen(self, _):
    #     return set(self.typed_gen([]))

    @dispatch(dict)
    def typed_gen(self, _):
        ret = dict()
        values = self.typed_gen([])
        # NOTE: Assumption: nobody uses dict with heterogeneous keys
        # NOTE: Assumption: nobody uses dict with boolean keys
        key_type = random.choice([int(), float(), str()])
        for v in values:
            ret[self.typed_gen(key_type)] = self.typed_gen(v)
        return ret

    ########################
    # Type-aware mutation  #
    ########################
    # Simple primitives
    @dispatch(int)
    def typed_mutate(self, seed_input: int):
        @use_ingredient(0.1)
        def _impl(_, seed_input: int):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.2:
                return seed_input * 2
            elif 0.2 <= prob < 0.9:
                return random.randint(-VALUE_MAX, VALUE_MAX)
            else:
                return seed_input + 5

        return _impl(self, seed_input)

    @dispatch(float)
    def typed_mutate(self, seed_input: float):
        @use_ingredient(0.1)
        def _impl(_, seed_input: float):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.2:
                return seed_input * (2 + random.uniform(-0.5, 0.5))
            elif 0.2 <= prob < 0.9:
                return random.uniform(-VALUE_MAX, VALUE_MAX)
            else:
                return seed_input + 5.0

        return _impl(self, seed_input)

    @dispatch(bool)
    def typed_mutate(self, seed_input: bool):
        return random.choice([True, False])

    @dispatch(NoneType)
    def typed_mutate(self, seed_input: NoneType):
        return None

    # List-like
    @dispatch(list)
    def typed_mutate(self, seed_input: List):
        if len(seed_input) == 0:
            return self.typed_gen([])

        choice = random.randint(1, 3)
        idx = random.randint(0, len(seed_input) - 1)
        if choice == 1 and 0 < len(seed_input) < MAX_SIZE:  # length *= 1.1
            old_length = len(seed_input)
            new_length = math.ceil(old_length * 1.1)
            for _ in range(new_length - old_length):
                seed_input.insert(
                    random.randint(0, len(seed_input) - 1),
                    self.typed_mutate(seed_input[idx]),
                )
        elif choice == 2 and 0 < len(seed_input) < MAX_SIZE:  # repeat, length *= 1.1
            old_length = len(seed_input)
            new_length = math.ceil(old_length * 1.1)
            for _ in range(new_length - old_length):
                seed_input.append(seed_input[idx])
        else:  # inplace element change, large_scale
            for idx in range(len(seed_input)):
                if random.uniform(0, 1) > 0.7:
                    seed_input[idx] = self.typed_mutate(seed_input[idx])
        return seed_input

    @dispatch(tuple)
    def typed_mutate(self, seed_input: Tuple):
        return tuple(self.typed_mutate(list(seed_input)))

    # String
    @dispatch(str)
    def typed_mutate(self, seed_input: str):
        @use_ingredient(0.1)
        def _impl(_, seed_input: str):
            choice = random.randint(0, 2) if seed_input else 0
            if (
                choice <= 1 and self.ingredients[str]
            ):  # insert ingredients, length *= 1.1
                new_length = math.ceil(len(seed_input) * 1.1)
                while len(seed_input) < new_length:
                    idx = random.randint(0, len(seed_input))
                    seed_input = (
                        seed_input[:idx]
                        + random.choice(list(self.ingredients[str]))
                        + seed_input[idx:]
                    )
                return seed_input
            # other choices assume len(seed_input) > 0
            elif choice == 2:  # inplace mutation, large_scale
                ch_list = []
                for i in range(len(seed_input)):
                    if random.uniform(0, 1) > 0.7:
                        ch_list.append(random.choice(string.ascii_letters))
                    else:
                        ch_list.append(seed_input[i])
                return "".join(ch_list)

            # random char
            return self.typed_gen(str())

        return _impl(self, seed_input)

    # Set
    @dispatch(set)
    def typed_mutate(self, seed_input: Set):
        return set(self.typed_mutate(list(seed_input)))

    # Dict
    @dispatch(dict)
    def typed_mutate(self, seed_input: Dict):
        if len(seed_input) == 0:
            return self.typed_gen(dict())

        choice = random.randint(1, 2)
        if choice == 1:  # add a kv
            k = self.typed_mutate(random.choice(list(seed_input.keys())))
            v = self.typed_mutate(random.choice(list(seed_input.values())))
            seed_input[k] = v
        elif choice == 2:  # inplace value change
            k0, v0 = random.choice(list(seed_input.items()))
            seed_input[k0] = self.typed_mutate(v0)
        return seed_input

    ############################################
    # Fetching ingredients to self.ingredients #
    ############################################
    def fetch_ingredient(self, seed_input):
        self.typed_fetch(seed_input)

    @dispatch(int)
    def typed_fetch(self, seed_input: int):
        self.ingredients[int].add(seed_input)

    @dispatch(float)
    def typed_fetch(self, seed_input: float):
        self.ingredients[float].add(seed_input)

    @dispatch(str)
    def typed_fetch(self, seed_input: str):
        self.ingredients[str].add(seed_input)
        for token in seed_input.strip().split():
            self.ingredients[str].add(token)

    # List-like
    def _fetch_list_like(self, seed_input):
        for x in seed_input:
            if self.typed_fetch.dispatch(type(x)):
                self.fetch_ingredient(x)

    @dispatch(list)
    def typed_fetch(self, seed_input: List):
        self._fetch_list_like(seed_input)

    @dispatch(tuple)
    def typed_fetch(self, seed_input: Tuple):
        self._fetch_list_like(seed_input)

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_fetch(self, seed_input: Set):
    #     self._fetch_list_like(seed_input)

    # Dict
    @dispatch(dict)
    def typed_fetch(self, seed_input: Dict):
        self._fetch_list_like(seed_input.keys())
        self._fetch_list_like(seed_input.values())

    # Type-aware concatenation

    @dispatch(int, int)
    def concat(x: int, y: int):
        return x + y

    @dispatch(float, float)
    def concat(x: float, y: float):
        return x + y

    @dispatch(bool, bool)
    def concat(x: bool, y: bool):
        return random.choice([x, y])

    @dispatch(NoneType, NoneType)
    def concat(x: NoneType, y: NoneType):
        return None

    @dispatch(list, list)
    def concat(x: list, y: list):
        choice = random.randint(0, 1)
        return (
            copy.deepcopy(x) + copy.deepcopy(y)
            if choice == 0
            else copy.deepcopy(y) + copy.deepcopy(x)
        )

    @dispatch(str, str)
    def concat(x: str, y: str):
        choice = random.randint(0, 1)
        return x + y if choice == 0 else y + x

    @dispatch(set, set)
    def concat(x: set, y: set):
        return x.union(y)

    @dispatch(dict, dict)
    def concat(x: dict, y: dict):
        return x.update(y)

    def mutate(self, seed: TestInput) -> List[Any]:
        new_input = copy.deepcopy(seed.inputs)

        for _ in range(20):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.1 and seed.sz <= MAX_SIZE:
                another_seed = random.choice(self.seed_pool).inputs
                new_input = [
                    self.concat(new_input[i], another_seed[i])
                    for i in range(len(new_input))
                ]
            else:
                for i in range(len(new_input)):
                    new_input[i] = self.typed_mutate(new_input[i])

        return new_input

    def generate(self) -> List[TestInput]:
        for _ in track(range(40)):
            seed = self.seed_selection()
            new_input = self.mutate(seed)
            # print(len(new_input[0]))
            avg, sd = self.test_efficiency(new_input)
            if avg != None and sd != None:
                self.insert_input(TestInput(new_input, avg, sd))
        return self.seed_pool


if __name__ == "__main__":
    from evalplus.data import get_human_eval_plus

    problems = get_human_eval_plus()
    for p in problems[43:44]:
        inputs = p["base_input"]
        entry_point = p["entry_point"]
        contract = p["prompt"] + p["contract"] + p["canonical_solution"]
        gen = TypedMutEffGen(inputs, entry_point, contract)
        new_inputs = gen.generate()
        for i, new_input in enumerate(new_inputs):
            print(f"New input {i}: sz: {new_input.sz}")
            if new_input.sz <= 10:
                print(new_input.inputs)
            print(
                f"- Runtime: {new_input.runtime}, Sd: {new_input.sd}, Per: {new_input.fluctuate_ratio}"
            )

# === NexusCore/evaluation\evalplus\tools\_experimental\type_mut_for_eff.py ===
import copy
import math
import random
import string
from typing import Any, Dict, List, Optional, Set, Tuple

from multipledispatch import dispatch
from rich.progress import track

from evalplus._experimental.evaluate_runtime import (
    MAX_WARMUP_LIMIT,
    RUN_REPEAT,
    execute_for_runtime,
)
from evalplus.gen.mut_gen import MutateGen

MUTATE_BOUND_SIZE = 5
MAX_MULTI_STEP_SIZE = 1000
MAX_SEED_POOL = 10

NoneType = type(None)
MAX_SIZE = 80000
VALUE_MAX = 1000000


# decorator to use ingredients
class use_ingredient:
    def __init__(self, prob: float):
        assert 0 <= prob <= 0.95
        self.prob = prob

    def __call__(obj, func):
        def wrapper(self, seed_input):
            if random.random() < obj.prob and self.ingredients[type(seed_input)]:
                return random.choice(list(self.ingredients[type(seed_input)]))
            else:
                return func(self, seed_input)

        return wrapper


class TestInput:
    def __init__(self, inputs: List, runtime: float, sd: float):
        self.inputs = inputs
        self.sz = self.typed_size(inputs)
        self.runtime = runtime
        self.sd = sd
        self.rank_sd = self.rank_sz = 1

    def __str__(self):
        return str(self.inputs)

    @property
    def fluctuate_ratio(self) -> float:
        return self.sd / self.runtime * 100

    @property
    def rank(self) -> float:
        return self.rank_sd * (self.rank_sz**0.8) if self.sz <= 2000 else self.rank_sd

    @dispatch(NoneType)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(int)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(float)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(bool)
    def typed_size(self, _) -> int:
        return 1

    @dispatch(str)
    def typed_size(self, s: str) -> int:
        return len(s)

    @dispatch(list)
    def typed_size(self, l: list) -> int:
        return sum(self.typed_size(x) for x in l)

    @dispatch(tuple)
    def typed_size(self, t: tuple) -> int:
        return sum(self.typed_size(x) for x in t)

    @dispatch(set)
    def typed_size(self, s: set) -> int:
        return sum(self.typed_size(x) for x in s)

    @dispatch(dict)
    def typed_size(self, d: dict) -> int:
        return sum(self.typed_size(x) for x in d.items())


class TypedMutEffGen(MutateGen):
    def __init__(self, inputs: List, signature: str, contract_code: str):
        super().__init__(inputs, signature, contract_code)

        self.base_inputs = copy.deepcopy(inputs)
        self.seed_pool: List[TestInput] = []
        self.seed_hash: Set[str] = set()
        for base_input in self.base_inputs:
            avg, sd = self.test_efficiency(base_input)
            assert avg != None and sd != None, "base inputs not correct"
            self.insert_input(TestInput(base_input, avg, sd))
            self.seed_hash.add(hash(str(base_input)))

        self.ingredients = {
            int: set(),
            float: set(),
            str: set(),
        }
        for x in inputs:
            self.fetch_ingredient(x)

    def insert_input(self, new_input: TestInput):
        new_input_hash = hash(str(new_input))
        if new_input_hash in self.seed_hash:
            return
        self.seed_pool.append(new_input)
        self.seed_pool.sort(key=lambda x: x.fluctuate_ratio)
        self.seed_hash.add(new_input_hash)

        if len(self.seed_pool) > MAX_SEED_POOL:
            self.seed_pool.sort(key=lambda x: x.fluctuate_ratio)
            for i in range(len(self.seed_pool)):
                self.seed_pool[i].rank_sd = i + 1
            self.seed_pool.sort(key=lambda x: -x.sz)
            for i in range(len(self.seed_pool)):
                self.seed_pool[i].rank_sz = i + 1
            self.seed_pool.sort(key=lambda x: x.rank)
            seed_deleted = self.seed_pool[-1]
            self.seed_hash.remove(hash(str(seed_deleted)))
            self.seed_pool = self.seed_pool[:-1]

    def test_efficiency(self, new_input: List) -> Tuple[Optional[float]]:
        warmups = []
        new_input_hash = hash(str(new_input))
        for input_list in self.base_inputs:
            if (
                len(warmups) < MAX_WARMUP_LIMIT
                and hash(str(input_list)) != new_input_hash
            ):
                warmups.append(input_list)
        runtime_list = [
            execute_for_runtime(self.contract_code, new_input, warmups, self.signature)
            for _ in range(RUN_REPEAT)
        ]
        if any(type(x) != float for x in runtime_list):
            return None, None
        avg = sum(runtime_list) / RUN_REPEAT
        sd = math.sqrt(sum((t - avg) ** 2 for t in runtime_list) / (RUN_REPEAT - 1))
        return avg, sd

    #########################
    # Type-aware generation #
    #########################
    @dispatch(NoneType)
    def typed_gen(self, _):
        return None

    @dispatch(int)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.randint(-VALUE_MAX, VALUE_MAX)

        return _impl(self, _)

    @dispatch(float)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.uniform(-VALUE_MAX, VALUE_MAX)

        return _impl(self, _)

    @dispatch(bool)
    def typed_gen(self, _):
        return random.choice([True, False])

    @dispatch(str)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return "".join(
                random.choice(string.ascii_letters)
                for _ in range(random.randint(0, 10))
            )

        return _impl(self, _)

    def any_gen(self):
        # weighted choose
        choice = random.choices(
            [
                True,
                1,
                1.1,
                "str",
                [],  # list
                tuple(),  # tuple
                dict(),  # dict
                None,  # None
            ],
            [0.2, 0.2, 0.2, 0.2, 0.05, 0.05, 0.05, 0.05],
        )[0]
        return self.typed_gen(choice)

    @dispatch(list)
    def typed_gen(self, _):
        ret = []
        size = random.randint(0, 10)
        if random.randint(0, 4) == 0:  # heterogeneous
            for _ in range(size):
                ret.append(self.any_gen())
        else:  # homogeneous
            t = random.choice([bool(), int(), float(), str()])
            for _ in range(size):
                ret.append(self.typed_gen(t))
        return ret

    @dispatch(tuple)
    def typed_gen(self, _):
        return tuple(self.typed_gen([]))

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_gen(self, _):
    #     return set(self.typed_gen([]))

    @dispatch(dict)
    def typed_gen(self, _):
        ret = dict()
        values = self.typed_gen([])
        # NOTE: Assumption: nobody uses dict with heterogeneous keys
        # NOTE: Assumption: nobody uses dict with boolean keys
        key_type = random.choice([int(), float(), str()])
        for v in values:
            ret[self.typed_gen(key_type)] = self.typed_gen(v)
        return ret

    ########################
    # Type-aware mutation  #
    ########################
    # Simple primitives
    @dispatch(int)
    def typed_mutate(self, seed_input: int):
        @use_ingredient(0.1)
        def _impl(_, seed_input: int):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.2:
                return seed_input * 2
            elif 0.2 <= prob < 0.9:
                return random.randint(-VALUE_MAX, VALUE_MAX)
            else:
                return seed_input + 5

        return _impl(self, seed_input)

    @dispatch(float)
    def typed_mutate(self, seed_input: float):
        @use_ingredient(0.1)
        def _impl(_, seed_input: float):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.2:
                return seed_input * (2 + random.uniform(-0.5, 0.5))
            elif 0.2 <= prob < 0.9:
                return random.uniform(-VALUE_MAX, VALUE_MAX)
            else:
                return seed_input + 5.0

        return _impl(self, seed_input)

    @dispatch(bool)
    def typed_mutate(self, seed_input: bool):
        return random.choice([True, False])

    @dispatch(NoneType)
    def typed_mutate(self, seed_input: NoneType):
        return None

    # List-like
    @dispatch(list)
    def typed_mutate(self, seed_input: List):
        if len(seed_input) == 0:
            return self.typed_gen([])

        choice = random.randint(1, 3)
        idx = random.randint(0, len(seed_input) - 1)
        if choice == 1 and 0 < len(seed_input) < MAX_SIZE:  # length *= 1.1
            old_length = len(seed_input)
            new_length = math.ceil(old_length * 1.1)
            for _ in range(new_length - old_length):
                seed_input.insert(
                    random.randint(0, len(seed_input) - 1),
                    self.typed_mutate(seed_input[idx]),
                )
        elif choice == 2 and 0 < len(seed_input) < MAX_SIZE:  # repeat, length *= 1.1
            old_length = len(seed_input)
            new_length = math.ceil(old_length * 1.1)
            for _ in range(new_length - old_length):
                seed_input.append(seed_input[idx])
        else:  # inplace element change, large_scale
            for idx in range(len(seed_input)):
                if random.uniform(0, 1) > 0.7:
                    seed_input[idx] = self.typed_mutate(seed_input[idx])
        return seed_input

    @dispatch(tuple)
    def typed_mutate(self, seed_input: Tuple):
        return tuple(self.typed_mutate(list(seed_input)))

    # String
    @dispatch(str)
    def typed_mutate(self, seed_input: str):
        @use_ingredient(0.1)
        def _impl(_, seed_input: str):
            choice = random.randint(0, 2) if seed_input else 0
            if (
                choice <= 1 and self.ingredients[str]
            ):  # insert ingredients, length *= 1.1
                new_length = math.ceil(len(seed_input) * 1.1)
                while len(seed_input) < new_length:
                    idx = random.randint(0, len(seed_input))
                    seed_input = (
                        seed_input[:idx]
                        + random.choice(list(self.ingredients[str]))
                        + seed_input[idx:]
                    )
                return seed_input
            # other choices assume len(seed_input) > 0
            elif choice == 2:  # inplace mutation, large_scale
                ch_list = []
                for i in range(len(seed_input)):
                    if random.uniform(0, 1) > 0.7:
                        ch_list.append(random.choice(string.ascii_letters))
                    else:
                        ch_list.append(seed_input[i])
                return "".join(ch_list)

            # random char
            return self.typed_gen(str())

        return _impl(self, seed_input)

    # Set
    @dispatch(set)
    def typed_mutate(self, seed_input: Set):
        return set(self.typed_mutate(list(seed_input)))

    # Dict
    @dispatch(dict)
    def typed_mutate(self, seed_input: Dict):
        if len(seed_input) == 0:
            return self.typed_gen(dict())

        choice = random.randint(1, 2)
        if choice == 1:  # add a kv
            k = self.typed_mutate(random.choice(list(seed_input.keys())))
            v = self.typed_mutate(random.choice(list(seed_input.values())))
            seed_input[k] = v
        elif choice == 2:  # inplace value change
            k0, v0 = random.choice(list(seed_input.items()))
            seed_input[k0] = self.typed_mutate(v0)
        return seed_input

    ############################################
    # Fetching ingredients to self.ingredients #
    ############################################
    def fetch_ingredient(self, seed_input):
        self.typed_fetch(seed_input)

    @dispatch(int)
    def typed_fetch(self, seed_input: int):
        self.ingredients[int].add(seed_input)

    @dispatch(float)
    def typed_fetch(self, seed_input: float):
        self.ingredients[float].add(seed_input)

    @dispatch(str)
    def typed_fetch(self, seed_input: str):
        self.ingredients[str].add(seed_input)
        for token in seed_input.strip().split():
            self.ingredients[str].add(token)

    # List-like
    def _fetch_list_like(self, seed_input):
        for x in seed_input:
            if self.typed_fetch.dispatch(type(x)):
                self.fetch_ingredient(x)

    @dispatch(list)
    def typed_fetch(self, seed_input: List):
        self._fetch_list_like(seed_input)

    @dispatch(tuple)
    def typed_fetch(self, seed_input: Tuple):
        self._fetch_list_like(seed_input)

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_fetch(self, seed_input: Set):
    #     self._fetch_list_like(seed_input)

    # Dict
    @dispatch(dict)
    def typed_fetch(self, seed_input: Dict):
        self._fetch_list_like(seed_input.keys())
        self._fetch_list_like(seed_input.values())

    # Type-aware concatenation

    @dispatch(int, int)
    def concat(x: int, y: int):
        return x + y

    @dispatch(float, float)
    def concat(x: float, y: float):
        return x + y

    @dispatch(bool, bool)
    def concat(x: bool, y: bool):
        return random.choice([x, y])

    @dispatch(NoneType, NoneType)
    def concat(x: NoneType, y: NoneType):
        return None

    @dispatch(list, list)
    def concat(x: list, y: list):
        choice = random.randint(0, 1)
        return (
            copy.deepcopy(x) + copy.deepcopy(y)
            if choice == 0
            else copy.deepcopy(y) + copy.deepcopy(x)
        )

    @dispatch(str, str)
    def concat(x: str, y: str):
        choice = random.randint(0, 1)
        return x + y if choice == 0 else y + x

    @dispatch(set, set)
    def concat(x: set, y: set):
        return x.union(y)

    @dispatch(dict, dict)
    def concat(x: dict, y: dict):
        return x.update(y)

    def mutate(self, seed: TestInput) -> List[Any]:
        new_input = copy.deepcopy(seed.inputs)

        for _ in range(20):
            prob = random.uniform(0, 1)
            if 0 <= prob < 0.1 and seed.sz <= MAX_SIZE:
                another_seed = random.choice(self.seed_pool).inputs
                new_input = [
                    self.concat(new_input[i], another_seed[i])
                    for i in range(len(new_input))
                ]
            else:
                for i in range(len(new_input)):
                    new_input[i] = self.typed_mutate(new_input[i])

        return new_input

    def generate(self) -> List[TestInput]:
        for _ in track(range(40)):
            seed = self.seed_selection()
            new_input = self.mutate(seed)
            # print(len(new_input[0]))
            avg, sd = self.test_efficiency(new_input)
            if avg != None and sd != None:
                self.insert_input(TestInput(new_input, avg, sd))
        return self.seed_pool


if __name__ == "__main__":
    from evalplus.data import get_human_eval_plus

    problems = get_human_eval_plus()
    for p in problems[43:44]:
        inputs = p["base_input"]
        entry_point = p["entry_point"]
        contract = p["prompt"] + p["contract"] + p["canonical_solution"]
        gen = TypedMutEffGen(inputs, entry_point, contract)
        new_inputs = gen.generate()
        for i, new_input in enumerate(new_inputs):
            print(f"New input {i}: sz: {new_input.sz}")
            if new_input.sz <= 10:
                print(new_input.inputs)
            print(
                f"- Runtime: {new_input.runtime}, Sd: {new_input.sd}, Per: {new_input.fluctuate_ratio}"
            )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\cachecontrol\controller.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The httplib2 algorithms ported for use with requests.
"""

from __future__ import annotations

import calendar
import logging
import re
import time
from email.utils import parsedate_tz
from typing import TYPE_CHECKING, Collection, Mapping

from pip._vendor.requests.structures import CaseInsensitiveDict

from pip._vendor.cachecontrol.cache import DictCache, SeparateBodyBaseCache
from pip._vendor.cachecontrol.serialize import Serializer

if TYPE_CHECKING:
    from typing import Literal

    from pip._vendor.requests import PreparedRequest
    from pip._vendor.urllib3 import HTTPResponse

    from pip._vendor.cachecontrol.cache import BaseCache

logger = logging.getLogger(__name__)

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")

PERMANENT_REDIRECT_STATUSES = (301, 308)


def parse_uri(uri: str) -> tuple[str, str, str, str, str]:
    """Parses a URI using the regex given in Appendix B of RFC 3986.

    (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    match = URI.match(uri)
    assert match is not None
    groups = match.groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController:
    """An interface to see if request should cached or not."""

    def __init__(
        self,
        cache: BaseCache | None = None,
        cache_etags: bool = True,
        serializer: Serializer | None = None,
        status_codes: Collection[int] | None = None,
    ):
        self.cache = DictCache() if cache is None else cache
        self.cache_etags = cache_etags
        self.serializer = serializer or Serializer()
        self.cacheable_status_codes = status_codes or (200, 203, 300, 301, 308)

    @classmethod
    def _urlnorm(cls, uri: str) -> str:
        """Normalize the URL to create a safe key for the cache"""
        (scheme, authority, path, query, fragment) = parse_uri(uri)
        if not scheme or not authority:
            raise Exception("Only absolute URIs are allowed. uri = %s" % uri)

        scheme = scheme.lower()
        authority = authority.lower()

        if not path:
            path = "/"

        # Could do syntax based normalization of the URI before
        # computing the digest. See Section 6.2.2 of Std 66.
        request_uri = query and "?".join([path, query]) or path
        defrag_uri = scheme + "://" + authority + request_uri

        return defrag_uri

    @classmethod
    def cache_url(cls, uri: str) -> str:
        return cls._urlnorm(uri)

    def parse_cache_control(self, headers: Mapping[str, str]) -> dict[str, int | None]:
        known_directives = {
            # https://tools.ietf.org/html/rfc7234#section-5.2
            "max-age": (int, True),
            "max-stale": (int, False),
            "min-fresh": (int, True),
            "no-cache": (None, False),
            "no-store": (None, False),
            "no-transform": (None, False),
            "only-if-cached": (None, False),
            "must-revalidate": (None, False),
            "public": (None, False),
            "private": (None, False),
            "proxy-revalidate": (None, False),
            "s-maxage": (int, True),
        }

        cc_headers = headers.get("cache-control", headers.get("Cache-Control", ""))

        retval: dict[str, int | None] = {}

        for cc_directive in cc_headers.split(","):
            if not cc_directive.strip():
                continue

            parts = cc_directive.split("=", 1)
            directive = parts[0].strip()

            try:
                typ, required = known_directives[directive]
            except KeyError:
                logger.debug("Ignoring unknown cache-control directive: %s", directive)
                continue

            if not typ or not required:
                retval[directive] = None
            if typ:
                try:
                    retval[directive] = typ(parts[1].strip())
                except IndexError:
                    if required:
                        logger.debug(
                            "Missing value for cache-control " "directive: %s",
                            directive,
                        )
                except ValueError:
                    logger.debug(
                        "Invalid value for cache-control directive " "%s, must be %s",
                        directive,
                        typ.__name__,
                    )

        return retval

    def _load_from_cache(self, request: PreparedRequest) -> HTTPResponse | None:
        """
        Load a cached response, or return None if it's not available.
        """
        # We do not support caching of partial content: so if the request contains a
        # Range header then we don't want to load anything from the cache.
        if "Range" in request.headers:
            return None

        cache_url = request.url
        assert cache_url is not None
        cache_data = self.cache.get(cache_url)
        if cache_data is None:
            logger.debug("No cache entry available")
            return None

        if isinstance(self.cache, SeparateBodyBaseCache):
            body_file = self.cache.get_body(cache_url)
        else:
            body_file = None

        result = self.serializer.loads(request, cache_data, body_file)
        if result is None:
            logger.warning("Cache entry deserialization failed, entry ignored")
        return result

    def cached_request(self, request: PreparedRequest) -> HTTPResponse | Literal[False]:
        """
        Return a cached response if it exists in the cache, otherwise
        return False.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Looking up "%s" in the cache', cache_url)
        cc = self.parse_cache_control(request.headers)

        # Bail out if the request insists on fresh data
        if "no-cache" in cc:
            logger.debug('Request header has "no-cache", cache bypassed')
            return False

        if "max-age" in cc and cc["max-age"] == 0:
            logger.debug('Request header has "max_age" as 0, cache bypassed')
            return False

        # Check whether we can load the response from the cache:
        resp = self._load_from_cache(request)
        if not resp:
            return False

        # If we have a cached permanent redirect, return it immediately. We
        # don't need to test our response for other headers b/c it is
        # intrinsically "cacheable" as it is Permanent.
        #
        # See:
        #   https://tools.ietf.org/html/rfc7231#section-6.4.2
        #
        # Client can try to refresh the value by repeating the request
        # with cache busting headers as usual (ie no-cache).
        if int(resp.status) in PERMANENT_REDIRECT_STATUSES:
            msg = (
                "Returning cached permanent redirect response "
                "(ignoring date and etag information)"
            )
            logger.debug(msg)
            return resp

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)
        if not headers or "date" not in headers:
            if "etag" not in headers:
                # Without date or etag, the cached response can never be used
                # and should be deleted.
                logger.debug("Purging cached response: no date or etag")
                self.cache.delete(cache_url)
            logger.debug("Ignoring cached response: no date")
            return False

        now = time.time()
        time_tuple = parsedate_tz(headers["date"])
        assert time_tuple is not None
        date = calendar.timegm(time_tuple[:6])
        current_age = max(0, now - date)
        logger.debug("Current age based on date: %i", current_age)

        # TODO: There is an assumption that the result will be a
        #       urllib3 response object. This may not be best since we
        #       could probably avoid instantiating or constructing the
        #       response until we know we need it.
        resp_cc = self.parse_cache_control(headers)

        # determine freshness
        freshness_lifetime = 0

        # Check the max-age pragma in the cache control header
        max_age = resp_cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug("Freshness lifetime from max-age: %i", freshness_lifetime)

        # If there isn't a max-age, check for an expires header
        elif "expires" in headers:
            expires = parsedate_tz(headers["expires"])
            if expires is not None:
                expire_time = calendar.timegm(expires[:6]) - date
                freshness_lifetime = max(0, expire_time)
                logger.debug("Freshness lifetime from expires: %i", freshness_lifetime)

        # Determine if we are setting freshness limit in the
        # request. Note, this overrides what was in the response.
        max_age = cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug(
                "Freshness lifetime from request max-age: %i", freshness_lifetime
            )

        min_fresh = cc.get("min-fresh")
        if min_fresh is not None:
            # adjust our current age by our min fresh
            current_age += min_fresh
            logger.debug("Adjusted current age from min-fresh: %i", current_age)

        # Return entry if it is fresh enough
        if freshness_lifetime > current_age:
            logger.debug('The response is "fresh", returning cached response')
            logger.debug("%i > %i", freshness_lifetime, current_age)
            return resp

        # we're not fresh. If we don't have an Etag, clear it out
        if "etag" not in headers:
            logger.debug('The cached response is "stale" with no etag, purging')
            self.cache.delete(cache_url)

        # return the original handler
        return False

    def conditional_headers(self, request: PreparedRequest) -> dict[str, str]:
        resp = self._load_from_cache(request)
        new_headers = {}

        if resp:
            headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)

            if "etag" in headers:
                new_headers["If-None-Match"] = headers["ETag"]

            if "last-modified" in headers:
                new_headers["If-Modified-Since"] = headers["Last-Modified"]

        return new_headers

    def _cache_set(
        self,
        cache_url: str,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
        expires_time: int | None = None,
    ) -> None:
        """
        Store the data in the cache.
        """
        if isinstance(self.cache, SeparateBodyBaseCache):
            # We pass in the body separately; just put a placeholder empty
            # string in the metadata.
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, b""),
                expires=expires_time,
            )
            # body is None can happen when, for example, we're only updating
            # headers, as is the case in update_cached_response().
            if body is not None:
                self.cache.set_body(cache_url, body)
        else:
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, body),
                expires=expires_time,
            )

    def cache_response(
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
        status_codes: Collection[int] | None = None,
    ) -> None:
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        # From httplib2: Don't cache 206's since we aren't going to
        #                handle byte range requests
        cacheable_status_codes = status_codes or self.cacheable_status_codes
        if response.status not in cacheable_status_codes:
            logger.debug(
                "Status code %s not in %s", response.status, cacheable_status_codes
            )
            return

        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            assert time_tuple is not None
            date = calendar.timegm(time_tuple[:6])
        else:
            date = 0

        # If we've been given a body, our response has a Content-Length, that
        # Content-Length is valid then we can check to see if the body we've
        # been given matches the expected size, and if it doesn't we'll just
        # skip trying to cache it.
        if (
            body is not None
            and "content-length" in response_headers
            and response_headers["content-length"].isdigit()
            and int(response_headers["content-length"]) != len(body)
        ):
            return

        cc_req = self.parse_cache_control(request.headers)
        cc = self.parse_cache_control(response_headers)

        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Updating cache with response from "%s"', cache_url)

        # Delete it from the cache if we happen to have it stored there
        no_store = False
        if "no-store" in cc:
            no_store = True
            logger.debug('Response header has "no-store"')
        if "no-store" in cc_req:
            no_store = True
            logger.debug('Request header has "no-store"')
        if no_store and self.cache.get(cache_url):
            logger.debug('Purging existing cache entry to honor "no-store"')
            self.cache.delete(cache_url)
        if no_store:
            return

        # https://tools.ietf.org/html/rfc7234#section-4.1:
        # A Vary header field-value of "*" always fails to match.
        # Storing such a response leads to a deserialization warning
        # during cache lookup and is not allowed to ever be served,
        # so storing it can be avoided.
        if "*" in response_headers.get("vary", ""):
            logger.debug('Response header has "Vary: *"')
            return

        # If we've been given an etag, then keep the response
        if self.cache_etags and "etag" in response_headers:
            expires_time = 0
            if response_headers.get("expires"):
                expires = parsedate_tz(response_headers["expires"])
                if expires is not None:
                    expires_time = calendar.timegm(expires[:6]) - date

            expires_time = max(expires_time, 14 * 86400)

            logger.debug(f"etag object cached for {expires_time} seconds")
            logger.debug("Caching due to etag")
            self._cache_set(cache_url, request, response, body, expires_time)

        # Add to the cache any permanent redirects. We do this before looking
        # that the Date headers.
        elif int(response.status) in PERMANENT_REDIRECT_STATUSES:
            logger.debug("Caching permanent redirect")
            self._cache_set(cache_url, request, response, b"")

        # Add to the cache if the response headers demand it. If there
        # is no date header then we can't do anything about expiring
        # the cache.
        elif "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            assert time_tuple is not None
            date = calendar.timegm(time_tuple[:6])
            # cache when there is a max-age > 0
            max_age = cc.get("max-age")
            if max_age is not None and max_age > 0:
                logger.debug("Caching b/c date exists and max-age > 0")
                expires_time = max_age
                self._cache_set(
                    cache_url,
                    request,
                    response,
                    body,
                    expires_time,
                )

            # If the request can expire, it means we should cache it
            # in the meantime.
            elif "expires" in response_headers:
                if response_headers["expires"]:
                    expires = parsedate_tz(response_headers["expires"])
                    if expires is not None:
                        expires_time = calendar.timegm(expires[:6]) - date
                    else:
                        expires_time = None

                    logger.debug(
                        "Caching b/c of expires header. expires in {} seconds".format(
                            expires_time
                        )
                    )
                    self._cache_set(
                        cache_url,
                        request,
                        response,
                        body,
                        expires_time,
                    )

    def update_cached_response(
        self, request: PreparedRequest, response: HTTPResponse
    ) -> HTTPResponse:
        """On a 304 we will get a new set of headers that we want to
        update our cached value with, assuming we have one.

        This should only ever be called when we've sent an ETag and
        gotten a 304 as the response.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        cached_response = self._load_from_cache(request)

        if not cached_response:
            # we didn't have a cached response
            return response

        # Lets update our headers with the headers from the new request:
        # http://tools.ietf.org/html/draft-ietf-httpbis-p4-conditional-26#section-4.1
        #
        # The server isn't supposed to send headers that would make
        # the cached body invalid. But... just in case, we'll be sure
        # to strip out ones we know that might be problmatic due to
        # typical assumptions.
        excluded_headers = ["content-length"]

        cached_response.headers.update(
            {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in excluded_headers
            }
        )

        # we want a 200 b/c we have content via the cache
        cached_response.status = 200

        # update our cache
        self._cache_set(cache_url, request, cached_response)

        return cached_response

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\keras_mixin.py ===
import collections.abc as collections
import json
import os
import warnings
from functools import wraps
from pathlib import Path
from shutil import copytree
from typing import Any, Dict, List, Optional, Union

from huggingface_hub import ModelHubMixin, snapshot_download
from huggingface_hub.utils import (
    get_tf_version,
    is_graphviz_available,
    is_pydot_available,
    is_tf_available,
    yaml_dump,
)

from . import constants
from .hf_api import HfApi
from .utils import SoftTemporaryDirectory, logging, validate_hf_hub_args
from .utils._typing import CallableT


logger = logging.get_logger(__name__)

keras = None
if is_tf_available():
    # Depending on which version of TensorFlow is installed, we need to import
    # keras from the correct location.
    # See https://github.com/tensorflow/tensorflow/releases/tag/v2.16.1.
    # Note: saving a keras model only works with Keras<3.0.
    try:
        import tf_keras as keras  # type: ignore
    except ImportError:
        import tensorflow as tf  # type: ignore

        keras = tf.keras


def _requires_keras_2_model(fn: CallableT) -> CallableT:
    # Wrapper to raise if user tries to save a Keras 3.x model
    @wraps(fn)
    def _inner(model, *args, **kwargs):
        if not hasattr(model, "history"):  # hacky way to check if model is Keras 2.x
            raise NotImplementedError(
                f"Cannot use '{fn.__name__}': Keras 3.x is not supported."
                " Please save models manually and upload them using `upload_folder` or `huggingface-cli upload`."
            )
        return fn(model, *args, **kwargs)

    return _inner  # type: ignore [return-value]


def _flatten_dict(dictionary, parent_key=""):
    """Flatten a nested dictionary.
    Reference: https://stackoverflow.com/a/6027615/10319735

    Args:
        dictionary (`dict`):
            The nested dictionary to be flattened.
        parent_key (`str`):
            The parent key to be prefixed to the children keys.
            Necessary for recursing over the nested dictionary.

    Returns:
        The flattened dictionary.
    """
    items = []
    for key, value in dictionary.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(
                _flatten_dict(
                    value,
                    new_key,
                ).items()
            )
        else:
            items.append((new_key, value))
    return dict(items)


def _create_hyperparameter_table(model):
    """Parse hyperparameter dictionary into a markdown table."""
    table = None
    if model.optimizer is not None:
        optimizer_params = model.optimizer.get_config()
        # flatten the configuration
        optimizer_params = _flatten_dict(optimizer_params)
        optimizer_params["training_precision"] = keras.mixed_precision.global_policy().name
        table = "| Hyperparameters | Value |\n| :-- | :-- |\n"
        for key, value in optimizer_params.items():
            table += f"| {key} | {value} |\n"
    return table


def _plot_network(model, save_directory):
    keras.utils.plot_model(
        model,
        to_file=f"{save_directory}/model.png",
        show_shapes=False,
        show_dtype=False,
        show_layer_names=True,
        rankdir="TB",
        expand_nested=False,
        dpi=96,
        layer_range=None,
    )


def _create_model_card(
    model,
    repo_dir: Path,
    plot_model: bool = True,
    metadata: Optional[dict] = None,
):
    """
    Creates a model card for the repository.

    Do not overwrite an existing README.md file.
    """
    readme_path = repo_dir / "README.md"
    if readme_path.exists():
        return

    hyperparameters = _create_hyperparameter_table(model)
    if plot_model and is_graphviz_available() and is_pydot_available():
        _plot_network(model, repo_dir)
    if metadata is None:
        metadata = {}
    metadata["library_name"] = "keras"
    model_card: str = "---\n"
    model_card += yaml_dump(metadata, default_flow_style=False)
    model_card += "---\n"
    model_card += "\n## Model description\n\nMore information needed\n"
    model_card += "\n## Intended uses & limitations\n\nMore information needed\n"
    model_card += "\n## Training and evaluation data\n\nMore information needed\n"
    if hyperparameters is not None:
        model_card += "\n## Training procedure\n"
        model_card += "\n### Training hyperparameters\n"
        model_card += "\nThe following hyperparameters were used during training:\n\n"
        model_card += hyperparameters
        model_card += "\n"
    if plot_model and os.path.exists(f"{repo_dir}/model.png"):
        model_card += "\n ## Model Plot\n"
        model_card += "\n<details>"
        model_card += "\n<summary>View Model Plot</summary>\n"
        path_to_plot = "./model.png"
        model_card += f"\n![Model Image]({path_to_plot})\n"
        model_card += "\n</details>"

    readme_path.write_text(model_card)


@_requires_keras_2_model
def save_pretrained_keras(
    model,
    save_directory: Union[str, Path],
    config: Optional[Dict[str, Any]] = None,
    include_optimizer: bool = False,
    plot_model: bool = True,
    tags: Optional[Union[list, str]] = None,
    **model_save_kwargs,
):
    """
    Saves a Keras model to save_directory in SavedModel format. Use this if
    you're using the Functional or Sequential APIs.

    Args:
        model (`Keras.Model`):
            The [Keras
            model](https://www.tensorflow.org/api_docs/python/tf/keras/Model)
            you'd like to save. The model must be compiled and built.
        save_directory (`str` or `Path`):
            Specify directory in which you want to save the Keras model.
        config (`dict`, *optional*):
            Configuration object to be saved alongside the model weights.
        include_optimizer(`bool`, *optional*, defaults to `False`):
            Whether or not to include optimizer in serialization.
        plot_model (`bool`, *optional*, defaults to `True`):
            Setting this to `True` will plot the model and put it in the model
            card. Requires graphviz and pydot to be installed.
        tags (Union[`str`,`list`], *optional*):
            List of tags that are related to model or string of a single tag. See example tags
            [here](https://github.com/huggingface/hub-docs/blob/main/modelcard.md?plain=1).
        model_save_kwargs(`dict`, *optional*):
            model_save_kwargs will be passed to
            [`tf.keras.models.save_model()`](https://www.tensorflow.org/api_docs/python/tf/keras/models/save_model).
    """
    if keras is None:
        raise ImportError("Called a Tensorflow-specific function but could not import it.")

    if not model.built:
        raise ValueError("Model should be built before trying to save")

    save_directory = Path(save_directory)
    save_directory.mkdir(parents=True, exist_ok=True)

    # saving config
    if config:
        if not isinstance(config, dict):
            raise RuntimeError(f"Provided config to save_pretrained_keras should be a dict. Got: '{type(config)}'")

        with (save_directory / constants.CONFIG_NAME).open("w") as f:
            json.dump(config, f)

    metadata = {}
    if isinstance(tags, list):
        metadata["tags"] = tags
    elif isinstance(tags, str):
        metadata["tags"] = [tags]

    task_name = model_save_kwargs.pop("task_name", None)
    if task_name is not None:
        warnings.warn(
            "`task_name` input argument is deprecated. Pass `tags` instead.",
            FutureWarning,
        )
        if "tags" in metadata:
            metadata["tags"].append(task_name)
        else:
            metadata["tags"] = [task_name]

    if model.history is not None:
        if model.history.history != {}:
            path = save_directory / "history.json"
            if path.exists():
                warnings.warn(
                    "`history.json` file already exists, it will be overwritten by the history of this version.",
                    UserWarning,
                )
            with path.open("w", encoding="utf-8") as f:
                json.dump(model.history.history, f, indent=2, sort_keys=True)

    _create_model_card(model, save_directory, plot_model, metadata)
    keras.models.save_model(model, save_directory, include_optimizer=include_optimizer, **model_save_kwargs)


def from_pretrained_keras(*args, **kwargs) -> "KerasModelHubMixin":
    r"""
    Instantiate a pretrained Keras model from a pre-trained model from the Hub.
    The model is expected to be in `SavedModel` format.

    Args:
        pretrained_model_name_or_path (`str` or `os.PathLike`):
            Can be either:
                - A string, the `model id` of a pretrained model hosted inside a
                  model repo on huggingface.co. Valid model ids can be located
                  at the root-level, like `bert-base-uncased`, or namespaced
                  under a user or organization name, like
                  `dbmdz/bert-base-german-cased`.
                - You can add `revision` by appending `@` at the end of model_id
                  simply like this: `dbmdz/bert-base-german-cased@main` Revision
                  is the specific model version to use. It can be a branch name,
                  a tag name, or a commit id, since we use a git-based system
                  for storing models and other artifacts on huggingface.co, so
                  `revision` can be any identifier allowed by git.
                - A path to a `directory` containing model weights saved using
                  [`~transformers.PreTrainedModel.save_pretrained`], e.g.,
                  `./my_model_directory/`.
                - `None` if you are both providing the configuration and state
                  dictionary (resp. with keyword arguments `config` and
                  `state_dict`).
        force_download (`bool`, *optional*, defaults to `False`):
            Whether to force the (re-)download of the model weights and
            configuration files, overriding the cached versions if they exist.
        proxies (`Dict[str, str]`, *optional*):
            A dictionary of proxy servers to use by protocol or endpoint, e.g.,
            `{'http': 'foo.bar:3128', 'http://hostname': 'foo.bar:4012'}`. The
            proxies are used on each request.
        token (`str` or `bool`, *optional*):
            The token to use as HTTP bearer authorization for remote files. If
            `True`, will use the token generated when running `transformers-cli
            login` (stored in `~/.huggingface`).
        cache_dir (`Union[str, os.PathLike]`, *optional*):
            Path to a directory in which a downloaded pretrained model
            configuration should be cached if the standard cache should not be
            used.
        local_files_only(`bool`, *optional*, defaults to `False`):
            Whether to only look at local files (i.e., do not try to download
            the model).
        model_kwargs (`Dict`, *optional*):
            model_kwargs will be passed to the model during initialization

    <Tip>

    Passing `token=True` is required when you want to use a private
    model.

    </Tip>
    """
    return KerasModelHubMixin.from_pretrained(*args, **kwargs)


@validate_hf_hub_args
@_requires_keras_2_model
def push_to_hub_keras(
    model,
    repo_id: str,
    *,
    config: Optional[dict] = None,
    commit_message: str = "Push Keras model using huggingface_hub.",
    private: Optional[bool] = None,
    api_endpoint: Optional[str] = None,
    token: Optional[str] = None,
    branch: Optional[str] = None,
    create_pr: Optional[bool] = None,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    delete_patterns: Optional[Union[List[str], str]] = None,
    log_dir: Optional[str] = None,
    include_optimizer: bool = False,
    tags: Optional[Union[list, str]] = None,
    plot_model: bool = True,
    **model_save_kwargs,
):
    """
    Upload model checkpoint to the Hub.

    Use `allow_patterns` and `ignore_patterns` to precisely filter which files should be pushed to the hub. Use
    `delete_patterns` to delete existing remote files in the same commit. See [`upload_folder`] reference for more
    details.

    Args:
        model (`Keras.Model`):
            The [Keras model](`https://www.tensorflow.org/api_docs/python/tf/keras/Model`) you'd like to push to the
            Hub. The model must be compiled and built.
        repo_id (`str`):
                ID of the repository to push to (example: `"username/my-model"`).
        commit_message (`str`, *optional*, defaults to "Add Keras model"):
            Message to commit while pushing.
        private (`bool`, *optional*):
            Whether the repository created should be private.
            If `None` (default), the repo will be public unless the organization's default is private.
        api_endpoint (`str`, *optional*):
            The API endpoint to use when pushing the model to the hub.
        token (`str`, *optional*):
            The token to use as HTTP bearer authorization for remote files. If
            not set, will use the token set when logging in with
            `huggingface-cli login` (stored in `~/.huggingface`).
        branch (`str`, *optional*):
            The git branch on which to push the model. This defaults to
            the default branch as specified in your repository, which
            defaults to `"main"`.
        create_pr (`boolean`, *optional*):
            Whether or not to create a Pull Request from `branch` with that commit.
            Defaults to `False`.
        config (`dict`, *optional*):
            Configuration object to be saved alongside the model weights.
        allow_patterns (`List[str]` or `str`, *optional*):
            If provided, only files matching at least one pattern are pushed.
        ignore_patterns (`List[str]` or `str`, *optional*):
            If provided, files matching any of the patterns are not pushed.
        delete_patterns (`List[str]` or `str`, *optional*):
            If provided, remote files matching any of the patterns will be deleted from the repo.
        log_dir (`str`, *optional*):
            TensorBoard logging directory to be pushed. The Hub automatically
            hosts and displays a TensorBoard instance if log files are included
            in the repository.
        include_optimizer (`bool`, *optional*, defaults to `False`):
            Whether or not to include optimizer during serialization.
        tags (Union[`list`, `str`], *optional*):
            List of tags that are related to model or string of a single tag. See example tags
            [here](https://github.com/huggingface/hub-docs/blob/main/modelcard.md?plain=1).
        plot_model (`bool`, *optional*, defaults to `True`):
            Setting this to `True` will plot the model and put it in the model
            card. Requires graphviz and pydot to be installed.
        model_save_kwargs(`dict`, *optional*):
            model_save_kwargs will be passed to
            [`tf.keras.models.save_model()`](https://www.tensorflow.org/api_docs/python/tf/keras/models/save_model).

    Returns:
        The url of the commit of your model in the given repository.
    """
    api = HfApi(endpoint=api_endpoint)
    repo_id = api.create_repo(repo_id=repo_id, token=token, private=private, exist_ok=True).repo_id

    # Push the files to the repo in a single commit
    with SoftTemporaryDirectory() as tmp:
        saved_path = Path(tmp) / repo_id
        save_pretrained_keras(
            model,
            saved_path,
            config=config,
            include_optimizer=include_optimizer,
            tags=tags,
            plot_model=plot_model,
            **model_save_kwargs,
        )

        # If `log_dir` provided, delete remote logs and upload new ones
        if log_dir is not None:
            delete_patterns = (
                []
                if delete_patterns is None
                else (
                    [delete_patterns]  # convert `delete_patterns` to a list
                    if isinstance(delete_patterns, str)
                    else delete_patterns
                )
            )
            delete_patterns.append("logs/*")
            copytree(log_dir, saved_path / "logs")

        return api.upload_folder(
            repo_type="model",
            repo_id=repo_id,
            folder_path=saved_path,
            commit_message=commit_message,
            token=token,
            revision=branch,
            create_pr=create_pr,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            delete_patterns=delete_patterns,
        )


class KerasModelHubMixin(ModelHubMixin):
    """
    Implementation of [`ModelHubMixin`] to provide model Hub upload/download
    capabilities to Keras models.


    ```python
    >>> import tensorflow as tf
    >>> from huggingface_hub import KerasModelHubMixin


    >>> class MyModel(tf.keras.Model, KerasModelHubMixin):
    ...     def __init__(self, **kwargs):
    ...         super().__init__()
    ...         self.config = kwargs.pop("config", None)
    ...         self.dummy_inputs = ...
    ...         self.layer = ...

    ...     def call(self, *args):
    ...         return ...


    >>> # Initialize and compile the model as you normally would
    >>> model = MyModel()
    >>> model.compile(...)
    >>> # Build the graph by training it or passing dummy inputs
    >>> _ = model(model.dummy_inputs)
    >>> # Save model weights to local directory
    >>> model.save_pretrained("my-awesome-model")
    >>> # Push model weights to the Hub
    >>> model.push_to_hub("my-awesome-model")
    >>> # Download and initialize weights from the Hub
    >>> model = MyModel.from_pretrained("username/super-cool-model")
    ```
    """

    def _save_pretrained(self, save_directory):
        save_pretrained_keras(self, save_directory)

    @classmethod
    def _from_pretrained(
        cls,
        model_id,
        revision,
        cache_dir,
        force_download,
        proxies,
        resume_download,
        local_files_only,
        token,
        config: Optional[Dict[str, Any]] = None,
        **model_kwargs,
    ):
        """Here we just call [`from_pretrained_keras`] function so both the mixin and
        functional APIs stay in sync.

                TODO - Some args above aren't used since we are calling
                snapshot_download instead of hf_hub_download.
        """
        if keras is None:
            raise ImportError("Called a TensorFlow-specific function but could not import it.")

        # Root is either a local filepath matching model_id or a cached snapshot
        if not os.path.isdir(model_id):
            storage_folder = snapshot_download(
                repo_id=model_id,
                revision=revision,
                cache_dir=cache_dir,
                library_name="keras",
                library_version=get_tf_version(),
            )
        else:
            storage_folder = model_id

        # TODO: change this in a future PR. We are not returning a KerasModelHubMixin instance here...
        model = keras.models.load_model(storage_folder)

        # For now, we add a new attribute, config, to store the config loaded from the hub/a local dir.
        model.config = config

        return model

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\cachecontrol\controller.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The httplib2 algorithms ported for use with requests.
"""

from __future__ import annotations

import calendar
import logging
import re
import time
from email.utils import parsedate_tz
from typing import TYPE_CHECKING, Collection, Mapping

from pip._vendor.requests.structures import CaseInsensitiveDict

from pip._vendor.cachecontrol.cache import DictCache, SeparateBodyBaseCache
from pip._vendor.cachecontrol.serialize import Serializer

if TYPE_CHECKING:
    from typing import Literal

    from pip._vendor.requests import PreparedRequest
    from pip._vendor.urllib3 import HTTPResponse

    from pip._vendor.cachecontrol.cache import BaseCache

logger = logging.getLogger(__name__)

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")

PERMANENT_REDIRECT_STATUSES = (301, 308)


def parse_uri(uri: str) -> tuple[str, str, str, str, str]:
    """Parses a URI using the regex given in Appendix B of RFC 3986.

    (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    match = URI.match(uri)
    assert match is not None
    groups = match.groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController:
    """An interface to see if request should cached or not."""

    def __init__(
        self,
        cache: BaseCache | None = None,
        cache_etags: bool = True,
        serializer: Serializer | None = None,
        status_codes: Collection[int] | None = None,
    ):
        self.cache = DictCache() if cache is None else cache
        self.cache_etags = cache_etags
        self.serializer = serializer or Serializer()
        self.cacheable_status_codes = status_codes or (200, 203, 300, 301, 308)

    @classmethod
    def _urlnorm(cls, uri: str) -> str:
        """Normalize the URL to create a safe key for the cache"""
        (scheme, authority, path, query, fragment) = parse_uri(uri)
        if not scheme or not authority:
            raise Exception("Only absolute URIs are allowed. uri = %s" % uri)

        scheme = scheme.lower()
        authority = authority.lower()

        if not path:
            path = "/"

        # Could do syntax based normalization of the URI before
        # computing the digest. See Section 6.2.2 of Std 66.
        request_uri = query and "?".join([path, query]) or path
        defrag_uri = scheme + "://" + authority + request_uri

        return defrag_uri

    @classmethod
    def cache_url(cls, uri: str) -> str:
        return cls._urlnorm(uri)

    def parse_cache_control(self, headers: Mapping[str, str]) -> dict[str, int | None]:
        known_directives = {
            # https://tools.ietf.org/html/rfc7234#section-5.2
            "max-age": (int, True),
            "max-stale": (int, False),
            "min-fresh": (int, True),
            "no-cache": (None, False),
            "no-store": (None, False),
            "no-transform": (None, False),
            "only-if-cached": (None, False),
            "must-revalidate": (None, False),
            "public": (None, False),
            "private": (None, False),
            "proxy-revalidate": (None, False),
            "s-maxage": (int, True),
        }

        cc_headers = headers.get("cache-control", headers.get("Cache-Control", ""))

        retval: dict[str, int | None] = {}

        for cc_directive in cc_headers.split(","):
            if not cc_directive.strip():
                continue

            parts = cc_directive.split("=", 1)
            directive = parts[0].strip()

            try:
                typ, required = known_directives[directive]
            except KeyError:
                logger.debug("Ignoring unknown cache-control directive: %s", directive)
                continue

            if not typ or not required:
                retval[directive] = None
            if typ:
                try:
                    retval[directive] = typ(parts[1].strip())
                except IndexError:
                    if required:
                        logger.debug(
                            "Missing value for cache-control " "directive: %s",
                            directive,
                        )
                except ValueError:
                    logger.debug(
                        "Invalid value for cache-control directive " "%s, must be %s",
                        directive,
                        typ.__name__,
                    )

        return retval

    def _load_from_cache(self, request: PreparedRequest) -> HTTPResponse | None:
        """
        Load a cached response, or return None if it's not available.
        """
        # We do not support caching of partial content: so if the request contains a
        # Range header then we don't want to load anything from the cache.
        if "Range" in request.headers:
            return None

        cache_url = request.url
        assert cache_url is not None
        cache_data = self.cache.get(cache_url)
        if cache_data is None:
            logger.debug("No cache entry available")
            return None

        if isinstance(self.cache, SeparateBodyBaseCache):
            body_file = self.cache.get_body(cache_url)
        else:
            body_file = None

        result = self.serializer.loads(request, cache_data, body_file)
        if result is None:
            logger.warning("Cache entry deserialization failed, entry ignored")
        return result

    def cached_request(self, request: PreparedRequest) -> HTTPResponse | Literal[False]:
        """
        Return a cached response if it exists in the cache, otherwise
        return False.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Looking up "%s" in the cache', cache_url)
        cc = self.parse_cache_control(request.headers)

        # Bail out if the request insists on fresh data
        if "no-cache" in cc:
            logger.debug('Request header has "no-cache", cache bypassed')
            return False

        if "max-age" in cc and cc["max-age"] == 0:
            logger.debug('Request header has "max_age" as 0, cache bypassed')
            return False

        # Check whether we can load the response from the cache:
        resp = self._load_from_cache(request)
        if not resp:
            return False

        # If we have a cached permanent redirect, return it immediately. We
        # don't need to test our response for other headers b/c it is
        # intrinsically "cacheable" as it is Permanent.
        #
        # See:
        #   https://tools.ietf.org/html/rfc7231#section-6.4.2
        #
        # Client can try to refresh the value by repeating the request
        # with cache busting headers as usual (ie no-cache).
        if int(resp.status) in PERMANENT_REDIRECT_STATUSES:
            msg = (
                "Returning cached permanent redirect response "
                "(ignoring date and etag information)"
            )
            logger.debug(msg)
            return resp

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)
        if not headers or "date" not in headers:
            if "etag" not in headers:
                # Without date or etag, the cached response can never be used
                # and should be deleted.
                logger.debug("Purging cached response: no date or etag")
                self.cache.delete(cache_url)
            logger.debug("Ignoring cached response: no date")
            return False

        now = time.time()
        time_tuple = parsedate_tz(headers["date"])
        assert time_tuple is not None
        date = calendar.timegm(time_tuple[:6])
        current_age = max(0, now - date)
        logger.debug("Current age based on date: %i", current_age)

        # TODO: There is an assumption that the result will be a
        #       urllib3 response object. This may not be best since we
        #       could probably avoid instantiating or constructing the
        #       response until we know we need it.
        resp_cc = self.parse_cache_control(headers)

        # determine freshness
        freshness_lifetime = 0

        # Check the max-age pragma in the cache control header
        max_age = resp_cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug("Freshness lifetime from max-age: %i", freshness_lifetime)

        # If there isn't a max-age, check for an expires header
        elif "expires" in headers:
            expires = parsedate_tz(headers["expires"])
            if expires is not None:
                expire_time = calendar.timegm(expires[:6]) - date
                freshness_lifetime = max(0, expire_time)
                logger.debug("Freshness lifetime from expires: %i", freshness_lifetime)

        # Determine if we are setting freshness limit in the
        # request. Note, this overrides what was in the response.
        max_age = cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug(
                "Freshness lifetime from request max-age: %i", freshness_lifetime
            )

        min_fresh = cc.get("min-fresh")
        if min_fresh is not None:
            # adjust our current age by our min fresh
            current_age += min_fresh
            logger.debug("Adjusted current age from min-fresh: %i", current_age)

        # Return entry if it is fresh enough
        if freshness_lifetime > current_age:
            logger.debug('The response is "fresh", returning cached response')
            logger.debug("%i > %i", freshness_lifetime, current_age)
            return resp

        # we're not fresh. If we don't have an Etag, clear it out
        if "etag" not in headers:
            logger.debug('The cached response is "stale" with no etag, purging')
            self.cache.delete(cache_url)

        # return the original handler
        return False

    def conditional_headers(self, request: PreparedRequest) -> dict[str, str]:
        resp = self._load_from_cache(request)
        new_headers = {}

        if resp:
            headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)

            if "etag" in headers:
                new_headers["If-None-Match"] = headers["ETag"]

            if "last-modified" in headers:
                new_headers["If-Modified-Since"] = headers["Last-Modified"]

        return new_headers

    def _cache_set(
        self,
        cache_url: str,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
        expires_time: int | None = None,
    ) -> None:
        """
        Store the data in the cache.
        """
        if isinstance(self.cache, SeparateBodyBaseCache):
            # We pass in the body separately; just put a placeholder empty
            # string in the metadata.
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, b""),
                expires=expires_time,
            )
            # body is None can happen when, for example, we're only updating
            # headers, as is the case in update_cached_response().
            if body is not None:
                self.cache.set_body(cache_url, body)
        else:
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, body),
                expires=expires_time,
            )

    def cache_response(
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
        status_codes: Collection[int] | None = None,
    ) -> None:
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        # From httplib2: Don't cache 206's since we aren't going to
        #                handle byte range requests
        cacheable_status_codes = status_codes or self.cacheable_status_codes
        if response.status not in cacheable_status_codes:
            logger.debug(
                "Status code %s not in %s", response.status, cacheable_status_codes
            )
            return

        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            assert time_tuple is not None
            date = calendar.timegm(time_tuple[:6])
        else:
            date = 0

        # If we've been given a body, our response has a Content-Length, that
        # Content-Length is valid then we can check to see if the body we've
        # been given matches the expected size, and if it doesn't we'll just
        # skip trying to cache it.
        if (
            body is not None
            and "content-length" in response_headers
            and response_headers["content-length"].isdigit()
            and int(response_headers["content-length"]) != len(body)
        ):
            return

        cc_req = self.parse_cache_control(request.headers)
        cc = self.parse_cache_control(response_headers)

        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Updating cache with response from "%s"', cache_url)

        # Delete it from the cache if we happen to have it stored there
        no_store = False
        if "no-store" in cc:
            no_store = True
            logger.debug('Response header has "no-store"')
        if "no-store" in cc_req:
            no_store = True
            logger.debug('Request header has "no-store"')
        if no_store and self.cache.get(cache_url):
            logger.debug('Purging existing cache entry to honor "no-store"')
            self.cache.delete(cache_url)
        if no_store:
            return

        # https://tools.ietf.org/html/rfc7234#section-4.1:
        # A Vary header field-value of "*" always fails to match.
        # Storing such a response leads to a deserialization warning
        # during cache lookup and is not allowed to ever be served,
        # so storing it can be avoided.
        if "*" in response_headers.get("vary", ""):
            logger.debug('Response header has "Vary: *"')
            return

        # If we've been given an etag, then keep the response
        if self.cache_etags and "etag" in response_headers:
            expires_time = 0
            if response_headers.get("expires"):
                expires = parsedate_tz(response_headers["expires"])
                if expires is not None:
                    expires_time = calendar.timegm(expires[:6]) - date

            expires_time = max(expires_time, 14 * 86400)

            logger.debug(f"etag object cached for {expires_time} seconds")
            logger.debug("Caching due to etag")
            self._cache_set(cache_url, request, response, body, expires_time)

        # Add to the cache any permanent redirects. We do this before looking
        # that the Date headers.
        elif int(response.status) in PERMANENT_REDIRECT_STATUSES:
            logger.debug("Caching permanent redirect")
            self._cache_set(cache_url, request, response, b"")

        # Add to the cache if the response headers demand it. If there
        # is no date header then we can't do anything about expiring
        # the cache.
        elif "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            assert time_tuple is not None
            date = calendar.timegm(time_tuple[:6])
            # cache when there is a max-age > 0
            max_age = cc.get("max-age")
            if max_age is not None and max_age > 0:
                logger.debug("Caching b/c date exists and max-age > 0")
                expires_time = max_age
                self._cache_set(
                    cache_url,
                    request,
                    response,
                    body,
                    expires_time,
                )

            # If the request can expire, it means we should cache it
            # in the meantime.
            elif "expires" in response_headers:
                if response_headers["expires"]:
                    expires = parsedate_tz(response_headers["expires"])
                    if expires is not None:
                        expires_time = calendar.timegm(expires[:6]) - date
                    else:
                        expires_time = None

                    logger.debug(
                        "Caching b/c of expires header. expires in {} seconds".format(
                            expires_time
                        )
                    )
                    self._cache_set(
                        cache_url,
                        request,
                        response,
                        body,
                        expires_time,
                    )

    def update_cached_response(
        self, request: PreparedRequest, response: HTTPResponse
    ) -> HTTPResponse:
        """On a 304 we will get a new set of headers that we want to
        update our cached value with, assuming we have one.

        This should only ever be called when we've sent an ETag and
        gotten a 304 as the response.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        cached_response = self._load_from_cache(request)

        if not cached_response:
            # we didn't have a cached response
            return response

        # Lets update our headers with the headers from the new request:
        # http://tools.ietf.org/html/draft-ietf-httpbis-p4-conditional-26#section-4.1
        #
        # The server isn't supposed to send headers that would make
        # the cached body invalid. But... just in case, we'll be sure
        # to strip out ones we know that might be problmatic due to
        # typical assumptions.
        excluded_headers = ["content-length"]

        cached_response.headers.update(
            {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in excluded_headers
            }
        )

        # we want a 200 b/c we have content via the cache
        cached_response.status = 200

        # update our cache
        self._cache_set(cache_url, request, cached_response)

        return cached_response

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\dataclasses.py ===
"""
The main purpose is to enhance stdlib dataclasses by adding validation
A pydantic dataclass can be generated from scratch or from a stdlib one.

Behind the scene, a pydantic dataclass is just like a regular one on which we attach
a `BaseModel` and magic methods to trigger the validation of the data.
`__init__` and `__post_init__` are hence overridden and have extra logic to be
able to validate input data.

When a pydantic dataclass is generated from scratch, it's just a plain dataclass
with validation triggered at initialization

The tricky part if for stdlib dataclasses that are converted after into pydantic ones e.g.

```py
@dataclasses.dataclass
class M:
    x: int

ValidatedM = pydantic.dataclasses.dataclass(M)
```

We indeed still want to support equality, hashing, repr, ... as if it was the stdlib one!

```py
assert isinstance(ValidatedM(x=1), M)
assert ValidatedM(x=1) == M(x=1)
```

This means we **don't want to create a new dataclass that inherits from it**
The trick is to create a wrapper around `M` that will act as a proxy to trigger
validation without altering default `M` behaviour.
"""
import copy
import dataclasses
import sys
from contextlib import contextmanager
from functools import wraps

try:
    from functools import cached_property
except ImportError:
    # cached_property available only for python3.8+
    pass

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, Generator, Optional, Type, TypeVar, Union, overload

from typing_extensions import dataclass_transform

from pydantic.v1.class_validators import gather_all_validators
from pydantic.v1.config import BaseConfig, ConfigDict, Extra, get_config
from pydantic.v1.error_wrappers import ValidationError
from pydantic.v1.errors import DataclassTypeError
from pydantic.v1.fields import Field, FieldInfo, Required, Undefined
from pydantic.v1.main import create_model, validate_model
from pydantic.v1.utils import ClassAttribute

if TYPE_CHECKING:
    from pydantic.v1.main import BaseModel
    from pydantic.v1.typing import CallableGenerator, NoArgAnyCallable

    DataclassT = TypeVar('DataclassT', bound='Dataclass')

    DataclassClassOrWrapper = Union[Type['Dataclass'], 'DataclassProxy']

    class Dataclass:
        # stdlib attributes
        __dataclass_fields__: ClassVar[Dict[str, Any]]
        __dataclass_params__: ClassVar[Any]  # in reality `dataclasses._DataclassParams`
        __post_init__: ClassVar[Callable[..., None]]

        # Added by pydantic
        __pydantic_run_validation__: ClassVar[bool]
        __post_init_post_parse__: ClassVar[Callable[..., None]]
        __pydantic_initialised__: ClassVar[bool]
        __pydantic_model__: ClassVar[Type[BaseModel]]
        __pydantic_validate_values__: ClassVar[Callable[['Dataclass'], None]]
        __pydantic_has_field_info_default__: ClassVar[bool]  # whether a `pydantic.Field` is used as default value

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        @classmethod
        def __get_validators__(cls: Type['Dataclass']) -> 'CallableGenerator':
            pass

        @classmethod
        def __validate__(cls: Type['DataclassT'], v: Any) -> 'DataclassT':
            pass


__all__ = [
    'dataclass',
    'set_validation',
    'create_pydantic_model_from_dataclass',
    'is_builtin_dataclass',
    'make_dataclass_validator',
]

_T = TypeVar('_T')

if sys.version_info >= (3, 10):

    @dataclass_transform(field_specifiers=(dataclasses.field, Field))
    @overload
    def dataclass(
        *,
        init: bool = True,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        config: Union[ConfigDict, Type[object], None] = None,
        validate_on_init: Optional[bool] = None,
        use_proxy: Optional[bool] = None,
        kw_only: bool = ...,
    ) -> Callable[[Type[_T]], 'DataclassClassOrWrapper']:
        ...

    @dataclass_transform(field_specifiers=(dataclasses.field, Field))
    @overload
    def dataclass(
        _cls: Type[_T],
        *,
        init: bool = True,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        config: Union[ConfigDict, Type[object], None] = None,
        validate_on_init: Optional[bool] = None,
        use_proxy: Optional[bool] = None,
        kw_only: bool = ...,
    ) -> 'DataclassClassOrWrapper':
        ...

else:

    @dataclass_transform(field_specifiers=(dataclasses.field, Field))
    @overload
    def dataclass(
        *,
        init: bool = True,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        config: Union[ConfigDict, Type[object], None] = None,
        validate_on_init: Optional[bool] = None,
        use_proxy: Optional[bool] = None,
    ) -> Callable[[Type[_T]], 'DataclassClassOrWrapper']:
        ...

    @dataclass_transform(field_specifiers=(dataclasses.field, Field))
    @overload
    def dataclass(
        _cls: Type[_T],
        *,
        init: bool = True,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        config: Union[ConfigDict, Type[object], None] = None,
        validate_on_init: Optional[bool] = None,
        use_proxy: Optional[bool] = None,
    ) -> 'DataclassClassOrWrapper':
        ...


@dataclass_transform(field_specifiers=(dataclasses.field, Field))
def dataclass(
    _cls: Optional[Type[_T]] = None,
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    config: Union[ConfigDict, Type[object], None] = None,
    validate_on_init: Optional[bool] = None,
    use_proxy: Optional[bool] = None,
    kw_only: bool = False,
) -> Union[Callable[[Type[_T]], 'DataclassClassOrWrapper'], 'DataclassClassOrWrapper']:
    """
    Like the python standard lib dataclasses but with type validation.
    The result is either a pydantic dataclass that will validate input data
    or a wrapper that will trigger validation around a stdlib dataclass
    to avoid modifying it directly
    """
    the_config = get_config(config)

    def wrap(cls: Type[Any]) -> 'DataclassClassOrWrapper':
        should_use_proxy = (
            use_proxy
            if use_proxy is not None
            else (
                is_builtin_dataclass(cls)
                and (cls.__bases__[0] is object or set(dir(cls)) == set(dir(cls.__bases__[0])))
            )
        )
        if should_use_proxy:
            dc_cls_doc = ''
            dc_cls = DataclassProxy(cls)
            default_validate_on_init = False
        else:
            dc_cls_doc = cls.__doc__ or ''  # needs to be done before generating dataclass
            if sys.version_info >= (3, 10):
                dc_cls = dataclasses.dataclass(
                    cls,
                    init=init,
                    repr=repr,
                    eq=eq,
                    order=order,
                    unsafe_hash=unsafe_hash,
                    frozen=frozen,
                    kw_only=kw_only,
                )
            else:
                dc_cls = dataclasses.dataclass(  # type: ignore
                    cls, init=init, repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash, frozen=frozen
                )
            default_validate_on_init = True

        should_validate_on_init = default_validate_on_init if validate_on_init is None else validate_on_init
        _add_pydantic_validation_attributes(cls, the_config, should_validate_on_init, dc_cls_doc)
        dc_cls.__pydantic_model__.__try_update_forward_refs__(**{cls.__name__: cls})
        return dc_cls

    if _cls is None:
        return wrap

    return wrap(_cls)


@contextmanager
def set_validation(cls: Type['DataclassT'], value: bool) -> Generator[Type['DataclassT'], None, None]:
    original_run_validation = cls.__pydantic_run_validation__
    try:
        cls.__pydantic_run_validation__ = value
        yield cls
    finally:
        cls.__pydantic_run_validation__ = original_run_validation


class DataclassProxy:
    __slots__ = '__dataclass__'

    def __init__(self, dc_cls: Type['Dataclass']) -> None:
        object.__setattr__(self, '__dataclass__', dc_cls)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        with set_validation(self.__dataclass__, True):
            return self.__dataclass__(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__dataclass__, name)

    def __setattr__(self, __name: str, __value: Any) -> None:
        return setattr(self.__dataclass__, __name, __value)

    def __instancecheck__(self, instance: Any) -> bool:
        return isinstance(instance, self.__dataclass__)

    def __copy__(self) -> 'DataclassProxy':
        return DataclassProxy(copy.copy(self.__dataclass__))

    def __deepcopy__(self, memo: Any) -> 'DataclassProxy':
        return DataclassProxy(copy.deepcopy(self.__dataclass__, memo))


def _add_pydantic_validation_attributes(  # noqa: C901 (ignore complexity)
    dc_cls: Type['Dataclass'],
    config: Type[BaseConfig],
    validate_on_init: bool,
    dc_cls_doc: str,
) -> None:
    """
    We need to replace the right method. If no `__post_init__` has been set in the stdlib dataclass
    it won't even exist (code is generated on the fly by `dataclasses`)
    By default, we run validation after `__init__` or `__post_init__` if defined
    """
    init = dc_cls.__init__

    @wraps(init)
    def handle_extra_init(self: 'Dataclass', *args: Any, **kwargs: Any) -> None:
        if config.extra == Extra.ignore:
            init(self, *args, **{k: v for k, v in kwargs.items() if k in self.__dataclass_fields__})

        elif config.extra == Extra.allow:
            for k, v in kwargs.items():
                self.__dict__.setdefault(k, v)
            init(self, *args, **{k: v for k, v in kwargs.items() if k in self.__dataclass_fields__})

        else:
            init(self, *args, **kwargs)

    if hasattr(dc_cls, '__post_init__'):
        try:
            post_init = dc_cls.__post_init__.__wrapped__  # type: ignore[attr-defined]
        except AttributeError:
            post_init = dc_cls.__post_init__

        @wraps(post_init)
        def new_post_init(self: 'Dataclass', *args: Any, **kwargs: Any) -> None:
            if config.post_init_call == 'before_validation':
                post_init(self, *args, **kwargs)

            if self.__class__.__pydantic_run_validation__:
                self.__pydantic_validate_values__()
                if hasattr(self, '__post_init_post_parse__'):
                    self.__post_init_post_parse__(*args, **kwargs)

            if config.post_init_call == 'after_validation':
                post_init(self, *args, **kwargs)

        setattr(dc_cls, '__init__', handle_extra_init)
        setattr(dc_cls, '__post_init__', new_post_init)

    else:

        @wraps(init)
        def new_init(self: 'Dataclass', *args: Any, **kwargs: Any) -> None:
            handle_extra_init(self, *args, **kwargs)

            if self.__class__.__pydantic_run_validation__:
                self.__pydantic_validate_values__()

            if hasattr(self, '__post_init_post_parse__'):
                # We need to find again the initvars. To do that we use `__dataclass_fields__` instead of
                # public method `dataclasses.fields`

                # get all initvars and their default values
                initvars_and_values: Dict[str, Any] = {}
                for i, f in enumerate(self.__class__.__dataclass_fields__.values()):
                    if f._field_type is dataclasses._FIELD_INITVAR:  # type: ignore[attr-defined]
                        try:
                            # set arg value by default
                            initvars_and_values[f.name] = args[i]
                        except IndexError:
                            initvars_and_values[f.name] = kwargs.get(f.name, f.default)

                self.__post_init_post_parse__(**initvars_and_values)

        setattr(dc_cls, '__init__', new_init)

    setattr(dc_cls, '__pydantic_run_validation__', ClassAttribute('__pydantic_run_validation__', validate_on_init))
    setattr(dc_cls, '__pydantic_initialised__', False)
    setattr(dc_cls, '__pydantic_model__', create_pydantic_model_from_dataclass(dc_cls, config, dc_cls_doc))
    setattr(dc_cls, '__pydantic_validate_values__', _dataclass_validate_values)
    setattr(dc_cls, '__validate__', classmethod(_validate_dataclass))
    setattr(dc_cls, '__get_validators__', classmethod(_get_validators))

    if dc_cls.__pydantic_model__.__config__.validate_assignment and not dc_cls.__dataclass_params__.frozen:
        setattr(dc_cls, '__setattr__', _dataclass_validate_assignment_setattr)


def _get_validators(cls: 'DataclassClassOrWrapper') -> 'CallableGenerator':
    yield cls.__validate__


def _validate_dataclass(cls: Type['DataclassT'], v: Any) -> 'DataclassT':
    with set_validation(cls, True):
        if isinstance(v, cls):
            v.__pydantic_validate_values__()
            return v
        elif isinstance(v, (list, tuple)):
            return cls(*v)
        elif isinstance(v, dict):
            return cls(**v)
        else:
            raise DataclassTypeError(class_name=cls.__name__)


def create_pydantic_model_from_dataclass(
    dc_cls: Type['Dataclass'],
    config: Type[Any] = BaseConfig,
    dc_cls_doc: Optional[str] = None,
) -> Type['BaseModel']:
    field_definitions: Dict[str, Any] = {}
    for field in dataclasses.fields(dc_cls):
        default: Any = Undefined
        default_factory: Optional['NoArgAnyCallable'] = None
        field_info: FieldInfo

        if field.default is not dataclasses.MISSING:
            default = field.default
        elif field.default_factory is not dataclasses.MISSING:
            default_factory = field.default_factory
        else:
            default = Required

        if isinstance(default, FieldInfo):
            field_info = default
            dc_cls.__pydantic_has_field_info_default__ = True
        else:
            field_info = Field(default=default, default_factory=default_factory, **field.metadata)

        field_definitions[field.name] = (field.type, field_info)

    validators = gather_all_validators(dc_cls)
    model: Type['BaseModel'] = create_model(
        dc_cls.__name__,
        __config__=config,
        __module__=dc_cls.__module__,
        __validators__=validators,
        __cls_kwargs__={'__resolve_forward_refs__': False},
        **field_definitions,
    )
    model.__doc__ = dc_cls_doc if dc_cls_doc is not None else dc_cls.__doc__ or ''
    return model


if sys.version_info >= (3, 8):

    def _is_field_cached_property(obj: 'Dataclass', k: str) -> bool:
        return isinstance(getattr(type(obj), k, None), cached_property)

else:

    def _is_field_cached_property(obj: 'Dataclass', k: str) -> bool:
        return False


def _dataclass_validate_values(self: 'Dataclass') -> None:
    # validation errors can occur if this function is called twice on an already initialised dataclass.
    # for example if Extra.forbid is enabled, it would consider __pydantic_initialised__ an invalid extra property
    if getattr(self, '__pydantic_initialised__'):
        return
    if getattr(self, '__pydantic_has_field_info_default__', False):
        # We need to remove `FieldInfo` values since they are not valid as input
        # It's ok to do that because they are obviously the default values!
        input_data = {
            k: v
            for k, v in self.__dict__.items()
            if not (isinstance(v, FieldInfo) or _is_field_cached_property(self, k))
        }
    else:
        input_data = {k: v for k, v in self.__dict__.items() if not _is_field_cached_property(self, k)}
    d, _, validation_error = validate_model(self.__pydantic_model__, input_data, cls=self.__class__)
    if validation_error:
        raise validation_error
    self.__dict__.update(d)
    object.__setattr__(self, '__pydantic_initialised__', True)


def _dataclass_validate_assignment_setattr(self: 'Dataclass', name: str, value: Any) -> None:
    if self.__pydantic_initialised__:
        d = dict(self.__dict__)
        d.pop(name, None)
        known_field = self.__pydantic_model__.__fields__.get(name, None)
        if known_field:
            value, error_ = known_field.validate(value, d, loc=name, cls=self.__class__)
            if error_:
                raise ValidationError([error_], self.__class__)

    object.__setattr__(self, name, value)


def is_builtin_dataclass(_cls: Type[Any]) -> bool:
    """
    Whether a class is a stdlib dataclass
    (useful to discriminated a pydantic dataclass that is actually a wrapper around a stdlib dataclass)

    we check that
    - `_cls` is a dataclass
    - `_cls` is not a processed pydantic dataclass (with a basemodel attached)
    - `_cls` is not a pydantic dataclass inheriting directly from a stdlib dataclass
    e.g.
    ```
    @dataclasses.dataclass
    class A:
        x: int

    @pydantic.dataclasses.dataclass
    class B(A):
        y: int
    ```
    In this case, when we first check `B`, we make an extra check and look at the annotations ('y'),
    which won't be a superset of all the dataclass fields (only the stdlib fields i.e. 'x')
    """
    return (
        dataclasses.is_dataclass(_cls)
        and not hasattr(_cls, '__pydantic_model__')
        and set(_cls.__dataclass_fields__).issuperset(set(getattr(_cls, '__annotations__', {})))
    )


def make_dataclass_validator(dc_cls: Type['Dataclass'], config: Type[BaseConfig]) -> 'CallableGenerator':
    """
    Create a pydantic.dataclass from a builtin dataclass to add type validation
    and yield the validators
    It retrieves the parameters of the dataclass and forwards them to the newly created dataclass
    """
    yield from _get_validators(dataclass(dc_cls, config=config, use_proxy=True))

# === NexusCore/openenv\Lib\site-packages\jedi\inference\context.py ===
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from parso.tree import search_ancestor
from parso.python.tree import Name

from jedi.inference.filters import ParserTreeFilter, MergedFilter, \
    GlobalNameFilter
from jedi.inference.names import AnonymousParamName, TreeNameDefinition
from jedi.inference.base_value import NO_VALUES, ValueSet
from jedi.parser_utils import get_parent_scope
from jedi import debug
from jedi import parser_utils


class AbstractContext:
    # Must be defined: inference_state and tree_node and parent_context as an attribute/property

    def __init__(self, inference_state):
        self.inference_state = inference_state
        self.predefined_names = {}

    @abstractmethod
    def get_filters(self, until_position=None, origin_scope=None):
        raise NotImplementedError

    def goto(self, name_or_str, position):
        from jedi.inference import finder
        filters = _get_global_filters_for_name(
            self, name_or_str if isinstance(name_or_str, Name) else None, position,
        )
        names = finder.filter_name(filters, name_or_str)
        debug.dbg('context.goto %s in (%s): %s', name_or_str, self, names)
        return names

    def py__getattribute__(self, name_or_str, name_context=None, position=None,
                           analysis_errors=True):
        """
        :param position: Position of the last statement -> tuple of line, column
        """
        if name_context is None:
            name_context = self
        names = self.goto(name_or_str, position)

        string_name = name_or_str.value if isinstance(name_or_str, Name) else name_or_str

        # This paragraph is currently needed for proper branch type inference
        # (static analysis).
        found_predefined_types = None
        if self.predefined_names and isinstance(name_or_str, Name):
            node = name_or_str
            while node is not None and not parser_utils.is_scope(node):
                node = node.parent
                if node.type in ("if_stmt", "for_stmt", "comp_for", 'sync_comp_for'):
                    try:
                        name_dict = self.predefined_names[node]
                        types = name_dict[string_name]
                    except KeyError:
                        continue
                    else:
                        found_predefined_types = types
                        break
        if found_predefined_types is not None and names:
            from jedi.inference import flow_analysis
            check = flow_analysis.reachability_check(
                context=self,
                value_scope=self.tree_node,
                node=name_or_str,
            )
            if check is flow_analysis.UNREACHABLE:
                values = NO_VALUES
            else:
                values = found_predefined_types
        else:
            values = ValueSet.from_sets(name.infer() for name in names)

        if not names and not values and analysis_errors:
            if isinstance(name_or_str, Name):
                from jedi.inference import analysis
                message = ("NameError: name '%s' is not defined." % string_name)
                analysis.add(name_context, 'name-error', name_or_str, message)

        debug.dbg('context.names_to_types: %s -> %s', names, values)
        if values:
            return values
        return self._check_for_additional_knowledge(name_or_str, name_context, position)

    def _check_for_additional_knowledge(self, name_or_str, name_context, position):
        name_context = name_context or self
        # Add isinstance and other if/assert knowledge.
        if isinstance(name_or_str, Name) and not name_context.is_instance():
            flow_scope = name_or_str
            base_nodes = [name_context.tree_node]

            if any(b.type in ('comp_for', 'sync_comp_for') for b in base_nodes):
                return NO_VALUES
            from jedi.inference.finder import check_flow_information
            while True:
                flow_scope = get_parent_scope(flow_scope, include_flows=True)
                n = check_flow_information(name_context, flow_scope,
                                           name_or_str, position)
                if n is not None:
                    return n
                if flow_scope in base_nodes:
                    break
        return NO_VALUES

    def get_root_context(self):
        parent_context = self.parent_context
        if parent_context is None:
            return self
        return parent_context.get_root_context()

    def is_module(self):
        return False

    def is_builtins_module(self):
        return False

    def is_class(self):
        return False

    def is_stub(self):
        return False

    def is_instance(self):
        return False

    def is_compiled(self):
        return False

    def is_bound_method(self):
        return False

    @abstractmethod
    def py__name__(self):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    @property
    def name(self):
        return None

    def get_qualified_names(self):
        return ()

    def py__doc__(self):
        return ''

    @contextmanager
    def predefine_names(self, flow_scope, dct):
        predefined = self.predefined_names
        predefined[flow_scope] = dct
        try:
            yield
        finally:
            del predefined[flow_scope]


class ValueContext(AbstractContext):
    """
    Should be defined, otherwise the API returns empty types.
    """
    def __init__(self, value):
        super().__init__(value.inference_state)
        self._value = value

    @property
    def tree_node(self):
        return self._value.tree_node

    @property
    def parent_context(self):
        return self._value.parent_context

    def is_module(self):
        return self._value.is_module()

    def is_builtins_module(self):
        return self._value == self.inference_state.builtins_module

    def is_class(self):
        return self._value.is_class()

    def is_stub(self):
        return self._value.is_stub()

    def is_instance(self):
        return self._value.is_instance()

    def is_compiled(self):
        return self._value.is_compiled()

    def is_bound_method(self):
        return self._value.is_bound_method()

    def py__name__(self):
        return self._value.py__name__()

    @property
    def name(self):
        return self._value.name

    def get_qualified_names(self):
        return self._value.get_qualified_names()

    def py__doc__(self):
        return self._value.py__doc__()

    def get_value(self):
        return self._value

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._value)


class TreeContextMixin:
    def infer_node(self, node):
        from jedi.inference.syntax_tree import infer_node
        return infer_node(self, node)

    def create_value(self, node):
        from jedi.inference import value

        if node == self.tree_node:
            assert self.is_module()
            return self.get_value()

        parent_context = self.create_context(node)

        if node.type in ('funcdef', 'lambdef'):
            func = value.FunctionValue.from_context(parent_context, node)
            if parent_context.is_class():
                class_value = parent_context.parent_context.create_value(parent_context.tree_node)
                instance = value.AnonymousInstance(
                    self.inference_state, parent_context.parent_context, class_value)
                func = value.BoundMethod(
                    instance=instance,
                    class_context=class_value.as_context(),
                    function=func
                )
            return func
        elif node.type == 'classdef':
            return value.ClassValue(self.inference_state, parent_context, node)
        else:
            raise NotImplementedError("Probably shouldn't happen: %s" % node)

    def create_context(self, node):
        def from_scope_node(scope_node, is_nested=True):
            if scope_node == self.tree_node:
                return self

            if scope_node.type in ('funcdef', 'lambdef', 'classdef'):
                return self.create_value(scope_node).as_context()
            elif scope_node.type in ('comp_for', 'sync_comp_for'):
                parent_context = from_scope_node(parent_scope(scope_node.parent))
                if node.start_pos >= scope_node.children[-1].start_pos:
                    return parent_context
                return CompForContext(parent_context, scope_node)
            raise Exception("There's a scope that was not managed: %s" % scope_node)

        def parent_scope(node):
            while True:
                node = node.parent

                if parser_utils.is_scope(node):
                    return node
                elif node.type in ('argument', 'testlist_comp'):
                    if node.children[1].type in ('comp_for', 'sync_comp_for'):
                        return node.children[1]
                elif node.type == 'dictorsetmaker':
                    for n in node.children[1:4]:
                        # In dictionaries it can be pretty much anything.
                        if n.type in ('comp_for', 'sync_comp_for'):
                            return n

        scope_node = parent_scope(node)
        if scope_node.type in ('funcdef', 'classdef'):
            colon = scope_node.children[scope_node.children.index(':')]
            if node.start_pos < colon.start_pos:
                parent = node.parent
                if not (parent.type == 'param' and parent.name == node):
                    scope_node = parent_scope(scope_node)
        return from_scope_node(scope_node, is_nested=True)

    def create_name(self, tree_name):
        definition = tree_name.get_definition()
        if definition and definition.type == 'param' and definition.name == tree_name:
            funcdef = search_ancestor(definition, 'funcdef', 'lambdef')
            func = self.create_value(funcdef)
            return AnonymousParamName(func, tree_name)
        else:
            context = self.create_context(tree_name)
            return TreeNameDefinition(context, tree_name)


class FunctionContext(TreeContextMixin, ValueContext):
    def get_filters(self, until_position=None, origin_scope=None):
        yield ParserTreeFilter(
            self.inference_state,
            parent_context=self,
            until_position=until_position,
            origin_scope=origin_scope
        )


class ModuleContext(TreeContextMixin, ValueContext):
    def py__file__(self) -> Optional[Path]:
        return self._value.py__file__()  # type: ignore[no-any-return]

    def get_filters(self, until_position=None, origin_scope=None):
        filters = self._value.get_filters(origin_scope)
        # Skip the first filter and replace it.
        next(filters, None)
        yield MergedFilter(
            ParserTreeFilter(
                parent_context=self,
                until_position=until_position,
                origin_scope=origin_scope
            ),
            self.get_global_filter(),
        )
        yield from filters

    def get_global_filter(self):
        return GlobalNameFilter(self)

    @property
    def string_names(self):
        return self._value.string_names

    @property
    def code_lines(self):
        return self._value.code_lines

    def get_value(self):
        """
        This is the only function that converts a context back to a value.
        This is necessary for stub -> python conversion and vice versa. However
        this method shouldn't be moved to AbstractContext.
        """
        return self._value


class NamespaceContext(TreeContextMixin, ValueContext):
    def get_filters(self, until_position=None, origin_scope=None):
        return self._value.get_filters()

    def get_value(self):
        return self._value

    @property
    def string_names(self):
        return self._value.string_names

    def py__file__(self) -> Optional[Path]:
        return self._value.py__file__()  # type: ignore[no-any-return]


class ClassContext(TreeContextMixin, ValueContext):
    def get_filters(self, until_position=None, origin_scope=None):
        yield self.get_global_filter(until_position, origin_scope)

    def get_global_filter(self, until_position=None, origin_scope=None):
        return ParserTreeFilter(
            parent_context=self,
            until_position=until_position,
            origin_scope=origin_scope
        )


class CompForContext(TreeContextMixin, AbstractContext):
    def __init__(self, parent_context, comp_for):
        super().__init__(parent_context.inference_state)
        self.tree_node = comp_for
        self.parent_context = parent_context

    def get_filters(self, until_position=None, origin_scope=None):
        yield ParserTreeFilter(self)

    def get_value(self):
        return None

    def py__name__(self):
        return '<comprehension context>'

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.tree_node)


class CompiledContext(ValueContext):
    def get_filters(self, until_position=None, origin_scope=None):
        return self._value.get_filters()


class CompiledModuleContext(CompiledContext):
    code_lines = None

    def get_value(self):
        return self._value

    @property
    def string_names(self):
        return self._value.string_names

    def py__file__(self) -> Optional[Path]:
        return self._value.py__file__()  # type: ignore[no-any-return]


def _get_global_filters_for_name(context, name_or_none, position):
    # For functions and classes the defaults don't belong to the
    # function and get inferred in the value before the function. So
    # make sure to exclude the function/class name.
    if name_or_none is not None:
        ancestor = search_ancestor(name_or_none, 'funcdef', 'classdef', 'lambdef')
        lambdef = None
        if ancestor == 'lambdef':
            # For lambdas it's even more complicated since parts will
            # be inferred later.
            lambdef = ancestor
            ancestor = search_ancestor(name_or_none, 'funcdef', 'classdef')
        if ancestor is not None:
            colon = ancestor.children[-2]
            if position is not None and position < colon.start_pos:
                if lambdef is None or position < lambdef.children[-2].start_pos:
                    position = ancestor.start_pos

    return get_global_filters(context, position, name_or_none)


def get_global_filters(context, until_position, origin_scope):
    """
    Returns all filters in order of priority for name resolution.

    For global name lookups. The filters will handle name resolution
    themselves, but here we gather possible filters downwards.

    >>> from jedi import Script
    >>> script = Script('''
    ... x = ['a', 'b', 'c']
    ... def func():
    ...     y = None
    ... ''')
    >>> module_node = script._module_node
    >>> scope = next(module_node.iter_funcdefs())
    >>> scope
    <Function: func@3-5>
    >>> context = script._get_module_context().create_context(scope)
    >>> filters = list(get_global_filters(context, (4, 0), None))

    First we get the names from the function scope.

    >>> print(filters[0])  # doctest: +ELLIPSIS
    MergedFilter(<ParserTreeFilter: ...>, <GlobalNameFilter: ...>)
    >>> sorted(str(n) for n in filters[0].values())  # doctest: +NORMALIZE_WHITESPACE
    ['<TreeNameDefinition: string_name=func start_pos=(3, 4)>',
     '<TreeNameDefinition: string_name=x start_pos=(2, 0)>']
    >>> filters[0]._filters[0]._until_position
    (4, 0)
    >>> filters[0]._filters[1]._until_position

    Then it yields the names from one level "lower". In this example, this is
    the module scope (including globals).
    As a side note, you can see, that the position in the filter is None on the
    globals filter, because there the whole module is searched.

    >>> list(filters[1].values())  # package modules -> Also empty.
    []
    >>> sorted(name.string_name for name in filters[2].values())  # Module attributes
    ['__doc__', '__name__', '__package__']

    Finally, it yields the builtin filter, if `include_builtin` is
    true (default).

    >>> list(filters[3].values())  # doctest: +ELLIPSIS
    [...]
    """
    base_context = context
    from jedi.inference.value.function import BaseFunctionExecutionContext
    while context is not None:
        # Names in methods cannot be resolved within the class.
        yield from context.get_filters(
            until_position=until_position,
            origin_scope=origin_scope
        )
        if isinstance(context, (BaseFunctionExecutionContext, ModuleContext)):
            # The position should be reset if the current scope is a function.
            until_position = None

        context = context.parent_context

    b = next(base_context.inference_state.builtins_module.get_filters(), None)
    assert b is not None
    # Add builtins to the global scope.
    yield b

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\langsmith.py ===
#### What this does ####
#    On success, logs events to Langsmith
import asyncio
import os
import random
import traceback
import types
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel  # type: ignore

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.langsmith import *
from litellm.types.utils import StandardCallbackDynamicParams, StandardLoggingPayload


def is_serializable(value):
    non_serializable_types = (
        types.CoroutineType,
        types.FunctionType,
        types.GeneratorType,
        BaseModel,
    )
    return not isinstance(value, non_serializable_types)


class LangsmithLogger(CustomBatchLogger):
    def __init__(
        self,
        langsmith_api_key: Optional[str] = None,
        langsmith_project: Optional[str] = None,
        langsmith_base_url: Optional[str] = None,
        **kwargs,
    ):
        self.flush_lock = asyncio.Lock()
        super().__init__(**kwargs, flush_lock=self.flush_lock)
        self.default_credentials = self.get_credentials_from_env(
            langsmith_api_key=langsmith_api_key,
            langsmith_project=langsmith_project,
            langsmith_base_url=langsmith_base_url,
        )
        self.sampling_rate: float = (
            float(os.getenv("LANGSMITH_SAMPLING_RATE"))  # type: ignore
            if os.getenv("LANGSMITH_SAMPLING_RATE") is not None
            and os.getenv("LANGSMITH_SAMPLING_RATE").strip().isdigit()  # type: ignore
            else 1.0
        )
        self.langsmith_default_run_name = os.getenv(
            "LANGSMITH_DEFAULT_RUN_NAME", "LLMRun"
        )
        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        _batch_size = (
            os.getenv("LANGSMITH_BATCH_SIZE", None) or litellm.langsmith_batch_size
        )

        if _batch_size:
            self.batch_size = int(_batch_size)
        self.log_queue: List[LangsmithQueueObject] = []
        asyncio.create_task(self.periodic_flush())

    def get_credentials_from_env(
        self,
        langsmith_api_key: Optional[str] = None,
        langsmith_project: Optional[str] = None,
        langsmith_base_url: Optional[str] = None,
    ) -> LangsmithCredentialsObject:
        _credentials_api_key = langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
        if _credentials_api_key is None:
            raise Exception(
                "Invalid Langsmith API Key given. _credentials_api_key=None."
            )
        _credentials_project = (
            langsmith_project or os.getenv("LANGSMITH_PROJECT") or "litellm-completion"
        )
        if _credentials_project is None:
            raise Exception(
                "Invalid Langsmith API Key given. _credentials_project=None."
            )
        _credentials_base_url = (
            langsmith_base_url
            or os.getenv("LANGSMITH_BASE_URL")
            or "https://api.smith.langchain.com"
        )
        if _credentials_base_url is None:
            raise Exception(
                "Invalid Langsmith API Key given. _credentials_base_url=None."
            )

        return LangsmithCredentialsObject(
            LANGSMITH_API_KEY=_credentials_api_key,
            LANGSMITH_BASE_URL=_credentials_base_url,
            LANGSMITH_PROJECT=_credentials_project,
        )

    def _prepare_log_data(
        self,
        kwargs,
        response_obj,
        start_time,
        end_time,
        credentials: LangsmithCredentialsObject,
    ):
        try:
            _litellm_params = kwargs.get("litellm_params", {}) or {}
            metadata = _litellm_params.get("metadata", {}) or {}
            project_name = metadata.get(
                "project_name", credentials["LANGSMITH_PROJECT"]
            )
            run_name = metadata.get("run_name", self.langsmith_default_run_name)
            run_id = metadata.get("id", metadata.get("run_id", None))
            parent_run_id = metadata.get("parent_run_id", None)
            trace_id = metadata.get("trace_id", None)
            session_id = metadata.get("session_id", None)
            dotted_order = metadata.get("dotted_order", None)
            verbose_logger.debug(
                f"Langsmith Logging - project_name: {project_name}, run_name {run_name}"
            )

            # Ensure everything in the payload is converted to str
            payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )

            if payload is None:
                raise Exception("Error logging request payload. Payload=none.")

            metadata = payload[
                "metadata"
            ]  # ensure logged metadata is json serializable

            data = {
                "name": run_name,
                "run_type": "llm",  # this should always be llm, since litellm always logs llm calls. Langsmith allow us to log "chain"
                "inputs": payload,
                "outputs": payload["response"],
                "session_name": project_name,
                "start_time": payload["startTime"],
                "end_time": payload["endTime"],
                "tags": payload["request_tags"],
                "extra": metadata,
            }

            if payload["error_str"] is not None and payload["status"] == "failure":
                data["error"] = payload["error_str"]

            if run_id:
                data["id"] = run_id

            if parent_run_id:
                data["parent_run_id"] = parent_run_id

            if trace_id:
                data["trace_id"] = trace_id

            if session_id:
                data["session_id"] = session_id

            if dotted_order:
                data["dotted_order"] = dotted_order

            run_id: Optional[str] = data.get("id")  # type: ignore
            if "id" not in data or data["id"] is None:
                """
                for /batch langsmith requires id, trace_id and dotted_order passed as params
                """
                run_id = str(uuid.uuid4())

                data["id"] = run_id

            if (
                "trace_id" not in data
                or data["trace_id"] is None
                and (run_id is not None and isinstance(run_id, str))
            ):
                data["trace_id"] = run_id

            if (
                "dotted_order" not in data
                or data["dotted_order"] is None
                and (run_id is not None and isinstance(run_id, str))
            ):
                data["dotted_order"] = self.make_dot_order(run_id=run_id)  # type: ignore

            verbose_logger.debug("Langsmith Logging data on langsmith: %s", data)

            return data
        except Exception:
            raise

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
            credentials = self._get_credentials_to_use_for_request(kwargs=kwargs)
            data = self._prepare_log_data(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=start_time,
                end_time=end_time,
                credentials=credentials,
            )
            self.log_queue.append(
                LangsmithQueueObject(
                    data=data,
                    credentials=credentials,
                )
            )
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
            credentials = self._get_credentials_to_use_for_request(kwargs=kwargs)
            data = self._prepare_log_data(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=start_time,
                end_time=end_time,
                credentials=credentials,
            )
            self.log_queue.append(
                LangsmithQueueObject(
                    data=data,
                    credentials=credentials,
                )
            )
            verbose_logger.debug(
                "Langsmith logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                await self.flush_queue()
        except Exception:
            verbose_logger.exception(
                "Langsmith Layer Error - error logging async success event."
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
            credentials = self._get_credentials_to_use_for_request(kwargs=kwargs)
            data = self._prepare_log_data(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=start_time,
                end_time=end_time,
                credentials=credentials,
            )
            self.log_queue.append(
                LangsmithQueueObject(
                    data=data,
                    credentials=credentials,
                )
            )
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
        Handles sending batches of runs to Langsmith

        self.log_queue contains LangsmithQueueObjects
            Each LangsmithQueueObject has the following:
                - "credentials" - credentials to use for the request (langsmith_api_key, langsmith_project, langsmith_base_url)
                - "data" - data to log on to langsmith for the request


        This function
         - groups the queue objects by credentials
         - loops through each unique credentials and sends batches to Langsmith


        This was added to support key/team based logging on langsmith
        """
        if not self.log_queue:
            return

        batch_groups = self._group_batches_by_credentials()
        for batch_group in batch_groups.values():
            await self._log_batch_on_langsmith(
                credentials=batch_group.credentials,
                queue_objects=batch_group.queue_objects,
            )

    def _add_endpoint_to_url(
        self, url: str, endpoint: str, api_version: str = "/api/v1"
    ) -> str:
        if api_version not in url:
            url = f"{url.rstrip('/')}{api_version}"

        if url.endswith("/"):
            return f"{url}{endpoint}"
        return f"{url}/{endpoint}"

    async def _log_batch_on_langsmith(
        self,
        credentials: LangsmithCredentialsObject,
        queue_objects: List[LangsmithQueueObject],
    ):
        """
        Logs a batch of runs to Langsmith
        sends runs to /batch endpoint for the given credentials

        Args:
            credentials: LangsmithCredentialsObject
            queue_objects: List[LangsmithQueueObject]

        Returns: None

        Raises: Does not raise an exception, will only verbose_logger.exception()
        """
        langsmith_api_base = credentials["LANGSMITH_BASE_URL"]
        langsmith_api_key = credentials["LANGSMITH_API_KEY"]
        url = self._add_endpoint_to_url(langsmith_api_base, "runs/batch")
        headers = {"x-api-key": langsmith_api_key}
        elements_to_log = [queue_object["data"] for queue_object in queue_objects]

        try:
            verbose_logger.debug(
                "Sending batch of %s runs to Langsmith", len(elements_to_log)
            )
            response = await self.async_httpx_client.post(
                url=url,
                json={"post": elements_to_log},
                headers=headers,
            )
            response.raise_for_status()

            if response.status_code >= 300:
                verbose_logger.error(
                    f"Langsmith Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.debug(
                    f"Batch of {len(self.log_queue)} runs successfully created"
                )
        except httpx.HTTPStatusError as e:
            verbose_logger.exception(
                f"Langsmith HTTP Error: {e.response.status_code} - {e.response.text}"
            )
        except Exception:
            verbose_logger.exception(
                f"Langsmith Layer Error - {traceback.format_exc()}"
            )

    def _group_batches_by_credentials(self) -> Dict[CredentialsKey, BatchGroup]:
        """Groups queue objects by credentials using a proper key structure"""
        log_queue_by_credentials: Dict[CredentialsKey, BatchGroup] = {}

        for queue_object in self.log_queue:
            credentials = queue_object["credentials"]
            key = CredentialsKey(
                api_key=credentials["LANGSMITH_API_KEY"],
                project=credentials["LANGSMITH_PROJECT"],
                base_url=credentials["LANGSMITH_BASE_URL"],
            )

            if key not in log_queue_by_credentials:
                log_queue_by_credentials[key] = BatchGroup(
                    credentials=credentials, queue_objects=[]
                )

            log_queue_by_credentials[key].queue_objects.append(queue_object)

        return log_queue_by_credentials

    def _get_credentials_to_use_for_request(
        self, kwargs: Dict[str, Any]
    ) -> LangsmithCredentialsObject:
        """
        Handles key/team based logging

        If standard_callback_dynamic_params are provided, use those credentials.

        Otherwise, use the default credentials.
        """
        standard_callback_dynamic_params: Optional[
            StandardCallbackDynamicParams
        ] = kwargs.get("standard_callback_dynamic_params", None)
        if standard_callback_dynamic_params is not None:
            credentials = self.get_credentials_from_env(
                langsmith_api_key=standard_callback_dynamic_params.get(
                    "langsmith_api_key", None
                ),
                langsmith_project=standard_callback_dynamic_params.get(
                    "langsmith_project", None
                ),
                langsmith_base_url=standard_callback_dynamic_params.get(
                    "langsmith_base_url", None
                ),
            )
        else:
            credentials = self.default_credentials
        return credentials

    def _send_batch(self):
        """Calls async_send_batch in an event loop"""
        if not self.log_queue:
            return

        try:
            # Try to get the existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a task
                asyncio.create_task(self.async_send_batch())
            else:
                # If no event loop is running, run the coroutine directly
                loop.run_until_complete(self.async_send_batch())
        except RuntimeError:
            # If we can't get an event loop, create a new one
            asyncio.run(self.async_send_batch())

    def get_run_by_id(self, run_id):
        langsmith_api_key = self.default_credentials["LANGSMITH_API_KEY"]

        langsmith_api_base = self.default_credentials["LANGSMITH_BASE_URL"]

        url = f"{langsmith_api_base}/runs/{run_id}"
        response = litellm.module_level_client.get(
            url=url,
            headers={"x-api-key": langsmith_api_key},
        )

        return response.json()

    def make_dot_order(self, run_id: str):
        st = datetime.now(timezone.utc)
        id_ = run_id
        return st.strftime("%Y%m%dT%H%M%S%fZ") + str(id_)

# === NexusCore/openenv\Lib\site-packages\PIL\BlpImagePlugin.py ===
"""
Blizzard Mipmap Format (.blp)
Jerome Leclanche <jerome@leclan.ch>

The contents of this file are hereby released in the public domain (CC0)
Full text of the CC0 license:
  https://creativecommons.org/publicdomain/zero/1.0/

BLP1 files, used mostly in Warcraft III, are not fully supported.
All types of BLP2 files used in World of Warcraft are supported.

The BLP file structure consists of a header, up to 16 mipmaps of the
texture

Texture sizes must be powers of two, though the two dimensions do
not have to be equal; 512x256 is valid, but 512x200 is not.
The first mipmap (mipmap #0) is the full size image; each subsequent
mipmap halves both dimensions. The final mipmap should be 1x1.

BLP files come in many different flavours:
* JPEG-compressed (type == 0) - only supported for BLP1.
* RAW images (type == 1, encoding == 1). Each mipmap is stored as an
  array of 8-bit values, one per pixel, left to right, top to bottom.
  Each value is an index to the palette.
* DXT-compressed (type == 1, encoding == 2):
- DXT1 compression is used if alpha_encoding == 0.
  - An additional alpha bit is used if alpha_depth == 1.
  - DXT3 compression is used if alpha_encoding == 1.
  - DXT5 compression is used if alpha_encoding == 7.
"""

from __future__ import annotations

import abc
import os
import struct
from enum import IntEnum
from io import BytesIO
from typing import IO

from . import Image, ImageFile


class Format(IntEnum):
    JPEG = 0


class Encoding(IntEnum):
    UNCOMPRESSED = 1
    DXT = 2
    UNCOMPRESSED_RAW_BGRA = 3


class AlphaEncoding(IntEnum):
    DXT1 = 0
    DXT3 = 1
    DXT5 = 7


def unpack_565(i: int) -> tuple[int, int, int]:
    return ((i >> 11) & 0x1F) << 3, ((i >> 5) & 0x3F) << 2, (i & 0x1F) << 3


def decode_dxt1(
    data: bytes, alpha: bool = False
) -> tuple[bytearray, bytearray, bytearray, bytearray]:
    """
    input: one "row" of data (i.e. will produce 4*width pixels)
    """

    blocks = len(data) // 8  # number of blocks in row
    ret = (bytearray(), bytearray(), bytearray(), bytearray())

    for block_index in range(blocks):
        # Decode next 8-byte block.
        idx = block_index * 8
        color0, color1, bits = struct.unpack_from("<HHI", data, idx)

        r0, g0, b0 = unpack_565(color0)
        r1, g1, b1 = unpack_565(color1)

        # Decode this block into 4x4 pixels
        # Accumulate the results onto our 4 row accumulators
        for j in range(4):
            for i in range(4):
                # get next control op and generate a pixel

                control = bits & 3
                bits = bits >> 2

                a = 0xFF
                if control == 0:
                    r, g, b = r0, g0, b0
                elif control == 1:
                    r, g, b = r1, g1, b1
                elif control == 2:
                    if color0 > color1:
                        r = (2 * r0 + r1) // 3
                        g = (2 * g0 + g1) // 3
                        b = (2 * b0 + b1) // 3
                    else:
                        r = (r0 + r1) // 2
                        g = (g0 + g1) // 2
                        b = (b0 + b1) // 2
                elif control == 3:
                    if color0 > color1:
                        r = (2 * r1 + r0) // 3
                        g = (2 * g1 + g0) // 3
                        b = (2 * b1 + b0) // 3
                    else:
                        r, g, b, a = 0, 0, 0, 0

                if alpha:
                    ret[j].extend([r, g, b, a])
                else:
                    ret[j].extend([r, g, b])

    return ret


def decode_dxt3(data: bytes) -> tuple[bytearray, bytearray, bytearray, bytearray]:
    """
    input: one "row" of data (i.e. will produce 4*width pixels)
    """

    blocks = len(data) // 16  # number of blocks in row
    ret = (bytearray(), bytearray(), bytearray(), bytearray())

    for block_index in range(blocks):
        idx = block_index * 16
        block = data[idx : idx + 16]
        # Decode next 16-byte block.
        bits = struct.unpack_from("<8B", block)
        color0, color1 = struct.unpack_from("<HH", block, 8)

        (code,) = struct.unpack_from("<I", block, 12)

        r0, g0, b0 = unpack_565(color0)
        r1, g1, b1 = unpack_565(color1)

        for j in range(4):
            high = False  # Do we want the higher bits?
            for i in range(4):
                alphacode_index = (4 * j + i) // 2
                a = bits[alphacode_index]
                if high:
                    high = False
                    a >>= 4
                else:
                    high = True
                    a &= 0xF
                a *= 17  # We get a value between 0 and 15

                color_code = (code >> 2 * (4 * j + i)) & 0x03

                if color_code == 0:
                    r, g, b = r0, g0, b0
                elif color_code == 1:
                    r, g, b = r1, g1, b1
                elif color_code == 2:
                    r = (2 * r0 + r1) // 3
                    g = (2 * g0 + g1) // 3
                    b = (2 * b0 + b1) // 3
                elif color_code == 3:
                    r = (2 * r1 + r0) // 3
                    g = (2 * g1 + g0) // 3
                    b = (2 * b1 + b0) // 3

                ret[j].extend([r, g, b, a])

    return ret


def decode_dxt5(data: bytes) -> tuple[bytearray, bytearray, bytearray, bytearray]:
    """
    input: one "row" of data (i.e. will produce 4 * width pixels)
    """

    blocks = len(data) // 16  # number of blocks in row
    ret = (bytearray(), bytearray(), bytearray(), bytearray())

    for block_index in range(blocks):
        idx = block_index * 16
        block = data[idx : idx + 16]
        # Decode next 16-byte block.
        a0, a1 = struct.unpack_from("<BB", block)

        bits = struct.unpack_from("<6B", block, 2)
        alphacode1 = bits[2] | (bits[3] << 8) | (bits[4] << 16) | (bits[5] << 24)
        alphacode2 = bits[0] | (bits[1] << 8)

        color0, color1 = struct.unpack_from("<HH", block, 8)

        (code,) = struct.unpack_from("<I", block, 12)

        r0, g0, b0 = unpack_565(color0)
        r1, g1, b1 = unpack_565(color1)

        for j in range(4):
            for i in range(4):
                # get next control op and generate a pixel
                alphacode_index = 3 * (4 * j + i)

                if alphacode_index <= 12:
                    alphacode = (alphacode2 >> alphacode_index) & 0x07
                elif alphacode_index == 15:
                    alphacode = (alphacode2 >> 15) | ((alphacode1 << 1) & 0x06)
                else:  # alphacode_index >= 18 and alphacode_index <= 45
                    alphacode = (alphacode1 >> (alphacode_index - 16)) & 0x07

                if alphacode == 0:
                    a = a0
                elif alphacode == 1:
                    a = a1
                elif a0 > a1:
                    a = ((8 - alphacode) * a0 + (alphacode - 1) * a1) // 7
                elif alphacode == 6:
                    a = 0
                elif alphacode == 7:
                    a = 255
                else:
                    a = ((6 - alphacode) * a0 + (alphacode - 1) * a1) // 5

                color_code = (code >> 2 * (4 * j + i)) & 0x03

                if color_code == 0:
                    r, g, b = r0, g0, b0
                elif color_code == 1:
                    r, g, b = r1, g1, b1
                elif color_code == 2:
                    r = (2 * r0 + r1) // 3
                    g = (2 * g0 + g1) // 3
                    b = (2 * b0 + b1) // 3
                elif color_code == 3:
                    r = (2 * r1 + r0) // 3
                    g = (2 * g1 + g0) // 3
                    b = (2 * b1 + b0) // 3

                ret[j].extend([r, g, b, a])

    return ret


class BLPFormatError(NotImplementedError):
    pass


def _accept(prefix: bytes) -> bool:
    return prefix.startswith((b"BLP1", b"BLP2"))


class BlpImageFile(ImageFile.ImageFile):
    """
    Blizzard Mipmap Format
    """

    format = "BLP"
    format_description = "Blizzard Mipmap Format"

    def _open(self) -> None:
        self.magic = self.fp.read(4)
        if not _accept(self.magic):
            msg = f"Bad BLP magic {repr(self.magic)}"
            raise BLPFormatError(msg)

        compression = struct.unpack("<i", self.fp.read(4))[0]
        if self.magic == b"BLP1":
            alpha = struct.unpack("<I", self.fp.read(4))[0] != 0
        else:
            encoding = struct.unpack("<b", self.fp.read(1))[0]
            alpha = struct.unpack("<b", self.fp.read(1))[0] != 0
            alpha_encoding = struct.unpack("<b", self.fp.read(1))[0]
            self.fp.seek(1, os.SEEK_CUR)  # mips

        self._size = struct.unpack("<II", self.fp.read(8))

        args: tuple[int, int, bool] | tuple[int, int, bool, int]
        if self.magic == b"BLP1":
            encoding = struct.unpack("<i", self.fp.read(4))[0]
            self.fp.seek(4, os.SEEK_CUR)  # subtype

            args = (compression, encoding, alpha)
            offset = 28
        else:
            args = (compression, encoding, alpha, alpha_encoding)
            offset = 20

        decoder = self.magic.decode()

        self._mode = "RGBA" if alpha else "RGB"
        self.tile = [ImageFile._Tile(decoder, (0, 0) + self.size, offset, args)]


class _BLPBaseDecoder(abc.ABC, ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        try:
            self._read_header()
            self._load()
        except struct.error as e:
            msg = "Truncated BLP file"
            raise OSError(msg) from e
        return -1, 0

    @abc.abstractmethod
    def _load(self) -> None:
        pass

    def _read_header(self) -> None:
        self._offsets = struct.unpack("<16I", self._safe_read(16 * 4))
        self._lengths = struct.unpack("<16I", self._safe_read(16 * 4))

    def _safe_read(self, length: int) -> bytes:
        assert self.fd is not None
        return ImageFile._safe_read(self.fd, length)

    def _read_palette(self) -> list[tuple[int, int, int, int]]:
        ret = []
        for i in range(256):
            try:
                b, g, r, a = struct.unpack("<4B", self._safe_read(4))
            except struct.error:
                break
            ret.append((b, g, r, a))
        return ret

    def _read_bgra(
        self, palette: list[tuple[int, int, int, int]], alpha: bool
    ) -> bytearray:
        data = bytearray()
        _data = BytesIO(self._safe_read(self._lengths[0]))
        while True:
            try:
                (offset,) = struct.unpack("<B", _data.read(1))
            except struct.error:
                break
            b, g, r, a = palette[offset]
            d: tuple[int, ...] = (r, g, b)
            if alpha:
                d += (a,)
            data.extend(d)
        return data


class BLP1Decoder(_BLPBaseDecoder):
    def _load(self) -> None:
        self._compression, self._encoding, alpha = self.args

        if self._compression == Format.JPEG:
            self._decode_jpeg_stream()

        elif self._compression == 1:
            if self._encoding in (4, 5):
                palette = self._read_palette()
                data = self._read_bgra(palette, alpha)
                self.set_as_raw(data)
            else:
                msg = f"Unsupported BLP encoding {repr(self._encoding)}"
                raise BLPFormatError(msg)
        else:
            msg = f"Unsupported BLP compression {repr(self._encoding)}"
            raise BLPFormatError(msg)

    def _decode_jpeg_stream(self) -> None:
        from .JpegImagePlugin import JpegImageFile

        (jpeg_header_size,) = struct.unpack("<I", self._safe_read(4))
        jpeg_header = self._safe_read(jpeg_header_size)
        assert self.fd is not None
        self._safe_read(self._offsets[0] - self.fd.tell())  # What IS this?
        data = self._safe_read(self._lengths[0])
        data = jpeg_header + data
        image = JpegImageFile(BytesIO(data))
        Image._decompression_bomb_check(image.size)
        if image.mode == "CMYK":
            args = image.tile[0].args
            assert isinstance(args, tuple)
            image.tile = [image.tile[0]._replace(args=(args[0], "CMYK"))]
        self.set_as_raw(image.convert("RGB").tobytes(), "BGR")


class BLP2Decoder(_BLPBaseDecoder):
    def _load(self) -> None:
        self._compression, self._encoding, alpha, self._alpha_encoding = self.args

        palette = self._read_palette()

        assert self.fd is not None
        self.fd.seek(self._offsets[0])

        if self._compression == 1:
            # Uncompressed or DirectX compression

            if self._encoding == Encoding.UNCOMPRESSED:
                data = self._read_bgra(palette, alpha)

            elif self._encoding == Encoding.DXT:
                data = bytearray()
                if self._alpha_encoding == AlphaEncoding.DXT1:
                    linesize = (self.state.xsize + 3) // 4 * 8
                    for yb in range((self.state.ysize + 3) // 4):
                        for d in decode_dxt1(self._safe_read(linesize), alpha):
                            data += d

                elif self._alpha_encoding == AlphaEncoding.DXT3:
                    linesize = (self.state.xsize + 3) // 4 * 16
                    for yb in range((self.state.ysize + 3) // 4):
                        for d in decode_dxt3(self._safe_read(linesize)):
                            data += d

                elif self._alpha_encoding == AlphaEncoding.DXT5:
                    linesize = (self.state.xsize + 3) // 4 * 16
                    for yb in range((self.state.ysize + 3) // 4):
                        for d in decode_dxt5(self._safe_read(linesize)):
                            data += d
                else:
                    msg = f"Unsupported alpha encoding {repr(self._alpha_encoding)}"
                    raise BLPFormatError(msg)
            else:
                msg = f"Unknown BLP encoding {repr(self._encoding)}"
                raise BLPFormatError(msg)

        else:
            msg = f"Unknown BLP compression {repr(self._compression)}"
            raise BLPFormatError(msg)

        self.set_as_raw(data)


class BLPEncoder(ImageFile.PyEncoder):
    _pushes_fd = True

    def _write_palette(self) -> bytes:
        data = b""
        assert self.im is not None
        palette = self.im.getpalette("RGBA", "RGBA")
        for i in range(len(palette) // 4):
            r, g, b, a = palette[i * 4 : (i + 1) * 4]
            data += struct.pack("<4B", b, g, r, a)
        while len(data) < 256 * 4:
            data += b"\x00" * 4
        return data

    def encode(self, bufsize: int) -> tuple[int, int, bytes]:
        palette_data = self._write_palette()

        offset = 20 + 16 * 4 * 2 + len(palette_data)
        data = struct.pack("<16I", offset, *((0,) * 15))

        assert self.im is not None
        w, h = self.im.size
        data += struct.pack("<16I", w * h, *((0,) * 15))

        data += palette_data

        for y in range(h):
            for x in range(w):
                data += struct.pack("<B", self.im.getpixel((x, y)))

        return len(data), 0, data


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode != "P":
        msg = "Unsupported BLP image mode"
        raise ValueError(msg)

    magic = b"BLP1" if im.encoderinfo.get("blp_version") == "BLP1" else b"BLP2"
    fp.write(magic)

    assert im.palette is not None
    fp.write(struct.pack("<i", 1))  # Uncompressed or DirectX compression

    alpha_depth = 1 if im.palette.mode == "RGBA" else 0
    if magic == b"BLP1":
        fp.write(struct.pack("<L", alpha_depth))
    else:
        fp.write(struct.pack("<b", Encoding.UNCOMPRESSED))
        fp.write(struct.pack("<b", alpha_depth))
        fp.write(struct.pack("<b", 0))  # alpha encoding
        fp.write(struct.pack("<b", 0))  # mips
    fp.write(struct.pack("<II", *im.size))
    if magic == b"BLP1":
        fp.write(struct.pack("<i", 5))
        fp.write(struct.pack("<i", 0))

    ImageFile._save(im, fp, [ImageFile._Tile("BLP", (0, 0) + im.size, 0, im.mode)])


Image.register_open(BlpImageFile.format, BlpImageFile, _accept)
Image.register_extension(BlpImageFile.format, ".blp")
Image.register_decoder("BLP1", BLP1Decoder)
Image.register_decoder("BLP2", BLP2Decoder)

Image.register_save(BlpImageFile.format, _save)
Image.register_encoder("BLP", BLPEncoder)

# === NexusCore/openenv\Lib\site-packages\google\auth\compute_engine\credentials.py ===
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

"""Google Compute Engine credentials.

This module provides authentication for an application running on Google
Compute Engine using the Compute Engine metadata server.

"""

import datetime

from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.auth import iam
from google.auth import jwt
from google.auth import metrics
from google.auth.compute_engine import _metadata
from google.oauth2 import _client


class Credentials(
    credentials.Scoped,
    credentials.CredentialsWithQuotaProject,
    credentials.CredentialsWithUniverseDomain,
):
    """Compute Engine Credentials.

    These credentials use the Google Compute Engine metadata server to obtain
    OAuth 2.0 access tokens associated with the instance's service account,
    and are also used for Cloud Run, Flex and App Engine (except for the Python
    2.7 runtime, which is supported only on older versions of this library).

    For more information about Compute Engine authentication, including how
    to configure scopes, see the `Compute Engine authentication
    documentation`_.

    .. note:: On Compute Engine the metadata server ignores requested scopes.
        On Cloud Run, Flex and App Engine the server honours requested scopes.

    .. _Compute Engine authentication documentation:
        https://cloud.google.com/compute/docs/authentication#using
    """

    def __init__(
        self,
        service_account_email="default",
        quota_project_id=None,
        scopes=None,
        default_scopes=None,
        universe_domain=None,
    ):
        """
        Args:
            service_account_email (str): The service account email to use, or
                'default'. A Compute Engine instance may have multiple service
                accounts.
            quota_project_id (Optional[str]): The project ID used for quota and
                billing.
            scopes (Optional[Sequence[str]]): The list of scopes for the credentials.
            default_scopes (Optional[Sequence[str]]): Default scopes passed by a
                Google client library. Use 'scopes' for user-defined scopes.
            universe_domain (Optional[str]): The universe domain. If not
                provided or None, credential will attempt to fetch the value
                from metadata server. If metadata server doesn't have universe
                domain endpoint, then the default googleapis.com will be used.
        """
        super(Credentials, self).__init__()
        self._service_account_email = service_account_email
        self._quota_project_id = quota_project_id
        self._scopes = scopes
        self._default_scopes = default_scopes
        self._universe_domain_cached = False
        if universe_domain:
            self._universe_domain = universe_domain
            self._universe_domain_cached = True

    def _retrieve_info(self, request):
        """Retrieve information about the service account.

        Updates the scopes and retrieves the full service account email.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.
        """
        info = _metadata.get_service_account_info(
            request, service_account=self._service_account_email
        )

        self._service_account_email = info["email"]

        # Don't override scopes requested by the user.
        if self._scopes is None:
            self._scopes = info["scopes"]

    def _metric_header_for_usage(self):
        return metrics.CRED_TYPE_SA_MDS

    def refresh(self, request):
        """Refresh the access token and scopes.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If the Compute Engine metadata
                service can't be reached if if the instance has not
                credentials.
        """
        scopes = self._scopes if self._scopes is not None else self._default_scopes
        try:
            self._retrieve_info(request)
            # Always fetch token with default service account email.
            self.token, self.expiry = _metadata.get_service_account_token(
                request, service_account="default", scopes=scopes
            )
        except exceptions.TransportError as caught_exc:
            new_exc = exceptions.RefreshError(caught_exc)
            raise new_exc from caught_exc

    @property
    def service_account_email(self):
        """The service account email.

        .. note:: This is not guaranteed to be set until :meth:`refresh` has been
            called.
        """
        return self._service_account_email

    @property
    def requires_scopes(self):
        return not self._scopes

    @property
    def universe_domain(self):
        if self._universe_domain_cached:
            return self._universe_domain

        from google.auth.transport import requests as google_auth_requests

        self._universe_domain = _metadata.get_universe_domain(
            google_auth_requests.Request()
        )
        self._universe_domain_cached = True
        return self._universe_domain

    @_helpers.copy_docstring(credentials.Credentials)
    def get_cred_info(self):
        return {
            "credential_source": "metadata server",
            "credential_type": "VM credentials",
            "principal": self.service_account_email,
        }

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        creds = self.__class__(
            service_account_email=self._service_account_email,
            quota_project_id=quota_project_id,
            scopes=self._scopes,
            default_scopes=self._default_scopes,
        )
        creds._universe_domain = self._universe_domain
        creds._universe_domain_cached = self._universe_domain_cached
        return creds

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes, default_scopes=None):
        # Compute Engine credentials can not be scoped (the metadata service
        # ignores the scopes parameter). App Engine, Cloud Run and Flex support
        # requesting scopes.
        creds = self.__class__(
            scopes=scopes,
            default_scopes=default_scopes,
            service_account_email=self._service_account_email,
            quota_project_id=self._quota_project_id,
        )
        creds._universe_domain = self._universe_domain
        creds._universe_domain_cached = self._universe_domain_cached
        return creds

    @_helpers.copy_docstring(credentials.CredentialsWithUniverseDomain)
    def with_universe_domain(self, universe_domain):
        return self.__class__(
            scopes=self._scopes,
            default_scopes=self._default_scopes,
            service_account_email=self._service_account_email,
            quota_project_id=self._quota_project_id,
            universe_domain=universe_domain,
        )


_DEFAULT_TOKEN_LIFETIME_SECS = 3600  # 1 hour in seconds
_DEFAULT_TOKEN_URI = "https://www.googleapis.com/oauth2/v4/token"


class IDTokenCredentials(
    credentials.CredentialsWithQuotaProject,
    credentials.Signing,
    credentials.CredentialsWithTokenUri,
):
    """Open ID Connect ID Token-based service account credentials.

    These credentials relies on the default service account of a GCE instance.

    ID token can be requested from `GCE metadata server identity endpoint`_, IAM
    token endpoint or other token endpoints you specify. If metadata server
    identity endpoint is not used, the GCE instance must have been started with
    a service account that has access to the IAM Cloud API.

    .. _GCE metadata server identity endpoint:
        https://cloud.google.com/compute/docs/instances/verifying-instance-identity
    """

    def __init__(
        self,
        request,
        target_audience,
        token_uri=None,
        additional_claims=None,
        service_account_email=None,
        signer=None,
        use_metadata_identity_endpoint=False,
        quota_project_id=None,
    ):
        """
        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.
            target_audience (str): The intended audience for these credentials,
                used when requesting the ID Token. The ID Token's ``aud`` claim
                will be set to this string.
            token_uri (str): The OAuth 2.0 Token URI.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT assertion used in the authorization grant.
            service_account_email (str): Optional explicit service account to
                use to sign JWT tokens.
                By default, this is the default GCE service account.
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
                In case the signer is specified, the request argument will be
                ignored.
            use_metadata_identity_endpoint (bool): Whether to use GCE metadata
                identity endpoint. For backward compatibility the default value
                is False. If set to True, ``token_uri``, ``additional_claims``,
                ``service_account_email``, ``signer`` argument should not be set;
                otherwise ValueError will be raised.
            quota_project_id (Optional[str]): The project ID used for quota and
                billing.

        Raises:
            ValueError:
                If ``use_metadata_identity_endpoint`` is set to True, and one of
                ``token_uri``, ``additional_claims``, ``service_account_email``,
                 ``signer`` arguments is set.
        """
        super(IDTokenCredentials, self).__init__()

        self._quota_project_id = quota_project_id
        self._use_metadata_identity_endpoint = use_metadata_identity_endpoint
        self._target_audience = target_audience

        if use_metadata_identity_endpoint:
            if token_uri or additional_claims or service_account_email or signer:
                raise exceptions.MalformedError(
                    "If use_metadata_identity_endpoint is set, token_uri, "
                    "additional_claims, service_account_email, signer arguments"
                    " must not be set"
                )
            self._token_uri = None
            self._additional_claims = None
            self._signer = None

        if service_account_email is None:
            sa_info = _metadata.get_service_account_info(request)
            self._service_account_email = sa_info["email"]
        else:
            self._service_account_email = service_account_email

        if not use_metadata_identity_endpoint:
            if signer is None:
                signer = iam.Signer(
                    request=request,
                    credentials=Credentials(),
                    service_account_email=self._service_account_email,
                )
            self._signer = signer
            self._token_uri = token_uri or _DEFAULT_TOKEN_URI

            if additional_claims is not None:
                self._additional_claims = additional_claims
            else:
                self._additional_claims = {}

    def with_target_audience(self, target_audience):
        """Create a copy of these credentials with the specified target
        audience.
        Args:
            target_audience (str): The intended audience for these credentials,
            used when requesting the ID Token.
        Returns:
            google.auth.service_account.IDTokenCredentials: A new credentials
                instance.
        """
        # since the signer is already instantiated,
        # the request is not needed
        if self._use_metadata_identity_endpoint:
            return self.__class__(
                None,
                target_audience=target_audience,
                use_metadata_identity_endpoint=True,
                quota_project_id=self._quota_project_id,
            )
        else:
            return self.__class__(
                None,
                service_account_email=self._service_account_email,
                token_uri=self._token_uri,
                target_audience=target_audience,
                additional_claims=self._additional_claims.copy(),
                signer=self.signer,
                use_metadata_identity_endpoint=False,
                quota_project_id=self._quota_project_id,
            )

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):

        # since the signer is already instantiated,
        # the request is not needed
        if self._use_metadata_identity_endpoint:
            return self.__class__(
                None,
                target_audience=self._target_audience,
                use_metadata_identity_endpoint=True,
                quota_project_id=quota_project_id,
            )
        else:
            return self.__class__(
                None,
                service_account_email=self._service_account_email,
                token_uri=self._token_uri,
                target_audience=self._target_audience,
                additional_claims=self._additional_claims.copy(),
                signer=self.signer,
                use_metadata_identity_endpoint=False,
                quota_project_id=quota_project_id,
            )

    @_helpers.copy_docstring(credentials.CredentialsWithTokenUri)
    def with_token_uri(self, token_uri):

        # since the signer is already instantiated,
        # the request is not needed
        if self._use_metadata_identity_endpoint:
            raise exceptions.MalformedError(
                "If use_metadata_identity_endpoint is set, token_uri" " must not be set"
            )
        else:
            return self.__class__(
                None,
                service_account_email=self._service_account_email,
                token_uri=token_uri,
                target_audience=self._target_audience,
                additional_claims=self._additional_claims.copy(),
                signer=self.signer,
                use_metadata_identity_endpoint=False,
                quota_project_id=self.quota_project_id,
            )

    def _make_authorization_grant_assertion(self):
        """Create the OAuth 2.0 assertion.
        This assertion is used during the OAuth 2.0 grant to acquire an
        ID token.
        Returns:
            bytes: The authorization grant assertion.
        """
        now = _helpers.utcnow()
        lifetime = datetime.timedelta(seconds=_DEFAULT_TOKEN_LIFETIME_SECS)
        expiry = now + lifetime

        payload = {
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
            # The issuer must be the service account email.
            "iss": self.service_account_email,
            # The audience must be the auth token endpoint's URI
            "aud": self._token_uri,
            # The target audience specifies which service the ID token is
            # intended for.
            "target_audience": self._target_audience,
        }

        payload.update(self._additional_claims)

        token = jwt.encode(self._signer, payload)

        return token

    def _call_metadata_identity_endpoint(self, request):
        """Request ID token from metadata identity endpoint.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Returns:
            Tuple[str, datetime.datetime]: The ID token and the expiry of the ID token.

        Raises:
            google.auth.exceptions.RefreshError: If the Compute Engine metadata
                service can't be reached or if the instance has no credentials.
            ValueError: If extracting expiry from the obtained ID token fails.
        """
        try:
            path = "instance/service-accounts/default/identity"
            params = {"audience": self._target_audience, "format": "full"}
            metrics_header = {
                metrics.API_CLIENT_HEADER: metrics.token_request_id_token_mds()
            }
            id_token = _metadata.get(
                request, path, params=params, headers=metrics_header
            )
        except exceptions.TransportError as caught_exc:
            new_exc = exceptions.RefreshError(caught_exc)
            raise new_exc from caught_exc

        _, payload, _, _ = jwt._unverified_decode(id_token)
        return id_token, datetime.datetime.utcfromtimestamp(payload["exp"])

    def refresh(self, request):
        """Refreshes the ID token.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If the credentials could
                not be refreshed.
            ValueError: If extracting expiry from the obtained ID token fails.
        """
        if self._use_metadata_identity_endpoint:
            self.token, self.expiry = self._call_metadata_identity_endpoint(request)
        else:
            assertion = self._make_authorization_grant_assertion()
            access_token, expiry, _ = _client.id_token_jwt_grant(
                request, self._token_uri, assertion
            )
            self.token = access_token
            self.expiry = expiry

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer(self):
        return self._signer

    def sign_bytes(self, message):
        """Signs the given message.

        Args:
            message (bytes): The message to sign.

        Returns:
            bytes: The message's cryptographic signature.

        Raises:
            ValueError:
                Signer is not available if metadata identity endpoint is used.
        """
        if self._use_metadata_identity_endpoint:
            raise exceptions.InvalidOperation(
                "Signer is not available if metadata identity endpoint is used"
            )
        return self._signer.sign(message)

    @property
    def service_account_email(self):
        """The service account email."""
        return self._service_account_email

    @property
    def signer_email(self):
        return self._service_account_email