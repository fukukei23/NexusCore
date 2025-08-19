
# === NexusCore/openenv\Lib\site-packages\debugpy\common\messaging.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

"""An implementation of the session and presentation layers as used in the Debug
Adapter Protocol (DAP): channels and their lifetime, JSON messages, requests,
responses, and events.

https://microsoft.github.io/debug-adapter-protocol/overview#base-protocol
"""

from __future__ import annotations

import collections
import contextlib
import functools
import itertools
import os
import socket
import sys
import threading

from debugpy.common import json, log, util
from debugpy.common.util import hide_thread_from_debugger


class JsonIOError(IOError):
    """Indicates that a read or write operation on JsonIOStream has failed."""

    def __init__(self, *args, **kwargs):
        stream = kwargs.pop("stream")
        cause = kwargs.pop("cause", None)
        if not len(args) and cause is not None:
            args = [str(cause)]
        super().__init__(*args, **kwargs)

        self.stream = stream
        """The stream that couldn't be read or written.

        Set by JsonIOStream.read_json() and JsonIOStream.write_json().

        JsonMessageChannel relies on this value to decide whether a NoMoreMessages
        instance that bubbles up to the message loop is related to that loop.
        """

        self.cause = cause
        """The underlying exception, if any."""


class NoMoreMessages(JsonIOError, EOFError):
    """Indicates that there are no more messages that can be read from or written
    to a stream.
    """

    def __init__(self, *args, **kwargs):
        args = args if len(args) else ["No more messages"]
        super().__init__(*args, **kwargs)


class JsonIOStream(object):
    """Implements a JSON value stream over two byte streams (input and output).

    Each value is encoded as a DAP packet, with metadata headers and a JSON payload.
    """

    MAX_BODY_SIZE = 0xFFFFFF

    json_decoder_factory = json.JsonDecoder
    """Used by read_json() when decoder is None."""

    json_encoder_factory = json.JsonEncoder
    """Used by write_json() when encoder is None."""

    @classmethod
    def from_stdio(cls, name="stdio"):
        """Creates a new instance that receives messages from sys.stdin, and sends
        them to sys.stdout.
        """
        return cls(sys.stdin.buffer, sys.stdout.buffer, name)

    @classmethod
    def from_process(cls, process, name="stdio"):
        """Creates a new instance that receives messages from process.stdin, and sends
        them to process.stdout.
        """
        return cls(process.stdout, process.stdin, name)

    @classmethod
    def from_socket(cls, sock, name=None):
        """Creates a new instance that sends and receives messages over a socket."""
        sock.settimeout(None)  # make socket blocking
        if name is None:
            name = repr(sock)

        # TODO: investigate switching to buffered sockets; readline() on unbuffered
        # sockets is very slow! Although the implementation of readline() itself is
        # native code, it calls read(1) in a loop - and that then ultimately calls
        # SocketIO.readinto(), which is implemented in Python.
        socket_io = sock.makefile("rwb", 0)

        # SocketIO.close() doesn't close the underlying socket.
        def cleanup():
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:  # pragma: no cover
                pass
            sock.close()

        return cls(socket_io, socket_io, name, cleanup)

    def __init__(self, reader, writer, name=None, cleanup=lambda: None):
        """Creates a new JsonIOStream.

        reader must be a BytesIO-like object, from which incoming messages will be
        read by read_json().

        writer must be a BytesIO-like object, into which outgoing messages will be
        written by write_json().

        cleanup must be a callable; it will be invoked without arguments when the
        stream is closed.

        reader.readline() must treat "\n" as the line terminator, and must leave "\r"
        as is - it must not replace "\r\n" with "\n" automatically, as TextIO does.
        """

        if name is None:
            name = f"reader={reader!r}, writer={writer!r}"

        self.name = name
        self._reader = reader
        self._writer = writer
        self._cleanup = cleanup
        self._closed = False

    def close(self):
        """Closes the stream, the reader, and the writer."""

        if self._closed:
            return
        self._closed = True

        log.debug("Closing {0} message stream", self.name)
        try:
            try:
                # Close the writer first, so that the other end of the connection has
                # its message loop waiting on read() unblocked. If there is an exception
                # while closing the writer, we still want to try to close the reader -
                # only one exception can bubble up, so if both fail, it'll be the one
                # from reader.
                try:
                    self._writer.close()
                finally:
                    if self._reader is not self._writer:
                        self._reader.close()
            finally:
                self._cleanup()
        except Exception:  # pragma: no cover
            log.reraise_exception("Error while closing {0} message stream", self.name)

    def _log_message(self, dir, data, logger=log.debug):
        return logger("{0} {1} {2}", self.name, dir, data)

    def _read_line(self, reader):
        line = b""
        while True:
            try:
                line += reader.readline()
            except Exception as exc:
                raise NoMoreMessages(str(exc), stream=self)
            if not line:
                raise NoMoreMessages(stream=self)
            if line.endswith(b"\r\n"):
                line = line[0:-2]
                return line

    def read_json(self, decoder=None):
        """Read a single JSON value from reader.

        Returns JSON value as parsed by decoder.decode(), or raises NoMoreMessages
        if there are no more values to be read.
        """

        decoder = decoder if decoder is not None else self.json_decoder_factory()
        reader = self._reader
        read_line = functools.partial(self._read_line, reader)

        # If any error occurs while reading and parsing the message, log the original
        # raw message data as is, so that it's possible to diagnose missing or invalid
        # headers, encoding issues, JSON syntax errors etc.
        def log_message_and_reraise_exception(format_string="", *args, **kwargs):
            if format_string:
                format_string += "\n\n"
            format_string += "{name} -->\n{raw_lines}"

            raw_lines = b"".join(raw_chunks).split(b"\n")
            raw_lines = "\n".join(repr(line) for line in raw_lines)

            log.reraise_exception(
                format_string, *args, name=self.name, raw_lines=raw_lines, **kwargs
            )

        raw_chunks = []
        headers = {}

        while True:
            try:
                line = read_line()
            except Exception:  # pragma: no cover
                # Only log it if we have already read some headers, and are looking
                # for a blank line terminating them. If this is the very first read,
                # there's no message data to log in any case, and the caller might
                # be anticipating the error - e.g. NoMoreMessages on disconnect.
                if headers:
                    log_message_and_reraise_exception(
                        "Error while reading message headers:"
                    )
                else:
                    raise

            raw_chunks += [line, b"\n"]
            if line == b"":
                break

            key, _, value = line.partition(b":")
            headers[key] = value

        try:
            length = int(headers[b"Content-Length"])
            if not (0 <= length <= self.MAX_BODY_SIZE):
                raise ValueError
        except (KeyError, ValueError):  # pragma: no cover
            try:
                raise IOError("Content-Length is missing or invalid:")
            except Exception:
                log_message_and_reraise_exception()

        body_start = len(raw_chunks)
        body_remaining = length
        while body_remaining > 0:
            try:
                chunk = reader.read(body_remaining)
                if not chunk:
                    raise EOFError
            except Exception as exc:
                # Not logged due to https://github.com/microsoft/ptvsd/issues/1699
                raise NoMoreMessages(str(exc), stream=self)

            raw_chunks.append(chunk)
            body_remaining -= len(chunk)
        assert body_remaining == 0

        body = b"".join(raw_chunks[body_start:])
        try:
            body = body.decode("utf-8")
        except Exception:  # pragma: no cover
            log_message_and_reraise_exception()

        try:
            body = decoder.decode(body)
        except Exception:  # pragma: no cover
            log_message_and_reraise_exception()

        # If parsed successfully, log as JSON for readability.
        self._log_message("-->", body)
        return body

    def write_json(self, value, encoder=None):
        """Write a single JSON value into writer.

        Value is written as encoded by encoder.encode().
        """

        if self._closed:
            # Don't log this - it's a common pattern to write to a stream while
            # anticipating EOFError from it in case it got closed concurrently.
            raise NoMoreMessages(stream=self)

        encoder = encoder if encoder is not None else self.json_encoder_factory()
        writer = self._writer

        # Format the value as a message, and try to log any failures using as much
        # information as we already have at the point of the failure. For example,
        # if it fails after it is serialized to JSON, log that JSON.

        try:
            body = encoder.encode(value)
        except Exception:  # pragma: no cover
            self._log_message("<--", repr(value), logger=log.reraise_exception)
        body = body.encode("utf-8")

        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        data = header + body
        data_written = 0
        try:
            while data_written < len(data):
                written = writer.write(data[data_written:])
                if written is not None:
                    data_written += written
            writer.flush()
        except Exception as exc:  # pragma: no cover
            self._log_message("<--", value, logger=log.swallow_exception)
            raise JsonIOError(stream=self, cause=exc)

        self._log_message("<--", value)

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


class MessageDict(collections.OrderedDict):
    """A specialized dict that is used for JSON message payloads - Request.arguments,
    Response.body, and Event.body.

    For all members that normally throw KeyError when a requested key is missing, this
    dict raises InvalidMessageError instead. Thus, a message handler can skip checks
    for missing properties, and just work directly with the payload on the assumption
    that it is valid according to the protocol specification; if anything is missing,
    it will be reported automatically in the proper manner.

    If the value for the requested key is itself a dict, it is returned as is, and not
    automatically converted to MessageDict. Thus, to enable convenient chaining - e.g.
    d["a"]["b"]["c"] - the dict must consistently use MessageDict instances rather than
    vanilla dicts for all its values, recursively. This is guaranteed for the payload
    of all freshly received messages (unless and until it is mutated), but there is no
    such guarantee for outgoing messages.
    """

    def __init__(self, message, items=None):
        assert message is None or isinstance(message, Message)

        if items is None:
            super().__init__()
        else:
            super().__init__(items)

        self.message = message
        """The Message object that owns this dict.

        For any instance exposed via a Message object corresponding to some incoming
        message, it is guaranteed to reference that Message object. There is no similar
        guarantee for outgoing messages.
        """

    def __repr__(self):
        try:
            return format(json.repr(self))
        except Exception:  # pragma: no cover
            return super().__repr__()

    def __call__(self, key, validate, optional=False):
        """Like get(), but with validation.

        The item is first retrieved as if with self.get(key, default=()) - the default
        value is () rather than None, so that JSON nulls are distinguishable from
        missing properties.

        If optional=True, and the value is (), it's returned as is. Otherwise, the
        item is validated by invoking validate(item) on it.

        If validate=False, it's treated as if it were (lambda x: x) - i.e. any value
        is considered valid, and is returned unchanged. If validate is a type or a
        tuple, it's treated as json.of_type(validate). Otherwise, if validate is not
        callable(), it's treated as json.default(validate).

        If validate() returns successfully, the item is substituted with the value
        it returns - thus, the validator can e.g. replace () with a suitable default
        value for the property.

        If validate() raises TypeError or ValueError, raises InvalidMessageError with
        the same text that applies_to(self.messages).

        See debugpy.common.json for reusable validators.
        """

        if not validate:
            validate = lambda x: x
        elif isinstance(validate, type) or isinstance(validate, tuple):
            validate = json.of_type(validate, optional=optional)
        elif not callable(validate):
            validate = json.default(validate)

        value = self.get(key, ())
        try:
            value = validate(value)
        except (TypeError, ValueError) as exc:
            message = Message if self.message is None else self.message
            err = str(exc)
            if not err.startswith("["):
                err = " " + err
            raise message.isnt_valid("{0}{1}", json.repr(key), err)
        return value

    def _invalid_if_no_key(func):
        def wrap(self, key, *args, **kwargs):
            try:
                return func(self, key, *args, **kwargs)
            except KeyError:
                message = Message if self.message is None else self.message
                raise message.isnt_valid("missing property {0!r}", key)

        return wrap

    __getitem__ = _invalid_if_no_key(collections.OrderedDict.__getitem__)
    __delitem__ = _invalid_if_no_key(collections.OrderedDict.__delitem__)
    pop = _invalid_if_no_key(collections.OrderedDict.pop)

    del _invalid_if_no_key


def _payload(value):
    """JSON validator for message payload.

    If that value is missing or null, it is treated as if it were {}.
    """

    if value is not None and value != ():
        if isinstance(value, dict):  # can be int, str, list...
            assert isinstance(value, MessageDict)
        return value

    # Missing payload. Construct a dummy MessageDict, and make it look like it was
    # deserialized. See JsonMessageChannel._parse_incoming_message for why it needs
    # to have associate_with().

    def associate_with(message):
        value.message = message

    value = MessageDict(None)
    value.associate_with = associate_with
    return value


class Message(object):
    """Represents a fully parsed incoming or outgoing message.

    https://microsoft.github.io/debug-adapter-protocol/specification#protocolmessage
    """

    def __init__(self, channel, seq, json=None):
        self.channel = channel

        self.seq = seq
        """Sequence number of the message in its channel.

        This can be None for synthesized Responses.
        """

        self.json = json
        """For incoming messages, the MessageDict containing raw JSON from which
        this message was originally parsed.
        """

    def __str__(self):
        return json.repr(self.json) if self.json is not None else repr(self)

    def describe(self):
        """A brief description of the message that is enough to identify it.

        Examples:
        '#1 request "launch" from IDE'
        '#2 response to #1 request "launch" from IDE'.
        """
        raise NotImplementedError

    @property
    def payload(self) -> MessageDict:
        """Payload of the message - self.body or self.arguments, depending on the
        message type.
        """
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        """Same as self.payload(...)."""
        return self.payload(*args, **kwargs)

    def __contains__(self, key):
        """Same as (key in self.payload)."""
        return key in self.payload

    def is_event(self, *event):
        """Returns True if this message is an Event of one of the specified types."""
        if not isinstance(self, Event):
            return False
        return event == () or self.event in event

    def is_request(self, *command):
        """Returns True if this message is a Request of one of the specified types."""
        if not isinstance(self, Request):
            return False
        return command == () or self.command in command

    def is_response(self, *command):
        """Returns True if this message is a Response to a request of one of the
        specified types.
        """
        if not isinstance(self, Response):
            return False
        return command == () or self.request.command in command

    def error(self, exc_type, format_string, *args, **kwargs):
        """Returns a new exception of the specified type from the point at which it is
        invoked, with the specified formatted message as the reason.

        The resulting exception will have its cause set to the Message object on which
        error() was called. Additionally, if that message is a Request, a failure
        response is immediately sent.
        """

        assert issubclass(exc_type, MessageHandlingError)

        silent = kwargs.pop("silent", False)
        reason = format_string.format(*args, **kwargs)
        exc = exc_type(reason, self, silent)  # will log it

        if isinstance(self, Request):
            self.respond(exc)
        return exc

    def isnt_valid(self, *args, **kwargs):
        """Same as self.error(InvalidMessageError, ...)."""
        return self.error(InvalidMessageError, *args, **kwargs)

    def cant_handle(self, *args, **kwargs):
        """Same as self.error(MessageHandlingError, ...)."""
        return self.error(MessageHandlingError, *args, **kwargs)


class Event(Message):
    """Represents an incoming event.

    https://microsoft.github.io/debug-adapter-protocol/specification#event

    It is guaranteed that body is a MessageDict associated with this Event, and so
    are all the nested dicts in it. If "body" was missing or null in JSON, body is
    an empty dict.

    To handle the event, JsonMessageChannel tries to find a handler for this event in
    JsonMessageChannel.handlers. Given event="X", if handlers.X_event exists, then it
    is the specific handler for this event. Otherwise, handlers.event must exist, and
    it is the generic handler for this event. A missing handler is a fatal error.

    No further incoming messages are processed until the handler returns, except for
    responses to requests that have wait_for_response() invoked on them.

    To report failure to handle the event, the handler must raise an instance of
    MessageHandlingError that applies_to() the Event object it was handling. Any such
    failure is logged, after which the message loop moves on to the next message.

    Helper methods Message.isnt_valid() and Message.cant_handle() can be used to raise
    the appropriate exception type that applies_to() the Event object.
    """

    def __init__(self, channel, seq, event, body, json=None):
        super().__init__(channel, seq, json)

        self.event = event

        if isinstance(body, MessageDict) and hasattr(body, "associate_with"):
            body.associate_with(self)
        self.body = body

    def describe(self):
        return f"#{self.seq} event {json.repr(self.event)} from {self.channel}"

    @property
    def payload(self):
        return self.body

    @staticmethod
    def _parse(channel, message_dict):
        seq = message_dict("seq", int)
        event = message_dict("event", str)
        body = message_dict("body", _payload)
        message = Event(channel, seq, event, body, json=message_dict)
        channel._enqueue_handlers(message, message._handle)

    def _handle(self):
        channel = self.channel
        handler = channel._get_handler_for("event", self.event)
        try:
            try:
                result = handler(self)
                assert (
                    result is None
                ), f"Handler {util.srcnameof(handler)} tried to respond to {self.describe()}."
            except MessageHandlingError as exc:
                if not exc.applies_to(self):
                    raise
                log.error(
                    "Handler {0}\ncouldn't handle {1}:\n{2}",
                    util.srcnameof(handler),
                    self.describe(),
                    str(exc),
                )
        except Exception:
            log.reraise_exception(
                "Handler {0}\ncouldn't handle {1}:",
                util.srcnameof(handler),
                self.describe(),
            )


NO_RESPONSE = object()
"""Can be returned from a request handler in lieu of the response body, to indicate
that no response is to be sent.

Request.respond() must be invoked explicitly at some later point to provide a response.
"""


class Request(Message):
    """Represents an incoming or an outgoing request.

    Incoming requests are represented directly by instances of this class.

    Outgoing requests are represented by instances of OutgoingRequest, which provides
    additional functionality to handle responses.

    For incoming requests, it is guaranteed that arguments is a MessageDict associated
    with this Request, and so are all the nested dicts in it. If "arguments" was missing
    or null in JSON, arguments is an empty dict.

    To handle the request, JsonMessageChannel tries to find a handler for this request
    in JsonMessageChannel.handlers. Given command="X", if handlers.X_request exists,
    then it is the specific handler for this request. Otherwise, handlers.request must
    exist, and it is the generic handler for this request. A missing handler is a fatal
    error.

    The handler is then invoked with the Request object as its sole argument.

    If the handler itself invokes respond() on the Request at any point, then it must
    not return any value.

    Otherwise, if the handler returns NO_RESPONSE, no response to the request is sent.
    It must be sent manually at some later point via respond().

    Otherwise, a response to the request is sent with the returned value as the body.

    To fail the request, the handler can return an instance of MessageHandlingError,
    or respond() with one, or raise one such that it applies_to() the Request object
    being handled.

    Helper methods Message.isnt_valid() and Message.cant_handle() can be used to raise
    the appropriate exception type that applies_to() the Request object.
    """

    def __init__(self, channel, seq, command, arguments, json=None):
        super().__init__(channel, seq, json)

        self.command = command

        if isinstance(arguments, MessageDict) and hasattr(arguments, "associate_with"):
            arguments.associate_with(self)
        self.arguments = arguments

        self.response = None
        """Response to this request.

        For incoming requests, it is set as soon as the request handler returns.

        For outgoing requests, it is set as soon as the response is received, and
        before self._handle_response is invoked.
        """

    def describe(self):
        return f"#{self.seq} request {json.repr(self.command)} from {self.channel}"

    @property
    def payload(self):
        return self.arguments

    def respond(self, body):
        assert self.response is None
        d = {"type": "response", "request_seq": self.seq, "command": self.command}

        if isinstance(body, Exception):
            d["success"] = False
            d["message"] = str(body)
        else:
            d["success"] = True
            if body is not None and body != {}:
                d["body"] = body

        with self.channel._send_message(d) as seq:
            pass
        self.response = Response(self.channel, seq, self, body)

    @staticmethod
    def _parse(channel, message_dict):
        seq = message_dict("seq", int)
        command = message_dict("command", str)
        arguments = message_dict("arguments", _payload)
        message = Request(channel, seq, command, arguments, json=message_dict)
        channel._enqueue_handlers(message, message._handle)

    def _handle(self):
        channel = self.channel
        handler = channel._get_handler_for("request", self.command)
        try:
            try:
                result = handler(self)
            except MessageHandlingError as exc:
                if not exc.applies_to(self):
                    raise
                result = exc
                log.error(
                    "Handler {0}\ncouldn't handle {1}:\n{2}",
                    util.srcnameof(handler),
                    self.describe(),
                    str(exc),
                )

            if result is NO_RESPONSE:
                assert self.response is None, (
                    "Handler {0} for {1} must not return NO_RESPONSE if it has already "
                    "invoked request.respond().".format(
                        util.srcnameof(handler), self.describe()
                    )
                )
            elif self.response is not None:
                assert result is None or result is self.response.body, (
                    "Handler {0} for {1} must not return a response body if it has "
                    "already invoked request.respond().".format(
                        util.srcnameof(handler), self.describe()
                    )
                )
            else:
                assert result is not None, (
                    "Handler {0} for {1} must either call request.respond() before it "
                    "returns, or return the response body, or return NO_RESPONSE.".format(
                        util.srcnameof(handler), self.describe()
                    )
                )
                try:
                    self.respond(result)
                except NoMoreMessages:
                    log.warning(
                        "Channel was closed before the response from handler {0} to {1} could be sent",
                        util.srcnameof(handler),
                        self.describe(),
                    )

        except Exception:
            log.reraise_exception(
                "Handler {0}\ncouldn't handle {1}:",
                util.srcnameof(handler),
                self.describe(),
            )


class OutgoingRequest(Request):
    """Represents an outgoing request, for which it is possible to wait for a
    response to be received, and register a response handler.
    """

    _parse = _handle = None

    def __init__(self, channel, seq, command, arguments):
        super().__init__(channel, seq, command, arguments)
        self._response_handlers = []

    def describe(self):
        return f"{self.seq} request {json.repr(self.command)} to {self.channel}"

    def wait_for_response(self, raise_if_failed=True):
        """Waits until a response is received for this request, records the Response
        object for it in self.response, and returns response.body.

        If no response was received from the other party before the channel closed,
        self.response is a synthesized Response with body=NoMoreMessages().

        If raise_if_failed=True and response.success is False, raises response.body
        instead of returning.
        """

        with self.channel:
            while self.response is None:
                self.channel._handlers_enqueued.wait()

        if raise_if_failed and not self.response.success:
            raise self.response.body
        return self.response.body

    def on_response(self, response_handler):
        """Registers a handler to invoke when a response is received for this request.
        The handler is invoked with Response as its sole argument.

        If response has already been received, invokes the handler immediately.

        It is guaranteed that self.response is set before the handler is invoked.
        If no response was received from the other party before the channel closed,
        self.response is a dummy Response with body=NoMoreMessages().

        The handler is always invoked asynchronously on an unspecified background
        thread - thus, the caller of on_response() can never be blocked or deadlocked
        by the handler.

        No further incoming messages are processed until the handler returns, except for
        responses to requests that have wait_for_response() invoked on them.
        """

        with self.channel:
            self._response_handlers.append(response_handler)
            self._enqueue_response_handlers()

    def _enqueue_response_handlers(self):
        response = self.response
        if response is None:
            # Response._parse() will submit the handlers when response is received.
            return

        def run_handlers():
            for handler in handlers:
                try:
                    try:
                        handler(response)
                    except MessageHandlingError as exc:
                        if not exc.applies_to(response):
                            raise
                        log.error(
                            "Handler {0}\ncouldn't handle {1}:\n{2}",
                            util.srcnameof(handler),
                            response.describe(),
                            str(exc),
                        )
                except Exception:
                    log.reraise_exception(
                        "Handler {0}\ncouldn't handle {1}:",
                        util.srcnameof(handler),
                        response.describe(),
                    )

        handlers = self._response_handlers[:]
        self.channel._enqueue_handlers(response, run_handlers)
        del self._response_handlers[:]


class Response(Message):
    """Represents an incoming or an outgoing response to a Request.

    https://microsoft.github.io/debug-adapter-protocol/specification#response

    error_message corresponds to "message" in JSON, and is renamed for clarity.

    If success is False, body is None. Otherwise, it is a MessageDict associated
    with this Response, and so are all the nested dicts in it. If "body" was missing
    or null in JSON, body is an empty dict.

    If this is a response to an outgoing request, it will be handled by the handler
    registered via self.request.on_response(), if any.

    Regardless of whether there is such a handler, OutgoingRequest.wait_for_response()
    can also be used to retrieve and handle the response. If there is a handler, it is
    executed before wait_for_response() returns.

    No further incoming messages are processed until the handler returns, except for
    responses to requests that have wait_for_response() invoked on them.

    To report failure to handle the event, the handler must raise an instance of
    MessageHandlingError that applies_to() the Response object it was handling. Any
    such failure is logged, after which the message loop moves on to the next message.

    Helper methods Message.isnt_valid() and Message.cant_handle() can be used to raise
    the appropriate exception type that applies_to() the Response object.
    """

    def __init__(self, channel, seq, request, body, json=None):
        super().__init__(channel, seq, json)

        self.request = request
        """The request to which this is the response."""

        if isinstance(body, MessageDict) and hasattr(body, "associate_with"):
            body.associate_with(self)
        self.body = body
        """Body of the response if the request was successful, or an instance
        of some class derived from Exception it it was not.

        If a response was received from the other side, but request failed, it is an
        instance of MessageHandlingError containing the received error message. If the
        error message starts with InvalidMessageError.PREFIX, then it's an instance of
        the InvalidMessageError specifically, and that prefix is stripped.

        If no response was received from the other party before the channel closed,
        it is an instance of NoMoreMessages.
        """

    def describe(self):
        return f"#{self.seq} response to {self.request.describe()}"

    @property
    def payload(self):
        return self.body

    @property
    def success(self):
        """Whether the request succeeded or not."""
        return not isinstance(self.body, Exception)

    @property
    def result(self):
        """Result of the request. Returns the value of response.body, unless it
        is an exception, in which case it is raised instead.
        """
        if self.success:
            return self.body
        else:
            raise self.body

    @staticmethod
    def _parse(channel, message_dict, body=None):
        seq = message_dict("seq", int) if (body is None) else None
        request_seq = message_dict("request_seq", int)
        command = message_dict("command", str)
        success = message_dict("success", bool)
        if body is None:
            if success:
                body = message_dict("body", _payload)
            else:
                error_message = message_dict("message", str)
                exc_type = MessageHandlingError
                if error_message.startswith(InvalidMessageError.PREFIX):
                    error_message = error_message[len(InvalidMessageError.PREFIX) :]
                    exc_type = InvalidMessageError
                body = exc_type(error_message, silent=True)

        try:
            with channel:
                request = channel._sent_requests.pop(request_seq)
                known_request = True
        except KeyError:
            # Synthetic Request that only has seq and command as specified in response
            # JSON, for error reporting purposes.
            request = OutgoingRequest(channel, request_seq, command, "<unknown>")
            known_request = False

        if not success:
            body.cause = request

        response = Response(channel, seq, request, body, json=message_dict)

        with channel:
            request.response = response
            request._enqueue_response_handlers()

        if known_request:
            return response
        else:
            raise response.isnt_valid(
                "request_seq={0} does not match any known request", request_seq
            )


class Disconnect(Message):
    """A dummy message used to represent disconnect. It's always the last message
    received from any channel.
    """

    def __init__(self, channel):
        super().__init__(channel, None)

    def describe(self):
        return f"disconnect from {self.channel}"


class MessageHandlingError(Exception):
    """Indicates that a message couldn't be handled for some reason.

    If the reason is a contract violation - i.e. the message that was handled did not
    conform to the protocol specification - InvalidMessageError, which is a subclass,
    should be used instead.

    If any message handler raises an exception not derived from this class, it will
    escape the message loop unhandled, and terminate the process.

    If any message handler raises this exception, but applies_to(message) is False, it
    is treated as if it was a generic exception, as desribed above. Thus, if a request
    handler issues another request of its own, and that one fails, the failure is not
    silently propagated. However, a request that is delegated via Request.delegate()
    will also propagate failures back automatically. For manual propagation, catch the
    exception, and call exc.propagate().

    If any event handler raises this exception, and applies_to(event) is True, the
    exception is silently swallowed by the message loop.

    If any request handler raises this exception, and applies_to(request) is True, the
    exception is silently swallowed by the message loop, and a failure response is sent
    with "message" set to str(reason).

    Note that, while errors are not logged when they're swallowed by the message loop,
    by that time they have already been logged by their __init__ (when instantiated).
    """

    def __init__(self, reason, cause=None, silent=False):
        """Creates a new instance of this class, and immediately logs the exception.

        Message handling errors are logged immediately unless silent=True, so that the
        precise context in which they occured can be determined from the surrounding
        log entries.
        """

        self.reason = reason
        """Why it couldn't be handled. This can be any object, but usually it's either
        str or Exception.
        """

        assert cause is None or isinstance(cause, Message)
        self.cause = cause
        """The Message object for the message that couldn't be handled. For responses
        to unknown requests, this is a synthetic Request.
        """

        if not silent:
            try:
                raise self
            except MessageHandlingError:
                log.swallow_exception()

    def __hash__(self):
        return hash((self.reason, id(self.cause)))

    def __eq__(self, other):
        if not isinstance(other, MessageHandlingError):
            return NotImplemented
        if type(self) is not type(other):
            return NotImplemented
        if self.reason != other.reason:
            return False
        if self.cause is not None and other.cause is not None:
            if self.cause.seq != other.cause.seq:
                return False
        return True

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return str(self.reason)

    def __repr__(self):
        s = type(self).__name__
        if self.cause is None:
            s += f"reason={self.reason!r})"
        else:
            s += f"channel={self.cause.channel.name!r}, cause={self.cause.seq!r}, reason={self.reason!r})"
        return s

    def applies_to(self, message):
        """Whether this MessageHandlingError can be treated as a reason why the
        handling of message failed.

        If self.cause is None, this is always true.

        If self.cause is not None, this is only true if cause is message.
        """
        return self.cause is None or self.cause is message

    def propagate(self, new_cause):
        """Propagates this error, raising a new instance of the same class with the
        same reason, but a different cause.
        """
        raise type(self)(self.reason, new_cause, silent=True)


class InvalidMessageError(MessageHandlingError):
    """Indicates that an incoming message did not follow the protocol specification -
    for example, it was missing properties that are required, or the message itself
    is not allowed in the current state.

    Raised by MessageDict in lieu of KeyError for missing keys.
    """

    PREFIX = "Invalid message: "
    """Automatically prepended to the "message" property in JSON responses, when the
    handler raises InvalidMessageError.

    If a failed response has "message" property that starts with this prefix, it is
    reported as InvalidMessageError rather than MessageHandlingError.
    """

    def __str__(self):
        return InvalidMessageError.PREFIX + str(self.reason)


