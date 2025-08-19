
# === NexusCore/tools\exports\export_20250803_114325\combined_137.py ===

# === NexusCore/openenv\Lib\site-packages\google\api_core\bidi.py ===
# Copyright 2017, Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bi-directional streaming RPC helpers."""

import collections
import datetime
import logging
import queue as queue_module
import threading
import time

from google.api_core import exceptions

_LOGGER = logging.getLogger(__name__)
_BIDIRECTIONAL_CONSUMER_NAME = "Thread-ConsumeBidirectionalStream"


class _RequestQueueGenerator(object):
    """A helper for sending requests to a gRPC stream from a Queue.

    This generator takes requests off a given queue and yields them to gRPC.

    This helper is useful when you have an indeterminate, indefinite, or
    otherwise open-ended set of requests to send through a request-streaming
    (or bidirectional) RPC.

    The reason this is necessary is because gRPC takes an iterator as the
    request for request-streaming RPCs. gRPC consumes this iterator in another
    thread to allow it to block while generating requests for the stream.
    However, if the generator blocks indefinitely gRPC will not be able to
    clean up the thread as it'll be blocked on `next(iterator)` and not be able
    to check the channel status to stop iterating. This helper mitigates that
    by waiting on the queue with a timeout and checking the RPC state before
    yielding.

    Finally, it allows for retrying without swapping queues because if it does
    pull an item off the queue when the RPC is inactive, it'll immediately put
    it back and then exit. This is necessary because yielding the item in this
    case will cause gRPC to discard it. In practice, this means that the order
    of messages is not guaranteed. If such a thing is necessary it would be
    easy to use a priority queue.

    Example::

        requests = request_queue_generator(q)
        call = stub.StreamingRequest(iter(requests))
        requests.call = call

        for response in call:
            print(response)
            q.put(...)

    Note that it is possible to accomplish this behavior without "spinning"
    (using a queue timeout). One possible way would be to use more threads to
    multiplex the grpc end event with the queue, another possible way is to
    use selectors and a custom event/queue object. Both of these approaches
    are significant from an engineering perspective for small benefit - the
    CPU consumed by spinning is pretty minuscule.

    Args:
        queue (queue_module.Queue): The request queue.
        period (float): The number of seconds to wait for items from the queue
            before checking if the RPC is cancelled. In practice, this
            determines the maximum amount of time the request consumption
            thread will live after the RPC is cancelled.
        initial_request (Union[protobuf.Message,
                Callable[None, protobuf.Message]]): The initial request to
            yield. This is done independently of the request queue to allow fo
            easily restarting streams that require some initial configuration
            request.
    """

    def __init__(self, queue, period=1, initial_request=None):
        self._queue = queue
        self._period = period
        self._initial_request = initial_request
        self.call = None

    def _is_active(self):
        # Note: there is a possibility that this starts *before* the call
        # property is set. So we have to check if self.call is set before
        # seeing if it's active. We need to return True if self.call is None.
        # See https://github.com/googleapis/python-api-core/issues/560.
        return self.call is None or self.call.is_active()

    def __iter__(self):
        if self._initial_request is not None:
            if callable(self._initial_request):
                yield self._initial_request()
            else:
                yield self._initial_request

        while True:
            try:
                item = self._queue.get(timeout=self._period)
            except queue_module.Empty:
                if not self._is_active():
                    _LOGGER.debug(
                        "Empty queue and inactive call, exiting request " "generator."
                    )
                    return
                else:
                    # call is still active, keep waiting for queue items.
                    continue

            # The consumer explicitly sent "None", indicating that the request
            # should end.
            if item is None:
                _LOGGER.debug("Cleanly exiting request generator.")
                return

            if not self._is_active():
                # We have an item, but the call is closed. We should put the
                # item back on the queue so that the next call can consume it.
                self._queue.put(item)
                _LOGGER.debug(
                    "Inactive call, replacing item on queue and exiting "
                    "request generator."
                )
                return

            yield item


class _Throttle(object):
    """A context manager limiting the total entries in a sliding time window.

    If more than ``access_limit`` attempts are made to enter the context manager
    instance in the last ``time window`` interval, the exceeding requests block
    until enough time elapses.

    The context manager instances are thread-safe and can be shared between
    multiple threads. If multiple requests are blocked and waiting to enter,
    the exact order in which they are allowed to proceed is not determined.

    Example::

        max_three_per_second = _Throttle(
            access_limit=3, time_window=datetime.timedelta(seconds=1)
        )

        for i in range(5):
            with max_three_per_second as time_waited:
                print("{}: Waited {} seconds to enter".format(i, time_waited))

    Args:
        access_limit (int): the maximum number of entries allowed in the time window
        time_window (datetime.timedelta): the width of the sliding time window
    """

    def __init__(self, access_limit, time_window):
        if access_limit < 1:
            raise ValueError("access_limit argument must be positive")

        if time_window <= datetime.timedelta(0):
            raise ValueError("time_window argument must be a positive timedelta")

        self._time_window = time_window
        self._access_limit = access_limit
        self._past_entries = collections.deque(
            maxlen=access_limit
        )  # least recent first
        self._entry_lock = threading.Lock()

    def __enter__(self):
        with self._entry_lock:
            cutoff_time = datetime.datetime.now() - self._time_window

            # drop the entries that are too old, as they are no longer relevant
            while self._past_entries and self._past_entries[0] < cutoff_time:
                self._past_entries.popleft()

            if len(self._past_entries) < self._access_limit:
                self._past_entries.append(datetime.datetime.now())
                return 0.0  # no waiting was needed

            to_wait = (self._past_entries[0] - cutoff_time).total_seconds()
            time.sleep(to_wait)

            self._past_entries.append(datetime.datetime.now())
            return to_wait

    def __exit__(self, *_):
        pass

    def __repr__(self):
        return "{}(access_limit={}, time_window={})".format(
            self.__class__.__name__, self._access_limit, repr(self._time_window)
        )


class BidiRpc(object):
    """A helper for consuming a bi-directional streaming RPC.

    This maps gRPC's built-in interface which uses a request iterator and a
    response iterator into a socket-like :func:`send` and :func:`recv`. This
    is a more useful pattern for long-running or asymmetric streams (streams
    where there is not a direct correlation between the requests and
    responses).

    Example::

        initial_request = example_pb2.StreamingRpcRequest(
            setting='example')
        rpc = BidiRpc(
            stub.StreamingRpc,
            initial_request=initial_request,
            metadata=[('name', 'value')]
        )

        rpc.open()

        while rpc.is_active():
            print(rpc.recv())
            rpc.send(example_pb2.StreamingRpcRequest(
                data='example'))

    This does *not* retry the stream on errors. See :class:`ResumableBidiRpc`.

    Args:
        start_rpc (grpc.StreamStreamMultiCallable): The gRPC method used to
            start the RPC.
        initial_request (Union[protobuf.Message,
                Callable[None, protobuf.Message]]): The initial request to
            yield. This is useful if an initial request is needed to start the
            stream.
        metadata (Sequence[Tuple(str, str)]): RPC metadata to include in
            the request.
    """

    def __init__(self, start_rpc, initial_request=None, metadata=None):
        self._start_rpc = start_rpc
        self._initial_request = initial_request
        self._rpc_metadata = metadata
        self._request_queue = queue_module.Queue()
        self._request_generator = None
        self._is_active = False
        self._callbacks = []
        self.call = None

    def add_done_callback(self, callback):
        """Adds a callback that will be called when the RPC terminates.

        This occurs when the RPC errors or is successfully terminated.

        Args:
            callback (Callable[[grpc.Future], None]): The callback to execute.
                It will be provided with the same gRPC future as the underlying
                stream which will also be a :class:`grpc.Call`.
        """
        self._callbacks.append(callback)

    def _on_call_done(self, future):
        # This occurs when the RPC errors or is successfully terminated.
        # Note that grpc's "future" here can also be a grpc.RpcError.
        # See note in https://github.com/grpc/grpc/issues/10885#issuecomment-302651331
        # that `grpc.RpcError` is also `grpc.call`.
        for callback in self._callbacks:
            callback(future)

    def open(self):
        """Opens the stream."""
        if self.is_active:
            raise ValueError("Can not open an already open stream.")

        request_generator = _RequestQueueGenerator(
            self._request_queue, initial_request=self._initial_request
        )
        try:
            call = self._start_rpc(iter(request_generator), metadata=self._rpc_metadata)
        except exceptions.GoogleAPICallError as exc:
            # The original `grpc.RpcError` (which is usually also a `grpc.Call`) is
            # available from the ``response`` property on the mapped exception.
            self._on_call_done(exc.response)
            raise

        request_generator.call = call

        # TODO: api_core should expose the future interface for wrapped
        # callables as well.
        if hasattr(call, "_wrapped"):  # pragma: NO COVER
            call._wrapped.add_done_callback(self._on_call_done)
        else:
            call.add_done_callback(self._on_call_done)

        self._request_generator = request_generator
        self.call = call

    def close(self):
        """Closes the stream."""
        if self.call is None:
            return

        self._request_queue.put(None)
        self.call.cancel()
        self._request_generator = None
        self._initial_request = None
        self._callbacks = []
        # Don't set self.call to None. Keep it around so that send/recv can
        # raise the error.

    def send(self, request):
        """Queue a message to be sent on the stream.

        Send is non-blocking.

        If the underlying RPC has been closed, this will raise.

        Args:
            request (protobuf.Message): The request to send.
        """
        if self.call is None:
            raise ValueError("Can not send() on an RPC that has never been open()ed.")

        # Don't use self.is_active(), as ResumableBidiRpc will overload it
        # to mean something semantically different.
        if self.call.is_active():
            self._request_queue.put(request)
        else:
            # calling next should cause the call to raise.
            next(self.call)

    def recv(self):
        """Wait for a message to be returned from the stream.

        Recv is blocking.

        If the underlying RPC has been closed, this will raise.

        Returns:
            protobuf.Message: The received message.
        """
        if self.call is None:
            raise ValueError("Can not recv() on an RPC that has never been open()ed.")

        return next(self.call)

    @property
    def is_active(self):
        """bool: True if this stream is currently open and active."""
        return self.call is not None and self.call.is_active()

    @property
    def pending_requests(self):
        """int: Returns an estimate of the number of queued requests."""
        return self._request_queue.qsize()


def _never_terminate(future_or_error):
    """By default, no errors cause BiDi termination."""
    return False


class ResumableBidiRpc(BidiRpc):
    """A :class:`BidiRpc` that can automatically resume the stream on errors.

    It uses the ``should_recover`` arg to determine if it should re-establish
    the stream on error.

    Example::

        def should_recover(exc):
            return (
                isinstance(exc, grpc.RpcError) and
                exc.code() == grpc.StatusCode.UNAVAILABLE)

        initial_request = example_pb2.StreamingRpcRequest(
            setting='example')

        metadata = [('header_name', 'value')]

        rpc = ResumableBidiRpc(
            stub.StreamingRpc,
            should_recover=should_recover,
            initial_request=initial_request,
            metadata=metadata
        )

        rpc.open()

        while rpc.is_active():
            print(rpc.recv())
            rpc.send(example_pb2.StreamingRpcRequest(
                data='example'))

    Args:
        start_rpc (grpc.StreamStreamMultiCallable): The gRPC method used to
            start the RPC.
        initial_request (Union[protobuf.Message,
                Callable[None, protobuf.Message]]): The initial request to
            yield. This is useful if an initial request is needed to start the
            stream.
        should_recover (Callable[[Exception], bool]): A function that returns
            True if the stream should be recovered. This will be called
            whenever an error is encountered on the stream.
        should_terminate (Callable[[Exception], bool]): A function that returns
            True if the stream should be terminated. This will be called
            whenever an error is encountered on the stream.
        metadata Sequence[Tuple(str, str)]: RPC metadata to include in
            the request.
        throttle_reopen (bool): If ``True``, throttling will be applied to
            stream reopen calls. Defaults to ``False``.
    """

    def __init__(
        self,
        start_rpc,
        should_recover,
        should_terminate=_never_terminate,
        initial_request=None,
        metadata=None,
        throttle_reopen=False,
    ):
        super(ResumableBidiRpc, self).__init__(start_rpc, initial_request, metadata)
        self._should_recover = should_recover
        self._should_terminate = should_terminate
        self._operational_lock = threading.RLock()
        self._finalized = False
        self._finalize_lock = threading.Lock()

        if throttle_reopen:
            self._reopen_throttle = _Throttle(
                access_limit=5, time_window=datetime.timedelta(seconds=10)
            )
        else:
            self._reopen_throttle = None

    def _finalize(self, result):
        with self._finalize_lock:
            if self._finalized:
                return

            for callback in self._callbacks:
                callback(result)

            self._finalized = True

    def _on_call_done(self, future):
        # Unlike the base class, we only execute the callbacks on a terminal
        # error, not for errors that we can recover from. Note that grpc's
        # "future" here is also a grpc.RpcError.
        with self._operational_lock:
            if self._should_terminate(future):
                self._finalize(future)
            elif not self._should_recover(future):
                self._finalize(future)
            else:
                _LOGGER.debug("Re-opening stream from gRPC callback.")
                self._reopen()

    def _reopen(self):
        with self._operational_lock:
            # Another thread already managed to re-open this stream.
            if self.call is not None and self.call.is_active():
                _LOGGER.debug("Stream was already re-established.")
                return

            self.call = None
            # Request generator should exit cleanly since the RPC its bound to
            # has exited.
            self._request_generator = None

            # Note: we do not currently do any sort of backoff here. The
            # assumption is that re-establishing the stream under normal
            # circumstances will happen in intervals greater than 60s.
            # However, it is possible in a degenerative case that the server
            # closes the stream rapidly which would lead to thrashing here,
            # but hopefully in those cases the server would return a non-
            # retryable error.

            try:
                if self._reopen_throttle:
                    with self._reopen_throttle:
                        self.open()
                else:
                    self.open()
            # If re-opening or re-calling the method fails for any reason,
            # consider it a terminal error and finalize the stream.
            except Exception as exc:
                _LOGGER.debug("Failed to re-open stream due to %s", exc)
                self._finalize(exc)
                raise

            _LOGGER.info("Re-established stream")

    def _recoverable(self, method, *args, **kwargs):
        """Wraps a method to recover the stream and retry on error.

        If a retryable error occurs while making the call, then the stream will
        be re-opened and the method will be retried. This happens indefinitely
        so long as the error is a retryable one. If an error occurs while
        re-opening the stream, then this method will raise immediately and
        trigger finalization of this object.

        Args:
            method (Callable[..., Any]): The method to call.
            args: The args to pass to the method.
            kwargs: The kwargs to pass to the method.
        """
        while True:
            try:
                return method(*args, **kwargs)

            except Exception as exc:
                with self._operational_lock:
                    _LOGGER.debug("Call to retryable %r caused %s.", method, exc)

                    if self._should_terminate(exc):
                        self.close()
                        _LOGGER.debug("Terminating %r due to %s.", method, exc)
                        self._finalize(exc)
                        break

                    if not self._should_recover(exc):
                        self.close()
                        _LOGGER.debug("Not retrying %r due to %s.", method, exc)
                        self._finalize(exc)
                        raise exc

                    _LOGGER.debug("Re-opening stream from retryable %r.", method)
                    self._reopen()

    def _send(self, request):
        # Grab a reference to the RPC call. Because another thread (notably
        # the gRPC error thread) can modify self.call (by invoking reopen),
        # we should ensure our reference can not change underneath us.
        # If self.call is modified (such as replaced with a new RPC call) then
        # this will use the "old" RPC, which should result in the same
        # exception passed into gRPC's error handler being raised here, which
        # will be handled by the usual error handling in retryable.
        with self._operational_lock:
            call = self.call

        if call is None:
            raise ValueError("Can not send() on an RPC that has never been open()ed.")

        # Don't use self.is_active(), as ResumableBidiRpc will overload it
        # to mean something semantically different.
        if call.is_active():
            self._request_queue.put(request)
            pass
        else:
            # calling next should cause the call to raise.
            next(call)

    def send(self, request):
        return self._recoverable(self._send, request)

    def _recv(self):
        with self._operational_lock:
            call = self.call

        if call is None:
            raise ValueError("Can not recv() on an RPC that has never been open()ed.")

        return next(call)

    def recv(self):
        return self._recoverable(self._recv)

    def close(self):
        self._finalize(None)
        super(ResumableBidiRpc, self).close()

    @property
    def is_active(self):
        """bool: True if this stream is currently open and active."""
        # Use the operational lock. It's entirely possible for something
        # to check the active state *while* the RPC is being retried.
        # Also, use finalized to track the actual terminal state here.
        # This is because if the stream is re-established by the gRPC thread
        # it's technically possible to check this between when gRPC marks the
        # RPC as inactive and when gRPC executes our callback that re-opens
        # the stream.
        with self._operational_lock:
            return self.call is not None and not self._finalized


class BackgroundConsumer(object):
    """A bi-directional stream consumer that runs in a separate thread.

    This maps the consumption of a stream into a callback-based model. It also
    provides :func:`pause` and :func:`resume` to allow for flow-control.

    Example::

        def should_recover(exc):
            return (
                isinstance(exc, grpc.RpcError) and
                exc.code() == grpc.StatusCode.UNAVAILABLE)

        initial_request = example_pb2.StreamingRpcRequest(
            setting='example')

        rpc = ResumeableBidiRpc(
            stub.StreamingRpc,
            initial_request=initial_request,
            should_recover=should_recover)

        def on_response(response):
            print(response)

        consumer = BackgroundConsumer(rpc, on_response)
        consumer.start()

    Note that error handling *must* be done by using the provided
    ``bidi_rpc``'s ``add_done_callback``. This helper will automatically exit
    whenever the RPC itself exits and will not provide any error details.

    Args:
        bidi_rpc (BidiRpc): The RPC to consume. Should not have been
            ``open()``ed yet.
        on_response (Callable[[protobuf.Message], None]): The callback to
            be called for every response on the stream.
        on_fatal_exception (Callable[[Exception], None]): The callback to
            be called on fatal errors during consumption. Default None.
    """

    def __init__(self, bidi_rpc, on_response, on_fatal_exception=None):
        self._bidi_rpc = bidi_rpc
        self._on_response = on_response
        self._paused = False
        self._on_fatal_exception = on_fatal_exception
        self._wake = threading.Condition()
        self._thread = None
        self._operational_lock = threading.Lock()

    def _on_call_done(self, future):
        # Resume the thread if it's paused, this prevents blocking forever
        # when the RPC has terminated.
        self.resume()

    def _thread_main(self, ready):
        try:
            ready.set()
            self._bidi_rpc.add_done_callback(self._on_call_done)
            self._bidi_rpc.open()

            while self._bidi_rpc.is_active:
                # Do not allow the paused status to change at all during this
                # section. There is a condition where we could be resumed
                # between checking if we are paused and calling wake.wait(),
                # which means that we will miss the notification to wake up
                # (oops!) and wait for a notification that will never come.
                # Keeping the lock throughout avoids that.
                # In the future, we could use `Condition.wait_for` if we drop
                # Python 2.7.
                # See: https://github.com/googleapis/python-api-core/issues/211
                with self._wake:
                    while self._paused:
                        _LOGGER.debug("paused, waiting for waking.")
                        self._wake.wait()
                        _LOGGER.debug("woken.")

                _LOGGER.debug("waiting for recv.")
                response = self._bidi_rpc.recv()
                _LOGGER.debug("recved response.")
                if self._on_response is not None:
                    self._on_response(response)

        except exceptions.GoogleAPICallError as exc:
            _LOGGER.debug(
                "%s caught error %s and will exit. Generally this is due to "
                "the RPC itself being cancelled and the error will be "
                "surfaced to the calling code.",
                _BIDIRECTIONAL_CONSUMER_NAME,
                exc,
                exc_info=True,
            )
            if self._on_fatal_exception is not None:
                self._on_fatal_exception(exc)

        except Exception as exc:
            _LOGGER.exception(
                "%s caught unexpected exception %s and will exit.",
                _BIDIRECTIONAL_CONSUMER_NAME,
                exc,
            )
            if self._on_fatal_exception is not None:
                self._on_fatal_exception(exc)

        _LOGGER.info("%s exiting", _BIDIRECTIONAL_CONSUMER_NAME)

    def start(self):
        """Start the background thread and begin consuming the thread."""
        with self._operational_lock:
            ready = threading.Event()
            thread = threading.Thread(
                name=_BIDIRECTIONAL_CONSUMER_NAME,
                target=self._thread_main,
                args=(ready,),
                daemon=True,
            )
            thread.start()
            # Other parts of the code rely on `thread.is_alive` which
            # isn't sufficient to know if a thread is active, just that it may
            # soon be active. This can cause races. Further protect
            # against races by using a ready event and wait on it to be set.
            ready.wait()
            self._thread = thread
            _LOGGER.debug("Started helper thread %s", thread.name)

    def stop(self):
        """Stop consuming the stream and shutdown the background thread.

        NOTE: Cannot be called within `_thread_main`, since it is not
        possible to join a thread to itself.
        """
        with self._operational_lock:
            self._bidi_rpc.close()

            if self._thread is not None:
                # Resume the thread to wake it up in case it is sleeping.
                self.resume()
                # The daemonized thread may itself block, so don't wait
                # for it longer than a second.
                self._thread.join(1.0)
                if self._thread.is_alive():  # pragma: NO COVER
                    _LOGGER.warning("Background thread did not exit.")

            self._thread = None
            self._on_response = None
            self._on_fatal_exception = None

    @property
    def is_active(self):
        """bool: True if the background thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def pause(self):
        """Pauses the response stream.

        This does *not* pause the request stream.
        """
        with self._wake:
            self._paused = True

    def resume(self):
        """Resumes the response stream."""
        with self._wake:
            self._paused = False
            self._wake.notify_all()

    @property
    def is_paused(self):
        """bool: True if the response stream is paused."""
        return self._paused

# === NexusCore/openenv\Lib\site-packages\nltk\inference\resolution.py ===
# Natural Language Toolkit: First-order Resolution-based Theorem Prover
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for a resolution-based First Order theorem prover.
"""

import operator
from collections import defaultdict
from functools import reduce

from nltk.inference.api import BaseProverCommand, Prover
from nltk.sem import skolemize
from nltk.sem.logic import (
    AndExpression,
    ApplicationExpression,
    EqualityExpression,
    Expression,
    IndividualVariableExpression,
    NegatedExpression,
    OrExpression,
    Variable,
    VariableExpression,
    is_indvar,
    unique_variable,
)


class ProverParseError(Exception):
    pass


class ResolutionProver(Prover):
    ANSWER_KEY = "ANSWER"
    _assume_false = True

    def _prove(self, goal=None, assumptions=None, verbose=False):
        """
        :param goal: Input expression to prove
        :type goal: sem.Expression
        :param assumptions: Input expressions to use as assumptions in the proof
        :type assumptions: list(sem.Expression)
        """
        if not assumptions:
            assumptions = []

        result = None
        try:
            clauses = []
            if goal:
                clauses.extend(clausify(-goal))
            for a in assumptions:
                clauses.extend(clausify(a))
            result, clauses = self._attempt_proof(clauses)
            if verbose:
                print(ResolutionProverCommand._decorate_clauses(clauses))
        except RuntimeError as e:
            if self._assume_false and str(e).startswith(
                "maximum recursion depth exceeded"
            ):
                result = False
                clauses = []
            else:
                if verbose:
                    print(e)
                else:
                    raise e
        return (result, clauses)

    def _attempt_proof(self, clauses):
        # map indices to lists of indices, to store attempted unifications
        tried = defaultdict(list)

        i = 0
        while i < len(clauses):
            if not clauses[i].is_tautology():
                # since we try clauses in order, we should start after the last
                # index tried
                if tried[i]:
                    j = tried[i][-1] + 1
                else:
                    j = i + 1  # nothing tried yet for 'i', so start with the next

                while j < len(clauses):
                    # don't: 1) unify a clause with itself,
                    #       2) use tautologies
                    if i != j and j and not clauses[j].is_tautology():
                        tried[i].append(j)
                        newclauses = clauses[i].unify(clauses[j])
                        if newclauses:
                            for newclause in newclauses:
                                newclause._parents = (i + 1, j + 1)
                                clauses.append(newclause)
                                if not len(newclause):  # if there's an empty clause
                                    return (True, clauses)
                            i = -1  # since we added a new clause, restart from the top
                            break
                    j += 1
            i += 1
        return (False, clauses)


class ResolutionProverCommand(BaseProverCommand):
    def __init__(self, goal=None, assumptions=None, prover=None):
        """
        :param goal: Input expression to prove
        :type goal: sem.Expression
        :param assumptions: Input expressions to use as assumptions in
            the proof.
        :type assumptions: list(sem.Expression)
        """
        if prover is not None:
            assert isinstance(prover, ResolutionProver)
        else:
            prover = ResolutionProver()

        BaseProverCommand.__init__(self, prover, goal, assumptions)
        self._clauses = None

    def prove(self, verbose=False):
        """
        Perform the actual proof.  Store the result to prevent unnecessary
        re-proving.
        """
        if self._result is None:
            self._result, clauses = self._prover._prove(
                self.goal(), self.assumptions(), verbose
            )
            self._clauses = clauses
            self._proof = ResolutionProverCommand._decorate_clauses(clauses)
        return self._result

    def find_answers(self, verbose=False):
        self.prove(verbose)

        answers = set()
        answer_ex = VariableExpression(Variable(ResolutionProver.ANSWER_KEY))
        for clause in self._clauses:
            for term in clause:
                if (
                    isinstance(term, ApplicationExpression)
                    and term.function == answer_ex
                    and not isinstance(term.argument, IndividualVariableExpression)
                ):
                    answers.add(term.argument)
        return answers

    @staticmethod
    def _decorate_clauses(clauses):
        """
        Decorate the proof output.
        """
        out = ""
        max_clause_len = max(len(str(clause)) for clause in clauses)
        max_seq_len = len(str(len(clauses)))
        for i in range(len(clauses)):
            parents = "A"
            taut = ""
            if clauses[i].is_tautology():
                taut = "Tautology"
            if clauses[i]._parents:
                parents = str(clauses[i]._parents)
            parents = " " * (max_clause_len - len(str(clauses[i])) + 1) + parents
            seq = " " * (max_seq_len - len(str(i + 1))) + str(i + 1)
            out += f"[{seq}] {clauses[i]} {parents} {taut}\n"
        return out


class Clause(list):
    def __init__(self, data):
        list.__init__(self, data)
        self._is_tautology = None
        self._parents = None

    def unify(self, other, bindings=None, used=None, skipped=None, debug=False):
        """
        Attempt to unify this Clause with the other, returning a list of
        resulting, unified, Clauses.

        :param other: ``Clause`` with which to unify
        :param bindings: ``BindingDict`` containing bindings that should be used
            during the unification
        :param used: tuple of two lists of atoms.  The first lists the
            atoms from 'self' that were successfully unified with atoms from
            'other'.  The second lists the atoms from 'other' that were successfully
            unified with atoms from 'self'.
        :param skipped: tuple of two ``Clause`` objects.  The first is a list of all
            the atoms from the 'self' Clause that have not been unified with
            anything on the path.  The second is same thing for the 'other' Clause.
        :param debug: bool indicating whether debug statements should print
        :return: list containing all the resulting ``Clause`` objects that could be
            obtained by unification
        """
        if bindings is None:
            bindings = BindingDict()
        if used is None:
            used = ([], [])
        if skipped is None:
            skipped = ([], [])
        if isinstance(debug, bool):
            debug = DebugObject(debug)

        newclauses = _iterate_first(
            self, other, bindings, used, skipped, _complete_unify_path, debug
        )

        # remove subsumed clauses.  make a list of all indices of subsumed
        # clauses, and then remove them from the list
        subsumed = []
        for i, c1 in enumerate(newclauses):
            if i not in subsumed:
                for j, c2 in enumerate(newclauses):
                    if i != j and j not in subsumed and c1.subsumes(c2):
                        subsumed.append(j)
        result = []
        for i in range(len(newclauses)):
            if i not in subsumed:
                result.append(newclauses[i])

        return result

    def isSubsetOf(self, other):
        """
        Return True iff every term in 'self' is a term in 'other'.

        :param other: ``Clause``
        :return: bool
        """
        for a in self:
            if a not in other:
                return False
        return True

    def subsumes(self, other):
        """
        Return True iff 'self' subsumes 'other', this is, if there is a
        substitution such that every term in 'self' can be unified with a term
        in 'other'.

        :param other: ``Clause``
        :return: bool
        """
        negatedother = []
        for atom in other:
            if isinstance(atom, NegatedExpression):
                negatedother.append(atom.term)
            else:
                negatedother.append(-atom)

        negatedotherClause = Clause(negatedother)

        bindings = BindingDict()
        used = ([], [])
        skipped = ([], [])
        debug = DebugObject(False)

        return (
            len(
                _iterate_first(
                    self,
                    negatedotherClause,
                    bindings,
                    used,
                    skipped,
                    _subsumes_finalize,
                    debug,
                )
            )
            > 0
        )

    def __getslice__(self, start, end):
        return Clause(list.__getslice__(self, start, end))

    def __sub__(self, other):
        return Clause([a for a in self if a not in other])

    def __add__(self, other):
        return Clause(list.__add__(self, other))

    def is_tautology(self):
        """
        Self is a tautology if it contains ground terms P and -P.  The ground
        term, P, must be an exact match, ie, not using unification.
        """
        if self._is_tautology is not None:
            return self._is_tautology
        for i, a in enumerate(self):
            if not isinstance(a, EqualityExpression):
                j = len(self) - 1
                while j > i:
                    b = self[j]
                    if isinstance(a, NegatedExpression):
                        if a.term == b:
                            self._is_tautology = True
                            return True
                    elif isinstance(b, NegatedExpression):
                        if a == b.term:
                            self._is_tautology = True
                            return True
                    j -= 1
        self._is_tautology = False
        return False

    def free(self):
        return reduce(operator.or_, ((atom.free() | atom.constants()) for atom in self))

    def replace(self, variable, expression):
        """
        Replace every instance of variable with expression across every atom
        in the clause

        :param variable: ``Variable``
        :param expression: ``Expression``
        """
        return Clause([atom.replace(variable, expression) for atom in self])

    def substitute_bindings(self, bindings):
        """
        Replace every binding

        :param bindings: A list of tuples mapping Variable Expressions to the
            Expressions to which they are bound.
        :return: ``Clause``
        """
        return Clause([atom.substitute_bindings(bindings) for atom in self])

    def __str__(self):
        return "{" + ", ".join("%s" % item for item in self) + "}"

    def __repr__(self):
        return "%s" % self


