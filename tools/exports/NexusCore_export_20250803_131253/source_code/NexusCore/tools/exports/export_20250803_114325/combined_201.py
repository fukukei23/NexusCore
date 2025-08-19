
# === NexusCore/openenv\Lib\site-packages\jupyter_client\channels.py ===
"""Base classes to manage a Client's interaction with a running kernel"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import atexit
import time
import typing as t
from queue import Empty
from threading import Event, Thread

import zmq.asyncio
from jupyter_core.utils import ensure_async

from ._version import protocol_version_info
from .channelsabc import HBChannelABC
from .session import Session

# import ZMQError in top-level namespace, to avoid ugly attribute-error messages
# during garbage collection of threads at exit

# -----------------------------------------------------------------------------
# Constants and exceptions
# -----------------------------------------------------------------------------

major_protocol_version = protocol_version_info[0]


class InvalidPortNumber(Exception):  # noqa
    """An exception raised for an invalid port number."""

    pass


class HBChannel(Thread):
    """The heartbeat channel which monitors the kernel heartbeat.

    Note that the heartbeat channel is paused by default. As long as you start
    this channel, the kernel manager will ensure that it is paused and un-paused
    as appropriate.
    """

    session = None
    socket = None
    address = None
    _exiting = False

    time_to_dead: float = 1.0
    _running = None
    _pause = None
    _beating = None

    def __init__(
        self,
        context: t.Optional[zmq.Context] = None,
        session: t.Optional[Session] = None,
        address: t.Union[t.Tuple[str, int], str] = "",
    ) -> None:
        """Create the heartbeat monitor thread.

        Parameters
        ----------
        context : :class:`zmq.Context`
            The ZMQ context to use.
        session : :class:`session.Session`
            The session to use.
        address : zmq url
            Standard (ip, port) tuple that the kernel is listening on.
        """
        super().__init__()
        self.daemon = True

        self.context = context
        self.session = session
        if isinstance(address, tuple):
            if address[1] == 0:
                message = "The port number for a channel cannot be 0."
                raise InvalidPortNumber(message)
            address_str = "tcp://%s:%i" % address
        else:
            address_str = address
        self.address = address_str

        # running is False until `.start()` is called
        self._running = False
        self._exit = Event()
        # don't start paused
        self._pause = False
        self.poller = zmq.Poller()

    @staticmethod
    @atexit.register
    def _notice_exit() -> None:
        # Class definitions can be torn down during interpreter shutdown.
        # We only need to set _exiting flag if this hasn't happened.
        if HBChannel is not None:
            HBChannel._exiting = True

    def _create_socket(self) -> None:
        if self.socket is not None:
            # close previous socket, before opening a new one
            self.poller.unregister(self.socket)  # type:ignore[unreachable]
            self.socket.close()
        assert self.context is not None
        self.socket = self.context.socket(zmq.REQ)
        self.socket.linger = 1000
        assert self.address is not None
        self.socket.connect(self.address)

        self.poller.register(self.socket, zmq.POLLIN)

    async def _async_run(self) -> None:
        """The thread's main activity.  Call start() instead."""
        self._create_socket()
        self._running = True
        self._beating = True
        assert self.socket is not None

        while self._running:
            if self._pause:
                # just sleep, and skip the rest of the loop
                self._exit.wait(self.time_to_dead)
                continue

            since_last_heartbeat = 0.0
            # no need to catch EFSM here, because the previous event was
            # either a recv or connect, which cannot be followed by EFSM)
            await ensure_async(self.socket.send(b"ping"))
            request_time = time.time()
            # Wait until timeout
            self._exit.wait(self.time_to_dead)
            # poll(0) means return immediately (see http://api.zeromq.org/2-1:zmq-poll)
            self._beating = bool(self.poller.poll(0))
            if self._beating:
                # the poll above guarantees we have something to recv
                await ensure_async(self.socket.recv())
                continue
            elif self._running:
                # nothing was received within the time limit, signal heart failure
                since_last_heartbeat = time.time() - request_time
                self.call_handlers(since_last_heartbeat)
                # and close/reopen the socket, because the REQ/REP cycle has been broken
                self._create_socket()
                continue

    def run(self) -> None:
        """Run the heartbeat thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_run())
        loop.close()

    def pause(self) -> None:
        """Pause the heartbeat."""
        self._pause = True

    def unpause(self) -> None:
        """Unpause the heartbeat."""
        self._pause = False

    def is_beating(self) -> bool:
        """Is the heartbeat running and responsive (and not paused)."""
        if self.is_alive() and not self._pause and self._beating:  # noqa
            return True
        else:
            return False

    def stop(self) -> None:
        """Stop the channel's event loop and join its thread."""
        self._running = False
        self._exit.set()
        self.join()
        self.close()

    def close(self) -> None:
        """Close the heartbeat thread."""
        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
            self.socket = None

    def call_handlers(self, since_last_heartbeat: float) -> None:
        """This method is called in the ioloop thread when a message arrives.

        Subclasses should override this method to handle incoming messages.
        It is important to remember that this method is called in the thread
        so that some logic must be done to ensure that the application level
        handlers are called in the application thread.
        """
        pass


HBChannelABC.register(HBChannel)


class ZMQSocketChannel:
    """A ZMQ socket wrapper"""

    def __init__(self, socket: zmq.Socket, session: Session, loop: t.Any = None) -> None:
        """Create a channel.

        Parameters
        ----------
        socket : :class:`zmq.Socket`
            The ZMQ socket to use.
        session : :class:`session.Session`
            The session to use.
        loop
            Unused here, for other implementations
        """
        super().__init__()

        self.socket: t.Optional[zmq.Socket] = socket
        self.session = session

    def _recv(self, **kwargs: t.Any) -> t.Dict[str, t.Any]:
        assert self.socket is not None
        msg = self.socket.recv_multipart(**kwargs)
        ident, smsg = self.session.feed_identities(msg)
        return self.session.deserialize(smsg)

    def get_msg(self, timeout: t.Optional[float] = None) -> t.Dict[str, t.Any]:
        """Gets a message if there is one that is ready."""
        assert self.socket is not None
        timeout_ms = None if timeout is None else int(timeout * 1000)  # seconds to ms
        ready = self.socket.poll(timeout_ms)
        if ready:
            res = self._recv()
            return res
        else:
            raise Empty

    def get_msgs(self) -> t.List[t.Dict[str, t.Any]]:
        """Get all messages that are currently ready."""
        msgs = []
        while True:
            try:
                msgs.append(self.get_msg())
            except Empty:
                break
        return msgs

    def msg_ready(self) -> bool:
        """Is there a message that has been received?"""
        assert self.socket is not None
        return bool(self.socket.poll(timeout=0))

    def close(self) -> None:
        """Close the socket channel."""
        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
            self.socket = None

    stop = close

    def is_alive(self) -> bool:
        """Test whether the channel is alive."""
        return self.socket is not None

    def send(self, msg: t.Dict[str, t.Any]) -> None:
        """Pass a message to the ZMQ socket to send"""
        assert self.socket is not None
        self.session.send(self.socket, msg)

    def start(self) -> None:
        """Start the socket channel."""
        pass


class AsyncZMQSocketChannel(ZMQSocketChannel):
    """A ZMQ socket in an async API"""

    socket: zmq.asyncio.Socket

    def __init__(self, socket: zmq.asyncio.Socket, session: Session, loop: t.Any = None) -> None:
        """Create a channel.

        Parameters
        ----------
        socket : :class:`zmq.asyncio.Socket`
            The ZMQ socket to use.
        session : :class:`session.Session`
            The session to use.
        loop
            Unused here, for other implementations
        """
        if not isinstance(socket, zmq.asyncio.Socket):
            msg = "Socket must be asyncio"  # type:ignore[unreachable]
            raise ValueError(msg)
        super().__init__(socket, session)

    async def _recv(self, **kwargs: t.Any) -> t.Dict[str, t.Any]:  # type:ignore[override]
        assert self.socket is not None
        msg = await self.socket.recv_multipart(**kwargs)
        _, smsg = self.session.feed_identities(msg)
        return self.session.deserialize(smsg)

    async def get_msg(  # type:ignore[override]
        self, timeout: t.Optional[float] = None
    ) -> t.Dict[str, t.Any]:
        """Gets a message if there is one that is ready."""
        assert self.socket is not None
        timeout_ms = None if timeout is None else int(timeout * 1000)  # seconds to ms
        ready = await self.socket.poll(timeout_ms)
        if ready:
            res = await self._recv()
            return res
        else:
            raise Empty

    async def get_msgs(self) -> t.List[t.Dict[str, t.Any]]:  # type:ignore[override]
        """Get all messages that are currently ready."""
        msgs = []
        while True:
            try:
                msgs.append(await self.get_msg())
            except Empty:
                break
        return msgs

    async def msg_ready(self) -> bool:  # type:ignore[override]
        """Is there a message that has been received?"""
        assert self.socket is not None
        return bool(await self.socket.poll(timeout=0))

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_additional_thread_info_regular.py ===
from _pydevd_bundle.pydevd_constants import (
    STATE_RUN,
    PYTHON_SUSPEND,
    SUPPORT_GEVENT,
    ForkSafeLock,
    _current_frames,
    STATE_SUSPEND,
    get_global_debugger,
    get_thread_id,
)
from _pydev_bundle import pydev_log
from _pydev_bundle._pydev_saved_modules import threading
from _pydev_bundle.pydev_is_thread_alive import is_thread_alive
import weakref

version = 11


# =======================================================================================================================
# PyDBAdditionalThreadInfo
# =======================================================================================================================
# fmt: off
# IFDEF CYTHON
# cdef class PyDBAdditionalThreadInfo:
# ELSE
class PyDBAdditionalThreadInfo(object):
# ENDIF
# fmt: on

    # Note: the params in cython are declared in pydevd_cython.pxd.
    # fmt: off
    # IFDEF CYTHON
    # ELSE
    __slots__ = [
        "pydev_state",
        "pydev_step_stop",
        "pydev_original_step_cmd",
        "pydev_step_cmd",
        "pydev_notify_kill",
        "pydev_django_resolve_frame",
        "pydev_call_from_jinja2",
        "pydev_call_inside_jinja2",
        "is_tracing",
        "conditional_breakpoint_exception",
        "pydev_message",
        "suspend_type",
        "pydev_next_line",
        "pydev_func_name",
        "suspended_at_unhandled",
        "trace_suspend_type",
        "top_level_thread_tracer_no_back_frames",
        "top_level_thread_tracer_unhandled",
        "thread_tracer",
        "step_in_initial_location",
        # Used for CMD_SMART_STEP_INTO (to know which smart step into variant to use)
        "pydev_smart_parent_offset",
        "pydev_smart_child_offset",
        # Used for CMD_SMART_STEP_INTO (list[_pydevd_bundle.pydevd_bytecode_utils.Variant])
        # Filled when the cmd_get_smart_step_into_variants is requested (so, this is a copy
        # of the last request for a given thread and pydev_smart_parent_offset/pydev_smart_child_offset relies on it).
        "pydev_smart_step_into_variants",
        "target_id_to_smart_step_into_variant",
        "pydev_use_scoped_step_frame",
        "weak_thread",
        "is_in_wait_loop",
    ]
    # ENDIF
    # fmt: on

    def __init__(self):
        self.pydev_state = STATE_RUN  # STATE_RUN or STATE_SUSPEND
        self.pydev_step_stop = None

        # Note: we have `pydev_original_step_cmd` and `pydev_step_cmd` because the original is to
        # say the action that started it and the other is to say what's the current tracing behavior
        # (because it's possible that we start with a step over but may have to switch to a
        # different step strategy -- for instance, if a step over is done and we return the current
        # method the strategy is changed to a step in).

        self.pydev_original_step_cmd = -1  # Something as CMD_STEP_INTO, CMD_STEP_OVER, etc.
        self.pydev_step_cmd = -1  # Something as CMD_STEP_INTO, CMD_STEP_OVER, etc.

        self.pydev_notify_kill = False
        self.pydev_django_resolve_frame = False
        self.pydev_call_from_jinja2 = None
        self.pydev_call_inside_jinja2 = None
        self.is_tracing = 0
        self.conditional_breakpoint_exception = None
        self.pydev_message = ""
        self.suspend_type = PYTHON_SUSPEND
        self.pydev_next_line = -1
        self.pydev_func_name = ".invalid."  # Must match the type in cython
        self.suspended_at_unhandled = False
        self.trace_suspend_type = "trace"  # 'trace' or 'frame_eval'
        self.top_level_thread_tracer_no_back_frames = []
        self.top_level_thread_tracer_unhandled = None
        self.thread_tracer = None
        self.step_in_initial_location = None
        self.pydev_smart_parent_offset = -1
        self.pydev_smart_child_offset = -1
        self.pydev_smart_step_into_variants = ()
        self.target_id_to_smart_step_into_variant = {}

        # Flag to indicate ipython use-case where each line will be executed as a call/line/return
        # in a new new frame but in practice we want to consider each new frame as if it was all
        # part of the same frame.
        #
        # In practice this means that a step over shouldn't revert to a step in and we need some
        # special logic to know when we should stop in a step over as we need to consider 2
        # different frames as being equal if they're logically the continuation of a frame
        # being executed by ipython line by line.
        #
        # See: https://github.com/microsoft/debugpy/issues/869#issuecomment-1132141003
        self.pydev_use_scoped_step_frame = False
        self.weak_thread = None

        # Purpose: detect if this thread is suspended and actually in the wait loop
        # at this time (otherwise it may be suspended but still didn't reach a point.
        # to pause).
        self.is_in_wait_loop = False

    # fmt: off
    # IFDEF CYTHON
    # cpdef object _get_related_thread(self):
    # ELSE
    def _get_related_thread(self):
    # ENDIF
    # fmt: on
        if self.pydev_notify_kill:  # Already killed
            return None

        if self.weak_thread is None:
            return None

        thread = self.weak_thread()
        if thread is None:
            return False

        if not is_thread_alive(thread):
            return None

        if thread._ident is None:  # Can this happen?
            pydev_log.critical("thread._ident is None in _get_related_thread!")
            return None

        if threading._active.get(thread._ident) is not thread:
            return None

        return thread

    # fmt: off
    # IFDEF CYTHON
    # cpdef bint _is_stepping(self):
    # ELSE
    def _is_stepping(self):
    # ENDIF
    # fmt: on
        if self.pydev_state == STATE_RUN and self.pydev_step_cmd != -1:
            # This means actually stepping in a step operation.
            return True

        if self.pydev_state == STATE_SUSPEND and self.is_in_wait_loop:
            # This means stepping because it was suspended but still didn't
            # reach a suspension point.
            return True

        return False

    # fmt: off
    # IFDEF CYTHON
    # cpdef get_topmost_frame(self, thread):
    # ELSE
    def get_topmost_frame(self, thread):
    # ENDIF
    # fmt: on
        """
        Gets the topmost frame for the given thread. Note that it may be None
        and callers should remove the reference to the frame as soon as possible
        to avoid disturbing user code.
        """
        # sys._current_frames(): dictionary with thread id -> topmost frame
        current_frames = _current_frames()
        topmost_frame = current_frames.get(thread._ident)
        if topmost_frame is None:
            # Note: this is expected for dummy threads (so, getting the topmost frame should be
            # treated as optional).
            pydev_log.info(
                "Unable to get topmost frame for thread: %s, thread.ident: %s, id(thread): %s\nCurrent frames: %s.\n" "GEVENT_SUPPORT: %s",
                thread,
                thread.ident,
                id(thread),
                current_frames,
                SUPPORT_GEVENT,
            )

        return topmost_frame

    # fmt: off
    # IFDEF CYTHON
    # cpdef update_stepping_info(self):
    # ELSE
    def update_stepping_info(self):
    # ENDIF
    # fmt: on
        _update_stepping_info(self)

    def __str__(self):
        return "State:%s Stop:%s Cmd: %s Kill:%s" % (self.pydev_state, self.pydev_step_stop, self.pydev_step_cmd, self.pydev_notify_kill)


_set_additional_thread_info_lock = ForkSafeLock()
_next_additional_info = [PyDBAdditionalThreadInfo()]


# fmt: off
# IFDEF CYTHON
# cpdef set_additional_thread_info(thread):
# ELSE
def set_additional_thread_info(thread):
# ENDIF
# fmt: on
    try:
        additional_info = thread.additional_info
        if additional_info is None:
            raise AttributeError()
    except:
        with _set_additional_thread_info_lock:
            # If it's not there, set it within a lock to avoid any racing
            # conditions.
            try:
                additional_info = thread.additional_info
            except:
                additional_info = None

            if additional_info is None:
                # Note: don't call PyDBAdditionalThreadInfo constructor at this
                # point as it can piggy-back into the debugger which could
                # get here again, rather get the global ref which was pre-created
                # and add a new entry only after we set thread.additional_info.
                additional_info = _next_additional_info[0]
                thread.additional_info = additional_info
                additional_info.weak_thread = weakref.ref(thread)
                add_additional_info(additional_info)
                del _next_additional_info[:]
                _next_additional_info.append(PyDBAdditionalThreadInfo())

    return additional_info


# fmt: off
# IFDEF CYTHON
# cdef set _all_infos
# cdef set _infos_stepping
# cdef object _update_infos_lock
# ELSE
# ENDIF
# fmt: on

_all_infos = set()
_infos_stepping = set()
_update_infos_lock = ForkSafeLock()


# fmt: off
# IFDEF CYTHON
# cdef _update_stepping_info(PyDBAdditionalThreadInfo info):
# ELSE
def _update_stepping_info(info):
# ENDIF
# fmt: on

    global _infos_stepping
    global _all_infos

    with _update_infos_lock:
        # Removes entries that are no longer valid.
        new_all_infos = set()
        for info in _all_infos:
            if info._get_related_thread() is not None:
                new_all_infos.add(info)
        _all_infos = new_all_infos

        new_stepping = set()
        for info in _all_infos:
            if info._is_stepping():
                new_stepping.add(info)
        _infos_stepping = new_stepping

    py_db = get_global_debugger()
    if py_db is not None and not py_db.pydb_disposed:
        thread = info.weak_thread()
        if thread is not None:
            thread_id = get_thread_id(thread)
            _queue, event = py_db.get_internal_queue_and_event(thread_id)
            event.set()

# fmt: off
# IFDEF CYTHON
# cpdef add_additional_info(PyDBAdditionalThreadInfo info):
# ELSE
def add_additional_info(info):
# ENDIF
# fmt: on
    with _update_infos_lock:
        _all_infos.add(info)
        if info._is_stepping():
            _infos_stepping.add(info)

# fmt: off
# IFDEF CYTHON
# cpdef remove_additional_info(PyDBAdditionalThreadInfo info):
# ELSE
def remove_additional_info(info):
# ENDIF
# fmt: on
    with _update_infos_lock:
        _all_infos.discard(info)
        _infos_stepping.discard(info)


# fmt: off
# IFDEF CYTHON
# cpdef bint any_thread_stepping():
# ELSE
def any_thread_stepping():
# ENDIF
# fmt: on
    return bool(_infos_stepping)

# === NexusCore/openenv\Lib\site-packages\google\oauth2\_reauth_async.py ===
# Copyright 2021 Google LLC
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

"""A module that provides functions for handling rapt authentication.

Reauth is a process of obtaining additional authentication (such as password,
security token, etc.) while refreshing OAuth 2.0 credentials for a user.

Credentials that use the Reauth flow must have the reauth scope,
``https://www.googleapis.com/auth/accounts.reauth``.

This module provides a high-level function for executing the Reauth process,
:func:`refresh_grant`, and lower-level helpers for doing the individual
steps of the reauth process.

Those steps are:

1. Obtaining a list of challenges from the reauth server.
2. Running through each challenge and sending the result back to the reauth
   server.
3. Refreshing the access token using the returned rapt token.
"""

import sys

from google.auth import exceptions
from google.oauth2 import _client
from google.oauth2 import _client_async
from google.oauth2 import challenges
from google.oauth2 import reauth


async def _get_challenges(
    request, supported_challenge_types, access_token, requested_scopes=None
):
    """Does initial request to reauth API to get the challenges.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        supported_challenge_types (Sequence[str]): list of challenge names
            supported by the manager.
        access_token (str): Access token with reauth scopes.
        requested_scopes (Optional(Sequence[str])): Authorized scopes for the credentials.

    Returns:
        dict: The response from the reauth API.
    """
    body = {"supportedChallengeTypes": supported_challenge_types}
    if requested_scopes:
        body["oauthScopesForDomainPolicyLookup"] = requested_scopes

    return await _client_async._token_endpoint_request(
        request,
        reauth._REAUTH_API + ":start",
        body,
        access_token=access_token,
        use_json=True,
    )


async def _send_challenge_result(
    request, session_id, challenge_id, client_input, access_token
):
    """Attempt to refresh access token by sending next challenge result.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        session_id (str): session id returned by the initial reauth call.
        challenge_id (str): challenge id returned by the initial reauth call.
        client_input: dict with a challenge-specific client input. For example:
            ``{'credential': password}`` for password challenge.
        access_token (str): Access token with reauth scopes.

    Returns:
        dict: The response from the reauth API.
    """
    body = {
        "sessionId": session_id,
        "challengeId": challenge_id,
        "action": "RESPOND",
        "proposalResponse": client_input,
    }

    return await _client_async._token_endpoint_request(
        request,
        reauth._REAUTH_API + "/{}:continue".format(session_id),
        body,
        access_token=access_token,
        use_json=True,
    )


async def _run_next_challenge(msg, request, access_token):
    """Get the next challenge from msg and run it.

    Args:
        msg (dict): Reauth API response body (either from the initial request to
            https://reauth.googleapis.com/v2/sessions:start or from sending the
            previous challenge response to
            https://reauth.googleapis.com/v2/sessions/id:continue)
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        access_token (str): reauth access token

    Returns:
        dict: The response from the reauth API.

    Raises:
        google.auth.exceptions.ReauthError: if reauth failed.
    """
    for challenge in msg["challenges"]:
        if challenge["status"] != "READY":
            # Skip non-activated challenges.
            continue
        c = challenges.AVAILABLE_CHALLENGES.get(challenge["challengeType"], None)
        if not c:
            raise exceptions.ReauthFailError(
                "Unsupported challenge type {0}. Supported types: {1}".format(
                    challenge["challengeType"],
                    ",".join(list(challenges.AVAILABLE_CHALLENGES.keys())),
                )
            )
        if not c.is_locally_eligible:
            raise exceptions.ReauthFailError(
                "Challenge {0} is not locally eligible".format(
                    challenge["challengeType"]
                )
            )
        client_input = c.obtain_challenge_input(challenge)
        if not client_input:
            return None
        return await _send_challenge_result(
            request,
            msg["sessionId"],
            challenge["challengeId"],
            client_input,
            access_token,
        )
    return None


async def _obtain_rapt(request, access_token, requested_scopes):
    """Given an http request method and reauth access token, get rapt token.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        access_token (str): reauth access token
        requested_scopes (Sequence[str]): scopes required by the client application

    Returns:
        str: The rapt token.

    Raises:
        google.auth.exceptions.ReauthError: if reauth failed
    """
    msg = await _get_challenges(
        request,
        list(challenges.AVAILABLE_CHALLENGES.keys()),
        access_token,
        requested_scopes,
    )

    if msg["status"] == reauth._AUTHENTICATED:
        return msg["encodedProofOfReauthToken"]

    for _ in range(0, reauth.RUN_CHALLENGE_RETRY_LIMIT):
        if not (
            msg["status"] == reauth._CHALLENGE_REQUIRED
            or msg["status"] == reauth._CHALLENGE_PENDING
        ):
            raise exceptions.ReauthFailError(
                "Reauthentication challenge failed due to API error: {}".format(
                    msg["status"]
                )
            )

        if not reauth.is_interactive():
            raise exceptions.ReauthFailError(
                "Reauthentication challenge could not be answered because you are not"
                " in an interactive session."
            )

        msg = await _run_next_challenge(msg, request, access_token)

        if msg["status"] == reauth._AUTHENTICATED:
            return msg["encodedProofOfReauthToken"]

    # If we got here it means we didn't get authenticated.
    raise exceptions.ReauthFailError("Failed to obtain rapt token.")


async def get_rapt_token(
    request, client_id, client_secret, refresh_token, token_uri, scopes=None
):
    """Given an http request method and refresh_token, get rapt token.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        client_id (str): client id to get access token for reauth scope.
        client_secret (str): client secret for the client_id
        refresh_token (str): refresh token to refresh access token
        token_uri (str): uri to refresh access token
        scopes (Optional(Sequence[str])): scopes required by the client application

    Returns:
        str: The rapt token.
    Raises:
        google.auth.exceptions.RefreshError: If reauth failed.
    """
    sys.stderr.write("Reauthentication required.\n")

    # Get access token for reauth.
    access_token, _, _, _ = await _client_async.refresh_grant(
        request=request,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        token_uri=token_uri,
        scopes=[reauth._REAUTH_SCOPE],
    )

    # Get rapt token from reauth API.
    rapt_token = await _obtain_rapt(request, access_token, requested_scopes=scopes)

    return rapt_token


async def refresh_grant(
    request,
    token_uri,
    refresh_token,
    client_id,
    client_secret,
    scopes=None,
    rapt_token=None,
    enable_reauth_refresh=False,
):
    """Implements the reauthentication flow.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests. This must be an aiohttp request.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        refresh_token (str): The refresh token to use to get a new access
            token.
        client_id (str): The OAuth 2.0 application's client ID.
        client_secret (str): The Oauth 2.0 appliaction's client secret.
        scopes (Optional(Sequence[str])): Scopes to request. If present, all
            scopes must be authorized for the refresh token. Useful if refresh
            token has a wild card scope (e.g.
            'https://www.googleapis.com/auth/any-api').
        rapt_token (Optional(str)): The rapt token for reauth.
        enable_reauth_refresh (Optional[bool]): Whether reauth refresh flow
            should be used. The default value is False. This option is for
            gcloud only, other users should use the default value.

    Returns:
        Tuple[str, Optional[str], Optional[datetime], Mapping[str, str], str]: The
            access token, new refresh token, expiration, the additional data
            returned by the token endpoint, and the rapt token.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    body = {
        "grant_type": _client._REFRESH_GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    if scopes:
        body["scope"] = " ".join(scopes)
    if rapt_token:
        body["rapt"] = rapt_token

    response_status_ok, response_data, retryable_error = await _client_async._token_endpoint_request_no_throw(
        request, token_uri, body
    )
    if (
        not response_status_ok
        and response_data.get("error") == reauth._REAUTH_NEEDED_ERROR
        and (
            response_data.get("error_subtype")
            == reauth._REAUTH_NEEDED_ERROR_INVALID_RAPT
            or response_data.get("error_subtype")
            == reauth._REAUTH_NEEDED_ERROR_RAPT_REQUIRED
        )
    ):
        if not enable_reauth_refresh:
            raise exceptions.RefreshError(
                "Reauthentication is needed. Please run `gcloud auth application-default login` to reauthenticate."
            )

        rapt_token = await get_rapt_token(
            request, client_id, client_secret, refresh_token, token_uri, scopes=scopes
        )
        body["rapt"] = rapt_token
        (
            response_status_ok,
            response_data,
            retryable_error,
        ) = await _client_async._token_endpoint_request_no_throw(
            request, token_uri, body
        )

    if not response_status_ok:
        _client._handle_error_response(response_data, retryable_error)
    refresh_response = _client._handle_refresh_grant_response(
        response_data, refresh_token
    )
    return refresh_response + (rapt_token,)

# === NexusCore/openenv\Lib\site-packages\google\api_core\retry\retry_streaming_async.py ===
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

"""
Generator wrapper for retryable async streaming RPCs.
"""
from __future__ import annotations

from typing import (
    cast,
    Any,
    Callable,
    Iterable,
    AsyncIterator,
    AsyncIterable,
    Awaitable,
    TypeVar,
    AsyncGenerator,
    TYPE_CHECKING,
)

import asyncio
import time
import sys
import functools

from google.api_core.retry.retry_base import _BaseRetry
from google.api_core.retry.retry_base import _retry_error_helper
from google.api_core.retry import exponential_sleep_generator
from google.api_core.retry import build_retry_error
from google.api_core.retry import RetryFailureReason


if TYPE_CHECKING:
    if sys.version_info >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec

    _P = ParamSpec("_P")  # target function call parameters
    _Y = TypeVar("_Y")  # yielded values


async def retry_target_stream(
    target: Callable[_P, AsyncIterable[_Y] | Awaitable[AsyncIterable[_Y]]],
    predicate: Callable[[Exception], bool],
    sleep_generator: Iterable[float],
    timeout: float | None = None,
    on_error: Callable[[Exception], None] | None = None,
    exception_factory: Callable[
        [list[Exception], RetryFailureReason, float | None],
        tuple[Exception, Exception | None],
    ] = build_retry_error,
    init_args: tuple = (),
    init_kwargs: dict = {},
    **kwargs,
) -> AsyncGenerator[_Y, None]:
    """Create a generator wrapper that retries the wrapped stream if it fails.

    This is the lowest-level retry helper. Generally, you'll use the
    higher-level retry helper :class:`AsyncRetry`.

    Args:
        target: The generator function to call and retry.
        predicate: A callable used to determine if an
            exception raised by the target should be considered retryable.
            It should return True to retry or False otherwise.
        sleep_generator: An infinite iterator that determines
            how long to sleep between retries.
        timeout: How long to keep retrying the target.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error: If given, the on_error callback will be called with each
            retryable exception raised by the target. Any error raised by this
            function will *not* be caught.
        exception_factory: A function that is called when the retryable reaches
            a terminal failure state, used to construct an exception to be raised.
            It takes a list of all exceptions encountered, a retry.RetryFailureReason
            enum indicating the failure cause, and the original timeout value
            as arguments. It should return a tuple of the exception to be raised,
            along with the cause exception if any. The default implementation will raise
            a RetryError on timeout, or the last exception encountered otherwise.
        init_args: Positional arguments to pass to the target function.
        init_kwargs: Keyword arguments to pass to the target function.

    Returns:
        AsyncGenerator: A retryable generator that wraps the target generator function.

    Raises:
        ValueError: If the sleep generator stops yielding values.
        Exception: a custom exception specified by the exception_factory if provided.
            If no exception_factory is provided:
                google.api_core.RetryError: If the timeout is exceeded while retrying.
                Exception: If the target raises an error that isn't retryable.
    """
    target_iterator: AsyncIterator[_Y] | None = None
    timeout = kwargs.get("deadline", timeout)
    deadline = time.monotonic() + timeout if timeout else None
    # keep track of retryable exceptions we encounter to pass in to exception_factory
    error_list: list[Exception] = []
    sleep_iter = iter(sleep_generator)
    target_is_generator: bool | None = None

    # continue trying until an attempt completes, or a terminal exception is raised in _retry_error_helper
    # TODO: support max_attempts argument: https://github.com/googleapis/python-api-core/issues/535
    while True:
        # Start a new retry loop
        try:
            # Note: in the future, we can add a ResumptionStrategy object
            # to generate new args between calls. For now, use the same args
            # for each attempt.
            target_output: AsyncIterable[_Y] | Awaitable[AsyncIterable[_Y]] = target(
                *init_args, **init_kwargs
            )
            try:
                # gapic functions return the generator behind an awaitable
                # unwrap the awaitable so we can work with the generator directly
                target_output = await target_output  # type: ignore
            except TypeError:
                # was not awaitable, continue
                pass
            target_iterator = cast(AsyncIterable["_Y"], target_output).__aiter__()

            if target_is_generator is None:
                # Check if target supports generator features (asend, athrow, aclose)
                target_is_generator = bool(getattr(target_iterator, "asend", None))

            sent_in = None
            while True:
                ## Read from target_iterator
                # If the target is a generator, we will advance it with `asend`
                # otherwise, we will use `anext`
                if target_is_generator:
                    next_value = await target_iterator.asend(sent_in)  # type: ignore
                else:
                    next_value = await target_iterator.__anext__()
                ## Yield from Wrapper to caller
                try:
                    # yield latest value from target
                    # exceptions from `athrow` and `aclose` are injected here
                    sent_in = yield next_value
                except GeneratorExit:
                    # if wrapper received `aclose` while waiting on yield,
                    # it will raise GeneratorExit here
                    if target_is_generator:
                        # pass to inner target_iterator for handling
                        await cast(AsyncGenerator["_Y", None], target_iterator).aclose()
                    else:
                        raise
                    return
                except:  # noqa: E722
                    # bare except catches any exception passed to `athrow`
                    if target_is_generator:
                        # delegate error handling to target_iterator
                        await cast(AsyncGenerator["_Y", None], target_iterator).athrow(
                            cast(BaseException, sys.exc_info()[1])
                        )
                    else:
                        raise
            return
        except StopAsyncIteration:
            # if iterator exhausted, return
            return
        # handle exceptions raised by the target_iterator
        # pylint: disable=broad-except
        # This function explicitly must deal with broad exceptions.
        except Exception as exc:
            # defer to shared logic for handling errors
            next_sleep = _retry_error_helper(
                exc,
                deadline,
                sleep_iter,
                error_list,
                predicate,
                on_error,
                exception_factory,
                timeout,
            )
            # if exception not raised, sleep before next attempt
            await asyncio.sleep(next_sleep)

        finally:
            if target_is_generator and target_iterator is not None:
                await cast(AsyncGenerator["_Y", None], target_iterator).aclose()


class AsyncStreamingRetry(_BaseRetry):
    """Exponential retry decorator for async streaming rpcs.

    This class returns an AsyncGenerator when called, which wraps the target
    stream in retry logic. If any exception is raised by the target, the
    entire stream will be retried within the wrapper.

    Although the default behavior is to retry transient API errors, a
    different predicate can be provided to retry other exceptions.

    Important Note: when a stream is encounters a retryable error, it will
    silently construct a fresh iterator instance in the background
    and continue yielding (likely duplicate) values as if no error occurred.
    This is the most general way to retry a stream, but it often is not the
    desired behavior. Example: iter([1, 2, 1/0]) -> [1, 2, 1, 2, ...]

    There are two ways to build more advanced retry logic for streams:

    1. Wrap the target
        Use a ``target`` that maintains state between retries, and creates a
        different generator on each retry call. For example, you can wrap a
        grpc call in a function that modifies the request based on what has
        already been returned:

        .. code-block:: python

            async def attempt_with_modified_request(target, request, seen_items=[]):
                # remove seen items from request on each attempt
                new_request = modify_request(request, seen_items)
                new_generator = await target(new_request)
                async for item in new_generator:
                    yield item
                    seen_items.append(item)

            retry_wrapped = AsyncRetry(is_stream=True,...)(attempt_with_modified_request, target, request, [])

        2. Wrap the retry generator
            Alternatively, you can wrap the retryable generator itself before
            passing it to the end-user to add a filter on the stream. For
            example, you can keep track of the items that were successfully yielded
            in previous retry attempts, and only yield new items when the
            new attempt surpasses the previous ones:

            .. code-block:: python

                async def retryable_with_filter(target):
                    stream_idx = 0
                    # reset stream_idx when the stream is retried
                    def on_error(e):
                        nonlocal stream_idx
                        stream_idx = 0
                    # build retryable
                    retryable_gen = AsyncRetry(is_stream=True, ...)(target)
                    # keep track of what has been yielded out of filter
                    seen_items = []
                    async for item in retryable_gen:
                        if stream_idx >= len(seen_items):
                            yield item
                            seen_items.append(item)
                        elif item != previous_stream[stream_idx]:
                            raise ValueError("Stream differs from last attempt")"
                        stream_idx += 1

                filter_retry_wrapped = retryable_with_filter(target)

    Args:
        predicate (Callable[Exception]): A callable that should return ``True``
            if the given exception is retryable.
        initial (float): The minimum amount of time to delay in seconds. This
            must be greater than 0.
        maximum (float): The maximum amount of time to delay in seconds.
        multiplier (float): The multiplier applied to the delay.
        timeout (Optional[float]): How long to keep retrying in seconds.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error (Optional[Callable[Exception]]): A function to call while processing
            a retryable exception. Any error raised by this function will
            *not* be caught.
        is_stream (bool): Indicates whether the input function
            should be treated as a stream function (i.e. an AsyncGenerator,
            or function or coroutine that returns an AsyncIterable).
            If True, the iterable will be wrapped with retry logic, and any
            failed outputs will restart the stream. If False, only the input
            function call itself will be retried. Defaults to False.
            To avoid duplicate values, retryable streams should typically be
            wrapped in additional filter logic before use.
        deadline (float): DEPRECATED use ``timeout`` instead. If set it will
        override ``timeout`` parameter.
    """

    def __call__(
        self,
        func: Callable[..., AsyncIterable[_Y] | Awaitable[AsyncIterable[_Y]]],
        on_error: Callable[[Exception], Any] | None = None,
    ) -> Callable[_P, Awaitable[AsyncGenerator[_Y, None]]]:
        """Wrap a callable with retry behavior.

        Args:
            func (Callable): The callable or stream to add retry behavior to.
            on_error (Optional[Callable[Exception]]): If given, the
                on_error callback will be called with each retryable exception
                raised by the wrapped function. Any error raised by this
                function will *not* be caught. If on_error was specified in the
                constructor, this value will be ignored.

        Returns:
            Callable: A callable that will invoke ``func`` with retry
                behavior.
        """
        if self._on_error is not None:
            on_error = self._on_error

        @functools.wraps(func)
        async def retry_wrapped_func(
            *args: _P.args, **kwargs: _P.kwargs
        ) -> AsyncGenerator[_Y, None]:
            """A wrapper that calls target function with retry."""
            sleep_generator = exponential_sleep_generator(
                self._initial, self._maximum, multiplier=self._multiplier
            )
            return retry_target_stream(
                func,
                self._predicate,
                sleep_generator,
                self._timeout,
                on_error,
                init_args=args,
                init_kwargs=kwargs,
            )

        return retry_wrapped_func

# === NexusCore/openenv\Lib\site-packages\grpc\framework\interfaces\base\base.py ===
# Copyright 2015 gRPC authors.
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
"""The base interface of RPC Framework.