class JsonMessageChannel(object):
    """Implements a JSON message channel on top of a raw JSON message stream, with
    support for DAP requests, responses, and events.

    The channel can be locked for exclusive use via the with-statement::

        with channel:
            channel.send_request(...)
            # No interleaving messages can be sent here from other threads.
            channel.send_event(...)
    """

    def __init__(self, stream, handlers=None, name=None):
        self.stream = stream
        self.handlers = handlers
        self.name = name if name is not None else stream.name
        self.started = False
        self._lock = threading.RLock()
        self._closed = False
        self._seq_iter = itertools.count(1)
        self._sent_requests = {}  # {seq: Request}
        self._handler_queue = []  # [(what, handler)]
        self._handlers_enqueued = threading.Condition(self._lock)
        self._handler_thread = None
        self._parser_thread = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._lock.release()

    def close(self):
        """Closes the underlying stream.

        This does not immediately terminate any handlers that are already executing,
        but they will be unable to respond. No new request or event handlers will
        execute after this method is called, even for messages that have already been
        received. However, response handlers will continue to executed for any request
        that is still pending, as will any handlers registered via on_response().
        """
        with self:
            if not self._closed:
                self._closed = True
                self.stream.close()

    def start(self):
        """Starts a message loop which parses incoming messages and invokes handlers
        for them on a background thread, until the channel is closed.

        Incoming messages, including responses to requests, will not be processed at
        all until this is invoked.
        """

        assert not self.started
        self.started = True

        self._parser_thread = threading.Thread(
            target=self._parse_incoming_messages, name=f"{self} message parser"
        )

        hide_thread_from_debugger(self._parser_thread)
        self._parser_thread.daemon = True
        self._parser_thread.start()

    def wait(self):
        """Waits for the message loop to terminate, and for all enqueued Response
        message handlers to finish executing.
        """
        parser_thread = self._parser_thread
        try:
            if parser_thread is not None:
                parser_thread.join()
        except AssertionError:
            log.debug("Handled error joining parser thread.")
        try:
            handler_thread = self._handler_thread
            if handler_thread is not None:
                handler_thread.join()
        except AssertionError:
            log.debug("Handled error joining handler thread.")

    # Order of keys for _prettify() - follows the order of properties in
    # https://microsoft.github.io/debug-adapter-protocol/specification
    _prettify_order = (
        "seq",
        "type",
        "request_seq",
        "success",
        "command",
        "event",
        "message",
        "arguments",
        "body",
        "error",
    )

    def _prettify(self, message_dict):
        """Reorders items in a MessageDict such that it is more readable."""
        for key in self._prettify_order:
            if key not in message_dict:
                continue
            value = message_dict[key]
            del message_dict[key]
            message_dict[key] = value

    @contextlib.contextmanager
    def _send_message(self, message):
        """Sends a new message to the other party.

        Generates a new sequence number for the message, and provides it to the
        caller before the message is sent, using the context manager protocol::

            with send_message(...) as seq:
                # The message hasn't been sent yet.
                ...
            # Now the message has been sent.

        Safe to call concurrently for the same channel from different threads.
        """

        assert "seq" not in message
        with self:
            seq = next(self._seq_iter)

        message = MessageDict(None, message)
        message["seq"] = seq
        self._prettify(message)

        with self:
            yield seq
            self.stream.write_json(message)

    def send_request(self, command, arguments=None, on_before_send=None):
        """Sends a new request, and returns the OutgoingRequest object for it.

        If arguments is None or {}, "arguments" will be omitted in JSON.

        If on_before_send is not None, invokes on_before_send() with the request
        object as the sole argument, before the request actually gets sent.

        Does not wait for response - use OutgoingRequest.wait_for_response().

        Safe to call concurrently for the same channel from different threads.
        """

        d = {"type": "request", "command": command}
        if arguments is not None and arguments != {}:
            d["arguments"] = arguments

        with self._send_message(d) as seq:
            request = OutgoingRequest(self, seq, command, arguments)
            if on_before_send is not None:
                on_before_send(request)
            self._sent_requests[seq] = request
        return request

    def send_event(self, event, body=None):
        """Sends a new event.

        If body is None or {}, "body" will be omitted in JSON.

        Safe to call concurrently for the same channel from different threads.
        """

        d = {"type": "event", "event": event}
        if body is not None and body != {}:
            d["body"] = body

        with self._send_message(d):
            pass

    def request(self, *args, **kwargs):
        """Same as send_request(...).wait_for_response()"""
        return self.send_request(*args, **kwargs).wait_for_response()

    def propagate(self, message):
        """Sends a new message with the same type and payload.

        If it was a request, returns the new OutgoingRequest object for it.
        """
        assert message.is_request() or message.is_event()
        if message.is_request():
            return self.send_request(message.command, message.arguments)
        else:
            self.send_event(message.event, message.body)

    def delegate(self, message):
        """Like propagate(message).wait_for_response(), but will also propagate
        any resulting MessageHandlingError back.
        """
        try:
            result = self.propagate(message)
            if result.is_request():
                result = result.wait_for_response()
            return result
        except MessageHandlingError as exc:
            exc.propagate(message)

    def _parse_incoming_messages(self):
        log.debug("Starting message loop for channel {0}", self)
        try:
            while True:
                self._parse_incoming_message()

        except NoMoreMessages as exc:
            log.debug("Exiting message loop for channel {0}: {1}", self, exc)
            with self:
                # Generate dummy responses for all outstanding requests.
                err_message = str(exc)

                # Response._parse() will remove items from _sent_requests, so
                # make a snapshot before iterating.
                sent_requests = list(self._sent_requests.values())

                for request in sent_requests:
                    response_json = MessageDict(
                        None,
                        {
                            "seq": -1,
                            "request_seq": request.seq,
                            "command": request.command,
                            "success": False,
                            "message": err_message,
                        },
                    )
                    Response._parse(self, response_json, body=exc)
                assert not len(self._sent_requests)

                self._enqueue_handlers(Disconnect(self), self._handle_disconnect)
                self.close()

    _message_parsers = {
        "event": Event._parse,
        "request": Request._parse,
        "response": Response._parse,
    }

    def _parse_incoming_message(self):
        """Reads incoming messages, parses them, and puts handlers into the queue
        for _run_handlers() to invoke, until the channel is closed.
        """

        # Set up a dedicated decoder for this message, to create MessageDict instances
        # for all JSON objects, and track them so that they can be later wired up to
        # the Message they belong to, once it is instantiated.
        def object_hook(d):
            d = MessageDict(None, d)
            if "seq" in d:
                self._prettify(d)
            d.associate_with = associate_with
            message_dicts.append(d)
            return d

        # A hack to work around circular dependency between messages, and instances of
        # MessageDict in their payload. We need to set message for all of them, but it
        # cannot be done until the actual Message is created - which happens after the
        # dicts are created during deserialization.
        #
        # So, upon deserialization, every dict in the message payload gets a method
        # that can be called to set MessageDict.message for *all* dicts belonging to
        # that message. This method can then be invoked on the top-level dict by the
        # parser, after it has parsed enough of the dict to create the appropriate
        # instance of Event, Request, or Response for this message.
        def associate_with(message):
            for d in message_dicts:
                d.message = message
                del d.associate_with

        message_dicts = []
        decoder = self.stream.json_decoder_factory(object_hook=object_hook)
        message_dict = self.stream.read_json(decoder)
        assert isinstance(message_dict, MessageDict)  # make sure stream used decoder

        msg_type = message_dict("type", json.enum("event", "request", "response"))
        parser = self._message_parsers[msg_type]
        try:
            parser(self, message_dict)
        except InvalidMessageError as exc:
            log.error(
                "Failed to parse message in channel {0}: {1} in:\n{2}",
                self,
                str(exc),
                json.repr(message_dict),
            )
        except Exception as exc:
            if isinstance(exc, NoMoreMessages) and exc.stream is self.stream:
                raise
            log.swallow_exception(
                "Fatal error in channel {0} while parsing:\n{1}",
                self,
                json.repr(message_dict),
            )
            os._exit(1)

    def _enqueue_handlers(self, what, *handlers):
        """Enqueues handlers for _run_handlers() to run.

        `what` is the Message being handled, and is used for logging purposes.

        If the background thread with _run_handlers() isn't running yet, starts it.
        """

        with self:
            self._handler_queue.extend((what, handler) for handler in handlers)
            self._handlers_enqueued.notify_all()

            # If there is anything to handle, but there's no handler thread yet,
            # spin it up. This will normally happen only once, on the first call
            # to _enqueue_handlers(), and that thread will run all the handlers
            # for parsed messages. However, this can also happen is somebody calls
            # Request.on_response() - possibly concurrently from multiple threads -
            # after the channel has already been closed, and the initial handler
            # thread has exited. In this case, we spin up a new thread just to run
            # the enqueued response handlers, and it will exit as soon as it's out
            # of handlers to run.
            if len(self._handler_queue) and self._handler_thread is None:
                self._handler_thread = threading.Thread(
                    target=self._run_handlers,
                    name=f"{self} message handler",
                )
                hide_thread_from_debugger(self._handler_thread)
                self._handler_thread.start()

    def _run_handlers(self):
        """Runs enqueued handlers until the channel is closed, or until the handler
        queue is empty once the channel is closed.
        """

        while True:
            with self:
                closed = self._closed
            if closed:
                # Wait for the parser thread to wrap up and enqueue any remaining
                # handlers, if it is still running.
                self._parser_thread.join()
                # From this point on, _enqueue_handlers() can only get called
                # from Request.on_response().

            with self:
                if not closed and not len(self._handler_queue):
                    # Wait for something to process.
                    self._handlers_enqueued.wait()

                # Make a snapshot before releasing the lock.
                handlers = self._handler_queue[:]
                del self._handler_queue[:]

                if closed and not len(handlers):
                    # Nothing to process, channel is closed, and parser thread is
                    # not running anymore - time to quit! If Request.on_response()
                    # needs to call _enqueue_handlers() later, it will spin up
                    # a new handler thread.
                    self._handler_thread = None
                    return

            for what, handler in handlers:
                # If the channel is closed, we don't want to process any more events
                # or requests - only responses and the final disconnect handler. This
                # is to guarantee that if a handler calls close() on its own channel,
                # the corresponding request or event is the last thing to be processed.
                if closed and handler in (Event._handle, Request._handle):
                    continue

                with log.prefixed("/handling {0}/\n", what.describe()):
                    try:
                        handler()
                    except Exception:
                        # It's already logged by the handler, so just fail fast.
                        self.close()
                        os._exit(1)

    def _get_handler_for(self, type, name):
        """Returns the handler for a message of a given type."""

        with self:
            handlers = self.handlers

        for handler_name in (name + "_" + type, type):
            try:
                return getattr(handlers, handler_name)
            except AttributeError:
                continue

        raise AttributeError(
            "handler object {0} for channel {1} has no handler for {2} {3!r}".format(
                util.srcnameof(handlers),
                self,
                type,
                name,
            )
        )

    def _handle_disconnect(self):
        handler = getattr(self.handlers, "disconnect", lambda: None)
        try:
            handler()
        except Exception:
            log.reraise_exception(
                "Handler {0}\ncouldn't handle disconnect from {1}:",
                util.srcnameof(handler),
                self,
            )


class MessageHandlers(object):
    """A simple delegating message handlers object for use with JsonMessageChannel.
    For every argument provided, the object gets an attribute with the corresponding
    name and value.
    """

    def __init__(self, **kwargs):
        for name, func in kwargs.items():
            setattr(self, name, func)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_arrayterator.py ===
from functools import reduce
from operator import mul

import numpy as np
from numpy.lib import Arrayterator
from numpy.random import randint
from numpy.testing import assert_


def test():
    np.random.seed(np.arange(10))

    # Create a random array
    ndims = randint(5) + 1
    shape = tuple(randint(10) + 1 for dim in range(ndims))
    els = reduce(mul, shape)
    a = np.arange(els)
    a.shape = shape

    buf_size = randint(2 * els)
    b = Arrayterator(a, buf_size)

    # Check that each block has at most ``buf_size`` elements
    for block in b:
        assert_(len(block.flat) <= (buf_size or els))

    # Check that all elements are iterated correctly
    assert_(list(b.flat) == list(a.flat))

    # Slice arrayterator
    start = [randint(dim) for dim in shape]
    stop = [randint(dim) + 1 for dim in shape]
    step = [randint(dim) + 1 for dim in shape]
    slice_ = tuple(slice(*t) for t in zip(start, stop, step))
    c = b[slice_]
    d = a[slice_]

    # Check that each block has at most ``buf_size`` elements
    for block in c:
        assert_(len(block.flat) <= (buf_size or els))

    # Check that the arrayterator is sliced correctly
    assert_(np.all(c.__array__() == d))

    # Check that all elements are iterated correctly
    assert_(list(c.flat) == list(d.flat))

# === NexusCore/openenv\Lib\site-packages\numpy\_core\einsumfunc.py ===
"""
Implementation of optimized einsum.

"""
import itertools
import operator

from numpy._core.multiarray import c_einsum
from numpy._core.numeric import asanyarray, tensordot
from numpy._core.overrides import array_function_dispatch

__all__ = ['einsum', 'einsum_path']

# importing string for string.ascii_letters would be too slow
# the first import before caching has been measured to take 800 µs (#23777)
# imports begin with uppercase to mimic ASCII values to avoid sorting issues
einsum_symbols = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
einsum_symbols_set = set(einsum_symbols)


def _flop_count(idx_contraction, inner, num_terms, size_dictionary):
    """
    Computes the number of FLOPS in the contraction.

    Parameters
    ----------
    idx_contraction : iterable
        The indices involved in the contraction
    inner : bool
        Does this contraction require an inner product?
    num_terms : int
        The number of terms in a contraction
    size_dictionary : dict
        The size of each of the indices in idx_contraction

    Returns
    -------
    flop_count : int
        The total number of FLOPS required for the contraction.

    Examples
    --------

    >>> _flop_count('abc', False, 1, {'a': 2, 'b':3, 'c':5})
    30

    >>> _flop_count('abc', True, 2, {'a': 2, 'b':3, 'c':5})
    60

    """

    overall_size = _compute_size_by_dict(idx_contraction, size_dictionary)
    op_factor = max(1, num_terms - 1)
    if inner:
        op_factor += 1

    return overall_size * op_factor

def _compute_size_by_dict(indices, idx_dict):
    """
    Computes the product of the elements in indices based on the dictionary
    idx_dict.

    Parameters
    ----------
    indices : iterable
        Indices to base the product on.
    idx_dict : dictionary
        Dictionary of index sizes

    Returns
    -------
    ret : int
        The resulting product.

    Examples
    --------
    >>> _compute_size_by_dict('abbc', {'a': 2, 'b':3, 'c':5})
    90

    """
    ret = 1
    for i in indices:
        ret *= idx_dict[i]
    return ret


def _find_contraction(positions, input_sets, output_set):
    """
    Finds the contraction for a given set of input and output sets.

    Parameters
    ----------
    positions : iterable
        Integer positions of terms used in the contraction.
    input_sets : list
        List of sets that represent the lhs side of the einsum subscript
    output_set : set
        Set that represents the rhs side of the overall einsum subscript

    Returns
    -------
    new_result : set
        The indices of the resulting contraction
    remaining : list
        List of sets that have not been contracted, the new set is appended to
        the end of this list
    idx_removed : set
        Indices removed from the entire contraction
    idx_contraction : set
        The indices used in the current contraction

    Examples
    --------

    # A simple dot product test case
    >>> pos = (0, 1)
    >>> isets = [set('ab'), set('bc')]
    >>> oset = set('ac')
    >>> _find_contraction(pos, isets, oset)
    ({'a', 'c'}, [{'a', 'c'}], {'b'}, {'a', 'b', 'c'})

    # A more complex case with additional terms in the contraction
    >>> pos = (0, 2)
    >>> isets = [set('abd'), set('ac'), set('bdc')]
    >>> oset = set('ac')
    >>> _find_contraction(pos, isets, oset)
    ({'a', 'c'}, [{'a', 'c'}, {'a', 'c'}], {'b', 'd'}, {'a', 'b', 'c', 'd'})
    """

    idx_contract = set()
    idx_remain = output_set.copy()
    remaining = []
    for ind, value in enumerate(input_sets):
        if ind in positions:
            idx_contract |= value
        else:
            remaining.append(value)
            idx_remain |= value

    new_result = idx_remain & idx_contract
    idx_removed = (idx_contract - new_result)
    remaining.append(new_result)

    return (new_result, remaining, idx_removed, idx_contract)


def _optimal_path(input_sets, output_set, idx_dict, memory_limit):
    """
    Computes all possible pair contractions, sieves the results based
    on ``memory_limit`` and returns the lowest cost path. This algorithm
    scales factorial with respect to the elements in the list ``input_sets``.

    Parameters
    ----------
    input_sets : list
        List of sets that represent the lhs side of the einsum subscript
    output_set : set
        Set that represents the rhs side of the overall einsum subscript
    idx_dict : dictionary
        Dictionary of index sizes
    memory_limit : int
        The maximum number of elements in a temporary array

    Returns
    -------
    path : list
        The optimal contraction order within the memory limit constraint.

    Examples
    --------
    >>> isets = [set('abd'), set('ac'), set('bdc')]
    >>> oset = set()
    >>> idx_sizes = {'a': 1, 'b':2, 'c':3, 'd':4}
    >>> _optimal_path(isets, oset, idx_sizes, 5000)
    [(0, 2), (0, 1)]
    """

    full_results = [(0, [], input_sets)]
    for iteration in range(len(input_sets) - 1):
        iter_results = []

        # Compute all unique pairs
        for curr in full_results:
            cost, positions, remaining = curr
            for con in itertools.combinations(
                range(len(input_sets) - iteration), 2
            ):

                # Find the contraction
                cont = _find_contraction(con, remaining, output_set)
                new_result, new_input_sets, idx_removed, idx_contract = cont

                # Sieve the results based on memory_limit
                new_size = _compute_size_by_dict(new_result, idx_dict)
                if new_size > memory_limit:
                    continue

                # Build (total_cost, positions, indices_remaining)
                total_cost = cost + _flop_count(
                    idx_contract, idx_removed, len(con), idx_dict
                )
                new_pos = positions + [con]
                iter_results.append((total_cost, new_pos, new_input_sets))

        # Update combinatorial list, if we did not find anything return best
        # path + remaining contractions
        if iter_results:
            full_results = iter_results
        else:
            path = min(full_results, key=lambda x: x[0])[1]
            path += [tuple(range(len(input_sets) - iteration))]
            return path

    # If we have not found anything return single einsum contraction
    if len(full_results) == 0:
        return [tuple(range(len(input_sets)))]

    path = min(full_results, key=lambda x: x[0])[1]
    return path

def _parse_possible_contraction(
        positions, input_sets, output_set, idx_dict,
        memory_limit, path_cost, naive_cost
    ):
    """Compute the cost (removed size + flops) and resultant indices for
    performing the contraction specified by ``positions``.

    Parameters
    ----------
    positions : tuple of int
        The locations of the proposed tensors to contract.
    input_sets : list of sets
        The indices found on each tensors.
    output_set : set
        The output indices of the expression.
    idx_dict : dict
        Mapping of each index to its size.
    memory_limit : int
        The total allowed size for an intermediary tensor.
    path_cost : int
        The contraction cost so far.
    naive_cost : int
        The cost of the unoptimized expression.

    Returns
    -------
    cost : (int, int)
        A tuple containing the size of any indices removed, and the flop cost.
    positions : tuple of int
        The locations of the proposed tensors to contract.
    new_input_sets : list of sets
        The resulting new list of indices if this proposed contraction
        is performed.

    """

    # Find the contraction
    contract = _find_contraction(positions, input_sets, output_set)
    idx_result, new_input_sets, idx_removed, idx_contract = contract

    # Sieve the results based on memory_limit
    new_size = _compute_size_by_dict(idx_result, idx_dict)
    if new_size > memory_limit:
        return None

    # Build sort tuple
    old_sizes = (
        _compute_size_by_dict(input_sets[p], idx_dict) for p in positions
    )
    removed_size = sum(old_sizes) - new_size

    # NB: removed_size used to be just the size of any removed indices i.e.:
    #     helpers.compute_size_by_dict(idx_removed, idx_dict)
    cost = _flop_count(idx_contract, idx_removed, len(positions), idx_dict)
    sort = (-removed_size, cost)

    # Sieve based on total cost as well
    if (path_cost + cost) > naive_cost:
        return None

    # Add contraction to possible choices
    return [sort, positions, new_input_sets]


def _update_other_results(results, best):
    """Update the positions and provisional input_sets of ``results``
    based on performing the contraction result ``best``. Remove any
    involving the tensors contracted.

    Parameters
    ----------
    results : list
        List of contraction results produced by
        ``_parse_possible_contraction``.
    best : list
        The best contraction of ``results`` i.e. the one that
        will be performed.

    Returns
    -------
    mod_results : list
        The list of modified results, updated with outcome of
        ``best`` contraction.
    """

    best_con = best[1]
    bx, by = best_con
    mod_results = []

    for cost, (x, y), con_sets in results:

        # Ignore results involving tensors just contracted
        if x in best_con or y in best_con:
            continue

        # Update the input_sets
        del con_sets[by - int(by > x) - int(by > y)]
        del con_sets[bx - int(bx > x) - int(bx > y)]
        con_sets.insert(-1, best[2][-1])

        # Update the position indices
        mod_con = x - int(x > bx) - int(x > by), y - int(y > bx) - int(y > by)
        mod_results.append((cost, mod_con, con_sets))

    return mod_results

def _greedy_path(input_sets, output_set, idx_dict, memory_limit):
    """
    Finds the path by contracting the best pair until the input list is
    exhausted. The best pair is found by minimizing the tuple
    ``(-prod(indices_removed), cost)``.  What this amounts to is prioritizing
    matrix multiplication or inner product operations, then Hadamard like
    operations, and finally outer operations. Outer products are limited by
    ``memory_limit``. This algorithm scales cubically with respect to the
    number of elements in the list ``input_sets``.

    Parameters
    ----------
    input_sets : list
        List of sets that represent the lhs side of the einsum subscript
    output_set : set
        Set that represents the rhs side of the overall einsum subscript
    idx_dict : dictionary
        Dictionary of index sizes
    memory_limit : int
        The maximum number of elements in a temporary array

    Returns
    -------
    path : list
        The greedy contraction order within the memory limit constraint.

    Examples
    --------
    >>> isets = [set('abd'), set('ac'), set('bdc')]
    >>> oset = set()
    >>> idx_sizes = {'a': 1, 'b':2, 'c':3, 'd':4}
    >>> _greedy_path(isets, oset, idx_sizes, 5000)
    [(0, 2), (0, 1)]
    """

    # Handle trivial cases that leaked through
    if len(input_sets) == 1:
        return [(0,)]
    elif len(input_sets) == 2:
        return [(0, 1)]

    # Build up a naive cost
    contract = _find_contraction(
        range(len(input_sets)), input_sets, output_set
    )
    idx_result, new_input_sets, idx_removed, idx_contract = contract
    naive_cost = _flop_count(
        idx_contract, idx_removed, len(input_sets), idx_dict
    )

    # Initially iterate over all pairs
    comb_iter = itertools.combinations(range(len(input_sets)), 2)
    known_contractions = []

    path_cost = 0
    path = []

    for iteration in range(len(input_sets) - 1):

        # Iterate over all pairs on the first step, only previously
        # found pairs on subsequent steps
        for positions in comb_iter:

            # Always initially ignore outer products
            if input_sets[positions[0]].isdisjoint(input_sets[positions[1]]):
                continue

            result = _parse_possible_contraction(
                positions, input_sets, output_set, idx_dict,
                memory_limit, path_cost, naive_cost
            )
            if result is not None:
                known_contractions.append(result)

        # If we do not have a inner contraction, rescan pairs
        # including outer products
        if len(known_contractions) == 0:

            # Then check the outer products
            for positions in itertools.combinations(
                range(len(input_sets)), 2
            ):
                result = _parse_possible_contraction(
                    positions, input_sets, output_set, idx_dict,
                    memory_limit, path_cost, naive_cost
                )
                if result is not None:
                    known_contractions.append(result)

            # If we still did not find any remaining contractions,
            # default back to einsum like behavior
            if len(known_contractions) == 0:
                path.append(tuple(range(len(input_sets))))
                break

        # Sort based on first index
        best = min(known_contractions, key=lambda x: x[0])

        # Now propagate as many unused contractions as possible
        # to the next iteration
        known_contractions = _update_other_results(known_contractions, best)

        # Next iteration only compute contractions with the new tensor
        # All other contractions have been accounted for
        input_sets = best[2]
        new_tensor_pos = len(input_sets) - 1
        comb_iter = ((i, new_tensor_pos) for i in range(new_tensor_pos))

        # Update path and total cost
        path.append(best[1])
        path_cost += best[0][1]

    return path


def _can_dot(inputs, result, idx_removed):
    """
    Checks if we can use BLAS (np.tensordot) call and its beneficial to do so.

    Parameters
    ----------
    inputs : list of str
        Specifies the subscripts for summation.
    result : str
        Resulting summation.
    idx_removed : set
        Indices that are removed in the summation


    Returns
    -------
    type : bool
        Returns true if BLAS should and can be used, else False

    Notes
    -----
    If the operations is BLAS level 1 or 2 and is not already aligned
    we default back to einsum as the memory movement to copy is more
    costly than the operation itself.


    Examples
    --------

    # Standard GEMM operation
    >>> _can_dot(['ij', 'jk'], 'ik', set('j'))
    True

    # Can use the standard BLAS, but requires odd data movement
    >>> _can_dot(['ijj', 'jk'], 'ik', set('j'))
    False

    # DDOT where the memory is not aligned
    >>> _can_dot(['ijk', 'ikj'], '', set('ijk'))
    False

    """

    # All `dot` calls remove indices
    if len(idx_removed) == 0:
        return False

    # BLAS can only handle two operands
    if len(inputs) != 2:
        return False

    input_left, input_right = inputs

    for c in set(input_left + input_right):
        # can't deal with repeated indices on same input or more than 2 total
        nl, nr = input_left.count(c), input_right.count(c)
        if (nl > 1) or (nr > 1) or (nl + nr > 2):
            return False

        # can't do implicit summation or dimension collapse e.g.
        #     "ab,bc->c" (implicitly sum over 'a')
        #     "ab,ca->ca" (take diagonal of 'a')
        if nl + nr - 1 == int(c in result):
            return False

    # Build a few temporaries
    set_left = set(input_left)
    set_right = set(input_right)
    keep_left = set_left - idx_removed
    keep_right = set_right - idx_removed
    rs = len(idx_removed)

    # At this point we are a DOT, GEMV, or GEMM operation

    # Handle inner products

    # DDOT with aligned data
    if input_left == input_right:
        return True

    # DDOT without aligned data (better to use einsum)
    if set_left == set_right:
        return False

    # Handle the 4 possible (aligned) GEMV or GEMM cases

    # GEMM or GEMV no transpose
    if input_left[-rs:] == input_right[:rs]:
        return True

    # GEMM or GEMV transpose both
    if input_left[:rs] == input_right[-rs:]:
        return True

    # GEMM or GEMV transpose right
    if input_left[-rs:] == input_right[-rs:]:
        return True

    # GEMM or GEMV transpose left
    if input_left[:rs] == input_right[:rs]:
        return True

    # Einsum is faster than GEMV if we have to copy data
    if not keep_left or not keep_right:
        return False

    # We are a matrix-matrix product, but we need to copy data
    return True