def _iterate_first(first, second, bindings, used, skipped, finalize_method, debug):
    """
    This method facilitates movement through the terms of 'self'
    """
    debug.line(f"unify({first},{second}) {bindings}")

    if not len(first) or not len(second):  # if no more recursions can be performed
        return finalize_method(first, second, bindings, used, skipped, debug)
    else:
        # explore this 'self' atom
        result = _iterate_second(
            first, second, bindings, used, skipped, finalize_method, debug + 1
        )

        # skip this possible 'self' atom
        newskipped = (skipped[0] + [first[0]], skipped[1])
        result += _iterate_first(
            first[1:], second, bindings, used, newskipped, finalize_method, debug + 1
        )

        try:
            newbindings, newused, unused = _unify_terms(
                first[0], second[0], bindings, used
            )
            # Unification found, so progress with this line of unification
            # put skipped and unused terms back into play for later unification.
            newfirst = first[1:] + skipped[0] + unused[0]
            newsecond = second[1:] + skipped[1] + unused[1]
            result += _iterate_first(
                newfirst,
                newsecond,
                newbindings,
                newused,
                ([], []),
                finalize_method,
                debug + 1,
            )
        except BindingException:
            # the atoms could not be unified,
            pass

        return result


def _iterate_second(first, second, bindings, used, skipped, finalize_method, debug):
    """
    This method facilitates movement through the terms of 'other'
    """
    debug.line(f"unify({first},{second}) {bindings}")

    if not len(first) or not len(second):  # if no more recursions can be performed
        return finalize_method(first, second, bindings, used, skipped, debug)
    else:
        # skip this possible pairing and move to the next
        newskipped = (skipped[0], skipped[1] + [second[0]])
        result = _iterate_second(
            first, second[1:], bindings, used, newskipped, finalize_method, debug + 1
        )

        try:
            newbindings, newused, unused = _unify_terms(
                first[0], second[0], bindings, used
            )
            # Unification found, so progress with this line of unification
            # put skipped and unused terms back into play for later unification.
            newfirst = first[1:] + skipped[0] + unused[0]
            newsecond = second[1:] + skipped[1] + unused[1]
            result += _iterate_second(
                newfirst,
                newsecond,
                newbindings,
                newused,
                ([], []),
                finalize_method,
                debug + 1,
            )
        except BindingException:
            # the atoms could not be unified,
            pass

        return result


def _unify_terms(a, b, bindings=None, used=None):
    """
    This method attempts to unify two terms.  Two expressions are unifiable
    if there exists a substitution function S such that S(a) == S(-b).

    :param a: ``Expression``
    :param b: ``Expression``
    :param bindings: ``BindingDict`` a starting set of bindings with which
    the unification must be consistent
    :return: ``BindingDict`` A dictionary of the bindings required to unify
    :raise ``BindingException``: If the terms cannot be unified
    """
    assert isinstance(a, Expression)
    assert isinstance(b, Expression)

    if bindings is None:
        bindings = BindingDict()
    if used is None:
        used = ([], [])

    # Use resolution
    if isinstance(a, NegatedExpression) and isinstance(b, ApplicationExpression):
        newbindings = most_general_unification(a.term, b, bindings)
        newused = (used[0] + [a], used[1] + [b])
        unused = ([], [])
    elif isinstance(a, ApplicationExpression) and isinstance(b, NegatedExpression):
        newbindings = most_general_unification(a, b.term, bindings)
        newused = (used[0] + [a], used[1] + [b])
        unused = ([], [])

    # Use demodulation
    elif isinstance(a, EqualityExpression):
        newbindings = BindingDict([(a.first.variable, a.second)])
        newused = (used[0] + [a], used[1])
        unused = ([], [b])
    elif isinstance(b, EqualityExpression):
        newbindings = BindingDict([(b.first.variable, b.second)])
        newused = (used[0], used[1] + [b])
        unused = ([a], [])

    else:
        raise BindingException((a, b))

    return newbindings, newused, unused


def _complete_unify_path(first, second, bindings, used, skipped, debug):
    if used[0] or used[1]:  # if bindings were made along the path
        newclause = Clause(skipped[0] + skipped[1] + first + second)
        debug.line("  -> New Clause: %s" % newclause)
        return [newclause.substitute_bindings(bindings)]
    else:  # no bindings made means no unification occurred.  so no result
        debug.line("  -> End")
        return []


def _subsumes_finalize(first, second, bindings, used, skipped, debug):
    if not len(skipped[0]) and not len(first):
        # If there are no skipped terms and no terms left in 'first', then
        # all of the terms in the original 'self' were unified with terms
        # in 'other'.  Therefore, there exists a binding (this one) such that
        # every term in self can be unified with a term in other, which
        # is the definition of subsumption.
        return [True]
    else:
        return []


def clausify(expression):
    """
    Skolemize, clausify, and standardize the variables apart.
    """
    clause_list = []
    for clause in _clausify(skolemize(expression)):
        for free in clause.free():
            if is_indvar(free.name):
                newvar = VariableExpression(unique_variable())
                clause = clause.replace(free, newvar)
        clause_list.append(clause)
    return clause_list


def _clausify(expression):
    """
    :param expression: a skolemized expression in CNF
    """
    if isinstance(expression, AndExpression):
        return _clausify(expression.first) + _clausify(expression.second)
    elif isinstance(expression, OrExpression):
        first = _clausify(expression.first)
        second = _clausify(expression.second)
        assert len(first) == 1
        assert len(second) == 1
        return [first[0] + second[0]]
    elif isinstance(expression, EqualityExpression):
        return [Clause([expression])]
    elif isinstance(expression, ApplicationExpression):
        return [Clause([expression])]
    elif isinstance(expression, NegatedExpression):
        if isinstance(expression.term, ApplicationExpression):
            return [Clause([expression])]
        elif isinstance(expression.term, EqualityExpression):
            return [Clause([expression])]
    raise ProverParseError()


class BindingDict:
    def __init__(self, binding_list=None):
        """
        :param binding_list: list of (``AbstractVariableExpression``, ``AtomicExpression``) to initialize the dictionary
        """
        self.d = {}

        if binding_list:
            for v, b in binding_list:
                self[v] = b

    def __setitem__(self, variable, binding):
        """
        A binding is consistent with the dict if its variable is not already bound, OR if its
        variable is already bound to its argument.

        :param variable: ``Variable`` The variable to bind
        :param binding: ``Expression`` The atomic to which 'variable' should be bound
        :raise BindingException: If the variable cannot be bound in this dictionary
        """
        assert isinstance(variable, Variable)
        assert isinstance(binding, Expression)

        try:
            existing = self[variable]
        except KeyError:
            existing = None

        if not existing or binding == existing:
            self.d[variable] = binding
        elif isinstance(binding, IndividualVariableExpression):
            # Since variable is already bound, try to bind binding to variable
            try:
                existing = self[binding.variable]
            except KeyError:
                existing = None

            binding2 = VariableExpression(variable)

            if not existing or binding2 == existing:
                self.d[binding.variable] = binding2
            else:
                raise BindingException(
                    "Variable %s already bound to another " "value" % (variable)
                )
        else:
            raise BindingException(
                "Variable %s already bound to another " "value" % (variable)
            )

    def __getitem__(self, variable):
        """
        Return the expression to which 'variable' is bound
        """
        assert isinstance(variable, Variable)

        intermediate = self.d[variable]
        while intermediate:
            try:
                intermediate = self.d[intermediate]
            except KeyError:
                return intermediate

    def __contains__(self, item):
        return item in self.d

    def __add__(self, other):
        """
        :param other: ``BindingDict`` The dict with which to combine self
        :return: ``BindingDict`` A new dict containing all the elements of both parameters
        :raise BindingException: If the parameter dictionaries are not consistent with each other
        """
        try:
            combined = BindingDict()
            for v in self.d:
                combined[v] = self.d[v]
            for v in other.d:
                combined[v] = other.d[v]
            return combined
        except BindingException as e:
            raise BindingException(
                "Attempting to add two contradicting "
                "BindingDicts: '%s' and '%s'" % (self, other)
            ) from e

    def __len__(self):
        return len(self.d)

    def __str__(self):
        data_str = ", ".join(f"{v}: {self.d[v]}" for v in sorted(self.d.keys()))
        return "{" + data_str + "}"

    def __repr__(self):
        return "%s" % self


def most_general_unification(a, b, bindings=None):
    """
    Find the most general unification of the two given expressions

    :param a: ``Expression``
    :param b: ``Expression``
    :param bindings: ``BindingDict`` a starting set of bindings with which the
                     unification must be consistent
    :return: a list of bindings
    :raise BindingException: if the Expressions cannot be unified
    """
    if bindings is None:
        bindings = BindingDict()

    if a == b:
        return bindings
    elif isinstance(a, IndividualVariableExpression):
        return _mgu_var(a, b, bindings)
    elif isinstance(b, IndividualVariableExpression):
        return _mgu_var(b, a, bindings)
    elif isinstance(a, ApplicationExpression) and isinstance(b, ApplicationExpression):
        return most_general_unification(
            a.function, b.function, bindings
        ) + most_general_unification(a.argument, b.argument, bindings)
    raise BindingException((a, b))


def _mgu_var(var, expression, bindings):
    if var.variable in expression.free() | expression.constants():
        raise BindingException((var, expression))
    else:
        return BindingDict([(var.variable, expression)]) + bindings


class BindingException(Exception):
    def __init__(self, arg):
        if isinstance(arg, tuple):
            Exception.__init__(self, "'%s' cannot be bound to '%s'" % arg)
        else:
            Exception.__init__(self, arg)


class UnificationException(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, f"'{a}' cannot unify with '{b}'")


class DebugObject:
    def __init__(self, enabled=True, indent=0):
        self.enabled = enabled
        self.indent = indent

    def __add__(self, i):
        return DebugObject(self.enabled, self.indent + i)

    def line(self, line):
        if self.enabled:
            print("    " * self.indent + line)


def testResolutionProver():
    resolution_test(r"man(x)")
    resolution_test(r"(man(x) -> man(x))")
    resolution_test(r"(man(x) -> --man(x))")
    resolution_test(r"-(man(x) and -man(x))")
    resolution_test(r"(man(x) or -man(x))")
    resolution_test(r"(man(x) -> man(x))")
    resolution_test(r"-(man(x) and -man(x))")
    resolution_test(r"(man(x) or -man(x))")
    resolution_test(r"(man(x) -> man(x))")
    resolution_test(r"(man(x) iff man(x))")
    resolution_test(r"-(man(x) iff -man(x))")
    resolution_test("all x.man(x)")
    resolution_test("-all x.some y.F(x,y) & some x.all y.(-F(x,y))")
    resolution_test("some x.all y.sees(x,y)")

    p1 = Expression.fromstring(r"all x.(man(x) -> mortal(x))")
    p2 = Expression.fromstring(r"man(Socrates)")
    c = Expression.fromstring(r"mortal(Socrates)")
    print(f"{p1}, {p2} |- {c}: {ResolutionProver().prove(c, [p1, p2])}")

    p1 = Expression.fromstring(r"all x.(man(x) -> walks(x))")
    p2 = Expression.fromstring(r"man(John)")
    c = Expression.fromstring(r"some y.walks(y)")
    print(f"{p1}, {p2} |- {c}: {ResolutionProver().prove(c, [p1, p2])}")

    p = Expression.fromstring(r"some e1.some e2.(believe(e1,john,e2) & walk(e2,mary))")
    c = Expression.fromstring(r"some e0.walk(e0,mary)")
    print(f"{p} |- {c}: {ResolutionProver().prove(c, [p])}")


def resolution_test(e):
    f = Expression.fromstring(e)
    t = ResolutionProver().prove(f)
    print(f"|- {f}: {t}")


def test_clausify():
    lexpr = Expression.fromstring

    print(clausify(lexpr("P(x) | Q(x)")))
    print(clausify(lexpr("(P(x) & Q(x)) | R(x)")))
    print(clausify(lexpr("P(x) | (Q(x) & R(x))")))
    print(clausify(lexpr("(P(x) & Q(x)) | (R(x) & S(x))")))

    print(clausify(lexpr("P(x) | Q(x) | R(x)")))
    print(clausify(lexpr("P(x) | (Q(x) & R(x)) | S(x)")))

    print(clausify(lexpr("exists x.P(x) | Q(x)")))

    print(clausify(lexpr("-(-P(x) & Q(x))")))
    print(clausify(lexpr("P(x) <-> Q(x)")))
    print(clausify(lexpr("-(P(x) <-> Q(x))")))
    print(clausify(lexpr("-(all x.P(x))")))
    print(clausify(lexpr("-(some x.P(x))")))

    print(clausify(lexpr("some x.P(x)")))
    print(clausify(lexpr("some x.all y.P(x,y)")))
    print(clausify(lexpr("all y.some x.P(x,y)")))
    print(clausify(lexpr("all z.all y.some x.P(x,y,z)")))
    print(clausify(lexpr("all x.(all y.P(x,y) -> -all y.(Q(x,y) -> R(x,y)))")))


def demo():
    test_clausify()
    print()
    testResolutionProver()
    print()

    p = Expression.fromstring("man(x)")
    print(ResolutionProverCommand(p, [p]).prove())


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\polyutils.py ===
"""
Utility classes and functions for the polynomial modules.

This module provides: error and warning objects; a polynomial base class;
and some routines used in both the `polynomial` and `chebyshev` modules.

Functions
---------

.. autosummary::
   :toctree: generated/

   as_series    convert list of array_likes into 1-D arrays of common type.
   trimseq      remove trailing zeros.
   trimcoef     remove small trailing coefficients.
   getdomain    return the domain appropriate for a given set of abscissae.
   mapdomain    maps points between domains.
   mapparms     parameters of the linear map between domains.

"""
import functools
import operator
import warnings

import numpy as np
from numpy._core.multiarray import dragon4_positional, dragon4_scientific
from numpy.exceptions import RankWarning

__all__ = [
    'as_series', 'trimseq', 'trimcoef', 'getdomain', 'mapdomain', 'mapparms',
    'format_float']

#
# Helper functions to convert inputs to 1-D arrays
#
def trimseq(seq):
    """Remove small Poly series coefficients.

    Parameters
    ----------
    seq : sequence
        Sequence of Poly series coefficients.

    Returns
    -------
    series : sequence
        Subsequence with trailing zeros removed. If the resulting sequence
        would be empty, return the first element. The returned sequence may
        or may not be a view.

    Notes
    -----
    Do not lose the type info if the sequence contains unknown objects.

    """
    if len(seq) == 0 or seq[-1] != 0:
        return seq
    else:
        for i in range(len(seq) - 1, -1, -1):
            if seq[i] != 0:
                break
        return seq[:i + 1]


def as_series(alist, trim=True):
    """
    Return argument as a list of 1-d arrays.

    The returned list contains array(s) of dtype double, complex double, or
    object.  A 1-d argument of shape ``(N,)`` is parsed into ``N`` arrays of
    size one; a 2-d argument of shape ``(M,N)`` is parsed into ``M`` arrays
    of size ``N`` (i.e., is "parsed by row"); and a higher dimensional array
    raises a Value Error if it is not first reshaped into either a 1-d or 2-d
    array.

    Parameters
    ----------
    alist : array_like
        A 1- or 2-d array_like
    trim : boolean, optional
        When True, trailing zeros are removed from the inputs.
        When False, the inputs are passed through intact.

    Returns
    -------
    [a1, a2,...] : list of 1-D arrays
        A copy of the input data as a list of 1-d arrays.

    Raises
    ------
    ValueError
        Raised when `as_series` cannot convert its input to 1-d arrays, or at
        least one of the resulting arrays is empty.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial import polyutils as pu
    >>> a = np.arange(4)
    >>> pu.as_series(a)
    [array([0.]), array([1.]), array([2.]), array([3.])]
    >>> b = np.arange(6).reshape((2,3))
    >>> pu.as_series(b)
    [array([0., 1., 2.]), array([3., 4., 5.])]

    >>> pu.as_series((1, np.arange(3), np.arange(2, dtype=np.float16)))
    [array([1.]), array([0., 1., 2.]), array([0., 1.])]

    >>> pu.as_series([2, [1.1, 0.]])
    [array([2.]), array([1.1])]

    >>> pu.as_series([2, [1.1, 0.]], trim=False)
    [array([2.]), array([1.1, 0. ])]

    """
    arrays = [np.array(a, ndmin=1, copy=None) for a in alist]
    for a in arrays:
        if a.size == 0:
            raise ValueError("Coefficient array is empty")
        if a.ndim != 1:
            raise ValueError("Coefficient array is not 1-d")
    if trim:
        arrays = [trimseq(a) for a in arrays]

    try:
        dtype = np.common_type(*arrays)
    except Exception as e:
        object_dtype = np.dtypes.ObjectDType()
        has_one_object_type = False
        ret = []
        for a in arrays:
            if a.dtype != object_dtype:
                tmp = np.empty(len(a), dtype=object_dtype)
                tmp[:] = a[:]
                ret.append(tmp)
            else:
                has_one_object_type = True
                ret.append(a.copy())
        if not has_one_object_type:
            raise ValueError("Coefficient arrays have no common type") from e
    else:
        ret = [np.array(a, copy=True, dtype=dtype) for a in arrays]
    return ret


def trimcoef(c, tol=0):
    """
    Remove "small" "trailing" coefficients from a polynomial.

    "Small" means "small in absolute value" and is controlled by the
    parameter `tol`; "trailing" means highest order coefficient(s), e.g., in
    ``[0, 1, 1, 0, 0]`` (which represents ``0 + x + x**2 + 0*x**3 + 0*x**4``)
    both the 3-rd and 4-th order coefficients would be "trimmed."

    Parameters
    ----------
    c : array_like
        1-d array of coefficients, ordered from lowest order to highest.
    tol : number, optional
        Trailing (i.e., highest order) elements with absolute value less
        than or equal to `tol` (default value is zero) are removed.

    Returns
    -------
    trimmed : ndarray
        1-d array with trailing zeros removed.  If the resulting series
        would be empty, a series containing a single zero is returned.

    Raises
    ------
    ValueError
        If `tol` < 0

    Examples
    --------
    >>> from numpy.polynomial import polyutils as pu
    >>> pu.trimcoef((0,0,3,0,5,0,0))
    array([0.,  0.,  3.,  0.,  5.])
    >>> pu.trimcoef((0,0,1e-3,0,1e-5,0,0),1e-3) # item == tol is trimmed
    array([0.])
    >>> i = complex(0,1) # works for complex
    >>> pu.trimcoef((3e-4,1e-3*(1-i),5e-4,2e-5*(1+i)), 1e-3)
    array([0.0003+0.j   , 0.001 -0.001j])

    """
    if tol < 0:
        raise ValueError("tol must be non-negative")

    [c] = as_series([c])
    [ind] = np.nonzero(np.abs(c) > tol)
    if len(ind) == 0:
        return c[:1] * 0
    else:
        return c[:ind[-1] + 1].copy()

def getdomain(x):
    """
    Return a domain suitable for given abscissae.

    Find a domain suitable for a polynomial or Chebyshev series
    defined at the values supplied.

    Parameters
    ----------
    x : array_like
        1-d array of abscissae whose domain will be determined.

    Returns
    -------
    domain : ndarray
        1-d array containing two values.  If the inputs are complex, then
        the two returned points are the lower left and upper right corners
        of the smallest rectangle (aligned with the axes) in the complex
        plane containing the points `x`. If the inputs are real, then the
        two points are the ends of the smallest interval containing the
        points `x`.

    See Also
    --------
    mapparms, mapdomain

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial import polyutils as pu
    >>> points = np.arange(4)**2 - 5; points
    array([-5, -4, -1,  4])
    >>> pu.getdomain(points)
    array([-5.,  4.])
    >>> c = np.exp(complex(0,1)*np.pi*np.arange(12)/6) # unit circle
    >>> pu.getdomain(c)
    array([-1.-1.j,  1.+1.j])

    """
    [x] = as_series([x], trim=False)
    if x.dtype.char in np.typecodes['Complex']:
        rmin, rmax = x.real.min(), x.real.max()
        imin, imax = x.imag.min(), x.imag.max()
        return np.array((complex(rmin, imin), complex(rmax, imax)))
    else:
        return np.array((x.min(), x.max()))

def mapparms(old, new):
    """
    Linear map parameters between domains.

    Return the parameters of the linear map ``offset + scale*x`` that maps
    `old` to `new` such that ``old[i] -> new[i]``, ``i = 0, 1``.

    Parameters
    ----------
    old, new : array_like
        Domains. Each domain must (successfully) convert to a 1-d array
        containing precisely two values.

    Returns
    -------
    offset, scale : scalars
        The map ``L(x) = offset + scale*x`` maps the first domain to the
        second.

    See Also
    --------
    getdomain, mapdomain

    Notes
    -----
    Also works for complex numbers, and thus can be used to calculate the
    parameters required to map any line in the complex plane to any other
    line therein.

    Examples
    --------
    >>> from numpy.polynomial import polyutils as pu
    >>> pu.mapparms((-1,1),(-1,1))
    (0.0, 1.0)
    >>> pu.mapparms((1,-1),(-1,1))
    (-0.0, -1.0)
    >>> i = complex(0,1)
    >>> pu.mapparms((-i,-1),(1,i))
    ((1+1j), (1-0j))

    """
    oldlen = old[1] - old[0]
    newlen = new[1] - new[0]
    off = (old[1] * new[0] - old[0] * new[1]) / oldlen
    scl = newlen / oldlen
    return off, scl

def mapdomain(x, old, new):
    """
    Apply linear map to input points.

    The linear map ``offset + scale*x`` that maps the domain `old` to
    the domain `new` is applied to the points `x`.

    Parameters
    ----------
    x : array_like
        Points to be mapped. If `x` is a subtype of ndarray the subtype
        will be preserved.
    old, new : array_like
        The two domains that determine the map.  Each must (successfully)
        convert to 1-d arrays containing precisely two values.

    Returns
    -------
    x_out : ndarray
        Array of points of the same shape as `x`, after application of the
        linear map between the two domains.

    See Also
    --------
    getdomain, mapparms

    Notes
    -----
    Effectively, this implements:

    .. math::
        x\\_out = new[0] + m(x - old[0])

    where

    .. math::
        m = \\frac{new[1]-new[0]}{old[1]-old[0]}

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial import polyutils as pu
    >>> old_domain = (-1,1)
    >>> new_domain = (0,2*np.pi)
    >>> x = np.linspace(-1,1,6); x
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ])
    >>> x_out = pu.mapdomain(x, old_domain, new_domain); x_out
    array([ 0.        ,  1.25663706,  2.51327412,  3.76991118,  5.02654825, # may vary
            6.28318531])
    >>> x - pu.mapdomain(x_out, new_domain, old_domain)
    array([0., 0., 0., 0., 0., 0.])

    Also works for complex numbers (and thus can be used to map any line in
    the complex plane to any other line therein).

    >>> i = complex(0,1)
    >>> old = (-1 - i, 1 + i)
    >>> new = (-1 + i, 1 - i)
    >>> z = np.linspace(old[0], old[1], 6); z
    array([-1. -1.j , -0.6-0.6j, -0.2-0.2j,  0.2+0.2j,  0.6+0.6j,  1. +1.j ])
    >>> new_z = pu.mapdomain(z, old, new); new_z
    array([-1.0+1.j , -0.6+0.6j, -0.2+0.2j,  0.2-0.2j,  0.6-0.6j,  1.0-1.j ]) # may vary

    """
    if type(x) not in (int, float, complex) and not isinstance(x, np.generic):
        x = np.asanyarray(x)
    off, scl = mapparms(old, new)
    return off + scl * x


def _nth_slice(i, ndim):
    sl = [np.newaxis] * ndim
    sl[i] = slice(None)
    return tuple(sl)


def _vander_nd(vander_fs, points, degrees):
    r"""
    A generalization of the Vandermonde matrix for N dimensions

    The result is built by combining the results of 1d Vandermonde matrices,

    .. math::
        W[i_0, \ldots, i_M, j_0, \ldots, j_N] = \prod_{k=0}^N{V_k(x_k)[i_0, \ldots, i_M, j_k]}

    where

    .. math::
        N &= \texttt{len(points)} = \texttt{len(degrees)} = \texttt{len(vander\_fs)} \\
        M &= \texttt{points[k].ndim} \\
        V_k &= \texttt{vander\_fs[k]} \\
        x_k &= \texttt{points[k]} \\
        0 \le j_k &\le \texttt{degrees[k]}

    Expanding the one-dimensional :math:`V_k` functions gives:

    .. math::
        W[i_0, \ldots, i_M, j_0, \ldots, j_N] = \prod_{k=0}^N{B_{k, j_k}(x_k[i_0, \ldots, i_M])}

    where :math:`B_{k,m}` is the m'th basis of the polynomial construction used along
    dimension :math:`k`. For a regular polynomial, :math:`B_{k, m}(x) = P_m(x) = x^m`.

    Parameters
    ----------
    vander_fs : Sequence[function(array_like, int) -> ndarray]
        The 1d vander function to use for each axis, such as ``polyvander``
    points : Sequence[array_like]
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to
        1-D arrays.
        This must be the same length as `vander_fs`.
    degrees : Sequence[int]
        The maximum degree (inclusive) to use for each axis.
        This must be the same length as `vander_fs`.

    Returns
    -------
    vander_nd : ndarray
        An array of shape ``points[0].shape + tuple(d + 1 for d in degrees)``.
    """  # noqa: E501
    n_dims = len(vander_fs)
    if n_dims != len(points):
        raise ValueError(
            f"Expected {n_dims} dimensions of sample points, got {len(points)}")
    if n_dims != len(degrees):
        raise ValueError(
            f"Expected {n_dims} dimensions of degrees, got {len(degrees)}")
    if n_dims == 0:
        raise ValueError("Unable to guess a dtype or shape when no points are given")

    # convert to the same shape and type
    points = tuple(np.asarray(tuple(points)) + 0.0)

    # produce the vandermonde matrix for each dimension, placing the last
    # axis of each in an independent trailing axis of the output
    vander_arrays = (
        vander_fs[i](points[i], degrees[i])[(...,) + _nth_slice(i, n_dims)]
        for i in range(n_dims)
    )

    # we checked this wasn't empty already, so no `initial` needed
    return functools.reduce(operator.mul, vander_arrays)


def _vander_nd_flat(vander_fs, points, degrees):
    """
    Like `_vander_nd`, but flattens the last ``len(degrees)`` axes into a single axis

    Used to implement the public ``<type>vander<n>d`` functions.
    """
    v = _vander_nd(vander_fs, points, degrees)
    return v.reshape(v.shape[:-len(degrees)] + (-1,))


def _fromroots(line_f, mul_f, roots):
    """
    Helper function used to implement the ``<type>fromroots`` functions.

    Parameters
    ----------
    line_f : function(float, float) -> ndarray
        The ``<type>line`` function, such as ``polyline``
    mul_f : function(array_like, array_like) -> ndarray
        The ``<type>mul`` function, such as ``polymul``
    roots
        See the ``<type>fromroots`` functions for more detail
    """
    if len(roots) == 0:
        return np.ones(1)
    else:
        [roots] = as_series([roots], trim=False)
        roots.sort()
        p = [line_f(-r, 1) for r in roots]
        n = len(p)
        while n > 1:
            m, r = divmod(n, 2)
            tmp = [mul_f(p[i], p[i + m]) for i in range(m)]
            if r:
                tmp[0] = mul_f(tmp[0], p[-1])
            p = tmp
            n = m
        return p[0]


def _valnd(val_f, c, *args):
    """
    Helper function used to implement the ``<type>val<n>d`` functions.

    Parameters
    ----------
    val_f : function(array_like, array_like, tensor: bool) -> array_like
        The ``<type>val`` function, such as ``polyval``
    c, args
        See the ``<type>val<n>d`` functions for more detail
    """
    args = [np.asanyarray(a) for a in args]
    shape0 = args[0].shape
    if not all(a.shape == shape0 for a in args[1:]):
        if len(args) == 3:
            raise ValueError('x, y, z are incompatible')
        elif len(args) == 2:
            raise ValueError('x, y are incompatible')
        else:
            raise ValueError('ordinates are incompatible')
    it = iter(args)
    x0 = next(it)

    # use tensor on only the first
    c = val_f(x0, c)
    for xi in it:
        c = val_f(xi, c, tensor=False)
    return c


def _gridnd(val_f, c, *args):
    """
    Helper function used to implement the ``<type>grid<n>d`` functions.

    Parameters
    ----------
    val_f : function(array_like, array_like, tensor: bool) -> array_like
        The ``<type>val`` function, such as ``polyval``
    c, args
        See the ``<type>grid<n>d`` functions for more detail
    """
    for xi in args:
        c = val_f(xi, c)
    return c


def _div(mul_f, c1, c2):
    """
    Helper function used to implement the ``<type>div`` functions.

    Implementation uses repeated subtraction of c2 multiplied by the nth basis.
    For some polynomial types, a more efficient approach may be possible.

    Parameters
    ----------
    mul_f : function(array_like, array_like) -> array_like
        The ``<type>mul`` function, such as ``polymul``
    c1, c2
        See the ``<type>div`` functions for more detail
    """
    # c1, c2 are trimmed copies
    [c1, c2] = as_series([c1, c2])
    if c2[-1] == 0:
        raise ZeroDivisionError  # FIXME: add message with details to exception

    lc1 = len(c1)
    lc2 = len(c2)
    if lc1 < lc2:
        return c1[:1] * 0, c1
    elif lc2 == 1:
        return c1 / c2[-1], c1[:1] * 0
    else:
        quo = np.empty(lc1 - lc2 + 1, dtype=c1.dtype)
        rem = c1
        for i in range(lc1 - lc2, - 1, -1):
            p = mul_f([0] * i + [1], c2)
            q = rem[-1] / p[-1]
            rem = rem[:-1] - q * p[:-1]
            quo[i] = q
        return quo, trimseq(rem)


def _add(c1, c2):
    """ Helper function used to implement the ``<type>add`` functions. """
    # c1, c2 are trimmed copies
    [c1, c2] = as_series([c1, c2])
    if len(c1) > len(c2):
        c1[:c2.size] += c2
        ret = c1
    else:
        c2[:c1.size] += c1
        ret = c2
    return trimseq(ret)


def _sub(c1, c2):
    """ Helper function used to implement the ``<type>sub`` functions. """
    # c1, c2 are trimmed copies
    [c1, c2] = as_series([c1, c2])
    if len(c1) > len(c2):
        c1[:c2.size] -= c2
        ret = c1
    else:
        c2 = -c2
        c2[:c1.size] += c1
        ret = c2
    return trimseq(ret)


