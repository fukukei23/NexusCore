
# === NexusCore/openenv\Lib\site-packages\ipykernel\kernelbase.py ===
"""Base class for a kernel that talks to frontends over 0MQ."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import itertools
import logging
import os
import socket
import sys
import threading
import time
import typing as t
import uuid
import warnings
from datetime import datetime
from functools import partial
from signal import SIGINT, SIGTERM, Signals, default_int_handler, signal

from .control import CONTROL_THREAD_NAME

if sys.platform != "win32":
    from signal import SIGKILL
else:
    SIGKILL = "windown-SIGKILL-sentinel"


try:
    # jupyter_client >= 5, use tz-aware now
    from jupyter_client.session import utcnow as now
except ImportError:
    # jupyter_client < 5, use local now()
    now = datetime.now

import psutil
import zmq
from IPython.core.error import StdinNotImplementedError
from jupyter_client.session import Session
from tornado import ioloop
from tornado.queues import Queue, QueueEmpty
from traitlets.config.configurable import SingletonConfigurable
from traitlets.traitlets import (
    Any,
    Bool,
    Dict,
    Float,
    Instance,
    Integer,
    List,
    Set,
    Unicode,
    default,
    observe,
)
from zmq.eventloop.zmqstream import ZMQStream

from ipykernel.jsonutil import json_clean

from ._version import kernel_protocol_version
from .iostream import OutStream


def _accepts_parameters(meth, param_names):
    parameters = inspect.signature(meth).parameters
    accepts = {param: False for param in param_names}

    for param in param_names:
        param_spec = parameters.get(param)
        accepts[param] = (
            param_spec
            and param_spec.kind in [param_spec.KEYWORD_ONLY, param_spec.POSITIONAL_OR_KEYWORD]
        ) or any(p.kind == p.VAR_KEYWORD for p in parameters.values())

    return accepts


class Kernel(SingletonConfigurable):
    """The base kernel class."""

    # ---------------------------------------------------------------------------
    # Kernel interface
    # ---------------------------------------------------------------------------

    # attribute to override with a GUI
    eventloop = Any(None)

    processes: dict[str, psutil.Process] = {}

    @observe("eventloop")
    def _update_eventloop(self, change):
        """schedule call to eventloop from IOLoop"""
        loop = ioloop.IOLoop.current()
        if change.new is not None:
            loop.add_callback(self.enter_eventloop)

    session = Instance(Session, allow_none=True)
    profile_dir = Instance("IPython.core.profiledir.ProfileDir", allow_none=True)
    shell_stream = Instance(ZMQStream, allow_none=True)

    shell_streams: List[t.Any] = List(
        help="""Deprecated shell_streams alias. Use shell_stream

        .. versionchanged:: 6.0
            shell_streams is deprecated. Use shell_stream.
        """
    )

    implementation: str
    implementation_version: str
    banner: str

    @default("shell_streams")
    def _shell_streams_default(self):  # pragma: no cover
        warnings.warn(
            "Kernel.shell_streams is deprecated in ipykernel 6.0. Use Kernel.shell_stream",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.shell_stream is not None:
            return [self.shell_stream]
        return []

    @observe("shell_streams")
    def _shell_streams_changed(self, change):  # pragma: no cover
        warnings.warn(
            "Kernel.shell_streams is deprecated in ipykernel 6.0. Use Kernel.shell_stream",
            DeprecationWarning,
            stacklevel=2,
        )
        if len(change.new) > 1:
            warnings.warn(
                "Kernel only supports one shell stream. Additional streams will be ignored.",
                RuntimeWarning,
                stacklevel=2,
            )
        if change.new:
            self.shell_stream = change.new[0]

    control_stream = Instance(ZMQStream, allow_none=True)

    debug_shell_socket = Any()

    control_thread = Any()
    iopub_socket = Any()
    iopub_thread = Any()
    stdin_socket = Any()
    log: logging.Logger = Instance(logging.Logger, allow_none=True)  # type:ignore[assignment]

    # identities:
    int_id = Integer(-1)
    ident = Unicode()

    @default("ident")
    def _default_ident(self):
        return str(uuid.uuid4())

    # This should be overridden by wrapper kernels that implement any real
    # language.
    language_info: dict[str, object] = {}

    # any links that should go in the help menu
    help_links: List[dict[str, str]] = List()

    # Experimental option to break in non-user code.
    # The ipykernel source is in the call stack, so the user
    # has to manipulate the step-over and step-into in a wize way.
    debug_just_my_code = Bool(
        True,
        help="""Set to False if you want to debug python standard and dependent libraries.
        """,
    ).tag(config=True)

    # track associations with current request
    # Private interface

    _darwin_app_nap = Bool(
        True,
        help="""Whether to use appnope for compatibility with OS X App Nap.

        Only affects OS X >= 10.9.
        """,
    ).tag(config=True)

    # track associations with current request
    _allow_stdin = Bool(False)
    _parents: Dict[str, t.Any] = Dict({"shell": {}, "control": {}})
    _parent_ident = Dict({"shell": b"", "control": b""})

    @property
    def _parent_header(self):
        warnings.warn(
            "Kernel._parent_header is deprecated in ipykernel 6. Use .get_parent()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_parent()

    # Time to sleep after flushing the stdout/err buffers in each execute
    # cycle.  While this introduces a hard limit on the minimal latency of the
    # execute cycle, it helps prevent output synchronization problems for
    # clients.
    # Units are in seconds.  The minimum zmq latency on local host is probably
    # ~150 microseconds, set this to 500us for now.  We may need to increase it
    # a little if it's not enough after more interactive testing.
    _execute_sleep = Float(0.0005).tag(config=True)

    # Frequency of the kernel's event loop.
    # Units are in seconds, kernel subclasses for GUI toolkits may need to
    # adapt to milliseconds.
    _poll_interval = Float(0.01).tag(config=True)

    stop_on_error_timeout = Float(
        0.0,
        config=True,
        help="""time (in seconds) to wait for messages to arrive
        when aborting queued requests after an error.

        Requests that arrive within this window after an error
        will be cancelled.

        Increase in the event of unusually slow network
        causing significant delays,
        which can manifest as e.g. "Run all" in a notebook
        aborting some, but not all, messages after an error.
        """,
    )

    # If the shutdown was requested over the network, we leave here the
    # necessary reply message so it can be sent by our registered atexit
    # handler.  This ensures that the reply is only sent to clients truly at
    # the end of our shutdown process (which happens after the underlying
    # IPython shell's own shutdown).
    _shutdown_message = None

    # This is a dict of port number that the kernel is listening on. It is set
    # by record_ports and used by connect_request.
    _recorded_ports = Dict()

    # set of aborted msg_ids
    aborted = Set()

    # Track execution count here. For IPython, we override this to use the
    # execution count we store in the shell.
    execution_count = 0

    msg_types = [
        "execute_request",
        "complete_request",
        "inspect_request",
        "history_request",
        "comm_info_request",
        "kernel_info_request",
        "connect_request",
        "shutdown_request",
        "is_complete_request",
        "interrupt_request",
        # deprecated:
        "apply_request",
    ]
    # add deprecated ipyparallel control messages
    control_msg_types = [
        *msg_types,
        "clear_request",
        "abort_request",
        "debug_request",
        "usage_request",
    ]

    def __init__(self, **kwargs):
        """Initialize the kernel."""
        super().__init__(**kwargs)

        # Kernel application may swap stdout and stderr to OutStream,
        # which is the case in `IPKernelApp.init_io`, hence `sys.stdout`
        # can already by different from TextIO at initialization time.
        self._stdout: OutStream | t.TextIO = sys.stdout
        self._stderr: OutStream | t.TextIO = sys.stderr

        # Build dict of handlers for message types
        self.shell_handlers = {}
        for msg_type in self.msg_types:
            self.shell_handlers[msg_type] = getattr(self, msg_type)

        self.control_handlers = {}
        for msg_type in self.control_msg_types:
            self.control_handlers[msg_type] = getattr(self, msg_type)

        self.control_queue: Queue[t.Any] = Queue()

        # Storing the accepted parameters for do_execute, used in execute_request
        self._do_exec_accepted_params = _accepts_parameters(
            self.do_execute, ["cell_meta", "cell_id"]
        )

    def dispatch_control(self, msg):
        self.control_queue.put_nowait(msg)

    async def poll_control_queue(self):
        while True:
            msg = await self.control_queue.get()
            # handle tracers from _flush_control_queue
            if isinstance(msg, (concurrent.futures.Future, asyncio.Future)):
                msg.set_result(None)
                continue
            await self.process_control(msg)

    async def _flush_control_queue(self):
        """Flush the control queue, wait for processing of any pending messages"""
        tracer_future: concurrent.futures.Future[object] | asyncio.Future[object]
        if self.control_thread:
            control_loop = self.control_thread.io_loop
            # concurrent.futures.Futures are threadsafe
            # and can be used to await across threads
            tracer_future = concurrent.futures.Future()
            awaitable_future = asyncio.wrap_future(tracer_future)
        else:
            control_loop = self.io_loop
            tracer_future = awaitable_future = asyncio.Future()

        def _flush():
            # control_stream.flush puts messages on the queue
            if self.control_stream:
                self.control_stream.flush()
            # put Future on the queue after all of those,
            # so we can wait for all queued messages to be processed
            self.control_queue.put(tracer_future)

        control_loop.add_callback(_flush)
        return awaitable_future

    async def process_control(self, msg):
        """dispatch control requests"""
        if not self.session:
            return
        idents, msg = self.session.feed_identities(msg, copy=False)
        try:
            msg = self.session.deserialize(msg, content=True, copy=False)
        except Exception:
            self.log.error("Invalid Control Message", exc_info=True)  # noqa: G201
            return

        self.log.debug("Control received: %s", msg)

        # Set the parent message for side effects.
        self.set_parent(idents, msg, channel="control")
        self._publish_status("busy", "control")

        header = msg["header"]
        msg_type = header["msg_type"]

        handler = self.control_handlers.get(msg_type, None)
        if handler is None:
            self.log.error("UNKNOWN CONTROL MESSAGE TYPE: %r", msg_type)
        else:
            try:
                result = handler(self.control_stream, idents, msg)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self.log.error("Exception in control handler:", exc_info=True)  # noqa: G201

        sys.stdout.flush()
        sys.stderr.flush()
        self._publish_status("idle", "control")
        # flush to ensure reply is sent
        if self.control_stream:
            self.control_stream.flush(zmq.POLLOUT)

    def should_handle(self, stream, msg, idents):
        """Check whether a shell-channel message should be handled

        Allows subclasses to prevent handling of certain messages (e.g. aborted requests).
        """
        msg_id = msg["header"]["msg_id"]
        if msg_id in self.aborted:
            # is it safe to assume a msg_id will not be resubmitted?
            self.aborted.remove(msg_id)
            self._send_abort_reply(stream, msg, idents)
            return False
        return True

    async def dispatch_shell(self, msg):
        """dispatch shell requests"""
        if not self.session:
            return
        # flush control queue before handling shell requests
        await self._flush_control_queue()

        idents, msg = self.session.feed_identities(msg, copy=False)
        try:
            msg = self.session.deserialize(msg, content=True, copy=False)
        except Exception:
            self.log.error("Invalid Message", exc_info=True)  # noqa: G201
            return

        # Set the parent message for side effects.
        self.set_parent(idents, msg, channel="shell")
        self._publish_status("busy", "shell")

        msg_type = msg["header"]["msg_type"]

        # Only abort execute requests
        if self._aborting and msg_type == "execute_request":
            self._send_abort_reply(self.shell_stream, msg, idents)
            self._publish_status("idle", "shell")
            # flush to ensure reply is sent before
            # handling the next request
            if self.shell_stream:
                self.shell_stream.flush(zmq.POLLOUT)
            return

        # Print some info about this message and leave a '--->' marker, so it's
        # easier to trace visually the message chain when debugging.  Each
        # handler prints its message at the end.
        self.log.debug("\n*** MESSAGE TYPE:%s***", msg_type)
        self.log.debug("   Content: %s\n   --->\n   ", msg["content"])

        if not self.should_handle(self.shell_stream, msg, idents):
            return

        handler = self.shell_handlers.get(msg_type, None)
        if handler is None:
            self.log.warning("Unknown message type: %r", msg_type)
        else:
            self.log.debug("%s: %s", msg_type, msg)
            try:
                self.pre_handler_hook()
            except Exception:
                self.log.debug("Unable to signal in pre_handler_hook:", exc_info=True)
            try:
                result = handler(self.shell_stream, idents, msg)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self.log.error("Exception in message handler:", exc_info=True)  # noqa: G201
            except KeyboardInterrupt:
                # Ctrl-c shouldn't crash the kernel here.
                self.log.error("KeyboardInterrupt caught in kernel.")
            finally:
                try:
                    self.post_handler_hook()
                except Exception:
                    self.log.debug("Unable to signal in post_handler_hook:", exc_info=True)

        sys.stdout.flush()
        sys.stderr.flush()
        self._publish_status("idle", "shell")
        # flush to ensure reply is sent before
        # handling the next request
        if self.shell_stream:
            self.shell_stream.flush(zmq.POLLOUT)

    def pre_handler_hook(self):
        """Hook to execute before calling message handler"""
        # ensure default_int_handler during handler call
        self.saved_sigint_handler = signal(SIGINT, default_int_handler)

    def post_handler_hook(self):
        """Hook to execute after calling message handler"""
        signal(SIGINT, self.saved_sigint_handler)

    def enter_eventloop(self):
        """enter eventloop"""
        self.log.info("Entering eventloop %s", self.eventloop)
        # record handle, so we can check when this changes
        eventloop = self.eventloop
        if eventloop is None:
            self.log.info("Exiting as there is no eventloop")
            return

        async def advance_eventloop():
            # check if eventloop changed:
            if self.eventloop is not eventloop:
                self.log.info("exiting eventloop %s", eventloop)
                return
            if self.msg_queue.qsize():
                self.log.debug("Delaying eventloop due to waiting messages")
                # still messages to process, make the eventloop wait
                schedule_next()
                return
            self.log.debug("Advancing eventloop %s", eventloop)
            try:
                eventloop(self)
            except KeyboardInterrupt:
                # Ctrl-C shouldn't crash the kernel
                self.log.error("KeyboardInterrupt caught in kernel")
            if self.eventloop is eventloop:
                # schedule advance again
                schedule_next()

        def schedule_next():
            """Schedule the next advance of the eventloop"""
            # call_later allows the io_loop to process other events if needed.
            # Going through schedule_dispatch ensures all other dispatches on msg_queue
            # are processed before we enter the eventloop, even if the previous dispatch was
            # already consumed from the queue by process_one and the queue is
            # technically empty.
            self.log.debug("Scheduling eventloop advance")
            self.io_loop.call_later(0.001, partial(self.schedule_dispatch, advance_eventloop))

        # begin polling the eventloop
        schedule_next()

    async def do_one_iteration(self):
        """Process a single shell message

        Any pending control messages will be flushed as well

        .. versionchanged:: 5
            This is now a coroutine
        """
        # flush messages off of shell stream into the message queue
        if self.shell_stream:
            self.shell_stream.flush()
        # process at most one shell message per iteration
        await self.process_one(wait=False)

    async def process_one(self, wait=True):
        """Process one request

        Returns None if no message was handled.
        """
        if wait:
            t, dispatch, args = await self.msg_queue.get()
        else:
            try:
                t, dispatch, args = self.msg_queue.get_nowait()
            except (asyncio.QueueEmpty, QueueEmpty):
                return
        await dispatch(*args)

    async def dispatch_queue(self):
        """Coroutine to preserve order of message handling

        Ensures that only one message is processing at a time,
        even when the handler is async
        """

        while True:
            try:
                await self.process_one()
            except Exception:
                self.log.exception("Error in message handler")

    _message_counter = Any(
        help="""Monotonic counter of messages
        """,
    )

    @default("_message_counter")
    def _message_counter_default(self):
        return itertools.count()

    def schedule_dispatch(self, dispatch, *args):
        """schedule a message for dispatch"""
        idx = next(self._message_counter)

        self.msg_queue.put_nowait(
            (
                idx,
                dispatch,
                args,
            )
        )
        # ensure the eventloop wakes up
        self.io_loop.add_callback(lambda: None)

    def start(self):
        """register dispatchers for streams"""
        self.io_loop = ioloop.IOLoop.current()
        self.msg_queue: Queue[t.Any] = Queue()
        self.io_loop.add_callback(self.dispatch_queue)

        if self.control_stream:
            self.control_stream.on_recv(self.dispatch_control, copy=False)

        control_loop = self.control_thread.io_loop if self.control_thread else self.io_loop

        asyncio.run_coroutine_threadsafe(self.poll_control_queue(), control_loop.asyncio_loop)
        if self.shell_stream:
            self.shell_stream.on_recv(
                partial(
                    self.schedule_dispatch,
                    self.dispatch_shell,
                ),
                copy=False,
            )

        # publish idle status
        self._publish_status("starting", "shell")

    def record_ports(self, ports):
        """Record the ports that this kernel is using.

        The creator of the Kernel instance must call this methods if they
        want the :meth:`connect_request` method to return the port numbers.
        """
        self._recorded_ports = ports

    # ---------------------------------------------------------------------------
    # Kernel request handlers
    # ---------------------------------------------------------------------------

    def _publish_execute_input(self, code, parent, execution_count):
        """Publish the code request on the iopub stream."""
        if not self.session:
            return
        self.session.send(
            self.iopub_socket,
            "execute_input",
            {"code": code, "execution_count": execution_count},
            parent=parent,
            ident=self._topic("execute_input"),
        )

    def _publish_status(self, status, channel, parent=None):
        """send status (busy/idle) on IOPub"""
        if not self.session:
            return
        self.session.send(
            self.iopub_socket,
            "status",
            {"execution_state": status},
            parent=parent or self.get_parent(channel),
            ident=self._topic("status"),
        )

    def _publish_debug_event(self, event):
        if not self.session:
            return
        self.session.send(
            self.iopub_socket,
            "debug_event",
            event,
            parent=self.get_parent(),
            ident=self._topic("debug_event"),
        )

    def set_parent(self, ident, parent, channel="shell"):
        """Set the current parent request

        Side effects (IOPub messages) and replies are associated with
        the request that caused them via the parent_header.

        The parent identity is used to route input_request messages
        on the stdin channel.
        """
        self._parent_ident[channel] = ident
        self._parents[channel] = parent

    def get_parent(self, channel=None):
        """Get the parent request associated with a channel.

        .. versionadded:: 6

        Parameters
        ----------
        channel : str
            the name of the channel ('shell' or 'control')

        Returns
        -------
        message : dict
            the parent message for the most recent request on the channel.
        """

        if channel is None:
            # If a channel is not specified, get information from current thread
            if threading.current_thread().name == CONTROL_THREAD_NAME:
                channel = "control"
            else:
                channel = "shell"

        return self._parents.get(channel, {})

    def send_response(
        self,
        stream,
        msg_or_type,
        content=None,
        ident=None,
        buffers=None,
        track=False,
        header=None,
        metadata=None,
        channel=None,
    ):
        """Send a response to the message we're currently processing.

        This accepts all the parameters of :meth:`jupyter_client.session.Session.send`
        except ``parent``.

        This relies on :meth:`set_parent` having been called for the current
        message.
        """
        if not self.session:
            return None
        return self.session.send(
            stream,
            msg_or_type,
            content,
            self.get_parent(channel),
            ident,
            buffers,
            track,
            header,
            metadata,
        )

    def init_metadata(self, parent):
        """Initialize metadata.

        Run at the beginning of execution requests.
        """
        # FIXME: `started` is part of ipyparallel
        # Remove for ipykernel 5.0
        return {
            "started": now(),
        }

    def finish_metadata(self, parent, metadata, reply_content):
        """Finish populating metadata.

        Run after completing an execution request.
        """
        return metadata

    async def execute_request(self, stream, ident, parent):
        """handle an execute_request"""
        if not self.session:
            return
        try:
            content = parent["content"]
            code = content["code"]
            silent = content.get("silent", False)
            store_history = content.get("store_history", not silent)
            user_expressions = content.get("user_expressions", {})
            allow_stdin = content.get("allow_stdin", False)
            cell_meta = parent.get("metadata", {})
            cell_id = cell_meta.get("cellId")
        except Exception:
            self.log.error("Got bad msg: ")
            self.log.error("%s", parent)
            return

        stop_on_error = content.get("stop_on_error", True)

        metadata = self.init_metadata(parent)

        # Re-broadcast our input for the benefit of listening clients, and
        # start computing output
        if not silent:
            self.execution_count += 1
            self._publish_execute_input(code, parent, self.execution_count)

        # Arguments based on the do_execute signature
        do_execute_args = {
            "code": code,
            "silent": silent,
            "store_history": store_history,
            "user_expressions": user_expressions,
            "allow_stdin": allow_stdin,
        }

        if self._do_exec_accepted_params["cell_meta"]:
            do_execute_args["cell_meta"] = cell_meta
        if self._do_exec_accepted_params["cell_id"]:
            do_execute_args["cell_id"] = cell_id

        # Call do_execute with the appropriate arguments
        reply_content = self.do_execute(**do_execute_args)

        if inspect.isawaitable(reply_content):
            reply_content = await reply_content

        # Flush output before sending the reply.
        sys.stdout.flush()
        sys.stderr.flush()
        # FIXME: on rare occasions, the flush doesn't seem to make it to the
        # clients... This seems to mitigate the problem, but we definitely need
        # to better understand what's going on.
        if self._execute_sleep:
            time.sleep(self._execute_sleep)

        # Send the reply.
        reply_content = json_clean(reply_content)
        metadata = self.finish_metadata(parent, metadata, reply_content)

        reply_msg: dict[str, t.Any] = self.session.send(  # type:ignore[assignment]
            stream,
            "execute_reply",
            reply_content,
            parent,
            metadata=metadata,
            ident=ident,
        )

        self.log.debug("%s", reply_msg)

        if not silent and reply_msg["content"]["status"] == "error" and stop_on_error:
            self._abort_queues()

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
        *,
        cell_meta=None,
        cell_id=None,
    ):
        """Execute user code. Must be overridden by subclasses."""
        raise NotImplementedError

    async def complete_request(self, stream, ident, parent):
        """Handle a completion request."""
        if not self.session:
            return
        content = parent["content"]
        code = content["code"]
        cursor_pos = content["cursor_pos"]

        matches = self.do_complete(code, cursor_pos)
        if inspect.isawaitable(matches):
            matches = await matches

        matches = json_clean(matches)
        self.session.send(stream, "complete_reply", matches, parent, ident)

    def do_complete(self, code, cursor_pos):
        """Override in subclasses to find completions."""
        return {
            "matches": [],
            "cursor_end": cursor_pos,
            "cursor_start": cursor_pos,
            "metadata": {},
            "status": "ok",
        }

    async def inspect_request(self, stream, ident, parent):
        """Handle an inspect request."""
        if not self.session:
            return
        content = parent["content"]

        reply_content = self.do_inspect(
            content["code"],
            content["cursor_pos"],
            content.get("detail_level", 0),
            set(content.get("omit_sections", [])),
        )
        if inspect.isawaitable(reply_content):
            reply_content = await reply_content

        # Before we send this object over, we scrub it for JSON usage
        reply_content = json_clean(reply_content)
        msg = self.session.send(stream, "inspect_reply", reply_content, parent, ident)
        self.log.debug("%s", msg)

    def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=()):
        """Override in subclasses to allow introspection."""
        return {"status": "ok", "data": {}, "metadata": {}, "found": False}

    async def history_request(self, stream, ident, parent):
        """Handle a history request."""
        if not self.session:
            return
        content = parent["content"]

        reply_content = self.do_history(**content)
        if inspect.isawaitable(reply_content):
            reply_content = await reply_content

        reply_content = json_clean(reply_content)
        msg = self.session.send(stream, "history_reply", reply_content, parent, ident)
        self.log.debug("%s", msg)

    def do_history(
        self,
        hist_access_type,
        output,
        raw,
        session=None,
        start=None,
        stop=None,
        n=None,
        pattern=None,
        unique=False,
    ):
        """Override in subclasses to access history."""
        return {"status": "ok", "history": []}

    async def connect_request(self, stream, ident, parent):
        """Handle a connect request."""
        if not self.session:
            return
        content = self._recorded_ports.copy() if self._recorded_ports else {}
        content["status"] = "ok"
        msg = self.session.send(stream, "connect_reply", content, parent, ident)
        self.log.debug("%s", msg)

    @property
    def kernel_info(self):
        return {
            "protocol_version": kernel_protocol_version,
            "implementation": self.implementation,
            "implementation_version": self.implementation_version,
            "language_info": self.language_info,
            "banner": self.banner,
            "help_links": self.help_links,
        }

    async def kernel_info_request(self, stream, ident, parent):
        """Handle a kernel info request."""
        if not self.session:
            return
        content = {"status": "ok"}
        content.update(self.kernel_info)
        msg = self.session.send(stream, "kernel_info_reply", content, parent, ident)
        self.log.debug("%s", msg)

    async def comm_info_request(self, stream, ident, parent):
        """Handle a comm info request."""
        if not self.session:
            return
        content = parent["content"]
        target_name = content.get("target_name", None)

        # Should this be moved to ipkernel?
        if hasattr(self, "comm_manager"):
            comms = {
                k: dict(target_name=v.target_name)
                for (k, v) in self.comm_manager.comms.items()
                if v.target_name == target_name or target_name is None
            }
        else:
            comms = {}
        reply_content = dict(comms=comms, status="ok")
        msg = self.session.send(stream, "comm_info_reply", reply_content, parent, ident)
        self.log.debug("%s", msg)

    def _send_interrupt_children(self):
        if os.name == "nt":
            self.log.error("Interrupt message not supported on Windows")
        else:
            pid = os.getpid()
            pgid = os.getpgid(pid)
            # Prefer process-group over process
            # but only if the kernel is the leader of the process group
            if pgid and pgid == pid and hasattr(os, "killpg"):
                try:
                    os.killpg(pgid, SIGINT)
                except OSError:
                    os.kill(pid, SIGINT)
                    raise
            else:
                os.kill(pid, SIGINT)

    async def interrupt_request(self, stream, ident, parent):
        """Handle an interrupt request."""
        if not self.session:
            return
        content: dict[str, t.Any] = {"status": "ok"}
        try:
            self._send_interrupt_children()
        except OSError as err:
            import traceback

            content = {
                "status": "error",
                "traceback": traceback.format_stack(),
                "ename": str(type(err).__name__),
                "evalue": str(err),
            }

        self.session.send(stream, "interrupt_reply", content, parent, ident=ident)
        return

    async def shutdown_request(self, stream, ident, parent):
        """Handle a shutdown request."""
        if not self.session:
            return
        content = self.do_shutdown(parent["content"]["restart"])
        if inspect.isawaitable(content):
            content = await content
        self.session.send(stream, "shutdown_reply", content, parent, ident=ident)
        # same content, but different msg_id for broadcasting on IOPub
        self._shutdown_message = self.session.msg("shutdown_reply", content, parent)

        await self._at_shutdown()

        self.log.debug("Stopping control ioloop")
        if self.control_stream:
            control_io_loop = self.control_stream.io_loop
            control_io_loop.add_callback(control_io_loop.stop)

        self.log.debug("Stopping shell ioloop")
        if self.shell_stream:
            shell_io_loop = self.shell_stream.io_loop
            shell_io_loop.add_callback(shell_io_loop.stop)

    def do_shutdown(self, restart):
        """Override in subclasses to do things when the frontend shuts down the
        kernel.
        """
        return {"status": "ok", "restart": restart}

    async def is_complete_request(self, stream, ident, parent):
        """Handle an is_complete request."""
        if not self.session:
            return
        content = parent["content"]
        code = content["code"]

        reply_content = self.do_is_complete(code)
        if inspect.isawaitable(reply_content):
            reply_content = await reply_content
        reply_content = json_clean(reply_content)
        reply_msg = self.session.send(stream, "is_complete_reply", reply_content, parent, ident)
        self.log.debug("%s", reply_msg)

    def do_is_complete(self, code):
        """Override in subclasses to find completions."""
        return {"status": "unknown"}

    async def debug_request(self, stream, ident, parent):
        """Handle a debug request."""
        if not self.session:
            return
        content = parent["content"]
        reply_content = self.do_debug_request(content)
        if inspect.isawaitable(reply_content):
            reply_content = await reply_content
        reply_content = json_clean(reply_content)
        reply_msg = self.session.send(stream, "debug_reply", reply_content, parent, ident)
        self.log.debug("%s", reply_msg)

    def get_process_metric_value(self, process, name, attribute=None):
        """Get the process metric value."""
        try:
            metric_value = getattr(process, name)()
            if attribute is not None:  # ... a named tuple
                return getattr(metric_value, attribute)
            # ... or a number
            return metric_value
        # Avoid littering logs with stack traces
        # complaining about dead processes
        except BaseException:
            return 0

    async def usage_request(self, stream, ident, parent):
        """Handle a usage request."""
        if not self.session:
            return
        reply_content = {"hostname": socket.gethostname(), "pid": os.getpid()}
        current_process = psutil.Process()
        all_processes = [current_process, *current_process.children(recursive=True)]
        # Ensure 1) self.processes is updated to only current subprocesses
        # and 2) we reuse processes when possible (needed for accurate CPU)
        self.processes = {
            process.pid: self.processes.get(process.pid, process)  # type:ignore[misc,call-overload]
            for process in all_processes
        }
        reply_content["kernel_cpu"] = sum(
            [
                self.get_process_metric_value(process, "cpu_percent", None)
                for process in self.processes.values()
            ]
        )
        mem_info_type = "pss" if hasattr(current_process.memory_full_info(), "pss") else "rss"
        reply_content["kernel_memory"] = sum(
            [
                self.get_process_metric_value(process, "memory_full_info", mem_info_type)
                for process in self.processes.values()
            ]
        )
        cpu_percent = psutil.cpu_percent()
        # https://psutil.readthedocs.io/en/latest/index.html?highlight=cpu#psutil.cpu_percent
        # The first time cpu_percent is called it will return a meaningless 0.0 value which you are supposed to ignore.
        if cpu_percent is not None and cpu_percent != 0.0:  # type:ignore[redundant-expr]
            reply_content["host_cpu_percent"] = cpu_percent
        reply_content["cpu_count"] = psutil.cpu_count(logical=True)
        reply_content["host_virtual_memory"] = dict(psutil.virtual_memory()._asdict())
        reply_msg = self.session.send(stream, "usage_reply", reply_content, parent, ident)
        self.log.debug("%s", reply_msg)

    async def do_debug_request(self, msg):
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Engine methods (DEPRECATED)
    # ---------------------------------------------------------------------------

    async def apply_request(self, stream, ident, parent):  # pragma: no cover
        """Handle an apply request."""
        self.log.warning("apply_request is deprecated in kernel_base, moving to ipyparallel.")
        try:
            content = parent["content"]
            bufs = parent["buffers"]
            msg_id = parent["header"]["msg_id"]
        except Exception:
            self.log.error("Got bad msg: %s", parent, exc_info=True)  # noqa: G201
            return

        md = self.init_metadata(parent)

        reply_content, result_buf = self.do_apply(content, bufs, msg_id, md)

        # flush i/o
        sys.stdout.flush()
        sys.stderr.flush()

        md = self.finish_metadata(parent, md, reply_content)
        if not self.session:
            return
        self.session.send(
            stream,
            "apply_reply",
            reply_content,
            parent=parent,
            ident=ident,
            buffers=result_buf,
            metadata=md,
        )

    def do_apply(self, content, bufs, msg_id, reply_metadata):
        """DEPRECATED"""
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Control messages (DEPRECATED)
    # ---------------------------------------------------------------------------

    async def abort_request(self, stream, ident, parent):  # pragma: no cover
        """abort a specific msg by id"""
        self.log.warning(
            "abort_request is deprecated in kernel_base. It is only part of IPython parallel"
        )
        msg_ids = parent["content"].get("msg_ids", None)
        if isinstance(msg_ids, str):
            msg_ids = [msg_ids]
        if not msg_ids:
            self._abort_queues()
        for mid in msg_ids:
            self.aborted.add(str(mid))

        content = dict(status="ok")
        if not self.session:
            return
        reply_msg = self.session.send(
            stream, "abort_reply", content=content, parent=parent, ident=ident
        )
        self.log.debug("%s", reply_msg)

    async def clear_request(self, stream, idents, parent):  # pragma: no cover
        """Clear our namespace."""
        self.log.warning(
            "clear_request is deprecated in kernel_base. It is only part of IPython parallel"
        )
        content = self.do_clear()
        if self.session:
            self.session.send(stream, "clear_reply", ident=idents, parent=parent, content=content)

    def do_clear(self):
        """DEPRECATED since 4.0.3"""
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Protected interface
    # ---------------------------------------------------------------------------

    def _topic(self, topic):
        """prefixed topic for IOPub messages"""
        base = "kernel.%s" % self.ident

        return (f"{base}.{topic}").encode()

    _aborting = Bool(False)

    def _abort_queues(self):
        # while this flag is true,
        # execute requests will be aborted
        self._aborting = True
        self.log.info("Aborting queue")

        # flush streams, so all currently waiting messages
        # are added to the queue
        if self.shell_stream:
            self.shell_stream.flush()

        # Callback to signal that we are done aborting
        # dispatch functions _must_ be async
        async def stop_aborting():
            self.log.info("Finishing abort")
            self._aborting = False

        # put the stop-aborting event on the message queue
        # so that all messages already waiting in the queue are aborted
        # before we reset the flag
        schedule_stop_aborting = partial(self.schedule_dispatch, stop_aborting)

        if self.stop_on_error_timeout:
            # if we have a delay, give messages this long to arrive on the queue
            # before we stop aborting requests
            self.io_loop.call_later(self.stop_on_error_timeout, schedule_stop_aborting)
            # If we have an eventloop, it may interfere with the call_later above.
            # If the loop has a _schedule_exit method, we call that so the loop exits
            # after stop_on_error_timeout, returning to the main io_loop and letting
            # the call_later fire.
            if self.eventloop is not None and hasattr(self.eventloop, "_schedule_exit"):
                self.eventloop._schedule_exit(self.stop_on_error_timeout + 0.01)
        else:
            schedule_stop_aborting()

    def _send_abort_reply(self, stream, msg, idents):
        """Send a reply to an aborted request"""
        if not self.session:
            return
        self.log.info("Aborting %s: %s", msg["header"]["msg_id"], msg["header"]["msg_type"])
        reply_type = msg["header"]["msg_type"].rsplit("_", 1)[0] + "_reply"
        status = {"status": "aborted"}
        md = self.init_metadata(msg)
        md = self.finish_metadata(msg, md, status)
        md.update(status)

        self.session.send(
            stream,
            reply_type,
            metadata=md,
            content=status,
            parent=msg,
            ident=idents,
        )

    def _no_raw_input(self):
        """Raise StdinNotImplementedError if active frontend doesn't support
        stdin."""
        msg = "raw_input was called, but this frontend does not support stdin."
        raise StdinNotImplementedError(msg)

    def getpass(self, prompt="", stream=None):
        """Forward getpass to frontends

        Raises
        ------
        StdinNotImplementedError if active frontend doesn't support stdin.
        """
        if not self._allow_stdin:
            msg = "getpass was called, but this frontend does not support input requests."
            raise StdinNotImplementedError(msg)
        if stream is not None:
            import warnings

            warnings.warn(
                "The `stream` parameter of `getpass.getpass` will have no effect when using ipykernel",
                UserWarning,
                stacklevel=2,
            )
        return self._input_request(
            prompt,
            self._parent_ident["shell"],
            self.get_parent("shell"),
            password=True,
        )

    def raw_input(self, prompt=""):
        """Forward raw_input to frontends

        Raises
        ------
        StdinNotImplementedError if active frontend doesn't support stdin.
        """
        if not self._allow_stdin:
            msg = "raw_input was called, but this frontend does not support input requests."
            raise StdinNotImplementedError(msg)
        return self._input_request(
            str(prompt),
            self._parent_ident["shell"],
            self.get_parent("shell"),
            password=False,
        )

    def _input_request(self, prompt, ident, parent, password=False):
        # Flush output before making the request.
        sys.stderr.flush()
        sys.stdout.flush()

        # flush the stdin socket, to purge stale replies
        while True:
            try:
                self.stdin_socket.recv_multipart(zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    break
                raise

        # Send the input request.
        assert self.session is not None
        content = json_clean(dict(prompt=prompt, password=password))
        self.session.send(self.stdin_socket, "input_request", content, parent, ident=ident)

        # Await a response.
        while True:
            try:
                # Use polling with select() so KeyboardInterrupts can get
                # through; doing a blocking recv() means stdin reads are
                # uninterruptible on Windows. We need a timeout because
                # zmq.select() is also uninterruptible, but at least this
                # way reads get noticed immediately and KeyboardInterrupts
                # get noticed fairly quickly by human response time standards.
                rlist, _, xlist = zmq.select([self.stdin_socket], [], [self.stdin_socket], 0.01)
                if rlist or xlist:
                    ident, reply = self.session.recv(self.stdin_socket)
                    if (ident, reply) != (None, None):
                        break
            except KeyboardInterrupt:
                # re-raise KeyboardInterrupt, to truncate traceback
                msg = "Interrupted by user"
                raise KeyboardInterrupt(msg) from None
            except Exception:
                self.log.warning("Invalid Message:", exc_info=True)

        try:
            value = reply["content"]["value"]  # type:ignore[index]
        except Exception:
            self.log.error("Bad input_reply: %s", parent)
            value = ""
        if value == "\x04":
            # EOF
            raise EOFError
        return value

    def _signal_children(self, signum):
        """
        Send a signal to all our children

        Like `killpg`, but does not include the current process
        (or possible parents).
        """
        sig_rep = f"{Signals(signum)!r}"
        for p in self._process_children():
            self.log.debug("Sending %s to subprocess %s", sig_rep, p)
            try:
                if signum == SIGTERM:
                    p.terminate()
                elif signum == SIGKILL:
                    p.kill()
                else:
                    p.send_signal(signum)
            except psutil.NoSuchProcess:
                pass

    def _process_children(self):
        """Retrieve child processes in the kernel's process group

        Avoids:
        - including parents and self with killpg
        - including all children that may have forked-off a new group
        """
        kernel_process = psutil.Process()
        all_children = kernel_process.children(recursive=True)
        if os.name == "nt":
            return all_children
        kernel_pgid = os.getpgrp()
        process_group_children = []
        for child in all_children:
            try:
                child_pgid = os.getpgid(child.pid)
            except OSError:
                pass
            else:
                if child_pgid == kernel_pgid:
                    process_group_children.append(child)
        return process_group_children

    async def _progressively_terminate_all_children(self):
        sleeps = (0.01, 0.03, 0.1, 0.3, 1, 3, 10)
        if not self._process_children():
            self.log.debug("Kernel has no children.")
            return

        for signum in (SIGTERM, SIGKILL):
            for delay in sleeps:
                children = self._process_children()
                if not children:
                    self.log.debug("No more children, continuing shutdown routine.")
                    return
                # signals only children, not current process
                self._signal_children(signum)
                self.log.debug(
                    "Will sleep %s sec before checking for children and retrying. %s",
                    delay,
                    children,
                )
                await asyncio.sleep(delay)

    async def _at_shutdown(self):
        """Actions taken at shutdown by the kernel, called by python's atexit."""
        try:
            await self._progressively_terminate_all_children()
        except Exception as e:
            self.log.exception("Exception during subprocesses termination %s", e)

        finally:
            if self._shutdown_message is not None and self.session:
                self.session.send(
                    self.iopub_socket,
                    self._shutdown_message,
                    ident=self._topic("shutdown"),
                )
                self.log.debug("%s", self._shutdown_message)
            if self.control_stream:
                self.control_stream.flush(zmq.POLLOUT)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\client.py ===
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
from google.protobuf import field_mask_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.services.permission_service import pagers
from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