def _parse_einsum_input(operands):
    """
    A reproduction of einsum c side einsum parsing in python.

    Returns
    -------
    input_strings : str
        Parsed input strings
    output_string : str
        Parsed output string
    operands : list of array_like
        The operands to use in the numpy contraction

    Examples
    --------
    The operand list is simplified to reduce printing:

    >>> np.random.seed(123)
    >>> a = np.random.rand(4, 4)
    >>> b = np.random.rand(4, 4, 4)
    >>> _parse_einsum_input(('...a,...a->...', a, b))
    ('za,xza', 'xz', [a, b]) # may vary

    >>> _parse_einsum_input((a, [Ellipsis, 0], b, [Ellipsis, 0]))
    ('za,xza', 'xz', [a, b]) # may vary
    """

    if len(operands) == 0:
        raise ValueError("No input operands")

    if isinstance(operands[0], str):
        subscripts = operands[0].replace(" ", "")
        operands = [asanyarray(v) for v in operands[1:]]

        # Ensure all characters are valid
        for s in subscripts:
            if s in '.,->':
                continue
            if s not in einsum_symbols:
                raise ValueError(f"Character {s} is not a valid symbol.")

    else:
        tmp_operands = list(operands)
        operand_list = []
        subscript_list = []
        for p in range(len(operands) // 2):
            operand_list.append(tmp_operands.pop(0))
            subscript_list.append(tmp_operands.pop(0))

        output_list = tmp_operands[-1] if len(tmp_operands) else None
        operands = [asanyarray(v) for v in operand_list]
        subscripts = ""
        last = len(subscript_list) - 1
        for num, sub in enumerate(subscript_list):
            for s in sub:
                if s is Ellipsis:
                    subscripts += "..."
                else:
                    try:
                        s = operator.index(s)
                    except TypeError as e:
                        raise TypeError(
                            "For this input type lists must contain "
                            "either int or Ellipsis"
                        ) from e
                    subscripts += einsum_symbols[s]
            if num != last:
                subscripts += ","

        if output_list is not None:
            subscripts += "->"
            for s in output_list:
                if s is Ellipsis:
                    subscripts += "..."
                else:
                    try:
                        s = operator.index(s)
                    except TypeError as e:
                        raise TypeError(
                            "For this input type lists must contain "
                            "either int or Ellipsis"
                        ) from e
                    subscripts += einsum_symbols[s]
    # Check for proper "->"
    if ("-" in subscripts) or (">" in subscripts):
        invalid = (subscripts.count("-") > 1) or (subscripts.count(">") > 1)
        if invalid or (subscripts.count("->") != 1):
            raise ValueError("Subscripts can only contain one '->'.")

    # Parse ellipses
    if "." in subscripts:
        used = subscripts.replace(".", "").replace(",", "").replace("->", "")
        unused = list(einsum_symbols_set - set(used))
        ellipse_inds = "".join(unused)
        longest = 0

        if "->" in subscripts:
            input_tmp, output_sub = subscripts.split("->")
            split_subscripts = input_tmp.split(",")
            out_sub = True
        else:
            split_subscripts = subscripts.split(',')
            out_sub = False

        for num, sub in enumerate(split_subscripts):
            if "." in sub:
                if (sub.count(".") != 3) or (sub.count("...") != 1):
                    raise ValueError("Invalid Ellipses.")

                # Take into account numerical values
                if operands[num].shape == ():
                    ellipse_count = 0
                else:
                    ellipse_count = max(operands[num].ndim, 1)
                    ellipse_count -= (len(sub) - 3)

                if ellipse_count > longest:
                    longest = ellipse_count

                if ellipse_count < 0:
                    raise ValueError("Ellipses lengths do not match.")
                elif ellipse_count == 0:
                    split_subscripts[num] = sub.replace('...', '')
                else:
                    rep_inds = ellipse_inds[-ellipse_count:]
                    split_subscripts[num] = sub.replace('...', rep_inds)

        subscripts = ",".join(split_subscripts)
        if longest == 0:
            out_ellipse = ""
        else:
            out_ellipse = ellipse_inds[-longest:]

        if out_sub:
            subscripts += "->" + output_sub.replace("...", out_ellipse)
        else:
            # Special care for outputless ellipses
            output_subscript = ""
            tmp_subscripts = subscripts.replace(",", "")
            for s in sorted(set(tmp_subscripts)):
                if s not in (einsum_symbols):
                    raise ValueError(f"Character {s} is not a valid symbol.")
                if tmp_subscripts.count(s) == 1:
                    output_subscript += s
            normal_inds = ''.join(sorted(set(output_subscript) -
                                         set(out_ellipse)))

            subscripts += "->" + out_ellipse + normal_inds

    # Build output string if does not exist
    if "->" in subscripts:
        input_subscripts, output_subscript = subscripts.split("->")
    else:
        input_subscripts = subscripts
        # Build output subscripts
        tmp_subscripts = subscripts.replace(",", "")
        output_subscript = ""
        for s in sorted(set(tmp_subscripts)):
            if s not in einsum_symbols:
                raise ValueError(f"Character {s} is not a valid symbol.")
            if tmp_subscripts.count(s) == 1:
                output_subscript += s

    # Make sure output subscripts are in the input
    for char in output_subscript:
        if output_subscript.count(char) != 1:
            raise ValueError("Output character %s appeared more than once in "
                             "the output." % char)
        if char not in input_subscripts:
            raise ValueError(f"Output character {char} did not appear in the input")

    # Make sure number operands is equivalent to the number of terms
    if len(input_subscripts.split(',')) != len(operands):
        raise ValueError("Number of einsum subscripts must be equal to the "
                         "number of operands.")

    return (input_subscripts, output_subscript, operands)


def _einsum_path_dispatcher(*operands, optimize=None, einsum_call=None):
    # NOTE: technically, we should only dispatch on array-like arguments, not
    # subscripts (given as strings). But separating operands into
    # arrays/subscripts is a little tricky/slow (given einsum's two supported
    # signatures), so as a practical shortcut we dispatch on everything.
    # Strings will be ignored for dispatching since they don't define
    # __array_function__.
    return operands


@array_function_dispatch(_einsum_path_dispatcher, module='numpy')
def einsum_path(*operands, optimize='greedy', einsum_call=False):
    """
    einsum_path(subscripts, *operands, optimize='greedy')

    Evaluates the lowest cost contraction order for an einsum expression by
    considering the creation of intermediate arrays.

    Parameters
    ----------
    subscripts : str
        Specifies the subscripts for summation.
    *operands : list of array_like
        These are the arrays for the operation.
    optimize : {bool, list, tuple, 'greedy', 'optimal'}
        Choose the type of path. If a tuple is provided, the second argument is
        assumed to be the maximum intermediate size created. If only a single
        argument is provided the largest input or output array size is used
        as a maximum intermediate size.

        * if a list is given that starts with ``einsum_path``, uses this as the
          contraction path
        * if False no optimization is taken
        * if True defaults to the 'greedy' algorithm
        * 'optimal' An algorithm that combinatorially explores all possible
          ways of contracting the listed tensors and chooses the least costly
          path. Scales exponentially with the number of terms in the
          contraction.
        * 'greedy' An algorithm that chooses the best pair contraction
          at each step. Effectively, this algorithm searches the largest inner,
          Hadamard, and then outer products at each step. Scales cubically with
          the number of terms in the contraction. Equivalent to the 'optimal'
          path for most contractions.

        Default is 'greedy'.

    Returns
    -------
    path : list of tuples
        A list representation of the einsum path.
    string_repr : str
        A printable representation of the einsum path.

    Notes
    -----
    The resulting path indicates which terms of the input contraction should be
    contracted first, the result of this contraction is then appended to the
    end of the contraction list. This list can then be iterated over until all
    intermediate contractions are complete.

    See Also
    --------
    einsum, linalg.multi_dot

    Examples
    --------

    We can begin with a chain dot example. In this case, it is optimal to
    contract the ``b`` and ``c`` tensors first as represented by the first
    element of the path ``(1, 2)``. The resulting tensor is added to the end
    of the contraction and the remaining contraction ``(0, 1)`` is then
    completed.

    >>> np.random.seed(123)
    >>> a = np.random.rand(2, 2)
    >>> b = np.random.rand(2, 5)
    >>> c = np.random.rand(5, 2)
    >>> path_info = np.einsum_path('ij,jk,kl->il', a, b, c, optimize='greedy')
    >>> print(path_info[0])
    ['einsum_path', (1, 2), (0, 1)]
    >>> print(path_info[1])
      Complete contraction:  ij,jk,kl->il # may vary
             Naive scaling:  4
         Optimized scaling:  3
          Naive FLOP count:  1.600e+02
      Optimized FLOP count:  5.600e+01
       Theoretical speedup:  2.857
      Largest intermediate:  4.000e+00 elements
    -------------------------------------------------------------------------
    scaling                  current                                remaining
    -------------------------------------------------------------------------
       3                   kl,jk->jl                                ij,jl->il
       3                   jl,ij->il                                   il->il


    A more complex index transformation example.

    >>> I = np.random.rand(10, 10, 10, 10)
    >>> C = np.random.rand(10, 10)
    >>> path_info = np.einsum_path('ea,fb,abcd,gc,hd->efgh', C, C, I, C, C,
    ...                            optimize='greedy')

    >>> print(path_info[0])
    ['einsum_path', (0, 2), (0, 3), (0, 2), (0, 1)]
    >>> print(path_info[1])
      Complete contraction:  ea,fb,abcd,gc,hd->efgh # may vary
             Naive scaling:  8
         Optimized scaling:  5
          Naive FLOP count:  8.000e+08
      Optimized FLOP count:  8.000e+05
       Theoretical speedup:  1000.000
      Largest intermediate:  1.000e+04 elements
    --------------------------------------------------------------------------
    scaling                  current                                remaining
    --------------------------------------------------------------------------
       5               abcd,ea->bcde                      fb,gc,hd,bcde->efgh
       5               bcde,fb->cdef                         gc,hd,cdef->efgh
       5               cdef,gc->defg                            hd,defg->efgh
       5               defg,hd->efgh                               efgh->efgh
    """

    # Figure out what the path really is
    path_type = optimize
    if path_type is True:
        path_type = 'greedy'
    if path_type is None:
        path_type = False

    explicit_einsum_path = False
    memory_limit = None

    # No optimization or a named path algorithm
    if (path_type is False) or isinstance(path_type, str):
        pass

    # Given an explicit path
    elif len(path_type) and (path_type[0] == 'einsum_path'):
        explicit_einsum_path = True

    # Path tuple with memory limit
    elif ((len(path_type) == 2) and isinstance(path_type[0], str) and
            isinstance(path_type[1], (int, float))):
        memory_limit = int(path_type[1])
        path_type = path_type[0]

    else:
        raise TypeError(f"Did not understand the path: {str(path_type)}")

    # Hidden option, only einsum should call this
    einsum_call_arg = einsum_call

    # Python side parsing
    input_subscripts, output_subscript, operands = (
        _parse_einsum_input(operands)
    )

    # Build a few useful list and sets
    input_list = input_subscripts.split(',')
    input_sets = [set(x) for x in input_list]
    output_set = set(output_subscript)
    indices = set(input_subscripts.replace(',', ''))

    # Get length of each unique dimension and ensure all dimensions are correct
    dimension_dict = {}
    broadcast_indices = [[] for x in range(len(input_list))]
    for tnum, term in enumerate(input_list):
        sh = operands[tnum].shape
        if len(sh) != len(term):
            raise ValueError("Einstein sum subscript %s does not contain the "
                             "correct number of indices for operand %d."
                             % (input_subscripts[tnum], tnum))
        for cnum, char in enumerate(term):
            dim = sh[cnum]

            # Build out broadcast indices
            if dim == 1:
                broadcast_indices[tnum].append(char)

            if char in dimension_dict.keys():
                # For broadcasting cases we always want the largest dim size
                if dimension_dict[char] == 1:
                    dimension_dict[char] = dim
                elif dim not in (1, dimension_dict[char]):
                    raise ValueError("Size of label '%s' for operand %d (%d) "
                                     "does not match previous terms (%d)."
                                     % (char, tnum, dimension_dict[char], dim))
            else:
                dimension_dict[char] = dim

    # Convert broadcast inds to sets
    broadcast_indices = [set(x) for x in broadcast_indices]

    # Compute size of each input array plus the output array
    size_list = [_compute_size_by_dict(term, dimension_dict)
                 for term in input_list + [output_subscript]]
    max_size = max(size_list)

    if memory_limit is None:
        memory_arg = max_size
    else:
        memory_arg = memory_limit

    # Compute naive cost
    # This isn't quite right, need to look into exactly how einsum does this
    inner_product = (sum(len(x) for x in input_sets) - len(indices)) > 0
    naive_cost = _flop_count(
        indices, inner_product, len(input_list), dimension_dict
    )

    # Compute the path
    if explicit_einsum_path:
        path = path_type[1:]
    elif (
        (path_type is False)
        or (len(input_list) in [1, 2])
        or (indices == output_set)
    ):
        # Nothing to be optimized, leave it to einsum
        path = [tuple(range(len(input_list)))]
    elif path_type == "greedy":
        path = _greedy_path(
            input_sets, output_set, dimension_dict, memory_arg
        )
    elif path_type == "optimal":
        path = _optimal_path(
            input_sets, output_set, dimension_dict, memory_arg
        )
    else:
        raise KeyError("Path name %s not found", path_type)

    cost_list, scale_list, size_list, contraction_list = [], [], [], []

    # Build contraction tuple (positions, gemm, einsum_str, remaining)
    for cnum, contract_inds in enumerate(path):
        # Make sure we remove inds from right to left
        contract_inds = tuple(sorted(contract_inds, reverse=True))

        contract = _find_contraction(contract_inds, input_sets, output_set)
        out_inds, input_sets, idx_removed, idx_contract = contract

        cost = _flop_count(
            idx_contract, idx_removed, len(contract_inds), dimension_dict
        )
        cost_list.append(cost)
        scale_list.append(len(idx_contract))
        size_list.append(_compute_size_by_dict(out_inds, dimension_dict))

        bcast = set()
        tmp_inputs = []
        for x in contract_inds:
            tmp_inputs.append(input_list.pop(x))
            bcast |= broadcast_indices.pop(x)

        new_bcast_inds = bcast - idx_removed

        # If we're broadcasting, nix blas
        if not len(idx_removed & bcast):
            do_blas = _can_dot(tmp_inputs, out_inds, idx_removed)
        else:
            do_blas = False

        # Last contraction
        if (cnum - len(path)) == -1:
            idx_result = output_subscript
        else:
            sort_result = [(dimension_dict[ind], ind) for ind in out_inds]
            idx_result = "".join([x[1] for x in sorted(sort_result)])

        input_list.append(idx_result)
        broadcast_indices.append(new_bcast_inds)
        einsum_str = ",".join(tmp_inputs) + "->" + idx_result

        contraction = (
            contract_inds, idx_removed, einsum_str, input_list[:], do_blas
        )
        contraction_list.append(contraction)

    opt_cost = sum(cost_list) + 1

    if len(input_list) != 1:
        # Explicit "einsum_path" is usually trusted, but we detect this kind of
        # mistake in order to prevent from returning an intermediate value.
        raise RuntimeError(
            f"Invalid einsum_path is specified: {len(input_list) - 1} more "
            "operands has to be contracted.")

    if einsum_call_arg:
        return (operands, contraction_list)

    # Return the path along with a nice string representation
    overall_contraction = input_subscripts + "->" + output_subscript
    header = ("scaling", "current", "remaining")

    speedup = naive_cost / opt_cost
    max_i = max(size_list)

    path_print = f"  Complete contraction:  {overall_contraction}\n"
    path_print += f"         Naive scaling:  {len(indices)}\n"
    path_print += "     Optimized scaling:  %d\n" % max(scale_list)
    path_print += f"      Naive FLOP count:  {naive_cost:.3e}\n"
    path_print += f"  Optimized FLOP count:  {opt_cost:.3e}\n"
    path_print += f"   Theoretical speedup:  {speedup:3.3f}\n"
    path_print += f"  Largest intermediate:  {max_i:.3e} elements\n"
    path_print += "-" * 74 + "\n"
    path_print += "%6s %24s %40s\n" % header
    path_print += "-" * 74

    for n, contraction in enumerate(contraction_list):
        inds, idx_rm, einsum_str, remaining, blas = contraction
        remaining_str = ",".join(remaining) + "->" + output_subscript
        path_run = (scale_list[n], einsum_str, remaining_str)
        path_print += "\n%4d    %24s %40s" % path_run

    path = ['einsum_path'] + path
    return (path, path_print)


def _einsum_dispatcher(*operands, out=None, optimize=None, **kwargs):
    # Arguably we dispatch on more arguments than we really should; see note in
    # _einsum_path_dispatcher for why.
    yield from operands
    yield out


# Rewrite einsum to handle different cases
@array_function_dispatch(_einsum_dispatcher, module='numpy')
def einsum(*operands, out=None, optimize=False, **kwargs):
    """
    einsum(subscripts, *operands, out=None, dtype=None, order='K',
           casting='safe', optimize=False)

    Evaluates the Einstein summation convention on the operands.

    Using the Einstein summation convention, many common multi-dimensional,
    linear algebraic array operations can be represented in a simple fashion.
    In *implicit* mode `einsum` computes these values.

    In *explicit* mode, `einsum` provides further flexibility to compute
    other array operations that might not be considered classical Einstein
    summation operations, by disabling, or forcing summation over specified
    subscript labels.

    See the notes and examples for clarification.

    Parameters
    ----------
    subscripts : str
        Specifies the subscripts for summation as comma separated list of
        subscript labels. An implicit (classical Einstein summation)
        calculation is performed unless the explicit indicator '->' is
        included as well as subscript labels of the precise output form.
    operands : list of array_like
        These are the arrays for the operation.
    out : ndarray, optional
        If provided, the calculation is done into this array.
    dtype : {data-type, None}, optional
        If provided, forces the calculation to use the data type specified.
        Note that you may have to also give a more liberal `casting`
        parameter to allow the conversions. Default is None.
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the memory layout of the output. 'C' means it should
        be C contiguous. 'F' means it should be Fortran contiguous,
        'A' means it should be 'F' if the inputs are all 'F', 'C' otherwise.
        'K' means it should be as close to the layout as the inputs as
        is possible, including arbitrarily permuted axes.
        Default is 'K'.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur.  Setting this to
        'unsafe' is not recommended, as it can adversely affect accumulations.

        * 'no' means the data types should not be cast at all.
        * 'equiv' means only byte-order changes are allowed.
        * 'safe' means only casts which can preserve values are allowed.
        * 'same_kind' means only safe casts or casts within a kind,
          like float64 to float32, are allowed.
        * 'unsafe' means any data conversions may be done.

        Default is 'safe'.
    optimize : {False, True, 'greedy', 'optimal'}, optional
        Controls if intermediate optimization should occur. No optimization
        will occur if False and True will default to the 'greedy' algorithm.
        Also accepts an explicit contraction list from the ``np.einsum_path``
        function. See ``np.einsum_path`` for more details. Defaults to False.

    Returns
    -------
    output : ndarray
        The calculation based on the Einstein summation convention.

    See Also
    --------
    einsum_path, dot, inner, outer, tensordot, linalg.multi_dot
    einsum:
        Similar verbose interface is provided by the
        `einops <https://github.com/arogozhnikov/einops>`_ package to cover
        additional operations: transpose, reshape/flatten, repeat/tile,
        squeeze/unsqueeze and reductions.
        The `opt_einsum <https://optimized-einsum.readthedocs.io/en/stable/>`_
        optimizes contraction order for einsum-like expressions
        in backend-agnostic manner.

    Notes
    -----
    The Einstein summation convention can be used to compute
    many multi-dimensional, linear algebraic array operations. `einsum`
    provides a succinct way of representing these.

    A non-exhaustive list of these operations,
    which can be computed by `einsum`, is shown below along with examples:

    * Trace of an array, :py:func:`numpy.trace`.
    * Return a diagonal, :py:func:`numpy.diag`.
    * Array axis summations, :py:func:`numpy.sum`.
    * Transpositions and permutations, :py:func:`numpy.transpose`.
    * Matrix multiplication and dot product, :py:func:`numpy.matmul`
        :py:func:`numpy.dot`.
    * Vector inner and outer products, :py:func:`numpy.inner`
        :py:func:`numpy.outer`.
    * Broadcasting, element-wise and scalar multiplication,
        :py:func:`numpy.multiply`.
    * Tensor contractions, :py:func:`numpy.tensordot`.
    * Chained array operations, in efficient calculation order,
        :py:func:`numpy.einsum_path`.

    The subscripts string is a comma-separated list of subscript labels,
    where each label refers to a dimension of the corresponding operand.
    Whenever a label is repeated it is summed, so ``np.einsum('i,i', a, b)``
    is equivalent to :py:func:`np.inner(a,b) <numpy.inner>`. If a label
    appears only once, it is not summed, so ``np.einsum('i', a)``
    produces a view of ``a`` with no changes. A further example
    ``np.einsum('ij,jk', a, b)`` describes traditional matrix multiplication
    and is equivalent to :py:func:`np.matmul(a,b) <numpy.matmul>`.
    Repeated subscript labels in one operand take the diagonal.
    For example, ``np.einsum('ii', a)`` is equivalent to
    :py:func:`np.trace(a) <numpy.trace>`.

    In *implicit mode*, the chosen subscripts are important
    since the axes of the output are reordered alphabetically.  This
    means that ``np.einsum('ij', a)`` doesn't affect a 2D array, while
    ``np.einsum('ji', a)`` takes its transpose. Additionally,
    ``np.einsum('ij,jk', a, b)`` returns a matrix multiplication, while,
    ``np.einsum('ij,jh', a, b)`` returns the transpose of the
    multiplication since subscript 'h' precedes subscript 'i'.

    In *explicit mode* the output can be directly controlled by
    specifying output subscript labels.  This requires the
    identifier '->' as well as the list of output subscript labels.
    This feature increases the flexibility of the function since
    summing can be disabled or forced when required. The call
    ``np.einsum('i->', a)`` is like :py:func:`np.sum(a) <numpy.sum>`
    if ``a`` is a 1-D array, and ``np.einsum('ii->i', a)``
    is like :py:func:`np.diag(a) <numpy.diag>` if ``a`` is a square 2-D array.
    The difference is that `einsum` does not allow broadcasting by default.
    Additionally ``np.einsum('ij,jh->ih', a, b)`` directly specifies the
    order of the output subscript labels and therefore returns matrix
    multiplication, unlike the example above in implicit mode.

    To enable and control broadcasting, use an ellipsis.  Default
    NumPy-style broadcasting is done by adding an ellipsis
    to the left of each term, like ``np.einsum('...ii->...i', a)``.
    ``np.einsum('...i->...', a)`` is like
    :py:func:`np.sum(a, axis=-1) <numpy.sum>` for array ``a`` of any shape.
    To take the trace along the first and last axes,
    you can do ``np.einsum('i...i', a)``, or to do a matrix-matrix
    product with the left-most indices instead of rightmost, one can do
    ``np.einsum('ij...,jk...->ik...', a, b)``.

    When there is only one operand, no axes are summed, and no output
    parameter is provided, a view into the operand is returned instead
    of a new array.  Thus, taking the diagonal as ``np.einsum('ii->i', a)``
    produces a view (changed in version 1.10.0).

    `einsum` also provides an alternative way to provide the subscripts and
    operands as ``einsum(op0, sublist0, op1, sublist1, ..., [sublistout])``.
    If the output shape is not provided in this format `einsum` will be
    calculated in implicit mode, otherwise it will be performed explicitly.
    The examples below have corresponding `einsum` calls with the two
    parameter methods.

    Views returned from einsum are now writeable whenever the input array
    is writeable. For example, ``np.einsum('ijk...->kji...', a)`` will now
    have the same effect as :py:func:`np.swapaxes(a, 0, 2) <numpy.swapaxes>`
    and ``np.einsum('ii->i', a)`` will return a writeable view of the diagonal
    of a 2D array.

    Added the ``optimize`` argument which will optimize the contraction order
    of an einsum expression. For a contraction with three or more operands
    this can greatly increase the computational efficiency at the cost of
    a larger memory footprint during computation.

    Typically a 'greedy' algorithm is applied which empirical tests have shown
    returns the optimal path in the majority of cases. In some cases 'optimal'
    will return the superlative path through a more expensive, exhaustive
    search. For iterative calculations it may be advisable to calculate
    the optimal path once and reuse that path by supplying it as an argument.
    An example is given below.

    See :py:func:`numpy.einsum_path` for more details.

    Examples
    --------
    >>> a = np.arange(25).reshape(5,5)
    >>> b = np.arange(5)
    >>> c = np.arange(6).reshape(2,3)

    Trace of a matrix:

    >>> np.einsum('ii', a)
    60
    >>> np.einsum(a, [0,0])
    60
    >>> np.trace(a)
    60

    Extract the diagonal (requires explicit form):

    >>> np.einsum('ii->i', a)
    array([ 0,  6, 12, 18, 24])
    >>> np.einsum(a, [0,0], [0])
    array([ 0,  6, 12, 18, 24])
    >>> np.diag(a)
    array([ 0,  6, 12, 18, 24])

    Sum over an axis (requires explicit form):

    >>> np.einsum('ij->i', a)
    array([ 10,  35,  60,  85, 110])
    >>> np.einsum(a, [0,1], [0])
    array([ 10,  35,  60,  85, 110])
    >>> np.sum(a, axis=1)
    array([ 10,  35,  60,  85, 110])

    For higher dimensional arrays summing a single axis can be done
    with ellipsis:

    >>> np.einsum('...j->...', a)
    array([ 10,  35,  60,  85, 110])
    >>> np.einsum(a, [Ellipsis,1], [Ellipsis])
    array([ 10,  35,  60,  85, 110])

    Compute a matrix transpose, or reorder any number of axes:

    >>> np.einsum('ji', c)
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.einsum('ij->ji', c)
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.einsum(c, [1,0])
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.transpose(c)
    array([[0, 3],
           [1, 4],
           [2, 5]])

    Vector inner products:

    >>> np.einsum('i,i', b, b)
    30
    >>> np.einsum(b, [0], b, [0])
    30
    >>> np.inner(b,b)
    30

    Matrix vector multiplication:

    >>> np.einsum('ij,j', a, b)
    array([ 30,  80, 130, 180, 230])
    >>> np.einsum(a, [0,1], b, [1])
    array([ 30,  80, 130, 180, 230])
    >>> np.dot(a, b)
    array([ 30,  80, 130, 180, 230])
    >>> np.einsum('...j,j', a, b)
    array([ 30,  80, 130, 180, 230])

    Broadcasting and scalar multiplication:

    >>> np.einsum('..., ...', 3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.einsum(',ij', 3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.einsum(3, [Ellipsis], c, [Ellipsis])
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.multiply(3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])

    Vector outer product:

    >>> np.einsum('i,j', np.arange(2)+1, b)
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])
    >>> np.einsum(np.arange(2)+1, [0], b, [1])
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])
    >>> np.outer(np.arange(2)+1, b)
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])

    Tensor contraction:

    >>> a = np.arange(60.).reshape(3,4,5)
    >>> b = np.arange(24.).reshape(4,3,2)
    >>> np.einsum('ijk,jil->kl', a, b)
    array([[4400., 4730.],
           [4532., 4874.],
           [4664., 5018.],
           [4796., 5162.],
           [4928., 5306.]])
    >>> np.einsum(a, [0,1,2], b, [1,0,3], [2,3])
    array([[4400., 4730.],
           [4532., 4874.],
           [4664., 5018.],
           [4796., 5162.],
           [4928., 5306.]])
    >>> np.tensordot(a,b, axes=([1,0],[0,1]))
    array([[4400., 4730.],
           [4532., 4874.],
           [4664., 5018.],
           [4796., 5162.],
           [4928., 5306.]])

    Writeable returned arrays (since version 1.10.0):

    >>> a = np.zeros((3, 3))
    >>> np.einsum('ii->i', a)[:] = 1
    >>> a
    array([[1., 0., 0.],
           [0., 1., 0.],
           [0., 0., 1.]])

    Example of ellipsis use:

    >>> a = np.arange(6).reshape((3,2))
    >>> b = np.arange(12).reshape((4,3))
    >>> np.einsum('ki,jk->ij', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])
    >>> np.einsum('ki,...k->i...', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])
    >>> np.einsum('k...,jk', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])

    Chained array operations. For more complicated contractions, speed ups
    might be achieved by repeatedly computing a 'greedy' path or pre-computing
    the 'optimal' path and repeatedly applying it, using an `einsum_path`
    insertion (since version 1.12.0). Performance improvements can be
    particularly significant with larger arrays:

    >>> a = np.ones(64).reshape(2,4,8)

    Basic `einsum`: ~1520ms  (benchmarked on 3.1GHz Intel i5.)

    >>> for iteration in range(500):
    ...     _ = np.einsum('ijk,ilm,njm,nlk,abc->',a,a,a,a,a)

    Sub-optimal `einsum` (due to repeated path calculation time): ~330ms

    >>> for iteration in range(500):
    ...     _ = np.einsum('ijk,ilm,njm,nlk,abc->',a,a,a,a,a,
    ...         optimize='optimal')

    Greedy `einsum` (faster optimal path approximation): ~160ms

    >>> for iteration in range(500):
    ...     _ = np.einsum('ijk,ilm,njm,nlk,abc->',a,a,a,a,a, optimize='greedy')

    Optimal `einsum` (best usage pattern in some use cases): ~110ms

    >>> path = np.einsum_path('ijk,ilm,njm,nlk,abc->',a,a,a,a,a,
    ...     optimize='optimal')[0]
    >>> for iteration in range(500):
    ...     _ = np.einsum('ijk,ilm,njm,nlk,abc->',a,a,a,a,a, optimize=path)

    """
    # Special handling if out is specified
    specified_out = out is not None

    # If no optimization, run pure einsum
    if optimize is False:
        if specified_out:
            kwargs['out'] = out
        return c_einsum(*operands, **kwargs)

    # Check the kwargs to avoid a more cryptic error later, without having to
    # repeat default values here
    valid_einsum_kwargs = ['dtype', 'order', 'casting']
    unknown_kwargs = [k for (k, v) in kwargs.items() if
                      k not in valid_einsum_kwargs]
    if len(unknown_kwargs):
        raise TypeError(f"Did not understand the following kwargs: {unknown_kwargs}")

    # Build the contraction list and operand
    operands, contraction_list = einsum_path(*operands, optimize=optimize,
                                             einsum_call=True)

    # Handle order kwarg for output array, c_einsum allows mixed case
    output_order = kwargs.pop('order', 'K')
    if output_order.upper() == 'A':
        if all(arr.flags.f_contiguous for arr in operands):
            output_order = 'F'
        else:
            output_order = 'C'

    # Start contraction loop
    for num, contraction in enumerate(contraction_list):
        inds, idx_rm, einsum_str, remaining, blas = contraction
        tmp_operands = [operands.pop(x) for x in inds]

        # Do we need to deal with the output?
        handle_out = specified_out and ((num + 1) == len(contraction_list))

        # Call tensordot if still possible
        if blas:
            # Checks have already been handled
            input_str, results_index = einsum_str.split('->')
            input_left, input_right = input_str.split(',')

            tensor_result = input_left + input_right
            for s in idx_rm:
                tensor_result = tensor_result.replace(s, "")

            # Find indices to contract over
            left_pos, right_pos = [], []
            for s in sorted(idx_rm):
                left_pos.append(input_left.find(s))
                right_pos.append(input_right.find(s))

            # Contract!
            new_view = tensordot(
                *tmp_operands, axes=(tuple(left_pos), tuple(right_pos))
            )

            # Build a new view if needed
            if (tensor_result != results_index) or handle_out:
                if handle_out:
                    kwargs["out"] = out
                new_view = c_einsum(
                    tensor_result + '->' + results_index, new_view, **kwargs
                )

        # Call einsum
        else:
            # If out was specified
            if handle_out:
                kwargs["out"] = out

            # Do the contraction
            new_view = c_einsum(einsum_str, *tmp_operands, **kwargs)

        # Append new items and dereference what we can
        operands.append(new_view)
        del tmp_operands, new_view

    if specified_out:
        return out
    else:
        return asanyarray(operands[0], order=output_order)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\bezierTools.py ===
# -*- coding: utf-8 -*-
"""fontTools.misc.bezierTools.py -- tools for working with Bezier path segments.
"""

from fontTools.misc.arrayTools import calcBounds, sectRect, rectArea
from fontTools.misc.transform import Identity
import math
from collections import namedtuple

try:
    import cython
except (AttributeError, ImportError):
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython
COMPILED = cython.compiled


EPSILON = 1e-9


Intersection = namedtuple("Intersection", ["pt", "t1", "t2"])


__all__ = [
    "approximateCubicArcLength",
    "approximateCubicArcLengthC",
    "approximateQuadraticArcLength",
    "approximateQuadraticArcLengthC",
    "calcCubicArcLength",
    "calcCubicArcLengthC",
    "calcQuadraticArcLength",
    "calcQuadraticArcLengthC",
    "calcCubicBounds",
    "calcQuadraticBounds",
    "splitLine",
    "splitQuadratic",
    "splitCubic",
    "splitQuadraticAtT",
    "splitCubicAtT",
    "splitCubicAtTC",
    "splitCubicIntoTwoAtTC",
    "solveQuadratic",
    "solveCubic",
    "quadraticPointAtT",
    "cubicPointAtT",
    "cubicPointAtTC",
    "linePointAtT",
    "segmentPointAtT",
    "lineLineIntersections",
    "curveLineIntersections",
    "curveCurveIntersections",
    "segmentSegmentIntersections",
]


def calcCubicArcLength(pt1, pt2, pt3, pt4, tolerance=0.005):
    """Calculates the arc length for a cubic Bezier segment.

    Whereas :func:`approximateCubicArcLength` approximates the length, this
    function calculates it by "measuring", recursively dividing the curve
    until the divided segments are shorter than ``tolerance``.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as 2D tuples.
        tolerance: Controls the precision of the calcuation.

    Returns:
        Arc length value.
    """
    return calcCubicArcLengthC(
        complex(*pt1), complex(*pt2), complex(*pt3), complex(*pt4), tolerance
    )


def _split_cubic_into_two(p0, p1, p2, p3):
    mid = (p0 + 3 * (p1 + p2) + p3) * 0.125
    deriv3 = (p3 + p2 - p1 - p0) * 0.125
    return (
        (p0, (p0 + p1) * 0.5, mid - deriv3, mid),
        (mid, mid + deriv3, (p2 + p3) * 0.5, p3),
    )


@cython.returns(cython.double)
@cython.locals(
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
@cython.locals(mult=cython.double, arch=cython.double, box=cython.double)
def _calcCubicArcLengthCRecurse(mult, p0, p1, p2, p3):
    arch = abs(p0 - p3)
    box = abs(p0 - p1) + abs(p1 - p2) + abs(p2 - p3)
    if arch * mult + EPSILON >= box:
        return (arch + box) * 0.5
    else:
        one, two = _split_cubic_into_two(p0, p1, p2, p3)
        return _calcCubicArcLengthCRecurse(mult, *one) + _calcCubicArcLengthCRecurse(
            mult, *two
        )


@cython.returns(cython.double)
@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
)
@cython.locals(
    tolerance=cython.double,
    mult=cython.double,
)
def calcCubicArcLengthC(pt1, pt2, pt3, pt4, tolerance=0.005):
    """Calculates the arc length for a cubic Bezier segment.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as complex numbers.
        tolerance: Controls the precision of the calcuation.

    Returns:
        Arc length value.
    """
    mult = 1.0 + 1.5 * tolerance  # The 1.5 is a empirical hack; no math
    return _calcCubicArcLengthCRecurse(mult, pt1, pt2, pt3, pt4)


epsilonDigits = 6
epsilon = 1e-10


@cython.cfunc
@cython.inline
@cython.returns(cython.double)
@cython.locals(v1=cython.complex, v2=cython.complex)
def _dot(v1, v2):
    return (v1 * v2.conjugate()).real


@cython.cfunc
@cython.inline
@cython.returns(cython.double)
@cython.locals(x=cython.double)
def _intSecAtan(x):
    # In : sympy.integrate(sp.sec(sp.atan(x)))
    # Out: x*sqrt(x**2 + 1)/2 + asinh(x)/2
    return x * math.sqrt(x**2 + 1) / 2 + math.asinh(x) / 2


def calcQuadraticArcLength(pt1, pt2, pt3):
    """Calculates the arc length for a quadratic Bezier segment.

    Args:
        pt1: Start point of the Bezier as 2D tuple.
        pt2: Handle point of the Bezier as 2D tuple.
        pt3: End point of the Bezier as 2D tuple.

    Returns:
        Arc length value.

    Example::

        >>> calcQuadraticArcLength((0, 0), (0, 0), (0, 0)) # empty segment
        0.0
        >>> calcQuadraticArcLength((0, 0), (50, 0), (80, 0)) # collinear points
        80.0
        >>> calcQuadraticArcLength((0, 0), (0, 50), (0, 80)) # collinear points vertical
        80.0
        >>> calcQuadraticArcLength((0, 0), (50, 20), (100, 40)) # collinear points
        107.70329614269008
        >>> calcQuadraticArcLength((0, 0), (0, 100), (100, 0))
        154.02976155645263
        >>> calcQuadraticArcLength((0, 0), (0, 50), (100, 0))
        120.21581243984076
        >>> calcQuadraticArcLength((0, 0), (50, -10), (80, 50))
        102.53273816445825
        >>> calcQuadraticArcLength((0, 0), (40, 0), (-40, 0)) # collinear points, control point outside
        66.66666666666667
        >>> calcQuadraticArcLength((0, 0), (40, 0), (0, 0)) # collinear points, looping back
        40.0
    """
    return calcQuadraticArcLengthC(complex(*pt1), complex(*pt2), complex(*pt3))


@cython.returns(cython.double)
@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    d0=cython.complex,
    d1=cython.complex,
    d=cython.complex,
    n=cython.complex,
)
@cython.locals(
    scale=cython.double,
    origDist=cython.double,
    a=cython.double,
    b=cython.double,
    x0=cython.double,
    x1=cython.double,
    Len=cython.double,
)
def calcQuadraticArcLengthC(pt1, pt2, pt3):
    """Calculates the arc length for a quadratic Bezier segment.

    Args:
        pt1: Start point of the Bezier as a complex number.
        pt2: Handle point of the Bezier as a complex number.
        pt3: End point of the Bezier as a complex number.

    Returns:
        Arc length value.
    """
    # Analytical solution to the length of a quadratic bezier.
    # Documentation: https://github.com/fonttools/fonttools/issues/3055
    d0 = pt2 - pt1
    d1 = pt3 - pt2
    d = d1 - d0
    n = d * 1j
    scale = abs(n)
    if scale == 0.0:
        return abs(pt3 - pt1)
    origDist = _dot(n, d0)
    if abs(origDist) < epsilon:
        if _dot(d0, d1) >= 0:
            return abs(pt3 - pt1)
        a, b = abs(d0), abs(d1)
        return (a * a + b * b) / (a + b)
    x0 = _dot(d, d0) / origDist
    x1 = _dot(d, d1) / origDist
    Len = abs(2 * (_intSecAtan(x1) - _intSecAtan(x0)) * origDist / (scale * (x1 - x0)))
    return Len


def approximateQuadraticArcLength(pt1, pt2, pt3):
    """Calculates the arc length for a quadratic Bezier segment.

    Uses Gauss-Legendre quadrature for a branch-free approximation.
    See :func:`calcQuadraticArcLength` for a slower but more accurate result.

    Args:
        pt1: Start point of the Bezier as 2D tuple.
        pt2: Handle point of the Bezier as 2D tuple.
        pt3: End point of the Bezier as 2D tuple.

    Returns:
        Approximate arc length value.
    """
    return approximateQuadraticArcLengthC(complex(*pt1), complex(*pt2), complex(*pt3))


@cython.returns(cython.double)
@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
)
@cython.locals(
    v0=cython.double,
    v1=cython.double,
    v2=cython.double,
)
def approximateQuadraticArcLengthC(pt1, pt2, pt3):
    """Calculates the arc length for a quadratic Bezier segment.

    Uses Gauss-Legendre quadrature for a branch-free approximation.
    See :func:`calcQuadraticArcLength` for a slower but more accurate result.

    Args:
        pt1: Start point of the Bezier as a complex number.
        pt2: Handle point of the Bezier as a complex number.
        pt3: End point of the Bezier as a complex number.

    Returns:
        Approximate arc length value.
    """
    # This, essentially, approximates the length-of-derivative function
    # to be integrated with the best-matching fifth-degree polynomial
    # approximation of it.
    #
    # https://en.wikipedia.org/wiki/Gaussian_quadrature#Gauss.E2.80.93Legendre_quadrature

    # abs(BezierCurveC[2].diff(t).subs({t:T})) for T in sorted(.5, .5±sqrt(3/5)/2),
    # weighted 5/18, 8/18, 5/18 respectively.
    v0 = abs(
        -0.492943519233745 * pt1 + 0.430331482911935 * pt2 + 0.0626120363218102 * pt3
    )
    v1 = abs(pt3 - pt1) * 0.4444444444444444
    v2 = abs(
        -0.0626120363218102 * pt1 - 0.430331482911935 * pt2 + 0.492943519233745 * pt3
    )

    return v0 + v1 + v2


def calcQuadraticBounds(pt1, pt2, pt3):
    """Calculates the bounding rectangle for a quadratic Bezier segment.

    Args:
        pt1: Start point of the Bezier as a 2D tuple.
        pt2: Handle point of the Bezier as a 2D tuple.
        pt3: End point of the Bezier as a 2D tuple.

    Returns:
        A four-item tuple representing the bounding rectangle ``(xMin, yMin, xMax, yMax)``.

    Example::

        >>> calcQuadraticBounds((0, 0), (50, 100), (100, 0))
        (0, 0, 100, 50.0)
        >>> calcQuadraticBounds((0, 0), (100, 0), (100, 100))
        (0.0, 0.0, 100, 100)
    """
    (ax, ay), (bx, by), (cx, cy) = calcQuadraticParameters(pt1, pt2, pt3)
    ax2 = ax * 2.0
    ay2 = ay * 2.0
    roots = []
    if ax2 != 0:
        roots.append(-bx / ax2)
    if ay2 != 0:
        roots.append(-by / ay2)
    points = [
        (ax * t * t + bx * t + cx, ay * t * t + by * t + cy)
        for t in roots
        if 0 <= t < 1
    ] + [pt1, pt3]
    return calcBounds(points)


def approximateCubicArcLength(pt1, pt2, pt3, pt4):
    """Approximates the arc length for a cubic Bezier segment.

    Uses Gauss-Lobatto quadrature with n=5 points to approximate arc length.
    See :func:`calcCubicArcLength` for a slower but more accurate result.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as 2D tuples.

    Returns:
        Arc length value.

    Example::

        >>> approximateCubicArcLength((0, 0), (25, 100), (75, 100), (100, 0))
        190.04332968932817
        >>> approximateCubicArcLength((0, 0), (50, 0), (100, 50), (100, 100))
        154.8852074945903
        >>> approximateCubicArcLength((0, 0), (50, 0), (100, 0), (150, 0)) # line; exact result should be 150.
        149.99999999999991
        >>> approximateCubicArcLength((0, 0), (50, 0), (100, 0), (-50, 0)) # cusp; exact result should be 150.
        136.9267662156362
        >>> approximateCubicArcLength((0, 0), (50, 0), (100, -50), (-50, 0)) # cusp
        154.80848416537057
    """
    return approximateCubicArcLengthC(
        complex(*pt1), complex(*pt2), complex(*pt3), complex(*pt4)
    )


@cython.returns(cython.double)
@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
)
@cython.locals(
    v0=cython.double,
    v1=cython.double,
    v2=cython.double,
    v3=cython.double,
    v4=cython.double,
)
def approximateCubicArcLengthC(pt1, pt2, pt3, pt4):
    """Approximates the arc length for a cubic Bezier segment.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as complex numbers.

    Returns:
        Arc length value.
    """
    # This, essentially, approximates the length-of-derivative function
    # to be integrated with the best-matching seventh-degree polynomial
    # approximation of it.
    #
    # https://en.wikipedia.org/wiki/Gaussian_quadrature#Gauss.E2.80.93Lobatto_rules

    # abs(BezierCurveC[3].diff(t).subs({t:T})) for T in sorted(0, .5±(3/7)**.5/2, .5, 1),
    # weighted 1/20, 49/180, 32/90, 49/180, 1/20 respectively.
    v0 = abs(pt2 - pt1) * 0.15
    v1 = abs(
        -0.558983582205757 * pt1
        + 0.325650248872424 * pt2
        + 0.208983582205757 * pt3
        + 0.024349751127576 * pt4
    )
    v2 = abs(pt4 - pt1 + pt3 - pt2) * 0.26666666666666666
    v3 = abs(
        -0.024349751127576 * pt1
        - 0.208983582205757 * pt2
        - 0.325650248872424 * pt3
        + 0.558983582205757 * pt4
    )
    v4 = abs(pt4 - pt3) * 0.15

    return v0 + v1 + v2 + v3 + v4


def calcCubicBounds(pt1, pt2, pt3, pt4):
    """Calculates the bounding rectangle for a quadratic Bezier segment.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as 2D tuples.

    Returns:
        A four-item tuple representing the bounding rectangle ``(xMin, yMin, xMax, yMax)``.

    Example::

        >>> calcCubicBounds((0, 0), (25, 100), (75, 100), (100, 0))
        (0, 0, 100, 75.0)
        >>> calcCubicBounds((0, 0), (50, 0), (100, 50), (100, 100))
        (0.0, 0.0, 100, 100)
        >>> print("%f %f %f %f" % calcCubicBounds((50, 0), (0, 100), (100, 100), (50, 0)))
        35.566243 0.000000 64.433757 75.000000
    """
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = calcCubicParameters(pt1, pt2, pt3, pt4)
    # calc first derivative
    ax3 = ax * 3.0
    ay3 = ay * 3.0
    bx2 = bx * 2.0
    by2 = by * 2.0
    xRoots = [t for t in solveQuadratic(ax3, bx2, cx) if 0 <= t < 1]
    yRoots = [t for t in solveQuadratic(ay3, by2, cy) if 0 <= t < 1]
    roots = xRoots + yRoots

    points = [
        (
            ax * t * t * t + bx * t * t + cx * t + dx,
            ay * t * t * t + by * t * t + cy * t + dy,
        )
        for t in roots
    ] + [pt1, pt4]
    return calcBounds(points)


def splitLine(pt1, pt2, where, isHorizontal):
    """Split a line at a given coordinate.

    Args:
        pt1: Start point of line as 2D tuple.
        pt2: End point of line as 2D tuple.
        where: Position at which to split the line.
        isHorizontal: Direction of the ray splitting the line. If true,
            ``where`` is interpreted as a Y coordinate; if false, then
            ``where`` is interpreted as an X coordinate.

    Returns:
        A list of two line segments (each line segment being two 2D tuples)
        if the line was successfully split, or a list containing the original
        line.

    Example::

        >>> printSegments(splitLine((0, 0), (100, 100), 50, True))
        ((0, 0), (50, 50))
        ((50, 50), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 100, True))
        ((0, 0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, True))
        ((0, 0), (0, 0))
        ((0, 0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, False))
        ((0, 0), (0, 0))
        ((0, 0), (100, 100))
        >>> printSegments(splitLine((100, 0), (0, 0), 50, False))
        ((100, 0), (50, 0))
        ((50, 0), (0, 0))
        >>> printSegments(splitLine((0, 100), (0, 0), 50, True))
        ((0, 100), (0, 50))
        ((0, 50), (0, 0))
    """
    pt1x, pt1y = pt1
    pt2x, pt2y = pt2

    ax = pt2x - pt1x
    ay = pt2y - pt1y

    bx = pt1x
    by = pt1y

    a = (ax, ay)[isHorizontal]

    if a == 0:
        return [(pt1, pt2)]
    t = (where - (bx, by)[isHorizontal]) / a
    if 0 <= t < 1:
        midPt = ax * t + bx, ay * t + by
        return [(pt1, midPt), (midPt, pt2)]
    else:
        return [(pt1, pt2)]


