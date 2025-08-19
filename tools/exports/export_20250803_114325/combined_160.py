
# === NexusCore/openenv\Lib\site-packages\trio\_channel.py ===
from __future__ import annotations

import sys
from collections import OrderedDict, deque
from collections.abc import AsyncGenerator, Callable  # noqa: TC003  # Needed for Sphinx
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import wraps
from math import inf
from typing import (
    TYPE_CHECKING,
    Generic,
)

import attrs
from outcome import Error, Value

import trio

from ._abc import ReceiveChannel, ReceiveType, SendChannel, SendType, T
from ._core import Abort, RaiseCancelT, Task, enable_ki_protection
from ._util import (
    MultipleExceptionError,
    NoPublicConstructor,
    final,
    generic_function,
    raise_single_exception_from_group,
)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import ParamSpec, Self

    P = ParamSpec("P")
elif "sphinx" in sys.modules:
    # P needs to exist for Sphinx to parse the type hints successfully.
    try:
        from typing_extensions import ParamSpec
    except ImportError:
        P = ...  # This is valid in Callable, though not correct
    else:
        P = ParamSpec("P")


def _open_memory_channel(
    max_buffer_size: int | float,  # noqa: PYI041
) -> tuple[MemorySendChannel[T], MemoryReceiveChannel[T]]:
    """Open a channel for passing objects between tasks within a process.

    Memory channels are lightweight, cheap to allocate, and entirely
    in-memory. They don't involve any operating-system resources, or any kind
    of serialization. They just pass Python objects directly between tasks
    (with a possible stop in an internal buffer along the way).

    Channel objects can be closed by calling `~trio.abc.AsyncResource.aclose`
    or using ``async with``. They are *not* automatically closed when garbage
    collected. Closing memory channels isn't mandatory, but it is generally a
    good idea, because it helps avoid situations where tasks get stuck waiting
    on a channel when there's no-one on the other side. See
    :ref:`channel-shutdown` for details.

    Memory channel operations are all atomic with respect to
    cancellation, either `~trio.abc.ReceiveChannel.receive` will
    successfully return an object, or it will raise :exc:`Cancelled`
    while leaving the channel unchanged.

    Args:
      max_buffer_size (int or math.inf): The maximum number of items that can
        be buffered in the channel before :meth:`~trio.abc.SendChannel.send`
        blocks. Choosing a sensible value here is important to ensure that
        backpressure is communicated promptly and avoid unnecessary latency;
        see :ref:`channel-buffering` for more details. If in doubt, use 0.

    Returns:
      A pair ``(send_channel, receive_channel)``. If you have
      trouble remembering which order these go in, remember: data
      flows from left → right.

    In addition to the standard channel methods, all memory channel objects
    provide a ``statistics()`` method, which returns an object with the
    following fields:

    * ``current_buffer_used``: The number of items currently stored in the
      channel buffer.
    * ``max_buffer_size``: The maximum number of items allowed in the buffer,
      as passed to :func:`open_memory_channel`.
    * ``open_send_channels``: The number of open
      :class:`MemorySendChannel` endpoints pointing to this channel.
      Initially 1, but can be increased by
      :meth:`MemorySendChannel.clone`.
    * ``open_receive_channels``: Likewise, but for open
      :class:`MemoryReceiveChannel` endpoints.
    * ``tasks_waiting_send``: The number of tasks blocked in ``send`` on this
      channel (summing over all clones).
    * ``tasks_waiting_receive``: The number of tasks blocked in ``receive`` on
      this channel (summing over all clones).

    """
    if max_buffer_size != inf and not isinstance(max_buffer_size, int):
        raise TypeError("max_buffer_size must be an integer or math.inf")
    if max_buffer_size < 0:
        raise ValueError("max_buffer_size must be >= 0")
    state: MemoryChannelState[T] = MemoryChannelState(max_buffer_size)
    return (
        MemorySendChannel[T]._create(state),
        MemoryReceiveChannel[T]._create(state),
    )


# This workaround requires python3.9+, once older python versions are not supported
# or there's a better way of achieving type-checking on a generic factory function,
# it could replace the normal function header
if TYPE_CHECKING:
    # written as a class so you can say open_memory_channel[int](5)
    class open_memory_channel(tuple["MemorySendChannel[T]", "MemoryReceiveChannel[T]"]):
        def __new__(  # type: ignore[misc]  # "must return a subtype"
            cls,
            max_buffer_size: int | float,  # noqa: PYI041
        ) -> tuple[MemorySendChannel[T], MemoryReceiveChannel[T]]:
            return _open_memory_channel(max_buffer_size)

        def __init__(self, max_buffer_size: int | float) -> None:  # noqa: PYI041
            ...

else:
    # apply the generic_function decorator to make open_memory_channel indexable
    # so it's valid to say e.g. ``open_memory_channel[bytes](5)`` at runtime
    open_memory_channel = generic_function(_open_memory_channel)


@attrs.frozen
class MemoryChannelStatistics:
    current_buffer_used: int
    max_buffer_size: int | float
    open_send_channels: int
    open_receive_channels: int
    tasks_waiting_send: int
    tasks_waiting_receive: int


@attrs.define
class MemoryChannelState(Generic[T]):
    max_buffer_size: int | float
    data: deque[T] = attrs.Factory(deque)
    # Counts of open endpoints using this state
    open_send_channels: int = 0
    open_receive_channels: int = 0
    # {task: value}
    send_tasks: OrderedDict[Task, T] = attrs.Factory(OrderedDict)
    # {task: None}
    receive_tasks: OrderedDict[Task, None] = attrs.Factory(OrderedDict)

    def statistics(self) -> MemoryChannelStatistics:
        return MemoryChannelStatistics(
            current_buffer_used=len(self.data),
            max_buffer_size=self.max_buffer_size,
            open_send_channels=self.open_send_channels,
            open_receive_channels=self.open_receive_channels,
            tasks_waiting_send=len(self.send_tasks),
            tasks_waiting_receive=len(self.receive_tasks),
        )


@final
@attrs.define(eq=False, repr=False, slots=False)
class MemorySendChannel(SendChannel[SendType], metaclass=NoPublicConstructor):
    _state: MemoryChannelState[SendType]
    _closed: bool = False
    # This is just the tasks waiting on *this* object. As compared to
    # self._state.send_tasks, which includes tasks from this object and
    # all clones.
    _tasks: set[Task] = attrs.Factory(set)

    def __attrs_post_init__(self) -> None:
        self._state.open_send_channels += 1

    def __repr__(self) -> str:
        return f"<send channel at {id(self):#x}, using buffer at {id(self._state):#x}>"

    def statistics(self) -> MemoryChannelStatistics:
        """Returns a `MemoryChannelStatistics` for the memory channel this is
        associated with."""
        # XX should we also report statistics specific to this object?
        return self._state.statistics()

    @enable_ki_protection
    def send_nowait(self, value: SendType) -> None:
        """Like `~trio.abc.SendChannel.send`, but if the channel's buffer is
        full, raises `WouldBlock` instead of blocking.

        """
        if self._closed:
            raise trio.ClosedResourceError
        if self._state.open_receive_channels == 0:
            raise trio.BrokenResourceError
        if self._state.receive_tasks:
            assert not self._state.data
            task, _ = self._state.receive_tasks.popitem(last=False)
            task.custom_sleep_data._tasks.remove(task)
            trio.lowlevel.reschedule(task, Value(value))
        elif len(self._state.data) < self._state.max_buffer_size:
            self._state.data.append(value)
        else:
            raise trio.WouldBlock

    @enable_ki_protection
    async def send(self, value: SendType) -> None:
        """See `SendChannel.send <trio.abc.SendChannel.send>`.

        Memory channels allow multiple tasks to call `send` at the same time.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.send_nowait(value)
        except trio.WouldBlock:
            pass
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            return

        task = trio.lowlevel.current_task()
        self._tasks.add(task)
        self._state.send_tasks[task] = value
        task.custom_sleep_data = self

        def abort_fn(_: RaiseCancelT) -> Abort:
            self._tasks.remove(task)
            del self._state.send_tasks[task]
            return trio.lowlevel.Abort.SUCCEEDED

        await trio.lowlevel.wait_task_rescheduled(abort_fn)

    # Return type must be stringified or use a TypeVar
    @enable_ki_protection
    def clone(self) -> MemorySendChannel[SendType]:
        """Clone this send channel object.

        This returns a new `MemorySendChannel` object, which acts as a
        duplicate of the original: sending on the new object does exactly the
        same thing as sending on the old object. (If you're familiar with
        `os.dup`, then this is a similar idea.)

        However, closing one of the objects does not close the other, and
        receivers don't get `EndOfChannel` until *all* clones have been
        closed.

        This is useful for communication patterns that involve multiple
        producers all sending objects to the same destination. If you give
        each producer its own clone of the `MemorySendChannel`, and then make
        sure to close each `MemorySendChannel` when it's finished, receivers
        will automatically get notified when all producers are finished. See
        :ref:`channel-mpmc` for examples.

        Raises:
          trio.ClosedResourceError: if you already closed this
              `MemorySendChannel` object.

        """
        if self._closed:
            raise trio.ClosedResourceError
        return MemorySendChannel._create(self._state)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @enable_ki_protection
    def close(self) -> None:
        """Close this send channel object synchronously.

        All channel objects have an asynchronous `~.AsyncResource.aclose` method.
        Memory channels can also be closed synchronously. This has the same
        effect on the channel and other tasks using it, but `close` is not a
        trio checkpoint. This simplifies cleaning up in cancelled tasks.

        Using ``with send_channel:`` will close the channel object on leaving
        the with block.

        """
        if self._closed:
            return
        self._closed = True
        for task in self._tasks:
            trio.lowlevel.reschedule(task, Error(trio.ClosedResourceError()))
            del self._state.send_tasks[task]
        self._tasks.clear()
        self._state.open_send_channels -= 1
        if self._state.open_send_channels == 0:
            assert not self._state.send_tasks
            for task in self._state.receive_tasks:
                task.custom_sleep_data._tasks.remove(task)
                trio.lowlevel.reschedule(task, Error(trio.EndOfChannel()))
            self._state.receive_tasks.clear()

    @enable_ki_protection
    async def aclose(self) -> None:
        """Close this send channel object asynchronously.

        See `MemorySendChannel.close`."""
        self.close()
        await trio.lowlevel.checkpoint()


@final
@attrs.define(eq=False, repr=False, slots=False)
class MemoryReceiveChannel(ReceiveChannel[ReceiveType], metaclass=NoPublicConstructor):
    _state: MemoryChannelState[ReceiveType]
    _closed: bool = False
    _tasks: set[trio._core._run.Task] = attrs.Factory(set)

    def __attrs_post_init__(self) -> None:
        self._state.open_receive_channels += 1

    def statistics(self) -> MemoryChannelStatistics:
        """Returns a `MemoryChannelStatistics` for the memory channel this is
        associated with."""
        return self._state.statistics()

    def __repr__(self) -> str:
        return (
            f"<receive channel at {id(self):#x}, using buffer at {id(self._state):#x}>"
        )

    @enable_ki_protection
    def receive_nowait(self) -> ReceiveType:
        """Like `~trio.abc.ReceiveChannel.receive`, but if there's nothing
        ready to receive, raises `WouldBlock` instead of blocking.

        """
        if self._closed:
            raise trio.ClosedResourceError
        if self._state.send_tasks:
            task, value = self._state.send_tasks.popitem(last=False)
            task.custom_sleep_data._tasks.remove(task)
            trio.lowlevel.reschedule(task)
            self._state.data.append(value)
            # Fall through
        if self._state.data:
            return self._state.data.popleft()
        if not self._state.open_send_channels:
            raise trio.EndOfChannel
        raise trio.WouldBlock

    @enable_ki_protection
    async def receive(self) -> ReceiveType:
        """See `ReceiveChannel.receive <trio.abc.ReceiveChannel.receive>`.

        Memory channels allow multiple tasks to call `receive` at the same
        time. The first task will get the first item sent, the second task
        will get the second item sent, and so on.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            value = self.receive_nowait()
        except trio.WouldBlock:
            pass
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            return value

        task = trio.lowlevel.current_task()
        self._tasks.add(task)
        self._state.receive_tasks[task] = None
        task.custom_sleep_data = self

        def abort_fn(_: RaiseCancelT) -> Abort:
            self._tasks.remove(task)
            del self._state.receive_tasks[task]
            return trio.lowlevel.Abort.SUCCEEDED

        # Not strictly guaranteed to return ReceiveType, but will do so unless
        # you intentionally reschedule with a bad value.
        return await trio.lowlevel.wait_task_rescheduled(abort_fn)  # type: ignore[no-any-return]

    @enable_ki_protection
    def clone(self) -> MemoryReceiveChannel[ReceiveType]:
        """Clone this receive channel object.

        This returns a new `MemoryReceiveChannel` object, which acts as a
        duplicate of the original: receiving on the new object does exactly
        the same thing as receiving on the old object.

        However, closing one of the objects does not close the other, and the
        underlying channel is not closed until all clones are closed. (If
        you're familiar with `os.dup`, then this is a similar idea.)

        This is useful for communication patterns that involve multiple
        consumers all receiving objects from the same underlying channel. See
        :ref:`channel-mpmc` for examples.

        .. warning:: The clones all share the same underlying channel.
           Whenever a clone :meth:`receive`\\s a value, it is removed from the
           channel and the other clones do *not* receive that value. If you
           want to send multiple copies of the same stream of values to
           multiple destinations, like :func:`itertools.tee`, then you need to
           find some other solution; this method does *not* do that.

        Raises:
          trio.ClosedResourceError: if you already closed this
              `MemoryReceiveChannel` object.

        """
        if self._closed:
            raise trio.ClosedResourceError
        return MemoryReceiveChannel._create(self._state)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @enable_ki_protection
    def close(self) -> None:
        """Close this receive channel object synchronously.

        All channel objects have an asynchronous `~.AsyncResource.aclose` method.
        Memory channels can also be closed synchronously. This has the same
        effect on the channel and other tasks using it, but `close` is not a
        trio checkpoint. This simplifies cleaning up in cancelled tasks.

        Using ``with receive_channel:`` will close the channel object on
        leaving the with block.

        """
        if self._closed:
            return
        self._closed = True
        for task in self._tasks:
            trio.lowlevel.reschedule(task, Error(trio.ClosedResourceError()))
            del self._state.receive_tasks[task]
        self._tasks.clear()
        self._state.open_receive_channels -= 1
        if self._state.open_receive_channels == 0:
            assert not self._state.receive_tasks
            for task in self._state.send_tasks:
                task.custom_sleep_data._tasks.remove(task)
                trio.lowlevel.reschedule(task, Error(trio.BrokenResourceError()))
            self._state.send_tasks.clear()
            self._state.data.clear()

    @enable_ki_protection
    async def aclose(self) -> None:
        """Close this receive channel object asynchronously.

        See `MemoryReceiveChannel.close`."""
        self.close()
        await trio.lowlevel.checkpoint()


class RecvChanWrapper(ReceiveChannel[T]):
    def __init__(
        self, recv_chan: MemoryReceiveChannel[T], send_semaphore: trio.Semaphore
    ) -> None:
        self._recv_chan = recv_chan
        self._send_semaphore = send_semaphore

    async def receive(self) -> T:
        self._send_semaphore.release()
        return await self._recv_chan.receive()

    async def aclose(self) -> None:
        await self._recv_chan.aclose()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._recv_chan.close()


def as_safe_channel(
    fn: Callable[P, AsyncGenerator[T, None]],
) -> Callable[P, AbstractAsyncContextManager[ReceiveChannel[T]]]:
    """Decorate an async generator function to make it cancellation-safe.

    The ``yield`` keyword offers a very convenient way to write iterators...
    which makes it really unfortunate that async generators are so difficult
    to call correctly.  Yielding from the inside of a cancel scope or a nursery
    to the outside `violates structured concurrency <https://xkcd.com/292/>`_
    with consequences explained in :pep:`789`.  Even then, resource cleanup
    errors remain common (:pep:`533`) unless you wrap every call in
    :func:`~contextlib.aclosing`.

    This decorator gives you the best of both worlds: with careful exception
    handling and a background task we preserve structured concurrency by
    offering only the safe interface, and you can still write your iterables
    with the convenience of ``yield``.  For example::

        @as_safe_channel
        async def my_async_iterable(arg, *, kwarg=True):
            while ...:
                item = await ...
                yield item

        async with my_async_iterable(...) as recv_chan:
            async for item in recv_chan:
                ...

    While the combined async-with-async-for can be inconvenient at first,
    the context manager is indispensable for both correctness and for prompt
    cleanup of resources.
    """
    # Perhaps a future PEP will adopt `async with for` syntax, like
    # https://coconut.readthedocs.io/en/master/DOCS.html#async-with-for

    @asynccontextmanager
    @wraps(fn)
    async def context_manager(
        *args: P.args, **kwargs: P.kwargs
    ) -> AsyncGenerator[trio._channel.RecvChanWrapper[T], None]:
        send_chan, recv_chan = trio.open_memory_channel[T](0)
        try:
            async with trio.open_nursery(strict_exception_groups=True) as nursery:
                agen = fn(*args, **kwargs)
                send_semaphore = trio.Semaphore(0)
                # `nursery.start` to make sure that we will clean up send_chan & agen
                # If this errors we don't close `recv_chan`, but the caller
                # never gets access to it, so that's not a problem.
                await nursery.start(
                    _move_elems_to_channel, agen, send_chan, send_semaphore
                )
                # `async with recv_chan` could eat exceptions, so use sync cm
                with RecvChanWrapper(recv_chan, send_semaphore) as wrapped_recv_chan:
                    yield wrapped_recv_chan
                # User has exited context manager, cancel to immediately close the
                # abandoned generator if it's still alive.
                nursery.cancel_scope.cancel()
        except BaseExceptionGroup as eg:
            try:
                raise_single_exception_from_group(eg)
            except MultipleExceptionError:
                # In case user has except* we make it possible for them to handle the
                # exceptions.
                raise BaseExceptionGroup(
                    "Encountered exception during cleanup of generator object, as well as exception in the contextmanager body - unable to unwrap.",
                    [eg],
                ) from None

    async def _move_elems_to_channel(
        agen: AsyncGenerator[T, None],
        send_chan: trio.MemorySendChannel[T],
        send_semaphore: trio.Semaphore,
        task_status: trio.TaskStatus,
    ) -> None:
        # `async with send_chan` will eat exceptions,
        # see https://github.com/python-trio/trio/issues/1559
        with send_chan:
            try:
                task_status.started()
                while True:
                    # wait for receiver to call next on the aiter
                    await send_semaphore.acquire()
                    try:
                        value = await agen.__anext__()
                    except StopAsyncIteration:
                        return
                    # Send the value to the channel
                    await send_chan.send(value)
            finally:
                # replace try-finally with contextlib.aclosing once python39 is dropped
                await agen.aclose()

    return context_manager

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_net_command_factory_json.py ===
from functools import partial
import itertools
import os
import sys
import socket as socket_module

from _pydev_bundle._pydev_imports_tipper import TYPE_IMPORT, TYPE_CLASS, TYPE_FUNCTION, TYPE_ATTR, TYPE_BUILTIN, TYPE_PARAM
from _pydev_bundle.pydev_is_thread_alive import is_thread_alive
from _pydev_bundle.pydev_override import overrides
from _pydevd_bundle._debug_adapter import pydevd_schema
from _pydevd_bundle._debug_adapter.pydevd_schema import (
    ModuleEvent,
    ModuleEventBody,
    Module,
    OutputEventBody,
    OutputEvent,
    ContinuedEventBody,
    ExitedEventBody,
    ExitedEvent,
)
from _pydevd_bundle.pydevd_comm_constants import (
    CMD_THREAD_CREATE,
    CMD_RETURN,
    CMD_MODULE_EVENT,
    CMD_WRITE_TO_CONSOLE,
    CMD_STEP_INTO,
    CMD_STEP_INTO_MY_CODE,
    CMD_STEP_OVER,
    CMD_STEP_OVER_MY_CODE,
    CMD_STEP_RETURN,
    CMD_STEP_CAUGHT_EXCEPTION,
    CMD_ADD_EXCEPTION_BREAK,
    CMD_SET_BREAK,
    CMD_SET_NEXT_STATEMENT,
    CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION,
    CMD_THREAD_RESUME_SINGLE_NOTIFICATION,
    CMD_THREAD_KILL,
    CMD_STOP_ON_START,
    CMD_INPUT_REQUESTED,
    CMD_EXIT,
    CMD_STEP_INTO_COROUTINE,
    CMD_STEP_RETURN_MY_CODE,
    CMD_SMART_STEP_INTO,
    CMD_SET_FUNCTION_BREAK,
    CMD_THREAD_RUN,
)
from _pydevd_bundle.pydevd_constants import get_thread_id, ForkSafeLock, DebugInfoHolder
from _pydevd_bundle.pydevd_net_command import NetCommand, NULL_NET_COMMAND
from _pydevd_bundle.pydevd_net_command_factory_xml import NetCommandFactory
from _pydevd_bundle.pydevd_utils import get_non_pydevd_threads
import pydevd_file_utils
from _pydevd_bundle.pydevd_comm import build_exception_info_response
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info
from _pydevd_bundle import pydevd_frame_utils, pydevd_constants, pydevd_utils
import linecache
from io import StringIO
from _pydev_bundle import pydev_log


class ModulesManager(object):
    def __init__(self):
        self._lock = ForkSafeLock()
        self._modules = {}
        self._next_id = partial(next, itertools.count(0))

    def track_module(self, filename_in_utf8, module_name, frame):
        """
        :return list(NetCommand):
            Returns a list with the module events to be sent.
        """
        if filename_in_utf8 in self._modules:
            return []

        module_events = []
        with self._lock:
            # Must check again after getting the lock.
            if filename_in_utf8 in self._modules:
                return

            try:
                version = str(frame.f_globals.get("__version__", ""))
            except:
                version = "<unknown>"

            try:
                package_name = str(frame.f_globals.get("__package__", ""))
            except:
                package_name = "<unknown>"

            module_id = self._next_id()

            module = Module(module_id, module_name, filename_in_utf8)
            if version:
                module.version = version

            if package_name:
                # Note: package doesn't appear in the docs but seems to be expected?
                module.kwargs["package"] = package_name

            module_event = ModuleEvent(ModuleEventBody("new", module))

            module_events.append(NetCommand(CMD_MODULE_EVENT, 0, module_event, is_json=True))

            self._modules[filename_in_utf8] = module.to_dict()
        return module_events

    def get_modules_info(self):
        """
        :return list(Module)
        """
        with self._lock:
            return list(self._modules.values())


class NetCommandFactoryJson(NetCommandFactory):
    """
    Factory for commands which will provide messages as json (they should be
    similar to the debug adapter where possible, although some differences
    are currently Ok).

    Note that it currently overrides the xml version so that messages
    can be done one at a time (any message not overridden will currently
    use the xml version) -- after having all messages handled, it should
    no longer use NetCommandFactory as the base class.
    """

    def __init__(self):
        NetCommandFactory.__init__(self)
        self.modules_manager = ModulesManager()

    @overrides(NetCommandFactory.make_version_message)
    def make_version_message(self, seq):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_protocol_set_message)
    def make_protocol_set_message(self, seq):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_thread_created_message)
    def make_thread_created_message(self, thread):
        # Note: the thread id for the debug adapter must be an int
        # (make the actual id from get_thread_id respect that later on).
        msg = pydevd_schema.ThreadEvent(
            pydevd_schema.ThreadEventBody("started", get_thread_id(thread)),
        )

        return NetCommand(CMD_THREAD_CREATE, 0, msg, is_json=True)

    @overrides(NetCommandFactory.make_custom_frame_created_message)
    def make_custom_frame_created_message(self, frame_id, frame_description):
        self._additional_thread_id_to_thread_name[frame_id] = frame_description
        msg = pydevd_schema.ThreadEvent(
            pydevd_schema.ThreadEventBody("started", frame_id),
        )

        return NetCommand(CMD_THREAD_CREATE, 0, msg, is_json=True)

    @overrides(NetCommandFactory.make_thread_killed_message)
    def make_thread_killed_message(self, tid):
        self._additional_thread_id_to_thread_name.pop(tid, None)
        msg = pydevd_schema.ThreadEvent(
            pydevd_schema.ThreadEventBody("exited", tid),
        )

        return NetCommand(CMD_THREAD_KILL, 0, msg, is_json=True)

    @overrides(NetCommandFactory.make_list_threads_message)
    def make_list_threads_message(self, py_db, seq):
        threads = []
        for thread in get_non_pydevd_threads():
            if is_thread_alive(thread):
                thread_id = get_thread_id(thread)

                # Notify that it's created (no-op if we already notified before).
                py_db.notify_thread_created(thread_id, thread)

                thread_schema = pydevd_schema.Thread(id=thread_id, name=thread.name)
                threads.append(thread_schema.to_dict())

        for thread_id, thread_name in list(self._additional_thread_id_to_thread_name.items()):
            thread_schema = pydevd_schema.Thread(id=thread_id, name=thread_name)
            threads.append(thread_schema.to_dict())

        body = pydevd_schema.ThreadsResponseBody(threads)
        response = pydevd_schema.ThreadsResponse(request_seq=seq, success=True, command="threads", body=body)

        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    @overrides(NetCommandFactory.make_get_completions_message)
    def make_get_completions_message(self, seq, completions, qualifier, start):
        COMPLETION_TYPE_LOOK_UP = {
            TYPE_IMPORT: pydevd_schema.CompletionItemType.MODULE,
            TYPE_CLASS: pydevd_schema.CompletionItemType.CLASS,
            TYPE_FUNCTION: pydevd_schema.CompletionItemType.FUNCTION,
            TYPE_ATTR: pydevd_schema.CompletionItemType.FIELD,
            TYPE_BUILTIN: pydevd_schema.CompletionItemType.KEYWORD,
            TYPE_PARAM: pydevd_schema.CompletionItemType.VARIABLE,
        }

        qualifier = qualifier.lower()
        qualifier_len = len(qualifier)
        targets = []
        for completion in completions:
            label = completion[0]
            if label.lower().startswith(qualifier):
                completion = pydevd_schema.CompletionItem(
                    label=label, type=COMPLETION_TYPE_LOOK_UP[completion[3]], start=start, length=qualifier_len
                )
                targets.append(completion.to_dict())

        body = pydevd_schema.CompletionsResponseBody(targets)
        response = pydevd_schema.CompletionsResponse(request_seq=seq, success=True, command="completions", body=body)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def _format_frame_name(self, fmt, initial_name, module_name, line, path):
        if fmt is None:
            return initial_name
        frame_name = initial_name
        if fmt.get("module", False):
            if module_name:
                if initial_name == "<module>":
                    frame_name = module_name
                else:
                    frame_name = "%s.%s" % (module_name, initial_name)
            else:
                basename = os.path.basename(path)
                basename = basename[0:-3] if basename.lower().endswith(".py") else basename
                if initial_name == "<module>":
                    frame_name = "%s in %s" % (initial_name, basename)
                else:
                    frame_name = "%s.%s" % (basename, initial_name)

        if fmt.get("line", False):
            frame_name = "%s : %d" % (frame_name, line)

        return frame_name

    @overrides(NetCommandFactory.make_get_thread_stack_message)
    def make_get_thread_stack_message(self, py_db, seq, thread_id, topmost_frame, fmt, must_be_suspended=False, start_frame=0, levels=0):
        frames = []
        module_events = []

        try:
            # : :type suspended_frames_manager: SuspendedFramesManager
            suspended_frames_manager = py_db.suspended_frames_manager
            frames_list = suspended_frames_manager.get_frames_list(thread_id)
            if frames_list is None:
                # Could not find stack of suspended frame...
                if must_be_suspended:
                    return None
                else:
                    frames_list = pydevd_frame_utils.create_frames_list_from_frame(topmost_frame)

            for (
                frame_id,
                frame,
                method_name,
                original_filename,
                filename_in_utf8,
                lineno,
                applied_mapping,
                show_as_current_frame,
                line_col_info,
            ) in self._iter_visible_frames_info(py_db, frames_list, flatten_chained=True):
                try:
                    module_name = str(frame.f_globals.get("__name__", ""))
                except:
                    module_name = "<unknown>"

                module_events.extend(self.modules_manager.track_module(filename_in_utf8, module_name, frame))

                presentation_hint = None
                if not getattr(frame, "IS_PLUGIN_FRAME", False):  # Never filter out plugin frames!
                    if py_db.is_files_filter_enabled and py_db.apply_files_filter(frame, original_filename, False):
                        continue

                    if not py_db.in_project_scope(frame):
                        presentation_hint = "subtle"

                formatted_name = self._format_frame_name(fmt, method_name, module_name, lineno, filename_in_utf8)
                if show_as_current_frame:
                    formatted_name += " (Current frame)"
                source_reference = pydevd_file_utils.get_client_filename_source_reference(filename_in_utf8)

                if not source_reference and not applied_mapping and not os.path.exists(original_filename):
                    if getattr(frame.f_code, "co_lines", None) or getattr(frame.f_code, "co_lnotab", None):
                        # Create a source-reference to be used where we provide the source by decompiling the code.
                        # Note: When the time comes to retrieve the source reference in this case, we'll
                        # check the linecache first (see: get_decompiled_source_from_frame_id).
                        source_reference = pydevd_file_utils.create_source_reference_for_frame_id(frame_id, original_filename)
                    else:
                        # Check if someone added a source reference to the linecache (Python attrs does this).
                        if linecache.getline(original_filename, 1):
                            source_reference = pydevd_file_utils.create_source_reference_for_linecache(original_filename)

                column = 1
                endcol = None
                if line_col_info is not None:
                    try:
                        line_text = linecache.getline(original_filename, lineno)
                    except:
                        if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 2:
                            pydev_log.exception("Unable to get line from linecache for file: %s", original_filename)
                    else:
                        if line_text:
                            colno, endcolno = line_col_info.map_columns_to_line(line_text)
                            column = colno + 1
                            if line_col_info.lineno == line_col_info.end_lineno:
                                endcol = endcolno + 1

                frames.append(
                    pydevd_schema.StackFrame(
                        frame_id,
                        formatted_name,
                        lineno,
                        column=column,
                        endColumn=endcol,
                        source={
                            "path": filename_in_utf8,
                            "sourceReference": source_reference,
                        },
                        presentationHint=presentation_hint,
                    ).to_dict()
                )
        finally:
            topmost_frame = None

        for module_event in module_events:
            py_db.writer.add_command(module_event)

        total_frames = len(frames)
        stack_frames = frames
        if bool(levels):
            start = start_frame
            end = min(start + levels, total_frames)
            stack_frames = frames[start:end]

        response = pydevd_schema.StackTraceResponse(
            request_seq=seq,
            success=True,
            command="stackTrace",
            body=pydevd_schema.StackTraceResponseBody(stackFrames=stack_frames, totalFrames=total_frames),
        )
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    @overrides(NetCommandFactory.make_warning_message)
    def make_warning_message(self, msg):
        category = "important"
        body = OutputEventBody(msg, category)
        event = OutputEvent(body)
        return NetCommand(CMD_WRITE_TO_CONSOLE, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_io_message)
    def make_io_message(self, msg, ctx):
        category = "stdout" if int(ctx) == 1 else "stderr"
        body = OutputEventBody(msg, category)
        event = OutputEvent(body)
        return NetCommand(CMD_WRITE_TO_CONSOLE, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_console_message)
    def make_console_message(self, msg):
        category = "console"
        body = OutputEventBody(msg, category)
        event = OutputEvent(body)
        return NetCommand(CMD_WRITE_TO_CONSOLE, 0, event, is_json=True)

    _STEP_REASONS = set(
        [
            CMD_STEP_INTO,
            CMD_STEP_INTO_MY_CODE,
            CMD_STEP_OVER,
            CMD_STEP_OVER_MY_CODE,
            CMD_STEP_RETURN,
            CMD_STEP_RETURN_MY_CODE,
            CMD_STEP_INTO_MY_CODE,
            CMD_STOP_ON_START,
            CMD_STEP_INTO_COROUTINE,
            CMD_SMART_STEP_INTO,
        ]
    )
    _EXCEPTION_REASONS = set(
        [
            CMD_STEP_CAUGHT_EXCEPTION,
            CMD_ADD_EXCEPTION_BREAK,
        ]
    )

    @overrides(NetCommandFactory.make_thread_suspend_single_notification)
    def make_thread_suspend_single_notification(self, py_db, thread_id, thread, stop_reason):
        exc_desc = None
        exc_name = None
        info = set_additional_thread_info(thread)

        preserve_focus_hint = False
        if stop_reason in self._STEP_REASONS:
            if info.pydev_original_step_cmd == CMD_STOP_ON_START:
                # Just to make sure that's not set as the original reason anymore.
                info.pydev_original_step_cmd = -1
                stop_reason = "entry"
            else:
                stop_reason = "step"
        elif stop_reason in self._EXCEPTION_REASONS:
            stop_reason = "exception"
        elif stop_reason == CMD_SET_BREAK:
            stop_reason = "breakpoint"
        elif stop_reason == CMD_SET_FUNCTION_BREAK:
            stop_reason = "function breakpoint"
        elif stop_reason == CMD_SET_NEXT_STATEMENT:
            stop_reason = "goto"
        else:
            stop_reason = "pause"
            preserve_focus_hint = True

        if stop_reason == "exception":
            exception_info_response = build_exception_info_response(
                py_db, thread_id, thread, -1, set_additional_thread_info, self._iter_visible_frames_info, max_frames=-1
            )
            exception_info_response

            exc_name = exception_info_response.body.exceptionId
            exc_desc = exception_info_response.body.description

        body = pydevd_schema.StoppedEventBody(
            reason=stop_reason,
            description=exc_desc,
            threadId=thread_id,
            text=exc_name,
            allThreadsStopped=True,
            preserveFocusHint=preserve_focus_hint,
        )
        event = pydevd_schema.StoppedEvent(body)
        return NetCommand(CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_thread_resume_single_notification)
    def make_thread_resume_single_notification(self, thread_id):
        body = ContinuedEventBody(threadId=thread_id, allThreadsContinued=True)
        event = pydevd_schema.ContinuedEvent(body)
        return NetCommand(CMD_THREAD_RESUME_SINGLE_NOTIFICATION, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_set_next_stmnt_status_message)
    def make_set_next_stmnt_status_message(self, seq, is_success, exception_msg):
        response = pydevd_schema.GotoResponse(
            request_seq=int(seq), success=is_success, command="goto", body={}, message=(None if is_success else exception_msg)
        )
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    @overrides(NetCommandFactory.make_send_curr_exception_trace_message)
    def make_send_curr_exception_trace_message(self, *args, **kwargs):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_send_curr_exception_trace_proceeded_message)
    def make_send_curr_exception_trace_proceeded_message(self, *args, **kwargs):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_send_breakpoint_exception_message)
    def make_send_breakpoint_exception_message(self, *args, **kwargs):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_process_created_message)
    def make_process_created_message(self, *args, **kwargs):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_process_about_to_be_replaced_message)
    def make_process_about_to_be_replaced_message(self):
        event = ExitedEvent(ExitedEventBody(-1, pydevdReason="processReplaced"))

        cmd = NetCommand(CMD_RETURN, 0, event, is_json=True)

        def after_send(socket):
            socket.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_NODELAY, 1)

        cmd.call_after_send(after_send)
        return cmd

    @overrides(NetCommandFactory.make_thread_suspend_message)
    def make_thread_suspend_message(self, py_db, thread_id, frames_list, stop_reason, message, trace_suspend_type, thread, info):
        from _pydevd_bundle.pydevd_comm_constants import CMD_THREAD_SUSPEND

        if py_db.multi_threads_single_notification:
            pydev_log.debug("Skipping per-thread thread suspend notification.")
            return NULL_NET_COMMAND  # Don't send per-thread, send a single one.
        pydev_log.debug("Sending per-thread thread suspend notification (stop_reason: %s)", stop_reason)

        exc_desc = None
        exc_name = None
        preserve_focus_hint = False
        if stop_reason in self._STEP_REASONS:
            if info.pydev_original_step_cmd == CMD_STOP_ON_START:
                # Just to make sure that's not set as the original reason anymore.
                info.pydev_original_step_cmd = -1
                stop_reason = "entry"
            else:
                stop_reason = "step"
        elif stop_reason in self._EXCEPTION_REASONS:
            stop_reason = "exception"
        elif stop_reason == CMD_SET_BREAK:
            stop_reason = "breakpoint"
        elif stop_reason == CMD_SET_FUNCTION_BREAK:
            stop_reason = "function breakpoint"
        elif stop_reason == CMD_SET_NEXT_STATEMENT:
            stop_reason = "goto"
        else:
            stop_reason = "pause"
            preserve_focus_hint = True

        if stop_reason == "exception":
            exception_info_response = build_exception_info_response(
                py_db, thread_id, thread, -1, set_additional_thread_info, self._iter_visible_frames_info, max_frames=-1
            )
            exception_info_response

            exc_name = exception_info_response.body.exceptionId
            exc_desc = exception_info_response.body.description

        body = pydevd_schema.StoppedEventBody(
            reason=stop_reason,
            description=exc_desc,
            threadId=thread_id,
            text=exc_name,
            allThreadsStopped=False,
            preserveFocusHint=preserve_focus_hint,
        )
        event = pydevd_schema.StoppedEvent(body)
        return NetCommand(CMD_THREAD_SUSPEND, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_thread_run_message)
    def make_thread_run_message(self, py_db, thread_id, reason):
        if py_db.multi_threads_single_notification:
            return NULL_NET_COMMAND  # Don't send per-thread, send a single one.
        body = ContinuedEventBody(threadId=thread_id, allThreadsContinued=False)
        event = pydevd_schema.ContinuedEvent(body)
        return NetCommand(CMD_THREAD_RUN, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_reloaded_code_message)
    def make_reloaded_code_message(self, *args, **kwargs):
        return NULL_NET_COMMAND  # Not a part of the debug adapter protocol

    @overrides(NetCommandFactory.make_input_requested_message)
    def make_input_requested_message(self, started):
        event = pydevd_schema.PydevdInputRequestedEvent(body={})
        return NetCommand(CMD_INPUT_REQUESTED, 0, event, is_json=True)

    @overrides(NetCommandFactory.make_skipped_step_in_because_of_filters)
    def make_skipped_step_in_because_of_filters(self, py_db, frame):
        msg = "Frame skipped from debugging during step-in."
        if py_db.get_use_libraries_filter():
            msg += (
                '\nNote: may have been skipped because of "justMyCode" option (default == true). '
                'Try setting "justMyCode": false in the debug configuration (e.g., launch.json).\n'
            )
        return self.make_warning_message(msg)

    @overrides(NetCommandFactory.make_evaluation_timeout_msg)
    def make_evaluation_timeout_msg(self, py_db, expression, curr_thread):
        msg = """Evaluating: %s did not finish after %.2f seconds.
This may mean a number of things:
- This evaluation is really slow and this is expected.
    In this case it's possible to silence this error by raising the timeout, setting the
    PYDEVD_WARN_EVALUATION_TIMEOUT environment variable to a bigger value.

- The evaluation may need other threads running while it's running:
    In this case, it's possible to set the PYDEVD_UNBLOCK_THREADS_TIMEOUT
    environment variable so that if after a given timeout an evaluation doesn't finish,
    other threads are unblocked or you can manually resume all threads.

    Alternatively, it's also possible to skip breaking on a particular thread by setting a
    `pydev_do_not_trace = True` attribute in the related threading.Thread instance
    (if some thread should always be running and no breakpoints are expected to be hit in it).

- The evaluation is deadlocked:
    In this case you may set the PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT
    environment variable to true so that a thread dump is shown along with this message and
    optionally, set the PYDEVD_INTERRUPT_THREAD_TIMEOUT to some value so that the debugger
    tries to interrupt the evaluation (if possible) when this happens.
""" % (expression, pydevd_constants.PYDEVD_WARN_EVALUATION_TIMEOUT)

        if pydevd_constants.PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT:
            stream = StringIO()
            pydevd_utils.dump_threads(stream, show_pydevd_threads=False)
            msg += "\n\n%s\n" % stream.getvalue()
        return self.make_warning_message(msg)

    @overrides(NetCommandFactory.make_exit_command)
    def make_exit_command(self, py_db):
        event = pydevd_schema.TerminatedEvent(pydevd_schema.TerminatedEventBody())
        return NetCommand(CMD_EXIT, 0, event, is_json=True)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\idle\PyParse.py ===