Implementations of this interface support the conduct of "operations":
exchanges between two distinct ends of an arbitrary number of data payloads
and metadata such as a name for the operation, initial and terminal metadata
in each direction, and flow control. These operations may be used for transfers
of data, remote procedure calls, status indication, or anything else
applications choose.
"""

# threading is referenced from specification in this module.
import abc
import enum
import threading  # pylint: disable=unused-import

# pylint: disable=too-many-arguments


class NoSuchMethodError(Exception):
    """Indicates that an unrecognized operation has been called.

    Attributes:
      code: A code value to communicate to the other side of the operation
        along with indication of operation termination. May be None.
      details: A details value to communicate to the other side of the
        operation along with indication of operation termination. May be None.
    """

    def __init__(self, code, details):
        """Constructor.

        Args:
          code: A code value to communicate to the other side of the operation
            along with indication of operation termination. May be None.
          details: A details value to communicate to the other side of the
            operation along with indication of operation termination. May be None.
        """
        super(NoSuchMethodError, self).__init__()
        self.code = code
        self.details = details


class Outcome(object):
    """The outcome of an operation.

    Attributes:
      kind: A Kind value coarsely identifying how the operation terminated.
      code: An application-specific code value or None if no such value was
        provided.
      details: An application-specific details value or None if no such value was
        provided.
    """

    @enum.unique
    class Kind(enum.Enum):
        """Ways in which an operation can terminate."""

        COMPLETED = "completed"
        CANCELLED = "cancelled"
        EXPIRED = "expired"
        LOCAL_SHUTDOWN = "local shutdown"
        REMOTE_SHUTDOWN = "remote shutdown"
        RECEPTION_FAILURE = "reception failure"
        TRANSMISSION_FAILURE = "transmission failure"
        LOCAL_FAILURE = "local failure"
        REMOTE_FAILURE = "remote failure"


class Completion(abc.ABC):
    """An aggregate of the values exchanged upon operation completion.

    Attributes:
      terminal_metadata: A terminal metadata value for the operation.
      code: A code value for the operation.
      message: A message value for the operation.
    """


class OperationContext(abc.ABC):
    """Provides operation-related information and action."""

    @abc.abstractmethod
    def outcome(self):
        """Indicates the operation's outcome (or that the operation is ongoing).

        Returns:
          None if the operation is still active or the Outcome value for the
            operation if it has terminated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_termination_callback(self, callback):
        """Adds a function to be called upon operation termination.

        Args:
          callback: A callable to be passed an Outcome value on operation
            termination.

        Returns:
          None if the operation has not yet terminated and the passed callback will
            later be called when it does terminate, or if the operation has already
            terminated an Outcome value describing the operation termination and the
            passed callback will not be called as a result of this method call.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def time_remaining(self):
        """Describes the length of allowed time remaining for the operation.

        Returns:
          A nonnegative float indicating the length of allowed time in seconds
          remaining for the operation to complete before it is considered to have
          timed out. Zero is returned if the operation has terminated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cancel(self):
        """Cancels the operation if the operation has not yet terminated."""
        raise NotImplementedError()

    @abc.abstractmethod
    def fail(self, exception):
        """Indicates that the operation has failed.

        Args:
          exception: An exception germane to the operation failure. May be None.
        """
        raise NotImplementedError()


class Operator(abc.ABC):
    """An interface through which to participate in an operation."""

    @abc.abstractmethod
    def advance(
        self,
        initial_metadata=None,
        payload=None,
        completion=None,
        allowance=None,
    ):
        """Progresses the operation.

        Args:
          initial_metadata: An initial metadata value. Only one may ever be
            communicated in each direction for an operation, and they must be
            communicated no later than either the first payload or the completion.
          payload: A payload value.
          completion: A Completion value. May only ever be non-None once in either
            direction, and no payloads may be passed after it has been communicated.
          allowance: A positive integer communicating the number of additional
            payloads allowed to be passed by the remote side of the operation.
        """
        raise NotImplementedError()


class ProtocolReceiver(abc.ABC):
    """A means of receiving protocol values during an operation."""

    @abc.abstractmethod
    def context(self, protocol_context):
        """Accepts the protocol context object for the operation.

        Args:
          protocol_context: The protocol context object for the operation.
        """
        raise NotImplementedError()


class Subscription(abc.ABC):
    """Describes customer code's interest in values from the other side.

    Attributes:
      kind: A Kind value describing the overall kind of this value.
      termination_callback: A callable to be passed the Outcome associated with
        the operation after it has terminated. Must be non-None if kind is
        Kind.TERMINATION_ONLY. Must be None otherwise.
      allowance: A callable behavior that accepts positive integers representing
        the number of additional payloads allowed to be passed to the other side
        of the operation. Must be None if kind is Kind.FULL. Must not be None
        otherwise.
      operator: An Operator to be passed values from the other side of the
        operation. Must be non-None if kind is Kind.FULL. Must be None otherwise.
      protocol_receiver: A ProtocolReceiver to be passed protocol objects as they
        become available during the operation. Must be non-None if kind is
        Kind.FULL.
    """

    @enum.unique
    class Kind(enum.Enum):
        NONE = "none"
        TERMINATION_ONLY = "termination only"
        FULL = "full"


class Servicer(abc.ABC):
    """Interface for service implementations."""

    @abc.abstractmethod
    def service(self, group, method, context, output_operator):
        """Services an operation.

        Args:
          group: The group identifier of the operation to be serviced.
          method: The method identifier of the operation to be serviced.
          context: An OperationContext object affording contextual information and
            actions.
          output_operator: An Operator that will accept output values of the
            operation.

        Returns:
          A Subscription via which this object may or may not accept more values of
            the operation.

        Raises:
          NoSuchMethodError: If this Servicer does not handle operations with the
            given group and method.
          abandonment.Abandoned: If the operation has been aborted and there no
            longer is any reason to service the operation.
        """
        raise NotImplementedError()


class End(abc.ABC):
    """Common type for entry-point objects on both sides of an operation."""

    @abc.abstractmethod
    def start(self):
        """Starts this object's service of operations."""
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self, grace):
        """Stops this object's service of operations.

        This object will refuse service of new operations as soon as this method is
        called but operations under way at the time of the call may be given a
        grace period during which they are allowed to finish.

        Args:
          grace: A duration of time in seconds to allow ongoing operations to
            terminate before being forcefully terminated by the stopping of this
            End. May be zero to terminate all ongoing operations and immediately
            stop.

        Returns:
          A threading.Event that will be set to indicate all operations having
            terminated and this End having completely stopped. The returned event
            may not be set until after the full grace period (if some ongoing
            operation continues for the full length of the period) or it may be set
            much sooner (if for example this End had no operations in progress at
            the time its stop method was called).
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def operate(
        self,
        group,
        method,
        subscription,
        timeout,
        initial_metadata=None,
        payload=None,
        completion=None,
        protocol_options=None,
    ):
        """Commences an operation.

        Args:
          group: The group identifier of the invoked operation.
          method: The method identifier of the invoked operation.
          subscription: A Subscription to which the results of the operation will be
            passed.
          timeout: A length of time in seconds to allow for the operation.
          initial_metadata: An initial metadata value to be sent to the other side
            of the operation. May be None if the initial metadata will be later
            passed via the returned operator or if there will be no initial metadata
            passed at all.
          payload: An initial payload for the operation.
          completion: A Completion value indicating the end of transmission to the
            other side of the operation.
          protocol_options: A value specified by the provider of a Base interface
            implementation affording custom state and behavior.

        Returns:
          A pair of objects affording information about the operation and action
            continuing the operation. The first element of the returned pair is an
            OperationContext for the operation and the second element of the
            returned pair is an Operator to which operation values not passed in
            this call should later be passed.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def operation_stats(self):
        """Reports the number of terminated operations broken down by outcome.

        Returns:
          A dictionary from Outcome.Kind value to an integer identifying the number
            of operations that terminated with that outcome kind.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_idle_action(self, action):
        """Adds an action to be called when this End has no ongoing operations.

        Args:
          action: A callable that accepts no arguments.
        """
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_webagg.py ===
"""Displays Agg images in the browser, with interactivity."""

# The WebAgg backend is divided into two modules:
#
# - `backend_webagg_core.py` contains code necessary to embed a WebAgg
#   plot inside of a web application, and communicate in an abstract
#   way over a web socket.
#
# - `backend_webagg.py` contains a concrete implementation of a basic
#   application, implemented with tornado.

from contextlib import contextmanager
import errno
from io import BytesIO
import json
import mimetypes
from pathlib import Path
import random
import sys
import signal
import threading

try:
    import tornado
except ImportError as err:
    raise RuntimeError("The WebAgg backend requires Tornado.") from err

import tornado.web
import tornado.ioloop
import tornado.websocket

import matplotlib as mpl
from matplotlib.backend_bases import _Backend
from matplotlib._pylab_helpers import Gcf
from . import backend_webagg_core as core
from .backend_webagg_core import (  # noqa: F401 # pylint: disable=W0611
    TimerAsyncio, TimerTornado)


webagg_server_thread = threading.Thread(
    target=lambda: tornado.ioloop.IOLoop.instance().start())


class FigureManagerWebAgg(core.FigureManagerWebAgg):
    _toolbar2_class = core.NavigationToolbar2WebAgg

    @classmethod
    def pyplot_show(cls, *, block=None):
        WebAggApplication.initialize()

        url = "http://{address}:{port}{prefix}".format(
            address=WebAggApplication.address,
            port=WebAggApplication.port,
            prefix=WebAggApplication.url_prefix)

        if mpl.rcParams['webagg.open_in_browser']:
            import webbrowser
            if not webbrowser.open(url):
                print(f"To view figure, visit {url}")
        else:
            print(f"To view figure, visit {url}")

        WebAggApplication.start()


class FigureCanvasWebAgg(core.FigureCanvasWebAggCore):
    manager_class = FigureManagerWebAgg


class WebAggApplication(tornado.web.Application):
    initialized = False
    started = False

    class FavIcon(tornado.web.RequestHandler):
        def get(self):
            self.set_header('Content-Type', 'image/png')
            self.write(Path(mpl.get_data_path(),
                            'images/matplotlib.png').read_bytes())

    class SingleFigurePage(tornado.web.RequestHandler):
        def __init__(self, application, request, *, url_prefix='', **kwargs):
            self.url_prefix = url_prefix
            super().__init__(application, request, **kwargs)

        def get(self, fignum):
            fignum = int(fignum)
            manager = Gcf.get_fig_manager(fignum)

            ws_uri = f'ws://{self.request.host}{self.url_prefix}/'
            self.render(
                "single_figure.html",
                prefix=self.url_prefix,
                ws_uri=ws_uri,
                fig_id=fignum,
                toolitems=core.NavigationToolbar2WebAgg.toolitems,
                canvas=manager.canvas)

    class AllFiguresPage(tornado.web.RequestHandler):
        def __init__(self, application, request, *, url_prefix='', **kwargs):
            self.url_prefix = url_prefix
            super().__init__(application, request, **kwargs)

        def get(self):
            ws_uri = f'ws://{self.request.host}{self.url_prefix}/'
            self.render(
                "all_figures.html",
                prefix=self.url_prefix,
                ws_uri=ws_uri,
                figures=sorted(Gcf.figs.items()),
                toolitems=core.NavigationToolbar2WebAgg.toolitems)

    class MplJs(tornado.web.RequestHandler):
        def get(self):
            self.set_header('Content-Type', 'application/javascript')

            js_content = core.FigureManagerWebAgg.get_javascript()

            self.write(js_content)

    class Download(tornado.web.RequestHandler):
        def get(self, fignum, fmt):
            fignum = int(fignum)
            manager = Gcf.get_fig_manager(fignum)
            self.set_header(
                'Content-Type', mimetypes.types_map.get(fmt, 'binary'))
            buff = BytesIO()
            manager.canvas.figure.savefig(buff, format=fmt)
            self.write(buff.getvalue())

    class WebSocket(tornado.websocket.WebSocketHandler):
        supports_binary = True

        def open(self, fignum):
            self.fignum = int(fignum)
            self.manager = Gcf.get_fig_manager(self.fignum)
            self.manager.add_web_socket(self)
            if hasattr(self, 'set_nodelay'):
                self.set_nodelay(True)

        def on_close(self):
            self.manager.remove_web_socket(self)

        def on_message(self, message):
            message = json.loads(message)
            # The 'supports_binary' message is on a client-by-client
            # basis.  The others affect the (shared) canvas as a
            # whole.
            if message['type'] == 'supports_binary':
                self.supports_binary = message['value']
            else:
                manager = Gcf.get_fig_manager(self.fignum)
                # It is possible for a figure to be closed,
                # but a stale figure UI is still sending messages
                # from the browser.
                if manager is not None:
                    manager.handle_json(message)

        def send_json(self, content):
            self.write_message(json.dumps(content))

        def send_binary(self, blob):
            if self.supports_binary:
                self.write_message(blob, binary=True)
            else:
                data_uri = "data:image/png;base64,{}".format(
                    blob.encode('base64').replace('\n', ''))
                self.write_message(data_uri)

    def __init__(self, url_prefix=''):
        if url_prefix:
            assert url_prefix[0] == '/' and url_prefix[-1] != '/', \
                'url_prefix must start with a "/" and not end with one.'

        super().__init__(
            [
                # Static files for the CSS and JS
                (url_prefix + r'/_static/(.*)',
                 tornado.web.StaticFileHandler,
                 {'path': core.FigureManagerWebAgg.get_static_file_path()}),

                # Static images for the toolbar
                (url_prefix + r'/_images/(.*)',
                 tornado.web.StaticFileHandler,
                 {'path': Path(mpl.get_data_path(), 'images')}),

                # A Matplotlib favicon
                (url_prefix + r'/favicon.ico', self.FavIcon),

                # The page that contains all of the pieces
                (url_prefix + r'/([0-9]+)', self.SingleFigurePage,
                 {'url_prefix': url_prefix}),

                # The page that contains all of the figures
                (url_prefix + r'/?', self.AllFiguresPage,
                 {'url_prefix': url_prefix}),

                (url_prefix + r'/js/mpl.js', self.MplJs),

                # Sends images and events to the browser, and receives
                # events from the browser
                (url_prefix + r'/([0-9]+)/ws', self.WebSocket),

                # Handles the downloading (i.e., saving) of static images
                (url_prefix + r'/([0-9]+)/download.([a-z0-9.]+)',
                 self.Download),
            ],
            template_path=core.FigureManagerWebAgg.get_static_file_path())

    @classmethod
    def initialize(cls, url_prefix='', port=None, address=None):
        if cls.initialized:
            return

        # Create the class instance
        app = cls(url_prefix=url_prefix)

        cls.url_prefix = url_prefix

        # This port selection algorithm is borrowed, more or less
        # verbatim, from IPython.
        def random_ports(port, n):
            """
            Generate a list of n random ports near the given port.

            The first 5 ports will be sequential, and the remaining n-5 will be
            randomly selected in the range [port-2*n, port+2*n].
            """
            for i in range(min(5, n)):
                yield port + i
            for i in range(n - 5):
                yield port + random.randint(-2 * n, 2 * n)

        if address is None:
            cls.address = mpl.rcParams['webagg.address']
        else:
            cls.address = address
        cls.port = mpl.rcParams['webagg.port']
        for port in random_ports(cls.port,
                                 mpl.rcParams['webagg.port_retries']):
            try:
                app.listen(port, cls.address)
            except OSError as e:
                if e.errno != errno.EADDRINUSE:
                    raise
            else:
                cls.port = port
                break
        else:
            raise SystemExit(
                "The webagg server could not be started because an available "
                "port could not be found")

        cls.initialized = True

    @classmethod
    def start(cls):
        import asyncio
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            cls.started = True

        if cls.started:
            return

        """
        IOLoop.running() was removed as of Tornado 2.4; see for example
        https://groups.google.com/forum/#!topic/python-tornado/QLMzkpQBGOY
        Thus there is no correct way to check if the loop has already been
        launched. We may end up with two concurrently running loops in that
        unlucky case with all the expected consequences.
        """
        ioloop = tornado.ioloop.IOLoop.instance()

        def shutdown():
            ioloop.stop()
            print("Server is stopped")
            sys.stdout.flush()
            cls.started = False

        @contextmanager
        def catch_sigint():
            old_handler = signal.signal(
                signal.SIGINT,
                lambda sig, frame: ioloop.add_callback_from_signal(shutdown))
            try:
                yield
            finally:
                signal.signal(signal.SIGINT, old_handler)

        # Set the flag to True *before* blocking on ioloop.start()
        cls.started = True

        print("Press Ctrl+C to stop WebAgg server")
        sys.stdout.flush()
        with catch_sigint():
            ioloop.start()


def ipython_inline_display(figure):
    import tornado.template

    WebAggApplication.initialize()
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        if not webagg_server_thread.is_alive():
            webagg_server_thread.start()

    fignum = figure.number
    tpl = Path(core.FigureManagerWebAgg.get_static_file_path(),
               "ipython_inline_figure.html").read_text()
    t = tornado.template.Template(tpl)
    return t.generate(
        prefix=WebAggApplication.url_prefix,
        fig_id=fignum,
        toolitems=core.NavigationToolbar2WebAgg.toolitems,
        canvas=figure.canvas,
        port=WebAggApplication.port).decode('utf-8')


@_Backend.export
class _BackendWebAgg(_Backend):
    FigureCanvas = FigureCanvasWebAgg
    FigureManager = FigureManagerWebAgg

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\grid_helper_curvelinear.py ===
"""
An experimental support for curvilinear grid.
"""

import functools

import numpy as np

import matplotlib as mpl
from matplotlib import _api
from matplotlib.path import Path
from matplotlib.transforms import Affine2D, IdentityTransform
from .axislines import (
    _FixedAxisArtistHelperBase, _FloatingAxisArtistHelperBase, GridHelperBase)
from .axis_artist import AxisArtist
from .grid_finder import GridFinder


def _value_and_jacobian(func, xs, ys, xlims, ylims):
    """
    Compute *func* and its derivatives along x and y at positions *xs*, *ys*,
    while ensuring that finite difference calculations don't try to evaluate
    values outside of *xlims*, *ylims*.
    """
    eps = np.finfo(float).eps ** (1/2)  # see e.g. scipy.optimize.approx_fprime
    val = func(xs, ys)
    # Take the finite difference step in the direction where the bound is the
    # furthest; the step size is min of epsilon and distance to that bound.
    xlo, xhi = sorted(xlims)
    dxlo = xs - xlo
    dxhi = xhi - xs
    xeps = (np.take([-1, 1], dxhi >= dxlo)
            * np.minimum(eps, np.maximum(dxlo, dxhi)))
    val_dx = func(xs + xeps, ys)
    ylo, yhi = sorted(ylims)
    dylo = ys - ylo
    dyhi = yhi - ys
    yeps = (np.take([-1, 1], dyhi >= dylo)
            * np.minimum(eps, np.maximum(dylo, dyhi)))
    val_dy = func(xs, ys + yeps)
    return (val, (val_dx - val) / xeps, (val_dy - val) / yeps)


class FixedAxisArtistHelper(_FixedAxisArtistHelperBase):
    """
    Helper class for a fixed axis.
    """

    def __init__(self, grid_helper, side, nth_coord_ticks=None):
        """
        nth_coord = along which coordinate value varies.
         nth_coord = 0 ->  x axis, nth_coord = 1 -> y axis
        """

        super().__init__(loc=side)

        self.grid_helper = grid_helper
        if nth_coord_ticks is None:
            nth_coord_ticks = self.nth_coord
        self.nth_coord_ticks = nth_coord_ticks

        self.side = side

    def update_lim(self, axes):
        self.grid_helper.update_lim(axes)

    def get_tick_transform(self, axes):
        return axes.transData

    def get_tick_iterators(self, axes):
        """tick_loc, tick_angle, tick_label"""
        v1, v2 = axes.get_ylim() if self.nth_coord == 0 else axes.get_xlim()
        if v1 > v2:  # Inverted limits.
            side = {"left": "right", "right": "left",
                    "top": "bottom", "bottom": "top"}[self.side]
        else:
            side = self.side

        angle_tangent = dict(left=90, right=90, bottom=0, top=0)[side]

        def iter_major():
            for nth_coord, show_labels in [
                    (self.nth_coord_ticks, True), (1 - self.nth_coord_ticks, False)]:
                gi = self.grid_helper._grid_info[["lon", "lat"][nth_coord]]
                for tick in gi["ticks"][side]:
                    yield (*tick["loc"], angle_tangent,
                           (tick["label"] if show_labels else ""))

        return iter_major(), iter([])


class FloatingAxisArtistHelper(_FloatingAxisArtistHelperBase):

    def __init__(self, grid_helper, nth_coord, value, axis_direction=None):
        """
        nth_coord = along which coordinate value varies.
         nth_coord = 0 ->  x axis, nth_coord = 1 -> y axis
        """
        super().__init__(nth_coord, value)
        self.value = value
        self.grid_helper = grid_helper
        self._extremes = -np.inf, np.inf
        self._line_num_points = 100  # number of points to create a line

    def set_extremes(self, e1, e2):
        if e1 is None:
            e1 = -np.inf
        if e2 is None:
            e2 = np.inf
        self._extremes = e1, e2

    def update_lim(self, axes):
        self.grid_helper.update_lim(axes)

        x1, x2 = axes.get_xlim()
        y1, y2 = axes.get_ylim()
        grid_finder = self.grid_helper.grid_finder
        extremes = grid_finder.extreme_finder(grid_finder.inv_transform_xy,
                                              x1, y1, x2, y2)

        lon_min, lon_max, lat_min, lat_max = extremes
        e_min, e_max = self._extremes  # ranges of other coordinates
        if self.nth_coord == 0:
            lat_min = max(e_min, lat_min)
            lat_max = min(e_max, lat_max)
        elif self.nth_coord == 1:
            lon_min = max(e_min, lon_min)
            lon_max = min(e_max, lon_max)

        lon_levs, lon_n, lon_factor = \
            grid_finder.grid_locator1(lon_min, lon_max)
        lat_levs, lat_n, lat_factor = \
            grid_finder.grid_locator2(lat_min, lat_max)

        if self.nth_coord == 0:
            xx0 = np.full(self._line_num_points, self.value)
            yy0 = np.linspace(lat_min, lat_max, self._line_num_points)
            xx, yy = grid_finder.transform_xy(xx0, yy0)
        elif self.nth_coord == 1:
            xx0 = np.linspace(lon_min, lon_max, self._line_num_points)
            yy0 = np.full(self._line_num_points, self.value)
            xx, yy = grid_finder.transform_xy(xx0, yy0)

        self._grid_info = {
            "extremes": (lon_min, lon_max, lat_min, lat_max),
            "lon_info": (lon_levs, lon_n, np.asarray(lon_factor)),
            "lat_info": (lat_levs, lat_n, np.asarray(lat_factor)),
            "lon_labels": grid_finder._format_ticks(
                1, "bottom", lon_factor, lon_levs),
            "lat_labels": grid_finder._format_ticks(
                2, "bottom", lat_factor, lat_levs),
            "line_xy": (xx, yy),
        }

    def get_axislabel_transform(self, axes):
        return Affine2D()  # axes.transData

    def get_axislabel_pos_angle(self, axes):
        def trf_xy(x, y):
            trf = self.grid_helper.grid_finder.get_transform() + axes.transData
            return trf.transform([x, y]).T

        xmin, xmax, ymin, ymax = self._grid_info["extremes"]
        if self.nth_coord == 0:
            xx0 = self.value
            yy0 = (ymin + ymax) / 2
        elif self.nth_coord == 1:
            xx0 = (xmin + xmax) / 2
            yy0 = self.value
        xy1, dxy1_dx, dxy1_dy = _value_and_jacobian(
            trf_xy, xx0, yy0, (xmin, xmax), (ymin, ymax))
        p = axes.transAxes.inverted().transform(xy1)
        if 0 <= p[0] <= 1 and 0 <= p[1] <= 1:
            d = [dxy1_dy, dxy1_dx][self.nth_coord]
            return xy1, np.rad2deg(np.arctan2(*d[::-1]))
        else:
            return None, None

    def get_tick_transform(self, axes):
        return IdentityTransform()  # axes.transData

    def get_tick_iterators(self, axes):
        """tick_loc, tick_angle, tick_label, (optionally) tick_label"""

        lat_levs, lat_n, lat_factor = self._grid_info["lat_info"]
        yy0 = lat_levs / lat_factor

        lon_levs, lon_n, lon_factor = self._grid_info["lon_info"]
        xx0 = lon_levs / lon_factor

        e0, e1 = self._extremes

        def trf_xy(x, y):
            trf = self.grid_helper.grid_finder.get_transform() + axes.transData
            return trf.transform(np.column_stack(np.broadcast_arrays(x, y))).T

        # find angles
        if self.nth_coord == 0:
            mask = (e0 <= yy0) & (yy0 <= e1)
            (xx1, yy1), (dxx1, dyy1), (dxx2, dyy2) = _value_and_jacobian(
                trf_xy, self.value, yy0[mask], (-np.inf, np.inf), (e0, e1))
            labels = self._grid_info["lat_labels"]

        elif self.nth_coord == 1:
            mask = (e0 <= xx0) & (xx0 <= e1)
            (xx1, yy1), (dxx2, dyy2), (dxx1, dyy1) = _value_and_jacobian(
                trf_xy, xx0[mask], self.value, (-np.inf, np.inf), (e0, e1))
            labels = self._grid_info["lon_labels"]

        labels = [l for l, m in zip(labels, mask) if m]

        angle_normal = np.arctan2(dyy1, dxx1)
        angle_tangent = np.arctan2(dyy2, dxx2)
        mm = (dyy1 == 0) & (dxx1 == 0)  # points with degenerate normal
        angle_normal[mm] = angle_tangent[mm] + np.pi / 2

        tick_to_axes = self.get_tick_transform(axes) - axes.transAxes
        in_01 = functools.partial(
            mpl.transforms._interval_contains_close, (0, 1))

        def iter_major():
            for x, y, normal, tangent, lab \
                    in zip(xx1, yy1, angle_normal, angle_tangent, labels):
                c2 = tick_to_axes.transform((x, y))
                if in_01(c2[0]) and in_01(c2[1]):
                    yield [x, y], *np.rad2deg([normal, tangent]), lab

        return iter_major(), iter([])

    def get_line_transform(self, axes):
        return axes.transData

    def get_line(self, axes):
        self.update_lim(axes)
        x, y = self._grid_info["line_xy"]
        return Path(np.column_stack([x, y]))


class GridHelperCurveLinear(GridHelperBase):
    def __init__(self, aux_trans,
                 extreme_finder=None,
                 grid_locator1=None,
                 grid_locator2=None,
                 tick_formatter1=None,
                 tick_formatter2=None):
        """
        Parameters
        ----------
        aux_trans : `.Transform` or tuple[Callable, Callable]
            The transform from curved coordinates to rectilinear coordinate:
            either a `.Transform` instance (which provides also its inverse),
            or a pair of callables ``(trans, inv_trans)`` that define the
            transform and its inverse.  The callables should have signature::

                x_rect, y_rect = trans(x_curved, y_curved)
                x_curved, y_curved = inv_trans(x_rect, y_rect)

        extreme_finder

        grid_locator1, grid_locator2
            Grid locators for each axis.

        tick_formatter1, tick_formatter2
            Tick formatters for each axis.
        """
        super().__init__()
        self._grid_info = None
        self.grid_finder = GridFinder(aux_trans,
                                      extreme_finder,
                                      grid_locator1,
                                      grid_locator2,
                                      tick_formatter1,
                                      tick_formatter2)

    def update_grid_finder(self, aux_trans=None, **kwargs):
        if aux_trans is not None:
            self.grid_finder.update_transform(aux_trans)
        self.grid_finder.update(**kwargs)
        self._old_limits = None  # Force revalidation.

    @_api.make_keyword_only("3.9", "nth_coord")
    def new_fixed_axis(
            self, loc, nth_coord=None, axis_direction=None, offset=None, axes=None):
        if axes is None:
            axes = self.axes
        if axis_direction is None:
            axis_direction = loc
        helper = FixedAxisArtistHelper(self, loc, nth_coord_ticks=nth_coord)
        axisline = AxisArtist(axes, helper, axis_direction=axis_direction)
        # Why is clip not set on axisline, unlike in new_floating_axis or in
        # the floating_axig.GridHelperCurveLinear subclass?
        return axisline

    def new_floating_axis(self, nth_coord, value, axes=None, axis_direction="bottom"):
        if axes is None:
            axes = self.axes
        helper = FloatingAxisArtistHelper(
            self, nth_coord, value, axis_direction)
        axisline = AxisArtist(axes, helper)
        axisline.line.set_clip_on(True)
        axisline.line.set_clip_box(axisline.axes.bbox)
        # axisline.major_ticklabels.set_visible(True)
        # axisline.minor_ticklabels.set_visible(False)
        return axisline

    def _update_grid(self, x1, y1, x2, y2):
        self._grid_info = self.grid_finder.get_grid_info(x1, y1, x2, y2)

    def get_gridlines(self, which="major", axis="both"):
        grid_lines = []
        if axis in ["both", "x"]:
            for gl in self._grid_info["lon"]["lines"]:
                grid_lines.extend(gl)
        if axis in ["both", "y"]:
            for gl in self._grid_info["lat"]["lines"]:
                grid_lines.extend(gl)
        return grid_lines

    @_api.deprecated("3.9")
    def get_tick_iterator(self, nth_coord, axis_side, minor=False):
        angle_tangent = dict(left=90, right=90, bottom=0, top=0)[axis_side]
        lon_or_lat = ["lon", "lat"][nth_coord]
        if not minor:  # major ticks
            for tick in self._grid_info[lon_or_lat]["ticks"][axis_side]:
                yield *tick["loc"], angle_tangent, tick["label"]
        else:
            for tick in self._grid_info[lon_or_lat]["ticks"][axis_side]:
                yield *tick["loc"], angle_tangent, ""

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\lexers\pygments.py ===
"""
Adaptor classes for using Pygments lexers within prompt_toolkit.

