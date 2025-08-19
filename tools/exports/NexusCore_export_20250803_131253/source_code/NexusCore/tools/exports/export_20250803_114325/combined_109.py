
# === NexusCore/openenv\Lib\site-packages\trio\_core\_io_windows.py ===
from __future__ import annotations

import enum
import itertools
import socket
import sys
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    TypeVar,
    cast,
)

import attrs
from outcome import Value

from .. import _core
from ._io_common import wake_all
from ._run import _public
from ._windows_cffi import (
    INVALID_HANDLE_VALUE,
    AFDPollFlags,
    CData,
    CompletionModes,
    CType,
    ErrorCodes,
    FileFlags,
    Handle,
    IoControlCodes,
    WSAIoctls,
    _handle,
    _Overlapped,
    ffi,
    kernel32,
    ntdll,
    raise_winerror,
    ws2_32,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from typing_extensions import Buffer, TypeAlias

    from .._file_io import _HasFileNo
    from ._traps import Abort, RaiseCancelT
    from ._unbounded_queue import UnboundedQueue

EventResult: TypeAlias = int
T = TypeVar("T")

# There's a lot to be said about the overall design of a Windows event
# loop. See
#
#    https://github.com/python-trio/trio/issues/52
#
# for discussion. This now just has some lower-level notes:
#
# How IOCP fits together:
#
# The general model is that you call some function like ReadFile or WriteFile
# to tell the kernel that you want it to perform some operation, and the
# kernel goes off and does that in the background, then at some point later it
# sends you a notification that the operation is complete. There are some more
# exotic APIs that don't quite fit this pattern, but most APIs do.
#
# Each background operation is tracked using an OVERLAPPED struct, that
# uniquely identifies that particular operation.
#
# An "IOCP" (or "I/O completion port") is an object that lets the kernel send
# us these notifications -- basically it's just a kernel->userspace queue.
#
# Each IOCP notification is represented by an OVERLAPPED_ENTRY struct, which
# contains 3 fields:
# - The "completion key". This is an opaque integer that we pick, and use
#   however is convenient.
# - pointer to the OVERLAPPED struct for the completed operation.
# - dwNumberOfBytesTransferred (an integer).
#
# And in addition, for regular I/O, the OVERLAPPED structure gets filled in
# with:
# - result code (named "Internal")
# - number of bytes transferred (named "InternalHigh"); usually redundant
#   with dwNumberOfBytesTransferred.
#
# There are also some other entries in OVERLAPPED which only matter on input:
# - Offset and OffsetHigh which are inputs to {Read,Write}File and
#   otherwise always zero
# - hEvent which is for if you aren't using IOCP; we always set it to zero.
#
# That describes the usual pattern for operations and the usual meaning of
# these struct fields, but really these are just some arbitrary chunks of
# bytes that get passed back and forth, so some operations like to overload
# them to mean something else.
#
# You can also directly queue an OVERLAPPED_ENTRY object to an IOCP by calling
# PostQueuedCompletionStatus. When you use this you get to set all the
# OVERLAPPED_ENTRY fields to arbitrary values.
#
# You can request to cancel any operation if you know which handle it was
# issued on + the OVERLAPPED struct that identifies it (via CancelIoEx). This
# request might fail because the operation has already completed, or it might
# be queued to happen in the background, so you only find out whether it
# succeeded or failed later, when we get back the notification for the
# operation being complete.
#
# There are three types of operations that we support:
#
# == Regular I/O operations on handles (e.g. files or named pipes) ==
#
# Implemented by: register_with_iocp, wait_overlapped
#
# To use these, you have to register the handle with your IOCP first. Once
# it's registered, any operations on that handle will automatically send
# completion events to that IOCP, with a completion key that you specify *when
# the handle is registered* (so you can't use different completion keys for
# different operations).
#
# We give these two dedicated completion keys: CKeys.WAIT_OVERLAPPED for
# regular operations, and CKeys.LATE_CANCEL that's used to make
# wait_overlapped cancellable even if the user forgot to call
# register_with_iocp. The problem here is that after we request the cancel,
# wait_overlapped keeps blocking until it sees the completion notification...
# but if the user forgot to register_with_iocp, then the completion will never
# come, so the cancellation will never resolve. To avoid this, whenever we try
# to cancel an I/O operation and the cancellation fails, we use
# PostQueuedCompletionStatus to send a CKeys.LATE_CANCEL notification. If this
# arrives before the real completion, we assume the user forgot to call
# register_with_iocp on their handle, and raise an error accordingly.
#
# == Socket state notifications ==
#
# Implemented by: wait_readable, wait_writable
#
# The public APIs that windows provides for this are all really awkward and
# don't integrate with IOCP. So we drop down to a lower level, and talk
# directly to the socket device driver in the kernel, which is called "AFD".
# Unfortunately, this is a totally undocumented internal API. Fortunately
# libuv also does this, so we can be pretty confident that MS won't break it
# on us, and there is a *little* bit of information out there if you go
# digging.
#
# Basically: we open a magic file that refers to the AFD driver, register the
# magic file with our IOCP, and then we can issue regular overlapped I/O
# operations on that handle. Specifically, the operation we use is called
# IOCTL_AFD_POLL, which lets us pass in a buffer describing which events we're
# interested in on a given socket (readable, writable, etc.). Later, when the
# operation completes, the kernel rewrites the buffer we passed in to record
# which events happened, and uses IOCP as normal to notify us that this
# operation has completed.
#
# Unfortunately, the Windows kernel seems to have bugs if you try to issue
# multiple simultaneous IOCTL_AFD_POLL operations on the same socket (see
# https://github.com/python-trio/trio/wiki/notes-to-self#afd-labpy).
# So if a user calls wait_readable and
# wait_writable at the same time, we have to combine those into a single
# IOCTL_AFD_POLL. This means we can't just use the wait_overlapped machinery.
# Instead we have some dedicated code to handle these operations, and a
# dedicated completion key CKeys.AFD_POLL.
#
# Sources of information:
# - https://github.com/python-trio/trio/issues/52
# - Wepoll: https://github.com/piscisaureus/wepoll/
# - libuv: https://github.com/libuv/libuv/
# - ReactOS: https://github.com/reactos/reactos/
# - Ancient leaked copies of the Windows NT and Winsock source code:
#   https://github.com/pustladi/Windows-2000/blob/661d000d50637ed6fab2329d30e31775046588a9/private/net/sockets/winsock2/wsp/msafd/select.c#L59-L655
#   https://github.com/metoo10987/WinNT4/blob/f5c14e6b42c8f45c20fe88d14c61f9d6e0386b8e/private/ntos/afd/poll.c#L68-L707
# - The WSAEventSelect docs (this exposes a finer-grained set of events than
#   select(), so if you squint you can treat it as a source of information on
#   the fine-grained AFD poll types)
#
#
# == Everything else ==
#
# There are also some weirder APIs for interacting with IOCP. For example, the
# "Job" API lets you specify an IOCP handle and "completion key", and then in
# the future whenever certain events happen it sends uses IOCP to send a
# notification. These notifications don't correspond to any particular
# operation; they're just spontaneous messages you get. The
# "dwNumberOfBytesTransferred" field gets repurposed to carry an identifier
# for the message type (e.g. JOB_OBJECT_MSG_EXIT_PROCESS), and the
# "lpOverlapped" field gets repurposed to carry some arbitrary data that
# depends on the message type (e.g. the pid of the process that exited).
#
# To handle these, we have monitor_completion_key, where we hand out an
# unassigned completion key, let users set it up however they want, and then
# get any events that arrive on that key.
#
# (Note: monitor_completion_key is not documented or fully baked; expect it to
# change in the future.)


# Our completion keys
class CKeys(enum.IntEnum):
    AFD_POLL = 0
    WAIT_OVERLAPPED = 1
    LATE_CANCEL = 2
    FORCE_WAKEUP = 3
    USER_DEFINED = 4  # and above


# AFD_POLL has a finer-grained set of events than other APIs. We collapse them
# down into Unix-style "readable" and "writable".
#
# Note: AFD_POLL_LOCAL_CLOSE isn't a reliable substitute for notify_closing(),
# because even if the user closes the socket *handle*, the socket *object*
# could still remain open, e.g. if the socket was dup'ed (possibly into
# another process). Explicitly calling notify_closing() guarantees that
# everyone waiting on the *handle* wakes up, which is what you'd expect.
#
# However, we can't avoid getting LOCAL_CLOSE notifications -- the kernel
# delivers them whether we ask for them or not -- so better to include them
# here for documentation, and so that when we check (delivered & requested) we
# get a match.

READABLE_FLAGS = (
    AFDPollFlags.AFD_POLL_RECEIVE
    | AFDPollFlags.AFD_POLL_ACCEPT
    | AFDPollFlags.AFD_POLL_DISCONNECT  # other side sent an EOF
    | AFDPollFlags.AFD_POLL_ABORT
    | AFDPollFlags.AFD_POLL_LOCAL_CLOSE
)

WRITABLE_FLAGS = (
    AFDPollFlags.AFD_POLL_SEND
    | AFDPollFlags.AFD_POLL_CONNECT_FAIL
    | AFDPollFlags.AFD_POLL_ABORT
    | AFDPollFlags.AFD_POLL_LOCAL_CLOSE
)


# Annoyingly, while the API makes it *seem* like you can happily issue as many
# independent AFD_POLL operations as you want without them interfering with
# each other, in fact if you issue two AFD_POLL operations for the same socket
# at the same time with notification going to the same IOCP port, then Windows
# gets super confused. For example, if we issue one operation from
# wait_readable, and another independent operation from wait_writable, then
# Windows may complete the wait_writable operation when the socket becomes
# readable.
#
# To avoid this, we have to coalesce all the operations on a single socket
# into one, and when the set of waiters changes we have to throw away the old
# operation and start a new one.
@attrs.define(eq=False)
class AFDWaiters:
    read_task: _core.Task | None = None
    write_task: _core.Task | None = None
    current_op: AFDPollOp | None = None


# Just used for internal type checking.
class _AFDHandle(Protocol):
    Handle: Handle
    Status: int
    Events: int


# Just used for internal type checking.
class _AFDPollInfo(Protocol):
    Timeout: int
    NumberOfHandles: int
    Exclusive: int
    Handles: list[_AFDHandle]


# We also need to bundle up all the info for a single op into a standalone
# object, because we need to keep all these objects alive until the operation
# finishes, even if we're throwing it away.
@attrs.frozen(eq=False)
class AFDPollOp:
    lpOverlapped: CData
    poll_info: _AFDPollInfo
    waiters: AFDWaiters
    afd_group: AFDGroup


# The Windows kernel has a weird issue when using AFD handles. If you have N
# instances of wait_readable/wait_writable registered with a single AFD handle,
# then cancelling any one of them takes something like O(N**2) time. So if we
# used just a single AFD handle, then cancellation would quickly become very
# expensive, e.g. a program with N active sockets would take something like
# O(N**3) time to unwind after control-C. The solution is to spread our sockets
# out over multiple AFD handles, so that N doesn't grow too large for any
# individual handle.
MAX_AFD_GROUP_SIZE = 500  # at 1000, the cubic scaling is just starting to bite


@attrs.define(eq=False)
class AFDGroup:
    size: int
    handle: Handle


assert not TYPE_CHECKING or sys.platform == "win32"


@attrs.frozen(eq=False)
class _WindowsStatistics:
    tasks_waiting_read: int
    tasks_waiting_write: int
    tasks_waiting_overlapped: int
    completion_key_monitors: int
    backend: Literal["windows"] = attrs.field(init=False, default="windows")


# Maximum number of events to dequeue from the completion port on each pass
# through the run loop. Somewhat arbitrary. Should be large enough to collect
# a good set of tasks on each loop, but not so large to waste tons of memory.
# (Each WindowsIOManager holds a buffer whose size is ~32x this number.)
MAX_EVENTS = 1000


def _check(success: T) -> T:
    if not success:
        raise_winerror()
    return success


def _get_underlying_socket(
    sock: _HasFileNo | int | Handle,
    *,
    which: WSAIoctls = WSAIoctls.SIO_BASE_HANDLE,
) -> Handle:
    if hasattr(sock, "fileno"):
        sock = sock.fileno()
    base_ptr = ffi.new("HANDLE *")
    out_size = ffi.new("DWORD *")
    failed = ws2_32.WSAIoctl(
        ffi.cast("SOCKET", sock),
        which,
        ffi.NULL,
        0,
        base_ptr,
        ffi.sizeof("HANDLE"),
        out_size,
        ffi.NULL,
        ffi.NULL,
    )
    if failed:
        code = ws2_32.WSAGetLastError()
        raise_winerror(code)
    return Handle(base_ptr[0])


def _get_base_socket(sock: _HasFileNo | int | Handle) -> Handle:
    # There is a development kit for LSPs called Komodia Redirector.
    # It does some unusual (some might say evil) things like intercepting
    # SIO_BASE_HANDLE (fails) and SIO_BSP_HANDLE_SELECT (returns the same
    # socket) in a misguided attempt to prevent bypassing it. It's been used
    # in malware including the infamous Lenovo Superfish incident from 2015,
    # but unfortunately is also used in some legitimate products such as
    # parental control tools and Astrill VPN. Komodia happens to not
    # block SIO_BSP_HANDLE_POLL, so we'll try SIO_BASE_HANDLE and fall back
    # to SIO_BSP_HANDLE_POLL if it doesn't work.
    # References:
    # - https://github.com/piscisaureus/wepoll/blob/0598a791bf9cbbf480793d778930fc635b044980/wepoll.c#L2223
    # - https://github.com/tokio-rs/mio/issues/1314

    while True:
        try:
            # If this is not a Komodia-intercepted socket, we can just use
            # SIO_BASE_HANDLE.
            return _get_underlying_socket(sock)
        except OSError as ex:
            if ex.winerror == ErrorCodes.ERROR_NOT_SOCKET:
                # SIO_BASE_HANDLE might fail even without LSP intervention,
                # if we get something that's not a socket.
                raise
            if hasattr(sock, "fileno"):
                sock = sock.fileno()
            sock = _handle(sock)
            next_sock = _get_underlying_socket(
                sock,
                which=WSAIoctls.SIO_BSP_HANDLE_POLL,
            )
            if next_sock == sock:
                # If BSP_HANDLE_POLL returns the same socket we already had,
                # then there's no layering going on and we need to fail
                # to prevent an infinite loop.
                raise RuntimeError(
                    "Unexpected network configuration detected: "
                    "SIO_BASE_HANDLE failed and SIO_BSP_HANDLE_POLL didn't "
                    "return a different socket. Please file a bug at "
                    "https://github.com/python-trio/trio/issues/new, "
                    "and include the output of running: "
                    "netsh winsock show catalog",
                ) from ex
            # Otherwise we've gotten at least one layer deeper, so
            # loop back around to keep digging.
            sock = next_sock


def _afd_helper_handle() -> Handle:
    # The "AFD" driver is exposed at the NT path "\Device\Afd". We're using
    # the Win32 CreateFile, though, so we have to pass a Win32 path. \\.\ is
    # how Win32 refers to the NT \GLOBAL??\ directory, and GLOBALROOT is a
    # symlink inside that directory that points to the root of the NT path
    # system. So by sticking that in front of the NT path, we get a Win32
    # path. Alternatively, we could use NtCreateFile directly, since it takes
    # an NT path. But we already wrap CreateFileW so this was easier.
    # References:
    #   https://blogs.msdn.microsoft.com/jeremykuhne/2016/05/02/dos-to-nt-a-paths-journey/
    #   https://stackoverflow.com/a/21704022
    #
    # I'm actually not sure what the \Trio part at the end of the path does.
    # Wepoll uses \Device\Afd\Wepoll, so I just copied them. (I'm guessing it
    # might be visible in some debug tools, and is otherwise arbitrary?)
    rawname = r"\\.\GLOBALROOT\Device\Afd\Trio".encode("utf-16le") + b"\0\0"
    rawname_buf = ffi.from_buffer(rawname)

    handle = kernel32.CreateFileW(
        ffi.cast("LPCWSTR", rawname_buf),
        FileFlags.SYNCHRONIZE,
        FileFlags.FILE_SHARE_READ | FileFlags.FILE_SHARE_WRITE,
        ffi.NULL,  # no security attributes
        FileFlags.OPEN_EXISTING,
        FileFlags.FILE_FLAG_OVERLAPPED,
        ffi.NULL,  # no template file
    )
    if handle == INVALID_HANDLE_VALUE:  # pragma: no cover
        raise_winerror()
    return handle


@attrs.frozen(slots=False)
class CompletionKeyEventInfo:
    lpOverlapped: CData
    dwNumberOfBytesTransferred: int


class WindowsIOManager:
    def __init__(self) -> None:
        # If this method raises an exception, then __del__ could run on a
        # half-initialized object. So we initialize everything that __del__
        # touches to safe values up front, before we do anything that can
        # fail.
        self._iocp = None
        self._all_afd_handles: list[Handle] = []

        self._iocp = _check(
            kernel32.CreateIoCompletionPort(INVALID_HANDLE_VALUE, ffi.NULL, 0, 0),
        )
        self._events = ffi.new("OVERLAPPED_ENTRY[]", MAX_EVENTS)

        self._vacant_afd_groups: set[AFDGroup] = set()
        # {lpOverlapped: AFDPollOp}
        self._afd_ops: dict[CData, AFDPollOp] = {}
        # {socket handle: AFDWaiters}
        self._afd_waiters: dict[Handle, AFDWaiters] = {}

        # {lpOverlapped: task}
        self._overlapped_waiters: dict[CData, _core.Task] = {}
        self._posted_too_late_to_cancel: set[CData] = set()

        self._completion_key_queues: dict[int, UnboundedQueue[object]] = {}
        self._completion_key_counter = itertools.count(CKeys.USER_DEFINED)

        with socket.socket() as s:
            # We assume we're not working with any LSP that changes
            # how select() is supposed to work. Validate this by
            # ensuring that the result of SIO_BSP_HANDLE_SELECT (the
            # LSP-hookable mechanism for "what should I use for
            # select()?") matches that of SIO_BASE_HANDLE ("what is
            # the real non-hooked underlying socket here?").
            #
            # This doesn't work for Komodia-based LSPs; see the comments
            # in _get_base_socket() for details. But we have special
            # logic for those, so we just skip this check if
            # SIO_BASE_HANDLE fails.

            # LSPs can in theory override this, but we believe that it never
            # actually happens in the wild (except Komodia)
            select_handle = _get_underlying_socket(
                s,
                which=WSAIoctls.SIO_BSP_HANDLE_SELECT,
            )
            try:
                # LSPs shouldn't override this...
                base_handle = _get_underlying_socket(s, which=WSAIoctls.SIO_BASE_HANDLE)
            except OSError:
                # But Komodia-based LSPs do anyway, in a way that causes
                # a failure with WSAEFAULT. We have special handling for
                # them in _get_base_socket(). Make sure it works.
                _get_base_socket(s)
            else:
                if base_handle != select_handle:
                    raise RuntimeError(
                        "Unexpected network configuration detected: "
                        "SIO_BASE_HANDLE and SIO_BSP_HANDLE_SELECT differ. "
                        "Please file a bug at "
                        "https://github.com/python-trio/trio/issues/new, "
                        "and include the output of running: "
                        "netsh winsock show catalog",
                    )

    def close(self) -> None:
        try:
            if self._iocp is not None:
                iocp = self._iocp
                self._iocp = None
                _check(kernel32.CloseHandle(iocp))
        finally:
            while self._all_afd_handles:
                afd_handle = self._all_afd_handles.pop()
                _check(kernel32.CloseHandle(afd_handle))

    def __del__(self) -> None:
        self.close()

    def statistics(self) -> _WindowsStatistics:
        tasks_waiting_read = 0
        tasks_waiting_write = 0
        for waiter in self._afd_waiters.values():
            if waiter.read_task is not None:
                tasks_waiting_read += 1
            if waiter.write_task is not None:
                tasks_waiting_write += 1
        return _WindowsStatistics(
            tasks_waiting_read=tasks_waiting_read,
            tasks_waiting_write=tasks_waiting_write,
            tasks_waiting_overlapped=len(self._overlapped_waiters),
            completion_key_monitors=len(self._completion_key_queues),
        )

    def force_wakeup(self) -> None:
        assert self._iocp is not None
        _check(
            kernel32.PostQueuedCompletionStatus(
                self._iocp,
                0,
                CKeys.FORCE_WAKEUP,
                ffi.NULL,
            ),
        )

    def get_events(self, timeout: float) -> EventResult:
        received = ffi.new("PULONG")
        milliseconds = round(1000 * timeout)
        if timeout > 0 and milliseconds == 0:
            milliseconds = 1
        try:
            assert self._iocp is not None
            _check(
                kernel32.GetQueuedCompletionStatusEx(
                    self._iocp,
                    self._events,
                    MAX_EVENTS,
                    received,
                    milliseconds,
                    0,
                ),
            )
        except OSError as exc:
            if exc.winerror != ErrorCodes.WAIT_TIMEOUT:  # pragma: no cover
                raise
            return 0
        result = received[0]
        assert isinstance(result, int)
        return result

    def process_events(self, received: EventResult) -> None:
        for i in range(received):
            entry = self._events[i]
            if entry.lpCompletionKey == CKeys.AFD_POLL:
                lpo = entry.lpOverlapped
                op = self._afd_ops.pop(lpo)
                waiters = op.waiters
                if waiters.current_op is not op:
                    # Stale op, nothing to do
                    pass
                else:
                    waiters.current_op = None
                    # I don't think this can happen, so if it does let's crash
                    # and get a debug trace.
                    if lpo.Internal != 0:  # pragma: no cover
                        code = ntdll.RtlNtStatusToDosError(lpo.Internal)
                        raise_winerror(code)
                    flags = op.poll_info.Handles[0].Events
                    if waiters.read_task and flags & READABLE_FLAGS:
                        _core.reschedule(waiters.read_task)
                        waiters.read_task = None
                    if waiters.write_task and flags & WRITABLE_FLAGS:
                        _core.reschedule(waiters.write_task)
                        waiters.write_task = None
                    self._refresh_afd(op.poll_info.Handles[0].Handle)
            elif entry.lpCompletionKey == CKeys.WAIT_OVERLAPPED:
                # Regular I/O event, dispatch on lpOverlapped
                waiter = self._overlapped_waiters.pop(entry.lpOverlapped)
                overlapped = entry.lpOverlapped
                transferred = entry.dwNumberOfBytesTransferred
                info = CompletionKeyEventInfo(
                    lpOverlapped=overlapped,
                    dwNumberOfBytesTransferred=transferred,
                )
                _core.reschedule(waiter, Value(info))
            elif entry.lpCompletionKey == CKeys.LATE_CANCEL:
                # Post made by a regular I/O event's abort_fn
                # after it failed to cancel the I/O. If we still
                # have a waiter with this lpOverlapped, we didn't
                # get the regular I/O completion and almost
                # certainly the user forgot to call
                # register_with_iocp.
                self._posted_too_late_to_cancel.remove(entry.lpOverlapped)
                try:
                    waiter = self._overlapped_waiters.pop(entry.lpOverlapped)
                except KeyError:
                    # Looks like the actual completion got here before this
                    # fallback post did -- we're in the "expected" case of
                    # too-late-to-cancel, where the user did nothing wrong.
                    # Nothing more to do.
                    pass
                else:
                    exc = _core.TrioInternalError(
                        f"Failed to cancel overlapped I/O in {waiter.name} and didn't "
                        "receive the completion either. Did you forget to "
                        "call register_with_iocp()?",
                    )
                    # Raising this out of handle_io ensures that
                    # the user will see our message even if some
                    # other task is in an uncancellable wait due
                    # to the same underlying forgot-to-register
                    # issue (if their CancelIoEx succeeds, we
                    # have no way of noticing that their completion
                    # won't arrive). Unfortunately it loses the
                    # task traceback. If you're debugging this
                    # error and can't tell where it's coming from,
                    # try changing this line to
                    # _core.reschedule(waiter, outcome.Error(exc))
                    raise exc
            elif entry.lpCompletionKey == CKeys.FORCE_WAKEUP:
                pass
            else:
                # dispatch on lpCompletionKey
                queue = self._completion_key_queues[entry.lpCompletionKey]
                overlapped = int(ffi.cast("uintptr_t", entry.lpOverlapped))
                transferred = entry.dwNumberOfBytesTransferred
                info = CompletionKeyEventInfo(
                    lpOverlapped=overlapped,
                    dwNumberOfBytesTransferred=transferred,
                )
                queue.put_nowait(info)

    def _register_with_iocp(self, handle_: int | CData, completion_key: int) -> None:
        handle = _handle(handle_)
        assert self._iocp is not None
        _check(kernel32.CreateIoCompletionPort(handle, self._iocp, completion_key, 0))
        # Supposedly this makes things slightly faster, by disabling the
        # ability to do WaitForSingleObject(handle). We would never want to do
        # that anyway, so might as well get the extra speed (if any).
        # Ref: http://www.lenholgate.com/blog/2009/09/interesting-blog-posts-on-high-performance-servers.html
        _check(
            kernel32.SetFileCompletionNotificationModes(
                handle,
                CompletionModes.FILE_SKIP_SET_EVENT_ON_HANDLE,
            ),
        )

    ################################################################
    # AFD stuff
    ################################################################

    def _refresh_afd(self, base_handle: Handle) -> None:
        waiters = self._afd_waiters[base_handle]
        if waiters.current_op is not None:
            afd_group = waiters.current_op.afd_group
            try:
                _check(
                    kernel32.CancelIoEx(
                        afd_group.handle,
                        waiters.current_op.lpOverlapped,
                    ),
                )
            except OSError as exc:
                if exc.winerror != ErrorCodes.ERROR_NOT_FOUND:
                    # I don't think this is possible, so if it happens let's
                    # crash noisily.
                    raise  # pragma: no cover
            waiters.current_op = None
            afd_group.size -= 1
            self._vacant_afd_groups.add(afd_group)

        flags = 0
        if waiters.read_task is not None:
            flags |= READABLE_FLAGS
        if waiters.write_task is not None:
            flags |= WRITABLE_FLAGS

        if not flags:
            del self._afd_waiters[base_handle]
        else:
            try:
                afd_group = self._vacant_afd_groups.pop()
            except KeyError:
                afd_group = AFDGroup(0, _afd_helper_handle())
                self._register_with_iocp(afd_group.handle, CKeys.AFD_POLL)
                self._all_afd_handles.append(afd_group.handle)
            self._vacant_afd_groups.add(afd_group)

            lpOverlapped = ffi.new("LPOVERLAPPED")

            poll_info = cast("_AFDPollInfo", ffi.new("AFD_POLL_INFO *"))
            poll_info.Timeout = 2**63 - 1  # INT64_MAX
            poll_info.NumberOfHandles = 1
            poll_info.Exclusive = 0
            poll_info.Handles[0].Handle = base_handle
            poll_info.Handles[0].Status = 0
            poll_info.Handles[0].Events = flags

            try:
                _check(
                    kernel32.DeviceIoControl(
                        afd_group.handle,
                        IoControlCodes.IOCTL_AFD_POLL,
                        cast("CType", poll_info),
                        ffi.sizeof("AFD_POLL_INFO"),
                        cast("CType", poll_info),
                        ffi.sizeof("AFD_POLL_INFO"),
                        ffi.NULL,
                        lpOverlapped,
                    ),
                )
            except OSError as exc:
                if exc.winerror != ErrorCodes.ERROR_IO_PENDING:
                    # This could happen if the socket handle got closed behind
                    # our back while a wait_* call was pending, and we tried
                    # to re-issue the call. Clear our state and wake up any
                    # pending calls.
                    del self._afd_waiters[base_handle]
                    # Do this last, because it could raise.
                    wake_all(waiters, exc)
                    return
            op = AFDPollOp(lpOverlapped, poll_info, waiters, afd_group)
            waiters.current_op = op
            self._afd_ops[lpOverlapped] = op
            afd_group.size += 1
            if afd_group.size >= MAX_AFD_GROUP_SIZE:
                self._vacant_afd_groups.remove(afd_group)

    async def _afd_poll(self, sock: _HasFileNo | int, mode: str) -> None:
        base_handle = _get_base_socket(sock)
        waiters = self._afd_waiters.get(base_handle)
        if waiters is None:
            waiters = AFDWaiters()
            self._afd_waiters[base_handle] = waiters
        if getattr(waiters, mode) is not None:
            raise _core.BusyResourceError
        setattr(waiters, mode, _core.current_task())
        # Could potentially raise if the handle is somehow invalid; that's OK,
        # we let it escape.
        self._refresh_afd(base_handle)

        def abort_fn(_: RaiseCancelT) -> Abort:
            setattr(waiters, mode, None)
            self._refresh_afd(base_handle)
            return _core.Abort.SUCCEEDED

        await _core.wait_task_rescheduled(abort_fn)

    @_public
    async def wait_readable(self, sock: _HasFileNo | int) -> None:
        """Block until the kernel reports that the given object is readable.

        On Unix systems, ``sock`` must either be an integer file descriptor,
        or else an object with a ``.fileno()`` method which returns an
        integer file descriptor. Any kind of file descriptor can be passed,
        though the exact semantics will depend on your kernel. For example,
        this probably won't do anything useful for on-disk files.

        On Windows systems, ``sock`` must either be an integer ``SOCKET``
        handle, or else an object with a ``.fileno()`` method which returns
        an integer ``SOCKET`` handle. File descriptors aren't supported,
        and neither are handles that refer to anything besides a
        ``SOCKET``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become readable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._afd_poll(sock, "read_task")

    @_public
    async def wait_writable(self, sock: _HasFileNo | int) -> None:
        """Block until the kernel reports that the given object is writable.

        See `wait_readable` for the definition of ``sock``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become writable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._afd_poll(sock, "write_task")

    @_public
    def notify_closing(self, handle: Handle | int | _HasFileNo) -> None:
        """Notify waiters of the given object that it will be closed.

        Call this before closing a file descriptor (on Unix) or socket (on
        Windows). This will cause any `wait_readable` or `wait_writable`
        calls on the given object to immediately wake up and raise
        `~trio.ClosedResourceError`.

        This doesn't actually close the object – you still have to do that
        yourself afterwards. Also, you want to be careful to make sure no
        new tasks start waiting on the object in between when you call this
        and when it's actually closed. So to close something properly, you
        usually want to do these steps in order:

        1. Explicitly mark the object as closed, so that any new attempts
           to use it will abort before they start.
        2. Call `notify_closing` to wake up any already-existing users.
        3. Actually close the object.

        It's also possible to do them in a different order if that's more
        convenient, *but only if* you make sure not to have any checkpoints in
        between the steps. This way they all happen in a single atomic
        step, so other tasks won't be able to tell what order they happened
        in anyway.
        """
        handle = _get_base_socket(handle)
        waiters = self._afd_waiters.get(handle)
        if waiters is not None:
            wake_all(waiters, _core.ClosedResourceError())
            self._refresh_afd(handle)

    ################################################################
    # Regular overlapped operations
    ################################################################

    @_public
    def register_with_iocp(self, handle: int | CData) -> None:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        self._register_with_iocp(handle, CKeys.WAIT_OVERLAPPED)

    @_public
    async def wait_overlapped(
        self,
        handle_: int | CData,
        lpOverlapped: CData | int,
    ) -> object:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        handle = _handle(handle_)
        if isinstance(lpOverlapped, int):  # TODO: test this line
            lpOverlapped = ffi.cast("LPOVERLAPPED", lpOverlapped)
        if lpOverlapped in self._overlapped_waiters:  # TODO: test this line
            raise _core.BusyResourceError(
                "another task is already waiting on that lpOverlapped",
            )
        task = _core.current_task()
        self._overlapped_waiters[lpOverlapped] = task
        raise_cancel = None

        def abort(raise_cancel_: RaiseCancelT) -> Abort:
            nonlocal raise_cancel
            raise_cancel = raise_cancel_
            try:
                _check(kernel32.CancelIoEx(handle, lpOverlapped))
            except OSError as exc:
                if exc.winerror == ErrorCodes.ERROR_NOT_FOUND:
                    assert self._iocp is not None
                    # Too late to cancel. If this happens because the
                    # operation is already completed, we don't need to do
                    # anything; we'll get a notification of that completion
                    # soon. But another possibility is that the operation was
                    # performed on a handle that wasn't registered with our
                    # IOCP (ie, the user forgot to call register_with_iocp),
                    # in which case we're just never going to see the
                    # completion. To avoid an uncancellable infinite sleep in
                    # the latter case, we'll PostQueuedCompletionStatus here,
                    # and if our post arrives before the original completion
                    # does, we'll assume the handle wasn't registered.
                    _check(
                        kernel32.PostQueuedCompletionStatus(
                            self._iocp,
                            0,
                            CKeys.LATE_CANCEL,
                            lpOverlapped,
                        ),
                    )
                    # Keep the lpOverlapped referenced so its address
                    # doesn't get reused until our posted completion
                    # status has been processed. Otherwise, we can
                    # get confused about which completion goes with
                    # which I/O.
                    self._posted_too_late_to_cancel.add(lpOverlapped)
                else:  # pragma: no cover
                    raise _core.TrioInternalError(
                        "CancelIoEx failed with unexpected error",
                    ) from exc
            return _core.Abort.FAILED

        # TODO: what type does this return?
        info = await _core.wait_task_rescheduled(abort)
        lpOverlappedTyped = cast("_Overlapped", lpOverlapped)
        if lpOverlappedTyped.Internal != 0:
            # the lpOverlapped reports the error as an NT status code,
            # which we must convert back to a Win32 error code before
            # it will produce the right sorts of exceptions
            code = ntdll.RtlNtStatusToDosError(lpOverlappedTyped.Internal)
            if code == ErrorCodes.ERROR_OPERATION_ABORTED:
                if raise_cancel is not None:
                    raise_cancel()
                else:
                    # We didn't request this cancellation, so assume
                    # it happened due to the underlying handle being
                    # closed before the operation could complete.
                    raise _core.ClosedResourceError("another task closed this resource")
            else:
                raise_winerror(code)
        return info

    async def _perform_overlapped(
        self,
        handle: int | CData,
        submit_fn: Callable[[_Overlapped], None],
    ) -> _Overlapped:
        # submit_fn(lpOverlapped) submits some I/O
        # it may raise an OSError with ERROR_IO_PENDING
        # the handle must already be registered using
        # register_with_iocp(handle)
        # This always does a schedule point, but it's possible that the
        # operation will not be cancellable, depending on how Windows is
        # feeling today. So we need to check for cancellation manually.
        await _core.checkpoint_if_cancelled()
        lpOverlapped = cast("_Overlapped", ffi.new("LPOVERLAPPED"))
        try:
            submit_fn(lpOverlapped)
        except OSError as exc:
            if exc.winerror != ErrorCodes.ERROR_IO_PENDING:
                raise
        await self.wait_overlapped(handle, cast("CData", lpOverlapped))
        return lpOverlapped

    @_public
    async def write_overlapped(
        self,
        handle: int | CData,
        data: Buffer,
        file_offset: int = 0,
    ) -> int:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        with ffi.from_buffer(data) as cbuf:

            def submit_write(lpOverlapped: _Overlapped) -> None:
                # yes, these are the real documented names
                offset_fields = lpOverlapped.DUMMYUNIONNAME.DUMMYSTRUCTNAME
                offset_fields.Offset = file_offset & 0xFFFFFFFF
                offset_fields.OffsetHigh = file_offset >> 32
                _check(
                    kernel32.WriteFile(
                        _handle(handle),
                        ffi.cast("LPCVOID", cbuf),
                        len(cbuf),
                        ffi.NULL,
                        lpOverlapped,
                    ),
                )

            lpOverlapped = await self._perform_overlapped(handle, submit_write)
            # this is "number of bytes transferred"
            return lpOverlapped.InternalHigh

    @_public
    async def readinto_overlapped(
        self,
        handle: int | CData,
        buffer: Buffer,
        file_offset: int = 0,
    ) -> int:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        with ffi.from_buffer(buffer, require_writable=True) as cbuf:

            def submit_read(lpOverlapped: _Overlapped) -> None:
                offset_fields = lpOverlapped.DUMMYUNIONNAME.DUMMYSTRUCTNAME
                offset_fields.Offset = file_offset & 0xFFFFFFFF
                offset_fields.OffsetHigh = file_offset >> 32
                _check(
                    kernel32.ReadFile(
                        _handle(handle),
                        ffi.cast("LPVOID", cbuf),
                        len(cbuf),
                        ffi.NULL,
                        lpOverlapped,
                    ),
                )

            lpOverlapped = await self._perform_overlapped(handle, submit_read)
            return lpOverlapped.InternalHigh

    ################################################################
    # Raw IOCP operations
    ################################################################

    @_public
    def current_iocp(self) -> int:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        assert self._iocp is not None
        return int(ffi.cast("uintptr_t", self._iocp))

    @contextmanager
    @_public
    def monitor_completion_key(self) -> Iterator[tuple[int, UnboundedQueue[object]]]:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__ and `#52
        <https://github.com/python-trio/trio/issues/52>`__.
        """
        key = next(self._completion_key_counter)
        queue = _core.UnboundedQueue[object]()
        self._completion_key_queues[key] = queue
        try:
            yield (key, queue)
        finally:
            del self._completion_key_queues[key]

# === NexusCore/openenv\Lib\site-packages\nltk\tgrep.py ===
#!/usr/bin/env python
#
# Natural Language Toolkit: TGrep search
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Will Roberts <wildwilhelm@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
============================================
 TGrep search implementation for NLTK trees
============================================

This module supports TGrep2 syntax for matching parts of NLTK Trees.
Note that many tgrep operators require the tree passed to be a
``ParentedTree``.

External links:

- `Tgrep tutorial <https://www.stanford.edu/dept/linguistics/corpora/cas-tut-tgrep.html>`_
- `Tgrep2 manual <http://tedlab.mit.edu/~dr/Tgrep2/tgrep2.pdf>`_
- `Tgrep2 source <http://tedlab.mit.edu/~dr/Tgrep2/>`_

Usage
=====

>>> from nltk.tree import ParentedTree
>>> from nltk.tgrep import tgrep_nodes, tgrep_positions
>>> tree = ParentedTree.fromstring('(S (NP (DT the) (JJ big) (NN dog)) (VP bit) (NP (DT a) (NN cat)))')
>>> list(tgrep_nodes('NN', [tree]))
[[ParentedTree('NN', ['dog']), ParentedTree('NN', ['cat'])]]
>>> list(tgrep_positions('NN', [tree]))
[[(0, 2), (2, 1)]]
>>> list(tgrep_nodes('DT', [tree]))
[[ParentedTree('DT', ['the']), ParentedTree('DT', ['a'])]]
>>> list(tgrep_nodes('DT $ JJ', [tree]))
[[ParentedTree('DT', ['the'])]]

This implementation adds syntax to select nodes based on their NLTK
tree position.  This syntax is ``N`` plus a Python tuple representing
the tree position.  For instance, ``N()``, ``N(0,)``, ``N(0,0)`` are
valid node selectors.  Example:

>>> tree = ParentedTree.fromstring('(S (NP (DT the) (JJ big) (NN dog)) (VP bit) (NP (DT a) (NN cat)))')
>>> tree[0,0]
ParentedTree('DT', ['the'])
>>> tree[0,0].treeposition()
(0, 0)
>>> list(tgrep_nodes('N(0,0)', [tree]))
[[ParentedTree('DT', ['the'])]]

Caveats:
========

- Link modifiers: "?" and "=" are not implemented.
- Tgrep compatibility: Using "@" for "!", "{" for "<", "}" for ">" are
  not implemented.
- The "=" and "~" links are not implemented.

Known Issues:
=============

- There are some issues with link relations involving leaf nodes
  (which are represented as bare strings in NLTK trees).  For
  instance, consider the tree::

      (S (A x))

  The search string ``* !>> S`` should select all nodes which are not
  dominated in some way by an ``S`` node (i.e., all nodes which are
  not descendants of an ``S``).  Clearly, in this tree, the only node
  which fulfills this criterion is the top node (since it is not
  dominated by anything).  However, the code here will find both the
  top node and the leaf node ``x``.  This is because we cannot recover
  the parent of the leaf, since it is stored as a bare string.

  A possible workaround, when performing this kind of search, would be
  to filter out all leaf nodes.

Implementation notes
====================

This implementation is (somewhat awkwardly) based on lambda functions
which are predicates on a node.  A predicate is a function which is
either True or False; using a predicate function, we can identify sets
of nodes with particular properties.  A predicate function, could, for
instance, return True only if a particular node has a label matching a
particular regular expression, and has a daughter node which has no
sisters.  Because tgrep2 search strings can do things statefully (such
as substituting in macros, and binding nodes with node labels), the
actual predicate function is declared with three arguments::

    pred = lambda n, m, l: return True # some logic here

``n``
    is a node in a tree; this argument must always be given

``m``
    contains a dictionary, mapping macro names onto predicate functions

``l``
    is a dictionary to map node labels onto nodes in the tree

``m`` and ``l`` are declared to default to ``None``, and so need not be
specified in a call to a predicate.  Predicates which call other
predicates must always pass the value of these arguments on.  The
top-level predicate (constructed by ``_tgrep_exprs_action``) binds the
macro definitions to ``m`` and initialises ``l`` to an empty dictionary.
"""

import functools
import re

try:
    import pyparsing
except ImportError:
    print("Warning: nltk.tgrep will not work without the `pyparsing` package")
    print("installed.")

import nltk.tree


class TgrepException(Exception):
    """Tgrep exception type."""

    pass


def ancestors(node):
    """
    Returns the list of all nodes dominating the given tree node.
    This method will not work with leaf nodes, since there is no way
    to recover the parent.
    """
    results = []
    try:
        current = node.parent()
    except AttributeError:
        # if node is a leaf, we cannot retrieve its parent
        return results
    while current:
        results.append(current)
        current = current.parent()
    return results


def unique_ancestors(node):
    """
    Returns the list of all nodes dominating the given node, where
    there is only a single path of descent.
    """
    results = []
    try:
        current = node.parent()
    except AttributeError:
        # if node is a leaf, we cannot retrieve its parent
        return results
    while current and len(current) == 1:
        results.append(current)
        current = current.parent()
    return results


def _descendants(node):
    """
    Returns the list of all nodes which are descended from the given
    tree node in some way.
    """
    try:
        treepos = node.treepositions()
    except AttributeError:
        return []
    return [node[x] for x in treepos[1:]]


def _leftmost_descendants(node):
    """
    Returns the set of all nodes descended in some way through
    left branches from this node.
    """
    try:
        treepos = node.treepositions()
    except AttributeError:
        return []
    return [node[x] for x in treepos[1:] if all(y == 0 for y in x)]


def _rightmost_descendants(node):
    """
    Returns the set of all nodes descended in some way through
    right branches from this node.
    """
    try:
        rightmost_leaf = max(node.treepositions())
    except AttributeError:
        return []
    return [node[rightmost_leaf[:i]] for i in range(1, len(rightmost_leaf) + 1)]


def _istree(obj):
    """Predicate to check whether `obj` is a nltk.tree.Tree."""
    return isinstance(obj, nltk.tree.Tree)


def _unique_descendants(node):
    """
    Returns the list of all nodes descended from the given node, where
    there is only a single path of descent.
    """
    results = []
    current = node
    while current and _istree(current) and len(current) == 1:
        current = current[0]
        results.append(current)
    return results


def _before(node):
    """
    Returns the set of all nodes that are before the given node.
    """
    try:
        pos = node.treeposition()
        tree = node.root()
    except AttributeError:
        return []
    return [tree[x] for x in tree.treepositions() if x[: len(pos)] < pos[: len(x)]]


def _immediately_before(node):
    """
    Returns the set of all nodes that are immediately before the given
    node.

    Tree node A immediately precedes node B if the last terminal
    symbol (word) produced by A immediately precedes the first
    terminal symbol produced by B.
    """
    try:
        pos = node.treeposition()
        tree = node.root()
    except AttributeError:
        return []
    # go "upwards" from pos until there is a place we can go to the left
    idx = len(pos) - 1
    while 0 <= idx and pos[idx] == 0:
        idx -= 1
    if idx < 0:
        return []
    pos = list(pos[: idx + 1])
    pos[-1] -= 1
    before = tree[pos]
    return [before] + _rightmost_descendants(before)


def _after(node):
    """
    Returns the set of all nodes that are after the given node.
    """
    try:
        pos = node.treeposition()
        tree = node.root()
    except AttributeError:
        return []
    return [tree[x] for x in tree.treepositions() if x[: len(pos)] > pos[: len(x)]]


def _immediately_after(node):
    """
    Returns the set of all nodes that are immediately after the given
    node.

    Tree node A immediately follows node B if the first terminal
    symbol (word) produced by A immediately follows the last
    terminal symbol produced by B.
    """
    try:
        pos = node.treeposition()
        tree = node.root()
        current = node.parent()
    except AttributeError:
        return []
    # go "upwards" from pos until there is a place we can go to the
    # right
    idx = len(pos) - 1
    while 0 <= idx and pos[idx] == len(current) - 1:
        idx -= 1
        current = current.parent()
    if idx < 0:
        return []
    pos = list(pos[: idx + 1])
    pos[-1] += 1
    after = tree[pos]
    return [after] + _leftmost_descendants(after)


def _tgrep_node_literal_value(node):
    """
    Gets the string value of a given parse tree node, for comparison
    using the tgrep node literal predicates.
    """
    return node.label() if _istree(node) else str(node)


def _tgrep_macro_use_action(_s, _l, tokens):
    """
    Builds a lambda function which looks up the macro name used.
    """
    assert len(tokens) == 1
    assert tokens[0][0] == "@"
    macro_name = tokens[0][1:]

    def macro_use(n, m=None, l=None):
        if m is None or macro_name not in m:
            raise TgrepException(f"macro {macro_name} not defined")
        return m[macro_name](n, m, l)

    return macro_use


def _tgrep_node_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    depending on the name of its node.
    """
    if tokens[0] == "'":
        # strip initial apostrophe (tgrep2 print command)
        tokens = tokens[1:]
    if len(tokens) > 1:
        # disjunctive definition of a node name
        assert list(set(tokens[1::2])) == ["|"]
        # recursively call self to interpret each node name definition
        tokens = [_tgrep_node_action(None, None, [node]) for node in tokens[::2]]
        # capture tokens and return the disjunction
        return (lambda t: lambda n, m=None, l=None: any(f(n, m, l) for f in t))(tokens)
    else:
        if hasattr(tokens[0], "__call__"):
            # this is a previously interpreted parenthetical node
            # definition (lambda function)
            return tokens[0]
        elif tokens[0] == "*" or tokens[0] == "__":
            return lambda n, m=None, l=None: True
        elif tokens[0].startswith('"'):
            assert tokens[0].endswith('"')
            node_lit = tokens[0][1:-1].replace('\\"', '"').replace("\\\\", "\\")
            return (
                lambda s: lambda n, m=None, l=None: _tgrep_node_literal_value(n) == s
            )(node_lit)
        elif tokens[0].startswith("/"):
            assert tokens[0].endswith("/")
            node_lit = tokens[0][1:-1]
            return (
                lambda r: lambda n, m=None, l=None: r.search(
                    _tgrep_node_literal_value(n)
                )
            )(re.compile(node_lit))
        elif tokens[0].startswith("i@"):
            node_func = _tgrep_node_action(_s, _l, [tokens[0][2:].lower()])
            return (
                lambda f: lambda n, m=None, l=None: f(
                    _tgrep_node_literal_value(n).lower()
                )
            )(node_func)
        else:
            return (
                lambda s: lambda n, m=None, l=None: _tgrep_node_literal_value(n) == s
            )(tokens[0])


def _tgrep_parens_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    from a parenthetical notation.
    """
    assert len(tokens) == 3
    assert tokens[0] == "("
    assert tokens[2] == ")"
    return tokens[1]


def _tgrep_nltk_tree_pos_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    which returns true if the node is located at a specific tree
    position.
    """
    # recover the tuple from the parsed string
    node_tree_position = tuple(int(x) for x in tokens if x.isdigit())
    # capture the node's tree position
    return (
        lambda i: lambda n, m=None, l=None: (
            hasattr(n, "treeposition") and n.treeposition() == i
        )
    )(node_tree_position)


def _tgrep_relation_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    depending on its relation to other nodes in the tree.
    """
    # process negation first if needed
    negated = False
    if tokens[0] == "!":
        negated = True
        tokens = tokens[1:]
    if tokens[0] == "[":
        # process square-bracketed relation expressions
        assert len(tokens) == 3
        assert tokens[2] == "]"
        retval = tokens[1]
    else:
        # process operator-node relation expressions
        assert len(tokens) == 2
        operator, predicate = tokens
        # A < B       A is the parent of (immediately dominates) B.
        if operator == "<":
            retval = lambda n, m=None, l=None: (
                _istree(n) and any(predicate(x, m, l) for x in n)
            )
        # A > B       A is the child of B.
        elif operator == ">":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and bool(n.parent())
                and predicate(n.parent(), m, l)
            )
        # A <, B      Synonymous with A <1 B.
        elif operator == "<," or operator == "<1":
            retval = lambda n, m=None, l=None: (
                _istree(n) and bool(list(n)) and predicate(n[0], m, l)
            )
        # A >, B      Synonymous with A >1 B.
        elif operator == ">," or operator == ">1":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and bool(n.parent())
                and (n is n.parent()[0])
                and predicate(n.parent(), m, l)
            )
        # A <N B      B is the Nth child of A (the first child is <1).
        elif operator[0] == "<" and operator[1:].isdigit():
            idx = int(operator[1:])
            # capture the index parameter
            retval = (
                lambda i: lambda n, m=None, l=None: (
                    _istree(n)
                    and bool(list(n))
                    and 0 <= i < len(n)
                    and predicate(n[i], m, l)
                )
            )(idx - 1)
        # A >N B      A is the Nth child of B (the first child is >1).
        elif operator[0] == ">" and operator[1:].isdigit():
            idx = int(operator[1:])
            # capture the index parameter
            retval = (
                lambda i: lambda n, m=None, l=None: (
                    hasattr(n, "parent")
                    and bool(n.parent())
                    and 0 <= i < len(n.parent())
                    and (n is n.parent()[i])
                    and predicate(n.parent(), m, l)
                )
            )(idx - 1)
        # A <' B      B is the last child of A (also synonymous with A <-1 B).
        # A <- B      B is the last child of A (synonymous with A <-1 B).
        elif operator == "<'" or operator == "<-" or operator == "<-1":
            retval = lambda n, m=None, l=None: (
                _istree(n) and bool(list(n)) and predicate(n[-1], m, l)
            )
        # A >' B      A is the last child of B (also synonymous with A >-1 B).
        # A >- B      A is the last child of B (synonymous with A >-1 B).
        elif operator == ">'" or operator == ">-" or operator == ">-1":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and bool(n.parent())
                and (n is n.parent()[-1])
                and predicate(n.parent(), m, l)
            )
        # A <-N B 	  B is the N th-to-last child of A (the last child is <-1).
        elif operator[:2] == "<-" and operator[2:].isdigit():
            idx = -int(operator[2:])
            # capture the index parameter
            retval = (
                lambda i: lambda n, m=None, l=None: (
                    _istree(n)
                    and bool(list(n))
                    and 0 <= (i + len(n)) < len(n)
                    and predicate(n[i + len(n)], m, l)
                )
            )(idx)
        # A >-N B 	  A is the N th-to-last child of B (the last child is >-1).
        elif operator[:2] == ">-" and operator[2:].isdigit():
            idx = -int(operator[2:])
            # capture the index parameter
            retval = (
                lambda i: lambda n, m=None, l=None: (
                    hasattr(n, "parent")
                    and bool(n.parent())
                    and 0 <= (i + len(n.parent())) < len(n.parent())
                    and (n is n.parent()[i + len(n.parent())])
                    and predicate(n.parent(), m, l)
                )
            )(idx)
        # A <: B      B is the only child of A
        elif operator == "<:":
            retval = lambda n, m=None, l=None: (
                _istree(n) and len(n) == 1 and predicate(n[0], m, l)
            )
        # A >: B      A is the only child of B.
        elif operator == ">:":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and bool(n.parent())
                and len(n.parent()) == 1
                and predicate(n.parent(), m, l)
            )
        # A << B      A dominates B (A is an ancestor of B).
        elif operator == "<<":
            retval = lambda n, m=None, l=None: (
                _istree(n) and any(predicate(x, m, l) for x in _descendants(n))
            )
        # A >> B      A is dominated by B (A is a descendant of B).
        elif operator == ">>":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in ancestors(n)
            )
        # A <<, B     B is a left-most descendant of A.
        elif operator == "<<," or operator == "<<1":
            retval = lambda n, m=None, l=None: (
                _istree(n) and any(predicate(x, m, l) for x in _leftmost_descendants(n))
            )
        # A >>, B     A is a left-most descendant of B.
        elif operator == ">>,":
            retval = lambda n, m=None, l=None: any(
                (predicate(x, m, l) and n in _leftmost_descendants(x))
                for x in ancestors(n)
            )
        # A <<' B     B is a right-most descendant of A.
        elif operator == "<<'":
            retval = lambda n, m=None, l=None: (
                _istree(n)
                and any(predicate(x, m, l) for x in _rightmost_descendants(n))
            )
        # A >>' B     A is a right-most descendant of B.
        elif operator == ">>'":
            retval = lambda n, m=None, l=None: any(
                (predicate(x, m, l) and n in _rightmost_descendants(x))
                for x in ancestors(n)
            )
        # A <<: B     There is a single path of descent from A and B is on it.
        elif operator == "<<:":
            retval = lambda n, m=None, l=None: (
                _istree(n) and any(predicate(x, m, l) for x in _unique_descendants(n))
            )
        # A >>: B     There is a single path of descent from B and A is on it.
        elif operator == ">>:":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in unique_ancestors(n)
            )
        # A . B       A immediately precedes B.
        elif operator == ".":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in _immediately_after(n)
            )
        # A , B       A immediately follows B.
        elif operator == ",":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in _immediately_before(n)
            )
        # A .. B      A precedes B.
        elif operator == "..":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in _after(n)
            )
        # A ,, B      A follows B.
        elif operator == ",,":
            retval = lambda n, m=None, l=None: any(
                predicate(x, m, l) for x in _before(n)
            )
        # A $ B       A is a sister of B (and A != B).
        elif operator == "$" or operator == "%":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and bool(n.parent())
                and any(predicate(x, m, l) for x in n.parent() if x is not n)
            )
        # A $. B      A is a sister of and immediately precedes B.
        elif operator == "$." or operator == "%.":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "right_sibling")
                and bool(n.right_sibling())
                and predicate(n.right_sibling(), m, l)
            )
        # A $, B      A is a sister of and immediately follows B.
        elif operator == "$," or operator == "%,":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "left_sibling")
                and bool(n.left_sibling())
                and predicate(n.left_sibling(), m, l)
            )
        # A $.. B     A is a sister of and precedes B.
        elif operator == "$.." or operator == "%..":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and hasattr(n, "parent_index")
                and bool(n.parent())
                and any(predicate(x, m, l) for x in n.parent()[n.parent_index() + 1 :])
            )
        # A $,, B     A is a sister of and follows B.
        elif operator == "$,," or operator == "%,,":
            retval = lambda n, m=None, l=None: (
                hasattr(n, "parent")
                and hasattr(n, "parent_index")
                and bool(n.parent())
                and any(predicate(x, m, l) for x in n.parent()[: n.parent_index()])
            )
        else:
            raise TgrepException(f'cannot interpret tgrep operator "{operator}"')
    # now return the built function
    if negated:
        return (lambda r: (lambda n, m=None, l=None: not r(n, m, l)))(retval)
    else:
        return retval