def _fit(vander_f, x, y, deg, rcond=None, full=False, w=None):
    """
    Helper function used to implement the ``<type>fit`` functions.

    Parameters
    ----------
    vander_f : function(array_like, int) -> ndarray
        The 1d vander function, such as ``polyvander``
    c1, c2
        See the ``<type>fit`` functions for more detail
    """
    x = np.asarray(x) + 0.0
    y = np.asarray(y) + 0.0
    deg = np.asarray(deg)

    # check arguments.
    if deg.ndim > 1 or deg.dtype.kind not in 'iu' or deg.size == 0:
        raise TypeError("deg must be an int or non-empty 1-D array of int")
    if deg.min() < 0:
        raise ValueError("expected deg >= 0")
    if x.ndim != 1:
        raise TypeError("expected 1D vector for x")
    if x.size == 0:
        raise TypeError("expected non-empty vector for x")
    if y.ndim < 1 or y.ndim > 2:
        raise TypeError("expected 1D or 2D array for y")
    if len(x) != len(y):
        raise TypeError("expected x and y to have same length")

    if deg.ndim == 0:
        lmax = deg
        order = lmax + 1
        van = vander_f(x, lmax)
    else:
        deg = np.sort(deg)
        lmax = deg[-1]
        order = len(deg)
        van = vander_f(x, lmax)[:, deg]

    # set up the least squares matrices in transposed form
    lhs = van.T
    rhs = y.T
    if w is not None:
        w = np.asarray(w) + 0.0
        if w.ndim != 1:
            raise TypeError("expected 1D vector for w")
        if len(x) != len(w):
            raise TypeError("expected x and w to have same length")
        # apply weights. Don't use inplace operations as they
        # can cause problems with NA.
        lhs = lhs * w
        rhs = rhs * w

    # set rcond
    if rcond is None:
        rcond = len(x) * np.finfo(x.dtype).eps

    # Determine the norms of the design matrix columns.
    if issubclass(lhs.dtype.type, np.complexfloating):
        scl = np.sqrt((np.square(lhs.real) + np.square(lhs.imag)).sum(1))
    else:
        scl = np.sqrt(np.square(lhs).sum(1))
    scl[scl == 0] = 1

    # Solve the least squares problem.
    c, resids, rank, s = np.linalg.lstsq(lhs.T / scl, rhs.T, rcond)
    c = (c.T / scl).T

    # Expand c to include non-fitted coefficients which are set to zero
    if deg.ndim > 0:
        if c.ndim == 2:
            cc = np.zeros((lmax + 1, c.shape[1]), dtype=c.dtype)
        else:
            cc = np.zeros(lmax + 1, dtype=c.dtype)
        cc[deg] = c
        c = cc

    # warn on rank reduction
    if rank != order and not full:
        msg = "The fit may be poorly conditioned"
        warnings.warn(msg, RankWarning, stacklevel=2)

    if full:
        return c, [resids, rank, s, rcond]
    else:
        return c


def _pow(mul_f, c, pow, maxpower):
    """
    Helper function used to implement the ``<type>pow`` functions.

    Parameters
    ----------
    mul_f : function(array_like, array_like) -> ndarray
        The ``<type>mul`` function, such as ``polymul``
    c : array_like
        1-D array of array of series coefficients
    pow, maxpower
        See the ``<type>pow`` functions for more detail
    """
    # c is a trimmed copy
    [c] = as_series([c])
    power = int(pow)
    if power != pow or power < 0:
        raise ValueError("Power must be a non-negative integer.")
    elif maxpower is not None and power > maxpower:
        raise ValueError("Power is too large")
    elif power == 0:
        return np.array([1], dtype=c.dtype)
    elif power == 1:
        return c
    else:
        # This can be made more efficient by using powers of two
        # in the usual way.
        prd = c
        for i in range(2, power + 1):
            prd = mul_f(prd, c)
        return prd


def _as_int(x, desc):
    """
    Like `operator.index`, but emits a custom exception when passed an
    incorrect type

    Parameters
    ----------
    x : int-like
        Value to interpret as an integer
    desc : str
        description to include in any error message

    Raises
    ------
    TypeError : if x is a float or non-numeric
    """
    try:
        return operator.index(x)
    except TypeError as e:
        raise TypeError(f"{desc} must be an integer, received {x}") from e