from .transports.base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .transports.grpc import PermissionServiceGrpcTransport
from .transports.grpc_asyncio import PermissionServiceGrpcAsyncIOTransport
from .transports.rest import PermissionServiceRestTransport


class PermissionServiceClientMeta(type):
    """Metaclass for the PermissionService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[PermissionServiceTransport]]
    _transport_registry["grpc"] = PermissionServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = PermissionServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = PermissionServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[PermissionServiceTransport]:
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


class PermissionServiceClient(metaclass=PermissionServiceClientMeta):
    """Provides methods for managing permissions to PaLM API
    resources.
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
            PermissionServiceClient: The constructed client.
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
            PermissionServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> PermissionServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            PermissionServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def permission_path(
        tuned_model: str,
        permission: str,
    ) -> str:
        """Returns a fully-qualified permission string."""
        return "tunedModels/{tuned_model}/permissions/{permission}".format(
            tuned_model=tuned_model,
            permission=permission,
        )

    @staticmethod
    def parse_permission_path(path: str) -> Dict[str, str]:
        """Parses a permission path into its component segments."""
        m = re.match(
            r"^tunedModels/(?P<tuned_model>.+?)/permissions/(?P<permission>.+?)$", path
        )
        return m.groupdict() if m else {}

    @staticmethod
    def tuned_model_path(
        tuned_model: str,
    ) -> str:
        """Returns a fully-qualified tuned_model string."""
        return "tunedModels/{tuned_model}".format(
            tuned_model=tuned_model,
        )

    @staticmethod
    def parse_tuned_model_path(path: str) -> Dict[str, str]:
        """Parses a tuned_model path into its component segments."""
        m = re.match(r"^tunedModels/(?P<tuned_model>.+?)$", path)
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
            _default_universe = PermissionServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = PermissionServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = PermissionServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = PermissionServiceClient._DEFAULT_UNIVERSE
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

        default_universe = PermissionServiceClient._DEFAULT_UNIVERSE
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
            or PermissionServiceClient._compare_universes(
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
                str,
                PermissionServiceTransport,
                Callable[..., PermissionServiceTransport],
            ]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the permission service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,PermissionServiceTransport,Callable[..., PermissionServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the PermissionServiceTransport constructor.
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
        ) = PermissionServiceClient._read_environment_variables()
        self._client_cert_source = PermissionServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = PermissionServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, PermissionServiceTransport)
        if transport_provided:
            # transport is a PermissionServiceTransport instance.
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
            self._transport = cast(PermissionServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or PermissionServiceClient._get_api_endpoint(
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
                Type[PermissionServiceTransport],
                Callable[..., PermissionServiceTransport],
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., PermissionServiceTransport], transport)
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

    def create_permission(
        self,
        request: Optional[
            Union[permission_service.CreatePermissionRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        permission: Optional[gag_permission.Permission] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Create a permission to a specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_create_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.CreatePermissionRequest(
                    parent="parent_value",
                )

                # Make the request
                response = client.create_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.CreatePermissionRequest, dict]):
                The request object. Request to create a ``Permission``.
            parent (str):
                Required. The parent resource of the ``Permission``.
                Format: tunedModels/{tuned_model}

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            permission (google.ai.generativelanguage_v1beta3.types.Permission):
                Required. The permission to create.
                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
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
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, permission])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.CreatePermissionRequest):
            request = permission_service.CreatePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent
            if permission is not None:
                request.permission = permission

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_permission]

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

    def get_permission(
        self,
        request: Optional[Union[permission_service.GetPermissionRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission.Permission:
        r"""Gets information about a specific Permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_get_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetPermissionRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.GetPermissionRequest, dict]):
                The request object. Request for getting information about a specific
                ``Permission``.
            name (str):
                Required. The resource name of the permission.

                Format:
                ``tunedModels/{tuned_model}permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
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
        if not isinstance(request, permission_service.GetPermissionRequest):
            request = permission_service.GetPermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_permission]

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

    def list_permissions(
        self,
        request: Optional[
            Union[permission_service.ListPermissionsRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListPermissionsPager:
        r"""Lists permissions for the specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_list_permissions():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListPermissionsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_permissions(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.ListPermissionsRequest, dict]):
                The request object. Request for listing permissions.
            parent (str):
                Required. The parent resource of the permissions.
                Format: tunedModels/{tuned_model}

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.permission_service.pagers.ListPermissionsPager:
                Response from ListPermissions containing a paginated list of
                   permissions.

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
        if not isinstance(request, permission_service.ListPermissionsRequest):
            request = permission_service.ListPermissionsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_permissions]

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
        response = pagers.ListPermissionsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def update_permission(
        self,
        request: Optional[
            Union[permission_service.UpdatePermissionRequest, dict]
        ] = None,
        *,
        permission: Optional[gag_permission.Permission] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Updates the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_update_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.UpdatePermissionRequest(
                )

                # Make the request
                response = client.update_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.UpdatePermissionRequest, dict]):
                The request object. Request to update the ``Permission``.
            permission (google.ai.generativelanguage_v1beta3.types.Permission):
                Required. The permission to update.

                The permission's ``name`` field is used to identify the
                permission to update.

                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to update. Accepted ones:

                -  role (``Permission.role`` field)

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
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
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([permission, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.UpdatePermissionRequest):
            request = permission_service.UpdatePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if permission is not None:
                request.permission = permission
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_permission]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("permission.name", request.permission.name),)
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

    def delete_permission(
        self,
        request: Optional[
            Union[permission_service.DeletePermissionRequest, dict]
        ] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_delete_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.DeletePermissionRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_permission(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.DeletePermissionRequest, dict]):
                The request object. Request to delete the ``Permission``.
            name (str):
                Required. The resource name of the permission. Format:
                ``tunedModels/{tuned_model}/permissions/{permission}``

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
        if not isinstance(request, permission_service.DeletePermissionRequest):
            request = permission_service.DeletePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_permission]

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

    def transfer_ownership(
        self,
        request: Optional[
            Union[permission_service.TransferOwnershipRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission_service.TransferOwnershipResponse:
        r"""Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_transfer_ownership():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.TransferOwnershipRequest(
                    name="name_value",
                    email_address="email_address_value",
                )

                # Make the request
                response = client.transfer_ownership(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.TransferOwnershipRequest, dict]):
                The request object. Request to transfer the ownership of
                the tuned model.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TransferOwnershipResponse:
                Response from TransferOwnership.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.TransferOwnershipRequest):
            request = permission_service.TransferOwnershipRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.transfer_ownership]

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

    def __enter__(self) -> "PermissionServiceClient":
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


__all__ = ("PermissionServiceClient",)

# === NexusCore/openenv\Lib\site-packages\setuptools\config\_validate_pyproject\fastjsonschema_validations.py ===
# noqa
# ruff: noqa
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# yapf: disable
# pylama:skip=1


# *** PLEASE DO NOT MODIFY DIRECTLY: Automatically generated code *** 


VERSION = "2.20.0"
from decimal import Decimal
import re
from .fastjsonschema_exceptions import JsonSchemaValueException


REGEX_PATTERNS = {
    '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$': re.compile('^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])\\Z'),
    '^.*$': re.compile('^.*$'),
    '.+': re.compile('.+'),
    '^.+$': re.compile('^.+$'),
    'idn-email_re_pattern': re.compile('^[^@]+@[^@]+\\.[^@]+\\Z')
}

NoneType = type(None)

def validate(data, custom_formats={}, name_prefix=None):
    validate_https___packaging_python_org_en_latest_specifications_declaring_build_dependencies(data, custom_formats, (name_prefix or "data") + "")
    return data

def validate_https___packaging_python_org_en_latest_specifications_declaring_build_dependencies(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/declaring-build-dependencies/', 'title': 'Data structure for ``pyproject.toml`` files', '$$description': ['File format containing build-time configurations for the Python ecosystem. ', ':pep:`517` initially defined a build-system independent format for source trees', 'which was complemented by :pep:`518` to provide a way of specifying dependencies ', 'for building Python projects.', 'Please notice the ``project`` table (as initially defined in  :pep:`621`) is not included', 'in this schema and should be considered separately.'], 'type': 'object', 'additionalProperties': False, 'properties': {'build-system': {'type': 'object', 'description': 'Table used to store build-related data', 'additionalProperties': False, 'properties': {'requires': {'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, 'build-backend': {'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, 'backend-path': {'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}}, 'required': ['requires']}, 'project': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create command-line wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.']}, 'gui-scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create GUI wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.', 'The difference between ``scripts`` and ``gui-scripts`` is only relevant in', 'Windows.']}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$ref': '#/definitions/entry-point-group'}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$ref': '#/definitions/dependency'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$ref': '#/definitions/dependency'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}, 'tool': {'type': 'object', 'properties': {'distutils': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html', 'title': '``tool.distutils`` table', '$$description': ['**EXPERIMENTAL** (NOT OFFICIALLY SUPPORTED): Use ``tool.distutils``', 'subtables to configure arguments for ``distutils`` commands.', 'Originally, ``distutils`` allowed developers to configure arguments for', '``setup.py`` commands via `distutils configuration files', '<https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.', 'See also `the old Python docs <https://docs.python.org/3.11/install/>_`.'], 'type': 'object', 'properties': {'global': {'type': 'object', 'description': 'Global options applied to all ``distutils`` commands'}}, 'patternProperties': {'.+': {'type': 'object'}}, '$comment': 'TODO: Is there a practical way of making this schema more specific?'}, 'setuptools': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html', 'title': '``tool.setuptools`` table', '$$description': ['``setuptools``-specific configurations that can be set by users that require', 'customization.', 'These configurations are completely optional and probably can be skipped when', 'creating simple packages. They are equivalent to some of the `Keywords', '<https://setuptools.pypa.io/en/latest/references/keywords.html>`_', 'used by the ``setup.py`` file, and can be set via the ``tool.setuptools`` table.', 'It considers only ``setuptools`` `parameters', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_', 'that are not covered by :pep:`621`; and intentionally excludes ``dependency_links``', 'and ``setup_requires`` (incompatible with modern workflows/standards).'], 'type': 'object', 'additionalProperties': False, 'properties': {'platforms': {'type': 'array', 'items': {'type': 'string'}}, 'provides': {'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'obsoletes': {'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'zip-safe': {'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, 'script-files': {'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, 'eager-resources': {'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, 'packages': {'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$ref': '#/definitions/package-name'}}, {'$ref': '#/definitions/find-directive'}]}, 'package-dir': {'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$ref': '#/definitions/package-name'}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, 'package-data': {'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'include-package-data': {'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, 'exclude-package-data': {'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'namespace-packages': {'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, 'py-modules': {'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, 'ext-modules': {'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$ref': '#/definitions/ext-module'}}, 'data-files': {'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'cmdclass': {'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, 'license-files': {'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, 'dynamic': {'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'$ref': '#/definitions/attr-directive'}, {'$ref': '#/definitions/file-directive'}]}, 'classifiers': {'$ref': '#/definitions/file-directive'}, 'description': {'$ref': '#/definitions/file-directive'}, 'entry-points': {'$ref': '#/definitions/file-directive'}, 'dependencies': {'$ref': '#/definitions/file-directive-for-dependencies'}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'$ref': '#/definitions/file-directive-for-dependencies'}}}, 'readme': {'type': 'object', 'anyOf': [{'$ref': '#/definitions/file-directive'}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'$ref': '#/definitions/file-directive/properties/file'}}, 'additionalProperties': False}], 'required': ['file']}}}}, 'definitions': {'package-name': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, 'ext-module': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, 'file-directive': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'file-directive-for-dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'attr-directive': {'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, 'find-directive': {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}}}}}, 'dependency-groups': {'type': 'object', 'description': 'Dependency groups following PEP 735', 'additionalProperties': False, 'patternProperties': {'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$': {'type': 'array', 'items': {'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}}}}}, 'project': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create command-line wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.']}, 'gui-scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create GUI wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.', 'The difference between ``scripts`` and ``gui-scripts`` is only relevant in', 'Windows.']}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$ref': '#/definitions/entry-point-group'}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$ref': '#/definitions/dependency'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$ref': '#/definitions/dependency'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "build-system" in data_keys:
            data_keys.remove("build-system")
            data__buildsystem = data["build-system"]
            if not isinstance(data__buildsystem, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system must be object", value=data__buildsystem, name="" + (name_prefix or "data") + ".build-system", definition={'type': 'object', 'description': 'Table used to store build-related data', 'additionalProperties': False, 'properties': {'requires': {'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, 'build-backend': {'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, 'backend-path': {'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}}, 'required': ['requires']}, rule='type')
            data__buildsystem_is_dict = isinstance(data__buildsystem, dict)
            if data__buildsystem_is_dict:
                data__buildsystem__missing_keys = set(['requires']) - data__buildsystem.keys()
                if data__buildsystem__missing_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system must contain " + (str(sorted(data__buildsystem__missing_keys)) + " properties"), value=data__buildsystem, name="" + (name_prefix or "data") + ".build-system", definition={'type': 'object', 'description': 'Table used to store build-related data', 'additionalProperties': False, 'properties': {'requires': {'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, 'build-backend': {'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, 'backend-path': {'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}}, 'required': ['requires']}, rule='required')
                data__buildsystem_keys = set(data__buildsystem.keys())
                if "requires" in data__buildsystem_keys:
                    data__buildsystem_keys.remove("requires")
                    data__buildsystem__requires = data__buildsystem["requires"]
                    if not isinstance(data__buildsystem__requires, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.requires must be array", value=data__buildsystem__requires, name="" + (name_prefix or "data") + ".build-system.requires", definition={'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, rule='type')
                    data__buildsystem__requires_is_list = isinstance(data__buildsystem__requires, (list, tuple))
                    if data__buildsystem__requires_is_list:
                        data__buildsystem__requires_len = len(data__buildsystem__requires)
                        for data__buildsystem__requires_x, data__buildsystem__requires_item in enumerate(data__buildsystem__requires):
                            if not isinstance(data__buildsystem__requires_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.requires[{data__buildsystem__requires_x}]".format(**locals()) + " must be string", value=data__buildsystem__requires_item, name="" + (name_prefix or "data") + ".build-system.requires[{data__buildsystem__requires_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if "build-backend" in data__buildsystem_keys:
                    data__buildsystem_keys.remove("build-backend")
                    data__buildsystem__buildbackend = data__buildsystem["build-backend"]
                    if not isinstance(data__buildsystem__buildbackend, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.build-backend must be string", value=data__buildsystem__buildbackend, name="" + (name_prefix or "data") + ".build-system.build-backend", definition={'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, rule='type')
                    if isinstance(data__buildsystem__buildbackend, str):
                        if not custom_formats["pep517-backend-reference"](data__buildsystem__buildbackend):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.build-backend must be pep517-backend-reference", value=data__buildsystem__buildbackend, name="" + (name_prefix or "data") + ".build-system.build-backend", definition={'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, rule='format')
                if "backend-path" in data__buildsystem_keys:
                    data__buildsystem_keys.remove("backend-path")
                    data__buildsystem__backendpath = data__buildsystem["backend-path"]
                    if not isinstance(data__buildsystem__backendpath, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.backend-path must be array", value=data__buildsystem__backendpath, name="" + (name_prefix or "data") + ".build-system.backend-path", definition={'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}, rule='type')
                    data__buildsystem__backendpath_is_list = isinstance(data__buildsystem__backendpath, (list, tuple))
                    if data__buildsystem__backendpath_is_list:
                        data__buildsystem__backendpath_len = len(data__buildsystem__backendpath)
                        for data__buildsystem__backendpath_x, data__buildsystem__backendpath_item in enumerate(data__buildsystem__backendpath):
                            if not isinstance(data__buildsystem__backendpath_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system.backend-path[{data__buildsystem__backendpath_x}]".format(**locals()) + " must be string", value=data__buildsystem__backendpath_item, name="" + (name_prefix or "data") + ".build-system.backend-path[{data__buildsystem__backendpath_x}]".format(**locals()) + "", definition={'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}, rule='type')
                if data__buildsystem_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".build-system must not contain "+str(data__buildsystem_keys)+" properties", value=data__buildsystem, name="" + (name_prefix or "data") + ".build-system", definition={'type': 'object', 'description': 'Table used to store build-related data', 'additionalProperties': False, 'properties': {'requires': {'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, 'build-backend': {'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, 'backend-path': {'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}}, 'required': ['requires']}, rule='additionalProperties')
        if "project" in data_keys:
            data_keys.remove("project")
            data__project = data["project"]
            validate_https___packaging_python_org_en_latest_specifications_pyproject_toml(data__project, custom_formats, (name_prefix or "data") + ".project")
        if "tool" in data_keys:
            data_keys.remove("tool")
            data__tool = data["tool"]
            if not isinstance(data__tool, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".tool must be object", value=data__tool, name="" + (name_prefix or "data") + ".tool", definition={'type': 'object', 'properties': {'distutils': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html', 'title': '``tool.distutils`` table', '$$description': ['**EXPERIMENTAL** (NOT OFFICIALLY SUPPORTED): Use ``tool.distutils``', 'subtables to configure arguments for ``distutils`` commands.', 'Originally, ``distutils`` allowed developers to configure arguments for', '``setup.py`` commands via `distutils configuration files', '<https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.', 'See also `the old Python docs <https://docs.python.org/3.11/install/>_`.'], 'type': 'object', 'properties': {'global': {'type': 'object', 'description': 'Global options applied to all ``distutils`` commands'}}, 'patternProperties': {'.+': {'type': 'object'}}, '$comment': 'TODO: Is there a practical way of making this schema more specific?'}, 'setuptools': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html', 'title': '``tool.setuptools`` table', '$$description': ['``setuptools``-specific configurations that can be set by users that require', 'customization.', 'These configurations are completely optional and probably can be skipped when', 'creating simple packages. They are equivalent to some of the `Keywords', '<https://setuptools.pypa.io/en/latest/references/keywords.html>`_', 'used by the ``setup.py`` file, and can be set via the ``tool.setuptools`` table.', 'It considers only ``setuptools`` `parameters', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_', 'that are not covered by :pep:`621`; and intentionally excludes ``dependency_links``', 'and ``setup_requires`` (incompatible with modern workflows/standards).'], 'type': 'object', 'additionalProperties': False, 'properties': {'platforms': {'type': 'array', 'items': {'type': 'string'}}, 'provides': {'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'obsoletes': {'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'zip-safe': {'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, 'script-files': {'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, 'eager-resources': {'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, 'packages': {'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$ref': '#/definitions/package-name'}}, {'$ref': '#/definitions/find-directive'}]}, 'package-dir': {'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$ref': '#/definitions/package-name'}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, 'package-data': {'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'include-package-data': {'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, 'exclude-package-data': {'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'namespace-packages': {'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, 'py-modules': {'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, 'ext-modules': {'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$ref': '#/definitions/ext-module'}}, 'data-files': {'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'cmdclass': {'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, 'license-files': {'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, 'dynamic': {'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'$ref': '#/definitions/attr-directive'}, {'$ref': '#/definitions/file-directive'}]}, 'classifiers': {'$ref': '#/definitions/file-directive'}, 'description': {'$ref': '#/definitions/file-directive'}, 'entry-points': {'$ref': '#/definitions/file-directive'}, 'dependencies': {'$ref': '#/definitions/file-directive-for-dependencies'}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'$ref': '#/definitions/file-directive-for-dependencies'}}}, 'readme': {'type': 'object', 'anyOf': [{'$ref': '#/definitions/file-directive'}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'$ref': '#/definitions/file-directive/properties/file'}}, 'additionalProperties': False}], 'required': ['file']}}}}, 'definitions': {'package-name': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, 'ext-module': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, 'file-directive': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'file-directive-for-dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'attr-directive': {'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, 'find-directive': {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}}}}}, rule='type')
            data__tool_is_dict = isinstance(data__tool, dict)
            if data__tool_is_dict:
                data__tool_keys = set(data__tool.keys())
                if "distutils" in data__tool_keys:
                    data__tool_keys.remove("distutils")
                    data__tool__distutils = data__tool["distutils"]
                    validate_https___setuptools_pypa_io_en_latest_deprecated_distutils_configfile_html(data__tool__distutils, custom_formats, (name_prefix or "data") + ".tool.distutils")
                if "setuptools" in data__tool_keys:
                    data__tool_keys.remove("setuptools")
                    data__tool__setuptools = data__tool["setuptools"]
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html(data__tool__setuptools, custom_formats, (name_prefix or "data") + ".tool.setuptools")
        if "dependency-groups" in data_keys:
            data_keys.remove("dependency-groups")
            data__dependencygroups = data["dependency-groups"]
            if not isinstance(data__dependencygroups, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups must be object", value=data__dependencygroups, name="" + (name_prefix or "data") + ".dependency-groups", definition={'type': 'object', 'description': 'Dependency groups following PEP 735', 'additionalProperties': False, 'patternProperties': {'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$': {'type': 'array', 'items': {'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}}}}, rule='type')
            data__dependencygroups_is_dict = isinstance(data__dependencygroups, dict)
            if data__dependencygroups_is_dict:
                data__dependencygroups_keys = set(data__dependencygroups.keys())
                for data__dependencygroups_key, data__dependencygroups_val in data__dependencygroups.items():
                    if REGEX_PATTERNS['^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'].search(data__dependencygroups_key):
                        if data__dependencygroups_key in data__dependencygroups_keys:
                            data__dependencygroups_keys.remove(data__dependencygroups_key)
                        if not isinstance(data__dependencygroups_val, (list, tuple)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}".format(**locals()) + " must be array", value=data__dependencygroups_val, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}".format(**locals()) + "", definition={'type': 'array', 'items': {'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}}, rule='type')
                        data__dependencygroups_val_is_list = isinstance(data__dependencygroups_val, (list, tuple))
                        if data__dependencygroups_val_is_list:
                            data__dependencygroups_val_len = len(data__dependencygroups_val)
                            for data__dependencygroups_val_x, data__dependencygroups_val_item in enumerate(data__dependencygroups_val):
                                data__dependencygroups_val_item_one_of_count1 = 0
                                if data__dependencygroups_val_item_one_of_count1 < 2:
                                    try:
                                        if not isinstance(data__dependencygroups_val_item, (str)):
                                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + " must be string", value=data__dependencygroups_val_item, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + "", definition={'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, rule='type')
                                        if isinstance(data__dependencygroups_val_item, str):
                                            if not custom_formats["pep508"](data__dependencygroups_val_item):
                                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + " must be pep508", value=data__dependencygroups_val_item, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + "", definition={'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, rule='format')
                                        data__dependencygroups_val_item_one_of_count1 += 1
                                    except JsonSchemaValueException: pass
                                if data__dependencygroups_val_item_one_of_count1 < 2:
                                    try:
                                        if not isinstance(data__dependencygroups_val_item, (dict)):
                                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + " must be object", value=data__dependencygroups_val_item, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + "", definition={'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}, rule='type')
                                        data__dependencygroups_val_item_is_dict = isinstance(data__dependencygroups_val_item, dict)
                                        if data__dependencygroups_val_item_is_dict:
                                            data__dependencygroups_val_item_keys = set(data__dependencygroups_val_item.keys())
                                            if "include-group" in data__dependencygroups_val_item_keys:
                                                data__dependencygroups_val_item_keys.remove("include-group")
                                                data__dependencygroups_val_item__includegroup = data__dependencygroups_val_item["include-group"]
                                                if not isinstance(data__dependencygroups_val_item__includegroup, (str)):
                                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}].include-group".format(**locals()) + " must be string", value=data__dependencygroups_val_item__includegroup, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}].include-group".format(**locals()) + "", definition={'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}, rule='type')
                                                if isinstance(data__dependencygroups_val_item__includegroup, str):
                                                    if not REGEX_PATTERNS['^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'].search(data__dependencygroups_val_item__includegroup):
                                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}].include-group".format(**locals()) + " must match pattern ^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$", value=data__dependencygroups_val_item__includegroup, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}].include-group".format(**locals()) + "", definition={'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}, rule='pattern')
                                            if data__dependencygroups_val_item_keys:
                                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + " must not contain "+str(data__dependencygroups_val_item_keys)+" properties", value=data__dependencygroups_val_item, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + "", definition={'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}, rule='additionalProperties')
                                        data__dependencygroups_val_item_one_of_count1 += 1
                                    except JsonSchemaValueException: pass
                                if data__dependencygroups_val_item_one_of_count1 != 1:
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + " must be valid exactly by one definition" + (" (" + str(data__dependencygroups_val_item_one_of_count1) + " matches found)"), value=data__dependencygroups_val_item, name="" + (name_prefix or "data") + ".dependency-groups.{data__dependencygroups_key}[{data__dependencygroups_val_x}]".format(**locals()) + "", definition={'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}, rule='oneOf')
                if data__dependencygroups_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependency-groups must not contain "+str(data__dependencygroups_keys)+" properties", value=data__dependencygroups, name="" + (name_prefix or "data") + ".dependency-groups", definition={'type': 'object', 'description': 'Dependency groups following PEP 735', 'additionalProperties': False, 'patternProperties': {'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$': {'type': 'array', 'items': {'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}}}}, rule='additionalProperties')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/declaring-build-dependencies/', 'title': 'Data structure for ``pyproject.toml`` files', '$$description': ['File format containing build-time configurations for the Python ecosystem. ', ':pep:`517` initially defined a build-system independent format for source trees', 'which was complemented by :pep:`518` to provide a way of specifying dependencies ', 'for building Python projects.', 'Please notice the ``project`` table (as initially defined in  :pep:`621`) is not included', 'in this schema and should be considered separately.'], 'type': 'object', 'additionalProperties': False, 'properties': {'build-system': {'type': 'object', 'description': 'Table used to store build-related data', 'additionalProperties': False, 'properties': {'requires': {'type': 'array', '$$description': ['List of dependencies in the :pep:`508` format required to execute the build', 'system. Please notice that the resulting dependency graph', '**MUST NOT contain cycles**'], 'items': {'type': 'string'}}, 'build-backend': {'type': 'string', 'description': 'Python object that will be used to perform the build according to :pep:`517`', 'format': 'pep517-backend-reference'}, 'backend-path': {'type': 'array', '$$description': ['List of directories to be prepended to ``sys.path`` when loading the', 'back-end, and running its hooks'], 'items': {'type': 'string', '$comment': 'Should be a path (TODO: enforce it with format?)'}}}, 'required': ['requires']}, 'project': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create command-line wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.']}, 'gui-scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create GUI wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.', 'The difference between ``scripts`` and ``gui-scripts`` is only relevant in', 'Windows.']}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$ref': '#/definitions/entry-point-group'}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$ref': '#/definitions/dependency'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$ref': '#/definitions/dependency'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}, 'tool': {'type': 'object', 'properties': {'distutils': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html', 'title': '``tool.distutils`` table', '$$description': ['**EXPERIMENTAL** (NOT OFFICIALLY SUPPORTED): Use ``tool.distutils``', 'subtables to configure arguments for ``distutils`` commands.', 'Originally, ``distutils`` allowed developers to configure arguments for', '``setup.py`` commands via `distutils configuration files', '<https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.', 'See also `the old Python docs <https://docs.python.org/3.11/install/>_`.'], 'type': 'object', 'properties': {'global': {'type': 'object', 'description': 'Global options applied to all ``distutils`` commands'}}, 'patternProperties': {'.+': {'type': 'object'}}, '$comment': 'TODO: Is there a practical way of making this schema more specific?'}, 'setuptools': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html', 'title': '``tool.setuptools`` table', '$$description': ['``setuptools``-specific configurations that can be set by users that require', 'customization.', 'These configurations are completely optional and probably can be skipped when', 'creating simple packages. They are equivalent to some of the `Keywords', '<https://setuptools.pypa.io/en/latest/references/keywords.html>`_', 'used by the ``setup.py`` file, and can be set via the ``tool.setuptools`` table.', 'It considers only ``setuptools`` `parameters', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_', 'that are not covered by :pep:`621`; and intentionally excludes ``dependency_links``', 'and ``setup_requires`` (incompatible with modern workflows/standards).'], 'type': 'object', 'additionalProperties': False, 'properties': {'platforms': {'type': 'array', 'items': {'type': 'string'}}, 'provides': {'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'obsoletes': {'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'zip-safe': {'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, 'script-files': {'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, 'eager-resources': {'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, 'packages': {'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$ref': '#/definitions/package-name'}}, {'$ref': '#/definitions/find-directive'}]}, 'package-dir': {'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$ref': '#/definitions/package-name'}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, 'package-data': {'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'include-package-data': {'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, 'exclude-package-data': {'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'namespace-packages': {'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, 'py-modules': {'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, 'ext-modules': {'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$ref': '#/definitions/ext-module'}}, 'data-files': {'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'cmdclass': {'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, 'license-files': {'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, 'dynamic': {'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'$ref': '#/definitions/attr-directive'}, {'$ref': '#/definitions/file-directive'}]}, 'classifiers': {'$ref': '#/definitions/file-directive'}, 'description': {'$ref': '#/definitions/file-directive'}, 'entry-points': {'$ref': '#/definitions/file-directive'}, 'dependencies': {'$ref': '#/definitions/file-directive-for-dependencies'}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'$ref': '#/definitions/file-directive-for-dependencies'}}}, 'readme': {'type': 'object', 'anyOf': [{'$ref': '#/definitions/file-directive'}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'$ref': '#/definitions/file-directive/properties/file'}}, 'additionalProperties': False}], 'required': ['file']}}}}, 'definitions': {'package-name': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, 'ext-module': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, 'file-directive': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'file-directive-for-dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'attr-directive': {'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, 'find-directive': {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}}}}}, 'dependency-groups': {'type': 'object', 'description': 'Dependency groups following PEP 735', 'additionalProperties': False, 'patternProperties': {'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$': {'type': 'array', 'items': {'oneOf': [{'type': 'string', 'description': 'Python package specifiers following PEP 508', 'format': 'pep508'}, {'type': 'object', 'additionalProperties': False, 'properties': {'include-group': {'description': 'Another dependency group to include in this one', 'type': 'string', 'pattern': '^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])$'}}}]}}}}}, 'project': {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$ref': '#/definitions/author'}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create command-line wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.']}, 'gui-scripts': {'$ref': '#/definitions/entry-point-group', '$$description': ['Instruct the installer to create GUI wrappers for the given', '`entry points <https://packaging.python.org/specifications/entry-points/>`_.', 'The difference between ``scripts`` and ``gui-scripts`` is only relevant in', 'Windows.']}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$ref': '#/definitions/entry-point-group'}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$ref': '#/definitions/dependency'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$ref': '#/definitions/dependency'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html', 'title': '``tool.setuptools`` table', '$$description': ['``setuptools``-specific configurations that can be set by users that require', 'customization.', 'These configurations are completely optional and probably can be skipped when', 'creating simple packages. They are equivalent to some of the `Keywords', '<https://setuptools.pypa.io/en/latest/references/keywords.html>`_', 'used by the ``setup.py`` file, and can be set via the ``tool.setuptools`` table.', 'It considers only ``setuptools`` `parameters', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_', 'that are not covered by :pep:`621`; and intentionally excludes ``dependency_links``', 'and ``setup_requires`` (incompatible with modern workflows/standards).'], 'type': 'object', 'additionalProperties': False, 'properties': {'platforms': {'type': 'array', 'items': {'type': 'string'}}, 'provides': {'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'obsoletes': {'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'zip-safe': {'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, 'script-files': {'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, 'eager-resources': {'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, 'packages': {'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}}, {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}]}, 'package-dir': {'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, 'package-data': {'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'include-package-data': {'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, 'exclude-package-data': {'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'namespace-packages': {'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, 'py-modules': {'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, 'ext-modules': {'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}}, 'data-files': {'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'cmdclass': {'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, 'license-files': {'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, 'dynamic': {'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'classifiers': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'description': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'entry-points': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, 'readme': {'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}}}}, 'definitions': {'package-name': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, 'ext-module': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, 'file-directive': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'file-directive-for-dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'attr-directive': {'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, 'find-directive': {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "platforms" in data_keys:
            data_keys.remove("platforms")
            data__platforms = data["platforms"]
            if not isinstance(data__platforms, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".platforms must be array", value=data__platforms, name="" + (name_prefix or "data") + ".platforms", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__platforms_is_list = isinstance(data__platforms, (list, tuple))
            if data__platforms_is_list:
                data__platforms_len = len(data__platforms)
                for data__platforms_x, data__platforms_item in enumerate(data__platforms):
                    if not isinstance(data__platforms_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".platforms[{data__platforms_x}]".format(**locals()) + " must be string", value=data__platforms_item, name="" + (name_prefix or "data") + ".platforms[{data__platforms_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "provides" in data_keys:
            data_keys.remove("provides")
            data__provides = data["provides"]
            if not isinstance(data__provides, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".provides must be array", value=data__provides, name="" + (name_prefix or "data") + ".provides", definition={'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, rule='type')
            data__provides_is_list = isinstance(data__provides, (list, tuple))
            if data__provides_is_list:
                data__provides_len = len(data__provides)
                for data__provides_x, data__provides_item in enumerate(data__provides):
                    if not isinstance(data__provides_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".provides[{data__provides_x}]".format(**locals()) + " must be string", value=data__provides_item, name="" + (name_prefix or "data") + ".provides[{data__provides_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='type')
                    if isinstance(data__provides_item, str):
                        if not custom_formats["pep508-identifier"](data__provides_item):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".provides[{data__provides_x}]".format(**locals()) + " must be pep508-identifier", value=data__provides_item, name="" + (name_prefix or "data") + ".provides[{data__provides_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='format')
        if "obsoletes" in data_keys:
            data_keys.remove("obsoletes")
            data__obsoletes = data["obsoletes"]
            if not isinstance(data__obsoletes, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".obsoletes must be array", value=data__obsoletes, name="" + (name_prefix or "data") + ".obsoletes", definition={'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, rule='type')
            data__obsoletes_is_list = isinstance(data__obsoletes, (list, tuple))
            if data__obsoletes_is_list:
                data__obsoletes_len = len(data__obsoletes)
                for data__obsoletes_x, data__obsoletes_item in enumerate(data__obsoletes):
                    if not isinstance(data__obsoletes_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".obsoletes[{data__obsoletes_x}]".format(**locals()) + " must be string", value=data__obsoletes_item, name="" + (name_prefix or "data") + ".obsoletes[{data__obsoletes_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='type')
                    if isinstance(data__obsoletes_item, str):
                        if not custom_formats["pep508-identifier"](data__obsoletes_item):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".obsoletes[{data__obsoletes_x}]".format(**locals()) + " must be pep508-identifier", value=data__obsoletes_item, name="" + (name_prefix or "data") + ".obsoletes[{data__obsoletes_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='format')
        if "zip-safe" in data_keys:
            data_keys.remove("zip-safe")
            data__zipsafe = data["zip-safe"]
            if not isinstance(data__zipsafe, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".zip-safe must be boolean", value=data__zipsafe, name="" + (name_prefix or "data") + ".zip-safe", definition={'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, rule='type')
        if "script-files" in data_keys:
            data_keys.remove("script-files")
            data__scriptfiles = data["script-files"]
            if not isinstance(data__scriptfiles, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".script-files must be array", value=data__scriptfiles, name="" + (name_prefix or "data") + ".script-files", definition={'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, rule='type')
            data__scriptfiles_is_list = isinstance(data__scriptfiles, (list, tuple))
            if data__scriptfiles_is_list:
                data__scriptfiles_len = len(data__scriptfiles)
                for data__scriptfiles_x, data__scriptfiles_item in enumerate(data__scriptfiles):
                    if not isinstance(data__scriptfiles_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".script-files[{data__scriptfiles_x}]".format(**locals()) + " must be string", value=data__scriptfiles_item, name="" + (name_prefix or "data") + ".script-files[{data__scriptfiles_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "eager-resources" in data_keys:
            data_keys.remove("eager-resources")
            data__eagerresources = data["eager-resources"]
            if not isinstance(data__eagerresources, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".eager-resources must be array", value=data__eagerresources, name="" + (name_prefix or "data") + ".eager-resources", definition={'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__eagerresources_is_list = isinstance(data__eagerresources, (list, tuple))
            if data__eagerresources_is_list:
                data__eagerresources_len = len(data__eagerresources)
                for data__eagerresources_x, data__eagerresources_item in enumerate(data__eagerresources):
                    if not isinstance(data__eagerresources_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".eager-resources[{data__eagerresources_x}]".format(**locals()) + " must be string", value=data__eagerresources_item, name="" + (name_prefix or "data") + ".eager-resources[{data__eagerresources_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "packages" in data_keys:
            data_keys.remove("packages")
            data__packages = data["packages"]
            data__packages_one_of_count2 = 0
            if data__packages_one_of_count2 < 2:
                try:
                    if not isinstance(data__packages, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".packages must be array", value=data__packages, name="" + (name_prefix or "data") + ".packages", definition={'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}}, rule='type')
                    data__packages_is_list = isinstance(data__packages, (list, tuple))
                    if data__packages_is_list:
                        data__packages_len = len(data__packages)
                        for data__packages_x, data__packages_item in enumerate(data__packages):
                            validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_package_name(data__packages_item, custom_formats, (name_prefix or "data") + ".packages[{data__packages_x}]".format(**locals()))
                    data__packages_one_of_count2 += 1
                except JsonSchemaValueException: pass
            if data__packages_one_of_count2 < 2:
                try:
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_find_directive(data__packages, custom_formats, (name_prefix or "data") + ".packages")
                    data__packages_one_of_count2 += 1
                except JsonSchemaValueException: pass
            if data__packages_one_of_count2 != 1:
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".packages must be valid exactly by one definition" + (" (" + str(data__packages_one_of_count2) + " matches found)"), value=data__packages, name="" + (name_prefix or "data") + ".packages", definition={'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}}, {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}]}, rule='oneOf')
        if "package-dir" in data_keys:
            data_keys.remove("package-dir")
            data__packagedir = data["package-dir"]
            if not isinstance(data__packagedir, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir must be object", value=data__packagedir, name="" + (name_prefix or "data") + ".package-dir", definition={'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, rule='type')
            data__packagedir_is_dict = isinstance(data__packagedir, dict)
            if data__packagedir_is_dict:
                data__packagedir_keys = set(data__packagedir.keys())
                for data__packagedir_key, data__packagedir_val in data__packagedir.items():
                    if REGEX_PATTERNS['^.*$'].search(data__packagedir_key):
                        if data__packagedir_key in data__packagedir_keys:
                            data__packagedir_keys.remove(data__packagedir_key)
                        if not isinstance(data__packagedir_val, (str)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir.{data__packagedir_key}".format(**locals()) + " must be string", value=data__packagedir_val, name="" + (name_prefix or "data") + ".package-dir.{data__packagedir_key}".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if data__packagedir_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir must not contain "+str(data__packagedir_keys)+" properties", value=data__packagedir, name="" + (name_prefix or "data") + ".package-dir", definition={'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, rule='additionalProperties')
                data__packagedir_len = len(data__packagedir)
                if data__packagedir_len != 0:
                    data__packagedir_property_names = True
                    for data__packagedir_key in data__packagedir:
                        try:
                            data__packagedir_key_any_of_count3 = 0
                            if not data__packagedir_key_any_of_count3:
                                try:
                                    if data__packagedir_key != "":
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir must be same as const definition: ", value=data__packagedir_key, name="" + (name_prefix or "data") + ".package-dir", definition={'const': ''}, rule='const')
                                    data__packagedir_key_any_of_count3 += 1
                                except JsonSchemaValueException: pass
                            if not data__packagedir_key_any_of_count3:
                                try:
                                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_package_name(data__packagedir_key, custom_formats, (name_prefix or "data") + ".package-dir")
                                    data__packagedir_key_any_of_count3 += 1
                                except JsonSchemaValueException: pass
                            if not data__packagedir_key_any_of_count3:
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir cannot be validated by any definition", value=data__packagedir_key, name="" + (name_prefix or "data") + ".package-dir", definition={'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, rule='anyOf')
                        except JsonSchemaValueException:
                            data__packagedir_property_names = False
                    if not data__packagedir_property_names:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-dir must be named by propertyName definition", value=data__packagedir, name="" + (name_prefix or "data") + ".package-dir", definition={'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, rule='propertyNames')
        if "package-data" in data_keys:
            data_keys.remove("package-data")
            data__packagedata = data["package-data"]
            if not isinstance(data__packagedata, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must be object", value=data__packagedata, name="" + (name_prefix or "data") + ".package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='type')
            data__packagedata_is_dict = isinstance(data__packagedata, dict)
            if data__packagedata_is_dict:
                data__packagedata_keys = set(data__packagedata.keys())
                for data__packagedata_key, data__packagedata_val in data__packagedata.items():
                    if REGEX_PATTERNS['^.*$'].search(data__packagedata_key):
                        if data__packagedata_key in data__packagedata_keys:
                            data__packagedata_keys.remove(data__packagedata_key)
                        if not isinstance(data__packagedata_val, (list, tuple)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data.{data__packagedata_key}".format(**locals()) + " must be array", value=data__packagedata_val, name="" + (name_prefix or "data") + ".package-data.{data__packagedata_key}".format(**locals()) + "", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
                        data__packagedata_val_is_list = isinstance(data__packagedata_val, (list, tuple))
                        if data__packagedata_val_is_list:
                            data__packagedata_val_len = len(data__packagedata_val)
                            for data__packagedata_val_x, data__packagedata_val_item in enumerate(data__packagedata_val):
                                if not isinstance(data__packagedata_val_item, (str)):
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data.{data__packagedata_key}[{data__packagedata_val_x}]".format(**locals()) + " must be string", value=data__packagedata_val_item, name="" + (name_prefix or "data") + ".package-data.{data__packagedata_key}[{data__packagedata_val_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if data__packagedata_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must not contain "+str(data__packagedata_keys)+" properties", value=data__packagedata, name="" + (name_prefix or "data") + ".package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='additionalProperties')
                data__packagedata_len = len(data__packagedata)
                if data__packagedata_len != 0:
                    data__packagedata_property_names = True
                    for data__packagedata_key in data__packagedata:
                        try:
                            data__packagedata_key_any_of_count4 = 0
                            if not data__packagedata_key_any_of_count4:
                                try:
                                    if not isinstance(data__packagedata_key, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must be string", value=data__packagedata_key, name="" + (name_prefix or "data") + ".package-data", definition={'type': 'string', 'format': 'python-module-name'}, rule='type')
                                    if isinstance(data__packagedata_key, str):
                                        if not custom_formats["python-module-name"](data__packagedata_key):
                                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must be python-module-name", value=data__packagedata_key, name="" + (name_prefix or "data") + ".package-data", definition={'type': 'string', 'format': 'python-module-name'}, rule='format')
                                    data__packagedata_key_any_of_count4 += 1
                                except JsonSchemaValueException: pass
                            if not data__packagedata_key_any_of_count4:
                                try:
                                    if data__packagedata_key != "*":
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must be same as const definition: *", value=data__packagedata_key, name="" + (name_prefix or "data") + ".package-data", definition={'const': '*'}, rule='const')
                                    data__packagedata_key_any_of_count4 += 1
                                except JsonSchemaValueException: pass
                            if not data__packagedata_key_any_of_count4:
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data cannot be validated by any definition", value=data__packagedata_key, name="" + (name_prefix or "data") + ".package-data", definition={'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, rule='anyOf')
                        except JsonSchemaValueException:
                            data__packagedata_property_names = False
                    if not data__packagedata_property_names:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".package-data must be named by propertyName definition", value=data__packagedata, name="" + (name_prefix or "data") + ".package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='propertyNames')
        if "include-package-data" in data_keys:
            data_keys.remove("include-package-data")
            data__includepackagedata = data["include-package-data"]
            if not isinstance(data__includepackagedata, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".include-package-data must be boolean", value=data__includepackagedata, name="" + (name_prefix or "data") + ".include-package-data", definition={'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, rule='type')
        if "exclude-package-data" in data_keys:
            data_keys.remove("exclude-package-data")
            data__excludepackagedata = data["exclude-package-data"]
            if not isinstance(data__excludepackagedata, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must be object", value=data__excludepackagedata, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='type')
            data__excludepackagedata_is_dict = isinstance(data__excludepackagedata, dict)
            if data__excludepackagedata_is_dict:
                data__excludepackagedata_keys = set(data__excludepackagedata.keys())
                for data__excludepackagedata_key, data__excludepackagedata_val in data__excludepackagedata.items():
                    if REGEX_PATTERNS['^.*$'].search(data__excludepackagedata_key):
                        if data__excludepackagedata_key in data__excludepackagedata_keys:
                            data__excludepackagedata_keys.remove(data__excludepackagedata_key)
                        if not isinstance(data__excludepackagedata_val, (list, tuple)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data.{data__excludepackagedata_key}".format(**locals()) + " must be array", value=data__excludepackagedata_val, name="" + (name_prefix or "data") + ".exclude-package-data.{data__excludepackagedata_key}".format(**locals()) + "", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
                        data__excludepackagedata_val_is_list = isinstance(data__excludepackagedata_val, (list, tuple))
                        if data__excludepackagedata_val_is_list:
                            data__excludepackagedata_val_len = len(data__excludepackagedata_val)
                            for data__excludepackagedata_val_x, data__excludepackagedata_val_item in enumerate(data__excludepackagedata_val):
                                if not isinstance(data__excludepackagedata_val_item, (str)):
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data.{data__excludepackagedata_key}[{data__excludepackagedata_val_x}]".format(**locals()) + " must be string", value=data__excludepackagedata_val_item, name="" + (name_prefix or "data") + ".exclude-package-data.{data__excludepackagedata_key}[{data__excludepackagedata_val_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if data__excludepackagedata_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must not contain "+str(data__excludepackagedata_keys)+" properties", value=data__excludepackagedata, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='additionalProperties')
                data__excludepackagedata_len = len(data__excludepackagedata)
                if data__excludepackagedata_len != 0:
                    data__excludepackagedata_property_names = True
                    for data__excludepackagedata_key in data__excludepackagedata:
                        try:
                            data__excludepackagedata_key_any_of_count5 = 0
                            if not data__excludepackagedata_key_any_of_count5:
                                try:
                                    if not isinstance(data__excludepackagedata_key, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must be string", value=data__excludepackagedata_key, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'type': 'string', 'format': 'python-module-name'}, rule='type')
                                    if isinstance(data__excludepackagedata_key, str):
                                        if not custom_formats["python-module-name"](data__excludepackagedata_key):
                                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must be python-module-name", value=data__excludepackagedata_key, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'type': 'string', 'format': 'python-module-name'}, rule='format')
                                    data__excludepackagedata_key_any_of_count5 += 1
                                except JsonSchemaValueException: pass
                            if not data__excludepackagedata_key_any_of_count5:
                                try:
                                    if data__excludepackagedata_key != "*":
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must be same as const definition: *", value=data__excludepackagedata_key, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'const': '*'}, rule='const')
                                    data__excludepackagedata_key_any_of_count5 += 1
                                except JsonSchemaValueException: pass
                            if not data__excludepackagedata_key_any_of_count5:
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data cannot be validated by any definition", value=data__excludepackagedata_key, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, rule='anyOf')
                        except JsonSchemaValueException:
                            data__excludepackagedata_property_names = False
                    if not data__excludepackagedata_property_names:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".exclude-package-data must be named by propertyName definition", value=data__excludepackagedata, name="" + (name_prefix or "data") + ".exclude-package-data", definition={'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='propertyNames')
        if "namespace-packages" in data_keys:
            data_keys.remove("namespace-packages")
            data__namespacepackages = data["namespace-packages"]
            if not isinstance(data__namespacepackages, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".namespace-packages must be array", value=data__namespacepackages, name="" + (name_prefix or "data") + ".namespace-packages", definition={'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, rule='type')
            data__namespacepackages_is_list = isinstance(data__namespacepackages, (list, tuple))
            if data__namespacepackages_is_list:
                data__namespacepackages_len = len(data__namespacepackages)
                for data__namespacepackages_x, data__namespacepackages_item in enumerate(data__namespacepackages):
                    if not isinstance(data__namespacepackages_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".namespace-packages[{data__namespacepackages_x}]".format(**locals()) + " must be string", value=data__namespacepackages_item, name="" + (name_prefix or "data") + ".namespace-packages[{data__namespacepackages_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='type')
                    if isinstance(data__namespacepackages_item, str):
                        if not custom_formats["python-module-name-relaxed"](data__namespacepackages_item):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".namespace-packages[{data__namespacepackages_x}]".format(**locals()) + " must be python-module-name-relaxed", value=data__namespacepackages_item, name="" + (name_prefix or "data") + ".namespace-packages[{data__namespacepackages_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='format')
        if "py-modules" in data_keys:
            data_keys.remove("py-modules")
            data__pymodules = data["py-modules"]
            if not isinstance(data__pymodules, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".py-modules must be array", value=data__pymodules, name="" + (name_prefix or "data") + ".py-modules", definition={'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, rule='type')
            data__pymodules_is_list = isinstance(data__pymodules, (list, tuple))
            if data__pymodules_is_list:
                data__pymodules_len = len(data__pymodules)
                for data__pymodules_x, data__pymodules_item in enumerate(data__pymodules):
                    if not isinstance(data__pymodules_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".py-modules[{data__pymodules_x}]".format(**locals()) + " must be string", value=data__pymodules_item, name="" + (name_prefix or "data") + ".py-modules[{data__pymodules_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='type')
                    if isinstance(data__pymodules_item, str):
                        if not custom_formats["python-module-name-relaxed"](data__pymodules_item):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".py-modules[{data__pymodules_x}]".format(**locals()) + " must be python-module-name-relaxed", value=data__pymodules_item, name="" + (name_prefix or "data") + ".py-modules[{data__pymodules_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='format')
        if "ext-modules" in data_keys:
            data_keys.remove("ext-modules")
            data__extmodules = data["ext-modules"]
            if not isinstance(data__extmodules, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ext-modules must be array", value=data__extmodules, name="" + (name_prefix or "data") + ".ext-modules", definition={'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}}, rule='type')
            data__extmodules_is_list = isinstance(data__extmodules, (list, tuple))
            if data__extmodules_is_list:
                data__extmodules_len = len(data__extmodules)
                for data__extmodules_x, data__extmodules_item in enumerate(data__extmodules):
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_ext_module(data__extmodules_item, custom_formats, (name_prefix or "data") + ".ext-modules[{data__extmodules_x}]".format(**locals()))
        if "data-files" in data_keys:
            data_keys.remove("data-files")
            data__datafiles = data["data-files"]
            if not isinstance(data__datafiles, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".data-files must be object", value=data__datafiles, name="" + (name_prefix or "data") + ".data-files", definition={'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, rule='type')
            data__datafiles_is_dict = isinstance(data__datafiles, dict)
            if data__datafiles_is_dict:
                data__datafiles_keys = set(data__datafiles.keys())
                for data__datafiles_key, data__datafiles_val in data__datafiles.items():
                    if REGEX_PATTERNS['^.*$'].search(data__datafiles_key):
                        if data__datafiles_key in data__datafiles_keys:
                            data__datafiles_keys.remove(data__datafiles_key)
                        if not isinstance(data__datafiles_val, (list, tuple)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".data-files.{data__datafiles_key}".format(**locals()) + " must be array", value=data__datafiles_val, name="" + (name_prefix or "data") + ".data-files.{data__datafiles_key}".format(**locals()) + "", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
                        data__datafiles_val_is_list = isinstance(data__datafiles_val, (list, tuple))
                        if data__datafiles_val_is_list:
                            data__datafiles_val_len = len(data__datafiles_val)
                            for data__datafiles_val_x, data__datafiles_val_item in enumerate(data__datafiles_val):
                                if not isinstance(data__datafiles_val_item, (str)):
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".data-files.{data__datafiles_key}[{data__datafiles_val_x}]".format(**locals()) + " must be string", value=data__datafiles_val_item, name="" + (name_prefix or "data") + ".data-files.{data__datafiles_key}[{data__datafiles_val_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "cmdclass" in data_keys:
            data_keys.remove("cmdclass")
            data__cmdclass = data["cmdclass"]
            if not isinstance(data__cmdclass, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".cmdclass must be object", value=data__cmdclass, name="" + (name_prefix or "data") + ".cmdclass", definition={'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, rule='type')
            data__cmdclass_is_dict = isinstance(data__cmdclass, dict)
            if data__cmdclass_is_dict:
                data__cmdclass_keys = set(data__cmdclass.keys())
                for data__cmdclass_key, data__cmdclass_val in data__cmdclass.items():
                    if REGEX_PATTERNS['^.*$'].search(data__cmdclass_key):
                        if data__cmdclass_key in data__cmdclass_keys:
                            data__cmdclass_keys.remove(data__cmdclass_key)
                        if not isinstance(data__cmdclass_val, (str)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".cmdclass.{data__cmdclass_key}".format(**locals()) + " must be string", value=data__cmdclass_val, name="" + (name_prefix or "data") + ".cmdclass.{data__cmdclass_key}".format(**locals()) + "", definition={'type': 'string', 'format': 'python-qualified-identifier'}, rule='type')
                        if isinstance(data__cmdclass_val, str):
                            if not custom_formats["python-qualified-identifier"](data__cmdclass_val):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".cmdclass.{data__cmdclass_key}".format(**locals()) + " must be python-qualified-identifier", value=data__cmdclass_val, name="" + (name_prefix or "data") + ".cmdclass.{data__cmdclass_key}".format(**locals()) + "", definition={'type': 'string', 'format': 'python-qualified-identifier'}, rule='format')
        if "license-files" in data_keys:
            data_keys.remove("license-files")
            data__licensefiles = data["license-files"]
            if not isinstance(data__licensefiles, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".license-files must be array", value=data__licensefiles, name="" + (name_prefix or "data") + ".license-files", definition={'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, rule='type')
            data__licensefiles_is_list = isinstance(data__licensefiles, (list, tuple))
            if data__licensefiles_is_list:
                data__licensefiles_len = len(data__licensefiles)
                for data__licensefiles_x, data__licensefiles_item in enumerate(data__licensefiles):
                    if not isinstance(data__licensefiles_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".license-files[{data__licensefiles_x}]".format(**locals()) + " must be string", value=data__licensefiles_item, name="" + (name_prefix or "data") + ".license-files[{data__licensefiles_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "dynamic" in data_keys:
            data_keys.remove("dynamic")
            data__dynamic = data["dynamic"]
            if not isinstance(data__dynamic, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic must be object", value=data__dynamic, name="" + (name_prefix or "data") + ".dynamic", definition={'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'classifiers': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'description': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'entry-points': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, 'readme': {'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}}}, rule='type')
            data__dynamic_is_dict = isinstance(data__dynamic, dict)
            if data__dynamic_is_dict:
                data__dynamic_keys = set(data__dynamic.keys())
                if "version" in data__dynamic_keys:
                    data__dynamic_keys.remove("version")
                    data__dynamic__version = data__dynamic["version"]
                    data__dynamic__version_one_of_count6 = 0
                    if data__dynamic__version_one_of_count6 < 2:
                        try:
                            validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_attr_directive(data__dynamic__version, custom_formats, (name_prefix or "data") + ".dynamic.version")
                            data__dynamic__version_one_of_count6 += 1
                        except JsonSchemaValueException: pass
                    if data__dynamic__version_one_of_count6 < 2:
                        try:
                            validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data__dynamic__version, custom_formats, (name_prefix or "data") + ".dynamic.version")
                            data__dynamic__version_one_of_count6 += 1
                        except JsonSchemaValueException: pass
                    if data__dynamic__version_one_of_count6 != 1:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.version must be valid exactly by one definition" + (" (" + str(data__dynamic__version_one_of_count6) + " matches found)"), value=data__dynamic__version, name="" + (name_prefix or "data") + ".dynamic.version", definition={'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, rule='oneOf')
                if "classifiers" in data__dynamic_keys:
                    data__dynamic_keys.remove("classifiers")
                    data__dynamic__classifiers = data__dynamic["classifiers"]
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data__dynamic__classifiers, custom_formats, (name_prefix or "data") + ".dynamic.classifiers")
                if "description" in data__dynamic_keys:
                    data__dynamic_keys.remove("description")
                    data__dynamic__description = data__dynamic["description"]
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data__dynamic__description, custom_formats, (name_prefix or "data") + ".dynamic.description")
                if "entry-points" in data__dynamic_keys:
                    data__dynamic_keys.remove("entry-points")
                    data__dynamic__entrypoints = data__dynamic["entry-points"]
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data__dynamic__entrypoints, custom_formats, (name_prefix or "data") + ".dynamic.entry-points")
                if "dependencies" in data__dynamic_keys:
                    data__dynamic_keys.remove("dependencies")
                    data__dynamic__dependencies = data__dynamic["dependencies"]
                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive_for_dependencies(data__dynamic__dependencies, custom_formats, (name_prefix or "data") + ".dynamic.dependencies")
                if "optional-dependencies" in data__dynamic_keys:
                    data__dynamic_keys.remove("optional-dependencies")
                    data__dynamic__optionaldependencies = data__dynamic["optional-dependencies"]
                    if not isinstance(data__dynamic__optionaldependencies, (dict)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.optional-dependencies must be object", value=data__dynamic__optionaldependencies, name="" + (name_prefix or "data") + ".dynamic.optional-dependencies", definition={'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, rule='type')
                    data__dynamic__optionaldependencies_is_dict = isinstance(data__dynamic__optionaldependencies, dict)
                    if data__dynamic__optionaldependencies_is_dict:
                        data__dynamic__optionaldependencies_keys = set(data__dynamic__optionaldependencies.keys())
                        for data__dynamic__optionaldependencies_key, data__dynamic__optionaldependencies_val in data__dynamic__optionaldependencies.items():
                            if REGEX_PATTERNS['.+'].search(data__dynamic__optionaldependencies_key):
                                if data__dynamic__optionaldependencies_key in data__dynamic__optionaldependencies_keys:
                                    data__dynamic__optionaldependencies_keys.remove(data__dynamic__optionaldependencies_key)
                                validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive_for_dependencies(data__dynamic__optionaldependencies_val, custom_formats, (name_prefix or "data") + ".dynamic.optional-dependencies.{data__dynamic__optionaldependencies_key}".format(**locals()))
                        if data__dynamic__optionaldependencies_keys:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.optional-dependencies must not contain "+str(data__dynamic__optionaldependencies_keys)+" properties", value=data__dynamic__optionaldependencies, name="" + (name_prefix or "data") + ".dynamic.optional-dependencies", definition={'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, rule='additionalProperties')
                        data__dynamic__optionaldependencies_len = len(data__dynamic__optionaldependencies)
                        if data__dynamic__optionaldependencies_len != 0:
                            data__dynamic__optionaldependencies_property_names = True
                            for data__dynamic__optionaldependencies_key in data__dynamic__optionaldependencies:
                                try:
                                    if not isinstance(data__dynamic__optionaldependencies_key, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.optional-dependencies must be string", value=data__dynamic__optionaldependencies_key, name="" + (name_prefix or "data") + ".dynamic.optional-dependencies", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='type')
                                    if isinstance(data__dynamic__optionaldependencies_key, str):
                                        if not custom_formats["pep508-identifier"](data__dynamic__optionaldependencies_key):
                                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.optional-dependencies must be pep508-identifier", value=data__dynamic__optionaldependencies_key, name="" + (name_prefix or "data") + ".dynamic.optional-dependencies", definition={'type': 'string', 'format': 'pep508-identifier'}, rule='format')
                                except JsonSchemaValueException:
                                    data__dynamic__optionaldependencies_property_names = False
                            if not data__dynamic__optionaldependencies_property_names:
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.optional-dependencies must be named by propertyName definition", value=data__dynamic__optionaldependencies, name="" + (name_prefix or "data") + ".dynamic.optional-dependencies", definition={'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, rule='propertyNames')
                if "readme" in data__dynamic_keys:
                    data__dynamic_keys.remove("readme")
                    data__dynamic__readme = data__dynamic["readme"]
                    if not isinstance(data__dynamic__readme, (dict)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme must be object", value=data__dynamic__readme, name="" + (name_prefix or "data") + ".dynamic.readme", definition={'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}, rule='type')
                    data__dynamic__readme_any_of_count7 = 0
                    if not data__dynamic__readme_any_of_count7:
                        try:
                            validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data__dynamic__readme, custom_formats, (name_prefix or "data") + ".dynamic.readme")
                            data__dynamic__readme_any_of_count7 += 1
                        except JsonSchemaValueException: pass
                    if not data__dynamic__readme_any_of_count7:
                        try:
                            if not isinstance(data__dynamic__readme, (dict)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme must be object", value=data__dynamic__readme, name="" + (name_prefix or "data") + ".dynamic.readme", definition={'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}, rule='type')
                            data__dynamic__readme_is_dict = isinstance(data__dynamic__readme, dict)
                            if data__dynamic__readme_is_dict:
                                data__dynamic__readme_keys = set(data__dynamic__readme.keys())
                                if "content-type" in data__dynamic__readme_keys:
                                    data__dynamic__readme_keys.remove("content-type")
                                    data__dynamic__readme__contenttype = data__dynamic__readme["content-type"]
                                    if not isinstance(data__dynamic__readme__contenttype, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme.content-type must be string", value=data__dynamic__readme__contenttype, name="" + (name_prefix or "data") + ".dynamic.readme.content-type", definition={'type': 'string'}, rule='type')
                                if "file" in data__dynamic__readme_keys:
                                    data__dynamic__readme_keys.remove("file")
                                    data__dynamic__readme__file = data__dynamic__readme["file"]
                                    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive_properties_file(data__dynamic__readme__file, custom_formats, (name_prefix or "data") + ".dynamic.readme.file")
                                if data__dynamic__readme_keys:
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme must not contain "+str(data__dynamic__readme_keys)+" properties", value=data__dynamic__readme, name="" + (name_prefix or "data") + ".dynamic.readme", definition={'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}, rule='additionalProperties')
                            data__dynamic__readme_any_of_count7 += 1
                        except JsonSchemaValueException: pass
                    if not data__dynamic__readme_any_of_count7:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme cannot be validated by any definition", value=data__dynamic__readme, name="" + (name_prefix or "data") + ".dynamic.readme", definition={'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}, rule='anyOf')
                    data__dynamic__readme_is_dict = isinstance(data__dynamic__readme, dict)
                    if data__dynamic__readme_is_dict:
                        data__dynamic__readme__missing_keys = set(['file']) - data__dynamic__readme.keys()
                        if data__dynamic__readme__missing_keys:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic.readme must contain " + (str(sorted(data__dynamic__readme__missing_keys)) + " properties"), value=data__dynamic__readme, name="" + (name_prefix or "data") + ".dynamic.readme", definition={'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}, rule='required')
                if data__dynamic_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic must not contain "+str(data__dynamic_keys)+" properties", value=data__dynamic, name="" + (name_prefix or "data") + ".dynamic", definition={'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'classifiers': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'description': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'entry-points': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, 'readme': {'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}}}, rule='additionalProperties')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html', 'title': '``tool.setuptools`` table', '$$description': ['``setuptools``-specific configurations that can be set by users that require', 'customization.', 'These configurations are completely optional and probably can be skipped when', 'creating simple packages. They are equivalent to some of the `Keywords', '<https://setuptools.pypa.io/en/latest/references/keywords.html>`_', 'used by the ``setup.py`` file, and can be set via the ``tool.setuptools`` table.', 'It considers only ``setuptools`` `parameters', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_', 'that are not covered by :pep:`621`; and intentionally excludes ``dependency_links``', 'and ``setup_requires`` (incompatible with modern workflows/standards).'], 'type': 'object', 'additionalProperties': False, 'properties': {'platforms': {'type': 'array', 'items': {'type': 'string'}}, 'provides': {'$$description': ['Package and virtual package names contained within this package', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'obsoletes': {'$$description': ['Packages which this package renders obsolete', '**(not supported by pip)**'], 'type': 'array', 'items': {'type': 'string', 'format': 'pep508-identifier'}}, 'zip-safe': {'$$description': ['Whether the project can be safely installed and run from a zip file.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'boolean'}, 'script-files': {'$$description': ['Legacy way of defining scripts (entry-points are preferred).', 'Equivalent to the ``script`` keyword in ``setup.py``', '(it was renamed to avoid confusion with entry-point based ``project.scripts``', 'defined in :pep:`621`).', '**DISCOURAGED**: generic script wrappers are tricky and may not work properly.', 'Whenever possible, please use ``project.scripts`` instead.'], 'type': 'array', 'items': {'type': 'string'}, '$comment': 'TODO: is this field deprecated/should be removed?'}, 'eager-resources': {'$$description': ['Resources that should be extracted together, if any of them is needed,', 'or if any C extensions included in the project are imported.', '**OBSOLETE**: only relevant for ``pkg_resources``, ``easy_install`` and', '``setup.py install`` in the context of ``eggs`` (**DEPRECATED**).'], 'type': 'array', 'items': {'type': 'string'}}, 'packages': {'$$description': ['Packages that should be included in the distribution.', 'It can be given either as a list of package identifiers', 'or as a ``dict``-like structure with a single key ``find``', 'which corresponds to a dynamic call to', '``setuptools.config.expand.find_packages`` function.', 'The ``find`` key is associated with a nested ``dict``-like structure that can', 'contain ``where``, ``include``, ``exclude`` and ``namespaces`` keys,', 'mimicking the keyword arguments of the associated function.'], 'oneOf': [{'title': 'Array of Python package identifiers', 'type': 'array', 'items': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}}, {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}]}, 'package-dir': {'$$description': [':class:`dict`-like structure mapping from package names to directories where their', 'code can be found.', 'The empty string (as key) means that all packages are contained inside', 'the given directory will be included in the distribution.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'const': ''}, {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}]}, 'patternProperties': {'^.*$': {'type': 'string'}}}, 'package-data': {'$$description': ['Mapping from package names to lists of glob patterns.', 'Usually this option is not needed when using ``include-package-data = true``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'include-package-data': {'$$description': ['Automatically include any data files inside the package directories', 'that are specified by ``MANIFEST.in``', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'boolean'}, 'exclude-package-data': {'$$description': ['Mapping from package names to lists of glob patterns that should be excluded', 'For more information on how to include data files, check ``setuptools`` `docs', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'additionalProperties': False, 'propertyNames': {'anyOf': [{'type': 'string', 'format': 'python-module-name'}, {'const': '*'}]}, 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'namespace-packages': {'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html', 'description': '**DEPRECATED**: use implicit namespaces instead (:pep:`420`).'}, 'py-modules': {'description': 'Modules that setuptools will manipulate', 'type': 'array', 'items': {'type': 'string', 'format': 'python-module-name-relaxed'}, '$comment': 'TODO: clarify the relationship with ``packages``'}, 'ext-modules': {'description': 'Extension modules to be compiled by setuptools', 'type': 'array', 'items': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}}, 'data-files': {'$$description': ['``dict``-like structure where each key represents a directory and', 'the value is a list of glob patterns that should be installed in them.', '**DISCOURAGED**: please notice this might not work as expected with wheels.', 'Whenever possible, consider using data files inside the package directories', '(or create a new namespace package that only contains data files).', 'See `data files support', '<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'array', 'items': {'type': 'string'}}}}, 'cmdclass': {'$$description': ['Mapping of distutils-style command names to ``setuptools.Command`` subclasses', 'which in turn should be represented by strings with a qualified class name', '(i.e., "dotted" form with module), e.g.::\n\n', '    cmdclass = {mycmd = "pkg.subpkg.module.CommandClass"}\n\n', 'The command class should be a directly defined at the top-level of the', 'containing module (no class nesting).'], 'type': 'object', 'patternProperties': {'^.*$': {'type': 'string', 'format': 'python-qualified-identifier'}}}, 'license-files': {'type': 'array', 'items': {'type': 'string'}, '$$description': ['**PROVISIONAL**: list of glob patterns for all license files being distributed.', '(likely to become standard with :pep:`639`).', "By default: ``['LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*']``"], '$comment': 'TODO: revise if PEP 639 is accepted. Probably ``project.license-files``?'}, 'dynamic': {'type': 'object', 'description': 'Instructions for loading :pep:`621`-related metadata dynamically', 'additionalProperties': False, 'properties': {'version': {'$$description': ['A version dynamically loaded via either the ``attr:`` or ``file:``', 'directives. Please make sure the given file or attribute respects :pep:`440`.', 'Also ensure to set ``project.dynamic`` accordingly.'], 'oneOf': [{'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'classifiers': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'description': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'entry-points': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}, 'optional-dependencies': {'type': 'object', 'propertyNames': {'type': 'string', 'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'.+': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$ref': '#/definitions/file-directive'}]}}}, 'readme': {'type': 'object', 'anyOf': [{'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, {'type': 'object', 'properties': {'content-type': {'type': 'string'}, 'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'additionalProperties': False}], 'required': ['file']}}}}, 'definitions': {'package-name': {'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, 'ext-module': {'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, 'file-directive': {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, 'file-directive-for-dependencies': {'title': "'file:' directive for dependencies", 'allOf': [{'$$description': ['**BETA**: subset of the ``requirements.txt`` format', 'without ``pip`` flags and options', '(one :pep:`508`-compliant string per line,', 'lines that are blank or start with ``#`` are excluded).', 'See `dynamic metadata', '<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.']}, {'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}]}, 'attr-directive': {'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, 'find-directive': {'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}}}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive_properties_file(data, custom_formats={}, name_prefix=None):
    data_one_of_count8 = 0
    if data_one_of_count8 < 2:
        try:
            if not isinstance(data, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'string'}, rule='type')
            data_one_of_count8 += 1
        except JsonSchemaValueException: pass
    if data_one_of_count8 < 2:
        try:
            if not isinstance(data, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must be array", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data_is_list = isinstance(data, (list, tuple))
            if data_is_list:
                data_len = len(data)
                for data_x, data_item in enumerate(data):
                    if not isinstance(data_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + "[{data_x}]".format(**locals()) + " must be string", value=data_item, name="" + (name_prefix or "data") + "[{data_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
            data_one_of_count8 += 1
        except JsonSchemaValueException: pass
    if data_one_of_count8 != 1:
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be valid exactly by one definition" + (" (" + str(data_one_of_count8) + " matches found)"), value=data, name="" + (name_prefix or "data") + "", definition={'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}, rule='oneOf')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive_for_dependencies(data, custom_formats={}, name_prefix=None):
    validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data, custom_formats, (name_prefix or "data") + "")
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_file_directive(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['file']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, rule='required')
        data_keys = set(data.keys())
        if "file" in data_keys:
            data_keys.remove("file")
            data__file = data["file"]
            data__file_one_of_count9 = 0
            if data__file_one_of_count9 < 2:
                try:
                    if not isinstance(data__file, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".file must be string", value=data__file, name="" + (name_prefix or "data") + ".file", definition={'type': 'string'}, rule='type')
                    data__file_one_of_count9 += 1
                except JsonSchemaValueException: pass
            if data__file_one_of_count9 < 2:
                try:
                    if not isinstance(data__file, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".file must be array", value=data__file, name="" + (name_prefix or "data") + ".file", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
                    data__file_is_list = isinstance(data__file, (list, tuple))
                    if data__file_is_list:
                        data__file_len = len(data__file)
                        for data__file_x, data__file_item in enumerate(data__file):
                            if not isinstance(data__file_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".file[{data__file_x}]".format(**locals()) + " must be string", value=data__file_item, name="" + (name_prefix or "data") + ".file[{data__file_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                    data__file_one_of_count9 += 1
                except JsonSchemaValueException: pass
            if data__file_one_of_count9 != 1:
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".file must be valid exactly by one definition" + (" (" + str(data__file_one_of_count9) + " matches found)"), value=data__file, name="" + (name_prefix or "data") + ".file", definition={'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}, rule='oneOf')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/file-directive', 'title': "'file:' directive", 'description': 'Value is read from a file (or list of files and then concatenated)', 'type': 'object', 'additionalProperties': False, 'properties': {'file': {'oneOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]}}, 'required': ['file']}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_attr_directive(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['attr']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, rule='required')
        data_keys = set(data.keys())
        if "attr" in data_keys:
            data_keys.remove("attr")
            data__attr = data["attr"]
            if not isinstance(data__attr, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attr must be string", value=data__attr, name="" + (name_prefix or "data") + ".attr", definition={'type': 'string', 'format': 'python-qualified-identifier'}, rule='type')
            if isinstance(data__attr, str):
                if not custom_formats["python-qualified-identifier"](data__attr):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attr must be python-qualified-identifier", value=data__attr, name="" + (name_prefix or "data") + ".attr", definition={'type': 'string', 'format': 'python-qualified-identifier'}, rule='format')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'title': "'attr:' directive", '$id': '#/definitions/attr-directive', '$$description': ['Value is read from a module attribute. Supports callables and iterables;', 'unsupported types are cast via ``str()``'], 'type': 'object', 'additionalProperties': False, 'properties': {'attr': {'type': 'string', 'format': 'python-qualified-identifier'}}, 'required': ['attr']}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_ext_module(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'sources']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, rule='required')
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string", value=data__name, name="" + (name_prefix or "data") + ".name", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='type')
            if isinstance(data__name, str):
                if not custom_formats["python-module-name-relaxed"](data__name):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be python-module-name-relaxed", value=data__name, name="" + (name_prefix or "data") + ".name", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='format')
        if "sources" in data_keys:
            data_keys.remove("sources")
            data__sources = data["sources"]
            if not isinstance(data__sources, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".sources must be array", value=data__sources, name="" + (name_prefix or "data") + ".sources", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__sources_is_list = isinstance(data__sources, (list, tuple))
            if data__sources_is_list:
                data__sources_len = len(data__sources)
                for data__sources_x, data__sources_item in enumerate(data__sources):
                    if not isinstance(data__sources_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".sources[{data__sources_x}]".format(**locals()) + " must be string", value=data__sources_item, name="" + (name_prefix or "data") + ".sources[{data__sources_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "include-dirs" in data_keys:
            data_keys.remove("include-dirs")
            data__includedirs = data["include-dirs"]
            if not isinstance(data__includedirs, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".include-dirs must be array", value=data__includedirs, name="" + (name_prefix or "data") + ".include-dirs", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__includedirs_is_list = isinstance(data__includedirs, (list, tuple))
            if data__includedirs_is_list:
                data__includedirs_len = len(data__includedirs)
                for data__includedirs_x, data__includedirs_item in enumerate(data__includedirs):
                    if not isinstance(data__includedirs_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".include-dirs[{data__includedirs_x}]".format(**locals()) + " must be string", value=data__includedirs_item, name="" + (name_prefix or "data") + ".include-dirs[{data__includedirs_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "define-macros" in data_keys:
            data_keys.remove("define-macros")
            data__definemacros = data["define-macros"]
            if not isinstance(data__definemacros, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros must be array", value=data__definemacros, name="" + (name_prefix or "data") + ".define-macros", definition={'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, rule='type')
            data__definemacros_is_list = isinstance(data__definemacros, (list, tuple))
            if data__definemacros_is_list:
                data__definemacros_len = len(data__definemacros)
                for data__definemacros_x, data__definemacros_item in enumerate(data__definemacros):
                    if not isinstance(data__definemacros_item, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}]".format(**locals()) + " must be array", value=data__definemacros_item, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}]".format(**locals()) + "", definition={'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}, rule='type')
                    data__definemacros_item_is_list = isinstance(data__definemacros_item, (list, tuple))
                    if data__definemacros_item_is_list:
                        data__definemacros_item_len = len(data__definemacros_item)
                        if data__definemacros_item_len > 0:
                            data__definemacros_item__0 = data__definemacros_item[0]
                            if not isinstance(data__definemacros_item__0, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][0]".format(**locals()) + " must be string", value=data__definemacros_item__0, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][0]".format(**locals()) + "", definition={'description': 'macro name', 'type': 'string'}, rule='type')
                        if data__definemacros_item_len > 1:
                            data__definemacros_item__1 = data__definemacros_item[1]
                            data__definemacros_item__1_one_of_count10 = 0
                            if data__definemacros_item__1_one_of_count10 < 2:
                                try:
                                    if not isinstance(data__definemacros_item__1, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + " must be string", value=data__definemacros_item__1, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                                    data__definemacros_item__1_one_of_count10 += 1
                                except JsonSchemaValueException: pass
                            if data__definemacros_item__1_one_of_count10 < 2:
                                try:
                                    if not isinstance(data__definemacros_item__1, (NoneType)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + " must be null", value=data__definemacros_item__1, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + "", definition={'type': 'null'}, rule='type')
                                    data__definemacros_item__1_one_of_count10 += 1
                                except JsonSchemaValueException: pass
                            if data__definemacros_item__1_one_of_count10 != 1:
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + " must be valid exactly by one definition" + (" (" + str(data__definemacros_item__1_one_of_count10) + " matches found)"), value=data__definemacros_item__1, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}][1]".format(**locals()) + "", definition={'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}, rule='oneOf')
                        if data__definemacros_item_len > 2:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}]".format(**locals()) + " must contain only specified items", value=data__definemacros_item, name="" + (name_prefix or "data") + ".define-macros[{data__definemacros_x}]".format(**locals()) + "", definition={'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}, rule='items')
        if "undef-macros" in data_keys:
            data_keys.remove("undef-macros")
            data__undefmacros = data["undef-macros"]
            if not isinstance(data__undefmacros, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".undef-macros must be array", value=data__undefmacros, name="" + (name_prefix or "data") + ".undef-macros", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__undefmacros_is_list = isinstance(data__undefmacros, (list, tuple))
            if data__undefmacros_is_list:
                data__undefmacros_len = len(data__undefmacros)
                for data__undefmacros_x, data__undefmacros_item in enumerate(data__undefmacros):
                    if not isinstance(data__undefmacros_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".undef-macros[{data__undefmacros_x}]".format(**locals()) + " must be string", value=data__undefmacros_item, name="" + (name_prefix or "data") + ".undef-macros[{data__undefmacros_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "library-dirs" in data_keys:
            data_keys.remove("library-dirs")
            data__librarydirs = data["library-dirs"]
            if not isinstance(data__librarydirs, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".library-dirs must be array", value=data__librarydirs, name="" + (name_prefix or "data") + ".library-dirs", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__librarydirs_is_list = isinstance(data__librarydirs, (list, tuple))
            if data__librarydirs_is_list:
                data__librarydirs_len = len(data__librarydirs)
                for data__librarydirs_x, data__librarydirs_item in enumerate(data__librarydirs):
                    if not isinstance(data__librarydirs_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".library-dirs[{data__librarydirs_x}]".format(**locals()) + " must be string", value=data__librarydirs_item, name="" + (name_prefix or "data") + ".library-dirs[{data__librarydirs_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "libraries" in data_keys:
            data_keys.remove("libraries")
            data__libraries = data["libraries"]
            if not isinstance(data__libraries, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".libraries must be array", value=data__libraries, name="" + (name_prefix or "data") + ".libraries", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__libraries_is_list = isinstance(data__libraries, (list, tuple))
            if data__libraries_is_list:
                data__libraries_len = len(data__libraries)
                for data__libraries_x, data__libraries_item in enumerate(data__libraries):
                    if not isinstance(data__libraries_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".libraries[{data__libraries_x}]".format(**locals()) + " must be string", value=data__libraries_item, name="" + (name_prefix or "data") + ".libraries[{data__libraries_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "runtime-library-dirs" in data_keys:
            data_keys.remove("runtime-library-dirs")
            data__runtimelibrarydirs = data["runtime-library-dirs"]
            if not isinstance(data__runtimelibrarydirs, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".runtime-library-dirs must be array", value=data__runtimelibrarydirs, name="" + (name_prefix or "data") + ".runtime-library-dirs", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__runtimelibrarydirs_is_list = isinstance(data__runtimelibrarydirs, (list, tuple))
            if data__runtimelibrarydirs_is_list:
                data__runtimelibrarydirs_len = len(data__runtimelibrarydirs)
                for data__runtimelibrarydirs_x, data__runtimelibrarydirs_item in enumerate(data__runtimelibrarydirs):
                    if not isinstance(data__runtimelibrarydirs_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".runtime-library-dirs[{data__runtimelibrarydirs_x}]".format(**locals()) + " must be string", value=data__runtimelibrarydirs_item, name="" + (name_prefix or "data") + ".runtime-library-dirs[{data__runtimelibrarydirs_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "extra-objects" in data_keys:
            data_keys.remove("extra-objects")
            data__extraobjects = data["extra-objects"]
            if not isinstance(data__extraobjects, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-objects must be array", value=data__extraobjects, name="" + (name_prefix or "data") + ".extra-objects", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__extraobjects_is_list = isinstance(data__extraobjects, (list, tuple))
            if data__extraobjects_is_list:
                data__extraobjects_len = len(data__extraobjects)
                for data__extraobjects_x, data__extraobjects_item in enumerate(data__extraobjects):
                    if not isinstance(data__extraobjects_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-objects[{data__extraobjects_x}]".format(**locals()) + " must be string", value=data__extraobjects_item, name="" + (name_prefix or "data") + ".extra-objects[{data__extraobjects_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "extra-compile-args" in data_keys:
            data_keys.remove("extra-compile-args")
            data__extracompileargs = data["extra-compile-args"]
            if not isinstance(data__extracompileargs, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-compile-args must be array", value=data__extracompileargs, name="" + (name_prefix or "data") + ".extra-compile-args", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__extracompileargs_is_list = isinstance(data__extracompileargs, (list, tuple))
            if data__extracompileargs_is_list:
                data__extracompileargs_len = len(data__extracompileargs)
                for data__extracompileargs_x, data__extracompileargs_item in enumerate(data__extracompileargs):
                    if not isinstance(data__extracompileargs_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-compile-args[{data__extracompileargs_x}]".format(**locals()) + " must be string", value=data__extracompileargs_item, name="" + (name_prefix or "data") + ".extra-compile-args[{data__extracompileargs_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "extra-link-args" in data_keys:
            data_keys.remove("extra-link-args")
            data__extralinkargs = data["extra-link-args"]
            if not isinstance(data__extralinkargs, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-link-args must be array", value=data__extralinkargs, name="" + (name_prefix or "data") + ".extra-link-args", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__extralinkargs_is_list = isinstance(data__extralinkargs, (list, tuple))
            if data__extralinkargs_is_list:
                data__extralinkargs_len = len(data__extralinkargs)
                for data__extralinkargs_x, data__extralinkargs_item in enumerate(data__extralinkargs):
                    if not isinstance(data__extralinkargs_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".extra-link-args[{data__extralinkargs_x}]".format(**locals()) + " must be string", value=data__extralinkargs_item, name="" + (name_prefix or "data") + ".extra-link-args[{data__extralinkargs_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "export-symbols" in data_keys:
            data_keys.remove("export-symbols")
            data__exportsymbols = data["export-symbols"]
            if not isinstance(data__exportsymbols, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".export-symbols must be array", value=data__exportsymbols, name="" + (name_prefix or "data") + ".export-symbols", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__exportsymbols_is_list = isinstance(data__exportsymbols, (list, tuple))
            if data__exportsymbols_is_list:
                data__exportsymbols_len = len(data__exportsymbols)
                for data__exportsymbols_x, data__exportsymbols_item in enumerate(data__exportsymbols):
                    if not isinstance(data__exportsymbols_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".export-symbols[{data__exportsymbols_x}]".format(**locals()) + " must be string", value=data__exportsymbols_item, name="" + (name_prefix or "data") + ".export-symbols[{data__exportsymbols_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "swig-opts" in data_keys:
            data_keys.remove("swig-opts")
            data__swigopts = data["swig-opts"]
            if not isinstance(data__swigopts, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".swig-opts must be array", value=data__swigopts, name="" + (name_prefix or "data") + ".swig-opts", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__swigopts_is_list = isinstance(data__swigopts, (list, tuple))
            if data__swigopts_is_list:
                data__swigopts_len = len(data__swigopts)
                for data__swigopts_x, data__swigopts_item in enumerate(data__swigopts):
                    if not isinstance(data__swigopts_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".swig-opts[{data__swigopts_x}]".format(**locals()) + " must be string", value=data__swigopts_item, name="" + (name_prefix or "data") + ".swig-opts[{data__swigopts_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "depends" in data_keys:
            data_keys.remove("depends")
            data__depends = data["depends"]
            if not isinstance(data__depends, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".depends must be array", value=data__depends, name="" + (name_prefix or "data") + ".depends", definition={'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__depends_is_list = isinstance(data__depends, (list, tuple))
            if data__depends_is_list:
                data__depends_len = len(data__depends)
                for data__depends_x, data__depends_item in enumerate(data__depends):
                    if not isinstance(data__depends_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".depends[{data__depends_x}]".format(**locals()) + " must be string", value=data__depends_item, name="" + (name_prefix or "data") + ".depends[{data__depends_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "language" in data_keys:
            data_keys.remove("language")
            data__language = data["language"]
            if not isinstance(data__language, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".language must be string", value=data__language, name="" + (name_prefix or "data") + ".language", definition={'type': 'string'}, rule='type')
        if "optional" in data_keys:
            data_keys.remove("optional")
            data__optional = data["optional"]
            if not isinstance(data__optional, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional must be boolean", value=data__optional, name="" + (name_prefix or "data") + ".optional", definition={'type': 'boolean'}, rule='type')
        if "py-limited-api" in data_keys:
            data_keys.remove("py-limited-api")
            data__pylimitedapi = data["py-limited-api"]
            if not isinstance(data__pylimitedapi, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".py-limited-api must be boolean", value=data__pylimitedapi, name="" + (name_prefix or "data") + ".py-limited-api", definition={'type': 'boolean'}, rule='type')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/ext-module', 'title': 'Extension module', 'description': 'Parameters to construct a :class:`setuptools.Extension` object', 'type': 'object', 'required': ['name', 'sources'], 'additionalProperties': False, 'properties': {'name': {'type': 'string', 'format': 'python-module-name-relaxed'}, 'sources': {'type': 'array', 'items': {'type': 'string'}}, 'include-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'define-macros': {'type': 'array', 'items': {'type': 'array', 'items': [{'description': 'macro name', 'type': 'string'}, {'description': 'macro value', 'oneOf': [{'type': 'string'}, {'type': 'null'}]}], 'additionalItems': False}}, 'undef-macros': {'type': 'array', 'items': {'type': 'string'}}, 'library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'libraries': {'type': 'array', 'items': {'type': 'string'}}, 'runtime-library-dirs': {'type': 'array', 'items': {'type': 'string'}}, 'extra-objects': {'type': 'array', 'items': {'type': 'string'}}, 'extra-compile-args': {'type': 'array', 'items': {'type': 'string'}}, 'extra-link-args': {'type': 'array', 'items': {'type': 'string'}}, 'export-symbols': {'type': 'array', 'items': {'type': 'string'}}, 'swig-opts': {'type': 'array', 'items': {'type': 'string'}}, 'depends': {'type': 'array', 'items': {'type': 'string'}}, 'language': {'type': 'string'}, 'optional': {'type': 'boolean'}, 'py-limited-api': {'type': 'boolean'}}}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_find_directive(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "find" in data_keys:
            data_keys.remove("find")
            data__find = data["find"]
            if not isinstance(data__find, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".find must be object", value=data__find, name="" + (name_prefix or "data") + ".find", definition={'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}, rule='type')
            data__find_is_dict = isinstance(data__find, dict)
            if data__find_is_dict:
                data__find_keys = set(data__find.keys())
                if "where" in data__find_keys:
                    data__find_keys.remove("where")
                    data__find__where = data__find["where"]
                    if not isinstance(data__find__where, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.where must be array", value=data__find__where, name="" + (name_prefix or "data") + ".find.where", definition={'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, rule='type')
                    data__find__where_is_list = isinstance(data__find__where, (list, tuple))
                    if data__find__where_is_list:
                        data__find__where_len = len(data__find__where)
                        for data__find__where_x, data__find__where_item in enumerate(data__find__where):
                            if not isinstance(data__find__where_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.where[{data__find__where_x}]".format(**locals()) + " must be string", value=data__find__where_item, name="" + (name_prefix or "data") + ".find.where[{data__find__where_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if "exclude" in data__find_keys:
                    data__find_keys.remove("exclude")
                    data__find__exclude = data__find["exclude"]
                    if not isinstance(data__find__exclude, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.exclude must be array", value=data__find__exclude, name="" + (name_prefix or "data") + ".find.exclude", definition={'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, rule='type')
                    data__find__exclude_is_list = isinstance(data__find__exclude, (list, tuple))
                    if data__find__exclude_is_list:
                        data__find__exclude_len = len(data__find__exclude)
                        for data__find__exclude_x, data__find__exclude_item in enumerate(data__find__exclude):
                            if not isinstance(data__find__exclude_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.exclude[{data__find__exclude_x}]".format(**locals()) + " must be string", value=data__find__exclude_item, name="" + (name_prefix or "data") + ".find.exclude[{data__find__exclude_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if "include" in data__find_keys:
                    data__find_keys.remove("include")
                    data__find__include = data__find["include"]
                    if not isinstance(data__find__include, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.include must be array", value=data__find__include, name="" + (name_prefix or "data") + ".find.include", definition={'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, rule='type')
                    data__find__include_is_list = isinstance(data__find__include, (list, tuple))
                    if data__find__include_is_list:
                        data__find__include_len = len(data__find__include)
                        for data__find__include_x, data__find__include_item in enumerate(data__find__include):
                            if not isinstance(data__find__include_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.include[{data__find__include_x}]".format(**locals()) + " must be string", value=data__find__include_item, name="" + (name_prefix or "data") + ".find.include[{data__find__include_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
                if "namespaces" in data__find_keys:
                    data__find_keys.remove("namespaces")
                    data__find__namespaces = data__find["namespaces"]
                    if not isinstance(data__find__namespaces, (bool)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".find.namespaces must be boolean", value=data__find__namespaces, name="" + (name_prefix or "data") + ".find.namespaces", definition={'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}, rule='type')
                if data__find_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".find must not contain "+str(data__find_keys)+" properties", value=data__find, name="" + (name_prefix or "data") + ".find", definition={'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}, rule='additionalProperties')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/find-directive', 'title': "'find:' directive", 'type': 'object', 'additionalProperties': False, 'properties': {'find': {'type': 'object', '$$description': ['Dynamic `package discovery', '<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.'], 'additionalProperties': False, 'properties': {'where': {'description': 'Directories to be searched for packages (Unix-style relative path)', 'type': 'array', 'items': {'type': 'string'}}, 'exclude': {'type': 'array', '$$description': ['Exclude packages that match the values listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'include': {'type': 'array', '$$description': ['Restrict the found packages to just the ones listed in this field.', "Can container shell-style wildcards (e.g. ``'pkg.*'``)"], 'items': {'type': 'string'}}, 'namespaces': {'type': 'boolean', '$$description': ['When ``True``, directories without a ``__init__.py`` file will also', 'be scanned for :pep:`420`-style implicit namespaces']}}}}}, rule='additionalProperties')
    return data

def validate_https___setuptools_pypa_io_en_latest_userguide_pyproject_config_html__definitions_package_name(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, rule='type')
    data_any_of_count11 = 0
    if not data_any_of_count11:
        try:
            if not isinstance(data, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='type')
            if isinstance(data, str):
                if not custom_formats["python-module-name-relaxed"](data):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + " must be python-module-name-relaxed", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'string', 'format': 'python-module-name-relaxed'}, rule='format')
            data_any_of_count11 += 1
        except JsonSchemaValueException: pass
    if not data_any_of_count11:
        try:
            if not isinstance(data, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'string', 'format': 'pep561-stub-name'}, rule='type')
            if isinstance(data, str):
                if not custom_formats["pep561-stub-name"](data):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + " must be pep561-stub-name", value=data, name="" + (name_prefix or "data") + "", definition={'type': 'string', 'format': 'pep561-stub-name'}, rule='format')
            data_any_of_count11 += 1
        except JsonSchemaValueException: pass
    if not data_any_of_count11:
        raise JsonSchemaValueException("" + (name_prefix or "data") + " cannot be validated by any definition", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/package-name', 'title': 'Valid package name', 'description': 'Valid package name (importable or :pep:`561`).', 'type': 'string', 'anyOf': [{'type': 'string', 'format': 'python-module-name-relaxed'}, {'type': 'string', 'format': 'pep561-stub-name'}]}, rule='anyOf')
    return data

def validate_https___setuptools_pypa_io_en_latest_deprecated_distutils_configfile_html(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html', 'title': '``tool.distutils`` table', '$$description': ['**EXPERIMENTAL** (NOT OFFICIALLY SUPPORTED): Use ``tool.distutils``', 'subtables to configure arguments for ``distutils`` commands.', 'Originally, ``distutils`` allowed developers to configure arguments for', '``setup.py`` commands via `distutils configuration files', '<https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.', 'See also `the old Python docs <https://docs.python.org/3.11/install/>_`.'], 'type': 'object', 'properties': {'global': {'type': 'object', 'description': 'Global options applied to all ``distutils`` commands'}}, 'patternProperties': {'.+': {'type': 'object'}}, '$comment': 'TODO: Is there a practical way of making this schema more specific?'}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "global" in data_keys:
            data_keys.remove("global")
            data__global = data["global"]
            if not isinstance(data__global, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".global must be object", value=data__global, name="" + (name_prefix or "data") + ".global", definition={'type': 'object', 'description': 'Global options applied to all ``distutils`` commands'}, rule='type')
        for data_key, data_val in data.items():
            if REGEX_PATTERNS['.+'].search(data_key):
                if data_key in data_keys:
                    data_keys.remove(data_key)
                if not isinstance(data_val, (dict)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object", value=data_val, name="" + (name_prefix or "data") + ".{data_key}".format(**locals()) + "", definition={'type': 'object'}, rule='type')
    return data

def validate_https___packaging_python_org_en_latest_specifications_pyproject_toml(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'gui-scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}, rule='type')
    try:
        try:
            data_is_dict = isinstance(data, dict)
            if data_is_dict:
                data__missing_keys = set(['dynamic']) - data.keys()
                if data__missing_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, rule='required')
                data_keys = set(data.keys())
                if "dynamic" in data_keys:
                    data_keys.remove("dynamic")
                    data__dynamic = data["dynamic"]
                    data__dynamic_is_list = isinstance(data__dynamic, (list, tuple))
                    if data__dynamic_is_list:
                        data__dynamic_contains = False
                        for data__dynamic_key in data__dynamic:
                            try:
                                if data__dynamic_key != "version":
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic must be same as const definition: version", value=data__dynamic_key, name="" + (name_prefix or "data") + ".dynamic", definition={'const': 'version'}, rule='const')
                                data__dynamic_contains = True
                                break
                            except JsonSchemaValueException: pass
                        if not data__dynamic_contains:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic must contain one of contains definition", value=data__dynamic, name="" + (name_prefix or "data") + ".dynamic", definition={'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}, rule='contains')
        except JsonSchemaValueException: pass
        else:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must NOT match a disallowed definition", value=data, name="" + (name_prefix or "data") + "", definition={'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, rule='not')
    except JsonSchemaValueException:
        pass
    else:
        data_is_dict = isinstance(data, dict)
        if data_is_dict:
            data__missing_keys = set(['version']) - data.keys()
            if data__missing_keys:
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}, rule='required')
    try:
        data_is_dict = isinstance(data, dict)
        if data_is_dict:
            data__missing_keys = set(['license-files']) - data.keys()
            if data__missing_keys:
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'required': ['license-files']}, rule='required')
    except JsonSchemaValueException:
        pass
    else:
        data_is_dict = isinstance(data, dict)
        if data_is_dict:
            data_keys = set(data.keys())
            if "license" in data_keys:
                data_keys.remove("license")
                data__license = data["license"]
                if not isinstance(data__license, (str)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be string", value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'string'}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + (str(sorted(data__missing_keys)) + " properties"), value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'gui-scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}, rule='required')
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string", value=data__name, name="" + (name_prefix or "data") + ".name", definition={'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, rule='type')
            if isinstance(data__name, str):
                if not custom_formats["pep508-identifier"](data__name):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be pep508-identifier", value=data__name, name="" + (name_prefix or "data") + ".name", definition={'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, rule='format')
        if "version" in data_keys:
            data_keys.remove("version")
            data__version = data["version"]
            if not isinstance(data__version, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".version must be string", value=data__version, name="" + (name_prefix or "data") + ".version", definition={'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, rule='type')
            if isinstance(data__version, str):
                if not custom_formats["pep440"](data__version):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".version must be pep440", value=data__version, name="" + (name_prefix or "data") + ".version", definition={'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, rule='format')
        if "description" in data_keys:
            data_keys.remove("description")
            data__description = data["description"]
            if not isinstance(data__description, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".description must be string", value=data__description, name="" + (name_prefix or "data") + ".description", definition={'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, rule='type')
        if "readme" in data_keys:
            data_keys.remove("readme")
            data__readme = data["readme"]
            data__readme_one_of_count12 = 0
            if data__readme_one_of_count12 < 2:
                try:
                    if not isinstance(data__readme, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must be string", value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, rule='type')
                    data__readme_one_of_count12 += 1
                except JsonSchemaValueException: pass
            if data__readme_one_of_count12 < 2:
                try:
                    if not isinstance(data__readme, (dict)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must be object", value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}, rule='type')
                    data__readme_any_of_count13 = 0
                    if not data__readme_any_of_count13:
                        try:
                            data__readme_is_dict = isinstance(data__readme, dict)
                            if data__readme_is_dict:
                                data__readme__missing_keys = set(['file']) - data__readme.keys()
                                if data__readme__missing_keys:
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must contain " + (str(sorted(data__readme__missing_keys)) + " properties"), value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, rule='required')
                                data__readme_keys = set(data__readme.keys())
                                if "file" in data__readme_keys:
                                    data__readme_keys.remove("file")
                                    data__readme__file = data__readme["file"]
                                    if not isinstance(data__readme__file, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme.file must be string", value=data__readme__file, name="" + (name_prefix or "data") + ".readme.file", definition={'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}, rule='type')
                            data__readme_any_of_count13 += 1
                        except JsonSchemaValueException: pass
                    if not data__readme_any_of_count13:
                        try:
                            data__readme_is_dict = isinstance(data__readme, dict)
                            if data__readme_is_dict:
                                data__readme__missing_keys = set(['text']) - data__readme.keys()
                                if data__readme__missing_keys:
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must contain " + (str(sorted(data__readme__missing_keys)) + " properties"), value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}, rule='required')
                                data__readme_keys = set(data__readme.keys())
                                if "text" in data__readme_keys:
                                    data__readme_keys.remove("text")
                                    data__readme__text = data__readme["text"]
                                    if not isinstance(data__readme__text, (str)):
                                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme.text must be string", value=data__readme__text, name="" + (name_prefix or "data") + ".readme.text", definition={'type': 'string', 'description': 'Full text describing the project.'}, rule='type')
                            data__readme_any_of_count13 += 1
                        except JsonSchemaValueException: pass
                    if not data__readme_any_of_count13:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme cannot be validated by any definition", value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, rule='anyOf')
                    data__readme_is_dict = isinstance(data__readme, dict)
                    if data__readme_is_dict:
                        data__readme__missing_keys = set(['content-type']) - data__readme.keys()
                        if data__readme__missing_keys:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must contain " + (str(sorted(data__readme__missing_keys)) + " properties"), value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}, rule='required')
                        data__readme_keys = set(data__readme.keys())
                        if "content-type" in data__readme_keys:
                            data__readme_keys.remove("content-type")
                            data__readme__contenttype = data__readme["content-type"]
                            if not isinstance(data__readme__contenttype, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme.content-type must be string", value=data__readme__contenttype, name="" + (name_prefix or "data") + ".readme.content-type", definition={'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}, rule='type')
                    data__readme_one_of_count12 += 1
                except JsonSchemaValueException: pass
            if data__readme_one_of_count12 != 1:
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".readme must be valid exactly by one definition" + (" (" + str(data__readme_one_of_count12) + " matches found)"), value=data__readme, name="" + (name_prefix or "data") + ".readme", definition={'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, rule='oneOf')
        if "requires-python" in data_keys:
            data_keys.remove("requires-python")
            data__requirespython = data["requires-python"]
            if not isinstance(data__requirespython, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".requires-python must be string", value=data__requirespython, name="" + (name_prefix or "data") + ".requires-python", definition={'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, rule='type')
            if isinstance(data__requirespython, str):
                if not custom_formats["pep508-versionspec"](data__requirespython):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".requires-python must be pep508-versionspec", value=data__requirespython, name="" + (name_prefix or "data") + ".requires-python", definition={'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, rule='format')
        if "license" in data_keys:
            data_keys.remove("license")
            data__license = data["license"]
            data__license_one_of_count14 = 0
            if data__license_one_of_count14 < 2:
                try:
                    if not isinstance(data__license, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be string", value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, rule='type')
                    if isinstance(data__license, str):
                        if not custom_formats["SPDX"](data__license):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be SPDX", value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, rule='format')
                    data__license_one_of_count14 += 1
                except JsonSchemaValueException: pass
            if data__license_one_of_count14 < 2:
                try:
                    if not isinstance(data__license, (dict)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be object", value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, rule='type')
                    data__license_is_dict = isinstance(data__license, dict)
                    if data__license_is_dict:
                        data__license__missing_keys = set(['file']) - data__license.keys()
                        if data__license__missing_keys:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must contain " + (str(sorted(data__license__missing_keys)) + " properties"), value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, rule='required')
                        data__license_keys = set(data__license.keys())
                        if "file" in data__license_keys:
                            data__license_keys.remove("file")
                            data__license__file = data__license["file"]
                            if not isinstance(data__license__file, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".license.file must be string", value=data__license__file, name="" + (name_prefix or "data") + ".license.file", definition={'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}, rule='type')
                    data__license_one_of_count14 += 1
                except JsonSchemaValueException: pass
            if data__license_one_of_count14 < 2:
                try:
                    if not isinstance(data__license, (dict)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be object", value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}, rule='type')
                    data__license_is_dict = isinstance(data__license, dict)
                    if data__license_is_dict:
                        data__license__missing_keys = set(['text']) - data__license.keys()
                        if data__license__missing_keys:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must contain " + (str(sorted(data__license__missing_keys)) + " properties"), value=data__license, name="" + (name_prefix or "data") + ".license", definition={'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}, rule='required')
                        data__license_keys = set(data__license.keys())
                        if "text" in data__license_keys:
                            data__license_keys.remove("text")
                            data__license__text = data__license["text"]
                            if not isinstance(data__license__text, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".license.text must be string", value=data__license__text, name="" + (name_prefix or "data") + ".license.text", definition={'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}, rule='type')
                    data__license_one_of_count14 += 1
                except JsonSchemaValueException: pass
            if data__license_one_of_count14 != 1:
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".license must be valid exactly by one definition" + (" (" + str(data__license_one_of_count14) + " matches found)"), value=data__license, name="" + (name_prefix or "data") + ".license", definition={'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, rule='oneOf')
        if "license-files" in data_keys:
            data_keys.remove("license-files")
            data__licensefiles = data["license-files"]
            if not isinstance(data__licensefiles, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".license-files must be array", value=data__licensefiles, name="" + (name_prefix or "data") + ".license-files", definition={'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, rule='type')
            data__licensefiles_is_list = isinstance(data__licensefiles, (list, tuple))
            if data__licensefiles_is_list:
                data__licensefiles_len = len(data__licensefiles)
                for data__licensefiles_x, data__licensefiles_item in enumerate(data__licensefiles):
                    if not isinstance(data__licensefiles_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".license-files[{data__licensefiles_x}]".format(**locals()) + " must be string", value=data__licensefiles_item, name="" + (name_prefix or "data") + ".license-files[{data__licensefiles_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "authors" in data_keys:
            data_keys.remove("authors")
            data__authors = data["authors"]
            if not isinstance(data__authors, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".authors must be array", value=data__authors, name="" + (name_prefix or "data") + ".authors", definition={'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, rule='type')
            data__authors_is_list = isinstance(data__authors, (list, tuple))
            if data__authors_is_list:
                data__authors_len = len(data__authors)
                for data__authors_x, data__authors_item in enumerate(data__authors):
                    validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_author(data__authors_item, custom_formats, (name_prefix or "data") + ".authors[{data__authors_x}]".format(**locals()))
        if "maintainers" in data_keys:
            data_keys.remove("maintainers")
            data__maintainers = data["maintainers"]
            if not isinstance(data__maintainers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".maintainers must be array", value=data__maintainers, name="" + (name_prefix or "data") + ".maintainers", definition={'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, rule='type')
            data__maintainers_is_list = isinstance(data__maintainers, (list, tuple))
            if data__maintainers_is_list:
                data__maintainers_len = len(data__maintainers)
                for data__maintainers_x, data__maintainers_item in enumerate(data__maintainers):
                    validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_author(data__maintainers_item, custom_formats, (name_prefix or "data") + ".maintainers[{data__maintainers_x}]".format(**locals()))
        if "keywords" in data_keys:
            data_keys.remove("keywords")
            data__keywords = data["keywords"]
            if not isinstance(data__keywords, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".keywords must be array", value=data__keywords, name="" + (name_prefix or "data") + ".keywords", definition={'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, rule='type')
            data__keywords_is_list = isinstance(data__keywords, (list, tuple))
            if data__keywords_is_list:
                data__keywords_len = len(data__keywords)
                for data__keywords_x, data__keywords_item in enumerate(data__keywords):
                    if not isinstance(data__keywords_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".keywords[{data__keywords_x}]".format(**locals()) + " must be string", value=data__keywords_item, name="" + (name_prefix or "data") + ".keywords[{data__keywords_x}]".format(**locals()) + "", definition={'type': 'string'}, rule='type')
        if "classifiers" in data_keys:
            data_keys.remove("classifiers")
            data__classifiers = data["classifiers"]
            if not isinstance(data__classifiers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".classifiers must be array", value=data__classifiers, name="" + (name_prefix or "data") + ".classifiers", definition={'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, rule='type')
            data__classifiers_is_list = isinstance(data__classifiers, (list, tuple))
            if data__classifiers_is_list:
                data__classifiers_len = len(data__classifiers)
                for data__classifiers_x, data__classifiers_item in enumerate(data__classifiers):
                    if not isinstance(data__classifiers_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".classifiers[{data__classifiers_x}]".format(**locals()) + " must be string", value=data__classifiers_item, name="" + (name_prefix or "data") + ".classifiers[{data__classifiers_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, rule='type')
                    if isinstance(data__classifiers_item, str):
                        if not custom_formats["trove-classifier"](data__classifiers_item):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".classifiers[{data__classifiers_x}]".format(**locals()) + " must be trove-classifier", value=data__classifiers_item, name="" + (name_prefix or "data") + ".classifiers[{data__classifiers_x}]".format(**locals()) + "", definition={'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, rule='format')
        if "urls" in data_keys:
            data_keys.remove("urls")
            data__urls = data["urls"]
            if not isinstance(data__urls, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".urls must be object", value=data__urls, name="" + (name_prefix or "data") + ".urls", definition={'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, rule='type')
            data__urls_is_dict = isinstance(data__urls, dict)
            if data__urls_is_dict:
                data__urls_keys = set(data__urls.keys())
                for data__urls_key, data__urls_val in data__urls.items():
                    if REGEX_PATTERNS['^.+$'].search(data__urls_key):
                        if data__urls_key in data__urls_keys:
                            data__urls_keys.remove(data__urls_key)
                        if not isinstance(data__urls_val, (str)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".urls.{data__urls_key}".format(**locals()) + " must be string", value=data__urls_val, name="" + (name_prefix or "data") + ".urls.{data__urls_key}".format(**locals()) + "", definition={'type': 'string', 'format': 'url'}, rule='type')
                        if isinstance(data__urls_val, str):
                            if not custom_formats["url"](data__urls_val):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".urls.{data__urls_key}".format(**locals()) + " must be url", value=data__urls_val, name="" + (name_prefix or "data") + ".urls.{data__urls_key}".format(**locals()) + "", definition={'type': 'string', 'format': 'url'}, rule='format')
                if data__urls_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".urls must not contain "+str(data__urls_keys)+" properties", value=data__urls, name="" + (name_prefix or "data") + ".urls", definition={'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, rule='additionalProperties')
        if "scripts" in data_keys:
            data_keys.remove("scripts")
            data__scripts = data["scripts"]
            validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_entry_point_group(data__scripts, custom_formats, (name_prefix or "data") + ".scripts")
        if "gui-scripts" in data_keys:
            data_keys.remove("gui-scripts")
            data__guiscripts = data["gui-scripts"]
            validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_entry_point_group(data__guiscripts, custom_formats, (name_prefix or "data") + ".gui-scripts")
        if "entry-points" in data_keys:
            data_keys.remove("entry-points")
            data__entrypoints = data["entry-points"]
            data__entrypoints_is_dict = isinstance(data__entrypoints, dict)
            if data__entrypoints_is_dict:
                data__entrypoints_keys = set(data__entrypoints.keys())
                for data__entrypoints_key, data__entrypoints_val in data__entrypoints.items():
                    if REGEX_PATTERNS['^.+$'].search(data__entrypoints_key):
                        if data__entrypoints_key in data__entrypoints_keys:
                            data__entrypoints_keys.remove(data__entrypoints_key)
                        validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_entry_point_group(data__entrypoints_val, custom_formats, (name_prefix or "data") + ".entry-points.{data__entrypoints_key}".format(**locals()))
                if data__entrypoints_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".entry-points must not contain "+str(data__entrypoints_keys)+" properties", value=data__entrypoints, name="" + (name_prefix or "data") + ".entry-points", definition={'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}}}, rule='additionalProperties')
                data__entrypoints_len = len(data__entrypoints)
                if data__entrypoints_len != 0:
                    data__entrypoints_property_names = True
                    for data__entrypoints_key in data__entrypoints:
                        try:
                            if isinstance(data__entrypoints_key, str):
                                if not custom_formats["python-entrypoint-group"](data__entrypoints_key):
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".entry-points must be python-entrypoint-group", value=data__entrypoints_key, name="" + (name_prefix or "data") + ".entry-points", definition={'format': 'python-entrypoint-group'}, rule='format')
                        except JsonSchemaValueException:
                            data__entrypoints_property_names = False
                    if not data__entrypoints_property_names:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".entry-points must be named by propertyName definition", value=data__entrypoints, name="" + (name_prefix or "data") + ".entry-points", definition={'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}}}, rule='propertyNames')
        if "dependencies" in data_keys:
            data_keys.remove("dependencies")
            data__dependencies = data["dependencies"]
            if not isinstance(data__dependencies, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dependencies must be array", value=data__dependencies, name="" + (name_prefix or "data") + ".dependencies", definition={'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}, rule='type')
            data__dependencies_is_list = isinstance(data__dependencies, (list, tuple))
            if data__dependencies_is_list:
                data__dependencies_len = len(data__dependencies)
                for data__dependencies_x, data__dependencies_item in enumerate(data__dependencies):
                    validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_dependency(data__dependencies_item, custom_formats, (name_prefix or "data") + ".dependencies[{data__dependencies_x}]".format(**locals()))
        if "optional-dependencies" in data_keys:
            data_keys.remove("optional-dependencies")
            data__optionaldependencies = data["optional-dependencies"]
            if not isinstance(data__optionaldependencies, (dict)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional-dependencies must be object", value=data__optionaldependencies, name="" + (name_prefix or "data") + ".optional-dependencies", definition={'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, rule='type')
            data__optionaldependencies_is_dict = isinstance(data__optionaldependencies, dict)
            if data__optionaldependencies_is_dict:
                data__optionaldependencies_keys = set(data__optionaldependencies.keys())
                for data__optionaldependencies_key, data__optionaldependencies_val in data__optionaldependencies.items():
                    if REGEX_PATTERNS['^.+$'].search(data__optionaldependencies_key):
                        if data__optionaldependencies_key in data__optionaldependencies_keys:
                            data__optionaldependencies_keys.remove(data__optionaldependencies_key)
                        if not isinstance(data__optionaldependencies_val, (list, tuple)):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional-dependencies.{data__optionaldependencies_key}".format(**locals()) + " must be array", value=data__optionaldependencies_val, name="" + (name_prefix or "data") + ".optional-dependencies.{data__optionaldependencies_key}".format(**locals()) + "", definition={'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}, rule='type')
                        data__optionaldependencies_val_is_list = isinstance(data__optionaldependencies_val, (list, tuple))
                        if data__optionaldependencies_val_is_list:
                            data__optionaldependencies_val_len = len(data__optionaldependencies_val)
                            for data__optionaldependencies_val_x, data__optionaldependencies_val_item in enumerate(data__optionaldependencies_val):
                                validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_dependency(data__optionaldependencies_val_item, custom_formats, (name_prefix or "data") + ".optional-dependencies.{data__optionaldependencies_key}[{data__optionaldependencies_val_x}]".format(**locals()))
                if data__optionaldependencies_keys:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional-dependencies must not contain "+str(data__optionaldependencies_keys)+" properties", value=data__optionaldependencies, name="" + (name_prefix or "data") + ".optional-dependencies", definition={'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, rule='additionalProperties')
                data__optionaldependencies_len = len(data__optionaldependencies)
                if data__optionaldependencies_len != 0:
                    data__optionaldependencies_property_names = True
                    for data__optionaldependencies_key in data__optionaldependencies:
                        try:
                            if isinstance(data__optionaldependencies_key, str):
                                if not custom_formats["pep508-identifier"](data__optionaldependencies_key):
                                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional-dependencies must be pep508-identifier", value=data__optionaldependencies_key, name="" + (name_prefix or "data") + ".optional-dependencies", definition={'format': 'pep508-identifier'}, rule='format')
                        except JsonSchemaValueException:
                            data__optionaldependencies_property_names = False
                    if not data__optionaldependencies_property_names:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".optional-dependencies must be named by propertyName definition", value=data__optionaldependencies, name="" + (name_prefix or "data") + ".optional-dependencies", definition={'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, rule='propertyNames')
        if "dynamic" in data_keys:
            data_keys.remove("dynamic")
            data__dynamic = data["dynamic"]
            if not isinstance(data__dynamic, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic must be array", value=data__dynamic, name="" + (name_prefix or "data") + ".dynamic", definition={'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}, rule='type')
            data__dynamic_is_list = isinstance(data__dynamic, (list, tuple))
            if data__dynamic_is_list:
                data__dynamic_len = len(data__dynamic)
                for data__dynamic_x, data__dynamic_item in enumerate(data__dynamic):
                    if data__dynamic_item not in ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']:
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".dynamic[{data__dynamic_x}]".format(**locals()) + " must be one of ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']", value=data__dynamic_item, name="" + (name_prefix or "data") + ".dynamic[{data__dynamic_x}]".format(**locals()) + "", definition={'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}, rule='enum')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$schema': 'http://json-schema.org/draft-07/schema#', '$id': 'https://packaging.python.org/en/latest/specifications/pyproject-toml/', 'title': 'Package metadata stored in the ``project`` table', '$$description': ['Data structure for the **project** table inside ``pyproject.toml``', '(as initially defined in :pep:`621`)'], 'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'The name (primary identifier) of the project. MUST be statically defined.', 'format': 'pep508-identifier'}, 'version': {'type': 'string', 'description': 'The version of the project as supported by :pep:`440`.', 'format': 'pep440'}, 'description': {'type': 'string', '$$description': ['The `summary description of the project', '<https://packaging.python.org/specifications/core-metadata/#summary>`_']}, 'readme': {'$$description': ['`Full/detailed description of the project in the form of a README', '<https://peps.python.org/pep-0621/#readme>`_', "with meaning similar to the one defined in `core metadata's Description", '<https://packaging.python.org/specifications/core-metadata/#description>`_'], 'oneOf': [{'type': 'string', '$$description': ['Relative path to a text file (UTF-8) containing the full description', 'of the project. If the file path ends in case-insensitive ``.md`` or', '``.rst`` suffixes, then the content-type is respectively', '``text/markdown`` or ``text/x-rst``']}, {'type': 'object', 'allOf': [{'anyOf': [{'properties': {'file': {'type': 'string', '$$description': ['Relative path to a text file containing the full description', 'of the project.']}}, 'required': ['file']}, {'properties': {'text': {'type': 'string', 'description': 'Full text describing the project.'}}, 'required': ['text']}]}, {'properties': {'content-type': {'type': 'string', '$$description': ['Content-type (:rfc:`1341`) of the full description', '(e.g. ``text/markdown``). The ``charset`` parameter is assumed', 'UTF-8 when not present.'], '$comment': 'TODO: add regex pattern or format?'}}, 'required': ['content-type']}]}]}, 'requires-python': {'type': 'string', 'format': 'pep508-versionspec', '$$description': ['`The Python version requirements of the project', '<https://packaging.python.org/specifications/core-metadata/#requires-python>`_.']}, 'license': {'description': '`Project license <https://peps.python.org/pep-0621/#license>`_.', 'oneOf': [{'type': 'string', 'description': 'An SPDX license identifier', 'format': 'SPDX'}, {'type': 'object', 'properties': {'file': {'type': 'string', '$$description': ['Relative path to the file (UTF-8) which contains the license for the', 'project.']}}, 'required': ['file']}, {'type': 'object', 'properties': {'text': {'type': 'string', '$$description': ['The license of the project whose meaning is that of the', '`License field from the core metadata', '<https://packaging.python.org/specifications/core-metadata/#license>`_.']}}, 'required': ['text']}]}, 'license-files': {'description': 'Paths or globs to paths of license files', 'type': 'array', 'items': {'type': 'string'}}, 'authors': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'authors' of the project.", 'The exact meaning is open to interpretation (e.g. original or primary authors,', 'current maintainers, or owners of the package).']}, 'maintainers': {'type': 'array', 'items': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, '$$description': ["The people or organizations considered to be the 'maintainers' of the project.", 'Similarly to ``authors``, the exact meaning is open to interpretation.']}, 'keywords': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of keywords to assist searching for the distribution in a larger catalog.'}, 'classifiers': {'type': 'array', 'items': {'type': 'string', 'format': 'trove-classifier', 'description': '`PyPI classifier <https://pypi.org/classifiers/>`_.'}, '$$description': ['`Trove classifiers <https://pypi.org/classifiers/>`_', 'which apply to the project.']}, 'urls': {'type': 'object', 'description': 'URLs associated with the project in the form ``label => value``.', 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', 'format': 'url'}}}, 'scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'gui-scripts': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'entry-points': {'$$description': ['Instruct the installer to expose the given modules/functions via', '``entry-point`` discovery mechanism (useful for plugins).', 'More information available in the `Python packaging guide', '<https://packaging.python.org/specifications/entry-points/>`_.'], 'propertyNames': {'format': 'python-entrypoint-group'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}}}, 'dependencies': {'type': 'array', 'description': 'Project (mandatory) dependencies.', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}, 'optional-dependencies': {'type': 'object', 'description': 'Optional dependency for the project', 'propertyNames': {'format': 'pep508-identifier'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'array', 'items': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}}, 'dynamic': {'type': 'array', '$$description': ['Specifies which fields are intentionally unspecified and expected to be', 'dynamically provided by build tools'], 'items': {'enum': ['version', 'description', 'readme', 'requires-python', 'license', 'license-files', 'authors', 'maintainers', 'keywords', 'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}}}, 'required': ['name'], 'additionalProperties': False, 'allOf': [{'if': {'not': {'required': ['dynamic'], 'properties': {'dynamic': {'contains': {'const': 'version'}, '$$description': ['version is listed in ``dynamic``']}}}, '$$comment': ['According to :pep:`621`:', '    If the core metadata specification lists a field as "Required", then', '    the metadata MUST specify the field statically or list it in dynamic', 'In turn, `core metadata`_ defines:', '    The required fields are: Metadata-Version, Name, Version.', '    All the other fields are optional.', 'Since ``Metadata-Version`` is defined by the build back-end, ``name`` and', '``version`` are the only mandatory information in ``pyproject.toml``.', '.. _core metadata: https://packaging.python.org/specifications/core-metadata/']}, 'then': {'required': ['version'], '$$description': ['version should be statically defined in the ``version`` field']}}, {'if': {'required': ['license-files']}, 'then': {'properties': {'license': {'type': 'string'}}}}], 'definitions': {'author': {'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, 'entry-point-group': {'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, 'dependency': {'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}}}, rule='additionalProperties')
    return data

def validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_dependency(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}, rule='type')
    if isinstance(data, str):
        if not custom_formats["pep508"](data):
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must be pep508", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/dependency', 'title': 'Dependency', 'type': 'string', 'description': 'Project dependency specification according to PEP 508', 'format': 'pep508'}, rule='format')
    return data

def validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_entry_point_group(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        for data_key, data_val in data.items():
            if REGEX_PATTERNS['^.+$'].search(data_key):
                if data_key in data_keys:
                    data_keys.remove(data_key)
                if not isinstance(data_val, (str)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be string", value=data_val, name="" + (name_prefix or "data") + ".{data_key}".format(**locals()) + "", definition={'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}, rule='type')
                if isinstance(data_val, str):
                    if not custom_formats["python-entrypoint-reference"](data_val):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be python-entrypoint-reference", value=data_val, name="" + (name_prefix or "data") + ".{data_key}".format(**locals()) + "", definition={'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}, rule='format')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, rule='additionalProperties')
        data_len = len(data)
        if data_len != 0:
            data_property_names = True
            for data_key in data:
                try:
                    if isinstance(data_key, str):
                        if not custom_formats["python-entrypoint-name"](data_key):
                            raise JsonSchemaValueException("" + (name_prefix or "data") + " must be python-entrypoint-name", value=data_key, name="" + (name_prefix or "data") + "", definition={'format': 'python-entrypoint-name'}, rule='format')
                except JsonSchemaValueException:
                    data_property_names = False
            if not data_property_names:
                raise JsonSchemaValueException("" + (name_prefix or "data") + " must be named by propertyName definition", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/entry-point-group', 'title': 'Entry-points', 'type': 'object', '$$description': ['Entry-points are grouped together to indicate what sort of capabilities they', 'provide.', 'See the `packaging guides', '<https://packaging.python.org/specifications/entry-points/>`_', 'and `setuptools docs', '<https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`_', 'for more information.'], 'propertyNames': {'format': 'python-entrypoint-name'}, 'additionalProperties': False, 'patternProperties': {'^.+$': {'type': 'string', '$$description': ['Reference to a Python object. It is either in the form', '``importable.module``, or ``importable.module:object.attr``.'], 'format': 'python-entrypoint-reference', '$comment': 'https://packaging.python.org/specifications/entry-points/'}}}, rule='propertyNames')
    return data

def validate_https___packaging_python_org_en_latest_specifications_pyproject_toml___definitions_author(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, rule='type')
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string", value=data__name, name="" + (name_prefix or "data") + ".name", definition={'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, rule='type')
        if "email" in data_keys:
            data_keys.remove("email")
            data__email = data["email"]
            if not isinstance(data__email, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".email must be string", value=data__email, name="" + (name_prefix or "data") + ".email", definition={'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}, rule='type')
            if isinstance(data__email, str):
                if not REGEX_PATTERNS["idn-email_re_pattern"].match(data__email):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".email must be idn-email", value=data__email, name="" + (name_prefix or "data") + ".email", definition={'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}, rule='format')
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties", value=data, name="" + (name_prefix or "data") + "", definition={'$id': '#/definitions/author', 'title': 'Author or Maintainer', '$comment': 'https://peps.python.org/pep-0621/#authors-maintainers', 'type': 'object', 'additionalProperties': False, 'properties': {'name': {'type': 'string', '$$description': ['MUST be a valid email name, i.e. whatever can be put as a name, before an', 'email, in :rfc:`822`.']}, 'email': {'type': 'string', 'format': 'idn-email', 'description': 'MUST be a valid email address'}}}, rule='additionalProperties')
    return data

# === NexusCore/openenv\Lib\site-packages\jsonschema\validators.py ===
"""
Creation and extension of validators, with implementations for existing drafts.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from operator import methodcaller
from typing import TYPE_CHECKING
from urllib.parse import unquote, urldefrag, urljoin, urlsplit
from urllib.request import urlopen
from warnings import warn
import contextlib
import json
import reprlib
import warnings

from attrs import define, field, fields
from jsonschema_specifications import REGISTRY as SPECIFICATIONS
from rpds import HashTrieMap
import referencing.exceptions
import referencing.jsonschema

from jsonschema import (
    _format,
    _keywords,
    _legacy_keywords,
    _types,
    _typing,
    _utils,
    exceptions,
)

if TYPE_CHECKING:
    from jsonschema.protocols import Validator

_UNSET = _utils.Unset()

_VALIDATORS: dict[str, Validator] = {}
_META_SCHEMAS = _utils.URIDict()


def __getattr__(name):
    if name == "ErrorTree":
        warnings.warn(
            "Importing ErrorTree from jsonschema.validators is deprecated. "
            "Instead import it from jsonschema.exceptions.",
            DeprecationWarning,
            stacklevel=2,
        )
        from jsonschema.exceptions import ErrorTree
        return ErrorTree
    elif name == "validators":
        warnings.warn(
            "Accessing jsonschema.validators.validators is deprecated. "
            "Use jsonschema.validators.validator_for with a given schema.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _VALIDATORS
    elif name == "meta_schemas":
        warnings.warn(
            "Accessing jsonschema.validators.meta_schemas is deprecated. "
            "Use jsonschema.validators.validator_for with a given schema.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _META_SCHEMAS
    elif name == "RefResolver":
        warnings.warn(
            _RefResolver._DEPRECATION_MESSAGE,
            DeprecationWarning,
            stacklevel=2,
        )
        return _RefResolver
    raise AttributeError(f"module {__name__} has no attribute {name}")


def validates(version):
    """
    Register the decorated validator for a ``version`` of the specification.

    Registered validators and their meta schemas will be considered when
    parsing :kw:`$schema` keywords' URIs.

    Arguments:

        version (str):

            An identifier to use as the version's name

    Returns:

        collections.abc.Callable:

            a class decorator to decorate the validator with the version

    """

    def _validates(cls):
        _VALIDATORS[version] = cls
        meta_schema_id = cls.ID_OF(cls.META_SCHEMA)
        _META_SCHEMAS[meta_schema_id] = cls
        return cls
    return _validates


def _warn_for_remote_retrieve(uri: str):
    from urllib.request import Request, urlopen
    headers = {"User-Agent": "python-jsonschema (deprecated $ref resolution)"}
    request = Request(uri, headers=headers)  # noqa: S310
    with urlopen(request) as response:  # noqa: S310
        warnings.warn(
            "Automatically retrieving remote references can be a security "
            "vulnerability and is discouraged by the JSON Schema "
            "specifications. Relying on this behavior is deprecated "
            "and will shortly become an error. If you are sure you want to "
            "remotely retrieve your reference and that it is safe to do so, "
            "you can find instructions for doing so via referencing.Registry "
            "in the referencing documentation "
            "(https://referencing.readthedocs.org).",
            DeprecationWarning,
            stacklevel=9,  # Ha ha ha ha magic numbers :/
        )
        return referencing.Resource.from_contents(
            json.load(response),
            default_specification=referencing.jsonschema.DRAFT202012,
        )


_REMOTE_WARNING_REGISTRY = SPECIFICATIONS.combine(
    referencing.Registry(retrieve=_warn_for_remote_retrieve),  # type: ignore[call-arg]
)


def create(
    meta_schema: referencing.jsonschema.ObjectSchema,
    validators: (
        Mapping[str, _typing.SchemaKeywordValidator]
        | Iterable[tuple[str, _typing.SchemaKeywordValidator]]
    ) = (),
    version: str | None = None,
    type_checker: _types.TypeChecker = _types.draft202012_type_checker,
    format_checker: _format.FormatChecker = _format.draft202012_format_checker,
    id_of: _typing.id_of = referencing.jsonschema.DRAFT202012.id_of,
    applicable_validators: _typing.ApplicableValidators = methodcaller(
        "items",
    ),
):
    """
    Create a new validator class.

    Arguments:

        meta_schema:

            the meta schema for the new validator class

        validators:

            a mapping from names to callables, where each callable will
            validate the schema property with the given name.

            Each callable should take 4 arguments:

                1. a validator instance,
                2. the value of the property being validated within the
                   instance
                3. the instance
                4. the schema

        version:

            an identifier for the version that this validator class will
            validate. If provided, the returned validator class will
            have its ``__name__`` set to include the version, and also
            will have `jsonschema.validators.validates` automatically
            called for the given version.

        type_checker:

            a type checker, used when applying the :kw:`type` keyword.

            If unprovided, a `jsonschema.TypeChecker` will be created
            with a set of default types typical of JSON Schema drafts.

        format_checker:

            a format checker, used when applying the :kw:`format` keyword.

            If unprovided, a `jsonschema.FormatChecker` will be created
            with a set of default formats typical of JSON Schema drafts.

        id_of:

            A function that given a schema, returns its ID.

        applicable_validators:

            A function that, given a schema, returns the list of
            applicable schema keywords and associated values
            which will be used to validate the instance.
            This is mostly used to support pre-draft 7 versions of JSON Schema
            which specified behavior around ignoring keywords if they were
            siblings of a ``$ref`` keyword. If you're not attempting to
            implement similar behavior, you can typically ignore this argument
            and leave it at its default.

    Returns:

        a new `jsonschema.protocols.Validator` class

    """
    # preemptively don't shadow the `Validator.format_checker` local
    format_checker_arg = format_checker

    specification = referencing.jsonschema.specification_with(
        dialect_id=id_of(meta_schema) or "urn:unknown-dialect",
        default=referencing.Specification.OPAQUE,
    )

    @define
    class Validator:

        VALIDATORS = dict(validators)  # noqa: RUF012
        META_SCHEMA = dict(meta_schema)  # noqa: RUF012
        TYPE_CHECKER = type_checker
        FORMAT_CHECKER = format_checker_arg
        ID_OF = staticmethod(id_of)

        _APPLICABLE_VALIDATORS = applicable_validators
        _validators = field(init=False, repr=False, eq=False)

        schema: referencing.jsonschema.Schema = field(repr=reprlib.repr)
        _ref_resolver = field(default=None, repr=False, alias="resolver")
        format_checker: _format.FormatChecker | None = field(default=None)
        # TODO: include new meta-schemas added at runtime
        _registry: referencing.jsonschema.SchemaRegistry = field(
            default=_REMOTE_WARNING_REGISTRY,
            kw_only=True,
            repr=False,
        )
        _resolver = field(
            alias="_resolver",
            default=None,
            kw_only=True,
            repr=False,
        )

        def __init_subclass__(cls):
            warnings.warn(
                (
                    "Subclassing validator classes is not intended to "
                    "be part of their public API. A future version "
                    "will make doing so an error, as the behavior of "
                    "subclasses isn't guaranteed to stay the same "
                    "between releases of jsonschema. Instead, prefer "
                    "composition of validators, wrapping them in an object "
                    "owned entirely by the downstream library."
                ),
                DeprecationWarning,
                stacklevel=2,
            )

            def evolve(self, **changes):
                cls = self.__class__
                schema = changes.setdefault("schema", self.schema)
                NewValidator = validator_for(schema, default=cls)

                for field in fields(cls):  # noqa: F402
                    if not field.init:
                        continue
                    attr_name = field.name
                    init_name = field.alias
                    if init_name not in changes:
                        changes[init_name] = getattr(self, attr_name)

                return NewValidator(**changes)

            cls.evolve = evolve

        def __attrs_post_init__(self):
            if self._resolver is None:
                registry = self._registry
                if registry is not _REMOTE_WARNING_REGISTRY:
                    registry = SPECIFICATIONS.combine(registry)
                resource = specification.create_resource(self.schema)
                self._resolver = registry.resolver_with_root(resource)

            if self.schema is True or self.schema is False:
                self._validators = []
            else:
                self._validators = [
                    (self.VALIDATORS[k], k, v)
                    for k, v in applicable_validators(self.schema)
                    if k in self.VALIDATORS
                ]

            # REMOVEME: Legacy ref resolution state management.
            push_scope = getattr(self._ref_resolver, "push_scope", None)
            if push_scope is not None:
                id = id_of(self.schema)
                if id is not None:
                    push_scope(id)

        @classmethod
        def check_schema(cls, schema, format_checker=_UNSET):
            Validator = validator_for(cls.META_SCHEMA, default=cls)
            if format_checker is _UNSET:
                format_checker = Validator.FORMAT_CHECKER
            validator = Validator(
                schema=cls.META_SCHEMA,
                format_checker=format_checker,
            )
            for error in validator.iter_errors(schema):
                raise exceptions.SchemaError.create_from(error)

        @property
        def resolver(self):
            warnings.warn(
                (
                    f"Accessing {self.__class__.__name__}.resolver is "
                    "deprecated as of v4.18.0, in favor of the "
                    "https://github.com/python-jsonschema/referencing "
                    "library, which provides more compliant referencing "
                    "behavior as well as more flexible APIs for "
                    "customization."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            if self._ref_resolver is None:
                self._ref_resolver = _RefResolver.from_schema(
                    self.schema,
                    id_of=id_of,
                )
            return self._ref_resolver

        def evolve(self, **changes):
            schema = changes.setdefault("schema", self.schema)
            NewValidator = validator_for(schema, default=self.__class__)

            for (attr_name, init_name) in evolve_fields:
                if init_name not in changes:
                    changes[init_name] = getattr(self, attr_name)

            return NewValidator(**changes)

        def iter_errors(self, instance, _schema=None):
            if _schema is not None:
                warnings.warn(
                    (
                        "Passing a schema to Validator.iter_errors "
                        "is deprecated and will be removed in a future "
                        "release. Call validator.evolve(schema=new_schema)."
                        "iter_errors(...) instead."
                    ),
                    DeprecationWarning,
                    stacklevel=2,
                )
                validators = [
                    (self.VALIDATORS[k], k, v)
                    for k, v in applicable_validators(_schema)
                    if k in self.VALIDATORS
                ]
            else:
                _schema, validators = self.schema, self._validators

            if _schema is True:
                return
            elif _schema is False:
                yield exceptions.ValidationError(
                    f"False schema does not allow {instance!r}",
                    validator=None,
                    validator_value=None,
                    instance=instance,
                    schema=_schema,
                )
                return

            for validator, k, v in validators:
                errors = validator(self, v, instance, _schema) or ()
                for error in errors:
                    # set details if not already set by the called fn
                    error._set(
                        validator=k,
                        validator_value=v,
                        instance=instance,
                        schema=_schema,
                        type_checker=self.TYPE_CHECKER,
                    )
                    if k not in {"if", "$ref"}:
                        error.schema_path.appendleft(k)
                    yield error

        def descend(
            self,
            instance,
            schema,
            path=None,
            schema_path=None,
            resolver=None,
        ):
            if schema is True:
                return
            elif schema is False:
                yield exceptions.ValidationError(
                    f"False schema does not allow {instance!r}",
                    validator=None,
                    validator_value=None,
                    instance=instance,
                    schema=schema,
                )
                return

            if self._ref_resolver is not None:
                evolved = self.evolve(schema=schema)
            else:
                if resolver is None:
                    resolver = self._resolver.in_subresource(
                        specification.create_resource(schema),
                    )
                evolved = self.evolve(schema=schema, _resolver=resolver)

            for k, v in applicable_validators(schema):
                validator = evolved.VALIDATORS.get(k)
                if validator is None:
                    continue

                errors = validator(evolved, v, instance, schema) or ()
                for error in errors:
                    # set details if not already set by the called fn
                    error._set(
                        validator=k,
                        validator_value=v,
                        instance=instance,
                        schema=schema,
                        type_checker=evolved.TYPE_CHECKER,
                    )
                    if k not in {"if", "$ref"}:
                        error.schema_path.appendleft(k)
                    if path is not None:
                        error.path.appendleft(path)
                    if schema_path is not None:
                        error.schema_path.appendleft(schema_path)
                    yield error

        def validate(self, *args, **kwargs):
            for error in self.iter_errors(*args, **kwargs):
                raise error

        def is_type(self, instance, type):
            try:
                return self.TYPE_CHECKER.is_type(instance, type)
            except exceptions.UndefinedTypeCheck:
                exc = exceptions.UnknownType(type, instance, self.schema)
                raise exc from None

        def _validate_reference(self, ref, instance):
            if self._ref_resolver is None:
                try:
                    resolved = self._resolver.lookup(ref)
                except referencing.exceptions.Unresolvable as err:
                    raise exceptions._WrappedReferencingError(err) from err

                return self.descend(
                    instance,
                    resolved.contents,
                    resolver=resolved.resolver,
                )
            else:
                resolve = getattr(self._ref_resolver, "resolve", None)
                if resolve is None:
                    with self._ref_resolver.resolving(ref) as resolved:
                        return self.descend(instance, resolved)
                else:
                    scope, resolved = resolve(ref)
                    self._ref_resolver.push_scope(scope)

                    try:
                        return list(self.descend(instance, resolved))
                    finally:
                        self._ref_resolver.pop_scope()

        def is_valid(self, instance, _schema=None):
            if _schema is not None:
                warnings.warn(
                    (
                        "Passing a schema to Validator.is_valid is deprecated "
                        "and will be removed in a future release. Call "
                        "validator.evolve(schema=new_schema).is_valid(...) "
                        "instead."
                    ),
                    DeprecationWarning,
                    stacklevel=2,
                )
                self = self.evolve(schema=_schema)

            error = next(self.iter_errors(instance), None)
            return error is None

    evolve_fields = [
        (field.name, field.alias)
        for field in fields(Validator)
        if field.init
    ]

    if version is not None:
        safe = version.title().replace(" ", "").replace("-", "")
        Validator.__name__ = Validator.__qualname__ = f"{safe}Validator"
        Validator = validates(version)(Validator)  # type: ignore[misc]

    return Validator


def extend(
    validator,
    validators=(),
    version=None,
    type_checker=None,
    format_checker=None,
):
    """
    Create a new validator class by extending an existing one.

    Arguments:

        validator (jsonschema.protocols.Validator):

            an existing validator class

        validators (collections.abc.Mapping):

            a mapping of new validator callables to extend with, whose
            structure is as in `create`.

            .. note::

                Any validator callables with the same name as an
                existing one will (silently) replace the old validator
                callable entirely, effectively overriding any validation
                done in the "parent" validator class.

                If you wish to instead extend the behavior of a parent's
                validator callable, delegate and call it directly in
                the new validator function by retrieving it using
                ``OldValidator.VALIDATORS["validation_keyword_name"]``.

        version (str):

            a version for the new validator class

        type_checker (jsonschema.TypeChecker):

            a type checker, used when applying the :kw:`type` keyword.

            If unprovided, the type checker of the extended
            `jsonschema.protocols.Validator` will be carried along.

        format_checker (jsonschema.FormatChecker):

            a format checker, used when applying the :kw:`format` keyword.

            If unprovided, the format checker of the extended
            `jsonschema.protocols.Validator` will be carried along.

    Returns:

        a new `jsonschema.protocols.Validator` class extending the one
        provided

    .. note:: Meta Schemas

        The new validator class will have its parent's meta schema.

        If you wish to change or extend the meta schema in the new
        validator class, modify ``META_SCHEMA`` directly on the returned
        class. Note that no implicit copying is done, so a copy should
        likely be made before modifying it, in order to not affect the
        old validator.

    """
    all_validators = dict(validator.VALIDATORS)
    all_validators.update(validators)

    if type_checker is None:
        type_checker = validator.TYPE_CHECKER
    if format_checker is None:
        format_checker = validator.FORMAT_CHECKER
    return create(
        meta_schema=validator.META_SCHEMA,
        validators=all_validators,
        version=version,
        type_checker=type_checker,
        format_checker=format_checker,
        id_of=validator.ID_OF,
        applicable_validators=validator._APPLICABLE_VALIDATORS,
    )


Draft3Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "http://json-schema.org/draft-03/schema#",
    ),
    validators={
        "$ref": _keywords.ref,
        "additionalItems": _legacy_keywords.additionalItems,
        "additionalProperties": _keywords.additionalProperties,
        "dependencies": _legacy_keywords.dependencies_draft3,
        "disallow": _legacy_keywords.disallow_draft3,
        "divisibleBy": _keywords.multipleOf,
        "enum": _keywords.enum,
        "extends": _legacy_keywords.extends_draft3,
        "format": _keywords.format,
        "items": _legacy_keywords.items_draft3_draft4,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maximum": _legacy_keywords.maximum_draft3_draft4,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minimum": _legacy_keywords.minimum_draft3_draft4,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "properties": _legacy_keywords.properties_draft3,
        "type": _legacy_keywords.type_draft3,
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft3_type_checker,
    format_checker=_format.draft3_format_checker,
    version="draft3",
    id_of=referencing.jsonschema.DRAFT3.id_of,
    applicable_validators=_legacy_keywords.ignore_ref_siblings,
)

Draft4Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "http://json-schema.org/draft-04/schema#",
    ),
    validators={
        "$ref": _keywords.ref,
        "additionalItems": _legacy_keywords.additionalItems,
        "additionalProperties": _keywords.additionalProperties,
        "allOf": _keywords.allOf,
        "anyOf": _keywords.anyOf,
        "dependencies": _legacy_keywords.dependencies_draft4_draft6_draft7,
        "enum": _keywords.enum,
        "format": _keywords.format,
        "items": _legacy_keywords.items_draft3_draft4,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maxProperties": _keywords.maxProperties,
        "maximum": _legacy_keywords.maximum_draft3_draft4,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minProperties": _keywords.minProperties,
        "minimum": _legacy_keywords.minimum_draft3_draft4,
        "multipleOf": _keywords.multipleOf,
        "not": _keywords.not_,
        "oneOf": _keywords.oneOf,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "properties": _keywords.properties,
        "required": _keywords.required,
        "type": _keywords.type,
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft4_type_checker,
    format_checker=_format.draft4_format_checker,
    version="draft4",
    id_of=referencing.jsonschema.DRAFT4.id_of,
    applicable_validators=_legacy_keywords.ignore_ref_siblings,
)

Draft6Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "http://json-schema.org/draft-06/schema#",
    ),
    validators={
        "$ref": _keywords.ref,
        "additionalItems": _legacy_keywords.additionalItems,
        "additionalProperties": _keywords.additionalProperties,
        "allOf": _keywords.allOf,
        "anyOf": _keywords.anyOf,
        "const": _keywords.const,
        "contains": _legacy_keywords.contains_draft6_draft7,
        "dependencies": _legacy_keywords.dependencies_draft4_draft6_draft7,
        "enum": _keywords.enum,
        "exclusiveMaximum": _keywords.exclusiveMaximum,
        "exclusiveMinimum": _keywords.exclusiveMinimum,
        "format": _keywords.format,
        "items": _legacy_keywords.items_draft6_draft7_draft201909,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maxProperties": _keywords.maxProperties,
        "maximum": _keywords.maximum,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minProperties": _keywords.minProperties,
        "minimum": _keywords.minimum,
        "multipleOf": _keywords.multipleOf,
        "not": _keywords.not_,
        "oneOf": _keywords.oneOf,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "properties": _keywords.properties,
        "propertyNames": _keywords.propertyNames,
        "required": _keywords.required,
        "type": _keywords.type,
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft6_type_checker,
    format_checker=_format.draft6_format_checker,
    version="draft6",
    id_of=referencing.jsonschema.DRAFT6.id_of,
    applicable_validators=_legacy_keywords.ignore_ref_siblings,
)

Draft7Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "http://json-schema.org/draft-07/schema#",
    ),
    validators={
        "$ref": _keywords.ref,
        "additionalItems": _legacy_keywords.additionalItems,
        "additionalProperties": _keywords.additionalProperties,
        "allOf": _keywords.allOf,
        "anyOf": _keywords.anyOf,
        "const": _keywords.const,
        "contains": _legacy_keywords.contains_draft6_draft7,
        "dependencies": _legacy_keywords.dependencies_draft4_draft6_draft7,
        "enum": _keywords.enum,
        "exclusiveMaximum": _keywords.exclusiveMaximum,
        "exclusiveMinimum": _keywords.exclusiveMinimum,
        "format": _keywords.format,
        "if": _keywords.if_,
        "items": _legacy_keywords.items_draft6_draft7_draft201909,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maxProperties": _keywords.maxProperties,
        "maximum": _keywords.maximum,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minProperties": _keywords.minProperties,
        "minimum": _keywords.minimum,
        "multipleOf": _keywords.multipleOf,
        "not": _keywords.not_,
        "oneOf": _keywords.oneOf,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "properties": _keywords.properties,
        "propertyNames": _keywords.propertyNames,
        "required": _keywords.required,
        "type": _keywords.type,
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft7_type_checker,
    format_checker=_format.draft7_format_checker,
    version="draft7",
    id_of=referencing.jsonschema.DRAFT7.id_of,
    applicable_validators=_legacy_keywords.ignore_ref_siblings,
)

Draft201909Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "https://json-schema.org/draft/2019-09/schema",
    ),
    validators={
        "$recursiveRef": _legacy_keywords.recursiveRef,
        "$ref": _keywords.ref,
        "additionalItems": _legacy_keywords.additionalItems,
        "additionalProperties": _keywords.additionalProperties,
        "allOf": _keywords.allOf,
        "anyOf": _keywords.anyOf,
        "const": _keywords.const,
        "contains": _keywords.contains,
        "dependentRequired": _keywords.dependentRequired,
        "dependentSchemas": _keywords.dependentSchemas,
        "enum": _keywords.enum,
        "exclusiveMaximum": _keywords.exclusiveMaximum,
        "exclusiveMinimum": _keywords.exclusiveMinimum,
        "format": _keywords.format,
        "if": _keywords.if_,
        "items": _legacy_keywords.items_draft6_draft7_draft201909,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maxProperties": _keywords.maxProperties,
        "maximum": _keywords.maximum,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minProperties": _keywords.minProperties,
        "minimum": _keywords.minimum,
        "multipleOf": _keywords.multipleOf,
        "not": _keywords.not_,
        "oneOf": _keywords.oneOf,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "properties": _keywords.properties,
        "propertyNames": _keywords.propertyNames,
        "required": _keywords.required,
        "type": _keywords.type,
        "unevaluatedItems": _legacy_keywords.unevaluatedItems_draft2019,
        "unevaluatedProperties": (
            _legacy_keywords.unevaluatedProperties_draft2019
        ),
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft201909_type_checker,
    format_checker=_format.draft201909_format_checker,
    version="draft2019-09",
)

Draft202012Validator = create(
    meta_schema=SPECIFICATIONS.contents(
        "https://json-schema.org/draft/2020-12/schema",
    ),
    validators={
        "$dynamicRef": _keywords.dynamicRef,
        "$ref": _keywords.ref,
        "additionalProperties": _keywords.additionalProperties,
        "allOf": _keywords.allOf,
        "anyOf": _keywords.anyOf,
        "const": _keywords.const,
        "contains": _keywords.contains,
        "dependentRequired": _keywords.dependentRequired,
        "dependentSchemas": _keywords.dependentSchemas,
        "enum": _keywords.enum,
        "exclusiveMaximum": _keywords.exclusiveMaximum,
        "exclusiveMinimum": _keywords.exclusiveMinimum,
        "format": _keywords.format,
        "if": _keywords.if_,
        "items": _keywords.items,
        "maxItems": _keywords.maxItems,
        "maxLength": _keywords.maxLength,
        "maxProperties": _keywords.maxProperties,
        "maximum": _keywords.maximum,
        "minItems": _keywords.minItems,
        "minLength": _keywords.minLength,
        "minProperties": _keywords.minProperties,
        "minimum": _keywords.minimum,
        "multipleOf": _keywords.multipleOf,
        "not": _keywords.not_,
        "oneOf": _keywords.oneOf,
        "pattern": _keywords.pattern,
        "patternProperties": _keywords.patternProperties,
        "prefixItems": _keywords.prefixItems,
        "properties": _keywords.properties,
        "propertyNames": _keywords.propertyNames,
        "required": _keywords.required,
        "type": _keywords.type,
        "unevaluatedItems": _keywords.unevaluatedItems,
        "unevaluatedProperties": _keywords.unevaluatedProperties,
        "uniqueItems": _keywords.uniqueItems,
    },
    type_checker=_types.draft202012_type_checker,
    format_checker=_format.draft202012_format_checker,
    version="draft2020-12",
)

_LATEST_VERSION: type[Validator] = Draft202012Validator


class _RefResolver:
    """
    Resolve JSON References.

    Arguments:

        base_uri (str):

            The URI of the referring document

        referrer:

            The actual referring document

        store (dict):

            A mapping from URIs to documents to cache

        cache_remote (bool):

            Whether remote refs should be cached after first resolution

        handlers (dict):

            A mapping from URI schemes to functions that should be used
            to retrieve them

        urljoin_cache (:func:`functools.lru_cache`):

            A cache that will be used for caching the results of joining
            the resolution scope to subscopes.

        remote_cache (:func:`functools.lru_cache`):

            A cache that will be used for caching the results of
            resolved remote URLs.

    Attributes:

        cache_remote (bool):

            Whether remote refs should be cached after first resolution

    .. deprecated:: v4.18.0

        ``RefResolver`` has been deprecated in favor of `referencing`.

    """

    _DEPRECATION_MESSAGE = (
        "jsonschema.RefResolver is deprecated as of v4.18.0, in favor of the "
        "https://github.com/python-jsonschema/referencing library, which "
        "provides more compliant referencing behavior as well as more "
        "flexible APIs for customization. A future release will remove "
        "RefResolver. Please file a feature request (on referencing) if you "
        "are missing an API for the kind of customization you need."
    )

    def __init__(
        self,
        base_uri,
        referrer,
        store=HashTrieMap(),
        cache_remote=True,
        handlers=(),
        urljoin_cache=None,
        remote_cache=None,
    ):
        if urljoin_cache is None:
            urljoin_cache = lru_cache(1024)(urljoin)
        if remote_cache is None:
            remote_cache = lru_cache(1024)(self.resolve_from_url)

        self.referrer = referrer
        self.cache_remote = cache_remote
        self.handlers = dict(handlers)

        self._scopes_stack = [base_uri]

        self.store = _utils.URIDict(
            (uri, each.contents) for uri, each in SPECIFICATIONS.items()
        )
        self.store.update(
            (id, each.META_SCHEMA) for id, each in _META_SCHEMAS.items()
        )
        self.store.update(store)
        self.store.update(
            (schema["$id"], schema)
            for schema in store.values()
            if isinstance(schema, Mapping) and "$id" in schema
        )
        self.store[base_uri] = referrer

        self._urljoin_cache = urljoin_cache
        self._remote_cache = remote_cache

    @classmethod
    def from_schema(  # noqa: D417
        cls,
        schema,
        id_of=referencing.jsonschema.DRAFT202012.id_of,
        *args,
        **kwargs,
    ):
        """
        Construct a resolver from a JSON schema object.

        Arguments:

            schema:

                the referring schema

        Returns:

            `_RefResolver`

        """
        return cls(base_uri=id_of(schema) or "", referrer=schema, *args, **kwargs)  # noqa: B026, E501

    def push_scope(self, scope):
        """
        Enter a given sub-scope.

        Treats further dereferences as being performed underneath the
        given scope.
        """
        self._scopes_stack.append(
            self._urljoin_cache(self.resolution_scope, scope),
        )

    def pop_scope(self):
        """
        Exit the most recent entered scope.

        Treats further dereferences as being performed underneath the
        original scope.

        Don't call this method more times than `push_scope` has been
        called.
        """
        try:
            self._scopes_stack.pop()
        except IndexError:
            raise exceptions._RefResolutionError(
                "Failed to pop the scope from an empty stack. "
                "`pop_scope()` should only be called once for every "
                "`push_scope()`",
            ) from None

    @property
    def resolution_scope(self):
        """
        Retrieve the current resolution scope.
        """
        return self._scopes_stack[-1]

    @property
    def base_uri(self):
        """
        Retrieve the current base URI, not including any fragment.
        """
        uri, _ = urldefrag(self.resolution_scope)
        return uri

    @contextlib.contextmanager
    def in_scope(self, scope):
        """
        Temporarily enter the given scope for the duration of the context.

        .. deprecated:: v4.0.0
        """
        warnings.warn(
            "jsonschema.RefResolver.in_scope is deprecated and will be "
            "removed in a future release.",
            DeprecationWarning,
            stacklevel=3,
        )
        self.push_scope(scope)
        try:
            yield
        finally:
            self.pop_scope()

    @contextlib.contextmanager
    def resolving(self, ref):
        """
        Resolve the given ``ref`` and enter its resolution scope.

        Exits the scope on exit of this context manager.

        Arguments:

            ref (str):

                The reference to resolve

        """
        url, resolved = self.resolve(ref)
        self.push_scope(url)
        try:
            yield resolved
        finally:
            self.pop_scope()

    def _find_in_referrer(self, key):
        return self._get_subschemas_cache()[key]

    @lru_cache  # noqa: B019
    def _get_subschemas_cache(self):
        cache = {key: [] for key in _SUBSCHEMAS_KEYWORDS}
        for keyword, subschema in _search_schema(
            self.referrer, _match_subschema_keywords,
        ):
            cache[keyword].append(subschema)
        return cache

    @lru_cache  # noqa: B019
    def _find_in_subschemas(self, url):
        subschemas = self._get_subschemas_cache()["$id"]
        if not subschemas:
            return None
        uri, fragment = urldefrag(url)
        for subschema in subschemas:
            id = subschema["$id"]
            if not isinstance(id, str):
                continue
            target_uri = self._urljoin_cache(self.resolution_scope, id)
            if target_uri.rstrip("/") == uri.rstrip("/"):
                if fragment:
                    subschema = self.resolve_fragment(subschema, fragment)
                self.store[url] = subschema
                return url, subschema
        return None

    def resolve(self, ref):
        """
        Resolve the given reference.
        """
        url = self._urljoin_cache(self.resolution_scope, ref).rstrip("/")

        match = self._find_in_subschemas(url)
        if match is not None:
            return match

        return url, self._remote_cache(url)

    def resolve_from_url(self, url):
        """
        Resolve the given URL.
        """
        url, fragment = urldefrag(url)
        if not url:
            url = self.base_uri

        try:
            document = self.store[url]
        except KeyError:
            try:
                document = self.resolve_remote(url)
            except Exception as exc:
                raise exceptions._RefResolutionError(exc) from exc

        return self.resolve_fragment(document, fragment)

    def resolve_fragment(self, document, fragment):
        """
        Resolve a ``fragment`` within the referenced ``document``.

        Arguments:

            document:

                The referent document

            fragment (str):

                a URI fragment to resolve within it

        """
        fragment = fragment.lstrip("/")

        if not fragment:
            return document

        if document is self.referrer:
            find = self._find_in_referrer
        else:

            def find(key):
                yield from _search_schema(document, _match_keyword(key))

        for keyword in ["$anchor", "$dynamicAnchor"]:
            for subschema in find(keyword):
                if fragment == subschema[keyword]:
                    return subschema
        for keyword in ["id", "$id"]:
            for subschema in find(keyword):
                if "#" + fragment == subschema[keyword]:
                    return subschema

        # Resolve via path
        parts = unquote(fragment).split("/") if fragment else []
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(document, Sequence):
                try:  # noqa: SIM105
                    part = int(part)
                except ValueError:
                    pass
            try:
                document = document[part]
            except (TypeError, LookupError) as err:
                raise exceptions._RefResolutionError(
                    f"Unresolvable JSON pointer: {fragment!r}",
                ) from err

        return document

    def resolve_remote(self, uri):
        """
        Resolve a remote ``uri``.

        If called directly, does not check the store first, but after
        retrieving the document at the specified URI it will be saved in
        the store if :attr:`cache_remote` is True.

        .. note::

            If the requests_ library is present, ``jsonschema`` will use it to
            request the remote ``uri``, so that the correct encoding is
            detected and used.

            If it isn't, or if the scheme of the ``uri`` is not ``http`` or
            ``https``, UTF-8 is assumed.

        Arguments:

            uri (str):

                The URI to resolve

        Returns:

            The retrieved document

        .. _requests: https://pypi.org/project/requests/

        """
        try:
            import requests
        except ImportError:
            requests = None

        scheme = urlsplit(uri).scheme

        if scheme in self.handlers:
            result = self.handlers[scheme](uri)
        elif scheme in ["http", "https"] and requests:
            # Requests has support for detecting the correct encoding of
            # json over http
            result = requests.get(uri).json()
        else:
            # Otherwise, pass off to urllib and assume utf-8
            with urlopen(uri) as url:  # noqa: S310
                result = json.loads(url.read().decode("utf-8"))

        if self.cache_remote:
            self.store[uri] = result
        return result


_SUBSCHEMAS_KEYWORDS = ("$id", "id", "$anchor", "$dynamicAnchor")


def _match_keyword(keyword):

    def matcher(value):
        if keyword in value:
            yield value

    return matcher


def _match_subschema_keywords(value):
    for keyword in _SUBSCHEMAS_KEYWORDS:
        if keyword in value:
            yield keyword, value


def _search_schema(schema, matcher):
    """Breadth-first search routine."""
    values = deque([schema])
    while values:
        value = values.pop()
        if not isinstance(value, dict):
            continue
        yield from matcher(value)
        values.extendleft(value.values())


def validate(instance, schema, cls=None, *args, **kwargs):  # noqa: D417
    """
    Validate an instance under the given schema.

        >>> validate([2, 3, 4], {"maxItems": 2})
        Traceback (most recent call last):
            ...
        ValidationError: [2, 3, 4] is too long

    :func:`~jsonschema.validators.validate` will first verify that the
    provided schema is itself valid, since not doing so can lead to less
    obvious error messages and fail in less obvious or consistent ways.

    If you know you have a valid schema already, especially
    if you intend to validate multiple instances with
    the same schema, you likely would prefer using the
    `jsonschema.protocols.Validator.validate` method directly on a
    specific validator (e.g. ``Draft202012Validator.validate``).


    Arguments:

        instance:

            The instance to validate

        schema:

            The schema to validate with

        cls (jsonschema.protocols.Validator):

            The class that will be used to validate the instance.

    If the ``cls`` argument is not provided, two things will happen
    in accordance with the specification. First, if the schema has a
    :kw:`$schema` keyword containing a known meta-schema [#]_ then the
    proper validator will be used. The specification recommends that
    all schemas contain :kw:`$schema` properties for this reason. If no
    :kw:`$schema` property is found, the default validator class is the
    latest released draft.

    Any other provided positional and keyword arguments will be passed
    on when instantiating the ``cls``.

    Raises:

        `jsonschema.exceptions.ValidationError`:

            if the instance is invalid

        `jsonschema.exceptions.SchemaError`:

            if the schema itself is invalid

    .. rubric:: Footnotes
    .. [#] known by a validator registered with
        `jsonschema.validators.validates`

    """
    if cls is None:
        cls = validator_for(schema)

    cls.check_schema(schema)
    validator = cls(schema, *args, **kwargs)
    error = exceptions.best_match(validator.iter_errors(instance))
    if error is not None:
        raise error


def validator_for(
    schema,
    default: type[Validator] | _utils.Unset = _UNSET,
) -> type[Validator]:
    """
    Retrieve the validator class appropriate for validating the given schema.

    Uses the :kw:`$schema` keyword that should be present in the given
    schema to look up the appropriate validator class.

    Arguments:

        schema (collections.abc.Mapping or bool):

            the schema to look at

        default:

            the default to return if the appropriate validator class
            cannot be determined.

            If unprovided, the default is to return the latest supported
            draft.

    Examples:

        The :kw:`$schema` JSON Schema keyword will control which validator
        class is returned:

        >>> schema = {
        ...     "$schema": "https://json-schema.org/draft/2020-12/schema",
        ...     "type": "integer",
        ... }
        >>> jsonschema.validators.validator_for(schema)
        <class 'jsonschema.validators.Draft202012Validator'>


        Here, a draft 7 schema instead will return the draft 7 validator:

        >>> schema = {
        ...     "$schema": "http://json-schema.org/draft-07/schema#",
        ...     "type": "integer",
        ... }
        >>> jsonschema.validators.validator_for(schema)
        <class 'jsonschema.validators.Draft7Validator'>


        Schemas with no ``$schema`` keyword will fallback to the default
        argument:

        >>> schema = {"type": "integer"}
        >>> jsonschema.validators.validator_for(
        ...     schema, default=Draft7Validator,
        ... )
        <class 'jsonschema.validators.Draft7Validator'>

        or if none is provided, to the latest version supported.
        Always including the keyword when authoring schemas is highly
        recommended.

    """
    DefaultValidator = _LATEST_VERSION if default is _UNSET else default

    if schema is True or schema is False or "$schema" not in schema:
        return DefaultValidator  # type: ignore[return-value]
    if schema["$schema"] not in _META_SCHEMAS and default is _UNSET:
        warn(
            (
                "The metaschema specified by $schema was not found. "
                "Using the latest draft to validate, but this will raise "
                "an error in the future."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
    return _META_SCHEMAS.get(schema["$schema"], DefaultValidator)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\client.py ===
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

from google.ai.generativelanguage_v1beta.services.permission_service import pagers
from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

from .transports.base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .transports.grpc import PermissionServiceGrpcTransport
from .transports.grpc_asyncio import PermissionServiceGrpcAsyncIOTransport
from .transports.rest import PermissionServiceRestTransport


class PermissionServiceClientMeta(type):
    """Metaclass for the PermissionService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[PermissionServiceTransport]]
    _transport_registry["grpc"] = PermissionServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = PermissionServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = PermissionServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[PermissionServiceTransport]:
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


class PermissionServiceClient(metaclass=PermissionServiceClientMeta):
    """Provides methods for managing permissions to PaLM API
    resources.
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
            PermissionServiceClient: The constructed client.
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
            PermissionServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> PermissionServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            PermissionServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def permission_path(
        tuned_model: str,
        permission: str,
    ) -> str:
        """Returns a fully-qualified permission string."""
        return "tunedModels/{tuned_model}/permissions/{permission}".format(
            tuned_model=tuned_model,
            permission=permission,
        )

    @staticmethod
    def parse_permission_path(path: str) -> Dict[str, str]:
        """Parses a permission path into its component segments."""
        m = re.match(
            r"^tunedModels/(?P<tuned_model>.+?)/permissions/(?P<permission>.+?)$", path
        )
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
            _default_universe = PermissionServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = PermissionServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = PermissionServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = PermissionServiceClient._DEFAULT_UNIVERSE
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

        default_universe = PermissionServiceClient._DEFAULT_UNIVERSE
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
            or PermissionServiceClient._compare_universes(
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
                str,
                PermissionServiceTransport,
                Callable[..., PermissionServiceTransport],
            ]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the permission service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,PermissionServiceTransport,Callable[..., PermissionServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the PermissionServiceTransport constructor.
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
        ) = PermissionServiceClient._read_environment_variables()
        self._client_cert_source = PermissionServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = PermissionServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, PermissionServiceTransport)
        if transport_provided:
            # transport is a PermissionServiceTransport instance.
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
            self._transport = cast(PermissionServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or PermissionServiceClient._get_api_endpoint(
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
                Type[PermissionServiceTransport],
                Callable[..., PermissionServiceTransport],
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., PermissionServiceTransport], transport)
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

    def create_permission(
        self,
        request: Optional[
            Union[permission_service.CreatePermissionRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        permission: Optional[gag_permission.Permission] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Create a permission to a specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreatePermissionRequest(
                    parent="parent_value",
                )

                # Make the request
                response = client.create_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreatePermissionRequest, dict]):
                The request object. Request to create a ``Permission``.
            parent (str):
                Required. The parent resource of the ``Permission``.
                Formats: ``tunedModels/{tuned_model}``
                ``corpora/{corpus}``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            permission (google.ai.generativelanguage_v1beta.types.Permission):
                Required. The permission to create.
                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

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
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, permission])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.CreatePermissionRequest):
            request = permission_service.CreatePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent
            if permission is not None:
                request.permission = permission

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_permission]

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

    def get_permission(
        self,
        request: Optional[Union[permission_service.GetPermissionRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission.Permission:
        r"""Gets information about a specific Permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetPermissionRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetPermissionRequest, dict]):
                The request object. Request for getting information about a specific
                ``Permission``.
            name (str):
                Required. The resource name of the permission.

                Formats:
                ``tunedModels/{tuned_model}/permissions/{permission}``
                ``corpora/{corpus}/permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

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
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

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
        if not isinstance(request, permission_service.GetPermissionRequest):
            request = permission_service.GetPermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_permission]

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

    def list_permissions(
        self,
        request: Optional[
            Union[permission_service.ListPermissionsRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListPermissionsPager:
        r"""Lists permissions for the specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_permissions():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListPermissionsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_permissions(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListPermissionsRequest, dict]):
                The request object. Request for listing permissions.
            parent (str):
                Required. The parent resource of the permissions.
                Formats: ``tunedModels/{tuned_model}``
                ``corpora/{corpus}``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.permission_service.pagers.ListPermissionsPager:
                Response from ListPermissions containing a paginated list of
                   permissions.

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
        if not isinstance(request, permission_service.ListPermissionsRequest):
            request = permission_service.ListPermissionsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if parent is not None:
                request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_permissions]

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
        response = pagers.ListPermissionsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def update_permission(
        self,
        request: Optional[
            Union[permission_service.UpdatePermissionRequest, dict]
        ] = None,
        *,
        permission: Optional[gag_permission.Permission] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Updates the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdatePermissionRequest(
                )

                # Make the request
                response = client.update_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdatePermissionRequest, dict]):
                The request object. Request to update the ``Permission``.
            permission (google.ai.generativelanguage_v1beta.types.Permission):
                Required. The permission to update.

                The permission's ``name`` field is used to identify the
                permission to update.

                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to update. Accepted ones:

                -  role (``Permission.role`` field)

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

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
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([permission, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.UpdatePermissionRequest):
            request = permission_service.UpdatePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if permission is not None:
                request.permission = permission
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_permission]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("permission.name", request.permission.name),)
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

    def delete_permission(
        self,
        request: Optional[
            Union[permission_service.DeletePermissionRequest, dict]
        ] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeletePermissionRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_permission(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeletePermissionRequest, dict]):
                The request object. Request to delete the ``Permission``.
            name (str):
                Required. The resource name of the permission. Formats:
                ``tunedModels/{tuned_model}/permissions/{permission}``
                ``corpora/{corpus}/permissions/{permission}``

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
        if not isinstance(request, permission_service.DeletePermissionRequest):
            request = permission_service.DeletePermissionRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_permission]

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

    def transfer_ownership(
        self,
        request: Optional[
            Union[permission_service.TransferOwnershipRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission_service.TransferOwnershipResponse:
        r"""Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_transfer_ownership():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.TransferOwnershipRequest(
                    name="name_value",
                    email_address="email_address_value",
                )

                # Make the request
                response = client.transfer_ownership(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.TransferOwnershipRequest, dict]):
                The request object. Request to transfer the ownership of
                the tuned model.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TransferOwnershipResponse:
                Response from TransferOwnership.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.TransferOwnershipRequest):
            request = permission_service.TransferOwnershipRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.transfer_ownership]

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

    def __enter__(self) -> "PermissionServiceClient":
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


__all__ = ("PermissionServiceClient",)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distro\distro.py ===
#!/usr/bin/env python
# Copyright 2015-2021 Nir Cohen
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

"""
The ``distro`` package (``distro`` stands for Linux Distribution) provides
information about the Linux distribution it runs on, such as a reliable
machine-readable distro ID, or version information.

It is the recommended replacement for Python's original
:py:func:`platform.linux_distribution` function, but it provides much more
functionality. An alternative implementation became necessary because Python
3.5 deprecated this function, and Python 3.8 removed it altogether. Its
predecessor function :py:func:`platform.dist` was already deprecated since
Python 2.6 and removed in Python 3.8. Still, there are many cases in which
access to OS distribution information is needed. See `Python issue 1322
<https://bugs.python.org/issue1322>`_ for more information.
"""

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
)

try:
    from typing import TypedDict
except ImportError:
    # Python 3.7
    TypedDict = dict

__version__ = "1.9.0"


class VersionDict(TypedDict):
    major: str
    minor: str
    build_number: str


class InfoDict(TypedDict):
    id: str
    version: str
    version_parts: VersionDict
    like: str
    codename: str


_UNIXCONFDIR = os.environ.get("UNIXCONFDIR", "/etc")
_UNIXUSRLIBDIR = os.environ.get("UNIXUSRLIBDIR", "/usr/lib")
_OS_RELEASE_BASENAME = "os-release"

#: Translation table for normalizing the "ID" attribute defined in os-release
#: files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as defined in the os-release file, translated to lower case,
#:   with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_OS_ID = {
    "ol": "oracle",  # Oracle Linux
    "opensuse-leap": "opensuse",  # Newer versions of OpenSuSE report as opensuse-leap
}

#: Translation table for normalizing the "Distributor ID" attribute returned by
#: the lsb_release command, for use by the :func:`distro.id` method.
#:
#: * Key: Value as returned by the lsb_release command, translated to lower
#:   case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_LSB_ID = {
    "enterpriseenterpriseas": "oracle",  # Oracle Enterprise Linux 4
    "enterpriseenterpriseserver": "oracle",  # Oracle Linux 5
    "redhatenterpriseworkstation": "rhel",  # RHEL 6, 7 Workstation
    "redhatenterpriseserver": "rhel",  # RHEL 6, 7 Server
    "redhatenterprisecomputenode": "rhel",  # RHEL 6 ComputeNode
}

#: Translation table for normalizing the distro ID derived from the file name
#: of distro release files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as derived from the file name of a distro release file,
#:   translated to lower case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_DISTRO_ID = {
    "redhat": "rhel",  # RHEL 6.x, 7.x
}

# Pattern for content of distro release file (reversed)
_DISTRO_RELEASE_CONTENT_REVERSED_PATTERN = re.compile(
    r"(?:[^)]*\)(.*)\()? *(?:STL )?([\d.+\-a-z]*\d) *(?:esaeler *)?(.+)"
)

# Pattern for base file name of distro release file
_DISTRO_RELEASE_BASENAME_PATTERN = re.compile(r"(\w+)[-_](release|version)$")

# Base file names to be looked up for if _UNIXCONFDIR is not readable.
_DISTRO_RELEASE_BASENAMES = [
    "SuSE-release",
    "altlinux-release",
    "arch-release",
    "base-release",
    "centos-release",
    "fedora-release",
    "gentoo-release",
    "mageia-release",
    "mandrake-release",
    "mandriva-release",
    "mandrivalinux-release",
    "manjaro-release",
    "oracle-release",
    "redhat-release",
    "rocky-release",
    "sl-release",
    "slackware-version",
]

# Base file names to be ignored when searching for distro release file
_DISTRO_RELEASE_IGNORE_BASENAMES = (
    "debian_version",
    "lsb-release",
    "oem-release",
    _OS_RELEASE_BASENAME,
    "system-release",
    "plesk-release",
    "iredmail-release",
    "board-release",
    "ec2_version",
)


def linux_distribution(full_distribution_name: bool = True) -> Tuple[str, str, str]:
    """
    .. deprecated:: 1.6.0

        :func:`distro.linux_distribution()` is deprecated. It should only be
        used as a compatibility shim with Python's
        :py:func:`platform.linux_distribution()`. Please use :func:`distro.id`,
        :func:`distro.version` and :func:`distro.name` instead.

    Return information about the current OS distribution as a tuple
    ``(id_name, version, codename)`` with items as follows:

    * ``id_name``:  If *full_distribution_name* is false, the result of
      :func:`distro.id`. Otherwise, the result of :func:`distro.name`.

    * ``version``:  The result of :func:`distro.version`.

    * ``codename``:  The extra item (usually in parentheses) after the
      os-release version number, or the result of :func:`distro.codename`.

    The interface of this function is compatible with the original
    :py:func:`platform.linux_distribution` function, supporting a subset of
    its parameters.

    The data it returns may not exactly be the same, because it uses more data
    sources than the original function, and that may lead to different data if
    the OS distribution is not consistent across multiple data sources it
    provides (there are indeed such distributions ...).

    Another reason for differences is the fact that the :func:`distro.id`
    method normalizes the distro ID string to a reliable machine-readable value
    for a number of popular OS distributions.
    """
    warnings.warn(
        "distro.linux_distribution() is deprecated. It should only be used as a "
        "compatibility shim with Python's platform.linux_distribution(). Please use "
        "distro.id(), distro.version() and distro.name() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _distro.linux_distribution(full_distribution_name)


def id() -> str:
    """
    Return the distro ID of the current distribution, as a
    machine-readable string.

    For a number of OS distributions, the returned distro ID value is
    *reliable*, in the sense that it is documented and that it does not change
    across releases of the distribution.

    This package maintains the following reliable distro ID values:

    ==============  =========================================
    Distro ID       Distribution
    ==============  =========================================
    "ubuntu"        Ubuntu
    "debian"        Debian
    "rhel"          RedHat Enterprise Linux
    "centos"        CentOS
    "fedora"        Fedora
    "sles"          SUSE Linux Enterprise Server
    "opensuse"      openSUSE
    "amzn"          Amazon Linux
    "arch"          Arch Linux
    "buildroot"     Buildroot
    "cloudlinux"    CloudLinux OS
    "exherbo"       Exherbo Linux
    "gentoo"        GenToo Linux
    "ibm_powerkvm"  IBM PowerKVM
    "kvmibm"        KVM for IBM z Systems
    "linuxmint"     Linux Mint
    "mageia"        Mageia
    "mandriva"      Mandriva Linux
    "parallels"     Parallels
    "pidora"        Pidora
    "raspbian"      Raspbian
    "oracle"        Oracle Linux (and Oracle Enterprise Linux)
    "scientific"    Scientific Linux
    "slackware"     Slackware
    "xenserver"     XenServer
    "openbsd"       OpenBSD
    "netbsd"        NetBSD
    "freebsd"       FreeBSD
    "midnightbsd"   MidnightBSD
    "rocky"         Rocky Linux
    "aix"           AIX
    "guix"          Guix System
    "altlinux"      ALT Linux
    ==============  =========================================

    If you have a need to get distros for reliable IDs added into this set,
    or if you find that the :func:`distro.id` function returns a different
    distro ID for one of the listed distros, please create an issue in the
    `distro issue tracker`_.

    **Lookup hierarchy and transformations:**

    First, the ID is obtained from the following sources, in the specified
    order. The first available and non-empty value is used:

    * the value of the "ID" attribute of the os-release file,

    * the value of the "Distributor ID" attribute returned by the lsb_release
      command,

    * the first part of the file name of the distro release file,

    The so determined ID value then passes the following transformations,
    before it is returned by this method:

    * it is translated to lower case,

    * blanks (which should not be there anyway) are translated to underscores,

    * a normalization of the ID is performed, based upon
      `normalization tables`_. The purpose of this normalization is to ensure
      that the ID is as reliable as possible, even across incompatible changes
      in the OS distributions. A common reason for an incompatible change is
      the addition of an os-release file, or the addition of the lsb_release
      command, with ID values that differ from what was previously determined
      from the distro release file name.
    """
    return _distro.id()


def name(pretty: bool = False) -> str:
    """
    Return the name of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the name is returned without version or codename.
    (e.g. "CentOS Linux")

    If *pretty* is true, the version and codename are appended.
    (e.g. "CentOS Linux 7.1.1503 (Core)")

    **Lookup hierarchy:**

    The name is obtained from the following sources, in the specified order.
    The first available and non-empty value is used:

    * If *pretty* is false:

      - the value of the "NAME" attribute of the os-release file,

      - the value of the "Distributor ID" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file.

    * If *pretty* is true:

      - the value of the "PRETTY_NAME" attribute of the os-release file,

      - the value of the "Description" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file, appended
        with the value of the pretty version ("<version_id>" and "<codename>"
        fields) of the distro release file, if available.
    """
    return _distro.name(pretty)


def version(pretty: bool = False, best: bool = False) -> str:
    """
    Return the version of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the version is returned without codename (e.g.
    "7.0").

    If *pretty* is true, the codename in parenthesis is appended, if the
    codename is non-empty (e.g. "7.0 (Maipo)").

    Some distributions provide version numbers with different precisions in
    the different sources of distribution information. Examining the different
    sources in a fixed priority order does not always yield the most precise
    version (e.g. for Debian 8.2, or CentOS 7.1).

    Some other distributions may not provide this kind of information. In these
    cases, an empty string would be returned. This behavior can be observed
    with rolling releases distributions (e.g. Arch Linux).

    The *best* parameter can be used to control the approach for the returned
    version:

    If *best* is false, the first non-empty version number in priority order of
    the examined sources is returned.

    If *best* is true, the most precise version number out of all examined
    sources is returned.

    **Lookup hierarchy:**

    In all cases, the version number is obtained from the following sources.
    If *best* is false, this order represents the priority order:

    * the value of the "VERSION_ID" attribute of the os-release file,
    * the value of the "Release" attribute returned by the lsb_release
      command,
    * the version number parsed from the "<version_id>" field of the first line
      of the distro release file,
    * the version number parsed from the "PRETTY_NAME" attribute of the
      os-release file, if it follows the format of the distro release files.
    * the version number parsed from the "Description" attribute returned by
      the lsb_release command, if it follows the format of the distro release
      files.
    """
    return _distro.version(pretty, best)


def version_parts(best: bool = False) -> Tuple[str, str, str]:
    """
    Return the version of the current OS distribution as a tuple
    ``(major, minor, build_number)`` with items as follows:

    * ``major``:  The result of :func:`distro.major_version`.

    * ``minor``:  The result of :func:`distro.minor_version`.

    * ``build_number``:  The result of :func:`distro.build_number`.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.version_parts(best)


def major_version(best: bool = False) -> str:
    """
    Return the major version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The major version is the first
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.major_version(best)


def minor_version(best: bool = False) -> str:
    """
    Return the minor version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The minor version is the second
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.minor_version(best)


def build_number(best: bool = False) -> str:
    """
    Return the build number of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The build number is the third part
    of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.build_number(best)


def like() -> str:
    """
    Return a space-separated list of distro IDs of distributions that are
    closely related to the current OS distribution in regards to packaging
    and programming interfaces, for example distributions the current
    distribution is a derivative from.

    **Lookup hierarchy:**

    This information item is only provided by the os-release file.
    For details, see the description of the "ID_LIKE" attribute in the
    `os-release man page
    <http://www.freedesktop.org/software/systemd/man/os-release.html>`_.
    """
    return _distro.like()


def codename() -> str:
    """
    Return the codename for the release of the current OS distribution,
    as a string.

    If the distribution does not have a codename, an empty string is returned.

    Note that the returned codename is not always really a codename. For
    example, openSUSE returns "x86_64". This function does not handle such
    cases in any special way and just returns the string it finds, if any.

    **Lookup hierarchy:**

    * the codename within the "VERSION" attribute of the os-release file, if
      provided,

    * the value of the "Codename" attribute returned by the lsb_release
      command,

    * the value of the "<codename>" field of the distro release file.
    """
    return _distro.codename()


def info(pretty: bool = False, best: bool = False) -> InfoDict:
    """
    Return certain machine-readable information items about the current OS
    distribution in a dictionary, as shown in the following example:

    .. sourcecode:: python

        {
            'id': 'rhel',
            'version': '7.0',
            'version_parts': {
                'major': '7',
                'minor': '0',
                'build_number': ''
            },
            'like': 'fedora',
            'codename': 'Maipo'
        }

    The dictionary structure and keys are always the same, regardless of which
    information items are available in the underlying data sources. The values
    for the various keys are as follows:

    * ``id``:  The result of :func:`distro.id`.

    * ``version``:  The result of :func:`distro.version`.

    * ``version_parts -> major``:  The result of :func:`distro.major_version`.

    * ``version_parts -> minor``:  The result of :func:`distro.minor_version`.

    * ``version_parts -> build_number``:  The result of
      :func:`distro.build_number`.

    * ``like``:  The result of :func:`distro.like`.

    * ``codename``:  The result of :func:`distro.codename`.

    For a description of the *pretty* and *best* parameters, see the
    :func:`distro.version` method.
    """
    return _distro.info(pretty, best)


def os_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the os-release file data source of the current OS distribution.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_info()


def lsb_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the lsb_release command data source of the current OS distribution.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_info()


def distro_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_info()


def uname_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.
    """
    return _distro.uname_info()


def os_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the os-release file data source
    of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_attr(attribute)


def lsb_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the lsb_release command output
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_attr(attribute)


def distro_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_attr(attribute)


def uname_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
                The empty string, if the item does not exist.
    """
    return _distro.uname_attr(attribute)


try:
    from functools import cached_property
except ImportError:
    # Python < 3.8
    class cached_property:  # type: ignore
        """A version of @property which caches the value.  On access, it calls the
        underlying function and sets the value in `__dict__` so future accesses
        will not re-call the property.
        """

        def __init__(self, f: Callable[[Any], Any]) -> None:
            self._fname = f.__name__
            self._f = f

        def __get__(self, obj: Any, owner: Type[Any]) -> Any:
            assert obj is not None, f"call {self._fname} on an instance"
            ret = obj.__dict__[self._fname] = self._f(obj)
            return ret


class LinuxDistribution:
    """
    Provides information about a OS distribution.

    This package creates a private module-global instance of this class with
    default initialization arguments, that is used by the
    `consolidated accessor functions`_ and `single source accessor functions`_.
    By using default initialization arguments, that module-global instance
    returns data about the current OS distribution (i.e. the distro this
    package runs on).

    Normally, it is not necessary to create additional instances of this class.
    However, in situations where control is needed over the exact data sources
    that are used, instances of this class can be created with a specific
    distro release file, or a specific os-release file, or without invoking the
    lsb_release command.
    """

    def __init__(
        self,
        include_lsb: Optional[bool] = None,
        os_release_file: str = "",
        distro_release_file: str = "",
        include_uname: Optional[bool] = None,
        root_dir: Optional[str] = None,
        include_oslevel: Optional[bool] = None,
    ) -> None:
        """
        The initialization method of this class gathers information from the
        available data sources, and stores that in private instance attributes.
        Subsequent access to the information items uses these private instance
        attributes, so that the data sources are read only once.

        Parameters:

        * ``include_lsb`` (bool): Controls whether the
          `lsb_release command output`_ is included as a data source.

          If the lsb_release command is not available in the program execution
          path, the data source for the lsb_release command will be empty.

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is to be used as a data source.

          An empty string (the default) will cause the default path name to
          be used (see `os-release file`_ for details).

          If the specified or defaulted os-release file does not exist, the
          data source for the os-release file will be empty.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is to be used as a data source.

          An empty string (the default) will cause a default search algorithm
          to be used (see `distro release file`_ for details).

          If the specified distro release file does not exist, or if no default
          distro release file can be found, the data source for the distro
          release file will be empty.

        * ``include_uname`` (bool): Controls whether uname command output is
          included as a data source. If the uname command is not available in
          the program execution path the data source for the uname command will
          be empty.

        * ``root_dir`` (string): The absolute path to the root directory to use
          to find distro-related information files. Note that ``include_*``
          parameters must not be enabled in combination with ``root_dir``.

        * ``include_oslevel`` (bool): Controls whether (AIX) oslevel command
          output is included as a data source. If the oslevel command is not
          available in the program execution path the data source will be
          empty.

        Public instance attributes:

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``include_lsb`` (bool): The result of the ``include_lsb`` parameter.
          This controls whether the lsb information will be loaded.

        * ``include_uname`` (bool): The result of the ``include_uname``
          parameter. This controls whether the uname information will
          be loaded.

        * ``include_oslevel`` (bool): The result of the ``include_oslevel``
          parameter. This controls whether (AIX) oslevel information will be
          loaded.

        * ``root_dir`` (string): The result of the ``root_dir`` parameter.
          The absolute path to the root directory to use to find distro-related
          information files.

        Raises:

        * :py:exc:`ValueError`: Initialization parameters combination is not
           supported.

        * :py:exc:`OSError`: Some I/O issue with an os-release file or distro
          release file.

        * :py:exc:`UnicodeError`: A data source has unexpected characters or
          uses an unexpected encoding.
        """
        self.root_dir = root_dir
        self.etc_dir = os.path.join(root_dir, "etc") if root_dir else _UNIXCONFDIR
        self.usr_lib_dir = (
            os.path.join(root_dir, "usr/lib") if root_dir else _UNIXUSRLIBDIR
        )

        if os_release_file:
            self.os_release_file = os_release_file
        else:
            etc_dir_os_release_file = os.path.join(self.etc_dir, _OS_RELEASE_BASENAME)
            usr_lib_os_release_file = os.path.join(
                self.usr_lib_dir, _OS_RELEASE_BASENAME
            )

            # NOTE: The idea is to respect order **and** have it set
            #       at all times for API backwards compatibility.
            if os.path.isfile(etc_dir_os_release_file) or not os.path.isfile(
                usr_lib_os_release_file
            ):
                self.os_release_file = etc_dir_os_release_file
            else:
                self.os_release_file = usr_lib_os_release_file

        self.distro_release_file = distro_release_file or ""  # updated later

        is_root_dir_defined = root_dir is not None
        if is_root_dir_defined and (include_lsb or include_uname or include_oslevel):
            raise ValueError(
                "Including subprocess data sources from specific root_dir is disallowed"
                " to prevent false information"
            )
        self.include_lsb = (
            include_lsb if include_lsb is not None else not is_root_dir_defined
        )
        self.include_uname = (
            include_uname if include_uname is not None else not is_root_dir_defined
        )
        self.include_oslevel = (
            include_oslevel if include_oslevel is not None else not is_root_dir_defined
        )

    def __repr__(self) -> str:
        """Return repr of all info"""
        return (
            "LinuxDistribution("
            "os_release_file={self.os_release_file!r}, "
            "distro_release_file={self.distro_release_file!r}, "
            "include_lsb={self.include_lsb!r}, "
            "include_uname={self.include_uname!r}, "
            "include_oslevel={self.include_oslevel!r}, "
            "root_dir={self.root_dir!r}, "
            "_os_release_info={self._os_release_info!r}, "
            "_lsb_release_info={self._lsb_release_info!r}, "
            "_distro_release_info={self._distro_release_info!r}, "
            "_uname_info={self._uname_info!r}, "
            "_oslevel_info={self._oslevel_info!r})".format(self=self)
        )

    def linux_distribution(
        self, full_distribution_name: bool = True
    ) -> Tuple[str, str, str]:
        """
        Return information about the OS distribution that is compatible
        with Python's :func:`platform.linux_distribution`, supporting a subset
        of its parameters.

        For details, see :func:`distro.linux_distribution`.
        """
        return (
            self.name() if full_distribution_name else self.id(),
            self.version(),
            self._os_release_info.get("release_codename") or self.codename(),
        )

    def id(self) -> str:
        """Return the distro ID of the OS distribution, as a string.

        For details, see :func:`distro.id`.
        """

        def normalize(distro_id: str, table: Dict[str, str]) -> str:
            distro_id = distro_id.lower().replace(" ", "_")
            return table.get(distro_id, distro_id)

        distro_id = self.os_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_OS_ID)

        distro_id = self.lsb_release_attr("distributor_id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_LSB_ID)

        distro_id = self.distro_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        distro_id = self.uname_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        return ""

    def name(self, pretty: bool = False) -> str:
        """
        Return the name of the OS distribution, as a string.

        For details, see :func:`distro.name`.
        """
        name = (
            self.os_release_attr("name")
            or self.lsb_release_attr("distributor_id")
            or self.distro_release_attr("name")
            or self.uname_attr("name")
        )
        if pretty:
            name = self.os_release_attr("pretty_name") or self.lsb_release_attr(
                "description"
            )
            if not name:
                name = self.distro_release_attr("name") or self.uname_attr("name")
                version = self.version(pretty=True)
                if version:
                    name = f"{name} {version}"
        return name or ""

    def version(self, pretty: bool = False, best: bool = False) -> str:
        """
        Return the version of the OS distribution, as a string.

        For details, see :func:`distro.version`.
        """
        versions = [
            self.os_release_attr("version_id"),
            self.lsb_release_attr("release"),
            self.distro_release_attr("version_id"),
            self._parse_distro_release_content(self.os_release_attr("pretty_name")).get(
                "version_id", ""
            ),
            self._parse_distro_release_content(
                self.lsb_release_attr("description")
            ).get("version_id", ""),
            self.uname_attr("release"),
        ]
        if self.uname_attr("id").startswith("aix"):
            # On AIX platforms, prefer oslevel command output.
            versions.insert(0, self.oslevel_info())
        elif self.id() == "debian" or "debian" in self.like().split():
            # On Debian-like, add debian_version file content to candidates list.
            versions.append(self._debian_version)
        version = ""
        if best:
            # This algorithm uses the last version in priority order that has
            # the best precision. If the versions are not in conflict, that
            # does not matter; otherwise, using the last one instead of the
            # first one might be considered a surprise.
            for v in versions:
                if v.count(".") > version.count(".") or version == "":
                    version = v
        else:
            for v in versions:
                if v != "":
                    version = v
                    break
        if pretty and version and self.codename():
            version = f"{version} ({self.codename()})"
        return version

    def version_parts(self, best: bool = False) -> Tuple[str, str, str]:
        """
        Return the version of the OS distribution, as a tuple of version
        numbers.

        For details, see :func:`distro.version_parts`.
        """
        version_str = self.version(best=best)
        if version_str:
            version_regex = re.compile(r"(\d+)\.?(\d+)?\.?(\d+)?")
            matches = version_regex.match(version_str)
            if matches:
                major, minor, build_number = matches.groups()
                return major, minor or "", build_number or ""
        return "", "", ""

    def major_version(self, best: bool = False) -> str:
        """
        Return the major version number of the current distribution.

        For details, see :func:`distro.major_version`.
        """
        return self.version_parts(best)[0]

    def minor_version(self, best: bool = False) -> str:
        """
        Return the minor version number of the current distribution.

        For details, see :func:`distro.minor_version`.
        """
        return self.version_parts(best)[1]

    def build_number(self, best: bool = False) -> str:
        """
        Return the build number of the current distribution.

        For details, see :func:`distro.build_number`.
        """
        return self.version_parts(best)[2]

    def like(self) -> str:
        """
        Return the IDs of distributions that are like the OS distribution.

        For details, see :func:`distro.like`.
        """
        return self.os_release_attr("id_like") or ""

    def codename(self) -> str:
        """
        Return the codename of the OS distribution.

        For details, see :func:`distro.codename`.
        """
        try:
            # Handle os_release specially since distros might purposefully set
            # this to empty string to have no codename
            return self._os_release_info["codename"]
        except KeyError:
            return (
                self.lsb_release_attr("codename")
                or self.distro_release_attr("codename")
                or ""
            )

    def info(self, pretty: bool = False, best: bool = False) -> InfoDict:
        """
        Return certain machine-readable information about the OS
        distribution.

        For details, see :func:`distro.info`.
        """
        return InfoDict(
            id=self.id(),
            version=self.version(pretty, best),
            version_parts=VersionDict(
                major=self.major_version(best),
                minor=self.minor_version(best),
                build_number=self.build_number(best),
            ),
            like=self.like(),
            codename=self.codename(),
        )

    def os_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the os-release file data source of the OS distribution.

        For details, see :func:`distro.os_release_info`.
        """
        return self._os_release_info

    def lsb_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the lsb_release command data source of the OS
        distribution.

        For details, see :func:`distro.lsb_release_info`.
        """
        return self._lsb_release_info

    def distro_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the distro release file data source of the OS
        distribution.

        For details, see :func:`distro.distro_release_info`.
        """
        return self._distro_release_info

    def uname_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the uname command data source of the OS distribution.

        For details, see :func:`distro.uname_info`.
        """
        return self._uname_info

    def oslevel_info(self) -> str:
        """
        Return AIX' oslevel command output.
        """
        return self._oslevel_info

    def os_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the os-release file data
        source of the OS distribution.

        For details, see :func:`distro.os_release_attr`.
        """
        return self._os_release_info.get(attribute, "")

    def lsb_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the lsb_release command
        output data source of the OS distribution.

        For details, see :func:`distro.lsb_release_attr`.
        """
        return self._lsb_release_info.get(attribute, "")

    def distro_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the distro release file
        data source of the OS distribution.

        For details, see :func:`distro.distro_release_attr`.
        """
        return self._distro_release_info.get(attribute, "")

    def uname_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the uname command
        output data source of the OS distribution.

        For details, see :func:`distro.uname_attr`.
        """
        return self._uname_info.get(attribute, "")

    @cached_property
    def _os_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified os-release file.

        Returns:
            A dictionary containing all information items.
        """
        if os.path.isfile(self.os_release_file):
            with open(self.os_release_file, encoding="utf-8") as release_file:
                return self._parse_os_release_content(release_file)
        return {}

    @staticmethod
    def _parse_os_release_content(lines: TextIO) -> Dict[str, str]:
        """
        Parse the lines of an os-release file.

        Parameters:

        * lines: Iterable through the lines in the os-release file.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        lexer = shlex.shlex(lines, posix=True)
        lexer.whitespace_split = True

        tokens = list(lexer)
        for token in tokens:
            # At this point, all shell-like parsing has been done (i.e.
            # comments processed, quotes and backslash escape sequences
            # processed, multi-line values assembled, trailing newlines
            # stripped, etc.), so the tokens are now either:
            # * variable assignments: var=value
            # * commands or their arguments (not allowed in os-release)
            # Ignore any tokens that are not variable assignments
            if "=" in token:
                k, v = token.split("=", 1)
                props[k.lower()] = v

        if "version" in props:
            # extract release codename (if any) from version attribute
            match = re.search(r"\((\D+)\)|,\s*(\D+)", props["version"])
            if match:
                release_codename = match.group(1) or match.group(2)
                props["codename"] = props["release_codename"] = release_codename

        if "version_codename" in props:
            # os-release added a version_codename field.  Use that in
            # preference to anything else Note that some distros purposefully
            # do not have code names.  They should be setting
            # version_codename=""
            props["codename"] = props["version_codename"]
        elif "ubuntu_codename" in props:
            # Same as above but a non-standard field name used on older Ubuntus
            props["codename"] = props["ubuntu_codename"]

        return props

    @cached_property
    def _lsb_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the lsb_release command output.

        Returns:
            A dictionary containing all information items.
        """
        if not self.include_lsb:
            return {}
        try:
            cmd = ("lsb_release", "-a")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        # Command not found or lsb_release returned error
        except (OSError, subprocess.CalledProcessError):
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_lsb_release_content(content)

    @staticmethod
    def _parse_lsb_release_content(lines: Iterable[str]) -> Dict[str, str]:
        """
        Parse the output of the lsb_release command.

        Parameters:

        * lines: Iterable through the lines of the lsb_release output.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        for line in lines:
            kv = line.strip("\n").split(":", 1)
            if len(kv) != 2:
                # Ignore lines without colon.
                continue
            k, v = kv
            props.update({k.replace(" ", "_").lower(): v.strip()})
        return props

    @cached_property
    def _uname_info(self) -> Dict[str, str]:
        if not self.include_uname:
            return {}
        try:
            cmd = ("uname", "-rs")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        except OSError:
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_uname_content(content)

    @cached_property
    def _oslevel_info(self) -> str:
        if not self.include_oslevel:
            return ""
        try:
            stdout = subprocess.check_output("oslevel", stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return ""
        return self._to_str(stdout).strip()

    @cached_property
    def _debian_version(self) -> str:
        try:
            with open(
                os.path.join(self.etc_dir, "debian_version"), encoding="ascii"
            ) as fp:
                return fp.readline().rstrip()
        except FileNotFoundError:
            return ""

    @staticmethod
    def _parse_uname_content(lines: Sequence[str]) -> Dict[str, str]:
        if not lines:
            return {}
        props = {}
        match = re.search(r"^([^\s]+)\s+([\d\.]+)", lines[0].strip())
        if match:
            name, version = match.groups()

            # This is to prevent the Linux kernel version from
            # appearing as the 'best' version on otherwise
            # identifiable distributions.
            if name == "Linux":
                return {}
            props["id"] = name.lower()
            props["name"] = name
            props["release"] = version
        return props

    @staticmethod
    def _to_str(bytestring: bytes) -> str:
        encoding = sys.getfilesystemencoding()
        return bytestring.decode(encoding)

    @cached_property
    def _distro_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified distro release file.

        Returns:
            A dictionary containing all information items.
        """
        if self.distro_release_file:
            # If it was specified, we use it and parse what we can, even if
            # its file name or content does not match the expected pattern.
            distro_info = self._parse_distro_release_file(self.distro_release_file)
            basename = os.path.basename(self.distro_release_file)
            # The file name pattern for user-specified distro release files
            # is somewhat more tolerant (compared to when searching for the
            # file), because we want to use what was specified as best as
            # possible.
            match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
        else:
            try:
                basenames = [
                    basename
                    for basename in os.listdir(self.etc_dir)
                    if basename not in _DISTRO_RELEASE_IGNORE_BASENAMES
                    and os.path.isfile(os.path.join(self.etc_dir, basename))
                ]
                # We sort for repeatability in cases where there are multiple
                # distro specific files; e.g. CentOS, Oracle, Enterprise all
                # containing `redhat-release` on top of their own.
                basenames.sort()
            except OSError:
                # This may occur when /etc is not readable but we can't be
                # sure about the *-release files. Check common entries of
                # /etc for information. If they turn out to not be there the
                # error is handled in `_parse_distro_release_file()`.
                basenames = _DISTRO_RELEASE_BASENAMES
            for basename in basenames:
                match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
                if match is None:
                    continue
                filepath = os.path.join(self.etc_dir, basename)
                distro_info = self._parse_distro_release_file(filepath)
                # The name is always present if the pattern matches.
                if "name" not in distro_info:
                    continue
                self.distro_release_file = filepath
                break
            else:  # the loop didn't "break": no candidate.
                return {}

        if match is not None:
            distro_info["id"] = match.group(1)

        # CloudLinux < 7: manually enrich info with proper id.
        if "cloudlinux" in distro_info.get("name", "").lower():
            distro_info["id"] = "cloudlinux"

        return distro_info

    def _parse_distro_release_file(self, filepath: str) -> Dict[str, str]:
        """
        Parse a distro release file.

        Parameters:

        * filepath: Path name of the distro release file.

        Returns:
            A dictionary containing all information items.
        """
        try:
            with open(filepath, encoding="utf-8") as fp:
                # Only parse the first line. For instance, on SLES there
                # are multiple lines. We don't want them...
                return self._parse_distro_release_content(fp.readline())
        except OSError:
            # Ignore not being able to read a specific, seemingly version
            # related file.
            # See https://github.com/python-distro/distro/issues/162
            return {}

    @staticmethod
    def _parse_distro_release_content(line: str) -> Dict[str, str]:
        """
        Parse a line from a distro release file.

        Parameters:
        * line: Line from the distro release file. Must be a unicode string
                or a UTF-8 encoded byte string.

        Returns:
            A dictionary containing all information items.
        """
        matches = _DISTRO_RELEASE_CONTENT_REVERSED_PATTERN.match(line.strip()[::-1])
        distro_info = {}
        if matches:
            # regexp ensures non-None
            distro_info["name"] = matches.group(3)[::-1]
            if matches.group(2):
                distro_info["version_id"] = matches.group(2)[::-1]
            if matches.group(1):
                distro_info["codename"] = matches.group(1)[::-1]
        elif line:
            distro_info["name"] = line.strip()
        return distro_info


_distro = LinuxDistribution()


def main() -> None:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    parser = argparse.ArgumentParser(description="OS distro info tool")
    parser.add_argument(
        "--json", "-j", help="Output in machine readable format", action="store_true"
    )

    parser.add_argument(
        "--root-dir",
        "-r",
        type=str,
        dest="root_dir",
        help="Path to the root filesystem directory (defaults to /)",
    )

    args = parser.parse_args()

    if args.root_dir:
        dist = LinuxDistribution(
            include_lsb=False,
            include_uname=False,
            include_oslevel=False,
            root_dir=args.root_dir,
        )
    else:
        dist = _distro

    if args.json:
        logger.info(json.dumps(dist.info(), indent=4, sort_keys=True))
    else:
        logger.info("Name: %s", dist.name(pretty=True))
        distribution_version = dist.version(pretty=True)
        logger.info("Version: %s", distribution_version)
        distribution_codename = dist.codename()
        logger.info("Codename: %s", distribution_codename)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\distro\distro.py ===
#!/usr/bin/env python
# Copyright 2015-2021 Nir Cohen
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

"""
The ``distro`` package (``distro`` stands for Linux Distribution) provides
information about the Linux distribution it runs on, such as a reliable
machine-readable distro ID, or version information.

It is the recommended replacement for Python's original
:py:func:`platform.linux_distribution` function, but it provides much more
functionality. An alternative implementation became necessary because Python
3.5 deprecated this function, and Python 3.8 removed it altogether. Its
predecessor function :py:func:`platform.dist` was already deprecated since
Python 2.6 and removed in Python 3.8. Still, there are many cases in which
access to OS distribution information is needed. See `Python issue 1322
<https://bugs.python.org/issue1322>`_ for more information.
"""

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
)

try:
    from typing import TypedDict
except ImportError:
    # Python 3.7
    TypedDict = dict

__version__ = "1.9.0"


class VersionDict(TypedDict):
    major: str
    minor: str
    build_number: str


class InfoDict(TypedDict):
    id: str
    version: str
    version_parts: VersionDict
    like: str
    codename: str


_UNIXCONFDIR = os.environ.get("UNIXCONFDIR", "/etc")
_UNIXUSRLIBDIR = os.environ.get("UNIXUSRLIBDIR", "/usr/lib")
_OS_RELEASE_BASENAME = "os-release"

#: Translation table for normalizing the "ID" attribute defined in os-release
#: files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as defined in the os-release file, translated to lower case,
#:   with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_OS_ID = {
    "ol": "oracle",  # Oracle Linux
    "opensuse-leap": "opensuse",  # Newer versions of OpenSuSE report as opensuse-leap
}

#: Translation table for normalizing the "Distributor ID" attribute returned by
#: the lsb_release command, for use by the :func:`distro.id` method.
#:
#: * Key: Value as returned by the lsb_release command, translated to lower
#:   case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_LSB_ID = {
    "enterpriseenterpriseas": "oracle",  # Oracle Enterprise Linux 4
    "enterpriseenterpriseserver": "oracle",  # Oracle Linux 5
    "redhatenterpriseworkstation": "rhel",  # RHEL 6, 7 Workstation
    "redhatenterpriseserver": "rhel",  # RHEL 6, 7 Server
    "redhatenterprisecomputenode": "rhel",  # RHEL 6 ComputeNode
}