def _tgrep_conjunction_action(_s, _l, tokens, join_char="&"):
    """
    Builds a lambda function representing a predicate on a tree node
    from the conjunction of several other such lambda functions.

    This is prototypically called for expressions like
    (`tgrep_rel_conjunction`)::

        < NP & < AP < VP

    where tokens is a list of predicates representing the relations
    (`< NP`, `< AP`, and `< VP`), possibly with the character `&`
    included (as in the example here).

    This is also called for expressions like (`tgrep_node_expr2`)::

        NP < NN
        S=s < /NP/=n : s < /VP/=v : n .. v

    tokens[0] is a tgrep_expr predicate; tokens[1:] are an (optional)
    list of segmented patterns (`tgrep_expr_labeled`, processed by
    `_tgrep_segmented_pattern_action`).
    """
    # filter out the ampersand
    tokens = [x for x in tokens if x != join_char]
    if len(tokens) == 1:
        return tokens[0]
    else:
        return (
            lambda ts: lambda n, m=None, l=None: all(
                predicate(n, m, l) for predicate in ts
            )
        )(tokens)


def _tgrep_segmented_pattern_action(_s, _l, tokens):
    """
    Builds a lambda function representing a segmented pattern.

    Called for expressions like (`tgrep_expr_labeled`)::

        =s .. =v < =n

    This is a segmented pattern, a tgrep2 expression which begins with
    a node label.

    The problem is that for segemented_pattern_action (': =v < =s'),
    the first element (in this case, =v) is specifically selected by
    virtue of matching a particular node in the tree; to retrieve
    the node, we need the label, not a lambda function.  For node
    labels inside a tgrep_node_expr, we need a lambda function which
    returns true if the node visited is the same as =v.

    We solve this by creating two copies of a node_label_use in the
    grammar; the label use inside a tgrep_expr_labeled has a separate
    parse action to the pred use inside a node_expr.  See
    `_tgrep_node_label_use_action` and
    `_tgrep_node_label_pred_use_action`.
    """
    # tokens[0] is a string containing the node label
    node_label = tokens[0]
    # tokens[1:] is an (optional) list of predicates which must all
    # hold of the bound node
    reln_preds = tokens[1:]

    def pattern_segment_pred(n, m=None, l=None):
        """This predicate function ignores its node argument."""
        # look up the bound node using its label
        if l is None or node_label not in l:
            raise TgrepException(f"node_label ={node_label} not bound in pattern")
        node = l[node_label]
        # match the relation predicates against the node
        return all(pred(node, m, l) for pred in reln_preds)

    return pattern_segment_pred


