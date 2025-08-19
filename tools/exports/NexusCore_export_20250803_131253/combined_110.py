
# === NexusCore/tools\exports\export_20250803_114325\combined_149.py ===

# === NexusCore/openenv\Lib\site-packages\ipykernel\zmqshell.py ===
"""A ZMQ-based subclass of InteractiveShell.

This code is meant to ease the refactoring of the base InteractiveShell into
something with a cleaner architecture for 2-process use, without actually
breaking InteractiveShell itself.  So we're doing something a bit ugly, where
we subclass and override what we want to fix.  Once this is working well, we
can go back to the base class and refactor the code for a cleaner inheritance
implementation that doesn't rely on so much monkeypatching.

But this lets us maintain a fully working IPython as we develop the new
machinery.  This should thus be thought of as scaffolding.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import sys
import warnings
from pathlib import Path
from threading import local

from IPython.core import page, payloadpage
from IPython.core.autocall import ZMQExitAutocall
from IPython.core.displaypub import DisplayPublisher
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.core.magic import Magics, line_magic, magics_class
from IPython.core.magics import CodeMagics, MacroToEdit  # type:ignore[attr-defined]
from IPython.core.usage import default_banner
from IPython.display import Javascript, display
from IPython.utils import openpy
from IPython.utils.process import arg_split, system  # type:ignore[attr-defined]
from jupyter_client.session import Session, extract_header
from jupyter_core.paths import jupyter_runtime_dir
from traitlets import Any, CBool, CBytes, Dict, Instance, Type, default, observe

from ipykernel import connect_qtconsole, get_connection_file, get_connection_info
from ipykernel.displayhook import ZMQShellDisplayHook
from ipykernel.jsonutil import encode_images, json_clean

# -----------------------------------------------------------------------------
# Functions and classes
# -----------------------------------------------------------------------------


class ZMQDisplayPublisher(DisplayPublisher):
    """A display publisher that publishes data using a ZeroMQ PUB socket."""

    session = Instance(Session, allow_none=True)
    pub_socket = Any(allow_none=True)
    parent_header = Dict({})
    topic = CBytes(b"display_data")

    # thread_local:
    # An attribute used to ensure the correct output message
    # is processed. See ipykernel Issue 113 for a discussion.
    _thread_local = Any()

    def set_parent(self, parent):
        """Set the parent for outbound messages."""
        self.parent_header = extract_header(parent)

    def _flush_streams(self):
        """flush IO Streams prior to display"""
        sys.stdout.flush()
        sys.stderr.flush()

    @default("_thread_local")
    def _default_thread_local(self):
        """Initialize our thread local storage"""
        return local()

    @property
    def _hooks(self):
        if not hasattr(self._thread_local, "hooks"):
            # create new list for a new thread
            self._thread_local.hooks = []
        return self._thread_local.hooks

    def publish(
        self,
        data,
        metadata=None,
        transient=None,
        update=False,
    ):
        """Publish a display-data message

        Parameters
        ----------
        data : dict
            A mime-bundle dict, keyed by mime-type.
        metadata : dict, optional
            Metadata associated with the data.
        transient : dict, optional, keyword-only
            Transient data that may only be relevant during a live display,
            such as display_id.
            Transient data should not be persisted to documents.
        update : bool, optional, keyword-only
            If True, send an update_display_data message instead of display_data.
        """
        self._flush_streams()
        if metadata is None:
            metadata = {}
        if transient is None:
            transient = {}
        self._validate_data(data, metadata)
        content = {}
        content["data"] = encode_images(data)
        content["metadata"] = metadata
        content["transient"] = transient

        msg_type = "update_display_data" if update else "display_data"

        # Use 2-stage process to send a message,
        # in order to put it through the transform
        # hooks before potentially sending.
        assert self.session is not None
        msg = self.session.msg(msg_type, json_clean(content), parent=self.parent_header)

        # Each transform either returns a new
        # message or None. If None is returned,
        # the message has been 'used' and we return.
        for hook in self._hooks:
            msg = hook(msg)
            if msg is None:
                return  # type:ignore[unreachable]

        self.session.send(
            self.pub_socket,
            msg,
            ident=self.topic,
        )

    def clear_output(self, wait=False):
        """Clear output associated with the current execution (cell).

        Parameters
        ----------
        wait : bool (default: False)
            If True, the output will not be cleared immediately,
            instead waiting for the next display before clearing.
            This reduces bounce during repeated clear & display loops.

        """
        content = dict(wait=wait)
        self._flush_streams()
        assert self.session is not None
        msg = self.session.msg("clear_output", json_clean(content), parent=self.parent_header)

        # see publish() for details on how this works
        for hook in self._hooks:
            msg = hook(msg)
            if msg is None:
                return  # type:ignore[unreachable]

        self.session.send(
            self.pub_socket,
            msg,
            ident=self.topic,
        )

    def register_hook(self, hook):
        """
        Registers a hook with the thread-local storage.

        Parameters
        ----------
        hook : Any callable object

        Returns
        -------
        Either a publishable message, or `None`.
        The DisplayHook objects must return a message from
        the __call__ method if they still require the
        `session.send` method to be called after transformation.
        Returning `None` will halt that execution path, and
        session.send will not be called.
        """
        self._hooks.append(hook)

    def unregister_hook(self, hook):
        """
        Un-registers a hook with the thread-local storage.

        Parameters
        ----------
        hook : Any callable object which has previously been
            registered as a hook.

        Returns
        -------
        bool - `True` if the hook was removed, `False` if it wasn't
            found.
        """
        try:
            self._hooks.remove(hook)
            return True
        except ValueError:
            return False


@magics_class
class KernelMagics(Magics):
    """Kernel magics."""

    # ------------------------------------------------------------------------
    # Magic overrides
    # ------------------------------------------------------------------------
    # Once the base class stops inheriting from magic, this code needs to be
    # moved into a separate machinery as well.  For now, at least isolate here
    # the magics which this class needs to implement differently from the base
    # class, or that are unique to it.

    @line_magic
    def edit(self, parameter_s="", last_call=None):
        """Bring up an editor and execute the resulting code.

        Usage:
          %edit [options] [args]

        %edit runs an external text editor. You will need to set the command for
        this editor via the ``TerminalInteractiveShell.editor`` option in your
        configuration file before it will work.

        This command allows you to conveniently edit multi-line code right in
        your IPython session.

        If called without arguments, %edit opens up an empty editor with a
        temporary file and will execute the contents of this file when you
        close it (don't forget to save it!).

        Options:

        -n <number>
          Open the editor at a specified line number. By default, the IPython
          editor hook uses the unix syntax 'editor +N filename', but you can
          configure this by providing your own modified hook if your favorite
          editor supports line-number specifications with a different syntax.

        -p
          Call the editor with the same data as the previous time it was used,
          regardless of how long ago (in your current session) it was.

        -r
          Use 'raw' input. This option only applies to input taken from the
          user's history.  By default, the 'processed' history is used, so that
          magics are loaded in their transformed version to valid Python.  If
          this option is given, the raw input as typed as the command line is
          used instead.  When you exit the editor, it will be executed by
          IPython's own processor.

        Arguments:

        If arguments are given, the following possibilities exist:

        - The arguments are numbers or pairs of colon-separated numbers (like
          1 4:8 9). These are interpreted as lines of previous input to be
          loaded into the editor. The syntax is the same of the %macro command.

        - If the argument doesn't start with a number, it is evaluated as a
          variable and its contents loaded into the editor. You can thus edit
          any string which contains python code (including the result of
          previous edits).

        - If the argument is the name of an object (other than a string),
          IPython will try to locate the file where it was defined and open the
          editor at the point where it is defined. You can use ``%edit function``
          to load an editor exactly at the point where 'function' is defined,
          edit it and have the file be executed automatically.

          If the object is a macro (see %macro for details), this opens up your
          specified editor with a temporary file containing the macro's data.
          Upon exit, the macro is reloaded with the contents of the file.

          Note: opening at an exact line is only supported under Unix, and some
          editors (like kedit and gedit up to Gnome 2.8) do not understand the
          '+NUMBER' parameter necessary for this feature. Good editors like
          (X)Emacs, vi, jed, pico and joe all do.

        - If the argument is not found as a variable, IPython will look for a
          file with that name (adding .py if necessary) and load it into the
          editor. It will execute its contents with execfile() when you exit,
          loading any code in the file into your interactive namespace.

        Unlike in the terminal, this is designed to use a GUI editor, and we do
        not know when it has closed. So the file you edit will not be
        automatically executed or printed.

        Note that %edit is also available through the alias %ed.
        """
        last_call = last_call or ["", ""]
        opts, args = self.parse_options(parameter_s, "prn:")

        try:
            filename, lineno, _ = CodeMagics._find_edit_target(self.shell, args, opts, last_call)
        except MacroToEdit:
            # TODO: Implement macro editing over 2 processes.
            print("Macro editing not yet implemented in 2-process model.")
            return

        # Make sure we send to the client an absolute path, in case the working
        # directory of client and kernel don't match
        filename = str(Path(filename).resolve())

        payload = {"source": "edit_magic", "filename": filename, "line_number": lineno}
        assert self.shell is not None
        self.shell.payload_manager.write_payload(payload)

    # A few magics that are adapted to the specifics of using pexpect and a
    # remote terminal

    @line_magic
    def clear(self, arg_s):
        """Clear the terminal."""
        assert self.shell is not None
        if os.name == "posix":
            self.shell.system("clear")
        else:
            self.shell.system("cls")

    if os.name == "nt":
        # This is the usual name in windows
        cls = line_magic("cls")(clear)

    # Terminal pagers won't work over pexpect, but we do have our own pager

    @line_magic
    def less(self, arg_s):
        """Show a file through the pager.

        Files ending in .py are syntax-highlighted."""
        if not arg_s:
            msg = "Missing filename."
            raise UsageError(msg)

        if arg_s.endswith(".py"):
            assert self.shell is not None
            cont = self.shell.pycolorize(openpy.read_py_file(arg_s, skip_encoding_cookie=False))
        else:
            with open(arg_s) as fid:
                cont = fid.read()
        page.page(cont)

    more = line_magic("more")(less)

    # Man calls a pager, so we also need to redefine it
    if os.name == "posix":

        @line_magic
        def man(self, arg_s):
            """Find the man page for the given command and display in pager."""
            assert self.shell is not None
            page.page(self.shell.getoutput("man %s | col -b" % arg_s, split=False))

    @line_magic
    def connect_info(self, arg_s):
        """Print information for connecting other clients to this kernel

        It will print the contents of this session's connection file, as well as
        shortcuts for local clients.

        In the simplest case, when called from the most recently launched kernel,
        secondary clients can be connected, simply with:

        $> jupyter <app> --existing

        """

        try:
            connection_file = get_connection_file()
            info = get_connection_info(unpack=False)
        except Exception as e:
            warnings.warn("Could not get connection info: %r" % e, stacklevel=2)
            return

        # if it's in the default dir, truncate to basename
        if jupyter_runtime_dir() == str(Path(connection_file).parent):
            connection_file = Path(connection_file).name

        assert isinstance(info, str)
        print(info + "\n")
        print(
            f"Paste the above JSON into a file, and connect with:\n"
            f"    $> jupyter <app> --existing <file>\n"
            f"or, if you are local, you can connect with just:\n"
            f"    $> jupyter <app> --existing {connection_file}\n"
            f"or even just:\n"
            f"    $> jupyter <app> --existing\n"
            f"if this is the most recent Jupyter kernel you have started."
        )

    @line_magic
    def qtconsole(self, arg_s):
        """Open a qtconsole connected to this kernel.

        Useful for connecting a qtconsole to running notebooks, for better
        debugging.
        """

        # %qtconsole should imply bind_kernel for engines:
        # FIXME: move to ipyparallel Kernel subclass
        if "ipyparallel" in sys.modules:
            from ipyparallel import bind_kernel

            bind_kernel()

        try:
            connect_qtconsole(argv=arg_split(arg_s, os.name == "posix"))
        except Exception as e:
            warnings.warn("Could not start qtconsole: %r" % e, stacklevel=2)
            return

    @line_magic
    def autosave(self, arg_s):
        """Set the autosave interval in the notebook (in seconds).

        The default value is 120, or two minutes.
        ``%autosave 0`` will disable autosave.

        This magic only has an effect when called from the notebook interface.
        It has no effect when called in a startup file.
        """

        try:
            interval = int(arg_s)
        except ValueError as e:
            raise UsageError("%%autosave requires an integer, got %r" % arg_s) from e

        # javascript wants milliseconds
        milliseconds = 1000 * interval
        display(
            Javascript("IPython.notebook.set_autosave_interval(%i)" % milliseconds),
            include=["application/javascript"],
        )
        if interval:
            print("Autosaving every %i seconds" % interval)
        else:
            print("Autosave disabled")


class ZMQInteractiveShell(InteractiveShell):
    """A subclass of InteractiveShell for ZMQ."""

    displayhook_class = Type(ZMQShellDisplayHook)
    display_pub_class = Type(ZMQDisplayPublisher)
    data_pub_class = Any()  # type:ignore[assignment]
    kernel = Any()
    parent_header = Any()

    @default("banner1")
    def _default_banner1(self):
        return default_banner

    # Override the traitlet in the parent class, because there's no point using
    # readline for the kernel. Can be removed when the readline code is moved
    # to the terminal frontend.
    readline_use = CBool(False)
    # autoindent has no meaning in a zmqshell, and attempting to enable it
    # will print a warning in the absence of readline.
    autoindent = CBool(False)

    exiter = Instance(ZMQExitAutocall)

    @default("exiter")
    def _default_exiter(self):
        return ZMQExitAutocall(self)

    @observe("exit_now")
    def _update_exit_now(self, change):
        """stop eventloop when exit_now fires"""
        if change["new"]:
            if hasattr(self.kernel, "io_loop"):
                loop = self.kernel.io_loop
                loop.call_later(0.1, loop.stop)
            if self.kernel.eventloop:
                exit_hook = getattr(self.kernel.eventloop, "exit_hook", None)
                if exit_hook:
                    exit_hook(self.kernel)

    keepkernel_on_exit = None

    # Over ZeroMQ, GUI control isn't done with PyOS_InputHook as there is no
    # interactive input being read; we provide event loop support in ipkernel
    def enable_gui(self, gui):
        """Enable a given guil."""
        from .eventloops import enable_gui as real_enable_gui

        try:
            real_enable_gui(gui)
            self.active_eventloop = gui
        except ValueError as e:
            raise UsageError("%s" % e) from e

    def init_environment(self):
        """Configure the user's environment."""
        env = os.environ
        # These two ensure 'ls' produces nice coloring on BSD-derived systems
        env["TERM"] = "xterm-color"
        env["CLICOLOR"] = "1"
        # These two add terminal color in tools that support it.
        env["FORCE_COLOR"] = "1"
        env["CLICOLOR_FORCE"] = "1"
        # Since normal pagers don't work at all (over pexpect we don't have
        # single-key control of the subprocess), try to disable paging in
        # subprocesses as much as possible.
        env["PAGER"] = "cat"
        env["GIT_PAGER"] = "cat"

    def init_hooks(self):
        """Initialize hooks."""
        super().init_hooks()
        self.set_hook("show_in_pager", page.as_hook(payloadpage.page), 99)

    def init_data_pub(self):
        """Delay datapub init until request, for deprecation warnings"""

    @property
    def data_pub(self):
        if not hasattr(self, "_data_pub"):
            warnings.warn(
                "InteractiveShell.data_pub is deprecated outside IPython parallel.",
                DeprecationWarning,
                stacklevel=2,
            )

            self._data_pub = self.data_pub_class(parent=self)  # type:ignore[has-type]
            self._data_pub.session = self.display_pub.session  # type:ignore[attr-defined]
            self._data_pub.pub_socket = self.display_pub.pub_socket  # type:ignore[attr-defined]
        return self._data_pub

    @data_pub.setter
    def data_pub(self, pub):
        self._data_pub = pub

    def ask_exit(self):
        """Engage the exit actions."""
        self.exit_now = not self.keepkernel_on_exit
        payload = dict(
            source="ask_exit",
            keepkernel=self.keepkernel_on_exit,
        )
        self.payload_manager.write_payload(payload)  # type:ignore[union-attr]

    def run_cell(self, *args, **kwargs):
        """Run a cell."""
        self._last_traceback = None
        return super().run_cell(*args, **kwargs)

    def _showtraceback(self, etype, evalue, stb):
        # try to preserve ordering of tracebacks and print statements
        sys.stdout.flush()
        sys.stderr.flush()

        exc_content = {
            "traceback": stb,
            "ename": str(etype.__name__),
            "evalue": str(evalue),
        }

        dh = self.displayhook
        # Send exception info over pub socket for other clients than the caller
        # to pick up
        topic = None
        if dh.topic:  # type:ignore[attr-defined]
            topic = dh.topic.replace(b"execute_result", b"error")  # type:ignore[attr-defined]

        dh.session.send(  # type:ignore[attr-defined]
            dh.pub_socket,  # type:ignore[attr-defined]
            "error",
            json_clean(exc_content),
            dh.parent_header,  # type:ignore[attr-defined]
            ident=topic,
        )

        # FIXME - Once we rely on Python 3, the traceback is stored on the
        # exception object, so we shouldn't need to store it here.
        self._last_traceback = stb

    def set_next_input(self, text, replace=False):
        """Send the specified text to the frontend to be presented at the next
        input cell."""
        payload = dict(
            source="set_next_input",
            text=text,
            replace=replace,
        )
        self.payload_manager.write_payload(payload)  # type:ignore[union-attr]

    def set_parent(self, parent):
        """Set the parent header for associating output with its triggering input"""
        self.parent_header = parent
        self.displayhook.set_parent(parent)  # type:ignore[attr-defined]
        self.display_pub.set_parent(parent)  # type:ignore[attr-defined]
        if hasattr(self, "_data_pub"):
            self.data_pub.set_parent(parent)
        try:
            sys.stdout.set_parent(parent)  # type:ignore[attr-defined]
        except AttributeError:
            pass
        try:
            sys.stderr.set_parent(parent)  # type:ignore[attr-defined]
        except AttributeError:
            pass

    def get_parent(self):
        """Get the parent header."""
        return self.parent_header

    def init_magics(self):
        """Initialize magics."""
        super().init_magics()
        self.register_magics(KernelMagics)
        self.magics_manager.register_alias("ed", "edit")

    def init_virtualenv(self):
        """Initialize virtual environment."""
        # Overridden not to do virtualenv detection, because it's probably
        # not appropriate in a kernel. To use a kernel in a virtualenv, install
        # it inside the virtualenv.
        # https://ipython.readthedocs.io/en/latest/install/kernel_install.html

    def system_piped(self, cmd):
        """Call the given cmd in a subprocess, piping stdout/err

        Parameters
        ----------
        cmd : str
            Command to execute (can not end in '&', as background processes are
            not supported.  Should not be a command that expects input
            other than simple text.
        """
        if cmd.rstrip().endswith("&"):
            # this is *far* from a rigorous test
            # We do not support backgrounding processes because we either use
            # pexpect or pipes to read from.  Users can always just call
            # os.system() or use ip.system=ip.system_raw
            # if they really want a background process.
            msg = "Background processes not supported."
            raise OSError(msg)

        # we explicitly do NOT return the subprocess status code, because
        # a non-None value would trigger :func:`sys.displayhook` calls.
        # Instead, we store the exit_code in user_ns.
        # Also, protect system call from UNC paths on Windows here too
        # as is done in InteractiveShell.system_raw
        if sys.platform == "win32":
            cmd = self.var_expand(cmd, depth=1)
            from IPython.utils._process_win32 import AvoidUNCPath

            with AvoidUNCPath() as path:
                if path is not None:
                    cmd = f"pushd {path} &&{cmd}"
                self.user_ns["_exit_code"] = system(cmd)
        else:
            self.user_ns["_exit_code"] = system(self.var_expand(cmd, depth=1))

    # Ensure new system_piped implementation is used
    system = system_piped


InteractiveShellABC.register(ZMQInteractiveShell)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\sfnt.py ===
"""ttLib/sfnt.py -- low-level module to deal with the sfnt file format.

Defines two public classes:

- SFNTReader
- SFNTWriter

(Normally you don't have to use these classes explicitly; they are
used automatically by ttLib.TTFont.)

The reading and writing of sfnt files is separated in two distinct
classes, since whenever the number of tables changes or whenever
a table's length changes you need to rewrite the whole file anyway.
"""

from io import BytesIO
from types import SimpleNamespace
from fontTools.misc.textTools import Tag
from fontTools.misc import sstruct
from fontTools.ttLib import TTLibError, TTLibFileIsCollectionError
import struct
from collections import OrderedDict
import logging


log = logging.getLogger(__name__)


class SFNTReader(object):
    def __new__(cls, *args, **kwargs):
        """Return an instance of the SFNTReader sub-class which is compatible
        with the input file type.
        """
        if args and cls is SFNTReader:
            infile = args[0]
            infile.seek(0)
            sfntVersion = Tag(infile.read(4))
            infile.seek(0)
            if sfntVersion == "wOF2":
                # return new WOFF2Reader object
                from fontTools.ttLib.woff2 import WOFF2Reader

                return object.__new__(WOFF2Reader)
        # return default object
        return object.__new__(cls)

    def __init__(self, file, checkChecksums=0, fontNumber=-1):
        self.file = file
        self.checkChecksums = checkChecksums

        self.flavor = None
        self.flavorData = None
        self.DirectoryEntry = SFNTDirectoryEntry
        self.file.seek(0)
        self.sfntVersion = self.file.read(4)
        self.file.seek(0)
        if self.sfntVersion == b"ttcf":
            header = readTTCHeader(self.file)
            numFonts = header.numFonts
            if not 0 <= fontNumber < numFonts:
                raise TTLibFileIsCollectionError(
                    "specify a font number between 0 and %d (inclusive)"
                    % (numFonts - 1)
                )
            self.numFonts = numFonts
            self.file.seek(header.offsetTable[fontNumber])
            data = self.file.read(sfntDirectorySize)
            if len(data) != sfntDirectorySize:
                raise TTLibError("Not a Font Collection (not enough data)")
            sstruct.unpack(sfntDirectoryFormat, data, self)
        elif self.sfntVersion == b"wOFF":
            self.flavor = "woff"
            self.DirectoryEntry = WOFFDirectoryEntry
            data = self.file.read(woffDirectorySize)
            if len(data) != woffDirectorySize:
                raise TTLibError("Not a WOFF font (not enough data)")
            sstruct.unpack(woffDirectoryFormat, data, self)
        else:
            data = self.file.read(sfntDirectorySize)
            if len(data) != sfntDirectorySize:
                raise TTLibError("Not a TrueType or OpenType font (not enough data)")
            sstruct.unpack(sfntDirectoryFormat, data, self)
        self.sfntVersion = Tag(self.sfntVersion)

        if self.sfntVersion not in ("\x00\x01\x00\x00", "OTTO", "true"):
            raise TTLibError("Not a TrueType or OpenType font (bad sfntVersion)")
        tables = {}
        for i in range(self.numTables):
            entry = self.DirectoryEntry()
            entry.fromFile(self.file)
            tag = Tag(entry.tag)
            tables[tag] = entry
        self.tables = OrderedDict(sorted(tables.items(), key=lambda i: i[1].offset))

        # Load flavor data if any
        if self.flavor == "woff":
            self.flavorData = WOFFFlavorData(self)

    def has_key(self, tag):
        return tag in self.tables

    __contains__ = has_key

    def keys(self):
        return self.tables.keys()

    def __getitem__(self, tag):
        """Fetch the raw table data."""
        entry = self.tables[Tag(tag)]
        data = entry.loadData(self.file)
        if self.checkChecksums:
            if tag == "head":
                # Beh: we have to special-case the 'head' table.
                checksum = calcChecksum(data[:8] + b"\0\0\0\0" + data[12:])
            else:
                checksum = calcChecksum(data)
            if self.checkChecksums > 1:
                # Be obnoxious, and barf when it's wrong
                assert checksum == entry.checkSum, "bad checksum for '%s' table" % tag
            elif checksum != entry.checkSum:
                # Be friendly, and just log a warning.
                log.warning("bad checksum for '%s' table", tag)
        return data

    def __delitem__(self, tag):
        del self.tables[Tag(tag)]

    def close(self):
        self.file.close()

    # We define custom __getstate__ and __setstate__ to make SFNTReader pickle-able
    # and deepcopy-able. When a TTFont is loaded as lazy=True, SFNTReader holds a
    # reference to an external file object which is not pickleable. So in __getstate__
    # we store the file name and current position, and in __setstate__ we reopen the
    # same named file after unpickling.

    def __getstate__(self):
        if isinstance(self.file, BytesIO):
            # BytesIO is already pickleable, return the state unmodified
            return self.__dict__

        # remove unpickleable file attribute, and only store its name and pos
        state = self.__dict__.copy()
        del state["file"]
        state["_filename"] = self.file.name
        state["_filepos"] = self.file.tell()
        return state

    def __setstate__(self, state):
        if "file" not in state:
            self.file = open(state.pop("_filename"), "rb")
            self.file.seek(state.pop("_filepos"))
        self.__dict__.update(state)


# default compression level for WOFF 1.0 tables and metadata
ZLIB_COMPRESSION_LEVEL = 6

# if set to True, use zopfli instead of zlib for compressing WOFF 1.0.
# The Python bindings are available at https://pypi.python.org/pypi/zopfli
USE_ZOPFLI = False

# mapping between zlib's compression levels and zopfli's 'numiterations'.
# Use lower values for files over several MB in size or it will be too slow
ZOPFLI_LEVELS = {
    # 0: 0,  # can't do 0 iterations...
    1: 1,
    2: 3,
    3: 5,
    4: 8,
    5: 10,
    6: 15,
    7: 25,
    8: 50,
    9: 100,
}


def compress(data, level=ZLIB_COMPRESSION_LEVEL):
    """Compress 'data' to Zlib format. If 'USE_ZOPFLI' variable is True,
    zopfli is used instead of the zlib module.
    The compression 'level' must be between 0 and 9. 1 gives best speed,
    9 gives best compression (0 gives no compression at all).
    The default value is a compromise between speed and compression (6).
    """
    if not (0 <= level <= 9):
        raise ValueError("Bad compression level: %s" % level)
    if not USE_ZOPFLI or level == 0:
        from zlib import compress

        return compress(data, level)
    else:
        from zopfli.zlib import compress

        return compress(data, numiterations=ZOPFLI_LEVELS[level])


class SFNTWriter(object):
    def __new__(cls, *args, **kwargs):
        """Return an instance of the SFNTWriter sub-class which is compatible
        with the specified 'flavor'.
        """
        flavor = None
        if kwargs and "flavor" in kwargs:
            flavor = kwargs["flavor"]
        elif args and len(args) > 3:
            flavor = args[3]
        if cls is SFNTWriter:
            if flavor == "woff2":
                # return new WOFF2Writer object
                from fontTools.ttLib.woff2 import WOFF2Writer

                return object.__new__(WOFF2Writer)
        # return default object
        return object.__new__(cls)

    def __init__(
        self,
        file,
        numTables,
        sfntVersion="\000\001\000\000",
        flavor=None,
        flavorData=None,
    ):
        self.file = file
        self.numTables = numTables
        self.sfntVersion = Tag(sfntVersion)
        self.flavor = flavor
        self.flavorData = flavorData

        if self.flavor == "woff":
            self.directoryFormat = woffDirectoryFormat
            self.directorySize = woffDirectorySize
            self.DirectoryEntry = WOFFDirectoryEntry

            self.signature = "wOFF"

            # to calculate WOFF checksum adjustment, we also need the original SFNT offsets
            self.origNextTableOffset = (
                sfntDirectorySize + numTables * sfntDirectoryEntrySize
            )
        else:
            assert not self.flavor, "Unknown flavor '%s'" % self.flavor
            self.directoryFormat = sfntDirectoryFormat
            self.directorySize = sfntDirectorySize
            self.DirectoryEntry = SFNTDirectoryEntry

            from fontTools.ttLib import getSearchRange

            self.searchRange, self.entrySelector, self.rangeShift = getSearchRange(
                numTables, 16
            )

        self.directoryOffset = self.file.tell()
        self.nextTableOffset = (
            self.directoryOffset
            + self.directorySize
            + numTables * self.DirectoryEntry.formatSize
        )
        # clear out directory area
        self.file.seek(self.nextTableOffset)
        # make sure we're actually where we want to be. (old cStringIO bug)
        self.file.write(b"\0" * (self.nextTableOffset - self.file.tell()))
        self.tables = OrderedDict()

    def setEntry(self, tag, entry):
        if tag in self.tables:
            raise TTLibError("cannot rewrite '%s' table" % tag)

        self.tables[tag] = entry

    def __setitem__(self, tag, data):
        """Write raw table data to disk."""
        if tag in self.tables:
            raise TTLibError("cannot rewrite '%s' table" % tag)

        entry = self.DirectoryEntry()
        entry.tag = tag
        entry.offset = self.nextTableOffset
        if tag == "head":
            entry.checkSum = calcChecksum(data[:8] + b"\0\0\0\0" + data[12:])
            self.headTable = data
            entry.uncompressed = True
        else:
            entry.checkSum = calcChecksum(data)
        entry.saveData(self.file, data)

        if self.flavor == "woff":
            entry.origOffset = self.origNextTableOffset
            self.origNextTableOffset += (entry.origLength + 3) & ~3

        self.nextTableOffset = self.nextTableOffset + ((entry.length + 3) & ~3)
        # Add NUL bytes to pad the table data to a 4-byte boundary.
        # Don't depend on f.seek() as we need to add the padding even if no
        # subsequent write follows (seek is lazy), ie. after the final table
        # in the font.
        self.file.write(b"\0" * (self.nextTableOffset - self.file.tell()))
        assert self.nextTableOffset == self.file.tell()

        self.setEntry(tag, entry)

    def __getitem__(self, tag):
        return self.tables[tag]

    def close(self):
        """All tables must have been written to disk. Now write the
        directory.
        """
        tables = sorted(self.tables.items())
        if len(tables) != self.numTables:
            raise TTLibError(
                "wrong number of tables; expected %d, found %d"
                % (self.numTables, len(tables))
            )

        if self.flavor == "woff":
            self.signature = b"wOFF"
            self.reserved = 0

            self.totalSfntSize = 12
            self.totalSfntSize += 16 * len(tables)
            for tag, entry in tables:
                self.totalSfntSize += (entry.origLength + 3) & ~3

            data = self.flavorData if self.flavorData else WOFFFlavorData()
            if data.majorVersion is not None and data.minorVersion is not None:
                self.majorVersion = data.majorVersion
                self.minorVersion = data.minorVersion
            else:
                if hasattr(self, "headTable"):
                    self.majorVersion, self.minorVersion = struct.unpack(
                        ">HH", self.headTable[4:8]
                    )
                else:
                    self.majorVersion = self.minorVersion = 0
            if data.metaData:
                self.metaOrigLength = len(data.metaData)
                self.file.seek(0, 2)
                self.metaOffset = self.file.tell()
                compressedMetaData = compress(data.metaData)
                self.metaLength = len(compressedMetaData)
                self.file.write(compressedMetaData)
            else:
                self.metaOffset = self.metaLength = self.metaOrigLength = 0
            if data.privData:
                self.file.seek(0, 2)
                off = self.file.tell()
                paddedOff = (off + 3) & ~3
                self.file.write(b"\0" * (paddedOff - off))
                self.privOffset = self.file.tell()
                self.privLength = len(data.privData)
                self.file.write(data.privData)
            else:
                self.privOffset = self.privLength = 0

            self.file.seek(0, 2)
            self.length = self.file.tell()

        else:
            assert not self.flavor, "Unknown flavor '%s'" % self.flavor
            pass

        directory = sstruct.pack(self.directoryFormat, self)

        self.file.seek(self.directoryOffset + self.directorySize)
        seenHead = 0
        for tag, entry in tables:
            if tag == "head":
                seenHead = 1
            directory = directory + entry.toString()
        if seenHead:
            self.writeMasterChecksum(directory)
        self.file.seek(self.directoryOffset)
        self.file.write(directory)

    def _calcMasterChecksum(self, directory):
        # calculate checkSumAdjustment
        tags = list(self.tables.keys())
        checksums = []
        for i in range(len(tags)):
            checksums.append(self.tables[tags[i]].checkSum)

        if self.DirectoryEntry != SFNTDirectoryEntry:
            # Create a SFNT directory for checksum calculation purposes
            from fontTools.ttLib import getSearchRange

            self.searchRange, self.entrySelector, self.rangeShift = getSearchRange(
                self.numTables, 16
            )
            directory = sstruct.pack(sfntDirectoryFormat, self)
            tables = sorted(self.tables.items())
            for tag, entry in tables:
                sfntEntry = SFNTDirectoryEntry()
                sfntEntry.tag = entry.tag
                sfntEntry.checkSum = entry.checkSum
                sfntEntry.offset = entry.origOffset
                sfntEntry.length = entry.origLength
                directory = directory + sfntEntry.toString()

        directory_end = sfntDirectorySize + len(self.tables) * sfntDirectoryEntrySize
        assert directory_end == len(directory)

        checksums.append(calcChecksum(directory))
        checksum = sum(checksums) & 0xFFFFFFFF
        # BiboAfba!
        checksumadjustment = (0xB1B0AFBA - checksum) & 0xFFFFFFFF
        return checksumadjustment

    def writeMasterChecksum(self, directory):
        checksumadjustment = self._calcMasterChecksum(directory)
        # write the checksum to the file
        self.file.seek(self.tables["head"].offset + 8)
        self.file.write(struct.pack(">L", checksumadjustment))

    def reordersTables(self):
        return False


# -- sfnt directory helpers and cruft

ttcHeaderFormat = """
		> # big endian
		TTCTag:                  4s # "ttcf"
		Version:                 L  # 0x00010000 or 0x00020000
		numFonts:                L  # number of fonts
		# OffsetTable[numFonts]: L  # array with offsets from beginning of file
		# ulDsigTag:             L  # version 2.0 only
		# ulDsigLength:          L  # version 2.0 only
		# ulDsigOffset:          L  # version 2.0 only
"""

ttcHeaderSize = sstruct.calcsize(ttcHeaderFormat)

sfntDirectoryFormat = """
		> # big endian
		sfntVersion:    4s
		numTables:      H    # number of tables
		searchRange:    H    # (max2 <= numTables)*16
		entrySelector:  H    # log2(max2 <= numTables)
		rangeShift:     H    # numTables*16-searchRange
"""

sfntDirectorySize = sstruct.calcsize(sfntDirectoryFormat)

sfntDirectoryEntryFormat = """
		> # big endian
		tag:            4s
		checkSum:       L
		offset:         L
		length:         L
"""

sfntDirectoryEntrySize = sstruct.calcsize(sfntDirectoryEntryFormat)

woffDirectoryFormat = """
		> # big endian
		signature:      4s   # "wOFF"
		sfntVersion:    4s
		length:         L    # total woff file size
		numTables:      H    # number of tables
		reserved:       H    # set to 0
		totalSfntSize:  L    # uncompressed size
		majorVersion:   H    # major version of WOFF file
		minorVersion:   H    # minor version of WOFF file
		metaOffset:     L    # offset to metadata block
		metaLength:     L    # length of compressed metadata
		metaOrigLength: L    # length of uncompressed metadata
		privOffset:     L    # offset to private data block
		privLength:     L    # length of private data block
"""

woffDirectorySize = sstruct.calcsize(woffDirectoryFormat)

woffDirectoryEntryFormat = """
		> # big endian
		tag:            4s
		offset:         L
		length:         L    # compressed length
		origLength:     L    # original length
		checkSum:       L    # original checksum
"""

woffDirectoryEntrySize = sstruct.calcsize(woffDirectoryEntryFormat)


class DirectoryEntry(object):
    def __init__(self):
        self.uncompressed = False  # if True, always embed entry raw

    def fromFile(self, file):
        sstruct.unpack(self.format, file.read(self.formatSize), self)

    def fromString(self, str):
        sstruct.unpack(self.format, str, self)

    def toString(self):
        return sstruct.pack(self.format, self)

    def __repr__(self):
        if hasattr(self, "tag"):
            return "<%s '%s' at %x>" % (self.__class__.__name__, self.tag, id(self))
        else:
            return "<%s at %x>" % (self.__class__.__name__, id(self))

    def loadData(self, file):
        file.seek(self.offset)
        data = file.read(self.length)
        assert len(data) == self.length
        if hasattr(self.__class__, "decodeData"):
            data = self.decodeData(data)
        return data

    def saveData(self, file, data):
        if hasattr(self.__class__, "encodeData"):
            data = self.encodeData(data)
        self.length = len(data)
        file.seek(self.offset)
        file.write(data)

    def decodeData(self, rawData):
        return rawData

    def encodeData(self, data):
        return data


class SFNTDirectoryEntry(DirectoryEntry):
    format = sfntDirectoryEntryFormat
    formatSize = sfntDirectoryEntrySize


class WOFFDirectoryEntry(DirectoryEntry):
    format = woffDirectoryEntryFormat
    formatSize = woffDirectoryEntrySize

    def __init__(self):
        super(WOFFDirectoryEntry, self).__init__()
        # With fonttools<=3.1.2, the only way to set a different zlib
        # compression level for WOFF directory entries was to set the class
        # attribute 'zlibCompressionLevel'. This is now replaced by a globally
        # defined `ZLIB_COMPRESSION_LEVEL`, which is also applied when
        # compressing the metadata. For backward compatibility, we still
        # use the class attribute if it was already set.
        if not hasattr(WOFFDirectoryEntry, "zlibCompressionLevel"):
            self.zlibCompressionLevel = ZLIB_COMPRESSION_LEVEL

    def decodeData(self, rawData):
        import zlib

        if self.length == self.origLength:
            data = rawData
        else:
            assert self.length < self.origLength
            data = zlib.decompress(rawData)
            assert len(data) == self.origLength
        return data

    def encodeData(self, data):
        self.origLength = len(data)
        if not self.uncompressed:
            compressedData = compress(data, self.zlibCompressionLevel)
        if self.uncompressed or len(compressedData) >= self.origLength:
            # Encode uncompressed
            rawData = data
            self.length = self.origLength
        else:
            rawData = compressedData
            self.length = len(rawData)
        return rawData


class WOFFFlavorData:
    Flavor = "woff"

    def __init__(self, reader=None):
        self.majorVersion = None
        self.minorVersion = None
        self.metaData = None
        self.privData = None
        if reader:
            self.majorVersion = reader.majorVersion
            self.minorVersion = reader.minorVersion
            if reader.metaLength:
                reader.file.seek(reader.metaOffset)
                rawData = reader.file.read(reader.metaLength)
                assert len(rawData) == reader.metaLength
                data = self._decompress(rawData)
                assert len(data) == reader.metaOrigLength
                self.metaData = data
            if reader.privLength:
                reader.file.seek(reader.privOffset)
                data = reader.file.read(reader.privLength)
                assert len(data) == reader.privLength
                self.privData = data

    def _decompress(self, rawData):
        import zlib

        return zlib.decompress(rawData)


def calcChecksum(data):
    """Calculate the checksum for an arbitrary block of data.

    If the data length is not a multiple of four, it assumes
    it is to be padded with null byte.

            >>> print(calcChecksum(b"abcd"))
            1633837924
            >>> print(calcChecksum(b"abcdxyz"))
            3655064932
    """
    remainder = len(data) % 4
    if remainder:
        data += b"\0" * (4 - remainder)
    value = 0
    blockSize = 4096
    assert blockSize % 4 == 0
    for i in range(0, len(data), blockSize):
        block = data[i : i + blockSize]
        longs = struct.unpack(">%dL" % (len(block) // 4), block)
        value = (value + sum(longs)) & 0xFFFFFFFF
    return value


def readTTCHeader(file):
    file.seek(0)
    data = file.read(ttcHeaderSize)
    if len(data) != ttcHeaderSize:
        raise TTLibError("Not a Font Collection (not enough data)")
    self = SimpleNamespace()
    sstruct.unpack(ttcHeaderFormat, data, self)
    if self.TTCTag != "ttcf":
        raise TTLibError("Not a Font Collection")
    assert self.Version == 0x00010000 or self.Version == 0x00020000, (
        "unrecognized TTC version 0x%08x" % self.Version
    )
    self.offsetTable = struct.unpack(
        ">%dL" % self.numFonts, file.read(self.numFonts * 4)
    )
    if self.Version == 0x00020000:
        pass  # ignoring version 2.0 signatures
    return self


def writeTTCHeader(file, numFonts):
    self = SimpleNamespace()
    self.TTCTag = "ttcf"
    self.Version = 0x00010000
    self.numFonts = numFonts
    file.seek(0)
    file.write(sstruct.pack(ttcHeaderFormat, self))
    offset = file.tell()
    file.write(struct.pack(">%dL" % self.numFonts, *([0] * self.numFonts)))
    return offset


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\fine_tuning_endpoints\endpoints.py ===
#########################################################################

#                          /v1/fine_tuning Endpoints

# Equivalent of https://platform.openai.com/docs/api-reference/fine-tuning
##########################################################################

import asyncio
from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from litellm.proxy.openai_files_endpoints.common_utils import (
    _is_base64_encoded_unified_file_id,
)
from litellm.proxy.utils import handle_exception_on_proxy
from litellm.types.utils import LiteLLMFineTuningJob

router = APIRouter()

from litellm.types.llms.openai import LiteLLMFineTuningJobCreate

fine_tuning_config = None


def set_fine_tuning_config(config):
    if config is None:
        return

    global fine_tuning_config
    if not isinstance(config, list):
        raise ValueError("invalid fine_tuning config, expected a list is not a list")

    for element in config:
        if isinstance(element, dict):
            for key, value in element.items():
                if isinstance(value, str) and value.startswith("os.environ/"):
                    element[key] = litellm.get_secret(value)

    fine_tuning_config = config


# Function to search for specific custom_llm_provider and return its configuration
def get_fine_tuning_provider_config(
    custom_llm_provider: str,
):
    global fine_tuning_config
    if fine_tuning_config is None:
        raise ValueError(
            "fine_tuning_config is not set, set it on your config.yaml file."
        )
    for setting in fine_tuning_config:
        if setting.get("custom_llm_provider") == custom_llm_provider:
            return setting
    return None


@router.post(
    "/v1/fine_tuning/jobs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Create Fine-Tuning Job",
)
@router.post(
    "/fine_tuning/jobs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Create Fine-Tuning Job",
)
async def create_fine_tuning_job(
    request: Request,
    fastapi_response: Response,
    fine_tuning_request: LiteLLMFineTuningJobCreate,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Creates a fine-tuning job which begins the process of creating a new model from a given dataset.
    This is the equivalent of POST https://api.openai.com/v1/fine_tuning/jobs

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/fine-tuning/create

    Example Curl:
    ```
    curl http://localhost:4000/v1/fine_tuning/jobs \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer sk-1234" \
      -d '{
        "model": "gpt-3.5-turbo",
        "training_file": "file-abc123",
        "hyperparameters": {
          "n_epochs": 4
        }
      }'
    ```
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        premium_user,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data = fine_tuning_request.model_dump(exclude_none=True)
    try:
        if premium_user is not True:
            raise ValueError(
                f"Only premium users can use this endpoint + {CommonProxyErrors.not_premium_user.value}"
            )
        # Convert Pydantic model to dict

        verbose_proxy_logger.debug(
            "Request received by LiteLLM:\n{}".format(json.dumps(data, indent=4)),
        )

        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type="acreate_fine_tuning_job",
        )

        ## CHECK IF MANAGED FILE ID
        unified_file_id: Union[str, Literal[False]] = False
        training_file = fine_tuning_request.training_file
        response: Optional[LiteLLMFineTuningJob] = None
        if training_file:
            unified_file_id = _is_base64_encoded_unified_file_id(training_file)
        ## IF SO, Route based on that
        if unified_file_id:
            """ """
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )

            response = cast(
                LiteLLMFineTuningJob, await llm_router.acreate_fine_tuning_job(**data)
            )
            response.training_file = unified_file_id
            response._hidden_params["unified_file_id"] = unified_file_id
        ## ELSE, Route based on custom_llm_provider
        elif fine_tuning_request.custom_llm_provider:
            # get configs for custom_llm_provider
            llm_provider_config = get_fine_tuning_provider_config(
                custom_llm_provider=fine_tuning_request.custom_llm_provider,
            )
            # add llm_provider_config to data
            if llm_provider_config is not None:
                data.update(llm_provider_config)

            response = await litellm.acreate_fine_tuning_job(**data)

        if response is None:
            raise ValueError(
                "Invalid request, No litellm managed file id or custom_llm_provider provided."
            )

        ### CALL HOOKS ### - modify outgoing data
        _response = await proxy_logging_obj.post_call_success_hook(
            data=data,
            user_api_key_dict=user_api_key_dict,
            response=response,
        )
        if _response is not None and isinstance(_response, LiteLLMFineTuningJob):
            response = _response

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.create_fine_tuning_job(): Exception occurred - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/v1/fine_tuning/jobs/{fine_tuning_job_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Retrieve Fine-Tuning Job",
)
@router.get(
    "/fine_tuning/jobs/{fine_tuning_job_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Retrieve Fine-Tuning Job",
)
async def retrieve_fine_tuning_job(
    request: Request,
    fastapi_response: Response,
    fine_tuning_job_id: str,
    custom_llm_provider: Optional[Literal["openai", "azure"]] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Retrieves a fine-tuning job.
    This is the equivalent of GET https://api.openai.com/v1/fine_tuning/jobs/{fine_tuning_job_id}

    Supported Query Params:
    - `custom_llm_provider`: Name of the LiteLLM provider
    - `fine_tuning_job_id`: The ID of the fine-tuning job to retrieve.
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        premium_user,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: dict = {"fine_tuning_job_id": fine_tuning_job_id}
    try:
        if premium_user is not True:
            raise ValueError(
                f"Only premium users can use this endpoint + {CommonProxyErrors.not_premium_user.value}"
            )
        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type=CallTypes.aretrieve_fine_tuning_job.value,
        )

        try:
            request_body = await request.json()
        except Exception:
            request_body = {}

        custom_llm_provider = request_body.get("custom_llm_provider", None)

        ## CHECK IF MANAGED FILE ID
        unified_finetuning_job_id: Union[str, Literal[False]] = False
        response: Optional[LiteLLMFineTuningJob] = None
        if fine_tuning_job_id:
            unified_finetuning_job_id = _is_base64_encoded_unified_file_id(
                fine_tuning_job_id
            )
        if unified_finetuning_job_id:
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )
            response = cast(
                LiteLLMFineTuningJob,
                await llm_router.aretrieve_fine_tuning_job(
                    **data,
                ),
            )
            response._hidden_params[
                "unified_finetuning_job_id"
            ] = unified_finetuning_job_id
        elif custom_llm_provider:
            # get configs for custom_llm_provider
            llm_provider_config = get_fine_tuning_provider_config(
                custom_llm_provider=custom_llm_provider
            )

            if llm_provider_config is not None:
                data.update(llm_provider_config)

            response = await litellm.aretrieve_fine_tuning_job(
                **data,
            )

        if response is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid request, No litellm managed file id or custom_llm_provider provided.",
            )

        ### CALL HOOKS ### - modify outgoing data
        _response = await proxy_logging_obj.post_call_success_hook(
            data=data,
            user_api_key_dict=user_api_key_dict,
            response=response,
        )
        if _response is not None and isinstance(_response, LiteLLMFineTuningJob):
            response = _response

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )

        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.retrieve_fine_tuning_job(): Exception occurred - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/v1/fine_tuning/jobs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) List Fine-Tuning Jobs",
)
@router.get(
    "/fine_tuning/jobs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) List Fine-Tuning Jobs",
)
async def list_fine_tuning_jobs(
    request: Request,
    fastapi_response: Response,
    custom_llm_provider: Optional[Literal["openai", "azure"]] = None,
    target_model_names: Optional[str] = Query(
        default=None,
        description="Comma separated list of model names to filter by. Example: 'gpt-4o,gpt-4o-mini'",
    ),
    after: Optional[str] = None,
    limit: Optional[int] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Lists fine-tuning jobs for the organization.
    This is the equivalent of GET https://api.openai.com/v1/fine_tuning/jobs

    Supported Query Params:
    - `custom_llm_provider`: Name of the LiteLLM provider
    - `after`: Identifier for the last job from the previous pagination request.
    - `limit`: Number of fine-tuning jobs to retrieve (default is 20).
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        premium_user,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: dict = {}
    try:
        if premium_user is not True:
            raise ValueError(
                f"Only premium users can use this endpoint + {CommonProxyErrors.not_premium_user.value}"
            )
        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type=CallTypes.alist_fine_tuning_jobs.value,
        )

        response: Optional[Any] = None
        if target_model_names and isinstance(target_model_names, str):
            target_model_names_list = target_model_names.split(",")
            if len(target_model_names_list) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="target_model_names on list fine-tuning jobs must be a list of one model name. Example: ['gpt-4o']",
                )
            ## Use router to list fine-tuning jobs for that model
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail="LLM Router not initialized. Ensure models added to proxy.",
                )
            data["model"] = target_model_names_list[0]
            response = await llm_router.alist_fine_tuning_jobs(
                **data,
                after=after,
                limit=limit,
            )
            return response
        elif custom_llm_provider:
            # get configs for custom_llm_provider
            llm_provider_config = get_fine_tuning_provider_config(
                custom_llm_provider=custom_llm_provider
            )

            if llm_provider_config is not None:
                data.update(llm_provider_config)

            response = await litellm.alist_fine_tuning_jobs(
                **data,
                after=after,
                limit=limit,
            )
        if response is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid request, No litellm managed file id or custom_llm_provider provided.",
            )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )

        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.list_fine_tuning_jobs(): Exception occurred - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.post(
    "/v1/fine_tuning/jobs/{fine_tuning_job_id:path}/cancel",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Cancel Fine-Tuning Jobs",
)
@router.post(
    "/fine_tuning/jobs/{fine_tuning_job_id:path}/cancel",
    dependencies=[Depends(user_api_key_auth)],
    tags=["fine-tuning"],
    summary="✨ (Enterprise) Cancel Fine-Tuning Jobs",
)
async def cancel_fine_tuning_job(
    request: Request,
    fastapi_response: Response,
    fine_tuning_job_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Cancel a fine-tuning job.

    This is the equivalent of POST https://api.openai.com/v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel

    Supported Query Params:
    - `custom_llm_provider`: Name of the LiteLLM provider
    - `fine_tuning_job_id`: The ID of the fine-tuning job to cancel.
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        premium_user,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: dict = {"fine_tuning_job_id": fine_tuning_job_id}
    try:
        if premium_user is not True:
            raise ValueError(
                f"Only premium users can use this endpoint + {CommonProxyErrors.not_premium_user.value}"
            )
        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type=CallTypes.acancel_fine_tuning_job.value,
        )

        try:
            request_body = await request.json()
        except Exception:
            request_body = {}

        custom_llm_provider = request_body.get("custom_llm_provider", None)

        ## CHECK IF MANAGED FILE ID
        unified_finetuning_job_id: Union[str, Literal[False]] = False
        response: Optional[LiteLLMFineTuningJob] = None
        if fine_tuning_job_id:
            unified_finetuning_job_id = _is_base64_encoded_unified_file_id(
                fine_tuning_job_id
            )
        if unified_finetuning_job_id:
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )
            response = cast(
                LiteLLMFineTuningJob,
                await llm_router.acancel_fine_tuning_job(
                    **data,
                ),
            )
            response._hidden_params[
                "unified_finetuning_job_id"
            ] = unified_finetuning_job_id
        else:
            # get configs for custom_llm_provider
            llm_provider_config = get_fine_tuning_provider_config(
                custom_llm_provider=custom_llm_provider
            )

            if llm_provider_config is not None:
                data.update(llm_provider_config)

            response = await litellm.acancel_fine_tuning_job(
                **data,
            )

        if response is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid request, No litellm managed file id or custom_llm_provider provided.",
            )

        ### CALL HOOKS ### - modify outgoing data
        _response = await proxy_logging_obj.post_call_success_hook(
            data=data,
            user_api_key_dict=user_api_key_dict,
            response=response,
        )
        if _response is not None and isinstance(_response, LiteLLMFineTuningJob):
            response = _response

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )

        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.cancel_fine_tuning_job(): Exception occurred - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)