This includes syntax synchronization code, so that we don't have to start
lexing at the beginning of a document, when displaying a very large text.
"""

from __future__ import annotations

import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, Dict, Generator, Iterable, Tuple

from prompt_toolkit.document import Document
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text.base import StyleAndTextTuples
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.styles.pygments import pygments_token_to_classname

from .base import Lexer, SimpleLexer

if TYPE_CHECKING:
    from pygments.lexer import Lexer as PygmentsLexerCls

__all__ = [
    "PygmentsLexer",
    "SyntaxSync",
    "SyncFromStart",
    "RegexSync",
]


class SyntaxSync(metaclass=ABCMeta):
    """
    Syntax synchronizer. This is a tool that finds a start position for the
    lexer. This is especially important when editing big documents; we don't
    want to start the highlighting by running the lexer from the beginning of
    the file. That is very slow when editing.
    """

    @abstractmethod
    def get_sync_start_position(
        self, document: Document, lineno: int
    ) -> tuple[int, int]:
        """
        Return the position from where we can start lexing as a (row, column)
        tuple.

        :param document: `Document` instance that contains all the lines.
        :param lineno: The line that we want to highlight. (We need to return
            this line, or an earlier position.)
        """


class SyncFromStart(SyntaxSync):
    """
    Always start the syntax highlighting from the beginning.
    """

    def get_sync_start_position(
        self, document: Document, lineno: int
    ) -> tuple[int, int]:
        return 0, 0


class RegexSync(SyntaxSync):
    """
    Synchronize by starting at a line that matches the given regex pattern.
    """

    # Never go more than this amount of lines backwards for synchronization.
    # That would be too CPU intensive.
    MAX_BACKWARDS = 500

    # Start lexing at the start, if we are in the first 'n' lines and no
    # synchronization position was found.
    FROM_START_IF_NO_SYNC_POS_FOUND = 100

    def __init__(self, pattern: str) -> None:
        self._compiled_pattern = re.compile(pattern)

    def get_sync_start_position(
        self, document: Document, lineno: int
    ) -> tuple[int, int]:
        """
        Scan backwards, and find a possible position to start.
        """
        pattern = self._compiled_pattern
        lines = document.lines

        # Scan upwards, until we find a point where we can start the syntax
        # synchronization.
        for i in range(lineno, max(-1, lineno - self.MAX_BACKWARDS), -1):
            match = pattern.match(lines[i])
            if match:
                return i, match.start()

        # No synchronization point found. If we aren't that far from the
        # beginning, start at the very beginning, otherwise, just try to start
        # at the current line.
        if lineno < self.FROM_START_IF_NO_SYNC_POS_FOUND:
            return 0, 0
        else:
            return lineno, 0

    @classmethod
    def from_pygments_lexer_cls(cls, lexer_cls: PygmentsLexerCls) -> RegexSync:
        """
        Create a :class:`.RegexSync` instance for this Pygments lexer class.
        """
        patterns = {
            # For Python, start highlighting at any class/def block.
            "Python": r"^\s*(class|def)\s+",
            "Python 3": r"^\s*(class|def)\s+",
            # For HTML, start at any open/close tag definition.
            "HTML": r"<[/a-zA-Z]",
            # For javascript, start at a function.
            "JavaScript": r"\bfunction\b",
            # TODO: Add definitions for other languages.
            #       By default, we start at every possible line.
        }
        p = patterns.get(lexer_cls.name, "^")
        return cls(p)


class _TokenCache(Dict[Tuple[str, ...], str]):
    """
    Cache that converts Pygments tokens into `prompt_toolkit` style objects.

    ``Token.A.B.C`` will be converted into:
    ``class:pygments,pygments.A,pygments.A.B,pygments.A.B.C``
    """

    def __missing__(self, key: tuple[str, ...]) -> str:
        result = "class:" + pygments_token_to_classname(key)
        self[key] = result
        return result


_token_cache = _TokenCache()


class PygmentsLexer(Lexer):
    """
    Lexer that calls a pygments lexer.

    Example::

        from pygments.lexers.html import HtmlLexer
        lexer = PygmentsLexer(HtmlLexer)

    Note: Don't forget to also load a Pygments compatible style. E.g.::

        from prompt_toolkit.styles.from_pygments import style_from_pygments_cls
        from pygments.styles import get_style_by_name
        style = style_from_pygments_cls(get_style_by_name('monokai'))

    :param pygments_lexer_cls: A `Lexer` from Pygments.
    :param sync_from_start: Start lexing at the start of the document. This
        will always give the best results, but it will be slow for bigger
        documents. (When the last part of the document is display, then the
        whole document will be lexed by Pygments on every key stroke.) It is
        recommended to disable this for inputs that are expected to be more
        than 1,000 lines.
    :param syntax_sync: `SyntaxSync` object.
    """

    # Minimum amount of lines to go backwards when starting the parser.
    # This is important when the lines are retrieved in reverse order, or when
    # scrolling upwards. (Due to the complexity of calculating the vertical
    # scroll offset in the `Window` class, lines are not always retrieved in
    # order.)
    MIN_LINES_BACKWARDS = 50

    # When a parser was started this amount of lines back, read the parser
    # until we get the current line. Otherwise, start a new parser.
    # (This should probably be bigger than MIN_LINES_BACKWARDS.)
    REUSE_GENERATOR_MAX_DISTANCE = 100

    def __init__(
        self,
        pygments_lexer_cls: type[PygmentsLexerCls],
        sync_from_start: FilterOrBool = True,
        syntax_sync: SyntaxSync | None = None,
    ) -> None:
        self.pygments_lexer_cls = pygments_lexer_cls
        self.sync_from_start = to_filter(sync_from_start)

        # Instantiate the Pygments lexer.
        self.pygments_lexer = pygments_lexer_cls(
            stripnl=False, stripall=False, ensurenl=False
        )

        # Create syntax sync instance.
        self.syntax_sync = syntax_sync or RegexSync.from_pygments_lexer_cls(
            pygments_lexer_cls
        )

    @classmethod
    def from_filename(
        cls, filename: str, sync_from_start: FilterOrBool = True
    ) -> Lexer:
        """
        Create a `Lexer` from a filename.
        """
        # Inline imports: the Pygments dependency is optional!
        from pygments.lexers import get_lexer_for_filename
        from pygments.util import ClassNotFound

        try:
            pygments_lexer = get_lexer_for_filename(filename)
        except ClassNotFound:
            return SimpleLexer()
        else:
            return cls(pygments_lexer.__class__, sync_from_start=sync_from_start)

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        """
        Create a lexer function that takes a line number and returns the list
        of (style_str, text) tuples as the Pygments lexer returns for that line.
        """
        LineGenerator = Generator[Tuple[int, StyleAndTextTuples], None, None]

        # Cache of already lexed lines.
        cache: dict[int, StyleAndTextTuples] = {}

        # Pygments generators that are currently lexing.
        # Map lexer generator to the line number.
        line_generators: dict[LineGenerator, int] = {}

        def get_syntax_sync() -> SyntaxSync:
            "The Syntax synchronization object that we currently use."
            if self.sync_from_start():
                return SyncFromStart()
            else:
                return self.syntax_sync

        def find_closest_generator(i: int) -> LineGenerator | None:
            "Return a generator close to line 'i', or None if none was found."
            for generator, lineno in line_generators.items():
                if lineno < i and i - lineno < self.REUSE_GENERATOR_MAX_DISTANCE:
                    return generator
            return None

        def create_line_generator(start_lineno: int, column: int = 0) -> LineGenerator:
            """
            Create a generator that yields the lexed lines.
            Each iteration it yields a (line_number, [(style_str, text), ...]) tuple.
            """

            def get_text_fragments() -> Iterable[tuple[str, str]]:
                text = "\n".join(document.lines[start_lineno:])[column:]

                # We call `get_text_fragments_unprocessed`, because `get_tokens` will
                # still replace \r\n and \r by \n.  (We don't want that,
                # Pygments should return exactly the same amount of text, as we
                # have given as input.)
                for _, t, v in self.pygments_lexer.get_tokens_unprocessed(text):
                    # Turn Pygments `Token` object into prompt_toolkit style
                    # strings.
                    yield _token_cache[t], v

            yield from enumerate(split_lines(list(get_text_fragments())), start_lineno)

        def get_generator(i: int) -> LineGenerator:
            """
            Find an already started generator that is close, or create a new one.
            """
            # Find closest line generator.
            generator = find_closest_generator(i)
            if generator:
                return generator

            # No generator found. Determine starting point for the syntax
            # synchronization first.

            # Go at least x lines back. (Make scrolling upwards more
            # efficient.)
            i = max(0, i - self.MIN_LINES_BACKWARDS)

            if i == 0:
                row = 0
                column = 0
            else:
                row, column = get_syntax_sync().get_sync_start_position(document, i)

            # Find generator close to this point, or otherwise create a new one.
            generator = find_closest_generator(i)
            if generator:
                return generator
            else:
                generator = create_line_generator(row, column)

            # If the column is not 0, ignore the first line. (Which is
            # incomplete. This happens when the synchronization algorithm tells
            # us to start parsing in the middle of a line.)
            if column:
                next(generator)
                row += 1

            line_generators[generator] = row
            return generator

        def get_line(i: int) -> StyleAndTextTuples:
            "Return the tokens for a given line number."
            try:
                return cache[i]
            except KeyError:
                generator = get_generator(i)

                # Exhaust the generator, until we find the requested line.
                for num, line in generator:
                    cache[num] = line
                    if num == i:
                        line_generators[generator] = i

                        # Remove the next item from the cache.
                        # (It could happen that it's already there, because of
                        # another generator that started filling these lines,
                        # but we want to synchronize these lines with the
                        # current lexer's state.)
                        if num + 1 in cache:
                            del cache[num + 1]

                        return cache[num]
            return []

        return get_line

# === NexusCore/openenv\Lib\site-packages\tornado\test\options_test.py ===
import datetime
from io import StringIO
import os
import sys
from unittest import mock
import unittest

from tornado.options import OptionParser, Error
from tornado.util import basestring_type

import typing

if typing.TYPE_CHECKING:
    from typing import List  # noqa: F401


class Email:
    def __init__(self, value):
        if isinstance(value, str) and "@" in value:
            self._value = value
        else:
            raise ValueError()

    @property
    def value(self):
        return self._value


class OptionsTest(unittest.TestCase):
    def test_parse_command_line(self):
        options = OptionParser()
        options.define("port", default=80)
        options.parse_command_line(["main.py", "--port=443"])
        self.assertEqual(options.port, 443)

    def test_parse_config_file(self):
        options = OptionParser()
        options.define("port", default=80)
        options.define("username", default="foo")
        options.define("my_path")
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "options_test.cfg"
        )
        options.parse_config_file(config_path)
        self.assertEqual(options.port, 443)
        self.assertEqual(options.username, "李康")
        self.assertEqual(options.my_path, config_path)

    def test_parse_callbacks(self):
        options = OptionParser()
        self.called = False

        def callback():
            self.called = True

        options.add_parse_callback(callback)

        # non-final parse doesn't run callbacks
        options.parse_command_line(["main.py"], final=False)
        self.assertFalse(self.called)

        # final parse does
        options.parse_command_line(["main.py"])
        self.assertTrue(self.called)

        # callbacks can be run more than once on the same options
        # object if there are multiple final parses
        self.called = False
        options.parse_command_line(["main.py"])
        self.assertTrue(self.called)

    def test_help(self):
        options = OptionParser()
        try:
            orig_stderr = sys.stderr
            sys.stderr = StringIO()
            with self.assertRaises(SystemExit):
                options.parse_command_line(["main.py", "--help"])
            usage = sys.stderr.getvalue()
        finally:
            sys.stderr = orig_stderr
        self.assertIn("Usage:", usage)

    def test_subcommand(self):
        base_options = OptionParser()
        base_options.define("verbose", default=False)
        sub_options = OptionParser()
        sub_options.define("foo", type=str)
        rest = base_options.parse_command_line(
            ["main.py", "--verbose", "subcommand", "--foo=bar"]
        )
        self.assertEqual(rest, ["subcommand", "--foo=bar"])
        self.assertTrue(base_options.verbose)
        rest2 = sub_options.parse_command_line(rest)
        self.assertEqual(rest2, [])
        self.assertEqual(sub_options.foo, "bar")

        # the two option sets are distinct
        try:
            orig_stderr = sys.stderr
            sys.stderr = StringIO()
            with self.assertRaises(Error):
                sub_options.parse_command_line(["subcommand", "--verbose"])
        finally:
            sys.stderr = orig_stderr

    def test_setattr(self):
        options = OptionParser()
        options.define("foo", default=1, type=int)
        options.foo = 2
        self.assertEqual(options.foo, 2)

    def test_setattr_type_check(self):
        # setattr requires that options be the right type and doesn't
        # parse from string formats.
        options = OptionParser()
        options.define("foo", default=1, type=int)
        with self.assertRaises(Error):
            options.foo = "2"

    def test_setattr_with_callback(self):
        values = []  # type: List[int]
        options = OptionParser()
        options.define("foo", default=1, type=int, callback=values.append)
        options.foo = 2
        self.assertEqual(values, [2])

    def _sample_options(self):
        options = OptionParser()
        options.define("a", default=1)
        options.define("b", default=2)
        return options

    def test_iter(self):
        options = self._sample_options()
        # OptionParsers always define 'help'.
        self.assertEqual({"a", "b", "help"}, set(iter(options)))

    def test_getitem(self):
        options = self._sample_options()
        self.assertEqual(1, options["a"])

    def test_setitem(self):
        options = OptionParser()
        options.define("foo", default=1, type=int)
        options["foo"] = 2
        self.assertEqual(options["foo"], 2)

    def test_items(self):
        options = self._sample_options()
        # OptionParsers always define 'help'.
        expected = [("a", 1), ("b", 2), ("help", options.help)]
        actual = sorted(options.items())
        self.assertEqual(expected, actual)

    def test_as_dict(self):
        options = self._sample_options()
        expected = {"a": 1, "b": 2, "help": options.help}
        self.assertEqual(expected, options.as_dict())

    def test_group_dict(self):
        options = OptionParser()
        options.define("a", default=1)
        options.define("b", group="b_group", default=2)

        frame = sys._getframe(0)
        this_file = frame.f_code.co_filename
        self.assertEqual({"b_group", "", this_file}, options.groups())

        b_group_dict = options.group_dict("b_group")
        self.assertEqual({"b": 2}, b_group_dict)

        self.assertEqual({}, options.group_dict("nonexistent"))

    def test_mock_patch(self):
        # ensure that our setattr hooks don't interfere with mock.patch
        options = OptionParser()
        options.define("foo", default=1)
        options.parse_command_line(["main.py", "--foo=2"])
        self.assertEqual(options.foo, 2)

        with mock.patch.object(options.mockable(), "foo", 3):
            self.assertEqual(options.foo, 3)
        self.assertEqual(options.foo, 2)

        # Try nested patches mixed with explicit sets
        with mock.patch.object(options.mockable(), "foo", 4):
            self.assertEqual(options.foo, 4)
            options.foo = 5
            self.assertEqual(options.foo, 5)
            with mock.patch.object(options.mockable(), "foo", 6):
                self.assertEqual(options.foo, 6)
            self.assertEqual(options.foo, 5)
        self.assertEqual(options.foo, 2)

    def _define_options(self):
        options = OptionParser()
        options.define("str", type=str)
        options.define("basestring", type=basestring_type)
        options.define("int", type=int)
        options.define("float", type=float)
        options.define("datetime", type=datetime.datetime)
        options.define("timedelta", type=datetime.timedelta)
        options.define("email", type=Email)
        options.define("list-of-int", type=int, multiple=True)
        options.define("list-of-str", type=str, multiple=True)
        return options

    def _check_options_values(self, options):
        self.assertEqual(options.str, "asdf")
        self.assertEqual(options.basestring, "qwer")
        self.assertEqual(options.int, 42)
        self.assertEqual(options.float, 1.5)
        self.assertEqual(options.datetime, datetime.datetime(2013, 4, 28, 5, 16))
        self.assertEqual(options.timedelta, datetime.timedelta(seconds=45))
        self.assertEqual(options.email.value, "tornado@web.com")
        self.assertTrue(isinstance(options.email, Email))
        self.assertEqual(options.list_of_int, [1, 2, 3])
        self.assertEqual(options.list_of_str, ["a", "b", "c"])

    def test_types(self):
        options = self._define_options()
        options.parse_command_line(
            [
                "main.py",
                "--str=asdf",
                "--basestring=qwer",
                "--int=42",
                "--float=1.5",
                "--datetime=2013-04-28 05:16",
                "--timedelta=45s",
                "--email=tornado@web.com",
                "--list-of-int=1,2,3",
                "--list-of-str=a,b,c",
            ]
        )
        self._check_options_values(options)

    def test_types_with_conf_file(self):
        for config_file_name in (
            "options_test_types.cfg",
            "options_test_types_str.cfg",
        ):
            options = self._define_options()
            options.parse_config_file(
                os.path.join(os.path.dirname(__file__), config_file_name)
            )
            self._check_options_values(options)

    def test_multiple_string(self):
        options = OptionParser()
        options.define("foo", type=str, multiple=True)
        options.parse_command_line(["main.py", "--foo=a,b,c"])
        self.assertEqual(options.foo, ["a", "b", "c"])

    def test_multiple_int(self):
        options = OptionParser()
        options.define("foo", type=int, multiple=True)
        options.parse_command_line(["main.py", "--foo=1,3,5:7"])
        self.assertEqual(options.foo, [1, 3, 5, 6, 7])

    def test_error_redefine(self):
        options = OptionParser()
        options.define("foo")
        with self.assertRaises(Error) as cm:
            options.define("foo")
        self.assertRegex(str(cm.exception), "Option.*foo.*already defined")

    def test_error_redefine_underscore(self):
        # Ensure that the dash/underscore normalization doesn't
        # interfere with the redefinition error.
        tests = [
            ("foo-bar", "foo-bar"),
            ("foo_bar", "foo_bar"),
            ("foo-bar", "foo_bar"),
            ("foo_bar", "foo-bar"),
        ]
        for a, b in tests:
            with self.subTest(self, a=a, b=b):
                options = OptionParser()
                options.define(a)
                with self.assertRaises(Error) as cm:
                    options.define(b)
                self.assertRegex(str(cm.exception), "Option.*foo.bar.*already defined")

    def test_dash_underscore_cli(self):
        # Dashes and underscores should be interchangeable.
        for defined_name in ["foo-bar", "foo_bar"]:
            for flag in ["--foo-bar=a", "--foo_bar=a"]:
                options = OptionParser()
                options.define(defined_name)
                options.parse_command_line(["main.py", flag])
                # Attr-style access always uses underscores.
                self.assertEqual(options.foo_bar, "a")
                # Dict-style access allows both.
                self.assertEqual(options["foo-bar"], "a")
                self.assertEqual(options["foo_bar"], "a")

    def test_dash_underscore_file(self):
        # No matter how an option was defined, it can be set with underscores
        # in a config file.
        for defined_name in ["foo-bar", "foo_bar"]:
            options = OptionParser()
            options.define(defined_name)
            options.parse_config_file(
                os.path.join(os.path.dirname(__file__), "options_test.cfg")
            )
            self.assertEqual(options.foo_bar, "a")

    def test_dash_underscore_introspection(self):
        # Original names are preserved in introspection APIs.
        options = OptionParser()
        options.define("with-dash", group="g")
        options.define("with_underscore", group="g")
        all_options = ["help", "with-dash", "with_underscore"]
        self.assertEqual(sorted(options), all_options)
        self.assertEqual(sorted(k for (k, v) in options.items()), all_options)
        self.assertEqual(sorted(options.as_dict().keys()), all_options)

        self.assertEqual(
            sorted(options.group_dict("g")), ["with-dash", "with_underscore"]
        )

        # --help shows CLI-style names with dashes.
        buf = StringIO()
        options.print_help(buf)
        self.assertIn("--with-dash", buf.getvalue())
        self.assertIn("--with-underscore", buf.getvalue())

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\utils.py ===
from __future__ import annotations

import os
import signal
import sys
import threading
from collections import deque
from typing import (
    Callable,
    ContextManager,
    Dict,
    Generator,
    Generic,
    TypeVar,
    Union,
)

from wcwidth import wcwidth

__all__ = [
    "Event",
    "DummyContext",
    "get_cwidth",
    "suspend_to_background_supported",
    "is_conemu_ansi",
    "is_windows",
    "in_main_thread",
    "get_bell_environment_variable",
    "get_term_environment_variable",
    "take_using_weights",
    "to_str",
    "to_int",
    "AnyFloat",
    "to_float",
    "is_dumb_terminal",
]

# Used to ensure sphinx autodoc does not try to import platform-specific
# stuff when documenting win32.py modules.
SPHINX_AUTODOC_RUNNING = "sphinx.ext.autodoc" in sys.modules

_Sender = TypeVar("_Sender", covariant=True)


class Event(Generic[_Sender]):
    """
    Simple event to which event handlers can be attached. For instance::

        class Cls:
            def __init__(self):
                # Define event. The first parameter is the sender.
                self.event = Event(self)

        obj = Cls()

        def handler(sender):
            pass

        # Add event handler by using the += operator.
        obj.event += handler

        # Fire event.
        obj.event()
    """

    def __init__(
        self, sender: _Sender, handler: Callable[[_Sender], None] | None = None
    ) -> None:
        self.sender = sender
        self._handlers: list[Callable[[_Sender], None]] = []

        if handler is not None:
            self += handler

    def __call__(self) -> None:
        "Fire event."
        for handler in self._handlers:
            handler(self.sender)

    def fire(self) -> None:
        "Alias for just calling the event."
        self()

    def add_handler(self, handler: Callable[[_Sender], None]) -> None:
        """
        Add another handler to this callback.
        (Handler should be a callable that takes exactly one parameter: the
        sender object.)
        """
        # Add to list of event handlers.
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[_Sender], None]) -> None:
        """
        Remove a handler from this callback.
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def __iadd__(self, handler: Callable[[_Sender], None]) -> Event[_Sender]:
        """
        `event += handler` notation for adding a handler.
        """
        self.add_handler(handler)
        return self

    def __isub__(self, handler: Callable[[_Sender], None]) -> Event[_Sender]:
        """
        `event -= handler` notation for removing a handler.
        """
        self.remove_handler(handler)
        return self


class DummyContext(ContextManager[None]):
    """
    (contextlib.nested is not available on Py3)
    """

    def __enter__(self) -> None:
        pass

    def __exit__(self, *a: object) -> None:
        pass


class _CharSizesCache(Dict[str, int]):
    """
    Cache for wcwidth sizes.
    """

    LONG_STRING_MIN_LEN = 64  # Minimum string length for considering it long.
    MAX_LONG_STRINGS = 16  # Maximum number of long strings to remember.

    def __init__(self) -> None:
        super().__init__()
        # Keep track of the "long" strings in this cache.
        self._long_strings: deque[str] = deque()

    def __missing__(self, string: str) -> int:
        # Note: We use the `max(0, ...` because some non printable control
        #       characters, like e.g. Ctrl-underscore get a -1 wcwidth value.
        #       It can be possible that these characters end up in the input
        #       text.
        result: int
        if len(string) == 1:
            result = max(0, wcwidth(string))
        else:
            result = sum(self[c] for c in string)

        # Store in cache.
        self[string] = result

        # Rotate long strings.
        # (It's hard to tell what we can consider short...)
        if len(string) > self.LONG_STRING_MIN_LEN:
            long_strings = self._long_strings
            long_strings.append(string)

            if len(long_strings) > self.MAX_LONG_STRINGS:
                key_to_remove = long_strings.popleft()
                if key_to_remove in self:
                    del self[key_to_remove]

        return result


_CHAR_SIZES_CACHE = _CharSizesCache()


def get_cwidth(string: str) -> int:
    """
    Return width of a string. Wrapper around ``wcwidth``.
    """
    return _CHAR_SIZES_CACHE[string]


def suspend_to_background_supported() -> bool:
    """
    Returns `True` when the Python implementation supports
    suspend-to-background. This is typically `False' on Windows systems.
    """
    return hasattr(signal, "SIGTSTP")


def is_windows() -> bool:
    """
    True when we are using Windows.
    """
    return sys.platform == "win32"  # Not 'darwin' or 'linux2'


def is_windows_vt100_supported() -> bool:
    """
    True when we are using Windows, but VT100 escape sequences are supported.
    """
    if sys.platform == "win32":
        # Import needs to be inline. Windows libraries are not always available.
        from prompt_toolkit.output.windows10 import is_win_vt100_enabled

        return is_win_vt100_enabled()

    return False


def is_conemu_ansi() -> bool:
    """
    True when the ConEmu Windows console is used.
    """
    return sys.platform == "win32" and os.environ.get("ConEmuANSI", "OFF") == "ON"


def in_main_thread() -> bool:
    """
    True when the current thread is the main thread.
    """
    return threading.current_thread().__class__.__name__ == "_MainThread"


def get_bell_environment_variable() -> bool:
    """
    True if env variable is set to true (true, TRUE, True, 1).
    """
    value = os.environ.get("PROMPT_TOOLKIT_BELL", "true")
    return value.lower() in ("1", "true")


def get_term_environment_variable() -> str:
    "Return the $TERM environment variable."
    return os.environ.get("TERM", "")


_T = TypeVar("_T")


def take_using_weights(
    items: list[_T], weights: list[int]
) -> Generator[_T, None, None]:
    """
    Generator that keeps yielding items from the items list, in proportion to
    their weight. For instance::

        # Getting the first 70 items from this generator should have yielded 10
        # times A, 20 times B and 40 times C, all distributed equally..
        take_using_weights(['A', 'B', 'C'], [5, 10, 20])

    :param items: List of items to take from.
    :param weights: Integers representing the weight. (Numbers have to be
                    integers, not floats.)
    """
    assert len(items) == len(weights)
    assert len(items) > 0

    # Remove items with zero-weight.
    items2 = []
    weights2 = []
    for item, w in zip(items, weights):
        if w > 0:
            items2.append(item)
            weights2.append(w)

    items = items2
    weights = weights2

    # Make sure that we have some items left.
    if not items:
        raise ValueError("Did't got any items with a positive weight.")

    #
    already_taken = [0 for i in items]
    item_count = len(items)
    max_weight = max(weights)

    i = 0
    while True:
        # Each iteration of this loop, we fill up until by (total_weight/max_weight).
        adding = True
        while adding:
            adding = False

            for item_i, item, weight in zip(range(item_count), items, weights):
                if already_taken[item_i] < i * weight / float(max_weight):
                    yield item
                    already_taken[item_i] += 1
                    adding = True

        i += 1


def to_str(value: Callable[[], str] | str) -> str:
    "Turn callable or string into string."
    if callable(value):
        return to_str(value())
    else:
        return str(value)


def to_int(value: Callable[[], int] | int) -> int:
    "Turn callable or int into int."
    if callable(value):
        return to_int(value())
    else:
        return int(value)


AnyFloat = Union[Callable[[], float], float]


def to_float(value: AnyFloat) -> float:
    "Turn callable or float into float."
    if callable(value):
        return to_float(value())
    else:
        return float(value)


def is_dumb_terminal(term: str | None = None) -> bool:
    """
    True if this terminal type is considered "dumb".

    If so, we should fall back to the simplest possible form of line editing,
    without cursor positioning and color support.
    """
    if term is None:
        return is_dumb_terminal(os.environ.get("TERM", ""))

    return term.lower() in ["dumb", "unknown"]

# === NexusCore/openenv\Lib\site-packages\fsspec\registry.py ===
from __future__ import annotations

import importlib
import types
import warnings

__all__ = ["registry", "get_filesystem_class", "default"]

# internal, mutable
_registry: dict[str, type] = {}

# external, immutable
registry = types.MappingProxyType(_registry)
default = "file"


def register_implementation(name, cls, clobber=False, errtxt=None):
    """Add implementation class to the registry

    Parameters
    ----------
    name: str
        Protocol name to associate with the class
    cls: class or str
        if a class: fsspec-compliant implementation class (normally inherits from
        ``fsspec.AbstractFileSystem``, gets added straight to the registry. If a
        str, the full path to an implementation class like package.module.class,
        which gets added to known_implementations,
        so the import is deferred until the filesystem is actually used.
    clobber: bool (optional)
        Whether to overwrite a protocol with the same name; if False, will raise
        instead.
    errtxt: str (optional)
        If given, then a failure to import the given class will result in this
        text being given.
    """
    if isinstance(cls, str):
        if name in known_implementations and clobber is False:
            if cls != known_implementations[name]["class"]:
                raise ValueError(
                    f"Name ({name}) already in the known_implementations and clobber "
                    f"is False"
                )
        else:
            known_implementations[name] = {
                "class": cls,
                "err": errtxt or f"{cls} import failed for protocol {name}",
            }

    else:
        if name in registry and clobber is False:
            if _registry[name] is not cls:
                raise ValueError(
                    f"Name ({name}) already in the registry and clobber is False"
                )
        else:
            _registry[name] = cls


# protocols mapped to the class which implements them. This dict can be
# updated with register_implementation
known_implementations = {
    "abfs": {
        "class": "adlfs.AzureBlobFileSystem",
        "err": "Install adlfs to access Azure Datalake Gen2 and Azure Blob Storage",
    },
    "adl": {
        "class": "adlfs.AzureDatalakeFileSystem",
        "err": "Install adlfs to access Azure Datalake Gen1",
    },
    "arrow_hdfs": {
        "class": "fsspec.implementations.arrow.HadoopFileSystem",
        "err": "pyarrow and local java libraries required for HDFS",
    },
    "asynclocal": {
        "class": "morefs.asyn_local.AsyncLocalFileSystem",
        "err": "Install 'morefs[asynclocalfs]' to use AsyncLocalFileSystem",
    },
    "asyncwrapper": {
        "class": "fsspec.implementations.asyn_wrapper.AsyncFileSystemWrapper",
    },
    "az": {
        "class": "adlfs.AzureBlobFileSystem",
        "err": "Install adlfs to access Azure Datalake Gen2 and Azure Blob Storage",
    },
    "blockcache": {"class": "fsspec.implementations.cached.CachingFileSystem"},
    "box": {
        "class": "boxfs.BoxFileSystem",
        "err": "Please install boxfs to access BoxFileSystem",
    },
    "cached": {"class": "fsspec.implementations.cached.CachingFileSystem"},
    "dask": {
        "class": "fsspec.implementations.dask.DaskWorkerFileSystem",
        "err": "Install dask distributed to access worker file system",
    },
    "data": {"class": "fsspec.implementations.data.DataFileSystem"},
    "dbfs": {
        "class": "fsspec.implementations.dbfs.DatabricksFileSystem",
        "err": "Install the requests package to use the DatabricksFileSystem",
    },
    "dir": {"class": "fsspec.implementations.dirfs.DirFileSystem"},
    "dropbox": {
        "class": "dropboxdrivefs.DropboxDriveFileSystem",
        "err": (
            'DropboxFileSystem requires "dropboxdrivefs","requests" and "'
            '"dropbox" to be installed'
        ),
    },
    "dvc": {
        "class": "dvc.api.DVCFileSystem",
        "err": "Install dvc to access DVCFileSystem",
    },
    "file": {"class": "fsspec.implementations.local.LocalFileSystem"},
    "filecache": {"class": "fsspec.implementations.cached.WholeFileCacheFileSystem"},
    "ftp": {"class": "fsspec.implementations.ftp.FTPFileSystem"},
    "gcs": {
        "class": "gcsfs.GCSFileSystem",
        "err": "Please install gcsfs to access Google Storage",
    },
    "gdrive": {
        "class": "gdrivefs.GoogleDriveFileSystem",
        "err": "Please install gdrivefs for access to Google Drive",
    },
    "generic": {"class": "fsspec.generic.GenericFileSystem"},
    "gist": {
        "class": "fsspec.implementations.gist.GistFileSystem",
        "err": "Install the requests package to use the gist FS",
    },
    "git": {
        "class": "fsspec.implementations.git.GitFileSystem",
        "err": "Install pygit2 to browse local git repos",
    },
    "github": {
        "class": "fsspec.implementations.github.GithubFileSystem",
        "err": "Install the requests package to use the github FS",
    },
    "gs": {
        "class": "gcsfs.GCSFileSystem",
        "err": "Please install gcsfs to access Google Storage",
    },
    "hdfs": {
        "class": "fsspec.implementations.arrow.HadoopFileSystem",
        "err": "pyarrow and local java libraries required for HDFS",
    },
    "hf": {
        "class": "huggingface_hub.HfFileSystem",
        "err": "Install huggingface_hub to access HfFileSystem",
    },
    "http": {
        "class": "fsspec.implementations.http.HTTPFileSystem",
        "err": 'HTTPFileSystem requires "requests" and "aiohttp" to be installed',
    },
    "https": {
        "class": "fsspec.implementations.http.HTTPFileSystem",
        "err": 'HTTPFileSystem requires "requests" and "aiohttp" to be installed',
    },
    "jlab": {
        "class": "fsspec.implementations.jupyter.JupyterFileSystem",
        "err": "Jupyter FS requires requests to be installed",
    },
    "jupyter": {
        "class": "fsspec.implementations.jupyter.JupyterFileSystem",
        "err": "Jupyter FS requires requests to be installed",
    },
    "lakefs": {
        "class": "lakefs_spec.LakeFSFileSystem",
        "err": "Please install lakefs-spec to access LakeFSFileSystem",
    },
    "libarchive": {
        "class": "fsspec.implementations.libarchive.LibArchiveFileSystem",
        "err": "LibArchive requires to be installed",
    },
    "local": {"class": "fsspec.implementations.local.LocalFileSystem"},
    "memory": {"class": "fsspec.implementations.memory.MemoryFileSystem"},
    "oci": {
        "class": "ocifs.OCIFileSystem",
        "err": "Install ocifs to access OCI Object Storage",
    },
    "ocilake": {
        "class": "ocifs.OCIFileSystem",
        "err": "Install ocifs to access OCI Data Lake",
    },
    "oss": {
        "class": "ossfs.OSSFileSystem",
        "err": "Install ossfs to access Alibaba Object Storage System",
    },
    "pyscript": {
        "class": "pyscript_fsspec_client.client.PyscriptFileSystem",
        "err": "Install requests (cpython) or run in pyscript",
    },
    "reference": {"class": "fsspec.implementations.reference.ReferenceFileSystem"},
    "root": {
        "class": "fsspec_xrootd.XRootDFileSystem",
        "err": (
            "Install fsspec-xrootd to access xrootd storage system. "
            "Note: 'root' is the protocol name for xrootd storage systems, "
            "not referring to root directories"
        ),
    },
    "s3": {"class": "s3fs.S3FileSystem", "err": "Install s3fs to access S3"},
    "s3a": {"class": "s3fs.S3FileSystem", "err": "Install s3fs to access S3"},
    "sftp": {
        "class": "fsspec.implementations.sftp.SFTPFileSystem",
        "err": 'SFTPFileSystem requires "paramiko" to be installed',
    },
    "simplecache": {"class": "fsspec.implementations.cached.SimpleCacheFileSystem"},
    "smb": {
        "class": "fsspec.implementations.smb.SMBFileSystem",
        "err": 'SMB requires "smbprotocol" or "smbprotocol[kerberos]" installed',
    },
    "ssh": {
        "class": "fsspec.implementations.sftp.SFTPFileSystem",
        "err": 'SFTPFileSystem requires "paramiko" to be installed',
    },
    "tar": {"class": "fsspec.implementations.tar.TarFileSystem"},
    "tosfs": {
        "class": "tosfs.TosFileSystem",
        "err": "Install tosfs to access ByteDance volcano engine Tinder Object Storage",
    },
    "wandb": {"class": "wandbfs.WandbFS", "err": "Install wandbfs to access wandb"},
    "webdav": {
        "class": "webdav4.fsspec.WebdavFileSystem",
        "err": "Install webdav4 to access WebDAV",
    },
    "webhdfs": {
        "class": "fsspec.implementations.webhdfs.WebHDFS",
        "err": 'webHDFS access requires "requests" to be installed',
    },
    "zip": {"class": "fsspec.implementations.zip.ZipFileSystem"},
}

assert list(known_implementations) == sorted(known_implementations), (
    "Not in alphabetical order"
)


def get_filesystem_class(protocol):
    """Fetch named protocol implementation from the registry

    The dict ``known_implementations`` maps protocol names to the locations
    of classes implementing the corresponding file-system. When used for the
    first time, appropriate imports will happen and the class will be placed in
    the registry. All subsequent calls will fetch directly from the registry.

    Some protocol implementations require additional dependencies, and so the
    import may fail. In this case, the string in the "err" field of the
    ``known_implementations`` will be given as the error message.
    """
    if not protocol:
        protocol = default

    if protocol not in registry:
        if protocol not in known_implementations:
            raise ValueError(f"Protocol not known: {protocol}")
        bit = known_implementations[protocol]
        try:
            register_implementation(protocol, _import_class(bit["class"]))
        except ImportError as e:
            raise ImportError(bit.get("err")) from e
    cls = registry[protocol]
    if getattr(cls, "protocol", None) in ("abstract", None):
        cls.protocol = protocol

    return cls


s3_msg = """Your installed version of s3fs is very old and known to cause
severe performance issues, see also https://github.com/dask/dask/issues/10276

To fix, you should specify a lower version bound on s3fs, or
update the current installation.
"""


def _import_class(fqp: str):
    """Take a fully-qualified path and return the imported class or identifier.

    ``fqp`` is of the form "package.module.klass" or
    "package.module:subobject.klass".

    Warnings
    --------
    This can import arbitrary modules. Make sure you haven't installed any modules
    that may execute malicious code at import time.
    """
    if ":" in fqp:
        mod, name = fqp.rsplit(":", 1)
    else:
        mod, name = fqp.rsplit(".", 1)

    is_s3 = mod == "s3fs"
    mod = importlib.import_module(mod)
    if is_s3 and mod.__version__.split(".") < ["0", "5"]:
        warnings.warn(s3_msg)
    for part in name.split("."):
        mod = getattr(mod, part)

    if not isinstance(mod, type):
        raise TypeError(f"{fqp} is not a class")

    return mod


def filesystem(protocol, **storage_options):
    """Instantiate filesystems for given protocol and arguments

    ``storage_options`` are specific to the protocol being chosen, and are
    passed directly to the class.
    """
    if protocol == "arrow_hdfs":
        warnings.warn(
            "The 'arrow_hdfs' protocol has been deprecated and will be "
            "removed in the future. Specify it as 'hdfs'.",
            DeprecationWarning,
        )

    cls = get_filesystem_class(protocol)
    return cls(**storage_options)


def available_protocols():
    """Return a list of the implemented protocols.

    Note that any given protocol may require extra packages to be importable.
    """
    return list(known_implementations)

# === NexusCore/openenv\Lib\site-packages\pyparsing\__init__.py ===
# module pyparsing.py
#
# Copyright (c) 2003-2022  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__doc__ = """
pyparsing module - Classes and methods to define and execute parsing grammars
=============================================================================

The pyparsing module is an alternative approach to creating and
executing simple grammars, vs. the traditional lex/yacc approach, or the
use of regular expressions.  With pyparsing, you don't need to learn
a new syntax for defining grammars or matching expressions - the parsing
module provides a library of classes that you use to construct the
grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form
``"<salutation>, <addressee>!"``), built up using :class:`Word`,
:class:`Literal`, and :class:`And` elements
(the :meth:`'+'<ParserElement.__add__>` operators create :class:`And` expressions,
and the strings are auto-converted to :class:`Literal` expressions)::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word(alphas) + "," + Word(alphas) + "!"

    hello = "Hello, World!"
    print(hello, "->", greet.parse_string(hello))

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the
self-explanatory class names, and the use of :class:`'+'<And>`,
:class:`'|'<MatchFirst>`, :class:`'^'<Or>` and :class:`'&'<Each>` operators.

The :class:`ParseResults` object returned from
:class:`ParserElement.parse_string` can be
accessed as a nested list, a dictionary, or an object with named
attributes.

The pyparsing module handles some of the problems that are typically
vexing when writing text parsers:

  - extra or missing whitespace (the above program will also handle
    "Hello,World!", "Hello  ,  World  !", etc.)
  - quoted strings
  - embedded comments


Getting Started -
-----------------
Visit the classes :class:`ParserElement` and :class:`ParseResults` to
see the base classes that most other pyparsing
classes inherit from. Use the docstrings for examples of how to:

 - construct literal match expressions from :class:`Literal` and
   :class:`CaselessLiteral` classes
 - construct character word-group expressions using the :class:`Word`
   class
 - see how to create repetitive expressions using :class:`ZeroOrMore`
   and :class:`OneOrMore` classes
 - use :class:`'+'<And>`, :class:`'|'<MatchFirst>`, :class:`'^'<Or>`,
   and :class:`'&'<Each>` operators to combine simple expressions into
   more complex ones
 - associate names with your parsed results using
   :class:`ParserElement.set_results_name`
 - access the parsed data, which is returned as a :class:`ParseResults`
   object
 - find some helpful expression short-cuts like :class:`DelimitedList`
   and :class:`one_of`
 - find more useful common expressions in the :class:`pyparsing_common`
   namespace class