def format_float(x, parens=False):
    if not np.issubdtype(type(x), np.floating):
        return str(x)

    opts = np.get_printoptions()

    if np.isnan(x):
        return opts['nanstr']
    elif np.isinf(x):
        return opts['infstr']

    exp_format = False
    if x != 0:
        a = np.abs(x)
        if a >= 1.e8 or a < 10**min(0, -(opts['precision'] - 1) // 2):
            exp_format = True

    trim, unique = '0', True
    if opts['floatmode'] == 'fixed':
        trim, unique = 'k', False

    if exp_format:
        s = dragon4_scientific(x, precision=opts['precision'],
                               unique=unique, trim=trim,
                               sign=opts['sign'] == '+')
        if parens:
            s = '(' + s + ')'
    else:
        s = dragon4_positional(x, precision=opts['precision'],
                               fractional=True,
                               unique=unique, trim=trim,
                               sign=opts['sign'] == '+')
    return s

# === NexusCore/openenv\Lib\site-packages\packaging\licenses\_spdx.py ===

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

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\licenses\_spdx.py ===

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

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\licenses\_spdx.py ===

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

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\code.py ===
"""Implementation of code management magic functions.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import inspect
import io
import os
import re
import sys
import ast
from itertools import chain
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from pathlib import Path

# Our own packages
from IPython.core.error import TryNext, StdinNotImplementedError, UsageError
from IPython.core.macro import Macro
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.oinspect import find_file, find_source_lines
from IPython.core.release import version
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.contexts import preserve_keys
from IPython.utils.path import get_py_filename
from warnings import warn
from logging import error
from IPython.utils.text import get_text_list

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

# Used for exception handling in magic_edit
class MacroToEdit(ValueError): pass

ipython_input_pat = re.compile(r"<ipython\-input\-(\d+)-[a-z\d]+>$")

# To match, e.g. 8-10 1:5 :10 3-
range_re = re.compile(r"""
(?P<start>\d+)?
((?P<sep>[\-:])
 (?P<end>\d+)?)?
$""", re.VERBOSE)


def extract_code_ranges(ranges_str):
    """Turn a string of range for %%load into 2-tuples of (start, stop)
    ready to use as a slice of the content split by lines.

    Examples
    --------
    list(extract_input_ranges("5-10 2"))
    [(4, 10), (1, 2)]
    """
    for range_str in ranges_str.split():
        rmatch = range_re.match(range_str)
        if not rmatch:
            continue
        sep = rmatch.group("sep")
        start = rmatch.group("start")
        end = rmatch.group("end")

        if sep == '-':
            start = int(start) - 1 if start else None
            end = int(end) if end else None
        elif sep == ':':
            start = int(start) - 1 if start else None
            end = int(end) - 1 if end else None
        else:
            end = int(start)
            start = int(start) - 1
        yield (start, end)


def extract_symbols(code, symbols):
    """
    Return a tuple  (blocks, not_found)
    where ``blocks`` is a list of code fragments
    for each symbol parsed from code, and ``not_found`` are
    symbols not found in the code.

    For example::

        In [1]: code = '''a = 10
           ...: def b(): return 42
           ...: class A: pass'''

        In [2]: extract_symbols(code, 'A,b,z')
        Out[2]: (['class A: pass\\n', 'def b(): return 42\\n'], ['z'])
    """
    symbols = symbols.split(',')

    # this will raise SyntaxError if code isn't valid Python
    py_code = ast.parse(code)

    marks = [(getattr(s, 'name', None), s.lineno) for s in py_code.body]
    code = code.split('\n')

    symbols_lines = {}
    
    # we already know the start_lineno of each symbol (marks). 
    # To find each end_lineno, we traverse in reverse order until each 
    # non-blank line
    end = len(code)  
    for name, start in reversed(marks):
        while not code[end - 1].strip():
            end -= 1
        if name:
            symbols_lines[name] = (start - 1, end)
        end = start - 1

    # Now symbols_lines is a map
    # {'symbol_name': (start_lineno, end_lineno), ...}
    
    # fill a list with chunks of codes for each requested symbol
    blocks = []
    not_found = []
    for symbol in symbols:
        if symbol in symbols_lines:
            start, end = symbols_lines[symbol]
            blocks.append('\n'.join(code[start:end]) + '\n')
        else:
            not_found.append(symbol)

    return blocks, not_found

def strip_initial_indent(lines):
    """For %load, strip indent from lines until finding an unindented line.

    https://github.com/ipython/ipython/issues/9775
    """
    indent_re = re.compile(r'\s+')

    it = iter(lines)
    first_line = next(it)
    indent_match = indent_re.match(first_line)

    if indent_match:
        # First line was indented
        indent = indent_match.group()
        yield first_line[len(indent):]

        for line in it:
            if line.startswith(indent):
                yield line[len(indent) :]
            elif line in ("\n", "\r\n") or len(line) == 0:
                yield line
            else:
                # Less indented than the first line - stop dedenting
                yield line
                break
    else:
        yield first_line

    # Pass the remaining lines through without dedenting
    for line in it:
        yield line


class InteractivelyDefined(Exception):
    """Exception for interactively defined variable in magic_edit"""
    def __init__(self, index):
        self.index = index


@magics_class
class CodeMagics(Magics):
    """Magics related to code management (loading, saving, editing, ...)."""

    def __init__(self, *args, **kwargs):
        self._knowntemps = set()
        super(CodeMagics, self).__init__(*args, **kwargs)

    @line_magic
    def save(self, parameter_s=''):
        """Save a set of lines or a macro to a given filename.

        Usage:\\
          %save [options] filename [history]

        Options:

          -r: use 'raw' input.  By default, the 'processed' history is used,
          so that magics are loaded in their transformed version to valid
          Python.  If this option is given, the raw input as typed at the
          command line is used instead.
          
          -f: force overwrite.  If file exists, %save will prompt for overwrite
          unless -f is given.

          -a: append to the file instead of overwriting it.

        The history argument uses the same syntax as %history for input ranges,
        then saves the lines to the filename you specify.

        If no ranges are specified, saves history of the current session up to
        this point.

        It adds a '.py' extension to the file if you don't do so yourself, and
        it asks for confirmation before overwriting existing files.

        If `-r` option is used, the default extension is `.ipy`.
        """

        opts,args = self.parse_options(parameter_s,'fra',mode='list')
        if not args:
            raise UsageError('Missing filename.')
        raw = 'r' in opts
        force = 'f' in opts
        append = 'a' in opts
        mode = 'a' if append else 'w'
        ext = '.ipy' if raw else '.py'
        fname, codefrom = args[0], " ".join(args[1:])
        if not fname.endswith(('.py','.ipy')):
            fname += ext
        fname = os.path.expanduser(fname)
        file_exists = os.path.isfile(fname)
        if file_exists and not force and not append:
            try:
                overwrite = self.shell.ask_yes_no('File `%s` exists. Overwrite (y/[N])? ' % fname, default='n')
            except StdinNotImplementedError:
                print("File `%s` exists. Use `%%save -f %s` to force overwrite" % (fname, parameter_s))
                return
            if not overwrite :
                print('Operation cancelled.')
                return
        try:
            cmds = self.shell.find_user_code(codefrom,raw)
        except (TypeError, ValueError) as e:
            print(e.args[0])
            return
        with io.open(fname, mode, encoding="utf-8") as f:
            if not file_exists or not append:
                f.write("# coding: utf-8\n")
            f.write(cmds)
            # make sure we end on a newline
            if not cmds.endswith('\n'):
                f.write('\n')
        print('The following commands were written to file `%s`:' % fname)
        print(cmds)

    @line_magic
    def pastebin(self, parameter_s=''):
        """Upload code to dpaste.com, returning the URL.

        Usage:\\
          %pastebin [-d "Custom description"][-e 24] 1-7

        The argument can be an input history range, a filename, or the name of a
        string or macro.

        If no arguments are given, uploads the history of this session up to
        this point.

        Options:

          -d: Pass a custom description. The default will say
              "Pasted from IPython".
          -e: Pass number of days for the link to be expired.
              The default will be 7 days.
        """
        opts, args = self.parse_options(parameter_s, "d:e:")

        try:
            code = self.shell.find_user_code(args)
        except (ValueError, TypeError) as e:
            print(e.args[0])
            return

        expiry_days = 7
        try:
            expiry_days = int(opts.get("e", 7))
        except ValueError as e:
            print(e.args[0].capitalize())
            return
        if expiry_days < 1 or expiry_days > 365:
            print("Expiry days should be in range of 1 to 365")
            return

        post_data = urlencode(
            {
                "title": opts.get("d", "Pasted from IPython"),
                "syntax": "python",
                "content": code,
                "expiry_days": expiry_days,
            }
        ).encode("utf-8")

        request = Request(
            "https://dpaste.com/api/v2/",
            headers={"User-Agent": "IPython v{}".format(version)},
        )
        response = urlopen(request, post_data)
        return response.headers.get('Location')

    @line_magic
    def loadpy(self, arg_s):
        """Alias of `%load`

        `%loadpy` has gained some flexibility and dropped the requirement of a `.py`
        extension. So it has been renamed simply into %load. You can look at
        `%load`'s docstring for more info.
        """
        self.load(arg_s)

    @line_magic
    def load(self, arg_s):
        """Load code into the current frontend.

        Usage:\\
          %load [options] source

          where source can be a filename, URL, input history range, macro, or
          element in the user namespace

        If no arguments are given, loads the history of this session up to this
        point.

        Options:

          -r <lines>: Specify lines or ranges of lines to load from the source.
          Ranges could be specified as x-y (x..y) or in python-style x:y 
          (x..(y-1)). Both limits x and y can be left blank (meaning the 
          beginning and end of the file, respectively).

          -s <symbols>: Specify function or classes to load from python source. 

          -y : Don't ask confirmation for loading source above 200 000 characters.

          -n : Include the user's namespace when searching for source code.

        This magic command can either take a local filename, a URL, an history
        range (see %history) or a macro as argument, it will prompt for
        confirmation before loading source with more than 200 000 characters, unless
        -y flag is passed or if the frontend does not support raw_input::

        %load
        %load myscript.py
        %load 7-27
        %load myMacro
        %load http://www.example.com/myscript.py
        %load -r 5-10 myscript.py
        %load -r 10-20,30,40: foo.py
        %load -s MyClass,wonder_function myscript.py
        %load -n MyClass
        %load -n my_module.wonder_function
        """
        opts,args = self.parse_options(arg_s,'yns:r:')
        search_ns = 'n' in opts
        contents = self.shell.find_user_code(args, search_ns=search_ns)

        if 's' in opts:
            try:
                blocks, not_found = extract_symbols(contents, opts['s'])
            except SyntaxError:
                # non python code
                error("Unable to parse the input as valid Python code")
                return

            if len(not_found) == 1:
                warn('The symbol `%s` was not found' % not_found[0])
            elif len(not_found) > 1:
                warn('The symbols %s were not found' % get_text_list(not_found,
                                                                     wrap_item_with='`')
                )

            contents = '\n'.join(blocks)

        if 'r' in opts:
            ranges = opts['r'].replace(',', ' ')
            lines = contents.split('\n')
            slices = extract_code_ranges(ranges)
            contents = [lines[slice(*slc)] for slc in slices]
            contents = '\n'.join(strip_initial_indent(chain.from_iterable(contents)))

        l = len(contents)

        # 200 000 is ~ 2500 full 80 character lines
        # so in average, more than 5000 lines
        if l > 200000 and 'y' not in opts:
            try:
                ans = self.shell.ask_yes_no(("The text you're trying to load seems pretty big"\
                " (%d characters). Continue (y/[N]) ?" % l), default='n' )
            except StdinNotImplementedError:
                #assume yes if raw input not implemented
                ans = True

            if ans is False :
                print('Operation cancelled.')
                return

        contents = "# %load {}\n".format(arg_s) + contents

        self.shell.set_next_input(contents, replace=True)

    @staticmethod
    def _find_edit_target(shell, args, opts, last_call):
        """Utility method used by magic_edit to find what to edit."""

        def make_filename(arg):
            "Make a filename from the given args"
            try:
                filename = get_py_filename(arg)
            except IOError:
                # If it ends with .py but doesn't already exist, assume we want
                # a new file.
                if arg.endswith('.py'):
                    filename = arg
                else:
                    filename = None
            return filename

        # Set a few locals from the options for convenience:
        opts_prev = 'p' in opts
        opts_raw = 'r' in opts

        # custom exceptions
        class DataIsObject(Exception): pass

        # Default line number value
        lineno = opts.get('n',None)

        if opts_prev:
            args = '_%s' % last_call[0]
            if args not in shell.user_ns:
                args = last_call[1]

        # by default this is done with temp files, except when the given
        # arg is a filename
        use_temp = True

        data = ''

        # First, see if the arguments should be a filename.
        filename = make_filename(args)
        if filename:
            use_temp = False
        elif args:
            # Mode where user specifies ranges of lines, like in %macro.
            data = shell.extract_input_lines(args, opts_raw)
            if not data:
                try:
                    # Load the parameter given as a variable. If not a string,
                    # process it as an object instead (below)

                    # print('*** args',args,'type',type(args))  # dbg
                    data = eval(args, shell.user_ns)
                    if not isinstance(data, str):
                        raise DataIsObject

                except (NameError,SyntaxError):
                    # given argument is not a variable, try as a filename
                    filename = make_filename(args)
                    if filename is None:
                        warn("Argument given (%s) can't be found as a variable "
                             "or as a filename." % args)
                        return (None, None, None)
                    use_temp = False

                except DataIsObject as e:
                    # macros have a special edit function
                    if isinstance(data, Macro):
                        raise MacroToEdit(data) from e

                    # For objects, try to edit the file where they are defined
                    filename = find_file(data)
                    if filename:
                        if 'fakemodule' in filename.lower() and \
                            inspect.isclass(data):
                            # class created by %edit? Try to find source
                            # by looking for method definitions instead, the
                            # __module__ in those classes is FakeModule.
                            attrs = [getattr(data, aname) for aname in dir(data)]
                            for attr in attrs:
                                if not inspect.ismethod(attr):
                                    continue
                                filename = find_file(attr)
                                if filename and \
                                  'fakemodule' not in filename.lower():
                                    # change the attribute to be the edit
                                    # target instead
                                    data = attr
                                    break
                        
                        m = ipython_input_pat.match(os.path.basename(filename))
                        if m:
                            raise InteractivelyDefined(int(m.groups()[0])) from e

                        datafile = 1
                    if filename is None:
                        filename = make_filename(args)
                        datafile = 1
                        if filename is not None:
                            # only warn about this if we get a real name
                            warn('Could not find file where `%s` is defined.\n'
                             'Opening a file named `%s`' % (args, filename))
                    # Now, make sure we can actually read the source (if it was
                    # in a temp file it's gone by now).
                    if datafile:
                        if lineno is None:
                            lineno = find_source_lines(data)
                        if lineno is None:
                            filename = make_filename(args)
                            if filename is None:
                                warn('The file where `%s` was defined '
                                     'cannot be read or found.' % data)
                                return (None, None, None)
                    use_temp = False

        if use_temp:
            filename = shell.mktempfile(data)
            print('IPython will make a temporary file named:',filename)

        # use last_call to remember the state of the previous call, but don't
        # let it be clobbered by successive '-p' calls.
        try:
            last_call[0] = shell.displayhook.prompt_count
            if not opts_prev:
                last_call[1] = args
        except:
            pass


        return filename, lineno, use_temp

    def _edit_macro(self,mname,macro):
        """open an editor with the macro data in a file"""
        filename = self.shell.mktempfile(macro.value)
        self.shell.hooks.editor(filename)

        # and make a new macro object, to replace the old one
        mvalue = Path(filename).read_text(encoding="utf-8")
        self.shell.user_ns[mname] = Macro(mvalue)

    @skip_doctest
    @line_magic
    def edit(self, parameter_s='',last_call=['','']):
        """Bring up an editor and execute the resulting code.

        Usage:
          %edit [options] [args]

        %edit runs IPython's editor hook. The default version of this hook is
        set to call the editor specified by your $EDITOR environment variable.
        If this isn't found, it will default to vi under Linux/Unix and to
        notepad under Windows. See the end of this docstring for how to change
        the editor hook.

        You can also set the value of this editor via the
        ``TerminalInteractiveShell.editor`` option in your configuration file.
        This is useful if you wish to use a different editor from your typical
        default with IPython (and for Windows users who typically don't set
        environment variables).

        This command allows you to conveniently edit multi-line code right in
        your IPython session.

        If called without arguments, %edit opens up an empty editor with a
        temporary file and will execute the contents of this file when you
        close it (don't forget to save it!).


        Options:

        -n <number>: open the editor at a specified line number.  By default,
        the IPython editor hook uses the unix syntax 'editor +N filename', but
        you can configure this by providing your own modified hook if your
        favorite editor supports line-number specifications with a different
        syntax.

        -p: this will call the editor with the same data as the previous time
        it was used, regardless of how long ago (in your current session) it
        was.

        -r: use 'raw' input.  This option only applies to input taken from the
        user's history.  By default, the 'processed' history is used, so that
        magics are loaded in their transformed version to valid Python.  If
        this option is given, the raw input as typed as the command line is
        used instead.  When you exit the editor, it will be executed by
        IPython's own processor.

        -x: do not execute the edited code immediately upon exit. This is
        mainly useful if you are editing programs which need to be called with
        command line arguments, which you can then do using %run.


        Arguments:

        If arguments are given, the following possibilities exist:

        - If the argument is a filename, IPython will load that into the
          editor. It will execute its contents with execfile() when you exit,
          loading any code in the file into your interactive namespace.

        - The arguments are ranges of input history,  e.g. "7 ~1/4-6".
          The syntax is the same as in the %history magic.

        - If the argument is a string variable, its contents are loaded
          into the editor. You can thus edit any string which contains
          python code (including the result of previous edits).

        - If the argument is the name of an object (other than a string),
          IPython will try to locate the file where it was defined and open the
          editor at the point where it is defined. You can use `%edit function`
          to load an editor exactly at the point where 'function' is defined,
          edit it and have the file be executed automatically.

        - If the object is a macro (see %macro for details), this opens up your
          specified editor with a temporary file containing the macro's data.
          Upon exit, the macro is reloaded with the contents of the file.

        Note: opening at an exact line is only supported under Unix, and some
        editors (like kedit and gedit up to Gnome 2.8) do not understand the
        '+NUMBER' parameter necessary for this feature. Good editors like
        (X)Emacs, vi, jed, pico and joe all do.

        After executing your code, %edit will return as output the code you
        typed in the editor (except when it was an existing file). This way
        you can reload the code in further invocations of %edit as a variable,
        via _<NUMBER> or Out[<NUMBER>], where <NUMBER> is the prompt number of
        the output.

        Note that %edit is also available through the alias %ed.

        This is an example of creating a simple function inside the editor and
        then modifying it. First, start up the editor::

          In [1]: edit
          Editing... done. Executing edited code...
          Out[1]: 'def foo():\\n    print("foo() was defined in an editing
          session")\\n'

        We can then call the function foo()::

          In [2]: foo()
          foo() was defined in an editing session

        Now we edit foo.  IPython automatically loads the editor with the
        (temporary) file where foo() was previously defined::

          In [3]: edit foo
          Editing... done. Executing edited code...

        And if we call foo() again we get the modified version::

          In [4]: foo()
          foo() has now been changed!

        Here is an example of how to edit a code snippet successive
        times. First we call the editor::

          In [5]: edit
          Editing... done. Executing edited code...
          hello
          Out[5]: "print('hello')\\n"

        Now we call it again with the previous output (stored in _)::

          In [6]: edit _
          Editing... done. Executing edited code...
          hello world
          Out[6]: "print('hello world')\\n"

        Now we call it with the output #8 (stored in _8, also as Out[8])::

          In [7]: edit _8
          Editing... done. Executing edited code...
          hello again
          Out[7]: "print('hello again')\\n"


        Changing the default editor hook:

        If you wish to write your own editor hook, you can put it in a
        configuration file which you load at startup time.  The default hook
        is defined in the IPython.core.hooks module, and you can use that as a
        starting example for further modifications.  That file also has
        general instructions on how to set a new hook for use once you've
        defined it."""
        opts,args = self.parse_options(parameter_s,'prxn:')

        try:
            filename, lineno, is_temp = self._find_edit_target(self.shell, 
                                                       args, opts, last_call)
        except MacroToEdit as e:
            self._edit_macro(args, e.args[0])
            return
        except InteractivelyDefined as e:
            print("Editing In[%i]" % e.index)
            args = str(e.index)
            filename, lineno, is_temp = self._find_edit_target(self.shell, 
                                                       args, opts, last_call)
        if filename is None:
            # nothing was found, warnings have already been issued,
            # just give up.
            return

        if is_temp:
            self._knowntemps.add(filename)
        elif (filename in self._knowntemps):
            is_temp = True


        # do actual editing here
        print('Editing...', end=' ')
        sys.stdout.flush()
        filepath = Path(filename)
        try:
            # Quote filenames that may have spaces in them when opening
            # the editor
            quoted = filename = str(filepath.absolute())
            if " " in quoted:
                quoted = "'%s'" % quoted
            self.shell.hooks.editor(quoted, lineno)
        except TryNext:
            warn('Could not open editor')
            return

        # XXX TODO: should this be generalized for all string vars?
        # For now, this is special-cased to blocks created by cpaste
        if args.strip() == "pasted_block":
            self.shell.user_ns["pasted_block"] = filepath.read_text(encoding="utf-8")

        if 'x' in opts:  # -x prevents actual execution
            print()
        else:
            print('done. Executing edited code...')
            with preserve_keys(self.shell.user_ns, '__file__'):
                if not is_temp:
                    self.shell.user_ns["__file__"] = filename
                if "r" in opts:  # Untranslated IPython code
                    source = filepath.read_text(encoding="utf-8")
                    self.shell.run_cell(source, store_history=False)
                else:
                    self.shell.safe_execfile(filename, self.shell.user_ns,
                                             self.shell.user_ns)

        if is_temp:
            try:
                return filepath.read_text(encoding="utf-8")
            except IOError as msg:
                if Path(msg.filename) == filepath:
                    warn('File not found. Did you forget to save?')
                    return
                else:
                    self.shell.showtraceback()

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\output\vt100.py ===
"""
Output for vt100 terminals.

A lot of thanks, regarding outputting of colors, goes to the Pygments project:
(We don't rely on Pygments anymore, because many things are very custom, and
everything has been highly optimized.)
http://pygments.org/
"""

from __future__ import annotations

import io
import os
import sys
from typing import Callable, Dict, Hashable, Iterable, Sequence, TextIO, Tuple

from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.data_structures import Size
from prompt_toolkit.output import Output
from prompt_toolkit.styles import ANSI_COLOR_NAMES, Attrs
from prompt_toolkit.utils import is_dumb_terminal

from .color_depth import ColorDepth
from .flush_stdout import flush_stdout

__all__ = [
    "Vt100_Output",
]


FG_ANSI_COLORS = {
    "ansidefault": 39,
    # Low intensity.
    "ansiblack": 30,
    "ansired": 31,
    "ansigreen": 32,
    "ansiyellow": 33,
    "ansiblue": 34,
    "ansimagenta": 35,
    "ansicyan": 36,
    "ansigray": 37,
    # High intensity.
    "ansibrightblack": 90,
    "ansibrightred": 91,
    "ansibrightgreen": 92,
    "ansibrightyellow": 93,
    "ansibrightblue": 94,
    "ansibrightmagenta": 95,
    "ansibrightcyan": 96,
    "ansiwhite": 97,
}

BG_ANSI_COLORS = {
    "ansidefault": 49,
    # Low intensity.
    "ansiblack": 40,
    "ansired": 41,
    "ansigreen": 42,
    "ansiyellow": 43,
    "ansiblue": 44,
    "ansimagenta": 45,
    "ansicyan": 46,
    "ansigray": 47,
    # High intensity.
    "ansibrightblack": 100,
    "ansibrightred": 101,
    "ansibrightgreen": 102,
    "ansibrightyellow": 103,
    "ansibrightblue": 104,
    "ansibrightmagenta": 105,
    "ansibrightcyan": 106,
    "ansiwhite": 107,
}


ANSI_COLORS_TO_RGB = {
    "ansidefault": (
        0x00,
        0x00,
        0x00,
    ),  # Don't use, 'default' doesn't really have a value.
    "ansiblack": (0x00, 0x00, 0x00),
    "ansigray": (0xE5, 0xE5, 0xE5),
    "ansibrightblack": (0x7F, 0x7F, 0x7F),
    "ansiwhite": (0xFF, 0xFF, 0xFF),
    # Low intensity.
    "ansired": (0xCD, 0x00, 0x00),
    "ansigreen": (0x00, 0xCD, 0x00),
    "ansiyellow": (0xCD, 0xCD, 0x00),
    "ansiblue": (0x00, 0x00, 0xCD),
    "ansimagenta": (0xCD, 0x00, 0xCD),
    "ansicyan": (0x00, 0xCD, 0xCD),
    # High intensity.
    "ansibrightred": (0xFF, 0x00, 0x00),
    "ansibrightgreen": (0x00, 0xFF, 0x00),
    "ansibrightyellow": (0xFF, 0xFF, 0x00),
    "ansibrightblue": (0x00, 0x00, 0xFF),
    "ansibrightmagenta": (0xFF, 0x00, 0xFF),
    "ansibrightcyan": (0x00, 0xFF, 0xFF),
}


assert set(FG_ANSI_COLORS) == set(ANSI_COLOR_NAMES)
assert set(BG_ANSI_COLORS) == set(ANSI_COLOR_NAMES)
assert set(ANSI_COLORS_TO_RGB) == set(ANSI_COLOR_NAMES)


def _get_closest_ansi_color(r: int, g: int, b: int, exclude: Sequence[str] = ()) -> str:
    """
    Find closest ANSI color. Return it by name.

    :param r: Red (Between 0 and 255.)
    :param g: Green (Between 0 and 255.)
    :param b: Blue (Between 0 and 255.)
    :param exclude: A tuple of color names to exclude. (E.g. ``('ansired', )``.)
    """
    exclude = list(exclude)

    # When we have a bit of saturation, avoid the gray-like colors, otherwise,
    # too often the distance to the gray color is less.
    saturation = abs(r - g) + abs(g - b) + abs(b - r)  # Between 0..510

    if saturation > 30:
        exclude.extend(["ansilightgray", "ansidarkgray", "ansiwhite", "ansiblack"])

    # Take the closest color.
    # (Thanks to Pygments for this part.)
    distance = 257 * 257 * 3  # "infinity" (>distance from #000000 to #ffffff)
    match = "ansidefault"

    for name, (r2, g2, b2) in ANSI_COLORS_TO_RGB.items():
        if name != "ansidefault" and name not in exclude:
            d = (r - r2) ** 2 + (g - g2) ** 2 + (b - b2) ** 2

            if d < distance:
                match = name
                distance = d

    return match


_ColorCodeAndName = Tuple[int, str]


class _16ColorCache:
    """
    Cache which maps (r, g, b) tuples to 16 ansi colors.

    :param bg: Cache for background colors, instead of foreground.
    """

    def __init__(self, bg: bool = False) -> None:
        self.bg = bg
        self._cache: dict[Hashable, _ColorCodeAndName] = {}

    def get_code(
        self, value: tuple[int, int, int], exclude: Sequence[str] = ()
    ) -> _ColorCodeAndName:
        """
        Return a (ansi_code, ansi_name) tuple. (E.g. ``(44, 'ansiblue')``.) for
        a given (r,g,b) value.
        """
        key: Hashable = (value, tuple(exclude))
        cache = self._cache

        if key not in cache:
            cache[key] = self._get(value, exclude)

        return cache[key]

    def _get(
        self, value: tuple[int, int, int], exclude: Sequence[str] = ()
    ) -> _ColorCodeAndName:
        r, g, b = value
        match = _get_closest_ansi_color(r, g, b, exclude=exclude)

        # Turn color name into code.
        if self.bg:
            code = BG_ANSI_COLORS[match]
        else:
            code = FG_ANSI_COLORS[match]

        return code, match


class _256ColorCache(Dict[Tuple[int, int, int], int]):
    """
    Cache which maps (r, g, b) tuples to 256 colors.
    """

    def __init__(self) -> None:
        # Build color table.
        colors: list[tuple[int, int, int]] = []

        # colors 0..15: 16 basic colors
        colors.append((0x00, 0x00, 0x00))  # 0
        colors.append((0xCD, 0x00, 0x00))  # 1
        colors.append((0x00, 0xCD, 0x00))  # 2
        colors.append((0xCD, 0xCD, 0x00))  # 3
        colors.append((0x00, 0x00, 0xEE))  # 4
        colors.append((0xCD, 0x00, 0xCD))  # 5
        colors.append((0x00, 0xCD, 0xCD))  # 6
        colors.append((0xE5, 0xE5, 0xE5))  # 7
        colors.append((0x7F, 0x7F, 0x7F))  # 8
        colors.append((0xFF, 0x00, 0x00))  # 9
        colors.append((0x00, 0xFF, 0x00))  # 10
        colors.append((0xFF, 0xFF, 0x00))  # 11
        colors.append((0x5C, 0x5C, 0xFF))  # 12
        colors.append((0xFF, 0x00, 0xFF))  # 13
        colors.append((0x00, 0xFF, 0xFF))  # 14
        colors.append((0xFF, 0xFF, 0xFF))  # 15

        # colors 16..232: the 6x6x6 color cube
        valuerange = (0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF)

        for i in range(217):
            r = valuerange[(i // 36) % 6]
            g = valuerange[(i // 6) % 6]
            b = valuerange[i % 6]
            colors.append((r, g, b))

        # colors 233..253: grayscale
        for i in range(1, 22):
            v = 8 + i * 10
            colors.append((v, v, v))

        self.colors = colors

    def __missing__(self, value: tuple[int, int, int]) -> int:
        r, g, b = value

        # Find closest color.
        # (Thanks to Pygments for this!)
        distance = 257 * 257 * 3  # "infinity" (>distance from #000000 to #ffffff)
        match = 0

        for i, (r2, g2, b2) in enumerate(self.colors):
            if i >= 16:  # XXX: We ignore the 16 ANSI colors when mapping RGB
                # to the 256 colors, because these highly depend on
                # the color scheme of the terminal.
                d = (r - r2) ** 2 + (g - g2) ** 2 + (b - b2) ** 2

                if d < distance:
                    match = i
                    distance = d

        # Turn color name into code.
        self[value] = match
        return match


_16_fg_colors = _16ColorCache(bg=False)
_16_bg_colors = _16ColorCache(bg=True)
_256_colors = _256ColorCache()


class _EscapeCodeCache(Dict[Attrs, str]):
    """
    Cache for VT100 escape codes. It maps
    (fgcolor, bgcolor, bold, underline, strike, reverse) tuples to VT100
    escape sequences.

    :param true_color: When True, use 24bit colors instead of 256 colors.
    """

    def __init__(self, color_depth: ColorDepth) -> None:
        self.color_depth = color_depth

    def __missing__(self, attrs: Attrs) -> str:
        (
            fgcolor,
            bgcolor,
            bold,
            underline,
            strike,
            italic,
            blink,
            reverse,
            hidden,
        ) = attrs
        parts: list[str] = []

        parts.extend(self._colors_to_code(fgcolor or "", bgcolor or ""))

        if bold:
            parts.append("1")
        if italic:
            parts.append("3")
        if blink:
            parts.append("5")
        if underline:
            parts.append("4")
        if reverse:
            parts.append("7")
        if hidden:
            parts.append("8")
        if strike:
            parts.append("9")

        if parts:
            result = "\x1b[0;" + ";".join(parts) + "m"
        else:
            result = "\x1b[0m"

        self[attrs] = result
        return result

    def _color_name_to_rgb(self, color: str) -> tuple[int, int, int]:
        "Turn 'ffffff', into (0xff, 0xff, 0xff)."
        try:
            rgb = int(color, 16)
        except ValueError:
            raise
        else:
            r = (rgb >> 16) & 0xFF
            g = (rgb >> 8) & 0xFF
            b = rgb & 0xFF
            return r, g, b

    def _colors_to_code(self, fg_color: str, bg_color: str) -> Iterable[str]:
        """
        Return a tuple with the vt100 values  that represent this color.
        """
        # When requesting ANSI colors only, and both fg/bg color were converted
        # to ANSI, ensure that the foreground and background color are not the
        # same. (Unless they were explicitly defined to be the same color.)
        fg_ansi = ""

        def get(color: str, bg: bool) -> list[int]:
            nonlocal fg_ansi

            table = BG_ANSI_COLORS if bg else FG_ANSI_COLORS

            if not color or self.color_depth == ColorDepth.DEPTH_1_BIT:
                return []

            # 16 ANSI colors. (Given by name.)
            elif color in table:
                return [table[color]]

            # RGB colors. (Defined as 'ffffff'.)
            else:
                try:
                    rgb = self._color_name_to_rgb(color)
                except ValueError:
                    return []

                # When only 16 colors are supported, use that.
                if self.color_depth == ColorDepth.DEPTH_4_BIT:
                    if bg:  # Background.
                        if fg_color != bg_color:
                            exclude = [fg_ansi]
                        else:
                            exclude = []
                        code, name = _16_bg_colors.get_code(rgb, exclude=exclude)
                        return [code]
                    else:  # Foreground.
                        code, name = _16_fg_colors.get_code(rgb)
                        fg_ansi = name
                        return [code]

                # True colors. (Only when this feature is enabled.)
                elif self.color_depth == ColorDepth.DEPTH_24_BIT:
                    r, g, b = rgb
                    return [(48 if bg else 38), 2, r, g, b]

                # 256 RGB colors.
                else:
                    return [(48 if bg else 38), 5, _256_colors[rgb]]

        result: list[int] = []
        result.extend(get(fg_color, False))
        result.extend(get(bg_color, True))

        return map(str, result)


def _get_size(fileno: int) -> tuple[int, int]:
    """
    Get the size of this pseudo terminal.

    :param fileno: stdout.fileno()
    :returns: A (rows, cols) tuple.
    """
    size = os.get_terminal_size(fileno)
    return size.lines, size.columns


class Vt100_Output(Output):
    """
    :param get_size: A callable which returns the `Size` of the output terminal.
    :param stdout: Any object with has a `write` and `flush` method + an 'encoding' property.
    :param term: The terminal environment variable. (xterm, xterm-256color, linux, ...)
    :param enable_cpr: When `True` (the default), send "cursor position
        request" escape sequences to the output in order to detect the cursor
        position. That way, we can properly determine how much space there is
        available for the UI (especially for drop down menus) to render. The
        `Renderer` will still try to figure out whether the current terminal
        does respond to CPR escapes. When `False`, never attempt to send CPR
        requests.
    """

    # For the error messages. Only display "Output is not a terminal" once per
    # file descriptor.
    _fds_not_a_terminal: set[int] = set()

    def __init__(
        self,
        stdout: TextIO,
        get_size: Callable[[], Size],
        term: str | None = None,
        default_color_depth: ColorDepth | None = None,
        enable_bell: bool = True,
        enable_cpr: bool = True,
    ) -> None:
        assert all(hasattr(stdout, a) for a in ("write", "flush"))

        self._buffer: list[str] = []
        self.stdout: TextIO = stdout
        self.default_color_depth = default_color_depth
        self._get_size = get_size
        self.term = term
        self.enable_bell = enable_bell
        self.enable_cpr = enable_cpr

        # Cache for escape codes.
        self._escape_code_caches: dict[ColorDepth, _EscapeCodeCache] = {
            ColorDepth.DEPTH_1_BIT: _EscapeCodeCache(ColorDepth.DEPTH_1_BIT),
            ColorDepth.DEPTH_4_BIT: _EscapeCodeCache(ColorDepth.DEPTH_4_BIT),
            ColorDepth.DEPTH_8_BIT: _EscapeCodeCache(ColorDepth.DEPTH_8_BIT),
            ColorDepth.DEPTH_24_BIT: _EscapeCodeCache(ColorDepth.DEPTH_24_BIT),
        }

        # Keep track of whether the cursor shape was ever changed.
        # (We don't restore the cursor shape if it was never changed - by
        # default, we don't change them.)
        self._cursor_shape_changed = False

        # Don't hide/show the cursor when this was already done.
        # (`None` means that we don't know whether the cursor is visible or
        # not.)
        self._cursor_visible: bool | None = None

    @classmethod
    def from_pty(
        cls,
        stdout: TextIO,
        term: str | None = None,
        default_color_depth: ColorDepth | None = None,
        enable_bell: bool = True,
    ) -> Vt100_Output:
        """
        Create an Output class from a pseudo terminal.
        (This will take the dimensions by reading the pseudo
        terminal attributes.)
        """
        fd: int | None
        # Normally, this requires a real TTY device, but people instantiate
        # this class often during unit tests as well. For convenience, we print
        # an error message, use standard dimensions, and go on.
        try:
            fd = stdout.fileno()
        except io.UnsupportedOperation:
            fd = None

        if not stdout.isatty() and (fd is None or fd not in cls._fds_not_a_terminal):
            msg = "Warning: Output is not a terminal (fd=%r).\n"
            sys.stderr.write(msg % fd)
            sys.stderr.flush()
            if fd is not None:
                cls._fds_not_a_terminal.add(fd)

        def get_size() -> Size:
            # If terminal (incorrectly) reports its size as 0, pick a
            # reasonable default.  See
            # https://github.com/ipython/ipython/issues/10071
            rows, columns = (None, None)

            # It is possible that `stdout` is no longer a TTY device at this
            # point. In that case we get an `OSError` in the ioctl call in
            # `get_size`. See:
            # https://github.com/prompt-toolkit/python-prompt-toolkit/pull/1021
            try:
                rows, columns = _get_size(stdout.fileno())
            except OSError:
                pass
            return Size(rows=rows or 24, columns=columns or 80)

        return cls(
            stdout,
            get_size,
            term=term,
            default_color_depth=default_color_depth,
            enable_bell=enable_bell,
        )

    def get_size(self) -> Size:
        return self._get_size()

    def fileno(self) -> int:
        "Return file descriptor."
        return self.stdout.fileno()

    def encoding(self) -> str:
        "Return encoding used for stdout."
        return self.stdout.encoding

    def write_raw(self, data: str) -> None:
        """
        Write raw data to output.
        """
        self._buffer.append(data)

    def write(self, data: str) -> None:
        """
        Write text to output.
        (Removes vt100 escape codes. -- used for safely writing text.)
        """
        self._buffer.append(data.replace("\x1b", "?"))

    def set_title(self, title: str) -> None:
        """
        Set terminal title.
        """
        if self.term not in (
            "linux",
            "eterm-color",
        ):  # Not supported by the Linux console.
            self.write_raw(
                "\x1b]2;{}\x07".format(title.replace("\x1b", "").replace("\x07", ""))
            )

    def clear_title(self) -> None:
        self.set_title("")

    def erase_screen(self) -> None:
        """
        Erases the screen with the background color and moves the cursor to
        home.
        """
        self.write_raw("\x1b[2J")

    def enter_alternate_screen(self) -> None:
        self.write_raw("\x1b[?1049h\x1b[H")

    def quit_alternate_screen(self) -> None:
        self.write_raw("\x1b[?1049l")

    def enable_mouse_support(self) -> None:
        self.write_raw("\x1b[?1000h")

        # Enable mouse-drag support.
        self.write_raw("\x1b[?1003h")

        # Enable urxvt Mouse mode. (For terminals that understand this.)
        self.write_raw("\x1b[?1015h")

        # Also enable Xterm SGR mouse mode. (For terminals that understand this.)
        self.write_raw("\x1b[?1006h")

        # Note: E.g. lxterminal understands 1000h, but not the urxvt or sgr
        #       extensions.

    def disable_mouse_support(self) -> None:
        self.write_raw("\x1b[?1000l")
        self.write_raw("\x1b[?1015l")
        self.write_raw("\x1b[?1006l")
        self.write_raw("\x1b[?1003l")

    def erase_end_of_line(self) -> None:
        """
        Erases from the current cursor position to the end of the current line.
        """
        self.write_raw("\x1b[K")

    def erase_down(self) -> None:
        """
        Erases the screen from the current line down to the bottom of the
        screen.
        """
        self.write_raw("\x1b[J")

    def reset_attributes(self) -> None:
        self.write_raw("\x1b[0m")

    def set_attributes(self, attrs: Attrs, color_depth: ColorDepth) -> None:
        """
        Create new style and output.

        :param attrs: `Attrs` instance.
        """
        # Get current depth.
        escape_code_cache = self._escape_code_caches[color_depth]

        # Write escape character.
        self.write_raw(escape_code_cache[attrs])

    def disable_autowrap(self) -> None:
        self.write_raw("\x1b[?7l")

    def enable_autowrap(self) -> None:
        self.write_raw("\x1b[?7h")

    def enable_bracketed_paste(self) -> None:
        self.write_raw("\x1b[?2004h")

    def disable_bracketed_paste(self) -> None:
        self.write_raw("\x1b[?2004l")

    def reset_cursor_key_mode(self) -> None:
        """
        For vt100 only.
        Put the terminal in cursor mode (instead of application mode).
        """
        # Put the terminal in cursor mode. (Instead of application mode.)
        self.write_raw("\x1b[?1l")

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        """
        Move cursor position.
        """
        self.write_raw("\x1b[%i;%iH" % (row, column))

    def cursor_up(self, amount: int) -> None:
        if amount == 0:
            pass
        elif amount == 1:
            self.write_raw("\x1b[A")
        else:
            self.write_raw("\x1b[%iA" % amount)

    def cursor_down(self, amount: int) -> None:
        if amount == 0:
            pass
        elif amount == 1:
            # Note: Not the same as '\n', '\n' can cause the window content to
            #       scroll.
            self.write_raw("\x1b[B")
        else:
            self.write_raw("\x1b[%iB" % amount)

    def cursor_forward(self, amount: int) -> None:
        if amount == 0:
            pass
        elif amount == 1:
            self.write_raw("\x1b[C")
        else:
            self.write_raw("\x1b[%iC" % amount)

    def cursor_backward(self, amount: int) -> None:
        if amount == 0:
            pass
        elif amount == 1:
            self.write_raw("\b")  # '\x1b[D'
        else:
            self.write_raw("\x1b[%iD" % amount)

    def hide_cursor(self) -> None:
        if self._cursor_visible in (True, None):
            self._cursor_visible = False
            self.write_raw("\x1b[?25l")

    def show_cursor(self) -> None:
        if self._cursor_visible in (False, None):
            self._cursor_visible = True
            self.write_raw("\x1b[?12l\x1b[?25h")  # Stop blinking cursor and show.

    def set_cursor_shape(self, cursor_shape: CursorShape) -> None:
        if cursor_shape == CursorShape._NEVER_CHANGE:
            return

        self._cursor_shape_changed = True
        self.write_raw(
            {
                CursorShape.BLOCK: "\x1b[2 q",
                CursorShape.BEAM: "\x1b[6 q",
                CursorShape.UNDERLINE: "\x1b[4 q",
                CursorShape.BLINKING_BLOCK: "\x1b[1 q",
                CursorShape.BLINKING_BEAM: "\x1b[5 q",
                CursorShape.BLINKING_UNDERLINE: "\x1b[3 q",
            }.get(cursor_shape, "")
        )

    def reset_cursor_shape(self) -> None:
        "Reset cursor shape."
        # (Only reset cursor shape, if we ever changed it.)
        if self._cursor_shape_changed:
            self._cursor_shape_changed = False

            # Reset cursor shape.
            self.write_raw("\x1b[0 q")

    def flush(self) -> None:
        """
        Write to output stream and flush.
        """
        if not self._buffer:
            return

        data = "".join(self._buffer)
        self._buffer = []

        flush_stdout(self.stdout, data)

    def ask_for_cpr(self) -> None:
        """
        Asks for a cursor position report (CPR).
        """
        self.write_raw("\x1b[6n")
        self.flush()

    @property
    def responds_to_cpr(self) -> bool:
        if not self.enable_cpr:
            return False

        # When the input is a tty, we assume that CPR is supported.
        # It's not when the input is piped from Pexpect.
        if os.environ.get("PROMPT_TOOLKIT_NO_CPR", "") == "1":
            return False

        if is_dumb_terminal(self.term):
            return False
        try:
            return self.stdout.isatty()
        except ValueError:
            return False  # ValueError: I/O operation on closed file

    def bell(self) -> None:
        "Sound bell."
        if self.enable_bell:
            self.write_raw("\a")
            self.flush()

    def get_default_color_depth(self) -> ColorDepth:
        """
        Return the default color depth for a vt100 terminal, according to the
        our term value.

        We prefer 256 colors almost always, because this is what most terminals
        support these days, and is a good default.
        """
        if self.default_color_depth is not None:
            return self.default_color_depth

        term = self.term

        if term is None:
            return ColorDepth.DEFAULT

        if is_dumb_terminal(term):
            return ColorDepth.DEPTH_1_BIT

        if term in ("linux", "eterm-color"):
            return ColorDepth.DEPTH_4_BIT

        return ColorDepth.DEFAULT

# === NexusCore/openenv\Lib\site-packages\joblib\numpy_pickle.py ===
"""Utilities for fast persistence of big data, with optional compression."""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import io
import os
import pickle
import warnings
from pathlib import Path

from .backports import make_memmap
from .compressor import (
    _COMPRESSORS,
    LZ4_NOT_INSTALLED_ERROR,
    BinaryZlibFile,
    BZ2CompressorWrapper,
    GzipCompressorWrapper,
    LZ4CompressorWrapper,
    LZMACompressorWrapper,
    XZCompressorWrapper,
    ZlibCompressorWrapper,
    lz4,
    register_compressor,
)

# For compatibility with old versions of joblib, we need ZNDArrayWrapper
# to be visible in the current namespace.
from .numpy_pickle_compat import (
    NDArrayWrapper,
    ZNDArrayWrapper,  # noqa: F401
    load_compatibility,
)
from .numpy_pickle_utils import (
    BUFFER_SIZE,
    Pickler,
    Unpickler,
    _ensure_native_byte_order,
    _read_bytes,
    _reconstruct,
    _validate_fileobject_and_memmap,
    _write_fileobject,
)

# Register supported compressors
register_compressor("zlib", ZlibCompressorWrapper())
register_compressor("gzip", GzipCompressorWrapper())
register_compressor("bz2", BZ2CompressorWrapper())
register_compressor("lzma", LZMACompressorWrapper())
register_compressor("xz", XZCompressorWrapper())
register_compressor("lz4", LZ4CompressorWrapper())


###############################################################################
# Utility objects for persistence.

# For convenience, 16 bytes are used to be sure to cover all the possible
# dtypes' alignments. For reference, see:
# https://numpy.org/devdocs/dev/alignment.html
NUMPY_ARRAY_ALIGNMENT_BYTES = 16


class NumpyArrayWrapper(object):
    """An object to be persisted instead of numpy arrays.

    This object is used to hack into the pickle machinery and read numpy
    array data from our custom persistence format.
    More precisely, this object is used for:
    * carrying the information of the persisted array: subclass, shape, order,
    dtype. Those ndarray metadata are used to correctly reconstruct the array
    with low level numpy functions.
    * determining if memmap is allowed on the array.
    * reading the array bytes from a file.
    * reading the array using memorymap from a file.
    * writing the array bytes to a file.

    Attributes
    ----------
    subclass: numpy.ndarray subclass
        Determine the subclass of the wrapped array.
    shape: numpy.ndarray shape
        Determine the shape of the wrapped array.
    order: {'C', 'F'}
        Determine the order of wrapped array data. 'C' is for C order, 'F' is
        for fortran order.
    dtype: numpy.ndarray dtype
        Determine the data type of the wrapped array.
    allow_mmap: bool
        Determine if memory mapping is allowed on the wrapped array.
        Default: False.
    """

    def __init__(
        self,
        subclass,
        shape,
        order,
        dtype,
        allow_mmap=False,
        numpy_array_alignment_bytes=NUMPY_ARRAY_ALIGNMENT_BYTES,
    ):
        """Constructor. Store the useful information for later."""
        self.subclass = subclass
        self.shape = shape
        self.order = order
        self.dtype = dtype
        self.allow_mmap = allow_mmap
        # We make numpy_array_alignment_bytes an instance attribute to allow us
        # to change our mind about the default alignment and still load the old
        # pickles (with the previous alignment) correctly
        self.numpy_array_alignment_bytes = numpy_array_alignment_bytes

    def safe_get_numpy_array_alignment_bytes(self):
        # NumpyArrayWrapper instances loaded from joblib <= 1.1 pickles don't
        # have an numpy_array_alignment_bytes attribute
        return getattr(self, "numpy_array_alignment_bytes", None)

    def write_array(self, array, pickler):
        """Write array bytes to pickler file handle.

        This function is an adaptation of the numpy write_array function
        available in version 1.10.1 in numpy/lib/format.py.
        """
        # Set buffer size to 16 MiB to hide the Python loop overhead.
        buffersize = max(16 * 1024**2 // array.itemsize, 1)
        if array.dtype.hasobject:
            # We contain Python objects so we cannot write out the data
            # directly. Instead, we will pickle it out with version 5 of the
            # pickle protocol.
            pickle.dump(array, pickler.file_handle, protocol=5)
        else:
            numpy_array_alignment_bytes = self.safe_get_numpy_array_alignment_bytes()
            if numpy_array_alignment_bytes is not None:
                current_pos = pickler.file_handle.tell()
                pos_after_padding_byte = current_pos + 1
                padding_length = numpy_array_alignment_bytes - (
                    pos_after_padding_byte % numpy_array_alignment_bytes
                )
                # A single byte is written that contains the padding length in
                # bytes
                padding_length_byte = int.to_bytes(
                    padding_length, length=1, byteorder="little"
                )
                pickler.file_handle.write(padding_length_byte)

                if padding_length != 0:
                    padding = b"\xff" * padding_length
                    pickler.file_handle.write(padding)

            for chunk in pickler.np.nditer(
                array,
                flags=["external_loop", "buffered", "zerosize_ok"],
                buffersize=buffersize,
                order=self.order,
            ):
                pickler.file_handle.write(chunk.tobytes("C"))

    def read_array(self, unpickler, ensure_native_byte_order):
        """Read array from unpickler file handle.

        This function is an adaptation of the numpy read_array function
        available in version 1.10.1 in numpy/lib/format.py.
        """
        if len(self.shape) == 0:
            count = 1
        else:
            # joblib issue #859: we cast the elements of self.shape to int64 to
            # prevent a potential overflow when computing their product.
            shape_int64 = [unpickler.np.int64(x) for x in self.shape]
            count = unpickler.np.multiply.reduce(shape_int64)
        # Now read the actual data.
        if self.dtype.hasobject:
            # The array contained Python objects. We need to unpickle the data.
            array = pickle.load(unpickler.file_handle)
        else:
            numpy_array_alignment_bytes = self.safe_get_numpy_array_alignment_bytes()
            if numpy_array_alignment_bytes is not None:
                padding_byte = unpickler.file_handle.read(1)
                padding_length = int.from_bytes(padding_byte, byteorder="little")
                if padding_length != 0:
                    unpickler.file_handle.read(padding_length)

            # This is not a real file. We have to read it the
            # memory-intensive way.
            # crc32 module fails on reads greater than 2 ** 32 bytes,
            # breaking large reads from gzip streams. Chunk reads to
            # BUFFER_SIZE bytes to avoid issue and reduce memory overhead
            # of the read. In non-chunked case count < max_read_count, so
            # only one read is performed.
            max_read_count = BUFFER_SIZE // min(BUFFER_SIZE, self.dtype.itemsize)

            array = unpickler.np.empty(count, dtype=self.dtype)
            for i in range(0, count, max_read_count):
                read_count = min(max_read_count, count - i)
                read_size = int(read_count * self.dtype.itemsize)
                data = _read_bytes(unpickler.file_handle, read_size, "array data")
                array[i : i + read_count] = unpickler.np.frombuffer(
                    data, dtype=self.dtype, count=read_count
                )
                del data

            if self.order == "F":
                array.shape = self.shape[::-1]
                array = array.transpose()
            else:
                array.shape = self.shape

        if ensure_native_byte_order:
            # Detect byte order mismatch and swap as needed.
            array = _ensure_native_byte_order(array)

        return array

    def read_mmap(self, unpickler):
        """Read an array using numpy memmap."""
        current_pos = unpickler.file_handle.tell()
        offset = current_pos
        numpy_array_alignment_bytes = self.safe_get_numpy_array_alignment_bytes()

        if numpy_array_alignment_bytes is not None:
            padding_byte = unpickler.file_handle.read(1)
            padding_length = int.from_bytes(padding_byte, byteorder="little")
            # + 1 is for the padding byte
            offset += padding_length + 1

        if unpickler.mmap_mode == "w+":
            unpickler.mmap_mode = "r+"

        marray = make_memmap(
            unpickler.filename,
            dtype=self.dtype,
            shape=self.shape,
            order=self.order,
            mode=unpickler.mmap_mode,
            offset=offset,
        )
        # update the offset so that it corresponds to the end of the read array
        unpickler.file_handle.seek(offset + marray.nbytes)

        if (
            numpy_array_alignment_bytes is None
            and current_pos % NUMPY_ARRAY_ALIGNMENT_BYTES != 0
        ):
            message = (
                f"The memmapped array {marray} loaded from the file "
                f"{unpickler.file_handle.name} is not byte aligned. "
                "This may cause segmentation faults if this memmapped array "
                "is used in some libraries like BLAS or PyTorch. "
                "To get rid of this warning, regenerate your pickle file "
                "with joblib >= 1.2.0. "
                "See https://github.com/joblib/joblib/issues/563 "
                "for more details"
            )
            warnings.warn(message)

        return marray

    def read(self, unpickler, ensure_native_byte_order):
        """Read the array corresponding to this wrapper.

        Use the unpickler to get all information to correctly read the array.

        Parameters
        ----------
        unpickler: NumpyUnpickler
        ensure_native_byte_order: bool
            If true, coerce the array to use the native endianness of the
            host system.

        Returns
        -------
        array: numpy.ndarray

        """
        # When requested, only use memmap mode if allowed.
        if unpickler.mmap_mode is not None and self.allow_mmap:
            assert not ensure_native_byte_order, (
                "Memmaps cannot be coerced to a given byte order, "
                "this code path is impossible."
            )
            array = self.read_mmap(unpickler)
        else:
            array = self.read_array(unpickler, ensure_native_byte_order)

        # Manage array subclass case
        if hasattr(array, "__array_prepare__") and self.subclass not in (
            unpickler.np.ndarray,
            unpickler.np.memmap,
        ):
            # We need to reconstruct another subclass
            new_array = _reconstruct(self.subclass, (0,), "b")
            return new_array.__array_prepare__(array)
        else:
            return array


###############################################################################
# Pickler classes


class NumpyPickler(Pickler):
    """A pickler to persist big data efficiently.

    The main features of this object are:
    * persistence of numpy arrays in a single file.
    * optional compression with a special care on avoiding memory copies.

    Attributes
    ----------
    fp: file
        File object handle used for serializing the input object.
    protocol: int, optional
        Pickle protocol used. Default is pickle.DEFAULT_PROTOCOL.
    """

    dispatch = Pickler.dispatch.copy()

    def __init__(self, fp, protocol=None):
        self.file_handle = fp
        self.buffered = isinstance(self.file_handle, BinaryZlibFile)

        # By default we want a pickle protocol that only changes with
        # the major python version and not the minor one
        if protocol is None:
            protocol = pickle.DEFAULT_PROTOCOL

        Pickler.__init__(self, self.file_handle, protocol=protocol)
        # delayed import of numpy, to avoid tight coupling
        try:
            import numpy as np
        except ImportError:
            np = None
        self.np = np

    def _create_array_wrapper(self, array):
        """Create and returns a numpy array wrapper from a numpy array."""
        order = (
            "F" if (array.flags.f_contiguous and not array.flags.c_contiguous) else "C"
        )
        allow_mmap = not self.buffered and not array.dtype.hasobject

        kwargs = {}
        try:
            self.file_handle.tell()
        except io.UnsupportedOperation:
            kwargs = {"numpy_array_alignment_bytes": None}

        wrapper = NumpyArrayWrapper(
            type(array),
            array.shape,
            order,
            array.dtype,
            allow_mmap=allow_mmap,
            **kwargs,
        )

        return wrapper

    def save(self, obj):
        """Subclass the Pickler `save` method.

        This is a total abuse of the Pickler class in order to use the numpy
        persistence function `save` instead of the default pickle
        implementation. The numpy array is replaced by a custom wrapper in the
        pickle persistence stack and the serialized array is written right
        after in the file. Warning: the file produced does not follow the
        pickle format. As such it can not be read with `pickle.load`.
        """
        if self.np is not None and type(obj) in (
            self.np.ndarray,
            self.np.matrix,
            self.np.memmap,
        ):
            if type(obj) is self.np.memmap:
                # Pickling doesn't work with memmapped arrays
                obj = self.np.asanyarray(obj)

            # The array wrapper is pickled instead of the real array.
            wrapper = self._create_array_wrapper(obj)
            Pickler.save(self, wrapper)

            # A framer was introduced with pickle protocol 4 and we want to
            # ensure the wrapper object is written before the numpy array
            # buffer in the pickle file.
            # See https://www.python.org/dev/peps/pep-3154/#framing to get
            # more information on the framer behavior.
            if self.proto >= 4:
                self.framer.commit_frame(force=True)

            # And then array bytes are written right after the wrapper.
            wrapper.write_array(obj, self)
            return

        return Pickler.save(self, obj)


class NumpyUnpickler(Unpickler):
    """A subclass of the Unpickler to unpickle our numpy pickles.

    Attributes
    ----------
    mmap_mode: str
        The memorymap mode to use for reading numpy arrays.
    file_handle: file_like
        File object to unpickle from.
    ensure_native_byte_order: bool
        If True, coerce the array to use the native endianness of the
        host system.
    filename: str
        Name of the file to unpickle from. It should correspond to file_handle.
        This parameter is required when using mmap_mode.
    np: module
        Reference to numpy module if numpy is installed else None.

    """

    dispatch = Unpickler.dispatch.copy()

    def __init__(self, filename, file_handle, ensure_native_byte_order, mmap_mode=None):
        # The next line is for backward compatibility with pickle generated
        # with joblib versions less than 0.10.
        self._dirname = os.path.dirname(filename)

        self.mmap_mode = mmap_mode
        self.file_handle = file_handle
        # filename is required for numpy mmap mode.
        self.filename = filename
        self.compat_mode = False
        self.ensure_native_byte_order = ensure_native_byte_order
        Unpickler.__init__(self, self.file_handle)
        try:
            import numpy as np
        except ImportError:
            np = None
        self.np = np

    def load_build(self):
        """Called to set the state of a newly created object.

        We capture it to replace our place-holder objects, NDArrayWrapper or
        NumpyArrayWrapper, by the array we are interested in. We
        replace them directly in the stack of pickler.
        NDArrayWrapper is used for backward compatibility with joblib <= 0.9.
        """
        Unpickler.load_build(self)

        # For backward compatibility, we support NDArrayWrapper objects.
        if isinstance(self.stack[-1], (NDArrayWrapper, NumpyArrayWrapper)):
            if self.np is None:
                raise ImportError(
                    "Trying to unpickle an ndarray, but numpy didn't import correctly"
                )
            array_wrapper = self.stack.pop()
            # If any NDArrayWrapper is found, we switch to compatibility mode,
            # this will be used to raise a DeprecationWarning to the user at
            # the end of the unpickling.
            if isinstance(array_wrapper, NDArrayWrapper):
                self.compat_mode = True
                _array_payload = array_wrapper.read(self)
            else:
                _array_payload = array_wrapper.read(self, self.ensure_native_byte_order)

            self.stack.append(_array_payload)

    # Be careful to register our new method.
    dispatch[pickle.BUILD[0]] = load_build


###############################################################################
# Utility functions


def dump(value, filename, compress=0, protocol=None):
    """Persist an arbitrary Python object into one file.

    Read more in the :ref:`User Guide <persistence>`.

    Parameters
    ----------
    value: any Python object
        The object to store to disk.
    filename: str, pathlib.Path, or file object.
        The file object or path of the file in which it is to be stored.
        The compression method corresponding to one of the supported filename
        extensions ('.z', '.gz', '.bz2', '.xz' or '.lzma') will be used
        automatically.
    compress: int from 0 to 9 or bool or 2-tuple, optional
        Optional compression level for the data. 0 or False is no compression.
        Higher value means more compression, but also slower read and
        write times. Using a value of 3 is often a good compromise.
        See the notes for more details.
        If compress is True, the compression level used is 3.
        If compress is a 2-tuple, the first element must correspond to a string
        between supported compressors (e.g 'zlib', 'gzip', 'bz2', 'lzma'
        'xz'), the second element must be an integer from 0 to 9, corresponding
        to the compression level.
    protocol: int, optional
        Pickle protocol, see pickle.dump documentation for more details.

    Returns
    -------
    filenames: list of strings
        The list of file names in which the data is stored. If
        compress is false, each array is stored in a different file.

    See Also
    --------
    joblib.load : corresponding loader

    Notes
    -----
    Memmapping on load cannot be used for compressed files. Thus
    using compression can significantly slow down loading. In
    addition, compressed files take up extra memory during
    dump and load.

    """

    if Path is not None and isinstance(filename, Path):
        filename = str(filename)

    is_filename = isinstance(filename, str)
    is_fileobj = hasattr(filename, "write")

    compress_method = "zlib"  # zlib is the default compression method.
    if compress is True:
        # By default, if compress is enabled, we want the default compress
        # level of the compressor.
        compress_level = None
    elif isinstance(compress, tuple):
        # a 2-tuple was set in compress
        if len(compress) != 2:
            raise ValueError(
                "Compress argument tuple should contain exactly 2 elements: "
                "(compress method, compress level), you passed {}".format(compress)
            )
        compress_method, compress_level = compress
    elif isinstance(compress, str):
        compress_method = compress
        compress_level = None  # Use default compress level
        compress = (compress_method, compress_level)
    else:
        compress_level = compress

    if compress_method == "lz4" and lz4 is None:
        raise ValueError(LZ4_NOT_INSTALLED_ERROR)

    if (
        compress_level is not None
        and compress_level is not False
        and compress_level not in range(10)
    ):
        # Raising an error if a non valid compress level is given.
        raise ValueError(
            'Non valid compress level given: "{}". Possible values are {}.'.format(
                compress_level, list(range(10))
            )
        )

    if compress_method not in _COMPRESSORS:
        # Raising an error if an unsupported compression method is given.
        raise ValueError(
            'Non valid compression method given: "{}". Possible values are {}.'.format(
                compress_method, _COMPRESSORS
            )
        )

    if not is_filename and not is_fileobj:
        # People keep inverting arguments, and the resulting error is
        # incomprehensible
        raise ValueError(
            "Second argument should be a filename or a file-like object, "
            "%s (type %s) was given." % (filename, type(filename))
        )

    if is_filename and not isinstance(compress, tuple):
        # In case no explicit compression was requested using both compression
        # method and level in a tuple and the filename has an explicit
        # extension, we select the corresponding compressor.

        # unset the variable to be sure no compression level is set afterwards.
        compress_method = None
        for name, compressor in _COMPRESSORS.items():
            if filename.endswith(compressor.extension):
                compress_method = name

        if compress_method in _COMPRESSORS and compress_level == 0:
            # we choose the default compress_level in case it was not given
            # as an argument (using compress).
            compress_level = None

    if compress_level != 0:
        with _write_fileobject(
            filename, compress=(compress_method, compress_level)
        ) as f:
            NumpyPickler(f, protocol=protocol).dump(value)
    elif is_filename:
        with open(filename, "wb") as f:
            NumpyPickler(f, protocol=protocol).dump(value)
    else:
        NumpyPickler(filename, protocol=protocol).dump(value)

    # If the target container is a file object, nothing is returned.
    if is_fileobj:
        return

    # For compatibility, the list of created filenames (e.g with one element
    # after 0.10.0) is returned by default.
    return [filename]


def _unpickle(fobj, ensure_native_byte_order, filename="", mmap_mode=None):
    """Internal unpickling function."""
    # We are careful to open the file handle early and keep it open to
    # avoid race-conditions on renames.
    # That said, if data is stored in companion files, which can be
    # the case with the old persistence format, moving the directory
    # will create a race when joblib tries to access the companion
    # files.
    unpickler = NumpyUnpickler(
        filename, fobj, ensure_native_byte_order, mmap_mode=mmap_mode
    )
    obj = None
    try:
        obj = unpickler.load()
        if unpickler.compat_mode:
            warnings.warn(
                "The file '%s' has been generated with a "
                "joblib version less than 0.10. "
                "Please regenerate this pickle file." % filename,
                DeprecationWarning,
                stacklevel=3,
            )
    except UnicodeDecodeError as exc:
        # More user-friendly error message
        new_exc = ValueError(
            "You may be trying to read with "
            "python 3 a joblib pickle generated with python 2. "
            "This feature is not supported by joblib."
        )
        new_exc.__cause__ = exc
        raise new_exc
    return obj


def load_temporary_memmap(filename, mmap_mode, unlink_on_gc_collect):
    from ._memmapping_reducer import JOBLIB_MMAPS, add_maybe_unlink_finalizer

    with open(filename, "rb") as f:
        with _validate_fileobject_and_memmap(f, filename, mmap_mode) as (
            fobj,
            validated_mmap_mode,
        ):
            # Memmap are used for interprocess communication, which should
            # keep the objects untouched. We pass `ensure_native_byte_order=False`
            # to remain consistent with the loading behavior of non-memmaped arrays
            # in workers, where the byte order is preserved.
            # Note that we do not implement endianness change for memmaps, as this
            # would result in inconsistent behavior.
            obj = _unpickle(
                fobj,
                ensure_native_byte_order=False,
                filename=filename,
                mmap_mode=validated_mmap_mode,
            )

    JOBLIB_MMAPS.add(obj.filename)
    if unlink_on_gc_collect:
        add_maybe_unlink_finalizer(obj)
    return obj


def load(filename, mmap_mode=None, ensure_native_byte_order="auto"):
    """Reconstruct a Python object from a file persisted with joblib.dump.

    Read more in the :ref:`User Guide <persistence>`.

    WARNING: joblib.load relies on the pickle module and can therefore
    execute arbitrary Python code. It should therefore never be used
    to load files from untrusted sources.

    Parameters
    ----------
    filename: str, pathlib.Path, or file object.
        The file object or path of the file from which to load the object
    mmap_mode: {None, 'r+', 'r', 'w+', 'c'}, optional
        If not None, the arrays are memory-mapped from the disk. This
        mode has no effect for compressed files. Note that in this
        case the reconstructed object might no longer match exactly
        the originally pickled object.
    ensure_native_byte_order: bool, or 'auto', default=='auto'
        If True, ensures that the byte order of the loaded arrays matches the
        native byte ordering (or _endianness_) of the host system. This is not
        compatible with memory-mapped arrays and using non-null `mmap_mode`
        parameter at the same time will raise an error. The default 'auto'
        parameter is equivalent to True if `mmap_mode` is None, else False.

    Returns
    -------
    result: any Python object
        The object stored in the file.

    See Also
    --------
    joblib.dump : function to save an object

    Notes
    -----

    This function can load numpy array files saved separately during the
    dump. If the mmap_mode argument is given, it is passed to np.load and
    arrays are loaded as memmaps. As a consequence, the reconstructed
    object might not match the original pickled object. Note that if the
    file was saved with compression, the arrays cannot be memmapped.
    """
    if ensure_native_byte_order == "auto":
        ensure_native_byte_order = mmap_mode is None

    if ensure_native_byte_order and mmap_mode is not None:
        raise ValueError(
            "Native byte ordering can only be enforced if 'mmap_mode' parameter "
            f"is set to None, but got 'mmap_mode={mmap_mode}' instead."
        )

    if Path is not None and isinstance(filename, Path):
        filename = str(filename)

    if hasattr(filename, "read"):
        fobj = filename
        filename = getattr(fobj, "name", "")
        with _validate_fileobject_and_memmap(fobj, filename, mmap_mode) as (fobj, _):
            obj = _unpickle(fobj, ensure_native_byte_order=ensure_native_byte_order)
    else:
        with open(filename, "rb") as f:
            with _validate_fileobject_and_memmap(f, filename, mmap_mode) as (
                fobj,
                validated_mmap_mode,
            ):
                if isinstance(fobj, str):
                    # if the returned file object is a string, this means we
                    # try to load a pickle file generated with an version of
                    # Joblib so we load it with joblib compatibility function.
                    return load_compatibility(fobj)

                # A memory-mapped array has to be mapped with the endianness
                # it has been written with. Other arrays are coerced to the
                # native endianness of the host system.
                obj = _unpickle(
                    fobj,
                    ensure_native_byte_order=ensure_native_byte_order,
                    filename=filename,
                    mmap_mode=validated_mmap_mode,
                )

    return obj

# === NexusCore/openenv\Lib\site-packages\psutil\_pssunos.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sun OS Solaris platform implementation."""

import errno
import functools
import os
import socket
import subprocess
import sys
from collections import namedtuple
from socket import AF_INET

from . import _common
from . import _psposix
from . import _psutil_posix as cext_posix
from . import _psutil_sunos as cext
from ._common import AF_INET6
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import ZombieProcess
from ._common import debug
from ._common import get_procfs_path
from ._common import isfile_strict
from ._common import memoize_when_activated
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._compat import PY3
from ._compat import FileNotFoundError
from ._compat import PermissionError
from ._compat import ProcessLookupError
from ._compat import b


__extra__all__ = ["CONN_IDLE", "CONN_BOUND", "PROCFS_PATH"]


# =====================================================================
# --- globals
# =====================================================================


PAGE_SIZE = cext_posix.getpagesize()
AF_LINK = cext_posix.AF_LINK
IS_64_BIT = sys.maxsize > 2**32

CONN_IDLE = "IDLE"
CONN_BOUND = "BOUND"

PROC_STATUSES = {
    cext.SSLEEP: _common.STATUS_SLEEPING,
    cext.SRUN: _common.STATUS_RUNNING,
    cext.SZOMB: _common.STATUS_ZOMBIE,
    cext.SSTOP: _common.STATUS_STOPPED,
    cext.SIDL: _common.STATUS_IDLE,
    cext.SONPROC: _common.STATUS_RUNNING,  # same as run
    cext.SWAIT: _common.STATUS_WAITING,
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
    cext.TCPS_IDLE: CONN_IDLE,  # sunos specific
    cext.TCPS_BOUND: CONN_BOUND,  # sunos specific
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
    uid=8,
    euid=9,
    gid=10,
    egid=11,
)


# =====================================================================
# --- named tuples
# =====================================================================


# psutil.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'system', 'idle', 'iowait'])
# psutil.cpu_times(percpu=True)
pcputimes = namedtuple(
    'pcputimes', ['user', 'system', 'children_user', 'children_system']
)
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
pfullmem = pmem
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple(
    'pmmap_grouped', ['path', 'rss', 'anonymous', 'locked']
)
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields)
)


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    """Report virtual memory metrics."""
    # we could have done this with kstat, but IMHO this is good enough
    total = os.sysconf('SC_PHYS_PAGES') * PAGE_SIZE
    # note: there's no difference on Solaris
    free = avail = os.sysconf('SC_AVPHYS_PAGES') * PAGE_SIZE
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return svmem(total, avail, percent, used, free)


