
# === NexusCore/openenv\Lib\site-packages\ipykernel\iostream.py ===
"""Wrappers for forwarding stdout/stderr over zmq"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import asyncio
import atexit
import contextvars
import io
import os
import sys
import threading
import traceback
import warnings
from binascii import b2a_hex
from collections import defaultdict, deque
from io import StringIO, TextIOBase
from threading import local
from typing import Any, Callable, Deque, Dict, Optional

import zmq
from jupyter_client.session import extract_header
from tornado.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

MASTER = 0
CHILD = 1

PIPE_BUFFER_SIZE = 1000

# -----------------------------------------------------------------------------
# IO classes
# -----------------------------------------------------------------------------


class IOPubThread:
    """An object for sending IOPub messages in a background thread

    Prevents a blocking main thread from delaying output from threads.

    IOPubThread(pub_socket).background_socket is a Socket-API-providing object
    whose IO is always run in a thread.
    """

    def __init__(self, socket, pipe=False):
        """Create IOPub thread

        Parameters
        ----------
        socket : zmq.PUB Socket
            the socket on which messages will be sent.
        pipe : bool
            Whether this process should listen for IOPub messages
            piped from subprocesses.
        """
        self.socket = socket
        self._stopped = False
        self.background_socket = BackgroundSocket(self)
        self._master_pid = os.getpid()
        self._pipe_flag = pipe
        self.io_loop = IOLoop(make_current=False)
        if pipe:
            self._setup_pipe_in()
        self._local = threading.local()
        self._events: Deque[Callable[..., Any]] = deque()
        self._event_pipes: Dict[threading.Thread, Any] = {}
        self._event_pipe_gc_lock: threading.Lock = threading.Lock()
        self._event_pipe_gc_seconds: float = 10
        self._event_pipe_gc_task: Optional[asyncio.Task[Any]] = None
        self._setup_event_pipe()
        self.thread = threading.Thread(target=self._thread_main, name="IOPub")
        self.thread.daemon = True
        self.thread.pydev_do_not_trace = True  # type:ignore[attr-defined]
        self.thread.is_pydev_daemon_thread = True  # type:ignore[attr-defined]
        self.thread.name = "IOPub"

    def _thread_main(self):
        """The inner loop that's actually run in a thread"""

        def _start_event_gc():
            self._event_pipe_gc_task = asyncio.ensure_future(self._run_event_pipe_gc())

        self.io_loop.run_sync(_start_event_gc)

        if not self._stopped:
            # avoid race if stop called before start thread gets here
            # probably only comes up in tests
            self.io_loop.start()

        if self._event_pipe_gc_task is not None:
            # cancel gc task to avoid pending task warnings
            async def _cancel():
                self._event_pipe_gc_task.cancel()  # type:ignore[union-attr]

            if not self._stopped:
                self.io_loop.run_sync(_cancel)
            else:
                self._event_pipe_gc_task.cancel()

        self.io_loop.close(all_fds=True)

    def _setup_event_pipe(self):
        """Create the PULL socket listening for events that should fire in this thread."""
        ctx = self.socket.context
        pipe_in = ctx.socket(zmq.PULL)
        pipe_in.linger = 0

        _uuid = b2a_hex(os.urandom(16)).decode("ascii")
        iface = self._event_interface = "inproc://%s" % _uuid
        pipe_in.bind(iface)
        self._event_puller = ZMQStream(pipe_in, self.io_loop)
        self._event_puller.on_recv(self._handle_event)

    async def _run_event_pipe_gc(self):
        """Task to run event pipe gc continuously"""
        while True:
            await asyncio.sleep(self._event_pipe_gc_seconds)
            try:
                await self._event_pipe_gc()
            except Exception as e:
                print(f"Exception in IOPubThread._event_pipe_gc: {e}", file=sys.__stderr__)

    async def _event_pipe_gc(self):
        """run a single garbage collection on event pipes"""
        if not self._event_pipes:
            # don't acquire the lock if there's nothing to do
            return
        with self._event_pipe_gc_lock:
            for thread, socket in list(self._event_pipes.items()):
                if not thread.is_alive():
                    socket.close()
                    del self._event_pipes[thread]

    @property
    def _event_pipe(self):
        """thread-local event pipe for signaling events that should be processed in the thread"""
        try:
            event_pipe = self._local.event_pipe
        except AttributeError:
            # new thread, new event pipe
            ctx = self.socket.context
            event_pipe = ctx.socket(zmq.PUSH)
            event_pipe.linger = 0
            event_pipe.connect(self._event_interface)
            self._local.event_pipe = event_pipe
            # associate event pipes to their threads
            # so they can be closed explicitly
            # implicit close on __del__ throws a ResourceWarning
            with self._event_pipe_gc_lock:
                self._event_pipes[threading.current_thread()] = event_pipe
        return event_pipe

    def _handle_event(self, msg):
        """Handle an event on the event pipe

        Content of the message is ignored.

        Whenever *an* event arrives on the event stream,
        *all* waiting events are processed in order.
        """
        # freeze event count so new writes don't extend the queue
        # while we are processing
        n_events = len(self._events)
        for _ in range(n_events):
            event_f = self._events.popleft()
            event_f()

    def _setup_pipe_in(self):
        """setup listening pipe for IOPub from forked subprocesses"""
        ctx = self.socket.context

        # use UUID to authenticate pipe messages
        self._pipe_uuid = os.urandom(16)

        pipe_in = ctx.socket(zmq.PULL)
        pipe_in.linger = 0

        try:
            self._pipe_port = pipe_in.bind_to_random_port("tcp://127.0.0.1")
        except zmq.ZMQError as e:
            warnings.warn(
                "Couldn't bind IOPub Pipe to 127.0.0.1: %s" % e
                + "\nsubprocess output will be unavailable.",
                stacklevel=2,
            )
            self._pipe_flag = False
            pipe_in.close()
            return
        self._pipe_in = ZMQStream(pipe_in, self.io_loop)
        self._pipe_in.on_recv(self._handle_pipe_msg)

    def _handle_pipe_msg(self, msg):
        """handle a pipe message from a subprocess"""
        if not self._pipe_flag or not self._is_master_process():
            return
        if msg[0] != self._pipe_uuid:
            print("Bad pipe message: %s", msg, file=sys.__stderr__)
            return
        self.send_multipart(msg[1:])

    def _setup_pipe_out(self):
        # must be new context after fork
        ctx = zmq.Context()
        pipe_out = ctx.socket(zmq.PUSH)
        pipe_out.linger = 3000  # 3s timeout for pipe_out sends before discarding the message
        pipe_out.connect("tcp://127.0.0.1:%i" % self._pipe_port)
        return ctx, pipe_out

    def _is_master_process(self):
        return os.getpid() == self._master_pid

    def _check_mp_mode(self):
        """check for forks, and switch to zmq pipeline if necessary"""
        if not self._pipe_flag or self._is_master_process():
            return MASTER
        return CHILD

    def start(self):
        """Start the IOPub thread"""
        self.thread.name = "IOPub"
        self.thread.start()
        # make sure we don't prevent process exit
        # I'm not sure why setting daemon=True above isn't enough, but it doesn't appear to be.
        atexit.register(self.stop)

    def stop(self):
        """Stop the IOPub thread"""
        self._stopped = True
        if not self.thread.is_alive():
            return
        self.io_loop.add_callback(self.io_loop.stop)

        self.thread.join(timeout=30)
        if self.thread.is_alive():
            # avoid infinite hang if stop fails
            msg = "IOPub thread did not terminate in 30 seconds"
            raise TimeoutError(msg)
        # close *all* event pipes, created in any thread
        # event pipes can only be used from other threads while self.thread.is_alive()
        # so after thread.join, this should be safe
        for _thread, event_pipe in self._event_pipes.items():
            event_pipe.close()

    def close(self):
        """Close the IOPub thread."""
        if self.closed:
            return
        self.socket.close()
        self.socket = None

    @property
    def closed(self):
        return self.socket is None

    def schedule(self, f):
        """Schedule a function to be called in our IO thread.

        If the thread is not running, call immediately.
        """
        if self.thread.is_alive():
            self._events.append(f)
            # wake event thread (message content is ignored)
            self._event_pipe.send(b"")
        else:
            f()

    def send_multipart(self, *args, **kwargs):
        """send_multipart schedules actual zmq send in my thread.

        If my thread isn't running (e.g. forked process), send immediately.
        """
        self.schedule(lambda: self._really_send(*args, **kwargs))

    def _really_send(self, msg, *args, **kwargs):
        """The callback that actually sends messages"""
        if self.closed:
            return

        mp_mode = self._check_mp_mode()

        if mp_mode != CHILD:
            # we are master, do a regular send
            self.socket.send_multipart(msg, *args, **kwargs)
        else:
            # we are a child, pipe to master
            # new context/socket for every pipe-out
            # since forks don't teardown politely, use ctx.term to ensure send has completed
            ctx, pipe_out = self._setup_pipe_out()
            pipe_out.send_multipart([self._pipe_uuid, *msg], *args, **kwargs)
            pipe_out.close()
            ctx.term()


class BackgroundSocket:
    """Wrapper around IOPub thread that provides zmq send[_multipart]"""

    io_thread = None

    def __init__(self, io_thread):
        """Initialize the socket."""
        self.io_thread = io_thread

    def __getattr__(self, attr):
        """Wrap socket attr access for backward-compatibility"""
        if attr.startswith("__") and attr.endswith("__"):
            # don't wrap magic methods
            super().__getattr__(attr)  # type:ignore[misc]
        assert self.io_thread is not None
        if hasattr(self.io_thread.socket, attr):
            warnings.warn(
                f"Accessing zmq Socket attribute {attr} on BackgroundSocket"
                f" is deprecated since ipykernel 4.3.0"
                f" use .io_thread.socket.{attr}",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(self.io_thread.socket, attr)
        return super().__getattr__(attr)  # type:ignore[misc]

    def __setattr__(self, attr, value):
        """Set an attribute on the socket."""
        if attr == "io_thread" or (attr.startswith("__") and attr.endswith("__")):
            super().__setattr__(attr, value)
        else:
            warnings.warn(
                f"Setting zmq Socket attribute {attr} on BackgroundSocket"
                f" is deprecated since ipykernel 4.3.0"
                f" use .io_thread.socket.{attr}",
                DeprecationWarning,
                stacklevel=2,
            )
            assert self.io_thread is not None
            setattr(self.io_thread.socket, attr, value)

    def send(self, msg, *args, **kwargs):
        """Send a message to the socket."""
        return self.send_multipart([msg], *args, **kwargs)

    def send_multipart(self, *args, **kwargs):
        """Schedule send in IO thread"""
        assert self.io_thread is not None
        return self.io_thread.send_multipart(*args, **kwargs)


class OutStream(TextIOBase):
    """A file like object that publishes the stream to a 0MQ PUB socket.

    Output is handed off to an IO Thread
    """

    # timeout for flush to avoid infinite hang
    # in case of misbehavior
    flush_timeout = 10
    # The time interval between automatic flushes, in seconds.
    flush_interval = 0.2
    topic = None
    encoding = "UTF-8"
    _exc: Optional[Any] = None

    def fileno(self):
        """
        Things like subprocess will peak and write to the fileno() of stderr/stdout.
        """
        if getattr(self, "_original_stdstream_copy", None) is not None:
            return self._original_stdstream_copy
        msg = "fileno"
        raise io.UnsupportedOperation(msg)

    def _watch_pipe_fd(self):
        """
        We've redirected standards streams 0 and 1 into a pipe.

        We need to watch in a thread and redirect them to the right places.

        1) the ZMQ channels to show in notebook interfaces,
        2) the original stdout/err, to capture errors in terminals.

        We cannot schedule this on the ioloop thread, as this might be blocking.

        """

        try:
            bts = os.read(self._fid, PIPE_BUFFER_SIZE)
            while bts and self._should_watch:
                self.write(bts.decode(errors="replace"))
                os.write(self._original_stdstream_copy, bts)
                bts = os.read(self._fid, PIPE_BUFFER_SIZE)
        except Exception:
            self._exc = sys.exc_info()

    def __init__(
        self,
        session,
        pub_thread,
        name,
        pipe=None,
        echo=None,
        *,
        watchfd=True,
        isatty=False,
    ):
        """
        Parameters
        ----------
        session : object
            the session object
        pub_thread : threading.Thread
            the publication thread
        name : str {'stderr', 'stdout'}
            the name of the standard stream to replace
        pipe : object
            the pipe object
        echo : bool
            whether to echo output
        watchfd : bool (default, True)
            Watch the file descriptor corresponding to the replaced stream.
            This is useful if you know some underlying code will write directly
            the file descriptor by its number. It will spawn a watching thread,
            that will swap the give file descriptor for a pipe, read from the
            pipe, and insert this into the current Stream.
        isatty : bool (default, False)
            Indication of whether this stream has terminal capabilities (e.g. can handle colors)

        """
        if pipe is not None:
            warnings.warn(
                "pipe argument to OutStream is deprecated and ignored since ipykernel 4.2.3.",
                DeprecationWarning,
                stacklevel=2,
            )
        # This is necessary for compatibility with Python built-in streams
        self.session = session
        if not isinstance(pub_thread, IOPubThread):
            # Backward-compat: given socket, not thread. Wrap in a thread.
            warnings.warn(
                "Since IPykernel 4.3, OutStream should be created with "
                "IOPubThread, not %r" % pub_thread,
                DeprecationWarning,
                stacklevel=2,
            )
            pub_thread = IOPubThread(pub_thread)
            pub_thread.start()
        self.pub_thread = pub_thread
        self.name = name
        self.topic = b"stream." + name.encode()
        self._parent_header: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
            "parent_header"
        )
        self._parent_header.set({})
        self._thread_to_parent = {}
        self._thread_to_parent_header = {}
        self._parent_header_global = {}
        self._master_pid = os.getpid()
        self._flush_pending = False
        self._subprocess_flush_pending = False
        self._io_loop = pub_thread.io_loop
        self._buffer_lock = threading.RLock()
        self._buffers = defaultdict(StringIO)
        self.echo = None
        self._isatty = bool(isatty)
        self._should_watch = False
        self._local = local()

        if (
            watchfd
            and (
                (sys.platform.startswith("linux") or sys.platform.startswith("darwin"))
                # Pytest set its own capture. Don't redirect from within pytest.
                and ("PYTEST_CURRENT_TEST" not in os.environ)
            )
            # allow forcing watchfd (mainly for tests)
            or watchfd == "force"
        ):
            self._should_watch = True
            self._setup_stream_redirects(name)

        if echo:
            if hasattr(echo, "read") and hasattr(echo, "write"):
                # make sure we aren't trying to echo on the FD we're watching!
                # that would cause an infinite loop, always echoing on itself
                if self._should_watch:
                    try:
                        echo_fd = echo.fileno()
                    except Exception:
                        echo_fd = None

                    if echo_fd is not None and echo_fd == self._original_stdstream_fd:
                        # echo on the _copy_ we made during
                        # this is the actual terminal FD now
                        echo = io.TextIOWrapper(
                            io.FileIO(
                                self._original_stdstream_copy,
                                "w",
                            )
                        )
                self.echo = echo
            else:
                msg = "echo argument must be a file-like object"
                raise ValueError(msg)

    @property
    def parent_header(self):
        try:
            # asyncio-specific
            return self._parent_header.get()
        except LookupError:
            try:
                # thread-specific
                identity = threading.current_thread().ident
                # retrieve the outermost (oldest ancestor,
                # discounting the kernel thread) thread identity
                while identity in self._thread_to_parent:
                    identity = self._thread_to_parent[identity]
                # use the header of the oldest ancestor
                return self._thread_to_parent_header[identity]
            except KeyError:
                # global (fallback)
                return self._parent_header_global

    @parent_header.setter
    def parent_header(self, value):
        self._parent_header_global = value
        return self._parent_header.set(value)

    def isatty(self):
        """Return a bool indicating whether this is an 'interactive' stream.

        Returns:
            Boolean
        """
        return self._isatty

    def _setup_stream_redirects(self, name):
        pr, pw = os.pipe()
        fno = self._original_stdstream_fd = getattr(sys, name).fileno()
        self._original_stdstream_copy = os.dup(fno)
        os.dup2(pw, fno)

        self._fid = pr

        self._exc = None
        self.watch_fd_thread = threading.Thread(target=self._watch_pipe_fd)
        self.watch_fd_thread.daemon = True
        self.watch_fd_thread.start()

    def _is_master_process(self):
        return os.getpid() == self._master_pid

    def set_parent(self, parent):
        """Set the parent header."""
        self.parent_header = extract_header(parent)

    def close(self):
        """Close the stream."""
        if self._should_watch:
            self._should_watch = False
            # thread won't wake unless there's something to read
            # writing something after _should_watch will not be echoed
            os.write(self._original_stdstream_fd, b"\0")
            self.watch_fd_thread.join()
            # restore original FDs
            os.dup2(self._original_stdstream_copy, self._original_stdstream_fd)
            os.close(self._original_stdstream_copy)
        if self._exc:
            etype, value, tb = self._exc
            traceback.print_exception(etype, value, tb)
        self.pub_thread = None

    @property
    def closed(self):
        return self.pub_thread is None

    def _schedule_flush(self):
        """schedule a flush in the IO thread

        call this on write, to indicate that flush should be called soon.
        """
        if self._flush_pending:
            return
        self._flush_pending = True

        # add_timeout has to be handed to the io thread via event pipe
        def _schedule_in_thread():
            self._io_loop.call_later(self.flush_interval, self._flush)

        self.pub_thread.schedule(_schedule_in_thread)

    def flush(self):
        """trigger actual zmq send

        send will happen in the background thread
        """
        if (
            self.pub_thread
            and self.pub_thread.thread is not None
            and self.pub_thread.thread.is_alive()
            and self.pub_thread.thread.ident != threading.current_thread().ident
        ):
            # request flush on the background thread
            self.pub_thread.schedule(self._flush)
            # wait for flush to actually get through, if we can.
            evt = threading.Event()
            self.pub_thread.schedule(evt.set)
            # and give a timeout to avoid
            if not evt.wait(self.flush_timeout):
                # write directly to __stderr__ instead of warning because
                # if this is happening sys.stderr may be the problem.
                print("IOStream.flush timed out", file=sys.__stderr__)
        else:
            self._flush()

    def _flush(self):
        """This is where the actual send happens.

        _flush should generally be called in the IO thread,
        unless the thread has been destroyed (e.g. forked subprocess).
        """
        self._flush_pending = False
        self._subprocess_flush_pending = False

        if self.echo is not None:
            try:
                self.echo.flush()
            except OSError as e:
                if self.echo is not sys.__stderr__:
                    print(f"Flush failed: {e}", file=sys.__stderr__)

        for parent, data in self._flush_buffers():
            if data:
                # FIXME: this disables Session's fork-safe check,
                # since pub_thread is itself fork-safe.
                # There should be a better way to do this.
                self.session.pid = os.getpid()
                content = {"name": self.name, "text": data}
                msg = self.session.msg("stream", content, parent=parent)

                # Each transform either returns a new
                # message or None. If None is returned,
                # the message has been 'used' and we return.
                for hook in self._hooks:
                    msg = hook(msg)
                    if msg is None:
                        return

                self.session.send(
                    self.pub_thread,
                    msg,
                    ident=self.topic,
                )

    def write(self, string: str) -> Optional[int]:  # type:ignore[override]
        """Write to current stream after encoding if necessary

        Returns
        -------
        len : int
            number of items from input parameter written to stream.

        """
        parent = self.parent_header

        if not isinstance(string, str):
            msg = f"write() argument must be str, not {type(string)}"  # type:ignore[unreachable]
            raise TypeError(msg)

        if self.echo is not None:
            try:
                self.echo.write(string)
            except OSError as e:
                if self.echo is not sys.__stderr__:
                    print(f"Write failed: {e}", file=sys.__stderr__)

        if self.pub_thread is None:
            msg = "I/O operation on closed file"
            raise ValueError(msg)

        is_child = not self._is_master_process()
        # only touch the buffer in the IO thread to avoid races
        with self._buffer_lock:
            self._buffers[frozenset(parent.items())].write(string)
        if is_child:
            # mp.Pool cannot be trusted to flush promptly (or ever),
            # and this helps.
            if self._subprocess_flush_pending:
                return None
            self._subprocess_flush_pending = True
            # We can not rely on self._io_loop.call_later from a subprocess
            self.pub_thread.schedule(self._flush)
        else:
            self._schedule_flush()

        return len(string)

    def writelines(self, sequence):
        """Write lines to the stream."""
        if self.pub_thread is None:
            msg = "I/O operation on closed file"
            raise ValueError(msg)
        for string in sequence:
            self.write(string)

    def writable(self):
        """Test whether the stream is writable."""
        return True

    def _flush_buffers(self):
        """clear the current buffer and return the current buffer data."""
        buffers = self._rotate_buffers()
        for frozen_parent, buffer in buffers.items():
            data = buffer.getvalue()
            buffer.close()
            yield dict(frozen_parent), data

    def _rotate_buffers(self):
        """Returns the current buffer and replaces it with an empty buffer."""
        with self._buffer_lock:
            old_buffers = self._buffers
            self._buffers = defaultdict(StringIO)
        return old_buffers

    @property
    def _hooks(self):
        if not hasattr(self._local, "hooks"):
            # create new list for a new thread
            self._local.hooks = []
        return self._local.hooks

    def register_hook(self, hook):
        """
        Registers a hook with the thread-local storage.

        Parameters
        ----------
        hook : Any callable object

        Returns
        -------
        Either a publishable message, or `None`.
        The hook callable must return a message from
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

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\validators.py ===
import math
import re
from collections import OrderedDict, deque
from collections.abc import Hashable as CollectionsHashable
from datetime import date, datetime, time, timedelta
from decimal import Decimal, DecimalException
from enum import Enum, IntEnum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Deque,
    Dict,
    ForwardRef,
    FrozenSet,
    Generator,
    Hashable,
    List,
    NamedTuple,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID
from warnings import warn

from pydantic.v1 import errors
from pydantic.v1.datetime_parse import parse_date, parse_datetime, parse_duration, parse_time
from pydantic.v1.typing import (
    AnyCallable,
    all_literal_values,
    display_as_type,
    get_class,
    is_callable_type,
    is_literal_type,
    is_namedtuple,
    is_none_type,
    is_typeddict,
)
from pydantic.v1.utils import almost_equal_floats, lenient_issubclass, sequence_like

if TYPE_CHECKING:
    from typing_extensions import Literal, TypedDict

    from pydantic.v1.config import BaseConfig
    from pydantic.v1.fields import ModelField
    from pydantic.v1.types import ConstrainedDecimal, ConstrainedFloat, ConstrainedInt

    ConstrainedNumber = Union[ConstrainedDecimal, ConstrainedFloat, ConstrainedInt]
    AnyOrderedDict = OrderedDict[Any, Any]
    Number = Union[int, float, Decimal]
    StrBytes = Union[str, bytes]


def str_validator(v: Any) -> Union[str]:
    if isinstance(v, str):
        if isinstance(v, Enum):
            return v.value
        else:
            return v
    elif isinstance(v, (float, int, Decimal)):
        # is there anything else we want to add here? If you think so, create an issue.
        return str(v)
    elif isinstance(v, (bytes, bytearray)):
        return v.decode()
    else:
        raise errors.StrError()


def strict_str_validator(v: Any) -> Union[str]:
    if isinstance(v, str) and not isinstance(v, Enum):
        return v
    raise errors.StrError()


def bytes_validator(v: Any) -> Union[bytes]:
    if isinstance(v, bytes):
        return v
    elif isinstance(v, bytearray):
        return bytes(v)
    elif isinstance(v, str):
        return v.encode()
    elif isinstance(v, (float, int, Decimal)):
        return str(v).encode()
    else:
        raise errors.BytesError()


def strict_bytes_validator(v: Any) -> Union[bytes]:
    if isinstance(v, bytes):
        return v
    elif isinstance(v, bytearray):
        return bytes(v)
    else:
        raise errors.BytesError()


BOOL_FALSE = {0, '0', 'off', 'f', 'false', 'n', 'no'}
BOOL_TRUE = {1, '1', 'on', 't', 'true', 'y', 'yes'}


def bool_validator(v: Any) -> bool:
    if v is True or v is False:
        return v
    if isinstance(v, bytes):
        v = v.decode()
    if isinstance(v, str):
        v = v.lower()
    try:
        if v in BOOL_TRUE:
            return True
        if v in BOOL_FALSE:
            return False
    except TypeError:
        raise errors.BoolError()
    raise errors.BoolError()


# matches the default limit cpython, see https://github.com/python/cpython/pull/96500
max_str_int = 4_300


def int_validator(v: Any) -> int:
    if isinstance(v, int) and not (v is True or v is False):
        return v

    # see https://github.com/pydantic/pydantic/issues/1477 and in turn, https://github.com/python/cpython/issues/95778
    # this check should be unnecessary once patch releases are out for 3.7, 3.8, 3.9 and 3.10
    # but better to check here until then.
    # NOTICE: this does not fully protect user from the DOS risk since the standard library JSON implementation
    # (and other std lib modules like xml) use `int()` and are likely called before this, the best workaround is to
    # 1. update to the latest patch release of python once released, 2. use a different JSON library like ujson
    if isinstance(v, (str, bytes, bytearray)) and len(v) > max_str_int:
        raise errors.IntegerError()

    try:
        return int(v)
    except (TypeError, ValueError, OverflowError):
        raise errors.IntegerError()


def strict_int_validator(v: Any) -> int:
    if isinstance(v, int) and not (v is True or v is False):
        return v
    raise errors.IntegerError()


def float_validator(v: Any) -> float:
    if isinstance(v, float):
        return v

    try:
        return float(v)
    except (TypeError, ValueError):
        raise errors.FloatError()


def strict_float_validator(v: Any) -> float:
    if isinstance(v, float):
        return v
    raise errors.FloatError()


def float_finite_validator(v: 'Number', field: 'ModelField', config: 'BaseConfig') -> 'Number':
    allow_inf_nan = getattr(field.type_, 'allow_inf_nan', None)
    if allow_inf_nan is None:
        allow_inf_nan = config.allow_inf_nan

    if allow_inf_nan is False and (math.isnan(v) or math.isinf(v)):
        raise errors.NumberNotFiniteError()
    return v


def number_multiple_validator(v: 'Number', field: 'ModelField') -> 'Number':
    field_type: ConstrainedNumber = field.type_
    if field_type.multiple_of is not None:
        mod = float(v) / float(field_type.multiple_of) % 1
        if not almost_equal_floats(mod, 0.0) and not almost_equal_floats(mod, 1.0):
            raise errors.NumberNotMultipleError(multiple_of=field_type.multiple_of)
    return v


def number_size_validator(v: 'Number', field: 'ModelField') -> 'Number':
    field_type: ConstrainedNumber = field.type_
    if field_type.gt is not None and not v > field_type.gt:
        raise errors.NumberNotGtError(limit_value=field_type.gt)
    elif field_type.ge is not None and not v >= field_type.ge:
        raise errors.NumberNotGeError(limit_value=field_type.ge)

    if field_type.lt is not None and not v < field_type.lt:
        raise errors.NumberNotLtError(limit_value=field_type.lt)
    if field_type.le is not None and not v <= field_type.le:
        raise errors.NumberNotLeError(limit_value=field_type.le)

    return v


def constant_validator(v: 'Any', field: 'ModelField') -> 'Any':
    """Validate ``const`` fields.

    The value provided for a ``const`` field must be equal to the default value
    of the field. This is to support the keyword of the same name in JSON
    Schema.
    """
    if v != field.default:
        raise errors.WrongConstantError(given=v, permitted=[field.default])

    return v


def anystr_length_validator(v: 'StrBytes', config: 'BaseConfig') -> 'StrBytes':
    v_len = len(v)

    min_length = config.min_anystr_length
    if v_len < min_length:
        raise errors.AnyStrMinLengthError(limit_value=min_length)

    max_length = config.max_anystr_length
    if max_length is not None and v_len > max_length:
        raise errors.AnyStrMaxLengthError(limit_value=max_length)

    return v


def anystr_strip_whitespace(v: 'StrBytes') -> 'StrBytes':
    return v.strip()


def anystr_upper(v: 'StrBytes') -> 'StrBytes':
    return v.upper()


def anystr_lower(v: 'StrBytes') -> 'StrBytes':
    return v.lower()


def ordered_dict_validator(v: Any) -> 'AnyOrderedDict':
    if isinstance(v, OrderedDict):
        return v

    try:
        return OrderedDict(v)
    except (TypeError, ValueError):
        raise errors.DictError()


def dict_validator(v: Any) -> Dict[Any, Any]:
    if isinstance(v, dict):
        return v

    try:
        return dict(v)
    except (TypeError, ValueError):
        raise errors.DictError()


def list_validator(v: Any) -> List[Any]:
    if isinstance(v, list):
        return v
    elif sequence_like(v):
        return list(v)
    else:
        raise errors.ListError()


def tuple_validator(v: Any) -> Tuple[Any, ...]:
    if isinstance(v, tuple):
        return v
    elif sequence_like(v):
        return tuple(v)
    else:
        raise errors.TupleError()


def set_validator(v: Any) -> Set[Any]:
    if isinstance(v, set):
        return v
    elif sequence_like(v):
        return set(v)
    else:
        raise errors.SetError()


def frozenset_validator(v: Any) -> FrozenSet[Any]:
    if isinstance(v, frozenset):
        return v
    elif sequence_like(v):
        return frozenset(v)
    else:
        raise errors.FrozenSetError()


def deque_validator(v: Any) -> Deque[Any]:
    if isinstance(v, deque):
        return v
    elif sequence_like(v):
        return deque(v)
    else:
        raise errors.DequeError()


def enum_member_validator(v: Any, field: 'ModelField', config: 'BaseConfig') -> Enum:
    try:
        enum_v = field.type_(v)
    except ValueError:
        # field.type_ should be an enum, so will be iterable
        raise errors.EnumMemberError(enum_values=list(field.type_))
    return enum_v.value if config.use_enum_values else enum_v


def uuid_validator(v: Any, field: 'ModelField') -> UUID:
    try:
        if isinstance(v, str):
            v = UUID(v)
        elif isinstance(v, (bytes, bytearray)):
            try:
                v = UUID(v.decode())
            except ValueError:
                # 16 bytes in big-endian order as the bytes argument fail
                # the above check
                v = UUID(bytes=v)
    except ValueError:
        raise errors.UUIDError()

    if not isinstance(v, UUID):
        raise errors.UUIDError()

    required_version = getattr(field.type_, '_required_version', None)
    if required_version and v.version != required_version:
        raise errors.UUIDVersionError(required_version=required_version)

    return v


def decimal_validator(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    elif isinstance(v, (bytes, bytearray)):
        v = v.decode()

    v = str(v).strip()

    try:
        v = Decimal(v)
    except DecimalException:
        raise errors.DecimalError()

    if not v.is_finite():
        raise errors.DecimalIsNotFiniteError()

    return v


def hashable_validator(v: Any) -> Hashable:
    if isinstance(v, Hashable):
        return v

    raise errors.HashableError()


def ip_v4_address_validator(v: Any) -> IPv4Address:
    if isinstance(v, IPv4Address):
        return v

    try:
        return IPv4Address(v)
    except ValueError:
        raise errors.IPv4AddressError()


def ip_v6_address_validator(v: Any) -> IPv6Address:
    if isinstance(v, IPv6Address):
        return v

    try:
        return IPv6Address(v)
    except ValueError:
        raise errors.IPv6AddressError()


def ip_v4_network_validator(v: Any) -> IPv4Network:
    """
    Assume IPv4Network initialised with a default ``strict`` argument

    See more:
    https://docs.python.org/library/ipaddress.html#ipaddress.IPv4Network
    """
    if isinstance(v, IPv4Network):
        return v

    try:
        return IPv4Network(v)
    except ValueError:
        raise errors.IPv4NetworkError()


def ip_v6_network_validator(v: Any) -> IPv6Network:
    """
    Assume IPv6Network initialised with a default ``strict`` argument

    See more:
    https://docs.python.org/library/ipaddress.html#ipaddress.IPv6Network
    """
    if isinstance(v, IPv6Network):
        return v

    try:
        return IPv6Network(v)
    except ValueError:
        raise errors.IPv6NetworkError()


def ip_v4_interface_validator(v: Any) -> IPv4Interface:
    if isinstance(v, IPv4Interface):
        return v

    try:
        return IPv4Interface(v)
    except ValueError:
        raise errors.IPv4InterfaceError()


def ip_v6_interface_validator(v: Any) -> IPv6Interface:
    if isinstance(v, IPv6Interface):
        return v

    try:
        return IPv6Interface(v)
    except ValueError:
        raise errors.IPv6InterfaceError()


def path_validator(v: Any) -> Path:
    if isinstance(v, Path):
        return v

    try:
        return Path(v)
    except TypeError:
        raise errors.PathError()


def path_exists_validator(v: Any) -> Path:
    if not v.exists():
        raise errors.PathNotExistsError(path=v)

    return v


def callable_validator(v: Any) -> AnyCallable:
    """
    Perform a simple check if the value is callable.

    Note: complete matching of argument type hints and return types is not performed
    """
    if callable(v):
        return v

    raise errors.CallableError(value=v)


def enum_validator(v: Any) -> Enum:
    if isinstance(v, Enum):
        return v

    raise errors.EnumError(value=v)


def int_enum_validator(v: Any) -> IntEnum:
    if isinstance(v, IntEnum):
        return v

    raise errors.IntEnumError(value=v)


def make_literal_validator(type_: Any) -> Callable[[Any], Any]:
    permitted_choices = all_literal_values(type_)

    # To have a O(1) complexity and still return one of the values set inside the `Literal`,
    # we create a dict with the set values (a set causes some problems with the way intersection works).
    # In some cases the set value and checked value can indeed be different (see `test_literal_validator_str_enum`)
    allowed_choices = {v: v for v in permitted_choices}

    def literal_validator(v: Any) -> Any:
        try:
            return allowed_choices[v]
        except (KeyError, TypeError):
            raise errors.WrongConstantError(given=v, permitted=permitted_choices)

    return literal_validator


def constr_length_validator(v: 'StrBytes', field: 'ModelField', config: 'BaseConfig') -> 'StrBytes':
    v_len = len(v)

    min_length = field.type_.min_length if field.type_.min_length is not None else config.min_anystr_length
    if v_len < min_length:
        raise errors.AnyStrMinLengthError(limit_value=min_length)

    max_length = field.type_.max_length if field.type_.max_length is not None else config.max_anystr_length
    if max_length is not None and v_len > max_length:
        raise errors.AnyStrMaxLengthError(limit_value=max_length)

    return v


def constr_strip_whitespace(v: 'StrBytes', field: 'ModelField', config: 'BaseConfig') -> 'StrBytes':
    strip_whitespace = field.type_.strip_whitespace or config.anystr_strip_whitespace
    if strip_whitespace:
        v = v.strip()

    return v


def constr_upper(v: 'StrBytes', field: 'ModelField', config: 'BaseConfig') -> 'StrBytes':
    upper = field.type_.to_upper or config.anystr_upper
    if upper:
        v = v.upper()

    return v


def constr_lower(v: 'StrBytes', field: 'ModelField', config: 'BaseConfig') -> 'StrBytes':
    lower = field.type_.to_lower or config.anystr_lower
    if lower:
        v = v.lower()
    return v


def validate_json(v: Any, config: 'BaseConfig') -> Any:
    if v is None:
        # pass None through to other validators
        return v
    try:
        return config.json_loads(v)  # type: ignore
    except ValueError:
        raise errors.JsonError()
    except TypeError:
        raise errors.JsonTypeError()


T = TypeVar('T')


def make_arbitrary_type_validator(type_: Type[T]) -> Callable[[T], T]:
    def arbitrary_type_validator(v: Any) -> T:
        if isinstance(v, type_):
            return v
        raise errors.ArbitraryTypeError(expected_arbitrary_type=type_)

    return arbitrary_type_validator


def make_class_validator(type_: Type[T]) -> Callable[[Any], Type[T]]:
    def class_validator(v: Any) -> Type[T]:
        if lenient_issubclass(v, type_):
            return v
        raise errors.SubclassError(expected_class=type_)

    return class_validator


def any_class_validator(v: Any) -> Type[T]:
    if isinstance(v, type):
        return v
    raise errors.ClassError()


def none_validator(v: Any) -> 'Literal[None]':
    if v is None:
        return v
    raise errors.NotNoneError()


def pattern_validator(v: Any) -> Pattern[str]:
    if isinstance(v, Pattern):
        return v

    str_value = str_validator(v)

    try:
        return re.compile(str_value)
    except re.error:
        raise errors.PatternError()


NamedTupleT = TypeVar('NamedTupleT', bound=NamedTuple)


def make_namedtuple_validator(
    namedtuple_cls: Type[NamedTupleT], config: Type['BaseConfig']
) -> Callable[[Tuple[Any, ...]], NamedTupleT]:
    from pydantic.v1.annotated_types import create_model_from_namedtuple

    NamedTupleModel = create_model_from_namedtuple(
        namedtuple_cls,
        __config__=config,
        __module__=namedtuple_cls.__module__,
    )
    namedtuple_cls.__pydantic_model__ = NamedTupleModel  # type: ignore[attr-defined]

    def namedtuple_validator(values: Tuple[Any, ...]) -> NamedTupleT:
        annotations = NamedTupleModel.__annotations__

        if len(values) > len(annotations):
            raise errors.ListMaxLengthError(limit_value=len(annotations))

        dict_values: Dict[str, Any] = dict(zip(annotations, values))
        validated_dict_values: Dict[str, Any] = dict(NamedTupleModel(**dict_values))
        return namedtuple_cls(**validated_dict_values)

    return namedtuple_validator


def make_typeddict_validator(
    typeddict_cls: Type['TypedDict'], config: Type['BaseConfig']  # type: ignore[valid-type]
) -> Callable[[Any], Dict[str, Any]]:
    from pydantic.v1.annotated_types import create_model_from_typeddict

    TypedDictModel = create_model_from_typeddict(
        typeddict_cls,
        __config__=config,
        __module__=typeddict_cls.__module__,
    )
    typeddict_cls.__pydantic_model__ = TypedDictModel  # type: ignore[attr-defined]

    def typeddict_validator(values: 'TypedDict') -> Dict[str, Any]:  # type: ignore[valid-type]
        return TypedDictModel.parse_obj(values).dict(exclude_unset=True)

    return typeddict_validator


class IfConfig:
    def __init__(self, validator: AnyCallable, *config_attr_names: str, ignored_value: Any = False) -> None:
        self.validator = validator
        self.config_attr_names = config_attr_names
        self.ignored_value = ignored_value

    def check(self, config: Type['BaseConfig']) -> bool:
        return any(getattr(config, name) not in {None, self.ignored_value} for name in self.config_attr_names)


# order is important here, for example: bool is a subclass of int so has to come first, datetime before date same,
# IPv4Interface before IPv4Address, etc
_VALIDATORS: List[Tuple[Type[Any], List[Any]]] = [
    (IntEnum, [int_validator, enum_member_validator]),
    (Enum, [enum_member_validator]),
    (
        str,
        [
            str_validator,
            IfConfig(anystr_strip_whitespace, 'anystr_strip_whitespace'),
            IfConfig(anystr_upper, 'anystr_upper'),
            IfConfig(anystr_lower, 'anystr_lower'),
            IfConfig(anystr_length_validator, 'min_anystr_length', 'max_anystr_length'),
        ],
    ),
    (
        bytes,
        [
            bytes_validator,
            IfConfig(anystr_strip_whitespace, 'anystr_strip_whitespace'),
            IfConfig(anystr_upper, 'anystr_upper'),
            IfConfig(anystr_lower, 'anystr_lower'),
            IfConfig(anystr_length_validator, 'min_anystr_length', 'max_anystr_length'),
        ],
    ),
    (bool, [bool_validator]),
    (int, [int_validator]),
    (float, [float_validator, IfConfig(float_finite_validator, 'allow_inf_nan', ignored_value=True)]),
    (Path, [path_validator]),
    (datetime, [parse_datetime]),
    (date, [parse_date]),
    (time, [parse_time]),
    (timedelta, [parse_duration]),
    (OrderedDict, [ordered_dict_validator]),
    (dict, [dict_validator]),
    (list, [list_validator]),
    (tuple, [tuple_validator]),
    (set, [set_validator]),
    (frozenset, [frozenset_validator]),
    (deque, [deque_validator]),
    (UUID, [uuid_validator]),
    (Decimal, [decimal_validator]),
    (IPv4Interface, [ip_v4_interface_validator]),
    (IPv6Interface, [ip_v6_interface_validator]),
    (IPv4Address, [ip_v4_address_validator]),
    (IPv6Address, [ip_v6_address_validator]),
    (IPv4Network, [ip_v4_network_validator]),
    (IPv6Network, [ip_v6_network_validator]),
]


def find_validators(  # noqa: C901 (ignore complexity)
    type_: Type[Any], config: Type['BaseConfig']
) -> Generator[AnyCallable, None, None]:
    from pydantic.v1.dataclasses import is_builtin_dataclass, make_dataclass_validator

    if type_ is Any or type_ is object:
        return
    type_type = type_.__class__
    if type_type == ForwardRef or type_type == TypeVar:
        return

    if is_none_type(type_):
        yield none_validator
        return
    if type_ is Pattern or type_ is re.Pattern:
        yield pattern_validator
        return
    if type_ is Hashable or type_ is CollectionsHashable:
        yield hashable_validator
        return
    if is_callable_type(type_):
        yield callable_validator
        return
    if is_literal_type(type_):
        yield make_literal_validator(type_)
        return
    if is_builtin_dataclass(type_):
        yield from make_dataclass_validator(type_, config)
        return
    if type_ is Enum:
        yield enum_validator
        return
    if type_ is IntEnum:
        yield int_enum_validator
        return
    if is_namedtuple(type_):
        yield tuple_validator
        yield make_namedtuple_validator(type_, config)
        return
    if is_typeddict(type_):
        yield make_typeddict_validator(type_, config)
        return

    class_ = get_class(type_)
    if class_ is not None:
        if class_ is not Any and isinstance(class_, type):
            yield make_class_validator(class_)
        else:
            yield any_class_validator
        return

    for val_type, validators in _VALIDATORS:
        try:
            if issubclass(type_, val_type):
                for v in validators:
                    if isinstance(v, IfConfig):
                        if v.check(config):
                            yield v.validator
                    else:
                        yield v
                return
        except TypeError:
            raise RuntimeError(f'error checking inheritance of {type_!r} (type: {display_as_type(type_)})')

    if config.arbitrary_types_allowed:
        yield make_arbitrary_type_validator(type_)
    else:
        if hasattr(type_, '__pydantic_core_schema__'):
            warn(f'Mixing V1 and V2 models is not supported. `{type_.__name__}` is a V2 model.', UserWarning)
        raise RuntimeError(f'no validator found for {type_}, see `arbitrary_types_allowed` in Config')

# === NexusCore/openenv\Lib\site-packages\matplotlib\scale.py ===
"""
Scales define the distribution of data values on an axis, e.g. a log scaling.