import re
import sys

# Reason last stmt is continued (or C_NONE if it's not).
C_NONE, C_BACKSLASH, C_STRING, C_BRACKET = list(range(4))

if 0:  # for throwaway debugging output

    def dump(*stuff):
        sys.__stdout__.write(" ".join(map(str, stuff)) + "\n")


# Find what looks like the start of a popular stmt.

_synchre = re.compile(
    r"""
    ^
    [ \t]*
    (?: if
    |   for
    |   while
    |   else
    |   def
    |   return
    |   assert
    |   break
    |   class
    |   continue
    |   elif
    |   try
    |   except
    |   raise
    |   import
    )
    \b
""",
    re.VERBOSE | re.MULTILINE,
).search

# Match blank line or non-indenting comment line.

_junkre = re.compile(
    r"""
    [ \t]*
    (?: \# \S .* )?
    \n
""",
    re.VERBOSE,
).match

# Match any flavor of string; the terminating quote is optional
# so that we're robust in the face of incomplete program text.

_match_stringre = re.compile(
    r"""
    \""" [^"\\]* (?:
                     (?: \\. | "(?!"") )
                     [^"\\]*
                 )*
    (?: \""" )?

|   " [^"\\\n]* (?: \\. [^"\\\n]* )* "?

|   ''' [^'\\]* (?:
                   (?: \\. | '(?!'') )
                   [^'\\]*
                )*
    (?: ''' )?

|   ' [^'\\\n]* (?: \\. [^'\\\n]* )* '?
""",
    re.VERBOSE | re.DOTALL,
).match

# Match a line that starts with something interesting;
# used to find the first item of a bracket structure.

_itemre = re.compile(
    r"""
    [ \t]*
    [^\s#\\]    # if we match, m.end()-1 is the interesting char
""",
    re.VERBOSE,
).match

# Match start of stmts that should be followed by a dedent.

_closere = re.compile(
    r"""
    \s*
    (?: return
    |   break
    |   continue
    |   raise
    |   pass
    )
    \b
""",
    re.VERBOSE,
).match

# Chew up non-special chars as quickly as possible.  If match is
# successful, m.end() less 1 is the index of the last boring char
# matched.  If match is unsuccessful, the string starts with an
# interesting char.

_chew_ordinaryre = re.compile(
    r"""
    [^[\](){}#'"\\]+
""",
    re.VERBOSE,
).match

# Build translation table to map uninteresting chars to "x", open
# brackets to "(", and close brackets to ")".

_tran = ["x"] * 256
for ch in "({[":
    _tran[ord(ch)] = "("
for ch in ")}]":
    _tran[ord(ch)] = ")"
for ch in "\"'\\\n#":
    _tran[ord(ch)] = ch
del ch


class Parser:
    def __init__(self, indentwidth, tabwidth):
        self.indentwidth = indentwidth
        self.tabwidth = tabwidth

    def set_str(self, str):
        assert len(str) == 0 or str[-1] == "\n", f"Oops - have str {str!r}"
        self.str = str
        self.study_level = 0

    # Return index of a good place to begin parsing, as close to the
    # end of the string as possible.  This will be the start of some
    # popular stmt like "if" or "def".  Return None if none found:
    # the caller should pass more prior context then, if possible, or
    # if not (the entire program text up until the point of interest
    # has already been tried) pass 0 to set_lo.
    #
    # This will be reliable iff given a reliable is_char_in_string
    # function, meaning that when it says "no", it's absolutely
    # guaranteed that the char is not in a string.
    #
    # Ack, hack: in the shell window this kills us, because there's
    # no way to tell the differences between output, >>> etc and
    # user input.  Indeed, IDLE's first output line makes the rest
    # look like it's in an unclosed paren!:
    # Python X.X.X (#0, Apr 13 1999, ...

    def find_good_parse_start(self, use_ps1, is_char_in_string=None):
        str, pos = self.str, None
        if use_ps1:
            # shell window
            ps1 = "\n" + sys.ps1
            i = str.rfind(ps1)
            if i >= 0:
                pos = i + len(ps1)
                # make it look like there's a newline instead
                # of ps1 at the start -- hacking here once avoids
                # repeated hackery later
                self.str = str[: pos - 1] + "\n" + str[pos:]
            return pos

        # File window -- real work.
        if not is_char_in_string:
            # no clue -- make the caller pass everything
            return None

        # Peek back from the end for a good place to start,
        # but don't try too often; pos will be left None, or
        # bumped to a legitimate synch point.
        limit = len(str)
        for tries in range(5):
            i = str.rfind(":\n", 0, limit)
            if i < 0:
                break
            i = str.rfind("\n", 0, i) + 1  # start of colon line
            m = _synchre(str, i, limit)
            if m and not is_char_in_string(m.start()):
                pos = m.start()
                break
            limit = i
        if pos is None:
            # Nothing looks like a block-opener, or stuff does
            # but is_char_in_string keeps returning true; most likely
            # we're in or near a giant string, the colorizer hasn't
            # caught up enough to be helpful, or there simply *aren't*
            # any interesting stmts.  In any of these cases we're
            # going to have to parse the whole thing to be sure, so
            # give it one last try from the start, but stop wasting
            # time here regardless of the outcome.
            m = _synchre(str)
            if m and not is_char_in_string(m.start()):
                pos = m.start()
            return pos

        # Peeking back worked; look forward until _synchre no longer
        # matches.
        i = pos + 1
        while 1:
            m = _synchre(str, i)
            if m:
                s, i = m.span()
                if not is_char_in_string(s):
                    pos = s
            else:
                break
        return pos

    # Throw away the start of the string.  Intended to be called with
    # find_good_parse_start's result.

    def set_lo(self, lo):
        assert lo == 0 or self.str[lo - 1] == "\n"
        if lo > 0:
            self.str = self.str[lo:]

    # As quickly as humanly possible <wink>, find the line numbers (0-
    # based) of the non-continuation lines.
    # Creates self.{goodlines, continuation}.

    def _study1(self):
        if self.study_level >= 1:
            return
        self.study_level = 1

        # Map all uninteresting characters to "x", all open brackets
        # to "(", all close brackets to ")", then collapse runs of
        # uninteresting characters.  This can cut the number of chars
        # by a factor of 10-40, and so greatly speed the following loop.
        str = self.str
        str = str.translate(_tran)
        str = str.replace("xxxxxxxx", "x")
        str = str.replace("xxxx", "x")
        str = str.replace("xx", "x")
        str = str.replace("xx", "x")
        str = str.replace("\nx", "\n")
        # note that replacing x\n with \n would be incorrect, because
        # x may be preceded by a backslash

        # March over the squashed version of the program, accumulating
        # the line numbers of non-continued stmts, and determining
        # whether & why the last stmt is a continuation.
        continuation = C_NONE
        level = lno = 0  # level is nesting level; lno is line number
        self.goodlines = goodlines = [0]
        push_good = goodlines.append
        i, n = 0, len(str)
        while i < n:
            ch = str[i]
            i += 1

            # cases are checked in decreasing order of frequency
            if ch == "x":
                continue

            if ch == "\n":
                lno += 1
                if level == 0:
                    push_good(lno)
                    # else we're in an unclosed bracket structure
                continue

            if ch == "(":
                level += 1
                continue

            if ch == ")":
                if level:
                    level -= 1
                    # else the program is invalid, but we can't complain
                continue

            if ch == '"' or ch == "'":
                # consume the string
                quote = ch
                if str[i - 1 : i + 2] == quote * 3:
                    quote *= 3
                w = len(quote) - 1
                i += w
                while i < n:
                    ch = str[i]
                    i += 1

                    if ch == "x":
                        continue

                    if str[i - 1 : i + w] == quote:
                        i += w
                        break

                    if ch == "\n":
                        lno += 1
                        if w == 0:
                            # unterminated single-quoted string
                            if level == 0:
                                push_good(lno)
                            break
                        continue

                    if ch == "\\":
                        assert i < n
                        if str[i] == "\n":
                            lno += 1
                        i += 1
                        continue

                    # else comment char or paren inside string

                else:
                    # didn't break out of the loop, so we're still
                    # inside a string
                    continuation = C_STRING
                continue  # with outer loop

            if ch == "#":
                # consume the comment
                i = str.find("\n", i)
                assert i >= 0
                continue

            assert ch == "\\"
            assert i < n
            if str[i] == "\n":
                lno += 1
                if i + 1 == n:
                    continuation = C_BACKSLASH
            i += 1

        # The last stmt may be continued for all 3 reasons.
        # String continuation takes precedence over bracket
        # continuation, which beats backslash continuation.
        if continuation != C_STRING and level > 0:
            continuation = C_BRACKET
        self.continuation = continuation

        # Push the final line number as a sentinel value, regardless of
        # whether it's continued.
        assert (continuation == C_NONE) == (goodlines[-1] == lno)
        if goodlines[-1] != lno:
            push_good(lno)

    def get_continuation_type(self):
        self._study1()
        return self.continuation

    # study1 was sufficient to determine the continuation status,
    # but doing more requires looking at every character.  study2
    # does this for the last interesting statement in the block.
    # Creates:
    #     self.stmt_start, stmt_end
    #         slice indices of last interesting stmt
    #     self.lastch
    #         last non-whitespace character before optional trailing
    #         comment
    #     self.lastopenbracketpos
    #         if continuation is C_BRACKET, index of last open bracket

    def _study2(self):
        if self.study_level >= 2:
            return
        self._study1()
        self.study_level = 2

        # Set p and q to slice indices of last interesting stmt.
        str, goodlines = self.str, self.goodlines
        i = len(goodlines) - 1
        p = len(str)  # index of newest line
        while i:
            assert p
            # p is the index of the stmt at line number goodlines[i].
            # Move p back to the stmt at line number goodlines[i-1].
            q = p
            for nothing in range(goodlines[i - 1], goodlines[i]):
                # tricky: sets p to 0 if no preceding newline
                p = str.rfind("\n", 0, p - 1) + 1
            # The stmt str[p:q] isn't a continuation, but may be blank
            # or a non-indenting comment line.
            if _junkre(str, p):
                i -= 1
            else:
                break
        if i == 0:
            # nothing but junk!
            assert p == 0
            q = p
        self.stmt_start, self.stmt_end = p, q

        # Analyze this stmt, to find the last open bracket (if any)
        # and last interesting character (if any).
        lastch = ""
        stack = []  # stack of open bracket indices
        push_stack = stack.append
        while p < q:
            # suck up all except ()[]{}'"#\\
            m = _chew_ordinaryre(str, p, q)
            if m:
                # we skipped at least one boring char
                newp = m.end()
                # back up over totally boring whitespace
                i = newp - 1  # index of last boring char
                while i >= p and str[i] in " \t\n":
                    i -= 1
                if i >= p:
                    lastch = str[i]
                p = newp
                if p >= q:
                    break

            ch = str[p]

            if ch in "([{":
                push_stack(p)
                lastch = ch
                p += 1
                continue

            if ch in ")]}":
                if stack:
                    del stack[-1]
                lastch = ch
                p += 1
                continue

            if ch == '"' or ch == "'":
                # consume string
                # Note that study1 did this with a Python loop, but
                # we use a regexp here; the reason is speed in both
                # cases; the string may be huge, but study1 pre-squashed
                # strings to a couple of characters per line.  study1
                # also needed to keep track of newlines, and we don't
                # have to.
                lastch = ch
                p = _match_stringre(str, p, q).end()
                continue

            if ch == "#":
                # consume comment and trailing newline
                p = str.find("\n", p, q) + 1
                assert p > 0
                continue

            assert ch == "\\"
            p += 1  # beyond backslash
            assert p < q
            if str[p] != "\n":
                # the program is invalid, but can't complain
                lastch = ch + str[p]
            p += 1  # beyond escaped char

        # end while p < q:

        self.lastch = lastch
        if stack:
            self.lastopenbracketpos = stack[-1]

    # Assuming continuation is C_BRACKET, return the number
    # of spaces the next line should be indented.

    def compute_bracket_indent(self):
        self._study2()
        assert self.continuation == C_BRACKET
        j = self.lastopenbracketpos
        str = self.str
        n = len(str)
        origi = i = str.rfind("\n", 0, j) + 1
        j += 1  # one beyond open bracket
        # find first list item; set i to start of its line
        while j < n:
            m = _itemre(str, j)
            if m:
                j = m.end() - 1  # index of first interesting char
                extra = 0
                break
            else:
                # this line is junk; advance to next line
                i = j = str.find("\n", j) + 1
        else:
            # nothing interesting follows the bracket;
            # reproduce the bracket line's indentation + a level
            j = i = origi
            while str[j] in " \t":
                j += 1
            extra = self.indentwidth
        return len(str[i:j].expandtabs(self.tabwidth)) + extra

    # Return number of physical lines in last stmt (whether or not
    # it's an interesting stmt!  this is intended to be called when
    # continuation is C_BACKSLASH).

    def get_num_lines_in_stmt(self):
        self._study1()
        goodlines = self.goodlines
        return goodlines[-1] - goodlines[-2]

    # Assuming continuation is C_BACKSLASH, return the number of spaces
    # the next line should be indented.  Also assuming the new line is
    # the first one following the initial line of the stmt.

    def compute_backslash_indent(self):
        self._study2()
        assert self.continuation == C_BACKSLASH
        str = self.str
        i = self.stmt_start
        while str[i] in " \t":
            i += 1
        startpos = i

        # See whether the initial line starts an assignment stmt; i.e.,
        # look for an = operator
        endpos = str.find("\n", startpos) + 1
        found = level = 0
        while i < endpos:
            ch = str[i]
            if ch in "([{":
                level += 1
                i += 1
            elif ch in ")]}":
                if level:
                    level -= 1
                i += 1
            elif ch == '"' or ch == "'":
                i = _match_stringre(str, i, endpos).end()
            elif ch == "#":
                break
            elif (
                level == 0
                and ch == "="
                and (i == 0 or str[i - 1] not in "=<>!")
                and str[i + 1] != "="
            ):
                found = 1
                break
            else:
                i += 1

        if found:
            # found a legit =, but it may be the last interesting
            # thing on the line
            i += 1  # move beyond the =
            found = re.match(r"\s*\\", str[i:endpos]) is None

        if not found:
            # oh well ... settle for moving beyond the first chunk
            # of non-whitespace chars
            i = startpos
            while str[i] not in " \t\n":
                i += 1

        return len(str[self.stmt_start : i].expandtabs(self.tabwidth)) + 1

    # Return the leading whitespace on the initial line of the last
    # interesting stmt.

    def get_base_indent_string(self):
        self._study2()
        i, n = self.stmt_start, self.stmt_end
        j = i
        str = self.str
        while j < n and str[j] in " \t":
            j += 1
        return str[i:j]

    # Did the last interesting stmt open a block?

    def is_block_opener(self):
        self._study2()
        return self.lastch == ":"

    # Did the last interesting stmt close a block?

    def is_block_closer(self):
        self._study2()
        return _closere(self.str, self.stmt_start) is not None

    # index of last open bracket ({[, or None if none
    lastopenbracketpos = None

    def get_last_open_bracket_pos(self):
        self._study2()
        return self.lastopenbracketpos

# === NexusCore/openenv\Lib\site-packages\win32com\test\testvb.py ===
# Test code for a VB Program.
#
# This requires the PythonCOM VB Test Harness.
#

import traceback
from collections.abc import Callable

import pythoncom
import win32com.client
import win32com.client.dynamic
import win32com.client.gencache
import winerror
from win32com.server.util import wrap
from win32com.test import util

# for debugging
useDispatcher = None
# import win32com.server.dispatcher
# useDispatcher = win32com.server.dispatcher.DefaultDebugDispatcher


# Set up a COM object that VB will do some callbacks on.  This is used
# to test byref params for gateway IDispatch.
class TestObject:
    _public_methods_ = [
        "CallbackVoidOneByRef",
        "CallbackResultOneByRef",
        "CallbackVoidTwoByRef",
        "CallbackString",
        "CallbackResultOneByRefButReturnNone",
        "CallbackVoidOneByRefButReturnNone",
        "CallbackArrayResult",
        "CallbackArrayResultOneArrayByRef",
        "CallbackArrayResultWrongSize",
    ]

    def CallbackVoidOneByRef(self, intVal):
        return intVal + 1

    def CallbackResultOneByRef(self, intVal):
        return intVal, intVal + 1

    def CallbackVoidTwoByRef(self, int1, int2):
        return int1 + int2, int1 - int2

    def CallbackString(self, strVal):
        return 0, strVal + " has visited Python"

    def CallbackArrayResult(self, arrayVal):
        ret = []
        for i in arrayVal:
            ret.append(i + 1)
        # returning as a list forces it be processed as a single result
        # (rather than a tuple, where it may be interpreted as
        # multiple results for byref unpacking)
        return ret

    def CallbackArrayResultWrongSize(self, arrayVal):
        return list(arrayVal[:-1])

    def CallbackArrayResultOneArrayByRef(self, arrayVal):
        ret = []
        for i in arrayVal:
            ret.append(i + 1)
        # See above for list processing.
        return list(arrayVal), ret

    def CallbackResultOneByRefButReturnNone(self, intVal):
        return

    def CallbackVoidOneByRefButReturnNone(self, intVal):
        return


def TestVB(vbtest, bUseGenerated):
    vbtest.LongProperty = -1
    assert vbtest.LongProperty == -1, "Could not set the long property correctly."
    vbtest.IntProperty = 10
    assert vbtest.IntProperty == 10, "Could not set the integer property correctly."
    vbtest.VariantProperty = 10
    assert (
        vbtest.VariantProperty == 10
    ), "Could not set the variant integer property correctly."
    vbtest.VariantProperty = memoryview(b"raw\0data")
    assert vbtest.VariantProperty == memoryview(
        b"raw\0data"
    ), "Could not set the variant buffer property correctly."
    vbtest.StringProperty = "Hello from Python"
    assert (
        vbtest.StringProperty == "Hello from Python"
    ), "Could not set the string property correctly."
    vbtest.VariantProperty = "Hello from Python"
    assert (
        vbtest.VariantProperty == "Hello from Python"
    ), "Could not set the variant string property correctly."
    vbtest.VariantProperty = (1.0, 2.0, 3.0)
    assert (
        vbtest.VariantProperty
        == (
            1.0,
            2.0,
            3.0,
        )
    ), f"Could not set the variant property to an array of floats correctly - '{vbtest.VariantProperty}'."

    TestArrays(vbtest, bUseGenerated)
    TestStructs(vbtest)
    TestCollections(vbtest)

    assert vbtest.TakeByValObject(vbtest) == vbtest

    # Python doesn't support PUTREF properties without a typeref
    # (although we could)
    if bUseGenerated:
        ob = vbtest.TakeByRefObject(vbtest)
        assert ob[0] == vbtest and ob[1] == vbtest

        # A property that only has PUTREF defined.
        vbtest.VariantPutref = vbtest
        assert (
            vbtest.VariantPutref._oleobj_ == vbtest._oleobj_
        ), "Could not set the VariantPutref property correctly."
        # Can't test further types for this VariantPutref, as only
        # COM objects can be stored ByRef.

        # A "set" type property - only works for generated.
        # VB recognizes a collection via a few "private" interfaces that we
        # could later build support in for.
        # vbtest.CollectionProperty = NewCollection((1, 2, "3", "Four"))
        # assert vbtest.CollectionProperty == (
        #     1, 2, "3", "Four",
        # ), f"Could not set the Collection property correctly - got back {vbtest.CollectionProperty}"

        # These are sub's that have a single byref param
        # Result should be just the byref.
        assert vbtest.IncrementIntegerParam(1) == 2, "Could not pass an integer byref"

        # Sigh - we can't have *both* "ommited byref" and optional args
        # We really have to opt that args nominated as optional work as optional
        # rather than simply all byrefs working as optional.
        # assert vbtest.IncrementIntegerParam() == 1, "Could not pass an omitted integer byref"

        assert (
            vbtest.IncrementVariantParam(1) == 2
        ), f"Could not pass an int VARIANT byref: {vbtest.IncrementVariantParam(1)}"
        assert (
            vbtest.IncrementVariantParam(1.5) == 2.5
        ), "Could not pass a float VARIANT byref"

        # Can't test IncrementVariantParam with the param omitted as it
        # it not declared in the VB code as "Optional"
        callback_ob = wrap(TestObject(), useDispatcher=useDispatcher)
        vbtest.DoSomeCallbacks(callback_ob)

    ret = vbtest.PassIntByVal(1)
    assert ret == 2, f"Could not increment the integer - {ret}"

    TestVBInterface(vbtest)
    # Python doesn't support byrefs without some sort of generated support.
    if bUseGenerated:
        # This is a VB function that takes a single byref
        # Hence 2 return values - function and byref.
        ret = vbtest.PassIntByRef(1)
        assert ret == (1, 2), f"Could not increment the integer - {ret}"
        # Check you can leave a byref arg blank.

    # see above
    # ret = vbtest.PassIntByRef()
    # assert ret == (0, 1), f"Could not increment the integer with default arg - {ret}"


def _DoTestCollection(vbtest, col_name, expected):
    # It sucks that some objects allow "Count()", but others "Count"
    def _getcount(ob):
        r = getattr(ob, "Count")
        if isinstance(r, Callable):
            return r()
        return r

    c = getattr(vbtest, col_name)
    check = []
    for item in c:
        check.append(item)
    assert check == list(
        expected
    ), f"Collection {col_name} didn't have {expected!r} (had {check!r})"
    # Just looping over the collection again works (ie, is restartable)
    check = []
    for item in c:
        check.append(item)
    assert check == list(
        expected
    ), f"Collection 2nd time around {col_name} didn't have {expected!r} (had {check!r})"

    # Check we can get it via iter()
    i = iter(getattr(vbtest, col_name))
    check = []
    for item in i:
        check.append(item)
    assert (
        check == list(expected)
    ), f"Collection iterator {col_name} didn't have {expected!r} 2nd time around (had {check!r})"
    # but an iterator is not restartable
    check = []
    for item in i:
        check.append(item)
    assert (
        check == []
    ), "2nd time around Collection iterator {col_name} wasn't empty (had {check!r})"
    # Check len()==Count()
    c = getattr(vbtest, col_name)
    assert len(c) == _getcount(
        c
    ), f"Collection {col_name} __len__({len(c)!r}) wasn't==Count({_getcount(c)!r})"
    # Check we can do it with zero based indexing.
    c = getattr(vbtest, col_name)
    check = []
    for i in range(_getcount(c)):
        check.append(c[i])
    assert check == list(
        expected
    ), f"Collection {col_name} didn't have {expected!r} (had {check!r})"

    # Check we can do it with our old "Skip/Next" methods.
    c = getattr(vbtest, col_name)._NewEnum()
    check = []
    while 1:
        n = c.Next()
        if not n:
            break
        check.append(n[0])
    assert check == list(
        expected
    ), f"Collection {col_name} didn't have {expected!r} (had {check!r})"


def TestCollections(vbtest):
    _DoTestCollection(vbtest, "CollectionProperty", [1, "Two", "3"])
    # zero based indexing works for simple VB collections.
    assert (
        vbtest.CollectionProperty[0] == 1
    ), "The CollectionProperty[0] element was not the default value"

    _DoTestCollection(vbtest, "EnumerableCollectionProperty", [])
    vbtest.EnumerableCollectionProperty.Add(1)
    vbtest.EnumerableCollectionProperty.Add("Two")
    vbtest.EnumerableCollectionProperty.Add("3")
    _DoTestCollection(vbtest, "EnumerableCollectionProperty", [1, "Two", "3"])


def _DoTestArray(vbtest, data, expected_exception=None):
    try:
        vbtest.ArrayProperty = data
        assert expected_exception is None, f"Expected '{expected_exception}'"
    except expected_exception:
        return
    got = vbtest.ArrayProperty
    assert (
        got == data
    ), f"Could not set the array data correctly - got {got!r}, expected {data!r}"


def TestArrays(vbtest, bUseGenerated):
    # Try and use a safe array (note that the VB code has this declared as a VARIANT
    # and I can't work out how to force it to use native arrays!
    # (NOTE Python will convert incoming arrays to tuples, so we pass a tuple, even tho
    # a list works fine - just makes it easier for us to compare the result!
    # Empty array
    _DoTestArray(vbtest, ())
    # Empty child array
    _DoTestArray(vbtest, ((), ()))
    # ints
    _DoTestArray(vbtest, tuple(range(1, 100)))
    # Floats
    _DoTestArray(vbtest, (1.0, 2.0, 3.0))
    # Strings.
    _DoTestArray(vbtest, tuple("Hello from Python".split()))
    # Date and Time?
    # COM objects.
    _DoTestArray(vbtest, (vbtest, vbtest))
    # Mixed
    _DoTestArray(vbtest, (1, 2.0, "3"))
    # Array alements containing other arrays
    _DoTestArray(vbtest, (1, (vbtest, vbtest), ("3", "4")))
    # Multi-dimensional
    _DoTestArray(vbtest, (((1, 2, 3), (4, 5, 6))))
    _DoTestArray(vbtest, (((vbtest, vbtest, vbtest), (vbtest, vbtest, vbtest))))
    # Another dimension!
    arrayData = (((1, 2), (3, 4), (5, 6)), ((7, 8), (9, 10), (11, 12)))
    arrayData = (
        ((vbtest, vbtest), (vbtest, vbtest), (vbtest, vbtest)),
        ((vbtest, vbtest), (vbtest, vbtest), (vbtest, vbtest)),
    )
    _DoTestArray(vbtest, arrayData)

    # Check that when a '__getitem__ that fails' object is the first item
    # in the structure, we don't mistake it for a sequence.
    _DoTestArray(vbtest, (vbtest, 2.0, "3"))
    _DoTestArray(vbtest, (1, 2.0, vbtest))

    # Pass arbitrarily sized arrays - these used to fail, but thanks to
    # Stefan Schukat, they now work!
    expected_exception = None
    arrayData = (((1, 2, 1), (3, 4), (5, 6)), ((7, 8), (9, 10), (11, 12)))
    _DoTestArray(vbtest, arrayData, expected_exception)
    arrayData = (((vbtest, vbtest),), ((vbtest,),))
    _DoTestArray(vbtest, arrayData, expected_exception)
    # Pass bad data - last item wrong size
    arrayData = (((1, 2), (3, 4), (5, 6, 8)), ((7, 8), (9, 10), (11, 12)))
    _DoTestArray(vbtest, arrayData, expected_exception)

    # byref safearray results with incorrect size.
    callback_ob = wrap(TestObject(), useDispatcher=useDispatcher)
    print("** Expecting a 'ValueError' exception to be printed next:")
    try:
        vbtest.DoCallbackSafeArraySizeFail(callback_ob)
    except pythoncom.com_error as exc:
        assert (
            exc.excepinfo[1] == "Python COM Server Internal Error"
        ), f"Didn't get the correct exception - '{exc}'"

    if bUseGenerated:
        # This one is a bit strange!  The array param is "ByRef", as VB insists.
        # The function itself also _returns_ the arram param.
        # Therefore, Python sees _2_ result values - one for the result,
        # and one for the byref.
        testData = "Mark was here".split()
        resultData, byRefParam = vbtest.PassSAFEARRAY(testData)
        assert testData == list(
            resultData
        ), f"The safe array data was not what we expected - got {resultData}"
        assert testData == list(
            byRefParam
        ), f"The safe array data was not what we expected - got {byRefParam}"
        testData = [1.0, 2.0, 3.0]
        resultData, byRefParam = vbtest.PassSAFEARRAYVariant(testData)
        assert testData == list(byRefParam)
        assert testData == list(resultData)
        testData = ["hi", "from", "Python"]
        resultData, byRefParam = vbtest.PassSAFEARRAYVariant(testData)
        assert testData == list(byRefParam), "Expected '{}', got '{}'".format(
            testData,
            list(byRefParam),
        )
        assert testData == list(resultData), "Expected '{}', got '{}'".format(
            testData,
            list(resultData),
        )
        # This time, we just pass Unicode, so the result should compare equal
        testData = [1, 2.0, "3"]
        resultData, byRefParam = vbtest.PassSAFEARRAYVariant(testData)
        assert testData == list(byRefParam)
        assert testData == list(resultData)
    print("Array tests passed")