def splitQuadratic(pt1, pt2, pt3, where, isHorizontal):
    """Split a quadratic Bezier curve at a given coordinate.

    Args:
        pt1,pt2,pt3: Control points of the Bezier as 2D tuples.
        where: Position at which to split the curve.
        isHorizontal: Direction of the ray splitting the curve. If true,
            ``where`` is interpreted as a Y coordinate; if false, then
            ``where`` is interpreted as an X coordinate.

    Returns:
        A list of two curve segments (each curve segment being three 2D tuples)
        if the curve was successfully split, or a list containing the original
        curve.

    Example::

        >>> printSegments(splitQuadratic((0, 0), (50, 100), (100, 0), 150, False))
        ((0, 0), (50, 100), (100, 0))
        >>> printSegments(splitQuadratic((0, 0), (50, 100), (100, 0), 50, False))
        ((0, 0), (25, 50), (50, 50))
        ((50, 50), (75, 50), (100, 0))
        >>> printSegments(splitQuadratic((0, 0), (50, 100), (100, 0), 25, False))
        ((0, 0), (12.5, 25), (25, 37.5))
        ((25, 37.5), (62.5, 75), (100, 0))
        >>> printSegments(splitQuadratic((0, 0), (50, 100), (100, 0), 25, True))
        ((0, 0), (7.32233, 14.6447), (14.6447, 25))
        ((14.6447, 25), (50, 75), (85.3553, 25))
        ((85.3553, 25), (92.6777, 14.6447), (100, -7.10543e-15))
        >>> # XXX I'm not at all sure if the following behavior is desirable:
        >>> printSegments(splitQuadratic((0, 0), (50, 100), (100, 0), 50, True))
        ((0, 0), (25, 50), (50, 50))
        ((50, 50), (50, 50), (50, 50))
        ((50, 50), (75, 50), (100, 0))
    """
    a, b, c = calcQuadraticParameters(pt1, pt2, pt3)
    solutions = solveQuadratic(
        a[isHorizontal], b[isHorizontal], c[isHorizontal] - where
    )
    solutions = sorted(t for t in solutions if 0 <= t < 1)
    if not solutions:
        return [(pt1, pt2, pt3)]
    return _splitQuadraticAtT(a, b, c, *solutions)


def splitCubic(pt1, pt2, pt3, pt4, where, isHorizontal):
    """Split a cubic Bezier curve at a given coordinate.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as 2D tuples.
        where: Position at which to split the curve.
        isHorizontal: Direction of the ray splitting the curve. If true,
            ``where`` is interpreted as a Y coordinate; if false, then
            ``where`` is interpreted as an X coordinate.

    Returns:
        A list of two curve segments (each curve segment being four 2D tuples)
        if the curve was successfully split, or a list containing the original
        curve.

    Example::

        >>> printSegments(splitCubic((0, 0), (25, 100), (75, 100), (100, 0), 150, False))
        ((0, 0), (25, 100), (75, 100), (100, 0))
        >>> printSegments(splitCubic((0, 0), (25, 100), (75, 100), (100, 0), 50, False))
        ((0, 0), (12.5, 50), (31.25, 75), (50, 75))
        ((50, 75), (68.75, 75), (87.5, 50), (100, 0))
        >>> printSegments(splitCubic((0, 0), (25, 100), (75, 100), (100, 0), 25, True))
        ((0, 0), (2.29379, 9.17517), (4.79804, 17.5085), (7.47414, 25))
        ((7.47414, 25), (31.2886, 91.6667), (68.7114, 91.6667), (92.5259, 25))
        ((92.5259, 25), (95.202, 17.5085), (97.7062, 9.17517), (100, 1.77636e-15))
    """
    a, b, c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
    solutions = solveCubic(
        a[isHorizontal], b[isHorizontal], c[isHorizontal], d[isHorizontal] - where
    )
    solutions = sorted(t for t in solutions if 0 <= t < 1)
    if not solutions:
        return [(pt1, pt2, pt3, pt4)]
    return _splitCubicAtT(a, b, c, d, *solutions)


def splitQuadraticAtT(pt1, pt2, pt3, *ts):
    """Split a quadratic Bezier curve at one or more values of t.

    Args:
        pt1,pt2,pt3: Control points of the Bezier as 2D tuples.
        *ts: Positions at which to split the curve.

    Returns:
        A list of curve segments (each curve segment being three 2D tuples).

    Examples::

        >>> printSegments(splitQuadraticAtT((0, 0), (50, 100), (100, 0), 0.5))
        ((0, 0), (25, 50), (50, 50))
        ((50, 50), (75, 50), (100, 0))
        >>> printSegments(splitQuadraticAtT((0, 0), (50, 100), (100, 0), 0.5, 0.75))
        ((0, 0), (25, 50), (50, 50))
        ((50, 50), (62.5, 50), (75, 37.5))
        ((75, 37.5), (87.5, 25), (100, 0))
    """
    a, b, c = calcQuadraticParameters(pt1, pt2, pt3)
    return _splitQuadraticAtT(a, b, c, *ts)


def splitCubicAtT(pt1, pt2, pt3, pt4, *ts):
    """Split a cubic Bezier curve at one or more values of t.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as 2D tuples.
        *ts: Positions at which to split the curve.

    Returns:
        A list of curve segments (each curve segment being four 2D tuples).

    Examples::

        >>> printSegments(splitCubicAtT((0, 0), (25, 100), (75, 100), (100, 0), 0.5))
        ((0, 0), (12.5, 50), (31.25, 75), (50, 75))
        ((50, 75), (68.75, 75), (87.5, 50), (100, 0))
        >>> printSegments(splitCubicAtT((0, 0), (25, 100), (75, 100), (100, 0), 0.5, 0.75))
        ((0, 0), (12.5, 50), (31.25, 75), (50, 75))
        ((50, 75), (59.375, 75), (68.75, 68.75), (77.3438, 56.25))
        ((77.3438, 56.25), (85.9375, 43.75), (93.75, 25), (100, 0))
    """
    a, b, c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
    split = _splitCubicAtT(a, b, c, d, *ts)

    # the split impl can introduce floating point errors; we know the first
    # segment should always start at pt1 and the last segment should end at pt4,
    # so we set those values directly before returning.
    split[0] = (pt1, *split[0][1:])
    split[-1] = (*split[-1][:-1], pt4)
    return split


@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
    a=cython.complex,
    b=cython.complex,
    c=cython.complex,
    d=cython.complex,
)
def splitCubicAtTC(pt1, pt2, pt3, pt4, *ts):
    """Split a cubic Bezier curve at one or more values of t.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as complex numbers..
        *ts: Positions at which to split the curve.

    Yields:
        Curve segments (each curve segment being four complex numbers).
    """
    a, b, c, d = calcCubicParametersC(pt1, pt2, pt3, pt4)
    yield from _splitCubicAtTC(a, b, c, d, *ts)


@cython.returns(cython.complex)
@cython.locals(
    t=cython.double,
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
    pointAtT=cython.complex,
    off1=cython.complex,
    off2=cython.complex,
)
@cython.locals(
    t2=cython.double, _1_t=cython.double, _1_t_2=cython.double, _2_t_1_t=cython.double
)
def splitCubicIntoTwoAtTC(pt1, pt2, pt3, pt4, t):
    """Split a cubic Bezier curve at t.

    Args:
        pt1,pt2,pt3,pt4: Control points of the Bezier as complex numbers.
        t: Position at which to split the curve.

    Returns:
        A tuple of two curve segments (each curve segment being four complex numbers).
    """
    t2 = t * t
    _1_t = 1 - t
    _1_t_2 = _1_t * _1_t
    _2_t_1_t = 2 * t * _1_t
    pointAtT = (
        _1_t_2 * _1_t * pt1 + 3 * (_1_t_2 * t * pt2 + _1_t * t2 * pt3) + t2 * t * pt4
    )
    off1 = _1_t_2 * pt1 + _2_t_1_t * pt2 + t2 * pt3
    off2 = _1_t_2 * pt2 + _2_t_1_t * pt3 + t2 * pt4

    pt2 = pt1 + (pt2 - pt1) * t
    pt3 = pt4 + (pt3 - pt4) * _1_t

    return ((pt1, pt2, off1, pointAtT), (pointAtT, off2, pt3, pt4))


def _splitQuadraticAtT(a, b, c, *ts):
    ts = list(ts)
    segments = []
    ts.insert(0, 0.0)
    ts.append(1.0)
    ax, ay = a
    bx, by = b
    cx, cy = c
    for i in range(len(ts) - 1):
        t1 = ts[i]
        t2 = ts[i + 1]
        delta = t2 - t1
        # calc new a, b and c
        delta_2 = delta * delta
        a1x = ax * delta_2
        a1y = ay * delta_2
        b1x = (2 * ax * t1 + bx) * delta
        b1y = (2 * ay * t1 + by) * delta
        t1_2 = t1 * t1
        c1x = ax * t1_2 + bx * t1 + cx
        c1y = ay * t1_2 + by * t1 + cy

        pt1, pt2, pt3 = calcQuadraticPoints((a1x, a1y), (b1x, b1y), (c1x, c1y))
        segments.append((pt1, pt2, pt3))
    return segments


def _splitCubicAtT(a, b, c, d, *ts):
    ts = list(ts)
    ts.insert(0, 0.0)
    ts.append(1.0)
    segments = []
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    for i in range(len(ts) - 1):
        t1 = ts[i]
        t2 = ts[i + 1]
        delta = t2 - t1

        delta_2 = delta * delta
        delta_3 = delta * delta_2
        t1_2 = t1 * t1
        t1_3 = t1 * t1_2

        # calc new a, b, c and d
        a1x = ax * delta_3
        a1y = ay * delta_3
        b1x = (3 * ax * t1 + bx) * delta_2
        b1y = (3 * ay * t1 + by) * delta_2
        c1x = (2 * bx * t1 + cx + 3 * ax * t1_2) * delta
        c1y = (2 * by * t1 + cy + 3 * ay * t1_2) * delta
        d1x = ax * t1_3 + bx * t1_2 + cx * t1 + dx
        d1y = ay * t1_3 + by * t1_2 + cy * t1 + dy
        pt1, pt2, pt3, pt4 = calcCubicPoints(
            (a1x, a1y), (b1x, b1y), (c1x, c1y), (d1x, d1y)
        )
        segments.append((pt1, pt2, pt3, pt4))
    return segments


@cython.locals(
    a=cython.complex,
    b=cython.complex,
    c=cython.complex,
    d=cython.complex,
    t1=cython.double,
    t2=cython.double,
    delta=cython.double,
    delta_2=cython.double,
    delta_3=cython.double,
    a1=cython.complex,
    b1=cython.complex,
    c1=cython.complex,
    d1=cython.complex,
)
def _splitCubicAtTC(a, b, c, d, *ts):
    ts = list(ts)
    ts.insert(0, 0.0)
    ts.append(1.0)
    for i in range(len(ts) - 1):
        t1 = ts[i]
        t2 = ts[i + 1]
        delta = t2 - t1

        delta_2 = delta * delta
        delta_3 = delta * delta_2
        t1_2 = t1 * t1
        t1_3 = t1 * t1_2

        # calc new a, b, c and d
        a1 = a * delta_3
        b1 = (3 * a * t1 + b) * delta_2
        c1 = (2 * b * t1 + c + 3 * a * t1_2) * delta
        d1 = a * t1_3 + b * t1_2 + c * t1 + d
        pt1, pt2, pt3, pt4 = calcCubicPointsC(a1, b1, c1, d1)
        yield (pt1, pt2, pt3, pt4)


#
# Equation solvers.
#

from math import sqrt, acos, cos, pi


def solveQuadratic(a, b, c, sqrt=sqrt):
    """Solve a quadratic equation.

    Solves *a*x*x + b*x + c = 0* where a, b and c are real.

    Args:
        a: coefficient of *x²*
        b: coefficient of *x*
        c: constant term

    Returns:
        A list of roots. Note that the returned list is neither guaranteed to
        be sorted nor to contain unique values!
    """
    if abs(a) < epsilon:
        if abs(b) < epsilon:
            # We have a non-equation; therefore, we have no valid solution
            roots = []
        else:
            # We have a linear equation with 1 root.
            roots = [-c / b]
    else:
        # We have a true quadratic equation.  Apply the quadratic formula to find two roots.
        DD = b * b - 4.0 * a * c
        if DD >= 0.0:
            rDD = sqrt(DD)
            roots = [(-b + rDD) / 2.0 / a, (-b - rDD) / 2.0 / a]
        else:
            # complex roots, ignore
            roots = []
    return roots


def solveCubic(a, b, c, d):
    """Solve a cubic equation.

    Solves *a*x*x*x + b*x*x + c*x + d = 0* where a, b, c and d are real.

    Args:
        a: coefficient of *x³*
        b: coefficient of *x²*
        c: coefficient of *x*
        d: constant term

    Returns:
        A list of roots. Note that the returned list is neither guaranteed to
        be sorted nor to contain unique values!

    Examples::

        >>> solveCubic(1, 1, -6, 0)
        [-3.0, -0.0, 2.0]
        >>> solveCubic(-10.0, -9.0, 48.0, -29.0)
        [-2.9, 1.0, 1.0]
        >>> solveCubic(-9.875, -9.0, 47.625, -28.75)
        [-2.911392, 1.0, 1.0]
        >>> solveCubic(1.0, -4.5, 6.75, -3.375)
        [1.5, 1.5, 1.5]
        >>> solveCubic(-12.0, 18.0, -9.0, 1.50023651123)
        [0.5, 0.5, 0.5]
        >>> solveCubic(
        ...     9.0, 0.0, 0.0, -7.62939453125e-05
        ... ) == [-0.0, -0.0, -0.0]
        True
    """
    #
    # adapted from:
    #   CUBIC.C - Solve a cubic polynomial
    #   public domain by Ross Cottrell
    # found at: http://www.strangecreations.com/library/snippets/Cubic.C
    #
    if abs(a) < epsilon:
        # don't just test for zero; for very small values of 'a' solveCubic()
        # returns unreliable results, so we fall back to quad.
        return solveQuadratic(b, c, d)
    a = float(a)
    a1 = b / a
    a2 = c / a
    a3 = d / a

    Q = (a1 * a1 - 3.0 * a2) / 9.0
    R = (2.0 * a1 * a1 * a1 - 9.0 * a1 * a2 + 27.0 * a3) / 54.0

    R2 = R * R
    Q3 = Q * Q * Q
    R2 = 0 if R2 < epsilon else R2
    Q3 = 0 if abs(Q3) < epsilon else Q3

    R2_Q3 = R2 - Q3

    if R2 == 0.0 and Q3 == 0.0:
        x = round(-a1 / 3.0, epsilonDigits)
        return [x, x, x]
    elif R2_Q3 <= epsilon * 0.5:
        # The epsilon * .5 above ensures that Q3 is not zero.
        theta = acos(max(min(R / sqrt(Q3), 1.0), -1.0))
        rQ2 = -2.0 * sqrt(Q)
        a1_3 = a1 / 3.0
        x0 = rQ2 * cos(theta / 3.0) - a1_3
        x1 = rQ2 * cos((theta + 2.0 * pi) / 3.0) - a1_3
        x2 = rQ2 * cos((theta + 4.0 * pi) / 3.0) - a1_3
        x0, x1, x2 = sorted([x0, x1, x2])
        # Merge roots that are close-enough
        if x1 - x0 < epsilon and x2 - x1 < epsilon:
            x0 = x1 = x2 = round((x0 + x1 + x2) / 3.0, epsilonDigits)
        elif x1 - x0 < epsilon:
            x0 = x1 = round((x0 + x1) / 2.0, epsilonDigits)
            x2 = round(x2, epsilonDigits)
        elif x2 - x1 < epsilon:
            x0 = round(x0, epsilonDigits)
            x1 = x2 = round((x1 + x2) / 2.0, epsilonDigits)
        else:
            x0 = round(x0, epsilonDigits)
            x1 = round(x1, epsilonDigits)
            x2 = round(x2, epsilonDigits)
        return [x0, x1, x2]
    else:
        x = pow(sqrt(R2_Q3) + abs(R), 1 / 3.0)
        x = x + Q / x
        if R >= 0.0:
            x = -x
        x = round(x - a1 / 3.0, epsilonDigits)
        return [x]


#
# Conversion routines for points to parameters and vice versa
#


def calcQuadraticParameters(pt1, pt2, pt3):
    x2, y2 = pt2
    x3, y3 = pt3
    cx, cy = pt1
    bx = (x2 - cx) * 2.0
    by = (y2 - cy) * 2.0
    ax = x3 - cx - bx
    ay = y3 - cy - by
    return (ax, ay), (bx, by), (cx, cy)


def calcCubicParameters(pt1, pt2, pt3, pt4):
    x2, y2 = pt2
    x3, y3 = pt3
    x4, y4 = pt4
    dx, dy = pt1
    cx = (x2 - dx) * 3.0
    cy = (y2 - dy) * 3.0
    bx = (x3 - x2) * 3.0 - cx
    by = (y3 - y2) * 3.0 - cy
    ax = x4 - dx - cx - bx
    ay = y4 - dy - cy - by
    return (ax, ay), (bx, by), (cx, cy), (dx, dy)


@cython.cfunc
@cython.inline
@cython.locals(
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
    a=cython.complex,
    b=cython.complex,
    c=cython.complex,
)
def calcCubicParametersC(pt1, pt2, pt3, pt4):
    c = (pt2 - pt1) * 3.0
    b = (pt3 - pt2) * 3.0 - c
    a = pt4 - pt1 - c - b
    return (a, b, c, pt1)