def _tgrep_node_label_use_action(_s, _l, tokens):
    """
    Returns the node label used to begin a tgrep_expr_labeled.  See
    `_tgrep_segmented_pattern_action`.

    Called for expressions like (`tgrep_node_label_use`)::

        =s

    when they appear as the first element of a `tgrep_expr_labeled`
    expression (see `_tgrep_segmented_pattern_action`).

    It returns the node label.
    """
    assert len(tokens) == 1
    assert tokens[0].startswith("=")
    return tokens[0][1:]


def _tgrep_node_label_pred_use_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    which describes the use of a previously bound node label.

    Called for expressions like (`tgrep_node_label_use_pred`)::

        =s

    when they appear inside a tgrep_node_expr (for example, inside a
    relation).  The predicate returns true if and only if its node
    argument is identical the the node looked up in the node label
    dictionary using the node's label.
    """
    assert len(tokens) == 1
    assert tokens[0].startswith("=")
    node_label = tokens[0][1:]

    def node_label_use_pred(n, m=None, l=None):
        # look up the bound node using its label
        if l is None or node_label not in l:
            raise TgrepException(f"node_label ={node_label} not bound in pattern")
        node = l[node_label]
        # truth means the given node is this node
        return n is node

    return node_label_use_pred


def _tgrep_bind_node_label_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    which can optionally bind a matching node into the tgrep2 string's
    label_dict.

    Called for expressions like (`tgrep_node_expr2`)::

        /NP/
        @NP=n
    """
    # tokens[0] is a tgrep_node_expr
    if len(tokens) == 1:
        return tokens[0]
    else:
        # if present, tokens[1] is the character '=', and tokens[2] is
        # a tgrep_node_label, a string value containing the node label
        assert len(tokens) == 3
        assert tokens[1] == "="
        node_pred = tokens[0]
        node_label = tokens[2]

        def node_label_bind_pred(n, m=None, l=None):
            if node_pred(n, m, l):
                # bind `n` into the dictionary `l`
                if l is None:
                    raise TgrepException(
                        "cannot bind node_label {}: label_dict is None".format(
                            node_label
                        )
                    )
                l[node_label] = n
                return True
            else:
                return False

        return node_label_bind_pred


def _tgrep_rel_disjunction_action(_s, _l, tokens):
    """
    Builds a lambda function representing a predicate on a tree node
    from the disjunction of several other such lambda functions.
    """
    # filter out the pipe
    tokens = [x for x in tokens if x != "|"]
    if len(tokens) == 1:
        return tokens[0]
    elif len(tokens) == 2:
        return (lambda a, b: lambda n, m=None, l=None: a(n, m, l) or b(n, m, l))(
            tokens[0], tokens[1]
        )


def _macro_defn_action(_s, _l, tokens):
    """
    Builds a dictionary structure which defines the given macro.
    """
    assert len(tokens) == 3
    assert tokens[0] == "@"
    return {tokens[1]: tokens[2]}


def _tgrep_exprs_action(_s, _l, tokens):
    """
    This is the top-lebel node in a tgrep2 search string; the
    predicate function it returns binds together all the state of a
    tgrep2 search string.

    Builds a lambda function representing a predicate on a tree node
    from the disjunction of several tgrep expressions.  Also handles
    macro definitions and macro name binding, and node label
    definitions and node label binding.
    """
    if len(tokens) == 1:
        return lambda n, m=None, l=None: tokens[0](n, None, {})
    # filter out all the semicolons
    tokens = [x for x in tokens if x != ";"]
    # collect all macro definitions
    macro_dict = {}
    macro_defs = [tok for tok in tokens if isinstance(tok, dict)]
    for macro_def in macro_defs:
        macro_dict.update(macro_def)
    # collect all tgrep expressions
    tgrep_exprs = [tok for tok in tokens if not isinstance(tok, dict)]

    # create a new scope for the node label dictionary
    def top_level_pred(n, m=macro_dict, l=None):
        label_dict = {}
        # bind macro definitions and OR together all tgrep_exprs
        return any(predicate(n, m, label_dict) for predicate in tgrep_exprs)

    return top_level_pred


def _build_tgrep_parser(set_parse_actions=True):
    """
    Builds a pyparsing-based parser object for tokenizing and
    interpreting tgrep search strings.
    """
    tgrep_op = pyparsing.Optional("!") + pyparsing.Regex("[$%,.<>][%,.<>0-9-':]*")
    tgrep_qstring = pyparsing.QuotedString(
        quoteChar='"', escChar="\\", unquoteResults=False
    )
    tgrep_node_regex = pyparsing.QuotedString(
        quoteChar="/", escChar="\\", unquoteResults=False
    )
    tgrep_qstring_icase = pyparsing.Regex('i@\\"(?:[^"\\n\\r\\\\]|(?:\\\\.))*\\"')
    tgrep_node_regex_icase = pyparsing.Regex("i@\\/(?:[^/\\n\\r\\\\]|(?:\\\\.))*\\/")
    tgrep_node_literal = pyparsing.Regex("[^][ \r\t\n;:.,&|<>()$!@%'^=]+")
    tgrep_expr = pyparsing.Forward()
    tgrep_relations = pyparsing.Forward()
    tgrep_parens = pyparsing.Literal("(") + tgrep_expr + ")"
    tgrep_nltk_tree_pos = (
        pyparsing.Literal("N(")
        + pyparsing.Optional(
            pyparsing.Word(pyparsing.nums)
            + ","
            + pyparsing.Optional(
                pyparsing.delimitedList(pyparsing.Word(pyparsing.nums), delim=",")
                + pyparsing.Optional(",")
            )
        )
        + ")"
    )
    tgrep_node_label = pyparsing.Regex("[A-Za-z0-9]+")
    tgrep_node_label_use = pyparsing.Combine("=" + tgrep_node_label)
    # see _tgrep_segmented_pattern_action
    tgrep_node_label_use_pred = tgrep_node_label_use.copy()
    macro_name = pyparsing.Regex("[^];:.,&|<>()[$!@%'^=\r\t\n ]+")
    macro_name.setWhitespaceChars("")
    macro_use = pyparsing.Combine("@" + macro_name)
    tgrep_node_expr = (
        tgrep_node_label_use_pred
        | macro_use
        | tgrep_nltk_tree_pos
        | tgrep_qstring_icase
        | tgrep_node_regex_icase
        | tgrep_qstring
        | tgrep_node_regex
        | "*"
        | tgrep_node_literal
    )
    tgrep_node_expr2 = (
        tgrep_node_expr
        + pyparsing.Literal("=").setWhitespaceChars("")
        + tgrep_node_label.copy().setWhitespaceChars("")
    ) | tgrep_node_expr
    tgrep_node = tgrep_parens | (
        pyparsing.Optional("'")
        + tgrep_node_expr2
        + pyparsing.ZeroOrMore("|" + tgrep_node_expr)
    )
    tgrep_brackets = pyparsing.Optional("!") + "[" + tgrep_relations + "]"
    tgrep_relation = tgrep_brackets | (tgrep_op + tgrep_node)
    tgrep_rel_conjunction = pyparsing.Forward()
    tgrep_rel_conjunction << (
        tgrep_relation
        + pyparsing.ZeroOrMore(pyparsing.Optional("&") + tgrep_rel_conjunction)
    )
    tgrep_relations << tgrep_rel_conjunction + pyparsing.ZeroOrMore(
        "|" + tgrep_relations
    )
    tgrep_expr << tgrep_node + pyparsing.Optional(tgrep_relations)
    tgrep_expr_labeled = tgrep_node_label_use + pyparsing.Optional(tgrep_relations)
    tgrep_expr2 = tgrep_expr + pyparsing.ZeroOrMore(":" + tgrep_expr_labeled)
    macro_defn = (
        pyparsing.Literal("@") + pyparsing.White().suppress() + macro_name + tgrep_expr2
    )
    tgrep_exprs = (
        pyparsing.Optional(macro_defn + pyparsing.ZeroOrMore(";" + macro_defn) + ";")
        + tgrep_expr2
        + pyparsing.ZeroOrMore(";" + (macro_defn | tgrep_expr2))
        + pyparsing.ZeroOrMore(";").suppress()
    )
    if set_parse_actions:
        tgrep_node_label_use.setParseAction(_tgrep_node_label_use_action)
        tgrep_node_label_use_pred.setParseAction(_tgrep_node_label_pred_use_action)
        macro_use.setParseAction(_tgrep_macro_use_action)
        tgrep_node.setParseAction(_tgrep_node_action)
        tgrep_node_expr2.setParseAction(_tgrep_bind_node_label_action)
        tgrep_parens.setParseAction(_tgrep_parens_action)
        tgrep_nltk_tree_pos.setParseAction(_tgrep_nltk_tree_pos_action)
        tgrep_relation.setParseAction(_tgrep_relation_action)
        tgrep_rel_conjunction.setParseAction(_tgrep_conjunction_action)
        tgrep_relations.setParseAction(_tgrep_rel_disjunction_action)
        macro_defn.setParseAction(_macro_defn_action)
        # the whole expression is also the conjunction of two
        # predicates: the first node predicate, and the remaining
        # relation predicates
        tgrep_expr.setParseAction(_tgrep_conjunction_action)
        tgrep_expr_labeled.setParseAction(_tgrep_segmented_pattern_action)
        tgrep_expr2.setParseAction(
            functools.partial(_tgrep_conjunction_action, join_char=":")
        )
        tgrep_exprs.setParseAction(_tgrep_exprs_action)
    return tgrep_exprs.ignore("#" + pyparsing.restOfLine)


def tgrep_tokenize(tgrep_string):
    """
    Tokenizes a TGrep search string into separate tokens.
    """
    parser = _build_tgrep_parser(False)
    if isinstance(tgrep_string, bytes):
        tgrep_string = tgrep_string.decode()
    return list(parser.parseString(tgrep_string))


def tgrep_compile(tgrep_string):
    """
    Parses (and tokenizes, if necessary) a TGrep search string into a
    lambda function.
    """
    parser = _build_tgrep_parser(True)
    if isinstance(tgrep_string, bytes):
        tgrep_string = tgrep_string.decode()
    return list(parser.parseString(tgrep_string, parseAll=True))[0]


def treepositions_no_leaves(tree):
    """
    Returns all the tree positions in the given tree which are not
    leaf nodes.
    """
    treepositions = tree.treepositions()
    # leaves are treeposition tuples that are not prefixes of any
    # other treeposition
    prefixes = set()
    for pos in treepositions:
        for length in range(len(pos)):
            prefixes.add(pos[:length])
    return [pos for pos in treepositions if pos in prefixes]


def tgrep_positions(pattern, trees, search_leaves=True):
    """
    Return the tree positions in the trees which match the given pattern.

    :param pattern: a tgrep search pattern
    :type pattern: str or output of tgrep_compile()
    :param trees: a sequence of NLTK trees (usually ParentedTrees)
    :type trees: iter(ParentedTree) or iter(Tree)
    :param search_leaves: whether to return matching leaf nodes
    :type search_leaves: bool
    :rtype: iter(tree positions)
    """

    if isinstance(pattern, (bytes, str)):
        pattern = tgrep_compile(pattern)

    for tree in trees:
        try:
            if search_leaves:
                positions = tree.treepositions()
            else:
                positions = treepositions_no_leaves(tree)
            yield [position for position in positions if pattern(tree[position])]
        except AttributeError:
            yield []


def tgrep_nodes(pattern, trees, search_leaves=True):
    """
    Return the tree nodes in the trees which match the given pattern.

    :param pattern: a tgrep search pattern
    :type pattern: str or output of tgrep_compile()
    :param trees: a sequence of NLTK trees (usually ParentedTrees)
    :type trees: iter(ParentedTree) or iter(Tree)
    :param search_leaves: whether to return matching leaf nodes
    :type search_leaves: bool
    :rtype: iter(tree nodes)
    """

    if isinstance(pattern, (bytes, str)):
        pattern = tgrep_compile(pattern)

    for tree in trees:
        try:
            if search_leaves:
                positions = tree.treepositions()
            else:
                positions = treepositions_no_leaves(tree)
            yield [tree[position] for position in positions if pattern(tree[position])]
        except AttributeError:
            yield []

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\S__i_l_f.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import floatToFixedToStr
from fontTools.misc.textTools import byteord, safeEval

# from itertools import *
from . import DefaultTable
from . import grUtils
from array import array
from functools import reduce
import struct, re, sys

Silf_hdr_format = """
    >
    version:            16.16F
"""

Silf_hdr_format_3 = """
    >
    version:            16.16F
    compilerVersion:    L
    numSilf:            H
                        x
                        x
"""

Silf_part1_format_v3 = """
    >
    ruleVersion:        16.16F
    passOffset:         H
    pseudosOffset:      H
"""

Silf_part1_format = """
    >
    maxGlyphID:         H
    extraAscent:        h
    extraDescent:       h
    numPasses:          B
    iSubst:             B
    iPos:               B
    iJust:              B
    iBidi:              B
    flags:              B
    maxPreContext:      B
    maxPostContext:     B
    attrPseudo:         B
    attrBreakWeight:    B
    attrDirectionality: B
    attrMirroring:      B
    attrSkipPasses:     B
    numJLevels:         B
"""

Silf_justify_format = """
    >
    attrStretch:        B
    attrShrink:         B
    attrStep:           B
    attrWeight:         B
    runto:              B
                        x
                        x
                        x
"""

Silf_part2_format = """
    >
    numLigComp:         H
    numUserDefn:        B
    maxCompPerLig:      B
    direction:          B
    attCollisions:      B
                        x
                        x
                        x
    numCritFeatures:    B
"""

Silf_pseudomap_format = """
    >
    unicode:            L
    nPseudo:            H
"""

Silf_pseudomap_format_h = """
    >
    unicode:            H
    nPseudo:            H
"""

Silf_classmap_format = """
    >
    numClass:           H
    numLinear:          H
"""

Silf_lookupclass_format = """
    >
    numIDs:             H
    searchRange:        H
    entrySelector:      H
    rangeShift:         H
"""

Silf_lookuppair_format = """
    >
    glyphId:            H
    index:              H
"""

Silf_pass_format = """
    >
    flags:              B
    maxRuleLoop:        B
    maxRuleContext:     B
    maxBackup:          B
    numRules:           H
    fsmOffset:          H
    pcCode:             L
    rcCode:             L
    aCode:              L
    oDebug:             L
    numRows:            H
    numTransitional:    H
    numSuccess:         H
    numColumns:         H
"""

aCode_info = (
    ("NOP", 0),
    ("PUSH_BYTE", "b"),
    ("PUSH_BYTE_U", "B"),
    ("PUSH_SHORT", ">h"),
    ("PUSH_SHORT_U", ">H"),
    ("PUSH_LONG", ">L"),
    ("ADD", 0),
    ("SUB", 0),
    ("MUL", 0),
    ("DIV", 0),
    ("MIN", 0),
    ("MAX", 0),
    ("NEG", 0),
    ("TRUNC8", 0),
    ("TRUNC16", 0),
    ("COND", 0),
    ("AND", 0),  # x10
    ("OR", 0),
    ("NOT", 0),
    ("EQUAL", 0),
    ("NOT_EQ", 0),
    ("LESS", 0),
    ("GTR", 0),
    ("LESS_EQ", 0),
    ("GTR_EQ", 0),
    ("NEXT", 0),
    ("NEXT_N", "b"),
    ("COPY_NEXT", 0),
    ("PUT_GLYPH_8BIT_OBS", "B"),
    ("PUT_SUBS_8BIT_OBS", "bBB"),
    ("PUT_COPY", "b"),
    ("INSERT", 0),
    ("DELETE", 0),  # x20
    ("ASSOC", -1),
    ("CNTXT_ITEM", "bB"),
    ("ATTR_SET", "B"),
    ("ATTR_ADD", "B"),
    ("ATTR_SUB", "B"),
    ("ATTR_SET_SLOT", "B"),
    ("IATTR_SET_SLOT", "BB"),
    ("PUSH_SLOT_ATTR", "Bb"),
    ("PUSH_GLYPH_ATTR_OBS", "Bb"),
    ("PUSH_GLYPH_METRIC", "Bbb"),
    ("PUSH_FEAT", "Bb"),
    ("PUSH_ATT_TO_GATTR_OBS", "Bb"),
    ("PUSH_ATT_TO_GLYPH_METRIC", "Bbb"),
    ("PUSH_ISLOT_ATTR", "Bbb"),
    ("PUSH_IGLYPH_ATTR", "Bbb"),
    ("POP_RET", 0),  # x30
    ("RET_ZERO", 0),
    ("RET_TRUE", 0),
    ("IATTR_SET", "BB"),
    ("IATTR_ADD", "BB"),
    ("IATTR_SUB", "BB"),
    ("PUSH_PROC_STATE", "B"),
    ("PUSH_VERSION", 0),
    ("PUT_SUBS", ">bHH"),
    ("PUT_SUBS2", 0),
    ("PUT_SUBS3", 0),
    ("PUT_GLYPH", ">H"),
    ("PUSH_GLYPH_ATTR", ">Hb"),
    ("PUSH_ATT_TO_GLYPH_ATTR", ">Hb"),
    ("BITOR", 0),
    ("BITAND", 0),
    ("BITNOT", 0),  # x40
    ("BITSET", ">HH"),
    ("SET_FEAT", "Bb"),
)
aCode_map = dict([(x[0], (i, x[1])) for i, x in enumerate(aCode_info)])


def disassemble(aCode):
    codelen = len(aCode)
    pc = 0
    res = []
    while pc < codelen:
        opcode = byteord(aCode[pc : pc + 1])
        if opcode > len(aCode_info):
            instr = aCode_info[0]
        else:
            instr = aCode_info[opcode]
        pc += 1
        if instr[1] != 0 and pc >= codelen:
            return res
        if instr[1] == -1:
            count = byteord(aCode[pc])
            fmt = "%dB" % count
            pc += 1
        elif instr[1] == 0:
            fmt = ""
        else:
            fmt = instr[1]
        if fmt == "":
            res.append(instr[0])
            continue
        parms = struct.unpack_from(fmt, aCode[pc:])
        res.append(instr[0] + "(" + ", ".join(map(str, parms)) + ")")
        pc += struct.calcsize(fmt)
    return res


instre = re.compile(r"^\s*([^(]+)\s*(?:\(([^)]+)\))?")


def assemble(instrs):
    res = b""
    for inst in instrs:
        m = instre.match(inst)
        if not m or not m.group(1) in aCode_map:
            continue
        opcode, parmfmt = aCode_map[m.group(1)]
        res += struct.pack("B", opcode)
        if m.group(2):
            if parmfmt == 0:
                continue
            parms = [int(x) for x in re.split(r",\s*", m.group(2))]
            if parmfmt == -1:
                l = len(parms)
                res += struct.pack(("%dB" % (l + 1)), l, *parms)
            else:
                res += struct.pack(parmfmt, *parms)
    return res


def writecode(tag, writer, instrs):
    writer.begintag(tag)
    writer.newline()
    for l in disassemble(instrs):
        writer.write(l)
        writer.newline()
    writer.endtag(tag)
    writer.newline()


def readcode(content):
    res = []
    for e in content_string(content).split("\n"):
        e = e.strip()
        if not len(e):
            continue
        res.append(e)
    return assemble(res)


attrs_info = (
    "flags",
    "extraAscent",
    "extraDescent",
    "maxGlyphID",
    "numLigComp",
    "numUserDefn",
    "maxCompPerLig",
    "direction",
    "lbGID",
)
attrs_passindexes = ("iSubst", "iPos", "iJust", "iBidi")
attrs_contexts = ("maxPreContext", "maxPostContext")
attrs_attributes = (
    "attrPseudo",
    "attrBreakWeight",
    "attrDirectionality",
    "attrMirroring",
    "attrSkipPasses",
    "attCollisions",
)
pass_attrs_info = (
    "flags",
    "maxRuleLoop",
    "maxRuleContext",
    "maxBackup",
    "minRulePreContext",
    "maxRulePreContext",
    "collisionThreshold",
)
pass_attrs_fsm = ("numRows", "numTransitional", "numSuccess", "numColumns")


def writesimple(tag, self, writer, *attrkeys):
    attrs = dict([(k, getattr(self, k)) for k in attrkeys])
    writer.simpletag(tag, **attrs)
    writer.newline()


def getSimple(self, attrs, *attr_list):
    for k in attr_list:
        if k in attrs:
            setattr(self, k, int(safeEval(attrs[k])))


def content_string(contents):
    res = ""
    for element in contents:
        if isinstance(element, tuple):
            continue
        res += element
    return res.strip()


def wrapline(writer, dat, length=80):
    currline = ""
    for d in dat:
        if len(currline) > length:
            writer.write(currline[:-1])
            writer.newline()
            currline = ""
        currline += d + " "
    if len(currline):
        writer.write(currline[:-1])
        writer.newline()


class _Object:
    pass


class table_S__i_l_f(DefaultTable.DefaultTable):
    """Graphite Rules table

    See also https://graphite.sil.org/graphite_techAbout#graphite-font-tables
    """

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.silfs = []

    def decompile(self, data, ttFont):
        sstruct.unpack2(Silf_hdr_format, data, self)
        self.version = float(floatToFixedToStr(self.version, precisionBits=16))
        if self.version >= 5.0:
            (data, self.scheme) = grUtils.decompress(data)
            sstruct.unpack2(Silf_hdr_format_3, data, self)
            base = sstruct.calcsize(Silf_hdr_format_3)
        elif self.version < 3.0:
            self.numSilf = struct.unpack(">H", data[4:6])
            self.scheme = 0
            self.compilerVersion = 0
            base = 8
        else:
            self.scheme = 0
            sstruct.unpack2(Silf_hdr_format_3, data, self)
            base = sstruct.calcsize(Silf_hdr_format_3)

        silfoffsets = struct.unpack_from((">%dL" % self.numSilf), data[base:])
        for offset in silfoffsets:
            s = Silf()
            self.silfs.append(s)
            s.decompile(data[offset:], ttFont, self.version)

    def compile(self, ttFont):
        self.numSilf = len(self.silfs)
        if self.version < 3.0:
            hdr = sstruct.pack(Silf_hdr_format, self)
            hdr += struct.pack(">HH", self.numSilf, 0)
        else:
            hdr = sstruct.pack(Silf_hdr_format_3, self)
        offset = len(hdr) + 4 * self.numSilf
        data = b""
        for s in self.silfs:
            hdr += struct.pack(">L", offset)
            subdata = s.compile(ttFont, self.version)
            offset += len(subdata)
            data += subdata
        if self.version >= 5.0:
            return grUtils.compress(self.scheme, hdr + data)
        return hdr + data

    def toXML(self, writer, ttFont):
        writer.comment("Attributes starting with _ are informative only")
        writer.newline()
        writer.simpletag(
            "version",
            version=self.version,
            compilerVersion=self.compilerVersion,
            compressionScheme=self.scheme,
        )
        writer.newline()
        for s in self.silfs:
            writer.begintag("silf")
            writer.newline()
            s.toXML(writer, ttFont, self.version)
            writer.endtag("silf")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.scheme = int(safeEval(attrs["compressionScheme"]))
            self.version = float(safeEval(attrs["version"]))
            self.compilerVersion = int(safeEval(attrs["compilerVersion"]))
            return
        if name == "silf":
            s = Silf()
            self.silfs.append(s)
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, attrs, subcontent = element
                s.fromXML(tag, attrs, subcontent, ttFont, self.version)