def TestStructs(vbtest):
    try:
        vbtest.IntProperty = "One"
        raise AssertionError("Should have failed by now")
    except pythoncom.com_error as exc:
        assert (
            exc.hresult == winerror.DISP_E_TYPEMISMATCH
        ), "Expected DISP_E_TYPEMISMATCH"

    s = vbtest.StructProperty
    assert (
        s.int_val == 99 and str(s.str_val) == "hello"
    ), "The struct value was not correct"
    s.str_val = "Hi from Python"
    s.int_val = 11
    assert (
        s.int_val == 11 and str(s.str_val) == "Hi from Python"
    ), "The struct value didn't persist!"
    assert (
        s.sub_val.int_val == 66 and str(s.sub_val.str_val) == "sub hello"
    ), "The sub-struct value was not correct"
    sub = s.sub_val
    sub.int_val = 22
    assert sub.int_val == 22, (
        f"The sub-struct value didn't persist!",
        str(sub.int_val),
    )
    assert s.sub_val.int_val == 22, (
        "The sub-struct value (re-fetched) didn't persist!",
        str(s.sub_val.int_val),
    )
    assert (
        s.sub_val.array_val[0].int_val == 0
        and str(s.sub_val.array_val[0].str_val) == "zero"
    ), ("The array element wasn't correct", str(s.sub_val.array_val[0].int_val))
    s.sub_val.array_val[0].int_val = 99
    s.sub_val.array_val[1].int_val = 66
    assert (
        s.sub_val.array_val[0].int_val == 99 and s.sub_val.array_val[1].int_val == 66
    ), (
        "The array elements didn't persist.",
        str(s.sub_val.array_val[0].int_val),
        str(s.sub_val.array_val[1].int_val),
    )
    # Now pass the struct back to VB
    vbtest.StructProperty = s
    # And get it back again
    s = vbtest.StructProperty
    assert (
        s.int_val == 11 and str(s.str_val) == "Hi from Python"
    ), "After sending to VB, the struct value didn't persist!"
    assert (
        s.sub_val.array_val[0].int_val == 99
    ), "After sending to VB, the struct array value didn't persist!"

    # Now do some object equality tests.
    assert s == s
    assert s is not None
    try:
        s < None
        raise AssertionError("Expected type error")
    except TypeError:
        pass
    try:
        None < s
        raise AssertionError("Expected type error")
    except TypeError:
        pass
    assert s != s.sub_val
    import copy

    s2 = copy.copy(s)
    assert s is not s2
    assert s == s2
    s2.int_val = 123
    assert s != s2
    # Make sure everything works with functions
    s2 = vbtest.GetStructFunc()
    assert s == s2
    vbtest.SetStructSub(s2)

    # Create a new structure, and set its elements.
    s = win32com.client.Record("VBStruct", vbtest)
    assert s.int_val == 0, "new struct inst initialized correctly!"
    s.int_val = -1
    vbtest.SetStructSub(s)
    assert (
        vbtest.GetStructFunc().int_val == -1
    ), "new struct didn't make the round trip!"
    # Finally, test stand-alone structure arrays.
    s_array = vbtest.StructArrayProperty
    assert s_array is None, "Expected None from the uninitialized VB array"
    vbtest.MakeStructArrayProperty(3)
    s_array = vbtest.StructArrayProperty
    assert len(s_array) == 3
    for i in range(len(s_array)):
        assert s_array[i].int_val == i
        assert s_array[i].sub_val.int_val == i
        assert s_array[i].sub_val.array_val[0].int_val == i
        assert s_array[i].sub_val.array_val[1].int_val == i + 1
        assert s_array[i].sub_val.array_val[2].int_val == i + 2

    # Some error type checks.
    try:
        s.bad_attribute
        raise AssertionError("Could get a bad attribute")
    except AttributeError:
        pass
    m = s.__members__
    assert (
        m[0] == "int_val"
        and m[1] == "str_val"
        and m[2] == "ob_val"
        and m[3] == "sub_val"
    ), m

    # Test attribute errors.
    try:
        s.foo
        raise AssertionError("Expected attribute error")
    except AttributeError as exc:
        assert "foo" in str(exc), exc

    # test repr - it uses repr() of the sub-objects, so check it matches.
    expected = (
        "com_struct(int_val={!r}, str_val={!r}, ob_val={!r}, sub_val={!r})".format(
            s.int_val,
            s.str_val,
            s.ob_val,
            s.sub_val,
        )
    )
    repr_s = repr(s)
    if repr_s != expected:
        print("Expected repr:", expected)
        print("Actual repr  :", repr_s)
        raise AssertionError("repr() of record object failed")

    print("Struct/Record tests passed")


def TestVBInterface(ob):
    t = ob.GetInterfaceTester(2)
    assert t.getn() == 2, "Initial value wrong"
    t.setn(3)
    assert t.getn() == 3, "New value wrong"


def TestObjectSemantics(ob):
    # a convenient place to test some of our equality semantics
    assert ob == ob._oleobj_
    assert not ob != ob._oleobj_
    # same test again, but lhs and rhs reversed.
    assert ob._oleobj_ == ob
    assert not ob._oleobj_ != ob
    # same tests but against different pointers.  COM identity rules should
    # still ensure all works
    assert ob._oleobj_ == ob._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
    assert not ob._oleobj_ != ob._oleobj_.QueryInterface(pythoncom.IID_IUnknown)

    assert ob._oleobj_ is not None
    assert None != ob._oleobj_
    assert ob is not None
    assert None != ob
    try:
        ob < None
        raise AssertionError("Expected type error")
    except TypeError:
        pass
    try:
        None < ob
        raise AssertionError("Expected type error")
    except TypeError:
        pass

    assert ob._oleobj_.QueryInterface(pythoncom.IID_IUnknown) == ob._oleobj_
    assert not ob._oleobj_.QueryInterface(pythoncom.IID_IUnknown) != ob._oleobj_

    assert ob._oleobj_ == ob._oleobj_.QueryInterface(pythoncom.IID_IDispatch)
    assert not ob._oleobj_ != ob._oleobj_.QueryInterface(pythoncom.IID_IDispatch)

    assert ob._oleobj_.QueryInterface(pythoncom.IID_IDispatch) == ob._oleobj_
    assert not ob._oleobj_.QueryInterface(pythoncom.IID_IDispatch) != ob._oleobj_

    print("Object semantic tests passed")


def DoTestAll():
    o = win32com.client.Dispatch("PyCOMVBTest.Tester")
    TestObjectSemantics(o)
    TestVB(o, 1)

    o = win32com.client.dynamic.DumbDispatch("PyCOMVBTest.Tester")
    TestObjectSemantics(o)
    TestVB(o, 0)


def TestAll():
    # Import the type library for the test module.  Let the 'invalid clsid'
    # exception filter up, where the test runner will treat it as 'skipped'
    win32com.client.gencache.EnsureDispatch("PyCOMVBTest.Tester")

    if not __debug__:
        raise RuntimeError("This must be run in debug mode - we use assert!")
    try:
        DoTestAll()
        print("All tests appear to have worked!")
    except:
        # ?????
        print("TestAll() failed!!")
        traceback.print_exc()
        raise


# Make this test run under our test suite to leak tests etc work
def suite():
    import unittest

    test = util.CapturingFunctionTestCase(TestAll, description="VB tests")
    suite = unittest.TestSuite()
    suite.addTest(test)
    return suite


if __name__ == "__main__":
    util.testmain()

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\gateways.py ===
# Classes which describe interfaces.

import pythoncom
import win32com.server.connect
import winerror
from win32com.axdebug import axdebug
from win32com.axdebug.util import RaiseNotImpl, _wrap
from win32com.server.exception import COMException
from win32com.server.util import ListEnumeratorGateway


class EnumDebugCodeContexts(ListEnumeratorGateway):
    """A class to expose a Python sequence as an EnumDebugCodeContexts

    Create an instance of this class passing a sequence (list, tuple, or
    any sequence protocol supporting object) and it will automatically
    support the EnumDebugCodeContexts interface for the object.

    """

    _com_interfaces_ = [axdebug.IID_IEnumDebugCodeContexts]


class EnumDebugStackFrames(ListEnumeratorGateway):
    """A class to expose a Python sequence as an EnumDebugStackFrames

    Create an instance of this class passing a sequence (list, tuple, or
    any sequence protocol supporting object) and it will automatically
    support the EnumDebugStackFrames interface for the object.

    """

    _com_interfaces_ = [axdebug.IID_IEnumDebugStackFrames]


class EnumDebugApplicationNodes(ListEnumeratorGateway):
    """A class to expose a Python sequence as an EnumDebugStackFrames

    Create an instance of this class passing a sequence (list, tuple, or
    any sequence protocol supporting object) and it will automatically
    support the EnumDebugApplicationNodes interface for the object.

    """

    _com_interfaces_ = [axdebug.IID_IEnumDebugApplicationNodes]


class EnumRemoteDebugApplications(ListEnumeratorGateway):
    _com_interfaces_ = [axdebug.IID_IEnumRemoteDebugApplications]


class EnumRemoteDebugApplicationThreads(ListEnumeratorGateway):
    _com_interfaces_ = [axdebug.IID_IEnumRemoteDebugApplicationThreads]


class DebugDocumentInfo:
    _public_methods_ = ["GetName", "GetDocumentClassId"]
    _com_interfaces_ = [axdebug.IID_IDebugDocumentInfo]

    def __init__(self):
        pass

    def GetName(self, dnt):
        """Get the one of the name of the document
        dnt -- int DOCUMENTNAMETYPE
        """
        RaiseNotImpl("GetName")

    def GetDocumentClassId(self):
        """
        Result must be an IID object (or string representing one).
        """
        RaiseNotImpl("GetDocumentClassId")


class DebugDocumentProvider(DebugDocumentInfo):
    _public_methods_ = DebugDocumentInfo._public_methods_ + ["GetDocument"]
    _com_interfaces_ = DebugDocumentInfo._com_interfaces_ + [
        axdebug.IID_IDebugDocumentProvider
    ]

    def GetDocument(self):
        RaiseNotImpl("GetDocument")


class DebugApplicationNode(DebugDocumentProvider):
    """Provides the functionality of IDebugDocumentProvider, plus a context within a project tree."""

    _public_methods_ = (
        """EnumChildren GetParent SetDocumentProvider
                    Close Attach Detach""".split()
        + DebugDocumentProvider._public_methods_
    )
    _com_interfaces_ = [
        axdebug.IID_IDebugDocumentProvider
    ] + DebugDocumentProvider._com_interfaces_

    def __init__(self):
        DebugDocumentProvider.__init__(self)

    def EnumChildren(self):
        # Result is type PyIEnumDebugApplicationNodes
        RaiseNotImpl("EnumChildren")

    def GetParent(self):
        # result is type PyIDebugApplicationNode
        RaiseNotImpl("GetParent")

    def SetDocumentProvider(self, pddp):  # PyIDebugDocumentProvider pddp
        # void result.
        RaiseNotImpl("SetDocumentProvider")

    def Close(self):
        # void result.
        RaiseNotImpl("Close")

    def Attach(self, parent):  # PyIDebugApplicationNode
        # void result.
        RaiseNotImpl("Attach")

    def Detach(self):
        # void result.
        RaiseNotImpl("Detach")


class DebugApplicationNodeEvents:
    """Event interface for DebugApplicationNode object."""

    _public_methods_ = "onAddChild onRemoveChild onDetach".split()
    _com_interfaces_ = [axdebug.IID_IDebugApplicationNodeEvents]

    def __init__(self):
        pass

    def onAddChild(self, child):  # PyIDebugApplicationNode
        # void result.
        RaiseNotImpl("onAddChild")

    def onRemoveChild(self, child):  # PyIDebugApplicationNode
        # void result.
        RaiseNotImpl("onRemoveChild")

    def onDetach(self):
        # void result.
        RaiseNotImpl("onDetach")

    def onAttach(self, parent):  # PyIDebugApplicationNode
        # void result.
        RaiseNotImpl("onAttach")


class DebugDocument(DebugDocumentInfo):
    """The base interface to all debug documents."""

    _public_methods_ = DebugDocumentInfo._public_methods_
    _com_interfaces_ = [axdebug.IID_IDebugDocument] + DebugDocumentInfo._com_interfaces_


class DebugDocumentText(DebugDocument):
    """The interface to a text only debug document."""

    _com_interfaces_ = [axdebug.IID_IDebugDocumentText] + DebugDocument._com_interfaces_
    _public_methods_ = [
        "GetDocumentAttributes",
        "GetSize",
        "GetPositionOfLine",
        "GetLineOfPosition",
        "GetText",
        "GetPositionOfContext",
        "GetContextOfPosition",
    ] + DebugDocument._public_methods_

    def __init__(self):
        pass

    # IDebugDocumentText
    def GetDocumentAttributes(self):
        # Result is int (TEXT_DOC_ATTR)
        RaiseNotImpl("GetDocumentAttributes")

    def GetSize(self):
        # Result is (numLines, numChars)
        RaiseNotImpl("GetSize")

    def GetPositionOfLine(self, cLineNumber):
        # Result is int char position
        RaiseNotImpl("GetPositionOfLine")

    def GetLineOfPosition(self, charPos):
        # Result is int, int (lineNo, offset)
        RaiseNotImpl("GetLineOfPosition")

    def GetText(self, charPos, maxChars, wantAttr):
        """Params
        charPos -- integer
        maxChars -- integer
        wantAttr -- Should the function compute attributes.

        Return value must be (string, attribtues).  attributes may be
        None if(not wantAttr)
        """
        RaiseNotImpl("GetText")

    def GetPositionOfContext(self, debugDocumentContext):
        """Params
        debugDocumentContext -- a PyIDebugDocumentContext object.

        Return value must be (charPos, numChars)
        """
        RaiseNotImpl("GetPositionOfContext")

    def GetContextOfPosition(self, charPos, maxChars):
        """Params are integers.
        Return value must be PyIDebugDocumentContext object
        """
        print(self)
        RaiseNotImpl("GetContextOfPosition")


class DebugDocumentTextExternalAuthor:
    """Allow external editors to edit file-based debugger documents, and to notify the document when the source file has been changed."""

    _public_methods_ = ["GetPathName", "GetFileName", "NotifyChanged"]
    _com_interfaces_ = [axdebug.IID_IDebugDocumentTextExternalAuthor]

    def __init__(self):
        pass

    def GetPathName(self):
        """Return the full path (including file name) to the document's source file.

        Result must be (filename, fIsOriginal), where
        - if fIsOriginalPath is TRUE if the path refers to the original file for the document.
        - if fIsOriginalPath is FALSE if the path refers to a newly created temporary file.

        raise COMException(winerror.E_FAIL) if no source file can be created/determined.
        """
        RaiseNotImpl("GetPathName")

    def GetFileName(self):
        """Return just the name of the document, with no path information.  (Used for "Save As...")

        Result is a string
        """
        RaiseNotImpl("GetFileName")

    def NotifyChanged(self):
        """Notify the host that the document's source file has been saved and
        that its contents should be refreshed.
        """
        RaiseNotImpl("NotifyChanged")


class DebugDocumentTextEvents:
    _public_methods_ = """onDestroy onInsertText onRemoveText
              onReplaceText onUpdateTextAttributes
              onUpdateDocumentAttributes""".split()
    _com_interfaces_ = [axdebug.IID_IDebugDocumentTextEvents]

    def __init__(self):
        pass

    def onDestroy(self):
        # Result is void.
        RaiseNotImpl("onDestroy")

    def onInsertText(self, cCharacterPosition, cNumToInsert):
        # Result is void.
        RaiseNotImpl("onInsertText")

    def onRemoveText(self, cCharacterPosition, cNumToRemove):
        # Result is void.
        RaiseNotImpl("onRemoveText")

    def onReplaceText(self, cCharacterPosition, cNumToReplace):
        # Result is void.
        RaiseNotImpl("onReplaceText")

    def onUpdateTextAttributes(self, cCharacterPosition, cNumToUpdate):
        # Result is void.
        RaiseNotImpl("onUpdateTextAttributes")

    def onUpdateDocumentAttributes(self, textdocattr):  # TEXT_DOC_ATTR
        # Result is void.
        RaiseNotImpl("onUpdateDocumentAttributes")


class DebugDocumentContext:
    _public_methods_ = ["GetDocument", "EnumCodeContexts"]
    _com_interfaces_ = [axdebug.IID_IDebugDocumentContext]

    def __init__(self):
        pass

    def GetDocument(self):
        """Return value must be a PyIDebugDocument object"""
        RaiseNotImpl("GetDocument")

    def EnumCodeContexts(self):
        """Return value must be a PyIEnumDebugCodeContexts object"""
        RaiseNotImpl("EnumCodeContexts")


class DebugCodeContext:
    _public_methods_ = ["GetDocumentContext", "SetBreakPoint"]
    _com_interfaces_ = [axdebug.IID_IDebugCodeContext]

    def __init__(self):
        pass

    def GetDocumentContext(self):
        """Return value must be a PyIDebugDocumentContext object"""
        RaiseNotImpl("GetDocumentContext")

    def SetBreakPoint(self, bps):
        """bps -- an integer with flags."""
        RaiseNotImpl("SetBreakPoint")


class DebugStackFrame:
    """Abstraction representing a logical stack frame on the stack of a thread."""

    _public_methods_ = [
        "GetCodeContext",
        "GetDescriptionString",
        "GetLanguageString",
        "GetThread",
        "GetDebugProperty",
    ]
    _com_interfaces_ = [axdebug.IID_IDebugStackFrame]

    def __init__(self):
        pass

    def GetCodeContext(self):
        """Returns the current code context associated with the stack frame.

        Return value must be a IDebugCodeContext object
        """
        RaiseNotImpl("GetCodeContext")

    def GetDescriptionString(self, fLong):
        """Returns a textual description of the stack frame.

        fLong -- A flag indicating if the long name is requested.
        """
        RaiseNotImpl("GetDescriptionString")

    def GetLanguageString(self):
        """Returns a short or long textual description of the language.

        fLong -- A flag indicating if the long name is requested.
        """
        RaiseNotImpl("GetLanguageString")

    def GetThread(self):
        """Returns the thread associated with this stack frame.

        Result must be a IDebugApplicationThread
        """
        RaiseNotImpl("GetThread")

    def GetDebugProperty(self):
        RaiseNotImpl("GetDebugProperty")


class DebugDocumentHost:
    """The interface from the IDebugDocumentHelper back to
    the smart host or language engine.  This interface
    exposes host specific functionality such as syntax coloring.
    """

    _public_methods_ = [
        "GetDeferredText",
        "GetScriptTextAttributes",
        "OnCreateDocumentContext",
        "GetPathName",
        "GetFileName",
        "NotifyChanged",
    ]
    _com_interfaces_ = [axdebug.IID_IDebugDocumentHost]

    def __init__(self):
        pass

    def GetDeferredText(self, dwTextStartCookie, maxChars, bWantAttr):
        RaiseNotImpl("GetDeferredText")

    def GetScriptTextAttributes(self, codeText, delimterText, flags):
        # Result must be an attribute sequence of same "length" as the code.
        RaiseNotImpl("GetScriptTextAttributes")

    def OnCreateDocumentContext(self):
        # Result must be a PyIUnknown
        RaiseNotImpl("OnCreateDocumentContext")

    def GetPathName(self):
        # Result must be (string, int) where the int is a BOOL
        # - TRUE if the path refers to the original file for the document.
        # - FALSE if the path refers to a newly created temporary file.
        # - raise COMException(scode=E_FAIL) if no source file can be created/determined.
        RaiseNotImpl("GetPathName")

    def GetFileName(self):
        # Result is a string with just the name of the document, no path information.
        RaiseNotImpl("GetFileName")

    def NotifyChanged(self):
        RaiseNotImpl("NotifyChanged")


# Additional gateway related functions.


class DebugDocumentTextConnectServer:
    _public_methods_ = (
        win32com.server.connect.IConnectionPointContainer_methods
        + win32com.server.connect.IConnectionPoint_methods
    )
    _com_interfaces_ = [
        pythoncom.IID_IConnectionPoint,
        pythoncom.IID_IConnectionPointContainer,
    ]

    # IConnectionPoint interfaces
    def __init__(self):
        self.cookieNo = -1
        self.connections = {}

    def EnumConnections(self):
        RaiseNotImpl("EnumConnections")

    def GetConnectionInterface(self):
        RaiseNotImpl("GetConnectionInterface")

    def GetConnectionPointContainer(self):
        return _wrap(self)

    def Advise(self, pUnk):
        # Creates a connection to the client.  Simply allocate a new cookie,
        # find the clients interface, and store it in a dictionary.
        interface = pUnk.QueryInterface(axdebug.IID_IDebugDocumentTextEvents, 1)
        self.cookieNo += 1
        self.connections[self.cookieNo] = interface
        return self.cookieNo

    def Unadvise(self, cookie):
        # Destroy a connection - simply delete interface from the map.
        try:
            del self.connections[cookie]
        except KeyError:
            return COMException(scode=winerror.E_UNEXPECTED)

    # IConnectionPointContainer interfaces
    def EnumConnectionPoints(self):
        RaiseNotImpl("EnumConnectionPoints")

    def FindConnectionPoint(self, iid):
        # Find a connection we support.  Only support the single event interface.
        if iid == axdebug.IID_IDebugDocumentTextEvents:
            return _wrap(self)
        raise COMException(scode=winerror.E_NOINTERFACE)  # ??


class RemoteDebugApplicationEvents:
    _public_methods_ = [
        "OnConnectDebugger",
        "OnDisconnectDebugger",
        "OnSetName",
        "OnDebugOutput",
        "OnClose",
        "OnEnterBreakPoint",
        "OnLeaveBreakPoint",
        "OnCreateThread",
        "OnDestroyThread",
        "OnBreakFlagChange",
    ]
    _com_interfaces_ = [axdebug.IID_IRemoteDebugApplicationEvents]

    def OnConnectDebugger(self, appDebugger):
        """appDebugger -- a PyIApplicationDebugger"""
        RaiseNotImpl("OnConnectDebugger")

    def OnDisconnectDebugger(self):
        RaiseNotImpl("OnDisconnectDebugger")

    def OnSetName(self, name):
        RaiseNotImpl("OnSetName")

    def OnDebugOutput(self, string):
        RaiseNotImpl("OnDebugOutput")

    def OnClose(self):
        RaiseNotImpl("OnClose")

    def OnEnterBreakPoint(self, rdat):
        """rdat -- PyIRemoteDebugApplicationThread"""
        RaiseNotImpl("OnEnterBreakPoint")

    def OnLeaveBreakPoint(self, rdat):
        """rdat -- PyIRemoteDebugApplicationThread"""
        RaiseNotImpl("OnLeaveBreakPoint")

    def OnCreateThread(self, rdat):
        """rdat -- PyIRemoteDebugApplicationThread"""
        RaiseNotImpl("OnCreateThread")

    def OnDestroyThread(self, rdat):
        """rdat -- PyIRemoteDebugApplicationThread"""
        RaiseNotImpl("OnDestroyThread")

    def OnBreakFlagChange(self, abf, rdat):
        """abf -- int - one of the axdebug.APPBREAKFLAGS constants
        rdat -- PyIRemoteDebugApplicationThread
        RaiseNotImpl("OnBreakFlagChange")
        """


class DebugExpressionContext:
    _public_methods_ = ["ParseLanguageText", "GetLanguageInfo"]
    _com_interfaces_ = [axdebug.IID_IDebugExpressionContext]

    def __init__(self):
        pass

    def ParseLanguageText(self, code, radix, delim, flags):
        """
        result is IDebugExpression
        """
        RaiseNotImpl("ParseLanguageText")

    def GetLanguageInfo(self):
        """
        result is (string langName, iid langId)
        """
        RaiseNotImpl("GetLanguageInfo")


class DebugExpression:
    _public_methods_ = [
        "Start",
        "Abort",
        "QueryIsComplete",
        "GetResultAsString",
        "GetResultAsDebugProperty",
    ]
    _com_interfaces_ = [axdebug.IID_IDebugExpression]

    def Start(self, callback):
        """
        callback -- an IDebugExpressionCallback

        result - void
        """
        RaiseNotImpl("Start")

    def Abort(self):
        """
        no params
        result -- void
        """
        RaiseNotImpl("Abort")

    def QueryIsComplete(self):
        """
        no params
        result -- void
        """
        RaiseNotImpl("QueryIsComplete")

    def GetResultAsString(self):
        RaiseNotImpl("GetResultAsString")

    def GetResultAsDebugProperty(self):
        RaiseNotImpl("GetResultAsDebugProperty")


class ProvideExpressionContexts:
    _public_methods_ = ["EnumExpressionContexts"]
    _com_interfaces_ = [axdebug.IID_IProvideExpressionContexts]

    def EnumExpressionContexts(self):
        RaiseNotImpl("EnumExpressionContexts")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\version.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from pip._vendor.packaging.version import parse, Version
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Callable, NamedTuple, SupportsInt, Tuple, Union

from ._structures import Infinity, InfinityType, NegativeInfinity, NegativeInfinityType

__all__ = ["VERSION_PATTERN", "InvalidVersion", "Version", "parse"]

LocalType = Tuple[Union[int, str], ...]

CmpPrePostDevType = Union[InfinityType, NegativeInfinityType, Tuple[str, int]]
CmpLocalType = Union[
    NegativeInfinityType,
    Tuple[Union[Tuple[int, str], Tuple[NegativeInfinityType, Union[int, str]]], ...],
]
CmpKey = Tuple[
    int,
    Tuple[int, ...],
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpLocalType,
]
VersionComparisonMethod = Callable[[CmpKey, CmpKey], bool]


class _Version(NamedTuple):
    epoch: int
    release: tuple[int, ...]
    dev: tuple[str, int] | None
    pre: tuple[str, int] | None
    post: tuple[str, int] | None
    local: LocalType | None


def parse(version: str) -> Version:
    """Parse the given version string.

    >>> parse('1.0.dev1')
    <Version('1.0.dev1')>

    :param version: The version string to parse.
    :raises InvalidVersion: When the version string is not a valid version.
    """
    return Version(version)


class InvalidVersion(ValueError):
    """Raised when a version string is not a valid version.

    >>> Version("invalid")
    Traceback (most recent call last):
        ...
    packaging.version.InvalidVersion: Invalid version: 'invalid'
    """


class _BaseVersion:
    _key: tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    # Please keep the duplicated `isinstance` check
    # in the six comparisons hereunder
    # unless you find a way to avoid adding overhead function calls.
    def __lt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key == other._key

    def __ge__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key >= other._key

    def __gt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key != other._key


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_PATTERN = _VERSION_PATTERN
"""
A string containing the regular expression used to match a valid version.

The pattern is not anchored at either end, and is intended for embedding in larger
expressions (for example, matching a version number as part of a file name). The
regular expression should be compiled with the ``re.VERBOSE`` and ``re.IGNORECASE``
flags set.

:meta hide-value:
"""


class Version(_BaseVersion):
    """This class abstracts handling of a project's versions.

    A :class:`Version` instance is comparison aware and can be compared and
    sorted using the standard Python interfaces.

    >>> v1 = Version("1.0a5")
    >>> v2 = Version("1.0")
    >>> v1
    <Version('1.0a5')>
    >>> v2
    <Version('1.0')>
    >>> v1 < v2
    True
    >>> v1 == v2
    False
    >>> v1 > v2
    False
    >>> v1 >= v2
    False
    >>> v1 <= v2
    True
    """

    _regex = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)
    _key: CmpKey

    def __init__(self, version: str) -> None:
        """Initialize a Version object.

        :param version:
            The string representation of a version which will be parsed and normalized
            before use.
        :raises InvalidVersion:
            If the ``version`` does not conform to PEP 440 in any way then this
            exception will be raised.
        """

        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: {version!r}")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(match.group("pre_l"), match.group("pre_n")),
            post=_parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=_parse_letter_version(match.group("dev_l"), match.group("dev_n")),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        """A representation of the Version that shows all internal state.

        >>> Version('1.0.0')
        <Version('1.0.0')>
        """
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        """A string representation of the version that can be round-tripped.

        >>> str(Version("1.0a5"))
        '1.0a5'
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            parts.append(f".post{self.post}")

        # Development release
        if self.dev is not None:
            parts.append(f".dev{self.dev}")

        # Local version segment
        if self.local is not None:
            parts.append(f"+{self.local}")

        return "".join(parts)

    @property
    def epoch(self) -> int:
        """The epoch of the version.

        >>> Version("2.0.0").epoch
        0
        >>> Version("1!2.0.0").epoch
        1
        """
        return self._version.epoch

    @property
    def release(self) -> tuple[int, ...]:
        """The components of the "release" segment of the version.

        >>> Version("1.2.3").release
        (1, 2, 3)
        >>> Version("2.0.0").release
        (2, 0, 0)
        >>> Version("1!2.0.0.post0").release
        (2, 0, 0)

        Includes trailing zeroes but not the epoch or any pre-release / development /
        post-release suffixes.
        """
        return self._version.release

    @property
    def pre(self) -> tuple[str, int] | None:
        """The pre-release segment of the version.

        >>> print(Version("1.2.3").pre)
        None
        >>> Version("1.2.3a1").pre
        ('a', 1)
        >>> Version("1.2.3b1").pre
        ('b', 1)
        >>> Version("1.2.3rc1").pre
        ('rc', 1)
        """
        return self._version.pre

    @property
    def post(self) -> int | None:
        """The post-release number of the version.

        >>> print(Version("1.2.3").post)
        None
        >>> Version("1.2.3.post1").post
        1
        """
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> int | None:
        """The development number of the version.

        >>> print(Version("1.2.3").dev)
        None
        >>> Version("1.2.3.dev1").dev
        1
        """
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> str | None:
        """The local version segment of the version.

        >>> print(Version("1.2.3").local)
        None
        >>> Version("1.2.3+abc").local
        'abc'
        """
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        """The public portion of the version.

        >>> Version("1.2.3").public
        '1.2.3'
        >>> Version("1.2.3+abc").public
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").public
        '1!1.2.3.dev1'
        """
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        """The "base version" of the version.

        >>> Version("1.2.3").base_version
        '1.2.3'
        >>> Version("1.2.3+abc").base_version
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").base_version
        '1!1.2.3'

        The "base version" is the public version of the project without any pre or post
        release markers.
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        """Whether this version is a pre-release.

        >>> Version("1.2.3").is_prerelease
        False
        >>> Version("1.2.3a1").is_prerelease
        True
        >>> Version("1.2.3b1").is_prerelease
        True
        >>> Version("1.2.3rc1").is_prerelease
        True
        >>> Version("1.2.3dev1").is_prerelease
        True
        """
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        """Whether this version is a post-release.

        >>> Version("1.2.3").is_postrelease
        False
        >>> Version("1.2.3.post1").is_postrelease
        True
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """Whether this version is a development release.

        >>> Version("1.2.3").is_devrelease
        False
        >>> Version("1.2.3.dev1").is_devrelease
        True
        """
        return self.dev is not None

    @property
    def major(self) -> int:
        """The first item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").major
        1
        """
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        """The second item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").minor
        2
        >>> Version("1").minor
        0
        """
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        """The third item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").micro
        3
        >>> Version("1").micro
        0
        """
        return self.release[2] if len(self.release) >= 3 else 0


class _TrimmedRelease(Version):
    @property
    def release(self) -> tuple[int, ...]:
        """
        Release segment without any trailing zeros.

        >>> _TrimmedRelease('1.0.0').release
        (1,)
        >>> _TrimmedRelease('0.0').release
        (0,)
        """
        rel = super().release
        nonzeros = (index for index, val in enumerate(rel) if val)
        last_nonzero = max(nonzeros, default=0)
        return rel[: last_nonzero + 1]


def _parse_letter_version(
    letter: str | None, number: str | bytes | SupportsInt | None
) -> tuple[str, int] | None:
    if letter:
        # We consider there to be an implicit 0 in a pre-release if there is
        # not a numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)

    assert not letter
    if number:
        # We assume if we are given a number, but we are not given a letter
        # then this is using the implicit post release syntax (e.g. 1.0-1)
        letter = "post"

        return letter, int(number)

    return None


_local_version_separators = re.compile(r"[\._-]")


def _parse_local_version(local: str | None) -> LocalType | None:
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_separators.split(local)
        )
    return None


def _cmpkey(
    epoch: int,
    release: tuple[int, ...],
    pre: tuple[str, int] | None,
    post: tuple[str, int] | None,
    dev: tuple[str, int] | None,
    local: LocalType | None,
) -> CmpKey:
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non zero, then take the rest
    # re-reverse it back into the correct order and make it a tuple and use
    # that for our sorting key.
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre segment, but we _only_ want to do this
    # if there is not a pre or a post segment. If we have one of those then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        _pre: CmpPrePostDevType = NegativeInfinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        _pre = Infinity
    else:
        _pre = pre

    # Versions without a post segment should sort before those with one.
    if post is None:
        _post: CmpPrePostDevType = NegativeInfinity

    else:
        _post = post

    # Versions without a development segment should sort after those with one.
    if dev is None:
        _dev: CmpPrePostDevType = Infinity

    else:
        _dev = dev

    if local is None:
        # Versions without a local segment should sort before those with one.
        _local: CmpLocalType = NegativeInfinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alpha numeric segments sort before numeric segments
        # - Alpha numeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        _local = tuple(
            (i, "") if isinstance(i, int) else (NegativeInfinity, i) for i in local
        )

    return epoch, _release, _pre, _post, _dev, _local

# === NexusCore/openenv\Lib\site-packages\ipython_pygments_lexers.py ===
# -*- coding: utf-8 -*-
"""
Defines a variety of Pygments lexers for highlighting IPython code.

This includes:

    IPythonLexer, IPython3Lexer
        Lexers for pure IPython (python + magic/shell commands)

    IPythonPartialTracebackLexer, IPythonTracebackLexer
        Supports 2.x and 3.x via keyword `python3`.  The partial traceback
        lexer reads everything but the Python code appearing in a traceback.
        The full lexer combines the partial lexer with an IPython lexer.

    IPythonConsoleLexer
        A lexer for IPython console sessions, with support for tracebacks.

    IPyLexer
        A friendly lexer which examines the first line of text and from it,
        decides whether to use an IPython lexer or an IPython console lexer.
        This is probably the only lexer that needs to be explicitly added
        to Pygments.