"""
from typing import NamedTuple


class version_info(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int

    @property
    def __version__(self):
        return (
            f"{self.major}.{self.minor}.{self.micro}"
            + (
                f"{'r' if self.releaselevel[0] == 'c' else ''}{self.releaselevel[0]}{self.serial}",
                "",
            )[self.releaselevel == "final"]
        )

    def __str__(self):
        return f"{__name__} {self.__version__} / {__version_time__}"

    def __repr__(self):
        return f"{__name__}.{type(self).__name__}({', '.join('{}={!r}'.format(*nv) for nv in zip(self._fields, self))})"


__version_info__ = version_info(3, 2, 3, "final", 1)
__version_time__ = "25 Mar 2025 01:38 UTC"
__version__ = __version_info__.__version__
__versionTime__ = __version_time__
__author__ = "Paul McGuire <ptmcg.gm+pyparsing@gmail.com>"

from .util import *
from .exceptions import *
from .actions import *
from .core import __diag__, __compat__
from .results import *
from .core import *
from .core import _builtin_exprs as core_builtin_exprs
from .helpers import *
from .helpers import _builtin_exprs as helper_builtin_exprs

from .unicode import unicode_set, UnicodeRangeList, pyparsing_unicode as unicode
from .testing import pyparsing_test as testing
from .common import (
    pyparsing_common as common,
    _builtin_exprs as common_builtin_exprs,
)

# Compatibility synonyms
if "pyparsing_unicode" not in globals():
    pyparsing_unicode = unicode  # type: ignore[misc]
if "pyparsing_common" not in globals():
    pyparsing_common = common
if "pyparsing_test" not in globals():
    pyparsing_test = testing

core_builtin_exprs += common_builtin_exprs + helper_builtin_exprs


__all__ = [
    "__version__",
    "__version_time__",
    "__author__",
    "__compat__",
    "__diag__",
    "And",
    "AtLineStart",
    "AtStringStart",
    "CaselessKeyword",
    "CaselessLiteral",
    "CharsNotIn",
    "CloseMatch",
    "Combine",
    "DelimitedList",
    "Dict",
    "Each",
    "Empty",
    "FollowedBy",
    "Forward",
    "GoToColumn",
    "Group",
    "IndentedBlock",
    "Keyword",
    "LineEnd",
    "LineStart",
    "Literal",
    "Located",
    "PrecededBy",
    "MatchFirst",
    "NoMatch",
    "NotAny",
    "OneOrMore",
    "OnlyOnce",
    "OpAssoc",
    "Opt",
    "Optional",
    "Or",
    "ParseBaseException",
    "ParseElementEnhance",
    "ParseException",
    "ParseExpression",
    "ParseFatalException",
    "ParseResults",
    "ParseSyntaxException",
    "ParserElement",
    "PositionToken",
    "QuotedString",
    "RecursiveGrammarException",
    "Regex",
    "SkipTo",
    "StringEnd",
    "StringStart",
    "Suppress",
    "Tag",
    "Token",
    "TokenConverter",
    "White",
    "Word",
    "WordEnd",
    "WordStart",
    "ZeroOrMore",
    "Char",
    "alphanums",
    "alphas",
    "alphas8bit",
    "any_close_tag",
    "any_open_tag",
    "autoname_elements",
    "c_style_comment",
    "col",
    "common_html_entity",
    "condition_as_parse_action",
    "counted_array",
    "cpp_style_comment",
    "dbl_quoted_string",
    "dbl_slash_comment",
    "delimited_list",
    "dict_of",
    "empty",
    "hexnums",
    "html_comment",
    "identchars",
    "identbodychars",
    "infix_notation",
    "java_style_comment",
    "line",
    "line_end",
    "line_start",
    "lineno",
    "make_html_tags",
    "make_xml_tags",
    "match_only_at_col",
    "match_previous_expr",
    "match_previous_literal",
    "nested_expr",
    "null_debug_action",
    "nums",
    "one_of",
    "original_text_for",
    "printables",
    "punc8bit",
    "pyparsing_common",
    "pyparsing_test",
    "pyparsing_unicode",
    "python_style_comment",
    "quoted_string",
    "remove_quotes",
    "replace_with",
    "replace_html_entity",
    "rest_of_line",
    "sgl_quoted_string",
    "srange",
    "string_end",
    "string_start",
    "token_map",
    "trace_parse_action",
    "ungroup",
    "unicode_set",
    "unicode_string",
    "with_attribute",
    "with_class",
    # pre-PEP8 compatibility names
    "__versionTime__",
    "anyCloseTag",
    "anyOpenTag",
    "cStyleComment",
    "commonHTMLEntity",
    "conditionAsParseAction",
    "countedArray",
    "cppStyleComment",
    "dblQuotedString",
    "dblSlashComment",
    "delimitedList",
    "dictOf",
    "htmlComment",
    "indentedBlock",
    "infixNotation",
    "javaStyleComment",
    "lineEnd",
    "lineStart",
    "locatedExpr",
    "makeHTMLTags",
    "makeXMLTags",
    "matchOnlyAtCol",
    "matchPreviousExpr",
    "matchPreviousLiteral",
    "nestedExpr",
    "nullDebugAction",
    "oneOf",
    "opAssoc",
    "originalTextFor",
    "pythonStyleComment",
    "quotedString",
    "removeQuotes",
    "replaceHTMLEntity",
    "replaceWith",
    "restOfLine",
    "sglQuotedString",
    "stringEnd",
    "stringStart",
    "tokenMap",
    "traceParseAction",
    "unicodeString",
    "withAttribute",
    "withClass",
    "common",
    "unicode",
    "testing",
]

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\llm_cost_calc\tool_call_cost_tracking.py ===
"""
Helper utilities for tracking the cost of built-in tools.
"""

from typing import Any, Dict, List, Literal, Optional

import litellm
from litellm.constants import OPENAI_FILE_SEARCH_COST_PER_1K_CALLS
from litellm.types.llms.openai import (
    FileSearchTool,
    ResponsesAPIResponse,
    WebSearchOptions,
)
from litellm.types.utils import (
    Message,
    ModelInfo,
    ModelResponse,
    SearchContextCostPerQuery,
    StandardBuiltInToolsParams,
    Usage,
)


class StandardBuiltInToolCostTracking:
    """
    Helper class for tracking the cost of built-in tools

    Example: Web Search
    """

    @staticmethod
    def get_cost_for_built_in_tools(
        model: str,
        response_object: Any,
        usage: Optional[Usage] = None,
        custom_llm_provider: Optional[str] = None,
        standard_built_in_tools_params: Optional[StandardBuiltInToolsParams] = None,
    ) -> float:
        """
        Get the cost of using built-in tools.

        Supported tools:
        - Web Search

        """
        from litellm.llms import get_cost_for_web_search_request

        standard_built_in_tools_params = standard_built_in_tools_params or {}
        #########################################################
        # Web Search
        #########################################################
        if StandardBuiltInToolCostTracking.response_object_includes_web_search_call(
            response_object=response_object,
            usage=usage,
        ):
            model_info = StandardBuiltInToolCostTracking._safe_get_model_info(
                model=model, custom_llm_provider=custom_llm_provider
            )
            result: Optional[float] = None
            if custom_llm_provider is None and model_info is not None:
                custom_llm_provider = model_info["litellm_provider"]
            if (
                model_info is not None
                and usage is not None
                and custom_llm_provider is not None
            ):
                result = get_cost_for_web_search_request(
                    custom_llm_provider=custom_llm_provider,
                    usage=usage,
                    model_info=model_info,
                )
            if result is None:
                return StandardBuiltInToolCostTracking.get_cost_for_web_search(
                    web_search_options=standard_built_in_tools_params.get(
                        "web_search_options", None
                    ),
                    model_info=model_info,
                )
            else:
                return result

        #########################################################
        # File Search
        #########################################################
        elif StandardBuiltInToolCostTracking.response_object_includes_file_search_call(
            response_object=response_object
        ):
            return StandardBuiltInToolCostTracking.get_cost_for_file_search(
                file_search=standard_built_in_tools_params.get("file_search", None),
            )

        return 0.0

    @staticmethod
    def response_object_includes_web_search_call(
        response_object: Any, usage: Optional[Usage] = None
    ) -> bool:
        """
        Check if the response object includes a web search call.

        This covers:
        - Chat Completion Response (ModelResponse)
        - ResponsesAPIResponse (streaming + non-streaming)
        """
        from litellm.types.utils import PromptTokensDetailsWrapper

        if isinstance(response_object, ModelResponse):
            # chat completions only include url_citation annotations when a web search call is made
            return StandardBuiltInToolCostTracking.response_includes_annotation_type(
                response_object=response_object, annotation_type="url_citation"
            )
        elif isinstance(response_object, ResponsesAPIResponse):
            # response api explicitly includes web_search_call in the output
            return StandardBuiltInToolCostTracking.response_includes_output_type(
                response_object=response_object, output_type="web_search_call"
            )
        elif usage is not None:
            if (
                hasattr(usage, "server_tool_use")
                and usage.server_tool_use is not None
                and usage.server_tool_use.web_search_requests is not None
            ):
                return True
            elif (
                hasattr(usage, "prompt_tokens_details")
                and usage.prompt_tokens_details is not None
                and isinstance(usage.prompt_tokens_details, PromptTokensDetailsWrapper)
                and hasattr(usage.prompt_tokens_details, "web_search_requests")
                and usage.prompt_tokens_details.web_search_requests is not None
            ):
                return True

        return False

    @staticmethod
    def response_object_includes_file_search_call(
        response_object: Any,
    ) -> bool:
        """
        Check if the response object includes a file search call.

        This covers:
            - Chat Completion Response (ModelResponse)
            - ResponsesAPIResponse (streaming + non-streaming)
        """
        if isinstance(response_object, ModelResponse):
            # chat completions only include file_citation annotations when a file search call is made
            return StandardBuiltInToolCostTracking.response_includes_annotation_type(
                response_object=response_object, annotation_type="file_citation"
            )
        elif isinstance(response_object, ResponsesAPIResponse):
            # response api explicitly includes file_search_call in the output
            return StandardBuiltInToolCostTracking.response_includes_output_type(
                response_object=response_object, output_type="file_search_call"
            )
        return False

    @staticmethod
    def response_includes_annotation_type(
        response_object: ModelResponse,
        annotation_type: Literal["url_citation", "file_citation"],
    ) -> bool:
        if isinstance(response_object, ModelResponse):
            for choice in response_object.choices:
                message: Optional[Message] = getattr(choice, "message", None)
                if message is None:
                    continue
                if annotations := getattr(message, "annotations", None):
                    if len(annotations) > 0:
                        for annotation in annotations:
                            if annotation.get("type", None) == annotation_type:
                                return True
        return False

    @staticmethod
    def response_includes_output_type(
        response_object: ResponsesAPIResponse,
        output_type: Literal["web_search_call", "file_search_call"],
    ) -> bool:
        """
        Check if the ResponsesAPIResponse includes one of the specified output types.

        This is used for cost tracking of built-in tools.

        Args:
            response_object: The ResponsesAPIResponse object to check.
            output_type: The type of output to check for.

        Returns:
            True if the ResponsesAPIResponse includes one of the specified output types, False otherwise.
        """
        output = response_object.output
        for output_item in output:
            _output_type: Optional[str] = getattr(output_item, "type", None)
            if _output_type == output_type:
                return True
        return False

    @staticmethod
    def _safe_get_model_info(
        model: str, custom_llm_provider: Optional[str] = None
    ) -> Optional[ModelInfo]:
        try:
            return litellm.get_model_info(
                model=model, custom_llm_provider=custom_llm_provider
            )
        except Exception:
            return None

    @staticmethod
    def get_cost_for_web_search(
        web_search_options: Optional[WebSearchOptions] = None,
        model_info: Optional[ModelInfo] = None,
    ) -> float:
        """
        If request includes `web_search_options`, calculate the cost of the web search.
        """
        web_search_options = web_search_options or {}
        if model_info is None:
            return 0.0

        search_context_pricing: SearchContextCostPerQuery = (
            model_info.get("search_context_cost_per_query", {}) or {}
        )
        if web_search_options.get("search_context_size", None) == "low":
            return search_context_pricing.get("search_context_size_low", 0.0)
        elif web_search_options.get("search_context_size", None) == "medium":
            return search_context_pricing.get("search_context_size_medium", 0.0)
        elif web_search_options.get("search_context_size", None) == "high":
            return search_context_pricing.get("search_context_size_high", 0.0)
        return StandardBuiltInToolCostTracking.get_default_cost_for_web_search(
            model_info
        )

    @staticmethod
    def get_default_cost_for_web_search(
        model_info: Optional[ModelInfo] = None,
    ) -> float:
        """
        If no web search options are provided, use the `search_context_size_medium` pricing.

        https://platform.openai.com/docs/pricing#web-search
        """
        if model_info is None:
            return 0.0
        search_context_pricing: SearchContextCostPerQuery = (
            model_info.get("search_context_cost_per_query", {}) or {}
        ) or {}
        return search_context_pricing.get("search_context_size_medium", 0.0)

    @staticmethod
    def get_cost_for_file_search(
        file_search: Optional[FileSearchTool] = None,
    ) -> float:
        """ "
        Charged at $2.50/1k calls

        Doc: https://platform.openai.com/docs/pricing#built-in-tools
        """
        if file_search is None:
            return 0.0
        return OPENAI_FILE_SEARCH_COST_PER_1K_CALLS

    @staticmethod
    def chat_completion_response_includes_annotations(
        response_object: ModelResponse,
    ) -> bool:
        for _choice in response_object.choices:
            message = getattr(_choice, "message", None)
            if (
                message is not None
                and hasattr(message, "annotations")
                and message.annotations is not None
                and len(message.annotations) > 0
            ):
                return True
        return False

    @staticmethod
    def _get_web_search_options(kwargs: Dict) -> Optional[WebSearchOptions]:
        if "web_search_options" in kwargs:
            return WebSearchOptions(**kwargs.get("web_search_options", {}))

        tools = StandardBuiltInToolCostTracking._get_tools_from_kwargs(
            kwargs, "web_search_preview"
        )
        if tools:
            # Look for web search tool in the tools array
            for tool in tools:
                if isinstance(tool, dict):
                    if StandardBuiltInToolCostTracking._is_web_search_tool_call(tool):
                        return WebSearchOptions(**tool)
        return None

    @staticmethod
    def _get_tools_from_kwargs(kwargs: Dict, tool_type: str) -> Optional[List[Dict]]:
        if "tools" in kwargs:
            tools = kwargs.get("tools", [])
            return tools
        return None

    @staticmethod
    def _get_file_search_tool_call(kwargs: Dict) -> Optional[FileSearchTool]:
        tools = StandardBuiltInToolCostTracking._get_tools_from_kwargs(
            kwargs, "file_search"
        )
        if tools:
            for tool in tools:
                if isinstance(tool, dict):
                    if StandardBuiltInToolCostTracking._is_file_search_tool_call(tool):
                        return FileSearchTool(**tool)
        return None

    @staticmethod
    def _is_web_search_tool_call(tool: Dict) -> bool:
        if tool.get("type", None) == "web_search_preview":
            return True
        if "search_context_size" in tool:
            return True
        return False

    @staticmethod
    def _is_file_search_tool_call(tool: Dict) -> bool:
        if tool.get("type", None) == "file_search":
            return True
        return False

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\grid_finder.py ===
import numpy as np

from matplotlib import ticker as mticker, _api
from matplotlib.transforms import Bbox, Transform


def _find_line_box_crossings(xys, bbox):
    """
    Find the points where a polyline crosses a bbox, and the crossing angles.

    Parameters
    ----------
    xys : (N, 2) array
        The polyline coordinates.
    bbox : `.Bbox`
        The bounding box.

    Returns
    -------
    list of ((float, float), float)
        Four separate lists of crossings, for the left, right, bottom, and top
        sides of the bbox, respectively.  For each list, the entries are the
        ``((x, y), ccw_angle_in_degrees)`` of the crossing, where an angle of 0
        means that the polyline is moving to the right at the crossing point.

        The entries are computed by linearly interpolating at each crossing
        between the nearest points on either side of the bbox edges.
    """
    crossings = []
    dxys = xys[1:] - xys[:-1]
    for sl in [slice(None), slice(None, None, -1)]:
        us, vs = xys.T[sl]  # "this" coord, "other" coord
        dus, dvs = dxys.T[sl]
        umin, vmin = bbox.min[sl]
        umax, vmax = bbox.max[sl]
        for u0, inside in [(umin, us > umin), (umax, us < umax)]:
            cross = []
            idxs, = (inside[:-1] ^ inside[1:]).nonzero()
            for idx in idxs:
                v = vs[idx] + (u0 - us[idx]) * dvs[idx] / dus[idx]
                if not vmin <= v <= vmax:
                    continue
                crossing = (u0, v)[sl]
                theta = np.degrees(np.arctan2(*dxys[idx][::-1]))
                cross.append((crossing, theta))
            crossings.append(cross)
    return crossings


class ExtremeFinderSimple:
    """
    A helper class to figure out the range of grid lines that need to be drawn.
    """

    def __init__(self, nx, ny):
        """
        Parameters
        ----------
        nx, ny : int
            The number of samples in each direction.
        """
        self.nx = nx
        self.ny = ny

    def __call__(self, transform_xy, x1, y1, x2, y2):
        """
        Compute an approximation of the bounding box obtained by applying
        *transform_xy* to the box delimited by ``(x1, y1, x2, y2)``.

        The intended use is to have ``(x1, y1, x2, y2)`` in axes coordinates,
        and have *transform_xy* be the transform from axes coordinates to data
        coordinates; this method then returns the range of data coordinates
        that span the actual axes.

        The computation is done by sampling ``nx * ny`` equispaced points in
        the ``(x1, y1, x2, y2)`` box and finding the resulting points with
        extremal coordinates; then adding some padding to take into account the
        finite sampling.

        As each sampling step covers a relative range of *1/nx* or *1/ny*,
        the padding is computed by expanding the span covered by the extremal
        coordinates by these fractions.
        """
        x, y = np.meshgrid(
            np.linspace(x1, x2, self.nx), np.linspace(y1, y2, self.ny))
        xt, yt = transform_xy(np.ravel(x), np.ravel(y))
        return self._add_pad(xt.min(), xt.max(), yt.min(), yt.max())

    def _add_pad(self, x_min, x_max, y_min, y_max):
        """Perform the padding mentioned in `__call__`."""
        dx = (x_max - x_min) / self.nx
        dy = (y_max - y_min) / self.ny
        return x_min - dx, x_max + dx, y_min - dy, y_max + dy


class _User2DTransform(Transform):
    """A transform defined by two user-set functions."""

    input_dims = output_dims = 2

    def __init__(self, forward, backward):
        """
        Parameters
        ----------
        forward, backward : callable
            The forward and backward transforms, taking ``x`` and ``y`` as
            separate arguments and returning ``(tr_x, tr_y)``.
        """
        # The normal Matplotlib convention would be to take and return an
        # (N, 2) array but axisartist uses the transposed version.
        super().__init__()
        self._forward = forward
        self._backward = backward

    def transform_non_affine(self, values):
        # docstring inherited
        return np.transpose(self._forward(*np.transpose(values)))

    def inverted(self):
        # docstring inherited
        return type(self)(self._backward, self._forward)


class GridFinder:
    """
    Internal helper for `~.grid_helper_curvelinear.GridHelperCurveLinear`, with
    the same constructor parameters; should not be directly instantiated.
    """

    def __init__(self,
                 transform,
                 extreme_finder=None,
                 grid_locator1=None,
                 grid_locator2=None,
                 tick_formatter1=None,
                 tick_formatter2=None):
        if extreme_finder is None:
            extreme_finder = ExtremeFinderSimple(20, 20)
        if grid_locator1 is None:
            grid_locator1 = MaxNLocator()
        if grid_locator2 is None:
            grid_locator2 = MaxNLocator()
        if tick_formatter1 is None:
            tick_formatter1 = FormatterPrettyPrint()
        if tick_formatter2 is None:
            tick_formatter2 = FormatterPrettyPrint()
        self.extreme_finder = extreme_finder
        self.grid_locator1 = grid_locator1
        self.grid_locator2 = grid_locator2
        self.tick_formatter1 = tick_formatter1
        self.tick_formatter2 = tick_formatter2
        self.set_transform(transform)

    def _format_ticks(self, idx, direction, factor, levels):
        """
        Helper to support both standard formatters (inheriting from
        `.mticker.Formatter`) and axisartist-specific ones; should be called instead of
        directly calling ``self.tick_formatter1`` and ``self.tick_formatter2``.  This
        method should be considered as a temporary workaround which will be removed in
        the future at the same time as axisartist-specific formatters.
        """
        fmt = _api.check_getitem(
            {1: self.tick_formatter1, 2: self.tick_formatter2}, idx=idx)
        return (fmt.format_ticks(levels) if isinstance(fmt, mticker.Formatter)
                else fmt(direction, factor, levels))

    def get_grid_info(self, x1, y1, x2, y2):
        """
        lon_values, lat_values : list of grid values. if integer is given,
                           rough number of grids in each direction.
        """

        extremes = self.extreme_finder(self.inv_transform_xy, x1, y1, x2, y2)

        # min & max rage of lat (or lon) for each grid line will be drawn.
        # i.e., gridline of lon=0 will be drawn from lat_min to lat_max.

        lon_min, lon_max, lat_min, lat_max = extremes
        lon_levs, lon_n, lon_factor = self.grid_locator1(lon_min, lon_max)
        lon_levs = np.asarray(lon_levs)
        lat_levs, lat_n, lat_factor = self.grid_locator2(lat_min, lat_max)
        lat_levs = np.asarray(lat_levs)

        lon_values = lon_levs[:lon_n] / lon_factor
        lat_values = lat_levs[:lat_n] / lat_factor

        lon_lines, lat_lines = self._get_raw_grid_lines(lon_values,
                                                        lat_values,
                                                        lon_min, lon_max,
                                                        lat_min, lat_max)

        bb = Bbox.from_extents(x1, y1, x2, y2).expanded(1 + 2e-10, 1 + 2e-10)

        grid_info = {
            "extremes": extremes,
            # "lon", "lat", filled below.
        }

        for idx, lon_or_lat, levs, factor, values, lines in [
                (1, "lon", lon_levs, lon_factor, lon_values, lon_lines),
                (2, "lat", lat_levs, lat_factor, lat_values, lat_lines),
        ]:
            grid_info[lon_or_lat] = gi = {
                "lines": [[l] for l in lines],
                "ticks": {"left": [], "right": [], "bottom": [], "top": []},
            }
            for (lx, ly), v, level in zip(lines, values, levs):
                all_crossings = _find_line_box_crossings(np.column_stack([lx, ly]), bb)
                for side, crossings in zip(
                        ["left", "right", "bottom", "top"], all_crossings):
                    for crossing in crossings:
                        gi["ticks"][side].append({"level": level, "loc": crossing})
            for side in gi["ticks"]:
                levs = [tick["level"] for tick in gi["ticks"][side]]
                labels = self._format_ticks(idx, side, factor, levs)
                for tick, label in zip(gi["ticks"][side], labels):
                    tick["label"] = label

        return grid_info

    def _get_raw_grid_lines(self,
                            lon_values, lat_values,
                            lon_min, lon_max, lat_min, lat_max):

        lons_i = np.linspace(lon_min, lon_max, 100)  # for interpolation
        lats_i = np.linspace(lat_min, lat_max, 100)

        lon_lines = [self.transform_xy(np.full_like(lats_i, lon), lats_i)
                     for lon in lon_values]
        lat_lines = [self.transform_xy(lons_i, np.full_like(lons_i, lat))
                     for lat in lat_values]

        return lon_lines, lat_lines

    def set_transform(self, aux_trans):
        if isinstance(aux_trans, Transform):
            self._aux_transform = aux_trans
        elif len(aux_trans) == 2 and all(map(callable, aux_trans)):
            self._aux_transform = _User2DTransform(*aux_trans)
        else:
            raise TypeError("'aux_trans' must be either a Transform "
                            "instance or a pair of callables")

    def get_transform(self):
        return self._aux_transform

    update_transform = set_transform  # backcompat alias.

    def transform_xy(self, x, y):
        return self._aux_transform.transform(np.column_stack([x, y])).T

    def inv_transform_xy(self, x, y):
        return self._aux_transform.inverted().transform(
            np.column_stack([x, y])).T

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k in ["extreme_finder",
                     "grid_locator1",
                     "grid_locator2",
                     "tick_formatter1",
                     "tick_formatter2"]:
                setattr(self, k, v)
            else:
                raise ValueError(f"Unknown update property {k!r}")


class MaxNLocator(mticker.MaxNLocator):
    def __init__(self, nbins=10, steps=None,
                 trim=True,
                 integer=False,
                 symmetric=False,
                 prune=None):
        # trim argument has no effect. It has been left for API compatibility
        super().__init__(nbins, steps=steps, integer=integer,
                         symmetric=symmetric, prune=prune)
        self.create_dummy_axis()

    def __call__(self, v1, v2):
        locs = super().tick_values(v1, v2)
        return np.array(locs), len(locs), 1  # 1: factor (see angle_helper)


class FixedLocator:
    def __init__(self, locs):
        self._locs = locs

    def __call__(self, v1, v2):
        v1, v2 = sorted([v1, v2])
        locs = np.array([l for l in self._locs if v1 <= l <= v2])
        return locs, len(locs), 1  # 1: factor (see angle_helper)


# Tick Formatter

class FormatterPrettyPrint:
    def __init__(self, useMathText=True):
        self._fmt = mticker.ScalarFormatter(
            useMathText=useMathText, useOffset=False)
        self._fmt.create_dummy_axis()

    def __call__(self, direction, factor, values):
        return self._fmt.format_ticks(values)


class DictFormatter:
    def __init__(self, format_dict, formatter=None):
        """
        format_dict : dictionary for format strings to be used.
        formatter : fall-back formatter
        """
        super().__init__()
        self._format_dict = format_dict
        self._fallback_formatter = formatter

    def __call__(self, direction, factor, values):
        """
        factor is ignored if value is found in the dictionary
        """
        if self._fallback_formatter:
            fallback_strings = self._fallback_formatter(
                direction, factor, values)
        else:
            fallback_strings = [""] * len(values)
        return [self._format_dict.get(k, v)
                for k, v in zip(values, fallback_strings)]

# === NexusCore/evaluation\evaluate\multi_turn\gen_plus_solution_multiround_human_feedback_oracle.py ===
import argparse
import os
import torch
from pathlib import Path
from tqdm import tqdm
import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from evalplus.data import (get_human_eval_plus, 
    write_jsonl,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from utils import sanitize_solution,check_correctness,get_groundtruth,SUCCESS
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from copy import deepcopy
from chat_with_gpt import gpt_predict

MAX_TRY = 2

def humaneval_build_instruction(languge: str, question: str):
    return '''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given code to do completion:
```{}
{}
```
Please continue to complete the function with {} programming language. You are not allowed to modify the given code and do the completion only. 

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''.strip().format(languge.lower(), question.strip(),languge.lower(),languge.lower())

mbpp_build_deepseekcoder_instruction='''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given problem and test examples:
{}

Please use the {} programming language to solve this problem.
Please make sure that your code includes the functions from the test samples and that the input and output formats of these functions match the test samples.

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''

def build_gpt_prompt(pre_messages: str, problem: str, current_code: str, execution_feedback: str, canonical_solution: str):
    prompt = """You are tasked with providing guidance to a programmer who has drafted a code for a programming problem. 
Your role is to mimic human-like responses and offer suggestions for modifying the code based on the canonical solution and the observed execution results.
You should NOT directly revealing contents of the @@Canonical Solution or mentioning terms such as "canonical solution."
You should refrain from directly writing code.
Begin by thoroughly examining the existing code and its functionality.
Compare the @@Existing Code with the @@Canonical Solution provided. Note any discrepancies in logic, approach, or implementation.
Analyze the @@Execution Result obtained from running the @@Existing Code. Identify any errors, unexpected behavior, or deviations from the expected output.
Consider potential edge cases, optimization opportunities, or alternative approaches based on insights from both the @@Canonical Solution and @@Execution Result.
Offer guidance in a clear and understandable manner, explaining the rationale behind each suggestion.
Refrain from providing actual code solutions, but instead focus on conceptual modifications or strategies.
Provide constructive feedback to help the programmer improve their coding skills.
Remember, your role is to simulate human-like guidance and expertise in programming without directly implementing solutions.
Please respond in no more than three sentences.

@@Problem
{}

@@Existing Code
{}

@@Execution Result
{}

@@Canonical Solution
{}

@@Guidance
""".format(problem.strip(), current_code, execution_feedback,canonical_solution)
    return prompt


def generate_multi_round(problem,expected_output, example, lang, tokenizer, model,name,flags):
    pre_messages=[]
    if flags.dataset=="humaneval":
        prompt = humaneval_build_instruction(lang, example['prompt'])
    elif flags.dataset=="mbpp":
        prompt = mbpp_build_deepseekcoder_instruction.strip().format(example['prompt'],"python","python")
    pre_messages.append({"role":"user","content":prompt})
    inputs = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': prompt}],
        return_tensors="pt"
    ).to(model.device)
    stop_id = tokenizer.convert_tokens_to_ids("<|EOT|>")
    assert isinstance(stop_id, int), "Invalid tokenizer, EOT id not found"
    max_new_tokens=1024
    logging.info(f"max_new_tokens{max_new_tokens}")
    outputs = model.generate(
        inputs, 
        max_new_tokens=max_new_tokens,#待定，evalplus论文说除了gpt用的1024，其他都用的512
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        temperature=0,
    )
    output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
    canonical_solution = example["canonical_solution"]
    solution = {k:v for k,v in example.items()}
    solution["solution"]=output
    sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)
    attempt = 1
    judge = False
    modify = False
    code = sanitized_solution["solution"]
    while attempt==1 or sanitized_solution["solution"]!="":
        pre_messages.append({"role":"assistant","content":solution["solution"]})
        args = (
            flags.dataset,
            0,
            problem,
            sanitized_solution["solution"],
            expected_output,
            flags.version,
            True,  # fast_check
            example["task_id"]+f'_{attempt}',
            flags.min_time_limit,
            flags.gt_time_limit_factor,
        )
        result = check_correctness(*args)
        if flags.version=="base" and result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        elif flags.version=="plus" and result["plus"][0]==result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        else:
            attempt += 1    
            if attempt > MAX_TRY:
                code = sanitized_solution["solution"]
                break
            execution_feedback=""
            if flags.version=="base":
                execution_feedback=result["base"][2]
            elif flags.version=="plus":
                if result["base"][0]!=SUCCESS:
                    execution_feedback+=result["base"][2]
                    if "The results aren't as expected." in execution_feedback:
                        if result["plus"][0]!=SUCCESS:
                            execution_feedback+="\n"+result["plus"][2]
                else:
                    execution_feedback=result["plus"][2]
            gpt_messages=[{"role":"system","content":"You are a helpful assistant."}]
            gpt_messages.append({"role":"user","content":build_gpt_prompt(\
                pre_messages, example['prompt'], sanitized_solution["solution"], execution_feedback, canonical_solution)})
            gpt_feedback=None
            trytime=0
            while gpt_feedback is None and trytime<5:
                gpt_feedback=gpt_predict(gpt_messages)
                trytime+=1
            if gpt_feedback==None:
                raise BaseException("Please resume.")
            if prompt.endswith("@@ Response"):
                prompt +="""
{}

@@ Instruction
{}
""".format(solution["solution"],gpt_feedback)
            else:
                prompt +="""

@@ Response
{}