#: Translation table for normalizing the distro ID derived from the file name
#: of distro release files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as derived from the file name of a distro release file,
#:   translated to lower case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_DISTRO_ID = {
    "redhat": "rhel",  # RHEL 6.x, 7.x
}

# Pattern for content of distro release file (reversed)
_DISTRO_RELEASE_CONTENT_REVERSED_PATTERN = re.compile(
    r"(?:[^)]*\)(.*)\()? *(?:STL )?([\d.+\-a-z]*\d) *(?:esaeler *)?(.+)"
)

# Pattern for base file name of distro release file
_DISTRO_RELEASE_BASENAME_PATTERN = re.compile(r"(\w+)[-_](release|version)$")

# Base file names to be looked up for if _UNIXCONFDIR is not readable.
_DISTRO_RELEASE_BASENAMES = [
    "SuSE-release",
    "altlinux-release",
    "arch-release",
    "base-release",
    "centos-release",
    "fedora-release",
    "gentoo-release",
    "mageia-release",
    "mandrake-release",
    "mandriva-release",
    "mandrivalinux-release",
    "manjaro-release",
    "oracle-release",
    "redhat-release",
    "rocky-release",
    "sl-release",
    "slackware-version",
]

# Base file names to be ignored when searching for distro release file
_DISTRO_RELEASE_IGNORE_BASENAMES = (
    "debian_version",
    "lsb-release",
    "oem-release",
    _OS_RELEASE_BASENAME,
    "system-release",
    "plesk-release",
    "iredmail-release",
    "board-release",
    "ec2_version",
)