"""
# -----------------------------------------------------------------------------
# Copyright (c) 2013, the IPython Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

__version__ = "1.1.1"

# Standard library
import re

# Third party
from pygments.lexers import (
    BashLexer,
    HtmlLexer,
    JavascriptLexer,
    RubyLexer,
    PerlLexer,
    Python2Lexer,
    Python3Lexer,
    TexLexer,
)
from pygments.lexer import (
    Lexer,
    DelegatingLexer,
    RegexLexer,
    do_insertions,
    bygroups,
    using,
)
from pygments.token import (
    Generic,
    Keyword,
    Literal,
    Name,
    Operator,
    Other,
    Text,
    Error,
)


line_re = re.compile(".*?\n")

__all__ = [
    "IPython3Lexer",
    "IPythonLexer",
    "IPythonPartialTracebackLexer",
    "IPythonTracebackLexer",
    "IPythonConsoleLexer",
    "IPyLexer",
]


ipython_tokens = [
    (
        r"(?s)(\s*)(%%capture)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%debug)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?is)(\s*)(%%html)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(HtmlLexer)),
    ),
    (
        r"(?s)(\s*)(%%javascript)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(JavascriptLexer)),
    ),
    (
        r"(?s)(\s*)(%%js)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(JavascriptLexer)),
    ),
    (
        r"(?s)(\s*)(%%latex)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(TexLexer)),
    ),
    (
        r"(?s)(\s*)(%%perl)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(PerlLexer)),
    ),
    (
        r"(?s)(\s*)(%%prun)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%pypy)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%python2)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python2Lexer)),
    ),
    (
        r"(?s)(\s*)(%%python3)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%python)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%ruby)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(RubyLexer)),
    ),
    (
        r"(?s)(\s*)(%%timeit)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%time)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%writefile)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (
        r"(?s)(\s*)(%%file)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(Python3Lexer)),
    ),
    (r"(?s)(\s*)(%%)(\w+)(.*)", bygroups(Text, Operator, Keyword, Text)),
    (
        r"(?s)(^\s*)(%%!)([^\n]*\n)(.*)",
        bygroups(Text, Operator, Text, using(BashLexer)),
    ),
    (r"(%%?)(\w+)(\?\??)$", bygroups(Operator, Keyword, Operator)),
    (r"\b(\?\??)(\s*)$", bygroups(Operator, Text)),
    (r"(%)(sx|sc|system)(.*)(\n)", bygroups(Operator, Keyword, using(BashLexer), Text)),
    (r"(%)(\w+)(.*\n)", bygroups(Operator, Keyword, Text)),
    (r"^(!!)(.+)(\n)", bygroups(Operator, using(BashLexer), Text)),
    (r"(!)(?!=)(.+)(\n)", bygroups(Operator, using(BashLexer), Text)),
    (r"^(\s*)(\?\??)(\s*%{0,2}[\w\.\*]*)", bygroups(Text, Operator, Text)),
    (r"(\s*%{0,2}[\w\.\*]*)(\?\??)(\s*)$", bygroups(Text, Operator, Text)),
]


class IPython3Lexer(Python3Lexer):
    """IPython code lexer (based on Python 3)"""

    name = "IPython"
    aliases = ["ipython", "ipython3"]

    tokens = Python3Lexer.tokens.copy()
    tokens["root"] = ipython_tokens + tokens["root"]


IPythonLexer = IPython3Lexer


class IPythonPartialTracebackLexer(RegexLexer):
    """
    Partial lexer for IPython tracebacks.

    Handles all the non-python output.

    """

    name = "IPython Partial Traceback"

    tokens = {
        "root": [
            # Tracebacks for syntax errors have a different style.
            # For both types of tracebacks, we mark the first line with
            # Generic.Traceback.  For syntax errors, we mark the filename
            # as we mark the filenames for non-syntax tracebacks.
            #
            # These two regexps define how IPythonConsoleLexer finds a
            # traceback.
            #
            ## Non-syntax traceback
            (r"^(\^C)?(-+\n)", bygroups(Error, Generic.Traceback)),
            ## Syntax traceback
            (
                r"^(  File)(.*)(, line )(\d+\n)",
                bygroups(
                    Generic.Traceback,
                    Name.Namespace,
                    Generic.Traceback,
                    Literal.Number.Integer,
                ),
            ),
            # (Exception Identifier)(Whitespace)(Traceback Message)
            (
                r"(?u)(^[^\d\W]\w*)(\s*)(Traceback.*?\n)",
                bygroups(Name.Exception, Generic.Whitespace, Text),
            ),
            # (Module/Filename)(Text)(Callee)(Function Signature)
            # Better options for callee and function signature?
            (
                r"(.*)( in )(.*)(\(.*\)\n)",
                bygroups(Name.Namespace, Text, Name.Entity, Name.Tag),
            ),
            # Regular line: (Whitespace)(Line Number)(Python Code)
            (
                r"(\s*?)(\d+)(.*?\n)",
                bygroups(Generic.Whitespace, Literal.Number.Integer, Other),
            ),
            # Emphasized line: (Arrow)(Line Number)(Python Code)
            # Using Exception token so arrow color matches the Exception.
            (
                r"(-*>?\s?)(\d+)(.*?\n)",
                bygroups(Name.Exception, Literal.Number.Integer, Other),
            ),
            # (Exception Identifier)(Message)
            (r"(?u)(^[^\d\W]\w*)(:.*?\n)", bygroups(Name.Exception, Text)),
            # Tag everything else as Other, will be handled later.
            (r".*\n", Other),
        ],
    }


class IPythonTracebackLexer(DelegatingLexer):
    """
    IPython traceback lexer.

    For doctests, the tracebacks can be snipped as much as desired with the
    exception to the lines that designate a traceback. For non-syntax error
    tracebacks, this is the line of hyphens. For syntax error tracebacks,
    this is the line which lists the File and line number.

    """

    # The lexer inherits from DelegatingLexer.  The "root" lexer is an
    # appropriate IPython lexer, which depends on the value of the boolean
    # `python3`.  First, we parse with the partial IPython traceback lexer.
    # Then, any code marked with the "Other" token is delegated to the root
    # lexer.
    #
    name = "IPython Traceback"
    aliases = ["ipythontb", "ipython3tb"]

    def __init__(self, **options):
        """
        A subclass of `DelegatingLexer` which delegates to the appropriate to either IPyLexer,
        IPythonPartialTracebackLexer.
        """
        # note we need a __init__ doc, as otherwise it inherits the doc from the super class
        # which will fail the documentation build as it references section of the pygments docs that
        # do not exists when building IPython's docs.
        DelegatingLexer.__init__(
            self, IPython3Lexer, IPythonPartialTracebackLexer, **options
        )


class IPythonConsoleLexer(Lexer):
    """
    An IPython console lexer for IPython code-blocks and doctests, such as:

    .. code-block:: rst

        .. code-block:: ipythonconsole

            In [1]: a = 'foo'

            In [2]: a
            Out[2]: 'foo'

            In [3]: print(a)
            foo


    Support is also provided for IPython exceptions:

    .. code-block:: rst

        .. code-block:: ipythonconsole

            In [1]: raise Exception
            Traceback (most recent call last):
            ...
            Exception

    """

    name = "IPython console session"
    aliases = ["ipythonconsole", "ipython3console"]
    mimetypes = ["text/x-ipython-console"]

    # The regexps used to determine what is input and what is output.
    # The default prompts for IPython are:
    #
    #    in           = 'In [#]: '
    #    continuation = '   .D.: '
    #    template     = 'Out[#]: '
    #
    # Where '#' is the 'prompt number' or 'execution count' and 'D'
    # D is a number of dots  matching the width of the execution count
    #
    in1_regex = r"In \[[0-9]+\]: "
    in2_regex = r"   \.\.+\.: "
    out_regex = r"Out\[[0-9]+\]: "

    #: The regex to determine when a traceback starts.
    ipytb_start = re.compile(r"^(\^C)?(-+\n)|^(  File)(.*)(, line )(\d+\n)")

    def __init__(self, **options):
        """Initialize the IPython console lexer.

        Parameters
        ----------
        in1_regex : RegexObject
            The compiled regular expression used to detect the start
            of inputs. Although the IPython configuration setting may have a
            trailing whitespace, do not include it in the regex. If `None`,
            then the default input prompt is assumed.
        in2_regex : RegexObject
            The compiled regular expression used to detect the continuation
            of inputs. Although the IPython configuration setting may have a
            trailing whitespace, do not include it in the regex. If `None`,
            then the default input prompt is assumed.
        out_regex : RegexObject
            The compiled regular expression used to detect outputs. If `None`,
            then the default output prompt is assumed.

        """
        in1_regex = options.get("in1_regex", self.in1_regex)
        in2_regex = options.get("in2_regex", self.in2_regex)
        out_regex = options.get("out_regex", self.out_regex)

        # So that we can work with input and output prompts which have been
        # rstrip'd (possibly by editors) we also need rstrip'd variants. If
        # we do not do this, then such prompts will be tagged as 'output'.
        # The reason can't just use the rstrip'd variants instead is because
        # we want any whitespace associated with the prompt to be inserted
        # with the token. This allows formatted code to be modified so as hide
        # the appearance of prompts, with the whitespace included. One example
        # use of this is in copybutton.js from the standard lib Python docs.
        in1_regex_rstrip = in1_regex.rstrip() + "\n"
        in2_regex_rstrip = in2_regex.rstrip() + "\n"
        out_regex_rstrip = out_regex.rstrip() + "\n"

        # Compile and save them all.
        attrs = [
            "in1_regex",
            "in2_regex",
            "out_regex",
            "in1_regex_rstrip",
            "in2_regex_rstrip",
            "out_regex_rstrip",
        ]
        for attr in attrs:
            self.__setattr__(attr, re.compile(locals()[attr]))

        Lexer.__init__(self, **options)

        self.pylexer = IPython3Lexer(**options)
        self.tblexer = IPythonTracebackLexer(**options)

        self.reset()

    def reset(self):
        self.mode = "output"
        self.index = 0
        self.buffer = ""
        self.insertions = []

    def buffered_tokens(self):
        """
        Generator of unprocessed tokens after doing insertions and before
        changing to a new state.

        """
        if self.mode == "output":
            tokens = [(0, Generic.Output, self.buffer)]
        elif self.mode == "input":
            tokens = self.pylexer.get_tokens_unprocessed(self.buffer)
        else:  # traceback
            tokens = self.tblexer.get_tokens_unprocessed(self.buffer)

        for i, t, v in do_insertions(self.insertions, tokens):
            # All token indexes are relative to the buffer.
            yield self.index + i, t, v

        # Clear it all
        self.index += len(self.buffer)
        self.buffer = ""
        self.insertions = []

    def get_mci(self, line):
        """
        Parses the line and returns a 3-tuple: (mode, code, insertion).

        `mode` is the next mode (or state) of the lexer, and is always equal
        to 'input', 'output', or 'tb'.

        `code` is a portion of the line that should be added to the buffer
        corresponding to the next mode and eventually lexed by another lexer.
        For example, `code` could be Python code if `mode` were 'input'.

        `insertion` is a 3-tuple (index, token, text) representing an
        unprocessed "token" that will be inserted into the stream of tokens
        that are created from the buffer once we change modes. This is usually
        the input or output prompt.

        In general, the next mode depends on current mode and on the contents
        of `line`.

        """
        # To reduce the number of regex match checks, we have multiple
        # 'if' blocks instead of 'if-elif' blocks.

        # Check for possible end of input
        in2_match = self.in2_regex.match(line)
        in2_match_rstrip = self.in2_regex_rstrip.match(line)
        if (
            in2_match and in2_match.group().rstrip() == line.rstrip()
        ) or in2_match_rstrip:
            end_input = True
        else:
            end_input = False
        if end_input and self.mode != "tb":
            # Only look for an end of input when not in tb mode.
            # An ellipsis could appear within the traceback.
            mode = "output"
            code = ""
            insertion = (0, Generic.Prompt, line)
            return mode, code, insertion

        # Check for output prompt
        out_match = self.out_regex.match(line)
        out_match_rstrip = self.out_regex_rstrip.match(line)
        if out_match or out_match_rstrip:
            mode = "output"
            if out_match:
                idx = out_match.end()
            else:
                idx = out_match_rstrip.end()
            code = line[idx:]
            # Use the 'heading' token for output.  We cannot use Generic.Error
            # since it would conflict with exceptions.
            insertion = (0, Generic.Heading, line[:idx])
            return mode, code, insertion

        # Check for input or continuation prompt (non stripped version)
        in1_match = self.in1_regex.match(line)
        if in1_match or (in2_match and self.mode != "tb"):
            # New input or when not in tb, continued input.
            # We do not check for continued input when in tb since it is
            # allowable to replace a long stack with an ellipsis.
            mode = "input"
            if in1_match:
                idx = in1_match.end()
            else:  # in2_match
                idx = in2_match.end()
            code = line[idx:]
            insertion = (0, Generic.Prompt, line[:idx])
            return mode, code, insertion

        # Check for input or continuation prompt (stripped version)
        in1_match_rstrip = self.in1_regex_rstrip.match(line)
        if in1_match_rstrip or (in2_match_rstrip and self.mode != "tb"):
            # New input or when not in tb, continued input.
            # We do not check for continued input when in tb since it is
            # allowable to replace a long stack with an ellipsis.
            mode = "input"
            if in1_match_rstrip:
                idx = in1_match_rstrip.end()
            else:  # in2_match
                idx = in2_match_rstrip.end()
            code = line[idx:]
            insertion = (0, Generic.Prompt, line[:idx])
            return mode, code, insertion

        # Check for traceback
        if self.ipytb_start.match(line):
            mode = "tb"
            code = line
            insertion = None
            return mode, code, insertion

        # All other stuff...
        if self.mode in ("input", "output"):
            # We assume all other text is output. Multiline input that
            # does not use the continuation marker cannot be detected.
            # For example, the 3 in the following is clearly output:
            #
            #    In [1]: print(3)
            #    3
            #
            # But the following second line is part of the input:
            #
            #    In [2]: while True:
            #        print(True)
            #
            # In both cases, the 2nd line will be 'output'.
            #
            mode = "output"
        else:
            mode = "tb"

        code = line
        insertion = None

        return mode, code, insertion

    def get_tokens_unprocessed(self, text):
        self.reset()
        for match in line_re.finditer(text):
            line = match.group()
            mode, code, insertion = self.get_mci(line)

            if mode != self.mode:
                # Yield buffered tokens before transitioning to new mode.
                for token in self.buffered_tokens():
                    yield token
                self.mode = mode

            if insertion:
                self.insertions.append((len(self.buffer), [insertion]))
            self.buffer += code

        for token in self.buffered_tokens():
            yield token


class IPyLexer(Lexer):
    r"""
    Primary lexer for all IPython-like code.

    This is a simple helper lexer.  If the first line of the text begins with
    "In \[[0-9]+\]:", then the entire text is parsed with an IPython console
    lexer. If not, then the entire text is parsed with an IPython lexer.

    The goal is to reduce the number of lexers that are registered
    with Pygments.

    """

    name = "IPy session"
    aliases = ["ipy", "ipy3"]

    def __init__(self, **options):
        """
        Create a new IPyLexer instance which dispatch to either an
        IPythonCOnsoleLexer (if In prompts are present) or and IPythonLexer (if
        In prompts are not present).
        """
        # init docstring is necessary for docs not to fail to build do to parent
        # docs referenceing a section in pygments docs.
        Lexer.__init__(self, **options)

        self.IPythonLexer = IPythonLexer(**options)
        self.IPythonConsoleLexer = IPythonConsoleLexer(**options)

    def get_tokens_unprocessed(self, text):
        # Search for the input prompt anywhere...this allows code blocks to
        # begin with comments as well.
        if re.match(r".*(In \[[0-9]+\]:)", text.strip(), re.DOTALL):
            lex = self.IPythonConsoleLexer
        else:
            lex = self.IPythonLexer
        for token in lex.get_tokens_unprocessed(text):
            yield token

# === NexusCore/openenv\Lib\site-packages\packaging\version.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.version import parse, Version
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Callable, NamedTuple, SupportsInt, Tuple, Union

from ._structures import Infinity, InfinityType, NegativeInfinity, NegativeInfinityType

__all__ = ["VERSION_PATTERN", "InvalidVersion", "Version", "parse"]

LocalType = Tuple[Union[int, str], ...]

CmpPrePostDevType = Union[InfinityType, NegativeInfinityType, Tuple[str, int]]
CmpLocalType = Union[
    NegativeInfinityType,
    Tuple[Union[Tuple[int, str], Tuple[NegativeInfinityType, Union[int, str]]], ...],
]
CmpKey = Tuple[
    int,
    Tuple[int, ...],
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpLocalType,
]
VersionComparisonMethod = Callable[[CmpKey, CmpKey], bool]


class _Version(NamedTuple):
    epoch: int
    release: tuple[int, ...]
    dev: tuple[str, int] | None
    pre: tuple[str, int] | None
    post: tuple[str, int] | None
    local: LocalType | None


def parse(version: str) -> Version:
    """Parse the given version string.

    >>> parse('1.0.dev1')
    <Version('1.0.dev1')>

    :param version: The version string to parse.
    :raises InvalidVersion: When the version string is not a valid version.
    """
    return Version(version)


class InvalidVersion(ValueError):
    """Raised when a version string is not a valid version.

    >>> Version("invalid")
    Traceback (most recent call last):
        ...
    packaging.version.InvalidVersion: Invalid version: 'invalid'
    """


class _BaseVersion:
    _key: tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    # Please keep the duplicated `isinstance` check
    # in the six comparisons hereunder
    # unless you find a way to avoid adding overhead function calls.
    def __lt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key == other._key

    def __ge__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key >= other._key

    def __gt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key != other._key


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_PATTERN = _VERSION_PATTERN
"""
A string containing the regular expression used to match a valid version.

The pattern is not anchored at either end, and is intended for embedding in larger
expressions (for example, matching a version number as part of a file name). The
regular expression should be compiled with the ``re.VERBOSE`` and ``re.IGNORECASE``
flags set.

:meta hide-value:
"""


class Version(_BaseVersion):
    """This class abstracts handling of a project's versions.

    A :class:`Version` instance is comparison aware and can be compared and
    sorted using the standard Python interfaces.

    >>> v1 = Version("1.0a5")
    >>> v2 = Version("1.0")
    >>> v1
    <Version('1.0a5')>
    >>> v2
    <Version('1.0')>
    >>> v1 < v2
    True
    >>> v1 == v2
    False
    >>> v1 > v2
    False
    >>> v1 >= v2
    False
    >>> v1 <= v2
    True
    """

    _regex = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)
    _key: CmpKey

    def __init__(self, version: str) -> None:
        """Initialize a Version object.

        :param version:
            The string representation of a version which will be parsed and normalized
            before use.
        :raises InvalidVersion:
            If the ``version`` does not conform to PEP 440 in any way then this
            exception will be raised.
        """

        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: {version!r}")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(match.group("pre_l"), match.group("pre_n")),
            post=_parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=_parse_letter_version(match.group("dev_l"), match.group("dev_n")),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        """A representation of the Version that shows all internal state.

        >>> Version('1.0.0')
        <Version('1.0.0')>
        """
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        """A string representation of the version that can be round-tripped.

        >>> str(Version("1.0a5"))
        '1.0a5'
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            parts.append(f".post{self.post}")

        # Development release
        if self.dev is not None:
            parts.append(f".dev{self.dev}")

        # Local version segment
        if self.local is not None:
            parts.append(f"+{self.local}")

        return "".join(parts)

    @property
    def epoch(self) -> int:
        """The epoch of the version.

        >>> Version("2.0.0").epoch
        0
        >>> Version("1!2.0.0").epoch
        1
        """
        return self._version.epoch

    @property
    def release(self) -> tuple[int, ...]:
        """The components of the "release" segment of the version.

        >>> Version("1.2.3").release
        (1, 2, 3)
        >>> Version("2.0.0").release
        (2, 0, 0)
        >>> Version("1!2.0.0.post0").release
        (2, 0, 0)

        Includes trailing zeroes but not the epoch or any pre-release / development /
        post-release suffixes.
        """
        return self._version.release

    @property
    def pre(self) -> tuple[str, int] | None:
        """The pre-release segment of the version.

        >>> print(Version("1.2.3").pre)
        None
        >>> Version("1.2.3a1").pre
        ('a', 1)
        >>> Version("1.2.3b1").pre
        ('b', 1)
        >>> Version("1.2.3rc1").pre
        ('rc', 1)
        """
        return self._version.pre

    @property
    def post(self) -> int | None:
        """The post-release number of the version.

        >>> print(Version("1.2.3").post)
        None
        >>> Version("1.2.3.post1").post
        1
        """
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> int | None:
        """The development number of the version.

        >>> print(Version("1.2.3").dev)
        None
        >>> Version("1.2.3.dev1").dev
        1
        """
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> str | None:
        """The local version segment of the version.

        >>> print(Version("1.2.3").local)
        None
        >>> Version("1.2.3+abc").local
        'abc'
        """
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        """The public portion of the version.

        >>> Version("1.2.3").public
        '1.2.3'
        >>> Version("1.2.3+abc").public
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").public
        '1!1.2.3.dev1'
        """
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        """The "base version" of the version.

        >>> Version("1.2.3").base_version
        '1.2.3'
        >>> Version("1.2.3+abc").base_version
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").base_version
        '1!1.2.3'

        The "base version" is the public version of the project without any pre or post
        release markers.
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        """Whether this version is a pre-release.

        >>> Version("1.2.3").is_prerelease
        False
        >>> Version("1.2.3a1").is_prerelease
        True
        >>> Version("1.2.3b1").is_prerelease
        True
        >>> Version("1.2.3rc1").is_prerelease
        True
        >>> Version("1.2.3dev1").is_prerelease
        True
        """
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        """Whether this version is a post-release.

        >>> Version("1.2.3").is_postrelease
        False
        >>> Version("1.2.3.post1").is_postrelease
        True
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """Whether this version is a development release.

        >>> Version("1.2.3").is_devrelease
        False
        >>> Version("1.2.3.dev1").is_devrelease
        True
        """
        return self.dev is not None

    @property
    def major(self) -> int:
        """The first item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").major
        1
        """
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        """The second item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").minor
        2
        >>> Version("1").minor
        0
        """
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        """The third item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").micro
        3
        >>> Version("1").micro
        0
        """
        return self.release[2] if len(self.release) >= 3 else 0


class _TrimmedRelease(Version):
    @property
    def release(self) -> tuple[int, ...]:
        """
        Release segment without any trailing zeros.

        >>> _TrimmedRelease('1.0.0').release
        (1,)
        >>> _TrimmedRelease('0.0').release
        (0,)
        """
        rel = super().release
        nonzeros = (index for index, val in enumerate(rel) if val)
        last_nonzero = max(nonzeros, default=0)
        return rel[: last_nonzero + 1]


def _parse_letter_version(
    letter: str | None, number: str | bytes | SupportsInt | None
) -> tuple[str, int] | None:
    if letter:
        # We consider there to be an implicit 0 in a pre-release if there is
        # not a numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)

    assert not letter
    if number:
        # We assume if we are given a number, but we are not given a letter
        # then this is using the implicit post release syntax (e.g. 1.0-1)
        letter = "post"

        return letter, int(number)

    return None


_local_version_separators = re.compile(r"[\._-]")


def _parse_local_version(local: str | None) -> LocalType | None:
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_separators.split(local)
        )
    return None


def _cmpkey(
    epoch: int,
    release: tuple[int, ...],
    pre: tuple[str, int] | None,
    post: tuple[str, int] | None,
    dev: tuple[str, int] | None,
    local: LocalType | None,
) -> CmpKey:
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non zero, then take the rest
    # re-reverse it back into the correct order and make it a tuple and use
    # that for our sorting key.
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre segment, but we _only_ want to do this
    # if there is not a pre or a post segment. If we have one of those then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        _pre: CmpPrePostDevType = NegativeInfinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        _pre = Infinity
    else:
        _pre = pre

    # Versions without a post segment should sort before those with one.
    if post is None:
        _post: CmpPrePostDevType = NegativeInfinity

    else:
        _post = post

    # Versions without a development segment should sort after those with one.
    if dev is None:
        _dev: CmpPrePostDevType = Infinity

    else:
        _dev = dev

    if local is None:
        # Versions without a local segment should sort before those with one.
        _local: CmpLocalType = NegativeInfinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alpha numeric segments sort before numeric segments
        # - Alpha numeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        _local = tuple(
            (i, "") if isinstance(i, int) else (NegativeInfinity, i) for i in local
        )

    return epoch, _release, _pre, _post, _dev, _local

# === NexusCore/openenv\Lib\site-packages\psutil\_psaix.py ===
# Copyright (c) 2009, Giampaolo Rodola'
# Copyright (c) 2017, Arnon Yaari
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""AIX platform implementation."""

import functools
import glob
import os
import re
import subprocess
import sys
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_aix as cext
from . import _psutil_posix as cext_posix
from ._common import NIC_DUPLEX_FULL
from ._common import NIC_DUPLEX_HALF
from ._common import NIC_DUPLEX_UNKNOWN
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import ZombieProcess
from ._common import conn_to_ntuple
from ._common import get_procfs_path
from ._common import memoize_when_activated
from ._common import usage_percent
from ._compat import PY3
from ._compat import FileNotFoundError
from ._compat import PermissionError
from ._compat import ProcessLookupError


__extra__all__ = ["PROCFS_PATH"]


# =====================================================================
# --- globals
# =====================================================================


HAS_THREADS = hasattr(cext, "proc_threads")
HAS_NET_IO_COUNTERS = hasattr(cext, "net_io_counters")
HAS_PROC_IO_COUNTERS = hasattr(cext, "proc_io_counters")

PAGE_SIZE = cext_posix.getpagesize()
AF_LINK = cext_posix.AF_LINK

PROC_STATUSES = {
    cext.SIDL: _common.STATUS_IDLE,
    cext.SZOMB: _common.STATUS_ZOMBIE,
    cext.SACTIVE: _common.STATUS_RUNNING,
    cext.SSWAP: _common.STATUS_RUNNING,  # TODO what status is this?
    cext.SSTOP: _common.STATUS_STOPPED,
}

TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RCVD: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

proc_info_map = dict(
    ppid=0,
    rss=1,
    vms=2,
    create_time=3,
    nice=4,
    num_threads=5,
    status=6,
    ttynr=7,
)


# =====================================================================
# --- named tuples
# =====================================================================


# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
# psutil.Process.memory_full_info()
pfullmem = pmem
# psutil.Process.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'system', 'idle', 'iowait'])
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    total, avail, free, pinned, inuse = cext.virtual_mem()
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, avail, percent, inuse, free)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, free, sin, sout = cext.swap_mem()
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system-wide CPU times as a named tuple."""
    ret = cext.per_cpu_times()
    return scputimes(*[sum(x) for x in zip(*ret)])


def per_cpu_times():
    """Return system per-CPU times as a list of named tuples."""
    ret = cext.per_cpu_times()
    return [scputimes(*x) for x in ret]


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # mimic os.cpu_count() behavior
        return None


def cpu_count_cores():
    cmd = ["lsdev", "-Cc", "processor"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if PY3:
        stdout, stderr = (
            x.decode(sys.stdout.encoding) for x in (stdout, stderr)
        )
    if p.returncode != 0:
        raise RuntimeError("%r command error\n%s" % (cmd, stderr))
    processors = stdout.strip().splitlines()
    return len(processors) or None


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    ctx_switches, interrupts, soft_interrupts, syscalls = cext.cpu_stats()
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls
    )


# =====================================================================
# --- disks
# =====================================================================


disk_io_counters = cext.disk_io_counters
disk_usage = _psposix.disk_usage


def disk_partitions(all=False):
    """Return system disk partitions."""
    # TODO - the filtering logic should be better checked so that
    # it tries to reflect 'df' as much as possible
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            # Differently from, say, Linux, we don't have a list of
            # common fs types so the best we can do, AFAIK, is to
            # filter by filesystem having a total size > 0.
            if not disk_usage(mountpoint).total:
                continue
        maxfile = maxpath = None  # set later
        ntuple = _common.sdiskpart(
            device, mountpoint, fstype, opts, maxfile, maxpath
        )
        retlist.append(ntuple)
    return retlist


# =====================================================================
# --- network
# =====================================================================


net_if_addrs = cext_posix.net_if_addrs

if HAS_NET_IO_COUNTERS:
    net_io_counters = cext.net_io_counters


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    cmap = _common.conn_tmap
    if kind not in cmap:
        raise ValueError(
            "invalid %r kind argument; choose between %s"
            % (kind, ', '.join([repr(x) for x in cmap]))
        )
    families, types = _common.conn_tmap[kind]
    rawlist = cext.net_connections(_pid)
    ret = []
    for item in rawlist:
        fd, fam, type_, laddr, raddr, status, pid = item
        if fam not in families:
            continue
        if type_ not in types:
            continue
        nt = conn_to_ntuple(
            fd,
            fam,
            type_,
            laddr,
            raddr,
            status,
            TCP_STATUSES,
            pid=pid if _pid == -1 else None,
        )
        ret.append(nt)
    return ret


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    duplex_map = {"Full": NIC_DUPLEX_FULL, "Half": NIC_DUPLEX_HALF}
    names = set([x[0] for x in net_if_addrs()])
    ret = {}
    for name in names:
        mtu = cext_posix.net_if_mtu(name)
        flags = cext_posix.net_if_flags(name)

        # try to get speed and duplex
        # TODO: rewrite this in C (entstat forks, so use truss -f to follow.
        # looks like it is using an undocumented ioctl?)
        duplex = ""
        speed = 0
        p = subprocess.Popen(
            ["/usr/bin/entstat", "-d", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = p.communicate()
        if PY3:
            stdout, stderr = (
                x.decode(sys.stdout.encoding) for x in (stdout, stderr)
            )
        if p.returncode == 0:
            re_result = re.search(
                r"Running: (\d+) Mbps.*?(\w+) Duplex", stdout
            )
            if re_result is not None:
                speed = int(re_result.group(1))
                duplex = re_result.group(2)

        output_flags = ','.join(flags)
        isup = 'running' in flags
        duplex = duplex_map.get(duplex, NIC_DUPLEX_UNKNOWN)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu, output_flags)
    return ret


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    localhost = (':0.0', ':0')
    for item in rawlist:
        user, tty, hostname, tstamp, user_process, pid = item
        # note: the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname in localhost:
            hostname = 'localhost'
        nt = _common.suser(user, tty, hostname, tstamp, pid)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir(get_procfs_path()) if x.isdigit()]


def pid_exists(pid):
    """Check for the existence of a unix pid."""
    return os.path.exists(os.path.join(get_procfs_path(), str(pid), "psinfo"))


def wrap_exceptions(fun):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except (FileNotFoundError, ProcessLookupError):
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            if not pid_exists(self.pid):
                raise NoSuchProcess(self.pid, self._name)
            else:
                raise ZombieProcess(self.pid, self._name, self._ppid)
        except PermissionError:
            raise AccessDenied(self.pid, self._name)

    return wrapper