@@ Instruction
{}
""".format(solution["solution"],gpt_feedback)        
            pre_messages.append({"role":"user","content":gpt_feedback})
            inputs = tokenizer.apply_chat_template(
                [{'role': 'user', 'content': prompt }],
                return_tensors="pt"
            ).to(model.device)

            outputs = model.generate(
                inputs, 
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                temperature=0,
            )
            output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
            solution = {k:v for k,v in example.items()}
            solution["solution"]=output 
            sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)

    return code,judge,modify


def gen_solution(args):
    a,b = 0,0
    total_modify = 0
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    fail_list=[]
    model_path = args.model
    logging.info(f"model:{model_path}")
    model_name =model_path.replace("/", "_")
    lang = "python"
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    output_file = os.path.join(args.output_path,model_name,f"multiround_{args.dataset}_{args.version}_solutions-sanitized.jsonl")
    if not args.resume:
        if os.path.exists(output_file):
            logging.info(f"Old sample jsonl file exists, remove it. {output_file}")
            os.remove(output_file)
    else:
        existing_task_ids = set()
        if os.path.exists(output_file):
            with open(output_file, 'r') as file:
                for line in file:
                    data = json.loads(line)
                    if 'task_id' in data:
                        existing_task_ids.add(data['task_id'])
                        a=data["pass_num"]
                        total_modify=data["total_modify"]
                        b=data["total_num"]-a
                        fail_list=data["fail_list"]

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    logging.info("load tokenizer {} from {} over.".format(tokenizer.__class__, model_path))
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()

    modelname=model_path.replace("/", "_")
    if args.dataset=="humaneval":
        problems = get_human_eval_plus()
        examples = problems.items()
        dataset_hash = get_human_eval_plus_hash()
        expected_outputs = get_groundtruth(problems, dataset_hash, [])
    else:
        problems = get_mbpp_plus()
        examples = problems.items()
        dataset_hash = get_mbpp_plus_hash()
        expected_outputs = get_groundtruth(
                problems,
                dataset_hash,
                MBPP_OUTPUT_NOT_NONE_TASKS,
            )
    logging.info("Read {} examples for evaluation over.".format(len(examples)))
    for task_id,example in tqdm(examples, desc='Generating'):
        if args.resume:
            if task_id in existing_task_ids:
                continue
        problem = problems[task_id]
        # print("problem:\n",problem.keys())
        # print("\n",problem)
        expected_output = expected_outputs[task_id]
        code,judge,modify = generate_multi_round(problem,expected_output,example, lang, tokenizer, model, modelname,args)
        if modify:
            total_modify += 1
        if judge:
            a += 1
        else:
            b += 1
            fail_list.append(task_id)
        result = a/(a+b)
        single_result = (a-total_modify)/(a+b)
        print ("pass num ",a)
        print ("totalnum ",a+b)
        print ("judge: ",judge)
        print ('modify: '+str(modify))
        print ("num modify: "+str(total_modify))
        print ("fail list: ",fail_list)
        print ('multisound rate: '+str(result))
        print ('singlesound rate: '+str(single_result))
        gen_sample=[dict(task_id=task_id, solution=code, pass_num=a, total_modify=total_modify, total_num=a+b, fail_list=fail_list)]
        write_jsonl(output_file, gen_sample ,append=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, help="model path")
    parser.add_argument('--output_path', type=str, help="output path", default="./multiround_output")
    parser.add_argument('--log_file', type=str, help="log file name", default="gen_humaneval_plus_solution_singleround.log")
    parser.add_argument("--min-time-limit", default=1, type=float)
    parser.add_argument("--gt-time-limit-factor", default=4.0, type=float)
    parser.add_argument(
        "--version", required=True, type=str, choices=["base", "plus"]
    )
    parser.add_argument(
        "--dataset", required=True, type=str, choices=["humaneval", "mbpp"]
    )
    parser.add_argument('--resume', action="store_true")

    args = parser.parse_args()
    args.eofs=None

    model_name = args.model.replace("/", "_")
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    logfile=os.path.join(args.output_path,model_name,args.log_file)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler.setFormatter(formatter)  
    logging.getLogger().addHandler(file_handler)

    gen_solution(args)

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\cu2quPen.py ===
# Copyright 2016 Google Inc. All Rights Reserved.
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

import operator
from fontTools.cu2qu import curve_to_quadratic, curves_to_quadratic
from fontTools.pens.basePen import decomposeSuperBezierSegment
from fontTools.pens.filterPen import FilterPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.pointPen import BasePointToSegmentPen
from fontTools.pens.pointPen import ReverseContourPointPen


class Cu2QuPen(FilterPen):
    """A filter pen to convert cubic bezier curves to quadratic b-splines
    using the FontTools SegmentPen protocol.

    Args:

        other_pen: another SegmentPen used to draw the transformed outline.
        max_err: maximum approximation error in font units. For optimal results,
            if you know the UPEM of the font, we recommend setting this to a
            value equal, or close to UPEM / 1000.
        reverse_direction: flip the contours' direction but keep starting point.
        stats: a dictionary counting the point numbers of quadratic segments.
        all_quadratic: if True (default), only quadratic b-splines are generated.
            if False, quadratic curves or cubic curves are generated depending
            on which one is more economical.
    """

    def __init__(
        self,
        other_pen,
        max_err,
        reverse_direction=False,
        stats=None,
        all_quadratic=True,
    ):
        if reverse_direction:
            other_pen = ReverseContourPen(other_pen)
        super().__init__(other_pen)
        self.max_err = max_err
        self.stats = stats
        self.all_quadratic = all_quadratic

    def _convert_curve(self, pt1, pt2, pt3):
        curve = (self.current_pt, pt1, pt2, pt3)
        result = curve_to_quadratic(curve, self.max_err, self.all_quadratic)
        if self.stats is not None:
            n = str(len(result) - 2)
            self.stats[n] = self.stats.get(n, 0) + 1
        if self.all_quadratic:
            self.qCurveTo(*result[1:])
        else:
            if len(result) == 3:
                self.qCurveTo(*result[1:])
            else:
                assert len(result) == 4
                super().curveTo(*result[1:])

    def curveTo(self, *points):
        n = len(points)
        if n == 3:
            # this is the most common case, so we special-case it
            self._convert_curve(*points)
        elif n > 3:
            for segment in decomposeSuperBezierSegment(points):
                self._convert_curve(*segment)
        else:
            self.qCurveTo(*points)


class Cu2QuPointPen(BasePointToSegmentPen):
    """A filter pen to convert cubic bezier curves to quadratic b-splines
    using the FontTools PointPen protocol.

    Args:
        other_point_pen: another PointPen used to draw the transformed outline.
        max_err: maximum approximation error in font units. For optimal results,
            if you know the UPEM of the font, we recommend setting this to a
            value equal, or close to UPEM / 1000.
        reverse_direction: reverse the winding direction of all contours.
        stats: a dictionary counting the point numbers of quadratic segments.
        all_quadratic: if True (default), only quadratic b-splines are generated.
            if False, quadratic curves or cubic curves are generated depending
            on which one is more economical.
    """

    __points_required = {
        "move": (1, operator.eq),
        "line": (1, operator.eq),
        "qcurve": (2, operator.ge),
        "curve": (3, operator.eq),
    }

    def __init__(
        self,
        other_point_pen,
        max_err,
        reverse_direction=False,
        stats=None,
        all_quadratic=True,
    ):
        BasePointToSegmentPen.__init__(self)
        if reverse_direction:
            self.pen = ReverseContourPointPen(other_point_pen)
        else:
            self.pen = other_point_pen
        self.max_err = max_err
        self.stats = stats
        self.all_quadratic = all_quadratic

    def _flushContour(self, segments):
        assert len(segments) >= 1
        closed = segments[0][0] != "move"
        new_segments = []
        prev_points = segments[-1][1]
        prev_on_curve = prev_points[-1][0]
        for segment_type, points in segments:
            if segment_type == "curve":
                for sub_points in self._split_super_bezier_segments(points):
                    on_curve, smooth, name, kwargs = sub_points[-1]
                    bcp1, bcp2 = sub_points[0][0], sub_points[1][0]
                    cubic = [prev_on_curve, bcp1, bcp2, on_curve]
                    quad = curve_to_quadratic(cubic, self.max_err, self.all_quadratic)
                    if self.stats is not None:
                        n = str(len(quad) - 2)
                        self.stats[n] = self.stats.get(n, 0) + 1
                    new_points = [(pt, False, None, {}) for pt in quad[1:-1]]
                    new_points.append((on_curve, smooth, name, kwargs))
                    if self.all_quadratic or len(new_points) == 2:
                        new_segments.append(["qcurve", new_points])
                    else:
                        new_segments.append(["curve", new_points])
                    prev_on_curve = sub_points[-1][0]
            else:
                new_segments.append([segment_type, points])
                prev_on_curve = points[-1][0]
        if closed:
            # the BasePointToSegmentPen.endPath method that calls _flushContour
            # rotates the point list of closed contours so that they end with
            # the first on-curve point. We restore the original starting point.
            new_segments = new_segments[-1:] + new_segments[:-1]
        self._drawPoints(new_segments)

    def _split_super_bezier_segments(self, points):
        sub_segments = []
        # n is the number of control points
        n = len(points) - 1
        if n == 2:
            # a simple bezier curve segment
            sub_segments.append(points)
        elif n > 2:
            # a "super" bezier; decompose it
            on_curve, smooth, name, kwargs = points[-1]
            num_sub_segments = n - 1
            for i, sub_points in enumerate(
                decomposeSuperBezierSegment([pt for pt, _, _, _ in points])
            ):
                new_segment = []
                for point in sub_points[:-1]:
                    new_segment.append((point, False, None, {}))
                if i == (num_sub_segments - 1):
                    # the last on-curve keeps its original attributes
                    new_segment.append((on_curve, smooth, name, kwargs))
                else:
                    # on-curves of sub-segments are always "smooth"
                    new_segment.append((sub_points[-1], True, None, {}))
                sub_segments.append(new_segment)
        else:
            raise AssertionError("expected 2 control points, found: %d" % n)
        return sub_segments

    def _drawPoints(self, segments):
        pen = self.pen
        pen.beginPath()
        last_offcurves = []
        points_required = self.__points_required
        for i, (segment_type, points) in enumerate(segments):
            if segment_type in points_required:
                n, op = points_required[segment_type]
                assert op(len(points), n), (
                    f"illegal {segment_type!r} segment point count: "
                    f"expected {n}, got {len(points)}"
                )
                offcurves = points[:-1]
                if i == 0:
                    # any off-curve points preceding the first on-curve
                    # will be appended at the end of the contour
                    last_offcurves = offcurves
                else:
                    for pt, smooth, name, kwargs in offcurves:
                        pen.addPoint(pt, None, smooth, name, **kwargs)
                pt, smooth, name, kwargs = points[-1]
                if pt is None:
                    assert segment_type == "qcurve"
                    # special quadratic contour with no on-curve points:
                    # we need to skip the "None" point. See also the Pen
                    # protocol's qCurveTo() method and fontTools.pens.basePen
                    pass
                else:
                    pen.addPoint(pt, segment_type, smooth, name, **kwargs)
            else:
                raise AssertionError("unexpected segment type: %r" % segment_type)
        for pt, smooth, name, kwargs in last_offcurves:
            pen.addPoint(pt, None, smooth, name, **kwargs)
        pen.endPath()

    def addComponent(self, baseGlyphName, transformation):
        assert self.currentPath is None
        self.pen.addComponent(baseGlyphName, transformation)


class Cu2QuMultiPen:
    """A filter multi-pen to convert cubic bezier curves to quadratic b-splines
    in a interpolation-compatible manner, using the FontTools SegmentPen protocol.

    Args:

        other_pens: list of SegmentPens used to draw the transformed outlines.
        max_err: maximum approximation error in font units. For optimal results,
            if you know the UPEM of the font, we recommend setting this to a
            value equal, or close to UPEM / 1000.
        reverse_direction: flip the contours' direction but keep starting point.

    This pen does not follow the normal SegmentPen protocol. Instead, its
    moveTo/lineTo/qCurveTo/curveTo methods take a list of tuples that are
    arguments that would normally be passed to a SegmentPen, one item for
    each of the pens in other_pens.
    """

    # TODO Simplify like 3e8ebcdce592fe8a59ca4c3a294cc9724351e1ce
    # Remove start_pts and _add_moveTO

    def __init__(self, other_pens, max_err, reverse_direction=False):
        if reverse_direction:
            other_pens = [
                ReverseContourPen(pen, outputImpliedClosingLine=True)
                for pen in other_pens
            ]
        self.pens = other_pens
        self.max_err = max_err
        self.start_pts = None
        self.current_pts = None

    def _check_contour_is_open(self):
        if self.current_pts is None:
            raise AssertionError("moveTo is required")

    def _check_contour_is_closed(self):
        if self.current_pts is not None:
            raise AssertionError("closePath or endPath is required")

    def _add_moveTo(self):
        if self.start_pts is not None:
            for pt, pen in zip(self.start_pts, self.pens):
                pen.moveTo(*pt)
            self.start_pts = None

    def moveTo(self, pts):
        self._check_contour_is_closed()
        self.start_pts = self.current_pts = pts
        self._add_moveTo()

    def lineTo(self, pts):
        self._check_contour_is_open()
        self._add_moveTo()
        for pt, pen in zip(pts, self.pens):
            pen.lineTo(*pt)
        self.current_pts = pts

    def qCurveTo(self, pointsList):
        self._check_contour_is_open()
        if len(pointsList[0]) == 1:
            self.lineTo([(points[0],) for points in pointsList])
            return
        self._add_moveTo()
        current_pts = []
        for points, pen in zip(pointsList, self.pens):
            pen.qCurveTo(*points)
            current_pts.append((points[-1],))
        self.current_pts = current_pts

    def _curves_to_quadratic(self, pointsList):
        curves = []
        for current_pt, points in zip(self.current_pts, pointsList):
            curves.append(current_pt + points)
        quadratics = curves_to_quadratic(curves, [self.max_err] * len(curves))
        pointsList = []
        for quadratic in quadratics:
            pointsList.append(quadratic[1:])
        self.qCurveTo(pointsList)

    def curveTo(self, pointsList):
        self._check_contour_is_open()
        self._curves_to_quadratic(pointsList)

    def closePath(self):
        self._check_contour_is_open()
        if self.start_pts is None:
            for pen in self.pens:
                pen.closePath()
        self.current_pts = self.start_pts = None

    def endPath(self):
        self._check_contour_is_open()
        if self.start_pts is None:
            for pen in self.pens:
                pen.endPath()
        self.current_pts = self.start_pts = None

    def addComponent(self, glyphName, transformations):
        self._check_contour_is_closed()
        for trans, pen in zip(transformations, self.pens):
            pen.addComponent(glyphName, trans)

# === NexusCore/openenv\Lib\site-packages\litellm\secret_managers\hashicorp_secret_manager.py ===
import os
from typing import Any, Dict, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.caching import InMemoryCache
from litellm.constants import SECRET_MANAGER_REFRESH_INTERVAL
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import KeyManagementSystem

from .base_secret_manager import BaseSecretManager


class HashicorpSecretManager(BaseSecretManager):
    def __init__(self):
        from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

        # Vault-specific config
        self.vault_addr = os.getenv("HCP_VAULT_ADDR", "http://127.0.0.1:8200")
        self.vault_token = os.getenv("HCP_VAULT_TOKEN", "")
        # If your KV engine is mounted somewhere other than "secret", adjust here:
        self.vault_namespace = os.getenv("HCP_VAULT_NAMESPACE", None)

        # Optional config for TLS cert auth
        self.tls_cert_path = os.getenv("HCP_VAULT_CLIENT_CERT", "")
        self.tls_key_path = os.getenv("HCP_VAULT_CLIENT_KEY", "")
        self.vault_cert_role = os.getenv("HCP_VAULT_CERT_ROLE", None)

        # Validate environment
        if not self.vault_token:
            raise ValueError(
                "Missing Vault token. Please set HCP_VAULT_TOKEN in your environment."
            )

        litellm.secret_manager_client = self
        litellm._key_management_system = KeyManagementSystem.HASHICORP_VAULT
        _refresh_interval = os.environ.get(
            "HCP_VAULT_REFRESH_INTERVAL", SECRET_MANAGER_REFRESH_INTERVAL
        )
        _refresh_interval = (
            int(_refresh_interval)
            if _refresh_interval
            else SECRET_MANAGER_REFRESH_INTERVAL
        )
        self.cache = InMemoryCache(
            default_ttl=_refresh_interval
        )  # store in memory for 1 day

        if premium_user is not True:
            raise ValueError(
                f"Hashicorp secret manager is only available for premium users. {CommonProxyErrors.not_premium_user.value}"
            )

    def _auth_via_tls_cert(self) -> str:
        """
        Ref: https://developer.hashicorp.com/vault/api-docs/auth/cert

        Request:
        ```
        curl \
            --request POST \
            --cacert vault-ca.pem \
            --cert cert.pem \
            --key key.pem \
            --header "X-Vault-Namespace: mynamespace/" \
            --data '{"name": "my-cert-role"}' \
            https://127.0.0.1:8200/v1/auth/cert/login
        ```

        Response:
        ```
        {
            "auth": {
                "client_token": "cf95f87d-f95b-47ff-b1f5-ba7bff850425",
                "policies": ["web", "stage"],
                "lease_duration": 3600,
                "renewable": true
            }
        }
        ```
        """
        verbose_logger.debug("Using TLS cert auth for Hashicorp Vault")
        # Vault endpoint for cert-based login, e.g. '/v1/auth/cert/login'
        login_url = f"{self.vault_addr}/v1/auth/cert/login"

        # Include your Vault namespace in the header if you're using namespaces.
        # E.g. self.vault_namespace = 'mynamespace/'
        # If you only have root namespace, you can omit this header entirely.
        headers = {}
        if hasattr(self, "vault_namespace") and self.vault_namespace:
            headers["X-Vault-Namespace"] = self.vault_namespace
        try:
            # We use the client cert and key for mutual TLS
            client = httpx.Client(cert=(self.tls_cert_path, self.tls_key_path))
            resp = client.post(
                login_url,
                headers=headers,
                json=self._get_tls_cert_auth_body(),
            )
            resp.raise_for_status()
            token = resp.json()["auth"]["client_token"]
            _lease_duration = resp.json()["auth"]["lease_duration"]
            verbose_logger.info("Successfully obtained Vault token via TLS cert auth.")
            self.cache.set_cache(
                key="hcp_vault_token", value=token, ttl=_lease_duration
            )
            return token
        except Exception as e:
            raise RuntimeError(f"Could not authenticate to Vault via TLS cert: {e}")

    def _get_tls_cert_auth_body(self) -> dict:
        return {"name": self.vault_cert_role}

    def get_url(self, secret_name: str) -> str:
        _url = f"{self.vault_addr}/v1/"
        if self.vault_namespace:
            _url += f"{self.vault_namespace}/"
        _url += f"secret/data/{secret_name}"
        return _url

    def _get_request_headers(self) -> dict:
        if self.tls_cert_path and self.tls_key_path:
            return {"X-Vault-Token": self._auth_via_tls_cert()}
        return {"X-Vault-Token": self.vault_token}

    async def async_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Optional[str]:
        """
        Reads a secret from Vault KV v2 using an async HTTPX client.
        secret_name is just the path inside the KV mount (e.g., 'myapp/config').
        Returns the entire data dict from data.data, or None on failure.
        """
        if self.cache.get_cache(secret_name) is not None:
            return self.cache.get_cache(secret_name)
        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
        )
        try:
            # For KV v2: /v1/<mount>/data/<path>
            # Example: http://127.0.0.1:8200/v1/secret/data/myapp/config
            _url = self.get_url(secret_name)
            url = _url

            response = await async_client.get(url, headers=self._get_request_headers())
            response.raise_for_status()

            # For KV v2, the secret is in response.json()["data"]["data"]
            json_resp = response.json()
            _value = self._get_secret_value_from_json_response(json_resp)
            self.cache.set_cache(secret_name, _value)
            return _value

        except Exception as e:
            verbose_logger.exception(f"Error reading secret from Hashicorp Vault: {e}")
            return None

    def sync_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Optional[str]:
        """
        Reads a secret from Vault KV v2 using a sync HTTPX client.
        secret_name is just the path inside the KV mount (e.g., 'myapp/config').
        Returns the entire data dict from data.data, or None on failure.
        """
        if self.cache.get_cache(secret_name) is not None:
            return self.cache.get_cache(secret_name)
        sync_client = _get_httpx_client()
        try:
            # For KV v2: /v1/<mount>/data/<path>
            url = self.get_url(secret_name)

            response = sync_client.get(url, headers=self._get_request_headers())
            response.raise_for_status()

            # For KV v2, the secret is in response.json()["data"]["data"]
            json_resp = response.json()
            _value = self._get_secret_value_from_json_response(json_resp)
            self.cache.set_cache(secret_name, _value)
            return _value

        except Exception as e:
            verbose_logger.exception(f"Error reading secret from Hashicorp Vault: {e}")
            return None

    async def async_write_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Dict[str, Any]:
        """
        Writes a secret to Vault KV v2 using an async HTTPX client.

        Args:
            secret_name: Path inside the KV mount (e.g., 'myapp/config')
            secret_value: Value to store
            description: Optional description for the secret
            optional_params: Additional parameters to include in the secret data
            timeout: Request timeout

        Returns:
            dict: Response containing status and details of the operation
        """
        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
            params={"timeout": timeout},
        )

        try:
            url = self.get_url(secret_name)

            # Prepare the secret data
            data = {"data": {"key": secret_value}}

            if description:
                data["data"]["description"] = description

            response = await async_client.post(
                url=url, headers=self._get_request_headers(), json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            verbose_logger.exception(f"Error writing secret to Hashicorp Vault: {e}")
            return {"status": "error", "message": str(e)}

    async def async_rotate_secret(
        self,
        current_secret_name: str,
        new_secret_name: str,
        new_secret_value: str,
        optional_params: Dict | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> Dict:
        raise NotImplementedError("Hashicorp does not support secret rotation")

    async def async_delete_secret(
        self,
        secret_name: str,
        recovery_window_in_days: Optional[int] = 7,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> dict:
        """
        Async function to delete a secret from Hashicorp Vault.
        In KV v2, this marks the latest version of the secret as deleted.

        Args:
            secret_name: Name of the secret to delete
            recovery_window_in_days: Not used for Vault (Vault handles this internally)
            optional_params: Additional parameters specific to the secret manager
            timeout: Request timeout

        Returns:
            dict: Response containing status and details of the operation
        """
        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
            params={"timeout": timeout},
        )

        try:
            # For KV v2 delete: /v1/<mount>/data/<path>
            url = self.get_url(secret_name)

            response = await async_client.delete(
                url=url, headers=self._get_request_headers()
            )
            response.raise_for_status()

            # Clear the cache for this secret
            self.cache.delete_cache(secret_name)

            return {
                "status": "success",
                "message": f"Secret {secret_name} deleted successfully",
            }
        except Exception as e:
            verbose_logger.exception(f"Error deleting secret from Hashicorp Vault: {e}")
            return {"status": "error", "message": str(e)}

    def _get_secret_value_from_json_response(
        self, json_resp: Optional[dict]
    ) -> Optional[str]:
        """
        Get the secret value from the JSON response

        Json response from hashicorp vault is of the form:

        {
            "request_id":"036ba77c-018b-31dd-047b-323bcd0cd332",
            "lease_id":"",
            "renewable":false,
            "lease_duration":0,
            "data":
                {"data":
                    {"key":"Vault Is The Way"},
                    "metadata":{"created_time":"2025-01-01T22:13:50.93942388Z","custom_metadata":null,"deletion_time":"","destroyed":false,"version":1}
                },
            "wrap_info":null,
            "warnings":null,
            "auth":null,
            "mount_type":"kv"
        }

        Note: LiteLLM assumes that all secrets are stored as under the key "key"
        """
        if json_resp is None:
            return None
        return json_resp.get("data", {}).get("data", {}).get("key", None)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\opik\opik.py ===
"""
Opik Logger that logs LLM events to an Opik server
"""

import asyncio
import json
import traceback
from typing import Dict, List

from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
    httpxSpecialProvider,
)

from .utils import (
    create_usage_object,
    create_uuid7,
    get_opik_config_variable,
    get_traces_and_spans_from_payload,
)


class OpikLogger(CustomBatchLogger):
    """
    Opik Logger for logging events to an Opik Server
    """

    def __init__(self, **kwargs):
        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        self.sync_httpx_client = _get_httpx_client()

        self.opik_project_name = get_opik_config_variable(
            "project_name",
            user_value=kwargs.get("project_name", None),
            default_value="Default Project",
        )

        opik_base_url = get_opik_config_variable(
            "url_override",
            user_value=kwargs.get("url", None),
            default_value="https://www.comet.com/opik/api",
        )
        opik_api_key = get_opik_config_variable(
            "api_key", user_value=kwargs.get("api_key", None), default_value=None
        )
        opik_workspace = get_opik_config_variable(
            "workspace", user_value=kwargs.get("workspace", None), default_value=None
        )

        self.trace_url = f"{opik_base_url}/v1/private/traces/batch"
        self.span_url = f"{opik_base_url}/v1/private/spans/batch"

        self.headers = {}
        if opik_workspace:
            self.headers["Comet-Workspace"] = opik_workspace

        if opik_api_key:
            self.headers["authorization"] = opik_api_key

        self.opik_workspace = opik_workspace
        self.opik_api_key = opik_api_key
        try:
            asyncio.create_task(self.periodic_flush())
            self.flush_lock = asyncio.Lock()
        except Exception as e:
            verbose_logger.exception(
                f"OpikLogger - Asynchronous processing not initialized as we are not running in an async context {str(e)}"
            )
            self.flush_lock = None

        super().__init__(**kwargs, flush_lock=self.flush_lock)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            opik_payload = self._create_opik_payload(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=start_time,
                end_time=end_time,
            )

            self.log_queue.extend(opik_payload)
            verbose_logger.debug(
                f"OpikLogger added event to log_queue - Will flush in {self.flush_interval} seconds..."
            )

            if len(self.log_queue) >= self.batch_size:
                verbose_logger.debug("OpikLogger - Flushing batch")
                await self.flush_queue()
        except Exception as e:
            verbose_logger.exception(
                f"OpikLogger failed to log success event - {str(e)}\n{traceback.format_exc()}"
            )

    def _sync_send(self, url: str, headers: Dict[str, str], batch: Dict):
        try:
            response = self.sync_httpx_client.post(
                url=url, headers=headers, json=batch  # type: ignore
            )
            response.raise_for_status()
            if response.status_code != 204:
                raise Exception(
                    f"Response from opik API status_code: {response.status_code}, text: {response.text}"
                )
        except Exception as e:
            verbose_logger.exception(
                f"OpikLogger failed to send batch - {str(e)}\n{traceback.format_exc()}"
            )

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            opik_payload = self._create_opik_payload(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=start_time,
                end_time=end_time,
            )

            traces, spans = get_traces_and_spans_from_payload(opik_payload)
            if len(traces) > 0:
                self._sync_send(
                    url=self.trace_url, headers=self.headers, batch={"traces": traces}
                )
            if len(spans) > 0:
                self._sync_send(
                    url=self.span_url, headers=self.headers, batch={"spans": spans}
                )
        except Exception as e:
            verbose_logger.exception(
                f"OpikLogger failed to log success event - {str(e)}\n{traceback.format_exc()}"
            )

    async def _submit_batch(self, url: str, headers: Dict[str, str], batch: Dict):
        try:
            response = await self.async_httpx_client.post(
                url=url, headers=headers, json=batch  # type: ignore
            )
            response.raise_for_status()

            if response.status_code >= 300:
                verbose_logger.error(
                    f"OpikLogger - Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.info(
                    f"OpikLogger - {len(self.log_queue)} Opik events submitted"
                )
        except Exception as e:
            verbose_logger.exception(f"OpikLogger failed to send batch - {str(e)}")

    def _create_opik_headers(self):
        headers = {}
        if self.opik_workspace:
            headers["Comet-Workspace"] = self.opik_workspace

        if self.opik_api_key:
            headers["authorization"] = self.opik_api_key
        return headers

    async def async_send_batch(self):
        verbose_logger.info("Calling async_send_batch")
        if not self.log_queue:
            return

        # Split the log_queue into traces and spans
        traces, spans = get_traces_and_spans_from_payload(self.log_queue)

        # Send trace batch
        if len(traces) > 0:
            await self._submit_batch(
                url=self.trace_url, headers=self.headers, batch={"traces": traces}
            )
            verbose_logger.info(f"Sent {len(traces)} traces")
        if len(spans) > 0:
            await self._submit_batch(
                url=self.span_url, headers=self.headers, batch={"spans": spans}
            )
            verbose_logger.info(f"Sent {len(spans)} spans")

    def _create_opik_payload(  # noqa: PLR0915
        self, kwargs, response_obj, start_time, end_time
    ) -> List[Dict]:
        # Get metadata
        _litellm_params = kwargs.get("litellm_params", {}) or {}
        litellm_params_metadata = _litellm_params.get("metadata", {}) or {}

        # Extract opik metadata
        litellm_opik_metadata = litellm_params_metadata.get("opik", {})
        verbose_logger.debug(
            f"litellm_opik_metadata - {json.dumps(litellm_opik_metadata, default=str)}"
        )
        project_name = litellm_opik_metadata.get("project_name", self.opik_project_name)

        # Extract trace_id and parent_span_id
        current_span_data = litellm_opik_metadata.get("current_span_data", None)
        if isinstance(current_span_data, dict):
            trace_id = current_span_data.get("trace_id", None)
            parent_span_id = current_span_data.get("id", None)
        elif current_span_data:
            trace_id = current_span_data.trace_id
            parent_span_id = current_span_data.id
        else:
            trace_id = None
            parent_span_id = None
        # Create Opik tags
        opik_tags = litellm_opik_metadata.get("tags", [])
        if kwargs.get("custom_llm_provider"):
            opik_tags.append(kwargs["custom_llm_provider"])

        # Use standard_logging_object to create metadata and input/output data
        standard_logging_object = kwargs.get("standard_logging_object", None)
        if standard_logging_object is None:
            verbose_logger.debug(
                "OpikLogger skipping event; no standard_logging_object found"
            )
            return []

        # Create input and output data
        input_data = standard_logging_object.get("messages", {})
        output_data = standard_logging_object.get("response", {})

        # Create usage object
        usage = create_usage_object(response_obj["usage"])

        # Define span and trace names
        span_name = "%s_%s_%s" % (
            response_obj.get("model", "unknown-model"),
            response_obj.get("object", "unknown-object"),
            response_obj.get("created", 0),
        )
        trace_name = response_obj.get("object", "unknown type")

        # Create metadata object, we add the opik metadata first and then
        # update it with the standard_logging_object metadata
        metadata = litellm_opik_metadata
        if "current_span_data" in metadata:
            del metadata["current_span_data"]
        metadata["created_from"] = "litellm"

        metadata.update(standard_logging_object.get("metadata", {}))
        if "call_type" in standard_logging_object:
            metadata["type"] = standard_logging_object["call_type"]
        if "status" in standard_logging_object:
            metadata["status"] = standard_logging_object["status"]
        if "response_cost" in kwargs:
            metadata["cost"] = {
                "total_tokens": kwargs["response_cost"],
                "currency": "USD",
            }
        if "response_cost_failure_debug_info" in kwargs:
            metadata["response_cost_failure_debug_info"] = kwargs[
                "response_cost_failure_debug_info"
            ]
        if "model_map_information" in standard_logging_object:
            metadata["model_map_information"] = standard_logging_object[
                "model_map_information"
            ]
        if "model" in standard_logging_object:
            metadata["model"] = standard_logging_object["model"]
        if "model_id" in standard_logging_object:
            metadata["model_id"] = standard_logging_object["model_id"]
        if "model_group" in standard_logging_object:
            metadata["model_group"] = standard_logging_object["model_group"]
        if "api_base" in standard_logging_object:
            metadata["api_base"] = standard_logging_object["api_base"]
        if "cache_hit" in standard_logging_object:
            metadata["cache_hit"] = standard_logging_object["cache_hit"]
        if "saved_cache_cost" in standard_logging_object:
            metadata["saved_cache_cost"] = standard_logging_object["saved_cache_cost"]
        if "error_str" in standard_logging_object:
            metadata["error_str"] = standard_logging_object["error_str"]
        if "model_parameters" in standard_logging_object:
            metadata["model_parameters"] = standard_logging_object["model_parameters"]
        if "hidden_params" in standard_logging_object:
            metadata["hidden_params"] = standard_logging_object["hidden_params"]

        payload = []
        if trace_id is None:
            trace_id = create_uuid7()
            verbose_logger.debug(
                f"OpikLogger creating payload for trace with id {trace_id}"
            )

            payload.append(
                {
                    "project_name": project_name,
                    "id": trace_id,
                    "name": trace_name,
                    "start_time": start_time.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "input": input_data,
                    "output": output_data,
                    "metadata": metadata,
                    "tags": opik_tags,
                }
            )

        span_id = create_uuid7()
        verbose_logger.debug(
            f"OpikLogger creating payload for trace with id {trace_id} and span with id {span_id}"
        )
        payload.append(
            {
                "id": span_id,
                "project_name": project_name,
                "trace_id": trace_id,
                "parent_span_id": parent_span_id,
                "name": span_name,
                "type": "llm",
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "input": input_data,
                "output": output_data,
                "metadata": metadata,
                "tags": opik_tags,
                "usage": usage,
            }
        )
        verbose_logger.debug(f"Payload: {payload}")
        return payload

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure_ai\chat\transformation.py ===
import enum
from typing import Any, List, Optional, Tuple, cast
from urllib.parse import urlparse

import httpx
from httpx import Response

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    _audio_or_image_in_message_content,
    convert_content_list_to_str,
)
from litellm.llms.base_llm.chat.transformation import LiteLLMLoggingObj
from litellm.llms.openai.common_utils import drop_params_from_unprocessable_entity_error
from litellm.llms.openai.openai import OpenAIConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse, ProviderField
from litellm.utils import _add_path_to_api_base, supports_tool_choice


class AzureFoundryErrorStrings(str, enum.Enum):
    SET_EXTRA_PARAMETERS_TO_PASS_THROUGH = "Set extra-parameters to 'pass-through'"


class AzureAIStudioConfig(OpenAIConfig):
    def get_supported_openai_params(self, model: str) -> List:
        model_supports_tool_choice = True  # azure ai supports this by default
        if not supports_tool_choice(model=f"azure_ai/{model}"):
            model_supports_tool_choice = False
        supported_params = super().get_supported_openai_params(model)
        if not model_supports_tool_choice:
            filtered_supported_params = []
            for param in supported_params:
                if param != "tool_choice":
                    filtered_supported_params.append(param)
            return filtered_supported_params
        return supported_params

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
        if api_base and self._should_use_api_key_header(api_base):
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        headers["Content-Type"] = (
            "application/json"  # tell Azure AI Studio to expect JSON
        )

        return headers

    def _should_use_api_key_header(self, api_base: str) -> bool:
        """
        Returns True if the request should use `api-key` header for authentication.
        """
        parsed_url = urlparse(api_base)
        host = parsed_url.hostname
        if host and (
            host.endswith(".services.ai.azure.com")
            or host.endswith(".openai.azure.com")
        ):
            return True
        return False

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
        Constructs a complete URL for the API request.

        Args:
        - api_base: Base URL, e.g.,
            "https://litellm8397336933.services.ai.azure.com"
            OR
            "https://litellm8397336933.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview"
        - model: Model name.
        - optional_params: Additional query parameters, including "api_version".
        - stream: If streaming is required (optional).

        Returns:
        - A complete URL string, e.g.,
        "https://litellm8397336933.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview"
        """
        if api_base is None:
            raise ValueError(
                f"api_base is required for Azure AI Studio. Please set the api_base parameter. Passed `api_base={api_base}`"
            )
        original_url = httpx.URL(api_base)

        # Extract api_version or use default
        api_version = cast(Optional[str], litellm_params.get("api_version"))

        # Create a new dictionary with existing params
        query_params = dict(original_url.params)

        # Add api_version if needed
        if "api-version" not in query_params and api_version:
            query_params["api-version"] = api_version

        # Add the path to the base URL
        if "services.ai.azure.com" in api_base:
            new_url = _add_path_to_api_base(
                api_base=api_base, ending_path="/models/chat/completions"
            )
        else:
            new_url = _add_path_to_api_base(
                api_base=api_base, ending_path="/chat/completions"
            )

        # Use the new query_params dictionary
        final_url = httpx.URL(new_url).copy_with(params=query_params)

        return str(final_url)

    def get_required_params(self) -> List[ProviderField]:
        """For a given provider, return it's required fields with a description"""
        return [
            ProviderField(
                field_name="api_key",
                field_type="string",
                field_description="Your Azure AI Studio API Key.",
                field_value="zEJ...",
            ),
            ProviderField(
                field_name="api_base",
                field_type="string",
                field_description="Your Azure AI Studio API Base.",
                field_value="https://Mistral-serverless.",
            ),
        ]

    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
    ) -> List:
        """
        - Azure AI Studio doesn't support content as a list. This handles:
            1. Transforms list content to a string.
            2. If message contains an image or audio, send as is (user-intended)
        """
        for message in messages:
            # Do nothing if the message contains an image or audio
            if _audio_or_image_in_message_content(message):
                continue

            texts = convert_content_list_to_str(message=message)
            if texts:
                message["content"] = texts
        return messages

    def _is_azure_openai_model(self, model: str, api_base: Optional[str]) -> bool:
        try:
            if "/" in model:
                model = model.split("/", 1)[1]
            if (
                model in litellm.open_ai_chat_completion_models
                or model in litellm.open_ai_text_completion_models
                or model in litellm.open_ai_embedding_models
            ):
                return True

        except Exception:
            return False
        return False

    def _get_openai_compatible_provider_info(
        self,
        model: str,
        api_base: Optional[str],
        api_key: Optional[str],
        custom_llm_provider: str,
    ) -> Tuple[Optional[str], Optional[str], str]:
        api_base = api_base or get_secret_str("AZURE_AI_API_BASE")
        dynamic_api_key = api_key or get_secret_str("AZURE_AI_API_KEY")

        if self._is_azure_openai_model(model=model, api_base=api_base):
            verbose_logger.debug(
                "Model={} is Azure OpenAI model. Setting custom_llm_provider='azure'.".format(
                    model
                )
            )
            custom_llm_provider = "azure"
        return api_base, dynamic_api_key, custom_llm_provider

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        extra_body = optional_params.pop("extra_body", {})
        if extra_body and isinstance(extra_body, dict):
            optional_params.update(extra_body)
        optional_params.pop("max_retries", None)
        return super().transform_request(
            model, messages, optional_params, litellm_params, headers
        )

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
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        model_response.model = f"azure_ai/{model}"
        return super().transform_response(
            model=model,
            raw_response=raw_response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=request_data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            api_key=api_key,
            json_mode=json_mode,
        )

    def should_retry_llm_api_inside_llm_translation_on_http_error(
        self, e: httpx.HTTPStatusError, litellm_params: dict
    ) -> bool:
        should_drop_params = litellm_params.get("drop_params") or litellm.drop_params
        error_text = e.response.text

        if should_drop_params and "Extra inputs are not permitted" in error_text:
            return True
        elif (
            "unknown field: parameter index is not a valid field" in error_text
        ):  # remove index from tool calls
            return True
        elif (
            AzureFoundryErrorStrings.SET_EXTRA_PARAMETERS_TO_PASS_THROUGH.value
            in error_text
        ):  # remove extra-parameters from tool calls
            return True
        return super().should_retry_llm_api_inside_llm_translation_on_http_error(
            e=e, litellm_params=litellm_params
        )

    @property
    def max_retry_on_unprocessable_entity_error(self) -> int:
        return 2

    def transform_request_on_unprocessable_entity_error(
        self, e: httpx.HTTPStatusError, request_data: dict
    ) -> dict:
        _messages = cast(Optional[List[AllMessageValues]], request_data.get("messages"))
        if (
            "unknown field: parameter index is not a valid field" in e.response.text
            and _messages is not None
        ):
            litellm.remove_index_from_tool_calls(
                messages=_messages,
            )
        elif (
            AzureFoundryErrorStrings.SET_EXTRA_PARAMETERS_TO_PASS_THROUGH.value
            in e.response.text
        ):
            request_data = self._drop_extra_params_from_request_data(
                request_data, e.response.text
            )
        data = drop_params_from_unprocessable_entity_error(e=e, data=request_data)
        return data

    def _drop_extra_params_from_request_data(
        self, request_data: dict, error_text: str
    ) -> dict:
        params_to_drop = self._extract_params_to_drop_from_error_text(error_text)
        if params_to_drop:
            for param in params_to_drop:
                if param in request_data:
                    request_data.pop(param, None)
        return request_data

    def _extract_params_to_drop_from_error_text(
        self, error_text: str
    ) -> Optional[List[str]]:
        """
        Error text looks like this"
            "Extra parameters ['stream_options', 'extra-parameters'] are not allowed when extra-parameters is not set or set to be 'error'.
        """
        import re

        # Extract parameters within square brackets
        match = re.search(r"\[(.*?)\]", error_text)
        if not match:
            return []

        # Parse the extracted string into a list of parameter names
        params_str = match.group(1)
        params = []
        for param in params_str.split(","):
            # Clean up the parameter name (remove quotes, spaces)
            clean_param = param.strip().strip("'").strip('"')
            if clean_param:
                params.append(clean_param)
        return params

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\template.py ===
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

import itertools as it
from abc import ABCMeta, abstractmethod

from nltk.tbl.feature import Feature
from nltk.tbl.rule import Rule


class BrillTemplateI(metaclass=ABCMeta):
    """
    An interface for generating lists of transformational rules that
    apply at given sentence positions.  ``BrillTemplateI`` is used by
    ``Brill`` training algorithms to generate candidate rules.
    """

    @abstractmethod
    def applicable_rules(self, tokens, i, correctTag):
        """
        Return a list of the transformational rules that would correct
        the ``i``-th subtoken's tag in the given token.  In particular,
        return a list of zero or more rules that would change
        ``tokens[i][1]`` to ``correctTag``, if applied to ``token[i]``.

        If the ``i``-th token already has the correct tag (i.e., if
        ``tagged_tokens[i][1] == correctTag``), then
        ``applicable_rules()`` should return the empty list.

        :param tokens: The tagged tokens being tagged.
        :type tokens: list(tuple)
        :param i: The index of the token whose tag should be corrected.
        :type i: int
        :param correctTag: The correct tag for the ``i``-th token.
        :type correctTag: any
        :rtype: list(BrillRule)
        """

    @abstractmethod
    def get_neighborhood(self, token, index):
        """
        Returns the set of indices *i* such that
        ``applicable_rules(token, i, ...)`` depends on the value of
        the *index*th token of *token*.

        This method is used by the "fast" Brill tagger trainer.

        :param token: The tokens being tagged.
        :type token: list(tuple)
        :param index: The index whose neighborhood should be returned.
        :type index: int
        :rtype: set
        """