def linux_distribution(full_distribution_name: bool = True) -> Tuple[str, str, str]:
    """
    .. deprecated:: 1.6.0

        :func:`distro.linux_distribution()` is deprecated. It should only be
        used as a compatibility shim with Python's
        :py:func:`platform.linux_distribution()`. Please use :func:`distro.id`,
        :func:`distro.version` and :func:`distro.name` instead.

    Return information about the current OS distribution as a tuple
    ``(id_name, version, codename)`` with items as follows:

    * ``id_name``:  If *full_distribution_name* is false, the result of
      :func:`distro.id`. Otherwise, the result of :func:`distro.name`.

    * ``version``:  The result of :func:`distro.version`.

    * ``codename``:  The extra item (usually in parentheses) after the
      os-release version number, or the result of :func:`distro.codename`.

    The interface of this function is compatible with the original
    :py:func:`platform.linux_distribution` function, supporting a subset of
    its parameters.

    The data it returns may not exactly be the same, because it uses more data
    sources than the original function, and that may lead to different data if
    the OS distribution is not consistent across multiple data sources it
    provides (there are indeed such distributions ...).

    Another reason for differences is the fact that the :func:`distro.id`
    method normalizes the distro ID string to a reliable machine-readable value
    for a number of popular OS distributions.
    """
    warnings.warn(
        "distro.linux_distribution() is deprecated. It should only be used as a "
        "compatibility shim with Python's platform.linux_distribution(). Please use "
        "distro.id(), distro.version() and distro.name() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _distro.linux_distribution(full_distribution_name)


def id() -> str:
    """
    Return the distro ID of the current distribution, as a
    machine-readable string.

    For a number of OS distributions, the returned distro ID value is
    *reliable*, in the sense that it is documented and that it does not change
    across releases of the distribution.

    This package maintains the following reliable distro ID values:

    ==============  =========================================
    Distro ID       Distribution
    ==============  =========================================
    "ubuntu"        Ubuntu
    "debian"        Debian
    "rhel"          RedHat Enterprise Linux
    "centos"        CentOS
    "fedora"        Fedora
    "sles"          SUSE Linux Enterprise Server
    "opensuse"      openSUSE
    "amzn"          Amazon Linux
    "arch"          Arch Linux
    "buildroot"     Buildroot
    "cloudlinux"    CloudLinux OS
    "exherbo"       Exherbo Linux
    "gentoo"        GenToo Linux
    "ibm_powerkvm"  IBM PowerKVM
    "kvmibm"        KVM for IBM z Systems
    "linuxmint"     Linux Mint
    "mageia"        Mageia
    "mandriva"      Mandriva Linux
    "parallels"     Parallels
    "pidora"        Pidora
    "raspbian"      Raspbian
    "oracle"        Oracle Linux (and Oracle Enterprise Linux)
    "scientific"    Scientific Linux
    "slackware"     Slackware
    "xenserver"     XenServer
    "openbsd"       OpenBSD
    "netbsd"        NetBSD
    "freebsd"       FreeBSD
    "midnightbsd"   MidnightBSD
    "rocky"         Rocky Linux
    "aix"           AIX
    "guix"          Guix System
    "altlinux"      ALT Linux
    ==============  =========================================

    If you have a need to get distros for reliable IDs added into this set,
    or if you find that the :func:`distro.id` function returns a different
    distro ID for one of the listed distros, please create an issue in the
    `distro issue tracker`_.

    **Lookup hierarchy and transformations:**

    First, the ID is obtained from the following sources, in the specified
    order. The first available and non-empty value is used:

    * the value of the "ID" attribute of the os-release file,

    * the value of the "Distributor ID" attribute returned by the lsb_release
      command,

    * the first part of the file name of the distro release file,

    The so determined ID value then passes the following transformations,
    before it is returned by this method:

    * it is translated to lower case,

    * blanks (which should not be there anyway) are translated to underscores,

    * a normalization of the ID is performed, based upon
      `normalization tables`_. The purpose of this normalization is to ensure
      that the ID is as reliable as possible, even across incompatible changes
      in the OS distributions. A common reason for an incompatible change is
      the addition of an os-release file, or the addition of the lsb_release
      command, with ID values that differ from what was previously determined
      from the distro release file name.
    """
    return _distro.id()


def name(pretty: bool = False) -> str:
    """
    Return the name of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the name is returned without version or codename.
    (e.g. "CentOS Linux")

    If *pretty* is true, the version and codename are appended.
    (e.g. "CentOS Linux 7.1.1503 (Core)")

    **Lookup hierarchy:**

    The name is obtained from the following sources, in the specified order.
    The first available and non-empty value is used:

    * If *pretty* is false:

      - the value of the "NAME" attribute of the os-release file,

      - the value of the "Distributor ID" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file.

    * If *pretty* is true:

      - the value of the "PRETTY_NAME" attribute of the os-release file,

      - the value of the "Description" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file, appended
        with the value of the pretty version ("<version_id>" and "<codename>"
        fields) of the distro release file, if available.
    """
    return _distro.name(pretty)


def version(pretty: bool = False, best: bool = False) -> str:
    """
    Return the version of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the version is returned without codename (e.g.
    "7.0").

    If *pretty* is true, the codename in parenthesis is appended, if the
    codename is non-empty (e.g. "7.0 (Maipo)").

    Some distributions provide version numbers with different precisions in
    the different sources of distribution information. Examining the different
    sources in a fixed priority order does not always yield the most precise
    version (e.g. for Debian 8.2, or CentOS 7.1).

    Some other distributions may not provide this kind of information. In these
    cases, an empty string would be returned. This behavior can be observed
    with rolling releases distributions (e.g. Arch Linux).

    The *best* parameter can be used to control the approach for the returned
    version:

    If *best* is false, the first non-empty version number in priority order of
    the examined sources is returned.

    If *best* is true, the most precise version number out of all examined
    sources is returned.

    **Lookup hierarchy:**

    In all cases, the version number is obtained from the following sources.
    If *best* is false, this order represents the priority order:

    * the value of the "VERSION_ID" attribute of the os-release file,
    * the value of the "Release" attribute returned by the lsb_release
      command,
    * the version number parsed from the "<version_id>" field of the first line
      of the distro release file,
    * the version number parsed from the "PRETTY_NAME" attribute of the
      os-release file, if it follows the format of the distro release files.
    * the version number parsed from the "Description" attribute returned by
      the lsb_release command, if it follows the format of the distro release
      files.
    """
    return _distro.version(pretty, best)


def version_parts(best: bool = False) -> Tuple[str, str, str]:
    """
    Return the version of the current OS distribution as a tuple
    ``(major, minor, build_number)`` with items as follows:

    * ``major``:  The result of :func:`distro.major_version`.

    * ``minor``:  The result of :func:`distro.minor_version`.

    * ``build_number``:  The result of :func:`distro.build_number`.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.version_parts(best)


def major_version(best: bool = False) -> str:
    """
    Return the major version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The major version is the first
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.major_version(best)


def minor_version(best: bool = False) -> str:
    """
    Return the minor version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The minor version is the second
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.minor_version(best)


def build_number(best: bool = False) -> str:
    """
    Return the build number of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The build number is the third part
    of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.build_number(best)


def like() -> str:
    """
    Return a space-separated list of distro IDs of distributions that are
    closely related to the current OS distribution in regards to packaging
    and programming interfaces, for example distributions the current
    distribution is a derivative from.

    **Lookup hierarchy:**

    This information item is only provided by the os-release file.
    For details, see the description of the "ID_LIKE" attribute in the
    `os-release man page
    <http://www.freedesktop.org/software/systemd/man/os-release.html>`_.
    """
    return _distro.like()


def codename() -> str:
    """
    Return the codename for the release of the current OS distribution,
    as a string.

    If the distribution does not have a codename, an empty string is returned.

    Note that the returned codename is not always really a codename. For
    example, openSUSE returns "x86_64". This function does not handle such
    cases in any special way and just returns the string it finds, if any.

    **Lookup hierarchy:**

    * the codename within the "VERSION" attribute of the os-release file, if
      provided,

    * the value of the "Codename" attribute returned by the lsb_release
      command,

    * the value of the "<codename>" field of the distro release file.
    """
    return _distro.codename()


def info(pretty: bool = False, best: bool = False) -> InfoDict:
    """
    Return certain machine-readable information items about the current OS
    distribution in a dictionary, as shown in the following example:

    .. sourcecode:: python

        {
            'id': 'rhel',
            'version': '7.0',
            'version_parts': {
                'major': '7',
                'minor': '0',
                'build_number': ''
            },
            'like': 'fedora',
            'codename': 'Maipo'
        }

    The dictionary structure and keys are always the same, regardless of which
    information items are available in the underlying data sources. The values
    for the various keys are as follows:

    * ``id``:  The result of :func:`distro.id`.

    * ``version``:  The result of :func:`distro.version`.

    * ``version_parts -> major``:  The result of :func:`distro.major_version`.

    * ``version_parts -> minor``:  The result of :func:`distro.minor_version`.

    * ``version_parts -> build_number``:  The result of
      :func:`distro.build_number`.

    * ``like``:  The result of :func:`distro.like`.

    * ``codename``:  The result of :func:`distro.codename`.

    For a description of the *pretty* and *best* parameters, see the
    :func:`distro.version` method.
    """
    return _distro.info(pretty, best)


def os_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the os-release file data source of the current OS distribution.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_info()


def lsb_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the lsb_release command data source of the current OS distribution.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_info()


def distro_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_info()


def uname_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.
    """
    return _distro.uname_info()


def os_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the os-release file data source
    of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_attr(attribute)


def lsb_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the lsb_release command output
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_attr(attribute)


def distro_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_attr(attribute)


def uname_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
                The empty string, if the item does not exist.
    """
    return _distro.uname_attr(attribute)


try:
    from functools import cached_property
except ImportError:
    # Python < 3.8
    class cached_property:  # type: ignore
        """A version of @property which caches the value.  On access, it calls the
        underlying function and sets the value in `__dict__` so future accesses
        will not re-call the property.
        """

        def __init__(self, f: Callable[[Any], Any]) -> None:
            self._fname = f.__name__
            self._f = f

        def __get__(self, obj: Any, owner: Type[Any]) -> Any:
            assert obj is not None, f"call {self._fname} on an instance"
            ret = obj.__dict__[self._fname] = self._f(obj)
            return ret


class LinuxDistribution:
    """
    Provides information about a OS distribution.

    This package creates a private module-global instance of this class with
    default initialization arguments, that is used by the
    `consolidated accessor functions`_ and `single source accessor functions`_.
    By using default initialization arguments, that module-global instance
    returns data about the current OS distribution (i.e. the distro this
    package runs on).

    Normally, it is not necessary to create additional instances of this class.
    However, in situations where control is needed over the exact data sources
    that are used, instances of this class can be created with a specific
    distro release file, or a specific os-release file, or without invoking the
    lsb_release command.
    """

    def __init__(
        self,
        include_lsb: Optional[bool] = None,
        os_release_file: str = "",
        distro_release_file: str = "",
        include_uname: Optional[bool] = None,
        root_dir: Optional[str] = None,
        include_oslevel: Optional[bool] = None,
    ) -> None:
        """
        The initialization method of this class gathers information from the
        available data sources, and stores that in private instance attributes.
        Subsequent access to the information items uses these private instance
        attributes, so that the data sources are read only once.

        Parameters:

        * ``include_lsb`` (bool): Controls whether the
          `lsb_release command output`_ is included as a data source.

          If the lsb_release command is not available in the program execution
          path, the data source for the lsb_release command will be empty.

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is to be used as a data source.

          An empty string (the default) will cause the default path name to
          be used (see `os-release file`_ for details).

          If the specified or defaulted os-release file does not exist, the
          data source for the os-release file will be empty.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is to be used as a data source.

          An empty string (the default) will cause a default search algorithm
          to be used (see `distro release file`_ for details).

          If the specified distro release file does not exist, or if no default
          distro release file can be found, the data source for the distro
          release file will be empty.

        * ``include_uname`` (bool): Controls whether uname command output is
          included as a data source. If the uname command is not available in
          the program execution path the data source for the uname command will
          be empty.

        * ``root_dir`` (string): The absolute path to the root directory to use
          to find distro-related information files. Note that ``include_*``
          parameters must not be enabled in combination with ``root_dir``.

        * ``include_oslevel`` (bool): Controls whether (AIX) oslevel command
          output is included as a data source. If the oslevel command is not
          available in the program execution path the data source will be
          empty.

        Public instance attributes:

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``include_lsb`` (bool): The result of the ``include_lsb`` parameter.
          This controls whether the lsb information will be loaded.

        * ``include_uname`` (bool): The result of the ``include_uname``
          parameter. This controls whether the uname information will
          be loaded.

        * ``include_oslevel`` (bool): The result of the ``include_oslevel``
          parameter. This controls whether (AIX) oslevel information will be
          loaded.

        * ``root_dir`` (string): The result of the ``root_dir`` parameter.
          The absolute path to the root directory to use to find distro-related
          information files.

        Raises:

        * :py:exc:`ValueError`: Initialization parameters combination is not
           supported.

        * :py:exc:`OSError`: Some I/O issue with an os-release file or distro
          release file.

        * :py:exc:`UnicodeError`: A data source has unexpected characters or
          uses an unexpected encoding.
        """
        self.root_dir = root_dir
        self.etc_dir = os.path.join(root_dir, "etc") if root_dir else _UNIXCONFDIR
        self.usr_lib_dir = (
            os.path.join(root_dir, "usr/lib") if root_dir else _UNIXUSRLIBDIR
        )

        if os_release_file:
            self.os_release_file = os_release_file
        else:
            etc_dir_os_release_file = os.path.join(self.etc_dir, _OS_RELEASE_BASENAME)
            usr_lib_os_release_file = os.path.join(
                self.usr_lib_dir, _OS_RELEASE_BASENAME
            )

            # NOTE: The idea is to respect order **and** have it set
            #       at all times for API backwards compatibility.
            if os.path.isfile(etc_dir_os_release_file) or not os.path.isfile(
                usr_lib_os_release_file
            ):
                self.os_release_file = etc_dir_os_release_file
            else:
                self.os_release_file = usr_lib_os_release_file

        self.distro_release_file = distro_release_file or ""  # updated later

        is_root_dir_defined = root_dir is not None
        if is_root_dir_defined and (include_lsb or include_uname or include_oslevel):
            raise ValueError(
                "Including subprocess data sources from specific root_dir is disallowed"
                " to prevent false information"
            )
        self.include_lsb = (
            include_lsb if include_lsb is not None else not is_root_dir_defined
        )
        self.include_uname = (
            include_uname if include_uname is not None else not is_root_dir_defined
        )
        self.include_oslevel = (
            include_oslevel if include_oslevel is not None else not is_root_dir_defined
        )

    def __repr__(self) -> str:
        """Return repr of all info"""
        return (
            "LinuxDistribution("
            "os_release_file={self.os_release_file!r}, "
            "distro_release_file={self.distro_release_file!r}, "
            "include_lsb={self.include_lsb!r}, "
            "include_uname={self.include_uname!r}, "
            "include_oslevel={self.include_oslevel!r}, "
            "root_dir={self.root_dir!r}, "
            "_os_release_info={self._os_release_info!r}, "
            "_lsb_release_info={self._lsb_release_info!r}, "
            "_distro_release_info={self._distro_release_info!r}, "
            "_uname_info={self._uname_info!r}, "
            "_oslevel_info={self._oslevel_info!r})".format(self=self)
        )

    def linux_distribution(
        self, full_distribution_name: bool = True
    ) -> Tuple[str, str, str]:
        """
        Return information about the OS distribution that is compatible
        with Python's :func:`platform.linux_distribution`, supporting a subset
        of its parameters.

        For details, see :func:`distro.linux_distribution`.
        """
        return (
            self.name() if full_distribution_name else self.id(),
            self.version(),
            self._os_release_info.get("release_codename") or self.codename(),
        )

    def id(self) -> str:
        """Return the distro ID of the OS distribution, as a string.

        For details, see :func:`distro.id`.
        """

        def normalize(distro_id: str, table: Dict[str, str]) -> str:
            distro_id = distro_id.lower().replace(" ", "_")
            return table.get(distro_id, distro_id)

        distro_id = self.os_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_OS_ID)

        distro_id = self.lsb_release_attr("distributor_id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_LSB_ID)

        distro_id = self.distro_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        distro_id = self.uname_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        return ""

    def name(self, pretty: bool = False) -> str:
        """
        Return the name of the OS distribution, as a string.

        For details, see :func:`distro.name`.
        """
        name = (
            self.os_release_attr("name")
            or self.lsb_release_attr("distributor_id")
            or self.distro_release_attr("name")
            or self.uname_attr("name")
        )
        if pretty:
            name = self.os_release_attr("pretty_name") or self.lsb_release_attr(
                "description"
            )
            if not name:
                name = self.distro_release_attr("name") or self.uname_attr("name")
                version = self.version(pretty=True)
                if version:
                    name = f"{name} {version}"
        return name or ""

    def version(self, pretty: bool = False, best: bool = False) -> str:
        """
        Return the version of the OS distribution, as a string.

        For details, see :func:`distro.version`.
        """
        versions = [
            self.os_release_attr("version_id"),
            self.lsb_release_attr("release"),
            self.distro_release_attr("version_id"),
            self._parse_distro_release_content(self.os_release_attr("pretty_name")).get(
                "version_id", ""
            ),
            self._parse_distro_release_content(
                self.lsb_release_attr("description")
            ).get("version_id", ""),
            self.uname_attr("release"),
        ]
        if self.uname_attr("id").startswith("aix"):
            # On AIX platforms, prefer oslevel command output.
            versions.insert(0, self.oslevel_info())
        elif self.id() == "debian" or "debian" in self.like().split():
            # On Debian-like, add debian_version file content to candidates list.
            versions.append(self._debian_version)
        version = ""
        if best:
            # This algorithm uses the last version in priority order that has
            # the best precision. If the versions are not in conflict, that
            # does not matter; otherwise, using the last one instead of the
            # first one might be considered a surprise.
            for v in versions:
                if v.count(".") > version.count(".") or version == "":
                    version = v
        else:
            for v in versions:
                if v != "":
                    version = v
                    break
        if pretty and version and self.codename():
            version = f"{version} ({self.codename()})"
        return version

    def version_parts(self, best: bool = False) -> Tuple[str, str, str]:
        """
        Return the version of the OS distribution, as a tuple of version
        numbers.

        For details, see :func:`distro.version_parts`.
        """
        version_str = self.version(best=best)
        if version_str:
            version_regex = re.compile(r"(\d+)\.?(\d+)?\.?(\d+)?")
            matches = version_regex.match(version_str)
            if matches:
                major, minor, build_number = matches.groups()
                return major, minor or "", build_number or ""
        return "", "", ""

    def major_version(self, best: bool = False) -> str:
        """
        Return the major version number of the current distribution.

        For details, see :func:`distro.major_version`.
        """
        return self.version_parts(best)[0]

    def minor_version(self, best: bool = False) -> str:
        """
        Return the minor version number of the current distribution.

        For details, see :func:`distro.minor_version`.
        """
        return self.version_parts(best)[1]

    def build_number(self, best: bool = False) -> str:
        """
        Return the build number of the current distribution.

        For details, see :func:`distro.build_number`.
        """
        return self.version_parts(best)[2]

    def like(self) -> str:
        """
        Return the IDs of distributions that are like the OS distribution.

        For details, see :func:`distro.like`.
        """
        return self.os_release_attr("id_like") or ""

    def codename(self) -> str:
        """
        Return the codename of the OS distribution.

        For details, see :func:`distro.codename`.
        """
        try:
            # Handle os_release specially since distros might purposefully set
            # this to empty string to have no codename
            return self._os_release_info["codename"]
        except KeyError:
            return (
                self.lsb_release_attr("codename")
                or self.distro_release_attr("codename")
                or ""
            )

    def info(self, pretty: bool = False, best: bool = False) -> InfoDict:
        """
        Return certain machine-readable information about the OS
        distribution.

        For details, see :func:`distro.info`.
        """
        return InfoDict(
            id=self.id(),
            version=self.version(pretty, best),
            version_parts=VersionDict(
                major=self.major_version(best),
                minor=self.minor_version(best),
                build_number=self.build_number(best),
            ),
            like=self.like(),
            codename=self.codename(),
        )

    def os_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the os-release file data source of the OS distribution.

        For details, see :func:`distro.os_release_info`.
        """
        return self._os_release_info

    def lsb_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the lsb_release command data source of the OS
        distribution.

        For details, see :func:`distro.lsb_release_info`.
        """
        return self._lsb_release_info

    def distro_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the distro release file data source of the OS
        distribution.

        For details, see :func:`distro.distro_release_info`.
        """
        return self._distro_release_info

    def uname_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the uname command data source of the OS distribution.

        For details, see :func:`distro.uname_info`.
        """
        return self._uname_info

    def oslevel_info(self) -> str:
        """
        Return AIX' oslevel command output.
        """
        return self._oslevel_info

    def os_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the os-release file data
        source of the OS distribution.

        For details, see :func:`distro.os_release_attr`.
        """
        return self._os_release_info.get(attribute, "")

    def lsb_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the lsb_release command
        output data source of the OS distribution.

        For details, see :func:`distro.lsb_release_attr`.
        """
        return self._lsb_release_info.get(attribute, "")

    def distro_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the distro release file
        data source of the OS distribution.

        For details, see :func:`distro.distro_release_attr`.
        """
        return self._distro_release_info.get(attribute, "")

    def uname_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the uname command
        output data source of the OS distribution.

        For details, see :func:`distro.uname_attr`.
        """
        return self._uname_info.get(attribute, "")

    @cached_property
    def _os_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified os-release file.

        Returns:
            A dictionary containing all information items.
        """
        if os.path.isfile(self.os_release_file):
            with open(self.os_release_file, encoding="utf-8") as release_file:
                return self._parse_os_release_content(release_file)
        return {}

    @staticmethod
    def _parse_os_release_content(lines: TextIO) -> Dict[str, str]:
        """
        Parse the lines of an os-release file.

        Parameters:

        * lines: Iterable through the lines in the os-release file.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        lexer = shlex.shlex(lines, posix=True)
        lexer.whitespace_split = True

        tokens = list(lexer)
        for token in tokens:
            # At this point, all shell-like parsing has been done (i.e.
            # comments processed, quotes and backslash escape sequences
            # processed, multi-line values assembled, trailing newlines
            # stripped, etc.), so the tokens are now either:
            # * variable assignments: var=value
            # * commands or their arguments (not allowed in os-release)
            # Ignore any tokens that are not variable assignments
            if "=" in token:
                k, v = token.split("=", 1)
                props[k.lower()] = v

        if "version" in props:
            # extract release codename (if any) from version attribute
            match = re.search(r"\((\D+)\)|,\s*(\D+)", props["version"])
            if match:
                release_codename = match.group(1) or match.group(2)
                props["codename"] = props["release_codename"] = release_codename

        if "version_codename" in props:
            # os-release added a version_codename field.  Use that in
            # preference to anything else Note that some distros purposefully
            # do not have code names.  They should be setting
            # version_codename=""
            props["codename"] = props["version_codename"]
        elif "ubuntu_codename" in props:
            # Same as above but a non-standard field name used on older Ubuntus
            props["codename"] = props["ubuntu_codename"]

        return props

    @cached_property
    def _lsb_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the lsb_release command output.

        Returns:
            A dictionary containing all information items.
        """
        if not self.include_lsb:
            return {}
        try:
            cmd = ("lsb_release", "-a")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        # Command not found or lsb_release returned error
        except (OSError, subprocess.CalledProcessError):
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_lsb_release_content(content)

    @staticmethod
    def _parse_lsb_release_content(lines: Iterable[str]) -> Dict[str, str]:
        """
        Parse the output of the lsb_release command.

        Parameters:

        * lines: Iterable through the lines of the lsb_release output.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        for line in lines:
            kv = line.strip("\n").split(":", 1)
            if len(kv) != 2:
                # Ignore lines without colon.
                continue
            k, v = kv
            props.update({k.replace(" ", "_").lower(): v.strip()})
        return props

    @cached_property
    def _uname_info(self) -> Dict[str, str]:
        if not self.include_uname:
            return {}
        try:
            cmd = ("uname", "-rs")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        except OSError:
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_uname_content(content)

    @cached_property
    def _oslevel_info(self) -> str:
        if not self.include_oslevel:
            return ""
        try:
            stdout = subprocess.check_output("oslevel", stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return ""
        return self._to_str(stdout).strip()

    @cached_property
    def _debian_version(self) -> str:
        try:
            with open(
                os.path.join(self.etc_dir, "debian_version"), encoding="ascii"
            ) as fp:
                return fp.readline().rstrip()
        except FileNotFoundError:
            return ""

    @staticmethod
    def _parse_uname_content(lines: Sequence[str]) -> Dict[str, str]:
        if not lines:
            return {}
        props = {}
        match = re.search(r"^([^\s]+)\s+([\d\.]+)", lines[0].strip())
        if match:
            name, version = match.groups()

            # This is to prevent the Linux kernel version from
            # appearing as the 'best' version on otherwise
            # identifiable distributions.
            if name == "Linux":
                return {}
            props["id"] = name.lower()
            props["name"] = name
            props["release"] = version
        return props

    @staticmethod
    def _to_str(bytestring: bytes) -> str:
        encoding = sys.getfilesystemencoding()
        return bytestring.decode(encoding)

    @cached_property
    def _distro_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified distro release file.

        Returns:
            A dictionary containing all information items.
        """
        if self.distro_release_file:
            # If it was specified, we use it and parse what we can, even if
            # its file name or content does not match the expected pattern.
            distro_info = self._parse_distro_release_file(self.distro_release_file)
            basename = os.path.basename(self.distro_release_file)
            # The file name pattern for user-specified distro release files
            # is somewhat more tolerant (compared to when searching for the
            # file), because we want to use what was specified as best as
            # possible.
            match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
        else:
            try:
                basenames = [
                    basename
                    for basename in os.listdir(self.etc_dir)
                    if basename not in _DISTRO_RELEASE_IGNORE_BASENAMES
                    and os.path.isfile(os.path.join(self.etc_dir, basename))
                ]
                # We sort for repeatability in cases where there are multiple
                # distro specific files; e.g. CentOS, Oracle, Enterprise all
                # containing `redhat-release` on top of their own.
                basenames.sort()
            except OSError:
                # This may occur when /etc is not readable but we can't be
                # sure about the *-release files. Check common entries of
                # /etc for information. If they turn out to not be there the
                # error is handled in `_parse_distro_release_file()`.
                basenames = _DISTRO_RELEASE_BASENAMES
            for basename in basenames:
                match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
                if match is None:
                    continue
                filepath = os.path.join(self.etc_dir, basename)
                distro_info = self._parse_distro_release_file(filepath)
                # The name is always present if the pattern matches.
                if "name" not in distro_info:
                    continue
                self.distro_release_file = filepath
                break
            else:  # the loop didn't "break": no candidate.
                return {}

        if match is not None:
            distro_info["id"] = match.group(1)

        # CloudLinux < 7: manually enrich info with proper id.
        if "cloudlinux" in distro_info.get("name", "").lower():
            distro_info["id"] = "cloudlinux"

        return distro_info

    def _parse_distro_release_file(self, filepath: str) -> Dict[str, str]:
        """
        Parse a distro release file.

        Parameters:

        * filepath: Path name of the distro release file.

        Returns:
            A dictionary containing all information items.
        """
        try:
            with open(filepath, encoding="utf-8") as fp:
                # Only parse the first line. For instance, on SLES there
                # are multiple lines. We don't want them...
                return self._parse_distro_release_content(fp.readline())
        except OSError:
            # Ignore not being able to read a specific, seemingly version
            # related file.
            # See https://github.com/python-distro/distro/issues/162
            return {}

    @staticmethod
    def _parse_distro_release_content(line: str) -> Dict[str, str]:
        """
        Parse a line from a distro release file.

        Parameters:
        * line: Line from the distro release file. Must be a unicode string
                or a UTF-8 encoded byte string.

        Returns:
            A dictionary containing all information items.
        """
        matches = _DISTRO_RELEASE_CONTENT_REVERSED_PATTERN.match(line.strip()[::-1])
        distro_info = {}
        if matches:
            # regexp ensures non-None
            distro_info["name"] = matches.group(3)[::-1]
            if matches.group(2):
                distro_info["version_id"] = matches.group(2)[::-1]
            if matches.group(1):
                distro_info["codename"] = matches.group(1)[::-1]
        elif line:
            distro_info["name"] = line.strip()
        return distro_info


_distro = LinuxDistribution()


def main() -> None:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    parser = argparse.ArgumentParser(description="OS distro info tool")
    parser.add_argument(
        "--json", "-j", help="Output in machine readable format", action="store_true"
    )

    parser.add_argument(
        "--root-dir",
        "-r",
        type=str,
        dest="root_dir",
        help="Path to the root filesystem directory (defaults to /)",
    )

    args = parser.parse_args()

    if args.root_dir:
        dist = LinuxDistribution(
            include_lsb=False,
            include_uname=False,
            include_oslevel=False,
            root_dir=args.root_dir,
        )
    else:
        dist = _distro

    if args.json:
        logger.info(json.dumps(dist.info(), indent=4, sort_keys=True))
    else:
        logger.info("Name: %s", dist.name(pretty=True))
        distribution_version = dist.version(pretty=True)
        logger.info("Version: %s", distribution_version)
        distribution_codename = dist.codename()
        logger.info("Codename: %s", distribution_codename)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distro\distro.py ===
#!/usr/bin/env python
# Copyright 2015-2021 Nir Cohen
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

"""
The ``distro`` package (``distro`` stands for Linux Distribution) provides
information about the Linux distribution it runs on, such as a reliable
machine-readable distro ID, or version information.

It is the recommended replacement for Python's original
:py:func:`platform.linux_distribution` function, but it provides much more
functionality. An alternative implementation became necessary because Python
3.5 deprecated this function, and Python 3.8 removed it altogether. Its
predecessor function :py:func:`platform.dist` was already deprecated since
Python 2.6 and removed in Python 3.8. Still, there are many cases in which
access to OS distribution information is needed. See `Python issue 1322
<https://bugs.python.org/issue1322>`_ for more information.
"""

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
)

try:
    from typing import TypedDict
except ImportError:
    # Python 3.7
    TypedDict = dict

__version__ = "1.9.0"


class VersionDict(TypedDict):
    major: str
    minor: str
    build_number: str


class InfoDict(TypedDict):
    id: str
    version: str
    version_parts: VersionDict
    like: str
    codename: str


_UNIXCONFDIR = os.environ.get("UNIXCONFDIR", "/etc")
_UNIXUSRLIBDIR = os.environ.get("UNIXUSRLIBDIR", "/usr/lib")
_OS_RELEASE_BASENAME = "os-release"

#: Translation table for normalizing the "ID" attribute defined in os-release
#: files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as defined in the os-release file, translated to lower case,
#:   with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_OS_ID = {
    "ol": "oracle",  # Oracle Linux
    "opensuse-leap": "opensuse",  # Newer versions of OpenSuSE report as opensuse-leap
}

#: Translation table for normalizing the "Distributor ID" attribute returned by
#: the lsb_release command, for use by the :func:`distro.id` method.
#:
#: * Key: Value as returned by the lsb_release command, translated to lower
#:   case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_LSB_ID = {
    "enterpriseenterpriseas": "oracle",  # Oracle Enterprise Linux 4
    "enterpriseenterpriseserver": "oracle",  # Oracle Linux 5
    "redhatenterpriseworkstation": "rhel",  # RHEL 6, 7 Workstation
    "redhatenterpriseserver": "rhel",  # RHEL 6, 7 Server
    "redhatenterprisecomputenode": "rhel",  # RHEL 6 ComputeNode
}

#: Translation table for normalizing the distro ID derived from the file name
#: of distro release files, for use by the :func:`distro.id` method.
#:
#: * Key: Value as derived from the file name of a distro release file,
#:   translated to lower case, with blanks translated to underscores.
#:
#: * Value: Normalized value.
NORMALIZED_DISTRO_ID = {
    "redhat": "rhel",  # RHEL 6.x, 7.x
}

# Pattern for content of distro release file (reversed)
_DISTRO_RELEASE_CONTENT_REVERSED_PATTERN = re.compile(
    r"(?:[^)]*\)(.*)\()? *(?:STL )?([\d.+\-a-z]*\d) *(?:esaeler *)?(.+)"
)

# Pattern for base file name of distro release file
_DISTRO_RELEASE_BASENAME_PATTERN = re.compile(r"(\w+)[-_](release|version)$")

# Base file names to be looked up for if _UNIXCONFDIR is not readable.
_DISTRO_RELEASE_BASENAMES = [
    "SuSE-release",
    "altlinux-release",
    "arch-release",
    "base-release",
    "centos-release",
    "fedora-release",
    "gentoo-release",
    "mageia-release",
    "mandrake-release",
    "mandriva-release",
    "mandrivalinux-release",
    "manjaro-release",
    "oracle-release",
    "redhat-release",
    "rocky-release",
    "sl-release",
    "slackware-version",
]

# Base file names to be ignored when searching for distro release file
_DISTRO_RELEASE_IGNORE_BASENAMES = (
    "debian_version",
    "lsb-release",
    "oem-release",
    _OS_RELEASE_BASENAME,
    "system-release",
    "plesk-release",
    "iredmail-release",
    "board-release",
    "ec2_version",
)


def linux_distribution(full_distribution_name: bool = True) -> Tuple[str, str, str]:
    """
    .. deprecated:: 1.6.0

        :func:`distro.linux_distribution()` is deprecated. It should only be
        used as a compatibility shim with Python's
        :py:func:`platform.linux_distribution()`. Please use :func:`distro.id`,
        :func:`distro.version` and :func:`distro.name` instead.

    Return information about the current OS distribution as a tuple
    ``(id_name, version, codename)`` with items as follows:

    * ``id_name``:  If *full_distribution_name* is false, the result of
      :func:`distro.id`. Otherwise, the result of :func:`distro.name`.

    * ``version``:  The result of :func:`distro.version`.

    * ``codename``:  The extra item (usually in parentheses) after the
      os-release version number, or the result of :func:`distro.codename`.

    The interface of this function is compatible with the original
    :py:func:`platform.linux_distribution` function, supporting a subset of
    its parameters.

    The data it returns may not exactly be the same, because it uses more data
    sources than the original function, and that may lead to different data if
    the OS distribution is not consistent across multiple data sources it
    provides (there are indeed such distributions ...).

    Another reason for differences is the fact that the :func:`distro.id`
    method normalizes the distro ID string to a reliable machine-readable value
    for a number of popular OS distributions.
    """
    warnings.warn(
        "distro.linux_distribution() is deprecated. It should only be used as a "
        "compatibility shim with Python's platform.linux_distribution(). Please use "
        "distro.id(), distro.version() and distro.name() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _distro.linux_distribution(full_distribution_name)


def id() -> str:
    """
    Return the distro ID of the current distribution, as a
    machine-readable string.

    For a number of OS distributions, the returned distro ID value is
    *reliable*, in the sense that it is documented and that it does not change
    across releases of the distribution.

    This package maintains the following reliable distro ID values:

    ==============  =========================================
    Distro ID       Distribution
    ==============  =========================================
    "ubuntu"        Ubuntu
    "debian"        Debian
    "rhel"          RedHat Enterprise Linux
    "centos"        CentOS
    "fedora"        Fedora
    "sles"          SUSE Linux Enterprise Server
    "opensuse"      openSUSE
    "amzn"          Amazon Linux
    "arch"          Arch Linux
    "buildroot"     Buildroot
    "cloudlinux"    CloudLinux OS
    "exherbo"       Exherbo Linux
    "gentoo"        GenToo Linux
    "ibm_powerkvm"  IBM PowerKVM
    "kvmibm"        KVM for IBM z Systems
    "linuxmint"     Linux Mint
    "mageia"        Mageia
    "mandriva"      Mandriva Linux
    "parallels"     Parallels
    "pidora"        Pidora
    "raspbian"      Raspbian
    "oracle"        Oracle Linux (and Oracle Enterprise Linux)
    "scientific"    Scientific Linux
    "slackware"     Slackware
    "xenserver"     XenServer
    "openbsd"       OpenBSD
    "netbsd"        NetBSD
    "freebsd"       FreeBSD
    "midnightbsd"   MidnightBSD
    "rocky"         Rocky Linux
    "aix"           AIX
    "guix"          Guix System
    "altlinux"      ALT Linux
    ==============  =========================================

    If you have a need to get distros for reliable IDs added into this set,
    or if you find that the :func:`distro.id` function returns a different
    distro ID for one of the listed distros, please create an issue in the
    `distro issue tracker`_.

    **Lookup hierarchy and transformations:**

    First, the ID is obtained from the following sources, in the specified
    order. The first available and non-empty value is used:

    * the value of the "ID" attribute of the os-release file,

    * the value of the "Distributor ID" attribute returned by the lsb_release
      command,

    * the first part of the file name of the distro release file,

    The so determined ID value then passes the following transformations,
    before it is returned by this method:

    * it is translated to lower case,

    * blanks (which should not be there anyway) are translated to underscores,

    * a normalization of the ID is performed, based upon
      `normalization tables`_. The purpose of this normalization is to ensure
      that the ID is as reliable as possible, even across incompatible changes
      in the OS distributions. A common reason for an incompatible change is
      the addition of an os-release file, or the addition of the lsb_release
      command, with ID values that differ from what was previously determined
      from the distro release file name.
    """
    return _distro.id()


def name(pretty: bool = False) -> str:
    """
    Return the name of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the name is returned without version or codename.
    (e.g. "CentOS Linux")

    If *pretty* is true, the version and codename are appended.
    (e.g. "CentOS Linux 7.1.1503 (Core)")

    **Lookup hierarchy:**

    The name is obtained from the following sources, in the specified order.
    The first available and non-empty value is used:

    * If *pretty* is false:

      - the value of the "NAME" attribute of the os-release file,

      - the value of the "Distributor ID" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file.

    * If *pretty* is true:

      - the value of the "PRETTY_NAME" attribute of the os-release file,

      - the value of the "Description" attribute returned by the lsb_release
        command,

      - the value of the "<name>" field of the distro release file, appended
        with the value of the pretty version ("<version_id>" and "<codename>"
        fields) of the distro release file, if available.
    """
    return _distro.name(pretty)


def version(pretty: bool = False, best: bool = False) -> str:
    """
    Return the version of the current OS distribution, as a human-readable
    string.

    If *pretty* is false, the version is returned without codename (e.g.
    "7.0").

    If *pretty* is true, the codename in parenthesis is appended, if the
    codename is non-empty (e.g. "7.0 (Maipo)").

    Some distributions provide version numbers with different precisions in
    the different sources of distribution information. Examining the different
    sources in a fixed priority order does not always yield the most precise
    version (e.g. for Debian 8.2, or CentOS 7.1).

    Some other distributions may not provide this kind of information. In these
    cases, an empty string would be returned. This behavior can be observed
    with rolling releases distributions (e.g. Arch Linux).

    The *best* parameter can be used to control the approach for the returned
    version:

    If *best* is false, the first non-empty version number in priority order of
    the examined sources is returned.

    If *best* is true, the most precise version number out of all examined
    sources is returned.

    **Lookup hierarchy:**

    In all cases, the version number is obtained from the following sources.
    If *best* is false, this order represents the priority order:

    * the value of the "VERSION_ID" attribute of the os-release file,
    * the value of the "Release" attribute returned by the lsb_release
      command,
    * the version number parsed from the "<version_id>" field of the first line
      of the distro release file,
    * the version number parsed from the "PRETTY_NAME" attribute of the
      os-release file, if it follows the format of the distro release files.
    * the version number parsed from the "Description" attribute returned by
      the lsb_release command, if it follows the format of the distro release
      files.
    """
    return _distro.version(pretty, best)


def version_parts(best: bool = False) -> Tuple[str, str, str]:
    """
    Return the version of the current OS distribution as a tuple
    ``(major, minor, build_number)`` with items as follows:

    * ``major``:  The result of :func:`distro.major_version`.

    * ``minor``:  The result of :func:`distro.minor_version`.

    * ``build_number``:  The result of :func:`distro.build_number`.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.version_parts(best)


def major_version(best: bool = False) -> str:
    """
    Return the major version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The major version is the first
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.major_version(best)


def minor_version(best: bool = False) -> str:
    """
    Return the minor version of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The minor version is the second
    part of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.minor_version(best)


def build_number(best: bool = False) -> str:
    """
    Return the build number of the current OS distribution, as a string,
    if provided.
    Otherwise, the empty string is returned. The build number is the third part
    of the dot-separated version string.

    For a description of the *best* parameter, see the :func:`distro.version`
    method.
    """
    return _distro.build_number(best)


def like() -> str:
    """
    Return a space-separated list of distro IDs of distributions that are
    closely related to the current OS distribution in regards to packaging
    and programming interfaces, for example distributions the current
    distribution is a derivative from.

    **Lookup hierarchy:**

    This information item is only provided by the os-release file.
    For details, see the description of the "ID_LIKE" attribute in the
    `os-release man page
    <http://www.freedesktop.org/software/systemd/man/os-release.html>`_.
    """
    return _distro.like()


def codename() -> str:
    """
    Return the codename for the release of the current OS distribution,
    as a string.

    If the distribution does not have a codename, an empty string is returned.

    Note that the returned codename is not always really a codename. For
    example, openSUSE returns "x86_64". This function does not handle such
    cases in any special way and just returns the string it finds, if any.

    **Lookup hierarchy:**

    * the codename within the "VERSION" attribute of the os-release file, if
      provided,

    * the value of the "Codename" attribute returned by the lsb_release
      command,

    * the value of the "<codename>" field of the distro release file.
    """
    return _distro.codename()


def info(pretty: bool = False, best: bool = False) -> InfoDict:
    """
    Return certain machine-readable information items about the current OS
    distribution in a dictionary, as shown in the following example:

    .. sourcecode:: python

        {
            'id': 'rhel',
            'version': '7.0',
            'version_parts': {
                'major': '7',
                'minor': '0',
                'build_number': ''
            },
            'like': 'fedora',
            'codename': 'Maipo'
        }

    The dictionary structure and keys are always the same, regardless of which
    information items are available in the underlying data sources. The values
    for the various keys are as follows:

    * ``id``:  The result of :func:`distro.id`.

    * ``version``:  The result of :func:`distro.version`.

    * ``version_parts -> major``:  The result of :func:`distro.major_version`.

    * ``version_parts -> minor``:  The result of :func:`distro.minor_version`.

    * ``version_parts -> build_number``:  The result of
      :func:`distro.build_number`.

    * ``like``:  The result of :func:`distro.like`.

    * ``codename``:  The result of :func:`distro.codename`.

    For a description of the *pretty* and *best* parameters, see the
    :func:`distro.version` method.
    """
    return _distro.info(pretty, best)


def os_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the os-release file data source of the current OS distribution.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_info()


def lsb_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the lsb_release command data source of the current OS distribution.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_info()


def distro_release_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_info()


def uname_info() -> Dict[str, str]:
    """
    Return a dictionary containing key-value pairs for the information items
    from the distro release file data source of the current OS distribution.
    """
    return _distro.uname_info()


def os_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the os-release file data source
    of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `os-release file`_ for details about these information items.
    """
    return _distro.os_release_attr(attribute)


def lsb_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the lsb_release command output
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `lsb_release command output`_ for details about these information
    items.
    """
    return _distro.lsb_release_attr(attribute)


def distro_release_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
      The empty string, if the item does not exist.

    See `distro release file`_ for details about these information items.
    """
    return _distro.distro_release_attr(attribute)


def uname_attr(attribute: str) -> str:
    """
    Return a single named information item from the distro release file
    data source of the current OS distribution.

    Parameters:

    * ``attribute`` (string): Key of the information item.

    Returns:

    * (string): Value of the information item, if the item exists.
                The empty string, if the item does not exist.
    """
    return _distro.uname_attr(attribute)


try:
    from functools import cached_property
except ImportError:
    # Python < 3.8
    class cached_property:  # type: ignore
        """A version of @property which caches the value.  On access, it calls the
        underlying function and sets the value in `__dict__` so future accesses
        will not re-call the property.
        """

        def __init__(self, f: Callable[[Any], Any]) -> None:
            self._fname = f.__name__
            self._f = f

        def __get__(self, obj: Any, owner: Type[Any]) -> Any:
            assert obj is not None, f"call {self._fname} on an instance"
            ret = obj.__dict__[self._fname] = self._f(obj)
            return ret


class LinuxDistribution:
    """
    Provides information about a OS distribution.

    This package creates a private module-global instance of this class with
    default initialization arguments, that is used by the
    `consolidated accessor functions`_ and `single source accessor functions`_.
    By using default initialization arguments, that module-global instance
    returns data about the current OS distribution (i.e. the distro this
    package runs on).

    Normally, it is not necessary to create additional instances of this class.
    However, in situations where control is needed over the exact data sources
    that are used, instances of this class can be created with a specific
    distro release file, or a specific os-release file, or without invoking the
    lsb_release command.
    """

    def __init__(
        self,
        include_lsb: Optional[bool] = None,
        os_release_file: str = "",
        distro_release_file: str = "",
        include_uname: Optional[bool] = None,
        root_dir: Optional[str] = None,
        include_oslevel: Optional[bool] = None,
    ) -> None:
        """
        The initialization method of this class gathers information from the
        available data sources, and stores that in private instance attributes.
        Subsequent access to the information items uses these private instance
        attributes, so that the data sources are read only once.

        Parameters:

        * ``include_lsb`` (bool): Controls whether the
          `lsb_release command output`_ is included as a data source.

          If the lsb_release command is not available in the program execution
          path, the data source for the lsb_release command will be empty.

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is to be used as a data source.

          An empty string (the default) will cause the default path name to
          be used (see `os-release file`_ for details).

          If the specified or defaulted os-release file does not exist, the
          data source for the os-release file will be empty.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is to be used as a data source.

          An empty string (the default) will cause a default search algorithm
          to be used (see `distro release file`_ for details).

          If the specified distro release file does not exist, or if no default
          distro release file can be found, the data source for the distro
          release file will be empty.

        * ``include_uname`` (bool): Controls whether uname command output is
          included as a data source. If the uname command is not available in
          the program execution path the data source for the uname command will
          be empty.

        * ``root_dir`` (string): The absolute path to the root directory to use
          to find distro-related information files. Note that ``include_*``
          parameters must not be enabled in combination with ``root_dir``.

        * ``include_oslevel`` (bool): Controls whether (AIX) oslevel command
          output is included as a data source. If the oslevel command is not
          available in the program execution path the data source will be
          empty.

        Public instance attributes:

        * ``os_release_file`` (string): The path name of the
          `os-release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``distro_release_file`` (string): The path name of the
          `distro release file`_ that is actually used as a data source. The
          empty string if no distro release file is used as a data source.

        * ``include_lsb`` (bool): The result of the ``include_lsb`` parameter.
          This controls whether the lsb information will be loaded.

        * ``include_uname`` (bool): The result of the ``include_uname``
          parameter. This controls whether the uname information will
          be loaded.

        * ``include_oslevel`` (bool): The result of the ``include_oslevel``
          parameter. This controls whether (AIX) oslevel information will be
          loaded.

        * ``root_dir`` (string): The result of the ``root_dir`` parameter.
          The absolute path to the root directory to use to find distro-related
          information files.

        Raises:

        * :py:exc:`ValueError`: Initialization parameters combination is not
           supported.

        * :py:exc:`OSError`: Some I/O issue with an os-release file or distro
          release file.

        * :py:exc:`UnicodeError`: A data source has unexpected characters or
          uses an unexpected encoding.
        """
        self.root_dir = root_dir
        self.etc_dir = os.path.join(root_dir, "etc") if root_dir else _UNIXCONFDIR
        self.usr_lib_dir = (
            os.path.join(root_dir, "usr/lib") if root_dir else _UNIXUSRLIBDIR
        )

        if os_release_file:
            self.os_release_file = os_release_file
        else:
            etc_dir_os_release_file = os.path.join(self.etc_dir, _OS_RELEASE_BASENAME)
            usr_lib_os_release_file = os.path.join(
                self.usr_lib_dir, _OS_RELEASE_BASENAME
            )

            # NOTE: The idea is to respect order **and** have it set
            #       at all times for API backwards compatibility.
            if os.path.isfile(etc_dir_os_release_file) or not os.path.isfile(
                usr_lib_os_release_file
            ):
                self.os_release_file = etc_dir_os_release_file
            else:
                self.os_release_file = usr_lib_os_release_file

        self.distro_release_file = distro_release_file or ""  # updated later

        is_root_dir_defined = root_dir is not None
        if is_root_dir_defined and (include_lsb or include_uname or include_oslevel):
            raise ValueError(
                "Including subprocess data sources from specific root_dir is disallowed"
                " to prevent false information"
            )
        self.include_lsb = (
            include_lsb if include_lsb is not None else not is_root_dir_defined
        )
        self.include_uname = (
            include_uname if include_uname is not None else not is_root_dir_defined
        )
        self.include_oslevel = (
            include_oslevel if include_oslevel is not None else not is_root_dir_defined
        )

    def __repr__(self) -> str:
        """Return repr of all info"""
        return (
            "LinuxDistribution("
            "os_release_file={self.os_release_file!r}, "
            "distro_release_file={self.distro_release_file!r}, "
            "include_lsb={self.include_lsb!r}, "
            "include_uname={self.include_uname!r}, "
            "include_oslevel={self.include_oslevel!r}, "
            "root_dir={self.root_dir!r}, "
            "_os_release_info={self._os_release_info!r}, "
            "_lsb_release_info={self._lsb_release_info!r}, "
            "_distro_release_info={self._distro_release_info!r}, "
            "_uname_info={self._uname_info!r}, "
            "_oslevel_info={self._oslevel_info!r})".format(self=self)
        )

    def linux_distribution(
        self, full_distribution_name: bool = True
    ) -> Tuple[str, str, str]:
        """
        Return information about the OS distribution that is compatible
        with Python's :func:`platform.linux_distribution`, supporting a subset
        of its parameters.

        For details, see :func:`distro.linux_distribution`.
        """
        return (
            self.name() if full_distribution_name else self.id(),
            self.version(),
            self._os_release_info.get("release_codename") or self.codename(),
        )

    def id(self) -> str:
        """Return the distro ID of the OS distribution, as a string.

        For details, see :func:`distro.id`.
        """

        def normalize(distro_id: str, table: Dict[str, str]) -> str:
            distro_id = distro_id.lower().replace(" ", "_")
            return table.get(distro_id, distro_id)

        distro_id = self.os_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_OS_ID)

        distro_id = self.lsb_release_attr("distributor_id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_LSB_ID)

        distro_id = self.distro_release_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        distro_id = self.uname_attr("id")
        if distro_id:
            return normalize(distro_id, NORMALIZED_DISTRO_ID)

        return ""

    def name(self, pretty: bool = False) -> str:
        """
        Return the name of the OS distribution, as a string.

        For details, see :func:`distro.name`.
        """
        name = (
            self.os_release_attr("name")
            or self.lsb_release_attr("distributor_id")
            or self.distro_release_attr("name")
            or self.uname_attr("name")
        )
        if pretty:
            name = self.os_release_attr("pretty_name") or self.lsb_release_attr(
                "description"
            )
            if not name:
                name = self.distro_release_attr("name") or self.uname_attr("name")
                version = self.version(pretty=True)
                if version:
                    name = f"{name} {version}"
        return name or ""

    def version(self, pretty: bool = False, best: bool = False) -> str:
        """
        Return the version of the OS distribution, as a string.

        For details, see :func:`distro.version`.
        """
        versions = [
            self.os_release_attr("version_id"),
            self.lsb_release_attr("release"),
            self.distro_release_attr("version_id"),
            self._parse_distro_release_content(self.os_release_attr("pretty_name")).get(
                "version_id", ""
            ),
            self._parse_distro_release_content(
                self.lsb_release_attr("description")
            ).get("version_id", ""),
            self.uname_attr("release"),
        ]
        if self.uname_attr("id").startswith("aix"):
            # On AIX platforms, prefer oslevel command output.
            versions.insert(0, self.oslevel_info())
        elif self.id() == "debian" or "debian" in self.like().split():
            # On Debian-like, add debian_version file content to candidates list.
            versions.append(self._debian_version)
        version = ""
        if best:
            # This algorithm uses the last version in priority order that has
            # the best precision. If the versions are not in conflict, that
            # does not matter; otherwise, using the last one instead of the
            # first one might be considered a surprise.
            for v in versions:
                if v.count(".") > version.count(".") or version == "":
                    version = v
        else:
            for v in versions:
                if v != "":
                    version = v
                    break
        if pretty and version and self.codename():
            version = f"{version} ({self.codename()})"
        return version

    def version_parts(self, best: bool = False) -> Tuple[str, str, str]:
        """
        Return the version of the OS distribution, as a tuple of version
        numbers.

        For details, see :func:`distro.version_parts`.
        """
        version_str = self.version(best=best)
        if version_str:
            version_regex = re.compile(r"(\d+)\.?(\d+)?\.?(\d+)?")
            matches = version_regex.match(version_str)
            if matches:
                major, minor, build_number = matches.groups()
                return major, minor or "", build_number or ""
        return "", "", ""

    def major_version(self, best: bool = False) -> str:
        """
        Return the major version number of the current distribution.

        For details, see :func:`distro.major_version`.
        """
        return self.version_parts(best)[0]

    def minor_version(self, best: bool = False) -> str:
        """
        Return the minor version number of the current distribution.

        For details, see :func:`distro.minor_version`.
        """
        return self.version_parts(best)[1]

    def build_number(self, best: bool = False) -> str:
        """
        Return the build number of the current distribution.

        For details, see :func:`distro.build_number`.
        """
        return self.version_parts(best)[2]

    def like(self) -> str:
        """
        Return the IDs of distributions that are like the OS distribution.

        For details, see :func:`distro.like`.
        """
        return self.os_release_attr("id_like") or ""

    def codename(self) -> str:
        """
        Return the codename of the OS distribution.

        For details, see :func:`distro.codename`.
        """
        try:
            # Handle os_release specially since distros might purposefully set
            # this to empty string to have no codename
            return self._os_release_info["codename"]
        except KeyError:
            return (
                self.lsb_release_attr("codename")
                or self.distro_release_attr("codename")
                or ""
            )

    def info(self, pretty: bool = False, best: bool = False) -> InfoDict:
        """
        Return certain machine-readable information about the OS
        distribution.

        For details, see :func:`distro.info`.
        """
        return InfoDict(
            id=self.id(),
            version=self.version(pretty, best),
            version_parts=VersionDict(
                major=self.major_version(best),
                minor=self.minor_version(best),
                build_number=self.build_number(best),
            ),
            like=self.like(),
            codename=self.codename(),
        )

    def os_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the os-release file data source of the OS distribution.

        For details, see :func:`distro.os_release_info`.
        """
        return self._os_release_info

    def lsb_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the lsb_release command data source of the OS
        distribution.

        For details, see :func:`distro.lsb_release_info`.
        """
        return self._lsb_release_info

    def distro_release_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the distro release file data source of the OS
        distribution.

        For details, see :func:`distro.distro_release_info`.
        """
        return self._distro_release_info

    def uname_info(self) -> Dict[str, str]:
        """
        Return a dictionary containing key-value pairs for the information
        items from the uname command data source of the OS distribution.

        For details, see :func:`distro.uname_info`.
        """
        return self._uname_info

    def oslevel_info(self) -> str:
        """
        Return AIX' oslevel command output.
        """
        return self._oslevel_info

    def os_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the os-release file data
        source of the OS distribution.

        For details, see :func:`distro.os_release_attr`.
        """
        return self._os_release_info.get(attribute, "")

    def lsb_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the lsb_release command
        output data source of the OS distribution.

        For details, see :func:`distro.lsb_release_attr`.
        """
        return self._lsb_release_info.get(attribute, "")

    def distro_release_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the distro release file
        data source of the OS distribution.

        For details, see :func:`distro.distro_release_attr`.
        """
        return self._distro_release_info.get(attribute, "")

    def uname_attr(self, attribute: str) -> str:
        """
        Return a single named information item from the uname command
        output data source of the OS distribution.

        For details, see :func:`distro.uname_attr`.
        """
        return self._uname_info.get(attribute, "")

    @cached_property
    def _os_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified os-release file.

        Returns:
            A dictionary containing all information items.
        """
        if os.path.isfile(self.os_release_file):
            with open(self.os_release_file, encoding="utf-8") as release_file:
                return self._parse_os_release_content(release_file)
        return {}

    @staticmethod
    def _parse_os_release_content(lines: TextIO) -> Dict[str, str]:
        """
        Parse the lines of an os-release file.

        Parameters:

        * lines: Iterable through the lines in the os-release file.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        lexer = shlex.shlex(lines, posix=True)
        lexer.whitespace_split = True

        tokens = list(lexer)
        for token in tokens:
            # At this point, all shell-like parsing has been done (i.e.
            # comments processed, quotes and backslash escape sequences
            # processed, multi-line values assembled, trailing newlines
            # stripped, etc.), so the tokens are now either:
            # * variable assignments: var=value
            # * commands or their arguments (not allowed in os-release)
            # Ignore any tokens that are not variable assignments
            if "=" in token:
                k, v = token.split("=", 1)
                props[k.lower()] = v

        if "version" in props:
            # extract release codename (if any) from version attribute
            match = re.search(r"\((\D+)\)|,\s*(\D+)", props["version"])
            if match:
                release_codename = match.group(1) or match.group(2)
                props["codename"] = props["release_codename"] = release_codename

        if "version_codename" in props:
            # os-release added a version_codename field.  Use that in
            # preference to anything else Note that some distros purposefully
            # do not have code names.  They should be setting
            # version_codename=""
            props["codename"] = props["version_codename"]
        elif "ubuntu_codename" in props:
            # Same as above but a non-standard field name used on older Ubuntus
            props["codename"] = props["ubuntu_codename"]

        return props

    @cached_property
    def _lsb_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the lsb_release command output.

        Returns:
            A dictionary containing all information items.
        """
        if not self.include_lsb:
            return {}
        try:
            cmd = ("lsb_release", "-a")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        # Command not found or lsb_release returned error
        except (OSError, subprocess.CalledProcessError):
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_lsb_release_content(content)

    @staticmethod
    def _parse_lsb_release_content(lines: Iterable[str]) -> Dict[str, str]:
        """
        Parse the output of the lsb_release command.

        Parameters:

        * lines: Iterable through the lines of the lsb_release output.
                 Each line must be a unicode string or a UTF-8 encoded byte
                 string.

        Returns:
            A dictionary containing all information items.
        """
        props = {}
        for line in lines:
            kv = line.strip("\n").split(":", 1)
            if len(kv) != 2:
                # Ignore lines without colon.
                continue
            k, v = kv
            props.update({k.replace(" ", "_").lower(): v.strip()})
        return props

    @cached_property
    def _uname_info(self) -> Dict[str, str]:
        if not self.include_uname:
            return {}
        try:
            cmd = ("uname", "-rs")
            stdout = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        except OSError:
            return {}
        content = self._to_str(stdout).splitlines()
        return self._parse_uname_content(content)

    @cached_property
    def _oslevel_info(self) -> str:
        if not self.include_oslevel:
            return ""
        try:
            stdout = subprocess.check_output("oslevel", stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return ""
        return self._to_str(stdout).strip()

    @cached_property
    def _debian_version(self) -> str:
        try:
            with open(
                os.path.join(self.etc_dir, "debian_version"), encoding="ascii"
            ) as fp:
                return fp.readline().rstrip()
        except FileNotFoundError:
            return ""

    @staticmethod
    def _parse_uname_content(lines: Sequence[str]) -> Dict[str, str]:
        if not lines:
            return {}
        props = {}
        match = re.search(r"^([^\s]+)\s+([\d\.]+)", lines[0].strip())
        if match:
            name, version = match.groups()

            # This is to prevent the Linux kernel version from
            # appearing as the 'best' version on otherwise
            # identifiable distributions.
            if name == "Linux":
                return {}
            props["id"] = name.lower()
            props["name"] = name
            props["release"] = version
        return props

    @staticmethod
    def _to_str(bytestring: bytes) -> str:
        encoding = sys.getfilesystemencoding()
        return bytestring.decode(encoding)

    @cached_property
    def _distro_release_info(self) -> Dict[str, str]:
        """
        Get the information items from the specified distro release file.

        Returns:
            A dictionary containing all information items.
        """
        if self.distro_release_file:
            # If it was specified, we use it and parse what we can, even if
            # its file name or content does not match the expected pattern.
            distro_info = self._parse_distro_release_file(self.distro_release_file)
            basename = os.path.basename(self.distro_release_file)
            # The file name pattern for user-specified distro release files
            # is somewhat more tolerant (compared to when searching for the
            # file), because we want to use what was specified as best as
            # possible.
            match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
        else:
            try:
                basenames = [
                    basename
                    for basename in os.listdir(self.etc_dir)
                    if basename not in _DISTRO_RELEASE_IGNORE_BASENAMES
                    and os.path.isfile(os.path.join(self.etc_dir, basename))
                ]
                # We sort for repeatability in cases where there are multiple
                # distro specific files; e.g. CentOS, Oracle, Enterprise all
                # containing `redhat-release` on top of their own.
                basenames.sort()
            except OSError:
                # This may occur when /etc is not readable but we can't be
                # sure about the *-release files. Check common entries of
                # /etc for information. If they turn out to not be there the
                # error is handled in `_parse_distro_release_file()`.
                basenames = _DISTRO_RELEASE_BASENAMES
            for basename in basenames:
                match = _DISTRO_RELEASE_BASENAME_PATTERN.match(basename)
                if match is None:
                    continue
                filepath = os.path.join(self.etc_dir, basename)
                distro_info = self._parse_distro_release_file(filepath)
                # The name is always present if the pattern matches.
                if "name" not in distro_info:
                    continue
                self.distro_release_file = filepath
                break
            else:  # the loop didn't "break": no candidate.
                return {}

        if match is not None:
            distro_info["id"] = match.group(1)

        # CloudLinux < 7: manually enrich info with proper id.
        if "cloudlinux" in distro_info.get("name", "").lower():
            distro_info["id"] = "cloudlinux"

        return distro_info

    def _parse_distro_release_file(self, filepath: str) -> Dict[str, str]:
        """
        Parse a distro release file.

        Parameters:

        * filepath: Path name of the distro release file.

        Returns:
            A dictionary containing all information items.
        """
        try:
            with open(filepath, encoding="utf-8") as fp:
                # Only parse the first line. For instance, on SLES there
                # are multiple lines. We don't want them...
                return self._parse_distro_release_content(fp.readline())
        except OSError:
            # Ignore not being able to read a specific, seemingly version
            # related file.
            # See https://github.com/python-distro/distro/issues/162
            return {}

    @staticmethod
    def _parse_distro_release_content(line: str) -> Dict[str, str]:
        """
        Parse a line from a distro release file.

        Parameters:
        * line: Line from the distro release file. Must be a unicode string
                or a UTF-8 encoded byte string.

        Returns:
            A dictionary containing all information items.
        """
        matches = _DISTRO_RELEASE_CONTENT_REVERSED_PATTERN.match(line.strip()[::-1])
        distro_info = {}
        if matches:
            # regexp ensures non-None
            distro_info["name"] = matches.group(3)[::-1]
            if matches.group(2):
                distro_info["version_id"] = matches.group(2)[::-1]
            if matches.group(1):
                distro_info["codename"] = matches.group(1)[::-1]
        elif line:
            distro_info["name"] = line.strip()
        return distro_info


_distro = LinuxDistribution()


def main() -> None:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    parser = argparse.ArgumentParser(description="OS distro info tool")
    parser.add_argument(
        "--json", "-j", help="Output in machine readable format", action="store_true"
    )

    parser.add_argument(
        "--root-dir",
        "-r",
        type=str,
        dest="root_dir",
        help="Path to the root filesystem directory (defaults to /)",
    )

    args = parser.parse_args()

    if args.root_dir:
        dist = LinuxDistribution(
            include_lsb=False,
            include_uname=False,
            include_oslevel=False,
            root_dir=args.root_dir,
        )
    else:
        dist = _distro

    if args.json:
        logger.info(json.dumps(dist.info(), indent=4, sort_keys=True))
    else:
        logger.info("Name: %s", dist.name(pretty=True))
        distribution_version = dist.version(pretty=True)
        logger.info("Version: %s", distribution_version)
        distribution_codename = dist.codename()
        logger.info("Codename: %s", distribution_codename)


if __name__ == "__main__":
    main()