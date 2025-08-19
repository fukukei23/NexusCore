
# === NexusCore/openenv\Lib\site-packages\anyio\_backends\_trio.py ===
from __future__ import annotations

import array
import math
import os
import socket
import sys
import types
import weakref
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Iterable,
    Sequence,
)
from concurrent.futures import Future
from contextlib import AbstractContextManager
from dataclasses import dataclass
from functools import partial
from io import IOBase
from os import PathLike
from signal import Signals
from socket import AddressFamily, SocketKind
from types import TracebackType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Generic,
    NoReturn,
    TypeVar,
    cast,
    overload,
)

import trio.from_thread
import trio.lowlevel
from outcome import Error, Outcome, Value
from trio.lowlevel import (
    current_root_task,
    current_task,
    wait_readable,
    wait_writable,
)
from trio.socket import SocketType as TrioSocketType
from trio.to_thread import run_sync

from .. import (
    CapacityLimiterStatistics,
    EventStatistics,
    LockStatistics,
    TaskInfo,
    WouldBlock,
    abc,
)
from .._core._eventloop import claim_worker_thread
from .._core._exceptions import (
    BrokenResourceError,
    BusyResourceError,
    ClosedResourceError,
    EndOfStream,
)
from .._core._sockets import convert_ipv6_sockaddr
from .._core._streams import create_memory_object_stream
from .._core._synchronization import (
    CapacityLimiter as BaseCapacityLimiter,
)
from .._core._synchronization import Event as BaseEvent
from .._core._synchronization import Lock as BaseLock
from .._core._synchronization import (
    ResourceGuard,
    SemaphoreStatistics,
)
from .._core._synchronization import Semaphore as BaseSemaphore
from .._core._tasks import CancelScope as BaseCancelScope
from ..abc import IPSockAddrType, UDPPacketType, UNIXDatagramPacketType
from ..abc._eventloop import AsyncBackend, StrOrBytesPath
from ..streams.memory import MemoryObjectSendStream

if TYPE_CHECKING:
    from _typeshed import HasFileno

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from exceptiongroup import BaseExceptionGroup
    from typing_extensions import TypeVarTuple, Unpack

T = TypeVar("T")
T_Retval = TypeVar("T_Retval")
T_SockAddr = TypeVar("T_SockAddr", str, IPSockAddrType)
PosArgsT = TypeVarTuple("PosArgsT")
P = ParamSpec("P")


#
# Event loop
#

RunVar = trio.lowlevel.RunVar


#
# Timeouts and cancellation
#


class CancelScope(BaseCancelScope):
    def __new__(
        cls, original: trio.CancelScope | None = None, **kwargs: object
    ) -> CancelScope:
        return object.__new__(cls)

    def __init__(self, original: trio.CancelScope | None = None, **kwargs: Any) -> None:
        self.__original = original or trio.CancelScope(**kwargs)

    def __enter__(self) -> CancelScope:
        self.__original.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        return self.__original.__exit__(exc_type, exc_val, exc_tb)

    def cancel(self) -> None:
        self.__original.cancel()

    @property
    def deadline(self) -> float:
        return self.__original.deadline

    @deadline.setter
    def deadline(self, value: float) -> None:
        self.__original.deadline = value

    @property
    def cancel_called(self) -> bool:
        return self.__original.cancel_called

    @property
    def cancelled_caught(self) -> bool:
        return self.__original.cancelled_caught

    @property
    def shield(self) -> bool:
        return self.__original.shield

    @shield.setter
    def shield(self, value: bool) -> None:
        self.__original.shield = value


#
# Task groups
#


class TaskGroup(abc.TaskGroup):
    def __init__(self) -> None:
        self._active = False
        self._nursery_manager = trio.open_nursery(strict_exception_groups=True)
        self.cancel_scope = None  # type: ignore[assignment]

    async def __aenter__(self) -> TaskGroup:
        self._active = True
        self._nursery = await self._nursery_manager.__aenter__()
        self.cancel_scope = CancelScope(self._nursery.cancel_scope)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        try:
            # trio.Nursery.__exit__ returns bool; .open_nursery has wrong type
            return await self._nursery_manager.__aexit__(exc_type, exc_val, exc_tb)  # type: ignore[return-value]
        except BaseExceptionGroup as exc:
            if not exc.split(trio.Cancelled)[1]:
                raise trio.Cancelled._create() from exc

            raise
        finally:
            del exc_val, exc_tb
            self._active = False

    def start_soon(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[Any]],
        *args: Unpack[PosArgsT],
        name: object = None,
    ) -> None:
        if not self._active:
            raise RuntimeError(
                "This task group is not active; no new tasks can be started."
            )

        self._nursery.start_soon(func, *args, name=name)

    async def start(
        self, func: Callable[..., Awaitable[Any]], *args: object, name: object = None
    ) -> Any:
        if not self._active:
            raise RuntimeError(
                "This task group is not active; no new tasks can be started."
            )

        return await self._nursery.start(func, *args, name=name)


#
# Threads
#


class BlockingPortal(abc.BlockingPortal):
    def __new__(cls) -> BlockingPortal:
        return object.__new__(cls)

    def __init__(self) -> None:
        super().__init__()
        self._token = trio.lowlevel.current_trio_token()

    def _spawn_task_from_thread(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        name: object,
        future: Future[T_Retval],
    ) -> None:
        trio.from_thread.run_sync(
            partial(self._task_group.start_soon, name=name),
            self._call_func,
            func,
            args,
            kwargs,
            future,
            trio_token=self._token,
        )


#
# Subprocesses
#


@dataclass(eq=False)
class ReceiveStreamWrapper(abc.ByteReceiveStream):
    _stream: trio.abc.ReceiveStream

    async def receive(self, max_bytes: int | None = None) -> bytes:
        try:
            data = await self._stream.receive_some(max_bytes)
        except trio.ClosedResourceError as exc:
            raise ClosedResourceError from exc.__cause__
        except trio.BrokenResourceError as exc:
            raise BrokenResourceError from exc.__cause__

        if data:
            return data
        else:
            raise EndOfStream

    async def aclose(self) -> None:
        await self._stream.aclose()


@dataclass(eq=False)
class SendStreamWrapper(abc.ByteSendStream):
    _stream: trio.abc.SendStream

    async def send(self, item: bytes) -> None:
        try:
            await self._stream.send_all(item)
        except trio.ClosedResourceError as exc:
            raise ClosedResourceError from exc.__cause__
        except trio.BrokenResourceError as exc:
            raise BrokenResourceError from exc.__cause__

    async def aclose(self) -> None:
        await self._stream.aclose()


@dataclass(eq=False)
class Process(abc.Process):
    _process: trio.Process
    _stdin: abc.ByteSendStream | None
    _stdout: abc.ByteReceiveStream | None
    _stderr: abc.ByteReceiveStream | None

    async def aclose(self) -> None:
        with CancelScope(shield=True):
            if self._stdin:
                await self._stdin.aclose()
            if self._stdout:
                await self._stdout.aclose()
            if self._stderr:
                await self._stderr.aclose()

        try:
            await self.wait()
        except BaseException:
            self.kill()
            with CancelScope(shield=True):
                await self.wait()
            raise

    async def wait(self) -> int:
        return await self._process.wait()

    def terminate(self) -> None:
        self._process.terminate()

    def kill(self) -> None:
        self._process.kill()

    def send_signal(self, signal: Signals) -> None:
        self._process.send_signal(signal)

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        return self._process.returncode

    @property
    def stdin(self) -> abc.ByteSendStream | None:
        return self._stdin

    @property
    def stdout(self) -> abc.ByteReceiveStream | None:
        return self._stdout

    @property
    def stderr(self) -> abc.ByteReceiveStream | None:
        return self._stderr


class _ProcessPoolShutdownInstrument(trio.abc.Instrument):
    def after_run(self) -> None:
        super().after_run()


current_default_worker_process_limiter: trio.lowlevel.RunVar = RunVar(
    "current_default_worker_process_limiter"
)


async def _shutdown_process_pool(workers: set[abc.Process]) -> None:
    try:
        await trio.sleep(math.inf)
    except trio.Cancelled:
        for process in workers:
            if process.returncode is None:
                process.kill()

        with CancelScope(shield=True):
            for process in workers:
                await process.aclose()


#
# Sockets and networking
#


class _TrioSocketMixin(Generic[T_SockAddr]):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        self._trio_socket = trio_socket
        self._closed = False

    def _check_closed(self) -> None:
        if self._closed:
            raise ClosedResourceError
        if self._trio_socket.fileno() < 0:
            raise BrokenResourceError

    @property
    def _raw_socket(self) -> socket.socket:
        return self._trio_socket._sock  # type: ignore[attr-defined]

    async def aclose(self) -> None:
        if self._trio_socket.fileno() >= 0:
            self._closed = True
            self._trio_socket.close()

    def _convert_socket_error(self, exc: BaseException) -> NoReturn:
        if isinstance(exc, trio.ClosedResourceError):
            raise ClosedResourceError from exc
        elif self._trio_socket.fileno() < 0 and self._closed:
            raise ClosedResourceError from None
        elif isinstance(exc, OSError):
            raise BrokenResourceError from exc
        else:
            raise exc


class SocketStream(_TrioSocketMixin, abc.SocketStream):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        super().__init__(trio_socket)
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    async def receive(self, max_bytes: int = 65536) -> bytes:
        with self._receive_guard:
            try:
                data = await self._trio_socket.recv(max_bytes)
            except BaseException as exc:
                self._convert_socket_error(exc)

            if data:
                return data
            else:
                raise EndOfStream

    async def send(self, item: bytes) -> None:
        with self._send_guard:
            view = memoryview(item)
            while view:
                try:
                    bytes_sent = await self._trio_socket.send(view)
                except BaseException as exc:
                    self._convert_socket_error(exc)

                view = view[bytes_sent:]

    async def send_eof(self) -> None:
        self._trio_socket.shutdown(socket.SHUT_WR)


class UNIXSocketStream(SocketStream, abc.UNIXSocketStream):
    async def receive_fds(self, msglen: int, maxfds: int) -> tuple[bytes, list[int]]:
        if not isinstance(msglen, int) or msglen < 0:
            raise ValueError("msglen must be a non-negative integer")
        if not isinstance(maxfds, int) or maxfds < 1:
            raise ValueError("maxfds must be a positive integer")

        fds = array.array("i")
        await trio.lowlevel.checkpoint()
        with self._receive_guard:
            while True:
                try:
                    message, ancdata, flags, addr = await self._trio_socket.recvmsg(
                        msglen, socket.CMSG_LEN(maxfds * fds.itemsize)
                    )
                except BaseException as exc:
                    self._convert_socket_error(exc)
                else:
                    if not message and not ancdata:
                        raise EndOfStream

                    break

        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level != socket.SOL_SOCKET or cmsg_type != socket.SCM_RIGHTS:
                raise RuntimeError(
                    f"Received unexpected ancillary data; message = {message!r}, "
                    f"cmsg_level = {cmsg_level}, cmsg_type = {cmsg_type}"
                )

            fds.frombytes(cmsg_data[: len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])

        return message, list(fds)

    async def send_fds(self, message: bytes, fds: Collection[int | IOBase]) -> None:
        if not message:
            raise ValueError("message must not be empty")
        if not fds:
            raise ValueError("fds must not be empty")

        filenos: list[int] = []
        for fd in fds:
            if isinstance(fd, int):
                filenos.append(fd)
            elif isinstance(fd, IOBase):
                filenos.append(fd.fileno())

        fdarray = array.array("i", filenos)
        await trio.lowlevel.checkpoint()
        with self._send_guard:
            while True:
                try:
                    await self._trio_socket.sendmsg(
                        [message],
                        [
                            (
                                socket.SOL_SOCKET,
                                socket.SCM_RIGHTS,
                                fdarray,
                            )
                        ],
                    )
                    break
                except BaseException as exc:
                    self._convert_socket_error(exc)


class TCPSocketListener(_TrioSocketMixin, abc.SocketListener):
    def __init__(self, raw_socket: socket.socket):
        super().__init__(trio.socket.from_stdlib_socket(raw_socket))
        self._accept_guard = ResourceGuard("accepting connections from")

    async def accept(self) -> SocketStream:
        with self._accept_guard:
            try:
                trio_socket, _addr = await self._trio_socket.accept()
            except BaseException as exc:
                self._convert_socket_error(exc)

        trio_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return SocketStream(trio_socket)


class UNIXSocketListener(_TrioSocketMixin, abc.SocketListener):
    def __init__(self, raw_socket: socket.socket):
        super().__init__(trio.socket.from_stdlib_socket(raw_socket))
        self._accept_guard = ResourceGuard("accepting connections from")

    async def accept(self) -> UNIXSocketStream:
        with self._accept_guard:
            try:
                trio_socket, _addr = await self._trio_socket.accept()
            except BaseException as exc:
                self._convert_socket_error(exc)

        return UNIXSocketStream(trio_socket)


class UDPSocket(_TrioSocketMixin[IPSockAddrType], abc.UDPSocket):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        super().__init__(trio_socket)
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    async def receive(self) -> tuple[bytes, IPSockAddrType]:
        with self._receive_guard:
            try:
                data, addr = await self._trio_socket.recvfrom(65536)
                return data, convert_ipv6_sockaddr(addr)
            except BaseException as exc:
                self._convert_socket_error(exc)

    async def send(self, item: UDPPacketType) -> None:
        with self._send_guard:
            try:
                await self._trio_socket.sendto(*item)
            except BaseException as exc:
                self._convert_socket_error(exc)


class ConnectedUDPSocket(_TrioSocketMixin[IPSockAddrType], abc.ConnectedUDPSocket):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        super().__init__(trio_socket)
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    async def receive(self) -> bytes:
        with self._receive_guard:
            try:
                return await self._trio_socket.recv(65536)
            except BaseException as exc:
                self._convert_socket_error(exc)

    async def send(self, item: bytes) -> None:
        with self._send_guard:
            try:
                await self._trio_socket.send(item)
            except BaseException as exc:
                self._convert_socket_error(exc)


class UNIXDatagramSocket(_TrioSocketMixin[str], abc.UNIXDatagramSocket):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        super().__init__(trio_socket)
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    async def receive(self) -> UNIXDatagramPacketType:
        with self._receive_guard:
            try:
                data, addr = await self._trio_socket.recvfrom(65536)
                return data, addr
            except BaseException as exc:
                self._convert_socket_error(exc)

    async def send(self, item: UNIXDatagramPacketType) -> None:
        with self._send_guard:
            try:
                await self._trio_socket.sendto(*item)
            except BaseException as exc:
                self._convert_socket_error(exc)


class ConnectedUNIXDatagramSocket(
    _TrioSocketMixin[str], abc.ConnectedUNIXDatagramSocket
):
    def __init__(self, trio_socket: TrioSocketType) -> None:
        super().__init__(trio_socket)
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    async def receive(self) -> bytes:
        with self._receive_guard:
            try:
                return await self._trio_socket.recv(65536)
            except BaseException as exc:
                self._convert_socket_error(exc)

    async def send(self, item: bytes) -> None:
        with self._send_guard:
            try:
                await self._trio_socket.send(item)
            except BaseException as exc:
                self._convert_socket_error(exc)


#
# Synchronization
#


class Event(BaseEvent):
    def __new__(cls) -> Event:
        return object.__new__(cls)

    def __init__(self) -> None:
        self.__original = trio.Event()

    def is_set(self) -> bool:
        return self.__original.is_set()

    async def wait(self) -> None:
        return await self.__original.wait()

    def statistics(self) -> EventStatistics:
        orig_statistics = self.__original.statistics()
        return EventStatistics(tasks_waiting=orig_statistics.tasks_waiting)

    def set(self) -> None:
        self.__original.set()


class Lock(BaseLock):
    def __new__(cls, *, fast_acquire: bool = False) -> Lock:
        return object.__new__(cls)

    def __init__(self, *, fast_acquire: bool = False) -> None:
        self._fast_acquire = fast_acquire
        self.__original = trio.Lock()

    @staticmethod
    def _convert_runtime_error_msg(exc: RuntimeError) -> None:
        if exc.args == ("attempt to re-acquire an already held Lock",):
            exc.args = ("Attempted to acquire an already held Lock",)

    async def acquire(self) -> None:
        if not self._fast_acquire:
            try:
                await self.__original.acquire()
            except RuntimeError as exc:
                self._convert_runtime_error_msg(exc)
                raise

            return

        # This is the "fast path" where we don't let other tasks run
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.__original.acquire_nowait()
        except trio.WouldBlock:
            await self.__original._lot.park()
        except RuntimeError as exc:
            self._convert_runtime_error_msg(exc)
            raise

    def acquire_nowait(self) -> None:
        try:
            self.__original.acquire_nowait()
        except trio.WouldBlock:
            raise WouldBlock from None
        except RuntimeError as exc:
            self._convert_runtime_error_msg(exc)
            raise

    def locked(self) -> bool:
        return self.__original.locked()

    def release(self) -> None:
        self.__original.release()

    def statistics(self) -> LockStatistics:
        orig_statistics = self.__original.statistics()
        owner = TrioTaskInfo(orig_statistics.owner) if orig_statistics.owner else None
        return LockStatistics(
            orig_statistics.locked, owner, orig_statistics.tasks_waiting
        )


class Semaphore(BaseSemaphore):
    def __new__(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> Semaphore:
        return object.__new__(cls)

    def __init__(
        self,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> None:
        super().__init__(initial_value, max_value=max_value, fast_acquire=fast_acquire)
        self.__original = trio.Semaphore(initial_value, max_value=max_value)

    async def acquire(self) -> None:
        if not self._fast_acquire:
            await self.__original.acquire()
            return

        # This is the "fast path" where we don't let other tasks run
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.__original.acquire_nowait()
        except trio.WouldBlock:
            await self.__original._lot.park()

    def acquire_nowait(self) -> None:
        try:
            self.__original.acquire_nowait()
        except trio.WouldBlock:
            raise WouldBlock from None

    @property
    def max_value(self) -> int | None:
        return self.__original.max_value

    @property
    def value(self) -> int:
        return self.__original.value

    def release(self) -> None:
        self.__original.release()

    def statistics(self) -> SemaphoreStatistics:
        orig_statistics = self.__original.statistics()
        return SemaphoreStatistics(orig_statistics.tasks_waiting)


class CapacityLimiter(BaseCapacityLimiter):
    def __new__(
        cls,
        total_tokens: float | None = None,
        *,
        original: trio.CapacityLimiter | None = None,
    ) -> CapacityLimiter:
        return object.__new__(cls)

    def __init__(
        self,
        total_tokens: float | None = None,
        *,
        original: trio.CapacityLimiter | None = None,
    ) -> None:
        if original is not None:
            self.__original = original
        else:
            assert total_tokens is not None
            self.__original = trio.CapacityLimiter(total_tokens)

    async def __aenter__(self) -> None:
        return await self.__original.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.__original.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def total_tokens(self) -> float:
        return self.__original.total_tokens

    @total_tokens.setter
    def total_tokens(self, value: float) -> None:
        self.__original.total_tokens = value

    @property
    def borrowed_tokens(self) -> int:
        return self.__original.borrowed_tokens

    @property
    def available_tokens(self) -> float:
        return self.__original.available_tokens

    def acquire_nowait(self) -> None:
        self.__original.acquire_nowait()

    def acquire_on_behalf_of_nowait(self, borrower: object) -> None:
        self.__original.acquire_on_behalf_of_nowait(borrower)

    async def acquire(self) -> None:
        await self.__original.acquire()

    async def acquire_on_behalf_of(self, borrower: object) -> None:
        await self.__original.acquire_on_behalf_of(borrower)

    def release(self) -> None:
        return self.__original.release()

    def release_on_behalf_of(self, borrower: object) -> None:
        return self.__original.release_on_behalf_of(borrower)

    def statistics(self) -> CapacityLimiterStatistics:
        orig = self.__original.statistics()
        return CapacityLimiterStatistics(
            borrowed_tokens=orig.borrowed_tokens,
            total_tokens=orig.total_tokens,
            borrowers=tuple(orig.borrowers),
            tasks_waiting=orig.tasks_waiting,
        )


_capacity_limiter_wrapper: trio.lowlevel.RunVar = RunVar("_capacity_limiter_wrapper")


#
# Signal handling
#


class _SignalReceiver:
    _iterator: AsyncIterator[int]

    def __init__(self, signals: tuple[Signals, ...]):
        self._signals = signals

    def __enter__(self) -> _SignalReceiver:
        self._cm = trio.open_signal_receiver(*self._signals)
        self._iterator = self._cm.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return self._cm.__exit__(exc_type, exc_val, exc_tb)

    def __aiter__(self) -> _SignalReceiver:
        return self

    async def __anext__(self) -> Signals:
        signum = await self._iterator.__anext__()
        return Signals(signum)


#
# Testing and debugging
#


class TestRunner(abc.TestRunner):
    def __init__(self, **options: Any) -> None:
        from queue import Queue

        self._call_queue: Queue[Callable[[], object]] = Queue()
        self._send_stream: MemoryObjectSendStream | None = None
        self._options = options

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._send_stream:
            self._send_stream.close()
            while self._send_stream is not None:
                self._call_queue.get()()

    async def _run_tests_and_fixtures(self) -> None:
        self._send_stream, receive_stream = create_memory_object_stream(1)
        with receive_stream:
            async for coro, outcome_holder in receive_stream:
                try:
                    retval = await coro
                except BaseException as exc:
                    outcome_holder.append(Error(exc))
                else:
                    outcome_holder.append(Value(retval))

    def _main_task_finished(self, outcome: object) -> None:
        self._send_stream = None

    def _call_in_runner_task(
        self,
        func: Callable[P, Awaitable[T_Retval]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T_Retval:
        if self._send_stream is None:
            trio.lowlevel.start_guest_run(
                self._run_tests_and_fixtures,
                run_sync_soon_threadsafe=self._call_queue.put,
                done_callback=self._main_task_finished,
                **self._options,
            )
            while self._send_stream is None:
                self._call_queue.get()()

        outcome_holder: list[Outcome] = []
        self._send_stream.send_nowait((func(*args, **kwargs), outcome_holder))
        while not outcome_holder:
            self._call_queue.get()()

        return outcome_holder[0].unwrap()

    def run_asyncgen_fixture(
        self,
        fixture_func: Callable[..., AsyncGenerator[T_Retval, Any]],
        kwargs: dict[str, Any],
    ) -> Iterable[T_Retval]:
        asyncgen = fixture_func(**kwargs)
        fixturevalue: T_Retval = self._call_in_runner_task(asyncgen.asend, None)

        yield fixturevalue

        try:
            self._call_in_runner_task(asyncgen.asend, None)
        except StopAsyncIteration:
            pass
        else:
            self._call_in_runner_task(asyncgen.aclose)
            raise RuntimeError("Async generator fixture did not stop")

    def run_fixture(
        self,
        fixture_func: Callable[..., Coroutine[Any, Any, T_Retval]],
        kwargs: dict[str, Any],
    ) -> T_Retval:
        return self._call_in_runner_task(fixture_func, **kwargs)

    def run_test(
        self, test_func: Callable[..., Coroutine[Any, Any, Any]], kwargs: dict[str, Any]
    ) -> None:
        self._call_in_runner_task(test_func, **kwargs)


class TrioTaskInfo(TaskInfo):
    def __init__(self, task: trio.lowlevel.Task):
        parent_id = None
        if task.parent_nursery and task.parent_nursery.parent_task:
            parent_id = id(task.parent_nursery.parent_task)

        super().__init__(id(task), parent_id, task.name, task.coro)
        self._task = weakref.proxy(task)

    def has_pending_cancellation(self) -> bool:
        try:
            return self._task._cancel_status.effectively_cancelled
        except ReferenceError:
            # If the task is no longer around, it surely doesn't have a cancellation
            # pending
            return False


class TrioBackend(AsyncBackend):
    @classmethod
    def run(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        options: dict[str, Any],
    ) -> T_Retval:
        return trio.run(func, *args)

    @classmethod
    def current_token(cls) -> object:
        return trio.lowlevel.current_trio_token()

    @classmethod
    def current_time(cls) -> float:
        return trio.current_time()

    @classmethod
    def cancelled_exception_class(cls) -> type[BaseException]:
        return trio.Cancelled

    @classmethod
    async def checkpoint(cls) -> None:
        await trio.lowlevel.checkpoint()

    @classmethod
    async def checkpoint_if_cancelled(cls) -> None:
        await trio.lowlevel.checkpoint_if_cancelled()

    @classmethod
    async def cancel_shielded_checkpoint(cls) -> None:
        await trio.lowlevel.cancel_shielded_checkpoint()

    @classmethod
    async def sleep(cls, delay: float) -> None:
        await trio.sleep(delay)

    @classmethod
    def create_cancel_scope(
        cls, *, deadline: float = math.inf, shield: bool = False
    ) -> abc.CancelScope:
        return CancelScope(deadline=deadline, shield=shield)

    @classmethod
    def current_effective_deadline(cls) -> float:
        return trio.current_effective_deadline()

    @classmethod
    def create_task_group(cls) -> abc.TaskGroup:
        return TaskGroup()

    @classmethod
    def create_event(cls) -> abc.Event:
        return Event()

    @classmethod
    def create_lock(cls, *, fast_acquire: bool) -> Lock:
        return Lock(fast_acquire=fast_acquire)

    @classmethod
    def create_semaphore(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> abc.Semaphore:
        return Semaphore(initial_value, max_value=max_value, fast_acquire=fast_acquire)

    @classmethod
    def create_capacity_limiter(cls, total_tokens: float) -> CapacityLimiter:
        return CapacityLimiter(total_tokens)

    @classmethod
    async def run_sync_in_worker_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        abandon_on_cancel: bool = False,
        limiter: abc.CapacityLimiter | None = None,
    ) -> T_Retval:
        def wrapper() -> T_Retval:
            with claim_worker_thread(TrioBackend, token):
                return func(*args)

        token = TrioBackend.current_token()
        return await run_sync(
            wrapper,
            abandon_on_cancel=abandon_on_cancel,
            limiter=cast(trio.CapacityLimiter, limiter),
        )

    @classmethod
    def check_cancelled(cls) -> None:
        trio.from_thread.check_cancelled()

    @classmethod
    def run_async_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        return trio.from_thread.run(func, *args)

    @classmethod
    def run_sync_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        return trio.from_thread.run_sync(func, *args)

    @classmethod
    def create_blocking_portal(cls) -> abc.BlockingPortal:
        return BlockingPortal()

    @classmethod
    async def open_process(
        cls,
        command: StrOrBytesPath | Sequence[StrOrBytesPath],
        *,
        stdin: int | IO[Any] | None,
        stdout: int | IO[Any] | None,
        stderr: int | IO[Any] | None,
        **kwargs: Any,
    ) -> Process:
        def convert_item(item: StrOrBytesPath) -> str:
            str_or_bytes = os.fspath(item)
            if isinstance(str_or_bytes, str):
                return str_or_bytes
            else:
                return os.fsdecode(str_or_bytes)

        if isinstance(command, (str, bytes, PathLike)):
            process = await trio.lowlevel.open_process(
                convert_item(command),
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                shell=True,
                **kwargs,
            )
        else:
            process = await trio.lowlevel.open_process(
                [convert_item(item) for item in command],
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                shell=False,
                **kwargs,
            )

        stdin_stream = SendStreamWrapper(process.stdin) if process.stdin else None
        stdout_stream = ReceiveStreamWrapper(process.stdout) if process.stdout else None
        stderr_stream = ReceiveStreamWrapper(process.stderr) if process.stderr else None
        return Process(process, stdin_stream, stdout_stream, stderr_stream)

    @classmethod
    def setup_process_pool_exit_at_shutdown(cls, workers: set[abc.Process]) -> None:
        trio.lowlevel.spawn_system_task(_shutdown_process_pool, workers)

    @classmethod
    async def connect_tcp(
        cls, host: str, port: int, local_address: IPSockAddrType | None = None
    ) -> SocketStream:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        trio_socket = trio.socket.socket(family)
        trio_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if local_address:
            await trio_socket.bind(local_address)

        try:
            await trio_socket.connect((host, port))
        except BaseException:
            trio_socket.close()
            raise

        return SocketStream(trio_socket)

    @classmethod
    async def connect_unix(cls, path: str | bytes) -> abc.UNIXSocketStream:
        trio_socket = trio.socket.socket(socket.AF_UNIX)
        try:
            await trio_socket.connect(path)
        except BaseException:
            trio_socket.close()
            raise

        return UNIXSocketStream(trio_socket)

    @classmethod
    def create_tcp_listener(cls, sock: socket.socket) -> abc.SocketListener:
        return TCPSocketListener(sock)

    @classmethod
    def create_unix_listener(cls, sock: socket.socket) -> abc.SocketListener:
        return UNIXSocketListener(sock)

    @classmethod
    async def create_udp_socket(
        cls,
        family: socket.AddressFamily,
        local_address: IPSockAddrType | None,
        remote_address: IPSockAddrType | None,
        reuse_port: bool,
    ) -> UDPSocket | ConnectedUDPSocket:
        trio_socket = trio.socket.socket(family=family, type=socket.SOCK_DGRAM)

        if reuse_port:
            trio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        if local_address:
            await trio_socket.bind(local_address)

        if remote_address:
            await trio_socket.connect(remote_address)
            return ConnectedUDPSocket(trio_socket)
        else:
            return UDPSocket(trio_socket)

    @classmethod
    @overload
    async def create_unix_datagram_socket(
        cls, raw_socket: socket.socket, remote_path: None
    ) -> abc.UNIXDatagramSocket: ...

    @classmethod
    @overload
    async def create_unix_datagram_socket(
        cls, raw_socket: socket.socket, remote_path: str | bytes
    ) -> abc.ConnectedUNIXDatagramSocket: ...

    @classmethod
    async def create_unix_datagram_socket(
        cls, raw_socket: socket.socket, remote_path: str | bytes | None
    ) -> abc.UNIXDatagramSocket | abc.ConnectedUNIXDatagramSocket:
        trio_socket = trio.socket.from_stdlib_socket(raw_socket)

        if remote_path:
            await trio_socket.connect(remote_path)
            return ConnectedUNIXDatagramSocket(trio_socket)
        else:
            return UNIXDatagramSocket(trio_socket)

    @classmethod
    async def getaddrinfo(
        cls,
        host: bytes | str | None,
        port: str | int | None,
        *,
        family: int | AddressFamily = 0,
        type: int | SocketKind = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> Sequence[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        return await trio.socket.getaddrinfo(host, port, family, type, proto, flags)

    @classmethod
    async def getnameinfo(
        cls, sockaddr: IPSockAddrType, flags: int = 0
    ) -> tuple[str, str]:
        return await trio.socket.getnameinfo(sockaddr, flags)

    @classmethod
    async def wait_readable(cls, obj: HasFileno | int) -> None:
        try:
            await wait_readable(obj)
        except trio.ClosedResourceError as exc:
            raise ClosedResourceError().with_traceback(exc.__traceback__) from None
        except trio.BusyResourceError:
            raise BusyResourceError("reading from") from None

    @classmethod
    async def wait_writable(cls, obj: HasFileno | int) -> None:
        try:
            await wait_writable(obj)
        except trio.ClosedResourceError as exc:
            raise ClosedResourceError().with_traceback(exc.__traceback__) from None
        except trio.BusyResourceError:
            raise BusyResourceError("writing to") from None

    @classmethod
    def current_default_thread_limiter(cls) -> CapacityLimiter:
        try:
            return _capacity_limiter_wrapper.get()
        except LookupError:
            limiter = CapacityLimiter(
                original=trio.to_thread.current_default_thread_limiter()
            )
            _capacity_limiter_wrapper.set(limiter)
            return limiter

    @classmethod
    def open_signal_receiver(
        cls, *signals: Signals
    ) -> AbstractContextManager[AsyncIterator[Signals]]:
        return _SignalReceiver(signals)

    @classmethod
    def get_current_task(cls) -> TaskInfo:
        task = current_task()
        return TrioTaskInfo(task)

    @classmethod
    def get_running_tasks(cls) -> Sequence[TaskInfo]:
        root_task = current_root_task()
        assert root_task
        task_infos = [TrioTaskInfo(root_task)]
        nurseries = root_task.child_nurseries
        while nurseries:
            new_nurseries: list[trio.Nursery] = []
            for nursery in nurseries:
                for task in nursery.child_tasks:
                    task_infos.append(TrioTaskInfo(task))
                    new_nurseries.extend(task.child_nurseries)

            nurseries = new_nurseries

        return task_infos

    @classmethod
    async def wait_all_tasks_blocked(cls) -> None:
        from trio.testing import wait_all_tasks_blocked

        await wait_all_tasks_blocked()

    @classmethod
    def create_test_runner(cls, options: dict[str, Any]) -> TestRunner:
        return TestRunner(**options)


backend_class = TrioBackend

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\database.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""PEP 376 implementation."""

from __future__ import unicode_literals

import base64
import codecs
import contextlib
import hashlib
import logging
import os
import posixpath
import sys
import zipimport

from . import DistlibException, resources
from .compat import StringIO
from .version import get_scheme, UnsupportedVersionError
from .metadata import (Metadata, METADATA_FILENAME, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME)
from .util import (parse_requirement, cached_property, parse_name_and_version, read_exports, write_exports, CSVReader,
                   CSVWriter)

__all__ = [
    'Distribution', 'BaseInstalledDistribution', 'InstalledDistribution', 'EggInfoDistribution', 'DistributionPath'
]

logger = logging.getLogger(__name__)

EXPORTS_FILENAME = 'pydist-exports.json'
COMMANDS_FILENAME = 'pydist-commands.json'

DIST_FILES = ('INSTALLER', METADATA_FILENAME, 'RECORD', 'REQUESTED', 'RESOURCES', EXPORTS_FILENAME, 'SHARED')

DISTINFO_EXT = '.dist-info'


class _Cache(object):
    """
    A simple cache mapping names and .dist-info paths to distributions
    """

    def __init__(self):
        """
        Initialise an instance. There is normally one for each DistributionPath.
        """
        self.name = {}
        self.path = {}
        self.generated = False

    def clear(self):
        """
        Clear the cache, setting it to its initial state.
        """
        self.name.clear()
        self.path.clear()
        self.generated = False

    def add(self, dist):
        """
        Add a distribution to the cache.
        :param dist: The distribution to add.
        """
        if dist.path not in self.path:
            self.path[dist.path] = dist
            self.name.setdefault(dist.key, []).append(dist)


class DistributionPath(object):
    """
    Represents a set of distributions installed on a path (typically sys.path).
    """

    def __init__(self, path=None, include_egg=False):
        """
        Create an instance from a path, optionally including legacy (distutils/
        setuptools/distribute) distributions.
        :param path: The path to use, as a list of directories. If not specified,
                     sys.path is used.
        :param include_egg: If True, this instance will look for and return legacy
                            distributions as well as those based on PEP 376.
        """
        if path is None:
            path = sys.path
        self.path = path
        self._include_dist = True
        self._include_egg = include_egg

        self._cache = _Cache()
        self._cache_egg = _Cache()
        self._cache_enabled = True
        self._scheme = get_scheme('default')

    def _get_cache_enabled(self):
        return self._cache_enabled

    def _set_cache_enabled(self, value):
        self._cache_enabled = value

    cache_enabled = property(_get_cache_enabled, _set_cache_enabled)

    def clear_cache(self):
        """
        Clears the internal cache.
        """
        self._cache.clear()
        self._cache_egg.clear()

    def _yield_distributions(self):
        """
        Yield .dist-info and/or .egg(-info) distributions.
        """
        # We need to check if we've seen some resources already, because on
        # some Linux systems (e.g. some Debian/Ubuntu variants) there are
        # symlinks which alias other files in the environment.
        seen = set()
        for path in self.path:
            finder = resources.finder_for_path(path)
            if finder is None:
                continue
            r = finder.find('')
            if not r or not r.is_container:
                continue
            rset = sorted(r.resources)
            for entry in rset:
                r = finder.find(entry)
                if not r or r.path in seen:
                    continue
                try:
                    if self._include_dist and entry.endswith(DISTINFO_EXT):
                        possible_filenames = [METADATA_FILENAME, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME]
                        for metadata_filename in possible_filenames:
                            metadata_path = posixpath.join(entry, metadata_filename)
                            pydist = finder.find(metadata_path)
                            if pydist:
                                break
                        else:
                            continue

                        with contextlib.closing(pydist.as_stream()) as stream:
                            metadata = Metadata(fileobj=stream, scheme='legacy')
                        logger.debug('Found %s', r.path)
                        seen.add(r.path)
                        yield new_dist_class(r.path, metadata=metadata, env=self)
                    elif self._include_egg and entry.endswith(('.egg-info', '.egg')):
                        logger.debug('Found %s', r.path)
                        seen.add(r.path)
                        yield old_dist_class(r.path, self)
                except Exception as e:
                    msg = 'Unable to read distribution at %s, perhaps due to bad metadata: %s'
                    logger.warning(msg, r.path, e)
                    import warnings
                    warnings.warn(msg % (r.path, e), stacklevel=2)

    def _generate_cache(self):
        """
        Scan the path for distributions and populate the cache with
        those that are found.
        """
        gen_dist = not self._cache.generated
        gen_egg = self._include_egg and not self._cache_egg.generated
        if gen_dist or gen_egg:
            for dist in self._yield_distributions():
                if isinstance(dist, InstalledDistribution):
                    self._cache.add(dist)
                else:
                    self._cache_egg.add(dist)

            if gen_dist:
                self._cache.generated = True
            if gen_egg:
                self._cache_egg.generated = True

    @classmethod
    def distinfo_dirname(cls, name, version):
        """
        The *name* and *version* parameters are converted into their
        filename-escaped form, i.e. any ``'-'`` characters are replaced
        with ``'_'`` other than the one in ``'dist-info'`` and the one
        separating the name from the version number.

        :parameter name: is converted to a standard distribution name by replacing
                         any runs of non- alphanumeric characters with a single
                         ``'-'``.
        :type name: string
        :parameter version: is converted to a standard version string. Spaces
                            become dots, and all other non-alphanumeric characters
                            (except dots) become dashes, with runs of multiple
                            dashes condensed to a single dash.
        :type version: string
        :returns: directory name
        :rtype: string"""
        name = name.replace('-', '_')
        return '-'.join([name, version]) + DISTINFO_EXT

    def get_distributions(self):
        """
        Provides an iterator that looks for distributions and returns
        :class:`InstalledDistribution` or
        :class:`EggInfoDistribution` instances for each one of them.

        :rtype: iterator of :class:`InstalledDistribution` and
                :class:`EggInfoDistribution` instances
        """
        if not self._cache_enabled:
            for dist in self._yield_distributions():
                yield dist
        else:
            self._generate_cache()

            for dist in self._cache.path.values():
                yield dist

            if self._include_egg:
                for dist in self._cache_egg.path.values():
                    yield dist

    def get_distribution(self, name):
        """
        Looks for a named distribution on the path.

        This function only returns the first result found, as no more than one
        value is expected. If nothing is found, ``None`` is returned.

        :rtype: :class:`InstalledDistribution`, :class:`EggInfoDistribution`
                or ``None``
        """
        result = None
        name = name.lower()
        if not self._cache_enabled:
            for dist in self._yield_distributions():
                if dist.key == name:
                    result = dist
                    break
        else:
            self._generate_cache()

            if name in self._cache.name:
                result = self._cache.name[name][0]
            elif self._include_egg and name in self._cache_egg.name:
                result = self._cache_egg.name[name][0]
        return result

    def provides_distribution(self, name, version=None):
        """
        Iterates over all distributions to find which distributions provide *name*.
        If a *version* is provided, it will be used to filter the results.

        This function only returns the first result found, since no more than
        one values are expected. If the directory is not found, returns ``None``.

        :parameter version: a version specifier that indicates the version
                            required, conforming to the format in ``PEP-345``

        :type name: string
        :type version: string
        """
        matcher = None
        if version is not None:
            try:
                matcher = self._scheme.matcher('%s (%s)' % (name, version))
            except ValueError:
                raise DistlibException('invalid name or version: %r, %r' % (name, version))

        for dist in self.get_distributions():
            # We hit a problem on Travis where enum34 was installed and doesn't
            # have a provides attribute ...
            if not hasattr(dist, 'provides'):
                logger.debug('No "provides": %s', dist)
            else:
                provided = dist.provides

                for p in provided:
                    p_name, p_ver = parse_name_and_version(p)
                    if matcher is None:
                        if p_name == name:
                            yield dist
                            break
                    else:
                        if p_name == name and matcher.match(p_ver):
                            yield dist
                            break

    def get_file_path(self, name, relative_path):
        """
        Return the path to a resource file.
        """
        dist = self.get_distribution(name)
        if dist is None:
            raise LookupError('no distribution named %r found' % name)
        return dist.get_resource_path(relative_path)

    def get_exported_entries(self, category, name=None):
        """
        Return all of the exported entries in a particular category.

        :param category: The category to search for entries.
        :param name: If specified, only entries with that name are returned.
        """
        for dist in self.get_distributions():
            r = dist.exports
            if category in r:
                d = r[category]
                if name is not None:
                    if name in d:
                        yield d[name]
                else:
                    for v in d.values():
                        yield v


class Distribution(object):
    """
    A base class for distributions, whether installed or from indexes.
    Either way, it must have some metadata, so that's all that's needed
    for construction.
    """

    build_time_dependency = False
    """
    Set to True if it's known to be only a build-time dependency (i.e.
    not needed after installation).
    """

    requested = False
    """A boolean that indicates whether the ``REQUESTED`` metadata file is
    present (in other words, whether the package was installed by user
    request or it was installed as a dependency)."""

    def __init__(self, metadata):
        """
        Initialise an instance.
        :param metadata: The instance of :class:`Metadata` describing this
        distribution.
        """
        self.metadata = metadata
        self.name = metadata.name
        self.key = self.name.lower()  # for case-insensitive comparisons
        self.version = metadata.version
        self.locator = None
        self.digest = None
        self.extras = None  # additional features requested
        self.context = None  # environment marker overrides
        self.download_urls = set()
        self.digests = {}

    @property
    def source_url(self):
        """
        The source archive download URL for this distribution.
        """
        return self.metadata.source_url

    download_url = source_url  # Backward compatibility

    @property
    def name_and_version(self):
        """
        A utility property which displays the name and version in parentheses.
        """
        return '%s (%s)' % (self.name, self.version)

    @property
    def provides(self):
        """
        A set of distribution names and versions provided by this distribution.
        :return: A set of "name (version)" strings.
        """
        plist = self.metadata.provides
        s = '%s (%s)' % (self.name, self.version)
        if s not in plist:
            plist.append(s)
        return plist

    def _get_requirements(self, req_attr):
        md = self.metadata
        reqts = getattr(md, req_attr)
        logger.debug('%s: got requirements %r from metadata: %r', self.name, req_attr, reqts)
        return set(md.get_requirements(reqts, extras=self.extras, env=self.context))

    @property
    def run_requires(self):
        return self._get_requirements('run_requires')

    @property
    def meta_requires(self):
        return self._get_requirements('meta_requires')

    @property
    def build_requires(self):
        return self._get_requirements('build_requires')

    @property
    def test_requires(self):
        return self._get_requirements('test_requires')

    @property
    def dev_requires(self):
        return self._get_requirements('dev_requires')

    def matches_requirement(self, req):
        """
        Say if this instance matches (fulfills) a requirement.
        :param req: The requirement to match.
        :rtype req: str
        :return: True if it matches, else False.
        """
        # Requirement may contain extras - parse to lose those
        # from what's passed to the matcher
        r = parse_requirement(req)
        scheme = get_scheme(self.metadata.scheme)
        try:
            matcher = scheme.matcher(r.requirement)
        except UnsupportedVersionError:
            # XXX compat-mode if cannot read the version
            logger.warning('could not read version %r - using name only', req)
            name = req.split()[0]
            matcher = scheme.matcher(name)

        name = matcher.key  # case-insensitive

        result = False
        for p in self.provides:
            p_name, p_ver = parse_name_and_version(p)
            if p_name != name:
                continue
            try:
                result = matcher.match(p_ver)
                break
            except UnsupportedVersionError:
                pass
        return result

    def __repr__(self):
        """
        Return a textual representation of this instance,
        """
        if self.source_url:
            suffix = ' [%s]' % self.source_url
        else:
            suffix = ''
        return '<Distribution %s (%s)%s>' % (self.name, self.version, suffix)

    def __eq__(self, other):
        """
        See if this distribution is the same as another.
        :param other: The distribution to compare with. To be equal to one
                      another. distributions must have the same type, name,
                      version and source_url.
        :return: True if it is the same, else False.
        """
        if type(other) is not type(self):
            result = False
        else:
            result = (self.name == other.name and self.version == other.version and self.source_url == other.source_url)
        return result

    def __hash__(self):
        """
        Compute hash in a way which matches the equality test.
        """
        return hash(self.name) + hash(self.version) + hash(self.source_url)


class BaseInstalledDistribution(Distribution):
    """
    This is the base class for installed distributions (whether PEP 376 or
    legacy).
    """

    hasher = None

    def __init__(self, metadata, path, env=None):
        """
        Initialise an instance.
        :param metadata: An instance of :class:`Metadata` which describes the
                         distribution. This will normally have been initialised
                         from a metadata file in the ``path``.
        :param path:     The path of the ``.dist-info`` or ``.egg-info``
                         directory for the distribution.
        :param env:      This is normally the :class:`DistributionPath`
                         instance where this distribution was found.
        """
        super(BaseInstalledDistribution, self).__init__(metadata)
        self.path = path
        self.dist_path = env

    def get_hash(self, data, hasher=None):
        """
        Get the hash of some data, using a particular hash algorithm, if
        specified.

        :param data: The data to be hashed.
        :type data: bytes
        :param hasher: The name of a hash implementation, supported by hashlib,
                       or ``None``. Examples of valid values are ``'sha1'``,
                       ``'sha224'``, ``'sha384'``, '``sha256'``, ``'md5'`` and
                       ``'sha512'``. If no hasher is specified, the ``hasher``
                       attribute of the :class:`InstalledDistribution` instance
                       is used. If the hasher is determined to be ``None``, MD5
                       is used as the hashing algorithm.
        :returns: The hash of the data. If a hasher was explicitly specified,
                  the returned hash will be prefixed with the specified hasher
                  followed by '='.
        :rtype: str
        """
        if hasher is None:
            hasher = self.hasher
        if hasher is None:
            hasher = hashlib.md5
            prefix = ''
        else:
            hasher = getattr(hashlib, hasher)
            prefix = '%s=' % self.hasher
        digest = hasher(data).digest()
        digest = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
        return '%s%s' % (prefix, digest)


class InstalledDistribution(BaseInstalledDistribution):
    """
    Created with the *path* of the ``.dist-info`` directory provided to the
    constructor. It reads the metadata contained in ``pydist.json`` when it is
    instantiated., or uses a passed in Metadata instance (useful for when
    dry-run mode is being used).
    """

    hasher = 'sha256'

    def __init__(self, path, metadata=None, env=None):
        self.modules = []
        self.finder = finder = resources.finder_for_path(path)
        if finder is None:
            raise ValueError('finder unavailable for %s' % path)
        if env and env._cache_enabled and path in env._cache.path:
            metadata = env._cache.path[path].metadata
        elif metadata is None:
            r = finder.find(METADATA_FILENAME)
            # Temporary - for Wheel 0.23 support
            if r is None:
                r = finder.find(WHEEL_METADATA_FILENAME)
            # Temporary - for legacy support
            if r is None:
                r = finder.find(LEGACY_METADATA_FILENAME)
            if r is None:
                raise ValueError('no %s found in %s' % (METADATA_FILENAME, path))
            with contextlib.closing(r.as_stream()) as stream:
                metadata = Metadata(fileobj=stream, scheme='legacy')

        super(InstalledDistribution, self).__init__(metadata, path, env)

        if env and env._cache_enabled:
            env._cache.add(self)

        r = finder.find('REQUESTED')
        self.requested = r is not None
        p = os.path.join(path, 'top_level.txt')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                data = f.read().decode('utf-8')
            self.modules = data.splitlines()

    def __repr__(self):
        return '<InstalledDistribution %r %s at %r>' % (self.name, self.version, self.path)

    def __str__(self):
        return "%s %s" % (self.name, self.version)

    def _get_records(self):
        """
        Get the list of installed files for the distribution
        :return: A list of tuples of path, hash and size. Note that hash and
                 size might be ``None`` for some entries. The path is exactly
                 as stored in the file (which is as in PEP 376).
        """
        results = []
        r = self.get_distinfo_resource('RECORD')
        with contextlib.closing(r.as_stream()) as stream:
            with CSVReader(stream=stream) as record_reader:
                # Base location is parent dir of .dist-info dir
                # base_location = os.path.dirname(self.path)
                # base_location = os.path.abspath(base_location)
                for row in record_reader:
                    missing = [None for i in range(len(row), 3)]
                    path, checksum, size = row + missing
                    # if not os.path.isabs(path):
                    #     path = path.replace('/', os.sep)
                    #     path = os.path.join(base_location, path)
                    results.append((path, checksum, size))
        return results

    @cached_property
    def exports(self):
        """
        Return the information exported by this distribution.
        :return: A dictionary of exports, mapping an export category to a dict
                 of :class:`ExportEntry` instances describing the individual
                 export entries, and keyed by name.
        """
        result = {}
        r = self.get_distinfo_resource(EXPORTS_FILENAME)
        if r:
            result = self.read_exports()
        return result

    def read_exports(self):
        """
        Read exports data from a file in .ini format.

        :return: A dictionary of exports, mapping an export category to a list
                 of :class:`ExportEntry` instances describing the individual
                 export entries.
        """
        result = {}
        r = self.get_distinfo_resource(EXPORTS_FILENAME)
        if r:
            with contextlib.closing(r.as_stream()) as stream:
                result = read_exports(stream)
        return result

    def write_exports(self, exports):
        """
        Write a dictionary of exports to a file in .ini format.
        :param exports: A dictionary of exports, mapping an export category to
                        a list of :class:`ExportEntry` instances describing the
                        individual export entries.
        """
        rf = self.get_distinfo_file(EXPORTS_FILENAME)
        with open(rf, 'w') as f:
            write_exports(exports, f)

    def get_resource_path(self, relative_path):
        """
        NOTE: This API may change in the future.

        Return the absolute path to a resource file with the given relative
        path.

        :param relative_path: The path, relative to .dist-info, of the resource
                              of interest.
        :return: The absolute path where the resource is to be found.
        """
        r = self.get_distinfo_resource('RESOURCES')
        with contextlib.closing(r.as_stream()) as stream:
            with CSVReader(stream=stream) as resources_reader:
                for relative, destination in resources_reader:
                    if relative == relative_path:
                        return destination
        raise KeyError('no resource file with relative path %r '
                       'is installed' % relative_path)

    def list_installed_files(self):
        """
        Iterates over the ``RECORD`` entries and returns a tuple
        ``(path, hash, size)`` for each line.

        :returns: iterator of (path, hash, size)
        """
        for result in self._get_records():
            yield result

    def write_installed_files(self, paths, prefix, dry_run=False):
        """
        Writes the ``RECORD`` file, using the ``paths`` iterable passed in. Any
        existing ``RECORD`` file is silently overwritten.

        prefix is used to determine when to write absolute paths.
        """
        prefix = os.path.join(prefix, '')
        base = os.path.dirname(self.path)
        base_under_prefix = base.startswith(prefix)
        base = os.path.join(base, '')
        record_path = self.get_distinfo_file('RECORD')
        logger.info('creating %s', record_path)
        if dry_run:
            return None
        with CSVWriter(record_path) as writer:
            for path in paths:
                if os.path.isdir(path) or path.endswith(('.pyc', '.pyo')):
                    # do not put size and hash, as in PEP-376
                    hash_value = size = ''
                else:
                    size = '%d' % os.path.getsize(path)
                    with open(path, 'rb') as fp:
                        hash_value = self.get_hash(fp.read())
                if path.startswith(base) or (base_under_prefix and path.startswith(prefix)):
                    path = os.path.relpath(path, base)
                writer.writerow((path, hash_value, size))

            # add the RECORD file itself
            if record_path.startswith(base):
                record_path = os.path.relpath(record_path, base)
            writer.writerow((record_path, '', ''))
        return record_path

    def check_installed_files(self):
        """
        Checks that the hashes and sizes of the files in ``RECORD`` are
        matched by the files themselves. Returns a (possibly empty) list of
        mismatches. Each entry in the mismatch list will be a tuple consisting
        of the path, 'exists', 'size' or 'hash' according to what didn't match
        (existence is checked first, then size, then hash), the expected
        value and the actual value.
        """
        mismatches = []
        base = os.path.dirname(self.path)
        record_path = self.get_distinfo_file('RECORD')
        for path, hash_value, size in self.list_installed_files():
            if not os.path.isabs(path):
                path = os.path.join(base, path)
            if path == record_path:
                continue
            if not os.path.exists(path):
                mismatches.append((path, 'exists', True, False))
            elif os.path.isfile(path):
                actual_size = str(os.path.getsize(path))
                if size and actual_size != size:
                    mismatches.append((path, 'size', size, actual_size))
                elif hash_value:
                    if '=' in hash_value:
                        hasher = hash_value.split('=', 1)[0]
                    else:
                        hasher = None

                    with open(path, 'rb') as f:
                        actual_hash = self.get_hash(f.read(), hasher)
                        if actual_hash != hash_value:
                            mismatches.append((path, 'hash', hash_value, actual_hash))
        return mismatches

    @cached_property
    def shared_locations(self):
        """
        A dictionary of shared locations whose keys are in the set 'prefix',
        'purelib', 'platlib', 'scripts', 'headers', 'data' and 'namespace'.
        The corresponding value is the absolute path of that category for
        this distribution, and takes into account any paths selected by the
        user at installation time (e.g. via command-line arguments). In the
        case of the 'namespace' key, this would be a list of absolute paths
        for the roots of namespace packages in this distribution.

        The first time this property is accessed, the relevant information is
        read from the SHARED file in the .dist-info directory.
        """
        result = {}
        shared_path = os.path.join(self.path, 'SHARED')
        if os.path.isfile(shared_path):
            with codecs.open(shared_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            for line in lines:
                key, value = line.split('=', 1)
                if key == 'namespace':
                    result.setdefault(key, []).append(value)
                else:
                    result[key] = value
        return result

    def write_shared_locations(self, paths, dry_run=False):
        """
        Write shared location information to the SHARED file in .dist-info.
        :param paths: A dictionary as described in the documentation for
        :meth:`shared_locations`.
        :param dry_run: If True, the action is logged but no file is actually
                        written.
        :return: The path of the file written to.
        """
        shared_path = os.path.join(self.path, 'SHARED')
        logger.info('creating %s', shared_path)
        if dry_run:
            return None
        lines = []
        for key in ('prefix', 'lib', 'headers', 'scripts', 'data'):
            path = paths[key]
            if os.path.isdir(paths[key]):
                lines.append('%s=%s' % (key, path))
        for ns in paths.get('namespace', ()):
            lines.append('namespace=%s' % ns)

        with codecs.open(shared_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return shared_path

    def get_distinfo_resource(self, path):
        if path not in DIST_FILES:
            raise DistlibException('invalid path for a dist-info file: '
                                   '%r at %r' % (path, self.path))
        finder = resources.finder_for_path(self.path)
        if finder is None:
            raise DistlibException('Unable to get a finder for %s' % self.path)
        return finder.find(path)

    def get_distinfo_file(self, path):
        """
        Returns a path located under the ``.dist-info`` directory. Returns a
        string representing the path.

        :parameter path: a ``'/'``-separated path relative to the
                         ``.dist-info`` directory or an absolute path;
                         If *path* is an absolute path and doesn't start
                         with the ``.dist-info`` directory path,
                         a :class:`DistlibException` is raised
        :type path: str
        :rtype: str
        """
        # Check if it is an absolute path  # XXX use relpath, add tests
        if path.find(os.sep) >= 0:
            # it's an absolute path?
            distinfo_dirname, path = path.split(os.sep)[-2:]
            if distinfo_dirname != self.path.split(os.sep)[-1]:
                raise DistlibException('dist-info file %r does not belong to the %r %s '
                                       'distribution' % (path, self.name, self.version))

        # The file must be relative
        if path not in DIST_FILES:
            raise DistlibException('invalid path for a dist-info file: '
                                   '%r at %r' % (path, self.path))

        return os.path.join(self.path, path)

    def list_distinfo_files(self):
        """
        Iterates over the ``RECORD`` entries and returns paths for each line if
        the path is pointing to a file located in the ``.dist-info`` directory
        or one of its subdirectories.

        :returns: iterator of paths
        """
        base = os.path.dirname(self.path)
        for path, checksum, size in self._get_records():
            # XXX add separator or use real relpath algo
            if not os.path.isabs(path):
                path = os.path.join(base, path)
            if path.startswith(self.path):
                yield path

    def __eq__(self, other):
        return (isinstance(other, InstalledDistribution) and self.path == other.path)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    __hash__ = object.__hash__


class EggInfoDistribution(BaseInstalledDistribution):
    """Created with the *path* of the ``.egg-info`` directory or file provided
    to the constructor. It reads the metadata contained in the file itself, or
    if the given path happens to be a directory, the metadata is read from the
    file ``PKG-INFO`` under that directory."""

    requested = True  # as we have no way of knowing, assume it was
    shared_locations = {}

    def __init__(self, path, env=None):

        def set_name_and_version(s, n, v):
            s.name = n
            s.key = n.lower()  # for case-insensitive comparisons
            s.version = v

        self.path = path
        self.dist_path = env
        if env and env._cache_enabled and path in env._cache_egg.path:
            metadata = env._cache_egg.path[path].metadata
            set_name_and_version(self, metadata.name, metadata.version)
        else:
            metadata = self._get_metadata(path)

            # Need to be set before caching
            set_name_and_version(self, metadata.name, metadata.version)

            if env and env._cache_enabled:
                env._cache_egg.add(self)
        super(EggInfoDistribution, self).__init__(metadata, path, env)

    def _get_metadata(self, path):
        requires = None

        def parse_requires_data(data):
            """Create a list of dependencies from a requires.txt file.

            *data*: the contents of a setuptools-produced requires.txt file.
            """
            reqs = []
            lines = data.splitlines()
            for line in lines:
                line = line.strip()
                # sectioned files have bare newlines (separating sections)
                if not line:  # pragma: no cover
                    continue
                if line.startswith('['):  # pragma: no cover
                    logger.warning('Unexpected line: quitting requirement scan: %r', line)
                    break
                r = parse_requirement(line)
                if not r:  # pragma: no cover
                    logger.warning('Not recognised as a requirement: %r', line)
                    continue
                if r.extras:  # pragma: no cover
                    logger.warning('extra requirements in requires.txt are '
                                   'not supported')
                if not r.constraints:
                    reqs.append(r.name)
                else:
                    cons = ', '.join('%s%s' % c for c in r.constraints)
                    reqs.append('%s (%s)' % (r.name, cons))
            return reqs

        def parse_requires_path(req_path):
            """Create a list of dependencies from a requires.txt file.

            *req_path*: the path to a setuptools-produced requires.txt file.
            """

            reqs = []
            try:
                with codecs.open(req_path, 'r', 'utf-8') as fp:
                    reqs = parse_requires_data(fp.read())
            except IOError:
                pass
            return reqs

        tl_path = tl_data = None
        if path.endswith('.egg'):
            if os.path.isdir(path):
                p = os.path.join(path, 'EGG-INFO')
                meta_path = os.path.join(p, 'PKG-INFO')
                metadata = Metadata(path=meta_path, scheme='legacy')
                req_path = os.path.join(p, 'requires.txt')
                tl_path = os.path.join(p, 'top_level.txt')
                requires = parse_requires_path(req_path)
            else:
                # FIXME handle the case where zipfile is not available
                zipf = zipimport.zipimporter(path)
                fileobj = StringIO(zipf.get_data('EGG-INFO/PKG-INFO').decode('utf8'))
                metadata = Metadata(fileobj=fileobj, scheme='legacy')
                try:
                    data = zipf.get_data('EGG-INFO/requires.txt')
                    tl_data = zipf.get_data('EGG-INFO/top_level.txt').decode('utf-8')
                    requires = parse_requires_data(data.decode('utf-8'))
                except IOError:
                    requires = None
        elif path.endswith('.egg-info'):
            if os.path.isdir(path):
                req_path = os.path.join(path, 'requires.txt')
                requires = parse_requires_path(req_path)
                path = os.path.join(path, 'PKG-INFO')
                tl_path = os.path.join(path, 'top_level.txt')
            metadata = Metadata(path=path, scheme='legacy')
        else:
            raise DistlibException('path must end with .egg-info or .egg, '
                                   'got %r' % path)

        if requires:
            metadata.add_requirements(requires)
        # look for top-level modules in top_level.txt, if present
        if tl_data is None:
            if tl_path is not None and os.path.exists(tl_path):
                with open(tl_path, 'rb') as f:
                    tl_data = f.read().decode('utf-8')
        if not tl_data:
            tl_data = []
        else:
            tl_data = tl_data.splitlines()
        self.modules = tl_data
        return metadata

    def __repr__(self):
        return '<EggInfoDistribution %r %s at %r>' % (self.name, self.version, self.path)

    def __str__(self):
        return "%s %s" % (self.name, self.version)

    def check_installed_files(self):
        """
        Checks that the hashes and sizes of the files in ``RECORD`` are
        matched by the files themselves. Returns a (possibly empty) list of
        mismatches. Each entry in the mismatch list will be a tuple consisting
        of the path, 'exists', 'size' or 'hash' according to what didn't match
        (existence is checked first, then size, then hash), the expected
        value and the actual value.
        """
        mismatches = []
        record_path = os.path.join(self.path, 'installed-files.txt')
        if os.path.exists(record_path):
            for path, _, _ in self.list_installed_files():
                if path == record_path:
                    continue
                if not os.path.exists(path):
                    mismatches.append((path, 'exists', True, False))
        return mismatches

    def list_installed_files(self):
        """
        Iterates over the ``installed-files.txt`` entries and returns a tuple
        ``(path, hash, size)`` for each line.

        :returns: a list of (path, hash, size)
        """

        def _md5(path):
            f = open(path, 'rb')
            try:
                content = f.read()
            finally:
                f.close()
            return hashlib.md5(content).hexdigest()

        def _size(path):
            return os.stat(path).st_size

        record_path = os.path.join(self.path, 'installed-files.txt')
        result = []
        if os.path.exists(record_path):
            with codecs.open(record_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    p = os.path.normpath(os.path.join(self.path, line))
                    # "./" is present as a marker between installed files
                    # and installation metadata files
                    if not os.path.exists(p):
                        logger.warning('Non-existent file: %s', p)
                        if p.endswith(('.pyc', '.pyo')):
                            continue
                        # otherwise fall through and fail
                    if not os.path.isdir(p):
                        result.append((p, _md5(p), _size(p)))
            result.append((record_path, None, None))
        return result

    def list_distinfo_files(self, absolute=False):
        """
        Iterates over the ``installed-files.txt`` entries and returns paths for
        each line if the path is pointing to a file located in the
        ``.egg-info`` directory or one of its subdirectories.

        :parameter absolute: If *absolute* is ``True``, each returned path is
                          transformed into a local absolute path. Otherwise the
                          raw value from ``installed-files.txt`` is returned.
        :type absolute: boolean
        :returns: iterator of paths
        """
        record_path = os.path.join(self.path, 'installed-files.txt')
        if os.path.exists(record_path):
            skip = True
            with codecs.open(record_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line == './':
                        skip = False
                        continue
                    if not skip:
                        p = os.path.normpath(os.path.join(self.path, line))
                        if p.startswith(self.path):
                            if absolute:
                                yield p
                            else:
                                yield line

    def __eq__(self, other):
        return (isinstance(other, EggInfoDistribution) and self.path == other.path)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    __hash__ = object.__hash__


new_dist_class = InstalledDistribution
old_dist_class = EggInfoDistribution


class DependencyGraph(object):
    """
    Represents a dependency graph between distributions.

    The dependency relationships are stored in an ``adjacency_list`` that maps
    distributions to a list of ``(other, label)`` tuples where  ``other``
    is a distribution and the edge is labeled with ``label`` (i.e. the version
    specifier, if such was provided). Also, for more efficient traversal, for
    every distribution ``x``, a list of predecessors is kept in
    ``reverse_list[x]``. An edge from distribution ``a`` to
    distribution ``b`` means that ``a`` depends on ``b``. If any missing
    dependencies are found, they are stored in ``missing``, which is a
    dictionary that maps distributions to a list of requirements that were not
    provided by any other distributions.
    """

    def __init__(self):
        self.adjacency_list = {}
        self.reverse_list = {}
        self.missing = {}

    def add_distribution(self, distribution):
        """Add the *distribution* to the graph.

        :type distribution: :class:`distutils2.database.InstalledDistribution`
                            or :class:`distutils2.database.EggInfoDistribution`
        """
        self.adjacency_list[distribution] = []
        self.reverse_list[distribution] = []
        # self.missing[distribution] = []

    def add_edge(self, x, y, label=None):
        """Add an edge from distribution *x* to distribution *y* with the given
        *label*.

        :type x: :class:`distutils2.database.InstalledDistribution` or
                 :class:`distutils2.database.EggInfoDistribution`
        :type y: :class:`distutils2.database.InstalledDistribution` or
                 :class:`distutils2.database.EggInfoDistribution`
        :type label: ``str`` or ``None``
        """
        self.adjacency_list[x].append((y, label))
        # multiple edges are allowed, so be careful
        if x not in self.reverse_list[y]:
            self.reverse_list[y].append(x)

    def add_missing(self, distribution, requirement):
        """
        Add a missing *requirement* for the given *distribution*.

        :type distribution: :class:`distutils2.database.InstalledDistribution`
                            or :class:`distutils2.database.EggInfoDistribution`
        :type requirement: ``str``
        """
        logger.debug('%s missing %r', distribution, requirement)
        self.missing.setdefault(distribution, []).append(requirement)

    def _repr_dist(self, dist):
        return '%s %s' % (dist.name, dist.version)

    def repr_node(self, dist, level=1):
        """Prints only a subgraph"""
        output = [self._repr_dist(dist)]
        for other, label in self.adjacency_list[dist]:
            dist = self._repr_dist(other)
            if label is not None:
                dist = '%s [%s]' % (dist, label)
            output.append('    ' * level + str(dist))
            suboutput = self.repr_node(other, level + 1)
            subs = suboutput.split('\n')
            output.extend(subs[1:])
        return '\n'.join(output)

    def to_dot(self, f, skip_disconnected=True):
        """Writes a DOT output for the graph to the provided file *f*.

        If *skip_disconnected* is set to ``True``, then all distributions
        that are not dependent on any other distribution are skipped.

        :type f: has to support ``file``-like operations
        :type skip_disconnected: ``bool``
        """
        disconnected = []

        f.write("digraph dependencies {\n")
        for dist, adjs in self.adjacency_list.items():
            if len(adjs) == 0 and not skip_disconnected:
                disconnected.append(dist)
            for other, label in adjs:
                if label is not None:
                    f.write('"%s" -> "%s" [label="%s"]\n' % (dist.name, other.name, label))
                else:
                    f.write('"%s" -> "%s"\n' % (dist.name, other.name))
        if not skip_disconnected and len(disconnected) > 0:
            f.write('subgraph disconnected {\n')
            f.write('label = "Disconnected"\n')
            f.write('bgcolor = red\n')

            for dist in disconnected:
                f.write('"%s"' % dist.name)
                f.write('\n')
            f.write('}\n')
        f.write('}\n')

    def topological_sort(self):
        """
        Perform a topological sort of the graph.
        :return: A tuple, the first element of which is a topologically sorted
                 list of distributions, and the second element of which is a
                 list of distributions that cannot be sorted because they have
                 circular dependencies and so form a cycle.
        """
        result = []
        # Make a shallow copy of the adjacency list
        alist = {}
        for k, v in self.adjacency_list.items():
            alist[k] = v[:]
        while True:
            # See what we can remove in this run
            to_remove = []
            for k, v in list(alist.items())[:]:
                if not v:
                    to_remove.append(k)
                    del alist[k]
            if not to_remove:
                # What's left in alist (if anything) is a cycle.
                break
            # Remove from the adjacency list of others
            for k, v in alist.items():
                alist[k] = [(d, r) for d, r in v if d not in to_remove]
            logger.debug('Moving to result: %s', ['%s (%s)' % (d.name, d.version) for d in to_remove])
            result.extend(to_remove)
        return result, list(alist.keys())

    def __repr__(self):
        """Representation of the graph"""
        output = []
        for dist, adjs in self.adjacency_list.items():
            output.append(self.repr_node(dist))
        return '\n'.join(output)


def make_graph(dists, scheme='default'):
    """Makes a dependency graph from the given distributions.

    :parameter dists: a list of distributions
    :type dists: list of :class:`distutils2.database.InstalledDistribution` and
                 :class:`distutils2.database.EggInfoDistribution` instances
    :rtype: a :class:`DependencyGraph` instance
    """
    scheme = get_scheme(scheme)
    graph = DependencyGraph()
    provided = {}  # maps names to lists of (version, dist) tuples

    # first, build the graph and find out what's provided
    for dist in dists:
        graph.add_distribution(dist)

        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Add to provided: %s, %s, %s', name, version, dist)
            provided.setdefault(name, []).append((version, dist))

    # now make the edges
    for dist in dists:
        requires = (dist.run_requires | dist.meta_requires | dist.build_requires | dist.dev_requires)
        for req in requires:
            try:
                matcher = scheme.matcher(req)
            except UnsupportedVersionError:
                # XXX compat-mode if cannot read the version
                logger.warning('could not read version %r - using name only', req)
                name = req.split()[0]
                matcher = scheme.matcher(name)

            name = matcher.key  # case-insensitive

            matched = False
            if name in provided:
                for version, provider in provided[name]:
                    try:
                        match = matcher.match(version)
                    except UnsupportedVersionError:
                        match = False

                    if match:
                        graph.add_edge(dist, provider, req)
                        matched = True
                        break
            if not matched:
                graph.add_missing(dist, req)
    return graph


def get_dependent_dists(dists, dist):
    """Recursively generate a list of distributions from *dists* that are
    dependent on *dist*.

    :param dists: a list of distributions
    :param dist: a distribution, member of *dists* for which we are interested
    """
    if dist not in dists:
        raise DistlibException('given distribution %r is not a member '
                               'of the list' % dist.name)
    graph = make_graph(dists)

    dep = [dist]  # dependent distributions
    todo = graph.reverse_list[dist]  # list of nodes we should inspect

    while todo:
        d = todo.pop()
        dep.append(d)
        for succ in graph.reverse_list[d]:
            if succ not in dep:
                todo.append(succ)

    dep.pop(0)  # remove dist from dep, was there to prevent infinite loops
    return dep


def get_required_dists(dists, dist):
    """Recursively generate a list of distributions from *dists* that are
    required by *dist*.

    :param dists: a list of distributions
    :param dist: a distribution, member of *dists* for which we are interested
                 in finding the dependencies.
    """
    if dist not in dists:
        raise DistlibException('given distribution %r is not a member '
                               'of the list' % dist.name)
    graph = make_graph(dists)

    req = set()  # required distributions
    todo = graph.adjacency_list[dist]  # list of nodes we should inspect
    seen = set(t[0] for t in todo)  # already added to todo

    while todo:
        d = todo.pop()[0]
        req.add(d)
        pred_list = graph.adjacency_list[d]
        for pred in pred_list:
            d = pred[0]
            if d not in req and d not in seen:
                seen.add(d)
                todo.append(pred)
    return req


def make_dist(name, version, **kwargs):
    """
    A convenience method for making a dist given just a name and version.
    """
    summary = kwargs.pop('summary', 'Placeholder for summary')
    md = Metadata(**kwargs)
    md.name = name
    md.version = version
    md.summary = summary or 'Placeholder for summary'
    return Distribution(md)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\database.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""PEP 376 implementation."""

from __future__ import unicode_literals

import base64
import codecs
import contextlib
import hashlib
import logging
import os
import posixpath
import sys
import zipimport

from . import DistlibException, resources
from .compat import StringIO
from .version import get_scheme, UnsupportedVersionError
from .metadata import (Metadata, METADATA_FILENAME, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME)
from .util import (parse_requirement, cached_property, parse_name_and_version, read_exports, write_exports, CSVReader,
                   CSVWriter)

__all__ = [
    'Distribution', 'BaseInstalledDistribution', 'InstalledDistribution', 'EggInfoDistribution', 'DistributionPath'
]

logger = logging.getLogger(__name__)

EXPORTS_FILENAME = 'pydist-exports.json'
COMMANDS_FILENAME = 'pydist-commands.json'

DIST_FILES = ('INSTALLER', METADATA_FILENAME, 'RECORD', 'REQUESTED', 'RESOURCES', EXPORTS_FILENAME, 'SHARED')

DISTINFO_EXT = '.dist-info'


class _Cache(object):
    """
    A simple cache mapping names and .dist-info paths to distributions
    """

    def __init__(self):
        """
        Initialise an instance. There is normally one for each DistributionPath.
        """
        self.name = {}
        self.path = {}
        self.generated = False

    def clear(self):
        """
        Clear the cache, setting it to its initial state.
        """
        self.name.clear()
        self.path.clear()
        self.generated = False

    def add(self, dist):
        """
        Add a distribution to the cache.
        :param dist: The distribution to add.
        """
        if dist.path not in self.path:
            self.path[dist.path] = dist
            self.name.setdefault(dist.key, []).append(dist)


class DistributionPath(object):
    """
    Represents a set of distributions installed on a path (typically sys.path).
    """

    def __init__(self, path=None, include_egg=False):
        """
        Create an instance from a path, optionally including legacy (distutils/
        setuptools/distribute) distributions.
        :param path: The path to use, as a list of directories. If not specified,
                     sys.path is used.
        :param include_egg: If True, this instance will look for and return legacy
                            distributions as well as those based on PEP 376.
        """
        if path is None:
            path = sys.path
        self.path = path
        self._include_dist = True
        self._include_egg = include_egg

        self._cache = _Cache()
        self._cache_egg = _Cache()
        self._cache_enabled = True
        self._scheme = get_scheme('default')

    def _get_cache_enabled(self):
        return self._cache_enabled

    def _set_cache_enabled(self, value):
        self._cache_enabled = value

    cache_enabled = property(_get_cache_enabled, _set_cache_enabled)

    def clear_cache(self):
        """
        Clears the internal cache.
        """
        self._cache.clear()
        self._cache_egg.clear()

    def _yield_distributions(self):
        """
        Yield .dist-info and/or .egg(-info) distributions.
        """
        # We need to check if we've seen some resources already, because on
        # some Linux systems (e.g. some Debian/Ubuntu variants) there are
        # symlinks which alias other files in the environment.
        seen = set()
        for path in self.path:
            finder = resources.finder_for_path(path)
            if finder is None:
                continue
            r = finder.find('')
            if not r or not r.is_container:
                continue
            rset = sorted(r.resources)
            for entry in rset:
                r = finder.find(entry)
                if not r or r.path in seen:
                    continue
                try:
                    if self._include_dist and entry.endswith(DISTINFO_EXT):
                        possible_filenames = [METADATA_FILENAME, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME]
                        for metadata_filename in possible_filenames:
                            metadata_path = posixpath.join(entry, metadata_filename)
                            pydist = finder.find(metadata_path)
                            if pydist:
                                break
                        else:
                            continue

                        with contextlib.closing(pydist.as_stream()) as stream:
                            metadata = Metadata(fileobj=stream, scheme='legacy')
                        logger.debug('Found %s', r.path)
                        seen.add(r.path)
                        yield new_dist_class(r.path, metadata=metadata, env=self)
                    elif self._include_egg and entry.endswith(('.egg-info', '.egg')):
                        logger.debug('Found %s', r.path)
                        seen.add(r.path)
                        yield old_dist_class(r.path, self)
                except Exception as e:
                    msg = 'Unable to read distribution at %s, perhaps due to bad metadata: %s'
                    logger.warning(msg, r.path, e)
                    import warnings
                    warnings.warn(msg % (r.path, e), stacklevel=2)

    def _generate_cache(self):
        """
        Scan the path for distributions and populate the cache with
        those that are found.
        """
        gen_dist = not self._cache.generated
        gen_egg = self._include_egg and not self._cache_egg.generated
        if gen_dist or gen_egg:
            for dist in self._yield_distributions():
                if isinstance(dist, InstalledDistribution):
                    self._cache.add(dist)
                else:
                    self._cache_egg.add(dist)

            if gen_dist:
                self._cache.generated = True
            if gen_egg:
                self._cache_egg.generated = True

    @classmethod
    def distinfo_dirname(cls, name, version):
        """
        The *name* and *version* parameters are converted into their
        filename-escaped form, i.e. any ``'-'`` characters are replaced
        with ``'_'`` other than the one in ``'dist-info'`` and the one
        separating the name from the version number.

        :parameter name: is converted to a standard distribution name by replacing
                         any runs of non- alphanumeric characters with a single
                         ``'-'``.
        :type name: string
        :parameter version: is converted to a standard version string. Spaces
                            become dots, and all other non-alphanumeric characters
                            (except dots) become dashes, with runs of multiple
                            dashes condensed to a single dash.
        :type version: string
        :returns: directory name
        :rtype: string"""
        name = name.replace('-', '_')
        return '-'.join([name, version]) + DISTINFO_EXT

    def get_distributions(self):
        """
        Provides an iterator that looks for distributions and returns
        :class:`InstalledDistribution` or
        :class:`EggInfoDistribution` instances for each one of them.

        :rtype: iterator of :class:`InstalledDistribution` and
                :class:`EggInfoDistribution` instances
        """
        if not self._cache_enabled:
            for dist in self._yield_distributions():
                yield dist
        else:
            self._generate_cache()

            for dist in self._cache.path.values():
                yield dist

            if self._include_egg:
                for dist in self._cache_egg.path.values():
                    yield dist

    def get_distribution(self, name):
        """
        Looks for a named distribution on the path.

        This function only returns the first result found, as no more than one
        value is expected. If nothing is found, ``None`` is returned.

        :rtype: :class:`InstalledDistribution`, :class:`EggInfoDistribution`
                or ``None``
        """
        result = None
        name = name.lower()
        if not self._cache_enabled:
            for dist in self._yield_distributions():
                if dist.key == name:
                    result = dist
                    break
        else:
            self._generate_cache()

            if name in self._cache.name:
                result = self._cache.name[name][0]
            elif self._include_egg and name in self._cache_egg.name:
                result = self._cache_egg.name[name][0]
        return result

    def provides_distribution(self, name, version=None):
        """
        Iterates over all distributions to find which distributions provide *name*.
        If a *version* is provided, it will be used to filter the results.

        This function only returns the first result found, since no more than
        one values are expected. If the directory is not found, returns ``None``.

        :parameter version: a version specifier that indicates the version
                            required, conforming to the format in ``PEP-345``

        :type name: string
        :type version: string
        """
        matcher = None
        if version is not None:
            try:
                matcher = self._scheme.matcher('%s (%s)' % (name, version))
            except ValueError:
                raise DistlibException('invalid name or version: %r, %r' % (name, version))

        for dist in self.get_distributions():
            # We hit a problem on Travis where enum34 was installed and doesn't
            # have a provides attribute ...
            if not hasattr(dist, 'provides'):
                logger.debug('No "provides": %s', dist)
            else:
                provided = dist.provides

                for p in provided:
                    p_name, p_ver = parse_name_and_version(p)
                    if matcher is None:
                        if p_name == name:
                            yield dist
                            break
                    else:
                        if p_name == name and matcher.match(p_ver):
                            yield dist
                            break

    def get_file_path(self, name, relative_path):
        """
        Return the path to a resource file.
        """
        dist = self.get_distribution(name)
        if dist is None:
            raise LookupError('no distribution named %r found' % name)
        return dist.get_resource_path(relative_path)

    def get_exported_entries(self, category, name=None):
        """
        Return all of the exported entries in a particular category.

        :param category: The category to search for entries.
        :param name: If specified, only entries with that name are returned.
        """
        for dist in self.get_distributions():
            r = dist.exports
            if category in r:
                d = r[category]
                if name is not None:
                    if name in d:
                        yield d[name]
                else:
                    for v in d.values():
                        yield v


class Distribution(object):
    """
    A base class for distributions, whether installed or from indexes.
    Either way, it must have some metadata, so that's all that's needed
    for construction.
    """

    build_time_dependency = False
    """
    Set to True if it's known to be only a build-time dependency (i.e.
    not needed after installation).
    """

    requested = False
    """A boolean that indicates whether the ``REQUESTED`` metadata file is
    present (in other words, whether the package was installed by user
    request or it was installed as a dependency)."""

    def __init__(self, metadata):
        """
        Initialise an instance.
        :param metadata: The instance of :class:`Metadata` describing this
        distribution.
        """
        self.metadata = metadata
        self.name = metadata.name
        self.key = self.name.lower()  # for case-insensitive comparisons
        self.version = metadata.version
        self.locator = None
        self.digest = None
        self.extras = None  # additional features requested
        self.context = None  # environment marker overrides
        self.download_urls = set()
        self.digests = {}

    @property
    def source_url(self):
        """
        The source archive download URL for this distribution.
        """
        return self.metadata.source_url

    download_url = source_url  # Backward compatibility

    @property
    def name_and_version(self):
        """
        A utility property which displays the name and version in parentheses.
        """
        return '%s (%s)' % (self.name, self.version)

    @property
    def provides(self):
        """
        A set of distribution names and versions provided by this distribution.
        :return: A set of "name (version)" strings.
        """
        plist = self.metadata.provides
        s = '%s (%s)' % (self.name, self.version)
        if s not in plist:
            plist.append(s)
        return plist

    def _get_requirements(self, req_attr):
        md = self.metadata
        reqts = getattr(md, req_attr)
        logger.debug('%s: got requirements %r from metadata: %r', self.name, req_attr, reqts)
        return set(md.get_requirements(reqts, extras=self.extras, env=self.context))

    @property
    def run_requires(self):
        return self._get_requirements('run_requires')

    @property
    def meta_requires(self):
        return self._get_requirements('meta_requires')

    @property
    def build_requires(self):
        return self._get_requirements('build_requires')

    @property
    def test_requires(self):
        return self._get_requirements('test_requires')

    @property
    def dev_requires(self):
        return self._get_requirements('dev_requires')

    def matches_requirement(self, req):
        """
        Say if this instance matches (fulfills) a requirement.
        :param req: The requirement to match.
        :rtype req: str
        :return: True if it matches, else False.
        """
        # Requirement may contain extras - parse to lose those
        # from what's passed to the matcher
        r = parse_requirement(req)
        scheme = get_scheme(self.metadata.scheme)
        try:
            matcher = scheme.matcher(r.requirement)
        except UnsupportedVersionError:
            # XXX compat-mode if cannot read the version
            logger.warning('could not read version %r - using name only', req)
            name = req.split()[0]
            matcher = scheme.matcher(name)

        name = matcher.key  # case-insensitive

        result = False
        for p in self.provides:
            p_name, p_ver = parse_name_and_version(p)
            if p_name != name:
                continue
            try:
                result = matcher.match(p_ver)
                break
            except UnsupportedVersionError:
                pass
        return result

    def __repr__(self):
        """
        Return a textual representation of this instance,
        """
        if self.source_url:
            suffix = ' [%s]' % self.source_url
        else:
            suffix = ''
        return '<Distribution %s (%s)%s>' % (self.name, self.version, suffix)

    def __eq__(self, other):
        """
        See if this distribution is the same as another.
        :param other: The distribution to compare with. To be equal to one
                      another. distributions must have the same type, name,
                      version and source_url.
        :return: True if it is the same, else False.
        """
        if type(other) is not type(self):
            result = False
        else:
            result = (self.name == other.name and self.version == other.version and self.source_url == other.source_url)
        return result

    def __hash__(self):
        """
        Compute hash in a way which matches the equality test.
        """
        return hash(self.name) + hash(self.version) + hash(self.source_url)


class BaseInstalledDistribution(Distribution):
    """
    This is the base class for installed distributions (whether PEP 376 or
    legacy).
    """

    hasher = None

    def __init__(self, metadata, path, env=None):
        """
        Initialise an instance.
        :param metadata: An instance of :class:`Metadata` which describes the
                         distribution. This will normally have been initialised
                         from a metadata file in the ``path``.
        :param path:     The path of the ``.dist-info`` or ``.egg-info``
                         directory for the distribution.
        :param env:      This is normally the :class:`DistributionPath`
                         instance where this distribution was found.
        """
        super(BaseInstalledDistribution, self).__init__(metadata)
        self.path = path
        self.dist_path = env

    def get_hash(self, data, hasher=None):
        """
        Get the hash of some data, using a particular hash algorithm, if
        specified.

        :param data: The data to be hashed.
        :type data: bytes
        :param hasher: The name of a hash implementation, supported by hashlib,
                       or ``None``. Examples of valid values are ``'sha1'``,
                       ``'sha224'``, ``'sha384'``, '``sha256'``, ``'md5'`` and
                       ``'sha512'``. If no hasher is specified, the ``hasher``
                       attribute of the :class:`InstalledDistribution` instance
                       is used. If the hasher is determined to be ``None``, MD5
                       is used as the hashing algorithm.
        :returns: The hash of the data. If a hasher was explicitly specified,
                  the returned hash will be prefixed with the specified hasher
                  followed by '='.
        :rtype: str
        """
        if hasher is None:
            hasher = self.hasher
        if hasher is None:
            hasher = hashlib.md5
            prefix = ''
        else:
            hasher = getattr(hashlib, hasher)
            prefix = '%s=' % self.hasher
        digest = hasher(data).digest()
        digest = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
        return '%s%s' % (prefix, digest)


class InstalledDistribution(BaseInstalledDistribution):
    """
    Created with the *path* of the ``.dist-info`` directory provided to the
    constructor. It reads the metadata contained in ``pydist.json`` when it is
    instantiated., or uses a passed in Metadata instance (useful for when
    dry-run mode is being used).
    """

    hasher = 'sha256'

    def __init__(self, path, metadata=None, env=None):
        self.modules = []
        self.finder = finder = resources.finder_for_path(path)
        if finder is None:
            raise ValueError('finder unavailable for %s' % path)
        if env and env._cache_enabled and path in env._cache.path:
            metadata = env._cache.path[path].metadata
        elif metadata is None:
            r = finder.find(METADATA_FILENAME)
            # Temporary - for Wheel 0.23 support
            if r is None:
                r = finder.find(WHEEL_METADATA_FILENAME)
            # Temporary - for legacy support
            if r is None:
                r = finder.find(LEGACY_METADATA_FILENAME)
            if r is None:
                raise ValueError('no %s found in %s' % (METADATA_FILENAME, path))
            with contextlib.closing(r.as_stream()) as stream:
                metadata = Metadata(fileobj=stream, scheme='legacy')

        super(InstalledDistribution, self).__init__(metadata, path, env)

        if env and env._cache_enabled:
            env._cache.add(self)

        r = finder.find('REQUESTED')
        self.requested = r is not None
        p = os.path.join(path, 'top_level.txt')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                data = f.read().decode('utf-8')
            self.modules = data.splitlines()

    def __repr__(self):
        return '<InstalledDistribution %r %s at %r>' % (self.name, self.version, self.path)

    def __str__(self):
        return "%s %s" % (self.name, self.version)

    def _get_records(self):
        """
        Get the list of installed files for the distribution
        :return: A list of tuples of path, hash and size. Note that hash and
                 size might be ``None`` for some entries. The path is exactly
                 as stored in the file (which is as in PEP 376).
        """
        results = []
        r = self.get_distinfo_resource('RECORD')
        with contextlib.closing(r.as_stream()) as stream:
            with CSVReader(stream=stream) as record_reader:
                # Base location is parent dir of .dist-info dir
                # base_location = os.path.dirname(self.path)
                # base_location = os.path.abspath(base_location)
                for row in record_reader:
                    missing = [None for i in range(len(row), 3)]
                    path, checksum, size = row + missing
                    # if not os.path.isabs(path):
                    #     path = path.replace('/', os.sep)
                    #     path = os.path.join(base_location, path)
                    results.append((path, checksum, size))
        return results

    @cached_property
    def exports(self):
        """
        Return the information exported by this distribution.
        :return: A dictionary of exports, mapping an export category to a dict
                 of :class:`ExportEntry` instances describing the individual
                 export entries, and keyed by name.
        """
        result = {}
        r = self.get_distinfo_resource(EXPORTS_FILENAME)
        if r:
            result = self.read_exports()
        return result

    def read_exports(self):
        """
        Read exports data from a file in .ini format.

        :return: A dictionary of exports, mapping an export category to a list
                 of :class:`ExportEntry` instances describing the individual
                 export entries.
        """
        result = {}
        r = self.get_distinfo_resource(EXPORTS_FILENAME)
        if r:
            with contextlib.closing(r.as_stream()) as stream:
                result = read_exports(stream)
        return result

    def write_exports(self, exports):
        """
        Write a dictionary of exports to a file in .ini format.
        :param exports: A dictionary of exports, mapping an export category to
                        a list of :class:`ExportEntry` instances describing the
                        individual export entries.
        """
        rf = self.get_distinfo_file(EXPORTS_FILENAME)
        with open(rf, 'w') as f:
            write_exports(exports, f)

    def get_resource_path(self, relative_path):
        """
        NOTE: This API may change in the future.

        Return the absolute path to a resource file with the given relative
        path.

        :param relative_path: The path, relative to .dist-info, of the resource
                              of interest.
        :return: The absolute path where the resource is to be found.
        """
        r = self.get_distinfo_resource('RESOURCES')
        with contextlib.closing(r.as_stream()) as stream:
            with CSVReader(stream=stream) as resources_reader:
                for relative, destination in resources_reader:
                    if relative == relative_path:
                        return destination
        raise KeyError('no resource file with relative path %r '
                       'is installed' % relative_path)

    def list_installed_files(self):
        """
        Iterates over the ``RECORD`` entries and returns a tuple
        ``(path, hash, size)`` for each line.

        :returns: iterator of (path, hash, size)
        """
        for result in self._get_records():
            yield result

    def write_installed_files(self, paths, prefix, dry_run=False):
        """
        Writes the ``RECORD`` file, using the ``paths`` iterable passed in. Any
        existing ``RECORD`` file is silently overwritten.

        prefix is used to determine when to write absolute paths.
        """
        prefix = os.path.join(prefix, '')
        base = os.path.dirname(self.path)
        base_under_prefix = base.startswith(prefix)
        base = os.path.join(base, '')
        record_path = self.get_distinfo_file('RECORD')
        logger.info('creating %s', record_path)
        if dry_run:
            return None
        with CSVWriter(record_path) as writer:
            for path in paths:
                if os.path.isdir(path) or path.endswith(('.pyc', '.pyo')):
                    # do not put size and hash, as in PEP-376
                    hash_value = size = ''
                else:
                    size = '%d' % os.path.getsize(path)
                    with open(path, 'rb') as fp:
                        hash_value = self.get_hash(fp.read())
                if path.startswith(base) or (base_under_prefix and path.startswith(prefix)):
                    path = os.path.relpath(path, base)
                writer.writerow((path, hash_value, size))

            # add the RECORD file itself
            if record_path.startswith(base):
                record_path = os.path.relpath(record_path, base)
            writer.writerow((record_path, '', ''))
        return record_path

    def check_installed_files(self):
        """
        Checks that the hashes and sizes of the files in ``RECORD`` are
        matched by the files themselves. Returns a (possibly empty) list of
        mismatches. Each entry in the mismatch list will be a tuple consisting
        of the path, 'exists', 'size' or 'hash' according to what didn't match
        (existence is checked first, then size, then hash), the expected
        value and the actual value.
        """
        mismatches = []
        base = os.path.dirname(self.path)
        record_path = self.get_distinfo_file('RECORD')
        for path, hash_value, size in self.list_installed_files():
            if not os.path.isabs(path):
                path = os.path.join(base, path)
            if path == record_path:
                continue
            if not os.path.exists(path):
                mismatches.append((path, 'exists', True, False))
            elif os.path.isfile(path):
                actual_size = str(os.path.getsize(path))
                if size and actual_size != size:
                    mismatches.append((path, 'size', size, actual_size))
                elif hash_value:
                    if '=' in hash_value:
                        hasher = hash_value.split('=', 1)[0]
                    else:
                        hasher = None

                    with open(path, 'rb') as f:
                        actual_hash = self.get_hash(f.read(), hasher)
                        if actual_hash != hash_value:
                            mismatches.append((path, 'hash', hash_value, actual_hash))
        return mismatches

    @cached_property
    def shared_locations(self):
        """
        A dictionary of shared locations whose keys are in the set 'prefix',
        'purelib', 'platlib', 'scripts', 'headers', 'data' and 'namespace'.
        The corresponding value is the absolute path of that category for
        this distribution, and takes into account any paths selected by the
        user at installation time (e.g. via command-line arguments). In the
        case of the 'namespace' key, this would be a list of absolute paths
        for the roots of namespace packages in this distribution.

        The first time this property is accessed, the relevant information is
        read from the SHARED file in the .dist-info directory.
        """
        result = {}
        shared_path = os.path.join(self.path, 'SHARED')
        if os.path.isfile(shared_path):
            with codecs.open(shared_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            for line in lines:
                key, value = line.split('=', 1)
                if key == 'namespace':
                    result.setdefault(key, []).append(value)
                else:
                    result[key] = value
        return result

    def write_shared_locations(self, paths, dry_run=False):
        """
        Write shared location information to the SHARED file in .dist-info.
        :param paths: A dictionary as described in the documentation for
        :meth:`shared_locations`.
        :param dry_run: If True, the action is logged but no file is actually
                        written.
        :return: The path of the file written to.
        """
        shared_path = os.path.join(self.path, 'SHARED')
        logger.info('creating %s', shared_path)
        if dry_run:
            return None
        lines = []
        for key in ('prefix', 'lib', 'headers', 'scripts', 'data'):
            path = paths[key]
            if os.path.isdir(paths[key]):
                lines.append('%s=%s' % (key, path))
        for ns in paths.get('namespace', ()):
            lines.append('namespace=%s' % ns)

        with codecs.open(shared_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return shared_path

    def get_distinfo_resource(self, path):
        if path not in DIST_FILES:
            raise DistlibException('invalid path for a dist-info file: '
                                   '%r at %r' % (path, self.path))
        finder = resources.finder_for_path(self.path)
        if finder is None:
            raise DistlibException('Unable to get a finder for %s' % self.path)
        return finder.find(path)

    def get_distinfo_file(self, path):
        """
        Returns a path located under the ``.dist-info`` directory. Returns a
        string representing the path.

        :parameter path: a ``'/'``-separated path relative to the
                         ``.dist-info`` directory or an absolute path;
                         If *path* is an absolute path and doesn't start
                         with the ``.dist-info`` directory path,
                         a :class:`DistlibException` is raised
        :type path: str
        :rtype: str
        """
        # Check if it is an absolute path  # XXX use relpath, add tests
        if path.find(os.sep) >= 0:
            # it's an absolute path?
            distinfo_dirname, path = path.split(os.sep)[-2:]
            if distinfo_dirname != self.path.split(os.sep)[-1]:
                raise DistlibException('dist-info file %r does not belong to the %r %s '
                                       'distribution' % (path, self.name, self.version))

        # The file must be relative
        if path not in DIST_FILES:
            raise DistlibException('invalid path for a dist-info file: '
                                   '%r at %r' % (path, self.path))

        return os.path.join(self.path, path)

    def list_distinfo_files(self):
        """
        Iterates over the ``RECORD`` entries and returns paths for each line if
        the path is pointing to a file located in the ``.dist-info`` directory
        or one of its subdirectories.

        :returns: iterator of paths
        """
        base = os.path.dirname(self.path)
        for path, checksum, size in self._get_records():
            # XXX add separator or use real relpath algo
            if not os.path.isabs(path):
                path = os.path.join(base, path)
            if path.startswith(self.path):
                yield path

    def __eq__(self, other):
        return (isinstance(other, InstalledDistribution) and self.path == other.path)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    __hash__ = object.__hash__


class EggInfoDistribution(BaseInstalledDistribution):
    """Created with the *path* of the ``.egg-info`` directory or file provided
    to the constructor. It reads the metadata contained in the file itself, or
    if the given path happens to be a directory, the metadata is read from the
    file ``PKG-INFO`` under that directory."""

    requested = True  # as we have no way of knowing, assume it was
    shared_locations = {}

    def __init__(self, path, env=None):

        def set_name_and_version(s, n, v):
            s.name = n
            s.key = n.lower()  # for case-insensitive comparisons
            s.version = v

        self.path = path
        self.dist_path = env
        if env and env._cache_enabled and path in env._cache_egg.path:
            metadata = env._cache_egg.path[path].metadata
            set_name_and_version(self, metadata.name, metadata.version)
        else:
            metadata = self._get_metadata(path)

            # Need to be set before caching
            set_name_and_version(self, metadata.name, metadata.version)

            if env and env._cache_enabled:
                env._cache_egg.add(self)
        super(EggInfoDistribution, self).__init__(metadata, path, env)

    def _get_metadata(self, path):
        requires = None

        def parse_requires_data(data):
            """Create a list of dependencies from a requires.txt file.

            *data*: the contents of a setuptools-produced requires.txt file.
            """
            reqs = []
            lines = data.splitlines()
            for line in lines:
                line = line.strip()
                # sectioned files have bare newlines (separating sections)
                if not line:  # pragma: no cover
                    continue
                if line.startswith('['):  # pragma: no cover
                    logger.warning('Unexpected line: quitting requirement scan: %r', line)
                    break
                r = parse_requirement(line)
                if not r:  # pragma: no cover
                    logger.warning('Not recognised as a requirement: %r', line)
                    continue
                if r.extras:  # pragma: no cover
                    logger.warning('extra requirements in requires.txt are '
                                   'not supported')
                if not r.constraints:
                    reqs.append(r.name)
                else:
                    cons = ', '.join('%s%s' % c for c in r.constraints)
                    reqs.append('%s (%s)' % (r.name, cons))
            return reqs

        def parse_requires_path(req_path):
            """Create a list of dependencies from a requires.txt file.

            *req_path*: the path to a setuptools-produced requires.txt file.
            """

            reqs = []
            try:
                with codecs.open(req_path, 'r', 'utf-8') as fp:
                    reqs = parse_requires_data(fp.read())
            except IOError:
                pass
            return reqs

        tl_path = tl_data = None
        if path.endswith('.egg'):
            if os.path.isdir(path):
                p = os.path.join(path, 'EGG-INFO')
                meta_path = os.path.join(p, 'PKG-INFO')
                metadata = Metadata(path=meta_path, scheme='legacy')
                req_path = os.path.join(p, 'requires.txt')
                tl_path = os.path.join(p, 'top_level.txt')
                requires = parse_requires_path(req_path)
            else:
                # FIXME handle the case where zipfile is not available
                zipf = zipimport.zipimporter(path)
                fileobj = StringIO(zipf.get_data('EGG-INFO/PKG-INFO').decode('utf8'))
                metadata = Metadata(fileobj=fileobj, scheme='legacy')
                try:
                    data = zipf.get_data('EGG-INFO/requires.txt')
                    tl_data = zipf.get_data('EGG-INFO/top_level.txt').decode('utf-8')
                    requires = parse_requires_data(data.decode('utf-8'))
                except IOError:
                    requires = None
        elif path.endswith('.egg-info'):
            if os.path.isdir(path):
                req_path = os.path.join(path, 'requires.txt')
                requires = parse_requires_path(req_path)
                path = os.path.join(path, 'PKG-INFO')
                tl_path = os.path.join(path, 'top_level.txt')
            metadata = Metadata(path=path, scheme='legacy')
        else:
            raise DistlibException('path must end with .egg-info or .egg, '
                                   'got %r' % path)

        if requires:
            metadata.add_requirements(requires)
        # look for top-level modules in top_level.txt, if present
        if tl_data is None:
            if tl_path is not None and os.path.exists(tl_path):
                with open(tl_path, 'rb') as f:
                    tl_data = f.read().decode('utf-8')
        if not tl_data:
            tl_data = []
        else:
            tl_data = tl_data.splitlines()
        self.modules = tl_data
        return metadata

    def __repr__(self):
        return '<EggInfoDistribution %r %s at %r>' % (self.name, self.version, self.path)

    def __str__(self):
        return "%s %s" % (self.name, self.version)

    def check_installed_files(self):
        """
        Checks that the hashes and sizes of the files in ``RECORD`` are
        matched by the files themselves. Returns a (possibly empty) list of
        mismatches. Each entry in the mismatch list will be a tuple consisting
        of the path, 'exists', 'size' or 'hash' according to what didn't match
        (existence is checked first, then size, then hash), the expected
        value and the actual value.
        """
        mismatches = []
        record_path = os.path.join(self.path, 'installed-files.txt')
        if os.path.exists(record_path):
            for path, _, _ in self.list_installed_files():
                if path == record_path:
                    continue
                if not os.path.exists(path):
                    mismatches.append((path, 'exists', True, False))
        return mismatches

    def list_installed_files(self):
        """
        Iterates over the ``installed-files.txt`` entries and returns a tuple
        ``(path, hash, size)`` for each line.

        :returns: a list of (path, hash, size)
        """

        def _md5(path):
            f = open(path, 'rb')
            try:
                content = f.read()
            finally:
                f.close()
            return hashlib.md5(content).hexdigest()

        def _size(path):
            return os.stat(path).st_size

        record_path = os.path.join(self.path, 'installed-files.txt')
        result = []
        if os.path.exists(record_path):
            with codecs.open(record_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    p = os.path.normpath(os.path.join(self.path, line))
                    # "./" is present as a marker between installed files
                    # and installation metadata files
                    if not os.path.exists(p):
                        logger.warning('Non-existent file: %s', p)
                        if p.endswith(('.pyc', '.pyo')):
                            continue
                        # otherwise fall through and fail
                    if not os.path.isdir(p):
                        result.append((p, _md5(p), _size(p)))
            result.append((record_path, None, None))
        return result

    def list_distinfo_files(self, absolute=False):
        """
        Iterates over the ``installed-files.txt`` entries and returns paths for
        each line if the path is pointing to a file located in the
        ``.egg-info`` directory or one of its subdirectories.

        :parameter absolute: If *absolute* is ``True``, each returned path is
                          transformed into a local absolute path. Otherwise the
                          raw value from ``installed-files.txt`` is returned.
        :type absolute: boolean
        :returns: iterator of paths
        """
        record_path = os.path.join(self.path, 'installed-files.txt')
        if os.path.exists(record_path):
            skip = True
            with codecs.open(record_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line == './':
                        skip = False
                        continue
                    if not skip:
                        p = os.path.normpath(os.path.join(self.path, line))
                        if p.startswith(self.path):
                            if absolute:
                                yield p
                            else:
                                yield line

    def __eq__(self, other):
        return (isinstance(other, EggInfoDistribution) and self.path == other.path)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    __hash__ = object.__hash__


new_dist_class = InstalledDistribution
old_dist_class = EggInfoDistribution


class DependencyGraph(object):
    """
    Represents a dependency graph between distributions.

    The dependency relationships are stored in an ``adjacency_list`` that maps
    distributions to a list of ``(other, label)`` tuples where  ``other``
    is a distribution and the edge is labeled with ``label`` (i.e. the version
    specifier, if such was provided). Also, for more efficient traversal, for
    every distribution ``x``, a list of predecessors is kept in
    ``reverse_list[x]``. An edge from distribution ``a`` to
    distribution ``b`` means that ``a`` depends on ``b``. If any missing
    dependencies are found, they are stored in ``missing``, which is a
    dictionary that maps distributions to a list of requirements that were not
    provided by any other distributions.
    """

    def __init__(self):
        self.adjacency_list = {}
        self.reverse_list = {}
        self.missing = {}

    def add_distribution(self, distribution):
        """Add the *distribution* to the graph.

        :type distribution: :class:`distutils2.database.InstalledDistribution`
                            or :class:`distutils2.database.EggInfoDistribution`
        """
        self.adjacency_list[distribution] = []
        self.reverse_list[distribution] = []
        # self.missing[distribution] = []

    def add_edge(self, x, y, label=None):
        """Add an edge from distribution *x* to distribution *y* with the given
        *label*.

        :type x: :class:`distutils2.database.InstalledDistribution` or
                 :class:`distutils2.database.EggInfoDistribution`
        :type y: :class:`distutils2.database.InstalledDistribution` or
                 :class:`distutils2.database.EggInfoDistribution`
        :type label: ``str`` or ``None``
        """
        self.adjacency_list[x].append((y, label))
        # multiple edges are allowed, so be careful
        if x not in self.reverse_list[y]:
            self.reverse_list[y].append(x)

    def add_missing(self, distribution, requirement):
        """
        Add a missing *requirement* for the given *distribution*.

        :type distribution: :class:`distutils2.database.InstalledDistribution`
                            or :class:`distutils2.database.EggInfoDistribution`
        :type requirement: ``str``
        """
        logger.debug('%s missing %r', distribution, requirement)
        self.missing.setdefault(distribution, []).append(requirement)

    def _repr_dist(self, dist):
        return '%s %s' % (dist.name, dist.version)

    def repr_node(self, dist, level=1):
        """Prints only a subgraph"""
        output = [self._repr_dist(dist)]
        for other, label in self.adjacency_list[dist]:
            dist = self._repr_dist(other)
            if label is not None:
                dist = '%s [%s]' % (dist, label)
            output.append('    ' * level + str(dist))
            suboutput = self.repr_node(other, level + 1)
            subs = suboutput.split('\n')
            output.extend(subs[1:])
        return '\n'.join(output)

    def to_dot(self, f, skip_disconnected=True):
        """Writes a DOT output for the graph to the provided file *f*.

        If *skip_disconnected* is set to ``True``, then all distributions
        that are not dependent on any other distribution are skipped.

        :type f: has to support ``file``-like operations
        :type skip_disconnected: ``bool``
        """
        disconnected = []

        f.write("digraph dependencies {\n")
        for dist, adjs in self.adjacency_list.items():
            if len(adjs) == 0 and not skip_disconnected:
                disconnected.append(dist)
            for other, label in adjs:
                if label is not None:
                    f.write('"%s" -> "%s" [label="%s"]\n' % (dist.name, other.name, label))
                else:
                    f.write('"%s" -> "%s"\n' % (dist.name, other.name))
        if not skip_disconnected and len(disconnected) > 0:
            f.write('subgraph disconnected {\n')
            f.write('label = "Disconnected"\n')
            f.write('bgcolor = red\n')

            for dist in disconnected:
                f.write('"%s"' % dist.name)
                f.write('\n')
            f.write('}\n')
        f.write('}\n')

    def topological_sort(self):
        """
        Perform a topological sort of the graph.
        :return: A tuple, the first element of which is a topologically sorted
                 list of distributions, and the second element of which is a
                 list of distributions that cannot be sorted because they have
                 circular dependencies and so form a cycle.
        """
        result = []
        # Make a shallow copy of the adjacency list
        alist = {}
        for k, v in self.adjacency_list.items():
            alist[k] = v[:]
        while True:
            # See what we can remove in this run
            to_remove = []
            for k, v in list(alist.items())[:]:
                if not v:
                    to_remove.append(k)
                    del alist[k]
            if not to_remove:
                # What's left in alist (if anything) is a cycle.
                break
            # Remove from the adjacency list of others
            for k, v in alist.items():
                alist[k] = [(d, r) for d, r in v if d not in to_remove]
            logger.debug('Moving to result: %s', ['%s (%s)' % (d.name, d.version) for d in to_remove])
            result.extend(to_remove)
        return result, list(alist.keys())

    def __repr__(self):
        """Representation of the graph"""
        output = []
        for dist, adjs in self.adjacency_list.items():
            output.append(self.repr_node(dist))
        return '\n'.join(output)


def make_graph(dists, scheme='default'):
    """Makes a dependency graph from the given distributions.

    :parameter dists: a list of distributions
    :type dists: list of :class:`distutils2.database.InstalledDistribution` and
                 :class:`distutils2.database.EggInfoDistribution` instances
    :rtype: a :class:`DependencyGraph` instance
    """
    scheme = get_scheme(scheme)
    graph = DependencyGraph()
    provided = {}  # maps names to lists of (version, dist) tuples

    # first, build the graph and find out what's provided
    for dist in dists:
        graph.add_distribution(dist)

        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Add to provided: %s, %s, %s', name, version, dist)
            provided.setdefault(name, []).append((version, dist))

    # now make the edges
    for dist in dists:
        requires = (dist.run_requires | dist.meta_requires | dist.build_requires | dist.dev_requires)
        for req in requires:
            try:
                matcher = scheme.matcher(req)
            except UnsupportedVersionError:
                # XXX compat-mode if cannot read the version
                logger.warning('could not read version %r - using name only', req)
                name = req.split()[0]
                matcher = scheme.matcher(name)

            name = matcher.key  # case-insensitive

            matched = False
            if name in provided:
                for version, provider in provided[name]:
                    try:
                        match = matcher.match(version)
                    except UnsupportedVersionError:
                        match = False

                    if match:
                        graph.add_edge(dist, provider, req)
                        matched = True
                        break
            if not matched:
                graph.add_missing(dist, req)
    return graph


def get_dependent_dists(dists, dist):
    """Recursively generate a list of distributions from *dists* that are
    dependent on *dist*.

    :param dists: a list of distributions
    :param dist: a distribution, member of *dists* for which we are interested
    """
    if dist not in dists:
        raise DistlibException('given distribution %r is not a member '
                               'of the list' % dist.name)
    graph = make_graph(dists)

    dep = [dist]  # dependent distributions
    todo = graph.reverse_list[dist]  # list of nodes we should inspect

    while todo:
        d = todo.pop()
        dep.append(d)
        for succ in graph.reverse_list[d]:
            if succ not in dep:
                todo.append(succ)

    dep.pop(0)  # remove dist from dep, was there to prevent infinite loops
    return dep


def get_required_dists(dists, dist):
    """Recursively generate a list of distributions from *dists* that are
    required by *dist*.

    :param dists: a list of distributions
    :param dist: a distribution, member of *dists* for which we are interested
                 in finding the dependencies.
    """
    if dist not in dists:
        raise DistlibException('given distribution %r is not a member '
                               'of the list' % dist.name)
    graph = make_graph(dists)

    req = set()  # required distributions
    todo = graph.adjacency_list[dist]  # list of nodes we should inspect
    seen = set(t[0] for t in todo)  # already added to todo

    while todo:
        d = todo.pop()[0]
        req.add(d)
        pred_list = graph.adjacency_list[d]
        for pred in pred_list:
            d = pred[0]
            if d not in req and d not in seen:
                seen.add(d)
                todo.append(pred)
    return req


def make_dist(name, version, **kwargs):
    """
    A convenience method for making a dist given just a name and version.
    """
    summary = kwargs.pop('summary', 'Placeholder for summary')
    md = Metadata(**kwargs)
    md.name = name
    md.version = version
    md.summary = summary or 'Placeholder for summary'
    return Distribution(md)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\azure.py ===
import asyncio
import json
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import httpx  # type: ignore
from openai import APITimeoutError, AsyncAzureOpenAI, AzureOpenAI

import litellm
from litellm.constants import AZURE_OPERATION_POLLING_TIMEOUT, DEFAULT_MAX_RETRIES
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.logging_utils import track_llm_api_timing
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.utils import (
    EmbeddingResponse,
    ImageResponse,
    LlmProviders,
    ModelResponse,
)
from litellm.utils import (
    CustomStreamWrapper,
    convert_to_model_response_object,
    modify_url,
)

from ...types.llms.openai import HttpxBinaryResponseContent
from ..base import BaseLLM
from .common_utils import (
    AzureOpenAIError,
    BaseAzureLLM,
    get_azure_ad_token_from_oidc,
    process_azure_headers,
    select_azure_base_url_or_endpoint,
)


class AzureOpenAIAssistantsAPIConfig:
    """
    Reference: https://learn.microsoft.com/en-us/azure/ai-services/openai/assistants-reference-messages?tabs=python#create-message
    """

    def __init__(
        self,
    ) -> None:
        pass

    def get_supported_openai_create_message_params(self):
        return [
            "role",
            "content",
            "attachments",
            "metadata",
        ]

    def map_openai_params_create_message_params(
        self, non_default_params: dict, optional_params: dict
    ):
        for param, value in non_default_params.items():
            if param == "role":
                optional_params["role"] = value
            if param == "metadata":
                optional_params["metadata"] = value
            elif param == "content":  # only string accepted
                if isinstance(value, str):
                    optional_params["content"] = value
                else:
                    raise litellm.utils.UnsupportedParamsError(
                        message="Azure only accepts content as a string.",
                        status_code=400,
                    )
            elif (
                param == "attachments"
            ):  # this is a v2 param. Azure currently supports the old 'file_id's param
                file_ids: List[str] = []
                if isinstance(value, list):
                    for item in value:
                        if "file_id" in item:
                            file_ids.append(item["file_id"])
                        else:
                            if litellm.drop_params is True:
                                pass
                            else:
                                raise litellm.utils.UnsupportedParamsError(
                                    message="Azure doesn't support {}. To drop it from the call, set `litellm.drop_params = True.".format(
                                        value
                                    ),
                                    status_code=400,
                                )
                else:
                    raise litellm.utils.UnsupportedParamsError(
                        message="Invalid param. attachments should always be a list. Got={}, Expected=List. Raw value={}".format(
                            type(value), value
                        ),
                        status_code=400,
                    )
        return optional_params


def _check_dynamic_azure_params(
    azure_client_params: dict,
    azure_client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]],
) -> bool:
    """
    Returns True if user passed in client params != initialized azure client

    Currently only implemented for api version
    """
    if azure_client is None:
        return True

    dynamic_params = ["api_version"]
    for k, v in azure_client_params.items():
        if k in dynamic_params and k == "api_version":
            if v is not None and v != azure_client._custom_query["api-version"]:
                return True

    return False


class AzureChatCompletion(BaseAzureLLM, BaseLLM):
    def __init__(self) -> None:
        super().__init__()

    def make_sync_azure_openai_chat_completion_request(
        self,
        azure_client: AzureOpenAI,
        data: dict,
        timeout: Union[float, httpx.Timeout],
    ):
        """
        Helper to:
        - call chat.completions.create.with_raw_response when litellm.return_response_headers is True
        - call chat.completions.create by default
        """
        try:
            raw_response = azure_client.chat.completions.with_raw_response.create(
                **data, timeout=timeout
            )

            headers = dict(raw_response.headers)
            response = raw_response.parse()
            return headers, response
        except Exception as e:
            raise e

    @track_llm_api_timing()
    async def make_azure_openai_chat_completion_request(
        self,
        azure_client: AsyncAzureOpenAI,
        data: dict,
        timeout: Union[float, httpx.Timeout],
        logging_obj: LiteLLMLoggingObj,
    ):
        """
        Helper to:
        - call chat.completions.create.with_raw_response when litellm.return_response_headers is True
        - call chat.completions.create by default
        """
        start_time = time.time()
        try:
            raw_response = await azure_client.chat.completions.with_raw_response.create(
                **data, timeout=timeout
            )

            headers = dict(raw_response.headers)
            response = raw_response.parse()
            return headers, response
        except APITimeoutError as e:
            end_time = time.time()
            time_delta = round(end_time - start_time, 2)
            e.message += f" - timeout value={timeout}, time taken={time_delta} seconds"
            raise e
        except Exception as e:
            raise e

    def completion(  # noqa: PLR0915
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        api_key: str,
        api_base: str,
        api_version: str,
        api_type: str,
        azure_ad_token: str,
        azure_ad_token_provider: Callable,
        dynamic_params: bool,
        print_verbose: Callable,
        timeout: Union[float, httpx.Timeout],
        logging_obj: LiteLLMLoggingObj,
        optional_params,
        litellm_params,
        logger_fn,
        acompletion: bool = False,
        headers: Optional[dict] = None,
        client=None,
    ):
        if headers:
            optional_params["extra_headers"] = headers
        try:
            if model is None or messages is None:
                raise AzureOpenAIError(
                    status_code=422, message="Missing model or messages"
                )

            max_retries = optional_params.pop("max_retries", None)
            if max_retries is None:
                max_retries = DEFAULT_MAX_RETRIES
            json_mode: Optional[bool] = optional_params.pop("json_mode", False)

            ### CHECK IF CLOUDFLARE AI GATEWAY ###
            ### if so - set the model as part of the base url
            if "gateway.ai.cloudflare.com" in api_base:
                client = self._init_azure_client_for_cloudflare_ai_gateway(
                    api_base=api_base,
                    model=model,
                    api_version=api_version,
                    max_retries=max_retries,
                    timeout=timeout,
                    api_key=api_key,
                    azure_ad_token=azure_ad_token,
                    azure_ad_token_provider=azure_ad_token_provider,
                    acompletion=acompletion,
                    client=client,
                    litellm_params=litellm_params,
                )

                data = {"model": None, "messages": messages, **optional_params}
            else:
                data = litellm.AzureOpenAIConfig().transform_request(
                    model=model,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    headers=headers or {},
                )

            if acompletion is True:
                if optional_params.get("stream", False):
                    return self.async_streaming(
                        logging_obj=logging_obj,
                        api_base=api_base,
                        dynamic_params=dynamic_params,
                        data=data,
                        model=model,
                        api_key=api_key,
                        api_version=api_version,
                        azure_ad_token=azure_ad_token,
                        azure_ad_token_provider=azure_ad_token_provider,
                        timeout=timeout,
                        client=client,
                        max_retries=max_retries,
                        litellm_params=litellm_params,
                    )
                else:
                    return self.acompletion(
                        api_base=api_base,
                        data=data,
                        model_response=model_response,
                        api_key=api_key,
                        api_version=api_version,
                        model=model,
                        azure_ad_token=azure_ad_token,
                        azure_ad_token_provider=azure_ad_token_provider,
                        dynamic_params=dynamic_params,
                        timeout=timeout,
                        client=client,
                        logging_obj=logging_obj,
                        max_retries=max_retries,
                        convert_tool_call_to_json_mode=json_mode,
                        litellm_params=litellm_params,
                    )
            elif "stream" in optional_params and optional_params["stream"] is True:
                return self.streaming(
                    logging_obj=logging_obj,
                    api_base=api_base,
                    dynamic_params=dynamic_params,
                    data=data,
                    model=model,
                    api_key=api_key,
                    api_version=api_version,
                    azure_ad_token=azure_ad_token,
                    azure_ad_token_provider=azure_ad_token_provider,
                    timeout=timeout,
                    client=client,
                    max_retries=max_retries,
                    litellm_params=litellm_params,
                )
            else:
                ## LOGGING
                logging_obj.pre_call(
                    input=messages,
                    api_key=api_key,
                    additional_args={
                        "headers": {
                            "api_key": api_key,
                            "azure_ad_token": azure_ad_token,
                        },
                        "api_version": api_version,
                        "api_base": api_base,
                        "complete_input_dict": data,
                    },
                )
                if not isinstance(max_retries, int):
                    raise AzureOpenAIError(
                        status_code=422, message="max retries must be an int"
                    )
                # init AzureOpenAI Client
                azure_client = self.get_azure_openai_client(
                    api_version=api_version,
                    api_base=api_base,
                    api_key=api_key,
                    model=model,
                    client=client,
                    _is_async=False,
                    litellm_params=litellm_params,
                )
                if not isinstance(azure_client, AzureOpenAI):
                    raise AzureOpenAIError(
                        status_code=500,
                        message="azure_client is not an instance of AzureOpenAI",
                    )

                headers, response = self.make_sync_azure_openai_chat_completion_request(
                    azure_client=azure_client, data=data, timeout=timeout
                )
                stringified_response = response.model_dump()
                ## LOGGING
                logging_obj.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=stringified_response,
                    additional_args={
                        "headers": headers,
                        "api_version": api_version,
                        "api_base": api_base,
                    },
                )
                return convert_to_model_response_object(
                    response_object=stringified_response,
                    model_response_object=model_response,
                    convert_tool_call_to_json_mode=json_mode,
                    _response_headers=headers,
                )
        except AzureOpenAIError as e:
            raise e
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            error_body = getattr(e, "body", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise AzureOpenAIError(
                status_code=status_code,
                message=str(e),
                headers=error_headers,
                body=error_body,
            )

    async def acompletion(
        self,
        api_key: str,
        api_version: str,
        model: str,
        api_base: str,
        data: dict,
        timeout: Any,
        dynamic_params: bool,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        max_retries: int,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        convert_tool_call_to_json_mode: Optional[bool] = None,
        client=None,  # this is the AsyncAzureOpenAI
        litellm_params: Optional[dict] = {},
    ):
        response = None
        try:
            # setting Azure client
            azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                client=client,
                _is_async=True,
                litellm_params=litellm_params,
            )
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise ValueError("Azure client is not an instance of AsyncAzureOpenAI")
            ## LOGGING
            logging_obj.pre_call(
                input=data["messages"],
                api_key=azure_client.api_key,
                additional_args={
                    "headers": {
                        "api_key": api_key,
                        "azure_ad_token": azure_ad_token,
                    },
                    "api_base": azure_client._base_url._uri_reference,
                    "acompletion": True,
                    "complete_input_dict": data,
                },
            )

            headers, response = await self.make_azure_openai_chat_completion_request(
                azure_client=azure_client,
                data=data,
                timeout=timeout,
                logging_obj=logging_obj,
            )
            logging_obj.model_call_details["response_headers"] = headers

            stringified_response = response.model_dump()
            logging_obj.post_call(
                input=data["messages"],
                api_key=api_key,
                original_response=stringified_response,
                additional_args={"complete_input_dict": data},
            )

            return convert_to_model_response_object(
                response_object=stringified_response,
                model_response_object=model_response,
                hidden_params={"headers": headers},
                _response_headers=headers,
                convert_tool_call_to_json_mode=convert_tool_call_to_json_mode,
            )
        except AzureOpenAIError as e:
            ## LOGGING
            logging_obj.post_call(
                input=data["messages"],
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=str(e),
            )
            raise e
        except asyncio.CancelledError as e:
            ## LOGGING
            logging_obj.post_call(
                input=data["messages"],
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=str(e),
            )
            raise AzureOpenAIError(status_code=500, message=str(e))
        except Exception as e:
            message = getattr(e, "message", str(e))
            body = getattr(e, "body", None)
            ## LOGGING
            logging_obj.post_call(
                input=data["messages"],
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=str(e),
            )
            if hasattr(e, "status_code"):
                raise e
            else:
                raise AzureOpenAIError(status_code=500, message=message, body=body)

    def streaming(
        self,
        logging_obj,
        api_base: str,
        api_key: str,
        api_version: str,
        dynamic_params: bool,
        data: dict,
        model: str,
        timeout: Any,
        max_retries: int,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        client=None,
        litellm_params: Optional[dict] = {},
    ):
        # init AzureOpenAI Client
        azure_client_params = {
            "api_version": api_version,
            "azure_endpoint": api_base,
            "azure_deployment": model,
            "http_client": litellm.client_session,
            "max_retries": max_retries,
            "timeout": timeout,
        }
        azure_client_params = select_azure_base_url_or_endpoint(
            azure_client_params=azure_client_params
        )
        if api_key is not None:
            azure_client_params["api_key"] = api_key
        elif azure_ad_token is not None:
            if azure_ad_token.startswith("oidc/"):
                azure_ad_token = get_azure_ad_token_from_oidc(azure_ad_token)
            azure_client_params["azure_ad_token"] = azure_ad_token
        elif azure_ad_token_provider is not None:
            azure_client_params["azure_ad_token_provider"] = azure_ad_token_provider

        azure_client = self.get_azure_openai_client(
            api_version=api_version,
            api_base=api_base,
            api_key=api_key,
            model=model,
            client=client,
            _is_async=False,
            litellm_params=litellm_params,
        )
        if not isinstance(azure_client, AzureOpenAI):
            raise AzureOpenAIError(
                status_code=500,
                message="azure_client is not an instance of AzureOpenAI",
            )
        ## LOGGING
        logging_obj.pre_call(
            input=data["messages"],
            api_key=azure_client.api_key,
            additional_args={
                "headers": {
                    "api_key": api_key,
                    "azure_ad_token": azure_ad_token,
                },
                "api_base": azure_client._base_url._uri_reference,
                "acompletion": True,
                "complete_input_dict": data,
            },
        )
        headers, response = self.make_sync_azure_openai_chat_completion_request(
            azure_client=azure_client, data=data, timeout=timeout
        )
        streamwrapper = CustomStreamWrapper(
            completion_stream=response,
            model=model,
            custom_llm_provider="azure",
            logging_obj=logging_obj,
            stream_options=data.get("stream_options", None),
            _response_headers=process_azure_headers(headers),
        )
        return streamwrapper

    async def async_streaming(
        self,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        api_key: str,
        api_version: str,
        dynamic_params: bool,
        data: dict,
        model: str,
        timeout: Any,
        max_retries: int,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        client=None,
        litellm_params: Optional[dict] = {},
    ):
        try:
            azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                client=client,
                _is_async=True,
                litellm_params=litellm_params,
            )
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise ValueError("Azure client is not an instance of AsyncAzureOpenAI")

            ## LOGGING
            logging_obj.pre_call(
                input=data["messages"],
                api_key=azure_client.api_key,
                additional_args={
                    "headers": {
                        "api_key": api_key,
                        "azure_ad_token": azure_ad_token,
                    },
                    "api_base": azure_client._base_url._uri_reference,
                    "acompletion": True,
                    "complete_input_dict": data,
                },
            )

            headers, response = await self.make_azure_openai_chat_completion_request(
                azure_client=azure_client,
                data=data,
                timeout=timeout,
                logging_obj=logging_obj,
            )
            logging_obj.model_call_details["response_headers"] = headers

            # return response
            streamwrapper = CustomStreamWrapper(
                completion_stream=response,
                model=model,
                custom_llm_provider="azure",
                logging_obj=logging_obj,
                stream_options=data.get("stream_options", None),
                _response_headers=headers,
            )
            return streamwrapper  ## DO NOT make this into an async for ... loop, it will yield an async generator, which won't raise errors if the response fails
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            message = getattr(e, "message", str(e))
            error_body = getattr(e, "body", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise AzureOpenAIError(
                status_code=status_code,
                message=message,
                headers=error_headers,
                body=error_body,
            )

    async def aembedding(
        self,
        model: str,
        data: dict,
        model_response: EmbeddingResponse,
        input: list,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        client: Optional[AsyncAzureOpenAI] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        max_retries: Optional[int] = None,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        litellm_params: Optional[dict] = {},
    ) -> EmbeddingResponse:
        response = None
        try:
            openai_aclient = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                _is_async=True,
                client=client,
                litellm_params=litellm_params,
            )
            if not isinstance(openai_aclient, AsyncAzureOpenAI):
                raise ValueError("Azure client is not an instance of AsyncAzureOpenAI")

            raw_response = await openai_aclient.embeddings.with_raw_response.create(
                **data, timeout=timeout
            )
            headers = dict(raw_response.headers)
            response = raw_response.parse()
            stringified_response = response.model_dump()
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=stringified_response,
            )
            embedding_response = convert_to_model_response_object(
                response_object=stringified_response,
                model_response_object=model_response,
                hidden_params={"headers": headers},
                _response_headers=process_azure_headers(headers),
                response_type="embedding",
            )
            if not isinstance(embedding_response, EmbeddingResponse):
                raise AzureOpenAIError(
                    status_code=500,
                    message="embedding_response is not an instance of EmbeddingResponse",
                )
            return embedding_response
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=str(e),
            )
            raise e

    def embedding(
        self,
        model: str,
        input: list,
        api_base: str,
        api_version: str,
        timeout: float,
        logging_obj: LiteLLMLoggingObj,
        model_response: EmbeddingResponse,
        optional_params: dict,
        api_key: Optional[str] = None,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        max_retries: Optional[int] = None,
        client=None,
        aembedding=None,
        headers: Optional[dict] = None,
        litellm_params: Optional[dict] = None,
    ) -> Union[EmbeddingResponse, Coroutine[Any, Any, EmbeddingResponse]]:
        if headers:
            optional_params["extra_headers"] = headers
        if self._client_session is None:
            self._client_session = self.create_client_session()
        try:
            data = {"model": model, "input": input, **optional_params}
            if max_retries is None:
                max_retries = litellm.DEFAULT_MAX_RETRIES
            ## LOGGING
            logging_obj.pre_call(
                input=input,
                api_key=api_key,
                additional_args={
                    "complete_input_dict": data,
                    "headers": {"api_key": api_key, "azure_ad_token": azure_ad_token},
                },
            )

            if aembedding is True:
                return self.aembedding(
                    data=data,
                    input=input,
                    model=model,
                    logging_obj=logging_obj,
                    api_key=api_key,
                    model_response=model_response,
                    timeout=timeout,
                    client=client,
                    litellm_params=litellm_params,
                    api_base=api_base,
                )
            azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                _is_async=False,
                client=client,
                litellm_params=litellm_params,
            )
            if not isinstance(azure_client, AzureOpenAI):
                raise AzureOpenAIError(
                    status_code=500,
                    message="azure_client is not an instance of AzureOpenAI",
                )

            ## COMPLETION CALL
            raw_response = azure_client.embeddings.with_raw_response.create(**data, timeout=timeout)  # type: ignore
            headers = dict(raw_response.headers)
            response = raw_response.parse()
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data, "api_base": api_base},
                original_response=response,
            )

            return convert_to_model_response_object(response_object=response.model_dump(), model_response_object=model_response, response_type="embedding", _response_headers=process_azure_headers(headers))  # type: ignore
        except AzureOpenAIError as e:
            raise e
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            error_text = str(e)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
                error_text = error_response.text
            raise AzureOpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

    async def make_async_azure_httpx_request(
        self,
        client: Optional[AsyncHTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        api_base: str,
        api_version: str,
        api_key: str,
        data: dict,
        headers: dict,
    ) -> httpx.Response:
        """
        Implemented for azure dall-e-2 image gen calls

        Alternative to needing a custom transport implementation
        """
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            async_handler = get_async_httpx_client(
                llm_provider=LlmProviders.AZURE,
                params=_params,
            )
        else:
            async_handler = client  # type: ignore

        if (
            "images/generations" in api_base
            and api_version
            in [  # dall-e-3 starts from `2023-12-01-preview` so we should be able to avoid conflict
                "2023-06-01-preview",
                "2023-07-01-preview",
                "2023-08-01-preview",
                "2023-09-01-preview",
                "2023-10-01-preview",
            ]
        ):  # CREATE + POLL for azure dall-e-2 calls
            api_base = modify_url(
                original_url=api_base, new_path="/openai/images/generations:submit"
            )

            data.pop(
                "model", None
            )  # REMOVE 'model' from dall-e-2 arg https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#request-a-generated-image-dall-e-2-preview
            response = await async_handler.post(
                url=api_base,
                data=json.dumps(data),
                headers=headers,
            )
            if "operation-location" in response.headers:
                operation_location_url = response.headers["operation-location"]
            else:
                raise AzureOpenAIError(status_code=500, message=response.text)
            response = await async_handler.get(
                url=operation_location_url,
                headers=headers,
            )

            await response.aread()

            timeout_secs: int = AZURE_OPERATION_POLLING_TIMEOUT
            start_time = time.time()
            if "status" not in response.json():
                raise Exception(
                    "Expected 'status' in response. Got={}".format(response.json())
                )
            while response.json()["status"] not in ["succeeded", "failed"]:
                if time.time() - start_time > timeout_secs:
                    raise AzureOpenAIError(
                        status_code=408, message="Operation polling timed out."
                    )

                await asyncio.sleep(int(response.headers.get("retry-after") or 10))
                response = await async_handler.get(
                    url=operation_location_url,
                    headers=headers,
                )
                await response.aread()

            if response.json()["status"] == "failed":
                error_data = response.json()
                raise AzureOpenAIError(status_code=400, message=json.dumps(error_data))

            result = response.json()["result"]
            return httpx.Response(
                status_code=200,
                headers=response.headers,
                content=json.dumps(result).encode("utf-8"),
                request=httpx.Request(method="POST", url="https://api.openai.com/v1"),
            )
        return await async_handler.post(
            url=api_base,
            json=data,
            headers=headers,
        )

    def make_sync_azure_httpx_request(
        self,
        client: Optional[HTTPHandler],
        timeout: Optional[Union[float, httpx.Timeout]],
        api_base: str,
        api_version: str,
        api_key: str,
        data: dict,
        headers: dict,
    ) -> httpx.Response:
        """
        Implemented for azure dall-e-2 image gen calls

        Alternative to needing a custom transport implementation
        """
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            sync_handler = HTTPHandler(**_params, client=litellm.client_session)  # type: ignore
        else:
            sync_handler = client  # type: ignore

        if (
            "images/generations" in api_base
            and api_version
            in [  # dall-e-3 starts from `2023-12-01-preview` so we should be able to avoid conflict
                "2023-06-01-preview",
                "2023-07-01-preview",
                "2023-08-01-preview",
                "2023-09-01-preview",
                "2023-10-01-preview",
            ]
        ):  # CREATE + POLL for azure dall-e-2 calls
            api_base = modify_url(
                original_url=api_base, new_path="/openai/images/generations:submit"
            )

            data.pop(
                "model", None
            )  # REMOVE 'model' from dall-e-2 arg https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#request-a-generated-image-dall-e-2-preview
            response = sync_handler.post(
                url=api_base,
                data=json.dumps(data),
                headers=headers,
            )
            if "operation-location" in response.headers:
                operation_location_url = response.headers["operation-location"]
            else:
                raise AzureOpenAIError(status_code=500, message=response.text)
            response = sync_handler.get(
                url=operation_location_url,
                headers=headers,
            )

            response.read()

            timeout_secs: int = AZURE_OPERATION_POLLING_TIMEOUT
            start_time = time.time()
            if "status" not in response.json():
                raise Exception(
                    "Expected 'status' in response. Got={}".format(response.json())
                )
            while response.json()["status"] not in ["succeeded", "failed"]:
                if time.time() - start_time > timeout_secs:
                    raise AzureOpenAIError(
                        status_code=408, message="Operation polling timed out."
                    )

                time.sleep(int(response.headers.get("retry-after") or 10))
                response = sync_handler.get(
                    url=operation_location_url,
                    headers=headers,
                )
                response.read()

            if response.json()["status"] == "failed":
                error_data = response.json()
                raise AzureOpenAIError(status_code=400, message=json.dumps(error_data))

            result = response.json()["result"]
            return httpx.Response(
                status_code=200,
                headers=response.headers,
                content=json.dumps(result).encode("utf-8"),
                request=httpx.Request(method="POST", url="https://api.openai.com/v1"),
            )
        return sync_handler.post(
            url=api_base,
            json=data,
            headers=headers,
        )

    def create_azure_base_url(
        self, azure_client_params: dict, model: Optional[str]
    ) -> str:
        api_base: str = azure_client_params.get(
            "azure_endpoint", ""
        )  # "https://example-endpoint.openai.azure.com"
        if api_base.endswith("/"):
            api_base = api_base.rstrip("/")
        api_version: str = azure_client_params.get("api_version", "")
        if model is None:
            model = ""

        if "/openai/deployments/" in api_base:
            base_url_with_deployment = api_base
        else:
            base_url_with_deployment = api_base + "/openai/deployments/" + model

        base_url_with_deployment += "/images/generations"
        base_url_with_deployment += "?api-version=" + api_version

        return base_url_with_deployment

    async def aimage_generation(
        self,
        data: dict,
        model_response: ModelResponse,
        azure_client_params: dict,
        api_key: str,
        input: list,
        logging_obj: LiteLLMLoggingObj,
        headers: dict,
        client=None,
        timeout=None,
    ) -> litellm.ImageResponse:
        response: Optional[dict] = None
        try:
            # response = await azure_client.images.generate(**data, timeout=timeout)
            api_base: str = azure_client_params.get(
                "api_base", ""
            )  # "https://example-endpoint.openai.azure.com"
            if api_base.endswith("/"):
                api_base = api_base.rstrip("/")
            api_version: str = azure_client_params.get("api_version", "")
            img_gen_api_base = self.create_azure_base_url(
                azure_client_params=azure_client_params, model=data.get("model", "")
            )

            ## LOGGING
            logging_obj.pre_call(
                input=data["prompt"],
                api_key=api_key,
                additional_args={
                    "complete_input_dict": data,
                    "api_base": img_gen_api_base,
                    "headers": headers,
                },
            )
            httpx_response: httpx.Response = await self.make_async_azure_httpx_request(
                client=None,
                timeout=timeout,
                api_base=img_gen_api_base,
                api_version=api_version,
                api_key=api_key,
                data=data,
                headers=headers,
            )
            response = httpx_response.json()

            stringified_response = response
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=stringified_response,
            )
            return convert_to_model_response_object(  # type: ignore
                response_object=stringified_response,
                model_response_object=model_response,
                response_type="image_generation",
            )
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=str(e),
            )
            raise e

    def image_generation(
        self,
        prompt: str,
        timeout: float,
        optional_params: dict,
        logging_obj: LiteLLMLoggingObj,
        headers: dict,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        model_response: Optional[ImageResponse] = None,
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        client=None,
        aimg_generation=None,
        litellm_params: Optional[dict] = None,
    ) -> ImageResponse:
        try:
            if model and len(model) > 0:
                model = model
            else:
                model = None

            ## BASE MODEL CHECK
            if (
                model_response is not None
                and optional_params.get("base_model", None) is not None
            ):
                model_response._hidden_params["model"] = optional_params.pop(
                    "base_model"
                )

            data = {"model": model, "prompt": prompt, **optional_params}
            max_retries = data.pop("max_retries", 2)
            if not isinstance(max_retries, int):
                raise AzureOpenAIError(
                    status_code=422, message="max retries must be an int"
                )

            # init AzureOpenAI Client
            azure_client_params: Dict[str, Any] = self.initialize_azure_sdk_client(
                litellm_params=litellm_params or {},
                api_key=api_key,
                model_name=model or "",
                api_version=api_version,
                api_base=api_base,
                is_async=False,
            )
            if aimg_generation is True:
                return self.aimage_generation(data=data, input=input, logging_obj=logging_obj, model_response=model_response, api_key=api_key, client=client, azure_client_params=azure_client_params, timeout=timeout, headers=headers)  # type: ignore

            img_gen_api_base = self.create_azure_base_url(
                azure_client_params=azure_client_params, model=data.get("model", "")
            )

            ## LOGGING
            logging_obj.pre_call(
                input=data["prompt"],
                api_key=api_key,
                additional_args={
                    "complete_input_dict": data,
                    "api_base": img_gen_api_base,
                    "headers": headers,
                },
            )
            httpx_response: httpx.Response = self.make_sync_azure_httpx_request(
                client=None,
                timeout=timeout,
                api_base=img_gen_api_base,
                api_version=api_version or "",
                api_key=api_key or "",
                data=data,
                headers=headers,
            )
            response = httpx_response.json()

            ## LOGGING
            logging_obj.post_call(
                input=prompt,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=response,
            )
            # return response
            return convert_to_model_response_object(response_object=response, model_response_object=model_response, response_type="image_generation")  # type: ignore
        except AzureOpenAIError as e:
            raise e
        except Exception as e:
            error_code = getattr(e, "status_code", None)
            if error_code is not None:
                raise AzureOpenAIError(status_code=error_code, message=str(e))
            else:
                raise AzureOpenAIError(status_code=500, message=str(e))

    def audio_speech(
        self,
        model: str,
        input: str,
        voice: str,
        optional_params: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        organization: Optional[str],
        max_retries: int,
        timeout: Union[float, httpx.Timeout],
        azure_ad_token: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        aspeech: Optional[bool] = None,
        client=None,
        litellm_params: Optional[dict] = None,
    ) -> HttpxBinaryResponseContent:
        max_retries = optional_params.pop("max_retries", 2)

        if aspeech is not None and aspeech is True:
            return self.async_audio_speech(
                model=model,
                input=input,
                voice=voice,
                optional_params=optional_params,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                azure_ad_token_provider=azure_ad_token_provider,
                max_retries=max_retries,
                timeout=timeout,
                client=client,
                litellm_params=litellm_params,
            )  # type: ignore

        azure_client: AzureOpenAI = self.get_azure_openai_client(
            api_base=api_base,
            api_version=api_version,
            api_key=api_key,
            model=model,
            _is_async=False,
            client=client,
            litellm_params=litellm_params,
        )  # type: ignore

        response = azure_client.audio.speech.create(
            model=model,
            voice=voice,  # type: ignore
            input=input,
            **optional_params,
        )
        return HttpxBinaryResponseContent(response=response.response)

    async def async_audio_speech(
        self,
        model: str,
        input: str,
        voice: str,
        optional_params: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        azure_ad_token_provider: Optional[Callable],
        max_retries: int,
        timeout: Union[float, httpx.Timeout],
        client=None,
        litellm_params: Optional[dict] = None,
    ) -> HttpxBinaryResponseContent:
        azure_client: AsyncAzureOpenAI = self.get_azure_openai_client(
            api_base=api_base,
            api_version=api_version,
            api_key=api_key,
            model=model,
            _is_async=True,
            client=client,
            litellm_params=litellm_params,
        )  # type: ignore

        azure_response = await azure_client.audio.speech.create(
            model=model,
            voice=voice,  # type: ignore
            input=input,
            **optional_params,
        )

        return HttpxBinaryResponseContent(response=azure_response.response)

    def get_headers(
        self,
        model: Optional[str],
        api_key: str,
        api_base: str,
        api_version: str,
        timeout: float,
        mode: str,
        messages: Optional[list] = None,
        input: Optional[list] = None,
        prompt: Optional[str] = None,
    ) -> dict:
        client_session = litellm.client_session or httpx.Client()
        if "gateway.ai.cloudflare.com" in api_base:
            ## build base url - assume api base includes resource name
            if not api_base.endswith("/"):
                api_base += "/"
            api_base += f"{model}"
            client = AzureOpenAI(
                base_url=api_base,
                api_version=api_version,
                api_key=api_key,
                timeout=timeout,
                http_client=client_session,
            )
            model = None
            # cloudflare ai gateway, needs model=None
        else:
            client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=api_base,
                api_key=api_key,
                timeout=timeout,
                http_client=client_session,
            )

            # only run this check if it's not cloudflare ai gateway
            if model is None and mode != "image_generation":
                raise Exception("model is not set")

        completion = None

        if messages is None:
            messages = [{"role": "user", "content": "Hey"}]
        try:
            completion = client.chat.completions.with_raw_response.create(
                model=model,  # type: ignore
                messages=messages,  # type: ignore
            )
        except Exception as e:
            raise e
        response = {}

        if completion is None or not hasattr(completion, "headers"):
            raise Exception("invalid completion response")

        if (
            completion.headers.get("x-ratelimit-remaining-requests", None) is not None
        ):  # not provided for dall-e requests
            response["x-ratelimit-remaining-requests"] = completion.headers[
                "x-ratelimit-remaining-requests"
            ]

        if completion.headers.get("x-ratelimit-remaining-tokens", None) is not None:
            response["x-ratelimit-remaining-tokens"] = completion.headers[
                "x-ratelimit-remaining-tokens"
            ]

        if completion.headers.get("x-ms-region", None) is not None:
            response["x-ms-region"] = completion.headers["x-ms-region"]

        return response

# === NexusCore/openenv\Lib\site-packages\nltk\tag\hmm.py ===
# Natural Language Toolkit: Hidden Markov Model
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Trevor Cohn <tacohn@csse.unimelb.edu.au>
#         Philip Blunsom <pcbl@csse.unimelb.edu.au>
#         Tiago Tresoldi <tiago@tresoldi.pro.br> (fixes)
#         Steven Bird <stevenbird1@gmail.com> (fixes)
#         Joseph Frazee <jfrazee@mail.utexas.edu> (fixes)
#         Steven Xu <xxu@student.unimelb.edu.au> (fixes)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Hidden Markov Models (HMMs) largely used to assign the correct label sequence
to sequential data or assess the probability of a given label and data
sequence. These models are finite state machines characterised by a number of
states, transitions between these states, and output symbols emitted while in
each state. The HMM is an extension to the Markov chain, where each state
corresponds deterministically to a given event. In the HMM the observation is
a probabilistic function of the state. HMMs share the Markov chain's
assumption, being that the probability of transition from one state to another
only depends on the current state - i.e. the series of states that led to the
current state are not used. They are also time invariant.

The HMM is a directed graph, with probability weighted edges (representing the
probability of a transition between the source and sink states) where each
vertex emits an output symbol when entered. The symbol (or observation) is
non-deterministically generated. For this reason, knowing that a sequence of
output observations was generated by a given HMM does not mean that the
corresponding sequence of states (and what the current state is) is known.
This is the 'hidden' in the hidden markov model.

Formally, a HMM can be characterised by:

- the output observation alphabet. This is the set of symbols which may be
  observed as output of the system.
- the set of states.
- the transition probabilities *a_{ij} = P(s_t = j | s_{t-1} = i)*. These
  represent the probability of transition to each state from a given state.
- the output probability matrix *b_i(k) = P(X_t = o_k | s_t = i)*. These
  represent the probability of observing each symbol in a given state.
- the initial state distribution. This gives the probability of starting
  in each state.

To ground this discussion, take a common NLP application, part-of-speech (POS)
tagging. An HMM is desirable for this task as the highest probability tag
sequence can be calculated for a given sequence of word forms. This differs
from other tagging techniques which often tag each word individually, seeking
to optimise each individual tagging greedily without regard to the optimal
combination of tags for a larger unit, such as a sentence. The HMM does this
with the Viterbi algorithm, which efficiently computes the optimal path
through the graph given the sequence of words forms.

In POS tagging the states usually have a 1:1 correspondence with the tag
alphabet - i.e. each state represents a single tag. The output observation
alphabet is the set of word forms (the lexicon), and the remaining three
parameters are derived by a training regime. With this information the
probability of a given sentence can be easily derived, by simply summing the
probability of each distinct path through the model. Similarly, the highest
probability tagging sequence can be derived with the Viterbi algorithm,
yielding a state sequence which can be mapped into a tag sequence.

This discussion assumes that the HMM has been trained. This is probably the
most difficult task with the model, and requires either MLE estimates of the
parameters or unsupervised learning using the Baum-Welch algorithm, a variant
of EM.

For more information, please consult the source code for this module,
which includes extensive demonstration code.
"""

import itertools
import re

try:
    import numpy as np
except ImportError:
    pass

from nltk.metrics import accuracy
from nltk.probability import (
    ConditionalFreqDist,
    ConditionalProbDist,
    DictionaryConditionalProbDist,
    DictionaryProbDist,
    FreqDist,
    LidstoneProbDist,
    MLEProbDist,
    MutableProbDist,
    RandomProbDist,
)
from nltk.tag.api import TaggerI
from nltk.util import LazyMap, unique_list

_TEXT = 0  # index of text in a tuple
_TAG = 1  # index of tag in a tuple


def _identity(labeled_symbols):
    return labeled_symbols


class HiddenMarkovModelTagger(TaggerI):
    """
    Hidden Markov model class, a generative model for labelling sequence data.
    These models define the joint probability of a sequence of symbols and
    their labels (state transitions) as the product of the starting state
    probability, the probability of each state transition, and the probability
    of each observation being generated from each state. This is described in
    more detail in the module documentation.

    This implementation is based on the HMM description in Chapter 8, Huang,
    Acero and Hon, Spoken Language Processing and includes an extension for
    training shallow HMM parsers or specialized HMMs as in Molina et.
    al, 2002.  A specialized HMM modifies training data by applying a
    specialization function to create a new training set that is more
    appropriate for sequential tagging with an HMM.  A typical use case is
    chunking.

    :param symbols: the set of output symbols (alphabet)
    :type symbols: seq of any
    :param states: a set of states representing state space
    :type states: seq of any
    :param transitions: transition probabilities; Pr(s_i | s_j) is the
        probability of transition from state i given the model is in
        state_j
    :type transitions: ConditionalProbDistI
    :param outputs: output probabilities; Pr(o_k | s_i) is the probability
        of emitting symbol k when entering state i
    :type outputs: ConditionalProbDistI
    :param priors: initial state distribution; Pr(s_i) is the probability
        of starting in state i
    :type priors: ProbDistI
    :param transform: an optional function for transforming training
        instances, defaults to the identity function.
    :type transform: callable
    """

    def __init__(
        self, symbols, states, transitions, outputs, priors, transform=_identity
    ):
        self._symbols = unique_list(symbols)
        self._states = unique_list(states)
        self._transitions = transitions
        self._outputs = outputs
        self._priors = priors
        self._cache = None
        self._transform = transform

    @classmethod
    def _train(
        cls,
        labeled_sequence,
        test_sequence=None,
        unlabeled_sequence=None,
        transform=_identity,
        estimator=None,
        **kwargs,
    ):
        if estimator is None:

            def estimator(fd, bins):
                return LidstoneProbDist(fd, 0.1, bins)

        labeled_sequence = LazyMap(transform, labeled_sequence)
        symbols = unique_list(word for sent in labeled_sequence for word, tag in sent)
        tag_set = unique_list(tag for sent in labeled_sequence for word, tag in sent)

        trainer = HiddenMarkovModelTrainer(tag_set, symbols)
        hmm = trainer.train_supervised(labeled_sequence, estimator=estimator)
        hmm = cls(
            hmm._symbols,
            hmm._states,
            hmm._transitions,
            hmm._outputs,
            hmm._priors,
            transform=transform,
        )

        if test_sequence:
            hmm.test(test_sequence, verbose=kwargs.get("verbose", False))

        if unlabeled_sequence:
            max_iterations = kwargs.get("max_iterations", 5)
            hmm = trainer.train_unsupervised(
                unlabeled_sequence, model=hmm, max_iterations=max_iterations
            )
            if test_sequence:
                hmm.test(test_sequence, verbose=kwargs.get("verbose", False))

        return hmm

    @classmethod
    def train(
        cls, labeled_sequence, test_sequence=None, unlabeled_sequence=None, **kwargs
    ):
        """
        Train a new HiddenMarkovModelTagger using the given labeled and
        unlabeled training instances. Testing will be performed if test
        instances are provided.

        :return: a hidden markov model tagger
        :rtype: HiddenMarkovModelTagger
        :param labeled_sequence: a sequence of labeled training instances,
            i.e. a list of sentences represented as tuples
        :type labeled_sequence: list(list)
        :param test_sequence: a sequence of labeled test instances
        :type test_sequence: list(list)
        :param unlabeled_sequence: a sequence of unlabeled training instances,
            i.e. a list of sentences represented as words
        :type unlabeled_sequence: list(list)
        :param transform: an optional function for transforming training
            instances, defaults to the identity function, see ``transform()``
        :type transform: function
        :param estimator: an optional function or class that maps a
            condition's frequency distribution to its probability
            distribution, defaults to a Lidstone distribution with gamma = 0.1
        :type estimator: class or function
        :param verbose: boolean flag indicating whether training should be
            verbose or include printed output
        :type verbose: bool
        :param max_iterations: number of Baum-Welch iterations to perform
        :type max_iterations: int
        """
        return cls._train(labeled_sequence, test_sequence, unlabeled_sequence, **kwargs)

    def probability(self, sequence):
        """
        Returns the probability of the given symbol sequence. If the sequence
        is labelled, then returns the joint probability of the symbol, state
        sequence. Otherwise, uses the forward algorithm to find the
        probability over all label sequences.

        :return: the probability of the sequence
        :rtype: float
        :param sequence: the sequence of symbols which must contain the TEXT
            property, and optionally the TAG property
        :type sequence:  Token
        """
        return 2 ** (self.log_probability(self._transform(sequence)))

    def log_probability(self, sequence):
        """
        Returns the log-probability of the given symbol sequence. If the
        sequence is labelled, then returns the joint log-probability of the
        symbol, state sequence. Otherwise, uses the forward algorithm to find
        the log-probability over all label sequences.

        :return: the log-probability of the sequence
        :rtype: float
        :param sequence: the sequence of symbols which must contain the TEXT
            property, and optionally the TAG property
        :type sequence:  Token
        """
        sequence = self._transform(sequence)

        T = len(sequence)

        if T > 0 and sequence[0][_TAG]:
            last_state = sequence[0][_TAG]
            p = self._priors.logprob(last_state) + self._output_logprob(
                last_state, sequence[0][_TEXT]
            )
            for t in range(1, T):
                state = sequence[t][_TAG]
                p += self._transitions[last_state].logprob(
                    state
                ) + self._output_logprob(state, sequence[t][_TEXT])
                last_state = state
            return p
        else:
            alpha = self._forward_probability(sequence)
            p = logsumexp2(alpha[T - 1])
            return p

    def tag(self, unlabeled_sequence):
        """
        Tags the sequence with the highest probability state sequence. This
        uses the best_path method to find the Viterbi path.

        :return: a labelled sequence of symbols
        :rtype: list
        :param unlabeled_sequence: the sequence of unlabeled symbols
        :type unlabeled_sequence: list
        """
        unlabeled_sequence = self._transform(unlabeled_sequence)
        return self._tag(unlabeled_sequence)

    def _tag(self, unlabeled_sequence):
        path = self._best_path(unlabeled_sequence)
        return list(zip(unlabeled_sequence, path))

    def _output_logprob(self, state, symbol):
        """
        :return: the log probability of the symbol being observed in the given
            state
        :rtype: float
        """
        return self._outputs[state].logprob(symbol)

    def _create_cache(self):
        """
        The cache is a tuple (P, O, X, S) where:

          - S maps symbols to integers.  I.e., it is the inverse
            mapping from self._symbols; for each symbol s in
            self._symbols, the following is true::

              self._symbols[S[s]] == s

          - O is the log output probabilities::

              O[i,k] = log( P(token[t]=sym[k]|tag[t]=state[i]) )

          - X is the log transition probabilities::

              X[i,j] = log( P(tag[t]=state[j]|tag[t-1]=state[i]) )

          - P is the log prior probabilities::

              P[i] = log( P(tag[0]=state[i]) )
        """
        if not self._cache:
            N = len(self._states)
            M = len(self._symbols)
            P = np.zeros(N, np.float32)
            X = np.zeros((N, N), np.float32)
            O = np.zeros((N, M), np.float32)
            for i in range(N):
                si = self._states[i]
                P[i] = self._priors.logprob(si)
                for j in range(N):
                    X[i, j] = self._transitions[si].logprob(self._states[j])
                for k in range(M):
                    O[i, k] = self._output_logprob(si, self._symbols[k])
            S = {}
            for k in range(M):
                S[self._symbols[k]] = k
            self._cache = (P, O, X, S)

    def _update_cache(self, symbols):
        # add new symbols to the symbol table and repopulate the output
        # probabilities and symbol table mapping
        if symbols:
            self._create_cache()
            P, O, X, S = self._cache
            for symbol in symbols:
                if symbol not in self._symbols:
                    self._cache = None
                    self._symbols.append(symbol)
            # don't bother with the work if there aren't any new symbols
            if not self._cache:
                N = len(self._states)
                M = len(self._symbols)
                Q = O.shape[1]
                # add new columns to the output probability table without
                # destroying the old probabilities
                O = np.hstack([O, np.zeros((N, M - Q), np.float32)])
                for i in range(N):
                    si = self._states[i]
                    # only calculate probabilities for new symbols
                    for k in range(Q, M):
                        O[i, k] = self._output_logprob(si, self._symbols[k])
                # only create symbol mappings for new symbols
                for k in range(Q, M):
                    S[self._symbols[k]] = k
                self._cache = (P, O, X, S)

    def reset_cache(self):
        self._cache = None

    def best_path(self, unlabeled_sequence):
        """
        Returns the state sequence of the optimal (most probable) path through
        the HMM. Uses the Viterbi algorithm to calculate this part by dynamic
        programming.

        :return: the state sequence
        :rtype: sequence of any
        :param unlabeled_sequence: the sequence of unlabeled symbols
        :type unlabeled_sequence: list
        """
        unlabeled_sequence = self._transform(unlabeled_sequence)
        return self._best_path(unlabeled_sequence)

    def _best_path(self, unlabeled_sequence):
        T = len(unlabeled_sequence)
        N = len(self._states)
        self._create_cache()
        self._update_cache(unlabeled_sequence)
        P, O, X, S = self._cache

        V = np.zeros((T, N), np.float32)
        B = -np.ones((T, N), int)

        V[0] = P + O[:, S[unlabeled_sequence[0]]]
        for t in range(1, T):
            for j in range(N):
                vs = V[t - 1, :] + X[:, j]
                best = np.argmax(vs)
                V[t, j] = vs[best] + O[j, S[unlabeled_sequence[t]]]
                B[t, j] = best

        current = np.argmax(V[T - 1, :])
        sequence = [current]
        for t in range(T - 1, 0, -1):
            last = B[t, current]
            sequence.append(last)
            current = last

        sequence.reverse()
        return list(map(self._states.__getitem__, sequence))

    def best_path_simple(self, unlabeled_sequence):
        """
        Returns the state sequence of the optimal (most probable) path through
        the HMM. Uses the Viterbi algorithm to calculate this part by dynamic
        programming.  This uses a simple, direct method, and is included for
        teaching purposes.

        :return: the state sequence
        :rtype: sequence of any
        :param unlabeled_sequence: the sequence of unlabeled symbols
        :type unlabeled_sequence: list
        """
        unlabeled_sequence = self._transform(unlabeled_sequence)
        return self._best_path_simple(unlabeled_sequence)

    def _best_path_simple(self, unlabeled_sequence):
        T = len(unlabeled_sequence)
        N = len(self._states)
        V = np.zeros((T, N), np.float64)
        B = {}

        # find the starting log probabilities for each state
        symbol = unlabeled_sequence[0]
        for i, state in enumerate(self._states):
            V[0, i] = self._priors.logprob(state) + self._output_logprob(state, symbol)
            B[0, state] = None

        # find the maximum log probabilities for reaching each state at time t
        for t in range(1, T):
            symbol = unlabeled_sequence[t]
            for j in range(N):
                sj = self._states[j]
                best = None
                for i in range(N):
                    si = self._states[i]
                    va = V[t - 1, i] + self._transitions[si].logprob(sj)
                    if not best or va > best[0]:
                        best = (va, si)
                V[t, j] = best[0] + self._output_logprob(sj, symbol)
                B[t, sj] = best[1]

        # find the highest probability final state
        best = None
        for i in range(N):
            val = V[T - 1, i]
            if not best or val > best[0]:
                best = (val, self._states[i])

        # traverse the back-pointers B to find the state sequence
        current = best[1]
        sequence = [current]
        for t in range(T - 1, 0, -1):
            last = B[t, current]
            sequence.append(last)
            current = last

        sequence.reverse()
        return sequence

    def random_sample(self, rng, length):
        """
        Randomly sample the HMM to generate a sentence of a given length. This
        samples the prior distribution then the observation distribution and
        transition distribution for each subsequent observation and state.
        This will mostly generate unintelligible garbage, but can provide some
        amusement.

        :return:        the randomly created state/observation sequence,
                        generated according to the HMM's probability
                        distributions. The SUBTOKENS have TEXT and TAG
                        properties containing the observation and state
                        respectively.
        :rtype:         list
        :param rng:     random number generator
        :type rng:      Random (or any object with a random() method)
        :param length:  desired output length
        :type length:   int
        """

        # sample the starting state and symbol prob dists
        tokens = []
        state = self._sample_probdist(self._priors, rng.random(), self._states)
        symbol = self._sample_probdist(
            self._outputs[state], rng.random(), self._symbols
        )
        tokens.append((symbol, state))

        for i in range(1, length):
            # sample the state transition and symbol prob dists
            state = self._sample_probdist(
                self._transitions[state], rng.random(), self._states
            )
            symbol = self._sample_probdist(
                self._outputs[state], rng.random(), self._symbols
            )
            tokens.append((symbol, state))

        return tokens

    def _sample_probdist(self, probdist, p, samples):
        cum_p = 0
        for sample in samples:
            add_p = probdist.prob(sample)
            if cum_p <= p <= cum_p + add_p:
                return sample
            cum_p += add_p
        raise Exception("Invalid probability distribution - " "does not sum to one")

    def entropy(self, unlabeled_sequence):
        """
        Returns the entropy over labellings of the given sequence. This is
        given by::

            H(O) = - sum_S Pr(S | O) log Pr(S | O)

        where the summation ranges over all state sequences, S. Let
        *Z = Pr(O) = sum_S Pr(S, O)}* where the summation ranges over all state
        sequences and O is the observation sequence. As such the entropy can
        be re-expressed as::

            H = - sum_S Pr(S | O) log [ Pr(S, O) / Z ]
            = log Z - sum_S Pr(S | O) log Pr(S, 0)
            = log Z - sum_S Pr(S | O) [ log Pr(S_0) + sum_t Pr(S_t | S_{t-1}) + sum_t Pr(O_t | S_t) ]

        The order of summation for the log terms can be flipped, allowing
        dynamic programming to be used to calculate the entropy. Specifically,
        we use the forward and backward probabilities (alpha, beta) giving::

            H = log Z - sum_s0 alpha_0(s0) beta_0(s0) / Z * log Pr(s0)
            + sum_t,si,sj alpha_t(si) Pr(sj | si) Pr(O_t+1 | sj) beta_t(sj) / Z * log Pr(sj | si)
            + sum_t,st alpha_t(st) beta_t(st) / Z * log Pr(O_t | st)

        This simply uses alpha and beta to find the probabilities of partial
        sequences, constrained to include the given state(s) at some point in
        time.
        """
        unlabeled_sequence = self._transform(unlabeled_sequence)

        T = len(unlabeled_sequence)
        N = len(self._states)

        alpha = self._forward_probability(unlabeled_sequence)
        beta = self._backward_probability(unlabeled_sequence)
        normalisation = logsumexp2(alpha[T - 1])

        entropy = normalisation

        # starting state, t = 0
        for i, state in enumerate(self._states):
            p = 2 ** (alpha[0, i] + beta[0, i] - normalisation)
            entropy -= p * self._priors.logprob(state)
            # print('p(s_0 = %s) =' % state, p)

        # state transitions
        for t0 in range(T - 1):
            t1 = t0 + 1
            for i0, s0 in enumerate(self._states):
                for i1, s1 in enumerate(self._states):
                    p = 2 ** (
                        alpha[t0, i0]
                        + self._transitions[s0].logprob(s1)
                        + self._outputs[s1].logprob(unlabeled_sequence[t1][_TEXT])
                        + beta[t1, i1]
                        - normalisation
                    )
                    entropy -= p * self._transitions[s0].logprob(s1)
                    # print('p(s_%d = %s, s_%d = %s) =' % (t0, s0, t1, s1), p)

        # symbol emissions
        for t in range(T):
            for i, state in enumerate(self._states):
                p = 2 ** (alpha[t, i] + beta[t, i] - normalisation)
                entropy -= p * self._outputs[state].logprob(
                    unlabeled_sequence[t][_TEXT]
                )
                # print('p(s_%d = %s) =' % (t, state), p)

        return entropy

    def point_entropy(self, unlabeled_sequence):
        """
        Returns the pointwise entropy over the possible states at each
        position in the chain, given the observation sequence.
        """
        unlabeled_sequence = self._transform(unlabeled_sequence)

        T = len(unlabeled_sequence)
        N = len(self._states)

        alpha = self._forward_probability(unlabeled_sequence)
        beta = self._backward_probability(unlabeled_sequence)
        normalisation = logsumexp2(alpha[T - 1])

        entropies = np.zeros(T, np.float64)
        probs = np.zeros(N, np.float64)
        for t in range(T):
            for s in range(N):
                probs[s] = alpha[t, s] + beta[t, s] - normalisation

            for s in range(N):
                entropies[t] -= 2 ** (probs[s]) * probs[s]

        return entropies

    def _exhaustive_entropy(self, unlabeled_sequence):
        unlabeled_sequence = self._transform(unlabeled_sequence)

        T = len(unlabeled_sequence)
        N = len(self._states)

        labellings = [[state] for state in self._states]
        for t in range(T - 1):
            current = labellings
            labellings = []
            for labelling in current:
                for state in self._states:
                    labellings.append(labelling + [state])

        log_probs = []
        for labelling in labellings:
            labeled_sequence = unlabeled_sequence[:]
            for t, label in enumerate(labelling):
                labeled_sequence[t] = (labeled_sequence[t][_TEXT], label)
            lp = self.log_probability(labeled_sequence)
            log_probs.append(lp)
        normalisation = _log_add(*log_probs)

        entropy = 0
        for lp in log_probs:
            lp -= normalisation
            entropy -= 2 ** (lp) * lp

        return entropy

    def _exhaustive_point_entropy(self, unlabeled_sequence):
        unlabeled_sequence = self._transform(unlabeled_sequence)

        T = len(unlabeled_sequence)
        N = len(self._states)

        labellings = [[state] for state in self._states]
        for t in range(T - 1):
            current = labellings
            labellings = []
            for labelling in current:
                for state in self._states:
                    labellings.append(labelling + [state])

        log_probs = []
        for labelling in labellings:
            labelled_sequence = unlabeled_sequence[:]
            for t, label in enumerate(labelling):
                labelled_sequence[t] = (labelled_sequence[t][_TEXT], label)
            lp = self.log_probability(labelled_sequence)
            log_probs.append(lp)

        normalisation = _log_add(*log_probs)

        probabilities = _ninf_array((T, N))

        for labelling, lp in zip(labellings, log_probs):
            lp -= normalisation
            for t, label in enumerate(labelling):
                index = self._states.index(label)
                probabilities[t, index] = _log_add(probabilities[t, index], lp)

        entropies = np.zeros(T, np.float64)
        for t in range(T):
            for s in range(N):
                entropies[t] -= 2 ** (probabilities[t, s]) * probabilities[t, s]

        return entropies

    def _transitions_matrix(self):
        """Return a matrix of transition log probabilities."""
        trans_iter = (
            self._transitions[sj].logprob(si)
            for sj in self._states
            for si in self._states
        )

        transitions_logprob = np.fromiter(trans_iter, dtype=np.float64)
        N = len(self._states)
        return transitions_logprob.reshape((N, N)).T

    def _outputs_vector(self, symbol):
        """
        Return a vector with log probabilities of emitting a symbol
        when entering states.
        """
        out_iter = (self._output_logprob(sj, symbol) for sj in self._states)
        return np.fromiter(out_iter, dtype=np.float64)

    def _forward_probability(self, unlabeled_sequence):
        """
        Return the forward probability matrix, a T by N array of
        log-probabilities, where T is the length of the sequence and N is the
        number of states. Each entry (t, s) gives the probability of being in
        state s at time t after observing the partial symbol sequence up to
        and including t.

        :param unlabeled_sequence: the sequence of unlabeled symbols
        :type unlabeled_sequence: list
        :return: the forward log probability matrix
        :rtype: array
        """
        T = len(unlabeled_sequence)
        N = len(self._states)
        alpha = _ninf_array((T, N))

        transitions_logprob = self._transitions_matrix()

        # Initialization
        symbol = unlabeled_sequence[0][_TEXT]
        for i, state in enumerate(self._states):
            alpha[0, i] = self._priors.logprob(state) + self._output_logprob(
                state, symbol
            )

        # Induction
        for t in range(1, T):
            symbol = unlabeled_sequence[t][_TEXT]
            output_logprob = self._outputs_vector(symbol)

            for i in range(N):
                summand = alpha[t - 1] + transitions_logprob[i]
                alpha[t, i] = logsumexp2(summand) + output_logprob[i]

        return alpha

    def _backward_probability(self, unlabeled_sequence):
        """
        Return the backward probability matrix, a T by N array of
        log-probabilities, where T is the length of the sequence and N is the
        number of states. Each entry (t, s) gives the probability of being in
        state s at time t after observing the partial symbol sequence from t
        .. T.

        :return: the backward log probability matrix
        :rtype:  array
        :param unlabeled_sequence: the sequence of unlabeled symbols
        :type unlabeled_sequence: list
        """
        T = len(unlabeled_sequence)
        N = len(self._states)
        beta = _ninf_array((T, N))

        transitions_logprob = self._transitions_matrix().T

        # initialise the backward values;
        # "1" is an arbitrarily chosen value from Rabiner tutorial
        beta[T - 1, :] = np.log2(1)

        # inductively calculate remaining backward values
        for t in range(T - 2, -1, -1):
            symbol = unlabeled_sequence[t + 1][_TEXT]
            outputs = self._outputs_vector(symbol)

            for i in range(N):
                summand = transitions_logprob[i] + beta[t + 1] + outputs
                beta[t, i] = logsumexp2(summand)

        return beta

    def test(self, test_sequence, verbose=False, **kwargs):
        """
        Tests the HiddenMarkovModelTagger instance.

        :param test_sequence: a sequence of labeled test instances
        :type test_sequence: list(list)
        :param verbose: boolean flag indicating whether training should be
            verbose or include printed output
        :type verbose: bool
        """

        def words(sent):
            return [word for (word, tag) in sent]

        def tags(sent):
            return [tag for (word, tag) in sent]

        def flatten(seq):
            return list(itertools.chain(*seq))

        test_sequence = self._transform(test_sequence)
        predicted_sequence = list(map(self._tag, map(words, test_sequence)))

        if verbose:
            for test_sent, predicted_sent in zip(test_sequence, predicted_sequence):
                print(
                    "Test:",
                    " ".join(f"{token}/{tag}" for (token, tag) in test_sent),
                )
                print()
                print("Untagged:", " ".join("%s" % token for (token, tag) in test_sent))
                print()
                print(
                    "HMM-tagged:",
                    " ".join(f"{token}/{tag}" for (token, tag) in predicted_sent),
                )
                print()
                print(
                    "Entropy:",
                    self.entropy([(token, None) for (token, tag) in predicted_sent]),
                )
                print()
                print("-" * 60)

        test_tags = flatten(map(tags, test_sequence))
        predicted_tags = flatten(map(tags, predicted_sequence))

        acc = accuracy(test_tags, predicted_tags)
        count = sum(len(sent) for sent in test_sequence)
        print("accuracy over %d tokens: %.2f" % (count, acc * 100))

    def __repr__(self):
        return "<HiddenMarkovModelTagger %d states and %d output symbols>" % (
            len(self._states),
            len(self._symbols),
        )


class HiddenMarkovModelTrainer:
    """
    Algorithms for learning HMM parameters from training data. These include
    both supervised learning (MLE) and unsupervised learning (Baum-Welch).

    Creates an HMM trainer to induce an HMM with the given states and
    output symbol alphabet. A supervised and unsupervised training
    method may be used. If either of the states or symbols are not given,
    these may be derived from supervised training.

    :param states:  the set of state labels
    :type states:   sequence of any
    :param symbols: the set of observation symbols
    :type symbols:  sequence of any
    """

    def __init__(self, states=None, symbols=None):
        self._states = states if states else []
        self._symbols = symbols if symbols else []

    def train(self, labeled_sequences=None, unlabeled_sequences=None, **kwargs):
        """
        Trains the HMM using both (or either of) supervised and unsupervised
        techniques.

        :return: the trained model
        :rtype: HiddenMarkovModelTagger
        :param labelled_sequences: the supervised training data, a set of
            labelled sequences of observations
            ex: [ (word_1, tag_1),...,(word_n,tag_n) ]
        :type labelled_sequences: list
        :param unlabeled_sequences: the unsupervised training data, a set of
            sequences of observations
            ex: [ word_1, ..., word_n ]
        :type unlabeled_sequences: list
        :param kwargs: additional arguments to pass to the training methods
        """
        assert labeled_sequences or unlabeled_sequences
        model = None
        if labeled_sequences:
            model = self.train_supervised(labeled_sequences, **kwargs)
        if unlabeled_sequences:
            if model:
                kwargs["model"] = model
            model = self.train_unsupervised(unlabeled_sequences, **kwargs)
        return model

    def _baum_welch_step(self, sequence, model, symbol_to_number):
        N = len(model._states)
        M = len(model._symbols)
        T = len(sequence)

        # compute forward and backward probabilities
        alpha = model._forward_probability(sequence)
        beta = model._backward_probability(sequence)

        # find the log probability of the sequence
        lpk = logsumexp2(alpha[T - 1])

        A_numer = _ninf_array((N, N))
        B_numer = _ninf_array((N, M))
        A_denom = _ninf_array(N)
        B_denom = _ninf_array(N)

        transitions_logprob = model._transitions_matrix().T

        for t in range(T):
            symbol = sequence[t][_TEXT]  # not found? FIXME
            next_symbol = None
            if t < T - 1:
                next_symbol = sequence[t + 1][_TEXT]  # not found? FIXME
            xi = symbol_to_number[symbol]

            next_outputs_logprob = model._outputs_vector(next_symbol)
            alpha_plus_beta = alpha[t] + beta[t]

            if t < T - 1:
                numer_add = (
                    transitions_logprob
                    + next_outputs_logprob
                    + beta[t + 1]
                    + alpha[t].reshape(N, 1)
                )
                A_numer = np.logaddexp2(A_numer, numer_add)
                A_denom = np.logaddexp2(A_denom, alpha_plus_beta)
            else:
                B_denom = np.logaddexp2(A_denom, alpha_plus_beta)

            B_numer[:, xi] = np.logaddexp2(B_numer[:, xi], alpha_plus_beta)

        return lpk, A_numer, A_denom, B_numer, B_denom

    def train_unsupervised(self, unlabeled_sequences, update_outputs=True, **kwargs):
        """
        Trains the HMM using the Baum-Welch algorithm to maximise the
        probability of the data sequence. This is a variant of the EM
        algorithm, and is unsupervised in that it doesn't need the state
        sequences for the symbols. The code is based on 'A Tutorial on Hidden
        Markov Models and Selected Applications in Speech Recognition',
        Lawrence Rabiner, IEEE, 1989.

        :return: the trained model
        :rtype: HiddenMarkovModelTagger
        :param unlabeled_sequences: the training data, a set of
            sequences of observations
        :type unlabeled_sequences: list

        kwargs may include following parameters:

        :param model: a HiddenMarkovModelTagger instance used to begin
            the Baum-Welch algorithm
        :param max_iterations: the maximum number of EM iterations
        :param convergence_logprob: the maximum change in log probability to
            allow convergence
        """

        # create a uniform HMM, which will be iteratively refined, unless
        # given an existing model
        model = kwargs.get("model")
        if not model:
            priors = RandomProbDist(self._states)
            transitions = DictionaryConditionalProbDist(
                {state: RandomProbDist(self._states) for state in self._states}
            )
            outputs = DictionaryConditionalProbDist(
                {state: RandomProbDist(self._symbols) for state in self._states}
            )
            model = HiddenMarkovModelTagger(
                self._symbols, self._states, transitions, outputs, priors
            )

        self._states = model._states
        self._symbols = model._symbols

        N = len(self._states)
        M = len(self._symbols)
        symbol_numbers = {sym: i for i, sym in enumerate(self._symbols)}

        # update model prob dists so that they can be modified
        # model._priors = MutableProbDist(model._priors, self._states)

        model._transitions = DictionaryConditionalProbDist(
            {
                s: MutableProbDist(model._transitions[s], self._states)
                for s in self._states
            }
        )

        if update_outputs:
            model._outputs = DictionaryConditionalProbDist(
                {
                    s: MutableProbDist(model._outputs[s], self._symbols)
                    for s in self._states
                }
            )

        model.reset_cache()

        # iterate until convergence
        converged = False
        last_logprob = None
        iteration = 0
        max_iterations = kwargs.get("max_iterations", 1000)
        epsilon = kwargs.get("convergence_logprob", 1e-6)

        while not converged and iteration < max_iterations:
            A_numer = _ninf_array((N, N))
            B_numer = _ninf_array((N, M))
            A_denom = _ninf_array(N)
            B_denom = _ninf_array(N)

            logprob = 0
            for sequence in unlabeled_sequences:
                sequence = list(sequence)
                if not sequence:
                    continue

                (
                    lpk,
                    seq_A_numer,
                    seq_A_denom,
                    seq_B_numer,
                    seq_B_denom,
                ) = self._baum_welch_step(sequence, model, symbol_numbers)

                # add these sums to the global A and B values
                for i in range(N):
                    A_numer[i] = np.logaddexp2(A_numer[i], seq_A_numer[i] - lpk)
                    B_numer[i] = np.logaddexp2(B_numer[i], seq_B_numer[i] - lpk)

                A_denom = np.logaddexp2(A_denom, seq_A_denom - lpk)
                B_denom = np.logaddexp2(B_denom, seq_B_denom - lpk)

                logprob += lpk

            # use the calculated values to update the transition and output
            # probability values
            for i in range(N):
                logprob_Ai = A_numer[i] - A_denom[i]
                logprob_Bi = B_numer[i] - B_denom[i]

                # We should normalize all probabilities (see p.391 Huang et al)
                # Let sum(P) be K.
                # We can divide each Pi by K to make sum(P) == 1.
                #   Pi' = Pi/K
                #   log2(Pi') = log2(Pi) - log2(K)
                logprob_Ai -= logsumexp2(logprob_Ai)
                logprob_Bi -= logsumexp2(logprob_Bi)

                # update output and transition probabilities
                si = self._states[i]

                for j in range(N):
                    sj = self._states[j]
                    model._transitions[si].update(sj, logprob_Ai[j])

                if update_outputs:
                    for k in range(M):
                        ok = self._symbols[k]
                        model._outputs[si].update(ok, logprob_Bi[k])

                # Rabiner says the priors don't need to be updated. I don't
                # believe him. FIXME

            # test for convergence
            if iteration > 0 and abs(logprob - last_logprob) < epsilon:
                converged = True

            print("iteration", iteration, "logprob", logprob)
            iteration += 1
            last_logprob = logprob

        return model

    def train_supervised(self, labelled_sequences, estimator=None):
        """
        Supervised training maximising the joint probability of the symbol and
        state sequences. This is done via collecting frequencies of
        transitions between states, symbol observations while within each
        state and which states start a sentence. These frequency distributions
        are then normalised into probability estimates, which can be
        smoothed if desired.

        :return: the trained model
        :rtype: HiddenMarkovModelTagger
        :param labelled_sequences: the training data, a set of
            labelled sequences of observations
        :type labelled_sequences: list
        :param estimator: a function taking
            a FreqDist and a number of bins and returning a CProbDistI;
            otherwise a MLE estimate is used
        """

        # default to the MLE estimate
        if estimator is None:
            estimator = lambda fdist, bins: MLEProbDist(fdist)

        # count occurrences of starting states, transitions out of each state
        # and output symbols observed in each state
        known_symbols = set(self._symbols)
        known_states = set(self._states)

        starting = FreqDist()
        transitions = ConditionalFreqDist()
        outputs = ConditionalFreqDist()
        for sequence in labelled_sequences:
            lasts = None
            for token in sequence:
                state = token[_TAG]
                symbol = token[_TEXT]
                if lasts is None:
                    starting[state] += 1
                else:
                    transitions[lasts][state] += 1
                outputs[state][symbol] += 1
                lasts = state

                # update the state and symbol lists
                if state not in known_states:
                    self._states.append(state)
                    known_states.add(state)

                if symbol not in known_symbols:
                    self._symbols.append(symbol)
                    known_symbols.add(symbol)

        # create probability distributions (with smoothing)
        N = len(self._states)
        pi = estimator(starting, N)
        A = ConditionalProbDist(transitions, estimator, N)
        B = ConditionalProbDist(outputs, estimator, len(self._symbols))

        return HiddenMarkovModelTagger(self._symbols, self._states, A, B, pi)


def _ninf_array(shape):
    res = np.empty(shape, np.float64)
    res.fill(-np.inf)
    return res


def logsumexp2(arr):
    max_ = arr.max()
    return np.log2(np.sum(2 ** (arr - max_))) + max_


def _log_add(*values):
    """
    Adds the logged values, returning the logarithm of the addition.
    """
    x = max(values)
    if x > -np.inf:
        sum_diffs = 0
        for value in values:
            sum_diffs += 2 ** (value - x)
        return x + np.log2(sum_diffs)
    else:
        return x


def _create_hmm_tagger(states, symbols, A, B, pi):
    def pd(values, samples):
        d = dict(zip(samples, values))
        return DictionaryProbDist(d)

    def cpd(array, conditions, samples):
        d = {}
        for values, condition in zip(array, conditions):
            d[condition] = pd(values, samples)
        return DictionaryConditionalProbDist(d)

    A = cpd(A, states, states)
    B = cpd(B, states, symbols)
    pi = pd(pi, states)
    return HiddenMarkovModelTagger(
        symbols=symbols, states=states, transitions=A, outputs=B, priors=pi
    )


def _market_hmm_example():
    """
    Return an example HMM (described at page 381, Huang et al)
    """
    states = ["bull", "bear", "static"]
    symbols = ["up", "down", "unchanged"]
    A = np.array([[0.6, 0.2, 0.2], [0.5, 0.3, 0.2], [0.4, 0.1, 0.5]], np.float64)
    B = np.array([[0.7, 0.1, 0.2], [0.1, 0.6, 0.3], [0.3, 0.3, 0.4]], np.float64)
    pi = np.array([0.5, 0.2, 0.3], np.float64)

    model = _create_hmm_tagger(states, symbols, A, B, pi)
    return model, states, symbols


def demo():
    # demonstrates HMM probability calculation

    print()
    print("HMM probability calculation demo")
    print()

    model, states, symbols = _market_hmm_example()

    print("Testing", model)

    for test in [
        ["up", "up"],
        ["up", "down", "up"],
        ["down"] * 5,
        ["unchanged"] * 5 + ["up"],
    ]:
        sequence = [(t, None) for t in test]

        print("Testing with state sequence", test)
        print("probability =", model.probability(sequence))
        print("tagging =    ", model.tag([word for (word, tag) in sequence]))
        print("p(tagged) =  ", model.probability(sequence))
        print("H =          ", model.entropy(sequence))
        print("H_exh =      ", model._exhaustive_entropy(sequence))
        print("H(point) =   ", model.point_entropy(sequence))
        print("H_exh(point)=", model._exhaustive_point_entropy(sequence))
        print()


def load_pos(num_sents):
    from nltk.corpus import brown

    sentences = brown.tagged_sents(categories="news")[:num_sents]

    tag_re = re.compile(r"[*]|--|[^+*-]+")
    tag_set = set()
    symbols = set()

    cleaned_sentences = []
    for sentence in sentences:
        for i in range(len(sentence)):
            word, tag = sentence[i]
            word = word.lower()  # normalize
            symbols.add(word)  # log this word
            # Clean up the tag.
            tag = tag_re.match(tag).group()
            tag_set.add(tag)
            sentence[i] = (word, tag)  # store cleaned-up tagged token
        cleaned_sentences += [sentence]

    return cleaned_sentences, list(tag_set), list(symbols)


def demo_pos():
    # demonstrates POS tagging using supervised training

    print()
    print("HMM POS tagging demo")
    print()

    print("Training HMM...")
    labelled_sequences, tag_set, symbols = load_pos(20000)
    trainer = HiddenMarkovModelTrainer(tag_set, symbols)
    hmm = trainer.train_supervised(
        labelled_sequences[10:],
        estimator=lambda fd, bins: LidstoneProbDist(fd, 0.1, bins),
    )

    print("Testing...")
    hmm.test(labelled_sequences[:10], verbose=True)


def _untag(sentences):
    unlabeled = []
    for sentence in sentences:
        unlabeled.append([(token[_TEXT], None) for token in sentence])
    return unlabeled


def demo_pos_bw(
    test=10, supervised=20, unsupervised=10, verbose=True, max_iterations=5
):
    # demonstrates the Baum-Welch algorithm in POS tagging

    print()
    print("Baum-Welch demo for POS tagging")
    print()

    print("Training HMM (supervised, %d sentences)..." % supervised)

    sentences, tag_set, symbols = load_pos(test + supervised + unsupervised)

    symbols = set()
    for sentence in sentences:
        for token in sentence:
            symbols.add(token[_TEXT])

    trainer = HiddenMarkovModelTrainer(tag_set, list(symbols))
    hmm = trainer.train_supervised(
        sentences[test : test + supervised],
        estimator=lambda fd, bins: LidstoneProbDist(fd, 0.1, bins),
    )

    hmm.test(sentences[:test], verbose=verbose)

    print("Training (unsupervised, %d sentences)..." % unsupervised)
    # it's rather slow - so only use 10 samples by default
    unlabeled = _untag(sentences[test + supervised :])
    hmm = trainer.train_unsupervised(
        unlabeled, model=hmm, max_iterations=max_iterations
    )
    hmm.test(sentences[:test], verbose=verbose)


def demo_bw():
    # demo Baum Welch by generating some sequences and then performing
    # unsupervised training on them

    print()
    print("Baum-Welch demo for market example")
    print()

    model, states, symbols = _market_hmm_example()

    # generate some random sequences
    training = []
    import random

    rng = random.Random()
    rng.seed(0)
    for i in range(10):
        item = model.random_sample(rng, 5)
        training.append([(i[0], None) for i in item])

    # train on those examples, starting with the model that generated them
    trainer = HiddenMarkovModelTrainer(states, symbols)
    hmm = trainer.train_unsupervised(training, model=model, max_iterations=1000)

# === NexusCore/openenv\Lib\site-packages\parso\python\errors.py ===
# -*- coding: utf-8 -*-
import codecs
import sys
import warnings
import re
from contextlib import contextmanager

from parso.normalizer import Normalizer, NormalizerConfig, Issue, Rule
from parso.python.tokenize import _get_token_collection

_BLOCK_STMTS = ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt')
_STAR_EXPR_PARENTS = ('testlist_star_expr', 'testlist_comp', 'exprlist')
# This is the maximal block size given by python.
_MAX_BLOCK_SIZE = 20
_MAX_INDENT_COUNT = 100
ALLOWED_FUTURES = (
    'nested_scopes', 'generators', 'division', 'absolute_import',
    'with_statement', 'print_function', 'unicode_literals', 'generator_stop',
)
_COMP_FOR_TYPES = ('comp_for', 'sync_comp_for')


def _get_rhs_name(node, version):
    type_ = node.type
    if type_ == "lambdef":
        return "lambda"
    elif type_ == "atom":
        comprehension = _get_comprehension_type(node)
        first, second = node.children[:2]
        if comprehension is not None:
            return comprehension
        elif second.type == "dictorsetmaker":
            if version < (3, 8):
                return "literal"
            else:
                if second.children[1] == ":" or second.children[0] == "**":
                    if version < (3, 10):
                        return "dict display"
                    else:
                        return "dict literal"
                else:
                    return "set display"
        elif (
            first == "("
            and (second == ")"
                 or (len(node.children) == 3 and node.children[1].type == "testlist_comp"))
        ):
            return "tuple"
        elif first == "(":
            return _get_rhs_name(_remove_parens(node), version=version)
        elif first == "[":
            return "list"
        elif first == "{" and second == "}":
            if version < (3, 10):
                return "dict display"
            else:
                return "dict literal"
        elif first == "{" and len(node.children) > 2:
            return "set display"
    elif type_ == "keyword":
        if "yield" in node.value:
            return "yield expression"
        if version < (3, 8):
            return "keyword"
        else:
            return str(node.value)
    elif type_ == "operator" and node.value == "...":
        if version < (3, 10):
            return "Ellipsis"
        else:
            return "ellipsis"
    elif type_ == "comparison":
        return "comparison"
    elif type_ in ("string", "number", "strings"):
        return "literal"
    elif type_ == "yield_expr":
        return "yield expression"
    elif type_ == "test":
        return "conditional expression"
    elif type_ in ("atom_expr", "power"):
        if node.children[0] == "await":
            return "await expression"
        elif node.children[-1].type == "trailer":
            trailer = node.children[-1]
            if trailer.children[0] == "(":
                return "function call"
            elif trailer.children[0] == "[":
                return "subscript"
            elif trailer.children[0] == ".":
                return "attribute"
    elif (
        ("expr" in type_ and "star_expr" not in type_)  # is a substring
        or "_test" in type_
        or type_ in ("term", "factor")
    ):
        if version < (3, 10):
            return "operator"
        else:
            return "expression"
    elif type_ == "star_expr":
        return "starred"
    elif type_ == "testlist_star_expr":
        return "tuple"
    elif type_ == "fstring":
        return "f-string expression"
    return type_  # shouldn't reach here


def _iter_stmts(scope):
    """
    Iterates over all statements and splits up  simple_stmt.
    """
    for child in scope.children:
        if child.type == 'simple_stmt':
            for child2 in child.children:
                if child2.type == 'newline' or child2 == ';':
                    continue
                yield child2
        else:
            yield child


def _get_comprehension_type(atom):
    first, second = atom.children[:2]
    if second.type == 'testlist_comp' and second.children[1].type in _COMP_FOR_TYPES:
        if first == '[':
            return 'list comprehension'
        else:
            return 'generator expression'
    elif second.type == 'dictorsetmaker' and second.children[-1].type in _COMP_FOR_TYPES:
        if second.children[1] == ':':
            return 'dict comprehension'
        else:
            return 'set comprehension'
    return None


def _is_future_import(import_from):
    # It looks like a __future__ import that is relative is still a future
    # import. That feels kind of odd, but whatever.
    # if import_from.level != 0:
    #     return False
    from_names = import_from.get_from_names()
    return [n.value for n in from_names] == ['__future__']


def _remove_parens(atom):
    """
    Returns the inner part of an expression like `(foo)`. Also removes nested
    parens.
    """
    try:
        children = atom.children
    except AttributeError:
        pass
    else:
        if len(children) == 3 and children[0] == '(':
            return _remove_parens(atom.children[1])
    return atom


def _skip_parens_bottom_up(node):
    """
    Returns an ancestor node of an expression, skipping all levels of parens
    bottom-up.
    """
    while node.parent is not None:
        node = node.parent
        if node.type != 'atom' or node.children[0] != '(':
            return node
    return None


def _iter_params(parent_node):
    return (n for n in parent_node.children if n.type == 'param' or n.type == 'operator')


def _is_future_import_first(import_from):
    """
    Checks if the import is the first statement of a file.
    """
    found_docstring = False
    for stmt in _iter_stmts(import_from.get_root_node()):
        if stmt.type == 'string' and not found_docstring:
            continue
        found_docstring = True

        if stmt == import_from:
            return True
        if stmt.type == 'import_from' and _is_future_import(stmt):
            continue
        return False


def _iter_definition_exprs_from_lists(exprlist):
    def check_expr(child):
        if child.type == 'atom':
            if child.children[0] == '(':
                testlist_comp = child.children[1]
                if testlist_comp.type == 'testlist_comp':
                    yield from _iter_definition_exprs_from_lists(testlist_comp)
                    return
                else:
                    # It's a paren that doesn't do anything, like 1 + (1)
                    yield from check_expr(testlist_comp)
                    return
            elif child.children[0] == '[':
                yield testlist_comp
                return
        yield child

    if exprlist.type in _STAR_EXPR_PARENTS:
        for child in exprlist.children[::2]:
            yield from check_expr(child)
    else:
        yield from check_expr(exprlist)


def _get_expr_stmt_definition_exprs(expr_stmt):
    exprs = []
    for list_ in expr_stmt.children[:-2:2]:
        if list_.type in ('testlist_star_expr', 'testlist'):
            exprs += _iter_definition_exprs_from_lists(list_)
        else:
            exprs.append(list_)
    return exprs


def _get_for_stmt_definition_exprs(for_stmt):
    exprlist = for_stmt.children[1]
    return list(_iter_definition_exprs_from_lists(exprlist))


def _is_argument_comprehension(argument):
    return argument.children[1].type in _COMP_FOR_TYPES


def _any_fstring_error(version, node):
    if version < (3, 9) or node is None:
        return False
    if node.type == "error_node":
        return any(child.type == "fstring_start" for child in node.children)
    elif node.type == "fstring":
        return True
    else:
        return node.search_ancestor("fstring")


class _Context:
    def __init__(self, node, add_syntax_error, parent_context=None):
        self.node = node
        self.blocks = []
        self.parent_context = parent_context
        self._used_name_dict = {}
        self._global_names = []
        self._local_params_names = []
        self._nonlocal_names = []
        self._nonlocal_names_in_subscopes = []
        self._add_syntax_error = add_syntax_error

    def is_async_funcdef(self):
        # Stupidly enough async funcdefs can have two different forms,
        # depending if a decorator is used or not.
        return self.is_function() \
            and self.node.parent.type in ('async_funcdef', 'async_stmt')

    def is_function(self):
        return self.node.type == 'funcdef'

    def add_name(self, name):
        parent_type = name.parent.type
        if parent_type == 'trailer':
            # We are only interested in first level names.
            return

        if parent_type == 'global_stmt':
            self._global_names.append(name)
        elif parent_type == 'nonlocal_stmt':
            self._nonlocal_names.append(name)
        elif parent_type == 'funcdef':
            self._local_params_names.extend(
                [param.name.value for param in name.parent.get_params()]
            )
        else:
            self._used_name_dict.setdefault(name.value, []).append(name)

    def finalize(self):
        """
        Returns a list of nonlocal names that need to be part of that scope.
        """
        self._analyze_names(self._global_names, 'global')
        self._analyze_names(self._nonlocal_names, 'nonlocal')

        global_name_strs = {n.value: n for n in self._global_names}
        for nonlocal_name in self._nonlocal_names:
            try:
                global_name = global_name_strs[nonlocal_name.value]
            except KeyError:
                continue

            message = "name '%s' is nonlocal and global" % global_name.value
            if global_name.start_pos < nonlocal_name.start_pos:
                error_name = global_name
            else:
                error_name = nonlocal_name
            self._add_syntax_error(error_name, message)

        nonlocals_not_handled = []
        for nonlocal_name in self._nonlocal_names_in_subscopes:
            search = nonlocal_name.value
            if search in self._local_params_names:
                continue
            if search in global_name_strs or self.parent_context is None:
                message = "no binding for nonlocal '%s' found" % nonlocal_name.value
                self._add_syntax_error(nonlocal_name, message)
            elif not self.is_function() or \
                    nonlocal_name.value not in self._used_name_dict:
                nonlocals_not_handled.append(nonlocal_name)
        return self._nonlocal_names + nonlocals_not_handled

    def _analyze_names(self, globals_or_nonlocals, type_):
        def raise_(message):
            self._add_syntax_error(base_name, message % (base_name.value, type_))

        params = []
        if self.node.type == 'funcdef':
            params = self.node.get_params()

        for base_name in globals_or_nonlocals:
            found_global_or_nonlocal = False
            # Somehow Python does it the reversed way.
            for name in reversed(self._used_name_dict.get(base_name.value, [])):
                if name.start_pos > base_name.start_pos:
                    # All following names don't have to be checked.
                    found_global_or_nonlocal = True

                parent = name.parent
                if parent.type == 'param' and parent.name == name:
                    # Skip those here, these definitions belong to the next
                    # scope.
                    continue

                if name.is_definition():
                    if parent.type == 'expr_stmt' \
                            and parent.children[1].type == 'annassign':
                        if found_global_or_nonlocal:
                            # If it's after the global the error seems to be
                            # placed there.
                            base_name = name
                        raise_("annotated name '%s' can't be %s")
                        break
                    else:
                        message = "name '%s' is assigned to before %s declaration"
                else:
                    message = "name '%s' is used prior to %s declaration"

                if not found_global_or_nonlocal:
                    raise_(message)
                    # Only add an error for the first occurence.
                    break

            for param in params:
                if param.name.value == base_name.value:
                    raise_("name '%s' is parameter and %s"),

    @contextmanager
    def add_block(self, node):
        self.blocks.append(node)
        yield
        self.blocks.pop()

    def add_context(self, node):
        return _Context(node, self._add_syntax_error, parent_context=self)

    def close_child_context(self, child_context):
        self._nonlocal_names_in_subscopes += child_context.finalize()


class ErrorFinder(Normalizer):
    """
    Searches for errors in the syntax tree.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_dict = {}
        self.version = self.grammar.version_info

    def initialize(self, node):
        def create_context(node):
            if node is None:
                return None

            parent_context = create_context(node.parent)
            if node.type in ('classdef', 'funcdef', 'file_input'):
                return _Context(node, self._add_syntax_error, parent_context)
            return parent_context

        self.context = create_context(node) or _Context(node, self._add_syntax_error)
        self._indentation_count = 0

    def visit(self, node):
        if node.type == 'error_node':
            with self.visit_node(node):
                # Don't need to investigate the inners of an error node. We
                # might find errors in there that should be ignored, because
                # the error node itself already shows that there's an issue.
                return ''
        return super().visit(node)

    @contextmanager
    def visit_node(self, node):
        self._check_type_rules(node)

        if node.type in _BLOCK_STMTS:
            with self.context.add_block(node):
                if len(self.context.blocks) == _MAX_BLOCK_SIZE:
                    self._add_syntax_error(node, "too many statically nested blocks")
                yield
            return
        elif node.type == 'suite':
            self._indentation_count += 1
            if self._indentation_count == _MAX_INDENT_COUNT:
                self._add_indentation_error(node.children[1], "too many levels of indentation")

        yield

        if node.type == 'suite':
            self._indentation_count -= 1
        elif node.type in ('classdef', 'funcdef'):
            context = self.context
            self.context = context.parent_context
            self.context.close_child_context(context)

    def visit_leaf(self, leaf):
        if leaf.type == 'error_leaf':
            if leaf.token_type in ('INDENT', 'ERROR_DEDENT'):
                # Indents/Dedents itself never have a prefix. They are just
                # "pseudo" tokens that get removed by the syntax tree later.
                # Therefore in case of an error we also have to check for this.
                spacing = list(leaf.get_next_leaf()._split_prefix())[-1]
                if leaf.token_type == 'INDENT':
                    message = 'unexpected indent'
                else:
                    message = 'unindent does not match any outer indentation level'
                self._add_indentation_error(spacing, message)
            else:
                if leaf.value.startswith('\\'):
                    message = 'unexpected character after line continuation character'
                else:
                    match = re.match('\\w{,2}("{1,3}|\'{1,3})', leaf.value)
                    if match is None:
                        message = 'invalid syntax'
                        if (
                            self.version >= (3, 9)
                            and leaf.value in _get_token_collection(
                                self.version
                            ).always_break_tokens
                        ):
                            message = "f-string: " + message
                    else:
                        if len(match.group(1)) == 1:
                            message = 'EOL while scanning string literal'
                        else:
                            message = 'EOF while scanning triple-quoted string literal'
                self._add_syntax_error(leaf, message)
            return ''
        elif leaf.value == ':':
            parent = leaf.parent
            if parent.type in ('classdef', 'funcdef'):
                self.context = self.context.add_context(parent)

        # The rest is rule based.
        return super().visit_leaf(leaf)

    def _add_indentation_error(self, spacing, message):
        self.add_issue(spacing, 903, "IndentationError: " + message)

    def _add_syntax_error(self, node, message):
        self.add_issue(node, 901, "SyntaxError: " + message)

    def add_issue(self, node, code, message):
        # Overwrite the default behavior.
        # Check if the issues are on the same line.
        line = node.start_pos[0]
        args = (code, message, node)
        self._error_dict.setdefault(line, args)

    def finalize(self):
        self.context.finalize()

        for code, message, node in self._error_dict.values():
            self.issues.append(Issue(node, code, message))


class IndentationRule(Rule):
    code = 903

    def _get_message(self, message, node):
        message = super()._get_message(message, node)
        return "IndentationError: " + message


@ErrorFinder.register_rule(type='error_node')
class _ExpectIndentedBlock(IndentationRule):
    message = 'expected an indented block'

    def get_node(self, node):
        leaf = node.get_next_leaf()
        return list(leaf._split_prefix())[-1]

    def is_issue(self, node):
        # This is the beginning of a suite that is not indented.
        return node.children[-1].type == 'newline'


class ErrorFinderConfig(NormalizerConfig):
    normalizer_class = ErrorFinder


class SyntaxRule(Rule):
    code = 901

    def _get_message(self, message, node):
        message = super()._get_message(message, node)
        if (
            "f-string" not in message
            and _any_fstring_error(self._normalizer.version, node)
        ):
            message = "f-string: " + message
        return "SyntaxError: " + message


@ErrorFinder.register_rule(type='error_node')
class _InvalidSyntaxRule(SyntaxRule):
    message = "invalid syntax"
    fstring_message = "f-string: invalid syntax"

    def get_node(self, node):
        return node.get_next_leaf()

    def is_issue(self, node):
        error = node.get_next_leaf().type != 'error_leaf'
        if (
            error
            and _any_fstring_error(self._normalizer.version, node)
        ):
            self.add_issue(node, message=self.fstring_message)
        else:
            # Error leafs will be added later as an error.
            return error


@ErrorFinder.register_rule(value='await')
class _AwaitOutsideAsync(SyntaxRule):
    message = "'await' outside async function"

    def is_issue(self, leaf):
        return not self._normalizer.context.is_async_funcdef()

    def get_error_node(self, node):
        # Return the whole await statement.
        return node.parent


@ErrorFinder.register_rule(value='break')
class _BreakOutsideLoop(SyntaxRule):
    message = "'break' outside loop"

    def is_issue(self, leaf):
        in_loop = False
        for block in self._normalizer.context.blocks:
            if block.type in ('for_stmt', 'while_stmt'):
                in_loop = True
        return not in_loop


@ErrorFinder.register_rule(value='continue')
class _ContinueChecks(SyntaxRule):
    message = "'continue' not properly in loop"
    message_in_finally = "'continue' not supported inside 'finally' clause"

    def is_issue(self, leaf):
        in_loop = False
        for block in self._normalizer.context.blocks:
            if block.type in ('for_stmt', 'while_stmt'):
                in_loop = True
            if block.type == 'try_stmt':
                last_block = block.children[-3]
                if (
                    last_block == "finally"
                    and leaf.start_pos > last_block.start_pos
                    and self._normalizer.version < (3, 8)
                ):
                    self.add_issue(leaf, message=self.message_in_finally)
                    return False  # Error already added
        if not in_loop:
            return True


@ErrorFinder.register_rule(value='from')
class _YieldFromCheck(SyntaxRule):
    message = "'yield from' inside async function"

    def get_node(self, leaf):
        return leaf.parent.parent  # This is the actual yield statement.

    def is_issue(self, leaf):
        return leaf.parent.type == 'yield_arg' \
            and self._normalizer.context.is_async_funcdef()


@ErrorFinder.register_rule(type='name')
class _NameChecks(SyntaxRule):
    message = 'cannot assign to __debug__'
    message_none = 'cannot assign to None'

    def is_issue(self, leaf):
        self._normalizer.context.add_name(leaf)

        if leaf.value == '__debug__' and leaf.is_definition():
            return True


@ErrorFinder.register_rule(type='string')
class _StringChecks(SyntaxRule):
    if sys.version_info < (3, 10):
        message = "bytes can only contain ASCII literal characters."
    else:
        message = "bytes can only contain ASCII literal characters"

    def is_issue(self, leaf):
        string_prefix = leaf.string_prefix.lower()
        if 'b' in string_prefix \
                and any(c for c in leaf.value if ord(c) > 127):
            # b'ä'
            return True

        if 'r' not in string_prefix:
            # Raw strings don't need to be checked if they have proper
            # escaping.

            payload = leaf._get_payload()
            if 'b' in string_prefix:
                payload = payload.encode('utf-8')
                func = codecs.escape_decode
            else:
                func = codecs.unicode_escape_decode

            try:
                with warnings.catch_warnings():
                    # The warnings from parsing strings are not relevant.
                    warnings.filterwarnings('ignore')
                    func(payload)
            except UnicodeDecodeError as e:
                self.add_issue(leaf, message='(unicode error) ' + str(e))
            except ValueError as e:
                self.add_issue(leaf, message='(value error) ' + str(e))


@ErrorFinder.register_rule(value='*')
class _StarCheck(SyntaxRule):
    message = "named arguments must follow bare *"

    def is_issue(self, leaf):
        params = leaf.parent
        if params.type == 'parameters' and params:
            after = params.children[params.children.index(leaf) + 1:]
            after = [child for child in after
                     if child not in (',', ')') and not child.star_count]
            return len(after) == 0


@ErrorFinder.register_rule(value='**')
class _StarStarCheck(SyntaxRule):
    # e.g. {**{} for a in [1]}
    # TODO this should probably get a better end_pos including
    #      the next sibling of leaf.
    message = "dict unpacking cannot be used in dict comprehension"

    def is_issue(self, leaf):
        if leaf.parent.type == 'dictorsetmaker':
            comp_for = leaf.get_next_sibling().get_next_sibling()
            return comp_for is not None and comp_for.type in _COMP_FOR_TYPES


@ErrorFinder.register_rule(value='yield')
@ErrorFinder.register_rule(value='return')
class _ReturnAndYieldChecks(SyntaxRule):
    message = "'return' with value in async generator"
    message_async_yield = "'yield' inside async function"

    def get_node(self, leaf):
        return leaf.parent

    def is_issue(self, leaf):
        if self._normalizer.context.node.type != 'funcdef':
            self.add_issue(self.get_node(leaf), message="'%s' outside function" % leaf.value)
        elif self._normalizer.context.is_async_funcdef() \
                and any(self._normalizer.context.node.iter_yield_exprs()):
            if leaf.value == 'return' and leaf.parent.type == 'return_stmt':
                return True


@ErrorFinder.register_rule(type='strings')
class _BytesAndStringMix(SyntaxRule):
    # e.g. 's' b''
    message = "cannot mix bytes and nonbytes literals"

    def _is_bytes_literal(self, string):
        if string.type == 'fstring':
            return False
        return 'b' in string.string_prefix.lower()

    def is_issue(self, node):
        first = node.children[0]
        first_is_bytes = self._is_bytes_literal(first)
        for string in node.children[1:]:
            if first_is_bytes != self._is_bytes_literal(string):
                return True


@ErrorFinder.register_rule(type='import_as_names')
class _TrailingImportComma(SyntaxRule):
    # e.g. from foo import a,
    message = "trailing comma not allowed without surrounding parentheses"

    def is_issue(self, node):
        if node.children[-1] == ',' and node.parent.children[-1] != ')':
            return True


@ErrorFinder.register_rule(type='import_from')
class _ImportStarInFunction(SyntaxRule):
    message = "import * only allowed at module level"

    def is_issue(self, node):
        return node.is_star_import() and self._normalizer.context.parent_context is not None


@ErrorFinder.register_rule(type='import_from')
class _FutureImportRule(SyntaxRule):
    message = "from __future__ imports must occur at the beginning of the file"

    def is_issue(self, node):
        if _is_future_import(node):
            if not _is_future_import_first(node):
                return True

            for from_name, future_name in node.get_paths():
                name = future_name.value
                allowed_futures = list(ALLOWED_FUTURES)
                if self._normalizer.version >= (3, 7):
                    allowed_futures.append('annotations')
                if name == 'braces':
                    self.add_issue(node, message="not a chance")
                elif name == 'barry_as_FLUFL':
                    m = "Seriously I'm not implementing this :) ~ Dave"
                    self.add_issue(node, message=m)
                elif name not in allowed_futures:
                    message = "future feature %s is not defined" % name
                    self.add_issue(node, message=message)


@ErrorFinder.register_rule(type='star_expr')
class _StarExprRule(SyntaxRule):
    message_iterable_unpacking = "iterable unpacking cannot be used in comprehension"

    def is_issue(self, node):
        def check_delete_starred(node):
            while node.parent is not None:
                node = node.parent
                if node.type == 'del_stmt':
                    return True
                if node.type not in (*_STAR_EXPR_PARENTS, 'atom'):
                    return False
            return False

        if self._normalizer.version >= (3, 9):
            ancestor = node.parent
        else:
            ancestor = _skip_parens_bottom_up(node)
        # starred expression not in tuple/list/set
        if ancestor.type not in (*_STAR_EXPR_PARENTS, 'dictorsetmaker') \
                and not (ancestor.type == 'atom' and ancestor.children[0] != '('):
            self.add_issue(node, message="can't use starred expression here")
            return

        if check_delete_starred(node):
            if self._normalizer.version >= (3, 9):
                self.add_issue(node, message="cannot delete starred")
            else:
                self.add_issue(node, message="can't use starred expression here")
            return

        if node.parent.type == 'testlist_comp':
            # [*[] for a in [1]]
            if node.parent.children[1].type in _COMP_FOR_TYPES:
                self.add_issue(node, message=self.message_iterable_unpacking)


@ErrorFinder.register_rule(types=_STAR_EXPR_PARENTS)
class _StarExprParentRule(SyntaxRule):
    def is_issue(self, node):
        def is_definition(node, ancestor):
            if ancestor is None:
                return False

            type_ = ancestor.type
            if type_ == 'trailer':
                return False

            if type_ == 'expr_stmt':
                return node.start_pos < ancestor.children[-1].start_pos

            return is_definition(node, ancestor.parent)

        if is_definition(node, node.parent):
            args = [c for c in node.children if c != ',']
            starred = [c for c in args if c.type == 'star_expr']
            if len(starred) > 1:
                if self._normalizer.version < (3, 9):
                    message = "two starred expressions in assignment"
                else:
                    message = "multiple starred expressions in assignment"
                self.add_issue(starred[1], message=message)
            elif starred:
                count = args.index(starred[0])
                if count >= 256:
                    message = "too many expressions in star-unpacking assignment"
                    self.add_issue(starred[0], message=message)


@ErrorFinder.register_rule(type='annassign')
class _AnnotatorRule(SyntaxRule):
    # True: int
    # {}: float
    message = "illegal target for annotation"

    def get_node(self, node):
        return node.parent

    def is_issue(self, node):
        type_ = None
        lhs = node.parent.children[0]
        lhs = _remove_parens(lhs)
        try:
            children = lhs.children
        except AttributeError:
            pass
        else:
            if ',' in children or lhs.type == 'atom' and children[0] == '(':
                type_ = 'tuple'
            elif lhs.type == 'atom' and children[0] == '[':
                type_ = 'list'
            trailer = children[-1]

        if type_ is None:
            if not (lhs.type == 'name'
                    # subscript/attributes are allowed
                    or lhs.type in ('atom_expr', 'power')
                    and trailer.type == 'trailer'
                    and trailer.children[0] != '('):
                return True
        else:
            # x, y: str
            message = "only single target (not %s) can be annotated"
            self.add_issue(lhs.parent, message=message % type_)


@ErrorFinder.register_rule(type='argument')
class _ArgumentRule(SyntaxRule):
    def is_issue(self, node):
        first = node.children[0]
        if self._normalizer.version < (3, 8):
            # a((b)=c) is valid in <3.8
            first = _remove_parens(first)
        if node.children[1] == '=' and first.type != 'name':
            if first.type == 'lambdef':
                # f(lambda: 1=1)
                if self._normalizer.version < (3, 8):
                    message = "lambda cannot contain assignment"
                else:
                    message = 'expression cannot contain assignment, perhaps you meant "=="?'
            else:
                # f(+x=1)
                if self._normalizer.version < (3, 8):
                    message = "keyword can't be an expression"
                else:
                    message = 'expression cannot contain assignment, perhaps you meant "=="?'
            self.add_issue(first, message=message)

        if _is_argument_comprehension(node) and node.parent.type == 'classdef':
            self.add_issue(node, message='invalid syntax')


@ErrorFinder.register_rule(type='nonlocal_stmt')
class _NonlocalModuleLevelRule(SyntaxRule):
    message = "nonlocal declaration not allowed at module level"

    def is_issue(self, node):
        return self._normalizer.context.parent_context is None


@ErrorFinder.register_rule(type='arglist')
class _ArglistRule(SyntaxRule):
    @property
    def message(self):
        if self._normalizer.version < (3, 7):
            return "Generator expression must be parenthesized if not sole argument"
        else:
            return "Generator expression must be parenthesized"

    def is_issue(self, node):
        arg_set = set()
        kw_only = False
        kw_unpacking_only = False
        for argument in node.children:
            if argument == ',':
                continue

            if argument.type == 'argument':
                first = argument.children[0]
                if _is_argument_comprehension(argument) and len(node.children) >= 2:
                    # a(a, b for b in c)
                    return True

                if first in ('*', '**'):
                    if first == '*':
                        if kw_unpacking_only:
                            # foo(**kwargs, *args)
                            message = "iterable argument unpacking " \
                                      "follows keyword argument unpacking"
                            self.add_issue(argument, message=message)
                    else:
                        kw_unpacking_only = True
                else:  # Is a keyword argument.
                    kw_only = True
                    if first.type == 'name':
                        if first.value in arg_set:
                            # f(x=1, x=2)
                            message = "keyword argument repeated"
                            if self._normalizer.version >= (3, 9):
                                message += ": {}".format(first.value)
                            self.add_issue(first, message=message)
                        else:
                            arg_set.add(first.value)
            else:
                if kw_unpacking_only:
                    # f(**x, y)
                    message = "positional argument follows keyword argument unpacking"
                    self.add_issue(argument, message=message)
                elif kw_only:
                    # f(x=2, y)
                    message = "positional argument follows keyword argument"
                    self.add_issue(argument, message=message)


@ErrorFinder.register_rule(type='parameters')
@ErrorFinder.register_rule(type='lambdef')
class _ParameterRule(SyntaxRule):
    # def f(x=3, y): pass
    message = "non-default argument follows default argument"

    def is_issue(self, node):
        param_names = set()
        default_only = False
        star_seen = False
        for p in _iter_params(node):
            if p.type == 'operator':
                if p.value == '*':
                    star_seen = True
                    default_only = False
                continue

            if p.name.value in param_names:
                message = "duplicate argument '%s' in function definition"
                self.add_issue(p.name, message=message % p.name.value)
            param_names.add(p.name.value)

            if not star_seen:
                if p.default is None and not p.star_count:
                    if default_only:
                        return True
                elif p.star_count:
                    star_seen = True
                    default_only = False
                else:
                    default_only = True


@ErrorFinder.register_rule(type='try_stmt')
class _TryStmtRule(SyntaxRule):
    message = "default 'except:' must be last"

    def is_issue(self, try_stmt):
        default_except = None
        for except_clause in try_stmt.children[3::3]:
            if except_clause in ('else', 'finally'):
                break
            if except_clause == 'except':
                default_except = except_clause
            elif default_except is not None:
                self.add_issue(default_except, message=self.message)


@ErrorFinder.register_rule(type='fstring')
class _FStringRule(SyntaxRule):
    _fstring_grammar = None
    message_expr = "f-string expression part cannot include a backslash"
    message_nested = "f-string: expressions nested too deeply"
    message_conversion = "f-string: invalid conversion character: expected 's', 'r', or 'a'"

    def _check_format_spec(self, format_spec, depth):
        self._check_fstring_contents(format_spec.children[1:], depth)

    def _check_fstring_expr(self, fstring_expr, depth):
        if depth >= 2:
            self.add_issue(fstring_expr, message=self.message_nested)

        expr = fstring_expr.children[1]
        if '\\' in expr.get_code():
            self.add_issue(expr, message=self.message_expr)

        children_2 = fstring_expr.children[2]
        if children_2.type == 'operator' and children_2.value == '=':
            conversion = fstring_expr.children[3]
        else:
            conversion = children_2
        if conversion.type == 'fstring_conversion':
            name = conversion.children[1]
            if name.value not in ('s', 'r', 'a'):
                self.add_issue(name, message=self.message_conversion)

        format_spec = fstring_expr.children[-2]
        if format_spec.type == 'fstring_format_spec':
            self._check_format_spec(format_spec, depth + 1)

    def is_issue(self, fstring):
        self._check_fstring_contents(fstring.children[1:-1])

    def _check_fstring_contents(self, children, depth=0):
        for fstring_content in children:
            if fstring_content.type == 'fstring_expr':
                self._check_fstring_expr(fstring_content, depth)


class _CheckAssignmentRule(SyntaxRule):
    def _check_assignment(self, node, is_deletion=False, is_namedexpr=False, is_aug_assign=False):
        error = None
        type_ = node.type
        if type_ == 'lambdef':
            error = 'lambda'
        elif type_ == 'atom':
            first, second = node.children[:2]
            error = _get_comprehension_type(node)
            if error is None:
                if second.type == 'dictorsetmaker':
                    if self._normalizer.version < (3, 8):
                        error = 'literal'
                    else:
                        if second.children[1] == ':':
                            if self._normalizer.version < (3, 10):
                                error = 'dict display'
                            else:
                                error = 'dict literal'
                        else:
                            error = 'set display'
                elif first == "{" and second == "}":
                    if self._normalizer.version < (3, 8):
                        error = 'literal'
                    else:
                        if self._normalizer.version < (3, 10):
                            error = "dict display"
                        else:
                            error = "dict literal"
                elif first == "{" and len(node.children) > 2:
                    if self._normalizer.version < (3, 8):
                        error = 'literal'
                    else:
                        error = "set display"
                elif first in ('(', '['):
                    if second.type == 'yield_expr':
                        error = 'yield expression'
                    elif second.type == 'testlist_comp':
                        # ([a, b] := [1, 2])
                        # ((a, b) := [1, 2])
                        if is_namedexpr:
                            if first == '(':
                                error = 'tuple'
                            elif first == '[':
                                error = 'list'

                        # This is not a comprehension, they were handled
                        # further above.
                        for child in second.children[::2]:
                            self._check_assignment(child, is_deletion, is_namedexpr, is_aug_assign)
                    else:  # Everything handled, must be useless brackets.
                        self._check_assignment(second, is_deletion, is_namedexpr, is_aug_assign)
        elif type_ == 'keyword':
            if node.value == "yield":
                error = "yield expression"
            elif self._normalizer.version < (3, 8):
                error = 'keyword'
            else:
                error = str(node.value)
        elif type_ == 'operator':
            if node.value == '...':
                if self._normalizer.version < (3, 10):
                    error = 'Ellipsis'
                else:
                    error = 'ellipsis'
        elif type_ == 'comparison':
            error = 'comparison'
        elif type_ in ('string', 'number', 'strings'):
            error = 'literal'
        elif type_ == 'yield_expr':
            # This one seems to be a slightly different warning in Python.
            message = 'assignment to yield expression not possible'
            self.add_issue(node, message=message)
        elif type_ == 'test':
            error = 'conditional expression'
        elif type_ in ('atom_expr', 'power'):
            if node.children[0] == 'await':
                error = 'await expression'
            elif node.children[-2] == '**':
                if self._normalizer.version < (3, 10):
                    error = 'operator'
                else:
                    error = 'expression'
            else:
                # Has a trailer
                trailer = node.children[-1]
                assert trailer.type == 'trailer'
                if trailer.children[0] == '(':
                    error = 'function call'
                elif is_namedexpr and trailer.children[0] == '[':
                    error = 'subscript'
                elif is_namedexpr and trailer.children[0] == '.':
                    error = 'attribute'
        elif type_ == "fstring":
            if self._normalizer.version < (3, 8):
                error = 'literal'
            else:
                error = "f-string expression"
        elif type_ in ('testlist_star_expr', 'exprlist', 'testlist'):
            for child in node.children[::2]:
                self._check_assignment(child, is_deletion, is_namedexpr, is_aug_assign)
        elif ('expr' in type_ and type_ != 'star_expr'  # is a substring
              or '_test' in type_
              or type_ in ('term', 'factor')):
            if self._normalizer.version < (3, 10):
                error = 'operator'
            else:
                error = 'expression'
        elif type_ == "star_expr":
            if is_deletion:
                if self._normalizer.version >= (3, 9):
                    error = "starred"
                else:
                    self.add_issue(node, message="can't use starred expression here")
            else:
                if self._normalizer.version >= (3, 9):
                    ancestor = node.parent
                else:
                    ancestor = _skip_parens_bottom_up(node)
                if ancestor.type not in _STAR_EXPR_PARENTS and not is_aug_assign \
                        and not (ancestor.type == 'atom' and ancestor.children[0] == '['):
                    message = "starred assignment target must be in a list or tuple"
                    self.add_issue(node, message=message)

            self._check_assignment(node.children[1])

        if error is not None:
            if is_namedexpr:
                message = 'cannot use assignment expressions with %s' % error
            else:
                cannot = "can't" if self._normalizer.version < (3, 8) else "cannot"
                message = ' '.join([cannot, "delete" if is_deletion else "assign to", error])
            self.add_issue(node, message=message)


@ErrorFinder.register_rule(type='sync_comp_for')
class _CompForRule(_CheckAssignmentRule):
    message = "asynchronous comprehension outside of an asynchronous function"

    def is_issue(self, node):
        expr_list = node.children[1]
        if expr_list.type != 'expr_list':  # Already handled.
            self._check_assignment(expr_list)

        return node.parent.children[0] == 'async' \
            and not self._normalizer.context.is_async_funcdef()


@ErrorFinder.register_rule(type='expr_stmt')
class _ExprStmtRule(_CheckAssignmentRule):
    message = "illegal expression for augmented assignment"
    extended_message = "'{target}' is an " + message

    def is_issue(self, node):
        augassign = node.children[1]
        is_aug_assign = augassign != '=' and augassign.type != 'annassign'

        if self._normalizer.version <= (3, 8) or not is_aug_assign:
            for before_equal in node.children[:-2:2]:
                self._check_assignment(before_equal, is_aug_assign=is_aug_assign)

        if is_aug_assign:
            target = _remove_parens(node.children[0])
            # a, a[b], a.b

            if target.type == "name" or (
                target.type in ("atom_expr", "power")
                and target.children[1].type == "trailer"
                and target.children[-1].children[0] != "("
            ):
                return False

            if self._normalizer.version <= (3, 8):
                return True
            else:
                self.add_issue(
                    node,
                    message=self.extended_message.format(
                        target=_get_rhs_name(node.children[0], self._normalizer.version)
                    ),
                )


@ErrorFinder.register_rule(type='with_item')
class _WithItemRule(_CheckAssignmentRule):
    def is_issue(self, with_item):
        self._check_assignment(with_item.children[2])


@ErrorFinder.register_rule(type='del_stmt')
class _DelStmtRule(_CheckAssignmentRule):
    def is_issue(self, del_stmt):
        child = del_stmt.children[1]

        if child.type != 'expr_list':  # Already handled.
            self._check_assignment(child, is_deletion=True)


@ErrorFinder.register_rule(type='expr_list')
class _ExprListRule(_CheckAssignmentRule):
    def is_issue(self, expr_list):
        for expr in expr_list.children[::2]:
            self._check_assignment(expr)


@ErrorFinder.register_rule(type='for_stmt')
class _ForStmtRule(_CheckAssignmentRule):
    def is_issue(self, for_stmt):
        # Some of the nodes here are already used, so no else if
        expr_list = for_stmt.children[1]
        if expr_list.type != 'expr_list':  # Already handled.
            self._check_assignment(expr_list)


@ErrorFinder.register_rule(type='namedexpr_test')
class _NamedExprRule(_CheckAssignmentRule):
    # namedexpr_test: test [':=' test]

    def is_issue(self, namedexpr_test):
        # assigned name
        first = namedexpr_test.children[0]

        def search_namedexpr_in_comp_for(node):
            while True:
                parent = node.parent
                if parent is None:
                    return parent
                if parent.type == 'sync_comp_for' and parent.children[3] == node:
                    return parent
                node = parent

        if search_namedexpr_in_comp_for(namedexpr_test):
            # [i+1 for i in (i := range(5))]
            # [i+1 for i in (j := range(5))]
            # [i+1 for i in (lambda: (j := range(5)))()]
            message = 'assignment expression cannot be used in a comprehension iterable expression'
            self.add_issue(namedexpr_test, message=message)

        # defined names
        exprlist = list()

        def process_comp_for(comp_for):
            if comp_for.type == 'sync_comp_for':
                comp = comp_for
            elif comp_for.type == 'comp_for':
                comp = comp_for.children[1]
            exprlist.extend(_get_for_stmt_definition_exprs(comp))

        def search_all_comp_ancestors(node):
            has_ancestors = False
            while True:
                node = node.search_ancestor('testlist_comp', 'dictorsetmaker')
                if node is None:
                    break
                for child in node.children:
                    if child.type in _COMP_FOR_TYPES:
                        process_comp_for(child)
                        has_ancestors = True
                        break
            return has_ancestors

        # check assignment expressions in comprehensions
        search_all = search_all_comp_ancestors(namedexpr_test)
        if search_all:
            if self._normalizer.context.node.type == 'classdef':
                message = 'assignment expression within a comprehension ' \
                          'cannot be used in a class body'
                self.add_issue(namedexpr_test, message=message)

            namelist = [expr.value for expr in exprlist if expr.type == 'name']
            if first.type == 'name' and first.value in namelist:
                # [i := 0 for i, j in range(5)]
                # [[(i := i) for j in range(5)] for i in range(5)]
                # [i for i, j in range(5) if True or (i := 1)]
                # [False and (i := 0) for i, j in range(5)]
                message = 'assignment expression cannot rebind ' \
                          'comprehension iteration variable %r' % first.value
                self.add_issue(namedexpr_test, message=message)

        self._check_assignment(first, is_namedexpr=True)

# === NexusCore/openenv\Lib\site-packages\trio\_socket.py ===
from __future__ import annotations

import os
import select
import socket as _stdlib_socket
import sys
from operator import index
from socket import AddressFamily, SocketKind
from typing import (
    TYPE_CHECKING,
    Any,
    SupportsIndex,
    TypeVar,
    Union,
    overload,
)

import idna as _idna

import trio
from trio._util import wraps as _wraps

from . import _core

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from types import TracebackType

    from typing_extensions import Buffer, Concatenate, ParamSpec, Self, TypeAlias

    from ._abc import HostnameResolver, SocketFactory

    P = ParamSpec("P")


T = TypeVar("T")

# _stdlib_socket.socket supports 13 different socket families, see
# https://docs.python.org/3/library/socket.html#socket-families
# and the return type of several methods in SocketType will depend on those. Typeshed
# has ended up typing those return types as `Any` in most cases, but for users that
# know which family/families they're working in we could make SocketType a generic type,
# where you specify the return values you expect from those methods depending on the
# protocol the socket will be handling.
# But without the ability to default the value to `Any` it will be overly cumbersome for
# most users, so currently we just specify it as `Any`. Otherwise we would write:
# `AddressFormat = TypeVar("AddressFormat")`
# but instead we simply do:
AddressFormat: TypeAlias = Any  # type: ignore[explicit-any]


# Usage:
#
#   async with _try_sync():
#       return sync_call_that_might_fail_with_exception()
#   # we only get here if the sync call in fact did fail with a
#   # BlockingIOError
#   return await do_it_properly_with_a_check_point()
#
class _try_sync:
    def __init__(
        self,
        blocking_exc_override: Callable[[BaseException], bool] | None = None,
    ) -> None:
        self._blocking_exc_override = blocking_exc_override

    def _is_blocking_io_error(self, exc: BaseException) -> bool:
        if self._blocking_exc_override is None:
            return isinstance(exc, BlockingIOError)
        else:
            return self._blocking_exc_override(exc)

    async def __aenter__(self) -> None:
        await trio.lowlevel.checkpoint_if_cancelled()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_value is not None and self._is_blocking_io_error(exc_value):
            # Discard the exception and fall through to the code below the
            # block
            return True
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            # Let the return or exception propagate
            return False


################################################################
# Overrides
################################################################

_resolver: _core.RunVar[HostnameResolver | None] = _core.RunVar("hostname_resolver")
_socket_factory: _core.RunVar[SocketFactory | None] = _core.RunVar("socket_factory")


def set_custom_hostname_resolver(
    hostname_resolver: HostnameResolver | None,
) -> HostnameResolver | None:
    """Set a custom hostname resolver.

    By default, Trio's :func:`getaddrinfo` and :func:`getnameinfo` functions
    use the standard system resolver functions. This function allows you to
    customize that behavior. The main intended use case is for testing, but it
    might also be useful for using third-party resolvers like `c-ares
    <https://c-ares.haxx.se/>`__ (though be warned that these rarely make
    perfect drop-in replacements for the system resolver). See
    :class:`trio.abc.HostnameResolver` for more details.

    Setting a custom hostname resolver affects all future calls to
    :func:`getaddrinfo` and :func:`getnameinfo` within the enclosing call to
    :func:`trio.run`. All other hostname resolution in Trio is implemented in
    terms of these functions.

    Generally you should call this function just once, right at the beginning
    of your program.

    Args:
      hostname_resolver (trio.abc.HostnameResolver or None): The new custom
          hostname resolver, or None to restore the default behavior.

    Returns:
      The previous hostname resolver (which may be None).

    """
    old = _resolver.get(None)
    _resolver.set(hostname_resolver)
    return old


def set_custom_socket_factory(
    socket_factory: SocketFactory | None,
) -> SocketFactory | None:
    """Set a custom socket object factory.

    This function allows you to replace Trio's normal socket class with a
    custom class. This is very useful for testing, and probably a bad idea in
    any other circumstance. See :class:`trio.abc.HostnameResolver` for more
    details.

    Setting a custom socket factory affects all future calls to :func:`socket`
    within the enclosing call to :func:`trio.run`.

    Generally you should call this function just once, right at the beginning
    of your program.

    Args:
      socket_factory (trio.abc.SocketFactory or None): The new custom
          socket factory, or None to restore the default behavior.

    Returns:
      The previous socket factory (which may be None).

    """
    old = _socket_factory.get(None)
    _socket_factory.set(socket_factory)
    return old


################################################################
# getaddrinfo and friends
################################################################

# AI_NUMERICSERV may be missing on some older platforms, so use it when available.
# See: https://github.com/python-trio/trio/issues/3133
_NUMERIC_ONLY = _stdlib_socket.AI_NUMERICHOST
_NUMERIC_ONLY |= getattr(_stdlib_socket, "AI_NUMERICSERV", 0)


# It would be possible to @overload the return value depending on Literal[AddressFamily.INET/6], but should probably be added in typeshed first
async def getaddrinfo(
    host: bytes | str | None,
    port: bytes | str | int | None,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
) -> list[
    tuple[
        AddressFamily,
        SocketKind,
        int,
        str,
        tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
    ]
]:
    """Look up a numeric address given a name.

    Arguments and return values are identical to :func:`socket.getaddrinfo`,
    except that this version is async.

    Also, :func:`trio.socket.getaddrinfo` correctly uses IDNA 2008 to process
    non-ASCII domain names. (:func:`socket.getaddrinfo` uses IDNA 2003, which
    can give the wrong result in some cases and cause you to connect to a
    different host than the one you intended; see `bpo-17305
    <https://bugs.python.org/issue17305>`__.)

    This function's behavior can be customized using
    :func:`set_custom_hostname_resolver`.

    """

    # If host and port are numeric, then getaddrinfo doesn't block and we can
    # skip the whole thread thing, which seems worthwhile. So we try first
    # with the _NUMERIC_ONLY flags set, and then only spawn a thread if that
    # fails with EAI_NONAME:
    def numeric_only_failure(exc: BaseException) -> bool:
        return (
            isinstance(exc, _stdlib_socket.gaierror)
            and exc.errno == _stdlib_socket.EAI_NONAME
        )

    async with _try_sync(numeric_only_failure):
        return _stdlib_socket.getaddrinfo(
            host,
            port,
            family,
            type,
            proto,
            flags | _NUMERIC_ONLY,
        )
    # That failed; it's a real hostname. We better use a thread.
    #
    # Also, it might be a unicode hostname, in which case we want to do our
    # own encoding using the idna module, rather than letting Python do
    # it. (Python will use the old IDNA 2003 standard, and possibly get the
    # wrong answer - see bpo-17305). However, the idna module is picky, and
    # will refuse to process some valid hostname strings, like "::1". So if
    # it's already ascii, we pass it through; otherwise, we encode it to.
    if isinstance(host, str):
        try:
            host = host.encode("ascii")
        except UnicodeEncodeError:
            # UTS-46 defines various normalizations; in particular, by default
            # idna.encode will error out if the hostname has Capital Letters
            # in it; with uts46=True it will lowercase them instead.
            host = _idna.encode(host, uts46=True)
    hr = _resolver.get(None)
    if hr is not None:
        return await hr.getaddrinfo(host, port, family, type, proto, flags)
    else:
        return await trio.to_thread.run_sync(
            _stdlib_socket.getaddrinfo,
            host,
            port,
            family,
            type,
            proto,
            flags,
            abandon_on_cancel=True,
        )


async def getnameinfo(
    sockaddr: tuple[str, int] | tuple[str, int, int, int],
    flags: int,
) -> tuple[str, str]:
    """Look up a name given a numeric address.

    Arguments and return values are identical to :func:`socket.getnameinfo`,
    except that this version is async.

    This function's behavior can be customized using
    :func:`set_custom_hostname_resolver`.

    """
    hr = _resolver.get(None)
    if hr is not None:
        return await hr.getnameinfo(sockaddr, flags)
    else:
        return await trio.to_thread.run_sync(
            _stdlib_socket.getnameinfo,
            sockaddr,
            flags,
            abandon_on_cancel=True,
        )


async def getprotobyname(name: str) -> int:
    """Look up a protocol number by name. (Rarely used.)

    Like :func:`socket.getprotobyname`, but async.

    """
    return await trio.to_thread.run_sync(
        _stdlib_socket.getprotobyname,
        name,
        abandon_on_cancel=True,
    )


# obsolete gethostbyname etc. intentionally omitted
# likewise for create_connection (use open_tcp_stream instead)

################################################################
# Socket "constructors"
################################################################


def from_stdlib_socket(sock: _stdlib_socket.socket) -> SocketType:
    """Convert a standard library :class:`socket.socket` object into a Trio
    socket object.

    """
    return _SocketType(sock)


@_wraps(_stdlib_socket.fromfd, assigned=(), updated=())
def fromfd(
    fd: SupportsIndex,
    family: AddressFamily | int = _stdlib_socket.AF_INET,
    type: SocketKind | int = _stdlib_socket.SOCK_STREAM,
    proto: int = 0,
) -> SocketType:
    """Like :func:`socket.fromfd`, but returns a Trio socket object."""
    family, type_, proto = _sniff_sockopts_for_fileno(family, type, proto, index(fd))
    return from_stdlib_socket(_stdlib_socket.fromfd(fd, family, type_, proto))


if sys.platform == "win32" or (
    not TYPE_CHECKING and hasattr(_stdlib_socket, "fromshare")
):

    @_wraps(_stdlib_socket.fromshare, assigned=(), updated=())
    def fromshare(info: bytes) -> SocketType:
        """Like :func:`socket.fromshare`, but returns a Trio socket object."""
        return from_stdlib_socket(_stdlib_socket.fromshare(info))


if sys.platform == "win32":
    FamilyT: TypeAlias = int
    TypeT: TypeAlias = int
    FamilyDefault = _stdlib_socket.AF_INET
else:
    FamilyDefault: None = None
    FamilyT: TypeAlias = Union[int, AddressFamily, None]
    TypeT: TypeAlias = Union[_stdlib_socket.socket, int]


@_wraps(_stdlib_socket.socketpair, assigned=(), updated=())
def socketpair(
    family: FamilyT = FamilyDefault,
    type: TypeT = SocketKind.SOCK_STREAM,
    proto: int = 0,
) -> tuple[SocketType, SocketType]:
    """Like :func:`socket.socketpair`, but returns a pair of Trio socket
    objects.

    """
    left, right = _stdlib_socket.socketpair(family, type, proto)
    return (from_stdlib_socket(left), from_stdlib_socket(right))


@_wraps(_stdlib_socket.socket, assigned=(), updated=())
def socket(
    family: AddressFamily | int = _stdlib_socket.AF_INET,
    type: SocketKind | int = _stdlib_socket.SOCK_STREAM,
    proto: int = 0,
    fileno: int | None = None,
) -> SocketType:
    """Create a new Trio socket, like :class:`socket.socket`.

    This function's behavior can be customized using
    :func:`set_custom_socket_factory`.

    """
    if fileno is None:
        sf = _socket_factory.get(None)
        if sf is not None:
            return sf.socket(family, type, proto)
    else:
        family, type, proto = _sniff_sockopts_for_fileno(  # noqa: A001
            family,
            type,
            proto,
            fileno,
        )
    stdlib_socket = _stdlib_socket.socket(family, type, proto, fileno)
    return from_stdlib_socket(stdlib_socket)


def _sniff_sockopts_for_fileno(
    family: AddressFamily | int,
    type_: SocketKind | int,
    proto: int,
    fileno: int | None,
) -> tuple[AddressFamily | int, SocketKind | int, int]:
    """Correct SOCKOPTS for given fileno, falling back to provided values."""
    # Wrap the raw fileno into a Python socket object
    # This object might have the wrong metadata, but it lets us easily call getsockopt
    # and then we'll throw it away and construct a new one with the correct metadata.
    if sys.platform != "linux":
        return family, type_, proto
    from socket import (  # type: ignore[attr-defined,unused-ignore]
        SO_DOMAIN,
        SO_PROTOCOL,
        SO_TYPE,
        SOL_SOCKET,
    )

    sockobj = _stdlib_socket.socket(family, type_, proto, fileno=fileno)
    try:
        family = sockobj.getsockopt(SOL_SOCKET, SO_DOMAIN)
        proto = sockobj.getsockopt(SOL_SOCKET, SO_PROTOCOL)
        type_ = sockobj.getsockopt(SOL_SOCKET, SO_TYPE)
    finally:
        # Unwrap it again, so that sockobj.__del__ doesn't try to close our socket
        sockobj.detach()
    return family, type_, proto


################################################################
# SocketType
################################################################

# sock.type gets weird stuff set in it, in particular on Linux:
#
#   https://bugs.python.org/issue21327
#
# But on other platforms (e.g. Windows) SOCK_NONBLOCK and SOCK_CLOEXEC aren't
# even defined. To recover the actual socket type (e.g. SOCK_STREAM) from a
# socket.type attribute, mask with this:
_SOCK_TYPE_MASK = ~(
    getattr(_stdlib_socket, "SOCK_NONBLOCK", 0)
    | getattr(_stdlib_socket, "SOCK_CLOEXEC", 0)
)


def _make_simple_sock_method_wrapper(
    fn: Callable[Concatenate[_stdlib_socket.socket, P], T],
    wait_fn: Callable[[_stdlib_socket.socket], Awaitable[None]],
    maybe_avail: bool = False,
) -> Callable[Concatenate[_SocketType, P], Awaitable[T]]:
    @_wraps(fn, assigned=("__name__",), updated=())
    async def wrapper(self: _SocketType, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self._nonblocking_helper(wait_fn, fn, *args, **kwargs)

    wrapper.__doc__ = f"""Like :meth:`socket.socket.{fn.__name__}`, but async.

            """
    if maybe_avail:
        wrapper.__doc__ += (
            f"Only available on platforms where :meth:`socket.socket.{fn.__name__}` is "
            "available."
        )
    return wrapper


# Helpers to work with the (hostname, port) language that Python uses for socket
# addresses everywhere. Split out into a standalone function so it can be reused by
# FakeNet.


# Take an address in Python's representation, and returns a new address in
# the same representation, but with names resolved to numbers,
# etc.
#
# local=True means that the address is being used with bind() or similar
# local=False means that the address is being used with connect() or sendto() or
# similar.
#


# Using a TypeVar to indicate we return the same type of address appears to give errors
# when passed a union of address types.
# @overload likely works, but is extremely verbose.
# NOTE: this function does not always checkpoint
async def _resolve_address_nocp(
    type_: int,
    family: AddressFamily,
    proto: int,
    *,
    ipv6_v6only: bool | int,
    address: AddressFormat,
    local: bool,
) -> AddressFormat:
    # Do some pre-checking (or exit early for non-IP sockets)
    if family == _stdlib_socket.AF_INET:
        if not isinstance(address, tuple) or not len(address) == 2:
            raise ValueError("address should be a (host, port) tuple")
    elif family == _stdlib_socket.AF_INET6:
        if not isinstance(address, tuple) or not 2 <= len(address) <= 4:
            raise ValueError(
                "address should be a (host, port, [flowinfo, [scopeid]]) tuple",
            )
    elif hasattr(_stdlib_socket, "AF_UNIX") and family == _stdlib_socket.AF_UNIX:
        # unwrap path-likes
        assert isinstance(address, (str, bytes, os.PathLike))
        return os.fspath(address)
    else:
        return address

    # -- From here on we know we have IPv4 or IPV6 --
    host: str | None
    host, port, *_ = address
    # Fast path for the simple case: already-resolved IP address,
    # already-resolved port. This is particularly important for UDP, since
    # every sendto call goes through here.
    if isinstance(port, int) and host is not None:
        try:
            _stdlib_socket.inet_pton(family, host)
        except (OSError, TypeError):
            pass
        else:
            return address
    # Special cases to match the stdlib, see gh-277
    if host == "":
        host = None
    if host == "<broadcast>":
        host = "255.255.255.255"
    flags = 0
    if local:
        flags |= _stdlib_socket.AI_PASSIVE
    # Since we always pass in an explicit family here, AI_ADDRCONFIG
    # doesn't add any value -- if we have no ipv6 connectivity and are
    # working with an ipv6 socket, then things will break soon enough! And
    # if we do enable it, then it makes it impossible to even run tests
    # for ipv6 address resolution on travis-ci, which as of 2017-03-07 has
    # no ipv6.
    # flags |= AI_ADDRCONFIG
    if family == _stdlib_socket.AF_INET6 and not ipv6_v6only:
        flags |= _stdlib_socket.AI_V4MAPPED
    gai_res = await getaddrinfo(host, port, family, type_, proto, flags)
    # AFAICT from the spec it's not possible for getaddrinfo to return an
    # empty list.
    assert len(gai_res) >= 1
    # Address is the last item in the first entry
    (*_, normed), *_ = gai_res
    # The above ignored any flowid and scopeid in the passed-in address,
    # so restore them if present:
    if family == _stdlib_socket.AF_INET6:
        list_normed = list(normed)
        assert len(normed) == 4
        if len(address) >= 3:
            list_normed[2] = address[2]
        if len(address) >= 4:
            list_normed[3] = address[3]
        return tuple(list_normed)
    return normed


class SocketType:
    def __init__(self) -> None:
        # make sure this __init__ works with multiple inheritance
        super().__init__()
        # and only raises error if it's directly constructed
        if type(self) is SocketType:
            raise TypeError(
                "SocketType is an abstract class; use trio.socket.socket if you "
                "want to construct a socket object",
            )

    def detach(self) -> int:
        raise NotImplementedError

    def fileno(self) -> int:
        raise NotImplementedError

    def getpeername(self) -> AddressFormat:
        raise NotImplementedError

    def getsockname(self) -> AddressFormat:
        raise NotImplementedError

    @overload
    def getsockopt(self, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self,
        level: int,
        optname: int,
        buflen: int | None = None,
    ) -> int | bytes:
        raise NotImplementedError

    @overload
    def setsockopt(self, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self,
        level: int,
        optname: int,
        value: None,
        optlen: int,
    ) -> None: ...

    def setsockopt(
        self,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        raise NotImplementedError

    def listen(self, backlog: int = min(_stdlib_socket.SOMAXCONN, 128)) -> None:
        raise NotImplementedError

    def get_inheritable(self) -> bool:
        raise NotImplementedError

    def set_inheritable(self, inheritable: bool) -> None:
        raise NotImplementedError

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "share")
    ):

        def share(self, process_id: int) -> bytes:
            raise NotImplementedError

    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @property
    def family(self) -> AddressFamily:
        raise NotImplementedError

    @property
    def type(self) -> SocketKind:
        raise NotImplementedError

    @property
    def proto(self) -> int:
        raise NotImplementedError

    @property
    def did_shutdown_SHUT_WR(self) -> bool:
        """Return True if the socket has been shut down with the SHUT_WR flag"""
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def dup(self) -> SocketType:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    async def bind(self, address: AddressFormat) -> None:
        raise NotImplementedError

    def shutdown(self, flag: int) -> None:
        raise NotImplementedError

    def is_readable(self) -> bool:
        """Return True if the socket is readable. This is checked with `select.select` on Windows, otherwise `select.poll`."""
        raise NotImplementedError

    async def wait_writable(self) -> None:
        """Convenience method that calls trio.lowlevel.wait_writable for the object."""
        raise NotImplementedError

    async def accept(self) -> tuple[SocketType, AddressFormat]:
        raise NotImplementedError

    async def connect(self, address: AddressFormat) -> None:
        raise NotImplementedError

    def recv(self, buflen: int, flags: int = 0, /) -> Awaitable[bytes]:
        raise NotImplementedError

    def recv_into(
        self,
        buffer: Buffer,
        nbytes: int = 0,
        flags: int = 0,
    ) -> Awaitable[int]:
        raise NotImplementedError

    # return type of socket.socket.recvfrom in typeshed is tuple[bytes, Any]
    def recvfrom(
        self,
        bufsize: int,
        flags: int = 0,
        /,
    ) -> Awaitable[tuple[bytes, AddressFormat]]:
        raise NotImplementedError

    # return type of socket.socket.recvfrom_into in typeshed is tuple[bytes, Any]
    def recvfrom_into(
        self,
        buffer: Buffer,
        nbytes: int = 0,
        flags: int = 0,
    ) -> Awaitable[tuple[int, AddressFormat]]:
        raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg")
    ):

        def recvmsg(
            self,
            bufsize: int,
            ancbufsize: int = 0,
            flags: int = 0,
            /,
        ) -> Awaitable[tuple[bytes, list[tuple[int, int, bytes]], int, object]]:
            raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg_into")
    ):

        def recvmsg_into(
            self,
            buffers: Iterable[Buffer],
            ancbufsize: int = 0,
            flags: int = 0,
            /,
        ) -> Awaitable[tuple[int, list[tuple[int, int, bytes]], int, object]]:
            raise NotImplementedError

    def send(self, bytes: Buffer, flags: int = 0, /) -> Awaitable[int]:
        raise NotImplementedError

    @overload
    async def sendto(
        self,
        data: Buffer,
        address: tuple[object, ...] | str | Buffer,
        /,
    ) -> int: ...

    @overload
    async def sendto(
        self,
        data: Buffer,
        flags: int,
        address: tuple[object, ...] | str | Buffer,
        /,
    ) -> int: ...

    async def sendto(self, *args: object) -> int:
        raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "sendmsg")
    ):

        @_wraps(_stdlib_socket.socket.sendmsg, assigned=(), updated=())
        async def sendmsg(
            self,
            buffers: Iterable[Buffer],
            ancdata: Iterable[tuple[int, int, Buffer]] = (),
            flags: int = 0,
            address: AddressFormat | None = None,
            /,
        ) -> int:
            raise NotImplementedError


# copy docstrings from socket.SocketType / socket.socket
for name, obj in SocketType.__dict__.items():
    # skip dunders and already defined docstrings
    if name.startswith("__") or obj.__doc__:
        continue
    # try both socket.socket and socket.SocketType
    for stdlib_type in _stdlib_socket.socket, _stdlib_socket.SocketType:
        stdlib_obj = getattr(stdlib_type, name, None)
        if stdlib_obj and stdlib_obj.__doc__:
            break
    else:
        continue
    obj.__doc__ = stdlib_obj.__doc__


class _SocketType(SocketType):
    def __init__(self, sock: _stdlib_socket.socket) -> None:
        if type(sock) is not _stdlib_socket.socket:
            # For example, ssl.SSLSocket subclasses socket.socket, but we
            # certainly don't want to blindly wrap one of those.
            raise TypeError(
                f"expected object of type 'socket.socket', not '{type(sock).__name__}'",
            )
        self._sock = sock
        self._sock.setblocking(False)
        self._did_shutdown_SHUT_WR = False

    ################################################################
    # Simple + portable methods and attributes
    ################################################################

    # forwarded methods
    def detach(self) -> int:
        return self._sock.detach()

    def fileno(self) -> int:
        return self._sock.fileno()

    def getpeername(self) -> AddressFormat:
        return self._sock.getpeername()

    def getsockname(self) -> AddressFormat:
        return self._sock.getsockname()

    @overload
    def getsockopt(self, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self,
        level: int,
        optname: int,
        buflen: int | None = None,
    ) -> int | bytes:
        if buflen is None:
            return self._sock.getsockopt(level, optname)
        return self._sock.getsockopt(level, optname, buflen)

    @overload
    def setsockopt(self, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self,
        level: int,
        optname: int,
        value: None,
        optlen: int,
    ) -> None: ...

    def setsockopt(
        self,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        if optlen is None:
            if value is None:
                raise TypeError(
                    "invalid value for argument 'value', must not be None when specifying optlen",
                )
            return self._sock.setsockopt(level, optname, value)
        if value is not None:
            raise TypeError(
                f"invalid value for argument 'value': {value!r}, must be None when specifying optlen",
            )

        # Note: PyPy may crash here due to setsockopt only supporting
        # four parameters.
        return self._sock.setsockopt(level, optname, value, optlen)

    def listen(self, backlog: int = min(_stdlib_socket.SOMAXCONN, 128)) -> None:
        return self._sock.listen(backlog)

    def get_inheritable(self) -> bool:
        return self._sock.get_inheritable()

    def set_inheritable(self, inheritable: bool) -> None:
        return self._sock.set_inheritable(inheritable)

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "share")
    ):

        def share(self, process_id: int) -> bytes:
            return self._sock.share(process_id)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self._sock.__exit__(exc_type, exc_value, traceback)

    @property
    def family(self) -> AddressFamily:
        return self._sock.family

    @property
    def type(self) -> SocketKind:
        return self._sock.type

    @property
    def proto(self) -> int:
        return self._sock.proto

    @property
    def did_shutdown_SHUT_WR(self) -> bool:
        return self._did_shutdown_SHUT_WR

    def __repr__(self) -> str:
        return repr(self._sock).replace("socket.socket", "trio.socket.socket")

    def dup(self) -> SocketType:
        """Same as :meth:`socket.socket.dup`."""
        return _SocketType(self._sock.dup())

    def close(self) -> None:
        if self._sock.fileno() != -1:
            trio.lowlevel.notify_closing(self._sock)
            self._sock.close()

    async def bind(self, address: AddressFormat) -> None:
        address = await self._resolve_address_nocp(address, local=True)
        if (
            hasattr(_stdlib_socket, "AF_UNIX")
            and self.family == _stdlib_socket.AF_UNIX
            and address[0]
        ):
            # Use a thread for the filesystem traversal (unless it's an
            # abstract domain socket)
            return await trio.to_thread.run_sync(self._sock.bind, address)
        else:
            # POSIX actually says that bind can return EWOULDBLOCK and
            # complete asynchronously, like connect. But in practice AFAICT
            # there aren't yet any real systems that do this, so we'll worry
            # about it when it happens.
            await trio.lowlevel.checkpoint()
            return self._sock.bind(address)

    def shutdown(self, flag: int) -> None:
        # no need to worry about return value b/c always returns None:
        self._sock.shutdown(flag)
        # only do this if the call succeeded:
        if flag in [_stdlib_socket.SHUT_WR, _stdlib_socket.SHUT_RDWR]:
            self._did_shutdown_SHUT_WR = True

    def is_readable(self) -> bool:
        # use select.select on Windows, and select.poll everywhere else
        if sys.platform == "win32":
            rready, _, _ = select.select([self._sock], [], [], 0)
            return bool(rready)
        p = select.poll()
        p.register(self._sock, select.POLLIN)
        return bool(p.poll(0))

    async def wait_writable(self) -> None:
        await _core.wait_writable(self._sock)

    async def _resolve_address_nocp(
        self,
        address: AddressFormat,
        *,
        local: bool,
    ) -> AddressFormat:
        if self.family == _stdlib_socket.AF_INET6:
            ipv6_v6only = self._sock.getsockopt(
                _stdlib_socket.IPPROTO_IPV6,
                _stdlib_socket.IPV6_V6ONLY,
            )
        else:
            ipv6_v6only = False
        return await _resolve_address_nocp(
            self.type,
            self.family,
            self.proto,
            ipv6_v6only=ipv6_v6only,
            address=address,
            local=local,
        )

    # args and kwargs must be starred, otherwise pyright complains:
    # '"args" member of ParamSpec is valid only when used with *args parameter'
    # '"kwargs" member of ParamSpec is valid only when used with **kwargs parameter'
    # wait_fn and fn must also be first in the signature
    # 'Keyword parameter cannot appear in signature after ParamSpec args parameter'

    async def _nonblocking_helper(
        self,
        wait_fn: Callable[[_stdlib_socket.socket], Awaitable[None]],
        fn: Callable[Concatenate[_stdlib_socket.socket, P], T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        # We have to reconcile two conflicting goals:
        # - We want to make it look like we always blocked in doing these
        #   operations. The obvious way is to always do an IO wait before
        #   calling the function.
        # - But, we also want to provide the correct semantics, and part
        #   of that means giving correct errors. So, for example, if you
        #   haven't called .listen(), then .accept() raises an error
        #   immediately. But in this same circumstance, then on macOS, the
        #   socket does not register as readable. So if we block waiting
        #   for read *before* we call accept, then we'll be waiting
        #   forever instead of properly raising an error. (On Linux,
        #   interestingly, AFAICT a socket that can't possible read/write
        #   *does* count as readable/writable for select() purposes. But
        #   not on macOS.)
        #
        # So, we have to call the function once, with the appropriate
        # cancellation/yielding sandwich if it succeeds, and if it gives
        # BlockingIOError *then* we fall back to IO wait.
        #
        # XX think if this can be combined with the similar logic for IOCP
        # submission...
        async with _try_sync():
            return fn(self._sock, *args, **kwargs)
        # First attempt raised BlockingIOError:
        while True:
            await wait_fn(self._sock)
            try:
                return fn(self._sock, *args, **kwargs)
            except BlockingIOError:
                pass

    ################################################################
    # accept
    ################################################################

    _accept = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.accept,
        _core.wait_readable,
    )

    async def accept(self) -> tuple[SocketType, AddressFormat]:
        """Like :meth:`socket.socket.accept`, but async."""
        sock, addr = await self._accept()
        return from_stdlib_socket(sock), addr

    ################################################################
    # connect
    ################################################################

    async def connect(self, address: AddressFormat) -> None:
        # nonblocking connect is weird -- you call it to start things
        # off, then the socket becomes writable as a completion
        # notification. This means it isn't really cancellable... we close the
        # socket if cancelled, to avoid confusion.
        try:
            address = await self._resolve_address_nocp(address, local=False)
            async with _try_sync():
                # An interesting puzzle: can a non-blocking connect() return EINTR
                # (= raise InterruptedError)? PEP 475 specifically left this as
                # the one place where it lets an InterruptedError escape instead
                # of automatically retrying. This is based on the idea that EINTR
                # from connect means that the connection was already started, and
                # will continue in the background. For a blocking connect, this
                # sort of makes sense: if it returns EINTR then the connection
                # attempt is continuing in the background, and on many system you
                # can't then call connect() again because there is already a
                # connect happening. See:
                #
                #   http://www.madore.org/~david/computers/connect-intr.html
                #
                # For a non-blocking connect, it doesn't make as much sense --
                # surely the interrupt didn't happen after we successfully
                # initiated the connect and are just waiting for it to complete,
                # because a non-blocking connect does not wait! And the spec
                # describes the interaction between EINTR/blocking connect, but
                # doesn't have anything useful to say about non-blocking connect:
                #
                #   http://pubs.opengroup.org/onlinepubs/007904975/functions/connect.html
                #
                # So we have a conundrum: if EINTR means that the connect() hasn't
                # happened (like it does for essentially every other syscall),
                # then InterruptedError should be caught and retried. If EINTR
                # means that the connect() has successfully started, then
                # InterruptedError should be caught and ignored. Which should we
                # do?
                #
                # In practice, the resolution is probably that non-blocking
                # connect simply never returns EINTR, so the question of how to
                # handle it is moot.  Someone spelunked macOS/FreeBSD and
                # confirmed this is true there:
                #
                #   https://stackoverflow.com/questions/14134440/eintr-and-non-blocking-calls
                #
                # and exarkun seems to think it's true in general of non-blocking
                # calls:
                #
                #   https://twistedmatrix.com/pipermail/twisted-python/2010-September/022864.html
                # (and indeed, AFAICT twisted doesn't try to handle
                # InterruptedError).
                #
                # So we don't try to catch InterruptedError. This way if it
                # happens, someone will hopefully tell us, and then hopefully we
                # can investigate their system to figure out what its semantics
                # are.
                return self._sock.connect(address)
            # It raised BlockingIOError, meaning that it's started the
            # connection attempt. We wait for it to complete:
            await _core.wait_writable(self._sock)
        except trio.Cancelled:
            # We can't really cancel a connect, and the socket is in an
            # indeterminate state. Better to close it so we don't get
            # confused.
            self._sock.close()
            raise
        # Okay, the connect finished, but it might have failed:
        err = self._sock.getsockopt(_stdlib_socket.SOL_SOCKET, _stdlib_socket.SO_ERROR)
        if err != 0:
            raise OSError(err, f"Error connecting to {address!r}: {os.strerror(err)}")

    ################################################################
    # recv
    ################################################################

    # Not possible to typecheck with a Callable (due to DefaultArg), nor with a
    # callback Protocol (https://github.com/python/typing/discussions/1040)
    # but this seems to work. If not explicitly defined then pyright --verifytypes will
    # complain about AmbiguousType
    if TYPE_CHECKING:

        def recv(self, buflen: int, flags: int = 0, /) -> Awaitable[bytes]: ...

    recv = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recv,
        _core.wait_readable,
    )

    ################################################################
    # recv_into
    ################################################################

    if TYPE_CHECKING:

        def recv_into(
            self,
            /,
            buffer: Buffer,
            nbytes: int = 0,
            flags: int = 0,
        ) -> Awaitable[int]: ...

    recv_into = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recv_into,
        _core.wait_readable,
    )

    ################################################################
    # recvfrom
    ################################################################

    if TYPE_CHECKING:
        # return type of socket.socket.recvfrom in typeshed is tuple[bytes, Any]
        def recvfrom(
            self,
            bufsize: int,
            flags: int = 0,
            /,
        ) -> Awaitable[tuple[bytes, AddressFormat]]: ...

    recvfrom = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recvfrom,
        _core.wait_readable,
    )

    ################################################################
    # recvfrom_into
    ################################################################

    if TYPE_CHECKING:
        # return type of socket.socket.recvfrom_into in typeshed is tuple[bytes, Any]
        def recvfrom_into(
            self,
            /,
            buffer: Buffer,
            nbytes: int = 0,
            flags: int = 0,
        ) -> Awaitable[tuple[int, AddressFormat]]: ...

    recvfrom_into = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recvfrom_into,
        _core.wait_readable,
    )

    ################################################################
    # recvmsg
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg")
    ):
        if TYPE_CHECKING:

            def recvmsg(
                self,
                bufsize: int,
                ancbufsize: int = 0,
                flags: int = 0,
                /,
            ) -> Awaitable[tuple[bytes, list[tuple[int, int, bytes]], int, object]]: ...

        recvmsg = _make_simple_sock_method_wrapper(
            _stdlib_socket.socket.recvmsg,
            _core.wait_readable,
            maybe_avail=True,
        )

    ################################################################
    # recvmsg_into
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg_into")
    ):
        if TYPE_CHECKING:

            def recvmsg_into(
                self,
                buffers: Iterable[Buffer],
                ancbufsize: int = 0,
                flags: int = 0,
                /,
            ) -> Awaitable[tuple[int, list[tuple[int, int, bytes]], int, object]]: ...

        recvmsg_into = _make_simple_sock_method_wrapper(
            _stdlib_socket.socket.recvmsg_into,
            _core.wait_readable,
            maybe_avail=True,
        )

    ################################################################
    # send
    ################################################################

    if TYPE_CHECKING:

        def send(self, bytes: Buffer, flags: int = 0, /) -> Awaitable[int]: ...

    send = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.send,
        _core.wait_writable,
    )

    ################################################################
    # sendto
    ################################################################

    @overload
    async def sendto(
        self,
        data: Buffer,
        address: tuple[object, ...] | str | Buffer,
        /,
    ) -> int: ...

    @overload
    async def sendto(
        self,
        data: Buffer,
        flags: int,
        address: tuple[object, ...] | str | Buffer,
        /,
    ) -> int: ...

    @_wraps(_stdlib_socket.socket.sendto, assigned=(), updated=())
    async def sendto(self, *args: object) -> int:
        """Similar to :meth:`socket.socket.sendto`, but async."""
        # args is: data[, flags], address
        # and kwargs are not accepted
        args_list = list(args)
        args_list[-1] = await self._resolve_address_nocp(args[-1], local=False)
        # args_list is Any, which isn't the signature of sendto().
        # We don't care about invalid types, sendto() will do the checking.
        return await self._nonblocking_helper(
            _core.wait_writable,
            _stdlib_socket.socket.sendto,  # type: ignore[arg-type]
            *args_list,
        )

    ################################################################
    # sendmsg
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "sendmsg")
    ):

        @_wraps(_stdlib_socket.socket.sendmsg, assigned=(), updated=())
        async def sendmsg(
            self,
            buffers: Iterable[Buffer],
            ancdata: Iterable[tuple[int, int, Buffer]] = (),
            flags: int = 0,
            address: AddressFormat | None = None,
            /,
        ) -> int:
            """Similar to :meth:`socket.socket.sendmsg`, but async.

            Only available on platforms where :meth:`socket.socket.sendmsg` is
            available.

            """
            if address is not None:
                address = await self._resolve_address_nocp(address, local=False)
            return await self._nonblocking_helper(
                _core.wait_writable,
                _stdlib_socket.socket.sendmsg,
                buffers,
                ancdata,
                flags,
                address,
            )

    ################################################################
    # sendfile
    ################################################################

    # Not implemented yet:
    # async def sendfile(self, file, offset=0, count=None):
    #     XX

    # Intentionally omitted:
    #   sendall
    #   makefile
    #   setblocking/getblocking
    #   settimeout/gettimeout
    #   timeout

# === NexusCore/openenv\Lib\site-packages\matplotlib\_cm_bivar.py ===
# auto-generated by https://github.com/trygvrad/multivariate_colormaps
# date: 2024-05-24

import numpy as np
from matplotlib.colors import SegmentedBivarColormap

BiPeak = np.array(
    [0.000, 0.674, 0.931, 0.000, 0.680, 0.922, 0.000, 0.685, 0.914, 0.000,
     0.691, 0.906, 0.000, 0.696, 0.898, 0.000, 0.701, 0.890, 0.000, 0.706,
     0.882, 0.000, 0.711, 0.875, 0.000, 0.715, 0.867, 0.000, 0.720, 0.860,
     0.000, 0.725, 0.853, 0.000, 0.729, 0.845, 0.000, 0.733, 0.838, 0.000,
     0.737, 0.831, 0.000, 0.741, 0.824, 0.000, 0.745, 0.816, 0.000, 0.749,
     0.809, 0.000, 0.752, 0.802, 0.000, 0.756, 0.794, 0.000, 0.759, 0.787,
     0.000, 0.762, 0.779, 0.000, 0.765, 0.771, 0.000, 0.767, 0.764, 0.000,
     0.770, 0.755, 0.000, 0.772, 0.747, 0.000, 0.774, 0.739, 0.000, 0.776,
     0.730, 0.000, 0.777, 0.721, 0.000, 0.779, 0.712, 0.021, 0.780, 0.702,
     0.055, 0.781, 0.693, 0.079, 0.782, 0.682, 0.097, 0.782, 0.672, 0.111,
     0.782, 0.661, 0.122, 0.782, 0.650, 0.132, 0.782, 0.639, 0.140, 0.781,
     0.627, 0.147, 0.781, 0.615, 0.154, 0.780, 0.602, 0.159, 0.778, 0.589,
     0.164, 0.777, 0.576, 0.169, 0.775, 0.563, 0.173, 0.773, 0.549, 0.177,
     0.771, 0.535, 0.180, 0.768, 0.520, 0.184, 0.766, 0.505, 0.187, 0.763,
     0.490, 0.190, 0.760, 0.474, 0.193, 0.756, 0.458, 0.196, 0.753, 0.442,
     0.200, 0.749, 0.425, 0.203, 0.745, 0.408, 0.206, 0.741, 0.391, 0.210,
     0.736, 0.373, 0.213, 0.732, 0.355, 0.216, 0.727, 0.337, 0.220, 0.722,
     0.318, 0.224, 0.717, 0.298, 0.227, 0.712, 0.278, 0.231, 0.707, 0.258,
     0.235, 0.701, 0.236, 0.239, 0.696, 0.214, 0.242, 0.690, 0.190, 0.246,
     0.684, 0.165, 0.250, 0.678, 0.136, 0.000, 0.675, 0.934, 0.000, 0.681,
     0.925, 0.000, 0.687, 0.917, 0.000, 0.692, 0.909, 0.000, 0.697, 0.901,
     0.000, 0.703, 0.894, 0.000, 0.708, 0.886, 0.000, 0.713, 0.879, 0.000,
     0.718, 0.872, 0.000, 0.722, 0.864, 0.000, 0.727, 0.857, 0.000, 0.731,
     0.850, 0.000, 0.736, 0.843, 0.000, 0.740, 0.836, 0.000, 0.744, 0.829,
     0.000, 0.748, 0.822, 0.000, 0.752, 0.815, 0.000, 0.755, 0.808, 0.000,
     0.759, 0.800, 0.000, 0.762, 0.793, 0.000, 0.765, 0.786, 0.000, 0.768,
     0.778, 0.000, 0.771, 0.770, 0.000, 0.773, 0.762, 0.051, 0.776, 0.754,
     0.087, 0.778, 0.746, 0.111, 0.780, 0.737, 0.131, 0.782, 0.728, 0.146,
     0.783, 0.719, 0.159, 0.784, 0.710, 0.171, 0.785, 0.700, 0.180, 0.786,
     0.690, 0.189, 0.786, 0.680, 0.196, 0.787, 0.669, 0.202, 0.787, 0.658,
     0.208, 0.786, 0.647, 0.213, 0.786, 0.635, 0.217, 0.785, 0.623, 0.221,
     0.784, 0.610, 0.224, 0.782, 0.597, 0.227, 0.781, 0.584, 0.230, 0.779,
     0.570, 0.232, 0.777, 0.556, 0.234, 0.775, 0.542, 0.236, 0.772, 0.527,
     0.238, 0.769, 0.512, 0.240, 0.766, 0.497, 0.242, 0.763, 0.481, 0.244,
     0.760, 0.465, 0.246, 0.756, 0.448, 0.248, 0.752, 0.432, 0.250, 0.748,
     0.415, 0.252, 0.744, 0.397, 0.254, 0.739, 0.379, 0.256, 0.735, 0.361,
     0.259, 0.730, 0.343, 0.261, 0.725, 0.324, 0.264, 0.720, 0.304, 0.266,
     0.715, 0.284, 0.269, 0.709, 0.263, 0.271, 0.704, 0.242, 0.274, 0.698,
     0.220, 0.277, 0.692, 0.196, 0.280, 0.686, 0.170, 0.283, 0.680, 0.143,
     0.000, 0.676, 0.937, 0.000, 0.682, 0.928, 0.000, 0.688, 0.920, 0.000,
     0.694, 0.913, 0.000, 0.699, 0.905, 0.000, 0.704, 0.897, 0.000, 0.710,
     0.890, 0.000, 0.715, 0.883, 0.000, 0.720, 0.876, 0.000, 0.724, 0.869,
     0.000, 0.729, 0.862, 0.000, 0.734, 0.855, 0.000, 0.738, 0.848, 0.000,
     0.743, 0.841, 0.000, 0.747, 0.834, 0.000, 0.751, 0.827, 0.000, 0.755,
     0.820, 0.000, 0.759, 0.813, 0.000, 0.762, 0.806, 0.003, 0.766, 0.799,
     0.066, 0.769, 0.792, 0.104, 0.772, 0.784, 0.131, 0.775, 0.777, 0.152,
     0.777, 0.769, 0.170, 0.780, 0.761, 0.185, 0.782, 0.753, 0.198, 0.784,
     0.744, 0.209, 0.786, 0.736, 0.219, 0.787, 0.727, 0.228, 0.788, 0.717,
     0.236, 0.789, 0.708, 0.243, 0.790, 0.698, 0.249, 0.791, 0.688, 0.254,
     0.791, 0.677, 0.259, 0.791, 0.666, 0.263, 0.791, 0.654, 0.266, 0.790,
     0.643, 0.269, 0.789, 0.631, 0.272, 0.788, 0.618, 0.274, 0.787, 0.605,
     0.276, 0.785, 0.592, 0.278, 0.783, 0.578, 0.279, 0.781, 0.564, 0.280,
     0.779, 0.549, 0.282, 0.776, 0.535, 0.283, 0.773, 0.519, 0.284, 0.770,
     0.504, 0.285, 0.767, 0.488, 0.286, 0.763, 0.472, 0.287, 0.759, 0.455,
     0.288, 0.756, 0.438, 0.289, 0.751, 0.421, 0.291, 0.747, 0.403, 0.292,
     0.742, 0.385, 0.293, 0.738, 0.367, 0.295, 0.733, 0.348, 0.296, 0.728,
     0.329, 0.298, 0.723, 0.310, 0.300, 0.717, 0.290, 0.302, 0.712, 0.269,
     0.304, 0.706, 0.247, 0.306, 0.700, 0.225, 0.308, 0.694, 0.201, 0.310,
     0.688, 0.176, 0.312, 0.682, 0.149, 0.000, 0.678, 0.939, 0.000, 0.683,
     0.931, 0.000, 0.689, 0.923, 0.000, 0.695, 0.916, 0.000, 0.701, 0.908,
     0.000, 0.706, 0.901, 0.000, 0.711, 0.894, 0.000, 0.717, 0.887, 0.000,
     0.722, 0.880, 0.000, 0.727, 0.873, 0.000, 0.732, 0.866, 0.000, 0.736,
     0.859, 0.000, 0.741, 0.853, 0.000, 0.745, 0.846, 0.000, 0.750, 0.839,
     0.000, 0.754, 0.833, 0.035, 0.758, 0.826, 0.091, 0.762, 0.819, 0.126,
     0.765, 0.812, 0.153, 0.769, 0.805, 0.174, 0.772, 0.798, 0.193, 0.775,
     0.791, 0.209, 0.778, 0.783, 0.223, 0.781, 0.776, 0.236, 0.784, 0.768,
     0.247, 0.786, 0.760, 0.257, 0.788, 0.752, 0.266, 0.790, 0.743, 0.273,
     0.791, 0.734, 0.280, 0.793, 0.725, 0.287, 0.794, 0.715, 0.292, 0.794,
     0.706, 0.297, 0.795, 0.695, 0.301, 0.795, 0.685, 0.305, 0.795, 0.674,
     0.308, 0.795, 0.662, 0.310, 0.794, 0.651, 0.312, 0.794, 0.638, 0.314,
     0.792, 0.626, 0.316, 0.791, 0.613, 0.317, 0.789, 0.599, 0.318, 0.787,
     0.586, 0.319, 0.785, 0.571, 0.320, 0.783, 0.557, 0.320, 0.780, 0.542,
     0.321, 0.777, 0.527, 0.321, 0.774, 0.511, 0.322, 0.770, 0.495, 0.322,
     0.767, 0.478, 0.323, 0.763, 0.462, 0.323, 0.759, 0.445, 0.324, 0.755,
     0.427, 0.325, 0.750, 0.410, 0.325, 0.745, 0.391, 0.326, 0.741, 0.373,
     0.327, 0.736, 0.354, 0.328, 0.730, 0.335, 0.329, 0.725, 0.315, 0.330,
     0.720, 0.295, 0.331, 0.714, 0.274, 0.333, 0.708, 0.253, 0.334, 0.702,
     0.230, 0.336, 0.696, 0.207, 0.337, 0.690, 0.182, 0.339, 0.684, 0.154,
     0.000, 0.679, 0.942, 0.000, 0.685, 0.934, 0.000, 0.691, 0.927, 0.000,
     0.696, 0.919, 0.000, 0.702, 0.912, 0.000, 0.708, 0.905, 0.000, 0.713,
     0.898, 0.000, 0.718, 0.891, 0.000, 0.724, 0.884, 0.000, 0.729, 0.877,
     0.000, 0.734, 0.871, 0.000, 0.739, 0.864, 0.000, 0.743, 0.857, 0.035,
     0.748, 0.851, 0.096, 0.752, 0.844, 0.133, 0.757, 0.838, 0.161, 0.761,
     0.831, 0.185, 0.765, 0.825, 0.205, 0.769, 0.818, 0.223, 0.772, 0.811,
     0.238, 0.776, 0.804, 0.252, 0.779, 0.797, 0.265, 0.782, 0.790, 0.276,
     0.785, 0.783, 0.286, 0.788, 0.775, 0.296, 0.790, 0.767, 0.304, 0.792,
     0.759, 0.311, 0.794, 0.751, 0.318, 0.796, 0.742, 0.324, 0.797, 0.733,
     0.329, 0.798, 0.723, 0.334, 0.799, 0.714, 0.338, 0.799, 0.703, 0.341,
     0.800, 0.693, 0.344, 0.800, 0.682, 0.347, 0.799, 0.670, 0.349, 0.799,
     0.659, 0.351, 0.798, 0.646, 0.352, 0.797, 0.634, 0.353, 0.795, 0.621,
     0.354, 0.794, 0.607, 0.354, 0.792, 0.593, 0.355, 0.789, 0.579, 0.355,
     0.787, 0.564, 0.355, 0.784, 0.549, 0.355, 0.781, 0.534, 0.355, 0.778,
     0.518, 0.355, 0.774, 0.502, 0.355, 0.770, 0.485, 0.355, 0.766, 0.468,
     0.355, 0.762, 0.451, 0.355, 0.758, 0.434, 0.355, 0.753, 0.416, 0.356,
     0.748, 0.397, 0.356, 0.743, 0.379, 0.356, 0.738, 0.360, 0.357, 0.733,
     0.340, 0.357, 0.728, 0.321, 0.358, 0.722, 0.300, 0.359, 0.716, 0.279,
     0.360, 0.710, 0.258, 0.361, 0.704, 0.235, 0.361, 0.698, 0.212, 0.362,
     0.692, 0.187, 0.363, 0.686, 0.160, 0.000, 0.680, 0.945, 0.000, 0.686,
     0.937, 0.000, 0.692, 0.930, 0.000, 0.698, 0.922, 0.000, 0.703, 0.915,
     0.000, 0.709, 0.908, 0.000, 0.715, 0.901, 0.000, 0.720, 0.894, 0.000,
     0.726, 0.888, 0.000, 0.731, 0.881, 0.007, 0.736, 0.875, 0.084, 0.741,
     0.869, 0.127, 0.746, 0.862, 0.159, 0.751, 0.856, 0.185, 0.755, 0.850,
     0.208, 0.760, 0.843, 0.227, 0.764, 0.837, 0.245, 0.768, 0.830, 0.260,
     0.772, 0.824, 0.275, 0.776, 0.817, 0.288, 0.779, 0.811, 0.300, 0.783,
     0.804, 0.310, 0.786, 0.797, 0.320, 0.789, 0.789, 0.329, 0.792, 0.782,
     0.337, 0.794, 0.774, 0.345, 0.796, 0.766, 0.351, 0.798, 0.758, 0.357,
     0.800, 0.749, 0.363, 0.801, 0.740, 0.367, 0.803, 0.731, 0.371, 0.803,
     0.721, 0.375, 0.804, 0.711, 0.378, 0.804, 0.701, 0.380, 0.804, 0.690,
     0.382, 0.804, 0.679, 0.384, 0.803, 0.667, 0.385, 0.802, 0.654, 0.386,
     0.801, 0.642, 0.386, 0.800, 0.629, 0.387, 0.798, 0.615, 0.387, 0.796,
     0.601, 0.387, 0.793, 0.587, 0.387, 0.791, 0.572, 0.387, 0.788, 0.557,
     0.386, 0.785, 0.541, 0.386, 0.781, 0.525, 0.385, 0.778, 0.509, 0.385,
     0.774, 0.492, 0.385, 0.770, 0.475, 0.384, 0.765, 0.457, 0.384, 0.761,
     0.440, 0.384, 0.756, 0.422, 0.384, 0.751, 0.403, 0.384, 0.746, 0.384,
     0.384, 0.741, 0.365, 0.384, 0.735, 0.346, 0.384, 0.730, 0.326, 0.384,
     0.724, 0.305, 0.384, 0.718, 0.284, 0.385, 0.712, 0.263, 0.385, 0.706,
     0.240, 0.386, 0.700, 0.217, 0.386, 0.694, 0.192, 0.387, 0.687, 0.165,
     0.000, 0.680, 0.948, 0.000, 0.687, 0.940, 0.000, 0.693, 0.933, 0.000,
     0.699, 0.925, 0.000, 0.705, 0.918, 0.000, 0.711, 0.912, 0.000, 0.716,
     0.905, 0.000, 0.722, 0.898, 0.050, 0.728, 0.892, 0.109, 0.733, 0.886,
     0.147, 0.738, 0.879, 0.177, 0.743, 0.873, 0.202, 0.748, 0.867, 0.224,
     0.753, 0.861, 0.243, 0.758, 0.855, 0.261, 0.763, 0.849, 0.277, 0.767,
     0.842, 0.292, 0.771, 0.836, 0.305, 0.775, 0.830, 0.318, 0.779, 0.823,
     0.329, 0.783, 0.817, 0.340, 0.787, 0.810, 0.350, 0.790, 0.803, 0.359,
     0.793, 0.796, 0.367, 0.796, 0.789, 0.374, 0.798, 0.782, 0.381, 0.801,
     0.774, 0.387, 0.803, 0.766, 0.393, 0.804, 0.757, 0.397, 0.806, 0.748,
     0.402, 0.807, 0.739, 0.405, 0.808, 0.729, 0.408, 0.809, 0.719, 0.411,
     0.809, 0.709, 0.413, 0.809, 0.698, 0.415, 0.808, 0.687, 0.416, 0.808,
     0.675, 0.417, 0.807, 0.663, 0.417, 0.806, 0.650, 0.417, 0.804, 0.637,
     0.418, 0.802, 0.623, 0.417, 0.800, 0.609, 0.417, 0.798, 0.594, 0.416,
     0.795, 0.579, 0.416, 0.792, 0.564, 0.415, 0.789, 0.548, 0.414, 0.785,
     0.532, 0.414, 0.781, 0.515, 0.413, 0.777, 0.499, 0.412, 0.773, 0.481,
     0.412, 0.769, 0.464, 0.411, 0.764, 0.446, 0.410, 0.759, 0.428, 0.410,
     0.754, 0.409, 0.409, 0.749, 0.390, 0.409, 0.743, 0.371, 0.409, 0.738,
     0.351, 0.409, 0.732, 0.331, 0.408, 0.726, 0.310, 0.408, 0.720, 0.289,
     0.408, 0.714, 0.268, 0.408, 0.708, 0.245, 0.409, 0.702, 0.222, 0.409,
     0.695, 0.197, 0.409, 0.689, 0.170, 0.000, 0.681, 0.950, 0.000, 0.688,
     0.943, 0.000, 0.694, 0.936, 0.000, 0.700, 0.929, 0.000, 0.706, 0.922,
     0.000, 0.712, 0.915, 0.074, 0.718, 0.908, 0.124, 0.724, 0.902, 0.159,
     0.730, 0.896, 0.188, 0.735, 0.890, 0.213, 0.740, 0.884, 0.235, 0.746,
     0.878, 0.255, 0.751, 0.872, 0.273, 0.756, 0.866, 0.289, 0.761, 0.860,
     0.305, 0.766, 0.854, 0.319, 0.770, 0.848, 0.332, 0.775, 0.842, 0.344,
     0.779, 0.836, 0.356, 0.783, 0.830, 0.366, 0.787, 0.823, 0.376, 0.790,
     0.817, 0.385, 0.794, 0.810, 0.394, 0.797, 0.803, 0.401, 0.800, 0.796,
     0.408, 0.802, 0.789, 0.414, 0.805, 0.781, 0.420, 0.807, 0.773, 0.425,
     0.809, 0.765, 0.430, 0.810, 0.756, 0.433, 0.812, 0.747, 0.437, 0.813,
     0.738, 0.440, 0.813, 0.728, 0.442, 0.814, 0.717, 0.444, 0.813, 0.706,
     0.445, 0.813, 0.695, 0.446, 0.812, 0.683, 0.446, 0.811, 0.671, 0.447,
     0.810, 0.658, 0.447, 0.809, 0.645, 0.446, 0.807, 0.631, 0.446, 0.804,
     0.617, 0.445, 0.802, 0.602, 0.444, 0.799, 0.587, 0.443, 0.796, 0.571,
     0.442, 0.792, 0.555, 0.441, 0.789, 0.539, 0.440, 0.785, 0.522, 0.439,
     0.781, 0.505, 0.438, 0.776, 0.488, 0.437, 0.772, 0.470, 0.436, 0.767,
     0.452, 0.435, 0.762, 0.433, 0.435, 0.757, 0.415, 0.434, 0.751, 0.396,
     0.433, 0.746, 0.376, 0.432, 0.740, 0.356, 0.432, 0.734, 0.336, 0.431,
     0.728, 0.315, 0.431, 0.722, 0.294, 0.431, 0.716, 0.272, 0.430, 0.710,
     0.250, 0.430, 0.703, 0.226, 0.430, 0.697, 0.201, 0.430, 0.690, 0.175,
     0.000, 0.682, 0.953, 0.000, 0.689, 0.946, 0.000, 0.695, 0.938, 0.002,
     0.701, 0.932, 0.086, 0.708, 0.925, 0.133, 0.714, 0.918, 0.167, 0.720,
     0.912, 0.196, 0.726, 0.906, 0.221, 0.731, 0.900, 0.243, 0.737, 0.894,
     0.263, 0.743, 0.888, 0.281, 0.748, 0.882, 0.298, 0.753, 0.876, 0.314,
     0.759, 0.870, 0.329, 0.764, 0.865, 0.342, 0.768, 0.859, 0.355, 0.773,
     0.853, 0.368, 0.778, 0.847, 0.379, 0.782, 0.842, 0.390, 0.786, 0.836,
     0.400, 0.790, 0.830, 0.409, 0.794, 0.823, 0.417, 0.798, 0.817, 0.425,
     0.801, 0.810, 0.433, 0.804, 0.803, 0.439, 0.807, 0.796, 0.445, 0.809,
     0.789, 0.451, 0.811, 0.781, 0.456, 0.813, 0.773, 0.460, 0.815, 0.764,
     0.463, 0.816, 0.755, 0.466, 0.817, 0.746, 0.469, 0.818, 0.736, 0.471,
     0.818, 0.725, 0.472, 0.818, 0.715, 0.473, 0.818, 0.703, 0.474, 0.817,
     0.691, 0.474, 0.816, 0.679, 0.474, 0.815, 0.666, 0.474, 0.813, 0.653,
     0.473, 0.811, 0.639, 0.473, 0.809, 0.624, 0.472, 0.806, 0.610, 0.471,
     0.803, 0.594, 0.469, 0.800, 0.579, 0.468, 0.796, 0.562, 0.467, 0.792,
     0.546, 0.466, 0.788, 0.529, 0.464, 0.784, 0.512, 0.463, 0.780, 0.494,
     0.462, 0.775, 0.476, 0.460, 0.770, 0.458, 0.459, 0.765, 0.439, 0.458,
     0.759, 0.420, 0.457, 0.754, 0.401, 0.456, 0.748, 0.381, 0.455, 0.742,
     0.361, 0.454, 0.736, 0.341, 0.453, 0.730, 0.320, 0.453, 0.724, 0.299,
     0.452, 0.718, 0.277, 0.452, 0.711, 0.254, 0.451, 0.705, 0.231, 0.451,
     0.698, 0.206, 0.450, 0.691, 0.179, 0.000, 0.683, 0.955, 0.013, 0.689,
     0.948, 0.092, 0.696, 0.941, 0.137, 0.702, 0.935, 0.171, 0.709, 0.928,
     0.200, 0.715, 0.922, 0.225, 0.721, 0.916, 0.247, 0.727, 0.909, 0.267,
     0.733, 0.904, 0.286, 0.739, 0.898, 0.303, 0.745, 0.892, 0.320, 0.750,
     0.886, 0.335, 0.756, 0.881, 0.350, 0.761, 0.875, 0.363, 0.766, 0.870,
     0.376, 0.771, 0.864, 0.388, 0.776, 0.859, 0.400, 0.781, 0.853, 0.411,
     0.785, 0.847, 0.421, 0.790, 0.842, 0.430, 0.794, 0.836, 0.439, 0.798,
     0.830, 0.448, 0.802, 0.824, 0.455, 0.805, 0.817, 0.462, 0.808, 0.810,
     0.469, 0.811, 0.804, 0.475, 0.814, 0.796, 0.480, 0.816, 0.789, 0.484,
     0.818, 0.781, 0.488, 0.820, 0.772, 0.492, 0.821, 0.763, 0.495, 0.822,
     0.754, 0.497, 0.823, 0.744, 0.499, 0.823, 0.734, 0.500, 0.823, 0.723,
     0.501, 0.823, 0.712, 0.501, 0.822, 0.700, 0.501, 0.821, 0.687, 0.501,
     0.819, 0.674, 0.500, 0.818, 0.661, 0.499, 0.815, 0.647, 0.498, 0.813,
     0.632, 0.497, 0.810, 0.617, 0.496, 0.807, 0.602, 0.494, 0.804, 0.586,
     0.493, 0.800, 0.569, 0.491, 0.796, 0.553, 0.490, 0.792, 0.536, 0.488,
     0.787, 0.518, 0.486, 0.783, 0.500, 0.485, 0.778, 0.482, 0.483, 0.773,
     0.463, 0.482, 0.767, 0.445, 0.480, 0.762, 0.425, 0.479, 0.756, 0.406,
     0.478, 0.750, 0.386, 0.477, 0.744, 0.366, 0.476, 0.738, 0.345, 0.475,
     0.732, 0.325, 0.474, 0.726, 0.303, 0.473, 0.719, 0.281, 0.472, 0.713,
     0.258, 0.471, 0.706, 0.235, 0.470, 0.699, 0.210, 0.469, 0.692, 0.184,
     0.095, 0.683, 0.958, 0.139, 0.690, 0.951, 0.173, 0.697, 0.944, 0.201,
     0.703, 0.938, 0.226, 0.710, 0.931, 0.249, 0.716, 0.925, 0.269, 0.723,
     0.919, 0.288, 0.729, 0.913, 0.306, 0.735, 0.907, 0.323, 0.741, 0.902,
     0.339, 0.747, 0.896, 0.354, 0.752, 0.891, 0.368, 0.758, 0.885, 0.382,
     0.764, 0.880, 0.394, 0.769, 0.875, 0.407, 0.774, 0.869, 0.418, 0.779,
     0.864, 0.429, 0.784, 0.859, 0.440, 0.789, 0.853, 0.450, 0.793, 0.848,
     0.459, 0.798, 0.842, 0.468, 0.802, 0.836, 0.476, 0.806, 0.830, 0.483,
     0.809, 0.824, 0.490, 0.812, 0.818, 0.496, 0.815, 0.811, 0.502, 0.818,
     0.804, 0.507, 0.821, 0.796, 0.512, 0.823, 0.789, 0.515, 0.825, 0.780,
     0.519, 0.826, 0.772, 0.521, 0.827, 0.762, 0.524, 0.828, 0.753, 0.525,
     0.828, 0.742, 0.526, 0.828, 0.732, 0.527, 0.828, 0.720, 0.527, 0.827,
     0.708, 0.527, 0.826, 0.696, 0.526, 0.824, 0.683, 0.525, 0.822, 0.669,
     0.524, 0.820, 0.655, 0.523, 0.817, 0.640, 0.522, 0.814, 0.625, 0.520,
     0.811, 0.609, 0.518, 0.808, 0.593, 0.516, 0.804, 0.576, 0.515, 0.800,
     0.559, 0.513, 0.795, 0.542, 0.511, 0.791, 0.524, 0.509, 0.786, 0.506,
     0.507, 0.781, 0.488, 0.505, 0.775, 0.469, 0.504, 0.770, 0.450, 0.502,
     0.764, 0.431, 0.500, 0.759, 0.411, 0.499, 0.753, 0.391, 0.497, 0.746,
     0.371, 0.496, 0.740, 0.350, 0.495, 0.734, 0.329, 0.494, 0.727, 0.307,
     0.492, 0.721, 0.285, 0.491, 0.714, 0.262, 0.490, 0.707, 0.239, 0.489,
     0.700, 0.214, 0.488, 0.693, 0.188, 0.172, 0.684, 0.961, 0.201, 0.691,
     0.954, 0.226, 0.698, 0.947, 0.248, 0.704, 0.941, 0.269, 0.711, 0.934,
     0.289, 0.717, 0.928, 0.307, 0.724, 0.922, 0.324, 0.730, 0.917, 0.340,
     0.736, 0.911, 0.356, 0.743, 0.906, 0.370, 0.749, 0.900, 0.384, 0.755,
     0.895, 0.398, 0.760, 0.890, 0.411, 0.766, 0.885, 0.423, 0.772, 0.880,
     0.435, 0.777, 0.874, 0.446, 0.782, 0.869, 0.457, 0.787, 0.864, 0.467,
     0.792, 0.859, 0.477, 0.797, 0.854, 0.486, 0.801, 0.848, 0.494, 0.806,
     0.843, 0.502, 0.810, 0.837, 0.510, 0.813, 0.831, 0.517, 0.817, 0.825,
     0.523, 0.820, 0.818, 0.528, 0.823, 0.811, 0.533, 0.825, 0.804, 0.538,
     0.828, 0.797, 0.542, 0.829, 0.788, 0.545, 0.831, 0.780, 0.547, 0.832,
     0.771, 0.549, 0.833, 0.761, 0.551, 0.833, 0.751, 0.552, 0.833, 0.740,
     0.552, 0.833, 0.729, 0.552, 0.832, 0.717, 0.551, 0.830, 0.704, 0.551,
     0.829, 0.691, 0.550, 0.827, 0.677, 0.548, 0.824, 0.663, 0.547, 0.822,
     0.648, 0.545, 0.819, 0.632, 0.543, 0.815, 0.617, 0.541, 0.812, 0.600,
     0.539, 0.808, 0.583, 0.537, 0.803, 0.566, 0.535, 0.799, 0.549, 0.533,
     0.794, 0.531, 0.531, 0.789, 0.512, 0.529, 0.784, 0.494, 0.527, 0.778,
     0.475, 0.525, 0.773, 0.455, 0.523, 0.767, 0.436, 0.521, 0.761, 0.416,
     0.519, 0.755, 0.396, 0.517, 0.748, 0.375, 0.516, 0.742, 0.354, 0.514,
     0.735, 0.333, 0.513, 0.729, 0.311, 0.511, 0.722, 0.289, 0.510, 0.715,
     0.266, 0.509, 0.708, 0.242, 0.507, 0.701, 0.218, 0.506, 0.694, 0.191,
     0.224, 0.684, 0.963, 0.247, 0.691, 0.956, 0.268, 0.698, 0.950, 0.287,
     0.705, 0.943, 0.305, 0.712, 0.937, 0.323, 0.719, 0.931, 0.339, 0.725,
     0.926, 0.355, 0.732, 0.920, 0.370, 0.738, 0.915, 0.385, 0.744, 0.909,
     0.399, 0.751, 0.904, 0.412, 0.757, 0.899, 0.425, 0.763, 0.894, 0.438,
     0.768, 0.889, 0.450, 0.774, 0.884, 0.461, 0.780, 0.879, 0.472, 0.785,
     0.875, 0.483, 0.790, 0.870, 0.493, 0.795, 0.865, 0.502, 0.800, 0.860,
     0.511, 0.805, 0.855, 0.520, 0.809, 0.849, 0.528, 0.814, 0.844, 0.535,
     0.818, 0.838, 0.542, 0.821, 0.832, 0.548, 0.824, 0.826, 0.554, 0.827,
     0.819, 0.559, 0.830, 0.812, 0.563, 0.832, 0.805, 0.567, 0.834, 0.797,
     0.570, 0.836, 0.788, 0.572, 0.837, 0.779, 0.574, 0.838, 0.770, 0.575,
     0.838, 0.760, 0.576, 0.838, 0.749, 0.576, 0.838, 0.737, 0.576, 0.837,
     0.725, 0.575, 0.835, 0.713, 0.574, 0.834, 0.699, 0.573, 0.831, 0.685,
     0.571, 0.829, 0.671, 0.570, 0.826, 0.656, 0.568, 0.823, 0.640, 0.566,
     0.819, 0.624, 0.563, 0.815, 0.607, 0.561, 0.811, 0.590, 0.559, 0.807,
     0.573, 0.556, 0.802, 0.555, 0.554, 0.797, 0.537, 0.552, 0.792, 0.518,
     0.549, 0.786, 0.499, 0.547, 0.781, 0.480, 0.545, 0.775, 0.460, 0.543,
     0.769, 0.441, 0.541, 0.763, 0.420, 0.539, 0.756, 0.400, 0.537, 0.750,
     0.379, 0.535, 0.743, 0.358, 0.533, 0.737, 0.337, 0.531, 0.730, 0.315,
     0.530, 0.723, 0.293, 0.528, 0.716, 0.270, 0.527, 0.709, 0.246, 0.525,
     0.702, 0.221, 0.524, 0.694, 0.195, 0.265, 0.685, 0.965, 0.284, 0.692,
     0.959, 0.303, 0.699, 0.952, 0.320, 0.706, 0.946, 0.337, 0.713, 0.940,
     0.353, 0.720, 0.935, 0.369, 0.726, 0.929, 0.384, 0.733, 0.924, 0.398,
     0.739, 0.918, 0.412, 0.746, 0.913, 0.425, 0.752, 0.908, 0.438, 0.759,
     0.903, 0.451, 0.765, 0.899, 0.463, 0.771, 0.894, 0.475, 0.777, 0.889,
     0.486, 0.782, 0.884, 0.497, 0.788, 0.880, 0.507, 0.793, 0.875, 0.517,
     0.799, 0.870, 0.527, 0.804, 0.866, 0.536, 0.809, 0.861, 0.544, 0.813,
     0.856, 0.552, 0.818, 0.850, 0.560, 0.822, 0.845, 0.566, 0.826, 0.839,
     0.573, 0.829, 0.833, 0.578, 0.832, 0.827, 0.583, 0.835, 0.820, 0.587,
     0.837, 0.813, 0.591, 0.839, 0.805, 0.594, 0.841, 0.797, 0.596, 0.842,
     0.788, 0.598, 0.843, 0.778, 0.599, 0.843, 0.768, 0.600, 0.843, 0.758,
     0.600, 0.843, 0.746, 0.599, 0.842, 0.734, 0.599, 0.840, 0.721, 0.597,
     0.838, 0.708, 0.596, 0.836, 0.694, 0.594, 0.834, 0.679, 0.592, 0.831,
     0.663, 0.590, 0.827, 0.648, 0.587, 0.823, 0.631, 0.585, 0.819, 0.614,
     0.582, 0.815, 0.597, 0.580, 0.810, 0.579, 0.577, 0.805, 0.561, 0.575,
     0.800, 0.542, 0.572, 0.795, 0.524, 0.569, 0.789, 0.504, 0.567, 0.783,
     0.485, 0.565, 0.777, 0.465, 0.562, 0.771, 0.445, 0.560, 0.765, 0.425,
     0.558, 0.758, 0.404, 0.556, 0.752, 0.383, 0.554, 0.745, 0.362, 0.552,
     0.738, 0.341, 0.550, 0.731, 0.319, 0.548, 0.724, 0.296, 0.546, 0.717,
     0.273, 0.544, 0.709, 0.249, 0.542, 0.702, 0.224, 0.541, 0.695, 0.198,
     0.299, 0.685, 0.968, 0.317, 0.692, 0.961, 0.334, 0.699, 0.955, 0.350,
     0.706, 0.949, 0.366, 0.713, 0.943, 0.381, 0.720, 0.938, 0.395, 0.727,
     0.932, 0.410, 0.734, 0.927, 0.423, 0.741, 0.922, 0.437, 0.747, 0.917,
     0.450, 0.754, 0.912, 0.463, 0.760, 0.907, 0.475, 0.767, 0.903, 0.487,
     0.773, 0.898, 0.498, 0.779, 0.894, 0.509, 0.785, 0.889, 0.520, 0.791,
     0.885, 0.531, 0.796, 0.880, 0.540, 0.802, 0.876, 0.550, 0.807, 0.871,
     0.559, 0.812, 0.867, 0.568, 0.817, 0.862, 0.576, 0.822, 0.857, 0.583,
     0.826, 0.852, 0.590, 0.830, 0.847, 0.596, 0.834, 0.841, 0.602, 0.837,
     0.835, 0.607, 0.840, 0.828, 0.611, 0.843, 0.821, 0.615, 0.845, 0.814,
     0.618, 0.846, 0.805, 0.620, 0.848, 0.797, 0.622, 0.848, 0.787, 0.623,
     0.849, 0.777, 0.623, 0.849, 0.766, 0.623, 0.848, 0.755, 0.622, 0.847,
     0.743, 0.621, 0.845, 0.730, 0.620, 0.843, 0.716, 0.618, 0.841, 0.702,
     0.616, 0.838, 0.687, 0.613, 0.835, 0.671, 0.611, 0.831, 0.655, 0.608,
     0.827, 0.638, 0.606, 0.823, 0.621, 0.603, 0.818, 0.604, 0.600, 0.814,
     0.585, 0.597, 0.808, 0.567, 0.594, 0.803, 0.548, 0.592, 0.797, 0.529,
     0.589, 0.792, 0.510, 0.586, 0.785, 0.490, 0.584, 0.779, 0.470, 0.581,
     0.773, 0.450, 0.579, 0.766, 0.429, 0.576, 0.760, 0.408, 0.574, 0.753,
     0.387, 0.572, 0.746, 0.366, 0.569, 0.739, 0.344, 0.567, 0.732, 0.322,
     0.565, 0.725, 0.299, 0.563, 0.717, 0.276, 0.561, 0.710, 0.252, 0.559,
     0.703, 0.227, 0.557, 0.695, 0.201, 0.329, 0.685, 0.970, 0.346, 0.692,
     0.964, 0.362, 0.699, 0.958, 0.377, 0.707, 0.952, 0.392, 0.714, 0.946,
     0.406, 0.721, 0.941, 0.420, 0.728, 0.935, 0.434, 0.735, 0.930, 0.447,
     0.742, 0.925, 0.460, 0.749, 0.920, 0.473, 0.756, 0.916, 0.485, 0.762,
     0.911, 0.497, 0.769, 0.907, 0.509, 0.775, 0.903, 0.521, 0.781, 0.898,
     0.532, 0.788, 0.894, 0.542, 0.794, 0.890, 0.553, 0.799, 0.886, 0.563,
     0.805, 0.882, 0.572, 0.811, 0.877, 0.581, 0.816, 0.873, 0.590, 0.821,
     0.868, 0.598, 0.826, 0.864, 0.606, 0.830, 0.859, 0.613, 0.834, 0.854,
     0.619, 0.838, 0.848, 0.625, 0.842, 0.842, 0.630, 0.845, 0.836, 0.634,
     0.848, 0.829, 0.638, 0.850, 0.822, 0.641, 0.852, 0.814, 0.643, 0.853,
     0.805, 0.645, 0.854, 0.796, 0.645, 0.854, 0.786, 0.646, 0.854, 0.775,
     0.645, 0.853, 0.764, 0.645, 0.852, 0.751, 0.643, 0.851, 0.738, 0.642,
     0.848, 0.725, 0.639, 0.846, 0.710, 0.637, 0.843, 0.695, 0.635, 0.839,
     0.679, 0.632, 0.836, 0.662, 0.629, 0.831, 0.645, 0.626, 0.827, 0.628,
     0.623, 0.822, 0.610, 0.620, 0.817, 0.592, 0.617, 0.811, 0.573, 0.614,
     0.806, 0.554, 0.611, 0.800, 0.534, 0.608, 0.794, 0.515, 0.605, 0.788,
     0.495, 0.602, 0.781, 0.474, 0.599, 0.775, 0.454, 0.597, 0.768, 0.433,
     0.594, 0.761, 0.412, 0.592, 0.754, 0.391, 0.589, 0.747, 0.369, 0.587,
     0.740, 0.347, 0.584, 0.733, 0.325, 0.582, 0.725, 0.302, 0.580, 0.718,
     0.279, 0.577, 0.710, 0.255, 0.575, 0.703, 0.230, 0.573, 0.695, 0.204,
     0.357, 0.685, 0.972, 0.372, 0.692, 0.966, 0.387, 0.700, 0.960, 0.401,
     0.707, 0.954, 0.416, 0.714, 0.949, 0.429, 0.722, 0.943, 0.443, 0.729,
     0.938, 0.456, 0.736, 0.933, 0.469, 0.743, 0.929, 0.482, 0.750, 0.924,
     0.494, 0.757, 0.919, 0.507, 0.764, 0.915, 0.519, 0.771, 0.911, 0.530,
     0.777, 0.907, 0.542, 0.784, 0.903, 0.553, 0.790, 0.899, 0.563, 0.796,
     0.895, 0.574, 0.802, 0.891, 0.584, 0.808, 0.887, 0.593, 0.814, 0.883,
     0.603, 0.820, 0.879, 0.611, 0.825, 0.875, 0.620, 0.830, 0.870, 0.627,
     0.835, 0.866, 0.635, 0.839, 0.861, 0.641, 0.843, 0.856, 0.647, 0.847,
     0.850, 0.652, 0.850, 0.844, 0.657, 0.853, 0.838, 0.660, 0.855, 0.831,
     0.663, 0.857, 0.823, 0.666, 0.859, 0.814, 0.667, 0.859, 0.805, 0.668,
     0.860, 0.795, 0.668, 0.860, 0.784, 0.667, 0.859, 0.773, 0.666, 0.858,
     0.760, 0.665, 0.856, 0.747, 0.663, 0.853, 0.733, 0.661, 0.851, 0.718,
     0.658, 0.847, 0.703, 0.655, 0.844, 0.687, 0.652, 0.840, 0.670, 0.649,
     0.835, 0.652, 0.646, 0.830, 0.635, 0.642, 0.825, 0.616, 0.639, 0.820,
     0.598, 0.636, 0.814, 0.579, 0.633, 0.808, 0.559, 0.629, 0.802, 0.539,
     0.626, 0.796, 0.519, 0.623, 0.790, 0.499, 0.620, 0.783, 0.479, 0.617,
     0.776, 0.458, 0.614, 0.769, 0.437, 0.611, 0.762, 0.416, 0.609, 0.755,
     0.394, 0.606, 0.748, 0.372, 0.603, 0.740, 0.350, 0.601, 0.733, 0.328,
     0.598, 0.726, 0.305, 0.596, 0.718, 0.282, 0.593, 0.710, 0.257, 0.591,
     0.703, 0.232, 0.589, 0.695, 0.206, 0.381, 0.684, 0.974, 0.396, 0.692,
     0.968, 0.410, 0.700, 0.962, 0.424, 0.707, 0.957, 0.438, 0.715, 0.951,
     0.451, 0.722, 0.946, 0.464, 0.729, 0.941, 0.477, 0.737, 0.936, 0.490,
     0.744, 0.932, 0.503, 0.751, 0.927, 0.515, 0.758, 0.923, 0.527, 0.765,
     0.919, 0.539, 0.772, 0.915, 0.550, 0.779, 0.911, 0.562, 0.786, 0.907,
     0.573, 0.792, 0.903, 0.584, 0.799, 0.900, 0.594, 0.805, 0.896, 0.604,
     0.811, 0.892, 0.614, 0.817, 0.889, 0.623, 0.823, 0.885, 0.632, 0.829,
     0.881, 0.641, 0.834, 0.877, 0.649, 0.839, 0.873, 0.656, 0.844, 0.868,
     0.663, 0.848, 0.863, 0.669, 0.852, 0.858, 0.674, 0.855, 0.852, 0.679,
     0.858, 0.846, 0.682, 0.861, 0.839, 0.685, 0.863, 0.832, 0.688, 0.864,
     0.823, 0.689, 0.865, 0.814, 0.690, 0.865, 0.804, 0.690, 0.865, 0.794,
     0.689, 0.864, 0.782, 0.688, 0.863, 0.769, 0.686, 0.861, 0.756, 0.684,
     0.858, 0.742, 0.681, 0.855, 0.726, 0.678, 0.852, 0.711, 0.675, 0.848,
     0.694, 0.672, 0.844, 0.677, 0.668, 0.839, 0.659, 0.665, 0.834, 0.641,
     0.662, 0.829, 0.622, 0.658, 0.823, 0.603, 0.655, 0.817, 0.584, 0.651,
     0.811, 0.564, 0.648, 0.805, 0.544, 0.644, 0.798, 0.524, 0.641, 0.791,
     0.503, 0.638, 0.785, 0.483, 0.635, 0.778, 0.462, 0.631, 0.770, 0.440,
     0.628, 0.763, 0.419, 0.625, 0.756, 0.397, 0.623, 0.748, 0.375, 0.620,
     0.741, 0.353, 0.617, 0.733, 0.330, 0.614, 0.726, 0.307, 0.612, 0.718,
     0.284, 0.609, 0.710, 0.260, 0.606, 0.702, 0.235, 0.604, 0.694, 0.208,
     0.404, 0.684, 0.977, 0.418, 0.692, 0.971, 0.432, 0.699, 0.965, 0.445,
     0.707, 0.959, 0.458, 0.715, 0.954, 0.472, 0.722, 0.949, 0.484, 0.730,
     0.944, 0.497, 0.737, 0.939, 0.510, 0.745, 0.935, 0.522, 0.752, 0.931,
     0.534, 0.759, 0.926, 0.546, 0.767, 0.922, 0.558, 0.774, 0.919, 0.569,
     0.781, 0.915, 0.581, 0.788, 0.911, 0.592, 0.794, 0.908, 0.603, 0.801,
     0.904, 0.613, 0.808, 0.901, 0.624, 0.814, 0.897, 0.633, 0.820, 0.894,
     0.643, 0.826, 0.891, 0.652, 0.832, 0.887, 0.661, 0.838, 0.883, 0.669,
     0.843, 0.879, 0.677, 0.848, 0.875, 0.684, 0.853, 0.871, 0.690, 0.857,
     0.866, 0.695, 0.860, 0.860, 0.700, 0.864, 0.855, 0.704, 0.866, 0.848,
     0.707, 0.869, 0.841, 0.709, 0.870, 0.833, 0.711, 0.871, 0.824, 0.711,
     0.871, 0.814, 0.711, 0.871, 0.803, 0.710, 0.870, 0.791, 0.709, 0.868,
     0.778, 0.707, 0.866, 0.765, 0.704, 0.864, 0.750, 0.701, 0.860, 0.735,
     0.698, 0.857, 0.718, 0.695, 0.852, 0.702, 0.691, 0.848, 0.684, 0.688,
     0.843, 0.666, 0.684, 0.837, 0.647, 0.680, 0.832, 0.628, 0.676, 0.826,
     0.609, 0.673, 0.820, 0.589, 0.669, 0.813, 0.569, 0.665, 0.807, 0.549,
     0.662, 0.800, 0.528, 0.658, 0.793, 0.507, 0.655, 0.786, 0.486, 0.651,
     0.779, 0.465, 0.648, 0.771, 0.444, 0.645, 0.764, 0.422, 0.642, 0.756,
     0.400, 0.639, 0.749, 0.378, 0.636, 0.741, 0.356, 0.633, 0.733, 0.333,
     0.630, 0.726, 0.310, 0.627, 0.718, 0.286, 0.624, 0.710, 0.262, 0.621,
     0.702, 0.237, 0.619, 0.694, 0.210, 0.425, 0.683, 0.979, 0.439, 0.691,
     0.973, 0.452, 0.699, 0.967, 0.465, 0.707, 0.962, 0.478, 0.715, 0.956,
     0.491, 0.722, 0.951, 0.503, 0.730, 0.947, 0.516, 0.738, 0.942, 0.528,
     0.745, 0.938, 0.540, 0.753, 0.934, 0.552, 0.760, 0.930, 0.564, 0.768,
     0.926, 0.576, 0.775, 0.922, 0.588, 0.782, 0.919, 0.599, 0.789, 0.915,
     0.610, 0.797, 0.912, 0.621, 0.803, 0.909, 0.632, 0.810, 0.906, 0.642,
     0.817, 0.902, 0.652, 0.823, 0.899, 0.662, 0.830, 0.896, 0.671, 0.836,
     0.893, 0.680, 0.842, 0.890, 0.689, 0.847, 0.886, 0.697, 0.853, 0.882,
     0.704, 0.857, 0.878, 0.710, 0.862, 0.874, 0.716, 0.866, 0.869, 0.721,
     0.869, 0.863, 0.725, 0.872, 0.857, 0.729, 0.874, 0.850, 0.731, 0.876,
     0.842, 0.732, 0.877, 0.833, 0.733, 0.877, 0.823, 0.732, 0.877, 0.812,
     0.731, 0.876, 0.800, 0.729, 0.874, 0.787, 0.727, 0.872, 0.773, 0.724,
     0.869, 0.759, 0.721, 0.865, 0.743, 0.718, 0.861, 0.726, 0.714, 0.857,
     0.709, 0.710, 0.852, 0.691, 0.706, 0.846, 0.672, 0.702, 0.841, 0.653,
     0.698, 0.835, 0.634, 0.694, 0.828, 0.614, 0.690, 0.822, 0.594, 0.686,
     0.815, 0.574, 0.683, 0.808, 0.553, 0.679, 0.801, 0.532, 0.675, 0.794,
     0.511, 0.672, 0.787, 0.490, 0.668, 0.779, 0.468, 0.665, 0.772, 0.446,
     0.661, 0.764, 0.425, 0.658, 0.757, 0.403, 0.654, 0.749, 0.380, 0.651,
     0.741, 0.358, 0.648, 0.733, 0.335, 0.645, 0.725, 0.312, 0.642, 0.717,
     0.288, 0.639, 0.709, 0.264, 0.636, 0.701, 0.238, 0.633, 0.693, 0.212,
     0.445, 0.682, 0.981, 0.458, 0.691, 0.975, 0.471, 0.699, 0.969, 0.484,
     0.707, 0.964, 0.496, 0.715, 0.959, 0.509, 0.722, 0.954, 0.521, 0.730,
     0.949, 0.534, 0.738, 0.945, 0.546, 0.746, 0.941, 0.558, 0.753, 0.937,
     0.570, 0.761, 0.933, 0.582, 0.769, 0.929, 0.593, 0.776, 0.926, 0.605,
     0.784, 0.922, 0.616, 0.791, 0.919, 0.628, 0.798, 0.916, 0.639, 0.806,
     0.913, 0.649, 0.813, 0.910, 0.660, 0.820, 0.907, 0.670, 0.826, 0.904,
     0.680, 0.833, 0.902, 0.690, 0.839, 0.899, 0.699, 0.846, 0.896, 0.708,
     0.851, 0.893, 0.716, 0.857, 0.889, 0.724, 0.862, 0.885, 0.731, 0.867,
     0.881, 0.737, 0.871, 0.877, 0.742, 0.875, 0.872, 0.746, 0.878, 0.866,
     0.750, 0.880, 0.859, 0.752, 0.882, 0.851, 0.753, 0.883, 0.843, 0.754,
     0.883, 0.833, 0.753, 0.883, 0.822, 0.752, 0.882, 0.810, 0.750, 0.880,
     0.797, 0.747, 0.877, 0.782, 0.744, 0.874, 0.767, 0.740, 0.870, 0.751,
     0.737, 0.866, 0.734, 0.733, 0.861, 0.716, 0.729, 0.855, 0.697, 0.724,
     0.850, 0.678, 0.720, 0.844, 0.659, 0.716, 0.837, 0.639, 0.712, 0.831,
     0.619, 0.708, 0.824, 0.598, 0.704, 0.817, 0.578, 0.699, 0.810, 0.557,
     0.696, 0.803, 0.535, 0.692, 0.795, 0.514, 0.688, 0.788, 0.493, 0.684,
     0.780, 0.471, 0.680, 0.772, 0.449, 0.677, 0.765, 0.427, 0.673, 0.757,
     0.405, 0.670, 0.749, 0.382, 0.666, 0.741, 0.360, 0.663, 0.733, 0.337,
     0.660, 0.725, 0.313, 0.657, 0.716, 0.289, 0.653, 0.708, 0.265, 0.650,
     0.700, 0.240, 0.647, 0.692, 0.213, 0.464, 0.681, 0.982, 0.476, 0.690,
     0.977, 0.489, 0.698, 0.971, 0.501, 0.706, 0.966, 0.514, 0.714, 0.961,
     0.526, 0.722, 0.956, 0.538, 0.730, 0.952, 0.550, 0.738, 0.947, 0.562,
     0.746, 0.943, 0.574, 0.754, 0.939, 0.586, 0.762, 0.936, 0.598, 0.769,
     0.932, 0.610, 0.777, 0.929, 0.621, 0.785, 0.926, 0.633, 0.792, 0.923,
     0.644, 0.800, 0.920, 0.655, 0.807, 0.917, 0.666, 0.815, 0.915, 0.677,
     0.822, 0.912, 0.688, 0.829, 0.909, 0.698, 0.836, 0.907, 0.708, 0.843,
     0.904, 0.717, 0.849, 0.902, 0.727, 0.855, 0.899, 0.735, 0.861, 0.896,
     0.743, 0.867, 0.893, 0.750, 0.872, 0.889, 0.757, 0.877, 0.885, 0.762,
     0.881, 0.880, 0.767, 0.884, 0.875, 0.770, 0.887, 0.868, 0.773, 0.888,
     0.861, 0.774, 0.889, 0.852, 0.774, 0.890, 0.842, 0.774, 0.889, 0.831,
     0.772, 0.888, 0.819, 0.770, 0.885, 0.806, 0.767, 0.883, 0.791, 0.763,
     0.879, 0.775, 0.759, 0.875, 0.759, 0.755, 0.870, 0.741, 0.751, 0.865,
     0.723, 0.747, 0.859, 0.704, 0.742, 0.853, 0.684, 0.738, 0.847, 0.664,
     0.733, 0.840, 0.644, 0.729, 0.833, 0.623, 0.724, 0.826, 0.603, 0.720,
     0.819, 0.581, 0.716, 0.811, 0.560, 0.712, 0.804, 0.539, 0.708, 0.796,
     0.517, 0.704, 0.788, 0.495, 0.700, 0.780, 0.473, 0.696, 0.772, 0.451,
     0.692, 0.764, 0.429, 0.688, 0.756, 0.407, 0.685, 0.748, 0.384, 0.681,
     0.740, 0.361, 0.678, 0.732, 0.338, 0.674, 0.724, 0.315, 0.671, 0.715,
     0.291, 0.667, 0.707, 0.266, 0.664, 0.699, 0.241, 0.661, 0.691, 0.214,
     0.481, 0.680, 0.984, 0.494, 0.689, 0.978, 0.506, 0.697, 0.973, 0.518,
     0.705, 0.968, 0.530, 0.713, 0.963, 0.542, 0.722, 0.958, 0.554, 0.730,
     0.954, 0.566, 0.738, 0.950, 0.578, 0.746, 0.946, 0.590, 0.754, 0.942,
     0.602, 0.762, 0.939, 0.614, 0.770, 0.935, 0.626, 0.778, 0.932, 0.637,
     0.786, 0.929, 0.649, 0.794, 0.926, 0.660, 0.801, 0.924, 0.671, 0.809,
     0.921, 0.683, 0.817, 0.919, 0.694, 0.824, 0.916, 0.704, 0.832, 0.914,
     0.715, 0.839, 0.912, 0.725, 0.846, 0.910, 0.735, 0.853, 0.908, 0.744,
     0.859, 0.905, 0.753, 0.866, 0.903, 0.762, 0.872, 0.900, 0.770, 0.877,
     0.897, 0.776, 0.882, 0.893, 0.782, 0.886, 0.889, 0.787, 0.890, 0.884,
     0.791, 0.893, 0.878, 0.794, 0.895, 0.871, 0.795, 0.896, 0.862, 0.795,
     0.896, 0.852, 0.794, 0.895, 0.841, 0.792, 0.894, 0.829, 0.789, 0.891,
     0.815, 0.786, 0.888, 0.800, 0.782, 0.884, 0.783, 0.778, 0.879, 0.766,
     0.774, 0.874, 0.748, 0.769, 0.868, 0.729, 0.764, 0.862, 0.710, 0.760,
     0.856, 0.690, 0.755, 0.849, 0.669, 0.750, 0.842, 0.649, 0.745, 0.835,
     0.628, 0.741, 0.827, 0.606, 0.736, 0.820, 0.585, 0.732, 0.812, 0.563,
     0.728, 0.804, 0.542, 0.723, 0.796, 0.520, 0.719, 0.788, 0.498, 0.715,
     0.780, 0.475, 0.711, 0.772, 0.453, 0.707, 0.764, 0.431, 0.703, 0.756,
     0.408, 0.699, 0.748, 0.386, 0.696, 0.739, 0.363, 0.692, 0.731, 0.339,
     0.688, 0.723, 0.316, 0.685, 0.714, 0.292, 0.681, 0.706, 0.267, 0.678,
     0.697, 0.242, 0.674, 0.689, 0.215, 0.498, 0.679, 0.986, 0.510, 0.687,
     0.980, 0.522, 0.696, 0.975, 0.534, 0.704, 0.970, 0.546, 0.712, 0.965,
     0.558, 0.721, 0.961, 0.570, 0.729, 0.956, 0.581, 0.737, 0.952, 0.593,
     0.746, 0.948, 0.605, 0.754, 0.945, 0.617, 0.762, 0.941, 0.629, 0.770,
     0.938, 0.640, 0.778, 0.935, 0.652, 0.786, 0.932, 0.664, 0.794, 0.930,
     0.675, 0.802, 0.927, 0.687, 0.810, 0.925, 0.698, 0.818, 0.923, 0.709,
     0.826, 0.921, 0.720, 0.834, 0.919, 0.731, 0.841, 0.917, 0.742, 0.849,
     0.915, 0.752, 0.856, 0.913, 0.762, 0.863, 0.911, 0.771, 0.870, 0.909,
     0.780, 0.876, 0.907, 0.788, 0.882, 0.904, 0.796, 0.887, 0.901, 0.802,
     0.892, 0.897, 0.807, 0.896, 0.893, 0.811, 0.899, 0.887, 0.814, 0.902,
     0.880, 0.815, 0.903, 0.872, 0.815, 0.903, 0.862, 0.814, 0.902, 0.851,
     0.812, 0.900, 0.838, 0.809, 0.897, 0.824, 0.805, 0.893, 0.808, 0.801,
     0.889, 0.791, 0.796, 0.884, 0.774, 0.791, 0.878, 0.755, 0.786, 0.872,
     0.735, 0.781, 0.865, 0.715, 0.776, 0.858, 0.695, 0.771, 0.851, 0.674,
     0.767, 0.844, 0.653, 0.762, 0.836, 0.631, 0.757, 0.829, 0.610, 0.752,
     0.821, 0.588, 0.748, 0.813, 0.566, 0.743, 0.805, 0.544, 0.739, 0.796,
     0.522, 0.734, 0.788, 0.500, 0.730, 0.780, 0.477, 0.726, 0.772, 0.455,
     0.722, 0.763, 0.432, 0.718, 0.755, 0.410, 0.714, 0.746, 0.387, 0.710,
     0.738, 0.364, 0.706, 0.730, 0.340, 0.702, 0.721, 0.317, 0.698, 0.713,
     0.293, 0.694, 0.704, 0.268, 0.691, 0.696, 0.243, 0.687, 0.687, 0.216,
     0.513, 0.677, 0.987, 0.525, 0.686, 0.982, 0.537, 0.694, 0.977, 0.549,
     0.703, 0.972, 0.561, 0.711, 0.967, 0.572, 0.720, 0.962, 0.584, 0.728,
     0.958, 0.596, 0.737, 0.954, 0.608, 0.745, 0.951, 0.619, 0.753, 0.947,
     0.631, 0.762, 0.944, 0.643, 0.770, 0.941, 0.655, 0.778, 0.938, 0.666,
     0.787, 0.935, 0.678, 0.795, 0.933, 0.689, 0.803, 0.930, 0.701, 0.811,
     0.928, 0.713, 0.820, 0.926, 0.724, 0.828, 0.925, 0.735, 0.836, 0.923,
     0.746, 0.844, 0.921, 0.757, 0.852, 0.920, 0.768, 0.859, 0.918, 0.778,
     0.867, 0.917, 0.788, 0.874, 0.915, 0.797, 0.881, 0.913, 0.806, 0.887,
     0.911, 0.814, 0.893, 0.909, 0.821, 0.898, 0.906, 0.827, 0.902, 0.902,
     0.831, 0.906, 0.897, 0.834, 0.908, 0.890, 0.836, 0.910, 0.882, 0.836,
     0.910, 0.873, 0.834, 0.909, 0.861, 0.832, 0.906, 0.848, 0.828, 0.903,
     0.833, 0.824, 0.899, 0.817, 0.819, 0.894, 0.799, 0.814, 0.888, 0.781,
     0.809, 0.882, 0.761, 0.804, 0.875, 0.741, 0.798, 0.868, 0.720, 0.793,
     0.861, 0.699, 0.788, 0.853, 0.678, 0.783, 0.845, 0.656, 0.777, 0.837,
     0.635, 0.772, 0.829, 0.613, 0.768, 0.821, 0.590, 0.763, 0.813, 0.568,
     0.758, 0.804, 0.546, 0.753, 0.796, 0.524, 0.749, 0.788, 0.501, 0.744,
     0.779, 0.479, 0.740, 0.771, 0.456, 0.736, 0.762, 0.433, 0.731, 0.754,
     0.411, 0.727, 0.745, 0.388, 0.723, 0.736, 0.365, 0.719, 0.728, 0.341,
     0.715, 0.719, 0.317, 0.711, 0.711, 0.293, 0.707, 0.702, 0.268, 0.704,
     0.694, 0.243, 0.700, 0.685, 0.216, 0.528, 0.675, 0.989, 0.540, 0.684,
     0.983, 0.551, 0.693, 0.978, 0.563, 0.701, 0.973, 0.575, 0.710, 0.969,
     0.586, 0.718, 0.964, 0.598, 0.727, 0.960, 0.610, 0.736, 0.956, 0.621,
     0.744, 0.953, 0.633, 0.753, 0.949, 0.645, 0.761, 0.946, 0.656, 0.770,
     0.943, 0.668, 0.778, 0.940, 0.680, 0.787, 0.938, 0.691, 0.795, 0.936,
     0.703, 0.804, 0.933, 0.715, 0.812, 0.932, 0.726, 0.821, 0.930, 0.738,
     0.829, 0.928, 0.749, 0.837, 0.927, 0.761, 0.846, 0.926, 0.772, 0.854,
     0.924, 0.783, 0.862, 0.923, 0.794, 0.870, 0.922, 0.804, 0.877, 0.921,
     0.814, 0.885, 0.920, 0.824, 0.892, 0.918, 0.832, 0.898, 0.917, 0.840,
     0.904, 0.914, 0.846, 0.909, 0.911, 0.851, 0.913, 0.906, 0.855, 0.915,
     0.901, 0.856, 0.917, 0.893, 0.856, 0.917, 0.883, 0.854, 0.915, 0.871,
     0.851, 0.913, 0.858, 0.847, 0.909, 0.842, 0.842, 0.904, 0.825, 0.837,
     0.898, 0.806, 0.831, 0.892, 0.787, 0.826, 0.885, 0.767, 0.820, 0.878,
     0.746, 0.814, 0.870, 0.725, 0.809, 0.862, 0.703, 0.803, 0.854, 0.681,
     0.798, 0.846, 0.659, 0.793, 0.838, 0.637, 0.788, 0.829, 0.615, 0.782,
     0.821, 0.592, 0.777, 0.812, 0.570, 0.773, 0.804, 0.548, 0.768, 0.795,
     0.525, 0.763, 0.787, 0.502, 0.758, 0.778, 0.480, 0.754, 0.769, 0.457,
     0.749, 0.761, 0.434, 0.745, 0.752, 0.411, 0.741, 0.743, 0.388, 0.737,
     0.735, 0.365, 0.732, 0.726, 0.342, 0.728, 0.717, 0.318, 0.724, 0.709,
     0.293, 0.720, 0.700, 0.269, 0.716, 0.691, 0.243, 0.712, 0.683, 0.216,
     0.542, 0.673, 0.990, 0.554, 0.682, 0.985, 0.565, 0.691, 0.980, 0.577,
     0.700, 0.975, 0.588, 0.708, 0.970, 0.600, 0.717, 0.966, 0.611, 0.726,
     0.962, 0.623, 0.734, 0.958, 0.634, 0.743, 0.955, 0.646, 0.752, 0.951,
     0.657, 0.760, 0.948, 0.669, 0.769, 0.945, 0.681, 0.778, 0.943, 0.692,
     0.786, 0.940, 0.704, 0.795, 0.938, 0.716, 0.804, 0.936, 0.728, 0.812,
     0.934, 0.739, 0.821, 0.933, 0.751, 0.830, 0.932, 0.763, 0.838, 0.930,
     0.774, 0.847, 0.929, 0.786, 0.856, 0.929, 0.797, 0.864, 0.928, 0.809,
     0.873, 0.927, 0.819, 0.881, 0.927, 0.830, 0.889, 0.926, 0.840, 0.896,
     0.925, 0.850, 0.903, 0.924, 0.858, 0.910, 0.922, 0.865, 0.915, 0.920,
     0.871, 0.920, 0.916, 0.875, 0.923, 0.911, 0.876, 0.924, 0.903, 0.876,
     0.924, 0.894, 0.873, 0.922, 0.882, 0.870, 0.919, 0.867, 0.865, 0.914,
     0.851, 0.860, 0.909, 0.832, 0.854, 0.902, 0.813, 0.848, 0.895, 0.793,
     0.842, 0.888, 0.772, 0.836, 0.880, 0.750, 0.830, 0.872, 0.729, 0.824,
     0.864, 0.707, 0.819, 0.855, 0.684, 0.813, 0.847, 0.662, 0.808, 0.838,
     0.639, 0.802, 0.829, 0.617, 0.797, 0.820, 0.594, 0.792, 0.812, 0.571,
     0.787, 0.803, 0.549, 0.782, 0.794, 0.526, 0.777, 0.785, 0.503, 0.772,
     0.776, 0.480, 0.767, 0.768, 0.458, 0.763, 0.759, 0.435, 0.758, 0.750,
     0.412, 0.754, 0.741, 0.388, 0.749, 0.732, 0.365, 0.745, 0.724, 0.342,
     0.741, 0.715, 0.318, 0.737, 0.706, 0.293, 0.732, 0.697, 0.269, 0.728,
     0.689, 0.243, 0.724, 0.680, 0.216, 0.556, 0.671, 0.992, 0.567, 0.680,
     0.986, 0.578, 0.689, 0.981, 0.590, 0.697, 0.976, 0.601, 0.706, 0.972,
     0.612, 0.715, 0.968, 0.624, 0.724, 0.964, 0.635, 0.733, 0.960, 0.646,
     0.741, 0.956, 0.658, 0.750, 0.953, 0.670, 0.759, 0.950, 0.681, 0.768,
     0.947, 0.693, 0.777, 0.945, 0.704, 0.786, 0.943, 0.716, 0.794, 0.941,
     0.728, 0.803, 0.939, 0.740, 0.812, 0.937, 0.752, 0.821, 0.936, 0.763,
     0.830, 0.935, 0.775, 0.839, 0.934, 0.787, 0.848, 0.933, 0.799, 0.857,
     0.932, 0.811, 0.866, 0.932, 0.822, 0.875, 0.932, 0.834, 0.883, 0.932,
     0.845, 0.892, 0.931, 0.856, 0.900, 0.931, 0.866, 0.908, 0.931, 0.876,
     0.915, 0.930, 0.884, 0.922, 0.929, 0.890, 0.927, 0.926, 0.895, 0.930,
     0.921, 0.896, 0.932, 0.914, 0.896, 0.932, 0.905, 0.893, 0.929, 0.892,
     0.888, 0.925, 0.876, 0.883, 0.920, 0.859, 0.877, 0.913, 0.840, 0.871,
     0.906, 0.819, 0.864, 0.898, 0.798, 0.858, 0.890, 0.776, 0.852, 0.882,
     0.754, 0.845, 0.873, 0.732, 0.839, 0.864, 0.709, 0.833, 0.855, 0.686,
     0.828, 0.846, 0.664, 0.822, 0.837, 0.641, 0.816, 0.828, 0.618, 0.811,
     0.819, 0.595, 0.806, 0.810, 0.572, 0.800, 0.801, 0.549, 0.795, 0.792,
     0.526, 0.790, 0.783, 0.504, 0.785, 0.774, 0.481, 0.781, 0.765, 0.458,
     0.776, 0.756, 0.435, 0.771, 0.748, 0.412, 0.766, 0.739, 0.388, 0.762,
     0.730, 0.365, 0.757, 0.721, 0.341, 0.753, 0.712, 0.318, 0.749, 0.703,
     0.293, 0.744, 0.695, 0.268, 0.740, 0.686, 0.243, 0.736, 0.677, 0.216,
     0.569, 0.668, 0.993, 0.580, 0.677, 0.987, 0.591, 0.686, 0.982, 0.602,
     0.695, 0.978, 0.613, 0.704, 0.973, 0.624, 0.713, 0.969, 0.635, 0.722,
     0.965, 0.647, 0.731, 0.961, 0.658, 0.740, 0.958, 0.670, 0.748, 0.955,
     0.681, 0.757, 0.952, 0.693, 0.766, 0.949, 0.704, 0.775, 0.947, 0.716,
     0.784, 0.945, 0.728, 0.793, 0.943, 0.739, 0.802, 0.941, 0.751, 0.812,
     0.939, 0.763, 0.821, 0.938, 0.775, 0.830, 0.937, 0.787, 0.839, 0.936,
     0.799, 0.848, 0.936, 0.811, 0.858, 0.936, 0.823, 0.867, 0.935, 0.835,
     0.876, 0.936, 0.847, 0.886, 0.936, 0.859, 0.895, 0.936, 0.870, 0.904,
     0.937, 0.882, 0.912, 0.937, 0.892, 0.920, 0.937, 0.901, 0.928, 0.937,
     0.909, 0.934, 0.936, 0.914, 0.938, 0.932, 0.917, 0.940, 0.926, 0.915,
     0.940, 0.916, 0.912, 0.936, 0.902, 0.906, 0.931, 0.885, 0.900, 0.925,
     0.866, 0.893, 0.917, 0.846, 0.887, 0.909, 0.824, 0.880, 0.900, 0.802,
     0.873, 0.891, 0.780, 0.867, 0.882, 0.757, 0.860, 0.873, 0.734, 0.854,
     0.864, 0.711, 0.848, 0.855, 0.688, 0.842, 0.845, 0.665, 0.836, 0.836,
     0.642, 0.830, 0.827, 0.619, 0.824, 0.818, 0.596, 0.819, 0.808, 0.573,
     0.814, 0.799, 0.549, 0.808, 0.790, 0.527, 0.803, 0.781, 0.504, 0.798,
     0.772, 0.481, 0.793, 0.763, 0.458, 0.788, 0.754, 0.434, 0.783, 0.745,
     0.411, 0.779, 0.736, 0.388, 0.774, 0.727, 0.365, 0.769, 0.718, 0.341,
     0.765, 0.709, 0.317, 0.760, 0.700, 0.293, 0.756, 0.691, 0.268, 0.751,
     0.683, 0.242, 0.747, 0.674, 0.215, 0.581, 0.665, 0.994, 0.592, 0.674,
     0.989, 0.603, 0.683, 0.984, 0.614, 0.692, 0.979, 0.625, 0.701, 0.974,
     0.636, 0.710, 0.970, 0.647, 0.719, 0.966, 0.658, 0.728, 0.963, 0.669,
     0.737, 0.959, 0.681, 0.746, 0.956, 0.692, 0.755, 0.953, 0.703, 0.765,
     0.951, 0.715, 0.774, 0.948, 0.727, 0.783, 0.946, 0.738, 0.792, 0.944,
     0.750, 0.801, 0.943, 0.762, 0.810, 0.941, 0.774, 0.820, 0.940, 0.786,
     0.829, 0.939, 0.798, 0.839, 0.939, 0.810, 0.848, 0.938, 0.822, 0.858,
     0.938, 0.834, 0.867, 0.939, 0.847, 0.877, 0.939, 0.859, 0.887, 0.940,
     0.871, 0.897, 0.940, 0.883, 0.906, 0.942, 0.896, 0.916, 0.943, 0.907,
     0.925, 0.944, 0.918, 0.933, 0.945, 0.927, 0.941, 0.945, 0.934, 0.946,
     0.943, 0.937, 0.949, 0.937, 0.935, 0.948, 0.927, 0.930, 0.943, 0.912,
     0.924, 0.937, 0.893, 0.916, 0.929, 0.872, 0.909, 0.920, 0.850, 0.902,
     0.911, 0.828, 0.895, 0.901, 0.805, 0.888, 0.892, 0.782, 0.881, 0.882,
     0.759, 0.874, 0.872, 0.735, 0.868, 0.863, 0.712, 0.861, 0.853, 0.689,
     0.855, 0.844, 0.665, 0.849, 0.834, 0.642, 0.843, 0.825, 0.619, 0.838,
     0.815, 0.596, 0.832, 0.806, 0.572, 0.826, 0.797, 0.549, 0.821, 0.787,
     0.526, 0.816, 0.778, 0.503, 0.811, 0.769, 0.480, 0.805, 0.760, 0.457,
     0.800, 0.751, 0.434, 0.795, 0.742, 0.411, 0.791, 0.733, 0.387, 0.786,
     0.724, 0.364, 0.781, 0.715, 0.340, 0.776, 0.706, 0.316, 0.772, 0.697,
     0.292, 0.767, 0.688, 0.267, 0.762, 0.679, 0.241, 0.758, 0.670, 0.215,
     0.593, 0.662, 0.995, 0.603, 0.671, 0.990, 0.614, 0.680, 0.985, 0.625,
     0.689, 0.980, 0.636, 0.699, 0.975, 0.647, 0.708, 0.971, 0.658, 0.717,
     0.967, 0.669, 0.726, 0.964, 0.680, 0.735, 0.960, 0.691, 0.744, 0.957,
     0.702, 0.753, 0.955, 0.714, 0.762, 0.952, 0.725, 0.771, 0.950, 0.737,
     0.781, 0.948, 0.748, 0.790, 0.946, 0.760, 0.799, 0.944, 0.772, 0.809,
     0.943, 0.784, 0.818, 0.942, 0.796, 0.828, 0.941, 0.808, 0.837, 0.941,
     0.820, 0.847, 0.940, 0.832, 0.857, 0.941, 0.844, 0.867, 0.941, 0.857,
     0.877, 0.942, 0.869, 0.887, 0.943, 0.882, 0.897, 0.944, 0.895, 0.908,
     0.945, 0.908, 0.918, 0.947, 0.920, 0.928, 0.949, 0.933, 0.938, 0.951,
     0.944, 0.947, 0.953, 0.953, 0.955, 0.954, 0.957, 0.958, 0.950, 0.954,
     0.956, 0.938, 0.948, 0.949, 0.920, 0.940, 0.941, 0.899, 0.932, 0.931,
     0.877, 0.924, 0.921, 0.854, 0.916, 0.911, 0.830, 0.909, 0.901, 0.807,
     0.901, 0.891, 0.783, 0.894, 0.881, 0.759, 0.887, 0.871, 0.736, 0.881,
     0.861, 0.712, 0.874, 0.851, 0.688, 0.868, 0.841, 0.665, 0.862, 0.832,
     0.642, 0.856, 0.822, 0.618, 0.850, 0.812, 0.595, 0.844, 0.803, 0.572,
     0.839, 0.793, 0.549, 0.833, 0.784, 0.525, 0.828, 0.775, 0.502, 0.822,
     0.766, 0.479, 0.817, 0.756, 0.456, 0.812, 0.747, 0.433, 0.807, 0.738,
     0.410, 0.802, 0.729, 0.387, 0.797, 0.720, 0.363, 0.792, 0.711, 0.339,
     0.787, 0.702, 0.315, 0.782, 0.693, 0.291, 0.778, 0.684, 0.266, 0.773,
     0.675, 0.240, 0.768, 0.666, 0.214, 0.604, 0.659, 0.996, 0.614, 0.668,
     0.990, 0.625, 0.677, 0.985, 0.636, 0.686, 0.981, 0.646, 0.695, 0.976,
     0.657, 0.704, 0.972, 0.668, 0.714, 0.968, 0.679, 0.723, 0.965, 0.690,
     0.732, 0.961, 0.701, 0.741, 0.958, 0.712, 0.750, 0.956, 0.723, 0.759,
     0.953, 0.735, 0.769, 0.951, 0.746, 0.778, 0.949, 0.758, 0.787, 0.947,
     0.769, 0.797, 0.945, 0.781, 0.806, 0.944, 0.793, 0.816, 0.943, 0.805,
     0.826, 0.943, 0.817, 0.836, 0.942, 0.829, 0.845, 0.942, 0.841, 0.855,
     0.942, 0.853, 0.866, 0.943, 0.866, 0.876, 0.943, 0.879, 0.886, 0.945,
     0.892, 0.897, 0.946, 0.905, 0.907, 0.948, 0.918, 0.918, 0.950, 0.931,
     0.930, 0.953, 0.945, 0.941, 0.956, 0.958, 0.952, 0.960, 0.971, 0.963,
     0.963, 0.978, 0.968, 0.963, 0.972, 0.963, 0.948, 0.963, 0.954, 0.926,
     0.954, 0.943, 0.903, 0.945, 0.931, 0.879, 0.937, 0.921, 0.855, 0.929,
     0.910, 0.831, 0.921, 0.899, 0.807, 0.914, 0.889, 0.783, 0.907, 0.878,
     0.759, 0.900, 0.868, 0.735, 0.893, 0.858, 0.711, 0.887, 0.848, 0.688,
     0.880, 0.838, 0.664, 0.874, 0.828, 0.641, 0.868, 0.818, 0.617, 0.862,
     0.809, 0.594, 0.856, 0.799, 0.571, 0.850, 0.790, 0.547, 0.845, 0.780,
     0.524, 0.839, 0.771, 0.501, 0.834, 0.762, 0.478, 0.828, 0.752, 0.455,
     0.823, 0.743, 0.432, 0.818, 0.734, 0.409, 0.813, 0.725, 0.385, 0.808,
     0.716, 0.362, 0.803, 0.707, 0.338, 0.798, 0.698, 0.314, 0.793, 0.689,
     0.290, 0.788, 0.680, 0.265, 0.783, 0.671, 0.239, 0.778, 0.662, 0.213,
     0.615, 0.655, 0.996, 0.625, 0.664, 0.991, 0.635, 0.673, 0.986, 0.646,
     0.683, 0.982, 0.656, 0.692, 0.977, 0.667, 0.701, 0.973, 0.678, 0.710,
     0.969, 0.688, 0.719, 0.966, 0.699, 0.729, 0.962, 0.710, 0.738, 0.959,
     0.721, 0.747, 0.956, 0.732, 0.756, 0.954, 0.744, 0.766, 0.952, 0.755,
     0.775, 0.950, 0.766, 0.784, 0.948, 0.778, 0.794, 0.946, 0.789, 0.804,
     0.945, 0.801, 0.813, 0.944, 0.813, 0.823, 0.943, 0.825, 0.833, 0.943,
     0.837, 0.843, 0.943, 0.849, 0.853, 0.943, 0.861, 0.863, 0.944, 0.874,
     0.873, 0.944, 0.886, 0.884, 0.946, 0.899, 0.895, 0.947, 0.912, 0.906,
     0.949, 0.926, 0.917, 0.952, 0.939, 0.928, 0.955, 0.953, 0.940, 0.958,
     0.967, 0.953, 0.963, 0.982, 0.966, 0.969, 0.994, 0.976, 0.972, 0.986,
     0.966, 0.952, 0.976, 0.953, 0.928, 0.966, 0.941, 0.903, 0.957, 0.929,
     0.878, 0.949, 0.918, 0.854, 0.941, 0.906, 0.830, 0.933, 0.896, 0.806,
     0.926, 0.885, 0.782, 0.918, 0.874, 0.758, 0.911, 0.864, 0.734, 0.905,
     0.854, 0.710, 0.898, 0.844, 0.686, 0.892, 0.834, 0.663, 0.885, 0.824,
     0.639, 0.879, 0.814, 0.616, 0.873, 0.804, 0.592, 0.867, 0.795, 0.569,
     0.861, 0.785, 0.546, 0.856, 0.776, 0.523, 0.850, 0.766, 0.500, 0.845,
     0.757, 0.477, 0.839, 0.748, 0.454, 0.834, 0.739, 0.430, 0.829, 0.729,
     0.407, 0.823, 0.720, 0.384, 0.818, 0.711, 0.361, 0.813, 0.702, 0.337,
     0.808, 0.693, 0.313, 0.803, 0.684, 0.289, 0.798, 0.675, 0.264, 0.793,
     0.666, 0.238, 0.788, 0.657, 0.211, 0.625, 0.651, 0.997, 0.635, 0.660,
     0.992, 0.645, 0.669, 0.987, 0.656, 0.679, 0.982, 0.666, 0.688, 0.978,
     0.676, 0.697, 0.974, 0.687, 0.706, 0.970, 0.698, 0.716, 0.966, 0.708,
     0.725, 0.963, 0.719, 0.734, 0.960, 0.730, 0.743, 0.957, 0.741, 0.753,
     0.954, 0.752, 0.762, 0.952, 0.763, 0.771, 0.950, 0.774, 0.781, 0.948,
     0.786, 0.790, 0.947, 0.797, 0.800, 0.945, 0.809, 0.810, 0.945, 0.820,
     0.819, 0.944, 0.832, 0.829, 0.943, 0.844, 0.839, 0.943, 0.856, 0.849,
     0.943, 0.868, 0.860, 0.944, 0.880, 0.870, 0.945, 0.893, 0.880, 0.946,
     0.905, 0.891, 0.947, 0.918, 0.902, 0.949, 0.931, 0.913, 0.951, 0.944,
     0.924, 0.954, 0.957, 0.936, 0.957, 0.971, 0.947, 0.961, 0.983, 0.958,
     0.964, 0.991, 0.963, 0.962, 0.990, 0.957, 0.946, 0.983, 0.946, 0.924,
     0.975, 0.935, 0.900, 0.967, 0.923, 0.876, 0.959, 0.912, 0.851, 0.951,
     0.901, 0.827, 0.943, 0.890, 0.803, 0.936, 0.880, 0.779, 0.929, 0.869,
     0.755, 0.922, 0.859, 0.732, 0.915, 0.849, 0.708, 0.909, 0.839, 0.684,
     0.902, 0.829, 0.661, 0.896, 0.819, 0.637, 0.890, 0.809, 0.614, 0.884,
     0.800, 0.591, 0.878, 0.790, 0.567, 0.872, 0.780, 0.544, 0.866, 0.771,
     0.521, 0.861, 0.762, 0.498, 0.855, 0.752, 0.475, 0.850, 0.743, 0.452,
     0.844, 0.734, 0.429, 0.839, 0.725, 0.406, 0.834, 0.715, 0.382, 0.828,
     0.706, 0.359, 0.823, 0.697, 0.335, 0.818, 0.688, 0.311, 0.813, 0.679,
     0.287, 0.808, 0.670, 0.262, 0.803, 0.662, 0.236, 0.798, 0.653, 0.210,
     0.635, 0.646, 0.998, 0.645, 0.656, 0.992, 0.655, 0.665, 0.987, 0.665,
     0.674, 0.983, 0.675, 0.684, 0.978, 0.685, 0.693, 0.974, 0.696, 0.702,
     0.970, 0.706, 0.711, 0.966, 0.717, 0.721, 0.963, 0.727, 0.730, 0.960,
     0.738, 0.739, 0.957, 0.749, 0.748, 0.955, 0.760, 0.758, 0.952, 0.771,
     0.767, 0.950, 0.782, 0.777, 0.948, 0.793, 0.786, 0.947, 0.804, 0.796,
     0.946, 0.816, 0.805, 0.945, 0.827, 0.815, 0.944, 0.839, 0.825, 0.943,
     0.850, 0.835, 0.943, 0.862, 0.845, 0.943, 0.874, 0.855, 0.943, 0.886,
     0.865, 0.944, 0.898, 0.875, 0.945, 0.910, 0.886, 0.946, 0.923, 0.896,
     0.948, 0.935, 0.907, 0.949, 0.947, 0.917, 0.951, 0.959, 0.927, 0.953,
     0.970, 0.937, 0.955, 0.980, 0.944, 0.955, 0.987, 0.946, 0.949, 0.989,
     0.942, 0.936, 0.985, 0.935, 0.916, 0.980, 0.925, 0.894, 0.973, 0.915,
     0.871, 0.966, 0.904, 0.847, 0.959, 0.894, 0.824, 0.952, 0.883, 0.800,
     0.945, 0.873, 0.776, 0.938, 0.863, 0.752, 0.932, 0.853, 0.729, 0.925,
     0.843, 0.705, 0.919, 0.833, 0.682, 0.912, 0.823, 0.658, 0.906, 0.813,
     0.635, 0.900, 0.803, 0.611, 0.894, 0.794, 0.588, 0.888, 0.784, 0.565,
     0.882, 0.775, 0.542, 0.876, 0.765, 0.519, 0.871, 0.756, 0.496, 0.865,
     0.747, 0.473, 0.859, 0.738, 0.450, 0.854, 0.728, 0.427, 0.848, 0.719,
     0.404, 0.843, 0.710, 0.380, 0.838, 0.701, 0.357, 0.833, 0.692, 0.333,
     0.827, 0.683, 0.310, 0.822, 0.674, 0.285, 0.817, 0.665, 0.260, 0.812,
     0.656, 0.235, 0.807, 0.648, 0.208, 0.644, 0.642, 0.998, 0.654, 0.651,
     0.993, 0.664, 0.660, 0.988, 0.674, 0.670, 0.983, 0.684, 0.679, 0.978,
     0.694, 0.688, 0.974, 0.704, 0.697, 0.970, 0.715, 0.707, 0.967, 0.725,
     0.716, 0.963, 0.735, 0.725, 0.960, 0.746, 0.735, 0.957, 0.757, 0.744,
     0.955, 0.767, 0.753, 0.952, 0.778, 0.763, 0.950, 0.789, 0.772, 0.948,
     0.800, 0.781, 0.947, 0.811, 0.791, 0.945, 0.822, 0.801, 0.944, 0.833,
     0.810, 0.943, 0.845, 0.820, 0.943, 0.856, 0.830, 0.942, 0.868, 0.839,
     0.942, 0.879, 0.849, 0.942, 0.891, 0.859, 0.943, 0.902, 0.869, 0.943,
     0.914, 0.879, 0.944, 0.926, 0.889, 0.945, 0.937, 0.899, 0.946, 0.949,
     0.908, 0.947, 0.959, 0.917, 0.948, 0.969, 0.924, 0.947, 0.978, 0.929,
     0.944, 0.984, 0.930, 0.937, 0.986, 0.927, 0.924, 0.986, 0.921, 0.907,
     0.982, 0.913, 0.887, 0.978, 0.904, 0.865, 0.972, 0.895, 0.842, 0.966,
     0.885, 0.819, 0.959, 0.875, 0.795, 0.953, 0.865, 0.772, 0.946, 0.855,
     0.749, 0.940, 0.846, 0.725, 0.934, 0.836, 0.702, 0.927, 0.826, 0.678,
     0.921, 0.816, 0.655, 0.915, 0.807, 0.632, 0.909, 0.797, 0.609, 0.903,
     0.788, 0.586, 0.897, 0.778, 0.562, 0.891, 0.769, 0.539, 0.886, 0.759,
     0.516, 0.880, 0.750, 0.493, 0.874, 0.741, 0.471, 0.869, 0.732, 0.448,
     0.863, 0.723, 0.425, 0.858, 0.713, 0.402, 0.852, 0.704, 0.378, 0.847,
     0.695, 0.355, 0.842, 0.686, 0.331, 0.836, 0.677, 0.308, 0.831, 0.669,
     0.283, 0.826, 0.660, 0.258, 0.821, 0.651, 0.233, 0.815, 0.642, 0.206,
     0.653, 0.636, 0.998, 0.663, 0.646, 0.993, 0.673, 0.655, 0.988, 0.682,
     0.665, 0.983, 0.692, 0.674, 0.979, 0.702, 0.683, 0.974, 0.712, 0.692,
     0.970, 0.722, 0.702, 0.967, 0.733, 0.711, 0.963, 0.743, 0.720, 0.960,
     0.753, 0.730, 0.957, 0.764, 0.739, 0.954, 0.774, 0.748, 0.952, 0.785,
     0.757, 0.950, 0.796, 0.767, 0.948, 0.806, 0.776, 0.946, 0.817, 0.786,
     0.945, 0.828, 0.795, 0.943, 0.839, 0.804, 0.942, 0.850, 0.814, 0.941,
     0.861, 0.824, 0.941, 0.872, 0.833, 0.940, 0.884, 0.843, 0.940, 0.895,
     0.852, 0.940, 0.906, 0.862, 0.940, 0.917, 0.871, 0.941, 0.928, 0.880,
     0.941, 0.939, 0.889, 0.941, 0.949, 0.897, 0.941, 0.959, 0.904, 0.940,
     0.968, 0.910, 0.938, 0.975, 0.914, 0.933, 0.981, 0.914, 0.925, 0.984,
     0.912, 0.913, 0.985, 0.907, 0.897, 0.983, 0.900, 0.878, 0.980, 0.893,
     0.857, 0.976, 0.884, 0.836, 0.971, 0.875, 0.813, 0.965, 0.866, 0.790,
     0.959, 0.856, 0.767, 0.954, 0.847, 0.744, 0.947, 0.837, 0.721, 0.941,
     0.828, 0.698, 0.935, 0.818, 0.675, 0.929, 0.809, 0.652, 0.923, 0.800,
     0.629, 0.917, 0.790, 0.605, 0.912, 0.781, 0.582, 0.906, 0.771, 0.560,
     0.900, 0.762, 0.537, 0.894, 0.753, 0.514, 0.889, 0.744, 0.491, 0.883,
     0.735, 0.468, 0.877, 0.725, 0.445, 0.872, 0.716, 0.422, 0.866, 0.707,
     0.399, 0.861, 0.698, 0.376, 0.856, 0.689, 0.353, 0.850, 0.680, 0.329,
     0.845, 0.672, 0.305, 0.840, 0.663, 0.281, 0.834, 0.654, 0.256, 0.829,
     0.645, 0.231, 0.824, 0.636, 0.204, 0.662, 0.631, 0.998, 0.672, 0.641,
     0.993, 0.681, 0.650, 0.988, 0.691, 0.659, 0.983, 0.700, 0.669, 0.979,
     0.710, 0.678, 0.974, 0.720, 0.687, 0.970, 0.730, 0.696, 0.966, 0.740,
     0.706, 0.963, 0.750, 0.715, 0.960, 0.760, 0.724, 0.957, 0.771, 0.733,
     0.954, 0.781, 0.742, 0.951, 0.791, 0.752, 0.949, 0.802, 0.761, 0.947,
     0.812, 0.770, 0.945, 0.823, 0.779, 0.943, 0.834, 0.789, 0.942, 0.844,
     0.798, 0.941, 0.855, 0.807, 0.940, 0.866, 0.817, 0.939, 0.877, 0.826,
     0.938, 0.887, 0.835, 0.938, 0.898, 0.844, 0.937, 0.909, 0.853, 0.937,
     0.919, 0.862, 0.937, 0.930, 0.870, 0.936, 0.940, 0.878, 0.936, 0.950,
     0.885, 0.934, 0.958, 0.891, 0.932, 0.967, 0.896, 0.928, 0.974, 0.898,
     0.922, 0.979, 0.899, 0.914, 0.982, 0.897, 0.902, 0.984, 0.893, 0.886,
     0.984, 0.887, 0.869, 0.982, 0.880, 0.849, 0.979, 0.872, 0.828, 0.975,
     0.864, 0.807, 0.970, 0.856, 0.785, 0.965, 0.847, 0.762, 0.959, 0.838,
     0.739, 0.954, 0.829, 0.717, 0.948, 0.819, 0.694, 0.943, 0.810, 0.671,
     0.937, 0.801, 0.648, 0.931, 0.792, 0.625, 0.925, 0.782, 0.602, 0.919,
     0.773, 0.579, 0.914, 0.764, 0.556, 0.908, 0.755, 0.533, 0.902, 0.746,
     0.511, 0.897, 0.737, 0.488, 0.891, 0.728, 0.465, 0.886, 0.719, 0.442,
     0.880, 0.710, 0.420, 0.875, 0.701, 0.397, 0.869, 0.692, 0.374, 0.864,
     0.683, 0.350, 0.858, 0.674, 0.327, 0.853, 0.665, 0.303, 0.848, 0.657,
     0.279, 0.842, 0.648, 0.254, 0.837, 0.639, 0.229, 0.832, 0.630, 0.202,
     0.671, 0.625, 0.998, 0.680, 0.635, 0.993, 0.689, 0.644, 0.988, 0.698,
     0.654, 0.983, 0.708, 0.663, 0.978, 0.718, 0.672, 0.974, 0.727, 0.681,
     0.970, 0.737, 0.691, 0.966, 0.747, 0.700, 0.962, 0.757, 0.709, 0.959,
     0.767, 0.718, 0.956, 0.777, 0.727, 0.953, 0.787, 0.736, 0.950, 0.797,
     0.745, 0.948, 0.807, 0.755, 0.946, 0.818, 0.764, 0.944, 0.828, 0.773,
     0.942, 0.839, 0.782, 0.940, 0.849, 0.791, 0.939, 0.859, 0.800, 0.938,
     0.870, 0.809, 0.937, 0.880, 0.818, 0.936, 0.891, 0.827, 0.935, 0.901,
     0.835, 0.934, 0.911, 0.844, 0.933, 0.921, 0.852, 0.932, 0.931, 0.859,
     0.931, 0.941, 0.866, 0.929, 0.950, 0.873, 0.927, 0.958, 0.878, 0.923,
     0.966, 0.881, 0.919, 0.972, 0.883, 0.912, 0.977, 0.883, 0.903, 0.981,
     0.882, 0.891, 0.983, 0.878, 0.876, 0.984, 0.873, 0.859, 0.983, 0.867,
     0.841, 0.980, 0.860, 0.821, 0.977, 0.853, 0.800, 0.974, 0.845, 0.778,
     0.969, 0.836, 0.756, 0.964, 0.828, 0.734, 0.959, 0.819, 0.712, 0.954,
     0.810, 0.689, 0.949, 0.801, 0.666, 0.943, 0.792, 0.644, 0.938, 0.783,
     0.621, 0.932, 0.774, 0.598, 0.927, 0.765, 0.575, 0.921, 0.756, 0.553,
     0.916, 0.747, 0.530, 0.910, 0.738, 0.507, 0.904, 0.729, 0.485, 0.899,
     0.721, 0.462, 0.893, 0.712, 0.439, 0.888, 0.703, 0.417, 0.882, 0.694,
     0.394, 0.877, 0.685, 0.371, 0.871, 0.676, 0.348, 0.866, 0.668, 0.324,
     0.861, 0.659, 0.301, 0.855, 0.650, 0.277, 0.850, 0.641, 0.252, 0.845,
     0.633, 0.226, 0.839, 0.624, 0.200, 0.679, 0.619, 0.998, 0.688, 0.629,
     0.993, 0.697, 0.638, 0.988, 0.706, 0.648, 0.983, 0.715, 0.657, 0.978,
     0.725, 0.666, 0.974, 0.734, 0.675, 0.969, 0.744, 0.684, 0.965, 0.754,
     0.693, 0.962, 0.763, 0.703, 0.958, 0.773, 0.712, 0.955, 0.783, 0.721,
     0.952, 0.793, 0.730, 0.949, 0.803, 0.739, 0.947, 0.813, 0.748, 0.944,
     0.823, 0.757, 0.942, 0.833, 0.766, 0.940, 0.843, 0.774, 0.938, 0.853,
     0.783, 0.937, 0.863, 0.792, 0.935, 0.874, 0.801, 0.934, 0.884, 0.809,
     0.932, 0.894, 0.818, 0.931, 0.904, 0.826, 0.930, 0.913, 0.833, 0.928,
     0.923, 0.841, 0.927, 0.932, 0.848, 0.925, 0.941, 0.854, 0.922, 0.950,
     0.859, 0.919, 0.957, 0.864, 0.915, 0.965, 0.867, 0.909, 0.971, 0.868,
     0.901, 0.976, 0.868, 0.892, 0.980, 0.867, 0.880, 0.982, 0.863, 0.866,
     0.983, 0.859, 0.849, 0.983, 0.854, 0.832, 0.982, 0.847, 0.812, 0.979,
     0.840, 0.792, 0.976, 0.833, 0.771, 0.973, 0.825, 0.750, 0.969, 0.817,
     0.728, 0.964, 0.809, 0.706, 0.959, 0.800, 0.684, 0.954, 0.792, 0.661,
     0.949, 0.783, 0.639, 0.944, 0.774, 0.617, 0.939, 0.766, 0.594, 0.933,
     0.757, 0.572, 0.928, 0.748, 0.549, 0.922, 0.739, 0.527, 0.917, 0.731,
     0.504, 0.911, 0.722, 0.481, 0.906, 0.713, 0.459, 0.901, 0.704, 0.436,
     0.895, 0.695, 0.414, 0.890, 0.687, 0.391, 0.884, 0.678, 0.368, 0.879,
     0.669, 0.345, 0.873, 0.661, 0.322, 0.868, 0.652, 0.298, 0.863, 0.643,
     0.274, 0.857, 0.635, 0.249, 0.852, 0.626, 0.224, 0.846, 0.617, 0.197,
     0.686, 0.613, 0.998, 0.695, 0.622, 0.993, 0.704, 0.632, 0.987, 0.713,
     0.641, 0.982, 0.722, 0.650, 0.977, 0.732, 0.660, 0.973, 0.741, 0.669,
     0.969, 0.750, 0.678, 0.965, 0.760, 0.687, 0.961, 0.769, 0.696, 0.957,
     0.779, 0.705, 0.954, 0.789, 0.714, 0.951, 0.798, 0.723, 0.948, 0.808,
     0.731, 0.945, 0.818, 0.740, 0.943, 0.828, 0.749, 0.940, 0.838, 0.758,
     0.938, 0.847, 0.766, 0.936, 0.857, 0.775, 0.934, 0.867, 0.783, 0.932,
     0.877, 0.792, 0.930, 0.887, 0.800, 0.929, 0.896, 0.808, 0.927, 0.906,
     0.815, 0.925, 0.915, 0.823, 0.923, 0.924, 0.829, 0.921, 0.933, 0.836,
     0.918, 0.942, 0.841, 0.915, 0.950, 0.846, 0.911, 0.957, 0.850, 0.906,
     0.964, 0.852, 0.899, 0.970, 0.853, 0.891, 0.975, 0.853, 0.881, 0.979,
     0.852, 0.869, 0.981, 0.849, 0.855, 0.983, 0.845, 0.840, 0.983, 0.840,
     0.822, 0.982, 0.834, 0.804, 0.981, 0.828, 0.784, 0.978, 0.821, 0.764,
     0.975, 0.814, 0.743, 0.972, 0.806, 0.722, 0.968, 0.798, 0.700, 0.964,
     0.790, 0.678, 0.959, 0.782, 0.656, 0.954, 0.773, 0.634, 0.949, 0.765,
     0.612, 0.944, 0.757, 0.590, 0.939, 0.748, 0.567, 0.934, 0.739, 0.545,
     0.929, 0.731, 0.523, 0.923, 0.722, 0.500, 0.918, 0.714, 0.478, 0.913,
     0.705, 0.456, 0.907, 0.696, 0.433, 0.902, 0.688, 0.411, 0.896, 0.679,
     0.388, 0.891, 0.670, 0.365, 0.886, 0.662, 0.342, 0.880, 0.653, 0.319,
     0.875, 0.645, 0.295, 0.869, 0.636, 0.271, 0.864, 0.628, 0.247, 0.859,
     0.619, 0.221, 0.853, 0.611, 0.195, 0.694, 0.606, 0.998, 0.703, 0.616,
     0.992, 0.711, 0.625, 0.987, 0.720, 0.634, 0.982, 0.729, 0.644, 0.977,
     0.738, 0.653, 0.972, 0.747, 0.662, 0.968, 0.757, 0.671, 0.964, 0.766,
     0.680, 0.960, 0.775, 0.689, 0.956, 0.785, 0.698, 0.953, 0.794, 0.706,
     0.949, 0.804, 0.715, 0.946, 0.813, 0.724, 0.943, 0.823, 0.732, 0.941,
     0.832, 0.741, 0.938, 0.842, 0.749, 0.936, 0.851, 0.758, 0.933, 0.861,
     0.766, 0.931, 0.870, 0.774, 0.929, 0.880, 0.782, 0.927, 0.889, 0.790,
     0.924, 0.899, 0.797, 0.922, 0.908, 0.805, 0.920, 0.917, 0.811, 0.917,
     0.925, 0.818, 0.914, 0.934, 0.823, 0.911, 0.942, 0.828, 0.907, 0.950,
     0.832, 0.902, 0.957, 0.836, 0.896, 0.963, 0.838, 0.889, 0.969, 0.839,
     0.881, 0.974, 0.838, 0.871, 0.978, 0.837, 0.859, 0.980, 0.834, 0.845,
     0.982, 0.831, 0.830, 0.983, 0.826, 0.813, 0.983, 0.821, 0.795, 0.982,
     0.815, 0.776, 0.980, 0.809, 0.757, 0.978, 0.802, 0.736, 0.975, 0.794,
     0.715, 0.971, 0.787, 0.694, 0.967, 0.779, 0.673, 0.963, 0.771, 0.651,
     0.959, 0.763, 0.629, 0.954, 0.755, 0.607, 0.949, 0.747, 0.585, 0.944,
     0.739, 0.563, 0.939, 0.730, 0.541, 0.934, 0.722, 0.519, 0.929, 0.714,
     0.496, 0.924, 0.705, 0.474, 0.919, 0.697, 0.452, 0.913, 0.688, 0.430,
     0.908, 0.680, 0.407, 0.903, 0.671, 0.385, 0.897, 0.663, 0.362, 0.892,
     0.654, 0.339, 0.887, 0.646, 0.316, 0.881, 0.637, 0.293, 0.876, 0.629,
     0.269, 0.870, 0.620, 0.244, 0.865, 0.612, 0.219, 0.860, 0.604, 0.192,
     0.701, 0.599, 0.997, 0.710, 0.609, 0.992, 0.718, 0.618, 0.986, 0.727,
     0.627, 0.981, 0.736, 0.636, 0.976, 0.745, 0.645, 0.971, 0.754, 0.655,
     0.967, 0.763, 0.663, 0.963, 0.772, 0.672, 0.959, 0.781, 0.681, 0.955,
     0.790, 0.690, 0.951, 0.799, 0.699, 0.948, 0.808, 0.707, 0.944, 0.818,
     0.716, 0.941, 0.827, 0.724, 0.938, 0.836, 0.732, 0.935, 0.846, 0.741,
     0.933, 0.855, 0.749, 0.930, 0.864, 0.757, 0.928, 0.874, 0.765, 0.925,
     0.883, 0.772, 0.923, 0.892, 0.780, 0.920, 0.901, 0.787, 0.917, 0.910,
     0.793, 0.914, 0.918, 0.800, 0.911, 0.927, 0.805, 0.908, 0.935, 0.811,
     0.904, 0.942, 0.815, 0.899, 0.950, 0.819, 0.894, 0.956, 0.821, 0.887,
     0.963, 0.823, 0.880, 0.968, 0.824, 0.871, 0.973, 0.824, 0.860, 0.977,
     0.822, 0.849, 0.980, 0.820, 0.835, 0.982, 0.817, 0.820, 0.983, 0.812,
     0.804, 0.983, 0.808, 0.786, 0.983, 0.802, 0.768, 0.981, 0.796, 0.749,
     0.979, 0.789, 0.729, 0.977, 0.783, 0.709, 0.974, 0.776, 0.688, 0.970,
     0.768, 0.667, 0.967, 0.761, 0.645, 0.963, 0.753, 0.624, 0.958, 0.745,
     0.602, 0.954, 0.737, 0.580, 0.949, 0.729, 0.558, 0.944, 0.721, 0.536,
     0.939, 0.713, 0.514, 0.934, 0.704, 0.492, 0.929, 0.696, 0.470, 0.924,
     0.688, 0.448, 0.919, 0.680, 0.426, 0.914, 0.671, 0.404, 0.908, 0.663,
     0.381, 0.903, 0.655, 0.359, 0.898, 0.646, 0.336, 0.893, 0.638, 0.313,
     0.887, 0.629, 0.290, 0.882, 0.621, 0.266, 0.876, 0.613, 0.241, 0.871,
     0.604, 0.216, 0.866, 0.596, 0.189, 0.708, 0.592, 0.997, 0.716, 0.601,
     0.991, 0.725, 0.611, 0.985, 0.733, 0.620, 0.980, 0.742, 0.629, 0.975,
     0.751, 0.638, 0.970, 0.759, 0.647, 0.966, 0.768, 0.656, 0.961, 0.777,
     0.665, 0.957, 0.786, 0.673, 0.953, 0.795, 0.682, 0.949, 0.804, 0.690,
     0.946, 0.813, 0.699, 0.942, 0.822, 0.707, 0.939, 0.831, 0.715, 0.936,
     0.840, 0.723, 0.933, 0.849, 0.731, 0.930, 0.859, 0.739, 0.927, 0.868,
     0.747, 0.924, 0.876, 0.754, 0.921, 0.885, 0.762, 0.918, 0.894, 0.769,
     0.915, 0.903, 0.775, 0.912, 0.911, 0.782, 0.909, 0.920, 0.787, 0.905,
     0.928, 0.793, 0.901, 0.935, 0.798, 0.896, 0.943, 0.802, 0.891, 0.950,
     0.805, 0.885, 0.956, 0.807, 0.878, 0.962, 0.809, 0.870, 0.967, 0.809,
     0.861, 0.972, 0.809, 0.850, 0.976, 0.808, 0.838, 0.979, 0.805, 0.825,
     0.981, 0.802, 0.810, 0.983, 0.799, 0.795, 0.983, 0.794, 0.778, 0.983,
     0.789, 0.760, 0.982, 0.783, 0.741, 0.981, 0.777, 0.721, 0.979, 0.771,
     0.701, 0.976, 0.764, 0.681, 0.973, 0.757, 0.660, 0.970, 0.750, 0.639,
     0.966, 0.742, 0.618, 0.962, 0.735, 0.597, 0.958, 0.727, 0.575, 0.953,
     0.719, 0.553, 0.949, 0.711, 0.532, 0.944, 0.703, 0.510, 0.939, 0.695,
     0.488, 0.934, 0.687, 0.466, 0.929, 0.679, 0.444, 0.924, 0.671, 0.422,
     0.919, 0.663, 0.400, 0.914, 0.654, 0.378, 0.909, 0.646, 0.355, 0.903,
     0.638, 0.333, 0.898, 0.630, 0.310, 0.893, 0.621, 0.287, 0.887, 0.613,
     0.263, 0.882, 0.605, 0.238, 0.877, 0.597, 0.213, 0.871, 0.589, 0.186,
     0.715, 0.584, 0.996, 0.723, 0.593, 0.990, 0.731, 0.603, 0.984, 0.739,
     0.612, 0.979, 0.748, 0.621, 0.974, 0.756, 0.630, 0.969, 0.765, 0.639,
     0.964, 0.774, 0.648, 0.960, 0.782, 0.656, 0.955, 0.791, 0.665, 0.951,
     0.800, 0.673, 0.947, 0.809, 0.682, 0.943, 0.818, 0.690, 0.940, 0.826,
     0.698, 0.936, 0.835, 0.706, 0.933, 0.844, 0.714, 0.930, 0.853, 0.722,
     0.926, 0.862, 0.729, 0.923, 0.871, 0.737, 0.920, 0.879, 0.744, 0.917,
     0.888, 0.751, 0.913, 0.896, 0.758, 0.910, 0.905, 0.764, 0.906, 0.913,
     0.770, 0.903, 0.921, 0.775, 0.898, 0.929, 0.780, 0.894, 0.936, 0.784,
     0.889, 0.943, 0.788, 0.883, 0.950, 0.791, 0.877, 0.956, 0.793, 0.869,
     0.962, 0.794, 0.861, 0.967, 0.795, 0.851, 0.971, 0.794, 0.841, 0.975,
     0.793, 0.829, 0.978, 0.791, 0.815, 0.981, 0.788, 0.801, 0.982, 0.785,
     0.785, 0.983, 0.780, 0.769, 0.983, 0.776, 0.751, 0.983, 0.770, 0.733,
     0.982, 0.764, 0.714, 0.980, 0.758, 0.694, 0.978, 0.752, 0.674, 0.975,
     0.745, 0.654, 0.972, 0.738, 0.633, 0.969, 0.731, 0.612, 0.965, 0.724,
     0.591, 0.961, 0.716, 0.570, 0.957, 0.709, 0.548, 0.953, 0.701, 0.527,
     0.948, 0.693, 0.505, 0.943, 0.685, 0.484, 0.939, 0.678, 0.462, 0.934,
     0.670, 0.440, 0.929, 0.662, 0.418, 0.924, 0.654, 0.396, 0.919, 0.646,
     0.374, 0.914, 0.637, 0.352, 0.908, 0.629, 0.329, 0.903, 0.621, 0.307,
     0.898, 0.613, 0.283, 0.893, 0.605, 0.260, 0.887, 0.597, 0.235, 0.882,
     0.589, 0.210, 0.876, 0.581, 0.183, 0.721, 0.576, 0.995, 0.729, 0.585,
     0.989, 0.737, 0.595, 0.983, 0.745, 0.604, 0.978, 0.754, 0.613, 0.973,
     0.762, 0.622, 0.968, 0.770, 0.631, 0.963, 0.779, 0.639, 0.958, 0.787,
     0.648, 0.954, 0.796, 0.656, 0.949, 0.805, 0.665, 0.945, 0.813, 0.673,
     0.941, 0.822, 0.681, 0.937, 0.830, 0.689, 0.933, 0.839, 0.697, 0.930,
     0.848, 0.704, 0.926, 0.856, 0.712, 0.923, 0.865, 0.719, 0.919, 0.873,
     0.726, 0.916, 0.882, 0.733, 0.912, 0.890, 0.740, 0.908, 0.898, 0.746,
     0.905, 0.906, 0.752, 0.901, 0.914, 0.757, 0.896, 0.922, 0.762, 0.892,
     0.929, 0.767, 0.887, 0.937, 0.771, 0.881, 0.943, 0.774, 0.875, 0.950,
     0.777, 0.868, 0.956, 0.779, 0.860, 0.961, 0.780, 0.851, 0.966, 0.780,
     0.842, 0.971, 0.780, 0.831, 0.975, 0.779, 0.819, 0.978, 0.777, 0.806,
     0.980, 0.774, 0.791, 0.982, 0.771, 0.776, 0.983, 0.767, 0.760, 0.984,
     0.762, 0.742, 0.983, 0.757, 0.725, 0.983, 0.752, 0.706, 0.981, 0.746,
     0.687, 0.979, 0.740, 0.667, 0.977, 0.733, 0.647, 0.974, 0.727, 0.627,
     0.971, 0.720, 0.606, 0.968, 0.713, 0.585, 0.964, 0.706, 0.564, 0.960,
     0.698, 0.543, 0.956, 0.691, 0.522, 0.952, 0.683, 0.501, 0.947, 0.676,
     0.479, 0.943, 0.668, 0.458, 0.938, 0.660, 0.436, 0.933, 0.652, 0.414,
     0.928, 0.644, 0.392, 0.923, 0.636, 0.370, 0.918, 0.629, 0.348, 0.913,
     0.621, 0.326, 0.908, 0.613, 0.303, 0.903, 0.605, 0.280, 0.897, 0.597,
     0.257, 0.892, 0.589, 0.232, 0.887, 0.581, 0.207, 0.881, 0.573, 0.180,
     0.727, 0.568, 0.994, 0.735, 0.577, 0.988, 0.743, 0.586, 0.982, 0.751,
     0.595, 0.977, 0.759, 0.604, 0.971, 0.767, 0.613, 0.966, 0.776, 0.622,
     0.961, 0.784, 0.630, 0.956, 0.792, 0.639, 0.951, 0.801, 0.647, 0.947,
     0.809, 0.655, 0.943, 0.817, 0.663, 0.938, 0.826, 0.671, 0.934, 0.834,
     0.679, 0.930, 0.843, 0.687, 0.927, 0.851, 0.694, 0.923, 0.859, 0.702,
     0.919, 0.868, 0.709, 0.915, 0.876, 0.715, 0.911, 0.884, 0.722, 0.907,
     0.892, 0.728, 0.903, 0.900, 0.734, 0.899, 0.908, 0.740, 0.895, 0.916,
     0.745, 0.890, 0.923, 0.750, 0.885, 0.930, 0.754, 0.879, 0.937, 0.758,
     0.873, 0.944, 0.761, 0.867, 0.950, 0.763, 0.859, 0.956, 0.765, 0.851,
     0.961, 0.766, 0.842, 0.966, 0.766, 0.832, 0.970, 0.766, 0.821, 0.974,
     0.764, 0.809, 0.977, 0.762, 0.796, 0.980, 0.760, 0.782, 0.982, 0.757,
     0.767, 0.983, 0.753, 0.751, 0.984, 0.749, 0.734, 0.984, 0.744, 0.716,
     0.983, 0.739, 0.698, 0.982, 0.733, 0.679, 0.980, 0.727, 0.660, 0.978,
     0.721, 0.640, 0.976, 0.715, 0.620, 0.973, 0.708, 0.600, 0.970, 0.701,
     0.579, 0.967, 0.694, 0.559, 0.963, 0.687, 0.538, 0.959, 0.680, 0.517,
     0.955, 0.673, 0.496, 0.951, 0.665, 0.474, 0.946, 0.658, 0.453, 0.942,
     0.650, 0.432, 0.937, 0.643, 0.410, 0.932, 0.635, 0.388, 0.927, 0.627,
     0.367, 0.922, 0.619, 0.345, 0.917, 0.612, 0.322, 0.912, 0.604, 0.300,
     0.907, 0.596, 0.277, 0.902, 0.588, 0.253, 0.897, 0.580, 0.229, 0.891,
     0.572, 0.204, 0.886, 0.564, 0.177, 0.733, 0.559, 0.993, 0.741, 0.568,
     0.987, 0.749, 0.577, 0.981, 0.757, 0.587, 0.975, 0.765, 0.595, 0.970,
     0.773, 0.604, 0.964, 0.781, 0.613, 0.959, 0.789, 0.621, 0.954, 0.797,
     0.630, 0.949, 0.805, 0.638, 0.945, 0.813, 0.646, 0.940, 0.821, 0.654,
     0.936, 0.830, 0.662, 0.931, 0.838, 0.669, 0.927, 0.846, 0.677, 0.923,
     0.854, 0.684, 0.919, 0.862, 0.691, 0.915, 0.870, 0.698, 0.911, 0.879,
     0.704, 0.907, 0.886, 0.711, 0.902, 0.894, 0.717, 0.898, 0.902, 0.722,
     0.893, 0.910, 0.727, 0.889, 0.917, 0.732, 0.883, 0.924, 0.737, 0.878,
     0.931, 0.741, 0.872, 0.938, 0.744, 0.866, 0.944, 0.747, 0.859, 0.950,
     0.749, 0.851, 0.956, 0.751, 0.842, 0.961, 0.751, 0.833, 0.966, 0.752,
     0.823, 0.970, 0.751, 0.812, 0.974, 0.750, 0.800, 0.977, 0.748, 0.787,
     0.979, 0.746, 0.773, 0.981, 0.743, 0.758, 0.983, 0.739, 0.742, 0.984,
     0.735, 0.725, 0.984, 0.731, 0.708, 0.983, 0.726, 0.690, 0.983, 0.721,
     0.672, 0.981, 0.715, 0.653, 0.980, 0.709, 0.633, 0.977, 0.703, 0.614,
     0.975, 0.697, 0.594, 0.972, 0.690, 0.573, 0.969, 0.683, 0.553, 0.965,
     0.676, 0.532, 0.962, 0.669, 0.512, 0.958, 0.662, 0.491, 0.954, 0.655,
     0.470, 0.949, 0.648, 0.448, 0.945, 0.640, 0.427, 0.941, 0.633, 0.406,
     0.936, 0.625, 0.384, 0.931, 0.618, 0.363, 0.926, 0.610, 0.341, 0.921,
     0.602, 0.319, 0.916, 0.595, 0.296, 0.911, 0.587, 0.273, 0.906, 0.579,
     0.250, 0.901, 0.571, 0.226, 0.896, 0.563, 0.201, 0.890, 0.556, 0.174,
     0.739, 0.550, 0.992, 0.747, 0.559, 0.986, 0.754, 0.568, 0.980, 0.762,
     0.577, 0.974, 0.770, 0.586, 0.968, 0.778, 0.595, 0.962, 0.785, 0.603,
     0.957, 0.793, 0.612, 0.952, 0.801, 0.620, 0.947, 0.809, 0.628, 0.942,
     0.817, 0.636, 0.937, 0.825, 0.644, 0.933, 0.833, 0.651, 0.928, 0.841,
     0.659, 0.924, 0.849, 0.666, 0.919, 0.857, 0.673, 0.915, 0.865, 0.680,
     0.911, 0.873, 0.686, 0.906, 0.881, 0.693, 0.902, 0.889, 0.699, 0.897,
     0.896, 0.705, 0.892, 0.904, 0.710, 0.887, 0.911, 0.715, 0.882, 0.918,
     0.720, 0.877, 0.925, 0.724, 0.871, 0.932, 0.727, 0.865, 0.938, 0.730,
     0.858, 0.944, 0.733, 0.850, 0.950, 0.735, 0.842, 0.956, 0.736, 0.834,
     0.961, 0.737, 0.824, 0.965, 0.737, 0.814, 0.970, 0.737, 0.802, 0.973,
     0.736, 0.790, 0.976, 0.734, 0.777, 0.979, 0.732, 0.763, 0.981, 0.729,
     0.749, 0.982, 0.726, 0.733, 0.983, 0.722, 0.717, 0.984, 0.717, 0.700,
     0.984, 0.713, 0.682, 0.983, 0.708, 0.664, 0.982, 0.702, 0.645, 0.980,
     0.697, 0.626, 0.979, 0.691, 0.607, 0.976, 0.685, 0.587, 0.974, 0.678,
     0.567, 0.971, 0.672, 0.547, 0.967, 0.665, 0.527, 0.964, 0.658, 0.506,
     0.960, 0.651, 0.485, 0.956, 0.644, 0.465, 0.952, 0.637, 0.444, 0.948,
     0.630, 0.423, 0.944, 0.623, 0.401, 0.939, 0.615, 0.380, 0.934, 0.608,
     0.358, 0.930, 0.600, 0.337, 0.925, 0.593, 0.315, 0.920, 0.585, 0.292,
     0.915, 0.578, 0.270, 0.910, 0.570, 0.246, 0.905, 0.562, 0.222, 0.899,
     0.555, 0.197, 0.894, 0.547, 0.171, 0.745, 0.540, 0.991, 0.752, 0.550,
     0.984, 0.760, 0.559, 0.978, 0.767, 0.568, 0.972, 0.775, 0.577, 0.966,
     0.782, 0.585, 0.960, 0.790, 0.594, 0.955, 0.798, 0.602, 0.950, 0.806,
     0.610, 0.944, 0.813, 0.618, 0.939, 0.821, 0.626, 0.934, 0.829, 0.634,
     0.930, 0.837, 0.641, 0.925, 0.845, 0.648, 0.920, 0.852, 0.655, 0.915,
     0.860, 0.662, 0.911, 0.868, 0.669, 0.906, 0.876, 0.675, 0.901, 0.883,
     0.681, 0.897, 0.891, 0.687, 0.892, 0.898, 0.692, 0.887, 0.905, 0.697,
     0.881, 0.912, 0.702, 0.876, 0.919, 0.707, 0.870, 0.926, 0.710, 0.864,
     0.932, 0.714, 0.857, 0.939, 0.717, 0.850, 0.945, 0.719, 0.842, 0.950,
     0.721, 0.834, 0.956, 0.722, 0.825, 0.961, 0.723, 0.815, 0.965, 0.723,
     0.804, 0.969, 0.723, 0.793, 0.973, 0.722, 0.781, 0.976, 0.720, 0.768,
     0.978, 0.718, 0.754, 0.981, 0.715, 0.739, 0.982, 0.712, 0.724, 0.983,
     0.708, 0.708, 0.984, 0.704, 0.691, 0.984, 0.700, 0.674, 0.983, 0.695,
     0.656, 0.982, 0.690, 0.638, 0.981, 0.684, 0.619, 0.979, 0.679, 0.600,
     0.977, 0.673, 0.581, 0.975, 0.666, 0.561, 0.972, 0.660, 0.541, 0.969,
     0.654, 0.521, 0.966, 0.647, 0.501, 0.962, 0.640, 0.480, 0.959, 0.634,
     0.459, 0.955, 0.627, 0.439, 0.951, 0.620, 0.418, 0.946, 0.612, 0.397,
     0.942, 0.605, 0.376, 0.937, 0.598, 0.354, 0.933, 0.591, 0.333, 0.928,
     0.583, 0.311, 0.923, 0.576, 0.289, 0.918, 0.568, 0.266, 0.913, 0.561,
     0.243, 0.908, 0.553, 0.219, 0.903, 0.546, 0.194, 0.898, 0.538, 0.167,
     0.750, 0.531, 0.989, 0.757, 0.540, 0.983, 0.765, 0.549, 0.976, 0.772,
     0.558, 0.970, 0.779, 0.567, 0.964, 0.787, 0.575, 0.958, 0.794, 0.584,
     0.953, 0.802, 0.592, 0.947, 0.810, 0.600, 0.942, 0.817, 0.608, 0.936,
     0.825, 0.615, 0.931, 0.833, 0.623, 0.926, 0.840, 0.630, 0.921, 0.848,
     0.637, 0.916, 0.855, 0.644, 0.911, 0.863, 0.651, 0.907, 0.870, 0.657,
     0.902, 0.878, 0.663, 0.897, 0.885, 0.669, 0.891, 0.893, 0.675, 0.886,
     0.900, 0.680, 0.881, 0.907, 0.685, 0.875, 0.914, 0.689, 0.869, 0.920,
     0.693, 0.863, 0.927, 0.697, 0.857, 0.933, 0.700, 0.850, 0.939, 0.703,
     0.842, 0.945, 0.705, 0.834, 0.950, 0.707, 0.825, 0.956, 0.708, 0.816,
     0.960, 0.709, 0.806, 0.965, 0.709, 0.795, 0.969, 0.708, 0.784, 0.972,
     0.707, 0.772, 0.975, 0.706, 0.759, 0.978, 0.704, 0.745, 0.980, 0.701,
     0.731, 0.982, 0.698, 0.715, 0.983, 0.694, 0.699, 0.984, 0.691, 0.683,
     0.984, 0.686, 0.666, 0.983, 0.682, 0.648, 0.983, 0.677, 0.630, 0.982,
     0.672, 0.612, 0.980, 0.666, 0.593, 0.978, 0.660, 0.574, 0.976, 0.655,
     0.554, 0.973, 0.648, 0.535, 0.971, 0.642, 0.515, 0.967, 0.636, 0.495,
     0.964, 0.629, 0.475, 0.961, 0.623, 0.454, 0.957, 0.616, 0.434, 0.953,
     0.609, 0.413, 0.949, 0.602, 0.392, 0.944, 0.595, 0.371, 0.940, 0.588,
     0.350, 0.936, 0.580, 0.328, 0.931, 0.573, 0.307, 0.926, 0.566, 0.285,
     0.921, 0.559, 0.262, 0.916, 0.551, 0.239, 0.911, 0.544, 0.215, 0.906,
     0.536, 0.190, 0.901, 0.529, 0.164, 0.755, 0.521, 0.988, 0.762, 0.530,
     0.981, 0.770, 0.539, 0.975, 0.777, 0.548, 0.968, 0.784, 0.557, 0.962,
     0.791, 0.565, 0.956, 0.799, 0.573, 0.950, 0.806, 0.582, 0.944, 0.814,
     0.589, 0.939, 0.821, 0.597, 0.933, 0.828, 0.605, 0.928, 0.836, 0.612,
     0.923, 0.843, 0.619, 0.918, 0.851, 0.626, 0.912, 0.858, 0.633, 0.907,
     0.866, 0.639, 0.902, 0.873, 0.645, 0.897, 0.880, 0.651, 0.892, 0.887,
     0.657, 0.886, 0.894, 0.662, 0.881, 0.901, 0.667, 0.875, 0.908, 0.672,
     0.869, 0.915, 0.676, 0.863, 0.921, 0.680, 0.856, 0.928, 0.684, 0.849,
     0.934, 0.687, 0.842, 0.940, 0.689, 0.834, 0.945, 0.691, 0.826, 0.951,
     0.693, 0.817, 0.956, 0.694, 0.807, 0.960, 0.695, 0.797, 0.964, 0.695,
     0.787, 0.968, 0.694, 0.775, 0.972, 0.693, 0.763, 0.975, 0.692, 0.750,
     0.977, 0.690, 0.736, 0.980, 0.687, 0.722, 0.981, 0.684, 0.707, 0.982,
     0.681, 0.691, 0.983, 0.677, 0.675, 0.984, 0.673, 0.658, 0.983, 0.669,
     0.641, 0.983, 0.664, 0.623, 0.982, 0.659, 0.605, 0.980, 0.654, 0.586,
     0.979, 0.648, 0.567, 0.977, 0.642, 0.548, 0.974, 0.637, 0.529, 0.972,
     0.630, 0.509, 0.969, 0.624, 0.489, 0.966, 0.618, 0.469, 0.962, 0.611,
     0.449, 0.959, 0.605, 0.429, 0.955, 0.598, 0.408, 0.951, 0.591, 0.387,
     0.947, 0.584, 0.367, 0.942, 0.577, 0.346, 0.938, 0.570, 0.324, 0.933,
     0.563, 0.303, 0.929, 0.556, 0.281, 0.924, 0.549, 0.258, 0.919, 0.541,
     0.235, 0.914, 0.534, 0.212, 0.909, 0.527, 0.187, 0.904, 0.519, 0.160,
     0.760, 0.510, 0.986, 0.767, 0.520, 0.979, 0.774, 0.529, 0.973, 0.781,
     0.538, 0.966, 0.788, 0.546, 0.960, 0.796, 0.555, 0.954, 0.803, 0.563,
     0.948, 0.810, 0.571, 0.942, 0.817, 0.579, 0.936, 0.825, 0.586, 0.930,
     0.832, 0.594, 0.925, 0.839, 0.601, 0.919, 0.846, 0.608, 0.914, 0.854,
     0.615, 0.908, 0.861, 0.621, 0.903, 0.868, 0.627, 0.897, 0.875, 0.633,
     0.892, 0.882, 0.639, 0.886, 0.889, 0.645, 0.881, 0.896, 0.650, 0.875,
     0.903, 0.655, 0.869, 0.909, 0.659, 0.863, 0.916, 0.663, 0.856, 0.922,
     0.667, 0.849, 0.928, 0.670, 0.842, 0.934, 0.673, 0.834, 0.940, 0.675,
     0.826, 0.945, 0.677, 0.818, 0.951, 0.679, 0.809, 0.955, 0.680, 0.799,
     0.960, 0.680, 0.789, 0.964, 0.680, 0.778, 0.968, 0.680, 0.766, 0.971,
     0.679, 0.754, 0.974, 0.677, 0.741, 0.977, 0.676, 0.727, 0.979, 0.673,
     0.713, 0.981, 0.670, 0.698, 0.982, 0.667, 0.682, 0.983, 0.664, 0.666,
     0.983, 0.660, 0.650, 0.983, 0.655, 0.633, 0.983, 0.651, 0.615, 0.982,
     0.646, 0.597, 0.981, 0.641, 0.579, 0.979, 0.636, 0.560, 0.977, 0.630,
     0.541, 0.975, 0.625, 0.522, 0.973, 0.619, 0.503, 0.970, 0.613, 0.483,
     0.967, 0.606, 0.463, 0.964, 0.600, 0.443, 0.960, 0.594, 0.423, 0.956,
     0.587, 0.403, 0.953, 0.580, 0.383, 0.949, 0.574, 0.362, 0.944, 0.567,
     0.341, 0.940, 0.560, 0.320, 0.936, 0.553, 0.298, 0.931, 0.546, 0.277,
     0.926, 0.539, 0.254, 0.922, 0.532, 0.232, 0.917, 0.524, 0.208, 0.912,
     0.517, 0.183, 0.906, 0.510, 0.156, 0.765, 0.499, 0.985, 0.772, 0.509,
     0.978, 0.779, 0.518, 0.971, 0.786, 0.527, 0.964, 0.793, 0.535, 0.957,
     0.800, 0.544, 0.951, 0.807, 0.552, 0.945, 0.814, 0.560, 0.939, 0.821,
     0.568, 0.933, 0.828, 0.575, 0.927, 0.835, 0.582, 0.921, 0.842, 0.589,
     0.915, 0.849, 0.596, 0.910, 0.856, 0.603, 0.904, 0.863, 0.609, 0.898,
     0.870, 0.615, 0.893, 0.877, 0.621, 0.887, 0.884, 0.627, 0.881, 0.891,
     0.632, 0.875, 0.898, 0.637, 0.869, 0.904, 0.642, 0.863, 0.911, 0.646,
     0.856, 0.917, 0.650, 0.849, 0.923, 0.653, 0.842, 0.929, 0.657, 0.835,
     0.935, 0.659, 0.827, 0.940, 0.662, 0.818, 0.946, 0.663, 0.810, 0.951,
     0.665, 0.800, 0.955, 0.666, 0.790, 0.960, 0.666, 0.780, 0.964, 0.666,
     0.769, 0.967, 0.666, 0.757, 0.971, 0.665, 0.745, 0.974, 0.663, 0.732,
     0.976, 0.662, 0.718, 0.978, 0.659, 0.704, 0.980, 0.657, 0.689, 0.981,
     0.654, 0.674, 0.982, 0.650, 0.658, 0.983, 0.646, 0.642, 0.983, 0.642,
     0.625, 0.983, 0.638, 0.608, 0.982, 0.633, 0.590, 0.981, 0.628, 0.572,
     0.979, 0.623, 0.553, 0.978, 0.618, 0.535, 0.976, 0.612, 0.516, 0.973,
     0.607, 0.497, 0.971, 0.601, 0.477, 0.968, 0.595, 0.458, 0.965, 0.589,
     0.438, 0.961, 0.582, 0.418, 0.958, 0.576, 0.398, 0.954, 0.569, 0.378,
     0.950, 0.563, 0.357, 0.946, 0.556, 0.336, 0.942, 0.549, 0.315, 0.938,
     0.542, 0.294, 0.933, 0.536, 0.273, 0.928, 0.529, 0.250, 0.924, 0.522,
     0.228, 0.919, 0.514, 0.204, 0.914, 0.507, 0.179, 0.909, 0.500, 0.153,
     0.770, 0.488, 0.983, 0.777, 0.498, 0.976, 0.783, 0.507, 0.969, 0.790,
     0.516, 0.962, 0.797, 0.524, 0.955, 0.804, 0.533, 0.948, 0.811, 0.541,
     0.942, 0.817, 0.549, 0.936, 0.824, 0.556, 0.930, 0.831, 0.564, 0.924,
     0.838, 0.571, 0.918, 0.845, 0.578, 0.912, 0.852, 0.584, 0.906, 0.859,
     0.591, 0.900, 0.866, 0.597, 0.894, 0.873, 0.603, 0.888, 0.879, 0.609,
     0.882, 0.886, 0.614, 0.876, 0.893, 0.619, 0.869, 0.899, 0.624, 0.863,
     0.906, 0.629, 0.856, 0.912, 0.633, 0.850, 0.918, 0.637, 0.843, 0.924,
     0.640, 0.835, 0.930, 0.643, 0.827, 0.935, 0.646, 0.819, 0.941, 0.648,
     0.811, 0.946, 0.649, 0.802, 0.951, 0.651, 0.792, 0.955, 0.652, 0.782,
     0.959, 0.652, 0.771, 0.963, 0.652, 0.760, 0.967, 0.652, 0.749, 0.970,
     0.651, 0.736, 0.973, 0.649, 0.723, 0.976, 0.647, 0.710, 0.978, 0.645,
     0.696, 0.980, 0.643, 0.681, 0.981, 0.640, 0.666, 0.982, 0.637, 0.650,
     0.982, 0.633, 0.634, 0.983, 0.629, 0.617, 0.982, 0.625, 0.600, 0.982,
     0.620, 0.582, 0.981, 0.616, 0.565, 0.979, 0.611, 0.546, 0.978, 0.605,
     0.528, 0.976, 0.600, 0.509, 0.974, 0.595, 0.490, 0.971, 0.589, 0.471,
     0.969, 0.583, 0.452, 0.966, 0.577, 0.432, 0.962, 0.571, 0.413, 0.959,
     0.565, 0.393, 0.955, 0.558, 0.373, 0.952, 0.552, 0.352, 0.948, 0.545,
     0.332, 0.943, 0.539, 0.311, 0.939, 0.532, 0.290, 0.935, 0.525, 0.268,
     0.930, 0.518, 0.246, 0.926, 0.511, 0.224, 0.921, 0.504, 0.200, 0.916,
     0.497, 0.175, 0.911, 0.490, 0.149, 0.775, 0.477, 0.981, 0.781, 0.486,
     0.974, 0.788, 0.495, 0.966, 0.794, 0.504, 0.959, 0.801, 0.513, 0.952,
     0.808, 0.521, 0.946, 0.814, 0.529, 0.939, 0.821, 0.537, 0.933, 0.828,
     0.545, 0.926, 0.835, 0.552, 0.920, 0.841, 0.559, 0.914, 0.848, 0.566,
     0.908, 0.855, 0.572, 0.901, 0.862, 0.579, 0.895, 0.868, 0.585, 0.889,
     0.875, 0.591, 0.883, 0.881, 0.596, 0.877, 0.888, 0.601, 0.870, 0.894,
     0.606, 0.864, 0.901, 0.611, 0.857, 0.907, 0.615, 0.850, 0.913, 0.619,
     0.843, 0.919, 0.623, 0.836, 0.925, 0.626, 0.828, 0.930, 0.629, 0.820,
     0.936, 0.632, 0.812, 0.941, 0.634, 0.803, 0.946, 0.635, 0.794, 0.951,
     0.637, 0.784, 0.955, 0.637, 0.774, 0.959, 0.638, 0.763, 0.963, 0.638,
     0.752, 0.967, 0.637, 0.740, 0.970, 0.636, 0.728, 0.973, 0.635, 0.715,
     0.975, 0.633, 0.701, 0.977, 0.631, 0.687, 0.979, 0.629, 0.672, 0.980,
     0.626, 0.657, 0.981, 0.623, 0.642, 0.982, 0.619, 0.626, 0.982, 0.616,
     0.609, 0.982, 0.612, 0.592, 0.981, 0.607, 0.575, 0.981, 0.603, 0.557,
     0.979, 0.598, 0.540, 0.978, 0.593, 0.521, 0.976, 0.588, 0.503, 0.974,
     0.582, 0.484, 0.972, 0.577, 0.465, 0.969, 0.571, 0.446, 0.966, 0.565,
     0.427, 0.963, 0.559, 0.407, 0.960, 0.553, 0.387, 0.956, 0.547, 0.368,
     0.953, 0.541, 0.347, 0.949, 0.534, 0.327, 0.945, 0.528, 0.306, 0.941,
     0.521, 0.285, 0.936, 0.514, 0.264, 0.932, 0.508, 0.242, 0.927, 0.501,
     0.220, 0.922, 0.494, 0.196, 0.918, 0.487, 0.172, 0.913, 0.480, 0.145,
     0.779, 0.465, 0.979, 0.785, 0.474, 0.971, 0.792, 0.484, 0.964, 0.798,
     0.492, 0.957, 0.805, 0.501, 0.950, 0.811, 0.509, 0.943, 0.818, 0.517,
     0.936, 0.824, 0.525, 0.929, 0.831, 0.533, 0.923, 0.838, 0.540, 0.916,
     0.844, 0.547, 0.910, 0.851, 0.554, 0.904, 0.857, 0.560, 0.897, 0.864,
     0.566, 0.891, 0.870, 0.572, 0.884, 0.877, 0.578, 0.878, 0.883, 0.583,
     0.871, 0.890, 0.589, 0.865, 0.896, 0.593, 0.858, 0.902, 0.598, 0.851,
     0.908, 0.602, 0.844, 0.914, 0.606, 0.837, 0.920, 0.609, 0.829, 0.925,
     0.613, 0.821, 0.931, 0.615, 0.813, 0.936, 0.618, 0.804, 0.941, 0.620,
     0.795, 0.946, 0.621, 0.786, 0.950, 0.622, 0.776, 0.955, 0.623, 0.765,
     0.959, 0.624, 0.755, 0.963, 0.624, 0.743, 0.966, 0.623, 0.731, 0.969,
     0.622, 0.719, 0.972, 0.621, 0.706, 0.974, 0.619, 0.693, 0.976, 0.617,
     0.679, 0.978, 0.615, 0.664, 0.979, 0.612, 0.649, 0.980, 0.609, 0.634,
     0.981, 0.606, 0.618, 0.981, 0.602, 0.601, 0.981, 0.598, 0.585, 0.981,
     0.594, 0.568, 0.980, 0.590, 0.550, 0.979, 0.585, 0.533, 0.978, 0.580,
     0.515, 0.976, 0.575, 0.496, 0.974, 0.570, 0.478, 0.972, 0.565, 0.459,
     0.969, 0.559, 0.440, 0.967, 0.553, 0.421, 0.964, 0.547, 0.402, 0.960,
     0.542, 0.382, 0.957, 0.535, 0.362, 0.953, 0.529, 0.342, 0.950, 0.523,
     0.322, 0.946, 0.517, 0.302, 0.942, 0.510, 0.281, 0.937, 0.504, 0.260,
     0.933, 0.497, 0.238, 0.929, 0.490, 0.216, 0.924, 0.484, 0.192, 0.919,
     0.477, 0.168, 0.914, 0.470, 0.141, 0.783, 0.453, 0.977, 0.789, 0.462,
     0.969, 0.796, 0.471, 0.962, 0.802, 0.480, 0.954, 0.808, 0.489, 0.947,
     0.815, 0.497, 0.940, 0.821, 0.505, 0.933, 0.828, 0.513, 0.926, 0.834,
     0.520, 0.919, 0.840, 0.527, 0.913, 0.847, 0.534, 0.906, 0.853, 0.541,
     0.899, 0.860, 0.548, 0.893, 0.866, 0.554, 0.886, 0.873, 0.560, 0.880,
     0.879, 0.565, 0.873, 0.885, 0.570, 0.866, 0.891, 0.575, 0.859, 0.897,
     0.580, 0.852, 0.903, 0.585, 0.845, 0.909, 0.589, 0.838, 0.915, 0.592,
     0.830, 0.921, 0.596, 0.822, 0.926, 0.599, 0.814, 0.931, 0.601, 0.805,
     0.936, 0.604, 0.797, 0.941, 0.606, 0.787, 0.946, 0.607, 0.778, 0.950,
     0.608, 0.768, 0.955, 0.609, 0.757, 0.958, 0.609, 0.746, 0.962, 0.609,
     0.735, 0.965, 0.609, 0.723, 0.968, 0.608, 0.710, 0.971, 0.607, 0.698,
     0.974, 0.605, 0.684, 0.976, 0.603, 0.670, 0.977, 0.601, 0.656, 0.979,
     0.598, 0.641, 0.980, 0.596, 0.626, 0.980, 0.592, 0.610, 0.981, 0.589,
     0.594, 0.981, 0.585, 0.577, 0.980, 0.581, 0.560, 0.980, 0.577, 0.543,
     0.979, 0.572, 0.526, 0.977, 0.568, 0.508, 0.976, 0.563, 0.490, 0.974,
     0.558, 0.471, 0.972, 0.552, 0.453, 0.969, 0.547, 0.434, 0.967, 0.541,
     0.415, 0.964, 0.536, 0.396, 0.961, 0.530, 0.377, 0.958, 0.524, 0.357,
     0.954, 0.518, 0.337, 0.950, 0.512, 0.317, 0.947, 0.505, 0.297, 0.943,
     0.499, 0.276, 0.938, 0.493, 0.255, 0.934, 0.486, 0.234, 0.930, 0.480,
     0.211, 0.925, 0.473, 0.188, 0.920, 0.466, 0.164, 0.916, 0.459, 0.137,
     0.787, 0.440, 0.975, 0.793, 0.450, 0.967, 0.799, 0.459, 0.959, 0.806,
     0.468, 0.952, 0.812, 0.476, 0.944, 0.818, 0.485, 0.937, 0.824, 0.493,
     0.930, 0.831, 0.500, 0.923, 0.837, 0.508, 0.916, 0.843, 0.515, 0.909,
     0.850, 0.522, 0.902, 0.856, 0.528, 0.895, 0.862, 0.535, 0.888, 0.868,
     0.541, 0.881, 0.874, 0.547, 0.875, 0.881, 0.552, 0.868, 0.887, 0.557,
     0.861, 0.893, 0.562, 0.853, 0.899, 0.567, 0.846, 0.904, 0.571, 0.839,
     0.910, 0.575, 0.831, 0.916, 0.579, 0.823, 0.921, 0.582, 0.815, 0.926,
     0.585, 0.807, 0.932, 0.587, 0.798, 0.937, 0.590, 0.789, 0.941, 0.591,
     0.780, 0.946, 0.593, 0.770, 0.950, 0.594, 0.760, 0.954, 0.595, 0.749,
     0.958, 0.595, 0.738, 0.962, 0.595, 0.727, 0.965, 0.595, 0.715, 0.968,
     0.594, 0.702, 0.970, 0.593, 0.689, 0.973, 0.591, 0.676, 0.975, 0.589,
     0.662, 0.976, 0.587, 0.648, 0.978, 0.585, 0.633, 0.979, 0.582, 0.618,
     0.980, 0.579, 0.602, 0.980, 0.575, 0.586, 0.980, 0.572, 0.570, 0.980,
     0.568, 0.553, 0.979, 0.564, 0.536, 0.978, 0.559, 0.518, 0.977, 0.555,
     0.501, 0.975, 0.550, 0.483, 0.974, 0.545, 0.465, 0.972, 0.540, 0.447,
     0.969, 0.535, 0.428, 0.967, 0.529, 0.409, 0.964, 0.524, 0.390, 0.961,
     0.518, 0.371, 0.958, 0.512, 0.352, 0.954, 0.506, 0.332, 0.951, 0.500,
     0.312, 0.947, 0.494, 0.292, 0.943, 0.488, 0.272, 0.939, 0.481, 0.251,
     0.935, 0.475, 0.229, 0.931, 0.469, 0.207, 0.926, 0.462, 0.184, 0.921,
     0.455, 0.159, 0.917, 0.449, 0.133, 0.791, 0.427, 0.973, 0.797, 0.437,
     0.964, 0.803, 0.446, 0.957, 0.809, 0.455, 0.949, 0.815, 0.464, 0.941,
     0.821, 0.472, 0.934, 0.827, 0.480, 0.926, 0.834, 0.488, 0.919, 0.840,
     0.495, 0.912, 0.846, 0.502, 0.905, 0.852, 0.509, 0.898, 0.858, 0.515,
     0.891, 0.864, 0.522, 0.884, 0.870, 0.528, 0.877, 0.876, 0.533, 0.870,
     0.882, 0.539, 0.862, 0.888, 0.544, 0.855, 0.894, 0.549, 0.848, 0.900,
     0.553, 0.840, 0.906, 0.557, 0.833, 0.911, 0.561, 0.825, 0.916, 0.565,
     0.817, 0.922, 0.568, 0.808, 0.927, 0.571, 0.800, 0.932, 0.573, 0.791,
     0.937, 0.575, 0.782, 0.941, 0.577, 0.772, 0.946, 0.579, 0.762, 0.950,
     0.580, 0.752, 0.954, 0.580, 0.741, 0.958, 0.581, 0.730, 0.961, 0.581,
     0.718, 0.964, 0.580, 0.706, 0.967, 0.580, 0.694, 0.970, 0.578, 0.681,
     0.972, 0.577, 0.667, 0.974, 0.575, 0.654, 0.976, 0.573, 0.639, 0.977,
     0.571, 0.625, 0.978, 0.568, 0.610, 0.979, 0.565, 0.594, 0.979, 0.562,
     0.578, 0.979, 0.558, 0.562, 0.979, 0.554, 0.545, 0.978, 0.550, 0.529,
     0.977, 0.546, 0.511, 0.976, 0.542, 0.494, 0.975, 0.537, 0.476, 0.973,
     0.532, 0.458, 0.971, 0.527, 0.440, 0.969, 0.522, 0.422, 0.967, 0.517,
     0.403, 0.964, 0.511, 0.385, 0.961, 0.506, 0.366, 0.958, 0.500, 0.347,
     0.955, 0.494, 0.327, 0.951, 0.488, 0.307, 0.947, 0.482, 0.287, 0.944,
     0.476, 0.267, 0.940, 0.470, 0.246, 0.935, 0.464, 0.225, 0.931, 0.458,
     0.203, 0.927, 0.451, 0.180, 0.922, 0.445, 0.155, 0.917, 0.438, 0.129,
     0.795, 0.413, 0.970, 0.801, 0.423, 0.962, 0.807, 0.433, 0.954, 0.813,
     0.442, 0.946, 0.818, 0.450, 0.938, 0.824, 0.459, 0.930, 0.830, 0.467,
     0.923, 0.836, 0.474, 0.915, 0.842, 0.482, 0.908, 0.848, 0.489, 0.901,
     0.854, 0.496, 0.894, 0.860, 0.502, 0.886, 0.866, 0.508, 0.879, 0.872,
     0.514, 0.872, 0.878, 0.520, 0.864, 0.884, 0.525, 0.857, 0.890, 0.530,
     0.850, 0.895, 0.535, 0.842, 0.901, 0.539, 0.834, 0.906, 0.543, 0.826,
     0.912, 0.547, 0.818, 0.917, 0.551, 0.810, 0.922, 0.554, 0.801, 0.927,
     0.557, 0.793, 0.932, 0.559, 0.783, 0.937, 0.561, 0.774, 0.941, 0.563,
     0.764, 0.946, 0.564, 0.754, 0.950, 0.565, 0.744, 0.953, 0.566, 0.733,
     0.957, 0.566, 0.722, 0.960, 0.566, 0.710, 0.963, 0.566, 0.698, 0.966,
     0.565, 0.685, 0.969, 0.564, 0.673, 0.971, 0.563, 0.659, 0.973, 0.561,
     0.645, 0.975, 0.559, 0.631, 0.976, 0.557, 0.617, 0.977, 0.554, 0.602,
     0.978, 0.551, 0.586, 0.978, 0.548, 0.571, 0.978, 0.545, 0.554, 0.978,
     0.541, 0.538, 0.977, 0.537, 0.521, 0.977, 0.533, 0.504, 0.976, 0.529,
     0.487, 0.974, 0.524, 0.470, 0.973, 0.519, 0.452, 0.971, 0.515, 0.434,
     0.969, 0.510, 0.416, 0.966, 0.504, 0.398, 0.964, 0.499, 0.379, 0.961,
     0.494, 0.360, 0.958, 0.488, 0.341, 0.955, 0.482, 0.322, 0.951, 0.477,
     0.302, 0.948, 0.471, 0.283, 0.944, 0.465, 0.262, 0.940, 0.459, 0.242,
     0.936, 0.452, 0.220, 0.932, 0.446, 0.198, 0.927, 0.440, 0.175, 0.923,
     0.434, 0.151, 0.918, 0.427, 0.124, 0.799, 0.399, 0.968, 0.804, 0.409,
     0.959, 0.810, 0.419, 0.951, 0.816, 0.428, 0.943, 0.822, 0.437, 0.935,
     0.827, 0.445, 0.927, 0.833, 0.453, 0.919, 0.839, 0.461, 0.912, 0.845,
     0.468, 0.904, 0.851, 0.475, 0.897, 0.857, 0.482, 0.889, 0.862, 0.489,
     0.882, 0.868, 0.495, 0.874, 0.874, 0.501, 0.867, 0.880, 0.506, 0.859,
     0.885, 0.511, 0.852, 0.891, 0.516, 0.844, 0.897, 0.521, 0.836, 0.902,
     0.525, 0.828, 0.907, 0.529, 0.820, 0.913, 0.533, 0.812, 0.918, 0.537,
     0.803, 0.923, 0.540, 0.794, 0.928, 0.542, 0.785, 0.932, 0.545, 0.776,
     0.937, 0.547, 0.767, 0.941, 0.549, 0.757, 0.945, 0.550, 0.747, 0.949,
     0.551, 0.736, 0.953, 0.552, 0.725, 0.956, 0.552, 0.714, 0.960, 0.552,
     0.702, 0.963, 0.552, 0.690, 0.965, 0.551, 0.677, 0.968, 0.550, 0.664,
     0.970, 0.549, 0.651, 0.972, 0.547, 0.637, 0.974, 0.545, 0.623, 0.975,
     0.543, 0.609, 0.976, 0.540, 0.594, 0.977, 0.537, 0.578, 0.977, 0.534,
     0.563, 0.977, 0.531, 0.547, 0.977, 0.527, 0.531, 0.976, 0.524, 0.514,
     0.976, 0.520, 0.497, 0.975, 0.516, 0.480, 0.973, 0.511, 0.463, 0.972,
     0.507, 0.446, 0.970, 0.502, 0.428, 0.968, 0.497, 0.410, 0.966, 0.492,
     0.392, 0.963, 0.487, 0.373, 0.960, 0.481, 0.355, 0.957, 0.476, 0.336,
     0.954, 0.470, 0.317, 0.951, 0.465, 0.297, 0.947, 0.459, 0.278, 0.944,
     0.453, 0.258, 0.940, 0.447, 0.237, 0.936, 0.441, 0.216, 0.932, 0.435,
     0.194, 0.927, 0.429, 0.171, 0.923, 0.422, 0.147, 0.918, 0.416, 0.120,
     0.802, 0.385, 0.965, 0.808, 0.395, 0.957, 0.813, 0.405, 0.948, 0.819,
     0.414, 0.940, 0.825, 0.423, 0.932, 0.830, 0.431, 0.924, 0.836, 0.439,
     0.916, 0.842, 0.447, 0.908, 0.847, 0.454, 0.900, 0.853, 0.462, 0.892,
     0.859, 0.468, 0.885, 0.864, 0.475, 0.877, 0.870, 0.481, 0.869, 0.876,
     0.487, 0.862, 0.881, 0.492, 0.854, 0.887, 0.498, 0.846, 0.892, 0.502,
     0.838, 0.898, 0.507, 0.830, 0.903, 0.511, 0.822, 0.908, 0.515, 0.814,
     0.913, 0.519, 0.805, 0.918, 0.522, 0.797, 0.923, 0.525, 0.788, 0.928,
     0.528, 0.778, 0.932, 0.530, 0.769, 0.937, 0.532, 0.759, 0.941, 0.534,
     0.749, 0.945, 0.535, 0.739, 0.949, 0.536, 0.728, 0.952, 0.537, 0.717,
     0.956, 0.537, 0.706, 0.959, 0.537, 0.694, 0.962, 0.537, 0.682, 0.964,
     0.536, 0.669, 0.967, 0.536, 0.656, 0.969, 0.534, 0.643, 0.971, 0.533,
     0.629, 0.972, 0.531, 0.615, 0.974, 0.529, 0.601, 0.975, 0.526, 0.586,
     0.975, 0.523, 0.571, 0.976, 0.521, 0.555, 0.976, 0.517, 0.540, 0.976,
     0.514, 0.523, 0.975, 0.510, 0.507, 0.975, 0.506, 0.490, 0.974, 0.502,
     0.474, 0.972, 0.498, 0.456, 0.971, 0.494, 0.439, 0.969, 0.489, 0.421,
     0.967, 0.484, 0.404, 0.965, 0.479, 0.386, 0.963, 0.474, 0.367, 0.960,
     0.469, 0.349, 0.957, 0.464, 0.330, 0.954, 0.458, 0.311, 0.951, 0.453,
     0.292, 0.947, 0.447, 0.273, 0.944, 0.441, 0.253, 0.940, 0.435, 0.232,
     0.936, 0.429, 0.211, 0.932, 0.423, 0.190, 0.927, 0.417, 0.167, 0.923,
     0.411, 0.142, 0.919, 0.405, 0.116, 0.806, 0.370, 0.963, 0.811, 0.380,
     0.954, 0.816, 0.390, 0.945, 0.822, 0.399, 0.937, 0.827, 0.408, 0.929,
     0.833, 0.417, 0.920, 0.838, 0.425, 0.912, 0.844, 0.433, 0.904, 0.850,
     0.440, 0.896, 0.855, 0.447, 0.888, 0.861, 0.454, 0.880, 0.866, 0.461,
     0.872, 0.872, 0.467, 0.865, 0.877, 0.473, 0.857, 0.883, 0.478, 0.849,
     0.888, 0.483, 0.841, 0.893, 0.488, 0.833, 0.899, 0.493, 0.824, 0.904,
     0.497, 0.816, 0.909, 0.501, 0.807, 0.914, 0.505, 0.799, 0.919, 0.508,
     0.790, 0.923, 0.511, 0.781, 0.928, 0.514, 0.771, 0.932, 0.516, 0.762,
     0.937, 0.518, 0.752, 0.941, 0.520, 0.742, 0.945, 0.521, 0.731, 0.948,
     0.522, 0.720, 0.952, 0.523, 0.709, 0.955, 0.523, 0.698, 0.958, 0.523,
     0.686, 0.961, 0.523, 0.674, 0.964, 0.522, 0.661, 0.966, 0.521, 0.648,
     0.968, 0.520, 0.635, 0.970, 0.518, 0.621, 0.971, 0.517, 0.607, 0.972,
     0.514, 0.593, 0.973, 0.512, 0.578, 0.974, 0.509, 0.563, 0.975, 0.507,
     0.548, 0.975, 0.503, 0.532, 0.975, 0.500, 0.516, 0.974, 0.497, 0.500,
     0.974, 0.493, 0.483, 0.973, 0.489, 0.467, 0.971, 0.485, 0.450, 0.970,
     0.480, 0.433, 0.968, 0.476, 0.415, 0.966, 0.471, 0.397, 0.964, 0.466,
     0.380, 0.962, 0.461, 0.362, 0.959, 0.456, 0.343, 0.956, 0.451, 0.325,
     0.953, 0.446, 0.306, 0.950, 0.440, 0.287, 0.947, 0.435, 0.268, 0.943,
     0.429, 0.248, 0.939, 0.423, 0.228, 0.936, 0.417, 0.207, 0.931, 0.411,
     0.185, 0.927, 0.405, 0.162, 0.923, 0.399, 0.138, 0.918, 0.393, 0.111,
     0.809, 0.354, 0.960, 0.814, 0.364, 0.951, 0.819, 0.375, 0.942, 0.825,
     0.384, 0.934, 0.830, 0.393, 0.925, 0.835, 0.402, 0.917, 0.841, 0.410,
     0.908, 0.846, 0.418, 0.900, 0.852, 0.426, 0.892, 0.857, 0.433, 0.884,
     0.863, 0.440, 0.876, 0.868, 0.446, 0.868, 0.873, 0.452, 0.860, 0.879,
     0.458, 0.852, 0.884, 0.464, 0.843, 0.889, 0.469, 0.835, 0.894, 0.474,
     0.827, 0.899, 0.478, 0.818, 0.904, 0.483, 0.810, 0.909, 0.486, 0.801,
     0.914, 0.490, 0.792, 0.919, 0.493, 0.783, 0.923, 0.496, 0.774, 0.928,
     0.499, 0.764, 0.932, 0.501, 0.755, 0.936, 0.503, 0.745, 0.940, 0.505,
     0.734, 0.944, 0.506, 0.724, 0.948, 0.507, 0.713, 0.951, 0.508, 0.701,
     0.954, 0.508, 0.690, 0.957, 0.508, 0.678, 0.960, 0.508, 0.666, 0.962,
     0.507, 0.653, 0.965, 0.507, 0.640, 0.967, 0.505, 0.627, 0.968, 0.504,
     0.613, 0.970, 0.502, 0.599, 0.971, 0.500, 0.585, 0.972, 0.498, 0.570,
     0.973, 0.495, 0.555, 0.973, 0.493, 0.540, 0.973, 0.490, 0.525, 0.973,
     0.486, 0.509, 0.973, 0.483, 0.493, 0.972, 0.479, 0.476, 0.971, 0.475,
     0.460, 0.970, 0.471, 0.443, 0.969, 0.467, 0.426, 0.967, 0.463, 0.409,
     0.965, 0.458, 0.391, 0.963, 0.453, 0.374, 0.961, 0.449, 0.356, 0.958,
     0.444, 0.338, 0.956, 0.438, 0.319, 0.953, 0.433, 0.301, 0.949, 0.428,
     0.282, 0.946, 0.422, 0.263, 0.943, 0.417, 0.243, 0.939, 0.411, 0.223,
     0.935, 0.405, 0.202, 0.931, 0.399, 0.181, 0.927, 0.393, 0.158, 0.923,
     0.387, 0.134, 0.918, 0.381, 0.107,
     ]).reshape((65, 65, 3))

BiOrangeBlue = np.array(
    [0.000, 0.000, 0.000, 0.000, 0.062, 0.125, 0.000, 0.125, 0.250, 0.000,
     0.188, 0.375, 0.000, 0.250, 0.500, 0.000, 0.312, 0.625, 0.000, 0.375,
     0.750, 0.000, 0.438, 0.875, 0.000, 0.500, 1.000, 0.125, 0.062, 0.000,
     0.125, 0.125, 0.125, 0.125, 0.188, 0.250, 0.125, 0.250, 0.375, 0.125,
     0.312, 0.500, 0.125, 0.375, 0.625, 0.125, 0.438, 0.750, 0.125, 0.500,
     0.875, 0.125, 0.562, 1.000, 0.250, 0.125, 0.000, 0.250, 0.188, 0.125,
     0.250, 0.250, 0.250, 0.250, 0.312, 0.375, 0.250, 0.375, 0.500, 0.250,
     0.438, 0.625, 0.250, 0.500, 0.750, 0.250, 0.562, 0.875, 0.250, 0.625,
     1.000, 0.375, 0.188, 0.000, 0.375, 0.250, 0.125, 0.375, 0.312, 0.250,
     0.375, 0.375, 0.375, 0.375, 0.438, 0.500, 0.375, 0.500, 0.625, 0.375,
     0.562, 0.750, 0.375, 0.625, 0.875, 0.375, 0.688, 1.000, 0.500, 0.250,
     0.000, 0.500, 0.312, 0.125, 0.500, 0.375, 0.250, 0.500, 0.438, 0.375,
     0.500, 0.500, 0.500, 0.500, 0.562, 0.625, 0.500, 0.625, 0.750, 0.500,
     0.688, 0.875, 0.500, 0.750, 1.000, 0.625, 0.312, 0.000, 0.625, 0.375,
     0.125, 0.625, 0.438, 0.250, 0.625, 0.500, 0.375, 0.625, 0.562, 0.500,
     0.625, 0.625, 0.625, 0.625, 0.688, 0.750, 0.625, 0.750, 0.875, 0.625,
     0.812, 1.000, 0.750, 0.375, 0.000, 0.750, 0.438, 0.125, 0.750, 0.500,
     0.250, 0.750, 0.562, 0.375, 0.750, 0.625, 0.500, 0.750, 0.688, 0.625,
     0.750, 0.750, 0.750, 0.750, 0.812, 0.875, 0.750, 0.875, 1.000, 0.875,
     0.438, 0.000, 0.875, 0.500, 0.125, 0.875, 0.562, 0.250, 0.875, 0.625,
     0.375, 0.875, 0.688, 0.500, 0.875, 0.750, 0.625, 0.875, 0.812, 0.750,
     0.875, 0.875, 0.875, 0.875, 0.938, 1.000, 1.000, 0.500, 0.000, 1.000,
     0.562, 0.125, 1.000, 0.625, 0.250, 1.000, 0.688, 0.375, 1.000, 0.750,
     0.500, 1.000, 0.812, 0.625, 1.000, 0.875, 0.750, 1.000, 0.938, 0.875,
     1.000, 1.000, 1.000,
     ]).reshape((9, 9, 3))

cmaps = {
    "BiPeak": SegmentedBivarColormap(
        BiPeak, 256, "square", (.5, .5), name="BiPeak"),
    "BiOrangeBlue": SegmentedBivarColormap(
        BiOrangeBlue, 256, "square", (0, 0), name="BiOrangeBlue"),
    "BiCone": SegmentedBivarColormap(BiPeak, 256, "circle", (.5, .5), name="BiCone"),
}