class Process:
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    def oneshot_enter(self):
        self._proc_basic_info.cache_activate(self)
        self._proc_cred.cache_activate(self)

    def oneshot_exit(self):
        self._proc_basic_info.cache_deactivate(self)
        self._proc_cred.cache_deactivate(self)

    @wrap_exceptions
    @memoize_when_activated
    def _proc_basic_info(self):
        return cext.proc_basic_info(self.pid, self._procfs_path)

    @wrap_exceptions
    @memoize_when_activated
    def _proc_cred(self):
        return cext.proc_cred(self.pid, self._procfs_path)

    @wrap_exceptions
    def name(self):
        if self.pid == 0:
            return "swapper"
        # note: max 16 characters
        return cext.proc_name(self.pid, self._procfs_path).rstrip("\x00")

    @wrap_exceptions
    def exe(self):
        # there is no way to get executable path in AIX other than to guess,
        # and guessing is more complex than what's in the wrapping class
        cmdline = self.cmdline()
        if not cmdline:
            return ''
        exe = cmdline[0]
        if os.path.sep in exe:
            # relative or absolute path
            if not os.path.isabs(exe):
                # if cwd has changed, we're out of luck - this may be wrong!
                exe = os.path.abspath(os.path.join(self.cwd(), exe))
            if (
                os.path.isabs(exe)
                and os.path.isfile(exe)
                and os.access(exe, os.X_OK)
            ):
                return exe
            # not found, move to search in PATH using basename only
            exe = os.path.basename(exe)
        # search for exe name PATH
        for path in os.environ["PATH"].split(":"):
            possible_exe = os.path.abspath(os.path.join(path, exe))
            if os.path.isfile(possible_exe) and os.access(
                possible_exe, os.X_OK
            ):
                return possible_exe
        return ''

    @wrap_exceptions
    def cmdline(self):
        return cext.proc_args(self.pid)

    @wrap_exceptions
    def environ(self):
        return cext.proc_environ(self.pid)

    @wrap_exceptions
    def create_time(self):
        return self._proc_basic_info()[proc_info_map['create_time']]

    @wrap_exceptions
    def num_threads(self):
        return self._proc_basic_info()[proc_info_map['num_threads']]

    if HAS_THREADS:

        @wrap_exceptions
        def threads(self):
            rawlist = cext.proc_threads(self.pid)
            retlist = []
            for thread_id, utime, stime in rawlist:
                ntuple = _common.pthread(thread_id, utime, stime)
                retlist.append(ntuple)
            # The underlying C implementation retrieves all OS threads
            # and filters them by PID.  At this point we can't tell whether
            # an empty list means there were no connections for process or
            # process is no longer active so we force NSP in case the PID
            # is no longer there.
            if not retlist:
                # will raise NSP if process is gone
                os.stat('%s/%s' % (self._procfs_path, self.pid))
            return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        ret = net_connections(kind, _pid=self.pid)
        # The underlying C implementation retrieves all OS connections
        # and filters them by PID.  At this point we can't tell whether
        # an empty list means there were no connections for process or
        # process is no longer active so we force NSP in case the PID
        # is no longer there.
        if not ret:
            # will raise NSP if process is gone
            os.stat('%s/%s' % (self._procfs_path, self.pid))
        return ret

    @wrap_exceptions
    def nice_get(self):
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def ppid(self):
        self._ppid = self._proc_basic_info()[proc_info_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def uids(self):
        real, effective, saved, _, _, _ = self._proc_cred()
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def gids(self):
        _, _, _, real, effective, saved = self._proc_cred()
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def cpu_times(self):
        t = cext.proc_cpu_times(self.pid, self._procfs_path)
        return _common.pcputimes(*t)

    @wrap_exceptions
    def terminal(self):
        ttydev = self._proc_basic_info()[proc_info_map['ttynr']]
        # convert from 64-bit dev_t to 32-bit dev_t and then map the device
        ttydev = ((ttydev & 0x0000FFFF00000000) >> 16) | (ttydev & 0xFFFF)
        # try to match rdev of /dev/pts/* files ttydev
        for dev in glob.glob("/dev/**/*"):
            if os.stat(dev).st_rdev == ttydev:
                return dev
        return None

    @wrap_exceptions
    def cwd(self):
        procfs_path = self._procfs_path
        try:
            result = os.readlink("%s/%s/cwd" % (procfs_path, self.pid))
            return result.rstrip('/')
        except FileNotFoundError:
            os.stat("%s/%s" % (procfs_path, self.pid))  # raise NSP or AD
            return ""

    @wrap_exceptions
    def memory_info(self):
        ret = self._proc_basic_info()
        rss = ret[proc_info_map['rss']] * 1024
        vms = ret[proc_info_map['vms']] * 1024
        return pmem(rss, vms)

    memory_full_info = memory_info

    @wrap_exceptions
    def status(self):
        code = self._proc_basic_info()[proc_info_map['status']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    def open_files(self):
        # TODO rewrite without using procfiles (stat /proc/pid/fd/* and then
        # find matching name of the inode)
        p = subprocess.Popen(
            ["/usr/bin/procfiles", "-n", str(self.pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = p.communicate()
        if PY3:
            stdout, stderr = (
                x.decode(sys.stdout.encoding) for x in (stdout, stderr)
            )
        if "no such process" in stderr.lower():
            raise NoSuchProcess(self.pid, self._name)
        procfiles = re.findall(r"(\d+): S_IFREG.*\s*.*name:(.*)\n", stdout)
        retlist = []
        for fd, path in procfiles:
            path = path.strip()
            if path.startswith("//"):
                path = path[1:]
            if path.lower() == "cannot be retrieved":
                continue
            retlist.append(_common.popenfile(path, int(fd)))
        return retlist

    @wrap_exceptions
    def num_fds(self):
        if self.pid == 0:  # no /proc/0/fd
            return 0
        return len(os.listdir("%s/%s/fd" % (self._procfs_path, self.pid)))

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(*cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    if HAS_PROC_IO_COUNTERS:

        @wrap_exceptions
        def io_counters(self):
            try:
                rc, wc, rb, wb = cext.proc_io_counters(self.pid)
            except OSError:
                # if process is terminated, proc_io_counters returns OSError
                # instead of NSP
                if not pid_exists(self.pid):
                    raise NoSuchProcess(self.pid, self._name)
                raise
            return _common.pio(rc, wc, rb, wb)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\version.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from pip._vendor.packaging.version import parse, Version
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Callable, NamedTuple, SupportsInt, Tuple, Union

from ._structures import Infinity, InfinityType, NegativeInfinity, NegativeInfinityType

__all__ = ["VERSION_PATTERN", "InvalidVersion", "Version", "parse"]

LocalType = Tuple[Union[int, str], ...]

CmpPrePostDevType = Union[InfinityType, NegativeInfinityType, Tuple[str, int]]
CmpLocalType = Union[
    NegativeInfinityType,
    Tuple[Union[Tuple[int, str], Tuple[NegativeInfinityType, Union[int, str]]], ...],
]
CmpKey = Tuple[
    int,
    Tuple[int, ...],
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpLocalType,
]
VersionComparisonMethod = Callable[[CmpKey, CmpKey], bool]


class _Version(NamedTuple):
    epoch: int
    release: tuple[int, ...]
    dev: tuple[str, int] | None
    pre: tuple[str, int] | None
    post: tuple[str, int] | None
    local: LocalType | None


def parse(version: str) -> Version:
    """Parse the given version string.

    >>> parse('1.0.dev1')
    <Version('1.0.dev1')>

    :param version: The version string to parse.
    :raises InvalidVersion: When the version string is not a valid version.
    """
    return Version(version)


class InvalidVersion(ValueError):
    """Raised when a version string is not a valid version.

    >>> Version("invalid")
    Traceback (most recent call last):
        ...
    packaging.version.InvalidVersion: Invalid version: 'invalid'
    """


class _BaseVersion:
    _key: tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    # Please keep the duplicated `isinstance` check
    # in the six comparisons hereunder
    # unless you find a way to avoid adding overhead function calls.
    def __lt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key == other._key

    def __ge__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key >= other._key

    def __gt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key != other._key


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_PATTERN = _VERSION_PATTERN
"""
A string containing the regular expression used to match a valid version.

The pattern is not anchored at either end, and is intended for embedding in larger
expressions (for example, matching a version number as part of a file name). The
regular expression should be compiled with the ``re.VERBOSE`` and ``re.IGNORECASE``
flags set.

:meta hide-value:
"""


class Version(_BaseVersion):
    """This class abstracts handling of a project's versions.

    A :class:`Version` instance is comparison aware and can be compared and
    sorted using the standard Python interfaces.

    >>> v1 = Version("1.0a5")
    >>> v2 = Version("1.0")
    >>> v1
    <Version('1.0a5')>
    >>> v2
    <Version('1.0')>
    >>> v1 < v2
    True
    >>> v1 == v2
    False
    >>> v1 > v2
    False
    >>> v1 >= v2
    False
    >>> v1 <= v2
    True
    """

    _regex = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)
    _key: CmpKey

    def __init__(self, version: str) -> None:
        """Initialize a Version object.

        :param version:
            The string representation of a version which will be parsed and normalized
            before use.
        :raises InvalidVersion:
            If the ``version`` does not conform to PEP 440 in any way then this
            exception will be raised.
        """

        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: {version!r}")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(match.group("pre_l"), match.group("pre_n")),
            post=_parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=_parse_letter_version(match.group("dev_l"), match.group("dev_n")),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        """A representation of the Version that shows all internal state.

        >>> Version('1.0.0')
        <Version('1.0.0')>
        """
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        """A string representation of the version that can be round-tripped.

        >>> str(Version("1.0a5"))
        '1.0a5'
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            parts.append(f".post{self.post}")

        # Development release
        if self.dev is not None:
            parts.append(f".dev{self.dev}")

        # Local version segment
        if self.local is not None:
            parts.append(f"+{self.local}")

        return "".join(parts)

    @property
    def epoch(self) -> int:
        """The epoch of the version.

        >>> Version("2.0.0").epoch
        0
        >>> Version("1!2.0.0").epoch
        1
        """
        return self._version.epoch

    @property
    def release(self) -> tuple[int, ...]:
        """The components of the "release" segment of the version.

        >>> Version("1.2.3").release
        (1, 2, 3)
        >>> Version("2.0.0").release
        (2, 0, 0)
        >>> Version("1!2.0.0.post0").release
        (2, 0, 0)

        Includes trailing zeroes but not the epoch or any pre-release / development /
        post-release suffixes.
        """
        return self._version.release

    @property
    def pre(self) -> tuple[str, int] | None:
        """The pre-release segment of the version.

        >>> print(Version("1.2.3").pre)
        None
        >>> Version("1.2.3a1").pre
        ('a', 1)
        >>> Version("1.2.3b1").pre
        ('b', 1)
        >>> Version("1.2.3rc1").pre
        ('rc', 1)
        """
        return self._version.pre

    @property
    def post(self) -> int | None:
        """The post-release number of the version.

        >>> print(Version("1.2.3").post)
        None
        >>> Version("1.2.3.post1").post
        1
        """
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> int | None:
        """The development number of the version.

        >>> print(Version("1.2.3").dev)
        None
        >>> Version("1.2.3.dev1").dev
        1
        """
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> str | None:
        """The local version segment of the version.

        >>> print(Version("1.2.3").local)
        None
        >>> Version("1.2.3+abc").local
        'abc'
        """
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        """The public portion of the version.

        >>> Version("1.2.3").public
        '1.2.3'
        >>> Version("1.2.3+abc").public
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").public
        '1!1.2.3.dev1'
        """
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        """The "base version" of the version.

        >>> Version("1.2.3").base_version
        '1.2.3'
        >>> Version("1.2.3+abc").base_version
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").base_version
        '1!1.2.3'

        The "base version" is the public version of the project without any pre or post
        release markers.
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        """Whether this version is a pre-release.

        >>> Version("1.2.3").is_prerelease
        False
        >>> Version("1.2.3a1").is_prerelease
        True
        >>> Version("1.2.3b1").is_prerelease
        True
        >>> Version("1.2.3rc1").is_prerelease
        True
        >>> Version("1.2.3dev1").is_prerelease
        True
        """
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        """Whether this version is a post-release.

        >>> Version("1.2.3").is_postrelease
        False
        >>> Version("1.2.3.post1").is_postrelease
        True
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """Whether this version is a development release.

        >>> Version("1.2.3").is_devrelease
        False
        >>> Version("1.2.3.dev1").is_devrelease
        True
        """
        return self.dev is not None

    @property
    def major(self) -> int:
        """The first item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").major
        1
        """
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        """The second item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").minor
        2
        >>> Version("1").minor
        0
        """
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        """The third item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").micro
        3
        >>> Version("1").micro
        0
        """
        return self.release[2] if len(self.release) >= 3 else 0


class _TrimmedRelease(Version):
    @property
    def release(self) -> tuple[int, ...]:
        """
        Release segment without any trailing zeros.

        >>> _TrimmedRelease('1.0.0').release
        (1,)
        >>> _TrimmedRelease('0.0').release
        (0,)
        """
        rel = super().release
        nonzeros = (index for index, val in enumerate(rel) if val)
        last_nonzero = max(nonzeros, default=0)
        return rel[: last_nonzero + 1]


def _parse_letter_version(
    letter: str | None, number: str | bytes | SupportsInt | None
) -> tuple[str, int] | None:
    if letter:
        # We consider there to be an implicit 0 in a pre-release if there is
        # not a numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)

    assert not letter
    if number:
        # We assume if we are given a number, but we are not given a letter
        # then this is using the implicit post release syntax (e.g. 1.0-1)
        letter = "post"

        return letter, int(number)

    return None


_local_version_separators = re.compile(r"[\._-]")


def _parse_local_version(local: str | None) -> LocalType | None:
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_separators.split(local)
        )
    return None


def _cmpkey(
    epoch: int,
    release: tuple[int, ...],
    pre: tuple[str, int] | None,
    post: tuple[str, int] | None,
    dev: tuple[str, int] | None,
    local: LocalType | None,
) -> CmpKey:
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non zero, then take the rest
    # re-reverse it back into the correct order and make it a tuple and use
    # that for our sorting key.
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre segment, but we _only_ want to do this
    # if there is not a pre or a post segment. If we have one of those then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        _pre: CmpPrePostDevType = NegativeInfinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        _pre = Infinity
    else:
        _pre = pre

    # Versions without a post segment should sort before those with one.
    if post is None:
        _post: CmpPrePostDevType = NegativeInfinity

    else:
        _post = post

    # Versions without a development segment should sort after those with one.
    if dev is None:
        _dev: CmpPrePostDevType = Infinity

    else:
        _dev = dev

    if local is None:
        # Versions without a local segment should sort before those with one.
        _local: CmpLocalType = NegativeInfinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alpha numeric segments sort before numeric segments
        # - Alpha numeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        _local = tuple(
            (i, "") if isinstance(i, int) else (NegativeInfinity, i) for i in local
        )

    return epoch, _release, _pre, _post, _dev, _local

# === NexusCore/openenv\Lib\site-packages\pyreadline3\modes\basemode.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import glob
import math
import os
import re
import sys

import pyreadline3.clipboard as clipboard
import pyreadline3.lineeditor.history as history
import pyreadline3.lineeditor.lineobj as lineobj
from pyreadline3.error import ReadlineError
from pyreadline3.keysyms.common import make_KeyPress_from_keydescr
from pyreadline3.logger import log
from pyreadline3.py3k_compat import is_callable, is_ironpython
from pyreadline3.unicode_helper import ensure_str, ensure_unicode


class BaseMode(object):
    mode = "base"

    def __init__(self, rlobj):
        self.argument = 0
        self.rlobj = rlobj
        self.exit_dispatch = {}
        self.key_dispatch = {}
        self.argument = 1
        self.prevargument = None
        self.l_buffer = lineobj.ReadLineTextBuffer("")
        self._history = history.LineHistory()
        self.completer_delims = " \t\n\"\\'`@$><=;|&{("
        self.show_all_if_ambiguous = "on"
        self.mark_directories = "on"
        self.complete_filesystem = "off"
        self.completer = None
        self.begidx = 0
        self.endidx = 0
        self.tabstop = 4
        self.startup_hook = None
        self.pre_input_hook = None
        self.first_prompt = True
        self.cursor_size = 25

        self.prompt = ">>> "

        # Paste settings
        # assumes data on clipboard is path if shorter than 300 characters and doesn't contain \t or \n
        # and replace \ with / for easier use in ipython
        self.enable_ipython_paste_for_paths = True

        # automatically convert tabseparated data to list of lists or array
        # constructors
        self.enable_ipython_paste_list_of_lists = True
        self.enable_win32_clipboard = True

        self.paste_line_buffer = []

        self._sub_modes = []

    def __repr__(self):
        return "<BaseMode>"

    def _gs(x):
        def g(self):
            return getattr(self.rlobj, x)

        def s(self, q):
            setattr(self.rlobj, x, q)

        return g, s

    def _g(x):
        def g(self):
            return getattr(self.rlobj, x)

        return g

    def _argreset(self):
        val = self.argument
        self.argument = 0
        if val == 0:
            val = 1
        return val

    argument_reset = property(_argreset)

    # used in readline
    ctrl_c_tap_time_interval = property(*_gs("ctrl_c_tap_time_interval"))
    allow_ctrl_c = property(*_gs("allow_ctrl_c"))
    _print_prompt = property(_g("_print_prompt"))
    _update_line = property(_g("_update_line"))
    console = property(_g("console"))
    prompt_begin_pos = property(_g("prompt_begin_pos"))
    prompt_end_pos = property(_g("prompt_end_pos"))

    # used in completer _completions
    # completer_delims=property(*_gs("completer_delims"))
    _bell = property(_g("_bell"))
    bell_style = property(_g("bell_style"))

    # used in emacs
    _clear_after = property(_g("_clear_after"))
    _update_prompt_pos = property(_g("_update_prompt_pos"))

    # not used in basemode or emacs

    def process_keyevent(self, keyinfo):
        raise NotImplementedError

    def readline_setup(self, prompt=""):
        self.l_buffer.selection_mark = -1
        if self.first_prompt:
            self.first_prompt = False
            if self.startup_hook:
                try:
                    self.startup_hook()
                except BaseException:
                    print("startup hook failed")
                    traceback.print_exc()

        self.l_buffer.reset_line()
        self.prompt = prompt

        if self.pre_input_hook:
            try:
                self.pre_input_hook()
            except BaseException:
                print("pre_input_hook failed")
                traceback.print_exc()
                self.pre_input_hook = None

    # ###################################

    def finalize(self):
        """Every bindable command should call this function for cleanup.
        Except those that want to set argument to a non-zero value.
        """
        self.argument = 0

    def add_history(self, text):
        self._history.add_history(lineobj.ReadLineTextBuffer(text))

    # Create key bindings:

    def rl_settings_to_string(self):
        out = ["%-20s: %s" % ("show all if ambigous", self.show_all_if_ambiguous)]
        out.append("%-20s: %s" % ("mark_directories", self.mark_directories))
        out.append("%-20s: %s" % ("bell_style", self.bell_style))
        out.append("------------- key bindings ------------")
        tablepat = "%-7s %-7s %-7s %-15s %-15s "
        out.append(tablepat % ("Control", "Meta", "Shift", "Keycode/char", "Function"))
        bindings = sorted(
            [(k[0], k[1], k[2], k[3], v.__name__) for k, v in self.key_dispatch.items()]
        )
        for key in bindings:
            out.append(tablepat % (key))
        return out

    def _bind_key(self, key, func):
        """setup the mapping from key to call the function."""
        if not is_callable(func):
            print("Trying to bind non method to keystroke:%s,%s" % (key, func))
            raise ReadlineError(
                "Trying to bind non method to keystroke:%s,%s,%s,%s"
                % (key, func, type(func), type(self._bind_key))
            )
        keyinfo = make_KeyPress_from_keydescr(key.lower()).tuple()
        log(">>>%s -> %s<<<" % (keyinfo, func.__name__))
        self.key_dispatch[keyinfo] = func

    def _bind_exit_key(self, key):
        """setup the mapping from key to call the function."""
        keyinfo = make_KeyPress_from_keydescr(key.lower()).tuple()
        self.exit_dispatch[keyinfo] = None

    def init_editing_mode(self, e):  # (C-e)
        """When in vi command mode, this causes a switch to emacs editing
        mode."""

        raise NotImplementedError

    # completion commands

    def _get_completions(self):
        """Return a list of possible completions for the string ending at the point.
        Also set begidx and endidx in the process."""
        completions = []
        self.begidx = self.l_buffer.point
        self.endidx = self.l_buffer.point
        buf = self.l_buffer.line_buffer
        if self.completer:
            # get the string to complete
            while self.begidx > 0:
                self.begidx -= 1
                if buf[self.begidx] in self.completer_delims:
                    self.begidx += 1
                    break
            text = ensure_str("".join(buf[self.begidx : self.endidx]))
            log('complete text="%s"' % ensure_unicode(text))
            i = 0
            while True:
                try:
                    r = self.completer(ensure_unicode(text), i)
                except IndexError:
                    break
                i += 1
                if r is None:
                    break
                elif r and r not in completions:
                    completions.append(r)
                else:
                    pass
            log("text completions=<%s>" % list(map(ensure_unicode, completions)))
        if (self.complete_filesystem == "on") and not completions:
            # get the filename to complete
            while self.begidx > 0:
                self.begidx -= 1
                if buf[self.begidx] in " \t\n":
                    self.begidx += 1
                    break
            text = ensure_str("".join(buf[self.begidx : self.endidx]))
            log('file complete text="%s"' % ensure_unicode(text))
            completions = list(
                map(
                    ensure_unicode,
                    glob.glob(os.path.expanduser(text) + "*".encode("ascii")),
                )
            )
            if self.mark_directories == "on":
                mc = []
                for f in completions:
                    if os.path.isdir(f):
                        mc.append(f + os.sep)
                    else:
                        mc.append(f)
                completions = mc
            log("fnames=<%s>" % list(map(ensure_unicode, completions)))
        return completions

    def _display_completions(self, completions):
        if not completions:
            return
        self.console.write("\n")
        wmax = max(map(len, completions))
        w, h = self.console.size()
        cols = max(1, int((w - 1) / (wmax + 1)))
        rows = int(math.ceil(float(len(completions)) / cols))
        for row in range(rows):
            s = ""
            for col in range(cols):
                i = col * rows + row
                if i < len(completions):
                    self.console.write(completions[i].ljust(wmax + 1))
            self.console.write("\n")
        if is_ironpython:
            self.prompt = sys.ps1
        self._print_prompt()

    def complete(self, e):  # (TAB)
        """Attempt to perform completion on the text before point. The
        actual completion performed is application-specific. The default is
        filename completion."""
        completions = self._get_completions()
        if completions:
            cprefix = commonprefix(completions)
            if len(cprefix) > 0:
                rep = [c for c in cprefix]
                point = self.l_buffer.point
                self.l_buffer[self.begidx : self.endidx] = rep
                self.l_buffer.point = point + len(rep) - (self.endidx - self.begidx)
            if len(completions) > 1:
                if self.show_all_if_ambiguous == "on":
                    self._display_completions(completions)
                else:
                    self._bell()
        else:
            self._bell()
        self.finalize()

    def possible_completions(self, e):  # (M-?)
        """List the possible completions of the text before point."""
        completions = self._get_completions()
        self._display_completions(completions)
        self.finalize()

    def insert_completions(self, e):  # (M-*)
        """Insert all completions of the text before point that would have
        been generated by possible-completions."""
        completions = self._get_completions()
        b = self.begidx
        e = self.endidx
        for comp in completions:
            rep = [c for c in comp]
            rep.append(" ")
            self.l_buffer[b:e] = rep
            b += len(rep)
            e = b
        self.line_cursor = b
        self.finalize()

    def menu_complete(self, e):  # ()
        """Similar to complete, but replaces the word to be completed with a
        single match from the list of possible completions. Repeated
        execution of menu-complete steps through the list of possible
        completions, inserting each match in turn. At the end of the list of
        completions, the bell is rung (subject to the setting of bell-style)
        and the original text is restored. An argument of n moves n
        positions forward in the list of matches; a negative argument may be
        used to move backward through the list. This command is intended to
        be bound to TAB, but is unbound by default."""
        self.finalize()

    # Methods below here are bindable emacs functions

    def insert_text(self, string):
        """Insert text into the command line."""
        self.l_buffer.insert_text(string, self.argument_reset)
        self.finalize()

    def beginning_of_line(self, e):  # (C-a)
        """Move to the start of the current line."""
        self.l_buffer.beginning_of_line()
        self.finalize()

    def end_of_line(self, e):  # (C-e)
        """Move to the end of the line."""
        self.l_buffer.end_of_line()
        self.finalize()

    def forward_char(self, e):  # (C-f)
        """Move forward a character."""
        self.l_buffer.forward_char(self.argument_reset)
        self.finalize()

    def backward_char(self, e):  # (C-b)
        """Move back a character."""
        self.l_buffer.backward_char(self.argument_reset)
        self.finalize()

    def forward_word(self, e):  # (M-f)
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.forward_word(self.argument_reset)
        self.finalize()

    def backward_word(self, e):  # (M-b)
        """Move back to the start of the current or previous word. Words are
        composed of letters and digits."""
        self.l_buffer.backward_word(self.argument_reset)
        self.finalize()

    def forward_word_end(self, e):  # ()
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.forward_word_end(self.argument_reset)
        self.finalize()

    def backward_word_end(self, e):  # ()
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.backward_word_end(self.argument_reset)
        self.finalize()

    # Movement with extend selection
    def beginning_of_line_extend_selection(self, e):
        """Move to the start of the current line."""
        self.l_buffer.beginning_of_line_extend_selection()
        self.finalize()

    def end_of_line_extend_selection(self, e):
        """Move to the end of the line."""
        self.l_buffer.end_of_line_extend_selection()
        self.finalize()

    def forward_char_extend_selection(self, e):
        """Move forward a character."""
        self.l_buffer.forward_char_extend_selection(self.argument_reset)
        self.finalize()

    def backward_char_extend_selection(self, e):
        """Move back a character."""
        self.l_buffer.backward_char_extend_selection(self.argument_reset)
        self.finalize()

    def forward_word_extend_selection(self, e):
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.forward_word_extend_selection(self.argument_reset)
        self.finalize()

    def backward_word_extend_selection(self, e):
        """Move back to the start of the current or previous word. Words are
        composed of letters and digits."""
        self.l_buffer.backward_word_extend_selection(self.argument_reset)
        self.finalize()

    def forward_word_end_extend_selection(self, e):
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.forward_word_end_extend_selection(self.argument_reset)
        self.finalize()

    def backward_word_end_extend_selection(self, e):
        """Move forward to the end of the next word. Words are composed of
        letters and digits."""
        self.l_buffer.forward_word_end_extend_selection(self.argument_reset)
        self.finalize()

    # Change case

    def upcase_word(self, e):  # (M-u)
        """Uppercase the current (or following) word. With a negative
        argument, uppercase the previous word, but do not move the cursor."""
        self.l_buffer.upcase_word()
        self.finalize()

    def downcase_word(self, e):  # (M-l)
        """Lowercase the current (or following) word. With a negative
        argument, lowercase the previous word, but do not move the cursor."""
        self.l_buffer.downcase_word()
        self.finalize()

    def capitalize_word(self, e):  # (M-c)
        """Capitalize the current (or following) word. With a negative
        argument, capitalize the previous word, but do not move the cursor."""
        self.l_buffer.capitalize_word()
        self.finalize()

    # #######

    def clear_screen(self, e):  # (C-l)
        """Clear the screen and redraw the current line, leaving the current
        line at the top of the screen."""
        self.console.page()
        self.finalize()

    def redraw_current_line(self, e):  # ()
        """Refresh the current line. By default, this is unbound."""
        self.finalize()

    def accept_line(self, e):  # (Newline or Return)
        """Accept the line regardless of where the cursor is. If this line
        is non-empty, it may be added to the history list for future recall
        with add_history(). If this line is a modified history line, the
        history line is restored to its original state."""
        self.finalize()
        return True

    def delete_char(self, e):  # (C-d)
        """Delete the character at point. If point is at the beginning of
        the line, there are no characters in the line, and the last
        character typed was not bound to delete-char, then return EOF."""
        self.l_buffer.delete_char(self.argument_reset)
        self.finalize()

    def backward_delete_char(self, e):  # (Rubout)
        """Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them."""
        self.l_buffer.backward_delete_char(self.argument_reset)
        self.finalize()

    def backward_delete_word(self, e):  # (Control-Rubout)
        """Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them."""
        self.l_buffer.backward_delete_word(self.argument_reset)
        self.finalize()

    def forward_delete_word(self, e):  # (Control-Delete)
        """Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them."""
        self.l_buffer.forward_delete_word(self.argument_reset)
        self.finalize()

    def delete_horizontal_space(self, e):  # ()
        """Delete all spaces and tabs around point. By default, this is unbound."""
        self.l_buffer.delete_horizontal_space()
        self.finalize()

    def self_insert(self, e):  # (a, b, A, 1, !, ...)
        """Insert yourself."""
        if (
            e.char and ord(e.char) != 0
        ):  # don't insert null character in buffer, can happen with dead keys.
            self.insert_text(e.char)
        self.finalize()

    # Paste from clipboard

    def paste(self, e):
        """Paste windows clipboard.
        Assume single line strip other lines and end of line markers and trailing spaces
        """  # (Control-v)
        if self.enable_win32_clipboard:
            txt = clipboard.get_clipboard_text_and_convert(False)
            txt = txt.split("\n")[0].strip("\r").strip("\n")
            log("paste: >%s<" % list(map(ord, txt)))
            self.insert_text(txt)
        self.finalize()

    def paste_mulitline_code(self, e):
        """Paste windows clipboard as multiline code.
        Removes any empty lines in the code"""
        reg = re.compile("\r?\n")
        if self.enable_win32_clipboard:
            txt = clipboard.get_clipboard_text_and_convert(False)
            t = reg.split(txt)
            t = [row for row in t if row.strip() != ""]  # remove empty lines
            if t != [""]:
                self.insert_text(t[0])
                self.add_history(self.l_buffer.copy())
                self.paste_line_buffer = t[1:]
                log("multi: >%s<" % self.paste_line_buffer)
                return True
            else:
                return False
        self.finalize()

    def ipython_paste(self, e):
        """Paste windows clipboard. If enable_ipython_paste_list_of_lists is
        True then try to convert tabseparated data to repr of list of lists or
        repr of array.
        If enable_ipython_paste_for_paths==True then change \\ to / and spaces
        to \\space"""
        if self.enable_win32_clipboard:
            txt = clipboard.get_clipboard_text_and_convert(
                self.enable_ipython_paste_list_of_lists
            )
            if self.enable_ipython_paste_for_paths:
                if len(txt) < 300 and ("\t" not in txt) and ("\n" not in txt):
                    txt = txt.replace("\\", "/").replace(" ", r"\ ")
            self.insert_text(txt)
        self.finalize()

    def copy_region_to_clipboard(self, e):  # ()
        """Copy the text in the region to the windows clipboard."""
        self.l_buffer.copy_region_to_clipboard()
        self.finalize()

    def copy_selection_to_clipboard(self, e):  # ()
        """Copy the text in the region to the windows clipboard."""
        self.l_buffer.copy_selection_to_clipboard()
        self.finalize()

    def cut_selection_to_clipboard(self, e):  # ()
        """Copy the text in the region to the windows clipboard."""
        self.l_buffer.cut_selection_to_clipboard()
        self.finalize()

    def dump_functions(self, e):  # ()
        """Print all of the functions and their key bindings to the Readline
        output stream. If a numeric argument is supplied, the output is
        formatted in such a way that it can be made part of an inputrc
        file. This command is unbound by default."""
        print()
        txt = "\n".join(self.rl_settings_to_string())
        print(txt)
        self._print_prompt()
        self.finalize()


def commonprefix(m):
    "Given a list of pathnames, returns the longest common leading component"
    if not m:
        return ""
    prefix = m[0]
    for item in m:
        for i in range(len(prefix)):
            if prefix[: i + 1].lower() != item[: i + 1].lower():
                prefix = prefix[:i]
                if i == 0:
                    return ""
                break
    return prefix

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\version.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.version import parse, Version
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Callable, NamedTuple, SupportsInt, Tuple, Union

from ._structures import Infinity, InfinityType, NegativeInfinity, NegativeInfinityType

__all__ = ["VERSION_PATTERN", "InvalidVersion", "Version", "parse"]

LocalType = Tuple[Union[int, str], ...]

CmpPrePostDevType = Union[InfinityType, NegativeInfinityType, Tuple[str, int]]
CmpLocalType = Union[
    NegativeInfinityType,
    Tuple[Union[Tuple[int, str], Tuple[NegativeInfinityType, Union[int, str]]], ...],
]
CmpKey = Tuple[
    int,
    Tuple[int, ...],
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpLocalType,
]
VersionComparisonMethod = Callable[[CmpKey, CmpKey], bool]


class _Version(NamedTuple):
    epoch: int
    release: tuple[int, ...]
    dev: tuple[str, int] | None
    pre: tuple[str, int] | None
    post: tuple[str, int] | None
    local: LocalType | None


def parse(version: str) -> Version:
    """Parse the given version string.

    >>> parse('1.0.dev1')
    <Version('1.0.dev1')>

    :param version: The version string to parse.
    :raises InvalidVersion: When the version string is not a valid version.
    """
    return Version(version)


class InvalidVersion(ValueError):
    """Raised when a version string is not a valid version.

    >>> Version("invalid")
    Traceback (most recent call last):
        ...
    packaging.version.InvalidVersion: Invalid version: 'invalid'
    """


class _BaseVersion:
    _key: tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    # Please keep the duplicated `isinstance` check
    # in the six comparisons hereunder
    # unless you find a way to avoid adding overhead function calls.
    def __lt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key == other._key

    def __ge__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key >= other._key

    def __gt__(self, other: _BaseVersion) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key != other._key


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_PATTERN = _VERSION_PATTERN
"""
A string containing the regular expression used to match a valid version.

The pattern is not anchored at either end, and is intended for embedding in larger
expressions (for example, matching a version number as part of a file name). The
regular expression should be compiled with the ``re.VERBOSE`` and ``re.IGNORECASE``
flags set.

:meta hide-value:
"""


class Version(_BaseVersion):
    """This class abstracts handling of a project's versions.

    A :class:`Version` instance is comparison aware and can be compared and
    sorted using the standard Python interfaces.

    >>> v1 = Version("1.0a5")
    >>> v2 = Version("1.0")
    >>> v1
    <Version('1.0a5')>
    >>> v2
    <Version('1.0')>
    >>> v1 < v2
    True
    >>> v1 == v2
    False
    >>> v1 > v2
    False
    >>> v1 >= v2
    False
    >>> v1 <= v2
    True
    """

    _regex = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)
    _key: CmpKey

    def __init__(self, version: str) -> None:
        """Initialize a Version object.

        :param version:
            The string representation of a version which will be parsed and normalized
            before use.
        :raises InvalidVersion:
            If the ``version`` does not conform to PEP 440 in any way then this
            exception will be raised.
        """

        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: {version!r}")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(match.group("pre_l"), match.group("pre_n")),
            post=_parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=_parse_letter_version(match.group("dev_l"), match.group("dev_n")),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        """A representation of the Version that shows all internal state.

        >>> Version('1.0.0')
        <Version('1.0.0')>
        """
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        """A string representation of the version that can be round-tripped.

        >>> str(Version("1.0a5"))
        '1.0a5'
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            parts.append(f".post{self.post}")

        # Development release
        if self.dev is not None:
            parts.append(f".dev{self.dev}")

        # Local version segment
        if self.local is not None:
            parts.append(f"+{self.local}")

        return "".join(parts)

    @property
    def epoch(self) -> int:
        """The epoch of the version.

        >>> Version("2.0.0").epoch
        0
        >>> Version("1!2.0.0").epoch
        1
        """
        return self._version.epoch

    @property
    def release(self) -> tuple[int, ...]:
        """The components of the "release" segment of the version.

        >>> Version("1.2.3").release
        (1, 2, 3)
        >>> Version("2.0.0").release
        (2, 0, 0)
        >>> Version("1!2.0.0.post0").release
        (2, 0, 0)

        Includes trailing zeroes but not the epoch or any pre-release / development /
        post-release suffixes.
        """
        return self._version.release

    @property
    def pre(self) -> tuple[str, int] | None:
        """The pre-release segment of the version.

        >>> print(Version("1.2.3").pre)
        None
        >>> Version("1.2.3a1").pre
        ('a', 1)
        >>> Version("1.2.3b1").pre
        ('b', 1)
        >>> Version("1.2.3rc1").pre
        ('rc', 1)
        """
        return self._version.pre

    @property
    def post(self) -> int | None:
        """The post-release number of the version.

        >>> print(Version("1.2.3").post)
        None
        >>> Version("1.2.3.post1").post
        1
        """
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> int | None:
        """The development number of the version.

        >>> print(Version("1.2.3").dev)
        None
        >>> Version("1.2.3.dev1").dev
        1
        """
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> str | None:
        """The local version segment of the version.

        >>> print(Version("1.2.3").local)
        None
        >>> Version("1.2.3+abc").local
        'abc'
        """
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        """The public portion of the version.

        >>> Version("1.2.3").public
        '1.2.3'
        >>> Version("1.2.3+abc").public
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").public
        '1!1.2.3.dev1'
        """
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        """The "base version" of the version.

        >>> Version("1.2.3").base_version
        '1.2.3'
        >>> Version("1.2.3+abc").base_version
        '1.2.3'
        >>> Version("1!1.2.3dev1+abc").base_version
        '1!1.2.3'

        The "base version" is the public version of the project without any pre or post
        release markers.
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        """Whether this version is a pre-release.

        >>> Version("1.2.3").is_prerelease
        False
        >>> Version("1.2.3a1").is_prerelease
        True
        >>> Version("1.2.3b1").is_prerelease
        True
        >>> Version("1.2.3rc1").is_prerelease
        True
        >>> Version("1.2.3dev1").is_prerelease
        True
        """
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        """Whether this version is a post-release.

        >>> Version("1.2.3").is_postrelease
        False
        >>> Version("1.2.3.post1").is_postrelease
        True
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """Whether this version is a development release.

        >>> Version("1.2.3").is_devrelease
        False
        >>> Version("1.2.3.dev1").is_devrelease
        True
        """
        return self.dev is not None

    @property
    def major(self) -> int:
        """The first item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").major
        1
        """
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        """The second item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").minor
        2
        >>> Version("1").minor
        0
        """
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        """The third item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").micro
        3
        >>> Version("1").micro
        0
        """
        return self.release[2] if len(self.release) >= 3 else 0


class _TrimmedRelease(Version):
    @property
    def release(self) -> tuple[int, ...]:
        """
        Release segment without any trailing zeros.

        >>> _TrimmedRelease('1.0.0').release
        (1,)
        >>> _TrimmedRelease('0.0').release
        (0,)
        """
        rel = super().release
        nonzeros = (index for index, val in enumerate(rel) if val)
        last_nonzero = max(nonzeros, default=0)
        return rel[: last_nonzero + 1]


def _parse_letter_version(
    letter: str | None, number: str | bytes | SupportsInt | None
) -> tuple[str, int] | None:
    if letter:
        # We consider there to be an implicit 0 in a pre-release if there is
        # not a numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)

    assert not letter
    if number:
        # We assume if we are given a number, but we are not given a letter
        # then this is using the implicit post release syntax (e.g. 1.0-1)
        letter = "post"

        return letter, int(number)

    return None


_local_version_separators = re.compile(r"[\._-]")


def _parse_local_version(local: str | None) -> LocalType | None:
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_separators.split(local)
        )
    return None


def _cmpkey(
    epoch: int,
    release: tuple[int, ...],
    pre: tuple[str, int] | None,
    post: tuple[str, int] | None,
    dev: tuple[str, int] | None,
    local: LocalType | None,
) -> CmpKey:
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non zero, then take the rest
    # re-reverse it back into the correct order and make it a tuple and use
    # that for our sorting key.
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre segment, but we _only_ want to do this
    # if there is not a pre or a post segment. If we have one of those then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        _pre: CmpPrePostDevType = NegativeInfinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        _pre = Infinity
    else:
        _pre = pre

    # Versions without a post segment should sort before those with one.
    if post is None:
        _post: CmpPrePostDevType = NegativeInfinity

    else:
        _post = post

    # Versions without a development segment should sort after those with one.
    if dev is None:
        _dev: CmpPrePostDevType = Infinity

    else:
        _dev = dev

    if local is None:
        # Versions without a local segment should sort before those with one.
        _local: CmpLocalType = NegativeInfinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alpha numeric segments sort before numeric segments
        # - Alpha numeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        _local = tuple(
            (i, "") if isinstance(i, int) else (NegativeInfinity, i) for i in local
        )

    return epoch, _release, _pre, _post, _dev, _local

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\ntdll.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
Wrapper for ntdll.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
_all.add("peb_teb")
# ==============================================================================

from winappdbg.win32.peb_teb import *

# --- Types --------------------------------------------------------------------

SYSDBG_COMMAND = DWORD
PROCESSINFOCLASS = DWORD
THREADINFOCLASS = DWORD
FILE_INFORMATION_CLASS = DWORD

# --- Constants ----------------------------------------------------------------

# DEP flags for ProcessExecuteFlags
MEM_EXECUTE_OPTION_ENABLE = 1
MEM_EXECUTE_OPTION_DISABLE = 2
MEM_EXECUTE_OPTION_ATL7_THUNK_EMULATION = 4
MEM_EXECUTE_OPTION_PERMANENT = 8

# SYSTEM_INFORMATION_CLASS
# http://www.informit.com/articles/article.aspx?p=22442&seqNum=4
SystemBasicInformation = 1  # 0x002C
SystemProcessorInformation = 2  # 0x000C
SystemPerformanceInformation = 3  # 0x0138
SystemTimeInformation = 4  # 0x0020
SystemPathInformation = 5  # not implemented
SystemProcessInformation = 6  # 0x00F8 + per process
SystemCallInformation = 7  # 0x0018 + (n * 0x0004)
SystemConfigurationInformation = 8  # 0x0018
SystemProcessorCounters = 9  # 0x0030 per cpu
SystemGlobalFlag = 10  # 0x0004
SystemInfo10 = 11  # not implemented
SystemModuleInformation = 12  # 0x0004 + (n * 0x011C)
SystemLockInformation = 13  # 0x0004 + (n * 0x0024)
SystemInfo13 = 14  # not implemented
SystemPagedPoolInformation = 15  # checked build only
SystemNonPagedPoolInformation = 16  # checked build only
SystemHandleInformation = 17  # 0x0004 + (n * 0x0010)
SystemObjectInformation = 18  # 0x0038+ + (n * 0x0030+)
SystemPagefileInformation = 19  # 0x0018+ per page file
SystemInstemulInformation = 20  # 0x0088
SystemInfo20 = 21  # invalid info class
SystemCacheInformation = 22  # 0x0024
SystemPoolTagInformation = 23  # 0x0004 + (n * 0x001C)
SystemProcessorStatistics = 24  # 0x0000, or 0x0018 per cpu
SystemDpcInformation = 25  # 0x0014
SystemMemoryUsageInformation1 = 26  # checked build only
SystemLoadImage = 27  # 0x0018, set mode only
SystemUnloadImage = 28  # 0x0004, set mode only
SystemTimeAdjustmentInformation = 29  # 0x000C, 0x0008 writeable
SystemMemoryUsageInformation2 = 30  # checked build only
SystemInfo30 = 31  # checked build only
SystemInfo31 = 32  # checked build only
SystemCrashDumpInformation = 33  # 0x0004
SystemExceptionInformation = 34  # 0x0010
SystemCrashDumpStateInformation = 35  # 0x0008
SystemDebuggerInformation = 36  # 0x0002
SystemThreadSwitchInformation = 37  # 0x0030
SystemRegistryQuotaInformation = 38  # 0x000C
SystemLoadDriver = 39  # 0x0008, set mode only
SystemPrioritySeparationInformation = 40  # 0x0004, set mode only
SystemInfo40 = 41  # not implemented
SystemInfo41 = 42  # not implemented
SystemInfo42 = 43  # invalid info class
SystemInfo43 = 44  # invalid info class
SystemTimeZoneInformation = 45  # 0x00AC
SystemLookasideInformation = 46  # n * 0x0020
# info classes specific to Windows 2000
# WTS = Windows Terminal Server
SystemSetTimeSlipEvent = 47  # set mode only
SystemCreateSession = 48  # WTS, set mode only
SystemDeleteSession = 49  # WTS, set mode only
SystemInfo49 = 50  # invalid info class
SystemRangeStartInformation = 51  # 0x0004
SystemVerifierInformation = 52  # 0x0068
SystemAddVerifier = 53  # set mode only
SystemSessionProcessesInformation = 54  # WTS

# NtQueryInformationProcess constants (from MSDN)
##ProcessBasicInformation = 0
##ProcessDebugPort        = 7
##ProcessWow64Information = 26
##ProcessImageFileName    = 27

# PROCESS_INFORMATION_CLASS
# http://undocumented.ntinternals.net/UserMode/Undocumented%20Functions/NT%20Objects/Process/PROCESS_INFORMATION_CLASS.html
ProcessBasicInformation = 0
ProcessQuotaLimits = 1
ProcessIoCounters = 2
ProcessVmCounters = 3
ProcessTimes = 4
ProcessBasePriority = 5
ProcessRaisePriority = 6
ProcessDebugPort = 7
ProcessExceptionPort = 8
ProcessAccessToken = 9
ProcessLdtInformation = 10
ProcessLdtSize = 11
ProcessDefaultHardErrorMode = 12
ProcessIoPortHandlers = 13
ProcessPooledUsageAndLimits = 14
ProcessWorkingSetWatch = 15
ProcessUserModeIOPL = 16
ProcessEnableAlignmentFaultFixup = 17
ProcessPriorityClass = 18
ProcessWx86Information = 19
ProcessHandleCount = 20
ProcessAffinityMask = 21
ProcessPriorityBoost = 22

ProcessWow64Information = 26
ProcessImageFileName = 27

# http://www.codeproject.com/KB/security/AntiReverseEngineering.aspx
ProcessDebugObjectHandle = 30

ProcessExecuteFlags = 34

# THREAD_INFORMATION_CLASS
ThreadBasicInformation = 0
ThreadTimes = 1
ThreadPriority = 2
ThreadBasePriority = 3
ThreadAffinityMask = 4
ThreadImpersonationToken = 5
ThreadDescriptorTableEntry = 6
ThreadEnableAlignmentFaultFixup = 7
ThreadEventPair = 8
ThreadQuerySetWin32StartAddress = 9
ThreadZeroTlsCell = 10
ThreadPerformanceCount = 11
ThreadAmILastThread = 12
ThreadIdealProcessor = 13
ThreadPriorityBoost = 14
ThreadSetTlsArrayAddress = 15
ThreadIsIoPending = 16
ThreadHideFromDebugger = 17

# OBJECT_INFORMATION_CLASS
ObjectBasicInformation = 0
ObjectNameInformation = 1
ObjectTypeInformation = 2
ObjectAllTypesInformation = 3
ObjectHandleInformation = 4

# FILE_INFORMATION_CLASS
FileDirectoryInformation = 1
FileFullDirectoryInformation = 2
FileBothDirectoryInformation = 3
FileBasicInformation = 4
FileStandardInformation = 5
FileInternalInformation = 6
FileEaInformation = 7
FileAccessInformation = 8
FileNameInformation = 9
FileRenameInformation = 10
FileLinkInformation = 11
FileNamesInformation = 12
FileDispositionInformation = 13
FilePositionInformation = 14
FileFullEaInformation = 15
FileModeInformation = 16
FileAlignmentInformation = 17
FileAllInformation = 18
FileAllocationInformation = 19
FileEndOfFileInformation = 20
FileAlternateNameInformation = 21
FileStreamInformation = 22
FilePipeInformation = 23
FilePipeLocalInformation = 24
FilePipeRemoteInformation = 25
FileMailslotQueryInformation = 26
FileMailslotSetInformation = 27
FileCompressionInformation = 28
FileCopyOnWriteInformation = 29
FileCompletionInformation = 30
FileMoveClusterInformation = 31
FileQuotaInformation = 32
FileReparsePointInformation = 33
FileNetworkOpenInformation = 34
FileObjectIdInformation = 35
FileTrackingInformation = 36
FileOleDirectoryInformation = 37
FileContentIndexInformation = 38
FileInheritContentIndexInformation = 37
FileOleInformation = 39
FileMaximumInformation = 40

# From http://www.nirsoft.net/kernel_struct/vista/EXCEPTION_DISPOSITION.html
# typedef enum _EXCEPTION_DISPOSITION
# {
#          ExceptionContinueExecution = 0,
#          ExceptionContinueSearch = 1,
#          ExceptionNestedException = 2,
#          ExceptionCollidedUnwind = 3
# } EXCEPTION_DISPOSITION;
ExceptionContinueExecution = 0
ExceptionContinueSearch = 1
ExceptionNestedException = 2
ExceptionCollidedUnwind = 3

# --- PROCESS_BASIC_INFORMATION structure --------------------------------------

# From MSDN:
#
# typedef struct _PROCESS_BASIC_INFORMATION {
#     PVOID Reserved1;
#     PPEB PebBaseAddress;
#     PVOID Reserved2[2];
#     ULONG_PTR UniqueProcessId;
#     PVOID Reserved3;
# } PROCESS_BASIC_INFORMATION;
##class PROCESS_BASIC_INFORMATION(Structure):
##    _fields_ = [
##        ("Reserved1",       PVOID),
##        ("PebBaseAddress",  PPEB),
##        ("Reserved2",       PVOID * 2),
##        ("UniqueProcessId", ULONG_PTR),
##        ("Reserved3",       PVOID),
##]

# From http://catch22.net/tuts/tips2
# (Only valid for 32 bits)
#
# typedef struct
# {
#     ULONG      ExitStatus;
#     PVOID      PebBaseAddress;
#     ULONG      AffinityMask;
#     ULONG      BasePriority;
#     ULONG_PTR  UniqueProcessId;
#     ULONG_PTR  InheritedFromUniqueProcessId;
# } PROCESS_BASIC_INFORMATION;


# My own definition follows:
class PROCESS_BASIC_INFORMATION(Structure):
    _fields_ = [
        ("ExitStatus", SIZE_T),
        ("PebBaseAddress", PVOID),  # PPEB
        ("AffinityMask", KAFFINITY),
        ("BasePriority", SDWORD),
        ("UniqueProcessId", ULONG_PTR),
        ("InheritedFromUniqueProcessId", ULONG_PTR),
    ]


# --- THREAD_BASIC_INFORMATION structure ---------------------------------------


# From http://undocumented.ntinternals.net/UserMode/Structures/THREAD_BASIC_INFORMATION.html
#
# typedef struct _THREAD_BASIC_INFORMATION {
#   NTSTATUS ExitStatus;
#   PVOID TebBaseAddress;
#   CLIENT_ID ClientId;
#   KAFFINITY AffinityMask;
#   KPRIORITY Priority;
#   KPRIORITY BasePriority;
# } THREAD_BASIC_INFORMATION, *PTHREAD_BASIC_INFORMATION;
class THREAD_BASIC_INFORMATION(Structure):
    _fields_ = [
        ("ExitStatus", NTSTATUS),
        ("TebBaseAddress", PVOID),  # PTEB
        ("ClientId", CLIENT_ID),
        ("AffinityMask", KAFFINITY),
        ("Priority", SDWORD),
        ("BasePriority", SDWORD),
    ]


# --- FILE_NAME_INFORMATION structure ------------------------------------------


# typedef struct _FILE_NAME_INFORMATION {
#     ULONG FileNameLength;
#     WCHAR FileName[1];
# } FILE_NAME_INFORMATION, *PFILE_NAME_INFORMATION;
class FILE_NAME_INFORMATION(Structure):
    _fields_ = [
        ("FileNameLength", ULONG),
        ("FileName", WCHAR * 1),
    ]


# --- SYSDBG_MSR structure and constants ---------------------------------------

SysDbgReadMsr = 16
SysDbgWriteMsr = 17


class SYSDBG_MSR(Structure):
    _fields_ = [
        ("Address", ULONG),
        ("Data", ULONGLONG),
    ]


# --- IO_STATUS_BLOCK structure ------------------------------------------------


# typedef struct _IO_STATUS_BLOCK {
#     union {
#         NTSTATUS Status;
#         PVOID Pointer;
#     };
#     ULONG_PTR Information;
# } IO_STATUS_BLOCK, *PIO_STATUS_BLOCK;
class IO_STATUS_BLOCK(Structure):
    _fields_ = [
        ("Status", NTSTATUS),
        ("Information", ULONG_PTR),
    ]

    def __get_Pointer(self):
        return PVOID(self.Status)

    def __set_Pointer(self, ptr):
        self.Status = ptr.value

    Pointer = property(__get_Pointer, __set_Pointer)


PIO_STATUS_BLOCK = POINTER(IO_STATUS_BLOCK)

# --- ntdll.dll ----------------------------------------------------------------


# ULONG WINAPI RtlNtStatusToDosError(
#   __in  NTSTATUS Status
# );
def RtlNtStatusToDosError(Status):
    _RtlNtStatusToDosError = windll.ntdll.RtlNtStatusToDosError
    _RtlNtStatusToDosError.argtypes = [NTSTATUS]
    _RtlNtStatusToDosError.restype = ULONG
    return _RtlNtStatusToDosError(Status)


# NTSYSAPI NTSTATUS NTAPI NtSystemDebugControl(
#   IN SYSDBG_COMMAND Command,
#   IN PVOID InputBuffer OPTIONAL,
#   IN ULONG InputBufferLength,
#   OUT PVOID OutputBuffer OPTIONAL,
#   IN ULONG OutputBufferLength,
#   OUT PULONG ReturnLength OPTIONAL
# );
def NtSystemDebugControl(Command, InputBuffer=None, InputBufferLength=None, OutputBuffer=None, OutputBufferLength=None):
    _NtSystemDebugControl = windll.ntdll.NtSystemDebugControl
    _NtSystemDebugControl.argtypes = [SYSDBG_COMMAND, PVOID, ULONG, PVOID, ULONG, PULONG]
    _NtSystemDebugControl.restype = NTSTATUS

    # Validate the input buffer
    if InputBuffer is None:
        if InputBufferLength is None:
            InputBufferLength = 0
        else:
            raise ValueError("Invalid call to NtSystemDebugControl: " "input buffer length given but no input buffer!")
    else:
        if InputBufferLength is None:
            InputBufferLength = sizeof(InputBuffer)
        InputBuffer = byref(InputBuffer)

    # Validate the output buffer
    if OutputBuffer is None:
        if OutputBufferLength is None:
            OutputBufferLength = 0
        else:
            OutputBuffer = ctypes.create_string_buffer("", OutputBufferLength)
    elif OutputBufferLength is None:
        OutputBufferLength = sizeof(OutputBuffer)

    # Make the call (with an output buffer)
    if OutputBuffer is not None:
        ReturnLength = ULONG(0)
        ntstatus = _NtSystemDebugControl(
            Command, InputBuffer, InputBufferLength, byref(OutputBuffer), OutputBufferLength, byref(ReturnLength)
        )
        if ntstatus != 0:
            raise ctypes.WinError(RtlNtStatusToDosError(ntstatus))
        ReturnLength = ReturnLength.value
        if ReturnLength != OutputBufferLength:
            raise ctypes.WinError(ERROR_BAD_LENGTH)
        return OutputBuffer, ReturnLength

    # Make the call (without an output buffer)
    ntstatus = _NtSystemDebugControl(Command, InputBuffer, InputBufferLength, OutputBuffer, OutputBufferLength, None)
    if ntstatus != 0:
        raise ctypes.WinError(RtlNtStatusToDosError(ntstatus))


ZwSystemDebugControl = NtSystemDebugControl


# NTSTATUS WINAPI NtQueryInformationProcess(
#   __in       HANDLE ProcessHandle,
#   __in       PROCESSINFOCLASS ProcessInformationClass,
#   __out      PVOID ProcessInformation,
#   __in       ULONG ProcessInformationLength,
#   __out_opt  PULONG ReturnLength
# );
def NtQueryInformationProcess(ProcessHandle, ProcessInformationClass, ProcessInformationLength=None):
    _NtQueryInformationProcess = windll.ntdll.NtQueryInformationProcess
    _NtQueryInformationProcess.argtypes = [HANDLE, PROCESSINFOCLASS, PVOID, ULONG, PULONG]
    _NtQueryInformationProcess.restype = NTSTATUS
    if ProcessInformationLength is not None:
        ProcessInformation = ctypes.create_string_buffer("", ProcessInformationLength)
    else:
        if ProcessInformationClass == ProcessBasicInformation:
            ProcessInformation = PROCESS_BASIC_INFORMATION()
            ProcessInformationLength = sizeof(PROCESS_BASIC_INFORMATION)
        elif ProcessInformationClass == ProcessImageFileName:
            unicode_buffer = ctypes.create_unicode_buffer("", 0x1000)
            ProcessInformation = UNICODE_STRING(0, 0x1000, addressof(unicode_buffer))
            ProcessInformationLength = sizeof(UNICODE_STRING)
        elif ProcessInformationClass in (
            ProcessDebugPort,
            ProcessWow64Information,
            ProcessWx86Information,
            ProcessHandleCount,
            ProcessPriorityBoost,
        ):
            ProcessInformation = DWORD()
            ProcessInformationLength = sizeof(DWORD)
        else:
            raise Exception("Unknown ProcessInformationClass, use an explicit ProcessInformationLength value instead")
    ReturnLength = ULONG(0)
    ntstatus = _NtQueryInformationProcess(
        ProcessHandle, ProcessInformationClass, byref(ProcessInformation), ProcessInformationLength, byref(ReturnLength)
    )
    if ntstatus != 0:
        raise ctypes.WinError(RtlNtStatusToDosError(ntstatus))
    if ProcessInformationClass == ProcessBasicInformation:
        retval = ProcessInformation
    elif ProcessInformationClass in (
        ProcessDebugPort,
        ProcessWow64Information,
        ProcessWx86Information,
        ProcessHandleCount,
        ProcessPriorityBoost,
    ):
        retval = ProcessInformation.value
    elif ProcessInformationClass == ProcessImageFileName:
        vptr = ctypes.c_void_p(ProcessInformation.Buffer)
        cptr = ctypes.cast(vptr, ctypes.c_wchar * ProcessInformation.Length)
        retval = cptr.contents.raw
    else:
        retval = ProcessInformation.raw[: ReturnLength.value]
    return retval


ZwQueryInformationProcess = NtQueryInformationProcess


# NTSTATUS WINAPI NtQueryInformationThread(
#   __in       HANDLE ThreadHandle,
#   __in       THREADINFOCLASS ThreadInformationClass,
#   __out      PVOID ThreadInformation,
#   __in       ULONG ThreadInformationLength,
#   __out_opt  PULONG ReturnLength
# );
def NtQueryInformationThread(ThreadHandle, ThreadInformationClass, ThreadInformationLength=None):
    _NtQueryInformationThread = windll.ntdll.NtQueryInformationThread
    _NtQueryInformationThread.argtypes = [HANDLE, THREADINFOCLASS, PVOID, ULONG, PULONG]
    _NtQueryInformationThread.restype = NTSTATUS
    if ThreadInformationLength is not None:
        ThreadInformation = ctypes.create_string_buffer("", ThreadInformationLength)
    else:
        if ThreadInformationClass == ThreadBasicInformation:
            ThreadInformation = THREAD_BASIC_INFORMATION()
        elif ThreadInformationClass == ThreadHideFromDebugger:
            ThreadInformation = BOOLEAN()
        elif ThreadInformationClass == ThreadQuerySetWin32StartAddress:
            ThreadInformation = PVOID()
        elif ThreadInformationClass in (ThreadAmILastThread, ThreadPriorityBoost):
            ThreadInformation = DWORD()
        elif ThreadInformationClass == ThreadPerformanceCount:
            ThreadInformation = LONGLONG()  # LARGE_INTEGER
        else:
            raise Exception("Unknown ThreadInformationClass, use an explicit ThreadInformationLength value instead")
        ThreadInformationLength = sizeof(ThreadInformation)
    ReturnLength = ULONG(0)
    ntstatus = _NtQueryInformationThread(
        ThreadHandle, ThreadInformationClass, byref(ThreadInformation), ThreadInformationLength, byref(ReturnLength)
    )
    if ntstatus != 0:
        raise ctypes.WinError(RtlNtStatusToDosError(ntstatus))
    if ThreadInformationClass == ThreadBasicInformation:
        retval = ThreadInformation
    elif ThreadInformationClass == ThreadHideFromDebugger:
        retval = bool(ThreadInformation.value)
    elif ThreadInformationClass in (ThreadQuerySetWin32StartAddress, ThreadAmILastThread, ThreadPriorityBoost, ThreadPerformanceCount):
        retval = ThreadInformation.value
    else:
        retval = ThreadInformation.raw[: ReturnLength.value]
    return retval


ZwQueryInformationThread = NtQueryInformationThread


# NTSTATUS
#   NtQueryInformationFile(
#     IN HANDLE  FileHandle,
#     OUT PIO_STATUS_BLOCK  IoStatusBlock,
#     OUT PVOID  FileInformation,
#     IN ULONG  Length,
#     IN FILE_INFORMATION_CLASS  FileInformationClass
#     );
def NtQueryInformationFile(FileHandle, FileInformationClass, FileInformation, Length):
    _NtQueryInformationFile = windll.ntdll.NtQueryInformationFile
    _NtQueryInformationFile.argtypes = [HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, DWORD]
    _NtQueryInformationFile.restype = NTSTATUS
    IoStatusBlock = IO_STATUS_BLOCK()
    ntstatus = _NtQueryInformationFile(FileHandle, byref(IoStatusBlock), byref(FileInformation), Length, FileInformationClass)
    if ntstatus != 0:
        raise ctypes.WinError(RtlNtStatusToDosError(ntstatus))
    return IoStatusBlock


ZwQueryInformationFile = NtQueryInformationFile


# DWORD STDCALL CsrGetProcessId (VOID);
def CsrGetProcessId():
    _CsrGetProcessId = windll.ntdll.CsrGetProcessId
    _CsrGetProcessId.argtypes = []
    _CsrGetProcessId.restype = DWORD
    return _CsrGetProcessId()


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\datadog\datadog.py ===
"""
DataDog Integration - sends logs to /api/v2/log

DD Reference API: https://docs.datadoghq.com/api/latest/logs

`async_log_success_event` - used by litellm proxy to send logs to datadog
`log_success_event` - sync version of logging to DataDog, only used on litellm Python SDK, if user opts in to using sync functions

async_log_success_event:  will store batch of DD_MAX_BATCH_SIZE in memory and flush to Datadog once it reaches DD_MAX_BATCH_SIZE or every 5 seconds

async_service_failure_hook: Logs failures from Redis, Postgres (Adjacent systems), as 'WARNING' on DataDog

For batching specific details see CustomBatchLogger class
"""

import asyncio
import datetime
import json
import os
import traceback
import uuid
from datetime import datetime as datetimeObj
from typing import Any, List, Optional, Union

import httpx
from httpx import Response

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.base_health_check import IntegrationHealthCheckStatus
from litellm.types.integrations.datadog import *
from litellm.types.services import ServiceLoggerPayload, ServiceTypes
from litellm.types.utils import StandardLoggingPayload

from ..additional_logging_utils import AdditionalLoggingUtils

# max number of logs DD API can accept


# specify what ServiceTypes are logged as success events to DD. (We don't want to spam DD traces with large number of service types)
DD_LOGGED_SUCCESS_SERVICE_TYPES = [
    ServiceTypes.RESET_BUDGET_JOB,
]


class DataDogLogger(
    CustomBatchLogger,
    AdditionalLoggingUtils,
):
    # Class variables or attributes
    def __init__(
        self,
        **kwargs,
    ):
        """
        Initializes the datadog logger, checks if the correct env variables are set

        Required environment variables:
        `DD_API_KEY` - your datadog api key
        `DD_SITE` - your datadog site, example = `"us5.datadoghq.com"`
        """
        try:
            verbose_logger.debug("Datadog: in init datadog logger")
            # check if the correct env variables are set
            if os.getenv("DD_API_KEY", None) is None:
                raise Exception("DD_API_KEY is not set, set 'DD_API_KEY=<>")
            if os.getenv("DD_SITE", None) is None:
                raise Exception("DD_SITE is not set in .env, set 'DD_SITE=<>")
            self.async_client = get_async_httpx_client(
                llm_provider=httpxSpecialProvider.LoggingCallback
            )
            self.DD_API_KEY = os.getenv("DD_API_KEY")
            self.intake_url = (
                f"https://http-intake.logs.{os.getenv('DD_SITE')}/api/v2/logs"
            )

            ###################################
            # OPTIONAL -only used for testing
            dd_base_url: Optional[str] = (
                os.getenv("_DATADOG_BASE_URL")
                or os.getenv("DATADOG_BASE_URL")
                or os.getenv("DD_BASE_URL")
            )
            if dd_base_url is not None:
                self.intake_url = f"{dd_base_url}/api/v2/logs"
            ###################################
            self.sync_client = _get_httpx_client()
            asyncio.create_task(self.periodic_flush())
            self.flush_lock = asyncio.Lock()
            super().__init__(
                **kwargs, flush_lock=self.flush_lock, batch_size=DD_MAX_BATCH_SIZE
            )
        except Exception as e:
            verbose_logger.exception(
                f"Datadog: Got exception on init Datadog client {str(e)}"
            )
            raise e

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Async Log success events to Datadog

        - Creates a Datadog payload
        - Adds the Payload to the in memory logs queue
        - Payload is flushed every 10 seconds or when batch size is greater than 100


        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        try:
            verbose_logger.debug(
                "Datadog: Logging - Enters logging function for model %s", kwargs
            )
            await self._log_async_event(kwargs, response_obj, start_time, end_time)

        except Exception as e:
            verbose_logger.exception(
                f"Datadog Layer Error - {str(e)}\n{traceback.format_exc()}"
            )
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                "Datadog: Logging - Enters logging function for model %s", kwargs
            )
            await self._log_async_event(kwargs, response_obj, start_time, end_time)

        except Exception as e:
            verbose_logger.exception(
                f"Datadog Layer Error - {str(e)}\n{traceback.format_exc()}"
            )
            pass

    async def async_send_batch(self):
        """
        Sends the in memory logs queue to datadog api

        Logs sent to /api/v2/logs

        DD Ref: https://docs.datadoghq.com/api/latest/logs/

        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        try:
            if not self.log_queue:
                verbose_logger.exception("Datadog: log_queue does not exist")
                return

            verbose_logger.debug(
                "Datadog - about to flush %s events on %s",
                len(self.log_queue),
                self.intake_url,
            )

            response = await self.async_send_compressed_data(self.log_queue)
            if response.status_code == 413:
                verbose_logger.exception(DD_ERRORS.DATADOG_413_ERROR.value)
                return

            response.raise_for_status()
            if response.status_code != 202:
                raise Exception(
                    f"Response from datadog API status_code: {response.status_code}, text: {response.text}"
                )

            verbose_logger.debug(
                "Datadog: Response from datadog API status_code: %s, text: %s",
                response.status_code,
                response.text,
            )
        except Exception as e:
            verbose_logger.exception(
                f"Datadog Error sending batch API - {str(e)}\n{traceback.format_exc()}"
            )

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Sync Log success events to Datadog

        - Creates a Datadog payload
        - instantly logs it on DD API
        """
        try:
            if litellm.datadog_use_v1 is True:
                dd_payload = self._create_v0_logging_payload(
                    kwargs=kwargs,
                    response_obj=response_obj,
                    start_time=start_time,
                    end_time=end_time,
                )
            else:
                dd_payload = self.create_datadog_logging_payload(
                    kwargs=kwargs,
                    response_obj=response_obj,
                    start_time=start_time,
                    end_time=end_time,
                )

            response = self.sync_client.post(
                url=self.intake_url,
                json=dd_payload,  # type: ignore
                headers={
                    "DD-API-KEY": self.DD_API_KEY,
                },
            )

            response.raise_for_status()
            if response.status_code != 202:
                raise Exception(
                    f"Response from datadog API status_code: {response.status_code}, text: {response.text}"
                )

            verbose_logger.debug(
                "Datadog: Response from datadog API status_code: %s, text: %s",
                response.status_code,
                response.text,
            )

        except Exception as e:
            verbose_logger.exception(
                f"Datadog Layer Error - {str(e)}\n{traceback.format_exc()}"
            )
            pass
        pass

    async def _log_async_event(self, kwargs, response_obj, start_time, end_time):
        dd_payload = self.create_datadog_logging_payload(
            kwargs=kwargs,
            response_obj=response_obj,
            start_time=start_time,
            end_time=end_time,
        )

        self.log_queue.append(dd_payload)
        verbose_logger.debug(
            f"Datadog, event added to queue. Will flush in {self.flush_interval} seconds..."
        )

        if len(self.log_queue) >= self.batch_size:
            await self.async_send_batch()

    def _create_datadog_logging_payload_helper(
        self,
        standard_logging_object: StandardLoggingPayload,
        status: DataDogStatus,
    ) -> DatadogPayload:
        json_payload = json.dumps(standard_logging_object, default=str)
        verbose_logger.debug("Datadog: Logger - Logging payload = %s", json_payload)
        dd_payload = DatadogPayload(
            ddsource=self._get_datadog_source(),
            ddtags=self._get_datadog_tags(
                standard_logging_object=standard_logging_object
            ),
            hostname=self._get_datadog_hostname(),
            message=json_payload,
            service=self._get_datadog_service(),
            status=status,
        )
        return dd_payload

    def create_datadog_logging_payload(
        self,
        kwargs: Union[dict, Any],
        response_obj: Any,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> DatadogPayload:
        """
        Helper function to create a datadog payload for logging

        Args:
            kwargs (Union[dict, Any]): request kwargs
            response_obj (Any): llm api response
            start_time (datetime.datetime): start time of request
            end_time (datetime.datetime): end time of request

        Returns:
            DatadogPayload: defined in types.py
        """

        standard_logging_object: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object", None
        )
        if standard_logging_object is None:
            raise ValueError("standard_logging_object not found in kwargs")

        status = DataDogStatus.INFO
        if standard_logging_object.get("status") == "failure":
            status = DataDogStatus.ERROR

        # Build the initial payload
        self.truncate_standard_logging_payload_content(standard_logging_object)

        dd_payload = self._create_datadog_logging_payload_helper(
            standard_logging_object=standard_logging_object,
            status=status,
        )
        return dd_payload

    async def async_send_compressed_data(self, data: List) -> Response:
        """
        Async helper to send compressed data to datadog self.intake_url

        Datadog recommends using gzip to compress data
        https://docs.datadoghq.com/api/latest/logs/

        "Datadog recommends sending your logs compressed. Add the Content-Encoding: gzip header to the request when sending"
        """

        import gzip
        import json

        compressed_data = gzip.compress(json.dumps(data, default=str).encode("utf-8"))
        response = await self.async_client.post(
            url=self.intake_url,
            data=compressed_data,  # type: ignore
            headers={
                "DD-API-KEY": self.DD_API_KEY,
                "Content-Encoding": "gzip",
                "Content-Type": "application/json",
            },
        )
        return response

    async def async_service_failure_hook(
        self,
        payload: ServiceLoggerPayload,
        error: Optional[str] = "",
        parent_otel_span: Optional[Any] = None,
        start_time: Optional[Union[datetimeObj, float]] = None,
        end_time: Optional[Union[float, datetimeObj]] = None,
        event_metadata: Optional[dict] = None,
    ):
        """
        Logs failures from Redis, Postgres (Adjacent systems), as 'WARNING' on DataDog

        - example - Redis is failing / erroring, will be logged on DataDog
        """
        try:
            _payload_dict = payload.model_dump()
            _payload_dict.update(event_metadata or {})
            _dd_message_str = json.dumps(_payload_dict, default=str)
            _dd_payload = DatadogPayload(
                ddsource=self._get_datadog_source(),
                ddtags=self._get_datadog_tags(),
                hostname=self._get_datadog_hostname(),
                message=_dd_message_str,
                service=self._get_datadog_service(),
                status=DataDogStatus.WARN,
            )

            self.log_queue.append(_dd_payload)

        except Exception as e:
            verbose_logger.exception(
                f"Datadog: Logger - Exception in async_service_failure_hook: {e}"
            )
        pass

    async def async_service_success_hook(
        self,
        payload: ServiceLoggerPayload,
        error: Optional[str] = "",
        parent_otel_span: Optional[Any] = None,
        start_time: Optional[Union[datetimeObj, float]] = None,
        end_time: Optional[Union[float, datetimeObj]] = None,
        event_metadata: Optional[dict] = None,
    ):
        """
        Logs success from Redis, Postgres (Adjacent systems), as 'INFO' on DataDog

        No user has asked for this so far, this might be spammy on datatdog. If need arises we can implement this
        """
        try:
            # intentionally done. Don't want to log all service types to DD
            if payload.service not in DD_LOGGED_SUCCESS_SERVICE_TYPES:
                return

            _payload_dict = payload.model_dump()
            _payload_dict.update(event_metadata or {})

            _dd_message_str = json.dumps(_payload_dict, default=str)
            _dd_payload = DatadogPayload(
                ddsource=self._get_datadog_source(),
                ddtags=self._get_datadog_tags(),
                hostname=self._get_datadog_hostname(),
                message=_dd_message_str,
                service=self._get_datadog_service(),
                status=DataDogStatus.INFO,
            )

            self.log_queue.append(_dd_payload)

        except Exception as e:
            verbose_logger.exception(
                f"Datadog: Logger - Exception in async_service_failure_hook: {e}"
            )

    def _create_v0_logging_payload(
        self,
        kwargs: Union[dict, Any],
        response_obj: Any,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> DatadogPayload:
        """
        Note: This is our V1 Version of DataDog Logging Payload


        (Not Recommended) If you want this to get logged set `litellm.datadog_use_v1 = True`
        """
        import json

        litellm_params = kwargs.get("litellm_params", {})
        metadata = (
            litellm_params.get("metadata", {}) or {}
        )  # if litellm_params['metadata'] == None
        messages = kwargs.get("messages")
        optional_params = kwargs.get("optional_params", {})
        call_type = kwargs.get("call_type", "litellm.completion")
        cache_hit = kwargs.get("cache_hit", False)
        usage = response_obj["usage"]
        id = response_obj.get("id", str(uuid.uuid4()))
        usage = dict(usage)
        try:
            response_time = (end_time - start_time).total_seconds() * 1000
        except Exception:
            response_time = None

        try:
            response_obj = dict(response_obj)
        except Exception:
            response_obj = response_obj

        # Clean Metadata before logging - never log raw metadata
        # the raw metadata can contain circular references which leads to infinite recursion
        # we clean out all extra litellm metadata params before logging
        clean_metadata = {}
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                # clean litellm metadata before logging
                if key in [
                    "endpoint",
                    "caching_groups",
                    "previous_models",
                ]:
                    continue
                else:
                    clean_metadata[key] = value

        # Build the initial payload
        payload = {
            "id": id,
            "call_type": call_type,
            "cache_hit": cache_hit,
            "start_time": start_time,
            "end_time": end_time,
            "response_time": response_time,
            "model": kwargs.get("model", ""),
            "user": kwargs.get("user", ""),
            "model_parameters": optional_params,
            "spend": kwargs.get("response_cost", 0),
            "messages": messages,
            "response": response_obj,
            "usage": usage,
            "metadata": clean_metadata,
        }

        json_payload = json.dumps(payload, default=str)

        verbose_logger.debug("Datadog: Logger - Logging payload = %s", json_payload)

        dd_payload = DatadogPayload(
            ddsource=self._get_datadog_source(),
            ddtags=self._get_datadog_tags(),
            hostname=self._get_datadog_hostname(),
            message=json_payload,
            service=self._get_datadog_service(),
            status=DataDogStatus.INFO,
        )
        return dd_payload

    @staticmethod
    def _get_datadog_tags(
        standard_logging_object: Optional[StandardLoggingPayload] = None,
    ) -> str:
        """
        Get the datadog tags for the request

        DD tags need to be as follows:
            - tags: ["user_handle:dog@gmail.com", "app_version:1.0.0"]
        """
        base_tags = {
            "env": os.getenv("DD_ENV", "unknown"),
            "service": os.getenv("DD_SERVICE", "litellm"),
            "version": os.getenv("DD_VERSION", "unknown"),
            "HOSTNAME": DataDogLogger._get_datadog_hostname(),
            "POD_NAME": os.getenv("POD_NAME", "unknown"),
        }

        tags = [f"{k}:{v}" for k, v in base_tags.items()]

        if standard_logging_object:
            _request_tags: List[str] = (
                standard_logging_object.get("request_tags", []) or []
            )
            request_tags = [f"request_tag:{tag}" for tag in _request_tags]
            tags.extend(request_tags)

        return ",".join(tags)

    @staticmethod
    def _get_datadog_source():
        return os.getenv("DD_SOURCE", "litellm")

    @staticmethod
    def _get_datadog_service():
        return os.getenv("DD_SERVICE", "litellm-server")

    @staticmethod
    def _get_datadog_hostname():
        return os.getenv("HOSTNAME", "")

    @staticmethod
    def _get_datadog_env():
        return os.getenv("DD_ENV", "unknown")

    @staticmethod
    def _get_datadog_pod_name():
        return os.getenv("POD_NAME", "unknown")

    async def async_health_check(self) -> IntegrationHealthCheckStatus:
        """
        Check if the service is healthy
        """
        from litellm.litellm_core_utils.litellm_logging import (
            create_dummy_standard_logging_payload,
        )

        standard_logging_object = create_dummy_standard_logging_payload()
        dd_payload = self._create_datadog_logging_payload_helper(
            standard_logging_object=standard_logging_object,
            status=DataDogStatus.INFO,
        )
        log_queue = [dd_payload]
        response = await self.async_send_compressed_data(log_queue)
        try:
            response.raise_for_status()
            return IntegrationHealthCheckStatus(
                status="healthy",
                error_message=None,
            )
        except httpx.HTTPStatusError as e:
            return IntegrationHealthCheckStatus(
                status="unhealthy",
                error_message=e.response.text,
            )
        except Exception as e:
            return IntegrationHealthCheckStatus(
                status="unhealthy",
                error_message=str(e),
            )

    async def get_request_response_payload(
        self,
        request_id: str,
        start_time_utc: Optional[datetimeObj],
        end_time_utc: Optional[datetimeObj],
    ) -> Optional[dict]:
        pass

# === NexusCore/openenv\Lib\site-packages\nltk\parse\pchart.py ===
# Natural Language Toolkit: Probabilistic Chart Parsers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for associating probabilities with tree
structures that represent the internal organization of a text.  The
probabilistic parser module defines ``BottomUpProbabilisticChartParser``.

``BottomUpProbabilisticChartParser`` is an abstract class that implements
a bottom-up chart parser for ``PCFG`` grammars.  It maintains a queue of edges,
and adds them to the chart one at a time.  The ordering of this queue
is based on the probabilities associated with the edges, allowing the
parser to expand more likely edges before less likely ones.  Each
subclass implements a different queue ordering, producing different
search strategies.  Currently the following subclasses are defined:

  - ``InsideChartParser`` searches edges in decreasing order of
    their trees' inside probabilities.
  - ``RandomChartParser`` searches edges in random order.
  - ``LongestChartParser`` searches edges in decreasing order of their
    location's length.

The ``BottomUpProbabilisticChartParser`` constructor has an optional
argument beam_size.  If non-zero, this controls the size of the beam
(aka the edge queue).  This option is most useful with InsideChartParser.
"""

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

# [XX] This might not be implemented quite right -- it would be better
# to associate probabilities with child pointer lists.

import random
from functools import reduce

from nltk.grammar import PCFG, Nonterminal
from nltk.parse.api import ParserI
from nltk.parse.chart import AbstractChartRule, Chart, LeafEdge, TreeEdge
from nltk.tree import ProbabilisticTree, Tree


# Probabilistic edges
class ProbabilisticLeafEdge(LeafEdge):
    def prob(self):
        return 1.0


class ProbabilisticTreeEdge(TreeEdge):
    def __init__(self, prob, *args, **kwargs):
        TreeEdge.__init__(self, *args, **kwargs)
        self._prob = prob
        # two edges with different probabilities are not equal.
        self._comparison_key = (self._comparison_key, prob)

    def prob(self):
        return self._prob

    @staticmethod
    def from_production(production, index, p):
        return ProbabilisticTreeEdge(
            p, (index, index), production.lhs(), production.rhs(), 0
        )


# Rules using probabilistic edges
class ProbabilisticBottomUpInitRule(AbstractChartRule):
    NUM_EDGES = 0

    def apply(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = ProbabilisticLeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge


class ProbabilisticBottomUpPredictRule(AbstractChartRule):
    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        for prod in grammar.productions():
            if edge.lhs() == prod.rhs()[0]:
                new_edge = ProbabilisticTreeEdge.from_production(
                    prod, edge.start(), prod.prob()
                )
                if chart.insert(new_edge, ()):
                    yield new_edge


class ProbabilisticFundamentalRule(AbstractChartRule):
    NUM_EDGES = 2

    def apply(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (
            left_edge.end() == right_edge.start()
            and left_edge.nextsym() == right_edge.lhs()
            and left_edge.is_incomplete()
            and right_edge.is_complete()
        ):
            return

        # Construct the new edge.
        p = left_edge.prob() * right_edge.prob()
        new_edge = ProbabilisticTreeEdge(
            p,
            span=(left_edge.start(), right_edge.end()),
            lhs=left_edge.lhs(),
            rhs=left_edge.rhs(),
            dot=left_edge.dot() + 1,
        )

        # Add it to the chart, with appropriate child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1 + (right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart:
            yield new_edge


class SingleEdgeProbabilisticFundamentalRule(AbstractChartRule):
    NUM_EDGES = 1

    _fundamental_rule = ProbabilisticFundamentalRule()

    def apply(self, chart, grammar, edge1):
        fr = self._fundamental_rule
        if edge1.is_incomplete():
            # edge1 = left_edge; edge2 = right_edge
            for edge2 in chart.select(
                start=edge1.end(), is_complete=True, lhs=edge1.nextsym()
            ):
                yield from fr.apply(chart, grammar, edge1, edge2)
        else:
            # edge2 = left_edge; edge1 = right_edge
            for edge2 in chart.select(
                end=edge1.start(), is_complete=False, nextsym=edge1.lhs()
            ):
                yield from fr.apply(chart, grammar, edge2, edge1)

    def __str__(self):
        return "Fundamental Rule"


class BottomUpProbabilisticChartParser(ParserI):
    """
    An abstract bottom-up parser for ``PCFG`` grammars that uses a ``Chart`` to
    record partial results.  ``BottomUpProbabilisticChartParser`` maintains
    a queue of edges that can be added to the chart.  This queue is
    initialized with edges for each token in the text that is being
    parsed.  ``BottomUpProbabilisticChartParser`` inserts these edges into
    the chart one at a time, starting with the most likely edges, and
    proceeding to less likely edges.  For each edge that is added to
    the chart, it may become possible to insert additional edges into
    the chart; these are added to the queue.  This process continues
    until enough complete parses have been generated, or until the
    queue is empty.

    The sorting order for the queue is not specified by
    ``BottomUpProbabilisticChartParser``.  Different sorting orders will
    result in different search strategies.  The sorting order for the
    queue is defined by the method ``sort_queue``; subclasses are required
    to provide a definition for this method.

    :type _grammar: PCFG
    :ivar _grammar: The grammar used to parse sentences.
    :type _trace: int
    :ivar _trace: The level of tracing output that should be generated
        when parsing a text.
    """

    def __init__(self, grammar, beam_size=0, trace=0):
        """
        Create a new ``BottomUpProbabilisticChartParser``, that uses
        ``grammar`` to parse texts.

        :type grammar: PCFG
        :param grammar: The grammar used to parse texts.
        :type beam_size: int
        :param beam_size: The maximum length for the parser's edge queue.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        if not isinstance(grammar, PCFG):
            raise ValueError("The grammar must be probabilistic PCFG")
        self._grammar = grammar
        self.beam_size = beam_size
        self._trace = trace

    def grammar(self):
        return self._grammar

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        :type trace: int
        :param trace: The trace level.  A trace level of ``0`` will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        :rtype: None
        """
        self._trace = trace

    # TODO: change this to conform more with the standard ChartParser
    def parse(self, tokens):
        self._grammar.check_coverage(tokens)
        chart = Chart(list(tokens))
        grammar = self._grammar

        # Chart parser rules.
        bu_init = ProbabilisticBottomUpInitRule()
        bu = ProbabilisticBottomUpPredictRule()
        fr = SingleEdgeProbabilisticFundamentalRule()

        # Our queue
        queue = []

        # Initialize the chart.
        for edge in bu_init.apply(chart, grammar):
            if self._trace > 1:
                print(
                    "  %-50s [%s]"
                    % (chart.pretty_format_edge(edge, width=2), edge.prob())
                )
            queue.append(edge)

        while len(queue) > 0:
            # Re-sort the queue.
            self.sort_queue(queue, chart)

            # Prune the queue to the correct size if a beam was defined
            if self.beam_size:
                self._prune(queue, chart)

            # Get the best edge.
            edge = queue.pop()
            if self._trace > 0:
                print(
                    "  %-50s [%s]"
                    % (chart.pretty_format_edge(edge, width=2), edge.prob())
                )

            # Apply BU & FR to it.
            queue.extend(bu.apply(chart, grammar, edge))
            queue.extend(fr.apply(chart, grammar, edge))

        # Get a list of complete parses.
        parses = list(chart.parses(grammar.start(), ProbabilisticTree))

        # Assign probabilities to the trees.
        prod_probs = {}
        for prod in grammar.productions():
            prod_probs[prod.lhs(), prod.rhs()] = prod.prob()
        for parse in parses:
            self._setprob(parse, prod_probs)

        # Sort by probability
        parses.sort(reverse=True, key=lambda tree: tree.prob())

        return iter(parses)

    def _setprob(self, tree, prod_probs):
        if tree.prob() is not None:
            return

        # Get the prob of the CFG production.
        lhs = Nonterminal(tree.label())
        rhs = []
        for child in tree:
            if isinstance(child, Tree):
                rhs.append(Nonterminal(child.label()))
            else:
                rhs.append(child)
        prob = prod_probs[lhs, tuple(rhs)]

        # Get the probs of children.
        for child in tree:
            if isinstance(child, Tree):
                self._setprob(child, prod_probs)
                prob *= child.prob()

        tree.set_prob(prob)

    def sort_queue(self, queue, chart):
        """
        Sort the given queue of ``Edge`` objects, placing the edge that should
        be tried first at the beginning of the queue.  This method
        will be called after each ``Edge`` is added to the queue.

        :param queue: The queue of ``Edge`` objects to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        :type queue: list(Edge)
        :param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        :type chart: Chart
        :rtype: None
        """
        raise NotImplementedError()

    def _prune(self, queue, chart):
        """Discard items in the queue if the queue is longer than the beam."""
        if len(queue) > self.beam_size:
            split = len(queue) - self.beam_size
            if self._trace > 2:
                for edge in queue[:split]:
                    print("  %-50s [DISCARDED]" % chart.pretty_format_edge(edge, 2))
            del queue[:split]


class InsideChartParser(BottomUpProbabilisticChartParser):
    """
    A bottom-up parser for ``PCFG`` grammars that tries edges in descending
    order of the inside probabilities of their trees.  The "inside
    probability" of a tree is simply the
    probability of the entire tree, ignoring its context.  In
    particular, the inside probability of a tree generated by
    production *p* with children *c[1], c[2], ..., c[n]* is
    *P(p)P(c[1])P(c[2])...P(c[n])*; and the inside
    probability of a token is 1 if it is present in the text, and 0 if
    it is absent.

    This sorting order results in a type of lowest-cost-first search
    strategy.
    """

    # Inherit constructor.
    def sort_queue(self, queue, chart):
        """
        Sort the given queue of edges, in descending order of the
        inside probabilities of the edges' trees.

        :param queue: The queue of ``Edge`` objects to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        :type queue: list(Edge)
        :param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        :type chart: Chart
        :rtype: None
        """
        queue.sort(key=lambda edge: edge.prob())


# Eventually, this will become some sort of inside-outside parser:
# class InsideOutsideParser(BottomUpProbabilisticChartParser):
#     def __init__(self, grammar, trace=0):
#         # Inherit docs.
#         BottomUpProbabilisticChartParser.__init__(self, grammar, trace)
#
#         # Find the best path from S to each nonterminal
#         bestp = {}
#         for production in grammar.productions(): bestp[production.lhs()]=0
#         bestp[grammar.start()] = 1.0
#
#         for i in range(len(grammar.productions())):
#             for production in grammar.productions():
#                 lhs = production.lhs()
#                 for elt in production.rhs():
#                     bestp[elt] = max(bestp[lhs]*production.prob(),
#                                      bestp.get(elt,0))
#
#         self._bestp = bestp
#         for (k,v) in self._bestp.items(): print(k,v)
#
#     def _sortkey(self, edge):
#         return edge.structure()[PROB] * self._bestp[edge.lhs()]
#
#     def sort_queue(self, queue, chart):
#         queue.sort(key=self._sortkey)


class RandomChartParser(BottomUpProbabilisticChartParser):
    """
    A bottom-up parser for ``PCFG`` grammars that tries edges in random order.
    This sorting order results in a random search strategy.
    """

    # Inherit constructor
    def sort_queue(self, queue, chart):
        i = random.randint(0, len(queue) - 1)
        (queue[-1], queue[i]) = (queue[i], queue[-1])


class UnsortedChartParser(BottomUpProbabilisticChartParser):
    """
    A bottom-up parser for ``PCFG`` grammars that tries edges in whatever order.
    """

    # Inherit constructor
    def sort_queue(self, queue, chart):
        return


class LongestChartParser(BottomUpProbabilisticChartParser):
    """
    A bottom-up parser for ``PCFG`` grammars that tries longer edges before
    shorter ones.  This sorting order results in a type of best-first
    search strategy.
    """

    # Inherit constructor
    def sort_queue(self, queue, chart):
        queue.sort(key=lambda edge: edge.length())


##//////////////////////////////////////////////////////
##  Test Code
##//////////////////////////////////////////////////////


def demo(choice=None, draw_parses=None, print_parses=None):
    """
    A demonstration of the probabilistic parsers.  The user is
    prompted to select which demo to run, and how many parses should
    be found; and then each parser is run on the same demo, and a
    summary of the results are displayed.
    """
    import sys
    import time

    from nltk import tokenize
    from nltk.parse import pchart

    # Define two demos.  Each demo has a sentence and a grammar.
    toy_pcfg1 = PCFG.fromstring(
        """
    S -> NP VP [1.0]
    NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
    Det -> 'the' [0.8] | 'my' [0.2]
    N -> 'man' [0.5] | 'telescope' [0.5]
    VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
    V -> 'ate' [0.35] | 'saw' [0.65]
    PP -> P NP [1.0]
    P -> 'with' [0.61] | 'under' [0.39]
    """
    )

    toy_pcfg2 = PCFG.fromstring(
        """
    S    -> NP VP         [1.0]
    VP   -> V NP          [.59]
    VP   -> V             [.40]
    VP   -> VP PP         [.01]
    NP   -> Det N         [.41]
    NP   -> Name          [.28]
    NP   -> NP PP         [.31]
    PP   -> P NP          [1.0]
    V    -> 'saw'         [.21]
    V    -> 'ate'         [.51]
    V    -> 'ran'         [.28]
    N    -> 'boy'         [.11]
    N    -> 'cookie'      [.12]
    N    -> 'table'       [.13]
    N    -> 'telescope'   [.14]
    N    -> 'hill'        [.5]
    Name -> 'Jack'        [.52]
    Name -> 'Bob'         [.48]
    P    -> 'with'        [.61]
    P    -> 'under'       [.39]
    Det  -> 'the'         [.41]
    Det  -> 'a'           [.31]
    Det  -> 'my'          [.28]
    """
    )

    demos = [
        ("I saw John with my telescope", toy_pcfg1),
        ("the boy saw Jack with Bob under the table with a telescope", toy_pcfg2),
    ]

    if choice is None:
        # Ask the user which demo they want to use.
        print()
        for i in range(len(demos)):
            print(f"{i + 1:>3}: {demos[i][0]}")
            print("     %r" % demos[i][1])
            print()
        print("Which demo (%d-%d)? " % (1, len(demos)), end=" ")
        choice = int(sys.stdin.readline().strip()) - 1
    try:
        sent, grammar = demos[choice]
    except:
        print("Bad sentence number")
        return

    # Tokenize the sentence.
    tokens = sent.split()

    # Define a list of parsers.  We'll use all parsers.
    parsers = [
        pchart.InsideChartParser(grammar),
        pchart.RandomChartParser(grammar),
        pchart.UnsortedChartParser(grammar),
        pchart.LongestChartParser(grammar),
        pchart.InsideChartParser(grammar, beam_size=len(tokens) + 1),  # was BeamParser
    ]

    # Run the parsers on the tokenized sentence.
    times = []
    average_p = []
    num_parses = []
    all_parses = {}
    for parser in parsers:
        print(f"\ns: {sent}\nparser: {parser}\ngrammar: {grammar}")
        parser.trace(3)
        t = time.time()
        parses = list(parser.parse(tokens))
        times.append(time.time() - t)
        p = reduce(lambda a, b: a + b.prob(), parses, 0) / len(parses) if parses else 0
        average_p.append(p)
        num_parses.append(len(parses))
        for p in parses:
            all_parses[p.freeze()] = 1

    # Print some summary statistics
    print()
    print("       Parser      Beam | Time (secs)   # Parses   Average P(parse)")
    print("------------------------+------------------------------------------")
    for i in range(len(parsers)):
        print(
            "%18s %4d |%11.4f%11d%19.14f"
            % (
                parsers[i].__class__.__name__,
                parsers[i].beam_size,
                times[i],
                num_parses[i],
                average_p[i],
            )
        )
    parses = all_parses.keys()
    if parses:
        p = reduce(lambda a, b: a + b.prob(), parses, 0) / len(parses)
    else:
        p = 0
    print("------------------------+------------------------------------------")
    print("%18s      |%11s%11d%19.14f" % ("(All Parses)", "n/a", len(parses), p))

    if draw_parses is None:
        # Ask the user if we should draw the parses.
        print()
        print("Draw parses (y/n)? ", end=" ")
        draw_parses = sys.stdin.readline().strip().lower().startswith("y")
    if draw_parses:
        from nltk.draw.tree import draw_trees

        print("  please wait...")
        draw_trees(*parses)

    if print_parses is None:
        # Ask the user if we should print the parses.
        print()
        print("Print parses (y/n)? ", end=" ")
        print_parses = sys.stdin.readline().strip().lower().startswith("y")
    if print_parses:
        for parse in parses:
            print(parse)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\conll.py ===
# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Read CoNLL-style chunk fileids.
"""

import textwrap

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.tag import map_tag
from nltk.tree import Tree
from nltk.util import LazyConcatenation, LazyMap


class ConllCorpusReader(CorpusReader):
    """
    A corpus reader for CoNLL-style files.  These files consist of a
    series of sentences, separated by blank lines.  Each sentence is
    encoded using a table (or "grid") of values, where each line
    corresponds to a single word, and each column corresponds to an
    annotation type.  The set of columns used by CoNLL-style files can
    vary from corpus to corpus; the ``ConllCorpusReader`` constructor
    therefore takes an argument, ``columntypes``, which is used to
    specify the columns that are used by a given corpus. By default
    columns are split by consecutive whitespaces, with the
    ``separator`` argument you can set a string to split by (e.g.
    ``\'\t\'``).


    @todo: Add support for reading from corpora where different
        parallel files contain different columns.
    @todo: Possibly add caching of the grid corpus view?  This would
        allow the same grid view to be used by different data access
        methods (eg words() and parsed_sents() could both share the
        same grid corpus view object).
    @todo: Better support for -DOCSTART-.  Currently, we just ignore
        it, but it could be used to define methods that retrieve a
        document at a time (eg parsed_documents()).
    """

    # /////////////////////////////////////////////////////////////////
    # Column Types
    # /////////////////////////////////////////////////////////////////

    WORDS = "words"  #: column type for words
    POS = "pos"  #: column type for part-of-speech tags
    TREE = "tree"  #: column type for parse trees
    CHUNK = "chunk"  #: column type for chunk structures
    NE = "ne"  #: column type for named entities
    SRL = "srl"  #: column type for semantic role labels
    IGNORE = "ignore"  #: column type for column that should be ignored

    #: A list of all column types supported by the conll corpus reader.
    COLUMN_TYPES = (WORDS, POS, TREE, CHUNK, NE, SRL, IGNORE)

    # /////////////////////////////////////////////////////////////////
    # Constructor
    # /////////////////////////////////////////////////////////////////

    def __init__(
        self,
        root,
        fileids,
        columntypes,
        chunk_types=None,
        root_label="S",
        pos_in_tree=False,
        srl_includes_roleset=True,
        encoding="utf8",
        tree_class=Tree,
        tagset=None,
        separator=None,
    ):
        for columntype in columntypes:
            if columntype not in self.COLUMN_TYPES:
                raise ValueError("Bad column type %r" % columntype)
        if isinstance(chunk_types, str):
            chunk_types = [chunk_types]
        self._chunk_types = chunk_types
        self._colmap = {c: i for (i, c) in enumerate(columntypes)}
        self._pos_in_tree = pos_in_tree
        self._root_label = root_label  # for chunks
        self._srl_includes_roleset = srl_includes_roleset
        self._tree_class = tree_class
        CorpusReader.__init__(self, root, fileids, encoding)
        self._tagset = tagset
        self.sep = separator

    # /////////////////////////////////////////////////////////////////
    # Data Access Methods
    # /////////////////////////////////////////////////////////////////

    def words(self, fileids=None):
        self._require(self.WORDS)
        return LazyConcatenation(LazyMap(self._get_words, self._grids(fileids)))

    def sents(self, fileids=None):
        self._require(self.WORDS)
        return LazyMap(self._get_words, self._grids(fileids))

    def tagged_words(self, fileids=None, tagset=None):
        self._require(self.WORDS, self.POS)

        def get_tagged_words(grid):
            return self._get_tagged_words(grid, tagset)

        return LazyConcatenation(LazyMap(get_tagged_words, self._grids(fileids)))

    def tagged_sents(self, fileids=None, tagset=None):
        self._require(self.WORDS, self.POS)

        def get_tagged_words(grid):
            return self._get_tagged_words(grid, tagset)

        return LazyMap(get_tagged_words, self._grids(fileids))

    def chunked_words(self, fileids=None, chunk_types=None, tagset=None):
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None:
            chunk_types = self._chunk_types

        def get_chunked_words(grid):  # capture chunk_types as local var
            return self._get_chunked_words(grid, chunk_types, tagset)

        return LazyConcatenation(LazyMap(get_chunked_words, self._grids(fileids)))

    def chunked_sents(self, fileids=None, chunk_types=None, tagset=None):
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None:
            chunk_types = self._chunk_types

        def get_chunked_words(grid):  # capture chunk_types as local var
            return self._get_chunked_words(grid, chunk_types, tagset)

        return LazyMap(get_chunked_words, self._grids(fileids))

    def parsed_sents(self, fileids=None, pos_in_tree=None, tagset=None):
        self._require(self.WORDS, self.POS, self.TREE)
        if pos_in_tree is None:
            pos_in_tree = self._pos_in_tree

        def get_parsed_sent(grid):  # capture pos_in_tree as local var
            return self._get_parsed_sent(grid, pos_in_tree, tagset)

        return LazyMap(get_parsed_sent, self._grids(fileids))

    def srl_spans(self, fileids=None):
        self._require(self.SRL)
        return LazyMap(self._get_srl_spans, self._grids(fileids))

    def srl_instances(self, fileids=None, pos_in_tree=None, flatten=True):
        self._require(self.WORDS, self.POS, self.TREE, self.SRL)
        if pos_in_tree is None:
            pos_in_tree = self._pos_in_tree

        def get_srl_instances(grid):  # capture pos_in_tree as local var
            return self._get_srl_instances(grid, pos_in_tree)

        result = LazyMap(get_srl_instances, self._grids(fileids))
        if flatten:
            result = LazyConcatenation(result)
        return result

    def iob_words(self, fileids=None, tagset=None):
        """
        :return: a list of word/tag/IOB tuples
        :rtype: list(tuple)
        :param fileids: the list of fileids that make up this corpus
        :type fileids: None or str or list
        """
        self._require(self.WORDS, self.POS, self.CHUNK)

        def get_iob_words(grid):
            return self._get_iob_words(grid, tagset)

        return LazyConcatenation(LazyMap(get_iob_words, self._grids(fileids)))

    def iob_sents(self, fileids=None, tagset=None):
        """
        :return: a list of lists of word/tag/IOB tuples
        :rtype: list(list)
        :param fileids: the list of fileids that make up this corpus
        :type fileids: None or str or list
        """
        self._require(self.WORDS, self.POS, self.CHUNK)

        def get_iob_words(grid):
            return self._get_iob_words(grid, tagset)

        return LazyMap(get_iob_words, self._grids(fileids))

    # /////////////////////////////////////////////////////////////////
    # Grid Reading
    # /////////////////////////////////////////////////////////////////

    def _grids(self, fileids=None):
        # n.b.: we could cache the object returned here (keyed on
        # fileids), which would let us reuse the same corpus view for
        # different things (eg srl and parse trees).
        return concat(
            [
                StreamBackedCorpusView(fileid, self._read_grid_block, encoding=enc)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def _read_grid_block(self, stream):
        grids = []
        for block in read_blankline_block(stream):
            block = block.strip()
            if not block:
                continue

            grid = [line.split(self.sep) for line in block.split("\n")]

            # If there's a docstart row, then discard. ([xx] eventually it
            # would be good to actually use it)
            if grid[0][self._colmap.get("words", 0)] == "-DOCSTART-":
                del grid[0]

            # Check that the grid is consistent.
            for row in grid:
                if len(row) != len(grid[0]):
                    raise ValueError("Inconsistent number of columns:\n%s" % block)
            grids.append(grid)
        return grids

    # /////////////////////////////////////////////////////////////////
    # Transforms
    # /////////////////////////////////////////////////////////////////
    # given a grid, transform it into some representation (e.g.,
    # a list of words or a parse tree).

    def _get_words(self, grid):
        return self._get_column(grid, self._colmap["words"])

    def _get_tagged_words(self, grid, tagset=None):
        pos_tags = self._get_column(grid, self._colmap["pos"])
        if tagset and tagset != self._tagset:
            pos_tags = [map_tag(self._tagset, tagset, t) for t in pos_tags]
        return list(zip(self._get_column(grid, self._colmap["words"]), pos_tags))

    def _get_iob_words(self, grid, tagset=None):
        pos_tags = self._get_column(grid, self._colmap["pos"])
        if tagset and tagset != self._tagset:
            pos_tags = [map_tag(self._tagset, tagset, t) for t in pos_tags]
        return list(
            zip(
                self._get_column(grid, self._colmap["words"]),
                pos_tags,
                self._get_column(grid, self._colmap["chunk"]),
            )
        )

    def _get_chunked_words(self, grid, chunk_types, tagset=None):
        # n.b.: this method is very similar to conllstr2tree.
        words = self._get_column(grid, self._colmap["words"])
        pos_tags = self._get_column(grid, self._colmap["pos"])
        if tagset and tagset != self._tagset:
            pos_tags = [map_tag(self._tagset, tagset, t) for t in pos_tags]
        chunk_tags = self._get_column(grid, self._colmap["chunk"])

        stack = [Tree(self._root_label, [])]

        for word, pos_tag, chunk_tag in zip(words, pos_tags, chunk_tags):
            if chunk_tag == "O":
                state, chunk_type = "O", ""
            else:
                (state, chunk_type) = chunk_tag.split("-")
            # If it's a chunk we don't care about, treat it as O.
            if chunk_types is not None and chunk_type not in chunk_types:
                state = "O"
            # Treat a mismatching I like a B.
            if state == "I" and chunk_type != stack[-1].label():
                state = "B"
            # For B or I: close any open chunks
            if state in "BO" and len(stack) == 2:
                stack.pop()
            # For B: start a new chunk.
            if state == "B":
                new_chunk = Tree(chunk_type, [])
                stack[-1].append(new_chunk)
                stack.append(new_chunk)
            # Add the word token.
            stack[-1].append((word, pos_tag))

        return stack[0]

    def _get_parsed_sent(self, grid, pos_in_tree, tagset=None):
        words = self._get_column(grid, self._colmap["words"])
        pos_tags = self._get_column(grid, self._colmap["pos"])
        if tagset and tagset != self._tagset:
            pos_tags = [map_tag(self._tagset, tagset, t) for t in pos_tags]
        parse_tags = self._get_column(grid, self._colmap["tree"])

        treestr = ""
        for word, pos_tag, parse_tag in zip(words, pos_tags, parse_tags):
            if word == "(":
                word = "-LRB-"
            if word == ")":
                word = "-RRB-"
            if pos_tag == "(":
                pos_tag = "-LRB-"
            if pos_tag == ")":
                pos_tag = "-RRB-"
            (left, right) = parse_tag.split("*")
            right = right.count(")") * ")"  # only keep ')'.
            treestr += f"{left} ({pos_tag} {word}) {right}"
        try:
            tree = self._tree_class.fromstring(treestr)
        except (ValueError, IndexError):
            tree = self._tree_class.fromstring(f"({self._root_label} {treestr})")

        if not pos_in_tree:
            for subtree in tree.subtrees():
                for i, child in enumerate(subtree):
                    if (
                        isinstance(child, Tree)
                        and len(child) == 1
                        and isinstance(child[0], str)
                    ):
                        subtree[i] = (child[0], child.label())

        return tree

    def _get_srl_spans(self, grid):
        """
        list of list of (start, end), tag) tuples
        """
        if self._srl_includes_roleset:
            predicates = self._get_column(grid, self._colmap["srl"] + 1)
            start_col = self._colmap["srl"] + 2
        else:
            predicates = self._get_column(grid, self._colmap["srl"])
            start_col = self._colmap["srl"] + 1

        # Count how many predicates there are.  This tells us how many
        # columns to expect for SRL data.
        num_preds = len([p for p in predicates if p != "-"])

        spanlists = []
        for i in range(num_preds):
            col = self._get_column(grid, start_col + i)
            spanlist = []
            stack = []
            for wordnum, srl_tag in enumerate(col):
                (left, right) = srl_tag.split("*")
                for tag in left.split("("):
                    if tag:
                        stack.append((tag, wordnum))
                for i in range(right.count(")")):
                    (tag, start) = stack.pop()
                    spanlist.append(((start, wordnum + 1), tag))
            spanlists.append(spanlist)

        return spanlists

    def _get_srl_instances(self, grid, pos_in_tree):
        tree = self._get_parsed_sent(grid, pos_in_tree)
        spanlists = self._get_srl_spans(grid)
        if self._srl_includes_roleset:
            predicates = self._get_column(grid, self._colmap["srl"] + 1)
            rolesets = self._get_column(grid, self._colmap["srl"])
        else:
            predicates = self._get_column(grid, self._colmap["srl"])
            rolesets = [None] * len(predicates)

        instances = ConllSRLInstanceList(tree)
        for wordnum, predicate in enumerate(predicates):
            if predicate == "-":
                continue
            # Decide which spanlist to use.  Don't assume that they're
            # sorted in the same order as the predicates (even though
            # they usually are).
            for spanlist in spanlists:
                for (start, end), tag in spanlist:
                    if wordnum in range(start, end) and tag in ("V", "C-V"):
                        break
                else:
                    continue
                break
            else:
                raise ValueError("No srl column found for %r" % predicate)
            instances.append(
                ConllSRLInstance(tree, wordnum, predicate, rolesets[wordnum], spanlist)
            )

        return instances

    # /////////////////////////////////////////////////////////////////
    # Helper Methods
    # /////////////////////////////////////////////////////////////////

    def _require(self, *columntypes):
        for columntype in columntypes:
            if columntype not in self._colmap:
                raise ValueError(
                    "This corpus does not contain a %s " "column." % columntype
                )

    @staticmethod
    def _get_column(grid, column_index):
        return [grid[i][column_index] for i in range(len(grid))]


class ConllSRLInstance:
    """
    An SRL instance from a CoNLL corpus, which identifies and
    providing labels for the arguments of a single verb.
    """

    # [xx] add inst.core_arguments, inst.argm_arguments?

    def __init__(self, tree, verb_head, verb_stem, roleset, tagged_spans):
        self.verb = []
        """A list of the word indices of the words that compose the
           verb whose arguments are identified by this instance.
           This will contain multiple word indices when multi-word
           verbs are used (e.g. 'turn on')."""

        self.verb_head = verb_head
        """The word index of the head word of the verb whose arguments
           are identified by this instance.  E.g., for a sentence that
           uses the verb 'turn on,' ``verb_head`` will be the word index
           of the word 'turn'."""

        self.verb_stem = verb_stem

        self.roleset = roleset

        self.arguments = []
        """A list of ``(argspan, argid)`` tuples, specifying the location
           and type for each of the arguments identified by this
           instance.  ``argspan`` is a tuple ``start, end``, indicating
           that the argument consists of the ``words[start:end]``."""

        self.tagged_spans = tagged_spans
        """A list of ``(span, id)`` tuples, specifying the location and
           type for each of the arguments, as well as the verb pieces,
           that make up this instance."""

        self.tree = tree
        """The parse tree for the sentence containing this instance."""

        self.words = tree.leaves()
        """A list of the words in the sentence containing this
           instance."""

        # Fill in the self.verb and self.arguments values.
        for (start, end), tag in tagged_spans:
            if tag in ("V", "C-V"):
                self.verb += list(range(start, end))
            else:
                self.arguments.append(((start, end), tag))

    def __repr__(self):
        # Originally, its:
        ##plural = 's' if len(self.arguments) != 1 else ''
        plural = "s" if len(self.arguments) != 1 else ""
        return "<ConllSRLInstance for %r with %d argument%s>" % (
            (self.verb_stem, len(self.arguments), plural)
        )

    def pprint(self):
        verbstr = " ".join(self.words[i][0] for i in self.verb)
        hdr = f"SRL for {verbstr!r} (stem={self.verb_stem!r}):\n"
        s = ""
        for i, word in enumerate(self.words):
            if isinstance(word, tuple):
                word = word[0]
            for (start, end), argid in self.arguments:
                if i == start:
                    s += "[%s " % argid
                if i == end:
                    s += "] "
            if i in self.verb:
                word = "<<%s>>" % word
            s += word + " "
        return hdr + textwrap.fill(
            s.replace(" ]", "]"), initial_indent="    ", subsequent_indent="    "
        )


class ConllSRLInstanceList(list):
    """
    Set of instances for a single sentence
    """

    def __init__(self, tree, instances=()):
        self.tree = tree
        list.__init__(self, instances)

    def __str__(self):
        return self.pprint()

    def pprint(self, include_tree=False):
        # Sanity check: trees should be the same
        for inst in self:
            if inst.tree != self.tree:
                raise ValueError("Tree mismatch!")

        # If desired, add trees:
        if include_tree:
            words = self.tree.leaves()
            pos = [None] * len(words)
            synt = ["*"] * len(words)
            self._tree2conll(self.tree, 0, words, pos, synt)

        s = ""
        for i in range(len(words)):
            # optional tree columns
            if include_tree:
                s += "%-20s " % words[i]
                s += "%-8s " % pos[i]
                s += "%15s*%-8s " % tuple(synt[i].split("*"))

            # verb head column
            for inst in self:
                if i == inst.verb_head:
                    s += "%-20s " % inst.verb_stem
                    break
            else:
                s += "%-20s " % "-"
            # Remaining columns: self
            for inst in self:
                argstr = "*"
                for (start, end), argid in inst.tagged_spans:
                    if i == start:
                        argstr = f"({argid}{argstr}"
                    if i == (end - 1):
                        argstr += ")"
                s += "%-12s " % argstr
            s += "\n"
        return s

    def _tree2conll(self, tree, wordnum, words, pos, synt):
        assert isinstance(tree, Tree)
        if len(tree) == 1 and isinstance(tree[0], str):
            pos[wordnum] = tree.label()
            assert words[wordnum] == tree[0]
            return wordnum + 1
        elif len(tree) == 1 and isinstance(tree[0], tuple):
            assert len(tree[0]) == 2
            pos[wordnum], pos[wordnum] = tree[0]
            return wordnum + 1
        else:
            synt[wordnum] = f"({tree.label()}{synt[wordnum]}"
            for child in tree:
                wordnum = self._tree2conll(child, wordnum, words, pos, synt)
            synt[wordnum - 1] += ")"
            return wordnum


class ConllChunkCorpusReader(ConllCorpusReader):
    """
    A ConllCorpusReader whose data file contains three columns: words,
    pos, and chunk.
    """

    def __init__(
        self, root, fileids, chunk_types, encoding="utf8", tagset=None, separator=None
    ):
        ConllCorpusReader.__init__(
            self,
            root,
            fileids,
            ("words", "pos", "chunk"),
            chunk_types=chunk_types,
            encoding=encoding,
            tagset=tagset,
            separator=separator,
        )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\regular_languages\compiler.py ===
r"""
Compiler for a regular grammar.

Example usage::

    # Create and compile grammar.
    p = compile('add \s+ (?P<var1>[^\s]+)  \s+  (?P<var2>[^\s]+)')

    # Match input string.
    m = p.match('add 23 432')

    # Get variables.
    m.variables().get('var1')  # Returns "23"
    m.variables().get('var2')  # Returns "432"


Partial matches are possible::

    # Create and compile grammar.
    p = compile('''
        # Operators with two arguments.
        ((?P<operator1>[^\s]+)  \s+ (?P<var1>[^\s]+)  \s+  (?P<var2>[^\s]+)) |

        # Operators with only one arguments.
        ((?P<operator2>[^\s]+)  \s+ (?P<var1>[^\s]+))
    ''')

    # Match partial input string.
    m = p.match_prefix('add 23')

    # Get variables. (Notice that both operator1 and operator2 contain the
    # value "add".) This is because our input is incomplete, and we don't know
    # yet in which rule of the regex we we'll end up. It could also be that
    # `operator1` and `operator2` have a different autocompleter and we want to
    # call all possible autocompleters that would result in valid input.)
    m.variables().get('var1')  # Returns "23"
    m.variables().get('operator1')  # Returns "add"
    m.variables().get('operator2')  # Returns "add"

"""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, Iterator, Pattern, TypeVar, overload
from typing import Match as RegexMatch

from .regex_parser import (
    AnyNode,
    Lookahead,
    Node,
    NodeSequence,
    Regex,
    Repeat,
    Variable,
    parse_regex,
    tokenize_regex,
)

__all__ = ["compile", "Match", "Variables"]


# Name of the named group in the regex, matching trailing input.
# (Trailing input is when the input contains characters after the end of the
# expression has been matched.)
_INVALID_TRAILING_INPUT = "invalid_trailing"

EscapeFuncDict = Dict[str, Callable[[str], str]]


class _CompiledGrammar:
    """
    Compiles a grammar. This will take the parse tree of a regular expression
    and compile the grammar.

    :param root_node: :class~`.regex_parser.Node` instance.
    :param escape_funcs: `dict` mapping variable names to escape callables.
    :param unescape_funcs: `dict` mapping variable names to unescape callables.
    """

    def __init__(
        self,
        root_node: Node,
        escape_funcs: EscapeFuncDict | None = None,
        unescape_funcs: EscapeFuncDict | None = None,
    ) -> None:
        self.root_node = root_node
        self.escape_funcs = escape_funcs or {}
        self.unescape_funcs = unescape_funcs or {}

        #: Dictionary that will map the regex names to Node instances.
        self._group_names_to_nodes: dict[
            str, str
        ] = {}  # Maps regex group names to varnames.
        counter = [0]

        def create_group_func(node: Variable) -> str:
            name = f"n{counter[0]}"
            self._group_names_to_nodes[name] = node.varname
            counter[0] += 1
            return name

        # Compile regex strings.
        self._re_pattern = f"^{self._transform(root_node, create_group_func)}$"
        self._re_prefix_patterns = list(
            self._transform_prefix(root_node, create_group_func)
        )

        # Compile the regex itself.
        flags = re.DOTALL  # Note that we don't need re.MULTILINE! (^ and $
        # still represent the start and end of input text.)
        self._re = re.compile(self._re_pattern, flags)
        self._re_prefix = [re.compile(t, flags) for t in self._re_prefix_patterns]

        # We compile one more set of regexes, similar to `_re_prefix`, but accept any trailing
        # input. This will ensure that we can still highlight the input correctly, even when the
        # input contains some additional characters at the end that don't match the grammar.)
        self._re_prefix_with_trailing_input = [
            re.compile(
                r"(?:{})(?P<{}>.*?)$".format(t.rstrip("$"), _INVALID_TRAILING_INPUT),
                flags,
            )
            for t in self._re_prefix_patterns
        ]

    def escape(self, varname: str, value: str) -> str:
        """
        Escape `value` to fit in the place of this variable into the grammar.
        """
        f = self.escape_funcs.get(varname)
        return f(value) if f else value

    def unescape(self, varname: str, value: str) -> str:
        """
        Unescape `value`.
        """
        f = self.unescape_funcs.get(varname)
        return f(value) if f else value

    @classmethod
    def _transform(
        cls, root_node: Node, create_group_func: Callable[[Variable], str]
    ) -> str:
        """
        Turn a :class:`Node` object into a regular expression.

        :param root_node: The :class:`Node` instance for which we generate the grammar.
        :param create_group_func: A callable which takes a `Node` and returns the next
            free name for this node.
        """

        def transform(node: Node) -> str:
            # Turn `AnyNode` into an OR.
            if isinstance(node, AnyNode):
                return "(?:{})".format("|".join(transform(c) for c in node.children))

            # Concatenate a `NodeSequence`
            elif isinstance(node, NodeSequence):
                return "".join(transform(c) for c in node.children)

            # For Regex and Lookahead nodes, just insert them literally.
            elif isinstance(node, Regex):
                return node.regex

            elif isinstance(node, Lookahead):
                before = "(?!" if node.negative else "(="
                return before + transform(node.childnode) + ")"

            # A `Variable` wraps the children into a named group.
            elif isinstance(node, Variable):
                return f"(?P<{create_group_func(node)}>{transform(node.childnode)})"

            # `Repeat`.
            elif isinstance(node, Repeat):
                if node.max_repeat is None:
                    if node.min_repeat == 0:
                        repeat_sign = "*"
                    elif node.min_repeat == 1:
                        repeat_sign = "+"
                else:
                    repeat_sign = "{%i,%s}" % (
                        node.min_repeat,
                        ("" if node.max_repeat is None else str(node.max_repeat)),
                    )

                return "(?:{}){}{}".format(
                    transform(node.childnode),
                    repeat_sign,
                    ("" if node.greedy else "?"),
                )
            else:
                raise TypeError(f"Got {node!r}")

        return transform(root_node)

    @classmethod
    def _transform_prefix(
        cls, root_node: Node, create_group_func: Callable[[Variable], str]
    ) -> Iterable[str]:
        """
        Yield all the regular expressions matching a prefix of the grammar
        defined by the `Node` instance.

        For each `Variable`, one regex pattern will be generated, with this
        named group at the end. This is required because a regex engine will
        terminate once a match is found. For autocompletion however, we need
        the matches for all possible paths, so that we can provide completions
        for each `Variable`.

        - So, in the case of an `Any` (`A|B|C)', we generate a pattern for each
          clause. This is one for `A`, one for `B` and one for `C`. Unless some
          groups don't contain a `Variable`, then these can be merged together.
        - In the case of a `NodeSequence` (`ABC`), we generate a pattern for
          each prefix that ends with a variable, and one pattern for the whole
          sequence. So, that's one for `A`, one for `AB` and one for `ABC`.

        :param root_node: The :class:`Node` instance for which we generate the grammar.
        :param create_group_func: A callable which takes a `Node` and returns the next
            free name for this node.
        """

        def contains_variable(node: Node) -> bool:
            if isinstance(node, Regex):
                return False
            elif isinstance(node, Variable):
                return True
            elif isinstance(node, (Lookahead, Repeat)):
                return contains_variable(node.childnode)
            elif isinstance(node, (NodeSequence, AnyNode)):
                return any(contains_variable(child) for child in node.children)

            return False

        def transform(node: Node) -> Iterable[str]:
            # Generate separate pattern for all terms that contain variables
            # within this OR. Terms that don't contain a variable can be merged
            # together in one pattern.
            if isinstance(node, AnyNode):
                # If we have a definition like:
                #           (?P<name> .*)  | (?P<city> .*)
                # Then we want to be able to generate completions for both the
                # name as well as the city. We do this by yielding two
                # different regular expressions, because the engine won't
                # follow multiple paths, if multiple are possible.
                children_with_variable = []
                children_without_variable = []
                for c in node.children:
                    if contains_variable(c):
                        children_with_variable.append(c)
                    else:
                        children_without_variable.append(c)

                for c in children_with_variable:
                    yield from transform(c)

                # Merge options without variable together.
                if children_without_variable:
                    yield "|".join(
                        r for c in children_without_variable for r in transform(c)
                    )

            # For a sequence, generate a pattern for each prefix that ends with
            # a variable + one pattern of the complete sequence.
            # (This is because, for autocompletion, we match the text before
            # the cursor, and completions are given for the variable that we
            # match right before the cursor.)
            elif isinstance(node, NodeSequence):
                # For all components in the sequence, compute prefix patterns,
                # as well as full patterns.
                complete = [cls._transform(c, create_group_func) for c in node.children]
                prefixes = [list(transform(c)) for c in node.children]
                variable_nodes = [contains_variable(c) for c in node.children]

                # If any child is contains a variable, we should yield a
                # pattern up to that point, so that we are sure this will be
                # matched.
                for i in range(len(node.children)):
                    if variable_nodes[i]:
                        for c_str in prefixes[i]:
                            yield "".join(complete[:i]) + c_str

                # If there are non-variable nodes, merge all the prefixes into
                # one pattern. If the input is: "[part1] [part2] [part3]", then
                # this gets compiled into:
                #  (complete1 + (complete2 + (complete3  | partial3) | partial2) | partial1 )
                # For nodes that contain a variable, we skip the "|partial"
                # part here, because thees are matched with the previous
                # patterns.
                if not all(variable_nodes):
                    result = []

                    # Start with complete patterns.
                    for i in range(len(node.children)):
                        result.append("(?:")
                        result.append(complete[i])

                    # Add prefix patterns.
                    for i in range(len(node.children) - 1, -1, -1):
                        if variable_nodes[i]:
                            # No need to yield a prefix for this one, we did
                            # the variable prefixes earlier.
                            result.append(")")
                        else:
                            result.append("|(?:")
                            # If this yields multiple, we should yield all combinations.
                            assert len(prefixes[i]) == 1
                            result.append(prefixes[i][0])
                            result.append("))")

                    yield "".join(result)

            elif isinstance(node, Regex):
                yield f"(?:{node.regex})?"

            elif isinstance(node, Lookahead):
                if node.negative:
                    yield f"(?!{cls._transform(node.childnode, create_group_func)})"
                else:
                    # Not sure what the correct semantics are in this case.
                    # (Probably it's not worth implementing this.)
                    raise Exception("Positive lookahead not yet supported.")

            elif isinstance(node, Variable):
                # (Note that we should not append a '?' here. the 'transform'
                # method will already recursively do that.)
                for c_str in transform(node.childnode):
                    yield f"(?P<{create_group_func(node)}>{c_str})"

            elif isinstance(node, Repeat):
                # If we have a repetition of 8 times. That would mean that the
                # current input could have for instance 7 times a complete
                # match, followed by a partial match.
                prefix = cls._transform(node.childnode, create_group_func)

                if node.max_repeat == 1:
                    yield from transform(node.childnode)
                else:
                    for c_str in transform(node.childnode):
                        if node.max_repeat:
                            repeat_sign = "{,%i}" % (node.max_repeat - 1)
                        else:
                            repeat_sign = "*"
                        yield "(?:{}){}{}{}".format(
                            prefix,
                            repeat_sign,
                            ("" if node.greedy else "?"),
                            c_str,
                        )

            else:
                raise TypeError(f"Got {node!r}")

        for r in transform(root_node):
            yield f"^(?:{r})$"

    def match(self, string: str) -> Match | None:
        """
        Match the string with the grammar.
        Returns a :class:`Match` instance or `None` when the input doesn't match the grammar.

        :param string: The input string.
        """
        m = self._re.match(string)

        if m:
            return Match(
                string, [(self._re, m)], self._group_names_to_nodes, self.unescape_funcs
            )
        return None

    def match_prefix(self, string: str) -> Match | None:
        """
        Do a partial match of the string with the grammar. The returned
        :class:`Match` instance can contain multiple representations of the
        match. This will never return `None`. If it doesn't match at all, the "trailing input"
        part will capture all of the input.

        :param string: The input string.
        """
        # First try to match using `_re_prefix`. If nothing is found, use the patterns that
        # also accept trailing characters.
        for patterns in [self._re_prefix, self._re_prefix_with_trailing_input]:
            matches = [(r, r.match(string)) for r in patterns]
            matches2 = [(r, m) for r, m in matches if m]

            if matches2 != []:
                return Match(
                    string, matches2, self._group_names_to_nodes, self.unescape_funcs
                )

        return None


class Match:
    """
    :param string: The input string.
    :param re_matches: List of (compiled_re_pattern, re_match) tuples.
    :param group_names_to_nodes: Dictionary mapping all the re group names to the matching Node instances.
    """

    def __init__(
        self,
        string: str,
        re_matches: list[tuple[Pattern[str], RegexMatch[str]]],
        group_names_to_nodes: dict[str, str],
        unescape_funcs: dict[str, Callable[[str], str]],
    ):
        self.string = string
        self._re_matches = re_matches
        self._group_names_to_nodes = group_names_to_nodes
        self._unescape_funcs = unescape_funcs

    def _nodes_to_regs(self) -> list[tuple[str, tuple[int, int]]]:
        """
        Return a list of (varname, reg) tuples.
        """

        def get_tuples() -> Iterable[tuple[str, tuple[int, int]]]:
            for r, re_match in self._re_matches:
                for group_name, group_index in r.groupindex.items():
                    if group_name != _INVALID_TRAILING_INPUT:
                        regs = re_match.regs
                        reg = regs[group_index]
                        node = self._group_names_to_nodes[group_name]
                        yield (node, reg)

        return list(get_tuples())

    def _nodes_to_values(self) -> list[tuple[str, str, tuple[int, int]]]:
        """
        Returns list of (Node, string_value) tuples.
        """

        def is_none(sl: tuple[int, int]) -> bool:
            return sl[0] == -1 and sl[1] == -1

        def get(sl: tuple[int, int]) -> str:
            return self.string[sl[0] : sl[1]]

        return [
            (varname, get(slice), slice)
            for varname, slice in self._nodes_to_regs()
            if not is_none(slice)
        ]

    def _unescape(self, varname: str, value: str) -> str:
        unwrapper = self._unescape_funcs.get(varname)
        return unwrapper(value) if unwrapper else value

    def variables(self) -> Variables:
        """
        Returns :class:`Variables` instance.
        """
        return Variables(
            [(k, self._unescape(k, v), sl) for k, v, sl in self._nodes_to_values()]
        )

    def trailing_input(self) -> MatchVariable | None:
        """
        Get the `MatchVariable` instance, representing trailing input, if there is any.
        "Trailing input" is input at the end that does not match the grammar anymore, but
        when this is removed from the end of the input, the input would be a valid string.
        """
        slices: list[tuple[int, int]] = []

        # Find all regex group for the name _INVALID_TRAILING_INPUT.
        for r, re_match in self._re_matches:
            for group_name, group_index in r.groupindex.items():
                if group_name == _INVALID_TRAILING_INPUT:
                    slices.append(re_match.regs[group_index])

        # Take the smallest part. (Smaller trailing text means that a larger input has
        # been matched, so that is better.)
        if slices:
            slice = (max(i[0] for i in slices), max(i[1] for i in slices))
            value = self.string[slice[0] : slice[1]]
            return MatchVariable("<trailing_input>", value, slice)
        return None

    def end_nodes(self) -> Iterable[MatchVariable]:
        """
        Yields `MatchVariable` instances for all the nodes having their end
        position at the end of the input string.
        """
        for varname, reg in self._nodes_to_regs():
            # If this part goes until the end of the input string.
            if reg[1] == len(self.string):
                value = self._unescape(varname, self.string[reg[0] : reg[1]])
                yield MatchVariable(varname, value, (reg[0], reg[1]))


_T = TypeVar("_T")


class Variables:
    def __init__(self, tuples: list[tuple[str, str, tuple[int, int]]]) -> None:
        #: List of (varname, value, slice) tuples.
        self._tuples = tuples

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v, _ in self._tuples),
        )

    @overload
    def get(self, key: str) -> str | None: ...

    @overload
    def get(self, key: str, default: str | _T) -> str | _T: ...

    def get(self, key: str, default: str | _T | None = None) -> str | _T | None:
        items = self.getall(key)
        return items[0] if items else default

    def getall(self, key: str) -> list[str]:
        return [v for k, v, _ in self._tuples if k == key]

    def __getitem__(self, key: str) -> str | None:
        return self.get(key)

    def __iter__(self) -> Iterator[MatchVariable]:
        """
        Yield `MatchVariable` instances.
        """
        for varname, value, slice in self._tuples:
            yield MatchVariable(varname, value, slice)


class MatchVariable:
    """
    Represents a match of a variable in the grammar.

    :param varname: (string) Name of the variable.
    :param value: (string) Value of this variable.
    :param slice: (start, stop) tuple, indicating the position of this variable
                  in the input string.
    """

    def __init__(self, varname: str, value: str, slice: tuple[int, int]) -> None:
        self.varname = varname
        self.value = value
        self.slice = slice

        self.start = self.slice[0]
        self.stop = self.slice[1]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.varname!r}, {self.value!r})"


def compile(
    expression: str,
    escape_funcs: EscapeFuncDict | None = None,
    unescape_funcs: EscapeFuncDict | None = None,
) -> _CompiledGrammar:
    """
    Compile grammar (given as regex string), returning a `CompiledGrammar`
    instance.
    """
    return _compile_from_parse_tree(
        parse_regex(tokenize_regex(expression)),
        escape_funcs=escape_funcs,
        unescape_funcs=unescape_funcs,
    )


def _compile_from_parse_tree(
    root_node: Node,
    escape_funcs: EscapeFuncDict | None = None,
    unescape_funcs: EscapeFuncDict | None = None,
) -> _CompiledGrammar:
    """
    Compile grammar (given as parse tree), returning a `CompiledGrammar`
    instance.
    """
    return _CompiledGrammar(
        root_node, escape_funcs=escape_funcs, unescape_funcs=unescape_funcs
    )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\web_authn.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: WebAuthn (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class AuthenticatorId(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> AuthenticatorId:
        return cls(json)

    def __repr__(self):
        return 'AuthenticatorId({})'.format(super().__repr__())


class AuthenticatorProtocol(enum.Enum):
    U2F = "u2f"
    CTAP2 = "ctap2"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class Ctap2Version(enum.Enum):
    CTAP2_0 = "ctap2_0"
    CTAP2_1 = "ctap2_1"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AuthenticatorTransport(enum.Enum):
    USB = "usb"
    NFC = "nfc"
    BLE = "ble"
    CABLE = "cable"
    INTERNAL = "internal"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class VirtualAuthenticatorOptions:
    protocol: AuthenticatorProtocol

    transport: AuthenticatorTransport

    #: Defaults to ctap2_0. Ignored if ``protocol`` == u2f.
    ctap2_version: typing.Optional[Ctap2Version] = None

    #: Defaults to false.
    has_resident_key: typing.Optional[bool] = None

    #: Defaults to false.
    has_user_verification: typing.Optional[bool] = None

    #: If set to true, the authenticator will support the largeBlob extension.
    #: https://w3c.github.io/webauthn#largeBlob
    #: Defaults to false.
    has_large_blob: typing.Optional[bool] = None

    #: If set to true, the authenticator will support the credBlob extension.
    #: https://fidoalliance.org/specs/fido-v2.1-rd-20201208/fido-client-to-authenticator-protocol-v2.1-rd-20201208.html#sctn-credBlob-extension
    #: Defaults to false.
    has_cred_blob: typing.Optional[bool] = None

    #: If set to true, the authenticator will support the minPinLength extension.
    #: https://fidoalliance.org/specs/fido-v2.1-ps-20210615/fido-client-to-authenticator-protocol-v2.1-ps-20210615.html#sctn-minpinlength-extension
    #: Defaults to false.
    has_min_pin_length: typing.Optional[bool] = None

    #: If set to true, the authenticator will support the prf extension.
    #: https://w3c.github.io/webauthn/#prf-extension
    #: Defaults to false.
    has_prf: typing.Optional[bool] = None

    #: If set to true, tests of user presence will succeed immediately.
    #: Otherwise, they will not be resolved. Defaults to true.
    automatic_presence_simulation: typing.Optional[bool] = None

    #: Sets whether User Verification succeeds or fails for an authenticator.
    #: Defaults to false.
    is_user_verified: typing.Optional[bool] = None

    #: Credentials created by this authenticator will have the backup
    #: eligibility (BE) flag set to this value. Defaults to false.
    #: https://w3c.github.io/webauthn/#sctn-credential-backup
    default_backup_eligibility: typing.Optional[bool] = None

    #: Credentials created by this authenticator will have the backup state
    #: (BS) flag set to this value. Defaults to false.
    #: https://w3c.github.io/webauthn/#sctn-credential-backup
    default_backup_state: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol.to_json()
        json['transport'] = self.transport.to_json()
        if self.ctap2_version is not None:
            json['ctap2Version'] = self.ctap2_version.to_json()
        if self.has_resident_key is not None:
            json['hasResidentKey'] = self.has_resident_key
        if self.has_user_verification is not None:
            json['hasUserVerification'] = self.has_user_verification
        if self.has_large_blob is not None:
            json['hasLargeBlob'] = self.has_large_blob
        if self.has_cred_blob is not None:
            json['hasCredBlob'] = self.has_cred_blob
        if self.has_min_pin_length is not None:
            json['hasMinPinLength'] = self.has_min_pin_length
        if self.has_prf is not None:
            json['hasPrf'] = self.has_prf
        if self.automatic_presence_simulation is not None:
            json['automaticPresenceSimulation'] = self.automatic_presence_simulation
        if self.is_user_verified is not None:
            json['isUserVerified'] = self.is_user_verified
        if self.default_backup_eligibility is not None:
            json['defaultBackupEligibility'] = self.default_backup_eligibility
        if self.default_backup_state is not None:
            json['defaultBackupState'] = self.default_backup_state
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=AuthenticatorProtocol.from_json(json['protocol']),
            transport=AuthenticatorTransport.from_json(json['transport']),
            ctap2_version=Ctap2Version.from_json(json['ctap2Version']) if 'ctap2Version' in json else None,
            has_resident_key=bool(json['hasResidentKey']) if 'hasResidentKey' in json else None,
            has_user_verification=bool(json['hasUserVerification']) if 'hasUserVerification' in json else None,
            has_large_blob=bool(json['hasLargeBlob']) if 'hasLargeBlob' in json else None,
            has_cred_blob=bool(json['hasCredBlob']) if 'hasCredBlob' in json else None,
            has_min_pin_length=bool(json['hasMinPinLength']) if 'hasMinPinLength' in json else None,
            has_prf=bool(json['hasPrf']) if 'hasPrf' in json else None,
            automatic_presence_simulation=bool(json['automaticPresenceSimulation']) if 'automaticPresenceSimulation' in json else None,
            is_user_verified=bool(json['isUserVerified']) if 'isUserVerified' in json else None,
            default_backup_eligibility=bool(json['defaultBackupEligibility']) if 'defaultBackupEligibility' in json else None,
            default_backup_state=bool(json['defaultBackupState']) if 'defaultBackupState' in json else None,
        )


@dataclass
class Credential:
    credential_id: str

    is_resident_credential: bool

    #: The ECDSA P-256 private key in PKCS#8 format.
    private_key: str

    #: Signature counter. This is incremented by one for each successful
    #: assertion.
    #: See https://w3c.github.io/webauthn/#signature-counter
    sign_count: int

    #: Relying Party ID the credential is scoped to. Must be set when adding a
    #: credential.
    rp_id: typing.Optional[str] = None

    #: An opaque byte sequence with a maximum size of 64 bytes mapping the
    #: credential to a specific user.
    user_handle: typing.Optional[str] = None

    #: The large blob associated with the credential.
    #: See https://w3c.github.io/webauthn/#sctn-large-blob-extension
    large_blob: typing.Optional[str] = None

    #: Assertions returned by this credential will have the backup eligibility
    #: (BE) flag set to this value. Defaults to the authenticator's
    #: defaultBackupEligibility value.
    backup_eligibility: typing.Optional[bool] = None

    #: Assertions returned by this credential will have the backup state (BS)
    #: flag set to this value. Defaults to the authenticator's
    #: defaultBackupState value.
    backup_state: typing.Optional[bool] = None

    #: The credential's user.name property. Equivalent to empty if not set.
    #: https://w3c.github.io/webauthn/#dom-publickeycredentialentity-name
    user_name: typing.Optional[str] = None

    #: The credential's user.displayName property. Equivalent to empty if
    #: not set.
    #: https://w3c.github.io/webauthn/#dom-publickeycredentialuserentity-displayname
    user_display_name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['credentialId'] = self.credential_id
        json['isResidentCredential'] = self.is_resident_credential
        json['privateKey'] = self.private_key
        json['signCount'] = self.sign_count
        if self.rp_id is not None:
            json['rpId'] = self.rp_id
        if self.user_handle is not None:
            json['userHandle'] = self.user_handle
        if self.large_blob is not None:
            json['largeBlob'] = self.large_blob
        if self.backup_eligibility is not None:
            json['backupEligibility'] = self.backup_eligibility
        if self.backup_state is not None:
            json['backupState'] = self.backup_state
        if self.user_name is not None:
            json['userName'] = self.user_name
        if self.user_display_name is not None:
            json['userDisplayName'] = self.user_display_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            credential_id=str(json['credentialId']),
            is_resident_credential=bool(json['isResidentCredential']),
            private_key=str(json['privateKey']),
            sign_count=int(json['signCount']),
            rp_id=str(json['rpId']) if 'rpId' in json else None,
            user_handle=str(json['userHandle']) if 'userHandle' in json else None,
            large_blob=str(json['largeBlob']) if 'largeBlob' in json else None,
            backup_eligibility=bool(json['backupEligibility']) if 'backupEligibility' in json else None,
            backup_state=bool(json['backupState']) if 'backupState' in json else None,
            user_name=str(json['userName']) if 'userName' in json else None,
            user_display_name=str(json['userDisplayName']) if 'userDisplayName' in json else None,
        )


def enable(
        enable_ui: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable the WebAuthn domain and start intercepting credential storage and
    retrieval with a virtual authenticator.

    :param enable_ui: *(Optional)* Whether to enable the WebAuthn user interface. Enabling the UI is recommended for debugging and demo purposes, as it is closer to the real experience. Disabling the UI is recommended for automated testing. Supported at the embedder's discretion if UI is available. Defaults to false.
    '''
    params: T_JSON_DICT = dict()
    if enable_ui is not None:
        params['enableUI'] = enable_ui
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable the WebAuthn domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.disable',
    }
    json = yield cmd_dict


def add_virtual_authenticator(
        options: VirtualAuthenticatorOptions
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,AuthenticatorId]:
    '''
    Creates and adds a virtual authenticator.

    :param options:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['options'] = options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.addVirtualAuthenticator',
        'params': params,
    }
    json = yield cmd_dict
    return AuthenticatorId.from_json(json['authenticatorId'])


def set_response_override_bits(
        authenticator_id: AuthenticatorId,
        is_bogus_signature: typing.Optional[bool] = None,
        is_bad_uv: typing.Optional[bool] = None,
        is_bad_up: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets parameters isBogusSignature, isBadUV, isBadUP to false if they are not present.

    :param authenticator_id:
    :param is_bogus_signature: *(Optional)* If isBogusSignature is set, overrides the signature in the authenticator response to be zero. Defaults to false.
    :param is_bad_uv: *(Optional)* If isBadUV is set, overrides the UV bit in the flags in the authenticator response to be zero. Defaults to false.
    :param is_bad_up: *(Optional)* If isBadUP is set, overrides the UP bit in the flags in the authenticator response to be zero. Defaults to false.
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    if is_bogus_signature is not None:
        params['isBogusSignature'] = is_bogus_signature
    if is_bad_uv is not None:
        params['isBadUV'] = is_bad_uv
    if is_bad_up is not None:
        params['isBadUP'] = is_bad_up
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.setResponseOverrideBits',
        'params': params,
    }
    json = yield cmd_dict


def remove_virtual_authenticator(
        authenticator_id: AuthenticatorId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the given authenticator.

    :param authenticator_id:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.removeVirtualAuthenticator',
        'params': params,
    }
    json = yield cmd_dict


def add_credential(
        authenticator_id: AuthenticatorId,
        credential: Credential
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Adds the credential to the specified authenticator.

    :param authenticator_id:
    :param credential:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['credential'] = credential.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.addCredential',
        'params': params,
    }
    json = yield cmd_dict


def get_credential(
        authenticator_id: AuthenticatorId,
        credential_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Credential]:
    '''
    Returns a single credential stored in the given virtual authenticator that
    matches the credential ID.

    :param authenticator_id:
    :param credential_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['credentialId'] = credential_id
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.getCredential',
        'params': params,
    }
    json = yield cmd_dict
    return Credential.from_json(json['credential'])


def get_credentials(
        authenticator_id: AuthenticatorId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Credential]]:
    '''
    Returns all the credentials stored in the given virtual authenticator.

    :param authenticator_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.getCredentials',
        'params': params,
    }
    json = yield cmd_dict
    return [Credential.from_json(i) for i in json['credentials']]