def swap_memory():
    """Report swap memory metrics."""
    sin, sout = cext.swap_mem()
    # XXX
    # we are supposed to get total/free by doing so:
    # http://cvs.opensolaris.org/source/xref/onnv/onnv-gate/
    #     usr/src/cmd/swap/swap.c
    # ...nevertheless I can't manage to obtain the same numbers as 'swap'
    # cmdline utility, so let's parse its output (sigh!)
    p = subprocess.Popen(
        [
            '/usr/bin/env',
            'PATH=/usr/sbin:/sbin:%s' % os.environ['PATH'],
            'swap',
            '-l',
        ],
        stdout=subprocess.PIPE,
    )
    stdout, _ = p.communicate()
    if PY3:
        stdout = stdout.decode(sys.stdout.encoding)
    if p.returncode != 0:
        raise RuntimeError("'swap -l' failed (retcode=%s)" % p.returncode)

    lines = stdout.strip().split('\n')[1:]
    if not lines:
        msg = 'no swap device(s) configured'
        raise RuntimeError(msg)
    total = free = 0
    for line in lines:
        line = line.split()
        t, f = line[3:5]
        total += int(int(t) * 512)
        free += int(int(f) * 512)
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(
        total, used, free, percent, sin * PAGE_SIZE, sout * PAGE_SIZE
    )


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
    """Return the number of CPU cores in the system."""
    return cext.cpu_count_cores()


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    ctx_switches, interrupts, syscalls, traps = cext.cpu_stats()
    soft_interrupts = 0
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
            try:
                if not disk_usage(mountpoint).total:
                    continue
            except OSError as err:
                # https://github.com/giampaolo/psutil/issues/1674
                debug("skipping %r: %s" % (mountpoint, err))
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