def calcQuadraticPoints(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    x1 = cx
    y1 = cy
    x2 = (bx * 0.5) + cx
    y2 = (by * 0.5) + cy
    x3 = ax + bx + cx
    y3 = ay + by + cy
    return (x1, y1), (x2, y2), (x3, y3)


def calcCubicPoints(a, b, c, d):
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    x1 = dx
    y1 = dy
    x2 = (cx / 3.0) + dx
    y2 = (cy / 3.0) + dy
    x3 = (bx + cx) / 3.0 + x2
    y3 = (by + cy) / 3.0 + y2
    x4 = ax + dx + cx + bx
    y4 = ay + dy + cy + by
    return (x1, y1), (x2, y2), (x3, y3), (x4, y4)


@cython.cfunc
@cython.inline
@cython.locals(
    a=cython.complex,
    b=cython.complex,
    c=cython.complex,
    d=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
    p4=cython.complex,
)
def calcCubicPointsC(a, b, c, d):
    p2 = c * (1 / 3) + d
    p3 = (b + c) * (1 / 3) + p2
    p4 = a + b + c + d
    return (d, p2, p3, p4)


#
# Point at time
#


def linePointAtT(pt1, pt2, t):
    """Finds the point at time `t` on a line.

    Args:
        pt1, pt2: Coordinates of the line as 2D tuples.
        t: The time along the line.

    Returns:
        A 2D tuple with the coordinates of the point.
    """
    return ((pt1[0] * (1 - t) + pt2[0] * t), (pt1[1] * (1 - t) + pt2[1] * t))


def quadraticPointAtT(pt1, pt2, pt3, t):
    """Finds the point at time `t` on a quadratic curve.

    Args:
        pt1, pt2, pt3: Coordinates of the curve as 2D tuples.
        t: The time along the curve.

    Returns:
        A 2D tuple with the coordinates of the point.
    """
    x = (1 - t) * (1 - t) * pt1[0] + 2 * (1 - t) * t * pt2[0] + t * t * pt3[0]
    y = (1 - t) * (1 - t) * pt1[1] + 2 * (1 - t) * t * pt2[1] + t * t * pt3[1]
    return (x, y)


def cubicPointAtT(pt1, pt2, pt3, pt4, t):
    """Finds the point at time `t` on a cubic curve.

    Args:
        pt1, pt2, pt3, pt4: Coordinates of the curve as 2D tuples.
        t: The time along the curve.

    Returns:
        A 2D tuple with the coordinates of the point.
    """
    t2 = t * t
    _1_t = 1 - t
    _1_t_2 = _1_t * _1_t
    x = (
        _1_t_2 * _1_t * pt1[0]
        + 3 * (_1_t_2 * t * pt2[0] + _1_t * t2 * pt3[0])
        + t2 * t * pt4[0]
    )
    y = (
        _1_t_2 * _1_t * pt1[1]
        + 3 * (_1_t_2 * t * pt2[1] + _1_t * t2 * pt3[1])
        + t2 * t * pt4[1]
    )
    return (x, y)


@cython.returns(cython.complex)
@cython.locals(
    t=cython.double,
    pt1=cython.complex,
    pt2=cython.complex,
    pt3=cython.complex,
    pt4=cython.complex,
)
@cython.locals(t2=cython.double, _1_t=cython.double, _1_t_2=cython.double)
def cubicPointAtTC(pt1, pt2, pt3, pt4, t):
    """Finds the point at time `t` on a cubic curve.

    Args:
        pt1, pt2, pt3, pt4: Coordinates of the curve as complex numbers.
        t: The time along the curve.

    Returns:
        A complex number with the coordinates of the point.
    """
    t2 = t * t
    _1_t = 1 - t
    _1_t_2 = _1_t * _1_t
    return _1_t_2 * _1_t * pt1 + 3 * (_1_t_2 * t * pt2 + _1_t * t2 * pt3) + t2 * t * pt4


def segmentPointAtT(seg, t):
    if len(seg) == 2:
        return linePointAtT(*seg, t)
    elif len(seg) == 3:
        return quadraticPointAtT(*seg, t)
    elif len(seg) == 4:
        return cubicPointAtT(*seg, t)
    raise ValueError("Unknown curve degree")


#
# Intersection finders
#


def _line_t_of_pt(s, e, pt):
    sx, sy = s
    ex, ey = e
    px, py = pt
    if abs(sx - ex) < epsilon and abs(sy - ey) < epsilon:
        # Line is a point!
        return -1
    # Use the largest
    if abs(sx - ex) > abs(sy - ey):
        return (px - sx) / (ex - sx)
    else:
        return (py - sy) / (ey - sy)


def _both_points_are_on_same_side_of_origin(a, b, origin):
    xDiff = (a[0] - origin[0]) * (b[0] - origin[0])
    yDiff = (a[1] - origin[1]) * (b[1] - origin[1])
    return not (xDiff <= 0.0 and yDiff <= 0.0)


def lineLineIntersections(s1, e1, s2, e2):
    """Finds intersections between two line segments.

    Args:
        s1, e1: Coordinates of the first line as 2D tuples.
        s2, e2: Coordinates of the second line as 2D tuples.

    Returns:
        A list of ``Intersection`` objects, each object having ``pt``, ``t1``
        and ``t2`` attributes containing the intersection point, time on first
        segment and time on second segment respectively.

    Examples::

        >>> a = lineLineIntersections( (310,389), (453, 222), (289, 251), (447, 367))
        >>> len(a)
        1
        >>> intersection = a[0]
        >>> intersection.pt
        (374.44882952482897, 313.73458370177315)
        >>> (intersection.t1, intersection.t2)
        (0.45069111555824465, 0.5408153767394238)
    """
    s1x, s1y = s1
    e1x, e1y = e1
    s2x, s2y = s2
    e2x, e2y = e2
    if (
        math.isclose(s2x, e2x) and math.isclose(s1x, e1x) and not math.isclose(s1x, s2x)
    ):  # Parallel vertical
        return []
    if (
        math.isclose(s2y, e2y) and math.isclose(s1y, e1y) and not math.isclose(s1y, s2y)
    ):  # Parallel horizontal
        return []
    if math.isclose(s2x, e2x) and math.isclose(s2y, e2y):  # Line segment is tiny
        return []
    if math.isclose(s1x, e1x) and math.isclose(s1y, e1y):  # Line segment is tiny
        return []
    if math.isclose(e1x, s1x):
        x = s1x
        slope34 = (e2y - s2y) / (e2x - s2x)
        y = slope34 * (x - s2x) + s2y
        pt = (x, y)
        return [
            Intersection(
                pt=pt, t1=_line_t_of_pt(s1, e1, pt), t2=_line_t_of_pt(s2, e2, pt)
            )
        ]
    if math.isclose(s2x, e2x):
        x = s2x
        slope12 = (e1y - s1y) / (e1x - s1x)
        y = slope12 * (x - s1x) + s1y
        pt = (x, y)
        return [
            Intersection(
                pt=pt, t1=_line_t_of_pt(s1, e1, pt), t2=_line_t_of_pt(s2, e2, pt)
            )
        ]

    slope12 = (e1y - s1y) / (e1x - s1x)
    slope34 = (e2y - s2y) / (e2x - s2x)
    if math.isclose(slope12, slope34):
        return []
    x = (slope12 * s1x - s1y - slope34 * s2x + s2y) / (slope12 - slope34)
    y = slope12 * (x - s1x) + s1y
    pt = (x, y)
    if _both_points_are_on_same_side_of_origin(
        pt, e1, s1
    ) and _both_points_are_on_same_side_of_origin(pt, s2, e2):
        return [
            Intersection(
                pt=pt, t1=_line_t_of_pt(s1, e1, pt), t2=_line_t_of_pt(s2, e2, pt)
            )
        ]
    return []


def _alignment_transformation(segment):
    # Returns a transformation which aligns a segment horizontally at the
    # origin. Apply this transformation to curves and root-find to find
    # intersections with the segment.
    start = segment[0]
    end = segment[-1]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    return Identity.rotate(-angle).translate(-start[0], -start[1])


def _curve_line_intersections_t(curve, line):
    aligned_curve = _alignment_transformation(line).transformPoints(curve)
    if len(curve) == 3:
        a, b, c = calcQuadraticParameters(*aligned_curve)
        intersections = solveQuadratic(a[1], b[1], c[1])
    elif len(curve) == 4:
        a, b, c, d = calcCubicParameters(*aligned_curve)
        intersections = solveCubic(a[1], b[1], c[1], d[1])
    else:
        raise ValueError("Unknown curve degree")
    return sorted(i for i in intersections if 0.0 <= i <= 1)


def curveLineIntersections(curve, line):
    """Finds intersections between a curve and a line.

    Args:
        curve: List of coordinates of the curve segment as 2D tuples.
        line: List of coordinates of the line segment as 2D tuples.

    Returns:
        A list of ``Intersection`` objects, each object having ``pt``, ``t1``
        and ``t2`` attributes containing the intersection point, time on first
        segment and time on second segment respectively.

    Examples::
        >>> curve = [ (100, 240), (30, 60), (210, 230), (160, 30) ]
        >>> line  = [ (25, 260), (230, 20) ]
        >>> intersections = curveLineIntersections(curve, line)
        >>> len(intersections)
        3
        >>> intersections[0].pt
        (84.9000930760723, 189.87306176459828)
    """
    if len(curve) == 3:
        pointFinder = quadraticPointAtT
    elif len(curve) == 4:
        pointFinder = cubicPointAtT
    else:
        raise ValueError("Unknown curve degree")
    intersections = []
    for t in _curve_line_intersections_t(curve, line):
        pt = pointFinder(*curve, t)
        # Back-project the point onto the line, to avoid problems with
        # numerical accuracy in the case of vertical and horizontal lines
        line_t = _line_t_of_pt(*line, pt)
        pt = linePointAtT(*line, line_t)
        intersections.append(Intersection(pt=pt, t1=t, t2=line_t))
    return intersections


def _curve_bounds(c):
    if len(c) == 3:
        return calcQuadraticBounds(*c)
    elif len(c) == 4:
        return calcCubicBounds(*c)
    raise ValueError("Unknown curve degree")


def _split_segment_at_t(c, t):
    if len(c) == 2:
        s, e = c
        midpoint = linePointAtT(s, e, t)
        return [(s, midpoint), (midpoint, e)]
    if len(c) == 3:
        return splitQuadraticAtT(*c, t)
    elif len(c) == 4:
        return splitCubicAtT(*c, t)
    raise ValueError("Unknown curve degree")


def _curve_curve_intersections_t(
    curve1, curve2, precision=1e-3, range1=None, range2=None
):
    bounds1 = _curve_bounds(curve1)
    bounds2 = _curve_bounds(curve2)

    if not range1:
        range1 = (0.0, 1.0)
    if not range2:
        range2 = (0.0, 1.0)

    # If bounds don't intersect, go home
    intersects, _ = sectRect(bounds1, bounds2)
    if not intersects:
        return []

    def midpoint(r):
        return 0.5 * (r[0] + r[1])

    # If they do overlap but they're tiny, approximate
    if rectArea(bounds1) < precision and rectArea(bounds2) < precision:
        return [(midpoint(range1), midpoint(range2))]

    c11, c12 = _split_segment_at_t(curve1, 0.5)
    c11_range = (range1[0], midpoint(range1))
    c12_range = (midpoint(range1), range1[1])

    c21, c22 = _split_segment_at_t(curve2, 0.5)
    c21_range = (range2[0], midpoint(range2))
    c22_range = (midpoint(range2), range2[1])

    found = []
    found.extend(
        _curve_curve_intersections_t(
            c11, c21, precision, range1=c11_range, range2=c21_range
        )
    )
    found.extend(
        _curve_curve_intersections_t(
            c12, c21, precision, range1=c12_range, range2=c21_range
        )
    )
    found.extend(
        _curve_curve_intersections_t(
            c11, c22, precision, range1=c11_range, range2=c22_range
        )
    )
    found.extend(
        _curve_curve_intersections_t(
            c12, c22, precision, range1=c12_range, range2=c22_range
        )
    )

    unique_key = lambda ts: (int(ts[0] / precision), int(ts[1] / precision))
    seen = set()
    unique_values = []

    for ts in found:
        key = unique_key(ts)
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(ts)

    return unique_values


def _is_linelike(segment):
    maybeline = _alignment_transformation(segment).transformPoints(segment)
    return all(math.isclose(p[1], 0.0) for p in maybeline)


def curveCurveIntersections(curve1, curve2):
    """Finds intersections between a curve and a curve.

    Args:
        curve1: List of coordinates of the first curve segment as 2D tuples.
        curve2: List of coordinates of the second curve segment as 2D tuples.

    Returns:
        A list of ``Intersection`` objects, each object having ``pt``, ``t1``
        and ``t2`` attributes containing the intersection point, time on first
        segment and time on second segment respectively.

    Examples::
        >>> curve1 = [ (10,100), (90,30), (40,140), (220,220) ]
        >>> curve2 = [ (5,150), (180,20), (80,250), (210,190) ]
        >>> intersections = curveCurveIntersections(curve1, curve2)
        >>> len(intersections)
        3
        >>> intersections[0].pt
        (81.7831487395506, 109.88904552375288)
    """
    if _is_linelike(curve1):
        line1 = curve1[0], curve1[-1]
        if _is_linelike(curve2):
            line2 = curve2[0], curve2[-1]
            return lineLineIntersections(*line1, *line2)
        else:
            return curveLineIntersections(curve2, line1)
    elif _is_linelike(curve2):
        line2 = curve2[0], curve2[-1]
        return curveLineIntersections(curve1, line2)

    intersection_ts = _curve_curve_intersections_t(curve1, curve2)
    return [
        Intersection(pt=segmentPointAtT(curve1, ts[0]), t1=ts[0], t2=ts[1])
        for ts in intersection_ts
    ]


def segmentSegmentIntersections(seg1, seg2):
    """Finds intersections between two segments.

    Args:
        seg1: List of coordinates of the first segment as 2D tuples.
        seg2: List of coordinates of the second segment as 2D tuples.

    Returns:
        A list of ``Intersection`` objects, each object having ``pt``, ``t1``
        and ``t2`` attributes containing the intersection point, time on first
        segment and time on second segment respectively.

    Examples::
        >>> curve1 = [ (10,100), (90,30), (40,140), (220,220) ]
        >>> curve2 = [ (5,150), (180,20), (80,250), (210,190) ]
        >>> intersections = segmentSegmentIntersections(curve1, curve2)
        >>> len(intersections)
        3
        >>> intersections[0].pt
        (81.7831487395506, 109.88904552375288)
        >>> curve3 = [ (100, 240), (30, 60), (210, 230), (160, 30) ]
        >>> line  = [ (25, 260), (230, 20) ]
        >>> intersections = segmentSegmentIntersections(curve3, line)
        >>> len(intersections)
        3
        >>> intersections[0].pt
        (84.9000930760723, 189.87306176459828)

    """
    # Arrange by degree
    swapped = False
    if len(seg2) > len(seg1):
        seg2, seg1 = seg1, seg2
        swapped = True
    if len(seg1) > 2:
        if len(seg2) > 2:
            intersections = curveCurveIntersections(seg1, seg2)
        else:
            intersections = curveLineIntersections(seg1, seg2)
    elif len(seg1) == 2 and len(seg2) == 2:
        intersections = lineLineIntersections(*seg1, *seg2)
    else:
        raise ValueError("Couldn't work out which intersection function to use")
    if not swapped:
        return intersections
    return [Intersection(pt=i.pt, t1=i.t2, t2=i.t1) for i in intersections]


def _segmentrepr(obj):
    """
    >>> _segmentrepr([1, [2, 3], [], [[2, [3, 4], [0.1, 2.2]]]])
    '(1, (2, 3), (), ((2, (3, 4), (0.1, 2.2))))'
    """
    try:
        it = iter(obj)
    except TypeError:
        return "%g" % obj
    else:
        return "(%s)" % ", ".join(_segmentrepr(x) for x in it)


def printSegments(segments):
    """Helper for the doctests, displaying each segment in a list of
    segments on a single line as a tuple.
    """
    for segment in segments:
        print(_segmentrepr(segment))


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\psCharStrings.py ===
"""psCharStrings.py -- module implementing various kinds of CharStrings:
CFF dictionary data and Type1/Type2 CharStrings.
"""

from fontTools.misc.fixedTools import (
    fixedToFloat,
    floatToFixed,
    floatToFixedToStr,
    strToFixedToFloat,
)
from fontTools.misc.textTools import bytechr, byteord, bytesjoin, strjoin
from fontTools.pens.boundsPen import BoundsPen
import struct
import logging


log = logging.getLogger(__name__)


def read_operator(self, b0, data, index):
    if b0 == 12:
        op = (b0, byteord(data[index]))
        index = index + 1
    else:
        op = b0
    try:
        operator = self.operators[op]
    except KeyError:
        return None, index
    value = self.handle_operator(operator)
    return value, index


def read_byte(self, b0, data, index):
    return b0 - 139, index


def read_smallInt1(self, b0, data, index):
    b1 = byteord(data[index])
    return (b0 - 247) * 256 + b1 + 108, index + 1


def read_smallInt2(self, b0, data, index):
    b1 = byteord(data[index])
    return -(b0 - 251) * 256 - b1 - 108, index + 1


def read_shortInt(self, b0, data, index):
    (value,) = struct.unpack(">h", data[index : index + 2])
    return value, index + 2


def read_longInt(self, b0, data, index):
    (value,) = struct.unpack(">l", data[index : index + 4])
    return value, index + 4


def read_fixed1616(self, b0, data, index):
    (value,) = struct.unpack(">l", data[index : index + 4])
    return fixedToFloat(value, precisionBits=16), index + 4


def read_reserved(self, b0, data, index):
    assert NotImplementedError
    return NotImplemented, index


def read_realNumber(self, b0, data, index):
    number = ""
    while True:
        b = byteord(data[index])
        index = index + 1
        nibble0 = (b & 0xF0) >> 4
        nibble1 = b & 0x0F
        if nibble0 == 0xF:
            break
        number = number + realNibbles[nibble0]
        if nibble1 == 0xF:
            break
        number = number + realNibbles[nibble1]
    return float(number), index


t1OperandEncoding = [None] * 256
t1OperandEncoding[0:32] = (32) * [read_operator]
t1OperandEncoding[32:247] = (247 - 32) * [read_byte]
t1OperandEncoding[247:251] = (251 - 247) * [read_smallInt1]
t1OperandEncoding[251:255] = (255 - 251) * [read_smallInt2]
t1OperandEncoding[255] = read_longInt
assert len(t1OperandEncoding) == 256

t2OperandEncoding = t1OperandEncoding[:]
t2OperandEncoding[28] = read_shortInt
t2OperandEncoding[255] = read_fixed1616

cffDictOperandEncoding = t2OperandEncoding[:]
cffDictOperandEncoding[29] = read_longInt
cffDictOperandEncoding[30] = read_realNumber
cffDictOperandEncoding[255] = read_reserved


realNibbles = [
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    ".",
    "E",
    "E-",
    None,
    "-",
]
realNibblesDict = {v: i for i, v in enumerate(realNibbles)}

maxOpStack = 193


def buildOperatorDict(operatorList):
    oper = {}
    opc = {}
    for item in operatorList:
        if len(item) == 2:
            oper[item[0]] = item[1]
        else:
            oper[item[0]] = item[1:]
        if isinstance(item[0], tuple):
            opc[item[1]] = item[0]
        else:
            opc[item[1]] = (item[0],)
    return oper, opc


t2Operators = [
    # 	opcode		name
    (1, "hstem"),
    (3, "vstem"),
    (4, "vmoveto"),
    (5, "rlineto"),
    (6, "hlineto"),
    (7, "vlineto"),
    (8, "rrcurveto"),
    (10, "callsubr"),
    (11, "return"),
    (14, "endchar"),
    (15, "vsindex"),
    (16, "blend"),
    (18, "hstemhm"),
    (19, "hintmask"),
    (20, "cntrmask"),
    (21, "rmoveto"),
    (22, "hmoveto"),
    (23, "vstemhm"),
    (24, "rcurveline"),
    (25, "rlinecurve"),
    (26, "vvcurveto"),
    (27, "hhcurveto"),
    # 	(28,		'shortint'),  # not really an operator
    (29, "callgsubr"),
    (30, "vhcurveto"),
    (31, "hvcurveto"),
    ((12, 0), "ignore"),  # dotsection. Yes, there a few very early OTF/CFF
    # fonts with this deprecated operator. Just ignore it.
    ((12, 3), "and"),
    ((12, 4), "or"),
    ((12, 5), "not"),
    ((12, 8), "store"),
    ((12, 9), "abs"),
    ((12, 10), "add"),
    ((12, 11), "sub"),
    ((12, 12), "div"),
    ((12, 13), "load"),
    ((12, 14), "neg"),
    ((12, 15), "eq"),
    ((12, 18), "drop"),
    ((12, 20), "put"),
    ((12, 21), "get"),
    ((12, 22), "ifelse"),
    ((12, 23), "random"),
    ((12, 24), "mul"),
    ((12, 26), "sqrt"),
    ((12, 27), "dup"),
    ((12, 28), "exch"),
    ((12, 29), "index"),
    ((12, 30), "roll"),
    ((12, 34), "hflex"),
    ((12, 35), "flex"),
    ((12, 36), "hflex1"),
    ((12, 37), "flex1"),
]


def getIntEncoder(format):
    if format == "cff":
        twoByteOp = bytechr(28)
        fourByteOp = bytechr(29)
    elif format == "t1":
        twoByteOp = None
        fourByteOp = bytechr(255)
    else:
        assert format == "t2"
        twoByteOp = bytechr(28)
        fourByteOp = None

    def encodeInt(
        value,
        fourByteOp=fourByteOp,
        bytechr=bytechr,
        pack=struct.pack,
        unpack=struct.unpack,
        twoByteOp=twoByteOp,
    ):
        if -107 <= value <= 107:
            code = bytechr(value + 139)
        elif 108 <= value <= 1131:
            value = value - 108
            code = bytechr((value >> 8) + 247) + bytechr(value & 0xFF)
        elif -1131 <= value <= -108:
            value = -value - 108
            code = bytechr((value >> 8) + 251) + bytechr(value & 0xFF)
        elif twoByteOp is not None and -32768 <= value <= 32767:
            code = twoByteOp + pack(">h", value)
        elif fourByteOp is None:
            # Backwards compatible hack: due to a previous bug in FontTools,
            # 16.16 fixed numbers were written out as 4-byte ints. When
            # these numbers were small, they were wrongly written back as
            # small ints instead of 4-byte ints, breaking round-tripping.
            # This here workaround doesn't do it any better, since we can't
            # distinguish anymore between small ints that were supposed to
            # be small fixed numbers and small ints that were just small
            # ints. Hence the warning.
            log.warning(
                "4-byte T2 number got passed to the "
                "IntType handler. This should happen only when reading in "
                "old XML files.\n"
            )
            code = bytechr(255) + pack(">l", value)
        else:
            code = fourByteOp + pack(">l", value)
        return code

    return encodeInt


encodeIntCFF = getIntEncoder("cff")
encodeIntT1 = getIntEncoder("t1")
encodeIntT2 = getIntEncoder("t2")


def encodeFixed(f, pack=struct.pack):
    """For T2 only"""
    value = floatToFixed(f, precisionBits=16)
    if value & 0xFFFF == 0:  # check if the fractional part is zero
        return encodeIntT2(value >> 16)  # encode only the integer part
    else:
        return b"\xff" + pack(">l", value)  # encode the entire fixed point value


realZeroBytes = bytechr(30) + bytechr(0xF)


def encodeFloat(f):
    # For CFF only, used in cffLib
    if f == 0.0:  # 0.0 == +0.0 == -0.0
        return realZeroBytes
    # Note: 14 decimal digits seems to be the limitation for CFF real numbers
    # in macOS. However, we use 8 here to match the implementation of AFDKO.
    s = "%.8G" % f
    if s[:2] == "0.":
        s = s[1:]
    elif s[:3] == "-0.":
        s = "-" + s[2:]
    elif s.endswith("000"):
        significantDigits = s.rstrip("0")
        s = "%sE%d" % (significantDigits, len(s) - len(significantDigits))
    else:
        dotIndex = s.find(".")
        eIndex = s.find("E")
        if dotIndex != -1 and eIndex != -1:
            integerPart = s[:dotIndex]
            fractionalPart = s[dotIndex + 1 : eIndex]
            exponent = int(s[eIndex + 1 :])
            newExponent = exponent - len(fractionalPart)
            if newExponent == 1:
                s = "%s%s0" % (integerPart, fractionalPart)
            else:
                s = "%s%sE%d" % (integerPart, fractionalPart, newExponent)
    if s.startswith((".0", "-.0")):
        sign, s = s.split(".", 1)
        s = "%s%sE-%d" % (sign, s.lstrip("0"), len(s))
    nibbles = []
    while s:
        c = s[0]
        s = s[1:]
        if c == "E":
            c2 = s[:1]
            if c2 == "-":
                s = s[1:]
                c = "E-"
            elif c2 == "+":
                s = s[1:]
            if s.startswith("0"):
                s = s[1:]
        nibbles.append(realNibblesDict[c])
    nibbles.append(0xF)
    if len(nibbles) % 2:
        nibbles.append(0xF)
    d = bytechr(30)
    for i in range(0, len(nibbles), 2):
        d = d + bytechr(nibbles[i] << 4 | nibbles[i + 1])
    return d


class CharStringCompileError(Exception):
    pass


class SimpleT2Decompiler(object):
    def __init__(self, localSubrs, globalSubrs, private=None, blender=None):
        self.localSubrs = localSubrs
        self.localBias = calcSubrBias(localSubrs)
        self.globalSubrs = globalSubrs
        self.globalBias = calcSubrBias(globalSubrs)
        self.private = private
        self.blender = blender
        self.reset()

    def reset(self):
        self.callingStack = []
        self.operandStack = []
        self.hintCount = 0
        self.hintMaskBytes = 0
        self.numRegions = 0
        self.vsIndex = 0

    def execute(self, charString):
        self.callingStack.append(charString)
        needsDecompilation = charString.needsDecompilation()
        if needsDecompilation:
            program = []
            pushToProgram = program.append
        else:
            pushToProgram = lambda x: None
        pushToStack = self.operandStack.append
        index = 0
        while True:
            token, isOperator, index = charString.getToken(index)
            if token is None:
                break  # we're done!
            pushToProgram(token)
            if isOperator:
                handlerName = "op_" + token
                handler = getattr(self, handlerName, None)
                if handler is not None:
                    rv = handler(index)
                    if rv:
                        hintMaskBytes, index = rv
                        pushToProgram(hintMaskBytes)
                else:
                    self.popall()
            else:
                pushToStack(token)
        if needsDecompilation:
            charString.setProgram(program)
        del self.callingStack[-1]

    def pop(self):
        value = self.operandStack[-1]
        del self.operandStack[-1]
        return value

    def popall(self):
        stack = self.operandStack[:]
        self.operandStack[:] = []
        return stack

    def push(self, value):
        self.operandStack.append(value)

    def op_return(self, index):
        if self.operandStack:
            pass

    def op_endchar(self, index):
        pass

    def op_ignore(self, index):
        pass

    def op_callsubr(self, index):
        subrIndex = self.pop()
        subr = self.localSubrs[subrIndex + self.localBias]
        self.execute(subr)

    def op_callgsubr(self, index):
        subrIndex = self.pop()
        subr = self.globalSubrs[subrIndex + self.globalBias]
        self.execute(subr)

    def op_hstem(self, index):
        self.countHints()

    def op_vstem(self, index):
        self.countHints()

    def op_hstemhm(self, index):
        self.countHints()

    def op_vstemhm(self, index):
        self.countHints()

    def op_hintmask(self, index):
        if not self.hintMaskBytes:
            self.countHints()
            self.hintMaskBytes = (self.hintCount + 7) // 8
        hintMaskBytes, index = self.callingStack[-1].getBytes(index, self.hintMaskBytes)
        return hintMaskBytes, index

    op_cntrmask = op_hintmask

    def countHints(self):
        args = self.popall()
        self.hintCount = self.hintCount + len(args) // 2

    # misc
    def op_and(self, index):
        raise NotImplementedError

    def op_or(self, index):
        raise NotImplementedError

    def op_not(self, index):
        raise NotImplementedError

    def op_store(self, index):
        raise NotImplementedError

    def op_abs(self, index):
        raise NotImplementedError

    def op_add(self, index):
        raise NotImplementedError

    def op_sub(self, index):
        raise NotImplementedError

    def op_div(self, index):
        raise NotImplementedError

    def op_load(self, index):
        raise NotImplementedError

    def op_neg(self, index):
        raise NotImplementedError

    def op_eq(self, index):
        raise NotImplementedError

    def op_drop(self, index):
        raise NotImplementedError

    def op_put(self, index):
        raise NotImplementedError

    def op_get(self, index):
        raise NotImplementedError

    def op_ifelse(self, index):
        raise NotImplementedError

    def op_random(self, index):
        raise NotImplementedError

    def op_mul(self, index):
        raise NotImplementedError

    def op_sqrt(self, index):
        raise NotImplementedError

    def op_dup(self, index):
        raise NotImplementedError

    def op_exch(self, index):
        raise NotImplementedError

    def op_index(self, index):
        raise NotImplementedError

    def op_roll(self, index):
        raise NotImplementedError

    def op_blend(self, index):
        if self.numRegions == 0:
            self.numRegions = self.private.getNumRegions()
        numBlends = self.pop()
        numOps = numBlends * (self.numRegions + 1)
        if self.blender is None:
            del self.operandStack[
                -(numOps - numBlends) :
            ]  # Leave the default operands on the stack.
        else:
            argi = len(self.operandStack) - numOps
            end_args = tuplei = argi + numBlends
            while argi < end_args:
                next_ti = tuplei + self.numRegions
                deltas = self.operandStack[tuplei:next_ti]
                delta = self.blender(self.vsIndex, deltas)
                self.operandStack[argi] += delta
                tuplei = next_ti
                argi += 1
            self.operandStack[end_args:] = []

    def op_vsindex(self, index):
        vi = self.pop()
        self.vsIndex = vi
        self.numRegions = self.private.getNumRegions(vi)


t1Operators = [
    # 	opcode		name
    (1, "hstem"),
    (3, "vstem"),
    (4, "vmoveto"),
    (5, "rlineto"),
    (6, "hlineto"),
    (7, "vlineto"),
    (8, "rrcurveto"),
    (9, "closepath"),
    (10, "callsubr"),
    (11, "return"),
    (13, "hsbw"),
    (14, "endchar"),
    (21, "rmoveto"),
    (22, "hmoveto"),
    (30, "vhcurveto"),
    (31, "hvcurveto"),
    ((12, 0), "dotsection"),
    ((12, 1), "vstem3"),
    ((12, 2), "hstem3"),
    ((12, 6), "seac"),
    ((12, 7), "sbw"),
    ((12, 12), "div"),
    ((12, 16), "callothersubr"),
    ((12, 17), "pop"),
    ((12, 33), "setcurrentpoint"),
]


class T2WidthExtractor(SimpleT2Decompiler):
    def __init__(
        self,
        localSubrs,
        globalSubrs,
        nominalWidthX,
        defaultWidthX,
        private=None,
        blender=None,
    ):
        SimpleT2Decompiler.__init__(self, localSubrs, globalSubrs, private, blender)
        self.nominalWidthX = nominalWidthX
        self.defaultWidthX = defaultWidthX

    def reset(self):
        SimpleT2Decompiler.reset(self)
        self.gotWidth = 0
        self.width = 0

    def popallWidth(self, evenOdd=0):
        args = self.popall()
        if not self.gotWidth:
            if evenOdd ^ (len(args) % 2):
                # For CFF2 charstrings, this should never happen
                assert (
                    self.defaultWidthX is not None
                ), "CFF2 CharStrings must not have an initial width value"
                self.width = self.nominalWidthX + args[0]
                args = args[1:]
            else:
                self.width = self.defaultWidthX
            self.gotWidth = 1
        return args

    def countHints(self):
        args = self.popallWidth()
        self.hintCount = self.hintCount + len(args) // 2

    def op_rmoveto(self, index):
        self.popallWidth()

    def op_hmoveto(self, index):
        self.popallWidth(1)

    def op_vmoveto(self, index):
        self.popallWidth(1)

    def op_endchar(self, index):
        self.popallWidth()


class T2OutlineExtractor(T2WidthExtractor):
    def __init__(
        self,
        pen,
        localSubrs,
        globalSubrs,
        nominalWidthX,
        defaultWidthX,
        private=None,
        blender=None,
    ):
        T2WidthExtractor.__init__(
            self,
            localSubrs,
            globalSubrs,
            nominalWidthX,
            defaultWidthX,
            private,
            blender,
        )
        self.pen = pen
        self.subrLevel = 0

    def reset(self):
        T2WidthExtractor.reset(self)
        self.currentPoint = (0, 0)
        self.sawMoveTo = 0
        self.subrLevel = 0

    def execute(self, charString):
        self.subrLevel += 1
        super().execute(charString)
        self.subrLevel -= 1
        if self.subrLevel == 0:
            self.endPath()

    def _nextPoint(self, point):
        x, y = self.currentPoint
        point = x + point[0], y + point[1]
        self.currentPoint = point
        return point

    def rMoveTo(self, point):
        self.pen.moveTo(self._nextPoint(point))
        self.sawMoveTo = 1

    def rLineTo(self, point):
        if not self.sawMoveTo:
            self.rMoveTo((0, 0))
        self.pen.lineTo(self._nextPoint(point))

    def rCurveTo(self, pt1, pt2, pt3):
        if not self.sawMoveTo:
            self.rMoveTo((0, 0))
        nextPoint = self._nextPoint
        self.pen.curveTo(nextPoint(pt1), nextPoint(pt2), nextPoint(pt3))

    def closePath(self):
        if self.sawMoveTo:
            self.pen.closePath()
        self.sawMoveTo = 0

    def endPath(self):
        # In T2 there are no open paths, so always do a closePath when
        # finishing a sub path. We avoid spurious calls to closePath()
        # because its a real T1 op we're emulating in T2 whereas
        # endPath() is just a means to that emulation
        if self.sawMoveTo:
            self.closePath()

    #
    # hint operators
    #
    # def op_hstem(self, index):
    # 	self.countHints()
    # def op_vstem(self, index):
    # 	self.countHints()
    # def op_hstemhm(self, index):
    # 	self.countHints()
    # def op_vstemhm(self, index):
    # 	self.countHints()
    # def op_hintmask(self, index):
    # 	self.countHints()
    # def op_cntrmask(self, index):
    # 	self.countHints()

    #
    # path constructors, moveto
    #
    def op_rmoveto(self, index):
        self.endPath()
        self.rMoveTo(self.popallWidth())

    def op_hmoveto(self, index):
        self.endPath()
        self.rMoveTo((self.popallWidth(1)[0], 0))

    def op_vmoveto(self, index):
        self.endPath()
        self.rMoveTo((0, self.popallWidth(1)[0]))

    def op_endchar(self, index):
        self.endPath()
        args = self.popallWidth()
        if args:
            from fontTools.encodings.StandardEncoding import StandardEncoding

            # endchar can do seac accent bulding; The T2 spec says it's deprecated,
            # but recent software that shall remain nameless does output it.
            adx, ady, bchar, achar = args
            baseGlyph = StandardEncoding[bchar]
            self.pen.addComponent(baseGlyph, (1, 0, 0, 1, 0, 0))
            accentGlyph = StandardEncoding[achar]
            self.pen.addComponent(accentGlyph, (1, 0, 0, 1, adx, ady))

    #
    # path constructors, lines
    #
    def op_rlineto(self, index):
        args = self.popall()
        for i in range(0, len(args), 2):
            point = args[i : i + 2]
            self.rLineTo(point)

    def op_hlineto(self, index):
        self.alternatingLineto(1)

    def op_vlineto(self, index):
        self.alternatingLineto(0)

    #
    # path constructors, curves
    #
    def op_rrcurveto(self, index):
        """{dxa dya dxb dyb dxc dyc}+ rrcurveto"""
        args = self.popall()
        for i in range(0, len(args), 6):
            (
                dxa,
                dya,
                dxb,
                dyb,
                dxc,
                dyc,
            ) = args[i : i + 6]
            self.rCurveTo((dxa, dya), (dxb, dyb), (dxc, dyc))

    def op_rcurveline(self, index):
        """{dxa dya dxb dyb dxc dyc}+ dxd dyd rcurveline"""
        args = self.popall()
        for i in range(0, len(args) - 2, 6):
            dxb, dyb, dxc, dyc, dxd, dyd = args[i : i + 6]
            self.rCurveTo((dxb, dyb), (dxc, dyc), (dxd, dyd))
        self.rLineTo(args[-2:])

    def op_rlinecurve(self, index):
        """{dxa dya}+ dxb dyb dxc dyc dxd dyd rlinecurve"""
        args = self.popall()
        lineArgs = args[:-6]
        for i in range(0, len(lineArgs), 2):
            self.rLineTo(lineArgs[i : i + 2])
        dxb, dyb, dxc, dyc, dxd, dyd = args[-6:]
        self.rCurveTo((dxb, dyb), (dxc, dyc), (dxd, dyd))

    def op_vvcurveto(self, index):
        "dx1? {dya dxb dyb dyc}+ vvcurveto"
        args = self.popall()
        if len(args) % 2:
            dx1 = args[0]
            args = args[1:]
        else:
            dx1 = 0
        for i in range(0, len(args), 4):
            dya, dxb, dyb, dyc = args[i : i + 4]
            self.rCurveTo((dx1, dya), (dxb, dyb), (0, dyc))
            dx1 = 0

    def op_hhcurveto(self, index):
        """dy1? {dxa dxb dyb dxc}+ hhcurveto"""
        args = self.popall()
        if len(args) % 2:
            dy1 = args[0]
            args = args[1:]
        else:
            dy1 = 0
        for i in range(0, len(args), 4):
            dxa, dxb, dyb, dxc = args[i : i + 4]
            self.rCurveTo((dxa, dy1), (dxb, dyb), (dxc, 0))
            dy1 = 0

    def op_vhcurveto(self, index):
        """dy1 dx2 dy2 dx3 {dxa dxb dyb dyc dyd dxe dye dxf}* dyf? vhcurveto (30)
        {dya dxb dyb dxc dxd dxe dye dyf}+ dxf? vhcurveto
        """
        args = self.popall()
        while args:
            args = self.vcurveto(args)
            if args:
                args = self.hcurveto(args)

    def op_hvcurveto(self, index):
        """dx1 dx2 dy2 dy3 {dya dxb dyb dxc dxd dxe dye dyf}* dxf?
        {dxa dxb dyb dyc dyd dxe dye dxf}+ dyf?
        """
        args = self.popall()
        while args:
            args = self.hcurveto(args)
            if args:
                args = self.vcurveto(args)

    #
    # path constructors, flex
    #
    def op_hflex(self, index):
        dx1, dx2, dy2, dx3, dx4, dx5, dx6 = self.popall()
        dy1 = dy3 = dy4 = dy6 = 0
        dy5 = -dy2
        self.rCurveTo((dx1, dy1), (dx2, dy2), (dx3, dy3))
        self.rCurveTo((dx4, dy4), (dx5, dy5), (dx6, dy6))

    def op_flex(self, index):
        dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4, dx5, dy5, dx6, dy6, fd = self.popall()
        self.rCurveTo((dx1, dy1), (dx2, dy2), (dx3, dy3))
        self.rCurveTo((dx4, dy4), (dx5, dy5), (dx6, dy6))

    def op_hflex1(self, index):
        dx1, dy1, dx2, dy2, dx3, dx4, dx5, dy5, dx6 = self.popall()
        dy3 = dy4 = 0
        dy6 = -(dy1 + dy2 + dy3 + dy4 + dy5)

        self.rCurveTo((dx1, dy1), (dx2, dy2), (dx3, dy3))
        self.rCurveTo((dx4, dy4), (dx5, dy5), (dx6, dy6))

    def op_flex1(self, index):
        dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4, dx5, dy5, d6 = self.popall()
        dx = dx1 + dx2 + dx3 + dx4 + dx5
        dy = dy1 + dy2 + dy3 + dy4 + dy5
        if abs(dx) > abs(dy):
            dx6 = d6
            dy6 = -dy
        else:
            dx6 = -dx
            dy6 = d6
        self.rCurveTo((dx1, dy1), (dx2, dy2), (dx3, dy3))
        self.rCurveTo((dx4, dy4), (dx5, dy5), (dx6, dy6))

    # misc
    def op_and(self, index):
        raise NotImplementedError

    def op_or(self, index):
        raise NotImplementedError

    def op_not(self, index):
        raise NotImplementedError

    def op_store(self, index):
        raise NotImplementedError

    def op_abs(self, index):
        raise NotImplementedError

    def op_add(self, index):
        raise NotImplementedError

    def op_sub(self, index):
        raise NotImplementedError

    def op_div(self, index):
        num2 = self.pop()
        num1 = self.pop()
        d1 = num1 // num2
        d2 = num1 / num2
        if d1 == d2:
            self.push(d1)
        else:
            self.push(d2)

    def op_load(self, index):
        raise NotImplementedError

    def op_neg(self, index):
        raise NotImplementedError

    def op_eq(self, index):
        raise NotImplementedError

    def op_drop(self, index):
        raise NotImplementedError

    def op_put(self, index):
        raise NotImplementedError

    def op_get(self, index):
        raise NotImplementedError

    def op_ifelse(self, index):
        raise NotImplementedError

    def op_random(self, index):
        raise NotImplementedError

    def op_mul(self, index):
        raise NotImplementedError

    def op_sqrt(self, index):
        raise NotImplementedError

    def op_dup(self, index):
        raise NotImplementedError

    def op_exch(self, index):
        raise NotImplementedError

    def op_index(self, index):
        raise NotImplementedError

    def op_roll(self, index):
        raise NotImplementedError

    #
    # miscellaneous helpers
    #
    def alternatingLineto(self, isHorizontal):
        args = self.popall()
        for arg in args:
            if isHorizontal:
                point = (arg, 0)
            else:
                point = (0, arg)
            self.rLineTo(point)
            isHorizontal = not isHorizontal

    def vcurveto(self, args):
        dya, dxb, dyb, dxc = args[:4]
        args = args[4:]
        if len(args) == 1:
            dyc = args[0]
            args = []
        else:
            dyc = 0
        self.rCurveTo((0, dya), (dxb, dyb), (dxc, dyc))
        return args

    def hcurveto(self, args):
        dxa, dxb, dyb, dyc = args[:4]
        args = args[4:]
        if len(args) == 1:
            dxc = args[0]
            args = []
        else:
            dxc = 0
        self.rCurveTo((dxa, 0), (dxb, dyb), (dxc, dyc))
        return args


class T1OutlineExtractor(T2OutlineExtractor):
    def __init__(self, pen, subrs):
        self.pen = pen
        self.subrs = subrs
        self.reset()

    def reset(self):
        self.flexing = 0
        self.width = 0
        self.sbx = 0
        T2OutlineExtractor.reset(self)

    def endPath(self):
        if self.sawMoveTo:
            self.pen.endPath()
        self.sawMoveTo = 0

    def popallWidth(self, evenOdd=0):
        return self.popall()

    def exch(self):
        stack = self.operandStack
        stack[-1], stack[-2] = stack[-2], stack[-1]

    #
    # path constructors
    #
    def op_rmoveto(self, index):
        if self.flexing:
            return
        self.endPath()
        self.rMoveTo(self.popall())

    def op_hmoveto(self, index):
        if self.flexing:
            # We must add a parameter to the stack if we are flexing
            self.push(0)
            return
        self.endPath()
        self.rMoveTo((self.popall()[0], 0))

    def op_vmoveto(self, index):
        if self.flexing:
            # We must add a parameter to the stack if we are flexing
            self.push(0)
            self.exch()
            return
        self.endPath()
        self.rMoveTo((0, self.popall()[0]))

    def op_closepath(self, index):
        self.closePath()

    def op_setcurrentpoint(self, index):
        args = self.popall()
        x, y = args
        self.currentPoint = x, y

    def op_endchar(self, index):
        self.endPath()

    def op_hsbw(self, index):
        sbx, wx = self.popall()
        self.width = wx
        self.sbx = sbx
        self.currentPoint = sbx, self.currentPoint[1]

    def op_sbw(self, index):
        self.popall()  # XXX

    #
    def op_callsubr(self, index):
        subrIndex = self.pop()
        subr = self.subrs[subrIndex]
        self.execute(subr)

    def op_callothersubr(self, index):
        subrIndex = self.pop()
        nArgs = self.pop()
        # print nArgs, subrIndex, "callothersubr"
        if subrIndex == 0 and nArgs == 3:
            self.doFlex()
            self.flexing = 0
        elif subrIndex == 1 and nArgs == 0:
            self.flexing = 1
        # ignore...

    def op_pop(self, index):
        pass  # ignore...

    def doFlex(self):
        finaly = self.pop()
        finalx = self.pop()
        self.pop()  # flex height is unused

        p3y = self.pop()
        p3x = self.pop()
        bcp4y = self.pop()
        bcp4x = self.pop()
        bcp3y = self.pop()
        bcp3x = self.pop()
        p2y = self.pop()
        p2x = self.pop()
        bcp2y = self.pop()
        bcp2x = self.pop()
        bcp1y = self.pop()
        bcp1x = self.pop()
        rpy = self.pop()
        rpx = self.pop()

        # call rrcurveto
        self.push(bcp1x + rpx)
        self.push(bcp1y + rpy)
        self.push(bcp2x)
        self.push(bcp2y)
        self.push(p2x)
        self.push(p2y)
        self.op_rrcurveto(None)

        # call rrcurveto
        self.push(bcp3x)
        self.push(bcp3y)
        self.push(bcp4x)
        self.push(bcp4y)
        self.push(p3x)
        self.push(p3y)
        self.op_rrcurveto(None)

        # Push back final coords so subr 0 can find them
        self.push(finalx)
        self.push(finaly)

    def op_dotsection(self, index):
        self.popall()  # XXX

    def op_hstem3(self, index):
        self.popall()  # XXX

    def op_seac(self, index):
        "asb adx ady bchar achar seac"
        from fontTools.encodings.StandardEncoding import StandardEncoding

        asb, adx, ady, bchar, achar = self.popall()
        baseGlyph = StandardEncoding[bchar]
        self.pen.addComponent(baseGlyph, (1, 0, 0, 1, 0, 0))
        accentGlyph = StandardEncoding[achar]
        adx = adx + self.sbx - asb  # seac weirdness
        self.pen.addComponent(accentGlyph, (1, 0, 0, 1, adx, ady))

    def op_vstem3(self, index):
        self.popall()  # XXX


class T2CharString(object):
    operandEncoding = t2OperandEncoding
    operators, opcodes = buildOperatorDict(t2Operators)
    decompilerClass = SimpleT2Decompiler
    outlineExtractor = T2OutlineExtractor

    def __init__(self, bytecode=None, program=None, private=None, globalSubrs=None):
        if program is None:
            program = []
        self.bytecode = bytecode
        self.program = program
        self.private = private
        self.globalSubrs = globalSubrs if globalSubrs is not None else []
        self._cur_vsindex = None

    def getNumRegions(self, vsindex=None):
        pd = self.private
        assert pd is not None
        if vsindex is not None:
            self._cur_vsindex = vsindex
        elif self._cur_vsindex is None:
            self._cur_vsindex = pd.vsindex if hasattr(pd, "vsindex") else 0
        return pd.getNumRegions(self._cur_vsindex)

    def __repr__(self):
        if self.bytecode is None:
            return "<%s (source) at %x>" % (self.__class__.__name__, id(self))
        else:
            return "<%s (bytecode) at %x>" % (self.__class__.__name__, id(self))

    def getIntEncoder(self):
        return encodeIntT2

    def getFixedEncoder(self):
        return encodeFixed

    def decompile(self):
        if not self.needsDecompilation():
            return
        subrs = getattr(self.private, "Subrs", [])
        decompiler = self.decompilerClass(subrs, self.globalSubrs, self.private)
        decompiler.execute(self)

    def draw(self, pen, blender=None):
        subrs = getattr(self.private, "Subrs", [])
        extractor = self.outlineExtractor(
            pen,
            subrs,
            self.globalSubrs,
            self.private.nominalWidthX,
            self.private.defaultWidthX,
            self.private,
            blender,
        )
        extractor.execute(self)
        self.width = extractor.width

    def calcBounds(self, glyphSet):
        boundsPen = BoundsPen(glyphSet)
        self.draw(boundsPen)
        return boundsPen.bounds

    def compile(self, isCFF2=False):
        if self.bytecode is not None:
            return
        opcodes = self.opcodes
        program = self.program

        if isCFF2:
            # If present, remove return and endchar operators.
            if program and program[-1] in ("return", "endchar"):
                program = program[:-1]
        elif program and not isinstance(program[-1], str):
            raise CharStringCompileError(
                "T2CharString or Subr has items on the stack after last operator."
            )

        bytecode = []
        encodeInt = self.getIntEncoder()
        encodeFixed = self.getFixedEncoder()
        i = 0
        end = len(program)
        while i < end:
            token = program[i]
            i = i + 1
            if isinstance(token, str):
                try:
                    bytecode.extend(bytechr(b) for b in opcodes[token])
                except KeyError:
                    raise CharStringCompileError("illegal operator: %s" % token)
                if token in ("hintmask", "cntrmask"):
                    bytecode.append(program[i])  # hint mask
                    i = i + 1
            elif isinstance(token, int):
                bytecode.append(encodeInt(token))
            elif isinstance(token, float):
                bytecode.append(encodeFixed(token))
            else:
                assert 0, "unsupported type: %s" % type(token)
        try:
            bytecode = bytesjoin(bytecode)
        except TypeError:
            log.error(bytecode)
            raise
        self.setBytecode(bytecode)

    def needsDecompilation(self):
        return self.bytecode is not None

    def setProgram(self, program):
        self.program = program
        self.bytecode = None

    def setBytecode(self, bytecode):
        self.bytecode = bytecode
        self.program = None

    def getToken(self, index, len=len, byteord=byteord, isinstance=isinstance):
        if self.bytecode is not None:
            if index >= len(self.bytecode):
                return None, 0, 0
            b0 = byteord(self.bytecode[index])
            index = index + 1
            handler = self.operandEncoding[b0]
            token, index = handler(self, b0, self.bytecode, index)
        else:
            if index >= len(self.program):
                return None, 0, 0
            token = self.program[index]
            index = index + 1
        isOperator = isinstance(token, str)
        return token, isOperator, index

    def getBytes(self, index, nBytes):
        if self.bytecode is not None:
            newIndex = index + nBytes
            bytes = self.bytecode[index:newIndex]
            index = newIndex
        else:
            bytes = self.program[index]
            index = index + 1
        assert len(bytes) == nBytes
        return bytes, index

    def handle_operator(self, operator):
        return operator

    def toXML(self, xmlWriter, ttFont=None):
        from fontTools.misc.textTools import num2binary

        if self.bytecode is not None:
            xmlWriter.dumphex(self.bytecode)
        else:
            index = 0
            args = []
            while True:
                token, isOperator, index = self.getToken(index)
                if token is None:
                    break
                if isOperator:
                    if token in ("hintmask", "cntrmask"):
                        hintMask, isOperator, index = self.getToken(index)
                        bits = []
                        for byte in hintMask:
                            bits.append(num2binary(byteord(byte), 8))
                        hintMask = strjoin(bits)
                        line = " ".join(args + [token, hintMask])
                    else:
                        line = " ".join(args + [token])
                    xmlWriter.write(line)
                    xmlWriter.newline()
                    args = []
                else:
                    if isinstance(token, float):
                        token = floatToFixedToStr(token, precisionBits=16)
                    else:
                        token = str(token)
                    args.append(token)
            if args:
                # NOTE: only CFF2 charstrings/subrs can have numeric arguments on
                # the stack after the last operator. Compiling this would fail if
                # this is part of CFF 1.0 table.
                line = " ".join(args)
                xmlWriter.write(line)

    def fromXML(self, name, attrs, content):
        from fontTools.misc.textTools import binary2num, readHex

        if attrs.get("raw"):
            self.setBytecode(readHex(content))
            return
        content = strjoin(content)
        content = content.split()
        program = []
        end = len(content)
        i = 0
        while i < end:
            token = content[i]
            i = i + 1
            try:
                token = int(token)
            except ValueError:
                try:
                    token = strToFixedToFloat(token, precisionBits=16)
                except ValueError:
                    program.append(token)
                    if token in ("hintmask", "cntrmask"):
                        mask = content[i]
                        maskBytes = b""
                        for j in range(0, len(mask), 8):
                            maskBytes = maskBytes + bytechr(binary2num(mask[j : j + 8]))
                        program.append(maskBytes)
                        i = i + 1
                else:
                    program.append(token)
            else:
                program.append(token)
        self.setProgram(program)


class T1CharString(T2CharString):
    operandEncoding = t1OperandEncoding
    operators, opcodes = buildOperatorDict(t1Operators)

    def __init__(self, bytecode=None, program=None, subrs=None):
        super().__init__(bytecode, program)
        self.subrs = subrs

    def getIntEncoder(self):
        return encodeIntT1

    def getFixedEncoder(self):
        def encodeFixed(value):
            raise TypeError("Type 1 charstrings don't support floating point operands")

    def decompile(self):
        if self.bytecode is None:
            return
        program = []
        index = 0
        while True:
            token, isOperator, index = self.getToken(index)
            if token is None:
                break
            program.append(token)
        self.setProgram(program)

    def draw(self, pen):
        extractor = T1OutlineExtractor(pen, self.subrs)
        extractor.execute(self)
        self.width = extractor.width


class DictDecompiler(object):
    operandEncoding = cffDictOperandEncoding

    def __init__(self, strings, parent=None):
        self.stack = []
        self.strings = strings
        self.dict = {}
        self.parent = parent

    def getDict(self):
        assert len(self.stack) == 0, "non-empty stack"
        return self.dict

    def decompile(self, data):
        index = 0
        lenData = len(data)
        push = self.stack.append
        while index < lenData:
            b0 = byteord(data[index])
            index = index + 1
            handler = self.operandEncoding[b0]
            value, index = handler(self, b0, data, index)
            if value is not None:
                push(value)

    def pop(self):
        value = self.stack[-1]
        del self.stack[-1]
        return value

    def popall(self):
        args = self.stack[:]
        del self.stack[:]
        return args

    def handle_operator(self, operator):
        operator, argType = operator
        if isinstance(argType, tuple):
            value = ()
            for i in range(len(argType) - 1, -1, -1):
                arg = argType[i]
                arghandler = getattr(self, "arg_" + arg)
                value = (arghandler(operator),) + value
        else:
            arghandler = getattr(self, "arg_" + argType)
            value = arghandler(operator)
        if operator == "blend":
            self.stack.extend(value)
        else:
            self.dict[operator] = value

    def arg_number(self, name):
        if isinstance(self.stack[0], list):
            out = self.arg_blend_number(self.stack)
        else:
            out = self.pop()
        return out

    def arg_blend_number(self, name):
        out = []
        blendArgs = self.pop()
        numMasters = len(blendArgs)
        out.append(blendArgs)
        out.append("blend")
        dummy = self.popall()
        return blendArgs

    def arg_SID(self, name):
        return self.strings[self.pop()]

    def arg_array(self, name):
        return self.popall()

    def arg_blendList(self, name):
        """
        There may be non-blend args at the top of the stack. We first calculate
        where the blend args start in the stack. These are the last
        numMasters*numBlends) +1 args.
        The blend args starts with numMasters relative coordinate values, the  BlueValues in the list from the default master font. This is followed by
        numBlends list of values. Each of  value in one of these lists is the
        Variable Font delta for the matching region.

        We re-arrange this to be a list of numMaster entries. Each entry starts with the corresponding default font relative value, and is followed by
        the delta values. We then convert the default values, the first item in each entry, to an absolute value.
        """
        vsindex = self.dict.get("vsindex", 0)
        numMasters = (
            self.parent.getNumRegions(vsindex) + 1
        )  # only a PrivateDict has blended ops.
        numBlends = self.pop()
        args = self.popall()
        numArgs = len(args)
        # The spec says that there should be no non-blended Blue Values,.
        assert numArgs == numMasters * numBlends
        value = [None] * numBlends
        numDeltas = numMasters - 1
        i = 0
        prevVal = 0
        while i < numBlends:
            newVal = args[i] + prevVal
            prevVal = newVal
            masterOffset = numBlends + (i * numDeltas)
            blendList = [newVal] + args[masterOffset : masterOffset + numDeltas]
            value[i] = blendList
            i += 1
        return value

    def arg_delta(self, name):
        valueList = self.popall()
        out = []
        if valueList and isinstance(valueList[0], list):
            # arg_blendList() has already converted these to absolute values.
            out = valueList
        else:
            current = 0
            for v in valueList:
                current = current + v
                out.append(current)
        return out


def calcSubrBias(subrs):
    nSubrs = len(subrs)
    if nSubrs < 1240:
        bias = 107
    elif nSubrs < 33900:
        bias = 1131
    else:
        bias = 32768
    return bias

# === NexusCore/openenv\Lib\site-packages\wcwidth\table_wide.py ===
"""
Exports WIDE_EASTASIAN table keyed by supporting unicode version level.

This code generated by wcwidth/bin/update-tables.py on 2024-01-06 01:39:49 UTC.
"""
WIDE_EASTASIAN = {
    '4.1.0': (
        # Source: EastAsianWidth-4.1.0.txt
        # Date: 2005-03-17, 15:21:00 PST [KW]
        #
        (0x01100, 0x01159,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Yeorinhi
        (0x0115f, 0x0115f,),  # Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312c,),  # Bopomofo Letter B       ..Bopomofo Letter Gn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031b7,),  # Ideographic Annotation L..Bopomofo Final Letter H
        (0x031c0, 0x031cf,),  # Cjk Stroke T            ..Cjk Stroke N
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03243,),  # Parenthesized Ideograph ..Parenthesized Ideograph
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04db5,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x09fbb,),  # Cjk Unified Ideograph-4e..Cjk Unified Ideograph-9f
        (0x0a000, 0x0a48c,),  # Yi Syllable It          ..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0fa2d,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa30, 0x0fa6a,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa70, 0x0fad9,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '5.0.0': (
        # Source: EastAsianWidth-5.0.0.txt
        # Date: 2006-02-15, 14:39:00 PST [KW]
        #
        (0x01100, 0x01159,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Yeorinhi
        (0x0115f, 0x0115f,),  # Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312c,),  # Bopomofo Letter B       ..Bopomofo Letter Gn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031b7,),  # Ideographic Annotation L..Bopomofo Final Letter H
        (0x031c0, 0x031cf,),  # Cjk Stroke T            ..Cjk Stroke N
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03243,),  # Parenthesized Ideograph ..Parenthesized Ideograph
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04db5,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x09fbb,),  # Cjk Unified Ideograph-4e..Cjk Unified Ideograph-9f
        (0x0a000, 0x0a48c,),  # Yi Syllable It          ..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0fa2d,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa30, 0x0fa6a,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa70, 0x0fad9,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '5.1.0': (
        # Source: EastAsianWidth-5.1.0.txt
        # Date: 2008-03-20, 17:42:00 PDT [KW]
        #
        (0x01100, 0x01159,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Yeorinhi
        (0x0115f, 0x0115f,),  # Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031b7,),  # Ideographic Annotation L..Bopomofo Final Letter H
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03243,),  # Parenthesized Ideograph ..Parenthesized Ideograph
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04db5,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x09fc3,),  # Cjk Unified Ideograph-4e..Cjk Unified Ideograph-9f
        (0x0a000, 0x0a48c,),  # Yi Syllable It          ..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0fa2d,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa30, 0x0fa6a,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fa70, 0x0fad9,),  # Cjk Compatibility Ideogr..Cjk Compatibility Ideogr
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '5.2.0': (
        # Source: EastAsianWidth-5.2.0.txt
        # Date: 2009-06-09, 17:47:00 PDT [KW]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031b7,),  # Ideographic Annotation L..Bopomofo Final Letter H
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1f200, 0x1f200,),  # Square Hiragana Hoka
        (0x1f210, 0x1f231,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '6.0.0': (
        # Source: EastAsianWidth-6.0.0.txt
        # Date: 2010-08-17, 12:17:00 PDT [KW]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '6.1.0': (
        # Source: EastAsianWidth-6.1.0.txt
        # Date: 2011-09-19, 18:46:00 GMT [KW]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '6.2.0': (
        # Source: EastAsianWidth-6.2.0.txt
        # Date: 2012-05-15, 18:30:00 GMT [KW]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '6.3.0': (
        # Source: EastAsianWidth-6.3.0.txt
        # Date: 2013-02-05, 20:09:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '7.0.0': (
        # Source: EastAsianWidth-7.0.0.txt
        # Date: 2014-02-28, 23:15:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '8.0.0': (
        # Source: EastAsianWidth-8.0.0.txt
        # Date: 2015-02-10, 21:00:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23a,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '9.0.0': (
        # Source: EastAsianWidth-9.0.0.txt
        # Date: 2016-05-27, 17:00:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312d,),  # Bopomofo Letter B       ..Bopomofo Letter Ih
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe0,),  # Tangut Iteration Mark
        (0x17000, 0x187ec,),  # (nil)
        (0x18800, 0x18af2,),  # Tangut Component-001    ..Tangut Component-755
        (0x1b000, 0x1b001,),  # Katakana Letter Archaic ..Hiragana Letter Archaic
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6f6,),  # Scooter                 ..Canoe
        (0x1f910, 0x1f91e,),  # Zipper-mouth Face       ..Hand With Index And Midd
        (0x1f920, 0x1f927,),  # Face With Cowboy Hat    ..Sneezing Face
        (0x1f930, 0x1f930,),  # Pregnant Woman
        (0x1f933, 0x1f93e,),  # Selfie                  ..Handball
        (0x1f940, 0x1f94b,),  # Wilted Flower           ..Martial Arts Uniform
        (0x1f950, 0x1f95e,),  # Croissant               ..Pancakes
        (0x1f980, 0x1f991,),  # Crab                    ..Squid
        (0x1f9c0, 0x1f9c0,),  # Cheese Wedge
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '10.0.0': (
        # Source: EastAsianWidth-10.0.0.txt
        # Date: 2017-03-08, 02:00:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312e,),  # Bopomofo Letter B       ..Bopomofo Letter O With D
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe1,),  # Tangut Iteration Mark   ..Nushu Iteration Mark
        (0x17000, 0x187ec,),  # (nil)
        (0x18800, 0x18af2,),  # Tangut Component-001    ..Tangut Component-755
        (0x1b000, 0x1b11e,),  # Katakana Letter Archaic ..Hentaigana Letter N-mu-m
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6f8,),  # Scooter                 ..Flying Saucer
        (0x1f910, 0x1f93e,),  # Zipper-mouth Face       ..Handball
        (0x1f940, 0x1f94c,),  # Wilted Flower           ..Curling Stone
        (0x1f950, 0x1f96b,),  # Croissant               ..Canned Food
        (0x1f980, 0x1f997,),  # Crab                    ..Cricket
        (0x1f9c0, 0x1f9c0,),  # Cheese Wedge
        (0x1f9d0, 0x1f9e6,),  # Face With Monocle       ..Socks
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '11.0.0': (
        # Source: EastAsianWidth-11.0.0.txt
        # Date: 2018-05-14, 09:41:59 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe1,),  # Tangut Iteration Mark   ..Nushu Iteration Mark
        (0x17000, 0x187f1,),  # (nil)
        (0x18800, 0x18af2,),  # Tangut Component-001    ..Tangut Component-755
        (0x1b000, 0x1b11e,),  # Katakana Letter Archaic ..Hentaigana Letter N-mu-m
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6f9,),  # Scooter                 ..Skateboard
        (0x1f910, 0x1f93e,),  # Zipper-mouth Face       ..Handball
        (0x1f940, 0x1f970,),  # Wilted Flower           ..Smiling Face With Smilin
        (0x1f973, 0x1f976,),  # Face With Party Horn And..Freezing Face
        (0x1f97a, 0x1f97a,),  # Face With Pleading Eyes
        (0x1f97c, 0x1f9a2,),  # Lab Coat                ..Swan
        (0x1f9b0, 0x1f9b9,),  # Emoji Component Red Hair..Supervillain
        (0x1f9c0, 0x1f9c2,),  # Cheese Wedge            ..Salt Shaker
        (0x1f9d0, 0x1f9ff,),  # Face With Monocle       ..Nazar Amulet
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '12.0.0': (
        # Source: EastAsianWidth-12.0.0.txt
        # Date: 2019-01-21, 14:12:58 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x032fe,),  # Partnership Sign        ..Circled Katakana Wo
        (0x03300, 0x04dbf,),  # Square Apaato           ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18af2,),  # Tangut Component-001    ..Tangut Component-755
        (0x1b000, 0x1b11e,),  # Katakana Letter Archaic ..Hentaigana Letter N-mu-m
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d5,),  # Hindu Temple
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fa,),  # Scooter                 ..Auto Rickshaw
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f90d, 0x1f971,),  # White Heart             ..Yawning Face
        (0x1f973, 0x1f976,),  # Face With Party Horn And..Freezing Face
        (0x1f97a, 0x1f9a2,),  # Face With Pleading Eyes ..Swan
        (0x1f9a5, 0x1f9aa,),  # Sloth                   ..Oyster
        (0x1f9ae, 0x1f9ca,),  # Guide Dog               ..Ice Cube
        (0x1f9cd, 0x1f9ff,),  # Standing Person         ..Nazar Amulet
        (0x1fa70, 0x1fa73,),  # Ballet Shoes            ..Shorts
        (0x1fa78, 0x1fa7a,),  # Drop Of Blood           ..Stethoscope
        (0x1fa80, 0x1fa82,),  # Yo-yo                   ..Parachute
        (0x1fa90, 0x1fa95,),  # Ringed Planet           ..Banjo
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '12.1.0': (
        # Source: EastAsianWidth-12.1.0.txt
        # Date: 2019-03-31, 22:01:58 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031ba,),  # Ideographic Annotation L..Bopomofo Letter Zy
        (0x031c0, 0x031e3,),  # Cjk Stroke T            ..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18af2,),  # Tangut Component-001    ..Tangut Component-755
        (0x1b000, 0x1b11e,),  # Katakana Letter Archaic ..Hentaigana Letter N-mu-m
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d5,),  # Hindu Temple
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fa,),  # Scooter                 ..Auto Rickshaw
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f90d, 0x1f971,),  # White Heart             ..Yawning Face
        (0x1f973, 0x1f976,),  # Face With Party Horn And..Freezing Face
        (0x1f97a, 0x1f9a2,),  # Face With Pleading Eyes ..Swan
        (0x1f9a5, 0x1f9aa,),  # Sloth                   ..Oyster
        (0x1f9ae, 0x1f9ca,),  # Guide Dog               ..Ice Cube
        (0x1f9cd, 0x1f9ff,),  # Standing Person         ..Nazar Amulet
        (0x1fa70, 0x1fa73,),  # Ballet Shoes            ..Shorts
        (0x1fa78, 0x1fa7a,),  # Drop Of Blood           ..Stethoscope
        (0x1fa80, 0x1fa82,),  # Yo-yo                   ..Parachute
        (0x1fa90, 0x1fa95,),  # Ringed Planet           ..Banjo
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '13.0.0': (
        # Source: EastAsianWidth-13.0.0.txt
        # Date: 2029-01-21, 18:14:00 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031e3,),  # Ideographic Annotation L..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18cd5,),  # Tangut Component-001    ..Khitan Small Script Char
        (0x18d00, 0x18d08,),  # (nil)
        (0x1b000, 0x1b11e,),  # Katakana Letter Archaic ..Hentaigana Letter N-mu-m
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d7,),  # Hindu Temple            ..Elevator
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fc,),  # Scooter                 ..Roller Skate
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f90c, 0x1f93a,),  # Pinched Fingers         ..Fencer
        (0x1f93c, 0x1f945,),  # Wrestlers               ..Goal Net
        (0x1f947, 0x1f978,),  # First Place Medal       ..Disguised Face
        (0x1f97a, 0x1f9cb,),  # Face With Pleading Eyes ..Bubble Tea
        (0x1f9cd, 0x1f9ff,),  # Standing Person         ..Nazar Amulet
        (0x1fa70, 0x1fa74,),  # Ballet Shoes            ..Thong Sandal
        (0x1fa78, 0x1fa7a,),  # Drop Of Blood           ..Stethoscope
        (0x1fa80, 0x1fa86,),  # Yo-yo                   ..Nesting Dolls
        (0x1fa90, 0x1faa8,),  # Ringed Planet           ..Rock
        (0x1fab0, 0x1fab6,),  # Fly                     ..Feather
        (0x1fac0, 0x1fac2,),  # Anatomical Heart        ..People Hugging
        (0x1fad0, 0x1fad6,),  # Blueberries             ..Teapot
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '14.0.0': (
        # Source: EastAsianWidth-14.0.0.txt
        # Date: 2021-07-06, 09:58:53 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031e3,),  # Ideographic Annotation L..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18cd5,),  # Tangut Component-001    ..Khitan Small Script Char
        (0x18d00, 0x18d08,),  # (nil)
        (0x1aff0, 0x1aff3,),  # Katakana Letter Minnan T..Katakana Letter Minnan T
        (0x1aff5, 0x1affb,),  # Katakana Letter Minnan T..Katakana Letter Minnan N
        (0x1affd, 0x1affe,),  # Katakana Letter Minnan N..Katakana Letter Minnan N
        (0x1b000, 0x1b122,),  # Katakana Letter Archaic ..Katakana Letter Archaic
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d7,),  # Hindu Temple            ..Elevator
        (0x1f6dd, 0x1f6df,),  # Playground Slide        ..Ring Buoy
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fc,),  # Scooter                 ..Roller Skate
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f7f0, 0x1f7f0,),  # Heavy Equals Sign
        (0x1f90c, 0x1f93a,),  # Pinched Fingers         ..Fencer
        (0x1f93c, 0x1f945,),  # Wrestlers               ..Goal Net
        (0x1f947, 0x1f9ff,),  # First Place Medal       ..Nazar Amulet
        (0x1fa70, 0x1fa74,),  # Ballet Shoes            ..Thong Sandal
        (0x1fa78, 0x1fa7c,),  # Drop Of Blood           ..Crutch
        (0x1fa80, 0x1fa86,),  # Yo-yo                   ..Nesting Dolls
        (0x1fa90, 0x1faac,),  # Ringed Planet           ..Hamsa
        (0x1fab0, 0x1faba,),  # Fly                     ..Nest With Eggs
        (0x1fac0, 0x1fac5,),  # Anatomical Heart        ..Person With Crown
        (0x1fad0, 0x1fad9,),  # Blueberries             ..Jar
        (0x1fae0, 0x1fae7,),  # Melting Face            ..Bubbles
        (0x1faf0, 0x1faf6,),  # Hand With Index Finger A..Heart Hands
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '15.0.0': (
        # Source: EastAsianWidth-15.0.0.txt
        # Date: 2022-05-24, 17:40:20 GMT [KW, LI]
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x02ffb,),  # Ideographic Description ..Ideographic Description
        (0x03000, 0x03029,),  # Ideographic Space       ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031e3,),  # Ideographic Annotation L..Cjk Stroke Q
        (0x031f0, 0x0321e,),  # Katakana Letter Small Ku..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18cd5,),  # Tangut Component-001    ..Khitan Small Script Char
        (0x18d00, 0x18d08,),  # (nil)
        (0x1aff0, 0x1aff3,),  # Katakana Letter Minnan T..Katakana Letter Minnan T
        (0x1aff5, 0x1affb,),  # Katakana Letter Minnan T..Katakana Letter Minnan N
        (0x1affd, 0x1affe,),  # Katakana Letter Minnan N..Katakana Letter Minnan N
        (0x1b000, 0x1b122,),  # Katakana Letter Archaic ..Katakana Letter Archaic
        (0x1b132, 0x1b132,),  # Hiragana Letter Small Ko
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b155, 0x1b155,),  # Katakana Letter Small Ko
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d7,),  # Hindu Temple            ..Elevator
        (0x1f6dc, 0x1f6df,),  # Wireless                ..Ring Buoy
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fc,),  # Scooter                 ..Roller Skate
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f7f0, 0x1f7f0,),  # Heavy Equals Sign
        (0x1f90c, 0x1f93a,),  # Pinched Fingers         ..Fencer
        (0x1f93c, 0x1f945,),  # Wrestlers               ..Goal Net
        (0x1f947, 0x1f9ff,),  # First Place Medal       ..Nazar Amulet
        (0x1fa70, 0x1fa7c,),  # Ballet Shoes            ..Crutch
        (0x1fa80, 0x1fa88,),  # Yo-yo                   ..Flute
        (0x1fa90, 0x1fabd,),  # Ringed Planet           ..Wing
        (0x1fabf, 0x1fac5,),  # Goose                   ..Person With Crown
        (0x1face, 0x1fadb,),  # Moose                   ..Pea Pod
        (0x1fae0, 0x1fae8,),  # Melting Face            ..Shaking Face
        (0x1faf0, 0x1faf8,),  # Hand With Index Finger A..Rightwards Pushing Hand
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
    '15.1.0': (
        # Source: EastAsianWidth-15.1.0.txt
        # Date: 2023-07-28, 23:34:08 GMT
        #
        (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
        (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
        (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
        (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
        (0x023f0, 0x023f0,),  # Alarm Clock
        (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
        (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
        (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
        (0x02648, 0x02653,),  # Aries                   ..Pisces
        (0x0267f, 0x0267f,),  # Wheelchair Symbol
        (0x02693, 0x02693,),  # Anchor
        (0x026a1, 0x026a1,),  # High Voltage Sign
        (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
        (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
        (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
        (0x026ce, 0x026ce,),  # Ophiuchus
        (0x026d4, 0x026d4,),  # No Entry
        (0x026ea, 0x026ea,),  # Church
        (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
        (0x026f5, 0x026f5,),  # Sailboat
        (0x026fa, 0x026fa,),  # Tent
        (0x026fd, 0x026fd,),  # Fuel Pump
        (0x02705, 0x02705,),  # White Heavy Check Mark
        (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
        (0x02728, 0x02728,),  # Sparkles
        (0x0274c, 0x0274c,),  # Cross Mark
        (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
        (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
        (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
        (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
        (0x027b0, 0x027b0,),  # Curly Loop
        (0x027bf, 0x027bf,),  # Double Curly Loop
        (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
        (0x02b50, 0x02b50,),  # White Medium Star
        (0x02b55, 0x02b55,),  # Heavy Large Circle
        (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
        (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
        (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
        (0x02ff0, 0x03029,),  # Ideographic Description ..Hangzhou Numeral Nine
        (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
        (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
        (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
        (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
        (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
        (0x03190, 0x031e3,),  # Ideographic Annotation L..Cjk Stroke Q
        (0x031ef, 0x0321e,),  # (nil)                   ..Parenthesized Korean Cha
        (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
        (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
        (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
        (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
        (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
        (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
        (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
        (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
        (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
        (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
        (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
        (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
        (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
        (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
        (0x17000, 0x187f7,),  # (nil)
        (0x18800, 0x18cd5,),  # Tangut Component-001    ..Khitan Small Script Char
        (0x18d00, 0x18d08,),  # (nil)
        (0x1aff0, 0x1aff3,),  # Katakana Letter Minnan T..Katakana Letter Minnan T
        (0x1aff5, 0x1affb,),  # Katakana Letter Minnan T..Katakana Letter Minnan N
        (0x1affd, 0x1affe,),  # Katakana Letter Minnan N..Katakana Letter Minnan N
        (0x1b000, 0x1b122,),  # Katakana Letter Archaic ..Katakana Letter Archaic
        (0x1b132, 0x1b132,),  # Hiragana Letter Small Ko
        (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
        (0x1b155, 0x1b155,),  # Katakana Letter Small Ko
        (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
        (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
        (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
        (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
        (0x1f18e, 0x1f18e,),  # Negative Squared Ab
        (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
        (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
        (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
        (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
        (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
        (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
        (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
        (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
        (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
        (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
        (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
        (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
        (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
        (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
        (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
        (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
        (0x1f440, 0x1f440,),  # Eyes
        (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
        (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
        (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
        (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
        (0x1f57a, 0x1f57a,),  # Man Dancing
        (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
        (0x1f5a4, 0x1f5a4,),  # Black Heart
        (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
        (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
        (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
        (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
        (0x1f6d5, 0x1f6d7,),  # Hindu Temple            ..Elevator
        (0x1f6dc, 0x1f6df,),  # Wireless                ..Ring Buoy
        (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
        (0x1f6f4, 0x1f6fc,),  # Scooter                 ..Roller Skate
        (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
        (0x1f7f0, 0x1f7f0,),  # Heavy Equals Sign
        (0x1f90c, 0x1f93a,),  # Pinched Fingers         ..Fencer
        (0x1f93c, 0x1f945,),  # Wrestlers               ..Goal Net
        (0x1f947, 0x1f9ff,),  # First Place Medal       ..Nazar Amulet
        (0x1fa70, 0x1fa7c,),  # Ballet Shoes            ..Crutch
        (0x1fa80, 0x1fa88,),  # Yo-yo                   ..Flute
        (0x1fa90, 0x1fabd,),  # Ringed Planet           ..Wing
        (0x1fabf, 0x1fac5,),  # Goose                   ..Person With Crown
        (0x1face, 0x1fadb,),  # Moose                   ..Pea Pod
        (0x1fae0, 0x1fae8,),  # Melting Face            ..Shaking Face
        (0x1faf0, 0x1faf8,),  # Hand With Index Finger A..Rightwards Pushing Hand
        (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
        (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
    ),
}

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_page.py ===
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
import base64
import inspect
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Union,
    cast,
)

from playwright._impl._accessibility import Accessibility
from playwright._impl._api_structures import (
    AriaRole,
    FilePayload,
    FloatRect,
    PdfMargins,
    Position,
    ViewportSize,
)
from playwright._impl._artifact import Artifact
from playwright._impl._clock import Clock
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._download import Download
from playwright._impl._element_handle import ElementHandle
from playwright._impl._errors import Error, TargetClosedError, is_target_closed_error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._file_chooser import FileChooser
from playwright._impl._frame import Frame
from playwright._impl._greenlets import LocatorHandlerGreenlet
from playwright._impl._har_router import HarRouter
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    DocumentLoadState,
    ForcedColors,
    HarMode,
    KeyboardModifier,
    MouseButton,
    ReducedMotion,
    RouteFromHarNotFoundPolicy,
    RouteHandler,
    RouteHandlerCallback,
    TimeoutSettings,
    URLMatch,
    URLMatchRequest,
    URLMatchResponse,
    WebSocketRouteHandlerCallback,
    async_readfile,
    async_writefile,
    locals_to_params,
    make_dirs_for_file,
    serialize_error,
    url_matches,
)
from playwright._impl._input import Keyboard, Mouse, Touchscreen
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    add_source_url_to_script,
    parse_result,
    serialize_argument,
)
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocketRoute,
    WebSocketRouteHandler,
    serialize_headers,
)
from playwright._impl._video import Video
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIRequestContext
    from playwright._impl._locator import FrameLocator, Locator
    from playwright._impl._network import WebSocket


class LocatorHandler:
    locator: "Locator"
    handler: Union[Callable[["Locator"], Any], Callable[..., Any]]
    times: Union[int, None]

    def __init__(
        self, locator: "Locator", handler: Callable[..., Any], times: Union[int, None]
    ) -> None:
        self.locator = locator
        self._handler = handler
        self.times = times

    def __call__(self) -> Any:
        arg_count = len(inspect.signature(self._handler).parameters)
        if arg_count == 0:
            return self._handler()
        return self._handler(self.locator)


class Page(ChannelOwner):
    Events = SimpleNamespace(
        Close="close",
        Crash="crash",
        Console="console",
        Dialog="dialog",
        Download="download",
        FileChooser="filechooser",
        DOMContentLoaded="domcontentloaded",
        PageError="pageerror",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
        FrameAttached="frameattached",
        FrameDetached="framedetached",
        FrameNavigated="framenavigated",
        Load="load",
        Popup="popup",
        WebSocket="websocket",
        Worker="worker",
    )
    accessibility: Accessibility
    keyboard: Keyboard
    mouse: Mouse
    touchscreen: Touchscreen

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_context = cast("BrowserContext", parent)
        self.accessibility = Accessibility(self._channel)
        self.keyboard = Keyboard(self._channel)
        self.mouse = Mouse(self._channel)
        self.touchscreen = Touchscreen(self._channel)

        self._main_frame: Frame = from_channel(initializer["mainFrame"])
        self._main_frame._page = self
        self._frames = [self._main_frame]
        self._viewport_size: Optional[ViewportSize] = initializer.get("viewportSize")
        self._is_closed = False
        self._workers: List["Worker"] = []
        self._bindings: Dict[str, Any] = {}
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []
        self._owned_context: Optional["BrowserContext"] = None
        self._timeout_settings: TimeoutSettings = TimeoutSettings(
            self._browser_context._timeout_settings
        )
        self._video: Optional[Video] = None
        self._opener = cast("Page", from_nullable_channel(initializer.get("opener")))
        self._close_reason: Optional[str] = None
        self._close_was_called = False
        self._har_routers: List[HarRouter] = []
        self._locator_handlers: Dict[str, LocatorHandler] = {}

        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on("crash", lambda _: self._on_crash())
        self._channel.on("download", lambda params: self._on_download(params))
        self._channel.on(
            "fileChooser",
            lambda params: self.emit(
                Page.Events.FileChooser,
                FileChooser(
                    self, from_channel(params["element"]), params["isMultiple"]
                ),
            ),
        )
        self._channel.on(
            "frameAttached",
            lambda params: self._on_frame_attached(from_channel(params["frame"])),
        )
        self._channel.on(
            "frameDetached",
            lambda params: self._on_frame_detached(from_channel(params["frame"])),
        )
        self._channel.on(
            "locatorHandlerTriggered",
            lambda params: self._loop.create_task(
                self._on_locator_handler_triggered(params["uid"])
            ),
        )
        self._channel.on(
            "route",
            lambda params: self._loop.create_task(
                self._on_route(from_channel(params["route"]))
            ),
        )
        self._channel.on(
            "webSocketRoute",
            lambda params: self._loop.create_task(
                self._on_web_socket_route(from_channel(params["webSocketRoute"]))
            ),
        )
        self._channel.on("video", lambda params: self._on_video(params))
        self._channel.on(
            "webSocket",
            lambda params: self.emit(
                Page.Events.WebSocket, from_channel(params["webSocket"])
            ),
        )
        self._channel.on(
            "worker", lambda params: self._on_worker(from_channel(params["worker"]))
        )
        self._closed_or_crashed_future: asyncio.Future = asyncio.Future()
        self.on(
            Page.Events.Close,
            lambda _: (
                self._closed_or_crashed_future.set_result(
                    self._close_error_with_reason()
                )
                if not self._closed_or_crashed_future.done()
                else None
            ),
        )
        self.on(
            Page.Events.Crash,
            lambda _: (
                self._closed_or_crashed_future.set_result(TargetClosedError())
                if not self._closed_or_crashed_future.done()
                else None
            ),
        )

        self._set_event_to_subscription_mapping(
            {
                Page.Events.Console: "console",
                Page.Events.Dialog: "dialog",
                Page.Events.Request: "request",
                Page.Events.Response: "response",
                Page.Events.RequestFinished: "requestFinished",
                Page.Events.RequestFailed: "requestFailed",
                Page.Events.FileChooser: "fileChooser",
            }
        )

    def __repr__(self) -> str:
        return f"<Page url={self.url!r}>"

    def _on_frame_attached(self, frame: Frame) -> None:
        frame._page = self
        self._frames.append(frame)
        self.emit(Page.Events.FrameAttached, frame)

    def _on_frame_detached(self, frame: Frame) -> None:
        self._frames.remove(frame)
        frame._detached = True
        self.emit(Page.Events.FrameDetached, frame)

    async def _on_route(self, route: Route) -> None:
        route._context = self.context
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            # If the page was closed we stall all requests right away.
            if self._close_was_called or self.context._close_was_called:
                return
            if not route_handler.matches(route.request.url):
                continue
            if route_handler not in self._routes:
                continue
            if route_handler.will_expire:
                self._routes.remove(route_handler)
            try:
                handled = await route_handler.handle(route)
            finally:
                if len(self._routes) == 0:

                    async def _update_interceptor_patterns_ignore_exceptions() -> None:
                        try:
                            await self._update_interception_patterns()
                        except Error:
                            pass

                    asyncio.create_task(
                        self._connection.wrap_api_call(
                            _update_interceptor_patterns_ignore_exceptions, True
                        )
                    )
            if handled:
                return
        await self._browser_context._on_route(route)

    async def _on_web_socket_route(self, web_socket_route: WebSocketRoute) -> None:
        route_handler = next(
            (
                route_handler
                for route_handler in self._web_socket_routes
                if route_handler.matches(web_socket_route.url)
            ),
            None,
        )
        if route_handler:
            await route_handler.handle(web_socket_route)
        else:
            await self._browser_context._on_web_socket_route(web_socket_route)

    def _on_binding(self, binding_call: "BindingCall") -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func:
            asyncio.create_task(binding_call.call(func))
        self._browser_context._on_binding(binding_call)

    def _on_worker(self, worker: "Worker") -> None:
        self._workers.append(worker)
        worker._page = self
        self.emit(Page.Events.Worker, worker)

    def _on_close(self) -> None:
        self._is_closed = True
        if self in self._browser_context._pages:
            self._browser_context._pages.remove(self)
        if self in self._browser_context._background_pages:
            self._browser_context._background_pages.remove(self)
        self._dispose_har_routers()
        self.emit(Page.Events.Close, self)

    def _on_crash(self) -> None:
        self.emit(Page.Events.Crash, self)

    def _on_download(self, params: Any) -> None:
        url = params["url"]
        suggested_filename = params["suggestedFilename"]
        artifact = cast(Artifact, from_channel(params["artifact"]))
        self.emit(
            Page.Events.Download, Download(self, url, suggested_filename, artifact)
        )

    def _on_video(self, params: Any) -> None:
        artifact = from_channel(params["artifact"])
        self._force_video()._artifact_ready(artifact)

    @property
    def context(self) -> "BrowserContext":
        return self._browser_context

    @property
    def clock(self) -> Clock:
        return self._browser_context.clock

    async def opener(self) -> Optional["Page"]:
        if self._opener and self._opener.is_closed():
            return None
        return self._opener

    @property
    def main_frame(self) -> Frame:
        return self._main_frame

    def frame(self, name: str = None, url: URLMatch = None) -> Optional[Frame]:
        for frame in self._frames:
            if name and frame.name == name:
                return frame
            if url and url_matches(
                self._browser_context._options.get("baseURL"), frame.url, url
            ):
                return frame

        return None

    @property
    def frames(self) -> List[Frame]:
        return self._frames.copy()

    def set_default_navigation_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultNavigationTimeoutNoReply", dict(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_timeout(timeout)
        self._channel.send_no_reply("setDefaultTimeoutNoReply", dict(timeout=timeout))

    async def query_selector(
        self,
        selector: str,
        strict: bool = None,
    ) -> Optional[ElementHandle]:
        return await self._main_frame.query_selector(selector, strict)

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return await self._main_frame.query_selector_all(selector)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        strict: bool = None,
    ) -> Optional[ElementHandle]:
        return await self._main_frame.wait_for_selector(**locals_to_params(locals()))

    async def is_checked(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_checked(**locals_to_params(locals()))

    async def is_disabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_disabled(**locals_to_params(locals()))

    async def is_editable(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_editable(**locals_to_params(locals()))

    async def is_enabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_enabled(**locals_to_params(locals()))

    async def is_hidden(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_hidden(**locals_to_params(locals()))

    async def is_visible(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_visible(**locals_to_params(locals()))

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        eventInit: Dict = None,
        timeout: float = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.dispatch_event(**locals_to_params(locals()))

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return await self._main_frame.evaluate(expression, arg)

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> JSHandle:
        return await self._main_frame.evaluate_handle(expression, arg)

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        strict: bool = None,
    ) -> Any:
        return await self._main_frame.eval_on_selector(
            selector, expression, arg, strict
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return await self._main_frame.eval_on_selector_all(selector, expression, arg)

    async def add_script_tag(
        self,
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        return await self._main_frame.add_script_tag(**locals_to_params(locals()))

    async def add_style_tag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        return await self._main_frame.add_style_tag(**locals_to_params(locals()))

    async def expose_function(self, name: str, callback: Callable) -> None:
        await self.expose_binding(name, lambda source, *args: callback(*args))

    async def expose_binding(
        self, name: str, callback: Callable, handle: bool = None
    ) -> None:
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        if name in self._browser_context._bindings:
            raise Error(
                f'Function "{name}" has been already registered in the browser context'
            )
        self._bindings[name] = callback
        await self._channel.send(
            "exposeBinding", dict(name=name, needsHandle=handle or False)
        )

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", dict(headers=serialize_headers(headers))
        )

    @property
    def url(self) -> str:
        return self._main_frame.url

    async def content(self) -> str:
        return await self._main_frame.content()

    async def set_content(
        self,
        html: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> None:
        return await self._main_frame.set_content(**locals_to_params(locals()))

    async def goto(
        self,
        url: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return await self._main_frame.goto(**locals_to_params(locals()))

    async def reload(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("reload", locals_to_params(locals()))
        )

    async def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None,
    ) -> None:
        return await self._main_frame.wait_for_load_state(**locals_to_params(locals()))

    async def wait_for_url(
        self,
        url: URLMatch,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> None:
        return await self._main_frame.wait_for_url(**locals_to_params(locals()))

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    async def go_back(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goBack", locals_to_params(locals()))
        )

    async def go_forward(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goForward", locals_to_params(locals()))
        )

    async def request_gc(self) -> None:
        await self._channel.send("requestGC")

    async def emulate_media(
        self,
        media: Literal["null", "print", "screen"] = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
    ) -> None:
        params = locals_to_params(locals())
        if "media" in params:
            params["media"] = "no-override" if params["media"] == "null" else media
        if "colorScheme" in params:
            params["colorScheme"] = (
                "no-override" if params["colorScheme"] == "null" else colorScheme
            )
        if "reducedMotion" in params:
            params["reducedMotion"] = (
                "no-override" if params["reducedMotion"] == "null" else reducedMotion
            )
        if "forcedColors" in params:
            params["forcedColors"] = (
                "no-override" if params["forcedColors"] == "null" else forcedColors
            )
        if "contrast" in params:
            params["contrast"] = (
                "no-override" if params["contrast"] == "null" else contrast
            )
        await self._channel.send("emulateMedia", params)

    async def set_viewport_size(self, viewportSize: ViewportSize) -> None:
        self._viewport_size = viewportSize
        await self._channel.send("setViewportSize", locals_to_params(locals()))

    @property
    def viewport_size(self) -> Optional[ViewportSize]:
        return self._viewport_size

    async def bring_to_front(self) -> None:
        await self._channel.send("bringToFront")

    async def add_init_script(
        self, script: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            script = add_source_url_to_script(
                (await async_readfile(path)).decode(), path
            )
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        await self._channel.send("addInitScript", dict(source=script))

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: int = None
    ) -> None:
        self._routes.insert(
            0,
            RouteHandler(
                self._browser_context._options.get("baseURL"),
                url,
                handler,
                True if self._dispatcher_fiber else False,
                times,
            ),
        )
        await self._update_interception_patterns()

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback] = None
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            if route.url != url or (handler and route.handler != handler):
                remaining.append(route)
            else:
                removed.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[RouteHandler],
        remaining: List[RouteHandler],
        behavior: Literal["default", "ignoreErrors", "wait"] = None,
    ) -> None:
        self._routes = remaining
        await self._update_interception_patterns()
        if behavior is None or behavior == "default":
            return
        await asyncio.gather(
            *map(
                lambda route: route.stop(behavior),  # type: ignore
                removed,
            )
        )

    async def route_web_socket(
        self, url: URLMatch, handler: WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(
                self._browser_context._options.get("baseURL"), url, handler
            ),
        )
        await self._update_web_socket_interception_patterns()

    def _dispose_har_routers(self) -> None:
        for router in self._har_routers:
            router.dispose()
        self._har_routers = []

    async def unroute_all(
        self, behavior: Literal["default", "ignoreErrors", "wait"] = None
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Union[Pattern[str], str] = None,
        notFound: RouteFromHarNotFoundPolicy = None,
        update: bool = None,
        updateContent: Literal["attach", "embed"] = None,
        updateMode: HarMode = None,
    ) -> None:
        if update:
            await self._browser_context._record_into_har(
                har=har,
                page=self,
                url=url,
                update_content=updateContent,
                update_mode=updateMode,
            )
            return
        router = await HarRouter.create(
            local_utils=self._connection.local_utils,
            file=str(har),
            not_found_action=notFound or "abort",
            url_matcher=url,
        )
        self._har_routers.append(router)
        await router.add_page_route(self)

    async def _update_interception_patterns(self) -> None:
        patterns = RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.send(
            "setNetworkInterceptionPatterns", {"patterns": patterns}
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        patterns = WebSocketRouteHandler.prepare_interception_patterns(
            self._web_socket_routes
        )
        await self._channel.send(
            "setWebSocketInterceptionPatterns", {"patterns": patterns}
        )

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: FloatRect = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: Sequence["Locator"] = None,
        maskColor: str = None,
        style: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        if "mask" in params:
            params["mask"] = list(
                map(
                    lambda locator: (
                        {
                            "frame": locator._frame._channel,
                            "selector": locator._selector,
                        }
                    ),
                    params["mask"],
                )
            )
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def title(self) -> str:
        return await self._main_frame.title()

    async def close(self, runBeforeUnload: bool = None, reason: str = None) -> None:
        self._close_reason = reason
        self._close_was_called = True
        try:
            await self._channel.send("close", locals_to_params(locals()))
            if self._owned_context:
                await self._owned_context.close()
        except Exception as e:
            if not is_target_closed_error(e) and not runBeforeUnload:
                raise e

    def is_closed(self) -> bool:
        return self._is_closed

    async def click(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.click(**locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.dblclick(**locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.tap(**locals_to_params(locals()))

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> None:
        return await self._main_frame.fill(**locals_to_params(locals()))

    def locator(
        self,
        selector: str,
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        hasNot: "Locator" = None,
    ) -> "Locator":
        return self._main_frame.locator(
            selector,
            hasText=hasText,
            hasNotText=hasNotText,
            has=has,
            hasNot=hasNot,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_alt_text(text, exact=exact)

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_label(text, exact=exact)

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_placeholder(text, exact=exact)

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self._main_frame.get_by_role(
            role,
            checked=checked,
            disabled=disabled,
            expanded=expanded,
            includeHidden=includeHidden,
            level=level,
            name=name,
            pressed=pressed,
            selected=selected,
            exact=exact,
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self._main_frame.get_by_test_id(testId)

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_text(text, exact=exact)

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_title(text, exact=exact)

    def frame_locator(self, selector: str) -> "FrameLocator":
        return self.main_frame.frame_locator(selector)

    async def focus(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> None:
        return await self._main_frame.focus(**locals_to_params(locals()))

    async def text_content(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._main_frame.text_content(**locals_to_params(locals()))

    async def inner_text(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._main_frame.inner_text(**locals_to_params(locals()))

    async def inner_html(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._main_frame.inner_html(**locals_to_params(locals()))

    async def get_attribute(
        self, selector: str, name: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._main_frame.get_attribute(**locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.hover(**locals_to_params(locals()))

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        sourcePosition: Position = None,
        targetPosition: Position = None,
        force: bool = None,
        noWaitAfter: bool = None,
        timeout: float = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.drag_and_drop(**locals_to_params(locals()))

    async def select_option(
        self,
        selector: str,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        return await self._main_frame.select_option(**params)

    async def input_value(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        params = locals_to_params(locals())
        return await self._main_frame.input_value(**params)

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: float = None,
        strict: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.set_input_files(**locals_to_params(locals()))

    async def type(
        self,
        selector: str,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.type(**locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.press(**locals_to_params(locals()))

    async def check(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.check(**locals_to_params(locals()))

    async def uncheck(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.uncheck(**locals_to_params(locals()))

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._main_frame.wait_for_timeout(timeout)

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable = None,
        timeout: float = None,
        polling: Union[float, Literal["raf"]] = None,
    ) -> JSHandle:
        return await self._main_frame.wait_for_function(**locals_to_params(locals()))

    @property
    def workers(self) -> List["Worker"]:
        return self._workers.copy()

    @property
    def request(self) -> "APIRequestContext":
        return self.context.request

    async def pause(self) -> None:
        default_navigation_timeout = (
            self._browser_context._timeout_settings.default_navigation_timeout()
        )
        default_timeout = self._browser_context._timeout_settings.default_timeout()
        self._browser_context.set_default_navigation_timeout(0)
        self._browser_context.set_default_timeout(0)
        try:
            await asyncio.wait(
                [
                    asyncio.create_task(self._browser_context._channel.send("pause")),
                    self._closed_or_crashed_future,
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            self._browser_context._set_default_navigation_timeout_impl(
                default_navigation_timeout
            )
            self._browser_context._set_default_timeout_impl(default_timeout)

    async def pdf(
        self,
        scale: float = None,
        displayHeaderFooter: bool = None,
        headerTemplate: str = None,
        footerTemplate: str = None,
        printBackground: bool = None,
        landscape: bool = None,
        pageRanges: str = None,
        format: str = None,
        width: Union[str, float] = None,
        height: Union[str, float] = None,
        preferCSSPageSize: bool = None,
        margin: PdfMargins = None,
        path: Union[str, Path] = None,
        outline: bool = None,
        tagged: bool = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        encoded_binary = await self._channel.send("pdf", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    def _force_video(self) -> Video:
        if not self._video:
            self._video = Video(self)
        return self._video

    @property
    def video(
        self,
    ) -> Optional[Video]:
        # Note: we are creating Video object lazily, because we do not know
        # BrowserContextOptions when constructing the page - it is assigned
        # too late during launchPersistentContext.
        if not self._browser_context._options.get("recordVideo"):
            return None
        return self._force_video()

    def _close_error_with_reason(self) -> TargetClosedError:
        return TargetClosedError(
            self._close_reason or self._browser_context._effective_close_reason()
        )

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        return self._expect_event(
            event, predicate, timeout, f'waiting for event "{event}"'
        )

    def _expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
        log_line: str = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        waiter = Waiter(self, f"page.expect_event({event})")
        waiter.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if log_line:
            waiter.log(log_line)
        if event != Page.Events.Crash:
            waiter.reject_on_event(self, Page.Events.Crash, Error("Page crashed"))
        if event != Page.Events.Close:
            waiter.reject_on_event(
                self, Page.Events.Close, lambda: self._close_error_with_reason()
            )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    def expect_console_message(
        self,
        predicate: Callable[[ConsoleMessage], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(Page.Events.Console, predicate, timeout)

    def expect_download(
        self,
        predicate: Callable[[Download], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Download]:
        return self.expect_event(Page.Events.Download, predicate, timeout)

    def expect_file_chooser(
        self,
        predicate: Callable[[FileChooser], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[FileChooser]:
        return self.expect_event(Page.Events.FileChooser, predicate, timeout)

    def expect_navigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        return self.main_frame.expect_navigation(url, waitUntil, timeout)

    def expect_popup(
        self,
        predicate: Callable[["Page"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["Page"]:
        return self.expect_event(Page.Events.Popup, predicate, timeout)

    def expect_request(
        self,
        urlOrPredicate: URLMatchRequest,
        timeout: float = None,
    ) -> EventContextManagerImpl[Request]:
        def my_predicate(request: Request) -> bool:
            if not callable(urlOrPredicate):
                return url_matches(
                    self._browser_context._options.get("baseURL"),
                    request.url,
                    urlOrPredicate,
                )
            return urlOrPredicate(request)

        trimmed_url = trim_url(urlOrPredicate)
        log_line = f"waiting for request {trimmed_url}" if trimmed_url else None
        return self._expect_event(
            Page.Events.Request,
            predicate=my_predicate,
            timeout=timeout,
            log_line=log_line,
        )

    def expect_request_finished(
        self,
        predicate: Callable[["Request"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Request]:
        return self.expect_event(
            Page.Events.RequestFinished, predicate=predicate, timeout=timeout
        )

    def expect_response(
        self,
        urlOrPredicate: URLMatchResponse,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        def my_predicate(request: Response) -> bool:
            if not callable(urlOrPredicate):
                return url_matches(
                    self._browser_context._options.get("baseURL"),
                    request.url,
                    urlOrPredicate,
                )
            return urlOrPredicate(request)

        trimmed_url = trim_url(urlOrPredicate)
        log_line = f"waiting for response {trimmed_url}" if trimmed_url else None
        return self._expect_event(
            Page.Events.Response,
            predicate=my_predicate,
            timeout=timeout,
            log_line=log_line,
        )

    def expect_websocket(
        self,
        predicate: Callable[["WebSocket"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["WebSocket"]:
        return self.expect_event("websocket", predicate, timeout)

    def expect_worker(
        self,
        predicate: Callable[["Worker"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["Worker"]:
        return self.expect_event("worker", predicate, timeout)

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                strict=strict,
                trial=trial,
            )
        else:
            await self.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                strict=strict,
                trial=trial,
            )

    async def add_locator_handler(
        self,
        locator: "Locator",
        handler: Union[Callable[["Locator"], Any], Callable[[], Any]],
        noWaitAfter: bool = None,
        times: int = None,
    ) -> None:
        if locator._frame != self._main_frame:
            raise Error("Locator must belong to the main frame of this page")
        if times == 0:
            return
        uid = await self._channel.send(
            "registerLocatorHandler",
            {
                "selector": locator._selector,
                "noWaitAfter": noWaitAfter,
            },
        )
        self._locator_handlers[uid] = LocatorHandler(
            handler=handler, times=times, locator=locator
        )

    async def _on_locator_handler_triggered(self, uid: str) -> None:
        remove = False
        try:
            handler = self._locator_handlers.get(uid)
            if handler and handler.times != 0:
                if handler.times is not None:
                    handler.times -= 1
                if self._dispatcher_fiber:
                    handler_finished_future = self._loop.create_future()

                    def _handler() -> None:
                        try:
                            handler()
                            handler_finished_future.set_result(None)
                        except Exception as e:
                            handler_finished_future.set_exception(e)

                    g = LocatorHandlerGreenlet(_handler)
                    g.switch()
                    await handler_finished_future
                else:
                    coro_or_future = handler()
                    if coro_or_future:
                        await coro_or_future
                remove = handler.times == 0
        finally:
            if remove:
                del self._locator_handlers[uid]
            try:
                await self._connection.wrap_api_call(
                    lambda: self._channel.send(
                        "resolveLocatorHandlerNoReply", {"uid": uid, "remove": remove}
                    ),
                    is_internal=True,
                )
            except Error:
                pass

    async def remove_locator_handler(self, locator: "Locator") -> None:
        for uid, data in self._locator_handlers.copy().items():
            if data.locator._equals(locator):
                del self._locator_handlers[uid]
                self._channel.send_no_reply("unregisterLocatorHandler", {"uid": uid})


class Worker(ChannelOwner):
    Events = SimpleNamespace(Close="close")

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("close", lambda _: self._on_close())
        self._page: Optional[Page] = None
        self._context: Optional["BrowserContext"] = None

    def __repr__(self) -> str:
        return f"<Worker url={self.url!r}>"

    def _on_close(self) -> None:
        if self._page:
            self._page._workers.remove(self)
        if self._context:
            self._context._service_workers.remove(self)
        self.emit(Worker.Events.Close, self)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> JSHandle:
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )


class BindingCall(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def call(self, func: Callable) -> None:
        try:
            frame = from_channel(self._initializer["frame"])
            source = dict(context=frame._page.context, page=frame._page, frame=frame)
            if self._initializer.get("handle"):
                result = func(source, from_channel(self._initializer["handle"]))
            else:
                func_args = list(map(parse_result, self._initializer["args"]))
                result = func(source, *func_args)
            if inspect.iscoroutine(result):
                result = await result
            await self._channel.send("resolve", dict(result=serialize_argument(result)))
        except Exception as e:
            tb = sys.exc_info()[2]
            asyncio.create_task(
                self._channel.send(
                    "reject", dict(error=dict(error=serialize_error(e, tb)))
                )
            )


def trim_url(param: Union[URLMatchRequest, URLMatchResponse]) -> Optional[str]:
    if isinstance(param, re.Pattern):
        return trim_end(param.pattern)
    if isinstance(param, str):
        return trim_end(param)
    return None


def trim_end(s: str) -> str:
    if len(s) > 50:
        return s[:50] + "\u2026"
    return s

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\__init__.py ===
# Copyright 2020 The HuggingFace Team. All rights reserved.
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

# ***********
# `huggingface_hub` init has 2 modes:
# - Normal usage:
#       If imported to use it, all modules and functions are lazy-loaded. This means
#       they exist at top level in module but are imported only the first time they are
#       used. This way, `from huggingface_hub import something` will import `something`
#       quickly without the hassle of importing all the features from `huggingface_hub`.
# - Static check:
#       If statically analyzed, all modules and functions are loaded normally. This way
#       static typing check works properly as well as autocomplete in text editors and
#       IDEs.
#
# The static model imports are done inside the `if TYPE_CHECKING:` statement at
# the bottom of this file. Since module/functions imports are duplicated, it is
# mandatory to make sure to add them twice when adding one. This is checked in the
# `make quality` command.
#
# To update the static imports, please run the following command and commit the changes.
# ```
# # Use script
# python utils/check_static_imports.py --update-file
#
# # Or run style on codebase
# make style
# ```
#
# ***********
# Lazy loader vendored from https://github.com/scientific-python/lazy_loader
import importlib
import os
import sys
from typing import TYPE_CHECKING


__version__ = "0.33.0"

# Alphabetical order of definitions is ensured in tests
# WARNING: any comment added in this dictionary definition will be lost when
# re-generating the file !
_SUBMOD_ATTRS = {
    "_commit_scheduler": [
        "CommitScheduler",
    ],
    "_inference_endpoints": [
        "InferenceEndpoint",
        "InferenceEndpointError",
        "InferenceEndpointStatus",
        "InferenceEndpointTimeoutError",
        "InferenceEndpointType",
    ],
    "_login": [
        "auth_list",
        "auth_switch",
        "interpreter_login",
        "login",
        "logout",
        "notebook_login",
    ],
    "_oauth": [
        "OAuthInfo",
        "OAuthOrgInfo",
        "OAuthUserInfo",
        "attach_huggingface_oauth",
        "parse_huggingface_oauth",
    ],
    "_snapshot_download": [
        "snapshot_download",
    ],
    "_space_api": [
        "SpaceHardware",
        "SpaceRuntime",
        "SpaceStage",
        "SpaceStorage",
        "SpaceVariable",
    ],
    "_tensorboard_logger": [
        "HFSummaryWriter",
    ],
    "_webhooks_payload": [
        "WebhookPayload",
        "WebhookPayloadComment",
        "WebhookPayloadDiscussion",
        "WebhookPayloadDiscussionChanges",
        "WebhookPayloadEvent",
        "WebhookPayloadMovedTo",
        "WebhookPayloadRepo",
        "WebhookPayloadUrl",
        "WebhookPayloadWebhook",
    ],
    "_webhooks_server": [
        "WebhooksServer",
        "webhook_endpoint",
    ],
    "community": [
        "Discussion",
        "DiscussionComment",
        "DiscussionCommit",
        "DiscussionEvent",
        "DiscussionStatusChange",
        "DiscussionTitleChange",
        "DiscussionWithDetails",
    ],
    "constants": [
        "CONFIG_NAME",
        "FLAX_WEIGHTS_NAME",
        "HUGGINGFACE_CO_URL_HOME",
        "HUGGINGFACE_CO_URL_TEMPLATE",
        "PYTORCH_WEIGHTS_NAME",
        "REPO_TYPE_DATASET",
        "REPO_TYPE_MODEL",
        "REPO_TYPE_SPACE",
        "TF2_WEIGHTS_NAME",
        "TF_WEIGHTS_NAME",
    ],
    "fastai_utils": [
        "_save_pretrained_fastai",
        "from_pretrained_fastai",
        "push_to_hub_fastai",
    ],
    "file_download": [
        "HfFileMetadata",
        "_CACHED_NO_EXIST",
        "get_hf_file_metadata",
        "hf_hub_download",
        "hf_hub_url",
        "try_to_load_from_cache",
    ],
    "hf_api": [
        "Collection",
        "CollectionItem",
        "CommitInfo",
        "CommitOperation",
        "CommitOperationAdd",
        "CommitOperationCopy",
        "CommitOperationDelete",
        "DatasetInfo",
        "GitCommitInfo",
        "GitRefInfo",
        "GitRefs",
        "HfApi",
        "ModelInfo",
        "RepoUrl",
        "SpaceInfo",
        "User",
        "UserLikes",
        "WebhookInfo",
        "WebhookWatchedItem",
        "accept_access_request",
        "add_collection_item",
        "add_space_secret",
        "add_space_variable",
        "auth_check",
        "cancel_access_request",
        "change_discussion_status",
        "comment_discussion",
        "create_branch",
        "create_collection",
        "create_commit",
        "create_discussion",
        "create_inference_endpoint",
        "create_inference_endpoint_from_catalog",
        "create_pull_request",
        "create_repo",
        "create_tag",
        "create_webhook",
        "dataset_info",
        "delete_branch",
        "delete_collection",
        "delete_collection_item",
        "delete_file",
        "delete_folder",
        "delete_inference_endpoint",
        "delete_repo",
        "delete_space_secret",
        "delete_space_storage",
        "delete_space_variable",
        "delete_tag",
        "delete_webhook",
        "disable_webhook",
        "duplicate_space",
        "edit_discussion_comment",
        "enable_webhook",
        "file_exists",
        "get_collection",
        "get_dataset_tags",
        "get_discussion_details",
        "get_full_repo_name",
        "get_inference_endpoint",
        "get_model_tags",
        "get_paths_info",
        "get_repo_discussions",
        "get_safetensors_metadata",
        "get_space_runtime",
        "get_space_variables",
        "get_token_permission",
        "get_user_overview",
        "get_webhook",
        "grant_access",
        "list_accepted_access_requests",
        "list_collections",
        "list_datasets",
        "list_inference_catalog",
        "list_inference_endpoints",
        "list_lfs_files",
        "list_liked_repos",
        "list_models",
        "list_organization_members",
        "list_papers",
        "list_pending_access_requests",
        "list_rejected_access_requests",
        "list_repo_commits",
        "list_repo_files",
        "list_repo_likers",
        "list_repo_refs",
        "list_repo_tree",
        "list_spaces",
        "list_user_followers",
        "list_user_following",
        "list_webhooks",
        "merge_pull_request",
        "model_info",
        "move_repo",
        "paper_info",
        "parse_safetensors_file_metadata",
        "pause_inference_endpoint",
        "pause_space",
        "permanently_delete_lfs_files",
        "preupload_lfs_files",
        "reject_access_request",
        "rename_discussion",
        "repo_exists",
        "repo_info",
        "repo_type_and_id_from_hf_id",
        "request_space_hardware",
        "request_space_storage",
        "restart_space",
        "resume_inference_endpoint",
        "revision_exists",
        "run_as_future",
        "scale_to_zero_inference_endpoint",
        "set_space_sleep_time",
        "space_info",
        "super_squash_history",
        "unlike",
        "update_collection_item",
        "update_collection_metadata",
        "update_inference_endpoint",
        "update_repo_settings",
        "update_repo_visibility",
        "update_webhook",
        "upload_file",
        "upload_folder",
        "upload_large_folder",
        "whoami",
    ],
    "hf_file_system": [
        "HfFileSystem",
        "HfFileSystemFile",
        "HfFileSystemResolvedPath",
        "HfFileSystemStreamFile",
    ],
    "hub_mixin": [
        "ModelHubMixin",
        "PyTorchModelHubMixin",
    ],
    "inference._client": [
        "InferenceClient",
        "InferenceTimeoutError",
    ],
    "inference._generated._async_client": [
        "AsyncInferenceClient",
    ],
    "inference._generated.types": [
        "AudioClassificationInput",
        "AudioClassificationOutputElement",
        "AudioClassificationOutputTransform",
        "AudioClassificationParameters",
        "AudioToAudioInput",
        "AudioToAudioOutputElement",
        "AutomaticSpeechRecognitionEarlyStoppingEnum",
        "AutomaticSpeechRecognitionGenerationParameters",
        "AutomaticSpeechRecognitionInput",
        "AutomaticSpeechRecognitionOutput",
        "AutomaticSpeechRecognitionOutputChunk",
        "AutomaticSpeechRecognitionParameters",
        "ChatCompletionInput",
        "ChatCompletionInputFunctionDefinition",
        "ChatCompletionInputFunctionName",
        "ChatCompletionInputGrammarType",
        "ChatCompletionInputJSONSchema",
        "ChatCompletionInputMessage",
        "ChatCompletionInputMessageChunk",
        "ChatCompletionInputMessageChunkType",
        "ChatCompletionInputResponseFormatJSONObject",
        "ChatCompletionInputResponseFormatJSONSchema",
        "ChatCompletionInputResponseFormatText",
        "ChatCompletionInputStreamOptions",
        "ChatCompletionInputTool",
        "ChatCompletionInputToolCall",
        "ChatCompletionInputToolChoiceClass",
        "ChatCompletionInputToolChoiceEnum",
        "ChatCompletionInputURL",
        "ChatCompletionOutput",
        "ChatCompletionOutputComplete",
        "ChatCompletionOutputFunctionDefinition",
        "ChatCompletionOutputLogprob",
        "ChatCompletionOutputLogprobs",
        "ChatCompletionOutputMessage",
        "ChatCompletionOutputToolCall",
        "ChatCompletionOutputTopLogprob",
        "ChatCompletionOutputUsage",
        "ChatCompletionStreamOutput",
        "ChatCompletionStreamOutputChoice",
        "ChatCompletionStreamOutputDelta",
        "ChatCompletionStreamOutputDeltaToolCall",
        "ChatCompletionStreamOutputFunction",
        "ChatCompletionStreamOutputLogprob",
        "ChatCompletionStreamOutputLogprobs",
        "ChatCompletionStreamOutputTopLogprob",
        "ChatCompletionStreamOutputUsage",
        "DepthEstimationInput",
        "DepthEstimationOutput",
        "DocumentQuestionAnsweringInput",
        "DocumentQuestionAnsweringInputData",
        "DocumentQuestionAnsweringOutputElement",
        "DocumentQuestionAnsweringParameters",
        "FeatureExtractionInput",
        "FeatureExtractionInputTruncationDirection",
        "FillMaskInput",
        "FillMaskOutputElement",
        "FillMaskParameters",
        "ImageClassificationInput",
        "ImageClassificationOutputElement",
        "ImageClassificationOutputTransform",
        "ImageClassificationParameters",
        "ImageSegmentationInput",
        "ImageSegmentationOutputElement",
        "ImageSegmentationParameters",
        "ImageSegmentationSubtask",
        "ImageToImageInput",
        "ImageToImageOutput",
        "ImageToImageParameters",
        "ImageToImageTargetSize",
        "ImageToTextEarlyStoppingEnum",
        "ImageToTextGenerationParameters",
        "ImageToTextInput",
        "ImageToTextOutput",
        "ImageToTextParameters",
        "ObjectDetectionBoundingBox",
        "ObjectDetectionInput",
        "ObjectDetectionOutputElement",
        "ObjectDetectionParameters",
        "Padding",
        "QuestionAnsweringInput",
        "QuestionAnsweringInputData",
        "QuestionAnsweringOutputElement",
        "QuestionAnsweringParameters",
        "SentenceSimilarityInput",
        "SentenceSimilarityInputData",
        "SummarizationInput",
        "SummarizationOutput",
        "SummarizationParameters",
        "SummarizationTruncationStrategy",
        "TableQuestionAnsweringInput",
        "TableQuestionAnsweringInputData",
        "TableQuestionAnsweringOutputElement",
        "TableQuestionAnsweringParameters",
        "Text2TextGenerationInput",
        "Text2TextGenerationOutput",
        "Text2TextGenerationParameters",
        "Text2TextGenerationTruncationStrategy",
        "TextClassificationInput",
        "TextClassificationOutputElement",
        "TextClassificationOutputTransform",
        "TextClassificationParameters",
        "TextGenerationInput",
        "TextGenerationInputGenerateParameters",
        "TextGenerationInputGrammarType",
        "TextGenerationOutput",
        "TextGenerationOutputBestOfSequence",
        "TextGenerationOutputDetails",
        "TextGenerationOutputFinishReason",
        "TextGenerationOutputPrefillToken",
        "TextGenerationOutputToken",
        "TextGenerationStreamOutput",
        "TextGenerationStreamOutputStreamDetails",
        "TextGenerationStreamOutputToken",
        "TextToAudioEarlyStoppingEnum",
        "TextToAudioGenerationParameters",
        "TextToAudioInput",
        "TextToAudioOutput",
        "TextToAudioParameters",
        "TextToImageInput",
        "TextToImageOutput",
        "TextToImageParameters",
        "TextToSpeechEarlyStoppingEnum",
        "TextToSpeechGenerationParameters",
        "TextToSpeechInput",
        "TextToSpeechOutput",
        "TextToSpeechParameters",
        "TextToVideoInput",
        "TextToVideoOutput",
        "TextToVideoParameters",
        "TokenClassificationAggregationStrategy",
        "TokenClassificationInput",
        "TokenClassificationOutputElement",
        "TokenClassificationParameters",
        "TranslationInput",
        "TranslationOutput",
        "TranslationParameters",
        "TranslationTruncationStrategy",
        "TypeEnum",
        "VideoClassificationInput",
        "VideoClassificationOutputElement",
        "VideoClassificationOutputTransform",
        "VideoClassificationParameters",
        "VisualQuestionAnsweringInput",
        "VisualQuestionAnsweringInputData",
        "VisualQuestionAnsweringOutputElement",
        "VisualQuestionAnsweringParameters",
        "ZeroShotClassificationInput",
        "ZeroShotClassificationOutputElement",
        "ZeroShotClassificationParameters",
        "ZeroShotImageClassificationInput",
        "ZeroShotImageClassificationOutputElement",
        "ZeroShotImageClassificationParameters",
        "ZeroShotObjectDetectionBoundingBox",
        "ZeroShotObjectDetectionInput",
        "ZeroShotObjectDetectionOutputElement",
        "ZeroShotObjectDetectionParameters",
    ],
    "inference._mcp.agent": [
        "Agent",
    ],
    "inference._mcp.mcp_client": [
        "MCPClient",
    ],
    "inference_api": [
        "InferenceApi",
    ],
    "keras_mixin": [
        "KerasModelHubMixin",
        "from_pretrained_keras",
        "push_to_hub_keras",
        "save_pretrained_keras",
    ],
    "repocard": [
        "DatasetCard",
        "ModelCard",
        "RepoCard",
        "SpaceCard",
        "metadata_eval_result",
        "metadata_load",
        "metadata_save",
        "metadata_update",
    ],
    "repocard_data": [
        "CardData",
        "DatasetCardData",
        "EvalResult",
        "ModelCardData",
        "SpaceCardData",
    ],
    "repository": [
        "Repository",
    ],
    "serialization": [
        "StateDictSplit",
        "get_tf_storage_size",
        "get_torch_storage_id",
        "get_torch_storage_size",
        "load_state_dict_from_file",
        "load_torch_model",
        "save_torch_model",
        "save_torch_state_dict",
        "split_state_dict_into_shards_factory",
        "split_tf_state_dict_into_shards",
        "split_torch_state_dict_into_shards",
    ],
    "serialization._dduf": [
        "DDUFEntry",
        "export_entries_as_dduf",
        "export_folder_as_dduf",
        "read_dduf_file",
    ],
    "utils": [
        "CacheNotFound",
        "CachedFileInfo",
        "CachedRepoInfo",
        "CachedRevisionInfo",
        "CorruptedCacheException",
        "DeleteCacheStrategy",
        "HFCacheInfo",
        "HfFolder",
        "cached_assets_path",
        "configure_http_backend",
        "dump_environment_info",
        "get_session",
        "get_token",
        "logging",
        "scan_cache_dir",
    ],
}

# WARNING: __all__ is generated automatically, Any manual edit will be lost when re-generating this file !
#
# To update the static imports, please run the following command and commit the changes.
# ```
# # Use script
# python utils/check_all_variable.py --update
#
# # Or run style on codebase
# make style
# ```

__all__ = [
    "Agent",
    "AsyncInferenceClient",
    "AudioClassificationInput",
    "AudioClassificationOutputElement",
    "AudioClassificationOutputTransform",
    "AudioClassificationParameters",
    "AudioToAudioInput",
    "AudioToAudioOutputElement",
    "AutomaticSpeechRecognitionEarlyStoppingEnum",
    "AutomaticSpeechRecognitionGenerationParameters",
    "AutomaticSpeechRecognitionInput",
    "AutomaticSpeechRecognitionOutput",
    "AutomaticSpeechRecognitionOutputChunk",
    "AutomaticSpeechRecognitionParameters",
    "CONFIG_NAME",
    "CacheNotFound",
    "CachedFileInfo",
    "CachedRepoInfo",
    "CachedRevisionInfo",
    "CardData",
    "ChatCompletionInput",
    "ChatCompletionInputFunctionDefinition",
    "ChatCompletionInputFunctionName",
    "ChatCompletionInputGrammarType",
    "ChatCompletionInputJSONSchema",
    "ChatCompletionInputMessage",
    "ChatCompletionInputMessageChunk",
    "ChatCompletionInputMessageChunkType",
    "ChatCompletionInputResponseFormatJSONObject",
    "ChatCompletionInputResponseFormatJSONSchema",
    "ChatCompletionInputResponseFormatText",
    "ChatCompletionInputStreamOptions",
    "ChatCompletionInputTool",
    "ChatCompletionInputToolCall",
    "ChatCompletionInputToolChoiceClass",
    "ChatCompletionInputToolChoiceEnum",
    "ChatCompletionInputURL",
    "ChatCompletionOutput",
    "ChatCompletionOutputComplete",
    "ChatCompletionOutputFunctionDefinition",
    "ChatCompletionOutputLogprob",
    "ChatCompletionOutputLogprobs",
    "ChatCompletionOutputMessage",
    "ChatCompletionOutputToolCall",
    "ChatCompletionOutputTopLogprob",
    "ChatCompletionOutputUsage",
    "ChatCompletionStreamOutput",
    "ChatCompletionStreamOutputChoice",
    "ChatCompletionStreamOutputDelta",
    "ChatCompletionStreamOutputDeltaToolCall",
    "ChatCompletionStreamOutputFunction",
    "ChatCompletionStreamOutputLogprob",
    "ChatCompletionStreamOutputLogprobs",
    "ChatCompletionStreamOutputTopLogprob",
    "ChatCompletionStreamOutputUsage",
    "Collection",
    "CollectionItem",
    "CommitInfo",
    "CommitOperation",
    "CommitOperationAdd",
    "CommitOperationCopy",
    "CommitOperationDelete",
    "CommitScheduler",
    "CorruptedCacheException",
    "DDUFEntry",
    "DatasetCard",
    "DatasetCardData",
    "DatasetInfo",
    "DeleteCacheStrategy",
    "DepthEstimationInput",
    "DepthEstimationOutput",
    "Discussion",
    "DiscussionComment",
    "DiscussionCommit",
    "DiscussionEvent",
    "DiscussionStatusChange",
    "DiscussionTitleChange",
    "DiscussionWithDetails",
    "DocumentQuestionAnsweringInput",
    "DocumentQuestionAnsweringInputData",
    "DocumentQuestionAnsweringOutputElement",
    "DocumentQuestionAnsweringParameters",
    "EvalResult",
    "FLAX_WEIGHTS_NAME",
    "FeatureExtractionInput",
    "FeatureExtractionInputTruncationDirection",
    "FillMaskInput",
    "FillMaskOutputElement",
    "FillMaskParameters",
    "GitCommitInfo",
    "GitRefInfo",
    "GitRefs",
    "HFCacheInfo",
    "HFSummaryWriter",
    "HUGGINGFACE_CO_URL_HOME",
    "HUGGINGFACE_CO_URL_TEMPLATE",
    "HfApi",
    "HfFileMetadata",
    "HfFileSystem",
    "HfFileSystemFile",
    "HfFileSystemResolvedPath",
    "HfFileSystemStreamFile",
    "HfFolder",
    "ImageClassificationInput",
    "ImageClassificationOutputElement",
    "ImageClassificationOutputTransform",
    "ImageClassificationParameters",
    "ImageSegmentationInput",
    "ImageSegmentationOutputElement",
    "ImageSegmentationParameters",
    "ImageSegmentationSubtask",
    "ImageToImageInput",
    "ImageToImageOutput",
    "ImageToImageParameters",
    "ImageToImageTargetSize",
    "ImageToTextEarlyStoppingEnum",
    "ImageToTextGenerationParameters",
    "ImageToTextInput",
    "ImageToTextOutput",
    "ImageToTextParameters",
    "InferenceApi",
    "InferenceClient",
    "InferenceEndpoint",
    "InferenceEndpointError",
    "InferenceEndpointStatus",
    "InferenceEndpointTimeoutError",
    "InferenceEndpointType",
    "InferenceTimeoutError",
    "KerasModelHubMixin",
    "MCPClient",
    "ModelCard",
    "ModelCardData",
    "ModelHubMixin",
    "ModelInfo",
    "OAuthInfo",
    "OAuthOrgInfo",
    "OAuthUserInfo",
    "ObjectDetectionBoundingBox",
    "ObjectDetectionInput",
    "ObjectDetectionOutputElement",
    "ObjectDetectionParameters",
    "PYTORCH_WEIGHTS_NAME",
    "Padding",
    "PyTorchModelHubMixin",
    "QuestionAnsweringInput",
    "QuestionAnsweringInputData",
    "QuestionAnsweringOutputElement",
    "QuestionAnsweringParameters",
    "REPO_TYPE_DATASET",
    "REPO_TYPE_MODEL",
    "REPO_TYPE_SPACE",
    "RepoCard",
    "RepoUrl",
    "Repository",
    "SentenceSimilarityInput",
    "SentenceSimilarityInputData",
    "SpaceCard",
    "SpaceCardData",
    "SpaceHardware",
    "SpaceInfo",
    "SpaceRuntime",
    "SpaceStage",
    "SpaceStorage",
    "SpaceVariable",
    "StateDictSplit",
    "SummarizationInput",
    "SummarizationOutput",
    "SummarizationParameters",
    "SummarizationTruncationStrategy",
    "TF2_WEIGHTS_NAME",
    "TF_WEIGHTS_NAME",
    "TableQuestionAnsweringInput",
    "TableQuestionAnsweringInputData",
    "TableQuestionAnsweringOutputElement",
    "TableQuestionAnsweringParameters",
    "Text2TextGenerationInput",
    "Text2TextGenerationOutput",
    "Text2TextGenerationParameters",
    "Text2TextGenerationTruncationStrategy",
    "TextClassificationInput",
    "TextClassificationOutputElement",
    "TextClassificationOutputTransform",
    "TextClassificationParameters",
    "TextGenerationInput",
    "TextGenerationInputGenerateParameters",
    "TextGenerationInputGrammarType",
    "TextGenerationOutput",
    "TextGenerationOutputBestOfSequence",
    "TextGenerationOutputDetails",
    "TextGenerationOutputFinishReason",
    "TextGenerationOutputPrefillToken",
    "TextGenerationOutputToken",
    "TextGenerationStreamOutput",
    "TextGenerationStreamOutputStreamDetails",
    "TextGenerationStreamOutputToken",
    "TextToAudioEarlyStoppingEnum",
    "TextToAudioGenerationParameters",
    "TextToAudioInput",
    "TextToAudioOutput",
    "TextToAudioParameters",
    "TextToImageInput",
    "TextToImageOutput",
    "TextToImageParameters",
    "TextToSpeechEarlyStoppingEnum",
    "TextToSpeechGenerationParameters",
    "TextToSpeechInput",
    "TextToSpeechOutput",
    "TextToSpeechParameters",
    "TextToVideoInput",
    "TextToVideoOutput",
    "TextToVideoParameters",
    "TokenClassificationAggregationStrategy",
    "TokenClassificationInput",
    "TokenClassificationOutputElement",
    "TokenClassificationParameters",
    "TranslationInput",
    "TranslationOutput",
    "TranslationParameters",
    "TranslationTruncationStrategy",
    "TypeEnum",
    "User",
    "UserLikes",
    "VideoClassificationInput",
    "VideoClassificationOutputElement",
    "VideoClassificationOutputTransform",
    "VideoClassificationParameters",
    "VisualQuestionAnsweringInput",
    "VisualQuestionAnsweringInputData",
    "VisualQuestionAnsweringOutputElement",
    "VisualQuestionAnsweringParameters",
    "WebhookInfo",
    "WebhookPayload",
    "WebhookPayloadComment",
    "WebhookPayloadDiscussion",
    "WebhookPayloadDiscussionChanges",
    "WebhookPayloadEvent",
    "WebhookPayloadMovedTo",
    "WebhookPayloadRepo",
    "WebhookPayloadUrl",
    "WebhookPayloadWebhook",
    "WebhookWatchedItem",
    "WebhooksServer",
    "ZeroShotClassificationInput",
    "ZeroShotClassificationOutputElement",
    "ZeroShotClassificationParameters",
    "ZeroShotImageClassificationInput",
    "ZeroShotImageClassificationOutputElement",
    "ZeroShotImageClassificationParameters",
    "ZeroShotObjectDetectionBoundingBox",
    "ZeroShotObjectDetectionInput",
    "ZeroShotObjectDetectionOutputElement",
    "ZeroShotObjectDetectionParameters",
    "_CACHED_NO_EXIST",
    "_save_pretrained_fastai",
    "accept_access_request",
    "add_collection_item",
    "add_space_secret",
    "add_space_variable",
    "attach_huggingface_oauth",
    "auth_check",
    "auth_list",
    "auth_switch",
    "cached_assets_path",
    "cancel_access_request",
    "change_discussion_status",
    "comment_discussion",
    "configure_http_backend",
    "create_branch",
    "create_collection",
    "create_commit",
    "create_discussion",
    "create_inference_endpoint",
    "create_inference_endpoint_from_catalog",
    "create_pull_request",
    "create_repo",
    "create_tag",
    "create_webhook",
    "dataset_info",
    "delete_branch",
    "delete_collection",
    "delete_collection_item",
    "delete_file",
    "delete_folder",
    "delete_inference_endpoint",
    "delete_repo",
    "delete_space_secret",
    "delete_space_storage",
    "delete_space_variable",
    "delete_tag",
    "delete_webhook",
    "disable_webhook",
    "dump_environment_info",
    "duplicate_space",
    "edit_discussion_comment",
    "enable_webhook",
    "export_entries_as_dduf",
    "export_folder_as_dduf",
    "file_exists",
    "from_pretrained_fastai",
    "from_pretrained_keras",
    "get_collection",
    "get_dataset_tags",
    "get_discussion_details",
    "get_full_repo_name",
    "get_hf_file_metadata",
    "get_inference_endpoint",
    "get_model_tags",
    "get_paths_info",
    "get_repo_discussions",
    "get_safetensors_metadata",
    "get_session",
    "get_space_runtime",
    "get_space_variables",
    "get_tf_storage_size",
    "get_token",
    "get_token_permission",
    "get_torch_storage_id",
    "get_torch_storage_size",
    "get_user_overview",
    "get_webhook",
    "grant_access",
    "hf_hub_download",
    "hf_hub_url",
    "interpreter_login",
    "list_accepted_access_requests",
    "list_collections",
    "list_datasets",
    "list_inference_catalog",
    "list_inference_endpoints",
    "list_lfs_files",
    "list_liked_repos",
    "list_models",
    "list_organization_members",
    "list_papers",
    "list_pending_access_requests",
    "list_rejected_access_requests",
    "list_repo_commits",
    "list_repo_files",
    "list_repo_likers",
    "list_repo_refs",
    "list_repo_tree",
    "list_spaces",
    "list_user_followers",
    "list_user_following",
    "list_webhooks",
    "load_state_dict_from_file",
    "load_torch_model",
    "logging",
    "login",
    "logout",
    "merge_pull_request",
    "metadata_eval_result",
    "metadata_load",
    "metadata_save",
    "metadata_update",
    "model_info",
    "move_repo",
    "notebook_login",
    "paper_info",
    "parse_huggingface_oauth",
    "parse_safetensors_file_metadata",
    "pause_inference_endpoint",
    "pause_space",
    "permanently_delete_lfs_files",
    "preupload_lfs_files",
    "push_to_hub_fastai",
    "push_to_hub_keras",
    "read_dduf_file",
    "reject_access_request",
    "rename_discussion",
    "repo_exists",
    "repo_info",
    "repo_type_and_id_from_hf_id",
    "request_space_hardware",
    "request_space_storage",
    "restart_space",
    "resume_inference_endpoint",
    "revision_exists",
    "run_as_future",
    "save_pretrained_keras",
    "save_torch_model",
    "save_torch_state_dict",
    "scale_to_zero_inference_endpoint",
    "scan_cache_dir",
    "set_space_sleep_time",
    "snapshot_download",
    "space_info",
    "split_state_dict_into_shards_factory",
    "split_tf_state_dict_into_shards",
    "split_torch_state_dict_into_shards",
    "super_squash_history",
    "try_to_load_from_cache",
    "unlike",
    "update_collection_item",
    "update_collection_metadata",
    "update_inference_endpoint",
    "update_repo_settings",
    "update_repo_visibility",
    "update_webhook",
    "upload_file",
    "upload_folder",
    "upload_large_folder",
    "webhook_endpoint",
    "whoami",
]


def _attach(package_name, submodules=None, submod_attrs=None):
    """Attach lazily loaded submodules, functions, or other attributes.

    Typically, modules import submodules and attributes as follows:

    ```py
    import mysubmodule
    import anothersubmodule

    from .foo import someattr
    ```

    The idea is to replace a package's `__getattr__`, `__dir__`, such that all imports
    work exactly the way they would with normal imports, except that the import occurs
    upon first use.

    The typical way to call this function, replacing the above imports, is:

    ```python
    __getattr__, __dir__ = lazy.attach(
        __name__,
        ['mysubmodule', 'anothersubmodule'],
        {'foo': ['someattr']}
    )
    ```
    This functionality requires Python 3.7 or higher.

    Args:
        package_name (`str`):
            Typically use `__name__`.
        submodules (`set`):
            List of submodules to attach.
        submod_attrs (`dict`):
            Dictionary of submodule -> list of attributes / functions.
            These attributes are imported as they are used.

    Returns:
        __getattr__, __dir__, __all__

    """
    if submod_attrs is None:
        submod_attrs = {}

    if submodules is None:
        submodules = set()
    else:
        submodules = set(submodules)

    attr_to_modules = {attr: mod for mod, attrs in submod_attrs.items() for attr in attrs}

    def __getattr__(name):
        if name in submodules:
            try:
                return importlib.import_module(f"{package_name}.{name}")
            except Exception as e:
                print(f"Error importing {package_name}.{name}: {e}")
                raise
        elif name in attr_to_modules:
            submod_path = f"{package_name}.{attr_to_modules[name]}"
            try:
                submod = importlib.import_module(submod_path)
            except Exception as e:
                print(f"Error importing {submod_path}: {e}")
                raise
            attr = getattr(submod, name)

            # If the attribute lives in a file (module) with the same
            # name as the attribute, ensure that the attribute and *not*
            # the module is accessible on the package.
            if name == attr_to_modules[name]:
                pkg = sys.modules[package_name]
                pkg.__dict__[name] = attr

            return attr
        else:
            raise AttributeError(f"No {package_name} attribute {name}")

    def __dir__():
        return __all__

    return __getattr__, __dir__


__getattr__, __dir__ = _attach(__name__, submodules=[], submod_attrs=_SUBMOD_ATTRS)

if os.environ.get("EAGER_IMPORT", ""):
    for attr in __all__:
        __getattr__(attr)

# WARNING: any content below this statement is generated automatically. Any manual edit
# will be lost when re-generating this file !
#
# To update the static imports, please run the following command and commit the changes.
# ```
# # Use script
# python utils/check_static_imports.py --update
#
# # Or run style on codebase
# make style
# ```
if TYPE_CHECKING:  # pragma: no cover
    from ._commit_scheduler import CommitScheduler  # noqa: F401
    from ._inference_endpoints import (
        InferenceEndpoint,  # noqa: F401
        InferenceEndpointError,  # noqa: F401
        InferenceEndpointStatus,  # noqa: F401
        InferenceEndpointTimeoutError,  # noqa: F401
        InferenceEndpointType,  # noqa: F401
    )
    from ._login import (
        auth_list,  # noqa: F401
        auth_switch,  # noqa: F401
        interpreter_login,  # noqa: F401
        login,  # noqa: F401
        logout,  # noqa: F401
        notebook_login,  # noqa: F401
    )
    from ._oauth import (
        OAuthInfo,  # noqa: F401
        OAuthOrgInfo,  # noqa: F401
        OAuthUserInfo,  # noqa: F401
        attach_huggingface_oauth,  # noqa: F401
        parse_huggingface_oauth,  # noqa: F401
    )
    from ._snapshot_download import snapshot_download  # noqa: F401
    from ._space_api import (
        SpaceHardware,  # noqa: F401
        SpaceRuntime,  # noqa: F401
        SpaceStage,  # noqa: F401
        SpaceStorage,  # noqa: F401
        SpaceVariable,  # noqa: F401
    )
    from ._tensorboard_logger import HFSummaryWriter  # noqa: F401
    from ._webhooks_payload import (
        WebhookPayload,  # noqa: F401
        WebhookPayloadComment,  # noqa: F401
        WebhookPayloadDiscussion,  # noqa: F401
        WebhookPayloadDiscussionChanges,  # noqa: F401
        WebhookPayloadEvent,  # noqa: F401
        WebhookPayloadMovedTo,  # noqa: F401
        WebhookPayloadRepo,  # noqa: F401
        WebhookPayloadUrl,  # noqa: F401
        WebhookPayloadWebhook,  # noqa: F401
    )
    from ._webhooks_server import (
        WebhooksServer,  # noqa: F401
        webhook_endpoint,  # noqa: F401
    )
    from .community import (
        Discussion,  # noqa: F401
        DiscussionComment,  # noqa: F401
        DiscussionCommit,  # noqa: F401
        DiscussionEvent,  # noqa: F401
        DiscussionStatusChange,  # noqa: F401
        DiscussionTitleChange,  # noqa: F401
        DiscussionWithDetails,  # noqa: F401
    )
    from .constants import (
        CONFIG_NAME,  # noqa: F401
        FLAX_WEIGHTS_NAME,  # noqa: F401
        HUGGINGFACE_CO_URL_HOME,  # noqa: F401
        HUGGINGFACE_CO_URL_TEMPLATE,  # noqa: F401
        PYTORCH_WEIGHTS_NAME,  # noqa: F401
        REPO_TYPE_DATASET,  # noqa: F401
        REPO_TYPE_MODEL,  # noqa: F401
        REPO_TYPE_SPACE,  # noqa: F401
        TF2_WEIGHTS_NAME,  # noqa: F401
        TF_WEIGHTS_NAME,  # noqa: F401
    )
    from .fastai_utils import (
        _save_pretrained_fastai,  # noqa: F401
        from_pretrained_fastai,  # noqa: F401
        push_to_hub_fastai,  # noqa: F401
    )
    from .file_download import (
        _CACHED_NO_EXIST,  # noqa: F401
        HfFileMetadata,  # noqa: F401
        get_hf_file_metadata,  # noqa: F401
        hf_hub_download,  # noqa: F401
        hf_hub_url,  # noqa: F401
        try_to_load_from_cache,  # noqa: F401
    )
    from .hf_api import (
        Collection,  # noqa: F401
        CollectionItem,  # noqa: F401
        CommitInfo,  # noqa: F401
        CommitOperation,  # noqa: F401
        CommitOperationAdd,  # noqa: F401
        CommitOperationCopy,  # noqa: F401
        CommitOperationDelete,  # noqa: F401
        DatasetInfo,  # noqa: F401
        GitCommitInfo,  # noqa: F401
        GitRefInfo,  # noqa: F401
        GitRefs,  # noqa: F401
        HfApi,  # noqa: F401
        ModelInfo,  # noqa: F401
        RepoUrl,  # noqa: F401
        SpaceInfo,  # noqa: F401
        User,  # noqa: F401
        UserLikes,  # noqa: F401
        WebhookInfo,  # noqa: F401
        WebhookWatchedItem,  # noqa: F401
        accept_access_request,  # noqa: F401
        add_collection_item,  # noqa: F401
        add_space_secret,  # noqa: F401
        add_space_variable,  # noqa: F401
        auth_check,  # noqa: F401
        cancel_access_request,  # noqa: F401
        change_discussion_status,  # noqa: F401
        comment_discussion,  # noqa: F401
        create_branch,  # noqa: F401
        create_collection,  # noqa: F401
        create_commit,  # noqa: F401
        create_discussion,  # noqa: F401
        create_inference_endpoint,  # noqa: F401
        create_inference_endpoint_from_catalog,  # noqa: F401
        create_pull_request,  # noqa: F401
        create_repo,  # noqa: F401
        create_tag,  # noqa: F401
        create_webhook,  # noqa: F401
        dataset_info,  # noqa: F401
        delete_branch,  # noqa: F401
        delete_collection,  # noqa: F401
        delete_collection_item,  # noqa: F401
        delete_file,  # noqa: F401
        delete_folder,  # noqa: F401
        delete_inference_endpoint,  # noqa: F401
        delete_repo,  # noqa: F401
        delete_space_secret,  # noqa: F401
        delete_space_storage,  # noqa: F401
        delete_space_variable,  # noqa: F401
        delete_tag,  # noqa: F401
        delete_webhook,  # noqa: F401
        disable_webhook,  # noqa: F401
        duplicate_space,  # noqa: F401
        edit_discussion_comment,  # noqa: F401
        enable_webhook,  # noqa: F401
        file_exists,  # noqa: F401
        get_collection,  # noqa: F401
        get_dataset_tags,  # noqa: F401
        get_discussion_details,  # noqa: F401
        get_full_repo_name,  # noqa: F401
        get_inference_endpoint,  # noqa: F401
        get_model_tags,  # noqa: F401
        get_paths_info,  # noqa: F401
        get_repo_discussions,  # noqa: F401
        get_safetensors_metadata,  # noqa: F401
        get_space_runtime,  # noqa: F401
        get_space_variables,  # noqa: F401
        get_token_permission,  # noqa: F401
        get_user_overview,  # noqa: F401
        get_webhook,  # noqa: F401
        grant_access,  # noqa: F401
        list_accepted_access_requests,  # noqa: F401
        list_collections,  # noqa: F401
        list_datasets,  # noqa: F401
        list_inference_catalog,  # noqa: F401
        list_inference_endpoints,  # noqa: F401
        list_lfs_files,  # noqa: F401
        list_liked_repos,  # noqa: F401
        list_models,  # noqa: F401
        list_organization_members,  # noqa: F401
        list_papers,  # noqa: F401
        list_pending_access_requests,  # noqa: F401
        list_rejected_access_requests,  # noqa: F401
        list_repo_commits,  # noqa: F401
        list_repo_files,  # noqa: F401
        list_repo_likers,  # noqa: F401
        list_repo_refs,  # noqa: F401
        list_repo_tree,  # noqa: F401
        list_spaces,  # noqa: F401
        list_user_followers,  # noqa: F401
        list_user_following,  # noqa: F401
        list_webhooks,  # noqa: F401
        merge_pull_request,  # noqa: F401
        model_info,  # noqa: F401
        move_repo,  # noqa: F401
        paper_info,  # noqa: F401
        parse_safetensors_file_metadata,  # noqa: F401
        pause_inference_endpoint,  # noqa: F401
        pause_space,  # noqa: F401
        permanently_delete_lfs_files,  # noqa: F401
        preupload_lfs_files,  # noqa: F401
        reject_access_request,  # noqa: F401
        rename_discussion,  # noqa: F401
        repo_exists,  # noqa: F401
        repo_info,  # noqa: F401
        repo_type_and_id_from_hf_id,  # noqa: F401
        request_space_hardware,  # noqa: F401
        request_space_storage,  # noqa: F401
        restart_space,  # noqa: F401
        resume_inference_endpoint,  # noqa: F401
        revision_exists,  # noqa: F401
        run_as_future,  # noqa: F401
        scale_to_zero_inference_endpoint,  # noqa: F401
        set_space_sleep_time,  # noqa: F401
        space_info,  # noqa: F401
        super_squash_history,  # noqa: F401
        unlike,  # noqa: F401
        update_collection_item,  # noqa: F401
        update_collection_metadata,  # noqa: F401
        update_inference_endpoint,  # noqa: F401
        update_repo_settings,  # noqa: F401
        update_repo_visibility,  # noqa: F401
        update_webhook,  # noqa: F401
        upload_file,  # noqa: F401
        upload_folder,  # noqa: F401
        upload_large_folder,  # noqa: F401
        whoami,  # noqa: F401
    )
    from .hf_file_system import (
        HfFileSystem,  # noqa: F401
        HfFileSystemFile,  # noqa: F401
        HfFileSystemResolvedPath,  # noqa: F401
        HfFileSystemStreamFile,  # noqa: F401
    )
    from .hub_mixin import (
        ModelHubMixin,  # noqa: F401
        PyTorchModelHubMixin,  # noqa: F401
    )
    from .inference._client import (
        InferenceClient,  # noqa: F401
        InferenceTimeoutError,  # noqa: F401
    )
    from .inference._generated._async_client import AsyncInferenceClient  # noqa: F401
    from .inference._generated.types import (
        AudioClassificationInput,  # noqa: F401
        AudioClassificationOutputElement,  # noqa: F401
        AudioClassificationOutputTransform,  # noqa: F401
        AudioClassificationParameters,  # noqa: F401
        AudioToAudioInput,  # noqa: F401
        AudioToAudioOutputElement,  # noqa: F401
        AutomaticSpeechRecognitionEarlyStoppingEnum,  # noqa: F401
        AutomaticSpeechRecognitionGenerationParameters,  # noqa: F401
        AutomaticSpeechRecognitionInput,  # noqa: F401
        AutomaticSpeechRecognitionOutput,  # noqa: F401
        AutomaticSpeechRecognitionOutputChunk,  # noqa: F401
        AutomaticSpeechRecognitionParameters,  # noqa: F401
        ChatCompletionInput,  # noqa: F401
        ChatCompletionInputFunctionDefinition,  # noqa: F401
        ChatCompletionInputFunctionName,  # noqa: F401
        ChatCompletionInputGrammarType,  # noqa: F401
        ChatCompletionInputJSONSchema,  # noqa: F401
        ChatCompletionInputMessage,  # noqa: F401
        ChatCompletionInputMessageChunk,  # noqa: F401
        ChatCompletionInputMessageChunkType,  # noqa: F401
        ChatCompletionInputResponseFormatJSONObject,  # noqa: F401
        ChatCompletionInputResponseFormatJSONSchema,  # noqa: F401
        ChatCompletionInputResponseFormatText,  # noqa: F401
        ChatCompletionInputStreamOptions,  # noqa: F401
        ChatCompletionInputTool,  # noqa: F401
        ChatCompletionInputToolCall,  # noqa: F401
        ChatCompletionInputToolChoiceClass,  # noqa: F401
        ChatCompletionInputToolChoiceEnum,  # noqa: F401
        ChatCompletionInputURL,  # noqa: F401
        ChatCompletionOutput,  # noqa: F401
        ChatCompletionOutputComplete,  # noqa: F401
        ChatCompletionOutputFunctionDefinition,  # noqa: F401
        ChatCompletionOutputLogprob,  # noqa: F401
        ChatCompletionOutputLogprobs,  # noqa: F401
        ChatCompletionOutputMessage,  # noqa: F401
        ChatCompletionOutputToolCall,  # noqa: F401
        ChatCompletionOutputTopLogprob,  # noqa: F401
        ChatCompletionOutputUsage,  # noqa: F401
        ChatCompletionStreamOutput,  # noqa: F401
        ChatCompletionStreamOutputChoice,  # noqa: F401
        ChatCompletionStreamOutputDelta,  # noqa: F401
        ChatCompletionStreamOutputDeltaToolCall,  # noqa: F401
        ChatCompletionStreamOutputFunction,  # noqa: F401
        ChatCompletionStreamOutputLogprob,  # noqa: F401
        ChatCompletionStreamOutputLogprobs,  # noqa: F401
        ChatCompletionStreamOutputTopLogprob,  # noqa: F401
        ChatCompletionStreamOutputUsage,  # noqa: F401
        DepthEstimationInput,  # noqa: F401
        DepthEstimationOutput,  # noqa: F401
        DocumentQuestionAnsweringInput,  # noqa: F401
        DocumentQuestionAnsweringInputData,  # noqa: F401
        DocumentQuestionAnsweringOutputElement,  # noqa: F401
        DocumentQuestionAnsweringParameters,  # noqa: F401
        FeatureExtractionInput,  # noqa: F401
        FeatureExtractionInputTruncationDirection,  # noqa: F401
        FillMaskInput,  # noqa: F401
        FillMaskOutputElement,  # noqa: F401
        FillMaskParameters,  # noqa: F401
        ImageClassificationInput,  # noqa: F401
        ImageClassificationOutputElement,  # noqa: F401
        ImageClassificationOutputTransform,  # noqa: F401
        ImageClassificationParameters,  # noqa: F401
        ImageSegmentationInput,  # noqa: F401
        ImageSegmentationOutputElement,  # noqa: F401
        ImageSegmentationParameters,  # noqa: F401
        ImageSegmentationSubtask,  # noqa: F401
        ImageToImageInput,  # noqa: F401
        ImageToImageOutput,  # noqa: F401
        ImageToImageParameters,  # noqa: F401
        ImageToImageTargetSize,  # noqa: F401
        ImageToTextEarlyStoppingEnum,  # noqa: F401
        ImageToTextGenerationParameters,  # noqa: F401
        ImageToTextInput,  # noqa: F401
        ImageToTextOutput,  # noqa: F401
        ImageToTextParameters,  # noqa: F401
        ObjectDetectionBoundingBox,  # noqa: F401
        ObjectDetectionInput,  # noqa: F401
        ObjectDetectionOutputElement,  # noqa: F401
        ObjectDetectionParameters,  # noqa: F401
        Padding,  # noqa: F401
        QuestionAnsweringInput,  # noqa: F401
        QuestionAnsweringInputData,  # noqa: F401
        QuestionAnsweringOutputElement,  # noqa: F401
        QuestionAnsweringParameters,  # noqa: F401
        SentenceSimilarityInput,  # noqa: F401
        SentenceSimilarityInputData,  # noqa: F401
        SummarizationInput,  # noqa: F401
        SummarizationOutput,  # noqa: F401
        SummarizationParameters,  # noqa: F401
        SummarizationTruncationStrategy,  # noqa: F401
        TableQuestionAnsweringInput,  # noqa: F401
        TableQuestionAnsweringInputData,  # noqa: F401
        TableQuestionAnsweringOutputElement,  # noqa: F401
        TableQuestionAnsweringParameters,  # noqa: F401
        Text2TextGenerationInput,  # noqa: F401
        Text2TextGenerationOutput,  # noqa: F401
        Text2TextGenerationParameters,  # noqa: F401
        Text2TextGenerationTruncationStrategy,  # noqa: F401
        TextClassificationInput,  # noqa: F401
        TextClassificationOutputElement,  # noqa: F401
        TextClassificationOutputTransform,  # noqa: F401
        TextClassificationParameters,  # noqa: F401
        TextGenerationInput,  # noqa: F401
        TextGenerationInputGenerateParameters,  # noqa: F401
        TextGenerationInputGrammarType,  # noqa: F401
        TextGenerationOutput,  # noqa: F401
        TextGenerationOutputBestOfSequence,  # noqa: F401
        TextGenerationOutputDetails,  # noqa: F401
        TextGenerationOutputFinishReason,  # noqa: F401
        TextGenerationOutputPrefillToken,  # noqa: F401
        TextGenerationOutputToken,  # noqa: F401
        TextGenerationStreamOutput,  # noqa: F401
        TextGenerationStreamOutputStreamDetails,  # noqa: F401
        TextGenerationStreamOutputToken,  # noqa: F401
        TextToAudioEarlyStoppingEnum,  # noqa: F401
        TextToAudioGenerationParameters,  # noqa: F401
        TextToAudioInput,  # noqa: F401
        TextToAudioOutput,  # noqa: F401
        TextToAudioParameters,  # noqa: F401
        TextToImageInput,  # noqa: F401
        TextToImageOutput,  # noqa: F401
        TextToImageParameters,  # noqa: F401
        TextToSpeechEarlyStoppingEnum,  # noqa: F401
        TextToSpeechGenerationParameters,  # noqa: F401
        TextToSpeechInput,  # noqa: F401
        TextToSpeechOutput,  # noqa: F401
        TextToSpeechParameters,  # noqa: F401
        TextToVideoInput,  # noqa: F401
        TextToVideoOutput,  # noqa: F401
        TextToVideoParameters,  # noqa: F401
        TokenClassificationAggregationStrategy,  # noqa: F401
        TokenClassificationInput,  # noqa: F401
        TokenClassificationOutputElement,  # noqa: F401
        TokenClassificationParameters,  # noqa: F401
        TranslationInput,  # noqa: F401
        TranslationOutput,  # noqa: F401
        TranslationParameters,  # noqa: F401
        TranslationTruncationStrategy,  # noqa: F401
        TypeEnum,  # noqa: F401
        VideoClassificationInput,  # noqa: F401
        VideoClassificationOutputElement,  # noqa: F401
        VideoClassificationOutputTransform,  # noqa: F401
        VideoClassificationParameters,  # noqa: F401
        VisualQuestionAnsweringInput,  # noqa: F401
        VisualQuestionAnsweringInputData,  # noqa: F401
        VisualQuestionAnsweringOutputElement,  # noqa: F401
        VisualQuestionAnsweringParameters,  # noqa: F401
        ZeroShotClassificationInput,  # noqa: F401
        ZeroShotClassificationOutputElement,  # noqa: F401
        ZeroShotClassificationParameters,  # noqa: F401
        ZeroShotImageClassificationInput,  # noqa: F401
        ZeroShotImageClassificationOutputElement,  # noqa: F401
        ZeroShotImageClassificationParameters,  # noqa: F401
        ZeroShotObjectDetectionBoundingBox,  # noqa: F401
        ZeroShotObjectDetectionInput,  # noqa: F401
        ZeroShotObjectDetectionOutputElement,  # noqa: F401
        ZeroShotObjectDetectionParameters,  # noqa: F401
    )
    from .inference._mcp.agent import Agent  # noqa: F401
    from .inference._mcp.mcp_client import MCPClient  # noqa: F401
    from .inference_api import InferenceApi  # noqa: F401
    from .keras_mixin import (
        KerasModelHubMixin,  # noqa: F401
        from_pretrained_keras,  # noqa: F401
        push_to_hub_keras,  # noqa: F401
        save_pretrained_keras,  # noqa: F401
    )
    from .repocard import (
        DatasetCard,  # noqa: F401
        ModelCard,  # noqa: F401
        RepoCard,  # noqa: F401
        SpaceCard,  # noqa: F401
        metadata_eval_result,  # noqa: F401
        metadata_load,  # noqa: F401
        metadata_save,  # noqa: F401
        metadata_update,  # noqa: F401
    )
    from .repocard_data import (
        CardData,  # noqa: F401
        DatasetCardData,  # noqa: F401
        EvalResult,  # noqa: F401
        ModelCardData,  # noqa: F401
        SpaceCardData,  # noqa: F401
    )
    from .repository import Repository  # noqa: F401
    from .serialization import (
        StateDictSplit,  # noqa: F401
        get_tf_storage_size,  # noqa: F401
        get_torch_storage_id,  # noqa: F401
        get_torch_storage_size,  # noqa: F401
        load_state_dict_from_file,  # noqa: F401
        load_torch_model,  # noqa: F401
        save_torch_model,  # noqa: F401
        save_torch_state_dict,  # noqa: F401
        split_state_dict_into_shards_factory,  # noqa: F401
        split_tf_state_dict_into_shards,  # noqa: F401
        split_torch_state_dict_into_shards,  # noqa: F401
    )
    from .serialization._dduf import (
        DDUFEntry,  # noqa: F401
        export_entries_as_dduf,  # noqa: F401
        export_folder_as_dduf,  # noqa: F401
        read_dduf_file,  # noqa: F401
    )
    from .utils import (
        CachedFileInfo,  # noqa: F401
        CachedRepoInfo,  # noqa: F401
        CachedRevisionInfo,  # noqa: F401
        CacheNotFound,  # noqa: F401
        CorruptedCacheException,  # noqa: F401
        DeleteCacheStrategy,  # noqa: F401
        HFCacheInfo,  # noqa: F401
        HfFolder,  # noqa: F401
        cached_assets_path,  # noqa: F401
        configure_http_backend,  # noqa: F401
        dump_environment_info,  # noqa: F401
        get_session,  # noqa: F401
        get_token,  # noqa: F401
        logging,  # noqa: F401
        scan_cache_dir,  # noqa: F401
    )