def remove_credential(
        authenticator_id: AuthenticatorId,
        credential_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes a credential from the authenticator.

    :param authenticator_id:
    :param credential_id:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['credentialId'] = credential_id
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.removeCredential',
        'params': params,
    }
    json = yield cmd_dict


def clear_credentials(
        authenticator_id: AuthenticatorId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all the credentials from the specified device.

    :param authenticator_id:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.clearCredentials',
        'params': params,
    }
    json = yield cmd_dict


def set_user_verified(
        authenticator_id: AuthenticatorId,
        is_user_verified: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets whether User Verification succeeds or fails for an authenticator.
    The default is true.

    :param authenticator_id:
    :param is_user_verified:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['isUserVerified'] = is_user_verified
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.setUserVerified',
        'params': params,
    }
    json = yield cmd_dict


def set_automatic_presence_simulation(
        authenticator_id: AuthenticatorId,
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets whether tests of user presence will succeed immediately (if true) or fail to resolve (if false) for an authenticator.
    The default is true.

    :param authenticator_id:
    :param enabled:
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.setAutomaticPresenceSimulation',
        'params': params,
    }
    json = yield cmd_dict


def set_credential_properties(
        authenticator_id: AuthenticatorId,
        credential_id: str,
        backup_eligibility: typing.Optional[bool] = None,
        backup_state: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows setting credential properties.
    https://w3c.github.io/webauthn/#sctn-automation-set-credential-properties

    :param authenticator_id:
    :param credential_id:
    :param backup_eligibility: *(Optional)*
    :param backup_state: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['authenticatorId'] = authenticator_id.to_json()
    params['credentialId'] = credential_id
    if backup_eligibility is not None:
        params['backupEligibility'] = backup_eligibility
    if backup_state is not None:
        params['backupState'] = backup_state
    cmd_dict: T_JSON_DICT = {
        'method': 'WebAuthn.setCredentialProperties',
        'params': params,
    }
    json = yield cmd_dict


@event_class('WebAuthn.credentialAdded')
@dataclass
class CredentialAdded:
    '''
    Triggered when a credential is added to an authenticator.
    '''
    authenticator_id: AuthenticatorId
    credential: Credential

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CredentialAdded:
        return cls(
            authenticator_id=AuthenticatorId.from_json(json['authenticatorId']),
            credential=Credential.from_json(json['credential'])
        )


@event_class('WebAuthn.credentialDeleted')
@dataclass
class CredentialDeleted:
    '''
    Triggered when a credential is deleted, e.g. through
    PublicKeyCredential.signalUnknownCredential().
    '''
    authenticator_id: AuthenticatorId
    credential_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CredentialDeleted:
        return cls(
            authenticator_id=AuthenticatorId.from_json(json['authenticatorId']),
            credential_id=str(json['credentialId'])
        )


@event_class('WebAuthn.credentialUpdated')
@dataclass
class CredentialUpdated:
    '''
    Triggered when a credential is updated, e.g. through
    PublicKeyCredential.signalCurrentUserDetails().
    '''
    authenticator_id: AuthenticatorId
    credential: Credential

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CredentialUpdated:
        return cls(
            authenticator_id=AuthenticatorId.from_json(json['authenticatorId']),
            credential=Credential.from_json(json['credential'])
        )


@event_class('WebAuthn.credentialAsserted')
@dataclass
class CredentialAsserted:
    '''
    Triggered when a credential is used in a webauthn assertion.
    '''
    authenticator_id: AuthenticatorId
    credential: Credential

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CredentialAsserted:
        return cls(
            authenticator_id=AuthenticatorId.from_json(json['authenticatorId']),
            credential=Credential.from_json(json['credential'])
        )