# === NexusCore/openenv\Lib\site-packages\openai\resources\evals\evals.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Iterable, Optional
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from ...types import eval_list_params, eval_create_params, eval_update_params
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from .runs.runs import (
    Runs,
    AsyncRuns,
    RunsWithRawResponse,
    AsyncRunsWithRawResponse,
    RunsWithStreamingResponse,
    AsyncRunsWithStreamingResponse,
)
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...pagination import SyncCursorPage, AsyncCursorPage
from ..._base_client import AsyncPaginator, make_request_options
from ...types.eval_list_response import EvalListResponse
from ...types.eval_create_response import EvalCreateResponse
from ...types.eval_delete_response import EvalDeleteResponse
from ...types.eval_update_response import EvalUpdateResponse
from ...types.eval_retrieve_response import EvalRetrieveResponse
from ...types.shared_params.metadata import Metadata

__all__ = ["Evals", "AsyncEvals"]


class Evals(SyncAPIResource):
    @cached_property
    def runs(self) -> Runs:
        return Runs(self._client)

    @cached_property
    def with_raw_response(self) -> EvalsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return EvalsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> EvalsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return EvalsWithStreamingResponse(self)

    def create(
        self,
        *,
        data_source_config: eval_create_params.DataSourceConfig,
        testing_criteria: Iterable[eval_create_params.TestingCriterion],
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalCreateResponse:
        """
        Create the structure of an evaluation that can be used to test a model's
        performance. An evaluation is a set of testing criteria and the config for a
        data source, which dictates the schema of the data used in the evaluation. After
        creating an evaluation, you can run it on different models and model parameters.
        We support several types of graders and datasources. For more information, see
        the [Evals guide](https://platform.openai.com/docs/guides/evals).

        Args:
          data_source_config: The configuration for the data source used for the evaluation runs. Dictates the
              schema of the data used in the evaluation.

          testing_criteria: A list of graders for all eval runs in this group. Graders can reference
              variables in the data source using double curly braces notation, like
              `{{item.variable_name}}`. To reference the model's output, use the `sample`
              namespace (ie, `{{sample.output_text}}`).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the evaluation.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/evals",
            body=maybe_transform(
                {
                    "data_source_config": data_source_config,
                    "testing_criteria": testing_criteria,
                    "metadata": metadata,
                    "name": name,
                },
                eval_create_params.EvalCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalCreateResponse,
        )

    def retrieve(
        self,
        eval_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalRetrieveResponse:
        """
        Get an evaluation by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._get(
            f"/evals/{eval_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalRetrieveResponse,
        )

    def update(
        self,
        eval_id: str,
        *,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalUpdateResponse:
        """
        Update certain properties of an evaluation.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: Rename the evaluation.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._post(
            f"/evals/{eval_id}",
            body=maybe_transform(
                {
                    "metadata": metadata,
                    "name": name,
                },
                eval_update_params.EvalUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalUpdateResponse,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        order_by: Literal["created_at", "updated_at"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[EvalListResponse]:
        """
        List evaluations for a project.

        Args:
          after: Identifier for the last eval from the previous pagination request.

          limit: Number of evals to retrieve.

          order: Sort order for evals by timestamp. Use `asc` for ascending order or `desc` for
              descending order.

          order_by: Evals can be ordered by creation time or last updated time. Use `created_at` for
              creation time or `updated_at` for last updated time.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/evals",
            page=SyncCursorPage[EvalListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "order_by": order_by,
                    },
                    eval_list_params.EvalListParams,
                ),
            ),
            model=EvalListResponse,
        )

    def delete(
        self,
        eval_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalDeleteResponse:
        """
        Delete an evaluation.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._delete(
            f"/evals/{eval_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalDeleteResponse,
        )


class AsyncEvals(AsyncAPIResource):
    @cached_property
    def runs(self) -> AsyncRuns:
        return AsyncRuns(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncEvalsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncEvalsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncEvalsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncEvalsWithStreamingResponse(self)

    async def create(
        self,
        *,
        data_source_config: eval_create_params.DataSourceConfig,
        testing_criteria: Iterable[eval_create_params.TestingCriterion],
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalCreateResponse:
        """
        Create the structure of an evaluation that can be used to test a model's
        performance. An evaluation is a set of testing criteria and the config for a
        data source, which dictates the schema of the data used in the evaluation. After
        creating an evaluation, you can run it on different models and model parameters.
        We support several types of graders and datasources. For more information, see
        the [Evals guide](https://platform.openai.com/docs/guides/evals).

        Args:
          data_source_config: The configuration for the data source used for the evaluation runs. Dictates the
              schema of the data used in the evaluation.

          testing_criteria: A list of graders for all eval runs in this group. Graders can reference
              variables in the data source using double curly braces notation, like
              `{{item.variable_name}}`. To reference the model's output, use the `sample`
              namespace (ie, `{{sample.output_text}}`).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the evaluation.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/evals",
            body=await async_maybe_transform(
                {
                    "data_source_config": data_source_config,
                    "testing_criteria": testing_criteria,
                    "metadata": metadata,
                    "name": name,
                },
                eval_create_params.EvalCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalCreateResponse,
        )

    async def retrieve(
        self,
        eval_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalRetrieveResponse:
        """
        Get an evaluation by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return await self._get(
            f"/evals/{eval_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalRetrieveResponse,
        )

    async def update(
        self,
        eval_id: str,
        *,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalUpdateResponse:
        """
        Update certain properties of an evaluation.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: Rename the evaluation.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return await self._post(
            f"/evals/{eval_id}",
            body=await async_maybe_transform(
                {
                    "metadata": metadata,
                    "name": name,
                },
                eval_update_params.EvalUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalUpdateResponse,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        order_by: Literal["created_at", "updated_at"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[EvalListResponse, AsyncCursorPage[EvalListResponse]]:
        """
        List evaluations for a project.

        Args:
          after: Identifier for the last eval from the previous pagination request.

          limit: Number of evals to retrieve.

          order: Sort order for evals by timestamp. Use `asc` for ascending order or `desc` for
              descending order.

          order_by: Evals can be ordered by creation time or last updated time. Use `created_at` for
              creation time or `updated_at` for last updated time.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/evals",
            page=AsyncCursorPage[EvalListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "order_by": order_by,
                    },
                    eval_list_params.EvalListParams,
                ),
            ),
            model=EvalListResponse,
        )

    async def delete(
        self,
        eval_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> EvalDeleteResponse:
        """
        Delete an evaluation.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return await self._delete(
            f"/evals/{eval_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=EvalDeleteResponse,
        )


class EvalsWithRawResponse:
    def __init__(self, evals: Evals) -> None:
        self._evals = evals

        self.create = _legacy_response.to_raw_response_wrapper(
            evals.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            evals.retrieve,
        )
        self.update = _legacy_response.to_raw_response_wrapper(
            evals.update,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            evals.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            evals.delete,
        )

    @cached_property
    def runs(self) -> RunsWithRawResponse:
        return RunsWithRawResponse(self._evals.runs)


class AsyncEvalsWithRawResponse:
    def __init__(self, evals: AsyncEvals) -> None:
        self._evals = evals

        self.create = _legacy_response.async_to_raw_response_wrapper(
            evals.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            evals.retrieve,
        )
        self.update = _legacy_response.async_to_raw_response_wrapper(
            evals.update,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            evals.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            evals.delete,
        )

    @cached_property
    def runs(self) -> AsyncRunsWithRawResponse:
        return AsyncRunsWithRawResponse(self._evals.runs)


class EvalsWithStreamingResponse:
    def __init__(self, evals: Evals) -> None:
        self._evals = evals

        self.create = to_streamed_response_wrapper(
            evals.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            evals.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            evals.update,
        )
        self.list = to_streamed_response_wrapper(
            evals.list,
        )
        self.delete = to_streamed_response_wrapper(
            evals.delete,
        )

    @cached_property
    def runs(self) -> RunsWithStreamingResponse:
        return RunsWithStreamingResponse(self._evals.runs)


class AsyncEvalsWithStreamingResponse:
    def __init__(self, evals: AsyncEvals) -> None:
        self._evals = evals

        self.create = async_to_streamed_response_wrapper(
            evals.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            evals.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            evals.update,
        )
        self.list = async_to_streamed_response_wrapper(
            evals.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            evals.delete,
        )

    @cached_property
    def runs(self) -> AsyncRunsWithStreamingResponse:
        return AsyncRunsWithStreamingResponse(self._evals.runs)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_win32_console.py ===
"""Light wrapper around the Win32 Console API - this module should only be imported on Windows

The API that this module wraps is documented at https://docs.microsoft.com/en-us/windows/console/console-functions
"""

import ctypes
import sys
from typing import Any

windll: Any = None
if sys.platform == "win32":
    windll = ctypes.LibraryLoader(ctypes.WinDLL)
else:
    raise ImportError(f"{__name__} can only be imported on Windows")

import time
from ctypes import Structure, byref, wintypes
from typing import IO, NamedTuple, Type, cast

from pip._vendor.rich.color import ColorSystem
from pip._vendor.rich.style import Style

STDOUT = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

COORD = wintypes._COORD


class LegacyWindowsError(Exception):
    pass


class WindowsCoordinates(NamedTuple):
    """Coordinates in the Windows Console API are (y, x), not (x, y).
    This class is intended to prevent that confusion.
    Rows and columns are indexed from 0.
    This class can be used in place of wintypes._COORD in arguments and argtypes.
    """

    row: int
    col: int

    @classmethod
    def from_param(cls, value: "WindowsCoordinates") -> COORD:
        """Converts a WindowsCoordinates into a wintypes _COORD structure.
        This classmethod is internally called by ctypes to perform the conversion.

        Args:
            value (WindowsCoordinates): The input coordinates to convert.

        Returns:
            wintypes._COORD: The converted coordinates struct.
        """
        return COORD(value.col, value.row)


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", wintypes.WORD),
        ("srWindow", wintypes.SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class CONSOLE_CURSOR_INFO(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("bVisible", wintypes.BOOL)]


_GetStdHandle = windll.kernel32.GetStdHandle
_GetStdHandle.argtypes = [
    wintypes.DWORD,
]
_GetStdHandle.restype = wintypes.HANDLE


def GetStdHandle(handle: int = STDOUT) -> wintypes.HANDLE:
    """Retrieves a handle to the specified standard device (standard input, standard output, or standard error).

    Args:
        handle (int): Integer identifier for the handle. Defaults to -11 (stdout).

    Returns:
        wintypes.HANDLE: The handle
    """
    return cast(wintypes.HANDLE, _GetStdHandle(handle))


_GetConsoleMode = windll.kernel32.GetConsoleMode
_GetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
_GetConsoleMode.restype = wintypes.BOOL


def GetConsoleMode(std_handle: wintypes.HANDLE) -> int:
    """Retrieves the current input mode of a console's input buffer
    or the current output mode of a console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Raises:
        LegacyWindowsError: If any error occurs while calling the Windows console API.

    Returns:
        int: Value representing the current console mode as documented at
            https://docs.microsoft.com/en-us/windows/console/getconsolemode#parameters
    """

    console_mode = wintypes.DWORD()
    success = bool(_GetConsoleMode(std_handle, console_mode))
    if not success:
        raise LegacyWindowsError("Unable to get legacy Windows Console Mode")
    return console_mode.value


_FillConsoleOutputCharacterW = windll.kernel32.FillConsoleOutputCharacterW
_FillConsoleOutputCharacterW.argtypes = [
    wintypes.HANDLE,
    ctypes.c_char,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputCharacterW.restype = wintypes.BOOL


def FillConsoleOutputCharacter(
    std_handle: wintypes.HANDLE,
    char: str,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Writes a character to the console screen buffer a specified number of times, beginning at the specified coordinates.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        char (str): The character to write. Must be a string of length 1.
        length (int): The number of times to write the character.
        start (WindowsCoordinates): The coordinates to start writing at.

    Returns:
        int: The number of characters written.
    """
    character = ctypes.c_char(char.encode())
    num_characters = wintypes.DWORD(length)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputCharacterW(
        std_handle,
        character,
        num_characters,
        start,
        byref(num_written),
    )
    return num_written.value


_FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
_FillConsoleOutputAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputAttribute.restype = wintypes.BOOL


def FillConsoleOutputAttribute(
    std_handle: wintypes.HANDLE,
    attributes: int,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Sets the character attributes for a specified number of character cells,
    beginning at the specified coordinates in a screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours of the cells.
        length (int): The number of cells to set the output attribute of.
        start (WindowsCoordinates): The coordinates of the first cell whose attributes are to be set.

    Returns:
        int: The number of cells whose attributes were actually set.
    """
    num_cells = wintypes.DWORD(length)
    style_attrs = wintypes.WORD(attributes)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputAttribute(
        std_handle, style_attrs, num_cells, start, byref(num_written)
    )
    return num_written.value


_SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
_SetConsoleTextAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
]
_SetConsoleTextAttribute.restype = wintypes.BOOL


def SetConsoleTextAttribute(
    std_handle: wintypes.HANDLE, attributes: wintypes.WORD
) -> bool:
    """Set the colour attributes for all text written after this function is called.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours.


    Returns:
        bool: True if the attribute was set successfully, otherwise False.
    """
    return bool(_SetConsoleTextAttribute(std_handle, attributes))


_GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
_GetConsoleScreenBufferInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
]
_GetConsoleScreenBufferInfo.restype = wintypes.BOOL


def GetConsoleScreenBufferInfo(
    std_handle: wintypes.HANDLE,
) -> CONSOLE_SCREEN_BUFFER_INFO:
    """Retrieves information about the specified console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Returns:
        CONSOLE_SCREEN_BUFFER_INFO: A CONSOLE_SCREEN_BUFFER_INFO ctype struct contain information about
            screen size, cursor position, colour attributes, and more."""
    console_screen_buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    _GetConsoleScreenBufferInfo(std_handle, byref(console_screen_buffer_info))
    return console_screen_buffer_info


_SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
_SetConsoleCursorPosition.argtypes = [
    wintypes.HANDLE,
    cast(Type[COORD], WindowsCoordinates),
]
_SetConsoleCursorPosition.restype = wintypes.BOOL


def SetConsoleCursorPosition(
    std_handle: wintypes.HANDLE, coords: WindowsCoordinates
) -> bool:
    """Set the position of the cursor in the console screen

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        coords (WindowsCoordinates): The coordinates to move the cursor to.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorPosition(std_handle, coords))


_GetConsoleCursorInfo = windll.kernel32.GetConsoleCursorInfo
_GetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_GetConsoleCursorInfo.restype = wintypes.BOOL


def GetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Get the cursor info - used to get cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct that receives information
            about the console's cursor.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_GetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleCursorInfo = windll.kernel32.SetConsoleCursorInfo
_SetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_SetConsoleCursorInfo.restype = wintypes.BOOL


def SetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Set the cursor info - used for adjusting cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct containing the new cursor info.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleTitle = windll.kernel32.SetConsoleTitleW
_SetConsoleTitle.argtypes = [wintypes.LPCWSTR]
_SetConsoleTitle.restype = wintypes.BOOL


def SetConsoleTitle(title: str) -> bool:
    """Sets the title of the current console window

    Args:
        title (str): The new title of the console window.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleTitle(title))


class LegacyWindowsTerm:
    """This class allows interaction with the legacy Windows Console API. It should only be used in the context
    of environments where virtual terminal processing is not available. However, if it is used in a Windows environment,
    the entire API should work.

    Args:
        file (IO[str]): The file which the Windows Console API HANDLE is retrieved from, defaults to sys.stdout.
    """

    BRIGHT_BIT = 8

    # Indices are ANSI color numbers, values are the corresponding Windows Console API color numbers
    ANSI_TO_WINDOWS = [
        0,  # black                      The Windows colours are defined in wincon.h as follows:
        4,  # red                         define FOREGROUND_BLUE            0x0001 -- 0000 0001
        2,  # green                       define FOREGROUND_GREEN           0x0002 -- 0000 0010
        6,  # yellow                      define FOREGROUND_RED             0x0004 -- 0000 0100
        1,  # blue                        define FOREGROUND_INTENSITY       0x0008 -- 0000 1000
        5,  # magenta                     define BACKGROUND_BLUE            0x0010 -- 0001 0000
        3,  # cyan                        define BACKGROUND_GREEN           0x0020 -- 0010 0000
        7,  # white                       define BACKGROUND_RED             0x0040 -- 0100 0000
        8,  # bright black (grey)         define BACKGROUND_INTENSITY       0x0080 -- 1000 0000
        12,  # bright red
        10,  # bright green
        14,  # bright yellow
        9,  # bright blue
        13,  # bright magenta
        11,  # bright cyan
        15,  # bright white
    ]

    def __init__(self, file: "IO[str]") -> None:
        handle = GetStdHandle(STDOUT)
        self._handle = handle
        default_text = GetConsoleScreenBufferInfo(handle).wAttributes
        self._default_text = default_text

        self._default_fore = default_text & 7
        self._default_back = (default_text >> 4) & 7
        self._default_attrs = self._default_fore | (self._default_back << 4)

        self._file = file
        self.write = file.write
        self.flush = file.flush

    @property
    def cursor_position(self) -> WindowsCoordinates:
        """Returns the current position of the cursor (0-based)

        Returns:
            WindowsCoordinates: The current cursor position.
        """
        coord: COORD = GetConsoleScreenBufferInfo(self._handle).dwCursorPosition
        return WindowsCoordinates(row=coord.Y, col=coord.X)

    @property
    def screen_size(self) -> WindowsCoordinates:
        """Returns the current size of the console screen buffer, in character columns and rows

        Returns:
            WindowsCoordinates: The width and height of the screen as WindowsCoordinates.
        """
        screen_size: COORD = GetConsoleScreenBufferInfo(self._handle).dwSize
        return WindowsCoordinates(row=screen_size.Y, col=screen_size.X)

    def write_text(self, text: str) -> None:
        """Write text directly to the terminal without any modification of styles

        Args:
            text (str): The text to write to the console
        """
        self.write(text)
        self.flush()

    def write_styled(self, text: str, style: Style) -> None:
        """Write styled text to the terminal.

        Args:
            text (str): The text to write
            style (Style): The style of the text
        """
        color = style.color
        bgcolor = style.bgcolor
        if style.reverse:
            color, bgcolor = bgcolor, color

        if color:
            fore = color.downgrade(ColorSystem.WINDOWS).number
            fore = fore if fore is not None else 7  # Default to ANSI 7: White
            if style.bold:
                fore = fore | self.BRIGHT_BIT
            if style.dim:
                fore = fore & ~self.BRIGHT_BIT
            fore = self.ANSI_TO_WINDOWS[fore]
        else:
            fore = self._default_fore

        if bgcolor:
            back = bgcolor.downgrade(ColorSystem.WINDOWS).number
            back = back if back is not None else 0  # Default to ANSI 0: Black
            back = self.ANSI_TO_WINDOWS[back]
        else:
            back = self._default_back

        assert fore is not None
        assert back is not None

        SetConsoleTextAttribute(
            self._handle, attributes=ctypes.c_ushort(fore | (back << 4))
        )
        self.write_text(text)
        SetConsoleTextAttribute(self._handle, attributes=self._default_text)

    def move_cursor_to(self, new_position: WindowsCoordinates) -> None:
        """Set the position of the cursor

        Args:
            new_position (WindowsCoordinates): The WindowsCoordinates representing the new position of the cursor.
        """
        if new_position.col < 0 or new_position.row < 0:
            return
        SetConsoleCursorPosition(self._handle, coords=new_position)

    def erase_line(self) -> None:
        """Erase all content on the line the cursor is currently located at"""
        screen_size = self.screen_size
        cursor_position = self.cursor_position
        cells_to_erase = screen_size.col
        start_coordinates = WindowsCoordinates(row=cursor_position.row, col=0)
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=start_coordinates
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=start_coordinates,
        )

    def erase_end_of_line(self) -> None:
        """Erase all content from the cursor position to the end of that line"""
        cursor_position = self.cursor_position
        cells_to_erase = self.screen_size.col - cursor_position.col
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=cursor_position
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=cursor_position,
        )

    def erase_start_of_line(self) -> None:
        """Erase all content from the cursor position to the start of that line"""
        row, col = self.cursor_position
        start = WindowsCoordinates(row, 0)
        FillConsoleOutputCharacter(self._handle, " ", length=col, start=start)
        FillConsoleOutputAttribute(
            self._handle, self._default_attrs, length=col, start=start
        )

    def move_cursor_up(self) -> None:
        """Move the cursor up a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row - 1, col=cursor_position.col
            ),
        )

    def move_cursor_down(self) -> None:
        """Move the cursor down a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row + 1,
                col=cursor_position.col,
            ),
        )

    def move_cursor_forward(self) -> None:
        """Move the cursor forward a single cell. Wrap to the next line if required."""
        row, col = self.cursor_position
        if col == self.screen_size.col - 1:
            row += 1
            col = 0
        else:
            col += 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def move_cursor_to_column(self, column: int) -> None:
        """Move cursor to the column specified by the zero-based column index, staying on the same row

        Args:
            column (int): The zero-based column index to move the cursor to.
        """
        row, _ = self.cursor_position
        SetConsoleCursorPosition(self._handle, coords=WindowsCoordinates(row, column))

    def move_cursor_backward(self) -> None:
        """Move the cursor backward a single cell. Wrap to the previous line if required."""
        row, col = self.cursor_position
        if col == 0:
            row -= 1
            col = self.screen_size.col - 1
        else:
            col -= 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def hide_cursor(self) -> None:
        """Hide the cursor"""
        current_cursor_size = self._get_cursor_size()
        invisible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=0)
        SetConsoleCursorInfo(self._handle, cursor_info=invisible_cursor)

    def show_cursor(self) -> None:
        """Show the cursor"""
        current_cursor_size = self._get_cursor_size()
        visible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=1)
        SetConsoleCursorInfo(self._handle, cursor_info=visible_cursor)

    def set_title(self, title: str) -> None:
        """Set the title of the terminal window

        Args:
            title (str): The new title of the console window
        """
        assert len(title) < 255, "Console title must be less than 255 characters"
        SetConsoleTitle(title)

    def _get_cursor_size(self) -> int:
        """Get the percentage of the character cell that is filled by the cursor"""
        cursor_info = CONSOLE_CURSOR_INFO()
        GetConsoleCursorInfo(self._handle, cursor_info=cursor_info)
        return int(cursor_info.dwSize)