net_io_counters = cext.net_io_counters
net_if_addrs = cext_posix.net_if_addrs


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    Only INET sockets are returned (UNIX are not).
    """
    cmap = _common.conn_tmap.copy()
    if _pid == -1:
        cmap.pop('unix', 0)
    if kind not in cmap:
        raise ValueError(
            "invalid %r kind argument; choose between %s"
            % (kind, ', '.join([repr(x) for x in cmap]))
        )
    families, types = _common.conn_tmap[kind]
    rawlist = cext.net_connections(_pid)
    ret = set()
    for item in rawlist:
        fd, fam, type_, laddr, raddr, status, pid = item
        if fam not in families:
            continue
        if type_ not in types:
            continue
        # TODO: refactor and use _common.conn_to_ntuple.
        if fam in (AF_INET, AF_INET6):
            if laddr:
                laddr = _common.addr(*laddr)
            if raddr:
                raddr = _common.addr(*raddr)
        status = TCP_STATUSES[status]
        fam = sockfam_to_enum(fam)
        type_ = socktype_to_enum(type_)
        if _pid == -1:
            nt = _common.sconn(fd, fam, type_, laddr, raddr, status, pid)
        else:
            nt = _common.pconn(fd, fam, type_, laddr, raddr, status)
        ret.add(nt)
    return list(ret)


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    ret = cext.net_if_stats()
    for name, items in ret.items():
        isup, duplex, speed, mtu = items
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu, '')
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
    return [int(x) for x in os.listdir(b(get_procfs_path())) if x.isdigit()]


def pid_exists(pid):
    """Check for the existence of a unix pid."""
    return _psposix.pid_exists(pid)


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
        except OSError:
            if self.pid == 0:
                if 0 in pids():
                    raise AccessDenied(self.pid, self._name)
                else:
                    raise
            raise

    return wrapper


class Process:
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    def _assert_alive(self):
        """Raise NSP if the process disappeared on us."""
        # For those C function who do not raise NSP, possibly returning
        # incorrect or incomplete result.
        os.stat('%s/%s' % (self._procfs_path, self.pid))

    def oneshot_enter(self):
        self._proc_name_and_args.cache_activate(self)
        self._proc_basic_info.cache_activate(self)
        self._proc_cred.cache_activate(self)

    def oneshot_exit(self):
        self._proc_name_and_args.cache_deactivate(self)
        self._proc_basic_info.cache_deactivate(self)
        self._proc_cred.cache_deactivate(self)

    @wrap_exceptions
    @memoize_when_activated
    def _proc_name_and_args(self):
        return cext.proc_name_and_args(self.pid, self._procfs_path)

    @wrap_exceptions
    @memoize_when_activated
    def _proc_basic_info(self):
        if self.pid == 0 and not os.path.exists(
            '%s/%s/psinfo' % (self._procfs_path, self.pid)
        ):
            raise AccessDenied(self.pid)
        ret = cext.proc_basic_info(self.pid, self._procfs_path)
        assert len(ret) == len(proc_info_map)
        return ret

    @wrap_exceptions
    @memoize_when_activated
    def _proc_cred(self):
        return cext.proc_cred(self.pid, self._procfs_path)

    @wrap_exceptions
    def name(self):
        # note: max len == 15
        return self._proc_name_and_args()[0]

    @wrap_exceptions
    def exe(self):
        try:
            return os.readlink(
                "%s/%s/path/a.out" % (self._procfs_path, self.pid)
            )
        except OSError:
            pass  # continue and guess the exe name from the cmdline
        # Will be guessed later from cmdline but we want to explicitly
        # invoke cmdline here in order to get an AccessDenied
        # exception if the user has not enough privileges.
        self.cmdline()
        return ""

    @wrap_exceptions
    def cmdline(self):
        return self._proc_name_and_args()[1].split(' ')

    @wrap_exceptions
    def environ(self):
        return cext.proc_environ(self.pid, self._procfs_path)

    @wrap_exceptions
    def create_time(self):
        return self._proc_basic_info()[proc_info_map['create_time']]

    @wrap_exceptions
    def num_threads(self):
        return self._proc_basic_info()[proc_info_map['num_threads']]

    @wrap_exceptions
    def nice_get(self):
        # Note #1: getpriority(3) doesn't work for realtime processes.
        # Psinfo is what ps uses, see:
        # https://github.com/giampaolo/psutil/issues/1194
        return self._proc_basic_info()[proc_info_map['nice']]

    @wrap_exceptions
    def nice_set(self, value):
        if self.pid in (2, 3):
            # Special case PIDs: internally setpriority(3) return ESRCH
            # (no such process), no matter what.
            # The process actually exists though, as it has a name,
            # creation time, etc.
            raise AccessDenied(self.pid, self._name)
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def ppid(self):
        self._ppid = self._proc_basic_info()[proc_info_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def uids(self):
        try:
            real, effective, saved, _, _, _ = self._proc_cred()
        except AccessDenied:
            real = self._proc_basic_info()[proc_info_map['uid']]
            effective = self._proc_basic_info()[proc_info_map['euid']]
            saved = None
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def gids(self):
        try:
            _, _, _, real, effective, saved = self._proc_cred()
        except AccessDenied:
            real = self._proc_basic_info()[proc_info_map['gid']]
            effective = self._proc_basic_info()[proc_info_map['egid']]
            saved = None
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def cpu_times(self):
        try:
            times = cext.proc_cpu_times(self.pid, self._procfs_path)
        except OSError as err:
            if err.errno == errno.EOVERFLOW and not IS_64_BIT:
                # We may get here if we attempt to query a 64bit process
                # with a 32bit python.
                # Error originates from read() and also tools like "cat"
                # fail in the same way (!).
                # Since there simply is no way to determine CPU times we
                # return 0.0 as a fallback. See:
                # https://github.com/giampaolo/psutil/issues/857
                times = (0.0, 0.0, 0.0, 0.0)
            else:
                raise
        return _common.pcputimes(*times)

    @wrap_exceptions
    def cpu_num(self):
        return cext.proc_cpu_num(self.pid, self._procfs_path)

    @wrap_exceptions
    def terminal(self):
        procfs_path = self._procfs_path
        hit_enoent = False
        tty = wrap_exceptions(self._proc_basic_info()[proc_info_map['ttynr']])
        if tty != cext.PRNODEV:
            for x in (0, 1, 2, 255):
                try:
                    return os.readlink(
                        '%s/%d/path/%d' % (procfs_path, self.pid, x)
                    )
                except FileNotFoundError:
                    hit_enoent = True
                    continue
        if hit_enoent:
            self._assert_alive()

    @wrap_exceptions
    def cwd(self):
        # /proc/PID/path/cwd may not be resolved by readlink() even if
        # it exists (ls shows it). If that's the case and the process
        # is still alive return None (we can return None also on BSD).
        # Reference: http://goo.gl/55XgO
        procfs_path = self._procfs_path
        try:
            return os.readlink("%s/%s/path/cwd" % (procfs_path, self.pid))
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

    @wrap_exceptions
    def threads(self):
        procfs_path = self._procfs_path
        ret = []
        tids = os.listdir('%s/%d/lwp' % (procfs_path, self.pid))
        hit_enoent = False
        for tid in tids:
            tid = int(tid)
            try:
                utime, stime = cext.query_process_thread(
                    self.pid, tid, procfs_path
                )
            except EnvironmentError as err:
                if err.errno == errno.EOVERFLOW and not IS_64_BIT:
                    # We may get here if we attempt to query a 64bit process
                    # with a 32bit python.
                    # Error originates from read() and also tools like "cat"
                    # fail in the same way (!).
                    # Since there simply is no way to determine CPU times we
                    # return 0.0 as a fallback. See:
                    # https://github.com/giampaolo/psutil/issues/857
                    continue
                # ENOENT == thread gone in meantime
                if err.errno == errno.ENOENT:
                    hit_enoent = True
                    continue
                raise
            else:
                nt = _common.pthread(tid, utime, stime)
                ret.append(nt)
        if hit_enoent:
            self._assert_alive()
        return ret

    @wrap_exceptions
    def open_files(self):
        retlist = []
        hit_enoent = False
        procfs_path = self._procfs_path
        pathdir = '%s/%d/path' % (procfs_path, self.pid)
        for fd in os.listdir('%s/%d/fd' % (procfs_path, self.pid)):
            path = os.path.join(pathdir, fd)
            if os.path.islink(path):
                try:
                    file = os.readlink(path)
                except FileNotFoundError:
                    hit_enoent = True
                    continue
                else:
                    if isfile_strict(file):
                        retlist.append(_common.popenfile(file, int(fd)))
        if hit_enoent:
            self._assert_alive()
        return retlist

    def _get_unix_sockets(self, pid):
        """Get UNIX sockets used by process by parsing 'pfiles' output."""
        # TODO: rewrite this in C (...but the damn netstat source code
        # does not include this part! Argh!!)
        cmd = ["pfiles", str(pid)]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        if PY3:
            stdout, stderr = (
                x.decode(sys.stdout.encoding) for x in (stdout, stderr)
            )
        if p.returncode != 0:
            if 'permission denied' in stderr.lower():
                raise AccessDenied(self.pid, self._name)
            if 'no such process' in stderr.lower():
                raise NoSuchProcess(self.pid, self._name)
            raise RuntimeError("%r command error\n%s" % (cmd, stderr))

        lines = stdout.split('\n')[2:]
        for i, line in enumerate(lines):
            line = line.lstrip()
            if line.startswith('sockname: AF_UNIX'):
                path = line.split(' ', 2)[2]
                type = lines[i - 2].strip()
                if type == 'SOCK_STREAM':
                    type = socket.SOCK_STREAM
                elif type == 'SOCK_DGRAM':
                    type = socket.SOCK_DGRAM
                else:
                    type = -1
                yield (-1, socket.AF_UNIX, type, path, "", _common.CONN_NONE)

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

        # UNIX sockets
        if kind in ('all', 'unix'):
            ret.extend([
                _common.pconn(*conn)
                for conn in self._get_unix_sockets(self.pid)
            ])
        return ret

    nt_mmap_grouped = namedtuple('mmap', 'path rss anon locked')
    nt_mmap_ext = namedtuple('mmap', 'addr perms path rss anon locked')

    @wrap_exceptions
    def memory_maps(self):
        def toaddr(start, end):
            return '%s-%s' % (
                hex(start)[2:].strip('L'),
                hex(end)[2:].strip('L'),
            )

        procfs_path = self._procfs_path
        retlist = []
        try:
            rawlist = cext.proc_memory_maps(self.pid, procfs_path)
        except OSError as err:
            if err.errno == errno.EOVERFLOW and not IS_64_BIT:
                # We may get here if we attempt to query a 64bit process
                # with a 32bit python.
                # Error originates from read() and also tools like "cat"
                # fail in the same way (!).
                # Since there simply is no way to determine CPU times we
                # return 0.0 as a fallback. See:
                # https://github.com/giampaolo/psutil/issues/857
                return []
            else:
                raise
        hit_enoent = False
        for item in rawlist:
            addr, addrsize, perm, name, rss, anon, locked = item
            addr = toaddr(addr, addrsize)
            if not name.startswith('['):
                try:
                    name = os.readlink(
                        '%s/%s/path/%s' % (procfs_path, self.pid, name)
                    )
                except OSError as err:
                    if err.errno == errno.ENOENT:
                        # sometimes the link may not be resolved by
                        # readlink() even if it exists (ls shows it).
                        # If that's the case we just return the
                        # unresolved link path.
                        # This seems an incosistency with /proc similar
                        # to: http://goo.gl/55XgO
                        name = '%s/%s/path/%s' % (procfs_path, self.pid, name)
                        hit_enoent = True
                    else:
                        raise
            retlist.append((addr, perm, name, rss, anon, locked))
        if hit_enoent:
            self._assert_alive()
        return retlist

    @wrap_exceptions
    def num_fds(self):
        return len(os.listdir("%s/%s/fd" % (self._procfs_path, self.pid)))

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(
            *cext.proc_num_ctx_switches(self.pid, self._procfs_path)
        )

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_guest_mode.py ===
from __future__ import annotations

import asyncio
import contextlib
import queue
import signal
import socket
import sys
import threading
import time
import traceback
import warnings
import weakref
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from functools import partial
from math import inf
from typing import (
    TYPE_CHECKING,
    NoReturn,
    TypeVar,
    cast,
)

import pytest
import sniffio
from outcome import Outcome

import trio
import trio.testing
from trio.abc import Clock, Instrument

from .tutil import gc_collect_harder, restore_unraisablehook

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from trio._channel import MemorySendChannel

T = TypeVar("T")
InHost: TypeAlias = Callable[[Callable[[], object]], None]


# The simplest possible "host" loop.
# Nice features:
# - we can run code "outside" of trio using the schedule function passed to
#   our main
# - final result is returned
# - any unhandled exceptions cause an immediate crash
def trivial_guest_run(
    trio_fn: Callable[[InHost], Awaitable[T]],
    *,
    in_host_after_start: Callable[[], None] | None = None,
    host_uses_signal_set_wakeup_fd: bool = False,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> T:
    todo: queue.Queue[tuple[str, Outcome[T] | Callable[[], object]]] = queue.Queue()

    host_thread = threading.current_thread()

    def run_sync_soon_threadsafe(fn: Callable[[], object]) -> None:
        nonlocal todo
        if host_thread is threading.current_thread():  # pragma: no cover
            crash = partial(
                pytest.fail,
                "run_sync_soon_threadsafe called from host thread",
            )
            todo.put(("run", crash))
        todo.put(("run", fn))

    def run_sync_soon_not_threadsafe(fn: Callable[[], object]) -> None:
        nonlocal todo
        if host_thread is not threading.current_thread():  # pragma: no cover
            crash = partial(
                pytest.fail,
                "run_sync_soon_not_threadsafe called from worker thread",
            )
            todo.put(("run", crash))
        todo.put(("run", fn))

    def done_callback(outcome: Outcome[T]) -> None:
        nonlocal todo
        todo.put(("unwrap", outcome))

    trio.lowlevel.start_guest_run(
        trio_fn,
        run_sync_soon_not_threadsafe,
        run_sync_soon_threadsafe=run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
        done_callback=done_callback,
        host_uses_signal_set_wakeup_fd=host_uses_signal_set_wakeup_fd,
        clock=clock,
        instruments=instruments,
        restrict_keyboard_interrupt_to_checkpoints=restrict_keyboard_interrupt_to_checkpoints,
        strict_exception_groups=strict_exception_groups,
    )
    if in_host_after_start is not None:
        in_host_after_start()

    try:
        while True:
            op, obj = todo.get()
            if op == "run":
                assert not isinstance(obj, Outcome)
                obj()
            elif op == "unwrap":
                assert isinstance(obj, Outcome)
                return obj.unwrap()
            else:  # pragma: no cover
                raise NotImplementedError(f"{op!r} not handled")
    finally:
        # Make sure that exceptions raised here don't capture these, so that
        # if an exception does cause us to abandon a run then the Trio state
        # has a chance to be GC'ed and warn about it.
        del todo, run_sync_soon_threadsafe, done_callback


def test_guest_trivial() -> None:
    async def trio_return(in_host: InHost) -> str:
        await trio.lowlevel.checkpoint()
        return "ok"

    assert trivial_guest_run(trio_return) == "ok"

    async def trio_fail(in_host: InHost) -> NoReturn:
        raise KeyError("whoopsiedaisy")

    with pytest.raises(KeyError, match="whoopsiedaisy"):
        trivial_guest_run(trio_fail)


def test_guest_can_do_io() -> None:
    async def trio_main(in_host: InHost) -> None:
        record = []
        a, b = trio.socket.socketpair()
        with a, b:
            async with trio.open_nursery() as nursery:

                async def do_receive() -> None:
                    record.append(await a.recv(1))

                nursery.start_soon(do_receive)
                await trio.testing.wait_all_tasks_blocked()

                await b.send(b"x")

        assert record == [b"x"]

    trivial_guest_run(trio_main)


def test_guest_is_initialized_when_start_returns() -> None:
    trio_token = None
    record = []

    async def trio_main(in_host: InHost) -> str:
        record.append("main task ran")
        await trio.lowlevel.checkpoint()
        assert trio.lowlevel.current_trio_token() is trio_token
        return "ok"

    def after_start() -> None:
        # We should get control back before the main task executes any code
        assert record == []

        nonlocal trio_token
        trio_token = trio.lowlevel.current_trio_token()
        trio_token.run_sync_soon(record.append, "run_sync_soon cb ran")

        @trio.lowlevel.spawn_system_task
        async def early_task() -> None:
            record.append("system task ran")
            await trio.lowlevel.checkpoint()

    res = trivial_guest_run(trio_main, in_host_after_start=after_start)
    assert res == "ok"
    assert set(record) == {"system task ran", "main task ran", "run_sync_soon cb ran"}

    class BadClock(Clock):
        def start_clock(self) -> NoReturn:
            raise ValueError("whoops")

        def current_time(self) -> float:
            raise NotImplementedError()

        def deadline_to_sleep_time(self, deadline: float) -> float:
            raise NotImplementedError()

    def after_start_never_runs() -> None:  # pragma: no cover
        pytest.fail("shouldn't get here")

    # Errors during initialization (which can only be TrioInternalErrors)
    # are raised out of start_guest_run, not out of the done_callback
    with pytest.raises(trio.TrioInternalError):
        trivial_guest_run(
            trio_main,
            clock=BadClock(),
            in_host_after_start=after_start_never_runs,
        )


def test_host_can_directly_wake_trio_task() -> None:
    async def trio_main(in_host: InHost) -> str:
        ev = trio.Event()
        in_host(ev.set)
        await ev.wait()
        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


def test_host_altering_deadlines_wakes_trio_up() -> None:
    def set_deadline(cscope: trio.CancelScope, new_deadline: float) -> None:
        cscope.deadline = new_deadline

    async def trio_main(in_host: InHost) -> str:
        with trio.CancelScope() as cscope:
            in_host(lambda: set_deadline(cscope, -inf))
            await trio.sleep_forever()
        assert cscope.cancelled_caught

        with trio.CancelScope() as cscope:
            # also do a change that doesn't affect the next deadline, just to
            # exercise that path
            in_host(lambda: set_deadline(cscope, 1e6))
            in_host(lambda: set_deadline(cscope, -inf))
            await trio.sleep(999)
        assert cscope.cancelled_caught

        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


def test_guest_mode_sniffio_integration() -> None:
    current_async_library = sniffio.current_async_library
    sniffio_library = sniffio.thread_local

    async def trio_main(in_host: InHost) -> str:
        async def synchronize() -> None:
            """Wait for all in_host() calls issued so far to complete."""
            evt = trio.Event()
            in_host(evt.set)
            await evt.wait()

        # Host and guest have separate sniffio_library contexts
        in_host(partial(setattr, sniffio_library, "name", "nullio"))
        await synchronize()
        assert current_async_library() == "trio"

        record = []
        in_host(lambda: record.append(current_async_library()))
        await synchronize()
        assert record == ["nullio"]
        assert current_async_library() == "trio"

        return "ok"

    try:
        assert trivial_guest_run(trio_main) == "ok"
    finally:
        sniffio_library.name = None


def test_guest_mode_trio_context_detection() -> None:
    def check(thing: bool) -> None:
        assert thing

    assert not trio.lowlevel.in_trio_run()
    assert not trio.lowlevel.in_trio_task()

    async def trio_main(in_host: InHost) -> None:
        for _ in range(2):
            assert trio.lowlevel.in_trio_run()
            assert trio.lowlevel.in_trio_task()

            in_host(lambda: check(trio.lowlevel.in_trio_run()))
            in_host(lambda: check(not trio.lowlevel.in_trio_task()))

    trivial_guest_run(trio_main)
    assert not trio.lowlevel.in_trio_run()
    assert not trio.lowlevel.in_trio_task()


def test_warn_set_wakeup_fd_overwrite() -> None:
    assert signal.set_wakeup_fd(-1) == -1

    async def trio_main(in_host: InHost) -> str:
        return "ok"

    a, b = socket.socketpair()
    with a, b:
        a.setblocking(False)

        # Warn if there's already a wakeup fd
        signal.set_wakeup_fd(a.fileno())
        try:
            with pytest.warns(RuntimeWarning, match="signal handling code.*collided"):
                assert trivial_guest_run(trio_main) == "ok"
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()

        signal.set_wakeup_fd(a.fileno())
        try:
            with pytest.warns(RuntimeWarning, match="signal handling code.*collided"):
                assert (
                    trivial_guest_run(trio_main, host_uses_signal_set_wakeup_fd=False)
                    == "ok"
                )
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()

        # Don't warn if there isn't already a wakeup fd
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert trivial_guest_run(trio_main) == "ok"

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert (
                trivial_guest_run(trio_main, host_uses_signal_set_wakeup_fd=True)
                == "ok"
            )

        # If there's already a wakeup fd, but we've been told to trust it,
        # then it's left alone and there's no warning
        signal.set_wakeup_fd(a.fileno())
        try:

            async def trio_check_wakeup_fd_unaltered(in_host: InHost) -> str:
                fd = signal.set_wakeup_fd(-1)
                assert fd == a.fileno()
                signal.set_wakeup_fd(fd)
                return "ok"

            with warnings.catch_warnings():
                warnings.simplefilter("error")
                assert (
                    trivial_guest_run(
                        trio_check_wakeup_fd_unaltered,
                        host_uses_signal_set_wakeup_fd=True,
                    )
                    == "ok"
                )
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()


def test_host_wakeup_doesnt_trigger_wait_all_tasks_blocked() -> None:
    # This is designed to hit the branch in unrolled_run where:
    #   idle_primed=True
    #   runner.runq is empty
    #   events is Truth-y
    # ...and confirm that in this case, wait_all_tasks_blocked does not get
    # triggered.
    def set_deadline(cscope: trio.CancelScope, new_deadline: float) -> None:
        print(f"setting deadline {new_deadline}")
        cscope.deadline = new_deadline

    async def trio_main(in_host: InHost) -> str:
        async def sit_in_wait_all_tasks_blocked(watb_cscope: trio.CancelScope) -> None:
            with watb_cscope:
                # Overall point of this test is that this
                # wait_all_tasks_blocked should *not* return normally, but
                # only by cancellation.
                await trio.testing.wait_all_tasks_blocked(cushion=9999)
                raise AssertionError(  # pragma: no cover
                    "wait_all_tasks_blocked should *not* return normally, "
                    "only by cancellation.",
                )
            assert watb_cscope.cancelled_caught

        async def get_woken_by_host_deadline(watb_cscope: trio.CancelScope) -> None:
            with trio.CancelScope() as cscope:
                print("scheduling stuff to happen")

                # Altering the deadline from the host, to something in the
                # future, will cause the run loop to wake up, but then
                # discover that there is nothing to do and go back to sleep.
                # This should *not* trigger wait_all_tasks_blocked.
                #
                # So the 'before_io_wait' here will wait until we're blocking
                # with the wait_all_tasks_blocked primed, and then schedule a
                # deadline change. The critical test is that this should *not*
                # wake up 'sit_in_wait_all_tasks_blocked'.
                #
                # The after we've had a chance to wake up
                # 'sit_in_wait_all_tasks_blocked', we want the test to
                # actually end. So in after_io_wait we schedule a second host
                # call to tear things down.
                class InstrumentHelper(Instrument):
                    def __init__(self) -> None:
                        self.primed = False

                    def before_io_wait(self, timeout: float) -> None:
                        print(f"before_io_wait({timeout})")
                        if timeout == 9999:  # pragma: no branch
                            assert not self.primed
                            in_host(lambda: set_deadline(cscope, 1e9))
                            self.primed = True

                    def after_io_wait(self, timeout: float) -> None:
                        if self.primed:  # pragma: no branch
                            print("instrument triggered")
                            in_host(lambda: cscope.cancel())
                            trio.lowlevel.remove_instrument(self)

                trio.lowlevel.add_instrument(InstrumentHelper())
                await trio.sleep_forever()
            assert cscope.cancelled_caught
            watb_cscope.cancel()

        async with trio.open_nursery() as nursery:
            watb_cscope = trio.CancelScope()
            nursery.start_soon(sit_in_wait_all_tasks_blocked, watb_cscope)
            await trio.testing.wait_all_tasks_blocked()
            nursery.start_soon(get_woken_by_host_deadline, watb_cscope)

        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


@restore_unraisablehook()
def test_guest_warns_if_abandoned() -> None:
    # This warning is emitted from the garbage collector. So we have to make
    # sure that our abandoned run is garbage. The easiest way to do this is to
    # put it into a function, so that we're sure all the local state,
    # traceback frames, etc. are garbage once it returns.
    def do_abandoned_guest_run() -> None:
        async def abandoned_main(in_host: InHost) -> None:
            in_host(lambda: 1 / 0)
            while True:
                await trio.lowlevel.checkpoint()

        with pytest.raises(ZeroDivisionError):
            trivial_guest_run(abandoned_main)

    with pytest.warns(  # noqa: PT031
        RuntimeWarning,
        match="Trio guest run got abandoned",
    ):
        do_abandoned_guest_run()
        gc_collect_harder()

    # If you have problems some day figuring out what's holding onto a
    # reference to the unrolled_run generator and making this test fail,
    # then this might be useful to help track it down. (It assumes you
    # also hack start_guest_run so that it does 'global W; W =
    # weakref(unrolled_run_gen)'.)
    #
    # import gc
    # print(trio._core._run.W)
    # targets = [trio._core._run.W()]
    # for i in range(15):
    #     new_targets = []
    #     for target in targets:
    #         new_targets += gc.get_referrers(target)
    #         new_targets.remove(targets)
    #     print("#####################")
    #     print(f"depth {i}: {len(new_targets)}")
    #     print(new_targets)
    #     targets = new_targets

    with pytest.raises(RuntimeError):
        trio.current_time()


def aiotrio_run(
    trio_fn: Callable[[], Awaitable[T]],
    *,
    pass_not_threadsafe: bool = True,
    run_sync_soon_not_threadsafe: InHost | None = None,
    host_uses_signal_set_wakeup_fd: bool = False,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> T:
    loop = asyncio.new_event_loop()

    async def aio_main() -> T:
        nonlocal run_sync_soon_not_threadsafe
        trio_done_fut: asyncio.Future[Outcome[T]] = loop.create_future()

        def trio_done_callback(main_outcome: Outcome[T]) -> None:
            print(f"trio_fn finished: {main_outcome!r}")
            trio_done_fut.set_result(main_outcome)

        if pass_not_threadsafe:
            run_sync_soon_not_threadsafe = cast("InHost", loop.call_soon)

        trio.lowlevel.start_guest_run(
            trio_fn,
            run_sync_soon_threadsafe=loop.call_soon_threadsafe,
            done_callback=trio_done_callback,
            run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
            host_uses_signal_set_wakeup_fd=host_uses_signal_set_wakeup_fd,
            clock=clock,
            instruments=instruments,
            restrict_keyboard_interrupt_to_checkpoints=restrict_keyboard_interrupt_to_checkpoints,
            strict_exception_groups=strict_exception_groups,
        )

        return (await trio_done_fut).unwrap()

    try:
        # can't use asyncio.run because that fails on Windows (3.8, x64, with
        # Komodia LSP) and segfaults on Windows (3.9, x64, with Komodia LSP)
        return loop.run_until_complete(aio_main())
    finally:
        loop.close()


def test_guest_mode_on_asyncio() -> None:
    async def trio_main() -> str:
        print("trio_main!")

        to_trio, from_aio = trio.open_memory_channel[int](float("inf"))
        from_trio: asyncio.Queue[int] = asyncio.Queue()

        aio_task = asyncio.ensure_future(aio_pingpong(from_trio, to_trio))

        # Make sure we have at least one tick where we don't need to go into
        # the thread
        await trio.lowlevel.checkpoint()

        from_trio.put_nowait(0)

        async for n in from_aio:
            print(f"trio got: {n}")
            from_trio.put_nowait(n + 1)
            if n >= 10:
                aio_task.cancel()
                return "trio-main-done"

        raise AssertionError("should never be reached")  # pragma: no cover

    async def aio_pingpong(
        from_trio: asyncio.Queue[int],
        to_trio: MemorySendChannel[int],
    ) -> None:
        print("aio_pingpong!")

        try:
            while True:
                n = await from_trio.get()
                print(f"aio got: {n}")
                to_trio.send_nowait(n + 1)
        except asyncio.CancelledError:
            raise
        except:  # pragma: no cover
            traceback.print_exc()
            raise

    assert (
        aiotrio_run(
            trio_main,
            # Not all versions of asyncio we test on can actually be trusted,
            # but this test doesn't care about signal handling, and it's
            # easier to just avoid the warnings.
            host_uses_signal_set_wakeup_fd=True,
        )
        == "trio-main-done"
    )

    assert (
        aiotrio_run(
            trio_main,
            # Also check that passing only call_soon_threadsafe works, via the
            # fallback path where we use it for everything.
            pass_not_threadsafe=False,
            host_uses_signal_set_wakeup_fd=True,
        )
        == "trio-main-done"
    )


def test_guest_mode_internal_errors(
    monkeypatch: pytest.MonkeyPatch,
    recwarn: pytest.WarningsRecorder,
) -> None:
    with monkeypatch.context() as m:

        async def crash_in_run_loop(in_host: InHost) -> None:
            m.setattr("trio._core._run.GLOBAL_RUN_CONTEXT.runner.runq", "HI")
            await trio.sleep(1)

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_run_loop)

    with monkeypatch.context() as m:

        async def crash_in_io(in_host: InHost) -> None:
            m.setattr("trio._core._run.TheIOManager.get_events", None)
            await trio.lowlevel.checkpoint()

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_io)

    with monkeypatch.context() as m:

        async def crash_in_worker_thread_io(in_host: InHost) -> None:
            t = threading.current_thread()
            old_get_events = trio._core._run.TheIOManager.get_events

            def bad_get_events(
                self: trio._core._run.TheIOManager,
                timeout: float,
            ) -> trio._core._run.EventResult:
                if threading.current_thread() is not t:
                    raise ValueError("oh no!")
                else:
                    return old_get_events(self, timeout)

            m.setattr("trio._core._run.TheIOManager.get_events", bad_get_events)

            await trio.sleep(1)

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_worker_thread_io)

    gc_collect_harder()


def test_guest_mode_ki() -> None:
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler

    # Check SIGINT in Trio func and in host func
    async def trio_main(in_host: InHost) -> None:
        with pytest.raises(KeyboardInterrupt):
            signal.raise_signal(signal.SIGINT)

        # Host SIGINT should get injected into Trio
        in_host(partial(signal.raise_signal, signal.SIGINT))
        await trio.sleep(10)

    with pytest.raises(KeyboardInterrupt) as excinfo:
        trivial_guest_run(trio_main)
    assert excinfo.value.__context__ is None
    # Signal handler should be restored properly on exit
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler

    # Also check chaining in the case where KI is injected after main exits
    final_exc = KeyError("whoa")

    async def trio_main_raising(in_host: InHost) -> NoReturn:
        in_host(partial(signal.raise_signal, signal.SIGINT))
        raise final_exc

    with pytest.raises(KeyboardInterrupt) as excinfo:
        trivial_guest_run(trio_main_raising)
    assert excinfo.value.__context__ is final_exc

    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_guest_mode_autojump_clock_threshold_changing() -> None:
    # This is super obscure and probably no-one will ever notice, but
    # technically mutating the MockClock.autojump_threshold from the host
    # should wake up the guest, so let's test it.

    clock = trio.testing.MockClock()

    DURATION = 120

    async def trio_main(in_host: InHost) -> None:
        assert trio.current_time() == 0
        in_host(lambda: setattr(clock, "autojump_threshold", 0))
        await trio.sleep(DURATION)
        assert trio.current_time() == DURATION

    start = time.monotonic()
    trivial_guest_run(trio_main, clock=clock)
    end = time.monotonic()
    # Should be basically instantaneous, but we'll leave a generous buffer to
    # account for any CI weirdness
    assert end - start < DURATION / 2


@restore_unraisablehook()
def test_guest_mode_asyncgens() -> None:
    record = set()

    async def agen(label: str) -> AsyncGenerator[int, None]:
        assert sniffio.current_async_library() == label
        try:
            yield 1
        finally:
            library = sniffio.current_async_library()
            with contextlib.suppress(trio.Cancelled):
                await sys.modules[library].sleep(0)
            record.add((label, library))

    async def iterate_in_aio() -> None:
        await agen("asyncio").asend(None)

    async def trio_main() -> None:
        task = asyncio.ensure_future(iterate_in_aio())
        done_evt = trio.Event()
        task.add_done_callback(lambda _: done_evt.set())
        with trio.fail_after(1):
            await done_evt.wait()

        await agen("trio").asend(None)

        gc_collect_harder()

    aiotrio_run(trio_main, host_uses_signal_set_wakeup_fd=True)

    assert record == {("asyncio", "asyncio"), ("trio", "trio")}


@restore_unraisablehook()
def test_guest_mode_asyncgens_garbage_collection() -> None:
    record: set[tuple[str, str, bool]] = set()

    async def agen(label: str) -> AsyncGenerator[int, None]:
        class A:
            pass

        a = A()
        a_wr = weakref.ref(a)
        assert sniffio.current_async_library() == label
        try:
            yield 1
        finally:
            library = sniffio.current_async_library()
            with contextlib.suppress(trio.Cancelled):
                await sys.modules[library].sleep(0)

            del a
            if sys.implementation.name == "pypy":
                gc_collect_harder()

            record.add((label, library, a_wr() is None))

    async def iterate_in_aio() -> None:
        await agen("asyncio").asend(None)

    async def trio_main() -> None:
        task = asyncio.ensure_future(iterate_in_aio())
        done_evt = trio.Event()
        task.add_done_callback(lambda _: done_evt.set())
        with trio.fail_after(1):
            await done_evt.wait()

        await agen("trio").asend(None)

        gc_collect_harder()

    aiotrio_run(trio_main, host_uses_signal_set_wakeup_fd=True)

    assert record == {("asyncio", "asyncio", True), ("trio", "trio", True)}

# === NexusCore/openenv\Lib\site-packages\ipykernel\kernelapp.py ===
"""An Application for launching a kernel"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import atexit
import errno
import logging
import os
import signal
import sys
import traceback
import typing as t
from functools import partial
from io import FileIO, TextIOWrapper
from logging import StreamHandler
from pathlib import Path

import zmq
from IPython.core.application import (  # type:ignore[attr-defined]
    BaseIPythonApplication,
    base_aliases,
    base_flags,
    catch_config_error,
)
from IPython.core.profiledir import ProfileDir
from IPython.core.shellapp import InteractiveShellApp, shell_aliases, shell_flags
from jupyter_client.connect import ConnectionFileMixin
from jupyter_client.session import Session, session_aliases, session_flags
from jupyter_core.paths import jupyter_runtime_dir
from tornado import ioloop
from traitlets.traitlets import (
    Any,
    Bool,
    Dict,
    DottedObjectName,
    Instance,
    Integer,
    Type,
    Unicode,
    default,
)
from traitlets.utils import filefind
from traitlets.utils.importstring import import_item
from zmq.eventloop.zmqstream import ZMQStream

from .connect import get_connection_info, write_connection_file

# local imports
from .control import ControlThread
from .heartbeat import Heartbeat
from .iostream import IOPubThread
from .ipkernel import IPythonKernel
from .parentpoller import ParentPollerUnix, ParentPollerWindows
from .zmqshell import ZMQInteractiveShell

# -----------------------------------------------------------------------------
# Flags and Aliases
# -----------------------------------------------------------------------------

kernel_aliases = dict(base_aliases)
kernel_aliases.update(
    {
        "ip": "IPKernelApp.ip",
        "hb": "IPKernelApp.hb_port",
        "shell": "IPKernelApp.shell_port",
        "iopub": "IPKernelApp.iopub_port",
        "stdin": "IPKernelApp.stdin_port",
        "control": "IPKernelApp.control_port",
        "f": "IPKernelApp.connection_file",
        "transport": "IPKernelApp.transport",
    }
)

kernel_flags = dict(base_flags)
kernel_flags.update(
    {
        "no-stdout": ({"IPKernelApp": {"no_stdout": True}}, "redirect stdout to the null device"),
        "no-stderr": ({"IPKernelApp": {"no_stderr": True}}, "redirect stderr to the null device"),
        "pylab": (
            {"IPKernelApp": {"pylab": "auto"}},
            """Pre-load matplotlib and numpy for interactive use with
        the default matplotlib backend.""",
        ),
        "trio-loop": (
            {"InteractiveShell": {"trio_loop": False}},
            "Enable Trio as main event loop.",
        ),
    }
)

# inherit flags&aliases for any IPython shell apps
kernel_aliases.update(shell_aliases)
kernel_flags.update(shell_flags)

# inherit flags&aliases for Sessions
kernel_aliases.update(session_aliases)
kernel_flags.update(session_flags)

_ctrl_c_message = """\
NOTE: When using the `ipython kernel` entry point, Ctrl-C will not work.

To exit, you will have to explicitly quit this process, by either sending
"quit" from a client, or using Ctrl-\\ in UNIX-like environments.

To read more about this, see https://github.com/ipython/ipython/issues/2049

"""

# -----------------------------------------------------------------------------
# Application class for starting an IPython Kernel
# -----------------------------------------------------------------------------