class Silf(object):
    """A particular Silf subtable"""

    def __init__(self):
        self.passes = []
        self.scriptTags = []
        self.critFeatures = []
        self.jLevels = []
        self.pMap = {}

    def decompile(self, data, ttFont, version=2.0):
        if version >= 3.0:
            _, data = sstruct.unpack2(Silf_part1_format_v3, data, self)
            self.ruleVersion = float(
                floatToFixedToStr(self.ruleVersion, precisionBits=16)
            )
        _, data = sstruct.unpack2(Silf_part1_format, data, self)
        for jlevel in range(self.numJLevels):
            j, data = sstruct.unpack2(Silf_justify_format, data, _Object())
            self.jLevels.append(j)
        _, data = sstruct.unpack2(Silf_part2_format, data, self)
        if self.numCritFeatures:
            self.critFeatures = struct.unpack_from(
                (">%dH" % self.numCritFeatures), data
            )
        data = data[self.numCritFeatures * 2 + 1 :]
        (numScriptTag,) = struct.unpack_from("B", data)
        if numScriptTag:
            self.scriptTags = [
                struct.unpack("4s", data[x : x + 4])[0].decode("ascii")
                for x in range(1, 1 + 4 * numScriptTag, 4)
            ]
        data = data[1 + 4 * numScriptTag :]
        (self.lbGID,) = struct.unpack(">H", data[:2])
        if self.numPasses:
            self.oPasses = struct.unpack(
                (">%dL" % (self.numPasses + 1)), data[2 : 6 + 4 * self.numPasses]
            )
        data = data[6 + 4 * self.numPasses :]
        (numPseudo,) = struct.unpack(">H", data[:2])
        for i in range(numPseudo):
            if version >= 3.0:
                pseudo = sstruct.unpack(
                    Silf_pseudomap_format, data[8 + 6 * i : 14 + 6 * i], _Object()
                )
            else:
                pseudo = sstruct.unpack(
                    Silf_pseudomap_format_h, data[8 + 4 * i : 12 + 4 * i], _Object()
                )
            self.pMap[pseudo.unicode] = ttFont.getGlyphName(pseudo.nPseudo)
        data = data[8 + 6 * numPseudo :]
        currpos = (
            sstruct.calcsize(Silf_part1_format)
            + sstruct.calcsize(Silf_justify_format) * self.numJLevels
            + sstruct.calcsize(Silf_part2_format)
            + 2 * self.numCritFeatures
            + 1
            + 1
            + 4 * numScriptTag
            + 6
            + 4 * self.numPasses
            + 8
            + 6 * numPseudo
        )
        if version >= 3.0:
            currpos += sstruct.calcsize(Silf_part1_format_v3)
        self.classes = Classes()
        self.classes.decompile(data, ttFont, version)
        for i in range(self.numPasses):
            p = Pass()
            self.passes.append(p)
            p.decompile(
                data[self.oPasses[i] - currpos : self.oPasses[i + 1] - currpos],
                ttFont,
                version,
            )

    def compile(self, ttFont, version=2.0):
        self.numPasses = len(self.passes)
        self.numJLevels = len(self.jLevels)
        self.numCritFeatures = len(self.critFeatures)
        numPseudo = len(self.pMap)
        data = b""
        if version >= 3.0:
            hdroffset = sstruct.calcsize(Silf_part1_format_v3)
        else:
            hdroffset = 0
        data += sstruct.pack(Silf_part1_format, self)
        for j in self.jLevels:
            data += sstruct.pack(Silf_justify_format, j)
        data += sstruct.pack(Silf_part2_format, self)
        if self.numCritFeatures:
            data += struct.pack((">%dH" % self.numCritFeaturs), *self.critFeatures)
        data += struct.pack("BB", 0, len(self.scriptTags))
        if len(self.scriptTags):
            tdata = [struct.pack("4s", x.encode("ascii")) for x in self.scriptTags]
            data += b"".join(tdata)
        data += struct.pack(">H", self.lbGID)
        self.passOffset = len(data)

        data1 = grUtils.bininfo(numPseudo, 6)
        currpos = hdroffset + len(data) + 4 * (self.numPasses + 1)
        self.pseudosOffset = currpos + len(data1)
        for u, p in sorted(self.pMap.items()):
            data1 += struct.pack(
                (">LH" if version >= 3.0 else ">HH"), u, ttFont.getGlyphID(p)
            )
        data1 += self.classes.compile(ttFont, version)
        currpos += len(data1)
        data2 = b""
        datao = b""
        for i, p in enumerate(self.passes):
            base = currpos + len(data2)
            datao += struct.pack(">L", base)
            data2 += p.compile(ttFont, base, version)
        datao += struct.pack(">L", currpos + len(data2))

        if version >= 3.0:
            data3 = sstruct.pack(Silf_part1_format_v3, self)
        else:
            data3 = b""
        return data3 + data + datao + data1 + data2

    def toXML(self, writer, ttFont, version=2.0):
        if version >= 3.0:
            writer.simpletag("version", ruleVersion=self.ruleVersion)
            writer.newline()
        writesimple("info", self, writer, *attrs_info)
        writesimple("passindexes", self, writer, *attrs_passindexes)
        writesimple("contexts", self, writer, *attrs_contexts)
        writesimple("attributes", self, writer, *attrs_attributes)
        if len(self.jLevels):
            writer.begintag("justifications")
            writer.newline()
            jformat, jnames, jfixes = sstruct.getformat(Silf_justify_format)
            for i, j in enumerate(self.jLevels):
                attrs = dict([(k, getattr(j, k)) for k in jnames])
                writer.simpletag("justify", **attrs)
                writer.newline()
            writer.endtag("justifications")
            writer.newline()
        if len(self.critFeatures):
            writer.begintag("critFeatures")
            writer.newline()
            writer.write(" ".join(map(str, self.critFeatures)))
            writer.newline()
            writer.endtag("critFeatures")
            writer.newline()
        if len(self.scriptTags):
            writer.begintag("scriptTags")
            writer.newline()
            writer.write(" ".join(self.scriptTags))
            writer.newline()
            writer.endtag("scriptTags")
            writer.newline()
        if self.pMap:
            writer.begintag("pseudoMap")
            writer.newline()
            for k, v in sorted(self.pMap.items()):
                writer.simpletag("pseudo", unicode=hex(k), pseudo=v)
                writer.newline()
            writer.endtag("pseudoMap")
            writer.newline()
        self.classes.toXML(writer, ttFont, version)
        if len(self.passes):
            writer.begintag("passes")
            writer.newline()
            for i, p in enumerate(self.passes):
                writer.begintag("pass", _index=i)
                writer.newline()
                p.toXML(writer, ttFont, version)
                writer.endtag("pass")
                writer.newline()
            writer.endtag("passes")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont, version=2.0):
        if name == "version":
            self.ruleVersion = float(safeEval(attrs.get("ruleVersion", "0")))
        if name == "info":
            getSimple(self, attrs, *attrs_info)
        elif name == "passindexes":
            getSimple(self, attrs, *attrs_passindexes)
        elif name == "contexts":
            getSimple(self, attrs, *attrs_contexts)
        elif name == "attributes":
            getSimple(self, attrs, *attrs_attributes)
        elif name == "justifications":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                (tag, attrs, subcontent) = element
                if tag == "justify":
                    j = _Object()
                    for k, v in attrs.items():
                        setattr(j, k, int(v))
                    self.jLevels.append(j)
        elif name == "critFeatures":
            self.critFeatures = []
            element = content_string(content)
            self.critFeatures.extend(map(int, element.split()))
        elif name == "scriptTags":
            self.scriptTags = []
            element = content_string(content)
            for n in element.split():
                self.scriptTags.append(n)
        elif name == "pseudoMap":
            self.pMap = {}
            for element in content:
                if not isinstance(element, tuple):
                    continue
                (tag, attrs, subcontent) = element
                if tag == "pseudo":
                    k = int(attrs["unicode"], 16)
                    v = attrs["pseudo"]
                self.pMap[k] = v
        elif name == "classes":
            self.classes = Classes()
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, attrs, subcontent = element
                self.classes.fromXML(tag, attrs, subcontent, ttFont, version)
        elif name == "passes":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, attrs, subcontent = element
                if tag == "pass":
                    p = Pass()
                    for e in subcontent:
                        if not isinstance(e, tuple):
                            continue
                        p.fromXML(e[0], e[1], e[2], ttFont, version)
                    self.passes.append(p)


class Classes(object):
    def __init__(self):
        self.linear = []
        self.nonLinear = []

    def decompile(self, data, ttFont, version=2.0):
        sstruct.unpack2(Silf_classmap_format, data, self)
        if version >= 4.0:
            oClasses = struct.unpack(
                (">%dL" % (self.numClass + 1)), data[4 : 8 + 4 * self.numClass]
            )
        else:
            oClasses = struct.unpack(
                (">%dH" % (self.numClass + 1)), data[4 : 6 + 2 * self.numClass]
            )
        for s, e in zip(oClasses[: self.numLinear], oClasses[1 : self.numLinear + 1]):
            self.linear.append(
                ttFont.getGlyphName(x)
                for x in struct.unpack((">%dH" % ((e - s) / 2)), data[s:e])
            )
        for s, e in zip(
            oClasses[self.numLinear : self.numClass],
            oClasses[self.numLinear + 1 : self.numClass + 1],
        ):
            nonLinids = [
                struct.unpack(">HH", data[x : x + 4]) for x in range(s + 8, e, 4)
            ]
            nonLin = dict([(ttFont.getGlyphName(x[0]), x[1]) for x in nonLinids])
            self.nonLinear.append(nonLin)

    def compile(self, ttFont, version=2.0):
        data = b""
        oClasses = []
        if version >= 4.0:
            offset = 8 + 4 * (len(self.linear) + len(self.nonLinear))
        else:
            offset = 6 + 2 * (len(self.linear) + len(self.nonLinear))
        for l in self.linear:
            oClasses.append(len(data) + offset)
            gs = [ttFont.getGlyphID(x) for x in l]
            data += struct.pack((">%dH" % len(l)), *gs)
        for l in self.nonLinear:
            oClasses.append(len(data) + offset)
            gs = [(ttFont.getGlyphID(x[0]), x[1]) for x in l.items()]
            data += grUtils.bininfo(len(gs))
            data += b"".join([struct.pack(">HH", *x) for x in sorted(gs)])
        oClasses.append(len(data) + offset)
        self.numClass = len(oClasses) - 1
        self.numLinear = len(self.linear)
        return (
            sstruct.pack(Silf_classmap_format, self)
            + struct.pack(
                ((">%dL" if version >= 4.0 else ">%dH") % len(oClasses)), *oClasses
            )
            + data
        )

    def toXML(self, writer, ttFont, version=2.0):
        writer.begintag("classes")
        writer.newline()
        writer.begintag("linearClasses")
        writer.newline()
        for i, l in enumerate(self.linear):
            writer.begintag("linear", _index=i)
            writer.newline()
            wrapline(writer, l)
            writer.endtag("linear")
            writer.newline()
        writer.endtag("linearClasses")
        writer.newline()
        writer.begintag("nonLinearClasses")
        writer.newline()
        for i, l in enumerate(self.nonLinear):
            writer.begintag("nonLinear", _index=i + self.numLinear)
            writer.newline()
            for inp, ind in l.items():
                writer.simpletag("map", glyph=inp, index=ind)
                writer.newline()
            writer.endtag("nonLinear")
            writer.newline()
        writer.endtag("nonLinearClasses")
        writer.newline()
        writer.endtag("classes")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont, version=2.0):
        if name == "linearClasses":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, attrs, subcontent = element
                if tag == "linear":
                    l = content_string(subcontent).split()
                    self.linear.append(l)
        elif name == "nonLinearClasses":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, attrs, subcontent = element
                if tag == "nonLinear":
                    l = {}
                    for e in subcontent:
                        if not isinstance(e, tuple):
                            continue
                        tag, attrs, subsubcontent = e
                        if tag == "map":
                            l[attrs["glyph"]] = int(safeEval(attrs["index"]))
                    self.nonLinear.append(l)


class Pass(object):
    def __init__(self):
        self.colMap = {}
        self.rules = []
        self.rulePreContexts = []
        self.ruleSortKeys = []
        self.ruleConstraints = []
        self.passConstraints = b""
        self.actions = []
        self.stateTrans = []
        self.startStates = []

    def decompile(self, data, ttFont, version=2.0):
        _, data = sstruct.unpack2(Silf_pass_format, data, self)
        (numRange, _, _, _) = struct.unpack(">4H", data[:8])
        data = data[8:]
        for i in range(numRange):
            (first, last, col) = struct.unpack(">3H", data[6 * i : 6 * i + 6])
            for g in range(first, last + 1):
                self.colMap[ttFont.getGlyphName(g)] = col
        data = data[6 * numRange :]
        oRuleMap = struct.unpack_from((">%dH" % (self.numSuccess + 1)), data)
        data = data[2 + 2 * self.numSuccess :]
        rules = struct.unpack_from((">%dH" % oRuleMap[-1]), data)
        self.rules = [rules[s:e] for (s, e) in zip(oRuleMap, oRuleMap[1:])]
        data = data[2 * oRuleMap[-1] :]
        (self.minRulePreContext, self.maxRulePreContext) = struct.unpack("BB", data[:2])
        numStartStates = self.maxRulePreContext - self.minRulePreContext + 1
        self.startStates = struct.unpack(
            (">%dH" % numStartStates), data[2 : 2 + numStartStates * 2]
        )
        data = data[2 + numStartStates * 2 :]
        self.ruleSortKeys = struct.unpack(
            (">%dH" % self.numRules), data[: 2 * self.numRules]
        )
        data = data[2 * self.numRules :]
        self.rulePreContexts = struct.unpack(
            ("%dB" % self.numRules), data[: self.numRules]
        )
        data = data[self.numRules :]
        (self.collisionThreshold, pConstraint) = struct.unpack(">BH", data[:3])
        oConstraints = list(
            struct.unpack(
                (">%dH" % (self.numRules + 1)), data[3 : 5 + self.numRules * 2]
            )
        )
        data = data[5 + self.numRules * 2 :]
        oActions = list(
            struct.unpack((">%dH" % (self.numRules + 1)), data[: 2 + self.numRules * 2])
        )
        data = data[2 * self.numRules + 2 :]
        for i in range(self.numTransitional):
            a = array(
                "H", data[i * self.numColumns * 2 : (i + 1) * self.numColumns * 2]
            )
            if sys.byteorder != "big":
                a.byteswap()
            self.stateTrans.append(a)
        data = data[self.numTransitional * self.numColumns * 2 + 1 :]
        self.passConstraints = data[:pConstraint]
        data = data[pConstraint:]
        for i in range(len(oConstraints) - 2, -1, -1):
            if oConstraints[i] == 0:
                oConstraints[i] = oConstraints[i + 1]
        self.ruleConstraints = [
            (data[s:e] if (e - s > 1) else b"")
            for (s, e) in zip(oConstraints, oConstraints[1:])
        ]
        data = data[oConstraints[-1] :]
        self.actions = [
            (data[s:e] if (e - s > 1) else "") for (s, e) in zip(oActions, oActions[1:])
        ]
        data = data[oActions[-1] :]
        # not using debug

    def compile(self, ttFont, base, version=2.0):
        # build it all up backwards
        oActions = reduce(
            lambda a, x: (a[0] + len(x), a[1] + [a[0]]), self.actions + [b""], (0, [])
        )[1]
        oConstraints = reduce(
            lambda a, x: (a[0] + len(x), a[1] + [a[0]]),
            self.ruleConstraints + [b""],
            (1, []),
        )[1]
        constraintCode = b"\000" + b"".join(self.ruleConstraints)
        transes = []
        for t in self.stateTrans:
            if sys.byteorder != "big":
                t.byteswap()
            transes.append(t.tobytes())
            if sys.byteorder != "big":
                t.byteswap()
        if not len(transes):
            self.startStates = [0]
        oRuleMap = reduce(
            lambda a, x: (a[0] + len(x), a[1] + [a[0]]), self.rules + [[]], (0, [])
        )[1]
        passRanges = []
        gidcolmap = dict([(ttFont.getGlyphID(x[0]), x[1]) for x in self.colMap.items()])
        for e in grUtils.entries(gidcolmap, sameval=True):
            if e[1]:
                passRanges.append((e[0], e[0] + e[1] - 1, e[2][0]))
        self.numRules = len(self.actions)
        self.fsmOffset = (
            sstruct.calcsize(Silf_pass_format)
            + 8
            + len(passRanges) * 6
            + len(oRuleMap) * 2
            + 2 * oRuleMap[-1]
            + 2
            + 2 * len(self.startStates)
            + 3 * self.numRules
            + 3
            + 4 * self.numRules
            + 4
        )
        self.pcCode = (
            self.fsmOffset + 2 * self.numTransitional * self.numColumns + 1 + base
        )
        self.rcCode = self.pcCode + len(self.passConstraints)
        self.aCode = self.rcCode + len(constraintCode)
        self.oDebug = 0
        # now generate output
        data = sstruct.pack(Silf_pass_format, self)
        data += grUtils.bininfo(len(passRanges), 6)
        data += b"".join(struct.pack(">3H", *p) for p in passRanges)
        data += struct.pack((">%dH" % len(oRuleMap)), *oRuleMap)
        flatrules = reduce(lambda a, x: a + x, self.rules, [])
        data += struct.pack((">%dH" % oRuleMap[-1]), *flatrules)
        data += struct.pack("BB", self.minRulePreContext, self.maxRulePreContext)
        data += struct.pack((">%dH" % len(self.startStates)), *self.startStates)
        data += struct.pack((">%dH" % self.numRules), *self.ruleSortKeys)
        data += struct.pack(("%dB" % self.numRules), *self.rulePreContexts)
        data += struct.pack(">BH", self.collisionThreshold, len(self.passConstraints))
        data += struct.pack((">%dH" % (self.numRules + 1)), *oConstraints)
        data += struct.pack((">%dH" % (self.numRules + 1)), *oActions)
        return (
            data
            + b"".join(transes)
            + struct.pack("B", 0)
            + self.passConstraints
            + constraintCode
            + b"".join(self.actions)
        )

    def toXML(self, writer, ttFont, version=2.0):
        writesimple("info", self, writer, *pass_attrs_info)
        writesimple("fsminfo", self, writer, *pass_attrs_fsm)
        writer.begintag("colmap")
        writer.newline()
        wrapline(
            writer,
            [
                "{}={}".format(*x)
                for x in sorted(
                    self.colMap.items(), key=lambda x: ttFont.getGlyphID(x[0])
                )
            ],
        )
        writer.endtag("colmap")
        writer.newline()
        writer.begintag("staterulemap")
        writer.newline()
        for i, r in enumerate(self.rules):
            writer.simpletag(
                "state",
                number=self.numRows - self.numSuccess + i,
                rules=" ".join(map(str, r)),
            )
            writer.newline()
        writer.endtag("staterulemap")
        writer.newline()
        writer.begintag("rules")
        writer.newline()
        for i in range(len(self.actions)):
            writer.begintag(
                "rule",
                index=i,
                precontext=self.rulePreContexts[i],
                sortkey=self.ruleSortKeys[i],
            )
            writer.newline()
            if len(self.ruleConstraints[i]):
                writecode("constraint", writer, self.ruleConstraints[i])
            writecode("action", writer, self.actions[i])
            writer.endtag("rule")
            writer.newline()
        writer.endtag("rules")
        writer.newline()
        if len(self.passConstraints):
            writecode("passConstraint", writer, self.passConstraints)
        if len(self.stateTrans):
            writer.begintag("fsm")
            writer.newline()
            writer.begintag("starts")
            writer.write(" ".join(map(str, self.startStates)))
            writer.endtag("starts")
            writer.newline()
            for i, s in enumerate(self.stateTrans):
                writer.begintag("row", _i=i)
                # no newlines here
                writer.write(" ".join(map(str, s)))
                writer.endtag("row")
                writer.newline()
            writer.endtag("fsm")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont, version=2.0):
        if name == "info":
            getSimple(self, attrs, *pass_attrs_info)
        elif name == "fsminfo":
            getSimple(self, attrs, *pass_attrs_fsm)
        elif name == "colmap":
            e = content_string(content)
            for w in e.split():
                x = w.split("=")
                if len(x) != 2 or x[0] == "" or x[1] == "":
                    continue
                self.colMap[x[0]] = int(x[1])
        elif name == "staterulemap":
            for e in content:
                if not isinstance(e, tuple):
                    continue
                tag, a, c = e
                if tag == "state":
                    self.rules.append([int(x) for x in a["rules"].split(" ")])
        elif name == "rules":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, a, c = element
                if tag != "rule":
                    continue
                self.rulePreContexts.append(int(a["precontext"]))
                self.ruleSortKeys.append(int(a["sortkey"]))
                con = b""
                act = b""
                for e in c:
                    if not isinstance(e, tuple):
                        continue
                    tag, a, subc = e
                    if tag == "constraint":
                        con = readcode(subc)
                    elif tag == "action":
                        act = readcode(subc)
                self.actions.append(act)
                self.ruleConstraints.append(con)
        elif name == "passConstraint":
            self.passConstraints = readcode(content)
        elif name == "fsm":
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, a, c = element
                if tag == "row":
                    s = array("H")
                    e = content_string(c)
                    s.extend(map(int, e.split()))
                    self.stateTrans.append(s)
                elif tag == "starts":
                    s = []
                    e = content_string(c)
                    s.extend(map(int, e.split()))
                    self.startStates = s

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\client.py ===
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
from google.protobuf import timestamp_pb2  # type: ignore
from google.rpc import status_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.file_service import pagers
from google.ai.generativelanguage_v1beta.types import file, file_service

from .transports.base import DEFAULT_CLIENT_INFO, FileServiceTransport
from .transports.grpc import FileServiceGrpcTransport
from .transports.grpc_asyncio import FileServiceGrpcAsyncIOTransport
from .transports.rest import FileServiceRestTransport