if __name__ == "__main__":
    handle = GetStdHandle()

    from pip._vendor.rich.console import Console

    console = Console()

    term = LegacyWindowsTerm(sys.stdout)
    term.set_title("Win32 Console Examples")

    style = Style(color="black", bgcolor="red")

    heading = Style.parse("black on green")

    # Check colour output
    console.rule("Checking colour output")
    console.print("[on red]on red!")
    console.print("[blue]blue!")
    console.print("[yellow]yellow!")
    console.print("[bold yellow]bold yellow!")
    console.print("[bright_yellow]bright_yellow!")
    console.print("[dim bright_yellow]dim bright_yellow!")
    console.print("[italic cyan]italic cyan!")
    console.print("[bold white on blue]bold white on blue!")
    console.print("[reverse bold white on blue]reverse bold white on blue!")
    console.print("[bold black on cyan]bold black on cyan!")
    console.print("[black on green]black on green!")
    console.print("[blue on green]blue on green!")
    console.print("[white on black]white on black!")
    console.print("[black on white]black on white!")
    console.print("[#1BB152 on #DA812D]#1BB152 on #DA812D!")

    # Check cursor movement
    console.rule("Checking cursor movement")
    console.print()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("went back and wrapped to prev line")
    time.sleep(1)
    term.move_cursor_up()
    term.write_text("we go up")
    time.sleep(1)
    term.move_cursor_down()
    term.write_text("and down")
    time.sleep(1)
    term.move_cursor_up()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went up and back 2")
    time.sleep(1)
    term.move_cursor_down()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went down and back 2")
    time.sleep(1)

    # Check erasing of lines
    term.hide_cursor()
    console.print()
    console.rule("Checking line erasing")
    console.print("\n...Deleting to the start of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)
    term.move_cursor_to_column(16)
    term.write_styled("<", Style.parse("black on red"))
    term.move_cursor_backward()
    time.sleep(1)
    term.erase_start_of_line()
    time.sleep(1)

    console.print("\n\n...And to the end of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)

    term.move_cursor_to_column(16)
    term.write_styled(">", Style.parse("black on red"))
    time.sleep(1)
    term.erase_end_of_line()
    time.sleep(1)

    console.print("\n\n...Now the whole line will be erased...")
    term.write_styled("I'm going to disappear!", style=Style.parse("black on cyan"))
    time.sleep(1)
    term.erase_line()

    term.show_cursor()
    print("\n")

# === NexusCore/openenv\Lib\site-packages\rich\_win32_console.py ===
"""Light wrapper around the Win32 Console API - this module should only be imported on Windows

The API that this module wraps is documented at https://docs.microsoft.com/en-us/windows/console/console-functions
"""

import ctypes
import sys
from typing import Any

windll: Any = None
if sys.platform == "win32":
    windll = ctypes.LibraryLoader(ctypes.WinDLL)
else:
    raise ImportError(f"{__name__} can only be imported on Windows")

import time
from ctypes import Structure, byref, wintypes
from typing import IO, NamedTuple, Type, cast

from rich.color import ColorSystem
from rich.style import Style

STDOUT = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

COORD = wintypes._COORD


class LegacyWindowsError(Exception):
    pass


class WindowsCoordinates(NamedTuple):
    """Coordinates in the Windows Console API are (y, x), not (x, y).
    This class is intended to prevent that confusion.
    Rows and columns are indexed from 0.
    This class can be used in place of wintypes._COORD in arguments and argtypes.
    """

    row: int
    col: int

    @classmethod
    def from_param(cls, value: "WindowsCoordinates") -> COORD:
        """Converts a WindowsCoordinates into a wintypes _COORD structure.
        This classmethod is internally called by ctypes to perform the conversion.

        Args:
            value (WindowsCoordinates): The input coordinates to convert.

        Returns:
            wintypes._COORD: The converted coordinates struct.
        """
        return COORD(value.col, value.row)


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", wintypes.WORD),
        ("srWindow", wintypes.SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class CONSOLE_CURSOR_INFO(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("bVisible", wintypes.BOOL)]


_GetStdHandle = windll.kernel32.GetStdHandle
_GetStdHandle.argtypes = [
    wintypes.DWORD,
]
_GetStdHandle.restype = wintypes.HANDLE


def GetStdHandle(handle: int = STDOUT) -> wintypes.HANDLE:
    """Retrieves a handle to the specified standard device (standard input, standard output, or standard error).

    Args:
        handle (int): Integer identifier for the handle. Defaults to -11 (stdout).

    Returns:
        wintypes.HANDLE: The handle
    """
    return cast(wintypes.HANDLE, _GetStdHandle(handle))


_GetConsoleMode = windll.kernel32.GetConsoleMode
_GetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
_GetConsoleMode.restype = wintypes.BOOL


def GetConsoleMode(std_handle: wintypes.HANDLE) -> int:
    """Retrieves the current input mode of a console's input buffer
    or the current output mode of a console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Raises:
        LegacyWindowsError: If any error occurs while calling the Windows console API.

    Returns:
        int: Value representing the current console mode as documented at
            https://docs.microsoft.com/en-us/windows/console/getconsolemode#parameters
    """

    console_mode = wintypes.DWORD()
    success = bool(_GetConsoleMode(std_handle, console_mode))
    if not success:
        raise LegacyWindowsError("Unable to get legacy Windows Console Mode")
    return console_mode.value


_FillConsoleOutputCharacterW = windll.kernel32.FillConsoleOutputCharacterW
_FillConsoleOutputCharacterW.argtypes = [
    wintypes.HANDLE,
    ctypes.c_char,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputCharacterW.restype = wintypes.BOOL


def FillConsoleOutputCharacter(
    std_handle: wintypes.HANDLE,
    char: str,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Writes a character to the console screen buffer a specified number of times, beginning at the specified coordinates.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        char (str): The character to write. Must be a string of length 1.
        length (int): The number of times to write the character.
        start (WindowsCoordinates): The coordinates to start writing at.

    Returns:
        int: The number of characters written.
    """
    character = ctypes.c_char(char.encode())
    num_characters = wintypes.DWORD(length)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputCharacterW(
        std_handle,
        character,
        num_characters,
        start,
        byref(num_written),
    )
    return num_written.value


_FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
_FillConsoleOutputAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputAttribute.restype = wintypes.BOOL


def FillConsoleOutputAttribute(
    std_handle: wintypes.HANDLE,
    attributes: int,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Sets the character attributes for a specified number of character cells,
    beginning at the specified coordinates in a screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours of the cells.
        length (int): The number of cells to set the output attribute of.
        start (WindowsCoordinates): The coordinates of the first cell whose attributes are to be set.

    Returns:
        int: The number of cells whose attributes were actually set.
    """
    num_cells = wintypes.DWORD(length)
    style_attrs = wintypes.WORD(attributes)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputAttribute(
        std_handle, style_attrs, num_cells, start, byref(num_written)
    )
    return num_written.value


_SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
_SetConsoleTextAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
]
_SetConsoleTextAttribute.restype = wintypes.BOOL


def SetConsoleTextAttribute(
    std_handle: wintypes.HANDLE, attributes: wintypes.WORD
) -> bool:
    """Set the colour attributes for all text written after this function is called.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours.


    Returns:
        bool: True if the attribute was set successfully, otherwise False.
    """
    return bool(_SetConsoleTextAttribute(std_handle, attributes))


_GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
_GetConsoleScreenBufferInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
]
_GetConsoleScreenBufferInfo.restype = wintypes.BOOL


def GetConsoleScreenBufferInfo(
    std_handle: wintypes.HANDLE,
) -> CONSOLE_SCREEN_BUFFER_INFO:
    """Retrieves information about the specified console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Returns:
        CONSOLE_SCREEN_BUFFER_INFO: A CONSOLE_SCREEN_BUFFER_INFO ctype struct contain information about
            screen size, cursor position, colour attributes, and more."""
    console_screen_buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    _GetConsoleScreenBufferInfo(std_handle, byref(console_screen_buffer_info))
    return console_screen_buffer_info


_SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
_SetConsoleCursorPosition.argtypes = [
    wintypes.HANDLE,
    cast(Type[COORD], WindowsCoordinates),
]
_SetConsoleCursorPosition.restype = wintypes.BOOL


def SetConsoleCursorPosition(
    std_handle: wintypes.HANDLE, coords: WindowsCoordinates
) -> bool:
    """Set the position of the cursor in the console screen

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        coords (WindowsCoordinates): The coordinates to move the cursor to.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorPosition(std_handle, coords))


_GetConsoleCursorInfo = windll.kernel32.GetConsoleCursorInfo
_GetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_GetConsoleCursorInfo.restype = wintypes.BOOL


def GetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Get the cursor info - used to get cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct that receives information
            about the console's cursor.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_GetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleCursorInfo = windll.kernel32.SetConsoleCursorInfo
_SetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_SetConsoleCursorInfo.restype = wintypes.BOOL


def SetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Set the cursor info - used for adjusting cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct containing the new cursor info.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleTitle = windll.kernel32.SetConsoleTitleW
_SetConsoleTitle.argtypes = [wintypes.LPCWSTR]
_SetConsoleTitle.restype = wintypes.BOOL


def SetConsoleTitle(title: str) -> bool:
    """Sets the title of the current console window

    Args:
        title (str): The new title of the console window.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleTitle(title))


class LegacyWindowsTerm:
    """This class allows interaction with the legacy Windows Console API. It should only be used in the context
    of environments where virtual terminal processing is not available. However, if it is used in a Windows environment,
    the entire API should work.

    Args:
        file (IO[str]): The file which the Windows Console API HANDLE is retrieved from, defaults to sys.stdout.
    """

    BRIGHT_BIT = 8

    # Indices are ANSI color numbers, values are the corresponding Windows Console API color numbers
    ANSI_TO_WINDOWS = [
        0,  # black                      The Windows colours are defined in wincon.h as follows:
        4,  # red                         define FOREGROUND_BLUE            0x0001 -- 0000 0001
        2,  # green                       define FOREGROUND_GREEN           0x0002 -- 0000 0010
        6,  # yellow                      define FOREGROUND_RED             0x0004 -- 0000 0100
        1,  # blue                        define FOREGROUND_INTENSITY       0x0008 -- 0000 1000
        5,  # magenta                     define BACKGROUND_BLUE            0x0010 -- 0001 0000
        3,  # cyan                        define BACKGROUND_GREEN           0x0020 -- 0010 0000
        7,  # white                       define BACKGROUND_RED             0x0040 -- 0100 0000
        8,  # bright black (grey)         define BACKGROUND_INTENSITY       0x0080 -- 1000 0000
        12,  # bright red
        10,  # bright green
        14,  # bright yellow
        9,  # bright blue
        13,  # bright magenta
        11,  # bright cyan
        15,  # bright white
    ]

    def __init__(self, file: "IO[str]") -> None:
        handle = GetStdHandle(STDOUT)
        self._handle = handle
        default_text = GetConsoleScreenBufferInfo(handle).wAttributes
        self._default_text = default_text

        self._default_fore = default_text & 7
        self._default_back = (default_text >> 4) & 7
        self._default_attrs = self._default_fore | (self._default_back << 4)

        self._file = file
        self.write = file.write
        self.flush = file.flush

    @property
    def cursor_position(self) -> WindowsCoordinates:
        """Returns the current position of the cursor (0-based)

        Returns:
            WindowsCoordinates: The current cursor position.
        """
        coord: COORD = GetConsoleScreenBufferInfo(self._handle).dwCursorPosition
        return WindowsCoordinates(row=coord.Y, col=coord.X)

    @property
    def screen_size(self) -> WindowsCoordinates:
        """Returns the current size of the console screen buffer, in character columns and rows

        Returns:
            WindowsCoordinates: The width and height of the screen as WindowsCoordinates.
        """
        screen_size: COORD = GetConsoleScreenBufferInfo(self._handle).dwSize
        return WindowsCoordinates(row=screen_size.Y, col=screen_size.X)

    def write_text(self, text: str) -> None:
        """Write text directly to the terminal without any modification of styles

        Args:
            text (str): The text to write to the console
        """
        self.write(text)
        self.flush()

    def write_styled(self, text: str, style: Style) -> None:
        """Write styled text to the terminal.

        Args:
            text (str): The text to write
            style (Style): The style of the text
        """
        color = style.color
        bgcolor = style.bgcolor
        if style.reverse:
            color, bgcolor = bgcolor, color

        if color:
            fore = color.downgrade(ColorSystem.WINDOWS).number
            fore = fore if fore is not None else 7  # Default to ANSI 7: White
            if style.bold:
                fore = fore | self.BRIGHT_BIT
            if style.dim:
                fore = fore & ~self.BRIGHT_BIT
            fore = self.ANSI_TO_WINDOWS[fore]
        else:
            fore = self._default_fore

        if bgcolor:
            back = bgcolor.downgrade(ColorSystem.WINDOWS).number
            back = back if back is not None else 0  # Default to ANSI 0: Black
            back = self.ANSI_TO_WINDOWS[back]
        else:
            back = self._default_back

        assert fore is not None
        assert back is not None

        SetConsoleTextAttribute(
            self._handle, attributes=ctypes.c_ushort(fore | (back << 4))
        )
        self.write_text(text)
        SetConsoleTextAttribute(self._handle, attributes=self._default_text)

    def move_cursor_to(self, new_position: WindowsCoordinates) -> None:
        """Set the position of the cursor

        Args:
            new_position (WindowsCoordinates): The WindowsCoordinates representing the new position of the cursor.
        """
        if new_position.col < 0 or new_position.row < 0:
            return
        SetConsoleCursorPosition(self._handle, coords=new_position)

    def erase_line(self) -> None:
        """Erase all content on the line the cursor is currently located at"""
        screen_size = self.screen_size
        cursor_position = self.cursor_position
        cells_to_erase = screen_size.col
        start_coordinates = WindowsCoordinates(row=cursor_position.row, col=0)
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=start_coordinates
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=start_coordinates,
        )

    def erase_end_of_line(self) -> None:
        """Erase all content from the cursor position to the end of that line"""
        cursor_position = self.cursor_position
        cells_to_erase = self.screen_size.col - cursor_position.col
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=cursor_position
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=cursor_position,
        )

    def erase_start_of_line(self) -> None:
        """Erase all content from the cursor position to the start of that line"""
        row, col = self.cursor_position
        start = WindowsCoordinates(row, 0)
        FillConsoleOutputCharacter(self._handle, " ", length=col, start=start)
        FillConsoleOutputAttribute(
            self._handle, self._default_attrs, length=col, start=start
        )

    def move_cursor_up(self) -> None:
        """Move the cursor up a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row - 1, col=cursor_position.col
            ),
        )

    def move_cursor_down(self) -> None:
        """Move the cursor down a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row + 1,
                col=cursor_position.col,
            ),
        )

    def move_cursor_forward(self) -> None:
        """Move the cursor forward a single cell. Wrap to the next line if required."""
        row, col = self.cursor_position
        if col == self.screen_size.col - 1:
            row += 1
            col = 0
        else:
            col += 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def move_cursor_to_column(self, column: int) -> None:
        """Move cursor to the column specified by the zero-based column index, staying on the same row

        Args:
            column (int): The zero-based column index to move the cursor to.
        """
        row, _ = self.cursor_position
        SetConsoleCursorPosition(self._handle, coords=WindowsCoordinates(row, column))

    def move_cursor_backward(self) -> None:
        """Move the cursor backward a single cell. Wrap to the previous line if required."""
        row, col = self.cursor_position
        if col == 0:
            row -= 1
            col = self.screen_size.col - 1
        else:
            col -= 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def hide_cursor(self) -> None:
        """Hide the cursor"""
        current_cursor_size = self._get_cursor_size()
        invisible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=0)
        SetConsoleCursorInfo(self._handle, cursor_info=invisible_cursor)

    def show_cursor(self) -> None:
        """Show the cursor"""
        current_cursor_size = self._get_cursor_size()
        visible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=1)
        SetConsoleCursorInfo(self._handle, cursor_info=visible_cursor)

    def set_title(self, title: str) -> None:
        """Set the title of the terminal window

        Args:
            title (str): The new title of the console window
        """
        assert len(title) < 255, "Console title must be less than 255 characters"
        SetConsoleTitle(title)

    def _get_cursor_size(self) -> int:
        """Get the percentage of the character cell that is filled by the cursor"""
        cursor_info = CONSOLE_CURSOR_INFO()
        GetConsoleCursorInfo(self._handle, cursor_info=cursor_info)
        return int(cursor_info.dwSize)