class Template(BrillTemplateI):
    """
    A tbl Template that generates a list of L{Rule}s that apply at a given sentence
    position.  In particular, each C{Template} is parameterized by a list of
    independent features (a combination of a specific
    property to extract and a list C{L} of relative positions at which to extract
    it) and generates all Rules that:

      - use the given features, each at its own independent position; and
      - are applicable to the given token.
    """

    ALLTEMPLATES = []
    # record a unique id of form "001", for each template created
    # _ids = it.count(0)

    def __init__(self, *features):
        """
        Construct a Template for generating Rules.

        Takes a list of Features. A C{Feature} is a combination
        of a specific property and its relative positions and should be
        a subclass of L{nltk.tbl.feature.Feature}.

        An alternative calling convention (kept for backwards compatibility,
        but less expressive as it only permits one feature type) is
        Template(Feature, (start1, end1), (start2, end2), ...)
        In new code, that would be better written
        Template(Feature(start1, end1), Feature(start2, end2), ...)

        For instance, importing some features

        >>> from nltk.tbl.template import Template
        >>> from nltk.tag.brill import Word, Pos

        Create some features

        >>> wfeat1, wfeat2, pfeat = (Word([-1]), Word([1,2]), Pos([-2,-1]))

        Create a single-feature template

        >>> Template(wfeat1)
        Template(Word([-1]))

        Or a two-feature one

        >>> Template(wfeat1, wfeat2)
        Template(Word([-1]),Word([1, 2]))

        Or a three-feature one with two different feature types

        >>> Template(wfeat1, wfeat2, pfeat)
        Template(Word([-1]),Word([1, 2]),Pos([-2, -1]))

        deprecated api: Feature subclass, followed by list of (start,end) pairs
        (permits only a single Feature)

        >>> Template(Word, (-2,-1), (0,0))
        Template(Word([-2, -1]),Word([0]))

        Incorrect specification raises TypeError

        >>> Template(Word, (-2,-1), Pos, (0,0))
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "nltk/tag/tbl/template.py", line 143, in __init__
            raise TypeError(
        TypeError: expected either Feature1(args), Feature2(args), ... or Feature, (start1, end1), (start2, end2), ...

        :type features: list of Features
        :param features: the features to build this Template on
        """
        # determine the calling form: either
        # Template(Feature, args1, [args2, ...)]
        # Template(Feature1(args),  Feature2(args), ...)
        if all(isinstance(f, Feature) for f in features):
            self._features = features
        elif issubclass(features[0], Feature) and all(
            isinstance(a, tuple) for a in features[1:]
        ):
            self._features = [features[0](*tp) for tp in features[1:]]
        else:
            raise TypeError(
                "expected either Feature1(args), Feature2(args), ... or Feature, (start1, end1), (start2, end2), ..."
            )
        self.id = f"{len(self.ALLTEMPLATES):03d}"
        self.ALLTEMPLATES.append(self)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ",".join([str(f) for f in self._features]),
        )

    def applicable_rules(self, tokens, index, correct_tag):
        if tokens[index][1] == correct_tag:
            return []

        # For each of this Template's features, find the conditions
        # that are applicable for the given token.
        # Then, generate one Rule for each combination of features
        # (the crossproduct of the conditions).

        applicable_conditions = self._applicable_conditions(tokens, index)
        xs = list(it.product(*applicable_conditions))
        return [Rule(self.id, tokens[index][1], correct_tag, tuple(x)) for x in xs]

    def _applicable_conditions(self, tokens, index):
        """
        :returns: A set of all conditions for rules
        that are applicable to C{tokens[index]}.
        """
        conditions = []

        for feature in self._features:
            conditions.append([])
            for pos in feature.positions:
                if not (0 <= index + pos < len(tokens)):
                    continue
                value = feature.extract_property(tokens, index + pos)
                conditions[-1].append((feature, value))
        return conditions

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI

        # applicable_rules(tokens, index, ...) depends on index.
        neighborhood = {index}  # set literal for python 2.7+

        # applicable_rules(tokens, i, ...) depends on index if
        # i+start < index <= i+end.

        allpositions = [0] + [p for feat in self._features for p in feat.positions]
        start, end = min(allpositions), max(allpositions)
        s = max(0, index + (-end))
        e = min(index + (-start) + 1, len(tokens))
        for i in range(s, e):
            neighborhood.add(i)
        return neighborhood

    @classmethod
    def expand(cls, featurelists, combinations=None, skipintersecting=True):
        """
        Factory method to mass generate Templates from a list L of lists of  Features.

        #With combinations=(k1, k2), the function will in all possible ways choose k1 ... k2
        #of the sublists in L; it will output all Templates formed by the Cartesian product
        #of this selection, with duplicates and other semantically equivalent
        #forms removed. Default for combinations is (1, len(L)).

        The feature lists may have been specified
        manually, or generated from Feature.expand(). For instance,

        >>> from nltk.tbl.template import Template
        >>> from nltk.tag.brill import Word, Pos

        #creating some features
        >>> (wd_0, wd_01) = (Word([0]), Word([0,1]))

        >>> (pos_m2, pos_m33) = (Pos([-2]), Pos([3-2,-1,0,1,2,3]))

        >>> list(Template.expand([[wd_0], [pos_m2]]))
        [Template(Word([0])), Template(Pos([-2])), Template(Pos([-2]),Word([0]))]

        >>> list(Template.expand([[wd_0, wd_01], [pos_m2]]))
        [Template(Word([0])), Template(Word([0, 1])), Template(Pos([-2])), Template(Pos([-2]),Word([0])), Template(Pos([-2]),Word([0, 1]))]

        #note: with Feature.expand(), it is very easy to generate more templates
        #than your system can handle -- for instance,
        >>> wordtpls = Word.expand([-2,-1,0,1], [1,2], excludezero=False)
        >>> len(wordtpls)
        7

        >>> postpls = Pos.expand([-3,-2,-1,0,1,2], [1,2,3], excludezero=True)
        >>> len(postpls)
        9

        #and now the Cartesian product of all non-empty combinations of two wordtpls and
        #two postpls, with semantic equivalents removed
        >>> templates = list(Template.expand([wordtpls, wordtpls, postpls, postpls]))
        >>> len(templates)
        713


          will return a list of eight templates
              Template(Word([0])),
              Template(Word([0, 1])),
              Template(Pos([-2])),
              Template(Pos([-1])),
              Template(Pos([-2]),Word([0])),
              Template(Pos([-1]),Word([0])),
              Template(Pos([-2]),Word([0, 1])),
              Template(Pos([-1]),Word([0, 1]))]


        #Templates where one feature is a subset of another, such as
        #Template(Word([0,1]), Word([1]), will not appear in the output.
        #By default, this non-subset constraint is tightened to disjointness:
        #Templates of type Template(Word([0,1]), Word([1,2]) will also be filtered out.
        #With skipintersecting=False, then such Templates are allowed

        WARNING: this method makes it very easy to fill all your memory when training
        generated templates on any real-world corpus

        :param featurelists: lists of Features, whose Cartesian product will return a set of Templates
        :type featurelists: list of (list of Features)
        :param combinations: given n featurelists: if combinations=k, all generated Templates will have
                k features; if combinations=(k1,k2) they will have k1..k2 features; if None, defaults to 1..n
        :type combinations: None, int, or (int, int)
        :param skipintersecting: if True, do not output intersecting Templates (non-disjoint positions for some feature)
        :type skipintersecting: bool
        :returns: generator of Templates

        """

        def nonempty_powerset(xs):  # xs is a list
            # itertools docnonempty_powerset([1,2,3]) --> (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

            # find the correct tuple given combinations, one of {None, k, (k1,k2)}
            k = combinations  # for brevity
            combrange = (
                (1, len(xs) + 1)
                if k is None
                else (
                    (k, k + 1)  # n over 1 .. n over n (all non-empty combinations)
                    if isinstance(k, int)
                    else (k[0], k[1] + 1)
                )  # n over k (only
            )  # n over k1, n over k1+1... n over k2
            return it.chain.from_iterable(
                it.combinations(xs, r) for r in range(*combrange)
            )

        seentemplates = set()
        for picks in nonempty_powerset(featurelists):
            for pick in it.product(*picks):
                if any(
                    i != j and x.issuperset(y)
                    for (i, x) in enumerate(pick)
                    for (j, y) in enumerate(pick)
                ):
                    continue
                if skipintersecting and any(
                    i != j and x.intersects(y)
                    for (i, x) in enumerate(pick)
                    for (j, y) in enumerate(pick)
                ):
                    continue
                thistemplate = cls(*sorted(pick))
                strpick = str(thistemplate)
                #!!FIXME --this is hackish
                if strpick in seentemplates:  # already added
                    cls._poptemplate()
                    continue
                seentemplates.add(strpick)
                yield thistemplate

    @classmethod
    def _cleartemplates(cls):
        cls.ALLTEMPLATES = []

    @classmethod
    def _poptemplate(cls):
        return cls.ALLTEMPLATES.pop() if cls.ALLTEMPLATES else None

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\teraterm.py ===
"""
    pygments.lexers.teraterm
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Tera Term macro files.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups
from pygments.token import Text, Comment, Operator, Name, String, \
    Number, Keyword, Error

__all__ = ['TeraTermLexer']


class TeraTermLexer(RegexLexer):
    """
    For Tera Term macro source code.
    """
    name = 'Tera Term macro'
    url = 'https://ttssh2.osdn.jp/'
    aliases = ['teratermmacro', 'teraterm', 'ttl']
    filenames = ['*.ttl']
    mimetypes = ['text/x-teratermmacro']
    version_added = '2.4'

    tokens = {
        'root': [
            include('comments'),
            include('labels'),
            include('commands'),
            include('builtin-variables'),
            include('user-variables'),
            include('operators'),
            include('numeric-literals'),
            include('string-literals'),
            include('all-whitespace'),
            (r'\S', Text),
        ],
        'comments': [
            (r';[^\r\n]*', Comment.Single),
            (r'/\*', Comment.Multiline, 'in-comment'),
        ],
        'in-comment': [
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^*/]+', Comment.Multiline),
            (r'[*/]', Comment.Multiline)
        ],
        'labels': [
            (r'(?i)^(\s*)(:[a-z0-9_]+)', bygroups(Text.Whitespace, Name.Label)),
        ],
        'commands': [
            (
                r'(?i)\b('
                r'basename|'
                r'beep|'
                r'bplusrecv|'
                r'bplussend|'
                r'break|'
                r'bringupbox|'
                # 'call' is handled separately.
                r'callmenu|'
                r'changedir|'
                r'checksum16|'
                r'checksum16file|'
                r'checksum32|'
                r'checksum32file|'
                r'checksum8|'
                r'checksum8file|'
                r'clearscreen|'
                r'clipb2var|'
                r'closesbox|'
                r'closett|'
                r'code2str|'
                r'connect|'
                r'continue|'
                r'crc16|'
                r'crc16file|'
                r'crc32|'
                r'crc32file|'
                r'cygconnect|'
                r'delpassword|'
                r'dirname|'
                r'dirnamebox|'
                r'disconnect|'
                r'dispstr|'
                r'do|'
                r'else|'
                r'elseif|'
                r'enablekeyb|'
                r'end|'
                r'endif|'
                r'enduntil|'
                r'endwhile|'
                r'exec|'
                r'execcmnd|'
                r'exit|'
                r'expandenv|'
                r'fileclose|'
                r'fileconcat|'
                r'filecopy|'
                r'filecreate|'
                r'filedelete|'
                r'filelock|'
                r'filemarkptr|'
                r'filenamebox|'
                r'fileopen|'
                r'fileread|'
                r'filereadln|'
                r'filerename|'
                r'filesearch|'
                r'fileseek|'
                r'fileseekback|'
                r'filestat|'
                r'filestrseek|'
                r'filestrseek2|'
                r'filetruncate|'
                r'fileunlock|'
                r'filewrite|'
                r'filewriteln|'
                r'findclose|'
                r'findfirst|'
                r'findnext|'
                r'flushrecv|'
                r'foldercreate|'
                r'folderdelete|'
                r'foldersearch|'
                r'for|'
                r'getdate|'
                r'getdir|'
                r'getenv|'
                r'getfileattr|'
                r'gethostname|'
                r'getipv4addr|'
                r'getipv6addr|'
                r'getmodemstatus|'
                r'getpassword|'
                r'getspecialfolder|'
                r'gettime|'
                r'gettitle|'
                r'getttdir|'
                r'getver|'
                # 'goto' is handled separately.
                r'if|'
                r'ifdefined|'
                r'include|'
                r'inputbox|'
                r'int2str|'
                r'intdim|'
                r'ispassword|'
                r'kmtfinish|'
                r'kmtget|'
                r'kmtrecv|'
                r'kmtsend|'
                r'listbox|'
                r'loadkeymap|'
                r'logautoclosemode|'
                r'logclose|'
                r'loginfo|'
                r'logopen|'
                r'logpause|'
                r'logrotate|'
                r'logstart|'
                r'logwrite|'
                r'loop|'
                r'makepath|'
                r'messagebox|'
                r'mpause|'
                r'next|'
                r'passwordbox|'
                r'pause|'
                r'quickvanrecv|'
                r'quickvansend|'
                r'random|'
                r'recvln|'
                r'regexoption|'
                r'restoresetup|'
                r'return|'
                r'rotateleft|'
                r'rotateright|'
                r'scprecv|'
                r'scpsend|'
                r'send|'
                r'sendbreak|'
                r'sendbroadcast|'
                r'sendfile|'
                r'sendkcode|'
                r'sendln|'
                r'sendlnbroadcast|'
                r'sendlnmulticast|'
                r'sendmulticast|'
                r'setbaud|'
                r'setdate|'
                r'setdebug|'
                r'setdir|'
                r'setdlgpos|'
                r'setdtr|'
                r'setecho|'
                r'setenv|'
                r'setexitcode|'
                r'setfileattr|'
                r'setflowctrl|'
                r'setmulticastname|'
                r'setpassword|'
                r'setrts|'
                r'setspeed|'
                r'setsync|'
                r'settime|'
                r'settitle|'
                r'show|'
                r'showtt|'
                r'sprintf|'
                r'sprintf2|'
                r'statusbox|'
                r'str2code|'
                r'str2int|'
                r'strcompare|'
                r'strconcat|'
                r'strcopy|'
                r'strdim|'
                r'strinsert|'
                r'strjoin|'
                r'strlen|'
                r'strmatch|'
                r'strremove|'
                r'strreplace|'
                r'strscan|'
                r'strspecial|'
                r'strsplit|'
                r'strtrim|'
                r'testlink|'
                r'then|'
                r'tolower|'
                r'toupper|'
                r'unlink|'
                r'until|'
                r'uptime|'
                r'var2clipb|'
                r'wait|'
                r'wait4all|'
                r'waitevent|'
                r'waitln|'
                r'waitn|'
                r'waitrecv|'
                r'waitregex|'
                r'while|'
                r'xmodemrecv|'
                r'xmodemsend|'
                r'yesnobox|'
                r'ymodemrecv|'
                r'ymodemsend|'
                r'zmodemrecv|'
                r'zmodemsend'
                r')\b',
                Keyword,
            ),
            (r'(?i)(call|goto)([ \t]+)([a-z0-9_]+)',
             bygroups(Keyword, Text.Whitespace, Name.Label)),
        ],
        'builtin-variables': [
            (
                r'(?i)('
                r'groupmatchstr1|'
                r'groupmatchstr2|'
                r'groupmatchstr3|'
                r'groupmatchstr4|'
                r'groupmatchstr5|'
                r'groupmatchstr6|'
                r'groupmatchstr7|'
                r'groupmatchstr8|'
                r'groupmatchstr9|'
                r'inputstr|'
                r'matchstr|'
                r'mtimeout|'
                r'param1|'
                r'param2|'
                r'param3|'
                r'param4|'
                r'param5|'
                r'param6|'
                r'param7|'
                r'param8|'
                r'param9|'
                r'paramcnt|'
                r'params|'
                r'result|'
                r'timeout'
                r')\b',
                Name.Builtin
            ),
        ],
        'user-variables': [
            (r'(?i)[a-z_][a-z0-9_]*', Name.Variable),
        ],
        'numeric-literals': [
            (r'(-?)([0-9]+)', bygroups(Operator, Number.Integer)),
            (r'(?i)\$[0-9a-f]+', Number.Hex),
        ],
        'string-literals': [
            (r'(?i)#(?:[0-9]+|\$[0-9a-f]+)', String.Char),
            (r"'[^'\n]*'", String.Single),
            (r'"[^"\n]*"', String.Double),
            # Opening quotes without a closing quote on the same line are errors.
            (r"('[^']*)(\n)", bygroups(Error, Text.Whitespace)),
            (r'("[^"]*)(\n)', bygroups(Error, Text.Whitespace)),
        ],
        'operators': [
            (r'and|not|or|xor', Operator.Word),
            (r'[!%&*+<=>^~\|\/-]+', Operator),
            (r'[()]', String.Symbol),
        ],
        'all-whitespace': [
            (r'\s+', Text.Whitespace),
        ],
    }

    # Turtle and Tera Term macro files share the same file extension
    # but each has a recognizable and distinct syntax.
    def analyse_text(text):
        if re.search(TeraTermLexer.tokens['commands'][0][0], text):
            return 0.01

# === NexusCore/myenv\Lib\site-packages\pip\_internal\vcs\subversion.py ===
import logging
import os
import re
from typing import List, Optional, Tuple

from pip._internal.utils.misc import (
    HiddenText,
    display_path,
    is_console_interactive,
    is_installable_dir,
    split_auth_from_netloc,
)
from pip._internal.utils.subprocess import CommandArgs, make_command
from pip._internal.vcs.versioncontrol import (
    AuthInfo,
    RemoteNotFoundError,
    RevOptions,
    VersionControl,
    vcs,
)

logger = logging.getLogger(__name__)

_svn_xml_url_re = re.compile('url="([^"]+)"')
_svn_rev_re = re.compile(r'committed-rev="(\d+)"')
_svn_info_xml_rev_re = re.compile(r'\s*revision="(\d+)"')
_svn_info_xml_url_re = re.compile(r"<url>(.*)</url>")


class Subversion(VersionControl):
    name = "svn"
    dirname = ".svn"
    repo_name = "checkout"
    schemes = ("svn+ssh", "svn+http", "svn+https", "svn+svn", "svn+file")

    @classmethod
    def should_add_vcs_url_prefix(cls, remote_url: str) -> bool:
        return True

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return ["-r", rev]

    @classmethod
    def get_revision(cls, location: str) -> str:
        """
        Return the maximum revision for all files under a given location
        """
        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, _ in os.walk(location):
            if cls.dirname not in dirs:
                dirs[:] = []
                continue  # no sense walking uncontrolled subdirs
            dirs.remove(cls.dirname)
            entries_fn = os.path.join(base, cls.dirname, "entries")
            if not os.path.exists(entries_fn):
                # FIXME: should we warn?
                continue

            dirurl, localrev = cls._get_svn_url_rev(base)

            if base == location:
                assert dirurl is not None
                base = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return str(revision)

    @classmethod
    def get_netloc_and_auth(
        cls, netloc: str, scheme: str
    ) -> Tuple[str, Tuple[Optional[str], Optional[str]]]:
        """
        This override allows the auth information to be passed to svn via the
        --username and --password options instead of via the URL.
        """
        if scheme == "ssh":
            # The --username and --password options can't be used for
            # svn+ssh URLs, so keep the auth information in the URL.
            return super().get_netloc_and_auth(netloc, scheme)

        return split_auth_from_netloc(netloc)

    @classmethod
    def get_url_rev_and_auth(cls, url: str) -> Tuple[str, Optional[str], AuthInfo]:
        # hotfix the URL scheme after removing svn+ from svn+ssh:// re-add it
        url, rev, user_pass = super().get_url_rev_and_auth(url)
        if url.startswith("ssh://"):
            url = "svn+" + url
        return url, rev, user_pass

    @staticmethod
    def make_rev_args(
        username: Optional[str], password: Optional[HiddenText]
    ) -> CommandArgs:
        extra_args: CommandArgs = []
        if username:
            extra_args += ["--username", username]
        if password:
            extra_args += ["--password", password]

        return extra_args

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        # In cases where the source is in a subdirectory, we have to look up in
        # the location until we find a valid project root.
        orig_location = location
        while not is_installable_dir(location):
            last_location = location
            location = os.path.dirname(location)
            if location == last_location:
                # We've traversed up to the root of the filesystem without
                # finding a Python project.
                logger.warning(
                    "Could not find Python project for directory %s (tried all "
                    "parent directories)",
                    orig_location,
                )
                raise RemoteNotFoundError

        url, _rev = cls._get_svn_url_rev(location)
        if url is None:
            raise RemoteNotFoundError

        return url

    @classmethod
    def _get_svn_url_rev(cls, location: str) -> Tuple[Optional[str], int]:
        from pip._internal.exceptions import InstallationError

        entries_path = os.path.join(location, cls.dirname, "entries")
        if os.path.exists(entries_path):
            with open(entries_path) as f:
                data = f.read()
        else:  # subversion >= 1.7 does not have the 'entries' file
            data = ""

        url = None
        if data.startswith("8") or data.startswith("9") or data.startswith("10"):
            entries = list(map(str.splitlines, data.split("\n\x0c\n")))
            del entries[0][0]  # get rid of the '8'
            url = entries[0][3]
            revs = [int(d[9]) for d in entries if len(d) > 9 and d[9]] + [0]
        elif data.startswith("<?xml"):
            match = _svn_xml_url_re.search(data)
            if not match:
                raise ValueError(f"Badly formatted data: {data!r}")
            url = match.group(1)  # get repository URL
            revs = [int(m.group(1)) for m in _svn_rev_re.finditer(data)] + [0]
        else:
            try:
                # subversion >= 1.7
                # Note that using get_remote_call_options is not necessary here
                # because `svn info` is being run against a local directory.
                # We don't need to worry about making sure interactive mode
                # is being used to prompt for passwords, because passwords
                # are only potentially needed for remote server requests.
                xml = cls.run_command(
                    ["info", "--xml", location],
                    show_stdout=False,
                    stdout_only=True,
                )
                match = _svn_info_xml_url_re.search(xml)
                assert match is not None
                url = match.group(1)
                revs = [int(m.group(1)) for m in _svn_info_xml_rev_re.finditer(xml)]
            except InstallationError:
                url, revs = None, []

        if revs:
            rev = max(revs)
        else:
            rev = 0

        return url, rev

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """Always assume the versions don't match"""
        return False

    def __init__(self, use_interactive: Optional[bool] = None) -> None:
        if use_interactive is None:
            use_interactive = is_console_interactive()
        self.use_interactive = use_interactive

        # This member is used to cache the fetched version of the current
        # ``svn`` client.
        # Special value definitions:
        #   None: Not evaluated yet.
        #   Empty tuple: Could not parse version.
        self._vcs_version: Optional[Tuple[int, ...]] = None

        super().__init__()

    def call_vcs_version(self) -> Tuple[int, ...]:
        """Query the version of the currently installed Subversion client.

        :return: A tuple containing the parts of the version information or
            ``()`` if the version returned from ``svn`` could not be parsed.
        :raises: BadCommand: If ``svn`` is not installed.
        """
        # Example versions:
        #   svn, version 1.10.3 (r1842928)
        #      compiled Feb 25 2019, 14:20:39 on x86_64-apple-darwin17.0.0
        #   svn, version 1.7.14 (r1542130)
        #      compiled Mar 28 2018, 08:49:13 on x86_64-pc-linux-gnu
        #   svn, version 1.12.0-SlikSvn (SlikSvn/1.12.0)
        #      compiled May 28 2019, 13:44:56 on x86_64-microsoft-windows6.2
        version_prefix = "svn, version "
        version = self.run_command(["--version"], show_stdout=False, stdout_only=True)
        if not version.startswith(version_prefix):
            return ()

        version = version[len(version_prefix) :].split()[0]
        version_list = version.partition("-")[0].split(".")
        try:
            parsed_version = tuple(map(int, version_list))
        except ValueError:
            return ()

        return parsed_version

    def get_vcs_version(self) -> Tuple[int, ...]:
        """Return the version of the currently installed Subversion client.

        If the version of the Subversion client has already been queried,
        a cached value will be used.

        :return: A tuple containing the parts of the version information or
            ``()`` if the version returned from ``svn`` could not be parsed.
        :raises: BadCommand: If ``svn`` is not installed.
        """
        if self._vcs_version is not None:
            # Use cached version, if available.
            # If parsing the version failed previously (empty tuple),
            # do not attempt to parse it again.
            return self._vcs_version

        vcs_version = self.call_vcs_version()
        self._vcs_version = vcs_version
        return vcs_version

    def get_remote_call_options(self) -> CommandArgs:
        """Return options to be used on calls to Subversion that contact the server.

        These options are applicable for the following ``svn`` subcommands used
        in this class.

            - checkout
            - switch
            - update

        :return: A list of command line arguments to pass to ``svn``.
        """
        if not self.use_interactive:
            # --non-interactive switch is available since Subversion 0.14.4.
            # Subversion < 1.8 runs in interactive mode by default.
            return ["--non-interactive"]

        svn_version = self.get_vcs_version()
        # By default, Subversion >= 1.8 runs in non-interactive mode if
        # stdin is not a TTY. Since that is how pip invokes SVN, in
        # call_subprocess(), pip must pass --force-interactive to ensure
        # the user can be prompted for a password, if required.
        #   SVN added the --force-interactive option in SVN 1.8. Since
        # e.g. RHEL/CentOS 7, which is supported until 2024, ships with
        # SVN 1.7, pip should continue to support SVN 1.7. Therefore, pip
        # can't safely add the option if the SVN version is < 1.8 (or unknown).
        if svn_version >= (1, 8):
            return ["--force-interactive"]

        return []

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info(
            "Checking out %s%s to %s",
            url,
            rev_display,
            display_path(dest),
        )
        if verbosity <= 0:
            flags = ["--quiet"]
        else:
            flags = []
        cmd_args = make_command(
            "checkout",
            *flags,
            self.get_remote_call_options(),
            rev_options.to_args(),
            url,
            dest,
        )
        self.run_command(cmd_args)

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        cmd_args = make_command(
            "switch",
            self.get_remote_call_options(),
            rev_options.to_args(),
            url,
            dest,
        )
        self.run_command(cmd_args)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        cmd_args = make_command(
            "update",
            self.get_remote_call_options(),
            rev_options.to_args(),
            dest,
        )
        self.run_command(cmd_args)


vcs.register(Subversion)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\util.py ===
"""
    pygments.util
    ~~~~~~~~~~~~~

    Utility functions.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from io import TextIOWrapper


split_path_re = re.compile(r'[/\\ ]')
doctype_lookup_re = re.compile(r'''
    <!DOCTYPE\s+(
     [a-zA-Z_][a-zA-Z0-9]*
     (?: \s+      # optional in HTML5
     [a-zA-Z_][a-zA-Z0-9]*\s+
     "[^"]*")?
     )
     [^>]*>
''', re.DOTALL | re.MULTILINE | re.VERBOSE)
tag_re = re.compile(r'<(.+?)(\s.*?)?>.*?</.+?>',
                    re.IGNORECASE | re.DOTALL | re.MULTILINE)
xml_decl_re = re.compile(r'\s*<\?xml[^>]*\?>', re.I)


class ClassNotFound(ValueError):
    """Raised if one of the lookup functions didn't find a matching class."""


class OptionError(Exception):
    """
    This exception will be raised by all option processing functions if
    the type or value of the argument is not correct.
    """

def get_choice_opt(options, optname, allowed, default=None, normcase=False):
    """
    If the key `optname` from the dictionary is not in the sequence
    `allowed`, raise an error, otherwise return it.
    """
    string = options.get(optname, default)
    if normcase:
        string = string.lower()
    if string not in allowed:
        raise OptionError('Value for option {} must be one of {}'.format(optname, ', '.join(map(str, allowed))))
    return string


def get_bool_opt(options, optname, default=None):
    """
    Intuitively, this is `options.get(optname, default)`, but restricted to
    Boolean value. The Booleans can be represented as string, in order to accept
    Boolean value from the command line arguments. If the key `optname` is
    present in the dictionary `options` and is not associated with a Boolean,
    raise an `OptionError`. If it is absent, `default` is returned instead.

    The valid string values for ``True`` are ``1``, ``yes``, ``true`` and
    ``on``, the ones for ``False`` are ``0``, ``no``, ``false`` and ``off``
    (matched case-insensitively).
    """
    string = options.get(optname, default)
    if isinstance(string, bool):
        return string
    elif isinstance(string, int):
        return bool(string)
    elif not isinstance(string, str):
        raise OptionError(f'Invalid type {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')
    elif string.lower() in ('1', 'yes', 'true', 'on'):
        return True
    elif string.lower() in ('0', 'no', 'false', 'off'):
        return False
    else:
        raise OptionError(f'Invalid value {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')


def get_int_opt(options, optname, default=None):
    """As :func:`get_bool_opt`, but interpret the value as an integer."""
    string = options.get(optname, default)
    try:
        return int(string)
    except TypeError:
        raise OptionError(f'Invalid type {string!r} for option {optname}; you '
                          'must give an integer value')
    except ValueError:
        raise OptionError(f'Invalid value {string!r} for option {optname}; you '
                          'must give an integer value')

def get_list_opt(options, optname, default=None):
    """
    If the key `optname` from the dictionary `options` is a string,
    split it at whitespace and return it. If it is already a list
    or a tuple, it is returned as a list.
    """
    val = options.get(optname, default)
    if isinstance(val, str):
        return val.split()
    elif isinstance(val, (list, tuple)):
        return list(val)
    else:
        raise OptionError(f'Invalid type {val!r} for option {optname}; you '
                          'must give a list value')


def docstring_headline(obj):
    if not obj.__doc__:
        return ''
    res = []
    for line in obj.__doc__.strip().splitlines():
        if line.strip():
            res.append(" " + line.strip())
        else:
            break
    return ''.join(res).lstrip()


def make_analysator(f):
    """Return a static text analyser function that returns float values."""
    def text_analyse(text):
        try:
            rv = f(text)
        except Exception:
            return 0.0
        if not rv:
            return 0.0
        try:
            return min(1.0, max(0.0, float(rv)))
        except (ValueError, TypeError):
            return 0.0
    text_analyse.__doc__ = f.__doc__
    return staticmethod(text_analyse)


def shebang_matches(text, regex):
    r"""Check if the given regular expression matches the last part of the
    shebang if one exists.

        >>> from pygments.util import shebang_matches
        >>> shebang_matches('#!/usr/bin/env python', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python2.4', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python-ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/python/ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/startsomethingwith python',
        ...                 r'python(2\.\d)?')
        True

    It also checks for common windows executable file extensions::

        >>> shebang_matches('#!C:\\Python2.4\\Python.exe', r'python(2\.\d)?')
        True

    Parameters (``'-f'`` or ``'--foo'`` are ignored so ``'perl'`` does
    the same as ``'perl -e'``)

    Note that this method automatically searches the whole string (eg:
    the regular expression is wrapped in ``'^$'``)
    """
    index = text.find('\n')
    if index >= 0:
        first_line = text[:index].lower()
    else:
        first_line = text.lower()
    if first_line.startswith('#!'):
        try:
            found = [x for x in split_path_re.split(first_line[2:].strip())
                     if x and not x.startswith('-')][-1]
        except IndexError:
            return False
        regex = re.compile(rf'^{regex}(\.(exe|cmd|bat|bin))?$', re.IGNORECASE)
        if regex.search(found) is not None:
            return True
    return False


def doctype_matches(text, regex):
    """Check if the doctype matches a regular expression (if present).

    Note that this method only checks the first part of a DOCTYPE.
    eg: 'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
    """
    m = doctype_lookup_re.search(text)
    if m is None:
        return False
    doctype = m.group(1)
    return re.compile(regex, re.I).match(doctype.strip()) is not None


def html_doctype_matches(text):
    """Check if the file looks like it has a html doctype."""
    return doctype_matches(text, r'html')


_looks_like_xml_cache = {}


def looks_like_xml(text):
    """Check if a doctype exists or if we have some tags."""
    if xml_decl_re.match(text):
        return True
    key = hash(text)
    try:
        return _looks_like_xml_cache[key]
    except KeyError:
        m = doctype_lookup_re.search(text)
        if m is not None:
            return True
        rv = tag_re.search(text[:1000]) is not None
        _looks_like_xml_cache[key] = rv
        return rv


def surrogatepair(c):
    """Given a unicode character code with length greater than 16 bits,
    return the two 16 bit surrogate pair.
    """
    # From example D28 of:
    # http://www.unicode.org/book/ch03.pdf
    return (0xd7c0 + (c >> 10), (0xdc00 + (c & 0x3ff)))


def format_lines(var_name, seq, raw=False, indent_level=0):
    """Formats a sequence of strings for output."""
    lines = []
    base_indent = ' ' * indent_level * 4
    inner_indent = ' ' * (indent_level + 1) * 4
    lines.append(base_indent + var_name + ' = (')
    if raw:
        # These should be preformatted reprs of, say, tuples.
        for i in seq:
            lines.append(inner_indent + i + ',')
    else:
        for i in seq:
            # Force use of single quotes
            r = repr(i + '"')
            lines.append(inner_indent + r[:-2] + r[-1] + ',')
    lines.append(base_indent + ')')
    return '\n'.join(lines)


def duplicates_removed(it, already_seen=()):
    """
    Returns a list with duplicates removed from the iterable `it`.

    Order is preserved.
    """
    lst = []
    seen = set()
    for i in it:
        if i in seen or i in already_seen:
            continue
        lst.append(i)
        seen.add(i)
    return lst


class Future:
    """Generic class to defer some work.

    Handled specially in RegexLexerMeta, to support regex string construction at
    first use.
    """
    def get(self):
        raise NotImplementedError


def guess_decode(text):
    """Decode *text* with guessed encoding.

    First try UTF-8; this should fail for non-UTF-8 encodings.
    Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    try:
        text = text.decode('utf-8')
        return text, 'utf-8'
    except UnicodeDecodeError:
        try:
            import locale
            prefencoding = locale.getpreferredencoding()
            text = text.decode()
            return text, prefencoding
        except (UnicodeDecodeError, LookupError):
            text = text.decode('latin1')
            return text, 'latin1'


def guess_decode_from_terminal(text, term):
    """Decode *text* coming from terminal *term*.

    First try the terminal encoding, if given.
    Then try UTF-8.  Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    if getattr(term, 'encoding', None):
        try:
            text = text.decode(term.encoding)
        except UnicodeDecodeError:
            pass
        else:
            return text, term.encoding
    return guess_decode(text)


def terminal_encoding(term):
    """Return our best guess of encoding for the given *term*."""
    if getattr(term, 'encoding', None):
        return term.encoding
    import locale
    return locale.getpreferredencoding()


class UnclosingTextIOWrapper(TextIOWrapper):
    # Don't close underlying buffer on destruction.
    def close(self):
        self.flush()

# === NexusCore/openenv\Lib\site-packages\fsspec\callbacks.py ===
from functools import wraps