class FileServiceClientMeta(type):
    """Metaclass for the FileService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[FileServiceTransport]]
    _transport_registry["grpc"] = FileServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = FileServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = FileServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[FileServiceTransport]:
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


class FileServiceClient(metaclass=FileServiceClientMeta):
    """An API for uploading and managing files."""

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
            FileServiceClient: The constructed client.
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
            FileServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> FileServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            FileServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def file_path(
        file: str,
    ) -> str:
        """Returns a fully-qualified file string."""
        return "files/{file}".format(
            file=file,
        )

    @staticmethod
    def parse_file_path(path: str) -> Dict[str, str]:
        """Parses a file path into its component segments."""
        m = re.match(r"^files/(?P<file>.+?)$", path)
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
            _default_universe = FileServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = FileServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = FileServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = FileServiceClient._DEFAULT_UNIVERSE
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

        default_universe = FileServiceClient._DEFAULT_UNIVERSE
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
            or FileServiceClient._compare_universes(
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
            Union[str, FileServiceTransport, Callable[..., FileServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the file service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,FileServiceTransport,Callable[..., FileServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the FileServiceTransport constructor.
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
        ) = FileServiceClient._read_environment_variables()
        self._client_cert_source = FileServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = FileServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, FileServiceTransport)
        if transport_provided:
            # transport is a FileServiceTransport instance.
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
            self._transport = cast(FileServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or FileServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
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
                Type[FileServiceTransport], Callable[..., FileServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., FileServiceTransport], transport)
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

    def create_file(
        self,
        request: Optional[Union[file_service.CreateFileRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> file_service.CreateFileResponse:
        r"""Creates a ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateFileRequest(
                )

                # Make the request
                response = client.create_file(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateFileRequest, dict]):
                The request object. Request for ``CreateFile``.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CreateFileResponse:
                Response for CreateFile.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, file_service.CreateFileRequest):
            request = file_service.CreateFileRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_file]

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

    def list_files(
        self,
        request: Optional[Union[file_service.ListFilesRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListFilesPager:
        r"""Lists the metadata for ``File``\ s owned by the requesting
        project.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_files():
                # Create a client
                client = generativelanguage_v1beta.FileServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListFilesRequest(
                )

                # Make the request
                page_result = client.list_files(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListFilesRequest, dict]):
                The request object. Request for ``ListFiles``.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.file_service.pagers.ListFilesPager:
                Response for ListFiles.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, file_service.ListFilesRequest):
            request = file_service.ListFilesRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_files]

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
        response = pagers.ListFilesPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_file(
        self,
        request: Optional[Union[file_service.GetFileRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> file.File:
        r"""Gets the metadata for the given ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetFileRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_file(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetFileRequest, dict]):
                The request object. Request for ``GetFile``.
            name (str):
                Required. The name of the ``File`` to get. Example:
                ``files/abc-123``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.File:
                A file uploaded to the API.
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
        if not isinstance(request, file_service.GetFileRequest):
            request = file_service.GetFileRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_file]

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

    def delete_file(
        self,
        request: Optional[Union[file_service.DeleteFileRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteFileRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_file(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteFileRequest, dict]):
                The request object. Request for ``DeleteFile``.
            name (str):
                Required. The name of the ``File`` to delete. Example:
                ``files/abc-123``

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
        if not isinstance(request, file_service.DeleteFileRequest):
            request = file_service.DeleteFileRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_file]

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

    def __enter__(self) -> "FileServiceClient":
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


__all__ = ("FileServiceClient",)

# === NexusCore/openenv\Lib\site-packages\requests\models.py ===
"""
requests.models
~~~~~~~~~~~~~~~

This module contains the primary objects that power Requests.
"""

import datetime

# Import encoding now, to avoid implicit import later.
# Implicit import within threads may cause LookupError when standard library is in a ZIP,
# such as in Embedded Python. See https://github.com/psf/requests/issues/3578.
import encodings.idna  # noqa: F401
from io import UnsupportedOperation

from urllib3.exceptions import (
    DecodeError,
    LocationParseError,
    ProtocolError,
    ReadTimeoutError,
    SSLError,
)
from urllib3.fields import RequestField
from urllib3.filepost import encode_multipart_formdata
from urllib3.util import parse_url

from ._internal_utils import to_native_string, unicode_is_ascii
from .auth import HTTPBasicAuth
from .compat import (
    Callable,
    JSONDecodeError,
    Mapping,
    basestring,
    builtin_str,
    chardet,
    cookielib,
)
from .compat import json as complexjson
from .compat import urlencode, urlsplit, urlunparse
from .cookies import _copy_cookie_jar, cookiejar_from_dict, get_cookie_header
from .exceptions import (
    ChunkedEncodingError,
    ConnectionError,
    ContentDecodingError,
    HTTPError,
    InvalidJSONError,
    InvalidURL,
)
from .exceptions import JSONDecodeError as RequestsJSONDecodeError
from .exceptions import MissingSchema
from .exceptions import SSLError as RequestsSSLError
from .exceptions import StreamConsumedError
from .hooks import default_hooks
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (
    check_header_validity,
    get_auth_from_url,
    guess_filename,
    guess_json_utf,
    iter_slices,
    parse_header_links,
    requote_uri,
    stream_decode_response_unicode,
    super_len,
    to_key_val_list,
)

#: The set of HTTP status codes that indicate an automatically
#: processable redirect.
REDIRECT_STATI = (
    codes.moved,  # 301
    codes.found,  # 302
    codes.other,  # 303
    codes.temporary_redirect,  # 307
    codes.permanent_redirect,  # 308
)

DEFAULT_REDIRECT_LIMIT = 30
CONTENT_CHUNK_SIZE = 10 * 1024
ITER_CHUNK_SIZE = 512


class RequestEncodingMixin:
    @property
    def path_url(self):
        """Build the path URL to use."""

        url = []

        p = urlsplit(self.url)

        path = p.path
        if not path:
            path = "/"

        url.append(path)

        query = p.query
        if query:
            url.append("?")
            url.append(query)

        return "".join(url)

    @staticmethod
    def _encode_params(data):
        """Encode parameters in a piece of data.

        Will successfully encode parameters when passed as a dict or a list of
        2-tuples. Order is retained if data is a list of 2-tuples but arbitrary
        if parameters are supplied as a dict.
        """

        if isinstance(data, (str, bytes)):
            return data
        elif hasattr(data, "read"):
            return data
        elif hasattr(data, "__iter__"):
            result = []
            for k, vs in to_key_val_list(data):
                if isinstance(vs, basestring) or not hasattr(vs, "__iter__"):
                    vs = [vs]
                for v in vs:
                    if v is not None:
                        result.append(
                            (
                                k.encode("utf-8") if isinstance(k, str) else k,
                                v.encode("utf-8") if isinstance(v, str) else v,
                            )
                        )
            return urlencode(result, doseq=True)
        else:
            return data

    @staticmethod
    def _encode_files(files, data):
        """Build the body for a multipart/form-data request.

        Will successfully encode files when passed as a dict or a list of
        tuples. Order is retained if data is a list of tuples but arbitrary
        if parameters are supplied as a dict.
        The tuples may be 2-tuples (filename, fileobj), 3-tuples (filename, fileobj, contentype)
        or 4-tuples (filename, fileobj, contentype, custom_headers).
        """
        if not files:
            raise ValueError("Files must be provided.")
        elif isinstance(data, basestring):
            raise ValueError("Data must not be a string.")

        new_fields = []
        fields = to_key_val_list(data or {})
        files = to_key_val_list(files or {})

        for field, val in fields:
            if isinstance(val, basestring) or not hasattr(val, "__iter__"):
                val = [val]
            for v in val:
                if v is not None:
                    # Don't call str() on bytestrings: in Py3 it all goes wrong.
                    if not isinstance(v, bytes):
                        v = str(v)

                    new_fields.append(
                        (
                            field.decode("utf-8")
                            if isinstance(field, bytes)
                            else field,
                            v.encode("utf-8") if isinstance(v, str) else v,
                        )
                    )

        for k, v in files:
            # support for explicit filename
            ft = None
            fh = None
            if isinstance(v, (tuple, list)):
                if len(v) == 2:
                    fn, fp = v
                elif len(v) == 3:
                    fn, fp, ft = v
                else:
                    fn, fp, ft, fh = v
            else:
                fn = guess_filename(v) or k
                fp = v

            if isinstance(fp, (str, bytes, bytearray)):
                fdata = fp
            elif hasattr(fp, "read"):
                fdata = fp.read()
            elif fp is None:
                continue
            else:
                fdata = fp

            rf = RequestField(name=k, data=fdata, filename=fn, headers=fh)
            rf.make_multipart(content_type=ft)
            new_fields.append(rf)

        body, content_type = encode_multipart_formdata(new_fields)

        return body, content_type


class RequestHooksMixin:
    def register_hook(self, event, hook):
        """Properly register a hook."""

        if event not in self.hooks:
            raise ValueError(f'Unsupported event specified, with event name "{event}"')

        if isinstance(hook, Callable):
            self.hooks[event].append(hook)
        elif hasattr(hook, "__iter__"):
            self.hooks[event].extend(h for h in hook if isinstance(h, Callable))

    def deregister_hook(self, event, hook):
        """Deregister a previously registered hook.
        Returns True if the hook existed, False if not.
        """

        try:
            self.hooks[event].remove(hook)
            return True
        except ValueError:
            return False


class Request(RequestHooksMixin):
    """A user-created :class:`Request <Request>` object.

    Used to prepare a :class:`PreparedRequest <PreparedRequest>`, which is sent to the server.

    :param method: HTTP method to use.
    :param url: URL to send.
    :param headers: dictionary of headers to send.
    :param files: dictionary of {filename: fileobject} files to multipart upload.
    :param data: the body to attach to the request. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param json: json for the body to attach to the request (if files or data is not specified).
    :param params: URL parameters to append to the URL. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param auth: Auth handler or (user, pass) tuple.
    :param cookies: dictionary or CookieJar of cookies to attach to this request.
    :param hooks: dictionary of callback hooks, for internal usage.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> req.prepare()
      <PreparedRequest [GET]>
    """

    def __init__(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        # Default empty dicts for dict params.
        data = [] if data is None else data
        files = [] if files is None else files
        headers = {} if headers is None else headers
        params = {} if params is None else params
        hooks = {} if hooks is None else hooks

        self.hooks = default_hooks()
        for k, v in list(hooks.items()):
            self.register_hook(event=k, hook=v)

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.json = json
        self.params = params
        self.auth = auth
        self.cookies = cookies

    def __repr__(self):
        return f"<Request [{self.method}]>"

    def prepare(self):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it."""
        p = PreparedRequest()
        p.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
        )
        return p


class PreparedRequest(RequestEncodingMixin, RequestHooksMixin):
    """The fully mutable :class:`PreparedRequest <PreparedRequest>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> r = req.prepare()
      >>> r
      <PreparedRequest [GET]>

      >>> s = requests.Session()
      >>> s.send(r)
      <Response [200]>
    """

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        # The `CookieJar` used to create the Cookie header will be stored here
        # after prepare_cookies is called
        self._cookies = None
        #: request body to send to the server.
        self.body = None
        #: dictionary of callback hooks, for internal usage.
        self.hooks = default_hooks()
        #: integer denoting starting position of a readable file-like body.
        self._body_position = None

    def prepare(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        """Prepares the entire request with the given parameters."""

        self.prepare_method(method)
        self.prepare_url(url, params)
        self.prepare_headers(headers)
        self.prepare_cookies(cookies)
        self.prepare_body(data, files, json)
        self.prepare_auth(auth, url)

        # Note that prepare_auth must be last to enable authentication schemes
        # such as OAuth to work on a fully prepared request.

        # This MUST go after prepare_auth. Authenticators could add a hook
        self.prepare_hooks(hooks)

    def __repr__(self):
        return f"<PreparedRequest [{self.method}]>"

    def copy(self):
        p = PreparedRequest()
        p.method = self.method
        p.url = self.url
        p.headers = self.headers.copy() if self.headers is not None else None
        p._cookies = _copy_cookie_jar(self._cookies)
        p.body = self.body
        p.hooks = self.hooks
        p._body_position = self._body_position
        return p

    def prepare_method(self, method):
        """Prepares the given HTTP method."""
        self.method = method
        if self.method is not None:
            self.method = to_native_string(self.method.upper())

    @staticmethod
    def _get_idna_encoded_host(host):
        import idna

        try:
            host = idna.encode(host, uts46=True).decode("utf-8")
        except idna.IDNAError:
            raise UnicodeError
        return host

    def prepare_url(self, url, params):
        """Prepares the given HTTP URL."""
        #: Accept objects that have string representations.
        #: We're unable to blindly call unicode/str functions
        #: as this will include the bytestring indicator (b'')
        #: on python 3.x.
        #: https://github.com/psf/requests/pull/2238
        if isinstance(url, bytes):
            url = url.decode("utf8")
        else:
            url = str(url)

        # Remove leading whitespaces from url
        url = url.lstrip()

        # Don't do any URL preparation for non-HTTP schemes like `mailto`,
        # `data` etc to work around exceptions from `url_parse`, which
        # handles RFC 3986 only.
        if ":" in url and not url.lower().startswith("http"):
            self.url = url
            return

        # Support for unicode domain names and paths.
        try:
            scheme, auth, host, port, path, query, fragment = parse_url(url)
        except LocationParseError as e:
            raise InvalidURL(*e.args)

        if not scheme:
            raise MissingSchema(
                f"Invalid URL {url!r}: No scheme supplied. "
                f"Perhaps you meant https://{url}?"
            )

        if not host:
            raise InvalidURL(f"Invalid URL {url!r}: No host supplied")

        # In general, we want to try IDNA encoding the hostname if the string contains
        # non-ASCII characters. This allows users to automatically get the correct IDNA
        # behaviour. For strings containing only ASCII characters, we need to also verify
        # it doesn't start with a wildcard (*), before allowing the unencoded hostname.
        if not unicode_is_ascii(host):
            try:
                host = self._get_idna_encoded_host(host)
            except UnicodeError:
                raise InvalidURL("URL has an invalid label.")
        elif host.startswith(("*", ".")):
            raise InvalidURL("URL has an invalid label.")

        # Carefully reconstruct the network location
        netloc = auth or ""
        if netloc:
            netloc += "@"
        netloc += host
        if port:
            netloc += f":{port}"

        # Bare domains aren't valid URLs.
        if not path:
            path = "/"

        if isinstance(params, (str, bytes)):
            params = to_native_string(params)

        enc_params = self._encode_params(params)
        if enc_params:
            if query:
                query = f"{query}&{enc_params}"
            else:
                query = enc_params

        url = requote_uri(urlunparse([scheme, netloc, path, None, query, fragment]))
        self.url = url

    def prepare_headers(self, headers):
        """Prepares the given HTTP headers."""

        self.headers = CaseInsensitiveDict()
        if headers:
            for header in headers.items():
                # Raise exception on invalid header value.
                check_header_validity(header)
                name, value = header
                self.headers[to_native_string(name)] = value

    def prepare_body(self, data, files, json=None):
        """Prepares the given HTTP body data."""

        # Check if file, fo, generator, iterator.
        # If not, run through normal process.

        # Nottin' on you.
        body = None
        content_type = None

        if not data and json is not None:
            # urllib3 requires a bytes-like body. Python 2's json.dumps
            # provides this natively, but Python 3 gives a Unicode string.
            content_type = "application/json"

            try:
                body = complexjson.dumps(json, allow_nan=False)
            except ValueError as ve:
                raise InvalidJSONError(ve, request=self)

            if not isinstance(body, bytes):
                body = body.encode("utf-8")

        is_stream = all(
            [
                hasattr(data, "__iter__"),
                not isinstance(data, (basestring, list, tuple, Mapping)),
            ]
        )

        if is_stream:
            try:
                length = super_len(data)
            except (TypeError, AttributeError, UnsupportedOperation):
                length = None

            body = data

            if getattr(body, "tell", None) is not None:
                # Record the current file position before reading.
                # This will allow us to rewind a file in the event
                # of a redirect.
                try:
                    self._body_position = body.tell()
                except OSError:
                    # This differentiates from None, allowing us to catch
                    # a failed `tell()` later when trying to rewind the body
                    self._body_position = object()

            if files:
                raise NotImplementedError(
                    "Streamed bodies and files are mutually exclusive."
                )

            if length:
                self.headers["Content-Length"] = builtin_str(length)
            else:
                self.headers["Transfer-Encoding"] = "chunked"
        else:
            # Multi-part file uploads.
            if files:
                (body, content_type) = self._encode_files(files, data)
            else:
                if data:
                    body = self._encode_params(data)
                    if isinstance(data, basestring) or hasattr(data, "read"):
                        content_type = None
                    else:
                        content_type = "application/x-www-form-urlencoded"

            self.prepare_content_length(body)

            # Add content-type if it wasn't explicitly provided.
            if content_type and ("content-type" not in self.headers):
                self.headers["Content-Type"] = content_type

        self.body = body

    def prepare_content_length(self, body):
        """Prepare Content-Length header based on request method and body"""
        if body is not None:
            length = super_len(body)
            if length:
                # If length exists, set it. Otherwise, we fallback
                # to Transfer-Encoding: chunked.
                self.headers["Content-Length"] = builtin_str(length)
        elif (
            self.method not in ("GET", "HEAD")
            and self.headers.get("Content-Length") is None
        ):
            # Set Content-Length to 0 for methods that can have a body
            # but don't provide one. (i.e. not GET or HEAD)
            self.headers["Content-Length"] = "0"

    def prepare_auth(self, auth, url=""):
        """Prepares the given HTTP auth data."""

        # If no Auth is explicitly provided, extract it from the URL first.
        if auth is None:
            url_auth = get_auth_from_url(self.url)
            auth = url_auth if any(url_auth) else None

        if auth:
            if isinstance(auth, tuple) and len(auth) == 2:
                # special-case basic HTTP auth
                auth = HTTPBasicAuth(*auth)

            # Allow auth to make its changes.
            r = auth(self)

            # Update self to reflect the auth changes.
            self.__dict__.update(r.__dict__)

            # Recompute Content-Length
            self.prepare_content_length(self.body)

    def prepare_cookies(self, cookies):
        """Prepares the given HTTP cookie data.

        This function eventually generates a ``Cookie`` header from the
        given cookies using cookielib. Due to cookielib's design, the header
        will not be regenerated if it already exists, meaning this function
        can only be called once for the life of the
        :class:`PreparedRequest <PreparedRequest>` object. Any subsequent calls
        to ``prepare_cookies`` will have no actual effect, unless the "Cookie"
        header is removed beforehand.
        """
        if isinstance(cookies, cookielib.CookieJar):
            self._cookies = cookies
        else:
            self._cookies = cookiejar_from_dict(cookies)

        cookie_header = get_cookie_header(self._cookies, self)
        if cookie_header is not None:
            self.headers["Cookie"] = cookie_header

    def prepare_hooks(self, hooks):
        """Prepares the given hooks."""
        # hooks can be passed as None to the prepare method and to this
        # method. To prevent iterating over None, simply use an empty list
        # if hooks is False-y
        hooks = hooks or []
        for event in hooks:
            self.register_hook(event, hooks[event])


class Response:
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    __attrs__ = [
        "_content",
        "status_code",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
    ]

    def __init__(self):
        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-encoding']`` will return the
        #: value of a ``'Content-Encoding'`` response header.
        self.headers = CaseInsensitiveDict()

        #: File-like object representation of response (for advanced usage).
        #: Use of ``raw`` requires that ``stream=True`` be set on the request.
        #: This requirement does not apply for use internally to Requests.
        self.raw = None

        #: Final URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing r.text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request. Any redirect responses will end
        #: up here. The list is sorted from the oldest to the most recent request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A CookieJar of Cookies the server sent back.
        self.cookies = cookiejar_from_dict({})

        #: The amount of time elapsed between sending the request
        #: and the arrival of the response (as a timedelta).
        #: This property specifically measures the time taken between sending
        #: the first byte of the request and finishing parsing the headers. It
        #: is therefore unaffected by consuming the response content or the
        #: value of the ``stream`` keyword argument.
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        # Consume everything; accessing the content attribute makes
        # sure the content has been fully read.
        if not self._content_consumed:
            self.content

        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        for name, value in state.items():
            setattr(self, name, value)

        # pickled objects do not have .raw
        setattr(self, "_content_consumed", True)
        setattr(self, "raw", None)

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    def __bool__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __nonzero__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __iter__(self):
        """Allows you to use a response as an iterator."""
        return self.iter_content(128)

    @property
    def ok(self):
        """Returns True if :attr:`status_code` is less than 400, False if not.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            self.raise_for_status()
        except HTTPError:
            return False
        return True

    @property
    def is_redirect(self):
        """True if this Response is a well-formed HTTP redirect that could have
        been processed automatically (by :meth:`Session.resolve_redirects`).
        """
        return "location" in self.headers and self.status_code in REDIRECT_STATI

    @property
    def is_permanent_redirect(self):
        """True if this Response one of the permanent versions of redirect."""
        return "location" in self.headers and self.status_code in (
            codes.moved_permanently,
            codes.permanent_redirect,
        )

    @property
    def next(self):
        """Returns a PreparedRequest for the next request in a redirect chain, if there is one."""
        return self._next

    @property
    def apparent_encoding(self):
        """The apparent encoding, provided by the charset_normalizer or chardet libraries."""
        if chardet is not None:
            return chardet.detect(self.content)["encoding"]
        else:
            # If no character detection library is available, we'll fall back
            # to a standard Python utf-8 str.
            return "utf-8"

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """Iterates over the response data.  When stream=True is set on the
        request, this avoids reading the content at once into memory for
        large responses.  The chunk size is the number of bytes it should
        read into memory.  This is not necessarily the length of each item
        returned as decoding can take place.

        chunk_size must be of type int or None. A value of None will
        function differently depending on the value of `stream`.
        stream=True will read data as it arrives in whatever size the
        chunks are received. If stream=False, data is returned as
        a single chunk.

        If decode_unicode is True, content will be decoded using the best
        available encoding based on the response.
        """

        def generate():
            # Special case for urllib3.
            if hasattr(self.raw, "stream"):
                try:
                    yield from self.raw.stream(chunk_size, decode_content=True)
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(
                f"chunk_size must be an int, it is instead a {type(chunk_size)}."
            )
        # simulate reading small chunks of the content
        reused_chunks = iter_slices(self._content, chunk_size)

        stream_chunks = generate()

        chunks = reused_chunks if self._content_consumed else stream_chunks

        if decode_unicode:
            chunks = stream_decode_response_unicode(chunks, self)

        return chunks

    def iter_lines(
        self, chunk_size=ITER_CHUNK_SIZE, decode_unicode=False, delimiter=None
    ):
        """Iterates over the response data, one line at a time.  When
        stream=True is set on the request, this avoids reading the
        content at once into memory for large responses.

        .. note:: This method is not reentrant safe.
        """

        pending = None

        for chunk in self.iter_content(
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            yield from lines

        if pending is not None:
            yield pending

    @property
    def content(self):
        """Content of the response, in bytes."""

        if self._content is False:
            # Read the contents.
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0 or self.raw is None:
                self._content = None
            else:
                self._content = b"".join(self.iter_content(CONTENT_CHUNK_SIZE)) or b""

        self._content_consumed = True
        # don't need to release the connection; that's been handled by urllib3
        # since we exhausted the data.
        return self._content

    @property
    def text(self):
        """Content of the response, in unicode.

        If Response.encoding is None, encoding will be guessed using
        ``charset_normalizer`` or ``chardet``.

        The encoding of the response content is determined based solely on HTTP
        headers, following RFC 2616 to the letter. If you can take advantage of
        non-HTTP knowledge to make a better guess at the encoding, you should
        set ``r.encoding`` appropriately before accessing this property.
        """

        # Try charset from content-type
        content = None
        encoding = self.encoding

        if not self.content:
            return ""

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding = self.apparent_encoding

        # Decode unicode from given encoding.
        try:
            content = str(self.content, encoding, errors="replace")
        except (LookupError, TypeError):
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            #
            # A TypeError can be raised if encoding is None
            #
            # So we try blindly encoding.
            content = str(self.content, errors="replace")

        return content

    def json(self, **kwargs):
        r"""Decodes the JSON response body (if any) as a Python object.

        This may return a dictionary, list, etc. depending on what is in the response.

        :param \*\*kwargs: Optional arguments that ``json.loads`` takes.
        :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json.
        """

        if not self.encoding and self.content and len(self.content) > 3:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding = guess_json_utf(self.content)
            if encoding is not None:
                try:
                    return complexjson.loads(self.content.decode(encoding), **kwargs)
                except UnicodeDecodeError:
                    # Wrong UTF codec detected; usually because it's not UTF-8
                    # but some other 8-bit codec.  This is an RFC violation,
                    # and the server didn't bother to tell us what codec *was*
                    # used.
                    pass
                except JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

        try:
            return complexjson.loads(self.text, **kwargs)
        except JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    @property
    def links(self):
        """Returns the parsed header links of the response, if any."""

        header = self.headers.get("link")

        resolved_links = {}

        if header:
            links = parse_header_links(header)

            for link in links:
                key = link.get("rel") or link.get("url")
                resolved_links[key] = link

        return resolved_links

    def raise_for_status(self):
        """Raises :class:`HTTPError`, if one occurred."""

        http_error_msg = ""
        if isinstance(self.reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings. (See PR #3538)
            try:
                reason = self.reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = self.reason.decode("iso-8859-1")
        else:
            reason = self.reason

        if 400 <= self.status_code < 500:
            http_error_msg = (
                f"{self.status_code} Client Error: {reason} for url: {self.url}"
            )

        elif 500 <= self.status_code < 600:
            http_error_msg = (
                f"{self.status_code} Server Error: {reason} for url: {self.url}"
            )

        if http_error_msg:
            raise HTTPError(http_error_msg, response=self)

    def close(self):
        """Releases the connection back to the pool. Once this method has been
        called the underlying ``raw`` object must not be accessed again.

        *Note: Should not normally need to be called explicitly.*
        """
        if not self._content_consumed:
            self.raw.close()

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import generative_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import GenerativeServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class GenerativeServiceRestInterceptor:
    """Interceptor for GenerativeService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the GenerativeServiceRestTransport.

    .. code-block:: python
        class MyCustomGenerativeServiceInterceptor(GenerativeServiceRestInterceptor):
            def pre_batch_embed_contents(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_batch_embed_contents(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_count_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_embed_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_embed_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_answer(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_answer(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_stream_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_stream_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = GenerativeServiceRestTransport(interceptor=MyCustomGenerativeServiceInterceptor())
        client = GenerativeServiceClient(transport=transport)


    """

    def pre_batch_embed_contents(
        self,
        request: generative_service.BatchEmbedContentsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.BatchEmbedContentsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for batch_embed_contents

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_batch_embed_contents(
        self, response: generative_service.BatchEmbedContentsResponse
    ) -> generative_service.BatchEmbedContentsResponse:
        """Post-rpc interceptor for batch_embed_contents

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_count_tokens(
        self,
        request: generative_service.CountTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.CountTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_count_tokens(
        self, response: generative_service.CountTokensResponse
    ) -> generative_service.CountTokensResponse:
        """Post-rpc interceptor for count_tokens

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_embed_content(
        self,
        request: generative_service.EmbedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.EmbedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for embed_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_embed_content(
        self, response: generative_service.EmbedContentResponse
    ) -> generative_service.EmbedContentResponse:
        """Post-rpc interceptor for embed_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_answer(
        self,
        request: generative_service.GenerateAnswerRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.GenerateAnswerRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_answer

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_generate_answer(
        self, response: generative_service.GenerateAnswerResponse
    ) -> generative_service.GenerateAnswerResponse:
        """Post-rpc interceptor for generate_answer

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_content(
        self,
        request: generative_service.GenerateContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_generate_content(
        self, response: generative_service.GenerateContentResponse
    ) -> generative_service.GenerateContentResponse:
        """Post-rpc interceptor for generate_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_stream_generate_content(
        self,
        request: generative_service.GenerateContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_stream_generate_content(
        self, response: rest_streaming.ResponseIterator
    ) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class GenerativeServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: GenerativeServiceRestInterceptor


class GenerativeServiceRestTransport(GenerativeServiceTransport):
    """REST backend transport for GenerativeService.

    API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[GenerativeServiceRestInterceptor] = None,
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

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or GenerativeServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _BatchEmbedContents(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("BatchEmbedContents")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.BatchEmbedContentsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.BatchEmbedContentsResponse:
            r"""Call the batch embed contents method over HTTP.

            Args:
                request (~.generative_service.BatchEmbedContentsRequest):
                    The request object. Batch request to get embeddings from
                the model for a list of prompts.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.BatchEmbedContentsResponse:
                    The response to a ``BatchEmbedContentsRequest``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:batchEmbedContents",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_batch_embed_contents(
                request, metadata
            )
            pb_request = generative_service.BatchEmbedContentsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.BatchEmbedContentsResponse()
            pb_resp = generative_service.BatchEmbedContentsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_batch_embed_contents(resp)
            return resp

    class _CountTokens(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("CountTokens")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.CountTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.CountTokensResponse:
            r"""Call the count tokens method over HTTP.

            Args:
                request (~.generative_service.CountTokensRequest):
                    The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.CountTokensResponse:
                    A response from ``CountTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:countTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_tokens(request, metadata)
            pb_request = generative_service.CountTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.CountTokensResponse()
            pb_resp = generative_service.CountTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_tokens(resp)
            return resp

    class _EmbedContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("EmbedContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.EmbedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.EmbedContentResponse:
            r"""Call the embed content method over HTTP.

            Args:
                request (~.generative_service.EmbedContentRequest):
                    The request object. Request containing the ``Content`` for the model to
                embed.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.EmbedContentResponse:
                    The response to an ``EmbedContentRequest``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:embedContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_embed_content(request, metadata)
            pb_request = generative_service.EmbedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.EmbedContentResponse()
            pb_resp = generative_service.EmbedContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_embed_content(resp)
            return resp

    class _GenerateAnswer(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("GenerateAnswer")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.GenerateAnswerRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.GenerateAnswerResponse:
            r"""Call the generate answer method over HTTP.

            Args:
                request (~.generative_service.GenerateAnswerRequest):
                    The request object. Request to generate a grounded answer
                from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.GenerateAnswerResponse:
                    Response from the model for a
                grounded answer.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:generateAnswer",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_answer(request, metadata)
            pb_request = generative_service.GenerateAnswerRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.GenerateAnswerResponse()
            pb_resp = generative_service.GenerateAnswerResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_answer(resp)
            return resp

    class _GenerateContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("GenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.GenerateContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.GenerateContentResponse:
            r"""Call the generate content method over HTTP.

            Args:
                request (~.generative_service.GenerateContentRequest):
                    The request object. Request to generate a completion from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.GenerateContentResponse:
                    Response from the model supporting multiple candidates.

                Note on safety ratings and content filtering. They are
                reported for both prompt in
                ``GenerateContentResponse.prompt_feedback`` and for each
                candidate in ``finish_reason`` and in
                ``safety_ratings``. The API contract is that:

                -  either all requested candidates are returned or no
                   candidates at all
                -  no candidates are returned only if there was
                   something wrong with the prompt (see
                   ``prompt_feedback``)
                -  feedback on each candidate is reported on
                   ``finish_reason`` and ``safety_ratings``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:generateContent",
                    "body": "*",
                },
                {
                    "method": "post",
                    "uri": "/v1beta/{model=tunedModels/*}:generateContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_content(
                request, metadata
            )
            pb_request = generative_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.GenerateContentResponse()
            pb_resp = generative_service.GenerateContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_content(resp)
            return resp

    class _StreamGenerateContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("StreamGenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.GenerateContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> rest_streaming.ResponseIterator:
            r"""Call the stream generate content method over HTTP.

            Args:
                request (~.generative_service.GenerateContentRequest):
                    The request object. Request to generate a completion from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.GenerateContentResponse:
                    Response from the model supporting multiple candidates.

                Note on safety ratings and content filtering. They are
                reported for both prompt in
                ``GenerateContentResponse.prompt_feedback`` and for each
                candidate in ``finish_reason`` and in
                ``safety_ratings``. The API contract is that:

                -  either all requested candidates are returned or no
                   candidates at all
                -  no candidates are returned only if there was
                   something wrong with the prompt (see
                   ``prompt_feedback``)
                -  feedback on each candidate is reported on
                   ``finish_reason`` and ``safety_ratings``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:streamGenerateContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_stream_generate_content(
                request, metadata
            )
            pb_request = generative_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(
                response, generative_service.GenerateContentResponse
            )
            resp = self._interceptor.post_stream_generate_content(resp)
            return resp

    @property
    def batch_embed_contents(
        self,
    ) -> Callable[
        [generative_service.BatchEmbedContentsRequest],
        generative_service.BatchEmbedContentsResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._BatchEmbedContents(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def count_tokens(
        self,
    ) -> Callable[
        [generative_service.CountTokensRequest], generative_service.CountTokensResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def embed_content(
        self,
    ) -> Callable[
        [generative_service.EmbedContentRequest],
        generative_service.EmbedContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._EmbedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_answer(
        self,
    ) -> Callable[
        [generative_service.GenerateAnswerRequest],
        generative_service.GenerateAnswerResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateAnswer(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def stream_generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamGenerateContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("GenerativeServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import PermissionServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class PermissionServiceRestInterceptor:
    """Interceptor for PermissionService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the PermissionServiceRestTransport.

    .. code-block:: python
        class MyCustomPermissionServiceInterceptor(PermissionServiceRestInterceptor):
            def pre_create_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_permissions(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_permissions(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_transfer_ownership(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_transfer_ownership(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_update_permission(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_permission(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = PermissionServiceRestTransport(interceptor=MyCustomPermissionServiceInterceptor())
        client = PermissionServiceClient(transport=transport)


    """

    def pre_create_permission(
        self,
        request: permission_service.CreatePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.CreatePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_create_permission(
        self, response: gag_permission.Permission
    ) -> gag_permission.Permission:
        """Post-rpc interceptor for create_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_permission(
        self,
        request: permission_service.DeletePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.DeletePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def pre_get_permission(
        self,
        request: permission_service.GetPermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.GetPermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_get_permission(
        self, response: permission.Permission
    ) -> permission.Permission:
        """Post-rpc interceptor for get_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_list_permissions(
        self,
        request: permission_service.ListPermissionsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.ListPermissionsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_permissions

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_list_permissions(
        self, response: permission_service.ListPermissionsResponse
    ) -> permission_service.ListPermissionsResponse:
        """Post-rpc interceptor for list_permissions

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_transfer_ownership(
        self,
        request: permission_service.TransferOwnershipRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.TransferOwnershipRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for transfer_ownership

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_transfer_ownership(
        self, response: permission_service.TransferOwnershipResponse
    ) -> permission_service.TransferOwnershipResponse:
        """Post-rpc interceptor for transfer_ownership

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response

    def pre_update_permission(
        self,
        request: permission_service.UpdatePermissionRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[permission_service.UpdatePermissionRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for update_permission

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PermissionService server.
        """
        return request, metadata

    def post_update_permission(
        self, response: gag_permission.Permission
    ) -> gag_permission.Permission:
        """Post-rpc interceptor for update_permission

        Override in a subclass to manipulate the response
        after it is returned by the PermissionService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class PermissionServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: PermissionServiceRestInterceptor


class PermissionServiceRestTransport(PermissionServiceTransport):
    """REST backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[PermissionServiceRestInterceptor] = None,
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

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or PermissionServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CreatePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("CreatePermission")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.CreatePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_permission.Permission:
            r"""Call the create permission method over HTTP.

            Args:
                request (~.permission_service.CreatePermissionRequest):
                    The request object. Request to create a ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_permission.Permission:
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

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{parent=tunedModels/*}/permissions",
                    "body": "permission",
                },
                {
                    "method": "post",
                    "uri": "/v1beta/{parent=corpora/*}/permissions",
                    "body": "permission",
                },
            ]
            request, metadata = self._interceptor.pre_create_permission(
                request, metadata
            )
            pb_request = permission_service.CreatePermissionRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = gag_permission.Permission()
            pb_resp = gag_permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_permission(resp)
            return resp

    class _DeletePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("DeletePermission")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.DeletePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete permission method over HTTP.

            Args:
                request (~.permission_service.DeletePermissionRequest):
                    The request object. Request to delete the ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta/{name=tunedModels/*/permissions/*}",
                },
                {
                    "method": "delete",
                    "uri": "/v1beta/{name=corpora/*/permissions/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_permission(
                request, metadata
            )
            pb_request = permission_service.DeletePermissionRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

    class _GetPermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("GetPermission")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.GetPermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission.Permission:
            r"""Call the get permission method over HTTP.

            Args:
                request (~.permission_service.GetPermissionRequest):
                    The request object. Request for getting information about a specific
                ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission.Permission:
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

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{name=tunedModels/*/permissions/*}",
                },
                {
                    "method": "get",
                    "uri": "/v1beta/{name=corpora/*/permissions/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_permission(request, metadata)
            pb_request = permission_service.GetPermissionRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = permission.Permission()
            pb_resp = permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_permission(resp)
            return resp

    class _ListPermissions(PermissionServiceRestStub):
        def __hash__(self):
            return hash("ListPermissions")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.ListPermissionsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission_service.ListPermissionsResponse:
            r"""Call the list permissions method over HTTP.

            Args:
                request (~.permission_service.ListPermissionsRequest):
                    The request object. Request for listing permissions.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission_service.ListPermissionsResponse:
                    Response from ``ListPermissions`` containing a paginated
                list of permissions.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{parent=tunedModels/*}/permissions",
                },
                {
                    "method": "get",
                    "uri": "/v1beta/{parent=corpora/*}/permissions",
                },
            ]
            request, metadata = self._interceptor.pre_list_permissions(
                request, metadata
            )
            pb_request = permission_service.ListPermissionsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = permission_service.ListPermissionsResponse()
            pb_resp = permission_service.ListPermissionsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_permissions(resp)
            return resp

    class _TransferOwnership(PermissionServiceRestStub):
        def __hash__(self):
            return hash("TransferOwnership")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.TransferOwnershipRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> permission_service.TransferOwnershipResponse:
            r"""Call the transfer ownership method over HTTP.

            Args:
                request (~.permission_service.TransferOwnershipRequest):
                    The request object. Request to transfer the ownership of
                the tuned model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.permission_service.TransferOwnershipResponse:
                    Response from ``TransferOwnership``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{name=tunedModels/*}:transferOwnership",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_transfer_ownership(
                request, metadata
            )
            pb_request = permission_service.TransferOwnershipRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = permission_service.TransferOwnershipResponse()
            pb_resp = permission_service.TransferOwnershipResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_transfer_ownership(resp)
            return resp

    class _UpdatePermission(PermissionServiceRestStub):
        def __hash__(self):
            return hash("UpdatePermission")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {
            "updateMask": {},
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: permission_service.UpdatePermissionRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_permission.Permission:
            r"""Call the update permission method over HTTP.

            Args:
                request (~.permission_service.UpdatePermissionRequest):
                    The request object. Request to update the ``Permission``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_permission.Permission:
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

            http_options: List[Dict[str, str]] = [
                {
                    "method": "patch",
                    "uri": "/v1beta/{permission.name=tunedModels/*/permissions/*}",
                    "body": "permission",
                },
                {
                    "method": "patch",
                    "uri": "/v1beta/{permission.name=corpora/*/permissions/*}",
                    "body": "permission",
                },
            ]
            request, metadata = self._interceptor.pre_update_permission(
                request, metadata
            )
            pb_request = permission_service.UpdatePermissionRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = gag_permission.Permission()
            pb_resp = gag_permission.Permission.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_update_permission(resp)
            return resp

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest], gag_permission.Permission
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreatePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_permission(
        self,
    ) -> Callable[[permission_service.DeletePermissionRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeletePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_permission(
        self,
    ) -> Callable[[permission_service.GetPermissionRequest], permission.Permission]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetPermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        permission_service.ListPermissionsResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListPermissions(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        permission_service.TransferOwnershipResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._TransferOwnership(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest], gag_permission.Permission
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdatePermission(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("PermissionServiceRestTransport",)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\models.py ===
"""
requests.models
~~~~~~~~~~~~~~~

This module contains the primary objects that power Requests.
"""

import datetime

# Import encoding now, to avoid implicit import later.
# Implicit import within threads may cause LookupError when standard library is in a ZIP,
# such as in Embedded Python. See https://github.com/psf/requests/issues/3578.
import encodings.idna  # noqa: F401
from io import UnsupportedOperation

from pip._vendor.urllib3.exceptions import (
    DecodeError,
    LocationParseError,
    ProtocolError,
    ReadTimeoutError,
    SSLError,
)
from pip._vendor.urllib3.fields import RequestField
from pip._vendor.urllib3.filepost import encode_multipart_formdata
from pip._vendor.urllib3.util import parse_url

from ._internal_utils import to_native_string, unicode_is_ascii
from .auth import HTTPBasicAuth
from .compat import (
    Callable,
    JSONDecodeError,
    Mapping,
    basestring,
    builtin_str,
    chardet,
    cookielib,
)
from .compat import json as complexjson
from .compat import urlencode, urlsplit, urlunparse
from .cookies import _copy_cookie_jar, cookiejar_from_dict, get_cookie_header
from .exceptions import (
    ChunkedEncodingError,
    ConnectionError,
    ContentDecodingError,
    HTTPError,
    InvalidJSONError,
    InvalidURL,
)
from .exceptions import JSONDecodeError as RequestsJSONDecodeError
from .exceptions import MissingSchema
from .exceptions import SSLError as RequestsSSLError
from .exceptions import StreamConsumedError
from .hooks import default_hooks
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (
    check_header_validity,
    get_auth_from_url,
    guess_filename,
    guess_json_utf,
    iter_slices,
    parse_header_links,
    requote_uri,
    stream_decode_response_unicode,
    super_len,
    to_key_val_list,
)

#: The set of HTTP status codes that indicate an automatically
#: processable redirect.
REDIRECT_STATI = (
    codes.moved,  # 301
    codes.found,  # 302
    codes.other,  # 303
    codes.temporary_redirect,  # 307
    codes.permanent_redirect,  # 308
)

DEFAULT_REDIRECT_LIMIT = 30
CONTENT_CHUNK_SIZE = 10 * 1024
ITER_CHUNK_SIZE = 512


class RequestEncodingMixin:
    @property
    def path_url(self):
        """Build the path URL to use."""

        url = []

        p = urlsplit(self.url)

        path = p.path
        if not path:
            path = "/"

        url.append(path)

        query = p.query
        if query:
            url.append("?")
            url.append(query)

        return "".join(url)

    @staticmethod
    def _encode_params(data):
        """Encode parameters in a piece of data.

        Will successfully encode parameters when passed as a dict or a list of
        2-tuples. Order is retained if data is a list of 2-tuples but arbitrary
        if parameters are supplied as a dict.
        """

        if isinstance(data, (str, bytes)):
            return data
        elif hasattr(data, "read"):
            return data
        elif hasattr(data, "__iter__"):
            result = []
            for k, vs in to_key_val_list(data):
                if isinstance(vs, basestring) or not hasattr(vs, "__iter__"):
                    vs = [vs]
                for v in vs:
                    if v is not None:
                        result.append(
                            (
                                k.encode("utf-8") if isinstance(k, str) else k,
                                v.encode("utf-8") if isinstance(v, str) else v,
                            )
                        )
            return urlencode(result, doseq=True)
        else:
            return data

    @staticmethod
    def _encode_files(files, data):
        """Build the body for a multipart/form-data request.

        Will successfully encode files when passed as a dict or a list of
        tuples. Order is retained if data is a list of tuples but arbitrary
        if parameters are supplied as a dict.
        The tuples may be 2-tuples (filename, fileobj), 3-tuples (filename, fileobj, contentype)
        or 4-tuples (filename, fileobj, contentype, custom_headers).
        """
        if not files:
            raise ValueError("Files must be provided.")
        elif isinstance(data, basestring):
            raise ValueError("Data must not be a string.")

        new_fields = []
        fields = to_key_val_list(data or {})
        files = to_key_val_list(files or {})

        for field, val in fields:
            if isinstance(val, basestring) or not hasattr(val, "__iter__"):
                val = [val]
            for v in val:
                if v is not None:
                    # Don't call str() on bytestrings: in Py3 it all goes wrong.
                    if not isinstance(v, bytes):
                        v = str(v)

                    new_fields.append(
                        (
                            field.decode("utf-8")
                            if isinstance(field, bytes)
                            else field,
                            v.encode("utf-8") if isinstance(v, str) else v,
                        )
                    )

        for k, v in files:
            # support for explicit filename
            ft = None
            fh = None
            if isinstance(v, (tuple, list)):
                if len(v) == 2:
                    fn, fp = v
                elif len(v) == 3:
                    fn, fp, ft = v
                else:
                    fn, fp, ft, fh = v
            else:
                fn = guess_filename(v) or k
                fp = v

            if isinstance(fp, (str, bytes, bytearray)):
                fdata = fp
            elif hasattr(fp, "read"):
                fdata = fp.read()
            elif fp is None:
                continue
            else:
                fdata = fp

            rf = RequestField(name=k, data=fdata, filename=fn, headers=fh)
            rf.make_multipart(content_type=ft)
            new_fields.append(rf)

        body, content_type = encode_multipart_formdata(new_fields)

        return body, content_type


class RequestHooksMixin:
    def register_hook(self, event, hook):
        """Properly register a hook."""

        if event not in self.hooks:
            raise ValueError(f'Unsupported event specified, with event name "{event}"')

        if isinstance(hook, Callable):
            self.hooks[event].append(hook)
        elif hasattr(hook, "__iter__"):
            self.hooks[event].extend(h for h in hook if isinstance(h, Callable))

    def deregister_hook(self, event, hook):
        """Deregister a previously registered hook.
        Returns True if the hook existed, False if not.
        """

        try:
            self.hooks[event].remove(hook)
            return True
        except ValueError:
            return False


class Request(RequestHooksMixin):
    """A user-created :class:`Request <Request>` object.

    Used to prepare a :class:`PreparedRequest <PreparedRequest>`, which is sent to the server.

    :param method: HTTP method to use.
    :param url: URL to send.
    :param headers: dictionary of headers to send.
    :param files: dictionary of {filename: fileobject} files to multipart upload.
    :param data: the body to attach to the request. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param json: json for the body to attach to the request (if files or data is not specified).
    :param params: URL parameters to append to the URL. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param auth: Auth handler or (user, pass) tuple.
    :param cookies: dictionary or CookieJar of cookies to attach to this request.
    :param hooks: dictionary of callback hooks, for internal usage.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> req.prepare()
      <PreparedRequest [GET]>
    """

    def __init__(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        # Default empty dicts for dict params.
        data = [] if data is None else data
        files = [] if files is None else files
        headers = {} if headers is None else headers
        params = {} if params is None else params
        hooks = {} if hooks is None else hooks

        self.hooks = default_hooks()
        for k, v in list(hooks.items()):
            self.register_hook(event=k, hook=v)

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.json = json
        self.params = params
        self.auth = auth
        self.cookies = cookies

    def __repr__(self):
        return f"<Request [{self.method}]>"

    def prepare(self):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it."""
        p = PreparedRequest()
        p.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
        )
        return p


class PreparedRequest(RequestEncodingMixin, RequestHooksMixin):
    """The fully mutable :class:`PreparedRequest <PreparedRequest>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> r = req.prepare()
      >>> r
      <PreparedRequest [GET]>

      >>> s = requests.Session()
      >>> s.send(r)
      <Response [200]>
    """

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        # The `CookieJar` used to create the Cookie header will be stored here
        # after prepare_cookies is called
        self._cookies = None
        #: request body to send to the server.
        self.body = None
        #: dictionary of callback hooks, for internal usage.
        self.hooks = default_hooks()
        #: integer denoting starting position of a readable file-like body.
        self._body_position = None

    def prepare(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        """Prepares the entire request with the given parameters."""

        self.prepare_method(method)
        self.prepare_url(url, params)
        self.prepare_headers(headers)
        self.prepare_cookies(cookies)
        self.prepare_body(data, files, json)
        self.prepare_auth(auth, url)

        # Note that prepare_auth must be last to enable authentication schemes
        # such as OAuth to work on a fully prepared request.

        # This MUST go after prepare_auth. Authenticators could add a hook
        self.prepare_hooks(hooks)

    def __repr__(self):
        return f"<PreparedRequest [{self.method}]>"

    def copy(self):
        p = PreparedRequest()
        p.method = self.method
        p.url = self.url
        p.headers = self.headers.copy() if self.headers is not None else None
        p._cookies = _copy_cookie_jar(self._cookies)
        p.body = self.body
        p.hooks = self.hooks
        p._body_position = self._body_position
        return p

    def prepare_method(self, method):
        """Prepares the given HTTP method."""
        self.method = method
        if self.method is not None:
            self.method = to_native_string(self.method.upper())

    @staticmethod
    def _get_idna_encoded_host(host):
        from pip._vendor import idna

        try:
            host = idna.encode(host, uts46=True).decode("utf-8")
        except idna.IDNAError:
            raise UnicodeError
        return host

    def prepare_url(self, url, params):
        """Prepares the given HTTP URL."""
        #: Accept objects that have string representations.
        #: We're unable to blindly call unicode/str functions
        #: as this will include the bytestring indicator (b'')
        #: on python 3.x.
        #: https://github.com/psf/requests/pull/2238
        if isinstance(url, bytes):
            url = url.decode("utf8")
        else:
            url = str(url)

        # Remove leading whitespaces from url
        url = url.lstrip()

        # Don't do any URL preparation for non-HTTP schemes like `mailto`,
        # `data` etc to work around exceptions from `url_parse`, which
        # handles RFC 3986 only.
        if ":" in url and not url.lower().startswith("http"):
            self.url = url
            return

        # Support for unicode domain names and paths.
        try:
            scheme, auth, host, port, path, query, fragment = parse_url(url)
        except LocationParseError as e:
            raise InvalidURL(*e.args)

        if not scheme:
            raise MissingSchema(
                f"Invalid URL {url!r}: No scheme supplied. "
                f"Perhaps you meant https://{url}?"
            )

        if not host:
            raise InvalidURL(f"Invalid URL {url!r}: No host supplied")

        # In general, we want to try IDNA encoding the hostname if the string contains
        # non-ASCII characters. This allows users to automatically get the correct IDNA
        # behaviour. For strings containing only ASCII characters, we need to also verify
        # it doesn't start with a wildcard (*), before allowing the unencoded hostname.
        if not unicode_is_ascii(host):
            try:
                host = self._get_idna_encoded_host(host)
            except UnicodeError:
                raise InvalidURL("URL has an invalid label.")
        elif host.startswith(("*", ".")):
            raise InvalidURL("URL has an invalid label.")

        # Carefully reconstruct the network location
        netloc = auth or ""
        if netloc:
            netloc += "@"
        netloc += host
        if port:
            netloc += f":{port}"

        # Bare domains aren't valid URLs.
        if not path:
            path = "/"

        if isinstance(params, (str, bytes)):
            params = to_native_string(params)

        enc_params = self._encode_params(params)
        if enc_params:
            if query:
                query = f"{query}&{enc_params}"
            else:
                query = enc_params

        url = requote_uri(urlunparse([scheme, netloc, path, None, query, fragment]))
        self.url = url

    def prepare_headers(self, headers):
        """Prepares the given HTTP headers."""

        self.headers = CaseInsensitiveDict()
        if headers:
            for header in headers.items():
                # Raise exception on invalid header value.
                check_header_validity(header)
                name, value = header
                self.headers[to_native_string(name)] = value

    def prepare_body(self, data, files, json=None):
        """Prepares the given HTTP body data."""

        # Check if file, fo, generator, iterator.
        # If not, run through normal process.

        # Nottin' on you.
        body = None
        content_type = None

        if not data and json is not None:
            # urllib3 requires a bytes-like body. Python 2's json.dumps
            # provides this natively, but Python 3 gives a Unicode string.
            content_type = "application/json"

            try:
                body = complexjson.dumps(json, allow_nan=False)
            except ValueError as ve:
                raise InvalidJSONError(ve, request=self)

            if not isinstance(body, bytes):
                body = body.encode("utf-8")

        is_stream = all(
            [
                hasattr(data, "__iter__"),
                not isinstance(data, (basestring, list, tuple, Mapping)),
            ]
        )

        if is_stream:
            try:
                length = super_len(data)
            except (TypeError, AttributeError, UnsupportedOperation):
                length = None

            body = data

            if getattr(body, "tell", None) is not None:
                # Record the current file position before reading.
                # This will allow us to rewind a file in the event
                # of a redirect.
                try:
                    self._body_position = body.tell()
                except OSError:
                    # This differentiates from None, allowing us to catch
                    # a failed `tell()` later when trying to rewind the body
                    self._body_position = object()

            if files:
                raise NotImplementedError(
                    "Streamed bodies and files are mutually exclusive."
                )

            if length:
                self.headers["Content-Length"] = builtin_str(length)
            else:
                self.headers["Transfer-Encoding"] = "chunked"
        else:
            # Multi-part file uploads.
            if files:
                (body, content_type) = self._encode_files(files, data)
            else:
                if data:
                    body = self._encode_params(data)
                    if isinstance(data, basestring) or hasattr(data, "read"):
                        content_type = None
                    else:
                        content_type = "application/x-www-form-urlencoded"

            self.prepare_content_length(body)

            # Add content-type if it wasn't explicitly provided.
            if content_type and ("content-type" not in self.headers):
                self.headers["Content-Type"] = content_type

        self.body = body

    def prepare_content_length(self, body):
        """Prepare Content-Length header based on request method and body"""
        if body is not None:
            length = super_len(body)
            if length:
                # If length exists, set it. Otherwise, we fallback
                # to Transfer-Encoding: chunked.
                self.headers["Content-Length"] = builtin_str(length)
        elif (
            self.method not in ("GET", "HEAD")
            and self.headers.get("Content-Length") is None
        ):
            # Set Content-Length to 0 for methods that can have a body
            # but don't provide one. (i.e. not GET or HEAD)
            self.headers["Content-Length"] = "0"

    def prepare_auth(self, auth, url=""):
        """Prepares the given HTTP auth data."""

        # If no Auth is explicitly provided, extract it from the URL first.
        if auth is None:
            url_auth = get_auth_from_url(self.url)
            auth = url_auth if any(url_auth) else None

        if auth:
            if isinstance(auth, tuple) and len(auth) == 2:
                # special-case basic HTTP auth
                auth = HTTPBasicAuth(*auth)

            # Allow auth to make its changes.
            r = auth(self)

            # Update self to reflect the auth changes.
            self.__dict__.update(r.__dict__)

            # Recompute Content-Length
            self.prepare_content_length(self.body)

    def prepare_cookies(self, cookies):
        """Prepares the given HTTP cookie data.

        This function eventually generates a ``Cookie`` header from the
        given cookies using cookielib. Due to cookielib's design, the header
        will not be regenerated if it already exists, meaning this function
        can only be called once for the life of the
        :class:`PreparedRequest <PreparedRequest>` object. Any subsequent calls
        to ``prepare_cookies`` will have no actual effect, unless the "Cookie"
        header is removed beforehand.
        """
        if isinstance(cookies, cookielib.CookieJar):
            self._cookies = cookies
        else:
            self._cookies = cookiejar_from_dict(cookies)

        cookie_header = get_cookie_header(self._cookies, self)
        if cookie_header is not None:
            self.headers["Cookie"] = cookie_header

    def prepare_hooks(self, hooks):
        """Prepares the given hooks."""
        # hooks can be passed as None to the prepare method and to this
        # method. To prevent iterating over None, simply use an empty list
        # if hooks is False-y
        hooks = hooks or []
        for event in hooks:
            self.register_hook(event, hooks[event])


class Response:
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    __attrs__ = [
        "_content",
        "status_code",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
    ]

    def __init__(self):
        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-encoding']`` will return the
        #: value of a ``'Content-Encoding'`` response header.
        self.headers = CaseInsensitiveDict()

        #: File-like object representation of response (for advanced usage).
        #: Use of ``raw`` requires that ``stream=True`` be set on the request.
        #: This requirement does not apply for use internally to Requests.
        self.raw = None

        #: Final URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing r.text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request. Any redirect responses will end
        #: up here. The list is sorted from the oldest to the most recent request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A CookieJar of Cookies the server sent back.
        self.cookies = cookiejar_from_dict({})

        #: The amount of time elapsed between sending the request
        #: and the arrival of the response (as a timedelta).
        #: This property specifically measures the time taken between sending
        #: the first byte of the request and finishing parsing the headers. It
        #: is therefore unaffected by consuming the response content or the
        #: value of the ``stream`` keyword argument.
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        # Consume everything; accessing the content attribute makes
        # sure the content has been fully read.
        if not self._content_consumed:
            self.content

        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        for name, value in state.items():
            setattr(self, name, value)

        # pickled objects do not have .raw
        setattr(self, "_content_consumed", True)
        setattr(self, "raw", None)

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    def __bool__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __nonzero__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __iter__(self):
        """Allows you to use a response as an iterator."""
        return self.iter_content(128)

    @property
    def ok(self):
        """Returns True if :attr:`status_code` is less than 400, False if not.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            self.raise_for_status()
        except HTTPError:
            return False
        return True

    @property
    def is_redirect(self):
        """True if this Response is a well-formed HTTP redirect that could have
        been processed automatically (by :meth:`Session.resolve_redirects`).
        """
        return "location" in self.headers and self.status_code in REDIRECT_STATI

    @property
    def is_permanent_redirect(self):
        """True if this Response one of the permanent versions of redirect."""
        return "location" in self.headers and self.status_code in (
            codes.moved_permanently,
            codes.permanent_redirect,
        )

    @property
    def next(self):
        """Returns a PreparedRequest for the next request in a redirect chain, if there is one."""
        return self._next

    @property
    def apparent_encoding(self):
        """The apparent encoding, provided by the charset_normalizer or chardet libraries."""
        if chardet is not None:
            return chardet.detect(self.content)["encoding"]
        else:
            # If no character detection library is available, we'll fall back
            # to a standard Python utf-8 str.
            return "utf-8"

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """Iterates over the response data.  When stream=True is set on the
        request, this avoids reading the content at once into memory for
        large responses.  The chunk size is the number of bytes it should
        read into memory.  This is not necessarily the length of each item
        returned as decoding can take place.

        chunk_size must be of type int or None. A value of None will
        function differently depending on the value of `stream`.
        stream=True will read data as it arrives in whatever size the
        chunks are received. If stream=False, data is returned as
        a single chunk.

        If decode_unicode is True, content will be decoded using the best
        available encoding based on the response.
        """

        def generate():
            # Special case for urllib3.
            if hasattr(self.raw, "stream"):
                try:
                    yield from self.raw.stream(chunk_size, decode_content=True)
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(
                f"chunk_size must be an int, it is instead a {type(chunk_size)}."
            )
        # simulate reading small chunks of the content
        reused_chunks = iter_slices(self._content, chunk_size)

        stream_chunks = generate()

        chunks = reused_chunks if self._content_consumed else stream_chunks

        if decode_unicode:
            chunks = stream_decode_response_unicode(chunks, self)

        return chunks

    def iter_lines(
        self, chunk_size=ITER_CHUNK_SIZE, decode_unicode=False, delimiter=None
    ):
        """Iterates over the response data, one line at a time.  When
        stream=True is set on the request, this avoids reading the
        content at once into memory for large responses.

        .. note:: This method is not reentrant safe.
        """

        pending = None

        for chunk in self.iter_content(
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            yield from lines

        if pending is not None:
            yield pending

    @property
    def content(self):
        """Content of the response, in bytes."""

        if self._content is False:
            # Read the contents.
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0 or self.raw is None:
                self._content = None
            else:
                self._content = b"".join(self.iter_content(CONTENT_CHUNK_SIZE)) or b""

        self._content_consumed = True
        # don't need to release the connection; that's been handled by urllib3
        # since we exhausted the data.
        return self._content

    @property
    def text(self):
        """Content of the response, in unicode.

        If Response.encoding is None, encoding will be guessed using
        ``charset_normalizer`` or ``chardet``.

        The encoding of the response content is determined based solely on HTTP
        headers, following RFC 2616 to the letter. If you can take advantage of
        non-HTTP knowledge to make a better guess at the encoding, you should
        set ``r.encoding`` appropriately before accessing this property.
        """

        # Try charset from content-type
        content = None
        encoding = self.encoding

        if not self.content:
            return ""

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding = self.apparent_encoding

        # Decode unicode from given encoding.
        try:
            content = str(self.content, encoding, errors="replace")
        except (LookupError, TypeError):
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            #
            # A TypeError can be raised if encoding is None
            #
            # So we try blindly encoding.
            content = str(self.content, errors="replace")

        return content

    def json(self, **kwargs):
        r"""Returns the json-encoded content of a response, if any.

        :param \*\*kwargs: Optional arguments that ``json.loads`` takes.
        :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json.
        """

        if not self.encoding and self.content and len(self.content) > 3:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding = guess_json_utf(self.content)
            if encoding is not None:
                try:
                    return complexjson.loads(self.content.decode(encoding), **kwargs)
                except UnicodeDecodeError:
                    # Wrong UTF codec detected; usually because it's not UTF-8
                    # but some other 8-bit codec.  This is an RFC violation,
                    # and the server didn't bother to tell us what codec *was*
                    # used.
                    pass
                except JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

        try:
            return complexjson.loads(self.text, **kwargs)
        except JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    @property
    def links(self):
        """Returns the parsed header links of the response, if any."""

        header = self.headers.get("link")

        resolved_links = {}

        if header:
            links = parse_header_links(header)

            for link in links:
                key = link.get("rel") or link.get("url")
                resolved_links[key] = link

        return resolved_links

    def raise_for_status(self):
        """Raises :class:`HTTPError`, if one occurred."""

        http_error_msg = ""
        if isinstance(self.reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings. (See PR #3538)
            try:
                reason = self.reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = self.reason.decode("iso-8859-1")
        else:
            reason = self.reason

        if 400 <= self.status_code < 500:
            http_error_msg = (
                f"{self.status_code} Client Error: {reason} for url: {self.url}"
            )

        elif 500 <= self.status_code < 600:
            http_error_msg = (
                f"{self.status_code} Server Error: {reason} for url: {self.url}"
            )

        if http_error_msg:
            raise HTTPError(http_error_msg, response=self)

    def close(self):
        """Releases the connection back to the pool. Once this method has been
        called the underlying ``raw`` object must not be accessed again.

        *Note: Should not normally need to be called explicitly.*
        """
        if not self._content_consumed:
            self.raw.close()

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\models.py ===
"""
requests.models
~~~~~~~~~~~~~~~

This module contains the primary objects that power Requests.
"""

import datetime

# Import encoding now, to avoid implicit import later.
# Implicit import within threads may cause LookupError when standard library is in a ZIP,
# such as in Embedded Python. See https://github.com/psf/requests/issues/3578.
import encodings.idna  # noqa: F401
from io import UnsupportedOperation

from pip._vendor.urllib3.exceptions import (
    DecodeError,
    LocationParseError,
    ProtocolError,
    ReadTimeoutError,
    SSLError,
)
from pip._vendor.urllib3.fields import RequestField
from pip._vendor.urllib3.filepost import encode_multipart_formdata
from pip._vendor.urllib3.util import parse_url

from ._internal_utils import to_native_string, unicode_is_ascii
from .auth import HTTPBasicAuth
from .compat import (
    Callable,
    JSONDecodeError,
    Mapping,
    basestring,
    builtin_str,
    chardet,
    cookielib,
)
from .compat import json as complexjson
from .compat import urlencode, urlsplit, urlunparse
from .cookies import _copy_cookie_jar, cookiejar_from_dict, get_cookie_header
from .exceptions import (
    ChunkedEncodingError,
    ConnectionError,
    ContentDecodingError,
    HTTPError,
    InvalidJSONError,
    InvalidURL,
)
from .exceptions import JSONDecodeError as RequestsJSONDecodeError
from .exceptions import MissingSchema
from .exceptions import SSLError as RequestsSSLError
from .exceptions import StreamConsumedError
from .hooks import default_hooks
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (
    check_header_validity,
    get_auth_from_url,
    guess_filename,
    guess_json_utf,
    iter_slices,
    parse_header_links,
    requote_uri,
    stream_decode_response_unicode,
    super_len,
    to_key_val_list,
)

#: The set of HTTP status codes that indicate an automatically
#: processable redirect.
REDIRECT_STATI = (
    codes.moved,  # 301
    codes.found,  # 302
    codes.other,  # 303
    codes.temporary_redirect,  # 307
    codes.permanent_redirect,  # 308
)

DEFAULT_REDIRECT_LIMIT = 30
CONTENT_CHUNK_SIZE = 10 * 1024
ITER_CHUNK_SIZE = 512


class RequestEncodingMixin:
    @property
    def path_url(self):
        """Build the path URL to use."""

        url = []

        p = urlsplit(self.url)

        path = p.path
        if not path:
            path = "/"

        url.append(path)

        query = p.query
        if query:
            url.append("?")
            url.append(query)

        return "".join(url)

    @staticmethod
    def _encode_params(data):
        """Encode parameters in a piece of data.

        Will successfully encode parameters when passed as a dict or a list of
        2-tuples. Order is retained if data is a list of 2-tuples but arbitrary
        if parameters are supplied as a dict.
        """

        if isinstance(data, (str, bytes)):
            return data
        elif hasattr(data, "read"):
            return data
        elif hasattr(data, "__iter__"):
            result = []
            for k, vs in to_key_val_list(data):
                if isinstance(vs, basestring) or not hasattr(vs, "__iter__"):
                    vs = [vs]
                for v in vs:
                    if v is not None:
                        result.append(
                            (
                                k.encode("utf-8") if isinstance(k, str) else k,
                                v.encode("utf-8") if isinstance(v, str) else v,
                            )
                        )
            return urlencode(result, doseq=True)
        else:
            return data

    @staticmethod
    def _encode_files(files, data):
        """Build the body for a multipart/form-data request.

        Will successfully encode files when passed as a dict or a list of
        tuples. Order is retained if data is a list of tuples but arbitrary
        if parameters are supplied as a dict.
        The tuples may be 2-tuples (filename, fileobj), 3-tuples (filename, fileobj, contentype)
        or 4-tuples (filename, fileobj, contentype, custom_headers).
        """
        if not files:
            raise ValueError("Files must be provided.")
        elif isinstance(data, basestring):
            raise ValueError("Data must not be a string.")

        new_fields = []
        fields = to_key_val_list(data or {})
        files = to_key_val_list(files or {})

        for field, val in fields:
            if isinstance(val, basestring) or not hasattr(val, "__iter__"):
                val = [val]
            for v in val:
                if v is not None:
                    # Don't call str() on bytestrings: in Py3 it all goes wrong.
                    if not isinstance(v, bytes):
                        v = str(v)

                    new_fields.append(
                        (
                            field.decode("utf-8")
                            if isinstance(field, bytes)
                            else field,
                            v.encode("utf-8") if isinstance(v, str) else v,
                        )
                    )

        for k, v in files:
            # support for explicit filename
            ft = None
            fh = None
            if isinstance(v, (tuple, list)):
                if len(v) == 2:
                    fn, fp = v
                elif len(v) == 3:
                    fn, fp, ft = v
                else:
                    fn, fp, ft, fh = v
            else:
                fn = guess_filename(v) or k
                fp = v

            if isinstance(fp, (str, bytes, bytearray)):
                fdata = fp
            elif hasattr(fp, "read"):
                fdata = fp.read()
            elif fp is None:
                continue
            else:
                fdata = fp

            rf = RequestField(name=k, data=fdata, filename=fn, headers=fh)
            rf.make_multipart(content_type=ft)
            new_fields.append(rf)

        body, content_type = encode_multipart_formdata(new_fields)

        return body, content_type


class RequestHooksMixin:
    def register_hook(self, event, hook):
        """Properly register a hook."""

        if event not in self.hooks:
            raise ValueError(f'Unsupported event specified, with event name "{event}"')

        if isinstance(hook, Callable):
            self.hooks[event].append(hook)
        elif hasattr(hook, "__iter__"):
            self.hooks[event].extend(h for h in hook if isinstance(h, Callable))

    def deregister_hook(self, event, hook):
        """Deregister a previously registered hook.
        Returns True if the hook existed, False if not.
        """

        try:
            self.hooks[event].remove(hook)
            return True
        except ValueError:
            return False


class Request(RequestHooksMixin):
    """A user-created :class:`Request <Request>` object.

    Used to prepare a :class:`PreparedRequest <PreparedRequest>`, which is sent to the server.

    :param method: HTTP method to use.
    :param url: URL to send.
    :param headers: dictionary of headers to send.
    :param files: dictionary of {filename: fileobject} files to multipart upload.
    :param data: the body to attach to the request. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param json: json for the body to attach to the request (if files or data is not specified).
    :param params: URL parameters to append to the URL. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param auth: Auth handler or (user, pass) tuple.
    :param cookies: dictionary or CookieJar of cookies to attach to this request.
    :param hooks: dictionary of callback hooks, for internal usage.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> req.prepare()
      <PreparedRequest [GET]>
    """

    def __init__(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        # Default empty dicts for dict params.
        data = [] if data is None else data
        files = [] if files is None else files
        headers = {} if headers is None else headers
        params = {} if params is None else params
        hooks = {} if hooks is None else hooks

        self.hooks = default_hooks()
        for k, v in list(hooks.items()):
            self.register_hook(event=k, hook=v)

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.json = json
        self.params = params
        self.auth = auth
        self.cookies = cookies

    def __repr__(self):
        return f"<Request [{self.method}]>"

    def prepare(self):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it."""
        p = PreparedRequest()
        p.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
        )
        return p


class PreparedRequest(RequestEncodingMixin, RequestHooksMixin):
    """The fully mutable :class:`PreparedRequest <PreparedRequest>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import requests
      >>> req = requests.Request('GET', 'https://httpbin.org/get')
      >>> r = req.prepare()
      >>> r
      <PreparedRequest [GET]>

      >>> s = requests.Session()
      >>> s.send(r)
      <Response [200]>
    """

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        # The `CookieJar` used to create the Cookie header will be stored here
        # after prepare_cookies is called
        self._cookies = None
        #: request body to send to the server.
        self.body = None
        #: dictionary of callback hooks, for internal usage.
        self.hooks = default_hooks()
        #: integer denoting starting position of a readable file-like body.
        self._body_position = None

    def prepare(
        self,
        method=None,
        url=None,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
    ):
        """Prepares the entire request with the given parameters."""

        self.prepare_method(method)
        self.prepare_url(url, params)
        self.prepare_headers(headers)
        self.prepare_cookies(cookies)
        self.prepare_body(data, files, json)
        self.prepare_auth(auth, url)

        # Note that prepare_auth must be last to enable authentication schemes
        # such as OAuth to work on a fully prepared request.

        # This MUST go after prepare_auth. Authenticators could add a hook
        self.prepare_hooks(hooks)

    def __repr__(self):
        return f"<PreparedRequest [{self.method}]>"

    def copy(self):
        p = PreparedRequest()
        p.method = self.method
        p.url = self.url
        p.headers = self.headers.copy() if self.headers is not None else None
        p._cookies = _copy_cookie_jar(self._cookies)
        p.body = self.body
        p.hooks = self.hooks
        p._body_position = self._body_position
        return p

    def prepare_method(self, method):
        """Prepares the given HTTP method."""
        self.method = method
        if self.method is not None:
            self.method = to_native_string(self.method.upper())

    @staticmethod
    def _get_idna_encoded_host(host):
        from pip._vendor import idna

        try:
            host = idna.encode(host, uts46=True).decode("utf-8")
        except idna.IDNAError:
            raise UnicodeError
        return host

    def prepare_url(self, url, params):
        """Prepares the given HTTP URL."""
        #: Accept objects that have string representations.
        #: We're unable to blindly call unicode/str functions
        #: as this will include the bytestring indicator (b'')
        #: on python 3.x.
        #: https://github.com/psf/requests/pull/2238
        if isinstance(url, bytes):
            url = url.decode("utf8")
        else:
            url = str(url)

        # Remove leading whitespaces from url
        url = url.lstrip()

        # Don't do any URL preparation for non-HTTP schemes like `mailto`,
        # `data` etc to work around exceptions from `url_parse`, which
        # handles RFC 3986 only.
        if ":" in url and not url.lower().startswith("http"):
            self.url = url
            return

        # Support for unicode domain names and paths.
        try:
            scheme, auth, host, port, path, query, fragment = parse_url(url)
        except LocationParseError as e:
            raise InvalidURL(*e.args)

        if not scheme:
            raise MissingSchema(
                f"Invalid URL {url!r}: No scheme supplied. "
                f"Perhaps you meant https://{url}?"
            )

        if not host:
            raise InvalidURL(f"Invalid URL {url!r}: No host supplied")

        # In general, we want to try IDNA encoding the hostname if the string contains
        # non-ASCII characters. This allows users to automatically get the correct IDNA
        # behaviour. For strings containing only ASCII characters, we need to also verify
        # it doesn't start with a wildcard (*), before allowing the unencoded hostname.
        if not unicode_is_ascii(host):
            try:
                host = self._get_idna_encoded_host(host)
            except UnicodeError:
                raise InvalidURL("URL has an invalid label.")
        elif host.startswith(("*", ".")):
            raise InvalidURL("URL has an invalid label.")

        # Carefully reconstruct the network location
        netloc = auth or ""
        if netloc:
            netloc += "@"
        netloc += host
        if port:
            netloc += f":{port}"

        # Bare domains aren't valid URLs.
        if not path:
            path = "/"

        if isinstance(params, (str, bytes)):
            params = to_native_string(params)

        enc_params = self._encode_params(params)
        if enc_params:
            if query:
                query = f"{query}&{enc_params}"
            else:
                query = enc_params

        url = requote_uri(urlunparse([scheme, netloc, path, None, query, fragment]))
        self.url = url

    def prepare_headers(self, headers):
        """Prepares the given HTTP headers."""

        self.headers = CaseInsensitiveDict()
        if headers:
            for header in headers.items():
                # Raise exception on invalid header value.
                check_header_validity(header)
                name, value = header
                self.headers[to_native_string(name)] = value

    def prepare_body(self, data, files, json=None):
        """Prepares the given HTTP body data."""

        # Check if file, fo, generator, iterator.
        # If not, run through normal process.

        # Nottin' on you.
        body = None
        content_type = None

        if not data and json is not None:
            # urllib3 requires a bytes-like body. Python 2's json.dumps
            # provides this natively, but Python 3 gives a Unicode string.
            content_type = "application/json"

            try:
                body = complexjson.dumps(json, allow_nan=False)
            except ValueError as ve:
                raise InvalidJSONError(ve, request=self)

            if not isinstance(body, bytes):
                body = body.encode("utf-8")

        is_stream = all(
            [
                hasattr(data, "__iter__"),
                not isinstance(data, (basestring, list, tuple, Mapping)),
            ]
        )

        if is_stream:
            try:
                length = super_len(data)
            except (TypeError, AttributeError, UnsupportedOperation):
                length = None

            body = data

            if getattr(body, "tell", None) is not None:
                # Record the current file position before reading.
                # This will allow us to rewind a file in the event
                # of a redirect.
                try:
                    self._body_position = body.tell()
                except OSError:
                    # This differentiates from None, allowing us to catch
                    # a failed `tell()` later when trying to rewind the body
                    self._body_position = object()

            if files:
                raise NotImplementedError(
                    "Streamed bodies and files are mutually exclusive."
                )

            if length:
                self.headers["Content-Length"] = builtin_str(length)
            else:
                self.headers["Transfer-Encoding"] = "chunked"
        else:
            # Multi-part file uploads.
            if files:
                (body, content_type) = self._encode_files(files, data)
            else:
                if data:
                    body = self._encode_params(data)
                    if isinstance(data, basestring) or hasattr(data, "read"):
                        content_type = None
                    else:
                        content_type = "application/x-www-form-urlencoded"

            self.prepare_content_length(body)

            # Add content-type if it wasn't explicitly provided.
            if content_type and ("content-type" not in self.headers):
                self.headers["Content-Type"] = content_type

        self.body = body

    def prepare_content_length(self, body):
        """Prepare Content-Length header based on request method and body"""
        if body is not None:
            length = super_len(body)
            if length:
                # If length exists, set it. Otherwise, we fallback
                # to Transfer-Encoding: chunked.
                self.headers["Content-Length"] = builtin_str(length)
        elif (
            self.method not in ("GET", "HEAD")
            and self.headers.get("Content-Length") is None
        ):
            # Set Content-Length to 0 for methods that can have a body
            # but don't provide one. (i.e. not GET or HEAD)
            self.headers["Content-Length"] = "0"

    def prepare_auth(self, auth, url=""):
        """Prepares the given HTTP auth data."""

        # If no Auth is explicitly provided, extract it from the URL first.
        if auth is None:
            url_auth = get_auth_from_url(self.url)
            auth = url_auth if any(url_auth) else None

        if auth:
            if isinstance(auth, tuple) and len(auth) == 2:
                # special-case basic HTTP auth
                auth = HTTPBasicAuth(*auth)

            # Allow auth to make its changes.
            r = auth(self)

            # Update self to reflect the auth changes.
            self.__dict__.update(r.__dict__)

            # Recompute Content-Length
            self.prepare_content_length(self.body)

    def prepare_cookies(self, cookies):
        """Prepares the given HTTP cookie data.

        This function eventually generates a ``Cookie`` header from the
        given cookies using cookielib. Due to cookielib's design, the header
        will not be regenerated if it already exists, meaning this function
        can only be called once for the life of the
        :class:`PreparedRequest <PreparedRequest>` object. Any subsequent calls
        to ``prepare_cookies`` will have no actual effect, unless the "Cookie"
        header is removed beforehand.
        """
        if isinstance(cookies, cookielib.CookieJar):
            self._cookies = cookies
        else:
            self._cookies = cookiejar_from_dict(cookies)

        cookie_header = get_cookie_header(self._cookies, self)
        if cookie_header is not None:
            self.headers["Cookie"] = cookie_header

    def prepare_hooks(self, hooks):
        """Prepares the given hooks."""
        # hooks can be passed as None to the prepare method and to this
        # method. To prevent iterating over None, simply use an empty list
        # if hooks is False-y
        hooks = hooks or []
        for event in hooks:
            self.register_hook(event, hooks[event])


class Response:
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    __attrs__ = [
        "_content",
        "status_code",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
    ]

    def __init__(self):
        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-encoding']`` will return the
        #: value of a ``'Content-Encoding'`` response header.
        self.headers = CaseInsensitiveDict()

        #: File-like object representation of response (for advanced usage).
        #: Use of ``raw`` requires that ``stream=True`` be set on the request.
        #: This requirement does not apply for use internally to Requests.
        self.raw = None

        #: Final URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing r.text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request. Any redirect responses will end
        #: up here. The list is sorted from the oldest to the most recent request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A CookieJar of Cookies the server sent back.
        self.cookies = cookiejar_from_dict({})

        #: The amount of time elapsed between sending the request
        #: and the arrival of the response (as a timedelta).
        #: This property specifically measures the time taken between sending
        #: the first byte of the request and finishing parsing the headers. It
        #: is therefore unaffected by consuming the response content or the
        #: value of the ``stream`` keyword argument.
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        # Consume everything; accessing the content attribute makes
        # sure the content has been fully read.
        if not self._content_consumed:
            self.content

        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        for name, value in state.items():
            setattr(self, name, value)

        # pickled objects do not have .raw
        setattr(self, "_content_consumed", True)
        setattr(self, "raw", None)

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    def __bool__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __nonzero__(self):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __iter__(self):
        """Allows you to use a response as an iterator."""
        return self.iter_content(128)

    @property
    def ok(self):
        """Returns True if :attr:`status_code` is less than 400, False if not.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            self.raise_for_status()
        except HTTPError:
            return False
        return True

    @property
    def is_redirect(self):
        """True if this Response is a well-formed HTTP redirect that could have
        been processed automatically (by :meth:`Session.resolve_redirects`).
        """
        return "location" in self.headers and self.status_code in REDIRECT_STATI

    @property
    def is_permanent_redirect(self):
        """True if this Response one of the permanent versions of redirect."""
        return "location" in self.headers and self.status_code in (
            codes.moved_permanently,
            codes.permanent_redirect,
        )

    @property
    def next(self):
        """Returns a PreparedRequest for the next request in a redirect chain, if there is one."""
        return self._next

    @property
    def apparent_encoding(self):
        """The apparent encoding, provided by the charset_normalizer or chardet libraries."""
        if chardet is not None:
            return chardet.detect(self.content)["encoding"]
        else:
            # If no character detection library is available, we'll fall back
            # to a standard Python utf-8 str.
            return "utf-8"

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """Iterates over the response data.  When stream=True is set on the
        request, this avoids reading the content at once into memory for
        large responses.  The chunk size is the number of bytes it should
        read into memory.  This is not necessarily the length of each item
        returned as decoding can take place.

        chunk_size must be of type int or None. A value of None will
        function differently depending on the value of `stream`.
        stream=True will read data as it arrives in whatever size the
        chunks are received. If stream=False, data is returned as
        a single chunk.

        If decode_unicode is True, content will be decoded using the best
        available encoding based on the response.
        """

        def generate():
            # Special case for urllib3.
            if hasattr(self.raw, "stream"):
                try:
                    yield from self.raw.stream(chunk_size, decode_content=True)
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(
                f"chunk_size must be an int, it is instead a {type(chunk_size)}."
            )
        # simulate reading small chunks of the content
        reused_chunks = iter_slices(self._content, chunk_size)

        stream_chunks = generate()

        chunks = reused_chunks if self._content_consumed else stream_chunks

        if decode_unicode:
            chunks = stream_decode_response_unicode(chunks, self)

        return chunks

    def iter_lines(
        self, chunk_size=ITER_CHUNK_SIZE, decode_unicode=False, delimiter=None
    ):
        """Iterates over the response data, one line at a time.  When
        stream=True is set on the request, this avoids reading the
        content at once into memory for large responses.

        .. note:: This method is not reentrant safe.
        """

        pending = None

        for chunk in self.iter_content(
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            yield from lines

        if pending is not None:
            yield pending

    @property
    def content(self):
        """Content of the response, in bytes."""

        if self._content is False:
            # Read the contents.
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0 or self.raw is None:
                self._content = None
            else:
                self._content = b"".join(self.iter_content(CONTENT_CHUNK_SIZE)) or b""

        self._content_consumed = True
        # don't need to release the connection; that's been handled by urllib3
        # since we exhausted the data.
        return self._content

    @property
    def text(self):
        """Content of the response, in unicode.

        If Response.encoding is None, encoding will be guessed using
        ``charset_normalizer`` or ``chardet``.

        The encoding of the response content is determined based solely on HTTP
        headers, following RFC 2616 to the letter. If you can take advantage of
        non-HTTP knowledge to make a better guess at the encoding, you should
        set ``r.encoding`` appropriately before accessing this property.
        """

        # Try charset from content-type
        content = None
        encoding = self.encoding

        if not self.content:
            return ""

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding = self.apparent_encoding

        # Decode unicode from given encoding.
        try:
            content = str(self.content, encoding, errors="replace")
        except (LookupError, TypeError):
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            #
            # A TypeError can be raised if encoding is None
            #
            # So we try blindly encoding.
            content = str(self.content, errors="replace")

        return content

    def json(self, **kwargs):
        r"""Returns the json-encoded content of a response, if any.

        :param \*\*kwargs: Optional arguments that ``json.loads`` takes.
        :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json.
        """

        if not self.encoding and self.content and len(self.content) > 3:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding = guess_json_utf(self.content)
            if encoding is not None:
                try:
                    return complexjson.loads(self.content.decode(encoding), **kwargs)
                except UnicodeDecodeError:
                    # Wrong UTF codec detected; usually because it's not UTF-8
                    # but some other 8-bit codec.  This is an RFC violation,
                    # and the server didn't bother to tell us what codec *was*
                    # used.
                    pass
                except JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

        try:
            return complexjson.loads(self.text, **kwargs)
        except JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    @property
    def links(self):
        """Returns the parsed header links of the response, if any."""

        header = self.headers.get("link")

        resolved_links = {}

        if header:
            links = parse_header_links(header)

            for link in links:
                key = link.get("rel") or link.get("url")
                resolved_links[key] = link

        return resolved_links

    def raise_for_status(self):
        """Raises :class:`HTTPError`, if one occurred."""

        http_error_msg = ""
        if isinstance(self.reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings. (See PR #3538)
            try:
                reason = self.reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = self.reason.decode("iso-8859-1")
        else:
            reason = self.reason

        if 400 <= self.status_code < 500:
            http_error_msg = (
                f"{self.status_code} Client Error: {reason} for url: {self.url}"
            )

        elif 500 <= self.status_code < 600:
            http_error_msg = (
                f"{self.status_code} Server Error: {reason} for url: {self.url}"
            )

        if http_error_msg:
            raise HTTPError(http_error_msg, response=self)

    def close(self):
        """Releases the connection back to the pool. Once this method has been
        called the underlying ``raw`` object must not be accessed again.

        *Note: Should not normally need to be called explicitly.*
        """
        if not self._content_consumed:
            self.raw.close()

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()

# === NexusCore/openenv\Lib\site-packages\interpreter\core\async_core.py ===
import asyncio
import json
import os
import shutil
import socket
import threading
import time
import traceback
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import shortuuid
from pydantic import BaseModel
from starlette.websockets import WebSocketState

from .core import OpenInterpreter

last_start_time = 0

try:
    import janus
    import uvicorn
    from fastapi import (
        APIRouter,
        FastAPI,
        File,
        Form,
        HTTPException,
        Request,
        UploadFile,
        WebSocket,
    )
    from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
    from starlette.status import HTTP_403_FORBIDDEN
except:
    # Server dependencies are not required by the main package.
    pass


complete_message = {"role": "server", "type": "status", "content": "complete"}


class AsyncInterpreter(OpenInterpreter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.respond_thread = None
        self.stop_event = threading.Event()
        self.output_queue = None
        self.unsent_messages = deque()
        self.id = os.getenv("INTERPRETER_ID", datetime.now().timestamp())
        self.print = False  # Will print output

        self.require_acknowledge = (
            os.getenv("INTERPRETER_REQUIRE_ACKNOWLEDGE", "False").lower() == "true"
        )
        self.acknowledged_outputs = []

        self.server = Server(self)

        # For the 01. This lets the OAI compatible server accumulate context before responding.
        self.context_mode = False

    async def input(self, chunk):
        """
        Accumulates LMC chunks onto interpreter.messages.
        When it hits an "end" flag, calls interpreter.respond().
        """

        if "start" in chunk:
            # If the user is starting something, the interpreter should stop.
            if self.respond_thread is not None and self.respond_thread.is_alive():
                self.stop_event.set()
                self.respond_thread.join()
            self.accumulate(chunk)
        elif "content" in chunk:
            self.accumulate(chunk)
        elif "end" in chunk:
            # If the user is done talking, the interpreter should respond.

            run_code = None  # Will later default to auto_run unless the user makes a command here

            # But first, process any commands.
            if self.messages[-1].get("type") == "command":
                command = self.messages[-1]["content"]
                self.messages = self.messages[:-1]

                if command == "stop":
                    # Any start flag would have stopped it a moment ago, but to be sure:
                    self.stop_event.set()
                    self.respond_thread.join()
                    return
                if command == "go":
                    # This is to approve code.
                    run_code = True
                    pass

            self.stop_event.clear()
            self.respond_thread = threading.Thread(
                target=self.respond, args=(run_code,)
            )
            self.respond_thread.start()

    async def output(self):
        if self.output_queue == None:
            self.output_queue = janus.Queue()
        return await self.output_queue.async_q.get()

    def respond(self, run_code=None):
        for attempt in range(5):  # 5 attempts
            try:
                if run_code == None:
                    run_code = self.auto_run

                sent_chunks = False

                for chunk_og in self._respond_and_store():
                    chunk = (
                        chunk_og.copy()
                    )  # This fixes weird double token chunks. Probably a deeper problem?

                    if chunk["type"] == "confirmation":
                        if run_code:
                            run_code = False
                            continue
                        else:
                            break

                    if self.stop_event.is_set():
                        return

                    if self.print:
                        if "start" in chunk:
                            print("\n")
                        if chunk["type"] in ["code", "console"] and "format" in chunk:
                            if "start" in chunk:
                                print(
                                    "\n------------\n\n```" + chunk["format"],
                                    flush=True,
                                )
                            if "end" in chunk:
                                print("\n```\n\n------------\n\n", flush=True)
                        if chunk.get("format") != "active_line":
                            if "format" in chunk and "base64" in chunk["format"]:
                                print("\n[An image was produced]")
                            else:
                                content = chunk.get("content", "")
                                content = (
                                    str(content)
                                    .encode("ascii", "ignore")
                                    .decode("ascii")
                                )
                                print(content, end="", flush=True)

                    if self.debug:
                        print("Interpreter produced this chunk:", chunk)

                    self.output_queue.sync_q.put(chunk)
                    sent_chunks = True

                if not sent_chunks:
                    print("ERROR. NO CHUNKS SENT. TRYING AGAIN.")
                    print("Messages:", self.messages)
                    messages = [
                        "Hello? Answer please.",
                        "Just say something, anything.",
                        "Are you there?",
                        "Can you respond?",
                        "Please reply.",
                    ]
                    self.messages.append(
                        {
                            "role": "user",
                            "type": "message",
                            "content": messages[attempt % len(messages)],
                        }
                    )
                    time.sleep(1)
                else:
                    self.output_queue.sync_q.put(complete_message)
                    if self.debug:
                        print("\nServer response complete.\n")
                    return

            except Exception as e:
                error = traceback.format_exc() + "\n" + str(e)
                error_message = {
                    "role": "server",
                    "type": "error",
                    "content": traceback.format_exc() + "\n" + str(e),
                }
                self.output_queue.sync_q.put(error_message)
                self.output_queue.sync_q.put(complete_message)
                print("\n\n--- SENT ERROR: ---\n\n")
                print(error)
                print("\n\n--- (ERROR ABOVE WAS SENT) ---\n\n")
                return

        error_message = {
            "role": "server",
            "type": "error",
            "content": "No chunks sent or unknown error.",
        }
        self.output_queue.sync_q.put(error_message)
        self.output_queue.sync_q.put(complete_message)
        raise Exception("No chunks sent or unknown error.")

    def accumulate(self, chunk):
        """
        Accumulates LMC chunks onto interpreter.messages.
        """
        if type(chunk) == str:
            chunk = json.loads(chunk)

        if type(chunk) == dict:
            if chunk.get("format") == "active_line":
                # We don't do anything with these.
                pass

            elif "content" in chunk and not (
                len(self.messages) > 0
                and (
                    (
                        "type" in self.messages[-1]
                        and chunk.get("type") != self.messages[-1].get("type")
                    )
                    or (
                        "format" in self.messages[-1]
                        and chunk.get("format") != self.messages[-1].get("format")
                    )
                )
            ):
                if len(self.messages) == 0:
                    raise Exception(
                        "You must send a 'start: True' chunk first to create this message."
                    )
                # Append to an existing message
                if (
                    "type" not in self.messages[-1]
                ):  # It was created with a type-less start message
                    self.messages[-1]["type"] = chunk["type"]
                if (
                    chunk.get("format") and "format" not in self.messages[-1]
                ):  # It was created with a type-less start message
                    self.messages[-1]["format"] = chunk["format"]
                if "content" not in self.messages[-1]:
                    self.messages[-1]["content"] = chunk["content"]
                else:
                    self.messages[-1]["content"] += chunk["content"]

            # elif "content" in chunk and (len(self.messages) > 0 and self.messages[-1] == {'role': 'user', 'start': True}):
            #     # Last message was {'role': 'user', 'start': True}. Just populate that with this chunk
            #     self.messages[-1] = chunk.copy()

            elif "start" in chunk or (
                len(self.messages) > 0
                and (
                    chunk.get("type") != self.messages[-1].get("type")
                    or chunk.get("format") != self.messages[-1].get("format")
                )
            ):
                # Create a new message
                chunk_copy = (
                    chunk.copy()
                )  # So we don't modify the original chunk, which feels wrong.
                if "start" in chunk_copy:
                    chunk_copy.pop("start")
                if "content" not in chunk_copy:
                    chunk_copy["content"] = ""
                self.messages.append(chunk_copy)

        elif type(chunk) == bytes:
            if self.messages[-1]["content"] == "":  # We initialize as an empty string ^
                self.messages[-1]["content"] = b""  # But it actually should be bytes
            self.messages[-1]["content"] += chunk


def authenticate_function(key):
    """
    This function checks if the provided key is valid for authentication.

    Returns True if the key is valid, False otherwise.
    """
    # Fetch the API key from the environment variables. If it's not set, return True.
    api_key = os.getenv("INTERPRETER_API_KEY", None)

    # If the API key is not set in the environment variables, return True.
    # Otherwise, check if the provided key matches the fetched API key.
    # Return True if they match, False otherwise.
    if api_key is None:
        return True
    else:
        return key == api_key


def create_router(async_interpreter):
    router = APIRouter()

    @router.get("/heartbeat")
    async def heartbeat():
        return {"status": "alive"}

    @router.get("/")
    async def home():
        return PlainTextResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Chat</title>
            </head>
            <body>
                <form action="" onsubmit="sendMessage(event)">
                    <textarea id="messageInput" rows="10" cols="50" autocomplete="off"></textarea>
                    <button>Send</button>
                </form>
                <button id="approveCodeButton">Approve Code</button>
                <button id="authButton">Send Auth</button>
                <div id="messages"></div>
                <script>
                    var ws = new WebSocket("ws://"""
            + async_interpreter.server.host
            + ":"
            + str(async_interpreter.server.port)
            + """/");
                    var lastMessageElement = null;

                    ws.onmessage = function(event) {

                        var eventData = JSON.parse(event.data);

                        """
            + (
                """
                        
                        // Acknowledge receipt
                        var acknowledge_message = {
                            "ack": eventData.id
                        };
                        ws.send(JSON.stringify(acknowledge_message));

                        """
                if async_interpreter.require_acknowledge
                else ""
            )
            + """

                        if (lastMessageElement == null) {
                            lastMessageElement = document.createElement('p');
                            document.getElementById('messages').appendChild(lastMessageElement);
                            lastMessageElement.innerHTML = "<br>"
                        }

                        if ((eventData.role == "assistant" && eventData.type == "message" && eventData.content) ||
                            (eventData.role == "computer" && eventData.type == "console" && eventData.format == "output" && eventData.content) ||
                            (eventData.role == "assistant" && eventData.type == "code" && eventData.content)) {
                            lastMessageElement.innerHTML += eventData.content;
                        } else {
                            lastMessageElement.innerHTML += "<br><br>" + JSON.stringify(eventData) + "<br><br>";
                        }
                    };
                    function sendMessage(event) {
                        event.preventDefault();
                        var input = document.getElementById("messageInput");
                        var message = input.value;
                        if (message.startsWith('{') && message.endsWith('}')) {
                            message = JSON.stringify(JSON.parse(message));
                            ws.send(message);
                        } else {
                            var startMessageBlock = {
                                "role": "user",
                                //"type": "message",
                                "start": true
                            };
                            ws.send(JSON.stringify(startMessageBlock));

                            var messageBlock = {
                                "role": "user",
                                "type": "message",
                                "content": message
                            };
                            ws.send(JSON.stringify(messageBlock));

                            var endMessageBlock = {
                                "role": "user",
                                //"type": "message",
                                "end": true
                            };
                            ws.send(JSON.stringify(endMessageBlock));
                        }
                        var userMessageElement = document.createElement('p');
                        userMessageElement.innerHTML = '<b>' + input.value + '</b><br>';
                        document.getElementById('messages').appendChild(userMessageElement);
                        lastMessageElement = document.createElement('p');
                        document.getElementById('messages').appendChild(lastMessageElement);
                        input.value = '';
                    }
                function approveCode() {
                    var startCommandBlock = {
                        "role": "user",
                        "type": "command",
                        "start": true
                    };
                    ws.send(JSON.stringify(startCommandBlock));

                    var commandBlock = {
                        "role": "user",
                        "type": "command",
                        "content": "go"
                    };
                    ws.send(JSON.stringify(commandBlock));

                    var endCommandBlock = {
                        "role": "user",
                        "type": "command",
                        "end": true
                    };
                    ws.send(JSON.stringify(endCommandBlock));
                }
                function authenticate() {
                    var authBlock = {
                        "auth": "dummy-api-key"
                    };
                    ws.send(JSON.stringify(authBlock));
                }

                document.getElementById("approveCodeButton").addEventListener("click", approveCode);
                document.getElementById("authButton").addEventListener("click", authenticate);
                </script>
            </body>
            </html>
            """,
            media_type="text/html",
        )

    @router.websocket("/")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        try:  # solving it ;)/ # killian super wrote this

            async def receive_input():
                authenticated = False
                while True:
                    try:
                        if websocket.client_state != WebSocketState.CONNECTED:
                            return
                        data = await websocket.receive()

                        if (
                            not authenticated
                            and os.getenv("INTERPRETER_REQUIRE_AUTH") != "False"
                        ):
                            if "text" in data:
                                data = json.loads(data["text"])
                                if "auth" in data:
                                    if async_interpreter.server.authenticate(
                                        data["auth"]
                                    ):
                                        authenticated = True
                                        await websocket.send_text(
                                            json.dumps({"auth": True})
                                        )
                            if not authenticated:
                                await websocket.send_text(json.dumps({"auth": False}))
                            continue

                        if data.get("type") == "websocket.receive":
                            if "text" in data:
                                data = json.loads(data["text"])
                                if (
                                    async_interpreter.require_acknowledge
                                    and "ack" in data
                                ):
                                    async_interpreter.acknowledged_outputs.append(
                                        data["ack"]
                                    )
                                    continue
                            elif "bytes" in data:
                                data = data["bytes"]
                            await async_interpreter.input(data)
                        elif data.get("type") == "websocket.disconnect":
                            print("Client wants to disconnect, that's fine..")
                            return
                        else:
                            print("Invalid data:", data)
                            continue

                    except Exception as e:
                        error = traceback.format_exc() + "\n" + str(e)
                        error_message = {
                            "role": "server",
                            "type": "error",
                            "content": traceback.format_exc() + "\n" + str(e),
                        }
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_text(json.dumps(error_message))
                            await websocket.send_text(json.dumps(complete_message))
                            print("\n\n--- SENT ERROR: ---\n\n")
                        else:
                            print(
                                "\n\n--- ERROR (not sent due to disconnected state): ---\n\n"
                            )
                        print(error)
                        print("\n\n--- (ERROR ABOVE) ---\n\n")

            async def send_output():
                while True:
                    if websocket.client_state != WebSocketState.CONNECTED:
                        return
                    try:
                        # First, try to send any unsent messages
                        while async_interpreter.unsent_messages:
                            output = async_interpreter.unsent_messages[0]
                            if async_interpreter.debug:
                                print("This was unsent, sending it again:", output)

                            success = await send_message(output)
                            if success:
                                async_interpreter.unsent_messages.popleft()

                        # If we've sent all unsent messages, get a new output
                        if not async_interpreter.unsent_messages:
                            output = await async_interpreter.output()
                            success = await send_message(output)
                            if not success:
                                async_interpreter.unsent_messages.append(output)
                                if async_interpreter.debug:
                                    print(
                                        f"Added message to unsent_messages queue after failed attempts: {output}"
                                    )

                    except Exception as e:
                        error = traceback.format_exc() + "\n" + str(e)
                        error_message = {
                            "role": "server",
                            "type": "error",
                            "content": error,
                        }
                        async_interpreter.unsent_messages.append(error_message)
                        async_interpreter.unsent_messages.append(complete_message)
                        print("\n\n--- ERROR (will be sent when possible): ---\n\n")
                        print(error)
                        print(
                            "\n\n--- (ERROR ABOVE WILL BE SENT WHEN POSSIBLE) ---\n\n"
                        )

            async def send_message(output):
                if isinstance(output, dict) and "id" in output:
                    id = output["id"]
                else:
                    id = shortuuid.uuid()
                    if (
                        isinstance(output, dict)
                        and async_interpreter.require_acknowledge
                    ):
                        output["id"] = id

                for attempt in range(20):
                    # time.sleep(0.5)

                    if websocket.client_state != WebSocketState.CONNECTED:
                        return False

                    try:
                        # print("sending:", output)

                        if isinstance(output, bytes):
                            await websocket.send_bytes(output)
                            return True  # Haven't set up ack for this
                        else:
                            if async_interpreter.require_acknowledge:
                                output["id"] = id
                            if async_interpreter.debug:
                                print("Sending this over the websocket:", output)
                            await websocket.send_text(json.dumps(output))

                        if async_interpreter.require_acknowledge:
                            acknowledged = False
                            for _ in range(100):
                                if id in async_interpreter.acknowledged_outputs:
                                    async_interpreter.acknowledged_outputs.remove(id)
                                    acknowledged = True
                                    if async_interpreter.debug:
                                        print("This output was acknowledged:", output)
                                    break
                                await asyncio.sleep(0.0001)

                            if acknowledged:
                                return True
                            else:
                                if async_interpreter.debug:
                                    print("Acknowledgement not received for:", output)
                                return False
                        else:
                            return True

                    except Exception as e:
                        print(
                            f"Failed to send output on attempt number: {attempt + 1}. Output was: {output}"
                        )
                        print(f"Error: {str(e)}")
                        traceback.print_exc()
                        await asyncio.sleep(0.01)

                # If we've reached this point, we've failed to send after 100 attempts
                if output not in async_interpreter.unsent_messages:
                    print("Failed to send message:", output)
                else:
                    print(
                        "Failed to send message, also it was already in unsent queue???:",
                        output,
                    )

                return False

            await asyncio.gather(receive_input(), send_output())

        except Exception as e:
            error = traceback.format_exc() + "\n" + str(e)
            error_message = {
                "role": "server",
                "type": "error",
                "content": error,
            }
            async_interpreter.unsent_messages.append(error_message)
            async_interpreter.unsent_messages.append(complete_message)
            print("\n\n--- ERROR (will be sent when possible): ---\n\n")
            print(error)
            print("\n\n--- (ERROR ABOVE WILL BE SENT WHEN POSSIBLE) ---\n\n")

    # TODO
    @router.post("/")
    async def post_input(payload: Dict[str, Any]):
        try:
            async_interpreter.input(payload)
            return {"status": "success"}
        except Exception as e:
            return {"error": str(e)}, 500

    @router.post("/settings")
    async def set_settings(payload: Dict[str, Any]):
        for key, value in payload.items():
            print("Updating settings...")
            # print(f"Updating settings: {key} = {value}")
            if key in ["llm", "computer"] and isinstance(value, dict):
                if key == "auto_run":
                    return {
                        "error": f"The setting {key} is not modifiable through the server due to security constraints."
                    }, 403
                if hasattr(async_interpreter, key):
                    for sub_key, sub_value in value.items():
                        if hasattr(getattr(async_interpreter, key), sub_key):
                            setattr(getattr(async_interpreter, key), sub_key, sub_value)
                        else:
                            return {
                                "error": f"Sub-setting {sub_key} not found in {key}"
                            }, 404
                else:
                    return {"error": f"Setting {key} not found"}, 404
            elif hasattr(async_interpreter, key):
                setattr(async_interpreter, key, value)
            else:
                return {"error": f"Setting {key} not found"}, 404

        return {"status": "success"}

    @router.get("/settings/{setting}")
    async def get_setting(setting: str):
        if hasattr(async_interpreter, setting):
            setting_value = getattr(async_interpreter, setting)
            try:
                return json.dumps({setting: setting_value})
            except TypeError:
                return {"error": "Failed to serialize the setting value"}, 500
        else:
            return json.dumps({"error": "Setting not found"}), 404

    if os.getenv("INTERPRETER_INSECURE_ROUTES", "").lower() == "true":

        @router.post("/run")
        async def run_code(payload: Dict[str, Any]):
            language, code = payload.get("language"), payload.get("code")
            if not (language and code):
                return {"error": "Both 'language' and 'code' are required."}, 400
            try:
                print(f"Running {language}:", code)
                output = async_interpreter.computer.run(language, code)
                print("Output:", output)
                return {"output": output}
            except Exception as e:
                return {"error": str(e)}, 500

        @router.post("/upload")
        async def upload_file(file: UploadFile = File(...), path: str = Form(...)):
            try:
                with open(path, "wb") as output_file:
                    shutil.copyfileobj(file.file, output_file)
                return {"status": "success"}
            except Exception as e:
                return {"error": str(e)}, 500

        @router.get("/download/{filename}")
        async def download_file(filename: str):
            try:
                return StreamingResponse(
                    open(filename, "rb"), media_type="application/octet-stream"
                )
            except Exception as e:
                return {"error": str(e)}, 500

    ### OPENAI COMPATIBLE ENDPOINT

    class ChatMessage(BaseModel):
        role: str
        content: Union[str, List[Dict[str, Any]]]

    class ChatCompletionRequest(BaseModel):
        model: str = "default-model"
        messages: List[ChatMessage]
        max_tokens: Optional[int] = None
        temperature: Optional[float] = None
        stream: Optional[bool] = False

    async def openai_compatible_generator(run_code):
        if run_code:
            print("Running code.\n")
            for i, chunk in enumerate(async_interpreter._respond_and_store()):
                if "content" in chunk:
                    print(chunk["content"], end="")  # Sorry! Shitty display for now
                if "start" in chunk:
                    print("\n")

                output_content = None

                if chunk["type"] == "message" and "content" in chunk:
                    output_content = chunk["content"]
                if chunk["type"] == "code" and "start" in chunk:
                    output_content = "```" + chunk["format"] + "\n"
                if chunk["type"] == "code" and "content" in chunk:
                    output_content = chunk["content"]
                if chunk["type"] == "code" and "end" in chunk:
                    output_content = "\n```\n"

                if output_content:
                    await asyncio.sleep(0)
                    output_chunk = {
                        "id": i,
                        "object": "chat.completion.chunk",
                        "created": time.time(),
                        "model": "open-interpreter",
                        "choices": [{"delta": {"content": output_content}}],
                    }
                    yield f"data: {json.dumps(output_chunk)}\n\n"

            return

        made_chunk = False

        for message in [
            ".",
            "Just say something, anything.",
            "Hello? Answer please.",
            "Are you there?",
            "Can you respond?",
            "Please reply.",
        ]:
            for i, chunk in enumerate(
                async_interpreter.chat(message=message, stream=True, display=True)
            ):
                await asyncio.sleep(0)  # Yield control to the event loop
                made_chunk = True

                if (
                    chunk["type"] == "confirmation"
                    and async_interpreter.auto_run == False
                ):
                    await asyncio.sleep(0)
                    output_content = "Do you want to run this code?"
                    output_chunk = {
                        "id": i,
                        "object": "chat.completion.chunk",
                        "created": time.time(),
                        "model": "open-interpreter",
                        "choices": [{"delta": {"content": output_content}}],
                    }
                    yield f"data: {json.dumps(output_chunk)}\n\n"
                    break

                if async_interpreter.stop_event.is_set():
                    break

                output_content = None

                if chunk["type"] == "message" and "content" in chunk:
                    output_content = chunk["content"]
                if chunk["type"] == "code" and "start" in chunk:
                    output_content = "```" + chunk["format"] + "\n"
                if chunk["type"] == "code" and "content" in chunk:
                    output_content = chunk["content"]
                if chunk["type"] == "code" and "end" in chunk:
                    output_content = "\n```\n"

                if output_content:
                    await asyncio.sleep(0)
                    output_chunk = {
                        "id": i,
                        "object": "chat.completion.chunk",
                        "created": time.time(),
                        "model": "open-interpreter",
                        "choices": [{"delta": {"content": output_content}}],
                    }
                    yield f"data: {json.dumps(output_chunk)}\n\n"

            if made_chunk:
                break

    @router.post("/openai/chat/completions")
    async def chat_completion(request: ChatCompletionRequest):
        global last_start_time

        # Convert to LMC
        last_message = request.messages[-1]

        if last_message.role != "user":
            raise ValueError("Last message must be from the user.")

        if last_message.content == "{STOP}":
            # Handle special STOP token
            async_interpreter.stop_event.set()
            time.sleep(5)
            async_interpreter.stop_event.clear()
            return

        if last_message.content in ["{CONTEXT_MODE_ON}", "{REQUIRE_START_ON}"]:
            async_interpreter.context_mode = True
            return

        if last_message.content in ["{CONTEXT_MODE_OFF}", "{REQUIRE_START_OFF}"]:
            async_interpreter.context_mode = False
            return

        if last_message.content == "{AUTO_RUN_ON}":
            async_interpreter.auto_run = True
            return

        if last_message.content == "{AUTO_RUN_OFF}":
            async_interpreter.auto_run = False
            return

        run_code = False
        if (
            async_interpreter.messages
            and async_interpreter.messages[-1]["type"] == "code"
            and last_message.content.lower().strip(".!?").strip() == "yes"
        ):
            run_code = True
        elif type(last_message.content) == str:
            async_interpreter.messages.append(
                {
                    "role": "user",
                    "type": "message",
                    "content": last_message.content,
                }
            )
            print(">", last_message.content)
        elif type(last_message.content) == list:
            for content in last_message.content:
                if content["type"] == "text":
                    async_interpreter.messages.append(
                        {"role": "user", "type": "message", "content": str(content)}
                    )
                    print(">", content)
                elif content["type"] == "image_url":
                    if "url" not in content["image_url"]:
                        raise Exception("`url` must be in `image_url`.")
                    url = content["image_url"]["url"]
                    print("> [user sent an image]", url[:100])
                    if "base64," not in url:
                        raise Exception(
                            '''Image must be in the format: "data:image/jpeg;base64,{base64_image}"'''
                        )

                    # data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA6oA...

                    data = url.split("base64,")[1]
                    format = "base64." + url.split(";")[0].split("/")[1]
                    async_interpreter.messages.append(
                        {
                            "role": "user",
                            "type": "image",
                            "format": format,
                            "content": data,
                        }
                    )

        else:
            if async_interpreter.context_mode:
                # In context mode, we only respond if we recieved a {START} message
                # Otherwise, we're just accumulating context
                if last_message.content == "{START}":
                    if async_interpreter.messages[-1]["content"] == "{START}":
                        # Remove that {START} message that would have just been added
                        async_interpreter.messages = async_interpreter.messages[:-1]
                    last_start_time = time.time()
                    if (
                        async_interpreter.messages
                        and async_interpreter.messages[-1].get("role") != "user"
                    ):
                        return
                else:
                    # Check if we're within 6 seconds of last_start_time
                    current_time = time.time()
                    if current_time - last_start_time <= 6:
                        # Continue processing
                        pass
                    else:
                        # More than 6 seconds have passed, so return
                        return

            else:
                if last_message.content == "{START}":
                    # This just sometimes happens I guess
                    # Remove that {START} message that would have just been added
                    async_interpreter.messages = async_interpreter.messages[:-1]
                    return

        async_interpreter.stop_event.set()
        time.sleep(0.1)
        async_interpreter.stop_event.clear()

        if request.stream:
            return StreamingResponse(
                openai_compatible_generator(run_code), media_type="application/x-ndjson"
            )
        else:
            messages = async_interpreter.chat(message=".", stream=False, display=True)
            content = messages[-1]["content"]
            return {
                "id": "200",
                "object": "chat.completion",
                "created": time.time(),
                "model": request.model,
                "choices": [{"message": {"role": "assistant", "content": content}}],
            }

    return router


class Server:
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8000

    def __init__(self, async_interpreter, host=None, port=None):
        self.app = FastAPI()
        router = create_router(async_interpreter)
        self.authenticate = authenticate_function

        # Add authentication middleware
        @self.app.middleware("http")
        async def validate_api_key(request: Request, call_next):
            # Ignore authentication for the /heartbeat route
            if request.url.path == "/heartbeat":
                return await call_next(request)

            api_key = request.headers.get("X-API-KEY")
            if self.authenticate(api_key):
                response = await call_next(request)
                return response
            else:
                return JSONResponse(
                    status_code=HTTP_403_FORBIDDEN,
                    content={"detail": "Authentication failed"},
                )

        self.app.include_router(router)
        h = host or os.getenv("INTERPRETER_HOST", Server.DEFAULT_HOST)
        p = port or int(os.getenv("INTERPRETER_PORT", Server.DEFAULT_PORT))
        self.config = uvicorn.Config(app=self.app, host=h, port=p)
        self.uvicorn_server = uvicorn.Server(self.config)

    @property
    def host(self):
        return self.config.host

    @host.setter
    def host(self, value):
        self.config.host = value
        self.uvicorn_server = uvicorn.Server(self.config)

    @property
    def port(self):
        return self.config.port

    @port.setter
    def port(self, value):
        self.config.port = value
        self.uvicorn_server = uvicorn.Server(self.config)

    def run(self, host=None, port=None, retries=5):
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

        # Print server information
        if self.host == "0.0.0.0":
            print(
                "Warning: Using host `0.0.0.0` will expose Open Interpreter over your local network."
            )
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Google's public DNS server
            print(f"Server will run at http://{s.getsockname()[0]}:{self.port}")
            s.close()
        else:
            print(f"Server will run at http://{self.host}:{self.port}")

        self.uvicorn_server.run()

        # for _ in range(retries):
        #     try:
        #         self.uvicorn_server.run()
        #         break
        #     except KeyboardInterrupt:
        #         break
        #     except ImportError as e:
        #         if _ == 4:  # If this is the last attempt
        #             raise ImportError(
        #                 str(e)
        #                 + """\n\nPlease ensure you have run `pip install "open-interpreter[server]"` to install server dependencies."""
        #             )
        #     except:
        #         print("An unexpected error occurred:", traceback.format_exc())
        #         print("Server restarting.")