class IPKernelApp(BaseIPythonApplication, InteractiveShellApp, ConnectionFileMixin):
    """The IPYKernel application class."""

    name = "ipython-kernel"
    aliases = Dict(kernel_aliases)  # type:ignore[assignment]
    flags = Dict(kernel_flags)  # type:ignore[assignment]
    classes = [IPythonKernel, ZMQInteractiveShell, ProfileDir, Session]
    # the kernel class, as an importstring
    kernel_class = Type(
        "ipykernel.ipkernel.IPythonKernel",
        klass="ipykernel.kernelbase.Kernel",
        help="""The Kernel subclass to be used.

    This should allow easy reuse of the IPKernelApp entry point
    to configure and launch kernels other than IPython's own.
    """,
    ).tag(config=True)
    kernel = Any()
    poller = Any()  # don't restrict this even though current pollers are all Threads
    heartbeat = Instance(Heartbeat, allow_none=True)

    context: zmq.Context[t.Any] | None = Any()  # type:ignore[assignment]
    shell_socket = Any()
    control_socket = Any()
    debugpy_socket = Any()
    debug_shell_socket = Any()
    stdin_socket = Any()
    iopub_socket = Any()
    iopub_thread = Any()
    control_thread = Any()

    _ports = Dict()

    subcommands = {
        "install": (
            "ipykernel.kernelspec.InstallIPythonKernelSpecApp",
            "Install the IPython kernel",
        ),
    }

    # connection info:
    connection_dir = Unicode()

    @default("connection_dir")
    def _default_connection_dir(self):
        return jupyter_runtime_dir()

    @property
    def abs_connection_file(self):
        if Path(self.connection_file).name == self.connection_file and self.connection_dir:
            return str(Path(str(self.connection_dir)) / self.connection_file)
        return self.connection_file

    # streams, etc.
    no_stdout = Bool(False, help="redirect stdout to the null device").tag(config=True)
    no_stderr = Bool(False, help="redirect stderr to the null device").tag(config=True)
    trio_loop = Bool(False, help="Set main event loop.").tag(config=True)
    quiet = Bool(True, help="Only send stdout/stderr to output stream").tag(config=True)
    outstream_class = DottedObjectName(
        "ipykernel.iostream.OutStream",
        help="The importstring for the OutStream factory",
        allow_none=True,
    ).tag(config=True)
    displayhook_class = DottedObjectName(
        "ipykernel.displayhook.ZMQDisplayHook", help="The importstring for the DisplayHook factory"
    ).tag(config=True)

    capture_fd_output = Bool(
        True,
        help="""Attempt to capture and forward low-level output, e.g. produced by Extension libraries.
    """,
    ).tag(config=True)

    # polling
    parent_handle = Integer(
        int(os.environ.get("JPY_PARENT_PID") or 0),
        help="""kill this process if its parent dies.  On Windows, the argument
        specifies the HANDLE of the parent process, otherwise it is simply boolean.
        """,
    ).tag(config=True)
    interrupt = Integer(
        int(os.environ.get("JPY_INTERRUPT_EVENT") or 0),
        help="""ONLY USED ON WINDOWS
        Interrupt this process when the parent is signaled.
        """,
    ).tag(config=True)

    def init_crash_handler(self):
        """Initialize the crash handler."""
        sys.excepthook = self.excepthook

    def excepthook(self, etype, evalue, tb):
        """Handle an exception."""
        # write uncaught traceback to 'real' stderr, not zmq-forwarder
        traceback.print_exception(etype, evalue, tb, file=sys.__stderr__)

    def init_poller(self):
        """Initialize the poller."""
        if sys.platform == "win32":
            if self.interrupt or self.parent_handle:
                self.poller = ParentPollerWindows(self.interrupt, self.parent_handle)
        elif self.parent_handle and self.parent_handle != 1:
            # PID 1 (init) is special and will never go away,
            # only be reassigned.
            # Parent polling doesn't work if ppid == 1 to start with.
            self.poller = ParentPollerUnix()

    def _try_bind_socket(self, s, port):
        iface = f"{self.transport}://{self.ip}"
        if self.transport == "tcp":
            if port <= 0:
                port = s.bind_to_random_port(iface)
            else:
                s.bind("tcp://%s:%i" % (self.ip, port))
        elif self.transport == "ipc":
            if port <= 0:
                port = 1
                path = "%s-%i" % (self.ip, port)
                while Path(path).exists():
                    port = port + 1
                    path = "%s-%i" % (self.ip, port)
            else:
                path = "%s-%i" % (self.ip, port)
            s.bind("ipc://%s" % path)
        return port

    def _bind_socket(self, s, port):
        try:
            win_in_use = errno.WSAEADDRINUSE  # type:ignore[attr-defined]
        except AttributeError:
            win_in_use = None

        # Try up to 100 times to bind a port when in conflict to avoid
        # infinite attempts in bad setups
        max_attempts = 1 if port else 100
        for attempt in range(max_attempts):
            try:
                return self._try_bind_socket(s, port)
            except zmq.ZMQError as ze:
                # Raise if we have any error not related to socket binding
                if ze.errno != errno.EADDRINUSE and ze.errno != win_in_use:
                    raise
                if attempt == max_attempts - 1:
                    raise
        return None

    def write_connection_file(self):
        """write connection info to JSON file"""
        cf = self.abs_connection_file
        connection_info = dict(
            ip=self.ip,
            key=self.session.key,
            transport=self.transport,
            shell_port=self.shell_port,
            stdin_port=self.stdin_port,
            hb_port=self.hb_port,
            iopub_port=self.iopub_port,
            control_port=self.control_port,
        )
        if Path(cf).exists():
            # If the file exists, merge our info into it. For example, if the
            # original file had port number 0, we update with the actual port
            # used.
            existing_connection_info = get_connection_info(cf, unpack=True)
            assert isinstance(existing_connection_info, dict)
            connection_info = dict(existing_connection_info, **connection_info)
            if connection_info == existing_connection_info:
                self.log.debug("Connection file %s with current information already exists", cf)
                return

        self.log.debug("Writing connection file: %s", cf)

        write_connection_file(cf, **connection_info)

    def cleanup_connection_file(self):
        """Clean up our connection file."""
        cf = self.abs_connection_file
        self.log.debug("Cleaning up connection file: %s", cf)
        try:
            Path(cf).unlink()
        except OSError:
            pass

        self.cleanup_ipc_files()

    def init_connection_file(self):
        """Initialize our connection file."""
        if not self.connection_file:
            self.connection_file = "kernel-%s.json" % os.getpid()
        try:
            self.connection_file = filefind(self.connection_file, [".", self.connection_dir])
        except OSError:
            self.log.debug("Connection file not found: %s", self.connection_file)
            # This means I own it, and I'll create it in this directory:
            Path(self.abs_connection_file).parent.mkdir(mode=0o700, exist_ok=True, parents=True)
            # Also, I will clean it up:
            atexit.register(self.cleanup_connection_file)
            return
        try:
            self.load_connection_file()
        except Exception:
            self.log.error(  # noqa: G201
                "Failed to load connection file: %r", self.connection_file, exc_info=True
            )
            self.exit(1)

    def init_sockets(self):
        """Create a context, a session, and the kernel sockets."""
        self.log.info("Starting the kernel at pid: %i", os.getpid())
        assert self.context is None, "init_sockets cannot be called twice!"
        self.context = context = zmq.Context()
        atexit.register(self.close)

        self.shell_socket = context.socket(zmq.ROUTER)
        self.shell_socket.linger = 1000
        self.shell_port = self._bind_socket(self.shell_socket, self.shell_port)
        self.log.debug("shell ROUTER Channel on port: %i" % self.shell_port)

        self.stdin_socket = context.socket(zmq.ROUTER)
        self.stdin_socket.linger = 1000
        self.stdin_port = self._bind_socket(self.stdin_socket, self.stdin_port)
        self.log.debug("stdin ROUTER Channel on port: %i" % self.stdin_port)

        if hasattr(zmq, "ROUTER_HANDOVER"):
            # set router-handover to workaround zeromq reconnect problems
            # in certain rare circumstances
            # see ipython/ipykernel#270 and zeromq/libzmq#2892
            self.shell_socket.router_handover = self.stdin_socket.router_handover = 1

        self.init_control(context)
        self.init_iopub(context)

    def init_control(self, context):
        """Initialize the control channel."""
        self.control_socket = context.socket(zmq.ROUTER)
        self.control_socket.linger = 1000
        self.control_port = self._bind_socket(self.control_socket, self.control_port)
        self.log.debug("control ROUTER Channel on port: %i" % self.control_port)

        self.debugpy_socket = context.socket(zmq.STREAM)
        self.debugpy_socket.linger = 1000

        self.debug_shell_socket = context.socket(zmq.DEALER)
        self.debug_shell_socket.linger = 1000
        if self.shell_socket.getsockopt(zmq.LAST_ENDPOINT):
            self.debug_shell_socket.connect(self.shell_socket.getsockopt(zmq.LAST_ENDPOINT))

        if hasattr(zmq, "ROUTER_HANDOVER"):
            # set router-handover to workaround zeromq reconnect problems
            # in certain rare circumstances
            # see ipython/ipykernel#270 and zeromq/libzmq#2892
            self.control_socket.router_handover = 1

        self.control_thread = ControlThread(daemon=True)

    def init_iopub(self, context):
        """Initialize the iopub channel."""
        self.iopub_socket = context.socket(zmq.PUB)
        self.iopub_socket.linger = 1000
        self.iopub_port = self._bind_socket(self.iopub_socket, self.iopub_port)
        self.log.debug("iopub PUB Channel on port: %i" % self.iopub_port)
        self.configure_tornado_logger()
        self.iopub_thread = IOPubThread(self.iopub_socket, pipe=True)
        self.iopub_thread.start()
        # backward-compat: wrap iopub socket API in background thread
        self.iopub_socket = self.iopub_thread.background_socket

    def init_heartbeat(self):
        """start the heart beating"""
        # heartbeat doesn't share context, because it mustn't be blocked
        # by the GIL, which is accessed by libzmq when freeing zero-copy messages
        hb_ctx = zmq.Context()
        self.heartbeat = Heartbeat(hb_ctx, (self.transport, self.ip, self.hb_port))
        self.hb_port = self.heartbeat.port
        self.log.debug("Heartbeat REP Channel on port: %i" % self.hb_port)
        self.heartbeat.start()

    def close(self):
        """Close zmq sockets in an orderly fashion"""
        # un-capture IO before we start closing channels
        self.reset_io()
        self.log.info("Cleaning up sockets")
        if self.heartbeat:
            self.log.debug("Closing heartbeat channel")
            self.heartbeat.context.term()
        if self.iopub_thread:
            self.log.debug("Closing iopub channel")
            self.iopub_thread.stop()
            self.iopub_thread.close()
        if self.control_thread and self.control_thread.is_alive():
            self.log.debug("Closing control thread")
            self.control_thread.stop()
            self.control_thread.join()

        if self.debugpy_socket and not self.debugpy_socket.closed:
            self.debugpy_socket.close()
        if self.debug_shell_socket and not self.debug_shell_socket.closed:
            self.debug_shell_socket.close()

        for channel in ("shell", "control", "stdin"):
            self.log.debug("Closing %s channel", channel)
            socket = getattr(self, channel + "_socket", None)
            if socket and not socket.closed:
                socket.close()
        self.log.debug("Terminating zmq context")
        if self.context:
            self.context.term()
        self.log.debug("Terminated zmq context")

    def log_connection_info(self):
        """display connection info, and store ports"""
        basename = Path(self.connection_file).name
        if (
            basename == self.connection_file
            or str(Path(self.connection_file).parent) == self.connection_dir
        ):
            # use shortname
            tail = basename
        else:
            tail = self.connection_file
        lines = [
            "To connect another client to this kernel, use:",
            "    --existing %s" % tail,
        ]
        # log connection info
        # info-level, so often not shown.
        # frontends should use the %connect_info magic
        # to see the connection info
        for line in lines:
            self.log.info(line)
        # also raw print to the terminal if no parent_handle (`ipython kernel`)
        # unless log-level is CRITICAL (--quiet)
        if not self.parent_handle and int(self.log_level) < logging.CRITICAL:  # type:ignore[call-overload]
            print(_ctrl_c_message, file=sys.__stdout__)
            for line in lines:
                print(line, file=sys.__stdout__)

        self._ports = dict(
            shell=self.shell_port,
            iopub=self.iopub_port,
            stdin=self.stdin_port,
            hb=self.hb_port,
            control=self.control_port,
        )

    def init_blackhole(self):
        """redirects stdout/stderr to devnull if necessary"""
        if self.no_stdout or self.no_stderr:
            blackhole = open(os.devnull, "w")  # noqa: SIM115
            if self.no_stdout:
                sys.stdout = sys.__stdout__ = blackhole  # type:ignore[misc]
            if self.no_stderr:
                sys.stderr = sys.__stderr__ = blackhole  # type:ignore[misc]

    def init_io(self):
        """Redirect input streams and set a display hook."""
        if self.outstream_class:
            outstream_factory = import_item(str(self.outstream_class))
            if sys.stdout is not None:
                sys.stdout.flush()

            e_stdout = None if self.quiet else sys.__stdout__
            e_stderr = None if self.quiet else sys.__stderr__

            if not self.capture_fd_output:
                outstream_factory = partial(outstream_factory, watchfd=False)

            sys.stdout = outstream_factory(self.session, self.iopub_thread, "stdout", echo=e_stdout)
            if sys.stderr is not None:
                sys.stderr.flush()
            sys.stderr = outstream_factory(self.session, self.iopub_thread, "stderr", echo=e_stderr)
            if hasattr(sys.stderr, "_original_stdstream_copy"):
                for handler in self.log.handlers:
                    if isinstance(handler, StreamHandler) and (handler.stream.buffer.fileno() == 2):
                        self.log.debug("Seeing logger to stderr, rerouting to raw filedescriptor.")

                        handler.stream = TextIOWrapper(
                            FileIO(
                                sys.stderr._original_stdstream_copy,
                                "w",
                            )
                        )
        if self.displayhook_class:
            displayhook_factory = import_item(str(self.displayhook_class))
            self.displayhook = displayhook_factory(self.session, self.iopub_socket)
            sys.displayhook = self.displayhook

        self.patch_io()

    def reset_io(self):
        """restore original io

        restores state after init_io
        """
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        sys.displayhook = sys.__displayhook__

    def patch_io(self):
        """Patch important libraries that can't handle sys.stdout forwarding"""
        try:
            import faulthandler
        except ImportError:
            pass
        else:
            # Warning: this is a monkeypatch of `faulthandler.enable`, watch for possible
            # updates to the upstream API and update accordingly (up-to-date as of Python 3.5):
            # https://docs.python.org/3/library/faulthandler.html#faulthandler.enable

            # change default file to __stderr__ from forwarded stderr
            faulthandler_enable = faulthandler.enable

            def enable(file=sys.__stderr__, all_threads=True, **kwargs):
                return faulthandler_enable(file=file, all_threads=all_threads, **kwargs)

            faulthandler.enable = enable

            if hasattr(faulthandler, "register"):
                faulthandler_register = faulthandler.register

                def register(signum, file=sys.__stderr__, all_threads=True, chain=False, **kwargs):
                    return faulthandler_register(
                        signum, file=file, all_threads=all_threads, chain=chain, **kwargs
                    )

                faulthandler.register = register

    def init_signal(self):
        """Initialize the signal handler."""
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def init_kernel(self):
        """Create the Kernel object itself"""
        shell_stream = ZMQStream(self.shell_socket)
        control_stream = ZMQStream(self.control_socket, self.control_thread.io_loop)
        debugpy_stream = ZMQStream(self.debugpy_socket, self.control_thread.io_loop)
        self.control_thread.start()
        kernel_factory = self.kernel_class.instance  # type:ignore[attr-defined]

        kernel = kernel_factory(
            parent=self,
            session=self.session,
            control_stream=control_stream,
            debugpy_stream=debugpy_stream,
            debug_shell_socket=self.debug_shell_socket,
            shell_stream=shell_stream,
            control_thread=self.control_thread,
            iopub_thread=self.iopub_thread,
            iopub_socket=self.iopub_socket,
            stdin_socket=self.stdin_socket,
            log=self.log,
            profile_dir=self.profile_dir,
            user_ns=self.user_ns,
        )
        kernel.record_ports({name + "_port": port for name, port in self._ports.items()})
        self.kernel = kernel

        # Allow the displayhook to get the execution count
        self.displayhook.get_execution_count = lambda: kernel.execution_count

    def init_gui_pylab(self):
        """Enable GUI event loop integration, taking pylab into account."""

        # Register inline backend as default
        # this is higher priority than matplotlibrc,
        # but lower priority than anything else (mpl.use() for instance).
        # This only affects matplotlib >= 1.5
        if not os.environ.get("MPLBACKEND"):
            os.environ["MPLBACKEND"] = "module://matplotlib_inline.backend_inline"

        # Provide a wrapper for :meth:`InteractiveShellApp.init_gui_pylab`
        # to ensure that any exception is printed straight to stderr.
        # Normally _showtraceback associates the reply with an execution,
        # which means frontends will never draw it, as this exception
        # is not associated with any execute request.

        shell = self.shell
        assert shell is not None
        _showtraceback = shell._showtraceback
        try:
            # replace error-sending traceback with stderr
            def print_tb(etype, evalue, stb):
                print("GUI event loop or pylab initialization failed", file=sys.stderr)
                assert shell is not None
                print(shell.InteractiveTB.stb2text(stb), file=sys.stderr)

            shell._showtraceback = print_tb
            InteractiveShellApp.init_gui_pylab(self)
        finally:
            shell._showtraceback = _showtraceback

    def init_shell(self):
        """Initialize the shell channel."""
        self.shell = getattr(self.kernel, "shell", None)
        if self.shell:
            self.shell.configurables.append(self)

    def configure_tornado_logger(self):
        """Configure the tornado logging.Logger.

        Must set up the tornado logger or else tornado will call
        basicConfig for the root logger which makes the root logger
        go to the real sys.stderr instead of the capture streams.
        This function mimics the setup of logging.basicConfig.
        """
        logger = logging.getLogger("tornado")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(logging.BASIC_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _init_asyncio_patch(self):
        """set default asyncio policy to be compatible with tornado

        Tornado 6 (at least) is not compatible with the default
        asyncio implementation on Windows

        Pick the older SelectorEventLoopPolicy on Windows
        if the known-incompatible default policy is in use.

        Support for Proactor via a background thread is available in tornado 6.1,
        but it is still preferable to run the Selector in the main thread
        instead of the background.

        do this as early as possible to make it a low priority and overridable

        ref: https://github.com/tornadoweb/tornado/issues/2608

        FIXME: if/when tornado supports the defaults in asyncio without threads,
               remove and bump tornado requirement for py38.
               Most likely, this will mean a new Python version
               where asyncio.ProactorEventLoop supports add_reader and friends.

        """
        if sys.platform.startswith("win") and sys.version_info >= (3, 8):
            import asyncio

            try:
                from asyncio import WindowsProactorEventLoopPolicy, WindowsSelectorEventLoopPolicy
            except ImportError:
                pass
                # not affected
            else:
                if type(asyncio.get_event_loop_policy()) is WindowsProactorEventLoopPolicy:
                    # WindowsProactorEventLoopPolicy is not compatible with tornado 6
                    # fallback to the pre-3.8 default of Selector
                    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    def init_pdb(self):
        """Replace pdb with IPython's version that is interruptible.

        With the non-interruptible version, stopping pdb() locks up the kernel in a
        non-recoverable state.
        """
        import pdb

        from IPython.core import debugger

        if hasattr(debugger, "InterruptiblePdb"):
            # Only available in newer IPython releases:
            debugger.Pdb = debugger.InterruptiblePdb  # type:ignore[misc]
            pdb.Pdb = debugger.Pdb  # type:ignore[assignment,misc]
            pdb.set_trace = debugger.set_trace

    @catch_config_error
    def initialize(self, argv=None):
        """Initialize the application."""
        self._init_asyncio_patch()
        super().initialize(argv)
        if self.subapp is not None:
            return

        self.init_pdb()
        self.init_blackhole()
        self.init_connection_file()
        self.init_poller()
        self.init_sockets()
        self.init_heartbeat()
        # writing/displaying connection info must be *after* init_sockets/heartbeat
        self.write_connection_file()
        # Log connection info after writing connection file, so that the connection
        # file is definitely available at the time someone reads the log.
        self.log_connection_info()
        self.init_io()
        try:
            self.init_signal()
        except Exception:
            # Catch exception when initializing signal fails, eg when running the
            # kernel on a separate thread
            if int(self.log_level) < logging.CRITICAL:  # type:ignore[call-overload]
                self.log.error("Unable to initialize signal:", exc_info=True)  # noqa: G201
        self.init_kernel()
        # shell init steps
        self.init_path()
        self.init_shell()
        if self.shell:
            self.init_gui_pylab()
            self.init_extensions()
            self.init_code()
        # flush stdout/stderr, so that anything written to these streams during
        # initialization do not get associated with the first execution request
        sys.stdout.flush()
        sys.stderr.flush()

    def start(self):
        """Start the application."""
        if self.subapp is not None:
            return self.subapp.start()
        if self.poller is not None:
            self.poller.start()
        self.kernel.start()
        self.io_loop = ioloop.IOLoop.current()
        if self.trio_loop:
            from ipykernel.trio_runner import TrioRunner

            tr = TrioRunner()
            tr.initialize(self.kernel, self.io_loop)
            try:
                tr.run()
            except KeyboardInterrupt:
                pass
        else:
            try:
                self.io_loop.start()
            except KeyboardInterrupt:
                pass


launch_new_instance = IPKernelApp.launch_instance


def main():  # pragma: no cover
    """Run an IPKernel as an application"""
    app = IPKernelApp.instance()
    app.initialize()
    app.start()


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\nltk\tag\sequential.py ===
# Natural Language Toolkit: Sequential Backoff Taggers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
#         Tiago Tresoldi <tresoldi@users.sf.net> (original affix tagger)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes for tagging sentences sequentially, left to right.  The
abstract base class SequentialBackoffTagger serves as the base
class for all the taggers in this module.  Tagging of individual words
is performed by the method ``choose_tag()``, which is defined by
subclasses of SequentialBackoffTagger.  If a tagger is unable to
determine a tag for the specified token, then its backoff tagger is
consulted instead.  Any SequentialBackoffTagger may serve as a
backoff tagger for any other SequentialBackoffTagger.
"""
import ast
import re
from abc import abstractmethod
from typing import List, Optional, Tuple

from nltk import jsontags
from nltk.classify import NaiveBayesClassifier
from nltk.probability import ConditionalFreqDist
from nltk.tag.api import FeaturesetTaggerI, TaggerI


######################################################################
# Abstract Base Classes
######################################################################
class SequentialBackoffTagger(TaggerI):
    """
    An abstract base class for taggers that tags words sequentially,
    left to right.  Tagging of individual words is performed by the
    ``choose_tag()`` method, which should be defined by subclasses.  If
    a tagger is unable to determine a tag for the specified token,
    then its backoff tagger is consulted.

    :ivar _taggers: A list of all the taggers that should be tried to
        tag a token (i.e., self and its backoff taggers).
    """

    def __init__(self, backoff=None):
        if backoff is None:
            self._taggers = [self]
        else:
            self._taggers = [self] + backoff._taggers

    @property
    def backoff(self):
        """The backoff tagger for this tagger."""
        return self._taggers[1] if len(self._taggers) > 1 else None

    def tag(self, tokens):
        # docs inherited from TaggerI
        tags = []
        for i in range(len(tokens)):
            tags.append(self.tag_one(tokens, i, tags))
        return list(zip(tokens, tags))

    def tag_one(self, tokens, index, history):
        """
        Determine an appropriate tag for the specified token, and
        return that tag.  If this tagger is unable to determine a tag
        for the specified token, then its backoff tagger is consulted.

        :rtype: str
        :type tokens: list
        :param tokens: The list of words that are being tagged.
        :type index: int
        :param index: The index of the word whose tag should be
            returned.
        :type history: list(str)
        :param history: A list of the tags for all words before *index*.
        """
        tag = None
        for tagger in self._taggers:
            tag = tagger.choose_tag(tokens, index, history)
            if tag is not None:
                break
        return tag

    @abstractmethod
    def choose_tag(self, tokens, index, history):
        """
        Decide which tag should be used for the specified token, and
        return that tag.  If this tagger is unable to determine a tag
        for the specified token, return None -- do not consult
        the backoff tagger.  This method should be overridden by
        subclasses of SequentialBackoffTagger.

        :rtype: str
        :type tokens: list
        :param tokens: The list of words that are being tagged.
        :type index: int
        :param index: The index of the word whose tag should be
            returned.
        :type history: list(str)
        :param history: A list of the tags for all words before *index*.
        """


class ContextTagger(SequentialBackoffTagger):
    """
    An abstract base class for sequential backoff taggers that choose
    a tag for a token based on the value of its "context".  Different
    subclasses are used to define different contexts.

    A ContextTagger chooses the tag for a token by calculating the
    token's context, and looking up the corresponding tag in a table.
    This table can be constructed manually; or it can be automatically
    constructed based on a training corpus, using the ``_train()``
    factory method.

    :ivar _context_to_tag: Dictionary mapping contexts to tags.
    """

    def __init__(self, context_to_tag, backoff=None):
        """
        :param context_to_tag: A dictionary mapping contexts to tags.
        :param backoff: The backoff tagger that should be used for this tagger.
        """
        super().__init__(backoff)
        self._context_to_tag = context_to_tag if context_to_tag else {}

    @abstractmethod
    def context(self, tokens, index, history):
        """
        :return: the context that should be used to look up the tag
            for the specified token; or None if the specified token
            should not be handled by this tagger.
        :rtype: (hashable)
        """

    def choose_tag(self, tokens, index, history):
        context = self.context(tokens, index, history)
        return self._context_to_tag.get(context)

    def size(self):
        """
        :return: The number of entries in the table used by this
            tagger to map from contexts to tags.
        """
        return len(self._context_to_tag)

    def __repr__(self):
        return f"<{self.__class__.__name__}: size={self.size()}>"

    def _train(self, tagged_corpus, cutoff=0, verbose=False):
        """
        Initialize this ContextTagger's ``_context_to_tag`` table
        based on the given training data.  In particular, for each
        context ``c`` in the training data, set
        ``_context_to_tag[c]`` to the most frequent tag for that
        context.  However, exclude any contexts that are already
        tagged perfectly by the backoff tagger(s).

        The old value of ``self._context_to_tag`` (if any) is discarded.

        :param tagged_corpus: A tagged corpus.  Each item should be
            a list of (word, tag tuples.
        :param cutoff: If the most likely tag for a context occurs
            fewer than cutoff times, then exclude it from the
            context-to-tag table for the new tagger.
        """

        token_count = hit_count = 0

        # A context is considered 'useful' if it's not already tagged
        # perfectly by the backoff tagger.
        useful_contexts = set()

        # Count how many times each tag occurs in each context.
        fd = ConditionalFreqDist()
        for sentence in tagged_corpus:
            tokens, tags = zip(*sentence)
            for index, (token, tag) in enumerate(sentence):
                # Record the event.
                token_count += 1
                context = self.context(tokens, index, tags[:index])
                if context is None:
                    continue
                fd[context][tag] += 1
                # If the backoff got it wrong, this context is useful:
                if self.backoff is None or tag != self.backoff.tag_one(
                    tokens, index, tags[:index]
                ):
                    useful_contexts.add(context)

        # Build the context_to_tag table -- for each context, figure
        # out what the most likely tag is.  Only include contexts that
        # we've seen at least `cutoff` times.
        for context in useful_contexts:
            best_tag = fd[context].max()
            hits = fd[context][best_tag]
            if hits > cutoff:
                self._context_to_tag[context] = best_tag
                hit_count += hits

        # Display some stats, if requested.
        if verbose:
            size = len(self._context_to_tag)
            backoff = 100 - (hit_count * 100.0) / token_count
            pruning = 100 - (size * 100.0) / len(fd.conditions())
            print("[Trained Unigram tagger:", end=" ")
            print(
                "size={}, backoff={:.2f}%, pruning={:.2f}%]".format(
                    size, backoff, pruning
                )
            )


######################################################################
# Tagger Classes
######################################################################


@jsontags.register_tag
class DefaultTagger(SequentialBackoffTagger):
    """
    A tagger that assigns the same tag to every token.

        >>> from nltk.tag import DefaultTagger
        >>> default_tagger = DefaultTagger('NN')
        >>> list(default_tagger.tag('This is a test'.split()))
        [('This', 'NN'), ('is', 'NN'), ('a', 'NN'), ('test', 'NN')]

    This tagger is recommended as a backoff tagger, in cases where
    a more powerful tagger is unable to assign a tag to the word
    (e.g. because the word was not seen during training).

    :param tag: The tag to assign to each token
    :type tag: str
    """

    json_tag = "nltk.tag.sequential.DefaultTagger"

    def __init__(self, tag):
        self._tag = tag
        super().__init__(None)

    def encode_json_obj(self):
        return self._tag

    @classmethod
    def decode_json_obj(cls, obj):
        tag = obj
        return cls(tag)

    def choose_tag(self, tokens, index, history):
        return self._tag  # ignore token and history

    def __repr__(self):
        return f"<DefaultTagger: tag={self._tag}>"


@jsontags.register_tag
class NgramTagger(ContextTagger):
    """
    A tagger that chooses a token's tag based on its word string and
    on the preceding n word's tags.  In particular, a tuple
    (tags[i-n:i-1], words[i]) is looked up in a table, and the
    corresponding tag is returned.  N-gram taggers are typically
    trained on a tagged corpus.

    Train a new NgramTagger using the given training data or
    the supplied model.  In particular, construct a new tagger
    whose table maps from each context (tag[i-n:i-1], word[i])
    to the most frequent tag for that context.  But exclude any
    contexts that are already tagged perfectly by the backoff
    tagger.

    :param train: A tagged corpus consisting of a list of tagged
        sentences, where each sentence is a list of (word, tag) tuples.
    :param backoff: A backoff tagger, to be used by the new
        tagger if it encounters an unknown context.
    :param cutoff: If the most likely tag for a context occurs
        fewer than *cutoff* times, then exclude it from the
        context-to-tag table for the new tagger.
    """

    json_tag = "nltk.tag.sequential.NgramTagger"

    def __init__(
        self, n, train=None, model=None, backoff=None, cutoff=0, verbose=False
    ):
        self._n = n
        self._check_params(train, model)

        super().__init__(model, backoff)

        if train:
            self._train(train, cutoff, verbose)

    def encode_json_obj(self):
        _context_to_tag = {repr(k): v for k, v in self._context_to_tag.items()}
        if "NgramTagger" in self.__class__.__name__:
            return self._n, _context_to_tag, self.backoff
        else:
            return _context_to_tag, self.backoff

    @classmethod
    def decode_json_obj(cls, obj):
        try:
            _n, _context_to_tag, backoff = obj
        except ValueError:
            _context_to_tag, backoff = obj

        if not _context_to_tag:
            return backoff

        _context_to_tag = {ast.literal_eval(k): v for k, v in _context_to_tag.items()}

        if "NgramTagger" in cls.__name__:
            return cls(_n, model=_context_to_tag, backoff=backoff)
        else:
            return cls(model=_context_to_tag, backoff=backoff)

    def context(self, tokens, index, history):
        tag_context = tuple(history[max(0, index - self._n + 1) : index])
        return tag_context, tokens[index]


@jsontags.register_tag
class UnigramTagger(NgramTagger):
    """
    Unigram Tagger

    The UnigramTagger finds the most likely tag for each word in a training
    corpus, and then uses that information to assign tags to new tokens.

        >>> from nltk.corpus import brown
        >>> from nltk.tag import UnigramTagger
        >>> test_sent = brown.sents(categories='news')[0]
        >>> unigram_tagger = UnigramTagger(brown.tagged_sents(categories='news')[:500])
        >>> for tok, tag in unigram_tagger.tag(test_sent):
        ...     print("({}, {}), ".format(tok, tag)) # doctest: +NORMALIZE_WHITESPACE
        (The, AT), (Fulton, NP-TL), (County, NN-TL), (Grand, JJ-TL),
        (Jury, NN-TL), (said, VBD), (Friday, NR), (an, AT),
        (investigation, NN), (of, IN), (Atlanta's, NP$), (recent, JJ),
        (primary, NN), (election, NN), (produced, VBD), (``, ``),
        (no, AT), (evidence, NN), ('', ''), (that, CS), (any, DTI),
        (irregularities, NNS), (took, VBD), (place, NN), (., .),

    :param train: The corpus of training data, a list of tagged sentences
    :type train: list(list(tuple(str, str)))
    :param model: The tagger model
    :type model: dict
    :param backoff: Another tagger which this tagger will consult when it is
        unable to tag a word
    :type backoff: TaggerI
    :param cutoff: The number of instances of training data the tagger must see
        in order not to use the backoff tagger
    :type cutoff: int
    """

    json_tag = "nltk.tag.sequential.UnigramTagger"

    def __init__(self, train=None, model=None, backoff=None, cutoff=0, verbose=False):
        super().__init__(1, train, model, backoff, cutoff, verbose)

    def context(self, tokens, index, history):
        return tokens[index]


@jsontags.register_tag
class BigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string and on
    the preceding words' tag.  In particular, a tuple consisting
    of the previous tag and the word is looked up in a table, and
    the corresponding tag is returned.

    :param train: The corpus of training data, a list of tagged sentences
    :type train: list(list(tuple(str, str)))
    :param model: The tagger model
    :type model: dict
    :param backoff: Another tagger which this tagger will consult when it is
        unable to tag a word
    :type backoff: TaggerI
    :param cutoff: The number of instances of training data the tagger must see
        in order not to use the backoff tagger
    :type cutoff: int
    """

    json_tag = "nltk.tag.sequential.BigramTagger"

    def __init__(self, train=None, model=None, backoff=None, cutoff=0, verbose=False):
        super().__init__(2, train, model, backoff, cutoff, verbose)


@jsontags.register_tag
class TrigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string and on
    the preceding two words' tags.  In particular, a tuple consisting
    of the previous two tags and the word is looked up in a table, and
    the corresponding tag is returned.

    :param train: The corpus of training data, a list of tagged sentences
    :type train: list(list(tuple(str, str)))
    :param model: The tagger model
    :type model: dict
    :param backoff: Another tagger which this tagger will consult when it is
        unable to tag a word
    :type backoff: TaggerI
    :param cutoff: The number of instances of training data the tagger must see
        in order not to use the backoff tagger
    :type cutoff: int
    """

    json_tag = "nltk.tag.sequential.TrigramTagger"

    def __init__(self, train=None, model=None, backoff=None, cutoff=0, verbose=False):
        super().__init__(3, train, model, backoff, cutoff, verbose)


@jsontags.register_tag
class AffixTagger(ContextTagger):
    """
    A tagger that chooses a token's tag based on a leading or trailing
    substring of its word string.  (It is important to note that these
    substrings are not necessarily "true" morphological affixes).  In
    particular, a fixed-length substring of the word is looked up in a
    table, and the corresponding tag is returned.  Affix taggers are
    typically constructed by training them on a tagged corpus.

    Construct a new affix tagger.

    :param affix_length: The length of the affixes that should be
        considered during training and tagging.  Use negative
        numbers for suffixes.
    :param min_stem_length: Any words whose length is less than
        min_stem_length+abs(affix_length) will be assigned a
        tag of None by this tagger.
    """

    json_tag = "nltk.tag.sequential.AffixTagger"

    def __init__(
        self,
        train=None,
        model=None,
        affix_length=-3,
        min_stem_length=2,
        backoff=None,
        cutoff=0,
        verbose=False,
    ):
        self._check_params(train, model)

        super().__init__(model, backoff)

        self._affix_length = affix_length
        self._min_word_length = min_stem_length + abs(affix_length)

        if train:
            self._train(train, cutoff, verbose)

    def encode_json_obj(self):
        return (
            self._affix_length,
            self._min_word_length,
            self._context_to_tag,
            self.backoff,
        )

    @classmethod
    def decode_json_obj(cls, obj):
        _affix_length, _min_word_length, _context_to_tag, backoff = obj
        return cls(
            affix_length=_affix_length,
            min_stem_length=_min_word_length - abs(_affix_length),
            model=_context_to_tag,
            backoff=backoff,
        )

    def context(self, tokens, index, history):
        token = tokens[index]
        if len(token) < self._min_word_length:
            return None
        elif self._affix_length > 0:
            return token[: self._affix_length]
        else:
            return token[self._affix_length :]


@jsontags.register_tag
class RegexpTagger(SequentialBackoffTagger):
    r"""
    Regular Expression Tagger

    The RegexpTagger assigns tags to tokens by comparing their
    word strings to a series of regular expressions.  The following tagger
    uses word suffixes to make guesses about the correct Brown Corpus part
    of speech tag:

        >>> from nltk.corpus import brown
        >>> from nltk.tag import RegexpTagger
        >>> test_sent = brown.sents(categories='news')[0]
        >>> regexp_tagger = RegexpTagger(
        ...     [(r'^-?[0-9]+(\.[0-9]+)?$', 'CD'),  # cardinal numbers
        ...      (r'(The|the|A|a|An|an)$', 'AT'),   # articles
        ...      (r'.*able$', 'JJ'),                # adjectives
        ...      (r'.*ness$', 'NN'),                # nouns formed from adjectives
        ...      (r'.*ly$', 'RB'),                  # adverbs
        ...      (r'.*s$', 'NNS'),                  # plural nouns
        ...      (r'.*ing$', 'VBG'),                # gerunds
        ...      (r'.*ed$', 'VBD'),                 # past tense verbs
        ...      (r'.*', 'NN')                      # nouns (default)
        ... ])
        >>> regexp_tagger
        <Regexp Tagger: size=9>
        >>> regexp_tagger.tag(test_sent) # doctest: +NORMALIZE_WHITESPACE
        [('The', 'AT'), ('Fulton', 'NN'), ('County', 'NN'), ('Grand', 'NN'), ('Jury', 'NN'),
        ('said', 'NN'), ('Friday', 'NN'), ('an', 'AT'), ('investigation', 'NN'), ('of', 'NN'),
        ("Atlanta's", 'NNS'), ('recent', 'NN'), ('primary', 'NN'), ('election', 'NN'),
        ('produced', 'VBD'), ('``', 'NN'), ('no', 'NN'), ('evidence', 'NN'), ("''", 'NN'),
        ('that', 'NN'), ('any', 'NN'), ('irregularities', 'NNS'), ('took', 'NN'),
        ('place', 'NN'), ('.', 'NN')]

    :type regexps: list(tuple(str, str))
    :param regexps: A list of ``(regexp, tag)`` pairs, each of
        which indicates that a word matching ``regexp`` should
        be tagged with ``tag``.  The pairs will be evaluated in
        order.  If none of the regexps match a word, then the
        optional backoff tagger is invoked, else it is
        assigned the tag None.
    """

    json_tag = "nltk.tag.sequential.RegexpTagger"

    def __init__(
        self, regexps: List[Tuple[str, str]], backoff: Optional[TaggerI] = None
    ):
        super().__init__(backoff)
        self._regexps = []
        for regexp, tag in regexps:
            try:
                self._regexps.append((re.compile(regexp), tag))
            except Exception as e:
                raise Exception(
                    f"Invalid RegexpTagger regexp: {e}\n- regexp: {regexp!r}\n- tag: {tag!r}"
                ) from e

    def encode_json_obj(self):
        return [(regexp.pattern, tag) for regexp, tag in self._regexps], self.backoff

    @classmethod
    def decode_json_obj(cls, obj):
        regexps, backoff = obj
        return cls(regexps, backoff)

    def choose_tag(self, tokens, index, history):
        for regexp, tag in self._regexps:
            if re.match(regexp, tokens[index]):
                return tag
        return None

    def __repr__(self):
        return f"<Regexp Tagger: size={len(self._regexps)}>"


class ClassifierBasedTagger(SequentialBackoffTagger, FeaturesetTaggerI):
    """
    A sequential tagger that uses a classifier to choose the tag for
    each token in a sentence.  The featureset input for the classifier
    is generated by a feature detector function::

        feature_detector(tokens, index, history) -> featureset

    Where tokens is the list of unlabeled tokens in the sentence;
    index is the index of the token for which feature detection
    should be performed; and history is list of the tags for all
    tokens before index.

    Construct a new classifier-based sequential tagger.

    :param feature_detector: A function used to generate the
        featureset input for the classifier::
        feature_detector(tokens, index, history) -> featureset

    :param train: A tagged corpus consisting of a list of tagged
        sentences, where each sentence is a list of (word, tag) tuples.

    :param backoff: A backoff tagger, to be used by the new tagger
        if it encounters an unknown context.

    :param classifier_builder: A function used to train a new
        classifier based on the data in *train*.  It should take
        one argument, a list of labeled featuresets (i.e.,
        (featureset, label) tuples).

    :param classifier: The classifier that should be used by the
        tagger.  This is only useful if you want to manually
        construct the classifier; normally, you would use *train*
        instead.

    :param backoff: A backoff tagger, used if this tagger is
        unable to determine a tag for a given token.

    :param cutoff_prob: If specified, then this tagger will fall
        back on its backoff tagger if the probability of the most
        likely tag is less than *cutoff_prob*.
    """

    def __init__(
        self,
        feature_detector=None,
        train=None,
        classifier_builder=NaiveBayesClassifier.train,
        classifier=None,
        backoff=None,
        cutoff_prob=None,
        verbose=False,
    ):
        self._check_params(train, classifier)

        super().__init__(backoff)

        if (train and classifier) or (not train and not classifier):
            raise ValueError(
                "Must specify either training data or " "trained classifier."
            )

        if feature_detector is not None:
            self._feature_detector = feature_detector
            # The feature detector function, used to generate a featureset
            # or each token: feature_detector(tokens, index, history) -> featureset

        self._cutoff_prob = cutoff_prob
        """Cutoff probability for tagging -- if the probability of the
           most likely tag is less than this, then use backoff."""

        self._classifier = classifier
        """The classifier used to choose a tag for each token."""

        if train:
            self._train(train, classifier_builder, verbose)

    def choose_tag(self, tokens, index, history):
        # Use our feature detector to get the featureset.
        featureset = self.feature_detector(tokens, index, history)

        # Use the classifier to pick a tag.  If a cutoff probability
        # was specified, then check that the tag's probability is
        # higher than that cutoff first; otherwise, return None.
        if self._cutoff_prob is None:
            return self._classifier.classify(featureset)

        pdist = self._classifier.prob_classify(featureset)
        tag = pdist.max()
        return tag if pdist.prob(tag) >= self._cutoff_prob else None

    def _train(self, tagged_corpus, classifier_builder, verbose):
        """
        Build a new classifier, based on the given training data
        *tagged_corpus*.
        """

        classifier_corpus = []
        if verbose:
            print("Constructing training corpus for classifier.")

        for sentence in tagged_corpus:
            history = []
            untagged_sentence, tags = zip(*sentence)
            for index in range(len(sentence)):
                featureset = self.feature_detector(untagged_sentence, index, history)
                classifier_corpus.append((featureset, tags[index]))
                history.append(tags[index])

        if verbose:
            print(f"Training classifier ({len(classifier_corpus)} instances)")
        self._classifier = classifier_builder(classifier_corpus)

    def __repr__(self):
        return f"<ClassifierBasedTagger: {self._classifier}>"

    def feature_detector(self, tokens, index, history):
        """
        Return the feature detector that this tagger uses to generate
        featuresets for its classifier.  The feature detector is a
        function with the signature::

          feature_detector(tokens, index, history) -> featureset

        See ``classifier()``
        """
        return self._feature_detector(tokens, index, history)

    def classifier(self):
        """
        Return the classifier that this tagger uses to choose a tag
        for each word in a sentence.  The input for this classifier is
        generated using this tagger's feature detector.
        See ``feature_detector()``
        """
        return self._classifier


class ClassifierBasedPOSTagger(ClassifierBasedTagger):
    """
    A classifier based part of speech tagger.
    """

    def feature_detector(self, tokens, index, history):
        word = tokens[index]
        if index == 0:
            prevword = prevprevword = None
            prevtag = prevprevtag = None
        elif index == 1:
            prevword = tokens[index - 1].lower()
            prevprevword = None
            prevtag = history[index - 1]
            prevprevtag = None
        else:
            prevword = tokens[index - 1].lower()
            prevprevword = tokens[index - 2].lower()
            prevtag = history[index - 1]
            prevprevtag = history[index - 2]

        if re.match(r"[0-9]+(\.[0-9]*)?|[0-9]*\.[0-9]+$", word):
            shape = "number"
        elif re.match(r"\W+$", word):
            shape = "punct"
        elif re.match("[A-Z][a-z]+$", word):
            shape = "upcase"
        elif re.match("[a-z]+$", word):
            shape = "downcase"
        elif re.match(r"\w+$", word):
            shape = "mixedcase"
        else:
            shape = "other"

        features = {
            "prevtag": prevtag,
            "prevprevtag": prevprevtag,
            "word": word,
            "word.lower": word.lower(),
            "suffix3": word.lower()[-3:],
            "suffix2": word.lower()[-2:],
            "suffix1": word.lower()[-1:],
            "prevprevword": prevprevword,
            "prevword": prevword,
            "prevtag+word": f"{prevtag}+{word.lower()}",
            "prevprevtag+word": f"{prevprevtag}+{word.lower()}",
            "prevword+word": f"{prevword}+{word.lower()}",
            "shape": shape,
        }
        return features

# === NexusCore/openenv\Lib\site-packages\pyparsing\diagram\__init__.py ===
# mypy: ignore-errors
from __future__ import annotations

import itertools
import railroad
import pyparsing
import dataclasses
import typing
from typing import (
    Generic,
    TypeVar,
    Callable,
    Iterable,
)
from jinja2 import Template
from io import StringIO
import inspect
import re


jinja2_template_source = """\
{% if not embed %}
<!DOCTYPE html>
<html>
<head>
{% endif %}
    {% if not head %}
        <style>
            .railroad-heading {
                font-family: monospace;
            }
        </style>
    {% else %}
        {{ head | safe }}
    {% endif %}
{% if not embed %}
</head>
<body>
{% endif %}
<meta charset="UTF-8"/>
{{ body | safe }}
{% for diagram in diagrams %}
    <div class="railroad-group">
        <h1 class="railroad-heading" id="{{ diagram.bookmark }}">{{ diagram.title }}</h1>
        <div class="railroad-description">{{ diagram.text }}</div>
        <div class="railroad-svg">
            {{ diagram.svg }}
        </div>
    </div>
{% endfor %}
{% if not embed %}
</body>
</html>
{% endif %}
"""

template = Template(jinja2_template_source)


_bookmark_lookup = {}
_bookmark_ids = itertools.count(start=1)

def _make_bookmark(s: str) -> str:
    """
    Converts a string into a valid HTML bookmark (ID or anchor name).
    """
    if s in _bookmark_lookup:
        return _bookmark_lookup[s]

    # Replace invalid characters with hyphens and ensure only valid characters
    bookmark = re.sub(r'[^a-zA-Z0-9-]+', '-', s)

    # Ensure it starts with a letter by adding 'z' if necessary
    if not bookmark[:1].isalpha():
        bookmark = f"z{bookmark}"

    # Convert to lowercase and strip hyphens
    bookmark = bookmark.lower().strip('-')

    _bookmark_lookup[s] = bookmark = f"{bookmark}-{next(_bookmark_ids):04d}"

    return bookmark


def _collapse_verbose_regex(regex_str: str) -> str:
    if "\n" not in regex_str:
        return regex_str
    collapsed = pyparsing.Regex(r"#.*$").suppress().transform_string(regex_str)
    collapsed = re.sub(r"\s*\n\s*", "", collapsed)
    return collapsed


@dataclasses.dataclass
class NamedDiagram:
    """
    A simple structure for associating a name with a railroad diagram
    """

    name: str
    index: int
    diagram: railroad.DiagramItem = None

    @property
    def bookmark(self):
        bookmark = _make_bookmark(self.name)
        return bookmark


T = TypeVar("T")


class EachItem(railroad.Group):
    """
    Custom railroad item to compose a:
    - Group containing a
      - OneOrMore containing a
        - Choice of the elements in the Each
    with the group label indicating that all must be matched
    """

    all_label = "[ALL]"

    def __init__(self, *items) -> None:
        choice_item = railroad.Choice(len(items) - 1, *items)
        one_or_more_item = railroad.OneOrMore(item=choice_item)
        super().__init__(one_or_more_item, label=self.all_label)


class AnnotatedItem(railroad.Group):
    """
    Simple subclass of Group that creates an annotation label
    """

    def __init__(self, label: str, item) -> None:
        super().__init__(item=item, label=f"[{label}]" if label else "")


class EditablePartial(Generic[T]):
    """
    Acts like a functools.partial, but can be edited. In other words, it represents a type that hasn't yet been
    constructed.
    """

    # We need this here because the railroad constructors actually transform the data, so can't be called until the
    # entire tree is assembled

    def __init__(self, func: Callable[..., T], args: list, kwargs: dict) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def from_call(cls, func: Callable[..., T], *args, **kwargs) -> EditablePartial[T]:
        """
        If you call this function in the same way that you would call the constructor, it will store the arguments
        as you expect. For example EditablePartial.from_call(Fraction, 1, 3)() == Fraction(1, 3)
        """
        return EditablePartial(func=func, args=list(args), kwargs=kwargs)

    @property
    def name(self):
        return self.kwargs["name"]

    def __call__(self) -> T:
        """
        Evaluate the partial and return the result
        """
        args = self.args.copy()
        kwargs = self.kwargs.copy()

        # This is a helpful hack to allow you to specify varargs parameters (e.g. *args) as keyword args (e.g.
        # args=['list', 'of', 'things'])
        arg_spec = inspect.getfullargspec(self.func)
        if arg_spec.varargs in self.kwargs:
            args += kwargs.pop(arg_spec.varargs)

        return self.func(*args, **kwargs)


def railroad_to_html(diagrams: list[NamedDiagram], embed=False, **kwargs) -> str:
    """
    Given a list of NamedDiagram, produce a single HTML string that visualises those diagrams
    :params kwargs: kwargs to be passed in to the template
    """
    data = []
    for diagram in diagrams:
        if diagram.diagram is None:
            continue
        io = StringIO()
        try:
            css = kwargs.get("css")
            diagram.diagram.writeStandalone(io.write, css=css)
        except AttributeError:
            diagram.diagram.writeSvg(io.write)
        title = diagram.name
        if diagram.index == 0:
            title += " (root)"
        data.append(
            {
                "title": title, "text": "", "svg": io.getvalue(), "bookmark": diagram.bookmark
            }
        )

    return template.render(diagrams=data, embed=embed, **kwargs)


def resolve_partial(partial: EditablePartial[T]) -> T:
    """
    Recursively resolves a collection of Partials into whatever type they are
    """
    if isinstance(partial, EditablePartial):
        partial.args = resolve_partial(partial.args)
        partial.kwargs = resolve_partial(partial.kwargs)
        return partial()
    elif isinstance(partial, list):
        return [resolve_partial(x) for x in partial]
    elif isinstance(partial, dict):
        return {key: resolve_partial(x) for key, x in partial.items()}
    else:
        return partial


def to_railroad(
    element: pyparsing.ParserElement,
    diagram_kwargs: typing.Optional[dict] = None,
    vertical: int = 3,
    show_results_names: bool = False,
    show_groups: bool = False,
    show_hidden: bool = False,
) -> list[NamedDiagram]:
    """
    Convert a pyparsing element tree into a list of diagrams. This is the recommended entrypoint to diagram
    creation if you want to access the Railroad tree before it is converted to HTML
    :param element: base element of the parser being diagrammed
    :param diagram_kwargs: kwargs to pass to the Diagram() constructor
    :param vertical: (optional) - int - limit at which number of alternatives should be
       shown vertically instead of horizontally
    :param show_results_names - bool to indicate whether results name annotations should be
       included in the diagram
    :param show_groups - bool to indicate whether groups should be highlighted with an unlabeled
       surrounding box
    :param show_hidden - bool to indicate whether internal elements that are typically hidden
       should be shown
    """
    # Convert the whole tree underneath the root
    lookup = ConverterState(diagram_kwargs=diagram_kwargs or {})
    _to_diagram_element(
        element,
        lookup=lookup,
        parent=None,
        vertical=vertical,
        show_results_names=show_results_names,
        show_groups=show_groups,
        show_hidden=show_hidden,
    )

    root_id = id(element)
    # Convert the root if it hasn't been already
    if root_id in lookup:
        if not element.customName:
            lookup[root_id].name = ""
        lookup[root_id].mark_for_extraction(root_id, lookup, force=True)

    # Now that we're finished, we can convert from intermediate structures into Railroad elements
    diags = list(lookup.diagrams.values())
    if len(diags) > 1:
        # collapse out duplicate diags with the same name
        seen = set()
        deduped_diags = []
        for d in diags:
            # don't extract SkipTo elements, they are uninformative as subdiagrams
            if d.name == "...":
                continue
            if d.name is not None and d.name not in seen:
                seen.add(d.name)
                deduped_diags.append(d)
        resolved = [resolve_partial(partial) for partial in deduped_diags]
    else:
        # special case - if just one diagram, always display it, even if
        # it has no name
        resolved = [resolve_partial(partial) for partial in diags]
    return sorted(resolved, key=lambda diag: diag.index)


def _should_vertical(
    specification: int, exprs: Iterable[pyparsing.ParserElement]
) -> bool:
    """
    Returns true if we should return a vertical list of elements
    """
    if specification is None:
        return False
    else:
        return len(_visible_exprs(exprs)) >= specification


@dataclasses.dataclass
class ElementState:
    """
    State recorded for an individual pyparsing Element
    """

    #: The pyparsing element that this represents
    element: pyparsing.ParserElement
    #: The output Railroad element in an unconverted state
    converted: EditablePartial
    #: The parent Railroad element, which we store so that we can extract this if it's duplicated
    parent: EditablePartial
    #: The order in which we found this element, used for sorting diagrams if this is extracted into a diagram
    number: int
    #: The name of the element
    name: str = None
    #: The index of this inside its parent
    parent_index: typing.Optional[int] = None
    #: If true, we should extract this out into a subdiagram
    extract: bool = False
    #: If true, all of this element's children have been filled out
    complete: bool = False

    def mark_for_extraction(
        self, el_id: int, state: ConverterState, name: str = None, force: bool = False
    ):
        """
        Called when this instance has been seen twice, and thus should eventually be extracted into a sub-diagram
        :param el_id: id of the element
        :param state: element/diagram state tracker
        :param name: name to use for this element's text
        :param force: If true, force extraction now, regardless of the state of this. Only useful for extracting the
        root element when we know we're finished
        """
        self.extract = True

        # Set the name
        if not self.name:
            if name:
                # Allow forcing a custom name
                self.name = name
            elif self.element.customName:
                self.name = self.element.customName
            else:
                self.name = ""

        # Just because this is marked for extraction doesn't mean we can do it yet. We may have to wait for children
        # to be added
        # Also, if this is just a string literal etc, don't bother extracting it
        if force or (self.complete and _worth_extracting(self.element)):
            state.extract_into_diagram(el_id)


class ConverterState:
    """
    Stores some state that persists between recursions into the element tree
    """

    def __init__(self, diagram_kwargs: typing.Optional[dict] = None) -> None:
        #: A dictionary mapping ParserElements to state relating to them
        self._element_diagram_states: dict[int, ElementState] = {}
        #: A dictionary mapping ParserElement IDs to subdiagrams generated from them
        self.diagrams: dict[int, EditablePartial[NamedDiagram]] = {}
        #: The index of the next unnamed element
        self.unnamed_index: int = 1
        #: The index of the next element. This is used for sorting
        self.index: int = 0
        #: Shared kwargs that are used to customize the construction of diagrams
        self.diagram_kwargs: dict = diagram_kwargs or {}
        self.extracted_diagram_names: set[str] = set()

    def __setitem__(self, key: int, value: ElementState):
        self._element_diagram_states[key] = value

    def __getitem__(self, key: int) -> ElementState:
        return self._element_diagram_states[key]

    def __delitem__(self, key: int):
        del self._element_diagram_states[key]

    def __contains__(self, key: int):
        return key in self._element_diagram_states

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def generate_unnamed(self) -> int:
        """
        Generate a number used in the name of an otherwise unnamed diagram
        """
        self.unnamed_index += 1
        return self.unnamed_index

    def generate_index(self) -> int:
        """
        Generate a number used to index a diagram
        """
        self.index += 1
        return self.index

    def extract_into_diagram(self, el_id: int):
        """
        Used when we encounter the same token twice in the same tree. When this
        happens, we replace all instances of that token with a terminal, and
        create a new subdiagram for the token
        """
        position = self[el_id]

        # Replace the original definition of this element with a regular block
        if position.parent:
            href = f"#{_make_bookmark(position.name)}"
            ret = EditablePartial.from_call(railroad.NonTerminal, text=position.name, href=href)
            if "item" in position.parent.kwargs:
                position.parent.kwargs["item"] = ret
            elif "items" in position.parent.kwargs:
                position.parent.kwargs["items"][position.parent_index] = ret

        # If the element we're extracting is a group, skip to its content but keep the title
        if position.converted.func == railroad.Group:
            content = position.converted.kwargs["item"]
        else:
            content = position.converted

        self.diagrams[el_id] = EditablePartial.from_call(
            NamedDiagram,
            name=position.name,
            diagram=EditablePartial.from_call(
                railroad.Diagram, content, **self.diagram_kwargs
            ),
            index=position.number,
        )

        del self[el_id]


def _worth_extracting(element: pyparsing.ParserElement) -> bool:
    """
    Returns true if this element is worth having its own sub-diagram. Simply, if any of its children
    themselves have children, then its complex enough to extract
    """
    children = element.recurse()
    return any(child.recurse() for child in children)


def _apply_diagram_item_enhancements(fn):
    """
    decorator to ensure enhancements to a diagram item (such as results name annotations)
    get applied on return from _to_diagram_element (we do this since there are several
    returns in _to_diagram_element)
    """

    def _inner(
        element: pyparsing.ParserElement,
        parent: typing.Optional[EditablePartial],
        lookup: ConverterState = None,
        vertical: int = None,
        index: int = 0,
        name_hint: str = None,
        show_results_names: bool = False,
        show_groups: bool = False,
        show_hidden: bool = False,
    ) -> typing.Optional[EditablePartial]:
        ret = fn(
            element,
            parent,
            lookup,
            vertical,
            index,
            name_hint,
            show_results_names,
            show_groups,
            show_hidden,
        )

        # apply annotation for results name, if present
        if show_results_names and ret is not None:
            element_results_name = element.resultsName
            if element_results_name:
                # add "*" to indicate if this is a "list all results" name
                modal_tag = "" if element.modalResults else "*"
                ret = EditablePartial.from_call(
                    railroad.Group,
                    item=ret,
                    label=f"{repr(element_results_name)}{modal_tag}",
                )

        return ret

    return _inner


def _visible_exprs(exprs: Iterable[pyparsing.ParserElement]):
    non_diagramming_exprs = (
        pyparsing.ParseElementEnhance,
        pyparsing.PositionToken,
        pyparsing.And._ErrorStop,
    )
    return [
        e
        for e in exprs
        if not isinstance(e, non_diagramming_exprs)
    ]


@_apply_diagram_item_enhancements
def _to_diagram_element(
    element: pyparsing.ParserElement,
    parent: typing.Optional[EditablePartial],
    lookup: ConverterState = None,
    vertical: int = None,
    index: int = 0,
    name_hint: str = None,
    show_results_names: bool = False,
    show_groups: bool = False,
    show_hidden: bool = False,
) -> typing.Optional[EditablePartial]:
    """
    Recursively converts a PyParsing Element to a railroad Element
    :param lookup: The shared converter state that keeps track of useful things
    :param index: The index of this element within the parent
    :param parent: The parent of this element in the output tree
    :param vertical: Controls at what point we make a list of elements vertical. If this is an integer (the default),
    it sets the threshold of the number of items before we go vertical. If True, always go vertical, if False, never
    do so
    :param name_hint: If provided, this will override the generated name
    :param show_results_names: bool flag indicating whether to add annotations for results names
    :param show_groups: bool flag indicating whether to show groups using bounding box
    :param show_hidden: bool flag indicating whether to show elements that are typically hidden
    :returns: The converted version of the input element, but as a Partial that hasn't yet been constructed
    """
    exprs = element.recurse()
    name = name_hint or element.customName or type(element).__name__

    # Python's id() is used to provide a unique identifier for elements
    el_id = id(element)

    element_results_name = element.resultsName

    # Here we basically bypass processing certain wrapper elements if they contribute nothing to the diagram
    if not element.customName:
        if isinstance(
            element,
            (
                # pyparsing.TokenConverter,
                pyparsing.Forward,
                pyparsing.Located,
            ),
        ):
            # However, if this element has a useful custom name, and its child does not, we can pass it on to the child
            if exprs:
                if not exprs[0].customName:
                    propagated_name = name
                else:
                    propagated_name = None

                return _to_diagram_element(
                    element.expr,
                    parent=parent,
                    lookup=lookup,
                    vertical=vertical,
                    index=index,
                    name_hint=propagated_name,
                    show_results_names=show_results_names,
                    show_groups=show_groups,
                    show_hidden=show_hidden,
                )

    # If the element isn't worth extracting, we always treat it as the first time we say it
    if _worth_extracting(element):
        looked_up = lookup.get(el_id)
        if looked_up and looked_up.name is not None:
            # If we've seen this element exactly once before, we are only just now finding out that it's a duplicate,
            # so we have to extract it into a new diagram.
            looked_up.mark_for_extraction(el_id, lookup, name=name_hint)
            href = f"#{_make_bookmark(looked_up.name)}"
            ret = EditablePartial.from_call(railroad.NonTerminal, text=looked_up.name, href=href)
            return ret

        elif el_id in lookup.diagrams:
            # If we have seen the element at least twice before, and have already extracted it into a subdiagram, we
            # just put in a marker element that refers to the sub-diagram
            text = lookup.diagrams[el_id].kwargs["name"]
            ret = EditablePartial.from_call(
                railroad.NonTerminal, text=text, href=f"#{_make_bookmark(text)}"
            )
            return ret

    # Recursively convert child elements
    # Here we find the most relevant Railroad element for matching pyparsing Element
    # We use ``items=[]`` here to hold the place for where the child elements will go once created

    # see if this element is normally hidden, and whether hidden elements are desired
    # if not, just return None
    if not element.show_in_diagram and not show_hidden:
        return None

    if isinstance(element, pyparsing.And):
        # detect And's created with ``expr*N`` notation - for these use a OneOrMore with a repeat
        # (all will have the same name, and resultsName)
        if not exprs:
            return None
        if len(set((e.name, e.resultsName) for e in exprs)) == 1 and len(exprs) > 2:
            ret = EditablePartial.from_call(
                railroad.OneOrMore, item="", repeat=str(len(exprs))
            )
        elif _should_vertical(vertical, exprs):
            ret = EditablePartial.from_call(railroad.Stack, items=[])
        else:
            ret = EditablePartial.from_call(railroad.Sequence, items=[])
    elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
        if not exprs:
            return None
        if _should_vertical(vertical, exprs):
            ret = EditablePartial.from_call(railroad.Choice, 0, items=[])
        else:
            ret = EditablePartial.from_call(railroad.HorizontalChoice, items=[])
    elif isinstance(element, pyparsing.Each):
        if not exprs:
            return None
        ret = EditablePartial.from_call(EachItem, items=[])
    elif isinstance(element, pyparsing.NotAny):
        ret = EditablePartial.from_call(AnnotatedItem, label="NOT", item="")
    elif isinstance(element, pyparsing.FollowedBy):
        ret = EditablePartial.from_call(AnnotatedItem, label="LOOKAHEAD", item="")
    elif isinstance(element, pyparsing.PrecededBy):
        ret = EditablePartial.from_call(AnnotatedItem, label="LOOKBEHIND", item="")
    elif isinstance(element, pyparsing.Group):
        if show_groups:
            ret = EditablePartial.from_call(AnnotatedItem, label="", item="")
        else:
            ret = EditablePartial.from_call(
                railroad.Group, item=None, label=element_results_name
            )
    elif isinstance(element, pyparsing.TokenConverter):
        label = type(element).__name__.lower()
        if label == "tokenconverter":
            ret = EditablePartial.from_call(railroad.Sequence, items=[])
        else:
            ret = EditablePartial.from_call(AnnotatedItem, label=label, item="")
    elif isinstance(element, pyparsing.Opt):
        ret = EditablePartial.from_call(railroad.Optional, item="")
    elif isinstance(element, pyparsing.OneOrMore):
        if element.not_ender is not None:
            args = [
                parent,
                lookup,
                vertical,
                index,
                name_hint,
                show_results_names,
                show_groups,
                show_hidden,
            ]
            return _to_diagram_element(
                (~element.not_ender.expr + element.expr)[1, ...].set_name(element.name),
                *args,
            )
        ret = EditablePartial.from_call(railroad.OneOrMore, item=None)
    elif isinstance(element, pyparsing.ZeroOrMore):
        if element.not_ender is not None:
            args = [
                parent,
                lookup,
                vertical,
                index,
                name_hint,
                show_results_names,
                show_groups,
                show_hidden,
            ]
            return _to_diagram_element(
                (~element.not_ender.expr + element.expr)[...].set_name(element.name),
                *args,
            )
        ret = EditablePartial.from_call(railroad.ZeroOrMore, item="")
    elif isinstance(element, pyparsing.Empty) and not element.customName:
        # Skip unnamed "Empty" elements
        ret = None
    elif isinstance(element, pyparsing.ParseElementEnhance):
        ret = EditablePartial.from_call(railroad.Sequence, items=[])
    elif len(exprs) > 0 and not element_results_name:
        ret = EditablePartial.from_call(railroad.Group, item="", label=name)
    elif isinstance(element, pyparsing.Regex):
        collapsed_patt = _collapse_verbose_regex(element.pattern)
        ret = EditablePartial.from_call(railroad.Terminal, collapsed_patt)
    elif len(exprs) > 0:
        ret = EditablePartial.from_call(railroad.Sequence, items=[])
    else:
        terminal = EditablePartial.from_call(railroad.Terminal, element.defaultName)
        ret = terminal

    if ret is None:
        return

    # Indicate this element's position in the tree so we can extract it if necessary
    lookup[el_id] = ElementState(
        element=element,
        converted=ret,
        parent=parent,
        parent_index=index,
        number=lookup.generate_index(),
    )
    if element.customName:
        lookup[el_id].mark_for_extraction(el_id, lookup, element.customName)

    i = 0
    for expr in exprs:
        # Add a placeholder index in case we have to extract the child before we even add it to the parent
        if "items" in ret.kwargs:
            ret.kwargs["items"].insert(i, None)

        item = _to_diagram_element(
            expr,
            parent=ret,
            lookup=lookup,
            vertical=vertical,
            index=i,
            show_results_names=show_results_names,
            show_groups=show_groups,
            show_hidden=show_hidden,
        )

        # Some elements don't need to be shown in the diagram
        if item is not None:
            if "item" in ret.kwargs:
                ret.kwargs["item"] = item
            elif "items" in ret.kwargs:
                # If we've already extracted the child, don't touch this index, since it's occupied by a nonterminal
                ret.kwargs["items"][i] = item
                i += 1
        elif "items" in ret.kwargs:
            # If we're supposed to skip this element, remove it from the parent
            del ret.kwargs["items"][i]

    # If all this items children are none, skip this item
    if ret and (
        ("items" in ret.kwargs and len(ret.kwargs["items"]) == 0)
        or ("item" in ret.kwargs and ret.kwargs["item"] is None)
    ):
        ret = EditablePartial.from_call(railroad.Terminal, name)

    # Mark this element as "complete", ie it has all of its children
    if el_id in lookup:
        lookup[el_id].complete = True

    if el_id in lookup and lookup[el_id].extract and lookup[el_id].complete:
        lookup.extract_into_diagram(el_id)
        if ret is not None:
            text = lookup.diagrams[el_id].kwargs["name"]
            href = f"#{_make_bookmark(text)}"
            ret = EditablePartial.from_call(
                railroad.NonTerminal, text=text, href=href
            )

    return ret