class Callback:
    """
    Base class and interface for callback mechanism

    This class can be used directly for monitoring file transfers by
    providing ``callback=Callback(hooks=...)`` (see the ``hooks`` argument,
    below), or subclassed for more specialised behaviour.

    Parameters
    ----------
    size: int (optional)
        Nominal quantity for the value that corresponds to a complete
        transfer, e.g., total number of tiles or total number of
        bytes
    value: int (0)
        Starting internal counter value
    hooks: dict or None
        A dict of named functions to be called on each update. The signature
        of these must be ``f(size, value, **kwargs)``
    """

    def __init__(self, size=None, value=0, hooks=None, **kwargs):
        self.size = size
        self.value = value
        self.hooks = hooks or {}
        self.kw = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc_args):
        self.close()

    def close(self):
        """Close callback."""

    def branched(self, path_1, path_2, **kwargs):
        """
        Return callback for child transfers

        If this callback is operating at a higher level, e.g., put, which may
        trigger transfers that can also be monitored. The function returns a callback
        that has to be passed to the child method, e.g., put_file,
        as `callback=` argument.

        The implementation uses `callback.branch` for compatibility.
        When implementing callbacks, it is recommended to override this function instead
        of `branch` and avoid calling `super().branched(...)`.

        Prefer using this function over `branch`.

        Parameters
        ----------
        path_1: str
            Child's source path
        path_2: str
            Child's destination path
        **kwargs:
            Arbitrary keyword arguments

        Returns
        -------
        callback: Callback
            A callback instance to be passed to the child method
        """
        self.branch(path_1, path_2, kwargs)
        # mutate kwargs so that we can force the caller to pass "callback=" explicitly
        return kwargs.pop("callback", DEFAULT_CALLBACK)

    def branch_coro(self, fn):
        """
        Wraps a coroutine, and pass a new child callback to it.
        """

        @wraps(fn)
        async def func(path1, path2: str, **kwargs):
            with self.branched(path1, path2, **kwargs) as child:
                return await fn(path1, path2, callback=child, **kwargs)

        return func

    def set_size(self, size):
        """
        Set the internal maximum size attribute

        Usually called if not initially set at instantiation. Note that this
        triggers a ``call()``.

        Parameters
        ----------
        size: int
        """
        self.size = size
        self.call()

    def absolute_update(self, value):
        """
        Set the internal value state

        Triggers ``call()``

        Parameters
        ----------
        value: int
        """
        self.value = value
        self.call()

    def relative_update(self, inc=1):
        """
        Delta increment the internal counter

        Triggers ``call()``

        Parameters
        ----------
        inc: int
        """
        self.value += inc
        self.call()

    def call(self, hook_name=None, **kwargs):
        """
        Execute hook(s) with current state

        Each function is passed the internal size and current value

        Parameters
        ----------
        hook_name: str or None
            If given, execute on this hook
        kwargs: passed on to (all) hook(s)
        """
        if not self.hooks:
            return
        kw = self.kw.copy()
        kw.update(kwargs)
        if hook_name:
            if hook_name not in self.hooks:
                return
            return self.hooks[hook_name](self.size, self.value, **kw)
        for hook in self.hooks.values() or []:
            hook(self.size, self.value, **kw)

    def wrap(self, iterable):
        """
        Wrap an iterable to call ``relative_update`` on each iterations

        Parameters
        ----------
        iterable: Iterable
            The iterable that is being wrapped
        """
        for item in iterable:
            self.relative_update()
            yield item

    def branch(self, path_1, path_2, kwargs):
        """
        Set callbacks for child transfers

        If this callback is operating at a higher level, e.g., put, which may
        trigger transfers that can also be monitored. The passed kwargs are
        to be *mutated* to add ``callback=``, if this class supports branching
        to children.

        Parameters
        ----------
        path_1: str
            Child's source path
        path_2: str
            Child's destination path
        kwargs: dict
            arguments passed to child method, e.g., put_file.

        Returns
        -------

        """
        return None

    def no_op(self, *_, **__):
        pass

    def __getattr__(self, item):
        """
        If undefined methods are called on this class, nothing happens
        """
        return self.no_op

    @classmethod
    def as_callback(cls, maybe_callback=None):
        """Transform callback=... into Callback instance

        For the special value of ``None``, return the global instance of
        ``NoOpCallback``. This is an alternative to including
        ``callback=DEFAULT_CALLBACK`` directly in a method signature.
        """
        if maybe_callback is None:
            return DEFAULT_CALLBACK
        return maybe_callback


class NoOpCallback(Callback):
    """
    This implementation of Callback does exactly nothing
    """

    def call(self, *args, **kwargs):
        return None


class DotPrinterCallback(Callback):
    """
    Simple example Callback implementation

    Almost identical to Callback with a hook that prints a char; here we
    demonstrate how the outer layer may print "#" and the inner layer "."
    """

    def __init__(self, chr_to_print="#", **kwargs):
        self.chr = chr_to_print
        super().__init__(**kwargs)

    def branch(self, path_1, path_2, kwargs):
        """Mutate kwargs to add new instance with different print char"""
        kwargs["callback"] = DotPrinterCallback(".")

    def call(self, **kwargs):
        """Just outputs a character"""
        print(self.chr, end="")


class TqdmCallback(Callback):
    """
    A callback to display a progress bar using tqdm

    Parameters
    ----------
    tqdm_kwargs : dict, (optional)
        Any argument accepted by the tqdm constructor.
        See the `tqdm doc <https://tqdm.github.io/docs/tqdm/#__init__>`_.
        Will be forwarded to `tqdm_cls`.
    tqdm_cls: (optional)
        subclass of `tqdm.tqdm`. If not passed, it will default to `tqdm.tqdm`.

    Examples
    --------
    >>> import fsspec
    >>> from fsspec.callbacks import TqdmCallback
    >>> fs = fsspec.filesystem("memory")
    >>> path2distant_data = "/your-path"
    >>> fs.upload(
            ".",
            path2distant_data,
            recursive=True,
            callback=TqdmCallback(),
        )

    You can forward args to tqdm using the ``tqdm_kwargs`` parameter.

    >>> fs.upload(
            ".",
            path2distant_data,
            recursive=True,
            callback=TqdmCallback(tqdm_kwargs={"desc": "Your tqdm description"}),
        )

    You can also customize the progress bar by passing a subclass of `tqdm`.

    .. code-block:: python

        class TqdmFormat(tqdm):
            '''Provides a `total_time` format parameter'''
            @property
            def format_dict(self):
                d = super().format_dict
                total_time = d["elapsed"] * (d["total"] or 0) / max(d["n"], 1)
                d.update(total_time=self.format_interval(total_time) + " in total")
                return d

    >>> with TqdmCallback(
            tqdm_kwargs={
                "desc": "desc",
                "bar_format": "{total_time}: {percentage:.0f}%|{bar}{r_bar}",
            },
            tqdm_cls=TqdmFormat,
        ) as callback:
            fs.upload(".", path2distant_data, recursive=True, callback=callback)
    """

    def __init__(self, tqdm_kwargs=None, *args, **kwargs):
        try:
            from tqdm import tqdm

        except ImportError as exce:
            raise ImportError(
                "Using TqdmCallback requires tqdm to be installed"
            ) from exce

        self._tqdm_cls = kwargs.pop("tqdm_cls", tqdm)
        self._tqdm_kwargs = tqdm_kwargs or {}
        self.tqdm = None
        super().__init__(*args, **kwargs)

    def call(self, *args, **kwargs):
        if self.tqdm is None:
            self.tqdm = self._tqdm_cls(total=self.size, **self._tqdm_kwargs)
        self.tqdm.total = self.size
        self.tqdm.update(self.value - self.tqdm.n)

    def close(self):
        if self.tqdm is not None:
            self.tqdm.close()
            self.tqdm = None

    def __del__(self):
        return self.close()


DEFAULT_CALLBACK = _DEFAULT_CALLBACK = NoOpCallback()

# === NexusCore/openenv\Lib\site-packages\fsspec\fuse.py ===
import argparse
import logging
import os
import stat
import threading
import time
from errno import EIO, ENOENT

from fuse import FUSE, FuseOSError, LoggingMixIn, Operations

from fsspec import __version__
from fsspec.core import url_to_fs

logger = logging.getLogger("fsspec.fuse")


class FUSEr(Operations):
    def __init__(self, fs, path, ready_file=False):
        self.fs = fs
        self.cache = {}
        self.root = path.rstrip("/") + "/"
        self.counter = 0
        logger.info("Starting FUSE at %s", path)
        self._ready_file = ready_file

    def getattr(self, path, fh=None):
        logger.debug("getattr %s", path)
        if self._ready_file and path in ["/.fuse_ready", ".fuse_ready"]:
            return {"type": "file", "st_size": 5}

        path = "".join([self.root, path.lstrip("/")]).rstrip("/")
        try:
            info = self.fs.info(path)
        except FileNotFoundError as exc:
            raise FuseOSError(ENOENT) from exc

        data = {"st_uid": info.get("uid", 1000), "st_gid": info.get("gid", 1000)}
        perm = info.get("mode", 0o777)

        if info["type"] != "file":
            data["st_mode"] = stat.S_IFDIR | perm
            data["st_size"] = 0
            data["st_blksize"] = 0
        else:
            data["st_mode"] = stat.S_IFREG | perm
            data["st_size"] = info["size"]
            data["st_blksize"] = 5 * 2**20
            data["st_nlink"] = 1
        data["st_atime"] = info["atime"] if "atime" in info else time.time()
        data["st_ctime"] = info["ctime"] if "ctime" in info else time.time()
        data["st_mtime"] = info["mtime"] if "mtime" in info else time.time()
        return data

    def readdir(self, path, fh):
        logger.debug("readdir %s", path)
        path = "".join([self.root, path.lstrip("/")])
        files = self.fs.ls(path, False)
        files = [os.path.basename(f.rstrip("/")) for f in files]
        return [".", ".."] + files

    def mkdir(self, path, mode):
        path = "".join([self.root, path.lstrip("/")])
        self.fs.mkdir(path)
        return 0

    def rmdir(self, path):
        path = "".join([self.root, path.lstrip("/")])
        self.fs.rmdir(path)
        return 0

    def read(self, path, size, offset, fh):
        logger.debug("read %s", (path, size, offset))
        if self._ready_file and path in ["/.fuse_ready", ".fuse_ready"]:
            # status indicator
            return b"ready"

        f = self.cache[fh]
        f.seek(offset)
        out = f.read(size)
        return out

    def write(self, path, data, offset, fh):
        logger.debug("write %s", (path, offset))
        f = self.cache[fh]
        f.seek(offset)
        f.write(data)
        return len(data)

    def create(self, path, flags, fi=None):
        logger.debug("create %s", (path, flags))
        fn = "".join([self.root, path.lstrip("/")])
        self.fs.touch(fn)  # OS will want to get attributes immediately
        f = self.fs.open(fn, "wb")
        self.cache[self.counter] = f
        self.counter += 1
        return self.counter - 1

    def open(self, path, flags):
        logger.debug("open %s", (path, flags))
        fn = "".join([self.root, path.lstrip("/")])
        if flags % 2 == 0:
            # read
            mode = "rb"
        else:
            # write/create
            mode = "wb"
        self.cache[self.counter] = self.fs.open(fn, mode)
        self.counter += 1
        return self.counter - 1

    def truncate(self, path, length, fh=None):
        fn = "".join([self.root, path.lstrip("/")])
        if length != 0:
            raise NotImplementedError
        # maybe should be no-op since open with write sets size to zero anyway
        self.fs.touch(fn)

    def unlink(self, path):
        fn = "".join([self.root, path.lstrip("/")])
        try:
            self.fs.rm(fn, False)
        except (OSError, FileNotFoundError) as exc:
            raise FuseOSError(EIO) from exc

    def release(self, path, fh):
        try:
            if fh in self.cache:
                f = self.cache[fh]
                f.close()
                self.cache.pop(fh)
        except Exception as e:
            print(e)
        return 0

    def chmod(self, path, mode):
        if hasattr(self.fs, "chmod"):
            path = "".join([self.root, path.lstrip("/")])
            return self.fs.chmod(path, mode)
        raise NotImplementedError


def run(
    fs,
    path,
    mount_point,
    foreground=True,
    threads=False,
    ready_file=False,
    ops_class=FUSEr,
):
    """Mount stuff in a local directory

    This uses fusepy to make it appear as if a given path on an fsspec
    instance is in fact resident within the local file-system.

    This requires that fusepy by installed, and that FUSE be available on
    the system (typically requiring a package to be installed with
    apt, yum, brew, etc.).

    Parameters
    ----------
    fs: file-system instance
        From one of the compatible implementations
    path: str
        Location on that file-system to regard as the root directory to
        mount. Note that you typically should include the terminating "/"
        character.
    mount_point: str
        An empty directory on the local file-system where the contents of
        the remote path will appear.
    foreground: bool
        Whether or not calling this function will block. Operation will
        typically be more stable if True.
    threads: bool
        Whether or not to create threads when responding to file operations
        within the mounter directory. Operation will typically be more
        stable if False.
    ready_file: bool
        Whether the FUSE process is ready. The ``.fuse_ready`` file will
        exist in the ``mount_point`` directory if True. Debugging purpose.
    ops_class: FUSEr or Subclass of FUSEr
        To override the default behavior of FUSEr. For Example, logging
        to file.

    """
    func = lambda: FUSE(
        ops_class(fs, path, ready_file=ready_file),
        mount_point,
        nothreads=not threads,
        foreground=foreground,
    )
    if not foreground:
        th = threading.Thread(target=func)
        th.daemon = True
        th.start()
        return th
    else:  # pragma: no cover
        try:
            func()
        except KeyboardInterrupt:
            pass


def main(args):
    """Mount filesystem from chained URL to MOUNT_POINT.

    Examples:

    python3 -m fsspec.fuse memory /usr/share /tmp/mem

    python3 -m fsspec.fuse local /tmp/source /tmp/local \\
            -l /tmp/fsspecfuse.log

    You can also mount chained-URLs and use special settings:

    python3 -m fsspec.fuse 'filecache::zip::file://data.zip' \\
            / /tmp/zip \\
            -o 'filecache-cache_storage=/tmp/simplecache'

    You can specify the type of the setting by using `[int]` or `[bool]`,
    (`true`, `yes`, `1` represents the Boolean value `True`):

    python3 -m fsspec.fuse 'simplecache::ftp://ftp1.at.proftpd.org' \\
            /historic/packages/RPMS /tmp/ftp \\
            -o 'simplecache-cache_storage=/tmp/simplecache' \\
            -o 'simplecache-check_files=false[bool]' \\
            -o 'ftp-listings_expiry_time=60[int]' \\
            -o 'ftp-username=anonymous' \\
            -o 'ftp-password=xieyanbo'
    """

    class RawDescriptionArgumentParser(argparse.ArgumentParser):
        def format_help(self):
            usage = super().format_help()
            parts = usage.split("\n\n")
            parts[1] = self.description.rstrip()
            return "\n\n".join(parts)

    parser = RawDescriptionArgumentParser(prog="fsspec.fuse", description=main.__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("url", type=str, help="fs url")
    parser.add_argument("source_path", type=str, help="source directory in fs")
    parser.add_argument("mount_point", type=str, help="local directory")
    parser.add_argument(
        "-o",
        "--option",
        action="append",
        help="Any options of protocol included in the chained URL",
    )
    parser.add_argument(
        "-l", "--log-file", type=str, help="Logging FUSE debug info (Default: '')"
    )
    parser.add_argument(
        "-f",
        "--foreground",
        action="store_false",
        help="Running in foreground or not (Default: False)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        action="store_false",
        help="Running with threads support (Default: False)",
    )
    parser.add_argument(
        "-r",
        "--ready-file",
        action="store_false",
        help="The `.fuse_ready` file will exist after FUSE is ready. "
        "(Debugging purpose, Default: False)",
    )
    args = parser.parse_args(args)

    kwargs = {}
    for item in args.option or []:
        key, sep, value = item.partition("=")
        if not sep:
            parser.error(message=f"Wrong option: {item!r}")
        val = value.lower()
        if val.endswith("[int]"):
            value = int(value[: -len("[int]")])
        elif val.endswith("[bool]"):
            value = val[: -len("[bool]")] in ["1", "yes", "true"]

        if "-" in key:
            fs_name, setting_name = key.split("-", 1)
            if fs_name in kwargs:
                kwargs[fs_name][setting_name] = value
            else:
                kwargs[fs_name] = {setting_name: value}
        else:
            kwargs[key] = value

    if args.log_file:
        logging.basicConfig(
            level=logging.DEBUG,
            filename=args.log_file,
            format="%(asctime)s %(message)s",
        )

        class LoggingFUSEr(FUSEr, LoggingMixIn):
            pass

        fuser = LoggingFUSEr
    else:
        fuser = FUSEr

    fs, url_path = url_to_fs(args.url, **kwargs)
    logger.debug("Mounting %s to %s", url_path, str(args.mount_point))
    run(
        fs,
        args.source_path,
        args.mount_point,
        foreground=args.foreground,
        threads=args.threads,
        ready_file=args.ready_file,
        ops_class=fuser,
    )


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])

# === NexusCore/openenv\Lib\site-packages\pygments\util.py ===
"""
    pygments.util
    ~~~~~~~~~~~~~

    Utility functions.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from io import TextIOWrapper


split_path_re = re.compile(r'[/\\ ]')
doctype_lookup_re = re.compile(r'''
    <!DOCTYPE\s+(
     [a-zA-Z_][a-zA-Z0-9]*
     (?: \s+      # optional in HTML5
     [a-zA-Z_][a-zA-Z0-9]*\s+
     "[^"]*")?
     )
     [^>]*>
''', re.DOTALL | re.MULTILINE | re.VERBOSE)
tag_re = re.compile(r'<(.+?)(\s.*?)?>.*?</.+?>',
                    re.IGNORECASE | re.DOTALL | re.MULTILINE)
xml_decl_re = re.compile(r'\s*<\?xml[^>]*\?>', re.I)


class ClassNotFound(ValueError):
    """Raised if one of the lookup functions didn't find a matching class."""


class OptionError(Exception):
    """
    This exception will be raised by all option processing functions if
    the type or value of the argument is not correct.
    """

def get_choice_opt(options, optname, allowed, default=None, normcase=False):
    """
    If the key `optname` from the dictionary is not in the sequence
    `allowed`, raise an error, otherwise return it.
    """
    string = options.get(optname, default)
    if normcase:
        string = string.lower()
    if string not in allowed:
        raise OptionError('Value for option {} must be one of {}'.format(optname, ', '.join(map(str, allowed))))
    return string


def get_bool_opt(options, optname, default=None):
    """
    Intuitively, this is `options.get(optname, default)`, but restricted to
    Boolean value. The Booleans can be represented as string, in order to accept
    Boolean value from the command line arguments. If the key `optname` is
    present in the dictionary `options` and is not associated with a Boolean,
    raise an `OptionError`. If it is absent, `default` is returned instead.

    The valid string values for ``True`` are ``1``, ``yes``, ``true`` and
    ``on``, the ones for ``False`` are ``0``, ``no``, ``false`` and ``off``
    (matched case-insensitively).
    """
    string = options.get(optname, default)
    if isinstance(string, bool):
        return string
    elif isinstance(string, int):
        return bool(string)
    elif not isinstance(string, str):
        raise OptionError(f'Invalid type {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')
    elif string.lower() in ('1', 'yes', 'true', 'on'):
        return True
    elif string.lower() in ('0', 'no', 'false', 'off'):
        return False
    else:
        raise OptionError(f'Invalid value {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')


def get_int_opt(options, optname, default=None):
    """As :func:`get_bool_opt`, but interpret the value as an integer."""
    string = options.get(optname, default)
    try:
        return int(string)
    except TypeError:
        raise OptionError(f'Invalid type {string!r} for option {optname}; you '
                          'must give an integer value')
    except ValueError:
        raise OptionError(f'Invalid value {string!r} for option {optname}; you '
                          'must give an integer value')

def get_list_opt(options, optname, default=None):
    """
    If the key `optname` from the dictionary `options` is a string,
    split it at whitespace and return it. If it is already a list
    or a tuple, it is returned as a list.
    """
    val = options.get(optname, default)
    if isinstance(val, str):
        return val.split()
    elif isinstance(val, (list, tuple)):
        return list(val)
    else:
        raise OptionError(f'Invalid type {val!r} for option {optname}; you '
                          'must give a list value')


def docstring_headline(obj):
    if not obj.__doc__:
        return ''
    res = []
    for line in obj.__doc__.strip().splitlines():
        if line.strip():
            res.append(" " + line.strip())
        else:
            break
    return ''.join(res).lstrip()


def make_analysator(f):
    """Return a static text analyser function that returns float values."""
    def text_analyse(text):
        try:
            rv = f(text)
        except Exception:
            return 0.0
        if not rv:
            return 0.0
        try:
            return min(1.0, max(0.0, float(rv)))
        except (ValueError, TypeError):
            return 0.0
    text_analyse.__doc__ = f.__doc__
    return staticmethod(text_analyse)


def shebang_matches(text, regex):
    r"""Check if the given regular expression matches the last part of the
    shebang if one exists.

        >>> from pygments.util import shebang_matches
        >>> shebang_matches('#!/usr/bin/env python', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python2.4', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python-ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/python/ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/startsomethingwith python',
        ...                 r'python(2\.\d)?')
        True

    It also checks for common windows executable file extensions::

        >>> shebang_matches('#!C:\\Python2.4\\Python.exe', r'python(2\.\d)?')
        True

    Parameters (``'-f'`` or ``'--foo'`` are ignored so ``'perl'`` does
    the same as ``'perl -e'``)

    Note that this method automatically searches the whole string (eg:
    the regular expression is wrapped in ``'^$'``)
    """
    index = text.find('\n')
    if index >= 0:
        first_line = text[:index].lower()
    else:
        first_line = text.lower()
    if first_line.startswith('#!'):
        try:
            found = [x for x in split_path_re.split(first_line[2:].strip())
                     if x and not x.startswith('-')][-1]
        except IndexError:
            return False
        regex = re.compile(rf'^{regex}(\.(exe|cmd|bat|bin))?$', re.IGNORECASE)
        if regex.search(found) is not None:
            return True
    return False


def doctype_matches(text, regex):
    """Check if the doctype matches a regular expression (if present).

    Note that this method only checks the first part of a DOCTYPE.
    eg: 'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
    """
    m = doctype_lookup_re.search(text)
    if m is None:
        return False
    doctype = m.group(1)
    return re.compile(regex, re.I).match(doctype.strip()) is not None


def html_doctype_matches(text):
    """Check if the file looks like it has a html doctype."""
    return doctype_matches(text, r'html')


_looks_like_xml_cache = {}


def looks_like_xml(text):
    """Check if a doctype exists or if we have some tags."""
    if xml_decl_re.match(text):
        return True
    key = hash(text)
    try:
        return _looks_like_xml_cache[key]
    except KeyError:
        m = doctype_lookup_re.search(text)
        if m is not None:
            return True
        rv = tag_re.search(text[:1000]) is not None
        _looks_like_xml_cache[key] = rv
        return rv


def surrogatepair(c):
    """Given a unicode character code with length greater than 16 bits,
    return the two 16 bit surrogate pair.
    """
    # From example D28 of:
    # http://www.unicode.org/book/ch03.pdf
    return (0xd7c0 + (c >> 10), (0xdc00 + (c & 0x3ff)))


def format_lines(var_name, seq, raw=False, indent_level=0):
    """Formats a sequence of strings for output."""
    lines = []
    base_indent = ' ' * indent_level * 4
    inner_indent = ' ' * (indent_level + 1) * 4
    lines.append(base_indent + var_name + ' = (')
    if raw:
        # These should be preformatted reprs of, say, tuples.
        for i in seq:
            lines.append(inner_indent + i + ',')
    else:
        for i in seq:
            # Force use of single quotes
            r = repr(i + '"')
            lines.append(inner_indent + r[:-2] + r[-1] + ',')
    lines.append(base_indent + ')')
    return '\n'.join(lines)


def duplicates_removed(it, already_seen=()):
    """
    Returns a list with duplicates removed from the iterable `it`.

    Order is preserved.
    """
    lst = []
    seen = set()
    for i in it:
        if i in seen or i in already_seen:
            continue
        lst.append(i)
        seen.add(i)
    return lst


class Future:
    """Generic class to defer some work.

    Handled specially in RegexLexerMeta, to support regex string construction at
    first use.
    """
    def get(self):
        raise NotImplementedError


def guess_decode(text):
    """Decode *text* with guessed encoding.

    First try UTF-8; this should fail for non-UTF-8 encodings.
    Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    try:
        text = text.decode('utf-8')
        return text, 'utf-8'
    except UnicodeDecodeError:
        try:
            import locale
            prefencoding = locale.getpreferredencoding()
            text = text.decode()
            return text, prefencoding
        except (UnicodeDecodeError, LookupError):
            text = text.decode('latin1')
            return text, 'latin1'


def guess_decode_from_terminal(text, term):
    """Decode *text* coming from terminal *term*.

    First try the terminal encoding, if given.
    Then try UTF-8.  Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    if getattr(term, 'encoding', None):
        try:
            text = text.decode(term.encoding)
        except UnicodeDecodeError:
            pass
        else:
            return text, term.encoding
    return guess_decode(text)


def terminal_encoding(term):
    """Return our best guess of encoding for the given *term*."""
    if getattr(term, 'encoding', None):
        return term.encoding
    import locale
    return locale.getpreferredencoding()


class UnclosingTextIOWrapper(TextIOWrapper):
    # Don't close underlying buffer on destruction.
    def close(self):
        self.flush()

# === NexusCore/openenv\Lib\site-packages\tqdm\cli.py ===
"""
Module version for monitoring CLI pipes (`... | python -m tqdm | ...`).
"""
import logging
import re
import sys
from ast import literal_eval as numeric
from textwrap import indent

from .std import TqdmKeyError, TqdmTypeError, tqdm
from .version import __version__

__all__ = ["main"]
log = logging.getLogger(__name__)


def cast(val, typ):
    log.debug((val, typ))
    if " or " in typ:
        for t in typ.split(" or "):
            try:
                return cast(val, t)
            except TqdmTypeError:
                pass
        raise TqdmTypeError(f"{val} : {typ}")

    # sys.stderr.write('\ndebug | `val:type`: `' + val + ':' + typ + '`.\n')
    if typ == 'bool':
        if (val == 'True') or (val == ''):
            return True
        if val == 'False':
            return False
        raise TqdmTypeError(val + ' : ' + typ)
    if typ == 'chr':
        if len(val) == 1:
            return val.encode()
        if re.match(r"^\\\w+$", val):
            return eval(f'"{val}"').encode()
        raise TqdmTypeError(f"{val} : {typ}")
    if typ == 'str':
        return val
    if typ == 'int':
        try:
            return int(val)
        except ValueError as exc:
            raise TqdmTypeError(f"{val} : {typ}") from exc
    if typ == 'float':
        try:
            return float(val)
        except ValueError as exc:
            raise TqdmTypeError(f"{val} : {typ}") from exc
    raise TqdmTypeError(f"{val} : {typ}")


def posix_pipe(fin, fout, delim=b'\\n', buf_size=256,
               callback=lambda float: None, callback_len=True):
    """
    Params
    ------
    fin  : binary file with `read(buf_size : int)` method
    fout  : binary file with `write` (and optionally `flush`) methods.
    callback  : function(float), e.g.: `tqdm.update`
    callback_len  : If (default: True) do `callback(len(buffer))`.
      Otherwise, do `callback(data) for data in buffer.split(delim)`.
    """
    fp_write = fout.write

    if not delim:
        while True:
            tmp = fin.read(buf_size)

            # flush at EOF
            if not tmp:
                getattr(fout, 'flush', lambda: None)()
                return

            fp_write(tmp)
            callback(len(tmp))
        # return

    buf = b''
    len_delim = len(delim)
    # n = 0
    while True:
        tmp = fin.read(buf_size)

        # flush at EOF
        if not tmp:
            if buf:
                fp_write(buf)
                if callback_len:
                    # n += 1 + buf.count(delim)
                    callback(1 + buf.count(delim))
                else:
                    for i in buf.split(delim):
                        callback(i)
            getattr(fout, 'flush', lambda: None)()
            return  # n

        while True:
            i = tmp.find(delim)
            if i < 0:
                buf += tmp
                break
            fp_write(buf + tmp[:i + len(delim)])
            # n += 1
            callback(1 if callback_len else (buf + tmp[:i]))
            buf = b''
            tmp = tmp[i + len_delim:]


# ((opt, type), ... )
RE_OPTS = re.compile(r'\n {4}(\S+)\s{2,}:\s*([^,]+)')
# better split method assuming no positional args
RE_SHLEX = re.compile(r'\s*(?<!\S)--?([^\s=]+)(\s+|=|$)')

# TODO: add custom support for some of the following?
UNSUPPORTED_OPTS = ('iterable', 'gui', 'out', 'file')

# The 8 leading spaces are required for consistency
CLI_EXTRA_DOC = r"""
    Extra CLI Options
    -----------------
    name  : type, optional
        TODO: find out why this is needed.
    delim  : chr, optional
        Delimiting character [default: '\n']. Use '\0' for null.
        N.B.: on Windows systems, Python converts '\n' to '\r\n'.
    buf_size  : int, optional
        String buffer size in bytes [default: 256]
        used when `delim` is specified.
    bytes  : bool, optional
        If true, will count bytes, ignore `delim`, and default
        `unit_scale` to True, `unit_divisor` to 1024, and `unit` to 'B'.
    tee  : bool, optional
        If true, passes `stdin` to both `stderr` and `stdout`.
    update  : bool, optional
        If true, will treat input as newly elapsed iterations,
        i.e. numbers to pass to `update()`. Note that this is slow
        (~2e5 it/s) since every input must be decoded as a number.
    update_to  : bool, optional
        If true, will treat input as total elapsed iterations,
        i.e. numbers to assign to `self.n`. Note that this is slow
        (~2e5 it/s) since every input must be decoded as a number.
    null  : bool, optional
        If true, will discard input (no stdout).
    manpath  : str, optional
        Directory in which to install tqdm man pages.
    comppath  : str, optional
        Directory in which to place tqdm completion.
    log  : str, optional
        CRITICAL|FATAL|ERROR|WARN(ING)|[default: 'INFO']|DEBUG|NOTSET.
"""


def main(fp=sys.stderr, argv=None):
    """
    Parameters (internal use only)
    ---------
    fp  : file-like object for tqdm
    argv  : list (default: sys.argv[1:])
    """
    if argv is None:
        argv = sys.argv[1:]
    try:
        log_idx = argv.index('--log')
    except ValueError:
        for i in argv:
            if i.startswith('--log='):
                logLevel = i[len('--log='):]
                break
        else:
            logLevel = 'INFO'
    else:
        # argv.pop(log_idx)
        # logLevel = argv.pop(log_idx)
        logLevel = argv[log_idx + 1]
    logging.basicConfig(level=getattr(logging, logLevel),
                        format="%(levelname)s:%(module)s:%(lineno)d:%(message)s")

    # py<3.13 doesn't dedent docstrings
    d = (tqdm.__doc__ if sys.version_info < (3, 13)
         else indent(tqdm.__doc__, "    ")) + CLI_EXTRA_DOC

    opt_types = dict(RE_OPTS.findall(d))
    # opt_types['delim'] = 'chr'

    for o in UNSUPPORTED_OPTS:
        opt_types.pop(o)

    log.debug(sorted(opt_types.items()))

    # d = RE_OPTS.sub(r'  --\1=<\1>  : \2', d)
    split = RE_OPTS.split(d)
    opt_types_desc = zip(split[1::3], split[2::3], split[3::3])
    d = ''.join(('\n  --{0}  : {2}{3}' if otd[1] == 'bool' else
                 '\n  --{0}=<{1}>  : {2}{3}').format(
                     otd[0].replace('_', '-'), otd[0], *otd[1:])
                for otd in opt_types_desc if otd[0] not in UNSUPPORTED_OPTS)

    help_short = "Usage:\n  tqdm [--help | options]\n"
    d = help_short + """
Options:
  -h, --help     Print this help and exit.
  -v, --version  Print version and exit.
""" + d.strip('\n') + '\n'

    # opts = docopt(d, version=__version__)
    if any(v in argv for v in ('-v', '--version')):
        sys.stdout.write(__version__ + '\n')
        sys.exit(0)
    elif any(v in argv for v in ('-h', '--help')):
        sys.stdout.write(d + '\n')
        sys.exit(0)
    elif argv and argv[0][:2] != '--':
        sys.stderr.write(f"Error:Unknown argument:{argv[0]}\n{help_short}")

    argv = RE_SHLEX.split(' '.join(["tqdm"] + argv))
    opts = dict(zip(argv[1::3], argv[3::3]))

    log.debug(opts)
    opts.pop('log', True)

    tqdm_args = {'file': fp}
    try:
        for (o, v) in opts.items():
            o = o.replace('-', '_')
            try:
                tqdm_args[o] = cast(v, opt_types[o])
            except KeyError as e:
                raise TqdmKeyError(str(e))
        log.debug('args:' + str(tqdm_args))

        delim_per_char = tqdm_args.pop('bytes', False)
        update = tqdm_args.pop('update', False)
        update_to = tqdm_args.pop('update_to', False)
        if sum((delim_per_char, update, update_to)) > 1:
            raise TqdmKeyError("Can only have one of --bytes --update --update_to")
    except Exception:
        fp.write("\nError:\n" + help_short)
        stdin, stdout_write = sys.stdin, sys.stdout.write
        for i in stdin:
            stdout_write(i)
        raise
    else:
        buf_size = tqdm_args.pop('buf_size', 256)
        delim = tqdm_args.pop('delim', b'\\n')
        tee = tqdm_args.pop('tee', False)
        manpath = tqdm_args.pop('manpath', None)
        comppath = tqdm_args.pop('comppath', None)
        if tqdm_args.pop('null', False):
            class stdout(object):
                @staticmethod
                def write(_):
                    pass
        else:
            stdout = sys.stdout
            stdout = getattr(stdout, 'buffer', stdout)
        stdin = getattr(sys.stdin, 'buffer', sys.stdin)
        if manpath or comppath:
            try:  # py<3.9
                import importlib_resources as resources
            except ImportError:
                from importlib import resources
            from pathlib import Path

            def cp(name, dst):
                """copy resource `name` to `dst`"""
                fi = resources.files('tqdm') / name
                dst.write_bytes(fi.read_bytes())
                log.info("written:%s", dst)
            if manpath is not None:
                cp('tqdm.1', Path(manpath) / 'tqdm.1')
            if comppath is not None:
                cp('completion.sh', Path(comppath) / 'tqdm_completion.sh')
            sys.exit(0)
        if tee:
            stdout_write = stdout.write
            fp_write = getattr(fp, 'buffer', fp).write

            class stdout(object):  # pylint: disable=function-redefined
                @staticmethod
                def write(x):
                    with tqdm.external_write_mode(file=fp):
                        fp_write(x)
                    stdout_write(x)
        if delim_per_char:
            tqdm_args.setdefault('unit', 'B')
            tqdm_args.setdefault('unit_scale', True)
            tqdm_args.setdefault('unit_divisor', 1024)
            log.debug(tqdm_args)
            with tqdm(**tqdm_args) as t:
                posix_pipe(stdin, stdout, '', buf_size, t.update)
        elif delim == b'\\n':
            log.debug(tqdm_args)
            write = stdout.write
            if update or update_to:
                with tqdm(**tqdm_args) as t:
                    if update:
                        def callback(i):
                            t.update(numeric(i.decode()))
                    else:  # update_to
                        def callback(i):
                            t.update(numeric(i.decode()) - t.n)
                    for i in stdin:
                        write(i)
                        callback(i)
            else:
                for i in tqdm(stdin, **tqdm_args):
                    write(i)
        else:
            log.debug(tqdm_args)
            with tqdm(**tqdm_args) as t:
                callback_len = False
                if update:
                    def callback(i):
                        t.update(numeric(i.decode()))
                elif update_to:
                    def callback(i):
                        t.update(numeric(i.decode()) - t.n)
                else:
                    callback = t.update
                    callback_len = True
                posix_pipe(stdin, stdout, delim, buf_size, callback, callback_len)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\vcs\subversion.py ===
import logging
import os
import re
from typing import List, Optional, Tuple

from pip._internal.utils.misc import (
    HiddenText,
    display_path,
    is_console_interactive,
    is_installable_dir,
    split_auth_from_netloc,
)
from pip._internal.utils.subprocess import CommandArgs, make_command
from pip._internal.vcs.versioncontrol import (
    AuthInfo,
    RemoteNotFoundError,
    RevOptions,
    VersionControl,
    vcs,
)

logger = logging.getLogger(__name__)

_svn_xml_url_re = re.compile('url="([^"]+)"')
_svn_rev_re = re.compile(r'committed-rev="(\d+)"')
_svn_info_xml_rev_re = re.compile(r'\s*revision="(\d+)"')
_svn_info_xml_url_re = re.compile(r"<url>(.*)</url>")