if __name__ == "__main__":
    handle = GetStdHandle()

    from rich.console import Console

    console = Console()

    term = LegacyWindowsTerm(sys.stdout)
    term.set_title("Win32 Console Examples")

    style = Style(color="black", bgcolor="red")

    heading = Style.parse("black on green")

    # Check colour output
    console.rule("Checking colour output")
    console.print("[on red]on red!")
    console.print("[blue]blue!")
    console.print("[yellow]yellow!")
    console.print("[bold yellow]bold yellow!")
    console.print("[bright_yellow]bright_yellow!")
    console.print("[dim bright_yellow]dim bright_yellow!")
    console.print("[italic cyan]italic cyan!")
    console.print("[bold white on blue]bold white on blue!")
    console.print("[reverse bold white on blue]reverse bold white on blue!")
    console.print("[bold black on cyan]bold black on cyan!")
    console.print("[black on green]black on green!")
    console.print("[blue on green]blue on green!")
    console.print("[white on black]white on black!")
    console.print("[black on white]black on white!")
    console.print("[#1BB152 on #DA812D]#1BB152 on #DA812D!")

    # Check cursor movement
    console.rule("Checking cursor movement")
    console.print()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("went back and wrapped to prev line")
    time.sleep(1)
    term.move_cursor_up()
    term.write_text("we go up")
    time.sleep(1)
    term.move_cursor_down()
    term.write_text("and down")
    time.sleep(1)
    term.move_cursor_up()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went up and back 2")
    time.sleep(1)
    term.move_cursor_down()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went down and back 2")
    time.sleep(1)

    # Check erasing of lines
    term.hide_cursor()
    console.print()
    console.rule("Checking line erasing")
    console.print("\n...Deleting to the start of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)
    term.move_cursor_to_column(16)
    term.write_styled("<", Style.parse("black on red"))
    term.move_cursor_backward()
    time.sleep(1)
    term.erase_start_of_line()
    time.sleep(1)

    console.print("\n\n...And to the end of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)

    term.move_cursor_to_column(16)
    term.write_styled(">", Style.parse("black on red"))
    time.sleep(1)
    term.erase_end_of_line()
    time.sleep(1)

    console.print("\n\n...Now the whole line will be erased...")
    term.write_styled("I'm going to disappear!", style=Style.parse("black on cyan"))
    time.sleep(1)
    term.erase_line()

    term.show_cursor()
    print("\n")

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\search.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Process memory finder
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
Process memory search.

@group Memory search:
    Search,
    Pattern,
    BytePattern,
    TextPattern,
    RegExpPattern,
    HexPattern
"""

__revision__ = "$Id$"

__all__ = [
    "Search",
    "Pattern",
    "BytePattern",
    "TextPattern",
    "RegExpPattern",
    "HexPattern",
]

from winappdbg.textio import HexInput
from winappdbg.util import StaticClass, MemoryAddresses
from winappdbg import win32

import warnings

try:
    # http://pypi.python.org/pypi/regex
    import regex as re
except ImportError:
    import re

# ==============================================================================


class Pattern(object):
    """
    Base class for search patterns.

    The following L{Pattern} subclasses are provided by WinAppDbg:
     - L{BytePattern}
     - L{TextPattern}
     - L{RegExpPattern}
     - L{HexPattern}

    @see: L{Search.search_process}
    """

    def __init__(self, pattern):
        """
        Class constructor.

        The only mandatory argument should be the pattern string.

        This method B{MUST} be reimplemented by subclasses of L{Pattern}.
        """
        raise NotImplementedError()

    def __len__(self):
        """
        Returns the maximum expected length of the strings matched by this
        pattern. Exact behavior is implementation dependent.

        Ideally it should be an exact value, but in some cases it's not
        possible to calculate so an upper limit should be returned instead.

        If that's not possible either an exception must be raised.

        This value will be used to calculate the required buffer size when
        doing buffered searches.

        This method B{MUST} be reimplemented by subclasses of L{Pattern}.
        """
        raise NotImplementedError()

    def read(self, process, address, size):
        """
        Reads the requested number of bytes from the process memory at the
        given address.

        Subclasses of L{Pattern} tipically don't need to reimplement this
        method.
        """
        return process.read(address, size)

    def find(self, buffer, pos=None):
        """
        Searches for the pattern in the given buffer, optionally starting at
        the given position within the buffer.

        This method B{MUST} be reimplemented by subclasses of L{Pattern}.

        @type  buffer: str
        @param buffer: Buffer to search on.

        @type  pos: int
        @param pos:
            (Optional) Position within the buffer to start searching from.

        @rtype:  tuple( int, int )
        @return: Tuple containing the following:
             - Position within the buffer where a match is found, or C{-1} if
               no match was found.
             - Length of the matched data if a match is found, or undefined if
               no match was found.
        """
        raise NotImplementedError()

    def found(self, address, size, data):
        """
        This method gets called when a match is found.

        This allows subclasses of L{Pattern} to filter out unwanted results,
        or modify the results before giving them to the caller of
        L{Search.search_process}.

        If the return value is C{None} the result is skipped.

        Subclasses of L{Pattern} don't need to reimplement this method unless
        filtering is needed.

        @type  address: int
        @param address: The memory address where the pattern was found.

        @type  size: int
        @param size: The size of the data that matches the pattern.

        @type  data: str
        @param data: The data that matches the pattern.

        @rtype:  tuple( int, int, str )
        @return: Tuple containing the following:
             * The memory address where the pattern was found.
             * The size of the data that matches the pattern.
             * The data that matches the pattern.
        """
        return (address, size, data)


# ------------------------------------------------------------------------------


class BytePattern(Pattern):
    """
    Fixed byte pattern.

    @type pattern: str
    @ivar pattern: Byte string to search for.

    @type length: int
    @ivar length: Length of the byte pattern.
    """

    def __init__(self, pattern):
        """
        @type  pattern: str
        @param pattern: Byte string to search for.
        """
        self.pattern = str(pattern)
        self.length = len(pattern)

    def __len__(self):
        """
        Returns the exact length of the pattern.

        @see: L{Pattern.__len__}
        """
        return self.length

    def find(self, buffer, pos=None):
        return buffer.find(self.pattern, pos), self.length


# ------------------------------------------------------------------------------

# FIXME: case insensitive compat.unicode searches are probably buggy!


class TextPattern(BytePattern):
    """
    Text pattern.

    @type isUnicode: bool
    @ivar isUnicode: C{True} if the text to search for is a compat.unicode string,
        C{False} otherwise.

    @type encoding: str
    @ivar encoding: Encoding for the text parameter.
        Only used when the text to search for is a Unicode string.
        Don't change unless you know what you're doing!

    @type caseSensitive: bool
    @ivar caseSensitive: C{True} of the search is case sensitive,
        C{False} otherwise.
    """

    def __init__(self, text, encoding="utf-16le", caseSensitive=False):
        """
        @type  text: str or compat.unicode
        @param text: Text to search for.

        @type  encoding: str
        @param encoding: (Optional) Encoding for the text parameter.
            Only used when the text to search for is a Unicode string.
            Don't change unless you know what you're doing!

        @type  caseSensitive: bool
        @param caseSensitive: C{True} of the search is case sensitive,
            C{False} otherwise.
        """
        self.isUnicode = isinstance(text, compat.unicode)
        self.encoding = encoding
        self.caseSensitive = caseSensitive
        if not self.caseSensitive:
            pattern = text.lower()
        if self.isUnicode:
            pattern = text.encode(encoding)
        super(TextPattern, self).__init__(pattern)

    def read(self, process, address, size):
        data = super(TextPattern, self).read(address, size)
        if not self.caseSensitive:
            if self.isUnicode:
                try:
                    encoding = self.encoding
                    text = data.decode(encoding, "replace")
                    text = text.lower()
                    new_data = text.encode(encoding, "replace")
                    if len(data) == len(new_data):
                        data = new_data
                    else:
                        data = data.lower()
                except Exception:
                    data = data.lower()
            else:
                data = data.lower()
        return data

    def found(self, address, size, data):
        if self.isUnicode:
            try:
                data = compat.unicode(data, self.encoding)
            except Exception:
                ##                traceback.print_exc()    # XXX DEBUG
                return None
        return (address, size, data)


# ------------------------------------------------------------------------------


class RegExpPattern(Pattern):
    """
    Regular expression pattern.

    @type pattern: str
    @ivar pattern: Regular expression in text form.

    @type flags: int
    @ivar flags: Regular expression flags.

    @type regexp: re.compile
    @ivar regexp: Regular expression in compiled form.

    @type maxLength: int
    @ivar maxLength:
        Maximum expected length of the strings matched by this regular
        expression.

        This value will be used to calculate the required buffer size when
        doing buffered searches.

        Ideally it should be an exact value, but in some cases it's not
        possible to calculate so an upper limit should be given instead.

        If that's not possible either, C{None} should be used. That will
        cause an exception to be raised if this pattern is used in a
        buffered search.
    """

    def __init__(self, regexp, flags=0, maxLength=None):
        """
        @type  regexp: str
        @param regexp: Regular expression string.

        @type  flags: int
        @param flags: Regular expression flags.

        @type  maxLength: int
        @param maxLength: Maximum expected length of the strings matched by
            this regular expression.

            This value will be used to calculate the required buffer size when
            doing buffered searches.

            Ideally it should be an exact value, but in some cases it's not
            possible to calculate so an upper limit should be given instead.

            If that's not possible either, C{None} should be used. That will
            cause an exception to be raised if this pattern is used in a
            buffered search.
        """
        self.pattern = regexp
        self.flags = flags
        self.regexp = re.compile(regexp, flags)
        self.maxLength = maxLength

    def __len__(self):
        """
        Returns the maximum expected length of the strings matched by this
        pattern. This value is taken from the C{maxLength} argument of the
        constructor if this class.

        Ideally it should be an exact value, but in some cases it's not
        possible to calculate so an upper limit should be returned instead.

        If that's not possible either an exception must be raised.

        This value will be used to calculate the required buffer size when
        doing buffered searches.
        """
        if self.maxLength is None:
            raise NotImplementedError()
        return self.maxLength

    def find(self, buffer, pos=None):
        if not pos:  # make sure pos is an int
            pos = 0
        match = self.regexp.search(buffer, pos)
        if match:
            start, end = match.span()
            return start, end - start
        return -1, 0


# ------------------------------------------------------------------------------


class HexPattern(RegExpPattern):
    """
    Hexadecimal pattern.

    Hex patterns must be in this form::
        "68 65 6c 6c 6f 20 77 6f 72 6c 64"  # "hello world"

    Spaces are optional. Capitalization of hex digits doesn't matter.
    This is exactly equivalent to the previous example::
        "68656C6C6F20776F726C64"            # "hello world"

    Wildcards are allowed, in the form of a C{?} sign in any hex digit::
        "5? 5? c3"          # pop register / pop register / ret
        "b8 ?? ?? ?? ??"    # mov eax, immediate value

    @type pattern: str
    @ivar pattern: Hexadecimal pattern.
    """

    def __new__(cls, pattern):
        """
        If the pattern is completely static (no wildcards are present) a
        L{BytePattern} is created instead. That's because searching for a
        fixed byte pattern is faster than searching for a regular expression.
        """
        if "?" not in pattern:
            return BytePattern(HexInput.hexadecimal(pattern))
        return object.__new__(cls, pattern)

    def __init__(self, hexa):
        """
        Hex patterns must be in this form::
            "68 65 6c 6c 6f 20 77 6f 72 6c 64"  # "hello world"

        Spaces are optional. Capitalization of hex digits doesn't matter.
        This is exactly equivalent to the previous example::
            "68656C6C6F20776F726C64"            # "hello world"

        Wildcards are allowed, in the form of a C{?} sign in any hex digit::
            "5? 5? c3"          # pop register / pop register / ret
            "b8 ?? ?? ?? ??"    # mov eax, immediate value

        @type  hexa: str
        @param hexa: Pattern to search for.
        """
        maxLength = len([x for x in hexa if x in "?0123456789ABCDEFabcdef"]) / 2
        super(HexPattern, self).__init__(HexInput.pattern(hexa), maxLength=maxLength)


# ==============================================================================


class Search(StaticClass):
    """
    Static class to group the search functionality.

    Do not instance this class! Use its static methods instead.
    """

    # TODO: aligned searches
    # TODO: method to coalesce search results
    # TODO: search memory dumps
    # TODO: search non-ascii C strings

    @staticmethod
    def search_process(process, pattern, minAddr=None, maxAddr=None, bufferPages=None, overlapping=False):
        """
        Search for the given pattern within the process memory.

        @type  process: L{Process}
        @param process: Process to search.

        @type  pattern: L{Pattern}
        @param pattern: Pattern to search for.
            It must be an instance of a subclass of L{Pattern}.

            The following L{Pattern} subclasses are provided by WinAppDbg:
             - L{BytePattern}
             - L{TextPattern}
             - L{RegExpPattern}
             - L{HexPattern}

            You can also write your own subclass of L{Pattern} for customized
            searches.

        @type  minAddr: int
        @param minAddr: (Optional) Start the search at this memory address.

        @type  maxAddr: int
        @param maxAddr: (Optional) Stop the search at this memory address.

        @type  bufferPages: int
        @param bufferPages: (Optional) Number of memory pages to buffer when
            performing the search. Valid values are:
             - C{0} or C{None}:
               Automatically determine the required buffer size. May not give
               complete results for regular expressions that match variable
               sized strings.
             - C{> 0}: Set the buffer size, in memory pages.
             - C{< 0}: Disable buffering entirely. This may give you a little
               speed gain at the cost of an increased memory usage. If the
               target process has very large contiguous memory regions it may
               actually be slower or even fail. It's also the only way to
               guarantee complete results for regular expressions that match
               variable sized strings.

        @type  overlapping: bool
        @param overlapping: C{True} to allow overlapping results, C{False}
            otherwise.

            Overlapping results yield the maximum possible number of results.

            For example, if searching for "AAAA" within "AAAAAAAA" at address
            C{0x10000}, when overlapping is turned off the following matches
            are yielded::
                (0x10000, 4, "AAAA")
                (0x10004, 4, "AAAA")

            If overlapping is turned on, the following matches are yielded::
                (0x10000, 4, "AAAA")
                (0x10001, 4, "AAAA")
                (0x10002, 4, "AAAA")
                (0x10003, 4, "AAAA")
                (0x10004, 4, "AAAA")

            As you can see, the middle results are overlapping the last two.

        @rtype:  iterator of tuple( int, int, str )
        @return: An iterator of tuples. Each tuple contains the following:
             - The memory address where the pattern was found.
             - The size of the data that matches the pattern.
             - The data that matches the pattern.

        @raise WindowsError: An error occurred when querying or reading the
            process memory.
        """

        # Do some namespace lookups of symbols we'll be using frequently.
        MEM_COMMIT = win32.MEM_COMMIT
        PAGE_GUARD = win32.PAGE_GUARD
        page = MemoryAddresses.pageSize
        read = pattern.read
        find = pattern.find

        # Calculate the address range.
        if minAddr is None:
            minAddr = 0
        if maxAddr is None:
            maxAddr = win32.LPVOID(-1).value  # XXX HACK

        # Calculate the buffer size from the number of pages.
        if bufferPages is None:
            try:
                size = MemoryAddresses.align_address_to_page_end(len(pattern)) + page
            except NotImplementedError:
                size = None
        elif bufferPages > 0:
            size = page * (bufferPages + 1)
        else:
            size = None

        # Get the memory map of the process.
        memory_map = process.iter_memory_map(minAddr, maxAddr)

        # Perform search with buffering enabled.
        if size:
            # Loop through all memory blocks containing data.
            buffer = ""  # buffer to hold the memory data
            prev_addr = 0  # previous memory block address
            last = 0  # position of the last match
            delta = 0  # delta of last read address and start of buffer
            for mbi in memory_map:
                # Skip blocks with no data to search on.
                if not mbi.has_content():
                    continue

                # Get the address and size of this block.
                address = mbi.BaseAddress  # current address to search on
                block_size = mbi.RegionSize  # total size of the block
                if address >= maxAddr:
                    break
                end = address + block_size  # end address of the block

                # If the block is contiguous to the previous block,
                # coalesce the new data in the buffer.
                if delta and address == prev_addr:
                    buffer += read(process, address, page)

                # If not, clear the buffer and read new data.
                else:
                    buffer = read(process, address, min(size, block_size))
                    last = 0
                    delta = 0

                # Search for the pattern in this block.
                while 1:
                    # Yield each match of the pattern in the buffer.
                    pos, length = find(buffer, last)
                    while pos >= last:
                        match_addr = address + pos - delta
                        if minAddr <= match_addr < maxAddr:
                            result = pattern.found(match_addr, length, buffer[pos : pos + length])
                            if result is not None:
                                yield result
                        if overlapping:
                            last = pos + 1
                        else:
                            last = pos + length
                        pos, length = find(buffer, last)

                    # Advance to the next page.
                    address = address + page
                    block_size = block_size - page
                    prev_addr = address

                    # Fix the position of the last match.
                    last = last - page
                    if last < 0:
                        last = 0

                    # Remove the first page in the buffer.
                    buffer = buffer[page:]
                    delta = page

                    # If we haven't reached the end of the block yet,
                    # read the next page in the block and keep seaching.
                    if address < end:
                        buffer = buffer + read(process, address, page)

                    # Otherwise, we're done searching this block.
                    else:
                        break

        # Perform search with buffering disabled.
        else:
            # Loop through all memory blocks containing data.
            for mbi in memory_map:
                # Skip blocks with no data to search on.
                if not mbi.has_content():
                    continue

                # Get the address and size of this block.
                address = mbi.BaseAddress
                block_size = mbi.RegionSize
                if address >= maxAddr:
                    break

                # Read the whole memory region.
                buffer = process.read(address, block_size)

                # Search for the pattern in this region.
                pos, length = find(buffer)
                last = 0
                while pos >= last:
                    match_addr = address + pos
                    if minAddr <= match_addr < maxAddr:
                        result = pattern.found(match_addr, length, buffer[pos : pos + length])
                        if result is not None:
                            yield result
                    if overlapping:
                        last = pos + 1
                    else:
                        last = pos + length
                    pos, length = find(buffer, last)

    @classmethod
    def extract_ascii_strings(cls, process, minSize=4, maxSize=1024):
        """
        Extract ASCII strings from the process memory.

        @type  process: L{Process}
        @param process: Process to search.

        @type  minSize: int
        @param minSize: (Optional) Minimum size of the strings to search for.

        @type  maxSize: int
        @param maxSize: (Optional) Maximum size of the strings to search for.

        @rtype:  iterator of tuple(int, int, str)
        @return: Iterator of strings extracted from the process memory.
            Each tuple contains the following:
             - The memory address where the string was found.
             - The size of the string.
             - The string.
        """
        regexp = r"[\s\w\!\@\#\$\%%\^\&\*\(\)\{\}\[\]\~\`\'\"\:\;\.\,\\\/\-\+\=\_\<\>]{%d,%d}\0" % (minSize, maxSize)
        pattern = RegExpPattern(regexp, 0, maxSize)
        return cls.search_process(process, pattern, overlapping=False)

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\start_terminal_interface.py ===
import argparse
import os
import sys
import time

import pkg_resources

from interpreter.terminal_interface.contributing_conversations import (
    contribute_conversation_launch_logic,
    contribute_conversations,
)

from .conversation_navigator import conversation_navigator
from .profiles.profiles import open_storage_dir, profile, reset_profile
from .utils.check_for_update import check_for_update
from .validate_llm_settings import validate_llm_settings


def start_terminal_interface(interpreter):
    """
    Meant to be used from the command line. Parses arguments, starts OI's terminal interface.
    """

    # Instead use an async interpreter, which has a server. Set settings on that
    if "--server" in sys.argv:
        from interpreter import AsyncInterpreter

        interpreter = AsyncInterpreter()

    arguments = [
        {
            "name": "profile",
            "nickname": "p",
            "help_text": "name of profile. run `--profiles` to open profile directory",
            "type": str,
            "default": "default.yaml",
        },
        {
            "name": "custom_instructions",
            "nickname": "ci",
            "help_text": "custom instructions for the language model. will be appended to the system_message",
            "type": str,
            "attribute": {"object": interpreter, "attr_name": "custom_instructions"},
        },
        {
            "name": "system_message",
            "nickname": "sm",
            "help_text": "(we don't recommend changing this) base prompt for the language model",
            "type": str,
            "attribute": {"object": interpreter, "attr_name": "system_message"},
        },
        {
            "name": "auto_run",
            "nickname": "y",
            "help_text": "automatically run generated code",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "auto_run"},
        },
        {
            "name": "no_highlight_active_line",
            "nickname": "nhl",
            "help_text": "turn off active line highlighting in code blocks",
            "type": bool,
            "action": "store_true",
            "default": False,  # Default to False, meaning highlighting is on by default
        },
        {
            "name": "verbose",
            "nickname": "v",
            "help_text": "print detailed logs",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "verbose"},
        },
        {
            "name": "model",
            "nickname": "m",
            "help_text": "language model to use",
            "type": str,
            "attribute": {"object": interpreter.llm, "attr_name": "model"},
        },
        {
            "name": "temperature",
            "nickname": "t",
            "help_text": "optional temperature setting for the language model",
            "type": float,
            "attribute": {"object": interpreter.llm, "attr_name": "temperature"},
        },
        {
            "name": "llm_supports_vision",
            "nickname": "lsv",
            "help_text": "inform OI that your model supports vision, and can receive vision inputs",
            "type": bool,
            "action": argparse.BooleanOptionalAction,
            "attribute": {"object": interpreter.llm, "attr_name": "supports_vision"},
        },
        {
            "name": "llm_supports_functions",
            "nickname": "lsf",
            "help_text": "inform OI that your model supports OpenAI-style functions, and can make function calls",
            "type": bool,
            "action": argparse.BooleanOptionalAction,
            "attribute": {"object": interpreter.llm, "attr_name": "supports_functions"},
        },
        {
            "name": "context_window",
            "nickname": "cw",
            "help_text": "optional context window size for the language model",
            "type": int,
            "attribute": {"object": interpreter.llm, "attr_name": "context_window"},
        },
        {
            "name": "max_tokens",
            "nickname": "x",
            "help_text": "optional maximum number of tokens for the language model",
            "type": int,
            "attribute": {"object": interpreter.llm, "attr_name": "max_tokens"},
        },
        {
            "name": "max_budget",
            "nickname": "b",
            "help_text": "optionally set the max budget (in USD) for your llm calls",
            "type": float,
            "attribute": {"object": interpreter.llm, "attr_name": "max_budget"},
        },
        {
            "name": "api_base",
            "nickname": "ab",
            "help_text": "optionally set the API base URL for your llm calls (this will override environment variables)",
            "type": str,
            "attribute": {"object": interpreter.llm, "attr_name": "api_base"},
        },
        {
            "name": "api_key",
            "nickname": "ak",
            "help_text": "optionally set the API key for your llm calls (this will override environment variables)",
            "type": str,
            "attribute": {"object": interpreter.llm, "attr_name": "api_key"},
        },
        {
            "name": "api_version",
            "nickname": "av",
            "help_text": "optionally set the API version for your llm calls (this will override environment variables)",
            "type": str,
            "attribute": {"object": interpreter.llm, "attr_name": "api_version"},
        },
        {
            "name": "max_output",
            "nickname": "xo",
            "help_text": "optional maximum number of characters for code outputs",
            "type": int,
            "attribute": {"object": interpreter, "attr_name": "max_output"},
        },
        {
            "name": "loop",
            "help_text": "runs OI in a loop, requiring it to admit to completing/failing task",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "loop"},
        },
        {
            "name": "disable_telemetry",
            "nickname": "dt",
            "help_text": "disables sending of basic anonymous usage stats",
            "type": bool,
            "default": False,
            "attribute": {"object": interpreter, "attr_name": "disable_telemetry"},
        },
        {
            "name": "offline",
            "nickname": "o",
            "help_text": "turns off all online features (except the language model, if it's hosted)",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "offline"},
        },
        {
            "name": "speak_messages",
            "nickname": "sp",
            "help_text": "(Mac only, experimental) use the applescript `say` command to read messages aloud",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "speak_messages"},
        },
        {
            "name": "safe_mode",
            "nickname": "safe",
            "help_text": "optionally enable safety mechanisms like code scanning; valid options are off, ask, and auto",
            "type": str,
            "choices": ["off", "ask", "auto"],
            "default": "off",
            "attribute": {"object": interpreter, "attr_name": "safe_mode"},
        },
        {
            "name": "debug",
            "nickname": "debug",
            "help_text": "debug mode for open interpreter developers",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "debug"},
        },
        {
            "name": "fast",
            "nickname": "f",
            "help_text": "runs `interpreter --model gpt-4o-mini` and asks OI to be extremely concise (shortcut for `interpreter --profile fast`)",
            "type": bool,
        },
        {
            "name": "multi_line",
            "nickname": "ml",
            "help_text": "enable multi-line inputs starting and ending with ```",
            "type": bool,
            "attribute": {"object": interpreter, "attr_name": "multi_line"},
        },
        {
            "name": "local",
            "nickname": "l",
            "help_text": "setup a local model (shortcut for `interpreter --profile local`)",
            "type": bool,
        },
        {
            "name": "codestral",
            "help_text": "shortcut for `interpreter --profile codestral`",
            "type": bool,
        },
        {
            "name": "assistant",
            "help_text": "shortcut for `interpreter --profile assistant.py`",
            "type": bool,
        },
        {
            "name": "llama3",
            "help_text": "shortcut for `interpreter --profile llama3`",
            "type": bool,
        },
        {
            "name": "groq",
            "help_text": "shortcut for `interpreter --profile groq`",
            "type": bool,
        },
        {
            "name": "vision",
            "nickname": "vi",
            "help_text": "experimentally use vision for supported languages (shortcut for `interpreter --profile vision`)",
            "type": bool,
        },
        {
            "name": "os",
            "nickname": "os",
            "help_text": "experimentally let Open Interpreter control your mouse and keyboard (shortcut for `interpreter --profile os`)",
            "type": bool,
        },
        # Special commands
        {
            "name": "reset_profile",
            "help_text": "reset a profile file. run `--reset_profile` without an argument to reset all default profiles",
            "type": str,
            "default": "NOT_PROVIDED",
            "nargs": "?",  # This means you can pass in nothing if you want
        },
        {"name": "profiles", "help_text": "opens profiles directory", "type": bool},
        {
            "name": "local_models",
            "help_text": "opens local models directory",
            "type": bool,
        },
        {
            "name": "conversations",
            "help_text": "list conversations to resume",
            "type": bool,
        },
        {
            "name": "server",
            "help_text": "start open interpreter as a server",
            "type": bool,
        },
        {
            "name": "version",
            "help_text": "get Open Interpreter's version number",
            "type": bool,
        },
        {
            "name": "contribute_conversation",
            "help_text": "let Open Interpreter use the current conversation to train an Open-Source LLM",
            "type": bool,
            "attribute": {
                "object": interpreter,
                "attr_name": "contribute_conversation",
            },
        },
        {
            "name": "plain",
            "nickname": "pl",
            "help_text": "set output to plain text",
            "type": bool,
            "attribute": {
                "object": interpreter,
                "attr_name": "plain_text_display",
            },
        },
        {
            "name": "stdin",
            "nickname": "s",
            "help_text": "Run OI in stdin mode",
            "type": bool,
        },
    ]

    if "--stdin" in sys.argv and "--plain" not in sys.argv:
        sys.argv += ["--plain"]

    # i shortcut
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        message = " ".join(sys.argv[1:])
        interpreter.messages.append(
            {"role": "user", "type": "message", "content": "I " + message}
        )
        sys.argv = sys.argv[:1]

        interpreter.custom_instructions = "UPDATED INSTRUCTIONS: You are in ULTRA FAST, ULTRA CERTAIN mode. Do not ask the user any questions or run code to gathet information. Go as quickly as you can. Run code quickly. Do not plan out loud, simply start doing the best thing. The user expects speed. Trust that the user knows best. Just interpret their ambiguous command as quickly and certainly as possible and try to fulfill it IN ONE COMMAND, assuming they have the right information. If they tell you do to something, just do it quickly in one command, DO NOT try to get more information (for example by running `cat` to get a file's infomration— this is probably unecessary!). DIRECTLY DO THINGS AS FAST AS POSSIBLE."

        files_in_directory = os.listdir()[:100]
        interpreter.custom_instructions += (
            "\nThe files in CWD, which THE USER MAY BE REFERRING TO, are: "
            + ", ".join(files_in_directory)
        )

        # interpreter.debug = True

    # Check for deprecated flags before parsing arguments
    deprecated_flags = {
        "--debug_mode": "--verbose",
    }

    for old_flag, new_flag in deprecated_flags.items():
        if old_flag in sys.argv:
            print(f"\n`{old_flag}` has been renamed to `{new_flag}`.\n")
            time.sleep(1.5)
            sys.argv.remove(old_flag)
            sys.argv.append(new_flag)

    class CustomHelpParser(argparse.ArgumentParser):
        def print_help(self, *args, **kwargs):
            super().print_help(*args, **kwargs)
            special_help_message = '''
Open Interpreter, 2024

Use """ to write multi-line messages.
            '''
            print(special_help_message)

    parser = CustomHelpParser(
        description="Open Interpreter", usage="%(prog)s [options]"
    )

    # Add arguments
    for arg in arguments:
        default = arg.get("default")
        action = arg.get("action", "store_true")
        nickname = arg.get("nickname")

        name_or_flags = [f'--{arg["name"]}']
        if nickname:
            name_or_flags.append(f"-{nickname}")

        # Construct argument name flags
        flags = (
            [f"-{nickname}", f'--{arg["name"]}'] if nickname else [f'--{arg["name"]}']
        )

        if arg["type"] == bool:
            parser.add_argument(
                *flags,
                dest=arg["name"],
                help=arg["help_text"],
                action=action,
                default=default,
            )
        else:
            choices = arg.get("choices")
            parser.add_argument(
                *flags,
                dest=arg["name"],
                help=arg["help_text"],
                type=arg["type"],
                choices=choices,
                default=default,
                nargs=arg.get("nargs"),
            )

    args, unknown_args = parser.parse_known_args()

    # handle unknown arguments
    if unknown_args:
        print(f"\nUnrecognized argument(s): {unknown_args}")
        parser.print_usage()
        print(
            "For detailed documentation of supported arguments, please visit: https://docs.openinterpreter.com/settings/all-settings"
        )
        sys.exit(1)

    if args.profiles:
        open_storage_dir("profiles")
        return

    if args.local_models:
        open_storage_dir("models")
        return

    if args.reset_profile is not None and args.reset_profile != "NOT_PROVIDED":
        reset_profile(
            args.reset_profile
        )  # This will be None if they just ran `--reset_profile`
        return

    if args.version:
        version = pkg_resources.get_distribution("open-interpreter").version
        update_name = "Developer Preview"  # Change this with each major update
        print(f"Open Interpreter {version} {update_name}")
        return

    if args.no_highlight_active_line:
        interpreter.highlight_active_line = False

    # if safe_mode and auto_run are enabled, safe_mode disables auto_run
    if interpreter.auto_run and (
        interpreter.safe_mode == "ask" or interpreter.safe_mode == "auto"
    ):
        setattr(interpreter, "auto_run", False)

    ### Set attributes on interpreter, so that a profile script can read the arguments passed in via the CLI

    set_attributes(args, arguments)

    ### Apply profile

    # Profile shortcuts, which should probably not exist:

    if args.fast:
        args.profile = "fast.yaml"

    if args.vision:
        args.profile = "vision.yaml"

    if args.os:
        args.profile = "os.py"

    if args.local:
        args.profile = "local.py"
        if args.vision:
            # This is local vision, set up moondream!
            interpreter.computer.vision.load()
        if args.os:
            args.profile = "local-os.py"

    if args.codestral:
        args.profile = "codestral.py"
        if args.vision:
            args.profile = "codestral-vision.py"
        if args.os:
            args.profile = "codestral-os.py"

    if args.assistant:
        args.profile = "assistant.py"

    if args.llama3:
        args.profile = "llama3.py"
        if args.vision:
            args.profile = "llama3-vision.py"
        if args.os:
            args.profile = "llama3-os.py"

    if args.groq:
        args.profile = "groq.py"

    interpreter = profile(
        interpreter,
        args.profile or get_argument_dictionary(arguments, "profile")["default"],
    )

    ### Set attributes on interpreter, because the arguments passed in via the CLI should override profile

    set_attributes(args, arguments)
    interpreter.disable_telemetry = (
        os.getenv("DISABLE_TELEMETRY", "false").lower() == "true"
        or args.disable_telemetry
    )

    ### Set some helpful settings we know are likely to be true

    if interpreter.llm.model == "gpt-4" or interpreter.llm.model == "openai/gpt-4":
        if interpreter.llm.context_window is None:
            interpreter.llm.context_window = 6500
        if interpreter.llm.max_tokens is None:
            interpreter.llm.max_tokens = 4096
        if interpreter.llm.supports_functions is None:
            interpreter.llm.supports_functions = (
                False if "vision" in interpreter.llm.model else True
            )

    elif interpreter.llm.model.startswith("gpt-4") or interpreter.llm.model.startswith(
        "openai/gpt-4"
    ):
        if interpreter.llm.context_window is None:
            interpreter.llm.context_window = 123000
        if interpreter.llm.max_tokens is None:
            interpreter.llm.max_tokens = 4096
        if interpreter.llm.supports_functions is None:
            interpreter.llm.supports_functions = (
                False if "vision" in interpreter.llm.model else True
            )

    if interpreter.llm.model.startswith(
        "gpt-3.5-turbo"
    ) or interpreter.llm.model.startswith("openai/gpt-3.5-turbo"):
        if interpreter.llm.context_window is None:
            interpreter.llm.context_window = 16000
        if interpreter.llm.max_tokens is None:
            interpreter.llm.max_tokens = 4096
        if interpreter.llm.supports_functions is None:
            interpreter.llm.supports_functions = True

    ### Check for update

    try:
        if not interpreter.offline and not args.stdin:
            # This message should actually be pushed into the utility
            if check_for_update():
                interpreter.display_message(
                    "> **A new version of Open Interpreter is available.**\n>Please run: `pip install --upgrade open-interpreter`\n\n---"
                )
    except:
        # Doesn't matter
        pass

    if interpreter.llm.api_base:
        if (
            not interpreter.llm.model.lower().startswith("openai/")
            and not interpreter.llm.model.lower().startswith("azure/")
            and not interpreter.llm.model.lower().startswith("ollama")
            and not interpreter.llm.model.lower().startswith("jan")
            and not interpreter.llm.model.lower().startswith("local")
        ):
            interpreter.llm.model = "openai/" + interpreter.llm.model
        elif interpreter.llm.model.lower().startswith("jan/"):
            # Strip jan/ from the model name
            interpreter.llm.model = interpreter.llm.model[4:]

    # If --conversations is used, run conversation_navigator
    if args.conversations:
        conversation_navigator(interpreter)
        return

    if interpreter.llm.model in [
        "claude-3.5",
        "claude-3-5",
        "claude-3.5-sonnet",
        "claude-3-5-sonnet",
    ]:
        interpreter.llm.model = "claude-3-5-sonnet-20240620"

    if not args.server:
        # This SHOULD RUN WHEN THE SERVER STARTS. But it can't rn because
        # if you don't have an API key, a prompt shows up, breaking the whole thing.
        validate_llm_settings(
            interpreter
        )  # This should actually just run interpreter.llm.load() once that's == to validate_llm_settings

    if args.server:
        interpreter.server.run()
        return

    interpreter.in_terminal_interface = True

    contribute_conversation_launch_logic(interpreter)

    # Standard in mode
    if args.stdin:
        stdin_input = input()
        interpreter.plain_text_display = True
        interpreter.chat(stdin_input)
    else:
        interpreter.chat()


def set_attributes(args, arguments):
    for argument_name, argument_value in vars(args).items():
        if argument_value is not None:
            if argument_dictionary := get_argument_dictionary(arguments, argument_name):
                if "attribute" in argument_dictionary:
                    attr_dict = argument_dictionary["attribute"]
                    setattr(attr_dict["object"], attr_dict["attr_name"], argument_value)

                    if args.verbose:
                        print(
                            f"Setting attribute {attr_dict['attr_name']} on {attr_dict['object'].__class__.__name__.lower()} to '{argument_value}'..."
                        )


def get_argument_dictionary(arguments: list[dict], key: str) -> dict:
    if (
        len(
            argument_dictionary_list := list(
                filter(lambda x: x["name"] == key, arguments)
            )
        )
        > 0
    ):
        return argument_dictionary_list[0]
    return {}


def main():
    from interpreter import interpreter

    try:
        start_terminal_interface(interpreter)
    except KeyboardInterrupt:
        try:
            interpreter.computer.terminate()

            if not interpreter.offline and not interpreter.disable_telemetry:
                feedback = None
                if len(interpreter.messages) > 3:
                    feedback = (
                        input("\n\nWas Open Interpreter helpful? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if feedback == "y":
                        feedback = True
                    elif feedback == "n":
                        feedback = False
                    else:
                        feedback = None
                    if feedback != None and not interpreter.contribute_conversation:
                        if interpreter.llm.model == "i":
                            contribute = "y"
                        else:
                            print(
                                "\nThanks for your feedback! Would you like to send us this chat so we can improve?\n"
                            )
                            contribute = input("(y/n): ").strip().lower()

                        if contribute == "y":
                            interpreter.contribute_conversation = True
                            interpreter.display_message(
                                "\n*Thank you for contributing!*\n"
                            )

                if (
                    interpreter.contribute_conversation or interpreter.llm.model == "i"
                ) and interpreter.messages != []:
                    conversation_id = (
                        interpreter.conversation_id
                        if hasattr(interpreter, "conversation_id")
                        else None
                    )
                    contribute_conversations(
                        [interpreter.messages], feedback, conversation_id
                    )

        except KeyboardInterrupt:
            pass
    finally:
        interpreter.computer.terminate()

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm5.py ===
# Natural Language Toolkit: IBM Model 5
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Translation model that keeps track of vacant positions in the target
sentence to decide where to place translated words.

Translation can be viewed as a process where each word in the source
sentence is stepped through sequentially, generating translated words
for each source word. The target sentence can be viewed as being made
up of ``m`` empty slots initially, which gradually fill up as generated
words are placed in them.

Models 3 and 4 use distortion probabilities to decide how to place
translated words. For simplicity, these models ignore the history of
which slots have already been occupied with translated words.
Consider the placement of the last translated word: there is only one
empty slot left in the target sentence, so the distortion probability
should be 1.0 for that position and 0.0 everywhere else. However, the
distortion probabilities for Models 3 and 4 are set up such that all
positions are under consideration.

IBM Model 5 fixes this deficiency by accounting for occupied slots
during translation. It introduces the vacancy function v(j), the number
of vacancies up to, and including, position j in the target sentence.

Terminology
-----------

:Maximum vacancy:
    The number of valid slots that a word can be placed in.
    This is not necessarily the same as the number of vacant slots.
    For example, if a tablet contains more than one word, the head word
    cannot be placed at the last vacant slot because there will be no
    space for the other words in the tablet. The number of valid slots
    has to take into account the length of the tablet.
    Non-head words cannot be placed before the head word, so vacancies
    to the left of the head word are ignored.
:Vacancy difference:
    For a head word: (v(j) - v(center of previous cept))
    Can be positive or negative.
    For a non-head word: (v(j) - v(position of previously placed word))
    Always positive, because successive words in a tablet are assumed to
    appear to the right of the previous word.

Positioning of target words fall under three cases:

1. Words generated by NULL are distributed uniformly
2. For a head word t, its position is modeled by the probability
   v_head(dv | max_v,word_class_t(t))
3. For a non-head word t, its position is modeled by the probability
   v_non_head(dv | max_v,word_class_t(t))

dv and max_v are defined differently for head and non-head words.

The EM algorithm used in Model 5 is:

:E step: In the training data, collect counts, weighted by prior
         probabilities.

         - (a) count how many times a source language word is translated
               into a target language word
         - (b) for a particular word class and maximum vacancy, count how
               many times a head word and the previous cept's center have
               a particular difference in number of vacancies
         - (b) for a particular word class and maximum vacancy, count how
               many times a non-head word and the previous target word
               have a particular difference in number of vacancies
         - (d) count how many times a source word is aligned to phi number
               of target words
         - (e) count how many times NULL is aligned to a target word

:M step: Estimate new probabilities based on the counts from the E step

Like Model 4, there are too many possible alignments to consider. Thus,
a hill climbing approach is used to sample good candidates. In addition,
pruning is used to weed out unlikely alignments based on Model 4 scores.

Notations
---------

:i: Position in the source sentence
     Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
:j: Position in the target sentence
     Valid values are 1, 2, ..., length of target sentence
:l: Number of words in the source sentence, excluding NULL
:m: Number of words in the target sentence
:s: A word in the source language
:t: A word in the target language
:phi: Fertility, the number of target words produced by a source word
:p1: Probability that a target word produced by a source word is
     accompanied by another target word that is aligned to NULL
:p0: 1 - p1
:max_v: Maximum vacancy
:dv: Vacancy difference, Δv

The definition of v_head here differs from GIZA++, section 4.7 of
[Brown et al., 1993], and [Koehn, 2010]. In the latter cases, v_head is
v_head(v(j) | v(center of previous cept),max_v,word_class(t)).

Here, we follow appendix B of [Brown et al., 1993] and combine v(j) with
v(center of previous cept) to obtain dv:
v_head(v(j) - v(center of previous cept) | max_v,word_class(t)).

References
----------

Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

import warnings
from collections import defaultdict
from math import factorial

from nltk.translate import AlignedSent, Alignment, IBMModel, IBMModel4
from nltk.translate.ibm_model import Counts, longest_target_sentence_length


class IBMModel5(IBMModel):
    """
    Translation model that keeps track of vacant positions in the target
    sentence to decide where to place translated words

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'war', 'ja', 'groß'], ['the', 'house', 'was', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['ein', 'haus', 'ist', 'klein'], ['a', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))
    >>> bitext.append(AlignedSent(['ich', 'fasse', 'das', 'buch', 'zusammen'], ['i', 'summarize', 'the', 'book']))
    >>> bitext.append(AlignedSent(['fasse', 'zusammen'], ['summarize']))
    >>> src_classes = {'the': 0, 'a': 0, 'small': 1, 'big': 1, 'house': 2, 'book': 2, 'is': 3, 'was': 3, 'i': 4, 'summarize': 5 }
    >>> trg_classes = {'das': 0, 'ein': 0, 'haus': 1, 'buch': 1, 'klein': 2, 'groß': 2, 'ist': 3, 'war': 3, 'ja': 4, 'ich': 5, 'fasse': 6, 'zusammen': 6 }

    >>> ibm5 = IBMModel5(bitext, 5, src_classes, trg_classes)

    >>> print(round(ibm5.head_vacancy_table[1][1][1], 3))
    1.0
    >>> print(round(ibm5.head_vacancy_table[2][1][1], 3))
    0.0
    >>> print(round(ibm5.non_head_vacancy_table[3][3][6], 3))
    1.0

    >>> print(round(ibm5.fertility_table[2]['summarize'], 3))
    1.0
    >>> print(round(ibm5.fertility_table[1]['book'], 3))
    1.0

    >>> print(round(ibm5.p1, 3))
    0.033

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, None), (4, 3)])

    """

    MIN_SCORE_FACTOR = 0.2
    """
    Alignments with scores below this factor are pruned during sampling
    """

    def __init__(
        self,
        sentence_aligned_corpus,
        iterations,
        source_word_classes,
        target_word_classes,
        probability_tables=None,
    ):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model, vacancy models, a fertility model, and a
        model for generating NULL-aligned words.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int

        :param source_word_classes: Lookup table that maps a source word
            to its word class, the latter represented by an integer id
        :type source_word_classes: dict[str]: int

        :param target_word_classes: Lookup table that maps a target word
            to its word class, the latter represented by an integer id
        :type target_word_classes: dict[str]: int

        :param probability_tables: Optional. Use this to pass in custom
            probability values. If not specified, probabilities will be
            set to a uniform distribution, or some other sensible value.
            If specified, all the following entries must be present:
            ``translation_table``, ``alignment_table``,
            ``fertility_table``, ``p1``, ``head_distortion_table``,
            ``non_head_distortion_table``, ``head_vacancy_table``,
            ``non_head_vacancy_table``. See ``IBMModel``, ``IBMModel4``,
            and ``IBMModel5`` for the type and purpose of these tables.
        :type probability_tables: dict[str]: object
        """
        super().__init__(sentence_aligned_corpus)
        self.reset_probabilities()
        self.src_classes = source_word_classes
        self.trg_classes = target_word_classes

        if probability_tables is None:
            # Get probabilities from IBM model 4
            ibm4 = IBMModel4(
                sentence_aligned_corpus,
                iterations,
                source_word_classes,
                target_word_classes,
            )
            self.translation_table = ibm4.translation_table
            self.alignment_table = ibm4.alignment_table
            self.fertility_table = ibm4.fertility_table
            self.p1 = ibm4.p1
            self.head_distortion_table = ibm4.head_distortion_table
            self.non_head_distortion_table = ibm4.non_head_distortion_table
            self.set_uniform_probabilities(sentence_aligned_corpus)
        else:
            # Set user-defined probabilities
            self.translation_table = probability_tables["translation_table"]
            self.alignment_table = probability_tables["alignment_table"]
            self.fertility_table = probability_tables["fertility_table"]
            self.p1 = probability_tables["p1"]
            self.head_distortion_table = probability_tables["head_distortion_table"]
            self.non_head_distortion_table = probability_tables[
                "non_head_distortion_table"
            ]
            self.head_vacancy_table = probability_tables["head_vacancy_table"]
            self.non_head_vacancy_table = probability_tables["non_head_vacancy_table"]

        for n in range(0, iterations):
            self.train(sentence_aligned_corpus)

    def reset_probabilities(self):
        super().reset_probabilities()
        self.head_vacancy_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: self.MIN_PROB))
        )
        """
        dict[int][int][int]: float. Probability(vacancy difference |
        number of remaining valid positions,target word class).
        Values accessed as ``head_vacancy_table[dv][v_max][trg_class]``.
        """

        self.non_head_vacancy_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: self.MIN_PROB))
        )
        """
        dict[int][int][int]: float. Probability(vacancy difference |
        number of remaining valid positions,target word class).
        Values accessed as ``non_head_vacancy_table[dv][v_max][trg_class]``.
        """

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        """
        Set vacancy probabilities uniformly to
        1 / cardinality of vacancy difference values
        """
        max_m = longest_target_sentence_length(sentence_aligned_corpus)

        # The maximum vacancy difference occurs when a word is placed in
        # the last available position m of the target sentence and the
        # previous word position has no vacancies.
        # The minimum is 1-max_v, when a word is placed in the first
        # available position and the previous word is placed beyond the
        # last available position.
        # Thus, the number of possible vacancy difference values is
        # (max_v) - (1-max_v) + 1 = 2 * max_v.
        if max_m > 0 and (1 / (2 * max_m)) < IBMModel.MIN_PROB:
            warnings.warn(
                "A target sentence is too long ("
                + str(max_m)
                + " words). Results may be less accurate."
            )

        for max_v in range(1, max_m + 1):
            for dv in range(1, max_m + 1):
                initial_prob = 1 / (2 * max_v)
                self.head_vacancy_table[dv][max_v] = defaultdict(lambda: initial_prob)
                self.head_vacancy_table[-(dv - 1)][max_v] = defaultdict(
                    lambda: initial_prob
                )
                self.non_head_vacancy_table[dv][max_v] = defaultdict(
                    lambda: initial_prob
                )
                self.non_head_vacancy_table[-(dv - 1)][max_v] = defaultdict(
                    lambda: initial_prob
                )

    def train(self, parallel_corpus):
        counts = Model5Counts()
        for aligned_sentence in parallel_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)

            # Sample the alignment space
            sampled_alignments, best_alignment = self.sample(aligned_sentence)
            # Record the most probable alignment
            aligned_sentence.alignment = Alignment(
                best_alignment.zero_indexed_alignment()
            )

            # E step (a): Compute normalization factors to weigh counts
            total_count = self.prob_of_alignments(sampled_alignments)

            # E step (b): Collect counts
            for alignment_info in sampled_alignments:
                count = self.prob_t_a_given_s(alignment_info)
                normalized_count = count / total_count

                for j in range(1, m + 1):
                    counts.update_lexical_translation(
                        normalized_count, alignment_info, j
                    )

                slots = Slots(m)
                for i in range(1, l + 1):
                    counts.update_vacancy(
                        normalized_count, alignment_info, i, self.trg_classes, slots
                    )

                counts.update_null_generation(normalized_count, alignment_info)
                counts.update_fertility(normalized_count, alignment_info)

        # M step: Update probabilities with maximum likelihood estimates
        # If any probability is less than MIN_PROB, clamp it to MIN_PROB
        existing_alignment_table = self.alignment_table
        self.reset_probabilities()
        self.alignment_table = existing_alignment_table  # don't retrain

        self.maximize_lexical_translation_probabilities(counts)
        self.maximize_vacancy_probabilities(counts)
        self.maximize_fertility_probabilities(counts)
        self.maximize_null_generation_probabilities(counts)

    def sample(self, sentence_pair):
        """
        Sample the most probable alignments from the entire alignment
        space according to Model 4

        Note that Model 4 scoring is used instead of Model 5 because the
        latter is too expensive to compute.

        First, determine the best alignment according to IBM Model 2.
        With this initial alignment, use hill climbing to determine the
        best alignment according to a IBM Model 4. Add this
        alignment and its neighbors to the sample set. Repeat this
        process with other initial alignments obtained by pegging an
        alignment point. Finally, prune alignments that have
        substantially lower Model 4 scores than the best alignment.

        :param sentence_pair: Source and target language sentence pair
            to generate a sample of alignments from
        :type sentence_pair: AlignedSent

        :return: A set of best alignments represented by their ``AlignmentInfo``
            and the best alignment of the set for convenience
        :rtype: set(AlignmentInfo), AlignmentInfo
        """
        sampled_alignments, best_alignment = super().sample(sentence_pair)
        return self.prune(sampled_alignments), best_alignment

    def prune(self, alignment_infos):
        """
        Removes alignments from ``alignment_infos`` that have
        substantially lower Model 4 scores than the best alignment

        :return: Pruned alignments
        :rtype: set(AlignmentInfo)
        """
        alignments = []
        best_score = 0

        for alignment_info in alignment_infos:
            score = IBMModel4.model4_prob_t_a_given_s(alignment_info, self)
            best_score = max(score, best_score)
            alignments.append((alignment_info, score))

        threshold = IBMModel5.MIN_SCORE_FACTOR * best_score
        alignments = [a[0] for a in alignments if a[1] > threshold]
        return set(alignments)

    def hillclimb(self, alignment_info, j_pegged=None):
        """
        Starting from the alignment in ``alignment_info``, look at
        neighboring alignments iteratively for the best one, according
        to Model 4

        Note that Model 4 scoring is used instead of Model 5 because the
        latter is too expensive to compute.

        There is no guarantee that the best alignment in the alignment
        space will be found, because the algorithm might be stuck in a
        local maximum.

        :param j_pegged: If specified, the search will be constrained to
            alignments where ``j_pegged`` remains unchanged
        :type j_pegged: int

        :return: The best alignment found from hill climbing
        :rtype: AlignmentInfo
        """
        alignment = alignment_info  # alias with shorter name
        max_probability = IBMModel4.model4_prob_t_a_given_s(alignment, self)

        while True:
            old_alignment = alignment
            for neighbor_alignment in self.neighboring(alignment, j_pegged):
                neighbor_probability = IBMModel4.model4_prob_t_a_given_s(
                    neighbor_alignment, self
                )

                if neighbor_probability > max_probability:
                    alignment = neighbor_alignment
                    max_probability = neighbor_probability

            if alignment == old_alignment:
                # Until there are no better alignments
                break

        alignment.score = max_probability
        return alignment

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        probability = 1.0
        MIN_PROB = IBMModel.MIN_PROB
        slots = Slots(len(alignment_info.trg_sentence) - 1)

        def null_generation_term():
            # Binomial distribution: B(m - null_fertility, p1)
            value = 1.0
            p1 = self.p1
            p0 = 1 - p1
            null_fertility = alignment_info.fertility_of_i(0)
            m = len(alignment_info.trg_sentence) - 1
            value *= pow(p1, null_fertility) * pow(p0, m - 2 * null_fertility)
            if value < MIN_PROB:
                return MIN_PROB

            # Combination: (m - null_fertility) choose null_fertility
            for i in range(1, null_fertility + 1):
                value *= (m - null_fertility - i + 1) / i
            return value

        def fertility_term():
            value = 1.0
            src_sentence = alignment_info.src_sentence
            for i in range(1, len(src_sentence)):
                fertility = alignment_info.fertility_of_i(i)
                value *= (
                    factorial(fertility)
                    * self.fertility_table[fertility][src_sentence[i]]
                )
                if value < MIN_PROB:
                    return MIN_PROB
            return value

        def lexical_translation_term(j):
            t = alignment_info.trg_sentence[j]
            i = alignment_info.alignment[j]
            s = alignment_info.src_sentence[i]
            return self.translation_table[t][s]

        def vacancy_term(i):
            value = 1.0
            tablet = alignment_info.cepts[i]
            tablet_length = len(tablet)
            total_vacancies = slots.vacancies_at(len(slots))

            # case 1: NULL-aligned words
            if tablet_length == 0:
                return value

            # case 2: head word
            j = tablet[0]
            previous_cept = alignment_info.previous_cept(j)
            previous_center = alignment_info.center_of_cept(previous_cept)
            dv = slots.vacancies_at(j) - slots.vacancies_at(previous_center)
            max_v = total_vacancies - tablet_length + 1
            trg_class = self.trg_classes[alignment_info.trg_sentence[j]]
            value *= self.head_vacancy_table[dv][max_v][trg_class]
            slots.occupy(j)  # mark position as occupied
            total_vacancies -= 1
            if value < MIN_PROB:
                return MIN_PROB

            # case 3: non-head words
            for k in range(1, tablet_length):
                previous_position = tablet[k - 1]
                previous_vacancies = slots.vacancies_at(previous_position)
                j = tablet[k]
                dv = slots.vacancies_at(j) - previous_vacancies
                max_v = total_vacancies - tablet_length + k + 1 - previous_vacancies
                trg_class = self.trg_classes[alignment_info.trg_sentence[j]]
                value *= self.non_head_vacancy_table[dv][max_v][trg_class]
                slots.occupy(j)  # mark position as occupied
                total_vacancies -= 1
                if value < MIN_PROB:
                    return MIN_PROB

            return value

        # end nested functions

        # Abort computation whenever probability falls below MIN_PROB at
        # any point, since MIN_PROB can be considered as zero
        probability *= null_generation_term()
        if probability < MIN_PROB:
            return MIN_PROB

        probability *= fertility_term()
        if probability < MIN_PROB:
            return MIN_PROB

        for j in range(1, len(alignment_info.trg_sentence)):
            probability *= lexical_translation_term(j)
            if probability < MIN_PROB:
                return MIN_PROB

        for i in range(1, len(alignment_info.src_sentence)):
            probability *= vacancy_term(i)
            if probability < MIN_PROB:
                return MIN_PROB

        return probability

    def maximize_vacancy_probabilities(self, counts):
        MIN_PROB = IBMModel.MIN_PROB
        head_vacancy_table = self.head_vacancy_table
        for dv, max_vs in counts.head_vacancy.items():
            for max_v, trg_classes in max_vs.items():
                for t_cls in trg_classes:
                    estimate = (
                        counts.head_vacancy[dv][max_v][t_cls]
                        / counts.head_vacancy_for_any_dv[max_v][t_cls]
                    )
                    head_vacancy_table[dv][max_v][t_cls] = max(estimate, MIN_PROB)

        non_head_vacancy_table = self.non_head_vacancy_table
        for dv, max_vs in counts.non_head_vacancy.items():
            for max_v, trg_classes in max_vs.items():
                for t_cls in trg_classes:
                    estimate = (
                        counts.non_head_vacancy[dv][max_v][t_cls]
                        / counts.non_head_vacancy_for_any_dv[max_v][t_cls]
                    )
                    non_head_vacancy_table[dv][max_v][t_cls] = max(estimate, MIN_PROB)


class Model5Counts(Counts):
    """
    Data object to store counts of various parameters during training.
    Includes counts for vacancies.
    """

    def __init__(self):
        super().__init__()
        self.head_vacancy = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        self.head_vacancy_for_any_dv = defaultdict(lambda: defaultdict(float))
        self.non_head_vacancy = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        self.non_head_vacancy_for_any_dv = defaultdict(lambda: defaultdict(float))

    def update_vacancy(self, count, alignment_info, i, trg_classes, slots):
        """
        :param count: Value to add to the vacancy counts
        :param alignment_info: Alignment under consideration
        :param i: Source word position under consideration
        :param trg_classes: Target word classes
        :param slots: Vacancy states of the slots in the target sentence.
            Output parameter that will be modified as new words are placed
            in the target sentence.
        """
        tablet = alignment_info.cepts[i]
        tablet_length = len(tablet)
        total_vacancies = slots.vacancies_at(len(slots))

        # case 1: NULL aligned words
        if tablet_length == 0:
            return  # ignore zero fertility words

        # case 2: head word
        j = tablet[0]
        previous_cept = alignment_info.previous_cept(j)
        previous_center = alignment_info.center_of_cept(previous_cept)
        dv = slots.vacancies_at(j) - slots.vacancies_at(previous_center)
        max_v = total_vacancies - tablet_length + 1
        trg_class = trg_classes[alignment_info.trg_sentence[j]]
        self.head_vacancy[dv][max_v][trg_class] += count
        self.head_vacancy_for_any_dv[max_v][trg_class] += count
        slots.occupy(j)  # mark position as occupied
        total_vacancies -= 1

        # case 3: non-head words
        for k in range(1, tablet_length):
            previous_position = tablet[k - 1]
            previous_vacancies = slots.vacancies_at(previous_position)
            j = tablet[k]
            dv = slots.vacancies_at(j) - previous_vacancies
            max_v = total_vacancies - tablet_length + k + 1 - previous_vacancies
            trg_class = trg_classes[alignment_info.trg_sentence[j]]
            self.non_head_vacancy[dv][max_v][trg_class] += count
            self.non_head_vacancy_for_any_dv[max_v][trg_class] += count
            slots.occupy(j)  # mark position as occupied
            total_vacancies -= 1


class Slots:
    """
    Represents positions in a target sentence. Used to keep track of
    which slot (position) is occupied.
    """

    def __init__(self, target_sentence_length):
        self._slots = [False] * (target_sentence_length + 1)  # 1-indexed

    def occupy(self, position):
        """
        :return: Mark slot at ``position`` as occupied
        """
        self._slots[position] = True

    def vacancies_at(self, position):
        """
        :return: Number of vacant slots up to, and including, ``position``
        """
        vacancies = 0
        for k in range(1, position + 1):
            if not self._slots[k]:
                vacancies += 1
        return vacancies

    def __len__(self):
        return len(self._slots) - 1  # exclude dummy zeroeth element

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\_win32_console.py ===
"""Light wrapper around the Win32 Console API - this module should only be imported on Windows

The API that this module wraps is documented at https://docs.microsoft.com/en-us/windows/console/console-functions
"""

import ctypes
import sys
from typing import Any

windll: Any = None
if sys.platform == "win32":
    windll = ctypes.LibraryLoader(ctypes.WinDLL)
else:
    raise ImportError(f"{__name__} can only be imported on Windows")

import time
from ctypes import Structure, byref, wintypes
from typing import IO, NamedTuple, Type, cast

from pip._vendor.rich.color import ColorSystem
from pip._vendor.rich.style import Style

STDOUT = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

COORD = wintypes._COORD


class LegacyWindowsError(Exception):
    pass


class WindowsCoordinates(NamedTuple):
    """Coordinates in the Windows Console API are (y, x), not (x, y).
    This class is intended to prevent that confusion.
    Rows and columns are indexed from 0.
    This class can be used in place of wintypes._COORD in arguments and argtypes.
    """

    row: int
    col: int

    @classmethod
    def from_param(cls, value: "WindowsCoordinates") -> COORD:
        """Converts a WindowsCoordinates into a wintypes _COORD structure.
        This classmethod is internally called by ctypes to perform the conversion.

        Args:
            value (WindowsCoordinates): The input coordinates to convert.

        Returns:
            wintypes._COORD: The converted coordinates struct.
        """
        return COORD(value.col, value.row)


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", wintypes.WORD),
        ("srWindow", wintypes.SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class CONSOLE_CURSOR_INFO(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("bVisible", wintypes.BOOL)]


_GetStdHandle = windll.kernel32.GetStdHandle
_GetStdHandle.argtypes = [
    wintypes.DWORD,
]
_GetStdHandle.restype = wintypes.HANDLE


def GetStdHandle(handle: int = STDOUT) -> wintypes.HANDLE:
    """Retrieves a handle to the specified standard device (standard input, standard output, or standard error).

    Args:
        handle (int): Integer identifier for the handle. Defaults to -11 (stdout).

    Returns:
        wintypes.HANDLE: The handle
    """
    return cast(wintypes.HANDLE, _GetStdHandle(handle))


_GetConsoleMode = windll.kernel32.GetConsoleMode
_GetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
_GetConsoleMode.restype = wintypes.BOOL


def GetConsoleMode(std_handle: wintypes.HANDLE) -> int:
    """Retrieves the current input mode of a console's input buffer
    or the current output mode of a console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Raises:
        LegacyWindowsError: If any error occurs while calling the Windows console API.

    Returns:
        int: Value representing the current console mode as documented at
            https://docs.microsoft.com/en-us/windows/console/getconsolemode#parameters
    """

    console_mode = wintypes.DWORD()
    success = bool(_GetConsoleMode(std_handle, console_mode))
    if not success:
        raise LegacyWindowsError("Unable to get legacy Windows Console Mode")
    return console_mode.value


_FillConsoleOutputCharacterW = windll.kernel32.FillConsoleOutputCharacterW
_FillConsoleOutputCharacterW.argtypes = [
    wintypes.HANDLE,
    ctypes.c_char,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputCharacterW.restype = wintypes.BOOL


def FillConsoleOutputCharacter(
    std_handle: wintypes.HANDLE,
    char: str,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Writes a character to the console screen buffer a specified number of times, beginning at the specified coordinates.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        char (str): The character to write. Must be a string of length 1.
        length (int): The number of times to write the character.
        start (WindowsCoordinates): The coordinates to start writing at.

    Returns:
        int: The number of characters written.
    """
    character = ctypes.c_char(char.encode())
    num_characters = wintypes.DWORD(length)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputCharacterW(
        std_handle,
        character,
        num_characters,
        start,
        byref(num_written),
    )
    return num_written.value


_FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
_FillConsoleOutputAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
    wintypes.DWORD,
    cast(Type[COORD], WindowsCoordinates),
    ctypes.POINTER(wintypes.DWORD),
]
_FillConsoleOutputAttribute.restype = wintypes.BOOL


def FillConsoleOutputAttribute(
    std_handle: wintypes.HANDLE,
    attributes: int,
    length: int,
    start: WindowsCoordinates,
) -> int:
    """Sets the character attributes for a specified number of character cells,
    beginning at the specified coordinates in a screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours of the cells.
        length (int): The number of cells to set the output attribute of.
        start (WindowsCoordinates): The coordinates of the first cell whose attributes are to be set.

    Returns:
        int: The number of cells whose attributes were actually set.
    """
    num_cells = wintypes.DWORD(length)
    style_attrs = wintypes.WORD(attributes)
    num_written = wintypes.DWORD(0)
    _FillConsoleOutputAttribute(
        std_handle, style_attrs, num_cells, start, byref(num_written)
    )
    return num_written.value


_SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
_SetConsoleTextAttribute.argtypes = [
    wintypes.HANDLE,
    wintypes.WORD,
]
_SetConsoleTextAttribute.restype = wintypes.BOOL


def SetConsoleTextAttribute(
    std_handle: wintypes.HANDLE, attributes: wintypes.WORD
) -> bool:
    """Set the colour attributes for all text written after this function is called.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        attributes (int): Integer value representing the foreground and background colours.


    Returns:
        bool: True if the attribute was set successfully, otherwise False.
    """
    return bool(_SetConsoleTextAttribute(std_handle, attributes))


_GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
_GetConsoleScreenBufferInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
]
_GetConsoleScreenBufferInfo.restype = wintypes.BOOL


def GetConsoleScreenBufferInfo(
    std_handle: wintypes.HANDLE,
) -> CONSOLE_SCREEN_BUFFER_INFO:
    """Retrieves information about the specified console screen buffer.

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.

    Returns:
        CONSOLE_SCREEN_BUFFER_INFO: A CONSOLE_SCREEN_BUFFER_INFO ctype struct contain information about
            screen size, cursor position, colour attributes, and more."""
    console_screen_buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    _GetConsoleScreenBufferInfo(std_handle, byref(console_screen_buffer_info))
    return console_screen_buffer_info


_SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
_SetConsoleCursorPosition.argtypes = [
    wintypes.HANDLE,
    cast(Type[COORD], WindowsCoordinates),
]
_SetConsoleCursorPosition.restype = wintypes.BOOL


def SetConsoleCursorPosition(
    std_handle: wintypes.HANDLE, coords: WindowsCoordinates
) -> bool:
    """Set the position of the cursor in the console screen

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        coords (WindowsCoordinates): The coordinates to move the cursor to.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorPosition(std_handle, coords))


_GetConsoleCursorInfo = windll.kernel32.GetConsoleCursorInfo
_GetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_GetConsoleCursorInfo.restype = wintypes.BOOL


def GetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Get the cursor info - used to get cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct that receives information
            about the console's cursor.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_GetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleCursorInfo = windll.kernel32.SetConsoleCursorInfo
_SetConsoleCursorInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CONSOLE_CURSOR_INFO),
]
_SetConsoleCursorInfo.restype = wintypes.BOOL


def SetConsoleCursorInfo(
    std_handle: wintypes.HANDLE, cursor_info: CONSOLE_CURSOR_INFO
) -> bool:
    """Set the cursor info - used for adjusting cursor visibility and width

    Args:
        std_handle (wintypes.HANDLE): A handle to the console input buffer or the console screen buffer.
        cursor_info (CONSOLE_CURSOR_INFO): CONSOLE_CURSOR_INFO ctype struct containing the new cursor info.

    Returns:
          bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleCursorInfo(std_handle, byref(cursor_info)))


_SetConsoleTitle = windll.kernel32.SetConsoleTitleW
_SetConsoleTitle.argtypes = [wintypes.LPCWSTR]
_SetConsoleTitle.restype = wintypes.BOOL


def SetConsoleTitle(title: str) -> bool:
    """Sets the title of the current console window

    Args:
        title (str): The new title of the console window.

    Returns:
        bool: True if the function succeeds, otherwise False.
    """
    return bool(_SetConsoleTitle(title))


class LegacyWindowsTerm:
    """This class allows interaction with the legacy Windows Console API. It should only be used in the context
    of environments where virtual terminal processing is not available. However, if it is used in a Windows environment,
    the entire API should work.

    Args:
        file (IO[str]): The file which the Windows Console API HANDLE is retrieved from, defaults to sys.stdout.
    """

    BRIGHT_BIT = 8

    # Indices are ANSI color numbers, values are the corresponding Windows Console API color numbers
    ANSI_TO_WINDOWS = [
        0,  # black                      The Windows colours are defined in wincon.h as follows:
        4,  # red                         define FOREGROUND_BLUE            0x0001 -- 0000 0001
        2,  # green                       define FOREGROUND_GREEN           0x0002 -- 0000 0010
        6,  # yellow                      define FOREGROUND_RED             0x0004 -- 0000 0100
        1,  # blue                        define FOREGROUND_INTENSITY       0x0008 -- 0000 1000
        5,  # magenta                     define BACKGROUND_BLUE            0x0010 -- 0001 0000
        3,  # cyan                        define BACKGROUND_GREEN           0x0020 -- 0010 0000
        7,  # white                       define BACKGROUND_RED             0x0040 -- 0100 0000
        8,  # bright black (grey)         define BACKGROUND_INTENSITY       0x0080 -- 1000 0000
        12,  # bright red
        10,  # bright green
        14,  # bright yellow
        9,  # bright blue
        13,  # bright magenta
        11,  # bright cyan
        15,  # bright white
    ]

    def __init__(self, file: "IO[str]") -> None:
        handle = GetStdHandle(STDOUT)
        self._handle = handle
        default_text = GetConsoleScreenBufferInfo(handle).wAttributes
        self._default_text = default_text

        self._default_fore = default_text & 7
        self._default_back = (default_text >> 4) & 7
        self._default_attrs = self._default_fore | (self._default_back << 4)

        self._file = file
        self.write = file.write
        self.flush = file.flush

    @property
    def cursor_position(self) -> WindowsCoordinates:
        """Returns the current position of the cursor (0-based)

        Returns:
            WindowsCoordinates: The current cursor position.
        """
        coord: COORD = GetConsoleScreenBufferInfo(self._handle).dwCursorPosition
        return WindowsCoordinates(row=coord.Y, col=coord.X)

    @property
    def screen_size(self) -> WindowsCoordinates:
        """Returns the current size of the console screen buffer, in character columns and rows

        Returns:
            WindowsCoordinates: The width and height of the screen as WindowsCoordinates.
        """
        screen_size: COORD = GetConsoleScreenBufferInfo(self._handle).dwSize
        return WindowsCoordinates(row=screen_size.Y, col=screen_size.X)

    def write_text(self, text: str) -> None:
        """Write text directly to the terminal without any modification of styles

        Args:
            text (str): The text to write to the console
        """
        self.write(text)
        self.flush()

    def write_styled(self, text: str, style: Style) -> None:
        """Write styled text to the terminal.

        Args:
            text (str): The text to write
            style (Style): The style of the text
        """
        color = style.color
        bgcolor = style.bgcolor
        if style.reverse:
            color, bgcolor = bgcolor, color

        if color:
            fore = color.downgrade(ColorSystem.WINDOWS).number
            fore = fore if fore is not None else 7  # Default to ANSI 7: White
            if style.bold:
                fore = fore | self.BRIGHT_BIT
            if style.dim:
                fore = fore & ~self.BRIGHT_BIT
            fore = self.ANSI_TO_WINDOWS[fore]
        else:
            fore = self._default_fore

        if bgcolor:
            back = bgcolor.downgrade(ColorSystem.WINDOWS).number
            back = back if back is not None else 0  # Default to ANSI 0: Black
            back = self.ANSI_TO_WINDOWS[back]
        else:
            back = self._default_back

        assert fore is not None
        assert back is not None

        SetConsoleTextAttribute(
            self._handle, attributes=ctypes.c_ushort(fore | (back << 4))
        )
        self.write_text(text)
        SetConsoleTextAttribute(self._handle, attributes=self._default_text)

    def move_cursor_to(self, new_position: WindowsCoordinates) -> None:
        """Set the position of the cursor

        Args:
            new_position (WindowsCoordinates): The WindowsCoordinates representing the new position of the cursor.
        """
        if new_position.col < 0 or new_position.row < 0:
            return
        SetConsoleCursorPosition(self._handle, coords=new_position)

    def erase_line(self) -> None:
        """Erase all content on the line the cursor is currently located at"""
        screen_size = self.screen_size
        cursor_position = self.cursor_position
        cells_to_erase = screen_size.col
        start_coordinates = WindowsCoordinates(row=cursor_position.row, col=0)
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=start_coordinates
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=start_coordinates,
        )

    def erase_end_of_line(self) -> None:
        """Erase all content from the cursor position to the end of that line"""
        cursor_position = self.cursor_position
        cells_to_erase = self.screen_size.col - cursor_position.col
        FillConsoleOutputCharacter(
            self._handle, " ", length=cells_to_erase, start=cursor_position
        )
        FillConsoleOutputAttribute(
            self._handle,
            self._default_attrs,
            length=cells_to_erase,
            start=cursor_position,
        )

    def erase_start_of_line(self) -> None:
        """Erase all content from the cursor position to the start of that line"""
        row, col = self.cursor_position
        start = WindowsCoordinates(row, 0)
        FillConsoleOutputCharacter(self._handle, " ", length=col, start=start)
        FillConsoleOutputAttribute(
            self._handle, self._default_attrs, length=col, start=start
        )

    def move_cursor_up(self) -> None:
        """Move the cursor up a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row - 1, col=cursor_position.col
            ),
        )

    def move_cursor_down(self) -> None:
        """Move the cursor down a single cell"""
        cursor_position = self.cursor_position
        SetConsoleCursorPosition(
            self._handle,
            coords=WindowsCoordinates(
                row=cursor_position.row + 1,
                col=cursor_position.col,
            ),
        )

    def move_cursor_forward(self) -> None:
        """Move the cursor forward a single cell. Wrap to the next line if required."""
        row, col = self.cursor_position
        if col == self.screen_size.col - 1:
            row += 1
            col = 0
        else:
            col += 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def move_cursor_to_column(self, column: int) -> None:
        """Move cursor to the column specified by the zero-based column index, staying on the same row

        Args:
            column (int): The zero-based column index to move the cursor to.
        """
        row, _ = self.cursor_position
        SetConsoleCursorPosition(self._handle, coords=WindowsCoordinates(row, column))

    def move_cursor_backward(self) -> None:
        """Move the cursor backward a single cell. Wrap to the previous line if required."""
        row, col = self.cursor_position
        if col == 0:
            row -= 1
            col = self.screen_size.col - 1
        else:
            col -= 1
        SetConsoleCursorPosition(
            self._handle, coords=WindowsCoordinates(row=row, col=col)
        )

    def hide_cursor(self) -> None:
        """Hide the cursor"""
        current_cursor_size = self._get_cursor_size()
        invisible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=0)
        SetConsoleCursorInfo(self._handle, cursor_info=invisible_cursor)

    def show_cursor(self) -> None:
        """Show the cursor"""
        current_cursor_size = self._get_cursor_size()
        visible_cursor = CONSOLE_CURSOR_INFO(dwSize=current_cursor_size, bVisible=1)
        SetConsoleCursorInfo(self._handle, cursor_info=visible_cursor)

    def set_title(self, title: str) -> None:
        """Set the title of the terminal window

        Args:
            title (str): The new title of the console window
        """
        assert len(title) < 255, "Console title must be less than 255 characters"
        SetConsoleTitle(title)

    def _get_cursor_size(self) -> int:
        """Get the percentage of the character cell that is filled by the cursor"""
        cursor_info = CONSOLE_CURSOR_INFO()
        GetConsoleCursorInfo(self._handle, cursor_info=cursor_info)
        return int(cursor_info.dwSize)


if __name__ == "__main__":
    handle = GetStdHandle()

    from pip._vendor.rich.console import Console

    console = Console()

    term = LegacyWindowsTerm(sys.stdout)
    term.set_title("Win32 Console Examples")

    style = Style(color="black", bgcolor="red")

    heading = Style.parse("black on green")

    # Check colour output
    console.rule("Checking colour output")
    console.print("[on red]on red!")
    console.print("[blue]blue!")
    console.print("[yellow]yellow!")
    console.print("[bold yellow]bold yellow!")
    console.print("[bright_yellow]bright_yellow!")
    console.print("[dim bright_yellow]dim bright_yellow!")
    console.print("[italic cyan]italic cyan!")
    console.print("[bold white on blue]bold white on blue!")
    console.print("[reverse bold white on blue]reverse bold white on blue!")
    console.print("[bold black on cyan]bold black on cyan!")
    console.print("[black on green]black on green!")
    console.print("[blue on green]blue on green!")
    console.print("[white on black]white on black!")
    console.print("[black on white]black on white!")
    console.print("[#1BB152 on #DA812D]#1BB152 on #DA812D!")

    # Check cursor movement
    console.rule("Checking cursor movement")
    console.print()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("went back and wrapped to prev line")
    time.sleep(1)
    term.move_cursor_up()
    term.write_text("we go up")
    time.sleep(1)
    term.move_cursor_down()
    term.write_text("and down")
    time.sleep(1)
    term.move_cursor_up()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went up and back 2")
    time.sleep(1)
    term.move_cursor_down()
    term.move_cursor_backward()
    term.move_cursor_backward()
    term.write_text("we went down and back 2")
    time.sleep(1)

    # Check erasing of lines
    term.hide_cursor()
    console.print()
    console.rule("Checking line erasing")
    console.print("\n...Deleting to the start of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)
    term.move_cursor_to_column(16)
    term.write_styled("<", Style.parse("black on red"))
    term.move_cursor_backward()
    time.sleep(1)
    term.erase_start_of_line()
    time.sleep(1)

    console.print("\n\n...And to the end of the line...")
    term.write_text("The red arrow shows the cursor location, and direction of erase")
    time.sleep(1)

    term.move_cursor_to_column(16)
    term.write_styled(">", Style.parse("black on red"))
    time.sleep(1)
    term.erase_end_of_line()
    time.sleep(1)

    console.print("\n\n...Now the whole line will be erased...")
    term.write_styled("I'm going to disappear!", style=Style.parse("black on cyan"))
    time.sleep(1)
    term.erase_line()

    term.show_cursor()
    print("\n")

# === NexusCore/openenv\Lib\site-packages\pyperclip\__init__.py ===
"""
Pyperclip

A cross-platform clipboard module for Python, with copy & paste functions for plain text.
By Al Sweigart al@inventwithpython.com
BSD License

Usage:
  import pyperclip
  pyperclip.copy('The text to be copied to the clipboard.')
  spam = pyperclip.paste()

  if not pyperclip.is_available():
    print("Copy functionality unavailable!")

On Windows, no additional modules are needed.
On Mac, the pyobjc module is used, falling back to the pbcopy and pbpaste cli
    commands. (These commands should come with OS X.).
On Linux, install xclip, xsel, or wl-clipboard (for "wayland" sessions) via package manager.
For example, in Debian:
    sudo apt-get install xclip
    sudo apt-get install xsel
    sudo apt-get install wl-clipboard

Otherwise on Linux, you will need the qtpy or PyQt5 modules installed.

This module does not work with PyGObject yet.

Cygwin is currently not supported.

Security Note: This module runs programs with these names:
    - which
    - pbcopy
    - pbpaste
    - xclip
    - xsel
    - wl-copy/wl-paste
    - klipper
    - qdbus
A malicious user could rename or add programs with these names, tricking
Pyperclip into running them with whatever permissions the Python process has.

"""
__version__ = '1.9.0'

import base64
import contextlib
import ctypes
import os
import platform
import subprocess
import sys
import time
import warnings

from ctypes import c_size_t, sizeof, c_wchar_p, get_errno, c_wchar
from typing import Union, Optional


_IS_RUNNING_PYTHON_2 = sys.version_info[0] == 2  # type: bool

# For paste(): Python 3 uses str, Python 2 uses unicode.
if _IS_RUNNING_PYTHON_2:
    # mypy complains about `unicode` for Python 2, so we ignore the type error:
    _PYTHON_STR_TYPE = unicode  # type: ignore
else:
    _PYTHON_STR_TYPE = str

ENCODING = 'utf-8'  # type: str

try:
    # Use shutil.which() for Python 3+
    from shutil import which
    def _py3_executable_exists(name):  # type: (str) -> bool
        return bool(which(name))
    _executable_exists = _py3_executable_exists
except ImportError:
    # Use the "which" unix command for Python 2.7 and prior.
    def _py2_executable_exists(name):  # type: (str) -> bool
        return subprocess.call(['which', name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
    _executable_exists = _py2_executable_exists

# Exceptions
class PyperclipException(RuntimeError):
    pass

class PyperclipWindowsException(PyperclipException):
    def __init__(self, message):
        message += " (%s)" % ctypes.WinError()
        super(PyperclipWindowsException, self).__init__(message)

class PyperclipTimeoutException(PyperclipException):
    pass


def init_osx_pbcopy_clipboard():
    def copy_osx_pbcopy(text):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        p = subprocess.Popen(['pbcopy', 'w'],
                             stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=text.encode(ENCODING))

    def paste_osx_pbcopy():
        p = subprocess.Popen(['pbpaste', 'r'],
                             stdout=subprocess.PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        return stdout.decode(ENCODING)

    return copy_osx_pbcopy, paste_osx_pbcopy


def init_osx_pyobjc_clipboard():
    def copy_osx_pyobjc(text):
        '''Copy string argument to clipboard'''
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        newStr = Foundation.NSString.stringWithString_(text).nsstring()
        newData = newStr.dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
        board = AppKit.NSPasteboard.generalPasteboard()
        board.declareTypes_owner_([AppKit.NSStringPboardType], None)
        board.setData_forType_(newData, AppKit.NSStringPboardType)

    def paste_osx_pyobjc():
        "Returns contents of clipboard"
        board = AppKit.NSPasteboard.generalPasteboard()
        content = board.stringForType_(AppKit.NSStringPboardType)
        return content

    return copy_osx_pyobjc, paste_osx_pyobjc


def init_qt_clipboard():
    global QApplication
    # $DISPLAY should exist

    # Try to import from qtpy, but if that fails try PyQt5
    try:
        from qtpy.QtWidgets import QApplication
    except:
        from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    def copy_qt(text):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        cb = app.clipboard()
        cb.setText(text)

    def paste_qt():
        cb = app.clipboard()
        return _PYTHON_STR_TYPE(cb.text())

    return copy_qt, paste_qt


def init_xclip_clipboard():
    DEFAULT_SELECTION='c'
    PRIMARY_SELECTION='p'

    def copy_xclip(text, primary=False):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        selection=DEFAULT_SELECTION
        if primary:
            selection=PRIMARY_SELECTION
        p = subprocess.Popen(['xclip', '-selection', selection],
                             stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=text.encode(ENCODING))

    def paste_xclip(primary=False):
        selection=DEFAULT_SELECTION
        if primary:
            selection=PRIMARY_SELECTION
        p = subprocess.Popen(['xclip', '-selection', selection, '-o'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             close_fds=True)
        stdout, stderr = p.communicate()
        # Intentionally ignore extraneous output on stderr when clipboard is empty
        return stdout.decode(ENCODING)

    return copy_xclip, paste_xclip


def init_xsel_clipboard():
    DEFAULT_SELECTION='-b'
    PRIMARY_SELECTION='-p'

    def copy_xsel(text, primary=False):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        selection_flag = DEFAULT_SELECTION
        if primary:
            selection_flag = PRIMARY_SELECTION
        p = subprocess.Popen(['xsel', selection_flag, '-i'],
                             stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=text.encode(ENCODING))

    def paste_xsel(primary=False):
        selection_flag = DEFAULT_SELECTION
        if primary:
            selection_flag = PRIMARY_SELECTION
        p = subprocess.Popen(['xsel', selection_flag, '-o'],
                             stdout=subprocess.PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        return stdout.decode(ENCODING)

    return copy_xsel, paste_xsel


def init_wl_clipboard():
    PRIMARY_SELECTION = "-p"

    def copy_wl(text, primary=False):
        text = _PYTHON_STR_TYPE(text)  # Converts non-str values to str.
        args = ["wl-copy"]
        if primary:
            args.append(PRIMARY_SELECTION)
        if not text:
            args.append('--clear')
            subprocess.check_call(args, close_fds=True)
        else:
            pass
            p = subprocess.Popen(args, stdin=subprocess.PIPE, close_fds=True)
            p.communicate(input=text.encode(ENCODING))

    def paste_wl(primary=False):
        args = ["wl-paste", "-n", "-t", "text"]
        if primary:
            args.append(PRIMARY_SELECTION)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, close_fds=True)
        stdout, _stderr = p.communicate()
        return stdout.decode(ENCODING)

    return copy_wl, paste_wl


def init_klipper_clipboard():
    def copy_klipper(text):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        p = subprocess.Popen(
            ['qdbus', 'org.kde.klipper', '/klipper', 'setClipboardContents',
             text.encode(ENCODING)],
            stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=None)

    def paste_klipper():
        p = subprocess.Popen(
            ['qdbus', 'org.kde.klipper', '/klipper', 'getClipboardContents'],
            stdout=subprocess.PIPE, close_fds=True)
        stdout, stderr = p.communicate()

        # Workaround for https://bugs.kde.org/show_bug.cgi?id=342874
        # TODO: https://github.com/asweigart/pyperclip/issues/43
        clipboardContents = stdout.decode(ENCODING)
        # even if blank, Klipper will append a newline at the end
        assert len(clipboardContents) > 0
        # make sure that newline is there
        assert clipboardContents.endswith('\n')
        if clipboardContents.endswith('\n'):
            clipboardContents = clipboardContents[:-1]
        return clipboardContents

    return copy_klipper, paste_klipper


def init_dev_clipboard_clipboard():
    def copy_dev_clipboard(text):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        if text == '':
            warnings.warn('Pyperclip cannot copy a blank string to the clipboard on Cygwin. This is effectively a no-op.')
        if '\r' in text:
            warnings.warn('Pyperclip cannot handle \\r characters on Cygwin.')

        fo = open('/dev/clipboard', 'wt')
        fo.write(text)
        fo.close()

    def paste_dev_clipboard():
        fo = open('/dev/clipboard', 'rt')
        content = fo.read()
        fo.close()
        return content

    return copy_dev_clipboard, paste_dev_clipboard


def init_no_clipboard():
    class ClipboardUnavailable(object):

        def __call__(self, *args, **kwargs):
            additionalInfo = ''
            if sys.platform == 'linux':
                additionalInfo = '\nOn Linux, you can run `sudo apt-get install xclip` or `sudo apt-get install xselect` to install a copy/paste mechanism.'
            raise PyperclipException('Pyperclip could not find a copy/paste mechanism for your system. For more information, please visit https://pyperclip.readthedocs.io/en/latest/index.html#not-implemented-error' + additionalInfo)

        if _IS_RUNNING_PYTHON_2:
            def __nonzero__(self):
                return False
        else:
            def __bool__(self):
                return False

    return ClipboardUnavailable(), ClipboardUnavailable()




# Windows-related clipboard functions:
class CheckedCall(object):
    def __init__(self, f):
        super(CheckedCall, self).__setattr__("f", f)

    def __call__(self, *args):
        ret = self.f(*args)
        if not ret and get_errno():
            raise PyperclipWindowsException("Error calling " + self.f.__name__)
        return ret

    def __setattr__(self, key, value):
        setattr(self.f, key, value)


def init_windows_clipboard():
    global HGLOBAL, LPVOID, DWORD, LPCSTR, INT, HWND, HINSTANCE, HMENU, BOOL, UINT, HANDLE
    from ctypes.wintypes import (HGLOBAL, LPVOID, DWORD, LPCSTR, INT, HWND,
                                 HINSTANCE, HMENU, BOOL, UINT, HANDLE)

    windll = ctypes.windll
    msvcrt = ctypes.CDLL('msvcrt')

    safeCreateWindowExA = CheckedCall(windll.user32.CreateWindowExA)
    safeCreateWindowExA.argtypes = [DWORD, LPCSTR, LPCSTR, DWORD, INT, INT,
                                    INT, INT, HWND, HMENU, HINSTANCE, LPVOID]
    safeCreateWindowExA.restype = HWND

    safeDestroyWindow = CheckedCall(windll.user32.DestroyWindow)
    safeDestroyWindow.argtypes = [HWND]
    safeDestroyWindow.restype = BOOL

    OpenClipboard = windll.user32.OpenClipboard
    OpenClipboard.argtypes = [HWND]
    OpenClipboard.restype = BOOL

    safeCloseClipboard = CheckedCall(windll.user32.CloseClipboard)
    safeCloseClipboard.argtypes = []
    safeCloseClipboard.restype = BOOL

    safeEmptyClipboard = CheckedCall(windll.user32.EmptyClipboard)
    safeEmptyClipboard.argtypes = []
    safeEmptyClipboard.restype = BOOL

    safeGetClipboardData = CheckedCall(windll.user32.GetClipboardData)
    safeGetClipboardData.argtypes = [UINT]
    safeGetClipboardData.restype = HANDLE

    safeSetClipboardData = CheckedCall(windll.user32.SetClipboardData)
    safeSetClipboardData.argtypes = [UINT, HANDLE]
    safeSetClipboardData.restype = HANDLE

    safeGlobalAlloc = CheckedCall(windll.kernel32.GlobalAlloc)
    safeGlobalAlloc.argtypes = [UINT, c_size_t]
    safeGlobalAlloc.restype = HGLOBAL

    safeGlobalLock = CheckedCall(windll.kernel32.GlobalLock)
    safeGlobalLock.argtypes = [HGLOBAL]
    safeGlobalLock.restype = LPVOID

    safeGlobalUnlock = CheckedCall(windll.kernel32.GlobalUnlock)
    safeGlobalUnlock.argtypes = [HGLOBAL]
    safeGlobalUnlock.restype = BOOL

    wcslen = CheckedCall(msvcrt.wcslen)
    wcslen.argtypes = [c_wchar_p]
    wcslen.restype = UINT

    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    @contextlib.contextmanager
    def window():
        """
        Context that provides a valid Windows hwnd.
        """
        # we really just need the hwnd, so setting "STATIC"
        # as predefined lpClass is just fine.
        hwnd = safeCreateWindowExA(0, b"STATIC", None, 0, 0, 0, 0, 0,
                                   None, None, None, None)
        try:
            yield hwnd
        finally:
            safeDestroyWindow(hwnd)

    @contextlib.contextmanager
    def clipboard(hwnd):
        """
        Context manager that opens the clipboard and prevents
        other applications from modifying the clipboard content.
        """
        # We may not get the clipboard handle immediately because
        # some other application is accessing it (?)
        # We try for at least 500ms to get the clipboard.
        t = time.time() + 0.5
        success = False
        while time.time() < t:
            success = OpenClipboard(hwnd)
            if success:
                break
            time.sleep(0.01)
        if not success:
            raise PyperclipWindowsException("Error calling OpenClipboard")

        try:
            yield
        finally:
            safeCloseClipboard()

    def copy_windows(text):
        # This function is heavily based on
        # http://msdn.com/ms649016#_win32_Copying_Information_to_the_Clipboard

        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.

        with window() as hwnd:
            # http://msdn.com/ms649048
            # If an application calls OpenClipboard with hwnd set to NULL,
            # EmptyClipboard sets the clipboard owner to NULL;
            # this causes SetClipboardData to fail.
            # => We need a valid hwnd to copy something.
            with clipboard(hwnd):
                safeEmptyClipboard()

                if text:
                    # http://msdn.com/ms649051
                    # If the hMem parameter identifies a memory object,
                    # the object must have been allocated using the
                    # function with the GMEM_MOVEABLE flag.
                    count = wcslen(text) + 1
                    handle = safeGlobalAlloc(GMEM_MOVEABLE,
                                             count * sizeof(c_wchar))
                    locked_handle = safeGlobalLock(handle)

                    ctypes.memmove(c_wchar_p(locked_handle), c_wchar_p(text), count * sizeof(c_wchar))

                    safeGlobalUnlock(handle)
                    safeSetClipboardData(CF_UNICODETEXT, handle)

    def paste_windows():
        with clipboard(None):
            handle = safeGetClipboardData(CF_UNICODETEXT)
            if not handle:
                # GetClipboardData may return NULL with errno == NO_ERROR
                # if the clipboard is empty.
                # (Also, it may return a handle to an empty buffer,
                # but technically that's not empty)
                return ""
            locked_handle = safeGlobalLock(handle)
            return_value = c_wchar_p(locked_handle).value
            safeGlobalUnlock(handle)
            return return_value

    return copy_windows, paste_windows


def init_wsl_clipboard():

    def copy_wsl(text):
        text = _PYTHON_STR_TYPE(text) # Converts non-str values to str.
        p = subprocess.Popen(['clip.exe'],
                             stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=text.encode('utf-16le'))

    def paste_wsl():
        ps_script = '[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Clipboard -Raw)))'

        # '-noprofile' speeds up load time
        p = subprocess.Popen(['powershell.exe', '-noprofile', '-command', ps_script],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             close_fds=True)
        stdout, stderr = p.communicate()

        if stderr:
            raise Exception(f"Error pasting from clipboard: {stderr}")

        try:
            base64_encoded = stdout.decode('utf-8').strip()
            decoded_bytes = base64.b64decode(base64_encoded)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Decoding error: {e}")

    return copy_wsl, paste_wsl


# Automatic detection of clipboard mechanisms and importing is done in determine_clipboard():
def determine_clipboard():
    '''
    Determine the OS/platform and set the copy() and paste() functions
    accordingly.
    '''

    global Foundation, AppKit, qtpy, PyQt5

    # Setup for the CYGWIN platform:
    if 'cygwin' in platform.system().lower(): # Cygwin has a variety of values returned by platform.system(), such as 'CYGWIN_NT-6.1'
        # FIXME: pyperclip currently does not support Cygwin,
        # see https://github.com/asweigart/pyperclip/issues/55
        if os.path.exists('/dev/clipboard'):
            warnings.warn('Pyperclip\'s support for Cygwin is not perfect, see https://github.com/asweigart/pyperclip/issues/55')
            return init_dev_clipboard_clipboard()

    # Setup for the WINDOWS platform:
    elif os.name == 'nt' or platform.system() == 'Windows':
        return init_windows_clipboard()

    if platform.system() == 'Linux' and os.path.isfile('/proc/version'):
        with open('/proc/version', 'r') as f:
            if "microsoft" in f.read().lower():
                return init_wsl_clipboard()

    # Setup for the MAC OS X platform:
    if os.name == 'mac' or platform.system() == 'Darwin':
        try:
            import Foundation  # check if pyobjc is installed
            import AppKit
        except ImportError:
            return init_osx_pbcopy_clipboard()
        else:
            return init_osx_pyobjc_clipboard()

    # Setup for the LINUX platform:

    if os.getenv("WAYLAND_DISPLAY") and _executable_exists("wl-copy")  and _executable_exists("wl-paste"):
        return init_wl_clipboard()

    # `import PyQt4` sys.exit()s if DISPLAY is not in the environment.
    # Thus, we need to detect the presence of $DISPLAY manually
    # and not load PyQt4 if it is absent.
    elif os.getenv("DISPLAY"):
        if _executable_exists("xclip"):
            # Note: 2024/06/18 Google Trends shows xclip as more popular than xsel.
            return init_xclip_clipboard()
        if _executable_exists("xsel"):
            return init_xsel_clipboard()
        if _executable_exists("klipper") and _executable_exists("qdbus"):
            return init_klipper_clipboard()

        try:
            # qtpy is a small abstraction layer that lets you write
            # applications using a single api call to either PyQt or PySide.
            # https://pypi.python.org/pypi/QtPy
            import qtpy  # check if qtpy is installed
            return init_qt_clipboard()
        except ImportError:
            pass

        # If qtpy isn't installed, fall back on importing PyQt5
        try:
            import PyQt5  # check if PyQt5 is installed
            return init_qt_clipboard()
        except ImportError:
            pass

    return init_no_clipboard()


def set_clipboard(clipboard):
    '''
    Explicitly sets the clipboard mechanism. The "clipboard mechanism" is how
    the copy() and paste() functions interact with the operating system to
    implement the copy/paste feature. The clipboard parameter must be one of:
        - pbcopy
        - pbobjc (default on Mac OS X)
        - qt
        - xclip
        - xsel
        - klipper
        - windows (default on Windows)
        - no (this is what is set when no clipboard mechanism can be found)
    '''
    global copy, paste

    clipboard_types = {
        "pbcopy": init_osx_pbcopy_clipboard,
        "pyobjc": init_osx_pyobjc_clipboard,
        "qt": init_qt_clipboard,  # TODO - split this into 'qtpy' and 'pyqt5'
        "xclip": init_xclip_clipboard,
        "xsel": init_xsel_clipboard,
        "wl-clipboard": init_wl_clipboard,
        "klipper": init_klipper_clipboard,
        "windows": init_windows_clipboard,
        "no": init_no_clipboard,
    }

    if clipboard not in clipboard_types:
        raise ValueError('Argument must be one of %s' % (', '.join([repr(_) for _ in clipboard_types.keys()])))

    # Sets pyperclip's copy() and paste() functions:
    copy, paste = clipboard_types[clipboard]()


def lazy_load_stub_copy(text):
    '''
    A stub function for copy(), which will load the real copy() function when
    called so that the real copy() function is used for later calls.

    This allows users to import pyperclip without having determine_clipboard()
    automatically run, which will automatically select a clipboard mechanism.
    This could be a problem if it selects, say, the memory-heavy PyQt5 module
    but the user was just going to immediately call set_clipboard() to use a
    different clipboard mechanism.

    The lazy loading this stub function implements gives the user a chance to
    call set_clipboard() to pick another clipboard mechanism. Or, if the user
    simply calls copy() or paste() without calling set_clipboard() first,
    will fall back on whatever clipboard mechanism that determine_clipboard()
    automatically chooses.
    '''
    global copy, paste
    copy, paste = determine_clipboard()
    return copy(text)


def lazy_load_stub_paste():
    '''
    A stub function for paste(), which will load the real paste() function when
    called so that the real paste() function is used for later calls.

    This allows users to import pyperclip without having determine_clipboard()
    automatically run, which will automatically select a clipboard mechanism.
    This could be a problem if it selects, say, the memory-heavy PyQt5 module
    but the user was just going to immediately call set_clipboard() to use a
    different clipboard mechanism.

    The lazy loading this stub function implements gives the user a chance to
    call set_clipboard() to pick another clipboard mechanism. Or, if the user
    simply calls copy() or paste() without calling set_clipboard() first,
    will fall back on whatever clipboard mechanism that determine_clipboard()
    automatically chooses.
    '''
    global copy, paste
    copy, paste = determine_clipboard()
    return paste()


def is_available():
    return copy != lazy_load_stub_copy and paste != lazy_load_stub_paste


# Initially, copy() and paste() are set to lazy loading wrappers which will
# set `copy` and `paste` to real functions the first time they're used, unless
# set_clipboard() or determine_clipboard() is called first.
copy, paste = lazy_load_stub_copy, lazy_load_stub_paste



__all__ = ['copy', 'paste', 'set_clipboard', 'determine_clipboard']



# === NexusCore/openenv\Lib\site-packages\h11\_connection.py ===
# This contains the main Connection class. Everything in h11 revolves around
# this.
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    overload,
    Tuple,
    Type,
    Union,
)

from ._events import (
    ConnectionClosed,
    Data,
    EndOfMessage,
    Event,
    InformationalResponse,
    Request,
    Response,
)
from ._headers import get_comma_header, has_expect_100_continue, set_comma_header
from ._readers import READERS, ReadersType
from ._receivebuffer import ReceiveBuffer
from ._state import (
    _SWITCH_CONNECT,
    _SWITCH_UPGRADE,
    CLIENT,
    ConnectionState,
    DONE,
    ERROR,
    MIGHT_SWITCH_PROTOCOL,
    SEND_BODY,
    SERVER,
    SWITCHED_PROTOCOL,
)
from ._util import (  # Import the internal things we need
    LocalProtocolError,
    RemoteProtocolError,
    Sentinel,
)
from ._writers import WRITERS, WritersType

# Everything in __all__ gets re-exported as part of the h11 public API.
__all__ = ["Connection", "NEED_DATA", "PAUSED"]


class NEED_DATA(Sentinel, metaclass=Sentinel):
    pass


class PAUSED(Sentinel, metaclass=Sentinel):
    pass


# If we ever have this much buffered without it making a complete parseable
# event, we error out. The only time we really buffer is when reading the
# request/response line + headers together, so this is effectively the limit on
# the size of that.
#
# Some precedents for defaults:
# - node.js: 80 * 1024
# - tomcat: 8 * 1024
# - IIS: 16 * 1024
# - Apache: <8 KiB per line>
DEFAULT_MAX_INCOMPLETE_EVENT_SIZE = 16 * 1024


# RFC 7230's rules for connection lifecycles:
# - If either side says they want to close the connection, then the connection
#   must close.
# - HTTP/1.1 defaults to keep-alive unless someone says Connection: close
# - HTTP/1.0 defaults to close unless both sides say Connection: keep-alive
#   (and even this is a mess -- e.g. if you're implementing a proxy then
#   sending Connection: keep-alive is forbidden).
#
# We simplify life by simply not supporting keep-alive with HTTP/1.0 peers. So
# our rule is:
# - If someone says Connection: close, we will close
# - If someone uses HTTP/1.0, we will close.
def _keep_alive(event: Union[Request, Response]) -> bool:
    connection = get_comma_header(event.headers, b"connection")
    if b"close" in connection:
        return False
    if getattr(event, "http_version", b"1.1") < b"1.1":
        return False
    return True


def _body_framing(
    request_method: bytes, event: Union[Request, Response]
) -> Tuple[str, Union[Tuple[()], Tuple[int]]]:
    # Called when we enter SEND_BODY to figure out framing information for
    # this body.
    #
    # These are the only two events that can trigger a SEND_BODY state:
    assert type(event) in (Request, Response)
    # Returns one of:
    #
    #    ("content-length", count)
    #    ("chunked", ())
    #    ("http/1.0", ())
    #
    # which are (lookup key, *args) for constructing body reader/writer
    # objects.
    #
    # Reference: https://tools.ietf.org/html/rfc7230#section-3.3.3
    #
    # Step 1: some responses always have an empty body, regardless of what the
    # headers say.
    if type(event) is Response:
        if (
            event.status_code in (204, 304)
            or request_method == b"HEAD"
            or (request_method == b"CONNECT" and 200 <= event.status_code < 300)
        ):
            return ("content-length", (0,))
        # Section 3.3.3 also lists another case -- responses with status_code
        # < 200. For us these are InformationalResponses, not Responses, so
        # they can't get into this function in the first place.
        assert event.status_code >= 200

    # Step 2: check for Transfer-Encoding (T-E beats C-L):
    transfer_encodings = get_comma_header(event.headers, b"transfer-encoding")
    if transfer_encodings:
        assert transfer_encodings == [b"chunked"]
        return ("chunked", ())

    # Step 3: check for Content-Length
    content_lengths = get_comma_header(event.headers, b"content-length")
    if content_lengths:
        return ("content-length", (int(content_lengths[0]),))

    # Step 4: no applicable headers; fallback/default depends on type
    if type(event) is Request:
        return ("content-length", (0,))
    else:
        return ("http/1.0", ())


################################################################
#
# The main Connection class
#
################################################################


class Connection:
    """An object encapsulating the state of an HTTP connection.

    Args:
        our_role: If you're implementing a client, pass :data:`h11.CLIENT`. If
            you're implementing a server, pass :data:`h11.SERVER`.

        max_incomplete_event_size (int):
            The maximum number of bytes we're willing to buffer of an
            incomplete event. In practice this mostly sets a limit on the
            maximum size of the request/response line + headers. If this is
            exceeded, then :meth:`next_event` will raise
            :exc:`RemoteProtocolError`.

    """

    def __init__(
        self,
        our_role: Type[Sentinel],
        max_incomplete_event_size: int = DEFAULT_MAX_INCOMPLETE_EVENT_SIZE,
    ) -> None:
        self._max_incomplete_event_size = max_incomplete_event_size
        # State and role tracking
        if our_role not in (CLIENT, SERVER):
            raise ValueError(f"expected CLIENT or SERVER, not {our_role!r}")
        self.our_role = our_role
        self.their_role: Type[Sentinel]
        if our_role is CLIENT:
            self.their_role = SERVER
        else:
            self.their_role = CLIENT
        self._cstate = ConnectionState()

        # Callables for converting data->events or vice-versa given the
        # current state
        self._writer = self._get_io_object(self.our_role, None, WRITERS)
        self._reader = self._get_io_object(self.their_role, None, READERS)

        # Holds any unprocessed received data
        self._receive_buffer = ReceiveBuffer()
        # If this is true, then it indicates that the incoming connection was
        # closed *after* the end of whatever's in self._receive_buffer:
        self._receive_buffer_closed = False

        # Extra bits of state that don't fit into the state machine.
        #
        # These two are only used to interpret framing headers for figuring
        # out how to read/write response bodies. their_http_version is also
        # made available as a convenient public API.
        self.their_http_version: Optional[bytes] = None
        self._request_method: Optional[bytes] = None
        # This is pure flow-control and doesn't at all affect the set of legal
        # transitions, so no need to bother ConnectionState with it:
        self.client_is_waiting_for_100_continue = False

    @property
    def states(self) -> Dict[Type[Sentinel], Type[Sentinel]]:
        """A dictionary like::

           {CLIENT: <client state>, SERVER: <server state>}

        See :ref:`state-machine` for details.

        """
        return dict(self._cstate.states)

    @property
    def our_state(self) -> Type[Sentinel]:
        """The current state of whichever role we are playing. See
        :ref:`state-machine` for details.
        """
        return self._cstate.states[self.our_role]

    @property
    def their_state(self) -> Type[Sentinel]:
        """The current state of whichever role we are NOT playing. See
        :ref:`state-machine` for details.
        """
        return self._cstate.states[self.their_role]

    @property
    def they_are_waiting_for_100_continue(self) -> bool:
        return self.their_role is CLIENT and self.client_is_waiting_for_100_continue

    def start_next_cycle(self) -> None:
        """Attempt to reset our connection state for a new request/response
        cycle.

        If both client and server are in :data:`DONE` state, then resets them
        both to :data:`IDLE` state in preparation for a new request/response
        cycle on this same connection. Otherwise, raises a
        :exc:`LocalProtocolError`.

        See :ref:`keepalive-and-pipelining`.

        """
        old_states = dict(self._cstate.states)
        self._cstate.start_next_cycle()
        self._request_method = None
        # self.their_http_version gets left alone, since it presumably lasts
        # beyond a single request/response cycle
        assert not self.client_is_waiting_for_100_continue
        self._respond_to_state_changes(old_states)

    def _process_error(self, role: Type[Sentinel]) -> None:
        old_states = dict(self._cstate.states)
        self._cstate.process_error(role)
        self._respond_to_state_changes(old_states)

    def _server_switch_event(self, event: Event) -> Optional[Type[Sentinel]]:
        if type(event) is InformationalResponse and event.status_code == 101:
            return _SWITCH_UPGRADE
        if type(event) is Response:
            if (
                _SWITCH_CONNECT in self._cstate.pending_switch_proposals
                and 200 <= event.status_code < 300
            ):
                return _SWITCH_CONNECT
        return None

    # All events go through here
    def _process_event(self, role: Type[Sentinel], event: Event) -> None:
        # First, pass the event through the state machine to make sure it
        # succeeds.
        old_states = dict(self._cstate.states)
        if role is CLIENT and type(event) is Request:
            if event.method == b"CONNECT":
                self._cstate.process_client_switch_proposal(_SWITCH_CONNECT)
            if get_comma_header(event.headers, b"upgrade"):
                self._cstate.process_client_switch_proposal(_SWITCH_UPGRADE)
        server_switch_event = None
        if role is SERVER:
            server_switch_event = self._server_switch_event(event)
        self._cstate.process_event(role, type(event), server_switch_event)

        # Then perform the updates triggered by it.

        if type(event) is Request:
            self._request_method = event.method

        if role is self.their_role and type(event) in (
            Request,
            Response,
            InformationalResponse,
        ):
            event = cast(Union[Request, Response, InformationalResponse], event)
            self.their_http_version = event.http_version

        # Keep alive handling
        #
        # RFC 7230 doesn't really say what one should do if Connection: close
        # shows up on a 1xx InformationalResponse. I think the idea is that
        # this is not supposed to happen. In any case, if it does happen, we
        # ignore it.
        if type(event) in (Request, Response) and not _keep_alive(
            cast(Union[Request, Response], event)
        ):
            self._cstate.process_keep_alive_disabled()

        # 100-continue
        if type(event) is Request and has_expect_100_continue(event):
            self.client_is_waiting_for_100_continue = True
        if type(event) in (InformationalResponse, Response):
            self.client_is_waiting_for_100_continue = False
        if role is CLIENT and type(event) in (Data, EndOfMessage):
            self.client_is_waiting_for_100_continue = False

        self._respond_to_state_changes(old_states, event)

    def _get_io_object(
        self,
        role: Type[Sentinel],
        event: Optional[Event],
        io_dict: Union[ReadersType, WritersType],
    ) -> Optional[Callable[..., Any]]:
        # event may be None; it's only used when entering SEND_BODY
        state = self._cstate.states[role]
        if state is SEND_BODY:
            # Special case: the io_dict has a dict of reader/writer factories
            # that depend on the request/response framing.
            framing_type, args = _body_framing(
                cast(bytes, self._request_method), cast(Union[Request, Response], event)
            )
            return io_dict[SEND_BODY][framing_type](*args)  # type: ignore[index]
        else:
            # General case: the io_dict just has the appropriate reader/writer
            # for this state
            return io_dict.get((role, state))  # type: ignore[return-value]

    # This must be called after any action that might have caused
    # self._cstate.states to change.
    def _respond_to_state_changes(
        self,
        old_states: Dict[Type[Sentinel], Type[Sentinel]],
        event: Optional[Event] = None,
    ) -> None:
        # Update reader/writer
        if self.our_state != old_states[self.our_role]:
            self._writer = self._get_io_object(self.our_role, event, WRITERS)
        if self.their_state != old_states[self.their_role]:
            self._reader = self._get_io_object(self.their_role, event, READERS)

    @property
    def trailing_data(self) -> Tuple[bytes, bool]:
        """Data that has been received, but not yet processed, represented as
        a tuple with two elements, where the first is a byte-string containing
        the unprocessed data itself, and the second is a bool that is True if
        the receive connection was closed.

        See :ref:`switching-protocols` for discussion of why you'd want this.
        """
        return (bytes(self._receive_buffer), self._receive_buffer_closed)

    def receive_data(self, data: bytes) -> None:
        """Add data to our internal receive buffer.

        This does not actually do any processing on the data, just stores
        it. To trigger processing, you have to call :meth:`next_event`.

        Args:
            data (:term:`bytes-like object`):
                The new data that was just received.

                Special case: If *data* is an empty byte-string like ``b""``,
                then this indicates that the remote side has closed the
                connection (end of file). Normally this is convenient, because
                standard Python APIs like :meth:`file.read` or
                :meth:`socket.recv` use ``b""`` to indicate end-of-file, while
                other failures to read are indicated using other mechanisms
                like raising :exc:`TimeoutError`. When using such an API you
                can just blindly pass through whatever you get from ``read``
                to :meth:`receive_data`, and everything will work.

                But, if you have an API where reading an empty string is a
                valid non-EOF condition, then you need to be aware of this and
                make sure to check for such strings and avoid passing them to
                :meth:`receive_data`.

        Returns:
            Nothing, but after calling this you should call :meth:`next_event`
            to parse the newly received data.

        Raises:
            RuntimeError:
                Raised if you pass an empty *data*, indicating EOF, and then
                pass a non-empty *data*, indicating more data that somehow
                arrived after the EOF.

                (Calling ``receive_data(b"")`` multiple times is fine,
                and equivalent to calling it once.)

        """
        if data:
            if self._receive_buffer_closed:
                raise RuntimeError("received close, then received more data?")
            self._receive_buffer += data
        else:
            self._receive_buffer_closed = True

    def _extract_next_receive_event(
        self,
    ) -> Union[Event, Type[NEED_DATA], Type[PAUSED]]:
        state = self.their_state
        # We don't pause immediately when they enter DONE, because even in
        # DONE state we can still process a ConnectionClosed() event. But
        # if we have data in our buffer, then we definitely aren't getting
        # a ConnectionClosed() immediately and we need to pause.
        if state is DONE and self._receive_buffer:
            return PAUSED
        if state is MIGHT_SWITCH_PROTOCOL or state is SWITCHED_PROTOCOL:
            return PAUSED
        assert self._reader is not None
        event = self._reader(self._receive_buffer)
        if event is None:
            if not self._receive_buffer and self._receive_buffer_closed:
                # In some unusual cases (basically just HTTP/1.0 bodies), EOF
                # triggers an actual protocol event; in that case, we want to
                # return that event, and then the state will change and we'll
                # get called again to generate the actual ConnectionClosed().
                if hasattr(self._reader, "read_eof"):
                    event = self._reader.read_eof()
                else:
                    event = ConnectionClosed()
        if event is None:
            event = NEED_DATA
        return event  # type: ignore[no-any-return]

    def next_event(self) -> Union[Event, Type[NEED_DATA], Type[PAUSED]]:
        """Parse the next event out of our receive buffer, update our internal
        state, and return it.

        This is a mutating operation -- think of it like calling :func:`next`
        on an iterator.

        Returns:
            : One of three things:

            1) An event object -- see :ref:`events`.

            2) The special constant :data:`NEED_DATA`, which indicates that
               you need to read more data from your socket and pass it to
               :meth:`receive_data` before this method will be able to return
               any more events.

            3) The special constant :data:`PAUSED`, which indicates that we
               are not in a state where we can process incoming data (usually
               because the peer has finished their part of the current
               request/response cycle, and you have not yet called
               :meth:`start_next_cycle`). See :ref:`flow-control` for details.

        Raises:
            RemoteProtocolError:
                The peer has misbehaved. You should close the connection
                (possibly after sending some kind of 4xx response).

        Once this method returns :class:`ConnectionClosed` once, then all
        subsequent calls will also return :class:`ConnectionClosed`.

        If this method raises any exception besides :exc:`RemoteProtocolError`
        then that's a bug -- if it happens please file a bug report!

        If this method raises any exception then it also sets
        :attr:`Connection.their_state` to :data:`ERROR` -- see
        :ref:`error-handling` for discussion.

        """

        if self.their_state is ERROR:
            raise RemoteProtocolError("Can't receive data when peer state is ERROR")
        try:
            event = self._extract_next_receive_event()
            if event not in [NEED_DATA, PAUSED]:
                self._process_event(self.their_role, cast(Event, event))
            if event is NEED_DATA:
                if len(self._receive_buffer) > self._max_incomplete_event_size:
                    # 431 is "Request header fields too large" which is pretty
                    # much the only situation where we can get here
                    raise RemoteProtocolError(
                        "Receive buffer too long", error_status_hint=431
                    )
                if self._receive_buffer_closed:
                    # We're still trying to complete some event, but that's
                    # never going to happen because no more data is coming
                    raise RemoteProtocolError("peer unexpectedly closed connection")
            return event
        except BaseException as exc:
            self._process_error(self.their_role)
            if isinstance(exc, LocalProtocolError):
                exc._reraise_as_remote_protocol_error()
            else:
                raise

    @overload
    def send(self, event: ConnectionClosed) -> None:
        ...

    @overload
    def send(
        self, event: Union[Request, InformationalResponse, Response, Data, EndOfMessage]
    ) -> bytes:
        ...

    @overload
    def send(self, event: Event) -> Optional[bytes]:
        ...

    def send(self, event: Event) -> Optional[bytes]:
        """Convert a high-level event into bytes that can be sent to the peer,
        while updating our internal state machine.

        Args:
            event: The :ref:`event <events>` to send.

        Returns:
            If ``type(event) is ConnectionClosed``, then returns
            ``None``. Otherwise, returns a :term:`bytes-like object`.

        Raises:
            LocalProtocolError:
                Sending this event at this time would violate our
                understanding of the HTTP/1.1 protocol.

        If this method raises any exception then it also sets
        :attr:`Connection.our_state` to :data:`ERROR` -- see
        :ref:`error-handling` for discussion.

        """
        data_list = self.send_with_data_passthrough(event)
        if data_list is None:
            return None
        else:
            return b"".join(data_list)

    def send_with_data_passthrough(self, event: Event) -> Optional[List[bytes]]:
        """Identical to :meth:`send`, except that in situations where
        :meth:`send` returns a single :term:`bytes-like object`, this instead
        returns a list of them -- and when sending a :class:`Data` event, this
        list is guaranteed to contain the exact object you passed in as
        :attr:`Data.data`. See :ref:`sendfile` for discussion.

        """
        if self.our_state is ERROR:
            raise LocalProtocolError("Can't send data when our state is ERROR")
        try:
            if type(event) is Response:
                event = self._clean_up_response_headers_for_sending(event)
            # We want to call _process_event before calling the writer,
            # because if someone tries to do something invalid then this will
            # give a sensible error message, while our writers all just assume
            # they will only receive valid events. But, _process_event might
            # change self._writer. So we have to do a little dance:
            writer = self._writer
            self._process_event(self.our_role, event)
            if type(event) is ConnectionClosed:
                return None
            else:
                # In any situation where writer is None, process_event should
                # have raised ProtocolError
                assert writer is not None
                data_list: List[bytes] = []
                writer(event, data_list.append)
                return data_list
        except:
            self._process_error(self.our_role)
            raise

    def send_failed(self) -> None:
        """Notify the state machine that we failed to send the data it gave
        us.

        This causes :attr:`Connection.our_state` to immediately become
        :data:`ERROR` -- see :ref:`error-handling` for discussion.

        """
        self._process_error(self.our_role)

    # When sending a Response, we take responsibility for a few things:
    #
    # - Sometimes you MUST set Connection: close. We take care of those
    #   times. (You can also set it yourself if you want, and if you do then
    #   we'll respect that and close the connection at the right time. But you
    #   don't have to worry about that unless you want to.)
    #
    # - The user has to set Content-Length if they want it. Otherwise, for
    #   responses that have bodies (e.g. not HEAD), then we will automatically
    #   select the right mechanism for streaming a body of unknown length,
    #   which depends on depending on the peer's HTTP version.
    #
    # This function's *only* responsibility is making sure headers are set up
    # right -- everything downstream just looks at the headers. There are no
    # side channels.
    def _clean_up_response_headers_for_sending(self, response: Response) -> Response:
        assert type(response) is Response

        headers = response.headers
        need_close = False

        # HEAD requests need some special handling: they always act like they
        # have Content-Length: 0, and that's how _body_framing treats
        # them. But their headers are supposed to match what we would send if
        # the request was a GET. (Technically there is one deviation allowed:
        # we're allowed to leave out the framing headers -- see
        # https://tools.ietf.org/html/rfc7231#section-4.3.2 . But it's just as
        # easy to get them right.)
        method_for_choosing_headers = cast(bytes, self._request_method)
        if method_for_choosing_headers == b"HEAD":
            method_for_choosing_headers = b"GET"
        framing_type, _ = _body_framing(method_for_choosing_headers, response)
        if framing_type in ("chunked", "http/1.0"):
            # This response has a body of unknown length.
            # If our peer is HTTP/1.1, we use Transfer-Encoding: chunked
            # If our peer is HTTP/1.0, we use no framing headers, and close the
            # connection afterwards.
            #
            # Make sure to clear Content-Length (in principle user could have
            # set both and then we ignored Content-Length b/c
            # Transfer-Encoding overwrote it -- this would be naughty of them,
            # but the HTTP spec says that if our peer does this then we have
            # to fix it instead of erroring out, so we'll accord the user the
            # same respect).
            headers = set_comma_header(headers, b"content-length", [])
            if self.their_http_version is None or self.their_http_version < b"1.1":
                # Either we never got a valid request and are sending back an
                # error (their_http_version is None), so we assume the worst;
                # or else we did get a valid HTTP/1.0 request, so we know that
                # they don't understand chunked encoding.
                headers = set_comma_header(headers, b"transfer-encoding", [])
                # This is actually redundant ATM, since currently we
                # unconditionally disable keep-alive when talking to HTTP/1.0
                # peers. But let's be defensive just in case we add
                # Connection: keep-alive support later:
                if self._request_method != b"HEAD":
                    need_close = True
            else:
                headers = set_comma_header(headers, b"transfer-encoding", [b"chunked"])

        if not self._cstate.keep_alive or need_close:
            # Make sure Connection: close is set
            connection = set(get_comma_header(headers, b"connection"))
            connection.discard(b"keep-alive")
            connection.add(b"close")
            headers = set_comma_header(headers, b"connection", sorted(connection))

        return Response(
            headers=headers,
            status_code=response.status_code,
            http_version=response.http_version,
            reason=response.reason,
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\bytecode\concrete.py ===
import dis
import inspect
import opcode as _opcode
import struct
import sys
import types

# alias to keep the 'bytecode' variable free
from _pydevd_frame_eval.vendored import bytecode as _bytecode
from _pydevd_frame_eval.vendored.bytecode.instr import (
    UNSET,
    Instr,
    Label,
    SetLineno,
    FreeVar,
    CellVar,
    Compare,
    const_key,
    _check_arg_int,
)

# - jumps use instruction
# - lineno use bytes (dis.findlinestarts(code))
# - dis displays bytes
OFFSET_AS_INSTRUCTION = sys.version_info >= (3, 10)


def _set_docstring(code, consts):
    if not consts:
        return
    first_const = consts[0]
    if isinstance(first_const, str) or first_const is None:
        code.docstring = first_const


class ConcreteInstr(Instr):
    """Concrete instruction.

    arg must be an integer in the range 0..2147483647.

    It has a read-only size attribute.
    """

    __slots__ = ("_size", "_extended_args", "offset")

    def __init__(self, name, arg=UNSET, *, lineno=None, extended_args=None, offset=None):
        # Allow to remember a potentially meaningless EXTENDED_ARG emitted by
        # Python to properly compute the size and avoid messing up the jump
        # targets
        self._extended_args = extended_args
        self._set(name, arg, lineno)
        self.offset = offset

    def _check_arg(self, name, opcode, arg):
        if opcode >= _opcode.HAVE_ARGUMENT:
            if arg is UNSET:
                raise ValueError("operation %s requires an argument" % name)

            _check_arg_int(name, arg)
        else:
            if arg is not UNSET:
                raise ValueError("operation %s has no argument" % name)

    def _set(self, name, arg, lineno):
        super()._set(name, arg, lineno)
        size = 2
        if arg is not UNSET:
            while arg > 0xFF:
                size += 2
                arg >>= 8
        if self._extended_args is not None:
            size = 2 + 2 * self._extended_args
        self._size = size

    @property
    def size(self):
        return self._size

    def _cmp_key(self, labels=None):
        return (self._lineno, self._name, self._arg)

    def get_jump_target(self, instr_offset):
        if self._opcode in _opcode.hasjrel:
            s = (self._size // 2) if OFFSET_AS_INSTRUCTION else self._size
            return instr_offset + s + self._arg
        if self._opcode in _opcode.hasjabs:
            return self._arg
        return None

    def assemble(self):
        if self._arg is UNSET:
            return bytes((self._opcode, 0))

        arg = self._arg
        b = [self._opcode, arg & 0xFF]
        while arg > 0xFF:
            arg >>= 8
            b[:0] = [_opcode.EXTENDED_ARG, arg & 0xFF]

        if self._extended_args:
            while len(b) < self._size:
                b[:0] = [_opcode.EXTENDED_ARG, 0x00]

        return bytes(b)

    @classmethod
    def disassemble(cls, lineno, code, offset):
        index = 2 * offset if OFFSET_AS_INSTRUCTION else offset
        op = code[index]
        if op >= _opcode.HAVE_ARGUMENT:
            arg = code[index + 1]
        else:
            arg = UNSET
        name = _opcode.opname[op]
        # fabioz: added offset to ConcreteBytecode
        # Need to keep an eye on https://github.com/MatthieuDartiailh/bytecode/issues/48 in
        # case the library decides to add this in some other way.
        return cls(name, arg, lineno=lineno, offset=index)


class ConcreteBytecode(_bytecode._BaseBytecodeList):
    def __init__(self, instructions=(), *, consts=(), names=(), varnames=()):
        super().__init__()
        self.consts = list(consts)
        self.names = list(names)
        self.varnames = list(varnames)
        for instr in instructions:
            self._check_instr(instr)
        self.extend(instructions)

    def __iter__(self):
        instructions = super().__iter__()
        for instr in instructions:
            self._check_instr(instr)
            yield instr

    def _check_instr(self, instr):
        if not isinstance(instr, (ConcreteInstr, SetLineno)):
            raise ValueError(
                "ConcreteBytecode must only contain " "ConcreteInstr and SetLineno objects, " "but %s was found" % type(instr).__name__
            )

    def _copy_attr_from(self, bytecode):
        super()._copy_attr_from(bytecode)
        if isinstance(bytecode, ConcreteBytecode):
            self.consts = bytecode.consts
            self.names = bytecode.names
            self.varnames = bytecode.varnames

    def __repr__(self):
        return "<ConcreteBytecode instr#=%s>" % len(self)

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        const_keys1 = list(map(const_key, self.consts))
        const_keys2 = list(map(const_key, other.consts))
        if const_keys1 != const_keys2:
            return False

        if self.names != other.names:
            return False
        if self.varnames != other.varnames:
            return False

        return super().__eq__(other)

    @staticmethod
    def from_code(code, *, extended_arg=False):
        line_starts = dict(entry for entry in dis.findlinestarts(code) if entry[1] is not None)

        # find block starts
        instructions = []
        offset = 0
        lineno = code.co_firstlineno
        while offset < (len(code.co_code) // (2 if OFFSET_AS_INSTRUCTION else 1)):
            lineno_off = (2 * offset) if OFFSET_AS_INSTRUCTION else offset
            if lineno_off in line_starts:
                lineno = line_starts[lineno_off]

            instr = ConcreteInstr.disassemble(lineno, code.co_code, offset)

            instructions.append(instr)
            offset += (instr.size // 2) if OFFSET_AS_INSTRUCTION else instr.size

        bytecode = ConcreteBytecode()

        # replace jump targets with blocks
        # HINT : in some cases Python generate useless EXTENDED_ARG opcode
        # with a value of zero. Such opcodes do not increases the size of the
        # following opcode the way a normal EXTENDED_ARG does. As a
        # consequence, they need to be tracked manually as otherwise the
        # offsets in jump targets can end up being wrong.
        if not extended_arg:
            # The list is modified in place
            bytecode._remove_extended_args(instructions)

        bytecode.name = code.co_name
        bytecode.filename = code.co_filename
        bytecode.flags = code.co_flags
        bytecode.argcount = code.co_argcount
        if sys.version_info >= (3, 8):
            bytecode.posonlyargcount = code.co_posonlyargcount
        bytecode.kwonlyargcount = code.co_kwonlyargcount
        bytecode.first_lineno = code.co_firstlineno
        bytecode.names = list(code.co_names)
        bytecode.consts = list(code.co_consts)
        bytecode.varnames = list(code.co_varnames)
        bytecode.freevars = list(code.co_freevars)
        bytecode.cellvars = list(code.co_cellvars)
        _set_docstring(bytecode, code.co_consts)

        bytecode[:] = instructions
        return bytecode

    @staticmethod
    def _normalize_lineno(instructions, first_lineno):
        lineno = first_lineno
        for instr in instructions:
            # if instr.lineno is not set, it's inherited from the previous
            # instruction, or from self.first_lineno
            if instr.lineno is not None:
                lineno = instr.lineno

            if isinstance(instr, ConcreteInstr):
                yield (lineno, instr)

    def _assemble_code(self):
        offset = 0
        code_str = []
        linenos = []
        for lineno, instr in self._normalize_lineno(self, self.first_lineno):
            code_str.append(instr.assemble())
            i_size = instr.size
            linenos.append(((offset * 2) if OFFSET_AS_INSTRUCTION else offset, i_size, lineno))
            offset += (i_size // 2) if OFFSET_AS_INSTRUCTION else i_size
        code_str = b"".join(code_str)
        return (code_str, linenos)

    @staticmethod
    def _assemble_lnotab(first_lineno, linenos):
        lnotab = []
        old_offset = 0
        old_lineno = first_lineno
        for offset, _, lineno in linenos:
            dlineno = lineno - old_lineno
            if dlineno == 0:
                continue
            # FIXME: be kind, force monotonic line numbers? add an option?
            if dlineno < 0 and sys.version_info < (3, 6):
                raise ValueError("negative line number delta is not supported " "on Python < 3.6")
            old_lineno = lineno

            doff = offset - old_offset
            old_offset = offset

            while doff > 255:
                lnotab.append(b"\xff\x00")
                doff -= 255

            while dlineno < -128:
                lnotab.append(struct.pack("Bb", doff, -128))
                doff = 0
                dlineno -= -128

            while dlineno > 127:
                lnotab.append(struct.pack("Bb", doff, 127))
                doff = 0
                dlineno -= 127

            assert 0 <= doff <= 255
            assert -128 <= dlineno <= 127

            lnotab.append(struct.pack("Bb", doff, dlineno))

        return b"".join(lnotab)

    @staticmethod
    def _pack_linetable(doff, dlineno, linetable):
        while dlineno < -127:
            linetable.append(struct.pack("Bb", 0, -127))
            dlineno -= -127

        while dlineno > 127:
            linetable.append(struct.pack("Bb", 0, 127))
            dlineno -= 127

        if doff > 254:
            linetable.append(struct.pack("Bb", 254, dlineno))
            doff -= 254

            while doff > 254:
                linetable.append(b"\xfe\x00")
                doff -= 254
            linetable.append(struct.pack("Bb", doff, 0))

        else:
            linetable.append(struct.pack("Bb", doff, dlineno))

        assert 0 <= doff <= 254
        assert -127 <= dlineno <= 127

    def _assemble_linestable(self, first_lineno, linenos):
        if not linenos:
            return b""

        linetable = []
        old_offset = 0

        iter_in = iter(linenos)

        offset, i_size, old_lineno = next(iter_in)
        old_dlineno = old_lineno - first_lineno
        for offset, i_size, lineno in iter_in:
            dlineno = lineno - old_lineno
            if dlineno == 0:
                continue
            old_lineno = lineno

            doff = offset - old_offset
            old_offset = offset

            self._pack_linetable(doff, old_dlineno, linetable)
            old_dlineno = dlineno

        # Pack the line of the last instruction.
        doff = offset + i_size - old_offset
        self._pack_linetable(doff, old_dlineno, linetable)

        return b"".join(linetable)

    @staticmethod
    def _remove_extended_args(instructions):
        # replace jump targets with blocks
        # HINT : in some cases Python generate useless EXTENDED_ARG opcode
        # with a value of zero. Such opcodes do not increases the size of the
        # following opcode the way a normal EXTENDED_ARG does. As a
        # consequence, they need to be tracked manually as otherwise the
        # offsets in jump targets can end up being wrong.
        nb_extended_args = 0
        extended_arg = None
        index = 0
        while index < len(instructions):
            instr = instructions[index]

            # Skip SetLineno meta instruction
            if isinstance(instr, SetLineno):
                index += 1
                continue

            if instr.name == "EXTENDED_ARG":
                nb_extended_args += 1
                if extended_arg is not None:
                    extended_arg = (extended_arg << 8) + instr.arg
                else:
                    extended_arg = instr.arg

                del instructions[index]
                continue

            if extended_arg is not None:
                arg = (extended_arg << 8) + instr.arg
                extended_arg = None

                instr = ConcreteInstr(
                    instr.name,
                    arg,
                    lineno=instr.lineno,
                    extended_args=nb_extended_args,
                    offset=instr.offset,
                )
                instructions[index] = instr
                nb_extended_args = 0

            index += 1

        if extended_arg is not None:
            raise ValueError("EXTENDED_ARG at the end of the code")

    def compute_stacksize(self, *, check_pre_and_post=True):
        bytecode = self.to_bytecode()
        cfg = _bytecode.ControlFlowGraph.from_bytecode(bytecode)
        return cfg.compute_stacksize(check_pre_and_post=check_pre_and_post)

    def to_code(self, stacksize=None, *, check_pre_and_post=True):
        code_str, linenos = self._assemble_code()
        lnotab = (
            self._assemble_linestable(self.first_lineno, linenos)
            if sys.version_info >= (3, 10)
            else self._assemble_lnotab(self.first_lineno, linenos)
        )
        nlocals = len(self.varnames)
        if stacksize is None:
            stacksize = self.compute_stacksize(check_pre_and_post=check_pre_and_post)

        if sys.version_info < (3, 8):
            return types.CodeType(
                self.argcount,
                self.kwonlyargcount,
                nlocals,
                stacksize,
                int(self.flags),
                code_str,
                tuple(self.consts),
                tuple(self.names),
                tuple(self.varnames),
                self.filename,
                self.name,
                self.first_lineno,
                lnotab,
                tuple(self.freevars),
                tuple(self.cellvars),
            )
        else:
            return types.CodeType(
                self.argcount,
                self.posonlyargcount,
                self.kwonlyargcount,
                nlocals,
                stacksize,
                int(self.flags),
                code_str,
                tuple(self.consts),
                tuple(self.names),
                tuple(self.varnames),
                self.filename,
                self.name,
                self.first_lineno,
                lnotab,
                tuple(self.freevars),
                tuple(self.cellvars),
            )

    def to_bytecode(self):
        # Copy instruction and remove extended args if any (in-place)
        c_instructions = self[:]
        self._remove_extended_args(c_instructions)

        # find jump targets
        jump_targets = set()
        offset = 0
        for instr in c_instructions:
            if isinstance(instr, SetLineno):
                continue
            target = instr.get_jump_target(offset)
            if target is not None:
                jump_targets.add(target)
            offset += (instr.size // 2) if OFFSET_AS_INSTRUCTION else instr.size

        # create labels
        jumps = []
        instructions = []
        labels = {}
        offset = 0
        ncells = len(self.cellvars)

        for lineno, instr in self._normalize_lineno(c_instructions, self.first_lineno):
            if offset in jump_targets:
                label = Label()
                labels[offset] = label
                instructions.append(label)

            jump_target = instr.get_jump_target(offset)
            size = instr.size

            arg = instr.arg
            # FIXME: better error reporting
            if instr.opcode in _opcode.hasconst:
                arg = self.consts[arg]
            elif instr.opcode in _opcode.haslocal:
                arg = self.varnames[arg]
            elif instr.opcode in _opcode.hasname:
                arg = self.names[arg]
            elif instr.opcode in _opcode.hasfree:
                if arg < ncells:
                    name = self.cellvars[arg]
                    arg = CellVar(name)
                else:
                    name = self.freevars[arg - ncells]
                    arg = FreeVar(name)
            elif instr.opcode in _opcode.hascompare:
                arg = Compare(arg)

            if jump_target is None:
                instr = Instr(instr.name, arg, lineno=lineno, offset=instr.offset)
            else:
                instr_index = len(instructions)
            instructions.append(instr)
            offset += (size // 2) if OFFSET_AS_INSTRUCTION else size

            if jump_target is not None:
                jumps.append((instr_index, jump_target))

        # replace jump targets with labels
        for index, jump_target in jumps:
            instr = instructions[index]
            # FIXME: better error reporting on missing label
            label = labels[jump_target]
            instructions[index] = Instr(instr.name, label, lineno=instr.lineno, offset=instr.offset)

        bytecode = _bytecode.Bytecode()
        bytecode._copy_attr_from(self)

        nargs = bytecode.argcount + bytecode.kwonlyargcount
        if sys.version_info > (3, 8):
            nargs += bytecode.posonlyargcount
        if bytecode.flags & inspect.CO_VARARGS:
            nargs += 1
        if bytecode.flags & inspect.CO_VARKEYWORDS:
            nargs += 1
        bytecode.argnames = self.varnames[:nargs]
        _set_docstring(bytecode, self.consts)

        bytecode.extend(instructions)
        return bytecode


class _ConvertBytecodeToConcrete:
    # Default number of passes of compute_jumps() before giving up.  Refer to
    # assemble_jump_offsets() in compile.c for background.
    _compute_jumps_passes = 10

    def __init__(self, code):
        assert isinstance(code, _bytecode.Bytecode)
        self.bytecode = code

        # temporary variables
        self.instructions = []
        self.jumps = []
        self.labels = {}

        # used to build ConcreteBytecode() object
        self.consts_indices = {}
        self.consts_list = []
        self.names = []
        self.varnames = []

    def add_const(self, value):
        key = const_key(value)
        if key in self.consts_indices:
            return self.consts_indices[key]
        index = len(self.consts_indices)
        self.consts_indices[key] = index
        self.consts_list.append(value)
        return index

    @staticmethod
    def add(names, name):
        try:
            index = names.index(name)
        except ValueError:
            index = len(names)
            names.append(name)
        return index

    def concrete_instructions(self):
        ncells = len(self.bytecode.cellvars)
        lineno = self.bytecode.first_lineno

        for instr in self.bytecode:
            if isinstance(instr, Label):
                self.labels[instr] = len(self.instructions)
                continue

            if isinstance(instr, SetLineno):
                lineno = instr.lineno
                continue

            if isinstance(instr, ConcreteInstr):
                instr = instr.copy()
            else:
                assert isinstance(instr, Instr)

                if instr.lineno is not None:
                    lineno = instr.lineno

                arg = instr.arg
                is_jump = isinstance(arg, Label)
                if is_jump:
                    label = arg
                    # fake value, real value is set in compute_jumps()
                    arg = 0
                elif instr.opcode in _opcode.hasconst:
                    arg = self.add_const(arg)
                elif instr.opcode in _opcode.haslocal:
                    arg = self.add(self.varnames, arg)
                elif instr.opcode in _opcode.hasname:
                    arg = self.add(self.names, arg)
                elif instr.opcode in _opcode.hasfree:
                    if isinstance(arg, CellVar):
                        arg = self.bytecode.cellvars.index(arg.name)
                    else:
                        assert isinstance(arg, FreeVar)
                        arg = ncells + self.bytecode.freevars.index(arg.name)
                elif instr.opcode in _opcode.hascompare:
                    if isinstance(arg, Compare):
                        arg = arg.value

                instr = ConcreteInstr(instr.name, arg, lineno=lineno)
                if is_jump:
                    self.jumps.append((len(self.instructions), label, instr))

            self.instructions.append(instr)

    def compute_jumps(self):
        offsets = []
        offset = 0
        for index, instr in enumerate(self.instructions):
            offsets.append(offset)
            offset += instr.size // 2 if OFFSET_AS_INSTRUCTION else instr.size
        # needed if a label is at the end
        offsets.append(offset)

        # fix argument of jump instructions: resolve labels
        modified = False
        for index, label, instr in self.jumps:
            target_index = self.labels[label]
            target_offset = offsets[target_index]

            if instr.opcode in _opcode.hasjrel:
                instr_offset = offsets[index]
                target_offset -= instr_offset + (instr.size // 2 if OFFSET_AS_INSTRUCTION else instr.size)

            old_size = instr.size
            # FIXME: better error report if target_offset is negative
            instr.arg = target_offset
            if instr.size != old_size:
                modified = True

        return modified

    def to_concrete_bytecode(self, compute_jumps_passes=None):
        if compute_jumps_passes is None:
            compute_jumps_passes = self._compute_jumps_passes

        first_const = self.bytecode.docstring
        if first_const is not UNSET:
            self.add_const(first_const)

        self.varnames.extend(self.bytecode.argnames)

        self.concrete_instructions()
        for pas in range(0, compute_jumps_passes):
            modified = self.compute_jumps()
            if not modified:
                break
        else:
            raise RuntimeError("compute_jumps() failed to converge after" " %d passes" % (pas + 1))

        concrete = ConcreteBytecode(
            self.instructions,
            consts=self.consts_list.copy(),
            names=self.names,
            varnames=self.varnames,
        )
        concrete._copy_attr_from(self.bytecode)
        return concrete

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\shortcuts\auto_suggest.py ===
import re
import asyncio
import tokenize
from io import StringIO
from typing import Callable, List, Optional, Union, Generator, Tuple, ClassVar, Any
import warnings

import prompt_toolkit
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.key_binding.bindings import named_commands as nc
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory, Suggestion
from prompt_toolkit.document import Document
from prompt_toolkit.history import History
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.layout.processors import (
    Processor,
    Transformation,
    TransformationInput,
)

from IPython.core.getipython import get_ipython
from IPython.utils.tokenutil import generate_tokens

from .filters import pass_through


def _get_query(document: Document):
    return document.lines[document.cursor_position_row]


class AppendAutoSuggestionInAnyLine(Processor):
    """
    Append the auto suggestion to lines other than the last (appending to the
    last line is natively supported by the prompt toolkit).

    This has a private `_debug` attribute that can be set to True to display
    debug information as virtual suggestion on the end of any line. You can do
    so with:

        >>> from IPython.terminal.shortcuts.auto_suggest import AppendAutoSuggestionInAnyLine
        >>> AppendAutoSuggestionInAnyLine._debug = True

    """

    _debug: ClassVar[bool] = False

    def __init__(self, style: str = "class:auto-suggestion") -> None:
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        """
         Apply transformation to the line that is currently being edited.

         This is a variation of the original implementation in prompt toolkit
         that allows to not only append suggestions to any line, but also to show
         multi-line suggestions.

         As transformation are applied on a line-by-line basis; we need to trick
         a bit, and elide any line that is after the line we are currently
         editing, until we run out of completions. We cannot shift the existing
         lines

         There are multiple cases to handle:

         The completions ends before the end of the buffer:
             We can resume showing the normal line, and say that some code may
             be hidden.

        The completions ends at the end of the buffer
             We can just say that some code may be hidden.

         And separately:

         The completions ends beyond the end of the buffer
             We need to both say that some code may be hidden, and that some
             lines are not shown.

        """
        last_line_number = ti.document.line_count - 1
        is_last_line = ti.lineno == last_line_number

        noop = lambda text: Transformation(
            fragments=ti.fragments + [(self.style, " " + text if self._debug else "")]
        )
        if ti.document.line_count == 1:
            return noop("noop:oneline")
        if ti.document.cursor_position_row == last_line_number and is_last_line:
            # prompt toolkit already appends something; just leave it be
            return noop("noop:last line and cursor")

        # first everything before the current line is unchanged.
        if ti.lineno < ti.document.cursor_position_row:
            return noop("noop:before cursor")

        buffer = ti.buffer_control.buffer
        if not buffer.suggestion or not ti.document.is_cursor_at_the_end_of_line:
            return noop("noop:not eol")

        delta = ti.lineno - ti.document.cursor_position_row
        suggestions = buffer.suggestion.text.splitlines()

        if len(suggestions) == 0:
            return noop("noop: no suggestions")

        if prompt_toolkit.VERSION < (3, 0, 49):
            if len(suggestions) > 1 and prompt_toolkit.VERSION < (3, 0, 49):
                if ti.lineno == ti.document.cursor_position_row:
                    return Transformation(
                        fragments=ti.fragments
                        + [
                            (
                                "red",
                                "(Cannot show multiline suggestion; requires prompt_toolkit > 3.0.49)",
                            )
                        ]
                    )
                else:
                    return Transformation(fragments=ti.fragments)
            elif len(suggestions) == 1:
                if ti.lineno == ti.document.cursor_position_row:
                    return Transformation(
                        fragments=ti.fragments + [(self.style, suggestions[0])]
                    )
            return Transformation(fragments=ti.fragments)

        if delta == 0:
            suggestion = suggestions[0]
            return Transformation(fragments=ti.fragments + [(self.style, suggestion)])
        if is_last_line:
            if delta < len(suggestions):
                suggestion = f"… rest of suggestion ({len(suggestions) - delta} lines) and code hidden"
                return Transformation([(self.style, suggestion)])

            n_elided = len(suggestions)
            for i in range(len(suggestions)):
                ll = ti.get_line(last_line_number - i)
                el = "".join(l[1] for l in ll).strip()
                if el:
                    break
                else:
                    n_elided -= 1
            if n_elided:
                return Transformation([(self.style, f"… {n_elided} line(s) hidden")])
            else:
                return Transformation(
                    ti.get_line(last_line_number - len(suggestions) + 1)
                    + ([(self.style, "shift-last-line")] if self._debug else [])
                )

        elif delta < len(suggestions):
            suggestion = suggestions[delta]
            return Transformation([(self.style, suggestion)])
        else:
            shift = ti.lineno - len(suggestions) + 1
            return Transformation(ti.get_line(shift))


class NavigableAutoSuggestFromHistory(AutoSuggestFromHistory):
    """
    A subclass of AutoSuggestFromHistory that allow navigation to next/previous
    suggestion from history. To do so it remembers the current position, but it
    state need to carefully be cleared on the right events.
    """

    skip_lines: int
    _connected_apps: list[PromptSession]

    # handle to the currently running llm task that appends suggestions to the
    # current buffer; we keep a handle to it in order to cancel it when there is a cursor movement, or
    # another request.
    _llm_task: asyncio.Task | None = None

    # This is the constructor of the LLM provider from jupyter-ai
    # to which we forward the request to generate inline completions.
    _init_llm_provider: Callable | None

    _llm_provider_instance: Any | None
    _llm_prefixer: Callable = lambda self, x: "wrong"

    def __init__(self):
        super().__init__()
        self.skip_lines = 0
        self._connected_apps = []
        self._llm_provider_instance = None
        self._init_llm_provider = None
        self._request_number = 0

    def reset_history_position(self, _: Buffer) -> None:
        self.skip_lines = 0

    def disconnect(self) -> None:
        self._cancel_running_llm_task()
        for pt_app in self._connected_apps:
            text_insert_event = pt_app.default_buffer.on_text_insert
            text_insert_event.remove_handler(self.reset_history_position)

    def connect(self, pt_app: PromptSession) -> None:
        self._connected_apps.append(pt_app)
        # note: `on_text_changed` could be used for a bit different behaviour
        # on character deletion (i.e. resetting history position on backspace)
        pt_app.default_buffer.on_text_insert.add_handler(self.reset_history_position)
        pt_app.default_buffer.on_cursor_position_changed.add_handler(self._dismiss)

    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Optional[Suggestion]:
        text = _get_query(document)

        if text.strip():
            for suggestion, _ in self._find_next_match(
                text, self.skip_lines, buffer.history
            ):
                return Suggestion(suggestion)

        return None

    def _dismiss(self, buffer, *args, **kwargs) -> None:
        self._cancel_running_llm_task()
        buffer.suggestion = None

    def _find_match(
        self, text: str, skip_lines: float, history: History, previous: bool
    ) -> Generator[Tuple[str, float], None, None]:
        """
        text : str
            Text content to find a match for, the user cursor is most of the
            time at the end of this text.
        skip_lines : float
            number of items to skip in the search, this is used to indicate how
            far in the list the user has navigated by pressing up or down.
            The float type is used as the base value is +inf
        history : History
            prompt_toolkit History instance to fetch previous entries from.
        previous : bool
            Direction of the search, whether we are looking previous match
            (True), or next match (False).

        Yields
        ------
        Tuple with:
        str:
            current suggestion.
        float:
            will actually yield only ints, which is passed back via skip_lines,
            which may be a +inf (float)


        """
        line_number = -1
        for string in reversed(list(history.get_strings())):
            for line in reversed(string.splitlines()):
                line_number += 1
                if not previous and line_number < skip_lines:
                    continue
                # do not return empty suggestions as these
                # close the auto-suggestion overlay (and are useless)
                if line.startswith(text) and len(line) > len(text):
                    yield line[len(text) :], line_number
                if previous and line_number >= skip_lines:
                    return

    def _find_next_match(
        self, text: str, skip_lines: float, history: History
    ) -> Generator[Tuple[str, float], None, None]:
        return self._find_match(text, skip_lines, history, previous=False)

    def _find_previous_match(self, text: str, skip_lines: float, history: History):
        return reversed(
            list(self._find_match(text, skip_lines, history, previous=True))
        )

    def up(self, query: str, other_than: str, history: History) -> None:
        self._cancel_running_llm_task()
        for suggestion, line_number in self._find_next_match(
            query, self.skip_lines, history
        ):
            # if user has history ['very.a', 'very', 'very.b'] and typed 'very'
            # we want to switch from 'very.b' to 'very.a' because a) if the
            # suggestion equals current text, prompt-toolkit aborts suggesting
            # b) user likely would not be interested in 'very' anyways (they
            # already typed it).
            if query + suggestion != other_than:
                self.skip_lines = line_number
                break
        else:
            # no matches found, cycle back to beginning
            self.skip_lines = 0

    def down(self, query: str, other_than: str, history: History) -> None:
        self._cancel_running_llm_task()
        for suggestion, line_number in self._find_previous_match(
            query, self.skip_lines, history
        ):
            if query + suggestion != other_than:
                self.skip_lines = line_number
                break
        else:
            # no matches found, cycle to end
            for suggestion, line_number in self._find_previous_match(
                query, float("Inf"), history
            ):
                if query + suggestion != other_than:
                    self.skip_lines = line_number
                    break

    def _cancel_running_llm_task(self) -> None:
        """
        Try to cancel the currently running llm_task if exists, and set it to None.
        """
        if self._llm_task is not None:
            if self._llm_task.done():
                self._llm_task = None
                return
            cancelled = self._llm_task.cancel()
            if cancelled:
                self._llm_task = None
            if not cancelled:
                warnings.warn(
                    "LLM task not cancelled, does your provider support cancellation?"
                )

    @property
    def _llm_provider(self):
        """Lazy-initialized instance of the LLM provider.

        Do not use in the constructor, as `_init_llm_provider` can trigger slow side-effects.
        """
        if self._llm_provider_instance is None and self._init_llm_provider:
            self._llm_provider_instance = self._init_llm_provider()
        return self._llm_provider_instance

    async def _trigger_llm(self, buffer) -> None:
        """
        This will ask the current llm provider a suggestion for the current buffer.

        If there is a currently running llm task, it will cancel it.
        """
        # we likely want to store the current cursor position, and cancel if the cursor has moved.
        try:
            import jupyter_ai_magics
        except ModuleNotFoundError:
            jupyter_ai_magics = None
        if not self._llm_provider:
            warnings.warn("No LLM provider found, cannot trigger LLM completions")
            return
        if jupyter_ai_magics is None:
            warnings.warn("LLM Completion requires `jupyter_ai_magics` to be installed")

        self._cancel_running_llm_task()

        async def error_catcher(buffer):
            """
            This catches and log any errors, as otherwise this is just
            lost in the void of the future running task.
            """
            try:
                await self._trigger_llm_core(buffer)
            except Exception as e:
                get_ipython().log.error("error %s", e)
                raise

        # here we need a cancellable task so we can't just await the error caught
        self._llm_task = asyncio.create_task(error_catcher(buffer))
        await self._llm_task

    async def _trigger_llm_core(self, buffer: Buffer):
        """
        This is the core of the current llm request.

        Here we build a compatible `InlineCompletionRequest` and ask the llm
        provider to stream it's response back to us iteratively setting it as
        the suggestion on the current buffer.

        Unlike with JupyterAi, as we do not have multiple cells, the cell id
        is always set to `None`.

        We set the prefix to the current cell content, but could also insert the
        rest of the history or even just the non-fail history.

        In the same way, we do not have cell id.

        LLM provider may return multiple suggestion stream, but for the time
        being we only support one.

        Here we make the assumption that the provider will have
        stream_inline_completions, I'm not sure it is the case for all
        providers.
        """
        try:
            import jupyter_ai.completions.models as jai_models
        except ModuleNotFoundError:
            jai_models = None

        if not jai_models:
            raise ValueError("jupyter-ai is not installed")

        if not self._llm_provider:
            raise ValueError("No LLM provider found, cannot trigger LLM completions")

        hm = buffer.history.shell.history_manager
        prefix = self._llm_prefixer(hm)
        get_ipython().log.debug("prefix: %s", prefix)

        self._request_number += 1
        request_number = self._request_number

        request = jai_models.InlineCompletionRequest(
            number=request_number,
            prefix=prefix + buffer.document.text_before_cursor,
            suffix=buffer.document.text_after_cursor,
            mime="text/x-python",
            stream=True,
            path=None,
            language="python",
            cell_id=None,
        )

        async for reply_and_chunks in self._llm_provider.stream_inline_completions(
            request
        ):
            if self._request_number != request_number:
                # If a new suggestion was requested, skip processing this one.
                return
            if isinstance(reply_and_chunks, jai_models.InlineCompletionReply):
                if len(reply_and_chunks.list.items) > 1:
                    raise ValueError(
                        "Terminal IPython cannot deal with multiple LLM suggestions at once"
                    )
                buffer.suggestion = Suggestion(
                    reply_and_chunks.list.items[0].insertText
                )
                buffer.on_suggestion_set.fire()
            elif isinstance(reply_and_chunks, jai_models.InlineCompletionStreamChunk):
                buffer.suggestion = Suggestion(reply_and_chunks.response.insertText)
                buffer.on_suggestion_set.fire()
        return


async def llm_autosuggestion(event: KeyPressEvent):
    """
    Ask the AutoSuggester from history to delegate to ask an LLM for completion

    This will first make sure that the current buffer have _MIN_LINES (7)
    available lines to insert the LLM completion

    Provisional as of 8.32, may change without warnings

    """
    _MIN_LINES = 5
    provider = get_ipython().auto_suggest
    if not isinstance(provider, NavigableAutoSuggestFromHistory):
        return
    doc = event.current_buffer.document
    lines_to_insert = max(0, _MIN_LINES - doc.line_count + doc.cursor_position_row)
    for _ in range(lines_to_insert):
        event.current_buffer.insert_text("\n", move_cursor=False, fire_event=False)

    await provider._trigger_llm(event.current_buffer)


def accept_or_jump_to_end(event: KeyPressEvent):
    """Apply autosuggestion or jump to end of line."""
    buffer = event.current_buffer
    d = buffer.document
    after_cursor = d.text[d.cursor_position :]
    lines = after_cursor.split("\n")
    end_of_current_line = lines[0].strip()
    suggestion = buffer.suggestion
    if (suggestion is not None) and (suggestion.text) and (end_of_current_line == ""):
        buffer.insert_text(suggestion.text)
    else:
        nc.end_of_line(event)


def accept(event: KeyPressEvent):
    """Accept autosuggestion"""
    buffer = event.current_buffer
    suggestion = buffer.suggestion
    if suggestion:
        buffer.insert_text(suggestion.text)
    else:
        nc.forward_char(event)


def discard(event: KeyPressEvent):
    """Discard autosuggestion"""
    buffer = event.current_buffer
    buffer.suggestion = None


def accept_word(event: KeyPressEvent):
    """Fill partial autosuggestion by word"""
    buffer = event.current_buffer
    suggestion = buffer.suggestion
    if suggestion:
        t = re.split(r"(\S+\s+)", suggestion.text)
        buffer.insert_text(next((x for x in t if x), ""))
    else:
        nc.forward_word(event)


def accept_character(event: KeyPressEvent):
    """Fill partial autosuggestion by character"""
    b = event.current_buffer
    suggestion = b.suggestion
    if suggestion and suggestion.text:
        b.insert_text(suggestion.text[0])


def accept_and_keep_cursor(event: KeyPressEvent):
    """Accept autosuggestion and keep cursor in place"""
    buffer = event.current_buffer
    old_position = buffer.cursor_position
    suggestion = buffer.suggestion
    if suggestion:
        buffer.insert_text(suggestion.text)
        buffer.cursor_position = old_position


def accept_and_move_cursor_left(event: KeyPressEvent):
    """Accept autosuggestion and move cursor left in place"""
    accept_and_keep_cursor(event)
    nc.backward_char(event)


def _update_hint(buffer: Buffer):
    if buffer.auto_suggest:
        suggestion = buffer.auto_suggest.get_suggestion(buffer, buffer.document)
        buffer.suggestion = suggestion


def backspace_and_resume_hint(event: KeyPressEvent):
    """Resume autosuggestions after deleting last character"""
    nc.backward_delete_char(event)
    _update_hint(event.current_buffer)


def resume_hinting(event: KeyPressEvent):
    """Resume autosuggestions"""
    pass_through.reply(event)
    # Order matters: if update happened first and event reply second, the
    # suggestion would be auto-accepted if both actions are bound to same key.
    _update_hint(event.current_buffer)


def up_and_update_hint(event: KeyPressEvent):
    """Go up and update hint"""
    current_buffer = event.current_buffer

    current_buffer.auto_up(count=event.arg)
    _update_hint(current_buffer)


def down_and_update_hint(event: KeyPressEvent):
    """Go down and update hint"""
    current_buffer = event.current_buffer

    current_buffer.auto_down(count=event.arg)
    _update_hint(current_buffer)


def accept_token(event: KeyPressEvent):
    """Fill partial autosuggestion by token"""
    b = event.current_buffer
    suggestion = b.suggestion

    if suggestion:
        prefix = _get_query(b.document)
        text = prefix + suggestion.text

        tokens: List[Optional[str]] = [None, None, None]
        substrings = [""]
        i = 0

        for token in generate_tokens(StringIO(text).readline):
            if token.type == tokenize.NEWLINE:
                index = len(text)
            else:
                index = text.index(token[1], len(substrings[-1]))
            substrings.append(text[:index])
            tokenized_so_far = substrings[-1]
            if tokenized_so_far.startswith(prefix):
                if i == 0 and len(tokenized_so_far) > len(prefix):
                    tokens[0] = tokenized_so_far[len(prefix) :]
                    substrings.append(tokenized_so_far)
                    i += 1
                tokens[i] = token[1]
                if i == 2:
                    break
                i += 1

        if tokens[0]:
            to_insert: str
            insert_text = substrings[-2]
            if tokens[1] and len(tokens[1]) == 1:
                insert_text = substrings[-1]
            to_insert = insert_text[len(prefix) :]
            b.insert_text(to_insert)
            return

    nc.forward_word(event)


Provider = Union[AutoSuggestFromHistory, NavigableAutoSuggestFromHistory, None]


def _swap_autosuggestion(
    buffer: Buffer,
    provider: NavigableAutoSuggestFromHistory,
    direction_method: Callable,
):
    """
    We skip most recent history entry (in either direction) if it equals the
    current autosuggestion because if user cycles when auto-suggestion is shown
    they most likely want something else than what was suggested (otherwise
    they would have accepted the suggestion).
    """
    suggestion = buffer.suggestion
    if not suggestion:
        return

    query = _get_query(buffer.document)
    current = query + suggestion.text

    direction_method(query=query, other_than=current, history=buffer.history)

    new_suggestion = provider.get_suggestion(buffer, buffer.document)
    buffer.suggestion = new_suggestion


def swap_autosuggestion_up(event: KeyPressEvent):
    """Get next autosuggestion from history."""
    shell = get_ipython()
    provider = shell.auto_suggest

    if not isinstance(provider, NavigableAutoSuggestFromHistory):
        return

    return _swap_autosuggestion(
        buffer=event.current_buffer, provider=provider, direction_method=provider.up
    )


def swap_autosuggestion_down(event: KeyPressEvent):
    """Get previous autosuggestion from history."""
    shell = get_ipython()
    provider = shell.auto_suggest

    if not isinstance(provider, NavigableAutoSuggestFromHistory):
        return

    return _swap_autosuggestion(
        buffer=event.current_buffer,
        provider=provider,
        direction_method=provider.down,
    )

# === NexusCore/openenv\Lib\site-packages\nltk\collections.py ===
# Natural Language Toolkit: Collections
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import bisect
from functools import total_ordering
from itertools import chain, islice

from nltk.internals import raise_unorderable_types, slice_bounds

##########################################################################
# Ordered Dictionary
##########################################################################


class OrderedDict(dict):
    def __init__(self, data=None, **kwargs):
        self._keys = self.keys(data, kwargs.get("keys"))
        self._default_factory = kwargs.get("default_factory")
        if data is None:
            dict.__init__(self)
        else:
            dict.__init__(self, data)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __iter__(self):
        return (key for key in self.keys())

    def __missing__(self, key):
        if not self._default_factory and key not in self._keys:
            raise KeyError()
        return self._default_factory()

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        dict.clear(self)
        self._keys.clear()

    def copy(self):
        d = dict.copy(self)
        d._keys = self._keys
        return d

    def items(self):
        return zip(self.keys(), self.values())

    def keys(self, data=None, keys=None):
        if data:
            if keys:
                assert isinstance(keys, list)
                assert len(data) == len(keys)
                return keys
            else:
                assert (
                    isinstance(data, dict)
                    or isinstance(data, OrderedDict)
                    or isinstance(data, list)
                )
                if isinstance(data, dict) or isinstance(data, OrderedDict):
                    return data.keys()
                elif isinstance(data, list):
                    return [key for (key, value) in data]
        elif "_keys" in self.__dict__:
            return self._keys
        else:
            return []

    def popitem(self):
        if not self._keys:
            raise KeyError()

        key = self._keys.pop()
        value = self[key]
        del self[key]
        return (key, value)

    def setdefault(self, key, failobj=None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, data):
        dict.update(self, data)
        for key in self.keys(data):
            if key not in self._keys:
                self._keys.append(key)

    def values(self):
        return map(self.get, self._keys)


######################################################################
# Lazy Sequences
######################################################################


@total_ordering
class AbstractLazySequence:
    """
    An abstract base class for read-only sequences whose values are
    computed as needed.  Lazy sequences act like tuples -- they can be
    indexed, sliced, and iterated over; but they may not be modified.

    The most common application of lazy sequences in NLTK is for
    corpus view objects, which provide access to the contents of a
    corpus without loading the entire corpus into memory, by loading
    pieces of the corpus from disk as needed.

    The result of modifying a mutable element of a lazy sequence is
    undefined.  In particular, the modifications made to the element
    may or may not persist, depending on whether and when the lazy
    sequence caches that element's value or reconstructs it from
    scratch.

    Subclasses are required to define two methods: ``__len__()``
    and ``iterate_from()``.
    """

    def __len__(self):
        """
        Return the number of tokens in the corpus file underlying this
        corpus view.
        """
        raise NotImplementedError("should be implemented by subclass")

    def iterate_from(self, start):
        """
        Return an iterator that generates the tokens in the corpus
        file underlying this corpus view, starting at the token number
        ``start``.  If ``start>=len(self)``, then this iterator will
        generate no tokens.
        """
        raise NotImplementedError("should be implemented by subclass")

    def __getitem__(self, i):
        """
        Return the *i* th token in the corpus file underlying this
        corpus view.  Negative indices and spans are both supported.
        """
        if isinstance(i, slice):
            start, stop = slice_bounds(self, i)
            return LazySubsequence(self, start, stop)
        else:
            # Handle negative indices
            if i < 0:
                i += len(self)
            if i < 0:
                raise IndexError("index out of range")
            # Use iterate_from to extract it.
            try:
                return next(self.iterate_from(i))
            except StopIteration as e:
                raise IndexError("index out of range") from e

    def __iter__(self):
        """Return an iterator that generates the tokens in the corpus
        file underlying this corpus view."""
        return self.iterate_from(0)

    def count(self, value):
        """Return the number of times this list contains ``value``."""
        return sum(1 for elt in self if elt == value)

    def index(self, value, start=None, stop=None):
        """Return the index of the first occurrence of ``value`` in this
        list that is greater than or equal to ``start`` and less than
        ``stop``.  Negative start and stop values are treated like negative
        slice bounds -- i.e., they count from the end of the list."""
        start, stop = slice_bounds(self, slice(start, stop))
        for i, elt in enumerate(islice(self, start, stop)):
            if elt == value:
                return i + start
        raise ValueError("index(x): x not in list")

    def __contains__(self, value):
        """Return true if this list contains ``value``."""
        return bool(self.count(value))

    def __add__(self, other):
        """Return a list concatenating self with other."""
        return LazyConcatenation([self, other])

    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return LazyConcatenation([other, self])

    def __mul__(self, count):
        """Return a list concatenating self with itself ``count`` times."""
        return LazyConcatenation([self] * count)

    def __rmul__(self, count):
        """Return a list concatenating self with itself ``count`` times."""
        return LazyConcatenation([self] * count)

    _MAX_REPR_SIZE = 60

    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(repr(elt))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % ", ".join(pieces[:-1])
        return "[%s]" % ", ".join(pieces)

    def __eq__(self, other):
        return type(self) == type(other) and list(self) == list(other)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if type(other) != type(self):
            raise_unorderable_types("<", self, other)
        return list(self) < list(other)

    def __hash__(self):
        """
        :raise ValueError: Corpus view objects are unhashable.
        """
        raise ValueError("%s objects are unhashable" % self.__class__.__name__)


class LazySubsequence(AbstractLazySequence):
    """
    A subsequence produced by slicing a lazy sequence.  This slice
    keeps a reference to its source sequence, and generates its values
    by looking them up in the source sequence.
    """

    MIN_SIZE = 100
    """
    The minimum size for which lazy slices should be created.  If
    ``LazySubsequence()`` is called with a subsequence that is
    shorter than ``MIN_SIZE``, then a tuple will be returned instead.
    """

    def __new__(cls, source, start, stop):
        """
        Construct a new slice from a given underlying sequence.  The
        ``start`` and ``stop`` indices should be absolute indices --
        i.e., they should not be negative (for indexing from the back
        of a list) or greater than the length of ``source``.
        """
        # If the slice is small enough, just use a tuple.
        if stop - start < cls.MIN_SIZE:
            return list(islice(source.iterate_from(start), stop - start))
        else:
            return object.__new__(cls)

    def __init__(self, source, start, stop):
        self._source = source
        self._start = start
        self._stop = stop

    def __len__(self):
        return self._stop - self._start

    def iterate_from(self, start):
        return islice(
            self._source.iterate_from(start + self._start), max(0, len(self) - start)
        )


class LazyConcatenation(AbstractLazySequence):
    """
    A lazy sequence formed by concatenating a list of lists.  This
    underlying list of lists may itself be lazy.  ``LazyConcatenation``
    maintains an index that it uses to keep track of the relationship
    between offsets in the concatenated lists and offsets in the
    sublists.
    """

    def __init__(self, list_of_lists):
        self._list = list_of_lists
        self._offsets = [0]

    def __len__(self):
        if len(self._offsets) <= len(self._list):
            for _ in self.iterate_from(self._offsets[-1]):
                pass
        return self._offsets[-1]

    def iterate_from(self, start_index):
        if start_index < self._offsets[-1]:
            sublist_index = bisect.bisect_right(self._offsets, start_index) - 1
        else:
            sublist_index = len(self._offsets) - 1

        index = self._offsets[sublist_index]

        # Construct an iterator over the sublists.
        if isinstance(self._list, AbstractLazySequence):
            sublist_iter = self._list.iterate_from(sublist_index)
        else:
            sublist_iter = islice(self._list, sublist_index, None)

        for sublist in sublist_iter:
            if sublist_index == (len(self._offsets) - 1):
                assert (
                    index + len(sublist) >= self._offsets[-1]
                ), "offsets not monotonic increasing!"
                self._offsets.append(index + len(sublist))
            else:
                assert self._offsets[sublist_index + 1] == index + len(
                    sublist
                ), "inconsistent list value (num elts)"

            yield from sublist[max(0, start_index - index) :]

            index += len(sublist)
            sublist_index += 1


class LazyMap(AbstractLazySequence):
    """
    A lazy sequence whose elements are formed by applying a given
    function to each element in one or more underlying lists.  The
    function is applied lazily -- i.e., when you read a value from the
    list, ``LazyMap`` will calculate that value by applying its
    function to the underlying lists' value(s).  ``LazyMap`` is
    essentially a lazy version of the Python primitive function
    ``map``.  In particular, the following two expressions are
    equivalent:

        >>> from nltk.collections import LazyMap
        >>> function = str
        >>> sequence = [1,2,3]
        >>> map(function, sequence) # doctest: +SKIP
        ['1', '2', '3']
        >>> list(LazyMap(function, sequence))
        ['1', '2', '3']

    Like the Python ``map`` primitive, if the source lists do not have
    equal size, then the value None will be supplied for the
    'missing' elements.

    Lazy maps can be useful for conserving memory, in cases where
    individual values take up a lot of space.  This is especially true
    if the underlying list's values are constructed lazily, as is the
    case with many corpus readers.

    A typical example of a use case for this class is performing
    feature detection on the tokens in a corpus.  Since featuresets
    are encoded as dictionaries, which can take up a lot of memory,
    using a ``LazyMap`` can significantly reduce memory usage when
    training and running classifiers.
    """

    def __init__(self, function, *lists, **config):
        """
        :param function: The function that should be applied to
            elements of ``lists``.  It should take as many arguments
            as there are ``lists``.
        :param lists: The underlying lists.
        :param cache_size: Determines the size of the cache used
            by this lazy map.  (default=5)
        """
        if not lists:
            raise TypeError("LazyMap requires at least two args")

        self._lists = lists
        self._func = function
        self._cache_size = config.get("cache_size", 5)
        self._cache = {} if self._cache_size > 0 else None

        # If you just take bool() of sum() here _all_lazy will be true just
        # in case n >= 1 list is an AbstractLazySequence.  Presumably this
        # isn't what's intended.
        self._all_lazy = sum(
            isinstance(lst, AbstractLazySequence) for lst in lists
        ) == len(lists)

    def iterate_from(self, index):
        # Special case: one lazy sublist
        if len(self._lists) == 1 and self._all_lazy:
            for value in self._lists[0].iterate_from(index):
                yield self._func(value)
            return

        # Special case: one non-lazy sublist
        elif len(self._lists) == 1:
            while True:
                try:
                    yield self._func(self._lists[0][index])
                except IndexError:
                    return
                index += 1

        # Special case: n lazy sublists
        elif self._all_lazy:
            iterators = [lst.iterate_from(index) for lst in self._lists]
            while True:
                elements = []
                for iterator in iterators:
                    try:
                        elements.append(next(iterator))
                    except:  # FIXME: What is this except really catching? StopIteration?
                        elements.append(None)
                if elements == [None] * len(self._lists):
                    return
                yield self._func(*elements)
                index += 1

        # general case
        else:
            while True:
                try:
                    elements = [lst[index] for lst in self._lists]
                except IndexError:
                    elements = [None] * len(self._lists)
                    for i, lst in enumerate(self._lists):
                        try:
                            elements[i] = lst[index]
                        except IndexError:
                            pass
                    if elements == [None] * len(self._lists):
                        return
                yield self._func(*elements)
                index += 1

    def __getitem__(self, index):
        if isinstance(index, slice):
            sliced_lists = [lst[index] for lst in self._lists]
            return LazyMap(self._func, *sliced_lists)
        else:
            # Handle negative indices
            if index < 0:
                index += len(self)
            if index < 0:
                raise IndexError("index out of range")
            # Check the cache
            if self._cache is not None and index in self._cache:
                return self._cache[index]
            # Calculate the value
            try:
                val = next(self.iterate_from(index))
            except StopIteration as e:
                raise IndexError("index out of range") from e
            # Update the cache
            if self._cache is not None:
                if len(self._cache) > self._cache_size:
                    self._cache.popitem()  # discard random entry
                self._cache[index] = val
            # Return the value
            return val

    def __len__(self):
        return max(len(lst) for lst in self._lists)


class LazyZip(LazyMap):
    """
    A lazy sequence whose elements are tuples, each containing the i-th
    element from each of the argument sequences.  The returned list is
    truncated in length to the length of the shortest argument sequence. The
    tuples are constructed lazily -- i.e., when you read a value from the
    list, ``LazyZip`` will calculate that value by forming a tuple from
    the i-th element of each of the argument sequences.

    ``LazyZip`` is essentially a lazy version of the Python primitive function
    ``zip``.  In particular, an evaluated LazyZip is equivalent to a zip:

        >>> from nltk.collections import LazyZip
        >>> sequence1, sequence2 = [1, 2, 3], ['a', 'b', 'c']
        >>> zip(sequence1, sequence2) # doctest: +SKIP
        [(1, 'a'), (2, 'b'), (3, 'c')]
        >>> list(LazyZip(sequence1, sequence2))
        [(1, 'a'), (2, 'b'), (3, 'c')]
        >>> sequences = [sequence1, sequence2, [6,7,8,9]]
        >>> list(zip(*sequences)) == list(LazyZip(*sequences))
        True

    Lazy zips can be useful for conserving memory in cases where the argument
    sequences are particularly long.

    A typical example of a use case for this class is combining long sequences
    of gold standard and predicted values in a classification or tagging task
    in order to calculate accuracy.  By constructing tuples lazily and
    avoiding the creation of an additional long sequence, memory usage can be
    significantly reduced.
    """

    def __init__(self, *lists):
        """
        :param lists: the underlying lists
        :type lists: list(list)
        """
        LazyMap.__init__(self, lambda *elts: elts, *lists)

    def iterate_from(self, index):
        iterator = LazyMap.iterate_from(self, index)
        while index < len(self):
            yield next(iterator)
            index += 1
        return

    def __len__(self):
        return min(len(lst) for lst in self._lists)


class LazyEnumerate(LazyZip):
    """
    A lazy sequence whose elements are tuples, each containing a count (from
    zero) and a value yielded by underlying sequence.  ``LazyEnumerate`` is
    useful for obtaining an indexed list. The tuples are constructed lazily
    -- i.e., when you read a value from the list, ``LazyEnumerate`` will
    calculate that value by forming a tuple from the count of the i-th
    element and the i-th element of the underlying sequence.

    ``LazyEnumerate`` is essentially a lazy version of the Python primitive
    function ``enumerate``.  In particular, the following two expressions are
    equivalent:

        >>> from nltk.collections import LazyEnumerate
        >>> sequence = ['first', 'second', 'third']
        >>> list(enumerate(sequence))
        [(0, 'first'), (1, 'second'), (2, 'third')]
        >>> list(LazyEnumerate(sequence))
        [(0, 'first'), (1, 'second'), (2, 'third')]

    Lazy enumerations can be useful for conserving memory in cases where the
    argument sequences are particularly long.

    A typical example of a use case for this class is obtaining an indexed
    list for a long sequence of values.  By constructing tuples lazily and
    avoiding the creation of an additional long sequence, memory usage can be
    significantly reduced.
    """

    def __init__(self, lst):
        """
        :param lst: the underlying list
        :type lst: list
        """
        LazyZip.__init__(self, range(len(lst)), lst)


class LazyIteratorList(AbstractLazySequence):
    """
    Wraps an iterator, loading its elements on demand
    and making them subscriptable.
    __repr__ displays only the first few elements.
    """

    def __init__(self, it, known_len=None):
        self._it = it
        self._len = known_len
        self._cache = []

    def __len__(self):
        if self._len:
            return self._len
        for _ in self.iterate_from(len(self._cache)):
            pass
        self._len = len(self._cache)
        return self._len

    def iterate_from(self, start):
        """Create a new iterator over this list starting at the given offset."""
        while len(self._cache) < start:
            v = next(self._it)
            self._cache.append(v)
        i = start
        while i < len(self._cache):
            yield self._cache[i]
            i += 1
        try:
            while True:
                v = next(self._it)
                self._cache.append(v)
                yield v
        except StopIteration:
            pass

    def __add__(self, other):
        """Return a list concatenating self with other."""
        return type(self)(chain(self, other))

    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return type(self)(chain(other, self))


######################################################################
# Trie Implementation
######################################################################
class Trie(dict):
    """A Trie implementation for strings"""

    LEAF = True

    def __init__(self, strings=None):
        """Builds a Trie object, which is built around a ``dict``

        If ``strings`` is provided, it will add the ``strings``, which
        consist of a ``list`` of ``strings``, to the Trie.
        Otherwise, it'll construct an empty Trie.

        :param strings: List of strings to insert into the trie
            (Default is ``None``)
        :type strings: list(str)

        """
        super().__init__()
        if strings:
            for string in strings:
                self.insert(string)

    def insert(self, string):
        """Inserts ``string`` into the Trie

        :param string: String to insert into the trie
        :type string: str

        :Example:

        >>> from nltk.collections import Trie
        >>> trie = Trie(["abc", "def"])
        >>> expected = {'a': {'b': {'c': {True: None}}}, \
                        'd': {'e': {'f': {True: None}}}}
        >>> trie == expected
        True

        """
        if len(string):
            self[string[0]].insert(string[1:])
        else:
            # mark the string is complete
            self[Trie.LEAF] = None

    def __missing__(self, key):
        self[key] = Trie()
        return self[key]

# === NexusCore/openenv\Lib\site-packages\packaging\tags.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import logging
import platform
import re
import struct
import subprocess
import sys
import sysconfig
from importlib.machinery import EXTENSION_SUFFIXES
from typing import (
    Iterable,
    Iterator,
    Sequence,
    Tuple,
    cast,
)

from . import _manylinux, _musllinux

logger = logging.getLogger(__name__)

PythonVersion = Sequence[int]
AppleVersion = Tuple[int, int]

INTERPRETER_SHORT_NAMES: dict[str, str] = {
    "python": "py",  # Generic.
    "cpython": "cp",
    "pypy": "pp",
    "ironpython": "ip",
    "jython": "jy",
}


_32_BIT_INTERPRETER = struct.calcsize("P") == 4


class Tag:
    """
    A representation of the tag triple for a wheel.

    Instances are considered immutable and thus are hashable. Equality checking
    is also supported.
    """

    __slots__ = ["_abi", "_hash", "_interpreter", "_platform"]

    def __init__(self, interpreter: str, abi: str, platform: str) -> None:
        self._interpreter = interpreter.lower()
        self._abi = abi.lower()
        self._platform = platform.lower()
        # The __hash__ of every single element in a Set[Tag] will be evaluated each time
        # that a set calls its `.disjoint()` method, which may be called hundreds of
        # times when scanning a page of links for packages with tags matching that
        # Set[Tag]. Pre-computing the value here produces significant speedups for
        # downstream consumers.
        self._hash = hash((self._interpreter, self._abi, self._platform))

    @property
    def interpreter(self) -> str:
        return self._interpreter

    @property
    def abi(self) -> str:
        return self._abi

    @property
    def platform(self) -> str:
        return self._platform

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented

        return (
            (self._hash == other._hash)  # Short-circuit ASAP for perf reasons.
            and (self._platform == other._platform)
            and (self._abi == other._abi)
            and (self._interpreter == other._interpreter)
        )

    def __hash__(self) -> int:
        return self._hash

    def __str__(self) -> str:
        return f"{self._interpreter}-{self._abi}-{self._platform}"

    def __repr__(self) -> str:
        return f"<{self} @ {id(self)}>"


def parse_tag(tag: str) -> frozenset[Tag]:
    """
    Parses the provided tag (e.g. `py3-none-any`) into a frozenset of Tag instances.

    Returning a set is required due to the possibility that the tag is a
    compressed tag set.
    """
    tags = set()
    interpreters, abis, platforms = tag.split("-")
    for interpreter in interpreters.split("."):
        for abi in abis.split("."):
            for platform_ in platforms.split("."):
                tags.add(Tag(interpreter, abi, platform_))
    return frozenset(tags)


def _get_config_var(name: str, warn: bool = False) -> int | str | None:
    value: int | str | None = sysconfig.get_config_var(name)
    if value is None and warn:
        logger.debug(
            "Config variable '%s' is unset, Python ABI tag may be incorrect", name
        )
    return value


def _normalize_string(string: str) -> str:
    return string.replace(".", "_").replace("-", "_").replace(" ", "_")


def _is_threaded_cpython(abis: list[str]) -> bool:
    """
    Determine if the ABI corresponds to a threaded (`--disable-gil`) build.

    The threaded builds are indicated by a "t" in the abiflags.
    """
    if len(abis) == 0:
        return False
    # expect e.g., cp313
    m = re.match(r"cp\d+(.*)", abis[0])
    if not m:
        return False
    abiflags = m.group(1)
    return "t" in abiflags


def _abi3_applies(python_version: PythonVersion, threading: bool) -> bool:
    """
    Determine if the Python version supports abi3.

    PEP 384 was first implemented in Python 3.2. The threaded (`--disable-gil`)
    builds do not support abi3.
    """
    return len(python_version) > 1 and tuple(python_version) >= (3, 2) and not threading


def _cpython_abis(py_version: PythonVersion, warn: bool = False) -> list[str]:
    py_version = tuple(py_version)  # To allow for version comparison.
    abis = []
    version = _version_nodot(py_version[:2])
    threading = debug = pymalloc = ucs4 = ""
    with_debug = _get_config_var("Py_DEBUG", warn)
    has_refcount = hasattr(sys, "gettotalrefcount")
    # Windows doesn't set Py_DEBUG, so checking for support of debug-compiled
    # extension modules is the best option.
    # https://github.com/pypa/pip/issues/3383#issuecomment-173267692
    has_ext = "_d.pyd" in EXTENSION_SUFFIXES
    if with_debug or (with_debug is None and (has_refcount or has_ext)):
        debug = "d"
    if py_version >= (3, 13) and _get_config_var("Py_GIL_DISABLED", warn):
        threading = "t"
    if py_version < (3, 8):
        with_pymalloc = _get_config_var("WITH_PYMALLOC", warn)
        if with_pymalloc or with_pymalloc is None:
            pymalloc = "m"
        if py_version < (3, 3):
            unicode_size = _get_config_var("Py_UNICODE_SIZE", warn)
            if unicode_size == 4 or (
                unicode_size is None and sys.maxunicode == 0x10FFFF
            ):
                ucs4 = "u"
    elif debug:
        # Debug builds can also load "normal" extension modules.
        # We can also assume no UCS-4 or pymalloc requirement.
        abis.append(f"cp{version}{threading}")
    abis.insert(0, f"cp{version}{threading}{debug}{pymalloc}{ucs4}")
    return abis


def cpython_tags(
    python_version: PythonVersion | None = None,
    abis: Iterable[str] | None = None,
    platforms: Iterable[str] | None = None,
    *,
    warn: bool = False,
) -> Iterator[Tag]:
    """
    Yields the tags for a CPython interpreter.

    The tags consist of:
    - cp<python_version>-<abi>-<platform>
    - cp<python_version>-abi3-<platform>
    - cp<python_version>-none-<platform>
    - cp<less than python_version>-abi3-<platform>  # Older Python versions down to 3.2.

    If python_version only specifies a major version then user-provided ABIs and
    the 'none' ABItag will be used.

    If 'abi3' or 'none' are specified in 'abis' then they will be yielded at
    their normal position and not at the beginning.
    """
    if not python_version:
        python_version = sys.version_info[:2]

    interpreter = f"cp{_version_nodot(python_version[:2])}"

    if abis is None:
        if len(python_version) > 1:
            abis = _cpython_abis(python_version, warn)
        else:
            abis = []
    abis = list(abis)
    # 'abi3' and 'none' are explicitly handled later.
    for explicit_abi in ("abi3", "none"):
        try:
            abis.remove(explicit_abi)
        except ValueError:
            pass

    platforms = list(platforms or platform_tags())
    for abi in abis:
        for platform_ in platforms:
            yield Tag(interpreter, abi, platform_)

    threading = _is_threaded_cpython(abis)
    use_abi3 = _abi3_applies(python_version, threading)
    if use_abi3:
        yield from (Tag(interpreter, "abi3", platform_) for platform_ in platforms)
    yield from (Tag(interpreter, "none", platform_) for platform_ in platforms)

    if use_abi3:
        for minor_version in range(python_version[1] - 1, 1, -1):
            for platform_ in platforms:
                version = _version_nodot((python_version[0], minor_version))
                interpreter = f"cp{version}"
                yield Tag(interpreter, "abi3", platform_)


def _generic_abi() -> list[str]:
    """
    Return the ABI tag based on EXT_SUFFIX.
    """
    # The following are examples of `EXT_SUFFIX`.
    # We want to keep the parts which are related to the ABI and remove the
    # parts which are related to the platform:
    # - linux:   '.cpython-310-x86_64-linux-gnu.so' => cp310
    # - mac:     '.cpython-310-darwin.so'           => cp310
    # - win:     '.cp310-win_amd64.pyd'             => cp310
    # - win:     '.pyd'                             => cp37 (uses _cpython_abis())
    # - pypy:    '.pypy38-pp73-x86_64-linux-gnu.so' => pypy38_pp73
    # - graalpy: '.graalpy-38-native-x86_64-darwin.dylib'
    #                                               => graalpy_38_native

    ext_suffix = _get_config_var("EXT_SUFFIX", warn=True)
    if not isinstance(ext_suffix, str) or ext_suffix[0] != ".":
        raise SystemError("invalid sysconfig.get_config_var('EXT_SUFFIX')")
    parts = ext_suffix.split(".")
    if len(parts) < 3:
        # CPython3.7 and earlier uses ".pyd" on Windows.
        return _cpython_abis(sys.version_info[:2])
    soabi = parts[1]
    if soabi.startswith("cpython"):
        # non-windows
        abi = "cp" + soabi.split("-")[1]
    elif soabi.startswith("cp"):
        # windows
        abi = soabi.split("-")[0]
    elif soabi.startswith("pypy"):
        abi = "-".join(soabi.split("-")[:2])
    elif soabi.startswith("graalpy"):
        abi = "-".join(soabi.split("-")[:3])
    elif soabi:
        # pyston, ironpython, others?
        abi = soabi
    else:
        return []
    return [_normalize_string(abi)]


def generic_tags(
    interpreter: str | None = None,
    abis: Iterable[str] | None = None,
    platforms: Iterable[str] | None = None,
    *,
    warn: bool = False,
) -> Iterator[Tag]:
    """
    Yields the tags for a generic interpreter.

    The tags consist of:
    - <interpreter>-<abi>-<platform>

    The "none" ABI will be added if it was not explicitly provided.
    """
    if not interpreter:
        interp_name = interpreter_name()
        interp_version = interpreter_version(warn=warn)
        interpreter = "".join([interp_name, interp_version])
    if abis is None:
        abis = _generic_abi()
    else:
        abis = list(abis)
    platforms = list(platforms or platform_tags())
    if "none" not in abis:
        abis.append("none")
    for abi in abis:
        for platform_ in platforms:
            yield Tag(interpreter, abi, platform_)


def _py_interpreter_range(py_version: PythonVersion) -> Iterator[str]:
    """
    Yields Python versions in descending order.

    After the latest version, the major-only version will be yielded, and then
    all previous versions of that major version.
    """
    if len(py_version) > 1:
        yield f"py{_version_nodot(py_version[:2])}"
    yield f"py{py_version[0]}"
    if len(py_version) > 1:
        for minor in range(py_version[1] - 1, -1, -1):
            yield f"py{_version_nodot((py_version[0], minor))}"


def compatible_tags(
    python_version: PythonVersion | None = None,
    interpreter: str | None = None,
    platforms: Iterable[str] | None = None,
) -> Iterator[Tag]:
    """
    Yields the sequence of tags that are compatible with a specific version of Python.

    The tags consist of:
    - py*-none-<platform>
    - <interpreter>-none-any  # ... if `interpreter` is provided.
    - py*-none-any
    """
    if not python_version:
        python_version = sys.version_info[:2]
    platforms = list(platforms or platform_tags())
    for version in _py_interpreter_range(python_version):
        for platform_ in platforms:
            yield Tag(version, "none", platform_)
    if interpreter:
        yield Tag(interpreter, "none", "any")
    for version in _py_interpreter_range(python_version):
        yield Tag(version, "none", "any")


def _mac_arch(arch: str, is_32bit: bool = _32_BIT_INTERPRETER) -> str:
    if not is_32bit:
        return arch

    if arch.startswith("ppc"):
        return "ppc"

    return "i386"


def _mac_binary_formats(version: AppleVersion, cpu_arch: str) -> list[str]:
    formats = [cpu_arch]
    if cpu_arch == "x86_64":
        if version < (10, 4):
            return []
        formats.extend(["intel", "fat64", "fat32"])

    elif cpu_arch == "i386":
        if version < (10, 4):
            return []
        formats.extend(["intel", "fat32", "fat"])

    elif cpu_arch == "ppc64":
        # TODO: Need to care about 32-bit PPC for ppc64 through 10.2?
        if version > (10, 5) or version < (10, 4):
            return []
        formats.append("fat64")

    elif cpu_arch == "ppc":
        if version > (10, 6):
            return []
        formats.extend(["fat32", "fat"])

    if cpu_arch in {"arm64", "x86_64"}:
        formats.append("universal2")

    if cpu_arch in {"x86_64", "i386", "ppc64", "ppc", "intel"}:
        formats.append("universal")

    return formats


def mac_platforms(
    version: AppleVersion | None = None, arch: str | None = None
) -> Iterator[str]:
    """
    Yields the platform tags for a macOS system.

    The `version` parameter is a two-item tuple specifying the macOS version to
    generate platform tags for. The `arch` parameter is the CPU architecture to
    generate platform tags for. Both parameters default to the appropriate value
    for the current system.
    """
    version_str, _, cpu_arch = platform.mac_ver()
    if version is None:
        version = cast("AppleVersion", tuple(map(int, version_str.split(".")[:2])))
        if version == (10, 16):
            # When built against an older macOS SDK, Python will report macOS 10.16
            # instead of the real version.
            version_str = subprocess.run(
                [
                    sys.executable,
                    "-sS",
                    "-c",
                    "import platform; print(platform.mac_ver()[0])",
                ],
                check=True,
                env={"SYSTEM_VERSION_COMPAT": "0"},
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            version = cast("AppleVersion", tuple(map(int, version_str.split(".")[:2])))
    else:
        version = version
    if arch is None:
        arch = _mac_arch(cpu_arch)
    else:
        arch = arch

    if (10, 0) <= version and version < (11, 0):
        # Prior to Mac OS 11, each yearly release of Mac OS bumped the
        # "minor" version number.  The major version was always 10.
        major_version = 10
        for minor_version in range(version[1], -1, -1):
            compat_version = major_version, minor_version
            binary_formats = _mac_binary_formats(compat_version, arch)
            for binary_format in binary_formats:
                yield f"macosx_{major_version}_{minor_version}_{binary_format}"

    if version >= (11, 0):
        # Starting with Mac OS 11, each yearly release bumps the major version
        # number.   The minor versions are now the midyear updates.
        minor_version = 0
        for major_version in range(version[0], 10, -1):
            compat_version = major_version, minor_version
            binary_formats = _mac_binary_formats(compat_version, arch)
            for binary_format in binary_formats:
                yield f"macosx_{major_version}_{minor_version}_{binary_format}"

    if version >= (11, 0):
        # Mac OS 11 on x86_64 is compatible with binaries from previous releases.
        # Arm64 support was introduced in 11.0, so no Arm binaries from previous
        # releases exist.
        #
        # However, the "universal2" binary format can have a
        # macOS version earlier than 11.0 when the x86_64 part of the binary supports
        # that version of macOS.
        major_version = 10
        if arch == "x86_64":
            for minor_version in range(16, 3, -1):
                compat_version = major_version, minor_version
                binary_formats = _mac_binary_formats(compat_version, arch)
                for binary_format in binary_formats:
                    yield f"macosx_{major_version}_{minor_version}_{binary_format}"
        else:
            for minor_version in range(16, 3, -1):
                compat_version = major_version, minor_version
                binary_format = "universal2"
                yield f"macosx_{major_version}_{minor_version}_{binary_format}"


def ios_platforms(
    version: AppleVersion | None = None, multiarch: str | None = None
) -> Iterator[str]:
    """
    Yields the platform tags for an iOS system.

    :param version: A two-item tuple specifying the iOS version to generate
        platform tags for. Defaults to the current iOS version.
    :param multiarch: The CPU architecture+ABI to generate platform tags for -
        (the value used by `sys.implementation._multiarch` e.g.,
        `arm64_iphoneos` or `x84_64_iphonesimulator`). Defaults to the current
        multiarch value.
    """
    if version is None:
        # if iOS is the current platform, ios_ver *must* be defined. However,
        # it won't exist for CPython versions before 3.13, which causes a mypy
        # error.
        _, release, _, _ = platform.ios_ver()  # type: ignore[attr-defined, unused-ignore]
        version = cast("AppleVersion", tuple(map(int, release.split(".")[:2])))

    if multiarch is None:
        multiarch = sys.implementation._multiarch
    multiarch = multiarch.replace("-", "_")

    ios_platform_template = "ios_{major}_{minor}_{multiarch}"

    # Consider any iOS major.minor version from the version requested, down to
    # 12.0. 12.0 is the first iOS version that is known to have enough features
    # to support CPython. Consider every possible minor release up to X.9. There
    # highest the minor has ever gone is 8 (14.8 and 15.8) but having some extra
    # candidates that won't ever match doesn't really hurt, and it saves us from
    # having to keep an explicit list of known iOS versions in the code. Return
    # the results descending order of version number.

    # If the requested major version is less than 12, there won't be any matches.
    if version[0] < 12:
        return

    # Consider the actual X.Y version that was requested.
    yield ios_platform_template.format(
        major=version[0], minor=version[1], multiarch=multiarch
    )

    # Consider every minor version from X.0 to the minor version prior to the
    # version requested by the platform.
    for minor in range(version[1] - 1, -1, -1):
        yield ios_platform_template.format(
            major=version[0], minor=minor, multiarch=multiarch
        )

    for major in range(version[0] - 1, 11, -1):
        for minor in range(9, -1, -1):
            yield ios_platform_template.format(
                major=major, minor=minor, multiarch=multiarch
            )


def android_platforms(
    api_level: int | None = None, abi: str | None = None
) -> Iterator[str]:
    """
    Yields the :attr:`~Tag.platform` tags for Android. If this function is invoked on
    non-Android platforms, the ``api_level`` and ``abi`` arguments are required.

    :param int api_level: The maximum `API level
        <https://developer.android.com/tools/releases/platforms>`__ to return. Defaults
        to the current system's version, as returned by ``platform.android_ver``.
    :param str abi: The `Android ABI <https://developer.android.com/ndk/guides/abis>`__,
        e.g. ``arm64_v8a``. Defaults to the current system's ABI , as returned by
        ``sysconfig.get_platform``. Hyphens and periods will be replaced with
        underscores.
    """
    if platform.system() != "Android" and (api_level is None or abi is None):
        raise TypeError(
            "on non-Android platforms, the api_level and abi arguments are required"
        )

    if api_level is None:
        # Python 3.13 was the first version to return platform.system() == "Android",
        # and also the first version to define platform.android_ver().
        api_level = platform.android_ver().api_level  # type: ignore[attr-defined]

    if abi is None:
        abi = sysconfig.get_platform().split("-")[-1]
    abi = _normalize_string(abi)

    # 16 is the minimum API level known to have enough features to support CPython
    # without major patching. Yield every API level from the maximum down to the
    # minimum, inclusive.
    min_api_level = 16
    for ver in range(api_level, min_api_level - 1, -1):
        yield f"android_{ver}_{abi}"


def _linux_platforms(is_32bit: bool = _32_BIT_INTERPRETER) -> Iterator[str]:
    linux = _normalize_string(sysconfig.get_platform())
    if not linux.startswith("linux_"):
        # we should never be here, just yield the sysconfig one and return
        yield linux
        return
    if is_32bit:
        if linux == "linux_x86_64":
            linux = "linux_i686"
        elif linux == "linux_aarch64":
            linux = "linux_armv8l"
    _, arch = linux.split("_", 1)
    archs = {"armv8l": ["armv8l", "armv7l"]}.get(arch, [arch])
    yield from _manylinux.platform_tags(archs)
    yield from _musllinux.platform_tags(archs)
    for arch in archs:
        yield f"linux_{arch}"


def _generic_platforms() -> Iterator[str]:
    yield _normalize_string(sysconfig.get_platform())


def platform_tags() -> Iterator[str]:
    """
    Provides the platform tags for this installation.
    """
    if platform.system() == "Darwin":
        return mac_platforms()
    elif platform.system() == "iOS":
        return ios_platforms()
    elif platform.system() == "Android":
        return android_platforms()
    elif platform.system() == "Linux":
        return _linux_platforms()
    else:
        return _generic_platforms()


def interpreter_name() -> str:
    """
    Returns the name of the running interpreter.

    Some implementations have a reserved, two-letter abbreviation which will
    be returned when appropriate.
    """
    name = sys.implementation.name
    return INTERPRETER_SHORT_NAMES.get(name) or name


def interpreter_version(*, warn: bool = False) -> str:
    """
    Returns the version of the running interpreter.
    """
    version = _get_config_var("py_version_nodot", warn=warn)
    if version:
        version = str(version)
    else:
        version = _version_nodot(sys.version_info[:2])
    return version


def _version_nodot(version: PythonVersion) -> str:
    return "".join(map(str, version))


def sys_tags(*, warn: bool = False) -> Iterator[Tag]:
    """
    Returns the sequence of tag triples for the running interpreter.

    The order of the sequence corresponds to priority order for the
    interpreter, from most to least important.
    """

    interp_name = interpreter_name()
    if interp_name == "cp":
        yield from cpython_tags(warn=warn)
    else:
        yield from generic_tags()

    if interp_name == "pp":
        interp = "pp3"
    elif interp_name == "cp":
        interp = "cp" + interpreter_version(warn=warn)
    else:
        interp = None
    yield from compatible_tags(interpreter=interp)