The mapping is implemented through `.Transform` subclasses.

The following scales are built-in:

.. _builtin_scales:

============= ===================== ================================ =================================
Name          Class                 Transform                        Inverted transform
============= ===================== ================================ =================================
"asinh"       `AsinhScale`          `AsinhTransform`                 `InvertedAsinhTransform`
"function"    `FuncScale`           `FuncTransform`                  `FuncTransform`
"functionlog" `FuncScaleLog`        `FuncTransform` + `LogTransform` `InvertedLogTransform` + `FuncTransform`
"linear"      `LinearScale`         `.IdentityTransform`             `.IdentityTransform`
"log"         `LogScale`            `LogTransform`                   `InvertedLogTransform`
"logit"       `LogitScale`          `LogitTransform`                 `LogisticTransform`
"symlog"      `SymmetricalLogScale` `SymmetricalLogTransform`        `InvertedSymmetricalLogTransform`
============= ===================== ================================ =================================

A user will often only use the scale name, e.g. when setting the scale through
`~.Axes.set_xscale`: ``ax.set_xscale("log")``.

See also the :ref:`scales examples <sphx_glr_gallery_scales>` in the documentation.

Custom scaling can be achieved through `FuncScale`, or by creating your own
`ScaleBase` subclass and corresponding transforms (see :doc:`/gallery/scales/custom_scale`).
Third parties can register their scales by name through `register_scale`.
"""  # noqa: E501

import inspect
import textwrap

import numpy as np

import matplotlib as mpl
from matplotlib import _api, _docstring
from matplotlib.ticker import (
    NullFormatter, ScalarFormatter, LogFormatterSciNotation, LogitFormatter,
    NullLocator, LogLocator, AutoLocator, AutoMinorLocator,
    SymmetricalLogLocator, AsinhLocator, LogitLocator)
from matplotlib.transforms import Transform, IdentityTransform


class ScaleBase:
    """
    The base class for all scales.

    Scales are separable transformations, working on a single dimension.

    Subclasses should override

    :attr:`name`
        The scale's name.
    :meth:`get_transform`
        A method returning a `.Transform`, which converts data coordinates to
        scaled coordinates.  This transform should be invertible, so that e.g.
        mouse positions can be converted back to data coordinates.
    :meth:`set_default_locators_and_formatters`
        A method that sets default locators and formatters for an `~.axis.Axis`
        that uses this scale.
    :meth:`limit_range_for_scale`
        An optional method that "fixes" the axis range to acceptable values,
        e.g. restricting log-scaled axes to positive values.
    """

    def __init__(self, axis):
        r"""
        Construct a new scale.

        Notes
        -----
        The following note is for scale implementers.

        For back-compatibility reasons, scales take an `~matplotlib.axis.Axis`
        object as first argument.  However, this argument should not
        be used: a single scale object should be usable by multiple
        `~matplotlib.axis.Axis`\es at the same time.
        """

    def get_transform(self):
        """
        Return the `.Transform` object associated with this scale.
        """
        raise NotImplementedError()

    def set_default_locators_and_formatters(self, axis):
        """
        Set the locators and formatters of *axis* to instances suitable for
        this scale.
        """
        raise NotImplementedError()

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """
        Return the range *vmin*, *vmax*, restricted to the
        domain supported by this scale (if any).

        *minpos* should be the minimum positive value in the data.
        This is used by log scales to determine a minimum value.
        """
        return vmin, vmax


class LinearScale(ScaleBase):
    """
    The default linear scale.
    """

    name = 'linear'

    def __init__(self, axis):
        # This method is present only to prevent inheritance of the base class'
        # constructor docstring, which would otherwise end up interpolated into
        # the docstring of Axis.set_scale.
        """
        """  # noqa: D419

    def set_default_locators_and_formatters(self, axis):
        # docstring inherited
        axis.set_major_locator(AutoLocator())
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_formatter(NullFormatter())
        # update the minor locator for x and y axis based on rcParams
        if (axis.axis_name == 'x' and mpl.rcParams['xtick.minor.visible'] or
                axis.axis_name == 'y' and mpl.rcParams['ytick.minor.visible']):
            axis.set_minor_locator(AutoMinorLocator())
        else:
            axis.set_minor_locator(NullLocator())

    def get_transform(self):
        """
        Return the transform for linear scaling, which is just the
        `~matplotlib.transforms.IdentityTransform`.
        """
        return IdentityTransform()


class FuncTransform(Transform):
    """
    A simple transform that takes and arbitrary function for the
    forward and inverse transform.
    """

    input_dims = output_dims = 1

    def __init__(self, forward, inverse):
        """
        Parameters
        ----------
        forward : callable
            The forward function for the transform.  This function must have
            an inverse and, for best behavior, be monotonic.
            It must have the signature::

               def forward(values: array-like) -> array-like

        inverse : callable
            The inverse of the forward function.  Signature as ``forward``.
        """
        super().__init__()
        if callable(forward) and callable(inverse):
            self._forward = forward
            self._inverse = inverse
        else:
            raise ValueError('arguments to FuncTransform must be functions')

    def transform_non_affine(self, values):
        return self._forward(values)

    def inverted(self):
        return FuncTransform(self._inverse, self._forward)


class FuncScale(ScaleBase):
    """
    Provide an arbitrary scale with user-supplied function for the axis.
    """

    name = 'function'

    def __init__(self, axis, functions):
        """
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`
            The axis for the scale.
        functions : (callable, callable)
            two-tuple of the forward and inverse functions for the scale.
            The forward function must be monotonic.

            Both functions must have the signature::

               def forward(values: array-like) -> array-like
        """
        forward, inverse = functions
        transform = FuncTransform(forward, inverse)
        self._transform = transform

    def get_transform(self):
        """Return the `.FuncTransform` associated with this scale."""
        return self._transform

    def set_default_locators_and_formatters(self, axis):
        # docstring inherited
        axis.set_major_locator(AutoLocator())
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_formatter(NullFormatter())
        # update the minor locator for x and y axis based on rcParams
        if (axis.axis_name == 'x' and mpl.rcParams['xtick.minor.visible'] or
                axis.axis_name == 'y' and mpl.rcParams['ytick.minor.visible']):
            axis.set_minor_locator(AutoMinorLocator())
        else:
            axis.set_minor_locator(NullLocator())


class LogTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, base, nonpositive='clip'):
        super().__init__()
        if base <= 0 or base == 1:
            raise ValueError('The log base cannot be <= 0 or == 1')
        self.base = base
        self._clip = _api.check_getitem(
            {"clip": True, "mask": False}, nonpositive=nonpositive)

    def __str__(self):
        return "{}(base={}, nonpositive={!r})".format(
            type(self).__name__, self.base, "clip" if self._clip else "mask")

    def transform_non_affine(self, values):
        # Ignore invalid values due to nans being passed to the transform.
        with np.errstate(divide="ignore", invalid="ignore"):
            log = {np.e: np.log, 2: np.log2, 10: np.log10}.get(self.base)
            if log:  # If possible, do everything in a single call to NumPy.
                out = log(values)
            else:
                out = np.log(values)
                out /= np.log(self.base)
            if self._clip:
                # SVG spec says that conforming viewers must support values up
                # to 3.4e38 (C float); however experiments suggest that
                # Inkscape (which uses cairo for rendering) runs into cairo's
                # 24-bit limit (which is apparently shared by Agg).
                # Ghostscript (used for pdf rendering appears to overflow even
                # earlier, with the max value around 2 ** 15 for the tests to
                # pass. On the other hand, in practice, we want to clip beyond
                #     np.log10(np.nextafter(0, 1)) ~ -323
                # so 1000 seems safe.
                out[values <= 0] = -1000
        return out

    def inverted(self):
        return InvertedLogTransform(self.base)


class InvertedLogTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, base):
        super().__init__()
        self.base = base

    def __str__(self):
        return f"{type(self).__name__}(base={self.base})"

    def transform_non_affine(self, values):
        return np.power(self.base, values)

    def inverted(self):
        return LogTransform(self.base)


class LogScale(ScaleBase):
    """
    A standard logarithmic scale.  Care is taken to only plot positive values.
    """
    name = 'log'

    def __init__(self, axis, *, base=10, subs=None, nonpositive="clip"):
        """
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`
            The axis for the scale.
        base : float, default: 10
            The base of the logarithm.
        nonpositive : {'clip', 'mask'}, default: 'clip'
            Determines the behavior for non-positive values. They can either
            be masked as invalid, or clipped to a very small positive number.
        subs : sequence of int, default: None
            Where to place the subticks between each major tick.  For example,
            in a log10 scale, ``[2, 3, 4, 5, 6, 7, 8, 9]`` will place 8
            logarithmically spaced minor ticks between each major tick.
        """
        self._transform = LogTransform(base, nonpositive)
        self.subs = subs

    base = property(lambda self: self._transform.base)

    def set_default_locators_and_formatters(self, axis):
        # docstring inherited
        axis.set_major_locator(LogLocator(self.base))
        axis.set_major_formatter(LogFormatterSciNotation(self.base))
        axis.set_minor_locator(LogLocator(self.base, self.subs))
        axis.set_minor_formatter(
            LogFormatterSciNotation(self.base,
                                    labelOnlyBase=(self.subs is not None)))

    def get_transform(self):
        """Return the `.LogTransform` associated with this scale."""
        return self._transform

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """Limit the domain to positive values."""
        if not np.isfinite(minpos):
            minpos = 1e-300  # Should rarely (if ever) have a visible effect.

        return (minpos if vmin <= 0 else vmin,
                minpos if vmax <= 0 else vmax)


class FuncScaleLog(LogScale):
    """
    Provide an arbitrary scale with user-supplied function for the axis and
    then put on a logarithmic axes.
    """

    name = 'functionlog'

    def __init__(self, axis, functions, base=10):
        """
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`
            The axis for the scale.
        functions : (callable, callable)
            two-tuple of the forward and inverse functions for the scale.
            The forward function must be monotonic.

            Both functions must have the signature::

                def forward(values: array-like) -> array-like

        base : float, default: 10
            Logarithmic base of the scale.
        """
        forward, inverse = functions
        self.subs = None
        self._transform = FuncTransform(forward, inverse) + LogTransform(base)

    @property
    def base(self):
        return self._transform._b.base  # Base of the LogTransform.

    def get_transform(self):
        """Return the `.Transform` associated with this scale."""
        return self._transform


class SymmetricalLogTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, base, linthresh, linscale):
        super().__init__()
        if base <= 1.0:
            raise ValueError("'base' must be larger than 1")
        if linthresh <= 0.0:
            raise ValueError("'linthresh' must be positive")
        if linscale <= 0.0:
            raise ValueError("'linscale' must be positive")
        self.base = base
        self.linthresh = linthresh
        self.linscale = linscale
        self._linscale_adj = (linscale / (1.0 - self.base ** -1))
        self._log_base = np.log(base)

    def transform_non_affine(self, values):
        abs_a = np.abs(values)
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.sign(values) * self.linthresh * (
                self._linscale_adj +
                np.log(abs_a / self.linthresh) / self._log_base)
            inside = abs_a <= self.linthresh
        out[inside] = values[inside] * self._linscale_adj
        return out

    def inverted(self):
        return InvertedSymmetricalLogTransform(self.base, self.linthresh,
                                               self.linscale)


class InvertedSymmetricalLogTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, base, linthresh, linscale):
        super().__init__()
        symlog = SymmetricalLogTransform(base, linthresh, linscale)
        self.base = base
        self.linthresh = linthresh
        self.invlinthresh = symlog.transform(linthresh)
        self.linscale = linscale
        self._linscale_adj = (linscale / (1.0 - self.base ** -1))

    def transform_non_affine(self, values):
        abs_a = np.abs(values)
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.sign(values) * self.linthresh * (
                np.power(self.base,
                         abs_a / self.linthresh - self._linscale_adj))
            inside = abs_a <= self.invlinthresh
        out[inside] = values[inside] / self._linscale_adj
        return out

    def inverted(self):
        return SymmetricalLogTransform(self.base,
                                       self.linthresh, self.linscale)


class SymmetricalLogScale(ScaleBase):
    """
    The symmetrical logarithmic scale is logarithmic in both the
    positive and negative directions from the origin.

    Since the values close to zero tend toward infinity, there is a
    need to have a range around zero that is linear.  The parameter
    *linthresh* allows the user to specify the size of this range
    (-*linthresh*, *linthresh*).

    See :doc:`/gallery/scales/symlog_demo` for a detailed description.

    Parameters
    ----------
    base : float, default: 10
        The base of the logarithm.

    linthresh : float, default: 2
        Defines the range ``(-x, x)``, within which the plot is linear.
        This avoids having the plot go to infinity around zero.

    subs : sequence of int
        Where to place the subticks between each major tick.
        For example, in a log10 scale: ``[2, 3, 4, 5, 6, 7, 8, 9]`` will place
        8 logarithmically spaced minor ticks between each major tick.

    linscale : float, optional
        This allows the linear range ``(-linthresh, linthresh)`` to be
        stretched relative to the logarithmic range. Its value is the number of
        decades to use for each half of the linear range. For example, when
        *linscale* == 1.0 (the default), the space used for the positive and
        negative halves of the linear range will be equal to one decade in
        the logarithmic range.
    """
    name = 'symlog'

    def __init__(self, axis, *, base=10, linthresh=2, subs=None, linscale=1):
        self._transform = SymmetricalLogTransform(base, linthresh, linscale)
        self.subs = subs

    base = property(lambda self: self._transform.base)
    linthresh = property(lambda self: self._transform.linthresh)
    linscale = property(lambda self: self._transform.linscale)

    def set_default_locators_and_formatters(self, axis):
        # docstring inherited
        axis.set_major_locator(SymmetricalLogLocator(self.get_transform()))
        axis.set_major_formatter(LogFormatterSciNotation(self.base))
        axis.set_minor_locator(SymmetricalLogLocator(self.get_transform(),
                                                     self.subs))
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        """Return the `.SymmetricalLogTransform` associated with this scale."""
        return self._transform


class AsinhTransform(Transform):
    """Inverse hyperbolic-sine transformation used by `.AsinhScale`"""
    input_dims = output_dims = 1

    def __init__(self, linear_width):
        super().__init__()
        if linear_width <= 0.0:
            raise ValueError("Scale parameter 'linear_width' " +
                             "must be strictly positive")
        self.linear_width = linear_width

    def transform_non_affine(self, values):
        return self.linear_width * np.arcsinh(values / self.linear_width)

    def inverted(self):
        return InvertedAsinhTransform(self.linear_width)


class InvertedAsinhTransform(Transform):
    """Hyperbolic sine transformation used by `.AsinhScale`"""
    input_dims = output_dims = 1

    def __init__(self, linear_width):
        super().__init__()
        self.linear_width = linear_width

    def transform_non_affine(self, values):
        return self.linear_width * np.sinh(values / self.linear_width)

    def inverted(self):
        return AsinhTransform(self.linear_width)


class AsinhScale(ScaleBase):
    """
    A quasi-logarithmic scale based on the inverse hyperbolic sine (asinh)

    For values close to zero, this is essentially a linear scale,
    but for large magnitude values (either positive or negative)
    it is asymptotically logarithmic. The transition between these
    linear and logarithmic regimes is smooth, and has no discontinuities
    in the function gradient in contrast to
    the `.SymmetricalLogScale` ("symlog") scale.

    Specifically, the transformation of an axis coordinate :math:`a` is
    :math:`a \\rightarrow a_0 \\sinh^{-1} (a / a_0)` where :math:`a_0`
    is the effective width of the linear region of the transformation.
    In that region, the transformation is
    :math:`a \\rightarrow a + \\mathcal{O}(a^3)`.
    For large values of :math:`a` the transformation behaves as
    :math:`a \\rightarrow a_0 \\, \\mathrm{sgn}(a) \\ln |a| + \\mathcal{O}(1)`.

    .. note::

       This API is provisional and may be revised in the future
       based on early user feedback.
    """

    name = 'asinh'

    auto_tick_multipliers = {
        3: (2, ),
        4: (2, ),
        5: (2, ),
        8: (2, 4),
        10: (2, 5),
        16: (2, 4, 8),
        64: (4, 16),
        1024: (256, 512)
    }

    def __init__(self, axis, *, linear_width=1.0,
                 base=10, subs='auto', **kwargs):
        """
        Parameters
        ----------
        linear_width : float, default: 1
            The scale parameter (elsewhere referred to as :math:`a_0`)
            defining the extent of the quasi-linear region,
            and the coordinate values beyond which the transformation
            becomes asymptotically logarithmic.
        base : int, default: 10
            The number base used for rounding tick locations
            on a logarithmic scale. If this is less than one,
            then rounding is to the nearest integer multiple
            of powers of ten.
        subs : sequence of int
            Multiples of the number base used for minor ticks.
            If set to 'auto', this will use built-in defaults,
            e.g. (2, 5) for base=10.
        """
        super().__init__(axis)
        self._transform = AsinhTransform(linear_width)
        self._base = int(base)
        if subs == 'auto':
            self._subs = self.auto_tick_multipliers.get(self._base)
        else:
            self._subs = subs

    linear_width = property(lambda self: self._transform.linear_width)

    def get_transform(self):
        return self._transform

    def set_default_locators_and_formatters(self, axis):
        axis.set(major_locator=AsinhLocator(self.linear_width,
                                            base=self._base),
                 minor_locator=AsinhLocator(self.linear_width,
                                            base=self._base,
                                            subs=self._subs),
                 minor_formatter=NullFormatter())
        if self._base > 1:
            axis.set_major_formatter(LogFormatterSciNotation(self._base))
        else:
            axis.set_major_formatter('{x:.3g}')


class LogitTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, nonpositive='mask'):
        super().__init__()
        _api.check_in_list(['mask', 'clip'], nonpositive=nonpositive)
        self._nonpositive = nonpositive
        self._clip = {"clip": True, "mask": False}[nonpositive]

    def transform_non_affine(self, values):
        """logit transform (base 10), masked or clipped"""
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.log10(values / (1 - values))
        if self._clip:  # See LogTransform for choice of clip value.
            out[values <= 0] = -1000
            out[1 <= values] = 1000
        return out

    def inverted(self):
        return LogisticTransform(self._nonpositive)

    def __str__(self):
        return f"{type(self).__name__}({self._nonpositive!r})"


class LogisticTransform(Transform):
    input_dims = output_dims = 1

    def __init__(self, nonpositive='mask'):
        super().__init__()
        self._nonpositive = nonpositive

    def transform_non_affine(self, values):
        """logistic transform (base 10)"""
        return 1.0 / (1 + 10**(-values))

    def inverted(self):
        return LogitTransform(self._nonpositive)

    def __str__(self):
        return f"{type(self).__name__}({self._nonpositive!r})"


class LogitScale(ScaleBase):
    """
    Logit scale for data between zero and one, both excluded.

    This scale is similar to a log scale close to zero and to one, and almost
    linear around 0.5. It maps the interval ]0, 1[ onto ]-infty, +infty[.
    """
    name = 'logit'

    def __init__(self, axis, nonpositive='mask', *,
                 one_half=r"\frac{1}{2}", use_overline=False):
        r"""
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`
            Currently unused.
        nonpositive : {'mask', 'clip'}
            Determines the behavior for values beyond the open interval ]0, 1[.
            They can either be masked as invalid, or clipped to a number very
            close to 0 or 1.
        use_overline : bool, default: False
            Indicate the usage of survival notation (\overline{x}) in place of
            standard notation (1-x) for probability close to one.
        one_half : str, default: r"\frac{1}{2}"
            The string used for ticks formatter to represent 1/2.
        """
        self._transform = LogitTransform(nonpositive)
        self._use_overline = use_overline
        self._one_half = one_half

    def get_transform(self):
        """Return the `.LogitTransform` associated with this scale."""
        return self._transform

    def set_default_locators_and_formatters(self, axis):
        # docstring inherited
        # ..., 0.01, 0.1, 0.5, 0.9, 0.99, ...
        axis.set_major_locator(LogitLocator())
        axis.set_major_formatter(
            LogitFormatter(
                one_half=self._one_half,
                use_overline=self._use_overline
            )
        )
        axis.set_minor_locator(LogitLocator(minor=True))
        axis.set_minor_formatter(
            LogitFormatter(
                minor=True,
                one_half=self._one_half,
                use_overline=self._use_overline
            )
        )

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """
        Limit the domain to values between 0 and 1 (excluded).
        """
        if not np.isfinite(minpos):
            minpos = 1e-7  # Should rarely (if ever) have a visible effect.
        return (minpos if vmin <= 0 else vmin,
                1 - minpos if vmax >= 1 else vmax)


_scale_mapping = {
    'linear': LinearScale,
    'log':    LogScale,
    'symlog': SymmetricalLogScale,
    'asinh':  AsinhScale,
    'logit':  LogitScale,
    'function': FuncScale,
    'functionlog': FuncScaleLog,
    }


def get_scale_names():
    """Return the names of the available scales."""
    return sorted(_scale_mapping)


def scale_factory(scale, axis, **kwargs):
    """
    Return a scale class by name.

    Parameters
    ----------
    scale : {%(names)s}
    axis : `~matplotlib.axis.Axis`
    """
    scale_cls = _api.check_getitem(_scale_mapping, scale=scale)
    return scale_cls(axis, **kwargs)


if scale_factory.__doc__:
    scale_factory.__doc__ = scale_factory.__doc__ % {
        "names": ", ".join(map(repr, get_scale_names()))}


def register_scale(scale_class):
    """
    Register a new kind of scale.

    Parameters
    ----------
    scale_class : subclass of `ScaleBase`
        The scale to register.
    """
    _scale_mapping[scale_class.name] = scale_class


def _get_scale_docs():
    """
    Helper function for generating docstrings related to scales.
    """
    docs = []
    for name, scale_class in _scale_mapping.items():
        docstring = inspect.getdoc(scale_class.__init__) or ""
        docs.extend([
            f"    {name!r}",
            "",
            textwrap.indent(docstring, " " * 8),
            ""
        ])
    return "\n".join(docs)


_docstring.interpd.register(
    scale_type='{%s}' % ', '.join([repr(x) for x in get_scale_names()]),
    scale_docs=_get_scale_docs().rstrip(),
    )

# === NexusCore/openenv\Lib\site-packages\parso\python\pep8.py ===
import re
from contextlib import contextmanager
from typing import Tuple

from parso.python.errors import ErrorFinder, ErrorFinderConfig
from parso.normalizer import Rule
from parso.python.tree import Flow, Scope


_IMPORT_TYPES = ('import_name', 'import_from')
_SUITE_INTRODUCERS = ('classdef', 'funcdef', 'if_stmt', 'while_stmt',
                      'for_stmt', 'try_stmt', 'with_stmt')
_NON_STAR_TYPES = ('term', 'import_from', 'power')
_OPENING_BRACKETS = '(', '[', '{'
_CLOSING_BRACKETS = ')', ']', '}'
_FACTOR = '+', '-', '~'
_ALLOW_SPACE = '*', '+', '-', '**', '/', '//', '@'
_BITWISE_OPERATOR = '<<', '>>', '|', '&', '^'
_NEEDS_SPACE: Tuple[str, ...] = (
    '=', '%', '->',
    '<', '>', '==', '>=', '<=', '<>', '!=',
    '+=', '-=', '*=', '@=', '/=', '%=', '&=', '|=', '^=', '<<=',
    '>>=', '**=', '//=')
_NEEDS_SPACE += _BITWISE_OPERATOR
_IMPLICIT_INDENTATION_TYPES = ('dictorsetmaker', 'argument')
_POSSIBLE_SLICE_PARENTS = ('subscript', 'subscriptlist', 'sliceop')


class IndentationTypes:
    VERTICAL_BRACKET = object()
    HANGING_BRACKET = object()
    BACKSLASH = object()
    SUITE = object()
    IMPLICIT = object()


class IndentationNode(object):
    type = IndentationTypes.SUITE

    def __init__(self, config, indentation, parent=None):
        self.bracket_indentation = self.indentation = indentation
        self.parent = parent

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

    def get_latest_suite_node(self):
        n = self
        while n is not None:
            if n.type == IndentationTypes.SUITE:
                return n

            n = n.parent


class BracketNode(IndentationNode):
    def __init__(self, config, leaf, parent, in_suite_introducer=False):
        self.leaf = leaf

        # Figure out here what the indentation is. For chained brackets
        # we can basically use the previous indentation.
        previous_leaf = leaf
        n = parent
        if n.type == IndentationTypes.IMPLICIT:
            n = n.parent
        while True:
            if hasattr(n, 'leaf') and previous_leaf.line != n.leaf.line:
                break

            previous_leaf = previous_leaf.get_previous_leaf()
            if not isinstance(n, BracketNode) or previous_leaf != n.leaf:
                break
            n = n.parent
        parent_indentation = n.indentation

        next_leaf = leaf.get_next_leaf()
        if '\n' in next_leaf.prefix or '\r' in next_leaf.prefix:
            # This implies code like:
            # foobarbaz(
            #     a,
            #     b,
            # )
            self.bracket_indentation = parent_indentation \
                + config.closing_bracket_hanging_indentation
            self.indentation = parent_indentation + config.indentation
            self.type = IndentationTypes.HANGING_BRACKET
        else:
            # Implies code like:
            # foobarbaz(
            #           a,
            #           b,
            #           )
            expected_end_indent = leaf.end_pos[1]
            if '\t' in config.indentation:
                self.indentation = None
            else:
                self.indentation = ' ' * expected_end_indent
            self.bracket_indentation = self.indentation
            self.type = IndentationTypes.VERTICAL_BRACKET

        if in_suite_introducer and parent.type == IndentationTypes.SUITE \
                and self.indentation == parent_indentation + config.indentation:
            self.indentation += config.indentation
            # The closing bracket should have the same indentation.
            self.bracket_indentation = self.indentation
        self.parent = parent


class ImplicitNode(BracketNode):
    """
    Implicit indentation after keyword arguments, default arguments,
    annotations and dict values.
    """
    def __init__(self, config, leaf, parent):
        super().__init__(config, leaf, parent)
        self.type = IndentationTypes.IMPLICIT

        next_leaf = leaf.get_next_leaf()
        if leaf == ':' and '\n' not in next_leaf.prefix and '\r' not in next_leaf.prefix:
            self.indentation += ' '


class BackslashNode(IndentationNode):
    type = IndentationTypes.BACKSLASH

    def __init__(self, config, parent_indentation, containing_leaf, spacing, parent=None):
        expr_stmt = containing_leaf.search_ancestor('expr_stmt')
        if expr_stmt is not None:
            equals = expr_stmt.children[-2]

            if '\t' in config.indentation:
                # TODO unite with the code of BracketNode
                self.indentation = None
            else:
                # If the backslash follows the equals, use normal indentation
                # otherwise it should align with the equals.
                if equals.end_pos == spacing.start_pos:
                    self.indentation = parent_indentation + config.indentation
                else:
                    # +1 because there is a space.
                    self.indentation = ' ' * (equals.end_pos[1] + 1)
        else:
            self.indentation = parent_indentation + config.indentation
        self.bracket_indentation = self.indentation
        self.parent = parent


def _is_magic_name(name):
    return name.value.startswith('__') and name.value.endswith('__')


class PEP8Normalizer(ErrorFinder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_part = None
        self._previous_leaf = None
        self._on_newline = True
        self._newline_count = 0
        self._wanted_newline_count = None
        self._max_new_lines_in_prefix = 0
        self._new_statement = True
        self._implicit_indentation_possible = False
        # The top of stack of the indentation nodes.
        self._indentation_tos = self._last_indentation_tos = \
            IndentationNode(self._config, indentation='')
        self._in_suite_introducer = False

        if ' ' in self._config.indentation:
            self._indentation_type = 'spaces'
            self._wrong_indentation_char = '\t'
        else:
            self._indentation_type = 'tabs'
            self._wrong_indentation_char = ' '

    @contextmanager
    def visit_node(self, node):
        with super().visit_node(node):
            with self._visit_node(node):
                yield

    @contextmanager
    def _visit_node(self, node):
        typ = node.type

        if typ in 'import_name':
            names = node.get_defined_names()
            if len(names) > 1:
                for name in names[:1]:
                    self.add_issue(name, 401, 'Multiple imports on one line')
        elif typ == 'lambdef':
            expr_stmt = node.parent
            # Check if it's simply defining a single name, not something like
            # foo.bar or x[1], where using a lambda could make more sense.
            if expr_stmt.type == 'expr_stmt' and any(n.type == 'name'
                                                     for n in expr_stmt.children[:-2:2]):
                self.add_issue(node, 731, 'Do not assign a lambda expression, use a def')
        elif typ == 'try_stmt':
            for child in node.children:
                # Here we can simply check if it's an except, because otherwise
                # it would be an except_clause.
                if child.type == 'keyword' and child.value == 'except':
                    self.add_issue(child, 722, 'Do not use bare except, specify exception instead')
        elif typ == 'comparison':
            for child in node.children:
                if child.type not in ('atom_expr', 'power'):
                    continue
                if len(child.children) > 2:
                    continue
                trailer = child.children[1]
                atom = child.children[0]
                if trailer.type == 'trailer' and atom.type == 'name' \
                        and atom.value == 'type':
                    self.add_issue(node, 721, "Do not compare types, use 'isinstance()")
                    break
        elif typ == 'file_input':
            endmarker = node.children[-1]
            prev = endmarker.get_previous_leaf()
            prefix = endmarker.prefix
            if (not prefix.endswith('\n') and not prefix.endswith('\r') and (
                    prefix or prev is None or prev.value not in {'\n', '\r\n', '\r'})):
                self.add_issue(endmarker, 292, "No newline at end of file")

        if typ in _IMPORT_TYPES:
            simple_stmt = node.parent
            module = simple_stmt.parent
            if module.type == 'file_input':
                index = module.children.index(simple_stmt)
                for child in module.children[:index]:
                    children = [child]
                    if child.type == 'simple_stmt':
                        # Remove the newline.
                        children = child.children[:-1]

                    found_docstring = False
                    for c in children:
                        if c.type == 'string' and not found_docstring:
                            continue
                        found_docstring = True

                        if c.type == 'expr_stmt' and \
                                all(_is_magic_name(n) for n in c.get_defined_names()):
                            continue

                        if c.type in _IMPORT_TYPES or isinstance(c, Flow):
                            continue

                        self.add_issue(node, 402, 'Module level import not at top of file')
                        break
                    else:
                        continue
                    break

        implicit_indentation_possible = typ in _IMPLICIT_INDENTATION_TYPES
        in_introducer = typ in _SUITE_INTRODUCERS
        if in_introducer:
            self._in_suite_introducer = True
        elif typ == 'suite':
            if self._indentation_tos.type == IndentationTypes.BACKSLASH:
                self._indentation_tos = self._indentation_tos.parent

            self._indentation_tos = IndentationNode(
                self._config,
                self._indentation_tos.indentation + self._config.indentation,
                parent=self._indentation_tos
            )
        elif implicit_indentation_possible:
            self._implicit_indentation_possible = True
        yield
        if typ == 'suite':
            assert self._indentation_tos.type == IndentationTypes.SUITE
            self._indentation_tos = self._indentation_tos.parent
            # If we dedent, no lines are needed anymore.
            self._wanted_newline_count = None
        elif implicit_indentation_possible:
            self._implicit_indentation_possible = False
            if self._indentation_tos.type == IndentationTypes.IMPLICIT:
                self._indentation_tos = self._indentation_tos.parent
        elif in_introducer:
            self._in_suite_introducer = False
            if typ in ('classdef', 'funcdef'):
                self._wanted_newline_count = self._get_wanted_blank_lines_count()

    def _check_tabs_spaces(self, spacing):
        if self._wrong_indentation_char in spacing.value:
            self.add_issue(spacing, 101, 'Indentation contains ' + self._indentation_type)
            return True
        return False

    def _get_wanted_blank_lines_count(self):
        suite_node = self._indentation_tos.get_latest_suite_node()
        return int(suite_node.parent is None) + 1

    def _reset_newlines(self, spacing, leaf, is_comment=False):
        self._max_new_lines_in_prefix = \
            max(self._max_new_lines_in_prefix, self._newline_count)

        wanted = self._wanted_newline_count
        if wanted is not None:
            # Need to substract one
            blank_lines = self._newline_count - 1
            if wanted > blank_lines and leaf.type != 'endmarker':
                # In case of a comment we don't need to add the issue, yet.
                if not is_comment:
                    # TODO end_pos wrong.
                    code = 302 if wanted == 2 else 301
                    message = "expected %s blank line, found %s" \
                        % (wanted, blank_lines)
                    self.add_issue(spacing, code, message)
                    self._wanted_newline_count = None
            else:
                self._wanted_newline_count = None

        if not is_comment:
            wanted = self._get_wanted_blank_lines_count()
            actual = self._max_new_lines_in_prefix - 1

            val = leaf.value
            needs_lines = (
                val == '@' and leaf.parent.type == 'decorator'
                or (
                    val == 'class'
                    or val == 'async' and leaf.get_next_leaf() == 'def'
                    or val == 'def' and self._previous_leaf != 'async'
                ) and leaf.parent.parent.type != 'decorated'
            )
            if needs_lines and actual < wanted:
                func_or_cls = leaf.parent
                suite = func_or_cls.parent
                if suite.type == 'decorated':
                    suite = suite.parent

                # The first leaf of a file or a suite should not need blank
                # lines.
                if suite.children[int(suite.type == 'suite')] != func_or_cls:
                    code = 302 if wanted == 2 else 301
                    message = "expected %s blank line, found %s" \
                        % (wanted, actual)
                    self.add_issue(spacing, code, message)

            self._max_new_lines_in_prefix = 0

        self._newline_count = 0

    def visit_leaf(self, leaf):
        super().visit_leaf(leaf)
        for part in leaf._split_prefix():
            if part.type == 'spacing':
                # This part is used for the part call after for.
                break
            self._visit_part(part, part.create_spacing_part(), leaf)

        self._analyse_non_prefix(leaf)
        self._visit_part(leaf, part, leaf)

        # Cleanup
        self._last_indentation_tos = self._indentation_tos

        self._new_statement = leaf.type == 'newline'

        # TODO does this work? with brackets and stuff?
        if leaf.type == 'newline' and \
                self._indentation_tos.type == IndentationTypes.BACKSLASH:
            self._indentation_tos = self._indentation_tos.parent

        if leaf.value == ':' and leaf.parent.type in _SUITE_INTRODUCERS:
            self._in_suite_introducer = False
        elif leaf.value == 'elif':
            self._in_suite_introducer = True

        if not self._new_statement:
            self._reset_newlines(part, leaf)
            self._max_blank_lines = 0

        self._previous_leaf = leaf

        return leaf.value

    def _visit_part(self, part, spacing, leaf):
        value = part.value
        type_ = part.type
        if type_ == 'error_leaf':
            return

        if value == ',' and part.parent.type == 'dictorsetmaker':
            self._indentation_tos = self._indentation_tos.parent

        node = self._indentation_tos

        if type_ == 'comment':
            if value.startswith('##'):
                # Whole blocks of # should not raise an error.
                if value.lstrip('#'):
                    self.add_issue(part, 266, "Too many leading '#' for block comment.")
            elif self._on_newline:
                if not re.match(r'#:? ', value) and not value == '#' \
                        and not (value.startswith('#!') and part.start_pos == (1, 0)):
                    self.add_issue(part, 265, "Block comment should start with '# '")
            else:
                if not re.match(r'#:? [^ ]', value):
                    self.add_issue(part, 262, "Inline comment should start with '# '")

            self._reset_newlines(spacing, leaf, is_comment=True)
        elif type_ == 'newline':
            if self._newline_count > self._get_wanted_blank_lines_count():
                self.add_issue(part, 303, "Too many blank lines (%s)" % self._newline_count)
            elif leaf in ('def', 'class') \
                    and leaf.parent.parent.type == 'decorated':
                self.add_issue(part, 304, "Blank lines found after function decorator")

            self._newline_count += 1

        if type_ == 'backslash':
            # TODO is this enough checking? What about ==?
            if node.type != IndentationTypes.BACKSLASH:
                if node.type != IndentationTypes.SUITE:
                    self.add_issue(part, 502, 'The backslash is redundant between brackets')
                else:
                    indentation = node.indentation
                    if self._in_suite_introducer and node.type == IndentationTypes.SUITE:
                        indentation += self._config.indentation

                    self._indentation_tos = BackslashNode(
                        self._config,
                        indentation,
                        part,
                        spacing,
                        parent=self._indentation_tos
                    )
        elif self._on_newline:
            indentation = spacing.value
            if node.type == IndentationTypes.BACKSLASH \
                    and self._previous_part.type == 'newline':
                self._indentation_tos = self._indentation_tos.parent

            if not self._check_tabs_spaces(spacing):
                should_be_indentation = node.indentation
                if type_ == 'comment':
                    # Comments can be dedented. So we have to care for that.
                    n = self._last_indentation_tos
                    while True:
                        if len(indentation) > len(n.indentation):
                            break

                        should_be_indentation = n.indentation

                        self._last_indentation_tos = n
                        if n == node:
                            break
                        n = n.parent

                if self._new_statement:
                    if type_ == 'newline':
                        if indentation:
                            self.add_issue(spacing, 291, 'Trailing whitespace')
                    elif indentation != should_be_indentation:
                        s = '%s %s' % (len(self._config.indentation), self._indentation_type)
                        self.add_issue(part, 111, 'Indentation is not a multiple of ' + s)
                else:
                    if value in '])}':
                        should_be_indentation = node.bracket_indentation
                    else:
                        should_be_indentation = node.indentation
                    if self._in_suite_introducer and indentation == \
                            node.get_latest_suite_node().indentation \
                            + self._config.indentation:
                        self.add_issue(part, 129, "Line with same indent as next logical block")
                    elif indentation != should_be_indentation:
                        if not self._check_tabs_spaces(spacing) and part.value not in \
                                {'\n', '\r\n', '\r'}:
                            if value in '])}':
                                if node.type == IndentationTypes.VERTICAL_BRACKET:
                                    self.add_issue(
                                        part,
                                        124,
                                        "Closing bracket does not match visual indentation"
                                    )
                                else:
                                    self.add_issue(
                                        part,
                                        123,
                                        "Losing bracket does not match "
                                        "indentation of opening bracket's line"
                                    )
                            else:
                                if len(indentation) < len(should_be_indentation):
                                    if node.type == IndentationTypes.VERTICAL_BRACKET:
                                        self.add_issue(
                                            part,
                                            128,
                                            'Continuation line under-indented for visual indent'
                                        )
                                    elif node.type == IndentationTypes.BACKSLASH:
                                        self.add_issue(
                                            part,
                                            122,
                                            'Continuation line missing indentation or outdented'
                                        )
                                    elif node.type == IndentationTypes.IMPLICIT:
                                        self.add_issue(part, 135, 'xxx')
                                    else:
                                        self.add_issue(
                                            part,
                                            121,
                                            'Continuation line under-indented for hanging indent'
                                        )
                                else:
                                    if node.type == IndentationTypes.VERTICAL_BRACKET:
                                        self.add_issue(
                                            part,
                                            127,
                                            'Continuation line over-indented for visual indent'
                                        )
                                    elif node.type == IndentationTypes.IMPLICIT:
                                        self.add_issue(part, 136, 'xxx')
                                    else:
                                        self.add_issue(
                                            part,
                                            126,
                                            'Continuation line over-indented for hanging indent'
                                        )
        else:
            self._check_spacing(part, spacing)

        self._check_line_length(part, spacing)
        # -------------------------------
        # Finalizing. Updating the state.
        # -------------------------------
        if value and value in '()[]{}' and type_ != 'error_leaf' \
                and part.parent.type != 'error_node':
            if value in _OPENING_BRACKETS:
                self._indentation_tos = BracketNode(
                    self._config, part,
                    parent=self._indentation_tos,
                    in_suite_introducer=self._in_suite_introducer
                )
            else:
                assert node.type != IndentationTypes.IMPLICIT
                self._indentation_tos = self._indentation_tos.parent
        elif value in ('=', ':') and self._implicit_indentation_possible \
                and part.parent.type in _IMPLICIT_INDENTATION_TYPES:
            indentation = node.indentation
            self._indentation_tos = ImplicitNode(
                self._config, part, parent=self._indentation_tos
            )

        self._on_newline = type_ in ('newline', 'backslash', 'bom')

        self._previous_part = part
        self._previous_spacing = spacing

    def _check_line_length(self, part, spacing):
        if part.type == 'backslash':
            last_column = part.start_pos[1] + 1
        else:
            last_column = part.end_pos[1]
        if last_column > self._config.max_characters \
                and spacing.start_pos[1] <= self._config.max_characters:
            # Special case for long URLs in multi-line docstrings or comments,
            # but still report the error when the 72 first chars are whitespaces.
            report = True
            if part.type == 'comment':
                splitted = part.value[1:].split()
                if len(splitted) == 1 \
                        and (part.end_pos[1] - len(splitted[0])) < 72:
                    report = False
            if report:
                self.add_issue(
                    part,
                    501,
                    'Line too long (%s > %s characters)' %
                    (last_column, self._config.max_characters),
                )

    def _check_spacing(self, part, spacing):
        def add_if_spaces(*args):
            if spaces:
                return self.add_issue(*args)

        def add_not_spaces(*args):
            if not spaces:
                return self.add_issue(*args)

        spaces = spacing.value
        prev = self._previous_part
        if prev is not None and prev.type == 'error_leaf' or part.type == 'error_leaf':
            return

        type_ = part.type
        if '\t' in spaces:
            self.add_issue(spacing, 223, 'Used tab to separate tokens')
        elif type_ == 'comment':
            if len(spaces) < self._config.spaces_before_comment:
                self.add_issue(spacing, 261, 'At least two spaces before inline comment')
        elif type_ == 'newline':
            add_if_spaces(spacing, 291, 'Trailing whitespace')
        elif len(spaces) > 1:
            self.add_issue(spacing, 221, 'Multiple spaces used')
        else:
            if prev in _OPENING_BRACKETS:
                message = "Whitespace after '%s'" % part.value
                add_if_spaces(spacing, 201, message)
            elif part in _CLOSING_BRACKETS:
                message = "Whitespace before '%s'" % part.value
                add_if_spaces(spacing, 202, message)
            elif part in (',', ';') or part == ':' \
                    and part.parent.type not in _POSSIBLE_SLICE_PARENTS:
                message = "Whitespace before '%s'" % part.value
                add_if_spaces(spacing, 203, message)
            elif prev == ':' and prev.parent.type in _POSSIBLE_SLICE_PARENTS:
                pass  # TODO
            elif prev in (',', ';', ':'):
                add_not_spaces(spacing, 231, "missing whitespace after '%s'")
            elif part == ':':  # Is a subscript
                # TODO
                pass
            elif part in ('*', '**') and part.parent.type not in _NON_STAR_TYPES \
                    or prev in ('*', '**') \
                    and prev.parent.type not in _NON_STAR_TYPES:
                # TODO
                pass
            elif prev in _FACTOR and prev.parent.type == 'factor':
                pass
            elif prev == '@' and prev.parent.type == 'decorator':
                pass  # TODO should probably raise an error if there's a space here
            elif part in _NEEDS_SPACE or prev in _NEEDS_SPACE:
                if part == '=' and part.parent.type in ('argument', 'param') \
                        or prev == '=' and prev.parent.type in ('argument', 'param'):
                    if part == '=':
                        param = part.parent
                    else:
                        param = prev.parent
                    if param.type == 'param' and param.annotation:
                        add_not_spaces(spacing, 252, 'Expected spaces around annotation equals')
                    else:
                        add_if_spaces(
                            spacing,
                            251,
                            'Unexpected spaces around keyword / parameter equals'
                        )
                elif part in _BITWISE_OPERATOR or prev in _BITWISE_OPERATOR:
                    add_not_spaces(
                        spacing,
                        227,
                        'Missing whitespace around bitwise or shift operator'
                    )
                elif part == '%' or prev == '%':
                    add_not_spaces(spacing, 228, 'Missing whitespace around modulo operator')
                else:
                    message_225 = 'Missing whitespace between tokens'
                    add_not_spaces(spacing, 225, message_225)
            elif type_ == 'keyword' or prev.type == 'keyword':
                add_not_spaces(spacing, 275, 'Missing whitespace around keyword')
            else:
                prev_spacing = self._previous_spacing
                if prev in _ALLOW_SPACE and spaces != prev_spacing.value \
                        and '\n' not in self._previous_leaf.prefix \
                        and '\r' not in self._previous_leaf.prefix:
                    message = "Whitespace before operator doesn't match with whitespace after"
                    self.add_issue(spacing, 229, message)

                if spaces and part not in _ALLOW_SPACE and prev not in _ALLOW_SPACE:
                    message_225 = 'Missing whitespace between tokens'
                    # self.add_issue(spacing, 225, message_225)
                    # TODO why only brackets?
                    if part in _OPENING_BRACKETS:
                        message = "Whitespace before '%s'" % part.value
                        add_if_spaces(spacing, 211, message)

    def _analyse_non_prefix(self, leaf):
        typ = leaf.type
        if typ == 'name' and leaf.value in ('l', 'O', 'I'):
            if leaf.is_definition():
                message = "Do not define %s named 'l', 'O', or 'I' one line"
                if leaf.parent.type == 'class' and leaf.parent.name == leaf:
                    self.add_issue(leaf, 742, message % 'classes')
                elif leaf.parent.type == 'function' and leaf.parent.name == leaf:
                    self.add_issue(leaf, 743, message % 'function')
                else:
                    self.add_issuadd_issue(741, message % 'variables', leaf)
        elif leaf.value == ':':
            if isinstance(leaf.parent, (Flow, Scope)) and leaf.parent.type != 'lambdef':
                next_leaf = leaf.get_next_leaf()
                if next_leaf.type != 'newline':
                    if leaf.parent.type == 'funcdef':
                        self.add_issue(next_leaf, 704, 'Multiple statements on one line (def)')
                    else:
                        self.add_issue(next_leaf, 701, 'Multiple statements on one line (colon)')
        elif leaf.value == ';':
            if leaf.get_next_leaf().type in ('newline', 'endmarker'):
                self.add_issue(leaf, 703, 'Statement ends with a semicolon')
            else:
                self.add_issue(leaf, 702, 'Multiple statements on one line (semicolon)')
        elif leaf.value in ('==', '!='):
            comparison = leaf.parent
            index = comparison.children.index(leaf)
            left = comparison.children[index - 1]
            right = comparison.children[index + 1]
            for node in left, right:
                if node.type == 'keyword' or node.type == 'name':
                    if node.value == 'None':
                        message = "comparison to None should be 'if cond is None:'"
                        self.add_issue(leaf, 711, message)
                        break
                    elif node.value in ('True', 'False'):
                        message = "comparison to False/True should be " \
                                  "'if cond is True:' or 'if cond:'"
                        self.add_issue(leaf, 712, message)
                        break
        elif leaf.value in ('in', 'is'):
            comparison = leaf.parent
            if comparison.type == 'comparison' and comparison.parent.type == 'not_test':
                if leaf.value == 'in':
                    self.add_issue(leaf, 713, "test for membership should be 'not in'")
                else:
                    self.add_issue(leaf, 714, "test for object identity should be 'is not'")
        elif typ == 'string':
            # Checking multiline strings
            for i, line in enumerate(leaf.value.splitlines()[1:]):
                indentation = re.match(r'[ \t]*', line).group(0)
                start_pos = leaf.line + i, len(indentation)
                # TODO check multiline indentation.
                start_pos
        elif typ == 'endmarker':
            if self._newline_count >= 2:
                self.add_issue(leaf, 391, 'Blank line at end of file')

    def add_issue(self, node, code, message):
        if self._previous_leaf is not None:
            if self._previous_leaf.search_ancestor('error_node') is not None:
                return
            if self._previous_leaf.type == 'error_leaf':
                return
        if node.search_ancestor('error_node') is not None:
            return
        if code in (901, 903):
            # 901 and 903 are raised by the ErrorFinder.
            super().add_issue(node, code, message)
        else:
            # Skip ErrorFinder here, because it has custom behavior.
            super(ErrorFinder, self).add_issue(node, code, message)


class PEP8NormalizerConfig(ErrorFinderConfig):
    normalizer_class = PEP8Normalizer
    """
    Normalizing to PEP8. Not really implemented, yet.
    """
    def __init__(self, indentation=' ' * 4, hanging_indentation=None,
                 max_characters=79, spaces_before_comment=2):
        self.indentation = indentation
        if hanging_indentation is None:
            hanging_indentation = indentation
        self.hanging_indentation = hanging_indentation
        self.closing_bracket_hanging_indentation = ''
        self.break_after_binary = False
        self.max_characters = max_characters
        self.spaces_before_comment = spaces_before_comment


# TODO this is not yet ready.
# @PEP8Normalizer.register_rule(type='endmarker')
class BlankLineAtEnd(Rule):
    code = 392
    message = 'Blank line at end of file'

    def is_issue(self, leaf):
        return self._newline_count >= 2

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_subprocess.py ===
from __future__ import annotations

import gc
import os
import random
import signal
import subprocess
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from pathlib import Path as SyncPath
from signal import Signals
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
)
from unittest import mock

import pytest

import trio
from trio.testing import Matcher, RaisesGroup

from .. import (
    Event,
    Process,
    _core,
    fail_after,
    move_on_after,
    run_process,
    sleep,
    sleep_forever,
)
from .._core._tests.tutil import skip_if_fbsd_pipes_broken, slow
from ..lowlevel import open_process
from ..testing import MockClock, assert_no_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from types import FrameType

    from typing_extensions import TypeAlias

    from .._abc import ReceiveStream

if sys.platform == "win32":
    SignalType: TypeAlias = None
else:
    SignalType: TypeAlias = Signals

SIGKILL: SignalType
SIGTERM: SignalType
SIGUSR1: SignalType

posix = os.name == "posix"
if (not TYPE_CHECKING and posix) or sys.platform != "win32":
    from signal import SIGKILL, SIGTERM, SIGUSR1
else:
    SIGKILL, SIGTERM, SIGUSR1 = None, None, None


# Since Windows has very few command-line utilities generally available,
# all of our subprocesses are Python processes running short bits of
# (mostly) cross-platform code.
def python(code: str) -> list[str]:
    return [sys.executable, "-u", "-c", "import sys; " + code]


EXIT_TRUE = python("sys.exit(0)")
EXIT_FALSE = python("sys.exit(1)")
CAT = python("sys.stdout.buffer.write(sys.stdin.buffer.read())")

if posix:

    def SLEEP(seconds: int) -> list[str]:
        return ["sleep", str(seconds)]

else:

    def SLEEP(seconds: int) -> list[str]:
        return python(f"import time; time.sleep({seconds})")


@asynccontextmanager
async def open_process_then_kill(  # type: ignore[misc, explicit-any]
    *args: Any,
    **kwargs: Any,
) -> AsyncIterator[Process]:
    proc = await open_process(*args, **kwargs)
    try:
        yield proc
    finally:
        proc.kill()
        await proc.wait()


@asynccontextmanager
async def run_process_in_nursery(  # type: ignore[misc, explicit-any]
    *args: Any,
    **kwargs: Any,
) -> AsyncIterator[Process]:
    async with _core.open_nursery() as nursery:
        kwargs.setdefault("check", False)
        value = await nursery.start(partial(run_process, *args, **kwargs))
        assert isinstance(value, Process)
        proc: Process = value
        yield proc
        nursery.cancel_scope.cancel()


background_process_param = pytest.mark.parametrize(
    "background_process",
    [open_process_then_kill, run_process_in_nursery],
    ids=["open_process", "run_process in nursery"],
)

BackgroundProcessType: TypeAlias = Callable[  # type: ignore[explicit-any]
    ...,
    AbstractAsyncContextManager[Process],
]


@background_process_param
async def test_basic(background_process: BackgroundProcessType) -> None:
    async with background_process(EXIT_TRUE) as proc:
        await proc.wait()
    assert isinstance(proc, Process)
    assert proc._pidfd is None
    assert proc.returncode == 0
    assert repr(proc) == f"<trio.Process {EXIT_TRUE}: exited with status 0>"

    async with background_process(EXIT_FALSE) as proc:
        await proc.wait()
    assert proc.returncode == 1
    assert repr(proc) == "<trio.Process {!r}: {}>".format(
        EXIT_FALSE,
        "exited with status 1",
    )


@background_process_param
async def test_basic_no_pidfd(background_process: BackgroundProcessType) -> None:
    with mock.patch("trio._subprocess.can_try_pidfd_open", new=False):
        async with background_process(EXIT_TRUE) as proc:
            assert proc._pidfd is None
            await proc.wait()
        assert isinstance(proc, Process)
        assert proc._pidfd is None
        assert proc.returncode == 0
        assert repr(proc) == f"<trio.Process {EXIT_TRUE}: exited with status 0>"

        async with background_process(EXIT_FALSE) as proc:
            await proc.wait()
        assert proc.returncode == 1
        assert repr(proc) == "<trio.Process {!r}: {}>".format(
            EXIT_FALSE,
            "exited with status 1",
        )


@background_process_param
async def test_auto_update_returncode(
    background_process: BackgroundProcessType,
) -> None:
    async with background_process(SLEEP(9999)) as p:
        assert p.returncode is None
        assert "running" in repr(p)
        p.kill()
        p._proc.wait()
        assert p.returncode is not None
        assert "exited" in repr(p)
        assert p._pidfd is None
        assert p.returncode is not None


@background_process_param
async def test_multi_wait(background_process: BackgroundProcessType) -> None:
    async with background_process(SLEEP(10)) as proc:
        # Check that wait (including multi-wait) tolerates being cancelled
        async with _core.open_nursery() as nursery:
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

        # Now try waiting for real
        async with _core.open_nursery() as nursery:
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            await wait_all_tasks_blocked()
            proc.kill()


@background_process_param
async def test_multi_wait_no_pidfd(background_process: BackgroundProcessType) -> None:
    with mock.patch("trio._subprocess.can_try_pidfd_open", new=False):
        async with background_process(SLEEP(10)) as proc:
            # Check that wait (including multi-wait) tolerates being cancelled
            async with _core.open_nursery() as nursery:
                nursery.start_soon(proc.wait)
                nursery.start_soon(proc.wait)
                nursery.start_soon(proc.wait)
                await wait_all_tasks_blocked()
                nursery.cancel_scope.cancel()

            # Now try waiting for real
            async with _core.open_nursery() as nursery:
                nursery.start_soon(proc.wait)
                nursery.start_soon(proc.wait)
                nursery.start_soon(proc.wait)
                await wait_all_tasks_blocked()
                proc.kill()


COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR = python(
    "data = sys.stdin.buffer.read(); "
    "sys.stdout.buffer.write(data); "
    "sys.stderr.buffer.write(data[::-1])",
)


@background_process_param
async def test_pipes(background_process: BackgroundProcessType) -> None:
    async with background_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        msg = b"the quick brown fox jumps over the lazy dog"

        async def feed_input() -> None:
            assert proc.stdin is not None
            await proc.stdin.send_all(msg)
            await proc.stdin.aclose()

        async def check_output(stream: ReceiveStream, expected: bytes) -> None:
            seen = bytearray()
            async for chunk in stream:
                seen += chunk
            assert seen == expected

        assert proc.stdout is not None
        assert proc.stderr is not None

        async with _core.open_nursery() as nursery:
            # fail eventually if something is broken
            nursery.cancel_scope.deadline = _core.current_time() + 30.0
            nursery.start_soon(feed_input)
            nursery.start_soon(check_output, proc.stdout, msg)
            nursery.start_soon(check_output, proc.stderr, msg[::-1])

        assert not nursery.cancel_scope.cancelled_caught
        assert await proc.wait() == 0


@background_process_param
async def test_interactive(background_process: BackgroundProcessType) -> None:
    # Test some back-and-forth with a subprocess. This one works like so:
    # in: 32\n
    # out: 0000...0000\n (32 zeroes)
    # err: 1111...1111\n (64 ones)
    # in: 10\n
    # out: 2222222222\n (10 twos)
    # err: 3333....3333\n (20 threes)
    # in: EOF
    # out: EOF
    # err: EOF

    async with background_process(
        python(
            "idx = 0\n"
            "while True:\n"
            "    line = sys.stdin.readline()\n"
            "    if line == '': break\n"
            "    request = int(line.strip())\n"
            "    print(str(idx * 2) * request)\n"
            "    print(str(idx * 2 + 1) * request * 2, file=sys.stderr)\n"
            "    idx += 1\n",
        ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        newline = b"\n" if posix else b"\r\n"

        async def expect(idx: int, request: int) -> None:
            async with _core.open_nursery() as nursery:

                async def drain_one(
                    stream: ReceiveStream,
                    count: int,
                    digit: int,
                ) -> None:
                    while count > 0:
                        result = await stream.receive_some(count)
                        assert result == (f"{digit}".encode() * len(result))
                        count -= len(result)
                    assert count == 0
                    assert await stream.receive_some(len(newline)) == newline

                assert proc.stdout is not None
                assert proc.stderr is not None
                nursery.start_soon(drain_one, proc.stdout, request, idx * 2)
                nursery.start_soon(drain_one, proc.stderr, request * 2, idx * 2 + 1)

        assert proc.stdin is not None
        assert proc.stdout is not None
        assert proc.stderr is not None
        with fail_after(5):
            await proc.stdin.send_all(b"12")
            await sleep(0.1)
            await proc.stdin.send_all(b"345" + newline)
            await expect(0, 12345)
            await proc.stdin.send_all(b"100" + newline + b"200" + newline)
            await expect(1, 100)
            await expect(2, 200)
            await proc.stdin.send_all(b"0" + newline)
            await expect(3, 0)
            await proc.stdin.send_all(b"999999")
            with move_on_after(0.1) as scope:
                await expect(4, 0)
            assert scope.cancelled_caught
            await proc.stdin.send_all(newline)
            await expect(4, 999999)
            await proc.stdin.aclose()
            assert await proc.stdout.receive_some(1) == b""
            assert await proc.stderr.receive_some(1) == b""
            await proc.wait()

    assert proc.returncode == 0


async def test_run() -> None:
    data = bytes(random.randint(0, 255) for _ in range(2**18))

    result = await run_process(
        CAT,
        stdin=data,
        capture_stdout=True,
        capture_stderr=True,
    )
    assert result.args == CAT
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == b""

    result = await run_process(CAT, capture_stdout=True)
    assert result.args == CAT
    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr is None

    result = await run_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=data,
        capture_stdout=True,
        capture_stderr=True,
    )
    assert result.args == COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == data[::-1]

    # invalid combinations
    with pytest.raises(UnicodeError):
        await run_process(CAT, stdin="oh no, it's text")

    pipe_stdout_error = r"^stdout=subprocess\.PIPE is only valid with nursery\.start, since that's the only way to access the pipe(; use nursery\.start or pass the data you want to write directly)*$"
    with pytest.raises(ValueError, match=pipe_stdout_error):
        await run_process(CAT, stdin=subprocess.PIPE)
    with pytest.raises(ValueError, match=pipe_stdout_error):
        await run_process(CAT, stdout=subprocess.PIPE)
    with pytest.raises(
        ValueError,
        match=pipe_stdout_error.replace("stdout", "stderr", 1),
    ):
        await run_process(CAT, stderr=subprocess.PIPE)
    with pytest.raises(
        ValueError,
        match=r"^can't specify both stdout and capture_stdout$",
    ):
        await run_process(CAT, capture_stdout=True, stdout=subprocess.DEVNULL)
    with pytest.raises(
        ValueError,
        match=r"^can't specify both stderr and capture_stderr$",
    ):
        await run_process(CAT, capture_stderr=True, stderr=None)


async def test_run_check() -> None:
    cmd = python("sys.stderr.buffer.write(b'test\\n'); sys.exit(1)")
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        await run_process(cmd, stdin=subprocess.DEVNULL, capture_stderr=True)
    assert excinfo.value.cmd == cmd
    assert excinfo.value.returncode == 1
    assert excinfo.value.stderr == b"test\n"
    assert excinfo.value.stdout is None

    result = await run_process(
        cmd,
        capture_stdout=True,
        capture_stderr=True,
        check=False,
    )
    assert result.args == cmd
    assert result.stdout == b""
    assert result.stderr == b"test\n"
    assert result.returncode == 1


@skip_if_fbsd_pipes_broken
async def test_run_with_broken_pipe() -> None:
    result = await run_process(
        [sys.executable, "-c", "import sys; sys.stdin.close()"],
        stdin=b"x" * 131072,
    )
    assert result.returncode == 0
    assert result.stdout is result.stderr is None


@background_process_param
async def test_stderr_stdout(background_process: BackgroundProcessType) -> None:
    async with background_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        assert proc.stdio is not None
        assert proc.stdout is not None
        assert proc.stderr is None
        await proc.stdio.send_all(b"1234")
        await proc.stdio.send_eof()

        output = []
        while True:
            chunk = await proc.stdio.receive_some(16)
            if chunk == b"":
                break
            output.append(chunk)
        assert b"".join(output) == b"12344321"
    assert proc.returncode == 0

    # equivalent test with run_process()
    result = await run_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=b"1234",
        capture_stdout=True,
        stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0
    assert result.stdout == b"12344321"
    assert result.stderr is None

    # this one hits the branch where stderr=STDOUT but stdout
    # is not redirected
    async with background_process(
        CAT,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        assert proc.stdout is None
        assert proc.stderr is None
        await proc.stdin.aclose()
        await proc.wait()
    assert proc.returncode == 0

    if posix:
        try:
            r, w = os.pipe()

            async with background_process(
                COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
                stdin=subprocess.PIPE,
                stdout=w,
                stderr=subprocess.STDOUT,
            ) as proc:
                os.close(w)
                assert proc.stdio is None
                assert proc.stdout is None
                assert proc.stderr is None
                await proc.stdin.send_all(b"1234")
                await proc.stdin.aclose()
                assert await proc.wait() == 0
                assert os.read(r, 4096) == b"12344321"
                assert os.read(r, 4096) == b""
        finally:
            os.close(r)


async def test_errors() -> None:
    with pytest.raises(TypeError) as excinfo:
        # call-overload on unix, call-arg on windows
        await open_process(["ls"], encoding="utf-8")  # type: ignore
    assert "unbuffered byte streams" in str(excinfo.value)
    assert "the 'encoding' option is not supported" in str(excinfo.value)

    if posix:
        with pytest.raises(TypeError) as excinfo:
            await open_process(["ls"], shell=True)
        with pytest.raises(TypeError) as excinfo:
            await open_process("ls", shell=False)


@background_process_param
async def test_signals(background_process: BackgroundProcessType) -> None:
    async def test_one_signal(
        send_it: Callable[[Process], None],
        signum: signal.Signals | None,
    ) -> None:
        with move_on_after(1.0) as scope:
            async with background_process(SLEEP(3600)) as proc:
                send_it(proc)
                await proc.wait()
        assert not scope.cancelled_caught
        if posix:
            assert signum is not None
            assert proc.returncode == -signum
        else:
            assert proc.returncode != 0

    await test_one_signal(Process.kill, SIGKILL)
    await test_one_signal(Process.terminate, SIGTERM)
    # Test that we can send arbitrary signals.
    #
    # We used to use SIGINT here, but it turns out that the Python interpreter
    # has race conditions that can cause it to explode in weird ways if it
    # tries to handle SIGINT during startup. SIGUSR1's default disposition is
    # to terminate the target process, and Python doesn't try to do anything
    # clever to handle it.
    if (not TYPE_CHECKING and posix) or sys.platform != "win32":
        await test_one_signal(lambda proc: proc.send_signal(SIGUSR1), SIGUSR1)


@pytest.mark.skipif(not posix, reason="POSIX specific")
@background_process_param
async def test_wait_reapable_fails(background_process: BackgroundProcessType) -> None:
    if TYPE_CHECKING and sys.platform == "win32":
        return
    old_sigchld = signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    try:
        # With SIGCHLD disabled, the wait() syscall will wait for the
        # process to exit but then fail with ECHILD. Make sure we
        # support this case as the stdlib subprocess module does.
        async with background_process(SLEEP(3600)) as proc:
            async with _core.open_nursery() as nursery:
                nursery.start_soon(proc.wait)
                await wait_all_tasks_blocked()
                proc.kill()
                nursery.cancel_scope.deadline = _core.current_time() + 1.0
            assert not nursery.cancel_scope.cancelled_caught
            assert proc.returncode == 0  # exit status unknowable, so...
    finally:
        signal.signal(signal.SIGCHLD, old_sigchld)


@pytest.mark.skipif(not posix, reason="POSIX specific")
@background_process_param
async def test_wait_reapable_fails_no_pidfd(
    background_process: BackgroundProcessType,
) -> None:
    if TYPE_CHECKING and sys.platform == "win32":
        return
    with mock.patch("trio._subprocess.can_try_pidfd_open", new=False):
        old_sigchld = signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        try:
            # With SIGCHLD disabled, the wait() syscall will wait for the
            # process to exit but then fail with ECHILD. Make sure we
            # support this case as the stdlib subprocess module does.
            async with background_process(SLEEP(3600)) as proc:
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(proc.wait)
                    await wait_all_tasks_blocked()
                    proc.kill()
                    nursery.cancel_scope.deadline = _core.current_time() + 1.0
                assert not nursery.cancel_scope.cancelled_caught
                assert proc.returncode == 0  # exit status unknowable, so...
        finally:
            signal.signal(signal.SIGCHLD, old_sigchld)


@slow
def test_waitid_eintr() -> None:
    # This only matters on PyPy (where we're coding EINTR handling
    # ourselves) but the test works on all waitid platforms.
    from .._subprocess_platform import wait_child_exiting

    if TYPE_CHECKING and (sys.platform == "win32" or sys.platform == "darwin"):
        return

    if not wait_child_exiting.__module__.endswith("waitid"):
        pytest.skip("waitid only")

    # despite the TYPE_CHECKING early return silencing warnings about signal.SIGALRM etc
    # this import is still checked on win32&darwin and raises [attr-defined].
    # Linux doesn't raise [attr-defined] though, so we need [unused-ignore]
    from .._subprocess_platform.waitid import (  # type: ignore[attr-defined, unused-ignore]
        sync_wait_reapable,
    )

    got_alarm = False
    sleeper = subprocess.Popen(["sleep", "3600"])

    def on_alarm(sig: int, frame: FrameType | None) -> None:
        nonlocal got_alarm
        got_alarm = True
        sleeper.kill()

    old_sigalrm = signal.signal(signal.SIGALRM, on_alarm)
    try:
        signal.alarm(1)
        sync_wait_reapable(sleeper.pid)
        assert sleeper.wait(timeout=1) == -9
    finally:
        if sleeper.returncode is None:  # pragma: no cover
            # We only get here if something fails in the above;
            # if the test passes, wait() will reap the process
            sleeper.kill()
            sleeper.wait()
        signal.signal(signal.SIGALRM, old_sigalrm)


async def test_custom_deliver_cancel() -> None:
    custom_deliver_cancel_called = False

    async def custom_deliver_cancel(proc: Process) -> None:
        nonlocal custom_deliver_cancel_called
        custom_deliver_cancel_called = True
        proc.terminate()
        # Make sure this does get cancelled when the process exits, and that
        # the process really exited.
        try:
            await sleep_forever()
        finally:
            assert proc.returncode is not None

    async with _core.open_nursery() as nursery:
        nursery.start_soon(
            partial(run_process, SLEEP(9999), deliver_cancel=custom_deliver_cancel),
        )
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()

    assert custom_deliver_cancel_called


def test_bad_deliver_cancel() -> None:
    async def custom_deliver_cancel(proc: Process) -> None:
        proc.terminate()
        raise ValueError("foo")

    async def do_stuff() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(
                partial(run_process, SLEEP(9999), deliver_cancel=custom_deliver_cancel),
            )
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    # double wrap from our nursery + the internal nursery
    with RaisesGroup(RaisesGroup(Matcher(ValueError, "^foo$"))):
        _core.run(do_stuff, strict_exception_groups=True)


async def test_warn_on_failed_cancel_terminate(monkeypatch: pytest.MonkeyPatch) -> None:
    original_terminate = Process.terminate

    def broken_terminate(self: Process) -> NoReturn:
        original_terminate(self)
        raise OSError("whoops")

    monkeypatch.setattr(Process, "terminate", broken_terminate)

    with pytest.warns(RuntimeWarning, match=".*whoops.*"):  # noqa: PT031
        async with _core.open_nursery() as nursery:
            nursery.start_soon(run_process, SLEEP(9999))
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()


@pytest.mark.skipif(not posix, reason="posix only")
async def test_warn_on_cancel_SIGKILL_escalation(
    autojump_clock: MockClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Process, "terminate", lambda *args: None)

    with pytest.warns(RuntimeWarning, match=".*ignored SIGTERM.*"):  # noqa: PT031
        async with _core.open_nursery() as nursery:
            nursery.start_soon(run_process, SLEEP(9999))
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()


# the background_process_param exercises a lot of run_process cases, but it uses
# check=False, so lets have a test that uses check=True as well
async def test_run_process_background_fail() -> None:
    with RaisesGroup(subprocess.CalledProcessError):
        async with _core.open_nursery() as nursery:
            value = await nursery.start(run_process, EXIT_FALSE)
            assert isinstance(value, Process)
            proc: Process = value
    assert proc.returncode == 1


@pytest.mark.skipif(
    not SyncPath("/dev/fd").exists(),
    reason="requires a way to iterate through open files",
)
async def test_for_leaking_fds() -> None:
    gc.collect()  # address possible flakiness on PyPy

    starting_fds = set(SyncPath("/dev/fd").iterdir())
    await run_process(EXIT_TRUE)
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds

    with pytest.raises(subprocess.CalledProcessError):
        await run_process(EXIT_FALSE)
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds

    with pytest.raises(PermissionError):
        await run_process(["/dev/fd/0"])
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds


async def test_run_process_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # There's probably less extreme ways of triggering errors inside the nursery
    # in run_process.
    async def very_broken_open(*args: object, **kwargs: object) -> str:
        return "oops"

    monkeypatch.setattr(trio._subprocess, "open_process", very_broken_open)
    with RaisesGroup(AttributeError, AttributeError):
        await run_process(EXIT_TRUE, capture_stdout=True)


# regression test for #2209
async def test_subprocess_pidfd_unnotified() -> None:
    noticed_exit = None

    async def wait_and_tell(proc: Process) -> None:
        nonlocal noticed_exit
        noticed_exit = Event()
        await proc.wait()
        noticed_exit.set()

    proc = await open_process(SLEEP(9999))
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_and_tell, proc)
        await wait_all_tasks_blocked()
        assert isinstance(noticed_exit, Event)
        proc.terminate()
        # without giving trio a chance to do so,
        with assert_no_checkpoints():
            # wait until the process has actually exited;
            proc._proc.wait()
            # force a call to poll (that closes the pidfd on linux)
            proc.poll()
        with move_on_after(5):
            # Some platforms use threads to wait for exit, so it might take a bit
            # for everything to notice
            await noticed_exit.wait()
        assert noticed_exit.is_set(), "child task wasn't woken after poll, DEADLOCK"

# === NexusCore/openenv\Lib\site-packages\jinja2\utils.py ===
import enum
import json
import os
import re
import typing as t
from collections import abc
from collections import deque
from random import choice
from random import randrange
from threading import Lock
from types import CodeType
from urllib.parse import quote_from_bytes

import markupsafe

if t.TYPE_CHECKING:
    import typing_extensions as te

F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class _MissingType:
    def __repr__(self) -> str:
        return "missing"

    def __reduce__(self) -> str:
        return "missing"


missing: t.Any = _MissingType()
"""Special singleton representing missing values for the runtime."""

internal_code: t.MutableSet[CodeType] = set()

concat = "".join


def pass_context(f: F) -> F:
    """Pass the :class:`~jinja2.runtime.Context` as the first argument
    to the decorated function when called while rendering a template.

    Can be used on functions, filters, and tests.

    If only ``Context.eval_context`` is needed, use
    :func:`pass_eval_context`. If only ``Context.environment`` is
    needed, use :func:`pass_environment`.

    .. versionadded:: 3.0.0
        Replaces ``contextfunction`` and ``contextfilter``.
    """
    f.jinja_pass_arg = _PassArg.context  # type: ignore
    return f


def pass_eval_context(f: F) -> F:
    """Pass the :class:`~jinja2.nodes.EvalContext` as the first argument
    to the decorated function when called while rendering a template.
    See :ref:`eval-context`.

    Can be used on functions, filters, and tests.

    If only ``EvalContext.environment`` is needed, use
    :func:`pass_environment`.

    .. versionadded:: 3.0.0
        Replaces ``evalcontextfunction`` and ``evalcontextfilter``.
    """
    f.jinja_pass_arg = _PassArg.eval_context  # type: ignore
    return f


def pass_environment(f: F) -> F:
    """Pass the :class:`~jinja2.Environment` as the first argument to
    the decorated function when called while rendering a template.

    Can be used on functions, filters, and tests.

    .. versionadded:: 3.0.0
        Replaces ``environmentfunction`` and ``environmentfilter``.
    """
    f.jinja_pass_arg = _PassArg.environment  # type: ignore
    return f


class _PassArg(enum.Enum):
    context = enum.auto()
    eval_context = enum.auto()
    environment = enum.auto()

    @classmethod
    def from_obj(cls, obj: F) -> t.Optional["_PassArg"]:
        if hasattr(obj, "jinja_pass_arg"):
            return obj.jinja_pass_arg  # type: ignore

        return None


def internalcode(f: F) -> F:
    """Marks the function as internally used"""
    internal_code.add(f.__code__)
    return f


def is_undefined(obj: t.Any) -> bool:
    """Check if the object passed is undefined.  This does nothing more than
    performing an instance check against :class:`Undefined` but looks nicer.
    This can be used for custom filters or tests that want to react to
    undefined variables.  For example a custom default filter can look like
    this::

        def default(var, default=''):
            if is_undefined(var):
                return default
            return var
    """
    from .runtime import Undefined

    return isinstance(obj, Undefined)


def consume(iterable: t.Iterable[t.Any]) -> None:
    """Consumes an iterable without doing anything with it."""
    for _ in iterable:
        pass


def clear_caches() -> None:
    """Jinja keeps internal caches for environments and lexers.  These are
    used so that Jinja doesn't have to recreate environments and lexers all
    the time.  Normally you don't have to care about that but if you are
    measuring memory consumption you may want to clean the caches.
    """
    from .environment import get_spontaneous_environment
    from .lexer import _lexer_cache

    get_spontaneous_environment.cache_clear()
    _lexer_cache.clear()


def import_string(import_name: str, silent: bool = False) -> t.Any:
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If the `silent` is True the return value will be `None` if the import
    fails.

    :return: imported object
    """
    try:
        if ":" in import_name:
            module, obj = import_name.split(":", 1)
        elif "." in import_name:
            module, _, obj = import_name.rpartition(".")
        else:
            return __import__(import_name)
        return getattr(__import__(module, None, None, [obj]), obj)
    except (ImportError, AttributeError):
        if not silent:
            raise


def open_if_exists(filename: str, mode: str = "rb") -> t.Optional[t.IO[t.Any]]:
    """Returns a file descriptor for the filename if that file exists,
    otherwise ``None``.
    """
    if not os.path.isfile(filename):
        return None

    return open(filename, mode)


def object_type_repr(obj: t.Any) -> str:
    """Returns the name of the object's type.  For some recognized
    singletons the name of the object is returned instead. (For
    example for `None` and `Ellipsis`).
    """
    if obj is None:
        return "None"
    elif obj is Ellipsis:
        return "Ellipsis"

    cls = type(obj)

    if cls.__module__ == "builtins":
        return f"{cls.__name__} object"

    return f"{cls.__module__}.{cls.__name__} object"


def pformat(obj: t.Any) -> str:
    """Format an object using :func:`pprint.pformat`."""
    from pprint import pformat

    return pformat(obj)


_http_re = re.compile(
    r"""
    ^
    (
        (https?://|www\.)  # scheme or www
        (([\w%-]+\.)+)?  # subdomain
        (
            [a-z]{2,63}  # basic tld
        |
            xn--[\w%]{2,59}  # idna tld
        )
    |
        ([\w%-]{2,63}\.)+  # basic domain
        (com|net|int|edu|gov|org|info|mil)  # basic tld
    |
        (https?://)  # scheme
        (
            (([\d]{1,3})(\.[\d]{1,3}){3})  # IPv4
        |
            (\[([\da-f]{0,4}:){2}([\da-f]{0,4}:?){1,6}])  # IPv6
        )
    )
    (?::[\d]{1,5})?  # port
    (?:[/?#]\S*)?  # path, query, and fragment
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)
_email_re = re.compile(r"^\S+@\w[\w.-]*\.\w+$")


def urlize(
    text: str,
    trim_url_limit: t.Optional[int] = None,
    rel: t.Optional[str] = None,
    target: t.Optional[str] = None,
    extra_schemes: t.Optional[t.Iterable[str]] = None,
) -> str:
    """Convert URLs in text into clickable links.

    This may not recognize links in some situations. Usually, a more
    comprehensive formatter, such as a Markdown library, is a better
    choice.

    Works on ``http://``, ``https://``, ``www.``, ``mailto:``, and email
    addresses. Links with trailing punctuation (periods, commas, closing
    parentheses) and leading punctuation (opening parentheses) are
    recognized excluding the punctuation. Email addresses that include
    header fields are not recognized (for example,
    ``mailto:address@example.com?cc=copy@example.com``).

    :param text: Original text containing URLs to link.
    :param trim_url_limit: Shorten displayed URL values to this length.
    :param target: Add the ``target`` attribute to links.
    :param rel: Add the ``rel`` attribute to links.
    :param extra_schemes: Recognize URLs that start with these schemes
        in addition to the default behavior.

    .. versionchanged:: 3.0
        The ``extra_schemes`` parameter was added.

    .. versionchanged:: 3.0
        Generate ``https://`` links for URLs without a scheme.

    .. versionchanged:: 3.0
        The parsing rules were updated. Recognize email addresses with
        or without the ``mailto:`` scheme. Validate IP addresses. Ignore
        parentheses and brackets in more cases.
    """
    if trim_url_limit is not None:

        def trim_url(x: str) -> str:
            if len(x) > trim_url_limit:
                return f"{x[:trim_url_limit]}..."

            return x

    else:

        def trim_url(x: str) -> str:
            return x

    words = re.split(r"(\s+)", str(markupsafe.escape(text)))
    rel_attr = f' rel="{markupsafe.escape(rel)}"' if rel else ""
    target_attr = f' target="{markupsafe.escape(target)}"' if target else ""

    for i, word in enumerate(words):
        head, middle, tail = "", word, ""
        match = re.match(r"^([(<]|&lt;)+", middle)

        if match:
            head = match.group()
            middle = middle[match.end() :]

        # Unlike lead, which is anchored to the start of the string,
        # need to check that the string ends with any of the characters
        # before trying to match all of them, to avoid backtracking.
        if middle.endswith((")", ">", ".", ",", "\n", "&gt;")):
            match = re.search(r"([)>.,\n]|&gt;)+$", middle)

            if match:
                tail = match.group()
                middle = middle[: match.start()]

        # Prefer balancing parentheses in URLs instead of ignoring a
        # trailing character.
        for start_char, end_char in ("(", ")"), ("<", ">"), ("&lt;", "&gt;"):
            start_count = middle.count(start_char)

            if start_count <= middle.count(end_char):
                # Balanced, or lighter on the left
                continue

            # Move as many as possible from the tail to balance
            for _ in range(min(start_count, tail.count(end_char))):
                end_index = tail.index(end_char) + len(end_char)
                # Move anything in the tail before the end char too
                middle += tail[:end_index]
                tail = tail[end_index:]

        if _http_re.match(middle):
            if middle.startswith("https://") or middle.startswith("http://"):
                middle = (
                    f'<a href="{middle}"{rel_attr}{target_attr}>{trim_url(middle)}</a>'
                )
            else:
                middle = (
                    f'<a href="https://{middle}"{rel_attr}{target_attr}>'
                    f"{trim_url(middle)}</a>"
                )

        elif middle.startswith("mailto:") and _email_re.match(middle[7:]):
            middle = f'<a href="{middle}">{middle[7:]}</a>'

        elif (
            "@" in middle
            and not middle.startswith("www.")
            # ignore values like `@a@b`
            and not middle.startswith("@")
            and ":" not in middle
            and _email_re.match(middle)
        ):
            middle = f'<a href="mailto:{middle}">{middle}</a>'

        elif extra_schemes is not None:
            for scheme in extra_schemes:
                if middle != scheme and middle.startswith(scheme):
                    middle = f'<a href="{middle}"{rel_attr}{target_attr}>{middle}</a>'

        words[i] = f"{head}{middle}{tail}"

    return "".join(words)


def generate_lorem_ipsum(
    n: int = 5, html: bool = True, min: int = 20, max: int = 100
) -> str:
    """Generate some lorem ipsum for the template."""
    from .constants import LOREM_IPSUM_WORDS

    words = LOREM_IPSUM_WORDS.split()
    result = []

    for _ in range(n):
        next_capitalized = True
        last_comma = last_fullstop = 0
        word = None
        last = None
        p = []

        # each paragraph contains out of 20 to 100 words.
        for idx, _ in enumerate(range(randrange(min, max))):
            while True:
                word = choice(words)
                if word != last:
                    last = word
                    break
            if next_capitalized:
                word = word.capitalize()
                next_capitalized = False
            # add commas
            if idx - randrange(3, 8) > last_comma:
                last_comma = idx
                last_fullstop += 2
                word += ","
            # add end of sentences
            if idx - randrange(10, 20) > last_fullstop:
                last_comma = last_fullstop = idx
                word += "."
                next_capitalized = True
            p.append(word)

        # ensure that the paragraph ends with a dot.
        p_str = " ".join(p)

        if p_str.endswith(","):
            p_str = p_str[:-1] + "."
        elif not p_str.endswith("."):
            p_str += "."

        result.append(p_str)

    if not html:
        return "\n\n".join(result)
    return markupsafe.Markup(
        "\n".join(f"<p>{markupsafe.escape(x)}</p>" for x in result)
    )


def url_quote(obj: t.Any, charset: str = "utf-8", for_qs: bool = False) -> str:
    """Quote a string for use in a URL using the given charset.

    :param obj: String or bytes to quote. Other types are converted to
        string then encoded to bytes using the given charset.
    :param charset: Encode text to bytes using this charset.
    :param for_qs: Quote "/" and use "+" for spaces.
    """
    if not isinstance(obj, bytes):
        if not isinstance(obj, str):
            obj = str(obj)

        obj = obj.encode(charset)

    safe = b"" if for_qs else b"/"
    rv = quote_from_bytes(obj, safe)

    if for_qs:
        rv = rv.replace("%20", "+")

    return rv


@abc.MutableMapping.register
class LRUCache:
    """A simple LRU Cache implementation."""

    # this is fast for small capacities (something below 1000) but doesn't
    # scale.  But as long as it's only used as storage for templates this
    # won't do any harm.

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._mapping: t.Dict[t.Any, t.Any] = {}
        self._queue: te.Deque[t.Any] = deque()
        self._postinit()

    def _postinit(self) -> None:
        # alias all queue methods for faster lookup
        self._popleft = self._queue.popleft
        self._pop = self._queue.pop
        self._remove = self._queue.remove
        self._wlock = Lock()
        self._append = self._queue.append

    def __getstate__(self) -> t.Mapping[str, t.Any]:
        return {
            "capacity": self.capacity,
            "_mapping": self._mapping,
            "_queue": self._queue,
        }

    def __setstate__(self, d: t.Mapping[str, t.Any]) -> None:
        self.__dict__.update(d)
        self._postinit()

    def __getnewargs__(self) -> t.Tuple[t.Any, ...]:
        return (self.capacity,)

    def copy(self) -> "te.Self":
        """Return a shallow copy of the instance."""
        rv = self.__class__(self.capacity)
        rv._mapping.update(self._mapping)
        rv._queue.extend(self._queue)
        return rv

    def get(self, key: t.Any, default: t.Any = None) -> t.Any:
        """Return an item from the cache dict or `default`"""
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key: t.Any, default: t.Any = None) -> t.Any:
        """Set `default` if the key is not in the cache otherwise
        leave unchanged. Return the value of this key.
        """
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def clear(self) -> None:
        """Clear the cache."""
        with self._wlock:
            self._mapping.clear()
            self._queue.clear()

    def __contains__(self, key: t.Any) -> bool:
        """Check if a key exists in this cache."""
        return key in self._mapping

    def __len__(self) -> int:
        """Return the current size of the cache."""
        return len(self._mapping)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._mapping!r}>"

    def __getitem__(self, key: t.Any) -> t.Any:
        """Get an item from the cache. Moves the item up so that it has the
        highest priority then.

        Raise a `KeyError` if it does not exist.
        """
        with self._wlock:
            rv = self._mapping[key]

            if self._queue[-1] != key:
                try:
                    self._remove(key)
                except ValueError:
                    # if something removed the key from the container
                    # when we read, ignore the ValueError that we would
                    # get otherwise.
                    pass

                self._append(key)

            return rv

    def __setitem__(self, key: t.Any, value: t.Any) -> None:
        """Sets the value for an item. Moves the item up so that it
        has the highest priority then.
        """
        with self._wlock:
            if key in self._mapping:
                self._remove(key)
            elif len(self._mapping) == self.capacity:
                del self._mapping[self._popleft()]

            self._append(key)
            self._mapping[key] = value

    def __delitem__(self, key: t.Any) -> None:
        """Remove an item from the cache dict.
        Raise a `KeyError` if it does not exist.
        """
        with self._wlock:
            del self._mapping[key]

            try:
                self._remove(key)
            except ValueError:
                pass

    def items(self) -> t.Iterable[t.Tuple[t.Any, t.Any]]:
        """Return a list of items."""
        result = [(key, self._mapping[key]) for key in list(self._queue)]
        result.reverse()
        return result

    def values(self) -> t.Iterable[t.Any]:
        """Return a list of all values."""
        return [x[1] for x in self.items()]

    def keys(self) -> t.Iterable[t.Any]:
        """Return a list of all keys ordered by most recent usage."""
        return list(self)

    def __iter__(self) -> t.Iterator[t.Any]:
        return reversed(tuple(self._queue))

    def __reversed__(self) -> t.Iterator[t.Any]:
        """Iterate over the keys in the cache dict, oldest items
        coming first.
        """
        return iter(tuple(self._queue))

    __copy__ = copy


def select_autoescape(
    enabled_extensions: t.Collection[str] = ("html", "htm", "xml"),
    disabled_extensions: t.Collection[str] = (),
    default_for_string: bool = True,
    default: bool = False,
) -> t.Callable[[t.Optional[str]], bool]:
    """Intelligently sets the initial value of autoescaping based on the
    filename of the template.  This is the recommended way to configure
    autoescaping if you do not want to write a custom function yourself.

    If you want to enable it for all templates created from strings or
    for all templates with `.html` and `.xml` extensions::

        from jinja2 import Environment, select_autoescape
        env = Environment(autoescape=select_autoescape(
            enabled_extensions=('html', 'xml'),
            default_for_string=True,
        ))

    Example configuration to turn it on at all times except if the template
    ends with `.txt`::

        from jinja2 import Environment, select_autoescape
        env = Environment(autoescape=select_autoescape(
            disabled_extensions=('txt',),
            default_for_string=True,
            default=True,
        ))

    The `enabled_extensions` is an iterable of all the extensions that
    autoescaping should be enabled for.  Likewise `disabled_extensions` is
    a list of all templates it should be disabled for.  If a template is
    loaded from a string then the default from `default_for_string` is used.
    If nothing matches then the initial value of autoescaping is set to the
    value of `default`.

    For security reasons this function operates case insensitive.

    .. versionadded:: 2.9
    """
    enabled_patterns = tuple(f".{x.lstrip('.').lower()}" for x in enabled_extensions)
    disabled_patterns = tuple(f".{x.lstrip('.').lower()}" for x in disabled_extensions)

    def autoescape(template_name: t.Optional[str]) -> bool:
        if template_name is None:
            return default_for_string
        template_name = template_name.lower()
        if template_name.endswith(enabled_patterns):
            return True
        if template_name.endswith(disabled_patterns):
            return False
        return default

    return autoescape


def htmlsafe_json_dumps(
    obj: t.Any, dumps: t.Optional[t.Callable[..., str]] = None, **kwargs: t.Any
) -> markupsafe.Markup:
    """Serialize an object to a string of JSON with :func:`json.dumps`,
    then replace HTML-unsafe characters with Unicode escapes and mark
    the result safe with :class:`~markupsafe.Markup`.

    This is available in templates as the ``|tojson`` filter.

    The following characters are escaped: ``<``, ``>``, ``&``, ``'``.

    The returned string is safe to render in HTML documents and
    ``<script>`` tags. The exception is in HTML attributes that are
    double quoted; either use single quotes or the ``|forceescape``
    filter.

    :param obj: The object to serialize to JSON.
    :param dumps: The ``dumps`` function to use. Defaults to
        ``env.policies["json.dumps_function"]``, which defaults to
        :func:`json.dumps`.
    :param kwargs: Extra arguments to pass to ``dumps``. Merged onto
        ``env.policies["json.dumps_kwargs"]``.

    .. versionchanged:: 3.0
        The ``dumper`` parameter is renamed to ``dumps``.

    .. versionadded:: 2.9
    """
    if dumps is None:
        dumps = json.dumps

    return markupsafe.Markup(
        dumps(obj, **kwargs)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )


class Cycler:
    """Cycle through values by yield them one at a time, then restarting
    once the end is reached. Available as ``cycler`` in templates.

    Similar to ``loop.cycle``, but can be used outside loops or across
    multiple loops. For example, render a list of folders and files in a
    list, alternating giving them "odd" and "even" classes.

    .. code-block:: html+jinja

        {% set row_class = cycler("odd", "even") %}
        <ul class="browser">
        {% for folder in folders %}
          <li class="folder {{ row_class.next() }}">{{ folder }}
        {% endfor %}
        {% for file in files %}
          <li class="file {{ row_class.next() }}">{{ file }}
        {% endfor %}
        </ul>

    :param items: Each positional argument will be yielded in the order
        given for each cycle.

    .. versionadded:: 2.1
    """

    def __init__(self, *items: t.Any) -> None:
        if not items:
            raise RuntimeError("at least one item has to be provided")
        self.items = items
        self.pos = 0

    def reset(self) -> None:
        """Resets the current item to the first item."""
        self.pos = 0

    @property
    def current(self) -> t.Any:
        """Return the current item. Equivalent to the item that will be
        returned next time :meth:`next` is called.
        """
        return self.items[self.pos]

    def next(self) -> t.Any:
        """Return the current item, then advance :attr:`current` to the
        next item.
        """
        rv = self.current
        self.pos = (self.pos + 1) % len(self.items)
        return rv

    __next__ = next


class Joiner:
    """A joining helper for templates."""

    def __init__(self, sep: str = ", ") -> None:
        self.sep = sep
        self.used = False

    def __call__(self) -> str:
        if not self.used:
            self.used = True
            return ""
        return self.sep


class Namespace:
    """A namespace object that can hold arbitrary attributes.  It may be
    initialized from a dictionary or with keyword arguments."""

    def __init__(*args: t.Any, **kwargs: t.Any) -> None:  # noqa: B902
        self, args = args[0], args[1:]
        self.__attrs = dict(*args, **kwargs)

    def __getattribute__(self, name: str) -> t.Any:
        # __class__ is needed for the awaitable check in async mode
        if name in {"_Namespace__attrs", "__class__"}:
            return object.__getattribute__(self, name)
        try:
            return self.__attrs[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setitem__(self, name: str, value: t.Any) -> None:
        self.__attrs[name] = value

    def __repr__(self) -> str:
        return f"<Namespace {self.__attrs!r}>"

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\base_aws_llm.py ===
import hashlib
import json
import os
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    cast,
    get_args,
)

import httpx
from pydantic import BaseModel

from litellm._logging import verbose_logger
from litellm.caching.caching import DualCache
from litellm.constants import BEDROCK_INVOKE_PROVIDERS_LITERAL, BEDROCK_MAX_POLICY_SIZE
from litellm.litellm_core_utils.dd_tracing import tracer
from litellm.secret_managers.main import get_secret

if TYPE_CHECKING:
    from botocore.awsrequest import AWSPreparedRequest
    from botocore.credentials import Credentials
else:
    Credentials = Any
    AWSPreparedRequest = Any


class Boto3CredentialsInfo(BaseModel):
    credentials: Credentials
    aws_region_name: str
    aws_bedrock_runtime_endpoint: Optional[str]


class AwsAuthError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url="https://us-west-2.console.aws.amazon.com/bedrock"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class BaseAWSLLM:
    def __init__(self) -> None:
        self.iam_cache = DualCache()
        super().__init__()
        self.aws_authentication_params = [
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_session_token",
            "aws_region_name",
            "aws_session_name",
            "aws_profile_name",
            "aws_role_name",
            "aws_web_identity_token",
            "aws_sts_endpoint",
            "aws_bedrock_runtime_endpoint",
        ]

    def get_cache_key(self, credential_args: Dict[str, Optional[str]]) -> str:
        """
        Generate a unique cache key based on the credential arguments.
        """
        # Convert credential arguments to a JSON string and hash it to create a unique key
        credential_str = json.dumps(credential_args, sort_keys=True)
        return hashlib.sha256(credential_str.encode()).hexdigest()

    @tracer.wrap()
    def get_credentials(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        aws_region_name: Optional[str] = None,
        aws_session_name: Optional[str] = None,
        aws_profile_name: Optional[str] = None,
        aws_role_name: Optional[str] = None,
        aws_web_identity_token: Optional[str] = None,
        aws_sts_endpoint: Optional[str] = None,
    ):
        """
        Return a boto3.Credentials object
        """
        ## CHECK IS  'os.environ/' passed in
        params_to_check: List[Optional[str]] = [
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            aws_region_name,
            aws_session_name,
            aws_profile_name,
            aws_role_name,
            aws_web_identity_token,
            aws_sts_endpoint,
        ]

        # Iterate over parameters and update if needed
        for i, param in enumerate(params_to_check):
            if param and param.startswith("os.environ/"):
                _v = get_secret(param)
                if _v is not None and isinstance(_v, str):
                    params_to_check[i] = _v
            elif param is None:  # check if uppercase value in env
                key = self.aws_authentication_params[i]
                if key.upper() in os.environ:
                    params_to_check[i] = os.getenv(key)

        # Assign updated values back to parameters
        (
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            aws_region_name,
            aws_session_name,
            aws_profile_name,
            aws_role_name,
            aws_web_identity_token,
            aws_sts_endpoint,
        ) = params_to_check

        verbose_logger.debug(
            "in get credentials\n"
            "aws_access_key_id=%s\n"
            "aws_secret_access_key=%s\n"
            "aws_session_token=%s\n"
            "aws_region_name=%s\n"
            "aws_session_name=%s\n"
            "aws_profile_name=%s\n"
            "aws_role_name=%s\n"
            "aws_web_identity_token=%s\n"
            "aws_sts_endpoint=%s",
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            aws_region_name,
            aws_session_name,
            aws_profile_name,
            aws_role_name,
            aws_web_identity_token,
            aws_sts_endpoint,
        )

        # create cache key for non-expiring auth flows
        args = {k: v for k, v in locals().items() if k.startswith("aws_")}

        cache_key = self.get_cache_key(args)
        _cached_credentials = self.iam_cache.get_cache(cache_key)
        if _cached_credentials:
            return _cached_credentials

        #########################################################
        # Handle diff boto3 auth flows
        # for each helper
        # Return:
        #   Credentials - boto3.Credentials
        #   cache ttl - Optional[int]. If None, the credentials are not cached. Some auth flows have no expiry time.
        #########################################################
        if (
            aws_web_identity_token is not None
            and aws_role_name is not None
            and aws_session_name is not None
        ):
            credentials, _cache_ttl = self._auth_with_web_identity_token(
                aws_web_identity_token=aws_web_identity_token,
                aws_role_name=aws_role_name,
                aws_session_name=aws_session_name,
                aws_region_name=aws_region_name,
                aws_sts_endpoint=aws_sts_endpoint,
            )
        elif aws_role_name is not None and aws_session_name is not None:
            credentials, _cache_ttl = self._auth_with_aws_role(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_role_name=aws_role_name,
                aws_session_name=aws_session_name,
            )

        elif aws_profile_name is not None:  ### CHECK SESSION ###
            credentials, _cache_ttl = self._auth_with_aws_profile(aws_profile_name)
        elif (
            aws_access_key_id is not None
            and aws_secret_access_key is not None
            and aws_session_token is not None
        ):
            credentials, _cache_ttl = self._auth_with_aws_session_token(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        elif (
            aws_access_key_id is not None
            and aws_secret_access_key is not None
            and aws_region_name is not None
        ):
            credentials, _cache_ttl = self._auth_with_access_key_and_secret_key(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_region_name=aws_region_name,
            )
        else:
            credentials, _cache_ttl = self._auth_with_env_vars()

        self.iam_cache.set_cache(cache_key, credentials, ttl=_cache_ttl)
        return credentials

    def _get_aws_region_from_model_arn(self, model: Optional[str]) -> Optional[str]:
        try:
            # First check if the string contains the expected prefix
            if not isinstance(model, str) or "arn:aws:bedrock" not in model:
                return None

            # Split the ARN and check if we have enough parts
            parts = model.split(":")
            if len(parts) < 4:
                return None

            # Get the region from the correct position
            region = parts[3]
            if not region:  # Check if region is empty
                return None

            return region
        except Exception:
            # Catch any unexpected errors and return None
            return None

    @staticmethod
    def _get_provider_from_model_path(
        model_path: str,
    ) -> Optional[BEDROCK_INVOKE_PROVIDERS_LITERAL]:
        """
        Helper function to get the provider from a model path with format: provider/model-name

        Args:
            model_path (str): The model path (e.g., 'llama/arn:aws:bedrock:us-east-1:086734376398:imported-model/r4c4kewx2s0n' or 'anthropic/model-name')

        Returns:
            Optional[str]: The provider name, or None if no valid provider found
        """
        parts = model_path.split("/")
        if len(parts) >= 1:
            provider = parts[0]
            if provider in get_args(BEDROCK_INVOKE_PROVIDERS_LITERAL):
                return cast(BEDROCK_INVOKE_PROVIDERS_LITERAL, provider)
        return None

    @staticmethod
    def get_bedrock_invoke_provider(
        model: str,
    ) -> Optional[BEDROCK_INVOKE_PROVIDERS_LITERAL]:
        """
        Helper function to get the bedrock provider from the model

        handles 3 scenarions:
        1. model=invoke/anthropic.claude-3-5-sonnet-20240620-v1:0 -> Returns `anthropic`
        2. model=anthropic.claude-3-5-sonnet-20240620-v1:0 -> Returns `anthropic`
        3. model=llama/arn:aws:bedrock:us-east-1:086734376398:imported-model/r4c4kewx2s0n -> Returns `llama`
        4. model=us.amazon.nova-pro-v1:0 -> Returns `nova`
        """
        if model.startswith("invoke/"):
            model = model.replace("invoke/", "", 1)

        _split_model = model.split(".")[0]
        if _split_model in get_args(BEDROCK_INVOKE_PROVIDERS_LITERAL):
            return cast(BEDROCK_INVOKE_PROVIDERS_LITERAL, _split_model)

        # If not a known provider, check for pattern with two slashes
        provider = BaseAWSLLM._get_provider_from_model_path(model)
        if provider is not None:
            return provider

        # check if provider == "nova"
        if "nova" in model:
            return "nova"
        else:
            for provider in get_args(BEDROCK_INVOKE_PROVIDERS_LITERAL):
                if provider in model:
                    return provider
        return None

    def _get_aws_region_name(
        self,
        optional_params: dict,
        model: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """
        Get the AWS region name from the environment variables.

        Parameters:
            optional_params (dict): Optional parameters for the model call
            model (str): The model name
            model_id (str): The model ID. This is the ARN of the model, if passed in as a separate param.

        Returns:
            str: The AWS region name
        """
        aws_region_name = optional_params.get("aws_region_name", None)
        ### SET REGION NAME ###
        if aws_region_name is None:
            # check model arn #
            if model_id is not None:
                aws_region_name = self._get_aws_region_from_model_arn(model_id)
            else:
                aws_region_name = self._get_aws_region_from_model_arn(model)
            # check env #
            litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)

            if (
                aws_region_name is None
                and litellm_aws_region_name is not None
                and isinstance(litellm_aws_region_name, str)
            ):
                aws_region_name = litellm_aws_region_name

            standard_aws_region_name = get_secret("AWS_REGION", None)
            if (
                aws_region_name is None
                and standard_aws_region_name is not None
                and isinstance(standard_aws_region_name, str)
            ):
                aws_region_name = standard_aws_region_name
        if aws_region_name is None:
            try:
                import boto3

                with tracer.trace("boto3.Session()"):
                    session = boto3.Session()
                configured_region = session.region_name
                if configured_region:
                    aws_region_name = configured_region
                else:
                    aws_region_name = "us-west-2"
            except Exception:
                aws_region_name = "us-west-2"

        return aws_region_name

    def get_aws_region_name_for_non_llm_api_calls(
        self,
        aws_region_name: Optional[str] = None,
    ):
        """
        Get the AWS region name for non-llm api calls.

        LLM API calls check the model arn and end up using that as the region name.

        For non-llm api calls eg. Guardrails, Vector Stores we just need to check the dynamic param or env vars.
        """
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
        return aws_region_name

    @tracer.wrap()
    def _auth_with_web_identity_token(
        self,
        aws_web_identity_token: str,
        aws_role_name: str,
        aws_session_name: str,
        aws_region_name: Optional[str],
        aws_sts_endpoint: Optional[str],
    ) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS Web Identity Token
        """
        import boto3

        verbose_logger.debug(
            f"IN Web Identity Token: {aws_web_identity_token} | Role Name: {aws_role_name} | Session Name: {aws_session_name}"
        )

        if aws_sts_endpoint is None:
            sts_endpoint = f"https://sts.{aws_region_name}.amazonaws.com"
        else:
            sts_endpoint = aws_sts_endpoint

        oidc_token = get_secret(aws_web_identity_token)

        if oidc_token is None:
            raise AwsAuthError(
                message="OIDC token could not be retrieved from secret manager.",
                status_code=401,
            )

        with tracer.trace("boto3.client(sts)"):
            sts_client = boto3.client(
                "sts",
                region_name=aws_region_name,
                endpoint_url=sts_endpoint,
            )

        # https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts/client/assume_role_with_web_identity.html
        sts_response = sts_client.assume_role_with_web_identity(
            RoleArn=aws_role_name,
            RoleSessionName=aws_session_name,
            WebIdentityToken=oidc_token,
            DurationSeconds=3600,
            Policy='{"Version":"2012-10-17","Statement":[{"Sid":"BedrockLiteLLM","Effect":"Allow","Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],"Resource":"*","Condition":{"Bool":{"aws:SecureTransport":"true"},"StringLike":{"aws:UserAgent":"litellm/*"}}}]}',
        )

        iam_creds_dict = {
            "aws_access_key_id": sts_response["Credentials"]["AccessKeyId"],
            "aws_secret_access_key": sts_response["Credentials"]["SecretAccessKey"],
            "aws_session_token": sts_response["Credentials"]["SessionToken"],
            "region_name": aws_region_name,
        }

        if sts_response["PackedPolicySize"] > BEDROCK_MAX_POLICY_SIZE:
            verbose_logger.warning(
                f"The policy size is greater than 75% of the allowed size, PackedPolicySize: {sts_response['PackedPolicySize']}"
            )

        with tracer.trace("boto3.Session(**iam_creds_dict)"):
            session = boto3.Session(**iam_creds_dict)

        iam_creds = session.get_credentials()
        return iam_creds, self._get_default_ttl_for_boto3_credentials()

    @tracer.wrap()
    def _auth_with_aws_role(
        self,
        aws_access_key_id: Optional[str],
        aws_secret_access_key: Optional[str],
        aws_role_name: str,
        aws_session_name: str,
    ) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS Role
        """
        import boto3
        from botocore.credentials import Credentials

        with tracer.trace("boto3.client(sts)"):
            sts_client = boto3.client(
                "sts",
                aws_access_key_id=aws_access_key_id,  # [OPTIONAL]
                aws_secret_access_key=aws_secret_access_key,  # [OPTIONAL]
            )

        sts_response = sts_client.assume_role(
            RoleArn=aws_role_name, RoleSessionName=aws_session_name
        )

        # Extract the credentials from the response and convert to Session Credentials
        sts_credentials = sts_response["Credentials"]
        credentials = Credentials(
            access_key=sts_credentials["AccessKeyId"],
            secret_key=sts_credentials["SecretAccessKey"],
            token=sts_credentials["SessionToken"],
        )

        sts_expiry = sts_credentials["Expiration"]
        # Convert to timezone-aware datetime for comparison
        current_time = datetime.now(sts_expiry.tzinfo)
        sts_ttl = (sts_expiry - current_time).total_seconds() - 60
        return credentials, sts_ttl

    @tracer.wrap()
    def _auth_with_aws_profile(
        self, aws_profile_name: str
    ) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS profile
        """
        import boto3

        # uses auth values from AWS profile usually stored in ~/.aws/credentials
        with tracer.trace("boto3.Session(profile_name=aws_profile_name)"):
            client = boto3.Session(profile_name=aws_profile_name)
            return client.get_credentials(), None

    @tracer.wrap()
    def _auth_with_aws_session_token(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_session_token: str,
    ) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS Session Token
        """
        ### CHECK FOR AWS SESSION TOKEN ###
        from botocore.credentials import Credentials

        credentials = Credentials(
            access_key=aws_access_key_id,
            secret_key=aws_secret_access_key,
            token=aws_session_token,
        )

        return credentials, None

    @tracer.wrap()
    def _auth_with_access_key_and_secret_key(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region_name: Optional[str],
    ) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS Access Key and Secret Key
        """
        import boto3

        # Check if credentials are already in cache. These credentials have no expiry time.
        with tracer.trace(
            "boto3.Session(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=aws_region_name)"
        ):
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region_name,
            )

        credentials = session.get_credentials()
        return credentials, self._get_default_ttl_for_boto3_credentials()

    @tracer.wrap()
    def _auth_with_env_vars(self) -> Tuple[Credentials, Optional[int]]:
        """
        Authenticate with AWS Environment Variables
        """
        import boto3

        with tracer.trace("boto3.Session()"):
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials, None

    @tracer.wrap()
    def _get_default_ttl_for_boto3_credentials(self) -> int:
        """
        Get the default TTL for boto3 credentials

        Returns `3600-60` which is 59 minutes
        """
        return 3600 - 60

    def get_runtime_endpoint(
        self,
        api_base: Optional[str],
        aws_bedrock_runtime_endpoint: Optional[str],
        aws_region_name: str,
        endpoint_type: Optional[Literal["runtime", "agent"]] = "runtime",
    ) -> Tuple[str, str]:
        env_aws_bedrock_runtime_endpoint = get_secret("AWS_BEDROCK_RUNTIME_ENDPOINT")
        if api_base is not None:
            endpoint_url = api_base
        elif aws_bedrock_runtime_endpoint is not None and isinstance(
            aws_bedrock_runtime_endpoint, str
        ):
            endpoint_url = aws_bedrock_runtime_endpoint
        elif env_aws_bedrock_runtime_endpoint and isinstance(
            env_aws_bedrock_runtime_endpoint, str
        ):
            endpoint_url = env_aws_bedrock_runtime_endpoint
        else:
            endpoint_url = self._select_default_endpoint_url(
                endpoint_type=endpoint_type,
                aws_region_name=aws_region_name,
            )

        # Determine proxy_endpoint_url
        if env_aws_bedrock_runtime_endpoint and isinstance(
            env_aws_bedrock_runtime_endpoint, str
        ):
            proxy_endpoint_url = env_aws_bedrock_runtime_endpoint
        elif aws_bedrock_runtime_endpoint is not None and isinstance(
            aws_bedrock_runtime_endpoint, str
        ):
            proxy_endpoint_url = aws_bedrock_runtime_endpoint
        else:
            proxy_endpoint_url = endpoint_url

        return endpoint_url, proxy_endpoint_url

    def _select_default_endpoint_url(
        self, endpoint_type: Optional[Literal["runtime", "agent"]], aws_region_name: str
    ) -> str:
        """
        Select the default endpoint url based on the endpoint type

        Default endpoint url is https://bedrock-runtime.{aws_region_name}.amazonaws.com
        """
        if endpoint_type == "agent":
            return f"https://bedrock-agent-runtime.{aws_region_name}.amazonaws.com"
        else:
            return f"https://bedrock-runtime.{aws_region_name}.amazonaws.com"

    def _get_boto_credentials_from_optional_params(
        self, optional_params: dict, model: Optional[str] = None
    ) -> Boto3CredentialsInfo:
        """
        Get boto3 credentials from optional params

        Args:
            optional_params (dict): Optional parameters for the model call

        Returns:
            Credentials: Boto3 credentials object
        """
        try:
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_region_name = self._get_aws_region_name(optional_params, model)
        optional_params.pop("aws_region_name", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)
        aws_bedrock_runtime_endpoint = optional_params.pop(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com

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

        return Boto3CredentialsInfo(
            credentials=credentials,
            aws_region_name=aws_region_name,
            aws_bedrock_runtime_endpoint=aws_bedrock_runtime_endpoint,
        )

    @tracer.wrap()
    def get_request_headers(
        self,
        credentials: Credentials,
        aws_region_name: str,
        extra_headers: Optional[dict],
        endpoint_url: str,
        data: str,
        headers: dict,
    ) -> AWSPreparedRequest:
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)

        request = AWSRequest(
            method="POST", url=endpoint_url, data=data, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]
        prepped = request.prepare()

        return prepped

    def _sign_request(
        self,
        service_name: Literal["bedrock", "sagemaker"],
        headers: dict,
        optional_params: dict,
        request_data: dict,
        api_base: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        fake_stream: Optional[bool] = None,
    ) -> Tuple[dict, Optional[bytes]]:
        """
        Sign a request for Bedrock or Sagemaker

        Returns:
            Tuple[dict, Optional[str]]: A tuple containing the headers and the json str body of the request
        """
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_session_token, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.get("aws_secret_access_key", None)
        aws_access_key_id = optional_params.get("aws_access_key_id", None)
        aws_session_token = optional_params.get("aws_session_token", None)
        aws_role_name = optional_params.get("aws_role_name", None)
        aws_session_name = optional_params.get("aws_session_name", None)
        aws_profile_name = optional_params.get("aws_profile_name", None)
        aws_web_identity_token = optional_params.get("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.get("aws_sts_endpoint", None)
        aws_region_name = self._get_aws_region_name(
            optional_params=optional_params, model=model
        )

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

        sigv4 = SigV4Auth(credentials, service_name, aws_region_name)
        if headers is not None:
            headers = {"Content-Type": "application/json", **headers}
        else:
            headers = {"Content-Type": "application/json"}

        request = AWSRequest(
            method="POST",
            url=api_base,
            data=json.dumps(request_data),
            headers=headers,
        )
        sigv4.add_auth(request)

        request_headers_dict = dict(request.headers)
        if (
            headers is not None and "Authorization" in headers
        ):  # prevent sigv4 from overwriting the auth header
            request_headers_dict["Authorization"] = headers["Authorization"]
        return request_headers_dict, request.body

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_call.py ===
# Copyright 2019 gRPC authors.
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
"""Invocation-side implementation of gRPC Asyncio Python."""

import asyncio
import enum
from functools import partial
import inspect
import logging
import traceback
from typing import (
    Any,
    AsyncIterator,
    Generator,
    Generic,
    Optional,
    Tuple,
    Union,
)

import grpc
from grpc import _common
from grpc._cython import cygrpc

from . import _base_call
from ._metadata import Metadata
from ._typing import DeserializingFunction
from ._typing import DoneCallbackType
from ._typing import EOFType
from ._typing import MetadatumType
from ._typing import RequestIterableType
from ._typing import RequestType
from ._typing import ResponseType
from ._typing import SerializingFunction

__all__ = "AioRpcError", "Call", "UnaryUnaryCall", "UnaryStreamCall"

_LOCAL_CANCELLATION_DETAILS = "Locally cancelled by application!"
_GC_CANCELLATION_DETAILS = "Cancelled upon garbage collection!"
_RPC_ALREADY_FINISHED_DETAILS = "RPC already finished."
_RPC_HALF_CLOSED_DETAILS = 'RPC is half closed after calling "done_writing".'
_API_STYLE_ERROR = (
    "The iterator and read/write APIs may not be mixed on a single RPC."
)

_OK_CALL_REPRESENTATION = (
    '<{} of RPC that terminated with:\n\tstatus = {}\n\tdetails = "{}"\n>'
)

_NON_OK_CALL_REPRESENTATION = (
    "<{} of RPC that terminated with:\n"
    "\tstatus = {}\n"
    '\tdetails = "{}"\n'
    '\tdebug_error_string = "{}"\n'
    ">"
)

_LOGGER = logging.getLogger(__name__)


class AioRpcError(grpc.RpcError):
    """An implementation of RpcError to be used by the asynchronous API.

    Raised RpcError is a snapshot of the final status of the RPC, values are
    determined. Hence, its methods no longer needs to be coroutines.
    """

    _code: grpc.StatusCode
    _details: Optional[str]
    _initial_metadata: Optional[Metadata]
    _trailing_metadata: Optional[Metadata]
    _debug_error_string: Optional[str]

    def __init__(
        self,
        code: grpc.StatusCode,
        initial_metadata: Metadata,
        trailing_metadata: Metadata,
        details: Optional[str] = None,
        debug_error_string: Optional[str] = None,
    ) -> None:
        """Constructor.

        Args:
          code: The status code with which the RPC has been finalized.
          details: Optional details explaining the reason of the error.
          initial_metadata: Optional initial metadata that could be sent by the
            Server.
          trailing_metadata: Optional metadata that could be sent by the Server.
        """

        super().__init__()
        self._code = code
        self._details = details
        self._initial_metadata = initial_metadata
        self._trailing_metadata = trailing_metadata
        self._debug_error_string = debug_error_string

    def code(self) -> grpc.StatusCode:
        """Accesses the status code sent by the server.

        Returns:
          The `grpc.StatusCode` status code.
        """
        return self._code

    def details(self) -> Optional[str]:
        """Accesses the details sent by the server.

        Returns:
          The description of the error.
        """
        return self._details

    def initial_metadata(self) -> Metadata:
        """Accesses the initial metadata sent by the server.

        Returns:
          The initial metadata received.
        """
        return self._initial_metadata

    def trailing_metadata(self) -> Metadata:
        """Accesses the trailing metadata sent by the server.

        Returns:
          The trailing metadata received.
        """
        return self._trailing_metadata

    def debug_error_string(self) -> str:
        """Accesses the debug error string sent by the server.

        Returns:
          The debug error string received.
        """
        return self._debug_error_string

    def _repr(self) -> str:
        """Assembles the error string for the RPC error."""
        return _NON_OK_CALL_REPRESENTATION.format(
            self.__class__.__name__,
            self._code,
            self._details,
            self._debug_error_string,
        )

    def __repr__(self) -> str:
        return self._repr()

    def __str__(self) -> str:
        return self._repr()

    def __reduce__(self):
        return (
            type(self),
            (
                self._code,
                self._initial_metadata,
                self._trailing_metadata,
                self._details,
                self._debug_error_string,
            ),
        )


def _create_rpc_error(
    initial_metadata: Metadata, status: cygrpc.AioRpcStatus
) -> AioRpcError:
    return AioRpcError(
        _common.CYGRPC_STATUS_CODE_TO_STATUS_CODE[status.code()],
        Metadata.from_tuple(initial_metadata),
        Metadata.from_tuple(status.trailing_metadata()),
        details=status.details(),
        debug_error_string=status.debug_error_string(),
    )


class Call:
    """Base implementation of client RPC Call object.

    Implements logic around final status, metadata and cancellation.
    """

    _loop: asyncio.AbstractEventLoop
    _code: grpc.StatusCode
    _cython_call: cygrpc._AioCall
    _metadata: Tuple[MetadatumType, ...]
    _request_serializer: SerializingFunction
    _response_deserializer: DeserializingFunction

    def __init__(
        self,
        cython_call: cygrpc._AioCall,
        metadata: Metadata,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._cython_call = cython_call
        self._metadata = tuple(metadata)
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __del__(self) -> None:
        # The '_cython_call' object might be destructed before Call object
        if hasattr(self, "_cython_call"):
            if not self._cython_call.done():
                self._cancel(_GC_CANCELLATION_DETAILS)

    def cancelled(self) -> bool:
        return self._cython_call.cancelled()

    def _cancel(self, details: str) -> bool:
        """Forwards the application cancellation reasoning."""
        if not self._cython_call.done():
            self._cython_call.cancel(details)
            return True
        else:
            return False

    def cancel(self) -> bool:
        return self._cancel(_LOCAL_CANCELLATION_DETAILS)

    def done(self) -> bool:
        return self._cython_call.done()

    def add_done_callback(self, callback: DoneCallbackType) -> None:
        cb = partial(callback, self)
        self._cython_call.add_done_callback(cb)

    def time_remaining(self) -> Optional[float]:
        return self._cython_call.time_remaining()

    async def initial_metadata(self) -> Metadata:
        raw_metadata_tuple = await self._cython_call.initial_metadata()
        return Metadata.from_tuple(raw_metadata_tuple)

    async def trailing_metadata(self) -> Metadata:
        raw_metadata_tuple = (
            await self._cython_call.status()
        ).trailing_metadata()
        return Metadata.from_tuple(raw_metadata_tuple)

    async def code(self) -> grpc.StatusCode:
        cygrpc_code = (await self._cython_call.status()).code()
        return _common.CYGRPC_STATUS_CODE_TO_STATUS_CODE[cygrpc_code]

    async def details(self) -> str:
        return (await self._cython_call.status()).details()

    async def debug_error_string(self) -> str:
        return (await self._cython_call.status()).debug_error_string()

    async def _raise_for_status(self) -> None:
        if self._cython_call.is_locally_cancelled():
            raise asyncio.CancelledError()
        code = await self.code()
        if code != grpc.StatusCode.OK:
            raise _create_rpc_error(
                await self.initial_metadata(), await self._cython_call.status()
            )

    def _repr(self) -> str:
        return repr(self._cython_call)

    def __repr__(self) -> str:
        return self._repr()

    def __str__(self) -> str:
        return self._repr()


class _APIStyle(enum.IntEnum):
    UNKNOWN = 0
    ASYNC_GENERATOR = 1
    READER_WRITER = 2


class _UnaryResponseMixin(Call, Generic[ResponseType]):
    _call_response: asyncio.Task

    def _init_unary_response_mixin(self, response_task: asyncio.Task):
        self._call_response = response_task

    def cancel(self) -> bool:
        if super().cancel():
            self._call_response.cancel()
            return True
        else:
            return False

    def __await__(self) -> Generator[Any, None, ResponseType]:
        """Wait till the ongoing RPC request finishes."""
        try:
            response = yield from self._call_response
        except asyncio.CancelledError:
            # Even if we caught all other CancelledError, there is still
            # this corner case. If the application cancels immediately after
            # the Call object is created, we will observe this
            # `CancelledError`.
            if not self.cancelled():
                self.cancel()
            raise

        # NOTE(lidiz) If we raise RpcError in the task, and users doesn't
        # 'await' on it. AsyncIO will log 'Task exception was never retrieved'.
        # Instead, if we move the exception raising here, the spam stops.
        # Unfortunately, there can only be one 'yield from' in '__await__'. So,
        # we need to access the private instance variable.
        if response is cygrpc.EOF:
            if self._cython_call.is_locally_cancelled():
                raise asyncio.CancelledError()
            else:
                raise _create_rpc_error(
                    self._cython_call._initial_metadata,
                    self._cython_call._status,
                )
        else:
            return response


class _StreamResponseMixin(Call):
    _message_aiter: AsyncIterator[ResponseType]
    _preparation: asyncio.Task
    _response_style: _APIStyle

    def _init_stream_response_mixin(self, preparation: asyncio.Task):
        self._message_aiter = None
        self._preparation = preparation
        self._response_style = _APIStyle.UNKNOWN

    def _update_response_style(self, style: _APIStyle):
        if self._response_style is _APIStyle.UNKNOWN:
            self._response_style = style
        elif self._response_style is not style:
            raise cygrpc.UsageError(_API_STYLE_ERROR)

    def cancel(self) -> bool:
        if super().cancel():
            self._preparation.cancel()
            return True
        else:
            return False

    async def _fetch_stream_responses(self) -> ResponseType:
        message = await self._read()
        while message is not cygrpc.EOF:
            yield message
            message = await self._read()

        # If the read operation failed, Core should explain why.
        await self._raise_for_status()

    def __aiter__(self) -> AsyncIterator[ResponseType]:
        self._update_response_style(_APIStyle.ASYNC_GENERATOR)
        if self._message_aiter is None:
            self._message_aiter = self._fetch_stream_responses()
        return self._message_aiter

    async def _read(self) -> ResponseType:
        # Wait for the request being sent
        await self._preparation

        # Reads response message from Core
        try:
            raw_response = await self._cython_call.receive_serialized_message()
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()
            raise

        if raw_response is cygrpc.EOF:
            return cygrpc.EOF
        else:
            return _common.deserialize(
                raw_response, self._response_deserializer
            )

    async def read(self) -> Union[EOFType, ResponseType]:
        if self.done():
            await self._raise_for_status()
            return cygrpc.EOF
        self._update_response_style(_APIStyle.READER_WRITER)

        response_message = await self._read()

        if response_message is cygrpc.EOF:
            # If the read operation failed, Core should explain why.
            await self._raise_for_status()
        return response_message


class _StreamRequestMixin(Call):
    _metadata_sent: asyncio.Event
    _done_writing_flag: bool
    _async_request_poller: Optional[asyncio.Task]
    _request_style: _APIStyle

    def _init_stream_request_mixin(
        self, request_iterator: Optional[RequestIterableType]
    ):
        self._metadata_sent = asyncio.Event()
        self._done_writing_flag = False

        # If user passes in an async iterator, create a consumer Task.
        if request_iterator is not None:
            self._async_request_poller = self._loop.create_task(
                self._consume_request_iterator(request_iterator)
            )
            self._request_style = _APIStyle.ASYNC_GENERATOR
        else:
            self._async_request_poller = None
            self._request_style = _APIStyle.READER_WRITER

    def _raise_for_different_style(self, style: _APIStyle):
        if self._request_style is not style:
            raise cygrpc.UsageError(_API_STYLE_ERROR)

    def cancel(self) -> bool:
        if super().cancel():
            if self._async_request_poller is not None:
                self._async_request_poller.cancel()
            return True
        else:
            return False

    def _metadata_sent_observer(self):
        self._metadata_sent.set()

    async def _consume_request_iterator(
        self, request_iterator: RequestIterableType
    ) -> None:
        try:
            if inspect.isasyncgen(request_iterator) or hasattr(
                request_iterator, "__aiter__"
            ):
                async for request in request_iterator:
                    try:
                        await self._write(request)
                    except AioRpcError as rpc_error:
                        _LOGGER.debug(
                            (
                                "Exception while consuming the"
                                " request_iterator: %s"
                            ),
                            rpc_error,
                        )
                        return
            else:
                for request in request_iterator:
                    try:
                        await self._write(request)
                    except AioRpcError as rpc_error:
                        _LOGGER.debug(
                            (
                                "Exception while consuming the"
                                " request_iterator: %s"
                            ),
                            rpc_error,
                        )
                        return

            await self._done_writing()
        except:  # pylint: disable=bare-except
            # Client iterators can raise exceptions, which we should handle by
            # cancelling the RPC and logging the client's error. No exceptions
            # should escape this function.
            _LOGGER.debug(
                "Client request_iterator raised exception:\n%s",
                traceback.format_exc(),
            )
            self.cancel()

    async def _write(self, request: RequestType) -> None:
        if self.done():
            raise asyncio.InvalidStateError(_RPC_ALREADY_FINISHED_DETAILS)
        if self._done_writing_flag:
            raise asyncio.InvalidStateError(_RPC_HALF_CLOSED_DETAILS)
        if not self._metadata_sent.is_set():
            await self._metadata_sent.wait()
            if self.done():
                await self._raise_for_status()

        serialized_request = _common.serialize(
            request, self._request_serializer
        )
        try:
            await self._cython_call.send_serialized_message(serialized_request)
        except cygrpc.InternalError as err:
            self._cython_call.set_internal_error(str(err))
            await self._raise_for_status()
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()
            raise

    async def _done_writing(self) -> None:
        if self.done():
            # If the RPC is finished, do nothing.
            return
        if not self._done_writing_flag:
            # If the done writing is not sent before, try to send it.
            self._done_writing_flag = True
            try:
                await self._cython_call.send_receive_close()
            except asyncio.CancelledError:
                if not self.cancelled():
                    self.cancel()
                raise

    async def write(self, request: RequestType) -> None:
        self._raise_for_different_style(_APIStyle.READER_WRITER)
        await self._write(request)

    async def done_writing(self) -> None:
        """Signal peer that client is done writing.

        This method is idempotent.
        """
        self._raise_for_different_style(_APIStyle.READER_WRITER)
        await self._done_writing()

    async def wait_for_connection(self) -> None:
        await self._metadata_sent.wait()
        if self.done():
            await self._raise_for_status()


class UnaryUnaryCall(_UnaryResponseMixin, Call, _base_call.UnaryUnaryCall):
    """Object for managing unary-unary RPC calls.

    Returned when an instance of `UnaryUnaryMultiCallable` object is called.
    """

    _request: RequestType
    _invocation_task: asyncio.Task

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: RequestType,
        deadline: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__(
            channel.call(method, deadline, credentials, wait_for_ready),
            metadata,
            request_serializer,
            response_deserializer,
            loop,
        )
        self._request = request
        self._context = cygrpc.build_census_context()
        self._invocation_task = loop.create_task(self._invoke())
        self._init_unary_response_mixin(self._invocation_task)

    async def _invoke(self) -> ResponseType:
        serialized_request = _common.serialize(
            self._request, self._request_serializer
        )

        # NOTE(lidiz) asyncio.CancelledError is not a good transport for status,
        # because the asyncio.Task class do not cache the exception object.
        # https://github.com/python/cpython/blob/edad4d89e357c92f70c0324b937845d652b20afd/Lib/asyncio/tasks.py#L785
        try:
            serialized_response = await self._cython_call.unary_unary(
                serialized_request, self._metadata, self._context
            )
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()

        if self._cython_call.is_ok():
            return _common.deserialize(
                serialized_response, self._response_deserializer
            )
        else:
            return cygrpc.EOF

    async def wait_for_connection(self) -> None:
        await self._invocation_task
        if self.done():
            await self._raise_for_status()


class UnaryStreamCall(_StreamResponseMixin, Call, _base_call.UnaryStreamCall):
    """Object for managing unary-stream RPC calls.

    Returned when an instance of `UnaryStreamMultiCallable` object is called.
    """

    _request: RequestType
    _send_unary_request_task: asyncio.Task

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: RequestType,
        deadline: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__(
            channel.call(method, deadline, credentials, wait_for_ready),
            metadata,
            request_serializer,
            response_deserializer,
            loop,
        )
        self._request = request
        self._context = cygrpc.build_census_context()
        self._send_unary_request_task = loop.create_task(
            self._send_unary_request()
        )
        self._init_stream_response_mixin(self._send_unary_request_task)

    async def _send_unary_request(self) -> ResponseType:
        serialized_request = _common.serialize(
            self._request, self._request_serializer
        )
        try:
            await self._cython_call.initiate_unary_stream(
                serialized_request, self._metadata, self._context
            )
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()
            raise

    async def wait_for_connection(self) -> None:
        await self._send_unary_request_task
        if self.done():
            await self._raise_for_status()


# pylint: disable=too-many-ancestors
class StreamUnaryCall(
    _StreamRequestMixin, _UnaryResponseMixin, Call, _base_call.StreamUnaryCall
):
    """Object for managing stream-unary RPC calls.

    Returned when an instance of `StreamUnaryMultiCallable` object is called.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request_iterator: Optional[RequestIterableType],
        deadline: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__(
            channel.call(method, deadline, credentials, wait_for_ready),
            metadata,
            request_serializer,
            response_deserializer,
            loop,
        )

        self._context = cygrpc.build_census_context()
        self._init_stream_request_mixin(request_iterator)
        self._init_unary_response_mixin(loop.create_task(self._conduct_rpc()))

    async def _conduct_rpc(self) -> ResponseType:
        try:
            serialized_response = await self._cython_call.stream_unary(
                self._metadata, self._metadata_sent_observer, self._context
            )
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()
            raise

        if self._cython_call.is_ok():
            return _common.deserialize(
                serialized_response, self._response_deserializer
            )
        else:
            return cygrpc.EOF


class StreamStreamCall(
    _StreamRequestMixin, _StreamResponseMixin, Call, _base_call.StreamStreamCall
):
    """Object for managing stream-stream RPC calls.

    Returned when an instance of `StreamStreamMultiCallable` object is called.
    """

    _initializer: asyncio.Task

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request_iterator: Optional[RequestIterableType],
        deadline: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__(
            channel.call(method, deadline, credentials, wait_for_ready),
            metadata,
            request_serializer,
            response_deserializer,
            loop,
        )
        self._context = cygrpc.build_census_context()
        self._initializer = self._loop.create_task(self._prepare_rpc())
        self._init_stream_request_mixin(request_iterator)
        self._init_stream_response_mixin(self._initializer)

    async def _prepare_rpc(self):
        """This method prepares the RPC for receiving/sending messages.

        All other operations around the stream should only happen after the
        completion of this method.
        """
        try:
            await self._cython_call.initiate_stream_stream(
                self._metadata, self._metadata_sent_observer, self._context
            )
        except asyncio.CancelledError:
            if not self.cancelled():
                self.cancel()
            # No need to raise RpcError here, because no one will `await` this task.

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\data.py ===
"""
    pygments.lexers.data
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for data file format.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import Lexer, ExtendedRegexLexer, LexerContext, \
    include, bygroups
from pygments.token import Comment, Error, Keyword, Literal, Name, Number, \
    Punctuation, String, Whitespace

__all__ = ['YamlLexer', 'JsonLexer', 'JsonBareObjectLexer', 'JsonLdLexer']


class YamlLexerContext(LexerContext):
    """Indentation context for the YAML lexer."""

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.indent_stack = []
        self.indent = -1
        self.next_indent = 0
        self.block_scalar_indent = None


class YamlLexer(ExtendedRegexLexer):
    """
    Lexer for YAML, a human-friendly data serialization
    language.
    """

    name = 'YAML'
    url = 'http://yaml.org/'
    aliases = ['yaml']
    filenames = ['*.yaml', '*.yml']
    mimetypes = ['text/x-yaml']
    version_added = '0.11'

    def something(token_class):
        """Do not produce empty tokens."""
        def callback(lexer, match, context):
            text = match.group()
            if not text:
                return
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def reset_indent(token_class):
        """Reset the indentation levels."""
        def callback(lexer, match, context):
            text = match.group()
            context.indent_stack = []
            context.indent = -1
            context.next_indent = 0
            context.block_scalar_indent = None
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def save_indent(token_class, start=False):
        """Save a possible indentation level."""
        def callback(lexer, match, context):
            text = match.group()
            extra = ''
            if start:
                context.next_indent = len(text)
                if context.next_indent < context.indent:
                    while context.next_indent < context.indent:
                        context.indent = context.indent_stack.pop()
                    if context.next_indent > context.indent:
                        extra = text[context.indent:]
                        text = text[:context.indent]
            else:
                context.next_indent += len(text)
            if text:
                yield match.start(), token_class, text
            if extra:
                yield match.start()+len(text), token_class.Error, extra
            context.pos = match.end()
        return callback

    def set_indent(token_class, implicit=False):
        """Set the previously saved indentation level."""
        def callback(lexer, match, context):
            text = match.group()
            if context.indent < context.next_indent:
                context.indent_stack.append(context.indent)
                context.indent = context.next_indent
            if not implicit:
                context.next_indent += len(text)
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def set_block_scalar_indent(token_class):
        """Set an explicit indentation level for a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            context.block_scalar_indent = None
            if not text:
                return
            increment = match.group(1)
            if increment:
                current_indent = max(context.indent, 0)
                increment = int(increment)
                context.block_scalar_indent = current_indent + increment
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback

    def parse_block_scalar_empty_line(indent_token_class, content_token_class):
        """Process an empty line in a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if (context.block_scalar_indent is None or
                    len(text) <= context.block_scalar_indent):
                if text:
                    yield match.start(), indent_token_class, text
            else:
                indentation = text[:context.block_scalar_indent]
                content = text[context.block_scalar_indent:]
                yield match.start(), indent_token_class, indentation
                yield (match.start()+context.block_scalar_indent,
                       content_token_class, content)
            context.pos = match.end()
        return callback

    def parse_block_scalar_indent(token_class):
        """Process indentation spaces in a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if context.block_scalar_indent is None:
                if len(text) <= max(context.indent, 0):
                    context.stack.pop()
                    context.stack.pop()
                    return
                context.block_scalar_indent = len(text)
            else:
                if len(text) < context.block_scalar_indent:
                    context.stack.pop()
                    context.stack.pop()
                    return
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback

    def parse_plain_scalar_indent(token_class):
        """Process indentation spaces in a plain scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if len(text) <= context.indent:
                context.stack.pop()
                context.stack.pop()
                return
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback

    tokens = {
        # the root rules
        'root': [
            # ignored whitespaces
            (r'[ ]+(?=#|$)', Whitespace),
            # line breaks
            (r'\n+', Whitespace),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # the '%YAML' directive
            (r'^%YAML(?=[ ]|$)', reset_indent(Name.Tag), 'yaml-directive'),
            # the %TAG directive
            (r'^%TAG(?=[ ]|$)', reset_indent(Name.Tag), 'tag-directive'),
            # document start and document end indicators
            (r'^(?:---|\.\.\.)(?=[ ]|$)', reset_indent(Name.Namespace),
             'block-line'),
            # indentation spaces
            (r'[ ]*(?!\s|$)', save_indent(Whitespace, start=True),
             ('block-line', 'indentation')),
        ],

        # trailing whitespaces after directives or a block scalar indicator
        'ignored-line': [
            # ignored whitespaces
            (r'[ ]+(?=#|$)', Whitespace),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # line break
            (r'\n', Whitespace, '#pop:2'),
        ],

        # the %YAML directive
        'yaml-directive': [
            # the version number
            (r'([ ]+)([0-9]+\.[0-9]+)',
             bygroups(Whitespace, Number), 'ignored-line'),
        ],

        # the %TAG directive
        'tag-directive': [
            # a tag handle and the corresponding prefix
            (r'([ ]+)(!|![\w-]*!)'
             r'([ ]+)(!|!?[\w;/?:@&=+$,.!~*\'()\[\]%-]+)',
             bygroups(Whitespace, Keyword.Type, Whitespace, Keyword.Type),
             'ignored-line'),
        ],

        # block scalar indicators and indentation spaces
        'indentation': [
            # trailing whitespaces are ignored
            (r'[ ]*$', something(Whitespace), '#pop:2'),
            # whitespaces preceding block collection indicators
            (r'[ ]+(?=[?:-](?:[ ]|$))', save_indent(Whitespace)),
            # block collection indicators
            (r'[?:-](?=[ ]|$)', set_indent(Punctuation.Indicator)),
            # the beginning a block line
            (r'[ ]*', save_indent(Whitespace), '#pop'),
        ],

        # an indented line in the block context
        'block-line': [
            # the line end
            (r'[ ]*(?=#|$)', something(Whitespace), '#pop'),
            # whitespaces separating tokens
            (r'[ ]+', Whitespace),
            # key with colon
            (r'''([^#,?\[\]{}"'\n]+)(:)(?=[ ]|$)''',
             bygroups(Name.Tag, set_indent(Punctuation, implicit=True))),
            # tags, anchors and aliases,
            include('descriptors'),
            # block collections and scalars
            include('block-nodes'),
            # flow collections and quoted scalars
            include('flow-nodes'),
            # a plain scalar
            (r'(?=[^\s?:,\[\]{}#&*!|>\'"%@`-]|[?:-]\S)',
             something(Name.Variable),
             'plain-scalar-in-block-context'),
        ],

        # tags, anchors, aliases
        'descriptors': [
            # a full-form tag
            (r'!<[\w#;/?:@&=+$,.!~*\'()\[\]%-]+>', Keyword.Type),
            # a tag in the form '!', '!suffix' or '!handle!suffix'
            (r'!(?:[\w-]+!)?'
             r'[\w#;/?:@&=+$,.!~*\'()\[\]%-]*', Keyword.Type),
            # an anchor
            (r'&[\w-]+', Name.Label),
            # an alias
            (r'\*[\w-]+', Name.Variable),
        ],

        # block collections and scalars
        'block-nodes': [
            # implicit key
            (r':(?=[ ]|$)', set_indent(Punctuation.Indicator, implicit=True)),
            # literal and folded scalars
            (r'[|>]', Punctuation.Indicator,
             ('block-scalar-content', 'block-scalar-header')),
        ],

        # flow collections and quoted scalars
        'flow-nodes': [
            # a flow sequence
            (r'\[', Punctuation.Indicator, 'flow-sequence'),
            # a flow mapping
            (r'\{', Punctuation.Indicator, 'flow-mapping'),
            # a single-quoted scalar
            (r'\'', String, 'single-quoted-scalar'),
            # a double-quoted scalar
            (r'\"', String, 'double-quoted-scalar'),
        ],

        # the content of a flow collection
        'flow-collection': [
            # whitespaces
            (r'[ ]+', Whitespace),
            # line breaks
            (r'\n+', Whitespace),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # simple indicators
            (r'[?:,]', Punctuation.Indicator),
            # tags, anchors and aliases
            include('descriptors'),
            # nested collections and quoted scalars
            include('flow-nodes'),
            # a plain scalar
            (r'(?=[^\s?:,\[\]{}#&*!|>\'"%@`])',
             something(Name.Variable),
             'plain-scalar-in-flow-context'),
        ],

        # a flow sequence indicated by '[' and ']'
        'flow-sequence': [
            # include flow collection rules
            include('flow-collection'),
            # the closing indicator
            (r'\]', Punctuation.Indicator, '#pop'),
        ],

        # a flow mapping indicated by '{' and '}'
        'flow-mapping': [
            # key with colon
            (r'''([^,:?\[\]{}"'\n]+)(:)(?=[ ]|$)''',
             bygroups(Name.Tag, Punctuation)),
            # include flow collection rules
            include('flow-collection'),
            # the closing indicator
            (r'\}', Punctuation.Indicator, '#pop'),
        ],

        # block scalar lines
        'block-scalar-content': [
            # line break
            (r'\n', Whitespace),
            # empty line
            (r'^[ ]+$',
             parse_block_scalar_empty_line(Whitespace, Name.Constant)),
            # indentation spaces (we may leave the state here)
            (r'^[ ]*', parse_block_scalar_indent(Whitespace)),
            # line content
            (r'[\S\t ]+', Name.Constant),
        ],

        # the content of a literal or folded scalar
        'block-scalar-header': [
            # indentation indicator followed by chomping flag
            (r'([1-9])?[+-]?(?=[ ]|$)',
             set_block_scalar_indent(Punctuation.Indicator),
             'ignored-line'),
            # chomping flag followed by indentation indicator
            (r'[+-]?([1-9])?(?=[ ]|$)',
             set_block_scalar_indent(Punctuation.Indicator),
             'ignored-line'),
        ],

        # ignored and regular whitespaces in quoted scalars
        'quoted-scalar-whitespaces': [
            # leading and trailing whitespaces are ignored
            (r'^[ ]+', Whitespace),
            (r'[ ]+$', Whitespace),
            # line breaks are ignored
            (r'\n+', Whitespace),
            # other whitespaces are a part of the value
            (r'[ ]+', Name.Variable),
        ],

        # single-quoted scalars
        'single-quoted-scalar': [
            # include whitespace and line break rules
            include('quoted-scalar-whitespaces'),
            # escaping of the quote character
            (r'\'\'', String.Escape),
            # regular non-whitespace characters
            (r'[^\s\']+', String),
            # the closing quote
            (r'\'', String, '#pop'),
        ],

        # double-quoted scalars
        'double-quoted-scalar': [
            # include whitespace and line break rules
            include('quoted-scalar-whitespaces'),
            # escaping of special characters
            (r'\\[0abt\tn\nvfre "\\N_LP]', String),
            # escape codes
            (r'\\(?:x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})',
             String.Escape),
            # regular non-whitespace characters
            (r'[^\s"\\]+', String),
            # the closing quote
            (r'"', String, '#pop'),
        ],

        # the beginning of a new line while scanning a plain scalar
        'plain-scalar-in-block-context-new-line': [
            # empty lines
            (r'^[ ]+$', Whitespace),
            # line breaks
            (r'\n+', Whitespace),
            # document start and document end indicators
            (r'^(?=---|\.\.\.)', something(Name.Namespace), '#pop:3'),
            # indentation spaces (we may leave the block line state here)
            (r'^[ ]*', parse_plain_scalar_indent(Whitespace), '#pop'),
        ],

        # a plain scalar in the block context
        'plain-scalar-in-block-context': [
            # the scalar ends with the ':' indicator
            (r'[ ]*(?=:[ ]|:$)', something(Whitespace), '#pop'),
            # the scalar ends with whitespaces followed by a comment
            (r'[ ]+(?=#)', Whitespace, '#pop'),
            # trailing whitespaces are ignored
            (r'[ ]+$', Whitespace),
            # line breaks are ignored
            (r'\n+', Whitespace, 'plain-scalar-in-block-context-new-line'),
            # other whitespaces are a part of the value
            (r'[ ]+', Literal.Scalar.Plain),
            # regular non-whitespace characters
            (r'(?::(?!\s)|[^\s:])+', Literal.Scalar.Plain),
        ],

        # a plain scalar is the flow context
        'plain-scalar-in-flow-context': [
            # the scalar ends with an indicator character
            (r'[ ]*(?=[,:?\[\]{}])', something(Whitespace), '#pop'),
            # the scalar ends with a comment
            (r'[ ]+(?=#)', Whitespace, '#pop'),
            # leading and trailing whitespaces are ignored
            (r'^[ ]+', Whitespace),
            (r'[ ]+$', Whitespace),
            # line breaks are ignored
            (r'\n+', Whitespace),
            # other whitespaces are a part of the value
            (r'[ ]+', Name.Variable),
            # regular non-whitespace characters
            (r'[^\s,:?\[\]{}]+', Name.Variable),
        ],

    }

    def get_tokens_unprocessed(self, text=None, context=None):
        if context is None:
            context = YamlLexerContext(text, 0)
        return super().get_tokens_unprocessed(text, context)


class JsonLexer(Lexer):
    """
    For JSON data structures.

    Javascript-style comments are supported (like ``/* */`` and ``//``),
    though comments are not part of the JSON specification.
    This allows users to highlight JSON as it is used in the wild.

    No validation is performed on the input JSON document.
    """

    name = 'JSON'
    url = 'https://www.json.org'
    aliases = ['json', 'json-object']
    filenames = ['*.json', '*.jsonl', '*.ndjson', 'Pipfile.lock']
    mimetypes = ['application/json', 'application/json-object', 'application/x-ndjson', 'application/jsonl', 'application/json-seq']
    version_added = '1.5'

    # No validation of integers, floats, or constants is done.
    # As long as the characters are members of the following
    # sets, the token will be considered valid. For example,
    #
    #     "--1--" is parsed as an integer
    #     "1...eee" is parsed as a float
    #     "trustful" is parsed as a constant
    #
    integers = set('-0123456789')
    floats = set('.eE+')
    constants = set('truefalsenull')  # true|false|null
    hexadecimals = set('0123456789abcdefABCDEF')
    punctuations = set('{}[],')
    whitespaces = {'\u0020', '\u000a', '\u000d', '\u0009'}

    def get_tokens_unprocessed(self, text):
        """Parse JSON data."""

        in_string = False
        in_escape = False
        in_unicode_escape = 0
        in_whitespace = False
        in_constant = False
        in_number = False
        in_float = False
        in_punctuation = False
        in_comment_single = False
        in_comment_multiline = False
        expecting_second_comment_opener = False  # // or /*
        expecting_second_comment_closer = False  # */

        start = 0

        # The queue is used to store data that may need to be tokenized
        # differently based on what follows. In particular, JSON object
        # keys are tokenized differently than string values, but cannot
        # be distinguished until punctuation is encountered outside the
        # string.
        #
        # A ":" character after the string indicates that the string is
        # an object key; any other character indicates the string is a
        # regular string value.
        #
        # The queue holds tuples that contain the following data:
        #
        #     (start_index, token_type, text)
        #
        # By default the token type of text in double quotes is
        # String.Double. The token type will be replaced if a colon
        # is encountered after the string closes.
        #
        queue = []

        for stop, character in enumerate(text):
            if in_string:
                if in_unicode_escape:
                    if character in self.hexadecimals:
                        in_unicode_escape -= 1
                        if not in_unicode_escape:
                            in_escape = False
                    else:
                        in_unicode_escape = 0
                        in_escape = False

                elif in_escape:
                    if character == 'u':
                        in_unicode_escape = 4
                    else:
                        in_escape = False

                elif character == '\\':
                    in_escape = True

                elif character == '"':
                    queue.append((start, String.Double, text[start:stop + 1]))
                    in_string = False
                    in_escape = False
                    in_unicode_escape = 0

                continue

            elif in_whitespace:
                if character in self.whitespaces:
                    continue

                if queue:
                    queue.append((start, Whitespace, text[start:stop]))
                else:
                    yield start, Whitespace, text[start:stop]
                in_whitespace = False
                # Fall through so the new character can be evaluated.

            elif in_constant:
                if character in self.constants:
                    continue

                yield start, Keyword.Constant, text[start:stop]
                in_constant = False
                # Fall through so the new character can be evaluated.

            elif in_number:
                if character in self.integers:
                    continue
                elif character in self.floats:
                    in_float = True
                    continue

                if in_float:
                    yield start, Number.Float, text[start:stop]
                else:
                    yield start, Number.Integer, text[start:stop]
                in_number = False
                in_float = False
                # Fall through so the new character can be evaluated.

            elif in_punctuation:
                if character in self.punctuations:
                    continue

                yield start, Punctuation, text[start:stop]
                in_punctuation = False
                # Fall through so the new character can be evaluated.

            elif in_comment_single:
                if character != '\n':
                    continue

                if queue:
                    queue.append((start, Comment.Single, text[start:stop]))
                else:
                    yield start, Comment.Single, text[start:stop]

                in_comment_single = False
                # Fall through so the new character can be evaluated.

            elif in_comment_multiline:
                if character == '*':
                    expecting_second_comment_closer = True
                elif expecting_second_comment_closer:
                    expecting_second_comment_closer = False
                    if character == '/':
                        if queue:
                            queue.append((start, Comment.Multiline, text[start:stop + 1]))
                        else:
                            yield start, Comment.Multiline, text[start:stop + 1]

                        in_comment_multiline = False

                continue

            elif expecting_second_comment_opener:
                expecting_second_comment_opener = False
                if character == '/':
                    in_comment_single = True
                    continue
                elif character == '*':
                    in_comment_multiline = True
                    continue

                # Exhaust the queue. Accept the existing token types.
                yield from queue
                queue.clear()

                yield start, Error, text[start:stop]
                # Fall through so the new character can be evaluated.

            start = stop

            if character == '"':
                in_string = True

            elif character in self.whitespaces:
                in_whitespace = True

            elif character in {'f', 'n', 't'}:  # The first letters of true|false|null
                # Exhaust the queue. Accept the existing token types.
                yield from queue
                queue.clear()

                in_constant = True

            elif character in self.integers:
                # Exhaust the queue. Accept the existing token types.
                yield from queue
                queue.clear()

                in_number = True

            elif character == ':':
                # Yield from the queue. Replace string token types.
                for _start, _token, _text in queue:
                    # There can be only three types of tokens before a ':':
                    # Whitespace, Comment, or a quoted string.
                    #
                    # If it's a quoted string we emit Name.Tag.
                    # Otherwise, we yield the original token.
                    #
                    # In all other cases this would be invalid JSON,
                    # but this is not a validating JSON lexer, so it's OK.
                    if _token is String.Double:
                        yield _start, Name.Tag, _text
                    else:
                        yield _start, _token, _text
                queue.clear()

                in_punctuation = True

            elif character in self.punctuations:
                # Exhaust the queue. Accept the existing token types.
                yield from queue
                queue.clear()

                in_punctuation = True

            elif character == '/':
                # This is the beginning of a comment.
                expecting_second_comment_opener = True

            else:
                # Exhaust the queue. Accept the existing token types.
                yield from queue
                queue.clear()

                yield start, Error, character

        # Yield any remaining text.
        yield from queue
        if in_string:
            yield start, Error, text[start:]
        elif in_float:
            yield start, Number.Float, text[start:]
        elif in_number:
            yield start, Number.Integer, text[start:]
        elif in_constant:
            yield start, Keyword.Constant, text[start:]
        elif in_whitespace:
            yield start, Whitespace, text[start:]
        elif in_punctuation:
            yield start, Punctuation, text[start:]
        elif in_comment_single:
            yield start, Comment.Single, text[start:]
        elif in_comment_multiline:
            yield start, Error, text[start:]
        elif expecting_second_comment_opener:
            yield start, Error, text[start:]


class JsonBareObjectLexer(JsonLexer):
    """
    For JSON data structures (with missing object curly braces).

    .. deprecated:: 2.8.0

       Behaves the same as `JsonLexer` now.
    """

    name = 'JSONBareObject'
    aliases = []
    filenames = []
    mimetypes = []
    version_added = '2.2'


class JsonLdLexer(JsonLexer):
    """
    For JSON-LD linked data.
    """

    name = 'JSON-LD'
    url = 'https://json-ld.org/'
    aliases = ['jsonld', 'json-ld']
    filenames = ['*.jsonld']
    mimetypes = ['application/ld+json']
    version_added = '2.0'

    json_ld_keywords = {
        f'"@{keyword}"'
        for keyword in (
            'base',
            'container',
            'context',
            'direction',
            'graph',
            'id',
            'import',
            'included',
            'index',
            'json',
            'language',
            'list',
            'nest',
            'none',
            'prefix',
            'propagate',
            'protected',
            'reverse',
            'set',
            'type',
            'value',
            'version',
            'vocab',
        )
    }

    def get_tokens_unprocessed(self, text):
        for start, token, value in super().get_tokens_unprocessed(text):
            if token is Name.Tag and value in self.json_ld_keywords:
                yield start, Name.Decorator, value
            else:
                yield start, token, value

# === NexusCore/openenv\Lib\site-packages\litellm\fine_tuning\main.py ===
"""
Main File for Fine Tuning API implementation

https://platform.openai.com/docs/api-reference/fine-tuning

- fine_tuning.jobs.create()
- fine_tuning.jobs.list()
- client.fine_tuning.jobs.list_events()
"""

import asyncio
import contextvars
import os
from functools import partial
from typing import Any, Coroutine, Dict, Literal, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.llms.azure.fine_tuning.handler import AzureOpenAIFineTuningAPI
from litellm.llms.openai.fine_tuning.handler import OpenAIFineTuningAPI
from litellm.llms.vertex_ai.fine_tuning.handler import VertexFineTuningAPI
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import FineTuningJobCreate, Hyperparameters
from litellm.types.router import *
from litellm.types.utils import LiteLLMFineTuningJob
from litellm.utils import client, supports_httpx_timeout

####### ENVIRONMENT VARIABLES ###################
openai_fine_tuning_apis_instance = OpenAIFineTuningAPI()
azure_fine_tuning_apis_instance = AzureOpenAIFineTuningAPI()
vertex_fine_tuning_apis_instance = VertexFineTuningAPI()
#################################################


@client
async def acreate_fine_tuning_job(
    model: str,
    training_file: str,
    hyperparameters: Optional[dict] = {},
    suffix: Optional[str] = None,
    validation_file: Optional[str] = None,
    integrations: Optional[List[str]] = None,
    seed: Optional[int] = None,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> LiteLLMFineTuningJob:
    """
    Async: Creates and executes a batch from an uploaded file of request

    """
    verbose_logger.debug(
        "inside acreate_fine_tuning_job model=%s and kwargs=%s", model, kwargs
    )
    try:
        loop = asyncio.get_event_loop()
        kwargs["acreate_fine_tuning_job"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            create_fine_tuning_job,
            model,
            training_file,
            hyperparameters,
            suffix,
            validation_file,
            integrations,
            seed,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore
        return response
    except Exception as e:
        raise e


@client
def create_fine_tuning_job(
    model: str,
    training_file: str,
    hyperparameters: Optional[dict] = {},
    suffix: Optional[str] = None,
    validation_file: Optional[str] = None,
    integrations: Optional[List[str]] = None,
    seed: Optional[int] = None,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
    """
    Creates a fine-tuning job which begins the process of creating a new model from a given dataset.

    Response includes details of the enqueued job including job status and the name of the fine-tuned models once complete

    """
    try:
        _is_async = kwargs.pop("acreate_fine_tuning_job", False) is True
        optional_params = GenericLiteLLMParams(**kwargs)

        # handle hyperparameters
        hyperparameters = hyperparameters or {}  # original hyperparameters
        _oai_hyperparameters: Hyperparameters = Hyperparameters(
            **hyperparameters
        )  # Typed Hyperparameters for OpenAI Spec
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        # OpenAI
        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            create_fine_tuning_job_data = FineTuningJobCreate(
                model=model,
                training_file=training_file,
                hyperparameters=_oai_hyperparameters,
                suffix=suffix,
                validation_file=validation_file,
                integrations=integrations,
                seed=seed,
            )

            create_fine_tuning_job_data_dict = create_fine_tuning_job_data.model_dump(
                exclude_none=True
            )

            response = openai_fine_tuning_apis_instance.create_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=optional_params.api_version,
                organization=organization,
                create_fine_tuning_job_data=create_fine_tuning_job_data_dict,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                client=kwargs.get(
                    "client", None
                ),  # note, when we add this to `GenericLiteLLMParams` it impacts a lot of other tests + linting
            )
        # Azure OpenAI
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore

            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore
            create_fine_tuning_job_data = FineTuningJobCreate(
                model=model,
                training_file=training_file,
                hyperparameters=_oai_hyperparameters,
                suffix=suffix,
                validation_file=validation_file,
                integrations=integrations,
                seed=seed,
            )

            create_fine_tuning_job_data_dict = create_fine_tuning_job_data.model_dump(
                exclude_none=True
            )

            response = azure_fine_tuning_apis_instance.create_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                create_fine_tuning_job_data=create_fine_tuning_job_data_dict,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                organization=optional_params.organization,
            )
        elif custom_llm_provider == "vertex_ai":
            api_base = optional_params.api_base or ""
            vertex_ai_project = (
                optional_params.vertex_project
                or litellm.vertex_project
                or get_secret_str("VERTEXAI_PROJECT")
            )
            vertex_ai_location = (
                optional_params.vertex_location
                or litellm.vertex_location
                or get_secret_str("VERTEXAI_LOCATION")
            )
            vertex_credentials = optional_params.vertex_credentials or get_secret_str(
                "VERTEXAI_CREDENTIALS"
            )
            create_fine_tuning_job_data = FineTuningJobCreate(
                model=model,
                training_file=training_file,
                hyperparameters=_oai_hyperparameters,
                suffix=suffix,
                validation_file=validation_file,
                integrations=integrations,
                seed=seed,
            )
            response = vertex_fine_tuning_apis_instance.create_fine_tuning_job(
                _is_async=_is_async,
                create_fine_tuning_job_data=create_fine_tuning_job_data,
                vertex_credentials=vertex_credentials,
                vertex_project=vertex_ai_project,
                vertex_location=vertex_ai_location,
                timeout=timeout,
                api_base=api_base,
                kwargs=kwargs,
                original_hyperparameters=hyperparameters,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'create_batch'. Only 'openai' is supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        verbose_logger.error("got exception in create_fine_tuning_job=%s", str(e))
        raise e


@client
async def acancel_fine_tuning_job(
    fine_tuning_job_id: str,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> LiteLLMFineTuningJob:
    """
    Async: Immediately cancel a fine-tune job.
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["acancel_fine_tuning_job"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            cancel_fine_tuning_job,
            fine_tuning_job_id,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore
        return response
    except Exception as e:
        raise e


@client
def cancel_fine_tuning_job(
    fine_tuning_job_id: str,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
    """
    Immediately cancel a fine-tune job.

    Response includes details of the enqueued job including job status and the name of the fine-tuned models once complete

    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _is_async = kwargs.pop("acancel_fine_tuning_job", False) is True

        # OpenAI
        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_fine_tuning_apis_instance.cancel_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=optional_params.api_version,
                organization=organization,
                fine_tuning_job_id=fine_tuning_job_id,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                client=kwargs.get("client", None),
            )
        # Azure OpenAI
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")  # type: ignore

            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_fine_tuning_apis_instance.cancel_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                fine_tuning_job_id=fine_tuning_job_id,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                organization=optional_params.organization,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'create_batch'. Only 'openai' is supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e


async def alist_fine_tuning_jobs(
    after: Optional[str] = None,
    limit: Optional[int] = None,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """
    Async: List your organization's fine-tuning jobs
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["alist_fine_tuning_jobs"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            list_fine_tuning_jobs,
            after,
            limit,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore
        return response
    except Exception as e:
        raise e


def list_fine_tuning_jobs(
    after: Optional[str] = None,
    limit: Optional[int] = None,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """
    List your organization's fine-tuning jobs

    Params:

    - after: Optional[str] = None, Identifier for the last job from the previous pagination request.
    - limit: Optional[int] = None, Number of fine-tuning jobs to retrieve. Defaults to 20
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _is_async = kwargs.pop("alist_fine_tuning_jobs", False) is True

        # OpenAI
        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_fine_tuning_apis_instance.list_fine_tuning_jobs(
                api_base=api_base,
                api_key=api_key,
                api_version=optional_params.api_version,
                organization=organization,
                after=after,
                limit=limit,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                client=kwargs.get("client", None),
            )
        # Azure OpenAI
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore

            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret("AZURE_AD_TOKEN")  # type: ignore

            response = azure_fine_tuning_apis_instance.list_fine_tuning_jobs(
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                after=after,
                limit=limit,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                organization=optional_params.organization,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'create_batch'. Only 'openai' is supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e


@client
async def aretrieve_fine_tuning_job(
    fine_tuning_job_id: str,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> LiteLLMFineTuningJob:
    """
    Async: Get info about a fine-tuning job.
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["aretrieve_fine_tuning_job"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            retrieve_fine_tuning_job,
            fine_tuning_job_id,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore
        return response
    except Exception as e:
        raise e


@client
def retrieve_fine_tuning_job(
    fine_tuning_job_id: str,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
    """
    Get info about a fine-tuning job.
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _is_async = kwargs.pop("aretrieve_fine_tuning_job", False) is True

        # OpenAI
        if custom_llm_provider == "openai":
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None
            )
            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_fine_tuning_apis_instance.retrieve_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=optional_params.api_version,
                organization=organization,
                fine_tuning_job_id=fine_tuning_job_id,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                client=kwargs.get("client", None),
            )
        # Azure OpenAI
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore

            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_fine_tuning_apis_instance.retrieve_fine_tuning_job(
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                fine_tuning_job_id=fine_tuning_job_id,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                _is_async=_is_async,
                organization=optional_params.organization,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'retrieve_fine_tuning_job'. Only 'openai' and 'azure' are supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="retrieve_fine_tuning_job", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e

# === NexusCore/openenv\Lib\site-packages\openai\resources\files.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import time
import typing_extensions
from typing import Mapping, cast
from typing_extensions import Literal

import httpx

from .. import _legacy_response
from ..types import FilePurpose, file_list_params, file_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from .._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    StreamedBinaryAPIResponse,
    AsyncStreamedBinaryAPIResponse,
    to_streamed_response_wrapper,
    async_to_streamed_response_wrapper,
    to_custom_streamed_response_wrapper,
    async_to_custom_streamed_response_wrapper,
)
from ..pagination import SyncCursorPage, AsyncCursorPage
from .._base_client import AsyncPaginator, make_request_options
from ..types.file_object import FileObject
from ..types.file_deleted import FileDeleted
from ..types.file_purpose import FilePurpose

__all__ = ["Files", "AsyncFiles"]


class Files(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> FilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return FilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> FilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return FilesWithStreamingResponse(self)

    def create(
        self,
        *,
        file: FileTypes,
        purpose: FilePurpose,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileObject:
        """Upload a file that can be used across various endpoints.

        Individual files can be
        up to 512 MB, and the size of all files uploaded by one organization can be up
        to 100 GB.

        The Assistants API supports files up to 2 million tokens and of specific file
        types. See the
        [Assistants Tools guide](https://platform.openai.com/docs/assistants/tools) for
        details.

        The Fine-tuning API only supports `.jsonl` files. The input also has certain
        required formats for fine-tuning
        [chat](https://platform.openai.com/docs/api-reference/fine-tuning/chat-input) or
        [completions](https://platform.openai.com/docs/api-reference/fine-tuning/completions-input)
        models.

        The Batch API only supports `.jsonl` files up to 200 MB in size. The input also
        has a specific required
        [format](https://platform.openai.com/docs/api-reference/batch/request-input).

        Please [contact us](https://help.openai.com/) if you need to increase these
        storage limits.

        Args:
          file: The File object (not file name) to be uploaded.

          purpose: The intended purpose of the uploaded file. One of: - `assistants`: Used in the
              Assistants API - `batch`: Used in the Batch API - `fine-tune`: Used for
              fine-tuning - `vision`: Images used for vision fine-tuning - `user_data`:
              Flexible file type for any purpose - `evals`: Used for eval data sets

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "purpose": purpose,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/files",
            body=maybe_transform(body, file_create_params.FileCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileObject,
        )

    def retrieve(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileObject:
        """
        Returns information about a specific file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return self._get(
            f"/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileObject,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        purpose: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[FileObject]:
        """Returns a list of files.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              10,000, and the default is 10,000.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          purpose: Only return files with the given purpose.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/files",
            page=SyncCursorPage[FileObject],
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
                        "purpose": purpose,
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=FileObject,
        )

    def delete(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileDeleted:
        """
        Delete a file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return self._delete(
            f"/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileDeleted,
        )

    def content(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Returns the contents of the specified file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        return self._get(
            f"/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )

    @typing_extensions.deprecated("The `.content()` method should be used instead")
    def retrieve_content(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str:
        """
        Returns the contents of the specified file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return self._get(
            f"/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=str,
        )

    def wait_for_processing(
        self,
        id: str,
        *,
        poll_interval: float = 5.0,
        max_wait_seconds: float = 30 * 60,
    ) -> FileObject:
        """Waits for the given file to be processed, default timeout is 30 mins."""
        TERMINAL_STATES = {"processed", "error", "deleted"}

        start = time.time()
        file = self.retrieve(id)
        while file.status not in TERMINAL_STATES:
            self._sleep(poll_interval)

            file = self.retrieve(id)
            if time.time() - start > max_wait_seconds:
                raise RuntimeError(
                    f"Giving up on waiting for file {id} to finish processing after {max_wait_seconds} seconds."
                )

        return file


class AsyncFiles(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncFilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncFilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncFilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncFilesWithStreamingResponse(self)

    async def create(
        self,
        *,
        file: FileTypes,
        purpose: FilePurpose,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileObject:
        """Upload a file that can be used across various endpoints.

        Individual files can be
        up to 512 MB, and the size of all files uploaded by one organization can be up
        to 100 GB.

        The Assistants API supports files up to 2 million tokens and of specific file
        types. See the
        [Assistants Tools guide](https://platform.openai.com/docs/assistants/tools) for
        details.

        The Fine-tuning API only supports `.jsonl` files. The input also has certain
        required formats for fine-tuning
        [chat](https://platform.openai.com/docs/api-reference/fine-tuning/chat-input) or
        [completions](https://platform.openai.com/docs/api-reference/fine-tuning/completions-input)
        models.

        The Batch API only supports `.jsonl` files up to 200 MB in size. The input also
        has a specific required
        [format](https://platform.openai.com/docs/api-reference/batch/request-input).

        Please [contact us](https://help.openai.com/) if you need to increase these
        storage limits.

        Args:
          file: The File object (not file name) to be uploaded.

          purpose: The intended purpose of the uploaded file. One of: - `assistants`: Used in the
              Assistants API - `batch`: Used in the Batch API - `fine-tune`: Used for
              fine-tuning - `vision`: Images used for vision fine-tuning - `user_data`:
              Flexible file type for any purpose - `evals`: Used for eval data sets

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "purpose": purpose,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/files",
            body=await async_maybe_transform(body, file_create_params.FileCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileObject,
        )

    async def retrieve(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileObject:
        """
        Returns information about a specific file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return await self._get(
            f"/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileObject,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        purpose: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FileObject, AsyncCursorPage[FileObject]]:
        """Returns a list of files.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              10,000, and the default is 10,000.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          purpose: Only return files with the given purpose.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/files",
            page=AsyncCursorPage[FileObject],
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
                        "purpose": purpose,
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=FileObject,
        )

    async def delete(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FileDeleted:
        """
        Delete a file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return await self._delete(
            f"/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FileDeleted,
        )

    async def content(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Returns the contents of the specified file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        return await self._get(
            f"/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )

    @typing_extensions.deprecated("The `.content()` method should be used instead")
    async def retrieve_content(
        self,
        file_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str:
        """
        Returns the contents of the specified file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        return await self._get(
            f"/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=str,
        )

    async def wait_for_processing(
        self,
        id: str,
        *,
        poll_interval: float = 5.0,
        max_wait_seconds: float = 30 * 60,
    ) -> FileObject:
        """Waits for the given file to be processed, default timeout is 30 mins."""
        TERMINAL_STATES = {"processed", "error", "deleted"}

        start = time.time()
        file = await self.retrieve(id)
        while file.status not in TERMINAL_STATES:
            await self._sleep(poll_interval)

            file = await self.retrieve(id)
            if time.time() - start > max_wait_seconds:
                raise RuntimeError(
                    f"Giving up on waiting for file {id} to finish processing after {max_wait_seconds} seconds."
                )

        return file


class FilesWithRawResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = _legacy_response.to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            files.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            files.delete,
        )
        self.content = _legacy_response.to_raw_response_wrapper(
            files.content,
        )
        self.retrieve_content = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                files.retrieve_content  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncFilesWithRawResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = _legacy_response.async_to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            files.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            files.delete,
        )
        self.content = _legacy_response.async_to_raw_response_wrapper(
            files.content,
        )
        self.retrieve_content = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                files.retrieve_content  # pyright: ignore[reportDeprecated],
            )
        )


class FilesWithStreamingResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            files.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            files.list,
        )
        self.delete = to_streamed_response_wrapper(
            files.delete,
        )
        self.content = to_custom_streamed_response_wrapper(
            files.content,
            StreamedBinaryAPIResponse,
        )
        self.retrieve_content = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                files.retrieve_content  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncFilesWithStreamingResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = async_to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            files.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            files.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            files.delete,
        )
        self.content = async_to_custom_streamed_response_wrapper(
            files.content,
            AsyncStreamedBinaryAPIResponse,
        )
        self.retrieve_content = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                files.retrieve_content  # pyright: ignore[reportDeprecated],
            )
        )

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5652.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Modified by Russ Housley to add support for opentypes.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Cryptographic Message Syntax (CMS)
#
# ASN.1 source from:
# http://www.ietf.org/rfc/rfc5652.txt
#
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc3281
from pyasn1_modules import rfc5280

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


cmsContentTypesMap = { }

cmsAttributesMap = { }

otherKeyAttributesMap = { }

otherCertFormatMap = { }

otherRevInfoFormatMap = { }

otherRecipientInfoMap = { }


class AttCertVersionV1(univ.Integer):
    pass


AttCertVersionV1.namedValues = namedval.NamedValues(
    ('v1', 0)
)


class AttributeCertificateInfoV1(univ.Sequence):
    pass


AttributeCertificateInfoV1.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', AttCertVersionV1().subtype(value="v1")),
    namedtype.NamedType(
        'subject', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('baseCertificateID', rfc3281.IssuerSerial().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
                namedtype.NamedType('subjectName', rfc5280.GeneralNames().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
            )
        )
    ),
    namedtype.NamedType('issuer', rfc5280.GeneralNames()),
    namedtype.NamedType('signature', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('serialNumber', rfc5280.CertificateSerialNumber()),
    namedtype.NamedType('attCertValidityPeriod', rfc3281.AttCertValidityPeriod()),
    namedtype.NamedType('attributes', univ.SequenceOf(componentType=rfc5280.Attribute())),
    namedtype.OptionalNamedType('issuerUniqueID', rfc5280.UniqueIdentifier()),
    namedtype.OptionalNamedType('extensions', rfc5280.Extensions())
)


class AttributeCertificateV1(univ.Sequence):
    pass


AttributeCertificateV1.componentType = namedtype.NamedTypes(
    namedtype.NamedType('acInfo', AttributeCertificateInfoV1()),
    namedtype.NamedType('signatureAlgorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class AttributeValue(univ.Any):
    pass


class Attribute(univ.Sequence):
    pass


Attribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', univ.ObjectIdentifier()),
    namedtype.NamedType('attrValues', univ.SetOf(componentType=AttributeValue()),
        openType=opentype.OpenType('attrType', cmsAttributesMap)
    )
)


class SignedAttributes(univ.SetOf):
    pass


SignedAttributes.componentType = Attribute()
SignedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class AttributeCertificateV2(rfc3281.AttributeCertificate):
    pass


class OtherKeyAttribute(univ.Sequence):
    pass


OtherKeyAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyAttrId', univ.ObjectIdentifier()),
    namedtype.OptionalNamedType('keyAttr', univ.Any(),
        openType=opentype.OpenType('keyAttrId', otherKeyAttributesMap)
    )
)


class UnauthAttributes(univ.SetOf):
    pass


UnauthAttributes.componentType = Attribute()
UnauthAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_encryptedData = _buildOid(1, 2, 840, 113549, 1, 7, 6)


class SignatureValue(univ.OctetString):
    pass


class IssuerAndSerialNumber(univ.Sequence):
    pass


IssuerAndSerialNumber.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuer', rfc5280.Name()),
    namedtype.NamedType('serialNumber', rfc5280.CertificateSerialNumber())
)


class SubjectKeyIdentifier(univ.OctetString):
    pass


class RecipientKeyIdentifier(univ.Sequence):
    pass


RecipientKeyIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier()),
    namedtype.OptionalNamedType('date', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('other', OtherKeyAttribute())
)


class KeyAgreeRecipientIdentifier(univ.Choice):
    pass


KeyAgreeRecipientIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('rKeyId', RecipientKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)


class EncryptedKey(univ.OctetString):
    pass


class RecipientEncryptedKey(univ.Sequence):
    pass


RecipientEncryptedKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rid', KeyAgreeRecipientIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class RecipientEncryptedKeys(univ.SequenceOf):
    pass


RecipientEncryptedKeys.componentType = RecipientEncryptedKey()


class MessageAuthenticationCode(univ.OctetString):
    pass


class CMSVersion(univ.Integer):
    pass


CMSVersion.namedValues = namedval.NamedValues(
    ('v0', 0),
    ('v1', 1),
    ('v2', 2),
    ('v3', 3),
    ('v4', 4),
    ('v5', 5)
)


class OtherCertificateFormat(univ.Sequence):
    pass


OtherCertificateFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherCertFormat', univ.ObjectIdentifier()),
    namedtype.NamedType('otherCert', univ.Any(),
        openType=opentype.OpenType('otherCertFormat', otherCertFormatMap)
    )
)


class ExtendedCertificateInfo(univ.Sequence):
    pass


ExtendedCertificateInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('certificate', rfc5280.Certificate()),
    namedtype.NamedType('attributes', UnauthAttributes())
)


class Signature(univ.BitString):
    pass


class SignatureAlgorithmIdentifier(rfc5280.AlgorithmIdentifier):
    pass


class ExtendedCertificate(univ.Sequence):
    pass


ExtendedCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('extendedCertificateInfo', ExtendedCertificateInfo()),
    namedtype.NamedType('signatureAlgorithm', SignatureAlgorithmIdentifier()),
    namedtype.NamedType('signature', Signature())
)


class CertificateChoices(univ.Choice):
    pass


CertificateChoices.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certificate', rfc5280.Certificate()),
    namedtype.NamedType('extendedCertificate', ExtendedCertificate().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('v1AttrCert', AttributeCertificateV1().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('v2AttrCert', AttributeCertificateV2().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('other', OtherCertificateFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)))
)


class CertificateSet(univ.SetOf):
    pass


CertificateSet.componentType = CertificateChoices()


class OtherRevocationInfoFormat(univ.Sequence):
    pass


OtherRevocationInfoFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherRevInfoFormat', univ.ObjectIdentifier()),
    namedtype.NamedType('otherRevInfo', univ.Any(),
        openType=opentype.OpenType('otherRevInfoFormat', otherRevInfoFormatMap)
    )
)


class RevocationInfoChoice(univ.Choice):
    pass


RevocationInfoChoice.componentType = namedtype.NamedTypes(
    namedtype.NamedType('crl', rfc5280.CertificateList()),
    namedtype.NamedType('other', OtherRevocationInfoFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class RevocationInfoChoices(univ.SetOf):
    pass


RevocationInfoChoices.componentType = RevocationInfoChoice()


class OriginatorInfo(univ.Sequence):
    pass


OriginatorInfo.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('certs', CertificateSet().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('crls', RevocationInfoChoices().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class ContentType(univ.ObjectIdentifier):
    pass


class EncryptedContent(univ.OctetString):
    pass


class ContentEncryptionAlgorithmIdentifier(rfc5280.AlgorithmIdentifier):
    pass


class EncryptedContentInfo(univ.Sequence):
    pass


EncryptedContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('contentEncryptionAlgorithm', ContentEncryptionAlgorithmIdentifier()),
    namedtype.OptionalNamedType('encryptedContent', EncryptedContent().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class UnprotectedAttributes(univ.SetOf):
    pass


UnprotectedAttributes.componentType = Attribute()
UnprotectedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class KeyEncryptionAlgorithmIdentifier(rfc5280.AlgorithmIdentifier):
    pass


class KEKIdentifier(univ.Sequence):
    pass


KEKIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyIdentifier', univ.OctetString()),
    namedtype.OptionalNamedType('date', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('other', OtherKeyAttribute())
)


class KEKRecipientInfo(univ.Sequence):
    pass


KEKRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('kekid', KEKIdentifier()),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class KeyDerivationAlgorithmIdentifier(rfc5280.AlgorithmIdentifier):
    pass


class PasswordRecipientInfo(univ.Sequence):
    pass


PasswordRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('keyDerivationAlgorithm', KeyDerivationAlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class RecipientIdentifier(univ.Choice):
    pass


RecipientIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class KeyTransRecipientInfo(univ.Sequence):
    pass


KeyTransRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('rid', RecipientIdentifier()),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class UserKeyingMaterial(univ.OctetString):
    pass


class OriginatorPublicKey(univ.Sequence):
    pass


OriginatorPublicKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('publicKey', univ.BitString())
)


class OriginatorIdentifierOrKey(univ.Choice):
    pass


OriginatorIdentifierOrKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('originatorKey', OriginatorPublicKey().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class KeyAgreeRecipientInfo(univ.Sequence):
    pass


KeyAgreeRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('originator', OriginatorIdentifierOrKey().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('ukm', UserKeyingMaterial().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('recipientEncryptedKeys', RecipientEncryptedKeys())
)


class OtherRecipientInfo(univ.Sequence):
    pass


OtherRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('oriType', univ.ObjectIdentifier()),
    namedtype.NamedType('oriValue', univ.Any(),
        openType=opentype.OpenType('oriType', otherRecipientInfoMap)
    )
)


class RecipientInfo(univ.Choice):
    pass


RecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('ktri', KeyTransRecipientInfo()),
    namedtype.NamedType('kari', KeyAgreeRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.NamedType('kekri', KEKRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.NamedType('pwri', PasswordRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
    namedtype.NamedType('ori', OtherRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4)))
)


class RecipientInfos(univ.SetOf):
    pass


RecipientInfos.componentType = RecipientInfo()
RecipientInfos.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class EnvelopedData(univ.Sequence):
    pass


EnvelopedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('originatorInfo', OriginatorInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('recipientInfos', RecipientInfos()),
    namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo()),
    namedtype.OptionalNamedType('unprotectedAttrs', UnprotectedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class DigestAlgorithmIdentifier(rfc5280.AlgorithmIdentifier):
    pass


id_ct_contentInfo = _buildOid(1, 2, 840, 113549, 1, 9, 16, 1, 6)

id_digestedData = _buildOid(1, 2, 840, 113549, 1, 7, 5)


class EncryptedData(univ.Sequence):
    pass


EncryptedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo()),
    namedtype.OptionalNamedType('unprotectedAttrs', UnprotectedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_messageDigest = _buildOid(1, 2, 840, 113549, 1, 9, 4)

id_signedData = _buildOid(1, 2, 840, 113549, 1, 7, 2)


class MessageAuthenticationCodeAlgorithm(rfc5280.AlgorithmIdentifier):
    pass


class UnsignedAttributes(univ.SetOf):
    pass


UnsignedAttributes.componentType = Attribute()
UnsignedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class SignerIdentifier(univ.Choice):
    pass


SignerIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class SignerInfo(univ.Sequence):
    pass


SignerInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('sid', SignerIdentifier()),
    namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
    namedtype.OptionalNamedType('signedAttrs', SignedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('signatureAlgorithm', SignatureAlgorithmIdentifier()),
    namedtype.NamedType('signature', SignatureValue()),
    namedtype.OptionalNamedType('unsignedAttrs', UnsignedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class SignerInfos(univ.SetOf):
    pass


SignerInfos.componentType = SignerInfo()


class Countersignature(SignerInfo):
    pass


class ContentInfo(univ.Sequence):
    pass


ContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('content', univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
        openType=opentype.OpenType('contentType', cmsContentTypesMap)
    )
)


class EncapsulatedContentInfo(univ.Sequence):
    pass


EncapsulatedContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('eContentType', ContentType()),
    namedtype.OptionalNamedType('eContent', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)

id_countersignature = _buildOid(1, 2, 840, 113549, 1, 9, 6)

id_data = _buildOid(1, 2, 840, 113549, 1, 7, 1)


class MessageDigest(univ.OctetString):
    pass


class AuthAttributes(univ.SetOf):
    pass


AuthAttributes.componentType = Attribute()
AuthAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class Time(univ.Choice):
    pass


Time.componentType = namedtype.NamedTypes(
    namedtype.NamedType('utcTime', useful.UTCTime()),
    namedtype.NamedType('generalTime', useful.GeneralizedTime())
)


class AuthenticatedData(univ.Sequence):
    pass


AuthenticatedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('originatorInfo', OriginatorInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('recipientInfos', RecipientInfos()),
    namedtype.NamedType('macAlgorithm', MessageAuthenticationCodeAlgorithm()),
    namedtype.OptionalNamedType('digestAlgorithm', DigestAlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.OptionalNamedType('authAttrs', AuthAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('mac', MessageAuthenticationCode()),
    namedtype.OptionalNamedType('unauthAttrs', UnauthAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

id_contentType = _buildOid(1, 2, 840, 113549, 1, 9, 3)


class ExtendedCertificateOrCertificate(univ.Choice):
    pass


ExtendedCertificateOrCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certificate', rfc5280.Certificate()),
    namedtype.NamedType('extendedCertificate', ExtendedCertificate().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)


class Digest(univ.OctetString):
    pass


class DigestedData(univ.Sequence):
    pass


DigestedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.NamedType('digest', Digest())
)

id_envelopedData = _buildOid(1, 2, 840, 113549, 1, 7, 3)


class DigestAlgorithmIdentifiers(univ.SetOf):
    pass


DigestAlgorithmIdentifiers.componentType = DigestAlgorithmIdentifier()


class SignedData(univ.Sequence):
    pass


SignedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('digestAlgorithms', DigestAlgorithmIdentifiers()),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.OptionalNamedType('certificates', CertificateSet().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('crls', RevocationInfoChoices().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('signerInfos', SignerInfos())
)

id_signingTime = _buildOid(1, 2, 840, 113549, 1, 9, 5)


class SigningTime(Time):
    pass


id_ct_authData = _buildOid(1, 2, 840, 113549, 1, 9, 16, 1, 2)


# CMS Content Type Map

_cmsContentTypesMapUpdate = {
    id_ct_contentInfo: ContentInfo(),
    id_data: univ.OctetString(),
    id_signedData: SignedData(),
    id_envelopedData: EnvelopedData(),
    id_digestedData: DigestedData(),
    id_encryptedData: EncryptedData(),
    id_ct_authData: AuthenticatedData(),
}

cmsContentTypesMap.update(_cmsContentTypesMapUpdate)


# CMS Attribute Map

_cmsAttributesMapUpdate = {
    id_contentType: ContentType(),
    id_messageDigest: MessageDigest(),
    id_signingTime: SigningTime(),
    id_countersignature: Countersignature(),
}

cmsAttributesMap.update(_cmsAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\IPython\core\magic.py ===
# encoding: utf-8
"""Magic functions for InteractiveShell.
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2001 Janko Hauser <jhauser@zscout.de> and
#  Copyright (C) 2001 Fernando Perez <fperez@colorado.edu>
#  Copyright (C) 2008 The IPython Development Team

#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import re
import sys
from getopt import getopt, GetoptError

from traitlets.config.configurable import Configurable
from . import oinspect
from .error import UsageError
from .inputtransformer2 import ESC_MAGIC, ESC_MAGIC2
from ..utils.ipstruct import Struct
from ..utils.process import arg_split
from ..utils.text import dedent
from traitlets import Bool, Dict, Instance, observe
from logging import error

import typing as t

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

# A dict we'll use for each class that has magics, used as temporary storage to
# pass information between the @line/cell_magic method decorators and the
# @magics_class class decorator, because the method decorators have no
# access to the class when they run.  See for more details:
# http://stackoverflow.com/questions/2366713/can-a-python-decorator-of-an-instance-method-access-the-class

magics: t.Dict = dict(line={}, cell={})

magic_kinds = ('line', 'cell')
magic_spec = ('line', 'cell', 'line_cell')
magic_escapes = dict(line=ESC_MAGIC, cell=ESC_MAGIC2)

#-----------------------------------------------------------------------------
# Utility classes and functions
#-----------------------------------------------------------------------------

class Bunch: pass


def on_off(tag):
    """Return an ON/OFF string for a 1/0 input. Simple utility function."""
    return ['OFF','ON'][tag]


def compress_dhist(dh):
    """Compress a directory history into a new one with at most 20 entries.

    Return a new list made from the first and last 10 elements of dhist after
    removal of duplicates.
    """
    head, tail = dh[:-10], dh[-10:]

    newhead = []
    done = set()
    for h in head:
        if h in done:
            continue
        newhead.append(h)
        done.add(h)

    return newhead + tail


def needs_local_scope(func):
    """Decorator to mark magic functions which need to local scope to run."""
    func.needs_local_scope = True
    return func

#-----------------------------------------------------------------------------
# Class and method decorators for registering magics
#-----------------------------------------------------------------------------

def magics_class(cls):
    """Class decorator for all subclasses of the main Magics class.

    Any class that subclasses Magics *must* also apply this decorator, to
    ensure that all the methods that have been decorated as line/cell magics
    get correctly registered in the class instance.  This is necessary because
    when method decorators run, the class does not exist yet, so they
    temporarily store their information into a module global.  Application of
    this class decorator copies that global data to the class instance and
    clears the global.

    Obviously, this mechanism is not thread-safe, which means that the
    *creation* of subclasses of Magic should only be done in a single-thread
    context.  Instantiation of the classes has no restrictions.  Given that
    these classes are typically created at IPython startup time and before user
    application code becomes active, in practice this should not pose any
    problems.
    """
    cls.registered = True
    cls.magics = dict(line = magics['line'],
                      cell = magics['cell'])
    magics['line'] = {}
    magics['cell'] = {}
    return cls


def record_magic(dct, magic_kind, magic_name, func):
    """Utility function to store a function as a magic of a specific kind.

    Parameters
    ----------
    dct : dict
        A dictionary with 'line' and 'cell' subdicts.
    magic_kind : str
        Kind of magic to be stored.
    magic_name : str
        Key to store the magic as.
    func : function
        Callable object to store.
    """
    if magic_kind == 'line_cell':
        dct['line'][magic_name] = dct['cell'][magic_name] = func
    else:
        dct[magic_kind][magic_name] = func


def validate_type(magic_kind):
    """Ensure that the given magic_kind is valid.

    Check that the given magic_kind is one of the accepted spec types (stored
    in the global `magic_spec`), raise ValueError otherwise.
    """
    if magic_kind not in magic_spec:
        raise ValueError('magic_kind must be one of %s, %s given' %
                         magic_kinds, magic_kind)


# The docstrings for the decorator below will be fairly similar for the two
# types (method and function), so we generate them here once and reuse the
# templates below.
_docstring_template = \
"""Decorate the given {0} as {1} magic.

The decorator can be used with or without arguments, as follows.

i) without arguments: it will create a {1} magic named as the {0} being
decorated::

    @deco
    def foo(...)

will create a {1} magic named `foo`.

ii) with one string argument: which will be used as the actual name of the
resulting magic::

    @deco('bar')
    def foo(...)

will create a {1} magic named `bar`.

To register a class magic use ``Interactiveshell.register_magic(class or instance)``.
"""

# These two are decorator factories.  While they are conceptually very similar,
# there are enough differences in the details that it's simpler to have them
# written as completely standalone functions rather than trying to share code
# and make a single one with convoluted logic.

def _method_magic_marker(magic_kind):
    """Decorator factory for methods in Magics subclasses.
    """

    validate_type(magic_kind)

    # This is a closure to capture the magic_kind.  We could also use a class,
    # but it's overkill for just that one bit of state.
    def magic_deco(arg):
        if callable(arg):
            # "Naked" decorator call (just @foo, no args)
            func = arg
            name = func.__name__
            retval = arg
            record_magic(magics, magic_kind, name, name)
        elif isinstance(arg, str):
            # Decorator called with arguments (@foo('bar'))
            name = arg
            def mark(func, *a, **kw):
                record_magic(magics, magic_kind, name, func.__name__)
                return func
            retval = mark
        else:
            raise TypeError("Decorator can only be called with "
                            "string or function")
        return retval

    # Ensure the resulting decorator has a usable docstring
    magic_deco.__doc__ = _docstring_template.format('method', magic_kind)
    return magic_deco


def _function_magic_marker(magic_kind):
    """Decorator factory for standalone functions.
    """
    validate_type(magic_kind)
    
    # This is a closure to capture the magic_kind.  We could also use a class,
    # but it's overkill for just that one bit of state.
    def magic_deco(arg):
        # Find get_ipython() in the caller's namespace
        caller = sys._getframe(1)
        for ns in ['f_locals', 'f_globals', 'f_builtins']:
            get_ipython = getattr(caller, ns).get('get_ipython')
            if get_ipython is not None:
                break
        else:
            raise NameError('Decorator can only run in context where '
                            '`get_ipython` exists')

        ip = get_ipython()

        if callable(arg):
            # "Naked" decorator call (just @foo, no args)
            func = arg
            name = func.__name__
            ip.register_magic_function(func, magic_kind, name)
            retval = arg
        elif isinstance(arg, str):
            # Decorator called with arguments (@foo('bar'))
            name = arg
            def mark(func, *a, **kw):
                ip.register_magic_function(func, magic_kind, name)
                return func
            retval = mark
        else:
            raise TypeError("Decorator can only be called with "
                             "string or function")
        return retval

    # Ensure the resulting decorator has a usable docstring
    ds = _docstring_template.format('function', magic_kind)

    ds += dedent("""
    Note: this decorator can only be used in a context where IPython is already
    active, so that the `get_ipython()` call succeeds.  You can therefore use
    it in your startup files loaded after IPython initializes, but *not* in the
    IPython configuration file itself, which is executed before IPython is
    fully up and running.  Any file located in the `startup` subdirectory of
    your configuration profile will be OK in this sense.
    """)
    
    magic_deco.__doc__ = ds
    return magic_deco


MAGIC_NO_VAR_EXPAND_ATTR = "_ipython_magic_no_var_expand"
MAGIC_OUTPUT_CAN_BE_SILENCED = "_ipython_magic_output_can_be_silenced"


def no_var_expand(magic_func):
    """Mark a magic function as not needing variable expansion

    By default, IPython interprets `{a}` or `$a` in the line passed to magics
    as variables that should be interpolated from the interactive namespace
    before passing the line to the magic function.
    This is not always desirable, e.g. when the magic executes Python code
    (%timeit, %time, etc.).
    Decorate magics with `@no_var_expand` to opt-out of variable expansion.

    .. versionadded:: 7.3
    """
    setattr(magic_func, MAGIC_NO_VAR_EXPAND_ATTR, True)
    return magic_func


def output_can_be_silenced(magic_func):
    """Mark a magic function so its output may be silenced.

    The output is silenced if the Python code used as a parameter of
    the magic ends in a semicolon, not counting a Python comment that can
    follow it.
    """
    setattr(magic_func, MAGIC_OUTPUT_CAN_BE_SILENCED, True)
    return magic_func

# Create the actual decorators for public use

# These three are used to decorate methods in class definitions
line_magic = _method_magic_marker('line')
cell_magic = _method_magic_marker('cell')
line_cell_magic = _method_magic_marker('line_cell')

# These three decorate standalone functions and perform the decoration
# immediately.  They can only run where get_ipython() works
register_line_magic = _function_magic_marker('line')
register_cell_magic = _function_magic_marker('cell')
register_line_cell_magic = _function_magic_marker('line_cell')

#-----------------------------------------------------------------------------
# Core Magic classes
#-----------------------------------------------------------------------------

class MagicsManager(Configurable):
    """Object that handles all magic-related functionality for IPython.
    """
    # Non-configurable class attributes

    # A two-level dict, first keyed by magic type, then by magic function, and
    # holding the actual callable object as value.  This is the dict used for
    # magic function dispatch
    magics = Dict()
    lazy_magics = Dict(
        help="""
    Mapping from magic names to modules to load.

    This can be used in IPython/IPykernel configuration to declare lazy magics
    that will only be imported/registered on first use.

    For example::

        c.MagicsManager.lazy_magics = {
          "my_magic": "slow.to.import",
          "my_other_magic": "also.slow",
        }

    On first invocation of `%my_magic`, `%%my_magic`, `%%my_other_magic` or
    `%%my_other_magic`, the corresponding module will be loaded as an ipython
    extensions as if you had previously done `%load_ext ipython`.

    Magics names should be without percent(s) as magics can be both cell
    and line magics.

    Lazy loading happen relatively late in execution process, and
    complex extensions that manipulate Python/IPython internal state or global state
    might not support lazy loading.
    """
    ).tag(
        config=True,
    )

    # A registry of the original objects that we've been given holding magics.
    registry = Dict()

    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC', allow_none=True)

    auto_magic = Bool(True, help=
        "Automatically call line magics without requiring explicit % prefix"
    ).tag(config=True)
    @observe('auto_magic')
    def _auto_magic_changed(self, change):
        self.shell.automagic = change['new']
    
    _auto_status = [
        'Automagic is OFF, % prefix IS needed for line magics.',
        'Automagic is ON, % prefix IS NOT needed for line magics.']

    user_magics = Instance('IPython.core.magics.UserMagics', allow_none=True)

    def __init__(self, shell=None, config=None, user_magics=None, **traits):

        super(MagicsManager, self).__init__(shell=shell, config=config,
                                           user_magics=user_magics, **traits)
        self.magics = dict(line={}, cell={})
        # Let's add the user_magics to the registry for uniformity, so *all*
        # registered magic containers can be found there.
        self.registry[user_magics.__class__.__name__] = user_magics

    def auto_status(self):
        """Return descriptive string with automagic status."""
        return self._auto_status[self.auto_magic]
    
    def lsmagic(self):
        """Return a dict of currently available magic functions.

        The return dict has the keys 'line' and 'cell', corresponding to the
        two types of magics we support.  Each value is a list of names.
        """
        return self.magics

    def lsmagic_docs(self, brief=False, missing=''):
        """Return dict of documentation of magic functions.

        The return dict has the keys 'line' and 'cell', corresponding to the
        two types of magics we support. Each value is a dict keyed by magic
        name whose value is the function docstring. If a docstring is
        unavailable, the value of `missing` is used instead.

        If brief is True, only the first line of each docstring will be returned.
        """
        docs = {}
        for m_type in self.magics:
            m_docs = {}
            for m_name, m_func in self.magics[m_type].items():
                if m_func.__doc__:
                    if brief:
                        m_docs[m_name] = m_func.__doc__.split('\n', 1)[0]
                    else:
                        m_docs[m_name] = m_func.__doc__.rstrip()
                else:
                    m_docs[m_name] = missing
            docs[m_type] = m_docs
        return docs

    def register_lazy(self, name: str, fully_qualified_name: str):
        """
        Lazily register a magic via an extension.


        Parameters
        ----------
        name : str
            Name of the magic you wish to register.
        fully_qualified_name :
            Fully qualified name of the module/submodule that should be loaded
            as an extensions when the magic is first called.
            It is assumed that loading this extensions will register the given
            magic.
        """

        self.lazy_magics[name] = fully_qualified_name

    def register(self, *magic_objects):
        """Register one or more instances of Magics.

        Take one or more classes or instances of classes that subclass the main
        `core.Magic` class, and register them with IPython to use the magic
        functions they provide.  The registration process will then ensure that
        any methods that have decorated to provide line and/or cell magics will
        be recognized with the `%x`/`%%x` syntax as a line/cell magic
        respectively.

        If classes are given, they will be instantiated with the default
        constructor.  If your classes need a custom constructor, you should
        instanitate them first and pass the instance.

        The provided arguments can be an arbitrary mix of classes and instances.

        Parameters
        ----------
        *magic_objects : one or more classes or instances
        """
        # Start by validating them to ensure they have all had their magic
        # methods registered at the instance level
        for m in magic_objects:
            if not m.registered:
                raise ValueError("Class of magics %r was constructed without "
                                 "the @register_magics class decorator")
            if isinstance(m, type):
                # If we're given an uninstantiated class
                m = m(shell=self.shell)

            # Now that we have an instance, we can register it and update the
            # table of callables
            self.registry[m.__class__.__name__] = m
            for mtype in magic_kinds:
                self.magics[mtype].update(m.magics[mtype])

    def register_function(self, func, magic_kind='line', magic_name=None):
        """Expose a standalone function as magic function for IPython.

        This will create an IPython magic (line, cell or both) from a
        standalone function.  The functions should have the following
        signatures:

        * For line magics: `def f(line)`
        * For cell magics: `def f(line, cell)`
        * For a function that does both: `def f(line, cell=None)`

        In the latter case, the function will be called with `cell==None` when
        invoked as `%f`, and with cell as a string when invoked as `%%f`.

        Parameters
        ----------
        func : callable
            Function to be registered as a magic.
        magic_kind : str
            Kind of magic, one of 'line', 'cell' or 'line_cell'
        magic_name : optional str
            If given, the name the magic will have in the IPython namespace.  By
            default, the name of the function itself is used.
        """

        # Create the new method in the user_magics and register it in the
        # global table
        validate_type(magic_kind)
        magic_name = func.__name__ if magic_name is None else magic_name
        setattr(self.user_magics, magic_name, func)
        record_magic(self.magics, magic_kind, magic_name, func)

    def register_alias(self, alias_name, magic_name, magic_kind='line', magic_params=None):
        """Register an alias to a magic function.

        The alias is an instance of :class:`MagicAlias`, which holds the
        name and kind of the magic it should call. Binding is done at
        call time, so if the underlying magic function is changed the alias
        will call the new function.

        Parameters
        ----------
        alias_name : str
            The name of the magic to be registered.
        magic_name : str
            The name of an existing magic.
        magic_kind : str
            Kind of magic, one of 'line' or 'cell'
        """

        # `validate_type` is too permissive, as it allows 'line_cell'
        # which we do not handle.
        if magic_kind not in magic_kinds:
            raise ValueError('magic_kind must be one of %s, %s given' %
                             magic_kinds, magic_kind)

        alias = MagicAlias(self.shell, magic_name, magic_kind, magic_params)
        setattr(self.user_magics, alias_name, alias)
        record_magic(self.magics, magic_kind, alias_name, alias)

# Key base class that provides the central functionality for magics.


class Magics(Configurable):
    """Base class for implementing magic functions.

    Shell functions which can be reached as %function_name. All magic
    functions should accept a string, which they can parse for their own
    needs. This can make some functions easier to type, eg `%cd ../`
    vs. `%cd("../")`

    Classes providing magic functions need to subclass this class, and they
    MUST:

    - Use the method decorators `@line_magic` and `@cell_magic` to decorate
      individual methods as magic functions, AND

    - Use the class decorator `@magics_class` to ensure that the magic
      methods are properly registered at the instance level upon instance
      initialization.

    See :mod:`magic_functions` for examples of actual implementation classes.
    """
    # Dict holding all command-line options for each magic.
    options_table = None
    # Dict for the mapping of magic names to methods, set by class decorator
    magics = None
    # Flag to check that the class decorator was properly applied
    registered = False
    # Instance of IPython shell
    shell = None

    def __init__(self, shell=None, **kwargs):
        if not(self.__class__.registered):
            raise ValueError('Magics subclass without registration - '
                             'did you forget to apply @magics_class?')
        if shell is not None:
            if hasattr(shell, 'configurables'):
                shell.configurables.append(self)
            if hasattr(shell, 'config'):
                kwargs.setdefault('parent', shell)

        self.shell = shell
        self.options_table = {}
        # The method decorators are run when the instance doesn't exist yet, so
        # they can only record the names of the methods they are supposed to
        # grab.  Only now, that the instance exists, can we create the proper
        # mapping to bound methods.  So we read the info off the original names
        # table and replace each method name by the actual bound method.
        # But we mustn't clobber the *class* mapping, in case of multiple instances.
        class_magics = self.magics
        self.magics = {}
        for mtype in magic_kinds:
            tab = self.magics[mtype] = {}
            cls_tab = class_magics[mtype]
            for magic_name, meth_name in cls_tab.items():
                if isinstance(meth_name, str):
                    # it's a method name, grab it
                    tab[magic_name] = getattr(self, meth_name)
                else:
                    # it's the real thing
                    tab[magic_name] = meth_name
        # Configurable **needs** to be initiated at the end or the config
        # magics get screwed up.
        super(Magics, self).__init__(**kwargs)

    def arg_err(self,func):
        """Print docstring if incorrect arguments were passed"""
        print('Error in arguments:')
        print(oinspect.getdoc(func))

    def format_latex(self, strng):
        """Format a string for latex inclusion."""

        # Characters that need to be escaped for latex:
        escape_re = re.compile(r'(%|_|\$|#|&)',re.MULTILINE)
        # Magic command names as headers:
        cmd_name_re = re.compile(r'^(%s.*?):' % ESC_MAGIC,
                                 re.MULTILINE)
        # Magic commands
        cmd_re = re.compile(r'(?P<cmd>%s.+?\b)(?!\}\}:)' % ESC_MAGIC,
                            re.MULTILINE)
        # Paragraph continue
        par_re = re.compile(r'\\$',re.MULTILINE)

        # The "\n" symbol
        newline_re = re.compile(r'\\n')

        # Now build the string for output:
        #strng = cmd_name_re.sub(r'\n\\texttt{\\textsl{\\large \1}}:',strng)
        strng = cmd_name_re.sub(r'\n\\bigskip\n\\texttt{\\textbf{ \1}}:',
                                strng)
        strng = cmd_re.sub(r'\\texttt{\g<cmd>}',strng)
        strng = par_re.sub(r'\\\\',strng)
        strng = escape_re.sub(r'\\\1',strng)
        strng = newline_re.sub(r'\\textbackslash{}n',strng)
        return strng

    def parse_options(self, arg_str, opt_str, *long_opts, **kw):
        """Parse options passed to an argument string.

        The interface is similar to that of :func:`getopt.getopt`, but it
        returns a :class:`~IPython.utils.struct.Struct` with the options as keys
        and the stripped argument string still as a string.

        arg_str is quoted as a true sys.argv vector by using shlex.split.
        This allows us to easily expand variables, glob files, quote
        arguments, etc.

        Parameters
        ----------
        arg_str : str
            The arguments to parse.
        opt_str : str
            The options specification.
        mode : str, default 'string'
            If given as 'list', the argument string is returned as a list (split
            on whitespace) instead of a string.
        list_all : bool, default False
            Put all option values in lists. Normally only options
            appearing more than once are put in a list.
        posix : bool, default True
            Whether to split the input line in POSIX mode or not, as per the
            conventions outlined in the :mod:`shlex` module from the standard
            library.
        """

        # inject default options at the beginning of the input line
        caller = sys._getframe(1).f_code.co_name
        arg_str = '%s %s' % (self.options_table.get(caller,''),arg_str)

        mode = kw.get('mode','string')
        if mode not in ['string','list']:
            raise ValueError('incorrect mode given: %s' % mode)
        # Get options
        list_all = kw.get('list_all',0)
        posix = kw.get('posix', os.name == 'posix')
        strict = kw.get('strict', True)

        preserve_non_opts = kw.get("preserve_non_opts", False)
        remainder_arg_str = arg_str

        # Check if we have more than one argument to warrant extra processing:
        odict = {}  # Dictionary with options
        args = arg_str.split()
        if len(args) >= 1:
            # If the list of inputs only has 0 or 1 thing in it, there's no
            # need to look for options
            argv = arg_split(arg_str, posix, strict)
            # Do regular option processing
            try:
                opts, args = getopt(argv, opt_str, long_opts)
            except GetoptError as e:
                raise UsageError(
                    '%s (allowed: "%s"%s)'
                    % (e.msg, opt_str, " ".join(("",) + long_opts) if long_opts else "")
                ) from e
            for o, a in opts:
                if mode == "string" and preserve_non_opts:
                    # remove option-parts from the original args-string and preserve remaining-part.
                    # This relies on the arg_split(...) and getopt(...)'s impl spec, that the parsed options are
                    # returned in the original order.
                    remainder_arg_str = remainder_arg_str.replace(o, "", 1).replace(
                        a, "", 1
                    )
                if o.startswith("--"):
                    o = o[2:]
                else:
                    o = o[1:]
                try:
                    odict[o].append(a)
                except AttributeError:
                    odict[o] = [odict[o],a]
                except KeyError:
                    if list_all:
                        odict[o] = [a]
                    else:
                        odict[o] = a

        # Prepare opts,args for return
        opts = Struct(odict)
        if mode == 'string':
            if preserve_non_opts:
                args = remainder_arg_str.lstrip()
            else:
                args = " ".join(args)

        return opts,args

    def default_option(self, fn, optstr):
        """Make an entry in the options_table for fn, with value optstr"""

        if fn not in self.lsmagic():
            error("%s is not a magic function" % fn)
        self.options_table[fn] = optstr


class MagicAlias:
    """An alias to another magic function.

    An alias is determined by its magic name and magic kind. Lookup
    is done at call time, so if the underlying magic changes the alias
    will call the new function.

    Use the :meth:`MagicsManager.register_alias` method or the
    `%alias_magic` magic function to create and register a new alias.
    """
    def __init__(self, shell, magic_name, magic_kind, magic_params=None):
        self.shell = shell
        self.magic_name = magic_name
        self.magic_params = magic_params
        self.magic_kind = magic_kind

        self.pretty_target = '%s%s' % (magic_escapes[self.magic_kind], self.magic_name)
        self.__doc__ = "Alias for `%s`." % self.pretty_target

        self._in_call = False

    def __call__(self, *args, **kwargs):
        """Call the magic alias."""
        fn = self.shell.find_magic(self.magic_name, self.magic_kind)
        if fn is None:
            raise UsageError("Magic `%s` not found." % self.pretty_target)

        # Protect against infinite recursion.
        if self._in_call:
            raise UsageError("Infinite recursion detected; "
                             "magic aliases cannot call themselves.")
        self._in_call = True
        try:
            if self.magic_params:
                args_list = list(args)
                args_list[0] = self.magic_params + " " + args[0]
                args = tuple(args_list)
            return fn(*args, **kwargs)
        finally:
            self._in_call = False

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\licenses\_spdx.py ===

from __future__ import annotations

from typing import TypedDict

class SPDXLicense(TypedDict):
    id: str
    deprecated: bool

class SPDXException(TypedDict):
    id: str
    deprecated: bool


VERSION = '3.25.0'

LICENSES: dict[str, SPDXLicense] = {
    '0bsd': {'id': '0BSD', 'deprecated': False},
    '3d-slicer-1.0': {'id': '3D-Slicer-1.0', 'deprecated': False},
    'aal': {'id': 'AAL', 'deprecated': False},
    'abstyles': {'id': 'Abstyles', 'deprecated': False},
    'adacore-doc': {'id': 'AdaCore-doc', 'deprecated': False},
    'adobe-2006': {'id': 'Adobe-2006', 'deprecated': False},
    'adobe-display-postscript': {'id': 'Adobe-Display-PostScript', 'deprecated': False},
    'adobe-glyph': {'id': 'Adobe-Glyph', 'deprecated': False},
    'adobe-utopia': {'id': 'Adobe-Utopia', 'deprecated': False},
    'adsl': {'id': 'ADSL', 'deprecated': False},
    'afl-1.1': {'id': 'AFL-1.1', 'deprecated': False},
    'afl-1.2': {'id': 'AFL-1.2', 'deprecated': False},
    'afl-2.0': {'id': 'AFL-2.0', 'deprecated': False},
    'afl-2.1': {'id': 'AFL-2.1', 'deprecated': False},
    'afl-3.0': {'id': 'AFL-3.0', 'deprecated': False},
    'afmparse': {'id': 'Afmparse', 'deprecated': False},
    'agpl-1.0': {'id': 'AGPL-1.0', 'deprecated': True},
    'agpl-1.0-only': {'id': 'AGPL-1.0-only', 'deprecated': False},
    'agpl-1.0-or-later': {'id': 'AGPL-1.0-or-later', 'deprecated': False},
    'agpl-3.0': {'id': 'AGPL-3.0', 'deprecated': True},
    'agpl-3.0-only': {'id': 'AGPL-3.0-only', 'deprecated': False},
    'agpl-3.0-or-later': {'id': 'AGPL-3.0-or-later', 'deprecated': False},
    'aladdin': {'id': 'Aladdin', 'deprecated': False},
    'amd-newlib': {'id': 'AMD-newlib', 'deprecated': False},
    'amdplpa': {'id': 'AMDPLPA', 'deprecated': False},
    'aml': {'id': 'AML', 'deprecated': False},
    'aml-glslang': {'id': 'AML-glslang', 'deprecated': False},
    'ampas': {'id': 'AMPAS', 'deprecated': False},
    'antlr-pd': {'id': 'ANTLR-PD', 'deprecated': False},
    'antlr-pd-fallback': {'id': 'ANTLR-PD-fallback', 'deprecated': False},
    'any-osi': {'id': 'any-OSI', 'deprecated': False},
    'apache-1.0': {'id': 'Apache-1.0', 'deprecated': False},
    'apache-1.1': {'id': 'Apache-1.1', 'deprecated': False},
    'apache-2.0': {'id': 'Apache-2.0', 'deprecated': False},
    'apafml': {'id': 'APAFML', 'deprecated': False},
    'apl-1.0': {'id': 'APL-1.0', 'deprecated': False},
    'app-s2p': {'id': 'App-s2p', 'deprecated': False},
    'apsl-1.0': {'id': 'APSL-1.0', 'deprecated': False},
    'apsl-1.1': {'id': 'APSL-1.1', 'deprecated': False},
    'apsl-1.2': {'id': 'APSL-1.2', 'deprecated': False},
    'apsl-2.0': {'id': 'APSL-2.0', 'deprecated': False},
    'arphic-1999': {'id': 'Arphic-1999', 'deprecated': False},
    'artistic-1.0': {'id': 'Artistic-1.0', 'deprecated': False},
    'artistic-1.0-cl8': {'id': 'Artistic-1.0-cl8', 'deprecated': False},
    'artistic-1.0-perl': {'id': 'Artistic-1.0-Perl', 'deprecated': False},
    'artistic-2.0': {'id': 'Artistic-2.0', 'deprecated': False},
    'aswf-digital-assets-1.0': {'id': 'ASWF-Digital-Assets-1.0', 'deprecated': False},
    'aswf-digital-assets-1.1': {'id': 'ASWF-Digital-Assets-1.1', 'deprecated': False},
    'baekmuk': {'id': 'Baekmuk', 'deprecated': False},
    'bahyph': {'id': 'Bahyph', 'deprecated': False},
    'barr': {'id': 'Barr', 'deprecated': False},
    'bcrypt-solar-designer': {'id': 'bcrypt-Solar-Designer', 'deprecated': False},
    'beerware': {'id': 'Beerware', 'deprecated': False},
    'bitstream-charter': {'id': 'Bitstream-Charter', 'deprecated': False},
    'bitstream-vera': {'id': 'Bitstream-Vera', 'deprecated': False},
    'bittorrent-1.0': {'id': 'BitTorrent-1.0', 'deprecated': False},
    'bittorrent-1.1': {'id': 'BitTorrent-1.1', 'deprecated': False},
    'blessing': {'id': 'blessing', 'deprecated': False},
    'blueoak-1.0.0': {'id': 'BlueOak-1.0.0', 'deprecated': False},
    'boehm-gc': {'id': 'Boehm-GC', 'deprecated': False},
    'borceux': {'id': 'Borceux', 'deprecated': False},
    'brian-gladman-2-clause': {'id': 'Brian-Gladman-2-Clause', 'deprecated': False},
    'brian-gladman-3-clause': {'id': 'Brian-Gladman-3-Clause', 'deprecated': False},
    'bsd-1-clause': {'id': 'BSD-1-Clause', 'deprecated': False},
    'bsd-2-clause': {'id': 'BSD-2-Clause', 'deprecated': False},
    'bsd-2-clause-darwin': {'id': 'BSD-2-Clause-Darwin', 'deprecated': False},
    'bsd-2-clause-first-lines': {'id': 'BSD-2-Clause-first-lines', 'deprecated': False},
    'bsd-2-clause-freebsd': {'id': 'BSD-2-Clause-FreeBSD', 'deprecated': True},
    'bsd-2-clause-netbsd': {'id': 'BSD-2-Clause-NetBSD', 'deprecated': True},
    'bsd-2-clause-patent': {'id': 'BSD-2-Clause-Patent', 'deprecated': False},
    'bsd-2-clause-views': {'id': 'BSD-2-Clause-Views', 'deprecated': False},
    'bsd-3-clause': {'id': 'BSD-3-Clause', 'deprecated': False},
    'bsd-3-clause-acpica': {'id': 'BSD-3-Clause-acpica', 'deprecated': False},
    'bsd-3-clause-attribution': {'id': 'BSD-3-Clause-Attribution', 'deprecated': False},
    'bsd-3-clause-clear': {'id': 'BSD-3-Clause-Clear', 'deprecated': False},
    'bsd-3-clause-flex': {'id': 'BSD-3-Clause-flex', 'deprecated': False},
    'bsd-3-clause-hp': {'id': 'BSD-3-Clause-HP', 'deprecated': False},
    'bsd-3-clause-lbnl': {'id': 'BSD-3-Clause-LBNL', 'deprecated': False},
    'bsd-3-clause-modification': {'id': 'BSD-3-Clause-Modification', 'deprecated': False},
    'bsd-3-clause-no-military-license': {'id': 'BSD-3-Clause-No-Military-License', 'deprecated': False},
    'bsd-3-clause-no-nuclear-license': {'id': 'BSD-3-Clause-No-Nuclear-License', 'deprecated': False},
    'bsd-3-clause-no-nuclear-license-2014': {'id': 'BSD-3-Clause-No-Nuclear-License-2014', 'deprecated': False},
    'bsd-3-clause-no-nuclear-warranty': {'id': 'BSD-3-Clause-No-Nuclear-Warranty', 'deprecated': False},
    'bsd-3-clause-open-mpi': {'id': 'BSD-3-Clause-Open-MPI', 'deprecated': False},
    'bsd-3-clause-sun': {'id': 'BSD-3-Clause-Sun', 'deprecated': False},
    'bsd-4-clause': {'id': 'BSD-4-Clause', 'deprecated': False},
    'bsd-4-clause-shortened': {'id': 'BSD-4-Clause-Shortened', 'deprecated': False},
    'bsd-4-clause-uc': {'id': 'BSD-4-Clause-UC', 'deprecated': False},
    'bsd-4.3reno': {'id': 'BSD-4.3RENO', 'deprecated': False},
    'bsd-4.3tahoe': {'id': 'BSD-4.3TAHOE', 'deprecated': False},
    'bsd-advertising-acknowledgement': {'id': 'BSD-Advertising-Acknowledgement', 'deprecated': False},
    'bsd-attribution-hpnd-disclaimer': {'id': 'BSD-Attribution-HPND-disclaimer', 'deprecated': False},
    'bsd-inferno-nettverk': {'id': 'BSD-Inferno-Nettverk', 'deprecated': False},
    'bsd-protection': {'id': 'BSD-Protection', 'deprecated': False},
    'bsd-source-beginning-file': {'id': 'BSD-Source-beginning-file', 'deprecated': False},
    'bsd-source-code': {'id': 'BSD-Source-Code', 'deprecated': False},
    'bsd-systemics': {'id': 'BSD-Systemics', 'deprecated': False},
    'bsd-systemics-w3works': {'id': 'BSD-Systemics-W3Works', 'deprecated': False},
    'bsl-1.0': {'id': 'BSL-1.0', 'deprecated': False},
    'busl-1.1': {'id': 'BUSL-1.1', 'deprecated': False},
    'bzip2-1.0.5': {'id': 'bzip2-1.0.5', 'deprecated': True},
    'bzip2-1.0.6': {'id': 'bzip2-1.0.6', 'deprecated': False},
    'c-uda-1.0': {'id': 'C-UDA-1.0', 'deprecated': False},
    'cal-1.0': {'id': 'CAL-1.0', 'deprecated': False},
    'cal-1.0-combined-work-exception': {'id': 'CAL-1.0-Combined-Work-Exception', 'deprecated': False},
    'caldera': {'id': 'Caldera', 'deprecated': False},
    'caldera-no-preamble': {'id': 'Caldera-no-preamble', 'deprecated': False},
    'catharon': {'id': 'Catharon', 'deprecated': False},
    'catosl-1.1': {'id': 'CATOSL-1.1', 'deprecated': False},
    'cc-by-1.0': {'id': 'CC-BY-1.0', 'deprecated': False},
    'cc-by-2.0': {'id': 'CC-BY-2.0', 'deprecated': False},
    'cc-by-2.5': {'id': 'CC-BY-2.5', 'deprecated': False},
    'cc-by-2.5-au': {'id': 'CC-BY-2.5-AU', 'deprecated': False},
    'cc-by-3.0': {'id': 'CC-BY-3.0', 'deprecated': False},
    'cc-by-3.0-at': {'id': 'CC-BY-3.0-AT', 'deprecated': False},
    'cc-by-3.0-au': {'id': 'CC-BY-3.0-AU', 'deprecated': False},
    'cc-by-3.0-de': {'id': 'CC-BY-3.0-DE', 'deprecated': False},
    'cc-by-3.0-igo': {'id': 'CC-BY-3.0-IGO', 'deprecated': False},
    'cc-by-3.0-nl': {'id': 'CC-BY-3.0-NL', 'deprecated': False},
    'cc-by-3.0-us': {'id': 'CC-BY-3.0-US', 'deprecated': False},
    'cc-by-4.0': {'id': 'CC-BY-4.0', 'deprecated': False},
    'cc-by-nc-1.0': {'id': 'CC-BY-NC-1.0', 'deprecated': False},
    'cc-by-nc-2.0': {'id': 'CC-BY-NC-2.0', 'deprecated': False},
    'cc-by-nc-2.5': {'id': 'CC-BY-NC-2.5', 'deprecated': False},
    'cc-by-nc-3.0': {'id': 'CC-BY-NC-3.0', 'deprecated': False},
    'cc-by-nc-3.0-de': {'id': 'CC-BY-NC-3.0-DE', 'deprecated': False},
    'cc-by-nc-4.0': {'id': 'CC-BY-NC-4.0', 'deprecated': False},
    'cc-by-nc-nd-1.0': {'id': 'CC-BY-NC-ND-1.0', 'deprecated': False},
    'cc-by-nc-nd-2.0': {'id': 'CC-BY-NC-ND-2.0', 'deprecated': False},
    'cc-by-nc-nd-2.5': {'id': 'CC-BY-NC-ND-2.5', 'deprecated': False},
    'cc-by-nc-nd-3.0': {'id': 'CC-BY-NC-ND-3.0', 'deprecated': False},
    'cc-by-nc-nd-3.0-de': {'id': 'CC-BY-NC-ND-3.0-DE', 'deprecated': False},
    'cc-by-nc-nd-3.0-igo': {'id': 'CC-BY-NC-ND-3.0-IGO', 'deprecated': False},
    'cc-by-nc-nd-4.0': {'id': 'CC-BY-NC-ND-4.0', 'deprecated': False},
    'cc-by-nc-sa-1.0': {'id': 'CC-BY-NC-SA-1.0', 'deprecated': False},
    'cc-by-nc-sa-2.0': {'id': 'CC-BY-NC-SA-2.0', 'deprecated': False},
    'cc-by-nc-sa-2.0-de': {'id': 'CC-BY-NC-SA-2.0-DE', 'deprecated': False},
    'cc-by-nc-sa-2.0-fr': {'id': 'CC-BY-NC-SA-2.0-FR', 'deprecated': False},
    'cc-by-nc-sa-2.0-uk': {'id': 'CC-BY-NC-SA-2.0-UK', 'deprecated': False},
    'cc-by-nc-sa-2.5': {'id': 'CC-BY-NC-SA-2.5', 'deprecated': False},
    'cc-by-nc-sa-3.0': {'id': 'CC-BY-NC-SA-3.0', 'deprecated': False},
    'cc-by-nc-sa-3.0-de': {'id': 'CC-BY-NC-SA-3.0-DE', 'deprecated': False},
    'cc-by-nc-sa-3.0-igo': {'id': 'CC-BY-NC-SA-3.0-IGO', 'deprecated': False},
    'cc-by-nc-sa-4.0': {'id': 'CC-BY-NC-SA-4.0', 'deprecated': False},
    'cc-by-nd-1.0': {'id': 'CC-BY-ND-1.0', 'deprecated': False},
    'cc-by-nd-2.0': {'id': 'CC-BY-ND-2.0', 'deprecated': False},
    'cc-by-nd-2.5': {'id': 'CC-BY-ND-2.5', 'deprecated': False},
    'cc-by-nd-3.0': {'id': 'CC-BY-ND-3.0', 'deprecated': False},
    'cc-by-nd-3.0-de': {'id': 'CC-BY-ND-3.0-DE', 'deprecated': False},
    'cc-by-nd-4.0': {'id': 'CC-BY-ND-4.0', 'deprecated': False},
    'cc-by-sa-1.0': {'id': 'CC-BY-SA-1.0', 'deprecated': False},
    'cc-by-sa-2.0': {'id': 'CC-BY-SA-2.0', 'deprecated': False},
    'cc-by-sa-2.0-uk': {'id': 'CC-BY-SA-2.0-UK', 'deprecated': False},
    'cc-by-sa-2.1-jp': {'id': 'CC-BY-SA-2.1-JP', 'deprecated': False},
    'cc-by-sa-2.5': {'id': 'CC-BY-SA-2.5', 'deprecated': False},
    'cc-by-sa-3.0': {'id': 'CC-BY-SA-3.0', 'deprecated': False},
    'cc-by-sa-3.0-at': {'id': 'CC-BY-SA-3.0-AT', 'deprecated': False},
    'cc-by-sa-3.0-de': {'id': 'CC-BY-SA-3.0-DE', 'deprecated': False},
    'cc-by-sa-3.0-igo': {'id': 'CC-BY-SA-3.0-IGO', 'deprecated': False},
    'cc-by-sa-4.0': {'id': 'CC-BY-SA-4.0', 'deprecated': False},
    'cc-pddc': {'id': 'CC-PDDC', 'deprecated': False},
    'cc0-1.0': {'id': 'CC0-1.0', 'deprecated': False},
    'cddl-1.0': {'id': 'CDDL-1.0', 'deprecated': False},
    'cddl-1.1': {'id': 'CDDL-1.1', 'deprecated': False},
    'cdl-1.0': {'id': 'CDL-1.0', 'deprecated': False},
    'cdla-permissive-1.0': {'id': 'CDLA-Permissive-1.0', 'deprecated': False},
    'cdla-permissive-2.0': {'id': 'CDLA-Permissive-2.0', 'deprecated': False},
    'cdla-sharing-1.0': {'id': 'CDLA-Sharing-1.0', 'deprecated': False},
    'cecill-1.0': {'id': 'CECILL-1.0', 'deprecated': False},
    'cecill-1.1': {'id': 'CECILL-1.1', 'deprecated': False},
    'cecill-2.0': {'id': 'CECILL-2.0', 'deprecated': False},
    'cecill-2.1': {'id': 'CECILL-2.1', 'deprecated': False},
    'cecill-b': {'id': 'CECILL-B', 'deprecated': False},
    'cecill-c': {'id': 'CECILL-C', 'deprecated': False},
    'cern-ohl-1.1': {'id': 'CERN-OHL-1.1', 'deprecated': False},
    'cern-ohl-1.2': {'id': 'CERN-OHL-1.2', 'deprecated': False},
    'cern-ohl-p-2.0': {'id': 'CERN-OHL-P-2.0', 'deprecated': False},
    'cern-ohl-s-2.0': {'id': 'CERN-OHL-S-2.0', 'deprecated': False},
    'cern-ohl-w-2.0': {'id': 'CERN-OHL-W-2.0', 'deprecated': False},
    'cfitsio': {'id': 'CFITSIO', 'deprecated': False},
    'check-cvs': {'id': 'check-cvs', 'deprecated': False},
    'checkmk': {'id': 'checkmk', 'deprecated': False},
    'clartistic': {'id': 'ClArtistic', 'deprecated': False},
    'clips': {'id': 'Clips', 'deprecated': False},
    'cmu-mach': {'id': 'CMU-Mach', 'deprecated': False},
    'cmu-mach-nodoc': {'id': 'CMU-Mach-nodoc', 'deprecated': False},
    'cnri-jython': {'id': 'CNRI-Jython', 'deprecated': False},
    'cnri-python': {'id': 'CNRI-Python', 'deprecated': False},
    'cnri-python-gpl-compatible': {'id': 'CNRI-Python-GPL-Compatible', 'deprecated': False},
    'coil-1.0': {'id': 'COIL-1.0', 'deprecated': False},
    'community-spec-1.0': {'id': 'Community-Spec-1.0', 'deprecated': False},
    'condor-1.1': {'id': 'Condor-1.1', 'deprecated': False},
    'copyleft-next-0.3.0': {'id': 'copyleft-next-0.3.0', 'deprecated': False},
    'copyleft-next-0.3.1': {'id': 'copyleft-next-0.3.1', 'deprecated': False},
    'cornell-lossless-jpeg': {'id': 'Cornell-Lossless-JPEG', 'deprecated': False},
    'cpal-1.0': {'id': 'CPAL-1.0', 'deprecated': False},
    'cpl-1.0': {'id': 'CPL-1.0', 'deprecated': False},
    'cpol-1.02': {'id': 'CPOL-1.02', 'deprecated': False},
    'cronyx': {'id': 'Cronyx', 'deprecated': False},
    'crossword': {'id': 'Crossword', 'deprecated': False},
    'crystalstacker': {'id': 'CrystalStacker', 'deprecated': False},
    'cua-opl-1.0': {'id': 'CUA-OPL-1.0', 'deprecated': False},
    'cube': {'id': 'Cube', 'deprecated': False},
    'curl': {'id': 'curl', 'deprecated': False},
    'cve-tou': {'id': 'cve-tou', 'deprecated': False},
    'd-fsl-1.0': {'id': 'D-FSL-1.0', 'deprecated': False},
    'dec-3-clause': {'id': 'DEC-3-Clause', 'deprecated': False},
    'diffmark': {'id': 'diffmark', 'deprecated': False},
    'dl-de-by-2.0': {'id': 'DL-DE-BY-2.0', 'deprecated': False},
    'dl-de-zero-2.0': {'id': 'DL-DE-ZERO-2.0', 'deprecated': False},
    'doc': {'id': 'DOC', 'deprecated': False},
    'docbook-schema': {'id': 'DocBook-Schema', 'deprecated': False},
    'docbook-xml': {'id': 'DocBook-XML', 'deprecated': False},
    'dotseqn': {'id': 'Dotseqn', 'deprecated': False},
    'drl-1.0': {'id': 'DRL-1.0', 'deprecated': False},
    'drl-1.1': {'id': 'DRL-1.1', 'deprecated': False},
    'dsdp': {'id': 'DSDP', 'deprecated': False},
    'dtoa': {'id': 'dtoa', 'deprecated': False},
    'dvipdfm': {'id': 'dvipdfm', 'deprecated': False},
    'ecl-1.0': {'id': 'ECL-1.0', 'deprecated': False},
    'ecl-2.0': {'id': 'ECL-2.0', 'deprecated': False},
    'ecos-2.0': {'id': 'eCos-2.0', 'deprecated': True},
    'efl-1.0': {'id': 'EFL-1.0', 'deprecated': False},
    'efl-2.0': {'id': 'EFL-2.0', 'deprecated': False},
    'egenix': {'id': 'eGenix', 'deprecated': False},
    'elastic-2.0': {'id': 'Elastic-2.0', 'deprecated': False},
    'entessa': {'id': 'Entessa', 'deprecated': False},
    'epics': {'id': 'EPICS', 'deprecated': False},
    'epl-1.0': {'id': 'EPL-1.0', 'deprecated': False},
    'epl-2.0': {'id': 'EPL-2.0', 'deprecated': False},
    'erlpl-1.1': {'id': 'ErlPL-1.1', 'deprecated': False},
    'etalab-2.0': {'id': 'etalab-2.0', 'deprecated': False},
    'eudatagrid': {'id': 'EUDatagrid', 'deprecated': False},
    'eupl-1.0': {'id': 'EUPL-1.0', 'deprecated': False},
    'eupl-1.1': {'id': 'EUPL-1.1', 'deprecated': False},
    'eupl-1.2': {'id': 'EUPL-1.2', 'deprecated': False},
    'eurosym': {'id': 'Eurosym', 'deprecated': False},
    'fair': {'id': 'Fair', 'deprecated': False},
    'fbm': {'id': 'FBM', 'deprecated': False},
    'fdk-aac': {'id': 'FDK-AAC', 'deprecated': False},
    'ferguson-twofish': {'id': 'Ferguson-Twofish', 'deprecated': False},
    'frameworx-1.0': {'id': 'Frameworx-1.0', 'deprecated': False},
    'freebsd-doc': {'id': 'FreeBSD-DOC', 'deprecated': False},
    'freeimage': {'id': 'FreeImage', 'deprecated': False},
    'fsfap': {'id': 'FSFAP', 'deprecated': False},
    'fsfap-no-warranty-disclaimer': {'id': 'FSFAP-no-warranty-disclaimer', 'deprecated': False},
    'fsful': {'id': 'FSFUL', 'deprecated': False},
    'fsfullr': {'id': 'FSFULLR', 'deprecated': False},
    'fsfullrwd': {'id': 'FSFULLRWD', 'deprecated': False},
    'ftl': {'id': 'FTL', 'deprecated': False},
    'furuseth': {'id': 'Furuseth', 'deprecated': False},
    'fwlw': {'id': 'fwlw', 'deprecated': False},
    'gcr-docs': {'id': 'GCR-docs', 'deprecated': False},
    'gd': {'id': 'GD', 'deprecated': False},
    'gfdl-1.1': {'id': 'GFDL-1.1', 'deprecated': True},
    'gfdl-1.1-invariants-only': {'id': 'GFDL-1.1-invariants-only', 'deprecated': False},
    'gfdl-1.1-invariants-or-later': {'id': 'GFDL-1.1-invariants-or-later', 'deprecated': False},
    'gfdl-1.1-no-invariants-only': {'id': 'GFDL-1.1-no-invariants-only', 'deprecated': False},
    'gfdl-1.1-no-invariants-or-later': {'id': 'GFDL-1.1-no-invariants-or-later', 'deprecated': False},
    'gfdl-1.1-only': {'id': 'GFDL-1.1-only', 'deprecated': False},
    'gfdl-1.1-or-later': {'id': 'GFDL-1.1-or-later', 'deprecated': False},
    'gfdl-1.2': {'id': 'GFDL-1.2', 'deprecated': True},
    'gfdl-1.2-invariants-only': {'id': 'GFDL-1.2-invariants-only', 'deprecated': False},
    'gfdl-1.2-invariants-or-later': {'id': 'GFDL-1.2-invariants-or-later', 'deprecated': False},
    'gfdl-1.2-no-invariants-only': {'id': 'GFDL-1.2-no-invariants-only', 'deprecated': False},
    'gfdl-1.2-no-invariants-or-later': {'id': 'GFDL-1.2-no-invariants-or-later', 'deprecated': False},
    'gfdl-1.2-only': {'id': 'GFDL-1.2-only', 'deprecated': False},
    'gfdl-1.2-or-later': {'id': 'GFDL-1.2-or-later', 'deprecated': False},
    'gfdl-1.3': {'id': 'GFDL-1.3', 'deprecated': True},
    'gfdl-1.3-invariants-only': {'id': 'GFDL-1.3-invariants-only', 'deprecated': False},
    'gfdl-1.3-invariants-or-later': {'id': 'GFDL-1.3-invariants-or-later', 'deprecated': False},
    'gfdl-1.3-no-invariants-only': {'id': 'GFDL-1.3-no-invariants-only', 'deprecated': False},
    'gfdl-1.3-no-invariants-or-later': {'id': 'GFDL-1.3-no-invariants-or-later', 'deprecated': False},
    'gfdl-1.3-only': {'id': 'GFDL-1.3-only', 'deprecated': False},
    'gfdl-1.3-or-later': {'id': 'GFDL-1.3-or-later', 'deprecated': False},
    'giftware': {'id': 'Giftware', 'deprecated': False},
    'gl2ps': {'id': 'GL2PS', 'deprecated': False},
    'glide': {'id': 'Glide', 'deprecated': False},
    'glulxe': {'id': 'Glulxe', 'deprecated': False},
    'glwtpl': {'id': 'GLWTPL', 'deprecated': False},
    'gnuplot': {'id': 'gnuplot', 'deprecated': False},
    'gpl-1.0': {'id': 'GPL-1.0', 'deprecated': True},
    'gpl-1.0+': {'id': 'GPL-1.0+', 'deprecated': True},
    'gpl-1.0-only': {'id': 'GPL-1.0-only', 'deprecated': False},
    'gpl-1.0-or-later': {'id': 'GPL-1.0-or-later', 'deprecated': False},
    'gpl-2.0': {'id': 'GPL-2.0', 'deprecated': True},
    'gpl-2.0+': {'id': 'GPL-2.0+', 'deprecated': True},
    'gpl-2.0-only': {'id': 'GPL-2.0-only', 'deprecated': False},
    'gpl-2.0-or-later': {'id': 'GPL-2.0-or-later', 'deprecated': False},
    'gpl-2.0-with-autoconf-exception': {'id': 'GPL-2.0-with-autoconf-exception', 'deprecated': True},
    'gpl-2.0-with-bison-exception': {'id': 'GPL-2.0-with-bison-exception', 'deprecated': True},
    'gpl-2.0-with-classpath-exception': {'id': 'GPL-2.0-with-classpath-exception', 'deprecated': True},
    'gpl-2.0-with-font-exception': {'id': 'GPL-2.0-with-font-exception', 'deprecated': True},
    'gpl-2.0-with-gcc-exception': {'id': 'GPL-2.0-with-GCC-exception', 'deprecated': True},
    'gpl-3.0': {'id': 'GPL-3.0', 'deprecated': True},
    'gpl-3.0+': {'id': 'GPL-3.0+', 'deprecated': True},
    'gpl-3.0-only': {'id': 'GPL-3.0-only', 'deprecated': False},
    'gpl-3.0-or-later': {'id': 'GPL-3.0-or-later', 'deprecated': False},
    'gpl-3.0-with-autoconf-exception': {'id': 'GPL-3.0-with-autoconf-exception', 'deprecated': True},
    'gpl-3.0-with-gcc-exception': {'id': 'GPL-3.0-with-GCC-exception', 'deprecated': True},
    'graphics-gems': {'id': 'Graphics-Gems', 'deprecated': False},
    'gsoap-1.3b': {'id': 'gSOAP-1.3b', 'deprecated': False},
    'gtkbook': {'id': 'gtkbook', 'deprecated': False},
    'gutmann': {'id': 'Gutmann', 'deprecated': False},
    'haskellreport': {'id': 'HaskellReport', 'deprecated': False},
    'hdparm': {'id': 'hdparm', 'deprecated': False},
    'hidapi': {'id': 'HIDAPI', 'deprecated': False},
    'hippocratic-2.1': {'id': 'Hippocratic-2.1', 'deprecated': False},
    'hp-1986': {'id': 'HP-1986', 'deprecated': False},
    'hp-1989': {'id': 'HP-1989', 'deprecated': False},
    'hpnd': {'id': 'HPND', 'deprecated': False},
    'hpnd-dec': {'id': 'HPND-DEC', 'deprecated': False},
    'hpnd-doc': {'id': 'HPND-doc', 'deprecated': False},
    'hpnd-doc-sell': {'id': 'HPND-doc-sell', 'deprecated': False},
    'hpnd-export-us': {'id': 'HPND-export-US', 'deprecated': False},
    'hpnd-export-us-acknowledgement': {'id': 'HPND-export-US-acknowledgement', 'deprecated': False},
    'hpnd-export-us-modify': {'id': 'HPND-export-US-modify', 'deprecated': False},
    'hpnd-export2-us': {'id': 'HPND-export2-US', 'deprecated': False},
    'hpnd-fenneberg-livingston': {'id': 'HPND-Fenneberg-Livingston', 'deprecated': False},
    'hpnd-inria-imag': {'id': 'HPND-INRIA-IMAG', 'deprecated': False},
    'hpnd-intel': {'id': 'HPND-Intel', 'deprecated': False},
    'hpnd-kevlin-henney': {'id': 'HPND-Kevlin-Henney', 'deprecated': False},
    'hpnd-markus-kuhn': {'id': 'HPND-Markus-Kuhn', 'deprecated': False},
    'hpnd-merchantability-variant': {'id': 'HPND-merchantability-variant', 'deprecated': False},
    'hpnd-mit-disclaimer': {'id': 'HPND-MIT-disclaimer', 'deprecated': False},
    'hpnd-netrek': {'id': 'HPND-Netrek', 'deprecated': False},
    'hpnd-pbmplus': {'id': 'HPND-Pbmplus', 'deprecated': False},
    'hpnd-sell-mit-disclaimer-xserver': {'id': 'HPND-sell-MIT-disclaimer-xserver', 'deprecated': False},
    'hpnd-sell-regexpr': {'id': 'HPND-sell-regexpr', 'deprecated': False},
    'hpnd-sell-variant': {'id': 'HPND-sell-variant', 'deprecated': False},
    'hpnd-sell-variant-mit-disclaimer': {'id': 'HPND-sell-variant-MIT-disclaimer', 'deprecated': False},
    'hpnd-sell-variant-mit-disclaimer-rev': {'id': 'HPND-sell-variant-MIT-disclaimer-rev', 'deprecated': False},
    'hpnd-uc': {'id': 'HPND-UC', 'deprecated': False},
    'hpnd-uc-export-us': {'id': 'HPND-UC-export-US', 'deprecated': False},
    'htmltidy': {'id': 'HTMLTIDY', 'deprecated': False},
    'ibm-pibs': {'id': 'IBM-pibs', 'deprecated': False},
    'icu': {'id': 'ICU', 'deprecated': False},
    'iec-code-components-eula': {'id': 'IEC-Code-Components-EULA', 'deprecated': False},
    'ijg': {'id': 'IJG', 'deprecated': False},
    'ijg-short': {'id': 'IJG-short', 'deprecated': False},
    'imagemagick': {'id': 'ImageMagick', 'deprecated': False},
    'imatix': {'id': 'iMatix', 'deprecated': False},
    'imlib2': {'id': 'Imlib2', 'deprecated': False},
    'info-zip': {'id': 'Info-ZIP', 'deprecated': False},
    'inner-net-2.0': {'id': 'Inner-Net-2.0', 'deprecated': False},
    'intel': {'id': 'Intel', 'deprecated': False},
    'intel-acpi': {'id': 'Intel-ACPI', 'deprecated': False},
    'interbase-1.0': {'id': 'Interbase-1.0', 'deprecated': False},
    'ipa': {'id': 'IPA', 'deprecated': False},
    'ipl-1.0': {'id': 'IPL-1.0', 'deprecated': False},
    'isc': {'id': 'ISC', 'deprecated': False},
    'isc-veillard': {'id': 'ISC-Veillard', 'deprecated': False},
    'jam': {'id': 'Jam', 'deprecated': False},
    'jasper-2.0': {'id': 'JasPer-2.0', 'deprecated': False},
    'jpl-image': {'id': 'JPL-image', 'deprecated': False},
    'jpnic': {'id': 'JPNIC', 'deprecated': False},
    'json': {'id': 'JSON', 'deprecated': False},
    'kastrup': {'id': 'Kastrup', 'deprecated': False},
    'kazlib': {'id': 'Kazlib', 'deprecated': False},
    'knuth-ctan': {'id': 'Knuth-CTAN', 'deprecated': False},
    'lal-1.2': {'id': 'LAL-1.2', 'deprecated': False},
    'lal-1.3': {'id': 'LAL-1.3', 'deprecated': False},
    'latex2e': {'id': 'Latex2e', 'deprecated': False},
    'latex2e-translated-notice': {'id': 'Latex2e-translated-notice', 'deprecated': False},
    'leptonica': {'id': 'Leptonica', 'deprecated': False},
    'lgpl-2.0': {'id': 'LGPL-2.0', 'deprecated': True},
    'lgpl-2.0+': {'id': 'LGPL-2.0+', 'deprecated': True},
    'lgpl-2.0-only': {'id': 'LGPL-2.0-only', 'deprecated': False},
    'lgpl-2.0-or-later': {'id': 'LGPL-2.0-or-later', 'deprecated': False},
    'lgpl-2.1': {'id': 'LGPL-2.1', 'deprecated': True},
    'lgpl-2.1+': {'id': 'LGPL-2.1+', 'deprecated': True},
    'lgpl-2.1-only': {'id': 'LGPL-2.1-only', 'deprecated': False},
    'lgpl-2.1-or-later': {'id': 'LGPL-2.1-or-later', 'deprecated': False},
    'lgpl-3.0': {'id': 'LGPL-3.0', 'deprecated': True},
    'lgpl-3.0+': {'id': 'LGPL-3.0+', 'deprecated': True},
    'lgpl-3.0-only': {'id': 'LGPL-3.0-only', 'deprecated': False},
    'lgpl-3.0-or-later': {'id': 'LGPL-3.0-or-later', 'deprecated': False},
    'lgpllr': {'id': 'LGPLLR', 'deprecated': False},
    'libpng': {'id': 'Libpng', 'deprecated': False},
    'libpng-2.0': {'id': 'libpng-2.0', 'deprecated': False},
    'libselinux-1.0': {'id': 'libselinux-1.0', 'deprecated': False},
    'libtiff': {'id': 'libtiff', 'deprecated': False},
    'libutil-david-nugent': {'id': 'libutil-David-Nugent', 'deprecated': False},
    'liliq-p-1.1': {'id': 'LiLiQ-P-1.1', 'deprecated': False},
    'liliq-r-1.1': {'id': 'LiLiQ-R-1.1', 'deprecated': False},
    'liliq-rplus-1.1': {'id': 'LiLiQ-Rplus-1.1', 'deprecated': False},
    'linux-man-pages-1-para': {'id': 'Linux-man-pages-1-para', 'deprecated': False},
    'linux-man-pages-copyleft': {'id': 'Linux-man-pages-copyleft', 'deprecated': False},
    'linux-man-pages-copyleft-2-para': {'id': 'Linux-man-pages-copyleft-2-para', 'deprecated': False},
    'linux-man-pages-copyleft-var': {'id': 'Linux-man-pages-copyleft-var', 'deprecated': False},
    'linux-openib': {'id': 'Linux-OpenIB', 'deprecated': False},
    'loop': {'id': 'LOOP', 'deprecated': False},
    'lpd-document': {'id': 'LPD-document', 'deprecated': False},
    'lpl-1.0': {'id': 'LPL-1.0', 'deprecated': False},
    'lpl-1.02': {'id': 'LPL-1.02', 'deprecated': False},
    'lppl-1.0': {'id': 'LPPL-1.0', 'deprecated': False},
    'lppl-1.1': {'id': 'LPPL-1.1', 'deprecated': False},
    'lppl-1.2': {'id': 'LPPL-1.2', 'deprecated': False},
    'lppl-1.3a': {'id': 'LPPL-1.3a', 'deprecated': False},
    'lppl-1.3c': {'id': 'LPPL-1.3c', 'deprecated': False},
    'lsof': {'id': 'lsof', 'deprecated': False},
    'lucida-bitmap-fonts': {'id': 'Lucida-Bitmap-Fonts', 'deprecated': False},
    'lzma-sdk-9.11-to-9.20': {'id': 'LZMA-SDK-9.11-to-9.20', 'deprecated': False},
    'lzma-sdk-9.22': {'id': 'LZMA-SDK-9.22', 'deprecated': False},
    'mackerras-3-clause': {'id': 'Mackerras-3-Clause', 'deprecated': False},
    'mackerras-3-clause-acknowledgment': {'id': 'Mackerras-3-Clause-acknowledgment', 'deprecated': False},
    'magaz': {'id': 'magaz', 'deprecated': False},
    'mailprio': {'id': 'mailprio', 'deprecated': False},
    'makeindex': {'id': 'MakeIndex', 'deprecated': False},
    'martin-birgmeier': {'id': 'Martin-Birgmeier', 'deprecated': False},
    'mcphee-slideshow': {'id': 'McPhee-slideshow', 'deprecated': False},
    'metamail': {'id': 'metamail', 'deprecated': False},
    'minpack': {'id': 'Minpack', 'deprecated': False},
    'miros': {'id': 'MirOS', 'deprecated': False},
    'mit': {'id': 'MIT', 'deprecated': False},
    'mit-0': {'id': 'MIT-0', 'deprecated': False},
    'mit-advertising': {'id': 'MIT-advertising', 'deprecated': False},
    'mit-cmu': {'id': 'MIT-CMU', 'deprecated': False},
    'mit-enna': {'id': 'MIT-enna', 'deprecated': False},
    'mit-feh': {'id': 'MIT-feh', 'deprecated': False},
    'mit-festival': {'id': 'MIT-Festival', 'deprecated': False},
    'mit-khronos-old': {'id': 'MIT-Khronos-old', 'deprecated': False},
    'mit-modern-variant': {'id': 'MIT-Modern-Variant', 'deprecated': False},
    'mit-open-group': {'id': 'MIT-open-group', 'deprecated': False},
    'mit-testregex': {'id': 'MIT-testregex', 'deprecated': False},
    'mit-wu': {'id': 'MIT-Wu', 'deprecated': False},
    'mitnfa': {'id': 'MITNFA', 'deprecated': False},
    'mmixware': {'id': 'MMIXware', 'deprecated': False},
    'motosoto': {'id': 'Motosoto', 'deprecated': False},
    'mpeg-ssg': {'id': 'MPEG-SSG', 'deprecated': False},
    'mpi-permissive': {'id': 'mpi-permissive', 'deprecated': False},
    'mpich2': {'id': 'mpich2', 'deprecated': False},
    'mpl-1.0': {'id': 'MPL-1.0', 'deprecated': False},
    'mpl-1.1': {'id': 'MPL-1.1', 'deprecated': False},
    'mpl-2.0': {'id': 'MPL-2.0', 'deprecated': False},
    'mpl-2.0-no-copyleft-exception': {'id': 'MPL-2.0-no-copyleft-exception', 'deprecated': False},
    'mplus': {'id': 'mplus', 'deprecated': False},
    'ms-lpl': {'id': 'MS-LPL', 'deprecated': False},
    'ms-pl': {'id': 'MS-PL', 'deprecated': False},
    'ms-rl': {'id': 'MS-RL', 'deprecated': False},
    'mtll': {'id': 'MTLL', 'deprecated': False},
    'mulanpsl-1.0': {'id': 'MulanPSL-1.0', 'deprecated': False},
    'mulanpsl-2.0': {'id': 'MulanPSL-2.0', 'deprecated': False},
    'multics': {'id': 'Multics', 'deprecated': False},
    'mup': {'id': 'Mup', 'deprecated': False},
    'naist-2003': {'id': 'NAIST-2003', 'deprecated': False},
    'nasa-1.3': {'id': 'NASA-1.3', 'deprecated': False},
    'naumen': {'id': 'Naumen', 'deprecated': False},
    'nbpl-1.0': {'id': 'NBPL-1.0', 'deprecated': False},
    'ncbi-pd': {'id': 'NCBI-PD', 'deprecated': False},
    'ncgl-uk-2.0': {'id': 'NCGL-UK-2.0', 'deprecated': False},
    'ncl': {'id': 'NCL', 'deprecated': False},
    'ncsa': {'id': 'NCSA', 'deprecated': False},
    'net-snmp': {'id': 'Net-SNMP', 'deprecated': True},
    'netcdf': {'id': 'NetCDF', 'deprecated': False},
    'newsletr': {'id': 'Newsletr', 'deprecated': False},
    'ngpl': {'id': 'NGPL', 'deprecated': False},
    'nicta-1.0': {'id': 'NICTA-1.0', 'deprecated': False},
    'nist-pd': {'id': 'NIST-PD', 'deprecated': False},
    'nist-pd-fallback': {'id': 'NIST-PD-fallback', 'deprecated': False},
    'nist-software': {'id': 'NIST-Software', 'deprecated': False},
    'nlod-1.0': {'id': 'NLOD-1.0', 'deprecated': False},
    'nlod-2.0': {'id': 'NLOD-2.0', 'deprecated': False},
    'nlpl': {'id': 'NLPL', 'deprecated': False},
    'nokia': {'id': 'Nokia', 'deprecated': False},
    'nosl': {'id': 'NOSL', 'deprecated': False},
    'noweb': {'id': 'Noweb', 'deprecated': False},
    'npl-1.0': {'id': 'NPL-1.0', 'deprecated': False},
    'npl-1.1': {'id': 'NPL-1.1', 'deprecated': False},
    'nposl-3.0': {'id': 'NPOSL-3.0', 'deprecated': False},
    'nrl': {'id': 'NRL', 'deprecated': False},
    'ntp': {'id': 'NTP', 'deprecated': False},
    'ntp-0': {'id': 'NTP-0', 'deprecated': False},
    'nunit': {'id': 'Nunit', 'deprecated': True},
    'o-uda-1.0': {'id': 'O-UDA-1.0', 'deprecated': False},
    'oar': {'id': 'OAR', 'deprecated': False},
    'occt-pl': {'id': 'OCCT-PL', 'deprecated': False},
    'oclc-2.0': {'id': 'OCLC-2.0', 'deprecated': False},
    'odbl-1.0': {'id': 'ODbL-1.0', 'deprecated': False},
    'odc-by-1.0': {'id': 'ODC-By-1.0', 'deprecated': False},
    'offis': {'id': 'OFFIS', 'deprecated': False},
    'ofl-1.0': {'id': 'OFL-1.0', 'deprecated': False},
    'ofl-1.0-no-rfn': {'id': 'OFL-1.0-no-RFN', 'deprecated': False},
    'ofl-1.0-rfn': {'id': 'OFL-1.0-RFN', 'deprecated': False},
    'ofl-1.1': {'id': 'OFL-1.1', 'deprecated': False},
    'ofl-1.1-no-rfn': {'id': 'OFL-1.1-no-RFN', 'deprecated': False},
    'ofl-1.1-rfn': {'id': 'OFL-1.1-RFN', 'deprecated': False},
    'ogc-1.0': {'id': 'OGC-1.0', 'deprecated': False},
    'ogdl-taiwan-1.0': {'id': 'OGDL-Taiwan-1.0', 'deprecated': False},
    'ogl-canada-2.0': {'id': 'OGL-Canada-2.0', 'deprecated': False},
    'ogl-uk-1.0': {'id': 'OGL-UK-1.0', 'deprecated': False},
    'ogl-uk-2.0': {'id': 'OGL-UK-2.0', 'deprecated': False},
    'ogl-uk-3.0': {'id': 'OGL-UK-3.0', 'deprecated': False},
    'ogtsl': {'id': 'OGTSL', 'deprecated': False},
    'oldap-1.1': {'id': 'OLDAP-1.1', 'deprecated': False},
    'oldap-1.2': {'id': 'OLDAP-1.2', 'deprecated': False},
    'oldap-1.3': {'id': 'OLDAP-1.3', 'deprecated': False},
    'oldap-1.4': {'id': 'OLDAP-1.4', 'deprecated': False},
    'oldap-2.0': {'id': 'OLDAP-2.0', 'deprecated': False},
    'oldap-2.0.1': {'id': 'OLDAP-2.0.1', 'deprecated': False},
    'oldap-2.1': {'id': 'OLDAP-2.1', 'deprecated': False},
    'oldap-2.2': {'id': 'OLDAP-2.2', 'deprecated': False},
    'oldap-2.2.1': {'id': 'OLDAP-2.2.1', 'deprecated': False},
    'oldap-2.2.2': {'id': 'OLDAP-2.2.2', 'deprecated': False},
    'oldap-2.3': {'id': 'OLDAP-2.3', 'deprecated': False},
    'oldap-2.4': {'id': 'OLDAP-2.4', 'deprecated': False},
    'oldap-2.5': {'id': 'OLDAP-2.5', 'deprecated': False},
    'oldap-2.6': {'id': 'OLDAP-2.6', 'deprecated': False},
    'oldap-2.7': {'id': 'OLDAP-2.7', 'deprecated': False},
    'oldap-2.8': {'id': 'OLDAP-2.8', 'deprecated': False},
    'olfl-1.3': {'id': 'OLFL-1.3', 'deprecated': False},
    'oml': {'id': 'OML', 'deprecated': False},
    'openpbs-2.3': {'id': 'OpenPBS-2.3', 'deprecated': False},
    'openssl': {'id': 'OpenSSL', 'deprecated': False},
    'openssl-standalone': {'id': 'OpenSSL-standalone', 'deprecated': False},
    'openvision': {'id': 'OpenVision', 'deprecated': False},
    'opl-1.0': {'id': 'OPL-1.0', 'deprecated': False},
    'opl-uk-3.0': {'id': 'OPL-UK-3.0', 'deprecated': False},
    'opubl-1.0': {'id': 'OPUBL-1.0', 'deprecated': False},
    'oset-pl-2.1': {'id': 'OSET-PL-2.1', 'deprecated': False},
    'osl-1.0': {'id': 'OSL-1.0', 'deprecated': False},
    'osl-1.1': {'id': 'OSL-1.1', 'deprecated': False},
    'osl-2.0': {'id': 'OSL-2.0', 'deprecated': False},
    'osl-2.1': {'id': 'OSL-2.1', 'deprecated': False},
    'osl-3.0': {'id': 'OSL-3.0', 'deprecated': False},
    'padl': {'id': 'PADL', 'deprecated': False},
    'parity-6.0.0': {'id': 'Parity-6.0.0', 'deprecated': False},
    'parity-7.0.0': {'id': 'Parity-7.0.0', 'deprecated': False},
    'pddl-1.0': {'id': 'PDDL-1.0', 'deprecated': False},
    'php-3.0': {'id': 'PHP-3.0', 'deprecated': False},
    'php-3.01': {'id': 'PHP-3.01', 'deprecated': False},
    'pixar': {'id': 'Pixar', 'deprecated': False},
    'pkgconf': {'id': 'pkgconf', 'deprecated': False},
    'plexus': {'id': 'Plexus', 'deprecated': False},
    'pnmstitch': {'id': 'pnmstitch', 'deprecated': False},
    'polyform-noncommercial-1.0.0': {'id': 'PolyForm-Noncommercial-1.0.0', 'deprecated': False},
    'polyform-small-business-1.0.0': {'id': 'PolyForm-Small-Business-1.0.0', 'deprecated': False},
    'postgresql': {'id': 'PostgreSQL', 'deprecated': False},
    'ppl': {'id': 'PPL', 'deprecated': False},
    'psf-2.0': {'id': 'PSF-2.0', 'deprecated': False},
    'psfrag': {'id': 'psfrag', 'deprecated': False},
    'psutils': {'id': 'psutils', 'deprecated': False},
    'python-2.0': {'id': 'Python-2.0', 'deprecated': False},
    'python-2.0.1': {'id': 'Python-2.0.1', 'deprecated': False},
    'python-ldap': {'id': 'python-ldap', 'deprecated': False},
    'qhull': {'id': 'Qhull', 'deprecated': False},
    'qpl-1.0': {'id': 'QPL-1.0', 'deprecated': False},
    'qpl-1.0-inria-2004': {'id': 'QPL-1.0-INRIA-2004', 'deprecated': False},
    'radvd': {'id': 'radvd', 'deprecated': False},
    'rdisc': {'id': 'Rdisc', 'deprecated': False},
    'rhecos-1.1': {'id': 'RHeCos-1.1', 'deprecated': False},
    'rpl-1.1': {'id': 'RPL-1.1', 'deprecated': False},
    'rpl-1.5': {'id': 'RPL-1.5', 'deprecated': False},
    'rpsl-1.0': {'id': 'RPSL-1.0', 'deprecated': False},
    'rsa-md': {'id': 'RSA-MD', 'deprecated': False},
    'rscpl': {'id': 'RSCPL', 'deprecated': False},
    'ruby': {'id': 'Ruby', 'deprecated': False},
    'ruby-pty': {'id': 'Ruby-pty', 'deprecated': False},
    'sax-pd': {'id': 'SAX-PD', 'deprecated': False},
    'sax-pd-2.0': {'id': 'SAX-PD-2.0', 'deprecated': False},
    'saxpath': {'id': 'Saxpath', 'deprecated': False},
    'scea': {'id': 'SCEA', 'deprecated': False},
    'schemereport': {'id': 'SchemeReport', 'deprecated': False},
    'sendmail': {'id': 'Sendmail', 'deprecated': False},
    'sendmail-8.23': {'id': 'Sendmail-8.23', 'deprecated': False},
    'sgi-b-1.0': {'id': 'SGI-B-1.0', 'deprecated': False},
    'sgi-b-1.1': {'id': 'SGI-B-1.1', 'deprecated': False},
    'sgi-b-2.0': {'id': 'SGI-B-2.0', 'deprecated': False},
    'sgi-opengl': {'id': 'SGI-OpenGL', 'deprecated': False},
    'sgp4': {'id': 'SGP4', 'deprecated': False},
    'shl-0.5': {'id': 'SHL-0.5', 'deprecated': False},
    'shl-0.51': {'id': 'SHL-0.51', 'deprecated': False},
    'simpl-2.0': {'id': 'SimPL-2.0', 'deprecated': False},
    'sissl': {'id': 'SISSL', 'deprecated': False},
    'sissl-1.2': {'id': 'SISSL-1.2', 'deprecated': False},
    'sl': {'id': 'SL', 'deprecated': False},
    'sleepycat': {'id': 'Sleepycat', 'deprecated': False},
    'smlnj': {'id': 'SMLNJ', 'deprecated': False},
    'smppl': {'id': 'SMPPL', 'deprecated': False},
    'snia': {'id': 'SNIA', 'deprecated': False},
    'snprintf': {'id': 'snprintf', 'deprecated': False},
    'softsurfer': {'id': 'softSurfer', 'deprecated': False},
    'soundex': {'id': 'Soundex', 'deprecated': False},
    'spencer-86': {'id': 'Spencer-86', 'deprecated': False},
    'spencer-94': {'id': 'Spencer-94', 'deprecated': False},
    'spencer-99': {'id': 'Spencer-99', 'deprecated': False},
    'spl-1.0': {'id': 'SPL-1.0', 'deprecated': False},
    'ssh-keyscan': {'id': 'ssh-keyscan', 'deprecated': False},
    'ssh-openssh': {'id': 'SSH-OpenSSH', 'deprecated': False},
    'ssh-short': {'id': 'SSH-short', 'deprecated': False},
    'ssleay-standalone': {'id': 'SSLeay-standalone', 'deprecated': False},
    'sspl-1.0': {'id': 'SSPL-1.0', 'deprecated': False},
    'standardml-nj': {'id': 'StandardML-NJ', 'deprecated': True},
    'sugarcrm-1.1.3': {'id': 'SugarCRM-1.1.3', 'deprecated': False},
    'sun-ppp': {'id': 'Sun-PPP', 'deprecated': False},
    'sun-ppp-2000': {'id': 'Sun-PPP-2000', 'deprecated': False},
    'sunpro': {'id': 'SunPro', 'deprecated': False},
    'swl': {'id': 'SWL', 'deprecated': False},
    'swrule': {'id': 'swrule', 'deprecated': False},
    'symlinks': {'id': 'Symlinks', 'deprecated': False},
    'tapr-ohl-1.0': {'id': 'TAPR-OHL-1.0', 'deprecated': False},
    'tcl': {'id': 'TCL', 'deprecated': False},
    'tcp-wrappers': {'id': 'TCP-wrappers', 'deprecated': False},
    'termreadkey': {'id': 'TermReadKey', 'deprecated': False},
    'tgppl-1.0': {'id': 'TGPPL-1.0', 'deprecated': False},
    'threeparttable': {'id': 'threeparttable', 'deprecated': False},
    'tmate': {'id': 'TMate', 'deprecated': False},
    'torque-1.1': {'id': 'TORQUE-1.1', 'deprecated': False},
    'tosl': {'id': 'TOSL', 'deprecated': False},
    'tpdl': {'id': 'TPDL', 'deprecated': False},
    'tpl-1.0': {'id': 'TPL-1.0', 'deprecated': False},
    'ttwl': {'id': 'TTWL', 'deprecated': False},
    'ttyp0': {'id': 'TTYP0', 'deprecated': False},
    'tu-berlin-1.0': {'id': 'TU-Berlin-1.0', 'deprecated': False},
    'tu-berlin-2.0': {'id': 'TU-Berlin-2.0', 'deprecated': False},
    'ubuntu-font-1.0': {'id': 'Ubuntu-font-1.0', 'deprecated': False},
    'ucar': {'id': 'UCAR', 'deprecated': False},
    'ucl-1.0': {'id': 'UCL-1.0', 'deprecated': False},
    'ulem': {'id': 'ulem', 'deprecated': False},
    'umich-merit': {'id': 'UMich-Merit', 'deprecated': False},
    'unicode-3.0': {'id': 'Unicode-3.0', 'deprecated': False},
    'unicode-dfs-2015': {'id': 'Unicode-DFS-2015', 'deprecated': False},
    'unicode-dfs-2016': {'id': 'Unicode-DFS-2016', 'deprecated': False},
    'unicode-tou': {'id': 'Unicode-TOU', 'deprecated': False},
    'unixcrypt': {'id': 'UnixCrypt', 'deprecated': False},
    'unlicense': {'id': 'Unlicense', 'deprecated': False},
    'upl-1.0': {'id': 'UPL-1.0', 'deprecated': False},
    'urt-rle': {'id': 'URT-RLE', 'deprecated': False},
    'vim': {'id': 'Vim', 'deprecated': False},
    'vostrom': {'id': 'VOSTROM', 'deprecated': False},
    'vsl-1.0': {'id': 'VSL-1.0', 'deprecated': False},
    'w3c': {'id': 'W3C', 'deprecated': False},
    'w3c-19980720': {'id': 'W3C-19980720', 'deprecated': False},
    'w3c-20150513': {'id': 'W3C-20150513', 'deprecated': False},
    'w3m': {'id': 'w3m', 'deprecated': False},
    'watcom-1.0': {'id': 'Watcom-1.0', 'deprecated': False},
    'widget-workshop': {'id': 'Widget-Workshop', 'deprecated': False},
    'wsuipa': {'id': 'Wsuipa', 'deprecated': False},
    'wtfpl': {'id': 'WTFPL', 'deprecated': False},
    'wxwindows': {'id': 'wxWindows', 'deprecated': True},
    'x11': {'id': 'X11', 'deprecated': False},
    'x11-distribute-modifications-variant': {'id': 'X11-distribute-modifications-variant', 'deprecated': False},
    'x11-swapped': {'id': 'X11-swapped', 'deprecated': False},
    'xdebug-1.03': {'id': 'Xdebug-1.03', 'deprecated': False},
    'xerox': {'id': 'Xerox', 'deprecated': False},
    'xfig': {'id': 'Xfig', 'deprecated': False},
    'xfree86-1.1': {'id': 'XFree86-1.1', 'deprecated': False},
    'xinetd': {'id': 'xinetd', 'deprecated': False},
    'xkeyboard-config-zinoviev': {'id': 'xkeyboard-config-Zinoviev', 'deprecated': False},
    'xlock': {'id': 'xlock', 'deprecated': False},
    'xnet': {'id': 'Xnet', 'deprecated': False},
    'xpp': {'id': 'xpp', 'deprecated': False},
    'xskat': {'id': 'XSkat', 'deprecated': False},
    'xzoom': {'id': 'xzoom', 'deprecated': False},
    'ypl-1.0': {'id': 'YPL-1.0', 'deprecated': False},
    'ypl-1.1': {'id': 'YPL-1.1', 'deprecated': False},
    'zed': {'id': 'Zed', 'deprecated': False},
    'zeeff': {'id': 'Zeeff', 'deprecated': False},
    'zend-2.0': {'id': 'Zend-2.0', 'deprecated': False},
    'zimbra-1.3': {'id': 'Zimbra-1.3', 'deprecated': False},
    'zimbra-1.4': {'id': 'Zimbra-1.4', 'deprecated': False},
    'zlib': {'id': 'Zlib', 'deprecated': False},
    'zlib-acknowledgement': {'id': 'zlib-acknowledgement', 'deprecated': False},
    'zpl-1.1': {'id': 'ZPL-1.1', 'deprecated': False},
    'zpl-2.0': {'id': 'ZPL-2.0', 'deprecated': False},
    'zpl-2.1': {'id': 'ZPL-2.1', 'deprecated': False},
}

EXCEPTIONS: dict[str, SPDXException] = {
    '389-exception': {'id': '389-exception', 'deprecated': False},
    'asterisk-exception': {'id': 'Asterisk-exception', 'deprecated': False},
    'asterisk-linking-protocols-exception': {'id': 'Asterisk-linking-protocols-exception', 'deprecated': False},
    'autoconf-exception-2.0': {'id': 'Autoconf-exception-2.0', 'deprecated': False},
    'autoconf-exception-3.0': {'id': 'Autoconf-exception-3.0', 'deprecated': False},
    'autoconf-exception-generic': {'id': 'Autoconf-exception-generic', 'deprecated': False},
    'autoconf-exception-generic-3.0': {'id': 'Autoconf-exception-generic-3.0', 'deprecated': False},
    'autoconf-exception-macro': {'id': 'Autoconf-exception-macro', 'deprecated': False},
    'bison-exception-1.24': {'id': 'Bison-exception-1.24', 'deprecated': False},
    'bison-exception-2.2': {'id': 'Bison-exception-2.2', 'deprecated': False},
    'bootloader-exception': {'id': 'Bootloader-exception', 'deprecated': False},
    'classpath-exception-2.0': {'id': 'Classpath-exception-2.0', 'deprecated': False},
    'clisp-exception-2.0': {'id': 'CLISP-exception-2.0', 'deprecated': False},
    'cryptsetup-openssl-exception': {'id': 'cryptsetup-OpenSSL-exception', 'deprecated': False},
    'digirule-foss-exception': {'id': 'DigiRule-FOSS-exception', 'deprecated': False},
    'ecos-exception-2.0': {'id': 'eCos-exception-2.0', 'deprecated': False},
    'erlang-otp-linking-exception': {'id': 'erlang-otp-linking-exception', 'deprecated': False},
    'fawkes-runtime-exception': {'id': 'Fawkes-Runtime-exception', 'deprecated': False},
    'fltk-exception': {'id': 'FLTK-exception', 'deprecated': False},
    'fmt-exception': {'id': 'fmt-exception', 'deprecated': False},
    'font-exception-2.0': {'id': 'Font-exception-2.0', 'deprecated': False},
    'freertos-exception-2.0': {'id': 'freertos-exception-2.0', 'deprecated': False},
    'gcc-exception-2.0': {'id': 'GCC-exception-2.0', 'deprecated': False},
    'gcc-exception-2.0-note': {'id': 'GCC-exception-2.0-note', 'deprecated': False},
    'gcc-exception-3.1': {'id': 'GCC-exception-3.1', 'deprecated': False},
    'gmsh-exception': {'id': 'Gmsh-exception', 'deprecated': False},
    'gnat-exception': {'id': 'GNAT-exception', 'deprecated': False},
    'gnome-examples-exception': {'id': 'GNOME-examples-exception', 'deprecated': False},
    'gnu-compiler-exception': {'id': 'GNU-compiler-exception', 'deprecated': False},
    'gnu-javamail-exception': {'id': 'gnu-javamail-exception', 'deprecated': False},
    'gpl-3.0-interface-exception': {'id': 'GPL-3.0-interface-exception', 'deprecated': False},
    'gpl-3.0-linking-exception': {'id': 'GPL-3.0-linking-exception', 'deprecated': False},
    'gpl-3.0-linking-source-exception': {'id': 'GPL-3.0-linking-source-exception', 'deprecated': False},
    'gpl-cc-1.0': {'id': 'GPL-CC-1.0', 'deprecated': False},
    'gstreamer-exception-2005': {'id': 'GStreamer-exception-2005', 'deprecated': False},
    'gstreamer-exception-2008': {'id': 'GStreamer-exception-2008', 'deprecated': False},
    'i2p-gpl-java-exception': {'id': 'i2p-gpl-java-exception', 'deprecated': False},
    'kicad-libraries-exception': {'id': 'KiCad-libraries-exception', 'deprecated': False},
    'lgpl-3.0-linking-exception': {'id': 'LGPL-3.0-linking-exception', 'deprecated': False},
    'libpri-openh323-exception': {'id': 'libpri-OpenH323-exception', 'deprecated': False},
    'libtool-exception': {'id': 'Libtool-exception', 'deprecated': False},
    'linux-syscall-note': {'id': 'Linux-syscall-note', 'deprecated': False},
    'llgpl': {'id': 'LLGPL', 'deprecated': False},
    'llvm-exception': {'id': 'LLVM-exception', 'deprecated': False},
    'lzma-exception': {'id': 'LZMA-exception', 'deprecated': False},
    'mif-exception': {'id': 'mif-exception', 'deprecated': False},
    'nokia-qt-exception-1.1': {'id': 'Nokia-Qt-exception-1.1', 'deprecated': True},
    'ocaml-lgpl-linking-exception': {'id': 'OCaml-LGPL-linking-exception', 'deprecated': False},
    'occt-exception-1.0': {'id': 'OCCT-exception-1.0', 'deprecated': False},
    'openjdk-assembly-exception-1.0': {'id': 'OpenJDK-assembly-exception-1.0', 'deprecated': False},
    'openvpn-openssl-exception': {'id': 'openvpn-openssl-exception', 'deprecated': False},
    'pcre2-exception': {'id': 'PCRE2-exception', 'deprecated': False},
    'ps-or-pdf-font-exception-20170817': {'id': 'PS-or-PDF-font-exception-20170817', 'deprecated': False},
    'qpl-1.0-inria-2004-exception': {'id': 'QPL-1.0-INRIA-2004-exception', 'deprecated': False},
    'qt-gpl-exception-1.0': {'id': 'Qt-GPL-exception-1.0', 'deprecated': False},
    'qt-lgpl-exception-1.1': {'id': 'Qt-LGPL-exception-1.1', 'deprecated': False},
    'qwt-exception-1.0': {'id': 'Qwt-exception-1.0', 'deprecated': False},
    'romic-exception': {'id': 'romic-exception', 'deprecated': False},
    'rrdtool-floss-exception-2.0': {'id': 'RRDtool-FLOSS-exception-2.0', 'deprecated': False},
    'sane-exception': {'id': 'SANE-exception', 'deprecated': False},
    'shl-2.0': {'id': 'SHL-2.0', 'deprecated': False},
    'shl-2.1': {'id': 'SHL-2.1', 'deprecated': False},
    'stunnel-exception': {'id': 'stunnel-exception', 'deprecated': False},
    'swi-exception': {'id': 'SWI-exception', 'deprecated': False},
    'swift-exception': {'id': 'Swift-exception', 'deprecated': False},
    'texinfo-exception': {'id': 'Texinfo-exception', 'deprecated': False},
    'u-boot-exception-2.0': {'id': 'u-boot-exception-2.0', 'deprecated': False},
    'ubdl-exception': {'id': 'UBDL-exception', 'deprecated': False},
    'universal-foss-exception-1.0': {'id': 'Universal-FOSS-exception-1.0', 'deprecated': False},
    'vsftpd-openssl-exception': {'id': 'vsftpd-openssl-exception', 'deprecated': False},
    'wxwindows-exception-3.1': {'id': 'WxWindows-exception-3.1', 'deprecated': False},
    'x11vnc-openssl-exception': {'id': 'x11vnc-openssl-exception', 'deprecated': False},
}