class Subversion(VersionControl):
    name = "svn"
    dirname = ".svn"
    repo_name = "checkout"
    schemes = ("svn+ssh", "svn+http", "svn+https", "svn+svn", "svn+file")

    @classmethod
    def should_add_vcs_url_prefix(cls, remote_url: str) -> bool:
        return True

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return ["-r", rev]

    @classmethod
    def get_revision(cls, location: str) -> str:
        """
        Return the maximum revision for all files under a given location
        """
        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, _ in os.walk(location):
            if cls.dirname not in dirs:
                dirs[:] = []
                continue  # no sense walking uncontrolled subdirs
            dirs.remove(cls.dirname)
            entries_fn = os.path.join(base, cls.dirname, "entries")
            if not os.path.exists(entries_fn):
                # FIXME: should we warn?
                continue

            dirurl, localrev = cls._get_svn_url_rev(base)

            if base == location:
                assert dirurl is not None
                base = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return str(revision)

    @classmethod
    def get_netloc_and_auth(
        cls, netloc: str, scheme: str
    ) -> Tuple[str, Tuple[Optional[str], Optional[str]]]:
        """
        This override allows the auth information to be passed to svn via the
        --username and --password options instead of via the URL.
        """
        if scheme == "ssh":
            # The --username and --password options can't be used for
            # svn+ssh URLs, so keep the auth information in the URL.
            return super().get_netloc_and_auth(netloc, scheme)

        return split_auth_from_netloc(netloc)

    @classmethod
    def get_url_rev_and_auth(cls, url: str) -> Tuple[str, Optional[str], AuthInfo]:
        # hotfix the URL scheme after removing svn+ from svn+ssh:// re-add it
        url, rev, user_pass = super().get_url_rev_and_auth(url)
        if url.startswith("ssh://"):
            url = "svn+" + url
        return url, rev, user_pass

    @staticmethod
    def make_rev_args(
        username: Optional[str], password: Optional[HiddenText]
    ) -> CommandArgs:
        extra_args: CommandArgs = []
        if username:
            extra_args += ["--username", username]
        if password:
            extra_args += ["--password", password]

        return extra_args

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        # In cases where the source is in a subdirectory, we have to look up in
        # the location until we find a valid project root.
        orig_location = location
        while not is_installable_dir(location):
            last_location = location
            location = os.path.dirname(location)
            if location == last_location:
                # We've traversed up to the root of the filesystem without
                # finding a Python project.
                logger.warning(
                    "Could not find Python project for directory %s (tried all "
                    "parent directories)",
                    orig_location,
                )
                raise RemoteNotFoundError

        url, _rev = cls._get_svn_url_rev(location)
        if url is None:
            raise RemoteNotFoundError

        return url

    @classmethod
    def _get_svn_url_rev(cls, location: str) -> Tuple[Optional[str], int]:
        from pip._internal.exceptions import InstallationError

        entries_path = os.path.join(location, cls.dirname, "entries")
        if os.path.exists(entries_path):
            with open(entries_path) as f:
                data = f.read()
        else:  # subversion >= 1.7 does not have the 'entries' file
            data = ""

        url = None
        if data.startswith("8") or data.startswith("9") or data.startswith("10"):
            entries = list(map(str.splitlines, data.split("\n\x0c\n")))
            del entries[0][0]  # get rid of the '8'
            url = entries[0][3]
            revs = [int(d[9]) for d in entries if len(d) > 9 and d[9]] + [0]
        elif data.startswith("<?xml"):
            match = _svn_xml_url_re.search(data)
            if not match:
                raise ValueError(f"Badly formatted data: {data!r}")
            url = match.group(1)  # get repository URL
            revs = [int(m.group(1)) for m in _svn_rev_re.finditer(data)] + [0]
        else:
            try:
                # subversion >= 1.7
                # Note that using get_remote_call_options is not necessary here
                # because `svn info` is being run against a local directory.
                # We don't need to worry about making sure interactive mode
                # is being used to prompt for passwords, because passwords
                # are only potentially needed for remote server requests.
                xml = cls.run_command(
                    ["info", "--xml", location],
                    show_stdout=False,
                    stdout_only=True,
                )
                match = _svn_info_xml_url_re.search(xml)
                assert match is not None
                url = match.group(1)
                revs = [int(m.group(1)) for m in _svn_info_xml_rev_re.finditer(xml)]
            except InstallationError:
                url, revs = None, []

        if revs:
            rev = max(revs)
        else:
            rev = 0

        return url, rev

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """Always assume the versions don't match"""
        return False

    def __init__(self, use_interactive: Optional[bool] = None) -> None:
        if use_interactive is None:
            use_interactive = is_console_interactive()
        self.use_interactive = use_interactive

        # This member is used to cache the fetched version of the current
        # ``svn`` client.
        # Special value definitions:
        #   None: Not evaluated yet.
        #   Empty tuple: Could not parse version.
        self._vcs_version: Optional[Tuple[int, ...]] = None

        super().__init__()

    def call_vcs_version(self) -> Tuple[int, ...]:
        """Query the version of the currently installed Subversion client.

        :return: A tuple containing the parts of the version information or
            ``()`` if the version returned from ``svn`` could not be parsed.
        :raises: BadCommand: If ``svn`` is not installed.
        """
        # Example versions:
        #   svn, version 1.10.3 (r1842928)
        #      compiled Feb 25 2019, 14:20:39 on x86_64-apple-darwin17.0.0
        #   svn, version 1.7.14 (r1542130)
        #      compiled Mar 28 2018, 08:49:13 on x86_64-pc-linux-gnu
        #   svn, version 1.12.0-SlikSvn (SlikSvn/1.12.0)
        #      compiled May 28 2019, 13:44:56 on x86_64-microsoft-windows6.2
        version_prefix = "svn, version "
        version = self.run_command(["--version"], show_stdout=False, stdout_only=True)
        if not version.startswith(version_prefix):
            return ()

        version = version[len(version_prefix) :].split()[0]
        version_list = version.partition("-")[0].split(".")
        try:
            parsed_version = tuple(map(int, version_list))
        except ValueError:
            return ()

        return parsed_version

    def get_vcs_version(self) -> Tuple[int, ...]:
        """Return the version of the currently installed Subversion client.

        If the version of the Subversion client has already been queried,
        a cached value will be used.

        :return: A tuple containing the parts of the version information or
            ``()`` if the version returned from ``svn`` could not be parsed.
        :raises: BadCommand: If ``svn`` is not installed.
        """
        if self._vcs_version is not None:
            # Use cached version, if available.
            # If parsing the version failed previously (empty tuple),
            # do not attempt to parse it again.
            return self._vcs_version

        vcs_version = self.call_vcs_version()
        self._vcs_version = vcs_version
        return vcs_version

    def get_remote_call_options(self) -> CommandArgs:
        """Return options to be used on calls to Subversion that contact the server.

        These options are applicable for the following ``svn`` subcommands used
        in this class.

            - checkout
            - switch
            - update

        :return: A list of command line arguments to pass to ``svn``.
        """
        if not self.use_interactive:
            # --non-interactive switch is available since Subversion 0.14.4.
            # Subversion < 1.8 runs in interactive mode by default.
            return ["--non-interactive"]

        svn_version = self.get_vcs_version()
        # By default, Subversion >= 1.8 runs in non-interactive mode if
        # stdin is not a TTY. Since that is how pip invokes SVN, in
        # call_subprocess(), pip must pass --force-interactive to ensure
        # the user can be prompted for a password, if required.
        #   SVN added the --force-interactive option in SVN 1.8. Since
        # e.g. RHEL/CentOS 7, which is supported until 2024, ships with
        # SVN 1.7, pip should continue to support SVN 1.7. Therefore, pip
        # can't safely add the option if the SVN version is < 1.8 (or unknown).
        if svn_version >= (1, 8):
            return ["--force-interactive"]

        return []

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info(
            "Checking out %s%s to %s",
            url,
            rev_display,
            display_path(dest),
        )
        if verbosity <= 0:
            flags = ["--quiet"]
        else:
            flags = []
        cmd_args = make_command(
            "checkout",
            *flags,
            self.get_remote_call_options(),
            rev_options.to_args(),
            url,
            dest,
        )
        self.run_command(cmd_args)

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        cmd_args = make_command(
            "switch",
            self.get_remote_call_options(),
            rev_options.to_args(),
            url,
            dest,
        )
        self.run_command(cmd_args)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        cmd_args = make_command(
            "update",
            self.get_remote_call_options(),
            rev_options.to_args(),
            dest,
        )
        self.run_command(cmd_args)


vcs.register(Subversion)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\util.py ===
"""
    pygments.util
    ~~~~~~~~~~~~~

    Utility functions.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from io import TextIOWrapper


split_path_re = re.compile(r'[/\\ ]')
doctype_lookup_re = re.compile(r'''
    <!DOCTYPE\s+(
     [a-zA-Z_][a-zA-Z0-9]*
     (?: \s+      # optional in HTML5
     [a-zA-Z_][a-zA-Z0-9]*\s+
     "[^"]*")?
     )
     [^>]*>
''', re.DOTALL | re.MULTILINE | re.VERBOSE)
tag_re = re.compile(r'<(.+?)(\s.*?)?>.*?</.+?>',
                    re.IGNORECASE | re.DOTALL | re.MULTILINE)
xml_decl_re = re.compile(r'\s*<\?xml[^>]*\?>', re.I)


class ClassNotFound(ValueError):
    """Raised if one of the lookup functions didn't find a matching class."""


class OptionError(Exception):
    """
    This exception will be raised by all option processing functions if
    the type or value of the argument is not correct.
    """

def get_choice_opt(options, optname, allowed, default=None, normcase=False):
    """
    If the key `optname` from the dictionary is not in the sequence
    `allowed`, raise an error, otherwise return it.
    """
    string = options.get(optname, default)
    if normcase:
        string = string.lower()
    if string not in allowed:
        raise OptionError('Value for option {} must be one of {}'.format(optname, ', '.join(map(str, allowed))))
    return string


def get_bool_opt(options, optname, default=None):
    """
    Intuitively, this is `options.get(optname, default)`, but restricted to
    Boolean value. The Booleans can be represented as string, in order to accept
    Boolean value from the command line arguments. If the key `optname` is
    present in the dictionary `options` and is not associated with a Boolean,
    raise an `OptionError`. If it is absent, `default` is returned instead.

    The valid string values for ``True`` are ``1``, ``yes``, ``true`` and
    ``on``, the ones for ``False`` are ``0``, ``no``, ``false`` and ``off``
    (matched case-insensitively).
    """
    string = options.get(optname, default)
    if isinstance(string, bool):
        return string
    elif isinstance(string, int):
        return bool(string)
    elif not isinstance(string, str):
        raise OptionError(f'Invalid type {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')
    elif string.lower() in ('1', 'yes', 'true', 'on'):
        return True
    elif string.lower() in ('0', 'no', 'false', 'off'):
        return False
    else:
        raise OptionError(f'Invalid value {string!r} for option {optname}; use '
                          '1/0, yes/no, true/false, on/off')


def get_int_opt(options, optname, default=None):
    """As :func:`get_bool_opt`, but interpret the value as an integer."""
    string = options.get(optname, default)
    try:
        return int(string)
    except TypeError:
        raise OptionError(f'Invalid type {string!r} for option {optname}; you '
                          'must give an integer value')
    except ValueError:
        raise OptionError(f'Invalid value {string!r} for option {optname}; you '
                          'must give an integer value')

def get_list_opt(options, optname, default=None):
    """
    If the key `optname` from the dictionary `options` is a string,
    split it at whitespace and return it. If it is already a list
    or a tuple, it is returned as a list.
    """
    val = options.get(optname, default)
    if isinstance(val, str):
        return val.split()
    elif isinstance(val, (list, tuple)):
        return list(val)
    else:
        raise OptionError(f'Invalid type {val!r} for option {optname}; you '
                          'must give a list value')


def docstring_headline(obj):
    if not obj.__doc__:
        return ''
    res = []
    for line in obj.__doc__.strip().splitlines():
        if line.strip():
            res.append(" " + line.strip())
        else:
            break
    return ''.join(res).lstrip()


def make_analysator(f):
    """Return a static text analyser function that returns float values."""
    def text_analyse(text):
        try:
            rv = f(text)
        except Exception:
            return 0.0
        if not rv:
            return 0.0
        try:
            return min(1.0, max(0.0, float(rv)))
        except (ValueError, TypeError):
            return 0.0
    text_analyse.__doc__ = f.__doc__
    return staticmethod(text_analyse)


def shebang_matches(text, regex):
    r"""Check if the given regular expression matches the last part of the
    shebang if one exists.

        >>> from pygments.util import shebang_matches
        >>> shebang_matches('#!/usr/bin/env python', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python2.4', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python-ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/python/ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/startsomethingwith python',
        ...                 r'python(2\.\d)?')
        True

    It also checks for common windows executable file extensions::

        >>> shebang_matches('#!C:\\Python2.4\\Python.exe', r'python(2\.\d)?')
        True

    Parameters (``'-f'`` or ``'--foo'`` are ignored so ``'perl'`` does
    the same as ``'perl -e'``)

    Note that this method automatically searches the whole string (eg:
    the regular expression is wrapped in ``'^$'``)
    """
    index = text.find('\n')
    if index >= 0:
        first_line = text[:index].lower()
    else:
        first_line = text.lower()
    if first_line.startswith('#!'):
        try:
            found = [x for x in split_path_re.split(first_line[2:].strip())
                     if x and not x.startswith('-')][-1]
        except IndexError:
            return False
        regex = re.compile(rf'^{regex}(\.(exe|cmd|bat|bin))?$', re.IGNORECASE)
        if regex.search(found) is not None:
            return True
    return False


def doctype_matches(text, regex):
    """Check if the doctype matches a regular expression (if present).

    Note that this method only checks the first part of a DOCTYPE.
    eg: 'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
    """
    m = doctype_lookup_re.search(text)
    if m is None:
        return False
    doctype = m.group(1)
    return re.compile(regex, re.I).match(doctype.strip()) is not None


def html_doctype_matches(text):
    """Check if the file looks like it has a html doctype."""
    return doctype_matches(text, r'html')


_looks_like_xml_cache = {}


def looks_like_xml(text):
    """Check if a doctype exists or if we have some tags."""
    if xml_decl_re.match(text):
        return True
    key = hash(text)
    try:
        return _looks_like_xml_cache[key]
    except KeyError:
        m = doctype_lookup_re.search(text)
        if m is not None:
            return True
        rv = tag_re.search(text[:1000]) is not None
        _looks_like_xml_cache[key] = rv
        return rv


def surrogatepair(c):
    """Given a unicode character code with length greater than 16 bits,
    return the two 16 bit surrogate pair.
    """
    # From example D28 of:
    # http://www.unicode.org/book/ch03.pdf
    return (0xd7c0 + (c >> 10), (0xdc00 + (c & 0x3ff)))


def format_lines(var_name, seq, raw=False, indent_level=0):
    """Formats a sequence of strings for output."""
    lines = []
    base_indent = ' ' * indent_level * 4
    inner_indent = ' ' * (indent_level + 1) * 4
    lines.append(base_indent + var_name + ' = (')
    if raw:
        # These should be preformatted reprs of, say, tuples.
        for i in seq:
            lines.append(inner_indent + i + ',')
    else:
        for i in seq:
            # Force use of single quotes
            r = repr(i + '"')
            lines.append(inner_indent + r[:-2] + r[-1] + ',')
    lines.append(base_indent + ')')
    return '\n'.join(lines)


def duplicates_removed(it, already_seen=()):
    """
    Returns a list with duplicates removed from the iterable `it`.

    Order is preserved.
    """
    lst = []
    seen = set()
    for i in it:
        if i in seen or i in already_seen:
            continue
        lst.append(i)
        seen.add(i)
    return lst


class Future:
    """Generic class to defer some work.

    Handled specially in RegexLexerMeta, to support regex string construction at
    first use.
    """
    def get(self):
        raise NotImplementedError


def guess_decode(text):
    """Decode *text* with guessed encoding.

    First try UTF-8; this should fail for non-UTF-8 encodings.
    Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    try:
        text = text.decode('utf-8')
        return text, 'utf-8'
    except UnicodeDecodeError:
        try:
            import locale
            prefencoding = locale.getpreferredencoding()
            text = text.decode()
            return text, prefencoding
        except (UnicodeDecodeError, LookupError):
            text = text.decode('latin1')
            return text, 'latin1'


def guess_decode_from_terminal(text, term):
    """Decode *text* coming from terminal *term*.

    First try the terminal encoding, if given.
    Then try UTF-8.  Then try the preferred locale encoding.
    Fall back to latin-1, which always works.
    """
    if getattr(term, 'encoding', None):
        try:
            text = text.decode(term.encoding)
        except UnicodeDecodeError:
            pass
        else:
            return text, term.encoding
    return guess_decode(text)


def terminal_encoding(term):
    """Return our best guess of encoding for the given *term*."""
    if getattr(term, 'encoding', None):
        return term.encoding
    import locale
    return locale.getpreferredencoding()


class UnclosingTextIOWrapper(TextIOWrapper):
    # Don't close underlying buffer on destruction.
    def close(self):
        self.flush()

# === NexusCore/openenv\Lib\site-packages\tornado\test\escape_test.py ===
import unittest

import tornado
from tornado.escape import (
    utf8,
    xhtml_escape,
    xhtml_unescape,
    url_escape,
    url_unescape,
    to_unicode,
    json_decode,
    json_encode,
    squeeze,
    recursive_unicode,
)
from tornado.util import unicode_type

from typing import List, Tuple, Union, Dict, Any  # noqa: F401

linkify_tests = [
    # (input, linkify_kwargs, expected_output)
    (
        "hello http://world.com/!",
        {},
        'hello <a href="http://world.com/">http://world.com/</a>!',
    ),
    (
        "hello http://world.com/with?param=true&stuff=yes",
        {},
        'hello <a href="http://world.com/with?param=true&amp;stuff=yes">http://world.com/with?param=true&amp;stuff=yes</a>',  # noqa: E501
    ),
    # an opened paren followed by many chars killed Gruber's regex
    (
        "http://url.com/w(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        {},
        '<a href="http://url.com/w">http://url.com/w</a>(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',  # noqa: E501
    ),
    # as did too many dots at the end
    (
        "http://url.com/withmany.......................................",
        {},
        '<a href="http://url.com/withmany">http://url.com/withmany</a>.......................................',  # noqa: E501
    ),
    (
        "http://url.com/withmany((((((((((((((((((((((((((((((((((a)",
        {},
        '<a href="http://url.com/withmany">http://url.com/withmany</a>((((((((((((((((((((((((((((((((((a)',  # noqa: E501
    ),
    # some examples from http://daringfireball.net/2009/11/liberal_regex_for_matching_urls
    # plus a fex extras (such as multiple parentheses).
    (
        "http://foo.com/blah_blah",
        {},
        '<a href="http://foo.com/blah_blah">http://foo.com/blah_blah</a>',
    ),
    (
        "http://foo.com/blah_blah/",
        {},
        '<a href="http://foo.com/blah_blah/">http://foo.com/blah_blah/</a>',
    ),
    (
        "(Something like http://foo.com/blah_blah)",
        {},
        '(Something like <a href="http://foo.com/blah_blah">http://foo.com/blah_blah</a>)',
    ),
    (
        "http://foo.com/blah_blah_(wikipedia)",
        {},
        '<a href="http://foo.com/blah_blah_(wikipedia)">http://foo.com/blah_blah_(wikipedia)</a>',
    ),
    (
        "http://foo.com/blah_(blah)_(wikipedia)_blah",
        {},
        '<a href="http://foo.com/blah_(blah)_(wikipedia)_blah">http://foo.com/blah_(blah)_(wikipedia)_blah</a>',  # noqa: E501
    ),
    (
        "(Something like http://foo.com/blah_blah_(wikipedia))",
        {},
        '(Something like <a href="http://foo.com/blah_blah_(wikipedia)">http://foo.com/blah_blah_(wikipedia)</a>)',  # noqa: E501
    ),
    (
        "http://foo.com/blah_blah.",
        {},
        '<a href="http://foo.com/blah_blah">http://foo.com/blah_blah</a>.',
    ),
    (
        "http://foo.com/blah_blah/.",
        {},
        '<a href="http://foo.com/blah_blah/">http://foo.com/blah_blah/</a>.',
    ),
    (
        "<http://foo.com/blah_blah>",
        {},
        '&lt;<a href="http://foo.com/blah_blah">http://foo.com/blah_blah</a>&gt;',
    ),
    (
        "<http://foo.com/blah_blah/>",
        {},
        '&lt;<a href="http://foo.com/blah_blah/">http://foo.com/blah_blah/</a>&gt;',
    ),
    (
        "http://foo.com/blah_blah,",
        {},
        '<a href="http://foo.com/blah_blah">http://foo.com/blah_blah</a>,',
    ),
    (
        "http://www.example.com/wpstyle/?p=364.",
        {},
        '<a href="http://www.example.com/wpstyle/?p=364">http://www.example.com/wpstyle/?p=364</a>.',  # noqa: E501
    ),
    (
        "rdar://1234",
        {"permitted_protocols": ["http", "rdar"]},
        '<a href="rdar://1234">rdar://1234</a>',
    ),
    (
        "rdar:/1234",
        {"permitted_protocols": ["rdar"]},
        '<a href="rdar:/1234">rdar:/1234</a>',
    ),
    (
        "http://userid:password@example.com:8080",
        {},
        '<a href="http://userid:password@example.com:8080">http://userid:password@example.com:8080</a>',  # noqa: E501
    ),
    (
        "http://userid@example.com",
        {},
        '<a href="http://userid@example.com">http://userid@example.com</a>',
    ),
    (
        "http://userid@example.com:8080",
        {},
        '<a href="http://userid@example.com:8080">http://userid@example.com:8080</a>',
    ),
    (
        "http://userid:password@example.com",
        {},
        '<a href="http://userid:password@example.com">http://userid:password@example.com</a>',
    ),
    (
        "message://%3c330e7f8409726r6a4ba78dkf1fd71420c1bf6ff@mail.gmail.com%3e",
        {"permitted_protocols": ["http", "message"]},
        '<a href="message://%3c330e7f8409726r6a4ba78dkf1fd71420c1bf6ff@mail.gmail.com%3e">'
        "message://%3c330e7f8409726r6a4ba78dkf1fd71420c1bf6ff@mail.gmail.com%3e</a>",
    ),
    (
        "http://\u27a1.ws/\u4a39",
        {},
        '<a href="http://\u27a1.ws/\u4a39">http://\u27a1.ws/\u4a39</a>',
    ),
    (
        "<tag>http://example.com</tag>",
        {},
        '&lt;tag&gt;<a href="http://example.com">http://example.com</a>&lt;/tag&gt;',
    ),
    (
        "Just a www.example.com link.",
        {},
        'Just a <a href="http://www.example.com">www.example.com</a> link.',
    ),
    (
        "Just a www.example.com link.",
        {"require_protocol": True},
        "Just a www.example.com link.",
    ),
    (
        "A http://reallylong.com/link/that/exceedsthelenglimit.html",
        {"require_protocol": True, "shorten": True},
        'A <a href="http://reallylong.com/link/that/exceedsthelenglimit.html"'
        ' title="http://reallylong.com/link/that/exceedsthelenglimit.html">http://reallylong.com/link...</a>',  # noqa: E501
    ),
    (
        "A http://reallylongdomainnamethatwillbetoolong.com/hi!",
        {"shorten": True},
        'A <a href="http://reallylongdomainnamethatwillbetoolong.com/hi"'
        ' title="http://reallylongdomainnamethatwillbetoolong.com/hi">http://reallylongdomainnametha...</a>!',  # noqa: E501
    ),
    (
        "A file:///passwords.txt and http://web.com link",
        {},
        'A file:///passwords.txt and <a href="http://web.com">http://web.com</a> link',
    ),
    (
        "A file:///passwords.txt and http://web.com link",
        {"permitted_protocols": ["file"]},
        'A <a href="file:///passwords.txt">file:///passwords.txt</a> and http://web.com link',
    ),
    (
        "www.external-link.com",
        {"extra_params": 'rel="nofollow" class="external"'},
        '<a href="http://www.external-link.com" rel="nofollow" class="external">www.external-link.com</a>',  # noqa: E501
    ),
    (
        "www.external-link.com and www.internal-link.com/blogs extra",
        {
            "extra_params": lambda href: (
                'class="internal"'
                if href.startswith("http://www.internal-link.com")
                else 'rel="nofollow" class="external"'
            )
        },
        '<a href="http://www.external-link.com" rel="nofollow" class="external">www.external-link.com</a>'  # noqa: E501
        ' and <a href="http://www.internal-link.com/blogs" class="internal">www.internal-link.com/blogs</a> extra',  # noqa: E501
    ),
    (
        "www.external-link.com",
        {"extra_params": lambda href: '    rel="nofollow" class="external"  '},
        '<a href="http://www.external-link.com" rel="nofollow" class="external">www.external-link.com</a>',  # noqa: E501
    ),
]  # type: List[Tuple[Union[str, bytes], Dict[str, Any], str]]


class EscapeTestCase(unittest.TestCase):
    def test_linkify(self):
        for text, kwargs, html in linkify_tests:
            linked = tornado.escape.linkify(text, **kwargs)
            self.assertEqual(linked, html)

    def test_xhtml_escape(self):
        tests = [
            ("<foo>", "&lt;foo&gt;"),
            ("<foo>", "&lt;foo&gt;"),
            (b"<foo>", b"&lt;foo&gt;"),
            ("<>&\"'", "&lt;&gt;&amp;&quot;&#x27;"),
            ("&amp;", "&amp;amp;"),
            ("<\u00e9>", "&lt;\u00e9&gt;"),
            (b"<\xc3\xa9>", b"&lt;\xc3\xa9&gt;"),
        ]  # type: List[Tuple[Union[str, bytes], Union[str, bytes]]]
        for unescaped, escaped in tests:
            self.assertEqual(utf8(xhtml_escape(unescaped)), utf8(escaped))
            self.assertEqual(utf8(unescaped), utf8(xhtml_unescape(escaped)))

    def test_xhtml_unescape_numeric(self):
        tests = [
            ("foo&#32;bar", "foo bar"),
            ("foo&#x20;bar", "foo bar"),
            ("foo&#X20;bar", "foo bar"),
            ("foo&#xabc;bar", "foo\u0abcbar"),
            ("foo&#xyz;bar", "foo&#xyz;bar"),  # invalid encoding
            ("foo&#;bar", "foo&#;bar"),  # invalid encoding
            ("foo&#x;bar", "foo&#x;bar"),  # invalid encoding
        ]
        for escaped, unescaped in tests:
            self.assertEqual(unescaped, xhtml_unescape(escaped))

    def test_url_escape_unicode(self):
        tests = [
            # byte strings are passed through as-is
            ("\u00e9".encode(), "%C3%A9"),
            ("\u00e9".encode("latin1"), "%E9"),
            # unicode strings become utf8
            ("\u00e9", "%C3%A9"),
        ]  # type: List[Tuple[Union[str, bytes], str]]
        for unescaped, escaped in tests:
            self.assertEqual(url_escape(unescaped), escaped)

    def test_url_unescape_unicode(self):
        tests = [
            ("%C3%A9", "\u00e9", "utf8"),
            ("%C3%A9", "\u00c3\u00a9", "latin1"),
            ("%C3%A9", utf8("\u00e9"), None),
        ]
        for escaped, unescaped, encoding in tests:
            # input strings to url_unescape should only contain ascii
            # characters, but make sure the function accepts both byte
            # and unicode strings.
            self.assertEqual(url_unescape(to_unicode(escaped), encoding), unescaped)
            self.assertEqual(url_unescape(utf8(escaped), encoding), unescaped)

    def test_url_escape_quote_plus(self):
        unescaped = "+ #%"
        plus_escaped = "%2B+%23%25"
        escaped = "%2B%20%23%25"
        self.assertEqual(url_escape(unescaped), plus_escaped)
        self.assertEqual(url_escape(unescaped, plus=False), escaped)
        self.assertEqual(url_unescape(plus_escaped), unescaped)
        self.assertEqual(url_unescape(escaped, plus=False), unescaped)
        self.assertEqual(url_unescape(plus_escaped, encoding=None), utf8(unescaped))
        self.assertEqual(
            url_unescape(escaped, encoding=None, plus=False), utf8(unescaped)
        )

    def test_escape_return_types(self):
        # On python2 the escape methods should generally return the same
        # type as their argument
        self.assertEqual(type(xhtml_escape("foo")), str)
        self.assertEqual(type(xhtml_escape("foo")), unicode_type)

    def test_json_decode(self):
        # json_decode accepts both bytes and unicode, but strings it returns
        # are always unicode.
        self.assertEqual(json_decode(b'"foo"'), "foo")
        self.assertEqual(json_decode('"foo"'), "foo")

        # Non-ascii bytes are interpreted as utf8
        self.assertEqual(json_decode(utf8('"\u00e9"')), "\u00e9")

    def test_json_encode(self):
        # json deals with strings, not bytes.  On python 2 byte strings will
        # convert automatically if they are utf8; on python 3 byte strings
        # are not allowed.
        self.assertEqual(json_decode(json_encode("\u00e9")), "\u00e9")
        if bytes is str:
            self.assertEqual(json_decode(json_encode(utf8("\u00e9"))), "\u00e9")
            self.assertRaises(UnicodeDecodeError, json_encode, b"\xe9")

    def test_squeeze(self):
        self.assertEqual(
            squeeze("sequences     of    whitespace   chars"),
            "sequences of whitespace chars",
        )

    def test_recursive_unicode(self):
        tests = {
            "dict": {b"foo": b"bar"},
            "list": [b"foo", b"bar"],
            "tuple": (b"foo", b"bar"),
            "bytes": b"foo",
        }
        self.assertEqual(recursive_unicode(tests["dict"]), {"foo": "bar"})
        self.assertEqual(recursive_unicode(tests["list"]), ["foo", "bar"])
        self.assertEqual(recursive_unicode(tests["tuple"]), ("foo", "bar"))
        self.assertEqual(recursive_unicode(tests["bytes"]), "foo")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\exceptions.py ===
from __future__ import absolute_import

from .packages.six.moves.http_client import IncompleteRead as httplib_IncompleteRead

# Base Exceptions


class HTTPError(Exception):
    """Base exception used by this module."""

    pass


class HTTPWarning(Warning):
    """Base warning used by this module."""

    pass


class PoolError(HTTPError):
    """Base exception for errors caused within a pool."""

    def __init__(self, pool, message):
        self.pool = pool
        HTTPError.__init__(self, "%s: %s" % (pool, message))

    def __reduce__(self):
        # For pickling purposes.
        return self.__class__, (None, None)


class RequestError(PoolError):
    """Base exception for PoolErrors that have associated URLs."""

    def __init__(self, pool, url, message):
        self.url = url
        PoolError.__init__(self, pool, message)

    def __reduce__(self):
        # For pickling purposes.
        return self.__class__, (None, self.url, None)


class SSLError(HTTPError):
    """Raised when SSL certificate fails in an HTTPS connection."""

    pass


class ProxyError(HTTPError):
    """Raised when the connection to a proxy fails."""

    def __init__(self, message, error, *args):
        super(ProxyError, self).__init__(message, error, *args)
        self.original_error = error


class DecodeError(HTTPError):
    """Raised when automatic decoding based on Content-Type fails."""

    pass


class ProtocolError(HTTPError):
    """Raised when something unexpected happens mid-request/response."""

    pass


#: Renamed to ProtocolError but aliased for backwards compatibility.
ConnectionError = ProtocolError


# Leaf Exceptions


class MaxRetryError(RequestError):
    """Raised when the maximum number of retries is exceeded.

    :param pool: The connection pool
    :type pool: :class:`~urllib3.connectionpool.HTTPConnectionPool`
    :param string url: The requested Url
    :param exceptions.Exception reason: The underlying error

    """

    def __init__(self, pool, url, reason=None):
        self.reason = reason

        message = "Max retries exceeded with url: %s (Caused by %r)" % (url, reason)

        RequestError.__init__(self, pool, url, message)


class HostChangedError(RequestError):
    """Raised when an existing pool gets a request for a foreign host."""

    def __init__(self, pool, url, retries=3):
        message = "Tried to open a foreign host with url: %s" % url
        RequestError.__init__(self, pool, url, message)
        self.retries = retries


class TimeoutStateError(HTTPError):
    """Raised when passing an invalid state to a timeout"""

    pass


class TimeoutError(HTTPError):
    """Raised when a socket timeout error occurs.

    Catching this error will catch both :exc:`ReadTimeoutErrors
    <ReadTimeoutError>` and :exc:`ConnectTimeoutErrors <ConnectTimeoutError>`.
    """

    pass


class ReadTimeoutError(TimeoutError, RequestError):
    """Raised when a socket timeout occurs while receiving data from a server"""

    pass


# This timeout error does not have a URL attached and needs to inherit from the
# base HTTPError
class ConnectTimeoutError(TimeoutError):
    """Raised when a socket timeout occurs while connecting to a server"""

    pass


class NewConnectionError(ConnectTimeoutError, PoolError):
    """Raised when we fail to establish a new connection. Usually ECONNREFUSED."""

    pass


class EmptyPoolError(PoolError):
    """Raised when a pool runs out of connections and no more are allowed."""

    pass


class ClosedPoolError(PoolError):
    """Raised when a request enters a pool after the pool has been closed."""

    pass


class LocationValueError(ValueError, HTTPError):
    """Raised when there is something wrong with a given URL input."""

    pass


class LocationParseError(LocationValueError):
    """Raised when get_host or similar fails to parse the URL input."""

    def __init__(self, location):
        message = "Failed to parse: %s" % location
        HTTPError.__init__(self, message)

        self.location = location


class URLSchemeUnknown(LocationValueError):
    """Raised when a URL input has an unsupported scheme."""

    def __init__(self, scheme):
        message = "Not supported URL scheme %s" % scheme
        super(URLSchemeUnknown, self).__init__(message)

        self.scheme = scheme


class ResponseError(HTTPError):
    """Used as a container for an error reason supplied in a MaxRetryError."""

    GENERIC_ERROR = "too many error responses"
    SPECIFIC_ERROR = "too many {status_code} error responses"


class SecurityWarning(HTTPWarning):
    """Warned when performing security reducing actions"""

    pass


class SubjectAltNameWarning(SecurityWarning):
    """Warned when connecting to a host with a certificate missing a SAN."""

    pass


class InsecureRequestWarning(SecurityWarning):
    """Warned when making an unverified HTTPS request."""

    pass


class SystemTimeWarning(SecurityWarning):
    """Warned when system time is suspected to be wrong"""

    pass


class InsecurePlatformWarning(SecurityWarning):
    """Warned when certain TLS/SSL configuration is not available on a platform."""

    pass


class SNIMissingWarning(HTTPWarning):
    """Warned when making a HTTPS request without SNI available."""

    pass


class DependencyWarning(HTTPWarning):
    """
    Warned when an attempt is made to import a module with missing optional
    dependencies.
    """

    pass


class ResponseNotChunked(ProtocolError, ValueError):
    """Response needs to be chunked in order to read it as chunks."""

    pass


class BodyNotHttplibCompatible(HTTPError):
    """
    Body should be :class:`http.client.HTTPResponse` like
    (have an fp attribute which returns raw chunks) for read_chunked().
    """

    pass


class IncompleteRead(HTTPError, httplib_IncompleteRead):
    """
    Response length doesn't match expected Content-Length

    Subclass of :class:`http.client.IncompleteRead` to allow int value
    for ``partial`` to avoid creating large objects on streamed reads.
    """

    def __init__(self, partial, expected):
        super(IncompleteRead, self).__init__(partial, expected)

    def __repr__(self):
        return "IncompleteRead(%i bytes read, %i more expected)" % (
            self.partial,
            self.expected,
        )


class InvalidChunkLength(HTTPError, httplib_IncompleteRead):
    """Invalid chunk length in a chunked response."""

    def __init__(self, response, length):
        super(InvalidChunkLength, self).__init__(
            response.tell(), response.length_remaining
        )
        self.response = response
        self.length = length

    def __repr__(self):
        return "InvalidChunkLength(got length %r, %i bytes read)" % (
            self.length,
            self.partial,
        )


class InvalidHeader(HTTPError):
    """The header provided was somehow invalid."""

    pass


class ProxySchemeUnknown(AssertionError, URLSchemeUnknown):
    """ProxyManager does not support the supplied scheme"""

    # TODO(t-8ch): Stop inheriting from AssertionError in v2.0.

    def __init__(self, scheme):
        # 'localhost' is here because our URL parser parses
        # localhost:8080 -> scheme=localhost, remove if we fix this.
        if scheme == "localhost":
            scheme = None
        if scheme is None:
            message = "Proxy URL had no scheme, should start with http:// or https://"
        else:
            message = (
                "Proxy URL had unsupported scheme %s, should use http:// or https://"
                % scheme
            )
        super(ProxySchemeUnknown, self).__init__(message)


class ProxySchemeUnsupported(ValueError):
    """Fetching HTTPS resources through HTTPS proxies is unsupported"""

    pass


class HeaderParsingError(HTTPError):
    """Raised by assert_header_parsing, but we convert it to a log.warning statement."""

    def __init__(self, defects, unparsed_data):
        message = "%s, unparsed data: %r" % (defects or "Unknown", unparsed_data)
        super(HeaderParsingError, self).__init__(message)


class UnrewindableBodyError(HTTPError):
    """urllib3 encountered an error when trying to rewind a body"""

    pass